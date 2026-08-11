"""TUNEL-CORE: persistent, multichannel, provider-neutral connectivity core."""

from .adapters import ApplicationAdapter, CredentialResolver as CredentialResolverProtocol, TunnelRuntimeAdapter
from .bootstrap import Bootstrap, BootstrapResult, TransactionalUpdater, default_state_root
from .control_plane import ConnectionManager, ConnectionState, CredentialResolver, HealthEngine, HealthSample, ProfileManager
from .data_plane import ConcurrencyFlowManager, Frame, HighFlowDataPlane, MultiChannelManager, ProviderAdapter, TransportAdapter
from .models import ConnectionProfile, HealthReport, RetryPolicy, RuntimeState, RuntimeStatus
from .observability import Observability
from .ownership import Lease, OwnershipLeaseManager, Session, SessionManager
from .persistence_engine import CheckpointRollback, PersistenceEngine
from .plugins import PluginDescriptor, PluginRegistry
from .process_identity import ProcessIdentity, authorize_termination
from .recovery import RecoveryEngine
from .reliability import CircuitBreaker, CircuitState, ReliabilityEngine, RetryBudget
from .selftest import CheckResult, SelfTest, SelfTestReport
from .state import StateStore
from .supervisor import Supervisor
from .watchdog import Watchdog

__version__ = "0.2.0"

__all__ = [
    "ApplicationAdapter", "Bootstrap", "BootstrapResult", "CheckpointRollback", "CheckResult",
    "CircuitBreaker", "CircuitState", "ConcurrencyFlowManager", "ConnectionManager", "ConnectionProfile",
    "ConnectionState", "CredentialResolver", "Frame", "HealthEngine", "HealthReport", "HealthSample",
    "HighFlowDataPlane", "Lease", "MultiChannelManager", "Observability", "OwnershipLeaseManager",
    "PersistenceEngine", "PluginDescriptor", "PluginRegistry", "ProcessIdentity", "ProfileManager",
    "ProviderAdapter", "RecoveryEngine", "ReliabilityEngine", "RetryBudget", "RetryPolicy", "RuntimeState",
    "RuntimeStatus", "SelfTest", "SelfTestReport", "Session", "SessionManager", "StateStore", "Supervisor",
    "TransactionalUpdater", "TransportAdapter", "TunnelRuntimeAdapter", "Watchdog", "authorize_termination",
    "default_state_root",
]
