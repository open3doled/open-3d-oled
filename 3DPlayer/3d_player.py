#!/usr/bin/env python3

# Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/

import os
import sys  # @UnusedImport
import tkinter  # @UnusedImport
import tkinter.filedialog
import time
import traceback
import functools
import idlelib.tooltip

# import sdl2.video  # @UnusedImport
import pysrt
import serial  # @UnusedImport
import serial.threaded
import threading
import queue
import json
import datetime

from PIL import ImageTk
from io import BytesIO
import cairosvg
import PIL.Image

# defaults LCD 2560x1080 75hz
# DEFAULT_DISPLAY_RESOLUTION = '2560x1080'
# DEFAULT_DISPLAY_SIZE = '34'
# DEFAULT_TARGET_FRAMERATE = '0'
# IR_FRAME_DELAY = 500
# IR_FRAME_DURATION = 11000
# OPT101_BLOCK_SIGNAL_DETECTION_DELAY = 5000

# defaults LG OLED 1920x1080 120hz
DEFAULT_DISPLAY_RESOLUTION = "1920x1080"
DEFAULT_DISPLAY_SIZE = "55"
DEFAULT_TARGET_FRAMERATE = "0"
IR_FRAME_DELAY = 500
IR_FRAME_DURATION = 7100
OPT101_BLOCK_SIGNAL_DETECTION_DELAY = 5000


# The following class is extracted from tkinter.
class _setit:
    """Internal class. It wraps the command in the widget OptionMenu."""

    def __init__(self, var, value, callback=None):
        self.__value = value
        self.__var = var
        self.__callback = callback

    def __call__(self, *args):
        self.__var.set(self.__value)
        if self.__callback:
            self.__callback(self.__value, *args)


# from https://stackoverflow.com/questions/67449774/how-to-display-svg-on-tkinter
def svg_to_imagetk_photoimage(image):
    png_data = cairosvg.svg2png(
        url=os.path.join(base_path, image), output_width=30, output_height=30
    )
    bytes_png = BytesIO(png_data)
    img = PIL.Image.open(bytes_png)
    return ImageTk.PhotoImage(img)


class EmitterSerialLineReader(serial.threaded.LineReader):

    TERMINATOR = b"\r\n"

    def __init__(self):
        super(EmitterSerialLineReader, self).__init__()
        self.alive = True
        self.total_left_frames = 0
        self.total_right_frames = 0
        self.total_duplicate_frames = 0
        self.total_premature_frames = 0
        self.responses = queue.Queue()
        self.events = queue.Queue()
        self._event_thread = threading.Thread(target=self._run_event)
        self._event_thread.daemon = True
        self._event_thread.name = "emitter-event"
        self._event_thread.start()
        self.lock = threading.Lock()
        self.__pageflipglsink = None

    def stop(self):
        self.alive = False
        self.events.put(None)
        self.responses.put("<exit>")

    def _run_event(self):
        while self.alive:
            try:
                self.handle_event(self.events.get())
            except:
                traceback.print_exc()

    def handle_line(self, line):
        if line.startswith("+"):
            self.events.put(line)
        else:
            self.responses.put(line)

    def handle_event(self, event):
        if event.startswith("+d "):
            if self.__pageflipglsink is not None:
                print("skipped")
                self.__pageflipglsink.set_property("skip-n-page-flips", "1")
        else:
            print("event received:", event)
            if event.startswith("+stats general"):
                for d in event.split(" "):
                    if d.startswith("duplicate_frames:"):
                        self.total_duplicate_frames += int(d.split(":")[1])
                    elif d.startswith("premature_frames:"):
                        self.total_premature_frames += int(d.split(":")[1])
            if event.startswith("+stats sensor channel:right"):
                for d in event.split(" "):
                    if d.startswith("detections:"):
                        self.total_right_frames += int(d.split(":")[1])
            if event.startswith("+stats sensor channel:left"):
                for d in event.split(" "):
                    if d.startswith("detections:"):
                        self.total_left_frames += int(d.split(":")[1])
                print(
                    f"event received: -stats total total_right_frames:{self.total_right_frames} total_left_frames:{self.total_left_frames} total_duplicate_frames:{self.total_duplicate_frames} total_premature_frames:{self.total_premature_frames}"
                )

    def command(self, command, response="OK", timeout=5):
        with self.lock:  # ensure that just one thread is sending commands at once
            self.write_line(command)
            lines = []
            while True:
                try:
                    line = self.responses.get(timeout=timeout)
                    # ~ print("%s -> %r" % (command, line))
                    if line == response:
                        return lines
                    else:
                        lines.append(line)
                except queue.Empty:
                    raise Exception("command timeout ({!r})".format(command))

    @property
    def pageflipglsink(self):
        return self.__pageflipglsink

    @pageflipglsink.setter
    def pageflipglsink(self, value):
        if value != self.__pageflipglsink:
            self.__pageflipglsink = value


class EmitterSerial(EmitterSerialLineReader):

    def __init__(self, path: str, baudrate: int = 115200):
        super(EmitterSerial, self).__init__()
        self.line_reader_manager = serial.threaded.ReaderThread(
            serial.Serial(path, baudrate), EmitterSerialLineReader
        )
        self.line_reader_manager_enter = type(self.line_reader_manager).__enter__
        self.line_reader_manager_exit = type(self.line_reader_manager).__exit__
        self.line_reader = self.line_reader_manager_enter(self.line_reader_manager)

    def close(self):
        self.line_reader_manager_exit(self.line_reader_manager, None, None, None)

    @property
    def pageflipglsink(self):
        return self.line_reader.pageflipglsink

    @pageflipglsink.setter
    def pageflipglsink(self, value):
        if value != self.line_reader.pageflipglsink:
            self.line_reader.pageflipglsink = value


