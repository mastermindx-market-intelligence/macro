"""B04 contract test — the frozen metric definitions ARE the formulas.

Synthetic-input pins for every `measured` metric whose computation is isolatable
(windows in sessions, relative-wealth vs percentage-point difference, price/TR basis
via the labelled rs_history meta), plus source-formula pins (exact-line regex) for the
metrics computed inline or behind a site/ file read — the doc marks which is which.

SIC-D-B04 r3 (RB04 repair) added pins: the no-basis TR closes load in compute(), the
exact `dir_hit_rate` / `mean_excess_vs_bench` source expressions, the Neutral clause
of the `_DIR_HIT_RATE_DEFINITION` literal, and a citation auditor that opens every
cited file and asserts the cited line range still contains a token the doc row names.

No network, no data/ reads, no site/ reads.
Run: python3 -m pytest -q -p no:cacheprovider tests/test_sector_metric_definitions.py
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import sector_cycles as sc
from engine.grading import grade_next_bar_return
from engine.narrative_rotation import _abs_gate
from engine.sector_central_grader import _HORIZONS_D

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "research" / "sector_completion_20261021" / "B04_METRIC_DEFINITIONS.md"


# ── synthetic panels ──────────────────────────────────────────────────────────
def _panel(n: int = 300):
    """XLK/SPY close panel with hand-computable 21/63/126-session RS endpoints.

    bench steps 100→102 at n-63; ticker steps 100→105 at n-63 and 105→115.5 at n-21,
    so over the last 63 sessions the ticker returns +15.5% raw while SPY returns +2.0%.
    ratio−1 reads (115.5/102)−1 = 13.235…% → 13.2; the pp-difference would be 13.5.
    """
    idx = pd.bdate_range("2024-01-02", periods=n)
    tk = np.full(n, 100.0)
    tk[n - 63:n - 21] = 105.0
    tk[n - 21:] = 115.5
    bench = np.full(n, 100.0)
    bench[n - 63:] = 102.0
    return pd.DataFrame({"XLK": tk, "SPY": bench}, index=idx)


def test_rs_windows_are_sessions_and_ratio_not_pp():
    lead = sc._leadership(_panel(), "XLK")
    # 21-session endpoint: (115.5/102) / (105/102) − 1 = 115.5/105 − 1 = +10.0%
    assert lead["rs_21d"] == pytest.approx(10.0, abs=1e-9)
    # 63-session endpoint: (115.5/102)/(100/100) − 1 = +13.235…% → rounds to 13.2
    assert lead["rs_63d"] == pytest.approx(13.2, abs=1e-9)
    # 126-session endpoint: same base segment → 13.2 as well
    assert lead["rs_126d"] == pytest.approx(13.2, abs=1e-9)
    # relative wealth, NOT percentage-point difference: 15.5 − 2.0 = 13.5 would be pp
    assert lead["rs_63d"] != pytest.approx(13.5)
    assert lead["thin_history"] is False
    assert lead["rs_above_trend"] is True  # 1.1324 vs a ~1.02 200-session RS mean


def test_rs_min_rows_fence():
    short = _panel(150)  # < _RS_MIN_ROWS (210)
    lead = sc._leadership(short, "XLK")
    assert lead.get("thin_history") is True


def test_rs_history_trail_is_reconstruction_of_the_same_formula():
    panel = _panel()
    rows, excluded = sc._leadership_history_counted(panel, "XLK")
    assert 0 < len(rows) <= sc.RS_HISTORY_MAX_POINTS == 252
    lead_now = sc._leadership(panel, "XLK")
    assert rows[-1]["date"] == panel.index[-1].date().isoformat()
    assert rows[-1]["rs_21d"] == lead_now["rs_21d"]
    assert rows[-1]["rs_63d"] == lead_now["rs_63d"]
    # as-of cut: the Time-Machine-style read ends on the requested session
    asof = panel.index[n_cut := len(panel) - 22]
    rows_asof, _ = sc._leadership_history_counted(panel, "XLK", asof=asof)
    assert rows_asof[-1]["date"] == asof.date().isoformat()
    # a panel shorter than the 210-row eligibility fence yields no trail at all
    assert sc._leadership_history_counted(_panel(150), "XLK")[0] == []


def test_rs_rank_stamping_is_cross_sectional_desc():
    recs = [
        {"now": {"rs_63d": 5.0, "rs_21d": 1.0}},
        {"now": {"rs_63d": -1.0, "rs_21d": 2.0}},
        {"now": {"rs_63d": 2.0, "rs_21d": 3.0}},
    ]
    sc._stamp_rs_ranks(recs)
    assert [r["now"]["rs_rank"] for r in recs] == [1, 3, 2]      # by rs_63d, desc
    assert [r["now"]["rs_21d_rank"] for r in recs] == [3, 2, 1]  # independent lens


def test_abs_gate_ret_12m_is_252_session_ratio():
    idx = pd.bdate_range("2023-01-02", periods=300)
    rising = pd.Series(np.concatenate([np.full(48, 100.0), np.linspace(100.0, 200.0, 252)]),
                       index=idx)
    ok, g = _abs_gate(rising)
    assert ok is True
    assert g["ret_12m"] == pytest.approx(1.0)      # s[-1]/s[-253] − 1 = 200/100 − 1
    assert g["pos_12m"] is True and g["above_200dma"] is True
    flat_top = pd.Series(np.concatenate([np.full(48, 100.0), np.full(252, 126.0)]), index=idx)
    ok2, g2 = _abs_gate(flat_top)
    assert ok2 is False                            # ret positive but sitting on the MA
    assert g2["ret_12m"] == pytest.approx(0.26)    # 126/100 − 1
    assert g2["above_200dma"] is False and g2["pos_12m"] is True


def test_abs_gate_ret_12m_is_none_below_253_rows_and_pos_12m_is_guarded():
    # RB04 MINOR: ret_12m needs >= 253 non-null rows else None; pos_12m is
    # None-guarded (False, never None and never an error).
    idx = pd.bdate_range("2023-01-02", periods=252)
    rising_short = pd.Series(np.linspace(100.0, 200.0, 252), index=idx)
    ok, g = _abs_gate(rising_short)
    assert g["ret_12m"] is None                    # 252 rows < n + skip + 1 = 253
    assert g["pos_12m"] is False                   # guarded read of a None ret_12m
    assert g["ret_12m"] != pytest.approx(1.0)      # no accidental ratio off a short tape
    # with NaN holes the count is of NON-NULL rows only
    holed = rising_short.copy()
    holed.iloc[:5] = np.nan
    ok_h, g_h = _abs_gate(holed)
    assert g_h["ret_12m"] is None                  # 247 usable rows, still short


def test_grade_next_bar_return_is_next_bar_and_h_bars():
    n = 60
    close = pd.Series(np.arange(101.0, 101.0 + n), index=pd.bdate_range("2024-01-02", periods=n))
    d0 = str(close.index[5].date())                # signal on bar 5 (close 106.0)
    # ENTRY = next bar (index 6, close 107.0); fwd_ret_21 = close[27]/close[6] − 1 = 128/107 − 1
    assert grade_next_bar_return(close, d0, 21) == pytest.approx(21.0 / 107.0)
    assert grade_next_bar_return(close, d0, 1000) is None  # frozen until matured


# ── source-formula pins (exact-line, for computations not isolatable here) ────
def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_grader_horizons_are_21_63_126_trading_bars():
    assert _HORIZONS_D == (21, 63, 126)


def test_rs_meta_pins_basis_benchmark_and_reconstruction_label():
    src = _src("engine/sector_cycles.py")
    for literal in (
        '"horizons_sessions": [21, 63]',
        '"mode": "reconstructed_price_history"',
        '"naturally_observed": False',
        '"basis": "tr"',
        "RS_BENCH_FFILL_LIMIT = 5",
        "_RS_MIN_ROWS = 210",
        "RS_HISTORY_MAX_POINTS = 252",
    ):
        assert literal in src, f"rs contract literal drifted: {literal!r}"
    # the shared ratio formula and the limit-free basket variant (B01 F4)
    assert "ratio = t / b.reindex(t.index).ffill(limit=RS_BENCH_FFILL_LIMIT)" in src
    assert 'rs = (full / spy.reindex(full.index).ffill()).dropna()' in src
    # SIC-D-B04 r3 pin (a): compute() loads the RS/momentum panel with NO basis
    # argument — the yahoo_closes default basis="tr" (engine/inputs.py) IS the TR
    # pin, not just the meta literal. Exactly one such load, and the structural
    # sibling names its basis, so a flipped default cannot hide.
    lines = src.splitlines()
    no_basis = [i for i, l in enumerate(lines) if l.strip() == "closes = yahoo_closes()"]
    assert len(no_basis) == 1, "compute() no-basis closes load moved or multiplied"
    assert any('yahoo_closes(basis="price")' in l for l in lines), \
        "price-basis sibling load drifted (TR/price split no longer adjacent)"


def test_heat_and_breadth_formula_pins():
    src = _src("engine/sector_central.py")
    assert 'cap_weighted = (hm.get("size_basis") != "weight_proxy")' in src
    assert 'for tf in ("1D", "1M", "YTD")' in src
    assert 'row["heat_" + tf] = round(a["vals"][tf] / w, 2) if w else None' in src
    # SIC-D-B03: breadth is None (not 0) when no tile moved — honest null, no max(…, 1) floor
    assert 'row["breadth_pct"] = round(100.0 * adv / (adv + dec), 0) if (adv + dec) else None' in src
    # post-base coverage fields the census now documents
    assert 'row["n_tiles"] = a["n_tiles"]' in src
    assert 'row["n_priced_1M"] = a["n_priced_1M"]' in src
    assert 'row["n_unchanged_1M"] = a["n_unchanged_1M"]' in src
    assert 'row["weight_coverage_1M"] = round(a["w_1m"] / a["w"], 4) if a["w"] else None' in src
    assert 'row["breadth_basis"] = "adv_over_adv_plus_dec_excl_unchanged"' in src


def test_grader_scorecard_formula_pins():
    src = _src("engine/sector_central_grader.py")
    assert '"excess": (fr - br) if br is not None else None' in src   # pp-diff, not ratio
    assert '((up["fwd"] > 0).sum() + (dn["fwd"] < 0).sum()) / len(g)' in src
    assert 'subset=["date", "id"], keep="first"' in src               # keep-first ledger
    # SIC-D-B04 r3 pin (b): the exact publish expressions, not existence-only
    # 'the key exists somewhere in the file' checks that let the doc drift.
    assert '"dir_hit_rate": round(hit, 3) if hit is not None else None' in src
    assert ('"mean_excess_vs_bench": (round(float(g["excess"].dropna().mean()), 4)'
            in src)
    assert '"rank_ic": round(float(np.mean(ics)), 4) if ics else None' in src
    # SIC-D-B04 r3 pin (c): the artifact ships its own definition literal — pin the
    # Neutral clause so the wording cannot silently drop the denominator contract.
    assert ("correct up + correct down calls / all graded rows including Neutral"
            in src), "_DIR_HIT_RATE_DEFINITION lost its Neutral clause"
    assert "not a conditional hit rate, not a win rate" in src
    # the conditional counterpart the doc points at
    assert '"conditional_directional_hit_rate": rate' in src


def test_conviction_and_trend_gate_formula_pins():
    central = _src("engine/sector_central.py")
    assert "raw = float(np.clip(gated + 0.5 * mom, -1, 1))" in central
    assert "score = round((raw + 1.0) / 2.0 * 100)" in central
    narr = _src("engine/narrative_rotation.py")
    assert "SMA_TREND_D = 200" in narr
    assert "_cum_ret(s, 252, skip=0)" in narr
    assert "v = s.iloc[-1 - skip] / base - 1.0" in narr
    assert "if len(s) < n + skip + 1:" in narr        # RB04 MINOR: the 253-row guard
    assert "pos12 = bool(r12 is not None and r12 > 0)" in narr  # None-guarded pos_12m


def test_post_base_writer_pins():
    """SIC-D-B04 r3: the post-base fields the new doc section documents exist in
    the tree exactly where the doc cites them."""
    cycles = _src("engine/sector_cycles.py")
    for literal in (
        'nw["phase_v2_age_bars"] = (age.get("sessions")',
        '"rhythm_version": 1',
        '"correction_contract": {',
        'rec["rhythm"] = rhythm',
        'rec["estimate_kinds"] = estimate_kinds(rec.get("now") or {}, rhythm)',
        'nw["hazard"] = hz',
    ):
        assert literal in cycles, f"post-base cycles writer drifted: {literal!r}"
    rhythm = _src("engine/cycle_rhythm.py")
    assert 'ESTIMATE_KINDS_SCHEMA = "sector_cycles.estimate_kinds.v1"' in rhythm
    assert "live_feature_parity" in rhythm
    phase_age = _src("engine/cycle_phase_age.py")
    assert 'PHASE_AGE_METHOD = "forward_log_replay.v2"' in phase_age
    assert '"measured"' in phase_age and '"lower_bound"' in phase_age
    hazard = _src("engine/hazard_score.py")
    assert '"source": "MODEL", "cell_verdict": "PASS"' in hazard
    assert '"source": "PRIOR", "cell_verdict": "PRIOR"' in hazard


# ── the doc and the pins agree ─────────────────────────────────────────────────
PINNED_FIELDS = (
    "rs_21d", "rs_63d", "rs_126d", "rs_above_trend", "rs_rank", "rs_21d_rank",
    "rs_history", "ret_12m", "pos_12m", "above_200dma", "fwd",
    "excess", "dir_hit_rate", "breadth_pct", "heat_1D", "heat_1M", "heat_YTD",
    "adv", "dec", "score", "pos_rate", "mean_fwd", "mean_excess", "rank_ic",
    "n_above_trend",
    # SIC-D-B04 r3: fields published after base 3d8d14ac (RB04 MAJOR-2)
    "phase_v2_age_bars", "phase_v2_age_sessions", "phase_v2_age_status",
    "rhythm_version", "correction_contract", "estimate_kinds",
    "live_feature_parity", "n_tiles", "n_priced_1M", "n_unchanged_1M",
    "weight_coverage_1M", "breadth_basis", "conditional_directional_hit_rate",
    "dir_hit_rate_definition", "grader_schema_version", "n_directional",
    "n_neutral", "n_correct_directional", "directional_coverage",
    "conditional_hit_rate_se", "neutral_outcomes", "rank_ic_distribution",
    "excess_distribution", "by_cohort_month",
)


def test_b04_doc_rows_are_wellformed_and_cover_the_pinned_fields():
    text = DOC.read_text(encoding="utf-8")
    assert text.startswith("# B04"), "doc header drifted"
    assert "unmeasured" in text and "**measured**" in text
    status_cells = re.findall(r"\|\s*(\*\*measured\*\*|\*\*unmeasured\*\*|\*\*descriptive\*\*|\*\*disclosure\*\*)[^|]*\|", text)
    assert len(status_cells) >= 20, "metric table shrank"
    for f in PINNED_FIELDS:
        assert f in text, f"B04 doc lost pinned field {f!r}"
    # every data row (field cell starts with a backtick) cites at least one file:line
    data_rows = re.findall(r"^\| `[^|]*\|.*\|$", text, re.M)
    assert len(data_rows) >= 20
    for row in data_rows:
        assert re.search(r"\.(?:py|js):\d+", row), f"row without a file:line citation: {row[:80]}"
    # the 20-interval row is recorded as absent, not invented
    assert "does not exist on these two artifacts" in text
    # the post-base section exists and is a table, not prose
    assert "## Fields published after base 3d8d14ac" in text


# ── SIC-D-B04 r3 pin (d): the citation auditor ─────────────────────────────────
_CITE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|js)):(\d+)(?:-(\d+))?`")
_CITE_BODY = re.compile(r"[A-Za-z0-9_./-]+\.(?:py|js):\d+(?:-\d+)?")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{3,}")
# tokens too generic to prove a citation still points at its formula — a cite that
# only matches through one of these has already drifted
_GENERIC = {
    "round", "float", "int", "bool", "str", "None", "True", "False", "dict",
    "list", "tuple", "data", "self", "return", "sorted", "sort", "value",
}


def _doc_data_rows() -> list[str]:
    text = DOC.read_text(encoding="utf-8")
    return re.findall(r"^\| `[^|]*\|.*\|$", text, re.M)


def _row_tokens(row: str) -> set[str]:
    """Named tokens of a doc row: every backticked span except the citations
    themselves (spans shorter than 4 chars are too weak as substring proofs),
    plus the identifiers inside those spans, minus a generic-word stoplist."""
    tokens: set[str] = set()
    for span in re.findall(r"`([^`]+)`", row):
        if _CITE_BODY.fullmatch(span):
            continue
        if len(span) >= 4 and span not in _GENERIC:
            tokens.add(span)
        tokens.update(t for t in _IDENT.findall(span) if t not in _GENERIC)
    return tokens


def _cited_segment(rel: str, start: int, end: int) -> str:
    lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
    assert 1 <= start <= end <= len(lines), \
        f"{rel}:{start}-{end} points outside the file ({len(lines)} lines)"
    return "\n".join(lines[start - 1:end])


def test_b04_doc_citations_resolve_to_lines_that_name_the_row():
    """Every `file.py:NNN[-MMM]` citation in every data row is opened and the
    cited line range must still contain a token the same row names — so a moved
    formula or a stale line number fails CI instead of shipping drift."""
    rows = _doc_data_rows()
    cited = 0
    for row in rows:
        tokens = _row_tokens(row)
        assert tokens, f"row names no backticked token: {row[:80]}"
        for rel, start, end in _CITE.findall(row):
            cited += 1
            seg = _cited_segment(rel, int(start), int(end or start))
            hits = [t for t in tokens if t in seg]
            assert hits, (
                f"citation `{rel}:{start}-{end or start}` no longer contains any "
                f"token the row names (row starts: {row[:60]}…)"
            )
    assert cited >= 60, f"citation auditor only saw {cited} citations — parser drift?"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
