from datetime import datetime

from ..canvas import Canvas
from .base import Mode

DIGIT_COLOR = (255, 150, 20)
SECONDS_BAR_COLOR = (20, 110, 255)


class ClockMode(Mode):
    """A big HH:MM clock with a blinking colon and a sub-second sweep bar.

    The sweep bar along the bottom row fills up over each minute (60s), giving a
    continuous, visibly-precise sense of time passing rather than just ticking digits.
    Accuracy comes from the Pi's NTP-synced system clock, not from anything drawn here.
    """

    name = "clock"

    def render(self, canvas: Canvas, now: datetime) -> None:
        canvas.clear((0, 0, 0))

        colon_on = now.microsecond < 500_000
        text = now.strftime("%H") + (":" if colon_on else " ") + now.strftime("%M")

        scale = 2
        text_w = canvas.text_width(text, scale=scale)
        glyph_h = 7 * scale
        x = (canvas.width - text_w) // 2
        y = (canvas.height - glyph_h) // 2 - 2
        canvas.draw_text(x, y, text, DIGIT_COLOR, scale=scale)

        fraction = (now.second + now.microsecond / 1_000_000) / 60.0
        filled = int(fraction * canvas.width)
        canvas.draw_hline(canvas.height - 1, 0, filled, SECONDS_BAR_COLOR)
        canvas.bloom()
