import random
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

"""Wa-Tor: a classic predator/prey cellular automaton (fish + sharks on a
toroidal grid). Produces genuine boom/bust population waves - never settles
into a repeating loop the way simpler automata can.
"""

STEP_INTERVAL = 0.12
FISH_BREED_TIME = 6
SHARK_BREED_TIME = 10
SHARK_START_ENERGY = 8
SHARK_ENERGY_GAIN = 5

FISH_COLOR = (60, 210, 70)
SHARK_COLOR = (230, 60, 40)


class EcosystemMode(Mode):
    name = "ecosystem"

    def __init__(self):
        self._grid: list[list[dict | None]] = []
        self._w = self._h = 0
        self._last_step: datetime | None = None
        self._empty_streak = 0

    def reset(self) -> None:
        self._grid = []
        self._last_step = None
        self._empty_streak = 0

    def _seed(self, canvas: Canvas) -> None:
        self._w, self._h = canvas.width, canvas.height
        self._grid = [[None for _ in range(self._w)] for _ in range(self._h)]
        for y in range(self._h):
            for x in range(self._w):
                r = random.random()
                if r < 0.22:
                    self._grid[y][x] = {"kind": "fish", "breed": random.randint(0, FISH_BREED_TIME)}
                elif r < 0.27:
                    self._grid[y][x] = {
                        "kind": "shark",
                        "breed": random.randint(0, SHARK_BREED_TIME),
                        "energy": SHARK_START_ENERGY,
                    }
        self._empty_streak = 0

    def _neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        return [
            ((x + 1) % self._w, y),
            ((x - 1) % self._w, y),
            (x, (y + 1) % self._h),
            (x, (y - 1) % self._h),
        ]

    def _step(self) -> tuple[int, int]:
        processed: set[tuple[int, int]] = set()
        coords = [(x, y) for y in range(self._h) for x in range(self._w)]
        random.shuffle(coords)

        for (x, y) in coords:
            if (x, y) in processed:
                continue
            cell = self._grid[y][x]
            if cell is None:
                continue

            neighbors = self._neighbors(x, y)
            random.shuffle(neighbors)

            if cell["kind"] == "fish":
                empties = [(nx, ny) for nx, ny in neighbors if self._grid[ny][nx] is None]
                if empties:
                    nx, ny = empties[0]
                    bred = cell["breed"] >= FISH_BREED_TIME
                    self._grid[y][x] = {"kind": "fish", "breed": 0} if bred else None
                    self._grid[ny][nx] = {"kind": "fish", "breed": 0 if bred else cell["breed"] + 1}
                    processed.add((nx, ny))
                    if bred:
                        processed.add((x, y))
                else:
                    cell["breed"] += 1
                    processed.add((x, y))
            else:  # shark
                cell["energy"] -= 1
                if cell["energy"] <= 0:
                    self._grid[y][x] = None
                    continue
                prey = [(nx, ny) for nx, ny in neighbors if self._grid[ny][nx] and self._grid[ny][nx]["kind"] == "fish"]
                empties = [(nx, ny) for nx, ny in neighbors if self._grid[ny][nx] is None]
                target = prey[0] if prey else (empties[0] if empties else None)
                if target is None:
                    processed.add((x, y))
                    continue
                nx, ny = target
                ate = target in prey
                bred = cell["breed"] >= SHARK_BREED_TIME
                new_energy = cell["energy"] + (SHARK_ENERGY_GAIN if ate else 0)
                self._grid[y][x] = (
                    {"kind": "shark", "breed": 0, "energy": SHARK_START_ENERGY} if bred else None
                )
                self._grid[ny][nx] = {
                    "kind": "shark",
                    "breed": 0 if bred else cell["breed"] + 1,
                    "energy": new_energy,
                }
                processed.add((nx, ny))
                if bred:
                    processed.add((x, y))

        fish = sharks = 0
        for row in self._grid:
            for cell in row:
                if cell is None:
                    continue
                if cell["kind"] == "fish":
                    fish += 1
                else:
                    sharks += 1
        return fish, sharks

    def render(self, canvas: Canvas, now: datetime) -> None:
        if not self._grid or self._last_step is None:
            self._seed(canvas)
            self._last_step = now

        if (now - self._last_step).total_seconds() >= STEP_INTERVAL:
            self._last_step = now
            fish, sharks = self._step()
            fill_ratio = (fish + sharks) / (self._w * self._h)
            if (fish == 0 and sharks == 0) or (sharks == 0 and fill_ratio > 0.9):
                self._empty_streak += 1
            else:
                self._empty_streak = 0
            if self._empty_streak > 15:
                self._seed(canvas)

        canvas.clear((0, 0, 0))
        for y in range(self._h):
            for x in range(self._w):
                cell = self._grid[y][x]
                if cell is None:
                    continue
                canvas.set_pixel(x, y, FISH_COLOR if cell["kind"] == "fish" else SHARK_COLOR)
        canvas.bloom()
