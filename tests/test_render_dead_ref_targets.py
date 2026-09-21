from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_nav_target_and_hk_sector_links_do_not_ship_dead_routes():
    assert (ROOT / "site" / "am_edition.html").exists(), (
        "public nav links am_edition.html from shared chrome, so the committed site "
        "must carry the target even when a narrowed render scope does not rebuild it"
    )

    sector_alias = ROOT / "site" / "sector_ranking.html"
    assert sector_alias.exists(), (
        "HK stock chrome links sector_ranking.html, so the compatibility target "
        "must remain committed even when a narrowed render scope does not run build_hk"
    )
    alias = sector_alias.read_text(encoding="utf-8")
    assert "hk_stocks.html#sector-rotation" in alias
    hk_stocks = (ROOT / "site" / "hk_stocks.html").read_text(encoding="utf-8")
    assert 'id="sector-rotation"' in hk_stocks