class EmitterSettingsDialog:
    def __init__(self, parent, main_app):
        self.main_app = main_app
        top = self.top = tkinter.Toplevel(parent)
        row_count = 0

        self.serial_port_identifier_frame = tkinter.Frame(top)
        self.serial_port_identifier_variable = tkinter.StringVar(top)
        self.serial_port_identifier_variable.set("/dev/ttyACM0")
        self.serial_port_identifier_label = tkinter.Label(
            self.serial_port_identifier_frame, text="Serial Port Identifier: "
        )
        self.serial_port_identifier_label.pack(padx=5, side=tkinter.LEFT)
        self.serial_port_identifier_entry = tkinter.Entry(
            self.serial_port_identifier_frame,
            textvariable=self.serial_port_identifier_variable,
        )
        self.serial_port_identifier_entry.pack(padx=5, side=tkinter.LEFT)
        self.serial_port_identifier_entry_tooltip = idlelib.tooltip.Hovertip(
            self.serial_port_identifier_entry,
            "Used as the serial port when connecting to the emitter. (On linux use /dev/ttyACM[0-9], on Windows use COM[0-9])",
            hover_delay=100,
        )
        self.serial_port_connect_button = tkinter.Button(
            self.serial_port_identifier_frame,
            text="Connect",
            command=self.serial_port_click_connect,
        )
        self.serial_port_connect_button.pack(padx=5, side=tkinter.LEFT)
        self.serial_port_connect_button_tooltip = idlelib.tooltip.Hovertip(
            self.serial_port_connect_button,
            "Connect to the emitter on the specified serial port. (On linux use /dev/ttyACM[0-9], on Windows use COM[0-9])",
            hover_delay=100,
        )
        self.serial_port_disconnect_button = tkinter.Button(
            self.serial_port_identifier_frame,
            text="Disconnect",
            command=self.serial_port_click_disconnect,
        )
        self.serial_port_disconnect_button.pack(padx=5, side=tkinter.LEFT)
        self.serial_port_disconnect_button_tooltip = idlelib.tooltip.Hovertip(
            self.serial_port_disconnect_button,
            "Disconnect from the emitter.",
            hover_delay=100,
        )
        self.serial_port_identifier_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.setting_ir_protocol_frame = tkinter.Frame(top)
        self.setting_ir_protocol_variable = tkinter.StringVar(top)
        self.setting_ir_protocol_variable.set("6")
        self.setting_ir_protocol_label = tkinter.Label(
            self.setting_ir_protocol_frame, text="IR Protocol: "
        )
        self.setting_ir_protocol_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_protocol_entry = tkinter.Entry(
            self.setting_ir_protocol_frame,
            textvariable=self.setting_ir_protocol_variable,
        )
        self.setting_ir_protocol_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_protocol_tooltip = idlelib.tooltip.Hovertip(
            self.setting_ir_protocol_entry,
            "0=Samsung07, 1=Xpand, 2=3DVision, 3=Sharp, 4=Sony, 5=Panasonic, 6=PanasonicCustom",
            hover_delay=100,
        )
        self.setting_ir_protocol_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.setting_glasses_mode_frame = tkinter.Frame(top)
        self.setting_glasses_mode_variable = tkinter.StringVar(top)
        self.setting_glasses_mode_variable.set("0")
        self.setting_glasses_mode_label = tkinter.Label(
            self.setting_glasses_mode_frame, text="Glasses Mode: "
        )
        self.setting_glasses_mode_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_glasses_mode_entry = tkinter.Entry(
            self.setting_glasses_mode_frame,
            textvariable=self.setting_glasses_mode_variable,
        )
        self.setting_glasses_mode_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_glasses_mode_tooltip = idlelib.tooltip.Hovertip(
            self.setting_glasses_mode_entry,
            "0=LeftAndRight, 1=RightOnly, 2=LeftOnly",
            hover_delay=100,
        )
        self.setting_glasses_mode_button = tkinter.Button(
            self.setting_glasses_mode_frame,
            text="Set Glasses Mode",
            command=self.click_set_glasses_mode,
        )
        self.setting_glasses_mode_button.pack(padx=5, side=tkinter.LEFT)
        self.setting_glasses_mode_button_tooltip = idlelib.tooltip.Hovertip(
            self.setting_glasses_mode_button,
            "On supported glasses with custom made firmware, this will send the specified IR command to glasses instructing them to display frames intended for 0=LeftAndRight, 1=RightOnly, 2=LeftOnly. \nBy shielding glasses IR sensors it is possible to have two people watch two different videos on the same TV at the same time. \n(this is not a traditional setting but more of a command, so it is not saved to JSON files or EEPROM.)",
            hover_delay=100,
        )
        self.setting_glasses_mode_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.setting_ir_frame_delay_frame = tkinter.Frame(top)
        self.setting_ir_frame_delay_variable = tkinter.StringVar(top)
        self.setting_ir_frame_delay_variable.set("100")
        self.setting_ir_frame_delay_label = tkinter.Label(
            self.setting_ir_frame_delay_frame, text="IR Frame Delay: "
        )
        self.setting_ir_frame_delay_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_frame_delay_entry = tkinter.Entry(
            self.setting_ir_frame_delay_frame,
            textvariable=self.setting_ir_frame_delay_variable,
        )
        self.setting_ir_frame_delay_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_frame_delay_tooltip = idlelib.tooltip.Hovertip(
            self.setting_ir_frame_delay_entry,
            "(in microseconds) how long to delay after getting tv signal before attempting to activate the shutter glasses",
            hover_delay=100,
        )
        self.setting_ir_frame_delay_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.setting_ir_frame_duration_frame = tkinter.Frame(top)
        self.setting_ir_frame_duration_variable = tkinter.StringVar(top)
        self.setting_ir_frame_duration_variable.set("8000")
        self.setting_ir_frame_duration_label = tkinter.Label(
            self.setting_ir_frame_duration_frame, text="IR Frame Duration: "
        )
        self.setting_ir_frame_duration_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_frame_duration_entry = tkinter.Entry(
            self.setting_ir_frame_duration_frame,
            textvariable=self.setting_ir_frame_duration_variable,
        )
        self.setting_ir_frame_duration_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_frame_duration_tooltip = idlelib.tooltip.Hovertip(
            self.setting_ir_frame_duration_entry,
            "(in microseconds) how long to delay before switching de-activating the shutter glasses after activating them",
            hover_delay=100,
        )
        self.setting_ir_frame_duration_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.setting_ir_signal_spacing_frame = tkinter.Frame(top)
        self.setting_ir_signal_spacing_variable = tkinter.StringVar(top)
        self.setting_ir_signal_spacing_variable.set("30")
        self.setting_ir_signal_spacing_label = tkinter.Label(
            self.setting_ir_signal_spacing_frame, text="IR Signal Spacing: "
        )
        self.setting_ir_signal_spacing_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_signal_spacing_entry = tkinter.Entry(
            self.setting_ir_signal_spacing_frame,
            textvariable=self.setting_ir_signal_spacing_variable,
        )
        self.setting_ir_signal_spacing_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_signal_spacing_tooltip = idlelib.tooltip.Hovertip(
            self.setting_ir_signal_spacing_entry,
            "(in microseconds) how long to delay after sending one signal before sending the next. \nThis is used to ensure the receiver is done handling one signal so as to not overload it. \n(default 30us which is more than 17us used by panasonic custom firmware)",
            hover_delay=100,
        )
        self.setting_ir_signal_spacing_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.setting_opt101_block_signal_detection_delay_frame = tkinter.Frame(top)
        self.setting_opt101_block_signal_detection_delay_variable = tkinter.StringVar(
            top
        )
        self.setting_opt101_block_signal_detection_delay_variable.set("5000")
        self.setting_opt101_block_signal_detection_delay_label = tkinter.Label(
            self.setting_opt101_block_signal_detection_delay_frame,
            text="OPT101 Block Signal Detection Delay: ",
        )
        self.setting_opt101_block_signal_detection_delay_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_block_signal_detection_delay_entry = tkinter.Entry(
            self.setting_opt101_block_signal_detection_delay_frame,
            textvariable=self.setting_opt101_block_signal_detection_delay_variable,
        )
        self.setting_opt101_block_signal_detection_delay_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_block_signal_detection_delay_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_block_signal_detection_delay_entry,
            "(in microseconds) how long to wait after a high tv signal on left or right before allowing another high tv signal \non either channel this is useful to eliminating false triggers when the tv signal is decreasing in a noisy fashion. \nthis is best set to slighly lower than the target refresh rate (about 80-90%).",
            hover_delay=100,
        )
        self.setting_opt101_block_signal_detection_delay_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt101_min_threshold_value_to_activate_frame = tkinter.Frame(top)
        self.setting_opt101_min_threshold_value_to_activate_variable = (
            tkinter.StringVar(top)
        )
        self.setting_opt101_min_threshold_value_to_activate_variable.set("10")
        self.setting_opt101_min_threshold_value_to_activate_label = tkinter.Label(
            self.setting_opt101_min_threshold_value_to_activate_frame,
            text="OPT101 Min Threshold Value To Activate: ",
        )
        self.setting_opt101_min_threshold_value_to_activate_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_min_threshold_value_to_activate_entry = tkinter.Entry(
            self.setting_opt101_min_threshold_value_to_activate_frame,
            textvariable=self.setting_opt101_min_threshold_value_to_activate_variable,
        )
        self.setting_opt101_min_threshold_value_to_activate_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_min_threshold_value_to_activate_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_min_threshold_value_to_activate_entry,
            "(as a value between 1-255) The light intensities highest threshold value in a given threshold update cycle must exceed this value before \nthe emitter will turn on.  This setting is used to stop the emitter turning on when the TV is turned off. \nTo low a value will cause it to turn on when the screen is black and trigger sporatically. \nTo high a value will mean that it never turns on. \n(default 10)",
            hover_delay=100,
        )
        self.setting_opt101_min_threshold_value_to_activate_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt101_detection_threshold_frame = tkinter.Frame(top)
        self.setting_opt101_detection_threshold_variable = tkinter.StringVar(top)
        self.setting_opt101_detection_threshold_variable.set("128")
        self.setting_opt101_detection_threshold_label = tkinter.Label(
            self.setting_opt101_detection_threshold_frame,
            text="OPT101 Detection Threshold: ",
        )
        self.setting_opt101_detection_threshold_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt101_detection_threshold_entry = tkinter.Entry(
            self.setting_opt101_detection_threshold_frame,
            textvariable=self.setting_opt101_detection_threshold_variable,
        )
        self.setting_opt101_detection_threshold_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt101_detection_threshold_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_detection_threshold_entry,
            "(as a value between 1-255) the level above which an increasing light intensity is detected as the beggining of a new frame, \nsetting this lower will make the device aware of new frames earlier but also increase the likelihood of duplicate \nframe detection if the light intensity doesn't fall below this threshold before the opt101_block_signal_detection_delay \ncompletes.",
            hover_delay=100,
        )
        self.setting_opt101_detection_threshold_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt101_detection_threshold_repeated_high_frame = tkinter.Frame(top)
        self.setting_opt101_detection_threshold_repeated_high_variable = (
            tkinter.StringVar(top)
        )
        self.setting_opt101_detection_threshold_repeated_high_variable.set("224")
        self.setting_opt101_detection_threshold_repeated_high_label = tkinter.Label(
            self.setting_opt101_detection_threshold_repeated_high_frame,
            text="OPT101 Detection Threshold High: ",
        )
        self.setting_opt101_detection_threshold_repeated_high_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_detection_threshold_repeated_high_entry = tkinter.Entry(
            self.setting_opt101_detection_threshold_repeated_high_frame,
            textvariable=self.setting_opt101_detection_threshold_repeated_high_variable,
        )
        self.setting_opt101_detection_threshold_repeated_high_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_detection_threshold_repeated_high_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_detection_threshold_repeated_high_entry,
            "(as a value between 1-255) (LCD Specific) when attempting to detect duplicate frames on screens without a black frame interval, \nfirst the framerate is detected. then after each frame detection we wait the frame period, if after the frame period \nthe signal for that same light sensor is above opt101_detection_threshold_repeated_high and not decreasing and the \nother light sensor is below opt101_detection_threshold_repeated_low and this condition persists for approximately \n0.5 milliseconds, it is detected as a duplicate frame.",
            hover_delay=100,
        )
        self.setting_opt101_detection_threshold_repeated_high_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt101_detection_threshold_repeated_low_frame = tkinter.Frame(top)
        self.setting_opt101_detection_threshold_repeated_low_variable = (
            tkinter.StringVar(top)
        )
        self.setting_opt101_detection_threshold_repeated_low_variable.set("32")
        self.setting_opt101_detection_threshold_repeated_low_label = tkinter.Label(
            self.setting_opt101_detection_threshold_repeated_low_frame,
            text="OPT101 Detection Threshold Low: ",
        )
        self.setting_opt101_detection_threshold_repeated_low_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_detection_threshold_repeated_low_entry = tkinter.Entry(
            self.setting_opt101_detection_threshold_repeated_low_frame,
            textvariable=self.setting_opt101_detection_threshold_repeated_low_variable,
        )
        self.setting_opt101_detection_threshold_repeated_low_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_detection_threshold_repeated_low_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_detection_threshold_repeated_low_entry,
            "(as a value between 1-255) (LCD Specific) see OPT101 Detection Threshold High above",
            hover_delay=100,
        )
        self.setting_opt101_detection_threshold_repeated_low_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt101_enable_ignore_during_ir_frame = tkinter.Frame(top)
        self.setting_opt101_enable_ignore_during_ir_variable = tkinter.StringVar(top)
        self.setting_opt101_enable_ignore_during_ir_variable.set("1")
        self.setting_opt101_enable_ignore_during_ir_label = tkinter.Label(
            self.setting_opt101_enable_ignore_during_ir_frame,
            text="Enable Ignore Frame Start During IR: ",
        )
        self.setting_opt101_enable_ignore_during_ir_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_enable_ignore_during_ir_entry = tkinter.Entry(
            self.setting_opt101_enable_ignore_during_ir_frame,
            textvariable=self.setting_opt101_enable_ignore_during_ir_variable,
        )
        self.setting_opt101_enable_ignore_during_ir_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_enable_ignore_during_ir_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_enable_ignore_during_ir_entry,
            "disable the opt101 sensor detection during the time when ir signals are being emitted. \nthis stops reflections of IR signals from triggering frame start signals.",
            hover_delay=100,
        )
        self.setting_opt101_enable_ignore_during_ir_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt101_enable_smart_duplicate_frame_handling_frame = tkinter.Frame(
            top
        )
        self.setting_opt101_enable_smart_duplicate_frame_handling_variable = (
            tkinter.StringVar(top)
        )
        self.setting_opt101_enable_smart_duplicate_frame_handling_variable.set("0")
        self.setting_opt101_enable_smart_duplicate_frame_handling_label = tkinter.Label(
            self.setting_opt101_enable_smart_duplicate_frame_handling_frame,
            text="Enable Smart Duplicate Frame Handling: ",
        )
        self.setting_opt101_enable_smart_duplicate_frame_handling_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_enable_smart_duplicate_frame_handling_entry = tkinter.Entry(
            self.setting_opt101_enable_smart_duplicate_frame_handling_frame,
            textvariable=self.setting_opt101_enable_smart_duplicate_frame_handling_variable,
        )
        self.setting_opt101_enable_smart_duplicate_frame_handling_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_enable_smart_duplicate_frame_handling_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_enable_smart_duplicate_frame_handling_entry,
            '*doesnt work - too much round trip latency* detect duplicate frames and pretend they arent dupes (send no ir) then report the dupe to the host pc so it can skip a second \nframe immediately. duplicaes are reported to pc in the format "+d 0" (right duplicate) "+d 1" (left duplicate)',
            hover_delay=100,
        )
        self.setting_opt101_enable_smart_duplicate_frame_handling_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt101_output_stats_frame = tkinter.Frame(top)
        self.setting_opt101_output_stats_variable = tkinter.StringVar(top)
        self.setting_opt101_output_stats_variable.set("0")
        self.setting_opt101_output_stats_label = tkinter.Label(
            self.setting_opt101_output_stats_frame, text="OPT101 Output Stats: "
        )
        self.setting_opt101_output_stats_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt101_output_stats_entry = tkinter.Entry(
            self.setting_opt101_output_stats_frame,
            textvariable=self.setting_opt101_output_stats_variable,
        )
        self.setting_opt101_output_stats_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt101_output_stats_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_output_stats_entry,
            'output statistics (if built with OPT101_ENABLE_STATS) relating to how the opt101 module is processing all lines start with \n"+stats " followed by specific statistics.',
            hover_delay=100,
        )
        self.setting_opt101_output_stats_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_frame = tkinter.Frame(
            top
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable = tkinter.StringVar(
            top
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable.set(
            "0"
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_label = tkinter.Label(
            self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_frame,
            text="OPT101 Enable Frequency Analysis Based Duplicate Frame Detection: ",
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_entry = tkinter.Entry(
            self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_frame,
            textvariable=self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable,
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_entry,
            "enables the code to detect duplicate frames on screens without a black frame interval (if built with OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION).",
            hover_delay=100,
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.action_button_frame_1 = tkinter.Frame(top)
        self.update_button = tkinter.Button(
            self.action_button_frame_1,
            text="Update Settings on Emitter",
            command=self.click_update_settings_on_emitter,
        )
        self.update_button.pack(padx=5, side=tkinter.LEFT)
        self.update_button_tooltip = idlelib.tooltip.Hovertip(
            self.update_button,
            "Updates the emitter settings using the UI values specified above. (doesn't update the emitters EEPROM so settings will be lost after power cycling.)",
            hover_delay=100,
        )
        self.save_settings_button = tkinter.Button(
            self.action_button_frame_1,
            text="Save Settings to EEPROM",
            command=self.click_save_settings_to_eeprom,
        )
        self.save_settings_button.pack(padx=5, side=tkinter.LEFT)
        self.save_settings_button_tooltip = idlelib.tooltip.Hovertip(
            self.save_settings_button,
            "Updates the emitter settings using the UI values specified above and saves them to the emitters EEPROM. (new settings will now persist after power cycling.)",
            hover_delay=100,
        )
        self.action_button_frame_1.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.action_button_frame_2 = tkinter.Frame(top)
        self.save_settings_to_disk_button = tkinter.Button(
            self.action_button_frame_2,
            text="Save Settings to Disk",
            command=self.click_save_visible_settings_to_disk,
        )
        self.save_settings_to_disk_button.pack(padx=5, side=tkinter.LEFT)
        self.save_settings_to_disk_button_tooltip = idlelib.tooltip.Hovertip(
            self.save_settings_to_disk_button,
            "Saves the emitter settings shown currently in the UI to the JSON file specified.",
            hover_delay=100,
        )
        self.load_settings_from_disk_button = tkinter.Button(
            self.action_button_frame_2,
            text="Load Settings from Disk",
            command=self.click_load_visisble_settings_from_disk,
        )
        self.load_settings_from_disk_button.pack(padx=5, side=tkinter.LEFT)
        self.load_settings_from_disk_button_tooltip = idlelib.tooltip.Hovertip(
            self.load_settings_from_disk_button,
            "Loads the emitter settings from the JSON file specified to the UI. (doesn't load them to the actual emitter, one needs to do that with 'Update Settings on Emitter' after loading them.)",
            hover_delay=100,
        )
        self.close_button = tkinter.Button(
            self.action_button_frame_2, text="Close", command=self.click_close
        )
        self.close_button.pack(padx=5, side=tkinter.LEFT)
        self.close_button_tooltip = idlelib.tooltip.Hovertip(
            self.close_button,
            "Closes this window, without updating/saving any settings or disconnecting from the emitter serial connection.",
            hover_delay=100,
        )
        self.action_button_frame_2.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.update_settings_from_serial()

    def update_settings_from_serial(self):
        if self.main_app.emitter_serial:
            response = self.main_app.emitter_serial.line_reader.command("0")[0].split(
                " "
            )
            if response[0] == "parameters":
                (
                    ir_protocol,
                    ir_frame_delay,
                    ir_frame_duration,
                    ir_signal_spacing,
                    opt101_block_signal_detection_delay,
                    opt101_min_threshold_value_to_activate,
                    opt101_detection_threshold,
                    opt101_detection_threshold_repeated_high,
                    opt101_detection_threshold_repeated_low,
                    opt101_enable_ignore_during_ir,
                    opt101_enable_smart_duplicate_frame_handling,
                    opt101_output_stats,
                    opt101_enable_frequency_analysis_based_duplicate_frame_detection,
                ) = response[1].split(",")
                self.setting_ir_protocol_variable.set(ir_protocol)
                self.setting_ir_frame_delay_variable.set(ir_frame_delay)
                self.setting_ir_frame_duration_variable.set(ir_frame_duration)
                self.setting_ir_signal_spacing_variable.set(ir_signal_spacing)
                self.setting_opt101_block_signal_detection_delay_variable.set(
                    opt101_block_signal_detection_delay
                )
                self.setting_opt101_min_threshold_value_to_activate_variable.set(
                    opt101_min_threshold_value_to_activate
                )
                self.setting_opt101_detection_threshold_variable.set(
                    opt101_detection_threshold
                )
                self.setting_opt101_detection_threshold_repeated_high_variable.set(
                    opt101_detection_threshold_repeated_high
                )
                self.setting_opt101_detection_threshold_repeated_low_variable.set(
                    opt101_detection_threshold_repeated_low
                )
                self.setting_opt101_enable_ignore_during_ir_variable.set(
                    opt101_enable_ignore_during_ir
                )
                self.setting_opt101_enable_smart_duplicate_frame_handling_variable.set(
                    opt101_enable_smart_duplicate_frame_handling
                )
                self.setting_opt101_output_stats_variable.set(opt101_output_stats)
                self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable.set(
                    opt101_enable_frequency_analysis_based_duplicate_frame_detection
                )

    def serial_port_click_connect(self):
        if self.main_app.emitter_serial:
            self.main_app.emitter_serial.close()
        self.main_app.emitter_serial = EmitterSerial(
            self.serial_port_identifier_variable.get(), 115200
        )
        self.update_settings_from_serial()

    def serial_port_click_disconnect(self):
        if self.main_app.emitter_serial:
            self.main_app.emitter_serial.close()
        self.main_app.emitter_serial = None

    def click_update_settings_on_emitter(self):
        if self.main_app.emitter_serial:
            command = (
                f"0,"
                f"{self.setting_ir_protocol_variable.get()},"
                f"{self.setting_ir_frame_delay_variable.get()},"
                f"{self.setting_ir_frame_duration_variable.get()},"
                f"{self.setting_ir_signal_spacing_variable.get()},"
                f"{self.setting_opt101_block_signal_detection_delay_variable.get()},"
                f"{self.setting_opt101_min_threshold_value_to_activate_variable.get()},"
                f"{self.setting_opt101_detection_threshold_variable.get()},"
                f"{self.setting_opt101_detection_threshold_repeated_high_variable.get()},"
                f"{self.setting_opt101_detection_threshold_repeated_low_variable.get()},"
                f"{self.setting_opt101_enable_ignore_during_ir_variable.get()},"
                f"{self.setting_opt101_enable_smart_duplicate_frame_handling_variable.get()},"
                f"{self.setting_opt101_output_stats_variable.get()},"
                f"{self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable.get()}"
            )
            print(command)
            self.main_app.emitter_serial.line_reader.command(command)

    def click_save_settings_to_eeprom(self):
        if self.main_app.emitter_serial:
            self.click_update_settings_on_emitter()
            self.main_app.emitter_serial.line_reader.command(f"8")

    def click_save_visible_settings_to_disk(self):
        file_name = tkinter.filedialog.asksaveasfilename(
            title="Save Emitter Settings to Disk",
            initialdir=os.path.join(base_path, "settings"),
            filetypes=[("Emitter Settings FIle", "*.emitter_settings.json")],
            defaultextension=".emitter_settings.json",
        )
        if file_name:
            f = open(file_name, "w")
            json.dump(
                {
                    "ir_protocol": self.setting_ir_protocol_variable.get(),
                    "ir_frame_delay": self.setting_ir_frame_delay_variable.get(),
                    "ir_frame_duration": self.setting_ir_frame_duration_variable.get(),
                    "ir_signal_spacing": self.setting_ir_signal_spacing_variable.get(),
                    "opt101_block_signal_detection_delay": self.setting_opt101_block_signal_detection_delay_variable.get(),
                    "opt101_min_threshold_value_to_activate": self.setting_opt101_min_threshold_value_to_activate_variable.get(),
                    "opt101_detection_threshold": self.setting_opt101_detection_threshold_variable.get(),
                    "opt101_detection_threshold_repeated_high": self.setting_opt101_detection_threshold_repeated_high_variable.get(),
                    "opt101_detection_threshold_repeated_low": self.setting_opt101_detection_threshold_repeated_low_variable.get(),
                    "opt101_enable_ignore_during_ir": self.setting_opt101_enable_ignore_during_ir_variable.get(),
                    "opt101_enable_smart_duplicate_frame_handling": self.setting_opt101_enable_smart_duplicate_frame_handling_variable.get(),
                    "opt101_output_stats": self.setting_opt101_output_stats_variable.get(),
                    "opt101_enable_frequency_analysis_based_duplicate_frame_detection": self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable.get(),
                },
                f,
                indent=2,
            )
            f.close()

    def click_load_visisble_settings_from_disk(self):
        file_name = tkinter.filedialog.askopenfilename(
            title="Load Emitter Settings from Disk",
            initialdir=os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "settings"
            ),
            filetypes=[("Emitter Settings FIle", "*.emitter_settings.json")],
        )
        if file_name:
            f = open(file_name, "r")
            settings = json.load(f)
            f.close()
            self.setting_ir_protocol_variable.set(settings["ir_protocol"])
            self.setting_ir_frame_delay_variable.set(settings["ir_frame_delay"])
            self.setting_ir_frame_duration_variable.set(settings["ir_frame_duration"])
            self.setting_ir_signal_spacing_variable.set(settings["ir_signal_spacing"])
            self.setting_opt101_block_signal_detection_delay_variable.set(
                settings["opt101_block_signal_detection_delay"]
            )
            self.setting_opt101_min_threshold_value_to_activate_variable.set(
                settings["opt101_min_threshold_value_to_activate"]
            )
            self.setting_opt101_detection_threshold_variable.set(
                settings["opt101_detection_threshold"]
            )
            self.setting_opt101_detection_threshold_repeated_high_variable.set(
                settings["opt101_detection_threshold_repeated_high"]
            )
            self.setting_opt101_detection_threshold_repeated_low_variable.set(
                settings["opt101_detection_threshold_repeated_low"]
            )
            self.setting_opt101_enable_ignore_during_ir_variable.set(
                settings["opt101_enable_ignore_during_ir"]
            )
            self.setting_opt101_enable_smart_duplicate_frame_handling_variable.set(
                settings["opt101_enable_smart_duplicate_frame_handling"]
            )
            self.setting_opt101_output_stats_variable.set(
                settings["opt101_output_stats"]
            )
            self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable.set(
                settings[
                    "opt101_enable_frequency_analysis_based_duplicate_frame_detection"
                ]
            )

    def click_set_glasses_mode(self):
        if self.main_app.emitter_serial:
            command = f"7," f"{self.setting_glasses_mode_variable.get()}"
            print(command)
            self.main_app.emitter_serial.line_reader.command(command)

    def click_close(self):
        self.top.destroy()


class OpenFileDialog:

    LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION = "Load Video Profile From History"
    VIDEO_HISTORY_MAX_SIZE = 10

    def __init__(self, parent):
        top = self.top = tkinter.Toplevel(parent)

        self.perform_open = False
        row_count = 0

        # Add History Frame with History Dropdown which populates below fields when any entry is selected.
        self.history_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "video_history.json"
        )
        if os.path.exists(self.history_file_path):
            f = open(self.history_file_path, "r")
            self.video_history = json.load(f)
            f.close()
        else:
            self.video_history = []
        self.video_history_options = [
            OpenFileDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        ]
        self.video_history_options.extend(
            reversed(
                [
                    f"{idx} {vh['history_datetime']} {vh['video_file_name']}"
                    for idx, vh in enumerate(self.video_history)
                ]
            )
        )
        self.video_history_frame = tkinter.Frame(top)
        self.video_history_clicked = tkinter.StringVar()
        self.video_history_clicked.set(
            OpenFileDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        )
        self.video_history_dropdown = tkinter.OptionMenu(
            self.video_history_frame,
            self.video_history_clicked,
            *(self.video_history_options),
        )
        self.video_history_dropdown.pack(padx=5, side=tkinter.LEFT)
        self.video_history_load_button = tkinter.Button(
            self.video_history_frame,
            text="Load",
            command=self.load_video_profile_from_history,
        )
        self.video_history_load_button.pack(padx=5, side=tkinter.LEFT)
        self.video_history_load_button_tooltip = idlelib.tooltip.Hovertip(
            self.video_history_load_button,
            "Load the settings from this video history entry below.",
            hover_delay=100,
        )
        self.video_history_remove_button = tkinter.Button(
            self.video_history_frame,
            text="Remove",
            command=self.remove_video_profile_from_history,
        )
        self.video_history_remove_button.pack(padx=5, side=tkinter.LEFT)
        self.video_history_remove_button_tooltip = idlelib.tooltip.Hovertip(
            self.video_history_remove_button,
            "Remove this video history entry from the list.",
            hover_delay=100,
        )
        self.video_history_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.video_file_frame = tkinter.Frame(top)
        self.video_file_name = ""
        self.video_file_label = tkinter.Label(
            self.video_file_frame, text="Video File: "
        )
        self.video_file_label.pack(padx=5, side=tkinter.LEFT)
        self.video_file_location_label = tkinter.Label(self.video_file_frame, text="")
        self.video_file_location_label.pack(padx=5, side=tkinter.LEFT)
        self.video_file_select_button = tkinter.Button(
            self.video_file_frame, text="Select", command=self.select_video_file
        )
        self.video_file_select_button.pack(padx=5, side=tkinter.LEFT)
        # self.video_file_frame.pack()
        self.video_file_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.subtitle_file_frame = tkinter.Frame(top)
        self.subtitle_file_name = ""
        self.subtitle_file_label = tkinter.Label(
            self.subtitle_file_frame, text="Subtitle File: "
        )
        self.subtitle_file_label.pack(padx=5, side=tkinter.LEFT)
        self.subtitle_file_location_label = tkinter.Label(
            self.subtitle_file_frame, text=""
        )
        self.subtitle_file_location_label.pack(padx=5, side=tkinter.LEFT)
        self.subtitle_file_select_button = tkinter.Button(
            self.subtitle_file_frame, text="Select", command=self.select_subtitle_file
        )
        self.subtitle_file_select_button.pack(padx=5, side=tkinter.LEFT)
        # self.subtitle_file_frame.pack()
        self.subtitle_file_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.subtitle_font_frame = tkinter.Frame(top)
        self.subtitle_font_variable = tkinter.StringVar(top)
        if os.name == "nt":
            self.subtitle_font_variable.set("MS Gothic")
        else:
            self.subtitle_font_variable.set("Noto Sans CJK JP")
        self.subtitle_font_label = tkinter.Label(
            self.subtitle_font_frame, text="Subtitle Font: "
        )
        self.subtitle_font_label.pack(padx=5, side=tkinter.LEFT)
        self.subtitle_font_entry = tkinter.Entry(
            self.subtitle_font_frame, textvariable=self.subtitle_font_variable
        )
        self.subtitle_font_entry.pack(padx=5, side=tkinter.LEFT)
        # self.subtitle_font_frame.pack()
        self.subtitle_font_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.subtitle_size_frame = tkinter.Frame(top)
        self.subtitle_size_variable = tkinter.StringVar(top)
        self.subtitle_size_variable.set("60")
        self.subtitle_size_label = tkinter.Label(
            self.subtitle_size_frame, text="Subtitle Size: "
        )
        self.subtitle_size_label.pack(padx=5, side=tkinter.LEFT)
        self.subtitle_size_option_menu = tkinter.OptionMenu(
            self.subtitle_size_frame,
            self.subtitle_size_variable,
            "30",
            "40",
            "50",
            "60",
            "70",
            "80",
            "90",
            "100",
        )
        self.subtitle_size_option_menu.pack(padx=5, side=tkinter.LEFT)
        # self.subtitle_size_frame.pack()
        self.subtitle_size_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.subtitle_depth_frame = tkinter.Frame(top)
        self.subtitle_depth_variable = tkinter.StringVar(top)
        self.subtitle_depth_variable.set("20")
        self.subtitle_depth_label = tkinter.Label(
            self.subtitle_depth_frame, text="Subtitle Depth: "
        )
        self.subtitle_depth_label.pack(padx=5, side=tkinter.LEFT)
        self.subtitle_depth_entry = tkinter.Entry(
            self.subtitle_depth_frame, textvariable=self.subtitle_depth_variable
        )
        self.subtitle_depth_entry.pack(padx=5, side=tkinter.LEFT)
        self.subtitle_depth_tooltip = idlelib.tooltip.Hovertip(
            self.subtitle_depth_frame,
            "The relative depth of subtitles to the screen, negative numbers are behind, positive numbers are in front.",
            hover_delay=100,
        )
        # self.subtitle_depth_frame.pack()
        self.subtitle_depth_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.subtitle_vertical_offset_frame = tkinter.Frame(top)
        self.subtitle_vertical_offset_variable = tkinter.StringVar(top)
        self.subtitle_vertical_offset_variable.set("150")
        self.subtitle_vertical_offset_label = tkinter.Label(
            self.subtitle_vertical_offset_frame, text="Subtitle Vertical Offset: "
        )
        self.subtitle_vertical_offset_label.pack(padx=5, side=tkinter.LEFT)
        self.subtitle_vertical_offset_entry = tkinter.Entry(
            self.subtitle_vertical_offset_frame,
            textvariable=self.subtitle_vertical_offset_variable,
        )
        self.subtitle_vertical_offset_entry.pack(padx=5, side=tkinter.LEFT)
        self.subtitle_vertical_offset_tooltip = idlelib.tooltip.Hovertip(
            self.subtitle_vertical_offset_frame,
            "The vertical offset for subtitles from the bottom of the screen measured in pixels. There may be minor ghosting at bottom of screen so we default to 150 pixels.",
            hover_delay=100,
        )
        # self.subtitle_vertical_offset_frame.pack()
        self.subtitle_vertical_offset_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.subtitle_offset_frame = tkinter.Frame(top)
        self.subtitle_offset_variable = tkinter.StringVar(top)
        self.subtitle_offset_variable.set("0")
        self.subtitle_offset_label = tkinter.Label(
            self.subtitle_offset_frame, text="Subtitle Time Offset (in seconds): "
        )
        self.subtitle_offset_label.pack(padx=5, side=tkinter.LEFT)
        self.subtitle_offset_entry = tkinter.Entry(
            self.subtitle_offset_frame, textvariable=self.subtitle_offset_variable
        )
        self.subtitle_offset_entry.pack(padx=5, side=tkinter.LEFT)
        # self.subtitle_offset_frame.pack()
        self.subtitle_offset_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.frame_packing_frame = tkinter.Frame(top)
        self.frame_packing_variable = tkinter.StringVar(top)
        self.frame_packing_variable.set("side-by-side-full")
        self.frame_packing_label = tkinter.Label(
            self.frame_packing_frame, text="Frame Packing: "
        )
        self.frame_packing_label.pack(padx=5, side=tkinter.LEFT)
        self.frame_packing_option_menu = tkinter.OptionMenu(
            self.frame_packing_frame,
            self.frame_packing_variable,
            "side-by-side-half",
            "side-by-side-full",
            "over-and-under-half",
            "over-and-under-full",
        )
        self.frame_packing_option_menu.pack(padx=5, side=tkinter.LEFT)
        # self.frame_packing_frame.pack()
        self.frame_packing_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.right_eye_frame = tkinter.Frame(top)
        self.right_eye_variable = tkinter.StringVar(top)
        self.right_eye_variable.set("right")
        self.right_eye_label = tkinter.Label(
            self.right_eye_frame, text="Right Eye On: "
        )
        self.right_eye_label.pack(padx=5, side=tkinter.LEFT)
        self.right_eye_option_menu = tkinter.OptionMenu(
            self.right_eye_frame,
            self.right_eye_variable,
            "right",
            "left",
            "top",
            "bottom",
        )
        self.right_eye_option_menu.pack(padx=5, side=tkinter.LEFT)
        # self.right_eye_frame.pack()
        self.right_eye_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.target_framerate_frame = tkinter.Frame(top)
        self.target_framerate_variable = tkinter.StringVar(top)
        self.target_framerate_variable.set(DEFAULT_TARGET_FRAMERATE)
        self.target_framerate_label = tkinter.Label(
            self.target_framerate_frame, text="Target Framerate: "
        )
        self.target_framerate_label.pack(padx=5, side=tkinter.LEFT)
        self.target_framerate_option_menu = tkinter.OptionMenu(
            self.target_framerate_frame,
            self.target_framerate_variable,
            "0",
            "50",
            "59.98",
            "60",
            "74.99",
            "75",
            "90",
            "120",
        )
        self.target_framerate_option_menu.pack(padx=5, side=tkinter.LEFT)
        # self.target_framerate_frame.pack()
        self.target_framerate_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.video_resolution_frame = tkinter.Frame(top)
        self.video_resolution_variable = tkinter.StringVar(top)
        self.video_resolution_variable.set("1920x1080")
        self.video_resolution_label = tkinter.Label(
            self.video_resolution_frame, text="Video Resolution: "
        )
        self.video_resolution_label.pack(padx=5, side=tkinter.LEFT)
        self.video_resolution_option_menu = tkinter.OptionMenu(
            self.video_resolution_frame,
            self.video_resolution_variable,
            "1920x1080",
            "1280x720",
        )
        self.video_resolution_option_menu.pack(padx=5, side=tkinter.LEFT)
        # self.video_resolution_frame.pack()
        self.video_resolution_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.display_resolution_frame = tkinter.Frame(top)
        self.display_resolution_variable = tkinter.StringVar(top)
        self.display_resolution_variable.set(DEFAULT_DISPLAY_RESOLUTION)
        self.display_resolution_label = tkinter.Label(
            self.display_resolution_frame, text="Display Resolution: "
        )
        self.display_resolution_label.pack(padx=5, side=tkinter.LEFT)
        self.display_resolution_option_menu = tkinter.OptionMenu(
            self.display_resolution_frame,
            self.display_resolution_variable,
            "2560x1080",
            "1920x1080",
            "1280x720",
        )
        self.display_resolution_option_menu.pack(padx=5, side=tkinter.LEFT)
        # self.display_resolution_frame.pack()
        self.display_resolution_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.display_size_frame = tkinter.Frame(top)
        self.display_size_variable = tkinter.StringVar(top)
        self.display_size_variable.set(DEFAULT_DISPLAY_SIZE)
        self.display_size_label = tkinter.Label(
            self.display_size_frame, text="Display Size (in inches): "
        )
        self.display_size_label.pack(padx=5, side=tkinter.LEFT)
        self.display_size_entry = tkinter.Entry(
            self.display_size_frame, textvariable=self.display_size_variable
        )
        self.display_size_entry.pack(padx=5, side=tkinter.LEFT)
        self.display_size_tooltip = idlelib.tooltip.Hovertip(
            self.display_size_frame,
            "Specifying the correct display size (provided in inches), allows the appropriate sizing of the trigger boxes to match the sensors unit.",
            hover_delay=100,
        )
        # self.display_size_frame.pack()
        self.display_size_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.whitebox_brightness_frame = tkinter.Frame(top)
        self.whitebox_brightness_variable = tkinter.StringVar(top)
        self.whitebox_brightness_variable.set("255")
        self.whitebox_brightness_label = tkinter.Label(
            self.whitebox_brightness_frame, text="Whitebox Brightness: "
        )
        self.whitebox_brightness_label.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_brightness_entry = tkinter.Entry(
            self.whitebox_brightness_frame,
            textvariable=self.whitebox_brightness_variable,
        )
        self.whitebox_brightness_entry.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_brightness_tooltip = idlelib.tooltip.Hovertip(
            self.whitebox_brightness_frame,
            "The whitebox brightness setting (0 black to 255 white) lets users lower the brightness of the white boxes to help aleviate concerns of OLED burn in.",
            hover_delay=100,
        )
        # self.whitebox_brightness_frame.pack()
        self.whitebox_brightness_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.use_separate_process_frame = tkinter.Frame(top)
        self.use_separate_process_variable = tkinter.BooleanVar(top)
        self.use_separate_process_variable.set(False)
        self.use_separate_process_label = tkinter.Label(
            self.use_separate_process_frame, text="Use Separate Process: "
        )
        self.use_separate_process_label.pack(padx=5, side=tkinter.LEFT)
        self.use_separate_process_option_menu = tkinter.Checkbutton(
            self.use_separate_process_frame, variable=self.use_separate_process_variable
        )
        self.use_separate_process_option_menu.pack(padx=5, side=tkinter.LEFT)
        self.use_separate_process_tooltip = idlelib.tooltip.Hovertip(
            self.use_separate_process_frame,
            "Use a separate process to perform page flipping, this requires additional CPU and memory copies but may help reduce the number of duplicate/dropped frames.",
            hover_delay=100,
        )
        # self.use_separate_process_frame.pack()
        self.use_separate_process_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.calibration_mode_frame = tkinter.Frame(top)
        self.calibration_mode_variable = tkinter.BooleanVar(top)
        self.calibration_mode_variable.set(False)
        self.calibration_mode_label = tkinter.Label(
            self.calibration_mode_frame, text="Calibration Mode: "
        )
        self.calibration_mode_label.pack(padx=5, side=tkinter.LEFT)
        self.calibration_mode_option_menu = tkinter.Checkbutton(
            self.calibration_mode_frame, variable=self.calibration_mode_variable
        )
        self.calibration_mode_option_menu.pack(padx=5, side=tkinter.LEFT)
        self.calibration_mode_tooltip = idlelib.tooltip.Hovertip(
            self.calibration_mode_frame,
            "Calibration mode shows a reticule to help with alignment of the sensor bar \nand also allows for adjustment of emitter frame_delay and frame_duration using hotkeys as instructed on the OSD. \nTo adjust emitter timing parameters you will need to ensure the emitter settings dialog is also open and connected to the emitter. \nTo optimize emitter settings adjustment it is recommended to use the red/blue or black/white test videos.",
            hover_delay=100,
        )
        # self.calibration_mode_frame.pack()
        self.calibration_mode_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.open_button = tkinter.Button(top, text="Open", command=self.send)
        # self.open_button.pack(side=tkinter.BOTTOM)
        self.open_button.grid(row=row_count, column=0)

    def load_video_profile_from_history(self):
        if (
            self.video_history_clicked.get()
            == OpenFileDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        ):
            return
        selected_index = int(self.video_history_clicked.get().split()[0])
        selected_video_history = self.video_history[selected_index]
        self.video_file_name = selected_video_history["video_file_name"]
        self.video_file_location_label.config(text=self.video_file_name)
        self.subtitle_file_name = selected_video_history["subtitle_file_name"]
        self.subtitle_file_location_label.config(text=self.subtitle_file_name)
        self.subtitle_font_variable.set(selected_video_history["subtitle_font"])
        self.subtitle_size_variable.set(selected_video_history["subtitle_size"])
        self.subtitle_depth_variable.set(selected_video_history["subtitle_depth"])
        self.subtitle_vertical_offset_variable.set(
            selected_video_history["subtitle_vertical_offset"]
        )
        self.subtitle_offset_variable.set(selected_video_history["subtitle_offset"])
        self.frame_packing_variable.set(selected_video_history["frame_packing"])
        self.right_eye_variable.set(selected_video_history["right_eye"])
        self.target_framerate_variable.set(selected_video_history["target_framerate"])
        self.video_resolution_variable.set(selected_video_history["video_resolution"])
        self.display_resolution_variable.set(
            selected_video_history["display_resolution"]
        )
        self.display_size_variable.set(selected_video_history["display_size"])
        self.whitebox_brightness_variable.set(
            selected_video_history["whitebox_brightness"]
        )
        self.use_separate_process_variable.set(
            selected_video_history["use_separate_process"]
        )
        self.calibration_mode_variable.set(
            selected_video_history.get("calibration_mode", False)
        )

    def remove_video_profile_from_history(self):
        if (
            self.video_history_clicked.get()
            == OpenFileDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        ):
            return
        selected_index = int(self.video_history_clicked.get().split()[0])
        self.video_history.pop(selected_index)
        f = open(self.history_file_path, "w")
        json.dump(self.video_history, f, indent=2)
        f.close()
        self.video_history_options = [
            OpenFileDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        ]
        self.video_history_options.extend(
            reversed(
                [
                    f"{idx} {vh['history_datetime']} {vh['video_file_name']}"
                    for idx, vh in enumerate(self.video_history)
                ]
            )
        )
        self.video_history_clicked.set(
            OpenFileDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        )
        menu = self.video_history_dropdown["menu"]
        menu.delete(1, "end")
        for menu_option in self.video_history_options[1:]:
            menu.add_command(
                label=menu_option,
                command=_setit(self.video_history_clicked, menu_option),
            )

    def select_video_file(self):
        self.video_file_name = tkinter.filedialog.askopenfilename()
        self.video_file_location_label.config(text=self.video_file_name)

    def select_subtitle_file(self):
        self.subtitle_file_name = tkinter.filedialog.askopenfilename()
        self.subtitle_file_location_label.config(text=self.subtitle_file_name)

    def send(self):
        new_video_history_entry = {
            "video_file_name": self.video_file_name,
            "subtitle_file_name": self.subtitle_file_name,
            "subtitle_font": self.subtitle_font_variable.get(),
            "subtitle_size": self.subtitle_size_variable.get(),
            "subtitle_depth": self.subtitle_depth_variable.get(),
            "subtitle_vertical_offset": self.subtitle_vertical_offset_variable.get(),
            "subtitle_offset": self.subtitle_offset_variable.get(),
            "frame_packing": self.frame_packing_variable.get(),
            "right_eye": self.right_eye_variable.get(),
            "target_framerate": self.target_framerate_variable.get(),
            "video_resolution": self.video_resolution_variable.get(),
            "display_resolution": self.display_resolution_variable.get(),
            "display_size": self.display_size_variable.get(),
            "whitebox_brightness": self.whitebox_brightness_variable.get(),
            "use_separate_process": self.use_separate_process_variable.get(),
            "calibration_mode": self.calibration_mode_variable.get(),
        }
        save_history = True
        if (
            self.video_history_clicked.get()
            != OpenFileDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        ):
            selected_index = self.video_history_clicked.get().split()[0]
            selected_video_history = self.video_history[int(selected_index)]
            new_video_history_entry["history_datetime"] = selected_video_history[
                "history_datetime"
            ]
            if new_video_history_entry == selected_video_history:
                save_history = False
        if save_history:
            new_video_history_entry["history_datetime"] = (
                datetime.datetime.now().strftime("%Y-%m-%d %H%M%S")
            )
            self.video_history.append(new_video_history_entry)
            if len(self.video_history) > OpenFileDialog.VIDEO_HISTORY_MAX_SIZE:
                self.video_history = self.video_history[1:]
            f = open(self.history_file_path, "w")
            json.dump(self.video_history, f, indent=2)
            f.close()
        self.perform_open = True
        self.top.destroy()


class TopWindow:
    def __init__(self):
        self.player = None
        self.video_open = False
        self.paused = False
        self.close = False
        self.emitter_serial = None

        self.pageflipglsink = None
        self.subtitle3dsink = None

        self.window = window = tkinter.Tk()
        window.wm_attributes("-topmost", True)
        try:
            window.wm_attributes(
                "-type", "toolbar"
            )  # no titlebar and not always on top (starts perfectly at top of screen)
        except Exception:
            window.wm_attributes("-toolwindow", True)
        # window.wm_attributes('-type', 'dock') # no titlebar and always on top of regular window manager (but starts off top of screen)
        window.title("")
        window.geometry("+300+0")
        # window.geometry("+2000+0")
        window.update_idletasks()
        self._offsetx = -self.window.winfo_rootx()
        self._offsety = -self.window.winfo_rooty()

        top_frame = tkinter.Frame(window)
        top_frame.pack(fill="x", expand=1, pady=5, padx=25, anchor="n")
        open_emitter_settings_button_image = svg_to_imagetk_photoimage(
            "./images/sliders2.svg"
        )
        open_emitter_settings_button = tkinter.Button(
            top_frame,
            text="Open Emitter Settings",
            image=open_emitter_settings_button_image,
            highlightthickness=0,
            bd=0,
        )
        open_emitter_settings_button.tk_img = open_emitter_settings_button_image
        open_emitter_settings_button_tooltip = (  # @UnusedVariable
            idlelib.tooltip.Hovertip(  # @UnusedVariable
                open_emitter_settings_button,
                "Open emitter settings to tweak timing parameters.",
                hover_delay=100,
            )
        )
        open_emitter_settings_button.pack(padx=5, side=tkinter.LEFT)
        open_emitter_settings_button.bind(
            "<Button-1>", self.click_open_emitter_settings_button
        )
        open_video_file_button_image = svg_to_imagetk_photoimage(
            "./images/folder2-open.svg"
        )
        open_video_file_button = tkinter.Button(
            top_frame,
            text="Open Video File",
            image=open_video_file_button_image,
            highlightthickness=0,
            bd=0,
        )
        open_video_file_button.tk_img = open_video_file_button_image
        open_video_file_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            open_video_file_button, "Open a video file for playback.", hover_delay=100
        )
        open_video_file_button.pack(padx=5, side=tkinter.LEFT)
        open_video_file_button.bind("<Button-1>", self.click_open_video_file_button)
        stop_video_button_image = svg_to_imagetk_photoimage("./images/stop-fill.svg")
        stop_video_button = tkinter.Button(
            top_frame,
            text="Stop Video",
            image=stop_video_button_image,
            highlightthickness=0,
            bd=0,
        )
        stop_video_button.tk_img = stop_video_button_image
        stop_video_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            stop_video_button, "Click to stop and close current video.", hover_delay=100
        )
        stop_video_button.pack(padx=5, side=tkinter.LEFT)
        stop_video_button.bind("<Button-1>", self.click_stop_video_button)
        fullscreen_button_image = svg_to_imagetk_photoimage(
            "./images/arrows-fullscreen.svg"
        )
        fullscreen_button = tkinter.Button(
            top_frame,
            text="Fullscreen/Windowed (F11)",
            image=fullscreen_button_image,
            highlightthickness=0,
            bd=0,
        )
        fullscreen_button.tk_img = fullscreen_button_image
        fullscreen_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            fullscreen_button, "Toggle fullscreen (F11).", hover_delay=100
        )
        fullscreen_button.pack(padx=5, side=tkinter.LEFT)
        fullscreen_button.bind("<Button-1>", self.toggle_fullscreen)
        flip_right_and_left_button_image = svg_to_imagetk_photoimage(
            "./images/flip-right-and-left.svg"
        )
        flip_right_and_left_button = tkinter.Button(
            top_frame,
            text="Flip Right and Left (F)",
            image=flip_right_and_left_button_image,
            highlightthickness=0,
            bd=0,
        )
        flip_right_and_left_button.tk_img = flip_right_and_left_button_image
        flip_right_and_left_button_tooltip = (  # @UnusedVariable
            idlelib.tooltip.Hovertip(
                fullscreen_button, "Flip Right and Left (F).", hover_delay=100
            )
        )
        flip_right_and_left_button.pack(padx=5, side=tkinter.LEFT)
        flip_right_and_left_button.bind("<Button-1>", self.flip_right_and_left)
        tooltip_number_text = (
            "\nUse numbers 0-9 to fast seek from 0% to 90% through the video."
        )
        backward_big_button_image = svg_to_imagetk_photoimage(
            "./images/rewind-3-fill.svg"
        )
        backward_big_button = tkinter.Button(
            top_frame,
            text="Back 60s (shift-left)",
            image=backward_big_button_image,
            highlightthickness=0,
            bd=0,
        )
        backward_big_button.tk_img = backward_big_button_image
        backward_big_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            backward_big_button,
            f"Rewind 60s (Shift-Left-Arrow).{tooltip_number_text}",
            hover_delay=100,
        )
        backward_big_button.pack(padx=5, side=tkinter.LEFT)
        backward_big_button.bind(
            "<Button-1>", functools.partial(self.perform_seek, "seek_backward_big")
        )
        backward_small_button_image = svg_to_imagetk_photoimage(
            "./images/rewind-fill.svg"
        )
        backward_small_button = tkinter.Button(
            top_frame,
            text="Back 5s (left)",
            image=backward_small_button_image,
            highlightthickness=0,
            bd=0,
        )
        backward_small_button.tk_img = backward_small_button_image
        backward_small_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            backward_small_button,
            f"Rewind 5s (Left-Arrow).{tooltip_number_text}",
            hover_delay=100,
        )
        backward_small_button.pack(padx=5, side=tkinter.LEFT)
        backward_small_button.bind(
            "<Button-1>", functools.partial(self.perform_seek, "seek_backward_small")
        )
        play_pause_button_image = svg_to_imagetk_photoimage(
            "./images/play-pause-fill.svg"
        )
        play_pause_button = tkinter.Button(
            top_frame,
            text="Play/Pause (Space)",
            image=play_pause_button_image,
            highlightthickness=0,
            bd=0,
        )
        play_pause_button.tk_img = play_pause_button_image
        play_pause_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            play_pause_button,
            "Click to play/pause current video. (Space)",
            hover_delay=100,
        )
        play_pause_button.pack(padx=5, side=tkinter.LEFT)
        play_pause_button.bind("<Button-1>", self.toggle_paused)
        forward_small_button_image = svg_to_imagetk_photoimage(
            "./images/fast-forward-fill.svg"
        )
        forward_small_button = tkinter.Button(
            top_frame,
            text="Forward 5s (right)",
            image=forward_small_button_image,
            highlightthickness=0,
            bd=0,
        )
        forward_small_button.tk_img = forward_small_button_image
        forward_small_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            forward_small_button,
            f"Fastforward 5s (Right-Arrow).{tooltip_number_text}",
            hover_delay=100,
        )
        forward_small_button.pack(padx=5, side=tkinter.LEFT)
        forward_small_button.bind(
            "<Button-1>", functools.partial(self.perform_seek, "seek_forward_small")
        )
        forward_big_button_image = svg_to_imagetk_photoimage(
            "./images/fast-forward-3-fill.svg"
        )
        forward_big_button = tkinter.Button(
            top_frame,
            text="Forward 60s (shift-right)",
            image=forward_big_button_image,
            highlightthickness=0,
            bd=0,
        )
        forward_big_button.tk_img = forward_big_button_image
        forward_big_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            forward_big_button,
            f"Fastforward 60s (Shift-Right-Arrow).{tooltip_number_text}",
            hover_delay=100,
        )
        forward_big_button.pack(padx=5, side=tkinter.LEFT)
        forward_big_button.bind(
            "<Button-1>", functools.partial(self.perform_seek, "seek_forward_big")
        )
        close_button_image = svg_to_imagetk_photoimage("./images/x.svg")
        close_button = tkinter.Button(
            top_frame,
            text="Close (Esc)",
            image=close_button_image,
            highlightthickness=0,
            bd=0,
        )
        close_button.tk_img = close_button_image
        close_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            close_button, f"Close 3D player (Escape).", hover_delay=100
        )
        close_button.pack(padx=5, side=tkinter.LEFT)
        close_button.bind("<Button-1>", self.close_player)

        # window.geometry('100x300')
        window.bind("<Button-1>", self.click_mouse)
        window.bind("<B1-Motion>", self.move_mouse)
        # https://www.tcl.tk/man/tcl8.4/TkCmd/keysyms.html
        window.bind("<F11>", self.toggle_fullscreen)
        window.bind("f", self.flip_right_and_left)
        window.bind("<Escape>", self.stop_or_close_player)
        window.bind("<space>", self.toggle_paused)
        # add seek with left and right arrow keys (use shift to seek farther)

    def move_mouse(self, event=None):
        if ".!frame.!button" in str(event.widget):
            return "break"
        # print(('move',dir(event),event.widget,str(event.widget),event.x,event.x_root,event.y,event.y_root,self._offsetx, self._offsety))
        x = self.window.winfo_pointerx() - self._offsetx
        y = self.window.winfo_pointery() - self._offsety
        self.window.geometry(f"+{x}+{y}")
        return "break"

    def click_mouse(self, event=None):  # @UnusedVariable
        self._offsetx = self.window.winfo_pointerx() - self.window.winfo_rootx()
        self._offsety = self.window.winfo_pointery() - self.window.winfo_rooty()
        # print(('click',dir(event),event.widget,str(event.widget),event.x,event.x_root,event.y,event.y_root,self._offsetx, self._offsety))
        return "break"

    def toggle_fullscreen(self, event=None):  # @UnusedVariable
        self.pageflipglsink.set_property(
            "fullscreen", not self.pageflipglsink.get_property("fullscreen")
        )
        return "break"

    def flip_right_and_left(self, event=None):  # @UnusedVariable
        current_setting = self.pageflipglsink.get_property("right-eye")
        if current_setting == "right":
            self.pageflipglsink.set_property("right-eye", "left")
        elif current_setting == "left":
            self.pageflipglsink.set_property("right-eye", "right")
        elif current_setting == "top":
            self.pageflipglsink.set_property("right-eye", "bottom")
        elif current_setting == "bottom":
            self.pageflipglsink.set_property("right-eye", "top")

    def set_menu_on_top(self, put_on_top, event=None):  # @UnusedVariable
        if (
            self.pageflipglsink
            and self.pageflipglsink.get_property("fullscreen")
            and not put_on_top
        ):
            self.window.wm_attributes("-topmost", False)
            self.window.wm_attributes("-alpha", 0.0)
        else:
            self.window.wm_attributes("-topmost", True)
            self.window.wm_attributes("-alpha", 1.0)

    def stop_player(self, event=None):  # @UnusedVariable
        print("stop_player")
        self.player.set_state(Gst.State.NULL)
        self.video_open = False
        if self.emitter_serial is not None:
            self.emitter_serial.pageflipglsink = None
        self.pageflipglsink.set_property("close", True)
        self.set_menu_on_top(True)
        # Gst.deinit()
        return "break"

    def close_player(self, event=None):  # @UnusedVariable
        if self.video_open:
            self.stop_player()
        self.close = True
        self.set_menu_on_top(True)
        if self.emitter_serial:
            self.emitter_serial.close()
        return "break"

    def stop_or_close_player(self, event=None):  # @UnusedVariable
        if self.video_open:
            self.stop_player()
        else:
            self.close_player()

    def toggle_paused(self, event=None):  # @UnusedVariable
        self.paused = not self.paused
        if self.paused:
            self.player.set_state(Gst.State.PAUSED)
        else:
            self.player.set_state(Gst.State.PLAYING)
        return "break"

    def perform_seek(self, seek_command, event=None):  # @UnusedVariable
        query_position = self.player.query_position(Gst.Format.TIME)[1]
        query_duration = self.player.query_duration(Gst.Format.TIME)[1]
        seek_position = 0
        seek_flags = Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT
        if "seek_percent" in seek_command:
            seek_position = query_duration // 10 * int(r.split("_")[2])
            seek_flags |= Gst.SeekFlags.SNAP_BEFORE
        elif "seek_forward_big" == seek_command:
            seek_position = query_position + Gst.SECOND * 60
            seek_flags |= Gst.SeekFlags.SNAP_AFTER
        elif "seek_forward_small" == seek_command:
            seek_position = query_position + Gst.SECOND * 5
            seek_flags |= Gst.SeekFlags.SNAP_AFTER
        elif "seek_backward_big" == seek_command:
            seek_position = query_position - Gst.SECOND * 60
            seek_flags |= Gst.SeekFlags.SNAP_BEFORE
        elif "seek_backward_small" == seek_command:
            seek_position = query_position - Gst.SECOND * 5
            seek_flags |= Gst.SeekFlags.SNAP_BEFORE
        if seek_position:
            # https://gstreamer.freedesktop.org/documentation/gstreamer/gstsegment.html?gi-language=python#GstSeekFlags
            # 'ACCURATE', 'FLUSH', 'KEY_UNIT', 'NONE', 'SEGMENT', 'SKIP', 'SNAP_AFTER', 'SNAP_BEFORE', 'SNAP_NEAREST', 'TRICKMODE', 'TRICKMODE_KEY_UNITS', 'TRICKMODE_NO_AUDIO'
            self.player.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                max(seek_position, 0),
            )

    def click_open_emitter_settings_button(self, event=None):  # @UnusedVariable
        self.emitter_settings_dialog = EmitterSettingsDialog(self.window, self)
        # self.window.wait_window(self.emitter_settings_dialog.top)

    def click_open_video_file_button(self, event=None):  # @UnusedVariable
        open_file_dialog = OpenFileDialog(self.window)
        self.window.wait_window(open_file_dialog.top)

        if not open_file_dialog.perform_open:
            return

        video_file_name = open_file_dialog.video_file_name
        subtitle_file_name = open_file_dialog.subtitle_file_name
        subtitle_font = open_file_dialog.subtitle_font_variable.get()
        subtitle_size = open_file_dialog.subtitle_size_variable.get()
        subtitle_depth = open_file_dialog.subtitle_depth_variable.get()
        subtitle_vertical_offset = (
            open_file_dialog.subtitle_vertical_offset_variable.get()
        )
        subtitle_offset = float(open_file_dialog.subtitle_offset_variable.get())
        frame_packing = open_file_dialog.frame_packing_variable.get()
        right_eye = open_file_dialog.right_eye_variable.get()
        target_framerate = open_file_dialog.target_framerate_variable.get()
        video_resolution = open_file_dialog.video_resolution_variable.get()
        display_resolution = open_file_dialog.display_resolution_variable.get()
        display_size = open_file_dialog.display_size_variable.get()
        whitebox_brightness = open_file_dialog.whitebox_brightness_variable.get()
        use_separate_process = open_file_dialog.use_separate_process_variable.get()
        calibration_mode = open_file_dialog.calibration_mode_variable.get()
        # print(frame_packing)
        # print(right_eye)
        # print(video_resolution)
        # print(display_resolution)
        if video_file_name == "":
            return
        video_file_path = os.path.realpath(video_file_name)
        video_file_path = "file:///" + video_file_path.replace("\\", "/").replace(
            ":", "|"
        )

        if subtitle_file_name:
            show_subtitles = True
            subtitle_file_path = os.path.realpath(subtitle_file_name)
            if subtitle_offset != 0:
                subs = pysrt.open(subtitle_file_path)
                subs.shift(seconds=float(subtitle_offset))
                subtitle_file_path = f"{subtitle_file_path}.shifted"
                subs.save(subtitle_file_path, encoding="utf-8-sig")
            subtitle_file_path = "file:///" + subtitle_file_path.replace(
                "\\", "/"
            ).replace(":", "|")
        else:
            show_subtitles = False
            subtitle_file_path = None

        video_resolution_width, video_resolution_height = tuple(  # @UnusedVariable
            map(int, video_resolution.split("x"))
        )
        display_resolution_width, display_resolution_height = tuple(  # @UnusedVariable
            map(int, display_resolution.split("x"))
        )

        self.player = Gst.ElementFactory.make("playbin", "Playbin")

        self.player.set_property("uri", video_file_path)
        self.player.set_property("current-audio", -1)  # -1 is the first audio stream
        # self.player.set_property('current-audio', 2) # -1 is the first audio stream

        self.pageflipglsink = Gst.ElementFactory.make(
            "gstpageflipglsink", "PageflipGLSink"
        )
        if self.pageflipglsink is None:
            print("Unable to find/initialize GStreamer plugin GSTPageflipGLSink.")
            return
        if self.emitter_serial is not None:
            self.emitter_serial.pageflipglsink = self.pageflipglsink

        """
      soft-colorbalance+deinterlace+soft-volume+text+audio+video 
      
      0x00000400 | 0x00000200 | 0x00000010 | 0x00000004 | 0x00000002 | 0x00000001
      
      https://gstreamer.freedesktop.org/documentation/playback/playsink.html?gi-language=python#GstPlayFlags
      video (0x00000001) – Render the video stream
      audio (0x00000002) – Render the audio stream
      text (0x00000004) – Render subtitles
      vis (0x00000008) – Render visualisation when no video is present
      soft-volume (0x00000010) – Use software volume
      native-audio (0x00000020) – Only use native audio formats
      native-video (0x00000040) – Only use native video formats
      download (0x00000080) – Attempt progressive download buffering
      buffering (0x00000100) – Buffer demuxed/parsed data
      deinterlace (0x00000200) – Deinterlace video if necessary
      soft-colorbalance (0x00000400) – Use software color balance
      force-filters (0x00000800) – Force audio/video filter(s) to be applied
      force-sw-decoders (0x00001000) – Force only software-based decoders (no effect for playbin3) 
    """
        play_flags = 0x00000400 | 0x00000200 | 0x00000010 | 0x00000002 | 0x00000001

        video_filters = None
        previous_video_filter = None  # @UnusedVariable
        sink_pad = None
        src_pad = None

        if show_subtitles and subtitle_file_path:
            play_flags |= 0x00000004  # add subtitles
            """
      if video_filters is None:
        video_filters = Gst.Bin("video_filters")
        
      subtitle_filesrc = Gst.ElementFactory.make('filesrc', 'FileSrc')
      subtitle_filesrc.set_property('location', subtitle_file_path)
      video_filters.add(subtitle_filesrc)
      
      subtitle_subparse = Gst.ElementFactory.make('subparse', 'SubParse')
      video_filters.add(subtitle_subparse)
      subtitle_filesrc.link(subtitle_subparse)
      
      if frame_packing == 'side-by-side-half':
        frame_packing = 'side-by-side-full'
          
        videoscale = Gst.ElementFactory.make('videoscale', 'VideoScale')
        sink_pad = videoscale.sinkpad
        videoscale.set_property('method', 0)
        videoscale.set_property('add-borders', False)
        video_filters.add(videoscale)

        previous_video_filter = videoscale_capsfilter = Gst.ElementFactory.make('capsfilter', 'VideoScaleCapsFilter')
        src_pad = videoscale_capsfilter.srcpad
        videoscale_capsfilter.set_property('caps', Gst.caps_from_string(f'video/x-raw,width={2*video_resolution_width},height={video_resolution_height},pixel-aspect-ratio=1/1'))
        video_filters.add(videoscale_capsfilter)
        videoscale.link(videoscale_capsfilter)
      
      subtitle_textoverlay = Gst.ElementFactory.make('subtitleoverlay', 'SubtitleOverlay')
      if previous_video_filter is None:
        sink_pad = subtitle_textoverlay.sinkpads[0]
      src_pad = subtitle_textoverlay.srcpads[0]
      subtitle_textoverlay.set_property('font-desc', f'{subtitle_font}, {subtitle_size}') # subtitle font we need a mono spacing font for the subtitle reformatter to work because it duplicates text and inserts whitespace to force the correct depth position
      subtitle_textoverlay.set_property('subtitle-ts-offset', float(subtitle_offset)) # The synchronisation offset between text and video in nanoseconds
      video_filters.add(subtitle_textoverlay)
      if previous_video_filter is not None:
        previous_video_filter.link(subtitle_textoverlay)
      subtitle_subparse.link(subtitle_textoverlay)
      """

            self.subtitle3dsink = Gst.ElementFactory.make(
                "gstsubtitle3dsink", "Subtitle3DSink"
            )
            # self.subtitle3dsink = Gst.ElementFactory.make('fakesink', 'Subtitle3DSink')
            # self.subtitle3dsink.set_property('dump', 1)
            # self.subtitle3dsink.set_property('silent', 1)

            # self.player.set_property('subtitle-encoding', None) # subtitle encoding defaults to utf8
            # self.player.set_property('subtitle-font-desc', None) # subtitle font
            # self.player.set_property('subtitle-font-desc', 'Sans, 12') # subtitle font
            self.player.set_property(
                "subtitle-font-desc", f"{subtitle_font}, {subtitle_size}"
            )  # subtitle font we need a mono spacing font for the subtitle reformatter to work because it duplicates text and inserts whitespace to force the correct depth position

            self.player.set_property("suburi", subtitle_file_path)  # subtitle file
            # self.player.set_property('text-offset', float(subtitle_offset)) # time offset for subtitles
            self.player.set_property(
                "text-sink", self.subtitle3dsink
            )  # https://gstreamer.freedesktop.org/documentation/playback/playbin.html?gi-language=python

        if video_filters is not None:
            ghostpad_sink = Gst.GhostPad.new("sink", sink_pad)
            ghostpad_source = Gst.GhostPad.new("src", src_pad)
            video_filters.add_pad(ghostpad_sink)
            video_filters.add_pad(ghostpad_source)
            self.player.set_property("video-filter", video_filters)

        self.pageflipglsink.set_property("use-separate-process", use_separate_process)
        self.pageflipglsink.set_property("calibration-mode", calibration_mode)
        self.pageflipglsink.set_property("fullscreen", False)
        self.pageflipglsink.set_property("frame-packing", frame_packing)
        self.pageflipglsink.set_property("right-eye", right_eye)
        self.pageflipglsink.set_property("target-framerate", target_framerate)
        self.pageflipglsink.set_property("display-resolution", display_resolution)
        self.pageflipglsink.set_property("display-size", display_size)
        self.pageflipglsink.set_property("whitebox-brightness", whitebox_brightness)
        self.pageflipglsink.set_property("subtitle-font", subtitle_font)
        self.pageflipglsink.set_property("subtitle-size", subtitle_size)
        self.pageflipglsink.set_property("subtitle-depth", subtitle_depth)
        self.pageflipglsink.set_property(
            "subtitle-vertical-offset", subtitle_vertical_offset
        )
        self.pageflipglsink.set_property("start", True)  # this must be done last
        self.player.set_property("video-sink", self.pageflipglsink)

        self.player.set_property("flags", play_flags)  # no subtitles 0x00000004

        # self.player.set_property('force-aspect-ratio', True)

        self.player.set_state(Gst.State.PLAYING)
        self.video_open = True

    def click_stop_video_button(self, event=None):  # @UnusedVariable
        self.stop_player()


