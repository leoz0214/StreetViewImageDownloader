"""Main module of the GUI feature."""
import tkinter as tk

import __init__
import panorama_id
from _utils import inter, BUTTON_COLOURS


TITLE = "Street View Image Downloader"


class MainMenu(tk.Frame):
    """Street View Image Downloader GUI implementation."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(TITLE)

        self.title = tk.Label(
            self, font=inter(40, True), text="Street View Image Downloader")
        self.panorama_id_button = tk.Button(
            self, font=inter(20),
            text="By Panorama ID", width=20, **BUTTON_COLOURS,
            command=self.panorama_id)
        self.url_button = tk.Button(
            self, font=inter(20), 
            text="By URL", width=20, **BUTTON_COLOURS)
        self.batch_button = tk.Button(
            self, font=inter(20), 
            text="Batch", width=20, **BUTTON_COLOURS)
        self.view_panorama_button = tk.Button(
            self, font=inter(20),
            text="Panorama Rendering", width=20, **BUTTON_COLOURS)
        
        self.title.pack(padx=10, pady=10)
        self.panorama_id_button.pack(pady=5)
        self.url_button.pack(pady=5)
        self.batch_button.pack(pady=5)
        self.view_panorama_button.pack(pady=5)
    
    def panorama_id(self) -> None:
        """Proceeds to downloading panoramas by ID."""
        self.destroy()
        panorama_id.PanoramaDownload(self.root).pack()


def main() -> None:
    root = tk.Tk()
    main_menu = MainMenu(root)
    main_menu.pack()
    root.mainloop()


if __name__ == "__main__":
    main()
