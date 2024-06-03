/*
* Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
*/

/*
* TODO:
* 
*
*/

#include <Arduino.h>
#include <EEPROM.h>

#include "settings.h"
#include "ir_signal.h"
#include "opt_sensor.h"

static uint32_t next_print;

String input;
uint32_t current_time;
#ifdef ENABLE_LOOP_TOGGLE_DEBUG_PIN_D9
bool loop_toggle = 0;
#endif

void setup()
{
    Serial.begin(118200);
    //Serial.begin(460800);
    Serial.println("+startup");
    bitSet(DDR_LED_IR_D3, LED_IR_D3);
    #ifdef ENABLE_DEBUG_PIN_OUTPUTS
    //#if (defined(OPT_SENSOR_ENABLE_IGNORE_DURING_IR) && defined(OPT_SENSOR_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2))
    bitSet(DDR_DEBUG_PORT_D2, DEBUG_PORT_D2);
    //#endif
    bitSet(DDR_DEBUG_PORT_D9, DEBUG_PORT_D9);
    bitSet(DDR_DEBUG_PORT_D15, DEBUG_PORT_D15);
    bitSet(DDR_DEBUG_PWM_READING_LEFT_D6, DEBUG_PWM_READING_LEFT_D6);
    bitSet(DDR_DEBUG_PWM_READING_RIGHT_D10, DEBUG_PWM_READING_RIGHT_D10);
    bitSet(DDR_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
    bitSet(DDR_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
    bitSet(DDR_DEBUG_ACTIVATE_LEFT_D7, DEBUG_ACTIVATE_LEFT_D7);
    bitSet(DDR_DEBUG_ACTIVATE_RIGHT_D8, DEBUG_ACTIVATE_RIGHT_D8);
    bitSet(DDR_DEBUG_DUPLICATE_FRAME_D16, DEBUG_DUPLICATE_FRAME_D16);
    bitSet(DDR_DEBUG_AVERAGE_TIMING_MODE_RESYNC_D14, DEBUG_AVERAGE_TIMING_MODE_RESYNC_D14);
    #endif
    #ifdef ENABLE_DEBUG_STATUS_LEDS
    bitSet(DDR_STATUS_LED_D2, STATUS_LED_D2);
    bitSet(DDR_STATUS_LED_D4, STATUS_LED_D4);
    bitSet(DDR_STATUS_LED_D5, STATUS_LED_D5);
    #ifdef ENABLE_DEBUG_STATUS_FLASH_D2_ON_STARTUP
    for (uint8_t i = 0; i < ENABLE_DEBUG_STATUS_FLASH_D2_ON_STARTUP; i++) 
    {
        bitSet(PORT_STATUS_LED_D2, STATUS_LED_D2);
        delay(500);
        bitClear(PORT_STATUS_LED_D2, STATUS_LED_D2);
        delay(500);
    }
    #endif
    #endif
    ir_signal_init();
    opt_sensor_Init();
    EEPROMSettings eeprom_settings;
    EEPROM.get(EEPROM_SETTING_ADDRESS, eeprom_settings);
    if (eeprom_settings.check_value == EEPROM_SETTING_CHECKVALUE)
    {
        if (eeprom_settings.version > 3 && eeprom_settings.version < 14) 
        {
            ir_glasses_selected = eeprom_settings.ir_glasses_selected;
            ir_frame_delay = eeprom_settings.ir_frame_delay;
            ir_frame_duration = eeprom_settings.ir_frame_duration;
            ir_signal_spacing = eeprom_settings.ir_signal_spacing;
            opt_sensor_block_signal_detection_delay = eeprom_settings.opt_sensor_block_signal_detection_delay;
            opt_sensor_min_threshold_value_to_activate = eeprom_settings.opt_sensor_min_threshold_value_to_activate;
            opt_sensor_detection_threshold_high = eeprom_settings.opt_sensor_detection_threshold_high;
            opt_sensor_enable_ignore_during_ir = eeprom_settings.opt_sensor_output_stats;
            opt_sensor_enable_duplicate_realtime_reporting = eeprom_settings.target_frametime;
            opt_sensor_output_stats = eeprom_settings.opt_sensor_ignore_all_duplicates;
            if (eeprom_settings.version >= 12) 
            {
                opt_sensor_ignore_all_duplicates = eeprom_settings.opt_sensor_detection_threshold_low;
            }
            if (eeprom_settings.version >= 13)
            {
                opt_sensor_filter_mode = eeprom_settings.ir_average_timing_mode;
;
            }
        }
        else
        {
            ir_glasses_selected = eeprom_settings.ir_glasses_selected;
            ir_frame_delay = eeprom_settings.ir_frame_delay;
            ir_frame_duration = eeprom_settings.ir_frame_duration;
            ir_signal_spacing = eeprom_settings.ir_signal_spacing;
            opt_sensor_block_signal_detection_delay = eeprom_settings.opt_sensor_block_signal_detection_delay;
            opt_sensor_min_threshold_value_to_activate = eeprom_settings.opt_sensor_min_threshold_value_to_activate;
            opt_sensor_detection_threshold_high = eeprom_settings.opt_sensor_detection_threshold_high;
            opt_sensor_enable_ignore_during_ir = eeprom_settings.opt_sensor_enable_ignore_during_ir;
            opt_sensor_enable_duplicate_realtime_reporting = eeprom_settings.opt_sensor_enable_duplicate_realtime_reporting;
            opt_sensor_output_stats = eeprom_settings.opt_sensor_output_stats;
            opt_sensor_ignore_all_duplicates = eeprom_settings.opt_sensor_ignore_all_duplicates;
            opt_sensor_filter_mode = eeprom_settings.opt_sensor_filter_mode;
            ir_flip_eyes = eeprom_settings.ir_flip_eyes;
            if (eeprom_settings.version >= 16)
            {
                opt_sensor_detection_threshold_low = eeprom_settings.opt_sensor_detection_threshold_low;
            }
            if (eeprom_settings.version >= 17)
            {
                ir_average_timing_mode = eeprom_settings.ir_average_timing_mode;
            }
            if (eeprom_settings.version >= 18) 
            {
                target_frametime = eeprom_settings.target_frametime;
                pwm_backlight_frequency = eeprom_settings.pwm_backlight_frequency;
                update_pwm_pulses_per_frame();
            }
        }

        Serial.println("eeprom read_settings");
    }
    Serial.println("init complete");
}

void loop()
{
    #ifdef ENABLE_DEBUG_PIN_OUTPUTS
    #ifdef ENABLE_LOOP_TOGGLE_DEBUG_PIN_D9
    loop_toggle = !loop_toggle;
    if (loop_toggle)
    {
        bitSet(PORT_DEBUG_PORT_D9, DEBUG_PORT_D9);
    }
    else
    {
        bitClear(PORT_DEBUG_PORT_D9, DEBUG_PORT_D9);
    }
    #endif
    #endif

    while (Serial.available() > 0) {
        char d = Serial.read();
        input.concat(d);
        //Serial.println(input);
        if (d == '\n') {
            uint8_t command = 0;
            uint8_t start = 0;
            uint8_t end;
            /*
            * Generally Applicable Parameters
            * 1) ir_glasses_selected - 0=Samsung07, 1=Xpand, 2=3DVision, 3=Sharp, 4=Sony, 5=Panasonic, 6=PanasonicCustom
            * 2) ir_frame_delay - how long to delay after getting tv signal before attempting to activate the shutter glasses (in microseconds)
            * 3) ir_frame_duration - how long to delay before switching de-activating the shutter glasses after activating them (in microseconds)
            * 4) ir_signal_spacing
            *   how long to delay after sending one signal before sending the next. 
            *   this is used to ensure the receiver is done handling one signal so as to not overload it. (default 200)
            * 14) ir_flip_eyes - 
            *   set this to 1 if you want to flip left and right eyes, this is useful if you need to use a high frame_delay 
            *   forcing this frame to actually trigger the glasses for the next frames opposite eye
            * 5) opt_sensor_block_signal_detection_delay - 
            *   how long to wait after a high tv signal on left or right before allowing another high tv signal on either 
            *   channel (in microseconds) this is useful to eliminating false triggers when the tv signal is decreasing in a noisy fashion.
            *   this is best set to slighly lower than the target refresh rate (about 80-90%).
            * 17) target_frametime -
            *   (the expected time to elapse between frames in microseconds this is 1000000/(monitor refresh rate))
            *   This is used to filter out invalid average frametimes computed when running with 'IR Average Timing Mode'. 
            *   With PWM displays and 'Ignore All Duplicates' enabled when you have a duplicate frame sent from your PC the sensor will detect a duplicate for each PWM backlight pulse, 
            *   in these situations the computed average frametime will be invalid so we just ignore it. (120 hz corresponds to 8333) (default 0 - don't filter average frametimes at all).
            * 11) pwm_backlight_frequency -
            *   (The number of cycles per second for the PWM backlight in the display)
            *   When running in 'IR Average Timing Mode' with PWM displays and 'Ignore All Duplicates' enabled this is used to deterine when the number of duplicates exceeds that of a single display frame.
            *   By making this determination we can resynchronize the built in timer on the next detected frame, thus only having 1 frame of ghosting.
            *   On many PWM backlit displays this is 120hz but you can also refer to the following table on RTINGs if you unsure https://www.rtings.com/tv/tools/table/138933
            *   (default 0 - unknown so we only resynchronize every second or so unless 'Ignore All Duplicates' is unchecked and this is not a PWM backlit display)
            * 12) opt_sensor_ignore_all_duplicates -
            *   (0=Disable, 1=Enable) On displays with too much jitter or PWM backlit displays you will need to set this to 1.
            *   The software will not send any signal to the glasses on what might be a duplicate frame but will instead ignore it. 
            *   This will mean that glasses only attempt resynchronization when the alternate eye trigger is sent by the display. 
            *   (If you are using a display without some form of BFI or a PWM backlit display it is highly recommended you enable this)
            *   (default 0 - off)
            * 6) opt_sensor_min_threshold_value_to_activate -
            *   the light intensities threshold value in a given threshold update cycle must exceed this value before the emitter will turn on.
            *   this setting is used to stop the emitter turning on when the TV is turned off.  (default 10)
            *   to low a value will cause it to turn on when the screen is black and trigger sporatically. 
            *   to high a value will mean that it never turns on.
            * 7) opt_sensor_detection_threshold_high - 
            *   the level (as a value between 1-255) above which an increasing light intensity is detected as the beggining of a new frame, 
            *   setting this lower will make the device aware of new frames earlier but also increase the likelihood of duplicate frame
            *   detection if the light intensity doesn't fall below this threshold before the opt_sensor_block_signal_detection_delay completes.
            *   (default 128)
            * 15) opt_sensor_detection_threshold_low - 
            *   the level (as a value between 1-255) below which the opposite trigger sensor must be before any triggers are detected.
            *   Setting this lower will ensure the device doesn't trigger while watching regular non stereoscopid content,
            *   but if set too low may result in the unit not triggering when it should (default 32).
            * 13) opt_sensor_filter_mode -
            *   this is used to apply custom filtering to the ADC readings to try and eliminate spurious noise currently there are only two modes.
            *   0 - off, 1 - check that the last three readings are trending in the same direction
            * 16) ir_average_timing_mode - 
            *   This is a special mode which will find the average screen refresh rate over 1 second, and use that to create a constant interval timer to trigger glasses.
            *   Some glasses appear to need a constant timer in order to synchronize with the ir signal, this may facilitate this.
            * 8) opt_sensor_enable_ignore_during_ir - 
            *   disable the opt_sensor sensor detection during the time when ir signals are being emitted.
            *   this stops reflections of IR signals from triggering frame start signals.
            * 9) opt_sensor_enable_duplicate_realtime_reporting -
            *   detect duplicate frames and pretend they aren't dupes (send no ir) then report the dupe to the host pc so it can skip a second frame immediately. duplicaes are reported to pc in the format "+d 0\n" (right duplicate) "+d 1\n" (left duplicate)
            * 10) opt_sensor_output_stats -
            *   output statistics (if built with OPT_SENSOR_ENABLE_STATS) relating to how the opt_sensor module is processing all lines start with "+stats " followed by specific statistics.
            */
            for (uint8_t p = 0; p < 20; p++) 
            {
                end = input.indexOf(",", start);
                if (end == 255) 
                {
                    end = input.indexOf("\n", start);
                }
                if (end != 255 && end > start) 
                {
                    long temp = input.substring(start, end).toInt();
                    start = end+1;
                    if (p == 0)
                    {
                        command = temp;
                    }
                    if (command == 0 && temp >= 0) // update settings
                    {
                        if (p == 1 && temp < NUMBER_OF_IR_PROTOCOLS) 
                        {
                            ir_glasses_selected = temp;
                        }
                        else if (p == 2) 
                        {
                            ir_frame_delay = temp;
                        }
                        else if (p == 3)
                        {
                            ir_frame_duration = temp;
                        }
                        else if (p == 4)
                        {
                            ir_signal_spacing = temp;
                        }
                        else if (p == 5) 
                        {
                            opt_sensor_block_signal_detection_delay = temp;
                        }
                        else if (p == 6) 
                        {
                            opt_sensor_min_threshold_value_to_activate = temp;
                        }
                        else if (p == 7) 
                        {
                            opt_sensor_detection_threshold_high = temp;
                        }
                        else if (p == 8) 
                        {
                            opt_sensor_enable_ignore_during_ir = temp;
                        }
                        else if (p == 9) 
                        {
                            opt_sensor_enable_duplicate_realtime_reporting = temp;
                        }
                        else if (p == 10) 
                        {
                            opt_sensor_output_stats = temp;
                        }
                        else if (p == 11) 
                        {
                            pwm_backlight_frequency = temp;
                            update_pwm_pulses_per_frame();
                        }
                        else if (p == 12) 
                        {
                            opt_sensor_ignore_all_duplicates = temp;
                        }
                        else if (p == 13) 
                        {
                            opt_sensor_filter_mode = temp;
                        }
                        else if (p == 14) 
                        {
                            ir_flip_eyes = temp;
                        }
                        else if (p == 15) 
                        {
                            opt_sensor_detection_threshold_low = temp;
                        }
                        else if (p == 16)
                        {
                            ir_average_timing_mode = temp;
                        }
                        else if (p == 17) 
                        {
                            target_frametime = temp;
                            update_pwm_pulses_per_frame();
                        }
                        opt_sensor_SettingsChanged();
                    }
                    else if (command == 7 && p == 1 && temp >= 0 && temp < 3) // update glasses mode
                    {
                        if (temp == 0) {
                            ir_signal_send_request(SIGNAL_MODE_RIGHT_AND_LEFT);
                        }
                        else if (temp == 1) {
                            ir_signal_send_request(SIGNAL_MODE_RIGHT_ONLY);
                        }
                        else if (temp == 2) {
                            ir_signal_send_request(SIGNAL_MODE_LEFT_ONLY);
                        }
                        Serial.println("OK");
                        break;
                    }
                    else if (command == 8) // store current config to eeprom as default
                    {
                        EEPROMSettings eeprom_settings = {
                            EEPROM_SETTING_CHECKVALUE,
                            EMITTER_VERSION,
                            ir_glasses_selected,
                            ir_frame_delay,
                            ir_frame_duration,
                            ir_signal_spacing,
                            opt_sensor_block_signal_detection_delay,
                            opt_sensor_min_threshold_value_to_activate,
                            opt_sensor_detection_threshold_high,
                            opt_sensor_enable_ignore_during_ir,
                            opt_sensor_enable_duplicate_realtime_reporting,
                            opt_sensor_output_stats,
                            0,
                            opt_sensor_ignore_all_duplicates,
                            opt_sensor_filter_mode,
                            ir_flip_eyes,
                            opt_sensor_detection_threshold_low,
                            ir_average_timing_mode,
                            target_frametime,
                            pwm_backlight_frequency
                        };
                        EEPROM.put(EEPROM_SETTING_ADDRESS, eeprom_settings);
                        Serial.println("OK");
                        break;
                    }
                    #ifdef OPT_SENSOR_ENABLE_STREAM_READINGS_TO_SERIAL
                    else if (command == 10 && p == 1 && temp >= 0 && temp < 2) // toggle opt_sensor stream readings to serial
                    {
                        opt_sensor_enable_stream_readings_to_serial = temp;
                        Serial.println("OK");
                        break;
                    }
                    #endif
                }
            }
            if (command == 0)
            {
                Serial.print("parameters ");

                Serial.print(EMITTER_VERSION);
                Serial.print(",");
                Serial.print(ir_glasses_selected);
                Serial.print(",");
                Serial.print(ir_frame_delay);
                Serial.print(",");
                Serial.print(ir_frame_duration);
                Serial.print(",");
                Serial.print(ir_signal_spacing);
                Serial.print(",");
                Serial.print(opt_sensor_block_signal_detection_delay);
                Serial.print(",");
                Serial.print(opt_sensor_min_threshold_value_to_activate);
                Serial.print(",");
                Serial.print(opt_sensor_detection_threshold_high);
                Serial.print(",");
                Serial.print(opt_sensor_enable_ignore_during_ir);
                Serial.print(",");
                Serial.print(opt_sensor_enable_duplicate_realtime_reporting);
                Serial.print(",");
                Serial.print(opt_sensor_output_stats);
                Serial.print(",");
                Serial.print(pwm_backlight_frequency);
                Serial.print(",");
                Serial.print(opt_sensor_ignore_all_duplicates);
                Serial.print(",");
                Serial.print(opt_sensor_filter_mode);
                Serial.print(",");
                Serial.print(ir_flip_eyes);
                Serial.print(",");
                Serial.print(opt_sensor_detection_threshold_low);
                Serial.print(",");
                Serial.print(ir_average_timing_mode);
                Serial.print(",");
                Serial.println(target_frametime);
                Serial.println("OK");
            }
            input = String();
        }
    }
    opt_sensor_CheckReadings();
    current_time = micros();
    if (current_time >= next_print && current_time - next_print < 60000000) 
    {
        #ifdef OPT_SENSOR_ENABLE_STATS
        if (opt_sensor_output_stats) 
        {   
            opt_sensor_PrintStats();
            if (opt_sensor_FinishPrintStats())
            {
                next_print = current_time + OPT_SENSOR_UPDATE_STAT_PERIOD;
            }
        }
        else
        {
        #endif
        opt_sensor_UpdateThresholds();
        opt_sensor_ClearStats();
        next_print = current_time + OPT_SENSOR_UPDATE_STAT_PERIOD;
        #ifdef OPT_SENSOR_ENABLE_STATS
        }
        #endif
    }
}