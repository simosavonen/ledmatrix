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
PLATFORM_WIDTH = (8, 24)
PLATFORM_MIN_Y_GAP = 5  # how far apart (in rows) overlapping platforms must be
PLATFORM_PLACEMENT_ATTEMPTS = 20

PLATFORM_COLOR = (95, 85, 80)

# Sunlight from above gets absorbed by whatever it passes through, so
# deeper sand/water reads as a different, darker color - not just a dimmer
# version of the surface color (real light absorption shifts hue, it
# doesn't just scale brightness - water in particular should go bluer/
# darker, not grayer). Depth is a running count of same-material cells
# above, counted in the same pass that already draws each column, and
# capped quickly since in practice most of the visible change happens
# in the first few cells, not gradually over the whole pile.
SAND_SURFACE_COLOR = (210, 170, 80)
SAND_DEEP_COLOR = (120, 90, 48)
WATER_SURFACE_COLOR = (90, 190, 255)
WATER_DEEP_COLOR = (12, 40, 85)
MAX_SHADE_DEPTH = 8
SMOOTH_RADIUS = 2  # how many neighbouring columns to blend depth across
PLATFORM_DEPTH_JUMP = 4  # a platform is opaque - a much bigger shadow than one grain


class SandMode(Mode):
    name = "sand"

    def __init__(self):
        self._grid: list[list[str | None]] = []
        self._water_dir: list[list[int]] = []  # water's current drift direction, -1/0/+1
        self._w = self._h = 0
        self._last_step: datetime | None = None
        self._steps_since_check = 0
        self._pour_x: int | None = None
        self._pour_remaining = 0
        self._next_pour_in = 0

    def reset(self) -> None:
        self._grid = []
        self._water_dir = []
        self._last_step = None
        self._steps_since_check = 0
        self._pour_x = None
        self._pour_remaining = 0
        self._next_pour_in = 0

    def _init(self, canvas: Canvas) -> None:
        self._w, self._h = canvas.width, canvas.height
        self._grid = [[None for _ in range(self._w)] for _ in range(self._h)]
        self._water_dir = [[0 for _ in range(self._w)] for _ in range(self._h)]
        self._seed_platforms()
        self._pour_remaining = 0
        self._next_pour_in = random.randint(10, 50)  # a pour starts soon after reset, not after a long wait

    def _seed_platforms(self) -> None:
        # Fixed, immovable ledges for sand and water to pile on and spill
        # off of - a few random ones each round, kept clear of the spawn
        # row up top and with room below to pile up before overflowing.
        # Retries placement to keep them spread out in both width and
        # position instead of stacking into one boring overlapping mass.
        count = random.randint(*PLATFORM_COUNT)
        placed: list[tuple[int, int, int]] = []  # (x0, x1, y)
        for _ in range(count):
            x0 = x1 = y = 0
            for _attempt in range(PLATFORM_PLACEMENT_ATTEMPTS):
                width = random.randint(*PLATFORM_WIDTH)
                x0 = random.randint(0, max(0, self._w - width))
                x1 = x0 + width
                y = random.randint(self._h // 3, self._h - 4)
                conflict = any(
                    abs(y - py) < PLATFORM_MIN_Y_GAP and x0 < px1 and x1 > px0
                    for px0, px1, py in placed
                )
                if not conflict:
                    break
            placed.append((x0, x1, y))
            for x in range(x0, min(self._w, x1)):
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

    def _move_target(self, x: int, y: int, material: str) -> tuple[tuple[int, int], int]:
        down = (x, y + 1)
        diag = [(x - 1, y + 1), (x + 1, y + 1)]
        random.shuffle(diag)

        if self._can_enter(*down, material):
            return down, 0
        for d in diag:
            if self._can_enter(*d, material):
                return d, 0
        if material == "water":
            # Keep drifting whichever way it was already going instead of
            # re-rolling a direction every single step - a flat run of water
            # should flow smoothly to one side and stop, not jitter back
            # and forth. It only picks a fresh direction once truly stuck.
            preferred = self._water_dir[y][x]
            sides = [(x - 1, y), (x + 1, y)]
            random.shuffle(sides)
            if preferred != 0:
                sides.sort(key=lambda s: 0 if s[0] - x == preferred else 1)
            for sx, sy in sides:
                if self._empty(sx, sy):
                    return (sx, sy), (1 if sx > x else -1)
        return (x, y), 0

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
                (nx, ny), new_dir = self._move_target(x, y, material)
                if (nx, ny) != (x, y):
                    displaced = self._grid[ny][nx]  # None, or water being sunk through
                    self._grid[ny][nx] = material
                    self._grid[y][x] = displaced
                    self._water_dir[y][x] = 0
                    if material == "water":
                        self._water_dir[ny][nx] = new_dir
                    moved.add((nx, ny))
                    if displaced is not None:
                        moved.add((x, y))
                else:
                    self._water_dir[y][x] = 0  # blocked both ways - come to rest, don't keep drifting
                    moved.add((x, y))

        self._steps_since_check += 1
        if self._steps_since_check >= FILL_CHECK_EVERY:
            self._steps_since_check = 0
            filled = sum(1 for row in self._grid for c in row if c is not None)
            if filled / (self._w * self._h) > FILL_CLEAR_THRESHOLD:
                self._grid = [[None for _ in range(self._w)] for _ in range(self._h)]
                self._water_dir = [[0 for _ in range(self._w)] for _ in range(self._h)]
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

        # Depth-from-the-top-of-this-exact-column is noisy: one column
        # being a single pixel "deeper" than its neighbour (one extra
        # droplet on the surface) would otherwise offset every row below
        # it by that same pixel versus the column next door, forever - a
        # hard vertical seam instead of a soft gradient. Smoothing depth
        # across a few neighbouring columns of the same material before
        # shading dilutes a lone bump instead of drawing a line with it.
        depth_grid = [[0] * self._w for _ in range(self._h)]
        for x in range(self._w):
            depth = 0
            prev_material = None
            for y in range(self._h):
                material = self._grid[y][x]
                if material != prev_material:
                    depth = 0
                prev_material = material
                if material in ("sand", "water"):
                    depth_grid[y][x] = depth
                    depth += 1
                elif material == "platform":
                    depth += PLATFORM_DEPTH_JUMP

        for y in range(self._h):
            for x in range(self._w):
                material = self._grid[y][x]
                if material == "platform":
                    canvas.set_pixel(x, y, PLATFORM_COLOR)
                    continue
                if material not in ("sand", "water"):
                    continue
                total = count = 0
                for dx in range(-SMOOTH_RADIUS, SMOOTH_RADIUS + 1):
                    nx = x + dx
                    if 0 <= nx < self._w and self._grid[y][nx] == material:
                        total += depth_grid[y][nx]
                        count += 1
                smoothed_depth = total / count if count else depth_grid[y][x]
                if material == "sand":
                    canvas.set_pixel(x, y, self._shaded(SAND_SURFACE_COLOR, SAND_DEEP_COLOR, smoothed_depth))
                else:
                    canvas.set_pixel(x, y, self._shaded(WATER_SURFACE_COLOR, WATER_DEEP_COLOR, smoothed_depth))

        canvas.bloom()

    def _shaded(
        self, surface_color: tuple[int, int, int], deep_color: tuple[int, int, int], depth: int
    ) -> tuple[int, int, int]:
        t = min(1.0, depth / MAX_SHADE_DEPTH)
        return tuple(round(s + (d - s) * t) for s, d in zip(surface_color, deep_color))
