from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path

import pytest

from tunel_core.data_plane import (
    ConcurrencyFlowManager,
    Frame,
    HighFlowDataPlane,
    MultiChannelManager,
    TransportAdapter,
)
from tunel_core.ownership import OwnershipLeaseManager, SessionManager
from tunel_core.persistence_engine import CheckpointRollback, PersistenceEngine


class TwinTransport(TransportAdapter):
    """Transport 100% local/in-memory: no sockets, services, subprocesses or external effects."""

    def __init__(self) -> None:
        self.opened: set[str] = set()
        self.healthy: dict[str, bool] = defaultdict(lambda: True)
        self.rx: dict[str, deque[bytes]] = defaultdict(deque)
        self.sent: dict[str, int] = defaultdict(int)

    def open_channel(self, channel_id: str) -> None:
        self.opened.add(channel_id)
        self.healthy[channel_id] = True

    def close_channel(self, channel_id: str) -> None:
        self.opened.discard(channel_id)

    def send(self, frame: Frame) -> int:
        if frame.channel_id not in self.opened or not self.healthy[frame.channel_id]:
            raise ConnectionError(frame.channel_id)
        # digital twin bilateral loopback: outbound becomes remote inbound response
        self.rx[frame.channel_id].append(b"ACK:" + frame.payload)
        self.sent[frame.channel_id] += len(frame.payload)
        return len(frame.payload)

    def receive(self, channel_id: str, max_bytes: int) -> bytes:
        if channel_id not in self.opened or not self.healthy[channel_id]:
            raise ConnectionError(channel_id)
        if not self.rx[channel_id]:
            return b""
        return self.rx[channel_id].popleft()[:max_bytes]

    def channel_healthy(self, channel_id: str) -> bool:
        return channel_id in self.opened and self.healthy[channel_id]


def test_digital_twin_32_bidirectional_channels_high_flow_and_isolation() -> None:
    transport = TwinTransport()
    channels = MultiChannelManager(transport, normal_capacity=16, peak_capacity=32)
    flow = ConcurrencyFlowManager(capacity=4096)
    plane = HighFlowDataPlane(channels, flow, batch_size=128)

    ids = [f"ch-{i:02d}" for i in range(32)]
    for channel_id in ids:
        channels.open(channel_id)

    assert len(channels.states()) == 32

    payload = b"x" * 4096
    rounds = 32
    expected_frames = len(ids) * rounds
    expected_bytes = expected_frames * len(payload)

    for _ in range(rounds):
        for channel_id in ids:
            assert plane.submit(channel_id, payload)

    frames = sent_bytes = 0
    while flow.depth:
        f, b = plane.flush_once()
        frames += f
        sent_bytes += b

    assert frames == expected_frames
    assert sent_bytes == expected_bytes

    # Bilateral proof: every outbound frame produced an isolated inbound response.
    received = 0
    for channel_id in ids:
        for _ in range(rounds):
            data = channels.receive(channel_id)
            assert data == b"ACK:" + payload
            received += len(data)
    assert received == expected_frames * (len(payload) + 4)

    # One failed channel must not take healthy channels down.
    failed = ids[7]
    transport.healthy[failed] = False
    with pytest.raises(ConnectionError):
        channels.send(failed, b"failure-probe")
    assert channels.send(ids[8], b"healthy-probe") == len(b"healthy-probe")

    # Hot replacement repairs only the failed channel.
    repaired = channels.replace_if_unhealthy(failed)
    assert repaired.healthy
    assert transport.channel_healthy(failed)
    assert len(channels.states()) == 32


def test_digital_twin_backpressure_is_bounded() -> None:
    flow = ConcurrencyFlowManager(capacity=8)
    for i in range(8):
        assert flow.enqueue(Frame("x", str(i).encode()))
    assert flow.depth == 8
    assert flow.enqueue(Frame("x", b"overflow")) is False
    assert flow.depth == 8


def test_digital_twin_crash_recovery_checkpoint_and_rollback(tmp_path: Path) -> None:
    state = tmp_path / "state"
    checkpoints = tmp_path / "checkpoints"
    engine = PersistenceEngine(state)

    engine.write("runtime", {"generation": 1, "state": "healthy"})
    cp = CheckpointRollback(state, checkpoints)
    cp.checkpoint("green-1")

    engine.write("runtime", {"generation": 2, "state": "degraded"})
    assert engine.read("runtime")["generation"] == 2

    cp.rollback("green-1")
    restored = PersistenceEngine(state).read("runtime")
    assert restored == {"generation": 1, "state": "healthy"}

    # Simulated interrupted atomic write: journal + tmp exist at crash time.
    path, temp, journal = engine._paths("crash")
    temp.write_text('{"state":"recovered"}', encoding="utf-8")
    journal.write_text('{"op":"replace"}', encoding="utf-8")
    assert not path.exists()
    recovered = engine.recover()
    assert recovered == ["crash"]
    assert engine.read("crash") == {"state": "recovered"}
    assert not journal.exists()


def test_digital_twin_split_brain_fencing_and_stale_owner_rejection() -> None:
    leases = OwnershipLeaseManager(ttl_seconds=10)
    owner_a = leases.acquire("runtime-1", "owner-a", now=100.0)

    with pytest.raises(RuntimeError):
        leases.acquire("runtime-1", "owner-b", now=101.0)

    owner_b = leases.acquire("runtime-1", "owner-b", now=111.0)
    assert owner_b.fencing_token > owner_a.fencing_token
    assert leases.release(owner_a) is False
    with pytest.raises(RuntimeError):
        leases.renew(owner_a, now=112.0)


def test_digital_twin_session_resume_after_disconnect() -> None:
    sessions = SessionManager()
    session = sessions.open("s1", "connection-1", {"side": "bilateral"})
    assert session.active and session.generation == 1
    sessions.close("s1")
    resumed = sessions.resume("s1")
    assert resumed.active
    assert resumed.generation == 2
    assert resumed.metadata["side"] == "bilateral"
