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
extern volatile uint8_t ir_led_token_active; // Flag indicating IR LED transmission is active
extern uint8_t opt_sensor_output_stats;      // Flag indicating whether +stats mode is enabled

// Internal state for pulse detection (static, persistent across interrupts)
static bool active = false;                   // Detection active after initial threshold exceeded
static bool in_pulse = false;                 // Currently in a pulse (between rise and fall)
static uint32_t last_pulse_start_time = 0;    // Timestamp of the previous pulse's start (for interval measurement)
static uint32_t current_pulse_start_time = 0; // Timestamp of the current pulse's start
static uint16_t baseline_est = 0;             // Estimated frame interval (baseline period in µs)
static uint16_t prev_interval = 0;            // Last measured inter-pulse interval (for baseline refinement)
static uint32_t block_until_time = 0;         // Time until which new pulse detection is blocked (after a pulse)

// Variables for communication with main loop (volatile because they are set in ISR and read in main)
static volatile uint32_t pulse_count = 0;         // Total pulses detected
static volatile uint16_t last_pulse_width_us = 0; // Last pulse duration in microseconds
static volatile int16_t last_jitter_us = 0;       // Last measured jitter (µs, positive=longer interval, negative=shorter)
static volatile uint8_t last_eye = 0;             // Last detected eye (0 = Left, 1 = Right)
static volatile uint8_t trigger_eye = 0;          // Eye value for the pending trigger event
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
    pulse_count = 0;
    trigger_pending = false;
    trigger_eye = EYE_LEFT;
    last_eye = EYE_LEFT;
    last_pulse_width_us = 0;
    last_jitter_us = 0;

    // Configure ADC for free-running mode on ADC6 (DLP-Link sensor channel)
    ADCSRA &= ~(1 << ADEN);                 // Disable ADC to configure
    ADMUX = (1 << REFS0)                    // AVcc as reference voltage
            | (1 << ADLAR)                  // Left-adjust result (8-bit reading from ADCH)
            | 6;                            // Select ADC6 channel
    ADCSRB = 0x00;                          // Free running mode, no auto-trigger source (ADTS=000)
    DIDR0 |= (1 << DLP_SENSOR_CHANNEL);     // Disable digital input on ADC6 pin
    ADCSRA = (1 << ADEN)                    // Enable ADC
             | (1 << ADATE)                 // Auto-trigger enable (free-run)
             | (1 << ADIE)                  // Enable ADC interrupt
             | (1 << ADPS1) | (1 << ADPS0); // Prescaler = 8 (ADC clock ~2 MHz for high-speed sampling)
    ADCSRA |= (1 << ADSC);                  // Start ADC conversions
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
        ir_signal_process_trigger(trigger_eye); // Invoke the IR trigger processing with the identified eye
        trigger_pending = false;
    }

    // If +stats mode is enabled, print DLP-Link sensor statistics
    if (opt_sensor_output_stats)
    {
#ifdef __AVR__
        printf_P(PSTR("DLP-Link: pulses=%lu, last_width=%u us, jitter=%+d us, last_eye=%c\n"),
                 pulse_count, last_pulse_width_us, last_jitter_us,
                 (last_eye == EYE_LEFT ? 'L' : 'R'));
#else
        printf("DLP-Link: pulses=%lu, last_width=%u us, jitter=%+d us, last_eye=%c\n",
               pulse_count, last_pulse_width_us, last_jitter_us,
               (last_eye == EYE_LEFT ? 'L' : 'R'));
#endif
    }
}

void dlplink_sensor_adc_isr_handler(void)
{
    // Read the latest ADC sample (8-bit value from ADCH since ADLAR=1)
    uint8_t value = ADCH;

    // Optionally ignore sensor input during IR LED transmission to avoid interference
    if (dlplink_sensor_enable_ignore_during_ir && ir_led_token_active)
    {
        return;
    }

    // Activation check: ensure ambient light exceeds minimum threshold before detecting pulses
    if (!active)
    {
        if (value > dlplink_sensor_min_threshold_value_to_activate)
        {
            active = true; // Sensor is now active and ready to detect pulses
        }
        else
        {
            return; // Not yet activated (ambient signal too low), ignore readings
        }
    }

    // If not currently in a pulse, enforce the post-pulse ignore delay (blocking interval)
    if (!in_pulse && block_until_time)
    {
        uint32_t now = micros();
        if (now < block_until_time)
        {
            // Still within blocking period after last pulse, ignore new pulse starts
            return;
        }
        // Blocking interval elapsed, allow detection of new pulses
        block_until_time = 0;
    }

    if (!in_pulse)
    {
        // Idle state: check for a pulse start (rising above high threshold)
        if (value > dlplink_sensor_detection_threshold_high)
        {
            // Rising edge detected – begin a new pulse
            in_pulse = true;
            current_pulse_start_time = micros(); // record start time of this pulse
        }
        // Otherwise, remain in idle state
    }
    else
    {
        // In-pulse state: check for pulse end (falling below low threshold)
        if (value < dlplink_sensor_detection_threshold_low)
        {
            // Falling edge detected – pulse ended
            uint32_t pulse_end_time = micros();
            uint32_t start_time = current_pulse_start_time;
            uint16_t pulse_width = (uint16_t)(pulse_end_time - start_time);

            // Update pulse statistics
            pulse_count++;
            last_pulse_width_us = pulse_width;

            if (pulse_count == 1)
            {
                // First pulse: no previous pulse to compare, so eye cannot be determined
                last_jitter_us = 0;
                trigger_pending = false; // Do not trigger on the very first pulse
            }
            else if (pulse_count == 2)
            {
                // Second pulse: calculate first inter-pulse interval and estimate baseline
                uint32_t interval = start_time - last_pulse_start_time;
                // Estimate frame period (baseline) based on the first interval
                if (interval > 14000)
                {
                    baseline_est = 16667; // assume ~60 Hz frame rate
                }
                else if (interval > 7500)
                {
                    baseline_est = 8333; // assume ~120 Hz frame rate
                }
                else
                {
                    baseline_est = 6944; // assume ~144 Hz frame rate
                }
                prev_interval = (uint16_t)interval;
                // Determine eye: a longer interval means last frame was left-eye, hence current is right-eye
                uint8_t eye = (interval > baseline_est ? EYE_RIGHT : EYE_LEFT);
                last_eye = eye;
                trigger_eye = eye;
                trigger_pending = true;
                // Record jitter (interval difference from baseline estimate)
                last_jitter_us = (int16_t)((int32_t)interval - (int32_t)baseline_est);
            }
            else
            {
                // Third or subsequent pulse: refine baseline and determine eye normally
                uint32_t interval = start_time - last_pulse_start_time;
                // Refine the baseline estimate as the average of the last two intervals
                baseline_est = (uint16_t)(((uint32_t)prev_interval + interval) / 2);
                prev_interval = (uint16_t)interval;
                // Determine eye from interval vs baseline: longer = Right, shorter = Left
                uint8_t eye = (interval > baseline_est ? EYE_RIGHT : EYE_LEFT);
                last_eye = eye;
                trigger_eye = eye;
                trigger_pending = true;
                // Calculate jitter relative to current baseline
                last_jitter_us = (int16_t)((int32_t)interval - (int32_t)baseline_est);
            }

            // Update the reference start time for the next interval measurement
            last_pulse_start_time = start_time;
            // Block new pulse detection for the configured delay to avoid immediate re-trigger
            block_until_time = start_time + dlplink_sensor_block_signal_detection_delay;
            // Reset state to idle, ready for the next pulse
            in_pulse = false;
        }
    }
}
