"""
Window to preview and save an image following a panorama or URL download.
"""
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

from PIL import Image, ImageTk

import main
import panorama_id
import rendering
from _utils import inter, BUTTON_COLOURS


# Minimum image dimensions to create a scrollbar for.
MIN_SCROLLBAR_WIDTH = 1600
MIN_SCROLLBAR_HEIGHT = 675


class SaveImageFrame(tk.Frame):
    """Save Image GUI, including an image preview."""

    def __init__(
        self, root: tk.Tk, previous: tk.Frame, image: Image.Image,
        can_render_panorama: bool = False
    ) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(f"{self.root.title()} - Save")
        self.menu = SaveImageMenu(self)
        self.root.config(menu=self.menu)
        self.previous_frame = previous
        self.image = image
        self.tk_image = ImageTk.PhotoImage(self.image)

        self.title = tk.Label(self, font=inter(25, True), text="Save Image")
        self.image_preview = ImagePreviewFrame(self)
        image_source = "Panorama ID" if isinstance(
            self.previous_frame, panorama_id.PanoramaDownload) else "URL"
        text = " | ".join((
            f"Source: {image_source}",
            f"Resolution: {self.image.width} x {self.image.height}",
            "Mode: RGB (24-bit)", "Format: JPG"))
        self.image_info_label = tk.Label(self, font=inter(12), text=text)
        self.retry_button = tk.Button(
            self, font=inter(20), text="Download Another", width=15,
            **BUTTON_COLOURS, command=self.retry)
        self.save_button = tk.Button(
            self, font=inter(20), text="Save", width=15, **BUTTON_COLOURS,
            command=self.save)
        self.render_button = tk.Button(
            self, font=inter(20), text="Render", width=15, **BUTTON_COLOURS,
            command=self.render)
        self.home_button = tk.Button(
            self, font=inter(20), text="Main Menu", width=15,
            **BUTTON_COLOURS, command=self.home)
        
        self.root.bind("<Control-s>", lambda *_: self.save())

        self.title.grid(row=0, column=0, columnspan=4, padx=10, pady=5)
        self.image_preview.grid(row=1, column=0, columnspan=4, padx=10, pady=5)
        self.image_info_label.grid(
            row=2, column=0, columnspan=4, padx=10, pady=5)
        self.retry_button.grid(row=3, column=0, padx=(50, 10), pady=5)
        self.save_button.grid(row=3, column=1, padx=10, pady=5)
        if can_render_panorama:
            self.render_button.grid(row=3, column=2, padx=10, pady=5)
        self.home_button.grid(
            row=3, column=2 + can_render_panorama, padx=(10, 50), pady=5)

    def destroy(self) -> None:
        """Exits the save image screen."""
        self.root.config(menu=None)
        self.root.unbind("<Control-s>")
        super().destroy()
    
    def retry(self) -> None:
        """Go back to the previous download screen."""
        self.destroy()
        self.root.title(self.root.title().removesuffix(" - Save"))
        self.previous_frame.pack()
    
    def save(self) -> None:
        """Allows the user to save the image to a file path of their choice."""
        file = filedialog.asksaveasfilename(
            defaultextension=".jpg", filetypes=(("JPG", ".jpg"),))
        if not file:
            return
        try:
            self.image.save(file, format="jpeg")
        except Exception as e:
            messagebox.showerror(
                "Error", f"Unfortunately, an error has occurred: {e}")
            
    def render(self) -> None:
        """Proceeds to the rendering screen (panoramas only)."""
        self.pack_forget()
        rendering.PanoramaRenderingScreen(self.root, self, self.image).pack()
    
    def home(self) -> None:
        """Returns to the main menu of the program."""
        self.destroy()
        main.MainMenu(self.root).pack()


class SaveImageMenu(tk.Menu):
    """Toplevel menu for the save image screen."""

    def __init__(self, master: SaveImageFrame) -> None:
        super().__init__(master)
        self.file_menu = tk.Menu(self, tearoff=False)
        self.file_menu.add_command(
            label="Save (Ctrl+S)", font=inter(12), command=master.save)
        self.file_menu.add_command(
            label="Download Another", font=inter(12), command=master.retry)
        self.file_menu.add_command(
            label="Main Menu", font=inter(12), command=master.home)
        self.add_cascade(label="File", menu=self.file_menu)


class ImagePreviewFrame(tk.Frame):
    """Image preview frame, including a canvas and scrollbars if necessary."""

    def __init__(self, master: SaveImageFrame) -> None:
        super().__init__(master)
        self.horizontal_scrollbar = None
        self.vertical_scrollbar = None
        image = master.tk_image
        if image.width() >= MIN_SCROLLBAR_WIDTH:
            self.horizontal_scrollbar = tk.Scrollbar(self, orient="horizontal")
        if image.height() >= MIN_SCROLLBAR_HEIGHT:
            self.vertical_scrollbar = tk.Scrollbar(self, orient="vertical")
        width = min(image.width(), MIN_SCROLLBAR_WIDTH)
        height = min(image.height(), MIN_SCROLLBAR_HEIGHT)
        if (
            self.horizontal_scrollbar is not None
            and self.vertical_scrollbar is not None
        ):
            self.canvas = tk.Canvas(
                self, width=width, height=height,
                xscrollcommand=self.horizontal_scrollbar.set,
                yscrollcommand=self.vertical_scrollbar.set)
        elif self.horizontal_scrollbar is not None:
            self.canvas = tk.Canvas(
                self, width=width, height=height,
                xscrollcommand=self.horizontal_scrollbar.set)
        elif self.vertical_scrollbar is not None:
            self.canvas = tk.Canvas(
                self, width=width, height=height,
                yscrollcommand=self.vertical_scrollbar.set)
        else:
            self.canvas = tk.Canvas(self, width=width, height=height)
        
        self.canvas.create_image(0, 0, image=image, anchor="nw")
        self.canvas.grid(row=0, column=0)
        if (
            self.horizontal_scrollbar is None
            and self.vertical_scrollbar is None
        ):
            return
        if self.horizontal_scrollbar is not None:
            self.horizontal_scrollbar.config(command=self.canvas.xview)
            self.horizontal_scrollbar.grid(row=1, column=0, sticky="we")
        if self.vertical_scrollbar is not None:
            self.vertical_scrollbar.config(command=self.canvas.yview)
            self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
