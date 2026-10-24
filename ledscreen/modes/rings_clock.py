import math
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

HOUR_COLOR = (255, 150, 20)
MINUTE_COLOR = (230, 230, 240)
SECOND_COLOR = (230, 50, 50)
TRACK_COLOR = (22, 22, 30)

# outer = hour, middle = minute, inner = second - biggest/slowest ring on
# the outside, like a clock face read from the rim inward
RINGS = [
    ("hour", 13, HOUR_COLOR),
    ("minute", 9, MINUTE_COLOR),
    ("second", 5, SECOND_COLOR),
]
DOT_RADIUS = 1.1


class RingsClockMode(Mode):
    """Three concentric activity-ring-style arcs instead of hands or digits -
    each ring fills clockwise over its unit (hour/minute/second) and resets.
    The dim, always-visible track makes each ring read as a ring even at 0%."""

    name = "rings_clock"

    def render(self, canvas: Canvas, now: datetime) -> None:
        canvas.clear((0, 0, 0))
        cx, cy = canvas.width / 2, canvas.height / 2

        sec = now.second + now.microsecond / 1_000_000
        minute = now.minute + sec / 60
        hour = (now.hour % 12) + minute / 60

        fractions = {"hour": hour / 12, "minute": minute / 60, "second": sec / 60}

        for key, radius, color in RINGS:
            fraction = fractions[key]
            steps = max(24, int(radius * 2 * math.pi * 1.3))
            filled_steps = int(steps * fraction)
            for i in range(steps):
                angle = i / steps * 2 * math.pi
                x = cx + math.sin(angle) * radius
                y = cy - math.cos(angle) * radius
                dot_color = color if i < filled_steps else TRACK_COLOR
                canvas.draw_dot(x, y, DOT_RADIUS, dot_color)

        canvas.bloom()
