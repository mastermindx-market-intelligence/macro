"""Render Crypto and Vector through their own template paths in four fixtures.

Each case injects a cockpit projection, a market dict, and an in-memory
signals frame. ``store.read`` is replaced so ``lib.store._path`` cannot create
``data/`` directories. Asset-state and options readers are the builders' own
functions with a reader that returns None. ``build_vector.main`` is not called:
it writes ``vector/signals.parquet``, spawns sibling builders, and publishes
``config["storage"]["site_dir"]`` (``scripts/build_vector.py``:4425, 5062).
The Vector HTML below repeats only the Environment, filters, render, and
whitespace collapse at ``scripts/build_vector.py``:5045-5061.

``CRYPTO_T19P_TEMPLATE_ROOT`` points both renders at another template
directory (stacked proof or an unpatched copy). Includes still resolve from
this repository's ``templates/``. The four patch-proof tests skip only when
that variable is unset and the T19p marker is absent from the repository
template.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd
import pytest

from engine.btc_options import build_contract as build_btc_options
from engine.eth_state import build_states as build_asset_states
from scripts import build_crypto, build_vector

ROOT = Path(__file__).resolve().parent.parent
T19P_TEMPLATE_ROOT = "CRYPTO_T19P_TEMPLATE_ROOT"
AS_OF = "2026-09-26"
PREV = "2026-09-25"
_HISTORY = ["2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25", AS_OF]


def _slice(html: str, start: str, end: str) -> str:
    i = html.index(start)
    j = html.index(end, i + len(start))
    return html[i:j]


def _template_roots() -> list[str]:
    override = os.environ.get(T19P_TEMPLATE_ROOT)
    roots = [override] if override else []
    roots.append(str(ROOT / "templates"))
    return roots


def _require_t19p(name: str, marker: str) -> None:
    """Skip only when the override is unset and the repository template lacks the marker."""
    if os.environ.get(T19P_TEMPLATE_ROOT):
        return
    source = (ROOT / "templates" / name).read_text(encoding="utf-8")
    if marker not in source:
        pytest.skip(
            f"{T19P_TEMPLATE_ROOT} is unset and the T19p patch marker is absent "
            f"from templates/{name}; this skip becomes a hard assert after integration"
        )


def _bind_crypto_templates(monkeypatch) -> None:
    if not os.environ.get(T19P_TEMPLATE_ROOT):
        return
    real = build_crypto.FileSystemLoader
    roots = _template_roots()
    repo = (ROOT / "templates").resolve()

    def loader(searchpath, *args, **kwargs):
        if Path(str(searchpath)).resolve() == repo:
            return real(roots, *args, **kwargs)
        return real(searchpath, *args, **kwargs)

    monkeypatch.setattr(build_crypto, "FileSystemLoader", loader)


def _none_reader(*_args, **_kwargs):
    return None


def _sensor(**extra) -> dict:
    base = {"value": None, "state": "Unavailable", "tone": "neutral", "percentile": None}
    base.update(extra)
    return base


def _market(*, dates: list[str], vals: list[float]) -> dict:
    return {
        "as_of": AS_OF,
        "stance": "Unavailable",
        "stance_zh": "暂无",
        "summary": "Fixture market read.",
        "summary_zh": "示例市场解读。",
        "tone": "neutral",
        "total_market_cap": None,
        "total_30d_pct": None,
        "total_state": "Unavailable",
        "total_tone": "neutral",
        "btc_dominance": None,
        "dominance_30d": None,
        "dominance_state": "Unavailable",
        "dominance_tone": "neutral",
        "fear_greed": None,
        "fear_state": "Unavailable",
        "fear_tone": "neutral",
        "history": {"dates": list(dates), "vals": list(vals)},
        "regimes": [],
        "flows": {
            "etf": _sensor(as_of=None),
            "stablecoins": _sensor(change_30d_pct=None, change_30d_usd=None),
            "volume": _sensor(proxy="fixture"),
        },
        "heat": {
            "funding": _sensor(),
            "open_interest": _sensor(),
            "volatility": _sensor(),
            "altseason": _sensor(),
        },
    }


def _projection(exposure: int | None, *, as_of: str, status: str = "ok", integrity_ok: bool = True) -> dict:
    return {
        "schema": "btc.decision/v1",
        "status": status,
        "as_of": as_of,
        "integrity_ok": integrity_ok,
        "final_exposure_pct": exposure,
        "errors": [],
        "authority_source": "btc.decision/v1.final.exposure_pct",
    }


def _row(*, price, change_24h) -> dict:
    return {
        "id": "bitcoin",
        "source": "fixture",
        "symbol": "BTC",
        "name": "Bitcoin",
        "rank": 1,
        "price": price,
        "change_24h": change_24h,
        "change_7d": None,
        "change_30d": None,
        "state": "Building",
        "tone": "neutral",
        "history_days": 0,
        "history_chip": "Building",
        "as_of": AS_OF,
    }


def _snapshot(row: dict) -> dict:
    return {
        "as_of": AS_OF,
        "rows": [row],
        "excluded": [{
            "symbol": "OLD",
            "file": "market_old.parquet",
            "source": "fixture",
            "as_of": "2026-01-01",
            "reason": "OLDER_SNAPSHOT",
        }],
        "requested": 50,
        "observed": 1,
        "sources": ["fixture"],
    }


def _signals(columns: dict[str, list]) -> pd.DataFrame:
    n = len(next(iter(columns.values())))
    index = pd.to_datetime(_HISTORY[-n:])
    return pd.DataFrame(columns, index=index)


def _crypto_case(name: str) -> dict:
    history_vals = [2.1e12, 2.15e12, 2.2e12, 2.12e12, 2.18e12, 2.25e12]
    if name == "missing_history":
        return {
            "projection": _projection(0, as_of=AS_OF),
            "market": _market(dates=[], vals=[]),
            "signals": _signals({"close": [100.0]}),
            "row": _row(price=None, change_24h=None),
            "hero_price": None,
            "hero_change": None,
        }
    if name == "valid_zero":
        return {
            "projection": _projection(0, as_of=AS_OF),
            "market": _market(dates=_HISTORY, vals=history_vals),
            "signals": _signals({"close": [100.0]}),
            "row": _row(price=100.0, change_24h=0.0),
            "hero_price": 100.0,
            "hero_change": 0.0,
        }
    if name == "stale_budget":
        return {
            "projection": _projection(60, as_of=PREV),
            "market": _market(dates=_HISTORY, vals=history_vals),
            "signals": _signals({"close": [100.0]}),
            "row": _row(price=100.0, change_24h=1.0),
            "hero_price": 100.0,
            "hero_change": 1.0,
        }
    if name == "partial":
        return {
            "projection": _projection(40, as_of=AS_OF),
            "market": _market(dates=_HISTORY, vals=history_vals),
            "signals": _signals({"open": [1.0]}),
            "row": _row(price=100.0, change_24h=1.0),
            "hero_price": 100.0,
            "hero_change": 1.0,
        }
    raise AssertionError(name)


def _render_crypto(tmp_path: Path, monkeypatch, case: dict) -> str:
    import engine.event_calendar as event_calendar
    import lib.pages as pages

    _bind_crypto_templates(monkeypatch)
    site = tmp_path / "site"
    site.mkdir()
    signals = case["signals"]
    # us_macro_events(use_fred=False) still calls _fetch_upcoming_auctions,
    # which mkdirs data/macro/auction_cache and requests TreasuryDirect
    # (engine/event_calendar.py:297-317, :433). The calendar shelf stays on
    # the static FOMC/CPI path; the auction fetch does not run.
    monkeypatch.setattr(event_calendar, "_fetch_upcoming_auctions", lambda _today: [])
    monkeypatch.setattr(pages, "_ensure_shim_asset", lambda: None)

    def fake_read(group, name):
        if (group, name) == ("vector", "signals"):
            return signals.copy()
        return None

    monkeypatch.setattr(build_crypto.store, "read", fake_read)
    monkeypatch.setattr(build_crypto, "build_market_state", lambda: case["market"])
    monkeypatch.setattr(build_crypto, "load_universe_snapshot", lambda *_a, **_k: _snapshot(case["row"]))
    monkeypatch.setattr(build_crypto, "build_asset_states", lambda: build_asset_states(_none_reader))
    monkeypatch.setattr(build_crypto, "build_btc_options", lambda: build_btc_options(_none_reader))
    (site / "crypto_cockpit.json").write_text(json.dumps({
        "schema": "crypto.cockpit/v1",
        "display_only": True,
        "as_of": AS_OF,
        "decision": case["projection"],
        "hero": {
            "price": case["hero_price"],
            "change_24h_pct": case["hero_change"],
            "stance_en": "Unavailable",
            "stance_zh": "暂无",
            "summary_en": "Fixture lane.",
            "summary_zh": "示例通道。",
            "exposure_pct": case["projection"]["final_exposure_pct"],
            "gate_active": False,
        },
        "axes": [],
    }), encoding="utf-8")
    data_existed = (ROOT / "data").exists()
    output = build_crypto.build(site)
    assert (site / "crypto_class_state.json").is_file()
    assert (ROOT / "data").exists() == data_existed
    return output.read_text(encoding="utf-8")


def _vector_decision(*, ok: bool, exposure: int | None) -> dict:
    if not ok:
        return {
            "schema": "btc.decision/v1",
            "status": "unavailable",
            "integrity": {"ok": False},
            "final": None,
            "advisory": {"levels": {}},
        }
    return {
        "schema": "btc.decision/v1",
        "status": "ok",
        "integrity": {"ok": True},
        "final": {
            "action_code": "STAY_OUT" if exposure == 0 else "SET_EXPOSURE",
            "action_en": "Hold cash." if exposure == 0 else "Set the recorded target.",
            "action_zh": "保持现金。" if exposure == 0 else "采用已记录目标。",
            "exposure_pct": exposure,
            "change_pp": 0.0,
        },
        "advisory": {"levels": {}},
    }


def _flow(kind: str) -> dict:
    base = dict(
        ok=True, display_only=True, causally_qualified=False, scope="OKX/BTC/CONTRACTS",
        asof="2026-09-26 08:00:00", evaluated_at="2026-09-26 09:00:00",
        n_hours=24, window_24h_complete=True, window_72h_complete=False,
        stale=False, gap_detected=False, flow_state="buy_dominant", buy_share_24h=0.5,
        net_flow_24h_native=1.0,
    )
    if kind == "unavailable":
        return build_vector._derivatives_flow_view(None)
    if kind == "stale":
        base["stale"] = True
    elif kind == "no_activity":
        base.update(flow_state="no_activity", buy_share_24h=None, net_flow_24h_native=0)
    elif kind == "coverage_gap":
        base["n_hours"] = 23
    else:
        raise AssertionError(kind)
    return build_vector._derivatives_flow_view({"context_legs": {"intraday_cvd": base}})


def _vector_case(name: str) -> dict:
    if name == "missing_history":
        frame = _signals({"close": [float("nan")] * 4, "alloc_optimal": [0.0] * 4})
        decision = _vector_decision(ok=True, exposure=0)
        flow = _flow("unavailable")
    elif name == "valid_zero":
        frame = _signals({"close": [100.0, 101.0, 99.0, 100.0], "alloc_optimal": [0.0, 0.0, 0.0, 0.0]})
        decision = _vector_decision(ok=True, exposure=0)
        flow = _flow("no_activity")
    elif name == "stale_budget":
        frame = _signals({"close": [100.0, 101.0, 99.0, 100.0], "alloc_optimal": [0.4, 0.4, 0.4, 0.4]})
        decision = _vector_decision(ok=False, exposure=None)
        flow = _flow("stale")
    elif name == "partial":
        frame = _signals({
            "close": [100.0, 101.0, 99.0, 100.0],
            "alloc_optimal": [0.4, float("nan"), 0.4, 0.4],
        })
        decision = _vector_decision(ok=True, exposure=40)
        flow = _flow("coverage_gap")
    else:
        raise AssertionError(name)
    contract = build_vector._risk_strategy_payload(frame)
    return {"decision": decision, "flow": flow, "contract": contract}


def _render_vector(case: dict, *, price: float | None = 100, chg24: float | None = 0.0) -> str:
    from jinja2 import Environment, FileSystemLoader

    vm = {
        "as_of": AS_OF,
        "price": price,
        "chg24": chg24,
        "built": "2026-09-26 00:00 UTC",
        "master": {"ok": False},
        "decision": case["decision"],
        "risk_index": None,
        "risk_label": "Unavailable",
        "risk_on": False,
        "chart_contract": case["contract"],
        "derivatives_flow": case["flow"],
        "btc_options": build_btc_options(_none_reader),
        "options": {"dvol": None, "gamma_flip": None},
        "leverage": {"oi_total": None, "okx_ls_ratio": None},
        "presentation": {"axes": [], "watch": [], "complex": []},
        "charts": {"etf_flow": "", "momentum": "", "structure": "", "bfi": ""},
        "strategy": {"as_of": AS_OF, "strategies": []},
        "newf": {"holders": {"state": None}, "miner": {"state": None}},
        "onchain": {"premium_state": None},
        "valuation": {"mvrv_z": None},
        "cycle_vintage": {"reserve_risk_asof": None, "vdd_asof": None},
        "cycle_stage": "—",
        "cycle_pos": "—",
        "bfi": None,
        "calib": {"signals": {}, "meta": {}, "risk_drawdown": None},
        "timeline": [],
        "cards": {},
    }
    env = Environment(
        loader=FileSystemLoader(_template_roots()),
        autoescape=True,
    )
    try:
        from engine import i18n
        td, tr = i18n.td, i18n.tr
    except Exception:
        td = tr = lambda en: en
    env.globals.update(td=td, tr=tr)
    env.filters["money"] = lambda v: f"${v:,.0f}" if pd.notna(v) else "—"
    env.filters["money1"] = lambda v: f"${v / 1000:,.1f}K" if pd.notna(v) else "—"
    html = env.get_template("vector.html.j2").render(**vm, C=build_vector.C)
    return re.sub(r">\s+<", "> <", html)


def _assert_common(crypto: str, vector: str) -> None:
    assert "validated" not in crypto.lower()
    assert "validated" not in vector.lower()
    assert "9876.5" not in crypto
    heat = _slice(crypto, 'id="leverage-heat"', 'id="allocation"')
    assert "Unavailable" in heat


def test_missing_history_withholds_curves(tmp_path, monkeypatch):
    crypto = _render_crypto(tmp_path, monkeypatch, _crypto_case("missing_history"))
    vector = _render_vector(_vector_case("missing_history"))
    _assert_common(crypto, vector)
    overview = _slice(crypto, 'id="crypto-overview"', 'id="universe-snapshot"')
    board = _slice(crypto, 'id="market-board"', 'id="money-flows"')
    assert 'data-market-history-state="unavailable"' in overview
    assert "Market history unavailable" in overview
    assert "ilx-path" not in overview
    assert "ilx-null" not in overview
    assert "<svg" not in overview
    assert 'data-desk-budget-state="available"' in overview
    assert "The recorded target is cash—not missing data." in overview
    assert "Building history" in board
    assert "<svg" not in board
    assert ">—<" in board or ">—" in board
    replay = _slice(vector, 'id="overview"', 'data-shelf="S2"')
    assert 'data-vector-replay-state="unavailable"' in replay
    assert "Interactive replay unavailable" in replay
    assert "Price history is incomplete" in replay
    assert 'id="vec-risk-chart"' not in replay
    assert "polyline points=" not in vector
    assert 'data-flow-state="unavailable"' in vector
    assert "Activity unavailable" in vector


def test_valid_zero_is_cash_not_a_missing_budget(tmp_path, monkeypatch):
    crypto = _render_crypto(tmp_path, monkeypatch, _crypto_case("valid_zero"))
    vector = _render_vector(_vector_case("valid_zero"))
    _assert_common(crypto, vector)
    overview = _slice(crypto, 'id="crypto-overview"', 'id="universe-snapshot"')
    board = _slice(crypto, 'id="market-board"', 'id="money-flows"')
    allocation = _slice(crypto, 'id="allocation"', 'id="asset-lanes"')
    budget = _slice(overview, 'class="desk-budget"', 'class="desk-next-step"')
    assert 'data-market-history-state="available"' in overview
    assert "ilx-path" in overview
    assert "Budget unavailable" not in budget
    assert ">0%<" in budget
    assert ">100%<" in budget
    assert "The recorded target is cash—not missing data." in budget
    assert "Model holds cash." in allocation
    assert "A valid 0% crypto target means 100% cash." in allocation
    assert "0.0%" in board
    assert "$100" in board
    replay = _slice(vector, 'id="overview"', 'data-shelf="S2"')
    assert 'data-vector-replay-state="valid"' in replay
    assert 'id="vec-risk-chart"' in replay
    assert "Interactive replay unavailable" not in replay
    assert "Decision unavailable" not in replay
    assert "DECISION TEMPORARILY UNAVAILABLE" not in vector
    assert 'data-decision-exposure="0"' in vector
    assert 'data-flow-state="no_activity"' in vector
    assert "No activity observed" in vector
    assert "not 0%" in vector
    flow = _slice(vector, 'data-flow-state="no_activity"', 'id="onchain-lab"')
    assert ">0.0%<" not in flow.split("flow-share", 1)[-1][:400]


def test_stale_budget_is_unavailable_not_cash(tmp_path, monkeypatch):
    crypto = _render_crypto(tmp_path, monkeypatch, _crypto_case("stale_budget"))
    vector = _render_vector(_vector_case("stale_budget"))
    _assert_common(crypto, vector)
    overview = _slice(crypto, 'id="crypto-overview"', 'id="universe-snapshot"')
    allocation = _slice(crypto, 'id="allocation"', 'id="asset-lanes"')
    budget = _slice(overview, 'class="desk-budget"', 'class="desk-next-step"')
    assert 'data-desk-budget-state="unavailable"' in budget
    assert "Budget unavailable" in budget
    assert "An unavailable target is not a cash recommendation." in budget
    assert "2026-09-25" in budget
    assert "60%" not in budget
    assert "60%" not in allocation
    assert "The decision belongs to a different snapshot. Its old target is not shown as current." in allocation
    assert ">—<" in allocation or ">—" in allocation
    assert "DECISION TEMPORARILY UNAVAILABLE" in vector
    assert 'data-decision-status="unavailable"' in vector
    assert "data-decision-exposure" not in vector
    assert 'data-flow-state="stale"' in vector
    assert "Stale observations" in vector
    flow = _slice(vector, 'data-flow-state="stale"', "Inspect coverage")
    assert "%" not in _slice(flow, "flow-share-value", "</div>")


def test_partial_keeps_known_budget_and_withholds_the_split(tmp_path, monkeypatch):
    crypto = _render_crypto(tmp_path, monkeypatch, _crypto_case("partial"))
    vector = _render_vector(_vector_case("partial"))
    _assert_common(crypto, vector)
    overview = _slice(crypto, 'id="crypto-overview"', 'id="universe-snapshot"')
    allocation = _slice(crypto, 'id="allocation"', 'id="asset-lanes"')
    assert 'data-allocation-state="breakdown-unavailable"' in allocation
    assert 'data-desk-budget-state="breakdown-unavailable"' in overview
    assert "Breakdown unavailable" in allocation
    assert "Total budget known; asset breakdown unavailable." in overview
    assert "40%" in allocation
    assert "60%" in allocation
    assert "alloc-seg" not in allocation
    assert "No asset percentages are inferred." in allocation
    replay = _slice(vector, 'id="overview"', 'data-shelf="S2"')
    assert 'id="vec-risk-chart"' in replay
    assert "the chart preserves them as unknown" in replay
    assert "Allocation simulation unavailable" in vector
    assert 'data-flow-state="coverage_gap"' in vector
    assert "Incomplete 24-hour window" in vector
    assert "Missing observations are not zero" in vector
    assert 'data-decision-exposure="40"' in vector


def test_short_history_does_not_paint_the_null_hairline(tmp_path, monkeypatch):
    _require_t19p("crypto.html.j2", "market.history.dates|length >= 4")
    for n in (2, 3):
        case = _crypto_case("valid_zero")
        case["market"] = _market(dates=_HISTORY[:n], vals=[2.1e12, 2.15e12, 2.2e12][:n])
        dest = tmp_path / f"h{n}"
        dest.mkdir()
        crypto = _render_crypto(dest, monkeypatch, case)
        overview = _slice(crypto, 'id="crypto-overview"', 'id="universe-snapshot"')
        assert "ilx-null" not in overview, f"{n}-point history painted the ilx-null hairline"
        assert 'data-market-history-state="unavailable"' in overview
        assert "ilx-path" not in overview


def test_altseason_none_does_not_paint_a_zero_rail(tmp_path, monkeypatch):
    _require_t19p(
        "crypto.html.j2",
        'meter-rail"><i{% if market.heat.altseason.value is not none %} style="width:{{ market.heat.altseason.value }}%"',
    )
    crypto = _render_crypto(tmp_path, monkeypatch, _crypto_case("valid_zero"))
    heat = _slice(crypto, 'id="leverage-heat"', 'id="allocation"')
    rail = _slice(heat, 'class="meter-rail"', ">")
    assert "--v:0%" not in heat
    assert "style=" not in rail
    assert "style=" not in _slice(heat, 'class="meter-rail"', "</div>")
    assert ">—<" in heat


def test_vector_quote_none_renders_without_a_number():
    _require_t19p(
        "vector.html.j2",
        '{% if price is not none %}${{ "{:,.0f}".format(price) }}',
    )
    try:
        html = _render_vector(_vector_case("valid_zero"), price=None, chg24=None)
    except Exception as exc:
        pytest.fail(f"vector quote None did not render: {type(exc).__name__}: {exc}")
    quote = _slice(html, 'class="live-quote"', 'class="asof-chip"')
    assert "—" in quote
    assert re.search(r"\d", quote) is None
    assert "pos" not in quote
    assert "neg" not in quote


def test_s2_withholds_risk_word_when_index_is_none():
    _require_t19p(
        "vector.html.j2",
        "{% if risk_index is not none %}{{ risk_index }}/100{% else %}—{% endif %}",
    )
    html = _render_vector(_vector_case("valid_zero"))
    ctx = _slice(html, 'class="risk-context"', "</div>")
    assert "高风险" not in ctx
    assert "低风险" not in ctx
    assert "/100" not in ctx
    assert "暂无" in ctx
    assert "—" in ctx


# --- R12 design-review repair: basis words, Tier-2 stale readings, sign before symbol.

_STALE_EN = "Stale — later than this source's cadence"
_STALE_ZH = "过期 — 晚于该来源的发布节奏"


def _reading(lang: str, fragment: str) -> str:
    """What a reader in one language sees: drop the other language's spans, then all tags."""
    other = "l-zh" if lang == "en" else "l-en"
    kept = re.sub(rf'<span class="{other}">.*?</span>', "", fragment, flags=re.S)
    return re.sub(r"<[^>]+>", "", kept)


