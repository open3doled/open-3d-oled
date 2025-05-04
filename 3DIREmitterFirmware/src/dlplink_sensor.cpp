#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "dlplink_sensor.h"

// Global configuration variables (with default values; can be overridden elsewhere)
uint32_t dlplink_sensor_block_signal_detection_delay = 1000; // Blocking delay after a pulse (in µs)
uint8_t dlplink_sensor_min_threshold_value_to_activate = 10; // Minimum ADC value to activate detection
uint8_t dlplink_sensor_detection_threshold_high = 50;        // High threshold for pulse detection (ADC value)
uint8_t dlplink_sensor_detection_threshold_low = 40;         // Low threshold for pulse end (ADC value)
uint8_t dlplink_sensor_enable_ignore_during_ir = 1;          // Ignore sensor during IR transmission (1=enabled)

// External flags (provided by other modules)
extern volatile bool ir_led_token_active; // Flag indicating IR LED transmission is active
extern uint8_t opt_sensor_output_stats;   // Flag indicating whether +stats mode is enabled

// DLP-Link pulse timing constants (in microseconds)
#define DLP_SENSOR_MIN_PULSE_US 20
#define DLP_SENSOR_MAX_PULSE_US 32
#define DLP_SENSOR_PULSE_GRACE_US 20 // Grace margin for ADC ISR timing

// IR ignore countdown (loops) after IR LED active
#define DLP_SENSOR_IR_IGNORE_COUNT 10

// Internal state for pulse detection (static, persistent across interrupts)
static bool active = false;                   // Detection active after initial threshold exceeded
static bool in_pulse = false;                 // Currently in a pulse (between rise and fall)
static uint32_t last_pulse_start_time = 0;    // Timestamp of the previous pulse's start (for interval measurement)
static uint32_t current_pulse_start_time = 0; // Timestamp of the current pulse's start
static uint16_t prev_interval = 0;            // Last measured inter-pulse interval (for baseline refinement)
static uint32_t block_until_time = 0;         // Time until which new pulse detection is blocked (after a pulse)
static uint32_t ir_led_token_active_countdown = 0;

// Variables for communication with main loop (volatile because they are set in ISR and read in main)
static volatile uint32_t pulse_count = 0;         // Total pulses detected
static volatile uint16_t last_pulse_width_us = 0; // Last pulse duration in microseconds
static volatile uint16_t baseline_est = 0;        // Estimated frame interval (baseline period in µs)
static volatile int16_t last_jitter_us = 0;       // Last measured jitter (µs, positive=longer, negative=shorter)
static volatile uint8_t last_eye = EYE_LEFT;      // Last detected eye (0=Left,1=Right)
static volatile uint8_t trigger_eye = EYE_LEFT;   // Eye value for the pending trigger event
static volatile bool trigger_pending = false;     // Whether a trigger event is waiting to be processed in main

void dlplink_sensor_init(void)
{
    // Reset internal state
    active = false;
    in_pulse = false;
    last_pulse_start_time = 0;
    current_pulse_start_time = 0;
    baseline_est = 0;
    prev_interval = 0;
    block_until_time = 0;
    ir_led_token_active_countdown = 0;
    pulse_count = 0;
    trigger_pending = false;
    trigger_eye = EYE_LEFT;
    last_eye = EYE_LEFT;
    last_pulse_width_us = 0;
    last_jitter_us = 0;

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
                                                           // | (1 << ADATE)                                // Auto-trigger enable (free-run)
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
    // If an eye trigger event was set in the ISR, process it
    if (trigger_pending)
    {
        ir_signal_process_trigger(trigger_eye);
        trigger_pending = false;
    }
}

void dlplink_sensor_print_stats(void)
{
    // If +stats mode is enabled, print DLP-Link sensor statistics
    if (opt_sensor_output_stats)
    {
        Serial.print("+stats dlplink pulses:");
        Serial.print(pulse_count);
        Serial.print(" last_width:");
        Serial.print(last_pulse_width_us);
        Serial.print(" baseline_est:");
        Serial.print(baseline_est);
        Serial.print(" jitter:");
        Serial.print(last_jitter_us);
        Serial.print(" in_pulse:");
        Serial.print(in_pulse);
        Serial.print(" trigger_pending:");
        Serial.print(trigger_pending);
        Serial.print(" last_eye:");
        Serial.println((last_eye == EYE_LEFT ? 'L' : 'R'));
    }
}

void dlplink_sensor_adc_isr_handler(void)
{
    uint8_t value = ADCH; // 8-bit ADC sample
    uint32_t now = 0;
    bool now_set = false;

    bitToggle(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2);

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
            ADCSRA |= (1 << ADIF) | (1 << ADSC); // Clear interrupt flag and start ADC conversions
            return;
        }
    }
#endif

    // Activation threshold
    if (!active)
    {
        if (value > dlplink_sensor_min_threshold_value_to_activate)
        {
            active = true;
        }
        else
        {
            ADCSRA |= (1 << ADIF) | (1 << ADSC); // Clear interrupt flag and start ADC conversions
            return;
        }
    }

    // 1) Post-pulse blocking
    if (!in_pulse && block_until_time)
    {
        if (!now_set)
        {
            now = micros();
            now_set = true;
        }
        if (now < block_until_time)
        {
            ADCSRA |= (1 << ADIF) | (1 << ADSC); // Clear interrupt flag and start ADC conversions
            return;
        }
        block_until_time = 0;
    }

    if (!in_pulse)
    {
        // Detect rising edge (pulse start)
        if (value > dlplink_sensor_detection_threshold_high)
        {
            if (!now_set)
            {
                now = micros();
                now_set = true;
            }
            in_pulse = true;
            current_pulse_start_time = now;
        }
    }
    else
    {
        // Detect falling edge (pulse end)
        if (value < dlplink_sensor_detection_threshold_low)
        {
            if (!now_set)
            {
                now = micros();
                now_set = true;
            }
            uint32_t end_time = now;
            uint32_t start_time = current_pulse_start_time;
            uint16_t pulse_width = (uint16_t)(end_time - start_time);

            // 1) Validate pulse width
            uint16_t min_pw = DLP_SENSOR_MIN_PULSE_US - DLP_SENSOR_PULSE_GRACE_US;
            uint16_t max_pw = DLP_SENSOR_MAX_PULSE_US + DLP_SENSOR_PULSE_GRACE_US;
            if (pulse_width < min_pw || pulse_width > max_pw)
            {
                in_pulse = false;
                ADCSRA |= (1 << ADIF) | (1 << ADSC); // Clear interrupt flag and start ADC conversions
                return;
            }

            // Update stats
            pulse_count++;
            last_pulse_width_us = pulse_width;

            // Compute interval since last pulse
            uint32_t interval = start_time - last_pulse_start_time;
            int32_t diff = (int32_t)interval - (int32_t)baseline_est;

            // 2x diff should match the values in the datasheet page 38 https://www.ti.com/lit/ds/symlink/dlpc3434.pdf
            // Specifically 15836 / [diff] = Refresh Hz
            // diff ~= 15836 / Refresh Hz
            // diff ~= 15836 * Refresh Period
            // Refresh Period = [diff] / 15836
            // 15836 = 0x3DDC

            // 2) Eye classification with jitter window
            uint8_t eye;
            if (diff > 30)
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
                if (eye != last_eye)
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
            block_until_time = start_time + dlplink_sensor_block_signal_detection_delay;
            last_pulse_start_time = start_time;
            in_pulse = false;
        }
    }
    ADCSRA |= (1 << ADIF) | (1 << ADSC); // Clear interrupt flag and start ADC conversions
}
