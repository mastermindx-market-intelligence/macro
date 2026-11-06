from pathlib import Path

from scripts.check_crypto_shelves import audit_text


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "vector.html.j2"


def test_wave1_structure_is_exact_and_verdict_is_singular():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert audit_text(
        source,
        tuple(f"S{i}" for i in range(1, 7)),
        1,
    ) == []


def test_wave1_uses_house_theme_and_signal_ink_without_legacy_skin_or_plotly():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert 'href="theme.css"' in source
    assert 'href="illus.css"' in source
    assert 'src="illus.js"' in source
    assert "_vector_polish" not in source
    assert "_plotly_head" not in source
    assert "Plotly" not in source


def test_wave1_keeps_both_advanced_interactive_instruments():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="vtm"' in source
    assert 'id="vtm-canvas"' in source
    assert 'src="vector_timemachine.js?v=2"' in source
    assert 'id="vec-risk-chart"' in source
    assert 'src="lightweight-charts-v5.js"' in source
    assert 'src="vector_chart.js"' in source


def test_wave1_front_door_avoids_banned_internal_language_and_alert_chrome():
    source = TEMPLATE.read_text(encoding="utf-8").lower()
    for banned in ("validated", "falsifier", "refuted", "证伪"):
        assert banned not in source
    assert "recent alerts" not in source
    assert 'href="alerts.html"' in source


def test_wave1_has_exactly_six_driver_rows_by_contract_loop():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert "{% for row in presentation.axes %}" in source
    builder = (ROOT / "scripts" / "build_vector.py").read_text(encoding="utf-8")
    assert "COCKPIT_AXIS_PRESENTATION" in builder


def test_wave1_arms_payload_budget_and_desktop_nav_containment():
    source = TEMPLATE.read_text(encoding="utf-8")
    builder = (ROOT / "scripts" / "build_vector.py").read_text(encoding="utf-8")
    assert "nth-last-child(3)" in source
    assert 're.sub(r">\\s+<", "> <", html)' in builder
    assert 'len(html.encode("utf-8"))' in builder


def test_r2_decision_fragment_does_not_require_overview_context():
    """The canonical decision can render without quotes, charts or market master data."""
    from jinja2 import Environment

    source = TEMPLATE.read_text(encoding="utf-8")
    macros = source[:source.index("<!DOCTYPE html>")]
    start = source.index("{% set decision_ok")
    end = source.index('<section class="shelf" data-shelf="S3">', start)
    fragment = Environment(autoescape=True).from_string(macros + source[start:end])
    available = {
        "schema": "btc.decision/v1",
        "status": "ok",
        "integrity": {"ok": True},
        "final": {
            "action_code": "HOLD_EXPOSURE",
            "action_en": "Hold Bitcoin",
            "action_zh": "持有比特币",
            "exposure_pct": 75,
            "change_pp": 0,
        },
        "advisory": {"levels": {}},
    }
    unavailable = {
        "schema": "btc.decision/v1",
        "status": "unavailable",
        "integrity": {"ok": False},
        "final": None,
        "advisory": {"levels": {}},
    }
    for decision in (available, unavailable):
        rendered = fragment.render(
            decision=decision, risk_index=19, risk_label="Low Risk", risk_on=True,
        )
        assert "hero-position" not in rendered
        assert "vec-risk-chart" not in rendered
        assert rendered.count("data-verdict") == 1
        if decision["status"] == "ok":
            assert 'data-decision-exposure="75"' in rendered
        else:
            assert "DECISION TEMPORARILY UNAVAILABLE" in rendered
            assert "data-decision-exposure=" not in rendered


def test_r2_performance_stays_in_strategy_not_the_current_decision():
    source = TEMPLATE.read_text(encoding="utf-8")
    overview_start = source.index('id="overview"')
    decision_start = source.index('data-shelf="S2"')
    overview = source[overview_start:decision_start]
    assert 'id="vec-risk-chart"' in overview
    assert 'id="vrc-score"' not in overview
    assert source.count('id="vrc-score"') == 1
    assert source.index('id="vrc-score"') > source.index('id="strategy-track-record"')
    assert "Full-history simulation, not live performance." in source


def test_r2_nav_accessible_name_is_text_not_bilingual_markup():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert 'aria-label="Bitcoin research sections / 比特币研究分区"' in source
    assert 'aria-label="{{ t(' not in source


def test_r2_missing_market_read_is_not_mixed_evidence():
    from jinja2 import Environment

    source = TEMPLATE.read_text(encoding="utf-8")
    macros = source[:source.index("<!DOCTYPE html>")]
    start = source.index('<h1 class="stance">')
    end = source.index("</h1>", start) + len("</h1>")
    rendered = Environment(autoescape=True).from_string(macros + source[start:end]).render(
        master={"ok": False}, hero_tone="neutral",
    )
    assert "Market read unavailable." in rendered
    assert "Mixed backdrop." not in rendered
