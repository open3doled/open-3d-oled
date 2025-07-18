/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#ifndef _SETTINGS_H_
#define _SETTINGS_H_

// #define ENABLE_DEBUG_PIN_OUTPUTS
#define ENABLE_LOOP_TOGGLE_DEBUG_PIN_D9             // will toggle on/off every time the loop goes round
#define OPT_SENSOR_ENABLE_STREAM_READINGS_TO_SERIAL // adds code for command "10" to stream the opt_sensor readings for the left and right eye over serial to the computer (this is a debug mode, don't use at the same time as show stats or you will get garbled output)
#define OPT_SENSOR_ENABLE_IGNORE_DURING_IR          // ignore opt_sensor sensor readings when LED is triggering due to power/light distortions that may cause opt_sensor sensor reading inconsistencies. (only applies when setting variable is set as well)
#define OPT_SENSOR_ENABLE_IGNORE_DURING_IR_ONLY     // only block when the ir led is actually on not during the whole ir sequence
// #define OPT_SENSOR_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2 // use the D2 pin to show when we disable opt_sensor reading because we are sending an active led token.
#define DLPLINK_DEBUG_PIN_D2                  // use the D2 pin to show debug status for the dlplink module (currently shows active pulse start to pulse end)
#define DLPLINK_DEBUG_PIN_D6                  // use the D6 pin to show debug status for the dlplink module (currently shows the blocking interval timeout)
#define DLPLINK_DEBUG_PIN_D10                 // use the D10 pin to show debug status for the dlplink module (this will break rf_trigger and minidin3_trigger mode as it uses that input pin as output) (currently shows the adc pulse block timeout)
#define DLPLINK_DEBUG_PIN_D16                 // use the D16 pin to show debug status for the dlplink module (this will break rf_trigger mode as it uses that input pin as output) (currently shows the adc sample rate)
#define OPT_SENSOR_ENABLE_STATS               // prints opt_sensor statistics every OPT_SENSOR_UPDATE_STAT_PERIOD micros
#define OPT_SENSOR_UPDATE_STAT_PERIOD 5000000 // in micros (frequency to update and optionally display stats for the opt_sensor sensor module)
#define OPT_SENSOR_FILTER_ADC_SIGNAL          // This will adjust the code to function properly with the BPW34 photodiode which has no transimpedance amplifier and has an output voltage much closer to 150mV so it can be mistriggered by noise ir led triggering. (beta testers have reported this causes flickering on some pwm backlit displays (possibly because the flashing of the backlight is irratic, perhaps this needs to be a proper peramater disabling for now by default)) (only applies when setting variable is set as well)
// #define BLOCK_IR_SIGNAL_OUTPUT                // Turn this on just blocks the IR signal output on the pin but leaves all logic in tact

#ifndef ENABLE_DEBUG_PIN_OUTPUTS
// #define ENABLE_DEBUG_STATUS_LEDS // we are using the pads for the unused button footprints on D2, D4 and D5 to drive some status LEDs.
// #define ENABLE_DEBUG_STATUS_FLASH_D2_ON_STARTUP 10
#define ENABLE_EYE_SWAP_ON_SWITCH_4_D5 // Use Switch 4 to swap the left and right eye signals it will toggle the ir_flip_eyes attribute but not store the change to eeprom
#endif
#define NUMBER_OF_IR_PROTOCOLS 8

#define IR_DRIVE_MODE_OPTICAL 0
#define IR_DRIVE_MODE_PC_SERIAL 1
#define IR_DRIVE_MODE_PC_SERIAL_LEFT 0
#define IR_DRIVE_MODE_PC_SERIAL_RIGHT 1
#define IR_DRIVE_MODE_MINIDIN3 2   // D10
#define IR_DRIVE_MODE_RF_TRIGGER 3 // D10, D16, D14, D15, D21
#define IR_DRIVE_MODE_DLP_LINK 4
#define IR_DRIVE_MODE_DLP_LINK_TRIGGER 5 // D14, D15, D21

