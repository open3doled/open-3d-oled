/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "usb_trigger.h"

uint32_t usb_trigger_current_time;
uint16_t usb_trigger_frametime_frame_counter = 0;
uint32_t usb_trigger_frametime_start_time = 0;
uint16_t usb_trigger_frametime_average = 0;
bool usb_trigger_frametime_average_set = false;
bool usb_trigger_resync_average_timing_mode_required = false;
bool usb_trigger_average_timing_mode_resync = false;
uint8_t usb_trigger_last_update_left_eye = 0;
bool usb_trigger_last_update_left_eye_set = false;

void usb_trigger_init(void)
{
    usb_trigger_frametime_frame_counter = 0;
    usb_trigger_frametime_start_time = 0;
    usb_trigger_frametime_average = 0;
    usb_trigger_frametime_average_set = false;
    usb_trigger_resync_average_timing_mode_required = false;
    usb_trigger_average_timing_mode_resync = false;
}

void usb_trigger_stop(void)
{
}

void usb_trigger_settings_changed(void)
{
    usb_trigger_frametime_frame_counter = 0;
    usb_trigger_frametime_start_time = 0;
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

    if (ir_average_timing_mode == 1)
    {
        usb_trigger_current_time = micros();

        if (usb_trigger_last_update_left_eye_set && usb_trigger_last_update_left_eye == left_eye)
        {
            usb_trigger_resync_average_timing_mode_required = true;
        }

        uint16_t new_frametime = usb_trigger_current_time - usb_trigger_frametime_start_time;

        if (usb_trigger_frametime_average_set)
        {
            // Rolling average update using bit shifting
            // Equivalent to: avg = (15/16) * avg + (1/16) * new_value
            uint16_t new_usb_trigger_frametime_average = usb_trigger_frametime_average - (usb_trigger_frametime_average >> 4); // Subtract 1/16 of current average
            new_usb_trigger_frametime_average += new_frametime >> 4;                                                         // Add 1/16 of new frametime

            // Ensure new_frametime is within 30 microseconds of the target before updating
            if (target_frametime == 0 || (new_usb_trigger_frametime_average >= target_frametime - 30 && new_usb_trigger_frametime_average <= target_frametime + 30))
            {
                usb_trigger_frametime_average = new_usb_trigger_frametime_average;
            }

            // Call IR signal process trigger every time
            ir_signal_process_trigger(left_eye, usb_trigger_frametime_average);
        }
        else
        {
            // Ensure new_frametime is within 100 microseconds of the target before updating
            if (target_frametime == 0 || (new_frametime >= target_frametime - 100 && new_frametime <= target_frametime + 100))
            {
                // First-time initialization
                usb_trigger_frametime_average = new_frametime;
                usb_trigger_frametime_average_set = true;
            }
        }

        usb_trigger_frametime_start_time = usb_trigger_current_time;
        usb_trigger_last_update_left_eye = left_eye;
        usb_trigger_last_update_left_eye_set = true;
    }
    else
    {
        ir_signal_process_trigger(left_eye, usb_trigger_frametime_average);
    }
}