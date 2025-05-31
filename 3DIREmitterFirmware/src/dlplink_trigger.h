/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#ifndef _DLPLINK_TRIGGER_H_
#define _DLPLINK_TRIGGER_H_

#define DLPLINK_TRIGGER_POWER_CYCLE_AFTER_DELAY (uint32_t)(30000) // Power cycle the RF relay after n milliseconds of inactivity to ensure it is always running.
#define DLPLINK_TRIGGER_POWER_CYCLE_OFF_DURATION (uint32_t)(15000) // When power cycling the RF relay turn it off for n milliseconds

// D14
#define DLPLINK_RIGHT_SHUTTER_ACTIVE_D14 3
#define DDR_DLPLINK_RIGHT_SHUTTER_ACTIVE_D14 DDRB
#define PORT_DLPLINK_RIGHT_SHUTTER_ACTIVE_D14 PORTB
#define PIN_DLPLINK_RIGHT_SHUTTER_ACTIVE_D14 PINB

// D15
#define DLPLINK_RIGHT_SHUTTER_COMMON_D15 1
#define DDR_DLPLINK_RIGHT_SHUTTER_COMMON_D15 DDRB
#define PORT_DLPLINK_RIGHT_SHUTTER_COMMON_D15 PORTB
#define PIN_DLPLINK_RIGHT_SHUTTER_COMMON_D15 PINB

// D21
#define DLPLINK_MODULE_POWER_ON_D21 4
#define DDR_DLPLINK_MODULE_POWER_ON_D21 DDRF
#define PORT_DLPLINK_MODULE_POWER_ON_D21 PORTF
#define PIN_DLPLINK_MODULE_POWER_ON_D21 PINF

void dlplink_trigger_init(void);
void dlplink_trigger_stop(void);
void dlplink_trigger_check_cycle_power(void);
void dlplink_trigger_update(void);
void dlplink_trigger_push_power_button(uint32_t duration);

#endif /* _DLPLINK_TRIGGER_H_ */