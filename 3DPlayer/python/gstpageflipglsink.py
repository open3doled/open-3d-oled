#!/usr/bin/env python

# Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/

"""
    cd 3DPlayer
    export GST_PLUGIN_PATH=$PWD
    export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD
    echo $GST_PLUGIN_PATH
    GST_DEBUG=python:4 gst-inspect-1.0 gstpageflipglsink
    gst-launch-1.0 videotestsrc ! videoconvert ! gstpageflipglsink
    Based on:
        https://github.com/GStreamer/gst-python/blob/master/examples/plugins/python/audioplot.py
    Sourced From:
        https://lifestyletransfer.com/how-to-write-gstreamer-plugin-with-python/
        https://github.com/jackersson/gst-python-plugins/blob/master/gst/python/gstvideocrop.py
        https://lifestyletransfer.com/how-to-make-gstreamer-buffer-writable-in-python/
    Sink Example From:
        https://github.com/GStreamer/gst-python/blob/master/examples/plugins/python/sinkelement.py
    Caps negotiation:
        https://gstreamer.freedesktop.org/documentation/plugin-development/advanced/negotiation.html?gi-language=c
    Requires:
        pip install git+https://github.com/jackersson/gstreamer-python.git@{tag_name}#egg=gstreamer-python
        pip install git+https://github.com/jackersson/gstreamer-python.git@master#egg=gstreamer-python
    SDL2:
        https://wiki.libsdl.org/SDL2/CategoryAPI
        https://github.com/libsdl-org/SDL/tree/SDL2
        https://github.com/pygame/pygame/blob/f11b7850f33a2e02b563717bfae929f3bf188b04/buildconfig/stubs/pygame/_sdl2/video.pyi#L60
        https://github.com/pygame/pygame/blob/f11b7850f33a2e02b563717bfae929f3bf188b04/src_c/_sdl2/video.c
        https://github.com/py-sdl/py-sdl2/blob/0.9.16/sdl2/video.py
"""

import logging
import math  # @UnusedImport
import traceback
import time

# import sdl2.video
import json
import collections
import threading
import ctypes
import multiprocessing  # @UnusedImport
import multiprocessing.sharedctypes
import multiprocessing.shared_memory
import psutil
import os

# """
import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")
gi.require_version("GstVideo", "1.0")

from gi.repository import Gst, GObject, GLib, GstBase, GstVideo  # noqa:F401,F402

import gstreamer_utils  # @UnresolvedImport

# """

import numpy as np
import sys  # @UnusedImport
from pygame import _sdl2 as pygame_sdl2
from pygame import locals as pg_locals

import OpenGL.GL as gl
import pygame as pg

# if __name__ == "__main__":
#    Gst.init(None)
Gst.init(
    None
)  # because of how multiprocessing on windows doesn't use fork we need to initialize again here

USE_LINE_PROFILER = False
if USE_LINE_PROFILER:
    from line_profiler import LineProfiler

    line_profiler_obj = LineProfiler()
