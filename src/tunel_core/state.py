from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any


class StateStore:
    """Atomic JSON state/checkpoint store with no application-specific paths."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = "".join(c for c in key if c.isalnum() or c in "-_.")
        if not safe or safe != key:
            raise ValueError("invalid state key")
        return self.root / f"{safe}.json"

    def write(self, key: str, value: Any) -> Path:
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        payload = asdict(value) if hasattr(value, "__dataclass_fields__") else value
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)
        return path

    def read(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
