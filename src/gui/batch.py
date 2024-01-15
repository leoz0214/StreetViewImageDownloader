"""Batch downloading of images by panorama ID or URL."""
import csv
import enum
import tkinter as tk
from contextlib import suppress
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from typing import Callable

import main
import panorama_id
from _utils import inter, BUTTON_COLOURS, GREEN, get_text_width, bool_to_state
from api.panorama import validate_panorama_id, PanoramaSettings


MIN_TABLE_HEIGHT = 15
MAX_BATCH_SIZE = 1000
PANORAMA_ID_HEADINGS = ("Panorama ID", "File Save Path")
URL_HEADINGS = ("URL", "File Save Path")


class DownloadMode(enum.Enum):
    """Enum representing the two download modes."""
    panorama_id = 0
    url = 1


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
            to_display = self.panorama_id_frame
            to_hide = self.url_frame
        else:
            to_display = self.url_frame
            to_hide = self.panorama_id_frame
        to_display.grid(row=2, column=0, columnspan=2, padx=10, pady=5)
        to_hide.grid_forget()
    
    def back(self) -> None:
        """Returns to the main menu."""
        self.destroy()
        main.MainMenu(self.root).pack()
    
    def download(self) -> None:
        """Downloads all the panorama ID/urls as required."""
        # TODO


class BatchDownloadMode(tk.Frame):
    """Allows the user to select between downloading by panorama ID/URL."""

    def __init__(self, master: BatchDownload) -> None:
        super().__init__(master)
        self._download_mode = tk.IntVar(value=0)
        self._download_mode.trace_add(
            "write", lambda *_: master.display_input_frame())
        self.label = tk.Label(self, font=inter(20), text="Download By:")
        self.by_panorama_id = tk.Radiobutton(
            self, font=inter(20), text="Panorama ID", width=15,
            value=0, variable=self._download_mode, indicatoron=False,
            **BUTTON_COLOURS, selectcolor=GREEN)
        self.by_url = tk.Radiobutton(
            self, font=inter(20), text="URL", width=15,
            value=1, variable=self._download_mode, indicatoron=False,
            **BUTTON_COLOURS, selectcolor=GREEN)
        
        self.label.grid(row=0, column=0, padx=10)
        self.by_panorama_id.grid(row=0, column=1, padx=10)
        self.by_url.grid(row=0, column=2, padx=10)
    
    @property
    def download_mode(self) -> DownloadMode:
        return (
            DownloadMode.panorama_id, DownloadMode.url
        )[self._download_mode.get()]