// defaults LCD 2560x1080 60hz
/*
#define OPT_SENSOR_BLOCK_SIGNAL_DETECTION_DELAY 15000 // in micros (some value around 90% of the frame rate, large enough to avoid false positive when signal is going down but small enough that dynamic framerate detection delay still works for displays without BFI)
#define IR_FRAME_DURATION  (9500)    // Frame exposure duration in microseconds (@16MHz)
#define IR_FRAME_DELAY       (250)       // Time between opt_sensor trigger and start of IR token (in microseconds (@16MHz))
//*/

// defaults LG OLED 1920x1080 120hz
//*
#define OPT_SENSOR_BLOCK_SIGNAL_DETECTION_DELAY 6500 // in micros (some value around 90% of the frame rate, large enough to avoid false positive when signal is going down but small enough that dynamic framerate detection delay still works for displays without BFI)
#define IR_FRAME_DURATION (7000)                     // Frame exposure duration in microseconds (@16MHz)
#define IR_FRAME_DELAY (500)                         // Time between opt_sensor trigger and start of IR token (in microseconds (@16MHz))
#define IR_SIGNAL_SPACING (30)                       // Minimum time required between ir signals being sent in us (measured at 17us currently so 30 us should be more than enough I think).
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
#define DEBUG_PORT_D2 1
#define DDR_DEBUG_PORT_D2 DDRD
#define PORT_DEBUG_PORT_D2 PORTD
#define STATUS_LED_D2 1
#define DDR_STATUS_LED_D2 DDRD
#define PORT_STATUS_LED_D2 PORTD

// D3 (was D10)
#define LED_IR_D3 0
#define DDR_LED_IR_D3 DDRD
#define PORT_LED_IR_D3 PORTD
#define SWITCH_2_D3 0
#define DDR_SWITCH_2_D3 DDRD
#define PORT_SWITCH_2_D3 PORTD

// D4
#define DEBUG_DETECTED_LEFT_D4 4
#define DDR_DEBUG_DETECTED_LEFT_D4 DDRD
#define PORT_DEBUG_DETECTED_LEFT_D4 PORTD
#define STATUS_LED_D4 4
#define DDR_STATUS_LED_D4 DDRD
#define PORT_STATUS_LED_D4 PORTD
#define SWITCH_3_D4 4
#define DDR_SWITCH_3_D4 DDRD
#define PORT_SWITCH_3_D4 PORTD

// D5
#define DEBUG_DETECTED_RIGHT_D5 6
#define DDR_DEBUG_DETECTED_RIGHT_D5 DDRC
#define PORT_DEBUG_DETECTED_RIGHT_D5 PORTC
#define STATUS_LED_D5 6
#define DDR_STATUS_LED_D5 DDRC
#define PORT_STATUS_LED_D5 PORTC
#define SWITCH_4_D5 6
#define DDR_SWITCH_4_D5 DDRC
#define PORT_SWITCH_4_D5 PORTC
#define PIN_SWITCH_4_D5 PINC

// D6
#define MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_OUT_D6 7
#define DDR_MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_OUT_D6 DDRD
#define PORT_MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_OUT_D6 PORTD
#define DEBUG_PORT_D6 7
#define DDR_DEBUG_PORT_D6 DDRD
#define PORT_DEBUG_PORT_D6 PORTD

// D7 (was D8)
#define DEBUG_ACTIVATE_LEFT_D7 6
#define DDR_DEBUG_ACTIVATE_LEFT_D7 DDRE
#define PORT_DEBUG_ACTIVATE_LEFT_D7 PORTE

// D8 (was D9)
#define DEBUG_ACTIVATE_RIGHT_D8 4
#define DDR_DEBUG_ACTIVATE_RIGHT_D8 DDRB
#define PORT_DEBUG_ACTIVATE_RIGHT_D8 PORTB

