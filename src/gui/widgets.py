"""Widgets used multiple times throughout the app."""
import tkinter as tk

import panorama_id
import url
from _utils import inter, BUTTON_COLOURS
from api.url import MIN_WIDTH, MAX_WIDTH, MIN_HEIGHT, MAX_HEIGHT


class UrlSettingsToplevel(tk.Toplevel):
    """Allows the user to set the URL download settings (width and height)."""

    def __init__(self, master: tk.Frame, root: tk.Tk) -> None:
        super().__init__(master)
        self.grab_set()
        self.title(f"{root.title()} - URL Download Settings")

        self.title_label = tk.Label(
            self, font=inter(25, True), text="URL Download Settings")
        self.width_input = url.DimensionInput(
            self, "Width:", MIN_WIDTH, MAX_WIDTH, master.width)
        self.height_input = url.DimensionInput(
            self, "Height:", MIN_HEIGHT, MAX_HEIGHT, master.height)
        self.save_button = tk.Button(
            self, font=inter(20), text="Save", width=15,
            **BUTTON_COLOURS, command=self.save)
        
        self.title_label.pack(padx=10, pady=10)
        self.width_input.pack(padx=10, pady=10)
        self.height_input.pack(padx=10, pady=10)
        self.save_button.pack(padx=10, pady=10)
    
    def save(self) -> None:
        """Saves the URL settings."""
        width = self.width_input.value
        height = self.height_input.value
        self.master.width = width
        self.master.height = height
        self.master.update_info_label()
        self.destroy()


class PanoramaIDSettingsToplevel(tk.Toplevel):
    """Toplevel for editing batch panorama ID download settings."""

    def __init__(
        self, master: tk.Frame, root: tk.Tk, settings_name: str = "settings"
    ) -> None:
        super().__init__(master)
        self.title(f"{root.title()} - Panorama Download Settings")
        self.grab_set()
        self.settings_name = settings_name
        settings = getattr(master, self.settings_name)

        self.title_label = tk.Label(
            self, font=inter(25, True), text="Panorama Download Settings")
        self.settings_frame = panorama_id.PanoramaSettingsInput(self)
        self.settings_frame.zoom_scale.set(settings.zoom)
        if settings.zoom != 0:
            range_input = self.settings_frame.range_inputs[settings.zoom]
            range_input.set_corners(settings.top_left, settings.bottom_right)

        self.save_button = tk.Button(
            self, font=inter(20), text="Save", width=15,
            **BUTTON_COLOURS, command=self.save)

        self.title_label.pack(padx=10, pady=10)
        self.settings_frame.pack(padx=10, pady=10)
        self.save_button.pack(padx=10, pady=10)
    
    def save(self) -> None:
        """Saves the current panorama ID download settings."""
        settings = self.settings_frame.settings
        setattr(self.master, self.settings_name, settings)
        self.master.update_info_label()
        self.destroy()