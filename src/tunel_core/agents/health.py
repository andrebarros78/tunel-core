from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from statistics import median
from typing import Deque

from .base import AgentResult
from ..control_plane import HealthEngine, HealthSample
from ..models import RuntimeState


@dataclass(slots=True)
class HealthAgent:
    engine: HealthEngine
    history_size: int = 64
    name: str = "health"
    _latencies: Deque[float] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._latencies = deque(maxlen=max(1, self.history_size))

    def observe(self, sample: HealthSample) -> AgentResult:
        self._latencies.append(max(0.0, sample.latency_ms))
        state = self.engine.observe(sample)
        return AgentResult(
            agent=self.name,
            ok=state == RuntimeState.HEALTHY,
            action="observe",
            detail=sample.detail,
            data={
                "state": state.value,
                "latency_ms": sample.latency_ms,
                "median_latency_ms": median(self._latencies),
                "throughput_bps": sample.throughput_bps,
            },
        )

    def status(self) -> AgentResult:
        state = self.engine.state
        return AgentResult(
            agent=self.name,
            ok=state == RuntimeState.HEALTHY,
            action="status",
            data={
                "state": state.value,
                "samples": len(self._latencies),
                "median_latency_ms": median(self._latencies) if self._latencies else 0.0,
            },
        )