if __name__ == "__main__":

    if os.name == "nt":
        os.system("chcp.com 65001")

    # set base path
    base_path = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists("_internal"):
        base_path = os.path.join(base_path, "_internal")

    os.environ["GST_PLUGIN_PATH"] = base_path

    import gi

    gi.require_version("Gst", "1.0")
    gi.require_version("GstVideo", "1.0")
    # gi.require_version('GdkX11', '3.0') # windows
    # from gi.repository import Gst, GObject, GdkX11, GstVideo, GstBase # windows
    # from gi.repository import Gst, GObject, GstVideo, GstBase  # windows
    from gi.repository import Gst  # windows

    # GObject.threads_init()
    Gst.init(None)

    top_window = TopWindow()

    try:

        # window.mainloop()
        while not top_window.close:
            if top_window.player is not None and top_window.video_open:
                pageflipglsink_requests = top_window.pageflipglsink.get_property(
                    "requests"
                )
                if pageflipglsink_requests:
                    ignore_duplicate_actions = (
                        set()
                    )  # we always seem to get two or more signals for one keyboard press
                    top_window.pageflipglsink.set_property("requests", "")
                    for r in pageflipglsink_requests.split(","):
                        if (
                            "toggle_paused" in r
                            and "toggle_paused" not in ignore_duplicate_actions
                        ):
                            ignore_duplicate_actions.add("toggle_paused")
                            top_window.toggle_paused()
                        if "seek" in r:
                            top_window.perform_seek(r)
                        if "close" in r and "close" not in ignore_duplicate_actions:
                            ignore_duplicate_actions.add("close")
                            top_window.stop_player()
                        if (
                            "set_menu_on_top" in r
                            and "set_menu_on_top" not in ignore_duplicate_actions
                        ):
                            ignore_duplicate_actions.add("set_menu_on_top")
                            top_window.set_menu_on_top(
                                True if r == "set_menu_on_top_true" else False
                            )
                        if (
                            r.startswith("calibration_")
                            and top_window.pageflipglsink.get_property(
                                "calibration-mode"
                            )
                            and top_window.emitter_serial is not None
                        ):
                            increment_by = 0
                            if "decrease_" in r:
                                increment_by = -5
                            elif "increase_" in r:
                                increment_by = 5
                            target = None
                            if "frame_delay" in r:
                                target = (
                                    top_window.emitter_settings_dialog.setting_ir_frame_delay_variable
                                )
                            elif "frame_duration" in r:
                                target = (
                                    top_window.emitter_settings_dialog.setting_ir_frame_duration_variable
                                )
                            if increment_by != 0 and target is not None:
                                target.set(str(int(target.get()) + increment_by))
                                top_window.emitter_settings_dialog.click_update_settings_on_emitter()

                if top_window.subtitle3dsink is not None:
                    latest_subtitle_data = top_window.subtitle3dsink.get_property(
                        "latest-subtitle-data"
                    )
                    if latest_subtitle_data:
                        top_window.subtitle3dsink.set_property(
                            "latest-subtitle-data", ""
                        )
                        top_window.pageflipglsink.set_property(
                            "latest-subtitle-data", latest_subtitle_data
                        )

            try:
                top_window.window.update_idletasks()
                top_window.window.update()
                time.sleep(0.001)
            except:
                # traceback.print_exc()
                top_window.close_player()

    finally:
        pass
