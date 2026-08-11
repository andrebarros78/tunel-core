from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class RuntimeState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    initial_seconds: float = 1.0
    maximum_seconds: float = 60.0
    multiplier: float = 2.0
    max_attempts: int = 0  # 0 = unlimited


@dataclass(frozen=True, slots=True)
class ConnectionProfile:
    project_id: str
    connection_id: str
    alias: str
    transport: str
    local_endpoint: str
    remote_provider: str
    credential_reference: str | None = None
    health_strategy: str = "adapter"
    startup_policy: str = "on_boot"
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    normal_capacity: int = 16
    peak_capacity: int = 32
    timeout_seconds: float = 10.0
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.project_id or not self.connection_id or not self.alias:
            raise ValueError("project_id, connection_id and alias are required")
        if self.normal_capacity < 1:
            raise ValueError("normal_capacity must be >= 1")
        if self.peak_capacity < self.normal_capacity:
            raise ValueError("peak_capacity must be >= normal_capacity")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")


@dataclass(frozen=True, slots=True)
class HealthReport:
    healthy: bool
    state: RuntimeState
    detail: str = ""


@dataclass(frozen=True, slots=True)
class RuntimeStatus:
    running: bool
    ready: bool
    detail: str = ""
