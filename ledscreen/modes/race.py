import random
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

"""Top-down racer: a randomly-winding road scrolls toward the viewer and an
AI driver tries to stay on it. Like Pong's AI, it has real lapses in
attention - on a sharp curve during a lapse it can genuinely run off the
road, which ends the race and starts a fresh one."""

STEP_INTERVAL = 0.1  # one simulation tick = one new track row

ROAD_WIDTH = 20
EDGE_COLOR = (230, 210, 60)
DASH_COLOR = (150, 150, 160)
CAR_COLOR = (230, 60, 40)
CRASH_COLOR = (255, 255, 255)

MAX_CURVE_VEL = 0.9  # px of center-drift per row
CURVE_ACCEL = 0.25

MAX_STEER_SPEED = 16.0  # px/sec
STEER_RESPONSIVENESS = 0.35  # how quickly car_vx approaches its target each tick
LAPSE_CHANCE = 0.03  # per tick
LAPSE_DURATION = (0.3, 0.9)
CRASH_GRACE = 0.3  # seconds continuously off-road before it counts as a crash
CRASH_FLASH_DURATION = 0.6

CAR_ROW_FROM_BOTTOM = 7


class RaceMode(Mode):
    name = "race"

    def __init__(self):
        self._centers: list[float] = []
        self._curve_vel = 0.0
        self._car_x = 0.0
        self._car_vx = 0.0
        self._lapse = 0.0
        self._offroad_time = 0.0
        self._crash_flash = 0.0
        self._last_step: datetime | None = None
        self._w = self._h = 0
        self._car_row = 0

    def reset(self) -> None:
        self._centers = []
        self._last_step = None

    def _margin(self) -> float:
        return ROAD_WIDTH / 2 + 2

    def _init(self, canvas: Canvas) -> None:
        self._w, self._h = canvas.width, canvas.height
        self._car_row = self._h - CAR_ROW_FROM_BOTTOM
        self._reset_race()

    def _reset_race(self) -> None:
        start = self._w / 2
        self._centers = [start for _ in range(self._h)]
        self._curve_vel = 0.0
        self._car_x = start
        self._car_vx = 0.0
        self._lapse = 0.0
        self._offroad_time = 0.0
        self._crash_flash = 0.0

    def _next_center(self, prev: float) -> float:
        self._curve_vel += random.uniform(-CURVE_ACCEL, CURVE_ACCEL)
        self._curve_vel = max(-MAX_CURVE_VEL, min(MAX_CURVE_VEL, self._curve_vel))
        new = prev + self._curve_vel
        margin = self._margin()
        if new < margin:
            new = margin
            self._curve_vel = abs(self._curve_vel)
        elif new > self._w - margin:
            new = self._w - margin
            self._curve_vel = -abs(self._curve_vel)
        return new

    def _step(self) -> None:
        if self._crash_flash > 0:
            self._crash_flash -= STEP_INTERVAL
            if self._crash_flash <= 0:
                self._reset_race()
            return

        # scroll the road one row toward the viewer
        self._centers.pop()
        self._centers.insert(0, self._next_center(self._centers[0]))

        target = self._centers[self._car_row]
        if self._lapse > 0:
            self._lapse -= STEP_INTERVAL
        elif random.random() < LAPSE_CHANCE:
            self._lapse = random.uniform(*LAPSE_DURATION)
        else:
            desired_vx = max(-MAX_STEER_SPEED, min(MAX_STEER_SPEED, (target - self._car_x) * 2.0))
            self._car_vx += (desired_vx - self._car_vx) * STEER_RESPONSIVENESS

        self._car_x += self._car_vx * STEP_INTERVAL
        self._car_x = max(1.0, min(self._w - 1.0, self._car_x))

        road_left = target - ROAD_WIDTH / 2
        road_right = target + ROAD_WIDTH / 2
        if self._car_x < road_left or self._car_x > road_right:
            self._offroad_time += STEP_INTERVAL
            if self._offroad_time > CRASH_GRACE:
                self._crash_flash = CRASH_FLASH_DURATION
        else:
            self._offroad_time = 0.0

    def render(self, canvas: Canvas, now: datetime) -> None:
        if not self._centers or self._last_step is None:
            self._init(canvas)
            self._last_step = now

        if (now - self._last_step).total_seconds() >= STEP_INTERVAL:
            self._last_step = now
            self._step()

        canvas.clear((0, 0, 0))
        for y in range(self._h):
            center = self._centers[y]
            left = int(center - ROAD_WIDTH / 2)
            right = int(center + ROAD_WIDTH / 2)
            if 0 <= left < self._w:
                canvas.set_pixel(left, y, EDGE_COLOR)
            if 0 <= right < self._w:
                canvas.set_pixel(right, y, EDGE_COLOR)
            if y % 4 < 2:
                cx = int(center)
                if 0 <= cx < self._w:
                    canvas.set_pixel(cx, y, DASH_COLOR)

        if self._crash_flash > 0:
            flash_on = int(self._crash_flash / STEP_INTERVAL) % 2 == 0
            color = CRASH_COLOR if flash_on else CAR_COLOR
            canvas.draw_dot(self._car_x, self._car_row, 1.6, color)
        else:
            tail_x = self._car_x - self._car_vx * 0.03
            dim = tuple(c // 3 for c in CAR_COLOR)
            canvas.draw_dot(tail_x, self._car_row + 1, 0.7, dim)
            canvas.draw_dot(self._car_x, self._car_row, 1.1, CAR_COLOR)

        canvas.bloom()
