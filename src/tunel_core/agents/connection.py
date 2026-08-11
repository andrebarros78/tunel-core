from __future__ import annotations

from .base import AgentResult
from ..control_plane import ConnectionManager, ConnectionState
from ..models import ConnectionProfile


class ConnectionAgent:
    name = "connection"

    def __init__(self, manager: ConnectionManager, profile: ConnectionProfile) -> None:
        self.manager = manager
        self.profile = profile

    def ensure_connected(self) -> AgentResult:
        result = self.manager.connect(self.profile)
        return AgentResult(
            agent=self.name,
            ok=bool(result.running and result.ready),
            action="ensure_connected",
            detail=result.detail,
            data={"state": self.manager.state(self.profile.connection_id).value},
        )

    def reconnect(self) -> AgentResult:
        result = self.manager.reconnect(self.profile)
        return AgentResult(
            agent=self.name,
            ok=bool(result.running and result.ready),
            action="reconnect",
            detail=result.detail,
            data={"state": self.manager.state(self.profile.connection_id).value},
        )

    def status(self) -> AgentResult:
        state = self.manager.state(self.profile.connection_id)
        return AgentResult(
            agent=self.name,
            ok=state == ConnectionState.CONNECTED,
            action="status",
            data={"state": state.value},
        )
