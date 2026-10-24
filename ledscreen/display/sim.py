from PIL import Image, ImageTk

from ..canvas import Canvas
from .base import Display


class SimDisplay(Display):
    """Windows-friendly stand-in for the real LED matrix: an upscaled preview window."""

    def __init__(self, width: int = 64, height: int = 32, scale: int = 12, live: bool = True):
        self.width = width
        self.height = height
        self.scale = scale
        self.last_image: Image.Image | None = None
        self._tk = None
        self._label = None
        self._photo = None
        if live:
            self._init_window()

    def _init_window(self) -> None:
        import tkinter as tk

        self._tk = tk.Tk()
        self._tk.title("LED screen simulator (64x32)")
        self._tk.configure(bg="black")
        self._label = tk.Label(self._tk, bg="black", borderwidth=0)
        self._label.pack()

    def show(self, canvas: Canvas) -> None:
        self.last_image = canvas.image.copy()
        if self._tk is None:
            return
        big = canvas.image.resize(
            (self.width * self.scale, self.height * self.scale), Image.NEAREST
        )
        self._photo = ImageTk.PhotoImage(big)
        self._label.configure(image=self._photo)
        self._tk.update_idletasks()
        self._tk.update()

    def save_snapshot(self, path: str, scale: int | None = None) -> None:
        if self.last_image is None:
            return
        s = scale or self.scale
        big = self.last_image.resize((self.width * s, self.height * s), Image.NEAREST)
        big.save(path)

    def close(self) -> None:
        if self._tk is not None:
            self._tk.destroy()
