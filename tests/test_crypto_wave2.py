from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from collectors.crypto_misc import CryptoUniverseAdapter
from engine.btc_decision import build_decision
from engine.crypto_market_state import build_market_state
from engine.crypto_universe import breadth_read, load_universe
from scripts import build_crypto, build_vector

ROOT = Path(__file__).resolve().parent.parent


def test_crypto_template_has_exact_governed_shelves():
    text = (ROOT / "templates" / "crypto.html.j2").read_text(encoding="utf-8")
    shelves = re.findall(r'data-shelf="([^"]+)"', text)
    assert shelves == [f"H{i}" for i in range(1, 9)]
    assert "plotly" not in text.lower()


def test_crypto_build_is_lightweight_and_live_wired(tmp_path):
    site = tmp_path / "site"
    site.mkdir(parents=True, exist_ok=True)
    signals = build_crypto.store.read("vector", "signals")
    assert signals is not None and not signals.empty
    decision = _decision_projection(
        60,
        as_of=str(pd.Timestamp(signals.index[-1]).date()),
    )
    (site / "crypto_cockpit.json").write_text(
        json.dumps(
            {
                "decision": decision,
                "hero": {
                    "stance_en": "Constructive",
                    "stance_zh": "偏积极",
                    "exposure_pct": 60,
                },
                "axes": [],
            }
        )
    )
    output = build_crypto.build(site)
    html = output.read_text(encoding="utf-8")
    assert output.stat().st_size < 200 * 1024
    assert re.findall(r'data-shelf="([^"]+)"', html) == [f"H{i}" for i in range(1, 9)]
    assert html.count('class="market-row tone-') >= 20
    assert 'data-sym="BTC-USD"' in html
    assert 'data-sym="ETH-USD"' in html
    assert "CoinGecko primary" in html
    assert "CoinPaprika" in html
    assert "plotly" not in html.lower()


def test_universe_reads_ranked_daily_accrual(tmp_path):
    dates = pd.date_range("2026-06-01", periods=31, freq="D")
    for rank, symbol in ((2, "ETH"), (1, "BTC")):
        frame = pd.DataFrame(
            {
                "source": ["CoinGecko"] * len(dates),
                "coin_id": [symbol.lower()] * len(dates),
                "symbol": [symbol] * len(dates),
                "name": [symbol.title()] * len(dates),
                "market_cap_rank": [rank] * len(dates),
                "current_price": list(range(100, 131)),
                "market_cap": [1_000_000] * len(dates),
                "total_volume": [100_000] * len(dates),
                "change_24h_pct": [1.0] * len(dates),
                "change_7d_pct": [4.0] * len(dates),
                "change_30d_pct": [12.0] * len(dates),
            },
            index=dates,
        )
        frame.to_parquet(tmp_path / f"market_{symbol.lower()}.parquet")
    rows = load_universe(50, root=tmp_path)
    assert [row["symbol"] for row in rows] == ["BTC", "ETH"]
    assert rows[0]["history_days"] == 31
    assert rows[0]["history_chip"] == "31D"
    assert rows[0]["state"] == "Firm"
    assert breadth_read(rows)["available"] is False


def test_universe_collector_normalizes_coingecko(monkeypatch):
    adapter = CryptoUniverseAdapter()
    payload = [
        {
            "id": f"coin-{rank}",
            "symbol": f"c{rank}",
            "name": f"Coin {rank}",
            "market_cap_rank": rank,
            "current_price": rank * 10,
            "market_cap": rank * 1_000_000,
            "fully_diluted_valuation": rank * 1_100_000,
            "total_volume": rank * 100_000,
            "high_24h": rank * 11,
            "low_24h": rank * 9,
            "price_change_percentage_24h": 1.5,
            "price_change_percentage_7d_in_currency": 3.0,
            "price_change_percentage_30d_in_currency": 7.0,
            "price_change_percentage_200d_in_currency": 20.0,
            "price_change_percentage_1y_in_currency": 30.0,
            "ath_change_percentage": -10.0,
            "last_updated": "2026-07-29T00:00:00Z",
        }
        for rank in range(1, 21)
    ]

    class Response:
        def json(self):
            return payload

    monkeypatch.setattr(adapter, "http_get", lambda *args, **kwargs: Response())
    frames = adapter.fetch()
    assert len(frames) == 20
    btc = frames["market_c1"].iloc[0]
    assert btc["source"] == "CoinGecko"
    assert btc["symbol"] == "C1"
    assert btc["market_cap_rank"] == 1


