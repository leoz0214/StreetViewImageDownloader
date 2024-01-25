"""Live image downloading using a tracked selenium window."""
import enum
import pathlib
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

import main
import widgets
from _utils import inter, BUTTON_COLOURS, GREEN, bool_to_state
from api.panorama import PanoramaSettings
from api.url import DEFAULT_WIDTH, DEFAULT_HEIGHT


class ImageMode(enum.Enum):
    """Download either panoramas or URL images."""
    panorama = "Panorama"
    url = "URL"


class CaptureMode(enum.Enum):
    """
    Either register URLs when a new latitude/longitude is detected,
    at fixed time intervals, or when a given key is pressed.
    """
    new_lat_long = "New Latitude/Longitude"
    fixed_time_intervals = "Fixed Time Intervals"
    keybind = "Keybind"


class SaveMode(enum.Enum):
    """
    Format file save names in various ways: smallest available integer,
    Unix timestamp, formatted date/time, panorama ID, latitude/longitude.
    """
    smallest_integer = "Smallest Available Integer"
    unix_timestamp = "Unix Timestamp"
    date_time = "Formatted Date/Time"
    panorama_id = "Panorama ID"
    lat_long = "Latitude/Longitude"


DEFAULT_IMAGE_MODE = 1
DEFAULT_CAPTURE_MODE = 0
DEFAULT_SAVE_MODE = SaveMode.date_time.value
SAVE_MODE_OPTIONS = {
    "Smallest Available Integer": SaveMode.smallest_integer,
    "Unix Timestamp": SaveMode.unix_timestamp,
    "Formatted Date/Time": SaveMode.date_time,
    "Latitude/Longitude": SaveMode.lat_long
}
PANORAMA_ID_SAVE_MODE_OPTIONS = (
    SAVE_MODE_OPTIONS | {"Panorama ID": SaveMode.panorama_id})

FIXED_TIME_INTERVALS = {
    "5 seconds": 5,
    "10 seconds": 10,
    "15 seconds": 15,
    "30 seconds": 30,
    "45 seconds": 45,
    "60 seconds": 60,
    "90 seconds": 90,
    "2 minutes": 120,
    "5 minutes": 300,
    "10 minutes": 600,
    "Paused": -1
}
DEFAULT_FIXED_TIME_INTERVAL = "15 seconds"
DEFAULT_KEYBIND = ("s",)
MAX_KEYBIND_LENGTH = 3
STATE_NAMES = {
    "Control": "Ctrl",
    "Shift": "Shift",
    "Alt": "Alt"
}
STATE_MASKS = {
    "Control": 0b00000100,
    "Shift": 0b0000000001,
    "Alt": 131072
}
# Support various symbols and special characters as keybinds.
KEYSYMS = {
    "Tab": "Tab", "Insert": "Ins", "Delete": "Del", "BackSpace": "Back",
    "Return": "Ret", "exclam": "!", "quotedbl": '"', "sterling": "£",
    "dollar": "$", "percent": "%", "asciicircum": "^", "ampersand": "&",
    "asterisk": "*", "parenleft": "(", "parenright": ")", "bracketleft": "[",
    "bracketright": "]", "braceleft": "{", "braceright": "}", "minus": "-",
    "underscore": "_", "plus": "+", "equal": "=", "colon": ":",
    "semicolon": ";", "at": "@", "apostrophe": "'", "numbersign": "#",
    "asciitilde": "~", "backslash": "\\", "bar": "|", "comma": ",",
    "period": ".", "greater": ">", "less": "<", "question": "?", "slash": "/",
    "Up": "↑", "Down": "↓", "Left": "←", "Right": "→"
} | {f"F{f}": f"F{f}" for f in range(1, 13)}


