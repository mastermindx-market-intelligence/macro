from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _ms(ts: str) -> int:
    return int(pd.Timestamp(ts).timestamp() * 1000)


def test_sge_au9999_frame_filters_contract_and_stamps_shanghai_close():
    from collectors import china_gold_basis as cgb

    raw = pd.DataFrame(
        [
            {"ts_code": "Au99.95", "trade_date": "20260917", "close": 816.0},
            {"ts_code": "Au99.99", "trade_date": "20260917", "close": 817.25},
            {"ts_code": "Au99.99", "trade_date": "20260918", "close": 820.50},
        ]
    )

    out = cgb._sge_au9999_frame(raw)

    assert list(out.columns) == ["rmb_per_g"]
    assert list(out["rmb_per_g"]) == [817.25, 820.50]
    assert list(out.index) == [
        pd.Timestamp("2026-09-17T07:30:00"),
        pd.Timestamp("2026-09-18T07:30:00"),
    ]


def test_massive_xaucny_frame_selects_nearest_bar_to_shanghai_close():
    from collectors import china_gold_basis as cgb

    payload = {
        "results": [
            {"t": _ms("2026-09-18T07:27:00Z"), "c": 30900.0},
            {"t": _ms("2026-09-18T07:29:00Z"), "c": 30950.0},
            {"t": _ms("2026-09-18T07:30:00Z"), "c": 30960.0},
            {"t": _ms("2026-09-18T07:31:00Z"), "c": 30970.0},
        ]
    }

    out = cgb._massive_xaucny_frame(payload, tolerance_minutes=2)

    assert list(out.columns) == ["cny_per_oz"]
    assert len(out) == 1
    assert out.index[0] == pd.Timestamp("2026-09-18T07:30:00")
    assert out.iloc[0]["cny_per_oz"] == pytest.approx(30960.0)


def test_massive_xaucny_frame_drops_days_without_close_aligned_bar():
    from collectors import china_gold_basis as cgb

    payload = {
        "results": [
            {"t": _ms("2026-09-18T07:20:00Z"), "c": 30900.0},
            {"t": _ms("2026-09-18T07:40:00Z"), "c": 31000.0},
        ]
    }

    out = cgb._massive_xaucny_frame(payload, tolerance_minutes=2)

    assert out.empty


def test_adapter_fetch_uses_existing_tushare_client_and_massive_currency_key(monkeypatch):
    from collectors import china_gold_basis as cgb

    raw_sge = pd.DataFrame(
        [
            {"ts_code": "Au99.99", "trade_date": "20260917", "close": 817.25},
            {"ts_code": "Au99.99", "trade_date": "20260918", "close": 820.50},
        ]
    )
    calls = []

    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(
        cgb.tushare_client,
        "query",
        lambda api_name, **kwargs: raw_sge.copy()
        if api_name == "sge_daily"
        else (_ for _ in ()).throw(AssertionError(api_name)),
    )
    monkeypatch.setattr(cgb.config, "secret", lambda name: "massive-key" if name in {"POLYGON_API_KEY", "MASSIVE_API_KEY"} else None)

    adapter = cgb.ChinaGoldBasisAdapter()

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _Resp(
            {
                "results": [
                    {"t": _ms("2026-09-17T07:30:00Z"), "c": 30750.0},
                    {"t": _ms("2026-09-18T07:30:00Z"), "c": 30960.0},
                ]
            }
        )

    monkeypatch.setattr(adapter, "http_get", fake_get)

    frames = adapter.fetch(full_history=False)

    assert set(frames) == {"sge_au9999", "xaucny_spot"}
    assert list(frames["sge_au9999"]["rmb_per_g"]) == [817.25, 820.50]
    assert list(frames["xaucny_spot"]["cny_per_oz"]) == [30750.0, 30960.0]
    assert calls
    url, kwargs = calls[0]
    assert "C:XAUUSD" not in url
    assert "C:XAUCNY" in url
    assert kwargs["headers"]["Authorization"] == "Bearer massive-key"
    assert "apiKey" not in kwargs.get("params", {})


