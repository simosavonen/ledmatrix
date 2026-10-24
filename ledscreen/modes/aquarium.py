import math
import random
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

"""A small school of boids (simple flocking agents) - chaotic, organic
motion that never repeats the same way twice."""

NUM_BOIDS = 16
NEIGHBOR_RADIUS = 9.0
SEPARATION_RADIUS = 2.5
MAX_SPEED = 13.0
EDGE_MARGIN = 4.0

PALETTE = [
    (60, 200, 220),
    (80, 160, 255),
    (120, 220, 200),
    (40, 180, 180),
]


class AquariumMode(Mode):
    name = "aquarium"

    def __init__(self):
        self._boids: list[dict] = []
        self._last_time: datetime | None = None

    def reset(self) -> None:
        self._boids = []
        self._last_time = None

    def _seed(self, canvas: Canvas) -> None:
        self._boids = []
        for _ in range(NUM_BOIDS):
            angle = random.uniform(0, 2 * math.pi)
            self._boids.append(
                {
                    "x": random.uniform(0, canvas.width),
                    "y": random.uniform(0, canvas.height),
                    "vx": math.cos(angle) * MAX_SPEED * 0.5,
                    "vy": math.sin(angle) * MAX_SPEED * 0.5,
                    "color": random.choice(PALETTE),
                }
            )

    def render(self, canvas: Canvas, now: datetime) -> None:
        if not self._boids or self._last_time is None:
            self._seed(canvas)
            self._last_time = now

        dt = min(max(0.0, (now - self._last_time).total_seconds()), 0.2)
        self._last_time = now

        for b in self._boids:
            sep_x = sep_y = align_x = align_y = coh_x = coh_y = 0.0
            count = 0
            for other in self._boids:
                if other is b:
                    continue
                dx = other["x"] - b["x"]
                dy = other["y"] - b["y"]
                dist = math.hypot(dx, dy)
                if dist > NEIGHBOR_RADIUS or dist == 0:
                    continue
                count += 1
                align_x += other["vx"]
                align_y += other["vy"]
                coh_x += other["x"]
                coh_y += other["y"]
                if dist < SEPARATION_RADIUS:
                    sep_x -= dx / dist
                    sep_y -= dy / dist

            ax = sep_x * 3.0
            ay = sep_y * 3.0
            if count:
                ax += (align_x / count - b["vx"]) * 0.08
                ay += (align_y / count - b["vy"]) * 0.08
                ax += (coh_x / count - b["x"]) * 0.03
                ay += (coh_y / count - b["y"]) * 0.03

            if b["x"] < EDGE_MARGIN:
                ax += (EDGE_MARGIN - b["x"]) * 1.5
            elif b["x"] > canvas.width - EDGE_MARGIN:
                ax -= (b["x"] - (canvas.width - EDGE_MARGIN)) * 1.5
            if b["y"] < EDGE_MARGIN:
                ay += (EDGE_MARGIN - b["y"]) * 1.5
            elif b["y"] > canvas.height - EDGE_MARGIN:
                ay -= (b["y"] - (canvas.height - EDGE_MARGIN)) * 1.5

            b["vx"] += ax * dt
            b["vy"] += ay * dt
            speed = math.hypot(b["vx"], b["vy"])
            if speed > MAX_SPEED:
                b["vx"] = b["vx"] / speed * MAX_SPEED
                b["vy"] = b["vy"] / speed * MAX_SPEED

            b["x"] = min(max(b["x"] + b["vx"] * dt, 0), canvas.width - 1)
            b["y"] = min(max(b["y"] + b["vy"] * dt, 0), canvas.height - 1)

        canvas.clear((0, 0, 0))
        for b in self._boids:
            tail_x = b["x"] - b["vx"] * 0.05
            tail_y = b["y"] - b["vy"] * 0.05
            dim = tuple(c // 3 for c in b["color"])
            canvas.draw_dot(tail_x, tail_y, 0.6, dim)
            canvas.draw_dot(b["x"], b["y"], 0.9, b["color"])
        canvas.bloom()