class BatchPanoramaIDDownload(tk.Frame):
    """Frame to input panorama IDs to download and save paths."""

    def __init__(self, master: BatchDownload) -> None:
        super().__init__(master)
        self.table = Table(self, PANORAMA_ID_HEADINGS, (500, 500), self.edit)
        self.settings = PanoramaSettings()
        self.info_label = tk.Label(self, font=inter(12))
        self.update_info_label()
        self.import_csv_button = tk.Button(
            self, font=inter(15), text="Import CSV", width=15,
            **BUTTON_COLOURS, command=self.import_csv)
        self.add_button = tk.Button(
            self, font=inter(15), text="Add", width=15,
            **BUTTON_COLOURS, command=self.add)
        self.settings_button = tk.Button(
            self, font=inter(15), text="Settings", width=15,
            **BUTTON_COLOURS, command=self.edit_settings)
        self.export_csv_button = tk.Button(
            self, font=inter(15), text="Export CSV", width=15,
            **BUTTON_COLOURS, command=self.export_csv)

        self.table.grid(row=0, column=0, columnspan=4, padx=10, pady=5)
        self.info_label.grid(row=1, column=0, columnspan=4, padx=10, pady=5)
        self.import_csv_button.grid(row=2, column=0, padx=5, pady=5)
        self.add_button.grid(row=2, column=1, padx=5, pady=5)
        self.settings_button.grid(row=2, column=2, padx=5, pady=5)
        self.export_csv_button.grid(row=2, column=3, padx=5, pady=5)
    
    def add(self) -> None:
        """Allows the user to add a panorama ID, file save path pair."""
        if len(self.table.records) == MAX_BATCH_SIZE:
            messagebox.showerror(
                "Error",
                    f"Maximum batch size of {MAX_BATCH_SIZE} reached.")
            return
        PanoramaIDToplevel(self)
    
    def edit(self) -> None:
        """Updates the currently selected record."""
        with suppress(IndexError):
            index = self.table.selected
            record = self.table.records[index]
            PanoramaIDToplevel(self, index, *record)
    
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
    
    def import_csv(self) -> None:
        """Imports a CSV file as input (first two columns only)."""
        try:
            file_path = filedialog.askopenfilename(
                defaultextension=".csv", filetypes=(("CSV", ".csv"),))
            if not file_path:
                return
            records = []
            seen_file_paths = set()
            with open(file_path, "r", encoding="utf8") as f:
                dialect = csv.Sniffer().sniff(f.read(1024), delimiters=";,| ")
                f.seek(0)
                reader = csv.reader(f, dialect)
                for i, record in enumerate(reader):
                    try:
                        panorama_id, file_path, *_ = record
                        validate_panorama_id(panorama_id)
                        if file_path.lower() in seen_file_paths:
                            raise RuntimeError(
                                "Same file path input multiple times.")
                        seen_file_paths.add(file_path.lower())
                        records.append((panorama_id, file_path))
                        if len(records) > MAX_BATCH_SIZE:
                            raise RuntimeError(
                                "Maximum batch size of "
                                f"{MAX_BATCH_SIZE} exceeded")
                    except RuntimeError as e:
                        raise e
                    except Exception as e:
                        if i == 0:
                            # Ignore first row if invalid (assume headings).
                            continue
                        raise RuntimeError(
                            "Invalid panorama ID or file save path found. "
                            "Please check all inputs are valid.")
            if self.table.records and not messagebox.askyesnocancel(
                "Confirm",
                    "Are you sure you would like to import the CSV?\n"
                    "The current input will be overwritten."
            ):
                return
            self.table.text_widths = [
                [get_text_width(text + " ", inter(11)) for text in record]
                for record in records]
            self.table.records = records
            self.table.create_treeview()
            for record in self.table.records:
                self.table.treeview.insert("", "end", values=record)
            self.update_info_label()
        except Exception as e:
            messagebox.showerror(
                "Error", f"Unfortunately, an error has occurred: {e}")
    
    def export_csv(self) -> None:
        """Exports a CSV file based on the current input."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=(("CSV", ".csv"),))
        if not file_path:
            return
        with open(file_path, "w", encoding="utf8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(PANORAMA_ID_HEADINGS)
            writer.writerows(self.table.records)
    
    def edit_settings(self) -> None:
        """Allows the panorama download settings to be edited."""
        PanoramaIDSettingsToplevel(self)


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
        self.horizontal_scrollbar = tk.Scrollbar(
            self, orient="horizontal", command=self.canvas.xview)
        self.vertical_scrollbar = tk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview)
        style = ttk.Style()
        style.configure("Treeview.Heading", font=inter(15))
        style.configure("Treeview", font=inter(11), rowheight=30)

        self.treeview = None
        self.treeview_window = None
        self.create_treeview()
    
        self.canvas.config(
            xscrollcommand=self.horizontal_scrollbar.set,
            yscrollcommand=self.vertical_scrollbar.set)

        self.canvas.grid(row=0, column=0)
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="we")
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
    
    @property
    def selected(self) -> int:
        return self.treeview.index(self.treeview.selection()[0])
    
    def create_treeview(self) -> None:
        """Sets up the treeview widget."""
        if self.treeview_window is not None:
            self.canvas.delete(self.treeview_window)
        self.treeview = ttk.Treeview(
            self.canvas, columns=self.headings, show="headings",
            height=max(len(self.text_widths), MIN_TABLE_HEIGHT))
        for heading, min_width in zip(self.headings, self.get_column_widths()):
            self.treeview.heading(heading, text=heading)
            self.treeview.column(heading, width=min_width)
        if self.select_command is not None:
            self.treeview.bind(
                "<<TreeviewSelect>>", lambda *_: self.select_command())

        self.treeview_window = self.canvas.create_window(
            0, 0, anchor="nw", window=self.treeview)
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
            return
        self.create_treeview()
        for record in self.records:
            self.treeview.insert("", "end", values=record)
        
    def edit(self, index: int, record: tuple) -> None:
        """Updates a given record."""
        previous_column_widths = self.get_column_widths()
        widths = [get_text_width(text + " ", inter(11)) for text in record]
        self.text_widths[index] = widths
        self.records[index] = record
        new_column_widths = self.get_column_widths()
        if previous_column_widths == new_column_widths:
            self.treeview.delete(self.treeview.selection())
            self.treeview.insert("", index, values=record)
            return
        self.create_treeview()
        for record in self.records:
            self.treeview.insert("", "end", values=record)
    
    def pop(self, index: int) -> None:
        """Deletes the record at the given index."""
        previous_column_widths = self.get_column_widths()
        self.text_widths.pop(index)
        self.records.pop(index)
        new_column_widths = self.get_column_widths()
        if previous_column_widths == new_column_widths:
            self.treeview.delete(self.treeview.selection())
            return
        self.create_treeview()
        for record in self.records:
            self.treeview.insert("", "end", values=record)

    def get_column_widths(self) -> list[int]:
        """Return required width for each column."""
        widths = []
        for i, min_width in enumerate(self.min_widths):
            if not self.text_widths:
                widths.append(min_width)
                continue
            width = max(
                min_width, max(width[i] for width in self.text_widths))
            widths.append(width)
        return widths


class PanoramaIDToplevel(tk.Toplevel):
    """Window to allow the user to add/edit/delete a panorama ID."""

    def __init__(
        self, master: BatchPanoramaIDDownload,
        index: int = None, _panorama_id: str = None, file_path: str = None
    ) -> None:
        super().__init__(master)
        self.index = index
        self.keyword = "Edit" if self.index is not None else "Add"
        self.title(
            f"{main.TITLE} - Batch Download - {self.keyword} Panorama ID")
        self.grab_set()

        self.title_label = tk.Label(
            self, font=inter(25, True), text=f"{self.keyword} Panorama ID")
        self.panorama_id_input = panorama_id.PanoramaIDInput(self)
        self.file_input = FileInput(self)
        
        self.bind("<Control-o>", lambda *_: self.file_input.select())

        self.submit_button = tk.Button(
            self, font=inter(20), text=self.keyword, width=15,
            **BUTTON_COLOURS, command=self.submit)

        if self.index is not None:
            self.panorama_id_input._panorama_id.set(_panorama_id)
            self.file_input._file_path.set(file_path)
            self.delete_button = tk.Button(
                self, font=inter(20), text="Delete", width=15,
                **BUTTON_COLOURS, command=self.delete)
        self.update_submit_button_state()
    
        self.title_label.pack(padx=10, pady=10)
        self.panorama_id_input.pack(padx=10, pady=10)
        self.file_input.pack(padx=10, pady=10)
        self.submit_button.pack(padx=10, pady=10)
        if self.index is not None:
            self.delete_button.pack(padx=10, pady=10)
    
    def update_submit_button_state(self):
        """
        Enables the submit button if the
        panorama ID input is valid and a file has been provided.
        """
        self.submit_button.config(
            state=bool_to_state(
                self.panorama_id_input.valid and self.file_input.file_path))

    def submit(self) -> None:
        """Submits the input and adds/edits as required."""
        panorama_id = self.panorama_id_input.panorama_id
        file_path = self.file_input.file_path
        if any(
            i != self.index and file_path.lower() == existing_file_path.lower()
            for i, (_, existing_file_path) in enumerate(
                self.master.table.records)
        ):
            messagebox.showerror(
                "Error",
                    "The file path provided has already been "
                    "set for another panorama ID.", parent=self)
            return
        record = (panorama_id, file_path)
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


class FileInput(tk.Frame):
    """File path input including a button to set file and a display."""

    def __init__(self, master: tk.Frame) -> None:
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
            defaultextension=".jpg", filetypes=(("JPG", ".jpg"),))
        if not file_path:
            return
        self._file_path.set(file_path)
        if isinstance(self.master, PanoramaIDToplevel):
            self.master.update_submit_button_state()


class PanoramaIDSettingsToplevel(tk.Toplevel):
    """Toplevel for editing batch panorama ID download settings."""

    def __init__(self, master: BatchPanoramaIDDownload) -> None:
        super().__init__(master)
        self.title(
            f"{main.TITLE} - Batch Download - Panorama Download Settings")
        self.grab_set()
        settings = master.settings

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
        self.master.settings = settings
        self.master.update_info_label()
        self.destroy()


class BatchUrlDownload(tk.Frame):
    """Allows Google Street View URLs to be downloaded en masse."""

    def __init__(self, master: BatchDownload) -> None:
        super().__init__(master)
        self.table = Table(self, URL_HEADINGS, (500, 500), self.edit)

        self.table.pack()
    
    def edit(self) -> None:
        """Allows a URL/file path pair to be edited."""