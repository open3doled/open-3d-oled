/*
* Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
*/

#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "opt101_sensor.h"

#define bitclr( reg, bit ) ( reg &= ~( 1 << bit ))  // Clear register bit.
#define bittst( reg, bit ) ( reg & ( 1 << bit ))    // Test register bit.
#define mult_by_threshold( high, low, threshold ) ( ((uint16_t)threshold*(uint16_t)high + (uint16_t)(255-threshold)*(uint16_t)low) >> 8)

#ifdef OPT101_ENABLE_IGNORE_DURING_IR
volatile uint8_t ir_led_token_active_countdown = 0;
#endif

#ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
#define OPT101_TARGET_CONTIGUOUS_NON_DECREASING_READINGS_ABOVE_THRESHOLD 5
uint32_t opt101_last_detection_time;
uint32_t opt101_next_eligible_detection_time;
bool opt101_last_detection_time_initialized;
uint32_t opt101_average_detection_time_running_total = 0;
uint8_t opt101_average_detection_time_count = 0;
uint8_t opt101_contiguous_non_decreasing_readings_above_threshold[OPT101_CHANNELS];
#endif

#ifdef OPT101_ENABLE_STATS
uint32_t opt101_stats_count = 0;
#endif

uint32_t opt101_current_time;
bool opt101_reading_above_threshold;

uint8_t opt101_enable_frequency_analysis_based_duplicate_frame_detection = 0;
uint8_t opt101_enable_ignore_during_ir = 0;
uint8_t opt101_enable_smart_duplicate_frame_handling = 0;
uint8_t opt101_output_stats = 0;
uint8_t opt101_detection_threshold = 128;
uint8_t opt101_detection_threshold_repeated_high = 224;
uint8_t opt101_detection_threshold_repeated_low = 32;
uint32_t opt101_block_signal_detection_delay = OPT101_BLOCK_SIGNAL_DETECTION_DELAY;
uint8_t opt101_block_n_subsequent_duplicates = 0;
uint8_t opt101_min_threshold_value_to_activate = OPT101_MIN_THRESHOLD_VALUE_TO_ACTIVATE;
uint32_t opt101_block_signal_detection_until = 0;
uint32_t opt101_disable_debug_detection_flag_after = 0;
uint8_t opt101_detected_signal_start_eye = 0;
bool opt101_detected_signal_start_eye_set = false;
volatile uint8_t opt101_sensor_channel = 0;
bool opt101_readings_active = false;
uint16_t opt101_duplicate_frames_in_a_row_counter = 0;
uint8_t opt101_readings_last[OPT101_CHANNELS];

uint16_t opt101_reading_counter = 0;
uint16_t opt101_duplicate_frames_counter = 0;
uint16_t opt101_premature_frames_counter = 0;
#ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
uint32_t opt101_average_detection_time_average = 0;
#endif
uint16_t opt101_channel_frequency_detection_counter[OPT101_CHANNELS];
volatile uint8_t opt101_readings[OPT101_CHANNELS];
uint8_t opt101_readings_high[OPT101_CHANNELS];
uint8_t opt101_readings_low[OPT101_CHANNELS];
uint8_t opt101_readings_threshold[OPT101_CHANNELS];
#ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
uint8_t opt101_readings_threshold_repeated_high[OPT101_CHANNELS];
uint8_t opt101_readings_threshold_repeated_low[OPT101_CHANNELS];
#endif

uint16_t opt101_ss_reading_counter = 0;
uint16_t opt101_ss_duplicate_frames_counter = 0;
uint16_t opt101_ss_premature_frames_counter = 0;
#ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
uint32_t opt101_ss_average_detection_time_average = 0;
#endif
uint16_t opt101_ss_channel_frequency_detection_counter[OPT101_CHANNELS];
volatile uint8_t opt101_ss_readings[OPT101_CHANNELS];
uint8_t opt101_ss_readings_high[OPT101_CHANNELS];
uint8_t opt101_ss_readings_low[OPT101_CHANNELS];
uint8_t opt101_ss_readings_threshold[OPT101_CHANNELS];
#ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
uint8_t opt101_ss_readings_threshold_repeated_high[OPT101_CHANNELS];
uint8_t opt101_ss_readings_threshold_repeated_low[OPT101_CHANNELS];
#endif

