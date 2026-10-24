import random
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

TRAIL_LEN = 8
HEAD_COLOR = (180, 255, 180)
TAIL_COLOR = (0, 120, 0)


class MatrixRainMode(Mode):
    """Ambient 'digital rain' - falling glowing trails, one per column."""

    name = "matrix_rain"

    def __init__(self):
        self._drops: list[dict] = []
        self._last_time: datetime | None = None

    def reset(self) -> None:
        self._drops = []
        self._last_time = None

    def _spawn(self, x: int, canvas: Canvas) -> dict:
        return {
            "x": x,
            "y": random.uniform(-canvas.height, 0),
            "speed": random.uniform(8.0, 20.0),  # rows per second
        }

    def render(self, canvas: Canvas, now: datetime) -> None:
        if not self._drops:
            self._drops = [self._spawn(x, canvas) for x in range(canvas.width)]
            self._last_time = now

        dt = max(0.0, (now - self._last_time).total_seconds())
        self._last_time = now
        dt = min(dt, 0.2)  # clamp in case of a long pause between frames

        canvas.clear((0, 0, 0))

        for drop in self._drops:
            drop["y"] += drop["speed"] * dt
            if drop["y"] - TRAIL_LEN > canvas.height:
                self._drops[drop["x"]] = self._spawn(drop["x"], canvas)
                drop = self._drops[drop["x"]]

            head_y = int(drop["y"])
            for offset in range(TRAIL_LEN):
                py = head_y - offset
                if py < 0 or py >= canvas.height:
                    continue
                t = offset / TRAIL_LEN
                color = tuple(
                    int(HEAD_COLOR[i] * (1 - t) + TAIL_COLOR[i] * t) for i in range(3)
                )
                canvas.set_pixel(drop["x"], py, color)
