#!/usr/bin/env bash

openscad --o "3d_ir_emitter_0201a_base.stl" --export-format asciistl --D build_base=1 3d_ir_emitter_0201a.scad
openscad --o "3d_ir_emitter_0201a_cover_main.stl" --export-format asciistl --D build_cover_main=1 3d_ir_emitter_0201a.scad
openscad --o "3d_ir_emitter_0201a_cover_sensor.stl" --export-format asciistl --D build_cover_sensor=1 3d_ir_emitter_0201a.scad

