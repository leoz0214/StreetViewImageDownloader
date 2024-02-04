"""
Downloads panoramas in bulk.
Takes a text file with valid panorama IDs, and a save folder.
"""
import argparse
import pathlib

from streetview_download.panorama import get_panorama, PanoramaSettings


parser = argparse.ArgumentParser(description="Downloads panoramas in bulk.")
parser.add_argument(
    "file", help="Input file containing panorama IDs separated by newlines.")
parser.add_argument("-z", "--zoom", type=int, help="Level of zoom [0, 5]")
parser.add_argument("-o", "--output", help="Output folder.")


def get_panorama_ids(input_file: str) -> list[str]:
    """Returns panorama IDs in the input file, except blank lines."""
    with open(input_file, "r", encoding="utf8") as f:
        panorama_ids = [line.strip() for line in f if line.strip()]
    return panorama_ids


def main() -> None:
    args = parser.parse_args()
    # Parse arguments.
    input_file = args.file
    zoom = args.zoom if args.zoom is not None else 0
    # Use current working directory as output folder by default.
    output_folder = (
        pathlib.Path(args.output) if args.output is not None
        else pathlib.Path().cwd())
    # Create output folder if non-existent.
    output_folder.mkdir(parents=True, exist_ok=True)

    panorama_ids = get_panorama_ids(input_file)
    settings = PanoramaSettings(zoom)
    # Download and save each panorama to the output folder.
    # The file names are by panorama ID to keep it simple.
    for i, panorama_id in enumerate(panorama_ids, 1):
        print(f"{i}/{len(panorama_ids)}: {panorama_id}")
        panorama = get_panorama(panorama_id, settings)
        (output_folder / f"{panorama_id}.jpg").write_bytes(panorama)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
