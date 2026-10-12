"""Bind btc.decision/v1 DecisionState into the crypto and vector pages.

Engine cases call ``build_decision`` / ``project_budget``. The page cases render
``templates/crypto.html.j2`` and ``templates/vector.html.j2`` through the same
Jinja environment the builders use (FileSystemLoader, autoescape, identity
``td``/``tr``). They skip until ``data-decision-state`` is in the crypto
template, which is what the T18b patch adds.

``CRYPTO_BINDING_TEMPLATE_ROOT`` overrides the template directory so a proof
copy can render the patch without touching the tracked tree. Includes still
resolve from the repository ``templates/`` directory.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader

from engine.btc_decision import build_decision, project_budget
from scripts import build_crypto

ROOT = Path(__file__).resolve().parent.parent
HOOK = "data-decision-state"
EM = "—"
GENERATED = datetime(2026, 8, 22, tzinfo=timezone.utc)


def _frame(rows: list[dict], on: str = "2026-08-21") -> pd.DataFrame:
    index = pd.date_range(on, periods=len(rows), freq="D")
    return pd.DataFrame(rows, index=index)


def _master() -> dict:
    return {"band_en": "NEUTRAL", "band_zh": "中性", "score": 46}


def _decide(rows: list[dict], on: str = "2026-08-21") -> dict:
    return build_decision(
        _frame(rows, on),
        _master(),
        generated_at=GENERATED,
    )


def _template_roots() -> list[str]:
    override = os.environ.get("CRYPTO_BINDING_TEMPLATE_ROOT")
    roots = [override] if override else []
    roots.append(str(ROOT / "templates"))
    return roots


def _source(name: str) -> str:
    return (Path(_template_roots()[0]) / name).read_text(encoding="utf-8")


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(_template_roots()), autoescape=True)
    env.globals.update(td=lambda value: value, tr=lambda value: value)
    return env


def _require_hook(name: str) -> None:
    if HOOK not in _source(name):
        pytest.skip(
            f"templates/{name} has no {HOOK} hook; "
            "render assertions activate when the T18b patch is applied"
        )


def _attrs(html: str, name: str) -> list[str]:
    return re.findall(rf'{name}="([^"]*)"', html)


def _patch_split(monkeypatch: pytest.MonkeyPatch, index: pd.DatetimeIndex) -> None:
    """Class-split inputs only. The budget still comes from project_budget."""
    monkeypatch.setattr(build_crypto.config, "load", lambda: {"vector": {"alt_cycle": {}}})
    highs = pd.DataFrame({"high": [101.0] * len(index)}, index=index)
    monkeypatch.setattr(
        build_crypto.store,
        "read",
        lambda group, name: highs if (group, name) == ("coinbase", "btc_daily") else None,
    )
    monkeypatch.setattr(
        build_crypto.btc_mtf,
        "mtf_ladder",
        lambda close, high: {"ladder": {"regime": "bull"}},
    )
    monkeypatch.setattr(
        build_crypto,
        "_series",
        lambda *args, **kwargs: pd.Series([0.05] * len(index), index=index),
    )
    monkeypatch.setattr(build_crypto.alt_cycle, "ethbtc_signal", lambda *a, **k: {"level": 0.05})
    monkeypatch.setattr(build_crypto.alt_cycle, "alt_season_score", lambda *a, **k: (60, "Mixed"))
    monkeypatch.setattr(
        build_crypto.alt_cycle,
        "alloc_grid",
        lambda *a, **k: {"btc": 60, "eth": 25, "alts": 15, "regime_key": "bull"},
    )


def _leaf(state: str = "Unavailable") -> dict:
    return {
        "tone": "flat",
        "state": state,
        "state_zh": "暂无",
        "value": None,
        "percentile": None,
        "change_30d_usd": None,
        "change_30d_pct": None,
    }


def _crypto_vm(allocation: dict, *, as_of: str) -> dict:
    flow = _leaf()
    heat = _leaf()
    return {
        "as_of": as_of,
        "built": "2026-08-22 00:00 UTC",
        "market": {
            "stance": "Range-bound, waiting for participation",
            "stance_zh": "区间震荡，等待参与度",
            "summary": "Daily context only.",
            "summary_zh": "仅为每日背景。",
            "total_tone": "flat",
            "dominance_tone": "flat",
            "fear_tone": "flat",
            "dominance_state": "Steady",
            "fear_state": "Neutral",
            "history": {"dates": [], "vals": []},
            "flows": {"etf": dict(flow), "stablecoins": dict(flow), "volume": dict(flow)},
            "heat": {
                "open_interest": dict(heat),
                "volatility": dict(heat),
                "altseason": dict(heat),
            },
        },
        "market_total": EM,
        "market_30d": EM,
        "dominance": EM,
        "dominance_30d": EM,
        "fear": EM,
        "total_state_zh": "暂无",
        "dominance_state_zh": "平稳",
        "fear_state_zh": "中性",
        "tape": "",
        "top_assets": [],
        "more_assets": [],
        "universe_count": 0,
        "universe_snapshot": {"as_of": None, "requested": 50, "excluded": [], "rows": []},
        "universe_sources": [],
        "breadth": {
            "available": False,
            "eligible": 0,
            "required": 10,
            "positive": None,
            "excluded": 0,
        },
        "allocation": allocation,
        "lanes": [],
        "equities": [],
        "calendar": [],
        "btc_options": {
            "as_of": None,
            "volatility": {"atm_iv_30d": None},
            "gamma": {
                "flip": None,
                "distance_pct": None,
                "assumption_en": "",
                "assumption_zh": "",
            },
            "positioning": {"put_call_oi_ratio": None, "max_pain": None},
            "basis": {"annualized_pct": None},
            "coverage": {"note_en": "", "note_zh": ""},
        },
        "fmt_money": lambda value, compact=False: EM,
        "fmt_pct": lambda value, digits=1, signed=True: EM,
    }


def _options() -> dict:
    return {
        "as_of": None,
        "volatility": {"atm_iv_30d": None},
        "gamma": {
            "flip": None,
            "distance_pct": None,
            "assumption_en": "",
            "assumption_zh": "",
        },
        "positioning": {"put_call_oi_ratio": None, "max_pain": None},
        "basis": {"annualized_pct": None},
        "coverage": {"note_en": "", "note_zh": ""},
    }


def _vector_vm(decision: dict, *, signal_as_of: str, page_as_of: str) -> dict:
    return {
        "as_of": page_as_of,
        "signal_as_of": signal_as_of,
        "built": "2026-08-22 00:00 UTC",
        "price": 64000.0,
        "chg24": 1.2,
        "master": {"ok": False},
        "decision": decision,
        "risk_index": 19,
        "risk_label": "Low Risk",
        "risk_on": True,
        "chart_contract": {
            "valid": False,
            "performance_valid": False,
            "issues": [],
            "meta": {
                "observed_at": None,
                "fields": {
                    "price": {"source_id": "price"},
                    "risk": {"source_id": "risk"},
                    "allocation": {"source_id": "allocation"},
                },
            },
        },
        "timeline": [],
        "presentation": {"axes": [], "watch": [], "complex": []},
        "cycle_stage": EM,
        "cycle_pos": EM,
        "btc_options": _options(),
        "options": {"dvol": None, "gamma_flip": None},
        "leverage": {"oi_total": None, "okx_ls_ratio": None},
        "bfi": None,
        "valuation": {"mvrv_z": None},
        "newf": {"holders": {"state": None}, "miner": {"state": None}},
        "onchain": {"premium_state": None},
        "charts": {"momentum": "", "structure": "", "bfi": "", "etf_flow": ""},
        "cycle_vintage": {"reserve_risk_asof": None, "vdd_asof": None},
        "strategy": {"as_of": None, "strategies": []},
        "calib": {"signals": {}, "meta": None, "risk_drawdown": None},
    }


def _render(template: str, vm: dict) -> str:
    return _env().get_template(template).render(**vm)


def test_valid_nonzero_decision_binds_final_exposure_and_as_of() -> None:
    decision = _decide([
        {"alloc_optimal": 0.4, "alloc_optimal_raw": 0.4, "close": 100.0},
    ])
    budget = project_budget(decision)

    assert decision["schema"] == "btc.decision/v1"
    assert decision["status"] == "ok"
    assert decision["integrity"]["ok"] is True
    assert decision["integrity"]["errors"] == []
    assert decision["as_of"] == "2026-08-21"
    assert decision["final"]["exposure"] == 0.4
    assert decision["final"]["exposure_pct"] == 40
    assert budget["status"] == "ok"
    assert budget["integrity_ok"] is True
    assert budget["as_of"] == decision["as_of"]
    assert budget["final_exposure_pct"] == 40
    assert budget["errors"] == []
    assert budget["final_exposure_pct"] != 0


def test_valid_zero_stays_zero_and_ok() -> None:
    decision = _decide([{"alloc_optimal": 0.0, "alloc_optimal_raw": 0.0}])
    budget = project_budget(decision)

    assert decision["status"] == "ok"
    assert decision["integrity"]["ok"] is True
    assert decision["final"]["exposure"] == 0.0
    assert decision["final"]["exposure_pct"] == 0
    assert decision["final"]["exposure_pct"] is not None
    assert decision["as_of"] == "2026-08-21"
    assert budget["status"] == "ok"
    assert budget["final_exposure_pct"] == 0
    assert budget["final_exposure_pct"] is not None
    assert budget["errors"] == []


def test_missing_input_is_unavailable_none_not_zero() -> None:
    missing = _decide([{"alloc_optimal": None, "alloc_optimal_raw": None}])
    missing_budget = project_budget(missing)
    empty = build_decision(pd.DataFrame(), _master(), generated_at=GENERATED)
    empty_budget = project_budget(empty)

    assert missing["status"] == "unavailable"
    assert missing["integrity"]["ok"] is False
    assert missing["as_of"] == "2026-08-21"
    assert missing["final"]["exposure"] is None
    assert missing["final"]["exposure_pct"] is None
    assert missing["final"]["action_code"] is None
    assert "MISSING_FINAL_ALLOCATION" in missing["integrity"]["errors"]
    assert missing_budget["status"] == "unavailable"
    assert missing_budget["final_exposure_pct"] is None
    assert missing_budget["final_exposure_pct"] != 0

    assert empty["status"] == "unavailable"
    assert empty["as_of"] is None
    assert empty["final"] is None
    assert "EMPTY_SIGNALS" in empty["integrity"]["errors"]
    assert empty_budget["final_exposure_pct"] is None
    assert empty_budget["final_exposure_pct"] != 0


def test_integrity_invalid_keeps_diagnostic_off_the_budget() -> None:
    decision = _decide([
        {"alloc_optimal": 0.4, "alloc_optimal_raw": 0.8, "override_active": False},
    ])
    budget = project_budget(decision)

    assert decision["status"] == "unavailable"
    assert decision["integrity"]["ok"] is False
    assert decision["as_of"] == "2026-08-21"
    assert "RAW_FINAL_MISMATCH_WITHOUT_NAMED_OVERRIDE" in decision["integrity"]["errors"]
    # The diagnostic final remains on the decision object and must not become the budget.
    assert decision["final"]["exposure_pct"] == 40
    assert budget["status"] == "unavailable"
    assert budget["integrity_ok"] is False
    assert budget["final_exposure_pct"] is None
    assert budget["final_exposure_pct"] != 0
    assert budget["as_of"] == decision["as_of"]
    assert "RAW_FINAL_MISMATCH_WITHOUT_NAMED_OVERRIDE" in budget["errors"]


def test_as_of_is_the_date_a_later_snapshot_mismatches() -> None:
    """Date mismatch is a consumer comparison. The engine keeps the real target."""
    decision = _decide(
        [{"alloc_optimal": 0.4, "alloc_optimal_raw": 0.4}],
        on="2026-08-20",
    )
    budget = project_budget(decision)

    assert decision["status"] == "ok"
    assert decision["integrity"]["errors"] == []
    assert decision["as_of"] == "2026-08-20"
    assert "CANONICAL_DECISION_AS_OF_MISMATCH" not in decision["integrity"]["errors"]
    assert budget["final_exposure_pct"] == 40
    assert budget["as_of"] == "2026-08-20"
    assert budget["as_of"] != "2026-08-21"


def test_crypto_page_renders_each_decision_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _require_hook("crypto.html.j2")
    fresh_index = pd.to_datetime(["2026-08-21"])
    _patch_split(monkeypatch, fresh_index)
    fresh_rows = [{"alloc_optimal": 0.4, "alloc_optimal_raw": 0.4, "close": 100.0}]
    fresh = build_decision(_frame(fresh_rows), _master(), generated_at=GENERATED)
    fresh_budget = project_budget(fresh)
    fresh_alloc = build_crypto._allocation(
        _frame(fresh_rows),
        {"btc_dominance": 58.0},
        fresh_budget,
    )
    assert fresh_alloc["exposure"] == fresh_budget["final_exposure_pct"] == 40
    assert fresh_alloc["available"] is True
    fresh_html = _render("crypto.html.j2", _crypto_vm(fresh_alloc, as_of="2026-08-21"))
    assert set(_attrs(fresh_html, "data-decision-state")) == {"available"}
    assert set(_attrs(fresh_html, "data-decision-freshness")) == {"fresh"}
    assert _attrs(fresh_html, "data-decision-as-of")
    assert set(_attrs(fresh_html, "data-decision-as-of")) == {"2026-08-21"}
    assert 'data-desk-budget-value>40%' in fresh_html
    assert 'data-allocation-state="available"' in fresh_html
    assert "2026-08-21" in fresh_html

    zero = _decide([{"alloc_optimal": 0.0, "alloc_optimal_raw": 0.0, "close": 100.0}])
    zero_alloc = build_crypto._allocation(
        _frame([{"alloc_optimal": 0.0, "alloc_optimal_raw": 0.0, "close": 100.0}]),
        {},
        project_budget(zero),
    )
    assert zero_alloc["exposure"] == 0
    assert zero_alloc["available"] is True
    zero_html = _render("crypto.html.j2", _crypto_vm(zero_alloc, as_of=zero["as_of"]))
    assert set(_attrs(zero_html, "data-decision-state")) == {"available"}
    assert 'data-desk-budget-value>0%' in zero_html
    assert 'data-desk-budget-value>—' not in zero_html
    assert "<b>0%</b>" in zero_html
    assert "The recorded target is cash" in zero_html

    missing = _decide([{"alloc_optimal": None}])
    missing_alloc = build_crypto._allocation(
        _frame([{"alloc_optimal": None}]),
        {},
        project_budget(missing),
    )
    assert missing_alloc["exposure"] is None
    assert missing_alloc["authority_error"] == "CANONICAL_DECISION_UNAVAILABLE"
    missing_html = _render("crypto.html.j2", _crypto_vm(missing_alloc, as_of="2026-08-21"))
    assert set(_attrs(missing_html, "data-decision-state")) == {"unavailable"}
    assert set(_attrs(missing_html, "data-decision-reason")) == {"CANONICAL_DECISION_UNAVAILABLE"}
    assert "MISSING_FINAL_ALLOCATION" in set(_attrs(missing_html, "data-decision-errors")).pop()
    assert 'data-desk-budget-value>—' in missing_html
    assert 'data-desk-budget-value>0%' not in missing_html
    assert "<b>—</b>" in missing_html
    assert "<b>0%</b>" not in missing_html

    invalid = _decide([
        {"alloc_optimal": 0.4, "alloc_optimal_raw": 0.8, "override_active": False},
    ])
    invalid_alloc = build_crypto._allocation(
        _frame([{"alloc_optimal": 0.4, "alloc_optimal_raw": 0.8, "override_active": False}]),
        {},
        project_budget(invalid),
    )
    assert invalid["final"]["exposure_pct"] == 40
    assert invalid_alloc["exposure"] is None
    invalid_html = _render("crypto.html.j2", _crypto_vm(invalid_alloc, as_of="2026-08-21"))
    assert set(_attrs(invalid_html, "data-decision-state")) == {"unavailable"}
    assert "RAW_FINAL_MISMATCH_WITHOUT_NAMED_OVERRIDE" in _attrs(invalid_html, "data-decision-errors")[0]
    assert 'data-desk-budget-value>—' in invalid_html
    assert 'data-desk-budget-value>40%' not in invalid_html
    assert 'data-desk-budget-value>0%' not in invalid_html
    assert "<b>40%</b>" not in invalid_html

    dated = _decide([{"alloc_optimal": 0.4, "alloc_optimal_raw": 0.4}], on="2026-08-20")
    later = _frame([{"close": 110.0}], on="2026-08-21")
    stale_alloc = build_crypto._allocation(later, {}, project_budget(dated))
    assert dated["status"] == "ok"
    assert dated["final"]["exposure_pct"] == 40
    assert stale_alloc["exposure"] is None
    assert stale_alloc["authority_error"] == "CANONICAL_DECISION_AS_OF_MISMATCH"
    assert stale_alloc["decision_as_of"] == dated["as_of"] == "2026-08-20"
    stale_html = _render("crypto.html.j2", _crypto_vm(stale_alloc, as_of="2026-08-21"))
    assert set(_attrs(stale_html, "data-decision-state")) == {"date-mismatch"}
    assert set(_attrs(stale_html, "data-decision-freshness")) == {"date-mismatch"}
    assert set(_attrs(stale_html, "data-decision-reason")) == {"CANONICAL_DECISION_AS_OF_MISMATCH"}
    assert set(_attrs(stale_html, "data-decision-as-of")) == {"2026-08-20"}
    assert 'data-allocation-state="unavailable"' in stale_html
    assert 'data-desk-budget-value>—' in stale_html
    assert 'data-desk-budget-value>40%' not in stale_html
    assert 'data-desk-budget-value>0%' not in stale_html
    assert "different snapshot" in stale_html
    assert "2026-08-20" in stale_html

    partial_rows = [{"alloc_optimal": 0.55, "alloc_optimal_raw": 0.55}]
    partial = _decide(partial_rows)
    partial_alloc = build_crypto._allocation(
        _frame(partial_rows),
        {},
        project_budget(partial),
    )
    assert partial_alloc["budget_available"] is True
    assert partial_alloc["available"] is False
    assert partial_alloc["exposure"] == 55
    partial_html = _render("crypto.html.j2", _crypto_vm(partial_alloc, as_of=partial["as_of"]))
    assert set(_attrs(partial_html, "data-decision-state")) == {"breakdown-unavailable"}
    assert set(_attrs(partial_html, "data-decision-freshness")) == {"fresh"}
    assert 'data-allocation-state="breakdown-unavailable"' in partial_html
    assert 'data-desk-budget-value>55%' in partial_html
    assert 'data-desk-budget-value>—' not in partial_html


def test_vector_page_renders_each_decision_state() -> None:
    _require_hook("vector.html.j2")

    def draw(decision: dict, signal_as_of: str) -> str:
        return _render(
            "vector.html.j2",
            _vector_vm(decision, signal_as_of=signal_as_of, page_as_of="Aug 21, 2026"),
        )

    def hero(html: str) -> str:
        match = re.search(r'class="hero-position-value"[^>]*>(.*?)</div>', html, re.S)
        assert match, "hero exposure missing"
        return match.group(1)

    fresh = _decide([{"alloc_optimal": 0.4, "alloc_optimal_raw": 0.4}])
    fresh_html = draw(fresh, fresh["as_of"])
    assert set(_attrs(fresh_html, "data-decision-state")) == {"available"}
    assert set(_attrs(fresh_html, "data-decision-freshness")) == {"fresh"}
    assert set(_attrs(fresh_html, "data-decision-as-of")) == {fresh["as_of"]}
    assert f"{fresh['final']['exposure_pct']}%" in hero(fresh_html)
    assert EM not in hero(fresh_html)
    assert f'data-decision-exposure="{fresh["final"]["exposure_pct"]}"' in fresh_html

    zero = _decide([{"alloc_optimal": 0.0, "alloc_optimal_raw": 0.0}])
    zero_html = draw(zero, zero["as_of"])
    assert zero["final"]["exposure_pct"] == 0
    assert set(_attrs(zero_html, "data-decision-state")) == {"available"}
    assert "0%" in hero(zero_html)
    assert EM not in hero(zero_html)
    assert 'data-decision-exposure="0"' in zero_html

    missing = _decide([{"alloc_optimal": None}])
    missing_html = draw(missing, missing["as_of"] or "")
    assert set(_attrs(missing_html, "data-decision-state")) == {"unavailable"}
    assert set(_attrs(missing_html, "data-decision-reason")) == {"MISSING_FINAL_ALLOCATION"}
    assert EM in hero(missing_html)
    assert "0%" not in hero(missing_html)
    assert "data-decision-exposure=" not in missing_html

    invalid = _decide([
        {"alloc_optimal": 0.4, "alloc_optimal_raw": 0.8, "override_active": False},
    ])
    invalid_html = draw(invalid, invalid["as_of"])
    assert invalid["final"]["exposure_pct"] == 40
    assert set(_attrs(invalid_html, "data-decision-state")) == {"unavailable"}
    assert set(_attrs(invalid_html, "data-decision-reason")) == {
        "RAW_FINAL_MISMATCH_WITHOUT_NAMED_OVERRIDE"
    }
    assert "RAW_FINAL_MISMATCH_WITHOUT_NAMED_OVERRIDE" in _attrs(invalid_html, "data-decision-errors")[0]
    assert EM in hero(invalid_html)
    assert "40%" not in hero(invalid_html)
    assert "0%" not in hero(invalid_html)
    assert "data-decision-exposure=" not in invalid_html

    dated = _decide([{"alloc_optimal": 0.4, "alloc_optimal_raw": 0.4}], on="2026-08-20")
    assert dated["status"] == "ok"
    assert dated["final"]["exposure_pct"] == 40
    stale_html = draw(dated, "2026-08-21")
    assert set(_attrs(stale_html, "data-decision-state")) == {"date-mismatch"}
    assert set(_attrs(stale_html, "data-decision-freshness")) == {"date-mismatch"}
    assert set(_attrs(stale_html, "data-decision-reason")) == {"CANONICAL_DECISION_AS_OF_MISMATCH"}
    assert set(_attrs(stale_html, "data-decision-as-of")) == {"2026-08-20"}
    assert EM in hero(stale_html)
    assert "40%" not in hero(stale_html)
    assert "0%" not in hero(stale_html)
    assert "2026-08-20" in hero(stale_html)
    assert "data-decision-exposure=" not in stale_html
    assert "Decision unavailable" in stale_html
