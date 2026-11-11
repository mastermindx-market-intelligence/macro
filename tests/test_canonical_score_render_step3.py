"""STEP-3 canonical-score-render regression tests (2026-11-09 divergence).

Incident being pinned: on 2026-11-09 the published score diverged three ways —
canonical data/market_state/latest.json said 41 (weighted 40.82 -> 41,
score_source=blend, capped=false) while the generated macro.html baked 39 (a
stale-input recompute rendered instead of the canonical artifact), and
/live/risk_state.json still served 36 from 2026-11-06 marked stale. The nightly
forward-ledger finalization was incomplete, so 41 was canonical but
unreconciled and the page said nothing about that either.

The repair under test (scripts/build_site.py, three changes):
1. CANONICAL RENDER — vm["market_state"] (score, components) and the
   ms_history chart endpoint are rendered from the single canonical
   data/market_state/latest.json via build_site._canonical_market_state();
   a missing/unparseable artifact raises instead of degrading.
2. SETTLE-BLOCK — the canonical view carries an explicit settlement flag:
   'settled' only when the forward ledger's graded evidence is at least as
   new as the snapshot and every graded row has a graded_at stamp;
   otherwise 'unreconciled' (the honest 2026-11-09 state).
3. PRODUCTION PARITY (this file) — a build from the canonical latest.json
   must display EXACTLY the canonical score + components in the rendered
   macro.html. Render conventions mirror tests/test_dashboard_template_render
   (_base_vm + _env + dashboard.html.j2 mode="macro"), the same path
   scripts/build_site.py drives; the HTML is parsed back out (id="ms-score",
   data-measured-score, the Six Factors dialog rows, the chart's endpoint
   date tick) so the assertion is on what the public page actually shows.
"""
from __future__ import annotations

import json
import re

import pytest

from scripts import build_site
from tests.test_dashboard_template_render import _base_vm, _env

# Distinctive fixture numbers: neither 41 nor 39 nor 36 — any accidental
# agreement with a real artifact or a recomputed value fails the parity test.
_SCORE = 37
_RAW = 37
_ASOF = "2026-11-10"

_COMPONENTS = [
    {"key": "trend", "label_en": "Trend & technicals", "label_zh": "趋势与技术",
     "score": 21, "weight": 0.24, "tone": "bad", "arrow": "▼",
     "read_en": "0/3 indices in an uptrend.", "read_zh": "0/3 个指数上升趋势。",
     "metrics": [], "degraded": False},
    {"key": "risk", "label_en": "Cross-asset risk", "label_zh": "跨资产风险",
     "score": 44, "weight": 0.18, "tone": "warn", "arrow": "▼",
     "read_en": "Credit wide.", "read_zh": "信用利差走阔。",
     "metrics": [], "degraded": False},
    {"key": "vol", "label_en": "Volatility", "label_zh": "波动率",
     "score": 12, "weight": 0.16, "tone": "bad", "arrow": "▼",
     "read_en": "VIX elevated.", "read_zh": "VIX 偏高。",
     "metrics": [], "degraded": False},
    {"key": "breadth", "label_en": "Breadth", "label_zh": "广度",
     "score": 58, "weight": 0.16, "tone": "good", "arrow": "▲",
     "read_en": "Breadth firm.", "read_zh": "广度稳固。",
     "metrics": [], "degraded": False},
    {"key": "liquidity", "label_en": "Liquidity", "label_zh": "流动性",
     "score": 33, "weight": 0.14, "tone": "warn", "arrow": "▼",
     "read_en": "Tightening.", "read_zh": "收紧。",
     "metrics": [], "degraded": False},
    {"key": "stress", "label_en": "Stress", "label_zh": "压力",
     "score": 75, "weight": 0.12, "tone": "bad", "arrow": "▼",
     "read_en": "Stress high.", "read_zh": "压力偏高。",
     "metrics": [], "degraded": False},
]


