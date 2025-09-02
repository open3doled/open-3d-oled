import glfw
import ctypes
import logging
import os
import threading
import time
import traceback

from pynput import keyboard

import OpenGL.GL as gl


WINDOW_NAME = "Open3DOLED3DSoftwareSyncBackgroundModeWindow"
SYNC_SIGNAL_LEFT = 1
SYNC_SIGNAL_RIGHT = 2


SW_MINIMIZE = 6
SW_MAXIMIZE = 3
RESIZE_WINDOW = SW_MAXIMIZE  # None - do nothing, SW_MINIMIZE, SW_MAXIMIZE
PIXEL_GRABBER_THRESHOLD = 30  # 0 - left, 20*3 - right
USE_PIXEL_GRABBER_WINDOWS_GET_DC = False
USE_PIXEL_GRABBER_DXCAM = False
SAMPLE_EVERY_NTH_FRAME = 3

if os.name == "nt":
    if USE_PIXEL_GRABBER_WINDOWS_GET_DC:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
    if USE_PIXEL_GRABBER_DXCAM:
        import dxcam

WINDOWS_OS_NAME = "nt"
# WINDOWS_OS_NAME = "posix"

USE_LINE_PROFILER = False
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
        self.__hdc = None

        self.__next_sync_value = None
        self.__grab_count = 0
        self.__last_trigger_pixel_brightness = -1
        self.__cycle_count = 0
        self.__sync_count = {1: 0, 2: 0}
        self.__last_time = 0

        glfw.init()

        if USE_PIXEL_GRABBER_DXCAM and os.name == WINDOWS_OS_NAME:
            self.__dxcam_camera = dxcam.create(output_idx=0)
            self.__dxcam_camera.region = (0, 0, 1, 1)

    def __start(self):

        self.__gl_window = glfw.create_window(1, 1, WINDOW_NAME, None, None)
        if not self.__gl_window:
            glfw.terminate()
            raise Exception("Failed to create GLFW window")

        glfw.make_context_current(self.__gl_window)

        glfw.swap_interval(1)

        def minimize_window():
            if os.name == WINDOWS_OS_NAME:
                hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_NAME)
                ctypes.windll.user32.ShowWindow(hwnd, RESIZE_WINDOW)
            else:
                self.__sdl2_window.minimize()

        if RESIZE_WINDOW is not None:
            timer = threading.Timer(1, minimize_window)
            timer.start()

        if self.__keyboard_listener is None:
            self.__keyboard_listener = keyboard.Listener(
                on_press=self.on_key_press, on_release=self.on_key_release
            )
            self.__keyboard_listener.start()

        if USE_PIXEL_GRABBER_WINDOWS_GET_DC and os.name == WINDOWS_OS_NAME:
            self.__hdc = user32.GetDC(0)  # entire desktop

        self.__started = True
        self.__time_started = time.perf_counter()

    def __stop(self):

        if USE_PIXEL_GRABBER_WINDOWS_GET_DC and os.name == WINDOWS_OS_NAME:
            user32.ReleaseDC(0, self.__hdc)
            self.__hdc = None

        if self.__keyboard_listener is not None:
            self.__keyboard_listener.stop()
            self.__keyboard_listener = None

        if USE_LINE_PROFILER:
            line_profiler_obj.print_stats()

    @line_profiler_obj
    def __update(self):
        try:
            glfw.poll_events()

            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

            glfw.swap_buffers(self.__gl_window)

            self.__synced_flip_event_callback(self.__next_sync_value)

            if self.__target_frametime is not None:
                time_delta = time.perf_counter() - self.__time_started
                frame_type_modulus = (time_delta / self.__target_frametime) % 2
                if frame_type_modulus <= 1.0:
                    self.__left_or_bottom_page = True
                else:
                    self.__left_or_bottom_page = False
            else:
                self.__left_or_bottom_page = not self.__left_or_bottom_page

            self.__grab_count += 1
            if (
                (USE_PIXEL_GRABBER_WINDOWS_GET_DC or USE_PIXEL_GRABBER_DXCAM)
                and os.name == WINDOWS_OS_NAME
                and self.__grab_count % SAMPLE_EVERY_NTH_FRAME == 0
            ):
                if USE_PIXEL_GRABBER_WINDOWS_GET_DC:

                    def get_pixel_with_timeout(hdc, x, y, timeout=0.007):  # 7 ms
                        result = [None]

                        def worker():
                            try:
                                result[0] = gdi32.GetPixel(hdc, x, y)
                            except Exception:
                                pass

                        t = threading.Thread(target=worker)
                        t.start()
                        t.join(timeout)
                        if t.is_alive():
                            # Took too long, ignore
                            return None
                        return result[0]

                    data = get_pixel_with_timeout(self.__hdc, 0, 0)
                    # data = gdi32.GetPixel(self.__hdc, 0, 0)
                    if data is not None:
                        r = data & 0xFF
                        g = (data >> 8) & 0xFF
                        b = (data >> 16) & 0xFF
                if USE_PIXEL_GRABBER_DXCAM:
                    data = self.__dxcam_camera.grab()
                    if data is not None:
                        b, g, r = data[0, 0]
                if data is not None:
                    self.__last_trigger_pixel_brightness = r + g + b
                    # print(f"{self.__last_trigger_pixel_brightness},", end="")
                    if (
                        self.__last_trigger_pixel_brightness > PIXEL_GRABBER_THRESHOLD
                    ) == (not self.__left_or_bottom_page ^ self.__flip_eyes):
                        print("F", end="")
                        self.__flip_eyes = not self.__flip_eyes

            if self.__flip_eyes:
                self.__next_sync_value = (
                    SYNC_SIGNAL_RIGHT
                    if self.__left_or_bottom_page
                    else SYNC_SIGNAL_LEFT
                )
            else:
                self.__next_sync_value = (
                    SYNC_SIGNAL_LEFT
                    if self.__left_or_bottom_page
                    else SYNC_SIGNAL_RIGHT
                )

            self.__sync_count[self.__next_sync_value] += 1
            self.__cycle_count += 1
            now_time = int(time.time())
            if now_time > self.__last_time:
                self.__last_time = now_time
                print(
                    f"{self.__last_time} {self.__cycle_count} {self.__last_trigger_pixel_brightness} {self.__sync_count}"
                )
                self.__sync_count = {1: 0, 2: 0}
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
