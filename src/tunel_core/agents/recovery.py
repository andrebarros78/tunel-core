from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .base import AgentResult


RecoveryAction = Callable[[], bool]


@dataclass(slots=True)
class RecoveryAgent:
    actions: Mapping[str, RecoveryAction]
    name: str = "recovery"

    def handle(self, event: str) -> AgentResult:
        action = self.actions.get(event)
        if action is None:
            return AgentResult(
                agent=self.name,
                ok=False,
                action="handle",
                detail=f"no recovery action for event: {event}",
                data={"event": event},
            )
        try:
            recovered = bool(action())
            return AgentResult(
                agent=self.name,
                ok=recovered,
                action="handle",
                detail="recovered" if recovered else "recovery failed",
                data={"event": event},
            )
        except Exception as exc:
            return AgentResult(
                agent=self.name,
                ok=False,
                action="handle",
                detail=f"recovery raised {type(exc).__name__}: {exc}",
                data={"event": event},
            )

    def status(self) -> AgentResult:
        return AgentResult(
            agent=self.name,
            ok=True,
            action="status",
            data={"registered_events": tuple(sorted(self.actions))},
        )
