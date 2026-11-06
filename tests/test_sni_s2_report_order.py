"""S2 report order (E12/REG §5): every family x h x split block carries the
ten REG §5 elements IN ORDER, the commission family-row fields (present and
non-blank), the E1 label, and P07/P08/P11 print NOT SUPPORTED in S2.

Runs against the committed evidence artifacts (research/, never data/).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

RUNS = (ROOT / "research" / "single_name_intelligence" / "runs"
        / "s2_event_response")
REG5_ORDER = ("plain_word_null", "analysis_set", "honest_n", "cluster_n",
              "literal_row_count", "visible_exclusions", "test", "ci",
              "trials", "receipt")
FAMILY_ROW_FIELDS = ("event_count", "distinct_calendar_clusters", "honest_n",
                     "effective_n", "pooling_weight", "uncertainty",
                     "abstention_state")


def _results(pid: str) -> dict:
    path = RUNS / "results" / f"{pid}.json"
    if not path.exists():  # pragma: no cover - evidence run pending
        pytest.skip(f"committed evidence results missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("pid", ["P04", "P05", "P06"])
def test_reg5_order_in_every_block(pid: str) -> None:
    res = _results(pid)
    assert res["label"].startswith("HISTORICAL-DESCRIPTIVE")
    assert res["identity_view"] == "RETROSPECTIVE_JOIN"
    assert all(v is False for v in res["authority_flags"].values())
    for split in ("TRAIN", "TUNE", "QUARANTINE"):
        for h in ("h5", "h21", "h63"):
            blk = res["splits"][split][h]
            keys = tuple(blk.keys())
            # REG §5 elements appear in order (later optional keys may follow)
            positions = [keys.index(k) for k in REG5_ORDER if k in keys]
            assert all(k in keys for k in REG5_ORDER), (pid, split, h, keys)
            assert positions == sorted(positions), (pid, split, h, keys)


@pytest.mark.parametrize("pid", ["P04", "P05", "P06"])
def test_family_row_fields_present_and_non_blank(pid: str) -> None:
    res = _results(pid)
    for split in ("TRAIN", "TUNE", "QUARANTINE"):
        for h in ("h5", "h21", "h63"):
            fr = res["splits"][split][h]["family_row"]
            for field in FAMILY_ROW_FIELDS:
                assert field in fr, (pid, split, h, field)
                assert fr[field] is not None and fr[field] != "", \
                    (pid, split, h, field)
            # honest-N for all three analysis sets is always printed
            for s in ("SENS_A", "SENS_B"):
                assert isinstance(fr[f"honest_n_{s.lower()}"], int)
            # the trials block is never blank
            tr = res["splits"][split][h]["trials"]
            assert tr["declared_budget"] == 6
            assert tr["effective_n"] >= tr["declared_budget"]
            assert "never a sample N" in tr["effective_n_label"]


def test_tune_retirement_disclosed_when_fired() -> None:
    res = _results("P04")
    lane = json.loads((RUNS / "LANE_MANIFEST.json").read_text(encoding="utf-8"))
    p04 = [r for r in lane["info_leak"]
           if r.get("protocol_id") == "P04"
           and r.get("contamination_class") == "information_leak"]
    if p04:
        assert p04[0]["successor"] == "P04 v2 — not drafted; owner = seat/S0"
        for h in ("h5", "h21", "h63"):
            blk = res["splits"]["TUNE"][h]
            assert "tune_retirement" in blk
            assert blk["tune_retirement"]["contamination_class"] == "information_leak"


def test_report_md_carries_labels_and_not_supported_lines() -> None:
    path = RUNS / "REPORT.md"
    if not path.exists():  # pragma: no cover
        pytest.skip("committed REPORT.md missing")
    text = path.read_text(encoding="utf-8")
    assert "HISTORICAL-DESCRIPTIVE" in text
    assert "RETROSPECTIVE_JOIN" in text
    for pid in ("P07", "P08", "P11"):
        assert f"{pid}: NOT SUPPORTED in S2 (not commissioned)" in text
