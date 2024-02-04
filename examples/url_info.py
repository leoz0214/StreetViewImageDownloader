"""Displays URL information, without actually downloading the URL."""
import argparse

from streetview_download.url import parse_url


parser = argparse.ArgumentParser(
    description="Displays Google Street View URL information.")
parser.add_argument("url", help="Google Street View URL")


def main() -> None:
    args = parser.parse_args()
    url = args.url
    url_info = parse_url(url)
    print(f"   Latitude: {url_info.latitude}")
    print(f"  Longitude: {url_info.longitude}")
    print(f"        Yaw: {url_info.yaw}")
    print(f"      Pitch: {url_info.pitch}")
    print(f"        FOV: {url_info.fov}")
    print(f"Panorama ID: {url_info.panorama_id}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
