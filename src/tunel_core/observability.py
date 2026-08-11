from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
import json
import math
import threading
import time
from typing import Deque


@dataclass(slots=True)
class MetricPoint:
    name: str
    value: float
    at: float = field(default_factory=time.time)
    labels: dict[str, str] = field(default_factory=dict)


class Observability:
    """Bounded in-memory events/metrics suitable for export by adapters."""

    def __init__(self, max_events: int = 10000, max_metrics: int = 20000) -> None:
        self._events: Deque[dict] = deque(maxlen=max_events)
        self._metrics: Deque[MetricPoint] = deque(maxlen=max_metrics)
        self._lock = threading.Lock()

    def event(self, name: str, **fields) -> None:
        record = {"event": name, "at": time.time(), **fields}
        safe = {k: v for k, v in record.items() if "secret" not in k.lower() and "credential" not in k.lower()}
        with self._lock:
            self._events.append(safe)

    def metric(self, name: str, value: float, **labels: str) -> None:
        if math.isnan(value) or math.isinf(value):
            raise ValueError("metric value must be finite")
        with self._lock:
            self._metrics.append(MetricPoint(name, float(value), labels=dict(labels)))

    def percentile(self, name: str, p: float) -> float | None:
        if not 0 <= p <= 100:
            raise ValueError("percentile out of range")
        with self._lock:
            values = sorted(point.value for point in self._metrics if point.name == name)
        if not values:
            return None
        index = min(len(values) - 1, max(0, math.ceil((p / 100) * len(values)) - 1))
        return values[index]

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "events": list(self._events),
                "metrics": [asdict(m) for m in self._metrics],
            }

    def json_lines(self) -> str:
        snap = self.snapshot()
        rows = [json.dumps(row, ensure_ascii=False, default=str) for row in snap["events"]]
        rows.extend(json.dumps(row, ensure_ascii=False, default=str) for row in snap["metrics"])
        return "\n".join(rows)
