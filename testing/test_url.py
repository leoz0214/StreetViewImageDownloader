"""Unit Tests the url.py module."""
import unittest

from __init__ import TEST_OUTPUT_FOLDER
from url import *


class Test_url(unittest.TestCase):

    def test_validate_dimensions(self) -> None:
        self.assertRaises(TypeError, validate_dimensions, "Invalid", 3)
        self.assertRaises(TypeError, validate_dimensions, 800.0, 60.0)
        self.assertRaises(ValueError, validate_dimensions, 25, 50)
        self.assertRaises(ValueError, validate_dimensions, 9000, 300)
        validate_dimensions(720, 440)
        validate_dimensions(2048, 2048)
        validate_dimensions(DEFAULT_WIDTH, DEFAULT_HEIGHT)

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
            "https://www.google.co.uk/maps/@51.5173558,-0.1232798,3a,75y,247.27t,70.52h/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "https:/www.google.co.uk/maps//@51.5173558,-0.1232798,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
            "https:/www.google.co.uk/maps//@51.5173558,-0.1232798,3a,75y,247.27h,70.52t,2a/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu",
        )
        for url in invalid_urls:
            with self.assertRaises(ValueError, msg=f"{url} is invalid."):
                parse_url(url)
        url_info = parse_url("https://www.google.co.uk/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu")
        self.assertEqual(url_info.latitude, 51.5173558)
        self.assertEqual(url_info.longitude, -0.1232798)
        self.assertEqual(url_info.fov, 75)
        self.assertEqual(url_info.yaw, 247.27)
        self.assertEqual(url_info.pitch, 70.52)
        self.assertEqual(url_info.panorama_id, "a67vofaBaZDzk62-g_5e8A")
        url_info = parse_url("google.cat/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu")
        self.assertEqual(url_info.longitude, -0.1232798)
        self.assertEqual(url_info.panorama_id, "a67vofaBaZDzk62-g_5e8A")
        url_info = parse_url("www.google.anything.at.all/maps/@5,4,3a,17y,0.05h,1t/data=!abc!def!ghi!1sabcdefghijklmnopqrstuv!2e0!7i16384!8i8192?&a=b&c=d    ")
        self.assertEqual(url_info.pitch, 1)
        self.assertEqual(url_info.panorama_id, "abcdefghijklmnopqrstuv")
        url_info = parse_url("http://www.google.co.fr/maps/@50,60,22.22y,16t,3a/data=!abc!def!ghi!1sabcdefghijklmnopqrstuv!2e0!7i163ENDDOESNOTMATTER")
        self.assertEqual(url_info.yaw, DEFAULT_YAW)
        self.assertEqual(url_info.fov, 22.22)
        self.assertEqual(url_info.pitch, 16)

    def test_get_pil_image(self) -> None:
        # Click into the URLs to confirm correctness.
        # London Eye
        url = "https://www.google.com/maps/@51.5008569,-0.1229866,3a,29.5y,40.13h,99.51t/data=!3m6!1e1!3m4!1svon5hH0A2iUfHzE3RjzMvg!2e0!7i16384!8i8192?entry=ttu"
        image = get_pil_image(url)
        self.assertEqual(image.size, (DEFAULT_WIDTH, DEFAULT_HEIGHT))
        image.save(TEST_OUTPUT_FOLDER / "london_eye.jpg")
        # View from Eiffel Tower
        url = "https://www.google.com/maps/@48.85813,2.2943272,2a,85.6y,229.81h,78.64t/data=!3m7!1e1!3m5!1sN-aSgjCBfROu7gpsMBWELg!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fpanoid%3DN-aSgjCBfROu7gpsMBWELg%26cb_client%3Dmaps_sv.tactile.gps%26w%3D203%26h%3D100%26yaw%3D57.1227%26pitch%3D0%26thumbfov%3D100!7i13312!8i6656?entry=ttu"
        image = get_pil_image(url, 1280, 720)
        self.assertEqual(image.size, (1280, 720))
        image.save(TEST_OUTPUT_FOLDER / "eiffel_tower_view.jpg")
        # Inside San Marino
        url = "https://www.google.com/maps/@43.9370454,12.4463079,3a,51.2y,231.08h,84.72t/data=!3m7!1e1!3m5!1sk6ywfPaKqXmqyk-u4PddbA!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fpanoid%3Dk6ywfPaKqXmqyk-u4PddbA%26cb_client%3Dmaps_sv.tactile.gps%26w%3D203%26h%3D100%26yaw%3D45.320965%26pitch%3D0%26thumbfov%3D100!7i13312!8i6656?entry=ttu"
        image = get_pil_image(url, width=2048)
        self.assertEqual(image.size, (2048, DEFAULT_HEIGHT))
        image.save(TEST_OUTPUT_FOLDER / "san_marino.jpg")
        # Mystical Russian lake
        url = "https://www.google.com/maps/@55.9553772,160.289749,2a,90y,253.82h,77.36t/data=!3m7!1e1!3m5!1sravxfvPPtlwg5q3iB2VngA!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fpanoid%3DravxfvPPtlwg5q3iB2VngA%26cb_client%3Dmaps_sv.tactile.gps%26w%3D203%26h%3D100%26yaw%3D60%26pitch%3D0%26thumbfov%3D100!7i13312!8i6656?entry=ttu"
        image = get_pil_image(url, height=500)
        self.assertEqual(image.size, (DEFAULT_WIDTH, 500))
        image.save(TEST_OUTPUT_FOLDER / "mystical_lake.jpg")
        # Taj Mahal
        url = "https://www.google.com/maps/@27.1744385,78.0421149,2a,90y,357.56h,111.18t/data=!3m6!1e1!3m4!1sKwyIz9J45WfVlkmr93oURg!2e0!7i13312!8i6656?entry=ttu"
        image = get_pil_image(url)
        image.save(TEST_OUTPUT_FOLDER / "taj_mahal.jpg")
        # Flying Fish Cove, Christmas Island
        url = "https://www.google.com/maps/@-10.4303034,105.6619123,3a,90y,239.35h,79.66t/data=!3m7!1e1!3m5!1sr4qCiWtfE_0dDUyepLuvfA!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fpanoid%3Dr4qCiWtfE_0dDUyepLuvfA%26cb_client%3Dmaps_sv.tactile.gps%26w%3D203%26h%3D100%26yaw%3D359.88742%26pitch%3D0%26thumbfov%3D100!7i13312!8i6656?entry=ttu"
        image = get_pil_image(url, 512, 512)
        image.save(TEST_OUTPUT_FOLDER / "flying_fish_cove.jpg")
        # Madagascar Boat
        url = "https://www.google.com/maps/@-13.5455058,48.3700052,2a,90y,349.88h,67.23t/data=!3m7!1e1!3m5!1sFAPW0QxlsJGzJb2yW5HtmQ!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fpanoid%3DFAPW0QxlsJGzJb2yW5HtmQ%26cb_client%3Dmaps_sv.tactile.gps%26w%3D203%26h%3D100%26yaw%3D179.88747%26pitch%3D-0.11254019%26thumbfov%3D100!7i13312!8i6656?entry=ttu"
        image = get_pil_image(url, 555, 555)
        image.save(TEST_OUTPUT_FOLDER / "madagascar_boat.jpg")
        # Grey Glacier, Chile
        url = "https://www.google.com/maps/@-50.9771654,-73.2232035,3a,90y,335.43h,75.44t/data=!3m7!1e1!3m5!1siOcRvC3KjIGrDZAa_36jfg!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fpanoid%3DiOcRvC3KjIGrDZAa_36jfg%26cb_client%3Dmaps_sv.tactile.gps%26w%3D203%26h%3D100%26yaw%3D-46.85633%26pitch%3D-0.027162854%26thumbfov%3D100!7i13312!8i6656?entry=ttu"
        image = get_pil_image(url, 2048, 2048)
        image.save(TEST_OUTPUT_FOLDER / "grey_glacier.jpg")
        # Statue of Liberty
        url = "https://www.google.com/maps/@40.6889302,-74.0438807,2a,57.3y,299.59h,122.95t/data=!3m7!1e1!3m5!1smVwoDjIdr9go4LjYriwkUw!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fpanoid%3DmVwoDjIdr9go4LjYriwkUw%26cb_client%3Dmaps_sv.tactile.gps%26w%3D203%26h%3D100%26yaw%3D112.62543%26pitch%3D0%26thumbfov%3D100!7i13312!8i6656?entry=ttu"
        image = get_pil_image(url)
        image.save(TEST_OUTPUT_FOLDER / "statue_of_liberty.jpg")
        # Nuuk, Greenland
        url = "https://www.google.com/maps/@64.1795079,-51.7433088,3a,55.2y,81.45h,91.53t/data=!3m7!1e1!3m5!1sB_kRxxyh_ys9bEfftZOxtQ!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fpanoid%3DB_kRxxyh_ys9bEfftZOxtQ%26cb_client%3Dmaps_sv.tactile.gps%26w%3D203%26h%3D100%26yaw%3D52.836292%26pitch%3D0%26thumbfov%3D100!7i13312!8i6656?entry=ttu"
        get_pil_image(url).save(TEST_OUTPUT_FOLDER / "greenland.jpg")

    def test_get_image(self) -> None:
       self.assertIsInstance(
           get_image("https://www.google.co.uk/maps/@51.5173558,-0.1232798,3a,75y,247.27h,70.52t/data=!3m6!1e1!3m4!1sa67vofaBaZDzk62-g_5e8A!2e0!7i16384!8i8192?entry=ttu"),
           bytes)
    

if __name__ == "__main__":
    unittest.main()
