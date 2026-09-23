from __future__ import annotations

from scripts import build_risk_state as brs


ASOF = "2026-09-18"


def _snapshot(
    breadth_score,
    *,
    asof: str = ASOF,
    vintage_asof: str | None = None,
    stale: bool = False,
    degraded: bool = False,
):
    components = []
    if breadth_score is not None:
        components.append({
            "key": "breadth",
            "score": breadth_score,
            "degraded": degraded,
        })
    return {
        "market": "us",
        "asof": asof,
        "components": components,
        "input_vintages": {
            "pct_above_200": {
                "asof": vintage_asof or asof,
                "stale": stale,
            }
        },
    }


def test_display_copy_uses_canonical_market_state_scope_for_weak_breadth():
    copy = brs._display_participation_copy("RISK_ON", _snapshot(0))

    assert copy["participation_scope"]["state"] == "selective"
    assert copy["participation_scope"]["participation"] == "weak"
    assert copy["participation_scope"]["breadth_asof"] == ASOF
    assert copy["headline_en"].startswith("Selective risk-on")
    assert "broad rally" in copy["headline_en"]


def test_display_copy_fails_closed_when_breadth_is_unavailable():
    copy = brs._display_participation_copy("RISK_ON", _snapshot(None))

    assert copy["participation_scope"]["state"] == "unverified"
    assert "participation is unverified" in copy["headline_en"]


def test_display_copy_fails_closed_on_stale_or_wrong_session_breadth():
    for source in (
        _snapshot(75, stale=True),
        _snapshot(75, vintage_asof="2026-09-17"),
        _snapshot(75, degraded=True),
    ):
        copy = brs._display_participation_copy("RISK_ON", source)
        assert copy["participation_scope"]["state"] == "unverified"
        assert "participation is unverified" in copy["headline_en"]


def test_display_copy_uses_debounced_display_verdict_not_source_verdict():
    source = _snapshot(0)
    source["verdict"] = "RISK_ON"

    copy = brs._display_participation_copy("MIXED", source)

    assert copy["participation_scope"] is None
    assert copy["headline_en"].startswith("Mixed / transition")


def test_verdict_transport_preserves_canonical_scope_for_closed_live_fallback():
    source = _snapshot(0)
    source.update({
        "verdict": "RISK_ON",
        "score": 61,
        "raw_score": 61,
        "color": "green",
        "label_en": "Risk-on",
        "label_zh": "风险偏好",
        "headline_en": "Selective risk-on — test",
        "headline_zh": "选择性风险偏好 — 测试",
        "participation_scope": brs.market_state._participation_scope(
            "RISK_ON",
            source["components"],
            market="us",
            asof=source["asof"],
            input_vintages=source["input_vintages"],
        ),
    })

    block = brs._verdict_block(source)

    assert block["label_en"] == "Risk-on"
    assert block["participation_scope"]["state"] == "selective"
    assert block["participation_scope"]["breadth_asof"] == ASOF


def test_display_projection_selects_full_nightly_snapshot_when_closed():
    nightly = _snapshot(0)
    live = _snapshot(75)

    copy = brs._display_participation_copy_for_sources(
        "RISK_ON",
        live_active=False,
        live_snapshot=live,
        nightly_snapshot=nightly,
    )

    assert copy["participation_scope"]["state"] == "selective"
    assert copy["participation_scope"]["participation"] == "weak"
    assert copy["headline_en"].startswith("Selective risk-on")


def test_display_projection_selects_full_live_snapshot_when_active():
    nightly = _snapshot(0)
    live = _snapshot(75)

    copy = brs._display_participation_copy_for_sources(
        "RISK_ON",
        live_active=True,
        live_snapshot=live,
        nightly_snapshot=nightly,
    )

    assert copy["participation_scope"]["state"] == "broad"
    assert copy["participation_scope"]["participation"] == "supportive"
    assert copy["headline_en"].startswith("Broad risk-on")