def test_adapter_without_either_credential_is_known_blocked(monkeypatch):
    from collectors import china_gold_basis as cgb

    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: False)
    monkeypatch.setattr(cgb.config, "secret", lambda name: None)

    adapter = cgb.ChinaGoldBasisAdapter()

    assert adapter.expected_failure
    with pytest.raises(RuntimeError, match="credentials"):
        adapter.fetch()


def test_close_aligned_proxy_compares_rmb_per_ounce_directly():
    from engine import china_gold_premium as cgp

    idx = [pd.Timestamp("2026-09-18T07:30:00")]
    sge = pd.DataFrame({"rmb_per_g": [820.50]}, index=idx)
    global_spot = pd.DataFrame({"cny_per_oz": [25490.0]}, index=idx)

    out = cgp.compute_close_aligned_proxy(
        sge,
        global_spot,
        sge_column="rmb_per_g",
        global_column="cny_per_oz",
        max_skew_minutes=2,
    )

    assert len(out) == 1
    row = out.iloc[-1]
    expected_local = 820.50 * cgp.TROY_OZ_GRAMS
    assert row["sge_cny_oz"] == pytest.approx(expected_local)
    assert row["reference_cny_oz"] == pytest.approx(25490.0)
    assert row["spread_cny_oz"] == pytest.approx(expected_local - 25490.0)
    assert row["premium_pct"] == pytest.approx((expected_local / 25490.0 - 1.0) * 100.0)


def test_proxy_only_view_model_is_available_and_keeps_canonical_separate():
    from engine import china_gold_premium as cgp

    idx = pd.date_range("2026-09-01 07:30:00", periods=18, freq="D")
    sge = pd.DataFrame({"rmb_per_g": [810.0 + i for i in range(18)]}, index=idx)
    global_spot = pd.DataFrame({"cny_per_oz": [25200.0 + 25 * i for i in range(18)]}, index=idx)
    frames = {
        ("china_gold_basis", "sge_au9999"): sge,
        ("china_gold_basis", "xaucny_spot"): global_spot,
    }
    cfg = {
        "canonical": {},
        "intraday": {},
        "close_proxy": {
            "sge": {
                "group": "china_gold_basis",
                "name": "sge_au9999",
                "column": "rmb_per_g",
                "source_label": "Shanghai Gold Exchange Au99.99",
                "entitled": True,
            },
            "global": {
                "group": "china_gold_basis",
                "name": "xaucny_spot",
                "column": "cny_per_oz",
                "source_label": "Global XAU/CNY spot",
                "entitled": True,
            },
            "max_skew_minutes": 2,
            "max_age_days": 4,
        },
    }

    vm = cgp.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-09-18T12:00:00Z"),
    )

    assert vm["available"] is True
    assert vm["current_method"] == "close_proxy"
    assert vm["methodology_label_en"] == "Indicative Shanghai-close basis"
    assert vm["price_currency"] == "CNY"
    assert vm["canonical"]["available"] is False
    assert vm["close_proxy"]["available"] is True
    assert len(vm["chart"]["canonical"]) == 0
    assert len(vm["chart"]["proxy"]) == 18
    assert vm["chart"]["display_source"] == "proxy"
    assert vm["stats"]["avg_5"] is not None
    assert vm["stats"]["range_30"] is not None
    assert vm["sge_price_oz"] == pytest.approx(vm["chart"]["proxy"][-1]["sge_price_oz"])
    assert vm["reference_price_oz"] == pytest.approx(vm["chart"]["proxy"][-1]["reference_price_oz"])


