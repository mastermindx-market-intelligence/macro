"""November 9 live-score regression: pointer 41, stale renderer 39.

The site-only path must render one canonical snapshot; only nightly with a
current NYSE/SPY store may compute and advance the forward-settlement ledger.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
from jinja2 import Environment

from engine import market_state as ms
from engine import market_state_audit as audit
from lib import config, nyse_calendar
from scripts import build_site
from scripts import check_ms_board_coherence as board_guard


NOV9 = "2026-11-09"
LEGS_41 = [38, 22, 47, 36, 39, 75]
LEGS_39 = [32, 22, 47, 36, 39, 75]


def _snapshot(score=41, *, asof=NOV9, legs=LEGS_41):
    return {
        "schema": "market_state.v1", "asof": asof, "score": score,
        "raw_score": score, "score_source": "blend", "verdict": "RISK_OFF",
        "components": [{"key": f"leg{i}", "score": n} for i, n in enumerate(legs)],
        "freshness": {"data_asof": asof, "expected_asof": NOV9, "stale": False},
    }


def _page(*, score=41, legs=LEGS_41, asof=NOV9, endpoint=41):
    rows = "".join(f'<span class="mx5-factor-score">{n}</span>' for n in legs)
    points = json.dumps([{"d": NOV9, "s": endpoint, "v": "Risk-off"}])
    return (f'<span id="regime-asof">{asof}</span>'
            f'<span id="ms-date">{asof}</span>'
            f'<section class="ms-verdict"><span id="ms-score">{score}</span></section>'
            f'{rows}<svg class="mx5-path-svg" data-points=\'{points}\'></svg>')


def _refuse_recompute(*args, **kwargs):
    raise AssertionError("a render lane must not recompute or persist Market State")


def test_express_render_uses_nov9_canonical_41_even_with_nov6_features(monkeypatch):
    canonical = _snapshot()
    monkeypatch.setattr(audit, "ledger_lane_armed", lambda: False)
    monkeypatch.setattr(ms, "load_persisted", lambda: canonical.copy())
    monkeypatch.setattr(ms, "market_state_snapshot", _refuse_recompute)
    monkeypatch.setattr(ms, "persist", _refuse_recompute)
    # This is the exact November 9 incident's stale SPY render frame.
    old_frame = pd.DataFrame({"close": [1]}, index=pd.to_datetime(["2026-11-06"]))
    got = build_site.market_state_view({"date": NOV9}, old_frame)
    assert got["score"] == 41
    assert [c["score"] for c in got["components"]] == LEGS_41


def test_express_render_withholds_missing_corrupt_or_wrong_session(monkeypatch):
    monkeypatch.setattr(audit, "ledger_lane_armed", lambda: False)
    monkeypatch.setattr(ms, "market_state_snapshot", _refuse_recompute)
    monkeypatch.setattr(ms, "persist", _refuse_recompute)
    for snapshot in (None, {}, _snapshot(asof="2026-11-06"),
                     {**_snapshot(), "freshness": {"data_asof": "2026-11-06"}},
                     {**_snapshot(), "score": 110},
                     {**_snapshot(), "verdict": "RISK_ON"},
                     {**_snapshot(), "components": []}):
        monkeypatch.setattr(ms, "load_persisted", lambda: snapshot)
        assert build_site.market_state_view({"date": NOV9}, pd.DataFrame()) is None


def test_nightly_stale_spy_preserves_41_and_never_appends_39(monkeypatch):
    from scripts import refresh_regime_if_stale as refresh

    canonical = _snapshot()
    monkeypatch.setattr(audit, "ledger_lane_armed", lambda: True)
    monkeypatch.setattr(ms, "load_persisted", lambda: canonical)
    monkeypatch.setattr(ms, "market_state_snapshot", _refuse_recompute)
    monkeypatch.setattr(ms, "persist", _refuse_recompute)
    monkeypatch.setattr(refresh, "_store_close_date", lambda: "2026-11-06")
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda: date(2026, 11, 9))
    assert build_site.market_state_view({"date": NOV9}, pd.DataFrame())["score"] == 41


def test_nightly_fresh_spy_can_compute_and_persist(monkeypatch):
    from scripts import refresh_regime_if_stale as refresh
    from engine import market_state_tune as tune

    published = []
    monkeypatch.setattr(audit, "ledger_lane_armed", lambda: True)
    monkeypatch.setattr(ms, "load_persisted", lambda: _snapshot(asof="2026-11-06"))
    monkeypatch.setattr(ms, "market_state_snapshot", lambda *_a: _snapshot())
    monkeypatch.setattr(ms, "persist", lambda snap: published.append(snap.copy()))
    monkeypatch.setattr(audit, "snapshot_and_grade", lambda snap: {"logged": True})
    monkeypatch.setattr(tune, "tune", lambda: {"updated": False})
    monkeypatch.setattr(refresh, "_store_close_date", lambda: NOV9)
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda: date(2026, 11, 9))
    got = build_site.market_state_view({"date": NOV9}, pd.DataFrame())
    assert got["score"] == published[0]["score"] == 41
    assert got["audit"]["logged"] is True


def test_nightly_does_not_publish_when_regime_and_spy_sessions_split(monkeypatch):
    from scripts import refresh_regime_if_stale as refresh

    published = []
    monkeypatch.setattr(audit, "ledger_lane_armed", lambda: True)
    monkeypatch.setattr(ms, "load_persisted", lambda: _snapshot())
    monkeypatch.setattr(ms, "market_state_snapshot", lambda *_a: _snapshot())
    monkeypatch.setattr(ms, "persist", lambda snap: published.append(snap))
    monkeypatch.setattr(refresh, "_store_close_date", lambda: NOV9)
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda: date(2026, 11, 9))
    assert build_site.market_state_view({"date": "2026-11-06"}, pd.DataFrame()) is None
    assert published == []


def test_forward_log_is_required_before_claiming_nov9_settled(monkeypatch, tmp_path):
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda: date(2026, 11, 9))
    ledger = tmp_path / "data/market_state/forward_log.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps({"asof": "2026-11-06", "score": 36, "raw_score": 36}) + "\n")
    assert not build_site._ms_settlement_verified(_snapshot(), root=tmp_path)
    ledger.write_text(ledger.read_text() + json.dumps({"asof": NOV9, "score": 39, "raw_score": 39}) + "\n")
    assert not build_site._ms_settlement_verified(_snapshot(), root=tmp_path)
    ledger.write_text(json.dumps({"asof": NOV9, "score": 41, "raw_score": 41}) + "\n")
    assert build_site._ms_settlement_verified(_snapshot(), root=tmp_path)
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda: date(2026, 11, 10))
    assert not build_site._ms_settlement_verified(_snapshot(), root=tmp_path)


def test_nov9_path_endpoint_tracks_canonical_41_even_before_nightly(monkeypatch, tmp_path):
    ledger = tmp_path / "data/market_state/forward_log.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps({"asof": "2026-11-06", "score": 36, "raw_score": 36}) + "\n")
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    history = build_site._ms_history_view(_snapshot())
    assert history[-1] == {"asof": NOV9, "score": 41}
    assert len(history) == 2


def test_actual_jinja_stamp_does_not_claim_unverified_nov9_settlement():
    source = (Path(__file__).parents[1] / "templates/dashboard.html.j2").read_text()
    start = source.index('<span class="mx5-path-meta">')
    # The full nested span is parsed as source, not constructed from a test-only
    # copy of the wording. Include its Jinja expressions through the meta close.
    end = source.index('</span>\n      </div>', start) + len('</span>')
    fragment = Environment(autoescape=True).from_string(source[start:end])
    values = {"_ph_last_d": NOV9, "_mx5_mos_en": ['', 'Jan', 'Feb', 'Mar', 'Apr',
              'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']}
    pending = fragment.render(ms_settlement_verified=False, **values)
    verified = fragment.render(ms_settlement_verified=True, **values)
    assert "Nov 9 snapshot" in pending and "nightly verification pending" in pending
    assert "settled through" not in pending
    assert "settled through Nov 9" in verified


def test_public_board_canonical_parity_detects_exact_41_vs_39_split():
    canonical = _snapshot()
    assert board_guard.check_canonical_parity("site/macro.html", _page(), canonical) == []
    failures = board_guard.check_canonical_parity(
        "site/macro.html", _page(score=39, legs=LEGS_39, endpoint=39), canonical)
    assert {"score", "factor", "path"} <= {
        "score" if "score 39" in v else "factor" if "factor scores" in v else "path"
        for v in failures
    }
    assert board_guard.check_canonical_parity(
        "site/macro.html", _page(asof="2026-11-06"), canonical)
    assert board_guard.check_canonical_parity(
        "site/macro.html", '<span id="regime-asof">2026-11-09</span>', canonical)


def test_nov9_canonical_data_matches_source_math():
    # Historical incident fixture, not a hard-coded expectation of tomorrow's
    # production pointer (which must advance normally after this repair).
    snap = _snapshot()
    assert snap["asof"] == NOV9 and snap["score"] == 41
    assert [c["score"] for c in snap["components"]] == LEGS_41
    assert round(sum(a * b for a, b in zip(LEGS_41, (.24, .18, .16, .16, .14, .12)))) == 41
    assert round(sum(a * b for a, b in zip(LEGS_39, (.24, .18, .16, .16, .14, .12)))) == 39


def test_both_express_publishers_gate_parity_and_pointer_races():
    base = Path(__file__).parents[1] / ".github/workflows"
    for workflow in ("render.yml", "engine-render.yml"):
        src = (base / workflow).read_text()
        assert "--canonical-parity site/macro.html" in src
        assert "MS_SOURCE_BLOB" in src
        assert "origin/main:data/market_state/latest.json" in src
        assert "refusing stale site/macro.html push" in src
