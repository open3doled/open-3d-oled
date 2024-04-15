import tkinter  # @UnusedImport
import os

from PIL import ImageTk
from io import BytesIO
import cairosvg
import PIL.Image


# The following class is extracted from tkinter.
class setit:
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
def svg_to_imagetk_photoimage(internal_base_path, image):
    png_data = cairosvg.svg2png(
        url=os.path.join(internal_base_path, image), output_width=30, output_height=30
    )
    bytes_png = BytesIO(png_data)
    img = PIL.Image.open(bytes_png)
    return ImageTk.PhotoImage(img)
