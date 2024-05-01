import os
import functools
import datetime
import json
import re
import tkinter  # @UnusedImport
import tkinter.filedialog
import idlelib.tooltip

import util

# Video Defaults
DEFAULT_SUBTITLE_FONT = "MS Gothic" if os.name == "nt" else "Noto Sans CJK JP"
DEFAULT_SUBTITLE_SIZE = "60"
DEFAULT_SUBTITLE_DEPTH = "20"
DEFAULT_SUBTITLE_VERTICAL_OFFSET = "150"
DEFAULT_SUBTITLE_OFFSET = "0"
DEFAULT_FRAME_PACKING = "side-by-side-half"
DEFAULT_RIGHT_EYE = "right"
DEFAULT_GENERATE_DOT_GRAPH_FILE = False
DEFAULT_AUDIO_FORMAT_FILTER = ""


class StartVideoDialog:

    LOAD_VIDEO_PROFILE_FROM_HISTORY_OPTION = "Load Video Profile From History"
    LOAD_VIDEO_DEFAULTS_HISTORY_OPTION = "Load Defaults"
    LOAD_VIDEO_DEFAULTS_HISTORY_SAVE_NAME = "Defaults"
    VIDEO_HISTORY_MAX_SIZE = 70

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
        self.video_file_clear_button = tkinter.Button(
            self.video_file_frame, text="Clear", command=self.clear_video_file
        )
        self.video_file_clear_button.pack(padx=5, side=tkinter.LEFT)
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
        self.subtitle_file_clear_button = tkinter.Button(
            self.subtitle_file_frame, text="Clear", command=self.clear_subtitle_file
        )
        self.subtitle_file_clear_button.pack(padx=5, side=tkinter.LEFT)
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

        self.generate_dot_graph_file_variable = tkinter.BooleanVar(parent)
        self.generate_dot_graph_file_variable.set(DEFAULT_GENERATE_DOT_GRAPH_FILE)
        self.generate_dot_graph_file_frame = tkinter.Frame(top)
        self.generate_dot_graph_file_label = tkinter.Label(
            self.generate_dot_graph_file_frame, text="Generate Dot Graph File: "
        )
        self.generate_dot_graph_file_label.pack(padx=5, side=tkinter.LEFT)
        self.generate_dot_graph_file_check_button = tkinter.Checkbutton(
            self.generate_dot_graph_file_frame,
            variable=self.generate_dot_graph_file_variable,
        )
        self.generate_dot_graph_file_check_button.pack(padx=5, side=tkinter.LEFT)
        # self.generate_dot_graph_file_frame.pack()
        self.generate_dot_graph_file_tooltip = idlelib.tooltip.Hovertip(
            self.generate_dot_graph_file_frame,
            "Generate a gstreamer dot graph file showing the gstreamer pipeline flow and elements. The file will be saved in the dot-graph folder. The graph can be viewed by copying the text into the text box at https://graphview.net/ and clicking view.",
            hover_delay=100,
        )
        self.generate_dot_graph_file_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.audio_format_filter_frame = tkinter.Frame(top)
        self.audio_format_filter_variable = tkinter.StringVar(top)
        self.audio_format_filter_variable.set(DEFAULT_AUDIO_FORMAT_FILTER)
        self.audio_format_filter_label = tkinter.Label(
            self.audio_format_filter_frame, text="Audio Format Filter: "
        )
        self.audio_format_filter_label.pack(padx=5, side=tkinter.LEFT)
        self.audio_format_filter_entry = tkinter.Entry(
            self.audio_format_filter_frame,
            textvariable=self.audio_format_filter_variable,
        )
        self.audio_format_filter_entry.pack(padx=5, side=tkinter.LEFT)
        # self.audio_format_filter_frame.pack()
        self.audio_format_filter_tooltip = idlelib.tooltip.Hovertip(
            self.audio_format_filter_frame,
            "(leave this blank unless you are experiencing audio issues) \nAdds an audio format filter to the gstreamer pipeline at the beginning of the 'playsink' element after 'uridecodebin3' element \nIt attempts to force 'uridecodebin3' to either decode to a specific format or preserve a specific digital audio format for passthrough. \nValid values take the form of gstreamer caps filter strings like 'audio/x-dts', 'audio/x-ac3', 'audio/mpeg', 'audio/x-raw' \nOne can also include format, channel, layout, and rate information like 'audio/x-raw,format=S16LE,channels=2,layout=interleaved,rate=48000'",
            hover_delay=100,
        )
        self.audio_format_filter_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.action_button_frame_1 = tkinter.Frame(top)
        self.open_button = tkinter.Button(
            self.action_button_frame_1,
            text="Just Open (No History)",
            command=functools.partial(self.open_video, False, False),
        )
        self.open_button.pack(padx=5, side=tkinter.LEFT)

        self.open_button_new_history = tkinter.Button(
            self.action_button_frame_1,
            text="Open and Save (New History Entry)",
            command=functools.partial(self.open_video, True, False),
        )
        self.open_button_new_history.pack(padx=5, side=tkinter.LEFT)

        self.open_button_update_history = tkinter.Button(
            self.action_button_frame_1,
            text="Open and Update (Existing History Entry)",
            command=functools.partial(self.open_video, False, True),
        )
        self.open_button_update_history.pack(padx=5, side=tkinter.LEFT)

        self.save_defaults_button = tkinter.Button(
            self.action_button_frame_1, text="Save Defaults", command=self.save_defaults
        )
        self.save_defaults_button.pack(padx=5, side=tkinter.LEFT)
        self.action_button_frame_1.grid(row=row_count, column=0)
        row_count += 1

        if self.video_history_default_index is not None:
            self.__load_video_profile_from_history_idx(self.video_history_default_index)

    def __update_right_eye_options(self, *args, **kwargs):
        frame_packing = self.frame_packing_variable.get()
        if frame_packing.startswith("side-by-side"):
            new_menu_options = ["right", "left"]
            default_selection = 0
        elif frame_packing.startswith("over-and-under"):
            new_menu_options = ["top", "bottom"]
            default_selection = 1
        else:
            return
        menu = self.right_eye_option_menu["menu"]
        menu.delete(0, "end")
        for menu_option in new_menu_options:
            menu.add_command(
                label=menu_option,
                command=util.setit(self.right_eye_variable, menu_option),
            )
        new_selection = new_menu_options[default_selection]
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
                    command=util.setit(self.video_history_clicked, menu_option),
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
            self.subtitle_file_name = selected_video_history.get(
                "subtitle_file_name", ""
            )
        self.subtitle_file_location_label.config(text=self.subtitle_file_name)
        self.subtitle_font_variable.set(
            selected_video_history.get("subtitle_font", DEFAULT_SUBTITLE_FONT)
        )
        self.subtitle_size_variable.set(
            selected_video_history.get("subtitle_size", DEFAULT_SUBTITLE_SIZE)
        )
        self.subtitle_depth_variable.set(
            selected_video_history.get("subtitle_depth", DEFAULT_SUBTITLE_DEPTH)
        )
        self.subtitle_vertical_offset_variable.set(
            selected_video_history.get(
                "subtitle_vertical_offset", DEFAULT_SUBTITLE_VERTICAL_OFFSET
            )
        )
        self.subtitle_offset_variable.set(
            selected_video_history.get("subtitle_offset", DEFAULT_SUBTITLE_OFFSET)
        )
        self.frame_packing_variable.set(
            selected_video_history.get("frame_packing", DEFAULT_FRAME_PACKING)
        )
        self.__update_right_eye_options(
            select=selected_video_history.get("right_eye", DEFAULT_RIGHT_EYE)
        )
        # self.right_eye_variable.set(selected_video_history["right_eye"])
        self.generate_dot_graph_file_variable.set(
            selected_video_history.get(
                "generate_dot_graph_file", DEFAULT_GENERATE_DOT_GRAPH_FILE
            )
        )
        self.audio_format_filter_variable.set(
            selected_video_history.get(
                "audio_format_filter", DEFAULT_AUDIO_FORMAT_FILTER
            )
        )

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

    def clear_video_file(self):
        self.video_file_name = ""
        self.video_file_location_label.config(text=self.video_file_name)

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

    def clear_subtitle_file(self):
        self.subtitle_file_name = ""
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
            "generate_dot_graph_file": self.generate_dot_graph_file_variable.get(),
            "audio_format_filter": self.audio_format_filter_variable.get(),
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

    def open_video(self, save_new_history, update_existing_history):
        if (
            not self.video_file_name
            or self.video_file_name
            == StartVideoDialog.LOAD_VIDEO_DEFAULTS_HISTORY_SAVE_NAME
        ):
            return

        new_video_history_entry = self.__build_video_history_entry()
        new_video_history_entry["video_file_name"] = self.video_file_name
        save_history = save_new_history
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
            elif update_existing_history:
                selected_video_history.update(new_video_history_entry)
                f = open(self.history_file_path, "w")
                json.dump(self.video_history, f, indent=2)
                f.close()
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
            return "side-by-side-half"
        if re.match(".*[_\-\.](((full)|(f))[_\-\.]?)sbs[_\-\.].*", filename, re.I):
            return "side-by-side-full"
        if re.match(
            ".*[_\-\.](((half)|(h))[_\-\.]?)((ou)|(tab))[_\-\.].*", filename, re.I
        ):
            return "over-and-under-half"
        if re.match(
            ".*[_\-\.](((full)|(f))[_\-\.]?)((ou)|(tab))[_\-\.].*", filename, re.I
        ):
            return "over-and-under-full"
        partial_match = False
        half_or_not = True
        if re.match(".*[_\-\.]((full)|f)[_\-\.].*", filename):
            half_or_not = False
            partial_match = True
        if re.match(".*[_\-\.]((half)|h)[_\-\.].*", filename):
            half_or_not = True
            partial_match = True
        side_by_side_or_over_and_under = True
        if re.match(
            ".*[_\-\.]((ou)|(over[_\-\.]?(and)?[_\-\.]?under)|(tab)|(top[_\-\.]?(and)?[_\-\.]?bottom))[_\-\.].*",
            filename,
        ):
            side_by_side_or_over_and_under = False
            partial_match = True
        if re.match(
            ".*[_\-\.]((sbs)|(side[_\-\.]?(by)?[_\-\.]?side))[_\-\.].*", filename
        ):
            side_by_side_or_over_and_under = True
            partial_match = True
        if partial_match:
            return f"{'side-by-side' if side_by_side_or_over_and_under else 'over-and-under'}-{'half' if half_or_not else 'full'}"
        else:
            return StartVideoDialog.get_video_history_default_settings()[
                "frame_packing"
            ]

    @staticmethod
    def get_video_history_default_settings():
        video_defaults = {
            "video_file_name": "Defaults",
            "subtitle_file_name": "",
            "subtitle_font": (DEFAULT_SUBTITLE_FONT),
            "subtitle_size": DEFAULT_SUBTITLE_SIZE,
            "subtitle_depth": DEFAULT_SUBTITLE_DEPTH,
            "subtitle_vertical_offset": DEFAULT_SUBTITLE_VERTICAL_OFFSET,
            "subtitle_offset": DEFAULT_SUBTITLE_OFFSET,
            "frame_packing": DEFAULT_FRAME_PACKING,
            "right_eye": DEFAULT_RIGHT_EYE,
            "generate_dot_graph_file": DEFAULT_GENERATE_DOT_GRAPH_FILE,
            "audio_format_filter": DEFAULT_AUDIO_FORMAT_FILTER,
        }
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
                    video_defaults.update(vh)
        return video_defaults
