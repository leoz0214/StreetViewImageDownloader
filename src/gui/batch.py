"""Batch downloading of images by panorama ID or URL."""
import asyncio
import csv
import enum
import threading
import time
import timeit
import tkinter as tk
from contextlib import suppress
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from typing import Callable, Union

import main
import panorama_id
import url
import widgets
from _utils import (
    inter, BUTTON_COLOURS, GREEN, RED, get_text_width, bool_to_state,
    format_seconds)
from api.panorama import (
    validate_panorama_id, PanoramaSettings, _get_async_images, _combine_tiles)
from api.url import DEFAULT_WIDTH, DEFAULT_HEIGHT, parse_url, get_pil_image


MIN_TABLE_HEIGHT = 15
MAX_BATCH_SIZE = 1000
PANORAMA_ID_HEADINGS = ("Panorama ID", "File Save Path")
URL_HEADINGS = ("URL", "File Save Path")
DOWNLOAD_STATUS_CHECK_RATE = 0.05
TABLE_FONT = inter(11)


class DownloadMode(enum.Enum):
    """Enum representing the two download modes."""
    panorama_id = "Panorama ID"
    url = "URL"


class BatchDownload(tk.Frame):
    """Batch image downloading functionality."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(f"{main.TITLE} - Batch Download")
        self._stop_upon_error = tk.BooleanVar(value=False)

        self.title = tk.Label(
            self, font=inter(25, True), text="Batch Download")
        self.download_mode_frame = BatchDownloadMode(self)
        self.panorama_id_frame = BatchPanoramaIDDownload(self)
        self.url_frame = BatchUrlDownload(self)
        self.to_display = None
        self.error_handling_checkbutton = tk.Checkbutton(
            self, font=inter(15), text="Stop upon error",
            variable=self._stop_upon_error)
        self.back_button = tk.Button(
            self, font=inter(20), text="Back", width=15,
            **BUTTON_COLOURS, command=self.back)
        self.download_button = tk.Button(
            self, font=inter(20), text="Download", width=15,
            **BUTTON_COLOURS, command=self.download)
        
        self.title.grid(row=0, column=0, columnspan=2, padx=10, pady=5)
        self.download_mode_frame.grid(
            row=1, column=0, columnspan=2, padx=10, pady=5)
        self.display_input_frame()
        self.error_handling_checkbutton.grid(
            row=3, column=0, columnspan=2, padx=10, pady=5)
        self.back_button.grid(row=4, column=0, padx=10, pady=5)
        self.download_button.grid(row=4, column=1, padx=10, pady=5)
    
    @property
    def stop_upon_error(self) -> bool:
        return self._stop_upon_error.get()

    def display_input_frame(self) -> None:
        """Displays the appropriate frame based on download mode selection."""
        if self.download_mode_frame.download_mode == DownloadMode.panorama_id:
            self.to_display = self.panorama_id_frame
            to_hide = self.url_frame
        else:
            self.to_display = self.url_frame
            to_hide = self.panorama_id_frame
        self.to_display.grid(row=2, column=0, columnspan=2, padx=10, pady=5)
        to_hide.grid_forget()
        # Set focus on root window (to unfocus on the treeview).
        # This avoids issues such as arrow keys opening edit windows.
        self.root.focus()
    
    def back(self) -> None:
        """Returns to the main menu."""
        self.destroy()
        main.MainMenu(self.root).pack()
    
    def download(self) -> None:
        """Downloads all the panorama ID/urls as required."""
        stop_upon_error = self.stop_upon_error
        download_mode = self.download_mode_frame.download_mode
        records = self.to_display.table.records
        if not records:
            messagebox.showerror(
                "No input",
                "Please add at least one input before starting the download.")
            return
        if download_mode == DownloadMode.panorama_id:
            panorama_settings = self.to_display.settings
            width = None
            height = None
        else:
            panorama_settings = None
            width = self.to_display.width
            height = self.to_display.height
        BatchDownloadToplevel(
            self, stop_upon_error, download_mode, records,
            panorama_settings, width, height)


class BatchDownloadMode(tk.Frame):
    """Allows the user to select between downloading by panorama ID/URL."""

    def __init__(self, master: BatchDownload) -> None:
        super().__init__(master)
        self._download_mode = tk.IntVar(value=0)
        self._download_mode.trace_add(
            "write", lambda *_: master.display_input_frame())
        self.label = tk.Label(self, font=inter(20), text="Download By:")
        self.label.grid(row=0, column=0, padx=10)

        for value, text in enumerate(("Panorama ID", "URL")):
            radiobutton = tk.Radiobutton(
                self, font=inter(20), text=text, width=15,
                value=value, variable=self._download_mode, indicatoron=False,
                **BUTTON_COLOURS, selectcolor=GREEN)
            radiobutton.grid(row=0, column=value + 1, padx=10)
    
    @property
    def download_mode(self) -> DownloadMode:
        value = self._download_mode.get()
        return (DownloadMode.panorama_id, DownloadMode.url)[value]


class BatchDownloadMaster(tk.Frame):
    """Common frame for panorama ID/URL input and settings frames."""

    def __init__(
        self, master: BatchDownload, headings: tuple[str],
        input_toplevel: tk.Toplevel, settings_toplevel: tk.Toplevel
    ) -> None:
        super().__init__(master)
        self.table = Table(self, headings, (500, 500), self.edit)
        self.info_label = tk.Label(self, font=inter(12))
        self.update_info_label()
        self.buttons = DownloadInputButtons(self)
        self.input_toplevel = input_toplevel
        self.settings_toplevel = settings_toplevel

        self.table.pack(padx=10, pady=5)
        self.info_label.pack(padx=10, pady=5)
        self.buttons.pack(padx=10, pady=5)
    
    def add(self) -> None:
        """Allows the user to add a X, file save path pair."""
        if len(self.table.records) == MAX_BATCH_SIZE:
            messagebox.showerror(
                "Error", f"Maximum batch size of {MAX_BATCH_SIZE} reached.")
            return
        self.input_toplevel(self)
    
    def edit(self) -> None:
        """Updates the currently selected record."""
        if any(
            isinstance(widget, self.input_toplevel) 
            for widget in self.children.values()
        ):
            # Only one instance of the input toplevel at a time.
            return
        with suppress(IndexError):
            index = self.table.selected
            record = self.table.records[index]
            self.input_toplevel(self, index, *record)
    
    def update_info_label(self) -> None:
        """Updates info label including number of records and settings."""
        raise NotImplementedError
    
    def edit_settings(self) -> None:
        """Allows the download settings to be edited."""
        self.settings_toplevel(self, self.master.root)


class BatchPanoramaIDDownload(BatchDownloadMaster):
    """Frame to input panorama IDs to download and save paths."""

    def __init__(self, master: BatchDownload) -> None:
        self.settings = PanoramaSettings()
        super().__init__(
            master, PANORAMA_ID_HEADINGS, PanoramaIDToplevel,
            widgets.PanoramaIDSettingsToplevel)
    
    def update_info_label(self) -> None:
        """Updates info label including number of records and settings."""
        if self.settings.zoom == 0:
            text = " | ".join((
                f"Count: {len(self.table.records)}",
                f"Zoom: {self.settings.zoom}",
                "Entire panoramas will be downloaded."))
        else:
            text = " | ".join((
                f"Count: {len(self.table.records)}",
                f"Zoom: {self.settings.zoom}",
                f"Top left: {self.settings.top_left}",
                f"Bottom right: {self.settings.bottom_right}",
                f"Width: {self.settings.width}",
                f"Height: {self.settings.height}",
                f"Tiles: {self.settings.tiles}"))
        self.info_label.config(text=text)


class DownloadInputButtons(tk.Frame):
    """
    Relevant buttons for CSV importing/exporting,
    adding inputs and adjusting settings.
    """

    def __init__(
        self, master: Union[BatchPanoramaIDDownload, "BatchUrlDownload"]
    ) -> None:
        super().__init__(master)
        for column, (text, command) in enumerate(
            (
                ("Import CSV", self.import_csv), ("Add", master.add),
                ("Settings", master.edit_settings),
                ("Export CSV", self.export_csv))
        ):
            button = tk.Button(
                self, font=inter(15), text=text, width=15,
                **BUTTON_COLOURS, command=command)
            button.grid(row=0, column=column, padx=5)

    def import_csv(self) -> None:
        """Imports a CSV file as input (first two columns only)."""
        try:
            file_path = filedialog.askopenfilename(
                defaultextension=".csv", filetypes=(("CSV", ".csv"),),
                title="Import CSV")
            if not file_path:
                return
            records = []
            seen_file_paths = set()
            with open(file_path, "r", encoding="utf8") as f:
                # Attempt to detect delimiter out of a common bunch.
                dialect = csv.Sniffer().sniff(f.read(1024), delimiters=";,| ")
                f.seek(0)
                reader = csv.reader(f, dialect)
                for i, record in enumerate(reader):
                    try:
                        value, file_path, *_ = record
                        if isinstance(self.master, BatchPanoramaIDDownload):
                            validate_panorama_id(value)
                        else:
                            # URL import.
                            parse_url(value)
                        if file_path.lower() in seen_file_paths:
                            raise RuntimeError(
                                "Same file path input multiple times.")
                        seen_file_paths.add(file_path.lower())
                        records.append((value, file_path))
                        if len(records) > MAX_BATCH_SIZE:
                            raise RuntimeError(
                                "Maximum batch size of "
                                f"{MAX_BATCH_SIZE} exceeded")
                    except RuntimeError as e:
                        raise e
                    except Exception as e:
                        if i == 0 or all(not value for value in record):
                            # Ignore first row if invalid (assume headings).
                            # Also ignore entirely empty row.
                            continue
                        if isinstance(self.master, BatchPanoramaIDDownload):
                            field = "panorama ID"
                        else:
                            field = "URL"
                        raise RuntimeError(
                            f"Invalid {field} or file save path found. "
                            "Please check all inputs are valid.")
            table = self.master.table
            if table.records and not messagebox.askyesnocancel(
                "Confirm",
                    "Are you sure you would like to import the CSV?\n"
                    "The current input will be overwritten."
            ):
                return
            table.text_widths = [
                [get_text_width(f"{text} ", TABLE_FONT) for text in record]
                for record in records]
            table.records = records
            table.create_treeview()
            for record in table.records:
                table.treeview.insert("", "end", values=record)
            self.master.update_info_label()
        except Exception as e:
            messagebox.showerror(
                "Error", f"Unfortunately, an error has occurred: {e}")

    def export_csv(self) -> None:
        """Exports a CSV file based on the current input."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=(("CSV", ".csv"),),
            title="Export CSV")
        if not file_path:
            return
        with open(file_path, "w", encoding="utf8") as f:
            writer = csv.writer(f, lineterminator="\n")
            if isinstance(self.master, BatchPanoramaIDDownload):   
                writer.writerow(PANORAMA_ID_HEADINGS)
            else:
                writer.writerow(URL_HEADINGS)
            writer.writerows(self.master.table.records)


