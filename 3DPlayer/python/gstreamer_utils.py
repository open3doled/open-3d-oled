#!/usr/bin/env python

# Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/

"""
This file includes the necessary portions extracted from https://github.com/jackersson/gstreamer-python
and updated to work on newer versions of gstreamer.
 - https://github.com/jackersson/gstreamer-python/blob/master/gstreamer/utils.py
 - https://github.com/jackersson/gstreamer-python/blob/master/gstreamer/gst_hacks.py
"""

import json  # @UnusedImport

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")
gi.require_version("GstVideo", "1.0")

from gi.repository import Gst, GObject, GLib, GstBase, GstVideo  # noqa:F401,F402

import numpy as np
import math
import ctypes  # @UnusedImport
from contextlib import contextmanager
from typing import Tuple

BITS_PER_BYTE = 8

_ALL_VIDEO_FORMATS = [
    GstVideo.VideoFormat.from_string(f.strip())
    for f in GstVideo.VIDEO_FORMATS_ALL.strip("{ }").split(",")
]


def has_flag(value: GstVideo.VideoFormatFlags, flag: GstVideo.VideoFormatFlags) -> bool:

    # in VideoFormatFlags each new value is 1 << 2**{0...8}
    return bool(value & (1 << max(1, math.ceil(math.log2(int(flag))))))


def _get_num_channels(fmt: GstVideo.VideoFormat) -> int:
    """
    -1: means complex format (YUV, ...)
    """
    frmt_info = GstVideo.VideoFormat.get_info(fmt)

    # temporal fix
    if fmt == GstVideo.VideoFormat.BGRX:
        return 4

    if has_flag(frmt_info.flags, GstVideo.VideoFormatFlags.ALPHA):
        return 4

    if has_flag(frmt_info.flags, GstVideo.VideoFormatFlags.RGB):
        return 3

    if has_flag(frmt_info.flags, GstVideo.VideoFormatFlags.GRAY):
        return 1

    return -1


_ALL_VIDEO_FORMAT_CHANNELS = {fmt: _get_num_channels(fmt) for fmt in _ALL_VIDEO_FORMATS}


def get_num_channels(fmt: GstVideo.VideoFormat):
    return _ALL_VIDEO_FORMAT_CHANNELS[fmt]


_DTYPES = {
    16: np.int16,
}


def get_np_dtype(fmt: GstVideo.VideoFormat) -> np.number:
    format_info = GstVideo.VideoFormat.get_info(fmt)
    return _DTYPES.get(format_info.bits, np.uint8)


def gst_video_format_from_string(frmt: str) -> GstVideo.VideoFormat:
    return GstVideo.VideoFormat.from_string(frmt)


'''
@contextmanager
def map_gst_buffer(pbuffer: Gst.Buffer, flags: Gst.MapFlags) -> _GST_MAP_INFO_POINTER:
    """ Map Gst.Buffer with READ/WRITE flags

        Example:
            with map_gst_buffer(pbuffer, Gst.MapFlags.READ | Gst.MapFlags.WRITE) as mapped:
                // do_something with mapped
    """

    if pbuffer is None:
        raise TypeError("Cannot pass NULL to _map_gst_buffer")

    ptr = hash(pbuffer)
    if flags & Gst.MapFlags.WRITE and _libgst.gst_mini_object_is_writable(ptr) == 0:
        raise ValueError(
            "Writable array requested but buffer is not writeable")

    mapping = _GstMapInfo()
    success = _libgst.gst_buffer_map(ptr, mapping, flags)
    if not success:
        raise RuntimeError("Couldn't map buffer")
    try:
        yield cast(
            mapping.data, POINTER(c_byte * mapping.size)).contents
    finally:
        _libgst.gst_buffer_unmap(ptr, mapping)
'''


@contextmanager
def map_gst_buffer(pbuffer: Gst.Buffer, flags: Gst.MapFlags) -> Gst.MapInfo:
    """

    https://gstreamer.freedesktop.org/documentation/gstreamer/gstbuffer.html?gi-language=python#gst_buffer_map

    Parameters:
    buffer (Gst.Buffer) –

    a Gst.Buffer.
    flags (Gst.MapFlags) –

    flags for the mapping

    Returns a tuple made of:
    (bool ) –

    True if the map succeeded and info contains valid data.
    info (Gst.MapInfo ) –

    True if the map succeeded and info contains valid data.

    https://gstreamer.freedesktop.org/documentation/gstreamer/gstmemory.html?gi-language=python#GstMapInfo

    Members
    memory (Gst.Memory) –

    a pointer to the mapped memory
    flags (Gst.MapFlags) –

    flags used when mapping the memory
    data ([ int ]) –

    a pointer to the mapped data
    size (int) –

    the valid size in data
    maxsize (int) –

    the maximum bytes in data
    user_data ([ object ]) –

    extra private user_data that the implementation of the memory can use to store extra info.

    """
    success, mapping = pbuffer.map(flags)
    if not success:
        raise RuntimeError("Couldn't map buffer")
    try:
        if type(mapping.data) == bytes:
            # yield ctypes.cast(mapping.data, ctypes.POINTER(ctypes.c_byte * mapping.size)).contents
            yield memoryview(mapping.data)
        else:
            assert type(mapping.data) == memoryview
            yield mapping.data
    finally:
        pbuffer.unmap(mapping)


def gst_buffer_with_caps_to_ndarray(
    buffer: Gst.Buffer, caps: Gst.Caps, do_copy: bool = False
) -> np.ndarray:
    "Converts Gst.Buffer with Gst.Caps (stores buffer info) to np.ndarray"

    # print(buffer.get_size()) # 3110400 for 1920x1080

    structure = caps.get_structure(0)  # Gst.Structure

    width, height = structure.get_value("width"), structure.get_value("height")

    # GstVideo.VideoFormat
    # print(structure.get_value('format')) # I420
    video_format = gst_video_format_from_string(structure.get_value("format"))

    if video_format == GstVideo.VideoFormat.RGBX:
        channels = 4
        dtype = np.uint8
        bpp = 8

    else:
        channels = get_num_channels(video_format)
        dtype = get_np_dtype(video_format)  # np.dtype
        format_info = GstVideo.VideoFormat.get_info(
            video_format
        )  # GstVideo.VideoFormatInfo
        bpp = format_info.bits

    result = None
    if do_copy:
        result = np.ndarray(
            buffer.get_size() // (bpp // BITS_PER_BYTE),
            buffer=buffer.extract_dup(0, buffer.get_size()),
            dtype=dtype,
        )
    else:
        with map_gst_buffer(buffer, Gst.MapFlags.READ) as mapped:
            result = np.ndarray(
                buffer.get_size() // (bpp // BITS_PER_BYTE), buffer=mapped, dtype=dtype
            )
        """
        result = np.frombuffer(
            buffer.data, 
            count=buffer.get_size() // (bpp // BITS_PER_BYTE), 
            dtype=dtype,
        )
        """
    if channels > 0:
        result = result.reshape(height, width, channels).squeeze()

    return result


@contextmanager
def gst_buffer_with_caps_to_bytes_and_size(
    buffer: Gst.Buffer, caps: Gst.Caps, do_copy: bool = False  # @UnusedVariable
) -> Tuple[memoryview, int, int]:
    structure = caps.get_structure(0)  # Gst.Structure

    width, height = structure.get_value("width"), structure.get_value("height")

    with map_gst_buffer(buffer, Gst.MapFlags.READ) as mapped:
        yield mapped, width, height
