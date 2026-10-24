try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:  # only available on the Pi, after installing rpi-rgb-led-matrix
    RGBMatrix = None
    RGBMatrixOptions = None

from ..canvas import Canvas
from .base import Display


class MatrixDisplay(Display):
    """Drives the real Adafruit RGB Matrix + RTC HAT via rpi-rgb-led-matrix."""

    def __init__(self, brightness: int = 30, gpio_slowdown: int = 4, hardware_pulsing: bool = False):
        if RGBMatrix is None:
            raise RuntimeError(
                "rgbmatrix library not available - this backend only runs on the "
                "Raspberry Pi with hzeller/rpi-rgb-led-matrix's Python bindings installed."
            )
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = "adafruit-hat-pwm" if hardware_pulsing else "adafruit-hat"
        options.gpio_slowdown = gpio_slowdown
        options.brightness = brightness  # percent - this is a display, not a light source
        options.pwm_bits = 11
        options.pwm_lsb_nanoseconds = 130
        options.disable_hardware_pulsing = not hardware_pulsing

        self.width = options.cols
        self.height = options.rows
        self.matrix = RGBMatrix(options=options)
        self._frame_canvas = self.matrix.CreateFrameCanvas()

    def show(self, canvas: Canvas) -> None:
        self._frame_canvas.SetImage(canvas.image.convert("RGB"))
        self._frame_canvas = self.matrix.SwapOnVSync(self._frame_canvas)

    def close(self) -> None:
        self.matrix.Clear()
