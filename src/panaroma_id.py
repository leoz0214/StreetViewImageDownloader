"""
This module allows panaroma images to be downloaded by the
internal panorama IDs. The user is responsible for obtaining
the panorama IDs for the panoramas they wish to download.
Also, zooming in/out is supported, alongside partial downloading.
"""
import io
import time

import requests as rq
from PIL import Image


MIN_ZOOM = 0
MAX_ZOOM = 5
MIN_COORDINATES = (0, 0)

PANORAMA_ID_LENGTH = 22
PANORAMA_DOWNLOAD_API = "https://streetviewpixels-pa.googleapis.com/v1/tile"
MAX_RETRIES = 2
TILE_WIDTH = 512
TILE_HEIGHT = 512


def get_max_coordinates(zoom: int) -> tuple[int, int]:
    """Returns the maximum coordinates for a given zoom."""
    return (2 ** zoom - 1, max(0, 2 ** (zoom - 1) - 1))


def validate_coordinates(coordinates: tuple[int, int]) -> None:
    """Raises an error if coordinates is not a 2-tuple of integers."""
    # Expecting a tuple, accept a list too.
    if not isinstance(coordinates, (tuple, list)) or len(coordinates) != 2:
        raise TypeError("Coordinates must be a 2-tuple.")
    if not all(isinstance(value, int) for value in coordinates):
        raise TypeError("Coordinates must have integer points only.")


def in_rectangle(
    top_left: tuple[int, int], bottom_right: tuple[int, int],
    coordinates: tuple[int, int]
) -> bool:
    """Returns True if coordinates lie in a given rectangle, else False."""
    return (
        top_left[0] <= coordinates[0] <= bottom_right[0]
        and top_left[1] <= coordinates[1] <= bottom_right[1])


class PanoramaSettings:
    """
    Allows the user to set the panorama download settings, including:
    - Level of zoom.
    - Top left and bottom right coordinates.
    """

    def __init__(
        self, zoom: int = 0, top_left: tuple[int, int] = None,
        bottom_right: tuple[int, int] = None
    ) -> None:
        self.update(zoom, top_left, bottom_right)
    
    def update(
        self, zoom: int, top_left: tuple[int, int],
        bottom_right: tuple[int, int]
    ) -> None:
        """Sets/updates the settings."""
        self._set_zoom(zoom)
        self._set_top_left(MIN_COORDINATES if top_left is None else top_left)
        if bottom_right is None:
            # Use maximum coordinates for the entire panorama (default).
            self._set_bottom_right(get_max_coordinates(self.zoom))
        else:
            self._set_bottom_right(bottom_right)
    
    def _set_zoom(self, zoom: int) -> None:
        """Internally sets the level of zoom."""
        if not isinstance(zoom, int):
            raise TypeError("Zoom must be an integer.")
        if zoom < MIN_ZOOM:
            raise ValueError(f"Zoom must be at least {MIN_ZOOM}.")
        if zoom > MAX_ZOOM:
            raise ValueError(f"Zoom must be {MAX_ZOOM} or less.")
        self._zoom = zoom
    
    def _set_top_left(self, top_left: tuple[int, int]) -> None:
        """Internally sets the top-left coordinates."""
        validate_coordinates(top_left)
        if not in_rectangle(
            MIN_COORDINATES, get_max_coordinates(self.zoom), top_left
        ):
            raise ValueError("Top-left coordinates out of bounds.")
        self._top_left = tuple(top_left)

    def _set_bottom_right(self, bottom_right: tuple[int, int]) -> None:
        """Internally sets the bottom-right coordinates."""
        validate_coordinates(bottom_right)
        if not in_rectangle(
            MIN_COORDINATES, get_max_coordinates(self.zoom), bottom_right
        ):
            raise ValueError("Bottom-right coordinates out of bounds.")
        # Top-left is always set first, then the bottom right, so ensure
        # here that the bottom right is greater than or equal to top left
        # on both the x and y axes.
        if (
            bottom_right[0] < self.top_left[0]
            or bottom_right[1] < self.top_left[1]
        ):
            raise ValueError(
                "Bottom-right coordinates must have x and y values "
                "greater than or equal to top-left coordinates.")
        self._bottom_right = tuple(bottom_right)
    
    @property
    def zoom(self) -> int:
        return self._zoom
    
    @property
    def top_left(self) -> tuple[int, int]:
        return self._top_left

    @property
    def bottom_right(self) -> tuple[int, int]:
        return self._bottom_right
    
    @property
    def tiles(self) -> int:
        """Number of tiles covered by the current settings."""
        return (
            self.bottom_right[0] - self.top_left[0] + 1
        ) * (self.bottom_right[1] - self.top_left[1] + 1)
    

def validate_panaroma_id(panaroma_id: str) -> None:
    """Performs basic validation on the panaroma ID."""
    if not isinstance(panaroma_id, str):
        raise TypeError("Panaroma ID must be a string.")
    if len(panaroma_id) != PANORAMA_ID_LENGTH:
        raise ValueError(f"Panorama ID must be {panaroma_id} characters long.")


def get_images(
    panaroma_id: str, settings: PanoramaSettings = None
) -> list[list[bytes]]:
    """
    Returns a 2D list of images in bytes,
    where each element is one tile at one (x, y) coordinate, as defined
    in the settings.
    If settings are not provided, use the default settings.
    """
    validate_panaroma_id(panaroma_id)
    if settings is None:
        settings = PanoramaSettings()
    images = []
    for y in range(settings.top_left[1], settings.bottom_right[1] + 1):
        image_row = []
        for x in range(settings.top_left[0], settings.bottom_right[0] + 1):
            params = {
                "cb_client": "maps_sv.tactile", "panoid": panaroma_id,
                "x": x, "y": y, "zoom": settings.zoom
            }
            retries = MAX_RETRIES
            while True:
                try:
                    response = rq.get(PANORAMA_DOWNLOAD_API, params)
                    match response.status_code:
                        case 200:
                            image_data = response.content
                            image_row.append(image_data)
                            break
                        case 400:
                            raise rq.RequestException("400 - Bad Request")
                        case _:
                            raise rq.RequestException(
                                f"{response.status_code} "
                                "- something went wrong.")
                except Exception as e:
                    if not retries:
                        raise e
                    time.sleep(1)
                retries -= 1
        images.append(image_row)
    if settings.zoom == 0:
        # When zoom = 0, there is a black strip at the bottom of the
        # single image. Remove it since it is useless.
        image = Image.open(io.BytesIO(images[0][0]))
        cropped = image.crop((0, 0, TILE_WIDTH, TILE_HEIGHT // 2))
        with io.BytesIO() as f:
            cropped.save(f, format="jpeg")
            images[0][0] = f.getvalue()
    return images
