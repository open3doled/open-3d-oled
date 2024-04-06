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
#include "opt101_sensor.h"

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
    //#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    //#if (defined(OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION) && defined(OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION_DEBUG_PIN_D2)) || defined(OPT101_ENABLE_IGNORE_DURING_IR) && defined(OPT101_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2) 
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
	bitSet(DDR_DEBUG_PREMATURE_FRAME_D14, DEBUG_PREMATURE_FRAME_D14);
    //#endif
    ir_signal_init();
    opt101_sensor_Init();
    EEPROMSettings eeprom_settings;
    EEPROM.get(EEPROM_SETTING_ADDRESS, eeprom_settings);
    if (eeprom_settings.check_value == EEPROM_SETTING_CHECKVALUE)
    {
        if (eeprom_settings.version == 2) 
        {
            ir_glasses_selected = eeprom_settings.ir_glasses_selected;
            ir_frame_delay = eeprom_settings.ir_frame_delay;
            ir_frame_duration = eeprom_settings.ir_frame_duration;
            ir_signal_spacing = eeprom_settings.ir_signal_spacing;
            opt101_block_signal_detection_delay = eeprom_settings.opt101_block_signal_detection_delay;
            opt101_min_threshold_value_to_activate = eeprom_settings.opt101_min_threshold_value_to_activate;
            opt101_detection_threshold = eeprom_settings.opt101_detection_threshold;
            opt101_detection_threshold_repeated_high = eeprom_settings.opt101_detection_threshold_repeated_high;
            opt101_detection_threshold_repeated_low = eeprom_settings.opt101_detection_threshold_repeated_low;
            opt101_enable_ignore_during_ir = 0;
            opt101_enable_duplicate_realtime_reporting =  eeprom_settings.opt101_enable_ignore_during_ir;
            opt101_output_stats = eeprom_settings.opt101_enable_duplicate_realtime_reporting;
            opt101_enable_frequency_analysis_based_duplicate_frame_detection = eeprom_settings.opt101_output_stats;
        }
        else if (eeprom_settings.version > 3) 
        {
            ir_glasses_selected = eeprom_settings.ir_glasses_selected;
            ir_frame_delay = eeprom_settings.ir_frame_delay;
            ir_frame_duration = eeprom_settings.ir_frame_duration;
            ir_signal_spacing = eeprom_settings.ir_signal_spacing;
            opt101_block_signal_detection_delay = eeprom_settings.opt101_block_signal_detection_delay;
            opt101_min_threshold_value_to_activate = eeprom_settings.opt101_min_threshold_value_to_activate;
            opt101_detection_threshold = eeprom_settings.opt101_detection_threshold;
            opt101_detection_threshold_repeated_high = eeprom_settings.opt101_detection_threshold_repeated_high;
            opt101_detection_threshold_repeated_low = eeprom_settings.opt101_detection_threshold_repeated_low;
            opt101_enable_ignore_during_ir = eeprom_settings.opt101_enable_ignore_during_ir;
            opt101_enable_duplicate_realtime_reporting = eeprom_settings.opt101_enable_duplicate_realtime_reporting;
            opt101_output_stats = eeprom_settings.opt101_output_stats;
            opt101_enable_frequency_analysis_based_duplicate_frame_detection = eeprom_settings.opt101_enable_frequency_analysis_based_duplicate_frame_detection;
            if (eeprom_settings.version >= 10) 
            {
                opt101_block_n_subsequent_duplicates = eeprom_settings.opt101_block_n_subsequent_duplicates;
            }
            if (eeprom_settings.version >= 12) 
            {
                opt101_ignore_all_duplicates = eeprom_settings.opt101_ignore_all_duplicates;
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
            * 5) opt101_block_signal_detection_delay - 
            *   how long to wait after a high tv signal on left or right before allowing another high tv signal on either 
            *   channel (in microseconds) this is useful to eliminating false triggers when the tv signal is decreasing in a noisy fashion.
            *   this is best set to slighly lower than the target refresh rate (about 80-90%).
            * 14) opt101_block_n_subsequent_duplicates -
            *   (number of detections to block) on displays that use a PWM backlight one needs to block fake duplicate frames 
            *   for at least the first math.ceiling((PWM frequency)/framerate) otherwise a PWM pulse may incorrectly 
            *   be detected as the next duplicate frame causing the unit to lose proper synchronization. 
            *   When using this setting one should set opt101_block_signal_detection_delay to a 
            *   value 80-90% of the PWM backlight cycle time. (default 0).
            * 15) opt101_ignore_all_duplicates -
            *   (0 disable - >1 enable) on displays with too much jitter where setting opt101_block_signal_detection_delay and/or
            *   opt101_block_n_subsequent_duplicates does not eliminate false dulicate detection due to strange PWM characteristics
            *   or variable brightness periods, it may be best to ignore any detected duplicates. This will mean that glasses only
            *   attempt resynchronization when the alternate eye trigger is sent by the display.
            * 6) opt101_min_threshold_value_to_activate -
            *   the light intensities threshold value in a given threshold update cycle must exceed this value before the emitter will turn on.
            *   this setting is used to stop the emitter turning on when the TV is turned off.  (default 10)
            *   to low a value will cause it to turn on when the screen is black and trigger sporatically. 
            *   to high a value will mean that it never turns on.
            * 7) opt101_detection_threshold - 
            *   the level (as a value between 1-255) above which an increasing light intensity is detected as the beggining of a new frame, 
            *   setting this lower will make the device aware of new frames earlier but also increase the likelihood of duplicate frame
            *   detection if the light intensity doesn't fall below this threshold before the opt101_block_signal_detection_delay completes.
            * 10) opt101_enable_ignore_during_ir - 
            *   disable the opt101 sensor detection during the time when ir signals are being emitted.
            *   this stops reflections of IR signals from triggering frame start signals.
            * 11) opt101_enable_duplicate_realtime_reporting -
            *   detect duplicate frames and pretend they aren't dupes (send no ir) then report the dupe to the host pc so it can skip a second frame immediately. duplicaes are reported to pc in the format "+d 0\n" (right duplicate) "+d 1\n" (left duplicate)
            * 12) opt101_output_stats -
            *   output statistics (if built with OPT101_ENABLE_STATS) relating to how the opt101 module is processing all lines start with "+stats " followed by specific statistics.
            * LCD Specific Parameters
            * 13) opt101_enable_frequency_analysis_based_duplicate_frame_detection -
            *   enables the code to detect duplicate frames on screens without a black frame interval (if built with OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION).
            * 8) opt101_detection_threshold_repeated_high -
            *   when attempting to detect duplicate frames on screens without a black frame interval, first the framerate is detected.
            *   then after each frame detection we wait the frame period, if after the frame period the signal for that same light sensor 
            *   is above opt101_detection_threshold_repeated_high and not decreasing and the other light sensor is below 
            *   opt101_detection_threshold_repeated_low and this condition persists for approximately 0.5 milliseconds, it is detected
            *   as a duplicate frame.
            * 9) opt101_detection_threshold_repeated_low - see 5 above
            */
            for (uint8_t p = 0; p < 17; p++) 
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
                            opt101_block_signal_detection_delay = temp;
                        }
                        else if (p == 6) 
                        {
                            opt101_min_threshold_value_to_activate = temp;
                        }
                        else if (p == 7) 
                        {
                            opt101_detection_threshold = temp;
                        }
                        else if (p == 8) 
                        {
                            opt101_detection_threshold_repeated_high = temp;
                        }
                        else if (p == 9) 
                        {
                            opt101_detection_threshold_repeated_low = temp;
                        }
                        else if (p == 10) 
                        {
                            opt101_enable_ignore_during_ir = temp;
                        }
                        else if (p == 11) 
                        {
                            opt101_enable_duplicate_realtime_reporting = temp;
                        }
                        else if (p == 12) 
                        {
                            opt101_output_stats = temp;
                        }
                        else if (p == 13) 
                        {
                            opt101_enable_frequency_analysis_based_duplicate_frame_detection = temp;
                        }
                        else if (p == 14) 
                        {
                            opt101_block_n_subsequent_duplicates = temp;
                        }
                        else if (p == 15) 
                        {
                            opt101_ignore_all_duplicates = temp;
                        }
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
                            opt101_block_signal_detection_delay,
                            opt101_min_threshold_value_to_activate,
                            opt101_detection_threshold,
                            opt101_detection_threshold_repeated_high,
                            opt101_detection_threshold_repeated_low,
                            opt101_enable_ignore_during_ir,
                            opt101_enable_duplicate_realtime_reporting,
                            opt101_output_stats,
                            opt101_enable_frequency_analysis_based_duplicate_frame_detection,
                            opt101_block_n_subsequent_duplicates,
                            opt101_ignore_all_duplicates
                        };
                        EEPROM.put(EEPROM_SETTING_ADDRESS, eeprom_settings);
                        Serial.println("OK");
                        break;
                    }
                    #ifdef OPT101_ENABLE_STREAM_READINGS_TO_SERIAL
                    else if (command == 10 && p == 1 && temp >= 0 && temp < 2) // toggle opt101 stream readings to serial
                    {
                        opt101_enable_stream_readings_to_serial = temp;
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
                Serial.print(opt101_block_signal_detection_delay);
                Serial.print(",");
                Serial.print(opt101_min_threshold_value_to_activate);
                Serial.print(",");
                Serial.print(opt101_detection_threshold);
                Serial.print(",");
                Serial.print(opt101_detection_threshold_repeated_high);
                Serial.print(",");
                Serial.print(opt101_detection_threshold_repeated_low);
                Serial.print(",");
                Serial.print(opt101_enable_ignore_during_ir);
                Serial.print(",");
                Serial.print(opt101_enable_duplicate_realtime_reporting);
                Serial.print(",");
                Serial.print(opt101_output_stats);
                Serial.print(",");
                Serial.print(opt101_enable_frequency_analysis_based_duplicate_frame_detection);
                Serial.print(",");
                Serial.print(opt101_block_n_subsequent_duplicates);
                Serial.print(",");
                Serial.println(opt101_ignore_all_duplicates);
                Serial.println("OK");
            }
            input = String();
        }
    }
    opt101_sensor_CheckReadings();
    current_time = micros();
    if (current_time >= next_print && current_time - next_print < 60000000) 
    {
        #ifdef OPT101_ENABLE_STATS
        if (opt101_output_stats) 
        {   
            opt101_sensor_PrintStats();
            if (opt101_sensor_FinishPrintStats())
            {
                next_print = current_time + OPT101_UPDATE_STAT_PERIOD;
            }
        }
        else
        {
        #endif
        opt101_sensor_UpdateThresholds();
        opt101_sensor_ClearStats();
        next_print = current_time + OPT101_UPDATE_STAT_PERIOD;
        #ifdef OPT101_ENABLE_STATS
        }
        #endif
    }
}