import math
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

TICK_COLOR = (80, 80, 110)
HOUR_COLOR = (255, 150, 20)
MINUTE_COLOR = (230, 230, 240)
TIP_COLOR = (255, 255, 255)
CENTER_COLOR = (60, 60, 90)
# Big relative to the 64x32 screen on purpose: at any moment only a slice
# of the dial fits, so it reads as a tight close-up on the second hand
# rather than a whole clock face shrunk to fit.
RADIUS = 22


class OrbitClockMode(Mode):
    """Same clock, inverted reference frame: the second hand's tip is pinned
    to the dead center of the screen, so instead of watching a hand sweep
    around a fixed face, you watch the whole dial swing around a fixed tip -
    the clock orbits the second hand instead of the other way around."""

    name = "orbit_clock"

    def render(self, canvas: Canvas, now: datetime) -> None:
        canvas.clear((0, 0, 0))
        cx, cy = canvas.width / 2, canvas.height / 2

        sec = now.second + now.microsecond / 1_000_000
        minute = now.minute + sec / 60
        hour = (now.hour % 12) + minute / 60

        sec_angle = sec / 60 * 2 * math.pi
        # Offset of the second hand's tip from the TRUE dial center. Shifting
        # every other point by minus this offset pins the tip at (cx, cy).
        tip_dx = math.sin(sec_angle) * RADIUS
        tip_dy = -math.cos(sec_angle) * RADIUS

        def plot(dx: float, dy: float, radius: float, color) -> None:
            canvas.draw_dot(cx + dx - tip_dx, cy + dy - tip_dy, radius, color)

        def line(dx: float, dy: float, color, width: float) -> None:
            canvas.draw_line_aa(
                cx - tip_dx, cy - tip_dy, cx + dx - tip_dx, cy + dy - tip_dy, color, width=width
            )

        for i in range(12):
            angle = i / 12 * 2 * math.pi
            plot(math.sin(angle) * RADIUS, -math.cos(angle) * RADIUS, 0.9, TICK_COLOR)

        hour_angle = hour / 12 * 2 * math.pi
        minute_angle = minute / 60 * 2 * math.pi
        line(math.sin(hour_angle) * RADIUS * 0.5, -math.cos(hour_angle) * RADIUS * 0.5, HOUR_COLOR, 2.6)
        line(math.sin(minute_angle) * RADIUS * 0.85, -math.cos(minute_angle) * RADIUS * 0.85, MINUTE_COLOR, 2.0)

        plot(0, 0, 1.4, CENTER_COLOR)  # the true dial center, swinging around the fixed tip
        canvas.draw_dot(cx, cy, 1.6, TIP_COLOR)  # the pinned second-hand tip
        canvas.bloom()
