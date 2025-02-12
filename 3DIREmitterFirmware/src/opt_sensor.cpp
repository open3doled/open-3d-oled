/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "opt_sensor.h"

#define bitclr(reg, bit) (reg &= ~(1 << bit)) // Clear register bit.
#define bittst(reg, bit) (reg & (1 << bit))   // Test register bit.
#define mult_by_threshold(high, low, threshold) (((uint16_t)threshold * (uint16_t)high + (uint16_t)(255 - threshold) * (uint16_t)low) >> 8)

#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
volatile uint8_t ir_led_token_active_countdown = 0;
#endif

#ifdef OPT_SENSOR_ENABLE_STATS
uint32_t opt_sensor_stats_count = 0;
#endif

uint32_t opt_sensor_current_time;
#ifdef OPT_SENSOR_ENABLE_STREAM_READINGS_TO_SERIAL
uint8_t opt_sensor_enable_stream_readings_to_serial = 0;
#endif
uint8_t opt_sensor_enable_frequency_analysis_based_duplicate_frame_detection = 0;
uint8_t opt_sensor_enable_ignore_during_ir = 0;
uint8_t opt_sensor_enable_duplicate_realtime_reporting = 0;
uint8_t opt_sensor_output_stats = 0;
uint8_t opt_sensor_detection_threshold_high = 128;
uint8_t opt_sensor_detection_threshold_low = 32;
uint32_t opt_sensor_block_signal_detection_delay = OPT_SENSOR_BLOCK_SIGNAL_DETECTION_DELAY;
uint8_t opt_sensor_ignore_all_duplicates = 0;
uint8_t opt_sensor_filter_mode = 0;
uint8_t opt_sensor_min_threshold_value_to_activate = OPT_SENSOR_MIN_THRESHOLD_VALUE_TO_ACTIVATE;
uint32_t opt_sensor_block_signal_detection_until = 0;
uint32_t opt_sensor_disable_debug_detection_flag_after = 0;
uint8_t opt_sensor_detected_signal_start_eye = 0;
bool opt_sensor_detected_signal_start_eye_set = false;
bool opt_sensor_initiated_sending_ir_signal = false;
volatile uint8_t opt_sensor_channel = 0;
bool opt_sensor_readings_active = false;
bool opt_sensor_reading_triggered[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_reading_triggered_count[OPT_SENSOR_CHANNELS];
bool opt_sensor_ignore_duplicate[OPT_SENSOR_CHANNELS];
bool opt_sensor_duplicate_frame[OPT_SENSOR_CHANNELS];
uint16_t opt_sensor_duplicate_frames_in_a_row_counter = 0;
uint8_t other_channel = 0;
uint8_t opt_sensor_readings_last[OPT_SENSOR_CHANNELS];
#ifdef OPT_SENSOR_FILTER_ADC_SIGNAL
uint8_t opt_sensor_readings_realtime_filter[OPT_SENSOR_CHANNELS];
#endif

uint16_t opt_sensor_reading_counter = 0;
uint16_t opt_sensor_duplicate_frames_counter = 0;
uint16_t opt_sensor_premature_frames_counter = 0;

volatile uint8_t opt_sensor_readings[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_readings_high[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_readings_low[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_readings_threshold_high[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_readings_threshold_low[OPT_SENSOR_CHANNELS];

uint16_t opt_sensor_ss_reading_counter = 0;
uint16_t opt_sensor_ss_duplicate_frames_counter = 0;
uint16_t opt_sensor_ss_premature_frames_counter = 0;

uint16_t opt_sensor_ss_channel_frequency_detection_counter[OPT_SENSOR_CHANNELS];
volatile uint8_t opt_sensor_ss_readings[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_ss_readings_high[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_ss_readings_low[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_ss_readings_threshold_high[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_ss_readings_threshold_low[OPT_SENSOR_CHANNELS];

/*
    7,  // A0               PF7                 ADC7 // right eye
    6,  // A1               PF6                 ADC6 // left eye
    5,  // A2               PF5                 ADC5
    4,  // A3               PF4                 ADC4
    1,  // A4               PF1                 ADC1
    0,  // A5               PF0                 ADC0
*/
// const uint8_t admux[OPT_SENSOR_CHANNELS] = {ADC7D, ADC6D, ADC5D, ADC4D}; // ADC MUX channels.
const uint8_t admux[OPT_SENSOR_CHANNELS] = {ADC7D, ADC6D}; // ADC MUX channels. (right eye, left eye)

void opt_sensor_init(void)
{
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    ir_led_token_active_countdown = 0;
#endif
#ifdef OPT_SENSOR_ENABLE_STATS
    opt_sensor_stats_count = 0;
#endif
#ifdef OPT_SENSOR_ENABLE_STREAM_READINGS_TO_SERIAL
    opt_sensor_enable_stream_readings_to_serial = 0;
#endif
    opt_sensor_enable_frequency_analysis_based_duplicate_frame_detection = 0;
    opt_sensor_enable_duplicate_realtime_reporting = 0;
    opt_sensor_output_stats = 0;
    opt_sensor_detection_threshold_high = 128;
    opt_sensor_detection_threshold_low = 32;
    opt_sensor_block_signal_detection_delay = OPT_SENSOR_BLOCK_SIGNAL_DETECTION_DELAY;
    opt_sensor_ignore_all_duplicates = 0;
    opt_sensor_filter_mode = 0;
    opt_sensor_min_threshold_value_to_activate = OPT_SENSOR_MIN_THRESHOLD_VALUE_TO_ACTIVATE;
    opt_sensor_block_signal_detection_until = 0;
    opt_sensor_disable_debug_detection_flag_after = 0;
    opt_sensor_detected_signal_start_eye = 0;
    opt_sensor_detected_signal_start_eye_set = false;
    opt_sensor_initiated_sending_ir_signal = false;
    opt_sensor_channel = 0;
    opt_sensor_readings_active = false;
    memset((void *)opt_sensor_reading_triggered, 0, sizeof(opt_sensor_reading_triggered));
    memset((void *)opt_sensor_reading_triggered_count, 0, sizeof(opt_sensor_reading_triggered_count));
    memset((void *)opt_sensor_ignore_duplicate, 0, sizeof(opt_sensor_ignore_duplicate));
    memset((void *)opt_sensor_duplicate_frame, 0, sizeof(opt_sensor_duplicate_frame));
    opt_sensor_duplicate_frames_in_a_row_counter = 0;
    other_channel = 0;

    opt_sensor_reading_counter = 0;
    opt_sensor_duplicate_frames_counter = 0;
    opt_sensor_premature_frames_counter = 0;

    memset((void *)opt_sensor_readings_last, 0, sizeof(opt_sensor_readings_last));
#ifdef OPT_SENSOR_FILTER_ADC_SIGNAL
    memset((void *)opt_sensor_readings_realtime_filter, 0, sizeof(opt_sensor_readings_realtime_filter));
#endif
    memset((void *)opt_sensor_readings, 0, sizeof(opt_sensor_readings));
    memset((void *)opt_sensor_readings_high, 0, sizeof(opt_sensor_readings_high));
    memset((void *)opt_sensor_readings_low, 255, sizeof(opt_sensor_readings_low));
    memset((void *)opt_sensor_readings_threshold_high, 255, sizeof(opt_sensor_readings_threshold_high));
    memset((void *)opt_sensor_readings_threshold_low, 0, sizeof(opt_sensor_readings_threshold_low));

    ADMUX = _BV(REFS0)                            // ref = AVCC
            | _BV(ADLAR)                          // left adjust result
            | (admux[opt_sensor_channel] & 0x07); // input channel
    ADCSRB = 0 | _BV(ADHSM)                       // Writing this ADHSM bit to one enables the ADC High Speed mode. This mode enables higher conversion rate at the expense of higher power consumption.
        ;                                         // free running mode (when ADATE set below)
    ADCSRA = _BV(ADEN)                            // enable
             | _BV(ADSC)                          // start conversion
                                                  //           | _BV(ADATE)  // auto trigger enable
             | _BV(ADIF)                          // clear interrupt flag
             | _BV(ADIE)                          // interrupt enable,
             | 4;                                 // prescaler (was 100) 13*2^n/16000000 = 000-001 2, 010 4, 011 8, 100 16, 101 32, 110 64 111 128
                                                  //
                                                  // (100 16 is a good tradeoff gives 36us delay and 70us jitter (calculated 13us conv time) but values seem noisy) (110 64 has 136us delay and 110us jitter (52us conv time) values seem non-noisy)
                                                  // atmel-7766-8-bit-avr-atmega16u4-32u4_datasheet.pdf
                                                  // By default, the successive approximation circuitry requires an input clock frequency between 50kHz and
                                                  // 200kHz to get maximum resolution. If a lower resolution than 10 bits is needed, the input clock frequency to the
                                                  // ADC can be higher than 200kHz to get a higher sample rate. Alternatively, setting the ADHSM bit in ADCSRB
                                                  // allows an increased ADC clock frequency at the expense of higher power consumption.
                                                  // A normal conversion takes 13 ADC clock cycles. The first conversion after the ADC is switched on (ADEN in
                                                  // ADCSRA is set) takes 25 ADC clock cycles in order to initialize the analog circuitry.
}

void opt_sensor_stop(void)
{
    ADCSRA &= ~(_BV(ADEN) | _BV(ADIE));
}

#ifdef OPT_SENSOR_ENABLE_STATS
void opt_sensor_print_stats(void)
{
    switch (opt_sensor_stats_count)
    {
    case 0:

        opt_sensor_ss_reading_counter = opt_sensor_reading_counter;
        opt_sensor_ss_duplicate_frames_counter = opt_sensor_duplicate_frames_counter;
        opt_sensor_ss_premature_frames_counter = opt_sensor_premature_frames_counter;
        for (int ch = 0; ch < OPT_SENSOR_CHANNELS; ch++)
        {
            opt_sensor_ss_readings[ch] = opt_sensor_readings[ch];
            opt_sensor_ss_readings_high[ch] = opt_sensor_readings_high[ch];
            opt_sensor_ss_readings_low[ch] = opt_sensor_readings_low[ch];
            opt_sensor_ss_readings_threshold_high[ch] = opt_sensor_readings_threshold_high[ch];
            opt_sensor_ss_readings_threshold_low[ch] = opt_sensor_readings_threshold_low[ch];
        }
        opt_sensor_update_thresholds();
        opt_sensor_clear_stats();
        break;
    case 1 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print("+stats general reading_counter:");
        Serial.print(opt_sensor_ss_reading_counter);
        break;
    case 2 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" duplicate_frames:");
        Serial.print(opt_sensor_ss_duplicate_frames_counter);
        break;
    case 3 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" premature_frames:");
        Serial.print(opt_sensor_ss_premature_frames_counter);
        Serial.println();
        opt_sensor_stats_count += OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY;
        break;
    case 5 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print("+stats sensor channel:right");
        break;
    case 6 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" detections:");
        Serial.print(opt_sensor_ss_channel_frequency_detection_counter[0]);
        break;
    case 7 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" reading:");
        Serial.print(opt_sensor_ss_readings[0]);
        break;
    case 8 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" high:");
        Serial.print(opt_sensor_ss_readings_high[0]);
        break;
    case 9 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" low:");
        Serial.print(opt_sensor_ss_readings_low[0]);
        break;
    case 10 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" thr_h:");
        Serial.print(opt_sensor_ss_readings_threshold_high[0]);
        break;
    case 11 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" thr_l:");
        Serial.print(opt_sensor_ss_readings_threshold_low[0]);
        Serial.println();
        opt_sensor_stats_count += 1 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY;
        break;
    case 13 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print("+stats sensor channel:left");
        break;
    case 14 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" detections:");
        Serial.print(opt_sensor_ss_channel_frequency_detection_counter[1]);
        break;
    case 15 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" reading:");
        Serial.print(opt_sensor_ss_readings[1]);
        break;
    case 16 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" high:");
        Serial.print(opt_sensor_ss_readings_high[1]);
        break;
    case 17 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" low:");
        Serial.print(opt_sensor_ss_readings_low[1]);
        break;
    case 18 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" thr_h:");
        Serial.print(opt_sensor_ss_readings_threshold_high[1]);
        break;
    case 19 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" thr_l:");
        Serial.print(opt_sensor_ss_readings_threshold_low[1]);
        Serial.println();
        opt_sensor_stats_count += 1 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY;
        break;
    }
    opt_sensor_stats_count++;
}