def test_same_date_canonical_benchmark_outranks_close_proxy():
    from engine import china_gold_premium as cgp

    idx = [pd.Timestamp("2026-09-18")]
    proxy_idx = [pd.Timestamp("2026-09-18T07:30:00")]
    frames = {
        ("sge", "pm"): pd.DataFrame({"v": [820.0]}, index=idx),
        ("lbma", "am"): pd.DataFrame({"v": [3700.0]}, index=idx),
        ("fx", "daily"): pd.DataFrame({"v": [6.95]}, index=idx),
        ("basis", "sge"): pd.DataFrame({"v": [820.0]}, index=proxy_idx),
        ("basis", "global"): pd.DataFrame({"v": [25450.0]}, index=proxy_idx),
    }
    leg = lambda g, n, label: {
        "group": g, "name": n, "column": "v", "source_label": label, "entitled": True
    }
    cfg = {
        "canonical": {
            "sge": leg("sge", "pm", "SGE SHAUPM"),
            "london": leg("lbma", "am", "LBMA AM"),
            "fx": leg("fx", "daily", "USDCNY"),
            "max_age_days": 4,
        },
        "close_proxy": {
            "sge": leg("basis", "sge", "SGE Au99.99"),
            "global": leg("basis", "global", "Global XAU/CNY"),
            "max_skew_minutes": 2,
            "max_age_days": 4,
        },
    }

    vm = cgp.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-09-18T12:00:00Z"),
    )

    assert vm["current_method"] == "canonical"
    assert vm["price_currency"] == "USD"
    assert vm["chart"]["display_source"] == "canonical"


