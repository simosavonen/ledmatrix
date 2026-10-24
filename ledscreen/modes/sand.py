import random
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

"""Falling-sand physics toy: water drizzles in steadily everywhere, while
sand only arrives in bucket-sized pours - a steady stream from one random
spot for a few seconds, then nothing for a while - so it piles into
mounds and displaces the water pooled underneath instead of raining
down uniformly."""

STEP_INTERVAL = 0.04
FILL_CLEAR_THRESHOLD = 0.85
FILL_CHECK_EVERY = 20

WATER_SPAWN_CHANCE = 0.5  # chance per step of one new water drop somewhere random

POUR_DURATION_STEPS = (40, 100)  # ~1.6-4s of active pouring
POUR_GAP_STEPS = (75, 225)  # ~3-9s of no sand between pours
POUR_RATE = 2  # sand grains attempted per step while a pour is active
POUR_SPREAD = 1  # pour wanders +-1 column around its center, like a loose stream

PLATFORM_COUNT = (2, 3)
PLATFORM_WIDTH = (10, 22)

SAND_COLOR = (210, 170, 80)
WATER_COLOR = (40, 130, 230)
PLATFORM_COLOR = (95, 85, 80)


class SandMode(Mode):
    name = "sand"

    def __init__(self):
        self._grid: list[list[str | None]] = []
        self._w = self._h = 0
        self._last_step: datetime | None = None
        self._steps_since_check = 0
        self._pour_x: int | None = None
        self._pour_remaining = 0
        self._next_pour_in = 0

    def reset(self) -> None:
        self._grid = []
        self._last_step = None
        self._steps_since_check = 0
        self._pour_x = None
        self._pour_remaining = 0
        self._next_pour_in = 0

    def _init(self, canvas: Canvas) -> None:
        self._w, self._h = canvas.width, canvas.height
        self._grid = [[None for _ in range(self._w)] for _ in range(self._h)]
        self._seed_platforms()
        self._pour_remaining = 0
        self._next_pour_in = random.randint(10, 50)  # a pour starts soon after reset, not after a long wait

    def _seed_platforms(self) -> None:
        # Fixed, immovable ledges for sand and water to pile on and spill
        # off of - a few random ones each round, kept clear of the spawn
        # row up top and with room below to pile up before overflowing.
        count = random.randint(*PLATFORM_COUNT)
        for _ in range(count):
            width = random.randint(*PLATFORM_WIDTH)
            x0 = random.randint(0, max(0, self._w - width))
            y = random.randint(self._h // 3, self._h - 4)
            for x in range(x0, min(self._w, x0 + width)):
                self._grid[y][x] = "platform"

    def _empty(self, x: int, y: int) -> bool:
        if x < 0 or x >= self._w or y < 0 or y >= self._h:
            return False
        return self._grid[y][x] is None

    def _can_enter(self, x: int, y: int, material: str) -> bool:
        if x < 0 or x >= self._w or y < 0 or y >= self._h:
            return False
        target = self._grid[y][x]
        if target is None:
            return True
        # Sand is denser than water: it sinks through and displaces it,
        # which is what makes water end up settling on top over time.
        return material == "sand" and target == "water"

    def _move_target(self, x: int, y: int, material: str) -> tuple[int, int]:
        down = (x, y + 1)
        diag = [(x - 1, y + 1), (x + 1, y + 1)]
        random.shuffle(diag)

        if self._can_enter(*down, material):
            return down
        for d in diag:
            if self._can_enter(*d, material):
                return d
        if material == "water":
            side = [(x - 1, y), (x + 1, y)]
            random.shuffle(side)
            for s in side:
                if self._empty(*s):
                    return s
        return (x, y)

    def _spawn(self) -> None:
        if random.random() < WATER_SPAWN_CHANCE:
            x = random.randrange(self._w)
            if self._grid[0][x] is None:
                self._grid[0][x] = "water"

        if self._pour_remaining > 0:
            self._pour_remaining -= 1
            for _ in range(POUR_RATE):
                x = self._pour_x + random.randint(-POUR_SPREAD, POUR_SPREAD)
                if 0 <= x < self._w and self._grid[0][x] is None:
                    self._grid[0][x] = "sand"
            if self._pour_remaining == 0:
                self._next_pour_in = random.randint(*POUR_GAP_STEPS)
        else:
            self._next_pour_in -= 1
            if self._next_pour_in <= 0:
                self._pour_x = random.randrange(POUR_SPREAD, self._w - POUR_SPREAD)
                self._pour_remaining = random.randint(*POUR_DURATION_STEPS)

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
                if material is None or material == "platform":
                    continue
                nx, ny = self._move_target(x, y, material)
                if (nx, ny) != (x, y):
                    displaced = self._grid[ny][nx]  # None, or water being sunk through
                    self._grid[ny][nx] = material
                    self._grid[y][x] = displaced
                    moved.add((nx, ny))
                    if displaced is not None:
                        moved.add((x, y))
                else:
                    moved.add((x, y))

        self._steps_since_check += 1
        if self._steps_since_check >= FILL_CHECK_EVERY:
            self._steps_since_check = 0
            filled = sum(1 for row in self._grid for c in row if c is not None)
            if filled / (self._w * self._h) > FILL_CLEAR_THRESHOLD:
                self._grid = [[None for _ in range(self._w)] for _ in range(self._h)]
                self._seed_platforms()
                self._pour_remaining = 0
                self._next_pour_in = random.randint(10, 50)

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
                elif material == "platform":
                    canvas.set_pixel(x, y, PLATFORM_COLOR)
        canvas.bloom()
