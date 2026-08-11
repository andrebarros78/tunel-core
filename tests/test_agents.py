from __future__ import annotations

from tunel_core.agents import (
    AgentRegistry,
    AgentResult,
    CapacityAgent,
    HealthAgent,
    ObservabilityAgent,
    RecoveryAgent,
)
from tunel_core.control_plane import HealthEngine, HealthSample
from tunel_core.data_plane import ConcurrencyFlowManager, Frame, MultiChannelManager, TransportAdapter


class FakeTransport(TransportAdapter):
    def __init__(self) -> None:
        self.opened: set[str] = set()
        self.healthy: dict[str, bool] = {}

    def open_channel(self, channel_id: str) -> None:
        self.opened.add(channel_id)
        self.healthy[channel_id] = True

    def close_channel(self, channel_id: str) -> None:
        self.opened.discard(channel_id)

    def send(self, frame: Frame) -> int:
        return len(frame.payload)

    def receive(self, channel_id: str, max_bytes: int) -> bytes:
        return b""

    def channel_healthy(self, channel_id: str) -> bool:
        return self.healthy.get(channel_id, False)


def test_health_agent_uses_existing_hysteresis() -> None:
    agent = HealthAgent(HealthEngine(failures_to_degrade=2, successes_to_recover=2))
    first = agent.observe(HealthSample(True, 10.0))
    second = agent.observe(HealthSample(True, 20.0))
    assert first.ok is False
    assert second.ok is True
    assert second.data["median_latency_ms"] == 15.0


def test_capacity_agent_detects_backpressure() -> None:
    transport = FakeTransport()
    channels = MultiChannelManager(transport, normal_capacity=1, peak_capacity=2)
    flow = ConcurrencyFlowManager(capacity=2)
    channels.open("c1")
    flow.enqueue(Frame("c1", b"a"))
    flow.enqueue(Frame("c1", b"b"))
    result = CapacityAgent(channels, flow, high_watermark=0.5).status()
    assert result.ok is False
    assert result.data["overloaded"] is True


def test_recovery_agent_is_event_driven() -> None:
    called: list[str] = []
    agent = RecoveryAgent({"channel_down": lambda: called.append("recovered") is None})
    result = agent.handle("channel_down")
    assert result.ok is True
    assert called == ["recovered"]
    missing = agent.handle("unknown")
    assert missing.ok is False


def test_observability_and_registry_are_decoupled() -> None:
    recovery = RecoveryAgent({})
    registry = AgentRegistry.from_agents([recovery])
    assert registry.names() == ("recovery",)
    observation = ObservabilityAgent()
    observation.record(AgentResult("health", True, "observe"))
    observation.record(AgentResult("capacity", False, "status"))
    snapshot = observation.snapshot()
    assert snapshot.ok is False
    assert snapshot.data["failures_by_agent"] == {"capacity": 1}