def test_proxy_partial_renders_cny_close_basis_as_primary_display():
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from engine import china_gold_premium as cgp

    idx = pd.date_range("2026-09-10 07:30:00", periods=9, freq="D")
    frames = {
        ("basis", "sge"): pd.DataFrame({"v": [818.0 + i for i in range(9)]}, index=idx),
        ("basis", "global"): pd.DataFrame({"v": [25400.0 + 20 * i for i in range(9)]}, index=idx),
    }
    leg = lambda g, n, label: {
        "group": g, "name": n, "column": "v", "source_label": label, "entitled": True
    }
    vm = cgp.build_view_model(
        {
            "canonical": {},
            "intraday": {},
            "close_proxy": {
                "sge": leg("basis", "sge", "Shanghai Gold Exchange Au99.99"),
                "global": leg("basis", "global", "Global XAU/CNY spot"),
                "max_skew_minutes": 2,
                "max_age_days": 4,
            },
        },
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-09-18T12:00:00Z"),
    )

    repo = Path(__file__).resolve().parents[1]
    env = Environment(
        loader=FileSystemLoader(str(repo / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = env.get_template("_china_gold_premium.html.j2").render(g=vm)

    assert "Indicative Shanghai-close basis" in html
    assert "上海收盘指示性价差" in html
    assert "Shanghai CNY/oz" in html
    assert "Global spot CNY/oz" in html
    assert "CNY/oz Spread" in html
    assert 'data-cgp-display-source="proxy"' in html
    assert 'data-cgp-currency="CNY"' in html
    assert 'class="cgp-chart"' in html
    assert "Shanghai Gold Exchange Au99.99" in html
    assert "Global XAU/CNY spot" in html
    assert "Tushare" not in html
    assert "Massive" not in html


def test_production_config_wires_close_proxy_to_source_store_without_vendor_branding():
    from lib import config

    cfg = config.load()["commodities"]["china_gold_premium"]
    proxy = cfg["close_proxy"]

    assert proxy["sge"] == {
        "group": "china_gold_basis",
        "name": "sge_au9999",
        "column": "rmb_per_g",
        "source_label": "Shanghai Gold Exchange Au99.99",
        "entitled": True,
    }
    assert proxy["global"] == {
        "group": "china_gold_basis",
        "name": "xaucny_spot",
        "column": "cny_per_oz",
        "source_label": "Global XAU/CNY spot",
        "entitled": True,
    }
    assert proxy["max_skew_minutes"] == 2
    assert proxy["max_age_days"] == 4
    public_labels = " ".join((proxy["sge"]["source_label"], proxy["global"]["source_label"]))
    assert "Tushare" not in public_labels
    assert "Massive" not in public_labels
    assert "Polygon" not in public_labels


def test_collector_registry_places_gold_basis_on_existing_asia_shard():
    from scripts import collect

    registry = collect.all_adapters()

    assert "china_gold_basis" in registry
    assert registry["china_gold_basis"].__name__ == "ChinaGoldBasisAdapter"
    assert "china_gold_basis" in collect.group_members("asia", registry)


def test_asia_close_supplies_existing_massive_credentials_to_gold_basis_collector():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    text = (repo / ".github" / "workflows" / "asia-close.yml").read_text()

    assert "TUSHARE_TOKEN: ${{ secrets.TUSHARE_TOKEN }}" in text
    assert "POLYGON_API_KEY: ${{ secrets.POLYGON_API_KEY }}" in text
    assert "MASSIVE_API_KEY: ${{ secrets.MASSIVE_API_KEY }}" in text


def test_massive_history_chunks_never_exceed_fourteen_calendar_days():
    from datetime import date
    from collectors import china_gold_basis as cgb

    chunks = list(cgb._date_chunks(date(2026, 7, 1), date(2026, 8, 9), max_days=14))

    assert chunks[0] == (date(2026, 7, 1), date(2026, 7, 14))
    assert chunks[-1][1] == date(2026, 8, 9)
    for start, end in chunks:
        assert (end - start).days <= 13
    for left, right in zip(chunks, chunks[1:]):
        assert right[0] == left[1] + pd.Timedelta(days=1)


def test_adapter_filters_tushare_request_to_au9999(monkeypatch):
    from collectors import china_gold_basis as cgb

    seen = {}
    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(cgb.config, "secret", lambda name: "massive-key")
    raw_sge = pd.DataFrame(
        [{"ts_code": "Au99.99", "trade_date": "20260918", "close": 820.5}]
    )

    def fake_query(api_name, **kwargs):
        seen.update(kwargs)
        return raw_sge

    monkeypatch.setattr(cgb.tushare_client, "query", fake_query)
    adapter = cgb.ChinaGoldBasisAdapter()
    monkeypatch.setattr(
        adapter,
        "http_get",
        lambda *args, **kwargs: _Resp(
            {"results": [{"t": _ms("2026-09-18T07:30:00Z"), "c": 30960.0}]}
        ),
    )

    adapter.fetch()

    assert seen["ts_code"] == "Au99.99"


def test_collector_store_is_consumed_by_product_engine_without_translation(tmp_path, monkeypatch):
    from collectors import china_gold_basis as cgb
    from collectors.base import run_adapter
    from engine import china_gold_premium as cgp
    from lib import config, store

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(cgb.config, "secret", lambda name: "fixture-key")
    adapter = cgb.ChinaGoldBasisAdapter()

    idx = pd.to_datetime(
        ["2026-09-17T07:30:00", "2026-09-18T07:30:00"]
    )
    frames = {
        "sge_au9999": pd.DataFrame({"rmb_per_g": [817.0, 820.5]}, index=idx),
        "xaucny_spot": pd.DataFrame({"cny_per_oz": [25380.0, 25490.0]}, index=idx),
    }
    monkeypatch.setattr(
        adapter,
        "fetch",
        lambda full_history=False: {name: frame.copy() for name, frame in frames.items()},
    )

    result = run_adapter(adapter)

    assert result.status == "ok"
    stored_sge = store.read("china_gold_basis", "sge_au9999")
    assert stored_sge is not None
    assert stored_sge.index[-1] == pd.Timestamp("2026-09-18T07:30:00")

    vm = cgp.build_view_model(
        config.load()["commodities"]["china_gold_premium"],
        now=pd.Timestamp("2026-09-18T12:00:00Z"),
    )
    assert vm["available"] is True
    assert vm["current_method"] == "close_proxy"
    assert vm["close_proxy"]["asof"] == "2026-09-18T07:30:00+00:00"
