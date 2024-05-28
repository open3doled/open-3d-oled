#!/usr/bin/env bash

openscad --o "0202a_base.stl" --export-format asciistl --D build_base=1 0202a.scad
openscad --o "0202a_cover_main.stl" --export-format asciistl --D build_cover_main=1 0202a.scad
openscad --o "0202a_cover_sensor.stl" --export-format asciistl --D build_cover_sensor=1 0202a.scad

