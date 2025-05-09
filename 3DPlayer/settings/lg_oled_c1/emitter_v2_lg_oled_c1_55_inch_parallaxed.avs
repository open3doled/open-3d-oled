# these are the same values from 3d player under the display settings
flip_eyes = 0
display_size  = 55
whitebox_brightness = 255
whitebox_corner_position = "top_left"
whitebox_vertical_position = -5
whitebox_horizontal_position = 0
whitebox_horizontal_spacing = 18
whitebox_size = 15
blackbox_border = 10
parallax = 100 # use only positive values to shift video towards center for additional popout

# assume half is sbs or tab (when we get a half tab or half sbs video we can't tell which is which)
assume_for_half = "half_sbs" # "half_sbs" ? "half_tab"

# main script starts here
clip = potplayer_source()

aspect_ratio = Float(clip.Width)/Float(clip.Height)
layout = (aspect_ratio > 2.0 ? "full_sbs" : (aspect_ratio < 1.2 ? "full_tab" : assume_for_half))
layout_sbs = ((layout == "full_sbs" || layout == "half_sbs") ? 1 : 0)
scale_x = (layout == "half_sbs" ? 0.5 : 1.0)
scale_y = (layout == "half_tab" ? 0.5 : 1.0)
display_resolution_width = Int(clip.Width * (layout == "full_sbs" ? 0.5 : 1) * scale_x)
display_resolution_height = Int(clip.Height * (layout == "full_tab" ? 0.5 : 1) * scale_y)

if (layout_sbs == 1 && parallax > 0) {
    if (layout == "half_sbs") {
        parallax = parallax / 2
    }
    left_half = clip.Crop(0, 0, clip.Width / 2 - parallax, clip.Height)  # Left side with reduced crop
    right_half = clip.Crop(clip.Width / 2 + parallax, 0, clip.Width / 2 - parallax, clip.Height)  # Right side with reduced crop
    black_bar_left = BlankClip(clip, width=parallax, height=clip.Height, color=$000000)  # Black bar on the left
    black_bar_right = BlankClip(clip, width=parallax, height=clip.Height, color=$000000)  # Black bar on the right
    clip = StackHorizontal(black_bar_left, left_half, right_half, black_bar_right)
}

function RoundInt(Float input) {
    return Int(Float(input))
}

blackbox_blur_gradient_offset_ppc = 5
whitebox_blur_gradient_offset_ppc = 2

whitebox_brightness_bgr = 255*65536 + 255*256 + 255
pixel_pitch_x = Float(display_resolution_width) / (Float(display_size) * 0.87 * 25.4) # 1.578
pixel_pitch_y = Float(display_resolution_height) / (Float(display_size) * 0.49 * 25.4) # 1.578
blackbox_horizontal_position_ppc = RoundInt(Float(whitebox_horizontal_position - blackbox_border) * pixel_pitch_x)
whitebox_width_ppc = RoundInt(Float(whitebox_size - 2 * whitebox_blur_gradient_offset_ppc) * pixel_pitch_x)
whitebox_height_ppc = RoundInt(Float(whitebox_size - 2 * whitebox_blur_gradient_offset_ppc) * pixel_pitch_y)
whitebox_vertical_position_ppc = RoundInt(Float(whitebox_vertical_position) * pixel_pitch_y) + whitebox_blur_gradient_offset_ppc
blackbox_border_width_ppc = RoundInt(Float(blackbox_border) * pixel_pitch_x)
blackbox_border_height_ppc = RoundInt(Float(blackbox_border) * pixel_pitch_y)
whitebox_horizontal_spacing_ppc = RoundInt(Float(whitebox_horizontal_spacing) * pixel_pitch_x)
blackbox_width_ppc = RoundInt(whitebox_width_ppc + whitebox_horizontal_spacing_ppc + 2.0 * blackbox_border_width_ppc + 4.0 * whitebox_blur_gradient_offset_ppc)
blackbox_height_ppc = RoundInt(whitebox_height_ppc + whitebox_vertical_position_ppc + blackbox_border_height_ppc + 1.0 * whitebox_blur_gradient_offset_ppc)
horizontal_mod2_fix = blackbox_width_ppc % 2
vertical_mod2_fix = blackbox_height_ppc % 2

