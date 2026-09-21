from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_nav_target_and_hk_sector_links_do_not_ship_dead_routes():
    assert (ROOT / "site" / "am_edition.html").exists(), (
        "public nav links am_edition.html from shared chrome, so the committed site "
        "must carry the target even when a narrowed render scope does not rebuild it"
    )

    hk = (ROOT / "templates" / "hk.html.j2").read_text(encoding="utf-8")
    assert 'href="sector_ranking.html"' not in hk
    assert hk.count('href="#sector-rotation"') >= 2
