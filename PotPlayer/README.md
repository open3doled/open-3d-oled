# Open3DOLED - PotPlayer

## Introduction
PotPlayer is a windows media player that support H264 MVC decoding and also supports Direct3D9 Ex Flip Mode and Overlay.
This provides the optimal set of tools to allow you to play 3D Blurays directly from discs with zero flicker due to dropped frames.
The setup of such a system is provided in the steps below.

## Add Support for Blu-ray On the Fly Playback (Optional)
* Install Xreveal from https://www.xreveal.com/how-to-use-xreveal.html (this is the recommended technique as it is 100% free to use)
  * If using Xreveal and you are not using the payed version some discs will not play with the default install due to libbdplus bd+.dll limitations, these limitations can be overcome by following the instructions at https://forum.doom9.org/showthread.php?t=176924
  * Specifically under the Xreveal "Settings -> Blu-ray -> KeyDB" you need to 
    * Update KeyDB.cfg to point to the downloaded keydb.cfg file (which you changed the first 3 lines of as described on the doom9 page)
    * Update the FUT location to point to the folder where you extract all the "cached BD+ tables"
    * I don't believe the vm0 setup is necessary but if you run into difficulties playing some discs you can try that too.
* DVDFab Passkey lite also works until the trial runs out, at which point you will only be able to play older 3d blu-ray until you buy a license.

## Install PotPlayer via ThreeDeeJay Installer Script (Includes all AVISynth and MVC Plugins)
* The following github repository has a prebuilt installer that will allow you to install PotPlayer with AVISynth and basic MVC/Bluray support.
* https://github.com/ThreeDeeJay/PotPlayer3D
* Installing using this script is simplest and allows you to skip directly to "First usage" below.
* Additionally it includes optional plugins to improve video quality using SVP motion interpolation and madVR Upscaling.

## Install PotPlayer and Required Plugins Manually

### Install AVISynth+
* First download and install the main AVISynth 2.6 32bit software
  * Download from https://www.videohelp.com/software/Avisynth
  * Install with default settings
* Next install AVISynth 2.6 MT replacement plugin for improved performance
  * Download from https://forum.doom9.org/showthread.php?t=148782
  * Extract avisynth.dll from the 7zip file over your file in C:\Windows\SysWOW64

### Install PotPlayer
* Download and install PotPlayer 32 bit from https://potplayer.daum.net/
* Be sure to select "Install additional codec (OpenCodec)" on the "Complete install PotPlayer" screen at the end.
* When installing OpenCodec be sure to select "Intel H.264 MVC Decoder"
* When it completes PotPlayer will auto-launch by default (unless you disabled it)

## PotPlayer 3D Setup
* Open up Preferences by hitting F5
* Navigate to "Video"
  * Change "Fullscreen exclusive mode" to "Enable: A little slow (gui support)"
* Navigate to "Video -> 3D Mode" 
  * Select the checkbox next to "Enable H.264 MVC 3D Decoder"
  * Change "Output Mode" to "Synthesized View: SBS at full resolution"
  * Change "3D Video Mode" to "Enable 3D Video Mode"
  * Change "Input (Source)" to "SBS (Side by Side)"
  * Check "Full resolution"
  * Change "Output (Screen)" to "Shutter Glasses (Page Flipping)"
  * Check "Auto detect 3D input format (based on filename suffixes ...)"
* Navigate to "Video -> AVI Synth"
  * Check "Enable AviSynth processing"
  * Click on "Load script -> Load script from a file"
  * If you have our native 3DPlayer installed you can generate the required scirpt by clicking "Generate PotPlayer AVISynth Script" under "Display Settings", then use the generated script with already populated parameters in place of the one discussed in teh following two steps.
  * Select either the file "[trigger_box_overlay.avs](/PotPlayer/trigger_box_overlay.avs)" from this folder or the one you generated from 3DPlayer and click "Open"
  * If you are using the standard template file instead of the custom generated one change the parameters at the top of the script to match those from 3d player TV Settings that you obtained from calibration, or tweak them manually until the trigger boxes are a satisfactory size and position.
