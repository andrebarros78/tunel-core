from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from .models import ConnectionProfile, HealthReport, RuntimeStatus


class CredentialResolver(Protocol):
    def resolve(self, reference: str) -> str: ...


class TunnelRuntimeAdapter(ABC):
    """Boundary between TUNEL-CORE and the concrete tunnel provider/runtime."""

    @abstractmethod
    def connect(self, profile: ConnectionProfile) -> RuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self, profile: ConnectionProfile) -> RuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    def status(self, profile: ConnectionProfile) -> RuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    def health(self, profile: ConnectionProfile) -> HealthReport:
        raise NotImplementedError


class ApplicationAdapter(ABC):
    """Optional application-side probe. Core never owns the application lifecycle by default."""

    @abstractmethod
    def health(self, profile: ConnectionProfile) -> HealthReport:
        raise NotImplementedError