else:

    def line_profiler_obj(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper


# resolution = '2560x1080'
resolution = "1920x1080"

# defaults for 55inch LG OLED 1920x1080 120hz all in mm to be adjusted by pixel pitch factor for different display sizes
default_black_box_gradient_width = 6.3371
default_white_box_gradient_width = 3.1686
# default_black_box_width = 44.3599
# default_black_box_height = 25.3485
default_black_box_width = 44.3599
default_black_box_height = 20.3485
default_white_box_width = 12.6743
default_white_box_height = 12.6743
default_white_box_horizontal_offset_1 = 0
default_white_box_horizontal_offset_2 = (
    22.86  # 22.86 mm sensor spacing x 1.578 pixels / mm = 36 pixels
)

# formats taken from existing videoconvert plugins
# gst-inspect-1.0 videoconvert
FORMATS = [
    f.strip()
    #           for f in "RGBx,xRGB,BGRx,xBGR,RGBA,ARGB,BGRA,ABGR,RGB,BGR,RGB16,RGB15,GRAY8,GRAY16_LE,GRAY16_BE".split(',')]
    #           for f in "I420,RGBx,xRGB,BGRx,xBGR,RGBA,ARGB,BGRA,ABGR,RGB,BGR,RGB16,RGB15,GRAY8,GRAY16_LE,GRAY16_BE".split(',')]
    #           for f in "I420,YV12,YUY2,UYVY,AYUV,VUYA,RGBx,BGRx,xRGB,xBGR,RGBA,BGRA,ARGB,ABGR,RGB,BGR,Y41B,Y42B,YVYU,Y444,v210,v216,Y210,Y410,NV12,NV21,GRAY8,GRAY16_BE,GRAY16_LE,v308,RGB16,BGR16,RGB15,BGR15,UYVP,A420,RGB8P,YUV9,YVU9,IYU1,ARGB64,AYUV64,r210,I420_10BE,I420_10LE,I422_10BE,I422_10LE,Y444_10BE,Y444_10LE,GBR,GBR_10BE,GBR_10LE,NV16,NV24,NV12_64Z32,A420_10BE,A420_10LE,A422_10BE,A422_10LE,A444_10BE,A444_10LE,NV61,P010_10BE,P010_10LE,IYU2,VYUY,GBRA,GBRA_10BE,GBRA_10LE,BGR10A2_LE,GBR_12BE,GBR_12LE,GBRA_12BE,GBRA_12LE,I420_12BE,I420_12LE,I422_12BE,I422_12LE,Y444_12BE,Y444_12LE,GRAY10_LE32,NV12_10LE32,NV16_10LE32,NV12_10LE40".split(',')]
    for f in "RGBA".split(",")
]

# Input caps
IN_CAPS = Gst.Caps(
    Gst.Structure(
        "video/x-raw",
        format=Gst.ValueList(FORMATS),
        width=Gst.IntRange(range(1, GLib.MAXINT)),
        height=Gst.IntRange(range(1, GLib.MAXINT)),
    )
)


def clip(value, min_value, max_value):
    "Clip value to range [min_value, max_value]"
    return min(max(value, min_value), max_value)


# """

FRAME_PACKING_SIDE_BY_SIDE_HALF = "side-by-side-half"
FRAME_PACKING_SIDE_BY_SIDE_FULL = "side-by-side-full"
FRAME_PACKING_OVER_AND_UNDER_HALF = "over-and-under-half"
FRAME_PACKING_OVER_AND_UNDER_FULL = "over-and-under-full"

WINDOW_NAME = "FlipGLPlayer"
FINISH_BUFFER_COPY_EVENT_TIMEOUT = 1 / 30


class PageflipGLWindow(threading.Thread):
    def __init__(self):
        super(PageflipGLWindow, self).__init__()
        self.__do_start = False
        self.__started = False
        self.__do_stop = False
        self.__left_or_bottom_page = True
        self.__finish_buffer_copy_event = threading.Event()
        self.__in_image_updated = False
        self.__in_image = None
        self.__in_image_play_timestamp = None
        self.__window_height = None
        self.__window_width = None
        self.__do_fullscreen = None
        self.__use_separate_process = True
        self.__fullscreen = False
        self.__frame_packing = "side-by-side-half"
        self.__right_eye = "right"
        self.__target_framerate = "0"
        self.__target_frametime = None
        self.__last_frame_at_millis = None
        self.__display_resolution = "1920x1080"
        self.__display_resolution_height = 1080
        self.__display_resolution_width = 1920
        self.__display_size = "55"
        self.__pixel_pitch_y = self.__display_resolution_height / (
            int(self.__display_size) * 0.49 * 25.4
        )  # for a 55 inch 16:9 1080 display gives 1.577724862 pixels per mm (gives bad sizes for non 16:9 display resolutions)
        self.__pixel_pitch_x = self.__display_resolution_width / (
            int(self.__display_size) * 0.87 * 25.4
        )  # for a 55 inch 16:9 1080 display gives 1.579739837 pixels per mm (gives bad sizes for non 16:9 display resolutions)
        self.__black_box_width = int(default_black_box_width * self.__pixel_pitch_x)
        self.__black_box_height = int(default_black_box_height * self.__pixel_pitch_y)
        self.__whitebox_brightness = 255
        self.__whitebox_vertical_position = 0
        self.__whitebox_horizontal_spacing = 23
        self.__last_mouse = True
        self.__last_mouse_moved_at = None
        self.__set_menu_on_top_true = True
        self.__set_video_on_top_true = False
        self.__requests = ""
        self.__overlay_boxes = None  # 0 left, 1 right
        self.__latest_subtitles = collections.deque()
        self.__latest_subtitles_event = threading.Event()
        self.__latest_subtitle_data = ""
        self.__subtitle_font = "arial"
        self.__subtitle_size = 30
        self.__subtitle_depth = 0
        self.__subtitle_vertical_offset = 150
        self.__window_size_scale_factor = 1.0
        self.__subtitle_font_set = None
        self.__skip_n_page_flips = 0

        self.__calibration_mode = False
        self.__show_calibration_instruction_image = (
            True  # this only applies if in calibration mode to begin with
        )
        calibration_image = pg.image.load(
            os.path.join(os.path.dirname(__file__), "calibration_message.png")
        )
        calibration_image_rgb = pg.surfarray.array3d(calibration_image)
        calibration_image_alpha = pg.surfarray.array_alpha(calibration_image).reshape(
            (*calibration_image_rgb.shape[0:2], 1)
        )
        calibration_image_rgba = np.concatenate(
            (calibration_image_rgb, calibration_image_alpha), 2
        )
        self.__calibration_instruction_image = np.flip(
            calibration_image_rgba.transpose((1, 0, 2)), 0
        )

        self.__debug_loop_times = dict()
        self.__debug_loop_count = 0

        pg.init()

    def __start(self):
        (self.__window_width, self.__window_height) = (
            self.__display_resolution_width // 2,
            self.__display_resolution_height // 2,
        )
        self.__pg_clock = pg.time.Clock()
        self.__pg_window = pg.display.set_mode(
            (self.__display_resolution_width, self.__display_resolution_height),
            pg_locals.DOUBLEBUF
            | pg_locals.OPENGL
            | pg_locals.RESIZABLE
            | pg_locals.FULLSCREEN,
            # pg_locals.DOUBLEBUF | pg_locals.OPENGL | pg_locals.RESIZABLE,
            vsync=1,
        )
        self.__fullscreen = True
        self.__sdl2_window = pygame_sdl2.Window.from_display_module()
        self.__sdl2_window.size = (
            self.__display_resolution_width // 2,
            self.__display_resolution_height // 2,
        )
        self.__sdl2_window.position = pygame_sdl2.WINDOWPOS_CENTERED
        # self.__sdl2_window.set_fullscreen(desktop=False) # desktop False change full screen resolution to window size, desktop True use desktop resolution
        # self.__sdl2_window.restore()  # this changes window from maximized state to normal window state
        # self.__sdl2_window.set_windowed()
        self.__do_fullscreen = False
        pg.display.set_caption(WINDOW_NAME)
        pg.display.set_icon(
            pg.image.load(os.path.join(os.path.dirname(__file__), "blank.ico"))
        )

        gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
        # gl.glEnable(gl.GL_DEPTH_TEST) # we are disabling this for now because the texture z depth and overlay elements aren't configured right yet.
        gl.glEnable(gl.GL_BLEND)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnable(gl.GL_TEXTURE_2D)

        self.__prepare_video_texture()
        # self.__prepare_pbos()
        self.__reshape_window()
        self.__started = True

        self.__update_overlay_boxes()

        temp_width, temp_height = self.__in_image_width, self.__in_image_height
        print(
            f"PageflipGLSink Started with display ({self.__display_resolution_width}x{self.__display_resolution_height}), source ({temp_width}x{temp_height})"
        )

    def __stop(self):

        # self.__destroy_pbos()
        self.__destroy_video_texture()

        self.__pg_window = None
        self.__sdl2_window = None

        pg.quit()

    def __prepare_video_texture(self):
        self.__video_texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.__video_texture_id)
        gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)

    def __destroy_video_texture(self):
        gl.glDeleteTextures([self.__video_texture_id])
        self.__video_texture_id = None

    def __prepare_pbos(self):
        temp_width, temp_height = self.__in_image_width, self.__in_image_height
        num_texels = temp_width * temp_height
        data = np.zeros((num_texels, 4), np.uint8)
        self.dest_pbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.dest_pbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, data, gl.GL_DYNAMIC_DRAW)
        # gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

    def __destroy_pbos(self):
        for pbo in (self.dest_pbo,):
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, int(pbo))
            gl.glDeleteBuffers(1, int(pbo))
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        self.dest_pbo = None

    def __reshape_window(self):
        # https://stackoverflow.com/questions/24538310/the-difference-between-glortho-and-glviewport-in-opengl
        gl.glViewport(
            0, 0, self.__display_resolution_width, self.__display_resolution_height
        )
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(
            0,
            self.__display_resolution_width,
            0,
            self.__display_resolution_height,
            -1,
            1,
        )
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

    def __update_overlay_boxes(self):
        black_box_gradient_width = int(
            default_black_box_gradient_width * self.__pixel_pitch_x
        )
        white_box_gradient_width = int(
            default_white_box_gradient_width * self.__pixel_pitch_x
        )
        # original_black_box_width = int(default_black_box_width * self.__pixel_pitch_x)
        original_black_box_width = int(
            (
                default_black_box_width
                - default_white_box_horizontal_offset_2
                + self.__whitebox_horizontal_spacing
            )
            * self.__pixel_pitch_x
        )
        original_black_box_height = int(
            (default_black_box_height + self.__whitebox_vertical_position)
            * self.__pixel_pitch_y
        )
        if self.__calibration_mode:
            black_box_width = self.__black_box_width = int(
                original_black_box_width
                + default_black_box_width * self.__pixel_pitch_x
            )
            black_box_height = self.__black_box_height = int(
                original_black_box_height
                + default_black_box_height * self.__pixel_pitch_y
            )
        else:
            black_box_width = self.__black_box_width = original_black_box_width
            black_box_height = self.__black_box_height = original_black_box_height
        white_box_width = int(default_white_box_width * self.__pixel_pitch_x)
        white_box_height = int(default_white_box_height * self.__pixel_pitch_y)
        white_box_horizontal_offset_1 = int(
            default_white_box_horizontal_offset_1 * self.__pixel_pitch_x
        )
        white_box_horizontal_offset_2 = int(
            # default_white_box_horizontal_offset_2 * self.__pixel_pitch_x
            (default_white_box_horizontal_offset_1 + self.__whitebox_horizontal_spacing)
            * self.__pixel_pitch_x
        )
        white_box_horizontal_offsets = (
            white_box_horizontal_offset_1,
            white_box_horizontal_offset_2,
        )
        self.__overlay_boxes = []
        for n in range(2):  # 0 left, 1 right
            box = np.ndarray(
                shape=(black_box_height, black_box_width, 4), dtype=np.uint8
            )
            # box = pg.surface.Surface((black_box_width, black_box_height), flags=pg_locals.SRCALPHA, )
            boxes_to_make = [
                (
                    0,
                    0,
                    black_box_width,
                    black_box_height,
                    black_box_gradient_width,
                    0,
                    False,
                    True,
                    False,
                    True,
                    False,
                ),
                # (white_box_horizontal_offsets[n], black_box_height-white_box_height, white_box_width, white_box_height, white_box_gradient_width, 0, False, True, True if n == 1 else False, True, True)
                (
                    white_box_horizontal_offsets[n],
                    black_box_height
                    - white_box_height
                    - int(self.__whitebox_vertical_position * self.__pixel_pitch_y),
                    white_box_width,
                    white_box_height,
                    white_box_gradient_width,
                    0,
                    True,
                    True,
                    True,
                    True,
                    True,
                ),
            ]
            if self.__calibration_mode:
                x_halfway_point = (
                    white_box_horizontal_offset_1
                    + white_box_width
                    + white_box_horizontal_offset_2
                ) // 2
                boxes_to_make.extend(
                    [
                        (
                            original_black_box_width,
                            black_box_height
                            - white_box_height // 2
                            - int(
                                self.__whitebox_vertical_position * self.__pixel_pitch_y
                            ),
                            black_box_width - original_black_box_width,
                            1,
                            0,
                            int(self.__whitebox_brightness),
                            False,
                            False,
                            False,
                            False,
                            False,
                        ),  # horizontal reticule
                        (
                            x_halfway_point,
                            0,
                            1,
                            black_box_height - original_black_box_height,
                            0,
                            int(self.__whitebox_brightness),
                            False,
                            False,
                            False,
                            False,
                            False,
                        ),  # verticle reticule
                    ]
                )
            # import pprint
            # pprint.pprint(boxes_to_make)
            for (
                px,
                py,
                wx,
                wy,
                box_gradient_width,
                shade,
                smooth_top,
                smooth_bottom,
                smooth_left,
                smooth_right,
                is_white_box,
            ) in boxes_to_make:
                for x in range(wx):
                    for y in range(wy):
                        if (
                            smooth_left
                            and smooth_bottom
                            and x < box_gradient_width
                            and y < box_gradient_width
                        ):  # bottom left corner (smoothed)
                            tone = int(
                                (min(x, box_gradient_width) / box_gradient_width)
                                * (min(y, box_gradient_width) / box_gradient_width)
                                * 255
                            )
                        elif (
                            smooth_left
                            and smooth_top
                            and x < box_gradient_width
                            and y > wy - box_gradient_width
                        ):  # top left corner (smoothed)
                            tone = int(
                                (min(x, box_gradient_width) / box_gradient_width)
                                * (min(wy - y, box_gradient_width) / box_gradient_width)
                                * 255
                            )
                        elif (
                            smooth_right
                            and smooth_bottom
                            and x > wx - box_gradient_width
                            and y < box_gradient_width
                        ):  # bottom right corner (smoothed)
                            tone = int(
                                (min(wx - x, box_gradient_width) / box_gradient_width)
                                * (min(y, box_gradient_width) / box_gradient_width)
                                * 255
                            )
                        elif (
                            smooth_right
                            and smooth_top
                            and x > wx - box_gradient_width
                            and y > wy - box_gradient_width
                        ):  # top right corner (smoothed)
                            tone = int(
                                (min(wx - x, box_gradient_width) / box_gradient_width)
                                * (min(wy - y, box_gradient_width) / box_gradient_width)
                                * 255
                            )
                        elif (
                            smooth_left and x < box_gradient_width
                        ):  # left side (smoothed)
                            tone = int(
                                (min(x, box_gradient_width) / box_gradient_width) * 255
                            )
                        elif (
                            smooth_right and x > wx - box_gradient_width
                        ):  # right side (smoothed)
                            tone = int(
                                (min(wx - x, box_gradient_width) / box_gradient_width)
                                * 255
                            )
                        elif (
                            smooth_bottom and y < box_gradient_width
                        ):  # bottom side (smoothed)
                            tone = int(
                                (min(y, box_gradient_width) / box_gradient_width) * 255
                            )
                        elif (
                            smooth_top and y > wy - box_gradient_width
                        ):  # top side (smoothed)
                            tone = int(
                                (min(wy - y, box_gradient_width) / box_gradient_width)
                                * 255
                            )
                        else:
                            tone = 255
                        if is_white_box:
                            white_box_shade = int(
                                tone * self.__whitebox_brightness / 255
                            )
                            box[max(min(py + y, black_box_height - 1), 0)][px + x][
                                0
                            ] = white_box_shade
                            box[max(min(py + y, black_box_height - 1), 0)][px + x][
                                1
                            ] = white_box_shade
                            box[max(min(py + y, black_box_height - 1), 0)][px + x][
                                2
                            ] = white_box_shade
                            box[max(min(py + y, black_box_height - 1), 0)][px + x][
                                3
                            ] = box[max(min(py + y, black_box_height - 1), 0)][px + x][
                                3
                            ]
                        else:
                            box[max(min(py + y, black_box_height - 1), 0)][px + x] = [
                                shade,
                                shade,
                                shade,
                                tone,
                            ]

            self.__overlay_boxes.append(box)
            # np.set_printoptions(threshold=sys.maxsize)
            # print(box)
            # self.__overlay_boxes.append(box.convert_alpha())

    def __update_subtitle_surface_and_data(self):
        if self.__latest_subtitle_data:
            for latest_subtitle in self.__latest_subtitles:
                new_latest_subtitle = {
                    "rendered_surface": [],
                    "rendered_surface_shadow": [],
                    "rendered_data": [],
                    "rendered_data_shadow": [],
                }
                latest_subtitle_text_lines = latest_subtitle["text"].splitlines()
                for latest_subtitle_text_line in latest_subtitle_text_lines:
                    latest_subtitle_rendered_surface_temp = (
                        self.__subtitle_font_set.render(
                            latest_subtitle_text_line, True, (170, 170, 170, 255)
                        ).convert_alpha()
                    )
                    new_latest_subtitle["rendered_surface"].append(
                        latest_subtitle_rendered_surface_temp
                    )
                    new_latest_subtitle["rendered_data"].append(
                        pg.image.tostring(
                            latest_subtitle_rendered_surface_temp, "RGBA", True
                        )
                    )
                    latest_subtitle_rendered_surface_shadow_temp = (
                        self.__subtitle_font_set.render(
                            latest_subtitle_text_line, True, (0, 0, 0, 255)
                        ).convert_alpha()
                    )
                    new_latest_subtitle["rendered_surface_shadow"].append(
                        latest_subtitle_rendered_surface_shadow_temp
                    )
                    new_latest_subtitle["rendered_data_shadow"].append(
                        pg.image.tostring(
                            latest_subtitle_rendered_surface_shadow_temp, "RGBA", True
                        )
                    )
                # TODO: these should be in a mutex to ensure we aren't trying to read these as they are changing
                latest_subtitle.update(new_latest_subtitle)
                latest_subtitle["text_line_count"] = len(latest_subtitle_text_lines)

    def __update_subtitle_fonts(self):
        # font_file = pygame.font.match_font(self.__subtitle_font)  # Select and
        # self.__subtitle_font_set = pygame.font.Font(font_file, int(self.__subtitle_size * self.__window_size_scale_factor))
        self.__subtitle_font_set = pg.font.SysFont(
            self.__subtitle_font,
            int(self.__subtitle_size * self.__window_size_scale_factor),
        )
        self.__update_subtitle_surface_and_data()

    def __update_window_scale_factor(self):
        if self.fullscreen:
            self.__window_size_scale_factor = 1
        else:
            self.__window_size_scale_factor = min(
                (
                    self.__window_width / self.__display_resolution_width,
                    self.__window_height / self.__display_resolution_height,
                )
            )
        self.__update_subtitle_fonts()
        self.__update_overlay_boxes()

    @line_profiler_obj
    def __update(self):
        try:
            if self.__last_mouse_moved_at is not None:
                set_menu_on_top_true = (
                    True if time.time() - self.__last_mouse_moved_at < 2.0 else False
                )
                if self.__set_menu_on_top_true != set_menu_on_top_true:
                    self.__set_menu_on_top_true = set_menu_on_top_true
                    if set_menu_on_top_true:
                        pg.mouse.set_visible(True)
                        self.__set_video_on_top_true = False
                    else:
                        if self.__fullscreen:
                            self.__sdl2_window.focus()
                    self.__requests = ",".join(
                        self.__requests.split(",")
                        + [
                            (
                                "set_menu_on_top_true"
                                if set_menu_on_top_true
                                else "set_menu_on_top_false"
                            )
                        ]
                    )
                set_video_on_top_true = (
                    True if time.time() - self.__last_mouse_moved_at > 3 else False
                )
                if (
                    self.__set_video_on_top_true is False
                    and set_video_on_top_true is True
                ):
                    self.__set_video_on_top_true = set_video_on_top_true
                    if self.__fullscreen:
                        pg.mouse.set_visible(False)
                        self.__sdl2_window.focus()
                        """
                  print('self.__sdl2_window.position', self.__sdl2_window.position)
                  window_sdl = sdl2.video.SDL_GetWindowFromID(self.__sdl2_window.id)
                  print(window_sdl)
                  pos_x, pos_y = ctypes.c_int(), ctypes.c_int()
                  sdl2.video.SDL_GetWindowPosition(window_sdl,ctypes.byref(pos_x),ctypes.byref(pos_y))
                  print('sdl2.video.SDL_GetWindowPosition(window_sdl)',(pos_x, pos_y))
                  sdl2.video.SDL_RaiseWindow(window_sdl)
                  sdl2.video.SDL_SetWindowInputFocus(window_sdl)
                  sdl2.video.SDL_SetWindowFullscreen(window_sdl, sdl2.video.SDL_WINDOW_FULLSCREEN_DESKTOP)
                  """
                        # self.__sdl2_window.position = (0,0)

            latest_mouse = pg.mouse.get_pos()
            if latest_mouse != self.__last_mouse:
                self.__last_mouse = latest_mouse
                self.__last_mouse_moved_at = time.time()
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    # TODO: figure out how to gracefully communicate shutdown back to main app
                    pass
                elif event.type == pg.VIDEORESIZE:
                    self.__window_width, self.__window_height = event.size
                    print(
                        f"PageflipGLSink Resized window ({self.__window_width}x{self.__window_height} {event.size})"
                    )
                    self.__update_window_scale_factor()
                elif event.type == pg.KEYDOWN:
                    # https://www.pygame.org/docs/ref/key.html
                    # print(f"Keydown {event.key}")
                    # print(f"Calibration Mode {self.__calibration_mode}")
                    if event.key == pg.K_ESCAPE:
                        self.__requests = ",".join(
                            self.__requests.split(",") + ["close"]
                        )
                    elif event.key == pg.K_SPACE:
                        self.__requests = ",".join(
                            self.__requests.split(",") + ["toggle_paused"]
                        )
                    elif event.key >= pg.K_0 and event.key <= pg.K_9:
                        self.__requests = ",".join(
                            self.__requests.split(",")
                            + [f"seek_percent_{event.key - pg.K_0}"]
                        )
                    elif event.key == pg.K_RIGHT:
                        if event.mod & pg.KMOD_SHIFT:
                            self.__requests = ",".join(
                                self.__requests.split(",") + ["seek_forward_big"]
                            )
                        else:
                            self.__requests = ",".join(
                                self.__requests.split(",") + ["seek_forward_small"]
                            )
                    elif event.key == pg.K_LEFT:
                        if event.mod & pg.KMOD_SHIFT:
                            self.__requests = ",".join(
                                self.__requests.split(",") + ["seek_backward_big"]
                            )
                        else:
                            self.__requests = ",".join(
                                self.__requests.split(",") + ["seek_backward_small"]
                            )
                    elif event.key == pg.K_F9:
                        if USE_LINE_PROFILER:
                            if not line_profiler_obj.global_enable:
                                print("enable global profiling")
                                line_profiler_obj.global_enable = True
                            else:
                                line_profiler_obj.global_enable = False
                                print("disable global profiling")
                    elif event.key == pg.K_F10:
                        if USE_LINE_PROFILER:
                            line_profiler_obj.print_stats()
                            line_profiler_obj.clear_stats()
                    elif event.key == pg.K_F11:
                        self.fullscreen = not self.__fullscreen
                    elif event.key == pg.K_f:
                        if self.__right_eye == "right":
                            self.__right_eye = "left"
                        elif self.__right_eye == "left":
                            self.__right_eye = "right"
                        elif self.__right_eye == "top":
                            self.__right_eye = "bottom"
                        elif self.__right_eye == "bottom":
                            self.__right_eye = "top"
                    elif self.__calibration_mode:
                        if event.key == pg.K_g:
                            self.__show_calibration_instruction_image = (
                                not self.__show_calibration_instruction_image
                            )
                        elif event.key == pg.K_y:
                            self.__whitebox_vertical_position -= 1
                            self.__update_overlay_boxes()
                            self.__requests = ",".join(
                                self.__requests.split(",")
                                + ["calibration_decrease_whitebox_vertical_position"]
                            )
                        elif event.key == pg.K_h:
                            self.__whitebox_vertical_position += 1
                            self.__update_overlay_boxes()
                            self.__requests = ",".join(
                                self.__requests.split(",")
                                + ["calibration_increase_whitebox_vertical_position"]
                            )
                        elif event.key == pg.K_u:
                            self.__whitebox_horizontal_spacing -= 1
                            self.__update_overlay_boxes()
                            self.__requests = ",".join(
                                self.__requests.split(",")
                                + ["calibration_decrease_whitebox_horizontal_spacing"]
                            )
                        elif event.key == pg.K_j:
                            self.__whitebox_horizontal_spacing += 1
                            self.__update_overlay_boxes()
                            self.__requests = ",".join(
                                self.__requests.split(",")
                                + ["calibration_increase_whitebox_horizontal_spacing"]
                            )
                        elif event.key == pg.K_o:
                            self.__requests = ",".join(
                                self.__requests.split(",")
                                + ["calibration_decrease_frame_duration"]
                            )
                        elif event.key == pg.K_l:
                            self.__requests = ",".join(
                                self.__requests.split(",")
                                + ["calibration_increase_frame_duration"]
                            )

            # this hack is necessary because for some reason if we don't do this in this loop the fullscreen from the menu button doesn't actually change the video size only the window size
            if self.__do_fullscreen is not None:
                self.fullscreen = self.__do_fullscreen
                self.__do_fullscreen = None

            in_width, in_height = self.__in_image_width, self.__in_image_height

            gl.glClearColor(0, 0, 0, 1)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glColor3fv((1, 1, 1))
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.__video_texture_id)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            # gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1) # may be necessary for non 32 bit aligned pixel formats https://stackoverflow.com/questions/66221801/glteximage2d-data-not-filled-as-expected
            if self.__in_image_updated:
                in_image_bytes = self.__in_image
                gl.glTexImage2D(
                    gl.GL_TEXTURE_2D,
                    0,
                    gl.GL_RGBA,  # https://www.khronos.org/opengl/wiki/Image_Format GL_ALPHA RL_RGBA
                    in_width,
                    in_height,
                    0,
                    gl.GL_RGBA,  # https://www.khronos.org/opengl/wiki/Image_Format GL_ALPHA RL_RGBA
                    gl.GL_UNSIGNED_BYTE,
                    in_image_bytes,
                )
                self.__finish_buffer_copy_event.set()
                self.__in_image_updated = False

            # https://community.khronos.org/t/gltexcoord2f-simple-questions/63784
            if self.__frame_packing == FRAME_PACKING_SIDE_BY_SIDE_HALF:
                crop_pos_x = (self.__display_resolution_width - in_width) / 2
                crop_pos_y = (self.__display_resolution_height - in_height) / 2
                texture_pos_x = 0
                texture_pos_y = 0
                if self.__left_or_bottom_page:
                    texture_coord_x_low = 0
                    texture_coord_x_high = 0.5
                else:
                    texture_coord_x_low = 0.5
                    texture_coord_x_high = 1.0
                texture_coord_y_low = 0.0
                texture_coord_y_high = 1.0
            elif self.__frame_packing == FRAME_PACKING_SIDE_BY_SIDE_FULL:
                crop_pos_x = (self.__display_resolution_width - in_width / 2) / 2
                crop_pos_y = (self.__display_resolution_height - in_height) / 2
                if self.__left_or_bottom_page:
                    texture_pos_x = 0
                else:
                    texture_pos_x = in_width / 2
                texture_pos_y = 0
                texture_coord_x_low = 0.0
                texture_coord_x_high = 1.0
                texture_coord_y_low = 0.0
                texture_coord_y_high = 1.0
            elif self.__frame_packing == FRAME_PACKING_OVER_AND_UNDER_HALF:
                crop_pos_x = (self.__display_resolution_width - in_width) / 2
                crop_pos_y = (self.__display_resolution_height - in_height) / 2
                texture_pos_x = 0
                texture_pos_y = 0
                texture_coord_x_low = 0.0
                texture_coord_x_high = 1.0
                if self.__left_or_bottom_page:
                    texture_coord_y_low = 0.0
                    texture_coord_y_high = 0.5
                else:
                    texture_coord_y_low = 0.5
                    texture_coord_y_high = 1.0
            else:
                assert self.__frame_packing == FRAME_PACKING_OVER_AND_UNDER_FULL
                crop_pos_x = (self.__display_resolution_width - in_width) / 2
                crop_pos_y = (self.__display_resolution_height - in_height / 2) / 2
                texture_pos_x = 0
                if self.__left_or_bottom_page:
                    texture_pos_y = 0
                else:
                    texture_pos_y = in_height / 2
                texture_coord_x_low = 0.0
                texture_coord_x_high = 1.0
                texture_coord_y_low = 0.0
                texture_coord_y_high = 1.0
            max_width = in_width
            max_height = in_height
            # gl.glColor(0, 0, 0, 1)
            gl.glPushMatrix()
            gl.glTranslate(
                crop_pos_x - texture_pos_x, max_height + crop_pos_y - texture_pos_y, 0
            )
            gl.glPushMatrix()
            gl.glBegin(gl.GL_QUADS)
            gl.glTexCoord2f(texture_coord_x_low, texture_coord_y_high)
            gl.glVertex(0, -max_height)
            gl.glTexCoord2f(texture_coord_x_low, texture_coord_y_low)
            gl.glVertex(0, 0)
            gl.glTexCoord2f(texture_coord_x_high, texture_coord_y_low)
            gl.glVertex(max_width, 0)
            gl.glTexCoord2f(texture_coord_x_high, texture_coord_y_high)
            gl.glVertex(max_width, -max_height)
            gl.glEnd()

            gl.glPopMatrix()
            gl.glPopMatrix()

            gl.glDisable(gl.GL_TEXTURE_2D)
            # black bars around video resolution to pad to display resolution
            gl.glColor3fv((0, 0, 0))
            gl.glRectf(0, 0, crop_pos_x, self.__display_resolution_height)
            gl.glColor3fv((0, 0, 0))
            gl.glRectf(
                self.__display_resolution_width - crop_pos_x,
                0,
                self.__display_resolution_width,
                self.__display_resolution_height,
            )
            gl.glColor3fv((0, 0, 0))
            gl.glRectf(0, 0, self.__display_resolution_width, crop_pos_y)
            gl.glColor3fv((0, 0, 0))
            gl.glRectf(
                0,
                self.__display_resolution_height - crop_pos_y,
                self.__display_resolution_width,
                self.__display_resolution_height,
            )

            # add black and white boxes then subtitles
            if self.__right_eye in ("right", "top"):
                if self.__left_or_bottom_page:
                    # white_box_offset = white_box_horizontal_offset_1
                    overlay_box = self.__overlay_boxes[0]
                    subtitle_depth_shift = self.__subtitle_depth
                else:
                    # white_box_offset = white_box_horizontal_offset_2
                    overlay_box = self.__overlay_boxes[1]
                    subtitle_depth_shift = -self.__subtitle_depth
            else:
                assert self.__right_eye in ("left", "bottom")
                if self.__left_or_bottom_page:
                    # white_box_offset = white_box_horizontal_offset_2
                    overlay_box = self.__overlay_boxes[1]
                    subtitle_depth_shift = -self.__subtitle_depth
                else:
                    # white_box_offset = white_box_horizontal_offset_1
                    overlay_box = self.__overlay_boxes[0]
                    subtitle_depth_shift = self.__subtitle_depth

            """
            gl.glColor3fv((0, 0, 0))
            gl.glRectf(0, self.__display_resolution_height-black_box_height, black_box_width, self.__display_resolution_height)
            gl.glColor3fv((1, 1, 1))
            gl.glRectf(white_box_offset, self.__display_resolution_height-white_box_height, white_box_offset+white_box_width, self.__display_resolution_height)
            """
            gl.glWindowPos2d(
                0, self.__display_resolution_height - self.__black_box_height
            )
            gl.glDrawPixels(
                self.__black_box_width,
                self.__black_box_height,
                gl.GL_RGBA,
                gl.GL_UNSIGNED_BYTE,
                overlay_box,
            )

            if self.__calibration_mode and self.__show_calibration_instruction_image:
                (
                    calibration_instruction_image_height,
                    calibration_instruction_image_width,
                    _,
                ) = self.__calibration_instruction_image.shape
                gl.glWindowPos2d(
                    (
                        self.__display_resolution_width
                        - calibration_instruction_image_width
                    )
                    // 2,
                    (
                        self.__display_resolution_height
                        - calibration_instruction_image_height
                    )
                    // 2,
                )
                gl.glDrawPixels(
                    calibration_instruction_image_width,
                    calibration_instruction_image_height,
                    gl.GL_RGBA,
                    gl.GL_UNSIGNED_BYTE,
                    self.__calibration_instruction_image,
                )

            if self.__target_frametime is None:
                self.__pg_clock.tick()  # just update the frame time for fps calculations and such
            else:
                # self.__pg_clock.tick(float(self.__target_framerate)) # uses not much cpu but is not accurate at delaying for framerate (this causes chop due to bad timing)
                self.__pg_clock.tick_busy_loop(
                    float(self.__target_framerate)
                )  # uses lots of cpu but is accurate at delaying for framerate

            if self.__latest_subtitle_data:
                self.__latest_subtitles_event.clear()
                for latest_subtitle in self.__latest_subtitles:
                    if (
                        latest_subtitle["start"] <= self.__in_image_play_timestamp
                        and self.__in_image_play_timestamp <= latest_subtitle["end"]
                    ):
                        current_vertical_position = (
                            self.__subtitle_vertical_offset
                            * self.__window_size_scale_factor
                        )
                        for subtitle_line in range(latest_subtitle["text_line_count"]):
                            current_horizontal_position = (
                                (
                                    self.__display_resolution_width
                                    * self.__window_size_scale_factor
                                )
                                - latest_subtitle["rendered_surface"][
                                    subtitle_line
                                ].get_width()
                            ) / 2 + subtitle_depth_shift
                            # print(f'current_horizontal_position {current_horizontal_position} scale_factor {self.__window_size_scale_factor} sub_width {latest_subtitle["rendered_surface"][subtitle_line].get_width()}')
                            for shift_x in range(-1, 2, 2):
                                for shift_y in range(-1, 2, 2):
                                    gl.glWindowPos2d(
                                        current_horizontal_position + shift_x,
                                        current_vertical_position + shift_y,
                                    )
                                    gl.glDrawPixels(
                                        latest_subtitle["rendered_surface_shadow"][
                                            subtitle_line
                                        ].get_width(),
                                        latest_subtitle["rendered_surface_shadow"][
                                            subtitle_line
                                        ].get_height(),
                                        gl.GL_RGBA,
                                        gl.GL_UNSIGNED_BYTE,
                                        latest_subtitle["rendered_data_shadow"][
                                            subtitle_line
                                        ],
                                    )
                            gl.glWindowPos2d(
                                current_horizontal_position, current_vertical_position
                            )
                            gl.glDrawPixels(
                                latest_subtitle["rendered_surface"][
                                    subtitle_line
                                ].get_width(),
                                latest_subtitle["rendered_surface"][
                                    subtitle_line
                                ].get_height(),
                                gl.GL_RGBA,
                                gl.GL_UNSIGNED_BYTE,
                                latest_subtitle["rendered_data"][subtitle_line],
                            )
                            current_vertical_position += latest_subtitle[
                                "rendered_surface"
                            ][subtitle_line].get_height()
                self.__latest_subtitles_event.set()

            loop_time_millis = self.__pg_clock.get_time()
            loop_time = loop_time_millis / 1000
            if loop_time_millis not in self.__debug_loop_times:
                self.__debug_loop_times[loop_time_millis] = 0
            self.__debug_loop_times[loop_time_millis] += 1
            if (
                self.__target_frametime is not None
                and loop_time > self.__target_frametime
                and loop_time % (2 * self.__target_frametime) > self.__target_frametime
            ):
                # if we missed a frame deadline and don't require a page flip then just skip a frame to avoid glasses getting desynced for 4+ frames due to the fact it takes 4-8 frames to resync sony TDG-XXX glasses.
                # pg.time.wait(int(self.__target_frametime - (loop_time % self.__target_frametime))) # not cpu intensie
                # pg.time.delay(int(self.__target_frametime - (loop_time % self.__target_frametime))) # cpu intensive
                # time.sleep(self.__target_frametime - (loop_time % self.__target_frametime)) # best because it allows for more precision on supported operating systems
                # this is easiest done by simulating a frame tick even though we didn't produce an actual frame
                # self.__pg_clock.tick() # just update the frame time for fps calculations and such
                # self.__pg_clock.tick(float(self.__target_framerate)) # uses not much cpu but is not accurate at delaying for framerate (this causes chop due to bad timing)
                self.__pg_clock.tick_busy_loop(
                    float(self.__target_framerate)
                )  # uses lots of cpu but is accurate at delaying for framerate
                # loop_time_millis = self.__pg_clock.get_time()
                # if loop_time_millis not in self.__debug_loop_times:
                #  self.__debug_loop_times[loop_time_millis] = 0
                # self.__debug_loop_times[loop_time_millis] += 1

            pg.display.flip()

            if self.__skip_n_page_flips > 0:
                self.__skip_n_page_flips -= 1
                # print(f'skipped frame {"left" if not self.__left_or_bottom_page else "right"}')
            else:
                self.__left_or_bottom_page = not self.__left_or_bottom_page

        except Exception as e:
            traceback.print_exc()
            logging.error(e)

    @line_profiler_obj
    def run(self):
        while not self.__do_start:
            pass
        self.__start()
        while not self.__do_stop:
            if self.__started:
                self.__update()
                # self.__debug_loop_count += 1
                # if self.__debug_loop_count % 120 == 0:
                #  print(self.__pg_clock.get_fps())
        self.__stop()
        # for loop_time in range(min(max(self.__debug_loop_times.keys()),50)+1):
        #  print(f'{loop_time},{self.__debug_loop_times[loop_time] if loop_time in self.__debug_loop_times else 0}')

    def stop(self):
        self.__do_stop = True

    @property
    def use_separate_process(self):
        return self.__use_separate_process

    @use_separate_process.setter
    def use_separate_process(self, value):
        if value != self.__use_separate_process:
            self.__use_separate_process = value

    @property
    def fullscreen(self):
        return self.__fullscreen

    @fullscreen.setter
    def fullscreen(self, value):
        self.__fullscreen = value
        if (
            self.__pg_window.get_flags() & pg_locals.FULLSCREEN != 0
        ) != self.__fullscreen:
            pg.display.toggle_fullscreen()
            self.__requests = ",".join(
                self.__requests.split(",") + ["set_menu_on_top_true"]
            )
            if not self.__fullscreen:
                pg.mouse.set_visible(True)
                self.__set_menu_on_top_true = True
                self.__set_video_on_top_true = False
            # self.__sdl2_window.focus()
            self.__update_window_scale_factor()

    @property
    def do_fullscreen(self):
        return self.__do_fullscreen

    @do_fullscreen.setter
    def do_fullscreen(self, value):
        self.__do_fullscreen = value

    @property
    def frame_packing(self):
        return self.__frame_packing

    @frame_packing.setter
    def frame_packing(self, value):
        if value != self.__frame_packing:
            self.__frame_packing = value

    @property
    def right_eye(self):
        return self.__right_eye

    @right_eye.setter
    def right_eye(self, value):
        if value != self.__right_eye:
            self.__right_eye = value

    @property
    def target_framerate(self):
        return self.__target_framerate

    @target_framerate.setter
    def target_framerate(self, value):
        if value != self.__target_framerate:
            self.__target_framerate = value
            self.__target_frametime = 1.0 / float(value) if float(value) > 0 else None

    @property
    def display_resolution(self):
        return f"{self.__display_resolution}"

    @display_resolution.setter
    def display_resolution(self, value):
        if value != self.__display_resolution:
            self.__display_resolution = value
            self.__display_resolution_width, self.__display_resolution_height = tuple(
                map(int, value.split("x"))
            )

    @property
    def display_size(self):
        return f"{self.__display_size}"

    @display_size.setter
    def display_size(self, value):
        if value != self.__display_size:
            self.__display_size = value
            self.__pixel_pitch_y = self.__display_resolution_height / (
                int(self.__display_size) * 0.49 * 25.4
            )  # 1.577724862 pixels per mm
            self.__pixel_pitch_x = self.__display_resolution_width / (
                int(self.__display_size) * 0.87 * 25.4
            )  # 1.579739837 pixels per mm

    @property
    def whitebox_brightness(self):
        return f"{self.__whitebox_brightness}"

    @whitebox_brightness.setter
    def whitebox_brightness(self, value):
        if value != self.__whitebox_brightness:
            self.__whitebox_brightness = int(value)

    @property
    def whitebox_vertical_position(self):
        return f"{self.__whitebox_vertical_position}"

    @whitebox_vertical_position.setter
    def whitebox_vertical_position(self, value):
        if value != self.__whitebox_vertical_position:
            self.__whitebox_vertical_position = int(value)

    @property
    def whitebox_horizontal_spacing(self):
        return f"{self.__whitebox_horizontal_spacing}"

    @whitebox_horizontal_spacing.setter
    def whitebox_horizontal_spacing(self, value):
        if value != self.__whitebox_horizontal_spacing:
            self.__whitebox_horizontal_spacing = int(value)

    @property
    def requests(self):
        return self.__requests

    @requests.setter
    def requests(self, value):
        if value == "":
            self.__requests = ""

    @property
    def latest_subtitle_data(self):
        return self.__latest_subtitle_data

    @latest_subtitle_data.setter
    def latest_subtitle_data(self, value):
        if value != self.__latest_subtitle_data:
            self.__latest_subtitle_data = value
            # print(value)
            parsed_data = json.loads(value)
            if self.__latest_subtitles_event.wait(
                0.2
            ):  # if we don't get a signal within 200ms just drop the subtitle and carry on
                self.__latest_subtitles.append(
                    {
                        "start": parsed_data["start"],
                        "end": parsed_data["start"] + parsed_data["duration"],
                        "text": parsed_data["text"],
                    }
                )
                if len(self.__latest_subtitles) > 5:
                    self.__latest_subtitles.popleft()
                self.__update_subtitle_surface_and_data()
            # print(f"pts:{self.__in_image_play_timestamp} b:{self.__latest_subtitles[-1]['start']} e:{self.__latest_subtitles[-1]['end']} {self.__latest_subtitles[-1]['text']}")

    @property
    def subtitle_font(self):
        return self.__subtitle_font

    @subtitle_font.setter
    def subtitle_font(self, value):
        if value != self.__subtitle_font:
            self.__subtitle_font = value
            self.__update_subtitle_fonts()

    @property
    def subtitle_size(self):
        return str(self.__subtitle_size)

    @subtitle_size.setter
    def subtitle_size(self, value):
        if value != self.__subtitle_size:
            self.__subtitle_size = int(value)
            self.__update_subtitle_fonts()

    @property
    def subtitle_depth(self):
        return str(self.__subtitle_depth)

    @subtitle_depth.setter
    def subtitle_depth(self, value):
        if value != self.__subtitle_depth:
            self.__subtitle_depth = int(value)

    @property
    def subtitle_vertical_offset(self):
        return str(self.__subtitle_vertical_offset)

    @subtitle_vertical_offset.setter
    def subtitle_vertical_offset(self, value):
        if value != self.__subtitle_vertical_offset:
            self.__subtitle_vertical_offset = int(value)

    @property
    def skip_n_page_flips(self):
        return str(self.__skip_n_page_flips)

    @skip_n_page_flips.setter
    def skip_n_page_flips(self, value):
        if value != self.__skip_n_page_flips:
            self.__skip_n_page_flips = int(value)

    @property
    def calibration_mode(self):
        return self.__calibration_mode

    @calibration_mode.setter
    def calibration_mode(self, value):
        if value != self.__calibration_mode:
            self.__calibration_mode = value

    def update_image(self, play_timestamp, in_image, in_image_width, in_image_height):
        self.__in_image = in_image
        # self.__in_image = in_image.tobytes()
        self.__in_image_width = in_image_width
        self.__in_image_height = in_image_height
        self.__in_image_updated = True
        self.__in_image_play_timestamp = play_timestamp

        if not self.__started:
            self.__do_start = True

        # we need to wait for the copy to finish before we return and release the GstBuffer memoryview that we are loading
        self.__finish_buffer_copy_event.wait(timeout=FINISH_BUFFER_COPY_EVENT_TIMEOUT)
        self.__finish_buffer_copy_event.clear()


