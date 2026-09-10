"""Risk Radar publication velocity + explainable transition regression tests.

The user-facing defect was twofold:
* the card showed only today's score, even though the canonical forward ledger already
  held prior publications; and
* the regime-transition alert said only that the state changed, not which flags did it.

These tests intentionally use the existing append-only ledgers.  No second history store.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from engine import risk_radar_audit as rra
from engine.alerts import alert_view, transition_state_change
from engine.market_state import _radar_to_rd

ROOT = Path(__file__).resolve().parent.parent


def _leg(name: str, pctile: float) -> dict:
    return {"leg": name, "pctile": pctile, "confirmed": True,
            "era_robust": True, "lift_2020": 1.0}


def _ledger_row(asof: str, state: str, top_score: float,
                growth_score: float, growth_band: str,
                growth_legs: list[dict], credit_score: float = 55.0) -> dict:
    return {
        "asof": asof,
        "state": state,
        "dominant_scare": "growth",
        "top_score": top_score,
        "scares": {
            "growth": {"score": growth_score, "band": growth_band,
                       "firing_legs": growth_legs},
            "credit": {"score": credit_score, "band": "watch",
                       "firing_legs": [_leg("credit_oas_roc", 0.70)]},
        },
    }


def _current_snapshot() -> dict:
    return {
        "asof": "2026-09-09",
        "state": "watch",
        "dominant_scare": "growth",
        "dominant_label_en": "Growth scare",
        "dominant_label_zh": "增长恐慌",
        "top_score": 65.7,
        "scares": [
            {"scare": "growth", "label_en": "Growth scare", "label_zh": "增长恐慌",
             "score": 65.7, "band": "watch",
             "firing_legs": [_leg("growth_cyc_def", 0.81)]},
            {"scare": "credit", "label_en": "Credit stress", "label_zh": "信用压力",
             "score": 55.6, "band": "watch",
             "firing_legs": [_leg("credit_oas_roc", 0.69)]},
        ],
    }


def _write_ledger(root: Path, rows: list[dict]) -> None:
    p = root / "data" / "risk_radar" / "forward_log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_publication_change_uses_strictly_earlier_row_and_explains_drivers(tmp_path) -> None:
    rows = [
        _ledger_row("2026-09-02", "caution", 70.0, 70.0, "caution",
                    [_leg("growth_cyc_def", 0.76), _leg("growth_defensives", 0.71)], 56.0),
        _ledger_row("2026-09-08", "caution", 75.1, 75.1, "caution",
                    [_leg("growth_cyc_def", 0.798), _leg("growth_defensives", 0.704)], 57.6),
        # Proves same-asof rows cannot become the comparator after the nightly append.
        _ledger_row("2026-09-09", "calm", 1.0, 1.0, "calm", [], 1.0),
    ]
    _write_ledger(tmp_path, rows)

    ch = rra.publication_change(_current_snapshot(), root=tmp_path)

    assert ch["available"] is True
    assert ch["basis"] == "prior_publication"
    assert ch["prior_asof"] == "2026-09-08"
    assert ch["score"] == {
        "current": 65.7, "prior": 75.1, "delta": -9.4, "direction": "easing"
    }
    assert ch["state"] == {"current": "watch", "prior": "caution", "changed": True}
    growth = next(s for s in ch["scares"] if s["scare"] == "growth")
    assert growth["prior"] == 75.1 and growth["current"] == 65.7
    assert growth["delta"] == -9.4 and growth["band_changed"] is True
    assert growth["cleared_legs"] == ["growth_defensives"]
    assert growth["added_legs"] == []
    assert ch["week"] == {
        "available": True, "asof": "2026-09-02", "score": 70.0, "delta": -4.3
    }
    assert "75.1→65.7" in ch["summary_en"]
    assert "Defensives outperforming cleared" in ch["summary_en"]
    assert "防御股跑赢解除" in ch["summary_zh"]


def test_publication_change_has_typed_absence_not_fake_zero(tmp_path) -> None:
    _write_ledger(tmp_path, [
        _ledger_row("2026-09-09", "watch", 65.7, 65.7, "watch",
                    [_leg("growth_cyc_def", 0.81)])
    ])
    ch = rra.publication_change(_current_snapshot(), root=tmp_path)
    assert ch["available"] is False
    assert ch["null_reason"] == "NO_EARLIER_PUBLICATION"
    assert ch["prior_asof"] is None
    assert ch["week"]["available"] is False
    assert ch["history"] == [{"asof": "2026-09-09", "state": "watch",
                              "dominant_scare": "growth", "top_score": 65.7}]


def test_snapshot_and_grade_attaches_change_without_advancing_second_ledger(monkeypatch) -> None:
    monkeypatch.setattr(rra, "log_snapshot", lambda snap, root=None: False)
    monkeypatch.setattr(rra, "grade_log", lambda root=None: 0)
    monkeypatch.setattr(rra, "scorecard", lambda root=None: {"n_graded": 3})
    monkeypatch.setattr(rra, "publication_change",
                        lambda snap, root=None: {"available": True, "prior_asof": "2026-09-08"})
    out = rra.snapshot_and_grade(_current_snapshot())
    assert out == {"n_graded": 3,
                   "publication_change": {"available": True, "prior_asof": "2026-09-08"}}


def test_radar_card_preserves_decimal_and_renders_compact_velocity(monkeypatch) -> None:
    monkeypatch.setattr("engine.market_state._rr_scorecard_track", lambda market: None)
    change = {
        "available": True,
        "prior_asof": "2026-09-08",
        "score": {"current": 65.7, "prior": 75.1, "delta": -9.4, "direction": "easing"},
        "week": {"available": True, "asof": "2026-09-02", "score": 70.0, "delta": -4.3},
        "summary_en": "Growth 75.1→65.7 · Caution→Watch · Defensives outperforming cleared",
        "summary_zh": "增长 75.1→65.7 · 警戒→关注 · 防御股跑赢解除",
    }
    rr = {
        **_current_snapshot(),
        "market": "us",
        "alert": False,
        "gross_factor": 1.0,
        "drawdown_prob": {"h5": 0.08, "h10": 0.12, "h21": 0.20,
                          "lift_h21": 1.1, "base_h5": 0.036,
                          "base_h10": 0.086, "base_h21": 0.178},
        "forward_log": {"n_graded": 3, "publication_change": change},
    }
    rd = _radar_to_rd(rr)
    assert rd["top_score"] == 65.7
    assert rd["change"] == change

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=select_autoescape(["html", "xml"]),
                      undefined=StrictUndefined)
    tpl = env.from_string(
        '{% import "_risk_radar_card.html.j2" as rrc %}'
        '{{ rrc.risk_radar_card(rd, [], false) }}'
    )
    html = tpl.render(rd=rd)
    assert "65.7/100" in html
    assert "▼9.4" in html
    assert "Prev 75.1" in html and "1W 70.0" in html
    assert "Defensives outperforming cleared" in html


def test_transition_alert_names_added_and_cleared_flags() -> None:
    idx = pd.bdate_range("2026-09-08", periods=2)
    hist = pd.DataFrame({
        "quad": ["Q1", "Q1"],
        "transition_state": ["STABLE", "WEAKENING"],
        "n_flags": [1, 2],
        "growth_confidence": [0.6, 0.6],
        "inflation_confidence": [0.6, 0.6],
        "flag_breadth_price": [False, True],
        "flag_credit_equity": [True, False],
        "flag_ratio_inflection": [False, False],
        "flag_inflation_basket": [False, False],
        "flag_confidence_decay": [False, False],
        "flag_gex": [False, True],
        "flag_rotation_persistence": [False, False],
    }, index=idx)

    alert = transition_state_change(hist, pd.DataFrame())
    assert alert is not None
    assert "added: breadth/price divergence, dealer-gamma fragility" in alert.message
    assert "cleared: credit/equity divergence" in alert.message
    assert "flag_breadth_price" not in alert.message
    assert "新增：宽度/价格背离、做市商 Gamma 脆弱" in alert.message_zh
    assert "解除：信用/股票背离" in alert.message_zh

    view = alert_view(alert.rule, alert.severity, alert.message, alert.message_zh)
    assert view["message"].startswith(
        "The regime's footing went from steady to weakening (2 warning flags active)"
    )
    assert "added: breadth/price divergence" in view["message"]
    assert "新增：宽度/价格背离" in view["message_zh"]
