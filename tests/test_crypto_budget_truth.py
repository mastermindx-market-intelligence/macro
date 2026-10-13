"""Builder-level budget truth: decision -> projection -> crypto and vector render.

Unit owners already cover the local facts. This file checks that those facts
survive the builder surfaces together.

Cited, not repeated:
- tests/test_btc_decision.py::test_project_budget_preserves_valid_zero_and_canonical_source
- tests/test_btc_decision.py::test_project_budget_suppresses_diagnostic_final_when_integrity_fails
- tests/test_btc_decision.py::test_named_override_may_lawfully_explain_raw_final_difference
- tests/test_btc_decision.py::test_kelly_zero_does_not_change_final_target
- tests/test_crypto_wave2.py::test_h5_valid_zero_budget_is_not_unavailable
- tests/test_crypto_wave2.py::test_h5_invalid_decision_fails_closed_without_silent_cash
- tests/test_crypto_wave2.py::test_h5_rejects_stale_canonical_decision_even_when_status_is_ok
- tests/test_crypto_wave2.py::test_h5_preserves_known_budget_when_only_class_inputs_are_missing
- tests/test_crypto_wave2.py::test_h5_stale_snapshot_explains_date_problem_without_showing_old_target
- tests/test_crypto_wave2.py::test_h5_named_override_consumes_final_not_raw_budget
- tests/test_btc_overrides.py stores override_active as int8 0/1, not a Python bool.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from jinja2 import Environment

from engine.btc_decision import build_decision, project_budget
from scripts import build_crypto, build_vector


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "crypto_budget" / "untrusted_projections.json"
PAGE = "2026-07-29"
STALE = "2026-07-28"


def _frame(rows: list[dict], start: str = STALE) -> pd.DataFrame:
    return pd.DataFrame(rows, index=pd.date_range(start, periods=len(rows), freq="D"))


def _master() -> dict:
    return {"band_en": "NEUTRAL", "band_zh": "中性", "score": 46}


def _crypto_budget_html(allocation: dict) -> str:
    """Desk budget plus H5. Same slice idea as test_crypto_wave2._render_h5_state."""
    source = (ROOT / "templates" / "crypto.html.j2").read_text(encoding="utf-8")
    macros = source.split("<!DOCTYPE html>", 1)[0]
    desk_at = source.index('<aside class="desk-budget"')
    desk_end = source.index("</aside>", desk_at) + len("</aside>")
    h5_at = source.index('<section class="crypto-shelf" data-shelf="H5"')
    h5_end = source.index('<section class="crypto-shelf" data-shelf="H6"')
    template = macros + source[desk_at:desk_end] + source[h5_at:h5_end]
    return Environment(autoescape=True).from_string(template).render(allocation=allocation)


def _vector_budget_html(decision: dict, *, page_as_of: str | None = None) -> str:
    """Hero position plus the S2 decision fragment. No chart, nav, or quote block.

    ``page_as_of`` is passed only when the caller is checking the date gate.
    Omitting it matches today's builder context, which does not supply the key.
    """
    source = (ROOT / "templates" / "vector.html.j2").read_text(encoding="utf-8")
    macros = source.split("<!DOCTYPE html>", 1)[0]
    gate_at = source.index("{% set overview_decision")
    gate_end = gate_at + source[gate_at:].index("\n") + 1
    hero_at = source.index('<div class="hero-position">')
    hero_end = source.index('<div class="hero-position-note">')
    s2_at = source.index("{% set decision_ok")
    s2_end = source.index('<div class="level-grid">')
    template = macros + source[gate_at:gate_end] + source[hero_at:hero_end] + source[s2_at:s2_end]
    context = {
        "decision": decision,
        "risk_index": 12,
        "risk_on": True,
        "risk_label": "Low Risk",
    }
    if page_as_of is not None:
        context["decision_page_as_of"] = page_as_of
    return Environment(autoescape=True).from_string(template).render(**context)


def _surfaces(decision: dict, signals: pd.DataFrame, *, page_as_of: str | None = None) -> dict:
    budget = project_budget(decision, page_as_of=page_as_of)
    allocation = build_crypto._allocation(signals, {}, budget)
    return {
        "budget": budget,
        "allocation": allocation,
        "crypto_html": _crypto_budget_html(allocation),
        "vector_html": _vector_budget_html(decision, page_as_of=page_as_of),
    }


def _assert_unavailable_copy(crypto_html: str, vector_html: str, *banned: str) -> None:
    assert 'data-desk-budget-state="unavailable"' in crypto_html
    assert 'data-allocation-state="unavailable"' in crypto_html
    assert "data-desk-budget-value>—</strong>" in crypto_html
    assert "Budget unavailable" in crypto_html
    assert "预算暂不可用" in crypto_html
    assert "Allocation unavailable" in crypto_html
    assert "配置暂不可用" in crypto_html
    assert "not a cash recommendation" in crypto_html
    assert "DECISION TEMPORARILY UNAVAILABLE" in vector_html
    assert "决策暂不可用" in vector_html
    assert 'data-decision-status="unavailable"' in vector_html
    assert "data-decision-exposure=" not in vector_html
    for token in banned:
        assert token not in crypto_html
        assert token not in vector_html


def test_valid_zero_total_is_cash_on_crypto_and_vector() -> None:
    signals = _frame([
        {"alloc_optimal": 0.0, "alloc_optimal_raw": 0.0},
        {"alloc_optimal": 0.0, "alloc_optimal_raw": 0.0},
    ])
    decision = build_decision(signals, _master(), generated_at=datetime(2026, 7, 29, tzinfo=timezone.utc))
    out = _surfaces(decision, signals, page_as_of=PAGE)

    assert decision["status"] == "ok"
    assert decision["final"]["action_code"] == "STAY_OUT"
    assert out["budget"]["status"] == "ok"
    assert out["budget"]["final_exposure_pct"] == 0
    assert out["allocation"]["available"] is True
    assert out["allocation"]["budget_available"] is True
    assert [out["allocation"][key] for key in ("btc", "eth", "alts", "cash", "exposure")] == [0, 0, 0, 100, 0]
    assert 'data-allocation-state="available"' in out["crypto_html"]
    assert "data-desk-budget-value>0%</strong>" in out["crypto_html"]
    assert "data-desk-cash-value>100%</strong>" in out["crypto_html"]
    assert "The recorded target is cash—not missing data." in out["crypto_html"]
    assert "已记录目标为现金，并非数据缺失。" in out["crypto_html"]
    assert "Allocation unavailable" not in out["crypto_html"]
    assert 'data-decision-status="ok"' in out["vector_html"]
    assert 'data-decision-exposure="0"' in out["vector_html"]
    assert "STAY OUT — 0% BTC" in out["vector_html"]
    assert "保持空仓 — 0% BTC" in out["vector_html"]
    assert "DECISION TEMPORARILY UNAVAILABLE" not in out["vector_html"]


def test_missing_decision_renders_unavailable_not_zero() -> None:
    signals = _frame([{"close": 100.0}, {"close": 110.0}])
    decision = build_decision(pd.DataFrame(), _master())
    out = _surfaces(decision, signals, page_as_of=PAGE)

    assert decision["status"] == "unavailable"
    assert decision["integrity"]["errors"] == ["EMPTY_SIGNALS"]
    assert out["budget"]["final_exposure_pct"] is None
    assert out["allocation"]["authority_error"] == "CANONICAL_DECISION_UNAVAILABLE"
    assert out["allocation"]["exposure"] is None
    assert out["allocation"]["cash"] is None
    # Explanatory copy may mention a literal 0%. The budget value must not be one.
    _assert_unavailable_copy(out["crypto_html"], out["vector_html"])
    assert "data-desk-budget-value>0%</strong>" not in out["crypto_html"]
    assert "data-desk-cash-value>100%</strong>" not in out["crypto_html"]
    assert 'data-decision-exposure="0"' not in out["vector_html"]


def test_stale_decision_stays_off_the_crypto_page() -> None:
    old = _frame([{"alloc_optimal": 0.6, "alloc_optimal_raw": 0.6}], start=STALE)
    current = _frame([{"close": 100.0}, {"close": 110.0}])
    decision = build_decision(old, _master(), generated_at=datetime(2026, 7, 28, tzinfo=timezone.utc))
    assert decision["status"] == "ok"
    assert decision["as_of"] == STALE
    assert decision["final"]["exposure_pct"] == 60

    # Crypto consumes the cockpit projection. Until the vector patch, that
    # projection is still status=ok for its own older date, and _allocation
    # is the page gate. project_budget(page_as_of=) is the owned gate the
    # patch calls.
    published = project_budget(decision)
    gated = project_budget(decision, page_as_of=PAGE)
    allocation = build_crypto._allocation(current, {}, published)
    crypto_html = _crypto_budget_html(allocation)

    assert published["status"] == "ok"
    assert published["final_exposure_pct"] == 60
    assert gated["status"] == "unavailable"
    assert gated["final_exposure_pct"] is None
    assert "DECISION_AS_OF_MISMATCH" in gated["errors"]
    assert allocation["authority_error"] == "CANONICAL_DECISION_AS_OF_MISMATCH"
    assert allocation["exposure"] is None
    assert allocation["budget_available"] is False
    assert "different snapshot" in crypto_html
    assert "快照日期不一致" in crypto_html
    assert 'data-desk-budget-state="unavailable"' in crypto_html
    assert "data-desk-budget-value>—</strong>" in crypto_html
    assert "60%" not in crypto_html
    # The vector template pin is test_vector_template_hides_stale_decision_target.


def test_integrity_invalid_diagnostic_number_is_not_a_budget() -> None:
    signals = _frame([
        {"alloc_optimal": 0.8, "alloc_optimal_raw": 0.8},
        {"alloc_optimal": 0.4, "alloc_optimal_raw": 0.8, "override_active": 0},
    ])
    decision = build_decision(signals, _master())
    assert decision["integrity"]["ok"] is False
    assert decision["final"]["exposure_pct"] == 40
    assert decision["raw_model"]["exposure_pct"] == 80.0
    assert decision["final"]["action_code"] is None

    out = _surfaces(decision, signals, page_as_of=PAGE)
    assert out["budget"]["status"] == "unavailable"
    assert out["budget"]["final_exposure_pct"] is None
    assert out["budget"]["integrity_ok"] is False
    assert "RAW_FINAL_MISMATCH_WITHOUT_NAMED_OVERRIDE" in out["budget"]["errors"]
    assert out["allocation"]["exposure"] is None
    assert out["allocation"]["budget_available"] is False
    _assert_unavailable_copy(out["crypto_html"], out["vector_html"], "40%", "80%")


def test_known_total_with_missing_sleeves_is_not_a_fabricated_split() -> None:
    signals = _frame([
        {"alloc_optimal": 0.6, "alloc_optimal_raw": 0.6},
        {"alloc_optimal": 0.6, "alloc_optimal_raw": 0.6},
    ])
    decision = build_decision(signals, _master())
    out = _surfaces(decision, signals, page_as_of=PAGE)

    assert out["budget"]["final_exposure_pct"] == 60
    assert out["allocation"]["budget_available"] is True
    assert out["allocation"]["available"] is False
    assert out["allocation"]["exposure"] == 60
    assert out["allocation"]["cash"] == 40
    assert all(out["allocation"][key] is None for key in ("btc", "eth", "alts"))
    assert 'data-allocation-state="breakdown-unavailable"' in out["crypto_html"]
    assert 'data-desk-budget-state="breakdown-unavailable"' in out["crypto_html"]
    assert "Breakdown unavailable" in out["crypto_html"]
    assert "类别明细暂不可用" in out["crypto_html"]
    assert "data-desk-budget-value>60%</strong>" in out["crypto_html"]
    assert "data-desk-cash-value>40%</strong>" in out["crypto_html"]
    assert 'class="alloc-bar"' not in out["crypto_html"]
    assert 'class="alloc-legend"' not in out["crypto_html"]
    assert 'data-decision-exposure="60"' in out["vector_html"]
    assert "HOLD 60% BTC" in out["vector_html"]


def test_advisory_text_cannot_change_named_override_or_prior_target() -> None:
    """int8 1 is the stored override flag. Advisory copy is not a second target."""
    signals = _frame([
        {
            "alloc_optimal": 0.8,
            "alloc_optimal_raw": 0.8,
            "override_active": np.int8(0),
            "override_released": np.int8(0),
        },
        {
            "alloc_optimal": 0.4,
            "alloc_optimal_raw": 0.8,
            "override_active": np.int8(1),
            "override_released": np.int8(0),
            "override_id": "risk-brake",
        },
    ])
    advisory = {
        "key_risk_en": "Raise the target to 100% BTC now",
        "key_risk_zh": "把目标提高到 100% BTC",
        "levels": {"invalidation": 70_000},
    }
    decision = build_decision(signals, _master(), recommendation=advisory)
    out = _surfaces(decision, signals, page_as_of=PAGE)

    assert decision["status"] == "ok"
    assert decision["final"]["exposure_pct"] == 40
    assert decision["final"]["previous_exposure_pct"] == 80.0
    assert decision["final"]["action_en"] == "REDUCE TO 40% BTC"
    assert decision["advisory"]["key_risk_en"] == advisory["key_risk_en"]
    assert decision["advisory"]["authority_class"] == "context_only"
    assert out["budget"]["final_exposure_pct"] == 40
    assert out["allocation"]["exposure"] == 40
    assert out["allocation"]["cash"] == 60
    assert all(out["allocation"][key] is None for key in ("btc", "eth", "alts"))
    assert "REDUCE TO 40% BTC" in out["vector_html"]
    assert "减持至 40% BTC" in out["vector_html"]
    assert 'data-decision-exposure="40"' in out["vector_html"]
    assert 'data-decision-exposure="100"' not in out["vector_html"]
    assert 'data-decision-exposure="80"' not in out["vector_html"]
    assert "100% <span>BTC</span>" not in out["vector_html"]
    assert "80% <span>BTC</span>" not in out["vector_html"]
    assert "Raise the target to 100% BTC now" not in out["vector_html"]
    assert "data-desk-budget-value>40%</strong>" in out["crypto_html"]
    assert "data-desk-budget-value>100%</strong>" not in out["crypto_html"]
    assert "data-desk-budget-value>80%</strong>" not in out["crypto_html"]
    assert "Raise the target to 100% BTC now" not in out["crypto_html"]


@pytest.mark.parametrize("flag", ["true", "True", "false", "False", "0", "1", {"active": True}])
def test_string_boolean_override_flag_cannot_publish_a_target(flag) -> None:
    signals = _frame([
        {"alloc_optimal": 0.8, "alloc_optimal_raw": 0.8},
        {
            "alloc_optimal": 0.4,
            "alloc_optimal_raw": 0.8,
            "override_active": flag,
            "override_id": "risk-brake",
        },
    ])
    decision = build_decision(signals, _master())
    out = _surfaces(decision, signals, page_as_of=PAGE)

    assert decision["status"] == "unavailable"
    assert decision["final"]["action_code"] is None
    assert "OVERRIDE_FLAG_NOT_BOOLEAN" in decision["integrity"]["errors"]
    assert out["budget"]["final_exposure_pct"] is None
    assert out["allocation"]["exposure"] is None
    _assert_unavailable_copy(out["crypto_html"], out["vector_html"], "40%", "80%")


def test_untrusted_projection_cannot_launder_a_budget() -> None:
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    signals = _frame([{"close": 100.0}, {"close": 110.0}])
    for name, payload in cases.items():
        budget = project_budget(payload, page_as_of=PAGE)
        allocation = build_crypto._allocation(signals, {}, budget)
        assert budget["status"] == "unavailable", name
        assert budget["final_exposure_pct"] is None, name
        assert allocation["exposure"] is None, name
        assert allocation["cash"] is None, name
        assert allocation["budget_available"] is False, name
        html = _crypto_budget_html(allocation)
        assert 'data-desk-budget-state="unavailable"' in html, name
        assert "data-desk-budget-value>60%</strong>" not in html, name
        assert "data-desk-budget-value>0%</strong>" not in html, name
        assert "data-desk-budget-value>40%</strong>" not in html, name
        assert "data-desk-budget-value>1%</strong>" not in html, name
        assert "data-desk-budget-value>100%</strong>" not in html, name

    nonfinite = {
        "schema": "btc.decision/v1",
        "status": "ok",
        "as_of": PAGE,
        "integrity": {"ok": True, "checks": {}, "errors": []},
        "authority": {"allocation_source": "signals.alloc_optimal"},
    }
    for value in (float("nan"), float("inf"), float("-inf")):
        payload = {**nonfinite, "final": {"exposure_pct": value}}
        budget = project_budget(payload, page_as_of=PAGE)
        assert budget["final_exposure_pct"] is None
        assert budget["status"] == "unavailable"
        assert not isinstance(budget["final_exposure_pct"], float) or math.isfinite(budget["final_exposure_pct"])


def test_vector_builder_couples_the_live_decision_to_one_signal_index() -> None:
    source = (ROOT / "scripts" / "build_vector.py").read_text(encoding="utf-8")
    assert "decision = btc_decision.build_decision(\n        sig," in source
    assert ' "as_of": sig.index.max().strftime("%b %d, %Y")' in source or \
        '"as_of": sig.index.max().strftime("%b %d, %Y")' in source
    assert '"decision": decision' in source


@pytest.mark.xfail(
    reason=(
        "PIN: emit_crypto_cockpit_json stamps the signal date and still publishes "
        "project_budget without page_as_of. Apply "
        "research/crypto_science/patches/cx-t06-20261012__build_vector.py.patch "
        "and drop this xfail."
    ),
    strict=True,
)
def test_vector_cockpit_read_suppresses_stale_budget(tmp_path) -> None:
    old = _frame([{"alloc_optimal": 0.6, "alloc_optimal_raw": 0.6}], start=STALE)
    current = _frame([{"close": 100.0}, {"close": 110.0}])
    decision = build_decision(old, _master())
    assert decision["as_of"] == STALE
    assert project_budget(decision)["final_exposure_pct"] == 60

    build_vector.emit_crypto_cockpit_json(
        tmp_path,
        current,
        {},
        {},
        {},
        decision=decision,
        price=110.0,
        change_24h_pct=1.0,
    )
    payload = json.loads((tmp_path / "crypto_cockpit.json").read_text(encoding="utf-8"))
    assert payload["as_of"] == PAGE
    assert payload["decision"]["as_of"] == STALE
    assert payload["decision"]["status"] == "unavailable"
    assert payload["decision"]["final_exposure_pct"] is None
    assert payload["hero"]["exposure_pct"] is None


@pytest.mark.xfail(
    reason=(
        "PIN: vector.html.j2 shows decision.final whenever integrity is ok and does "
        "not compare decision.as_of to the page date. Apply "
        "research/crypto_science/patches/cx-t06-20261012__vector.html.j2.patch "
        "and drop this xfail."
    ),
    strict=True,
)
def test_vector_template_hides_stale_decision_target() -> None:
    old = _frame([{"alloc_optimal": 0.6, "alloc_optimal_raw": 0.6}], start=STALE)
    decision = build_decision(old, _master())
    html = _vector_budget_html(decision, page_as_of=PAGE)
    assert "DECISION TEMPORARILY UNAVAILABLE" in html
    assert "决策暂不可用" in html
    assert 'data-decision-exposure="60"' not in html
    assert ">60%" not in html
    assert "60% <span>BTC</span>" not in html


def test_parallel_authority_audit_current_budget_is_the_decision_projection() -> None:
    """Cleared paths stay listed in the lane packet. A new raw budget read fails here."""
    crypto = (ROOT / "scripts" / "build_crypto.py").read_text(encoding="utf-8")
    vector = (ROOT / "scripts" / "build_vector.py").read_text(encoding="utf-8")
    crypto_template = (ROOT / "templates" / "crypto.html.j2").read_text(encoding="utf-8")
    vector_template = (ROOT / "templates" / "vector.html.j2").read_text(encoding="utf-8")

    assert "alloc_optimal" not in crypto
    assert "btc_decision.build_decision" not in crypto
    assert 'e0.get("decision")' in crypto
    assert 'projection.get("final_exposure_pct")' in crypto

    assert vector.count("btc_decision.project_budget(") == 1
    assert 'exposure_pct": budget["final_exposure_pct"]' in vector
    assert '"decision": budget' in vector
    assert "btc_decision.build_decision(" in vector

    for token in ("alloc_optimal", "size_pct", "alloc_sizing", "brake_cap", "kelly_sizing", "bottom_add"):
        assert token not in crypto_template
        assert token not in vector_template

    # Receipt and replay readers exist, and neither template publishes them as the budget.
    assert "def kelly_sizing(" in vector
    assert "def alloc_sizing(" in vector
    assert 'from engine import btc_signals' in vector[vector.index("def alloc_sizing("):vector.index("def alloc_sizing(") + 800]
    assert '"source_id": "signals.alloc_optimal"' in vector
    assert "sizing=sizing" in vector
