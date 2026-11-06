"""Actual builder/Jinja proof for R26. Synthetic inputs; incumbent writers isolated."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import importlib.util
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
import pytest
from bs4 import BeautifulSoup

from engine import forex_alerts, forex_inputs, forex_signals
from scripts import build_forex as BF

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("r26_incumbent_fixture", ROOT / "tests/test_forex_context_bus.py")
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)
_REAL_MAIN, _REAL_VM, _REAL_ENV = BF.main, BF.dollar_vm, BF.Environment
_CONFIG = deepcopy(BF.config.load()["forex"])
NOW = "2026-10-21T18:00:00+00:00"
PRICES = {"EURUSD": 1.082, "USDJPY": 150.0, "AUDUSD": 0.665, "GBPUSD": 1.27,
          "USDCAD": 1.35, "USDCHF": 0.9, "USDMXN": 19.8, "USDBRL": 5.65, "USDCNH": 7.12}


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        stamp = datetime.fromisoformat(NOW)
        return stamp.astimezone(tz) if tz else stamp.replace(tzinfo=None)


class TimestampProxy:
    def __call__(self, *args, **kwargs):
        return pd.Timestamp(*args, **kwargs)

    @staticmethod
    def now(tz=None):
        stamp = pd.Timestamp(NOW)
        return stamp.tz_convert(tz) if tz else stamp.tz_localize(None)


class PandasProxy:
    Timestamp = TimestampProxy()

    def __getattr__(self, key):
        return getattr(pd, key)


def render_case(location, monkeypatch, *, missing_risk=False, market_date="2026-10-21",
                risk_date=None, quote_changes=None, residual_shock=False):
    """Reusable browser fixture: actual main, snapshot assembly and real templates.

    The incumbent R12 fixture owns every market-state/ledger isolation seam.
    This wrapper restores real projection/rendering and supplies nine explicit
    market inputs; it does not exercise a live engine or account endpoint.
    """
    location = Path(location)
    quotes = dict(PRICES)
    cfg = deepcopy(_CONFIG)
    cfg["active"] = list(quotes)
    frames, pairs, captures, writes = {}, {}, [], []
    index = pd.bdate_range(end=market_date, periods=300)
    risk_index = pd.bdate_range(end=risk_date or market_date, periods=300)
    dollar = pd.DataFrame({
        "broad": np.linspace(98, 102, 300), "dxy": 104.0, "dollar_roc": 0.01,
        "risk_off": np.nan if missing_risk else 0.0,
        "smile_regime": None if missing_risk else "US growth premium",
        "dollar_day_z": 0.0,
        "smile_unavailable_reason": "missing_or_invalid_risk_or_direction" if missing_risk else None,
        "smile_last_confirmed": "US growth premium",
        "smile_last_confirmed_asof": pd.Timestamp("2026-10-16"),
    }, index=risk_index)
    frames["_dollar"] = dollar
    for pair, price in quotes.items():
        meta = cfg["assets"][pair]
        literal = np.linspace(price * .96, price, 300)
        frames[pair] = pd.DataFrame({
            "close": 1 / literal if meta.get("invert") else literal,
            "residual_method": "adjusted", "momentum_state": ["bear"] * 299 + ["bull"],
        }, index=index)
        row = deepcopy(_fixture._fake_pairs()[0])
        row.update(key=pair, label=pair[:3] + "/" + pair[3:], zh=pair[:3] + "/" + pair[3:],
                   base=meta["base"], quote_ccy=pair[3:], quote=price,
                   chg=(quote_changes or {}).get(pair, -0.1), spark_pts="")
        row["conviction"].update(reliable=True, base=meta["base"],
                                 headline=f"Source LONG {meta['base']}",
                                 headline_zh=f"来源偏多 {meta['base']}")
        row["conviction"]["factors"][0]["value"] = 0.4
        pairs[pair] = row
    if residual_shock:
        frames["USDJPY"]["shock_state"] = ["normal"] * 299 + ["exogenous_bid"]
        frames["USDJPY"]["shock_z"] = [0.0] * 299 + [3.2]
    events = forex_alerts._pair_events("USDJPY", frames["USDJPY"],
                                      {"label": "USD/JPY", **cfg["assets"]["USDJPY"]})
    previous = location / "data/forex/latest.json"
    previous.parent.mkdir(parents=True, exist_ok=True)
    previous.write_text(json.dumps({"asof": "1999-01-01", "pairs": {"USDJPY": {"quote": 777.111}},
                                    "r26_consumer": {"stale_sentinel": "MUST_NOT_RENDER"}}))
    class CapturingEnvironment(_REAL_ENV):
        def get_template(self, name, *args, **kwargs):
            template = super().get_template(name, *args, **kwargs)
            if name != "forex.html.j2":
                return template
            class Boundary:
                def render(self, **context):
                    captures.append(context)
                    return template.render(**context)
            return Boundary()

    def sink(path, html):
        path = Path(path)
        assert path.is_relative_to(location)
        writes.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    def main():
        qualified_cfg = deepcopy(cfg)
        # R12's isolation helper intentionally supplies an incomplete asset
        # config. Restore the real quote metadata, not a consumer-side guess.
        monkeypatch.setattr(BF.config, "load", lambda: {"forex": qualified_cfg,
            "storage": {"site_dir": str(location / "site")}})
        monkeypatch.setattr(BF, "dollar_vm", _REAL_VM)
        monkeypatch.setattr(BF, "pair_vm", lambda pair, *args: deepcopy(pairs[pair]))
        monkeypatch.setattr(BF, "Environment", CapturingEnvironment)
        monkeypatch.setattr(BF, "write_page", sink)
        monkeypatch.setattr(forex_inputs, "load_all", lambda *args: {pair: {"drivers": {}} for pair in pairs})
        monkeypatch.setattr(forex_signals, "compute_all", lambda *args: deepcopy(frames))
        monkeypatch.setattr(forex_alerts, "rebuild", lambda *args, **kwargs: deepcopy(events))
        monkeypatch.setattr(forex_alerts, "recent", lambda *args: deepcopy(events))
        return _REAL_MAIN()

    monkeypatch.setattr(BF, "datetime", FixedDateTime)
    monkeypatch.setattr(BF, "pd", PandasProxy())
    monkeypatch.setattr(_fixture, "_r12_cfg", lambda: deepcopy(cfg))
    monkeypatch.setattr(BF, "main", main)
    snapshot, stub_contexts = _fixture._r12_build_fixture(location, monkeypatch, _fixture._r12_table())
    assert not stub_contexts and len(captures) == len(writes) == 1
    assert not list(location.rglob("*.jsonl")), "isolated builder must not write a ledger"
    return snapshot, writes[0], captures[0]


@pytest.mark.parametrize("missing,market,risk,current", [
    (False, "2026-10-21", None, True),
    (True, "2026-10-21", None, False),
    (False, "2026-10-20", None, False),
    (False, "2026-10-21", "2026-10-20", False),
])
def test_real_builder_html_and_json_share_new_snapshot_and_component_clocks(tmp_path, monkeypatch, missing, market, risk, current):
    snapshot, path, context = render_case(tmp_path, monkeypatch, missing_risk=missing,
                                          market_date=market, risk_date=risk)
    html = path.read_text()
    soup = BeautifulSoup(html, "html.parser")
    consumer = json.loads(soup.select_one("#forex-r26-consumer").string)
    assert consumer == snapshot["r26_consumer"] == context["r26_view"]
    assert context["r26_histories"] == snapshot["price_history"]
    assert "MUST_NOT_RENDER" not in html and "777.111" not in html
    assert consumer["current_read"]["available"] is current
    assert consumer["current_read"]["asof"] == (risk or market)
    assert consumer["current_read"]["assembled_at"] == NOW
    assert snapshot["risk_off"] == (None if missing else 0)
    assert snapshot["price_history"]["USDJPY"]["series"]["vals"][-1] == 150
    assert len(soup.select("main")) == 1 and len(soup.select("h1")) == 1
    assert len(soup.select("[data-fxr-pair]")) == 9
    assert len(soup.select("[data-fxr-panel]")) == 36
    assert soup.select_one("#forex-full-study") and soup.select_one("#fx-study-USDJPY")
    assert len([n["id"] for n in soup.select("[id]")]) == len({n["id"] for n in soup.select("[id]")}), "duplicate chart or control IDs"
    for pair, row in context["r26_by_pair"].items():
        if pair == "DXY":
            assert row["pair_scope"] == "non_pair"
            continue
        assert row["model_direction"]["available"] is current
        expected = ("lower" if _CONFIG["assets"][pair]["invert"] else "higher") if current else None
        assert row["model_direction"]["pair_direction"] == expected
        legacy = soup.select_one("#fx-study-" + pair + " .action-chip")
        assert (expected or "flat") in legacy["class"]
        assert ("倾向走低" if expected == "lower" else "倾向走高" if expected == "higher" else "当前倾向不可用") in legacy.get_text()
    assert snapshot["decision_context"]["changes"][0]["headline"].startswith("USD/JPY:")
    assert "JPY: Trend turned up" in soup.select_one("[data-fxr-pair='USDJPY'] [data-fxr-panel='history']").get_text()
    json.dumps(snapshot, allow_nan=False)
    for asset in ("forex_r26.css", "forex_r26.js"):
        assert (path.parent / asset).read_bytes() == (ROOT / "templates" / asset).read_bytes()


def test_rendered_null_change_is_not_a_flat_zero(tmp_path, monkeypatch):
    _, path, _ = render_case(tmp_path, monkeypatch, quote_changes={"USDJPY": None, "EURUSD": 0})
    soup = BeautifulSoup(path.read_text(), "html.parser")
    assert "0.00%" in soup.select_one("[data-fxr-open-pair='EURUSD'] .fxr-change").get_text()
    assert "0.00%" not in soup.select_one("[data-fxr-open-pair='USDJPY'] .fxr-change").get_text()
    assert "—" in soup.select_one("#fx-study-USDJPY .chg").get_text()


@pytest.mark.parametrize("invert,assessed", [(True, "JPY"), (False, "USD")])
def test_history_uses_literal_quote_and_does_not_bridge_missing_rows(invert, assessed):
    values = [140, 141, None, 149, 150]
    frame = pd.DataFrame({"close": [1 / n if invert and n else n for n in values]},
                         index=pd.bdate_range(end="2026-10-21", periods=5))
    cfg = {"assets": {"USDJPY": {"base": assessed, "invert": invert}}}
    result = BF._r26_price_history({"USDJPY": frame}, cfg, date(2026, 10, 21))["USDJPY"]
    assert result["status"] == "partial"
    assert result["series"]["vals"] == [149, 150]
    assert result["observations"] == 2 and result["window_observations"] == 5


@pytest.mark.parametrize("last", [None, np.nan, np.inf, 0, -1, True])
def test_invalid_final_price_withholds_history_without_carry_forward(last):
    frame = pd.DataFrame({"close": pd.Series([140, 141, last], dtype=object).to_numpy()},
                         index=pd.bdate_range(end="2026-10-21", periods=3))
    cfg = {"assets": {"USDJPY": {"base": "USD", "invert": False}}}
    result = BF._r26_price_history({"USDJPY": frame}, cfg, date(2026, 10, 21))["USDJPY"]
    assert result["status"] == "unavailable" and not result["series"]["vals"]


def test_history_rejects_unknown_convention_and_future_endpoint():
    frame = pd.DataFrame({"close": [1.1, 1.2]}, index=pd.to_datetime(["2026-10-21", "2026-10-22"]))
    for meta in ({"base": "EUR", "invert": False}, {"base": "JPY", "invert": False}):
        result = BF._r26_price_history({"EURUSD": frame}, {"assets": {"EURUSD": meta}}, date(2026, 10, 21))
        assert result["EURUSD"]["status"] == "unavailable"



def test_actual_builder_qualifies_residual_shock_in_today_and_pair_history(tmp_path, monkeypatch):
    snapshot, path, _ = render_case(tmp_path, monkeypatch, residual_shock=True)
    soup = BeautifulSoup(path.read_text(), "html.parser")
    source = next(event for event in snapshot["decision_context"]["changes"]
                  if event["type"] == "residual_shock")
    assert source["headline"].startswith("USD/JPY:")
    for selector in ("#fxr-today", "[data-fxr-pair=\'USDJPY\'] [data-fxr-panel=\'history\']"):
        events = soup.select_one(selector).select(".fxr-event")
        event = next(node for node in events if source["id"] in node.get_text())
        headline = event.select_one("strong").get_text()
        assert "JPY: Unusual move" in headline and "JPY：出现" in headline
        assert "USD/JPY:" not in headline and "USD/JPY：" not in headline
        assert "(up)" in headline and "异常上行" in headline
        assert "Assessed JPY residual technical series" in event.get_text()
        assert "受评估货币 JPY 的残差技术序列" in event.get_text()
