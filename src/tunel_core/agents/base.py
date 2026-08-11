from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Mapping, Protocol


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AgentResult:
    agent: str
    ok: bool
    action: str
    detail: str = ""
    data: Mapping[str, Any] = field(default_factory=dict)
    at_monotonic: float = field(default_factory=time.monotonic)


class CoreAgent(Protocol):
    name: str

    def status(self) -> AgentResult: ...