def test_market_state_derives_class_cap_without_new_authority():
    dates = pd.date_range("2025-12-01", periods=220, freq="D")
    frames = {
        ("coinmetrics", "mcap_usd"): pd.DataFrame(
            {"mcap_usd": pd.Series(range(900, 1120), index=dates) * 1e9}
        ),
        ("bgeo", "btc_dominance"): pd.DataFrame(
            {"btc_dominance": pd.Series(range(220), index=dates) * 0.02 + 50}
        ),
        ("sentiment_crypto", "fear_greed"): pd.DataFrame(
            {"fear_greed": [42] * 220}, index=dates
        ),
        ("defillama", "stablecoins"): pd.DataFrame(
            {"stablecoin_mcap_usd": pd.Series(range(220), index=dates) * 1e8 + 200e9}
        ),
        ("coinbase", "btc_daily"): pd.DataFrame(
            {
                "close": pd.Series(range(220), index=dates) * 100 + 50_000,
                "volume": pd.Series(range(220), index=dates) * 1e6 + 1e9,
            }
        ),
        ("yahoo", "ETH-USD"): pd.DataFrame(
            {"close": pd.Series(range(220), index=dates) * 10 + 2_000}
        ),
        ("farside", "etf_flows"): pd.DataFrame({"total": [30] * 220}, index=dates),
        ("vector", "signals"): pd.DataFrame(
            {
                "funding_annual_pct": [4.0] * 220,
                "oi_mcap_ratio": [0.02] * 220,
                "oi_mcap_pctile": [45.0] * 220,
                "dvol": [48.0] * 220,
                "dvol_pctile": [55.0] * 220,
            },
            index=dates,
        ),
    }

    state = build_market_state(lambda group, name: frames.get((group, name)))
    expected = frames[("coinmetrics", "mcap_usd")]["mcap_usd"].iloc[-1] / (
        frames[("bgeo", "btc_dominance")]["btc_dominance"].iloc[-1] / 100
    )
    assert state["total_market_cap"] == expected
    assert state["flows"]["etf"]["value"] == 150
    assert state["heat"]["funding"]["state"] == "Balanced"
    assert state["as_of"] == str(dates[-1].date())


def test_allocation_and_strategy_legacy_urls_are_durable_redirects():
    allocation = (ROOT / "site" / "vector_allocation.html").read_text(
        encoding="utf-8"
    )
    strategy = (ROOT / "site" / "btc_strategy.html").read_text(encoding="utf-8")
    assert 'href="https://www.mastermind-x.com/crypto.html"' in allocation
    assert "crypto.html#allocation" in allocation
    assert 'http-equiv="refresh"' in allocation
    assert '<nav class="site-nav">' not in allocation
    assert 'href="https://www.mastermind-x.com/vector.html"' in strategy
    assert "vector.html#strategy-track-record" in strategy
    template = (ROOT / "templates" / "vector_allocation.html.j2").read_text(
        encoding="utf-8"
    )
    assert '"_seo_head.html.j2"' in template
    assert '"crypto" ~ ".html"' in template
    assert "crypto.html#allocation" in template

    vector_builder = (ROOT / "scripts" / "build_vector.py").read_text(encoding="utf-8")
    assert re.search(r"^\s+build_allocation_page\(", vector_builder, re.MULTILINE)


def test_vector_builder_regenerates_allocation_redirect(tmp_path):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))
    build_vector.build_allocation_page(env, tmp_path, None, {}, {}, {})
    allocation = (tmp_path / "vector_allocation.html").read_text(encoding="utf-8")
    assert 'href="https://www.mastermind-x.com/crypto.html"' in allocation
    assert "crypto.html#allocation" in allocation
    assert "Bitcoin Vector — Allocation Strategy" not in allocation


