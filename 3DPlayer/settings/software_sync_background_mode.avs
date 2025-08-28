flip_eyes = 0
left_brightness = 0
right_brightness = 10
triggerbox_horizontal_position = 0
triggerbox_vertical_position = 0
triggerbox_width_ppc = 2
triggerbox_height_ppc = 2

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

left_brightness_bgr = left_brightness*65536 + left_brightness*256 + left_brightness
right_brightness_bgr = right_brightness*65536 + right_brightness*256 + right_brightness

triggerbox_horizontal_position_left = (flip_eyes == 1 ? (layout_sbs == 1 ? display_resolution_width+triggerbox_horizontal_position : triggerbox_horizontal_position) : triggerbox_horizontal_position)
triggerbox_vertical_position_left = (flip_eyes == 1 ? (layout_sbs == 0 ? display_resolution_height+triggerbox_vertical_position : triggerbox_vertical_position) : triggerbox_vertical_position)
triggerbox_horizontal_position_right = (flip_eyes == 1 ? triggerbox_horizontal_position : (layout_sbs == 1 ? display_resolution_width+triggerbox_horizontal_position : triggerbox_horizontal_position))
triggerbox_vertical_position_right = (flip_eyes == 1 ? triggerbox_vertical_position : (layout_sbs == 0 ? display_resolution_height+triggerbox_vertical_position : triggerbox_vertical_position))

left_trigger_box = BlankClip( \
  width=triggerbox_width_ppc, \
  height=triggerbox_height_ppc, \
  color=left_brightness_bgr \
)

overlay( \
  clip, \
  left_trigger_box, \
  x=triggerbox_horizontal_position_left, \
  y=triggerbox_vertical_position_left, \
  mode="blend" \
)

right_trigger_box = BlankClip( \
  width=triggerbox_width_ppc, \
  height=triggerbox_height_ppc, \
  color=right_brightness_bgr \
)

overlay( \
  last, \
  right_trigger_box, \
  x=triggerbox_horizontal_position_right, \
  y=triggerbox_vertical_position_right, \
  mode="blend" \
)
