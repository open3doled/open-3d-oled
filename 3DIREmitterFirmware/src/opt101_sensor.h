/*
* Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
*/

#ifndef _OPT101_SENSOR_H_
#define _OPT101_SENSOR_H_

#define OPT101_CHANNELS 2
#define OPT101_MIN_THRESHOLD_VALUE_TO_ACTIVATE 10 // IR LED was triggering shutters while testing
//#define OPT101_MIN_THRESHOLD_VALUE_TO_ACTIVATE 15
#define OPT101_STATS_SERIAL_OUTPUT_FREQUENCY 25

extern uint32_t opt101_block_signal_detection_delay;
extern uint8_t opt101_block_n_subsequent_duplicates;
extern uint8_t opt101_ignore_all_duplicates;
extern uint8_t opt101_min_threshold_value_to_activate;
extern uint8_t opt101_detection_threshold;
extern uint8_t opt101_detection_threshold_repeated_high;
extern uint8_t opt101_detection_threshold_repeated_low;
extern uint8_t opt101_enable_ignore_during_ir;
extern uint8_t opt101_enable_duplicate_realtime_reporting;
extern uint8_t opt101_output_stats;
extern uint8_t opt101_enable_frequency_analysis_based_duplicate_frame_detection;
#ifdef OPT101_ENABLE_STREAM_READINGS_TO_SERIAL
extern uint8_t opt101_enable_stream_readings_to_serial;
#endif

void opt101_sensor_Init(void);
#ifdef OPT101_ENABLE_STATS
void opt101_sensor_PrintStats(void);
bool opt101_sensor_FinishPrintStats(void);
#endif
void opt101_sensor_UpdateThresholds(void);
void opt101_sensor_CheckReadings(void);
void opt101_sensor_ClearStats(void);


#endif /* _OPT101_SENSOR_H_ */