// D9 (was D4)
#define DEBUG_PORT_D9 5
#define DDR_DEBUG_PORT_D9 DDRB
#define PORT_DEBUG_PORT_D9 PORTB

// D10 (MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN, RF_LEFT_SHUTTER_ACTIVE)
#define DEBUG_PORT_D10 6
#define DDR_DEBUG_PORT_D10 DDRB
#define PORT_DEBUG_PORT_D10 PORTB

// D16 (RF_LEFT_SHUTTER_COMMON)
#define DEBUG_PORT_D16 2
#define DDR_DEBUG_PORT_D16 DDRB
#define PORT_DEBUG_PORT_D16 PORTB

// D14 (RF_RIGHT_SHUTTER_ACTIVE, DLPLINK_RIGHT_SHUTTER_ACTIVE)

// D15 (RF_RIGHT_SHUTTER_COMMON, DLPLINK_RIGHT_SHUTTER_COMMON)

// D18/A0 (OPT RIGHT TRIGGER BOX ADC)

// D19/A1 (OPT LEFT TRIGGER BOX ADC, DLPLINK ADC)

// D20/A2
// FREE

// D21/A3 (RF_MODULE_POWER_ON, DLPLINK_MODULE_POWER_ON)

/* Includes: */
#include <avr/io.h>
#include <avr/wdt.h>
#include <avr/power.h>
#include <avr/interrupt.h>
#include <avr/sfr_defs.h>

/* Util macros */
// #define bitSet(addr,bit) (addr |= (1<<bit))
// #define bitClear(addr,bit) (addr &= ~(1<<bit))

#define EEPROM_SETTING_ADDRESS 0
#define EEPROM_SETTING_CHECKVALUE 0x3D3D3D3D
#define EMITTER_VERSION 22

/*
Version History
22 - Added support for dlplink input
21 - Removed pwm_backlight_frequency
20 - Added drive_mode and serial based triggering for use with WibbleWobble
19 - Added DLP-link protocol
18 - Removed opt_sensor_block_n_subsequent_duplicates and added target_frametime and pwm_backlight_frequency
17 - Added average timing mode
16 - Added detection threshold low option
15 - Fixed handling of two token ir protocols
14 - Removed all frequency analysis frame detection stuff for LCD's it was to complicated, and added ir_flip_eyes to support inverting the eye signals if frame_delay is triggering next frames eye instead
13 - Improved sensor logging and added opt_sensor_filter_mode
12 - Added support for OPT_SENSOR_IGNORE_ALL_DUPLICATES to help with displays with strange timings and PWM values
11 - Added support for OPT_SENSOR_ENABLE_STREAM_READINGS_TO_SERIAL to help debug timings on new displays
10 - First official tracked version
*/

struct EEPROMSettings
{
  uint32_t check_value;
  uint8_t version;
  uint8_t ir_glasses_selected;
  uint16_t ir_frame_delay;
  uint16_t ir_frame_duration;
  uint16_t ir_signal_spacing;
  uint32_t opt_sensor_block_signal_detection_delay;
  uint32_t opt_sensor_min_threshold_value_to_activate;
  uint8_t opt_sensor_detection_threshold_high;
  uint8_t opt_sensor_enable_ignore_during_ir;
  uint8_t opt_sensor_enable_duplicate_realtime_reporting;
  uint8_t opt_sensor_output_stats;          // was opt_sensor_enable_ignore_during_ir;
  uint8_t ir_drive_mode;                    // was opt_sensor_enable_duplicate_realtime_reporting;
  uint8_t opt_sensor_ignore_all_duplicates; // was opt_sensor_output_stats;
  uint8_t opt_sensor_filter_mode;
  uint8_t ir_flip_eyes;                       // was opt_sensor_block_n_subsequent_duplicates;
  uint8_t opt_sensor_detection_threshold_low; // was opt_sensor_ignore_all_duplicates;
  uint8_t ir_average_timing_mode;             // was opt_sensor_filter_mode;
  uint16_t target_frametime;
};

#endif /* _SETTINGS_H_ */