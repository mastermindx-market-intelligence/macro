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
    assert '["--display", "--out", str(self.stage_dir / "quotes.json"),' in orchestrator
    assert '"--hk-heatmap-out", str(self.stage_dir / "hk_heatmap.json")' in orchestrator
    assert '("quotes.json", "hk_heatmap.json")' in orchestrator
    assert "for s in list(DISPLAY_SYMBOLS) + heatmap_hk_symbols(site_dir) + board_display_symbols(site_dir)" in quotes
    assert 'HK_LIVE_URL = \'live/hk_heatmap.json\'' in (
        root / "templates" / "heatmap.js"
    ).read_text(encoding="utf-8")


def test_fast_publisher_preserves_anonymous_allowlist_and_paid_hk_slice(tmp_path, monkeypatch):
    import sys
    from scripts import build_live_quotes as blq

    marketdata = tmp_path / "marketdata"
    marketdata.mkdir()
    (marketdata / "hk_heatmap.json").write_text(json.dumps({
        "market": "hk", "map_type": "stocks", "asof": "2026-10-09",
        "tiles": [{"t": "0001.HK"}, {"t": "0002.HK"}, {"t": "0003.HK"}],
    }))
    monkeypatch.setattr(blq, "DISPLAY_SYMBOLS", ["SPY", "0001.HK"])
    monkeypatch.setattr(blq, "board_display_symbols", lambda _: ["AAPL", "0003.HK"])
    monkeypatch.setattr(blq.config, "load", lambda: {"live": {}, "storage": {"site_dir": "site"}})
    names = ["SPY", "AAPL", "0001.HK", "0002.HK", "0003.HK", "SECRET"]
    stamp = 1791792000000
    def quote():
        return {"source": "yahoo", "basis": "regular", "price": 102.0,
                "prevClose": 100.0, "changePct": 2.0, "ts": stamp,
                "private_provenance": "must-not-leak"}
    fetched = []
    def fake_build(_site, **kwargs):
        fetched.extend(kwargs["symbols"])
        return {"source": "snapshot", "ts": stamp + 60000,
                "quotes": {name: quote() for name in names},
                "meta": {"requested": len(names), "resolved": len(names),
                         "polygon_status": "unused"}}
    monkeypatch.setattr(blq, "build", fake_build)
    public = tmp_path / "public.json"
    gated = tmp_path / "gated.json"
    monkeypatch.setattr(sys, "argv", ["build_live_quotes", "--display",
        "--site", str(tmp_path), "--out", str(public),
        "--hk-heatmap-out", str(gated)])
    blq.main()
    pub, member = json.loads(public.read_text()), json.loads(gated.read_text())
    assert set(fetched) == {"SPY", "AAPL", "0001.HK", "0002.HK", "0003.HK"}
    assert set(pub["quotes"]) == {"SPY", "AAPL", "0001.HK", "0003.HK"}
    assert "0002.HK" not in pub["quotes"]
    assert pub["meta"]["requested"] == pub["meta"]["resolved"] == 4
    assert set(member["quotes"]) == {"0001.HK", "0002.HK", "0003.HK"}
    assert member["baseline_asof"] == "2026-10-09"
    assert member["meta"] == {"requested": 3, "resolved": 3}
    for row in member["quotes"].values():
        assert set(row) == {"source", "basis", "price", "prevClose", "changePct", "ts"}
        assert "private_provenance" not in row
    assert "SECRET" not in member["quotes"]


def test_gated_hk_quote_artifact_is_not_in_caddy_public_matchers():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    caddy = (root / "app/deploy/Caddyfile").read_text()
    access = (root / "config/site_access.yml").read_text()
    public = caddy.split("@vps_public_live {")[1].split("handle @vps_public_live {")[0]
    exemptions = caddy.split("@reg_asset {")[1].split("handle @reg_asset {")[0]
    assert "/live/hk_heatmap.json" not in public
    assert "/live/hk_heatmap.json" not in exemptions
    assert "/live/hk_heatmap.json" not in access
    assert "path /live/* /marketdata/sp500_heatmap.json" in caddy
    assert "handle @reg_asset {" in caddy
    assert "handle @vps_external {" in caddy
