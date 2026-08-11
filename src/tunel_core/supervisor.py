from __future__ import annotations

from dataclasses import dataclass

from .adapters import ApplicationAdapter, TunnelRuntimeAdapter
from .models import ConnectionProfile, HealthReport, RuntimeState, RuntimeStatus
from .recovery import RecoveryEngine


@dataclass(slots=True)
class Supervisor:
    profile: ConnectionProfile
    tunnel: TunnelRuntimeAdapter
    recovery: RecoveryEngine
    application: ApplicationAdapter | None = None

    def inspect(self) -> tuple[RuntimeStatus, HealthReport, HealthReport | None]:
        tunnel_status = self.tunnel.status(self.profile)
        tunnel_health = self.tunnel.health(self.profile)
        app_health = self.application.health(self.profile) if self.application else None
        return tunnel_status, tunnel_health, app_health

    def ensure_tunnel(self) -> RuntimeStatus:
        status, tunnel_health, _ = self.inspect()
        if status.running and status.ready and tunnel_health.healthy:
            return status

        # Deliberately repairs only the tunnel. A healthy application is never restarted here.
        return self.recovery.run(
            lambda: self.tunnel.connect(self.profile),
            lambda current: current.running and current.ready,
        )

    def health(self) -> HealthReport:
        status, tunnel_health, app_health = self.inspect()
        if not tunnel_health.healthy or not status.ready:
            return HealthReport(False, RuntimeState.DEGRADED, "tunnel unhealthy")
        if app_health is not None and not app_health.healthy:
            return HealthReport(False, RuntimeState.DEGRADED, "application unhealthy")
        return HealthReport(True, RuntimeState.HEALTHY, "tunnel and observed application healthy")
