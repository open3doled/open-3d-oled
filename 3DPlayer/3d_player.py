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
import serial.tools.list_ports
import threading
import queue
import json
import datetime

from PIL import ImageTk
from io import BytesIO
import cairosvg
import PIL.Image
import avrloader
import argparse
import pathlib
import textwrap
import re


# Default IR Settings
DEFAULT_IR_PROTOCOL = "6"
DEFAULT_GLASSES_MODE = "0"
DEFAULT_IR_FRAME_DELAY = "500"
DEFAULT_IR_FRAME_DURATION = "7000"
DEFAULT_IR_SIGNAL_SPACING = "30"
DEFAULT_OPT101_BLOCK_SIGNAL_DETECTION_DELAY = "7500"
DEFAULT_OPT101_BLOCK_N_SUBSEQUENT_DUPLICATES = "0"
DEFAULT_OPT101_IGNORE_ALL_DUPLICATES = "0"
DEFAULT_OPT101_MIN_THRESHOLD_VALUE_TO_ACTIVATE = "10"
DEFAULT_OPT101_DETECTION_THRESHOLD = "128"
DEFAULT_OPT101_ENABLE_IGNORE_DURING_IR = "0"
DEFAULT_OPT101_ENABLE_DUPLICATE_REALTIME_REPORTING = "0"
DEFAULT_OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION = "0"
DEFAULT_OPT101_DETECTION_THRESHOLD_REPEATED_HIGH = "224"
DEFAULT_OPT101_DETECTION_THRESHOLD_REPEATED_LOW = "32"
DEFAULT_OPT101_OUTPUT_STATS = "0"
DEFAULT_OPT101_SENSOR_FILTER_MODE = "0"

# Display Setting Defaults
DEFAULT_TARGET_FRAMERATE = "0"
DEFAULT_DISPLAY_RESOLUTION = "1920x1080"
DEFAULT_DISPLAY_ZOOM_FACTOR = "100"
DEFAULT_DISPLAY_SIZE = "55"
DEFAULT_WHITEBOX_BRIGHTNESS = "255"
DEFAULT_WHITEBOX_CORNER_POSITION = "top_left"
DEFAULT_WHITEBOX_VERTICAL_POSITION = "0"
DEFAULT_WHITEBOX_HORIZONTAL_POSITION = "0"
DEFAULT_WHITEBOX_SIZE = "13"
DEFAULT_WHITEBOX_HORIZONTAL_SPACING = "23"
DEFAULT_CALIBRATION_MODE = False

# Video Defaults
DEFAULT_SUBTITLE_FONT = "MS Gothic" if os.name == "nt" else "Noto Sans CJK JP"
DEFAULT_SUBTITLE_SIZE = "60"
DEFAULT_SUBTITLE_DEPTH = "20"
DEFAULT_SUBTITLE_VERTICAL_OFFSET = "150"
DEFAULT_SUBTITLE_OFFSET = "0"
DEFAULT_FRAME_PACKING = "side-by-side-half"
DEFAULT_RIGHT_EYE = "right"


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


def create_toggled_frame(parent, text, expanded=False):
    top_frame = tkinter.Frame(parent, relief="raised", borderwidth=1)
    top_frame.pack(fill="x", expand=1, pady=2, padx=2, anchor="n")
    title_frame = tkinter.Frame(top_frame)
    title_frame.pack(fill="x", expand=1)
    tkinter.Label(title_frame, text=text).pack(side="left", fill="x", expand=1)

    def toggle():
        if expanded_.get() == 1:
            expanded_.set(0)
            sub_frame.forget()
            toggle_button.configure(text="+")
        else:
            expanded_.set(1)
            sub_frame.pack(padx=3, pady=3, fill="x", expand=1)
            toggle_button.configure(text="-")

    toggle_button = tkinter.Button(title_frame, width=2, text="+", command=toggle)
    toggle_button.pack(side="left")
    sub_frame = tkinter.Frame(top_frame, relief="sunken", borderwidth=1)
    expanded_ = tkinter.IntVar(master=parent)
    if expanded:
        expanded_.set(1)
        sub_frame.pack(padx=3, pady=3, fill="x", expand=1)
        toggle_button.configure(text="-")
    else:
        expanded_.set(0)
    return sub_frame


# from https://stackoverflow.com/questions/67449774/how-to-display-svg-on-tkinter
def svg_to_imagetk_photoimage(image):
    png_data = cairosvg.svg2png(
        url=os.path.join(internal_base_path, image), output_width=30, output_height=30
    )
    bytes_png = BytesIO(png_data)
    img = PIL.Image.open(bytes_png)
    return ImageTk.PhotoImage(img)


class EmitterSerialLineReader(serial.threaded.LineReader):

    TERMINATOR = b"\r\n"
    ENCODING = "iso-8859-1"

    def __init__(self):
        super(EmitterSerialLineReader, self).__init__()
        self.alive = True
        self.total_left_frames = 0
        self.total_right_frames = 0
        self.realtime_duplicate_counter = 0
        self.total_duplicate_frames = 0
        self.total_premature_frames = 0
        self.debug_stream_file = None
        self.debug_opt101_enable_stream_readings_to_serial = 0
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
        if event.startswith("+d"):
            self.realtime_duplicate_counter += 1
            if self.__pageflipglsink is not None:
                # self.__pageflipglsink.set_property("skip-n-page-flips", "1")
                if self.__pageflipglsink.get_property("calibration-mode"):
                    print(self.__pageflipglsink.get_property("calibration-mode"))
                    self.__pageflipglsink.set_property(
                        "latest-subtitle-data",
                        json.dumps(
                            {
                                "show_now": True,
                                "text": f"duplicate frames {self.realtime_duplicate_counter}",
                                "duration": 500000000,
                            }
                        ),
                    )
        elif (
            event.startswith("+o ")
            and self.debug_opt101_enable_stream_readings_to_serial == 1
        ):
            # self.debug_stream.file.write(f"{event.split(" ")[1]}\n")
            raw_bytes = event.split(" ")[1].encode("iso-8859-1")
            opt101_current_time = (
                (raw_bytes[9] & 0x7F)
                | ((raw_bytes[8] & 0x7F) << 7)
                | ((raw_bytes[7] & 0x7F) << 14)
                | ((raw_bytes[6] & 0x7F) << 21)
                | ((raw_bytes[5] & 0x0F) << 28)
            )
            left_sensor = ((raw_bytes[5] & 0x70) >> 4) | ((raw_bytes[4] & 0x1F) << 3)
            right_sensor = ((raw_bytes[4] & 0x60) >> 5) | ((raw_bytes[3] & 0x3F) << 2)
            duplicate_frames_in_a_row_counter = raw_bytes[2] & 0x7F

            opt101_duplicate_frame_left = 1 if (raw_bytes[0] & 0x20) else 0
            opt101_ignore_duplicate_left = 1 if (raw_bytes[0] & 0x10) else 0
            opt101_reading_above_threshold_left = 1 if (raw_bytes[0] & 0x08) else 0
            opt101_duplicate_frame_right = 1 if (raw_bytes[0] & 0x04) else 0
            opt101_ignore_duplicate_right = 1 if (raw_bytes[0] & 0x02) else 0
            opt101_reading_above_threshold_right = 1 if (raw_bytes[0] & 0x01) else 0
            opt101_readings_active = 1 if (raw_bytes[1] & 0x08) else 0
            opt101_detected_signal_start_eye = 1 if (raw_bytes[1] & 0x04) else 0
            opt101_initiated_sending_ir_signal = 1 if (raw_bytes[1] & 0x02) else 0
            opt101_block_signal_detection_until = 1 if (raw_bytes[1] & 0x01) else 0

            left_sent_ir = 0
            right_sent_ir = 0
            if opt101_initiated_sending_ir_signal:
                if opt101_detected_signal_start_eye:
                    left_sent_ir = 1
                else:
                    right_sent_ir = 1
            left_duplicate_detected = 0
            left_duplicate_ignored = 0
            if opt101_reading_above_threshold_left:
                left_duplicate_detected = opt101_duplicate_frame_left
                if left_duplicate_detected:
                    left_duplicate_ignored = opt101_ignore_duplicate_left
            right_duplicate_detected = 0
            right_duplicate_ignored = 0
            if opt101_reading_above_threshold_right:
                right_duplicate_detected = opt101_duplicate_frame_right
                if right_duplicate_detected:
                    right_duplicate_ignored = opt101_ignore_duplicate_right
            self.debug_stream_file.write(
                f"{opt101_current_time},{left_sensor},{right_sensor},{duplicate_frames_in_a_row_counter},"
                f"{opt101_block_signal_detection_until},{opt101_readings_active},"
                f"{opt101_reading_above_threshold_left},{left_duplicate_detected},{left_duplicate_ignored},{left_sent_ir},"
                f"{opt101_reading_above_threshold_right},{right_duplicate_detected},{right_duplicate_ignored},{right_sent_ir}\n"
            )
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


class EmitterFirmwareUpdateDialog:
    def __init__(self, parent, main_app):
        self.main_app = main_app
        top = self.top = tkinter.Toplevel(parent)
        top.protocol("WM_DELETE_WINDOW", self.click_close)

        row_count = 0
        ports = serial.tools.list_ports.comports()
        print(f"Available serial ports {[(a,b,c) for a,b,c in ports]}")
        pro_micro_ports = [
            port
            for port, desc, hwid in ports
            if "1B4F:9206" in hwid
            or desc == "SparkFun Pro Micro"
            or desc.startswith("USB Serial Device")
        ]

        self.warning_frame = tkinter.Frame(top)
        self.warning_label = tkinter.Label(
            self.warning_frame,
            text="Make sure you do not disconnect the unit while updating the firmware or you may need to recover \nthe firmware and bootloader via ISP protocol.",
            justify=tkinter.LEFT,
        )
        self.warning_label.pack(padx=5, side=tkinter.LEFT)
        self.warning_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.serial_port_identifier_frame = tkinter.Frame(top)
        self.serial_port_identifier_variable = tkinter.StringVar(top)
        self.serial_port_identifier_variable.set(
            pro_micro_ports[0] if pro_micro_ports else "/dev/ttyACM0"
        )
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
            "Used as the serial port when updating the emitter firmware. (On linux use /dev/ttyACM[0-9], on Windows use COM[0-9])",
            hover_delay=100,
        )
        self.serial_port_identifier_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.firmware_file_frame = tkinter.Frame(top)
        self.firmware_file_name = ""
        self.firmware_file_label = tkinter.Label(
            self.firmware_file_frame, text="Firmware File: "
        )
        self.firmware_file_label.pack(padx=5, side=tkinter.LEFT)
        self.firmware_file_location_label = tkinter.Label(
            self.firmware_file_frame, text=""
        )
        self.firmware_file_location_label.pack(padx=5, side=tkinter.LEFT)
        self.firmware_file_select_button = tkinter.Button(
            self.firmware_file_frame, text="Select", command=self.select_firmware_file
        )
        self.firmware_file_select_button.pack(padx=5, side=tkinter.LEFT)
        # self.firmware_file_frame.pack()
        self.firmware_file_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.status_frame = tkinter.Frame(top)
        self.status_label = tkinter.Label(
            self.status_frame,
            text="",
            justify=tkinter.LEFT,
        )
        self.status_label.pack(padx=5, side=tkinter.LEFT)
        self.status_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.action_button_frame = tkinter.Frame(top)
        self.update_firmware_button = tkinter.Button(
            self.action_button_frame,
            text="Update Firmware",
            command=self.click_update_firmware,
        )
        self.update_firmware_button.pack(padx=5, side=tkinter.LEFT)
        self.update_firmware_button_tooltip = idlelib.tooltip.Hovertip(
            self.update_firmware_button,
            "Updates the emitter firmware.",
            hover_delay=100,
        )
        self.close_button = tkinter.Button(
            self.action_button_frame, text="Close", command=self.click_close
        )
        self.close_button.pack(padx=5, side=tkinter.LEFT)
        self.close_button_tooltip = idlelib.tooltip.Hovertip(
            self.close_button,
            "Closes this window.",
            hover_delay=100,
        )
        self.action_button_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

    def select_firmware_file(self):
        new_firmware_file_name = tkinter.filedialog.askopenfilename(
            title="Select Firmware File from Disk",
            initialdir=self.main_app.select_firmware_file_initialdir,
            filetypes=[("HEX Firmware File", "*.hex")],
        )
        if new_firmware_file_name:
            self.main_app.select_firmware_file_initialdir = os.path.dirname(
                os.path.abspath(new_firmware_file_name)
            )
            self.firmware_file_name = new_firmware_file_name
            self.firmware_file_location_label.config(text=self.firmware_file_name)

    def click_update_firmware(self):
        if os.path.exists(self.firmware_file_name):
            self.update_firmware_button.config(state="disabled")
            self.close_button.config(state="disabled")

            port = serial.Serial(
                port=self.serial_port_identifier_entry.get(), baudrate=1200
            )
            port.close()

            while range(10):
                time.sleep(0.5)

                ports = serial.tools.list_ports.comports()
                print(
                    f"Available serial ports for firmware update {[(a,b,c) for a,b,c in ports]}"
                )
                pro_micro_ports = [
                    port
                    for port, desc, hwid in ports
                    if "2341:0036" in hwid
                    or desc == "Arduino Leonardo"
                    or desc.startswith("USB Serial Device")
                ]
                if len(pro_micro_ports) > 0:
                    break
            time.sleep(
                1
            )  # windows needs afew seconds to figure out the driver situation even after the device is detected...
            if len(pro_micro_ports) == 0:
                self.status_label.config(
                    text=f"Failed to update emitter firmware, unable to enter bootloader."
                )
                top_window.window.update_idletasks()
                self.update_firmware_button.config(state="normal")
                self.close_button.config(state="normal")
                return

            self.serial_port_identifier_variable.set(pro_micro_ports[0])

            self.status_label.config(
                text=f"Updating emitter with firmware file {self.firmware_file_name}..."
            )
            top_window.window.update_idletasks()

            j = avrloader.JobInfo()
            j.com_port_name = self.serial_port_identifier_entry.get()
            j.device_name = "ATmega32U4"
            j.input_file_flash = self.firmware_file_name
            j.flash_start_address = 0x0000
            j.flash_end_address = 0x6FFF
            j.memory_fill_pattern = 0x00
            j.read_signature = True
            j.program_flash = True
            j.verify_flash = True
            j.do_job()

            self.status_label.config(
                text=f"Completed updating emitter firmware, waiting for emitter restart."
            )
            top_window.window.update_idletasks()
            time.sleep(1)

            ports = serial.tools.list_ports.comports()
            print(
                f"Available serial ports after firmware update {[(a,b,c) for a,b,c in ports]}"
            )
            pro_micro_ports = [
                port
                for port, desc, hwid in ports
                if "1B4F:9206" in hwid
                or desc == "SparkFun Pro Micro"
                or desc.startswith("USB Serial Device")
            ]
            self.serial_port_identifier_variable.set(
                pro_micro_ports[0] if pro_micro_ports else "/dev/ttyACM0"
            )

            self.status_label.config(text=f"Completed updating emitter firmware.")
            self.update_firmware_button.config(state="normal")
            self.close_button.config(state="normal")

    def click_close(self):
        self.top.destroy()
        self.top = None


