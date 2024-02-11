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
* If necessary change the "IR Protocol" to match your glasses, most settings templates should have this set correctly already. (Optional)
* Click "Update Settings" to send these settings to the emitter (Leave this window open but you can let it go into the background)
* Click the "Open disply settings" icon button on the main toolbar, and then the checkbox that says "Calibration Mode" at the bottom you can close this window.
* Click the "Open a video file for playback" icon button on the main toolbar, then click the "Select" button next to "Video File" and from the videos directory choose the file "test_video_red_left_blue_right.mp4" then click "Open"
* Use F11 or the "Toggle fullscreen" icon button on the main toolbar to make the video fullscreen.
* Physically align horizontally the 3d emitter alignment marker with the vertical alignment line on the screen to ensure it is centered.
* Use the y and h keys to move the horizontal alignment line up and down until it matches the 3d emitter alignment marker. 
* Put on your 3D glasses and turn them on after they synchronize ensure the right eye looks red and the left eye looks blue, you may see red and blue lines at the top and bottom of the screen on opposing eyes.
* Based on your decision earlier about ghosting vs vignetting at the top and bottom of the screen, follow the onscreen instructions using the i and k keys to adjust the start frame timing and the o and l keys to adjust the end frame timing. (You may want to repeat this with the black and white calibration videos as well if you are try to reduce cross talk, remember you can use the "F" hotkey to flip left and right eyes)
* When you are happy with the timings you can press the escape key to close the video or F11 to minimize the playback window.
* Next navigate back to the emitter settings window, you should see that "Frame Delay" and "Frame Duration" have no been updated to the optimized values obtained during calibration.
* Click "Save Settings to EEPROM" to make these settings persist next time your power up the 3d emitter.
* Click "Save Settings to Disk" to make a copy of your optimized 3d emitter settings locally incase for whatever reason you decide to experiment with a different type of 3d glasses.
* Click the "Open disply settings" icon button on the main toolbar, and disable the checkbox that says "Calibration Mode", you should see that the "Whitebox Vertical Position" has changed from "0" to whatever value you aligned it with.
* Click "Save Settings to Disk" to make a copy of your optimized display settings locally incase for whatever reason you decide to experiment with a different display.
* Click "Close" on the display settings window.
* Your now done and should be able to watch 3D videos on your OLED!
    
## FAQ, Useful Commands and Tips
* Supported TVs
```
Working (Tested)
LG C1 OLED
Sony OLED XBR 48a9s
Should Work (Untested)
LG C2 OLED
Other OLEDs with BFI technology.
LCD Monitors with strobed backlight for BFI and with front polarization that is compatible with 3D glasses (https://www.rtings.com/monitor/tests/motion/black-frame-insertion)
```
* Performance is best on Linux (tested on Ubuntu 20.04 an 22.04) followed by Windows 10. Windows 11 has problems with excessively dropping frames, it needs to be looked into. I haven't tested on Windows 7.
* if during development you get the error "Unable to find/initialize GStreamer plugin GSTPageflipGLSink." it can sometimes be solved by removing the gstreamer registry cache (and/or rebooting).
```
   rm  ~/.cache/gstreamer-1.0/registry.x86_64.bin
```   
* GStreamer has difficulty processing matroska packed videos with multi-language audio streams that have 5.1 or 7.1 channel audio, removing all but the language you want from the file can solve playback issues. This can be performed with ffmpeg as follows.
```
   ffmpeg -i Movie.7xAudio.mkv -map 0:v:0 -map 0:a:0 -c copy Movie.7xAudio.EngOnly.mkv
```   
* This software relies of strong BFI when run on OLED TV's. AMD graphics cards have a tendancy of turning on ALLM (Adaptive Low Latency Mode) in a way that cannot be turned off. ALLM forces BFI Off. The easiest way to disable ALLM is to use a registry hack as below (it requires rebooting after you change the value). CRU tool can also be used by it is more complicated and can affected HDMI audio so is not recommended.
```
   Goto GPU Registry Location: HKLM\System\CurrentControlSet\Control\Class{4d36e968-e325-11ce-bfc1-08002be10318}\0000 (or 0001/0002/..., check inside 0000 to verify that it is indeed your GPU)
   Add or Update the DalHdmiEnableALLM Entry as follows (Dword: DalHdmiEnableALLM, Value:0 for Disabled, 1 for Enabled)
```

