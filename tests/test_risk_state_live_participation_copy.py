from __future__ import annotations

from scripts import build_risk_state as brs


def _block(breadth_score):
    components = []
    if breadth_score is not None:
        components.append({"key": "breadth", "score": breadth_score})
    return {"components": components}


def test_display_copy_uses_canonical_market_state_scope_for_weak_breadth():
    copy = brs._display_participation_copy("RISK_ON", _block(0))

    assert copy["participation_scope"]["state"] == "selective"
    assert copy["participation_scope"]["participation"] == "weak"
    assert copy["headline_en"].startswith("Selective risk-on")
    assert "broad rally" in copy["headline_en"]


def test_display_copy_fails_closed_when_breadth_is_unavailable():
    copy = brs._display_participation_copy("RISK_ON", _block(None))

    assert copy["participation_scope"]["state"] == "unverified"
    assert "participation is unverified" in copy["headline_en"]


def test_display_copy_does_not_reinterpret_non_risk_on():
    copy = brs._display_participation_copy("MIXED", _block(0))

    assert copy["participation_scope"] is None
    assert copy["headline_en"].startswith("Mixed / transition")
