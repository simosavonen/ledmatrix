import random
from datetime import datetime

from .modes.base import Mode


class RotationController:
    """Wall-clock-synced rotation: a clock shows at the top of each minute,
    cuts to a random fun mode at `clock_lead` seconds in (if any fun modes
    are configured), then returns to a clock before the next minute change
    so you see it tick over live. The clock face itself also rotates once
    per minute on its own - it doesn't just wait for a fun break to end,
    so rotation still works with `fun_modes` empty.

    Both the clock and the fun break are drawn from a shuffled bag per
    pool, so every style gets shown before any style repeats, instead of
    picking independently at random (which can land on the same one
    several times in a row).
    """

    def __init__(
        self,
        clock_modes: list[Mode],
        fun_modes: list[Mode],
        clock_lead: float = 10.0,
        fun_duration: float = 45.0,
    ):
        self.clock_modes = clock_modes
        self.fun_modes = fun_modes
        self.clock_lead = clock_lead
        self.fun_duration = fun_duration

        self._clock_bag: list[Mode] = []
        self._fun_bag: list[Mode] = []
        self._in_fun = False
        self._fun_cycle_key: datetime | None = None
        self._clock_cycle_key: datetime | None = None
        self._current: Mode = self._next_from(self._clock_bag, self.clock_modes)

    def _next_from(self, bag: list[Mode], pool: list[Mode]) -> Mode:
        if not bag:
            bag.extend(pool)
            random.shuffle(bag)
        return bag.pop()

    def current_mode(self, now: datetime) -> Mode:
        second_of_minute = now.second + now.microsecond / 1_000_000
        should_be_fun = (
            self.fun_modes
            and self.clock_lead <= second_of_minute < self.clock_lead + self.fun_duration
        )
        cycle_key = now.replace(second=0, microsecond=0)

        if should_be_fun:
            if not self._in_fun or cycle_key != self._fun_cycle_key:
                self._current = self._next_from(self._fun_bag, self.fun_modes)
                self._current.reset()
                self._fun_cycle_key = cycle_key
            self._in_fun = True
        else:
            if self._in_fun or cycle_key != self._clock_cycle_key:
                self._current = self._next_from(self._clock_bag, self.clock_modes)
                self._current.reset()
                self._clock_cycle_key = cycle_key
            self._in_fun = False

        return self._current
