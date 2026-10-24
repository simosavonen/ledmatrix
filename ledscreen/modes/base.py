from abc import ABC, abstractmethod
from datetime import datetime

from ..canvas import Canvas


class Mode(ABC):
    name: str = "mode"

    @abstractmethod
    def render(self, canvas: Canvas, now: datetime) -> None:
        """Draw the current frame. Called repeatedly while this mode is active."""

    def reset(self) -> None:
        """Called whenever this mode becomes active again after being swapped out."""
