"""Runs the Street View Image Download app."""
import pathlib
import sys


if hasattr(sys, "_MEIPASS"):
    FOLDER = pathlib.Path(sys._MEIPASS) / "src"
else:
    FOLDER = pathlib.Path(__file__).parent / "src"
    
sys.path.append(str(FOLDER))
sys.path.append(str(FOLDER / "gui"))

from gui.main import main


if __name__ == "__main__":
    main()