class EmitterSettingsDialog:
    def __init__(self, parent, main_app, close_callback):
        self.main_app = main_app
        self.close_callback = close_callback
        top = self.top = tkinter.Toplevel(parent)
        top.title("Emitter Settings")
        top.protocol("WM_DELETE_WINDOW", self.click_close)

        self.emitter_firmware_update_dialog = None

        row_count = 0
        pro_micro_ports = [
            port
            for port, desc, hwid in serial.tools.list_ports.comports()
            if "1B4F:9206" in hwid
            or desc == "SparkFun Pro Micro"
            or desc.startswith("USB Serial Device")
        ]

        self.serial_port_identifier_frame = tkinter.Frame(top)
        self.serial_port_identifier_variable = tkinter.StringVar(top)
        self.serial_port_identifier_variable.set(
            pro_micro_ports[0] if pro_micro_ports else "/dev/ttyACM0"
        )
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
        self.serial_port_disconnect_button.config(state="disabled")
        self.serial_port_disconnect_button.pack(padx=5, side=tkinter.LEFT)
        self.serial_port_disconnect_button_tooltip = idlelib.tooltip.Hovertip(
            self.serial_port_disconnect_button,
            "Disconnect from the emitter.",
            hover_delay=100,
        )
        self.update_emitter_firmware_button = tkinter.Button(
            self.serial_port_identifier_frame,
            text="Update Emitter Firmware",
            command=self.click_update_emitter_firmware,
        )
        self.update_emitter_firmware_button.pack(padx=5, side=tkinter.LEFT)
        self.update_emitter_firmware_button_tooltip = idlelib.tooltip.Hovertip(
            self.update_emitter_firmware_button,
            "Open the dialog to update the emitter firmware.",
            hover_delay=100,
        )
        self.serial_port_identifier_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.setting_emitter_firmware_version_frame = tkinter.Frame(top)
        self.setting_emitter_firmware_version_variable = tkinter.StringVar(top)
        self.setting_emitter_firmware_version_variable.set("Not Connected")
        self.setting_emitter_firmware_version_label = tkinter.Label(
            self.setting_emitter_firmware_version_frame,
            text="Emitter Firmware Version: ",
        )
        self.setting_emitter_firmware_version_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_emitter_firmware_version_entry = tkinter.Entry(
            self.setting_emitter_firmware_version_frame,
            textvariable=self.setting_emitter_firmware_version_variable,
        )
        self.setting_emitter_firmware_version_entry.config(state="disabled")
        self.setting_emitter_firmware_version_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_emitter_firmware_version_tooltip = idlelib.tooltip.Hovertip(
            self.setting_emitter_firmware_version_entry,
            "The version of your ir emitter firmware",
            hover_delay=100,
        )
        self.setting_emitter_firmware_version_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_ir_protocol_frame = tkinter.Frame(top)
        self.setting_ir_protocol_variable = tkinter.StringVar(top)
        self.setting_ir_protocol_variable.set(DEFAULT_IR_PROTOCOL)
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
        self.setting_glasses_mode_variable.set(DEFAULT_GLASSES_MODE)
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
        self.setting_glasses_mode_button.config(state="disabled")
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
        self.setting_ir_frame_delay_variable.set(DEFAULT_IR_FRAME_DELAY)
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
        self.setting_ir_frame_duration_variable.set(DEFAULT_IR_FRAME_DURATION)
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
        self.setting_ir_signal_spacing_variable.set(DEFAULT_IR_SIGNAL_SPACING)
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
        self.setting_opt101_block_signal_detection_delay_variable.set(
            DEFAULT_OPT101_BLOCK_SIGNAL_DETECTION_DELAY
        )
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
            "(in microseconds) how long to wait after a high tv signal on left or right before allowing another high tv signal \non either channel this is useful to eliminating false triggers when the tv signal is decreasing in a noisy fashion. \nthis is best set to slighly lower than the target refresh rate (about 80-90%). \n(when used in conjunction with a PWM backlit display this should be set to a value 80-90% of the PWM backlight cycle time.)",
            hover_delay=100,
        )
        self.setting_opt101_block_signal_detection_delay_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt101_block_n_subsequent_duplicates_frame = tkinter.Frame(top)
        self.setting_opt101_block_n_subsequent_duplicates_variable = tkinter.StringVar(
            top
        )
        self.setting_opt101_block_n_subsequent_duplicates_variable.set(
            DEFAULT_OPT101_BLOCK_N_SUBSEQUENT_DUPLICATES
        )
        self.setting_opt101_block_n_subsequent_duplicates_label = tkinter.Label(
            self.setting_opt101_block_n_subsequent_duplicates_frame,
            text="OPT101 Block N Subsequent Duplicates: ",
        )
        self.setting_opt101_block_n_subsequent_duplicates_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_block_n_subsequent_duplicates_entry = tkinter.Entry(
            self.setting_opt101_block_n_subsequent_duplicates_frame,
            textvariable=self.setting_opt101_block_n_subsequent_duplicates_variable,
        )
        self.setting_opt101_block_n_subsequent_duplicates_entry.config(
            state="disabled"
        )  # we only enable it after we confirm the emitter firmware supports this parameter
        self.setting_opt101_block_n_subsequent_duplicates_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_block_n_subsequent_duplicates_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_block_n_subsequent_duplicates_entry,
            "(number of detections to block) on displays that use a PWM backlight one needs to block fake duplicate frames \nfor at least the first math.ceiling((PWM frequency)/framerate) otherwise a PWM pulse may incorrectly \nbe detected as the next duplicate frame causing the unit to lose proper synchronization. \nWhen using this setting one should set 'OPT101 Block Signal Detection Delay' to a \nvalue 80-90% of the PWM backlight cycle time. \nThis feature is only availble from emitter firmware version 10 \n(default 0).",
            hover_delay=100,
        )
        self.setting_opt101_block_n_subsequent_duplicates_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt101_ignore_all_duplicates_frame = tkinter.Frame(top)
        self.setting_opt101_ignore_all_duplicates_variable = tkinter.StringVar(top)
        self.setting_opt101_ignore_all_duplicates_variable.set(
            DEFAULT_OPT101_IGNORE_ALL_DUPLICATES
        )
        self.setting_opt101_ignore_all_duplicates_label = tkinter.Label(
            self.setting_opt101_ignore_all_duplicates_frame,
            text="OPT101 Ignore All Duplicates: ",
        )
        self.setting_opt101_ignore_all_duplicates_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt101_ignore_all_duplicates_entry = tkinter.Entry(
            self.setting_opt101_ignore_all_duplicates_frame,
            textvariable=self.setting_opt101_ignore_all_duplicates_variable,
        )
        self.setting_opt101_ignore_all_duplicates_entry.config(
            state="disabled"
        )  # we only enable it after we confirm the emitter firmware supports this parameter
        self.setting_opt101_ignore_all_duplicates_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt101_ignore_all_duplicates_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_ignore_all_duplicates_entry,
            "(0=Disable, 1=Enable) On displays with too much jitter where setting OPT101 Block Signal Detection Delay and/or \nOPT101 Block N Subsequent Duplicates does not eliminate false dulicate detection due to strange PWM characteristics \nor variable brightness periods, it may be best to ignore any detected duplicates. This will mean that glasses only \nattempt resynchronization when the alternate eye trigger is sent by the display.",
            hover_delay=100,
        )
        self.setting_opt101_ignore_all_duplicates_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt101_min_threshold_value_to_activate_frame = tkinter.Frame(top)
        self.setting_opt101_min_threshold_value_to_activate_variable = (
            tkinter.StringVar(top)
        )
        self.setting_opt101_min_threshold_value_to_activate_variable.set(
            DEFAULT_OPT101_MIN_THRESHOLD_VALUE_TO_ACTIVATE
        )
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
        self.setting_opt101_detection_threshold_variable.set(
            DEFAULT_OPT101_DETECTION_THRESHOLD
        )
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

        self.experimental_and_debug_grid_frame = tkinter.Frame(top)
        self.experimental_and_debug_frame = create_toggled_frame(
            self.experimental_and_debug_grid_frame, "Experimental and Debug"
        )
        self.experimental_and_debug_grid_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        debug_row_count = 0
        self.setting_opt101_enable_ignore_during_ir_frame = tkinter.Frame(
            self.experimental_and_debug_frame
        )
        self.setting_opt101_enable_ignore_during_ir_variable = tkinter.StringVar(top)
        self.setting_opt101_enable_ignore_during_ir_variable.set(
            DEFAULT_OPT101_ENABLE_IGNORE_DURING_IR
        )
        self.setting_opt101_enable_ignore_during_ir_label = tkinter.Label(
            self.setting_opt101_enable_ignore_during_ir_frame,
            text="Enable Ignore Frame Start During IR*: ",
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
            "(experimental) disable the opt101 sensor detection during the time when ir signals are being emitted. \nthis stops reflections of IR signals OR voltage ripples on vcc from incorrectly triggering frame start signals.",
            hover_delay=100,
        )
        self.setting_opt101_enable_ignore_during_ir_frame.grid(
            row=debug_row_count, column=0, sticky="w"
        )
        debug_row_count += 1

        self.setting_opt101_enable_duplicate_realtime_reporting_frame = tkinter.Frame(
            self.experimental_and_debug_frame
        )
        self.setting_opt101_enable_duplicate_realtime_reporting_variable = (
            tkinter.StringVar(top)
        )
        self.setting_opt101_enable_duplicate_realtime_reporting_variable.set(
            DEFAULT_OPT101_ENABLE_DUPLICATE_REALTIME_REPORTING
        )
        self.setting_opt101_enable_duplicate_realtime_reporting_label = tkinter.Label(
            self.setting_opt101_enable_duplicate_realtime_reporting_frame,
            text="Enable Duplicate Realtime Reporting: ",
        )
        self.setting_opt101_enable_duplicate_realtime_reporting_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_enable_duplicate_realtime_reporting_entry = tkinter.Entry(
            self.setting_opt101_enable_duplicate_realtime_reporting_frame,
            textvariable=self.setting_opt101_enable_duplicate_realtime_reporting_variable,
        )
        self.setting_opt101_enable_duplicate_realtime_reporting_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_enable_duplicate_realtime_reporting_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_enable_duplicate_realtime_reporting_entry,
            "When enabled (set to 1) the emitter will send a signal to the PC every time it detects a duplicate frame. This can be useful during calibration to see if the emitter thinks the pc is sending duplicate frames.",
            hover_delay=100,
        )
        self.setting_opt101_enable_duplicate_realtime_reporting_frame.grid(
            row=debug_row_count, column=0, sticky="w"
        )
        debug_row_count += 1

        self.setting_opt101_output_stats_frame = tkinter.Frame(
            self.experimental_and_debug_frame
        )
        self.setting_opt101_output_stats_variable = tkinter.StringVar(top)
        self.setting_opt101_output_stats_variable.set(DEFAULT_OPT101_OUTPUT_STATS)
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
            '(0=Disable, 1=Enable) output statistics (if built with OPT101_ENABLE_STATS) relating to how the opt101 module is processing all lines start with \n"+stats " followed by specific statistics. Turn this off when not experimenting as it may degrade timing accuracy when serial communication occurs',
            hover_delay=100,
        )
        self.setting_opt101_output_stats_frame.grid(
            row=debug_row_count, column=0, sticky="w"
        )
        debug_row_count += 1

        self.setting_opt101_sensor_filter_mode_frame = tkinter.Frame(
            self.experimental_and_debug_frame
        )
        self.setting_opt101_sensor_filter_mode_variable = tkinter.StringVar(top)
        self.setting_opt101_sensor_filter_mode_variable.set(
            DEFAULT_OPT101_SENSOR_FILTER_MODE
        )
        self.setting_opt101_sensor_filter_mode_label = tkinter.Label(
            self.setting_opt101_sensor_filter_mode_frame,
            text="OPT101 Sensor Filter Mode: ",
        )
        self.setting_opt101_sensor_filter_mode_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt101_sensor_filter_mode_entry = tkinter.Entry(
            self.setting_opt101_sensor_filter_mode_frame,
            textvariable=self.setting_opt101_sensor_filter_mode_variable,
        )
        self.setting_opt101_sensor_filter_mode_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt101_sensor_filter_mode_entry.config(state="disabled")
        self.setting_opt101_sensor_filter_mode_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_sensor_filter_mode_entry,
            "(0=Disable (default), 1=Mode 1) (Mode 1: check that the last three readings are trending in the same direction) \n(this may be useful in helping to eliminate the effect of noise caused by IR leds or low signal to noise from the optical sensor.) \n(Only available from firmware version 13 onwards)",
            hover_delay=100,
        )
        self.setting_opt101_sensor_filter_mode_frame.grid(
            row=debug_row_count, column=0, sticky="w"
        )
        debug_row_count += 1

        self.frequency_analysis_based_duplicate_frame_detection_frame_top_frame = (
            tkinter.Frame(
                self.experimental_and_debug_frame, relief="raised", borderwidth=1
            )
        )
        self.frequency_analysis_based_duplicate_frame_detection_frame_top_frame.grid(
            row=debug_row_count, column=0, sticky="w"
        )
        debug_row_count += 1

        freq_debug_row_count = 0
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_frame = tkinter.Frame(
            self.frequency_analysis_based_duplicate_frame_detection_frame_top_frame
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable = tkinter.StringVar(
            top
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable.set(
            DEFAULT_OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_label = tkinter.Label(
            self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_frame,
            text="OPT101 Enable Frequency Analysis Based Duplicate Frame Detection*: ",
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
            "*experimental* enables the code to detect duplicate frames on screens without a black frame interval (if built with OPT101_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION).",
            hover_delay=100,
        )
        self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_frame.grid(
            row=freq_debug_row_count, column=0, sticky="w"
        )
        freq_debug_row_count += 1

        self.setting_opt101_detection_threshold_repeated_high_frame = tkinter.Frame(
            self.frequency_analysis_based_duplicate_frame_detection_frame_top_frame
        )
        self.setting_opt101_detection_threshold_repeated_high_variable = (
            tkinter.StringVar(top)
        )
        self.setting_opt101_detection_threshold_repeated_high_variable.set(
            DEFAULT_OPT101_DETECTION_THRESHOLD_REPEATED_HIGH
        )
        self.setting_opt101_detection_threshold_repeated_high_label = tkinter.Label(
            self.setting_opt101_detection_threshold_repeated_high_frame,
            text="OPT101 Detection Threshold High*: ",
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
            row=freq_debug_row_count, column=0, sticky="w"
        )
        freq_debug_row_count += 1

        self.setting_opt101_detection_threshold_repeated_low_frame = tkinter.Frame(
            self.frequency_analysis_based_duplicate_frame_detection_frame_top_frame
        )
        self.setting_opt101_detection_threshold_repeated_low_variable = (
            tkinter.StringVar(top)
        )
        self.setting_opt101_detection_threshold_repeated_low_variable.set(
            DEFAULT_OPT101_DETECTION_THRESHOLD_REPEATED_LOW
        )
        self.setting_opt101_detection_threshold_repeated_low_label = tkinter.Label(
            self.setting_opt101_detection_threshold_repeated_low_frame,
            text="OPT101 Detection Threshold Low*: ",
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
            "(as a value between 1-255) (LCD Specific) see OPT101 Detection Threshold High above*",
            hover_delay=100,
        )
        self.setting_opt101_detection_threshold_repeated_low_frame.grid(
            row=freq_debug_row_count, column=0, sticky="w"
        )
        freq_debug_row_count += 1

        self.setting_opt101_debug_frame = tkinter.Frame(
            self.experimental_and_debug_frame
        )
        self.setting_opt101_enable_stream_readings_to_serial_toggle_button = (
            tkinter.Button(
                self.setting_opt101_debug_frame,
                text="Toggle OPT101 Enable Stream Readings To Serial",
                command=self.click_opt101_enable_stream_readings_to_serial_toggle,
            )
        )
        self.setting_opt101_enable_stream_readings_to_serial_toggle_button.config(
            state="disabled"
        )
        self.setting_opt101_enable_stream_readings_to_serial_toggle_button.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt101_enable_stream_readings_to_serial_toggle_button_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt101_enable_stream_readings_to_serial_toggle_button,
            "toggles logging of opt101 sensor readings to a file for analysis and debugging (if built with OPT101_ENABLE_STREAM_READINGS_TO_SERIAL)",
            hover_delay=100,
        )
        self.setting_opt101_debug_frame.grid(row=debug_row_count, column=0, sticky="w")
        debug_row_count += 1

        self.action_button_frame_1 = tkinter.Frame(top)
        self.update_button = tkinter.Button(
            self.action_button_frame_1,
            text="Update Settings on Emitter",
            command=self.click_update_settings_on_emitter,
        )
        self.update_button.config(state="disabled")
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
        self.save_settings_button.config(state="disabled")
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

        if self.main_app.emitter_serial:
            if self.emitter_firmware_version_int >= 11:
                self.setting_opt101_enable_stream_readings_to_serial_toggle_button.config(
                    state="normal"
                )
            else:
                self.setting_opt101_enable_stream_readings_to_serial_toggle_button.config(
                    state="disabled"
                )
            self.setting_glasses_mode_button.config(state="normal")
            self.update_emitter_firmware_button.config(state="disabled")
            self.update_button.config(state="normal")
            self.serial_port_connect_button.config(state="disabled")
            self.serial_port_disconnect_button.config(state="normal")
            self.save_settings_button.config(state="normal")
        else:
            self.setting_opt101_enable_stream_readings_to_serial_toggle_button.config(
                state="disabled"
            )
            self.setting_glasses_mode_button.config(state="disabled")
            self.update_emitter_firmware_button.config(state="normal")
            self.update_button.config(state="disabled")
            self.serial_port_connect_button.config(state="normal")
            self.serial_port_disconnect_button.config(state="disabled")
            self.save_settings_button.config(state="disabled")

        self.supported_parameters = None
        self.update_settings_from_serial()

    def update_settings_from_serial(self):
        if self.main_app.emitter_serial:
            response = self.main_app.emitter_serial.line_reader.command("0")[0].split(
                " "
            )
            if response[0] == "parameters":
                parameters = response[1].split(",")
                if int(parameters[0]) < 10:
                    parameters = [3] + parameters
                (
                    emitter_firmware_version,
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
                    opt101_enable_duplicate_realtime_reporting,
                    opt101_output_stats,
                    opt101_enable_frequency_analysis_based_duplicate_frame_detection,
                ) = parameters[:14]

                self.emitter_firmware_version_int = int(emitter_firmware_version)
                self.setting_emitter_firmware_version_variable.set(
                    emitter_firmware_version
                )
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
                self.setting_opt101_enable_duplicate_realtime_reporting_variable.set(
                    opt101_enable_duplicate_realtime_reporting
                )
                self.setting_opt101_output_stats_variable.set(opt101_output_stats)
                self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable.set(
                    opt101_enable_frequency_analysis_based_duplicate_frame_detection
                )
                if self.emitter_firmware_version_int > 9:
                    self.setting_opt101_block_n_subsequent_duplicates_variable.set(
                        parameters[14]
                    )
                    self.setting_opt101_block_n_subsequent_duplicates_entry.config(
                        state="normal"
                    )
                if self.emitter_firmware_version_int >= 11:
                    self.setting_opt101_enable_stream_readings_to_serial_toggle_button.config(
                        state="normal"
                    )
                else:
                    self.setting_opt101_enable_stream_readings_to_serial_toggle_button.config(
                        state="disabled"
                    )
                if self.emitter_firmware_version_int >= 12:
                    self.setting_opt101_ignore_all_duplicates_variable.set(
                        parameters[15]
                    )
                    self.setting_opt101_ignore_all_duplicates_entry.config(
                        state="normal"
                    )
                else:
                    self.setting_opt101_ignore_all_duplicates_variable.set(
                        DEFAULT_OPT101_IGNORE_ALL_DUPLICATES
                    )
                    self.setting_opt101_ignore_all_duplicates_entry.config(
                        state="disabled"
                    )
                if self.emitter_firmware_version_int >= 13:
                    self.setting_opt101_sensor_filter_mode_variable.set(parameters[16])
                    self.setting_opt101_sensor_filter_mode_entry.config(state="normal")
                else:
                    self.setting_opt101_sensor_filter_mode_variable.set(
                        DEFAULT_OPT101_SENSOR_FILTER_MODE
                    )
                    self.setting_opt101_sensor_filter_mode_entry.config(
                        state="disabled"
                    )

    def serial_port_click_connect(self):
        if self.main_app.emitter_serial:
            self.main_app.emitter_serial.close()
        self.main_app.emitter_serial = EmitterSerial(
            self.serial_port_identifier_variable.get(), 118200  # 118200 or 460800
        )
        self.update_settings_from_serial()
        self.setting_glasses_mode_button.config(state="normal")
        self.update_emitter_firmware_button.config(state="disabled")
        self.update_button.config(state="normal")
        self.save_settings_button.config(state="normal")
        self.serial_port_connect_button.config(state="disabled")
        self.serial_port_disconnect_button.config(state="normal")

    def serial_port_click_disconnect(self):
        if self.main_app.emitter_serial:
            self.main_app.emitter_serial.close()
        self.main_app.emitter_serial = None
        self.setting_opt101_enable_stream_readings_to_serial_toggle_button.config(
            state="disabled"
        )
        self.setting_glasses_mode_button.config(state="disabled")
        self.update_emitter_firmware_button.config(state="normal")
        self.update_button.config(state="disabled")
        self.serial_port_connect_button.config(state="normal")
        self.serial_port_disconnect_button.config(state="disabled")
        self.save_settings_button.config(state="disabled")

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
                f"{self.setting_opt101_enable_duplicate_realtime_reporting_variable.get()},"
                f"{self.setting_opt101_output_stats_variable.get()},"
                f"{self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable.get()}"
            )
            if self.emitter_firmware_version_int >= 10:
                command += f",{self.setting_opt101_block_n_subsequent_duplicates_variable.get()}"
            if self.emitter_firmware_version_int >= 12:
                command += (
                    f",{self.setting_opt101_ignore_all_duplicates_variable.get()}"
                )
            if self.emitter_firmware_version_int >= 13:
                command += f",{self.setting_opt101_sensor_filter_mode_variable.get()}"
            print(command)
            self.main_app.emitter_serial.line_reader.command(command)

    def click_save_settings_to_eeprom(self):
        if self.main_app.emitter_serial:
            self.click_update_settings_on_emitter()
            self.main_app.emitter_serial.line_reader.command(f"8")

    def click_save_visible_settings_to_disk(self):
        file_name = tkinter.filedialog.asksaveasfilename(
            title="Save Emitter Settings to Disk",
            initialdir=os.path.join(self.main_app.base_path, "settings"),
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
                    "opt101_block_n_subsequent_duplicates": self.setting_opt101_block_n_subsequent_duplicates_variable.get(),
                    "opt101_ignore_all_duplicates": self.setting_opt101_ignore_all_duplicates_variable.get(),
                    "opt101_sensor_filter_mode_variable": self.setting_opt101_sensor_filter_mode_variable.get(),
                    "opt101_min_threshold_value_to_activate": self.setting_opt101_min_threshold_value_to_activate_variable.get(),
                    "opt101_detection_threshold": self.setting_opt101_detection_threshold_variable.get(),
                    "opt101_detection_threshold_repeated_high": self.setting_opt101_detection_threshold_repeated_high_variable.get(),
                    "opt101_detection_threshold_repeated_low": self.setting_opt101_detection_threshold_repeated_low_variable.get(),
                    "opt101_enable_ignore_during_ir": self.setting_opt101_enable_ignore_during_ir_variable.get(),
                    "opt101_enable_duplicate_realtime_reporting": self.setting_opt101_enable_duplicate_realtime_reporting_variable.get(),
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
            initialdir=os.path.join(self.main_app.base_path, "settings"),
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
            self.setting_opt101_enable_duplicate_realtime_reporting_variable.set(
                settings["opt101_enable_duplicate_realtime_reporting"]
            )
            self.setting_opt101_output_stats_variable.set(
                settings["opt101_output_stats"]
            )
            self.setting_opt101_enable_frequency_analysis_based_duplicate_frame_detection_variable.set(
                settings[
                    "opt101_enable_frequency_analysis_based_duplicate_frame_detection"
                ]
            )
            self.setting_opt101_block_n_subsequent_duplicates_variable.set(
                settings.get(
                    "opt101_block_n_subsequent_duplicates",
                    DEFAULT_OPT101_BLOCK_N_SUBSEQUENT_DUPLICATES,
                )
            )
            self.setting_opt101_ignore_all_duplicates_variable.set(
                settings.get(
                    "opt101_ignore_all_duplicates", DEFAULT_OPT101_IGNORE_ALL_DUPLICATES
                )
            )
            self.setting_opt101_sensor_filter_mode_variable.set(
                settings.get(
                    "opt101_sensor_filter_mode_variable",
                    DEFAULT_OPT101_SENSOR_FILTER_MODE,
                )
            )

    def click_set_glasses_mode(self):
        if self.main_app.emitter_serial:
            command = f"7,{self.setting_glasses_mode_variable.get()}"
            print(command)
            self.main_app.emitter_serial.line_reader.command(command)

    def click_opt101_enable_stream_readings_to_serial_toggle(self):
        if self.main_app.emitter_serial:
            new_value = (
                self.main_app.emitter_serial.line_reader.debug_opt101_enable_stream_readings_to_serial
                ^ 1
            )
            if new_value == 1:
                if (
                    self.main_app.emitter_serial.line_reader.debug_stream_file
                    is not None
                ):
                    return
                self.main_app.emitter_serial.line_reader.debug_stream_file = open(
                    os.path.join(
                        self.main_app.base_path,
                        f'{datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")}_debug_opt101_stream_readings.csv',
                    ),
                    "wt",
                )
                self.main_app.emitter_serial.line_reader.debug_stream_file.write(
                    "opt101_current_time,left_sensor,right_sensor,duplicate_frames_in_a_row_counter,"
                    "opt101_block_signal_detection_until,opt101_readings_active,"
                    "opt101_reading_above_threshold_left,left_duplicate_detected,left_duplicate_ignored,left_sent_ir,"
                    "opt101_reading_above_threshold_right,right_duplicate_detected,right_duplicate_ignored,right_sent_ir\n"
                )

            self.main_app.emitter_serial.line_reader.debug_opt101_enable_stream_readings_to_serial = (
                new_value
            )

            if new_value == 0:
                self.main_app.emitter_serial.line_reader.debug_stream_file.close()
                self.main_app.emitter_serial.line_reader.debug_stream_file = None
            command = f"10,{new_value}"
            print(command)
            try:
                self.main_app.emitter_serial.line_reader.command(command)
            except:
                if (
                    new_value == 1
                ):  # we have trouble disabling the stream so we ignore no response as the buffer is flooded by incoming data so the OK doesn't always come through as uninterrupted...
                    raise

    def click_update_emitter_firmware(self):
        if (
            self.emitter_firmware_update_dialog
            and self.emitter_firmware_update_dialog.top
        ):
            return
        self.emitter_firmware_update_dialog = EmitterFirmwareUpdateDialog(
            self.top, self.main_app
        )
        self.serial_port_connect_button.config(state="disabled")
        self.top.wait_window(self.emitter_firmware_update_dialog.top)
        pro_micro_ports = [
            port
            for port, desc, hwid in serial.tools.list_ports.comports()  # @UnusedVariable
            if desc == "SparkFun Pro Micro" or desc.startswith("USB Serial Device")
        ]
        self.serial_port_identifier_variable.set(
            pro_micro_ports[0] if pro_micro_ports else "/dev/ttyACM0"
        )
        self.serial_port_connect_button.config(state="normal")

    def click_close(self):
        self.top.destroy()
        self.top = None
        self.close_callback()


class DisplaySettingsDialog:
    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.top = None

        self.target_framerate_variable = tkinter.StringVar(parent)
        self.target_framerate_variable.set(DEFAULT_TARGET_FRAMERATE)
        self.display_resolution_variable = tkinter.StringVar(parent)
        self.display_resolution_variable.set(DEFAULT_DISPLAY_RESOLUTION)
        self.display_zoom_factor_variable = tkinter.StringVar(parent)
        self.display_zoom_factor_variable.set(DEFAULT_DISPLAY_ZOOM_FACTOR)
        self.display_size_variable = tkinter.StringVar(parent)
        self.display_size_variable.set(DEFAULT_DISPLAY_SIZE)
        self.whitebox_brightness_variable = tkinter.StringVar(parent)
        self.whitebox_brightness_variable.set(DEFAULT_WHITEBOX_BRIGHTNESS)
        self.whitebox_corner_position_variable = tkinter.StringVar(parent)
        self.whitebox_corner_position_variable.set(DEFAULT_WHITEBOX_CORNER_POSITION)
        self.whitebox_vertical_position_variable = tkinter.StringVar(parent)
        self.whitebox_vertical_position_variable.set(DEFAULT_WHITEBOX_VERTICAL_POSITION)
        self.whitebox_horizontal_position_variable = tkinter.StringVar(parent)
        self.whitebox_horizontal_position_variable.set(
            DEFAULT_WHITEBOX_HORIZONTAL_POSITION
        )
        self.whitebox_size_variable = tkinter.StringVar(parent)
        self.whitebox_size_variable.set(DEFAULT_WHITEBOX_SIZE)
        self.whitebox_horizontal_spacing_variable = tkinter.StringVar(parent)
        self.whitebox_horizontal_spacing_variable.set(
            DEFAULT_WHITEBOX_HORIZONTAL_SPACING
        )
        self.calibration_mode_variable = tkinter.BooleanVar(parent)
        self.calibration_mode_variable.set(False)

        file_name = os.path.join(
            self.main_app.base_path, "settings", "last_display_settings.json"
        )
        if os.path.exists(file_name):
            self.load_settings_from_file(file_name)

    def show(self):
        top = self.top = tkinter.Toplevel(self.parent)
        top.title("Display Settings")
        top.protocol("WM_DELETE_WINDOW", self.click_close)

        row_count = 0

        self.target_framerate_frame = tkinter.Frame(top)
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
        self.target_framerate_option_menu_tooltip = idlelib.tooltip.Hovertip(
            self.target_framerate_option_menu,
            "If set to a value other than 0 this will force pygame to use a frame delay with tick_busy_loop instead of relying on vsync, this should not normally need to be set and is for experimental purposes only.",
            hover_delay=100,
        )
        self.target_framerate_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.display_resolution_frame = tkinter.Frame(top)
        self.display_resolution_label = tkinter.Label(
            self.display_resolution_frame, text="Display Resolution: "
        )
        self.display_resolution_label.pack(padx=5, side=tkinter.LEFT)
        self.display_resolution_option_menu = tkinter.OptionMenu(
            self.display_resolution_frame,
            self.display_resolution_variable,
            "3840x2160",
            "2560x1080",
            "1920x1080",
            "1280x720",
        )
        self.display_resolution_option_menu.pack(padx=5, side=tkinter.LEFT)
        # self.display_resolution_frame.pack()
        self.display_resolution_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.display_zoom_factor_frame = tkinter.Frame(top)
        self.display_zoom_factor_label = tkinter.Label(
            self.display_zoom_factor_frame, text="Display Zoom Factor: "
        )
        self.display_zoom_factor_label.pack(padx=5, side=tkinter.LEFT)
        self.display_zoom_factor_entry = tkinter.Entry(
            self.display_zoom_factor_frame,
            textvariable=self.display_zoom_factor_variable,
        )
        self.display_zoom_factor_entry.pack(padx=5, side=tkinter.LEFT)
        # self.display_zoom_factor_frame.pack()
        self.display_zoom_factor_tooltip = idlelib.tooltip.Hovertip(
            self.display_zoom_factor_frame,
            "(integer 0 to 100) Zooms out the video by the percent specified. This is to shrink videos on displays which have ghosting at the top and bottom of screen.",
            hover_delay=100,
        )
        self.display_zoom_factor_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.display_size_frame = tkinter.Frame(top)
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
            "Specifying the correct display size (provided in inches), allows the screen specific scaling of the on screen trigger boxes to match the sensors unit.",
            hover_delay=100,
        )
        # self.display_size_frame.pack()
        self.display_size_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.whitebox_brightness_frame = tkinter.Frame(top)
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
            f"The whitebox brightness setting (0 black to 255 white) lets users lower the brightness of the white boxes to help aleviate concerns of OLED burn in. (default {DEFAULT_WHITEBOX_BRIGHTNESS})",
            hover_delay=100,
        )
        # self.whitebox_brightness_frame.pack()
        self.whitebox_brightness_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.whitebox_corner_position_frame = tkinter.Frame(top)
        self.whitebox_corner_position_label = tkinter.Label(
            self.whitebox_corner_position_frame, text="Whitebox Corner Position: "
        )
        self.whitebox_corner_position_label.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_corner_position_option_menu = tkinter.OptionMenu(
            self.whitebox_corner_position_frame,
            self.whitebox_corner_position_variable,
            "top_left",
            "top_right",
            "bottom_left",
            "bottom_right",
        )
        self.whitebox_corner_position_option_menu.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_corner_position_tooltip = idlelib.tooltip.Hovertip(
            self.whitebox_corner_position_frame,
            f"The whitebox corner position lets the user specify where the whitebox should be positioned, for best performance and duplicate frame (dropped frame) handling on OLED displays (or other displays which update from the top of the screen first) top_left or top_right are recommended. (default {DEFAULT_WHITEBOX_CORNER_POSITION})",
            hover_delay=100,
        )
        # self.whitebox_corner_position_frame.pack()
        self.whitebox_corner_position_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.whitebox_vertical_position_frame = tkinter.Frame(top)
        self.whitebox_vertical_position_label = tkinter.Label(
            self.whitebox_vertical_position_frame, text="Whitebox Vertical Position: "
        )
        self.whitebox_vertical_position_label.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_vertical_position_entry = tkinter.Entry(
            self.whitebox_vertical_position_frame,
            textvariable=self.whitebox_vertical_position_variable,
        )
        self.whitebox_vertical_position_entry.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_vertical_position_tooltip = idlelib.tooltip.Hovertip(
            self.whitebox_vertical_position_frame,
            f"The whitebox vertical position lets the user move the screen based whitebox down to better align with the 3d emitter tv mount they have. It is roughly equivalent to mm when display size is correctly configured. (default {DEFAULT_WHITEBOX_VERTICAL_POSITION})",
            hover_delay=100,
        )
        # self.whitebox_vertical_position_frame.pack()
        self.whitebox_vertical_position_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.whitebox_horizontal_position_frame = tkinter.Frame(top)
        self.whitebox_horizontal_position_label = tkinter.Label(
            self.whitebox_horizontal_position_frame,
            text="Whitebox Horizontal Position: ",
        )
        self.whitebox_horizontal_position_label.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_horizontal_position_entry = tkinter.Entry(
            self.whitebox_horizontal_position_frame,
            textvariable=self.whitebox_horizontal_position_variable,
        )
        self.whitebox_horizontal_position_entry.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_horizontal_position_tooltip = idlelib.tooltip.Hovertip(
            self.whitebox_horizontal_position_frame,
            f"The whitebox horizontal position lets the user move the screen based whitebox sideways towards the center of the screen. It is roughly equivalent to mm when display size is correctly configured. (default {DEFAULT_WHITEBOX_HORIZONTAL_POSITION})",
            hover_delay=100,
        )
        # self.whitebox_horizontal_position_frame.pack()
        self.whitebox_horizontal_position_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.whitebox_horizontal_spacing_frame = tkinter.Frame(top)
        self.whitebox_horizontal_spacing_label = tkinter.Label(
            self.whitebox_horizontal_spacing_frame, text="Whitebox Horozontal Spacing: "
        )
        self.whitebox_horizontal_spacing_label.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_horizontal_spacing_entry = tkinter.Entry(
            self.whitebox_horizontal_spacing_frame,
            textvariable=self.whitebox_horizontal_spacing_variable,
        )
        self.whitebox_horizontal_spacing_entry.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_horizontal_spacing_tooltip = idlelib.tooltip.Hovertip(
            self.whitebox_horizontal_spacing_frame,
            f"The whitebox horizontal spacing lets the user increase/decrease the separation between white boxes to better align with the 3d emitter and tv pixel pitch they have. It is roughly equivalent to mm when display size is correctly configured. (default {DEFAULT_WHITEBOX_HORIZONTAL_SPACING})",
            hover_delay=100,
        )
        # self.whitebox_horizontal_spacing_frame.pack()
        self.whitebox_horizontal_spacing_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.whitebox_size_frame = tkinter.Frame(top)
        self.whitebox_size_label = tkinter.Label(
            self.whitebox_size_frame,
            text="Whitebox Size: ",
        )
        self.whitebox_size_label.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_size_entry = tkinter.Entry(
            self.whitebox_size_frame,
            textvariable=self.whitebox_size_variable,
        )
        self.whitebox_size_entry.pack(padx=5, side=tkinter.LEFT)
        self.whitebox_size_tooltip = idlelib.tooltip.Hovertip(
            self.whitebox_size_frame,
            f"The whitebox size lets the user increase or decrease the size of the whitebox. Setting the value too high will lead to cross talk and miss triggering, setting it too low will cause a low signal to noise and also miss triggering. (default {DEFAULT_WHITEBOX_SIZE})",
            hover_delay=100,
        )
        # self.whitebox_size_frame.pack()
        self.whitebox_size_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.calibration_mode_frame = tkinter.Frame(top)
        self.calibration_mode_label = tkinter.Label(
            self.calibration_mode_frame, text="Calibration Mode: "
        )
        self.calibration_mode_label.pack(padx=5, side=tkinter.LEFT)
        self.calibration_mode_check_button = tkinter.Checkbutton(
            self.calibration_mode_frame, variable=self.calibration_mode_variable
        )
        self.calibration_mode_check_button.pack(padx=5, side=tkinter.LEFT)
        self.calibration_mode_tooltip = idlelib.tooltip.Hovertip(
            self.calibration_mode_frame,
            "Calibration mode shows a reticule to help with alignment of the sensor bar \nand also allows for adjustment of emitter frame_delay and frame_duration using hotkeys as instructed on the OSD. \nTo adjust emitter timing parameters you will need to ensure the emitter settings dialog is also open and connected to the emitter. \nTo optimize emitter settings adjustment it is recommended to use the red/blue or black/white test videos.",
            hover_delay=100,
        )
        # self.calibration_mode_frame.pack()
        self.calibration_mode_frame.grid(row=row_count, column=0, sticky="w")
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
            "Saves the display settings shown currently in the UI to the JSON file specified.",
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
            "Loads the display settings from the JSON file specified to the UI.",
            hover_delay=100,
        )
        self.apply_settings_to_active_video_button = tkinter.Button(
            self.action_button_frame_2,
            text="Apply Settings to Active Video",
            command=self.click_apply_settings_to_active_video,
        )
        self.apply_settings_to_active_video_button.pack(padx=5, side=tkinter.LEFT)
        self.apply_settings_to_active_video_button_tooltip = idlelib.tooltip.Hovertip(
            self.load_settings_from_disk_button,
            "Apply settings to an active video if there is one running.",
            hover_delay=100,
        )
        self.close_button = tkinter.Button(
            self.action_button_frame_2, text="Close", command=self.click_close
        )
        self.close_button.pack(padx=5, side=tkinter.LEFT)
        self.close_button_tooltip = idlelib.tooltip.Hovertip(
            self.close_button,
            "Closes this window.",
            hover_delay=100,
        )
        self.action_button_frame_2.grid(row=row_count, column=0, sticky="w")
        row_count += 1

    def save_settings_to_file(self, file_name):
        f = open(file_name, "w")
        json.dump(
            {
                "target_framerate": self.target_framerate_variable.get(),
                "display_resolution": self.display_resolution_variable.get(),
                "display_zoom_factor": self.display_zoom_factor_variable.get(),
                "display_size": self.display_size_variable.get(),
                "whitebox_brightness": self.whitebox_brightness_variable.get(),
                "whitebox_corner_position": self.whitebox_corner_position_variable.get(),
                "whitebox_vertical_position": self.whitebox_vertical_position_variable.get(),
                "whitebox_horizontal_position": self.whitebox_horizontal_position_variable.get(),
                "whitebox_size": self.whitebox_size_variable.get(),
                "whitebox_horizontal_spacing": self.whitebox_horizontal_spacing_variable.get(),
                "calibration_mode": self.calibration_mode_variable.get(),
            },
            f,
            indent=2,
        )
        f.close()

    def click_save_visible_settings_to_disk(self):
        file_name = tkinter.filedialog.asksaveasfilename(
            title="Save Display Settings to Disk",
            initialdir=os.path.join(self.main_app.base_path, "settings"),
            filetypes=[("Display Settings FIle", "*.display_settings.json")],
            defaultextension=".display_settings.json",
        )
        if file_name:
            self.save_settings_to_file(file_name)

    def load_settings_from_file(self, file_name):
        f = open(file_name, "r")
        settings = json.load(f)
        f.close()
        self.target_framerate_variable.set(
            settings.get("target_framerate", DEFAULT_TARGET_FRAMERATE)
        )
        self.display_resolution_variable.set(
            settings.get("display_resolution", DEFAULT_DISPLAY_RESOLUTION)
        )
        self.display_zoom_factor_variable.set(
            settings.get("display_zoom_factor", DEFAULT_DISPLAY_ZOOM_FACTOR)
        )
        self.display_size_variable.set(
            settings.get("display_size", DEFAULT_DISPLAY_SIZE)
        )
        self.whitebox_brightness_variable.set(
            settings.get("whitebox_brightness", DEFAULT_WHITEBOX_BRIGHTNESS)
        )
        self.whitebox_corner_position_variable.set(
            settings.get("whitebox_corner_position", DEFAULT_WHITEBOX_CORNER_POSITION)
        )
        self.whitebox_vertical_position_variable.set(
            settings.get(
                "whitebox_vertical_position", DEFAULT_WHITEBOX_VERTICAL_POSITION
            )
        )
        self.whitebox_horizontal_position_variable.set(
            settings.get(
                "whitebox_horizontal_position", DEFAULT_WHITEBOX_HORIZONTAL_POSITION
            )
        )
        self.whitebox_size_variable.set(
            settings.get("whitebox_size", DEFAULT_WHITEBOX_SIZE)
        )
        self.whitebox_horizontal_spacing_variable.set(
            settings.get(
                "whitebox_horizontal_spacing", DEFAULT_WHITEBOX_HORIZONTAL_SPACING
            )
        )
        self.calibration_mode_variable.set(
            settings.get("calibration_mode", DEFAULT_CALIBRATION_MODE)
        )

    def click_load_visisble_settings_from_disk(self):
        file_name = tkinter.filedialog.askopenfilename(
            title="Load Display Settings from Disk",
            initialdir=os.path.join(self.main_app.base_path, "settings"),
            filetypes=[("Display Settings FIle", "*.display_settings.json")],
        )
        if file_name:
            self.load_settings_from_file(file_name)

    def click_apply_settings_to_active_video(self):
        if self.main_app.pageflipglsink is not None:
            self.main_app.pageflipglsink.set_property(
                "calibration-mode", self.calibration_mode_variable.get()
            )
            self.main_app.pageflipglsink.set_property(
                "display-zoom-factor", self.display_zoom_factor_variable.get()
            )
            self.main_app.pageflipglsink.set_property(
                "whitebox-brightness", self.whitebox_brightness_variable.get()
            )
            self.main_app.pageflipglsink.set_property(
                "whitebox-corner-position", self.whitebox_corner_position_variable.get()
            )
            self.main_app.pageflipglsink.set_property(
                "whitebox-vertical-position",
                self.whitebox_vertical_position_variable.get(),
            )
            self.main_app.pageflipglsink.set_property(
                "whitebox-horizontal-position",
                self.whitebox_horizontal_position_variable.get(),
            )
            self.main_app.pageflipglsink.set_property(
                "whitebox-horizontal-spacing",
                self.whitebox_horizontal_spacing_variable.get(),
            )
            self.main_app.pageflipglsink.set_property(
                "whitebox-size", self.whitebox_size_variable.get()
            )

    def autosave_active_settings(self):
        self.save_settings_to_file(
            os.path.join(
                self.main_app.base_path, "settings", "last_display_settings.json"
            )
        )

    def click_close(self):
        self.autosave_active_settings()
        self.top.destroy()
        self.top = None


