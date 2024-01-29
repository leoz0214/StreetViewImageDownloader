"""Live image downloading using a tracked selenium window."""
import asyncio
import datetime as dt
import enum
import hashlib
import json
import os
import pathlib
import queue
import threading
import time
import tkinter as tk
from contextlib import suppress
from dataclasses import dataclass
from timeit import default_timer as timer
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

import psutil
from pynput import keyboard
from selenium.webdriver import Chrome

import main
import widgets
from _utils import (
    inter, BUTTON_COLOURS, GREEN, RED, bool_to_state, format_seconds,
    load_cpp_foreground_pid_library)
from api.panorama import PanoramaSettings, _get_async_images, _combine_tiles
from api.url import DEFAULT_WIDTH, DEFAULT_HEIGHT, parse_url, get_pil_image


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


class DownloadMode(enum.Enum):
    """
    URLs may be captured very fast, too fast for the program
    to keep up with in terms of processing each URL.
    Either maintain a queue or download on demand.
    """
    queue = "Queue"
    on_demand = "On Demand"


@dataclass
class LiveSettings:
    """Bundles together all the settings for live downloading."""
    # Image Mode
    image_mode: ImageMode
    panorama_settings: PanoramaSettings
    url_width: int
    url_height: int
    # Capture Mode
    capture_mode: CaptureMode
    fixed_time_interval: int | float
    keybind: tuple[str]
    # Save Mode
    save_mode: SaveMode
    save_folder: pathlib.Path
    # Download Mode / Stop Upon Error
    download_mode: DownloadMode
    stop_upon_error: bool

    def to_json(self) -> str:
        """
        Converts the settings object to a JSON string with
        hashing to maintain data integrity.
        """
        data = {
            "image_mode": {
                "image_mode": self.image_mode.value,
                "panorama_settings": (
                    self.panorama_settings.zoom,
                    self.panorama_settings.top_left,
                    self.panorama_settings.bottom_right,
                ),
                "url_width": self.url_width,
                "url_height": self.url_height
            },
            "capture_mode": {
                "capture_mode": self.capture_mode.value,
                "fixed_time_interval": self.fixed_time_interval,
                "keybind": self.keybind,
            },
            "save_mode": {
                "save_mode": self.save_mode.value,
                "save_folder": str(self.save_folder)
            },
            "download_mode": self.download_mode.value,
            "stop_upon_error": self.stop_upon_error
        }
        integrity_hash = hashlib.sha256(
            json.dumps(data).encode()).hexdigest()
        data["integrity_hash"] = integrity_hash
        return json.dumps(data, indent=4)

    @staticmethod
    def from_json(json_data: dict) -> "LiveSettings":
        """Creates the settings object from JSON."""
        integrity_hash = json_data.pop("integrity_hash", None)
        expected_hash = hashlib.sha256(
            json.dumps(json_data).encode()).hexdigest()
        if integrity_hash != expected_hash:
            raise ValueError(
                "Data is not in its original form - "
                "modification has taken place.")
        return LiveSettings(
            ImageMode(json_data["image_mode"]["image_mode"]),
            PanoramaSettings(*json_data["image_mode"]["panorama_settings"]),
            json_data["image_mode"]["url_width"],
            json_data["image_mode"]["url_height"],
            CaptureMode(json_data["capture_mode"]["capture_mode"]),
            json_data["capture_mode"]["fixed_time_interval"],
            tuple(json_data["capture_mode"]["keybind"]),
            SaveMode(json_data["save_mode"]["save_mode"]),
            pathlib.Path(json_data["save_mode"]["save_folder"]),
            DownloadMode(json_data["download_mode"]),
            json_data["stop_upon_error"])


# Default settings
DEFAULT_IMAGE_MODE = 1
DEFAULT_CAPTURE_MODE = 0
DEFAULT_SAVE_MODE = SaveMode.date_time.value
DEFAULT_DOWNLOAD_MODE = 1
DEFAULT_STOP_UPON_ERROR = False