```
# these are the same values from 3d player under the display settings
flip_eyes = 0
display_size  = 24
whitebox_brightness = 255
whitebox_position = "top_left"
whitebox_vertical_position = -4
whitebox_horizontal_position = -3
whitebox_horizontal_spacing = 17
whitebox_size = 13
blackbox_border = 7

# assume half is sbs or tab (when we get a half tab or half sbs video we can't tell which is which)
assume_for_half = "half_sbs" # "half_sbs" ? "half_tab"
```
  * The "assume_for_half" parameter is used to define the default oreintation side-by-side top-and-bottom when half width or half height content will be played as there is no way to make this determination from the resolution alone.

## FAQ
* The trigger boxes aren't showing an any videos
  * Make sure you installed the 32 bit version of both PotPlayer and AVISynth+ the 64bit version has been reported to not work.
* The trigger boxes aren't showing on some videos
  * Make sure "Use Built-in DXVA Video Decoder" is "Off", when it is "On" the AVISynth script will not run. Look for the botton with the text "H/W" next to teh video duration and click it. It should update to show "S/W" and the trigger boxes should show.
* Clicking "Swap left/right images" is not flipping the eyes.
  * This option may not have any effect depending on factors I don't fully understand, you have two options.
    * You can use 3d_player to invert the eyes by changing the setting "Emitter Settings -> IR Flip Eyes" to either "0" or "1" 
    * You can set the variable in the AVISynth script to invert the eyes by setting "flip_eyes" to either "0" or "1" 
* Non 16:9 content has trigger boxes half way down screen.
  * Currently PotPlayer doesn't support resizing the video size from the AVISynth script, nor does it support embedding multiple videos inside a larger video container. 
  * If your video is an top-and-bottom video with less than 16:9 aspect ratio, there isn't much that can be done, however you can use "Fullscreen (Stretch)" to watch it in a stretched aspect ratio. 
  * If however your video is side-by-side it is possible to override the aspect ratio so that using "Extend/Crop" as described below.
    * Open PotPlayer "Preferences" and navigate to "Video" -> "Extend/Crop"
    * Depending on if your video is hsbs or fsbs the follow step will differ.
      * If HSBS, select "Video Extending/Cropping" "Method" "16:9 Extending" and click "Apply"
      * If FSBS, select "Video Extending/Cropping" "Method" "Extend by aspect ratio (X:Y)" and click "Apply", then down below change "Ratio" to "32" : "9"
    * Check "Scale only frame height"
    * Click "Apply" at the bottom and then "OK"
    * Once again the AVSynth plugin only works in "S/W" decoding mode so you will need to ensure the icon under your video shows "S/W" and not "H/W"
    * You may need to stop and restart playback for "Extend" setting to start to be applied to the video
    * Since these adjustments are applied to the raw video before PotPlayer attempts to process it for 3d playback, you will need to switch aspect ratios if you change between fsbs and hsbs, so it is recommended to only turn this on when you need it.
  * I'm currently investigating how difficult it would be to port the AVISynth script to a "Pixel Shader" it may be possible to get it working using "Pixel Shaders" but a separate script may be required for hsbs, fsbs, tab/ou and htab/hou.

## Playing 3D Blu-rays
* Start Xreveal (or DVDFab Passkey) if it isn't already running.
* Open -> Open Blu-ray

## Subtitles
Currently it isn't possible to get stereo subtitles to work as far as I can tell but it may be possible in the future.

## Thanks
A big thankyou to following two sites have useful information about setting up PotPlayer for 3D playback.
* https://www.mtbs3d.com/phpbb/viewtopic.php?t=26137
* https://github.com/ThreeDeeJay/PotPlayer3D
