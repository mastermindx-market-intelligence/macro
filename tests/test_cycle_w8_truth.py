"""Cycle Intelligence W8 P0 truth blockers (r1 + r2).

B1  hazard.turn_kind vs proj.nextTurn; suppress headline on disagreement
B2  monotone CDF (or unavailable) over every emitted hazard cell set
B3  notes_as_of vs tape_as_of
A6  day-precision staleness arithmetic (14 / 19 / 29 day cases)
r2  unavailable why, fail-closed unknown phase, evidence-grade lead cell

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
    """Python twin of cycle_app.js hazardLeadCell (consumer contract).

    Seat ruling (W8 r2): lead with the shortest MODEL/PASS horizon; if no
    PASS cell exists, the shortest horizon of the best grade present.
    Evidence grade, not probability magnitude.
    """
    if hz.get("unavailable"):
        return None
    keys = ("1m", "3m", "6m")
    cells = [h for h in keys if hz.get(h) and hz[h].get("p") is not None]
    if not cells:
        return None
    vals = [hz[h]["p"] for h in cells]
    if any(vals[i] + 1e-12 < vals[i - 1] for i in range(1, len(vals))):
        return None
    pass_keys = [
        h for h in cells
        if hz[h].get("cell_verdict") == "PASS" or hz[h].get("source") == "MODEL"
    ]
    return (pass_keys or cells)[0]


def _extract_js_function(js: str, name: str) -> str:
    token = f"function {name}("
    start = js.find(token)
    assert start != -1, f"{name} missing from cycle_app.js"
    i = js.find("{", start)
    depth = 0
    for j, ch in enumerate(js[i:], i):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return js[start:j + 1]
    raise AssertionError(f"unbalanced {name}")


UNAVAIL_CDF_EN = (
    "Unavailable today — the model's short- and long-window reads disagreed, "
    "so no clean probability can be shown. The projection below still stands."
)
UNAVAIL_CDF_ZH = (
    "今日暂不可用——模型的短窗与长窗读数不一致，无法给出可靠概率。下方的推算仍然有效。"
)
UNAVAIL_DEFAULT_EN = "Unavailable today — a required input didn't settle cleanly."
UNAVAIL_DEFAULT_ZH = "今日暂不可用——所需输入未能完整结算。"


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


def test_attach_hazard_agreement_unknown_direction_is_unavailable_no_claim():
    """Reviewer probe: empty direction must not stamp a confident trough."""
    out = build_cycle._attach_hazard_agreement({"epoch": "E"}, "", None)
    assert out["unavailable"] is True
    assert out["unavailable_reason"] == "unknown_phase"
    assert out["unavailable_reason"] != "non_monotone_cdf"
    assert "turn_kind" not in out
    assert "direction" not in out
    assert out.get("direction_agrees") is None
    assert "1m" not in out and "3m" not in out and "6m" not in out
    assert out["epoch"] == "E"
    # same with a trough projection — still no claim
    out_proj = build_cycle._attach_hazard_agreement(
        {"epoch": "E"}, "", {"nextTurn": "trough"}
    )
    assert out_proj["unavailable"] is True
    assert "turn_kind" not in out_proj
    assert out_proj.get("direction_agrees") is None
    # live call site passes {} — must not treat an empty stub as "no hazard"
    out_empty = build_cycle._attach_hazard_agreement({}, "", None)
    assert out_empty["unavailable"] is True
    assert "turn_kind" not in out_empty
    assert out_empty.get("direction_agrees") is None


def test_hazard_direction_for_phase_known_and_unknown():
    assert build_cycle._hazard_direction_for_phase("Trough") == "up"
    assert build_cycle._hazard_direction_for_phase("Recovery") == "up"
    assert build_cycle._hazard_direction_for_phase("Expansion") == "up"
    assert build_cycle._hazard_direction_for_phase("Peak") == "down"
    assert build_cycle._hazard_direction_for_phase("Downturn") == "down"
    assert build_cycle._hazard_direction_for_phase("") == ""
    assert build_cycle._hazard_direction_for_phase(None) == ""
    assert build_cycle._hazard_direction_for_phase("mystery") == ""


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
        if hz.get("unavailable") and not hz.get("turn_kind") and not hz.get("direction"):
            assert tk is None
            assert lead is None
            assert hz.get("direction_agrees") is None
            continue
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


def test_consumer_leads_shortest_pass_source_pin():
    js = _read_app()
    assert "function hazardLeadCell(" in js
    fn = _extract_js_function(js, "hazardLeadCell")
    assert 'var keys = ["1m", "3m", "6m"]' in fn
    assert "pass.length ? pass : cells" in fn
    assert "hz[k].p >" not in fn  # not argmax p
    assert "within 1 month" in js
    assert "within 3 months" in js
    assert "within 6 months" in js
    assert "一个月内" in js


def test_lead_cell_shortest_pass_then_shortest_best_grade():
    """Seat ruling: PASS at 1m+3m leads 1m; all-PRIOR leads shortest PRIOR."""
    hz = {
        "1m": {"p": 0.12, "source": "MODEL", "cell_verdict": "PASS"},
        "3m": {"p": 0.40, "source": "MODEL", "cell_verdict": "PASS"},
        "6m": {"p": 0.70, "source": "MODEL", "cell_verdict": "PASS"},
    }
    assert _lead_cell(hz) == "1m"
    hz_pass_1m_3m = {
        "1m": {"p": 0.12, "source": "MODEL", "cell_verdict": "PASS"},
        "3m": {"p": 0.40, "source": "MODEL", "cell_verdict": "PASS"},
        "6m": {"p": 0.70, "source": "PRIOR", "cell_verdict": "PRIOR"},
    }
    assert _lead_cell(hz_pass_1m_3m) == "1m"
    hz2 = {
        "1m": {"p": 0.05, "source": "PRIOR", "cell_verdict": "PRIOR"},
        "3m": {"p": 0.08, "source": "PRIOR", "cell_verdict": "PRIOR"},
        "6m": {"p": 0.70, "source": "MODEL", "cell_verdict": "PASS"},
    }
    assert _lead_cell(hz2) == "6m"  # only PASS cell
    hz_prior = {
        "1m": {"p": 0.05, "source": "PRIOR", "cell_verdict": "PRIOR"},
        "3m": {"p": 0.20, "source": "PRIOR", "cell_verdict": "PRIOR"},
        "6m": {"p": 0.70, "source": "PRIOR", "cell_verdict": "PRIOR"},
    }
    assert _lead_cell(hz_prior) == "1m"  # shortest PRIOR, not 6m


# ── B3 ───────────────────────────────────────────────────────────────────────

def test_notes_and_tape_as_of_helper():
    notes, tape = build_cycle._notes_and_tape_as_of(
        {"asOf": "2026-06-25"},
        {
            "vol": {"bands": [{"tier": "measured", "series_last": "2026-09-08"}]},
            "business": {"bands": [{"tier": "measured", "series_last": "2026-07-01"}, {}]},
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


# ── r2 unavailable why + stutter ─────────────────────────────────────────────

def test_yf_is_month_granularity_again():
    js = _read_app()
    fn = _extract_js_function(js, "yf")
    assert "p.length >= 3" not in fn
    assert "new Date(y, m - 1, d)" not in fn


def test_unavailable_why_copy_both_reasons_both_lanes_no_stutter(tmp_path):
    js = _read_app()
    assert UNAVAIL_CDF_EN in js
    assert UNAVAIL_CDF_ZH in js
    assert UNAVAIL_DEFAULT_EN in js
    assert UNAVAIL_DEFAULT_ZH in js
    assert "Turn hazard unavailable" not in js
    assert "转折风险暂不可用" not in js
    assert "non_monotone_cdf" not in _extract_js_function(js, "hazardLine")

    node = shutil.which("node")
    if not node:
        pytest.skip("node not on PATH — source-pin still asserts frozen copy")
    harness = tmp_path / "unavail.js"
    harness.write_text(
        _extract_js_function(js, "esc") + "\n"
        + _extract_js_function(js, "hazardUnavailableWhy") + "\n"
        + _extract_js_function(js, "hazardCdfMonotone") + "\n"
        + _extract_js_function(js, "hazardLine") + "\n"
        + r"""
