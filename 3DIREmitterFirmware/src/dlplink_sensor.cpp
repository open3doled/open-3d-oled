#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "dlplink_sensor.h"

#define mult_by_threshold(high, low, threshold) (((uint16_t)threshold * (uint16_t)high + (uint16_t)(255 - threshold) * (uint16_t)low) >> 8)

// Global configuration variables (with default values; can be overridden elsewhere)
uint32_t dlplink_sensor_block_signal_detection_delay = OPT_SENSOR_BLOCK_SIGNAL_DETECTION_DELAY;      // Blocking delay after a pulse (in µs)
uint8_t dlplink_sensor_min_threshold_value_to_activate = DLP_SENSOR_MIN_THRESHOLD_VALUE_TO_ACTIVATE; // Minimum ADC value to activate detection
uint8_t dlplink_sensor_detection_threshold_high = 128;                                               // High threshold for pulse detection (ADC value)
uint8_t dlplink_sensor_detection_threshold_low = 64;                                                 // Low threshold for pulse end (ADC value)
uint8_t dlplink_sensor_enable_ignore_during_ir = 0;                                                  // Ignore sensor during IR transmission (1=enabled)

// External flags (provided by other modules)
extern volatile bool ir_led_token_active; // Flag indicating IR LED transmission is active
extern uint8_t opt_sensor_output_stats;   // Flag indicating whether +stats mode is enabled

// IR ignore countdown (loops) after IR LED active
#define DLP_SENSOR_IR_IGNORE_COUNT 10

// Internal state for pulse detection (static, persistent across interrupts)
static uint32_t last_pulse_start_time = 0; // Timestamp of the previous pulse's start (for interval measurement)
static uint16_t prev_interval = 0;         // Last measured inter-pulse interval (for baseline refinement)
static uint32_t block_until_time = 0;      // Time until which new pulse detection is blocked (after a pulse)
static uint32_t ir_led_token_active_countdown = 0;
static uint32_t pulse_count = 0;       // Total pulses detected
static uint16_t baseline_est = 0;      // Estimated frame interval (baseline period in µs)
static int16_t last_jitter_us = 0;     // Last measured jitter (µs, positive=longer, negative=shorter)
static uint8_t last_eye = EYE_LEFT;    // Last detected eye (0=Left,1=Right)
static uint8_t trigger_eye = EYE_LEFT; // Eye value for the pending trigger event
static uint8_t dlplink_sensor_reading_high = 255;
static uint8_t dlplink_sensor_reading_low = 0;
static uint16_t loop_counter = 0;
static uint16_t loop_counter_update_thresholds_at = 0;

// Variables for communication with main loop (volatile because they are set in ISR and read in main)
static volatile uint8_t adc_value = 0;
static volatile uint8_t dlplink_pulse_count = 0;
static volatile uint8_t dlplink_pulse_count_detected = 0;
static volatile uint8_t dlplink_sensor_reading_threshold_high = 255;
static volatile uint8_t dlplink_sensor_reading_threshold_low = 0;

#ifdef ENABLE_DEBUG_PIN_OUTPUTS
static uint16_t dlplink_disable_debug_detection_flag_at = 0;
#endif

void dlplink_sensor_init(void)
{
    // Reset internal state
    last_pulse_start_time = 0;
    baseline_est = 0;
    prev_interval = 0;
    block_until_time = 0;
    ir_led_token_active_countdown = 0;
    pulse_count = 0;
    trigger_eye = EYE_LEFT;
    last_eye = EYE_LEFT;
    last_jitter_us = 0;
    dlplink_sensor_reading_high = 0;
    dlplink_sensor_reading_low = 255;
    dlplink_sensor_reading_threshold_high = 0;
    dlplink_sensor_reading_threshold_low = 255;
    loop_counter = 0;
    loop_counter_update_thresholds_at = 0;
    adc_value = 0;
    dlplink_pulse_count = 0;
    dlplink_pulse_count_detected = 0;

#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    dlplink_disable_debug_detection_flag_at = 0;
#endif

    // Configure ADC for free-running mode on ADC6 (DLP-Link sensor channel)
    ADCSRA &= ~(1 << ADEN);                                // Disable ADC to configure
    ADMUX = (1 << REFS0)                                   // AVcc as reference voltage
            | (1 << ADLAR)                                 // Left-adjust result (8-bit reading from ADCH)
            | 6;                                           // Select ADC6 channel
    ADCSRB = 0x00 | _BV(ADHSM);                            // Free running mode, no auto-trigger source (ADTS=000)
    DIDR0 |= (1 << DLP_SENSOR_CHANNEL);                    // Disable digital input on ADC6 pin
    ADCSRA = (1 << ADEN)                                   // Enable ADC
             | (1 << ADSC)                                 // start conversion
             | (1 << ADIF)                                 // Clear interrupt flag
             | (1 << ADATE)                                // Auto-trigger enable (free-run)
             | (1 << ADIE)                                 // Enable ADC interrupt
                                                           // | (0 << ADPS2) | (1 << ADPS1) | (0 << ADPS0); // Prescaler = 4 (ADC clock ~2 MHz)
                                                           // | (0 << ADPS2) | (1 << ADPS1) | (1 << ADPS0); // Prescaler = 8 (ADC clock ~2 MHz)
             | (1 << ADPS2) | (0 << ADPS1) | (0 << ADPS0); // Prescaler = 16 (ADC clock ~2 MHz)
    ADCSRA |= (1 << ADSC);                                 // Start ADC conversions
}