/*
    7,  // A0               PF7                 ADC7 // right eye
    6,  // A1               PF6                 ADC6 // left eye
    5,  // A2               PF5                 ADC5    
    4,  // A3               PF4                 ADC4
    1,  // A4               PF1                 ADC1    
    0,  // A5               PF0                 ADC0   
*/
//const uint8_t admux[OPT101_CHANNELS] = {ADC7D, ADC6D, ADC5D, ADC4D}; // ADC MUX channels.
const uint8_t admux[OPT101_CHANNELS] = {ADC7D, ADC6D}; // ADC MUX channels. (right eye, left eye)

void opt101_sensor_Init(void) 
{
    #ifdef OPT101_ENABLE_IGNORE_DURING_IR
    ir_led_token_active_countdown = 0;
    #endif
    #ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
    opt101_last_detection_time = 0;
    opt101_next_eligible_detection_time = 0;
    opt101_last_detection_time_initialized = false;
    opt101_average_detection_time_running_total = 0;
    opt101_average_detection_time_count = 0;
    memset((void *)opt101_contiguous_non_decreasing_readings_above_threshold, 0, sizeof(opt101_contiguous_non_decreasing_readings_above_threshold));
    #endif
    #ifdef OPT101_ENABLE_STATS
    opt101_stats_count = 0;
    #endif
    opt101_enable_frequency_analysis_based_duplicate_frame_detection = 0;
    opt101_enable_smart_duplicate_frame_handling = 0;
    opt101_output_stats = 0;
    opt101_detection_threshold = 128;
    opt101_detection_threshold_repeated_high = 224;
    opt101_detection_threshold_repeated_low = 32;
    opt101_block_signal_detection_delay = OPT101_BLOCK_SIGNAL_DETECTION_DELAY;
    opt101_min_threshold_value_to_activate = OPT101_MIN_THRESHOLD_VALUE_TO_ACTIVATE;
    opt101_block_signal_detection_until = 0;
    opt101_disable_debug_detection_flag_after = 0;
    opt101_detected_signal_start_eye = 0;
    opt101_detected_signal_start_eye_set = false;
    opt101_sensor_channel = 0;
    opt101_readings_active = false;
    opt101_duplicate_frames_in_a_row_counter = 0;

    opt101_reading_counter = 0;
    opt101_duplicate_frames_counter = 0;
    opt101_premature_frames_counter = 0;
    #ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
    opt101_average_detection_time_average = 0;
    #endif
    memset((void *)opt101_channel_frequency_detection_counter, 0, sizeof(opt101_channel_frequency_detection_counter));
    memset((void *)opt101_readings, 0, sizeof(opt101_readings));
    memset((void *)opt101_readings_high, 0, sizeof(opt101_readings_high));
    memset((void *)opt101_readings_low, 255, sizeof(opt101_readings_low));
    memset((void *)opt101_readings_threshold, 60, sizeof(opt101_readings_threshold));
    #ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
    memset((void *)opt101_readings_threshold_repeated_high, 60, sizeof(opt101_readings_threshold_repeated_high));
    memset((void *)opt101_readings_threshold_repeated_low, 60, sizeof(opt101_readings_threshold_repeated_low));
    #endif
    
    ADMUX  = _BV(REFS0)  // ref = AVCC
           | _BV(ADLAR)  // left adjust result
           | (admux[opt101_sensor_channel] & 0x07);  // input channel
    ADCSRB = 0
           | _BV(ADHSM) // Writing this ADHSM bit to one enables the ADC High Speed mode. This mode enables higher conversion rate at the expense of higher power consumption.
           ;          // free running mode (when ADATE set below) 
    ADCSRA = _BV(ADEN)   // enable
           | _BV(ADSC)   // start conversion
//           | _BV(ADATE)  // auto trigger enable
           | _BV(ADIF)   // clear interrupt flag
           | _BV(ADIE)   // interrupt enable,
           | 4;          // prescaler (was 100) 13*2^n/16000000 = 000-001 2, 010 4, 011 8, 100 16, 101 32, 110 64 111 128 
           // 
           // (100 16 is a good tradeoff gives 36us delay and 70us jitter (calculated 13us conv time) but values seem noisy) (110 64 has 136us delay and 110us jitter (52us conv time) values seem non-noisy)
           // atmel-7766-8-bit-avr-atmega16u4-32u4_datasheet.pdf
           // By default, the successive approximation circuitry requires an input clock frequency between 50kHz and
           // 200kHz to get maximum resolution. If a lower resolution than 10 bits is needed, the input clock frequency to the
           // ADC can be higher than 200kHz to get a higher sample rate. Alternatively, setting the ADHSM bit in ADCSRB
           // allows an increased ADC clock frequency at the expense of higher power consumption.
           // A normal conversion takes 13 ADC clock cycles. The first conversion after the ADC is switched on (ADEN in
           // ADCSRA is set) takes 25 ADC clock cycles in order to initialize the analog circuitry. 

    #ifdef OPT101_ENABLE_PWM_ADC_MIRRORS_DEBUG_PIN_D6_D10
    // OC4D -> PD7 -> D6 and OC4B -> PB6 -> D10
    TCCR4A = 0;
    TCCR4B = 0;
    TCCR4C = 0;
    TCCR4D = 0; // count up to OCR4C only
    //TCCR4B |= (0 << CS43) | (0 << CS42) | (0 << CS41) | (1 << CS40); // 0 0 0 1 ... clkIO/1 (No prescaling)
    TCCR4B |= (1 << CS43) | (0 << CS42) | (0 << CS41) | (0 << CS40); // 1 0 0 0 ... clkIO/2^8 clkIO/256 (No prescaling)
    OCR4C = 255; // count up to 255
    TCCR4A |= (1 << PWM4B) | (1 << COM4B1); // CLEAR at compare with OCR4B, SET at 0x00 
    TCCR4C |= (1 << PWM4D) | (1 << COM4D1); // CLEAR at compare with OCR4D, SET at 0x00 
    //TCCR4A |= (1 << PWM4B) | (1 << COM4B1) | (1 << COM4B0); // SET at compare with OCR4B, CLEAR at 0x00 
    //TCCR4C |= (1 << PWM4D) | (1 << COM4D1) | (1 << COM4D0); // SET at compare with OCR4D, CLEAR at 0x00 
    OCR4D = 0; // left
    OCR4B = 0; // right
    #endif

}

