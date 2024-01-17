"""Panorama ID downloading section of the GUI."""
import asyncio
import math
import threading
import time
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from typing import Union

from PIL import Image

import batch
import main
import save
from _utils import (
    inter, RED, GREEN, BLUE, GREY, BLACK, DARK_BLUE, draw_circle,
    BUTTON_COLOURS, bool_to_state)
from api.panorama import (
    PANORAMA_CHARACTERS, PANORAMA_ID_LENGTH, MIN_ZOOM, MAX_ZOOM,
    get_max_coordinates, PanoramaSettings, _combine_tiles,
    _get_async_images)


CANVAS_CIRCLE_RADIUS = 12
CANVAS_DIMENSIONS_BY_ZOOM = {
    1: (256, 128),
    2: (512, 256),
    3: (512, 256),
    4: (1024, 512),
    5: (1024, 512)
}
DOWNLOAD_PROGRESS_REFRESH_RATE = 0.05


class PanoramaDownload(tk.Frame):
    """Panorama ID downloading window."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(f"{main.TITLE} - Panorama Download")

        self.title = tk.Label(
            self, font=inter(25, True), text="Panorama Download")
        self.panorama_id_input = PanoramaIDInput(self)
        self.settings_input = PanoramaSettingsInput(self)
        self.back_button = tk.Button(
            self, font=inter(20), text="Back", width=15, command=self.back,
            **BUTTON_COLOURS)
        self.download_button = tk.Button(
            self, font=inter(20), text="Download", width=15,
            command=self.download, **BUTTON_COLOURS, state="disabled")
        
        self.title.grid(row=0, column=0, columnspan=2, padx=10, pady=5)
        self.panorama_id_input.grid(
            row=1, column=0, columnspan=2, padx=10, pady=3)
        self.settings_input.grid(
            row=2, column=0, columnspan=2, padx=10, pady=3)
        self.back_button.grid(row=3, column=0, padx=10, pady=3)
        self.download_button.grid(row=3, column=1, padx=10, pady=3)
    
    def back(self) -> None:
        """Returns to the main menu."""
        self.destroy()
        main.MainMenu(self.root).pack()
    
    def update_download_button_state(self) -> None:
        """Updates download button state based on valid input or not."""
        self.download_button.config(
            state=bool_to_state(self.panorama_id_input.valid))
    
    def download(self) -> None:
        """Downloads the required image (in a thread to avoid freezing)."""
        PanoramaDownloadToplevel(
            self, self.panorama_id_input.panorama_id,
            self.settings_input.settings)
    
    def save(self, panorama: Image.Image) -> None:
        """Proceeds to the image saving screen."""
        self.pack_forget()
        save.SaveImageFrame(self.root, self, panorama).pack()


class PanoramaIDInput(tk.Frame):
    """Frame for handling panorama ID input."""

    def __init__(
        self, master: Union[PanoramaDownload, "batch.PanoramaIDToplevel"]
    ) -> None:
        super().__init__(master)
        self.label = tk.Label(self, font=inter(20), text="Panorama ID:")
        self._panorama_id = tk.StringVar()
        self._previous = ""
        self.valid = False
        self._panorama_id.trace_add("write", lambda *_: self.validate())
        self.input = tk.Entry(
            self, font=inter(20), width=25, textvariable=self._panorama_id)
        self.feedback_label = tk.Label(
            self, font=inter(8), fg=RED,
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
        if (
            len(new) > PANORAMA_ID_LENGTH
            or any(char not in PANORAMA_CHARACTERS for char in new)
        ):
            self._panorama_id.set(self._previous)
        else:
            self._previous = new
            missing_characters = PANORAMA_ID_LENGTH - len(new)
            if missing_characters:
                self.valid = False
                self.feedback_label.config(
                    text=f"Missing characters: {missing_characters}", fg=RED)
            else:
                self.valid = True
                self.feedback_label.config(text="Valid panorama ID.", fg=GREEN)
        if isinstance(self.master, PanoramaDownload):
            self.master.update_download_button_state()
        else:
            self.master.update_submit_button_state()


class PanoramaSettingsInput(tk.Frame):
    """
    Allows the user to input panorama download settings: zoom and tile range.
    """

    def __init__(
        self,
        master: Union[PanoramaDownload, "batch.PanoramaIDSettingsToplevel"]
    ) -> None:
        super().__init__(master)
        self.zoom_label = tk.Label(self, font=inter(20), text="Zoom:")
        self.zoom_scale = tk.Scale(
            self, orient=tk.HORIZONTAL, font=inter(12), length=600,
            sliderlength=100, width=30, from_=MIN_ZOOM, to=MAX_ZOOM,
            command=lambda *_: self.update_zoom())
        self.range_inputs = [
            PanoramaRangeInput(self, zoom)
            for zoom in range(MIN_ZOOM, MAX_ZOOM + 1)]
        self.range_input = None
        self.update_zoom()
        
        self.zoom_label.grid(row=0, column=0, padx=10, sticky="ne")
        self.zoom_scale.grid(row=0, column=1, padx=10, sticky="w")
    
    @property
    def zoom(self) -> int:
        return self.zoom_scale.get()
    
    @property
    def settings(self) -> PanoramaSettings:
        if self.zoom == 0:
            return PanoramaSettings(self.zoom)
        return PanoramaSettings(
            self.zoom, self.range_input.top_left,
            self.range_input.bottom_right)
    
    def update_zoom(self) -> None:
        """Zoom update - update range input display."""
        if self.range_input is not None:
            self.range_input.grid_forget()
        self.range_input = self.range_inputs[self.zoom]
        self.range_input.grid(row=1, column=0, columnspan=2, pady=5)
    

class PanoramaRangeInput(tk.Frame):
    """
    Allows the user to download a portion of the panorama
    by dragging the area of the panorama to download.
    """

    def __init__(self, master: PanoramaSettingsInput, zoom: int) -> None:
        super().__init__(master, width=1200, height=600)
        self.pack_propagate(False)
        self.zoom = zoom
        self.max_x, self.max_y = get_max_coordinates(self.zoom)
        self.info_label = tk.Label(self, font=inter(12))
        if self.zoom == 0:
            # Only one tile - no point in additional settings.
            if isinstance(master.master, PanoramaDownload):
                text = "The entire panorama will be downloaded."
            else:
                text = "Entire panoramas will be downloaded."
            self.info_label.config(text=text, font=inter(25))
            self.info_label.place(relx=0.5, rely=0.5, anchor="center")
            return
        self.width, self.height = CANVAS_DIMENSIONS_BY_ZOOM[self.zoom]
        self.total_width = self.width + CANVAS_CIRCLE_RADIUS * 2
        self.total_height = self.height + CANVAS_CIRCLE_RADIUS * 2
        self.canvas = tk.Canvas(
            self, width=self.total_width, height=self.total_height)
        
        self.circle_coordinates = [
            (CANVAS_CIRCLE_RADIUS, CANVAS_CIRCLE_RADIUS),
            (self.total_width - CANVAS_CIRCLE_RADIUS,
                self.total_height - CANVAS_CIRCLE_RADIUS)]
        self.canvas.create_rectangle(
            *self.circle_coordinates[0], *self.circle_coordinates[1],
            fill=GREY)

        self.circles = []
        self.selected_circle = None
        self.previous_circle_coordinates = None
        self.lines = []
        self.selected_area = None

        self.top_left = (0, 0)
        self.bottom_right = (self.max_x, self.max_y)

        self.draw()

        self.canvas.bind("<Motion>", self.motion)
        self.canvas.bind("<Leave>", lambda *_: self.draw())
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", lambda *_: self.drop())

        self.update_info()
        
        self.canvas.pack(padx=5, pady=5)
        self.info_label.pack(padx=5, pady=5)
    
    def draw_grid_lines(self) -> None:
        """Draws the grid lines separating the tiles."""
        for line in self.lines:
            self.canvas.delete(line)
        self.lines.clear()
        for x in range(self.max_x + 1):
            canvas_x = self.width * x // self.max_x + CANVAS_CIRCLE_RADIUS
            line = self.canvas.create_line(
                canvas_x, CANVAS_CIRCLE_RADIUS,
                canvas_x, self.total_height - CANVAS_CIRCLE_RADIUS, fill=BLACK)
            self.lines.append(line)
        for y in range(self.max_y + 1):
            canvas_y = self.height * y // self.max_y + CANVAS_CIRCLE_RADIUS
            line = self.canvas.create_line(
                CANVAS_CIRCLE_RADIUS, canvas_y,
                self.total_width - CANVAS_CIRCLE_RADIUS, canvas_y, fill=BLACK)
            self.lines.append(line)
    
    def draw(self) -> None:
        """Draws circles, selected area and grid lines."""
        for circle in self.circles:
            self.canvas.delete(circle)
        self.circles.clear()
        self.draw_selected_area()
        self.draw_grid_lines()
        for coordinates in self.circle_coordinates:
            circle = draw_circle(
                self.canvas, *coordinates, CANVAS_CIRCLE_RADIUS, fill=BLUE)
            self.circles.append(circle)
    
    def draw_selected_area(self) -> None:
        """Draws green rectangle representing the selected area."""
        if self.selected_area is not None:
            self.canvas.delete(self.selected_area)
        top_left = (
            min(self.circle_coordinates[0][0], self.circle_coordinates[1][0]),
            min(self.circle_coordinates[0][1], self.circle_coordinates[1][1]))
        bottom_right = (
            max(self.circle_coordinates[0][0], self.circle_coordinates[1][0]),
            max(self.circle_coordinates[0][1], self.circle_coordinates[1][1]))   
        self.selected_area = self.canvas.create_rectangle(
            *top_left, *bottom_right, fill=GREEN)
        # Tile top left and bottom right
        self.top_left = (
            (top_left[0] - CANVAS_CIRCLE_RADIUS) * self.max_x // self.width,
            (top_left[1] - CANVAS_CIRCLE_RADIUS) * self.max_y // self.height)
        self.bottom_right = (
            (bottom_right[0] - CANVAS_CIRCLE_RADIUS)
                * self.max_x // self.width,
            (bottom_right[1] - CANVAS_CIRCLE_RADIUS)
                * self.max_y // self.height)
    
    def motion(self, event: tk.Event) -> None:
        """Mouse movement over canvas."""
        x, y = event.x, event.y
        self.draw()
        for i, coordinates in enumerate(self.circle_coordinates):
            if (
                math.hypot(x - coordinates[0], y - coordinates[1])
                < CANVAS_CIRCLE_RADIUS
            ):
                # Circle being hovered over currently.
                self.canvas.delete(self.circles[i])
                circle = draw_circle(
                    self.canvas, *coordinates,
                    CANVAS_CIRCLE_RADIUS, fill=DARK_BLUE)
                self.circles[i] = circle
                self.selected_circle = i
                break
    
    def drag(self, event: tk.Event) -> None:
        """Dragging a circle to adjust its position."""
        if self.selected_circle is None:
            return
        if self.previous_circle_coordinates is None:
            self.previous_circle_coordinates = self.circle_coordinates.copy()
        x, y = event.x, event.y
        x = min(
            max(x, CANVAS_CIRCLE_RADIUS),
            self.total_width - CANVAS_CIRCLE_RADIUS)
        y = min(
            max(y, CANVAS_CIRCLE_RADIUS),
            self.total_height - CANVAS_CIRCLE_RADIUS)
        self.circle_coordinates[self.selected_circle] = (x, y)
        self.draw()
        self.info_label.config(text="Dragging...")
    
    def drop(self) -> None:
        """No longer dragging a circle."""
        if self.selected_circle is None:
            return
        rounded_coordinates = []
        for coordinates in self.circle_coordinates:
            x, y = coordinates
            x = CANVAS_CIRCLE_RADIUS + self.width * round(
                (x - CANVAS_CIRCLE_RADIUS) / self.width * self.max_x
            ) // self.max_x
            y = CANVAS_CIRCLE_RADIUS + self.height * round(
                (y - CANVAS_CIRCLE_RADIUS) / self.height * self.max_y
            ) // self.max_y
            rounded_coordinates.append((x, y))
        if any(
            rounded_coordinates[0][i] == rounded_coordinates[1][i]
            for i in range(2)
        ):
            self.circle_coordinates = self.previous_circle_coordinates
        else:
            self.circle_coordinates = rounded_coordinates
        self.draw()
        
        self.selected_circle = None
        self.previous_circle_coordinates = None
        self.update_info()
    
    def set_corners(
        self, top_left: tuple[int, int], bottom_right: tuple[int, int]
    ) -> None:
        """Programmatically sets the top left/bottom right coordinates."""
        self.top_left = top_left
        self.bottom_right = bottom_right
        self.circle_coordinates = [
            (
                CANVAS_CIRCLE_RADIUS + x * self.width // self.max_x,
                CANVAS_CIRCLE_RADIUS + y * self.height // self.max_y)
            for x, y in (self.top_left, self.bottom_right)]
        self.draw()
        self.update_info()
    
    def update_info(self) -> None:
        """Updates information on selection."""
        width = self.bottom_right[0] - self.top_left[0]
        height = self.bottom_right[1] - self.top_left[1]
        text = " | ".join((
            f"Top left: {self.top_left}", f"Bottom right: {self.bottom_right}",
            f"Width: {width}", f"Height: {height}", f"Tiles: {width * height}"
        ))
        self.info_label.config(text=text)


class PanoramaDownloadToplevel(tk.Toplevel):
    """
    Toplevel window where the panorama downloading occurs
    and progress is displayed.
    """

    def __init__(
        self, master: PanoramaDownload, panorama_id: str,
        settings: PanoramaSettings
    ) -> None:
        super().__init__(master)
        self.title(f"{main.TITLE} - Downloading Panorama...")
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.panorama_id = panorama_id
        self.settings = settings
        self.cancelled = False
        self.tiles = [
            [None] * self.settings.width
            for _ in range(self.settings.height)]
        self.panorama = None
        self.exception = None
        self.async_loop = None
        
        self.title_label = tk.Label(
            self, font=inter(25, True), text="Downloading Panorama...")
        self.progress_bar = ttk.Progressbar(
            self, length=500, maximum=self.settings.tiles)
        self.progress_label = tk.Label(self, font=inter(12))
        self.cancel_button = tk.Button(
            self, font=inter(15), text="Cancel",width=15,
            bg=RED, activebackground=RED, command=self.cancel)
        
        self.update_progress()
        threading.Thread(target=self.download, daemon=True).start()
    
        self.title_label.pack(padx=25, pady=25)
        self.progress_bar.pack(padx=25, pady=25)
        self.progress_label.pack(padx=25, pady=25)
        self.cancel_button.pack(padx=25, pady=25)
    
    @property
    def tiles_downloaded(self) -> int:
        return self.settings.tiles - sum(row.count(None) for row in self.tiles)
    
    def update_progress(self) -> None:
        """Updates the progress bar and progress label."""
        self.progress_bar.config(value=self.tiles_downloaded)
        percentage = round(
            self.tiles_downloaded / self.settings.tiles * 100, 1)
        if percentage == 100:
            text = "Merging Tiles..."
        else:
            text = " | ".join((
                f"Tiles downloaded: {self.tiles_downloaded} / "
                    f"{self.settings.tiles}",
                f"Progress: {percentage}%"))
        self.progress_label.config(text=text)
    
    def _process_download(self) -> None:
        try:
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(_get_async_images(
                self.tiles, self.panorama_id, self.settings, self))
            self.panorama = _combine_tiles(self.tiles, True, self)
            if self.cancelled:
                raise RuntimeError
            if self.panorama.size == (0, 0):
                raise RuntimeError("No panorama data.")
        except Exception as e:
            self.exception = e    
    
    def download(self) -> None:
        """Method to download the image tiles as required."""
        try:
            threading.Thread(
                target=self._process_download, daemon=True).start()
            while self.panorama is None:
                if self.exception is not None:
                    raise self.exception
                self.update_progress()
                time.sleep(DOWNLOAD_PROGRESS_REFRESH_RATE)
            if self.exception is not None:
                raise self.exception
        except Exception as e:
            if self.cancelled:
                return
            messagebox.showerror(
                "Error", f"Unfortunately, an error has occurred: {e}",
                parent=self)
            self.destroy()
        else:
            self.save()
    
    def cancel(self) -> None:
        """Cancels the panorama download."""
        self.cancelled = True
        self.destroy()
    
    def save(self) -> None:
        """Proceeds to the save GUI."""
        self.destroy()
        self.master.save(self.panorama)
        