def _canonical_snapshot() -> dict:
    """Synthetic canonical latest.json — same shape engine.market_state.persist
    writes (data/market_state/latest.json), with fixture-distinctive numbers."""
    return {
        "schema": "market_state.v1",
        "asof": _ASOF,
        "score": _SCORE,
        "raw_score": _RAW,
        "score_source": "blend",
        "capped": False,
        "score_ceiling": None,
        "score_caps": [],
        "score_gap": None,
        "radar": None,
        "verdict": "RISK_OFF",
        "color": "red",
        "label_en": "Risk-off",
        "label_zh": "避险",
        "posture_en": "Risk-off",
        "posture_zh": "避险",
        "headline_en": "Risk-off — defend capital first.",
        "headline_zh": "避险 —— 先保住资本。",
        "participation_scope": None,
        "components": [dict(c) for c in _COMPONENTS],
        "mtf": None,
        "overrides": [],
        "flip_en": None,
        "flip_zh": None,
        "alerts_count": 0,
        "market": "us",
        "caveat_en": "",
        "caveat_zh": "",
        "is_display_only": True,
    }


def _ledger_row(asof: str, score: int, graded: dict | None = None, **extra) -> dict:
    row = {"asof": asof, "score": score, "raw_score": score,
           "verdict": "RISK_OFF", "logged_at": f"{asof}T23:00:00+00:00", "graded": graded}
    row.update(extra)
    return row


def _graded(asof: str, score: int, graded_at: str = "2026-11-08T10:00:00+00:00") -> dict:
    return _ledger_row(asof, score, graded={
        "base_px": 500.0, "fwd_dd": {"h5": -0.01, "h10": -0.02, "h21": -0.03},
        "any_dd5_within_h21": False, "outcome": "quiet", "graded_at": graded_at,
    })


