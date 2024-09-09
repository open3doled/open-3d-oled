# Open3DOLED 

## Beta Testers Needed
I'm looking for beta testers who have potentially compatible displays.
I have 49 partially assembled units.
If you have a 120hz TV and it is either and OLED with BFI (@120hz), or an LCD with fast pixel response time your display may work, checkout [this fantastic table](https://www.rtings.com/tv/tools/table/138933) provided by rtings.com for relevant display parameters.
Just to be clear the beta units are not free, but produced near cost and bundled with a pair of panasonic glasses with custom firmware optimized for software pageflipping (see below for details about this).
Prices for the emitter and glasses start at $70 USD with untracked shipping or $90 USD with tracked ems shipping.
I will help you configure the unit to work with your display and help with any trouble shooting, if the unit does not work with your TV you can return it for a refund (minus cost of shipping).
In return all I ask is that you share the config settings that work best with your TV.
If interested contact me at: support at open3doled dot com.

## Introduction
Open3DOLED is a set of software and hardware designs that allow one to turn any display into a 3D display using compatible shutter glasses.  
It works best for displays that incorporate Black Frame Insertion (BFI) technologies and have framerates that exceed 120hz.  
This includes OLED TV's by the likes of LG and Sony which incorporate technologies like LG "Motion Pro" and Sony "Clearness" settings.  
It can also work on LCD TV's and monitors that have fast pixel response time, in such cases it works best if the TV supports HDMI/DVI QFT (Quick Frame Transport), this can be used to force a large vertical blanking interval during which time the image on the LCD will be static.  
It also has been tested to work on the latest Sony micro-LED TV's.  
If your compatibility information for your TV is not listed below, or you are considering buying a TV and would like to know if it might be compatible I would suggest referring to [this fantastic table](https://www.rtings.com/tv/tools/table/138933) provided by rtings.com  
You can compare, sort and filter by pixel response time, support for BFI 120hz, BFI duty cycle, PWM backlight fruency and duty cycle.  
There is a webstore in the works where you will be able to buy a pre-built/pre-programmed emitter unit in the next month or so once preliminary beta testing is complete..  
In the future custom firmware images that are optimized for software pageflipping for popular brands of glasses by Panasonic (and other manufacturers) may be released.  
(I plan to sell these glasses on the webstore initially along with the emitters to help recoup the over 200(?) hours put into this project, they reduce jitter greatly and eliminate crosstalk from dropped frames)  

## Glasses Warning
* If you are using Panasonic Gen2 (TY-EW3D2XX) glasses, do NOT turn them on while a USB charging cable is attached or you will destroy the left shutter element from DC bias.
* If you are using Panasonic Gen3 (TY-EW3D3XX) glasses, ONLY use a micro-usb power cable (like the one included), do not use a micro-usb cable with data lines or you will destroy the right shutter element  from DC bias.
* I didn't design the hardware for these glasses so unfortunately I cannot fix this issue, anything more than 1-2 seconds risks damaging them so always check the shutter elements when you plug them in and unplug it quickly, just incase you are using the wrong cable. (please be careful).

## Getting Started

### Configuring TV or Monitor
* Set your TV to 1080p 120hz (this system should work with 4K 120hz but hasn't been tested yet)
* If you are using an AMD/Intel graphics card and your TV switches to ALLM (adaptive low latency mode) you will need to disable ALLM as detailed in the FAQ below.
* On LG TV's you need to set OLED Motion Pro to the maximum value.
* On Sony TV's you need to set Motion Flow Clearness setting to MAX
* If you are using a high refresh rate monitor you will benefit from looking into QFT (HDMI quick frame transport) see [instructions](3DPlayer/settings/viewsonic_xg2431/how_to_setup_custom_resolution_with_quick_frame_transport.txt).

### Calibration and Playback
* Linux
  * Install 3DPlayer as described below.
* Windows
  * If you are using a display and glasses for which both an emitter_settings.json and display_settings.json file is available under the settings folder you can skip installing 3DPlayer and use [PotPlayer](PotPlayer/README.md) directly.
  * It is still recommended to install the 3DPlayer if you have time to ensure optimal calibration.
  * If either your glasses or display don't have a settings.json file you will need to install 3DPlayer as described below to perform calibration of the emitter and screen parameters.
  * Once calibration if you intend to use PotPlayer is complete save the required AVI-Synth script by clicking "Generate PotPlayer AVISynth Script" under "Display Settings", then load this script into PotPlayer.

## 3DPlayer Installation Instructions:

### Ubuntu Install:
* First time installation
```
apt update
apt upgrade
apt install git git-gui
cd ~
git clone https://github.com/open3doled/open-3d-oled.git
cd open-3d-oled/3DPlayer
sudo apt install gobject-introspection gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-gtk3 gstreamer1.0-plugins-bad libgstreamer-plugins-bad1.0-0 gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly python3-gst-1.0 gstreamer1.0-libav
sudo apt install python3 python3-pip python3-virtualenv python3-virtualenvwrapper python3-tk python3-pil.imagetk idle3 gstreamer1.0-python3-plugin-loader
sudo apt install python3-gi
echo "export WORKON_HOME=$HOME/.virtualenvs" >> ~/.bashrc
echo "VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3" >> ~/.bashrc
echo "source /usr/share/virtualenvwrapper/virtualenvwrapper.sh" >> ~/.bashrc
mkvirtualenv --system-site-packages open3doled
pip install -r requirements.txt
  if pyopengl-accelerate fails to install due to some numpy error https://github.com/mcfletch/pyopengl/issues/118 and your system has numpy installed via apt already you can try either of the following.
  ignore the system numpy with: pip install --ignore-installed -r requirements.txt
  don't use pyopengl-accelerate: remove pyopengl-accelerate from requirements.txt
python3 3d_player.py
```
* Running subsequently
```
workon open3doled
python3 3d_player.py

OR

~/.virtualenvs/open3doled/bin/python3 3d_player.py
```

### Windows Release Install:
Download the latest release version from the Releases page.
Unzip and run 3d_player.exe
The first time you run the program it can take a while to load all required libraries, please be patient.

If running windows 11 or 10 with DPI scaling be sure to disable it as follows.
1) Right click properties on 3d_player.exe in the 3DPlayer folder
2) Click on "Compatability" tab then click on the button at the bottom "Change high DPI settings"
3) At the very bottom check the box next to the text "Override high DPI scaling behavior. Scaling performed: Application"
4) Click OK on this sub dialog as well as the parent one

