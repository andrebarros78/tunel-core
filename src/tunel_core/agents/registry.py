from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .base import AgentResult, CoreAgent


@dataclass(slots=True)
class AgentRegistry:
    _agents: dict[str, CoreAgent] = field(default_factory=dict)

    def register(self, agent: CoreAgent) -> None:
        if not agent.name:
            raise ValueError("agent name is required")
        if agent.name in self._agents:
            raise ValueError(f"agent already registered: {agent.name}")
        self._agents[agent.name] = agent

    def get(self, name: str) -> CoreAgent:
        return self._agents[name]

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._agents))

    def statuses(self) -> tuple[AgentResult, ...]:
        return tuple(self._agents[name].status() for name in self.names())

    @classmethod
    def from_agents(cls, agents: Iterable[CoreAgent]) -> "AgentRegistry":
        registry = cls()
        for agent in agents:
            registry.register(agent)
        return registry