class PageflipGLWindowProcess(multiprocessing.Process):
    def __init__(self):
        super(PageflipGLWindowProcess, self).__init__()
        self.__lock = multiprocessing.Lock()
        self.__do_stop = multiprocessing.sharedctypes.Value(
            ctypes.c_bool, False, lock=self.__lock
        )
        self.__use_separate_process = multiprocessing.sharedctypes.Value(
            ctypes.c_bool, True, lock=self.__lock
        )
        self.__fullscreen = multiprocessing.sharedctypes.Value(
            ctypes.c_bool, False, lock=self.__lock
        )
        self.__do_fullscreen = multiprocessing.sharedctypes.Value(
            ctypes.c_bool, False, lock=self.__lock
        )
        self.__frame_packing = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock) # broken see https://stackoverflow.com/questions/76440266/python-shared-memory-string-variable-synchronizedarray-has-no-attribute-value and https://github.com/python/typeshed/issues/8799#issuecomment-1285897528
        self.__frame_packing.value = "side-by-side"
        self.__right_eye = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__right_eye.value = "right"
        self.__target_framerate = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__target_framerate.value = "0"
        self.__display_resolution = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__display_resolution.value = "1920x1080"
        self.__display_size = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__display_size.value = "55"
        self.__whitebox_brightness = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__whitebox_brightness.value = "255"
        self.__whitebox_vertical_position = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__whitebox_vertical_position.value = "0"
        self.__whitebox_horizontal_spacing = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__whitebox_horizontal_spacing.value = "23"
        self.__requests = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 65536
        )  # , lock=self.__lock)
        self.__requests.value = ""
        self.__latest_subtitle_data = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 65536
        )  # , lock=self.__lock)
        self.__latest_subtitle_data.value = ""
        self.__subtitle_font = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 1024
        )  # , lock=self.__lock)
        self.__subtitle_font.value = "ariel"
        self.__subtitle_size = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__subtitle_size.value = "30"
        self.__subtitle_depth = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__subtitle_depth.value = "0"
        self.__subtitle_vertical_offset = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__subtitle_vertical_offset.value = "150"
        self.__skip_n_page_flips = multiprocessing.sharedctypes.RawArray(
            ctypes.c_wchar, 64
        )  # , lock=self.__lock)
        self.__skip_n_page_flips.value = "0"
        self.__calibration_mode = multiprocessing.sharedctypes.Value(
            ctypes.c_bool, False, lock=self.__lock
        )

        self.__in_image_updated = multiprocessing.sharedctypes.Value(
            ctypes.c_bool, False, lock=self.__lock
        )
        self.__in_image_width = multiprocessing.sharedctypes.Value(
            ctypes.c_longlong, 0, lock=self.__lock
        )
        self.__in_image_height = multiprocessing.sharedctypes.Value(
            ctypes.c_longlong, 0, lock=self.__lock
        )
        self.__in_image_play_timestamp = multiprocessing.sharedctypes.Value(
            ctypes.c_longlong, 0, lock=self.__lock
        )
        self.__in_image = multiprocessing.shared_memory.SharedMemory(
            create=True, size=20000000
        )  # 20 Megabytes should be big enough for all 1080p displays

    def run(self):
        process = psutil.Process(os.getpid())
        if os.name == "nt":
            process.nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            pass  # commented out for now as you need root to set permissions on my system
            # process.nice(-20)
        pageflip_gl_window = PageflipGLWindow()
        started = False
        last_do_fullscreen = self.__do_fullscreen.value
        last_requests = self.__requests.value
        last_latest_subtitle_data = self.__latest_subtitle_data.value
        last_skip_n_page_flips = self.__skip_n_page_flips.value
        while not self.__do_stop.value:
            if pageflip_gl_window.fullscreen != self.__fullscreen.value:
                self.__fullscreen.value = pageflip_gl_window.fullscreen
            if self.__do_fullscreen.value != last_do_fullscreen:
                last_do_fullscreen = self.__do_fullscreen.value
                pageflip_gl_window.do_fullscreen = self.__do_fullscreen.value
            if pageflip_gl_window.frame_packing != self.__frame_packing.value:
                pageflip_gl_window.frame_packing = self.__frame_packing.value
            if pageflip_gl_window.right_eye != self.__right_eye.value:
                pageflip_gl_window.right_eye = self.__right_eye.value
            if pageflip_gl_window.target_framerate != self.__target_framerate.value:
                pageflip_gl_window.target_framerate = self.__target_framerate.value
            if pageflip_gl_window.display_resolution != self.__display_resolution.value:
                pageflip_gl_window.display_resolution = self.__display_resolution.value
            if pageflip_gl_window.display_size != self.__display_size.value:
                pageflip_gl_window.display_size = self.__display_size.value
            if (
                pageflip_gl_window.whitebox_brightness
                != self.__whitebox_brightness.value
            ):
                pageflip_gl_window.whitebox_brightness = (
                    self.__whitebox_brightness.value
                )
            if (
                pageflip_gl_window.whitebox_vertical_position
                != self.__whitebox_vertical_position.value
            ):
                pageflip_gl_window.whitebox_vertical_position = (
                    self.__whitebox_vertical_position.value
                )
            if (
                pageflip_gl_window.whitebox_horizontal_spacing
                != self.__whitebox_horizontal_spacing.value
            ):
                pageflip_gl_window.whitebox_horizontal_spacing = (
                    self.__whitebox_horizontal_spacing.value
                )
            if pageflip_gl_window.requests != last_requests:
                last_requests = pageflip_gl_window.requests
                self.__requests.value = pageflip_gl_window.requests
            elif pageflip_gl_window.requests != self.__requests.value:
                pageflip_gl_window.requests = self.__requests.value
            if pageflip_gl_window.latest_subtitle_data != last_latest_subtitle_data:
                last_latest_subtitle_data = pageflip_gl_window.latest_subtitle_data
                self.__latest_subtitle_data.value = (
                    pageflip_gl_window.latest_subtitle_data
                )
            elif (
                pageflip_gl_window.latest_subtitle_data
                != self.__latest_subtitle_data.value
            ):
                pageflip_gl_window.latest_subtitle_data = (
                    self.__latest_subtitle_data.value
                )
            if pageflip_gl_window.subtitle_font != self.__subtitle_font.value:
                pageflip_gl_window.subtitle_font = self.__subtitle_font.value
            if pageflip_gl_window.subtitle_size != self.__subtitle_size.value:
                pageflip_gl_window.subtitle_size = self.__subtitle_size.value
            if pageflip_gl_window.subtitle_depth != self.__subtitle_depth.value:
                pageflip_gl_window.subtitle_depth = self.__subtitle_depth.value
            if (
                pageflip_gl_window.subtitle_vertical_offset
                != self.__subtitle_vertical_offset.value
            ):
                pageflip_gl_window.subtitle_vertical_offset = (
                    self.__subtitle_vertical_offset.value
                )
            if pageflip_gl_window.skip_n_page_flips != last_skip_n_page_flips:
                last_skip_n_page_flips = pageflip_gl_window.skip_n_page_flips
                self.__skip_n_page_flips.value = pageflip_gl_window.skip_n_page_flips
            elif pageflip_gl_window.skip_n_page_flips != self.__skip_n_page_flips.value:
                pageflip_gl_window.skip_n_page_flips = self.__skip_n_page_flips.value
            if pageflip_gl_window.calibration_mode != self.__calibration_mode.value:
                pageflip_gl_window.calibration_mode = self.__calibration_mode.value
            if not started:
                pageflip_gl_window.start()
                started = True
            if self.__in_image_updated.value:
                pageflip_gl_window.update_image(
                    self.__in_image_play_timestamp.value,
                    self.__in_image.buf,
                    self.__in_image_width.value,
                    self.__in_image_height.value,
                )
                self.__in_image_updated.value = False
            time.sleep(0.001)
        pageflip_gl_window.stop()
        self.__in_image.close()
        self.__in_image.unlink()

    def stop(self):
        self.__do_stop.value = True

    @property
    def use_separate_process(self):
        return self.__use_separate_process.value

    @use_separate_process.setter
    def use_separate_process(self, value):
        self.__use_separate_process.value = value

    @property
    def fullscreen(self):
        return self.__fullscreen.value

    @fullscreen.setter
    def fullscreen(self, value):
        self.__fullscreen.value = value

    @property
    def do_fullscreen(self):
        return self.__do_fullscreen.value

    @do_fullscreen.setter
    def do_fullscreen(self, value):
        self.__do_fullscreen.value = value

    @property
    def frame_packing(self):
        return self.__frame_packing.value

    @frame_packing.setter
    def frame_packing(self, value):
        self.__frame_packing.value = value

    @property
    def right_eye(self):
        return self.__right_eye.value

    @right_eye.setter
    def right_eye(self, value):
        self.__right_eye.value = value

    @property
    def target_framerate(self):
        return self.__target_framerate.value

    @target_framerate.setter
    def target_framerate(self, value):
        self.__target_framerate.value = value

    @property
    def display_resolution(self):
        return self.__display_resolution.value

    @display_resolution.setter
    def display_resolution(self, value):
        self.__display_resolution.value = value

    @property
    def display_size(self):
        return self.__display_size.value

    @display_size.setter
    def display_size(self, value):
        self.__display_size.value = value

    @property
    def whitebox_brightness(self):
        return self.__whitebox_brightness.value

    @whitebox_brightness.setter
    def whitebox_brightness(self, value):
        self.__whitebox_brightness.value = value

    @property
    def whitebox_vertical_position(self):
        return self.__whitebox_vertical_position.value

    @whitebox_vertical_position.setter
    def whitebox_vertical_position(self, value):
        self.__whitebox_vertical_position.value = value

    @property
    def whitebox_horizontal_spacing(self):
        return self.__whitebox_horizontal_spacing.value

    @whitebox_horizontal_spacing.setter
    def whitebox_horizontal_spacing(self, value):
        self.__whitebox_horizontal_spacing.value = value

    @property
    def requests(self):
        return self.__requests.value

    @requests.setter
    def requests(self, value):
        self.__requests.value = value

    @property
    def latest_subtitle_data(self):
        return self.__latest_subtitle_data.value

    @latest_subtitle_data.setter
    def latest_subtitle_data(self, value):
        self.__latest_subtitle_data.value = value

    @property
    def subtitle_font(self):
        return self.__subtitle_font.value

    @subtitle_font.setter
    def subtitle_font(self, value):
        self.__subtitle_font.value = value

    @property
    def subtitle_size(self):
        return self.__subtitle_size.value

    @subtitle_size.setter
    def subtitle_size(self, value):
        self.__subtitle_size.value = value

    @property
    def subtitle_depth(self):
        return self.__subtitle_depth.value

    @subtitle_depth.setter
    def subtitle_depth(self, value):
        self.__subtitle_depth.value = value

    @property
    def subtitle_vertical_offset(self):
        return self.__subtitle_vertical_offset.value

    @subtitle_vertical_offset.setter
    def subtitle_vertical_offset(self, value):
        self.__subtitle_vertical_offset.value = value

    @property
    def skip_n_page_flips(self):
        return self.__skip_n_page_flips.value

    @skip_n_page_flips.setter
    def skip_n_page_flips(self, value):
        self.__skip_n_page_flips.value = value

    @property
    def calibration_mode(self):
        return self.__calibration_mode.value

    @calibration_mode.setter
    def calibration_mode(self, value):
        self.__calibration_mode.value = value

    def update_image(self, play_timestamp, in_image, in_image_width, in_image_height):
        self.__in_image.buf[: len(in_image)] = in_image[:]
        # self.__in_image = in_image.tobytes()
        self.__in_image_width.value = in_image_width
        self.__in_image_height.value = in_image_height
        self.__in_image_updated.value = True
        self.__in_image_play_timestamp.value = play_timestamp


