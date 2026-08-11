from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import time
from typing import Any

from .bootstrap import default_state_root
from .persistence_engine import PersistenceEngine


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
    tmp.replace(path)


def _load_supervisor(config: dict[str, Any]):
    plugin = config.get("supervisor_plugin") or {}
    module = plugin.get("module")
    factory = plugin.get("factory")
    if not module or not factory:
        return None
    target = importlib.import_module(str(module))
    creator = getattr(target, str(factory))
    supervisor = creator(config)
    if not hasattr(supervisor, "converge_once"):
        raise TypeError("supervisor plugin factory must return an object with converge_once()")
    return supervisor


def run(config_path: Path, interval: float = 5.0) -> int:
    home = default_state_root()
    heartbeat = home / "state" / "supervisor-heartbeat.json"
    log = home / "logs" / "supervisor.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    persistence = PersistenceEngine(home / "state")
    persistence.recover()
    supervisor = None
    loaded_mtime = None

    while True:
        now = time.time()
        state = "waiting_configuration"
        detail = ""
        try:
            if config_path.exists():
                mtime = config_path.stat().st_mtime_ns
                if loaded_mtime != mtime:
                    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
                    supervisor = _load_supervisor(config)
                    loaded_mtime = mtime
                if supervisor is not None:
                    report = supervisor.converge_once()
                    state = "healthy" if getattr(report, "healthy", False) else "degraded"
                    detail = getattr(report, "detail", "")
                else:
                    state = "waiting_runtime_adapter"
            _atomic_json(heartbeat, {"at": now, "state": state, "detail": detail})
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"at": now, "state": state, "detail": detail}, ensure_ascii=False) + "\n")
        except Exception as exc:
            _atomic_json(heartbeat, {"at": now, "state": "error", "detail": f"{type(exc).__name__}: {exc}"})
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"at": now, "state": "error", "detail": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False) + "\n")
        time.sleep(max(1.0, interval))


def main() -> int:
    parser = argparse.ArgumentParser(description="TUNEL-CORE supervisor runner")
    parser.add_argument("--config", default=None)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    home = default_state_root()
    config = Path(args.config) if args.config else home / "config" / "runtime.json"
    return run(config, args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
