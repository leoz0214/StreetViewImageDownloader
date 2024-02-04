"""
This script takes a Street View URL and downloads the URL view,
with a given width and height, saving or displaying the output image.
"""
import argparse

from streetview_download.url import (
    get_pil_image, DEFAULT_WIDTH, DEFAULT_HEIGHT)


parser = argparse.ArgumentParser(
    description="Downloads a Google Street View URL view.")
parser.add_argument("url", help="Google Street View URL.")
parser.add_argument("-W", "--width", type=int, help="Width of output image.")
parser.add_argument("-H", "--height", type=int, help="Height of output image.")
parser.add_argument("-o", "--output", help="Output file save path.")


def main() -> None:
    args = parser.parse_args()
    # Process arguments.
    url = args.url
    width = args.width if args.width is not None else DEFAULT_WIDTH
    height = args.height if args.height is not None else DEFAULT_HEIGHT
    output_file = args.output

    # Downloads URL view image.
    image = get_pil_image(url, width, height)
    if output_file is not None:
        # Saves image if output file is provided.
        image.save(output_file, format="jpeg")
        print("Successfully saved URL view.")
    else:
        # Displays image otherwise.
        image.show()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
    