class Table(tk.Frame):
    """
    Treeview table in a Canvas such that the
    horizontal and vertical scrollbars can be applied.
    """

    def __init__(
        self, master: tk.Frame, headings: tuple[str], min_widths: tuple[int],
        select_command: Callable = None
    ) -> None:
        super().__init__(master)
        self.headings = headings
        self.min_widths = min_widths
        self.text_widths = []
        self.records = []
        self.select_command = select_command

        self.canvas = tk.Canvas(self, width=sum(min_widths), height=490)
        style = ttk.Style()
        style.configure("Treeview.Heading", font=inter(15))
        style.configure("Treeview", font=TABLE_FONT, rowheight=30)

        self.horizontal_scrollbar = tk.Scrollbar(
            self, orient="horizontal", command=self.canvas.xview)
        self.vertical_scrollbar = tk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview)

        self.treeview = None
        self.treeview_window = None
        self.create_treeview()

        self.canvas.grid(row=0, column=0)
    
    @property
    def selected(self) -> int:
        return self.treeview.index(self.treeview.selection()[0])
    
    def create_treeview(self, records: list = None) -> None:
        """Sets up the treeview widget."""
        if self.treeview_window is not None:
            self.canvas.delete(self.treeview_window)
        self.treeview = ttk.Treeview(
            self.canvas, columns=self.headings, show="headings",
            height=max(len(self.records), MIN_TABLE_HEIGHT))
        for heading, width in zip(self.headings, self.get_column_widths()):
            self.treeview.heading(heading, text=heading)
            self.treeview.column(heading, width=width)
        if self.select_command is not None:
            self.treeview.bind(
                "<<TreeviewSelect>>", lambda *_: self.select_command())
        if records is not None:
            for record in records:
                self.treeview.insert("", "end", values=record)

        self.treeview_window = self.canvas.create_window(
            0, 0, anchor="nw", window=self.treeview)
        self.update_scrollbars()
    
    def update_scrollbars(self) -> None:
        """
        Displays or hides the horizontal and vertical scrollbars
        depending on their need.
        """
        height = self.treeview.cget("height")
        vertical = height > MIN_TABLE_HEIGHT
        horizontal = any(
            self.treeview.column(heading, "width") > min_width
            for heading, min_width in zip(self.headings, self.min_widths))
        if vertical:
            self.canvas.config(yscrollcommand=self.vertical_scrollbar.set)
            self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        else:
            self.canvas.config(yscrollcommand=None)
            self.vertical_scrollbar.grid_forget()
        if horizontal:
            self.canvas.config(xscrollcommand=self.horizontal_scrollbar.set)
            self.horizontal_scrollbar.grid(row=1, column=0, sticky="we")
        else:
            self.canvas.config(xscrollcommand=None)
            self.horizontal_scrollbar.grid_forget()
        self.master.master.root.update()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
    
    def append(self, record: tuple) -> None:
        """Appends a record to the table."""
        previous_column_widths = self.get_column_widths()
        widths = [get_text_width(text + " ", inter(11)) for text in record]
        self.text_widths.append(widths)
        self.records.append(record)
        new_column_widths = self.get_column_widths()
        if previous_column_widths == new_column_widths:
            self.treeview.insert("", "end", values=record)
            self.treeview.config(
                height=max(len(self.records), MIN_TABLE_HEIGHT))
            self.update_scrollbars()
            return
        self.create_treeview(self.records)
        
    def edit(self, index: int, record: tuple) -> None:
        """Updates a given record."""
        previous_column_widths = self.get_column_widths()
        widths = [get_text_width(f"{text} ", TABLE_FONT) for text in record]
        self.text_widths[index] = widths
        self.records[index] = record
        new_column_widths = self.get_column_widths()
        if previous_column_widths == new_column_widths:
            self.treeview.delete(self.treeview.get_children()[index])
            self.treeview.insert("", index, values=record)
            self.update_scrollbars()
            return
        self.create_treeview(self.records)
    
    def pop(self, index: int) -> None:
        """Deletes the record at the given index."""
        previous_column_widths = self.get_column_widths()
        self.text_widths.pop(index)
        self.records.pop(index)
        new_column_widths = self.get_column_widths()
        if previous_column_widths == new_column_widths:
            self.treeview.delete(self.treeview.get_children()[index])
            self.treeview.config(
                height=max(len(self.records), MIN_TABLE_HEIGHT))
            self.update_scrollbars()
            return
        self.create_treeview(self.records)

    def get_column_widths(self) -> list[int]:
        """Return required width for each column."""
        if not self.text_widths:
            return list(self.min_widths)
        return [
            max(min_width, max(width[i] for width in self.text_widths))
            for i, min_width in enumerate(self.min_widths)]


