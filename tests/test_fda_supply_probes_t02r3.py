"""Frozen acceptance probe for Healthcare D1 T02 round 4 (seat-frozen from the r3 lane
reviewer's confirmed blocker; never lane-edited).

Law (R-T02R3-06): a sweep whose source page carries no `meta.last_updated` has no source
generation, so the CAPTURE ITSELF is unqualified with failure code NO_SOURCE_GENERATION —
not merely demoted later inside save_shortage_observation. At 4623f6e7 the public seam
`collect_shortage_sweep` still reports qualified=True / failure_code=None for such a page.
"""
from __future__ import annotations

from datetime import datetime, timezone

from collectors.fda_shortages import collect_shortage_sweep


def _row() -> dict:
    return {
        "package_ndc": "0000-0000-00",
        "generic_name": "T02R3-MOLECULE",
        "status": "Current",
        "availability": "Available",
        "initial_posting_date": "20260101",
        "update_date": "20260901",
        "openfda": {},
    }


def _fetch_page_without_generation(skip: int, limit: int) -> dict:
    return {
        "meta": {"results": {"total": 1, "skip": skip, "limit": limit}},
        "results": [_row()] if skip == 0 else [],
    }


def test_t02r3_generation_less_page_is_unqualified_at_the_public_seam():
    clock = lambda: datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
    result = collect_shortage_sweep(
        _fetch_page_without_generation, clock=clock, page_size=100, max_pages=3
    )
    assert result.get("source_generation") in (None, ""), result
    assert result.get("qualified") is False, (
        "T02R3-B1: a generation-less page qualified at the public seam: "
        f"qualified={result.get('qualified')!r} failure_code={result.get('failure_code')!r}"
    )
    assert result.get("failure_code") == "NO_SOURCE_GENERATION", result.get("failure_code")
