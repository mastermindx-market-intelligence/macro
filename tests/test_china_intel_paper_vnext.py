"""Paper vNext production contract for China Intelligence.

Locks the accepted 1440/820/390 information architecture to the real Jinja route.
Template-first only: no alternate data plane and no generated-page hand editing.
"""
from pathlib import Path

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


def test_no_page_local_duplicate_global_header():
    src = _src()
    assert '<header' not in src.lower()
    assert 'class="ci-sidebar"' not in src