def test_crypto_is_first_class_in_navigation_workflows_and_products():
    nav = (ROOT / "templates" / "_navlinks.html.j2").read_text(encoding="utf-8")
    nav_market = (ROOT / "templates" / "nav_market.js").read_text(encoding="utf-8")
    assert "{{ t('Crypto', '加密') }}" not in nav
    assert "Crypto Intelligence" in nav_market
    assert "Bitcoin Vector" in nav_market
    assert "Market state, flows, leverage and asset lanes" in nav_market
    assert "vector_allocation.html" not in nav
    assert "btc_strategy.html" not in nav

    daily = (ROOT / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")
    render = (ROOT / ".github" / "workflows" / "render.yml").read_text(encoding="utf-8")
    assert "python -m scripts.build_crypto" in daily
    assert "scripts.build_crypto" in render
    assert "hub; crypto" in render

    engine_render = (
        ROOT / ".github" / "workflows" / "engine-render.yml"
    ).read_text(encoding="utf-8")
    assert "crypto() {" in engine_render
    assert "scripts.build_crypto" in engine_render
    case_body = engine_render.split('case "$SCOPE" in', 1)[1].split("esac", 1)[0]
    assert len(re.findall(r"\bhub\s*;\s*crypto\b", case_body)) == 8
    assert not re.search(r"\bhub\s*;(?!\s*crypto\b)", case_body)

    product = ROOT / "content" / "seo" / "products" / "crypto-intelligence.md"
    assert product.exists()
    assert "/crypto.html" in product.read_text(encoding="utf-8")


def test_committed_universe_has_snapshot_provenance():
    files = sorted((ROOT / "data" / "crypto_universe").glob("market_*.parquet"))
    assert len(files) >= 20
    frame = pd.read_parquet(files[0])
    assert {"source", "symbol", "market_cap_rank", "current_price"} <= set(frame.columns)
    assert frame.iloc[-1]["source"] in {"CoinGecko", "CoinPaprika"}


def _patch_h5_split_context(monkeypatch, index):
    monkeypatch.setattr(
        build_crypto.config,
        "load",
        lambda: {"vector": {"alt_cycle": {}}},
    )
    highs = pd.DataFrame({"high": [101.0, 111.0]}, index=index)
    monkeypatch.setattr(
        build_crypto.store,
        "read",
        lambda group, name: highs
        if (group, name) == ("coinbase", "btc_daily")
        else None,
    )
    monkeypatch.setattr(
        build_crypto.btc_mtf,
        "mtf_ladder",
        lambda close, high: {"ladder": {"regime": "bull"}},
    )
    monkeypatch.setattr(
        build_crypto,
        "_series",
        lambda *args, **kwargs: pd.Series([0.04, 0.05], index=index),
    )
    monkeypatch.setattr(
        build_crypto.alt_cycle,
        "ethbtc_signal",
        lambda eth, close, cfg: {"level": 0.05},
    )
    monkeypatch.setattr(
        build_crypto.alt_cycle,
        "alt_season_score",
        lambda ethbtc, dominance, cfg: (60, "Mixed"),
    )
    monkeypatch.setattr(
        build_crypto.alt_cycle,
        "alloc_grid",
        lambda regime, bucket: {
            "btc": 60,
            "eth": 25,
            "alts": 15,
            "regime_key": "bull",
        },
    )


def _decision_projection(
    exposure_pct,
    *,
    status="ok",
    integrity_ok=True,
    errors=None,
    as_of="2026-07-29",
):
    return {
        "schema": "btc.decision/v1",
        "status": status,
        "as_of": as_of,
        "integrity_ok": integrity_ok,
        "final_exposure_pct": exposure_pct,
        "errors": list(errors or []),
    }


def test_h5_total_budget_comes_from_canonical_decision_not_raw_signal(monkeypatch):
    index = pd.to_datetime(["2026-07-28", "2026-07-29"])
    _patch_h5_split_context(monkeypatch, index)
    signals = pd.DataFrame(
        {
            "close": [100.0, 110.0],
            # Deliberately disagree with the canonical projection. H5 must not
            # recover its total budget from this raw signal column.
            "alloc_optimal": [1.0, 1.0],
        },
        index=index,
    )

    out = build_crypto._allocation(
        signals,
        {"btc_dominance": 58.0},
        _decision_projection(40),
    )

    assert out["available"] is True
    assert out["exposure"] == 40
    assert out["btc"] == 24
    assert out["eth"] == 10
    assert out["alts"] == 6
    assert out["cash"] == 60
    assert out["authority_source"] == "btc.decision/v1.final.exposure_pct"


def test_h5_valid_zero_budget_is_not_unavailable(monkeypatch):
    index = pd.to_datetime(["2026-07-28", "2026-07-29"])
    _patch_h5_split_context(monkeypatch, index)
    signals = pd.DataFrame(
        {"close": [100.0, 110.0], "alloc_optimal": [0.9, 0.9]},
        index=index,
    )

    out = build_crypto._allocation(
        signals,
        {"btc_dominance": 58.0},
        _decision_projection(0),
    )

    assert out["available"] is True
    assert out["exposure"] == 0
    assert out["btc"] == 0
    assert out["eth"] == 0
    assert out["alts"] == 0
    assert out["cash"] == 100


def test_h5_invalid_decision_fails_closed_without_silent_cash():
    index = pd.to_datetime(["2026-07-28", "2026-07-29"])
    signals = pd.DataFrame(
        {"close": [100.0, 110.0], "alloc_optimal": [1.0, 1.0]},
        index=index,
    )

    out = build_crypto._allocation(
        signals,
        {"btc_dominance": 58.0},
        _decision_projection(
            None,
            status="unavailable",
            integrity_ok=False,
            errors=["RAW_FINAL_MISMATCH_WITHOUT_NAMED_OVERRIDE"],
        ),
    )

    assert out["available"] is False
    assert out["exposure"] is None
    assert out["btc"] is None
    assert out["eth"] is None
    assert out["alts"] is None
    assert out["cash"] is None
    assert out["authority_error"] == "CANONICAL_DECISION_UNAVAILABLE"


def test_h5_missing_cockpit_projection_is_unavailable_not_zero(tmp_path):
    e0 = build_crypto._load_e0(tmp_path)

    assert e0["hero"]["exposure_pct"] is None
    assert e0["decision"]["schema"] == "btc.decision/v1"
    assert e0["decision"]["status"] == "unavailable"
    assert e0["decision"]["integrity_ok"] is False
    assert e0["decision"]["final_exposure_pct"] is None


def test_h5_build_has_explicit_fail_closed_guard():
    source = (ROOT / "scripts" / "build_crypto.py").read_text(encoding="utf-8")

    assert 'if not allocation.get("available"):' in source
    assert "Crypto H5 budget unavailable" in source
    assert 'latest["alloc_optimal"]' not in source


def test_h5_rejects_stale_canonical_decision_even_when_status_is_ok(monkeypatch):
    index = pd.to_datetime(["2026-07-28", "2026-07-29"])
    _patch_h5_split_context(monkeypatch, index)
    signals = pd.DataFrame(
        {"close": [100.0, 110.0], "alloc_optimal": [0.4, 0.4]},
        index=index,
    )

    out = build_crypto._allocation(
        signals,
        {"btc_dominance": 58.0},
        _decision_projection(40, as_of="2026-07-28"),
    )

    assert out["available"] is False
    assert out["exposure"] is None
    assert out["authority_error"] == "CANONICAL_DECISION_AS_OF_MISMATCH"


def test_h5_build_consumes_cockpit_decision_without_recomputing_authority():
    source = (ROOT / "scripts" / "build_crypto.py").read_text(encoding="utf-8")

    assert "btc_decision.build_decision" not in source
    assert 'e0.get("decision")' in source
    assert "CANONICAL_DECISION_AS_OF_MISMATCH" in source
