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
bool usb_trigger_frametime_average_updated = false;
uint8_t usb_trigger_last_update_left_eye = 0;
bool usb_trigger_last_update_left_eye_set = false;

void usb_trigger_Init(void)
{
    usb_trigger_frametime_frame_counter = 0;
    usb_trigger_frametime_start_time = 0;
    usb_trigger_frametime_average = 0;
    usb_trigger_frametime_average_set = false;
    usb_trigger_resync_average_timing_mode_required = false;
    usb_trigger_average_timing_mode_resync = false;
    usb_trigger_frametime_average_updated = false;
}

void usb_trigger_SettingsChanged(void)
{
    usb_trigger_frametime_frame_counter = 0;
    usb_trigger_frametime_start_time = 0;
}

void usb_trigger_Update(uint8_t left_eye)
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
        usb_trigger_current_time = 0;
        if (usb_trigger_current_time == 0)
        {
            usb_trigger_current_time = micros();
        }
        if (usb_trigger_last_update_left_eye_set)
        {
            if (usb_trigger_last_update_left_eye == left_eye)
            {
                usb_trigger_resync_average_timing_mode_required = true;
            }
        }
        if (usb_trigger_frametime_average_set && (usb_trigger_resync_average_timing_mode_required))
        {
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
            bitSet(PORT_DEBUG_AVERAGE_TIMING_MODE_RESYNC_D14, DEBUG_AVERAGE_TIMING_MODE_RESYNC_D14);
#endif
            ir_signal_process_trigger(left_eye, usb_trigger_frametime_average);
            usb_trigger_resync_average_timing_mode_required = false;
        }
        if (usb_trigger_frametime_frame_counter == USB_FRAMETIME_COUNT_PERIOD)
        {
            uint16_t new_frametime_average = (usb_trigger_current_time - usb_trigger_frametime_start_time) >> USB_FRAMETIME_COUNT_PERIOD_2PN;
            if (target_frametime == 0 || (target_frametime - 30 < new_frametime_average && new_frametime_average < target_frametime + 30))
            {
                // if a target_frametime is specified we only permit deviation by 30 us above or below the target.
                // For a 120hz display this equates to 120 +/- 0.438
                // With a 120hz display and USB_FRAMETIME_COUNT_PERIOD_2PN of 128 a single duplicate uncounted frame would result in an average frametime of 8333.3333×121÷120 = 8402.777744167 which is 70 microseconds longer and thus would be ignored.
                usb_trigger_frametime_average = new_frametime_average;
                usb_trigger_frametime_average_set = true;
                usb_trigger_frametime_average_updated = true;
            }
            if (usb_trigger_frametime_average_set)
            {
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
                bitSet(PORT_DEBUG_AVERAGE_TIMING_MODE_RESYNC_D14, DEBUG_AVERAGE_TIMING_MODE_RESYNC_D14);
#endif
                ir_signal_process_trigger(left_eye, usb_trigger_frametime_average);
                usb_trigger_resync_average_timing_mode_required = false;
            }
            usb_trigger_frametime_frame_counter = 0;
        }
        if (usb_trigger_frametime_frame_counter == 0)
        {
            usb_trigger_frametime_start_time = usb_trigger_current_time;
        }
        usb_trigger_frametime_frame_counter++;
        usb_trigger_last_update_left_eye = left_eye;
        usb_trigger_last_update_left_eye_set = true;
    }
    else
    {
        ir_signal_process_trigger(left_eye, usb_trigger_frametime_average);
    }
}
