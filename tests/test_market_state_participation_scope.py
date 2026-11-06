from __future__ import annotations

from engine import market_state as ms


ASOF = "2026-09-18"


def _fresh(*, asof: str = ASOF, vintage_asof: str | None = None, stale: bool = False) -> dict:
    return {
        "market": "us",
        "asof": asof,
        "input_vintages": {
            "pct_above_200": {
                "asof": vintage_asof or asof,
                "stale": stale,
            }
        },
    }


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

    scope = ms._participation_scope("RISK_ON", comps, **_fresh())
    headline = ms._headline_for("RISK_ON", comps, **_fresh())

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

    scope = ms._participation_scope("RISK_ON", comps, **_fresh())
    headline = ms._headline_for("RISK_ON", comps, **_fresh())

    assert scope["state"] == "selective"
    assert scope["participation"] == "uneven"
    assert scope["breadth_score"] == 50
    assert headline[0].startswith("Selective risk-on")
    assert "participation is uneven" in headline[0]


def test_us_risk_on_with_supportive_breadth_is_broad():
    comps = _risk_on_components(75)

    scope = ms._participation_scope("RISK_ON", comps, **_fresh())
    headline = ms._headline_for("RISK_ON", comps, **_fresh())

    assert scope["state"] == "broad"
    assert scope["participation"] == "supportive"
    assert scope["breadth_score"] == 75
    assert headline[0].startswith("Broad risk-on")
    assert "participation confirms" in headline[0]


def test_us_risk_on_with_missing_breadth_fails_closed():
    comps = [c for c in _risk_on_components(75) if c["key"] != "breadth"]

    scope = ms._participation_scope("RISK_ON", comps, **_fresh())
    headline = ms._headline_for("RISK_ON", comps, **_fresh())

    assert scope["state"] == "unverified"
    assert scope["participation"] == "unverified"
    assert scope["breadth_score"] is None
    assert "participation is unverified" in headline[0]
    assert "Broad risk-on" not in headline[0]


def test_breadth_truth_fails_closed_when_not_one_fresh_same_session_observation():
    fresh = _fresh()
    degraded = _risk_on_components(75)
    degraded[2]["degraded"] = True
    boolean_score = _risk_on_components(75)
    boolean_score[2]["score"] = True
    numeric_string = _risk_on_components(75)
    numeric_string[2]["score"] = "75"

    cases = [
        ([c for c in _risk_on_components(75) if c["key"] != "breadth"], fresh),
        (_risk_on_components(75) + [_leg("breadth", 80)], fresh),
        (_risk_on_components(101), fresh),
        (boolean_score, fresh),
        (numeric_string, fresh),
        (degraded, fresh),
        (_risk_on_components(75), _fresh(stale=True)),
        (_risk_on_components(75), _fresh(vintage_asof="2026-09-17")),
        (_risk_on_components(75), {"market": "us", "asof": ASOF, "input_vintages": {}}),
    ]
    for comps, kwargs in cases:
        scope = ms._participation_scope("RISK_ON", comps, **kwargs)
        headline = ms._headline_for("RISK_ON", comps, **kwargs)
        assert scope["state"] == "unverified"
        assert scope["participation"] == "unverified"
        assert "participation is unverified" in headline[0]
        assert not headline[0].startswith(("Broad risk-on", "Selective risk-on"))


def test_base_risk_on_fallback_never_claims_breadth_confirmation():
    en, zh = ms._HEADLINES["RISK_ON"]

    assert "breadth and cross-asset signals line up" not in en
    assert "participation and entry quality still matter" in en
    assert "市场参与度" in zh


def test_non_risk_on_and_non_us_keep_existing_headline_contract():
    comps = _risk_on_components(0)

    assert ms._participation_scope("MIXED", comps, **_fresh()) is None
    assert ms._headline_for("MIXED", comps, **_fresh()) == ms._HEADLINES["MIXED"]
    assert ms._participation_scope("RISK_ON", comps, market="cn", asof=ASOF, input_vintages=_fresh()["input_vintages"]) is None
    assert ms._headline_for("RISK_ON", comps, market="cn", asof=ASOF, input_vintages=_fresh()["input_vintages"]) == ms._HEADLINES["RISK_ON"]


def test_committed_macro_risk_on_thesis_is_participation_qualified():
    """The VPS publishes committed site/macro.html; template-only fixes are not release-complete."""
    import html as html_lib
    import re
    from pathlib import Path

    shipped = (Path(__file__).resolve().parents[1] / "site" / "macro.html").read_text(encoding="utf-8")
    unsafe = "the tape, breadth and cross-asset signals line up"
    assert unsafe not in shipped.lower()

    word_match = re.search(r'id="ms-word"[^>]*>(.*?)</p>', shipped, flags=re.S)
    thesis_match = re.search(r'<p class="v-thesis[^\"]*"[^>]*>(.*?)</p>', shipped, flags=re.S)
    assert word_match is not None
    assert thesis_match is not None

    def visible_text(fragment: str) -> str:
        return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())

    word = visible_text(word_match.group(1))
    thesis = visible_text(thesis_match.group(1))
    if "Risk-on" in word:
        assert (
            thesis.startswith("Broad risk-on")
            or thesis.startswith("Selective risk-on")
            or "participation is unverified" in thesis
        ), thesis


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

    latest = {
        "date": ASOF,
        "conditions": {"vintages": _fresh()["input_vintages"]},
    }
    snap = ms.market_state_snapshot(latest, None, [], profile=profile)

    assert snap is not None
    assert snap["raw_score"] >= 60
    assert snap["score"] == snap["raw_score"]
    assert snap["verdict"] == "RISK_ON"
    assert snap["label_en"] == "Risk-on"
    assert snap["posture_en"] == "Risk-on"
    assert snap["participation_scope"]["state"] == "selective"
    assert snap["participation_scope"]["breadth_score"] == 0
    assert snap["headline_en"].startswith("Selective risk-on")