#ifdef OPT101_ENABLE_SPI8_ADC_OUTPUT_DEBUG_PIN_D6_D10
void debug_output_spi_8_d6_d10(uint8_t data_value) {
	uint8_t data_value_flipped = data_value;
    /*
	uint8_t p;
	for (p = 0; p < 8; p++) {
		if (data_value_flipped & 0x80) {
			bitSet(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
		}
		else {
			bitClear(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
		}
		bitSet(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
		data_value_flipped <<= 1;
		bitClear(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
	}
    */

    if (data_value_flipped & 0x80) {
        bitSet(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    else {
        bitClear(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    bitSet(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
    data_value_flipped <<= 1;
    bitClear(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);

    if (data_value_flipped & 0x80) {
        bitSet(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    else {
        bitClear(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    bitSet(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
    data_value_flipped <<= 1;
    bitClear(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);

    if (data_value_flipped & 0x80) {
        bitSet(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    else {
        bitClear(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    bitSet(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
    data_value_flipped <<= 1;
    bitClear(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);

    if (data_value_flipped & 0x80) {
        bitSet(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    else {
        bitClear(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    bitSet(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
    data_value_flipped <<= 1;
    bitClear(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);

    if (data_value_flipped & 0x80) {
        bitSet(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    else {
        bitClear(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    bitSet(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
    data_value_flipped <<= 1;
    bitClear(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);

    if (data_value_flipped & 0x80) {
        bitSet(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    else {
        bitClear(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    bitSet(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
    data_value_flipped <<= 1;
    bitClear(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);

    if (data_value_flipped & 0x80) {
        bitSet(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    else {
        bitClear(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    bitSet(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
    data_value_flipped <<= 1;
    bitClear(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);

    if (data_value_flipped & 0x80) {
        bitSet(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    else {
        bitClear(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    }
    bitSet(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
    data_value_flipped <<= 1;
    bitClear(PORT_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);

    __asm__ __volatile__ ("nop\n\t");
	bitClear(PORT_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    __asm__ __volatile__ ("nop\n\t");
    __asm__ __volatile__ ("nop\n\t");
    __asm__ __volatile__ ("nop\n\t");
    __asm__ __volatile__ ("nop\n\t");
    __asm__ __volatile__ ("nop\n\t");
}
#endif

#ifdef OPT101_ENABLE_STATS
void opt101_sensor_PrintStats(void) 
{
    #ifdef OPT101_STATS_TOGGLE_D15
    bitSet(PORT_DEBUG_PORT_D15, DEBUG_PORT_D15);
    #endif
    switch(opt101_stats_count)
    {
        case 0:
            
            opt101_ss_reading_counter = opt101_reading_counter;
            opt101_ss_duplicate_frames_counter = opt101_duplicate_frames_counter;
            opt101_ss_premature_frames_counter = opt101_premature_frames_counter;
            #ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
            opt101_ss_average_detection_time_average = opt101_average_detection_time_average;
            #endif
            for (int ch = 0; ch < OPT101_CHANNELS; ch++)
            {
                opt101_ss_channel_frequency_detection_counter[ch] = opt101_channel_frequency_detection_counter[ch];
                opt101_ss_readings[ch] = opt101_readings[ch];
                opt101_ss_readings_high[ch] = opt101_readings_high[ch];
                opt101_ss_readings_low[ch] = opt101_readings_low[ch];
                opt101_ss_readings_threshold[ch] = opt101_readings_threshold[ch];
                #ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
                opt101_ss_readings_threshold_repeated_high[ch] = opt101_readings_threshold_repeated_high[ch];
                opt101_ss_readings_threshold_repeated_low[ch] = opt101_readings_threshold_repeated_low[ch];
                #endif
            }
            opt101_sensor_UpdateThresholds();
            opt101_sensor_ClearStats();
        case 1*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print("+stats general reading_counter:");
            Serial.print(opt101_ss_reading_counter);
            break;
        case 2*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" duplicate_frames:");
            Serial.print(opt101_ss_duplicate_frames_counter);
            break;
        case 3*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" premature_frames:");
            Serial.print(opt101_ss_premature_frames_counter);
    #ifndef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
            Serial.println();
            opt101_stats_count += OPT101_STATS_SERIAL_OUTPUT_FREQUENCY;
            break;
    #else
            break;
        case 4*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" average_detection_time:");
            Serial.print(opt101_ss_average_detection_time_average);
            Serial.println();
            break;
    #endif
        case 5*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print("+stats sensor channel:right");
            break;
        case 6*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" detections:");
            Serial.print(opt101_ss_channel_frequency_detection_counter[0]);
            break;
        case 7*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" reading:");
            Serial.print(opt101_ss_readings[0]);
            break;
        case 8*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" high:");
            Serial.print(opt101_ss_readings_high[0]);
            break;
        case 9*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" low:");
            Serial.print(opt101_ss_readings_low[0]);
            break;
        case 10*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" thr:");
            Serial.print(opt101_ss_readings_threshold[0]);
    #ifndef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
            Serial.println();
            opt101_stats_count += 2*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY;
            break;
    #else
        case 11*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" thr_rh:");
            Serial.print(opt101_ss_readings_threshold_repeated_high[0]);
            break;
        case 12*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" thr_rl:");
            Serial.print(opt101_ss_readings_threshold_repeated_low[0]);
            Serial.println();
            break;
    #endif
        case 13*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print("+stats sensor channel:left");
            break;
        case 14*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" detections:");
            Serial.print(opt101_ss_channel_frequency_detection_counter[1]);
            break;
        case 15*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" reading:");
            Serial.print(opt101_ss_readings[1]);
            break;
        case 16*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" high:");
            Serial.print(opt101_ss_readings_high[1]);
            break;
        case 17*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" low:");
            Serial.print(opt101_ss_readings_low[1]);
            break;
        case 18*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" thr:");
            Serial.print(opt101_ss_readings_threshold[1]);
    #ifndef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
            Serial.println();
            opt101_stats_count += 2*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY;
            break;
    #else
        case 19*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" thr_rh:");
            Serial.print(opt101_ss_readings_threshold_repeated_high[1]);
            break;
        case 20*OPT101_STATS_SERIAL_OUTPUT_FREQUENCY:
            Serial.print(" thr_rl:");
            Serial.print(opt101_ss_readings_threshold_repeated_low[1]);
            Serial.println();
            break;
    #endif
    }
    opt101_stats_count++;
    #ifdef OPT101_STATS_TOGGLE_D15
    bitClear(PORT_DEBUG_PORT_D15, DEBUG_PORT_D15);
    #endif
}

bool opt101_sensor_FinishPrintStats(void) 
{
    bool done = (opt101_stats_count > (4 + 8*2) * OPT101_STATS_SERIAL_OUTPUT_FREQUENCY);
    if (done)
    {
        opt101_stats_count = 0;
    }
    return done;
}
#endif

void opt101_sensor_UpdateThresholds(void) 
{
    opt101_readings_active = true;
    for (uint8_t c = 0; c < OPT101_CHANNELS; c++)
    {
        if (opt101_readings_threshold[c] < opt101_min_threshold_value_to_activate)
        {
            opt101_readings_active = false;
        }
        opt101_readings_threshold[c] = mult_by_threshold(opt101_readings_high[c], opt101_readings_low[c], opt101_detection_threshold);
        #ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
        opt101_readings_threshold_repeated_high[c] = mult_by_threshold(opt101_readings_high[c], opt101_readings_low[c], opt101_detection_threshold_repeated_high);
        opt101_readings_threshold_repeated_low[c] = mult_by_threshold(opt101_readings_high[c], opt101_readings_low[c], opt101_detection_threshold_repeated_low);
        #endif
    }
}

void opt101_sensor_CheckReadings(void) 
{
    uint8_t checked_readings[2]; 
    #ifdef OPT101_ENABLE_PWM_ADC_MIRRORS_DEBUG_PIN_D6_D10
    // OC4D -> PD7 -> D6 and OC4B -> PB6 -> D10
    OCR4D = opt101_readings[1]; // left
    OCR4B = opt101_readings[0]; // right
    #endif
    #ifdef OPT101_ENABLE_SPI8_ADC_OUTPUT_DEBUG_PIN_D6_D10
    debug_output_spi_8_d6_d10(opt101_readings[1]); // left
    debug_output_spi_8_d6_d10(opt101_readings[0]); // right
    #endif
    #ifdef OPT101_ENABLE_IGNORE_DURING_IR
    if (opt101_enable_ignore_during_ir == 0 || (!ir_led_token_active && !ir_led_token_active_countdown))
    {
    #endif
    for (uint8_t c = 0; c < OPT101_CHANNELS; c++)
    {
        checked_readings[c] = opt101_readings[c];
    }
    opt101_current_time = 0;
    if (opt101_block_signal_detection_until == 0)
    {
        for (uint8_t c = 0; c < OPT101_CHANNELS; c++)
        {
            uint8_t last_reading = opt101_readings_last[c];
            checked_readings[c] = opt101_readings[c];
            #ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
            uint8_t other_channel = c == 1 ? 0 : 1;
            #endif
            opt101_reading_above_threshold = false;
            if (opt101_readings_active)
            {
                if (last_reading < opt101_readings_threshold[c] && 
                    checked_readings[c] >= opt101_readings_threshold[c])
                {
                    opt101_reading_above_threshold = true;
                }
                #ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
                else if (opt101_enable_frequency_analysis_based_duplicate_frame_detection)
                {
                    if (opt101_current_time == 0)
                    {
                        opt101_current_time = micros();
                    }
                    if (opt101_average_detection_time_average &&
                        opt101_current_time > opt101_next_eligible_detection_time &&
                        last_reading > opt101_readings_threshold_repeated_high[c] && 
                        reading > opt101_readings_threshold_repeated_high[c] &&
                        reading >= last_reading &&
                        opt101_readings[other_channel] < opt101_readings_threshold_repeated_low[other_channel]) // is the other channel under the low threshold
                    {
                        opt101_contiguous_non_decreasing_readings_above_threshold[c] += 1;
                        if (opt101_contiguous_non_decreasing_readings_above_threshold[c] > OPT101_TARGET_CONTIGUOUS_NON_DECREASING_READINGS_ABOVE_THRESHOLD)
                        {
                            opt101_reading_above_threshold = true;
                            #ifdef ENABLE_DEBUG_PIN_OUTPUTS
                            #ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION_DEBUG_PIN_D2
                            bitSet(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2);
                            #endif
                            #endif
                        }
                    }
                    else {
                        opt101_contiguous_non_decreasing_readings_above_threshold[c] = 0;
                    }
                }
            #endif
            }
            if (opt101_reading_above_threshold)
            {
                if (opt101_current_time == 0)
                {
                    opt101_current_time = micros();
                }
                #ifdef OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
                if (opt101_last_detection_time_initialized)
                {
                    if (opt101_average_detection_time_count == (1 << OPT101_UPDATE_AVERAGE_PERIOD_FOR_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION))
                    {
                        opt101_average_detection_time_average = opt101_average_detection_time_running_total >> OPT101_UPDATE_AVERAGE_PERIOD_FOR_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION;
                        opt101_average_detection_time_running_total = opt101_current_time - opt101_last_detection_time;
                        opt101_average_detection_time_count = 1;
                    }
                    else
                    {
                        opt101_average_detection_time_running_total += opt101_current_time - opt101_last_detection_time;
                        opt101_average_detection_time_count += 1;
                    }
                    if (opt101_average_detection_time_average) 
                    {
                        // we adjuste down to compensate for OPT101_TARGET_CONTIGUOUS_NON_DECREASING_READINGS_ABOVE_THRESHOLD at 75 micros per cycle
                        opt101_next_eligible_detection_time = opt101_current_time + opt101_average_detection_time_average - 50 * OPT101_TARGET_CONTIGUOUS_NON_DECREASING_READINGS_ABOVE_THRESHOLD;
                    }
                }
                opt101_last_detection_time = opt101_current_time;
                opt101_last_detection_time_initialized = true;
                #endif
                opt101_block_signal_detection_until = opt101_current_time + opt101_block_signal_detection_delay;
                #ifdef ENABLE_DEBUG_PIN_OUTPUTS
                opt101_disable_debug_detection_flag_after = opt101_current_time + (opt101_block_signal_detection_delay>>2); // half of the block signal detection delay in length
                if (c) 
                {
                    bitSet(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
                }
                else
                {
                    bitSet(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
                }
                #endif
                bool opt101_ignore_duplicate = false;
                bool opt101_duplicate_frame = (opt101_detected_signal_start_eye == c && opt101_detected_signal_start_eye_set);
                if (opt101_duplicate_frame) 
                {
                    #ifdef ENABLE_DEBUG_PIN_OUTPUTS
                    bitSet(PORT_DEBUG_DUPLICATE_FRAME_D16, DEBUG_DUPLICATE_FRAME_D16);
                    #endif
                    opt101_duplicate_frames_counter++;
                    opt101_duplicate_frames_in_a_row_counter++;
                    if (opt101_enable_smart_duplicate_frame_handling && (opt101_duplicate_frames_in_a_row_counter % 2) == 1) 
                    {
                        opt101_ignore_duplicate = true;
                        Serial.print("+d ");
                        Serial.println(c);
                    }
                }
                else
                {
                    opt101_duplicate_frames_in_a_row_counter = 0;
                }
                opt101_detected_signal_start_eye = c;
                opt101_detected_signal_start_eye_set = true;
                if (!opt101_ignore_duplicate)
                {
                    // TODO: make sure we are doing the right thing here
                    if (opt101_duplicate_frame) {
                        ir_signal_process_opt101(opt101_detected_signal_start_eye, true);
                    }
                    else {
                        ir_signal_process_opt101(opt101_detected_signal_start_eye, false);
                    }
                    /*
                    {
                        #ifdef ENABLE_DEBUG_PIN_OUTPUTS
                        bitSet(PORT_DEBUG_PREMATURE_FRAME_D14, DEBUG_PREMATURE_FRAME_D14);
                        #endif
                        opt101_premature_frames_counter += 1;
                    }
                    */
                }
                opt101_channel_frequency_detection_counter[opt101_detected_signal_start_eye] += 1;
            }
            if (opt101_reading_above_threshold)
            {
                break;
            }
        }
    }
    else
    {
        if (opt101_current_time == 0)
        {
            opt101_current_time = micros();
        }
        if (opt101_current_time >= opt101_block_signal_detection_until && opt101_current_time - opt101_block_signal_detection_until < 60000000)
        {
            opt101_block_signal_detection_until = 0;
        }
    }
    for (uint8_t c = 0; c < OPT101_CHANNELS; c++)
    {
        uint8_t reading = checked_readings[c];
        opt101_readings_last[c] = reading;
        opt101_reading_counter++;
        if (reading > opt101_readings_high[c]) 
        {
            opt101_readings_high[c] = reading;
        }
        if (reading < opt101_readings_low[c]) 
        {
            opt101_readings_low[c] = reading;
        }
    }
    #ifdef OPT101_ENABLE_IGNORE_DURING_IR
    }
    #endif
    #ifdef ENABLE_DEBUG_PIN_OUTPUTS
    if (opt101_disable_debug_detection_flag_after)
    {
        if (opt101_current_time == 0)
        {
            opt101_current_time = micros();
        }
        if (opt101_current_time >= opt101_disable_debug_detection_flag_after && opt101_current_time - opt101_disable_debug_detection_flag_after < 60000000)
        {
            opt101_disable_debug_detection_flag_after = 0;
            bitClear(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
            bitClear(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
            bitClear(PORT_DEBUG_PREMATURE_FRAME_D14, DEBUG_PREMATURE_FRAME_D14);
            bitClear(PORT_DEBUG_DUPLICATE_FRAME_D16, DEBUG_DUPLICATE_FRAME_D16);
            #if defined(OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION) && defined(OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION_DEBUG_PIN_D2)
            bitClear(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2);
            #endif
        }
    }
    #endif
    #ifdef OPT101_ENABLE_IGNORE_DURING_IR
    if (ir_led_token_active)
    {
        ir_led_token_active_countdown = 10; // 10 loops equites to 136 usec (the adc delay could be as much as 100 usec so lets use 10)
    }
    else if (ir_led_token_active_countdown > 0)
    {
        ir_led_token_active_countdown -= 1;
        #ifdef ENABLE_DEBUG_PIN_OUTPUTS
        #ifdef OPT101_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2
        if (ir_led_token_active_countdown == 0)
        {
            bitClear(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2); // IR LED token ended
        }
        #endif
        #endif
    }
    #endif
}

void opt101_sensor_ClearStats(void) 
{
    opt101_reading_counter = 0;
    opt101_duplicate_frames_counter = 0;
    opt101_premature_frames_counter = 0;
    memset((void *)opt101_channel_frequency_detection_counter, 0, sizeof(opt101_channel_frequency_detection_counter));
    memset((void *)opt101_readings_high, 0, sizeof(opt101_readings_high));
    memset((void *)opt101_readings_low, 255, sizeof(opt101_readings_low));
}


// Interrupt handler called each time an ADC reading is ready.
ISR(ADC_vect)
{
    uint8_t reading = ADCH;
    opt101_readings[opt101_sensor_channel] = reading;
    opt101_sensor_channel++;
    if (opt101_sensor_channel >= OPT101_CHANNELS)
    {
        opt101_sensor_channel = 0;
    }
    ADMUX = ( ADMUX & 0xf8 ) | ( admux[opt101_sensor_channel] & 0x07 );
    bitSet(ADCSRA, ADSC);
}