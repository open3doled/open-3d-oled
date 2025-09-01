import dxcam
import time

import os
import ctypes
import psutil
import threading
from pygame import _sdl2 as pygame_sdl2
from pygame import locals as pg_locals
import OpenGL.GL as gl
import pygame as pg

if os.name == "nt":
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
                
WINDOW_NAME = "Open3DOLED3DSoftwareSyncBackgroundModeWindow"
WINDOWS_OS_NAME = "nt"

display_resolution_width = 200
display_resolution_height = 100

p = psutil.Process(os.getpid())
if os.name == WINDOWS_OS_NAME:
    p.nice(psutil.HIGH_PRIORITY_CLASS)
else:
    p.nice(10)

pg.init()
        
flags = pg_locals.DOUBLEBUF | pg_locals.OPENGL | pg_locals.RESIZABLE
pg_clock = pg.time.Clock()
pg_window = pg.display.set_mode(
    (display_resolution_width, display_resolution_height),
    flags,
    vsync=1,
)

pg.display.set_caption(WINDOW_NAME)

sdl2_window = pygame_sdl2.Window.from_display_module()
sdl2_window.size = (
    display_resolution_width,
    display_resolution_height,
)
sdl2_window.position = pygame_sdl2.WINDOWPOS_CENTERED

def minimize_window():
    if os.name == WINDOWS_OS_NAME:
        hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_NAME)
        SW_MINIMIZE = 6
        ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
    else:
        sdl2_window.minimize()
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
    0, 0, display_resolution_width, display_resolution_height
)
gl.glMatrixMode(gl.GL_PROJECTION)
gl.glLoadIdentity()
gl.glOrtho(
    0,
    display_resolution_width,
    0,
    display_resolution_height,
    -1,
    1,
)
gl.glMatrixMode(gl.GL_MODELVIEW)
gl.glLoadIdentity()

# Create a capture object for the primary display (index 0)
camera = dxcam.create(output_idx=0)
camera.region = (0,0,1,1)

# Give the system a moment to warm up
time.sleep(5)

colors = {}
start = time.time()

for _ in range(1200):
    #pg.display.flip()
    
    # Grab the latest frame from the desktop
    frame = camera.grab()

    # dxcam returns a NumPy array in BGR format
    if frame is not None:
        b, g, r = frame[0, 0]
        color = (r, g, b)
    else:
        colors[None] = colors.get(None, 0) + 1
    
    # Count occurrences
    colors[color] = colors.get(color, 0) + 1

elapsed = time.time() - start
print(f"Elapsed: {elapsed:.4f} sec for 600 samples")

for color, count in colors.items():
    print(f"RGB: {color} count {count}")

pg.quit()