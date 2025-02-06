/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "usb_trigger.h"

#define FRAME_HISTORY_SIZE 64
#define FRAME_HISTORY_SHIFT 6 // Log2(FRAME_HISTORY_SIZE) for efficient division

uint32_t usb_trigger_current_time;
uint32_t usb_trigger_frametime_start_time = 0;
bool usb_trigger_frametime_start_time_set = false;
bool usb_trigger_frametime_average_set = false;
bool usb_trigger_time_history_filled = false;

uint32_t usb_trigger_time_history[FRAME_HISTORY_SIZE] = {0};
uint8_t usb_trigger_time_history_index = 0;
uint32_t usb_trigger_frametime_average_shifted = 0;

uint16_t logger_counter = 0;

void usb_trigger_init(void)
{
    usb_trigger_frametime_start_time = 0;
    usb_trigger_frametime_start_time_set = false;
    usb_trigger_frametime_average_set = false;
    usb_trigger_time_history_filled = false; // Reset flag
    memset((void *)usb_trigger_time_history, 0, sizeof(usb_trigger_time_history));
    usb_trigger_time_history_index = 0;
    usb_trigger_frametime_average_shifted = 0;
}

void usb_trigger_stop(void)
{
}

void usb_trigger_settings_changed(void)
{
    usb_trigger_frametime_start_time = 0;
    usb_trigger_frametime_start_time_set = false;
    usb_trigger_frametime_average_set = false;
    usb_trigger_time_history_filled = false; // Reset flag
    memset((void *)usb_trigger_time_history, 0, sizeof(usb_trigger_time_history));
    usb_trigger_time_history_index = 0;
    usb_trigger_frametime_average_shifted = 0;
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

    usb_trigger_current_time = micros();

    if (usb_trigger_frametime_start_time_set == true)
    {
        uint16_t new_frametime = usb_trigger_current_time - usb_trigger_frametime_start_time;

        if (new_frametime > (target_frametime << 1))
        {
            // no updates for more than 1 frame reset all averaging counters.
            usb_trigger_frametime_average_set = false;
            usb_trigger_time_history_filled = false; // Reset flag
            usb_trigger_time_history_index = 0;
            usb_trigger_frametime_average_shifted = 0;
        }

        if (usb_trigger_frametime_average_set)
        {
            // Rolling average update using bit shifting (normalized)
            uint32_t new_usb_trigger_frametime_average_shifted = usb_trigger_frametime_average_shifted - (usb_trigger_frametime_average_shifted >> FRAME_HISTORY_SHIFT);
            new_usb_trigger_frametime_average_shifted += new_frametime;

            // Ensure new_frametime is within 30 microseconds of the target before updating
            uint16_t new_usb_trigger_frametime_average = new_usb_trigger_frametime_average_shifted >> FRAME_HISTORY_SHIFT;
            if (target_frametime == 0 || (new_usb_trigger_frametime_average >= target_frametime - 60 && new_usb_trigger_frametime_average <= target_frametime + 60))
            {
                usb_trigger_frametime_average_shifted = new_usb_trigger_frametime_average_shifted;
            }

            // **Compute Phase Correction Using a 32-Frame Lookback (only if history is filled)**
            if (usb_trigger_time_history_filled)
            {
                uint8_t past_index = (usb_trigger_time_history_index - FRAME_HISTORY_SIZE) & (FRAME_HISTORY_SIZE - 1);
                uint32_t expected_time = usb_trigger_time_history[past_index] + usb_trigger_frametime_average_shifted;
                int16_t time_error = (int16_t)(usb_trigger_current_time - expected_time);
                int16_t frame_delay_adjustment = time_error - (time_error >> 4); // Correction (~15/16 of error)

                // Call IR signal process trigger with improved phase adjustment
                ir_signal_process_trigger(left_eye, usb_trigger_frametime_average_shifted >> FRAME_HISTORY_SHIFT, frame_delay_adjustment);

                //*
                logger_counter++;
                if (logger_counter % 128 == 0)
                {
                    Serial.print(usb_trigger_current_time);
                    Serial.print(",");
                    Serial.print(expected_time);
                    Serial.print(",");
                    Serial.print(time_error);
                    Serial.print(",");
                    Serial.print(frame_delay_adjustment);
                    Serial.print(",");
                    Serial.print(usb_trigger_frametime_average_shifted >> FRAME_HISTORY_SHIFT);
                    Serial.println();
                }
                //*/
            }
        }
        else
        {
            if (target_frametime == 0 || (new_frametime >= target_frametime - 100 && new_frametime <= target_frametime + 100))
            {
                usb_trigger_frametime_average_shifted = ((uint32_t)new_frametime) << FRAME_HISTORY_SHIFT; // Store unnormalized value
                usb_trigger_frametime_average_set = true;
            }
        }

        // **Update Rolling Time History**
        usb_trigger_time_history[usb_trigger_time_history_index] = usb_trigger_current_time;              // Store new value
        usb_trigger_time_history_index = (usb_trigger_time_history_index + 1) & (FRAME_HISTORY_SIZE - 1); // Circular buffer

        // **Mark history as valid after collecting FRAME_HISTORY_SIZE entries**
        if (usb_trigger_time_history_index == 0)
        {
            usb_trigger_time_history_filled = true;
        }
    }

    usb_trigger_frametime_start_time = usb_trigger_current_time;
    usb_trigger_frametime_start_time_set = true;
}
