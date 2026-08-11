from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from typing import Callable


@dataclass(slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass(slots=True)
class SelfTestReport:
    checks: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict:
        return {"passed": self.passed, "checks": [asdict(c) for c in self.checks]}


class SelfTest:
    """Composable final validation for install, connection, health, recovery and flow."""

    def __init__(self) -> None:
        self._checks: list[tuple[str, Callable[[], object]]] = []

    def add(self, name: str, check: Callable[[], object]) -> "SelfTest":
        self._checks.append((name, check))
        return self

    def run(self) -> SelfTestReport:
        results: list[CheckResult] = []
        for name, check in self._checks:
            started = time.perf_counter()
            try:
                value = check()
                passed = bool(value)
                detail = "ok" if passed else f"returned {value!r}"
            except Exception as exc:
                passed = False
                detail = f"{type(exc).__name__}: {exc}"
            elapsed = (time.perf_counter() - started) * 1000
            results.append(CheckResult(name, passed, detail, elapsed))
        return SelfTestReport(results)
