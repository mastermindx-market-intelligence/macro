from __future__ import annotations

import pytest

from engine import market_state as ms


LABELS = {
    "trend": ("Trend & technicals", "趋势与技术"),
    "risk": ("Risk appetite", "风险偏好"),
    "vol": ("Volatility regime", "波动率环境"),
    "breadth": ("Breadth & participation", "广度与参与"),
    "liquidity": ("Liquidity & credit", "流动性与信用"),
    "stress": ("Downturn-risk guard", "下行风险护栏"),
}


def _component(key: str, score: int) -> dict:
    en, zh = LABELS[key]
    return {
        "key": key, "score": score, "weight": ms.WEIGHTS[key],
        "label_en": en, "label_zh": zh, "degraded": False,
    }


def _components(breadth: int | None) -> list[dict]:
    base = {"trend": 62, "risk": 85, "vol": 87, "liquidity": 47, "stress": 83}
    out = [_component(k, v) for k, v in base.items()]
    if breadth is not None:
        out.append(_component("breadth", breadth))
    return out


def test_narrow_risk_on_copy_is_selective_not_broad():
    copy = ms.market_state_display_copy("RISK_ON", _components(0))
    assert copy["participation"]["state"] == "narrow"
    assert copy["participation"]["score"] == 0
    assert copy["label_en"] == "Risk-on"
    assert copy["scope_en"] == "Selective risk-on"
    assert "breadth is weak" in copy["headline_en"]
    assert "sector/theme participation" in copy["action_en"]
    assert "entry setup" in copy["action_en"]
    assert "Do not" in copy["action_en"]
    assert "broad buy signal" in copy["action_en"]


def test_uneven_risk_on_copy_names_uneven_participation():
    copy = ms.market_state_display_copy("RISK_ON", _components(50))
    assert copy["participation"]["state"] == "uneven"
    assert copy["label_en"] == "Risk-on"
    assert copy["scope_en"] == "Risk-on · uneven participation"
    assert "not broad enough for an all-clear" in copy["headline_en"]


def test_broad_risk_on_copy_requires_supportive_breadth():
    copy = ms.market_state_display_copy("RISK_ON", _components(60))
    assert copy["participation"]["state"] == "broad"
    assert copy["label_en"] == "Risk-on"
    assert copy["scope_en"] == "Broad risk-on"
    assert "participation confirms" in copy["headline_en"]


def test_missing_breadth_fails_to_unverified_not_broad():
    copy = ms.market_state_display_copy("RISK_ON", _components(None))
    assert copy["participation"]["state"] == "unverified"
    assert copy["participation"]["score"] is None
    assert copy["label_en"] == "Risk-on"
    assert copy["scope_en"] == "Risk-on · participation unverified"


@pytest.mark.parametrize("verdict", ["MIXED", "RISK_OFF"])
def test_non_risk_on_verdicts_keep_canonical_stance_copy(verdict):
    copy = ms.market_state_display_copy(verdict, _components(0))
    assert copy["label_en"] == ms._LABEL[verdict][0]
    assert copy["headline_en"] == ms._HEADLINES[verdict][0]
    assert "broad buy signal" not in copy["action_en"]


def test_current_61_shape_keeps_score_and_canonical_label_but_projects_selective_copy():
    comps = _components(0)
    profile = ms.MarketProfile(
        key="us",
        indices=(),
        tape_noun_en="US indices",
        tape_noun_zh="美股指数",
        component_readers=tuple((lambda _latest, c=c: c) for c in comps),
        radar_override=None,
        overrides=frozenset(),
    )
    snap = ms.market_state_snapshot({"date": "2026-09-18", "conditions": {}}, profile=profile)

    assert snap is not None
    assert snap["score"] == 61
    assert snap["raw_score"] == 61
    assert snap["verdict"] == "RISK_ON"
    assert snap["label_en"] == "Risk-on"
    assert snap["participation"]["state"] == "narrow"
    assert snap["display_copy"]["label_en"] == "Risk-on"
    assert snap["display_copy"]["scope_en"] == "Selective risk-on"
    assert snap["headline_en"] == snap["display_copy"]["headline_en"]
