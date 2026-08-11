from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class Watchdog:
    """Supervises only the supervisor lifecycle, never the application directly."""

    supervisor_alive: Callable[[], bool]
    start_supervisor: Callable[[], bool]

    def tick(self) -> bool:
        if self.supervisor_alive():
            return True
        return bool(self.start_supervisor())
