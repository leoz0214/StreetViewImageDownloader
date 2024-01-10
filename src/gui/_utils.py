"""Utilities for the GUI."""
import pathlib
import tkinter as tk

import pyglet


BIN_FOLDER = pathlib.Path(__file__).parent / "bin"
# Load Inter font downloaded online.
pyglet.font.add_file(str(BIN_FOLDER / "Inter.ttf"))


RED = "#ff0000"
GREEN = "green"
BLUE = "#0096ff"
GREY = "#cccccc"
BLACK = "#000000"
BUTTON_COLOURS = dict.fromkeys(("bg", "activebackground"), GREY)


def inter(size: int, bold: bool = False, italic: bool = False) -> tuple:
    """Utility function for the Inter font."""
    font = ("Inter", size)
    if bold:
        font += ("bold",)
    if italic:
        font += ("italic",)
    return font


def draw_circle(
    canvas: tk.Canvas, x: int, y: int, radius: int, fill: str
) -> None:
    """Utility to draw circle on canvas"""
    canvas.create_oval(
        x - radius, y - radius, x + radius, y + radius, fill=fill)