corner_position_bottom = (whitebox_corner_position == "bottom_right" || whitebox_corner_position == "bottom_left")
corner_position_right = (whitebox_corner_position == "top_right" || whitebox_corner_position == "bottom_right")
blackbox_horizontal_position_ppc_cf = (corner_position_right ? (display_resolution_width - blackbox_horizontal_position_ppc - blackbox_width_ppc) : blackbox_horizontal_position_ppc)
blackbox_vertical_position_ppc_cf = (corner_position_bottom ? (display_resolution_height - blackbox_height_ppc) : 0)
whitebox_top_border_ppc_cf = (corner_position_bottom ? (blackbox_border_height_ppc+whitebox_blur_gradient_offset_ppc+vertical_mod2_fix) : (whitebox_vertical_position_ppc > 0 ? whitebox_vertical_position_ppc : 0))
whitebox_bottom_border_ppc_cf = (corner_position_bottom ? (whitebox_vertical_position_ppc > 0 ? whitebox_vertical_position_ppc : 0) : (blackbox_border_height_ppc+whitebox_blur_gradient_offset_ppc+vertical_mod2_fix))

blackbox_horizontal_position_ppc_cf_left = (flip_eyes == 1 ? (layout_sbs == 1 ? display_resolution_width+blackbox_horizontal_position_ppc_cf : blackbox_horizontal_position_ppc_cf) : blackbox_horizontal_position_ppc_cf)
blackbox_vertical_position_ppc_cf_left = (flip_eyes == 1 ? (layout_sbs == 0 ? display_resolution_height+blackbox_vertical_position_ppc_cf : blackbox_vertical_position_ppc_cf) : blackbox_vertical_position_ppc_cf)
blackbox_horizontal_position_ppc_cf_right = (flip_eyes == 1 ? blackbox_horizontal_position_ppc_cf : (layout_sbs == 1 ? display_resolution_width+blackbox_horizontal_position_ppc_cf : blackbox_horizontal_position_ppc_cf))
blackbox_vertical_position_ppc_cf_right = (flip_eyes == 1 ? blackbox_vertical_position_ppc_cf : (layout_sbs == 0 ? display_resolution_height+blackbox_vertical_position_ppc_cf : blackbox_vertical_position_ppc_cf))

trigger_box_mask = BlankClip( \
  width=blackbox_width_ppc-2*blackbox_blur_gradient_offset_ppc+horizontal_mod2_fix, \
  height=blackbox_height_ppc-blackbox_blur_gradient_offset_ppc+vertical_mod2_fix, \
  color=$FFFFFF \
).AddBorders( \
  blackbox_blur_gradient_offset_ppc, \
  (corner_position_bottom ? blackbox_blur_gradient_offset_ppc : 0), \
  blackbox_blur_gradient_offset_ppc, \
  (corner_position_bottom ? 0 : blackbox_blur_gradient_offset_ppc), \
  color=$000000 \
).blur(1.5).blur(1.5).blur(1.5).converttoyv12().coloryuv(levels="tv->pc")

left_trigger_box = BlankClip( \
  width=whitebox_width_ppc, \
  height=(whitebox_vertical_position_ppc > 0 ? whitebox_height_ppc : whitebox_height_ppc + whitebox_vertical_position_ppc), \
  color=whitebox_brightness_bgr \
).AddBorders( \
  blackbox_border_width_ppc+whitebox_blur_gradient_offset_ppc, \
  whitebox_top_border_ppc_cf, \
  whitebox_horizontal_spacing_ppc+horizontal_mod2_fix+blackbox_border_width_ppc+3*whitebox_blur_gradient_offset_ppc, \
  whitebox_bottom_border_ppc_cf, \
  color=$000000 \
).converttoyv12().coloryuv(levels="tv->pc").blur(1.5).blur(1.5).blur(1.5)

overlay( \
  clip, \
  left_trigger_box, \
  x=blackbox_horizontal_position_ppc_cf_left, \
  y=blackbox_vertical_position_ppc_cf_left, \
  mode="blend", \
  mask=trigger_box_mask \
)

right_trigger_box = BlankClip( \
  width=whitebox_width_ppc, \
  height=(whitebox_vertical_position_ppc > 0 ? whitebox_height_ppc : whitebox_height_ppc + whitebox_vertical_position_ppc), \
  color=whitebox_brightness_bgr \
).AddBorders( \
  blackbox_border_width_ppc+horizontal_mod2_fix+whitebox_horizontal_spacing_ppc+3*whitebox_blur_gradient_offset_ppc, \
  whitebox_top_border_ppc_cf, \
  blackbox_border_width_ppc+whitebox_blur_gradient_offset_ppc, \
  whitebox_bottom_border_ppc_cf, \
  color=$000000 \
).converttoyv12().coloryuv(levels="tv->pc").blur(1.5).blur(1.5).blur(1.5)

overlay( \
  last, \
  right_trigger_box, \
  x=blackbox_horizontal_position_ppc_cf_right, \
  y=blackbox_vertical_position_ppc_cf_right, \
  mode="blend", \
  mask=trigger_box_mask \
)
