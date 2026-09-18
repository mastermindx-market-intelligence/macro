from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "sector_heatmap.html.j2"
SITE = ROOT / "site" / "sector_heatmap.html"


def _read_tracked(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT).as_posix()
    return subprocess.check_output(
        ["git", "show", f"HEAD:{rel}"], cwd=ROOT, text=True, encoding="utf-8"
    )


def _atlas_block(path: Path) -> str:
    text = _read_tracked(path)
    start = text.index('  <section class="hta" id="house-theme-atlas"')
    end = text.index('\n\n  <div id="rotation-strip"></div>', start)
    return text[start:end]


def _atlas_script(block: str) -> str:
    match = re.search(r"<script>\s*(\(function\(\)\{.*?\}\)\(\);)\s*</script>", block, re.S)
    assert match, "house Atlas inline script not found"
    return match.group(1)


def test_house_atlas_template_and_rendered_surface_are_identical():
    assert _atlas_block(TEMPLATE) == _atlas_block(SITE)


def test_house_atlas_is_closed_to_house_p1_context_only_sources():
    block = _atlas_block(TEMPLATE)
    assert 'data-observations="basketdata/member_observations.json"' in block
    assert 'data-metadata="basketdata/baskets.json"' in block
    assert "group_member_observations.v1" in block
    assert "obs.authority!=='context_only'" in block
    assert "finviz.com" not in block
    assert "/api/map_perf" not in block


def test_house_atlas_keeps_nulls_and_display_filters_separate_from_measurement():
    block = _atlas_block(TEMPLATE)
    assert "typeof v.value==='number'?v.value:null" in block
    assert "if(x==null||y==null)missing.push(g)" in block
    assert "state.category==='all'||g.category===state.category" in block
    assert "Display filters never recompute the measurements." in block
    assert "visible groups withheld from the plot because an axis value is unavailable" in block


def test_house_atlas_has_four_views_and_no_trade_authority():
    block = _atlas_block(TEMPLATE)
    for view in ("matrix", "clusters", "bubbles", "table"):
        assert f'data-hta-view="{view}"' in block
    assert "Context only" in block
    lowered = block.lower()
    for forbidden in ("prophet score", "buy signal", "position size", "trade gate"):
        assert forbidden not in lowered


def test_house_atlas_bubbles_use_only_accepted_group_metrics():
    block = _atlas_block(TEMPLATE)
    metric_ids = re.findall(r"\['(legacy_activity|strict_trend_50|strict_trend_200)'", block)
    assert set(metric_ids) == {"legacy_activity", "strict_trend_50", "strict_trend_200"}
    assert "state.size==='members'" in block
    assert "member_count" in block
    assert "Circle proximity has no statistical or causal meaning." in block


def test_house_atlas_dynamic_controls_and_table_keep_zh_parity():
    block = _atlas_block(TEMPLATE)
    assert "isZh()?m[2]:m[1]" in block
    assert "'全部分类':'All categories'" in block
    assert "'等面积':'Equal area'" in block
    assert "'成员数量':'Member count'" in block
    assert "isZh()?'主题 / 组别':'Theme / group'" in block
    assert "L(esc(g.category),esc(g.category_zh))" in block


def test_house_atlas_inline_javascript_parses_with_node(tmp_path: Path):
    script = tmp_path / "house_atlas.js"
    script.write_text(_atlas_script(_atlas_block(TEMPLATE)), encoding="utf-8")
    proc = subprocess.run(["node", "--check", str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
