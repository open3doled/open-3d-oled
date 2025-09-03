import time
import glfw
from OpenGL.GL import *

# pacman -S mingw-w64-ucrt-x86_64-glfw
# pip install glfw

USE_LINE_PROFILER = True
if USE_LINE_PROFILER:
    from line_profiler import LineProfiler

    line_profiler_obj = LineProfiler()
else:

    def line_profiler_obj(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

hdc = user32.GetDC(0)  # entire desktop
if not hdc:
    raise RuntimeError("Failed to get DC for window")

# Initialize GLFW
if not glfw.init():
    raise Exception("GLFW initialization failed")

# Create a window with OpenGL context
window = glfw.create_window(1, 1, "OpenGL with VSync", None, None)
if not window:
    glfw.terminate()
    raise Exception("Failed to create GLFW window")

glfw.make_context_current(window)

# Enable VSync
glfw.swap_interval(1)


# Give the system a moment to warm up
time.sleep(5)

colors = {}
start = time.time()


@line_profiler_obj
def loop():
    # Main loop
    # while not glfw.window_should_close(window):
    for _ in range(2400):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # Render your OpenGL content here

        glfw.swap_buffers(window)

        # Grab the latest frame from the desktop
        data = gdi32.GetPixel(hdc, 0, 0)

        if data != -1:
            r = data & 0xFF
            g = (data >> 8) & 0xFF
            b = (data >> 16) & 0xFF
            color = (r, g, b)
        else:
            color = None

        # Count occurrences
        colors[color] = colors.get(color, 0) + 1

        glfw.poll_events()


loop()

elapsed = time.time() - start
print(f"Elapsed: {elapsed:.4f} sec")

for color, count in colors.items():
    print(f"RGB: {color} count {count}")

glfw.terminate()

if USE_LINE_PROFILER:
    line_profiler_obj.print_stats()
