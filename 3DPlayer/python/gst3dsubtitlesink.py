#!/usr/bin/env python

# Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/

import json

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")

from gi.repository import Gst, GObject, GLib, GstBase  # noqa:F401,F402

# FORMATS = [f.strip() for f in "pango-markup,utf8".split(',')]

# IN_CAPS = Gst.Caps(Gst.Structure('text/x-raw',
#                                 format=Gst.ValueList(FORMATS)
#                                 ))


class GstSubtitle3DSink(GstBase.BaseSink):
    GST_PLUGIN_NAME = "gstsubtitle3dsink"

    __gstmetadata__ = (
        "GstSubtitle3DSink",
        "Sink",
        "Sink to be used with playbin to capture subtitle data and provide it to GstPageflipGLSink",
        "Peter",
    )

    __gsttemplates__ = Gst.PadTemplate.new(
        "sink",
        Gst.PadDirection.SINK,
        Gst.PadPresence.ALWAYS,
        Gst.Caps.new_any(),
        # IN_CAPS
    )

    __gproperties__ = {
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
        "close": (
            GObject.TYPE_BOOLEAN,
            "Close",
            "Close the player",
            False,  # default
            GObject.ParamFlags.WRITABLE,
        ),
        "latest_subtitle_data": (
            GObject.TYPE_STRING,
            "Latest Subtitle Data",
            "Latest subtitle data as json object",
            "",  # default
            GObject.ParamFlags.READWRITE,
        ),
    }

    def __init__(self):
        super(GstSubtitle3DSink, self).__init__()
        self.__latest_subtitle_data = ""

    def do_get_property(self, prop: GObject.GParamSpec):
        if prop.name == "latest-subtitle-data":
            return self.__latest_subtitle_data
        else:
            raise AttributeError("unknown property %s" % prop.name)

    def do_set_property(self, prop: GObject.GParamSpec, value):
        if prop.name == "latest-subtitle-data":
            if value == "":
                self.__latest_subtitle_data = value
        else:
            raise AttributeError("unknown property %s" % prop.name)

    def do_render(self, inbuffer: Gst.Buffer) -> Gst.FlowReturn:
        # https://gstreamer.freedesktop.org/documentation/gstreamer/gstbuffer.html?gi-language=python
        text = inbuffer.extract_dup(0, inbuffer.get_size()).decode(
            "utf-8", errors="ignore"
        )
        # Gst.info(f"start:{Gst.TIME_ARGS(inbuffer.pts)} duration:{Gst.TIME_ARGS(inbuffer.duration)} text={text}")
        # print(f"start:{Gst.TIME_ARGS(inbuffer.pts)} duration:{Gst.TIME_ARGS(inbuffer.duration)} text={text}")
        subtitle_data = {
            "start": inbuffer.pts,
            "duration": inbuffer.duration,
            "text": text,
        }
        self.__latest_subtitle_data = json.dumps(subtitle_data)

        return Gst.FlowReturn.OK


# Register plugin to use it from command line
GObject.type_register(GstSubtitle3DSink)
__gstelementfactory__ = (
    GstSubtitle3DSink.GST_PLUGIN_NAME,
    Gst.Rank.NONE,
    GstSubtitle3DSink,
)
