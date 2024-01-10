"""Panorama ID downloading section of the GUI."""
import tkinter as tk

import main
from _utils import inter, RED, GREEN, BLUE, GREY, BLACK,  draw_circle
from api.panorama import (
    PANORAMA_CHARACTERS, PANORAMA_ID_LENGTH, MIN_ZOOM, MAX_ZOOM,
    get_max_coordinates)


CANVAS_CIRCLE_RADIUS = 12
CANVAS_WIDTH = 1024
CANVAS_HEIGHT = 512
TOTAL_CANVAS_WIDTH = CANVAS_WIDTH + CANVAS_CIRCLE_RADIUS * 2
TOTAL_CANVAS_HEIGHT = CANVAS_HEIGHT + CANVAS_CIRCLE_RADIUS * 2


class PanoramaDownload(tk.Frame):
    """Panorama ID downloading window."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(f"{main.TITLE} - Panorama Download")

        self.title = tk.Label(
            self, font=inter(40, True), text="Panorama Download")
        self.panorama_id_input = PanoramaIDInput(self)
        self.settings_input = PanoramaSettingsInput(self)
        
        self.title.pack(padx=10, pady=10)
        self.panorama_id_input.pack(padx=10, pady=5)
        self.settings_input.pack(padx=10, pady=5)


class PanoramaIDInput(tk.Frame):
    """Frame for handling panorama ID input."""

    def __init__(self, master: PanoramaDownload) -> None:
        super().__init__(master)
        self.label = tk.Label(self, font=inter(25), text="Panorama ID:")
        self._panorama_id = tk.StringVar()
        self._previous = ""
        self.valid = False
        self._panorama_id.trace_add("write", lambda *_: self.validate())
        self.input = tk.Entry(
            self, font=inter(25), width=25, textvariable=self._panorama_id)
        self.feedback_label = tk.Label(
            self, font=inter(11), fg=RED,
            text=f"Missing characters: {PANORAMA_ID_LENGTH}")

        self.label.grid(row=0, column=0, rowspan=2, padx=5, sticky="n")
        self.input.grid(row=0, column=1, pady=3, padx=5)
        self.feedback_label.grid(row=1, column=1, pady=3, sticky="e")
    
    @property
    def panorama_id(self) -> str:
        return self._panorama_id.get()
    
    def validate(self) -> None:
        """Validates the updated panorama ID."""
        new = self._panorama_id.get()
        self.valid = False
        if (
            len(new) > PANORAMA_ID_LENGTH
            or any(char not in PANORAMA_CHARACTERS for char in new)
        ):
            self._panorama_id.set(self._previous)
        else:
            self._previous = new
            missing_characters = PANORAMA_ID_LENGTH - len(new)
            if missing_characters:
                self.feedback_label.config(
                    text=f"Missing characters: {missing_characters}", fg=RED)
            else:
                self.valid = True
                self.feedback_label.config(text="Valid panorama ID", fg=GREEN)


class PanoramaSettingsInput(tk.Frame):
    """
    Allows the user to input panorama download settings: zoom and tile range.
    """

    def __init__(self, master: PanoramaDownload) -> None:
        super().__init__(master)
        self.zoom_label = tk.Label(self, font=inter(20), text="Zoom:")
        self.zoom_scale = tk.Scale(
            self, orient=tk.HORIZONTAL, font=inter(20), length=600,
            sliderlength=100, width=40, from_=MIN_ZOOM, to=MAX_ZOOM)
        self.range_input = PanoramaRangeInput(self, self.zoom)
        
        self.zoom_label.grid(row=0, column=0, padx=5, sticky="n")
        self.zoom_scale.grid(row=0, column=1, padx=5)
        self.range_input.grid(row=1, column=0, columnspan=2, pady=5)
    
    @property
    def zoom(self) -> int:
        return self.zoom_scale.get()
    

class PanoramaRangeInput(tk.Frame):
    """
    Allows the user to download a portion of the panorama
    by dragging the area of the panorama to download.
    """

    def __init__(self, master: PanoramaSettingsInput, zoom: int) -> None:
        super().__init__(master)
        self.zoom = zoom
        self.max_x, self.max_y = get_max_coordinates(self.zoom)
        self.canvas = tk.Canvas(
            self, width=TOTAL_CANVAS_WIDTH, height=TOTAL_CANVAS_HEIGHT)
        self.circle_coordinates = (
            [CANVAS_CIRCLE_RADIUS, CANVAS_CIRCLE_RADIUS],
            [TOTAL_CANVAS_WIDTH - CANVAS_CIRCLE_RADIUS,
                TOTAL_CANVAS_HEIGHT - CANVAS_CIRCLE_RADIUS]
        )
        self.canvas.create_rectangle(
            *self.circle_coordinates[0], *self.circle_coordinates[1],
            fill=GREY)
        
        # Draw grid lines.
        for x in range(self.max_x + 1):
            canvas_x = CANVAS_WIDTH * x // self.max_x + CANVAS_CIRCLE_RADIUS
            self.canvas.create_line(
                canvas_x, CANVAS_CIRCLE_RADIUS,
                canvas_x, TOTAL_CANVAS_HEIGHT - CANVAS_CIRCLE_RADIUS,
                fill=BLACK)
        for y in range(self.max_y + 1):
            canvas_y = CANVAS_HEIGHT * y // self.max_y + CANVAS_CIRCLE_RADIUS
            self.canvas.create_line(
                CANVAS_CIRCLE_RADIUS, canvas_y,
                TOTAL_CANVAS_WIDTH - CANVAS_CIRCLE_RADIUS, canvas_y,
                fill=BLACK)

        for coordinates in self.circle_coordinates:
            draw_circle(
                self.canvas, *coordinates, CANVAS_CIRCLE_RADIUS, fill=BLUE)
            
        self.canvas.pack()
