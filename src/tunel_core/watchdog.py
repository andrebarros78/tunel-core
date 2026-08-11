from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable


@dataclass(slots=True)
class Watchdog:
    """Watches only Supervisor liveness/heartbeat; never application or tunnel directly."""

    supervisor_alive: Callable[[], bool]
    start_supervisor: Callable[[], bool]
    supervisor_heartbeat: Callable[[], float] | None = None
    heartbeat_timeout: float = 60.0
    monotonic: Callable[[], float] = time.monotonic

    def tick(self) -> bool:
        alive = bool(self.supervisor_alive())
        stale = False
        if alive and self.supervisor_heartbeat is not None:
            last = self.supervisor_heartbeat()
            stale = self.monotonic() - last > self.heartbeat_timeout
        if alive and not stale:
            return True
        return bool(self.start_supervisor())
