from datetime import datetime

from ..canvas import Canvas
from .base import Mode

HOUR_COLOR = (255, 150, 20)
MINUTE_COLOR = (230, 230, 240)
SECOND_COLOR = (230, 50, 50)
TRACK_COLOR = (22, 22, 30)

BAR_HEIGHT = 8
GAUGE_WIDTH = 50  # leaves room on the right for the two-digit readout

# (label color, scale of this unit, value fraction extractor name, bar top y)
BARS = [
    ("hour", HOUR_COLOR, 24, 2),
    ("minute", MINUTE_COLOR, 60, 12),
    ("second", SECOND_COLOR, 60, 22),
]


class GaugeClockMode(Mode):
    """Three thick horizontal bars - hour (0-24), minute (0-60), second
    (0-60) - filling left to right, with a small exact readout at the end
    of each. Reads as a shape from across the room; exact up close."""

    name = "gauge_clock"

    def render(self, canvas: Canvas, now: datetime) -> None:
        canvas.clear((0, 0, 0))

        sec = now.second + now.microsecond / 1_000_000
        minute = now.minute + sec / 60
        hour = now.hour + minute / 60

        values = {"hour": (hour, now.hour), "minute": (minute, now.minute), "second": (sec, now.second)}

        for key, color, scale, y0 in BARS:
            smooth_value, display_value = values[key]
            fraction = smooth_value / scale
            filled = fraction * GAUGE_WIDTH
            full_px = int(filled)
            partial = filled - full_px

            for y in range(y0, y0 + BAR_HEIGHT):
                for x in range(GAUGE_WIDTH):
                    if x < full_px:
                        canvas.set_pixel(x, y, color)
                    elif x == full_px and partial > 0.05:
                        dim = tuple(int(c * partial) for c in color)
                        canvas.set_pixel(x, y, dim)
                    else:
                        canvas.set_pixel(x, y, TRACK_COLOR)

            text = f"{display_value:02d}"
            text_w = canvas.text_width(text, scale=1)
            canvas.draw_text(canvas.width - text_w - 1, y0, text, color, scale=1)

        canvas.bloom()