def _div_text(block: str, cls: str) -> str:
    return re.sub(r"<[^>]+>", "", _slice(block, f'<div class="{cls}">', "</div>"))


def _etf_block(html: str) -> str:
    return _slice(html, "US spot-BTC ETFs · 5D", "Stablecoin supply · 30D")


def _stable_block(html: str) -> str:
    return _slice(html, "Stablecoin supply · 30D", "Spot participation proxy")


def test_splice_line_speaks_words_not_codes(tmp_path, monkeypatch):
    case = _crypto_case("valid_zero")
    case["market"]["cap_basis"] = {"splices": [{
        "date": "2026-08-01", "from_basis": "derived", "to_basis": "direct",
        "from_label_en": "derived total", "from_label_zh": "推算总量",
        "to_label_en": "direct total", "to_label_zh": "直接总量",
        "support_before": 120, "support_after": 40,
    }]}
    crypto = _render_crypto(tmp_path, monkeypatch, case)
    line = _slice(crypto, '<p class="desk-splice">', "</p>")
    zh = _reading("zh", line)
    for word in ("derived", "direct", "support"):
        assert word not in zh.lower()
    assert "推算总量" in zh and "直接总量" in zh and "在册天数" in zh
    en = _reading("en", line)
    assert "derived total" in en and "direct total" in en and "days on file" in en
    assert "support" not in en.lower()
    assert "120/40" in en


