"""Contracts for the compact macro.html "What To Do Now" glance."""

from pathlib import Path

import jinja2


ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "templates" / "dashboard.html.j2"


def _glance_source() -> str:
    source = DASH.read_text(encoding="utf-8")
    start = source.index('{# Three-priority glance.')
    end = source.index("</div>{# /sx-evidence #}", start)
    return source[start:end]


def _render_glance(
    *, catalysts=True, policy_state="QUIET", risk_elevated=True,
    color="yellow", participation_scope=None, qualified_quiet=True,
) -> str:
    state = {
        "color": color,
        "label_en": "Risk-on" if color == "green" else "Mixed",
        "label_zh": "风险偏好" if color == "green" else "混合",
        "score": 61 if color == "green" else 44,
        "participation_scope": participation_scope,
        "radar": {
            "state": "ELEVATED" if risk_elevated else "QUIET",
            "do_en": "Avoid chasing extended leaders.",
            "do_zh": "避免追逐过度延伸的领涨股。",
        },
    }
    events = (
        [{"label": "FOMC rate decision", "label_zh": "FOMC 利率决议", "impact": "high"}]
        if catalysts
        else []
    )
    # This fragment now uses the same foreground presentation macro as the full
    # page. Supply the real dependency, not a stub. The default quiet envelope
    # isolates the established three-row/participation contracts; separate tests
    # exercise missing/qualified-warning context and its visible precedence.
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / "templates"), autoescape=True)
    source = '{% from "_risk_envelope_band.html.j2" import risk_foreground %}' + _glance_source()
    quiet = {"schema":"mastermind.risk_envelope/v1", "market":"US", "source_session":"2026-10-14",
             "hazard_summary":{"stage":"NONE", "contributing_sources":[]}, "measured_state":{"usable":True}}
    return environment.from_string(source).render(
        risk_envelope=quiet if qualified_quiet else None,
        _risk_fg_expected="2026-10-14",
        market_state=state,
        MS=state,
        macro_catalysts=events,
        _weakest={"label_en": "Volatility", "label_zh": "波动率", "score": 48},
        PL={"state": policy_state},
        _mx5_risk_elevated=risk_elevated,
    )


def _visible_primary(html):
    import re
    return re.search(r'data-wtd-primary.*?<div class="mx5-action-label"[^>]*>(.*?)</div>', html, re.S)[1]


def test_glance_is_capped_at_three_rendered_rows():
    """The face stays a decision glance instead of growing back into a report."""
    html = _render_glance()
    assert html.count('class="mx5-action-item') == 3
    assert "data-wtd-primary" in html
    assert "Trade small. Stay selective." in _visible_primary(html)
    assert "FOMC rate decision: expect noise; ignore the first move." in html
    assert "Avoid chasing extended leaders." in html


def test_active_policy_takes_the_third_priority_slot():
    html = _render_glance(policy_state="ARMED")
    assert html.count('class="mx5-action-item') == 3
    assert "Watch for policy repricing." in html
    assert "Avoid chasing extended leaders." not in html


def test_weakest_leg_replaces_event_when_calendar_is_empty():
    html = _render_glance(catalysts=False)
    assert html.count('class="mx5-action-item') == 3
    assert "Volatility (48/100)." in html
    assert "expect noise" not in html


def test_quiet_policy_copy_does_not_consume_a_glance_row():
    """Only active policy conditions deserve one of the three priority slots."""
    glance = _glance_source()
    assert "Policy is quiet" not in glance
    assert "No active jawboning" not in glance
    assert "PL.get('state') in ('ARMED','ELEVATED')" in glance


def test_primary_copy_is_short_and_live_patchable():
    glance = _glance_source()
    assert "Trade small. Stay selective." in glance
    assert "{{ MS.label_en }} &middot; {{ MS.score }}/100" in glance


def test_primary_copy_is_participation_aware_in_selective_risk_on():
    html = _render_glance(
        color="green",
        participation_scope={
            "state": "selective",
            "participation": "weak",
            "breadth_score": 0,
            "action_en": "Stay selective. Follow confirmed leadership and fresh turns.",
            "action_zh": "保持精选。跟随已确认的强势板块与新出现的转强信号。",
            "subline_en": "GREEN — Selective risk-on",
            "subline_zh": "偏多 — 选择性风险偏好",
        },
    )

    assert "Stay selective. Follow confirmed leadership and fresh turns." in _visible_primary(html)
    assert "Follow the trend. Add on strength." not in html


def test_glance_uses_the_dashboard_typography_without_alert_labels():
    """The compact face should read like the surrounding cards, not an alert feed."""
    source = DASH.read_text(encoding="utf-8")
    start = source.index("/* ── WHAT TO DO (three-priority glance")
    end = source.index("/* ── UPCOMING EVENTS", start)
    css = source[start:end]
    html = _render_glance()

    assert "font-weight:500" in css
    assert "font-weight:560" not in css
    assert "font-weight:720" not in css
    assert "font-weight:760" not in css
    assert "text-transform:uppercase" not in css
    assert "mx5-action-verb" not in html


def test_missing_risk_context_is_not_permission_to_add_risk():
    html = _render_glance(color="green", qualified_quiet=False)
    assert "Verify conditions before adding risk." in _visible_primary(html)
    assert "Add where setups confirm." not in _visible_primary(html)
    assert html.count('class="mx5-action-item') == 3
