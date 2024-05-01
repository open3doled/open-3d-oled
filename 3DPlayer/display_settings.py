import os
import json
import tkinter  # @UnusedImport
import tkinter.filedialog
import idlelib.tooltip

DECODER_PREFERENCE_DEFAULT = "default (GStreamers first choice)"
DECODER_PREFERENCE_NVCODEC = "nvcodec (NVidia Codec)"
DECODER_PREFERENCE_VAAPI = "vaapi (Video Acceleration API)"
DECODER_PREFERENCE_MSDK = "msdk (Intel Media SDK)"
DECODER_PREFERENCE_D3D11 = "d3d11 (Direct 3D 11)"
DECODER_PREFERENCE_SOFTWARE = "software (No HW Acceleration)"

# Display Setting Defaults
DEFAULT_TARGET_FRAMERATE = "0"
DEFAULT_DISPLAY_RESOLUTION = "1920x1080"
DEFAULT_DISPLAY_ZOOM_FACTOR = "100"
DEFAULT_DISPLAY_SIZE = "55"
DEFAULT_DECODER_PREFERENCE = DECODER_PREFERENCE_DEFAULT
DEFAULT_WHITEBOX_BRIGHTNESS = "255"
DEFAULT_WHITEBOX_CORNER_POSITION = "top_left"
DEFAULT_WHITEBOX_VERTICAL_POSITION = "0"
DEFAULT_WHITEBOX_HORIZONTAL_POSITION = "0"
DEFAULT_WHITEBOX_SIZE = "13"
DEFAULT_WHITEBOX_HORIZONTAL_SPACING = "23"
DEFAULT_BLACKBOX_BORDER = "10"
DEFAULT_CALIBRATION_MODE = False
DEFAULT_DISPLAY_OSD_TIMESTAMP = False
DEFAULT_DISABLE_3D_ON_MOUSE_MOVE_UNDER_WINDOWS = True


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
        self.decoder_preference_variable = tkinter.StringVar(parent)
        self.decoder_preference_variable.set(DEFAULT_DECODER_PREFERENCE)
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
        self.blackbox_border_variable = tkinter.StringVar(parent)
        self.blackbox_border_variable.set(DEFAULT_BLACKBOX_BORDER)
        self.calibration_mode_variable = tkinter.BooleanVar(parent)
        self.calibration_mode_variable.set(DEFAULT_CALIBRATION_MODE)
        self.display_osd_timestamp_variable = tkinter.BooleanVar(parent)
        self.display_osd_timestamp_variable.set(DEFAULT_DISPLAY_OSD_TIMESTAMP)
        self.disable_3d_on_mouse_move_under_windows_variable = tkinter.BooleanVar(
            parent
        )
        self.disable_3d_on_mouse_move_under_windows_variable.set(
            DEFAULT_DISABLE_3D_ON_MOUSE_MOVE_UNDER_WINDOWS
        )

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
            f"If set to a value other than 0 this will force pygame to use a frame delay with tick_busy_loop instead of relying on vsync, this should not normally need to be set and is for experimental purposes only. \n(this value will not be updated on an already playing video) \n(default {DEFAULT_TARGET_FRAMERATE})",
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
        self.display_resolution_tooltip = idlelib.tooltip.Hovertip(
            self.display_resolution_frame,
            f"This is the resolution the video player will target for fullscreen mode while playing the video. \nIt may change your active resolution if it is different than your current resolution. \n(this value will not be updated on an already playing video) \n(default {DEFAULT_DISPLAY_RESOLUTION})",
            hover_delay=100,
        )
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
            f"(integer 0 to 100) Zooms out the video by the percent specified. This is to shrink videos on displays which have ghosting at the top and bottom of screen. \n(default {DEFAULT_DISPLAY_ZOOM_FACTOR})",
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
            f"Specifying the correct display size (provided in inches), allows the screen specific scaling of the on screen trigger boxes to match the sensors unit. \n(this value will not be updated on an already playing video) \n(default {DEFAULT_DISPLAY_SIZE})",
            hover_delay=100,
        )
        # self.display_size_frame.pack()
        self.display_size_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.decoder_preference_frame = tkinter.Frame(top)
        self.decoder_preference_label = tkinter.Label(
            self.decoder_preference_frame, text="Decoder Preference: "
        )
        self.decoder_preference_label.pack(padx=5, side=tkinter.LEFT)
        self.decoder_preference_option_menu = tkinter.OptionMenu(
            self.decoder_preference_frame,
            self.decoder_preference_variable,
            DECODER_PREFERENCE_DEFAULT,
            DECODER_PREFERENCE_NVCODEC,
            DECODER_PREFERENCE_VAAPI,
            DECODER_PREFERENCE_MSDK,
            DECODER_PREFERENCE_D3D11,
            DECODER_PREFERENCE_SOFTWARE,
        )
        self.decoder_preference_option_menu.pack(padx=5, side=tkinter.LEFT)
        # self.decoder_preference_frame.pack()
        self.generate_dot_graph_file_tooltip = idlelib.tooltip.Hovertip(
            self.decoder_preference_frame,
            "Sets a decoder preference which will be used to instruct gstreamer about which decoder to use. \nThis will only have an effect if the approriate hardware accelerated decoders are available on your system and compatible with the media file you are playing. \nYou can check available decoders using 'gst-inspect-1.0 | grep 'nvcodec\|vaapi\|264\|265\|vp9' \n(this value will not be updated on an already playing video)",
            hover_delay=100,
        )
        self.decoder_preference_frame.grid(row=row_count, column=0, sticky="w")
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
            f"The whitebox brightness setting (0 black to 255 white) lets users lower the brightness of the white boxes to help aleviate concerns of OLED burn in. \n(default {DEFAULT_WHITEBOX_BRIGHTNESS})",
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
            f"The whitebox corner position lets the user specify where the whitebox should be positioned, for best performance and duplicate frame (dropped frame) handling on OLED displays (or other displays which update from the top of the screen first) top_left or top_right are recommended. \n(default {DEFAULT_WHITEBOX_CORNER_POSITION})",
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
            f"The whitebox vertical position lets the user move the screen based whitebox down to better align with the 3d emitter tv mount they have. It is roughly equivalent to mm when display size is correctly configured. \n(default {DEFAULT_WHITEBOX_VERTICAL_POSITION})",
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
            f"The whitebox horizontal position lets the user move the screen based whitebox sideways towards the center of the screen. It is roughly equivalent to mm when display size is correctly configured. \n(default {DEFAULT_WHITEBOX_HORIZONTAL_POSITION})",
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
            f"The whitebox horizontal spacing lets the user increase/decrease the separation between white boxes to better align with the 3d emitter and tv pixel pitch they have. It is roughly equivalent to mm when display size is correctly configured. \n(default {DEFAULT_WHITEBOX_HORIZONTAL_SPACING})",
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
            f"The whitebox size lets the user increase or decrease the size of the whitebox. Setting the value too high will lead to cross talk and miss triggering, setting it too low will cause a low signal to noise and also miss triggering. \n(default {DEFAULT_WHITEBOX_SIZE})",
            hover_delay=100,
        )
        # self.whitebox_size_frame.pack()
        self.whitebox_size_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.blackbox_border_frame = tkinter.Frame(top)
        self.blackbox_border_label = tkinter.Label(
            self.blackbox_border_frame, text="Blackbox Border: "
        )
        self.blackbox_border_label.pack(padx=5, side=tkinter.LEFT)
        self.blackbox_border_entry = tkinter.Entry(
            self.blackbox_border_frame,
            textvariable=self.blackbox_border_variable,
        )
        self.blackbox_border_entry.pack(padx=5, side=tkinter.LEFT)
        self.blackbox_border_tooltip = idlelib.tooltip.Hovertip(
            self.blackbox_border_frame,
            f"The width of the black border that blocks the underlying movie content from interferring with detection of the trigger whiteboxes.  \nIt is roughly equivalent to mm when display size is correctly configured. \n(default {DEFAULT_BLACKBOX_BORDER})",
            hover_delay=100,
        )
        # self.blackbox_border_frame.pack()
        self.blackbox_border_frame.grid(row=row_count, column=0, sticky="w")
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
            f"Calibration mode shows a reticule to help with alignment of the sensor bar \nand also allows for adjustment of emitter frame_delay and frame_duration using hotkeys as instructed on the OSD. \nTo adjust emitter timing parameters you will need to ensure the emitter settings dialog is also open and connected to the emitter. \nTo optimize emitter settings adjustment it is recommended to use the red/blue or black/white test videos. \n(default {DEFAULT_CALIBRATION_MODE})",
            hover_delay=100,
        )
        # self.calibration_mode_frame.pack()
        self.calibration_mode_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.display_osd_timestamp_frame = tkinter.Frame(top)
        self.display_osd_timestamp_label = tkinter.Label(
            self.display_osd_timestamp_frame, text="Display OSD Timestamp: "
        )
        self.display_osd_timestamp_label.pack(padx=5, side=tkinter.LEFT)
        self.display_osd_timestamp_check_button = tkinter.Checkbutton(
            self.display_osd_timestamp_frame,
            variable=self.display_osd_timestamp_variable,
        )
        self.display_osd_timestamp_check_button.pack(padx=5, side=tkinter.LEFT)
        self.display_osd_timestamp_tooltip = idlelib.tooltip.Hovertip(
            self.display_osd_timestamp_frame,
            f"When enabled display OSD timestamp shows a timestamp and video duration on screen when the user moves their mouse. \nThis is useful for users when they cannot get the main toolbar window to popover the video on mouse move due to incompatible display drivers. \n(default {DEFAULT_DISPLAY_OSD_TIMESTAMP})",
            hover_delay=100,
        )
        # self.display_osd_timestamp_frame.pack()
        self.display_osd_timestamp_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

        self.disable_3d_on_mouse_move_under_windows_frame = tkinter.Frame(top)
        self.disable_3d_on_mouse_move_under_windows_label = tkinter.Label(
            self.disable_3d_on_mouse_move_under_windows_frame,
            text="Disable 3D On Mouse Move Under Windows: ",
        )
        self.disable_3d_on_mouse_move_under_windows_label.pack(
            padx=5, side=tkinter.LEFT
        )
        self.disable_3d_on_mouse_move_under_windows_check_button = tkinter.Checkbutton(
            self.disable_3d_on_mouse_move_under_windows_frame,
            variable=self.disable_3d_on_mouse_move_under_windows_variable,
        )
        self.disable_3d_on_mouse_move_under_windows_check_button.pack(
            padx=5, side=tkinter.LEFT
        )
        self.disable_3d_on_mouse_move_under_windows_tooltip = idlelib.tooltip.Hovertip(
            self.disable_3d_on_mouse_move_under_windows_frame,
            f"When the mouse moves on windows we switch from true fullscreen overlay mode to full screen windowed mode, this causes a drop in performance which can result in lots of duplicate frames on some PC's, this option will stop the 3D effect on mouse movement to avoid potential discomfort. \n(default {DEFAULT_DISABLE_3D_ON_MOUSE_MOVE_UNDER_WINDOWS})",
            hover_delay=100,
        )
        # self.disable_3d_on_mouse_move_under_windows_frame.pack()
        self.disable_3d_on_mouse_move_under_windows_frame.grid(
            row=row_count, column=0, sticky="w"
        )
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
                "decoder_preference": self.decoder_preference_variable.get(),
                "whitebox_brightness": self.whitebox_brightness_variable.get(),
                "whitebox_corner_position": self.whitebox_corner_position_variable.get(),
                "whitebox_vertical_position": self.whitebox_vertical_position_variable.get(),
                "whitebox_horizontal_position": self.whitebox_horizontal_position_variable.get(),
                "whitebox_size": self.whitebox_size_variable.get(),
                "whitebox_horizontal_spacing": self.whitebox_horizontal_spacing_variable.get(),
                "blackbox_border": self.blackbox_border_variable.get(),
                "calibration_mode": self.calibration_mode_variable.get(),
                "display_osd_timestamp": self.display_osd_timestamp_variable.get(),
                "disable_3d_on_mouse_move_under_windows": self.disable_3d_on_mouse_move_under_windows_variable.get(),
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
        self.decoder_preference_variable.set(
            settings.get("decoder_preference", DEFAULT_DECODER_PREFERENCE)
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
        self.blackbox_border_variable.set(
            settings.get("blackbox_border", DEFAULT_BLACKBOX_BORDER)
        )
        self.calibration_mode_variable.set(
            settings.get("calibration_mode", DEFAULT_CALIBRATION_MODE)
        )
        self.display_osd_timestamp_variable.set(
            settings.get("display_osd_timestamp", DEFAULT_DISPLAY_OSD_TIMESTAMP)
        )
        self.disable_3d_on_mouse_move_under_windows_variable.set(
            settings.get(
                "disable_3d_on_mouse_move_under_windows",
                DEFAULT_DISABLE_3D_ON_MOUSE_MOVE_UNDER_WINDOWS,
            )
        )

    def click_load_visisble_settings_from_disk(self):
        file_name = tkinter.filedialog.askopenfilename(
            title="Load Display Settings from Disk",
            initialdir=os.path.join(self.main_app.base_path, "settings"),
            filetypes=[("Display Settings File", "*.display_settings.json")],
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
            self.main_app.pageflipglsink.set_property(
                "blackbox-border", self.blackbox_border_variable.get()
            )
            self.main_app.pageflipglsink.set_property(
                "display-osd-timestamp", self.display_osd_timestamp_variable.get()
            )
            self.main_app.pageflipglsink.set_property(
                "disable-3d-on-mouse-move-under-windows",
                self.disable_3d_on_mouse_move_under_windows_variable.get(),
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
