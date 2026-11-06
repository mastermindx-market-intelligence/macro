"""M6B killing tests for s2_collapse._programme_key and p04_v2_draft_loader
validators (2026-10-14).

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay false.
Fixtures are synthetic. Residuals and event-study numbers are descriptive,
never causal, never a news-impact claim.

Each test_m6b_* docstring names one non-equivalent mutant that survived the
2026-10-13 sweep (seed 20261014): file:line, original -> mutated.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
P04_DIR = ROOT / "research" / "single_name_intelligence" / "event_response"
P04_JSON = P04_DIR / "P04_V2_PREREG_DRAFT.json"

if str(P04_DIR) not in sys.path:
    sys.path.insert(0, str(P04_DIR))

import p04_v2_draft_loader as p04_loader  # noqa: E402
from s2_collapse import _programme_key  # noqa: E402


def _raw_draft() -> dict:
    return json.loads(P04_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# s2_collapse._programme_key — module-level EQUIVALENT until a direct caller
# test exercises it. _programme_key is defined but never imported by step2
# dedup, so mutations on it were not observable through run_collapse.
# ---------------------------------------------------------------------------


def test_m6b_s2_collapse__programme_key_1() -> None:
    """s2_collapse.py:111 `in` -> `not in` (programme match)."""
    r = {"id": "r1", "issuer_key": "alibaba"}
    programmes = [{"key": "placing:alibaba", "member_ids": ["r1", "r2"]}]
    assert _programme_key(r, programmes) == "placing:alibaba"


def test_m6b_s2_collapse__programme_key_2() -> None:
    """s2_collapse.py:112 `return p["key"]` -> `return None`."""
    r = {"id": "r1", "issuer_key": "alibaba"}
    programmes = [{"key": "placing:alibaba", "member_ids": ["r1", "r2"]}]
    assert _programme_key(r, programmes) is not None
    assert _programme_key(r, programmes) == "placing:alibaba"


def test_m6b_s2_collapse__programme_key_3() -> None:
    """s2_collapse.py:113 `return None` -> `return p["key"]` for unmatched."""
    r = {"id": "r9", "issuer_key": "alibaba"}
    programmes = [{"key": "placing:alibaba", "member_ids": ["r1", "r2"]}]
    assert _programme_key(r, programmes) is None


def test_m6b_s2_collapse__programme_key_4() -> None:
    """s2_collapse.py:111 if `r['id'] in p['member_ids']` negated."""
    r = {"id": "r1", "issuer_key": "alibaba"}
    programmes = [{"key": "placing:alibaba", "member_ids": ["r1", "r2"]}]
    # A negated guard would never match a real member; pinned to "placing:...".
    assert _programme_key(r, programmes) == "placing:alibaba"
    # And the empty programme list still yields None.
    assert _programme_key(r, []) is None


# ---------------------------------------------------------------------------
# p04_v2_draft_loader validator survivors
# ---------------------------------------------------------------------------


def test_m6b_p04__check_tune_empty_table_rows_or_members_refused_5() -> None:
    """p04_v2_draft_loader.py:206 `or` -> `and` on table.get fallback chain."""
    draft = _raw_draft()
    draft["membership_table"] = {"rows": [{"episode_id": "synthetic-ep-1"}]}
    with pytest.raises(ValueError, match="membership_table is non-empty"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__check_tune_empty_tune_must_be_empty_string_6() -> None:
    """p04_v2_draft_loader.py:196 negate `'EMPTY' not in tune`."""
    draft = _raw_draft()
    draft["splits"] = dict(draft["splits"])
    # Original refuses anything that lacks 'EMPTY'. Negated guard accepts.
    draft["splits"]["TUNE"] = "OPEN"
    with pytest.raises(ValueError, match="splits.TUNE is not EMPTY"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__parse_utc_timestamp_rejects_naive_7() -> None:
    """p04_v2_draft_loader.py:86 negate `parsed.tzinfo is None`."""
    with pytest.raises(ValueError, match="not timezone-aware UTC"):
        p04_loader._parse_utc_timestamp("2025-01-02T00:00:00", "ts")


def test_m6b_p04__check_as_of_rule_rejects_missing_keys_8() -> None:
    """p04_v2_draft_loader.py:173 cmp_flip `key not in as_of` -> `in as_of`."""
    draft = _raw_draft()
    as_of = draft["vintage_rule"]["as_of_utc"]
    # Drop a required key — original refuses; mutated guard would accept it.
    del as_of["equals"]
    with pytest.raises(ValueError, match="vintage_rule.as_of_utc.equals is missing"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__check_authority_block_rejects_missing_flag_names_9() -> None:
    """p04_v2_draft_loader.py:132 cmp_flip `name not in flags` -> `in flags`."""
    draft = _raw_draft()
    flags = dict(draft["authority_flags"])
    del flags["rank_authority"]
    draft["authority_flags"] = flags
    with pytest.raises(ValueError, match="rank_authority is missing"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__label_for_returns_tested_at_min_threshold_10() -> None:
    """p04_v2_draft_loader.py:123 negate `episodes < min_episodes`."""
    # At-threshold case: the original returns TESTED; the mutated guard flips
    # to DESCRIPTIVE_ONLY because the inequality becomes ==.
    assert p04_loader.label_for(153, 2, 153) == "TESTED"


def test_m6b_p04__label_for_min_clusters_3_11() -> None:
    """p04_v2_draft_loader.py:121 `2` -> `3` (TESTED min_clusters)."""
    # Original label_for refuses TESTED below 2; mutant refuses TESTED below 3.
    assert p04_loader.label_for(500, 2, 11) == "TESTED"
    assert p04_loader.label_for(500, 3, 11) == "TESTED"


def test_m6b_p04__refuse_smuggled_authority_walks_string_keys_12() -> None:
    """p04_v2_draft_loader.py:148 negate `isinstance(key, str)` guard."""
    # A smuggled authority inside a string-keyed dict must still be refused.
    draft = _raw_draft()
    draft["nested_dict"] = {"alliance_authority": True}
    with pytest.raises(ValueError, match="alliance_authority"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__refuse_smuggled_authority_recognises_authority_keys_13() -> None:
    """p04_v2_draft_loader.py:149 negate authority-key detection `BoolOp`."""
    # Original guards a True under a name that ENDS in '_authority' even when
    # the name is not in AUTHORITY_FLAG_NAMES. Mutated guard skips it.
    draft = _raw_draft()
    draft["nested_dict"] = {"alliance_authority": True}
    with pytest.raises(ValueError, match="alliance_authority"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__validate_draft_rejects_whitespace_family_n_14() -> None:
    """p04_v2_draft_loader.py:295 `or` -> `and` on `isinstance ... or strip`."""
    draft = _raw_draft()
    draft["trial_ledger"] = dict(draft["trial_ledger"])
    draft["trial_ledger"]["family_n"] = "   "
    with pytest.raises(ValueError, match="family_n is missing"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__validate_draft_rejects_naive_vintage_timestamp_15() -> None:
    """p04_v2_draft_loader.py:86 cmp_flip `tzinfo is None` -> `is not None`.

    Naive timestamps must be refused; only the original guard fires on
    `tzinfo is None`. The mutated guard flips to `is not None`, so naive
    timestamps are accepted — the test fails on the mutant.
    """
    with pytest.raises(ValueError, match="not timezone-aware UTC"):
        p04_loader._parse_utc_timestamp("2025-01-02T00:00:00", "ts")


def test_m6b_p04__check_as_of_rule_rejects_key_not_in_as_of_16() -> None:
    """p04_v2_draft_loader.py:173 negate `key not in as_of`."""
    draft = _raw_draft()
    as_of = copy.deepcopy(draft["vintage_rule"]["as_of_utc"])
    del as_of["per_episode"]
    draft["vintage_rule"] = dict(draft["vintage_rule"])
    draft["vintage_rule"]["as_of_utc"] = as_of
    with pytest.raises(ValueError, match="as_of_utc.per_episode is missing"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__check_authority_block_rejects_flag_present_17() -> None:
    """p04_v2_draft_loader.py:132 negate `name not in flags`."""
    draft = _raw_draft()
    flags = dict(draft["authority_flags"])
    # Drop a flag; mutated code (negated guard) refuses to fail here.
    del flags["size_authority"]
    draft["authority_flags"] = flags
    with pytest.raises(ValueError, match="size_authority is missing"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__parse_utc_timestamp_tzinfo_negation_18() -> None:
    """p04_v2_draft_loader.py:86 negate `parsed.tzinfo is None` (alias)."""
    # A naive parsed timestamp is rejected — guard must fire on None tzinfo.
    with pytest.raises(ValueError, match="not timezone-aware UTC"):
        p04_loader._parse_utc_timestamp("2025-01-02T00:00:00", "vintage")


# ---------------------------------------------------------------------------
# Additional killing tests for second-pass survivors.
# ---------------------------------------------------------------------------


def test_m6b_p04__label_for_bool_or_int_check_19() -> None:
    """p04_v2_draft_loader.py:115 `or` -> `and` on `isinstance bool or int`."""
    # With `or` -> `and`, label_for would accept bool values (True/False) as
    # the episodes count. The original raises on a bool.
    with pytest.raises(ValueError, match="episodes must be int"):
        p04_loader.label_for(True, 2, 153)
    with pytest.raises(ValueError, match="clusters must be int"):
        p04_loader.label_for(10, False, 153)


def test_m6b_p04__label_for_zero_means_abstain_20() -> None:
    """p04_v2_draft_loader.py:119 `0` -> `1` (episodes == 0 abstain gate)."""
    # Original returns ABSTAIN_NO_EPISODES for episodes=0. With the constant
    # bumped to 1, episodes=0 falls through to DESCRIPTIVE_ONLY instead.
    assert p04_loader.label_for(0, 2, 153) == "ABSTAIN_NO_EPISODES"
    assert p04_loader.label_for(0, 5, 153) == "ABSTAIN_NO_EPISODES"


def test_m6b_p04__check_tune_empty_dict_membership_must_be_empty_21() -> None:
    """p04_v2_draft_loader.py:193 negate `'EMPTY' not in membership`."""
    # The dict-branch membership check refuses a non-EMPTY string under the
    # original guard. The negated guard accepts it.
    draft = _raw_draft()
    draft["splits"] = dict(draft["splits"])
    draft["splits"]["TUNE"] = {"membership": "OPEN", "members": []}
    with pytest.raises(ValueError, match="splits.TUNE is not EMPTY"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__check_as_of_rule_key_equality_guard_22() -> None:
    """p04_v2_draft_loader.py:173 cmp_flip `key not in as_of` -> `==`."""
    # Original fires when key is missing from as_of; mutated guard compares
    # the key string to the as_of dict (always False), so the guard misses.
    draft = _raw_draft()
    as_of = copy.deepcopy(draft["vintage_rule"]["as_of_utc"])
    del as_of["format"]
    draft["vintage_rule"] = dict(draft["vintage_rule"])
    draft["vintage_rule"]["as_of_utc"] = as_of
    with pytest.raises(ValueError, match="vintage_rule.as_of_utc.format is missing"):
        p04_loader.validate_draft(draft)


def test_m6b_p04__check_tune_empty_dict_members_or_table_refused_23() -> None:
    """p04_v2_draft_loader.py:189 `or` -> `and` on tune.get fallback chain.

    The dict-branch fallback builds `members` from either `members` or
    `membership_table`. Flipping the chain to `and` collapses every value to
    None, so `if members:` never fires. The original refuses a populated
    `members` list.
    """
    draft = _raw_draft()
    draft["splits"] = dict(draft["splits"])
    draft["splits"]["TUNE"] = {
        "membership": "EMPTY",
        "members": [{"episode_id": "synthetic-ep-1"}],
    }
    with pytest.raises(ValueError, match="splits.TUNE describes members"):
        p04_loader.validate_draft(draft)