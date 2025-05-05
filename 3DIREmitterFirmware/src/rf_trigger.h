/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#ifndef _RF_TRIGGER_H_
#define _RF_TRIGGER_H_

#define RF_TRIGGER_POWER_CYCLE_AFTER_DELAY (uint32_t)(600000) // Power cycle the RF relay after n milliseconds of inactivity to ensure it is always running.
#define RF_TRIGGER_POWER_CYCLE_OFF_DURATION (uint32_t)(5000)  // When power cycling the RF relay turn it off for n milliseconds

// D10
#define RF_LEFT_SHUTTER_ACTIVE_D10 6
#define DDR_RF_LEFT_SHUTTER_ACTIVE_D10 DDRB
#define PORT_RF_LEFT_SHUTTER_ACTIVE_D10 PORTB
#define PIN_RF_LEFT_SHUTTER_ACTIVE_D10 PINB

// D16
#define RF_LEFT_SHUTTER_COMMON_D16 2
#define DDR_RF_LEFT_SHUTTER_COMMON_D16 DDRB
#define PORT_RF_LEFT_SHUTTER_COMMON_D16 PORTB
#define PIN_RF_LEFT_SHUTTER_COMMON_D16 PINB

// D14
#define RF_RIGHT_SHUTTER_ACTIVE_D14 3
#define DDR_RF_RIGHT_SHUTTER_ACTIVE_D14 DDRB
#define PORT_RF_RIGHT_SHUTTER_ACTIVE_D14 PORTB
#define PIN_RF_RIGHT_SHUTTER_ACTIVE_D14 PINB

// D15
#define RF_RIGHT_SHUTTER_COMMON_D15 1
#define DDR_RF_RIGHT_SHUTTER_COMMON_D15 DDRB
#define PORT_RF_RIGHT_SHUTTER_COMMON_D15 PORTB
#define PIN_RF_RIGHT_SHUTTER_COMMON_D15 PINB

// D21
#define RF_MODULE_POWER_ON_D21 4
#define DDR_RF_MODULE_POWER_ON_D21 DDRF
#define PORT_RF_MODULE_POWER_ON_D21 PORTF
#define PIN_RF_MODULE_POWER_ON_D21 PINF

void rf_trigger_init(void);
void rf_trigger_stop(void);
void rf_trigger_check_cycle_power(void);
void rf_trigger_update(void);

#endif /* _RF_TRIGGER_H_ */