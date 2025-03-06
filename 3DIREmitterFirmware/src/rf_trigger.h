/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#ifndef _RF_TRIGGER_H_
#define _RF_TRIGGER_H_

#define RF_TRIGGER_POWER_CYCLE_AFTER_DELAY (uint32_t)(600000) // Power cycle the RF relay after n milliseconds of inactivity to ensure it is always running.
#define RF_TRIGGER_POWER_CYCLE_OFF_DURATION (uint32_t)(5000)  // When power cycling the RF relay turn it off for n milliseconds

void rf_trigger_init(void);
void rf_trigger_stop(void);
void rf_trigger_check_cycle_power(void);
void rf_trigger_update(void);

#endif /* _RF_TRIGGER_H_ */