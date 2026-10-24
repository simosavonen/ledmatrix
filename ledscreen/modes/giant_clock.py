from datetime import datetime

from ..canvas import Canvas
from .base import Mode

HOUR_COLOR = (255, 150, 20)
MINUTE_COLOR = (230, 230, 240)
SECOND_COLOR = (230, 50, 50)

SCALE = 4
CYCLE_SECONDS = 4  # how long each unit stays on screen

# (label, color, value extractor)
UNITS = [
    ("H", HOUR_COLOR, lambda now: now.hour),
    ("M", MINUTE_COLOR, lambda now: now.minute),
    ("S", SECOND_COLOR, lambda now: now.second),
]


class GiantClockMode(Mode):
    """One huge number at a time, cycling hour -> minute -> second every few
    seconds, with a small corner letter marking which. The most readable
    option at a distance, at the cost of not showing everything at once.
    Cycling is keyed off wall-clock time (not internal state), so it's
    always in sync no matter when this mode happens to come up."""

    name = "giant_clock"

    def render(self, canvas: Canvas, now: datetime) -> None:
        canvas.clear((0, 0, 0))

        phase = int(now.timestamp()) % (CYCLE_SECONDS * len(UNITS)) // CYCLE_SECONDS
        label, color, extractor = UNITS[phase]

        text = f"{extractor(now):02d}"
        text_w = canvas.text_width(text, scale=SCALE)
        glyph_h = 7 * SCALE
        x = (canvas.width - text_w) // 2
        y = (canvas.height - glyph_h) // 2
        canvas.draw_text(x, y, text, color, scale=SCALE)
        canvas.draw_text(2, 1, label, color, scale=1)

        canvas.bloom()