void dlplink_sensor_stop(void)
{
    ADCSRA &= ~(_BV(ADEN) | _BV(ADIE));
}

void dlplink_sensor_check_readings(void)
{
    bool trigger_pending = false; // Whether a trigger event is waiting to be processed in main
    cli();
    uint8_t value = adc_value;
    uint8_t pulse_count_detected = dlplink_pulse_count_detected;
    dlplink_pulse_count_detected = 0;
    sei();

#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    if (loop_counter == dlplink_disable_debug_detection_flag_at)
    {
        bitClear(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
        bitClear(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
    }
#endif

    // 4) IR ignore countdown
#ifdef DLP_SENSOR_IR_IGNORE_COUNT
    if (dlplink_sensor_enable_ignore_during_ir)
    {
        if (ir_led_token_active)
        {
            ir_led_token_active_countdown = DLP_SENSOR_IR_IGNORE_COUNT;
        }
        if (ir_led_token_active_countdown > 0)
        {
            ir_led_token_active_countdown--;
            return;
        }
    }
#endif

    loop_counter++;
    dlplink_sensor_reading_high = max(dlplink_sensor_reading_high, value);
    dlplink_sensor_reading_low = min(dlplink_sensor_reading_low, value);
    if (loop_counter > loop_counter_update_thresholds_at)
    {
        cli();
        dlplink_sensor_reading_threshold_high = mult_by_threshold(dlplink_sensor_reading_high, dlplink_sensor_reading_low, dlplink_sensor_detection_threshold_high);
        dlplink_sensor_reading_threshold_low = mult_by_threshold(dlplink_sensor_reading_high, dlplink_sensor_reading_low, dlplink_sensor_detection_threshold_low);
        sei();
        loop_counter_update_thresholds_at += 80000; // About every 1 seconds
        dlplink_disable_debug_detection_flag_at -= loop_counter;
        loop_counter = 0;
        dlplink_sensor_reading_high = 0;
        dlplink_sensor_reading_low = 255;
    }

    if (pulse_count_detected > 0)
    {
        uint32_t now = micros();

        if (dlplink_sensor_reading_high < dlplink_sensor_min_threshold_value_to_activate)
        {
            return;
        }

        // 1) Post-pulse blocking
        if (block_until_time)
        {
            if (now < block_until_time)
            {
                return;
            }
            block_until_time = 0;
        }

        // Update stats
        pulse_count++;

        // Compute interval since last pulse
        uint32_t interval = now - last_pulse_start_time;
        int32_t diff = (int32_t)interval - (int32_t)baseline_est;

        // 2x diff should match the values in the datasheet page 38 https://www.ti.com/lit/ds/symlink/dlpc3434.pdf
        // Specifically 15836 / [diff] = Refresh Hz
        // diff ~= 15836 / Refresh Hz
        // diff ~= 15836 * Refresh Period
        // Refresh Period = [diff] / 15836
        // 15836 = 0x3DDC

        // 2) Eye classification with jitter window
        uint8_t eye;
        if (diff > 2000) // this is caused by missing one frames pulse so just repeat eyes
            eye = last_eye;
        else if (diff > 30)
            eye = EYE_RIGHT;
        else if (diff < -30)
            eye = EYE_LEFT;
        else
            eye = last_eye;

        // 3) Baseline update only on eye flip (except initial pulses)
        if (pulse_count == 1)
        {
            last_jitter_us = 0;
            trigger_pending = false;
        }
        else if (pulse_count == 2)
        {
            // Initial baseline estimation with extra ranges
            if (interval > 14500)
                baseline_est = 16667; // ~60Hz
            else if (interval > 13500)
                baseline_est = 12500; // ~80Hz
            else if (interval > 11000)
                baseline_est = 10417; // ~96Hz
            else if (interval > 10000)
                baseline_est = 10000; // ~100Hz
            else if (interval > 8000)
                baseline_est = 8333; // ~120Hz
            else
                baseline_est = 6944; // ~144Hz
            prev_interval = (uint16_t)interval;
            last_jitter_us = diff;
            last_eye = eye;
            trigger_eye = eye;
            trigger_pending = true;
        }
        else
        {
            if (eye != last_eye || diff > 150 || diff < -150)
            {
                baseline_est = (uint16_t)(((uint32_t)prev_interval + interval) / 2);
                prev_interval = (uint16_t)interval;
            }
            last_jitter_us = diff;
            last_eye = eye;
            trigger_eye = eye;
            trigger_pending = true;
        }

        // 1) Post-pulse block
        block_until_time = now + dlplink_sensor_block_signal_detection_delay;
        last_pulse_start_time = now;
    }

    // If an eye trigger event was set in the ISR, process it
    if (trigger_pending)
    {
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
        ;
        dlplink_disable_debug_detection_flag_at = loop_counter + 300; // around 3-4 ms at 12.5 microsecond loop time average
        if (last_eye)
        {
            bitSet(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
        }
        else
        {
            bitSet(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
        }
#endif
        if (last_eye == EYE_LEFT)
        {
            int16_t delay;
            uint16_t abs_jitter = abs(last_jitter_us);
            // 15836 / Hz
            // 144 = 109.9, 120 = 132, 100 = 158.4, 96 = 164.9, 90 = 175.9, 80 = 197.95, 75 = 211.15, 60 = 263.9
            if (abs_jitter < 120)
            {
                delay = 110;
            }
            else if (abs_jitter < 145)
            {
                delay = 132;
            }
            else if (abs_jitter < 162)
            {
                delay = 158;
            }
            else if (abs_jitter < 170)
            {
                delay = 165;
            }
            else if (abs_jitter < 185)
            {
                delay = 176;
            }
            else if (abs_jitter < 205)
            {
                delay = 198;
            }
            else if (abs_jitter < 240)
            {
                delay = 211;
            }
            else
            {
                delay = 264;
            }
            delayMicroseconds(delay);
        }
        ir_signal_process_trigger(trigger_eye);
        trigger_pending = false;
    }
}

void dlplink_sensor_print_stats(void)
{
    // If +stats mode is enabled, print DLP-Link sensor statistics
    if (opt_sensor_output_stats)
    {
        Serial.print("+stats dlplink");
        Serial.print(" high:");
        Serial.print(dlplink_sensor_reading_high);
        Serial.print(" low:");
        Serial.print(dlplink_sensor_reading_low);
        Serial.print(" thresh_high:");
        Serial.print(dlplink_sensor_reading_threshold_high);
        Serial.print(" thresh_low:");
        Serial.print(dlplink_sensor_reading_threshold_low);
        Serial.print(" pulses:");
        Serial.print(pulse_count);
        Serial.print(" pulse_width_count:");
        Serial.print(dlplink_pulse_count_detected);
        Serial.print(" baseline_est:");
        Serial.print(baseline_est);
        Serial.print(" jitter:");
        Serial.print(last_jitter_us);
        Serial.print(" last_eye:");
        Serial.println((last_eye == EYE_LEFT ? 'L' : 'R'));
    }
}

void dlplink_sensor_adc_isr_handler(void)
{
    adc_value = ADCH;
    if (adc_value > dlplink_sensor_reading_threshold_high)
    {
        if (dlplink_pulse_count < 255)
        {
            dlplink_pulse_count++;
        }
    }
    else if (adc_value > dlplink_sensor_reading_threshold_low)
    {
        if (dlplink_pulse_count > 0 && dlplink_pulse_count < 255)
        {
            dlplink_pulse_count++;
        }
    }
    else
    {
        // The pulse length needs to be between 20 to 32 microseconds but we can only make a determination based on results we have so we say 1 to 4 ADC cycles.
        // https://www.ti.com/lit/ds/symlink/dlpc3434.pdf
        if (dlplink_pulse_count > 0)
        {
            // if (dlplink_pulse_count < 5) // Good for DLP Link Based on Specs 20 to 32 microseconds
            if (dlplink_pulse_count > 5 && dlplink_pulse_count < 11) // Xgimi Aura has 80 microsecond pulse length...
            {
                dlplink_pulse_count_detected = dlplink_pulse_count;
            }
            dlplink_pulse_count = 0;
        }
    }
    // ADCSRA |= (1 << ADIF) | (1 << ADSC); // Clear interrupt flag and start ADC conversions
}
