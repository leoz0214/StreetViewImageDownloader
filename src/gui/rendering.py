"""
Panorama rendering feature - the user inputs a panorama ID or URL.
Then, the panorama is downloaded and then the user can adjust
pitch, yaw and FOV, and subsequently save the square projected image.
"""
import array
import ctypes
import threading
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

from PIL import Image, ImageTk

import main
import panorama_id
import url
from _utils import (
    inter, BUTTON_COLOURS, GREEN, bool_to_state, int_if_possible,
    load_cpp_conversion_library)
from api.panorama import PanoramaSettings
from api.url import (
    parse_url, MIN_YAW, MAX_YAW, MIN_PITCH, MAX_PITCH, MIN_FOV, MAX_FOV)
from api._utils import _in_rectangle


DEFAULT_INPUT_MODE = 0
DEFAULT_ZOOM = 4
# Projection dimensions (balance between performance and resolution).
# Sensible upper and lower bounds in use.
MIN_LENGTH = 64
MAX_LENGTH = 625
DEFAULT_LENGTH = 512 
# C++ functions
try:
    conversion = load_cpp_conversion_library()
    set_cubemap = conversion.set_cubemap
    project = conversion.project
    CAN_RENDER = True
except Exception as e:
    CAN_RENDER = False
    print(
        "Warning: Rendering not possible as required "
        "C++ object file not found.")

# Initial yaw, pitch and FOV values.
DEFAULT_YAW = 0
DEFAULT_PITCH = 90
DEFAULT_FOV = 90
MAX_FLOAT_INPUT_LENGTH = 10
# Absolute FOV change upon scrolling to zoom in or out.
SCROLL_FOV_CHANGE = 10
# Ensures mouse sensitivity is reasonable.
YAW_MULTIPLIER_CONSTANT = 1.4
PITCH_MULTIPLIER_CONSTANT = 1.4


