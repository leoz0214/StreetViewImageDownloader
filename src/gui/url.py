"""URL downloading section of the GUI."""
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Union

import batch
import main
import rendering
import save
import widgets
from _utils import inter, RED, GREEN, BUTTON_COLOURS, bool_to_state
from api.url import (
    MIN_WIDTH, MIN_HEIGHT, MAX_WIDTH, MAX_HEIGHT,
    DEFAULT_WIDTH, DEFAULT_HEIGHT, parse_url, get_pil_image)


# Sensible limit
MAX_URL_INPUT_LENGTH = 512
DOWNLOAD_STATUS_CHECK_RATE = 0.05


class UrlDownload(tk.Frame):
    """GUI for downloading an image by URL."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(f"{main.TITLE} - URL Download")
        self.image = None
        self.exception = None
        self.cancelled = False
        # Infinitely incrementing variable to allow overlapping
        # download states after one is cancelled.
        self.download_id = 0

        self.title = tk.Label(self, font=inter(25, True), text="URL Download")
        self.url_input = UrlInput(self)
        self.width_input = DimensionInput(
            self, "Width:", MIN_WIDTH, MAX_WIDTH, DEFAULT_WIDTH)
        self.height_input = DimensionInput(
            self, "Height:", MIN_HEIGHT, MAX_HEIGHT, DEFAULT_HEIGHT)
        self.back_button = tk.Button(
            self, font=inter(20), text="Back", width=15,
            **BUTTON_COLOURS, command=self.back)
        self.download_button = tk.Button(
            self, font=inter(20), text="Download", width=15,
            **BUTTON_COLOURS, command=self.start_download, state="disabled")
        
        self.title.grid(row=0, column=0, columnspan=2, padx=10, pady=5)
        self.url_input.grid(row=1, column=0, columnspan=2, padx=10, pady=5)
        self.width_input.grid(row=2, column=0, columnspan=2, padx=10, pady=5)
        self.height_input.grid(row=3, column=0, columnspan=2, padx=10, pady=5)
        self.back_button.grid(row=4, column=0, padx=10, pady=(50, 10))
        self.download_button.grid(row=4, column=1, padx=10, pady=(50, 10))
    
    def update_download_button_state(self) -> None:
        """Activates or disables the download button based on URL validity."""
        self.download_button.config(state=bool_to_state(self.url_input.valid))
    
    def back(self) -> None:
        """Returns back to the main menu."""
        self.cancelled = True
        self.destroy()
        main.MainMenu(self.root).pack()
    
    def _process_download(self, download_id: int) -> None:
        try:
            url = self.url_input.url
            width = self.width_input.value
            height = self.height_input.value
            image = get_pil_image(url, width, height)
            if download_id == self.download_id:
                self.image = image
        except Exception as e:
            if download_id == self.download_id:
                self.exception = e
    
    def start_download(self) -> None:
        """Prepares to begin the download."""
        self.download_button.config(
            text="Cancel", bg=RED, activebackground=RED, command=self.cancel)
        threading.Thread(target=self.download, daemon=True).start()
    
    def download(self) -> None:
        """Proceeds to download the image at the given URL."""
        threading.Thread(
            target=self._process_download(self.download_id),
            daemon=True).start()
        while True:
            if self.exception is not None:
                messagebox.showerror(
                    "Error",
                    f"Unfortunately, an error has occurred: {self.exception}")
                break
            if self.image is not None or self.cancelled:
                break
            time.sleep(DOWNLOAD_STATUS_CHECK_RATE)
        if self.image is not None and not self.cancelled:
            self.pack_forget()
            save.SaveImageFrame(self.root, self, self.image).pack()
        self.reset()
    
    def reset(self) -> None:
        """Resets download state."""
        self.image = None
        self.exception = None
        self.cancelled = False
        self.download_button.config(
            text="Download", **BUTTON_COLOURS, command=self.start_download)
    
    def cancel(self) -> None:
        """Cancels the download."""
        self.cancelled = True
        # Increment download ID so current download will be invalidated.
        # Once the get image function returns the image, nothing occurs.
        # Further errors are also ignored.
        self.download_id += 1


class UrlInput(tk.Frame):
    """Allows the user to input the URL, with immediate validation."""

    def __init__(
        self, master: Union[
            UrlDownload, "batch.UrlToplevel", "rendering.PanoramaInput"]
    ) -> None:
        super().__init__(master)
        self._url = tk.StringVar()
        self._url.trace_add("write", lambda *_: self.validate())
        self.valid = False
        self.previous = ""

        self.label = tk.Label(self, font=inter(20), text="URL:")
        self.entry = tk.Entry(
            self, font=inter(10), width=128, textvariable=self._url)
        self.feedback_label = tk.Label(
            self, font=inter(8), text="Enter a valid URL.", fg=RED)

        self.label.grid(row=0, column=0, padx=10)
        self.entry.grid(row=0, column=1, padx=10)
        self.feedback_label.grid(row=1, column=1, padx=10, sticky="e")
    
    @property
    def url(self) -> str:
        return self._url.get().strip()
        
    def validate(self) -> None:
        """Validates the URL input."""
        url = self.url
        if not url:
            self.valid = False
            self.previous = url
            self.feedback_label.config(text="Enter a valid URL.", fg=RED)
        elif len(url) > MAX_URL_INPUT_LENGTH:
            self._url.set(self.previous)
        else:
            self.previous = url
            try:
                parse_url(url)
                self.valid = True
                self.feedback_label.config(text="Valid URL.", fg=GREEN)
            except ValueError as e:
                self.valid = False
                self.feedback_label.config(text=e, fg=RED)
        if isinstance(self.master, UrlDownload):
            self.master.update_download_button_state()
        elif isinstance(self.master, batch.UrlToplevel):
            self.master.update_submit_button_state()
        else:
            # Rendering screen.
            self.master.master.update_start_button_state()


class DimensionInput(tk.Frame):
    """Input for a single dimension - width or height."""

    def __init__(
        self, master: Union[
            UrlDownload, "widgets.UrlSettingsToplevel",
            "rendering.RenderingInputs"],
        label: str, minimum: int, maximum: int, default: int,
        length: int = 1500, label_width: int = 8, font_size: int = 20
    ) -> None:
        super().__init__(master)
        self.min = minimum
        self.max = maximum
        self._value = tk.IntVar(value=default)
        self._value_str = tk.StringVar(value=str(default))
        self.previous_value_str = str(default)
        self._value.trace_add("write", lambda *_: self.update_value(False))
        self._value_str.trace_add("write", lambda *_: self.update_value(True))

        self.label = tk.Label(
            self, font=inter(font_size), text=label, width=label_width)
        self.scale = tk.Scale(
            self, font=inter(font_size), from_=self.min, to=self.max,
            length=length, width=30, sliderlength=100,
            orient="horizontal", variable=self._value)
        self.entry = tk.Entry(
            self, font=inter(font_size), width=len(str(self.max)),
            textvariable=self._value_str)
        
        self.label.grid(row=0, column=0, padx=5, pady=5)
        self.scale.grid(row=0, column=1, padx=5, pady=5)
        self.entry.grid(row=0, column=2, padx=5, pady=5)
    
    @property
    def value(self) -> int:
        return self._value.get()
    
    def update_value(self, entry_change: bool) -> None:
        """Synchronises the scale and entry, with relevant validation."""
        if not entry_change:
            self._value_str.set(str(self._value.get()))
            self.previous_width = self._value.get()
            return
        entry_str = self._value_str.get()
        if entry_str and (
            len(entry_str) > len(str(self.max)) or not entry_str.isdigit()
        ):
            self._value_str.set(str(self.previous_value_str))
            return
        self.previous_value_str = entry_str
        if not self.min <= int(entry_str or 0) <= self.max:
            return
        self._value.set(int(entry_str))
        if isinstance(self.master, rendering.RenderingInputs):
            # Render - projection size changed.
            self.master.update_display("length", self.value)