def test_stale_etf_reading_moves_to_receipt(tmp_path, monkeypatch):
    case = _crypto_case("valid_zero")
    case["market"]["flows"]["etf"] = {
        "kind": "subscription", "value": -505.0, "latest": -120.0,
        "state": "Unavailable", "tone": "neutral", "as_of": "2026-10-09",
        "observation": "stale", "observation_label_en": _STALE_EN,
        "observation_label_zh": _STALE_ZH, "percentile": None,
    }
    crypto = _render_crypto(tmp_path, monkeypatch, case)
    etf = _etf_block(crypto)
    reading = _div_text(etf, "reading")
    assert reading == "—"
    assert "505" not in reading
    receipt = re.sub(r"<[^>]+>", "", etf[etf.index('class="receipt"'):])
    assert "-$505M" in receipt
    assert "Last on file" in receipt and "最近在册" in receipt
    assert "2026-10-09" in receipt
    assert "$-" not in crypto


def test_stale_stablecoin_reading_moves_to_receipt(tmp_path, monkeypatch):
    case = _crypto_case("valid_zero")
    case["market"]["flows"]["stablecoins"] = {
        "kind": "supply", "value": 1.6e11, "change_30d_usd": -2.5e9,
        "change_30d_pct": -1.6, "state": "Unavailable", "tone": "neutral",
        "as_of": "2026-10-09", "observation": "stale",
        "observation_label_en": _STALE_EN, "observation_label_zh": _STALE_ZH,
        "percentile": None,
    }
    crypto = _render_crypto(tmp_path, monkeypatch, case)
    block = _stable_block(crypto)
    assert _div_text(block, "reading") == "—"
    label = _div_text(block, "read-label")
    assert "·" not in label and "%" not in label
    receipt = re.sub(r"<[^>]+>", "", block[block.index('class="receipt"'):])
    assert "-$2.5B" in receipt and "Last on file" in receipt and "2026-10-09" in receipt
    assert "$-" not in crypto


