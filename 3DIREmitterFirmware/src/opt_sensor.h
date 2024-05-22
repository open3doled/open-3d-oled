/*
* Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
*/

#ifndef _OPT_SENSOR_SENSOR_H_
#define _OPT_SENSOR_SENSOR_H_

#define OPT_SENSOR_CHANNELS 2
#define OPT_SENSOR_MIN_THRESHOLD_VALUE_TO_ACTIVATE 10 // IR LED was triggering shutters while testing
//#define OPT_SENSOR_MIN_THRESHOLD_VALUE_TO_ACTIVATE 15
#define OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY 25

extern uint32_t opt_sensor_block_signal_detection_delay;
extern uint8_t opt_sensor_block_n_subsequent_duplicates;
extern uint8_t opt_sensor_ignore_all_duplicates;
extern uint8_t opt_sensor_filter_mode;
extern uint8_t opt_sensor_min_threshold_value_to_activate;
extern uint8_t opt_sensor_detection_threshold;
extern uint8_t opt_sensor_detection_threshold_repeated_high;
extern uint8_t opt_sensor_detection_threshold_repeated_low;
extern uint8_t opt_sensor_enable_ignore_during_ir;
extern uint8_t opt_sensor_enable_duplicate_realtime_reporting;
extern uint8_t opt_sensor_output_stats;
extern uint8_t opt_sensor_enable_frequency_analysis_based_duplicate_frame_detection;
#ifdef OPT_SENSOR_ENABLE_STREAM_READINGS_TO_SERIAL
extern uint8_t opt_sensor_enable_stream_readings_to_serial;
#endif

void opt_sensor_Init(void);
#ifdef OPT_SENSOR_ENABLE_STATS
void opt_sensor_PrintStats(void);
bool opt_sensor_FinishPrintStats(void);
#endif
void opt_sensor_UpdateThresholds(void);
void opt_sensor_CheckReadings(void);
void opt_sensor_ClearStats(void);


#endif /* _OPT_SENSOR_SENSOR_H_ */