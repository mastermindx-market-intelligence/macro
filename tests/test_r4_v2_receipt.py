"""R4 dry-run receipt V2: the committed receipt passes its checker, and the checker fails closed.

Pins: every promotion flag false, every clock strictly before the EVAL-1 boundary, the era label on
the header and every row, the verdict inside the frozen enum, and no effect field on a cell that is
below its floor (or on a sensitivity cell).
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "research" / "alpha_intelligence" / "expectation_market_dynamics"
RECEIPT = HERE / "R4_DRYRUN_RECEIPT_V2_2026-10-07.json"
RENDERED = HERE / "R4_DRYRUN_RECEIPT_V2_2026-10-07.md"
_SPEC = importlib.util.spec_from_file_location("r4_v2_receipt_check", HERE / "r4_v2_receipt_check.py")
check = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check)


@pytest.fixture(scope="module")
def doc() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _below_floor_s_cell(d: dict) -> dict:
    return next(r for r in d["cells"] if r["variant"] == "S" and not r["meets_floor"])


def test_committed_receipt_has_no_violations(doc):
    assert check._violations(doc) == []


def test_cli_accepts_receipt_and_markdown():
    assert check.main(["--check", str(RECEIPT), "--md", str(RENDERED)]) == 0


def test_markdown_cites_the_json_digest():
    digest = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    assert digest in RENDERED.read_text(encoding="utf-8")


def test_flags_false_and_no_score_or_rank(doc):
    for labels in [doc["labels"]] + [r["labels"] for r in doc["cells"]]:
        assert labels["financial_influence"] is False
        assert labels["k3e_admissible"] is False
        assert labels["promotion_eligible"] is False
        assert labels["promotion_bearing"] is False
        assert labels["score"] is None and labels["rank"] is None
    assert doc["not_promotion_bearing"] is True
    assert doc["trial_consumption"] == "NONE"


def test_era_label_on_header_and_every_row(doc):
    assert doc["labels"]["era"] == "INTER_ERA_GAP"
    assert all(r["labels"]["era"] == "INTER_ERA_GAP" for r in doc["cells"])
    assert all(r["labels"] == check.LABELS for r in doc["cells"])


def test_verdict_in_enum(doc):
    assert doc["verdict"] in check.VERDICTS or check.BLOCKED.match(doc["verdict"])


def test_all_clocks_before_boundary(doc):
    for key in check.CORPUS_CLOCKS:
        assert check._when(doc["corpus"][key]) < check.BOUNDARY
    for day in doc["corpus"]["cutoff_sessions"]:
        assert check._day(day) <= check.LAST_SESSION
    for day, version in doc["identity"]["known_version_by_cutoff_session"].items():
        assert check._day(day) <= check.LAST_SESSION
        assert check._when(version["committer_time"]) < check.BOUNDARY


def test_no_effect_fields_below_floor(doc):
    for r in doc["cells"]:
        if not r["meets_floor"]:
            assert "effect" not in r
            assert r["effect_status"].startswith("NOT_ESTIMATED")


@pytest.mark.parametrize("flag", ["financial_influence", "k3e_admissible", "promotion_eligible"])
def test_rejects_a_true_flag_anywhere(doc, flag):
    bad = copy.deepcopy(doc)
    bad["cells"][3]["labels"][flag] = True
    assert any(flag in v for v in check._violations(bad))
    bad = copy.deepcopy(doc)
    bad["mkt1"][flag] = True
    assert any(flag in v for v in check._violations(bad))


def test_rejects_a_score(doc):
    bad = copy.deepcopy(doc)
    bad["cells"][0]["labels"]["score"] = 0.5
    assert check._violations(bad)


def test_rejects_effect_on_below_floor_cell(doc):
    bad = copy.deepcopy(doc)
    _below_floor_s_cell(bad)["effect"] = dict(n=1, mean=0.01)
    assert any("not at the floor" in v for v in check._violations(bad))


def test_rejects_effect_on_sensitivity_cell(doc):
    bad = copy.deepcopy(doc)
    next(r for r in bad["cells"] if r["variant"] == "L")["effect"] = dict(n=1, mean=0.01)
    assert check._violations(bad)


def test_rejects_estimated_status_below_floor(doc):
    bad = copy.deepcopy(doc)
    _below_floor_s_cell(bad)["effect_status"] = "ESTIMATED_DESCRIPTIVE"
    assert check._violations(bad)


@pytest.mark.parametrize("key", ["max_system_observed_at", "max_provider_observed_at", "max_decision_cutoff"])
def test_rejects_a_clock_on_or_after_the_boundary(doc, key):
    bad = copy.deepcopy(doc)
    bad["corpus"][key] = "2026-10-07 13:30:00+00:00"
    assert any(key in v for v in check._violations(bad))


def test_rejects_a_known_version_inside_the_24h_guard(doc):
    bad = copy.deepcopy(doc)
    day = sorted(bad["identity"]["known_version_by_cutoff_session"])[-1]
    bad["identity"]["known_version_by_cutoff_session"][day]["committer_time"] = day + " 19:00:00+00:00"
    assert any("24h" in v for v in check._violations(bad))


def test_rejects_a_post_boundary_cutoff_session(doc):
    bad = copy.deepcopy(doc)
    bad["corpus"]["cutoff_sessions"]["2026-10-07"] = 1
    assert check._violations(bad)


def test_rejects_a_verdict_outside_the_enum(doc):
    bad = copy.deepcopy(doc)
    bad["verdict"] = "R4_PROBABLY_FINE"
    assert any("verdict" in v for v in check._violations(bad))


def test_rejects_a_missing_era_label(doc):
    bad = copy.deepcopy(doc)
    del bad["cells"][5]["labels"]["era"]
    assert any("labels" in v for v in check._violations(bad))
    bad = copy.deepcopy(doc)
    bad["labels"]["era"] = "EVAL_1"
    assert any("labels" in v for v in check._violations(bad))


def test_rejects_count_arithmetic_drift(doc):
    bad = copy.deepcopy(doc)
    bad["cells"][0]["complete"] += 1
    assert check._violations(bad)


def test_rejects_admissible_verdict_without_floor(doc):
    bad = copy.deepcopy(doc)
    bad["verdict"] = "R4_ADMISSIBLE_DESCRIPTIVE"
    if not any(all(r["meets_floor"] for r in bad["cells"] if r["variant"] == "S" and r["h"] == h)
               for h in check.HORIZONS):
        assert any("ADMISSIBLE" in v for v in check._violations(bad))
