import math
import random
from datetime import datetime, timedelta

from ..canvas import Canvas
from .base import Mode

"""A small school of boids (simple flocking agents) - chaotic, organic
motion that never repeats the same way twice. A predator occasionally
swims through and scatters the school."""

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

PREDATOR_COLOR = (230, 45, 45)
PREDATOR_SPEED = 15.0
PREDATOR_SIZE = 2.2
FLEE_RADIUS = 11.0
FLEE_STRENGTH = 14.0
PANIC_SPEED_MULT = 1.6  # fleeing fish briefly swim faster than their normal cap
PREDATOR_GAP_MIN = 8.0  # seconds between the predator leaving and its next pass
PREDATOR_GAP_MAX = 20.0


class AquariumMode(Mode):
    name = "aquarium"

    def __init__(self):
        self._boids: list[dict] = []
        self._last_time: datetime | None = None
        self._predator: dict | None = None
        self._next_predator_at: datetime | None = None

    def reset(self) -> None:
        self._boids = []
        self._last_time = None
        self._predator = None
        self._next_predator_at = None

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

    def _spawn_predator(self, canvas: Canvas) -> None:
        from_left = random.random() < 0.5
        direction = 1 if from_left else -1
        self._predator = {
            "x": -PREDATOR_SIZE * 2 if from_left else canvas.width + PREDATOR_SIZE * 2,
            "y": random.uniform(canvas.height * 0.3, canvas.height * 0.7),
            "vx": direction * PREDATOR_SPEED,
            "age": 0.0,
        }

    def render(self, canvas: Canvas, now: datetime) -> None:
        if not self._boids or self._last_time is None:
            self._seed(canvas)
            self._last_time = now

        dt = min(max(0.0, (now - self._last_time).total_seconds()), 0.2)
        self._last_time = now

        if self._next_predator_at is None:
            self._next_predator_at = now + timedelta(seconds=random.uniform(PREDATOR_GAP_MIN, PREDATOR_GAP_MAX))
        if self._predator is None and now >= self._next_predator_at:
            self._spawn_predator(canvas)

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

            panic = False
            if self._predator is not None:
                pdx = b["x"] - self._predator["x"]
                pdy = b["y"] - self._predator["y"]
                pdist = math.hypot(pdx, pdy)
                if pdist < FLEE_RADIUS:
                    panic = True
                    if pdist > 0:
                        push = (FLEE_RADIUS - pdist) / FLEE_RADIUS
                        ax += pdx / pdist * FLEE_STRENGTH * push
                        ay += pdy / pdist * FLEE_STRENGTH * push

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
            max_speed = MAX_SPEED * PANIC_SPEED_MULT if panic else MAX_SPEED
            if speed > max_speed:
                b["vx"] = b["vx"] / speed * max_speed
                b["vy"] = b["vy"] / speed * max_speed

            b["x"] = min(max(b["x"] + b["vx"] * dt, 0), canvas.width - 1)
            b["y"] = min(max(b["y"] + b["vy"] * dt, 0), canvas.height - 1)

        if self._predator is not None:
            p = self._predator
            p["age"] += dt
            p["x"] += p["vx"] * dt
            p["y"] += math.sin(p["age"] * 1.3) * 6.0 * dt
            if p["x"] < -PREDATOR_SIZE * 3 or p["x"] > canvas.width + PREDATOR_SIZE * 3:
                self._predator = None
                self._next_predator_at = now + timedelta(
                    seconds=random.uniform(PREDATOR_GAP_MIN, PREDATOR_GAP_MAX)
                )

        canvas.clear((0, 0, 0))
        for b in self._boids:
            tail_x = b["x"] - b["vx"] * 0.05
            tail_y = b["y"] - b["vy"] * 0.05
            dim = tuple(c // 3 for c in b["color"])
            canvas.draw_dot(tail_x, tail_y, 0.6, dim)
            canvas.draw_dot(b["x"], b["y"], 0.9, b["color"])
        if self._predator is not None:
            p = self._predator
            tail_x = p["x"] - p["vx"] * 0.08
            dim = tuple(c // 3 for c in PREDATOR_COLOR)
            canvas.draw_dot(tail_x, p["y"], PREDATOR_SIZE * 0.6, dim)
            canvas.draw_dot(p["x"], p["y"], PREDATOR_SIZE, PREDATOR_COLOR)
        canvas.bloom()
