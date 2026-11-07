"""Pin invariants of the P04 v2 pre-registration DRAFT (SNI-local contract).

This test consumes the draft documents. It does not mint identity ids, does
not load outcomes, and does not register or seal. All authority flags stay
false; a caller that sets any of them true is refused (raise).
"""
from __future__ import annotations

import json
import re
import sys
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
LOADER_DIR = JSON_PATH.parent
if str(LOADER_DIR) not in sys.path:
    sys.path.insert(0, str(LOADER_DIR))

import p04_v2_draft_loader as draft_loader  # noqa: E402

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
IDENTITY_FORBIDDEN = re.compile(r"SEC:|9988|0700")
VINTAGE_PIN_KEYS = (
    "per_episode_pin",
    "cross_vintage_detector",
    "train_read_ceiling",
)
LABELS = (
    "ABSTAIN_NO_EPISODES",
    "ABSTAIN_INSUFFICIENT_CLUSTERS",
    "DESCRIPTIVE_ONLY",
    "TESTED",
)
REG_SEAL_ITEM = (
    "v2 membership seal row in REG §6 (not minted by this draft)"
)


def _raw_draft() -> dict:
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


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
    assert spec["outcome"] is None
    assert spec["seal"] is None

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


def test_r1_01_vintage_pin_fields_required() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    for key in VINTAGE_PIN_KEYS:
        assert key in loaded["vintage_rule"]
        mutated = _raw_draft()
        del mutated["vintage_rule"][key]
        with pytest.raises(ValueError, match=key):
            draft_loader.validate_draft(mutated)


@pytest.mark.parametrize("bad", ["2024-01-02", "yesterday"])
def test_r1_02_non_iso_as_of_raises(bad: str) -> None:
    with pytest.raises(ValueError):
        draft_loader.check_episode_as_of(
            bad, "2024-01-02T00:00:00Z", "2024-01-01T00:00:00Z"
        )


@pytest.mark.parametrize(
    "bad",
    ["2024-01-02T00:00:00+00:00", "2024-01-02T00:00:00-05:00"],
)
def test_r1_02_non_utc_offset_as_of_raises(bad: str) -> None:
    with pytest.raises(ValueError):
        draft_loader.check_episode_as_of(
            bad, "2024-01-02T00:00:00Z", "2024-01-01T00:00:00Z"
        )


def test_r1_02_as_of_utc_machine_checkable() -> None:
    mutated = _raw_draft()
    del mutated["vintage_rule"]["as_of_utc"]
    with pytest.raises(ValueError, match="as_of_utc"):
        draft_loader.validate_draft(mutated)

    with pytest.raises(ValueError, match="differs from decision_utc"):
        draft_loader.check_episode_as_of(
            "2024-01-03T00:00:00Z",
            "2024-01-02T00:00:00Z",
            "2024-01-01T00:00:00Z",
        )
    with pytest.raises(ValueError, match="input_vintage_utc"):
        draft_loader.check_episode_as_of(
            "2024-01-02T00:00:00Z",
            "2024-01-02T00:00:00Z",
            "2024-01-02T00:00:01Z",
        )

    draft_loader.check_episode_as_of(
        "2024-01-02T00:00:00Z",
        "2024-01-02T00:00:00Z",
        "2024-01-02T00:00:00Z",
    )
    draft_loader.check_episode_as_of(
        "2023-12-29T21:00:00Z",
        "2023-12-29T21:00:00Z",
        "2023-12-29T20:59:59Z",
    )


def test_r1_03_successor_citation_anchored() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    citation = loaded["successor_of"]["register_citation"]
    assert citation["digest"] == loaded["successor_of"]["composite_split_digest"]
    assert citation["section"] == "§7 Retirement Log"
    assert REG_SEAL_ITEM in loaded["registration_gate"]["requires"]

    missing = _raw_draft()
    del missing["successor_of"]["register_citation"]
    with pytest.raises(ValueError, match="register_citation"):
        draft_loader.validate_draft(missing)

    mismatch = _raw_draft()
    mismatch["successor_of"]["register_citation"]["digest"] = "0" * 64
    with pytest.raises(ValueError, match="digest differs"):
        draft_loader.validate_draft(mismatch)


def test_r1_04_tuning_rule_closed() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    assert loaded["tuning"]["mode"] == "UNTUNED"
    assert loaded["tuning"]["selectors"] == []
    assert loaded["tuning"]["test_conditional_selection"] == "REFUSED"

    mode = _raw_draft()
    mode["tuning"]["mode"] = "TRAIN_ONLY"
    with pytest.raises(ValueError, match="tuning.mode"):
        draft_loader.validate_draft(mode)

    selectors = _raw_draft()
    selectors["tuning"]["selectors"] = ["pick_winner_on_test"]
    with pytest.raises(ValueError, match="tuning.selectors"):
        draft_loader.validate_draft(selectors)

    cond = _raw_draft()
    cond["tuning"]["test_conditional_selection"] = "ALLOWED"
    with pytest.raises(ValueError, match="test_conditional_selection"):
        draft_loader.validate_draft(cond)


def test_r1_05_budget_floor_is_six() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    assert loaded["trial_ledger"]["declared_budget_floor"] == 6
    source = loaded["trial_ledger"]["declared_budget_floor_source"]
    assert "SEAL_AND_BUDGET.json" in source
    assert "carried_literal_n" not in loaded["trial_ledger"]

    mutated = _raw_draft()
    mutated["trial_ledger"]["declared_budget_floor"] = 13
    with pytest.raises(ValueError, match="declared_budget_floor"):
        draft_loader.validate_draft(mutated)


