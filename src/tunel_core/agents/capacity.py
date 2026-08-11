from __future__ import annotations

from dataclasses import dataclass

from .base import AgentResult
from ..data_plane import ConcurrencyFlowManager, MultiChannelManager


@dataclass(slots=True)
class CapacityAgent:
    channels: MultiChannelManager
    flow: ConcurrencyFlowManager
    high_watermark: float = 0.80
    name: str = "capacity"

    def __post_init__(self) -> None:
        if not 0 < self.high_watermark <= 1:
            raise ValueError("high_watermark must be in (0, 1]")

    def status(self) -> AgentResult:
        states = self.channels.states()
        open_channels = len(states)
        unhealthy = sum(1 for item in states if not item.healthy)
        queue_depth = self.flow.depth
        queue_ratio = queue_depth / self.flow.capacity
        overloaded = queue_ratio >= self.high_watermark or open_channels >= self.channels.peak_capacity
        return AgentResult(
            agent=self.name,
            ok=not overloaded and unhealthy == 0,
            action="status",
            detail="capacity degraded" if overloaded or unhealthy else "capacity healthy",
            data={
                "open_channels": open_channels,
                "normal_capacity": self.channels.normal_capacity,
                "peak_capacity": self.channels.peak_capacity,
                "unhealthy_channels": unhealthy,
                "queue_depth": queue_depth,
                "queue_capacity": self.flow.capacity,
                "queue_ratio": queue_ratio,
                "overloaded": overloaded,
            },
        )

    def repair_channels(self) -> AgentResult:
        repaired: list[str] = []
        failed: list[str] = []
        for state in self.channels.states():
            if state.healthy and self.channels.transport.channel_healthy(state.channel_id):
                continue
            try:
                self.channels.replace_if_unhealthy(state.channel_id)
                repaired.append(state.channel_id)
            except Exception:
                failed.append(state.channel_id)
        return AgentResult(
            agent=self.name,
            ok=not failed,
            action="repair_channels",
            data={"repaired": tuple(repaired), "failed": tuple(failed)},
        )
