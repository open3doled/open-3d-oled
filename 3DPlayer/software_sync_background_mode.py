import ctypes
import logging
import os
import threading
import time
import traceback

import psutil
from pygame import _sdl2 as pygame_sdl2
from pygame import locals as pg_locals
from pynput import keyboard

import OpenGL.GL as gl
import pygame as pg

if os.name == "nt":
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
                
WINDOW_NAME = "Open3DOLED3DSoftwareSyncBackgroundModeWindow"
SYNC_SIGNAL_LEFT = 1
SYNC_SIGNAL_RIGHT = 2

WINDOWS_OS_NAME = "nt"
# WINDOWS_OS_NAME = "posix"

USE_LINE_PROFILER = True
if USE_LINE_PROFILER:
    from line_profiler import LineProfiler

    line_profiler_obj = LineProfiler()
else:

    def line_profiler_obj(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    
class SoftwareSyncBackgroundModeGLWindow(threading.Thread):

    def __init__(self, synced_flip_event_callback, target_framerate):
        super(SoftwareSyncBackgroundModeGLWindow, self).__init__()
        self.__synced_flip_event_callback = synced_flip_event_callback
        self.__started = False
        self.__do_stop = False
        self.__time_started = None
        self.__left_or_bottom_page = True
        self.__target_framerate = target_framerate
        self.__target_frametime = (
            1.0 / float(target_framerate) if float(target_framerate) > 0 else None
        )
        self.__display_resolution_width = 200
        self.__display_resolution_height = 100
        self.__keyboard_listener = None
        self.__flip_eyes = False
        self.__ctrl_pressed = False
        self.__shift_pressed = False
        self.__trigger_pixel_brightness = 0
        self.__trigger_pixel_last_brightness = 0
        self.__hdc = None
        
        self.__cycle_count = 0
        self.__last_time = 0
        
        pg.init()

    def __start(self):
        p = psutil.Process(os.getpid())
        if os.name == WINDOWS_OS_NAME:
            p.nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            p.nice(10)

        flags = pg_locals.DOUBLEBUF | pg_locals.OPENGL | pg_locals.RESIZABLE
        self.__pg_clock = pg.time.Clock()
        self.__pg_window = pg.display.set_mode(
            (self.__display_resolution_width, self.__display_resolution_height),
            flags,
            vsync=1,
        )

        pg.display.set_caption(WINDOW_NAME)
        pg.display.set_icon(
            pg.image.load(
                os.path.join(os.path.dirname(__file__), "python", "blank.ico")
            )
        )

        self.__sdl2_window = pygame_sdl2.Window.from_display_module()
        self.__sdl2_window.size = (
            self.__display_resolution_width,
            self.__display_resolution_height,
        )
        self.__sdl2_window.position = pygame_sdl2.WINDOWPOS_CENTERED

        def minimize_window():
            if os.name == WINDOWS_OS_NAME:
                hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_NAME)
                SW_MINIMIZE = 6
                ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
            else:
                self.__sdl2_window.minimize()
            # timer = threading.Timer(2, minimize_window)
            # timer.start()

        timer = threading.Timer(1, minimize_window)
        timer.start()

        gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
        # gl.glEnable(gl.GL_DEPTH_TEST) # we are disabling this for now because the texture z depth and overlay elements aren't configured right yet.
        gl.glEnable(gl.GL_BLEND)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnable(gl.GL_TEXTURE_2D)
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

        if self.__keyboard_listener is None:
            self.__keyboard_listener = keyboard.Listener(
                on_press=self.on_key_press, on_release=self.on_key_release
            )
            self.__keyboard_listener.start()

        if os.name == WINDOWS_OS_NAME:
            self.__hdc = user32.GetDC(0)  # entire desktop

        self.__started = True
        self.__time_started = time.perf_counter()

    def __stop(self):

        if os.name == WINDOWS_OS_NAME:
            user32.ReleaseDC(0, self.__hdc)
            self.__hdc = None
                
        if self.__keyboard_listener is not None:
            self.__keyboard_listener.stop()
            self.__keyboard_listener = None

        self.__pg_window = None
        self.__sdl2_window = None
        pg.quit()
        
        if USE_LINE_PROFILER:
            line_profiler_obj.print_stats()
        
    @line_profiler_obj
    def __update(self):
        try:

            pg.display.flip()
            
            if True and os.name == WINDOWS_OS_NAME:
                color = gdi32.GetPixel(self.__hdc, 0, 0)
                r = color & 0xFF
                g = (color >> 8) & 0xFF
                b = (color >> 16) & 0xFF
                self.__trigger_pixel_last_brightness = self.__trigger_pixel_brightness
                self.__trigger_pixel_brightness = r + g + b
                self.__left_or_bottom_page = (self.__trigger_pixel_last_brightness > self.__trigger_pixel_brightness)
            else:
                if self.__target_frametime is not None:
                    time_delta = time.perf_counter() - self.__time_started
                    frame_type_modulus = (time_delta / self.__target_frametime) % 2
                    if frame_type_modulus <= 1.0:
                        self.__left_or_bottom_page = True
                    else:
                        self.__left_or_bottom_page = False    
                else:
                    self.__left_or_bottom_page = not self.__left_or_bottom_page
            
            if self.__flip_eyes:
                new_sync_value = (
                    SYNC_SIGNAL_RIGHT
                    if self.__left_or_bottom_page
                    else SYNC_SIGNAL_LEFT
                )
            else:
                new_sync_value = (
                    SYNC_SIGNAL_LEFT
                    if self.__left_or_bottom_page
                    else SYNC_SIGNAL_RIGHT
                )
                
            self.__synced_flip_event_callback(new_sync_value)

            self.__cycle_count += 1
            now_time = int(time.time())
            if now_time > self.__last_time:
                self.__last_time = now_time
                print(f"{self.__last_time} {self.__cycle_count}")
                self.__cycle_count = 0

        except Exception as e:
            traceback.print_exc()
            logging.error(e)

    def run(self):
        if not self.__do_stop:
            self.__start()
        while not self.__do_stop:
            if self.__started:
                self.__update()
        self.__stop()

    def stop(self):
        self.__do_stop = True

    def on_key_press(self, key):
        try:
            # print(key)
            if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self.__ctrl_pressed = True
            elif key == keyboard.Key.shift:
                self.__shift_pressed = True
            elif (
                (key.char == "F" or key.char == "f" or key.char == "\x06")
                and self.__ctrl_pressed
                and self.__shift_pressed
            ):
                self.__flip_eyes = not self.__flip_eyes
                print("Flipped Eyes for Software Sync Background Mode")
        except AttributeError:
            pass

    def on_key_release(self, key):
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.__ctrl_pressed = False
        elif key == keyboard.Key.shift:
            self.__shift_pressed = False

    @property
    def target_framerate(self):
        return self.__target_framerate

    @target_framerate.setter
    def target_framerate(self, value):
        if value != self.__target_framerate:
            self.__target_framerate = value
            self.__target_frametime = 1.0 / float(value) if float(value) > 0 else None


if __name__ == "__main__":

    def synced_flip_event_callback_temp(left_or_right_synced_flip):
        if left_or_right_synced_flip == SYNC_SIGNAL_LEFT:
            pass
            # print("L", end="")
        elif left_or_right_synced_flip == SYNC_SIGNAL_RIGHT:
            pass
            # print("R", end="")

    software_sync_background_mode_gl_window = SoftwareSyncBackgroundModeGLWindow(
        synced_flip_event_callback_temp
    )
    software_sync_background_mode_gl_window.start()
    time.sleep(15)
    software_sync_background_mode_gl_window.stop()
