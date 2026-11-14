"""Tests for the US Sector Central fuser (engine.sector_central) + its self-grader.

The fuser's load-bearing US-specific behaviors are tested deterministically with hand-built
cycle records: (1) the cycle-state score keys off the 0–100 oscillator (no `signature` field);
(2) the VALIDATED absolute-trend gate de-rates / caps a bullish read when a sector is below its
own trend (the genuine US drawdown lever — the opposite of China, where the gate failed);
(3) the per-sector macro-beta differentiation gates cyclicals harder than defensives in risk-off.
The public compute() is checked for fail-soft well-formedness, and the grader for a PIT roundtrip.
"""
from __future__ import annotations

from copy import deepcopy

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

def _strength_rows(values):
    return [{"id": str(i), "momentum": {"rs_63d": value}}
            for i, value in enumerate(values)]


def _strength(rows, peer_group="sectors"):
    sc._attach_strength(rows, peer_group=peer_group, as_of="2023-12-29")
    return {row["id"]: row["strength"] for row in rows}


def test_washout_setup_and_peer_strength_can_disagree_without_reweighting():
    recs = [_rec(ticker="XLF", pos=5, phase="Trough", rs_rank=3, rs_63d=-12),
            _rec(ticker="XLP", pos=50, phase="Expansion", signal=None, rs_rank=2, rs_63d=0),
            _rec(ticker="XLK", pos=95, phase="Peak", signal="SELL", rs_rank=1, rs_63d=12)]
    rows = [{"id": rec["id"], **sc._fuse(rec, _mkt(), 3, trend={"pass": True})}
            for rec in recs]
    before = deepcopy(rows)
    _strength(rows)
    assert rows[0]["conviction"]["score"] > rows[2]["conviction"]["score"]
    assert rows[0]["strength"]["band"] == "lagging"
    assert rows[2]["strength"]["band"] == "leading"
    assert [{k: v for k, v in row.items() if k != "strength"} for row in rows] == before


def test_strength_ignores_setup_fast_momentum_legacy_ranks_and_display_order():
    rows = _strength_rows([-5, -3, -1])
    expected = _strength(rows)
    for row in rows:
        row.update(conviction={"score": 99, "dir": "up"},
                   state={"pos": 1, "phase": "Recovery", "signal": "BUY"},
                   forward={"trend_pass": False}, heat={"heat_1M": 100},
                   crowding={"frac": 1}, rotation={"ordinal": 1})
        row["momentum"].update(rs_rank=1, rs_21d=100, rs_21d_rank=1, lead="leading")
    assert _strength(list(reversed(rows))) == expected
    # The strongest peer can still be down relative to SPY.
    assert expected["2"]["band"] == "leading" and expected["2"]["rs_63d"] == -1


@pytest.mark.parametrize("values,expected", [
    ([3, 2, 1, 0], ["leading", "leading", "lagging", "lagging"]),
    ([6, 5, 4, 3, 2, 1, 0], ["leading"] * 3 + ["mid-pack"] + ["lagging"] * 3),
    ([3, 2, 2, 0], ["leading", "mid-pack", "mid-pack", "lagging"]),
    ([7, 6, 6, 4, 3, 3, 1], ["leading"] * 3 + ["mid-pack"] + ["lagging"] * 3),
    ([0, 0, 0], ["mid-pack"] * 3),
])
def test_strength_thirds_keep_ties_and_exact_boundaries(values, expected):
    rows = _strength_rows(values)
    readings = _strength(rows)
    assert [row["strength"]["band"] for row in rows] == expected
    assert _strength(list(reversed(rows))) == readings


def test_strength_missing_values_do_not_vote_or_fall_back_to_fast_rs():
    invalid = [None, float("nan"), float("inf"), -float("inf"), True, np.bool_(False), "12", {}, 10**400]
    rows = _strength_rows([1, 0, -1] + invalid)
    for row in rows:
        row["momentum"].update(rs_rank=1, rs_21d=100, rs_21d_rank=1)
    _strength(rows)
    assert [row["strength"]["band"] for row in rows[:3]] == ["leading", "mid-pack", "lagging"]
    assert rows[1]["strength"]["rs_63d"] == 0
    for row in rows:
        assert row["strength"]["n_measured"] == 3
        assert row["strength"]["n_peers"] == len(rows)
    for row in rows[3:]:
        assert row["strength"]["band"] == "unavailable"
        assert row["strength"]["rs_63d"] is None
        assert row["strength"]["reason"] == "missing_rs63"


