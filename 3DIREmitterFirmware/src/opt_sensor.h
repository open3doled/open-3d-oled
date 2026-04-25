/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0.
 * To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */
#ifndef _OPT_SENSOR_SENSOR_H_
#define _OPT_SENSOR_SENSOR_H_

#define OPT_SENSOR_CHANNELS 2
#define OPT_SENSOR_MIN_THRESHOLD_VALUE_TO_ACTIVATE 0
#define OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY 25
#define OPT_TRIGGER_COUNT_THRESHOLD 2
#define OPT_FRAMETIME_COUNT_PERIOD_2PN 7
#define OPT_FRAMETIME_COUNT_PERIOD (1 << OPT_FRAMETIME_COUNT_PERIOD_2PN)

/*
 * In BLUR_REDUCTION_FIRMWARE the old high/low stereo sensor semantics are
 * replaced with a negative-going OLED refresh-dip detector.
 *
 * Existing serial-config parameters are intentionally reused:
 *   opt_sensor_block_signal_detection_delay = global refresh lockout, us
 *   opt_sensor_detection_threshold_high     = baseline-to-sample dip threshold, ADC counts
 *   opt_sensor_detection_threshold_low      = per-sample falling-step threshold, ADC counts
 *   opt_sensor_min_threshold_value_to_activate = optional minimum baseline; 0 disables
 *   opt_sensor_filter_mode                  = keeps the old simple ADC deglitch filter
 */
extern uint32_t opt_sensor_block_signal_detection_delay;
extern uint8_t opt_sensor_ignore_all_duplicates;
extern uint8_t opt_sensor_filter_mode;
extern uint8_t opt_sensor_min_threshold_value_to_activate;
extern uint8_t opt_sensor_detection_threshold_high;
extern uint8_t opt_sensor_detection_threshold_low;
extern uint8_t opt_sensor_enable_ignore_during_ir;
extern uint8_t opt_sensor_enable_duplicate_realtime_reporting;
extern uint8_t opt_sensor_output_stats;
extern uint8_t opt_sensor_enable_frequency_analysis_based_duplicate_frame_detection;

#ifdef OPT_SENSOR_ENABLE_STREAM_READINGS_TO_SERIAL
extern uint8_t opt_sensor_enable_stream_readings_to_serial;
#endif

#ifdef BLUR_REDUCTION_FIRMWARE
extern volatile uint16_t opt_sensor_blur_detected_counter;
extern volatile uint16_t opt_sensor_blur_rejected_counter;
extern volatile uint16_t opt_sensor_blur_forwarded_dip_counter;
extern volatile uint16_t opt_sensor_blur_phase_rejected_counter;
extern volatile uint8_t opt_sensor_blur_last_detection_channel;
extern volatile uint8_t opt_sensor_blur_pending_detection;
extern volatile uint8_t opt_sensor_blur_panel_phase;
extern volatile uint8_t opt_sensor_blur_selected_phase;
extern volatile uint8_t opt_sensor_blur_last_forwarded_phase;
extern uint8_t opt_sensor_blur_required_falling_samples;
extern uint8_t opt_sensor_blur_baseline_shift;
extern uint8_t opt_sensor_blur_brightness_change_threshold;
extern uint8_t opt_sensor_blur_phase_score_margin;
void opt_sensor_blur_toggle_phase_override(void);
#endif

void opt_sensor_init(void);
void opt_sensor_stop(void);

#ifdef OPT_SENSOR_ENABLE_STATS
void opt_sensor_print_stats(void);
bool opt_sensor_finish_print_stats(void);
#endif

void opt_sensor_update_thresholds(void);
void opt_sensor_settings_changed(void);
void opt_sensor_check_readings(void);
void opt_sensor_clear_stats(void);
void opt_sensor_adc_isr_handler(void);

#endif /* _OPT_SENSOR_SENSOR_H_ */
