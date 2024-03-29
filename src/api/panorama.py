"""
This module allows panorama images to be downloaded by their
internal panorama IDs. Each panorama ID is a string of 22
alphanumeric characters alongside - and _, found in Google
Street View URLs after '1s'. The user is responsible for obtaining
the panorama IDs for the panoramas they wish to download.

Here is an example of a URL and its corresponding panorama ID:
https://www.google.co.uk/maps/@51.5002793,-0.1490781,3a,75y,169.86h,65.89t/data=!3m6!1e1!3m4!1sL3GLvqpla79_pSq2fxUunw!2e0!7i16384!8i8192?entry=ttu

Panorama ID: L3GLvqpla79_pSq2fxUunw

Zooming in/out is supported, where there are 6 levels of zoom
from 0 to 5, with increased resolution for each level.

Partial panorama downloading is also possible, since panoramas
are split into square tiles, and as zoom increases, the number
of tiles increases, so a subset of tiles can be downloaded accordingly.
"""
import asyncio
import io
import itertools
import string
import time
from contextlib import suppress

import aiohttp
import requests as rq
from PIL import Image

try:
    from api._utils import _split_array, _in_rectangle
except ImportError:
    try:
        from _utils import _split_array, _in_rectangle
    except ImportError:
        from ._utils import _split_array, _in_rectangle


MIN_ZOOM = 0
MAX_ZOOM = 5
MIN_COORDINATES = (0, 0)

PANORAMA_ID_CHARACTERS = f"{string.ascii_letters}{string.digits}-_"
PANORAMA_ID_LENGTH = 22
PANORAMA_DOWNLOAD_API = "https://streetviewpixels-pa.googleapis.com/v1/tile"
MAX_RETRIES = 2
MAX_ASYNC_COROUTINES = 8
TILE_WIDTH = 512
TILE_HEIGHT = 512
MAX_BLACK = (5, 5, 5)


def _validate_zoom(zoom: int) -> None:
    if not isinstance(zoom, int):
        raise TypeError("Zoom must be an integer.")
    if zoom < MIN_ZOOM:
        raise ValueError(f"Zoom must be at least {MIN_ZOOM}.")
    if zoom > MAX_ZOOM:
        raise ValueError(f"Zoom must be {MAX_ZOOM} or less.")


def get_max_coordinates(zoom: int) -> tuple[int, int]:
    """
    Returns the maximum (bottom right) tile coordinates for a given zoom.
    If the return coordinate is (x, y), x is the number of columns
    and y is the number of rows.

    Max coordinates by zoom:

    0 - (1, 1) - 1 tile

    1 - (2, 1) - 2 tiles

    2 - (4, 2) - 8 tiles

    3 - (8, 4) - 32 tiles

    4 - (16, 8) - 128 tiles

    5 - (32, 16) - 512 tiles
    """
    _validate_zoom(zoom)  
    return (2 ** zoom, max(1, 2 ** (zoom - 1)))


def validate_coordinates(coordinates: tuple[int, int]) -> None:
    """Raises an error if coordinates is not a 2-tuple of integers."""
    # Expecting a tuple, accept a list too.
    if not isinstance(coordinates, (tuple, list)) or len(coordinates) != 2:
        raise TypeError("Coordinates must be a 2-tuple.")
    if not all(isinstance(value, int) for value in coordinates):
        raise TypeError("Coordinates must have integer points only.")


