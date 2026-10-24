import random
from datetime import datetime, timedelta

from .modes.base import Mode


class RotationController:
    """Shows `anchor` most of the time, cutting to a random fun mode periodically."""

    def __init__(
        self,
        anchor: Mode,
        fun_modes: list[Mode],
        fun_every: timedelta = timedelta(minutes=5),
        fun_duration: timedelta = timedelta(seconds=45),
    ):
        self.anchor = anchor
        self.fun_modes = fun_modes
        self.fun_every = fun_every
        self.fun_duration = fun_duration

        self._current: Mode = anchor
        self._segment_start: datetime | None = None
        self._in_fun = False

    def current_mode(self, now: datetime) -> Mode:
        if self._segment_start is None:
            self._segment_start = now
            self._current.reset()
            return self._current

        elapsed = now - self._segment_start

        if self._in_fun and elapsed >= self.fun_duration:
            self._switch_to(self.anchor, now)
        elif not self._in_fun and self.fun_modes and elapsed >= self.fun_every:
            choices = [m for m in self.fun_modes if m is not self._current] or self.fun_modes
            self._switch_to(random.choice(choices), now, in_fun=True)

        return self._current

    def _switch_to(self, mode: Mode, now: datetime, in_fun: bool = False) -> None:
        self._current = mode
        self._segment_start = now
        self._in_fun = in_fun
        mode.reset()

    def skip(self, now: datetime) -> None:
        """Force an immediate transition, as if the current segment had timed out."""
        if self._in_fun:
            self._switch_to(self.anchor, now)
        elif self.fun_modes:
            choices = [m for m in self.fun_modes if m is not self._current] or self.fun_modes
            self._switch_to(random.choice(choices), now, in_fun=True)
