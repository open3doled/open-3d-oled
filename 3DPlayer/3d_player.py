#!/usr/bin/env python3

# Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/

import os
import sys  # @UnusedImport
import tkinter  # @UnusedImport
import tkinter.ttk
import time
import traceback  # @UnusedImport
import functools
import idlelib.tooltip

# import sdl2.video  # @UnusedImport
import pysrt
import serial  # @UnusedImport
import json
import datetime

import argparse
import pathlib
import textwrap

import util
import emitter_settings
import display_settings
import start_video
import thanks


class TopWindow:
    def __init__(self, command_line_arguments):
        self.player = None
        self.video_open = False
        self.paused = False
        self.close = False
        self.emitter_serial = None
        self.last_mouse_position = None

        self.pageflipglsink = None
        self.subtitle3dsink = None

        # set base path
        self.internal_base_path = os.path.dirname(os.path.abspath(__file__))
        split_base_path = os.path.split(self.internal_base_path)
        if "_internal" == split_base_path[1]:
            self.base_path = split_base_path[0]
        else:
            self.base_path = self.internal_base_path

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
        self.thanks_dialog = None
        self.select_video_initialdir = os.path.join(self.base_path, "videos")
        self.select_subtitle_initialdir = os.path.join(self.base_path, "videos")
        self.select_firmware_file_initialdir = os.path.join(self.base_path, "firmwares")

        top_frame = tkinter.Frame(window)
        top_frame.pack(fill="x", expand=1, pady=5, padx=25, anchor="n")
        open_emitter_settings_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/sliders2-ir.svg"
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
        open_display_settings_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/sliders2-tv.svg"
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
        open_video_file_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/folder2-open.svg"
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
        stop_video_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/stop-fill.svg"
        )
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
        fullscreen_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/arrows-fullscreen.svg"
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
        flip_right_and_left_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/flip-right-and-left.svg"
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
        backward_big_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/rewind-3-fill.svg"
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
        backward_small_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/rewind-fill.svg"
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
        play_pause_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/play-pause-fill.svg"
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
        forward_small_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/fast-forward-fill.svg"
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
        forward_big_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/fast-forward-3-fill.svg"
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
        thanks_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/bookmark-heart.svg"
        )
        self.__thanks_button = tkinter.Button(
            top_frame,
            text="Forward 60s (shift-right)",
            image=thanks_button_image,
            highlightthickness=0,
            bd=0,
        )
        self.__thanks_button.tk_img = thanks_button_image
        self.__thanks_button.pack(padx=5, side=tkinter.LEFT)
        self.__thanks_button.bind("<Button-1>", self.click_thanks_button)
        close_button_image = util.svg_to_imagetk_photoimage(
            self.internal_base_path, "./images/x.svg"
        )
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

        self.video_progress_timestamp_variable = tkinter.IntVar(self.window)
        self.video_progress_timestamp_variable.set(0)
        self.video_progress_frame = None

        # window.geometry('100x300')
        window.bind("<Button-1>", self.click_mouse)
        window.bind("<B1-Motion>", self.move_mouse_with_click)
        # https://www.tcl.tk/man/tcl8.4/TkCmd/keysyms.html
        window.bind("<F11>", self.toggle_fullscreen)
        window.bind("f", self.flip_right_and_left)
        window.bind("<Escape>", self.stop_or_close_player)
        window.bind("<space>", self.toggle_paused)
        # add seek with left and right arrow keys (use shift to seek farther)

        # create display settings dialog object to store display settings
        self.display_settings_dialog = display_settings.DisplaySettingsDialog(
            self.window, self
        )

        self.process_command_line_arguments(command_line_arguments)

    def notify_player_if_mouse_moved(self):
        next_mouse_position = (
            self.window.winfo_pointerx(),
            self.window.winfo_pointery(),
        )
        if (
            next_mouse_position != self.last_mouse_position
            and self.pageflipglsink is not None
        ):
            self.pageflipglsink.set_property("mouse-moved", True)
            self.last_mouse_position = next_mouse_position

    def move_mouse_with_click(self, event=None):
        widget_string = str(event.widget)
        if (
            ".!frame.!button" in widget_string
            or ".!frame2.!progressbar" in widget_string
        ):
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

    def set_menu_on_top(
        self,
        control_on_top,
        dialogs_on_top,
        control_transparent,
        dialogs_transparent,
        event=None,
    ):  # @UnusedVariable
        window_list = [self.window]
        if (
            self.emitter_settings_dialog is not None
            and self.emitter_settings_dialog.top is not None
        ):
            window_list.append(self.emitter_settings_dialog.top)
        if (
            self.display_settings_dialog is not None
            and self.display_settings_dialog.top is not None
        ):
            window_list.append(self.display_settings_dialog.top)
        if (
            self.start_video_dialog is not None
            and self.start_video_dialog.top is not None
        ):
            window_list.append(self.start_video_dialog.top)
        for idx, temp_window in enumerate(window_list):
            if (
                self.pageflipglsink
                and self.pageflipglsink.get_property("fullscreen")
                and ((idx == 0 and control_on_top) or (idx > 0 and dialogs_on_top))
            ):
                set_topmost = True
            else:
                set_topmost = False

            if (
                self.pageflipglsink
                and self.pageflipglsink.get_property("fullscreen")
                and (
                    (idx == 0 and control_transparent)
                    or (idx > 0 and dialogs_transparent)
                )
            ):
                set_alpha = 0.0
            else:
                set_alpha = 1.0
            temp_window.wm_attributes("-topmost", set_topmost)
            temp_window.wm_attributes("-alpha", set_alpha)

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

        if self.video_progress_frame is not None:
            self.video_progress_frame.destroy()
            self.video_progress_frame = None
        if self.player is not None:
            self.player.set_state(Gst.State.NULL)
            self.player.run_dispose()
            del self.player
            self.player = None
        self.video_open = False
        if self.emitter_serial is not None:
            self.emitter_serial.pageflipglsink = None
        if self.pageflipglsink is not None:
            self.pageflipglsink.set_property("close", True)
        self.set_menu_on_top(True, False, False, False)
        # Gst.deinit()
        return "break"

    def close_player(self, event=None):  # @UnusedVariable
        if self.video_open:
            self.stop_player()
        self.close = True
        self.set_menu_on_top(True, False, False, False)
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
            seek_position = query_duration // 10 * int(seek_command.split("_")[2])
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

        self.emitter_settings_dialog = emitter_settings.EmitterSettingsDialog(
            self.window, self, close_callback
        )
        # self.window.wait_window(self.emitter_settings_dialog.top)

    def click_open_display_settings_button(self, event=None):  # @UnusedVariable
        if self.display_settings_dialog and self.display_settings_dialog.top:
            return
        self.display_settings_dialog.show()

    def process_command_line_arguments(self, args):
        if args.video_path:
            playback_parameters = (
                start_video.StartVideoDialog.get_video_history_default_settings()
            )
            playback_parameters["video_file_name"] = str(pathlib.Path(args.video_path))
            if args.subtitle_path:
                playback_parameters["subtitle_file_name"] = str(
                    pathlib.Path(args.subtitle_path)
                )
            if args.frame_packing:
                frame_packing = args.frame_packing
            else:
                frame_packing = (
                    start_video.StartVideoDialog.get_frame_packing_from_filename(
                        playback_parameters["video_file_name"]
                    )
                )
            playback_parameters["frame_packing"] = frame_packing
            if args.right_eye:
                playback_parameters["right_eye"] = args.right_eye
            else:
                playback_parameters["right_eye"] = (
                    "right" if frame_packing.startswith("side-by-side") else "bottom"
                )
            if args.display_resolution:
                playback_parameters["display_resolution"] = args.display_resolution
            self.start_video(playback_parameters)

    def click_thanks_button(self, event=None):  # @UnusedVariable
        if self.thanks_dialog and self.thanks_dialog.top:
            return

        self.thanks_dialog = thanks.ThanksDialog(self.window, self)

    def click_start_video_button(self, event=None):  # @UnusedVariable
        if self.video_open:
            return

        if self.start_video_dialog and self.start_video_dialog.top:
            return

        self.start_video_dialog = start_video_dialog = start_video.StartVideoDialog(
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
            "generate_dot_graph_file": start_video_dialog.generate_dot_graph_file_variable.get(),
            "audio_format_filter": start_video_dialog.audio_format_filter_variable.get(),
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
        generate_dot_graph_file = playback_parameters["generate_dot_graph_file"]
        audio_format_filter = playback_parameters["audio_format_filter"]

        target_framerate = self.display_settings_dialog.target_framerate_variable.get()
        add_n_bfi_frames_every_frame = (
            self.display_settings_dialog.add_n_bfi_frames_every_frame_variable.get()
        )
        display_resolution = playback_parameters.get(
            "display_resolution",
            (self.display_settings_dialog.display_resolution_variable.get()),
        )
        display_zoom_factor = playback_parameters.get(
            "display_zoom_factor",
            (self.display_settings_dialog.display_zoom_factor_variable.get()),
        )
        display_size = self.display_settings_dialog.display_size_variable.get()
        decoder_preference = (
            self.display_settings_dialog.decoder_preference_variable.get()
        )
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
        blackbox_border = self.display_settings_dialog.blackbox_border_variable.get()
        calibration_mode = self.display_settings_dialog.calibration_mode_variable.get()
        display_osd_timestamp = (
            self.display_settings_dialog.display_osd_timestamp_variable.get()
        )
        disable_3d_on_mouse_move_under_windows = (
            self.display_settings_dialog.disable_3d_on_mouse_move_under_windows_variable.get()
        )
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

        nvcodec_filters = [
            "cudaconvevrt",
            "cudaupload",
            "cudadownload",
            "nvjpegdec",
            "nvmpeg2videodec",
            "nvmpeg4videodec",
            "nvmpegvideodec",
            "nvh264dec",
            "nvh265dec",
            "nvvp9dec",
        ]
        vaapi_filters = [
            "vaapidecodebin",
            "vaapih264dec",
            "vaapih264enc",
            "vaapih265dec",
            "vaapijpegdec",
            "vaapijpegenc",
            "vaapimpeg2dec",
            "vaapipostproc",
            "vaapisink",
            "vaapivp8dec",
            "vaapivp9dec",
        ]
        msdk_filters = [
            "msdkh264dec",
            "msdkh265dec",
            "msdkvp9dec",
        ]
        d3d11_filters = [
            "d3d11h264dec",
            "d3d11h264device1dec",
            "d3d11h265dec",
            "d3d11h265device1dec",
            "d3d11mpeg2dec",
            "d3d11mpeg2device1dec",
            "d3d11vp8dec",
            "d3d11vp9dec",
            "d3d11vp9device1dec",
        ]
        software_filters = [
            "openh264",
            "avdec_h264",
            "vah264dec",
            "vah265dec",
            "libde265dec" "avdec_h265",
            "vavp9dec",
            "vp9dec",
            "avdec_vp9",
        ]

        filters_to_prioritize = []
        filters_to_deprioritize = set(
            nvcodec_filters
            + vaapi_filters
            + msdk_filters
            + d3d11_filters
            + software_filters
        )
        if decoder_preference == display_settings.DECODER_PREFERENCE_NVCODEC:
            filters_to_prioritize.extend(nvcodec_filters)
        elif decoder_preference == display_settings.DECODER_PREFERENCE_VAAPI:
            filters_to_prioritize.extend(vaapi_filters)
        elif decoder_preference == display_settings.DECODER_PREFERENCE_MSDK:
            filters_to_prioritize.extend(msdk_filters)
        elif decoder_preference == display_settings.DECODER_PREFERENCE_D3D11:
            filters_to_prioritize.extend(d3d11_filters)
        elif decoder_preference == display_settings.DECODER_PREFERENCE_SOFTWARE:
            filters_to_prioritize.extend(software_filters)
        else:  # default
            filters_to_deprioritize = set()
        filters_to_deprioritize.difference_update(filters_to_prioritize)
        for filter_to_prioritize in filters_to_prioritize:
            primary_decoder_element_factory = Gst.ElementFactory.find(
                filter_to_prioritize
            )
            if primary_decoder_element_factory:
                primary_decoder_element_factory.set_rank(Gst.Rank.PRIMARY + 1)
        for filter_to_deprioritize in filters_to_deprioritize:
            primary_decoder_element_factory = Gst.ElementFactory.find(
                filter_to_deprioritize
            )
            if primary_decoder_element_factory:
                primary_decoder_element_factory.set_rank(Gst.Rank.MARGINAL)
                # primary_decoder_element_factory.set_rank(Gst.Rank.NONE)

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

        # Sample of adding video filters to pipeline
        video_filters = None
        previous_video_filter = None  # @UnusedVariable
        video_sink_pad = None
        video_src_pad = None

        """
        if video_filters is None:
            video_filters = Gst.Bin("video_filters")

        subtitle_filesrc = Gst.ElementFactory.make("filesrc", "FileSrc")
        subtitle_filesrc.set_property("location", subtitle_file_path)
        video_filters.add(subtitle_filesrc)

        subtitle_subparse = Gst.ElementFactory.make("subparse", "SubParse")
        video_filters.add(subtitle_subparse)
        subtitle_filesrc.link(subtitle_subparse)

        if frame_packing == "side-by-side-half":
            frame_packing = "side-by-side-full"

            videoscale = Gst.ElementFactory.make("videoscale", "VideoScale")
            video_sink_pad = videoscale.sinkpad
            videoscale.set_property("method", 0)
            videoscale.set_property("add-borders", False)
            video_filters.add(videoscale)

            video_resolution_width = 1920
            video_resolution_height = 1080
            previous_video_filter = videoscale_capsfilter = Gst.ElementFactory.make(
                "capsfilter", "VideoScaleCapsFilter"
            )
            video_src_pad = videoscale_capsfilter.srcpad
            videoscale_capsfilter.set_property(
                "caps",
                Gst.caps_from_string(
                    f"video/x-raw,width={2*video_resolution_width},height={video_resolution_height},pixel-aspect-ratio=1/1"
                ),
            )
            video_filters.add(videoscale_capsfilter)
            videoscale.link(videoscale_capsfilter)

        subtitle_textoverlay = Gst.ElementFactory.make(
            "subtitleoverlay", "SubtitleOverlay"
        )
        if previous_video_filter is None:
            video_sink_pad = subtitle_textoverlay.sinkpads[0]
        video_src_pad = subtitle_textoverlay.srcpads[0]
        subtitle_textoverlay.set_property(
            "font-desc", f"{subtitle_font}, {subtitle_size}"
        )  # subtitle font we need a mono spacing font for the subtitle reformatter to work because it duplicates text and inserts whitespace to force the correct depth position
        subtitle_textoverlay.set_property(
            "subtitle-ts-offset", float(subtitle_offset)
        )  # The synchronisation offset between text and video in nanoseconds
        video_filters.add(subtitle_textoverlay)
        if previous_video_filter is not None:
            previous_video_filter.link(subtitle_textoverlay)
        subtitle_subparse.link(subtitle_textoverlay)
        """

        if video_filters is not None:
            ghostpad_video_sink = Gst.GhostPad.new("sink", video_sink_pad)
            ghostpad_video_source = Gst.GhostPad.new("src", video_src_pad)
            video_filters.add_pad(ghostpad_video_sink)
            video_filters.add_pad(ghostpad_video_source)
            self.player.set_property("video-filter", video_filters)

        # Sample of adding audio filters to pipeline
        audio_filters = None
        previous_audio_filter = None  # @UnusedVariable
        audio_sink_pad = None
        audio_src_pad = None

        if audio_format_filter != "":
            if audio_filters is None:
                audio_filters = Gst.Bin("audio_filters")

            previous_audio_filter = audio_capsfilter = (  # @UnusedVariable
                Gst.ElementFactory.make("capsfilter", "AudioCapsFilter")
            )
            audio_sink_pad = audio_capsfilter.sinkpad
            audio_src_pad = audio_capsfilter.srcpad
            audio_capsfilter.set_property(
                "caps",
                Gst.caps_from_string(audio_format_filter),
            )
            audio_filters.add(audio_capsfilter)

        if audio_filters is not None:
            ghostpad_audio_sink = Gst.GhostPad.new("sink", audio_sink_pad)
            ghostpad_audio_source = Gst.GhostPad.new("src", audio_src_pad)
            audio_filters.add_pad(ghostpad_audio_sink)
            audio_filters.add_pad(ghostpad_audio_source)
            self.player.set_property("audio-filter", audio_filters)

        if show_subtitles and subtitle_file_path:
            play_flags |= 0x00000004  # add subtitles

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

        self.pageflipglsink.set_property("calibration-mode", calibration_mode)
        self.pageflipglsink.set_property("fullscreen", True)
        self.pageflipglsink.set_property("frame-packing", frame_packing)
        self.pageflipglsink.set_property("right-eye", right_eye)
        self.pageflipglsink.set_property("target-framerate", target_framerate)
        self.pageflipglsink.set_property(
            "add-n-bfi-frames-every-frame", add_n_bfi_frames_every_frame
        )
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
        self.pageflipglsink.set_property("blackbox-border", blackbox_border)
        self.pageflipglsink.set_property("display-osd-timestamp", display_osd_timestamp)

        self.pageflipglsink.set_property("subtitle-font", subtitle_font)
        self.pageflipglsink.set_property("subtitle-size", subtitle_size)
        self.pageflipglsink.set_property("subtitle-depth", subtitle_depth)
        self.pageflipglsink.set_property(
            "subtitle-vertical-offset", subtitle_vertical_offset
        )
        self.pageflipglsink.set_property(
            "disable-3d-on-mouse-move-under-windows",
            disable_3d_on_mouse_move_under_windows,
        )
        self.pageflipglsink.set_property("start", True)  # this must be done last
        self.player.set_property("video-sink", self.pageflipglsink)

        self.player.set_property("flags", play_flags)  # no subtitles 0x00000004

        # self.player.set_property('force-aspect-ratio', True)

        self.player.set_state(Gst.State.PLAYING)

        self.video_open = True

        # setting fullscreen prematurely has no effect until video playback has full started
        failed_to_start = False
        for _ in range(75):
            if self.pageflipglsink.get_property("started"):
                break
            time.sleep(0.2)
        else:
            # if it didn't start after 15 seconds just stop as it probably means there was a gstreamer decoding error
            failed_to_start = True

        if not failed_to_start:
            video_duration = self.player.query_duration(Gst.Format.TIME).duration
            self.pageflipglsink.set_property("video-duration", video_duration)

            # show video progress frame
            self.video_progress_timestamp_variable.set(
                self.player.query_position(Gst.Format.TIME).cur
            )
            self.video_progress_frame = tkinter.Frame(self.window)
            self.video_progress_frame.pack(
                fill="x",
                expand=1,
                pady=5,
                padx=25,
                anchor="n",
            )
            self.video_progress_bar = tkinter.ttk.Progressbar(
                self.video_progress_frame,
                orient=tkinter.HORIZONTAL,
                maximum=video_duration,
                mode="determinate",
                variable=self.video_progress_timestamp_variable,
            )
            self.video_progress_bar.pack(
                fill="x", expand=1, pady=5, padx=5, anchor="n", side=tkinter.LEFT
            )
            self.video_progress_bar.bind("<Button-1>", self.seek_from_video_progress)
            self.video_duration_label = tkinter.Label(
                self.video_progress_frame,
                text=str(datetime.timedelta(seconds=video_duration // 1000000000)),
            )
            self.video_duration_label.pack(
                pady=5, padx=5, anchor="n", side=tkinter.RIGHT
            )

            self.__open_video_file_button.config(state="disabled")
            self.__flip_right_and_left_button.config(state="normal")
            self.__fullscreen_button.config(state="normal")
            self.__backward_big_button.config(state="normal")
            self.__backward_small_button.config(state="normal")
            self.__stop_video_button.config(state="normal")
            self.__play_pause_button.config(state="normal")
            self.__forward_small_button.config(state="normal")
            self.__forward_big_button.config(state="normal")

        if generate_dot_graph_file:
            Gst.debug_bin_to_dot_file(
                self.player,
                Gst.DebugGraphDetails.ALL,
                "pipeline_" + datetime.datetime.now().strftime("%Y-%m-%d %H%M%S"),
            )

        if failed_to_start:
            self.stop_player()

    def update_video_progress(self):
        self.video_progress_timestamp_variable.set(
            self.player.query_position(Gst.Format.TIME).cur
        )

    def seek_from_video_progress(self, event=None):  # @UnusedVariable
        click_x_progress_position = (
            self.video_progress_bar.winfo_pointerx()
            - self.video_progress_bar.winfo_rootx()
        )
        click_x_progress_width = self.video_progress_bar.winfo_width()
        video_duration = self.video_progress_bar["maximum"]
        seek_target_timestamp = (
            click_x_progress_position / click_x_progress_width * video_duration
        )
        # 'ACCURATE', 'FLUSH', 'KEY_UNIT', 'NONE', 'SEGMENT', 'SKIP', 'SNAP_AFTER', 'SNAP_BEFORE', 'SNAP_NEAREST', 'TRICKMODE', 'TRICKMODE_KEY_UNITS', 'TRICKMODE_NO_AUDIO'
        self.player.seek_simple(
            Gst.Format.TIME,
            # Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, # use these flags for fast seeking that isn't accurate
            Gst.SeekFlags.FLUSH
            | Gst.SeekFlags.ACCURATE,  # use these flags for slower but accurate seeking
            max(min(seek_target_timestamp, video_duration), 0),
        )

    def click_stop_video_button(self, event=None):  # @UnusedVariable
        self.stop_player()


def main():

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
    parsed_arguments = parser.parse_args()

    top_window = TopWindow(parsed_arguments)
    try:
        # window.mainloop()
        while not top_window.close:
            if top_window.player is not None and top_window.video_open:
                top_window.update_video_progress()
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
                        if (
                            "toggle_sensor_logging" in r
                            and "toggle_sensor_log" not in ignore_duplicate_actions
                        ):
                            if (
                                top_window.emitter_serial is not None
                                and top_window.emitter_settings_dialog is not None
                            ):
                                top_window.emitter_settings_dialog.click_opt_enable_stream_readings_to_serial_toggle()
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
                            if r == "set_menu_on_top_true":
                                top_window.set_menu_on_top(True, True, False, False)
                            else:
                                top_window.set_menu_on_top(False, False, True, True)
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
                                "whitebox_vertical_position": (
                                    "display",
                                    top_window.display_settings_dialog.whitebox_vertical_position_variable,
                                ),
                                "whitebox_horizontal_position": (
                                    "display",
                                    top_window.display_settings_dialog.whitebox_horizontal_position_variable,
                                ),
                                "whitebox_horizontal_spacing": (
                                    "display",
                                    top_window.display_settings_dialog.whitebox_horizontal_spacing_variable,
                                ),
                                "blackbox_border": (
                                    "display",
                                    top_window.display_settings_dialog.blackbox_border_variable,
                                ),
                                "whitebox_size": (
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
                                            "special_type": "setting",
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

                top_window.notify_player_if_mouse_moved()
            try:
                top_window.window.update_idletasks()
                top_window.window.update()
                time.sleep(0.01)
            except:
                # traceback.print_exc()
                top_window.close_player()

    finally:
        pass


if os.name == "nt":
    os.system("chcp.com 65001")

# set base path
internal_base_path = os.path.dirname(os.path.abspath(__file__))
gstreamer_plugins_active = os.path.join(internal_base_path, "gstreamer_plugins_active")
split_base_path = os.path.split(internal_base_path)
if "_internal" == split_base_path[1]:
    base_path = split_base_path[0]
else:
    base_path = internal_base_path
# os.environ["GST_DEBUG"] = "3"
if os.name == "nt":
    os.environ["GST_PLUGIN_PATH"] = (
        f"{gstreamer_plugins_active};{internal_base_path};{os.environ.get('GST_PLUGIN_PATH', '')}"
    )
else:
    os.environ["GST_PLUGIN_PATH"] = (
        f"{gstreamer_plugins_active}:{internal_base_path}:{os.environ.get('GST_PLUGIN_PATH', '')}"
    )
dot_graph_files_path = os.path.join(base_path, "dot_graph_files")
if not os.path.exists(dot_graph_files_path):
    os.mkdir(dot_graph_files_path)
os.environ["GST_DEBUG_DUMP_DOT_DIR"] = dot_graph_files_path
# LIBVA_DRIVER_NAME=i965 vainfo --display drm --device /dev/dri/renderD128
# os.environ["GST_VAAPI_ALL_DRIVERS"] = "1" # This environment variable can be set, independently of its value, to disable the drivers white list. By default only intel and mesa va drivers are loaded if they are available. The rest are ignored. With this environment variable defined, all the available va drivers are loaded, even if they are deprecated.
# os.environ["LIBVA_DRIVER_NAME"] = "i965" # This environment variable can be set with the drivers name to load. For example, intel's driver is i965, meanwhile mesa is gallium.
# os.environ["LIBVA_DRIVERS_PATH"] = "" # This environment variable can be set to a colon-separated list of paths (or a semicolon-separated list on Windows). libva will scan these paths for va drivers.
# os.environ["GST_VAAPI_DRM_DEVICE"] = "/dev/dri/renderD128" # This environment variable can be set to a specified DRM device when DRM display is used, it is ignored when other types of displays are used. By default /dev/dri/renderD128 is used for DRM display.
# os.environ["GST_PLUGIN_FEATURE_RANK"] = "vaapih264dec:MAX"

os.environ["SDL_HINT_VIDEO_HIGHDPI_DISABLED"] = (
    "1"  # https://wiki.libsdl.org/SDL2/SDL_HINT_VIDEO_HIGHDPI_DISABLED https://www.reddit.com/r/sdl/comments/pkvze5/i_wish_i_knew_about_this_feature_months_ago/
)

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

if __name__ == "__main__":
    main()
