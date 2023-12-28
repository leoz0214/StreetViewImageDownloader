"""Unit Tests the url.py module."""
import unittest

import __init__
from url import *


class Test_url(unittest.TestCase):

    def test_validate_dimensions(self) -> None:
        self.assertRaises(TypeError, validate_dimensions, "Invalid", 3)
        self.assertRaises(TypeError, validate_dimensions, 800.0, 60.0)
        self.assertRaises(ValueError, validate_dimensions, 25, 50)
        self.assertRaises(ValueError, validate_dimensions, 9000, 300)
        validate_dimensions(720, 440)
        validate_dimensions(2048, 2048)

    def test_parse_url(self) -> None:
        invalid_urls = (
            "https:/www.google.co.uk/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "ww.google.co.uk/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "https://www.goggle.c/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "www.google.co.uk/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "https://www.google.co.uk/maps/51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "https://www.google.co.uk/maps/@51.5173558,251,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "https://www.google.co.uk/maps/@51.5173558,-0.1232798,3a,75y,433.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "https://www.google.co.uk/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "http://www.google.co.uk/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "https://www.google.co.uk/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sNOTAPANID!2e0!7i16384!8i8192?entry=ttu&random_param"
        )
        for url in invalid_urls:
            with self.assertRaises(ValueError, msg=f"{url} is invalid."):
                parse_url(url)
        url_info = parse_url("https://www.google.co.uk/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu")
        self.assertEqual(url_info.latitude, 51.5173558)
        self.assertEqual(url_info.longitude, -0.1232798)
        self.assertEqual(url_info.zoom, 75)
        self.assertEqual(url_info.horizontal_pan, 247.27)
        self.assertEqual(url_info.vertical_pan, 70.52)
        self.assertEqual(url_info.panorama_id, "a67vofaBaZDzk62-g_5e8A")
        url_info = parse_url("google.cat/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu")
        self.assertEqual(url_info.longitude, -0.1232798)
        self.assertEqual(url_info.panorama_id, "a67vofaBaZDzk62-g_5e8A")
        url_info = parse_url("www.google.anything.at.all/maps/@5,4,3a,17y,0.05h,1t/data=!abc!def!ghi!1sabcdefghijklmnopqrstuv!2e0!7i16384!8i8192?&a=b&c=d    ")
        self.assertEqual(url_info.vertical_pan, 1)
        self.assertEqual(url_info.panorama_id, "abcdefghijklmnopqrstuv")

if __name__ == "__main__":
    unittest.main()
