"""Stdlib-only shared SEC request pacer for Fundamental Forensics (FIF A20).

``SecRequestPacer`` deliberately lives in a module importing nothing beyond
the standard library so lite CI jobs (environments with no pandas, requests
or yaml installed) can import it directly.
"""
from __future__ import annotations

import threading
import time
from typing import Callable


class SecRequestPacer:
    """The ONE incumbent forensics SEC request pacer (FIF A20).

    Every forensics SEC GET in a process acquires this single object.  It
    consolidates what were three per-collector pacers (``SecForensicsCollector``,
    ``SecCompanyFactsCollector``, ``SecFilingArchiveCollector``) into one shared
    request budget, so concurrent operators in one process cannot multiply the
    SEC request rate by each building a private pacer.  It adds no scheduler,
    no queue, no token bucket, no lease and no cross-process lock: the workflow
    concurrency group ``filing-forensics-sec`` remains the only cross-process
    mutex, and the cross-host aggregate per-IP limit stays with the scheduler
    (``OPERATOR_CONSTRAINTS`` in ``fundamental_forensics_companyfacts``).
    """

    def __init__(
        self,
        *,
        min_interval_seconds: float = 0.12,
        sleeper: Callable[[float], None] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        self._min_interval_seconds = max(0.1, float(min_interval_seconds))
        # Late-bound module lookups on purpose: patching ``time.sleep`` /
        # ``time.monotonic`` (e.g. monkeypatch.setattr on the time module) keeps
        # working because the attribute is resolved at call time, exactly as the
        # pre-consolidation inline ``time.sleep``/``time.monotonic`` calls did.
        self._sleeper = sleeper if sleeper is not None else (lambda seconds: time.sleep(seconds))
        self._monotonic = monotonic if monotonic is not None else (lambda: time.monotonic())
        self._lock = threading.Lock()
        self._last_request_at: float | None = None

    @property
    def min_interval_seconds(self) -> float:
        return self._min_interval_seconds

    @property
    def last_request_at(self) -> float | None:
        """The last mark, or None before the first acquire."""
        return self._last_request_at

    def acquire(self) -> None:
        """Reserve one SEC request slot, sleeping while the interval is unmet.

        The read-compute-sleep-mark sequence holds the lock so two threads can
        never interleave two marks inside one interval.  The first acquire
        never sleeps (prior mark is None); every later one sleeps
        ``interval - (now - last)`` when positive, then marks.
        """
        with self._lock:
            last = self._last_request_at
            if last is not None:
                wait = self._min_interval_seconds - (self._monotonic() - last)
                if wait > 0:
                    self._sleeper(wait)
            self._last_request_at = self._monotonic()
