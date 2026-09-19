"""China primary-route family-parity rollback guard.

PR #7054 intentionally migrated ``china.html`` alone to the six-block
Archetype-D reference composition.  On 2026-09-19 the Chairman rejected that
standalone production divergence and directed China back to the regional macro
family baseline used before #7054.

The long-term registry archetype is still ``regime_dashboard``.  This file pins
only the *release boundary*: do not strand one primary geography on the new
composition while the US/HK/Canada primary macro routes remain on the existing
family experience.  A later coherent family migration can replace this guard.

The historical filename is retained because ``.github/ci/legacy-jobs.yml``
already routes it through the conviction-profile pack; keeping that wiring avoids
turning a product rollback into a CI-topology change.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "templates" / "china.html.j2").read_text(encoding="utf-8")
REGISTRY = (ROOT / "config" / "product_experience" / "page_registry_overrides.yml").read_text(
    encoding="utf-8"
)
FACTORY = (ROOT / "research" / "DESIGN_MIGRATION_FACTORY_V1.md").read_text(encoding="utf-8")
DESIGN = (ROOT / "research" / "MASTER_PRODUCT_DESIGN_SYSTEM_V1.md").read_text(encoding="utf-8")


def test_primary_china_route_uses_pre_7054_regional_composition():
    """The live macro route keeps the established MX5 regional dashboard shell."""
    assert "MX5 CHINA GLANCE REDESIGN — macro mode" in SRC
    assert 'class="cnx-card cnx-hero' in SRC
    assert 'class="cnx-score-line"' in SRC
    assert 'id="cnx-dlg-read"' in SRC
    assert 'id="cnx-dlg-markets"' in SRC
    assert 'id="cnx-dlg-policy"' in SRC
    assert 'id="cnx-dlg-flows"' in SRC
    assert 'id="cnx-dlg-property"' in SRC
    assert 'id="cnx-dlg-events"' in SRC


def test_standalone_six_block_archetype_d_shell_is_not_on_primary_route():
    """The #7054 five-band/one-hero release shape stays off china.html for now."""
    assert 'class="band-label"' not in SRC
    for hook in ("hero", "todo", "changed", "drivers", "watching-deeper"):
        assert f'data-ev="{hook}"' not in SRC


def test_stock_mode_contract_survives_the_macro_route_rollback():
    """The shared template must keep the A-share stock desk and runtime board wiring."""
    assert "{% if mode == 'stocks' %}" in SRC
    assert "_cn_theme_tape.html.j2" in SRC
    assert "cn_prophet_live.js" in SRC
    assert "mode != 'macro'" in SRC


def test_registry_keeps_future_archetype_but_marks_current_surface_unmigrated():
    """Long-term D architecture and current release state are two different facts."""
    china = REGISTRY[REGISTRY.index("  macro:china:"):REGISTRY.index("  macro:china_history:")]
    assert 'archetype: "regime_dashboard"' in china
    assert 'design_system: {compliant: false' in china
    assert "standalone #7054 migration rolled back" in china


def test_binding_design_sources_record_the_family_parity_gate():
    marker = "Regional primary-route parity gate (Chairman, 2026-09-19)"
    assert marker in FACTORY
    assert marker in DESIGN
    assert "#7054" in FACTORY
    assert "#7054" in DESIGN
