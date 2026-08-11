from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Iterable

from .base import AgentResult


@dataclass(slots=True)
class ObservabilityAgent:
    history_size: int = 256
    name: str = "observability"
    _history: Deque[AgentResult] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._history = deque(maxlen=max(1, self.history_size))

    def record(self, result: AgentResult) -> None:
        self._history.append(result)

    def record_many(self, results: Iterable[AgentResult]) -> None:
        for result in results:
            self.record(result)

    def snapshot(self) -> AgentResult:
        items = tuple(self._history)
        failures = tuple(item for item in items if not item.ok)
        by_agent: dict[str, int] = {}
        for item in failures:
            by_agent[item.agent] = by_agent.get(item.agent, 0) + 1
        return AgentResult(
            agent=self.name,
            ok=not failures,
            action="snapshot",
            detail="healthy" if not failures else "degraded",
            data={
                "events": len(items),
                "failures": len(failures),
                "failures_by_agent": by_agent,
                "last_agent": items[-1].agent if items else "",
                "last_action": items[-1].action if items else "",
            },
        )

    def status(self) -> AgentResult:
        return self.snapshot()
