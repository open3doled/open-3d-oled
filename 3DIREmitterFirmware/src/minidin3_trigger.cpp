/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "minidin3_trigger.h"

void minidin3_trigger_init(void)
{
  // Input
  // https://medesign.seas.upenn.edu/index.php/Guides/MaEvArM-pcint
  // Set pin as input
  bitClear(DDR_MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10, MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10);
  // Enable pull-up resistor on the pin
  // bitSet(PORT_MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10, MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10);
  // Disable pull-up resistor on the pin
  //*
  bitClear(PORT_MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10, MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10);
  //*/
  // Enable pin change interrupt for PCINT0
  bitSet(PCICR, PCIE0);
  // Enable interrupt on the specific pin
  bitSet(PCMSK0, PCINT6);
  // Enable global interrupts
  sei();
}

void minidin3_trigger_stop(void)
{
  bitClear(PCICR, PCIE0);
  bitClear(PCMSK0, PCINT6);
}

void minidin3_trigger_settings_changed(void)
{
}

void minidin3_trigger_update(void)
{
  uint8_t minidin3_3d_stereo_sync_left_open = bitRead(PIN_MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10, MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10);
  if (minidin3_3d_stereo_sync_left_open == 1)
  {
    ir_signal_process_trigger(1);
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    bitClear(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
    bitSet(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
#endif
  }
  else
  {
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    bitClear(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
    bitSet(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
#endif
    ir_signal_process_trigger(0);
  }
}

// Pin change interrupt service routine
ISR(PCINT0_vect)
{
  minidin3_trigger_update();
}