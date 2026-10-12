"""Pin invariants of the P04 v2 pre-registration DRAFT (SNI-local contract).

This test consumes the draft documents. It does not mint identity ids, does
not load outcomes, and does not register or seal. All authority flags stay
false; a caller that sets any of them true is refused (raise).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "event_response"
    / "P04_V2_PREREG_DRAFT.json"
)
MD_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "event_response"
    / "P04_V2_PREREG_DRAFT.md"
)

AUTHORITY_FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

RETIRED_TUNE_DIGEST = (
    "a3b15693e32d9d2f44e5e4a78f90bdfb3ac2afece84b5691be12e03685804ed6"
)

FORBIDDEN_PHRASES = ("coin flip", "50/50")


def refuse_authority_true(flags: dict) -> None:
    """Refuse (raise) if a caller tries to set any authority flag true."""
    if not isinstance(flags, dict):
        raise TypeError("authority_flags must be a dict")
    for name in AUTHORITY_FLAG_NAMES:
        if flags.get(name) is True:
            raise ValueError(
                f"authority flag {name} must stay false; "
                "this draft refuses a true value"
            )
        if name not in flags:
            raise ValueError(f"authority flag {name} is missing")
        if flags[name] is not False:
            raise ValueError(
                f"authority flag {name} must be false, got {flags[name]!r}"
            )


def test_authority_true_is_refused() -> None:
    good = {name: False for name in AUTHORITY_FLAG_NAMES}
    refuse_authority_true(good)
    bad = dict(good)
    bad["rank_authority"] = True
    with pytest.raises(ValueError, match="rank_authority"):
        refuse_authority_true(bad)


def test_p04_v2_draft_invariants() -> None:
    spec = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    md = MD_PATH.read_text(encoding="utf-8")

    assert spec["registered"] is False
    assert spec["status"] == "DRAFT"
    assert spec["outcome_free"] is True
    assert spec["protocol"] == "P04"
    assert spec["version"] == "v2"

    refuse_authority_true(spec["authority_flags"])
    for name in AUTHORITY_FLAG_NAMES:
        assert spec["authority_flags"][name] is False

    nested = spec.get("labels", {}).get("authority_flags")
    if nested is not None:
        refuse_authority_true(nested)

    assert (
        spec["successor_of"]["composite_split_digest"] == RETIRED_TUNE_DIGEST
    )
    assert RETIRED_TUNE_DIGEST in md
    assert "DESCRIPTIVE_ONLY" in md
    assert "NOT registered" in md
    assert "NO outcome" in md

    json_text = JSON_PATH.read_text(encoding="utf-8")
    blob = json_text + "\n" + md
    lowered = blob.lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in lowered
