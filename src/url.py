"""
This module allows the user to input a valid Google Street View
URL (the full one, not a shorthand), set an image size, and
the code downloads the relevant panorama tiles and renders
an image to replicate the angle and zoom of the one represented
by the URL, which would be roughly seen on the web app.
"""
from dataclasses import dataclass
from PIL import Image

from panorama_id import validate_panorama_id


MIN_WIDTH = 32
MIN_HEIGHT = 16
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
MAX_WIDTH = 2048
MAX_HEIGHT = 2048
MIN_LATITUDE = -90
MAX_LATITUDE = 90
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180
MIN_ZOOM = 15
MAX_ZOOM = 90
MIN_HORIZONTAL_PAN = 0
MAX_HORIZONTAL_PAN = 359.999999999
MIN_VERTICAL_PAN = 1
MAX_VERTICAL_PAN = 179


@dataclass
class StreetViewURL:
    """Relevant street view URL information as required by the program."""
    latitude: float
    longitude: float
    # A value of the zoom as seen in the URL, between 15 and 90.
    # The larger is value, the smaller the zoom.
    zoom: float
    # Horizontal/vertical pan in degrees.
    horizontal_pan: float
    vertical_pan: float
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
    - Valid a, y, h, t values in the URL.
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
        latitude, longitude, a, y, h, t = position.split(",")
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
    if a != "3a":
        raise ValueError("Invalid 'a' value.")
    try:
        assert y.endswith("y")
        zoom = float(y.removesuffix("y"))
        assert MIN_ZOOM <= zoom <= MAX_ZOOM
    except Exception:
        raise ValueError("Invalid 'y' value.")
    try:
        assert h.endswith("h")
        horizontal_pan = float(h.removesuffix("h"))
        assert MIN_HORIZONTAL_PAN <= horizontal_pan <= MAX_HORIZONTAL_PAN
    except Exception:
        raise ValueError("Invalid 'h' value.")
    try:
        assert t.endswith("t")
        vertical_pan = float(t.removesuffix("t"))
        assert MIN_VERTICAL_PAN <= vertical_pan <= MAX_VERTICAL_PAN
    except Exception:
        raise ValueError("Invalid 't' value.")
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
    return StreetViewURL(
        latitude, longitude, zoom, horizontal_pan, vertical_pan, panorama_id)
    

def get_pil_image(
    url: str, width: int = DEFAULT_WIDTH, height = DEFAULT_HEIGHT
) -> Image.Image:
    """
    Takes a Google Street View URL and renders an image with a
    given width and height, with the correct zoom and angle.
    This is achieved by downloading the relevant panorama tiles
    and rendering them correctly from there on in.
    """
    validate_dimensions(width, height)
    url_info = parse_url(url)
    # TODO
