from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
import threading
import time
from typing import Callable, Mapping

from .models import ConnectionProfile, HealthReport, RuntimeState, RuntimeStatus
from .recovery import RecoveryEngine


class ConnectionState(str, Enum):
    STOPPED = "stopped"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"
    DRAINING = "draining"
    FAILED = "failed"


class ProfileManager:
    """Validates and versions immutable runtime profiles."""

    def __init__(self) -> None:
        self._profiles: dict[str, ConnectionProfile] = {}
        self._versions: dict[str, int] = {}
        self._lock = threading.RLock()

    def put(self, profile: ConnectionProfile) -> int:
        with self._lock:
            self._profiles[profile.connection_id] = profile
            version = self._versions.get(profile.connection_id, 0) + 1
            self._versions[profile.connection_id] = version
            return version

    def get(self, connection_id: str) -> ConnectionProfile:
        with self._lock:
            return self._profiles[connection_id]

    def version(self, connection_id: str) -> int:
        with self._lock:
            return self._versions.get(connection_id, 0)


class CredentialResolver:
    """Resolves secret references without persisting secret values."""

    def __init__(self, env: Mapping[str, str] | None = None, store: Callable[[str], str | None] | None = None) -> None:
        self._env = env if env is not None else os.environ
        self._store = store

    def resolve(self, reference: str) -> str:
        if not reference:
            raise ValueError("credential reference is required")
        value = self._env.get(reference)
        if value is None and self._store is not None:
            value = self._store(reference)
        if not value:
            raise KeyError(f"credential reference not found: {reference}")
        return value


@dataclass(slots=True)
class HealthSample:
    healthy: bool
    latency_ms: float
    throughput_bps: float = 0.0
    detail: str = ""
    at_monotonic: float = field(default_factory=time.monotonic)


class HealthEngine:
    """Aggregates health with hysteresis to avoid flapping."""

    def __init__(self, failures_to_degrade: int = 2, successes_to_recover: int = 2) -> None:
        if failures_to_degrade < 1 or successes_to_recover < 1:
            raise ValueError("hysteresis thresholds must be positive")
        self.failures_to_degrade = failures_to_degrade
        self.successes_to_recover = successes_to_recover
        self._failures = 0
        self._successes = 0
        self._state = RuntimeState.STARTING
        self._lock = threading.Lock()

    def observe(self, sample: HealthSample) -> RuntimeState:
        with self._lock:
            if sample.healthy:
                self._successes += 1
                self._failures = 0
                if self._successes >= self.successes_to_recover:
                    self._state = RuntimeState.HEALTHY
            else:
                self._failures += 1
                self._successes = 0
                if self._failures >= self.failures_to_degrade:
                    self._state = RuntimeState.DEGRADED
            return self._state

    @property
    def state(self) -> RuntimeState:
        with self._lock:
            return self._state


class ConnectionManager:
    """Owns connection lifecycle while delegating concrete runtime operations."""

    def __init__(self, tunnel, recovery: RecoveryEngine) -> None:
        self._tunnel = tunnel
        self._recovery = recovery
        self._states: dict[str, ConnectionState] = {}
        self._locks: dict[str, threading.RLock] = {}
        self._global = threading.Lock()

    def _lock_for(self, connection_id: str) -> threading.RLock:
        with self._global:
            return self._locks.setdefault(connection_id, threading.RLock())

    def state(self, connection_id: str) -> ConnectionState:
        return self._states.get(connection_id, ConnectionState.STOPPED)

    def connect(self, profile: ConnectionProfile) -> RuntimeStatus:
        with self._lock_for(profile.connection_id):
            current = self._tunnel.status(profile)
            if current.running and current.ready:
                self._states[profile.connection_id] = ConnectionState.CONNECTED
                return current
            self._states[profile.connection_id] = ConnectionState.CONNECTING
            result = self._recovery.run(
                lambda: self._tunnel.connect(profile),
                lambda s: bool(s.running and s.ready),
            )
            self._states[profile.connection_id] = ConnectionState.CONNECTED if result.ready else ConnectionState.FAILED
            return result

    def reconnect(self, profile: ConnectionProfile) -> RuntimeStatus:
        with self._lock_for(profile.connection_id):
            self._states[profile.connection_id] = ConnectionState.RECONNECTING
            try:
                self._tunnel.disconnect(profile)
            finally:
                return self.connect(profile)

    def disconnect(self, profile: ConnectionProfile) -> RuntimeStatus:
        with self._lock_for(profile.connection_id):
            self._states[profile.connection_id] = ConnectionState.DRAINING
            result = self._tunnel.disconnect(profile)
            self._states[profile.connection_id] = ConnectionState.STOPPED
            return result