class PanoramaRendering(tk.Frame):
    """Panorama rendering feature."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.root.title(f"{main.TITLE} - Panorama Rendering")

        self.title = tk.Label(
            self, font=inter(25, True), text="Panorama Rendering")
        self.panorama_input = PanoramaInput(self)
        self.zoom_input = PanoramaRenderingZoomInput(self)
        self.back_button = tk.Button(
            self, font=inter(20), text="Back", width=15,
            **BUTTON_COLOURS, command=self.back)
        self.start_button = tk.Button(
            self, font=inter(20), text="Start", width=15,
            **BUTTON_COLOURS, command=self.start, state="disabled")
        
        self.title.grid(row=0, column=0, columnspan=2, padx=10, pady=5)
        self.panorama_input.grid(
            row=1, column=0, columnspan=2, padx=10, pady=5)
        self.zoom_input.grid(row=2, column=0, columnspan=2, padx=10, pady=5)
        self.back_button.grid(row=3, column=0, padx=10, pady=5)
        self.start_button.grid(row=3, column=1, padx=10, pady=5)

    def update_start_button_state(self) -> None:
        """Updates the state of the start button depending on input."""
        is_valid = self.panorama_input.valid
        self.start_button.config(state=bool_to_state(is_valid))
    
    def back(self) -> None:
        """Returns back to the main menu."""
        self.destroy()
        main.MainMenu(self.root).pack()
    
    def start(self) -> None:
        """Starts the download and subsequent rendering."""
        panorama_id_ = self.panorama_input.panorama_id
        zoom = self.zoom_input.zoom
        panorama_settings = PanoramaSettings(zoom=zoom)
        panorama_id.PanoramaDownloadToplevel(
            self,  panorama_id_, panorama_settings)
    
    def render(self, panorama: Image.Image) -> None:
        """Prepares to render the panorama."""
        self.pack_forget()
        PanoramaRenderingScreen(self.root, self, panorama).pack()


class PanoramaInput(tk.Frame):
    """
    Obtain panorama ID to download, either directly or extracted from a URL.
    """

    def __init__(self, master: PanoramaRendering) -> None:
        super().__init__(master, width=1800, height=200)
        self.pack_propagate(False)
        self._input_mode = tk.IntVar(value=DEFAULT_INPUT_MODE)
        self._input_mode.trace_add("write", lambda *_: self.update_input())
        # Frame to compartmentalise the radiobuttons even when the input
        # frame is stretched a lot by the URL input.
        self.input_mode_frame = tk.Frame(self)
        self.label = tk.Label(
            self.input_mode_frame, font=inter(20), text="Input Mode:")
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        for value, text in enumerate(("Panorama ID", "URL")):
            radiobutton = tk.Radiobutton(
                self.input_mode_frame, font=inter(20), text=text, width=15,
                value=value, variable=self._input_mode, **BUTTON_COLOURS,
                selectcolor=GREEN, indicatoron=False)
            radiobutton.grid(row=0, column=value + 1, padx=5, pady=5)
        self.current_input = None
        self.panorama_id_input = panorama_id.PanoramaIDInput(self)
        self.url_input = url.UrlInput(self)

        self.input_mode_frame.pack(padx=5, pady=5)
        self.update_input(True)
    
    @property
    def valid(self) -> bool:
        return self.current_input.valid
    
    @property
    def panorama_id(self) -> str:
        return (
            self.current_input.panorama_id if self._input_mode.get() == 0
            else parse_url(self.current_input.url).panorama_id)
    
    def update_input(self, first: bool = False) -> None:
        """Updates the input display based on mode selection."""
        input_mode = self._input_mode.get()
        inputs = (self.panorama_id_input, self.url_input)
        if self.current_input is inputs[input_mode]:
            return
        if self.current_input is not None:
            self.current_input.pack_forget()
        self.current_input = inputs[input_mode]
        self.current_input.pack(padx=5, pady=5)
        if not first:
            self.master.update_start_button_state()


class PanoramaRenderingZoomInput(tk.Frame):
    """
    Allows the user to either select zoom 4 or 5 (medium or max quality).
    Zoom 5 is sharper but takes even longer to set up.
    """

    def __init__(self, master: PanoramaRendering) -> None:
        super().__init__(master)
        self._zoom = tk.IntVar(value=DEFAULT_ZOOM)
        self.label = tk.Label(self, font=inter(20), text="Zoom:")
        self.label.grid(row=0, column=0, padx=5, pady=5)
        for value in range(4, 6):
            radiobutton = tk.Radiobutton(
                self, font=inter(20), text=value, width=5,
                value=value, variable=self._zoom, indicatoron=False,
                **BUTTON_COLOURS, selectcolor=GREEN)
            radiobutton.grid(row=0, column=value, padx=5, pady=5)
    
    @property
    def zoom(self) -> int:
        return self._zoom.get()
        

class PanoramaRenderingScreen(tk.Frame):
    """Main panorama rendering screen, allowing viewing of the panorama."""

    def __init__(
        self, root: tk.Tk, previous_screen: tk.Frame, panorama: Image.Image
    ) -> None:
        super().__init__(root)
        self.root = root
        self.previous_screen = previous_screen
        self.panorama = panorama
        self.previous_title = self.root.title()
        self.previous_menu = self.root.cget("menu")
        if "Save" in self.previous_title:
            self.root.title(f"{self.previous_title} - Rendering")
            self.root.config(menu="")

        self.title = tk.Label(
            self, font=inter(25, True), text="Panorama Rendering")
        self.rendering_frame = PanoramaRenderingFrame(self)
        self.back_button = tk.Button(
            self, font=inter(20), text="Back", width=15,
            **BUTTON_COLOURS, command=self.back)
        self.save_button = tk.Button(
            self, font=inter(20), text="Save", width=15,
            **BUTTON_COLOURS, command=self.save, state="disabled")
        self.home_button = tk.Button(
            self, font=inter(20), text="Home", width=15,
            **BUTTON_COLOURS, command=self.home)
        
        self.title.grid(row=0, column=0, columnspan=3, padx=10, pady=3)
        self.rendering_frame.grid(
            row=1, column=0, columnspan=3, padx=10, pady=3)
        self.back_button.grid(row=2, column=0, padx=5, pady=3)
        self.save_button.grid(row=2, column=1, padx=5, pady=3)
        self.home_button.grid(row=2, column=2, padx=5, pady=3)
    
    def destroy(self) -> None:
        """Exists rendering screen."""
        if self.rendering_frame.tk_image is None:
            # Set the C-bool variable to True, such that the C++
            # code receives the signal to cancel further cubemap
            # processing, returning early.
            self.rendering_frame.cancel.value = True
        super().destroy()
    
    def back(self) -> None:
        """Returns back to the previous screen."""
        self.destroy()
        self.root.title(self.previous_title)
        self.root.config(menu=self.previous_menu)
        self.previous_screen.pack()
    
    def save(self) -> None:
        """Save the image in the current pitch, yaw and FOV."""
        file = filedialog.asksaveasfilename(
            defaultextension=".jpg", filetypes=(("JPG", ".jpg"),),
            title="Save Image")
        if not file:
            return
        try:
            self.rendering_frame.pil_image.save(file, format="jpeg")
        except Exception as e:
            messagebox.showerror(
                "Error", f"Unfortunately, an error has occurred: {e}")
    
    def home(self) -> None:
        """Returns back to the main menu."""
        self.destroy()
        main.MainMenu(self.root).pack()


class PanoramaRenderingFrame(tk.Frame):
    """
    Final frame where the panorama rendering occurs.
    This handles all the low-level functionality too,
    such as maintaining C-arrays of pixels and RGB values, and calling
    the C++ functions.
    """

    def __init__(self, master: PanoramaRenderingScreen) -> None:
        super().__init__(master)
        self.image = master.panorama
        self.pil_image = None
        self.tk_image = None
        self.length = DEFAULT_LENGTH
        # Allows setup to be cancelled if exited.
        self.cancel = ctypes.c_bool(False)
        self.yaw = DEFAULT_YAW # Horizontal rotation [0, 360).
        self.pitch = DEFAULT_PITCH # Vertical rotation [1, 179].
        self.fov = DEFAULT_FOV # Field of view [15, 90]
        self.previous_drag_coordinates = None

        self.image_label = tk.Label(
            self, text="Generating Cubemap...", font=inter(25))
        self.image_label.pack(padx=10, pady=5)
        # Use thread to avoid freezing the GUI whilst rendering cubemap.
        threading.Thread(target=self._set_up_rendering, daemon=True).start()
    
    @property
    def offset(self) -> int:
        return MAX_LENGTH // 2 - self.length // 2

    def _set_up_rendering(self) -> None:
        # Panorama bytes (input).
        image_bytes = array.array("b", self.image.tobytes())
        self.c_image_bytes = (
            ctypes.c_byte * len(image_bytes)).from_buffer(image_bytes)
        self.image_pointer = ctypes.c_char_p(
            ctypes.addressof(self.c_image_bytes))
        # Cubemap bytes (to be used in rendering.)
        cubemap_bytes = array.array(
            "b", bytes((0, 0, 0)) * (self.image.width // 4) ** 2 * 6)
        self.c_cubemap_bytes = (
            ctypes.c_byte * len(cubemap_bytes)).from_buffer(cubemap_bytes)
        self.cubemap_pointer = ctypes.c_char_p(
            ctypes.addressof(self.c_cubemap_bytes))
        cancel_pointer = ctypes.POINTER(ctypes.c_bool)(self.cancel)
        # Generates the cubemap, writing the data to the cubemap buffer.
        set_cubemap(
            self.image_pointer, self.image.width,
            self.image.height, self.cubemap_pointer, cancel_pointer)
        if self.cancel:
            return

        self.display(new_size=True)
        self.rendering_inputs = RenderingInputs(self)
        self.rendering_inputs.pack(padx=10, pady=5)
        self.master.save_button.config(state="normal")

        self.image_label.bind("<MouseWheel>", self.scroll)
        self.image_label.bind("<B1-Motion>", self.drag)
        self.image_label.bind("<ButtonRelease-1>", lambda *_: self.release())

    def display(self, new_size: bool = False) -> None:
        """Displays the image with the current yaw, pitch and fov."""
        if new_size:
            # Only create new projection bytes if the size is changed
            # (first display or subsequent size change).
            # Does not run this every time the pitch/yaw/FOV changes.
            self.projection_bytes = array.array(
                "b", bytes((0, 0, 0)) * self.length ** 2)
            self.c_projection_bytes = (
                ctypes.c_byte * len(self.projection_bytes)
            ).from_buffer(self.projection_bytes)
            self.projection_pointer = ctypes.c_char_p(
                ctypes.addressof(self.c_projection_bytes))
        # Projects the image.
        project(
            self.projection_pointer, self.length, self.length,
            ctypes.c_double(self.yaw), ctypes.c_double(self.pitch),
            ctypes.c_double(self.fov),
            self.cubemap_pointer, self.image.width // 4)
        self.pil_image = Image.frombytes(
            "RGB", (self.length, self.length), self.c_projection_bytes)
        self.tk_image = ImageTk.PhotoImage(self.pil_image)
        self.image_label.config(
            width=MAX_LENGTH, height=MAX_LENGTH, font=None, image=self.tk_image)
    
    def scroll(self, event: tk.Event) -> None:
        """Scrolls the mouse to zoom in and out (change FOV)."""
        # When projection surface size is smaller than the maximum,
        # it will be centralised inside the maximum square.
        # Compute relative coordinates as a result and work from there.
        x = event.x - self.offset
        y = event.y - self.offset
        if not _in_rectangle((0, 0), (self.length, self.length), (x, y)):
            return
        previous_fov = self.fov
        if event.delta > 0:
            # Zoom in, decrease FOV, up to the minimum.
            self.fov = max(self.fov - SCROLL_FOV_CHANGE, MIN_FOV)
        else:
            # Zoom out, increase FOV, up to the maximum.
            self.fov = min(self.fov + SCROLL_FOV_CHANGE, MAX_FOV)
        x_from_centre = x - self.length // 2
        y_from_centre = y - self.length // 2 
        fov_change = self.fov - previous_fov
        # When scrolling occurs from position other than the centre,
        # also adjust yaw and pitch in a given direction (more natural).
        # fov change < 0 => zoom in => yaw/pitch change left/right or up/down
        # depending on mouse position relative to the centre.
        # fov change > 0 => zoom out => opposite yaw/pitch change.
        yaw_increase = -(fov_change / 2) * (x_from_centre / (self.length // 2))
        pitch_increase = (fov_change / 2) * (y_from_centre / (self.length // 2))
        self.adjust_yaw_and_pitch(yaw_increase, pitch_increase)
    
    def drag(self, event: tk.Event) -> None:
        """Allows the panorama to be dragged to alter the yaw and pitch."""
        if self.previous_drag_coordinates is None:
            # Initial. Again adjust coordinates given offset.
            image_coordinates = (event.x - self.offset, event.y - self.offset)
            if not _in_rectangle(
                (0, 0), (self.length, self.length), image_coordinates
            ):
                return
            self.previous_drag_coordinates = (event.x, event.y)
            return
        # The fast the change in x or y, the faster the camera movement.
        x_change = event.x - self.previous_drag_coordinates[0]
        y_change = event.y - self.previous_drag_coordinates[1]
        yaw_increase = (
            -x_change * self.fov / self.length * YAW_MULTIPLIER_CONSTANT)
        pitch_increase = (
            y_change * self.fov / self.length * PITCH_MULTIPLIER_CONSTANT)
        self.adjust_yaw_and_pitch(yaw_increase, pitch_increase)
        self.previous_drag_coordinates = (event.x, event.y)
    
    def release(self) -> None:
        """Mouse dragging terminated."""
        self.previous_drag_coordinates = None
    
    def adjust_yaw_and_pitch(
        self, yaw_increase: float, pitch_increase: float
    ) -> None:
        """Increases/decreases yaw and pitch by a given value."""
        # Keep yaw in valid range (using modulus).
        self.yaw = round((self.yaw + yaw_increase) % MAX_YAW, 2)
        # Keep pitch in valid range (clipping).
        self.pitch = max(
            min(round(self.pitch + pitch_increase, 2), MAX_PITCH), MIN_PITCH)
        self.display()
        self.rendering_inputs.synchronise()


class RenderingInputs(tk.Frame):
    """
    Entries to allow the user to set the yaw,
    pitch and FOV directly, by numeric input, alongside image length.
    """

    def __init__(self, master: PanoramaRenderingFrame) -> None:
        super().__init__(master)
        self.length_input = url.DimensionInput(
            self, "Width/Height:", MIN_LENGTH, MAX_LENGTH, DEFAULT_LENGTH,
            length=600, label_width=12, font_size=15)
        self.yaw_label = tk.Label(self, font=inter(15), text="Yaw:")
        self.yaw_input = RenderingInput(
            self, master.yaw, MIN_YAW, MAX_YAW - 0.000001, "yaw")
        self.pitch_label = tk.Label(self, font=inter(15), text="Pitch:")
        self.pitch_input = RenderingInput(
            self, master.pitch, MIN_PITCH, MAX_PITCH, "pitch")
        self.fov_label = tk.Label(self, font=inter(15), text="FOV:")
        self.fov_input = RenderingInput(
            self, master.fov, MIN_FOV, MAX_FOV, "fov")

        self.length_input.grid(row=0, column=0, columnspan=6, padx=5, pady=3)
        self.yaw_label.grid(row=1, column=0, padx=5, pady=3, sticky="e")
        self.yaw_input.grid(row=1, column=1, padx=5, pady=3, sticky="w")
        self.pitch_label.grid(row=1, column=2, padx=5, pady=3, sticky="e")
        self.pitch_input.grid(row=1, column=3, padx=5, pady=3, sticky="w")
        self.fov_label.grid(row=1, column=4, padx=5, pady=3, sticky="e")
        self.fov_input.grid(row=1, column=5, padx=5, pady=3, sticky="w")
    
    def update_display(self, name: str, value: int | float) -> None:
        """Updates the display based on yaw/pitch/FOV change."""
        setattr(self.master, name, value)
        self.master.display(name == "length")
    
    def synchronise(self) -> None:
        """Synchronises values with current live values."""
        self.yaw_input.value = int_if_possible(self.master.yaw)
        self.pitch_input.value = int_if_possible(self.master.pitch)
        self.fov_input.value = int_if_possible(self.master.fov)


class RenderingInput(tk.Entry):
    """Entry for one of the rendering inputs (yaw/pitch/FOV)."""

    def __init__(
        self, master: RenderingInputs, initial_value: float,
        minimum: int, maximum: int, name: str
    ) -> None:
        self.variable = tk.StringVar(value=initial_value)
        self.variable.trace_add("write", lambda *_: self.validate())
        self.previous = initial_value
        self.min = minimum
        self.max = maximum
        self.setting = False
        self.name = name
        super().__init__(
            master, font=inter(15), width=6, textvariable=self.variable)
    
    @property
    def value(self) -> float:
        return float(self.variable.get())
    
    @value.setter
    def value(self, value: float) -> None:
        self.setting = True
        self.variable.set(value)
        self.setting = False

    def validate(self) -> None:
        """
        Validates the new variable value,
        reverting if not a valid decimal number (all digits, max one period).
        """
        if self.setting:
            # Don't bother validating if setting from program - it is valid.
            return
        value = self.variable.get()
        if value in ("", "."):
            self.previous = value
            return
        if (
            len(value) > MAX_FLOAT_INPUT_LENGTH
            or value.count(".") > 1 or not value.replace(".", "").isdigit()
        ):
            self.variable.set(value=self.previous)
            return
        if self.min <= self.value <= self.max:
            self.master.update_display(self.name, self.value)
        self.previous = value
