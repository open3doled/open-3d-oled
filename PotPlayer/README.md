# Open3DOLED - PotPlayer

## Introduction
PPotPlayer is a windows media player that support H264 MVC decoding and also supports Direct3D9 Ex Flip Mode and Overlay.
This provides the optimal set of tools to allow you to play 3D Blurays directly from discs with zero flicker due to dropped frames.
The setup of such a system is provided in the steps below.

## Add Support for Blu-ray On the Fly Playback (Optional)
* Install Xreveal from https://www.xreveal.com/how-to-use-xreveal.html (this is the recommended technique as it is 100% free to use)
* If you are not comfortable using Xreveal DVDFab Passkey lite also works until the trial runs out, at which point you will only be able to play older 3d blu-ray until you buy a license.

## Install PotPlayer via ThreeDeeJay Installer Script (Includes all AVISynth and MVC Plugins)
The following github repository has a prebuilt installer that will allow you to install PotPlayer with AVISynth and basic MVC/Bluray support.
https://github.com/ThreeDeeJay/PotPlayer3D
Installing using this script is simplest and allows you to skip directly to "First usage" below.
Additionally it includes optional plugins to improve video quality using SVP motion interpolation and madVR Upscaling.

## Install PotPlayer and Required Plugins Manually

### Install AVISynth+
* First download and install the main AVISynth 2.6 32bit software
 * Download from https://www.videohelp.com/software/Avisynth
 * Install with default settings
* Next install AVISynth 2.6 MT replacement plugin for improved performance
 * Download from https://forum.doom9.org/showthread.php?t=148782
 * Extract avisynth.dll from the 7zip file over your file in C:\Windows\SysWOW64

### Install PotPlayer
Download and install PotPlayer 32 bit from
https://potplayer.daum.net/
Be sure to select "Install additional codec (OpenCodec)" on the "Complete install PotPlayer" screen at the end.
When installing OpenCodec be sure to select "Intel H.264 MVC Decoder"
When it completes PotPlayer will auto-launch by default (unless you disabled it)

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
 * Select the file "trigger_box_overlay.avs" from this folder and "Open"
 * Change the parameters at the top of the script to match those from 3d player TV Settings that you obtained from calibration.
```
# these are the same values from 3d player under the display settings
display_size  = 24
whitebox_brightness = 255
whitebox_position = "top_left" # currently only top_left is supported and this value is ignored
whitebox_vertical_position = -4
whitebox_horizontal_position = -3
whitebox_horizontal_spacing = 17
whitebox_size = 13
blackbox_border = 7

# assume half is sbs or tab (when we get a half tab or half sbs video we can't tell which is which)
assume_for_half = "half_sbs" # "half_sbs" ? "half_tab"
```

## Playing 3D Blu-rays
* Start Xreveal (or DVDFab Passkey) if it isn't already running.
1) Open -> Open Blu-ray

## Subtitles
Currently it isn't possible to get stereo subtitles to work 

## Thanks
A big thankyou to following two sites have useful information about setting up PotPlayer for 3D playback.
* https://www.mtbs3d.com/phpbb/viewtopic.php?t=26137
* https://github.com/ThreeDeeJay/PotPlayer3D
