# Street View Image Downloader

## Introduction

*Google Street View* is a powerful tool created by Google that allows users to view the world digitally, through 360° panoramic images captured worldwide. However, Google does not provide any direct functionality to save panoramas locally nor save rendered images seen through URLs, with the camera zoom and angle adjusted.

## Scope

This project involves downloading these Google Street View images, including panoramas and URL views, using exposed backend APIs discovered from the usage of these APIs by the Google Street View frontend.

For developers, a Python library is available for use, and there is also a desktop app with a GUI that makes this functionality more accessible, with some extra useful features.

### Library
The library can be considered the backend of the overall project, tested and functional.

Refer to the [LIB.md](https://github.com/leoz0214/StreetViewImageDownloader/tree/main/LIB.md) guide for information regarding the library setup and features.

### Desktop App
The desktop app indeed provides the core functionality of simply downloading panoramas and URL views as required, using the library. However, there are some additional features to enhance the convenience and usefulness of this app:

- **Batch downloading** is supported, so that multiple images can be processed at once given the inputs for each image.
- **Panorama rendering** is integrated, which takes a panorama and renders it on a square projection image, allowing camera angles to be adjusted.
- **Live downloading** is a unique, interesting feature that allows a tracked Chrome window to be opened, Google Street View opened, and subsequently the URL can be tracked and captured in real time, with images downloaded. There are many settings to customise this process.

Refer to [APP.md](https://github.com/leoz0214/StreetViewImageDownloader/tree/main/APP.md) for installation requirements and instructions, alongside detailed information on each feature in the app.

## Disclaimer

This project's license can be seen [here](https://github.com/leoz0214/StreetViewImageDownloader/tree/main/LICENSE). You are free to use the project as you wish, but THERE WILL BE NO LIABILITY FOR ANY ISSUES caused by usage of this project.

Google may change or delete the API endpoints used by the project at any time, possibly breaking the code.

Be aware that the project may break Google's Terms of Service, so you should proceed with caution if using either the library or app for anything but trival purposes.

Google provides a public [Street View API](https://developers.google.com/maps/documentation/javascript/streetview) that provides much deeper functionality and is a significantly safer option for more serious projects interfacing with Google Street View.