### Calibration

* Put the sensor bar on the top left corner of your TV and connect it to the PC you will be using to play your 3D videos.
* Start Open3DOLED 3DPlayer
* Click the "Open emitter settings" icon button on the main toolbar, and then in the emitter settings window "Connect" to your 3d emitter
* Click on "Load Settings From Disk" and select a profile for your TV and glasses from the "settings" directory. Some settings files are optimized to reduce vignetting (black at top and bottom of screen) and others are optimized to reduce ghosting (cross talk between left and right eye at top and bottom of screen), choose the settings file matching your preference.
* If you are using a none OLED display or a display for which settings are not already available it is recommended that you set "OPT101 Ignore All Duplicates" to 1. This can be disabled later, but will ensure the highest possibility the emitter can synchronize to your TV.
* If necessary change the "IR Protocol" to match your glasses, most settings templates should have this set correctly already. (Optional)
* Click "Update Settings" to send these settings to the emitter (Leave this window open but you can let it go into the background)
* Click the "Open disply settings" icon button on the main toolbar, and then the checkbox that says "Calibration Mode" at the bottom you can close this window.
* Click the "Open a video file for playback" icon button on the main toolbar, then click the "Select" button next to "Video File" and from the videos directory choose the file "ghosting_test_video_1080p_red_left_blue_right_side_by_side_full.mp4" then click "Open"
* Use F11 or the "Toggle fullscreen" icon button on the main toolbar to make the video fullscreen if it does not automatically go fullscreen
* Perform calibration using the onscreen callibration instructions paying consideration to the following points
  * Position the emitter and trigger boxes.
  * Adjust timing with a goal of either optimizing for zero ghosting (with some minor vignetting at top and bottom) or vignetting (with some minor ghosting at top and bottom).