def test_r1_06_label_for_grid() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    listed = set(loaded["label_semantics"]["labels"])
    min_episodes = loaded["label_semantics"]["min_episodes"]
    assert min_episodes == 153
    family_n = loaded["trial_ledger"]["family_n"]
    assert "honest-N after IL §3 collapse" in family_n
    mapping = loaded["label_semantics"]["rule"]["ABSTAIN_INSUFFICIENT_CLUSTERS"]
    assert "NOT ESTIMABLE" in mapping["not_estimable_mapping"]

    for clusters in range(0, 4):
        for episodes in (0, 1, 152, 153, 500):
            label = draft_loader.label_for(episodes, clusters, min_episodes)
            assert label in listed
            assert label in LABELS
            if clusters < 2:
                assert label != "TESTED"


@pytest.mark.parametrize("location", ["authority_flags", "labels.authority_flags"])
@pytest.mark.parametrize("flag", AUTHORITY_FLAG_NAMES)
@pytest.mark.parametrize("value", [True, "false"])
def test_r1_07_authority_enforced(location: str, flag: str, value) -> None:
    mutated = _raw_draft()
    if location == "authority_flags":
        mutated["authority_flags"][flag] = value
    else:
        mutated["labels"]["authority_flags"][flag] = value
    with pytest.raises(ValueError):
        draft_loader.validate_draft(mutated)


def test_r1_08_no_identity_literals() -> None:
    json_text = JSON_PATH.read_text(encoding="utf-8")
    md_text = MD_PATH.read_text(encoding="utf-8")
    loaded = draft_loader.load_draft(JSON_PATH)
    dumped = json.dumps(loaded, ensure_ascii=False)
    for blob in (json_text, md_text, dumped):
        assert IDENTITY_FORBIDDEN.search(blob) is None
    graded = loaded["graded_legs"]["graded_leg"]
    assert graded["kind"] == "caller_supplied_opaque_id"
    assert graded["role"] == "Alibaba ADR leg, MARKET_US"


def _mutate_tune_nonempty(draft: dict) -> dict:
    draft["splits"]["TUNE"] = "2024-01-01 <= s < 2026-10-01"
    return draft


def _mutate_membership_nonempty(draft: dict) -> dict:
    draft["membership_table"] = [{"episode_id": "synthetic-ep-1"}]
    return draft


def _mutate_never_refill_missing(draft: dict) -> dict:
    del draft["splits"]["never_refill"]
    return draft


def _mutate_detection_missing(draft: dict) -> dict:
    del draft["clock_rules"]["detection_before_outcome"]
    return draft


def _mutate_vintage_rule_missing(draft: dict) -> dict:
    del draft["vintage_rule"]
    return draft


def _mutate_info_leak_missing(draft: dict) -> dict:
    del draft["info_leak_predicate"]
    return draft


def _mutate_as_of_missing(draft: dict) -> dict:
    del draft["vintage_rule"]["as_of_utc"]
    return draft


def _mutate_tested_low_clusters(draft: dict) -> dict:
    draft["label_semantics"]["rule"]["TESTED"]["min_clusters"] = 1
    return draft


@pytest.mark.parametrize(
    "mutator",
    [
        _mutate_tune_nonempty,
        _mutate_membership_nonempty,
        _mutate_never_refill_missing,
        _mutate_detection_missing,
        _mutate_vintage_rule_missing,
        _mutate_info_leak_missing,
        _mutate_as_of_missing,
        _mutate_tested_low_clusters,
    ],
    ids=[
        "tune_nonempty",
        "membership_table_nonempty",
        "never_refill_missing",
        "detection_before_outcome_missing",
        "vintage_rule_missing",
        "info_leak_predicate_missing",
        "as_of_utc_missing",
        "tested_clusters_lt_2",
    ],
)
def test_r1_09_mutations_refused(mutator) -> None:
    mutated = mutator(_raw_draft())
    with pytest.raises(ValueError):
        draft_loader.validate_draft(mutated)


def test_r1_10_ladder_separated_from_labels() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    ladder = loaded["abstention_ladder"]
    assert "TESTED" not in ladder
    assert "DESCRIPTIVE_ONLY" not in ladder
    for item in ladder:
        assert "TESTED" not in str(item)
        assert "DESCRIPTIVE_ONLY" not in str(item)
    assert set(loaded["label_order"]) == set(loaded["label_semantics"]["labels"])

    mixed = _raw_draft()
    mixed["abstention_ladder"] = [
        "ABSTAIN_NO_EPISODES",
        "ABSTAIN_INSUFFICIENT_CLUSTERS",
        "DESCRIPTIVE_ONLY",
        "TESTED",
    ]
    with pytest.raises(ValueError, match="abstention_ladder"):
        draft_loader.validate_draft(mixed)

    order = _raw_draft()
    order["label_order"] = ["TESTED"]
    with pytest.raises(ValueError, match="label_order"):
        draft_loader.validate_draft(order)

def test_x6r_06_no_alpha_token_in_p04_v2() -> None:
    """X6-03: Type-I field is significance_level, never a word-boundary alpha."""
    spec = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert spec["statistics"]["significance_level"] == 0.05
    assert "alpha" not in spec["statistics"]
    assert "one-sided significance level 0.05" in spec["minimum_evidence"]["derivation"]
    pat = re.compile(r"\balpha\b", re.IGNORECASE)
    for path in (JSON_PATH, MD_PATH):
        blob = path.read_text(encoding="utf-8")
        hits = pat.findall(blob)
        assert hits == [], f"word-boundary alpha in {path.name}: {hits}"
