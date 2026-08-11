from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
import os
from pathlib import Path
import shutil
import threading
import time
from typing import Any


class PersistenceEngine:
    """Durable JSON state with journaled, atomic replacement and crash recovery."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _safe(self, key: str) -> str:
        safe = "".join(c for c in key if c.isalnum() or c in "-_.")
        if not safe or safe != key:
            raise ValueError("invalid persistence key")
        return safe

    def _paths(self, key: str) -> tuple[Path, Path, Path]:
        safe = self._safe(key)
        return (
            self.root / f"{safe}.json",
            self.root / f"{safe}.tmp",
            self.root / f"{safe}.journal",
        )

    def write(self, key: str, value: Any) -> Path:
        path, tmp, journal = self._paths(key)
        payload = asdict(value) if is_dataclass(value) else value
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
        with self._lock:
            journal.write_text(json.dumps({"op": "replace", "target": path.name, "at": time.time()}), encoding="utf-8")
            with open(tmp, "wb") as fh:
                fh.write(encoded)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            journal.unlink(missing_ok=True)
        return path

    def read(self, key: str) -> Any | None:
        path, _, _ = self._paths(key)
        with self._lock:
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))

    def recover(self) -> list[str]:
        recovered: list[str] = []
        with self._lock:
            for journal in self.root.glob("*.journal"):
                key = journal.stem
                path, tmp, _ = self._paths(key)
                if tmp.exists():
                    os.replace(tmp, path)
                    recovered.append(key)
                journal.unlink(missing_ok=True)
        return recovered


class CheckpointRollback:
    """Versioned snapshots with atomic restore."""

    def __init__(self, state_root: Path, checkpoint_root: Path) -> None:
        self.state_root = state_root
        self.checkpoint_root = checkpoint_root
        self.checkpoint_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def checkpoint(self, generation: str) -> Path:
        if not generation or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for c in generation):
            raise ValueError("invalid generation")
        target = self.checkpoint_root / generation
        temp = self.checkpoint_root / f".{generation}.tmp"
        with self._lock:
            shutil.rmtree(temp, ignore_errors=True)
            if self.state_root.exists():
                shutil.copytree(self.state_root, temp)
            else:
                temp.mkdir(parents=True)
            (temp / "checkpoint.json").write_text(json.dumps({"generation": generation, "created_at": time.time()}), encoding="utf-8")
            shutil.rmtree(target, ignore_errors=True)
            os.replace(temp, target)
        return target

    def rollback(self, generation: str) -> None:
        source = self.checkpoint_root / generation
        if not source.exists():
            raise FileNotFoundError(generation)
        temp = self.state_root.with_name(self.state_root.name + ".rollback")
        with self._lock:
            shutil.rmtree(temp, ignore_errors=True)
            shutil.copytree(source, temp, ignore=shutil.ignore_patterns("checkpoint.json"))
            backup = self.state_root.with_name(self.state_root.name + ".before-rollback")
            shutil.rmtree(backup, ignore_errors=True)
            if self.state_root.exists():
                os.replace(self.state_root, backup)
            os.replace(temp, self.state_root)
            shutil.rmtree(backup, ignore_errors=True)
