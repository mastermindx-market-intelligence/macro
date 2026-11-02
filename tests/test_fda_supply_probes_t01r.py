"""
SEAT NOTE (2026-09-24): the reviewer's M1 probe (production staleness budget) was removed by the seat — it contradicts accepted ruling R-T01-12 (no invented age limit). Six law-backed probes + one GREEN pin remain.
T01R — independent Opus adversarial probes for Healthcare D1 task T01.

Authored against exact head 604a3755c3ff1b3ed7bcf0d50e2716e5ee0b4f98 (PR #7930).
Synthetic data only: no network, no real molecule names, no writes outside tmp_path.
Every probe below is RED at 604a3755 except the one marked GREEN PIN.
Imports are confined to engine.fda_scarcity / engine.foresight_cascade public seams.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

UTC = timezone.utc
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@pytest.fixture(autouse=True)
def _isolate_real_data_tree(tmp_path, monkeypatch):
    from lib import config as _config
    _config.load()
    monkeypatch.setattr(_config, "ROOT", tmp_path)
    monkeypatch.setattr(_config, "data_dir", lambda: tmp_path / "data")


def _row(status="Current", availability="Available", ndc="TEST-A", name="Synthetic A"):
    return {"generic_name": name, "package_ndc": ndc, "status": status,
            "availability": availability}


# ── T01R-B1 ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("capture", [
    {"qualified": False, "failure_code": "FileNotFoundError: no cache"},
    {"qualified": False, "failure_code": "FIRST_PAGE_OUTAGE", "source_generation": None},
    {"qualified": False, "failure_code": "FIRST_PAGE_OUTAGE", "source_generation": ""},
])
def test_t01r_b1_unavailable_label_never_renders_a_python_none(capture):
    """B1: a cold-cache failure must not print the literal `None` in visible EN/ZH copy."""
    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply([], capture=capture, now=now, max_capture_age=timedelta(days=2))
    assert out["source_status"] == "UNAVAILABLE"
    for field in ("label", "label_zh"):
        text = out[field]
        assert "None" not in text, \
            f"T01R-B1: visible {field} renders the literal None: {text!r}"
        assert ISO_DATE.search(text) is None, \
            f"T01R-B1: no qualified generation exists, so {field} may claim no date: {text!r}"
    assert out["label"] != out["label_zh"], "T01R-B1: both languages must still be authored"


# ── T01R-B2 ──────────────────────────────────────────────────────────────────
def test_t01r_b2_failed_refresh_keeps_the_retained_shortage_visible():
    """B2: a failed refresh over a qualified cache is STALE, not evidence-free.

    The retained capture still holds a current-shortage record; the chip counts it
    (n_active == 1) while the visible label reports only `source unavailable`, so the
    visible copy contradicts the chip's own counts and a live shortage disappears from
    the card because a fetch failed.  Law: failed != stale; absence of a refresh is not
    absence of evidence; composition follows configuration, not acquisition.
    """
    from engine.fda_scarcity import format_theme_feed_chip, summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    stale = summarize_supply(
        [_row("Current")],
        capture={"qualified": False, "failure_code": "FIRST_PAGE_OUTAGE",
                 "source_generation": "2026-09-20",
                 "finished_at": "2026-09-20T12:00:07+00:00"},
        now=now, max_capture_age=timedelta(days=2))
    chip = format_theme_feed_chip(
        {"summary": stale, "band": "SHORTAGE_ACTIVE",
         "source_status": stale["source_status"]}, "glp1_obesity")
    assert chip["n_active"] == 1, "precondition: the retained capture still carries the record"
    assert "current" in chip["label"].casefold(), \
        f"T01R-B2: the chip counts a current record but hides it: {chip['label']!r}"
    assert "当前" in chip["label_zh"], \
        f"T01R-B2: the Chinese twin hides the same record: {chip['label_zh']!r}"


def test_t01r_b2_failed_refresh_does_not_erase_the_legacy_band():
    """B2 (production seam): a refresh outage flips SHORTAGE_ACTIVE -> NONE."""
    from engine.fda_scarcity import SHORTAGE_ACTIVE, compute_fda_scarcity

    df = pd.DataFrame([{"generic_name": "tirzepatide synthetic", "package_ndc": "TEST-A",
                        "status": "Current", "availability": "Available",
                        "initial_posting_date": "2026-03-02"}])
    df.attrs["fda_observation"] = {
        "capture": {"qualified": True, "source_generation": "2026-09-20",
                    "finished_at": "2026-09-20T12:00:07+00:00"},
        "last_refresh": {"qualified": False, "failure_code": "FIRST_PAGE_OUTAGE",
                         "attempted_at": "2026-09-22T09:00:00+00:00"},
    }
    row = compute_fda_scarcity(df)["glp1_obesity"]
    assert row["n_active"] == 1, "precondition: the retained row is still matched"
    assert row["band"] == SHORTAGE_ACTIVE, \
        f"T01R-B2: a failed refresh erased the legacy band: {row['band']!r}"


# ── T01R-M1 ──────────────────────────────────────────────────────────────────

def test_t01r_m2_unparseable_generation_is_disclosed_not_silently_dropped():
    """M2: a source_generation in ISO-datetime form fails date.fromisoformat, so the
    generation is dropped without a word and the only time token left in the visible
    label is the ACQUISITION clock (`captured 0 d ago`).  Law: labels name the source
    generation, never the fetch clock; nulls are printed, not hidden."""
    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [_row("Current")],
        capture={"qualified": True, "finished_at": now.isoformat(),
                 "source_generation": "2026-07-25T00:00:00+00:00"},
        now=now, max_capture_age=timedelta(days=2))
    label, label_zh = out["label"], out["label_zh"]
    if out["freshness"]["source_generation"] is None:
        assert "generation" in label.casefold(), \
            f"T01R-M2: generation dropped in silence, only the fetch clock survives: {label!r}"
        assert "生成" in label_zh, f"T01R-M2: same silent drop in Chinese: {label_zh!r}"
    assert "captured" not in label.casefold() or "generation" in label.casefold(), \
        f"T01R-M2: acquisition time may not stand alone as the label's freshness: {label!r}"


# ── GREEN PIN (GLM-M1 gate gap) ──────────────────────────────────────────────
def test_t01r_pin_tier_unchanged_when_the_source_is_unavailable():
    """GREEN PIN (must stay green): the ruling-mandated cache-absent tier comparison.

    tests/test_foresight_cascade.py:682 asserts only source_status == UNAVAILABLE and
    never formats a chip or compares a tier; the tier comparison at :1336 uses
    CURRENT vs RESOLVED.  This pins the actual law: tier follows configuration, so an
    UNAVAILABLE / NO_MATCHING_RECORDS source must not demote the row off tier P.
    """
    from engine import foresight_cascade as fc

    bottleneck = {"themes": {"glp1_obesity": {"name": "GLP-1 / Obesity", "band": "AWAITING_DATA"}}}
    revisions = {"themes": {"glp1_obesity": {"name": "GLP-1 / Obesity", "breadth": 0.05,
                                             "level_state": "FLAT_LOW"}}}

    def run(source_status, band):
        scarcity = {"glp1_obesity": {"band": band, "source_status": source_status,
                                     "freshness": {}, "n_active": 0, "n_resolved": 0,
                                     "n_discontinued": 0, "molecules_checked": [],
                                     "details": [], "rationale": "synthetic"}}
        return fc.compute_foresight_cascade(
            bottleneck=bottleneck, revisions=revisions, demand={"themes": {}},
            glut={"themes": {}}, fda_scarcity=scarcity, write_ledger=False)["themes"][0]

    current = run("CURRENT_REPORTED", "SHORTAGE_ACTIVE")
    unavailable = run("UNAVAILABLE", "NONE")
    empty = run("NO_MATCHING_RECORDS", "NONE")
    assert current["tier"] == unavailable["tier"] == empty["tier"] == "P"
    assert current["stage"] == unavailable["stage"] == empty["stage"]
    assert current.get("entry") == unavailable.get("entry") == empty.get("entry")
    assert unavailable["theme_feed_summary"] is not None
    assert unavailable["theme_feed_summary"]["label"] != empty["theme_feed_summary"]["label"]
