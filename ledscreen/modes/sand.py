import random
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

"""Falling-sand physics toy: sand and water rain in from the top, pile up,
flow around each other, and the board clears itself once it gets too full."""

STEP_INTERVAL = 0.04
FILL_CLEAR_THRESHOLD = 0.85
FILL_CHECK_EVERY = 20

SAND_COLOR = (210, 170, 80)
WATER_COLOR = (40, 130, 230)


class SandMode(Mode):
    name = "sand"

    def __init__(self):
        self._grid: list[list[str | None]] = []
        self._w = self._h = 0
        self._last_step: datetime | None = None
        self._steps_since_check = 0

    def reset(self) -> None:
        self._grid = []
        self._last_step = None
        self._steps_since_check = 0

    def _init(self, canvas: Canvas) -> None:
        self._w, self._h = canvas.width, canvas.height
        self._grid = [[None for _ in range(self._w)] for _ in range(self._h)]

    def _empty(self, x: int, y: int) -> bool:
        if x < 0 or x >= self._w or y < 0 or y >= self._h:
            return False
        return self._grid[y][x] is None

    def _move_target(self, x: int, y: int, material: str) -> tuple[int, int]:
        down = (x, y + 1)
        diag = [(x - 1, y + 1), (x + 1, y + 1)]
        random.shuffle(diag)

        if self._empty(*down):
            return down
        for d in diag:
            if self._empty(*d):
                return d
        if material == "water":
            side = [(x - 1, y), (x + 1, y)]
            random.shuffle(side)
            for s in side:
                if self._empty(*s):
                    return s
        return (x, y)

    def _spawn(self) -> None:
        for _ in range(random.randint(0, 2)):
            x = random.randrange(self._w)
            if self._grid[0][x] is None:
                self._grid[0][x] = "sand" if random.random() < 0.65 else "water"

    def _step(self) -> None:
        self._spawn()
        moved: set[tuple[int, int]] = set()
        for y in range(self._h - 1, -1, -1):
            xs = list(range(self._w))
            random.shuffle(xs)
            for x in xs:
                if (x, y) in moved:
                    continue
                material = self._grid[y][x]
                if material is None:
                    continue
                nx, ny = self._move_target(x, y, material)
                if (nx, ny) != (x, y):
                    self._grid[ny][nx] = material
                    self._grid[y][x] = None
                    moved.add((nx, ny))
                else:
                    moved.add((x, y))

        self._steps_since_check += 1
        if self._steps_since_check >= FILL_CHECK_EVERY:
            self._steps_since_check = 0
            filled = sum(1 for row in self._grid for c in row if c is not None)
            if filled / (self._w * self._h) > FILL_CLEAR_THRESHOLD:
                self._grid = [[None for _ in range(self._w)] for _ in range(self._h)]

    def render(self, canvas: Canvas, now: datetime) -> None:
        if not self._grid or self._last_step is None:
            self._init(canvas)
            self._last_step = now

        if (now - self._last_step).total_seconds() >= STEP_INTERVAL:
            self._last_step = now
            self._step()

        canvas.clear((0, 0, 0))
        for y in range(self._h):
            for x in range(self._w):
                material = self._grid[y][x]
                if material == "sand":
                    canvas.set_pixel(x, y, SAND_COLOR)
                elif material == "water":
                    canvas.set_pixel(x, y, WATER_COLOR)