# """
class GstPageflipGLSink(GstBase.BaseSink):

    GST_PLUGIN_NAME = "gstpageflipglsink"

    __gstmetadata__ = (
        "PageflipGLSink",
        "Sink",
        "Page Flip GL SBS Stereo Sink",
        "Peter",
    )

    __gsttemplates__ = Gst.PadTemplate.new(
        "sink", Gst.PadDirection.SINK, Gst.PadPresence.ALWAYS, IN_CAPS
    )

    __gproperties__ = {
        "use_separate_process": (
            GObject.TYPE_BOOLEAN,
            "Use Separate Process",
            "Use separate process for page flipping thread (requires more CPU and memory copies but can reduce eye resynchronization problems)",
            True,  # default
            GObject.ParamFlags.READWRITE,
        ),
        "fullscreen": (
            GObject.TYPE_BOOLEAN,
            "Fullscreen",
            "Change the players fullscreen property",
            False,  # default
            GObject.ParamFlags.READWRITE,
        ),
        "frame_packing": (
            GObject.TYPE_STRING,
            "Frame Packing",
            "Frame packing (side-by-side-half, side-by-side-full, over-and-under-half, over-and-under-full)",
            "side-by-side",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "right_eye": (
            GObject.TYPE_STRING,
            "Right Eye",
            "Right Eye Location (left, right, top, bottom)",
            "right",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "target_framerate": (
            GObject.TYPE_STRING,
            "Target Framerate",
            "If any positive float number this is the framerate used to swap eyes at, if 0 then swap every frame irregarless.",
            "0",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "display_resolution": (
            GObject.TYPE_STRING,
            "Display Resolution",
            "Resolution of the display (eg 1920x1080)",
            "1920x1080",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "display_size": (
            GObject.TYPE_STRING,
            "Display Size",
            "Size of the display in inches (eg 55)",
            "1920x1080",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "whitebox_brightness": (
            GObject.TYPE_STRING,
            "Whitebox Brightness",
            "The relative brightness of the whitebox used for sensor triggering from 0 to 255 (255 being the brightest)",
            "255",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "whitebox_vertical_position": (
            GObject.TYPE_STRING,
            "Whitebox Vertical Position",
            "The whitebox vertical position lets the user move the screen based whitebox down to better align with the 3d emitter tv mount they have. It is an arbitrary measurement and has only relative meaning.",
            "0",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "whitebox_horizontal_spacing": (
            GObject.TYPE_STRING,
            "Whitebox Horizontal Spacing",
            "The whitebox horizontal spacing lets the user increase/decrease the separation between white boxes to better align with the 3d emitter and tv pixel pitch they have. It is an arbitrary measurement and has only relative meaning.",
            "0",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "start": (
            GObject.TYPE_BOOLEAN,
            "Start",
            "Start the player (last action after configuration properties have been set)",
            False,  # default
            GObject.ParamFlags.WRITABLE,
        ),
        "close": (
            GObject.TYPE_BOOLEAN,
            "Close",
            "Close the player (can only be used after starting)",
            False,  # default
            GObject.ParamFlags.WRITABLE,
        ),
        "requests": (
            GObject.TYPE_STRING,
            "Requests",
            "Request from filter to parent app as csv list (can only be used after starting)",
            "",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "latest_subtitle_data": (
            GObject.TYPE_STRING,
            "Latest Subtitle Data",
            "Latest subtitle data as json object (can only be used after starting)",
            "",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "subtitle_font": (
            GObject.TYPE_STRING,
            "Subtitle Font",
            "Font to render subtitles if present",
            "arial",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "subtitle_size": (
            GObject.TYPE_STRING,
            "Subtitle Size",
            "Size to render subtitles if present",
            "30",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "subtitle_depth": (
            GObject.TYPE_STRING,
            "Subtitle Depth",
            "Depth to render subtitles if present (positive is in-front, negative behind)",
            "0",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "subtitle_vertical_offset": (
            GObject.TYPE_STRING,
            "Subtitle Vertical Offset",
            "Vertial offset for subtitles from bottom of screen",
            "150",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "skip_n_page_flips": (
            GObject.TYPE_STRING,
            "Skip N Page Flips",
            "Skip the next N page flips starting immediately (can only be used after starting)",
            "0",  # default
            GObject.ParamFlags.READWRITE,
        ),
        "calibration_mode": (
            GObject.TYPE_BOOLEAN,
            "Calibration Mode",
            "Shows reticule to help aligning sensor bar as well as on screen instructions to assist with timing adjustment.",
            False,  # default
            GObject.ParamFlags.READWRITE,
        ),
    }

    def __init__(self):
        super(GstPageflipGLSink, self).__init__()
        self.__started = False
        self.__use_separate_process = True
        self.__parameters = {
            "fullscreen": False,
            "frame-packing": "side-by-side",
            "right-eye": "right",
            "target-framerate": "0",
            "display-resolution": "1920x1080",
            "display-size": "55",
            "whitebox-brightness": "255",
            "whitebox-vertical-position": "0",
            "whitebox-horizontal-spacing": "23",
            "whitebox-brightness": "255",
            "requests": "",
            "latest-subtitle-data": "",
            "subtitle_font": "arial",
            "subtitle_size": "30",
            "subtitle_depth": "0",
            "subtitle_vertical_offset": "150",
            "skip_n_page_flips": "0",
            "calibration_mode": False,
        }

    def do_get_property(self, prop: GObject.GParamSpec):
        if not self.__started:
            if prop.name == "use-separate-process":
                return self.__use_separate_process
            elif prop.name in self.__parameters:
                return self.__parameters[prop.name]
            else:
                raise AttributeError("unknown property %s" % prop.name)
        else:
            if prop.name == "use-separate-process":
                return self.__pageflip_gl_window.use_separate_process
            elif prop.name == "fullscreen":
                return self.__pageflip_gl_window.fullscreen
            elif prop.name == "frame-packing":
                return self.__pageflip_gl_window.frame_packing
            elif prop.name == "right-eye":
                return self.__pageflip_gl_window.right_eye
            elif prop.name == "target-framerate":
                return self.__pageflip_gl_window.target_framerate
            elif prop.name == "display-resolution":
                return self.__pageflip_gl_window.display_resolution
            elif prop.name == "display-size":
                return self.__pageflip_gl_window.display_size
            elif prop.name == "whitebox-brightness":
                return self.__pageflip_gl_window.whitebox_brightness
            elif prop.name == "whitebox-vertical-position":
                return self.__pageflip_gl_window.whitebox_vertical_position
            elif prop.name == "whitebox-horizontal-spacing":
                return self.__pageflip_gl_window.whitebox_horizontal_spacing
            elif prop.name == "requests":
                return self.__pageflip_gl_window.requests
            elif prop.name == "latest-subtitle-data":
                return self.__pageflip_gl_window.latest_subtitle_data
            elif prop.name == "subtitle-font":
                return self.__pageflip_gl_window.subtitle_font
            elif prop.name == "subtitle-size":
                return self.__pageflip_gl_window.subtitle_size
            elif prop.name == "subtitle-depth":
                return self.__pageflip_gl_window.subtitle_depth
            elif prop.name == "subtitle-vertical-offset":
                return self.__pageflip_gl_window.subtitle_vertical_offset
            elif prop.name == "skip-n-page-flips":
                return self.__pageflip_gl_window.skip_n_page_flips
            elif prop.name == "calibration-mode":
                return self.__pageflip_gl_window.calibration_mode
            else:
                raise AttributeError("unknown property %s" % prop.name)

    def do_set_property(self, prop: GObject.GParamSpec, value):
        if not self.__started:
            if prop.name == "use-separate-process":
                self.__use_separate_process = value
            elif prop.name in (
                "fullscreen",
                "frame-packing",
                "right-eye",
                "target-framerate",
                "display-resolution",
                "display-size",
                "whitebox-brightness",
                "whitebox-vertical-position",
                "whitebox-horizontal-spacing",
                "whitebox-brightness",
                "requests",
                "latest-subtitle-data",
                "subtitle-font",
                "subtitle-size",
                "subtitle-depth",
                "subtitle-vertical-offset",
                "calibration-mode",
            ):
                self.__parameters[prop.name] = value
            elif prop.name == "start" and value:
                if not self.__use_separate_process:
                    self.__pageflip_gl_window = PageflipGLWindow()
                else:
                    self.__pageflip_gl_window = PageflipGLWindowProcess()
                self.__pageflip_gl_window.use_separate_process = (
                    self.__use_separate_process
                )
                for prop_name in self.__parameters:
                    if prop_name == "fullscreen":
                        self.__pageflip_gl_window.do_fullscreen = self.__parameters[
                            prop_name
                        ]
                    else:
                        prop_name_fixed = prop_name.replace("-", "_")
                        setattr(
                            self.__pageflip_gl_window,
                            prop_name_fixed,
                            self.__parameters[prop_name],
                        )
                self.__pageflip_gl_window.start()
                self.__started = True
            else:
                raise AttributeError("unknown property %s" % prop.name)
        else:
            if prop.name == "fullscreen":
                self.__pageflip_gl_window.do_fullscreen = value
            elif prop.name == "frame-packing":
                self.__pageflip_gl_window.frame_packing = value
            elif prop.name == "right-eye":
                self.__pageflip_gl_window.right_eye = value
            elif prop.name == "target-framerate":
                self.__pageflip_gl_window.target_framerate = value
            elif prop.name == "display-resolution":
                self.__pageflip_gl_window.display_resolution = value
            elif prop.name == "display-size":
                self.__pageflip_gl_window.display_size = value
            elif prop.name == "whitebox-brightness":
                self.__pageflip_gl_window.whitebox_brightness = value
            elif prop.name == "whitebox-vertical-position":
                self.__pageflip_gl_window.whitebox_vertical_position = value
            elif prop.name == "whitebox-horizontal-spacing":
                self.__pageflip_gl_window.whitebox_horizontal_spacing = value
            elif prop.name == "close" and value:
                self.__pageflip_gl_window.stop()
                if self.__use_separate_process:
                    self.__pageflip_gl_window.join()  # may not be necessary
            elif prop.name == "requests":
                self.__pageflip_gl_window.requests = value
            elif prop.name == "latest-subtitle-data":
                self.__pageflip_gl_window.latest_subtitle_data = value
            elif prop.name == "subtitle-font":
                self.__pageflip_gl_window.subtitle_font = value
            elif prop.name == "subtitle-size":
                self.__pageflip_gl_window.subtitle_size = value
            elif prop.name == "subtitle-depth":
                self.__pageflip_gl_window.subtitle_depth = value
            elif prop.name == "subtitle-vertical-offset":
                self.__pageflip_gl_window.subtitle_vertical_offset = value
            elif prop.name == "skip-n-page-flips":
                self.__pageflip_gl_window.skip_n_page_flips = value
            elif prop.name == "calibration-mode":
                self.__pageflip_gl_window.calibration_mode = value
            else:
                raise AttributeError("unknown property %s" % prop.name)

    def do_render(self, inbuffer: Gst.Buffer) -> Gst.FlowReturn:
        "https://gstreamer.freedesktop.org/documentation/base/gstbasesink.html?gi-language=python#GstBaseSinkClass::render"

        try:
            # print((inbuffer.get_size(), outbuffer.get_size()))
            # in_struct = self.sinkpad.get_current_caps().get_structure(0)
            # out_struct = self.srcpad.get_current_caps().get_structure(0)
            # print(((in_struct.get_value("width"), in_struct.get_value("height")),(out_struct.get_value("width"), out_struct.get_value("height"))))
            # GstVideoFrame

            # convert Gst.Buffer to np.ndarray
            # self.__pageflip_gl_window.update_image(inbuffer.pts, gstreamer_utils.gst_buffer_with_caps_to_ndarray(inbuffer, self.sinkpad.get_current_caps())) # we may need to clone it so we don't lock the Gst.Buffer
            # convert Gst.Buffer to bytes and get dimensions
            with gstreamer_utils.gst_buffer_with_caps_to_bytes_and_size(
                inbuffer, self.sinkpad.get_current_caps()
            ) as (in_image, in_image_width, in_image_height):
                self.__pageflip_gl_window.update_image(
                    inbuffer.pts, in_image, in_image_width, in_image_height
                )  # we may need to clone it so we don't lock the Gst.Buffer

        except Exception as e:
            traceback.print_exc()
            logging.error(e)

        return Gst.FlowReturn.OK

    def do_set_caps(self, caps: Gst.Caps) -> bool:

        self.__in_width, self.__in_height = [
            caps.get_structure(0).get_value(v) for v in ["width", "height"]
        ]

        return True


# Register plugin to use it from command line
GObject.type_register(GstPageflipGLSink)
__gstelementfactory__ = (
    GstPageflipGLSink.GST_PLUGIN_NAME,
    Gst.Rank.NONE,
    GstPageflipGLSink,
)

# """

# """
if __name__ == "__main__":
    pageflip_gl_window = PageflipGLWindow()
    pageflip_gl_window.use_separate_process = True
    pageflip_gl_window.display_resolution = resolution
    pageflip_gl_window.display_size = "34"
    pageflip_gl_window.right_eye = "left"
    pageflip_gl_window.frame_packing = FRAME_PACKING_SIDE_BY_SIDE_HALF
    # pageflip_gl_window.frame_packing = FRAME_PACKING_SIDE_BY_SIDE_FULL
    # pageflip_gl_window.frame_packing = FRAME_PACKING_OVER_AND_UNDER_HALF
    # pageflip_gl_window.frame_packing = FRAME_PACKING_OVER_AND_UNDER_FULL
    pageflip_gl_window.start()
    test_image = pg.image.load("sbs_half_1080_1920_sample.png")
    # test_image = pg.image.load("sbs_full_1080_1920_sample.png")
    # test_image = pg.image.load("oau_half_1080_1920_sample.png")
    # test_image = pg.image.load("oau_full_1080_1920_sample.png")
    test_image_rgb = pg.surfarray.array3d(test_image)
    test_image_alpha = pg.surfarray.array_alpha(test_image).reshape(
        (*test_image_rgb.shape[0:2], 1)
    )
    test_image_rgba = np.concatenate((test_image_rgb, test_image_alpha), 2)
    test_image_np_bytes = test_image_rgba.transpose((1, 0, 2)).tobytes()
    test_image_pg_surface_bytes = pg.image.tostring(test_image, "RGBA", False)
    pageflip_gl_window.update_image(
        0,
        memoryview(test_image_rgba.tobytes()),
        test_image_rgb.shape[1],
        test_image_rgb.shape[0],
    )
    time.sleep(120)
    pageflip_gl_window.stop()
# """