def _write_canonical(data_dir, snap, ledger_rows=None) -> None:
    ms_dir = data_dir / "market_state"
    ms_dir.mkdir(parents=True, exist_ok=True)
    (ms_dir / "latest.json").write_text(
        json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    if ledger_rows is not None:
        (ms_dir / "forward_log.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in ledger_rows), encoding="utf-8")


# ── Change 3: production parity — the page displays the canonical artifact ──

def test_macro_html_displays_exactly_the_canonical_latest_json(tmp_path, monkeypatch):
    """A build from canonical latest.json reproduces, in the rendered
    macro.html, exactly the canonical score, raw score, as-of and every
    component score — the 41-vs-39 divergence cannot recur silently."""
    data_dir = tmp_path / "data"
    # Ledger graded through 2026-11-05, snapshot is 2026-11-10: evidence lags.
    _write_canonical(
        data_dir, _canonical_snapshot(),
        ledger_rows=[_graded("2026-11-05", 55), _ledger_row("2026-11-08", 41)])
    monkeypatch.setattr(build_site.config, "data_dir", lambda: data_dir)

    # The exact call the build makes for vm["market_state"] (STEP-3 change 1).
    ms = build_site._canonical_market_state()
    assert ms["score"] == _SCORE
    assert ms["raw_score"] == _RAW
    assert ms["settlement"]["status"] == "unreconciled"   # change 2 rides along

    vm = _base_vm()
    vm["market_state"] = ms                                  # the build's wiring
    vm["ms_history"] = build_site._ms_history_view(ms)       # chart endpoint
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="macro")

    # Score numeral + measured/raw attribute (id="ms-score" anchor).
    m = re.search(
        r'id="ms-score" data-measured-score="(\d+)">\s*(\d+)\s*<', html)
    assert m, "ms-score anchor missing from rendered macro.html"
    assert int(m.group(1)) == ms["raw_score"], "displayed raw score drifted from canonical"
    assert int(m.group(2)) == ms["score"], "displayed score drifted from canonical"

    # Hidden as-of stamp must be the canonical snapshot's as-of.
    m = re.search(r'id="ms-date"[^>]*>\s*(\d{4}-\d{2}-\d{2})\s*<', html)
    assert m and m.group(1) == ms["asof"], "displayed as-of drifted from canonical"

    # Six Factors dialog: every component row shows the canonical label + score.
    rows = re.findall(
        r'class="mx5-dlg-factor-name">\s*<span class="l-en">([^<]+?)</span>'
        r'.*?class="mx5-dlg-factor-score"[^>]*>\s*(\d+)\s*</div>',
        html, re.DOTALL)
    displayed = {label.strip(): int(score) for label, score in rows}
    canonical = {c["label_en"]: c["score"] for c in ms["components"]}
    assert len(rows) == len(canonical), (
        f"component row count {len(rows)} != canonical {len(canonical)}")
    assert displayed == canonical, (
        f"displayed components {displayed} != canonical {canonical}")

    # Chart data: the history path the page renders ends on the canonical
    # (asof, raw_score) endpoint, and the chart's last x-tick is the canonical
    # as-of date — never an older ledger tail or a recomputed score.
    hist = vm["ms_history"]
    assert hist and hist[-1] == {"asof": ms["asof"], "score": ms["raw_score"]}, (
        f"chart endpoint {hist[-1] if hist else None} != canonical")
    ticks = re.findall(
        r'class="mx5-pl-x"[^>]*>\s*<span class="l-en">([A-Za-z]{3} \d{1,2})</span>',
        html)
    assert ticks, "chart date ticks missing from rendered macro.html"
    assert ticks[-1] == "Nov 10", f"last chart tick {ticks[-1]!r} != canonical as-of"


# ── Change 1: canonical render fails loudly, never falls back silently ──

def test_missing_canonical_artifact_fails_the_build_loudly(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    monkeypatch.setattr(build_site.config, "data_dir", lambda: data_dir)
    with pytest.raises(RuntimeError, match="canonical market state artifact missing"):
        build_site._canonical_market_state()


def test_unparseable_canonical_artifact_fails_the_build_loudly(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    ms_dir = data_dir / "market_state"
    ms_dir.mkdir(parents=True)
    (ms_dir / "latest.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(build_site.config, "data_dir", lambda: data_dir)
    with pytest.raises(RuntimeError, match="unparseable"):
        build_site._canonical_market_state()


def test_canonical_artifact_without_score_fails_the_build_loudly(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    snap = _canonical_snapshot()
    del snap["score"]
    _write_canonical(data_dir, snap)
    monkeypatch.setattr(build_site.config, "data_dir", lambda: data_dir)
    with pytest.raises(RuntimeError, match="incomplete"):
        build_site._canonical_market_state()


# ── Change 2: settle-block — 'settled' only when evidence covers the snapshot ──

def test_settle_block_marks_snapshot_newer_than_settlement_unreconciled(tmp_path, monkeypatch):
    """The 2026-11-09 state: canonical score current, forward-ledger grading
    lags behind it — the page must publish 'unreconciled', never 'settled'."""
    data_dir = tmp_path / "data"
    _write_canonical(data_dir, _canonical_snapshot(),
                     ledger_rows=[_graded("2026-11-05", 55)])
    monkeypatch.setattr(build_site.config, "data_dir", lambda: data_dir)
    ms = build_site._canonical_market_state()
    assert ms["settlement"] == {
        "status": "unreconciled",
        "snapshot_asof": "2026-11-10",
        "newest_settled_asof": "2026-11-05",
        "n_graded": 1,
    }


def test_settle_block_absent_settlement_timestamp_is_unreconciled(tmp_path, monkeypatch):
    """A graded row missing its graded_at stamp is a settlement-timestamp gap —
    evidence does not vouch, so the flag must be 'unreconciled'."""
    data_dir = tmp_path / "data"
    unstamped = _graded("2026-11-12", 50)
    unstamped["graded"]["graded_at"] = None
    _write_canonical(data_dir, _canonical_snapshot(), ledger_rows=[unstamped])
    monkeypatch.setattr(build_site.config, "data_dir", lambda: data_dir)
    ms = build_site._canonical_market_state()
    assert ms["settlement"]["status"] == "unreconciled"


def test_settle_block_absent_ledger_is_unreconciled(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    _write_canonical(data_dir, _canonical_snapshot())   # no forward_log at all
    monkeypatch.setattr(build_site.config, "data_dir", lambda: data_dir)
    ms = build_site._canonical_market_state()
    assert ms["settlement"]["status"] == "unreconciled"
    assert ms["settlement"]["n_graded"] == 0


def test_settle_block_current_graded_evidence_may_be_settled(tmp_path, monkeypatch):
    """Graded evidence at least as new as the snapshot, all rows stamped —
    only then may the published flag say 'settled'."""
    data_dir = tmp_path / "data"
    _write_canonical(data_dir, _canonical_snapshot(),
                     ledger_rows=[_graded("2026-11-05", 55),
                                  _graded("2026-11-10", _SCORE,
                                          graded_at="2026-12-15T10:00:00+00:00")])
    monkeypatch.setattr(build_site.config, "data_dir", lambda: data_dir)
    ms = build_site._canonical_market_state()
    assert ms["settlement"]["status"] == "settled"
    assert ms["settlement"]["newest_settled_asof"] == "2026-11-10"
