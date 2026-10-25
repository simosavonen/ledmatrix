from datetime import datetime

from ..canvas import Canvas
from .base import Mode

HOUR_COLOR = (255, 150, 20)
MINUTE_COLOR = (230, 230, 240)
MARBLE_COLOR = (230, 50, 50)
TRACK_COLOR = (24, 24, 32)

LANE_SLOTS = 30  # per lane; two lanes back-and-forth = 60 slots, one per second
PITCH = 64 / LANE_SLOTS
MARBLE_RADIUS = 0.95
LANE0_Y = 14.0
LANE1_Y = 24.0
ROLLOFF_DURATION = 0.6  # seconds, for the full tray to clear at the top of each minute


def _slot_pos(i: int) -> tuple[float, float]:
    """Screen position of ramp slot i (0-59): left-to-right along the top
    lane, then right-to-left along the bottom lane, so the two lanes join
    into one continuous zigzag track instead of jumping back to the start."""
    if i < LANE_SLOTS:
        return i * PITCH + PITCH / 2, LANE0_Y
    j = i - LANE_SLOTS
    return (LANE_SLOTS - 1 - j) * PITCH + PITCH / 2, LANE1_Y


class MarbleClockMode(Mode):
    """A gravity ball-clock: one marble rolls into the next slot along a
    60-slot zigzag ramp every second. When the ramp fills up at the top of
    the minute, the whole tray dumps and rolls off, and the ramp empties to
    start the next minute - like a real marble clock tipping its tray.
    Hour/minute stay an exact digital readout up top; 60 seconds' worth of
    marbles already fills the panel without also tracking minutes/hours
    as marbles."""

    name = "marble_clock"

    def render(self, canvas: Canvas, now: datetime) -> None:
        canvas.clear((0, 0, 0))

        text = now.strftime("%H:%M")
        text_w = canvas.text_width(text)
        x = (canvas.width - text_w) // 2
        x += canvas.draw_text(x, 1, now.strftime("%H"), HOUR_COLOR)
        x += canvas.draw_text(x, 1, ":", MINUTE_COLOR)
        canvas.draw_text(x, 1, now.strftime("%M"), MINUTE_COLOR)

        for i in range(60):
            sx, sy = _slot_pos(i)
            canvas.draw_dot(sx, sy, MARBLE_RADIUS, TRACK_COLOR)

        sec = now.second + now.microsecond / 1_000_000

        if sec < ROLLOFF_DURATION:
            exit_t = sec / ROLLOFF_DURATION
            dim = tuple(int(c * (1 - exit_t)) for c in MARBLE_COLOR)
            for i in range(60):
                sx, sy = _slot_pos(i)
                canvas.draw_dot(sx - exit_t * 6, sy + exit_t * 6, MARBLE_RADIUS, dim)
        else:
            filled = int(sec)
            for i in range(filled):
                sx, sy = _slot_pos(i)
                canvas.draw_dot(sx, sy, MARBLE_RADIUS, MARBLE_COLOR)

            if filled > 0:
                prev_x, prev_y = _slot_pos(filled - 1)
                progress = sec - filled
            else:
                prev_x, prev_y = _slot_pos(0)[0], LANE0_Y - 5  # feed chute above the ramp's start
                progress = (sec - ROLLOFF_DURATION) / (1 - ROLLOFF_DURATION)

            target_x, target_y = _slot_pos(filled)
            rolling_x = prev_x + (target_x - prev_x) * progress
            rolling_y = prev_y + (target_y - prev_y) * progress
            canvas.draw_dot(rolling_x, rolling_y, MARBLE_RADIUS, MARBLE_COLOR)

        canvas.bloom()
