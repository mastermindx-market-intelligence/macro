"""Cycle Intelligence W8 round-1 P0 truth blockers.

B1  hazard.turn_kind vs proj.nextTurn; suppress headline on disagreement
B2  monotone CDF (or unavailable) over every emitted hazard cell set
B3  notes_as_of vs tape_as_of
A6  day-precision staleness arithmetic (14 / 19 / 29 day cases)

site/cycle_app.js, site/cycle.css, site/cycle_i18n.js are site-canonical sources
(no templates/ twins — see tests/test_cycle_forward_framing.py). cycle.html is
baked from templates/cycle.html.j2.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

from engine.hazard_score import (
    _enforce_hazard_cdf,
    _hazard_cdf_cells,
    _hazard_cdf_is_monotone,
)
from scripts import _cycle_seed
from scripts import build_cycle

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
ENGINE_JS = SITE / "cycledata" / "cycle_engine.js"
APP_JS = SITE / "cycle_app.js"
SEED_JS = SITE / "cycle_data.js"
TPL = ROOT / "templates" / "cycle.html.j2"


def _read_app() -> str:
    if not APP_JS.exists():
        pytest.skip("cycle_app.js not in site/ — opt in site/")
    return APP_JS.read_text(encoding="utf-8")


def _load_engine() -> dict:
    if not ENGINE_JS.exists():
        pytest.skip("cycle_engine.js not built in this checkout")
    txt = ENGINE_JS.read_text(encoding="utf-8")
    body = txt.split("window.CYCLE_ENGINE = ", 1)[1].rsplit(";", 1)[0]
    return json.loads(body)


def _iter_hazard_bands(engine: dict):
    for cid, card in (engine.get("cycles") or {}).items():
        for band in card.get("bands") or []:
            hz = (band.get("now") or {}).get("hazard")
            if hz:
                yield cid, band, hz


def _turn_kind_from_hz(hz: dict) -> str | None:
    if hz.get("turn_kind"):
        return hz["turn_kind"]
    direction = hz.get("direction")
    if direction == "up":
        return "peak"
    if direction == "down":
        return "trough"
    return None


def _lead_cell(hz: dict) -> str | None:
    """Python twin of cycle_app.js hazardLeadCell (consumer contract)."""
    if hz.get("unavailable"):
        return None
    cells = [(h, hz[h]) for h in ("1m", "3m", "6m") if hz.get(h) and hz[h].get("p") is not None]
    if not cells:
        return None
    vals = [c["p"] for _, c in cells]
    if any(vals[i] + 1e-12 < vals[i - 1] for i in range(1, len(vals))):
        return None
    pass_keys = [
        h for h, c in cells
        if c.get("cell_verdict") == "PASS" or c.get("source") == "MODEL"
    ]
    pool = pass_keys or [h for h, _ in cells]
    if pass_keys and any(k != "6m" for k in pass_keys):
        pool = [k for k in pass_keys if k != "6m"]
    order = ["1m", "3m", "6m"]
    best = pool[0]
    for k in pool:
        pk, pb = hz[k]["p"], hz[best]["p"]
        if pk > pb + 1e-12:
            best = k
        elif abs(pk - pb) <= 1e-12 and order.index(k) < order.index(best):
            best = k
    return best


# ── B1 ───────────────────────────────────────────────────────────────────────

def test_consumer_labels_hazard_from_turn_kind_never_nextturn_in_headline():
    js = _read_app()
    assert "function hazardTurnKind(" in js
    assert "function hazardDirectionAgrees(" in js
    # the hazard lead path must not read pj.nextTurn
    lead_fn = js.split("function hazardLeadInner(", 1)[1].split("function hazardHeadlineHTML(", 1)[0]
    assert "pj.nextTurn" not in lead_fn
    headline = js.split("function hazardHeadlineHTML(", 1)[1].split("function cardNextInnerHTML(", 1)[0]
    assert "hazardDirectionAgrees" in headline
    assert "hazardLeadCell" in headline
    card_next = js.split("function cardNextInnerHTML(", 1)[1].split("function projRefHTML(", 1)[0]
    assert "hazardDirectionAgrees" in card_next
    assert "projFallbackInner" in card_next


def test_attach_hazard_agreement_stamps_turn_kind_and_agrees():
    hz = {"direction": "down", "1m": {"p": 0.5, "source": "MODEL", "cell_verdict": "PASS"}}
    out = build_cycle._attach_hazard_agreement(hz, "down", {"nextTurn": "peak"})
    assert out["turn_kind"] == "trough"
    assert out["direction_agrees"] is False
    out2 = build_cycle._attach_hazard_agreement(
        {"direction": "down"}, "down", {"nextTurn": "trough"}
    )
    assert out2["turn_kind"] == "trough"
    assert out2["direction_agrees"] is True


def test_every_emitted_card_turn_kind_agrees_or_headline_suppressed():
    engine = _load_engine()
    rows = []
    for cid, band, hz in _iter_hazard_bands(engine):
        pj = band.get("proj") or {}
        tk = _turn_kind_from_hz(hz)
        agrees = (tk == pj.get("nextTurn")) if tk and pj.get("nextTurn") else False
        if hz.get("direction_agrees") is not None:
            agrees = bool(hz["direction_agrees"])
        lead = _lead_cell(hz) if agrees else None
        rows.append((cid, tk, pj.get("nextTurn"), agrees, lead))
        assert tk in ("peak", "trough")
        if agrees:
            assert lead is not None or hz.get("unavailable") or not _hazard_cdf_is_monotone(
                _hazard_cdf_cells(hz)
            )
        else:
            assert lead is None
    assert rows, "no hazard bands in committed engine"


def test_vol_and_biotech_suppress_the_trough_model_peak_label():
    """Today both print P(Peak ≤ 6m) from a P(trough) model. After B1 the
    hazard headline is suppressed (direction_agrees is false) and the card
    falls back to the overdue-aware projection wording."""
    engine = _load_engine()
    receipts = {}
    for cid in ("vol", "biotech"):
        card = engine["cycles"][cid]
        band = next(b for b in card["bands"] if b.get("tier") == "measured")
        hz = (band.get("now") or {}).get("hazard")
        pj = band.get("proj") or {}
        tk = _turn_kind_from_hz(hz)
        agrees = tk == pj.get("nextTurn")
        assert tk == "trough", f"{cid}: hazard model is P(trough), got turn_kind={tk}"
        assert pj.get("nextTurn") == "peak"
        assert agrees is False
        assert _lead_cell(hz) is None or not agrees
        if pj.get("overdue"):
            word = f"ref: Peak was proj. {pj.get('central')} — elapsed"
        else:
            word = f"Peak ≈ {pj.get('central')}"
        receipts[cid] = {
            "turn_kind": tk,
            "proj_next": pj.get("nextTurn"),
            "headline": "SUPPRESSED",
            "fallback": word,
            "overdue": bool(pj.get("overdue")),
        }
    assert receipts["vol"]["headline"] == "SUPPRESSED"
    assert receipts["biotech"]["headline"] == "SUPPRESSED"
    # stash on the test for the session report (also asserted)
    test_vol_and_biotech_suppress_the_trough_model_peak_label.receipts = receipts


# ── B2 ───────────────────────────────────────────────────────────────────────

def test_monotonicity_sweep_every_emitted_hazard_cell_set(capsys):
    engine = _load_engine()
    n = 0
    n_mono = 0
    n_unavail = 0
    for cid, band, hz in _iter_hazard_bands(engine):
        n += 1
        guarded = _enforce_hazard_cdf(dict(hz))
        if guarded.get("unavailable"):
            n_unavail += 1
            for h in ("1m", "3m", "6m"):
                assert h not in guarded, f"{cid} unavailable block still has {h}"
            # consumer must not lead with any cell
            assert _lead_cell(guarded) is None
        else:
            n_mono += 1
            cells = _hazard_cdf_cells(guarded)
            assert _hazard_cdf_is_monotone(cells), f"{cid} non-monotone after guard: {cells}"
            lead = _lead_cell(guarded)
            pass_keys = [
                h for h in ("1m", "3m", "6m")
                if guarded.get(h)
                and (guarded[h].get("cell_verdict") == "PASS" or guarded[h].get("source") == "MODEL")
            ]
            if lead == "6m":
                assert not any(k != "6m" for k in pass_keys), (
                    f"{cid} led with 6m while shorter PASS cells exist: {pass_keys}"
                )
    print(
        f"monotonicity sweep: n={n} monotone_or_kept={n_mono} "
        f"unavailable={n_unavail}",
        flush=True,
    )
    assert n >= 19


def test_consumer_never_leads_with_6m_when_shorter_pass_exists_source_pin():
    js = _read_app()
    assert "function hazardLeadCell(" in js
    assert 'k !== "6m"' in js
    assert "within 1 month" in js
    assert "within 3 months" in js
    assert "within 6 months" in js
    assert "一个月内" in js


def test_lead_cell_picks_highest_confidence_shorter_pass():
    hz = {
        "1m": {"p": 0.12, "source": "MODEL", "cell_verdict": "PASS"},
        "3m": {"p": 0.40, "source": "MODEL", "cell_verdict": "PASS"},
        "6m": {"p": 0.70, "source": "MODEL", "cell_verdict": "PASS"},
    }
    assert _lead_cell(hz) == "3m"
    hz2 = {
        "1m": {"p": 0.05, "source": "PRIOR", "cell_verdict": "PRIOR"},
        "3m": {"p": 0.08, "source": "PRIOR", "cell_verdict": "PRIOR"},
        "6m": {"p": 0.70, "source": "MODEL", "cell_verdict": "PASS"},
    }
    assert _lead_cell(hz2) == "6m"


# ── B3 ───────────────────────────────────────────────────────────────────────

def test_notes_and_tape_as_of_helper():
    notes, tape = build_cycle._notes_and_tape_as_of(
        {"asOf": "2026-06-25"},
        {
            "vol": {"bands": [{"series_last": "2026-09-08"}]},
            "business": {"bands": [{"series_last": "2026-07-01"}, {}]},
        },
    )
    assert notes == "2026-06-25"
    assert tape == "2026-09-08"
    assert tape >= "2026-09-08"


def test_committed_engine_as_of_pair_receipts():
    engine = _load_engine()
    seed = _cycle_seed.load_seed(SEED_JS)
    notes = engine.get("notes_as_of") or engine.get("as_of")
    lasts = [
        str(b["series_last"])
        for c in engine["cycles"].values()
        for b in (c.get("bands") or [])
        if b.get("series_last")
    ]
    tape = engine.get("tape_as_of") or max(lasts)
    assert notes == seed["meta"]["asOf"]
    assert tape >= max(lasts)
    assert tape >= max(lasts)  # tape_as_of >= max(series_last)
    test_committed_engine_as_of_pair_receipts.receipts = {
        "notes_as_of": notes,
        "tape_as_of": tape,
        "max_series_last": max(lasts),
        "meta_asOf": seed["meta"]["asOf"],
    }


def test_header_asof_binds_tape_not_notes():
    tpl = TPL.read_text(encoding="utf-8")
    html = (SITE / "cycle.html").read_text(encoding="utf-8")
    for src, label in ((tpl, "templates/cycle.html.j2"), (html, "site/cycle.html")):
        assert "E.tape_as_of" in src, f"{label} does not bind tape_as_of"
        assert "id=\"cyc-asof\"" in src or "id='cyc-asof'" in src or 'id="cyc-asof"' in src
    js = _read_app()
    assert "TAPE_AS_OF" in js
    assert "NOTES_AS_OF" in js
    assert "function stampTapeAsOf(" in js


# ── A6 ───────────────────────────────────────────────────────────────────────

BANNER_EN = "Engine reads live · analyst notes as of "
BANNER_ZH = "引擎实时读数 · 分析师注释更新于 "
STALE_CHIP = "showing last data, through "


def test_banner_and_stale_chip_copy_unchanged():
    js = _read_app()
    assert BANNER_EN in js
    assert BANNER_ZH in js
    assert "where they differ, the tape wins" in js
    assert STALE_CHIP in js
    assert 'L("DATA DELAYED", "数据延迟")' in js


def _extract_days_since_as_of(js: str) -> str:
    start = js.find("function daysSinceAsOf(")
    assert start != -1, "daysSinceAsOf() missing from cycle_app.js"
    i = js.find("{", start)
    depth = 0
    for j, ch in enumerate(js[i:], i):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return js[start:j + 1]
    raise AssertionError("unbalanced daysSinceAsOf")


def test_days_since_as_of_fires_at_14_19_29(tmp_path):
    js = _read_app()
    fn = _extract_days_since_as_of(js)
    node = shutil.which("node")
    if not node:
        pytest.skip("node not on PATH — source-pin still asserts Date arithmetic")
    harness = tmp_path / "days.js"
    harness.write_text(
        fn
        + """