class InputToplevel(tk.Toplevel):
    """Master toplevel for panorama ID/URL and file path input."""

    def __init__(
        self, master: tk.Frame, field: str,
        input_frame: panorama_id.PanoramaIDInput | url.UrlInput,
        input_frame_variable: str, input_frame_property: str,
        index: int, value: str, file_path: str
    ) -> None:
        super().__init__(master)
        self.index = index
        self.keyword = "Edit" if self.index is not None else "Add"
        self.field = field
        self.property = input_frame_property
        self.title(
            f"{main.TITLE} - Batch Download - {self.keyword} {self.field}")
        self.grab_set()

        self.title_label = tk.Label(
            self, font=inter(25, True), text=f"{self.keyword} {self.field}")
        self.input_frame = input_frame(self)
        self.file_input = FileInput(self)
        
        self.bind("<Control-o>", lambda *_: self.file_input.select())

        self.submit_button = tk.Button(
            self, font=inter(20), text=self.keyword, width=15,
            **BUTTON_COLOURS, command=self.submit)

        if self.index is not None:
            getattr(self.input_frame, input_frame_variable).set(value)
            self.file_input._file_path.set(file_path)
            self.delete_button = tk.Button(
                self, font=inter(20), text="Delete", width=15,
                **BUTTON_COLOURS, command=self.delete)
        self.update_submit_button_state()
    
        self.title_label.pack(padx=10, pady=10)
        self.input_frame.pack(padx=10, pady=10)
        self.file_input.pack(padx=10, pady=10)
        self.submit_button.pack(padx=10, pady=10)
        if self.index is not None:
            self.delete_button.pack(padx=10, pady=10)
    
    def update_submit_button_state(self):
        """
        Enables the submit button if the
        input is valid and a file has been provided.
        """
        self.submit_button.config(
            state=bool_to_state(
                self.input_frame.valid and self.file_input.file_path))

    def submit(self) -> None:
        """Submits the input and adds/edits as required."""
        value = getattr(self.input_frame, self.property)
        file_path = self.file_input.file_path
        if any(
            i != self.index and file_path.lower() == existing_file_path.lower()
            for i, (_, existing_file_path) in enumerate(
                self.master.table.records)
        ):
            messagebox.showerror(
                "Error",
                    "The file path provided has already been "
                    "set for another record.", parent=self)
            return
        record = (value, file_path)
        if self.index is None:
            self.master.table.append(record)
        else:
            self.master.table.edit(self.index, record)
        self.destroy()

    def delete(self) -> None:
        """Deletes the record."""
        self.master.table.pop(self.index)
        self.destroy()
    
    def destroy(self) -> None:
        """Destroys the toplevel and updates information."""
        super().destroy()
        self.master.update_info_label()


