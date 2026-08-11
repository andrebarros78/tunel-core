from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
import threading
import time
from typing import Callable


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(slots=True)
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    opened_at: float = 0.0

    def allow(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        if self.state == CircuitState.OPEN and now - self.opened_at >= self.recovery_timeout:
            self.state = CircuitState.HALF_OPEN
            return True
        return self.state != CircuitState.OPEN

    def success(self) -> None:
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at = 0.0

    def failure(self, now: float | None = None) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic() if now is None else now


class RetryBudget:
    def __init__(self, capacity: int = 100, refill_per_second: float = 1.0) -> None:
        self.capacity = float(max(1, capacity))
        self.tokens = self.capacity
        self.refill = max(0.0, refill_per_second)
        self.updated = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, cost: float = 1.0) -> bool:
        with self._lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.refill)
            self.updated = now
            if self.tokens < cost:
                return False
            self.tokens -= cost
            return True


class ReliabilityEngine:
    """Failure isolation, retry budgets and controlled degradation."""

    def __init__(self, retry_budget: RetryBudget | None = None) -> None:
        self.retry_budget = retry_budget or RetryBudget()
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def breaker(self, failure_domain: str) -> CircuitBreaker:
        with self._lock:
            return self._breakers.setdefault(failure_domain, CircuitBreaker())

    def execute(self, failure_domain: str, operation: Callable[[], object]):
        breaker = self.breaker(failure_domain)
        if not breaker.allow():
            raise RuntimeError(f"circuit open: {failure_domain}")
        try:
            result = operation()
        except Exception:
            breaker.failure()
            raise
        else:
            breaker.success()
            return result

    def retry_delay(self, attempt: int, base: float = 0.25, maximum: float = 30.0) -> float:
        exponential = min(maximum, base * (2 ** max(0, attempt - 1)))
        return random.uniform(exponential * 0.5, exponential)

    def may_retry(self) -> bool:
        return self.retry_budget.consume()
