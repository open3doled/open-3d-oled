/*
* Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
*/

#ifndef _SETTINGS_H_
#define _SETTINGS_H_

#define ENABLE_DEBUG_PIN_OUTPUTS
#define ENABLE_LOOP_TOGGLE_DEBUG_PIN_D9 // will toggle on/off every time the loop goes round
//#define EMITTER_TEST_MODE // runs in 120 hz output mode locally without using opt101 sensors to test glasses.
#define OPT101_ENABLE_IGNORE_DURING_IR // ignore opt101 sensor readings when LED is triggering due to power/light distortions that may cause opt101 sensor reading inconsistencies.
//#define OPT101_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2 // use the D2 pin to show when we disable opt101 reading because we are sending an active led token.
#define OPT101_ENABLE_STATS // prints opt101 statistics every OPT101_UPDATE_STAT_PERIOD micros
//#define OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION // enable display update frequency analysis and apply it to duplicate frame detection (this is to aid in support for display types that don't support BFI).
//#define OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION_DEBUG_PIN_D2 // use the D2 pin to show when we have a duplicate frame detected using frequency analysis.
//#define OPT101_ENABLE_PWM_ADC_MIRRORS_DEBUG_PIN_D6_D10 // this isn't usable any longer because we are using timer 4 in the ir signal scheduler instead.
//#define OPT101_STATS_TOGGLE_D15 // will toggle on/off every time the stats are printed
//#define OPT101_ENABLE_SPI8_ADC_OUTPUT_DEBUG_PIN_D6_D10 // this outputs the adc value as an SPI8 value on each call to opt101_sensor_CheckReadings

#define OPT101_UPDATE_AVERAGE_PERIOD_FOR_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION 7 // this is 2^n so for 7 it will be 128 we do this because then we can do division for average computation with a bitshift.
#define OPT101_UPDATE_STAT_PERIOD 5000000 // in micros (frequency to update and optionally display stats for the opt101 sensor module)
#define NUMBER_OF_IR_PROTOCOLS 7

// defaults LCD 2560x1080 60hz
/*
#define OPT101_BLOCK_SIGNAL_DETECTION_DELAY 15000 // in micros (some value around 90% of the frame rate, large enough to avoid false positive when signal is going down but small enough that dynamic framerate detection delay still works for displays without BFI)
#define IR_FRAME_DURATION  (9500)    // Frame exposure duration in microseconds (@16MHz)
#define IR_FRAME_DELAY       (250)       // Time between opt101 trigger and start of IR token (in microseconds (@16MHz))
//*/

// defaults LG OLED 1920x1080 120hz
//*
#define OPT101_BLOCK_SIGNAL_DETECTION_DELAY 6500 // in micros (some value around 90% of the frame rate, large enough to avoid false positive when signal is going down but small enough that dynamic framerate detection delay still works for displays without BFI)
#define IR_FRAME_DURATION  (7000)    // Frame exposure duration in microseconds (@16MHz)
#define IR_FRAME_DELAY       (500)    // Time between opt101 trigger and start of IR token (in microseconds (@16MHz))
#define IR_SIGNAL_SPACING   (30)    // Minimum time required between ir signals being sent in us (measured at 17us currently so 30 us should be more than enough I think). 
//*/

/* 
* Useful Commands
* cd ~/Documents/PlatformIO/Projects/misc/3d_ir_controller/.pio/build/sparkfun_promicro16/
* avr-objdump -S firmware.elf > firmware.asm
*/

// ATMEL ATMEGA32U4 / ARDUINO LEONARDO
//
// D0               PD2                 RXD1/INT2
// D1               PD3                 TXD1/INT3
// D2               PD1     SDA         SDA/INT1
// D3#              PD0     PWM8/SCL    OC0B/SCL/INT0
// D4       A6      PD4                 ADC8
// D5#              PC6     ???         OC3A/#OC4A
// D6#      A7      PD7     FastPWM     #OC4D/ADC10
// D7               PE6                 INT6/AIN0
//
// D8       A8      PB4                 ADC11/PCINT4
// D9#      A9      PB5     PWM16       OC1A/#OC4B/ADC12/PCINT5
// D10#     A10     PB6     PWM16       OC1B/0c4B/ADC13/PCINT6
// D11#             PB7     PWM8/16     0C0A/OC1C/#RTS/PCINT7
// D12      A11     PD6                 T1/#OC4D/ADC9
// D13#             PC7     PWM10       CLK0/OC4A
//
// A0       D18     PF7                 ADC7
// A1       D19     PF6                 ADC6
// A2       D20     PF5                 ADC5
// A3       D21     PF4                 ADC4
// A4       D22     PF1                 ADC1
// A5       D23     PF0                 ADC0
//
// New pins D14..D17 to map SPI port to digital pins
//
// MISO     D14     PB3                 MISO,PCINT3
// SCK      D15     PB1                 SCK,PCINT1
// MOSI     D16     PB2                 MOSI,PCINT2
// SS       D17     PB0                 RXLED,SS/PCINT0
//
// Connected LEDs on board for TX and RX
// TXLED    D30     PD5                 XCK1
// RXLED    D17     PB0
// HWB              PE2                 HWB