* When you are happy with the calibration settings you can press the escape key to close the video or F11 to minimize the playback window.
* Next navigate back to the emitter settings window, you should see that "Frame Delay" and "Frame Duration" have no been updated to the optimized values obtained during calibration.
* Click "Save Settings to EEPROM" to make these settings persist next time your power up the 3d emitter.
* Click "Save Settings to Disk" to make a copy of your optimized 3d emitter settings locally incase for whatever reason you decide to experiment with a different type of 3d glasses.
* Click the "Open disply settings" icon button on the main toolbar, and disable the checkbox that says "Calibration Mode", you should see that the "Whitebox Vertical Position" has changed from "0" to whatever value you aligned it with.
* Click "Save Settings to Disk" to make a copy of your optimized display settings locally incase for whatever reason you decide to experiment with a different display.
* Click "Close" on the display settings window.
* Your now done and should be able to watch 3D videos on your OLED!
* Refer to this video for an example using a slightly dated version of the software if you need a demonstration of this proceedure https://youtu.be/tEjXUV8hVDs
    
### Command Line Interface
3DPlayer supports a simple command line interface for integration into systems like Kodi, if you implement scripts for a video management s ystem please let us know so we can link to them here.
If the "video-path" command line argument is supplied it will auto launch playback of that video using the default settings you have stored from prior usage.
Defaults can be overriden using additionally avaiable command line arguments to support videos with different formats and subtitle files.
```
Linux (in terminal):
python3 3d_player.py --video-path ./videos/ghosting_test_video_1080p_red_left_blue_right_side_by_side_full.mp4 --frame-packing side-by-side-full --right-eye right --display-resolution 1920x1080
Windows (in command prompt):
3d_player.exe --video-path ./videos/ghosting_test_video_1080p_red_left_blue_right_side_by_side_full.mp4 --frame-packing side-by-side-full --right-eye right --display-resolution 1920x1080
3d_player.exe --video-path "C:\open-3d-oled\3DPlayer\videos\ghosting_test_video_1080p_red_left_blue_right_side_by_side_full.mp4" --frame-packing side-by-side-full --right-eye right --display-resolution 1920x1080
```

## PotPlayer
For those who want the best and most versatile playback performnce on Windows it is recommended to use [PotPlayer](PotPlayer/README.md). 
Click [here](PotPlayer/README.md) for instructions on how to setup and PotPlayer.
    
