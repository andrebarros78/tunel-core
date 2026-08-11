from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
import threading
import time
from typing import Callable, Deque


@dataclass(slots=True)
class Frame:
    channel_id: str
    payload: bytes
    priority: int = 0
    created_at: float = field(default_factory=time.monotonic)


class TransportAdapter(ABC):
    @abstractmethod
    def open_channel(self, channel_id: str) -> None: ...

    @abstractmethod
    def close_channel(self, channel_id: str) -> None: ...

    @abstractmethod
    def send(self, frame: Frame) -> int: ...

    @abstractmethod
    def receive(self, channel_id: str, max_bytes: int) -> bytes: ...

    @abstractmethod
    def channel_healthy(self, channel_id: str) -> bool: ...


class ProviderAdapter(ABC):
    @abstractmethod
    def provision(self, profile) -> dict[str, str]: ...

    @abstractmethod
    def deprovision(self, profile) -> None: ...

    @abstractmethod
    def provider_healthy(self) -> bool: ...


@dataclass(slots=True)
class ChannelState:
    channel_id: str
    healthy: bool = True
    sent_bytes: int = 0
    received_bytes: int = 0
    last_activity: float = field(default_factory=time.monotonic)


class MultiChannelManager:
    """Independent bidirectional channels with hot replacement and no global data-path lock."""

    def __init__(self, transport: TransportAdapter, normal_capacity: int = 16, peak_capacity: int = 32) -> None:
        if normal_capacity < 1 or peak_capacity < normal_capacity:
            raise ValueError("invalid channel capacity")
        self.transport = transport
        self.normal_capacity = normal_capacity
        self.peak_capacity = peak_capacity
        self._channels: dict[str, ChannelState] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._meta_lock = threading.Lock()

    def open(self, channel_id: str) -> ChannelState:
        with self._meta_lock:
            if channel_id in self._channels:
                return self._channels[channel_id]
            if len(self._channels) >= self.peak_capacity:
                raise RuntimeError("peak channel capacity reached")
            self.transport.open_channel(channel_id)
            state = ChannelState(channel_id)
            self._channels[channel_id] = state
            self._locks[channel_id] = threading.Lock()
            return state

    def close(self, channel_id: str) -> None:
        with self._meta_lock:
            state = self._channels.pop(channel_id, None)
            self._locks.pop(channel_id, None)
        if state is not None:
            self.transport.close_channel(channel_id)

    def send(self, channel_id: str, payload: bytes, priority: int = 0) -> int:
        state = self._channels[channel_id]
        lock = self._locks[channel_id]
        with lock:
            if not state.healthy or not self.transport.channel_healthy(channel_id):
                state.healthy = False
                raise ConnectionError(f"channel unhealthy: {channel_id}")
            written = self.transport.send(Frame(channel_id, payload, priority))
            state.sent_bytes += written
            state.last_activity = time.monotonic()
            return written

    def receive(self, channel_id: str, max_bytes: int = 1 << 20) -> bytes:
        state = self._channels[channel_id]
        lock = self._locks[channel_id]
        with lock:
            data = self.transport.receive(channel_id, max_bytes)
            state.received_bytes += len(data)
            state.last_activity = time.monotonic()
            return data

    def replace_if_unhealthy(self, channel_id: str) -> ChannelState:
        state = self._channels[channel_id]
        if state.healthy and self.transport.channel_healthy(channel_id):
            return state
        self.close(channel_id)
        return self.open(channel_id)

    def states(self) -> tuple[ChannelState, ...]:
        with self._meta_lock:
            return tuple(self._channels.values())


class ConcurrencyFlowManager:
    """Bounded priority lanes providing backpressure and overload protection."""

    def __init__(self, capacity: int = 4096) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._high: Deque[Frame] = deque()
        self._normal: Deque[Frame] = deque()
        self._lock = threading.Lock()

    def enqueue(self, frame: Frame) -> bool:
        with self._lock:
            if len(self._high) + len(self._normal) >= self.capacity:
                return False
            (self._high if frame.priority > 0 else self._normal).append(frame)
            return True

    def dequeue(self) -> Frame | None:
        with self._lock:
            if self._high:
                return self._high.popleft()
            if self._normal:
                return self._normal.popleft()
            return None

    @property
    def depth(self) -> int:
        with self._lock:
            return len(self._high) + len(self._normal)


class HighFlowDataPlane:
    """Minimal-allocation streaming loop with bounded batches."""

    def __init__(self, channels: MultiChannelManager, flow: ConcurrencyFlowManager, batch_size: int = 64) -> None:
        self.channels = channels
        self.flow = flow
        self.batch_size = max(1, batch_size)

    def submit(self, channel_id: str, payload: bytes, priority: int = 0) -> bool:
        return self.flow.enqueue(Frame(channel_id, payload, priority))

    def flush_once(self) -> tuple[int, int]:
        frames = 0
        payload_bytes = 0
        while frames < self.batch_size:
            frame = self.flow.dequeue()
            if frame is None:
                break
            payload_bytes += self.channels.send(frame.channel_id, frame.payload, frame.priority)
            frames += 1
        return frames, payload_bytes
