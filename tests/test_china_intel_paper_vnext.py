"""Paper vNext production contract for China Intelligence.

Locks the accepted 1440/820/390 information architecture to the real Jinja route.
Template-first only: no alternate data plane and no generated-page hand editing.
"""
from pathlib import Path
import re

from scripts.build_china_intel import _env

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "china_intel.html.j2"


def _src() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_vnext_route_identity_and_local_tabs_present():
    src = _src()
    assert 'data-ci-vnext="paper-p7-1"' in src
    assert 'class="ci-vnext-tabs"' in src
    for label in ("Overview", "Policy", "Markets", "Sectors", "Companies", "Catalysts"):
        assert label in src


def test_paper_information_architecture_sections_present():
    src = _src()
    for marker in (
        "WHAT MATTERS NOW",
        "FRESHNESS & SOURCES",
        "SURFACE SIGNALS",
        "PRIORITY THREADS",
        "SECTOR / TICKER FOCUS",
        "UPCOMING CATALYSTS",
    ):
        assert marker in src


def test_accepted_map_is_inline_vector_not_an_image_dependency():
    src = _src()
    assert 'class="ci-map"' in src
    assert 'viewBox="0 0 440 142"' in src
    assert "Beijing" in src and "Shanghai" in src and "Shenzhen" in src
    assert "PEOPLE · MARKETS · POLICY · OPPORTUNITY" in src


def test_staleness_copy_is_truthful_worst_age_not_freshest():
    src = _src()
    assert "Oldest data" in src
    assert "Freshest data" not in src


def test_vnext_responsive_contract_has_tablet_and_mobile_breakpoints():
    src = _src()
    assert "@media(max-width:900px)" in src
    assert "@media(max-width:560px)" in src
    assert "grid-template-columns:repeat(3,1fr)" in src
    assert "grid-template-columns:repeat(2,1fr)" in src


def test_existing_machine_inputs_are_still_consumed():
    src = _src()
    assert "b.salience" in src
    assert "b.conviction" in src
    assert "b.surface_asof" in src
    assert "cmd_full.command" in src
    assert "cmd_full.discovery" in src


def _signal_source() -> str:
    src = _src()
    start = src.index('<section class="ci-vnext-signals">')
    end = src.index("</section>", start) + len("</section>")
    return src[start:end]


def test_surface_signal_cards_project_existing_live_schema_values():
    src = _signal_source()
    for field in (
        "b.news.n_events_7d",
        "b.policy.stance_label_en",
        "b.altdata.n_triple",
        "b.radar.n_active",
        "b.special_situations.n_unlocks",
        "cmd_full.command|length",
        "b.conviction|length",
    ):
        assert field in src
    for state in ("active", "measured", "watch", "unavailable"):
        assert 'data-state="' in src
        assert state in src
    assert "b.news.get('band') != 'unknown'" in src
    assert "b.policy.get('pboc_stance')" in src
    assert "n_events_7d or 0" not in src
    assert "n_triple or 0" not in src
    assert "n_active or 0" not in src
    assert "n_unlocks or 0" not in src
    assert "n_inquiry or 0" not in src


def _minimal_b() -> dict:
    return {
        "asof": "2026-09-22",
        "schema": "china_intel.briefing.v6",
        "regime": None,
        "policy": None,
        "news": None,
        "max_staleness_days": None,
        "surfaces_present": [],
        "surface_asof": {},
        "policy_phrase": None,
        "narrative_divergence": None,
        "salience": None,
        "what_changed": None,
        "conviction": None,
        "analysis": None,
        "flagged_tickers": None,
        "special_situations": None,
        "altdata": None,
        "radar": None,
        "analogs": None,
        "digest": None,
    }


def _signal_html(b: dict, cmd_full: dict | None) -> str:
    # Render the exact production source block, not a copied mini-template,
    # while avoiding unrelated deep-page fixture requirements below it.
    prefix = """
{% macro bl(en, zh='') -%}
<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh if zh else en }}</span>
{%- endmacro %}
{% set STANCE_ZH = {'easing':'宽松','neutral':'中性','tightening':'收紧'} %}
"""
    return _env().from_string(prefix + _signal_source()).render(b=b, cmd_full=cmd_full)


def test_surface_signal_missing_metrics_fail_closed_unavailable():
    b = _minimal_b()
    b["news"] = {"band": "unknown", "n_events_7d": None, "asof": "2026-09-22"}
    b["policy"] = {"pboc_stance": None, "asof": "2026-09-22"}
    b["altdata"] = {"n_triple": None, "asof": "2026-09-22"}
    b["radar"] = {"n_active": None, "asof": "2026-09-22"}
    b["special_situations"] = {"n_unlocks": None, "n_inquiry": None, "asof": "2026-09-22"}
    section = _signal_html(b, {"command": None})
    assert section.count('data-state="unavailable"') == 7
    assert section.count("UNAVAILABLE") == 7
    assert "0 triple-signal names" not in section
    assert "0 active divergences" not in section
    assert "0 unlocks" not in section


def test_surface_signal_measured_zero_remains_zero_not_unavailable():
    b = _minimal_b()
    b["news"] = {
        "band": "steady", "band_label_en": "steady", "band_label_zh": "平稳",
        "n_events_7d": 0, "asof": "2026-09-22",
    }
    b["policy"] = {
        "pboc_stance": "neutral", "stance_label_en": "neutral",
        "stance_label_zh": "中性", "asof": "2026-09-22",
    }
    b["altdata"] = {"n_triple": 0, "asof": "2026-09-22"}
    b["radar"] = {"n_active": 0, "asof": "2026-09-22"}
    b["special_situations"] = {"n_unlocks": 0, "n_inquiry": 0, "asof": "2026-09-22"}
    b["conviction"] = []
    section = _signal_html(b, {"command": []})
    assert 'data-state="unavailable"' not in section
    text = re.sub(r"<[^>]+>", "", section)
    for expected in (
        "0 events / 7d",
        "0 triple-signal names",
        "0 active divergences",
        "0 unlocks",
        "0 inquiry letters",
        "0 ranked names",
        "0 sector reads",
    ):
        assert expected in text


def test_no_page_local_duplicate_global_header():
    src = _src()
    assert '<header' not in src.lower()
    assert 'class="ci-sidebar"' not in src