class StartVideoDialog:

    LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION = "Load Video Profile From History"
    LOAD_VIDEO_DEFAULTS_HISTORY_OPTION = "Load Defaults"
    LOAD_VIDEO_DEFAULTS_HISTORY_SAVE_NAME = "Defaults"
    VIDEO_HISTORY_MAX_SIZE = 30

    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        top = self.top = tkinter.Toplevel(parent)
        top.title("Open Video File")
        top.protocol("WM_DELETE_WINDOW", self.click_close)

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
        self.__update_video_history_options(update_menu=False)
        self.video_history_frame = tkinter.Frame(top)
        self.video_history_clicked = tkinter.StringVar()
        self.video_history_clicked.set(
            StartVideoDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        )
        self.video_history_dropdown = tkinter.OptionMenu(
            self.video_history_frame,
            self.video_history_clicked,
            *(self.video_history_options),
        )
        self.video_history_dropdown.pack(padx=5, side=tkinter.LEFT)
        self.video_history_clicked.trace("w", self.load_video_profile_from_history)
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
        self.subtitle_font_variable.set(DEFAULT_SUBTITLE_FONT)
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
        self.subtitle_size_variable.set(DEFAULT_SUBTITLE_SIZE)
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
        self.subtitle_depth_variable.set(DEFAULT_SUBTITLE_DEPTH)
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
        self.subtitle_vertical_offset_variable.set(DEFAULT_SUBTITLE_VERTICAL_OFFSET)
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
        self.subtitle_offset_variable.set(DEFAULT_SUBTITLE_OFFSET)
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
        self.frame_packing_variable.set(DEFAULT_FRAME_PACKING)
        self.frame_packing_variable.trace("w", self.__update_right_eye_options)
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
        self.right_eye_variable.set(DEFAULT_RIGHT_EYE)
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
        self.__update_right_eye_options()
        self.right_eye_option_menu.pack(padx=5, side=tkinter.LEFT)
        # self.right_eye_frame.pack()
        self.right_eye_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.action_button_frame_1 = tkinter.Frame(top)
        self.open_button = tkinter.Button(
            self.action_button_frame_1, text="Open", command=self.open_video
        )
        self.open_button.pack(padx=5, side=tkinter.LEFT)

        self.save_defaults_button = tkinter.Button(
            self.action_button_frame_1, text="Save Defaults", command=self.save_defaults
        )
        self.save_defaults_button.pack(padx=5, side=tkinter.LEFT)
        self.action_button_frame_1.grid(row=row_count, column=1)
        row_count += 1

        if self.video_history_default_index is not None:
            self.__load_video_profile_from_history_idx(self.video_history_default_index)

    def __update_right_eye_options(self, *args, **kwargs):
        frame_packing = self.frame_packing_variable.get()
        if frame_packing.startswith("side-by-side"):
            new_menu_options = ["right", "left"]
        elif frame_packing.startswith("over-and-under"):
            new_menu_options = ["top", "bottom"]
        else:
            return
        menu = self.right_eye_option_menu["menu"]
        menu.delete(0, "end")
        for menu_option in new_menu_options:
            menu.add_command(
                label=menu_option,
                command=_setit(self.right_eye_variable, menu_option),
            )
        new_selection = new_menu_options[0]
        if "select" in kwargs:
            new_desired_selection = kwargs["select"]
            if new_desired_selection in new_menu_options:
                new_selection = new_desired_selection
        self.right_eye_variable.set(new_selection)

    def __update_video_history_options(self, update_menu, select_instruction=False):
        self.video_history_options = [
            StartVideoDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        ]
        self.video_history_default_index = None
        for idx, vh in enumerate(self.video_history):
            if (
                vh["video_file_name"]
                == StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_SAVE_NAME
            ):
                self.video_history_default_index = idx
                self.video_history_options.append(
                    StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_OPTION
                )
        self.video_history_options.extend(
            reversed(
                [
                    f"{idx} {vh['history_datetime']} {vh['video_file_name']}"
                    for idx, vh in enumerate(self.video_history)
                    if vh["video_file_name"]
                    != StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_SAVE_NAME
                ]
            )
        )
        if select_instruction:
            self.video_history_clicked.set(
                StartVideoDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
            )
        if update_menu:
            menu = self.video_history_dropdown["menu"]
            menu.delete(1, "end")
            for menu_option in self.video_history_options[1:]:
                menu.add_command(
                    label=menu_option,
                    command=_setit(self.video_history_clicked, menu_option),
                )

    def __load_video_profile_from_history_idx(self, selected_index):
        selected_video_history = self.video_history[selected_index]
        target_video_file_name = selected_video_history["video_file_name"]
        if (
            target_video_file_name
            != StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_SAVE_NAME
        ):
            self.video_file_name = target_video_file_name
        self.video_file_location_label.config(text=self.video_file_name)
        if (
            target_video_file_name
            != StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_SAVE_NAME
        ):
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
        self.__update_right_eye_options(select=selected_video_history["right_eye"])
        # self.right_eye_variable.set(selected_video_history["right_eye"])

    def load_video_profile_from_history(self, *args):  # @UnusedVariable
        if (
            self.video_history_clicked.get()
            == StartVideoDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        ):
            return
        if (
            self.video_history_clicked.get()
            == StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_OPTION
        ):
            selected_index = self.video_history_default_index
        else:
            selected_index = int(self.video_history_clicked.get().split()[0])
        self.__load_video_profile_from_history_idx(selected_index)

    def remove_video_profile_from_history(self):
        if (
            self.video_history_clicked.get()
            == StartVideoDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
        ):
            return
        if (
            self.video_history_clicked.get()
            == StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_OPTION
        ):
            selected_index = self.video_history_default_index
        else:
            selected_index = int(self.video_history_clicked.get().split()[0])
        self.video_history.pop(selected_index)
        f = open(self.history_file_path, "w")
        json.dump(self.video_history, f, indent=2)
        f.close()
        self.__update_video_history_options(update_menu=True, select_instruction=True)

    def select_video_file(self):
        new_video_file_name = tkinter.filedialog.askopenfilename(
            title="Select Video from Disk",
            initialdir=self.main_app.select_video_initialdir,
        )
        if new_video_file_name:
            self.main_app.select_video_initialdir = os.path.dirname(
                os.path.abspath(new_video_file_name)
            )
            self.main_app.select_subtitle_initialdir = (
                self.main_app.select_video_initialdir
            )
            self.video_file_name = new_video_file_name
            self.video_file_location_label.config(text=self.video_file_name)
            self.frame_packing_variable.set(
                StartVideoDialog.get_frame_packing_from_filename(new_video_file_name)
            )
            self.__update_right_eye_options()

    def select_subtitle_file(self):
        new_subtitle_file_name = tkinter.filedialog.askopenfilename(
            title="Select Subtitle from Disk",
            initialdir=self.main_app.select_subtitle_initialdir,
        )
        if new_subtitle_file_name:
            self.main_app.select_subtitle_initialdir = os.path.dirname(
                os.path.abspath(new_subtitle_file_name)
            )
            self.subtitle_file_name = new_subtitle_file_name
            self.subtitle_file_location_label.config(text=self.subtitle_file_name)

    def __build_video_history_entry(self):
        return {
            "video_file_name": None,
            "subtitle_file_name": self.subtitle_file_name,
            "subtitle_font": self.subtitle_font_variable.get(),
            "subtitle_size": self.subtitle_size_variable.get(),
            "subtitle_depth": self.subtitle_depth_variable.get(),
            "subtitle_vertical_offset": self.subtitle_vertical_offset_variable.get(),
            "subtitle_offset": self.subtitle_offset_variable.get(),
            "frame_packing": self.frame_packing_variable.get(),
            "right_eye": self.right_eye_variable.get(),
        }

    def save_defaults(self):
        new_video_history_entry = self.__build_video_history_entry()
        new_video_history_entry["video_file_name"] = (
            StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_SAVE_NAME
        )
        if self.video_history_default_index is None:
            self.video_history = [new_video_history_entry] + self.video_history
        else:
            self.video_history[self.video_history_default_index] = (
                new_video_history_entry
            )

        f = open(self.history_file_path, "w")
        json.dump(self.video_history, f, indent=2)
        f.close()
        self.__update_video_history_options(update_menu=True)

    def open_video(self):
        if (
            not self.video_file_name
            or self.video_file_name
            == StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_SAVE_NAME
        ):
            return

        new_video_history_entry = self.__build_video_history_entry()
        new_video_history_entry["video_file_name"] = self.video_file_name
        save_history = True
        if (
            self.video_history_clicked.get()
            != StartVideoDialog.LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION
            and self.video_history_clicked.get()
            != StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_OPTION
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
            if len(self.video_history) > StartVideoDialog.VIDEO_HISTORY_MAX_SIZE:
                if self.video_history_default_index is None:
                    self.video_history = self.video_history[1:]
                else:
                    self.video_history = self.video_history[:1] + self.video_history[2:]
            f = open(self.history_file_path, "w")
            json.dump(self.video_history, f, indent=2)
            f.close()
        self.perform_open = True
        self.top.destroy()
        self.top = None

    def click_close(self):
        self.top.destroy()
        self.top = None

    @staticmethod
    def get_frame_packing_from_filename(filename):
        if re.match(".*[_\-\.](((half)|(h))[_\-\.]?)sbs[_\-\.].*", filename, re.I):
            return "half-side-by-side"
        if re.match(".*[_\-\.](((full)|(f))[_\-\.]?)sbs[_\-\.].*", filename, re.I):
            return "full-side-by-side"
        if re.match(
            ".*[_\-\.](((half)|(h))[_\-\.]?)((ou)|(tab))[_\-\.].*", filename, re.I
        ):
            return "half-over-and-under"
        if re.match(
            ".*[_\-\.](((full)|(f))[_\-\.]?)((ou)|(tab))[_\-\.].*", filename, re.I
        ):
            return "full-over-and-under"
        half_or_not = True
        if re.match(".*[_\-\.]((full)|f)[_\-\.].*", filename):
            half_or_not = False
        if re.match(".*[_\-\.]((half)|h)[_\-\.].*", filename):
            half_or_not = True
        side_by_side_or_over_and_under = True
        if re.match(
            ".*[_\-\.]((ou)|(over[_\-\.]?(and)?[_\-\.]?under)|(tab)|(top[_\-\.]?(and)?[_\-\.]?bottom))[_\-\.].*",
            filename,
        ):
            side_by_side_or_over_and_under = False
        if re.match(
            ".*[_\-\.]((sbs)|(side[_\-\.]?(by)?[_\-\.]?side))[_\-\.].*", filename
        ):
            side_by_side_or_over_and_under = True
        return f"{'side-by-side' if side_by_side_or_over_and_under else 'over-and-under'}-{'half' if half_or_not else 'full'}"

    @staticmethod
    def get_video_history_default_settings():
        history_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "video_history.json"
        )
        if os.path.exists(history_file_path):
            f = open(history_file_path, "r")
            video_history = json.load(f)
            f.close()
            for vh in video_history:
                if (
                    vh["video_file_name"]
                    == StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_SAVE_NAME
                ):
                    return vh
        return {
            "video_file_name": "Defaults",
            "subtitle_file_name": "",
            "subtitle_font": (DEFAULT_SUBTITLE_FONT),
            "subtitle_size": DEFAULT_SUBTITLE_SIZE,
            "subtitle_depth": DEFAULT_SUBTITLE_DEPTH,
            "subtitle_vertical_offset": DEFAULT_SUBTITLE_VERTICAL_OFFSET,
            "subtitle_offset": DEFAULT_SUBTITLE_OFFSET,
            "frame_packing": DEFAULT_FRAME_PACKING,
            "right_eye": DEFAULT_RIGHT_EYE,
        }


