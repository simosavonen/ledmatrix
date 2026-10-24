import random
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

"""Top-down racer, simplified to a single winding spline instead of a
painted road: the car sits off to one side so you can see the road curving
ahead of it, driving left-to-right for a while, then turning around and
driving right-to-left, forever. An AI driver tries to track the line, with
real attention lapses - a lapse during a sharp curve can genuinely run the
car off the line, which ends the leg and starts a fresh one."""

STEP_INTERVAL = 0.05  # one simulation tick = one new spline column - fast, arcade pace
ROAD_DOT_RADIUS = 0.9  # a touch wider than a hairline

ROAD_COLOR = (90, 160, 230)
CAR_COLOR = (230, 60, 40)
CRASH_COLOR = (255, 255, 255)

MAX_CURVE_VEL = 0.9  # px of line-drift per column
CURVE_ACCEL = 0.25

MAX_STEER_SPEED = 50.0  # px/sec, vertical
STEER_RESPONSIVENESS = 0.5
# Proportional gain on position error. Needs to be high enough that normal
# tracking lag alone (not just lapses) stays well under TOLERANCE even at
# the curve's max drift rate (MAX_CURVE_VEL / STEP_INTERVAL px/sec) - a
# steady-state P-controller lags its target by roughly (target speed / gain).
STEER_GAIN = 10.0
# Per-tick, not per-second - rescaled down from the old slower tick rate so
# lapses still happen about as often in real time (roughly one every ~4s).
LAPSE_CHANCE = 0.012
LAPSE_DURATION = (0.3, 0.9)
TOLERANCE = 4.0  # px the car may drift from the line before it's "off"
CRASH_GRACE = 0.3
CRASH_FLASH_DURATION = 0.6

CAR_EDGE_MARGIN = 14  # how far from the leading-opposite edge the car sits
LEG_DURATION = (8.0, 15.0)  # seconds driving one way before turning around
CAR_EASE = 0.2  # how quickly the car slides to its new side when turning around


class RaceMode(Mode):
    name = "race"

    def __init__(self):
        self._spline: list[float] = []
        self._curve_vel = 0.0
        self._direction = 1  # +1 = driving left-to-right, -1 = right-to-left
        self._car_x = 0.0
        self._car_y = 0.0
        self._car_vy = 0.0
        self._lapse = 0.0
        self._off_time = 0.0
        self._crash_flash = 0.0
        self._leg_timer = 0.0
        self._last_step: datetime | None = None
        self._w = self._h = 0

    def reset(self) -> None:
        self._spline = []
        self._last_step = None

    def _margin(self) -> float:
        return 4.0

    def _init(self, canvas: Canvas) -> None:
        self._w, self._h = canvas.width, canvas.height
        self._direction = random.choice([1, -1])
        self._car_x = self._target_car_x()
        self._new_leg()

    def _target_car_x(self) -> float:
        return CAR_EDGE_MARGIN if self._direction == 1 else self._w - CAR_EDGE_MARGIN

    def _new_leg(self) -> None:
        mid = self._h / 2
        self._spline = [mid for _ in range(self._w)]
        self._curve_vel = 0.0
        self._car_y = mid
        self._car_vy = 0.0
        self._lapse = 0.0
        self._off_time = 0.0
        self._crash_flash = 0.0
        self._leg_timer = random.uniform(*LEG_DURATION)

    def _next_value(self, prev: float) -> float:
        self._curve_vel += random.uniform(-CURVE_ACCEL, CURVE_ACCEL)
        self._curve_vel = max(-MAX_CURVE_VEL, min(MAX_CURVE_VEL, self._curve_vel))
        new = prev + self._curve_vel
        margin = self._margin()
        if new < margin:
            new = margin
            self._curve_vel = abs(self._curve_vel)
        elif new > self._h - margin:
            new = self._h - margin
            self._curve_vel = -abs(self._curve_vel)
        return new

    def _car_column(self) -> int:
        return max(0, min(self._w - 1, int(round(self._car_x))))

    def _step(self) -> None:
        if self._crash_flash > 0:
            self._crash_flash -= STEP_INTERVAL
            if self._crash_flash <= 0:
                self._new_leg()
            return

        self._leg_timer -= STEP_INTERVAL
        if self._leg_timer <= 0:
            self._direction *= -1
            self._leg_timer = random.uniform(*LEG_DURATION)

        # scroll the spline one column in the direction of travel: new track
        # appears at the leading edge, old track exits behind the car
        if self._direction == 1:
            self._spline.pop(0)
            self._spline.append(self._next_value(self._spline[-1]))
        else:
            self._spline.pop()
            self._spline.insert(0, self._next_value(self._spline[0]))

        self._car_x += (self._target_car_x() - self._car_x) * CAR_EASE

        target = self._spline[self._car_column()]
        if self._lapse > 0:
            self._lapse -= STEP_INTERVAL
        elif random.random() < LAPSE_CHANCE:
            self._lapse = random.uniform(*LAPSE_DURATION)
        else:
            desired_vy = max(-MAX_STEER_SPEED, min(MAX_STEER_SPEED, (target - self._car_y) * STEER_GAIN))
            self._car_vy += (desired_vy - self._car_vy) * STEER_RESPONSIVENESS

        self._car_y += self._car_vy * STEP_INTERVAL
        self._car_y = max(1.0, min(self._h - 1.0, self._car_y))

        if abs(self._car_y - target) > TOLERANCE:
            self._off_time += STEP_INTERVAL
            if self._off_time > CRASH_GRACE:
                self._crash_flash = CRASH_FLASH_DURATION
        else:
            self._off_time = 0.0

    def render(self, canvas: Canvas, now: datetime) -> None:
        if not self._spline or self._last_step is None:
            self._init(canvas)
            self._last_step = now

        if (now - self._last_step).total_seconds() >= STEP_INTERVAL:
            self._last_step = now
            self._step()

        canvas.clear((0, 0, 0))
        for x in range(self._w):
            canvas.draw_dot(x, self._spline[x], ROAD_DOT_RADIUS, ROAD_COLOR)

        if self._crash_flash > 0:
            flash_on = int(self._crash_flash / STEP_INTERVAL) % 2 == 0
            color = CRASH_COLOR if flash_on else CAR_COLOR
            canvas.draw_dot(self._car_x, self._car_y, 1.6, color)
        else:
            tail_x = self._car_x - self._direction * 2.5
            dim = tuple(c // 3 for c in CAR_COLOR)
            canvas.draw_dot(tail_x, self._car_y, 0.7, dim)
            canvas.draw_dot(self._car_x, self._car_y, 1.1, CAR_COLOR)

        canvas.bloom()
