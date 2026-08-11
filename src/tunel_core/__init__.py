"""TUNEL-CORE: universal tunnel supervision and recovery primitives."""

from .models import ConnectionProfile, HealthReport, RetryPolicy, RuntimeState, RuntimeStatus
from .process_identity import ProcessIdentity, authorize_termination
from .recovery import RecoveryEngine
from .state import StateStore
from .supervisor import Supervisor
from .watchdog import Watchdog

__all__ = [
    "ConnectionProfile",
    "HealthReport",
    "RetryPolicy",
    "RuntimeState",
    "RuntimeStatus",
    "ProcessIdentity",
    "authorize_termination",
    "RecoveryEngine",
    "StateStore",
    "Supervisor",
    "Watchdog",
]
