import math
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

RING_COLOR = (230, 230, 240)
TRACK_COLOR = (25, 25, 35)
TEXT_COLOR = (255, 150, 20)
RADIUS = 13
DOT_RADIUS = 1.6  # large enough that a single ring of dots reads as a thick band


class ThickRingClockMode(Mode):
    """A bold minute ring wrapped around a big HH:MM readout - combines an
    abstract glanceable shape with an exact digital time in one face,
    instead of choosing between them."""

    name = "thick_ring_clock"

    def render(self, canvas: Canvas, now: datetime) -> None:
        canvas.clear((0, 0, 0))
        cx, cy = canvas.width / 2, canvas.height / 2

        minute = now.minute + (now.second + now.microsecond / 1_000_000) / 60
        fraction = minute / 60

        steps = max(24, int(RADIUS * 2 * math.pi * 1.3))
        filled_steps = int(steps * fraction)
        for i in range(steps):
            angle = i / steps * 2 * math.pi
            x = cx + math.sin(angle) * RADIUS
            y = cy - math.cos(angle) * RADIUS
            color = RING_COLOR if i < filled_steps else TRACK_COLOR
            canvas.draw_dot(x, y, DOT_RADIUS, color)

        text = now.strftime("%H:%M")
        text_w = canvas.text_width(text, scale=1)
        canvas.draw_text((canvas.width - text_w) // 2, int(cy) - 3, text, TEXT_COLOR, scale=1)

        canvas.bloom()