@pytest.mark.parametrize("values", [[], [0], [-1, 1]])
def test_strength_requires_three_measured_peers_without_hiding_valid_rs(values):
    rows = _strength_rows(values)
    _strength(rows)
    for row, value in zip(rows, values):
        assert row["strength"]["band"] == "unavailable"
        assert row["strength"]["reason"] == "insufficient_peers"
        assert row["strength"]["rs_63d"] == value


def test_compute_attaches_separate_peer_boards_without_changing_legacy_output(monkeypatch, tmp_path):
    from engine import inputs, narrative_rotation, sector_cycles

    cyc = {"meta": {"asOf": "2023-12-29"},
           "sectors": [_rec(ticker=t, rs_63d=v) for t, v in zip(("XLK", "XLF", "XLP"), (-3, -2, -1))],
           "baskets": [_rec(ticker=t, rs_63d=v, kind="basket")
                       for t, v in zip(("A", "B", "C"), (100, 200, 300))]}
    monkeypatch.setattr(sector_cycles, "compute", lambda: deepcopy(cyc))
    monkeypatch.setattr(inputs, "yahoo_closes", lambda: None)
    monkeypatch.setattr(narrative_rotation, "compute_narrative_rotation", lambda **kw: None)
    monkeypatch.setattr(sc, "market_context", _mkt)
    monkeypatch.setattr(sc, "_trend_gates", lambda *args: {})
    monkeypatch.setattr(sc, "_load_rotation_artifact", lambda: {})
    monkeypatch.setattr(sc, "_measured_read", lambda data: None)
    monkeypatch.setattr(sc.config, "data_dir", lambda: tmp_path)
    out = sc.compute()
    assert out is not None
    for key in ("sectors", "baskets"):
        rows = out[key]
        assert {row["strength"]["band"] for row in rows} == {"leading", "mid-pack", "lagging"}
        assert all(row["strength"]["peer_group"] == key for row in rows)
        assert all(row["strength"]["n_measured"] == 3 for row in rows)
        assert all(row["strength"]["as_of"] is None for row in rows)
        assert all(row["strength"]["board_as_of"] == "2023-12-29" for row in rows)
        assert all(row["strength"]["horizon_sessions"] is None for row in rows)
        assert all(row["strength"]["window_status"] == "unqualified" for row in rows)
        for row in rows:
            row.pop("strength")
    monkeypatch.setattr(sc, "_attach_strength", lambda *args, **kwargs: None)
    assert out == sc.compute()  # existing scores, fields, ordering and metadata are identical


def test_split_copy_does_not_infer_strength_or_extension_from_setup():
    for label in ("Accumulate", "Constructive"):
        text = sc._SPLIT_COPY_EN["slower"].format(conv=sc._CONV_PLAIN_EN[label])
        assert "setup" in text
        assert "extended" not in text and "after the run" not in text
        assert "强势" not in sc._CONV_PLAIN_ZH[label]


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


def test_compute_block_publishes_the_status_beside_the_board_order():
    # Slice compute(): the status must be derived from the same armed flag as the order.
    assert 'mkt["fast_lens"] = _fast_lens_status(rotation_armed, rotation_raw)' in (
        _ROOT / "engine" / "sector_central.py").read_text(encoding="utf-8")


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


def test_note_says_setup_and_names_the_date_when_stale():
    en, zh = _note({"state": "stale", "asof": "2026-10-16"})
    assert en.startswith("Cards are ordered by setup score.") and "2026-10-16" in en
    assert zh.startswith("卡片按形态条件评分排序。") and "2026-10-16" in zh
    assert "ordered by the fast rotation lens" not in en
    assert "按快速轮动视角排序" not in zh


@pytest.mark.parametrize("fast_lens", [{"state": "absent", "asof": None}, {}, None])
def test_note_says_setup_with_no_date_when_nothing_was_published(fast_lens):
    en, zh = _note(fast_lens)
    assert en.startswith("Cards are ordered by setup score.") and "not published" in en
    assert zh.startswith("卡片按形态条件评分排序。") and "尚未发布" in zh
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


