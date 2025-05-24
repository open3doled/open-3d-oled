/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "rf_trigger.h"

uint32_t rf_trigger_current_time = 0;
uint32_t last_rf_trigger_shutter_signal_time = 0;
uint32_t last_rf_trigger_power_cycle_time = 0;

void rf_trigger_init(void)
{
  rf_trigger_current_time = millis();
  last_rf_trigger_shutter_signal_time = rf_trigger_current_time;
  last_rf_trigger_power_cycle_time = rf_trigger_current_time;

  // Module Power On
  bitSet(DDR_RF_MODULE_POWER_ON_D21, RF_MODULE_POWER_ON_D21);
  bitSet(PORT_RF_MODULE_POWER_ON_D21, RF_MODULE_POWER_ON_D21);

  // Input
  // https://medesign.seas.upenn.edu/index.php/Guides/MaEvArM-pcint
  // Set pin as input
  bitClear(DDR_RF_LEFT_SHUTTER_ACTIVE_D10, RF_LEFT_SHUTTER_ACTIVE_D10);
  bitClear(DDR_RF_LEFT_SHUTTER_COMMON_D16, RF_LEFT_SHUTTER_COMMON_D16);
  bitClear(DDR_RF_RIGHT_SHUTTER_ACTIVE_D14, RF_RIGHT_SHUTTER_ACTIVE_D14);
  bitClear(DDR_RF_RIGHT_SHUTTER_COMMON_D15, RF_RIGHT_SHUTTER_COMMON_D15);
  // Enable pull-up resistor on the pin
  bitSet(PORT_RF_LEFT_SHUTTER_ACTIVE_D10, RF_LEFT_SHUTTER_ACTIVE_D10);
  bitSet(PORT_RF_LEFT_SHUTTER_COMMON_D16, RF_LEFT_SHUTTER_COMMON_D16);
  bitSet(PORT_RF_RIGHT_SHUTTER_ACTIVE_D14, RF_RIGHT_SHUTTER_ACTIVE_D14);
  bitSet(PORT_RF_RIGHT_SHUTTER_COMMON_D15, RF_RIGHT_SHUTTER_COMMON_D15);
  // Disable pull-up resistor on the pin
  //*
  bitClear(PORT_RF_LEFT_SHUTTER_ACTIVE_D10, RF_LEFT_SHUTTER_ACTIVE_D10);
  bitClear(PORT_RF_LEFT_SHUTTER_COMMON_D16, RF_LEFT_SHUTTER_COMMON_D16);
  bitClear(PORT_RF_RIGHT_SHUTTER_ACTIVE_D14, RF_RIGHT_SHUTTER_ACTIVE_D14);
  bitClear(PORT_RF_RIGHT_SHUTTER_COMMON_D15, RF_RIGHT_SHUTTER_COMMON_D15);
  //*/
  cli();
  // Enable pin change interrupt for PCINT0
  bitSet(PCICR, PCIE0);
  // Enable interrupt on the specific pin
  bitSet(PCMSK0, PCINT6);
  bitSet(PCMSK0, PCINT2);
  bitSet(PCMSK0, PCINT3);
  bitSet(PCMSK0, PCINT1);
  // Enable global interrupts
  sei();
}

void rf_trigger_stop(void)
{
  cli();
  // Disable pin change interrupt for PCINT0
  bitClear(PCICR, PCIE0);
  // Disable interrupt on the specific pin
  bitClear(PCMSK0, PCINT6);
  bitClear(PCMSK0, PCINT2);
  bitClear(PCMSK0, PCINT3);
  bitClear(PCMSK0, PCINT1);
  // Enable global interrupts
  sei();

  bitClear(PORT_RF_LEFT_SHUTTER_ACTIVE_D10, RF_LEFT_SHUTTER_ACTIVE_D10);
  bitClear(PORT_RF_LEFT_SHUTTER_COMMON_D16, RF_LEFT_SHUTTER_COMMON_D16);
  bitClear(PORT_RF_RIGHT_SHUTTER_ACTIVE_D14, RF_RIGHT_SHUTTER_ACTIVE_D14);
  bitClear(PORT_RF_RIGHT_SHUTTER_COMMON_D15, RF_RIGHT_SHUTTER_COMMON_D15);

  bitClear(PORT_RF_MODULE_POWER_ON_D21, RF_MODULE_POWER_ON_D21);
  bitClear(DDR_RF_MODULE_POWER_ON_D21, RF_MODULE_POWER_ON_D21);
}

void rf_trigger_check_cycle_power(void)
{
  rf_trigger_current_time = millis();
  if (rf_trigger_current_time > last_rf_trigger_shutter_signal_time + RF_TRIGGER_POWER_CYCLE_AFTER_DELAY &&
      rf_trigger_current_time > last_rf_trigger_power_cycle_time + RF_TRIGGER_POWER_CYCLE_AFTER_DELAY)
  {
    bitClear(PORT_RF_MODULE_POWER_ON_D21, RF_MODULE_POWER_ON_D21); // power off rf relay
    last_rf_trigger_power_cycle_time = rf_trigger_current_time;
  }
  if (rf_trigger_current_time > last_rf_trigger_power_cycle_time + RF_TRIGGER_POWER_CYCLE_OFF_DURATION)
  {
    bitSet(PORT_RF_MODULE_POWER_ON_D21, RF_MODULE_POWER_ON_D21); // power on rf relay
  }
}

void rf_trigger_update(void)
{
  uint8_t rf_left_shutter_active = bitRead(PIN_RF_LEFT_SHUTTER_ACTIVE_D10, RF_LEFT_SHUTTER_ACTIVE_D10);
  uint8_t rf_left_shutter_common = bitRead(PIN_RF_LEFT_SHUTTER_COMMON_D16, RF_LEFT_SHUTTER_COMMON_D16);
  uint8_t rf_right_shutter_active = bitRead(PIN_RF_RIGHT_SHUTTER_ACTIVE_D14, RF_RIGHT_SHUTTER_ACTIVE_D14);
  uint8_t rf_right_shutter_common = bitRead(PIN_RF_RIGHT_SHUTTER_COMMON_D15, RF_RIGHT_SHUTTER_COMMON_D15);
  if (rf_left_shutter_active == 0 && rf_left_shutter_common == 0)
  {
    ir_signal_process_trigger(1);
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    bitSet(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
#endif
  }
  else
  {
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    bitClear(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
#endif
  }
  if (rf_right_shutter_active == 0 && rf_right_shutter_common == 0)
  {
    ir_signal_process_trigger(0);
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    bitSet(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
#endif
  }
  else
  {
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    bitClear(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
#endif
  }
  rf_trigger_current_time = millis();
  last_rf_trigger_shutter_signal_time = rf_trigger_current_time;
}
