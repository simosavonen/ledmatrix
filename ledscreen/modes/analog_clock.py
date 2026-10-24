import math
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

TICK_COLOR = (90, 90, 100)
HOUR_COLOR = (255, 150, 20)
MINUTE_COLOR = (230, 230, 240)
SECOND_COLOR = (220, 40, 40)
RADIUS = 14


class AnalogClockMode(Mode):
    """A classic round clock face - a change of pace from the digital readout."""

    name = "analog_clock"

    def render(self, canvas: Canvas, now: datetime) -> None:
        canvas.clear((0, 0, 0))
        cx, cy = canvas.width / 2, canvas.height / 2

        for i in range(12):
            angle = i / 12 * 2 * math.pi
            x = cx + math.sin(angle) * RADIUS
            y = cy - math.cos(angle) * RADIUS
            canvas.draw_dot(x, y, 0.5, TICK_COLOR)

        sec = now.second + now.microsecond / 1_000_000
        minute = now.minute + sec / 60
        hour = (now.hour % 12) + minute / 60

        hour_angle = hour / 12 * 2 * math.pi
        minute_angle = minute / 60 * 2 * math.pi
        sec_angle = sec / 60 * 2 * math.pi

        canvas.draw_line_aa(
            cx, cy, cx + math.sin(hour_angle) * RADIUS * 0.5, cy - math.cos(hour_angle) * RADIUS * 0.5,
            HOUR_COLOR, width=1.6,
        )
        canvas.draw_line_aa(
            cx, cy, cx + math.sin(minute_angle) * RADIUS * 0.85, cy - math.cos(minute_angle) * RADIUS * 0.85,
            MINUTE_COLOR, width=1.2,
        )
        canvas.draw_line_aa(
            cx, cy, cx + math.sin(sec_angle) * RADIUS * 0.9, cy - math.cos(sec_angle) * RADIUS * 0.9,
            SECOND_COLOR, width=0.8,
        )
        canvas.draw_dot(cx, cy, 0.8, MINUTE_COLOR)
        # The hands converge at the hub, so several strokes overlap there -
        # same compounding issue as the clock digits and Pong paddles.
        canvas.bloom(radius=1.0, strength=0.3)
