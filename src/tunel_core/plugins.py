from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .adapters import TunnelRuntimeAdapter
from .data_plane import ProviderAdapter, TransportAdapter


@dataclass(frozen=True, slots=True)
class PluginDescriptor:
    name: str
    version: str
    kind: str
    api_version: int = 1


class CorePlugin(ABC):
    descriptor: PluginDescriptor

    @abstractmethod
    def validate(self) -> None: ...


class RuntimePlugin(CorePlugin, ABC):
    @abstractmethod
    def runtime(self) -> TunnelRuntimeAdapter: ...


class TransportPlugin(CorePlugin, ABC):
    @abstractmethod
    def transport(self) -> TransportAdapter: ...


class ProviderPlugin(CorePlugin, ABC):
    @abstractmethod
    def provider(self) -> ProviderAdapter: ...


class PluginRegistry:
    """Strict registry: core owns contracts, plugins own application/provider specifics."""

    def __init__(self) -> None:
        self._plugins: dict[str, CorePlugin] = {}

    def register(self, plugin: CorePlugin) -> None:
        plugin.validate()
        descriptor = plugin.descriptor
        if descriptor.api_version != 1:
            raise ValueError(f"unsupported plugin api: {descriptor.api_version}")
        if descriptor.name in self._plugins:
            raise ValueError(f"plugin already registered: {descriptor.name}")
        self._plugins[descriptor.name] = plugin

    def get(self, name: str) -> CorePlugin:
        return self._plugins[name]

    def descriptors(self) -> tuple[PluginDescriptor, ...]:
        return tuple(plugin.descriptor for plugin in self._plugins.values())
