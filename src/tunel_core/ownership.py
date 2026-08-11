from __future__ import annotations

from dataclasses import dataclass, field
import secrets
import threading
import time


@dataclass(slots=True)
class Lease:
    resource_id: str
    owner_id: str
    fencing_token: int
    generation_id: str
    expires_at: float

    def expired(self, now: float | None = None) -> bool:
        return (time.monotonic() if now is None else now) >= self.expires_at


class OwnershipLeaseManager:
    """In-process lease/fencing primitive; persistent adapters may externalize the store."""

    def __init__(self, ttl_seconds: float = 30.0) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.ttl_seconds = ttl_seconds
        self._leases: dict[str, Lease] = {}
        self._tokens: dict[str, int] = {}
        self._lock = threading.RLock()

    def acquire(self, resource_id: str, owner_id: str, now: float | None = None) -> Lease:
        now = time.monotonic() if now is None else now
        with self._lock:
            current = self._leases.get(resource_id)
            if current and not current.expired(now) and current.owner_id != owner_id:
                raise RuntimeError(f"resource already leased: {resource_id}")
            token = self._tokens.get(resource_id, 0) + 1
            self._tokens[resource_id] = token
            lease = Lease(resource_id, owner_id, token, secrets.token_hex(8), now + self.ttl_seconds)
            self._leases[resource_id] = lease
            return lease

    def renew(self, lease: Lease, now: float | None = None) -> Lease:
        now = time.monotonic() if now is None else now
        with self._lock:
            current = self._leases.get(lease.resource_id)
            if current is None or current.owner_id != lease.owner_id or current.fencing_token != lease.fencing_token:
                raise RuntimeError("stale lease cannot be renewed")
            if current.expired(now):
                raise RuntimeError("expired lease cannot be renewed")
            current.expires_at = now + self.ttl_seconds
            return current

    def release(self, lease: Lease) -> bool:
        with self._lock:
            current = self._leases.get(lease.resource_id)
            if current is None or current.owner_id != lease.owner_id or current.fencing_token != lease.fencing_token:
                return False
            del self._leases[lease.resource_id]
            return True

    def validate_fence(self, resource_id: str, token: int) -> bool:
        with self._lock:
            current = self._leases.get(resource_id)
            return bool(current and not current.expired() and current.fencing_token == token)


@dataclass(slots=True)
class Session:
    session_id: str
    connection_id: str
    generation: int = 1
    active: bool = True
    metadata: dict[str, str] = field(default_factory=dict)
    last_activity: float = field(default_factory=time.monotonic)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def open(self, session_id: str, connection_id: str, metadata: dict[str, str] | None = None) -> Session:
        with self._lock:
            current = self._sessions.get(session_id)
            if current and current.active:
                return current
            session = Session(session_id, connection_id, metadata=dict(metadata or {}))
            self._sessions[session_id] = session
            return session

    def touch(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions[session_id]
            session.last_activity = time.monotonic()

    def resume(self, session_id: str) -> Session:
        with self._lock:
            session = self._sessions[session_id]
            session.generation += 1
            session.active = True
            session.last_activity = time.monotonic()
            return session

    def close(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.active = False
                session.last_activity = time.monotonic()
