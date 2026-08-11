from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time

from .adapters import ApplicationAdapter, TunnelRuntimeAdapter
from .models import ConnectionProfile, HealthReport, RuntimeState, RuntimeStatus
from .observability import Observability
from .ownership import Lease, OwnershipLeaseManager
from .recovery import RecoveryEngine


@dataclass(slots=True)
class Supervisor:
    """Convergent supervisor: repairs only unhealthy owned resources."""

    profile: ConnectionProfile
    tunnel: TunnelRuntimeAdapter
    recovery: RecoveryEngine
    application: ApplicationAdapter | None = None
    ownership: OwnershipLeaseManager | None = None
    observability: Observability | None = None
    owner_id: str = "tunel-core-supervisor"
    _lease: Lease | None = field(default=None, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _heartbeat: float = field(default_factory=time.monotonic, init=False, repr=False)

    def heartbeat(self) -> float:
        with self._lock:
            self._heartbeat = time.monotonic()
            if self.ownership is not None and self._lease is not None:
                try:
                    self._lease = self.ownership.renew(self._lease)
                except RuntimeError:
                    self._lease = self.ownership.acquire(f"supervisor:{self.profile.connection_id}", self.owner_id)
            return self._heartbeat

    @property
    def last_heartbeat(self) -> float:
        with self._lock:
            return self._heartbeat

    def acquire_ownership(self) -> Lease | None:
        if self.ownership is None:
            return None
        with self._lock:
            if self._lease is None or self._lease.expired():
                self._lease = self.ownership.acquire(f"supervisor:{self.profile.connection_id}", self.owner_id)
            return self._lease

    def inspect(self) -> tuple[RuntimeStatus, HealthReport, HealthReport | None]:
        tunnel_status = self.tunnel.status(self.profile)
        tunnel_health = self.tunnel.health(self.profile)
        app_health = self.application.health(self.profile) if self.application else None
        if self.observability:
            self.observability.metric("tunnel.ready", 1.0 if tunnel_status.ready else 0.0, connection=self.profile.connection_id)
            self.observability.event("supervisor.inspect", connection=self.profile.connection_id, tunnel_healthy=tunnel_health.healthy)
        return tunnel_status, tunnel_health, app_health

    def ensure_tunnel(self) -> RuntimeStatus:
        with self._lock:
            self.acquire_ownership()
            status, tunnel_health, _ = self.inspect()
            if status.running and status.ready and tunnel_health.healthy:
                self.heartbeat()
                return status
            if self.observability:
                self.observability.event("tunnel.recovery.start", connection=self.profile.connection_id)
            result = self.recovery.run(
                lambda: self.tunnel.connect(self.profile),
                lambda current: current.running and current.ready,
            )
            if self.observability:
                self.observability.event("tunnel.recovery.finish", connection=self.profile.connection_id, ready=result.ready)
            self.heartbeat()
            return result

    def converge_once(self) -> HealthReport:
        self.ensure_tunnel()
        return self.health()

    def health(self) -> HealthReport:
        status, tunnel_health, app_health = self.inspect()
        if not tunnel_health.healthy or not status.ready:
            return HealthReport(False, RuntimeState.DEGRADED, "tunnel unhealthy")
        if app_health is not None and not app_health.healthy:
            return HealthReport(False, RuntimeState.DEGRADED, "application unhealthy")
        return HealthReport(True, RuntimeState.HEALTHY, "owned tunnel healthy")
