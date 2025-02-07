/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "usb_trigger.h"

void usb_trigger_init(void)
{
}

void usb_trigger_stop(void)
{
}

void usb_trigger_settings_changed(void)
{
}

void usb_trigger_update(uint8_t left_eye)
{
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    if (left_eye)
    {
        bitClear(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
        bitSet(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
    }
    else
    {
        bitClear(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
        bitSet(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
    }
#endif

    // Call IR signal process trigger with improved phase adjustment
    ir_signal_process_trigger(left_eye);
    /*
    #ifdef ENABLE_DEBUG_PIN_OUTPUTS
        bitClear(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
        bitClear(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
    #endif
    //*/
}