class PanoramaIDToplevel(InputToplevel):
    """Window to allow the user to add/edit/delete a panorama ID."""

    def __init__(
        self, master: BatchPanoramaIDDownload,
        index: int = None, _panorama_id: str = None, file_path: str = None
    ) -> None:
        super().__init__(
            master, "Panorama ID", panorama_id.PanoramaIDInput,
            "_panorama_id", "panorama_id", index, _panorama_id, file_path)


class FileInput(tk.Frame):
    """File path input including a button to set file and a display."""

    def __init__(self, master: InputToplevel) -> None:
        super().__init__(master)
        self._file_path = tk.StringVar()

        self.label = tk.Label(self, font=inter(20), text="File Path:")
        self.display = tk.Entry(
            self, font=inter(10), width=64,
            textvariable=self._file_path, state="readonly")
        self.button = tk.Button(
            self, font=inter(20), text="Select", width=15,
            **BUTTON_COLOURS, command=self.select)

        self.label.grid(row=0, column=0, padx=5, pady=5)
        self.display.grid(row=0, column=1, padx=5, pady=5)
        self.button.grid(row=0, column=2, padx=5, pady=5)
    
    @property
    def file_path(self) -> str:
        return self._file_path.get()
    
    def select(self) -> None:
        """Selects a file using the file dialog."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".jpg", filetypes=(("JPG", ".jpg"),),
            title="Select File")
        if not file_path:
            return
        self._file_path.set(file_path)
        self.master.update_submit_button_state()


class BatchUrlDownload(BatchDownloadMaster):
    """Allows Google Street View URLs to be downloaded en masse."""

    def __init__(self, master: BatchDownload) -> None:
        self.width = DEFAULT_WIDTH
        self.height = DEFAULT_HEIGHT
        super().__init__(
            master, URL_HEADINGS, UrlToplevel, widgets.UrlSettingsToplevel)

    def update_info_label(self) -> None:
        """Updates information, including URL count, width and height."""
        text = " | ".join((
            f"Count: {len(self.table.records)}",
            f"Dimension: {self.width} x {self.height}"))
        self.info_label.config(text=text)


class UrlToplevel(InputToplevel):
    """Window to allow the user to add/edit/delete a URL."""

    def __init__(
        self, master: BatchUrlDownload,
        index: int = None, _url: str = None, file_path: str = None
    ) -> None:
        super().__init__(
            master, "URL", url.UrlInput, "_url", "url", index, _url, file_path)


class BatchDownloadToplevel(tk.Toplevel):
    """
    Toplevel where the batch downloading occurs
    when the user clicks on the download button.
    """

    def __init__(
        self, master: BatchDownload, stop_upon_error: bool,
        mode: DownloadMode, records: list[tuple],
        panorama_settings: panorama_id.PanoramaSettings = None,
        width: int = None, height: int = None
    ) -> None:
        super().__init__(master)
        self.stop_upon_error = stop_upon_error
        self.mode = mode
        self.records = records
        self.panorama_settings = panorama_settings
        self.url_width = width
        self.url_height = height
        self.done = 0
        self.cancelled = False
        self.image = None
        self.exception = None
        if self.mode == DownloadMode.panorama_id:
            self.tiles = [
                [None] * self.panorama_settings.width
                for _ in range(self.panorama_settings.height)]

        self.title(
            f"{main.TITLE} - Batch Download - "
            f"Downloading {self.mode.value}s...")
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.title_label = tk.Label(
            self, font=inter(25, True),
            text=f"Downloading {self.mode.value}s...")
        self.progress_bar = ttk.Progressbar(
            self, length=1000, maximum=len(self.records),
            orient="horizontal")
        self.progress_label = tk.Label(self, font=inter(12))
        self.update_progress()
        self.logger = widgets.Logger(self, width=64, height=25)
        self.cancel_button = tk.Button(
            self, font=inter(20), text="Cancel", width=15,
            bg=RED, activebackground=RED, command=self.cancel)

        threading.Thread(target=self.download, daemon=True).start()

        self.title_label.pack(padx=10, pady=10)
        self.progress_bar.pack(padx=25, pady=10)
        self.progress_label.pack(padx=10, pady=10)
        self.logger.pack(padx=10, pady=10)
        self.cancel_button.pack(padx=10, pady=10)
    
    def update_progress(self) -> None:
        """Updates the progress bar and label."""
        percentage = round(self.done / len(self.records) * 100, 1)
        self.progress_bar.config(value=self.done)
        text = " | ".join((
            f"Downloaded: {self.done} / {len(self.records)}",
            f"Progress: {percentage}%"))
        self.progress_label.config(text=text)

    def _process_panorama_download(self, panorama_id: str) -> None:
        try:
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(_get_async_images(
                self.tiles, panorama_id, self.panorama_settings, self))
            image = _combine_tiles(self.tiles, True, self)
            if self.cancelled:
                raise RuntimeError
            if image.size == (0, 0):
                raise RuntimeError("No panorama data.")
            self.image = image
        except Exception as e:
            self.exception = e
        
    def _process_url_download(self, url: str) -> None:
        try:
            image = get_pil_image(url, self.url_width, self.url_height)
            if self.cancelled:
                raise RuntimeError
            self.image = image
        except Exception as e:
            self.exception = e
    
    def download(self) -> None:
        """Sequentially downloads and saves each input."""
        start = timeit.default_timer()
        for i, (value, file_path) in enumerate(self.records, 1):
            if self.cancelled:
                return
            self.logger.log_neutral(f"{i}. {value}")
            if self.mode == DownloadMode.panorama_id:
                target = lambda: self._process_panorama_download(value)
            else:
                target = lambda: self._process_url_download(value)
            threading.Thread(target=target, daemon=True).start()
            while True:
                if self.cancelled:
                    return
                if self.exception is not None:
                    self.logger.log_bad(f"Download Error: {self.exception}")
                    if self.stop_upon_error:
                        self.logger.log_bad("Downloading terminated.")
                        self.cancel_button.config(
                            text="Close", **BUTTON_COLOURS)
                        return
                    self.exception = None
                    break
                if self.image is not None:
                    break
                time.sleep(DOWNLOAD_STATUS_CHECK_RATE)
            if self.image is None:
                continue
            try:
                self.image.save(file_path, format="jpeg")
            except Exception as e:
                self.logger.log_bad(f"Save Error: {e}")
                if self.stop_upon_error:
                    self.logger.log_bad("Downloading terminated.")
                    return
            else:
                self.logger.log_good(
                    f"Successfully saved image to {file_path}")
                self.done += 1
                self.update_progress()
            self.image = None
        stop = timeit.default_timer()
        time_taken = format_seconds(stop - start)
        self.logger.log_good(f"Downloading completed in {time_taken}")
        self.cancel_button.config(
            text="Close", bg=GREEN, activebackground=GREEN)
    
    def cancel(self) -> None:
        """Cancels the bulk download."""
        self.cancelled = True
        self.destroy()
