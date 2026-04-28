# ROV-GUI (laptop workspace)
This is the simplest setup that we used before and were sure that it would work again because we were running out of time. the setup can be summarized as:
- have ros-jazzy installed on system
- make a venv that sees the system packages with uv
- git clone opencv (already added in this repo you don't have to clone it again) and compile it with gstreamer
- install torch and torchvision for cuda 13
- make a python package for gui that depends on crab and information sheet packages (also pygame, paramiko,pyqt5,screeninfo, pygame and other stuff)
- add gui package to the venv using uv github url

## Building Virtual Environment

Since opencv is already on this repo you don't need to clone it but just in case here is the [article](https://galaktyk.medium.com/how-to-build-opencv-with-gstreamer-b11668fa09c) that we used across the years to compile it from source. Given that we already have opencv present here is the steps that I repeated in a cycle until I got the wanted environment.

1. `uv venv --system-site-packages`
1. `. .venv/bin/activate`
1. `uv pip install 'numpy<2'`
1. `cd opencv/build/`
1. `cmake -D CMAKE_BUILD_TYPE=RELEASE -D INSTALL_PYTHON_EXAMPLES=ON -D INSTALL_C_EXAMPLES=OFF -D PYTHON_EXECUTABLE=$(which python3) -D BUILD_opencv_python2=OFF -D CMAKE_INSTALL_PREFIX=$(python3 -c "import sys; print(sys.prefix)") -D PYTHON3_EXECUTABLE=$(which python3) -D PYTHON3_INCLUDE_DIR=$(python3 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") -D PYTHON3_PACKAGES_PATH=$(python3 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") -D WITH_GSTREAMER=ON -D BUILD_EXAMPLES=ON ..`
1. `sudo make -j$(nproc)`
1. `sudo make install`
1. `sudo ldconfig` # this is probably not required idk
1. `cd ../..`
1. `sudo uv pip install torch torchvision screeninfo paramiko PyQt5 pygame 'numpy<2' git+https://github.com/ejustroboticsclub/mate-rov-2026-information-sheet-problem.git@v3 git+https://github.com/ejustroboticsclub/mate-rov-2026-crab-detection.git@v5`

## Notes
- you can see that the task for 3d model is not here because it only needs blender and a single file that will be registered as an addon on blender. As for length measurement it was installed globally on another pc that has stronger cuda support. check its repo and installation steps seperately.
- you can find the blender addon as a single script inside `./scripts/pvc_blender_addon.py` the steps for adding a blender addon is easy to follow from any tutorial on the internet. blender -> Edit -> preferences -> Add-ons -> click on down arrow -> Install from disk -> choose script.
- using the frozed crab detection button requires downloading the onnx model to the path `./src/rov_gui/best_v4_all4.onnx`