def _render_central_card(row, language="en"):
    """Run the actual renderer used by both the sector board and basket expansions."""
    scripts = _re.findall(r"<script[^>]*>(.*?)</script>", _TEMPLATE, _re.S)
    script = next(src for src in scripts if "function card(s)" in src and "window.__siTrace" in src)
    payload = {"sectors": [row] if row["kind"] == "sector" else [],
               "baskets": [row] if row["kind"] == "basket" else []}
    src = ("var window={SECTOR_CENTRAL:" + _json.dumps(payload) + "};"
           "var document={readyState:'loading',addEventListener:function(){},getElementById:function(){return null;},"
           "documentElement:{getAttribute:function(){return " + _json.dumps(language) + ";}}};"
           + script + "process.stdout.write(window.__siTrace(" + _json.dumps(row["id"]) + "));")
    res = _subprocess.run(["node", "-e", src], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    return res.stdout


@_needs_node
@pytest.mark.parametrize("kind", ["sector", "basket"])
@pytest.mark.parametrize("language", ["en", "zh"])
def test_card_displays_strength_beside_setup_in_both_consumers(kind, language):
    row = {"id": "sample", "name": "Sample", "name_zh": "示例", "kind": kind,
           "conviction": {"score": 80, "label_en": "Accumulate", "label_zh": "积极配置", "dir": "up"},
           "cycle": {"phase": "Recovery", "rs_rank": 11, "rs_21d_rank": 1},
           "strength": {"band": "lagging", "rs_63d": -12, "n_measured": 11,
                        "n_peers": 11, "peer_group": "baskets" if kind == "basket" else "sectors"}}
    html = _render_central_card(row, language)
    assert ("示例" if language == "zh" else "Sample") in html
    for text in ("Setup", "形态条件", "Lagging peers", "同组落后", "-12.0%", "vs SPY", "Observed strength"):
        assert text in html
    strength = _re.search(r'<div class="strength-read".*?</div>', html, _re.S).group(0)
    visible = _re.sub(r'<[^>]+>', '', strength)
    assert "Window/end date unverified" in visible
    assert "窗口/截至日期未核实" in visible
    assert "may differ or be stale" in strength and "可能不同或陈旧" in strength
    assert "63 sessions" not in strength and "63-session" not in strength
    assert "63个交易日" not in strength
    assert 'class="conv-score">80<' in html
    assert "63d RS rank" not in html
    assert 'class="strength-read"' in html


@_needs_node
def test_card_unknown_strength_never_falls_back_to_conviction_or_fast_rank():
    row = {"id": "sample", "name": "Sample", "kind": "sector",
           "conviction": {"score": 99, "label_en": "Accumulate", "dir": "up"},
           "cycle": {"rs_rank": 1, "rs_21d_rank": 1}, "momentum": {"rs_21d": 100}}
    html = _render_central_card(row)
    assert "Unavailable" in html and "暂无比较" in html
    assert "Leading peers" not in html and 'class="strength-rs"' not in html
    assert "0 measured" not in html
    row["strength"] = {"band": "leading", "rs_63d": -1, "n_measured": 3, "n_peers": 3}
    html = _render_central_card(row)
    assert "Leading peers" in html and "-1.0%" in html


@pytest.mark.parametrize("board_date", [None, "2023-12-29", "2026-11-14"])
def test_strength_board_clock_cannot_qualify_an_unknown_observation_window(board_date):
    rows = _strength_rows([-3, -2, -1])
    before = deepcopy(rows)
    sc._attach_strength(rows, peer_group="sectors", as_of=board_date)
    for row, original in zip(rows, before):
        reading = row["strength"]
        assert reading["board_as_of"] == board_date
        assert reading["as_of"] is None and reading["horizon_sessions"] is None
        assert reading["window_status"] == "unqualified"
        assert reading["rs_63d"] == original["momentum"]["rs_63d"]
        assert {k: v for k, v in row.items() if k != "strength"} == original


@_needs_node
def test_old_strength_payload_cannot_make_an_unverified_window_current():
    row = {"id": "sample", "name": "Sample", "kind": "sector",
           "conviction": {"score": 80, "label_en": "Accumulate", "dir": "up"},
           "strength": {"band": "leading", "rs_63d": -1, "n_measured": 3,
                        "n_peers": 3, "horizon_sessions": 63, "as_of": "2026-11-14"}}
    html = _render_central_card(row)
    strength = _re.search(r'<div class="strength-read".*?</div>', html, _re.S).group(0)
    visible = _re.sub(r'<[^>]+>', '', strength)
    assert "Window/end date unverified" in visible and "窗口/截至日期未核实" in visible
    assert "2026-11-14" not in strength
    assert "63-session" not in strength and "63 sessions" not in strength
