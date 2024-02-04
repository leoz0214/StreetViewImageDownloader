# Street View Image Downloader - Library

## Introduction
The backend code for the Street View Image Downloader is provided and available for use. This is a lightweight Python library consisting of two public modules for downloading two image variants: **panoramas** in equirectangular form and **URL** views (as seen in the Google Street View app).

## Requirements
The library has the following requirements:

- Python version >= 3.10
- Tested on Windows, should work on MacOS/Linux but not guaranteed.
- Third party dependencies (all very commonly used):
    - [aiohttp](https://pypi.org/project/aiohttp/)
    - [requests](https://pypi.org/project/requests/)
    - [PIL](https://pypi.org/project/pillow/)

The third party dependencies will be installed automatically when installing this library.

## Installation
You can install this library using pip as usual. The identifier of this library on PyPi is `streetview-download`

The PyPi page for this library is: https://pypi.org/project/streetview-download/

## Documentation
The modules of the library have been documented so that key information is available regarding usage of modules, functions and classes.

The documentation for this library is found here: https://streetviewimagedownloader.readthedocs.io/en/latest/

## Examples
Here are two extremely simple, minimal scripts asking the user for a panorama ID or URL, downloading and saving the JPEG.

Panorama (with moderate zoom).
```
from streetview_download.panorama import get_panorama, PanoramaSettings

# Zoom varies from 0 to 5
settings = PanoramaSettings(zoom=3)

panorama_id = input("Enter panorama ID: ")

# bytes returned
image = get_panorama(panorama_id, settings)

with open("output.jpg", "wb") as f:
    f.write(image)
```

URL (with default dimensions and using the PIL alternative).
```
from streetview_download.url import get_pil_image

url = input("Enter Google Street View URL: ")

# PIL image returned
pil_image = get_pil_image(url)

pil_image.save("output.jpg", format="jpeg")
```

These are barebones examples. For additional examples, see the [Examples](examples) folder and of course refer to the [Documentation](https://streetviewimagedownloader.readthedocs.io/en/latest/) for additional details, including how Google Street View panoramas and URLs work.
 
## Limitations/Warnings
The library is simple and effective, but there are pitfalls nonetheless, noted here:

- The URL view download has **limited resolution**, so do not expect very high quality images being generated.
- Only **official Google panoramas** are supported (22 characters long), not third-party contributor panoramas (44 characters long).
- High-zoom panoramas are **massive** (up to 16384x8192) and downloading entirely can take quite a lot of time and bandwidth, so be careful.
- Functionality may break at any time if Google decides to change or delete the hidden APIs or change the maps URL structure.
