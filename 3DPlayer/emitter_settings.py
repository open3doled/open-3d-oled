import os
import time
import datetime
import traceback
import serial.threaded
import serial.tools.list_ports
import threading
import queue
import json
import tkinter  # @UnusedImport
import tkinter.filedialog
import idlelib.tooltip

import avrloader
import util

# Default IR Settings
DEFAULT_IR_DRIVE_MODE = "0"
DEFAULT_IR_PROTOCOL = "6"
DEFAULT_GLASSES_MODE = "0"
DEFAULT_IR_FRAME_DELAY = "500"
DEFAULT_IR_FRAME_DURATION = "7000"
DEFAULT_IR_SIGNAL_SPACING = "30"
DEFAULT_IR_FLIP_EYES = "0"
DEFAULT_TARGET_FRAMETIME = "0"
DEFAULT_PWM_BACKLIGHT_FREQUENCY = "0"
DEFAULT_OPT_BLOCK_SIGNAL_DETECTION_DELAY = "7500"
DEFAULT_OPT_BLOCK_N_SUBSEQUENT_DUPLICATES = "0"
DEFAULT_OPT_IGNORE_ALL_DUPLICATES = "0"
DEFAULT_OPT_MIN_THRESHOLD_VALUE_TO_ACTIVATE = "10"
DEFAULT_OPT_DETECTION_THRESHOLD_HIGH = "128"
DEFAULT_OPT_DETECTION_THRESHOLD_LOW = "32"
DEFAULT_OPT_ENABLE_IGNORE_DURING_IR = "0"
DEFAULT_OPT_ENABLE_DUPLICATE_REALTIME_REPORTING = "0"
DEFAULT_OPT_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION = "0"
DEFAULT_OPT_DETECTION_THRESHOLD_REPEATED_HIGH = "224"
DEFAULT_OPT_DETECTION_THRESHOLD_REPEATED_LOW = "32"
DEFAULT_OPT_OUTPUT_STATS = "0"
DEFAULT_OPT_SENSOR_FILTER_MODE = "0"
DEFAULT_IR_AVERAGE_TIMING_MODE = "0"


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
        self.debug_opt_enable_stream_readings_to_serial = 0
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
                # if self.__pageflipglsink.get_property("calibration-mode"):
                self.__pageflipglsink.set_property(
                    "latest-subtitle-data",
                    json.dumps(
                        {
                            "show_now": True,
                            "text": f"\nduplicate frames {self.realtime_duplicate_counter}",
                            "duration": 500000000,
                            "special_type": "duplicate",
                        }
                    ),
                )
        elif (
            event.startswith("+o ")
            and self.debug_opt_enable_stream_readings_to_serial == 1
        ):
            # self.debug_stream.file.write(f"{event.split(" ")[1]}\n")
            raw_bytes = event.split(" ")[1].encode("iso-8859-1")
            opt_current_time = (
                (raw_bytes[9] & 0x7F)
                | ((raw_bytes[8] & 0x7F) << 7)
                | ((raw_bytes[7] & 0x7F) << 14)
                | ((raw_bytes[6] & 0x7F) << 21)
                | ((raw_bytes[5] & 0x0F) << 28)
            )
            left_sensor = ((raw_bytes[5] & 0x70) >> 4) | ((raw_bytes[4] & 0x1F) << 3)
            right_sensor = ((raw_bytes[4] & 0x60) >> 5) | ((raw_bytes[3] & 0x3F) << 2)
            duplicate_frames_in_a_row_counter = raw_bytes[2] & 0x7F

            opt_duplicate_frame_left = 1 if (raw_bytes[0] & 0x20) else 0
            opt_ignore_duplicate_left = 1 if (raw_bytes[0] & 0x10) else 0
            opt_reading_triggered_left = 1 if (raw_bytes[0] & 0x08) else 0
            opt_duplicate_frame_right = 1 if (raw_bytes[0] & 0x04) else 0
            opt_ignore_duplicate_right = 1 if (raw_bytes[0] & 0x02) else 0
            opt_reading_triggered_right = 1 if (raw_bytes[0] & 0x01) else 0

            opt_sensor_average_timing_mode_resync = 1 if (raw_bytes[1] & 0x20) else 0
            opt_sensor_frametime_average_updated = 1 if (raw_bytes[1] & 0x10) else 0
            opt_readings_active = 1 if (raw_bytes[1] & 0x08) else 0
            opt_detected_signal_start_eye = 1 if (raw_bytes[1] & 0x04) else 0
            opt_initiated_sending_ir_signal = 1 if (raw_bytes[1] & 0x02) else 0
            opt_block_signal_detection_until = 1 if (raw_bytes[1] & 0x01) else 0

            left_sent_ir = 0
            right_sent_ir = 0
            if opt_initiated_sending_ir_signal:
                if opt_detected_signal_start_eye:
                    left_sent_ir = 1
                else:
                    right_sent_ir = 1
            left_duplicate_detected = 0
            left_duplicate_ignored = 0
            if opt_reading_triggered_left:
                left_duplicate_detected = opt_duplicate_frame_left
                if left_duplicate_detected:
                    left_duplicate_ignored = opt_ignore_duplicate_left
            right_duplicate_detected = 0
            right_duplicate_ignored = 0
            if opt_reading_triggered_right:
                right_duplicate_detected = opt_duplicate_frame_right
                if right_duplicate_detected:
                    right_duplicate_ignored = opt_ignore_duplicate_right
            self.debug_stream_file.write(
                f"{opt_current_time},{left_sensor},{right_sensor},{duplicate_frames_in_a_row_counter},"
                f"{opt_block_signal_detection_until},{opt_readings_active},{opt_sensor_average_timing_mode_resync},{opt_sensor_frametime_average_updated},"
                f"{opt_reading_triggered_left},{left_duplicate_detected},{left_duplicate_ignored},{left_sent_ir},"
                f"{opt_reading_triggered_right},{right_duplicate_detected},{right_duplicate_ignored},{right_sent_ir}\n"
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
                self.main_app.window.update_idletasks()
                self.update_firmware_button.config(state="normal")
                self.close_button.config(state="normal")
                return

            self.serial_port_identifier_variable.set(pro_micro_ports[0])

            self.status_label.config(
                text=f"Updating emitter with firmware file {self.firmware_file_name}..."
            )
            self.main_app.window.update_idletasks()

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
            self.main_app.window.update_idletasks()
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
        self.emitter_firmware_version_int = 0

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

        self.setting_ir_drive_mode_frame = tkinter.Frame(top)
        self.setting_ir_drive_mode_variable = tkinter.StringVar(top)
        self.setting_ir_drive_mode_variable.set(DEFAULT_IR_DRIVE_MODE)
        self.setting_ir_drive_mode_label = tkinter.Label(
            self.setting_ir_drive_mode_frame, text="IR Drive Mode: "
        )
        self.setting_ir_drive_mode_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_drive_mode_entry = tkinter.Entry(
            self.setting_ir_drive_mode_frame,
            textvariable=self.setting_ir_drive_mode_variable,
        )
        self.setting_ir_drive_mode_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_drive_mode_tooltip = idlelib.tooltip.Hovertip(
            self.setting_ir_drive_mode_entry,
            "0=Optical, 1=PCSerial 2=Minidin3(D10), 3=RFTrigger(D10,D16,D14,D15,D21), 4=DLPLink (A1-left eye trigger optical sensor) \n(Only available from firmware version 20 onwards)\n(PCSerial only works with WibbleWobble currently, 3d player and PotPlayer both require Optical, \nMinidin3 requires soldering a connector with datapin to D10, \nRFTrigger lets you wire up a broken pair of RF glasses control board to the input pins to relay them as IR signals) \nDLPLink lets you trigger based on the DLP-Link projector light pulses using A1 the left eye trigger optical sensor (only available from firmware version 22 onwards) \n(default 0 Optical)",
            hover_delay=100,
        )
        self.setting_ir_drive_mode_frame.grid(row=row_count, column=0, sticky="w")
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
            "0=Samsung07, 1=Xpand, 2=3DVision, 3=Sharp, 4=Sony, 5=Panasonic, 6=PanasonicCustom, 7=DLPLink \n(DLPLink Only available from firmware version 19 onwards)",
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

        self.setting_ir_flip_eyes_frame = tkinter.Frame(top)
        self.setting_ir_flip_eyes_variable = tkinter.StringVar(top)
        self.setting_ir_flip_eyes_variable.set(DEFAULT_IR_FLIP_EYES)
        self.setting_ir_flip_eyes_label = tkinter.Label(
            self.setting_ir_flip_eyes_frame, text="IR Flip Eyes: "
        )
        self.setting_ir_flip_eyes_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_flip_eyes_entry = tkinter.Entry(
            self.setting_ir_flip_eyes_frame,
            textvariable=self.setting_ir_flip_eyes_variable,
        )
        self.setting_ir_flip_eyes_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_flip_eyes_tooltip = idlelib.tooltip.Hovertip(
            self.setting_ir_flip_eyes_entry,
            "(set to 1 to enable) Set this to 1 if you want to flip left and right eyes, this is useful if you need to use a high frame_delay forcing this frame to actually trigger the glasses for the next frames opposite eye\n(default 0 disabled)",
            hover_delay=100,
        )
        self.setting_ir_flip_eyes_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.setting_ir_average_timing_mode_frame = tkinter.Frame(top)
        self.setting_ir_average_timing_mode_variable = tkinter.StringVar(top)
        self.setting_ir_average_timing_mode_variable.set(DEFAULT_IR_AVERAGE_TIMING_MODE)
        self.setting_ir_average_timing_mode_label = tkinter.Label(
            self.setting_ir_average_timing_mode_frame,
            text="IR Average Timing Mode: ",
        )
        self.setting_ir_average_timing_mode_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_average_timing_mode_entry = tkinter.Entry(
            self.setting_ir_average_timing_mode_frame,
            textvariable=self.setting_ir_average_timing_mode_variable,
        )
        self.setting_ir_average_timing_mode_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_ir_average_timing_mode_tooltip = idlelib.tooltip.Hovertip(
            self.setting_ir_average_timing_mode_entry,
            "(0=Disable (default), 1=Mode 1) \nMode 1: This will turn on real-time averaging to eliminate jitter from optical and serial frame triggers. It will help if you experience flicker on custom firmware glasses or stock firmware glasses fail to initiate there shutter pattern. \nMost glasses stock firmwares appear to need a constant timer in order to synchronize with the ir signal this will help. \n Also if your display transition times are too variable this may help stablize the signal. \nIMPORTANT: Be sure to set 'Target Frametime' below for best results. \n(New better version available from firmware version 20 onwards, avoid using if your firmware is older) \n(default: 0)",
            hover_delay=100,
        )
        self.setting_ir_average_timing_mode_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_target_frametime_frame = tkinter.Frame(top)
        self.setting_target_frametime_variable = tkinter.StringVar(top)
        self.setting_target_frametime_variable.set(DEFAULT_TARGET_FRAMETIME)
        self.setting_target_frametime_label = tkinter.Label(
            self.setting_target_frametime_frame,
            text="Target Frametime: ",
        )
        self.setting_target_frametime_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_target_frametime_entry = tkinter.Entry(
            self.setting_target_frametime_frame,
            textvariable=self.setting_target_frametime_variable,
        )
        self.setting_target_frametime_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_target_frametime_tooltip = idlelib.tooltip.Hovertip(
            self.setting_target_frametime_entry,
            "(the expected time to elapse between frames in microseconds this is 1000000/(monitor refresh rate)) \nThis is used to filter out invalid average frametimes when running with 'IR Average Timing Mode'. \n (120 hz corresponds to 8333) \nIMPORTANT: If you want ot use 'IR Average Timing Mode' set this accurately for best results.  \n(default 0 - don't filter average frametimes at all)",
            hover_delay=100,
        )
        self.setting_target_frametime_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.setting_opt_block_signal_detection_delay_frame = tkinter.Frame(top)
        self.setting_opt_block_signal_detection_delay_variable = tkinter.StringVar(top)
        self.setting_opt_block_signal_detection_delay_variable.set(
            DEFAULT_OPT_BLOCK_SIGNAL_DETECTION_DELAY
        )
        self.setting_opt_block_signal_detection_delay_label = tkinter.Label(
            self.setting_opt_block_signal_detection_delay_frame,
            text="OPT Block Signal Detection Delay: ",
        )
        self.setting_opt_block_signal_detection_delay_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt_block_signal_detection_delay_entry = tkinter.Entry(
            self.setting_opt_block_signal_detection_delay_frame,
            textvariable=self.setting_opt_block_signal_detection_delay_variable,
        )
        self.setting_opt_block_signal_detection_delay_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt_block_signal_detection_delay_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt_block_signal_detection_delay_entry,
            "(in microseconds) how long to wait after a high tv signal on left or right before allowing another high tv signal \non either channel this is useful to eliminating false triggers when the tv signal is decreasing in a noisy fashion. \nthis is best set to slighly lower than the target refresh rate (about 80-90%). \n(when used in conjunction with a PWM backlit display this should be set to a value 80-90% of the PWM backlight cycle time.)",
            hover_delay=100,
        )
        self.setting_opt_block_signal_detection_delay_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt_ignore_all_duplicates_frame = tkinter.Frame(top)
        self.setting_opt_ignore_all_duplicates_variable = tkinter.StringVar(top)
        self.setting_opt_ignore_all_duplicates_variable.set(
            DEFAULT_OPT_IGNORE_ALL_DUPLICATES
        )
        self.setting_opt_ignore_all_duplicates_label = tkinter.Label(
            self.setting_opt_ignore_all_duplicates_frame,
            text="OPT Ignore All Duplicates: ",
        )
        self.setting_opt_ignore_all_duplicates_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_ignore_all_duplicates_entry = tkinter.Entry(
            self.setting_opt_ignore_all_duplicates_frame,
            textvariable=self.setting_opt_ignore_all_duplicates_variable,
        )
        self.setting_opt_ignore_all_duplicates_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_ignore_all_duplicates_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt_ignore_all_duplicates_entry,
            "(0=Disable, 1=Enable) On displays with too much jitter or PWM backlit displays you will need to set this to 1. \nThe software will not send any signal to the glasses on what might be a duplicate frame but will instead ignore it. \nThis will mean that glasses only attempt resynchronization when the alternate eye trigger is sent by the display. \n(If you are using a display without some form of BFI or a PWM backlit display it is highly recommended you enable this) \n(default 0 - off)",
            hover_delay=100,
        )
        self.setting_opt_ignore_all_duplicates_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt_min_threshold_value_to_activate_frame = tkinter.Frame(top)
        self.setting_opt_min_threshold_value_to_activate_variable = tkinter.StringVar(
            top
        )
        self.setting_opt_min_threshold_value_to_activate_variable.set(
            DEFAULT_OPT_MIN_THRESHOLD_VALUE_TO_ACTIVATE
        )
        self.setting_opt_min_threshold_value_to_activate_label = tkinter.Label(
            self.setting_opt_min_threshold_value_to_activate_frame,
            text="OPT Min Threshold Value To Activate: ",
        )
        self.setting_opt_min_threshold_value_to_activate_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt_min_threshold_value_to_activate_entry = tkinter.Entry(
            self.setting_opt_min_threshold_value_to_activate_frame,
            textvariable=self.setting_opt_min_threshold_value_to_activate_variable,
        )
        self.setting_opt_min_threshold_value_to_activate_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt_min_threshold_value_to_activate_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt_min_threshold_value_to_activate_entry,
            "(as a value between 1-255) The light intensities highest threshold value in a given threshold update cycle must exceed this value before \nthe emitter will turn on.  This setting is used to stop the emitter turning on when the TV is turned off. \nTo low a value will cause it to turn on when the screen is black and trigger sporatically. \nTo high a value will mean that it never turns on. \n(default 10)",
            hover_delay=100,
        )
        self.setting_opt_min_threshold_value_to_activate_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt_detection_threshold_high_frame = tkinter.Frame(top)
        self.setting_opt_detection_threshold_high_variable = tkinter.StringVar(top)
        self.setting_opt_detection_threshold_high_variable.set(
            DEFAULT_OPT_DETECTION_THRESHOLD_HIGH
        )
        self.setting_opt_detection_threshold_high_label = tkinter.Label(
            self.setting_opt_detection_threshold_high_frame,
            text="OPT Detection Threshold High: ",
        )
        self.setting_opt_detection_threshold_high_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_detection_threshold_high_entry = tkinter.Entry(
            self.setting_opt_detection_threshold_high_frame,
            textvariable=self.setting_opt_detection_threshold_high_variable,
        )
        self.setting_opt_detection_threshold_high_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_detection_threshold_high_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt_detection_threshold_high_entry,
            "(as a value between 1-255) the level above which an increasing light intensity is detected as the beggining of a new frame, \nsetting this lower will make the device aware of new frames earlier but also increase the likelihood of duplicate \nframe detection if the light intensity doesn't fall below this threshold before the opt_block_signal_detection_delay \ncompletes. \n(default: 128)",
            hover_delay=100,
        )
        self.setting_opt_detection_threshold_high_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.setting_opt_detection_threshold_low_frame = tkinter.Frame(top)
        self.setting_opt_detection_threshold_low_variable = tkinter.StringVar(top)
        self.setting_opt_detection_threshold_low_variable.set(
            DEFAULT_OPT_DETECTION_THRESHOLD_LOW
        )
        self.setting_opt_detection_threshold_low_label = tkinter.Label(
            self.setting_opt_detection_threshold_low_frame,
            text="OPT Detection Threshold Low: ",
        )
        self.setting_opt_detection_threshold_low_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_detection_threshold_low_entry = tkinter.Entry(
            self.setting_opt_detection_threshold_low_frame,
            textvariable=self.setting_opt_detection_threshold_low_variable,
        )
        self.setting_opt_detection_threshold_low_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_detection_threshold_low_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt_detection_threshold_low_entry,
            "(as a value between 1-255) the level below which the other eyes trigger box light intensity must be \ndetected in order for the newly rising trigger box to signal the beggining of a new frame, \nsetting this too low may make the device miss new frames from the triggering box with increasing light intensity \nif the last trigger box has not yet faded adequitly. \n(default: 32)",
            hover_delay=100,
        )
        self.setting_opt_detection_threshold_low_frame.grid(
            row=row_count, column=0, sticky="w"
        )
        row_count += 1

        self.experimental_and_debug_grid_frame = tkinter.Frame(top)
        self.experimental_and_debug_frame = util.create_toggled_frame(
            self.experimental_and_debug_grid_frame, "Experimental and Debug"
        )
        self.experimental_and_debug_grid_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        debug_row_count = 0
        self.setting_opt_enable_ignore_during_ir_frame = tkinter.Frame(
            self.experimental_and_debug_frame
        )
        self.setting_opt_enable_ignore_during_ir_variable = tkinter.StringVar(top)
        self.setting_opt_enable_ignore_during_ir_variable.set(
            DEFAULT_OPT_ENABLE_IGNORE_DURING_IR
        )
        self.setting_opt_enable_ignore_during_ir_label = tkinter.Label(
            self.setting_opt_enable_ignore_during_ir_frame,
            text="Enable Ignore Frame Start During IR*: ",
        )
        self.setting_opt_enable_ignore_during_ir_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_enable_ignore_during_ir_entry = tkinter.Entry(
            self.setting_opt_enable_ignore_during_ir_frame,
            textvariable=self.setting_opt_enable_ignore_during_ir_variable,
        )
        self.setting_opt_enable_ignore_during_ir_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_enable_ignore_during_ir_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt_enable_ignore_during_ir_entry,
            "(experimental) disable the opt sensor detection during the time when ir signals are being emitted. \nthis stops reflections of IR signals OR voltage ripples on vcc from incorrectly triggering frame start signals.",
            hover_delay=100,
        )
        self.setting_opt_enable_ignore_during_ir_frame.grid(
            row=debug_row_count, column=0, sticky="w"
        )
        debug_row_count += 1

        self.setting_opt_enable_duplicate_realtime_reporting_frame = tkinter.Frame(
            self.experimental_and_debug_frame
        )
        self.setting_opt_enable_duplicate_realtime_reporting_variable = (
            tkinter.StringVar(top)
        )
        self.setting_opt_enable_duplicate_realtime_reporting_variable.set(
            DEFAULT_OPT_ENABLE_DUPLICATE_REALTIME_REPORTING
        )
        self.setting_opt_enable_duplicate_realtime_reporting_label = tkinter.Label(
            self.setting_opt_enable_duplicate_realtime_reporting_frame,
            text="Enable Duplicate Realtime Reporting: ",
        )
        self.setting_opt_enable_duplicate_realtime_reporting_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt_enable_duplicate_realtime_reporting_entry = tkinter.Entry(
            self.setting_opt_enable_duplicate_realtime_reporting_frame,
            textvariable=self.setting_opt_enable_duplicate_realtime_reporting_variable,
        )
        self.setting_opt_enable_duplicate_realtime_reporting_entry.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt_enable_duplicate_realtime_reporting_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt_enable_duplicate_realtime_reporting_entry,
            "When enabled (set to 1) the emitter will send a signal to the PC every time it detects a duplicate frame. This can be useful during calibration to see if the emitter thinks the pc is sending duplicate frames. \n(This will not work unless you have a display with some form of BFI and have tuned 'block signal detection delay appropriately'. \nIf you are relying on 'ignore all duplicates' this will not work)",
            hover_delay=100,
        )
        self.setting_opt_enable_duplicate_realtime_reporting_frame.grid(
            row=debug_row_count, column=0, sticky="w"
        )
        debug_row_count += 1

        self.setting_opt_output_stats_frame = tkinter.Frame(
            self.experimental_and_debug_frame
        )
        self.setting_opt_output_stats_variable = tkinter.StringVar(top)
        self.setting_opt_output_stats_variable.set(DEFAULT_OPT_OUTPUT_STATS)
        self.setting_opt_output_stats_label = tkinter.Label(
            self.setting_opt_output_stats_frame, text="OPT Output Stats: "
        )
        self.setting_opt_output_stats_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_output_stats_entry = tkinter.Entry(
            self.setting_opt_output_stats_frame,
            textvariable=self.setting_opt_output_stats_variable,
        )
        self.setting_opt_output_stats_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_output_stats_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt_output_stats_entry,
            '(0=Disable, 1=Enable) output statistics (if built with OPT_ENABLE_STATS) relating to how the opt module is processing all lines start with \n"+stats " followed by specific statistics. Turn this off when not experimenting as it may degrade timing accuracy when serial communication occurs',
            hover_delay=100,
        )
        self.setting_opt_output_stats_frame.grid(
            row=debug_row_count, column=0, sticky="w"
        )
        debug_row_count += 1

        self.setting_opt_sensor_filter_mode_frame = tkinter.Frame(
            self.experimental_and_debug_frame
        )
        self.setting_opt_sensor_filter_mode_variable = tkinter.StringVar(top)
        self.setting_opt_sensor_filter_mode_variable.set(DEFAULT_OPT_SENSOR_FILTER_MODE)
        self.setting_opt_sensor_filter_mode_label = tkinter.Label(
            self.setting_opt_sensor_filter_mode_frame,
            text="OPT Sensor Filter Mode: ",
        )
        self.setting_opt_sensor_filter_mode_label.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_sensor_filter_mode_entry = tkinter.Entry(
            self.setting_opt_sensor_filter_mode_frame,
            textvariable=self.setting_opt_sensor_filter_mode_variable,
        )
        self.setting_opt_sensor_filter_mode_entry.pack(padx=5, side=tkinter.LEFT)
        self.setting_opt_sensor_filter_mode_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt_sensor_filter_mode_entry,
            "(0=Disable (default), 1=Mode 1) (Mode 1: check that the last three readings are trending in the same direction) \n(this may be useful in helping to eliminate the effect of noise caused by IR leds or low signal to noise from the optical sensor.) \n(Only available from firmware version 13 onwards)",
            hover_delay=100,
        )
        self.setting_opt_sensor_filter_mode_frame.grid(
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

        self.setting_opt_debug_frame = tkinter.Frame(self.experimental_and_debug_frame)
        self.setting_opt_enable_stream_readings_to_serial_toggle_button = (
            tkinter.Button(
                self.setting_opt_debug_frame,
                text="Toggle OPT Enable Stream Readings To Serial",
                command=self.click_opt_enable_stream_readings_to_serial_toggle,
            )
        )
        self.setting_opt_enable_stream_readings_to_serial_toggle_button.config(
            state="disabled"
        )
        self.setting_opt_enable_stream_readings_to_serial_toggle_button.pack(
            padx=5, side=tkinter.LEFT
        )
        self.setting_opt_enable_stream_readings_to_serial_toggle_button_tooltip = idlelib.tooltip.Hovertip(
            self.setting_opt_enable_stream_readings_to_serial_toggle_button,
            "toggles logging of opt sensor readings to a file for analysis and debugging (if built with OPT_ENABLE_STREAM_READINGS_TO_SERIAL)",
            hover_delay=100,
        )
        self.setting_opt_debug_frame.grid(row=debug_row_count, column=0, sticky="w")
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
                self.setting_opt_enable_stream_readings_to_serial_toggle_button.config(
                    state="normal"
                )
            else:
                self.setting_opt_enable_stream_readings_to_serial_toggle_button.config(
                    state="disabled"
                )
            self.setting_glasses_mode_button.config(state="normal")
            self.update_emitter_firmware_button.config(state="disabled")
            self.update_button.config(state="normal")
            self.serial_port_connect_button.config(state="disabled")
            self.serial_port_disconnect_button.config(state="normal")
            self.save_settings_button.config(state="normal")
        else:
            self.setting_opt_enable_stream_readings_to_serial_toggle_button.config(
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

    def get_settings_dictionary(self):
        return {
            "ir_drive_mode": self.setting_ir_drive_mode_variable.get(),
            "ir_protocol": self.setting_ir_protocol_variable.get(),
            "ir_frame_delay": self.setting_ir_frame_delay_variable.get(),
            "ir_frame_duration": self.setting_ir_frame_duration_variable.get(),
            "ir_signal_spacing": self.setting_ir_signal_spacing_variable.get(),
            "ir_flip_eyes": self.setting_ir_flip_eyes_variable.get(),
            "ir_average_timing_mode": self.setting_ir_average_timing_mode_variable.get(),
            "target_frametime": self.setting_target_frametime_variable.get(),
            "opt_block_signal_detection_delay": self.setting_opt_block_signal_detection_delay_variable.get(),
            "opt_ignore_all_duplicates": self.setting_opt_ignore_all_duplicates_variable.get(),
            "opt_sensor_filter_mode_variable": self.setting_opt_sensor_filter_mode_variable.get(),
            "opt_min_threshold_value_to_activate": self.setting_opt_min_threshold_value_to_activate_variable.get(),
            "opt_detection_threshold_high": self.setting_opt_detection_threshold_high_variable.get(),
            "opt_detection_threshold_low": self.setting_opt_detection_threshold_low_variable.get(),
            "opt_enable_ignore_during_ir": self.setting_opt_enable_ignore_during_ir_variable.get(),
            "opt_enable_duplicate_realtime_reporting": self.setting_opt_enable_duplicate_realtime_reporting_variable.get(),
            "opt_output_stats": self.setting_opt_output_stats_variable.get(),
        }

    def update_settings_from_serial(self):
        if self.main_app.emitter_serial:
            response = self.main_app.emitter_serial.line_reader.command("0")[0].split(
                " "
            )
            print(response)
            if response[0] == "parameters":
                parameters = response[1].split(",")
                if int(parameters[0]) < 10:
                    parameters = [3] + parameters
                emitter_firmware_version = parameters[0]
                self.emitter_firmware_version_int = int(emitter_firmware_version)
                # remove what was param_12 or setting_pwm_backlight_frequency_variable
                if (
                    self.emitter_firmware_version_int > 14
                    and self.emitter_firmware_version_int < 21
                ):
                    parameters = parameters[0:11] + parameters[12:]
                if self.emitter_firmware_version_int < 14:
                    (
                        ir_protocol,
                        ir_frame_delay,
                        ir_frame_duration,
                        ir_signal_spacing,
                        opt_block_signal_detection_delay,
                        opt_min_threshold_value_to_activate,
                        opt_detection_threshold_high,
                        opt_detection_threshold_repeated_high,  # @UnusedVariable
                        opt_detection_threshold_repeated_low,  # @UnusedVariable
                        opt_enable_ignore_during_ir,
                        opt_enable_duplicate_realtime_reporting,
                        opt_output_stats,
                        opt_enable_frequency_analysis_based_duplicate_frame_detection,  # @UnusedVariable
                    ) = parameters[1:14]

                    self.setting_emitter_firmware_version_variable.set(
                        emitter_firmware_version
                    )
                    self.setting_ir_protocol_variable.set(ir_protocol)
                    self.setting_ir_frame_delay_variable.set(ir_frame_delay)
                    self.setting_ir_frame_duration_variable.set(ir_frame_duration)
                    self.setting_ir_signal_spacing_variable.set(ir_signal_spacing)
                    self.setting_opt_block_signal_detection_delay_variable.set(
                        opt_block_signal_detection_delay
                    )
                    self.setting_opt_min_threshold_value_to_activate_variable.set(
                        opt_min_threshold_value_to_activate
                    )
                    self.setting_opt_detection_threshold_high_variable.set(
                        opt_detection_threshold_high
                    )
                    self.setting_opt_enable_ignore_during_ir_variable.set(
                        opt_enable_ignore_during_ir
                    )
                    self.setting_opt_enable_duplicate_realtime_reporting_variable.set(
                        opt_enable_duplicate_realtime_reporting
                    )
                    self.setting_opt_output_stats_variable.set(opt_output_stats)
                    if self.emitter_firmware_version_int >= 11:
                        self.setting_opt_enable_stream_readings_to_serial_toggle_button.config(
                            state="normal"
                        )
                    else:
                        self.setting_opt_enable_stream_readings_to_serial_toggle_button.config(
                            state="disabled"
                        )
                    if self.emitter_firmware_version_int >= 12:
                        self.setting_opt_ignore_all_duplicates_variable.set(
                            parameters[15]
                        )
                        self.setting_opt_ignore_all_duplicates_entry.config(
                            state="normal"
                        )
                    else:
                        self.setting_opt_ignore_all_duplicates_variable.set(
                            DEFAULT_OPT_IGNORE_ALL_DUPLICATES
                        )
                        self.setting_opt_ignore_all_duplicates_entry.config(
                            state="disabled"
                        )
                    if self.emitter_firmware_version_int >= 13:
                        self.setting_opt_sensor_filter_mode_variable.set(parameters[16])
                        self.setting_opt_sensor_filter_mode_entry.config(state="normal")
                    else:
                        self.setting_opt_sensor_filter_mode_variable.set(
                            DEFAULT_OPT_SENSOR_FILTER_MODE
                        )
                        self.setting_opt_sensor_filter_mode_entry.config(
                            state="disabled"
                        )
                    self.setting_ir_flip_eyes_variable.set(DEFAULT_IR_FLIP_EYES)
                    self.setting_ir_flip_eyes_entry.config(state="disabled")
                    self.setting_target_frametime_entry.config(state="disabled")
                else:
                    (
                        ir_protocol,
                        ir_frame_delay,
                        ir_frame_duration,
                        ir_signal_spacing,
                        opt_block_signal_detection_delay,
                        opt_min_threshold_value_to_activate,
                        opt_detection_threshold_high,
                        opt_enable_ignore_during_ir,
                        opt_enable_duplicate_realtime_reporting,
                        opt_output_stats,
                        opt_ignore_all_duplicates,
                        opt_sensor_filter_mode,
                        ir_flip_eyes,
                    ) = parameters[1:14]

                    self.setting_emitter_firmware_version_variable.set(
                        emitter_firmware_version
                    )
                    self.setting_ir_protocol_variable.set(ir_protocol)
                    self.setting_ir_frame_delay_variable.set(ir_frame_delay)
                    self.setting_ir_frame_duration_variable.set(ir_frame_duration)
                    self.setting_ir_signal_spacing_variable.set(ir_signal_spacing)
                    self.setting_opt_block_signal_detection_delay_variable.set(
                        opt_block_signal_detection_delay
                    )
                    self.setting_opt_min_threshold_value_to_activate_variable.set(
                        opt_min_threshold_value_to_activate
                    )
                    self.setting_opt_detection_threshold_high_variable.set(
                        opt_detection_threshold_high
                    )
                    self.setting_opt_enable_ignore_during_ir_variable.set(
                        opt_enable_ignore_during_ir
                    )
                    self.setting_opt_enable_duplicate_realtime_reporting_variable.set(
                        opt_enable_duplicate_realtime_reporting
                    )
                    self.setting_opt_output_stats_variable.set(opt_output_stats)
                    self.setting_opt_ignore_all_duplicates_variable.set(
                        opt_ignore_all_duplicates
                    )
                    self.setting_opt_sensor_filter_mode_variable.set(
                        opt_sensor_filter_mode
                    )
                    self.setting_ir_flip_eyes_variable.set(ir_flip_eyes)

                    self.setting_opt_enable_stream_readings_to_serial_toggle_button.config(
                        state="normal"
                    )
                    self.setting_opt_ignore_all_duplicates_entry.config(state="normal")
                    self.setting_opt_sensor_filter_mode_entry.config(state="normal")
                    self.setting_ir_flip_eyes_entry.config(state="normal")
                    if self.emitter_firmware_version_int >= 16:
                        self.setting_opt_detection_threshold_low_variable.set(
                            parameters[14]
                        )
                        self.setting_opt_detection_threshold_low_entry.config(
                            state="normal"
                        )
                    else:
                        self.setting_opt_detection_threshold_low_variable.set(
                            DEFAULT_OPT_DETECTION_THRESHOLD_LOW
                        )
                        self.setting_opt_detection_threshold_low_entry.config(
                            state="disabled"
                        )
                    if self.emitter_firmware_version_int >= 17:
                        self.setting_ir_average_timing_mode_variable.set(parameters[15])
                        self.setting_ir_average_timing_mode_entry.config(state="normal")
                    else:
                        self.setting_ir_average_timing_mode_variable.set(
                            DEFAULT_OPT_DETECTION_THRESHOLD_LOW
                        )
                        self.setting_ir_average_timing_mode_entry.config(
                            state="disabled"
                        )
                    if self.emitter_firmware_version_int >= 18:
                        self.setting_target_frametime_variable.set(parameters[16])
                        self.setting_target_frametime_entry.config(state="normal")
                    else:
                        self.setting_target_frametime_variable.set(
                            DEFAULT_TARGET_FRAMETIME
                        )
                        self.setting_target_frametime_entry.config(state="disabled")
                    if self.emitter_firmware_version_int >= 20:
                        self.setting_ir_drive_mode_variable.set(parameters[17])
                        self.setting_ir_drive_mode_entry.config(state="normal")
                    else:
                        self.setting_ir_drive_mode_variable.set(DEFAULT_IR_DRIVE_MODE)
                        self.setting_ir_drive_mode_entry.config(state="disabled")

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
        self.setting_opt_enable_stream_readings_to_serial_toggle_button.config(
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
            if self.emitter_firmware_version_int < 14:
                command = (
                    f"0,"
                    f"{self.setting_ir_protocol_variable.get()},"
                    f"{self.setting_ir_frame_delay_variable.get()},"
                    f"{self.setting_ir_frame_duration_variable.get()},"
                    f"{self.setting_ir_signal_spacing_variable.get()},"
                    f"{self.setting_opt_block_signal_detection_delay_variable.get()},"
                    f"{self.setting_opt_min_threshold_value_to_activate_variable.get()},"
                    f"{self.setting_opt_detection_threshold_high_variable.get()},"
                    f"{DEFAULT_OPT_DETECTION_THRESHOLD_REPEATED_HIGH},"
                    f"{DEFAULT_OPT_DETECTION_THRESHOLD_REPEATED_LOW},"
                    f"{self.setting_opt_enable_ignore_during_ir_variable.get()},"
                    f"{self.setting_opt_enable_duplicate_realtime_reporting_variable.get()},"
                    f"{self.setting_opt_output_stats_variable.get()},"
                    f"{DEFAULT_OPT_ENABLE_FREQUENCY_ANALYSIS_BASED_DUPLICATE_FRAME_DETECTION}"
                )
                if self.emitter_firmware_version_int >= 10:
                    command += f",{DEFAULT_OPT_BLOCK_N_SUBSEQUENT_DUPLICATES}"
                if self.emitter_firmware_version_int >= 12:
                    command += (
                        f",{self.setting_opt_ignore_all_duplicates_variable.get()}"
                    )
                if self.emitter_firmware_version_int >= 13:
                    command += f",{self.setting_opt_sensor_filter_mode_variable.get()}"
            else:
                command = (
                    f"0,"
                    f"{self.setting_ir_protocol_variable.get()},"
                    f"{self.setting_ir_frame_delay_variable.get()},"
                    f"{self.setting_ir_frame_duration_variable.get()},"
                    f"{self.setting_ir_signal_spacing_variable.get()},"
                    f"{self.setting_opt_block_signal_detection_delay_variable.get()},"
                    f"{self.setting_opt_min_threshold_value_to_activate_variable.get()},"
                    f"{self.setting_opt_detection_threshold_high_variable.get()},"
                    f"{self.setting_opt_enable_ignore_during_ir_variable.get()},"
                    f"{self.setting_opt_enable_duplicate_realtime_reporting_variable.get()},"
                    f"{self.setting_opt_output_stats_variable.get()},"
                )
                if self.emitter_firmware_version_int >= 21:
                    pass
                elif self.emitter_firmware_version_int >= 18:
                    command += f"0,"  # was setting_pwm_backlight_frequency_variable
                else:
                    command += f"{DEFAULT_OPT_BLOCK_N_SUBSEQUENT_DUPLICATES},"
                command += (
                    f"{self.setting_opt_ignore_all_duplicates_variable.get()},"
                    f"{self.setting_opt_sensor_filter_mode_variable.get()},"
                    f"{self.setting_ir_flip_eyes_variable.get()}"
                )
                if self.emitter_firmware_version_int >= 16:
                    command += (
                        f",{self.setting_opt_detection_threshold_low_variable.get()}"
                    )
                if self.emitter_firmware_version_int >= 17:
                    command += f",{self.setting_ir_average_timing_mode_variable.get()}"
                if self.emitter_firmware_version_int >= 18:
                    command += f",{self.setting_target_frametime_variable.get()}"
                if self.emitter_firmware_version_int >= 20:
                    command += f",{self.setting_ir_drive_mode_variable.get()}"

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
            filetypes=[("Emitter Settings File", "*.emitter_settings.json")],
            defaultextension=".emitter_settings.json",
        )
        if file_name:
            f = open(file_name, "w")
            json.dump(
                self.get_settings_dictionary(),
                f,
                indent=2,
            )
            f.close()

    def click_load_visisble_settings_from_disk(self):
        file_name = tkinter.filedialog.askopenfilename(
            title="Load Emitter Settings from Disk",
            initialdir=os.path.join(self.main_app.base_path, "settings"),
            filetypes=[("Emitter Settings File", "*.emitter_settings.json")],
        )
        if file_name:
            f = open(file_name, "r")
            settings = json.load(f)
            f.close()
            self.setting_ir_drive_mode_variable.set(
                settings.get("ir_drive_mode", DEFAULT_IR_DRIVE_MODE)
            )
            self.setting_ir_protocol_variable.set(
                settings.get("ir_protocol", DEFAULT_IR_PROTOCOL)
            )
            self.setting_ir_frame_delay_variable.set(
                settings.get("ir_frame_delay", DEFAULT_IR_FRAME_DELAY)
            )
            self.setting_ir_frame_duration_variable.set(
                settings.get("ir_frame_duration", DEFAULT_IR_FRAME_DURATION)
            )
            self.setting_ir_signal_spacing_variable.set(
                settings.get("ir_signal_spacing", DEFAULT_IR_SIGNAL_SPACING)
            )
            self.setting_ir_flip_eyes_variable.set(
                settings.get(
                    "ir_flip_eyes",
                    DEFAULT_IR_FLIP_EYES,
                )
            )
            self.setting_ir_average_timing_mode_variable.set(
                settings.get(
                    "ir_average_timing_mode",
                    DEFAULT_IR_AVERAGE_TIMING_MODE,
                )
            )
            self.setting_target_frametime_variable.set(
                settings.get(
                    "target_frametime",
                    DEFAULT_TARGET_FRAMETIME,
                )
            )
            self.setting_opt_block_signal_detection_delay_variable.set(
                settings.get(
                    "opt_block_signal_detection_delay",
                    settings.get(
                        "opt101_block_signal_detection_delay",
                        DEFAULT_OPT_BLOCK_SIGNAL_DETECTION_DELAY,
                    ),
                )
            )
            self.setting_opt_min_threshold_value_to_activate_variable.set(
                settings.get(
                    "opt_min_threshold_value_to_activate",
                    settings.get(
                        "opt101_min_threshold_value_to_activate",
                        DEFAULT_OPT_MIN_THRESHOLD_VALUE_TO_ACTIVATE,
                    ),
                )
            )
            self.setting_opt_detection_threshold_high_variable.set(
                settings.get(
                    "opt_detection_threshold_high",
                    settings.get(
                        "opt101_detection_threshold",
                        DEFAULT_OPT_DETECTION_THRESHOLD_HIGH,
                    ),
                )
            )
            self.setting_opt_detection_threshold_low_variable.set(
                settings.get(
                    "opt_detection_threshold_low", DEFAULT_OPT_DETECTION_THRESHOLD_LOW
                )
            )
            self.setting_opt_enable_ignore_during_ir_variable.set(
                settings.get(
                    "opt_enable_ignore_during_ir",
                    settings.get(
                        "opt101_enable_ignore_during_ir",
                        DEFAULT_OPT_ENABLE_IGNORE_DURING_IR,
                    ),
                )
            )
            self.setting_opt_enable_duplicate_realtime_reporting_variable.set(
                settings.get(
                    "opt_enable_duplicate_realtime_reporting",
                    settings.get(
                        "opt101_enable_duplicate_realtime_reporting",
                        DEFAULT_OPT_ENABLE_DUPLICATE_REALTIME_REPORTING,
                    ),
                )
            )
            self.setting_opt_output_stats_variable.set(
                settings.get("opt_output_stats", DEFAULT_OPT_OUTPUT_STATS)
            )
            self.setting_opt_ignore_all_duplicates_variable.set(
                settings.get(
                    "opt_ignore_all_duplicates",
                    settings.get(
                        "opt101_ignore_all_duplicates",
                        DEFAULT_OPT_IGNORE_ALL_DUPLICATES,
                    ),
                )
            )
            self.setting_opt_sensor_filter_mode_variable.set(
                settings.get(
                    "opt_sensor_filter_mode",
                    settings.get(
                        "opt101_sensor_filter_mode",
                        DEFAULT_OPT_SENSOR_FILTER_MODE,
                    ),
                )
            )

    def click_set_glasses_mode(self):
        if self.main_app.emitter_serial:
            command = f"7,{self.setting_glasses_mode_variable.get()}"
            print(command)
            self.main_app.emitter_serial.line_reader.command(command)

    def click_opt_enable_stream_readings_to_serial_toggle(self):
        if self.main_app.emitter_serial:
            new_value = (
                self.main_app.emitter_serial.line_reader.debug_opt_enable_stream_readings_to_serial
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
                        f'{datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")}_debug_opt_stream_readings.csv',
                    ),
                    "wt",
                )
                self.main_app.emitter_serial.line_reader.debug_stream_file.write(
                    "opt_current_time,left_sensor,right_sensor,duplicate_frames_in_a_row_counter,"
                    "opt_block_signal_detection_until,opt_readings_active,opt_sensor_average_timing_mode_resync,opt_sensor_frametime_average_updated,"
                    "opt_reading_triggered_left,left_duplicate_detected,left_duplicate_ignored,left_sent_ir,"
                    "opt_reading_triggered_right,right_duplicate_detected,right_duplicate_ignored,right_sent_ir\n"
                )

            self.main_app.emitter_serial.line_reader.debug_opt_enable_stream_readings_to_serial = (
                new_value
            )

            if new_value == 0:
                self.main_app.emitter_serial.line_reader.debug_stream_file.write(
                    f"\n\n"
                )
                for (
                    setting_name,
                    setting_value,
                ) in self.get_settings_dictionary().items():
                    self.main_app.emitter_serial.line_reader.debug_stream_file.write(
                        f"\n\n{setting_name},{setting_value}\n"
                    )
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