class PanoramaSettings:
    """
    Stores panorama download settings, including the level of zoom
    and the top left and bottom right coordinates. By default, zoom
    is 0 (minimum), and the entire panorama is downloaded.
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
        _validate_zoom(zoom)
        self._zoom = zoom
    
    def _set_top_left(self, top_left: tuple[int, int]) -> None:
        validate_coordinates(top_left)
        max_coordinates = get_max_coordinates(self.zoom)
        if not _in_rectangle(MIN_COORDINATES, max_coordinates, top_left):
            raise ValueError("Top-left coordinates out of bounds.")
        self._top_left = tuple(top_left)

    def _set_bottom_right(self, bottom_right: tuple[int, int]) -> None:
        validate_coordinates(bottom_right)
        max_coordinates = get_max_coordinates(self.zoom)
        if not _in_rectangle(MIN_COORDINATES, max_coordinates, bottom_right):
            raise ValueError("Bottom-right coordinates out of bounds.")
        # Top-left is always set first, then the bottom right, so ensure
        # here that the bottom right is greater than top left
        # on both the x and y axes.
        if (
            bottom_right[0] <= self.top_left[0]
            or bottom_right[1] <= self.top_left[1]
        ):
            raise ValueError(
                "Bottom-right coordinates must have x and y values "
                "greater than the top-left coordinates.")
        self._bottom_right = tuple(bottom_right)
    
    @property
    def zoom(self) -> int:
        """Current zoom level, between 0 and 5."""
        return self._zoom
    
    @property
    def top_left(self) -> tuple[int, int]:
        """Top-left coordinates (x, y)"""
        return self._top_left

    @property
    def bottom_right(self) -> tuple[int, int]:
        """Bottom-right coordinates (x, y)"""
        return self._bottom_right
    
    @property
    def tiles(self) -> int:
        """
        Total number of tiles covered by the current settings.
        Equivalent to the product of the width and height in tiles.
        """
        return self.width * self.height

    @property
    def width(self) -> int:
        """
        Width of the tiles covered by the settings (number of tiles across).
        """
        return self.bottom_right[0] - self.top_left[0]
    
    @property
    def height(self) -> int:
        """
        Height of the tiles covered by the settings (number of tiles down).
        """
        return self.bottom_right[1] - self.top_left[1]
    

def validate_panorama_id(panorama_id: str) -> None:
    """
    Performs validation on a panorama ID.
    The panorama ID must be a 22 character string consisting
    of letters, numbers, and dashes/underscores only.
    Note: the existence of valid panorama IDs is not checked.
    """
    if not isinstance(panorama_id, str):
        raise TypeError("Panorama ID must be a string.")
    if len(panorama_id) != PANORAMA_ID_LENGTH:
        raise ValueError(
            f"Panorama ID must be {PANORAMA_ID_LENGTH} characters long.")
    if any(char not in PANORAMA_ID_CHARACTERS for char in panorama_id):
        raise ValueError(
            "Panorama ID must only contain letters, numbers "
            "and dashes/underscores.")


async def _get_async_images_batch(
    array: list[list], batch: list[tuple], panorama_id: str,
    settings: PanoramaSettings, gui
) -> None:
    # Processes a batch of tiles to download for a given panorama ID.
    min_x, min_y = settings.top_left
    async with aiohttp.ClientSession() as session:
        for y, x in batch:
            params = {
                "cb_client": "maps_sv.tactile", "panoid": panorama_id,
                "x": x, "y": y, "zoom": settings.zoom
            }
            retries = MAX_RETRIES
            while True:
                # Check cancellation from GUI (if supplied).
                if gui is not None and gui.cancelled:
                    raise RuntimeError
                try:
                    async with session.get(
                        PANORAMA_DOWNLOAD_API, params=params
                    ) as response:
                        match response.status:
                            case 200:
                                array[y-min_y][x-min_x] = await response.read()
                                break
                            case 400:
                                raise rq.RequestException("400 - Bad Request")
                            case _:
                                raise rq.RequestException(
                                    f"{response.status} "
                                    "- something went wrong.")
                except Exception as e:
                    if not retries:
                        raise e
                    time.sleep(1)
                retries -= 1
    

async def _get_async_images(
    array: list[list], panorama_id: str, settings: PanoramaSettings, gui = None
) -> None:
    # Splits required tiles into batches.
    batches = _split_array(
        list(itertools.product(
            range(settings.top_left[1], settings.bottom_right[1]),
            range(settings.top_left[0], settings.bottom_right[0]))), 
        MAX_ASYNC_COROUTINES)
    await asyncio.gather(
        *(_get_async_images_batch(array, batch, panorama_id, settings, gui)
        for batch in batches))


def get_tiles(
    panorama_id: str, settings: PanoramaSettings = None, use_async: bool = True
) -> list[list[bytes]]:
    """
    Returns a 2D list of JPEG images in bytes, where each element is
    one tile at one (x, y) coordinate, as defined in the panorama settings.
    If `settings` are not provided, use the default settings.
    If `use_async` is set to True, then speed up image downloads using
    asynchronous processing. Otherwise, use serial requests.
    """
    validate_panorama_id(panorama_id)
    if settings is None:
        settings = PanoramaSettings()
    if not isinstance(settings, PanoramaSettings):
        raise TypeError("Settings must be a PanoramaSettings object.")
    if use_async and settings.tiles > 1:
        images = [[None] * settings.width for _ in range(settings.height)]
        with suppress(Exception):
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(_get_async_images(images, panorama_id, settings))
        return images
    # Serial requests.
    images = []
    for y in range(settings.top_left[1], settings.bottom_right[1]):
        image_row = []
        for x in range(settings.top_left[0], settings.bottom_right[0]):
            params = {
                "cb_client": "maps_sv.tactile", "panoid": panorama_id,
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
    return images


def get_pil_tiles(
    panorama_id: str, settings: PanoramaSettings = None, use_async: bool = True
) -> list[list[Image.Image]]:
    """
    Returns a 2D list of PIL images representing each downloaded tile.
    See the `get_tiles` documentation for more information.
    """
    tiles = get_tiles(panorama_id, settings, use_async)
    return [[Image.open(io.BytesIO(tile)) for tile in row] for row in tiles]


def _binary_search_black(
    width: int, height: int, pixels: Image.Image, gui, is_y: bool
) -> int:
    # First entirely black row/column in image preceded by one not the case.
    # Does not perform a complete check, only a systematic sample of pixels.
    minimum = 0
    upper = height - 1 if is_y else width - 1
    maximum = upper
    while True:
        if gui is not None and gui.cancelled:
            raise RuntimeError
        v = (minimum + maximum) // 2
        if is_y:
            is_black = not any(
                pixels[x, v] > MAX_BLACK
                for x in range(0, width, width // 100))
        else:
            is_black = not any(
                pixels[v, y] > MAX_BLACK
                for y in range(0, height, height // 100))
        if not is_black:
            # First black row/column to the right or below.
            minimum = v + 1
        elif v == 0:
            return v
        elif (
            (is_y and any(
                pixels[x, v - 1] > MAX_BLACK
                for x in range(0, width, width // 100)))
            or ((not is_y) and any(
                pixels[v - 1, y] > MAX_BLACK
                for y in range(0, height, height // 100)))
        ):
            # Previous row/column is first non-black one.
            return v - 1
        else:
            # First black row/column to the left or above.
            maximum = v - 1
        if minimum > maximum:
            # No black strip at bottom/right.
            return upper


def _combine_tiles(
    tiles: list[list[bytes]], crop_black_edges: bool, gui = None
) -> Image.Image:
    # Concatenates rows into single images and then
    # concatenates the rows into a single image.
    # Merge rows of tiles.
    rows = []
    for row in tiles:
        row_image = Image.new("RGB", (TILE_WIDTH * len(row), TILE_HEIGHT))
        for i, tile in enumerate(row):
            if gui is not None and gui.cancelled:
                raise RuntimeError
            tile = Image.open(io.BytesIO(tile))
            row_image.paste(
                tile, (TILE_WIDTH * i, 0, TILE_WIDTH * (i+1), TILE_HEIGHT))
        rows.append(row_image)
    # Merge rows to form entire image.
    width = rows[0].width
    height = TILE_HEIGHT * len(rows)
    image = Image.new("RGB", (width, height))
    for i, row in enumerate(rows):
        if gui is not None and gui.cancelled:
            raise RuntimeError
        image.paste(row, (0, TILE_HEIGHT * i, width, TILE_HEIGHT * (i+1)))
    if not crop_black_edges:
        return image
    pixels = image.load()
    # Quick check of top left 32x32 area. If this area is fully black,
    # then assume entire image is black and thus no information.
    if not any(any(pixels[x, y]) for y in range(32) for x in range(32)):
        return image.crop((0, 0, 0, 0))
    # Checks for bottom/right black edges and crops if necessary.
    x = _binary_search_black(width, height, pixels, gui, False)
    y = _binary_search_black(width, height, pixels, gui, True)
    if x == width - 1 and y == height - 1:
        # No cropping required.
        return image
    crop_box = (0, 0, x + 1, y + 1)
    return image.crop(crop_box)
    

def get_pil_panorama(
    panorama_id: str, settings: PanoramaSettings = None,
    use_async: bool = True, crop_black_edges: bool = True,
) -> Image.Image:
    """
    Downloads all required tiles of a panorama,
    and then merges the tiles together, returning a single PIL Image.
    Default panorama settings are used if not supplied.
    By default, asynchronous processing is used, otherwise serial
    requests are performed if `use_async` is set to False.
    Many panoramas have entirely black rows and columns at the
    bottom and on the right, which are stripped away provided
    `crop_black_edges` is set to True.
    """
    if settings is None:
        settings = PanoramaSettings()
    tiles = get_tiles(panorama_id, settings, use_async)
    return _combine_tiles(tiles, crop_black_edges)


def get_panorama(
    panorama_id: str, settings: PanoramaSettings = None,
    use_async: bool = True, crop_black_edges = True
) -> bytes:
    """
    Downloads all required tiles of a panorama, and then merges the tiles
    together, returning the resulting JPEG image in bytes.
    For more information, see the `get_pil_panorama` documentation.
    """
    image = get_pil_panorama(
        panorama_id, settings, use_async, crop_black_edges)
    with io.BytesIO() as f:
        image.save(f, format="jpeg")
        return f.getvalue()
