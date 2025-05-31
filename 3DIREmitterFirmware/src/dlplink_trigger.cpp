/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 *
 * This trigger module is for using the dlplink glasses module directly to trigger instead of an opt module.
 * It is designed to work with the JX-30 right eye active and common lines with a 50% voltage divider to take them from 10v to 5v
 * It also needs to use A3 to power on the module by pulling it to ground if no dlp link signal is detected.
 * It should leave it as floating when it is not pulling to ground as the module uses 3.3V logic levels not 5V like the atmega32u4 module.
 *
 */

#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "dlplink_trigger.h"

uint8_t last_dlplink_right_shutter_active = 0;
uint8_t last_dlplink_right_shutter_common = 0;
volatile uint32_t dlplink_trigger_current_time = 0;
volatile uint32_t last_dlplink_trigger_shutter_signal_time = 0;
uint32_t last_dlplink_trigger_power_cycle_time = 0;
uint8_t last_dlplink_trigger_power_cycle_action = 0;

void dlplink_trigger_init(void)
{
  last_dlplink_right_shutter_active = 0;
  last_dlplink_right_shutter_common = 0;
  cli();
  dlplink_trigger_current_time = millis();
  last_dlplink_trigger_shutter_signal_time = dlplink_trigger_current_time;
  sei();
  last_dlplink_trigger_power_cycle_time = dlplink_trigger_current_time;
  last_dlplink_trigger_power_cycle_action = 0;

  bitSet(DDR_DLPLINK_MODULE_POWER_ON_D21, DLPLINK_MODULE_POWER_ON_D21);
  bitSet(PORT_DLPLINK_MODULE_POWER_ON_D21, DLPLINK_MODULE_POWER_ON_D21);
  delay(1000); // delay 1 second so that the button registering logic can register the off state so our press to turn the unit on works
  // Module Power On
  dlplink_trigger_push_power_button(200); // power on dlplink module

  // Input
  // https://medesign.seas.upenn.edu/index.php/Guides/MaEvArM-pcint
  // Set pin as input
  bitClear(DDR_DLPLINK_RIGHT_SHUTTER_ACTIVE_D14, DLPLINK_RIGHT_SHUTTER_ACTIVE_D14);
  bitClear(DDR_DLPLINK_RIGHT_SHUTTER_COMMON_D15, DLPLINK_RIGHT_SHUTTER_COMMON_D15);
  // Enable pull-up resistor on the pin
  // bitSet(PORT_DLPLINK_RIGHT_SHUTTER_ACTIVE_D14, DLPLINK_RIGHT_SHUTTER_ACTIVE_D14);
  // bitSet(PORT_DLPLINK_RIGHT_SHUTTER_COMMON_D15, DLPLINK_RIGHT_SHUTTER_COMMON_D15);
  // Disable pull-up resistor on the pin
  //*
  // bitClear(PORT_DLPLINK_RIGHT_SHUTTER_ACTIVE_D14, DLPLINK_RIGHT_SHUTTER_ACTIVE_D14);
  // bitClear(PORT_DLPLINK_RIGHT_SHUTTER_COMMON_D15, DLPLINK_RIGHT_SHUTTER_COMMON_D15);
  //*/
  cli();
  // Enable pin change interrupt for PCINT0
  bitSet(PCICR, PCIE0);
  // Enable interrupt on the specific pin
  bitSet(PCMSK0, PCINT3);
  bitSet(PCMSK0, PCINT1);
  // Enable global interrupts
  sei();
}

void dlplink_trigger_stop(void)
{
  cli();
  // Disable pin change interrupt for PCINT0
  bitClear(PCICR, PCIE0);
  // Disable interrupt on the specific pin
  bitClear(PCMSK0, PCINT3);
  bitClear(PCMSK0, PCINT1);
  // Enable global interrupts
  sei();

  dlplink_trigger_push_power_button(4000); // power off dlplink module

  bitClear(PORT_DLPLINK_RIGHT_SHUTTER_ACTIVE_D14, DLPLINK_RIGHT_SHUTTER_ACTIVE_D14);
  bitClear(PORT_DLPLINK_RIGHT_SHUTTER_COMMON_D15, DLPLINK_RIGHT_SHUTTER_COMMON_D15);

  bitClear(PORT_DLPLINK_MODULE_POWER_ON_D21, DLPLINK_MODULE_POWER_ON_D21);
  bitClear(DDR_DLPLINK_MODULE_POWER_ON_D21, DLPLINK_MODULE_POWER_ON_D21);
}

void dlplink_trigger_check_cycle_power(void)
{
  uint32_t dlplink_trigger_current_time_temp = millis();
  cli();
  dlplink_trigger_current_time = dlplink_trigger_current_time_temp;
  uint32_t last_dlplink_trigger_shutter_signal_time_temp = last_dlplink_trigger_shutter_signal_time;
  sei();
  if (last_dlplink_trigger_power_cycle_action == 0 &&
      dlplink_trigger_current_time_temp > last_dlplink_trigger_shutter_signal_time_temp + DLPLINK_TRIGGER_POWER_CYCLE_AFTER_DELAY &&
      dlplink_trigger_current_time_temp > last_dlplink_trigger_power_cycle_time + DLPLINK_TRIGGER_POWER_CYCLE_AFTER_DELAY)
  {
    dlplink_trigger_push_power_button(4000); // power off dlplink module
    last_dlplink_trigger_power_cycle_time = dlplink_trigger_current_time_temp;
    last_dlplink_trigger_power_cycle_action = 1;
  }
  if (last_dlplink_trigger_power_cycle_action == 1 && dlplink_trigger_current_time_temp > last_dlplink_trigger_power_cycle_time + DLPLINK_TRIGGER_POWER_CYCLE_OFF_DURATION)
  {
    dlplink_trigger_push_power_button(200); // power on dlplink module
    last_dlplink_trigger_power_cycle_action = 0;
  }
}

void dlplink_trigger_update(void)
{
  uint8_t dlplink_right_shutter_active = bitRead(PIN_DLPLINK_RIGHT_SHUTTER_ACTIVE_D14, DLPLINK_RIGHT_SHUTTER_ACTIVE_D14);
  uint8_t dlplink_right_shutter_common = bitRead(PIN_DLPLINK_RIGHT_SHUTTER_COMMON_D15, DLPLINK_RIGHT_SHUTTER_COMMON_D15);
  if ((dlplink_trigger_current_time - last_dlplink_trigger_shutter_signal_time) < 2)
  {
    return;
  }
  last_dlplink_trigger_shutter_signal_time = dlplink_trigger_current_time;
  if (dlplink_right_shutter_active != last_dlplink_right_shutter_active)
  {
    ir_signal_process_trigger(1);
    last_dlplink_right_shutter_active = dlplink_right_shutter_active;
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    bitSet(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
    bitClear(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
#endif
  }
  if (dlplink_right_shutter_common != last_dlplink_right_shutter_common)
  {
    ir_signal_process_trigger(0);
    last_dlplink_right_shutter_common = dlplink_right_shutter_common;
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    bitClear(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
    bitSet(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
#endif
  }
}

void dlplink_trigger_push_power_button(uint32_t duration)
{
  bitClear(PORT_DLPLINK_MODULE_POWER_ON_D21, DLPLINK_MODULE_POWER_ON_D21);
  delay(duration);
  bitSet(PORT_DLPLINK_MODULE_POWER_ON_D21, DLPLINK_MODULE_POWER_ON_D21);
}