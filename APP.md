# Street View Image Downloader - App

The Street View Image Downloader app is a convenient deskop application that provides the library functionality alongside additional features.

These are the features in the app summarised:
- **Download by Panorama ID** - a panorama ID is input, the zoom level is set, and the panorama tile range to download can also be set.
- **Download by URL** - a Google Street View URL is input and the output width and height is set.
- **Batch Download** - download multiple panoramas or URLs by setting the panorama ID, file save path or URL, file save path pairs.
- **Panorama Rendering** - project a panorama onto a square image and allow mouse movement to adjust the yaw, pitch and FOV, updating the display accordingly.
- **Live Downloading** - opening a tracked Chrome window and capturing Street View URLs to download either panoramas or URL views, with many settings to control the flow.

## Requirements

The app can be run in two ways, as an executable or through Python, with the former being much simpler to set up.

Note, the app is only supported for **Windows**.

### Running through EXE
A pre-built standalone Windows EXE is available in a Release, which can be downloaded and run directly.

Upon running the EXE, if successful, the app will launch on the main menu.

### Running through Python
Alternatively, for more advanced users, or those who have security policies barring running external EXEs, it is also possible to run the program through Python.

Follow these steps to set up and run the code:
1. Download the source code from a Release.
2. Ensure Python version **3.10** or above is installed and in use.
3. Ensure the following third party libraries are installed.
    - [aiohttp](https://pypi.org/project/aiohttp/)
    - [requests](https://pypi.org/project/requests/)
    - [pillow](https://pypi.org/project/pillow/)
    - [psutil](https://pypi.org/project/psutil/)
    - [pyglet](https://pypi.org/project/pyglet/)
To install these libraries, use pip, something like this: `pip install aiohttp requests pillow psutil pyglet`
4. Some C++ code is also used in this project for performance and API reasons. Two optional C++ object files can be added, namely `conversion.so` for fast panorama rendering and `foreground.so` for a function to return the PID of the current foreground window. Without `conversion.so`, panorama rendering will be disabled. Without `foreground.so`, keybind detection in the live downloader will fail. These object files are available in the corresponding Release that you downloaded the source code from.
    - Download the object files.
    - Add them into the `gui/cpp` folder containing the C++ source files. Do not rename them.
    - If you plan to modify and re-compile the C++ code yourself, note that `conversion.so` is a shared library formed by compiling `cubemap.cpp` and `projection.cpp` and `foreground.so` is a shared library by compiling `foreground.cpp`. For example, for `conversion.so`, the following g++ command has been used with `gui/cpp` as the current working directory: `g++ cubemap.cpp projection.cpp --static --shared -o conversion.so -O2`.
5. Run the `main.py` module in the `gui` folder. If successful, the app will launch on the main menu.

## Download by Panorama ID

## Download by URL

## Batch Download

## Panorama Rendering

## Live Downloading

## Limitations