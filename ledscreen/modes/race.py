import math
import random
from collections import deque
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

"""Race mode, step 2: a random undulating closed-loop track. The car
tries to stay on the road while driving as fast as it can - steering to
match the road's direction while correcting any sideways drift back
toward the centerline, and braking in advance for whatever sharp bend
is coming up next. If it runs off the road anyway it spins out and
brakes to a stop, then resumes the same way as before by steering back
toward the track's direction at wherever it ended up."""

BODY_COLOR = (230, 60, 40)
NOSE_COLOR = (255, 240, 200)
TAIL_COLOR = (120, 20, 15)
CRASH_COLOR = (255, 170, 40)
TRACK_EDGE_COLOR = (55, 62, 75)

CAR_WIDTH = 3.6  # roughly how wide the car sprite reads visually
TRACK_WIDTH = CAR_WIDTH * 2.6
TRACK_HALF_WIDTH = TRACK_WIDTH / 2

TRACK_POINTS = 480
TRACK_BASE_RADIUS = 70.0
TRACK_HARMONICS = [(2, 0.20), (3, 0.14), (5, 0.09)]  # (frequency, amplitude fraction)

MAX_SPEED = 42.0
ACCEL = 42.0
BRAKE = 70.0
STOP_SPEED = 1.5
MIN_SPEED_ABS = 10.0

CURVATURE_SAMPLE = 12  # point offset used to estimate local track curvature
LAT_ACCEL_MAX = 95.0  # how hard the car can corner before it should be braking instead

MAX_TURN_RATE = 3.4  # rad/sec, how sharply the car can steer
STANLEY_GAIN = 2.2  # how hard it corrects sideways drift back toward the centerline
STANLEY_SPEED_EPS = 4.0

LAPSE_CHANCE = 0.0035  # per tick, chance of a momentary steering slip starting
LAPSE_DURATION = (0.25, 0.5)
LAPSE_MAGNITUDE = (0.15, 0.35)  # radians of sustained bad steering while lapsing

REACTION_DELAY = 0.12  # seconds between the road changing and the driver responding to it

PROGRESS_WINDOW = 60

OFFTRACK_GRIP_K = 0.1  # losing grip once off the paved surface - the further off, the slower
OFFTRACK_MIN_FRAC = 0.45

CRASH_LATERAL_MULT = 2.2  # how far past the track edge counts as a real crash, not just running wide
CRASH_SPIN_RATE = (4.0, 7.0)
CRASH_FRICTION = 45.0
CRASH_TRIGGER_MIN_SPEED = 5.0  # a near-stopped car just steers back, it doesn't "spin out"

LOOKAHEAD_TIME = 0.55  # camera lookahead, from step 1
MAX_LOOKAHEAD_VERTICAL = 14.0
MAX_LOOKAHEAD_HORIZONTAL = 26.0  # the screen is wider than it is tall, so look further ahead when driving sideways
CAMERA_GAIN = 4.0

STATE_DRIVE = "drive"
STATE_CRASH = "crash"


def _angle_diff(a: float, b: float) -> float:
    d = (a - b) % (2 * math.pi)
    if d > math.pi:
        d -= 2 * math.pi
    return d


