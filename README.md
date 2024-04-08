# Open3DOLED 

## Introduction
Open3DOLED is a set of software and hardware designs that allow one to turn any display into a 3D display using compatible shutter glasses.
It works best for displays that incorporate Black Frame Insertion (BFI) technologies and have framerates that exceed 120hz.
This includes OLED TV's by the likes of LG and Sony which incorporate technologies like LG "Motion Pro" and Sony "Clearness" settings.
But it should also works with LCD displays that include strobed backlight like those mentioned at https://www.rtings.com/monitor/tests/motion/black-frame-insertion
In the future support will be added to do manual black frame insertion on displays with a framerate of 200hz or greater.
Also there is a webstore in the works where you will be able to buy a pre-built/pre-programmed emitter unit in the next month or so once preliminary beta testing is complete..
In the future custom firmware images that are optimized for software pageflipping for popular brands of glasses by Sony and Panasonic may be released. 
(I plan to sell these glasses on the webstore initially along with the emitters to help recoup the over 200(?) hours put into this project, they reduce jitter greatly and eliminate crosstalk from dropped frames)

## Installation Instructions:

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

## Getting Started

### Configuring TV and Computer
* Set your TV to 1080p 120hz (this system should work with 4K 120hz but hasn't been tested yet)
* If you are using an AMD graphics card and your TV switches to ALLM (adaptive low latency mode) you will need to disable ALLM as detailed in the FAQ below.
* On LG TV's you need to set OLED Motion Pro to the maximum value.
* On Sony TV's you need to set Motion Flow Clearness setting to MAX

### Calibration

* Put the sensor bar on the top right corner of your TV and connect it to the PC you will be using to play your 3D videos.
* Start Open3DOLED 3DPlayer
* Click the "Open emitter settings" icon button on the main toolbar, and then in the emitter settings window "Connect" to your 3d emitter
* Click on "Load Settings From Disk" and select a profile for your TV and glasses from the "settings" directory. Some settings files are optimized to reduce vignetting (black at top and bottom of screen) and others are optimized to reduce ghosting (cross talk between left and right eye at top and bottom of screen), choose the settings file matching your preference.
* If you are using a none OLED display or a display for which settings are not already available it is recommended that you set "OPT101 Ignore All Duplicates" to 1. This can be disabled later, but will ensure the highest possibility the emitter can synchronize to your TV.
* If necessary change the "IR Protocol" to match your glasses, most settings templates should have this set correctly already. (Optional)
* Click "Update Settings" to send these settings to the emitter (Leave this window open but you can let it go into the background)
* Click the "Open disply settings" icon button on the main toolbar, and then the checkbox that says "Calibration Mode" at the bottom you can close this window.
* Click the "Open a video file for playback" icon button on the main toolbar, then click the "Select" button next to "Video File" and from the videos directory choose the file "test_video_red_left_blue_right.mp4" then click "Open"
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
    
## FAQ, Useful Commands and Tips
* Supported TVs
```
Working (Tested)
 - LG C1 OLED (Fully working with Motion Pro high setting with no crosstalk due to ~41% BFI duty cycle)
 - Sony OLED XBR 48a9s (Working with clearness high setting but the bottom and top 10% of the screen has crosstalk due to ~61% BFI duty cycle)
 - Asus VG248QE LightBoost Capable (Works perfectly with [LightBoost enabled](https://blurbusters.com/zero-motion-blur/lightboost/), Works usably with lightboost turned off using "OPT101 Ignore All Duplicates")
Partially Working (Tested)
 - Sony X95K MiniLED (Used with "OPT101 Ignore All Duplicates", "Block Signal Detection Delay" 7500, on tv disable "Local Dimming" to reduce ghosting at top of screen, BFI 1, and run at native 4K from pc)
Untested (But should work well)
 - LG CX/GX/G1 OLED (These should work identical to LG C1 OLED but are as of yet untested)
 - Other OLEDs with 120hz BFI technology.
 - LCD monitors with strobed backlight for BFI and with front polarization that is compatible with 3D glasses (https://www.rtings.com/monitor/tests/motion/black-frame-insertion)
 - Any monitor with strobed backlight for blur reduction (eg NVIDIA "Ultra Low Motion Blur" (ULMB), EIZO "Turbo240", ASUS "Extreme Low Motion Blur" (ELMB), BenQ "Blur Reduction", BenQ/Zowie "Dynamic Acceleration" (DyAc)) (https://blurbusters.com/faq/120hz-monitors/)
 Untested (But should work ok)
 - Any monitor with at least 120hz at 1080p and a G2G (grey to grey) pixel refresh under 1ms (Used with "OPT101 Ignore All Duplicates", "Block Signal Detection Delay" 7500)
Not Working (Untested)
 - LG C2/G2 OLED (Missing 120hz BFI)
 - LG C3/G3 OLED (Missing 120hz BFI)
```
* If you are using a non OLED display or a display for which settings are not already available it is recommended that you set "OPT101 Ignore All Duplicates" to 1 under Emitter Settings. This will ensure the highest possibility the emitter can synchronize to your TV, at the cost of not being able to detect duplicate frames and inform the glasses to resynchornize immediately. It will typically result in a resynchronization delay of 1-2 frames on a duplicate frame, you may be able to get satisfactory results without using this by tuning "OPT101 Block Signal Detection Delay" and "OPT101 Block N Subsequent Duplicates" to match your display characteristics.
* Performance is best on Linux (tested on Ubuntu 20.04 an 22.04) followed by Windows 10 then Windows 11. I haven't tested on Windows 7.
* On Windows 11 when using a 4k display sometimes Windows decides to use "Active Signal Mode" resolution of 4k and have a "Display Resolution" of 1080p. This confuses the software so make sure your "Active signal mode" and "Display Resolution" match at either 1080P or 4K.
* HDMI bitstream audio passthrough may have issues on some computers, if you are having difficulty it is recommended to disable HDMI audio passthrough and confirm the audio works on your local PC.
* For test videos beyond the calibration videos below are some recommendations
```
   http://bbb3d.renderfarming.net/download.html
```
* If gstreamer cannot initiate playback on a playback pipeline it will timeout after 15 seconds.
* GStreamer has difficulty processing matroska packed videos with multi-language audio streams that have 5.1 or 7.1 channel audio, removing all but the language you want from the file can solve playback issues. This can be performed with ffmpeg as follows.
```
   ffmpeg -i Movie.7xAudio.mkv -map 0:v:0 -map 0:a:0 -c copy Movie.7xAudio.EngOnly.mkv
```   
* This software relies of strong BFI when run on OLED TV's. AMD graphics cards have a tendancy of turning on ALLM (Adaptive Low Latency Mode) in a way that cannot be turned off. ALLM forces BFI Off. The easiest way to disable ALLM is to use a registry hack as below (it requires rebooting after you change the value). CRU tool can also be used by it is more complicated and can affected HDMI audio so is not recommended.
```
   Goto GPU Registry Location: HKLM\System\CurrentControlSet\Control\Class{4d36e968-e325-11ce-bfc1-08002be10318}\0000 (or 0001/0002/..., check inside 0000 to verify that it is indeed your GPU)
   Add or Update the DalHdmiEnableALLM Entry as follows (Dword: DalHdmiEnableALLM, Value:0 for Disabled, 1 for Enabled)
```
* Emitter not working
```
   Sometimes when changing the glasses IR Protocol the emitter will enter an unresponsive state. If this happens save your settings to EEPROM and disconnect and reconnect it's power.
```

* If during development you get the error "Unable to find/initialize GStreamer plugin GSTPageflipGLSink." it can sometimes be solved by removing the gstreamer registry cache (and/or rebooting).
```
   rm  ~/.cache/gstreamer-1.0/registry.x86_64.bin
   rm "C:\Users\[USERNAME]\AppData\Local\Microsoft\Windows\INetCache\gstreamer-1.0\registry.x86_64-mingw.bin"
```   

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

