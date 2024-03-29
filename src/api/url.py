"""
This module allows the user to input a valid Google Street View
URL, set an image size (width and height), and the code
downloads the relevant file using a hidden thumbnail API
replicating the angle and zoom of the image represented
by the URL, which would be roughly seen on the Street View web app.

Here is an example of a valid Street View URL.
https://www.google.co.uk/maps/@51.5002793,-0.1490781,3a,87.2y,170.82h,66.46t/data=!3m6!1e1!3m4!1sL3GLvqpla79_pSq2fxUunw!2e0!7i16384!8i8192?entry=ttu

Dissecting this example URL provides the following useful information:

Latitude = 51.5002793 = degrees north or south of the equator.

Longitude = -0.1490781 = degrees east or west of the prime meridian.

Pitch = 87.2 = vertical camera orientation in degrees, where horizontal = 90.

Yaw = 170.82 = bearing in degrees relative to North.

FOV = 66.46 = field of view in degrees (smaller FOV, greater zoom).

Panorama ID = L3GLvqpla79_pSq2fxUunw
"""
import io
import time
from dataclasses import dataclass

import requests as rq
from PIL import Image

try:
    from api.panorama import validate_panorama_id
except ImportError:
    try:
        from panorama import validate_panorama_id
    except ImportError:
        from .panorama import validate_panorama_id


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
MAX_YAW = 360
MIN_PITCH = 1
MAX_PITCH = 179

URL_PARTS = 4
# View parameters as seen in the URLs.
URL_SUFFIXES = set("ayht")
MIN_DATA_STRING_PARTS = 5
PANORAMA_ID_PREFIX = "1s"


@dataclass
class StreetViewURL:
    """
    Relevant parsed street view URL information.
    The toplevel documentation explains each attribute.

    Whilst usually returned after URL parsing, the user may
    initialise an instance themselves, ensuring all inputs are valid.
    """
    # A value of the FOV as seen in the URL, between 15 and 90 degrees.
    fov: float
    # Horizontal/vertical offset in degrees.
    yaw: float
    pitch: float
    # Corresponding panorama ID embedded in the URL.
    panorama_id: str
    # Latitude/longitude coordinates.
    latitude: float = None
    longitude: float = None


def validate_dimensions(width: int, height: int) -> None:
    """
    Ensures width and height are in range integers.
    A sensible width and height range is in place.
    """
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
    Upon success, return a `StreetViewURL` object providing key information.

    This function can be powerfully used to parse a URL for its panorama
    ID, by accessing the `panorama_id` attribute of the return object.

    Key requirements:

    - Valid Google domain followed by /maps/

    - Valid latitude and longitude.

    - Valid a, y, h, t values in the URL (h can be omitted, 0 by default).
        y is pitch, h is yaw, t is FOV, a is irrelevant but must be present.

    - Panorama ID is followed by '1s' and must be deducible and valid.

    Other extra data is ignored, including query parameters.
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
    # Split URL into its separate parts. The number of parts must be correct.
    parts = url.split("/")
    if len(parts) != URL_PARTS:
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
        if not MIN_LATITUDE <= latitude <= MAX_LATITUDE:
            raise ValueError
    except Exception:
        raise ValueError("Invalid latitude.")
    try:
        longitude = float(longitude)
        if not MIN_LONGITUDE <= longitude <= MAX_LONGITUDE:
            raise ValueError
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
                            if parameter not in ("2a", "3a"):
                                raise ValueError
                        case "y":
                            fov = float(parameter.removesuffix("y"))
                            if not MIN_FOV <= fov <= MAX_FOV:
                                raise ValueError
                        case "h":
                            yaw = float(parameter.removesuffix("h"))
                            if not MIN_YAW <= yaw < MAX_YAW:
                                raise ValueError
                        case "t":
                            pitch = float(parameter.removesuffix("t"))
                            if not MIN_PITCH <= pitch <= MAX_PITCH:
                                raise ValueError
                except Exception:
                    raise ValueError(f"Invalid '{suffix}' value.")
                suffixes.remove(suffix)
                break
    for remaining_suffix in suffixes:
        if remaining_suffix != "h":
            raise ValueError(f"Missing '{remaining_suffix}' value")
        # Yaw or 'h' argument can be missing - set to 0 if the case.
        yaw = DEFAULT_YAW
    # Finally, extract panorama ID, validate and return.
    if not parts[-1].startswith("data="):
        raise ValueError("Invalid URL.")
    data_parts = parts[-1].split("!")
    if len(data_parts) < MIN_DATA_STRING_PARTS:
        raise ValueError("Invalid data string.")
    panorama_id_part = data_parts[4]
    if not panorama_id_part.startswith(PANORAMA_ID_PREFIX):
        raise ValueError("Invalid data string.")
    panorama_id = panorama_id_part.removeprefix(PANORAMA_ID_PREFIX)
    validate_panorama_id(panorama_id)
    return StreetViewURL(fov, yaw, pitch, panorama_id, latitude, longitude)


def get_pil_image(
    url: str, width: int = DEFAULT_WIDTH, height = DEFAULT_HEIGHT,
) -> Image.Image:
    """
    Takes a Google Street View URL and returns a PIL image with a
    given width and height representing the input URL,
    with the correct yaw, pitch and FOV.

    Note: the thumbnail API has slightly limited resolution so the image may
    be scaled up by the code if needed, without quality improvement.
    """
    validate_dimensions(width, height)
    url_info = parse_url(url)
    params = {
        "cb_client": "maps_sv.tactile", "output": "thumbnail",
        "panoid": url_info.panorama_id, "w": width, "h": height,
        # Pitch (vertical) [-89, 89] where positive is downwards.
        "yaw": url_info.yaw, "pitch": -(url_info.pitch - 90),
        "thumbfov": round(url_info.fov) # FOV must be integral,
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
    Takes a Google Street View URL and returns an JPEG image in bytes with a
    given width and height representing the input URL,
    with the correct yaw, pitch and FOV.

    Note: the thumbnail API has slightly limited resolution so the image may
    be scaled up by the code if needed, without quality improvement.
    """
    image = get_pil_image(url, width, height)
    with io.BytesIO() as f:
        image.save(f, format="jpeg")
        return f.getvalue()
