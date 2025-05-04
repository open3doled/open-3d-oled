#ifndef DLPLINK_SENSOR_H
#define DLPLINK_SENSOR_H

#include <stdint.h>
#include <avr/io.h>

// ADC channel definition for the DLP-Link optical sensor (uses ADC6 input)
#define DLP_SENSOR_CHANNEL ADC6D

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
