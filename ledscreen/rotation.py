import random
from datetime import datetime

from .modes.base import Mode


class RotationController:
    """Wall-clock-synced rotation: clock shows at the top of each minute,
    cuts to a random fun mode at `clock_lead` seconds in, then returns to
    the clock before the next minute change so you see it tick over live.
    """

    def __init__(
        self,
        anchor: Mode,
        fun_modes: list[Mode],
        clock_lead: float = 10.0,
        fun_duration: float = 45.0,
    ):
        self.anchor = anchor
        self.fun_modes = fun_modes
        self.clock_lead = clock_lead
        self.fun_duration = fun_duration

        self._current: Mode = anchor
        self._in_fun = False
        self._cycle_key: datetime | None = None

    def current_mode(self, now: datetime) -> Mode:
        second_of_minute = now.second + now.microsecond / 1_000_000
        should_be_fun = (
            self.fun_modes
            and self.clock_lead <= second_of_minute < self.clock_lead + self.fun_duration
        )
        cycle_key = now.replace(second=0, microsecond=0)

        if should_be_fun:
            if not self._in_fun or cycle_key != self._cycle_key:
                self._current = random.choice(self.fun_modes)
                self._current.reset()
                self._cycle_key = cycle_key
            self._in_fun = True
        else:
            if self._in_fun:
                self._current = self.anchor
                self._current.reset()
            self._in_fun = False

        return self._current
