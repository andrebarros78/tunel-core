from pathlib import Path

import pytest

from tunel_core.control_plane import CredentialResolver, HealthEngine, HealthSample, ProfileManager
from tunel_core.data_plane import ConcurrencyFlowManager, Frame, HighFlowDataPlane, MultiChannelManager, TransportAdapter
from tunel_core.models import ConnectionProfile, RuntimeState
from tunel_core.observability import Observability
from tunel_core.ownership import OwnershipLeaseManager, SessionManager
from tunel_core.persistence_engine import CheckpointRollback, PersistenceEngine
from tunel_core.reliability import CircuitState, ReliabilityEngine, RetryBudget
from tunel_core.selftest import SelfTest
from tunel_core.watchdog import Watchdog


class MemoryTransport(TransportAdapter):
    def __init__(self):
        self.channels = {}
        self.rx = {}

    def open_channel(self, channel_id):
        self.channels[channel_id] = True
        self.rx.setdefault(channel_id, bytearray())

    def close_channel(self, channel_id):
        self.channels.pop(channel_id, None)

    def send(self, frame):
        self.rx[frame.channel_id].extend(frame.payload)
        return len(frame.payload)

    def receive(self, channel_id, max_bytes):
        buf = self.rx[channel_id]
        data = bytes(buf[:max_bytes])
        del buf[:max_bytes]
        return data

    def channel_healthy(self, channel_id):
        return bool(self.channels.get(channel_id))


def profile(connection_id="c1"):
    return ConnectionProfile(
        project_id="reference",
        connection_id=connection_id,
        alias=f"alias-{connection_id}",
        transport="streamable-http",
        local_endpoint="http://127.0.0.1:8765/mcp",
        remote_provider="adapter",
    )


def test_profile_version_and_secret_reference_only():
    mgr = ProfileManager()
    assert mgr.put(profile()) == 1
    assert mgr.put(profile()) == 2
    assert mgr.version("c1") == 2
    resolver = CredentialResolver(env={"REF": "secret-value"})
    assert resolver.resolve("REF") == "secret-value"
    with pytest.raises(KeyError):
        resolver.resolve("MISSING")


def test_health_hysteresis_avoids_flapping():
    health = HealthEngine(failures_to_degrade=2, successes_to_recover=2)
    assert health.observe(HealthSample(False, 10)) == RuntimeState.STARTING
    assert health.observe(HealthSample(False, 10)) == RuntimeState.DEGRADED
    assert health.observe(HealthSample(True, 5)) == RuntimeState.DEGRADED
    assert health.observe(HealthSample(True, 5)) == RuntimeState.HEALTHY


def test_32_independent_bidirectional_channels_and_hot_replacement():
    transport = MemoryTransport()
    channels = MultiChannelManager(transport, normal_capacity=16, peak_capacity=32)
    for i in range(32):
        cid = f"ch-{i}"
        channels.open(cid)
        assert channels.send(cid, f"payload-{i}".encode()) > 0
    assert len(channels.states()) == 32
    assert channels.receive("ch-7") == b"payload-7"
    transport.channels["ch-7"] = False
    replacement = channels.replace_if_unhealthy("ch-7")
    assert replacement.healthy is True
    assert transport.channel_healthy("ch-7") is True


def test_backpressure_is_bounded_and_priority_lane_wins():
    flow = ConcurrencyFlowManager(capacity=2)
    assert flow.enqueue(Frame("a", b"normal", 0))
    assert flow.enqueue(Frame("b", b"urgent", 1))
    assert flow.enqueue(Frame("c", b"overflow", 0)) is False
    assert flow.dequeue().channel_id == "b"
    assert flow.dequeue().channel_id == "a"


def test_high_flow_batch_flush():
    transport = MemoryTransport()
    channels = MultiChannelManager(transport, 1, 4)
    channels.open("a")
    plane = HighFlowDataPlane(channels, ConcurrencyFlowManager(10), batch_size=4)
    for _ in range(6):
        assert plane.submit("a", b"1234")
    assert plane.flush_once() == (4, 16)
    assert plane.flush_once() == (2, 8)


def test_lease_fencing_prevents_split_brain():
    leases = OwnershipLeaseManager(ttl_seconds=10)
    first = leases.acquire("runtime:a", "owner-1")
    with pytest.raises(RuntimeError):
        leases.acquire("runtime:a", "owner-2")
    assert leases.validate_fence("runtime:a", first.fencing_token)
    assert leases.release(first)
    second = leases.acquire("runtime:a", "owner-2")
    assert second.fencing_token > first.fencing_token


def test_session_resume_increments_generation():
    sessions = SessionManager()
    one = sessions.open("s1", "c1")
    assert one.generation == 1
    sessions.close("s1")
    two = sessions.resume("s1")
    assert two.active and two.generation == 2


def test_persistence_recovery_and_checkpoint_rollback(tmp_path: Path):
    state = tmp_path / "state"
    engine = PersistenceEngine(state)
    engine.write("runtime", {"generation": 1})
    checkpoints = CheckpointRollback(state, tmp_path / "checkpoints")
    checkpoints.checkpoint("g1")
    engine.write("runtime", {"generation": 2})
    checkpoints.rollback("g1")
    assert PersistenceEngine(state).read("runtime")["generation"] == 1


def test_circuit_breaker_and_retry_budget():
    reliability = ReliabilityEngine(RetryBudget(capacity=1, refill_per_second=0))
    breaker = reliability.breaker("provider")
    breaker.failure_threshold = 2
    breaker.failure(now=0)
    breaker.failure(now=0)
    assert breaker.state == CircuitState.OPEN
    assert reliability.may_retry() is True
    assert reliability.may_retry() is False


def test_observability_is_bounded_and_filters_secret_fields():
    obs = Observability(max_events=2, max_metrics=3)
    obs.event("one", secret_value="must-not-leak", visible="yes")
    obs.event("two")
    obs.event("three")
    snap = obs.snapshot()
    assert len(snap["events"]) == 2
    assert all("secret_value" not in row for row in snap["events"])
    for value in (10, 20, 30):
        obs.metric("latency.ms", value)
    assert obs.percentile("latency.ms", 95) == 30


def test_watchdog_restarts_stale_supervisor_only():
    starts = []
    wd = Watchdog(
        supervisor_alive=lambda: True,
        start_supervisor=lambda: starts.append("supervisor") or True,
        supervisor_heartbeat=lambda: 10.0,
        heartbeat_timeout=5.0,
        monotonic=lambda: 20.0,
    )
    assert wd.tick() is True
    assert starts == ["supervisor"]


def test_selftest_reports_failures_without_aborting():
    report = SelfTest().add("ok", lambda: True).add("bad", lambda: False).run()
    assert report.passed is False
    assert len(report.checks) == 2