class LiveDownloading(tk.Frame):
    """Live downloading window."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(f"{main.TITLE} - Live Downloading")

        self.title = tk.Label(
            self, font=inter(25, True), text="Live Downloading")
        self.back_button = tk.Button(
            self, font=inter(20), text="Back", width=15,
            **BUTTON_COLOURS, command=self.back)
        self.start_button = tk.Button(
            self, font=inter(20), text="Start", width=15,
            **BUTTON_COLOURS, command=self.start)

        self.notebook = ttk.Notebook(self)
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=inter(15))
        self.settings_frame = LiveSettingsFrame(self.notebook)
        self.info_frame = LiveInfoFrame(self.notebook)
        self.settings_frame.pack()
        self.info_frame.pack()
        self.notebook.add(self.settings_frame, text="Settings")
        self.notebook.add(self.info_frame, text="Output")

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
    
    def update_start_button_state(self, folder_set: bool) -> None:
        """Updates start button state based on inputs."""
        self.start_button.config(state=bool_to_state(folder_set))


class LiveSettingsFrame(tk.Frame):
    """Handles the various live downloading options."""

    def __init__(self, master: ttk.Notebook) -> None:
        super().__init__(master)
        self.image_mode_frame = LiveImageMode(self)
        self.capture_mode_frame = LiveCaptureMode(self)
        self.save_mode_frame = LiveSaveMode(self)

        self.image_mode_frame.pack(pady=25)
        self.capture_mode_frame.pack(pady=25)
        self.save_mode_frame.pack(pady=25)

        self.synchronise()
    
    def synchronise(self) -> None:
        """
        Performs any relevant updates to other settings
        after a significant change.
        """
        self.save_mode_frame.update_options(
            self.image_mode_frame.image_mode == ImageMode.panorama)
        self.master.master.update_start_button_state(
            self.save_mode_frame.folder_set)


class LiveImageMode(tk.Frame):
    """Allows the user to download panoramas or URL images."""

    def __init__(self, master: LiveSettingsFrame) -> None:
        super().__init__(master)
        self.panorama_settings = PanoramaSettings()
        self.width = DEFAULT_WIDTH
        self.height = DEFAULT_HEIGHT
        self._mode = tk.IntVar(value=DEFAULT_IMAGE_MODE)
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

        self.update_info_label(first=True)
    
    @property
    def image_mode(self) -> ImageMode:
        return ImageMode.panorama if self._mode.get() == 0 else ImageMode.url
    
    def update_info_label(self, first: bool = False) -> None:
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
        if not first:
            # Also update save mode options state.
            self.master.synchronise()
    
    def edit(self) -> None:
        """Opens the appropriate settings toplevel for editing."""
        if self.image_mode == ImageMode.panorama:
            widgets.PanoramaIDSettingsToplevel(
                self, self.master.master.master.root, "panorama_settings")
            return
        widgets.UrlSettingsToplevel(self, self.master.master.master.root)


class LiveCaptureMode(tk.Frame):
    """Allows the user to select the mechanism of capturing URLs."""

    def __init__(self, master: LiveSettingsFrame) -> None:
        super().__init__(master)
        self._fixed_time_interval_text = DEFAULT_FIXED_TIME_INTERVAL
        self.keybind = DEFAULT_KEYBIND
        self._mode = tk.IntVar(value=DEFAULT_CAPTURE_MODE)
        self._mode.trace_add("write", lambda *_: self.update_display())
        self.label = tk.Label(self, font=inter(20), text="Capture Mode:")
        self.label.grid(row=0, column=0, padx=5, pady=5)
        for value, text in enumerate(
            ("New Lat/Long", "Fixed Intervals", "Keybind")
        ):
            radiobutton = tk.Radiobutton(
                self, font=inter(20), text=text, width=15, value=value,
                variable=self._mode, **BUTTON_COLOURS, indicatoron=False,
                selectcolor=GREEN)
            radiobutton.grid(row=0, column=value + 1, padx=5, pady=5)
        
        self.info_label = tk.Label(self, font=inter(12))
        self.edit_button = tk.Button(
            self, font=inter(12), text="Edit", width=15,
            **BUTTON_COLOURS, command=self.edit, state="disabled")
        self.info_label.grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        self.edit_button.grid(row=1, column=3, padx=5, pady=5)
        self.update_display()
    
    @property
    def mode(self) -> CaptureMode:
        return (
            CaptureMode.new_lat_long, CaptureMode.fixed_time_intervals,
            CaptureMode.keybind)[self._mode.get()]

    @property
    def fixed_time_interval(self) -> int | float:
        return FIXED_TIME_INTERVALS[self._fixed_time_interval_text]

    def update_display(self) -> None:
        """Updates the display when the register mode is changed."""
        self.update_info_label()
        self.edit_button.config(
            state=bool_to_state(self.mode != CaptureMode.new_lat_long))

    def update_info_label(self) -> None:
        """Updates the information label when settings are changed."""
        match self.mode:
            case CaptureMode.new_lat_long:
                text = "URLs with a new latitude/longitude will be captured."
            case CaptureMode.fixed_time_intervals:
                text = (
                    f"Time between captures: {self._fixed_time_interval_text}")
            case CaptureMode.keybind:
                text = f"Keybind: {' '.join(self.keybind)}"
        self.info_label.config(text=text)

    def edit(self) -> None:
        """Allows editing of a sub-setting."""
        if self.mode == CaptureMode.fixed_time_intervals:
            FixedTimeIntervalToplevel(self)
            return
        KeybindToplevel(self)


class FixedTimeIntervalToplevel(tk.Toplevel):
    """Toplevel setting for setting a fixed time between captures."""

    def __init__(self, master: LiveCaptureMode) -> None:
        super().__init__(master)
        self._fixed_time_interval = tk.StringVar(
            value=master._fixed_time_interval_text)
        self.title(
            f"{main.TITLE} - Live Downloading - Fixed Time Interval Setting")
        self.grab_set()

        self.title_label = tk.Label(
            self, font=inter(25, True), text="Fixed Time Interval Setting")
        self.info_label = tk.Label(
            self, font=inter(12),
            text=("Consider how often you would like to capture URLs.\n"
                "Note that the same URL will only be downloaded once."))

        self.title_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        self.info_label.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        for i, text in enumerate(FIXED_TIME_INTERVALS):
            radiobutton = tk.Radiobutton(
                self, font=inter(15), text=text, width=15, value=text,
                variable=self._fixed_time_interval, **BUTTON_COLOURS,
                indicatoron=False, selectcolor=GREEN)
            radiobutton.grid(row=2 + i // 2, column=i % 2, padx=5, pady=3)
        
        self.save_button = tk.Button(
            self, font=inter(20), text="Save", width=15,
            **BUTTON_COLOURS, command=self.save)
        self.save_button.grid(row=99, column=0, columnspan=2, padx=10, pady=10)
    
    def save(self) -> None:
        """Saves the fixed time interval setting."""
        self.master._fixed_time_interval_text = self._fixed_time_interval.get()
        self.master.update_info_label()
        self.destroy()


class KeybindToplevel(tk.Toplevel):
    """Allows the user to set a keybind to capture URLs by."""

    def __init__(self, master: LiveCaptureMode) -> None:
        super().__init__(master)
        self.keybind = master.keybind
        self.keys_pressed = set()
        self.keys_released = set()
        self.title(f"{main.TITLE} - Live Downloading - Keybind Setting")
        self.grab_set()
        self.focus()

        self.title_label = tk.Label(
            self, font=inter(25, True), text="Keybind Setting")
        self.info_label = tk.Label(
            self, font=inter(12),
            text=("When the given keybind is registered, "
                "the current URL will be captured.\n"
                "Try to select a keybind you feel comfortable using, "
                "ideally one not already used in Chrome.\n"
                f"Maximum keybind length: {MAX_KEYBIND_LENGTH}"))
        self.keybind_label = tk.Label(
            self, font=inter(25),
            text=f"Current keybind: {' '.join(self.keybind)}")
        self.save_button = tk.Button(
            self, font=inter(20), text="Save", width=15,
            **BUTTON_COLOURS, command=self.save)
        
        self.bind("<KeyPress>", self.key_press)
        self.bind("<KeyRelease>", self.key_release)
        
        self.title_label.pack(padx=10, pady=10)
        self.info_label.pack(padx=10, pady=10)
        self.keybind_label.pack(padx=10, pady=10)
        self.save_button.pack(padx=10, pady=10)
    
    @property
    def all_released(self) -> bool:
        # All pressed keys also registered as released.
        keybind_lists = self._get_keybind_lists()
        return sorted(keybind_lists[0]) == sorted(keybind_lists[1])
    
    @property
    def no_pressed(self) -> bool:
        # No pressed keys, but possibly some failed
        # to have been registered as released.
        keybind_lists = self._get_keybind_lists()
        return not set(keybind_lists[0]) - set(keybind_lists[1])

    def _get_keybind_lists(self) -> list:
        keybind_lists = []
        for keybinds in (self.keys_pressed, self.keys_released):
            keybind_lists.append(
                [
                    tuple(part.lower() for part in keybind.split("+")
                        if part not in STATE_NAMES.values())
                    for keybind in keybinds])
        return keybind_lists

    def _get_key(self, event: tk.Event) -> str | None:
        if event.keysym in KEYSYMS:
            keysym = KEYSYMS[event.keysym]
        elif len(event.keysym) > 1:
            return None
        else:
            keysym = event.keysym
        parts = [
            STATE_NAMES[state]
            for state in ("Control", "Shift", "Alt")
                if event.state & STATE_MASKS[state]] + [keysym]
        return "+".join(parts)

    def key_press(self, event: tk.Event) -> None:
        """Registers a key input."""
        key = self._get_key(event)
        if key is None:
            return
        self.keys_pressed.add(key)
        if key in self.keys_released:
            self.keys_released.remove(key)
    
    def key_release(self, event: tk.Event) -> None:
        """Key release. If all keys released, that is the keybind."""
        key = self._get_key(event)
        if key is None:
            return
        self.keys_released.add(self._get_key(event))
        if self.all_released and len(self.keys_pressed) <= MAX_KEYBIND_LENGTH:
            self.keybind = tuple(sorted(self.keys_pressed))
            self.keybind_label.config(
                text=f"Current keybind: {' '.join(self.keybind)}")
        if self.all_released or self.no_pressed:
            self.keys_pressed.clear()
            self.keys_released.clear()
    
    def save(self) -> None:
        """Saves the currently set keybind."""
        self.master.keybind = self.keybind
        self.master.update_info_label()
        self.destroy()


class LiveSaveMode(tk.Frame):
    """
    Allows the user to select the file name save format and the save folder.
    """

    def __init__(self, master: LiveSettingsFrame) -> None:
        super().__init__(master)
        self._save_mode = tk.StringVar(value=DEFAULT_SAVE_MODE)
        self._save_folder = tk.StringVar(value="Not Set")
        self.save_mode_label = tk.Label(
            self, font=inter(20), text="Filename Mode:")
        style = ttk.Style()
        style.configure("TMenubutton", font=inter(15), width=20)

        self.save_folder_label = tk.Label(
            self, font=inter(20), text="Save Folder:")
        self.save_folder_entry = tk.Entry(
            self, font=inter(10), width=64, textvariable=self._save_folder,
            state="readonly")
        self.save_folder_button = tk.Button(
            self, font=inter(12), text="Select", width=15,
            **BUTTON_COLOURS, command=self.select_folder)

        self.save_mode_label.grid(row=0, column=0, padx=5, pady=5)
        self.save_folder_label.grid(row=1, column=0, padx=5, pady=5)
        self.save_folder_entry.grid(row=1, column=1, padx=5, pady=5)
        self.save_folder_button.grid(row=1, column=2, padx=5, pady=5)
        
    @property
    def save_mode(self) -> SaveMode:
        return PANORAMA_ID_SAVE_MODE_OPTIONS[self._save_mode.get()]
    
    @property
    def folder_set(self) -> bool:
        return self._save_folder.get() != "Not Set"
    
    @property
    def save_folder(self) -> pathlib.Path:
        return pathlib.Path(self._save_folder.get())
    
    def select_folder(self) -> None:
        """Allows user to set save folder."""
        folder = filedialog.askdirectory(title="Select Save Folder")
        if not folder:
            return
        self._save_folder.set(folder)
        self.master.synchronise()
    
    def update_options(self, is_panorama_mode: bool) -> None:
        """Updates options depending on image mode."""
        if hasattr(self, "save_mode_option_menu"):
            self.save_mode_option_menu.destroy()
        if is_panorama_mode:
            options = PANORAMA_ID_SAVE_MODE_OPTIONS
        else:
            options = SAVE_MODE_OPTIONS
            if self.save_mode == SaveMode.panorama_id:
                self._save_mode.set(DEFAULT_SAVE_MODE)
        self.save_mode_option_menu = ttk.OptionMenu(
            self, self._save_mode, None, *options)
        self.save_mode_option_menu.grid(
            row=0, column=1, columnspan=2, padx=5, pady=5)


class LiveInfoFrame(tk.Frame):
    """Handles live information display, and logging."""

    def __init__(self, master: ttk.Notebook) -> None:
        super().__init__(master)
