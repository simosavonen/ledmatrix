import math
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

TICK_COLOR = (90, 90, 100)
HOUR_COLOR = (255, 150, 20)
MINUTE_COLOR = (230, 230, 240)
SECOND_COLOR = (220, 40, 40)
RADIUS = 14

# Each time this face comes up it slowly zooms in over its ~60s on screen,
# so by the time it's about to switch away the hands fill the screen up
# close instead of looking static the whole minute. Resets via reset()
# every time the rotation brings this face back.
ZOOM_DURATION = 60.0
ZOOM_END = 3.0


class AnalogClockMode(Mode):
    """A classic round clock face - a change of pace from the digital readout."""

    name = "analog_clock"

    def __init__(self):
        self._shown_since: datetime | None = None

    def reset(self) -> None:
        self._shown_since = None

    def render(self, canvas: Canvas, now: datetime) -> None:
        canvas.clear((0, 0, 0))
        cx, cy = canvas.width / 2, canvas.height / 2

        if self._shown_since is None:
            self._shown_since = now
        elapsed = (now - self._shown_since).total_seconds()
        progress = max(0.0, min(1.0, elapsed / ZOOM_DURATION))
        zoom = 1.0 + (ZOOM_END - 1.0) * progress
        radius = RADIUS * zoom

        for i in range(12):
            angle = i / 12 * 2 * math.pi
            x = cx + math.sin(angle) * radius
            y = cy - math.cos(angle) * radius
            canvas.draw_dot(x, y, 0.5 * zoom, TICK_COLOR)

        sec = now.second + now.microsecond / 1_000_000
        minute = now.minute + sec / 60
        hour = (now.hour % 12) + minute / 60

        hour_angle = hour / 12 * 2 * math.pi
        minute_angle = minute / 60 * 2 * math.pi
        sec_angle = sec / 60 * 2 * math.pi

        canvas.draw_line_aa(
            cx, cy, cx + math.sin(hour_angle) * radius * 0.5, cy - math.cos(hour_angle) * radius * 0.5,
            HOUR_COLOR, width=1.6 * zoom,
        )
        canvas.draw_line_aa(
            cx, cy, cx + math.sin(minute_angle) * radius * 0.85, cy - math.cos(minute_angle) * radius * 0.85,
            MINUTE_COLOR, width=1.2 * zoom,
        )
        canvas.draw_line_aa(
            cx, cy, cx + math.sin(sec_angle) * radius * 0.9, cy - math.cos(sec_angle) * radius * 0.9,
            SECOND_COLOR, width=0.8 * zoom,
        )
        canvas.draw_dot(cx, cy, 0.8 * zoom, MINUTE_COLOR)
        canvas.bloom()
