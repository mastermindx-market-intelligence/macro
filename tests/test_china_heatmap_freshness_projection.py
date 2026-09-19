"""China heatmap user-facing freshness projection contract.

The public dead-man sentinel is the canonical freshness verdict. The shared
MMHeatmap renderer must consume it so both the standalone China heatmap and the
embedded Markets-dialog scorecard warn on a definitive stale/blind verdict
without duplicating calendar logic in browser JavaScript.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (ROOT / "templates" / "heatmap.js", ROOT / "site" / "heatmap.js")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_shared_renderer_consumes_existing_public_sentinel() -> None:
    for path in SOURCES:
        src = _source(path)
        assert "/live/staleness.json" in src
        assert "china_heatmap" in src
        assert "active_breach" in src
        assert "blind_surfaces" in src
        assert "cache: 'no-store'" in src
        assert "hm-freshness" in src


def test_freshness_projection_is_hidden_by_default_and_bilingual() -> None:
    src = _source(SOURCES[0])
    assert 'class="hm-freshness" hidden' in src
    assert "Heatmap freshness degraded" in src
    assert "热力图数据可能已过期" in src
    assert "Heatmap freshness check unavailable" in src
    assert "热力图新鲜度校验暂不可用" in src


def test_template_and_served_renderer_remain_identical() -> None:
    assert SOURCES[0].read_bytes() == SOURCES[1].read_bytes()
