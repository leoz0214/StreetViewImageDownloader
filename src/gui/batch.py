"""Batch downloading of images by panorama ID or URL."""
import enum
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog
from tkinter import ttk

import main
import panorama_id
from _utils import inter, BUTTON_COLOURS, GREEN, get_text_width, bool_to_state


class DownloadMode(enum.Enum):
    """Enum representing the two download modes."""
    panorama_id = 0
    url = 1


@dataclass
class PanoramaID:
    """Panorama ID, file save path pair."""
    panorama_id: str
    file_path: str


class BatchDownload(tk.Frame):
    """Batch image downloading functionality."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(f"{main.TITLE} - Batch Download")

        self.title = tk.Label(
            self, font=inter(25, True), text="Batch Download")
        self.download_mode_frame = BatchDownloadMode(self)
        self.panorama_id_frame = BatchPanoramaIDDownload(self)
        self.back_button = tk.Button(
            self, font=inter(20), text="Back", width=15,
            **BUTTON_COLOURS, command=self.back)
        self.download_button = tk.Button(
            self, font=inter(20), text="Download", width=15,
            **BUTTON_COLOURS, command=self.download)
        
        self.title.grid(row=0, column=0, columnspan=2, padx=10, pady=5)
        self.download_mode_frame.grid(
            row=1, column=0, columnspan=2, padx=10, pady=5)
        self.panorama_id_frame.grid(
            row=2, column=0, columnspan=2, padx=10, pady=5)
        self.back_button.grid(row=3, column=0, padx=10, pady=5)
        self.download_button.grid(row=3, column=1, padx=10, pady=5)
    
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
        self.table = Table(
            self, ("Panorama ID", "File Save Path"), (500, 500))
        self.records = []
        self.add_button = tk.Button(
            self, font=inter(15), text="Add", width=15,
            **BUTTON_COLOURS, command=self.add)

        self.table.pack()
        self.add_button.pack()
    
    def add(self) -> None:
        """Allows the user to add a panorama ID, file save path pair."""
        PanoramaIDToplevel(self)


class Table(tk.Frame):
    """
    Treeview table in a Canvas such that the
    horizontal and vertical scrollbars can be applied.
    """

    def __init__(
        self, master: tk.Frame, headings: tuple[str], min_widths: tuple[int]
    ) -> None:
        super().__init__(master)
        self.headings = headings
        self.min_widths = min_widths
        self.canvas = tk.Canvas(self, width=sum(min_widths), height=500)
        self.horizontal_scrollbar = tk.Scrollbar(
            self, orient="horizontal", command=self.canvas.xview)
        self.vertical_scrollbar = tk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview)
        style = ttk.Style()
        style.configure("Treeview.Heading", font=inter(15))
        style.configure("Treeview", font=inter(11), rowheight=30)
        self.treeview = ttk.Treeview(
            self.canvas, columns=self.headings, show="headings", height=0)
        for heading, min_width in zip(self.headings, self.min_widths):
            self.treeview.heading(heading, text=heading)
            self.treeview.column(heading, width=min_width)

        self.canvas.create_window(0, 0, anchor="nw", window=self.treeview)
        self.master.master.root.update()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.canvas.config(
            xscrollcommand=self.horizontal_scrollbar.set,
            yscrollcommand=self.vertical_scrollbar.set)

        self.canvas.grid(row=0, column=0)
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="we")
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
    
    def append(self, record: tuple) -> None:
        """Appends a record to the table."""
        self.treeview.config(height=self.treeview.cget("height") + 1)
        self.treeview.insert("", "end", values=record)
        self.master.master.root.update()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))


class PanoramaIDToplevel(tk.Toplevel):
    """Window to allow the user to add/edit/delete a panorama ID."""

    def __init__(self, master: BatchPanoramaIDDownload) -> None:
        super().__init__(master)
        self.title(f"{main.TITLE} - Batch Download - Add Panorama ID")
        self.grab_set()

        self.title_label = tk.Label(
            self, font=inter(25, True), text="Add Panorama ID")
        self.panorama_id_input = panorama_id.PanoramaIDInput(self)
        self.file_input = FileInput(self)
        self.bind("<Control-o>", lambda *_: self.file_input.select())

        self.submit_button = tk.Button(
            self, font=inter(20), text="Add", width=15,
            **BUTTON_COLOURS, command=self.submit, state="disabled")
    
        self.title_label.pack(padx=10, pady=10)
        self.panorama_id_input.pack(padx=10, pady=10)
        self.file_input.pack(padx=10, pady=10)
        self.submit_button.pack(padx=10, pady=10)
    
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
        record = (panorama_id, file_path)
        self.master.table.append(record)
        self.master.records.append(PanoramaID(panorama_id, file_path))
        self.destroy()


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