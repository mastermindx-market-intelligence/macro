"""HK same-session heatmap reuses the existing full-universe quote publisher."""
import json
from scripts import build_live_quotes as live


def test_hk_membership_all_enrolled_before_generic_universe(monkeypatch, tmp_path):
    data = tmp_path / "marketdata"
    data.mkdir()
    data.joinpath("hk_heatmap.json").write_text(json.dumps({
        "market": "hk", "map_type": "stocks", "tiles": [
            {"t": f"{i:04d}.HK"} for i in range(1, 159)
        ],
    }))
    monkeypatch.setattr(live, "CORE_SYMBOLS", ["SPY"])
    monkeypatch.setattr(live, "basket_member_symbols", lambda: ["SPY", "0001.HK"])
    monkeypatch.setattr(live, "scrape_site_symbols", lambda _root: ["AAPL"])
    monkeypatch.setattr(live, "top_conviction", lambda _root, _n: ["MSFT"])
    members = live.heatmap_hk_symbols(tmp_path)
    assert len(members) == 158
    assert members[0] == "0001.HK" and members[-1] == "0158.HK"
    universe = live.build_universe(tmp_path, cap=161)
    assert universe[:3] == ["SPY", "0001.HK", "0002.HK"]
    assert universe[158] == "0158.HK"
    assert universe[159:] == ["AAPL", "MSFT"]
    # The real public browser consumes fast --display, NOT the five-minute
    # private full-universe quotes_full.json.
    monkeypatch.setattr(live, "DISPLAY_SYMBOLS", ["SPY"])
    monkeypatch.setattr(live, "board_display_symbols", lambda _site: ["0001.HK", "MSFT"])
    display = live.display_universe(tmp_path)
    assert display == ["SPY"] + members + ["MSFT"]
    assert len(display) == 160


def test_hk_heatmap_universe_fail_closed_on_missing_or_spoofed_data(tmp_path):
    assert live.heatmap_hk_symbols(tmp_path) == []
    directory = tmp_path / "marketdata"
    directory.mkdir()
    path = directory / "hk_heatmap.json"
    for bad in ('{broken', '[]', json.dumps({"market": "china", "map_type": "stocks", "tiles": [{"t": "0700.HK"}]}),
                json.dumps({"market": "hk", "map_type": "themes", "tiles": [{"t": "0700.HK"}]})):
        path.write_text(bad)
        assert live.heatmap_hk_symbols(tmp_path) == []
    path.write_text(json.dumps({"market": "hk", "map_type": "stocks", "tiles": [
        {"t": "0700.HK"}, {"t": "0700.HK"}, {"t": "../spy.HK"},
        {"t": "=1+1"}, {"t": "AAPL"}, {}, None,
    ]}))
    assert live.heatmap_hk_symbols(tmp_path) == ["0700.HK"]


def test_hk_fast_lane_reuses_incumbent_public_display_snapshot():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    orchestrator = (root / "scripts" / "vps_live_orchestrator.py").read_text(encoding="utf-8")
    quotes = (root / "scripts" / "build_live_quotes.py").read_text(encoding="utf-8")
    # Exactly one existing fast quote writer. No extra feed/daemon or private
    # full-universe artifact accidentally connected to the browser.
    assert '"display_quotes"' in orchestrator
    assert '["--display", "--out", str(self.stage_dir / "quotes.json")]' in orchestrator
    assert "for s in list(DISPLAY_SYMBOLS) + heatmap_hk_symbols(site_dir) + board_display_symbols(site_dir)" in quotes
    assert 'HK_LIVE_URL = \'live/quotes.json\'' in (
        root / "templates" / "heatmap.js"
    ).read_text(encoding="utf-8")
