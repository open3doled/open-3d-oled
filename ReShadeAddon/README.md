# Open3DOLED - Reshade Plugin

## Introduction
The following Reshade Addon and AVS script are intended to be used with PotPlayer.
The AVS Script adds a 4x4 pixel block at the top corner of the screen that based on it's color and intensity determines which eye is currently be displayed.
The Reshade Addon extracts the intensity signal and based on configurable levels will determine which eye is being shown, and then send the serial over usb signal to the emitter to trigger the shutter glasses.


## Installation
* Before attempting to use this ensure your PotPlayer is configured according to he instructions on the [PotPlayer](../PotPlayer/README.md) page. 
* The only difference being you will need to use the AVI Synth Script located in this folder instead for the special trigger pixels.
* Next you will need to change the permissions on your "C:\Program Files\DAUM\PotPlayer" folder so that the "Users" group has full access otherwise Reshade will throw errors.
* Now copy he contents of the "install" folder into "C:\Program Files\DAUM\PotPlayer".
* The Reshade addon probably will not work with HDR currently so ensure you turn that off in PotPlayer if you have it on. I've run into issues where the RGB BGR byte order for pixels is not consistent between different PC's. So the first you run the Reshade addon you should turn on debug mode to make sure the color channel (default to GREEN) you are using to signal is indeed the correct one.
* Make sure your IR emitter is connected to your PC.
* So now open "Open3dOLED.ini" and change the following lines
  * "COMPort=COM3" to whatever com port is used by the emitter (check in 3DPlayer or Device Manager if you're not sure)
  * "DebugMode=1" to "DebugMode=2", this will print out a debug line on every frame. 
* Now launch "PotPlayerMini64_Reshade.bat" and a command box should popup and quickly close to load the injector, followed by PotPlayer opening.
* Once PotPlayer has opened, open the normal side by side red blue 1080p test video in pageflipping mode and fullscreen it, let it run afew seconds and then stop it (you don't need to close PotPlayer).
* Now open the log file "Open3DOLED.log" and you should see down below a section with a bunch of lines like the following.
```
Debug Trigger LeftEye: 1    R: 0 G: 0 B: 0         R2: 0 G2: 0 B2: 0.
.... then afew hundred lines down after you fullscreened the window you will start to see something like the following repeating ....
Debug Trigger LeftEye: 1    R: 0 G: 8 B: 0         R2: 255 G2: 0 B2: 0.
Debug Trigger LeftEye: 0    R: 48 G: 10 B: 0         R2: 1 G2: 0 B2: 255.
Debug Trigger LeftEye: 1    R: 0 G: 8 B: 0         R2: 255 G2: 0 B2: 0.
Debug Trigger LeftEye: 0    R: 48 G: 10 B: 0         R2: 1 G2: 0 B2: 255.
.... on some machines the R and G channels are inverted for the first set of R G B values used by the trigger box. It seems related to AVISynth or something ....
Debug Trigger LeftEye: 1    R: 8 G: 0 B: 0         R2: 255 G2: 0 B2: 0.
Debug Trigger LeftEye: 0    R: 10 G: 48 B: 0         R2: 1 G2: 0 B2: 255.
Debug Trigger LeftEye: 1    R: 8 G: 0 B: 0         R2: 255 G2: 0 B2: 0.
Debug Trigger LeftEye: 0    R: 10 G: 48 B: 0         R2: 1 G2: 0 B2: 255.
.... you need to identify which of the channels from the first set of R G B values is flipping between close to 0 and close to 30. The numbers will vary based on any color correction or gama adjustments PotPlayer is configured with so it may differ slightly ....
```
* Once you've figured out which channel is flipping and approximately over what range it is flipping you need to open "Open3DOled.ini" again
  * Change "TriggerChannel=1" to "0", "1" or "2" based on if R, G or B was flipping.
  * Change "TriggerThreshold=20" to a number half way between the high and low value that were flipping.
  * Change "TriggerMin=5" to number less than or equal to the lowest value it was fliping between.
  * Change "TriggerMax=5" to number greater than or equal to the highest value it was fliping between.
  * Turn debug mode back to 1. "DebugMode=1"
* Delete the "Open3DOLED.log" file from the PotPlayer folder.
* Play the side by side red blue 1080p test video again for afew seconds in fullscreen mode then stop it.
* Open the "Open3DOLED.log" and confirm you see something like the following.
```
COMPort: COM7
TriggerThreshold: 20
TriggerMin: 5
TriggerMax: 45
DebugMode: 1
Opened COM port: COM7
Staging 1x1 readback texture created (debug build).
Staging 1x1 readback texture created (debug build).
Left eye signals: 11 | Right eye signals: 12
Left eye signals: 61 | Right eye signals: 60
Left eye signals: 60 | Right eye signals: 61
Left eye signals: 60 | Right eye signals: 61
Left eye signals: 61 | Right eye signals: 60
... roughly 1 additional line for every second it was open ....
Left eye signals: 60 | Right eye signals: 61
Left eye signals: 61 | Right eye signals: 60
Left eye signals: 60 | Right eye signals: 60
Left eye signals: 41 | Right eye signals: 39
Left eye signals: 0 | Right eye signals: 0
Destroyed staging resource.
```
* If you see any lines like "Error Wrong Eye Debug Trigger LeftEye: 1    R: 8 G: 0 B: 0         R2: 255 G2: 0 B2: 0." it means either your Trigger channel, threshold, min, or max are not right. Repeat the step above and if it persists send me the log and let me know.
* If you see an error like "Backbuffer format not recognized as common 8-bit RGBA. Creating staging anyway for debug. Format : NN" send me the format number and I will add support for it.
* If it looks like above then you should be good to proceed to calibration.


## Calbiration
* Currently there is no calibration functionality in the Reshade plugin so you have to use 3DPlayer to adjust your timings (sorry for the hassle).
* The easiest way to do this is as follows.
* First configure all your timings using 3DPlayer first so you have the ghosting / brightess tradeoff how you like it.
* Now open 3DPlayer and open IR Settings, but but make sure your not connected to the unit. Also you need "IR Average Timing Mode" on (set to 1) or the reshade background sync will have too much jitter.
* Open PotPlayer with "PotPlayerMini64_Reshade.bat", open the red blue side-by-side 1080p test video with frame sequential and fullscreen it with enter.
* Put on your glasses and check to see if the frame_delay needs increasing or decreasing to center the least ghosted part of the image in the vertical middle of the screen.
* Press "Enter" to exit fullscreen and "Stop" the video, the keyboard shortcut for this on my system is "F4".
* Go back to 3DPlayer "IR Settings" and click "Connect"
* Increase or decrease the "Frame Delay" click "Update" and "Save to EEPROM".
* Click disconnect
* Then back in PotPlayer click "Space" to start playback again, followed by "Enter" to go into fullscreen.
* Check to see if the frame_delay needs increasing or decreasing to center the least ghosted part of the image in the vertical middle of the screen.
* Press "Enter" to exit fullscreen and "Stop" the video with "F4"
* Repeat the 6-7 steps above until you get it centered.
* I've notest the "IR Average Timing Mode" is slightly non-deterministic in where it finally settles, I'm going to work on improving this in the ir emitters firmware. But for now you can just click "Enter" afew times to exit and enter "Fullscreen" afew times and see where it settles each time.
  * I've made a test firwmare with an updated PID controller that smooths out the jitter more and settles more deterministically. Any firmware after from [22b_20250903](../3DPlayer/firmwares/firmware_v22b_20250903.hex) onwards should have this algorithm.


## Questions
* This is very much alpha so if you run into any issues just let me know and I'll be happy to get back to you as soon as possible.

## Links
* https://guides.martysmods.com/reshade/installing/reshademanualinjection/
