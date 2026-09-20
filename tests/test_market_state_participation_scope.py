from __future__ import annotations

from engine import market_state as ms


def _leg(key: str, score: int) -> dict:
    return {
        "key": key,
        "label_en": key.title(),
        "label_zh": key,
        "score": score,
        "weight": ms.WEIGHTS[key],
        "tone": "good" if score >= 60 else "warn" if score >= 42 else "bad",
        "arrow": "▶",
        "read_en": "",
        "read_zh": "",
        "metrics": [],
        "degraded": False,
    }


def _risk_on_components(breadth: int) -> list[dict]:
    return [
        _leg("risk", 100),
        _leg("vol", 100),
        _leg("breadth", breadth),
        _leg("liquidity", 100),
        _leg("stress", 100),
    ]


def test_us_risk_on_with_weak_breadth_is_selective_not_broad():
    comps = _risk_on_components(0)

    scope = ms._participation_scope("RISK_ON", comps, market="us")
    headline = ms._headline_for("RISK_ON", comps, market="us")

    assert scope["state"] == "selective"
    assert scope["participation"] == "weak"
    assert scope["breadth_score"] == 0
    assert scope["subline_en"] == "GREEN — Selective risk-on"
    assert scope["action_en"] == "Stay selective. Follow confirmed leadership and fresh turns."
    assert headline[0].startswith("Selective risk-on")
    assert "participation is weak" in headline[0]
    assert "broad rally" in headline[0]
    assert "breadth and cross-asset signals line up" not in headline[0]


def test_us_risk_on_with_uneven_breadth_is_selective():
    comps = _risk_on_components(50)

    scope = ms._participation_scope("RISK_ON", comps, market="us")
    headline = ms._headline_for("RISK_ON", comps, market="us")

    assert scope["state"] == "selective"
    assert scope["participation"] == "uneven"
    assert scope["breadth_score"] == 50
    assert headline[0].startswith("Selective risk-on")
    assert "participation is uneven" in headline[0]


def test_us_risk_on_with_supportive_breadth_is_broad():
    comps = _risk_on_components(75)

    scope = ms._participation_scope("RISK_ON", comps, market="us")
    headline = ms._headline_for("RISK_ON", comps, market="us")

    assert scope["state"] == "broad"
    assert scope["participation"] == "supportive"
    assert scope["breadth_score"] == 75
    assert headline[0].startswith("Broad risk-on")
    assert "participation confirms" in headline[0]


def test_us_risk_on_with_missing_breadth_fails_closed():
    comps = [c for c in _risk_on_components(75) if c["key"] != "breadth"]

    scope = ms._participation_scope("RISK_ON", comps, market="us")
    headline = ms._headline_for("RISK_ON", comps, market="us")

    assert scope["state"] == "unverified"
    assert scope["participation"] == "unverified"
    assert scope["breadth_score"] is None
    assert "participation is unverified" in headline[0]
    assert "Broad risk-on" not in headline[0]


def test_base_risk_on_fallback_never_claims_breadth_confirmation():
    en, zh = ms._HEADLINES["RISK_ON"]

    assert "breadth and cross-asset signals line up" not in en
    assert "participation and entry quality still matter" in en
    assert "市场参与度" in zh


def test_non_risk_on_and_non_us_keep_existing_headline_contract():
    comps = _risk_on_components(0)

    assert ms._participation_scope("MIXED", comps, market="us") is None
    assert ms._headline_for("MIXED", comps, market="us") == ms._HEADLINES["MIXED"]
    assert ms._participation_scope("RISK_ON", comps, market="cn") is None
    assert ms._headline_for("RISK_ON", comps, market="cn") == ms._HEADLINES["RISK_ON"]


def test_snapshot_keeps_score_and_verdict_while_exposing_selective_scope():
    comps = _risk_on_components(0)
    readers = tuple((lambda _latest, c=c: c) for c in comps)
    profile = ms.MarketProfile(
        key="us",
        indices=(),
        tape_noun_en="US indices",
        tape_noun_zh="美股指数",
        component_readers=readers,
        radar_override=None,
        overrides=frozenset(),
    )

    snap = ms.market_state_snapshot({"date": "2026-09-18"}, None, [], profile=profile)

    assert snap is not None
    assert snap["raw_score"] >= 60
    assert snap["score"] == snap["raw_score"]
    assert snap["verdict"] == "RISK_ON"
    assert snap["participation_scope"]["state"] == "selective"
    assert snap["participation_scope"]["breadth_score"] == 0
    assert snap["headline_en"].startswith("Selective risk-on")