def test_live_negative_flow_puts_sign_before_symbol(tmp_path, monkeypatch):
    assert build_crypto._signed_musd(-505) == "-$505M"
    assert build_crypto._signed_musd(505) == "+$505M"
    assert build_crypto._signed_musd(None) == "—"
    assert build_crypto._money(-2.5e9, compact=True, signed=True) == "-$2.5B"
    assert build_crypto._money(2.5e9, compact=True, signed=True) == "+$2.5B"
    assert build_crypto._money(-2.5e9, compact=True) == "$-2.5B"  # unsigned path unchanged
    case = _crypto_case("valid_zero")
    case["market"]["flows"]["etf"] = {
        "kind": "subscription", "value": -505.0, "latest": -120.0,
        "state": "Falling", "tone": "bear", "as_of": "2026-10-12",
        "observation": "current", "observation_label_en": "Current print",
        "observation_label_zh": "已有最新发布", "percentile": None,
    }
    crypto = _render_crypto(tmp_path, monkeypatch, case)
    etf = _etf_block(crypto)
    assert _div_text(etf, "reading") == "-$505M"
    assert "Last on file" not in etf
    assert "$-" not in crypto


# cx-p2-polish: a receipt phrase is one unbreakable unit, never split mid-date or mid-fraction.
_NOWRAP_OPEN = '<span class="receipt-nowrap">'


