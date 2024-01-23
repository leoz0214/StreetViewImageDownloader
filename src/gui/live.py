"""Live image downloading using a tracked selenium window."""
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

import main
import widgets
from _utils import inter, BUTTON_COLOURS, GREEN
from api.panorama import PanoramaSettings
from api.url import DEFAULT_WIDTH, DEFAULT_HEIGHT


@dataclass
class ImageMode:
    """Download either panoramas or URL images."""
    panorama = "Panorama"
    url = "URL"


class LiveDownloading(tk.Frame):
    """Live downloading window."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(f"{main.TITLE} - Live Downloading")

        self.title = tk.Label(
            self, font=inter(25, True), text="Live Downloading")

        self.notebook = ttk.Notebook(self)
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=inter(15))
        self.settings_frame = LiveSettingsFrame(self.notebook)
        self.info_frame = LiveInfoFrame(self.notebook)
        self.settings_frame.pack()
        self.info_frame.pack()
        self.notebook.add(self.settings_frame, text="Settings")
        self.notebook.add(self.info_frame, text="Output")

        self.back_button = tk.Button(
            self, font=inter(20), text="Back", width=15,
            **BUTTON_COLOURS, command=self.back)
        self.start_button = tk.Button(
            self, font=inter(20), text="Start", width=15,
            **BUTTON_COLOURS, command=self.start)
        
        self.title.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        self.notebook.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        self.back_button.grid(row=2, column=0, padx=5, pady=5)
        self.start_button.grid(row=2, column=1, padx=5, pady=5)
    
    def back(self) -> None:
        """Returns to the home screen."""
        self.destroy()
        main.MainMenu(self.root).pack()
    
    def start(self) -> None:
        """Opens the selenium window and starts the tracking."""
        # TODO


class LiveSettingsFrame(tk.Frame):
    """Handles the various live downloading options."""

    def __init__(self, master: ttk.Notebook) -> None:
        super().__init__(master)
        self.image_mode_frame = LiveImageMode(self)

        self.image_mode_frame.pack()


class LiveImageMode(tk.Frame):
    """Allows the user to download panoramas or URL images."""

    def __init__(self, master: LiveSettingsFrame) -> None:
        super().__init__(master)
        self.panorama_settings = PanoramaSettings()
        self.width = DEFAULT_WIDTH
        self.height = DEFAULT_HEIGHT
        self._mode = tk.IntVar(value=1)
        self._mode.trace_add("write", lambda *_: self.update_info_label())
        self.label = tk.Label(self, font=inter(20), text="Image Mode:")
        self.label.grid(row=0, column=0, padx=5, pady=5)
        for value, text in enumerate(("Panorama", "URL")):
            radiobutton = tk.Radiobutton(
                self, font=inter(20), text=text, width=15, value=value,
                variable=self._mode, **BUTTON_COLOURS, indicatoron=False,
                selectcolor=GREEN)
            radiobutton.grid(row=0, column=value + 1, padx=5, pady=5)
        
        self.info_label = tk.Label(self, font=inter(12), width=50)
        self.edit_button = tk.Button(
            self, font=inter(12), text="Edit", width=15, **BUTTON_COLOURS,
            command=self.edit)
        self.info_label.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        self.edit_button.grid(row=1, column=2, padx=5, pady=5)

        self.update_info_label()
    
    @property
    def image_mode(self) -> ImageMode:
        return ImageMode.panorama if self._mode.get() == 0 else ImageMode.url
    
    def update_info_label(self) -> None:
        """Updates the information text."""
        font_size = 12
        width = 50
        if self.image_mode == ImageMode.panorama:
            if self.panorama_settings.zoom == 0:
                text = "Zoom: 0 | Entire panoramas will be downloaded"
            else:
                text = " | ".join((
                    f"Zoom: {self.panorama_settings.zoom}",
                    f"Top left: {self.panorama_settings.top_left}",
                    f"Bottom right: {self.panorama_settings.bottom_right}",
                    f"Width: {self.panorama_settings.width}",
                    f"Height: {self.panorama_settings.height}",
                    f"Tiles: {self.panorama_settings.tiles}"))
                font_size = 9
                width = 75
        else:
            text = f"Dimensions: {self.width} x {self.height}"
        self.info_label.config(text=text, font=inter(font_size), width=width)
    
    def edit(self) -> None:
        """Opens the appropriate settings toplevel for editing."""
        if self.image_mode == ImageMode.panorama:
            widgets.PanoramaIDSettingsToplevel(
                self, self.master.master.master.root, "panorama_settings")
            return
        widgets.UrlSettingsToplevel(self, self.master.master.master.root)


class LiveInfoFrame(tk.Frame):
    """Handles live information display, and logging."""

    def __init__(self, master: ttk.Notebook) -> None:
        super().__init__(master)
