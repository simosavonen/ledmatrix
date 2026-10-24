from abc import ABC, abstractmethod

from ..canvas import Canvas


class Display(ABC):
    width: int = 64
    height: int = 32

    @abstractmethod
    def show(self, canvas: Canvas) -> None:
        """Push a rendered frame to the physical or simulated screen."""

    def close(self) -> None:
        pass
