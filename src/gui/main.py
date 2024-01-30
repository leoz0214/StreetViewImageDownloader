"""Main module of the GUI app."""
import tkinter as tk

import __init__
import batch
import live
import panorama_id
import rendering
import url
from _utils import inter, BUTTON_COLOURS

TITLE = "Street View Image Downloader"


class MainMenu(tk.Frame):
    """Street View Image Downloader GUI implementation."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(TITLE)
        self.menu = Menu(self)
        self.root.config(menu=self.menu)

        self.title = tk.Label(
            self, font=inter(40, True), text="Street View Image Downloader")
        self.panorama_id_button = tk.Button(
            self, font=inter(20), text="By Panorama ID", width=20,
            **BUTTON_COLOURS, command=self.panorama_id)
        self.url_button = tk.Button(
            self, font=inter(20), text="By URL", width=20,
            **BUTTON_COLOURS, command=self.url)
        self.batch_button = tk.Button(
            self, font=inter(20), text="Batch", width=20,
            **BUTTON_COLOURS, command=self.batch)
        self.panorama_rendering_button = tk.Button(
            self, font=inter(20), text="Panorama Rendering", width=20,
            **BUTTON_COLOURS, command=self.panorama_rendering)
        self.live_button = tk.Button(
            self, font=inter(20), text="Live", width=20,
            **BUTTON_COLOURS, command=self.live)
        
        self.title.pack(padx=10, pady=10)
        self.panorama_id_button.pack(pady=5)
        self.url_button.pack(pady=5)
        self.batch_button.pack(pady=5)
        self.panorama_rendering_button.pack(pady=5)
        self.live_button.pack(pady=5)
    
    def panorama_id(self) -> None:
        """Proceeds to downloading panoramas by ID."""
        self.destroy()
        panorama_id.PanoramaDownload(self.root).pack()
    
    def url(self) -> None:
        """Proceeds to downloading by a Google Street View URL."""
        self.destroy()
        url.UrlDownload(self.root).pack()
    
    def batch(self) -> None:
        """Proceeds to batch downloading panoramas/URLs."""
        self.destroy()
        batch.BatchDownload(self.root).pack()
    
    def panorama_rendering(self) -> None:
        """Proceeds to the panorama rendering screen."""
        self.destroy()
        rendering.PanoramaRendering(self.root).pack()
    
    def live(self) -> None:
        """Proceeds to the live downloading screen."""
        self.destroy()
        live.LiveDownloading(self.root).pack()


class Menu(tk.Menu):
    """Toplevel menu for the main menu."""

    def __init__(self, master: MainMenu) -> None:
        super().__init__(master)
        self.menu = tk.Menu(self, tearoff=False)
        self.menu.add_command(
            label="By Panorama ID", font=inter(12), command=master.panorama_id)
        self.menu.add_command(
            label="By URL", font=inter(12), command=master.url)
        self.menu.add_command(
            label="Batch", font=inter(12), command=master.batch)
        self.menu.add_command(
            label="Panorama Rendering", font=inter(12),
            command=master.panorama_rendering)
        self.menu.add_command(
            label="Live", font=inter(12), command=master.live)
        self.add_cascade(label="Menu", menu=self.menu)


def main() -> None:
    """Main procedure of the program."""
    root = tk.Tk()
    main_menu = MainMenu(root)
    main_menu.pack()
    root.mainloop()


if __name__ == "__main__":
    main()
