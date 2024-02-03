"""Builds the Sphinx documentation for the API."""
import pathlib
import shutil
import subprocess


FOLDER = pathlib.Path(__file__).parent
BUILD_FOLDER = FOLDER / "_build"

TEMP_FOLDER = FOLDER / "_temp"
if TEMP_FOLDER.is_dir():
    shutil.rmtree(TEMP_FOLDER)
TEMP_FOLDER.mkdir()

# Copy all modules into a temporary folder except the __init__.py
# file, e.g. since api.panorama.x is not wanted (panorama.x is wanted instead).
API_FOLDER = FOLDER.parent / "src" / "api"
for path in API_FOLDER.iterdir():
    if path.suffix == ".py" and path.stem != "__init__":
        shutil.copy(path, TEMP_FOLDER / path.name)


if __name__ == "__main__":
    subprocess.run(("sphinx-build", "-b", "html", str(FOLDER), str(BUILD_FOLDER)))
    shutil.rmtree(TEMP_FOLDER)
