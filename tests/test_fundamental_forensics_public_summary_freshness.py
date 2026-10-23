"""FIF A21 — the public counts shell must not mint freshness on a re-render.

``_write_public_summary`` stamps ``datetime.now`` only when there is no
explicit ``generated_at`` AND no prior file carrying the identical projection.
A rewrite of UNCHANGED counts reuses the prior file's stamp verbatim, so the
file is byte-identical — a render lane that re-projects the same counts can
never advertise a fresher source clock than the source actually moved.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.build_fundamental_forensics import (
    PUBLIC_SUMMARY_MAX_AGE_DAYS,
    PUBLIC_SUMMARY_RELATIVE,
    PUBLIC_SUMMARY_SCHEMA,
    _write_public_summary,
    read_public_summary,
)

COUNTS = {"companies": 1240, "findings": 3417}


def _summary_path(root: Path) -> Path:
    return root / PUBLIC_SUMMARY_RELATIVE


def _stamp(path: Path) -> str:
    return json.loads(path.read_text(encoding="utf-8"))["generated_at"]


def test_rewrite_of_unchanged_counts_is_byte_identical(tmp_path: Path):
    first = _write_public_summary(tmp_path, COUNTS)  # no generated_at, no prior file
    original_bytes = first.read_bytes()
    original_stamp = _stamp(first)

    second = _write_public_summary(tmp_path, dict(COUNTS))  # same counts, still no stamp
    assert second == first
    assert second.read_bytes() == original_bytes  # byte-identical, NOT fresher
    assert _stamp(second) == original_stamp
    # A richer summary dict that projects to the same two counts is unchanged
    # for this file's purposes — the projection is the payload.
    _write_public_summary(tmp_path, {**COUNTS, "top_symbol": "SMCI", "high": 88})
    assert first.read_bytes() == original_bytes


def test_changed_counts_without_generated_at_still_write_a_fresh_stamp(tmp_path: Path):
    first = _write_public_summary(tmp_path, COUNTS)
    original_stamp = _stamp(first)
    before = datetime.now(timezone.utc) - timedelta(seconds=1)

    changed = _write_public_summary(tmp_path, {"companies": 1241, "findings": 3417})
    new_stamp = _stamp(changed)
    assert new_stamp != original_stamp
    parsed = datetime.fromisoformat(new_stamp)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    assert parsed >= before  # the fallback path genuinely stamped the clock
    assert read_public_summary(tmp_path) == {"companies": 1241, "findings": 3417}


def test_explicit_generated_at_always_wins(tmp_path: Path):
    # Over a prior file with identical counts...
    _write_public_summary(tmp_path, COUNTS)
    explicit = _write_public_summary(tmp_path, COUNTS, generated_at="2026-01-01T00:00:00+00:00")
    assert _stamp(explicit) == "2026-01-01T00:00:00+00:00"
    # ...and over a prior file with different counts. (A months-old explicit
    # stamp legitimately reads back as absent — staleness is the reader's
    # call — so assert on the file bytes, not read_public_summary.)
    explicit_again = _write_public_summary(
        tmp_path, {"companies": 1, "findings": 2}, generated_at="2026-02-02T00:00:00Z"
    )
    assert _stamp(explicit_again) == "2026-02-02T00:00:00Z"
    payload = json.loads(explicit_again.read_text(encoding="utf-8"))
    assert payload["companies"] == 1 and payload["findings"] == 2


def test_first_write_without_prior_file_stamps_and_reads_back(tmp_path: Path):
    path = _write_public_summary(tmp_path, COUNTS)
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == PUBLIC_SUMMARY_SCHEMA
    assert payload["companies"] == 1240 and payload["findings"] == 3417
    # The fresh stamp is recent enough that the committed projection reads back.
    assert read_public_summary(tmp_path) == {"companies": 1240, "findings": 3417}


def test_stale_prior_stamp_is_still_reused_verbatim(tmp_path: Path):
    # Reuse is about not FRESHENING a rewrite: even a projection whose stamp
    # has aged past the public max is carried verbatim, so a counts-unchanged
    # rewrite can never look newer than the source that produced it.
    ancient = datetime.now(timezone.utc) - timedelta(days=PUBLIC_SUMMARY_MAX_AGE_DAYS + 5)
    hand_written = {
        "schema": PUBLIC_SUMMARY_SCHEMA,
        "generated_at": ancient.isoformat(),
        "companies": 1240,
        "findings": 3417,
    }
    path = _summary_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hand_written, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    original_bytes = path.read_bytes()

    _write_public_summary(tmp_path, COUNTS)
    assert path.read_bytes() == original_bytes
    # And the aged projection still reads as absent for consumers.
    assert read_public_summary(tmp_path) == {}