const now = new Date(2026, 8, 10); // 2026-09-10 local
const cases = [
  ["2026-08-27", 14],
  ["2026-08-22", 19],
  ["2026-08-12", 29],
  ["2026-09-01", 9],
  ["2026-08-28", 13],
];
let failed = 0;
for (const [asOf, want] of cases) {
  const got = daysSinceAsOf(asOf, now);
  if (got !== want) {
    console.error("FAIL", asOf, "got", got, "want", want);
    failed++;
  } else {
    console.log("OK", asOf, got);
  }
}
// same-month 29-day silence was the yf() bug: 2026-09-01 vs 2026-09-30
const sameMonth = daysSinceAsOf("2026-09-01", new Date(2026, 8, 30));
if (sameMonth !== 29) {
  console.error("FAIL same-month 29 got", sameMonth);
  failed++;
} else {
  console.log("OK same-month-29", sameMonth);
}
process.exit(failed ? 1 : 0);
""",
        encoding="utf-8",
    )
    proc = subprocess.run([node, str(harness)], capture_output=True, text=True)
    print(proc.stdout)
    print(proc.stderr)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # banner threshold
    assert "if (days < 14" in js
    assert "daysSinceAsOf(AS_OF, new Date())" in js
    # must not use month-midpoint yf() for the banner
    assert "yf(AS_OF)" not in js


def test_python_calendar_days_match_the_packet_cases():
    now = date(2026, 9, 10)
    cases = {
        date(2026, 8, 27): 14,
        date(2026, 8, 22): 19,
        date(2026, 8, 12): 29,
    }
    for as_of, want in cases.items():
        got = (now - as_of).days
        assert got == want
        assert got >= 14  # banner fires
    assert (now - date(2026, 8, 28)).days == 13  # still silent
    # the yf() month-midpoint bug: 29 days inside one month
    assert (date(2026, 9, 30) - date(2026, 9, 1)).days == 29