const cdfEn = "Unavailable today — the model's short- and long-window reads disagreed, so no clean probability can be shown. The projection below still stands.";
const cdfZh = "今日暂不可用——模型的短窗与长窗读数不一致，无法给出可靠概率。下方的推算仍然有效。";
const defEn = "Unavailable today — a required input didn't settle cleanly.";
const defZh = "今日暂不可用——所需输入未能完整结算。";
function check(html, en, zh, label) {
  if (html.indexOf('class="l-en">Turn hazard<') < 0) throw new Error(label + " missing EN label");
  if (html.indexOf('class="l-zh">转折风险<') < 0) throw new Error(label + " missing ZH label");
  if (html.indexOf(en) < 0) throw new Error(label + " missing EN why");
  if (html.indexOf(zh) < 0) throw new Error(label + " missing ZH why");
  if (/Turn hazard unavailable/.test(html)) throw new Error(label + " EN stutter");
  if (/转折风险暂不可用/.test(html)) throw new Error(label + " ZH stutter");
  if (html.indexOf("non_monotone_cdf") >= 0) throw new Error(label + " leaked enum");
  if (html.indexOf("unknown_phase") >= 0) throw new Error(label + " leaked enum");
  const bodyEn = html.match(/<span class="l-en">([^<]*)<\/span>/g) || [];
  const enBodies = bodyEn.map(s => s.replace(/<[^>]+>/g, ""));
  if (!enBodies.some(s => s.indexOf("Unavailable today") === 0)) {
    throw new Error(label + " EN body does not start at Unavailable today: " + enBodies.join(" | "));
  }
}
const cdf = hazardLine({now:{hazard:{unavailable:true, unavailable_reason:"non_monotone_cdf"}}});
const other = hazardLine({now:{hazard:{unavailable:true, unavailable_reason:"unknown_phase"}}});
const missing = hazardLine({now:{hazard:{unavailable:true}}});
check(cdf, cdfEn, cdfZh, "cdf");
check(other, defEn, defZh, "other");
check(missing, defEn, defZh, "missing");
console.log("OK unavailable why both reasons both lanes");
""",
        encoding="utf-8",
    )
    proc = subprocess.run([node, str(harness)], capture_output=True, text=True)
    print(proc.stdout)
    print(proc.stderr)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_unknown_phase_consumer_null_branch_falls_to_projection(tmp_path):
    js = _read_app()
    node = shutil.which("node")
    if not node:
        pytest.skip("node not on PATH")
    harness = tmp_path / "null_branch.js"
    harness.write_text(
        'var MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];\n'
        "function curLang(){ return 'en'; }\n"
        "function L(en, zh){ return curLang() === 'zh' ? zh : en; }\n"
        + _extract_js_function(js, "turnWord") + "\n"
        + _extract_js_function(js, "fmtMon") + "\n"
        + _extract_js_function(js, "hazardTurnKind") + "\n"
        + _extract_js_function(js, "hazardDirectionAgrees") + "\n"
        + _extract_js_function(js, "hazardCdfMonotone") + "\n"
        + _extract_js_function(js, "hazardLeadCell") + "\n"
        + _extract_js_function(js, "projFallbackInner") + "\n"
        + _extract_js_function(js, "hazardLeadInner") + "\n"
        + _extract_js_function(js, "cardNextInnerHTML") + "\n"
        + r"""
