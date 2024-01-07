"""
This module allows the user to input a valid Google Street View
URL (the full one, not a shorthand), set an image size, and
the code downloads the relevant file using a hidden thumbnail API
replicating the angle and zoom of the image represented
by the URL, which would be roughly seen on the web app.
This includes handling pitch, yaw and zoom correctly.
"""
import io
import time
from dataclasses import dataclass

import requests as rq
from PIL import Image

from panorama_id import validate_panorama_id


THUMBNAIL_API = "https://geo0.ggpht.com/cbk"
MAX_RETRIES = 2

MIN_WIDTH = 32
MIN_HEIGHT = 16
DEFAULT_WIDTH = 768
DEFAULT_HEIGHT = 768
MAX_WIDTH = 2048
MAX_HEIGHT = 2048
MIN_LATITUDE = -90
MAX_LATITUDE = 90
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180
MIN_FOV = 15
MAX_FOV = 90
MIN_YAW = 0
DEFAULT_YAW = 0
MAX_YAW = 359.999999999
MIN_PITCH = 1
MAX_PITCH = 179
URL_SUFFIXES = set("ayht")


@dataclass
class StreetViewURL:
    """Relevant parsed street view URL information."""
    latitude: float
    longitude: float
    # A value of the FOV as seen in the URL, between 15 and 90.
    fov: float
    # Horizontal/vertical offset in degrees.
    yaw: float
    pitch: float
    # Corresponding panorama ID embedded in the URL.
    panorama_id: str


def validate_dimensions(width: int, height: int) -> None:
    """Ensures width and height are in range integers."""
    if not (isinstance(width, int) and isinstance(height, int)):
        raise TypeError("Width and height must be integers.")
    if not MIN_WIDTH <= width <= MAX_WIDTH:
        raise ValueError(
            f"Width must be between {MIN_WIDTH} and {MAX_WIDTH} pixels.")
    if not MIN_HEIGHT <= height <= MAX_HEIGHT:
        raise ValueError(
            f"Height must be between {MIN_HEIGHT} and {MAX_HEIGHT} pixels.")


def parse_url(url: str) -> StreetViewURL:
    """
    Thoroughly validates and parses a Google Street View URL.
    In the process, return the parsed URL with the key information.
    Key Points:
    - Valid Google domain followed by /maps/
    - Valid latitude and longitude
    - Valid a, y, h, t values in the URL (h can be omitted, 0 by default).
    - Panorama ID is followed by '1s' and must be deducible and valid.
    - Ignore other data, including query parameters.
    """
    if not isinstance(url, str):
        raise TypeError("URL must be a string.")
    # Ignore valid protocols by stripping them away.
    for protocol in ("http://", "https://"):
        if url.startswith(protocol):
            url = url.removeprefix(protocol)
            break
    # Ignore www. and trailing forward slashes (not relevant)
    url = url.removeprefix("www.").rstrip("/")
    parts = url.split("/")
    if len(parts) != 4:
        raise ValueError("Invalid URL.")
    if not (parts[0].startswith("google.") and parts[0] != "google."):
        raise ValueError("Invalid protocol or Google domain.")
    if parts[1] != "maps":
        raise ValueError("Invalid URL.")
    position = parts[2]
    if not position.startswith("@"):
        raise ValueError("Invalid URL.")
    position = position.removeprefix("@")
    # Get all position information, raising an error if anything is wrong.
    try:
        latitude, longitude, *parameters = position.split(",")
    except ValueError:
        raise ValueError("Invalid URL.")
    try:
        latitude = float(latitude)
        assert MIN_LATITUDE <= latitude <= MAX_LATITUDE
    except Exception:
        raise ValueError("Invalid latitude.")
    try:
        longitude = float(longitude)
        assert MIN_LONGITUDE <= longitude <= MAX_LONGITUDE
    except Exception:
        raise ValueError("Invalid longitude.")
    suffixes = URL_SUFFIXES.copy()
    for parameter in parameters:
        for suffix in URL_SUFFIXES:
            if parameter.endswith(suffix):
                if suffix not in suffixes:
                    raise ValueError(f"Invalid URL.")
                try:
                    match suffix:
                        case "a":
                            assert parameter in ("2a", "3a")
                        case "y":
                            fov = float(parameter.removesuffix("y"))
                            assert MIN_FOV <= fov <= MAX_FOV
                        case "h":
                            yaw = float(parameter.removesuffix("h"))
                            assert MIN_YAW <= yaw <= MAX_YAW
                        case "t":
                            pitch = float(parameter.removesuffix("t"))
                            assert MIN_PITCH <= pitch <= MAX_PITCH
                except Exception:
                    raise ValueError(f"Invalid '{suffix}' value.")
                suffixes.remove(suffix)
                break
    for remaining_suffix in suffixes:
        if remaining_suffix != "h":
            raise ValueError(f"Missing '{remaining_suffix}' value")
        yaw = DEFAULT_YAW
    # Finally, extract panorama ID, validate and return.
    if not parts[-1].startswith("data="):
        raise ValueError("Invalid URL.")
    data_parts = parts[-1].split("!")
    if len(data_parts) < 5:
        raise ValueError("Invalid data string.")
    panorama_id_part = data_parts[4]
    if not panorama_id_part.startswith("1s"):
        raise ValueError("Invalid data string.")
    panorama_id = panorama_id_part.removeprefix("1s")
    validate_panorama_id(panorama_id)
    return StreetViewURL(latitude, longitude, fov, yaw, pitch, panorama_id)


def get_pil_image(
    url: str, width: int = DEFAULT_WIDTH, height = DEFAULT_HEIGHT,
) -> Image.Image:
    """
    Takes a Google Street View URL and returns a PIL Image with a
    given width and height, with the correct zoom and angle.
    """
    validate_dimensions(width, height)
    url_info = parse_url(url)
    params = {
        "cb_client": "maps_sv.tactile", "output": "thumbnail",
        "panoid": url_info.panorama_id, "w": width, "h": height,
        # Pitch (vertical) [-90, 90] where positive is downwards.
        "yaw": url_info.yaw, "pitch": -(url_info.pitch - 90),
        "thumbfov": round(url_info.fov) # Must be integer,
    }
    retries = MAX_RETRIES
    while True:
        try:
            response = rq.get(THUMBNAIL_API, params=params)
            match response.status_code:
                case 200:
                    image = Image.open(io.BytesIO(response.content))
                    if image.size == (width, height):
                        return image
                    return image.resize((width, height))
                case 400:
                    raise rq.RequestException("400 - Bad Request")
                case _:
                    raise rq.RequestException(
                        f"{response.status_code} - something went wrong.")
        except Exception as e:
            if not retries:
                raise e
            time.sleep(1)
        retries -= 1


def get_image(
    url: str, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
) -> bytes:
    """
    Takes a valid Google Street View URL and returns the image bytes
    representing the display rendered at the given URL, based on
    the camera yaw, pitch and zoom.
    """
    image = get_pil_image(url, width, height)
    with io.BytesIO() as f:
        image.save(f, format="jpeg")
        return f.getvalue()
