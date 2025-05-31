#ifndef DLPLINK_SENSOR_H
#define DLPLINK_SENSOR_H

#include <stdint.h>
#include <avr/io.h>

// ADC channel definition for the DLP-Link optical sensor (uses ADC6 input)
#define DLP_SENSOR_CHANNEL ADC6D
#define DLP_SENSOR_MIN_THRESHOLD_VALUE_TO_ACTIVATE 10 // IR LED was triggering shutters while testing

// IR ignore countdown (loops) after IR LED active
#define DLPLINK_SENSOR_IR_IGNORE_COUNT 10

// How long to ignore subsequent pulses after detecting a pulse
// Since the off interval prior to a pulse signal is is >500 us for A or >600 us for B
// we should ignore any pulses that follow within 25 cycles (25*13 us = 325 us) of another pulse.
#define DLPLINK_IGNORE_ADC_COUNTDOWN_VALUE 25

// Good for DLP Link Based on Specs 20 to 32 microseconds
// Xgimi Aura has 80 microsecond pulse length...
// Our ADC sample rate is 13 microseconds with prescaler 16 "100"

// Pulse count minumum hits
// The number of pulse counts hit on the ADC before a pulse is considered eligible as a DLPLink pulse.
// Our ADC sample rate is 13 microseconds with prescaler 16 "100"
#define DLPLINK_PULSE_COUNT_MIN 2 // DLP Link Based on Specs 20 to 32 microseconds
// #define DLPLINK_PULSE_COUNT_MIN 5 // Xgimi Aura 80 us pulse length

// Pulse count maximum hits
// The number of pulse counts hit on the ADC below which a pulse is considered eligible as a DLPLink pulse.
// Our ADC sample rate is 13 microseconds with prescaler 16 "100"
#define DLPLINK_PULSE_COUNT_MAX 6 // DLP Link Based on Specs 20 to 32 microseconds (the actual pulse width on my test bench seems to take up to 55 us for a pulse of 35 us)
// #define DLPLINK_PULSE_COUNT_MIN 10 // Xgimi Aura 80 us pulse length

extern uint32_t dlplink_sensor_block_signal_detection_delay;
extern uint8_t dlplink_sensor_min_threshold_value_to_activate;
extern uint8_t dlplink_sensor_detection_threshold_high;
extern uint8_t dlplink_sensor_detection_threshold_low;
extern uint8_t dlplink_sensor_enable_ignore_during_ir;

void dlplink_sensor_init(void);
void dlplink_sensor_stop(void);
void dlplink_sensor_check_readings(void);
void dlplink_sensor_adc_isr_handler(void);
void dlplink_sensor_print_stats(void);

#endif /* DLPLINK_SENSOR_H */
