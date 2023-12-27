"""Unit Tests the panaroma_id.py module."""
import unittest

import __init__
from panaroma_id import *


class Test_panaroma_id(unittest.TestCase):

    def test_validate_coordinates(self) -> None:
        self.assertRaises(TypeError, validate_coordinates, ("abc", "def"))
        self.assertRaises(TypeError, validate_coordinates, (5, 2.25))
        validate_coordinates((3, 0))
        validate_coordinates([1, 5])
    
    def test_PanaromaSettings(self) -> None:
        self.assertRaises(ValueError, PanoramaSettings, -1, (1, 2), (3, 4))
        self.assertRaises(ValueError, PanoramaSettings, 0, (3, 3), (2, 2))
        settings = PanoramaSettings()
        self.assertEqual(settings.zoom, 0)
        self.assertEqual(settings.top_left, (0, 0))
        self.assertEqual(settings.bottom_right, (0, 0))
        self.assertEqual(settings.tiles, 1)
        self.assertRaises(ValueError, settings.update, 1, (1, 0), (2, 3))
        settings.update(5, (0, 0), get_max_coordinates(5))
        self.assertEqual(settings.tiles, 512)
    
    def test_validate_panaroma_id(self) -> None:
        self.assertRaises(TypeError, validate_panaroma_id, 123456)
        self.assertRaises(ValueError, validate_panaroma_id, "tooShort12345")
        validate_panaroma_id("*"*22)
    
    def test_get_images(self) -> None:
        self.assertRaises(rq.RequestException, get_images, "*"*22)
        images = get_images("xbK9YuuJe1GMpPPMqGFocA")
        images[0][0]
        images = get_images(
            "xbK9YuuJe1GMpPPMqGFocA",
            PanoramaSettings(zoom=5, top_left=(10, 10), bottom_right=(12, 13)))
        count = sum(map(len, images))
        self.assertEqual(count, 12)


if __name__ == "__main__":
    unittest.main()