def _nowrap_units(fragment: str) -> list:
    """Inner HTML of every receipt-nowrap span, balanced over the nested language spans."""
    units, pos = [], fragment.find(_NOWRAP_OPEN)
    while pos != -1:
        i, depth = pos + len(_NOWRAP_OPEN), 1
        while depth:
            nxt_open, nxt_close = fragment.find("<span", i), fragment.find("</span>", i)
            assert nxt_close != -1, "unbalanced receipt-nowrap span"
            if nxt_open != -1 and nxt_open < nxt_close:
                depth, i = depth + 1, nxt_open + len("<span")
            else:
                depth, i = depth - 1, nxt_close + len("</span>")
        units.append(fragment[pos + len(_NOWRAP_OPEN): i - len("</span>")])
        pos = fragment.find(_NOWRAP_OPEN, i)
    return units


def test_cxp2_polish_stale_etf_value_and_date_are_one_nowrap_unit(tmp_path, monkeypatch):
    case = _crypto_case("valid_zero")
    case["market"]["flows"]["etf"] = {
        "kind": "subscription", "value": -505.0, "latest": -120.0,
        "state": "Unavailable", "tone": "neutral", "as_of": "2026-10-08",
        "observation": "stale", "observation_label_en": _STALE_EN,
        "observation_label_zh": _STALE_ZH, "percentile": None,
    }
    etf = _etf_block(_render_crypto(tmp_path, monkeypatch, case))
    units = _nowrap_units(etf[etf.index('class="receipt"'):])
    assert len(units) == 1
    en, zh = _reading("en", units[0]), _reading("zh", units[0])
    assert "Last on file" in en and "最近在册" in zh
    for text in (en, zh):
        assert "-$505M" in text and "2026-10-08" in text
        assert text.index("-$505M") < text.index("·") < text.index("2026-10-08")
        assert not text.lstrip().startswith("·")
    assert _STALE_EN not in units[0] and _STALE_ZH not in units[0]


