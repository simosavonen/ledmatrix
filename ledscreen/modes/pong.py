import random
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

"""Two AI paddles play Pong forever. Paddles have limited speed and
occasional lapses in attention, so points - and misses - happen for real."""

PADDLE_HEIGHT = 7
PADDLE_WIDTH = 2
PADDLE_SPEED = 28.0
PADDLE_X_LEFT = 2
PADDLE_X_RIGHT = 60
BALL_SPEED_START = 20.0
BALL_SPEED_MAX = 42.0
BALL_RADIUS = 1.0

LEFT_COLOR = (70, 210, 230)
RIGHT_COLOR = (230, 80, 190)
BALL_COLOR = (255, 255, 255)


class PongMode(Mode):
    name = "pong"

    def __init__(self):
        self._state: dict | None = None
        self._last_time: datetime | None = None

    def reset(self) -> None:
        self._state = None
        self._last_time = None

    def _new_rally(self, canvas: Canvas, serve_dir: int = 0) -> None:
        s = self._state
        s["ball_x"] = canvas.width / 2
        s["ball_y"] = canvas.height / 2
        angle = random.uniform(-0.5, 0.5)
        direction = serve_dir or random.choice([-1, 1])
        s["ball_vx"] = direction * BALL_SPEED_START
        s["ball_vy"] = angle * BALL_SPEED_START

    def _seed(self, canvas: Canvas) -> None:
        self._state = {
            "left_y": canvas.height / 2 - PADDLE_HEIGHT / 2,
            "right_y": canvas.height / 2 - PADDLE_HEIGHT / 2,
            "left_score": 0,
            "right_score": 0,
            "left_lapse": 0.0,
            "right_lapse": 0.0,
        }
        self._new_rally(canvas)

    def _ai_track(self, paddle_y: float, ball_y: float, lapse: float, dt: float) -> tuple[float, float]:
        if lapse > 0:
            lapse -= dt
            return paddle_y, lapse
        if random.random() < 0.01:
            return paddle_y, 0.5  # brief lapse in concentration
        center = paddle_y + PADDLE_HEIGHT / 2
        if abs(center - ball_y) < 1.0:
            return paddle_y, lapse
        step = PADDLE_SPEED * dt
        if center < ball_y:
            paddle_y += step
        else:
            paddle_y -= step
        return paddle_y, lapse

    def render(self, canvas: Canvas, now: datetime) -> None:
        if self._state is None or self._last_time is None:
            self._seed(canvas)
            self._last_time = now

        dt = min(max(0.0, (now - self._last_time).total_seconds()), 0.2)
        self._last_time = now
        s = self._state

        s["left_y"], s["left_lapse"] = self._ai_track(s["left_y"], s["ball_y"], s["left_lapse"], dt)
        s["right_y"], s["right_lapse"] = self._ai_track(s["right_y"], s["ball_y"], s["right_lapse"], dt)
        s["left_y"] = min(max(s["left_y"], 0), canvas.height - PADDLE_HEIGHT)
        s["right_y"] = min(max(s["right_y"], 0), canvas.height - PADDLE_HEIGHT)

        s["ball_x"] += s["ball_vx"] * dt
        s["ball_y"] += s["ball_vy"] * dt

        if s["ball_y"] <= 0:
            s["ball_y"] = 0
            s["ball_vy"] *= -1
        elif s["ball_y"] >= canvas.height - 1:
            s["ball_y"] = canvas.height - 1
            s["ball_vy"] *= -1

        if s["ball_vx"] < 0 and s["ball_x"] <= PADDLE_X_LEFT + 1:
            if s["left_y"] - 1 <= s["ball_y"] <= s["left_y"] + PADDLE_HEIGHT + 1:
                offset = (s["ball_y"] - (s["left_y"] + PADDLE_HEIGHT / 2)) / (PADDLE_HEIGHT / 2)
                speed = min(abs(s["ball_vx"]) * 1.08, BALL_SPEED_MAX)
                s["ball_vx"] = speed
                s["ball_vy"] = offset * speed * 0.6
                s["ball_x"] = PADDLE_X_LEFT + PADDLE_WIDTH  # never leave it past the paddle
        elif s["ball_vx"] > 0 and s["ball_x"] >= PADDLE_X_RIGHT - 1:
            if s["right_y"] - 1 <= s["ball_y"] <= s["right_y"] + PADDLE_HEIGHT + 1:
                offset = (s["ball_y"] - (s["right_y"] + PADDLE_HEIGHT / 2)) / (PADDLE_HEIGHT / 2)
                speed = min(abs(s["ball_vx"]) * 1.08, BALL_SPEED_MAX)
                s["ball_vx"] = -speed
                s["ball_vy"] = offset * speed * 0.6
                s["ball_x"] = PADDLE_X_RIGHT - 1  # never leave it past the paddle

        if s["ball_x"] < 0:
            s["right_score"] = (s["right_score"] + 1) % 10
            self._new_rally(canvas, serve_dir=1)
        elif s["ball_x"] > canvas.width:
            s["left_score"] = (s["left_score"] + 1) % 10
            self._new_rally(canvas, serve_dir=-1)

        canvas.clear((0, 0, 0))
        canvas.draw_vbar_aa(PADDLE_X_LEFT, PADDLE_WIDTH, s["left_y"], s["left_y"] + PADDLE_HEIGHT, LEFT_COLOR)
        canvas.draw_vbar_aa(PADDLE_X_RIGHT, PADDLE_WIDTH, s["right_y"], s["right_y"] + PADDLE_HEIGHT, RIGHT_COLOR)
        canvas.draw_dot(s["ball_x"], s["ball_y"], BALL_RADIUS, BALL_COLOR)
        canvas.draw_text(8, 1, str(s["left_score"]), LEFT_COLOR, scale=1)
        canvas.draw_text(canvas.width - 13, 1, str(s["right_score"]), RIGHT_COLOR, scale=1)