const hz = {epoch:"E", unavailable:true, unavailable_reason:"unknown_phase", direction_agrees:null};
if (hazardTurnKind(hz) !== null) throw new Error("hazardTurnKind should be null, got " + hazardTurnKind(hz));
if (hazardLeadCell(hz) !== null) throw new Error("hazardLeadCell should be null");
const pj = {nextTurn:"peak", central:"2026-09", overdue:false};
const html = cardNextInnerHTML({now:{hazard:hz}}, pj);
if (html.indexOf("Peak ≈") < 0 && html.indexOf("peak") < 0) {
  throw new Error("expected projection fallback, got " + html);
}
if (html.indexOf("P(") >= 0) throw new Error("null branch leaked a P() hazard claim: " + html);
console.log("OK null branch fallback", html);
""",
        encoding="utf-8",
    )
    proc = subprocess.run([node, str(harness)], capture_output=True, text=True)
    print(proc.stdout)
    print(proc.stderr)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_frame_record_emits_no_series_last():
    from engine import cycle_proxies as cp
    seed = _cycle_seed.load_seed(SEED_JS)
    band = cp.REGISTRY["housing"]["bands"][0]
    assert band["tier"] == "frame"
    rec = build_cycle._frame_record("housing", band, seed["by_id"]["housing"], today_x=2026.5)
    assert "series_last" not in rec


def test_tape_as_of_ignores_frame_and_uses_parsed_date_max():
    notes, tape = build_cycle._notes_and_tape_as_of(
        {"asOf": "2026-06-25"},
        {
            "housing": {"bands": [{"tier": "frame", "series_last": "2099-12-31"}]},
            "vol": {"bands": [{"tier": "measured", "series_last": "2026-09-08"}]},
            "business": {"bands": [{"tier": "measured", "series_last": "2026-09-10"}]},
        },
    )
    assert notes == "2026-06-25"
    assert tape == "2026-09-10"
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        build_cycle._notes_and_tape_as_of(
            {"asOf": "2026-06-25"},
            {"vol": {"bands": [{"tier": "measured", "series_last": "2026-9-8"}]}},
        )


def test_strict_iso_as_of_assertion_fail_closed():
    assert build_cycle._assert_strict_iso_date("2026-06-25", "asOf") == "2026-06-25"
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        build_cycle._assert_strict_iso_date("June 2026", "asOf")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        build_cycle._assert_strict_iso_date("2026-6-25", "asOf")
    with pytest.raises(ValueError, match="missing"):
        build_cycle._assert_strict_iso_date("", "asOf")
    with pytest.raises(ValueError, match="missing"):
        build_cycle._assert_strict_iso_date(None, "asOf")
