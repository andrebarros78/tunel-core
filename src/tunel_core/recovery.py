from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, TypeVar

from .models import RetryPolicy

T = TypeVar("T")


@dataclass(slots=True)
class RecoveryEngine:
    policy: RetryPolicy
    sleeper: Callable[[float], None] = time.sleep

    def run(self, operation: Callable[[], T], success: Callable[[T], bool]) -> T:
        delay = max(0.0, self.policy.initial_seconds)
        attempt = 0
        last: T | None = None
        while True:
            attempt += 1
            last = operation()
            if success(last):
                return last
            if self.policy.max_attempts and attempt >= self.policy.max_attempts:
                return last
            self.sleeper(delay)
            delay = min(
                self.policy.maximum_seconds,
                max(self.policy.initial_seconds, delay * self.policy.multiplier),
            )