// D2
#define DEBUG_PORT_D2      1
#define DDR_DEBUG_PORT_D2  DDRD
#define PORT_DEBUG_PORT_D2 PORTD

// D3 (was D10)
#define LED_IR_D3          0
#define DDR_LED_IR_D3      DDRD
#define PORT_LED_IR_D3     PORTD

// D4
#define DEBUG_DETECTED_LEFT_D4        4
#define DDR_DEBUG_DETECTED_LEFT_D4    DDRD
#define PORT_DEBUG_DETECTED_LEFT_D4   PORTD

// D5
#define DEBUG_DETECTED_RIGHT_D5       6
#define DDR_DEBUG_DETECTED_RIGHT_D5   DDRC
#define PORT_DEBUG_DETECTED_RIGHT_D5  PORTC

// D6
#define DEBUG_PWM_READING_LEFT_D6       7
#define DDR_DEBUG_PWM_READING_LEFT_D6   DDRD
#define PORT_DEBUG_PWM_READING_LEFT_D6  PORTD

// D7 (was D8)
#define DEBUG_ACTIVATE_LEFT_D7         6
#define DDR_DEBUG_ACTIVATE_LEFT_D7     DDRE
#define PORT_DEBUG_ACTIVATE_LEFT_D7    PORTE

// D8 (was D9)
#define DEBUG_ACTIVATE_RIGHT_D8        4
#define DDR_DEBUG_ACTIVATE_RIGHT_D8    DDRB
#define PORT_DEBUG_ACTIVATE_RIGHT_D8   PORTB

// D9 (was D4)
#define DEBUG_PORT_D9        5
#define DDR_DEBUG_PORT_D9    DDRB
#define PORT_DEBUG_PORT_D9   PORTB

// D10 (was D5)
#define DEBUG_PWM_READING_RIGHT_D10       6
#define DDR_DEBUG_PWM_READING_RIGHT_D10   DDRB
#define PORT_DEBUG_PWM_READING_RIGHT_D10  PORTB

// D16 (was D6)
#define DEBUG_DUPLICATE_FRAME_D16       2
#define DDR_DEBUG_DUPLICATE_FRAME_D16   DDRB
#define PORT_DEBUG_DUPLICATE_FRAME_D16  PORTB

// D14 (was D7)
#define DEBUG_PREMATURE_FRAME_D14       3
#define DDR_DEBUG_PREMATURE_FRAME_D14   DDRB
#define PORT_DEBUG_PREMATURE_FRAME_D14  PORTB

// D15
#define DEBUG_PORT_D15       1
#define DDR_DEBUG_PORT_D15   DDRB
#define PORT_DEBUG_PORT_D15  PORTB

/* Includes: */
	#include <avr/io.h>
	#include <avr/wdt.h>
	#include <avr/power.h>
	#include <avr/interrupt.h>
	#include <avr/sfr_defs.h>
    
/* Util macros */
	//#define bitSet(addr,bit) (addr |= (1<<bit))
	//#define bitClear(addr,bit) (addr &= ~(1<<bit))

#define EEPROM_SETTING_ADDRESS 0
#define EEPROM_SETTING_CHECKVALUE 0x3D3D3D3D
#define EMITTER_VERSION 10

struct EEPROMSettings {
  uint32_t check_value;
  uint8_t version;
  uint8_t ir_glasses_selected;
  uint16_t ir_frame_delay; 
  uint16_t ir_frame_duration;
  uint16_t ir_signal_spacing;
  uint32_t opt101_block_signal_detection_delay;
  uint32_t opt101_min_threshold_value_to_activate;
  uint8_t opt101_detection_threshold;
  uint8_t opt101_detection_threshold_repeated_high;
  uint8_t opt101_detection_threshold_repeated_low;
  uint8_t opt101_enable_ignore_during_ir;
  uint8_t opt101_enable_smart_duplicate_frame_handling;
  uint8_t opt101_output_stats;
  uint8_t opt101_enable_frequency_analysis_based_duplicate_frame_detection;
  uint8_t opt101_block_n_subsequent_duplicates;
};

#endif /* _SETTINGS_H_ */