SAVE_MODE_OPTIONS = {
    "Smallest Available Integer": SaveMode.smallest_integer,
    "Unix Timestamp": SaveMode.unix_timestamp,
    "Formatted Date/Time": SaveMode.date_time,
    "Latitude/Longitude": SaveMode.lat_long
}
PANORAMA_ID_SAVE_MODE_OPTIONS = (
    SAVE_MODE_OPTIONS | {"Panorama ID": SaveMode.panorama_id})

FIXED_TIME_INTERVALS = {
    "5 seconds": 5, "10 seconds": 10, "15 seconds": 15, "30 seconds": 30,
    "45 seconds": 45, "90 seconds": 90, "2 minutes": 120, "5 minutes": 300,
    "10 minutes": 600, "Paused": -1
}
DEFAULT_FIXED_TIME_INTERVAL = "15 seconds"
DEFAULT_KEYBIND = ("s",)
MAX_KEYBIND_LENGTH = 3
STATE_NAMES = {"Control": "Ctrl", "Shift": "Shift", "Alt": "Alt"}
STATE_MASKS = {"Control": 0b00000100, "Shift": 0b00000001, "Alt": 131072}
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
# Ascii control characters. Index = binary value.
CONTROL_CHARACTERS = "@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_"
CONTROL_KEYS = (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
SHIFT_KEYS = (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
ALT_KEYS = (
    keyboard.Key.alt, keyboard.Key.alt_gr,
    keyboard.Key.alt_l, keyboard.Key.alt_r)

MAPS_URL = "https://www.google.com/maps"
TIME_BETWEEN_CHECKS = 0.02
TIME_BETWEEN_INFO_REFRESH_MS = 100

get_foreground_pid = load_cpp_foreground_pid_library().get_foreground_pid


class LiveDownloading(tk.Frame):
    """Live downloading window."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(f"{main.TITLE} - Live Downloading")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # Selenium Chrome window object.
        self.window = None
        # Live downloading has been terminated.
        self.stopped = False
        # Queue of URLs to download.
        self.download_queue = queue.Queue()
        # Any exception that occurs in the downloading threads
        # is written to this variable.
        self.exception = None
        # The resulting image from a downloading thread.
        self.image = None
        # Ensures expired downloads are ignored by incrementing
        # the download ID per new download and upon stopping.
        self.download_id = 0
        # Tracks the number of downloaded images in the session.
        self.download_count = 0
        # Similar to stopped, but compatible with the API.
        self.cancelled = False
        # Flag indicating the main live loop should stop the session.
        self.to_stop = False
        # Currently stopping session.
        # Prevents creating a new one until the previous one is ended.
        self.stopping = False
        # Start timestamp (to track time elapsed).
        self.start_time = None
        # Timestamp of previous captured by fixed time intervals.
        self.previous_time = None
        # Keys pressed (for keybind capture).
        self.keys_pressed = set()
        # Cumulative keys pressed.
        self.keys_pressed_count = 0
        # Cumulative keys released.
        self.keys_released_count = 0
        # Previous key pressed (ignore hold down).
        self.previous_key_press = None
        # Shift states currently active (multiple possible).
        self.shift_states = set()
        # Alt states currently active (multiple possible).
        self.alt_states = set()

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
        self.to_stop = True
        self.destroy()
        self.root.protocol("WM_DELETE_WINDOW", self.root.quit)
        main.MainMenu(self.root).pack()
    
    def _live(self) -> None:
        # Main live code run in the thread.
        try:
            self.window = Chrome()
            if self.to_stop:
                self.stop()
                return
            process = psutil.Process(self.window.service.process.pid)
            pids = {child.pid for child in process.children()}
            date_time = dt.datetime.now().replace(microsecond=0)
            self.info_frame.logger.log_good(
                f"Initialised window at {date_time}")
        except Exception as e:
            messagebox.showerror(
                "Error", 
                    "Unfortunately, an error occurred "
                    f"while initialising the window: {e}")
            date_time = dt.datetime.now().replace(microsecond=0)
            self.info_frame.logger.log_bad(
                f"An initialisation error occurred at {date_time}")
            self.stop()
            self.info_frame.logger.log_bad(
                f"Live tracking stopped at {date_time}")
            return
        threading.Thread(target=self._handle_queue, daemon=True).start()
        keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press, on_release=self._on_key_release)
        keyboard_listener.start()
        # Unique latitude/longitude maintenance
        # as each lat/long has a unique panorama ID.
        seen_panorama_ids = set()
        try:
            self.window.get(MAPS_URL)
            while not self.to_stop:
                settings = self.settings_frame.settings
                try:
                    url = self.window.current_url
                    if url is None:
                        break
                except Exception:
                    break
                match settings.capture_mode:
                    case CaptureMode.new_lat_long:
                        # No need to do anything for new lat/long (default).
                        pass
                    case CaptureMode.fixed_time_intervals:
                        fixed_time_interval = settings.fixed_time_interval
                        if (
                            fixed_time_interval == -1 or
                            timer() - self.previous_time < fixed_time_interval
                        ):
                            # Paused OR not time yet for the next capture.
                            continue
                        self.previous_time = timer()
                    case CaptureMode.keybind:
                        foreground_pid = get_foreground_pid()
                        print(foreground_pid in pids)
                        continue
                try:
                    url_info = parse_url(url)
                except ValueError:
                    continue
                panorama_id = url_info.panorama_id
                if panorama_id in seen_panorama_ids:
                    continue
                seen_panorama_ids.add(panorama_id)
                self.info_frame.logger.log_neutral(
                    f"Captured URL: {url}")
                self._add_to_queue(
                    url,
                    settings.download_mode == DownloadMode.on_demand)
                time.sleep(TIME_BETWEEN_CHECKS)
        except Exception as e:
            date_time = dt.datetime.now().replace(microsecond=0)
            self.info_frame.logger.log_bad(f"Fatal error at {date_time}: {e}")
        keyboard_listener.stop()
        self.stop()
        date_time = dt.datetime.now().replace(microsecond=0)
        self.info_frame.logger.log_bad(f"Live tracking stopped at {date_time}")
    
    def _on_key_press(self, key) -> None:
        if key != self.previous_key_press:
            self.keys_pressed_count += 1
            self.previous_key_press = key
            if key in SHIFT_KEYS:
                self.shift_states.add(key)
            elif key in ALT_KEYS:
                self.alt_states.add(key)
            elif key in CONTROL_KEYS:
                return
            else:
                parts = []
                if self.shift_states:
                    parts.append("Shift")
                if self.alt_states:
                    parts.append("Alt")
                if ord(key.char) < 32:
                    parts.append("Ctrl")
                    parts.append(CONTROL_CHARACTERS[ord(key.char)])
                else:
                    parts.append(key.char)
                self.keys_pressed.add("+".join(parts))
    
    def _on_key_release(self, key) -> None:
        self.keys_released_count += 1
        if key in SHIFT_KEYS:
            self.shift_states.remove(key)
        if key in ALT_KEYS:
            self.alt_states.remove(key)
        if self.keys_pressed_count == self.keys_released_count:
            # Reset unnecessary - equal, ready for next press/release cycle.
            if self._is_keybind():
                print(self.keys_pressed)
            # Do reset pressed keys and previous pressed key, however.
            self.keys_pressed.clear()
            self.previous_key_press = None
    
    def _is_keybind(self) -> bool:
        # The matching keybind as per the settings has been registered.
        keybind_lists = []
        for keys in (self.keys_pressed, self.settings_frame.settings.keybind):
            keybind_list = sorted(
                sorted(keybind.split("+")) for keybind in keys)
            keybind_lists.append(keybind_list)
        return keybind_lists[0] == keybind_lists[1]
    
    def _handle_queue(self) -> None:
        # Handles the downloading of URLs as they appear in the queue.
        while True:
            if self.stopped:
                return
            time.sleep(TIME_BETWEEN_CHECKS)
            settings = self.settings_frame.settings
            if not self.download_queue.qsize():
                continue
            try:
                url = self.download_queue.get(block=False)
            except queue.Empty:
                continue
            url_info = parse_url(url)
            self.download_id += 1
            if settings.image_mode == ImageMode.panorama:
                target = lambda: self._download_panorama_image(
                    url_info.panorama_id, settings.panorama_settings,
                    self.download_id)
            else:
                target = lambda: self._download_url_image(
                    url, settings.url_width, settings.url_height,
                    self.download_id)
            self.info_frame.logger.log_neutral(f"Downloading URL: {url}")
            threading.Thread(target=target, daemon=True).start()
            while (
                self.image is None and self.exception is None
                and not self.stopped
            ):
                time.sleep(TIME_BETWEEN_CHECKS)
            if self.stopped:
                return
            # Refresh settings after processing.
            settings = self.settings_frame.settings
            if self.exception is not None:
                self.info_frame.logger.log_bad(f"Error: {self.exception}")
                if settings.stop_upon_error:
                    self.to_stop = True
                self.exception = None
            if self.image is not None:
                self._save_image(
                    settings, url_info.latitude, url_info.longitude,
                    url_info.panorama_id)
                self.image = None
    
    def _download_panorama_image(
        self, panorama_id: str, settings: PanoramaSettings, download_id: int
    ) -> None:
        tiles = [[None] * settings.width for _ in range(settings.height)]
        try:
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(_get_async_images(tiles, panorama_id, settings, self))
            image = _combine_tiles(tiles, True, self)
            if download_id == self.download_id:
                self.image = image
        except Exception as e:
            if download_id == self.download_id:
                self.exception = e
    
    def _download_url_image(
        self, url: str, width: int, height: int, download_id: int
    ) -> None:
        try:
            image = get_pil_image(url, width, height)
            if download_id == self.download_id:
                self.image = image
        except Exception as e:
            if download_id == self.download_id:
                self.exception = e
    
    def _save_image(
        self, settings: LiveSettings,
        latitude: float, longitude: float, panorama_id: str
    ) -> None:
        folder = settings.save_folder
        match settings.save_mode:
            case SaveMode.smallest_integer:
                n = 0
                while (save_path := folder / f"{n}.jpg").exists():
                    n += 1
            case SaveMode.unix_timestamp:
                timestamp = int(time.time())
                save_path = folder / f"{timestamp}.jpg"
            case SaveMode.date_time:
                date_time = dt.datetime.now().replace(
                    microsecond=0).isoformat().replace(":", ".")
                save_path = folder / f"{date_time}.jpg"
            case SaveMode.lat_long:
                save_path = folder / f"{latitude}_{longitude}.jpg"
            case SaveMode.panorama_id:
                save_path = folder / f"{panorama_id}.jpg"
        if save_path.exists():
            n = 1
            stem = save_path.stem
            while (save_path := folder / f"{stem} ({n}).jpg").exists():
                n += 1
        if self.to_stop:
            return
        try:
            self.image.save(save_path, format="jpeg")
            date_time = dt.datetime.now().replace(microsecond=0)
            if self.to_stop:
                return
            self.download_count += 1
            self.info_frame.logger.log_good(
                f"Successfully saved image to {save_path} at {date_time}")
        except Exception as e:
            if self.to_stop:
                return
            self.info_frame.logger.log_bad(f"Error while saving: {e}")
            if settings.stop_upon_error:
                self.to_stop = True

    def _add_to_queue(self, url: str, on_demand: bool) -> None:
        # Adds a URL to the queue to be downloaded.
        if on_demand:
            # Clear queue - max one item at a time.
            self.download_queue = queue.Queue()
        self.download_queue.put(url)
        
    def start(self) -> None:
        """Opens the selenium window and starts the tracking."""
        while self.stopping:
            time.sleep(TIME_BETWEEN_CHECKS)
        self.stopped = False
        self.cancelled = False
        self.download_count = 0
        self.start_time = timer()
        self.previous_time = timer()
        self.start_button.config(
            text="Stop", bg=RED, activebackground=RED,
            command=lambda: setattr(self, "to_stop", True))
        threading.Thread(target=self._live, daemon=True).start()

    def stop(self) -> None:
        """Stops the live tracking."""
        self.to_stop = False
        self.stopping = True
        with suppress(Exception):
            self.window.quit()
        self.download_id += 1
        self.window = None
        self.stopped = True
        self.image = None
        self.exception = None
        self.download_queue = queue.Queue()
        self.cancelled = True
        with suppress(tk.TclError):
            self.start_button.config(
                text="Start", **BUTTON_COLOURS, command=self.start)
        self.stopping = False
        self.to_stop = False
    
    def close(self) -> None:
        """Closes the window, ensuring live mode is stopped."""
        self.stop()
        os._exit(0)
    
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
        self.download_mode_frame = LiveDownloadMode(self)
        self.stop_upon_error_checkbutton = LiveStopUponError(self)
        self.import_json_button = tk.Button(
            self, font=inter(15), text="Import JSON", width=15,
            **BUTTON_COLOURS, command=self.import_json)
        self.export_json_button = tk.Button(
            self, font=inter(15), text="Export JSON", width=15,
            **BUTTON_COLOURS, command=self.export_json)

        self.image_mode_frame.grid(row=0, column=0, columnspan=2, pady=10)
        self.capture_mode_frame.grid(row=1, column=0, columnspan=2, pady=10)
        self.save_mode_frame.grid(row=2, column=0, columnspan=2, pady=10)
        self.download_mode_frame.grid(row=3, column=0, columnspan=2, pady=10)
        self.stop_upon_error_checkbutton.grid(
            row=4, column=0, columnspan=2, pady=10)
        self.import_json_button.grid(row=5, column=0, pady=10)
        self.export_json_button.grid(row=5, column=1, pady=10)

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
    
    @property
    def settings(self) -> LiveSettings:
        # Returns entire settings object based on current GUI inputs.
        return LiveSettings(
            self.image_mode_frame.image_mode,
            self.image_mode_frame.panorama_settings,
            self.image_mode_frame.width, self.image_mode_frame.height,

            self.capture_mode_frame.capture_mode,
            self.capture_mode_frame.fixed_time_interval,
            self.capture_mode_frame.keybind,

            self.save_mode_frame.save_mode, self.save_mode_frame.save_folder,

            self.download_mode_frame.download_mode,
            self.stop_upon_error_checkbutton.stop_upon_error)

    def import_json(self) -> None:
        """Allows the user to select a JSON settings file to import."""
        file = filedialog.askopenfilename(
            defaultextension=".json", filetypes=(("JSON", ".json"),),
            title="Import JSON")
        if not file:
            return
        try:
            with open(file, "r", encoding="utf8") as f:
                try:
                    json_data = json.load(f)
                except Exception:
                    raise ValueError("Invalid JSON file.")
            settings = LiveSettings.from_json(json_data)
            self.image_mode_frame.import_settings(settings)
            self.capture_mode_frame.import_settings(settings)
            self.save_mode_frame.import_settings(settings)
            self.download_mode_frame.download_mode = settings.download_mode
            self.stop_upon_error_checkbutton.stop_upon_error = (
                settings.stop_upon_error)
            self.synchronise()
        except Exception as e:
            messagebox.showerror(
                "Error", f"Unfortunately, an error has occurred: {e}")

    def export_json(self) -> None:
        """Exports settings in JSON format."""
        file = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=(("JSON", ".json"),),
            title="Export JSON")
        if not file:
            return
        try:
            with open(file, "w", encoding="utf8") as f:
                f.write(self.settings.to_json())
        except Exception as e:
            messagebox.showerror(
                "Error", f"Unfortunately, an error has occurred: {e}")


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
        return (ImageMode.panorama, ImageMode.url)[self._mode.get()]
    
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

    def import_settings(self, settings: LiveSettings) -> None:
        """Adjust settings based on imported input."""
        self._mode.set(
            (ImageMode.panorama, ImageMode.url).index(settings.image_mode))
        self.panorama_settings = settings.panorama_settings
        self.width = settings.url_width
        self.height = settings.url_height
        self.update_info_label()


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
    def capture_mode(self) -> CaptureMode:
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
            state=bool_to_state(self.capture_mode != CaptureMode.new_lat_long))

    def update_info_label(self) -> None:
        """Updates the information label when settings are changed."""
        match self.capture_mode:
            case CaptureMode.new_lat_long:
                text = "URLs with a new latitude/longitude will be captured."
            case CaptureMode.fixed_time_intervals:
                if self.fixed_time_interval == -1:
                    text = "Capturing paused"
                else:
                    text = (
                        "Time between captures: "
                        f"{self._fixed_time_interval_text}")
            case CaptureMode.keybind:
                text = f"Keybind: {' '.join(self.keybind)}"
        self.info_label.config(text=text)

    def edit(self) -> None:
        """Allows editing of a sub-setting."""
        if self.capture_mode == CaptureMode.fixed_time_intervals:
            FixedTimeIntervalToplevel(self)
            return
        KeybindToplevel(self)
    
    def import_settings(self, settings: LiveSettings) -> None:
        """Adjusts settings based on imported input."""
        self._mode.set(
            (CaptureMode.new_lat_long, CaptureMode.fixed_time_intervals,
                CaptureMode.keybind).index(settings.capture_mode))
        self._fixed_time_interval_text = next(
            (text for text, value in FIXED_TIME_INTERVALS.items()
                if value == settings.fixed_time_interval))
        self.keybind = settings.keybind
        self.update_display()


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
        self.bind("<FocusOut>", lambda *_: self.focus_out())
        
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

    def _get_keybind_lists(self) -> list[list[tuple]]:
        # Get keybinds pressed and released, but case-insensitive and
        # ignoring special states: Control/Shift/Alt.
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
            # Not a character key nor a supported control key.
            return None
        else:
            keysym = event.keysym
        parts = [
            name for state, name in STATE_NAMES.items()
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
            final_keys_pressed = []
            for key in self.keys_pressed:
                if "++" in key:
                    break
                parts = key.split("+")
                if "Ctrl" in parts:
                    parts[-1] = parts[-1].upper()
                    if parts[-1] not in CONTROL_CHARACTERS:
                        break
                final_keys_pressed.append("+".join(parts))
            else:
                self.keybind = tuple(sorted(final_keys_pressed))
                self.keybind_label.config(
                    text=f"Current keybind: {' '.join(self.keybind)}")
        if self.all_released or self.no_pressed:
            self.keys_pressed.clear()
            self.keys_released.clear()
    
    def focus_out(self) -> None:
        """Window lost focus, cancel keybind setting."""
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
        self._save_folder.set(str(pathlib.Path(folder)))
        self.master.synchronise()
    
    def update_options(self, is_panorama_mode: bool) -> None:
        """Updates options depending on image mode."""
        with suppress(AttributeError):
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
    
    def import_settings(self, settings: LiveSettings) -> None:
        """"Adjusts settings based on imported input."""
        self._save_mode.set(
            next(text for text, value in PANORAMA_ID_SAVE_MODE_OPTIONS.items()
                    if value == settings.save_mode))
        self._save_folder.set(
            str(settings.save_folder if settings.save_folder.is_dir()
                    else "Not Set"))


class LiveDownloadMode(tk.Frame):
    """Option to set the download mode."""

    def __init__(self, master: LiveSettingsFrame) -> None:
        super().__init__(master)
        self._mode = tk.IntVar(value=DEFAULT_DOWNLOAD_MODE)
        self.label = tk.Label(self, font=inter(20), text="Download Mode:")
        self.label.grid(row=0, column=0, padx=5, pady=5)
        for value, text in enumerate(("Queue", "On Demand")):
            radiobutton = tk.Radiobutton(
                self, font=inter(20), text=text, width=15, value=value,
                variable=self._mode, **BUTTON_COLOURS, indicatoron=False,
                selectcolor=GREEN)
            radiobutton.grid(row=0, column=value + 1, padx=5, pady=5)
    
    @property
    def download_mode(self) -> DownloadMode:
        return (DownloadMode.queue, DownloadMode.on_demand)[self._mode.get()]

    @download_mode.setter
    def download_mode(self, download_mode: DownloadMode) -> None:
        self._mode.set(
            (DownloadMode.queue, DownloadMode.on_demand).index(download_mode))


class LiveStopUponError(tk.Checkbutton):
    """
    Option to allow the user to stop the live downloading upon any error,
    or log but otherwise ignore errors.
    """

    def __init__(self, master: LiveSettingsFrame) -> None:
        self._stop_upon_error = tk.BooleanVar(value=DEFAULT_STOP_UPON_ERROR)
        super().__init__(
            master, font=inter(15), text="Stop upon error", width=15,
            variable=self._stop_upon_error)

    @property
    def stop_upon_error(self) -> bool:
        return self._stop_upon_error.get()
    
    @stop_upon_error.setter
    def stop_upon_error(self, stop_upon_error: bool) -> None:
        self._stop_upon_error.set(stop_upon_error)


class LiveInfoFrame(tk.Frame):
    """Handles live information display, and logging."""

    def __init__(self, master: ttk.Notebook) -> None:
        super().__init__(master)
        self.logger = widgets.Logger(self, width=100, height=20)
        self.info_label = tk.Label(self, font=inter(12))
        self.export_log_button = tk.Button(
            self, font=inter(15), text="Export Log", width=15,
            **BUTTON_COLOURS, command=self.export_log)
        
        self.logger.pack(padx=10, pady=10)
        self.info_label.pack(padx=10, pady=10)
        self.export_log_button.pack(padx=10, pady=10)

        self.info_label.after(
            TIME_BETWEEN_INFO_REFRESH_MS, self.update_info)
    
    def update_info(self) -> None:
        """Updates the info label and window title based on download state."""
        title = f"{main.TITLE} - Live Downloading"
        with suppress(Exception):
            if self.master.master.window is None:
                text = "Currently inactive"
            else:
                download_count = self.master.master.download_count
                time_elapsed = format_seconds(
                    timer() - self.master.master.start_time)
                in_queue = self.master.master.download_queue.qsize()
                text = " | ".join((
                    f"Download count: {download_count}",
                    f"Time elapsed: {time_elapsed}", f"In queue: {in_queue}"))
                settings = self.master.master.settings_frame.settings
                if settings.capture_mode == CaptureMode.fixed_time_intervals:
                    if settings.fixed_time_interval == -1:
                        # The user has paused the live downloading.
                        text = f"{text} | Capturing paused"
                    else:
                        time_until_next_capture = format_seconds(
                            settings.fixed_time_interval - (
                                timer() - self.master.master.previous_time
                            ))[3:]
                        text = (
                            f"{text} | Time until next capture: "
                            f"{time_until_next_capture}")
                title = f"{title} - {text}"
            self.info_label.config(text=text)
            self.master.master.root.title(title)
            self.info_label.after(
                TIME_BETWEEN_INFO_REFRESH_MS, self.update_info)
    
    def export_log(self) -> None:
        """Exports the log text."""
        file = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=(("Text", ".txt"),),
            title="Export Log")
        if not file:
            return
        try:
            with open(file, "w", encoding="utf8") as f:
                f.write(self.logger.text)
        except Exception as e:
            messagebox.showerror(
                "Error", f"Unfortunately, an error has occurred: {e}")
