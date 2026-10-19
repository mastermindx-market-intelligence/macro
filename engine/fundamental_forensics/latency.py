"""Bounded in-process latency distributions and declared SLO budgets (FIF V0-a).

Pure stdlib; the only I/O is ``load_slo_config`` reading its config file. The
recorder keeps a fixed-size window of ``(duration_ms, status)`` samples per
route template, with at most 64 distinct templates — every further template
shares the single ``__overflow__`` bucket, so memory stays bounded no matter
what a future mount adds. Percentiles are NEAREST RANK over the windowed
samples (``index = ceil(q * n) - 1``, no interpolation), rounded to 0.1 ms.
Nothing here fetches, parses filings, or talks to the network.
"""
from __future__ import annotations

import json
import math
import threading
from collections import deque
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "fif_slo.v1"
MAX_TEMPLATES = 64
OVERFLOW_TEMPLATE = "__overflow__"
_PERCENTILES = (("p50_ms", 0.50), ("p95_ms", 0.95), ("p99_ms", 0.99))


def _nearest_rank(sorted_values: list[float], q: float) -> float:
    """Nearest-rank percentile: the value at index ``ceil(q * n) - 1``."""
    index = math.ceil(q * len(sorted_values)) - 1
    return sorted_values[index]


class LatencyRecorder:
    """One bounded sample window plus a monotonic total, per route template."""

    def __init__(self, window: int = 512) -> None:
        self._window = max(1, int(window))
        self._lock = threading.Lock()
        self._samples: dict[str, deque[tuple[float, int]]] = {}
        self._count_total: dict[str, int] = {}

    def record(self, template: str, duration_ms: float, status: int) -> None:
        with self._lock:
            key = template
            if key not in self._samples and len(self._samples) >= MAX_TEMPLATES:
                key = OVERFLOW_TEMPLATE
            samples = self._samples.get(key)
            if samples is None:
                samples = deque(maxlen=self._window)
                self._samples[key] = samples
            samples.append((float(duration_ms), int(status)))
            self._count_total[key] = self._count_total.get(key, 0) + 1

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """A sorted, point-in-time copy; never a live view of the windows."""
        with self._lock:
            captured = {
                key: (list(samples), self._count_total.get(key, 0))
                for key, samples in self._samples.items()
            }
        report: dict[str, dict[str, Any]] = {}
        for key in sorted(captured):
            samples, count_total = captured[key]
            durations = sorted(duration for duration, _status in samples)
            if durations:
                percentiles = {
                    name: round(_nearest_rank(durations, q), 1)
                    for name, q in _PERCENTILES
                }
                max_ms: float | None = round(durations[-1], 1)
            else:
                percentiles = {name: None for name, _q in _PERCENTILES}
                max_ms = None
            report[key] = {
                "count_total": count_total,
                "window_n": len(durations),
                "p50_ms": percentiles["p50_ms"],
                "p95_ms": percentiles["p95_ms"],
                "p99_ms": percentiles["p99_ms"],
                "max_ms": max_ms,
                "error_n": sum(1 for _d, status in samples if status >= 500),
            }
        return report

    def reset(self) -> None:
        """Test seam: drop every window and total."""
        with self._lock:
            self._samples.clear()
            self._count_total.clear()


RECORDER = LatencyRecorder()


def _positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value > 0
    )


def load_slo_config(path: str | Path) -> dict[str, Any]:
    """Load and refuse a declared SLO config. The only I/O in this module.

    Refuses (``ValueError``) a config whose ``schema_version`` is not
    ``fif_slo.v1``, one with a route budget that is not a positive number,
    and one whose ``p95_ms`` budget exceeds its ``p99_ms``.
    """
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("slo config must be a JSON object")
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("slo config schema_version must be fif_slo.v1")
    if not isinstance(config.get("status"), str) or not config["status"]:
        raise ValueError("slo config status must be a non-empty string")
    if not _positive_number(config.get("window")):
        raise ValueError("slo config window must be a positive number")
    if not _positive_number(config.get("min_samples")):
        raise ValueError("slo config min_samples must be a positive number")
    routes = config.get("routes")
    if not isinstance(routes, dict) or not routes:
        raise ValueError("slo config must carry a non-empty routes mapping")
    for template, budget in routes.items():
        if not isinstance(budget, dict):
            raise ValueError(f"route budget must be an object: {template}")
        p95 = budget.get("p95_ms")
        p99 = budget.get("p99_ms")
        if not _positive_number(p95) or not _positive_number(p99):
            raise ValueError(f"route budgets must be positive numbers: {template}")
        if p95 > p99:
            raise ValueError(f"route p95 budget exceeds p99: {template}")
    return config


def evaluate_slo(snapshot: dict[str, dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    """Judge a measured snapshot against the declared budgets.

    One entry per configured template — ``insufficient_samples`` below
    ``min_samples``, ``breach`` when a measured p95/p99 exceeds its budget,
    ``within`` otherwise. A measured template with no budget is named under
    ``unbudgeted``, never silently dropped.
    """
    routes_config = config.get("routes", {})
    min_samples = int(config.get("min_samples", 1))
    evaluated: dict[str, dict[str, Any]] = {}
    for template in sorted(routes_config):
        budget = routes_config[template]
        budget_p95 = budget["p95_ms"]
        budget_p99 = budget["p99_ms"]
        measured = snapshot.get(template, {})
        window_n = int(measured.get("window_n", 0))
        p95 = measured.get("p95_ms")
        p99 = measured.get("p99_ms")
        if window_n < min_samples or p95 is None or p99 is None:
            state = "insufficient_samples"
        elif p95 > budget_p95 or p99 > budget_p99:
            state = "breach"
        else:
            state = "within"
        evaluated[template] = {
            "state": state,
            "p95_ms": p95,
            "p99_ms": p99,
            "budget_p95_ms": budget_p95,
            "budget_p99_ms": budget_p99,
            "window_n": window_n,
        }
    unbudgeted = sorted(key for key in snapshot if key not in routes_config)
    return {"routes": evaluated, "unbudgeted": unbudgeted}
