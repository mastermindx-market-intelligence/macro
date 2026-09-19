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


def test_rollback_preserves_orthogonal_truth_and_accessibility_fixes():
    """Do not throw away #7054 fixes that were independent of its rejected L1 shell."""
    # The markets dialog must actually retain the first CNH/CGB tile found in a
    # Jinja loop and explain the inverted USD/CNH quote orientation.
    assert "namespace(tile=none)" in SRC
    assert "_cnh_ns.tile" in SRC and "_cgb_ns.tile" in SRC
    assert "_cnh.meaning_en" in SRC and "_cnh.meaning_zh" in SRC
    assert "cnx-orient" in SRC

    # Multi-timeframe rows use the producer's named D/W/M cells rather than
    # positional score indexes, and labels keep EN/ZH parity.
    assert "ix.cells or {}" in SRC
    assert "ix.label_en or ix.label" in SRC
    assert "_cells.D" in SRC and "_cells.W" in SRC and "_cells.M" in SRC

    # Restored cards keep an actual keyboard focus outline, not box-shadow only.
    assert "sxg-face.mx5-card-face:focus-visible" in SRC
    assert "mx5-mkt-tile:focus-visible" in SRC
    assert "outline:2px solid color-mix(in srgb, var(--link) 70%, transparent)" in SRC

    # Light mode really disables the dark aurora regardless of whether the
    # theme attribute sits on html or body, and dark aurora stays behind content.
    assert "pointer-events:none;z-index:-1;overflow:hidden" in SRC
    assert 'html[data-theme="light"] body.page-china .aurora::before' in SRC
    assert "display:none !important;background:none !important" in SRC

    # Locale correctness retained from #7054.
    assert "{% macro cny_yi_pair(n)" in SRC
    assert "'Neutral':'中性'" in SRC


def test_rollback_keeps_dialog_truth_without_six_block_shell():
    """Modal detail keeps corrected semantics even though L1 returns to the family shell."""
    assert "signal_stack.agreement_pct" in SRC
    assert "t('Signal agreement','信号一致度')" not in SRC
    assert "Driver table unavailable — the index rows are not ready." in SRC
    assert "驱动表暂不可用 — 指数行尚未就绪。" in SRC


def _registry_page_block(page_id: str) -> str:
    marker = f"  {page_id}:\n"
    start = REGISTRY.index(marker)
    rest = REGISTRY[start + len(marker):]
    # Top-level page keys are exactly two-space-indented; nested mappings are deeper.
    ends = [i for i, line in enumerate(rest.splitlines(True)) if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":")]
    if not ends:
        return rest
    return "".join(rest.splitlines(True)[:ends[0]])


def test_primary_regional_family_migration_is_atomic():
    """A normal geography route may not become the lone design-system migration again."""
    primary = ("macro:macro", "macro:china", "macro:hk", "macro:canada")
    states = {
        page_id: "design_system: {compliant: true" in _registry_page_block(page_id)
        for page_id in primary
    }
    assert len(set(states.values())) == 1, (
        "primary regional macro routes must migrate together; "
        f"partial design-system state: {states}"
    )


def test_rollback_keeps_honest_live_quote_loading():
    """Live-only index cells load honestly and do not strand a permanent bare dash."""
    for sym in ("000300.SS", "399006.SZ"):
        assert f'data-sym="{sym}" data-mkt="cn" data-bare aria-busy="true"' in SRC
    assert "mx5-mkt-price nb-px mx-skel" in SRC
    assert "function cnxSkelFallback()" in SRC
    assert "No quote" in SRC and "暂无报价" in SRC
    assert "the tape is still catching up" in SRC and "行情仍在同步" in SRC