def test_cxp2_polish_stale_stablecoin_value_and_date_are_one_nowrap_unit(tmp_path, monkeypatch):
    case = _crypto_case("valid_zero")
    case["market"]["flows"]["stablecoins"] = {
        "kind": "supply", "value": 1.6e11, "change_30d_usd": -2.5e9,
        "change_30d_pct": -1.6, "state": "Unavailable", "tone": "neutral",
        "as_of": "2026-10-09", "observation": "stale",
        "observation_label_en": _STALE_EN, "observation_label_zh": _STALE_ZH,
        "percentile": None,
    }
    block = _stable_block(_render_crypto(tmp_path, monkeypatch, case))
    units = _nowrap_units(block[block.index('class="receipt"'):])
    assert len(units) == 1
    for lang in ("en", "zh"):
        text = _reading(lang, units[0])
        assert "-$2.5B" in text and "2026-10-09" in text
        assert text.index("-$2.5B") < text.index("·") < text.index("2026-10-09")
        assert not text.lstrip().startswith("·")


def test_cxp2_polish_splice_fraction_sits_inside_nowrap_unit(tmp_path, monkeypatch):
    case = _crypto_case("valid_zero")
    case["market"]["cap_basis"] = {"splices": [{
        "date": "2026-08-01", "from_basis": "derived", "to_basis": "direct",
        "from_label_en": "derived total", "from_label_zh": "推算总量",
        "to_label_en": "direct total", "to_label_zh": "直接总量",
        "support_before": 1, "support_after": 5,
    }]}
    line = _slice(_render_crypto(tmp_path, monkeypatch, case), '<p class="desk-splice">', "</p>")
    units = _nowrap_units(line)
    assert len(units) == 1
    en, zh = _reading("en", units[0]), _reading("zh", units[0])
    assert "days on file" in en and "1/5" in en
    assert "在册天数" in zh and "1/5" in zh
    assert "·" not in en and "·" not in zh  # the leading separator stays outside the unit


def test_cxp2_polish_nowrap_rule_lives_in_the_receipt_style_owner():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "templates" / "crypto.html.j2").read_text(encoding="utf-8")
    style = src[src.index("<style>"):src.index("</style>")]
    assert ".sensor .receipt{" in style
    assert style.count(".receipt-nowrap{white-space:nowrap}") == 1
    assert src.count("<style>") == 1
