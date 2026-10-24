import colorsys
import random
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

STEP_INTERVAL = 0.15  # seconds per generation
MAX_GENERATIONS = 500  # force a reseed even if still 'alive', to keep it fresh
MIN_POPULATION = 6


class LifeMode(Mode):
    """Conway's Game of Life as slowly-evolving ambient art, hue drifting over time."""

    name = "life"

    def __init__(self):
        self._grid: set[tuple[int, int]] = set()
        self._last_step: datetime | None = None
        self._generation = 0
        self._prev_grid: frozenset | None = None
        self._hue_t0: datetime | None = None

    def reset(self) -> None:
        self._grid = set()
        self._last_step = None
        self._generation = 0
        self._prev_grid = None
        self._hue_t0 = None

    def _seed(self, canvas: Canvas) -> None:
        self._grid = {
            (x, y)
            for x in range(canvas.width)
            for y in range(canvas.height)
            if random.random() < 0.25
        }
        self._generation = 0
        self._prev_grid = None

    def _step(self, canvas: Canvas) -> None:
        neighbor_counts: dict[tuple[int, int], int] = {}
        for (x, y) in self._grid:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < canvas.width and 0 <= ny < canvas.height:
                        key = (nx, ny)
                        neighbor_counts[key] = neighbor_counts.get(key, 0) + 1

        new_grid = set()
        for cell, count in neighbor_counts.items():
            if count == 3 or (count == 2 and cell in self._grid):
                new_grid.add(cell)

        self._prev_grid = frozenset(self._grid)
        self._grid = new_grid
        self._generation += 1

    def render(self, canvas: Canvas, now: datetime) -> None:
        if self._hue_t0 is None:
            self._hue_t0 = now
        if not self._grid or self._last_step is None:
            self._seed(canvas)
            self._last_step = now

        if (now - self._last_step).total_seconds() >= STEP_INTERVAL:
            self._last_step = now
            self._step(canvas)
            stagnant = self._prev_grid is not None and frozenset(self._grid) == self._prev_grid
            if (
                len(self._grid) < MIN_POPULATION
                or self._generation >= MAX_GENERATIONS
                or stagnant
            ):
                self._seed(canvas)

        hue = ((now - self._hue_t0).total_seconds() / 25.0) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
        color = (int(r * 255), int(g * 255), int(b * 255))

        canvas.clear((0, 0, 0))
        for (x, y) in self._grid:
            canvas.set_pixel(x, y, color)
        canvas.bloom()