## Development Installation Instructions

### Windows Developer Install:
```
 - install msys2 (https://stackoverflow.com/questions/37460073/msys-vs-mingw-internal-environment-variables)
 - follow steps at https://pygobject.readthedocs.io/en/latest/getting_started.html
 - open ucrt64 shell
 - pacman -Suy
 - pacman -S mingw-w64-ucrt-x86_64-gtk4 mingw-w64-ucrt-x86_64-python3 mingw-w64-ucrt-x86_64-python3-pip mingw-w64-ucrt-x86_64-python3-gobject mingw-w64-ucrt-x86_64-python-pygame mingw-w64-ucrt-x86_64-python-pyopengl mingw-w64-ucrt-x86_64-python-pyopengl-accelerate mingw-w64-ucrt-x86_64-python-numpy mingw-w64-ucrt-x86_64-python-cffi mingw-w64-ucrt-x86_64-python-wheel mingw-w64-ucrt-x86_64-python-pillow mingw-w64-ucrt-x86_64-python-pyusb mingw-w64-ucrt-x86_64-python-pyserial 
 - pacman -S mingw-w64-ucrt-x86_64-gstreamer mingw-w64-ucrt-x86_64-gst-devtools mingw-w64-ucrt-x86_64-gst-plugins-base mingw-w64-ucrt-x86_64-gst-plugin-gtk mingw-w64-ucrt-x86_64-gst-plugins-bad mingw-w64-ucrt-x86_64-gst-plugins-bad-libs mingw-w64-ucrt-x86_64-gst-plugins-good mingw-w64-ucrt-x86_64-gst-plugins-ugly mingw-w64-ucrt-x86_64-gst-python
 - pacman -S mingw-w64-ucrt-x86_64-python-psutil
 - pip install pysrt cairosvg pyinstaller pysdl2
 - building libgstpython.dll (https://gstreamer.freedesktop.org/documentation/installing/building-from-source-using-meson.html?gi-language=python)
  - pacman -S git mingw-w64-ucrt-x86_64-meson-python mingw-w64-ucrt-x86_64-cc mingw-w64-ucrt-x86_64-meson mingw-w64-ucrt-x86_64-ninja mingw-w64-ucrt-x86_64-pkg-config mingw-w64-ucrt-x86_64-pygobject-devel mingw-w64-ucrt-x86_64-python
  - git clone https://gitlab.freedesktop.org/gstreamer/gstreamer.git
  - cd gstreamer
  - git checkout 1.22.5
  - cd subprojects/gst-python/
  - meson build
  - cd build
  - ninja
  - cp plugin/libgstpython.dll /ucrt64/lib/gstreamer-1.0/libgstpython.dll
```
  
### Windows Standalone Application Build Instructions:
```
  - pip install pyinstaller
  - pyi-makespec \
    3d_player.py \
    --console \
    --onedir \
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
    pyinstaller 3d_player.spec
    
  - to get rid of gstreamer dll warnings on my system
    rm dist/3d_player/_internal/OpenGL/DLLS/*32.*
    rm dist/3d_player/_internal/OpenGL/DLLS/*.vc9.*
    rm dist/3d_player/_internal/OpenGL/DLLS/*.vc10.*

  - copy remaining assets and zip
    cp -R videos dist/3d_player/videos
    cp -R settings dist/3d_player/settings
    cd dist
    zip -r 3d_player.zip 3d_player
    
  - 3d_player.zip will be the equivalent of the release files available on the releases page.
```

# Licenses
Please refer to LICENSE files and license folders for references to open source licenses. If you find any missing licenses please open a support ticket.
<p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/open3doled/Open3DOLED">Open3DOLED</a> is licensed under <a href="http://creativecommons.org/licenses/by-nc-sa/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">CC BY-NC-SA 4.0<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/nc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1"></a></p> 