## FAQ, Useful Commands and Tips
* Supported TVs
```
Working (Tested)
 - LG C1 OLED (Fully working with Motion Pro high setting with no crosstalk due to ~41% BFI duty cycle)
 - Sony OLED XBR 48a9s (Working with clearness high setting but the bottom and top 10% of the screen has crosstalk due to ~61% BFI duty cycle)
 - Viewsonic XG2431 (Works perfectly zero-ghosting without any BFI enabled at up to 144 hz shutter glasses refresh speed, you online need to setup a custom quick frame transport HDMI profile to get a blanking interval that matches more than 40% of the screen duty cycle, see https://forums.blurbusters.com/viewtopic.php?t=8946 or read the document in the corresponding settings folder)
 - Asus VG248QE LightBoost Capable (Works perfectly with [LightBoost enabled](https://blurbusters.com/zero-motion-blur/lightboost/), Works usably with lightboost turned off using "OPT101 Ignore All Duplicates")
Partially Working (Tested)
 - Sony X95K MiniLED (Used with "OPT101 Ignore All Duplicates", "Block Signal Detection Delay" 7500, on tv disable "Local Dimming" to reduce ghosting at top of screen, BFI 1, and run at native 4K from pc)
Untested (But should work well)
 - LG CX/GX/G1 OLED (These should work identical to LG C1 OLED but are as of yet untested)
 - Other OLEDs with 120hz BFI technology.
 - Any monitor without BFI with at least 144hz at 1080p and a G2G (grey to grey) pixel refresh under 1ms (Used with "OPT101 Ignore All Duplicates") (You will need to setup an HDMI QFT quick frame transport monitor profile and run the glasses at 110 or 120 hz)
Untested (But should work ok)
 - Any monitor without BFI with at least 120hz at 1080p and a G2G (grey to grey) pixel refresh under 1ms (Used with "OPT101 Ignore All Duplicates") (You will need to setup an HDMI QFT quick frame transport monitor profile and run the glasses at 90 or 100 hz)
Not Working (Untested)
 - LG C2/G2 OLED (Missing 120hz BFI)
 - LG C3/G3 OLED (Missing 120hz BFI)
```
* If you are using a non OLED display or a display for which settings are not already available it is recommended that you set "OPT101 Ignore All Duplicates" to 1 under Emitter Settings. This will ensure the highest possibility the emitter can synchronize to your TV, at the cost of not being able to detect duplicate frames and inform the glasses to resynchornize immediately. It will typically result in a resynchronization delay of 1-2 frames on a duplicate frame, you may be able to get satisfactory results without using this by tuning "OPT101 Block Signal Detection Delay" and "OPT101 Block N Subsequent Duplicates" to match your display characteristics.
* If you are using an LCD you will want to use HDMI QFT "Quick Frame Transport" (if available) to force a long blanking interval between frames. You basically run the monitor clock at for example 240hz but only send 120hz of data. That way 50% of the time the monitor will not be updating the physical screen. During this time the shutter glasses will open and show an image with minimal ghosting. Take a look at these [instructions](3DPlayer/settings/viewsonic_xg2431/how_to_setup_custom_resolution_with_quick_frame_transport.txt) for more details of how to enable this.
```
* If you display supports BFI and it is an LCD make sure the BFI is phase synchronized to the actual refresh rate. I do not believe this is actually done on many monitors. Even Viewsonic XG2431 doesn't phase synchronize it and you need to do this manually using the blurbusters tool. Unless the BFI/strobing is phase synchronized you may be better to just turn it off.
* Performance is best on Linux (tested on Ubuntu 20.04 an 22.04) followed by Windows 10 then Windows 11. I haven't tested on Windows 7.
* On Windows 11 when using a 4k display sometimes Windows decides to use "Active Signal Mode" resolution of 4k and have a "Display Resolution" of 1080p. This confuses the software so make sure your "Active signal mode" and "Display Resolution" match at either 1080P or 4K. Most users will not want to change this as it will cause text to be tiny on your PC but there is a workaround where this setting can be applied only to the 3d_player software, the following steps detail that process.
1) right click on the 3d_player.exe and goto "Properties"
2) select the compatabillity tab from the top
3) down near the bottom click the button "Change high DPI settings"
4) a new window titled "High DPI settings for 3d_player.exe" should open.
5) at the bottom select the checkbox next to "Override high DPI scaling behavior. Scaling performed by:"
6) click OK to close the window "High DPI settings for 3d_player.exe"
7) click OK to close the window "3d_player.exe Properties"
8) Now when you use the program on a screen with High DPI scaling the software should function with all necessary elements at the correct size.
```
* HDMI bitstream audio passthrough may have issues on some computers, if you are having difficulty it is recommended to disable HDMI audio passthrough and confirm the audio works on your local PC.
* For test videos beyond the calibration videos below are some recommendations (note the mvc mkv files will only work under PotPlayer currently).
```
   http://bbb3d.renderfarming.net/download.html
   https://kodi.wiki/view/Samples#3D_Test_Clips
```
* If gstreamer cannot initiate playback on a playback pipeline it will timeout after 15 seconds.
* GStreamer has difficulty processing matroska packed videos with multi-language audio streams that have 5.1 or 7.1 channel audio, removing all but the language you want from the file can solve playback issues. This can be performed with ffmpeg as follows.
```
   ffmpeg -i Movie.7xAudio.mkv -map 0:v:0 -map 0:a:0 -c copy Movie.7xAudio.EngOnly.mkv
```   
* This software relies of strong BFI when run on OLED TV's. AMD and Intel graphics cards have a tendancy of turning on ALLM (Adaptive Low Latency Mode) in a way that cannot be turned off. ALLM forces BFI Off. 
  * For AMD the easiest way to disable ALLM is to use a registry hack as below (it requires rebooting after you change the value).
