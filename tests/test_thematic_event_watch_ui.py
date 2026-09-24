from pathlib import Path


def _source(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def test_event_watch_renders_before_zero_thesis_return_and_site_matches_template():
    root = Path(__file__).resolve().parents[1]
    template = _source(root, "templates/ai_desk_thematic.js")
    site = _source(root, "site/ai_desk_thematic.js")

    assert site == template
    watch = "if (brief && brief.emerging_watch && watchEl)"
    empty = "if (!brief || !theses.length)"
    assert template.count(watch) == 1
    assert template.index(watch) < template.index(empty)
    assert "source-bound · context only · unscored" in template
    assert "来源已绑定 · 仅供背景 · 不计分" in template
