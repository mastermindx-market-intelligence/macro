from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shared_render_tree_has_no_known_dead_targets():
    # Shared public chrome links Morning Edition from thousands of pages, so a
    # narrowed render must inherit a committed target even when it does not run
    # build_am_edition itself.
    assert (ROOT / "site" / "am_edition.html").exists()

    # HK already owns an in-page sector rotation board. Do not ship links to the
    # retired/nonexistent sector_ranking.html route from either source or the
    # committed page inherited by unrelated narrowed renders.
    for rel in ("templates/hk.html.j2", "site/hk_stocks.html"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert 'href="sector_ranking.html"' not in text
        assert text.count('href="#sector-rotation"') >= 2