```
   Goto GPU Registry Location: HKLM\System\CurrentControlSet\Control\Class{4d36e968-e325-11ce-bfc1-08002be10318}\0000 (or 0001/0002/..., check inside 0000 to verify that it is indeed your GPU)
   Add or Update the DalHdmiEnableALLM Entry as follows (Dword: DalHdmiEnableALLM, Value:0 for Disabled, 1 for Enabled)
```
  * For Intel [CRU tool](https://www.reddit.com/r/OLED_Gaming/comments/r3poj4/fullscreen_windows_10_games_enable_allm_which/) can also be used but it is more complicated and can be difficult to setup with proper HDMI audio.
* Emitter not working
```
   Sometimes when changing the glasses IR Protocol the emitter will enter an unresponsive state. If this happens save your settings to EEPROM and disconnect and reconnect it's power.
```

* If during development you get the error "Unable to find/initialize GStreamer plugin GSTPageflipGLSink." it can sometimes be solved by removing the gstreamer registry cache (and/or rebooting).
```
   rm  ~/.cache/gstreamer-1.0/registry.x86_64.bin
   rm "C:\Users\[USERNAME]\AppData\Local\Microsoft\Windows\INetCache\gstreamer-1.0\registry.x86_64-mingw.bin"
```  
* If you need to use line profiling to do performance analysis of gstpageflipglsink.py then use the following modified version of line profiler with a global enable flag and max time tracking.
```
   pip install git+https://github.com/46cv8/line_profiler.git@max_time ps
``` 
* On Linux based operating systems if you experience dropped/duplicate frames every few seconds you may benefit form disabling compositing if possible. Many window managers will auto bypass compositing with ["fullscreen unredirect"](https://www.reddit.com/r/linux_gaming/comments/u6dckj/comment/i57o5r4/) when you swtich to fullscreen mode, not to be confused with fullscreen windowed mode.

## Development Installation Instructions

### Windows Developer Install:
```
  - install msys2 (https://stackoverflow.com/questions/37460073/msys-vs-mingw-internal-environment-variables)
  - follow steps at https://pygobject.readthedocs.io/en/latest/getting_started.html
  - open ucrt64 shell
  - pacman -S git
  - git clone https://github.com/open3doled/open-3d-oled.git 
  - due to potential issues with the latest msys2 packages not working a copy of the latest working pacman database files are provided it is recommended you copy them over if you are having difficulty getting a build to work
    - cp -rf open-3d-oled/3DPlayer/building/msys2_pacman_db_files/* /var/lib/pacman/sync
  - pacman -Su (you can use "pacman -Suy" here to update your database files if you are trying to build using the latest packages otherwise omit the y option) (you will need to restart your ucrt64 shell after this)
  - pacman -Su
  - pacman -S mingw-w64-ucrt-x86_64-gtk4 mingw-w64-ucrt-x86_64-python3 mingw-w64-ucrt-x86_64-python3-pip mingw-w64-ucrt-x86_64-python3-gobject mingw-w64-ucrt-x86_64-python-pygame mingw-w64-ucrt-x86_64-python-pyopengl mingw-w64-ucrt-x86_64-python-pyopengl-accelerate mingw-w64-ucrt-x86_64-python-numpy mingw-w64-ucrt-x86_64-python-cffi mingw-w64-ucrt-x86_64-python-wheel mingw-w64-ucrt-x86_64-python-pillow mingw-w64-ucrt-x86_64-python-pyusb mingw-w64-ucrt-x86_64-python-pyserial 
  - pacman -S mingw-w64-ucrt-x86_64-gstreamer mingw-w64-ucrt-x86_64-gst-devtools mingw-w64-ucrt-x86_64-gst-plugins-base mingw-w64-ucrt-x86_64-gst-plugin-gtk mingw-w64-ucrt-x86_64-gst-plugins-bad mingw-w64-ucrt-x86_64-gst-plugins-bad-libs mingw-w64-ucrt-x86_64-gst-plugins-good mingw-w64-ucrt-x86_64-gst-plugins-ugly mingw-w64-ucrt-x86_64-gst-python mingw-w64-ucrt-x86_64-gst-libav
  - pacman -S mingw-w64-ucrt-x86_64-python-psutil
  - pip install pysrt cairosvg pyinstaller pysdl2
  - building libgstpython.dll (https://gstreamer.freedesktop.org/documentation/installing/building-from-source-using-meson.html?gi-language=python)
    - pacman -S git mingw-w64-ucrt-x86_64-meson-python mingw-w64-ucrt-x86_64-cc mingw-w64-ucrt-x86_64-meson mingw-w64-ucrt-x86_64-ninja mingw-w64-ucrt-x86_64-pkg-config mingw-w64-ucrt-x86_64-pygobject-devel mingw-w64-ucrt-x86_64-python
    - git clone https://gitlab.freedesktop.org/gstreamer/gstreamer.git
    - cd gstreamer
    - git checkout 1.22.9
    - cd subprojects/gst-python/
    - meson build
    - cd build
    - ninja
    - cp plugin/libgstpython.dll /ucrt64/lib/gstreamer-1.0/libgstpython.dll
  - cd open-3d-oled/3DPlayer
  - fix to ensure gst-plugin-scanner.exe builds a valid gstreamer plugin cache including our python plugin.
    - export PYTHONLEGACYWINDOWSDLLLOADING=1
  - test the application
    - python3 3d_player.py
   
  
  - if you run into issues where it says "Unable to find/initialize GStreamer plugin GSTPageflipGLSink." try deleting the gstreamer plugin registry
    - rm "C:\Users\[USERNAME]\AppData\Local\Microsoft\Windows\INetCache\gstreamer-1.0\registry.x86_64-mingw.bin"
 
  - If you run into issues about "ImportError('DLL load failed while importing _gi: The specified module could not be found.'))" try either of the following
    - export PYTHONLEGACYWINDOWSDLLLOADING=1
    - mv /ucrt64/libexec/gstreamer-1.0/gst-plugin-scanner.exe /ucrt64/libexec/gstreamer-1.0/gst-plugin-scanner.exe.bak
   
  - If the application fails with an error about Gst bad types make sure you don't have reminants from a pyinstaller build still around
    - rm -rf ~/open-3d-oled/3DPlayer/build
    - rm -rf ~/open-3d-oled/3DPlayer/dist
```
  
### Windows Standalone Application Build Instructions:
```
  - The official build system used ot build releases is Windows 10 22H2 with Intel HD Graphics and NVidia Drivers 552.12 (It shouldn't effect anything but it also has Windows WSL2 with all related packages installed)

  - pip install pyinstaller
  
  - build the 3d_player.spec file (be sure to do this if you update anything as the format may have changed)
  - it used to build fine without '--contents-directory "."' but now it seems to get a bunch of dll import errors without it at least when built under a VM, so you may be able to remove that directive and bundle all internal files in the _internal directory.
  
  - pyi-makespec \
    3d_player.py \
    --console \
    --onedir \
    --contents-directory "." \
    --hidden-import pygame \
    --hidden-import pygame._sdl2 \
    --hidden-import pygame.locals \
    --hidden-import OpenGL.GL \
    --hidden-import cairocffi \
    --hidden-import 'PIL._tkinter_finder' \
    --icon=.\\images\\movie-player_icon-icons.com_56259.ico

  - add the following to 3d_player.spec after Analysis is defined to ensure necessary images and gstreamer python modules are bundled
    a.datas += Tree('./images', prefix='images')
    a.datas += Tree('./python', prefix='python')
    
  - build the pyinstaller release dist 
    rm -rf ./dist 
    PYTHONLEGACYWINDOWSDLLLOADING=1 pyinstaller 3d_player.spec
    
  - to get rid of gstreamer dll warnings on my system
    rm dist/3d_player/OpenGL/DLLS/*32.*
    rm dist/3d_player/OpenGL/DLLS/*.vc9.*
    rm dist/3d_player/OpenGL/DLLS/*.vc10.*

  - copy remaining assets and zip
    cp -R videos dist/3d_player/videos
    cp -R settings dist/3d_player/settings
    rm dist/3d_player/settings/last_display_settings.json
    cp -R firmwares dist/3d_player/firmwares
    cp -R gstreamer_plugins_active /c/3D/3DPlayerWindowsLatest/gstreamer_plugins_active
    cp -R licenses dist/3d_player/licenses
    cp LICENSE dist/3d_player
    cd dist
    zip -r 3d_player.zip 3d_player
    
  - 3d_player.zip will be the equivalent of the release files available on the releases page.
  
  - when you are done remove the "dist" and "build" folder under 3DPlayer otherwise it will not run any longer due to finding invalid libraries with some error about Gst bad types.
    rm -rf dist
    rm -rf build
    

```

# Licenses
Please refer to LICENSE files and license folders for references to open source licenses. If you find any missing licenses please open a support ticket.
<p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/open3doled/Open3DOLED">Open3DOLED</a> is licensed under <a href="http://creativecommons.org/licenses/by-nc-sa/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">CC BY-NC-SA 4.0<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/nc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1"></a></p> 