class TopWindow:
    def __init__(self, command_line_arguments):
        self.player = None
        self.video_open = False
        self.paused = False
        self.close = False
        self.emitter_serial = None

        self.pageflipglsink = None
        self.subtitle3dsink = None

        # set base path
        internal_base_path = os.path.dirname(os.path.abspath(__file__))
        split_base_path = os.path.split(internal_base_path)
        if "_internal" == split_base_path[1]:
            self.base_path = split_base_path[0]
        else:
            self.base_path = internal_base_path

        self.window = window = tkinter.Tk()
        window.wm_attributes("-topmost", True)
        try:
            window.wm_attributes(
                "-type", "toolbar"
            )  # no titlebar and not always on top (starts perfectly at top of screen)
        except Exception:
            window.wm_attributes("-toolwindow", True)
        # window.wm_attributes('-type', 'dock') # no titlebar and always on top of regular window manager (but starts off top of screen)
        window.protocol("WM_DELETE_WINDOW", self.close_player)
        window.title("")
        window.geometry("+300+0")
        # window.geometry("+2000+0")
        window.update_idletasks()
        self._offsetx = -self.window.winfo_rootx()
        self._offsety = -self.window.winfo_rooty()

        self.emitter_settings_dialog = None
        self.display_settings_dialog = None
        self.start_video_dialog = None
        self.select_video_initialdir = os.path.join(self.base_path, "videos")
        self.select_subtitle_initialdir = os.path.join(self.base_path, "videos")
        self.select_firmware_file_initialdir = os.path.join(self.base_path, "firmwares")

        top_frame = tkinter.Frame(window)
        top_frame.pack(fill="x", expand=1, pady=5, padx=25, anchor="n")
        open_emitter_settings_button_image = svg_to_imagetk_photoimage(
            "./images/sliders2-ir.svg"
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
        open_display_settings_button_image = svg_to_imagetk_photoimage(
            "./images/sliders2-tv.svg"
        )
        open_display_settings_button = tkinter.Button(
            top_frame,
            text="Open Display Settings",
            image=open_display_settings_button_image,
            highlightthickness=0,
            bd=0,
        )
        open_display_settings_button.tk_img = open_display_settings_button_image
        open_display_settings_button_tooltip = (  # @UnusedVariable
            idlelib.tooltip.Hovertip(  # @UnusedVariable
                open_display_settings_button,
                "Open display settings to tweak display parameters.",
                hover_delay=100,
            )
        )
        open_display_settings_button.pack(padx=5, side=tkinter.LEFT)
        open_display_settings_button.bind(
            "<Button-1>", self.click_open_display_settings_button
        )
        open_video_file_button_image = svg_to_imagetk_photoimage(
            "./images/folder2-open.svg"
        )
        self.__open_video_file_button = tkinter.Button(
            top_frame,
            text="Open Video File",
            image=open_video_file_button_image,
            highlightthickness=0,
            bd=0,
        )
        self.__open_video_file_button.tk_img = open_video_file_button_image
        open_video_file_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            self.__open_video_file_button,
            "Open a video file for playback.",
            hover_delay=100,
        )
        self.__open_video_file_button.pack(padx=5, side=tkinter.LEFT)
        self.__open_video_file_button.bind("<Button-1>", self.click_start_video_button)
        stop_video_button_image = svg_to_imagetk_photoimage("./images/stop-fill.svg")
        self.__stop_video_button = tkinter.Button(
            top_frame,
            text="Stop Video",
            image=stop_video_button_image,
            highlightthickness=0,
            bd=0,
        )
        self.__stop_video_button.config(state="disabled")
        self.__stop_video_button.tk_img = stop_video_button_image
        stop_video_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            self.__stop_video_button,
            "Click to stop and close current video.",
            hover_delay=100,
        )
        self.__stop_video_button.pack(padx=5, side=tkinter.LEFT)
        self.__stop_video_button.bind("<Button-1>", self.click_stop_video_button)
        fullscreen_button_image = svg_to_imagetk_photoimage(
            "./images/arrows-fullscreen.svg"
        )
        self.__fullscreen_button = tkinter.Button(
            top_frame,
            text="Fullscreen/Windowed (F11)",
            image=fullscreen_button_image,
            highlightthickness=0,
            bd=0,
        )
        self.__fullscreen_button.config(state="disabled")
        self.__fullscreen_button.tk_img = fullscreen_button_image
        fullscreen_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            self.__fullscreen_button, "Toggle fullscreen (F11).", hover_delay=100
        )
        self.__fullscreen_button.pack(padx=5, side=tkinter.LEFT)
        self.__fullscreen_button.bind("<Button-1>", self.toggle_fullscreen)
        flip_right_and_left_button_image = svg_to_imagetk_photoimage(
            "./images/flip-right-and-left.svg"
        )
        self.__flip_right_and_left_button = tkinter.Button(
            top_frame,
            text="Flip Right and Left (F)",
            image=flip_right_and_left_button_image,
            highlightthickness=0,
            bd=0,
        )
        self.__flip_right_and_left_button.config(state="disabled")
        self.__flip_right_and_left_button.tk_img = flip_right_and_left_button_image
        flip_right_and_left_button_tooltip = (  # @UnusedVariable
            idlelib.tooltip.Hovertip(
                self.__flip_right_and_left_button,
                "Flip Right and Left (F).",
                hover_delay=100,
            )
        )
        self.__flip_right_and_left_button.pack(padx=5, side=tkinter.LEFT)
        self.__flip_right_and_left_button.bind("<Button-1>", self.flip_right_and_left)
        tooltip_number_text = (
            "\nUse numbers 0-9 to fast seek from 0% to 90% through the video."
        )
        backward_big_button_image = svg_to_imagetk_photoimage(
            "./images/rewind-3-fill.svg"
        )
        self.__backward_big_button = tkinter.Button(
            top_frame,
            text="Back 60s (shift-left)",
            image=backward_big_button_image,
            highlightthickness=0,
            bd=0,
        )
        self.__backward_big_button.config(state="disabled")
        self.__backward_big_button.tk_img = backward_big_button_image
        backward_big_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            self.__backward_big_button,
            f"Rewind 60s (Shift-Left-Arrow).{tooltip_number_text}",
            hover_delay=100,
        )
        self.__backward_big_button.pack(padx=5, side=tkinter.LEFT)
        self.__backward_big_button.bind(
            "<Button-1>", functools.partial(self.perform_seek, "seek_backward_big")
        )
        backward_small_button_image = svg_to_imagetk_photoimage(
            "./images/rewind-fill.svg"
        )
        self.__backward_small_button = tkinter.Button(
            top_frame,
            text="Back 5s (left)",
            image=backward_small_button_image,
            highlightthickness=0,
            bd=0,
        )
        self.__backward_small_button.config(state="disabled")
        self.__backward_small_button.tk_img = backward_small_button_image
        backward_small_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            self.__backward_small_button,
            f"Rewind 5s (Left-Arrow).{tooltip_number_text}",
            hover_delay=100,
        )
        self.__backward_small_button.pack(padx=5, side=tkinter.LEFT)
        self.__backward_small_button.bind(
            "<Button-1>", functools.partial(self.perform_seek, "seek_backward_small")
        )
        play_pause_button_image = svg_to_imagetk_photoimage(
            "./images/play-pause-fill.svg"
        )
        self.__play_pause_button = tkinter.Button(
            top_frame,
            text="Play/Pause (Space)",
            image=play_pause_button_image,
            highlightthickness=0,
            bd=0,
        )
        self.__play_pause_button.config(state="disabled")
        self.__play_pause_button.tk_img = play_pause_button_image
        play_pause_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            self.__play_pause_button,
            "Click to play/pause current video. (Space)",
            hover_delay=100,
        )
        self.__play_pause_button.pack(padx=5, side=tkinter.LEFT)
        self.__play_pause_button.bind("<Button-1>", self.toggle_paused)
        forward_small_button_image = svg_to_imagetk_photoimage(
            "./images/fast-forward-fill.svg"
        )
        self.__forward_small_button = tkinter.Button(
            top_frame,
            text="Forward 5s (right)",
            image=forward_small_button_image,
            highlightthickness=0,
            bd=0,
        )
        self.__forward_small_button.config(state="disabled")
        self.__forward_small_button.tk_img = forward_small_button_image
        forward_small_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            self.__forward_small_button,
            f"Fastforward 5s (Right-Arrow).{tooltip_number_text}",
            hover_delay=100,
        )
        self.__forward_small_button.pack(padx=5, side=tkinter.LEFT)
        self.__forward_small_button.bind(
            "<Button-1>", functools.partial(self.perform_seek, "seek_forward_small")
        )
        forward_big_button_image = svg_to_imagetk_photoimage(
            "./images/fast-forward-3-fill.svg"
        )
        self.__forward_big_button = tkinter.Button(
            top_frame,
            text="Forward 60s (shift-right)",
            image=forward_big_button_image,
            highlightthickness=0,
            bd=0,
        )
        self.__forward_big_button.config(state="disabled")
        self.__forward_big_button.tk_img = forward_big_button_image
        forward_big_button_tooltip = idlelib.tooltip.Hovertip(  # @UnusedVariable
            self.__forward_big_button,
            f"Fastforward 60s (Shift-Right-Arrow).{tooltip_number_text}",
            hover_delay=100,
        )
        self.__forward_big_button.pack(padx=5, side=tkinter.LEFT)
        self.__forward_big_button.bind(
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

        # create display settings dialog object to store display settings
        self.display_settings_dialog = DisplaySettingsDialog(self.window, self)

        self.process_command_line_arguments(command_line_arguments)

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

        self.__open_video_file_button.config(state="normal")
        self.__flip_right_and_left_button.config(state="disabled")
        self.__fullscreen_button.config(state="disabled")
        self.__backward_big_button.config(state="disabled")
        self.__backward_small_button.config(state="disabled")
        self.__stop_video_button.config(state="disabled")
        self.__play_pause_button.config(state="disabled")
        self.__forward_small_button.config(state="disabled")
        self.__forward_big_button.config(state="disabled")

        if self.player is not None:
            self.player.set_state(Gst.State.NULL)
        self.video_open = False
        if self.emitter_serial is not None:
            self.emitter_serial.pageflipglsink = None
        if self.pageflipglsink is not None:
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
        self.display_settings_dialog.autosave_active_settings()
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
        seek_position = None
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
        if seek_position is not None:
            # https://gstreamer.freedesktop.org/documentation/gstreamer/gstsegment.html?gi-language=python#GstSeekFlags
            # 'ACCURATE', 'FLUSH', 'KEY_UNIT', 'NONE', 'SEGMENT', 'SKIP', 'SNAP_AFTER', 'SNAP_BEFORE', 'SNAP_NEAREST', 'TRICKMODE', 'TRICKMODE_KEY_UNITS', 'TRICKMODE_NO_AUDIO'
            self.player.seek_simple(
                Gst.Format.TIME,
                # Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, # use these flags for fast seeking that isn't accurate
                Gst.SeekFlags.FLUSH
                | Gst.SeekFlags.ACCURATE,  # use these flags for slower but accurate seeking
                max(seek_position, 0),
            )

    def click_open_emitter_settings_button(self, event=None):  # @UnusedVariable
        if self.emitter_settings_dialog and self.emitter_settings_dialog.top:
            return

        def close_callback():
            self.emitter_settings_dialog = None

        self.emitter_settings_dialog = EmitterSettingsDialog(
            self.window, self, close_callback
        )
        # self.window.wait_window(self.emitter_settings_dialog.top)

    def click_open_display_settings_button(self, event=None):  # @UnusedVariable
        if self.display_settings_dialog and self.display_settings_dialog.top:
            return
        self.display_settings_dialog.show()

    def process_command_line_arguments(self, args):
        if args.video_path:
            playback_parameters = StartVideoDialog.get_video_history_default_settings()
            playback_parameters["video_file_name"] = str(pathlib.Path(args.video_path))
            if args.subtitle_path:
                playback_parameters["subtitle_file_name"] = str(
                    pathlib.Path(args.subtitle_path)
                )
            if args.frame_packing:
                frame_packing = args.frame_packing
            else:
                frame_packing = StartVideoDialog.get_frame_packing_from_filename(
                    playback_parameters["video_file_name"]
                )
            playback_parameters["frame_packing"] = frame_packing
            if args.right_eye:
                playback_parameters["right_eye"] = args.right_eye
            else:
                playback_parameters["right_eye"] = (
                    "right" if frame_packing.startswith("side-by-side") else "top"
                )
            if args.display_resolution:
                playback_parameters["display_resolution"] = args.display_resolution
            self.start_video(playback_parameters)

    def click_start_video_button(self, event=None):  # @UnusedVariable
        if self.video_open:
            return

        if self.start_video_dialog and self.start_video_dialog.top:
            return

        self.start_video_dialog = start_video_dialog = StartVideoDialog(
            self.window, self
        )
        self.window.wait_window(start_video_dialog.top)

        if not start_video_dialog.perform_open:
            return

        playback_parameters = {
            "video_file_name": start_video_dialog.video_file_name,
            "subtitle_file_name": start_video_dialog.subtitle_file_name,
            "subtitle_font": start_video_dialog.subtitle_font_variable.get(),
            "subtitle_size": start_video_dialog.subtitle_size_variable.get(),
            "subtitle_depth": start_video_dialog.subtitle_depth_variable.get(),
            "subtitle_vertical_offset": (
                start_video_dialog.subtitle_vertical_offset_variable.get()
            ),
            "subtitle_offset": start_video_dialog.subtitle_offset_variable.get(),
            "frame_packing": start_video_dialog.frame_packing_variable.get(),
            "right_eye": start_video_dialog.right_eye_variable.get(),
        }

        self.start_video(playback_parameters)

    def start_video(self, playback_parameters):

        video_file_name = playback_parameters["video_file_name"]
        subtitle_file_name = playback_parameters["subtitle_file_name"]
        subtitle_font = playback_parameters["subtitle_font"]
        subtitle_size = playback_parameters["subtitle_size"]
        subtitle_depth = playback_parameters["subtitle_depth"]
        subtitle_vertical_offset = playback_parameters["subtitle_vertical_offset"]
        subtitle_offset = playback_parameters["subtitle_offset"]
        frame_packing = playback_parameters["frame_packing"]
        right_eye = playback_parameters["right_eye"]

        target_framerate = self.display_settings_dialog.target_framerate_variable.get()
        display_resolution = playback_parameters.get(
            "display_resolution",
            (self.display_settings_dialog.display_resolution_variable.get()),
        )
        display_zoom_factor = playback_parameters.get(
            "display_zoom_factor",
            (self.display_settings_dialog.display_zoom_factor_variable.get()),
        )
        display_size = self.display_settings_dialog.display_size_variable.get()
        whitebox_brightness = (
            self.display_settings_dialog.whitebox_brightness_variable.get()
        )
        whitebox_corner_position = (
            self.display_settings_dialog.whitebox_corner_position_variable.get()
        )
        whitebox_vertical_position = (
            self.display_settings_dialog.whitebox_vertical_position_variable.get()
        )
        whitebox_horizontal_position = (
            self.display_settings_dialog.whitebox_horizontal_position_variable.get()
        )
        whitebox_size = self.display_settings_dialog.whitebox_size_variable.get()
        whitebox_horizontal_spacing = (
            self.display_settings_dialog.whitebox_horizontal_spacing_variable.get()
        )
        calibration_mode = self.display_settings_dialog.calibration_mode_variable.get()
        # print(frame_packing)
        # print(right_eye)
        # print(display_resolution)
        if video_file_name == "":
            return
        video_file_path = os.path.realpath(video_file_name)
        if not os.path.exists(video_file_path):
            return
        video_file_path = "file:///" + video_file_path.replace("\\", "/").replace(
            ":", "|"
        )

        if subtitle_file_name:
            show_subtitles = True
            subtitle_file_path = os.path.realpath(subtitle_file_name)
            if subtitle_offset != "0":
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

        display_resolution_width, display_resolution_height = tuple(  # @UnusedVariable
            map(int, display_resolution.split("x"))
        )

        filters_to_prioritize = [
            "nvjpegdec",
            "nvmpeg2videodec",
            "nvmpeg4videodec",
            "nvmpegvideodec",
            "nvh264dec",
            "nvh265dec",
            "nvvp9dec",
        ]
        # filters_to_prioritize = []
        for filter_to_prioritize in filters_to_prioritize:
            primary_decoder_element_factory = Gst.ElementFactory.find(
                filter_to_prioritize
            )
            if primary_decoder_element_factory:
                primary_decoder_element_factory.set_rank(Gst.Rank.PRIMARY + 1)
        filters_to_deprioritize = ["vaapidecodebin"]
        # filters_to_deprioritize = []
        for filter_to_deprioritize in filters_to_deprioritize:
            primary_decoder_element_factory = Gst.ElementFactory.find(
                filter_to_deprioritize
            )
            if primary_decoder_element_factory:
                primary_decoder_element_factory.set_rank(Gst.Rank.NONE)

        # self.player = Gst.ElementFactory.make("playbin", "Playbin")
        self.player = Gst.ElementFactory.make("playbin3", "Playbin")

        self.player.set_property("uri", video_file_path)
        # self.player.set_property("current-audio", -1)  # -1 is the first audio stream
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

        self.pageflipglsink.set_property("calibration-mode", calibration_mode)
        self.pageflipglsink.set_property("fullscreen", False)
        self.pageflipglsink.set_property("frame-packing", frame_packing)
        self.pageflipglsink.set_property("right-eye", right_eye)
        self.pageflipglsink.set_property("target-framerate", target_framerate)
        self.pageflipglsink.set_property("display-resolution", display_resolution)
        self.pageflipglsink.set_property("display-zoom-factor", display_zoom_factor)
        self.pageflipglsink.set_property("display-size", display_size)
        self.pageflipglsink.set_property("whitebox-brightness", whitebox_brightness)
        self.pageflipglsink.set_property(
            "whitebox-corner-position", whitebox_corner_position
        )
        self.pageflipglsink.set_property(
            "whitebox-vertical-position", whitebox_vertical_position
        )
        self.pageflipglsink.set_property(
            "whitebox-horizontal-position", whitebox_horizontal_position
        )
        self.pageflipglsink.set_property(
            "whitebox-horizontal-spacing", whitebox_horizontal_spacing
        )
        self.pageflipglsink.set_property("whitebox-size", whitebox_size)
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

        # setting fullscreen prematurely has no effect until video playback has full started
        for _ in range(75):
            if self.pageflipglsink.get_property("started"):
                break
            time.sleep(0.2)
        else:
            # if it didn't start after 15 seconds just stop as it probably means there was a gstreamer decoding error
            self.stop_player()

        duration = self.player.query_duration(Gst.Format.TIME).duration
        self.pageflipglsink.set_property("video-duration", duration)

        # even after playback started it can still take 1-2 second until all the renderers are ready
        for _ in range(10):
            time.sleep(0.2)
            self.pageflipglsink.set_property("fullscreen", True)

        self.__open_video_file_button.config(state="disabled")
        self.__flip_right_and_left_button.config(state="normal")
        self.__fullscreen_button.config(state="normal")
        self.__backward_big_button.config(state="normal")
        self.__backward_small_button.config(state="normal")
        self.__stop_video_button.config(state="normal")
        self.__play_pause_button.config(state="normal")
        self.__forward_small_button.config(state="normal")
        self.__forward_big_button.config(state="normal")

        Gst.debug_bin_to_dot_file(
            self.player,
            Gst.DebugGraphDetails.ALL,
            "pipeline_" + datetime.datetime.now().strftime("%Y-%m-%d %H%M%S"),
        )

    def click_stop_video_button(self, event=None):  # @UnusedVariable
        self.stop_player()


if __name__ == "__main__":

    if os.name == "nt":
        os.system("chcp.com 65001")

    # set base path
    internal_base_path = os.path.dirname(os.path.abspath(__file__))
    gstreamer_plugins_active = os.path.join(
        internal_base_path, "gstreamer_plugins_active"
    )
    split_base_path = os.path.split(internal_base_path)
    if "_internal" == split_base_path[1]:
        base_path = split_base_path[0]
    else:
        base_path = internal_base_path
    os.environ["GST_DEBUG"] = "3"
    os.environ["GST_PLUGIN_PATH"] = (
        f"{gstreamer_plugins_active}:{internal_base_path}:{os.environ.get('GST_PLUGIN_PATH', '')}"
    )
    os.environ["GST_DEBUG_DUMP_DOT_DIR"] = os.path.join(base_path, "dot_files")
    # LIBVA_DRIVER_NAME=i965 vainfo --display drm --device /dev/dri/renderD128
    # os.environ["GST_VAAPI_ALL_DRIVERS"] = "1" # This environment variable can be set, independently of its value, to disable the drivers white list. By default only intel and mesa va drivers are loaded if they are available. The rest are ignored. With this environment variable defined, all the available va drivers are loaded, even if they are deprecated.
    # os.environ["LIBVA_DRIVER_NAME"] = "i965" # This environment variable can be set with the drivers name to load. For example, intel's driver is i965, meanwhile mesa is gallium.
    # os.environ["LIBVA_DRIVERS_PATH"] = "" # This environment variable can be set to a colon-separated list of paths (or a semicolon-separated list on Windows). libva will scan these paths for va drivers.
    # os.environ["GST_VAAPI_DRM_DEVICE"] = "/dev/dri/renderD128" # This environment variable can be set to a specified DRM device when DRM display is used, it is ignored when other types of displays are used. By default /dev/dri/renderD128 is used for DRM display.
    # os.environ["GST_PLUGIN_FEATURE_RANK"] = "vaapih264dec:MAX"

    import gi

    gi.require_version("Gst", "1.0")
    gi.require_version("GstBase", "1.0")
    gi.require_version("GstVideo", "1.0")
    # gi.require_version('GdkX11', '3.0') # windows
    # from gi.repository import Gst, GObject, GdkX11, GstVideo, GstBase # windows
    from gi.repository import Gst  # windows
    from gi.repository import (
        GObject,  # @UnusedImport
        GstVideo,  # @UnusedImport
        GstBase,  # @UnusedImport
    )  # we need to import these here or pyinstaller won't pickup GstBase-1.0.typelib and GstVideo-1.0.typelib

    # GObject.threads_init()
    Gst.init(None)

    # parse commandline arguments
    parser = argparse.ArgumentParser(
        prog="Open3DOLED 3DPlayer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
        Plays 3D videos for use with Open3DOLED emitter unit. 
        This commandline interface is used for launching videos directly, unless a video is specified all other parameters will be ignored.
        """
        ),
        epilog="Uses default display settings and video settings set in app to play specified file unless overriden on command-line.",
    )
    parser.add_argument("--video-path")
    parser.add_argument("--subtitle-path")
    parser.add_argument(
        "--frame-packing",
        choices=[
            "side-by-side-full",
            "side-by-side-half",
            "over-and-under-full",
            "over-and-under-half",
        ],
    )
    parser.add_argument("--right-eye", choices=["right", "left", "top", "bottom"])
    parser.add_argument(
        "--display-resolution",
        choices=[
            "3840x2160",
            "2560x1080",
            "1920x1080",
            "1280x720",
        ],
    )

    top_window = TopWindow(parser.parse_args())

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
                        if r.startswith("calibration-"):
                            increment_by = 0
                            target = None
                            (
                                _,
                                calibration_target_field,
                                calibration_decrease_or_increase_or_set,
                                calibration_adjustment_amount,
                            ) = r.split("-")
                            calibration_target_field_map = {
                                "calibration_mode": (
                                    "display",
                                    top_window.display_settings_dialog.calibration_mode_variable,
                                ),
                                "white_box_vertical_position": (
                                    "display",
                                    top_window.display_settings_dialog.whitebox_vertical_position_variable,
                                ),
                                "white_box_horizontal_position": (
                                    "display",
                                    top_window.display_settings_dialog.whitebox_horizontal_position_variable,
                                ),
                                "white_box_horizontal_spacing": (
                                    "display",
                                    top_window.display_settings_dialog.whitebox_horizontal_spacing_variable,
                                ),
                                "white_box_size": (
                                    "display",
                                    top_window.display_settings_dialog.whitebox_size_variable,
                                ),
                            }
                            if top_window.emitter_settings_dialog is not None:
                                calibration_target_field_map["frame_delay"] = (
                                    "emitter",
                                    top_window.emitter_settings_dialog.setting_ir_frame_delay_variable,
                                )
                                calibration_target_field_map["frame_duration"] = (
                                    "emitter",
                                    top_window.emitter_settings_dialog.setting_ir_frame_duration_variable,
                                )

                            if (
                                calibration_target_field
                                not in calibration_target_field_map
                            ):
                                continue
                            emitter_or_display, target = calibration_target_field_map[
                                calibration_target_field
                            ]
                            if calibration_decrease_or_increase_or_set == "increase":
                                set_to = str(
                                    int(target.get())
                                    + int(calibration_adjustment_amount)
                                )
                            elif calibration_decrease_or_increase_or_set == "decrease":
                                set_to = str(
                                    int(target.get())
                                    - int(calibration_adjustment_amount)
                                )
                            elif calibration_decrease_or_increase_or_set == "set":
                                set_to = (
                                    True
                                    if calibration_adjustment_amount == "true"
                                    else (
                                        False
                                        if calibration_adjustment_amount == "false"
                                        else calibration_adjustment_amount
                                    )
                                )
                            else:
                                continue
                            target.set(set_to)
                            if (
                                emitter_or_display == "emitter"
                                and top_window.emitter_serial is not None
                            ):
                                top_window.emitter_settings_dialog.click_update_settings_on_emitter()
                            if emitter_or_display == "display":
                                top_window.display_settings_dialog.click_apply_settings_to_active_video()
                            if calibration_target_field != "calibration_mode":
                                top_window.pageflipglsink.set_property(
                                    "latest-subtitle-data",
                                    json.dumps(
                                        {
                                            "show_now": True,
                                            "text": f"{calibration_target_field} {target.get()} {'connect emitter!' if emitter_or_display == 'emitter' and top_window.emitter_serial is None else ''}",
                                            "duration": 1000000000,
                                        }
                                    ),
                                )

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
