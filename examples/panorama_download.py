"""
This script downloads a panorama by ID, with optional
arguments of zoom and file save path.
"""
import argparse

from streetview_download.panorama import get_pil_panorama, PanoramaSettings


parser = argparse.ArgumentParser(description="Downloads a panorama by ID.")
parser.add_argument("panorama_id", help="Panorama ID (22 characters).")
parser.add_argument("-z", "--zoom", type=int, help="Level of zoom [0, 5]")
parser.add_argument("-o", "--output", help="Output file path.")


def main() -> None:
    args = parser.parse_args()
    # Gather arguments.
    panorama_id = args.panorama_id
    zoom = args.zoom if args.zoom is not None else 0
    output_file = args.output
    # Downloads panorama.  
    pil_panorama = get_pil_panorama(panorama_id, PanoramaSettings(zoom))
    if output_file is not None:
        # Save to given output file.
        pil_panorama.save(output_file, format="jpeg")
        print(f"Successfully saved panorama.")
    else:
        # Display the image instead, if no file is provided.
        pil_panorama.show()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
