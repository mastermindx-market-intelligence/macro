"""
D1 FINAL — independent Opus acceptance probes for Healthcare D1 (PR #7930).

Authored against exact head 28b986d4de696f0087ad760eabe95c09cdd695f1.
Synthetic data only: no network, no real molecule names, no writes outside tmp_path.

  test_final_end_to_end_truth_path      GREEN at 28b986d4 (freeze as a regression guard)
  test_d1f_b1_torn_pair_*               RED  at 28b986d4 (finding D1F-B1)
  test_d1f_b2_cold_start_*              RED  at 28b986d4 (finding D1F-B2)
  test_d1f_b3_qualified_capture_*       RED  at 28b986d4 (finding D1F-B3)

The three RED probes all share one root cause: `_observation_capture`
(engine/fda_scarcity.py:273) never emits a `qualified` key, so the
`qualified is False` branch at :215 — the ONLY door to the UNAVAILABLE state —
is unreachable from the real read path, and `capture_qualified` is None for
every rendered chip (:159).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import pytest

UTC = timezone.utc

BANNED = ("glut", "tell", "all-clear", "catching up",
          "demand exceeds supply", "supply constraint lifted")


def _record(ndc="SYN-A", name="zetamide injection", status="Current",
            availability="Limited Availability"):
    return {"package_ndc": ndc, "generic_name": name, "status": status,
            "availability": availability, "initial_posting_date": "01/02/2026",
            "update_date": "01/03/2026", "openfda": {"substance_name": ["zetamide"]}}


def _sweep(collector, generation, rows, start, finish, *, outage=False):
    ticks = iter([start, finish])

    def fetch_page(skip, limit):
        if outage:
            raise RuntimeError("synthetic outage")
        return {"meta": {"last_updated": generation,
                         "results": {"total": len(rows)}},
                "results": rows[skip:skip + limit]}

    return collector.collect_shortage_sweep(
        fetch_page, clock=lambda: next(ticks), page_size=100, max_pages=3)


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


@pytest.fixture()
def seam(tmp_path, monkeypatch):
    """Wire the collector store and the engine theme map onto synthetic ground."""
    import collectors.fda_shortages as collector
    import engine.fda_scarcity as scarcity
    from engine.foresight_cascade import _compute_tier

    path = tmp_path / "shortages.parquet"
    monkeypatch.setattr(collector, "_shortages_path", lambda: path)
    monkeypatch.setattr(scarcity, "MOLECULE_THEME_MAP", {"zetamide": ["synthetic_theme"]})

    class Seam:
        C = collector
        S = scarcity
        parquet = path
        sidecar = path.with_suffix(".observation.json")

        def render(self):
            row = scarcity.compute_fda_scarcity().get("synthetic_theme")
            chip = scarcity.format_theme_feed_chip(row, "synthetic_theme")
            return row, chip, _compute_tier(None, chip)

    return Seam()


def _assert_visible_copy_is_clean(chip):
    for field in ("label", "label_zh", "rationale"):
        text = chip[field]
        assert isinstance(text, str) and text, f"{field} is empty: {text!r}"
        assert "None" not in text, f"{field} renders the literal None: {text!r}"
        assert "nan" not in text.casefold(), f"{field} renders nan: {text!r}"
        for banned in BANNED:
            assert banned not in text.casefold(), \
                f"{field} carries banned vocabulary {banned!r}: {text!r}"
    assert chip["label"] != chip["label_zh"], "EN/ZH parity: both languages must be authored"
    assert chip["rationale"].isascii(), "the tooltip must stay ASCII (title attribute law)"


# ── GREEN: the end-to-end truth path ────────────────────────────────────────
def test_final_end_to_end_truth_path(seam):
    """collect -> save -> read -> compute -> chip -> tier across five states.

    Asserts only invariants that must hold BOTH at this head and after any repair
    of D1F-B1..B3: qualification, promotion, non-destructive failed refresh,
    generation-less rejection, clean visible copy, tone/band/tier coherence.
    """
    now = datetime.now(UTC)

    # 1. a qualified sweep with one Current row
    first = _sweep(seam.C, "2026-09-23", [_record()],
                   now - timedelta(seconds=40), now - timedelta(seconds=30))
    assert first["qualified"] is True, first
    assert first["failure_code"] is None, first
    promoted = seam.C.save_shortage_observation(
        first, path=seam.parquet, expected_predecessor=None)
    assert promoted["promoted"] is True, promoted

    row, chip, tier = seam.render()
    assert chip["source_status"] == "CURRENT_REPORTED", chip["source_status"]
    assert chip["tone"] == "warn" and chip["band"] == "SHORTAGE_ACTIVE"
    assert chip["n_active"] == 1 and tier == "P"
    assert chip["freshness"]["source_generation"] == "2026-09-23"
    _assert_visible_copy_is_clean(chip)
    assert "current" in chip["label"].casefold()

    # 2. a failed refresh over it is non-destructive and is disclosed
    outage = _sweep(seam.C, None, [], now - timedelta(seconds=20),
                    now - timedelta(seconds=10), outage=True)
    assert outage["qualified"] is False and outage["failure_code"] == "FIRST_PAGE_OUTAGE"
    outcome = seam.C.save_shortage_observation(
        outage, path=seam.parquet, expected_predecessor=_digest(seam.sidecar))
    assert outcome["promoted"] is False and outcome["reason"] == "FIRST_PAGE_OUTAGE"

    row, chip, tier = seam.render()
    assert chip["source_status"] == "CURRENT_REPORTED", "the retained evidence survives"
    assert chip["n_active"] == 1 and tier == "P"
    assert chip["freshness"]["failed_refresh"]["failure_code"] == "FIRST_PAGE_OUTAGE"
    assert "refresh failed" in chip["label"], chip["label"]
    assert "刷新失败" in chip["label_zh"], chip["label_zh"]
    _assert_visible_copy_is_clean(chip)

    # 3. a generation-less page is refused at the public seam
    blind = _sweep(seam.C, None, [_record()], now - timedelta(seconds=9),
                   now - timedelta(seconds=8))
    assert blind["qualified"] is False, blind
    assert blind["failure_code"] == "NO_SOURCE_GENERATION", blind["failure_code"]
    outcome = seam.C.save_shortage_observation(
        blind, path=seam.parquet, expected_predecessor=_digest(seam.sidecar))
    assert outcome["promoted"] is False and outcome["reason"] == "NO_SOURCE_GENERATION"
    row, chip, tier = seam.render()
    assert chip["freshness"]["source_generation"] == "2026-09-23", \
        "the refused sweep must not overwrite the qualified generation"
    _assert_visible_copy_is_clean(chip)

    # 4. a torn pair is never an exception and never invents rows
    seam.parquet.write_bytes(b"PAR1-not-a-parquet")
    state = seam.C.read_shortage_observation(path=seam.parquet)
    assert state["inconsistent"] is True and state["rows"] is None
    row, chip, tier = seam.render()
    assert chip["n_active"] == 0, "a torn pair must not report records"
    _assert_visible_copy_is_clean(chip)

    # 5. the drip receipt never raises and never claims a qualification it lacks
    receipt = seam.C.format_observation_receipt(state)
    assert receipt.startswith("fda_shortages: observation qualified=False")
    assert "inconsistent=True" in receipt


# ── RED: D1F-B1 ─────────────────────────────────────────────────────────────
def test_d1f_b1_torn_pair_is_reported_unavailable_not_no_matching_records(seam):
    """D1F-B1. A parquet whose digest fails its sidecar is an UNREAD source.

    The rendered chip claims `FDA: no matching records` — a positive statement
    that the source was consulted and held nothing for this theme — while
    read_shortage_observation reports inconsistent=True, rows=None. Law: absence
    of a readable observation is not evidence of absence; the module's own
    UNAVAILABLE state exists for exactly this.
    """
    now = datetime.now(UTC)
    first = _sweep(seam.C, "2026-09-23", [_record()],
                   now - timedelta(seconds=40), now - timedelta(seconds=30))
    seam.C.save_shortage_observation(first, path=seam.parquet, expected_predecessor=None)
    seam.parquet.write_bytes(b"PAR1-not-a-parquet")

    state = seam.C.read_shortage_observation(path=seam.parquet)
    assert state["inconsistent"] is True, "precondition: the pair is torn"

    _, chip, _ = seam.render()
    assert chip["source_status"] != "NO_MATCHING_RECORDS", (
        "D1F-B1: a torn observation renders as a source claim about matching "
        f"records: {chip['source_status']} / {chip['label']!r} / {chip['rationale']!r}")
    assert chip["source_status"] == "UNAVAILABLE", chip["source_status"]


# ── RED: D1F-B2 ─────────────────────────────────────────────────────────────
def test_d1f_b2_cold_start_is_not_rendered_as_no_matching_records(seam):
    """D1F-B2. With no parquet and no sidecar the collector has never run.

    origin/main degraded honestly (`Missing cache -> ALL entries are None`), so
    no chip rendered at all. At this head the chip claims `FDA: no matching
    records`, asserting a source read that never happened. Law: nulls are
    printed, never dressed as an observation.
    """
    assert not seam.parquet.exists() and not seam.sidecar.exists()
    row, chip, tier = seam.render()
    if chip is None:
        return  # honest degradation, as on origin/main
    assert chip["source_status"] == "UNAVAILABLE", (
        "D1F-B2: a never-collected source renders as a records claim: "
        f"{chip['source_status']} / {chip['label']!r} / {chip['rationale']!r}")


# ── RED: D1F-B3 ─────────────────────────────────────────────────────────────
def test_d1f_b3_qualified_capture_is_not_labelled_capture_time_unknown(seam):
    """D1F-B3. The happy path contradicts itself in EN and ZH.

    save_shortage_observation stores `selected_capture` = the sweep capture,
    which carries no `qualified` key, so summarize_supply reads qualified=None
    (engine/fda_scarcity.py:177) and _label appends `capture time unknown`
    (:159) to EVERY chip — including one that has just printed `captured 0 d
    ago` from the same capture. freshness.capture_qualified is null for a fully
    qualified observation, so downstream consumers cannot tell it from unknown.
    """
    now = datetime.now(UTC)
    first = _sweep(seam.C, "2026-09-23", [_record()],
                   now - timedelta(seconds=40), now - timedelta(seconds=30))
    assert first["qualified"] is True
    assert seam.C.save_shortage_observation(
        first, path=seam.parquet, expected_predecessor=None)["promoted"] is True

    _, chip, _ = seam.render()
    label, label_zh = chip["label"], chip["label_zh"]
    assert not ("captured" in label and "capture time unknown" in label), (
        "D1F-B3: the label states the capture age and calls the capture time "
        f"unknown in one breath: {label!r}")
    assert "采集时间未知" not in label_zh, f"D1F-B3 (ZH): {label_zh!r}"
    assert chip["freshness"]["capture_qualified"] is True, (
        "D1F-B3: a qualified capture reports capture_qualified="
        f"{chip['freshness']['capture_qualified']!r}")
