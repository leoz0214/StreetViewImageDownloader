"""Utilities for the GUI."""
import pathlib

import pyglet


BIN_FOLDER = pathlib.Path(__file__).parent / "bin"
# Load Inter font downloaded online.
pyglet.font.add_file(str(BIN_FOLDER / "Inter.ttf"))


GREY = "#cccccc"
BUTTON_COLOURS = dict.fromkeys(("bg", "activebackground"), GREY)


def inter(size: int, bold: bool = False, italic: bool = False) -> tuple:
    """Utility function for the Inter font."""
    font = ("Inter", size)
    if bold:
        font += ("bold",)
    if italic:
        font += ("italic",)
    return font
