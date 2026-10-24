from datetime import datetime

from ..canvas import Canvas
from .base import Mode

HOUR_COLOR = (255, 150, 20)
COLON_COLOR = (140, 140, 155)
MINUTE_COLOR = (230, 230, 240)
SECOND_COLOR = (230, 50, 50)

SCALE = 4
PAN_DURATION = 15.0  # seconds for the full text to cross the screen, left to right


class GiantClockMode(Mode):
    """The full HH:MM:SS in one large, color-coded string that's wider than
    the screen, slowly panning left to right so it's always legible up
    close even though it never all fits in view at once. Position is
    keyed off wall-clock time (not internal state), so it's always in
    sync no matter when this mode happens to come up."""

    name = "giant_clock"

    def render(self, canvas: Canvas, now: datetime) -> None:
        canvas.clear((0, 0, 0))

        text = now.strftime("%H:%M:%S")
        colors = [HOUR_COLOR, HOUR_COLOR, COLON_COLOR, MINUTE_COLOR, MINUTE_COLOR, COLON_COLOR, SECOND_COLOR, SECOND_COLOR]

        text_w = canvas.text_width(text, scale=SCALE)
        glyph_h = 7 * SCALE
        y = (canvas.height - glyph_h) // 2

        phase = (now.timestamp() % PAN_DURATION) / PAN_DURATION
        start_x, end_x = canvas.width, -text_w
        x = start_x + (end_x - start_x) * phase

        cursor = x
        for char, color in zip(text, colors):
            cursor += canvas.draw_glyph(round(cursor), y, char, color, scale=SCALE)

        canvas.bloom()
