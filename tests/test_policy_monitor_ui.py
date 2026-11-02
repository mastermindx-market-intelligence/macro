"""Policy Monitor card + dialog — template contract and honesty coverage.

These tests render the REAL dashboard template (templates/dashboard.html.j2)
through the same Jinja environment build_site.py uses, with the display model
produced by lib/policy_monitor_view.py. They pin the DOM contract the redesign
had to preserve, the honesty rules the frozen packet requires, and the
bilingual/theme discipline of the new scoped stylesheet.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import jinja2  # noqa: E402

from engine import i18n  # noqa: E402
from lib import policy_monitor_view as pmv  # noqa: E402
from tests.test_policy_monitor_view import _latest, _policy_lever  # noqa: E402

TEMPLATES = ROOT / "templates"
FACE = TEMPLATES / "_policy_monitor_face.html.j2"
DIALOG = TEMPLATES / "_policy_monitor_dialog.html.j2"
CSS = TEMPLATES / "_policy_monitor.css.j2"


# --------------------------------------------------------------------------- #
# render helpers
# --------------------------------------------------------------------------- #

def _env() -> jinja2.Environment:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.filters["min"] = lambda seq: min(seq)
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    env.globals["pm_view"] = pmv.build_view
    return env


def _vm(policy_lever=None, latest=None, **over) -> dict:
    """A minimal macro view-model. Only the policy inputs matter here."""
    vm = dict(
        latest=latest if latest is not None else {
            "date": "2026-10-30", "quad": "Q4", "quad_name": "Slowdown",
            "label": "Q4 — Slowdown", "confidence": 0.61,
            "fed_stance": None, "dislocation": None, "turning_point": None,
            "risk_radar": None, "rate_inflation_transmission": None,
            "cross_asset_confirm": None, "transition_state": "stable",
            "liquidity_overlay": "neutral", "conditions": None,
            "risk_state": None, "cycle_tag": "late",
        },
        mtf=None, macro_catalysts=[], event_strip=[], event_risk=None,
        prediction_markets=None, narrative_regime=None, ndi=None,
        macro_news=None, macro_brief=None, macro_news_disclaimer="",
        macro_news_disclaimer_zh="", alerts=[], pb=None, month_name="October",
        commodities=[], sector_timing={},
        action_board={"hold": [], "avoid": [], "notable": [], "buy": []},
        top_setups=[], us_standouts={"buy": [], "eligible": 0},
        us_board_outcomes=None, market_gamma=None,
        components_confirming=[], components_contradicting=[],
        flip_plain=None, internals=[], size_style=[], breadth_div=None,
        breadth_panel=None, adv_breadth=None, sector_setups=None,
        generated_utc="2026-10-30 06:00", chart_liquidity=None,
        chart_credit_breadth=None, market_tiles=[], vix=None, chart_vix=None,
        positioning=[], holdings_changes=[], holdings_threshold=5.0,
        accumulation=[], flows_html="", health=[], factor_leadership=None,
        nowcast_hist=None, stance=None, index_health=[], alloc_card=None,
        risk_model=None, chart_risk_model=None, chart_curve=None,
        chart_vix_term=None, cross_asset=None, fear_euphoria=None,
        regime_snap=None, market_state=None, signal_stack=None,
        vol_shock=None, froth_fragility=None, fear_greed=None,
        sector_heat=None, dispersion_regime=None,
        policy_lever=policy_lever,
    )
    vm.update(over)
    return vm


def _render(policy_lever=None, latest=None, mode="macro", **over) -> str:
    return _env().get_template("dashboard.html.j2").render(
        **_vm(policy_lever, latest, **over), mode=mode)


def _panel(html: str, start_id: str, end_id: str) -> str:
    start = html.index(start_id)
    end = html.index(end_id, start + 1)
    return html[start:end]


def _face(html: str) -> str:
    """The Policy Monitor card face, bounded by the next sibling card."""
    start = html.index('id="sx-policy-v2"')
    nxt = html.find('<div class="sx" id="sx-', start + 10)
    return html[start:nxt if nxt > 0 else start + 8000]


# --------------------------------------------------------------------------- #
# DOM contract
# --------------------------------------------------------------------------- #

class TestDomContract:
    def test_the_face_id_is_present_exactly_once(self):
        html = _render(_policy_lever(), _latest())
        assert html.count('id="sx-policy-v2"') == 1

    def test_the_dialog_id_is_present_exactly_once(self):
        html = _render(_policy_lever(), _latest())
        assert html.count('id="dlg-policy"') == 1

    def test_the_inner_consumer_anchor_is_present_exactly_once(self):
        html = _render(_policy_lever(), _latest())
        assert html.count('id="dlg-policy-lever-card"') == 1

    def test_the_dialog_is_named_for_assistive_tech(self):
        html = _render(_policy_lever(), _latest())
        assert 'aria-labelledby="dlg-policy-title"' in html
        assert 'id="dlg-policy-title"' in html

    def test_the_face_still_drives_the_shared_dialog_controller(self):
        html = _render(_policy_lever(), _latest())
        face = _face(html)
        assert "mx5OpenDlg('dlg-policy')" in face
        assert 'aria-haspopup="dialog"' in face
        assert "mx5CloseDlg()" in html

    def test_the_face_keeps_its_keyboard_handler(self):
        html = _render(_policy_lever(), _latest())
        face = _face(html)
        assert "event.key==='Enter'" in face

    def test_the_backdrop_still_closes_through_the_controller(self):
        html = _render(_policy_lever(), _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert 'class="mx5-dlg-backdrop" onclick="mx5CloseDlg()"' in dlg

    def test_no_duplicate_ids_are_introduced_by_the_policy_panel(self):
        html = _render(_policy_lever(), _latest())
        ids = re.findall(r'\sid="([^"]+)"', html)
        dupes = {i for i in ids if ids.count(i) > 1}
        # the estate may already carry legacy duplicates; the policy ids must
        # not add any of their own
        policy_dupes = {i for i in dupes if i.startswith(("dlg-policy", "sx-policy", "plm-"))}
        assert policy_dupes == set()

    def test_the_stocks_surface_carries_no_policy_panel(self):
        html = _render(_policy_lever(), _latest(), mode="stocks")
        assert 'id="sx-policy-v2"' not in html
        assert 'id="dlg-policy"' not in html


# --------------------------------------------------------------------------- #
# honesty rules
# --------------------------------------------------------------------------- #

class TestHonesty:
    def test_the_old_quiet_fallback_copy_is_gone(self):
        html = _render(_policy_lever(state=None), _latest())
        assert "Quiet — no active jawboning" not in html
        assert "Assessment unavailable" in html

    def test_the_old_hawkish_unknown_copy_is_gone(self):
        html = _render(_policy_lever(), _latest())
        assert "Hawkish — unknown" not in html

    def test_unknown_guidance_says_guidance_unavailable(self):
        html = _render(_policy_lever(), _latest())
        assert "Guidance unavailable" in html
        assert "指引不可用" in html

    def test_recorded_alerts_are_not_called_fed_speeches(self):
        html = _render(_policy_lever(), _latest())
        assert "speeches 7d" not in html
        assert "speech this week" not in html
        assert "recorded policy alerts" in html

    def test_an_absent_repricing_field_is_not_reported_as_an_empty_channel_list(self):
        html = _render(_policy_lever(), _latest())
        assert "No repricing channels active today" not in html
        assert "No active channels" not in html
        assert "absent field" in html

    def test_no_literal_number_of_hikes_is_asserted(self):
        html = _render(_policy_lever(), _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert "hikes over the next 12m" not in dlg
        assert "次加息" not in dlg

    def test_the_market_pricing_move_is_reported_in_basis_points(self):
        html = _render(_policy_lever(), _latest())
        assert "+56 bp" in html
        assert "+56 基点" in html

    def test_a_zero_recorded_count_renders_as_zero(self):
        html = _render(_policy_lever(), _latest())
        assert "Recorded policy alerts: 0 (7d)" in html

    def test_a_missing_arming_block_does_not_render_as_quiet(self):
        html = _render(_policy_lever(), _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert "Observed: Not observed" in dlg
        assert "no technical asset" in dlg

    def test_the_conditions_state_and_the_evidence_condition_are_separate(self):
        html = _render(_policy_lever(), _latest())
        assert "Evidence:" in html
        assert "One condition is met" in html

    def test_the_countdown_is_marked_as_a_count_not_a_live_clock(self):
        html = _render(_policy_lever(), _latest())
        assert "calculation date unavailable" in html

    def test_the_stale_narrative_is_flagged_next_to_the_copy(self):
        html = _render(_policy_lever(), _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert "Narrative last reviewed 2026-07-18" in dlg
        assert "stale" in dlg

    def test_the_sources_disclosure_is_present(self):
        html = _render(_policy_lever(), _latest())
        assert "sep_vs_market_year_end.v1" in html
        assert "ZQ fed-funds futures" in html
        assert "fred:FEDTARMD" in html

    def test_no_source_link_is_invented(self):
        html = _render(_policy_lever(), _latest())
        assert "http://" not in _panel(html, 'id="dlg-policy"', "</body>")


# --------------------------------------------------------------------------- #
# chart + table
# --------------------------------------------------------------------------- #

class TestRatesPanel:
    def test_the_chart_has_an_accessible_name_and_description(self):
        html = _render(_policy_lever(), _latest())
        assert 'role="img"' in html
        assert 'aria-labelledby="plm-chart-title"' in html
        assert 'aria-describedby="plm-chart-desc"' in html

    def test_the_equivalent_values_table_is_present(self):
        html = _render(_policy_lever(), _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert '<table class="plm-table">' in dlg
        for horizon in ("1 month", "3 months", "6 months", "12 months"):
            assert horizon in dlg

    def test_the_axis_carries_percent_units_and_a_horizon_title(self):
        html = _render(_policy_lever(), _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert "Fed funds rate (%)" in dlg
        assert "Horizon (months)" in dlg

    def test_the_legend_names_every_series(self):
        html = _render(_policy_lever(), _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert "Market-implied rate" in dlg
        assert "SEP year-end projection" in dlg
        assert "Target range midpoint" in dlg

    def test_the_supporting_rail_carries_the_three_qualified_facts(self):
        html = _render(_policy_lever(), _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert "12-month market rate" in dlg
        assert "Fed projection comparison" in dlg
        assert "-14 bp at end-2026" in dlg

    def test_the_fed_projection_table_is_tabulated_by_year(self):
        html = _render(_policy_lever(), _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert "Fed projections by year" in dlg
        assert "Tabulated by year" in dlg

    def test_a_missing_horizon_is_shown_as_a_gap_in_the_chart(self):
        fp = _latest()["fed_path"]
        fp["implied"]["m3"] = None
        html = _render(_policy_lever(), _latest(fed_path=fp))
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert "not available" in dlg
        assert "plm-gapmark" in dlg
        assert "3.00%" not in dlg  # a gap is never drawn as a zero reading

    def test_the_rate_axis_text_uses_a_text_token_not_translucent_white(self):
        """The old chart painted axis labels rgba(255,255,255,.36) — invisible
        on the light panel. The new axis text is a theme text token."""
        for path in (CSS, DIALOG, FACE):
            body = path.read_text(encoding="utf-8")
            assert "rgba(255,255,255" not in body, path.name
        css = CSS.read_text(encoding="utf-8")
        assert ".plm-axis-text{" in css
        assert "fill:var(--muted)" in css


# --------------------------------------------------------------------------- #
# degradation
# --------------------------------------------------------------------------- #

class TestDegradation:
    def test_source_text_is_inert_in_the_production_autoescape_environment(self):
        pl = _policy_lever()
        pl["levers"][0]["watch"] = '<img src=x onerror="window.policyInjected=true">'
        html = _render(pl, _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert '<img src=x onerror=' not in dlg
        assert '&lt;img src=x onerror=' in dlg

    def test_policy_disclosures_participate_in_the_existing_focus_trap(self):
        body = DIALOG.read_text(encoding="utf-8")
        assert '<summary>' not in body
        assert body.count('<summary tabindex="0">') >= 4

    def test_undated_sep_is_retained_as_an_unqualified_reference(self):
        fp = _latest()["fed_path"]
        fp["implied_source_meta"]["dots"]["vintage"] = None
        html = _render(_policy_lever(), _latest(fed_path=fp))
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert 'Publication date unavailable' in dlg
        assert 'Comparison unavailable' in dlg
        assert '-14 bp at end-2026' not in dlg
        assert '<polygon class="plm-dot-marker"' not in dlg

    def test_current_rate_survives_a_missing_futures_path(self):
        fp = _latest()["fed_path"]
        fp["implied"] = {}
        html = _render(_policy_lever(), _latest(fed_path=fp))
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert 'Target range midpoint' in dlg
        assert '3.88%' in dlg

    def test_an_all_null_policy_lever_renders_without_a_calm_claim(self):
        pl = {"schema": "policy_lever.v1"}
        html = _render(pl, {"date": "2026-10-30", "fed_path": {}, "fed_stance": None})
        assert 'id="sx-policy-v2"' in html
        assert "Assessment unavailable" in html
        assert "Market-implied path unavailable" in html

    def test_a_malformed_lever_row_does_not_break_the_panel(self):
        pl = _policy_lever()
        pl["levers"].append({"name": "Broken", "arming": "not-a-mapping"})
        html = _render(pl, _latest())
        assert 'id="dlg-policy"' in html
        assert "Observed: Not observed" in html

    def test_a_malformed_fed_path_does_not_break_the_panel(self):
        lt = _latest()
        lt["fed_path"] = {"implied": {"m3": float("nan"), "m6": True}, "dots": "nope"}
        html = _render(_policy_lever(), lt)
        assert 'id="dlg-policy"' in html

    def test_a_non_comparable_basis_suppresses_the_spread(self):
        fp = _latest()["fed_path"]
        fp["implied_source_meta"]["gap"]["status"] = "not_comparable"
        html = _render(_policy_lever(), _latest(fed_path=fp))
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        assert "Comparison unavailable" in dlg
        assert "-14 bp at end-2026" not in dlg


# --------------------------------------------------------------------------- #
# bilingual + theme discipline
# --------------------------------------------------------------------------- #

class TestBilingual:
    def test_every_policy_label_has_a_zh_twin(self):
        html = _render(_policy_lever(), _latest())
        dlg = _panel(html, 'id="dlg-policy"', "</body>")
        en = re.findall(r'<span class="l-en">([^<]{2,})</span>', dlg)
        zh = re.findall(r'<span class="l-zh">([^<]{2,})</span>', dlg)
        assert len(en) == len(zh)
        assert len(en) > 40

    def test_the_face_is_bilingual(self):
        html = _render(_policy_lever(), _latest())
        face = _face(html)
        assert "One condition is met" in face
        assert "一项条件成立" in face

    def test_no_chinese_text_leaks_into_a_title_attribute(self):
        html = _render(_policy_lever(), _latest())
        for value in re.findall(r'title="([^"]*)"', html):
            assert not [c for c in value if "一" <= c <= "鿿"], value


class TestScopedStylesheet:
    @staticmethod
    def _css_body() -> str:
        """The stylesheet with its Jinja comment block removed."""
        css = CSS.read_text(encoding="utf-8")
        return re.sub(r"\{#.*?#\}", "", css, flags=re.S)

    def test_the_stylesheet_declares_no_colour_literal(self):
        body = self._css_body()
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", body)
        assert not re.search(r"\b(?:rgba?|hsla?|color-mix|oklch|oklab|hwb)\s*\(", body)

    def test_the_stylesheet_declares_no_radius_literal(self):
        for m in re.finditer(r"border-radius\s*:\s*([^;}\n]+)", self._css_body()):
            value = m.group(1).strip()
            assert "var(--r-" in value, value

    def test_the_stylesheet_declares_no_parallel_token_root(self):
        assert ":root" not in self._css_body()

    def test_the_stylesheet_declares_no_new_literal_custom_property(self):
        for m in re.finditer(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;}\n]+)", self._css_body()):
            name, value = m.group(1), m.group(2).strip()
            assert value.startswith("var("), f"{name}: {value}"

    def test_the_light_art_direction_is_authored_not_only_swapped(self):
        css = CSS.read_text(encoding="utf-8")
        # the panel/axis tokens are theme tokens, so light resolves through
        # theme.css — but the scoped sheet must still carry its own light
        # counterpart for the pieces that differ.
        assert "[data-theme=\"light\"]" in css

    def test_the_policy_markup_lives_outside_the_dashboard_template(self):
        dash = (TEMPLATES / "dashboard.html.j2").read_text(encoding="utf-8")
        assert "plx-state-hero" not in dash
        assert "plx-lever-row" not in dash
        assert '{% include "_policy_monitor_face.html.j2" %}' in dash
        assert '{% include "_policy_monitor_dialog.html.j2" %}' in dash
        assert '{% include "_policy_monitor.css.j2" %}' in dash

    def test_the_fragment_files_exist_and_are_non_trivial(self):
        for path in (FACE, DIALOG, CSS):
            assert path.exists()
            assert len(path.read_text(encoding="utf-8")) > 2000



class TestIntegratedProducerRendering:
    def test_partial_activity_and_past_election_reach_the_real_dialog(self, tmp_path):
        from datetime import datetime, timezone
        from scripts.build_policy_lever import _compute_calendar, _compute_jawboning
        path = tmp_path / 'alerts.jsonl'
        path.write_text('broken line\n{"published":"2026-11-03T12:00:00Z","summary":"Observed alert"}\n')
        evaluation = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
        pl = _policy_lever(calendar=_compute_calendar(now=evaluation),
                           jawboning=_compute_jawboning(path, now=evaluation))
        html = _render(pl, _latest())
        dlg = _panel(html, 'id="dlg-policy"', '</body>')
        assert 'valid records only' in dlg
        assert 'ending 2026-11-04 (UTC)' in dlg
        assert 'Scheduled date passed: 2026-11-03' in dlg
        assert '预定日期已过' in dlg
        assert 'Observed alert' in dlg
        assert 'Fed guidance' in dlg
        assert 'Technical observation · 2026-10-30' in dlg
