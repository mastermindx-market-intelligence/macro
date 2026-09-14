from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapacityWindow:
    used_percent: int | None
    reset_at: str | None = None


@dataclass(frozen=True)
class CapacityEvidence:
    account_id: str
    observed_at: str
    rolling: CapacityWindow
    weekly: CapacityWindow
    monthly: CapacityWindow
    concurrency_used: int | None = None
    concurrency_limit: int | None = None
