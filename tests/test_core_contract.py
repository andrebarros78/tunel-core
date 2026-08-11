from pathlib import Path

from tunel_core.adapters import ApplicationAdapter, TunnelRuntimeAdapter
from tunel_core.models import ConnectionProfile, HealthReport, RetryPolicy, RuntimeState, RuntimeStatus
from tunel_core.process_identity import ProcessIdentity, authorize_termination
from tunel_core.recovery import RecoveryEngine
from tunel_core.supervisor import Supervisor
from tunel_core.watchdog import Watchdog


class FakeTunnel(TunnelRuntimeAdapter):
    def __init__(self, ready=False):
        self.ready = ready
        self.connect_calls = 0

    def connect(self, profile):
        self.connect_calls += 1
        self.ready = True
        return RuntimeStatus(True, True, "connected")

    def disconnect(self, profile):
        self.ready = False
        return RuntimeStatus(False, False, "stopped")

    def status(self, profile):
        return RuntimeStatus(self.ready, self.ready)

    def health(self, profile):
        return HealthReport(self.ready, RuntimeState.HEALTHY if self.ready else RuntimeState.DEGRADED)


class HealthyApp(ApplicationAdapter):
    def __init__(self):
        self.health_calls = 0

    def health(self, profile):
        self.health_calls += 1
        return HealthReport(True, RuntimeState.HEALTHY)


def profile():
    return ConnectionProfile(
        project_id="reference",
        connection_id="c1",
        alias="reference-tunnel",
        transport="streamable-http",
        local_endpoint="http://127.0.0.1:8765/mcp",
        remote_provider="adapter",
        retry_policy=RetryPolicy(initial_seconds=0, maximum_seconds=0, max_attempts=2),
    )


def test_stale_pid_cannot_authorize_kill():
    expected = ProcessIdentity(123, r"C:\\core\\tunnel.exe", "tunnel connect --alias x", 10)
    reused = ProcessIdentity(123, r"C:\\Program Files\\Browser\\browser.exe", "browser.exe", 99)
    assert authorize_termination(expected, reused) is False


def test_same_identity_can_authorize_kill():
    expected = ProcessIdentity(123, r"C:\\core\\tunnel.exe", "tunnel connect --alias x", 10)
    actual = ProcessIdentity(123, r"C:\\core\\tunnel.exe", "tunnel connect --alias x", 10)
    assert authorize_termination(expected, actual) is True


def test_supervisor_repairs_tunnel_without_application_restart():
    tunnel = FakeTunnel(False)
    app = HealthyApp()
    supervisor = Supervisor(profile(), tunnel, RecoveryEngine(profile().retry_policy, sleeper=lambda _: None), app)
    status = supervisor.ensure_tunnel()
    assert status.ready is True
    assert tunnel.connect_calls == 1
    assert app.health_calls == 1


def test_healthy_tunnel_is_not_restarted():
    tunnel = FakeTunnel(True)
    supervisor = Supervisor(profile(), tunnel, RecoveryEngine(profile().retry_policy, sleeper=lambda _: None))
    status = supervisor.ensure_tunnel()
    assert status.ready is True
    assert tunnel.connect_calls == 0


def test_watchdog_only_recovers_supervisor():
    started = []
    watchdog = Watchdog(lambda: False, lambda: started.append("supervisor") or True)
    assert watchdog.tick() is True
    assert started == ["supervisor"]
