from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Callable

from .persistence_engine import CheckpointRollback, PersistenceEngine


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    state_recovered: bool
    runtime_discovered: bool
    supervisor_started: bool
    detail: str = ""


class Bootstrap:
    """Boot-time composition: recover durable state, discover runtime and start supervisor."""

    def __init__(
        self,
        persistence: PersistenceEngine,
        discover_runtime: Callable[[], bool],
        start_supervisor: Callable[[], bool],
    ) -> None:
        self.persistence = persistence
        self.discover_runtime = discover_runtime
        self.start_supervisor = start_supervisor

    def run(self) -> BootstrapResult:
        recovered = bool(self.persistence.recover())
        runtime = bool(self.discover_runtime())
        supervisor = bool(self.start_supervisor())
        return BootstrapResult(recovered, runtime, supervisor, "bootstrap complete")


class TransactionalUpdater:
    """Stages an update, validates it, then promotes or rolls back atomically where possible."""

    def __init__(self, install_root: Path, checkpoint: CheckpointRollback) -> None:
        self.install_root = install_root
        self.checkpoint = checkpoint

    def update(self, source: Path, generation: str, health_gate: Callable[[Path], bool]) -> bool:
        if not source.exists() or not source.is_dir():
            raise FileNotFoundError(source)
        self.checkpoint.checkpoint(generation)
        parent = self.install_root.parent
        parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix="tunel-core-stage-", dir=parent))
        try:
            shutil.copytree(source, stage / "payload", dirs_exist_ok=True)
            payload = stage / "payload"
            if not health_gate(payload):
                return False
            backup = parent / (self.install_root.name + ".update-backup")
            shutil.rmtree(backup, ignore_errors=True)
            if self.install_root.exists():
                os.replace(self.install_root, backup)
            os.replace(payload, self.install_root)
            shutil.rmtree(backup, ignore_errors=True)
            return True
        except Exception:
            self.checkpoint.rollback(generation)
            raise
        finally:
            shutil.rmtree(stage, ignore_errors=True)


def default_state_root() -> Path:
    base = os.environ.get("TUNEL_CORE_HOME")
    if base:
        return Path(base)
    program_data = os.environ.get("ProgramData")
    if program_data:
        return Path(program_data) / "TUNEL-CORE"
    return Path.home() / ".tunel-core"
