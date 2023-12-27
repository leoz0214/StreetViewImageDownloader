"""Unit Tests the panaroma_id.py module."""
import unittest

import __init__
from panorama_id import *


class Test_panorama_id(unittest.TestCase):

    def test_validate_coordinates(self) -> None:
        self.assertRaises(TypeError, validate_coordinates, ("abc", "def"))
        self.assertRaises(TypeError, validate_coordinates, (5, 2.25))
        validate_coordinates((3, 0))
        validate_coordinates([1, 5])
    
    def test_PanoramaSettings(self) -> None:
        self.assertRaises(ValueError, PanoramaSettings, -1, (1, 2), (4, 5))
        self.assertRaises(ValueError, PanoramaSettings, 0, (3, 3), (2, 2))
        self.assertRaises(ValueError, PanoramaSettings, 0, (0, 0), (0, 0))
        settings = PanoramaSettings()
        self.assertEqual(settings.zoom, 0)
        self.assertEqual(settings.top_left, (0, 0))
        self.assertEqual(settings.bottom_right, (1, 1))
        self.assertEqual(settings.tiles, 1)
        self.assertRaises(ValueError, settings.update, 1, (1, 0), (3, 4))
        settings.update(5, (0, 0), get_max_coordinates(5))
        self.assertEqual(settings.tiles, 512)
    
    def test_validate_panorama_id(self) -> None:
        self.assertRaises(TypeError, validate_panorama_id, 123456)
        self.assertRaises(ValueError, validate_panorama_id, "tooShort12345")
        validate_panorama_id("*"*22)
    
    def test_get_images(self) -> None:
        self.assertRaises(rq.RequestException, get_images, "*"*22)
        images = get_images("xbK9YuuJe1GMpPPMqGFocA")
        images[0][0]
        images = get_images(
            "xbK9YuuJe1GMpPPMqGFocA",
            PanoramaSettings(zoom=5, top_left=(10, 10), bottom_right=(13, 14)))
        count = sum(map(len, images))
        self.assertEqual(count, 12)
        images = get_images(
            "xbK9YuuJe1GMpPPMqGFocA",
            PanoramaSettings(zoom=5, top_left=(8, 10), bottom_right=(9, 13)),
            use_async=False)
        count = sum(map(len, images))
        self.assertEqual(count, 3)

    def test_get_pil_images(self) -> None:
        images = get_pil_images("xbK9YuuJe1GMpPPMqGFocA", PanoramaSettings(2))
        for row in images:
            for tile in row:
                self.assertIsInstance(tile, Image.Image)
    
    def test_get_image(self) -> None:
        self.assertRaises(
            ValueError, get_image,
            "xbK9YuuJe1GMpPPMqGFocA", PanoramaSettings(zoom=5))
        self.assertIsInstance(get_image("xbK9YuuJe1GMpPPMqGFocA"), bytes)
        get_image("xbK9YuuJe1GMpPPMqGFocA", PanoramaSettings(zoom=2))
        get_image(
            "xbK9YuuJe1GMpPPMqGFocA", PanoramaSettings(3, top_left=(1, 1)))
        get_image(
            "xbK9YuuJe1GMpPPMqGFocA", PanoramaSettings(5, top_left=(28, 12)))
    
    def test_get_pil_image(self) -> None:
        self.assertIsInstance(
            get_pil_image("xbK9YuuJe1GMpPPMqGFocA", PanoramaSettings(zoom=1)),
            Image.Image)


if __name__ == "__main__":
    unittest.main()
