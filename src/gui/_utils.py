"""Utilities for the GUI."""
import ctypes
import pathlib
import tkinter as tk
from tkinter.font import Font

import pyglet


BIN_FOLDER = pathlib.Path(__file__).parent / "bin"
CPP_FOLDER = pathlib.Path(__file__).parent / "cpp"
CPP_FOREGROUND_PID_LIBRARY = CPP_FOLDER / "foreground.so"
CPP_CONVERSION_LIBRARY = CPP_FOLDER / "conversion.so"

# Load Inter font downloaded online.
pyglet.font.add_file(str(BIN_FOLDER / "Inter.ttf"))


RED = "#ff0000"
GREEN = "green"
BLUE = "#0096ff"
DARK_BLUE = "#0000ff"
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
) -> int:
    """Utility to draw circle on canvas."""
    return canvas.create_oval(
        x - radius, y - radius, x + radius, y + radius, fill=fill)


def bool_to_state(expression: bool) -> str:
    """Returns 'normal' if True, else 'disabled'"""
    return "normal" if expression else "disabled"


def get_text_width(text: str, font: tuple) -> int:
    """Returns the text width for a given font in pixels."""
    font = Font(family=font[0], size=font[1])
    return font.measure(text)


def format_seconds(seconds: float) -> str:
    """Converts seconds to HH:MM:SS"""
    seconds = int(seconds)
    hours = str(seconds // 3600).zfill(2)
    minutes = str(seconds % 3600 // 60).zfill(2)
    seconds = str(seconds % 60).zfill(2)
    return f"{hours}:{minutes}:{seconds}"


def int_if_possible(float_: float) -> int | float:
    """Converts a float to an integer if it is indeed an integer."""
    return int(float_) if float_ % 1 == 0 else float_


def load_cpp_foreground_pid_library() -> ctypes.CDLL:
    """Returns the library for retrieving the foreground process PID."""
    return ctypes.CDLL(str(CPP_FOREGROUND_PID_LIBRARY))


def load_cpp_conversion_library() -> ctypes.CDLL:
    """Loads C++ image conversion library"""
    return ctypes.CDLL(str(CPP_CONVERSION_LIBRARY))
