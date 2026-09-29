from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "china.html.j2"
RENDERED = ROOT / "site" / "china.html"

SECTOR_TICKERS = (
    "512200.SS",  # Real Estate
    "512170.SS",  # Healthcare
    "512800.SS",  # Banks
    "512660.SS",  # Defense & Military
    "512760.SS",  # Semiconductors
    "159992.SZ",  # Innovative Drugs
    "515250.SS",  # Automobiles
    "515220.SS",  # Coal
    "159928.SZ",  # Consumer Staples
    "512980.SS",  # Media
    "515790.SS",  # Solar & Photovoltaic
    "512690.SS",  # Baijiu & Liquor
    "512880.SS",  # Securities & Brokers
    "515030.SS",  # New-Energy Vehicle
    "515000.SS",  # Technology
    "512400.SS",  # Nonferrous Metals
)


def _sector_dialog(html: str) -> str:
    start = html.index('<!-- Sector dialog -->')
    end = html.index('<!-- Policy dialog -->', start)
    return html[start:end]


def test_china_template_wires_every_sector_name_surface_to_detail_pages() -> None:
    """The China dashboard exposes sector names in every sector-focused surface.

    Keep all of them on the canonical generated sector-detail family rather than
    letting chips/table rows regress into inert text.
    """
    src = TEMPLATE.read_text(encoding="utf-8")

    # x.ticker: Sector Temperature hot/buy chips + dialog buy/avoid/leader chips.
    assert src.count('href="sectors/{{ x.ticker }}.html"') == 5

    # s.ticker: risk-dialog leaders/laggards + Rotation-vs-CSI-300 table.
    assert src.count('href="sectors/{{ s.ticker }}.html"') == 3

    # The overview card itself opens the dialog, so its nested links must not
    # bubble and steal the user's sector-detail navigation.
    assert src.count('onclick="event.stopPropagation()"') >= 2
    assert "body.page-china .cnx-sector-link:hover" in src
    assert "click a sector for its detail page" in src


def test_rendered_china_sector_dialog_links_current_sector_universe() -> None:
    html = RENDERED.read_text(encoding="utf-8")
    dlg = _sector_dialog(html)

    # Every current dashboard sector has a real generated detail page and at
    # least one direct link in the sector dialog.
    for ticker in SECTOR_TICKERS:
        assert f'href="sectors/{ticker}.html"' in dlg

    # Current action chips and the visible rotation-table sector names are links,
    # not inert span-only controls.
    assert '<span class="cnx-chip turn">' not in dlg
    assert '<span class="cnx-chip hot">' not in dlg

    top10 = SECTOR_TICKERS[:10]
    for ticker in top10:
        assert f'<td><a class="cnx-sector-link" href="sectors/{ticker}.html">' in dlg