bool opt_sensor_finish_print_stats(void)
{
    bool done = (opt_sensor_stats_count > (4 + 8 * 2) * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY);
    if (done)
    {
        opt_sensor_stats_count = 0;
    }
    return done;
}
#endif

void opt_sensor_update_thresholds(void)
{
    opt_sensor_readings_active = true;
    for (uint8_t c = 0; c < OPT_SENSOR_CHANNELS; c++)
    {
        if (opt_sensor_readings_high[c] < opt_sensor_min_threshold_value_to_activate)
        {
            opt_sensor_readings_active = false;
        }
        opt_sensor_readings_threshold_high[c] = mult_by_threshold(opt_sensor_readings_high[c], opt_sensor_readings_low[c], opt_sensor_detection_threshold_high);
        opt_sensor_readings_threshold_low[c] = mult_by_threshold(opt_sensor_readings_high[c], opt_sensor_readings_low[c], opt_sensor_detection_threshold_low);
    }
}

void opt_sensor_settings_changed(void)
{
    if (opt_sensor_ignore_all_duplicates)
    {
        opt_sensor_detected_signal_start_eye_set = false;
    }
}

void opt_sensor_check_readings(void)
{
    uint8_t checked_readings[2];
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    if (opt_sensor_enable_ignore_during_ir == 0 || (!ir_led_token_active && !ir_led_token_active_countdown))
    {
#endif
        for (uint8_t c = 0; c < OPT_SENSOR_CHANNELS; c++)
        {
            checked_readings[c] = opt_sensor_readings[c];
        }
        opt_sensor_current_time = 0;
        if (opt_sensor_block_signal_detection_until == 0)
        {
            for (uint8_t c = 0; c < OPT_SENSOR_CHANNELS; c++)
            {
                other_channel = (c == 1 ? 0 : 1);
                if (opt_sensor_readings_active)
                {
                    if (checked_readings[c] >= opt_sensor_readings_threshold_high[c] &&
                        checked_readings[other_channel] <= opt_sensor_readings_threshold_low[other_channel])
                    {
                        opt_sensor_reading_triggered_count[c]++;
                        opt_sensor_reading_triggered_count[other_channel] = 0;
                    }
                    else if (checked_readings[c] < opt_sensor_readings_threshold_high[c])
                    {
                        opt_sensor_reading_triggered_count[c] = 0;
                        opt_sensor_reading_triggered[c] = false;
                    }
                    else
                    {
                        opt_sensor_reading_triggered_count[c] = 0;
                    }
                }
                if ((opt_sensor_reading_triggered_count[c] > OPT_TRIGGER_COUNT_THRESHOLD || (opt_sensor_enable_stream_readings_to_serial && opt_sensor_reading_triggered_count[c] > 1))) // when we are running in sensor log mode we skip the check as it already takes 140 us per cycle, there is still the risk of miss triggering, but operating on a pwm backlight display sensor log mode already breaks the algorithm entirely (this at least helps it kind of continue working)
                {
                    if (opt_sensor_reading_triggered[c] == false) // we only count it the first time we hit it....)
                    {
                        opt_sensor_reading_triggered[c] = true;
                        if (opt_sensor_current_time == 0)
                        {
                            opt_sensor_current_time = micros();
                        }
                        opt_sensor_ignore_duplicate[c] = false;
                        opt_sensor_duplicate_frame[c] = (opt_sensor_detected_signal_start_eye == c && opt_sensor_detected_signal_start_eye_set);
                        if (opt_sensor_duplicate_frame[c])
                        {
                            opt_sensor_duplicate_frames_counter++;
                            opt_sensor_duplicate_frames_in_a_row_counter++;
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
                            if (opt_sensor_duplicate_frame[c])
                            {
                                bitSet(PORT_DEBUG_DUPLICATE_FRAME_D16, DEBUG_DUPLICATE_FRAME_D16);
                            }
#endif
                            if (opt_sensor_enable_duplicate_realtime_reporting && ((opt_sensor_duplicate_frames_in_a_row_counter % 2) == 1) &&
                                (!opt_sensor_ignore_all_duplicates || opt_sensor_duplicate_frames_in_a_row_counter == 1)) // if ignore all duplicates is on then we only report the first duplicate because it will keep detecting duplicates multiple times per frame
                            {
                                Serial.println("+d");
                            }
                            if (opt_sensor_ignore_all_duplicates)
                            {
                                opt_sensor_ignore_duplicate[c] = true;
                            }
                        }
                        else
                        {
                            opt_sensor_duplicate_frames_in_a_row_counter = 0;
                        }
                        if (opt_sensor_ignore_duplicate[c])
                        {
                            opt_sensor_block_signal_detection_until = opt_sensor_current_time + opt_sensor_block_signal_detection_delay;
                        }
                        else
                        {
                            // when running in ignore all duplicates which is for PWM and LCD we ignore the first detection and don't set the block signal detection delay to ensure the signal syncs properly as there is no black interval like for OLED and BFI
                            bool ignore_update = opt_sensor_ignore_all_duplicates && (!opt_sensor_detected_signal_start_eye_set || opt_sensor_detected_signal_start_eye == c);
                            opt_sensor_detected_signal_start_eye = c;
                            opt_sensor_detected_signal_start_eye_set = true;
                            if (!ignore_update)
                            {
                                opt_sensor_block_signal_detection_until = opt_sensor_current_time + opt_sensor_block_signal_detection_delay;
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
                                opt_sensor_disable_debug_detection_flag_after = opt_sensor_current_time + (opt_sensor_block_signal_detection_delay >> 2); // half of the block signal detection delay in length
                                if (c)
                                {
                                    bitSet(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
                                }
                                else
                                {
                                    bitSet(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
                                }
#endif
                                ir_signal_process_trigger(opt_sensor_detected_signal_start_eye);
                                opt_sensor_initiated_sending_ir_signal = true;
                            }
                            break;
                        }
                    }
                }
            }
        }
        else
        {
            if (opt_sensor_current_time == 0)
            {
                opt_sensor_current_time = micros();
            }
            if (opt_sensor_current_time >= opt_sensor_block_signal_detection_until && opt_sensor_current_time - opt_sensor_block_signal_detection_until < 60000000)
            {
                opt_sensor_block_signal_detection_until = 0;
            }
        }

#ifdef OPT_SENSOR_ENABLE_STREAM_READINGS_TO_SERIAL
        if (opt_sensor_enable_stream_readings_to_serial)
        {
            uint8_t buffer[3 + 10 + 2] = {'+', 'o', ' ', 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, '\r', '\n'};
            if (opt_sensor_current_time == 0)
            {
                opt_sensor_current_time = micros();
            }
            /*
            Serial.print("+o ");
            Serial.print(opt_sensor_current_time);
            Serial.print(",");
            Serial.print(checked_readings[0]);
            Serial.print(",");
            Serial.println(checked_readings[1]);
            */

            buffer[3] = (0x80 |
                         (opt_sensor_duplicate_frame[1] == true ? 0x20 : 0x00) |
                         (opt_sensor_ignore_duplicate[1] == true ? 0x10 : 0x00) |
                         (opt_sensor_reading_triggered[1] == true ? 0x08 : 0x00) |
                         (opt_sensor_duplicate_frame[0] == true ? 0x04 : 0x00) |
                         (opt_sensor_ignore_duplicate[0] == true ? 0x02 : 0x00) |
                         (opt_sensor_reading_triggered[0] == true ? 0x01 : 0x00));
            buffer[4] = (0x80 |
                         (opt_sensor_readings_active == true ? 0x08 : 0x00) |
                         (opt_sensor_detected_signal_start_eye == 1 ? 0x04 : 0x00) |
                         (opt_sensor_initiated_sending_ir_signal ? 0x02 : 0x00) |
                         (opt_sensor_block_signal_detection_until > 0 ? 0x01 : 0x00));
            buffer[5] = 0x80 | ((opt_sensor_duplicate_frames_in_a_row_counter) & 0x7f);
            buffer[6] = 0x80 | ((checked_readings[0] >> 2) & 0x3f);
            buffer[7] = 0x80 | ((checked_readings[1] >> 3) & 0x1f) | ((checked_readings[0] << 5) & 0x60);
            buffer[8] = 0x80 | ((opt_sensor_current_time >> 28) & 0x0f) | ((checked_readings[1] << 4) & 0x70);
            buffer[9] = 0x80 | ((opt_sensor_current_time >> 21) & 0x7f);
            buffer[10] = 0x80 | ((opt_sensor_current_time >> 14) & 0x7f);
            buffer[11] = 0x80 | ((opt_sensor_current_time >> 7) & 0x7f);
            buffer[12] = 0x80 | ((opt_sensor_current_time >> 0) & 0x7f);
            Serial.write(buffer, 15);
            // We only really need to clear these here, as their values aren't used in between loops except for sensor logging.
            opt_sensor_initiated_sending_ir_signal = false;
            opt_sensor_duplicate_frame[1] = false;
            opt_sensor_ignore_duplicate[1] = false;
            opt_sensor_duplicate_frame[0] = false;
            opt_sensor_ignore_duplicate[0] = false;
        }
#endif
        for (uint8_t c = 0; c < OPT_SENSOR_CHANNELS; c++)
        {
            uint8_t reading = checked_readings[c];
            opt_sensor_readings_last[c] = reading;
            opt_sensor_reading_counter++;
            if (reading > opt_sensor_readings_high[c])
            {
                opt_sensor_readings_high[c] = reading;
            }
            if (reading < opt_sensor_readings_low[c])
            {
                opt_sensor_readings_low[c] = reading;
            }
        }
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    }
#endif
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    if (opt_sensor_disable_debug_detection_flag_after)
    {
        if (opt_sensor_current_time == 0)
        {
            opt_sensor_current_time = micros();
        }
        if (opt_sensor_current_time >= opt_sensor_disable_debug_detection_flag_after && opt_sensor_current_time - opt_sensor_disable_debug_detection_flag_after < 60000000)
        {
            opt_sensor_disable_debug_detection_flag_after = 0;
            bitClear(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
            bitClear(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
            bitClear(PORT_DEBUG_AVERAGE_TIMING_MODE_RESYNC_D14, DEBUG_AVERAGE_TIMING_MODE_RESYNC_D14);
            bitClear(PORT_DEBUG_DUPLICATE_FRAME_D16, DEBUG_DUPLICATE_FRAME_D16);
        }
    }
#endif
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    if (ir_led_token_active)
    {
        ir_led_token_active_countdown = 10; // 10 loops equites to 136 usec (the adc delay could be as much as 100 usec so lets use 10)
    }
    else if (ir_led_token_active_countdown > 0)
    {
        ir_led_token_active_countdown -= 1;
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2
        if (ir_led_token_active_countdown == 0)
        {
            bitClear(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2); // IR LED token ended
        }
#endif
#endif
    }
#endif
}

void opt_sensor_clear_stats(void)
{
    opt_sensor_reading_counter = 0;
    opt_sensor_duplicate_frames_counter = 0;
    opt_sensor_premature_frames_counter = 0;
    memset((void *)opt_sensor_readings_high, 0, sizeof(opt_sensor_readings_high));
    memset((void *)opt_sensor_readings_low, 255, sizeof(opt_sensor_readings_low));
}

// Interrupt handler called each time an ADC reading is ready.
ISR(ADC_vect)
{
    uint8_t reading = ADCH;
#ifdef OPT_SENSOR_FILTER_ADC_SIGNAL
    if (opt_sensor_filter_mode == 1)
    {
        uint8_t filter = opt_sensor_readings_realtime_filter[opt_sensor_channel];
        uint8_t reading_last = opt_sensor_readings[opt_sensor_channel];
        if ((reading > filter && filter > reading_last) || (reading < filter && filter < reading_last))
        {
            opt_sensor_readings[opt_sensor_channel] = filter;
        }
        opt_sensor_readings_realtime_filter[opt_sensor_channel] = reading;
    }
    else
    {
        opt_sensor_readings[opt_sensor_channel] = reading;
    }
#else
    opt_sensor_readings[opt_sensor_channel] = reading;
#endif
    opt_sensor_channel++;
    if (opt_sensor_channel >= OPT_SENSOR_CHANNELS)
    {
        opt_sensor_channel = 0;
    }
    ADMUX = (ADMUX & 0xf8) | (admux[opt_sensor_channel] & 0x07);
    bitSet(ADCSRA, ADSC);
}