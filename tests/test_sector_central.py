"""Tests for the US Sector Central fuser (engine.sector_central) + its self-grader.

The fuser's load-bearing US-specific behaviors are tested deterministically with hand-built
cycle records: (1) the cycle-state score keys off the 0–100 oscillator (no `signature` field);
(2) the VALIDATED absolute-trend gate de-rates / caps a bullish read when a sector is below its
own trend (the genuine US drawdown lever — the opposite of China, where the gate failed);
(3) the per-sector macro-beta differentiation gates cyclicals harder than defensives in risk-off.
The public compute() is checked for fail-soft well-formedness, and the grader for a PIT roundtrip.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import sector_central as sc
from engine import sector_central_grader as scg


def _rec(ticker="XLK", name="Technology", pos=10.0, phase="Recovery", signal="BUY",
         rs_rank=1, above200d=True, rs_63d=5.0, kind="sector"):
    """A bullish, washed-out cycle record (the strongest setup) unless overridden."""
    return {
        "id": ticker.lower(), "ticker": ticker, "kind": kind, "name": name,
        "accent": "#38bdf8", "group": "Growth",
        "proj": {"tilt": "tailwind", "nextTurn": "trough", "low": "2026-07", "high": "2027-01"},
        "now": {"pos": pos, "phase": phase, "phaseLabel": phase, "signal": signal,
                "osc_slope": 1.0, "rs_rank": rs_rank, "above200d": above200d, "rs_63d": rs_63d},
    }


def _mkt(risk_on=0.5, gate_factor=1.0):
    return {"risk_on": risk_on, "gate_factor": gate_factor, "state_en": "Risk-on",
            "quad_name": "Goldilocks", "liquidity": "expanding", "derisk_blended": 0.25,
            "_crowd_by_ticker": {}}


# ------------------------------------------------------------- state scoring ----

def test_state_score_washout_is_bullish_stretched_is_bearish():
    washed, _ = sc._state_score({"pos": 5, "phase": "Trough", "signal": None})
    stretched, _ = sc._state_score({"pos": 95, "phase": "Peak", "signal": None})
    assert washed > 0.4
    assert stretched < -0.3


def test_state_score_turn_signal_nudges():
    base, _ = sc._state_score({"pos": 50, "phase": "Expansion", "signal": None})
    buy, _ = sc._state_score({"pos": 50, "phase": "Expansion", "signal": "BUY"})
    sell, _ = sc._state_score({"pos": 50, "phase": "Expansion", "signal": "SELL"})
    assert buy > base > sell


def test_as_str_flattens_list_proxy():
    assert sc._as_str(["XLP", "XLU"]) == "XLP/XLU"
    assert sc._as_str("XLK") == "XLK"
    assert sc._as_str(None) is None


def test_tier_for_thresholds():
    assert sc._tier_for(80)[0] == "Accumulate"
    assert sc._tier_for(60)[0] == "Constructive"
    assert sc._tier_for(50)[0] == "Neutral"
    assert sc._tier_for(35)[0] == "Cautious"
    assert sc._tier_for(10)[0] == "Reduce"


# -------------------------------------- the VALIDATED absolute-trend drawdown gate ----

def test_trend_gate_below_trend_derates_and_caps_a_bullish_read():
    """The US lever: a strongly bullish washed-out sector that is BELOW its own 200-day trend is
    de-rated and cannot be top-tier (validated_risk_control), even though the cycle setup screams
    buy. This is the XLC 2026-06 behavior and the core US-vs-China difference."""
    rec = _rec()
    above = sc._fuse(rec, _mkt(), 11, trend={"pass": True, "above_200dma": True})
    below = sc._fuse(rec, _mkt(), 11, trend={"pass": False, "above_200dma": False})
    assert above["conviction"]["score"] > below["conviction"]["score"]
    # below-trend can never be an up-tier conviction
    assert below["conviction"]["label_en"] not in ("Accumulate", "Constructive")
    assert above["conviction"]["label_en"] in ("Accumulate", "Constructive")
    assert below["components"]["trend_pass"] is False


def test_trend_gate_none_is_neither_derated_nor_capped():
    rec = _rec()
    none = sc._fuse(rec, _mkt(), 11, trend=None)
    above = sc._fuse(rec, _mkt(), 11, trend={"pass": True})
    # an unknown gate behaves like a permissive (no de-rate)
    assert none["conviction"]["score"] == above["conviction"]["score"]


# ----------------------------------------- per-sector macro-beta differentiation ----

def test_macro_beta_gates_cyclical_harder_than_defensive_in_riskoff():
    """In a risk-OFF regime the per-sector gate shrinks a cyclical (XLF, β+) more than a
    defensive (XLP, β−). Both are otherwise identical bullish above-trend reads."""
    mkt = _mkt(risk_on=-0.6, gate_factor=0.6)
    cyc = sc._fuse(_rec(ticker="XLF", name="Financials"), mkt, 11, trend={"pass": True})
    dfn = sc._fuse(_rec(ticker="XLP", name="Consumer Staples"), mkt, 11, trend={"pass": True})
    # the defensive keeps a higher effective gate → higher conviction
    assert dfn["components"]["gate_eff"] > cyc["components"]["gate_eff"]
    assert dfn["conviction"]["score"] >= cyc["conviction"]["score"]
    assert cyc["components"]["macro_beta"] > dfn["components"]["macro_beta"]


# ------------------------------------------------------------- momentum confirmer ----

def test_momentum_is_capped_and_lagging_marks_early():
    rec = _rec(rs_rank=11, above200d=True)            # last of 11 = lagging
    out = sc._fuse(rec, _mkt(), 11, trend={"pass": True})
    assert -0.3 <= out["components"]["momentum"] <= 0.3      # hard cap
    assert out["conviction"]["early"] is True               # bullish lead + lagging RS = early


def test_reasoning_trace_tiers_are_well_formed():
    out = sc._fuse(_rec(), _mkt(), 11, trend={"pass": True},
                   heat={"heat_1M": 2.5, "breadth_pct": 80})
    layers = {r["layer"] for r in out["reasoning"]}
    assert {"Cycle state", "Trend gate", "Regime gate", "Momentum"} <= layers
    for r in out["reasoning"]:
        assert r["tier"] in ("validated", "confirmer", "display")
        assert r["en"] and r["zh"]


def test_reasoning_zh_has_no_english_leak():
    """The zh reasoning BODIES must translate every phaseLabel/quad/lead/signal/beta token so a
    zh reader sees no English in the expanded trace (guards the build-side i18n fix). state_zh is
    supplied upstream, so the regime row falls back to it rather than leaking the English state."""
    import re
    latin = re.compile(r"[A-Za-z]")
    mkt = {"state_en": "Risk-on — adding", "state_zh": "风险偏好 — 加仓", "derisk_blended": 0.25,
           "quad": "Q1", "quad_name": "Goldilocks", "liquidity": "expanding",
           "gate_factor": 0.6, "risk_on": 0.5}
    fwd = {"trend_pass": True, "ret_12m": 0.17}
    plabs = [("Bottoming", "Trough"), ("Prime entry", "Recovery"), ("Trending", "Expansion"),
             ("Topping", "Peak"), ("Rolling over", "Downturn")]
    for (plab, phase), sig, lead, beta in [(p, s, ld, b) for p in plabs
                                           for s in ("BUY", "SELL", None)
                                           for ld in ("leading", "lagging", "mid-pack")
                                           for b in (0.5, -0.5, 0.0)]:
        state_d = {"pos": 27.0, "phase": phase, "phaseLabel": plab, "signal": sig, "osc_slope": 1.0}
        rows = sc._trace(state_d, fwd, mkt, {"rs_rank": 3, "lead": lead},
                         {"n_crowded": 2, "n_members": 6, "frac": 0.33}, early=True,
                         stretched=True, beta=beta, heat={"breadth_pct": 55, "heat_1M": 2.3})
        for r in rows:
            assert not latin.search(r["zh"]), f"English leaked into zh body: {r['zh']!r}"


# ---------------------------------------------------------------- trend gates map ----

def test_trend_gates_keys_sectors_by_ticker_and_baskets_by_bid():
    idx = pd.bdate_range("2022-01-01", periods=400)
    up = pd.Series(100 * np.cumprod(1 + np.full(400, 0.001)), index=idx)      # above trend, +12m
    dn = pd.Series(100 * np.cumprod(1 + np.full(400, -0.0015)), index=idx)    # below trend, −12m
    closes = pd.DataFrame({"XLK": up, "XLE": dn})
    rotation = {"ranks": [{"id": "us_sector_tech", "eligible": True,
                           "gate": {"above_200dma": True, "pos_12m": True}}]}
    gates = sc._trend_gates(closes, rotation)
    assert gates["xlk"]["pass"] is True and gates["xlk"]["source"] == "spdr"
    assert gates["xle"]["pass"] is False
    assert gates["b-us_sector_tech"]["pass"] is True and gates["b-us_sector_tech"]["source"] == "basket-ctx"


# --------------------------------------------------------------- compute (soft) ----

def test_compute_is_fail_soft_and_well_formed():
    """compute() must return None OR a well-formed payload — never raise (additive build)."""
    out = sc.compute()
    if out is None:
        return                                       # store unavailable in this env — acceptable
    assert out["meta"]["region"] == "us"
    assert isinstance(out["sectors"], list) and out["sectors"]
    for s in out["sectors"]:
        c = s["conviction"]
        assert 0 <= c["score"] <= 100
        assert c["label_en"] in {t[1] for t in sc.TIERS}
        assert isinstance(s["reasoning"], list) and s["reasoning"]
    # Board order: XSR-R2/R9 re-sorts by fast-rotation rank when the rotation artifact is
    # armed, and FAILS OPEN to the conviction sort when it is missing/stale/unparseable.
    # Assert whichever contract compute() DECLARES it used — a bare conviction-sort
    # assertion rotted silently here the day the rotation lens landed, because this suite
    # was run by no CI job.
    scores = [s["conviction"]["score"] for s in out["sectors"]]
    assert out["meta"]["board_order"] == (
        "fast-lens (XSR-R2)" if out["market"]["rotation_board_order"] == "fast-lens"
        else "conviction")
    # The sentence under the board reads this: fresh only when the lens really set the order.
    assert (out["market"]["fast_lens"]["state"] == "fresh") == (
        out["market"]["rotation_board_order"] == "fast-lens")
    if out["market"]["rotation_board_order"] == "fast-lens":
        # rotation-matched records come first, ascending by per-kind ordinal (1..n) …
        ordinals = [(s.get("rotation") or {}).get("ordinal") for s in out["sectors"]]
        matched = [o for o in ordinals if o is not None]
        assert matched == list(range(1, len(matched) + 1))
        # … then the unmatched tail, which keeps the conviction sort among itself.
        assert all(o is None for o in ordinals[len(matched):])
        tail = scores[len(matched):]
        assert tail == sorted(tail, reverse=True)
    else:
        assert scores == sorted(scores, reverse=True)


# --------------------------------------------------------------------- grader ----

def test_grader_append_keeps_first_and_grade_accrues(tmp_path, monkeypatch):
    monkeypatch.setattr(scg.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(scg, "_yahoo_panel", lambda: None)
    monkeypatch.setattr(scg, "_basket_levels", lambda: {})
    data = {"as_of": "2026-06-01",
            "sectors": [{"id": "xlk", "kind": "sector", "ticker": "XLK", "name": "Technology",
                         "conviction": {"score": 70, "label_en": "Accumulate", "dir": "up",
                                        "confluence": {"agree": 3}},
                         "forward": {"trend_pass": True, "ret_12m": 0.2},
                         "components": {"gate_factor": 0.6}}],
            "baskets": []}
    assert scg.append_central_log(data) == 1
    # keep-FIRST: a second append on the same (date, id) must not duplicate
    data2 = dict(data); data2["sectors"] = [dict(data["sectors"][0])]
    data2["sectors"][0]["conviction"] = {"score": 5, "label_en": "Reduce", "dir": "down",
                                         "confluence": {"agree": 0}}
    scg.append_central_log(data2)
    g = scg.grade()
    assert g["available"] is True and g["n_calls"] == 1
    # sparse → accruing (no matured horizons / <3 graded)
    for h in ("21d", "63d", "126d"):
        assert g["by_horizon"][h].get("dir_hit_rate") in (None,)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# ---------------------------------------------------------------------------
# Fast-lens honesty: the page must say what order the board is in and why a card has no rank.
# Production 2026-10-31: the sentence under the board said "ordered by the fast rotation lens"
# while the payload said board_order=conviction, and all 60 cards said "awaiting tonight's data".
# ---------------------------------------------------------------------------
import datetime as _dt  # noqa: E402
import json as _json  # noqa: E402
import pathlib as _pathlib  # noqa: E402
import re as _re  # noqa: E402
import shutil as _shutil  # noqa: E402
import subprocess as _subprocess  # noqa: E402

import jinja2 as _jinja2  # noqa: E402

_ROOT = _pathlib.Path(__file__).resolve().parents[1]
_TEMPLATE = (_ROOT / "templates" / "sector_central.html.j2").read_text(encoding="utf-8")
_BUILDER = (_ROOT / "scripts" / "build_sector_central.py").read_text(encoding="utf-8")
_needs_node = pytest.mark.skipif(_shutil.which("node") is None, reason="node not on PATH")
_NOTE_RE = _re.compile(r'<p class="rvx-sec-sub" id="board-order-note".*?\{% endif %\}', _re.S)
_T_MACRO = "{% macro t(en, zh='') -%}<en>{{ en }}</en><zh>{{ zh if zh else en }}</zh>{%- endmacro %}"


def _write_artifact(monkeypatch, tmp_path, body):
    monkeypatch.setattr(sc.config, "data_dir", lambda: tmp_path)
    if body is None:
        return
    d = tmp_path / "us_sector_rotation"
    d.mkdir(parents=True)
    text = body if isinstance(body, str) else _json.dumps(body)
    (d / "latest.json").write_text(text, encoding="utf-8")


def _ts(hours_ago):
    now = _dt.datetime.now(_dt.timezone.utc)
    return (now - _dt.timedelta(hours=hours_ago)).isoformat()


_INST = [{"kind": "sector", "id": "xlk", "ticker": "XLK", "rotation_rank": 1}]


def _status(monkeypatch, tmp_path, body):
    # Mirrors compute() (engine/sector_central.py, SIC-D-B02 #9917): the loader returns the raw
    # file and the settled-session gate decides arming — no wall-clock age rule. The consumer
    # session is pinned to 2026-10-30 so a 2026-10-16 artifact, a session-less one and a hostile
    # one all fail the gate exactly as they would on the rendered page; #10290 wrote this helper
    # against the pre-B02 48 h loader guard, which the gate replaced.
    from engine import sector_generation_guard as _sgg
    _write_artifact(monkeypatch, tmp_path, body)
    raw = sc._load_rotation_artifact()
    alignment = _sgg.session_alignment(raw.get("session") or raw.get("asof"), "2026-10-30",
                                       today=_dt.date(2026, 10, 30))
    if alignment["status"] != "aligned":
        raw = {}
    return sc._fast_lens_status(bool(raw and raw.get("instruments")), raw)


def test_fast_lens_status_fresh_artifact(monkeypatch, tmp_path):
    body = {"asof": "2026-10-30", "ts": _ts(2), "instruments": _INST}
    assert _status(monkeypatch, tmp_path, body) == {"state": "fresh", "asof": "2026-10-30"}


def test_fast_lens_status_stale_artifact_names_its_own_date(monkeypatch, tmp_path):
    body = {"asof": "2026-10-16", "ts": _ts(49), "instruments": _INST}
    assert _status(monkeypatch, tmp_path, body) == {"state": "stale", "asof": "2026-10-16"}


def test_fast_lens_status_stale_without_asof_falls_back_to_the_timestamp_date(monkeypatch, tmp_path):
    ts = _ts(100)
    body = {"ts": ts, "instruments": _INST}
    assert _status(monkeypatch, tmp_path, body) == {"state": "stale", "asof": ts[:10]}


@pytest.mark.parametrize("body", [
    None,
    "{not json",
    "[1, 2]",
    {"asof": "2026-10-16", "ts": _ts(100), "instruments": []},
    {"asof": "2026-10-30", "ts": _ts(1), "instruments": []},
])
def test_fast_lens_status_nothing_to_rank_is_absent(monkeypatch, tmp_path, body):
    assert _status(monkeypatch, tmp_path, body) == {"state": "absent", "asof": None}


def test_fast_lens_status_never_passes_a_hostile_date_through(monkeypatch, tmp_path):
    ts = _ts(100)
    body = {"asof": "<img src=x onerror=alert(1)>", "ts": ts, "instruments": _INST}
    assert _status(monkeypatch, tmp_path, body) == {"state": "stale", "asof": ts[:10]}


@pytest.mark.parametrize("session,expected", [
    ("2026-11-05", "fresh"), ("2026-11-04", "stale"), (None, "absent"),
])
def test_compute_publishes_status_from_the_selected_rotation_input(session, expected):
    inputs = _explicit_central_inputs(rotation_session=session)
    out = sc.compute_from_inputs(inputs, evaluation_date=_dt.date(2026, 11, 6))
    assert out["market"]["fast_lens"]["state"] == expected
    assert (out["market"]["rotation_board_order"] == "fast-lens") == (expected == "fresh")
    assert out["market"]["fast_lens"]["asof"] == session


def test_builder_hands_the_status_to_the_page():
    assert 'fast_lens=(data.get("market") or {}).get("fast_lens") or {},' in _BUILDER


def _note(fast_lens):
    block = _NOTE_RE.search(_TEMPLATE)
    assert block, "board-order note is missing its id or its branch"
    env = _jinja2.Environment(autoescape=True)
    out = env.from_string(_T_MACRO + block.group(0)).render(fast_lens=fast_lens)
    en = " ".join(_re.findall(r"<en>(.*?)</en>", out, _re.S))
    zh = " ".join(_re.findall(r"<zh>(.*?)</zh>", out, _re.S))
    return en, zh


def test_note_keeps_the_fast_lens_sentence_only_when_the_lens_ordered_the_board():
    en, zh = _note({"state": "fresh", "asof": "2026-10-30"})
    assert "ordered by the fast rotation lens" in en
    assert "卡片按快速轮动视角排序" in zh


def test_note_says_conviction_and_names_the_date_when_stale():
    en, zh = _note({"state": "stale", "asof": "2026-10-16"})
    assert en.startswith("Cards are ordered by conviction.") and "2026-10-16" in en
    assert zh.startswith("卡片按信念排序。") and "2026-10-16" in zh
    assert "ordered by the fast rotation lens" not in en
    assert "按快速轮动视角排序" not in zh


@pytest.mark.parametrize("fast_lens", [{"state": "absent", "asof": None}, {}, None])
def test_note_says_conviction_with_no_date_when_nothing_was_published(fast_lens):
    en, zh = _note(fast_lens)
    assert en.startswith("Cards are ordered by conviction.") and "not published" in en
    assert zh.startswith("卡片按信念排序。") and "尚未发布" in zh
    assert "ordered by the fast rotation lens" not in en


def _rail_copy(fl):
    """Run the page's own copy function: L joins both languages so each arm is visible."""
    m = _re.search(r"function fastLensNoRankCopy\(fl\)\{.*?\n    \}\n", _TEMPLATE, _re.S)
    assert m, "fastLensNoRankCopy is gone"
    src = ("var L=function(e,z){return e+'|'+z};"
           "var esc=function(s){return String(s).replace(/</g,'&lt;')};"
           + m.group(0)
           + "process.stdout.write(fastLensNoRankCopy(%s));" % _json.dumps(fl))
    res = _subprocess.run(["node", "-e", src], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    return res.stdout


@_needs_node
def test_rail_stale_names_the_date_in_both_languages():
    assert _rail_copy({"state": "stale", "asof": "2026-10-16"}) == \
        "no ranks since 2026-10-16|2026-10-16 后无排名"


@_needs_node
def test_rail_fresh_says_this_row_is_not_covered():
    # A proxy basket has no rank even on a fresh lens. It will not get one tonight either.
    assert _rail_copy({"state": "fresh", "asof": "2026-10-30"}) == "not ranked on this lens|不在此视角排名内"


@_needs_node
@pytest.mark.parametrize("fl", [{"state": "absent", "asof": None}, {}, {"state": "stale", "asof": None}])
def test_rail_without_a_date_promises_nothing(fl):
    assert _rail_copy(fl) == "no ranks published|尚未发布排名"


@_needs_node
def test_rail_escapes_the_date():
    assert "<img" not in _rail_copy({"state": "stale", "asof": "<img src=x>"})


def test_card_rail_uses_the_copy_function_and_the_payload_status():
    assert "fastLensNoRankCopy((D.market&&D.market.fast_lens)||{})" in _TEMPLATE


def test_the_page_no_longer_promises_data_tonight():
    assert "awaiting tonight" not in _TEMPLATE
    assert "等待今晚数据" not in _TEMPLATE


# ------------------------------------------------------ explicit runtime inputs ----

def _explicit_central_inputs(*, rotation_session="2026-11-05"):
    """Small real arithmetic fixture; no mocked fusion, trend, or measured-read helper."""
    sectors = [_rec(), _rec(ticker="XLF", name="Financials", rs_rank=2)]
    basket = _rec(ticker="XLK", name="AI", kind="basket")
    basket["ticker"] = ["XLK", "XLC"]
    basket["id"] = "b-ai"
    for rec in [*sectors, basket]:
        rec["now"]["timing_state"] = "UPSWING"
    cycle = {"meta": {"asOf": "2026-11-05", "benchmark": "SPY"},
             "sectors": sectors, "baskets": [basket]}
    index = pd.bdate_range(end="2026-11-05", periods=280)
    closes = pd.DataFrame({"XLK": np.linspace(100, 160, len(index)),
                           "XLF": np.linspace(110, 90, len(index))}, index=index)
    rotation = ({
        "asof": rotation_session, "session": rotation_session,
        "ts": rotation_session + "T22:00:00Z",
        "instruments": [{"id": "xlf", "ticker": "XLF", "kind": "sector",
                         "rotation_rank": 1, "rotation_score": 0.9}],
    } if rotation_session else {})
    market = _mkt(risk_on=-0.6, gate_factor=0.6)
    market["heat"] = {"Technology": {"heat_1M": 2.5, "breadth_pct": 80}}
    market["_crowd_by_ticker"] = {"AAA": {"level": "crowded"}}
    return sc.SectorCentralInputs(
        cycle_spine=cycle, market_context=market, closes=closes,
        narrative_rotation={"ranks": [
            {"id": "ai", "eligible": True, "gate": {"above_200dma": True, "ret_12m": 0.1}}]},
        membership_document={"version": "fixture-v1", "baskets": {
            "ai": {"members": [{"ticker": "AAA", "added": "2020-01-01"}]}}},
        membership_unavailable=False, rotation_artifact=rotation,
        rotation_events={"schema": "rotation_events.v1", "ok": True,
                         "as_of": "2026-11-05", "active": [],
                         "early_context": {"as_of": "2026-11-05", "state": "quiet",
                                           "coverage": {"n": 2}, "reason_codes": []}},
        fusion_calibrations={
            sc.fusion_calibration_key(rec): (0.4, 0.8) for rec in [*sectors, basket]},
    )


@pytest.mark.parametrize("rotation_session,membership_unavailable", [
    ("2026-11-05", False), ("2026-11-04", False),
    (None, False), (None, True),
])
def test_explicit_core_never_reads_ambient_data_clock_or_ledgers(
        monkeypatch, rotation_session, membership_unavailable):
    from dataclasses import replace
    from pathlib import Path
    import builtins
    import socket
    import requests
    from engine import conditions, cycles, inputs as engine_inputs
    from engine import narrative_rotation, leadership_rotation_context, sector_cycles

    # Initialize code dependencies before trapping data access. Importing Python
    # modules is code loading, not acquisition of an undeclared market input.
    assert leadership_rotation_context.MEASURED_READ_SCHEMA
    assert sector_cycles.SECTORS
    bundle = _explicit_central_inputs(rotation_session=rotation_session)
    bundle = replace(bundle, membership_document={}, rotation_events=None,
                     membership_unavailable=membership_unavailable)
    evaluation_day = _dt.date(2026, 11, 6)

    class UndeclaredInput(BaseException):
        pass  # fail-soft 'except Exception' must not hide a forbidden read

    def forbidden(*args, **kwargs):
        raise UndeclaredInput("explicit fusion touched an ambient input or effect")

    class NoClockDateTime(_dt.datetime):
        now = classmethod(forbidden)
        utcnow = classmethod(forbidden)
        today = classmethod(forbidden)

    class NoClockDate(_dt.date):
        today = classmethod(forbidden)

    with monkeypatch.context() as guard:
        for name in ("data_dir", "load"):
            guard.setattr(sc.config, name, forbidden)
        for name in ("market_context", "_load_rotation_artifact", "_load_rotation_events",
                     "_resolve_fusion_calibration"):
            guard.setattr(sc, name, forbidden)
        guard.setattr(engine_inputs, "yahoo_closes", forbidden)
        guard.setattr(sector_cycles, "compute", forbidden)
        guard.setattr(narrative_rotation, "compute_narrative_rotation", forbidden)
        guard.setattr(conditions, "sector_macro_beta", forbidden)
        guard.setattr(cycles, "risk_size_mult", forbidden)
        guard.setattr(scg, "append_central_log", forbidden)
        guard.setattr(scg, "grade", forbidden)
        guard.setattr(builtins, "open", forbidden)
        for name in ("open", "read_text", "read_bytes", "write_text", "write_bytes", "exists"):
            guard.setattr(Path, name, forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(requests.sessions.Session, "request", forbidden)
        guard.setattr(_dt, "datetime", NoClockDateTime)
        guard.setattr(_dt, "date", NoClockDate)
        out = sc.compute_from_inputs(bundle, evaluation_date=evaluation_day)
    assert out["as_of"] == "2026-11-05"
    assert out["measured_read"]["confirmed_events"]["reason"] == "missing_input"
    assert out["baskets"][0]["membership_coverage"]["status"] == (
        "source_unavailable" if membership_unavailable else "basket_not_listed")


def test_explicit_core_is_repeatable_and_does_not_mutate_or_alias_documents():
    from copy import deepcopy
    from dataclasses import fields

    bundle = _explicit_central_inputs()
    before = deepcopy(bundle)
    first = sc.compute_from_inputs(bundle, evaluation_date=_dt.date(2026, 11, 6))
    second = sc.compute_from_inputs(bundle, evaluation_date=_dt.date(2026, 11, 6))
    assert first == second
    first["market"]["heat"]["Technology"]["heat_1M"] = -999
    first["sectors"][0]["cycle"]["proj"]["tilt"] = "changed by consumer"
    first["measured_read"]["early_context"]["coverage"]["n"] = 999
    for field in fields(bundle):
        if field.name == "closes":
            pd.testing.assert_frame_equal(bundle.closes, before.closes)
        else:
            assert getattr(bundle, field.name) == getattr(before, field.name)


def test_explicit_calibration_drives_existing_beta_and_size_arithmetic(monkeypatch):
    from dataclasses import replace
    bundle = _explicit_central_inputs()
    original = sc.compute_from_inputs(bundle, evaluation_date=_dt.date(2026, 11, 6))
    calibration = dict(bundle.fusion_calibrations)
    key = sc.fusion_calibration_key(bundle.cycle_spine["sectors"][0])
    calibration[key] = (0.0, 0.5)
    changed = sc.compute_from_inputs(
        replace(bundle, fusion_calibrations=calibration), evaluation_date=_dt.date(2026, 11, 6))
    before = next(r for r in original["sectors"] if r["ticker"] == "XLK")
    after = next(r for r in changed["sectors"] if r["ticker"] == "XLK")
    assert before["components"]["macro_beta"] == 0.4
    assert after["components"]["macro_beta"] == 0.0
    assert after["components"]["risk_size_mult"] == 0.5
    assert after["components"]["gate_eff"] > before["components"]["gate_eff"]
    assert after["conviction"]["score"] != before["conviction"]["score"]


@pytest.mark.parametrize("bad_value", ["missing", None])
def test_missing_explicit_calibration_cannot_fall_back(monkeypatch, bad_value):
    from dataclasses import replace
    bundle = _explicit_central_inputs()
    calibration = dict(bundle.fusion_calibrations)
    key = sc.fusion_calibration_key(bundle.cycle_spine["sectors"][0])
    if bad_value == "missing":
        del calibration[key]
    else:
        calibration[key] = bad_value
    calls = []
    def forbidden(*args):
        calls.append(args)
        raise AssertionError("legacy calibration must not run")
    monkeypatch.setattr(sc, "_resolve_fusion_calibration", forbidden)
    with pytest.raises(ValueError, match="fusion calibration"):
        sc.compute_from_inputs(replace(bundle, fusion_calibrations=calibration),
                               evaluation_date=_dt.date(2026, 11, 6))
    assert calls == []


def test_calibration_key_distinguishes_risk_family_state_and_list_proxy():
    from copy import deepcopy
    record = _rec(ticker="XLP", kind="basket")
    record["ticker"] = ["XLP", "XLU"]
    record["family"] = "basket"
    record["now"]["timing_state"] = "UPSWING"
    key = sc.fusion_calibration_key(record)
    assert key == ("XLP/XLU", "basket", "UPSWING")
    changed = deepcopy(record)
    changed["now"]["timing_state"] = "DOWNSWING"
    assert sc.fusion_calibration_key(changed) != key
    changed = deepcopy(record)
    changed["family"] = "us_sector"
    assert sc.fusion_calibration_key(changed) != key


def test_explicit_date_controls_future_rotation_without_refreshing_source_date():
    bundle = _explicit_central_inputs()
    future = sc.compute_from_inputs(bundle, evaluation_date=_dt.date(2026, 11, 4))
    current = sc.compute_from_inputs(bundle, evaluation_date=_dt.date(2026, 11, 6))
    assert future["meta"]["rotation_alignment"]["reason"] == "future_session"
    assert current["meta"]["rotation_alignment"]["reason"] == "aligned"
    assert future["as_of"] == current["as_of"] == "2026-11-05"
    with pytest.raises(ValueError, match="explicit date"):
        sc.compute_from_inputs(bundle, evaluation_date=None)


def test_explicit_rotation_event_revision_and_membership_status_are_preserved():
    from dataclasses import replace
    bundle = _explicit_central_inputs()
    baseline = sc.compute_from_inputs(bundle, evaluation_date=_dt.date(2026, 11, 6))
    assert baseline["measured_read"]["confirmed_events"]["status"] == "none"
    assert baseline["measured_read"]["confirmed_events"]["n_active"] == 0
    assert baseline["baskets"][0]["membership_coverage"]["status"] == "ok"
    assert baseline["baskets"][0]["membership_coverage"]["crowding_input_members"] == 1
    revised_events = dict(bundle.rotation_events, as_of="2026-11-04")
    revised = sc.compute_from_inputs(
        replace(bundle, rotation_events=revised_events, membership_unavailable=True),
        evaluation_date=_dt.date(2026, 11, 6))
    assert revised["measured_read"]["confirmed_events"]["status"] == "incompatible_generation"
    assert revised["measured_read"]["confirmed_events"]["reason"] == "as_of_mismatch"
    assert revised["baskets"][0]["membership_coverage"]["status"] == "source_unavailable"
    assert revised["baskets"][0]["crowding"] is None


def test_compatibility_adapter_selects_inputs_and_delegates_without_mutating_context(
        monkeypatch, tmp_path):
    from copy import deepcopy
    from engine import sector_cycles, inputs as engine_inputs, narrative_rotation
    bundle = _explicit_central_inputs()
    membership_dir = tmp_path / "baskets"
    membership_dir.mkdir()
    (membership_dir / "membership.json").write_text(_json.dumps(bundle.membership_document))
    monkeypatch.setattr(sc.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(sector_cycles, "compute", lambda: deepcopy(bundle.cycle_spine))
    monkeypatch.setattr(sc, "market_context", lambda: bundle.market_context)
    monkeypatch.setattr(engine_inputs, "yahoo_closes", lambda: bundle.closes)
    monkeypatch.setattr(narrative_rotation, "compute_narrative_rotation",
                        lambda **kwargs: bundle.narrative_rotation)
    monkeypatch.setattr(sc, "_load_rotation_artifact", lambda: bundle.rotation_artifact)
    monkeypatch.setattr(sc, "_load_rotation_events", lambda: bundle.rotation_events)
    monkeypatch.setattr(sc, "_resolve_fusion_calibration",
                        lambda rec: bundle.fusion_calibrations[sc.fusion_calibration_key(rec)])
    real_compute = sc.compute_from_inputs
    captured = []
    def capture(inputs, *, evaluation_date):
        captured.append((inputs, evaluation_date))
        return real_compute(inputs, evaluation_date=evaluation_date)
    monkeypatch.setattr(sc, "compute_from_inputs", capture)
    out = sc.compute()
    selected, evaluation_date = captured[0]
    assert selected.membership_document == bundle.membership_document
    assert selected.fusion_calibrations == bundle.fusion_calibrations
    assert out == real_compute(bundle, evaluation_date=evaluation_date)
    assert "_crowd_by_ticker" in bundle.market_context