class RaceMode(Mode):
    name = "race"

    def __init__(self):
        self._track: list[tuple[float, float]] = []
        self._tangent: list[tuple[float, float]] = []
        self._normal: list[tuple[float, float]] = []
        self._curve_radius: list[float] = []
        self._avg_spacing = 1.0
        self._car_x = 0.0
        self._car_y = 0.0
        self._speed = 0.0
        self._heading = 0.0
        self._cam_x = 0.0
        self._cam_y = 0.0
        self._state = STATE_DRIVE
        self._progress_idx = 0
        self._spin_rate = 0.0
        self._crash_flash = 0.0
        self._lapse_timer = 0.0
        self._lapse_offset = 0.0
        self._sim_time = 0.0
        self._heading_history: deque[tuple[float, float]] = deque()
        self._last_time: datetime | None = None

    def reset(self) -> None:
        self._last_time = None

    def _build_track(self) -> None:
        harmonics = [(freq, amp, random.uniform(0, 2 * math.pi)) for freq, amp in TRACK_HARMONICS]
        track = []
        for i in range(TRACK_POINTS):
            theta = i / TRACK_POINTS * 2 * math.pi
            radius = TRACK_BASE_RADIUS
            for freq, amp_frac, phase in harmonics:
                radius += TRACK_BASE_RADIUS * amp_frac * math.sin(freq * theta + phase)
            track.append((radius * math.cos(theta), radius * math.sin(theta)))
        self._track = track

        n = len(track)
        tangent, normal, curve_radius = [], [], []
        spacing_total = 0.0
        for i in range(n):
            ax, ay = track[(i - CURVATURE_SAMPLE) % n]
            bx, by = track[i]
            cx, cy = track[(i + CURVATURE_SAMPLE) % n]
            tx, ty = cx - ax, cy - ay
            tlen = math.hypot(tx, ty) or 1.0
            tx, ty = tx / tlen, ty / tlen
            tangent.append((tx, ty))
            normal.append((-ty, tx))
            ab = math.hypot(bx - ax, by - ay)
            bc = math.hypot(cx - bx, cy - by)
            ca = math.hypot(ax - cx, ay - cy)
            area2 = abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))
            curve_radius.append((ab * bc * ca) / (2 * area2) if area2 > 1e-6 else 10000.0)
            nx_, ny_ = track[(i + 1) % n]
            spacing_total += math.hypot(nx_ - bx, ny_ - by)
        self._tangent = tangent
        self._normal = normal
        self._curve_radius = curve_radius
        self._avg_spacing = spacing_total / n

    def _init(self) -> None:
        self._build_track()
        start_x, start_y = self._track[0]
        next_x, next_y = self._track[1]
        self._car_x, self._car_y = start_x, start_y
        self._heading = math.atan2(next_y - start_y, next_x - start_x)
        self._speed = 0.0
        self._cam_x, self._cam_y = self._car_x, self._car_y
        self._state = STATE_DRIVE
        self._progress_idx = 0
        self._spin_rate = 0.0
        self._crash_flash = 0.0
        self._lapse_timer = 0.0
        self._lapse_offset = 0.0
        self._sim_time = 0.0
        self._heading_history.clear()

    def _nearest_track_idx(self) -> tuple[int, float]:
        n = len(self._track)
        best_idx = self._progress_idx
        best_dist_sq = float("inf")
        for offset in range(-PROGRESS_WINDOW, PROGRESS_WINDOW + 1):
            idx = (self._progress_idx + offset) % n
            px, py = self._track[idx]
            dist_sq = (px - self._car_x) ** 2 + (py - self._car_y) ** 2
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_idx = idx
        return best_idx, math.sqrt(best_dist_sq)

    def _update(self, dt: float) -> None:
        n = len(self._track)
        idx, lateral_dist = self._nearest_track_idx()
        self._progress_idx = idx

        if (
            self._state == STATE_DRIVE
            and lateral_dist > TRACK_HALF_WIDTH * CRASH_LATERAL_MULT
            and self._speed > CRASH_TRIGGER_MIN_SPEED
        ):
            self._state = STATE_CRASH
            self._spin_rate = random.uniform(*CRASH_SPIN_RATE) * random.choice((-1, 1))
            self._crash_flash = 0.5

        if self._state == STATE_DRIVE:
            if self._lapse_timer > 0:
                self._lapse_timer -= dt
            else:
                self._lapse_offset = 0.0
                if random.random() < LAPSE_CHANCE:
                    self._lapse_timer = random.uniform(*LAPSE_DURATION)
                    self._lapse_offset = random.uniform(*LAPSE_MAGNITUDE) * random.choice((-1, 1))

            tx, ty = self._tangent[idx]
            nx, ny = self._normal[idx]
            px, py = self._track[idx]
            cross_track = (self._car_x - px) * nx + (self._car_y - py) * ny
            tangent_heading = math.atan2(ty, tx)
            correction = math.atan2(STANLEY_GAIN * cross_track, self._speed + STANLEY_SPEED_EPS)
            raw_desired_heading = tangent_heading - correction + self._lapse_offset

            # The driver reacts to what the road looked like a beat ago, not
            # to its current state - so it clips corners and drifts wide
            # instead of tracking the centerline perfectly.
            self._sim_time += dt
            self._heading_history.append((self._sim_time, raw_desired_heading))
            desired_heading = raw_desired_heading
            while self._heading_history and self._heading_history[0][0] <= self._sim_time - REACTION_DELAY:
                desired_heading = self._heading_history.popleft()[1]

            heading_error = _angle_diff(desired_heading, self._heading)
            max_turn = MAX_TURN_RATE * dt
            self._heading += max(-max_turn, min(max_turn, heading_error))

            brake_lookahead = self._speed**2 / (2 * BRAKE) + 4.0
            lookahead_points = max(1, min(40, int(brake_lookahead / self._avg_spacing)))
            min_radius = min(self._curve_radius[(idx + j) % n] for j in range(lookahead_points + 1))
            target_speed = max(MIN_SPEED_ABS, min(MAX_SPEED, math.sqrt(LAT_ACCEL_MAX * min_radius)))

            off_track = max(0.0, lateral_dist - TRACK_HALF_WIDTH)
            grip_penalty = max(OFFTRACK_MIN_FRAC, 1 - OFFTRACK_GRIP_K * off_track)
            target_speed *= grip_penalty
            if self._speed < target_speed:
                self._speed = min(target_speed, self._speed + ACCEL * dt)
            else:
                self._speed = max(target_speed, self._speed - BRAKE * dt)

            self._car_x += math.cos(self._heading) * self._speed * dt
            self._car_y += math.sin(self._heading) * self._speed * dt

        else:  # STATE_CRASH
            self._heading += self._spin_rate * dt
            self._crash_flash = max(0.0, self._crash_flash - dt)
            decel = min(CRASH_FRICTION * dt, self._speed)
            self._speed -= decel
            self._car_x += math.cos(self._heading) * self._speed * dt
            self._car_y += math.sin(self._heading) * self._speed * dt
            if self._speed <= STOP_SPEED:
                self._speed = 0.0
                self._state = STATE_DRIVE
                self._heading_history.clear()

        horizontalness = math.cos(self._heading) ** 2
        lookahead_cap = MAX_LOOKAHEAD_VERTICAL + (MAX_LOOKAHEAD_HORIZONTAL - MAX_LOOKAHEAD_VERTICAL) * horizontalness
        lookahead_dist = min(self._speed * LOOKAHEAD_TIME, lookahead_cap)
        focus_x = self._car_x + math.cos(self._heading) * lookahead_dist
        focus_y = self._car_y + math.sin(self._heading) * lookahead_dist
        ease = min(1.0, CAMERA_GAIN * dt)
        self._cam_x += (focus_x - self._cam_x) * ease
        self._cam_y += (focus_y - self._cam_y) * ease

    def _draw_track(self, canvas: Canvas, base_x: float, base_y: float) -> None:
        n = len(self._track)
        margin = 3
        for i in range(n):
            x, y = self._track[i]
            sx = base_x + x
            sy = base_y + y
            if sx < -margin or sx > canvas.width + margin or sy < -margin or sy > canvas.height + margin:
                continue
            nx, ny = self._normal[i]
            for side in (-1, 1):
                canvas.draw_dot(sx + nx * TRACK_HALF_WIDTH * side, sy + ny * TRACK_HALF_WIDTH * side, 0.7, TRACK_EDGE_COLOR)

    def _draw_car(self, canvas: Canvas, cx: float, cy: float) -> None:
        cos_h, sin_h = math.cos(self._heading), math.sin(self._heading)
        body_color = CRASH_COLOR if self._crash_flash > 0 else BODY_COLOR

        def to_world(lx: float, ly: float) -> tuple[float, float]:
            return (cx + lx * cos_h - ly * sin_h, cy + lx * sin_h + ly * cos_h)

        for lx in (-2.0, -1.0, 0.0, 1.0):
            for ly in (-1.0, 1.0):
                wx, wy = to_world(lx, ly)
                canvas.draw_dot(wx, wy, 0.8, body_color)
        canvas.draw_dot(*to_world(0.0, 0.0), 0.9, body_color)

        canvas.draw_dot(*to_world(2.2, 0.0), 0.8, NOSE_COLOR)
        canvas.draw_dot(*to_world(-2.0, -0.9), 0.5, TAIL_COLOR)
        canvas.draw_dot(*to_world(-2.0, 0.9), 0.5, TAIL_COLOR)

    def render(self, canvas: Canvas, now: datetime) -> None:
        if self._last_time is None or not self._track:
            self._init()
            self._last_time = now

        dt = min(max(0.0, (now - self._last_time).total_seconds()), 0.1)
        self._last_time = now
        self._update(dt)

        canvas.clear((0, 0, 0))
        base_x = canvas.width / 2 - self._cam_x
        base_y = canvas.height / 2 - self._cam_y
        self._draw_track(canvas, base_x, base_y)
        self._draw_car(canvas, base_x + self._car_x, base_y + self._car_y)
        canvas.bloom()
