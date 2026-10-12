"""Elapsed coverage and funding semantics for the derivatives flow view.

Descriptive only. A null stays unavailable. Row count is not elapsed time.
Predicted funding is not a settled payment. Native aggressor units are not
USD spot inflow.
"""
from __future__ import annotations

import ast
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors import _crypto_observations as obs  # noqa: E402
from engine import btc_intraday_cvd as CVD  # noqa: E402

PATCHES = ROOT / "research" / "crypto_science" / "patches"
VECTOR_PATCH = PATCHES / "cx-t09-20261012__build_vector.py.patch"
TEMPLATE_PATCH = PATCHES / "cx-t09-20261012__vector.html.j2.patch"

SPAN_33 = {
    "rows": 24,
    "first_ts": "2026-01-01 00:00:00",
    "last_ts": "2026-01-02 09:00:00",
    "elapsed_hours": 33.0,
    "completeness": "incomplete",
}

FORBIDDEN = (
    "USD spot inflow",
    "all-venue",
    "all venue",
    "net position",
    "absorption",
    "spot inflow",
)


def _span(hours):
    start = pd.Timestamp("2026-01-01 00:00:00")
    idx = pd.DatetimeIndex([start + pd.Timedelta(hours=int(h)) for h in hours])
    return pd.DataFrame(
        {"taker_buy_vol": np.full(len(idx), 2.0), "taker_sell_vol": np.full(len(idx), 1.0)},
        index=idx,
    )


def _read_okx(frame):
    def read(ns, nm):
        return frame if ns == "okx" and nm == "taker_volume_hourly" else None
    return read


def _apply(patch: Path, relative: str, dest_root: Path) -> Path:
    target = dest_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / relative, target)
    proc = subprocess.run(
        ["patch", "-p0", "--forward", "--batch", "--directory", str(dest_root), "--input", str(patch)],
        check=False, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"patch failed\n{proc.stdout}\n{proc.stderr}")
    return target


def _patched_view(tmp_path: Path):
    path = _apply(VECTOR_PATCH, "scripts/build_vector.py", tmp_path)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_derivatives_flow_view")
    ns = {"np": np, "pd": pd}
    exec(compile(ast.Module([node], type_ignores=[]), str(path), "exec"), ns)  # noqa: S102
    return ns["_derivatives_flow_view"]


def _funding(rate, realized, *, interval=None, at="2026-01-01T01:00:00Z"):
    row = {
        "instId": "BTC-USDT-SWAP", "instType": "SWAP",
        "fundingTime": "1767225600000", "fundingRate": rate, "realizedRate": realized,
        "formulaType": "withRate", "method": "current_period",
    }
    if interval is not None:
        row["fundingInterval"] = interval
    capture = obs.build_capture(
        "okx_funding", {"instId": "BTC-USDT-SWAP", "limit": "100"},
        {"code": "0", "data": [row]}, at,
    )
    events = obs.funding_asof(pd.DataFrame([capture]), "2026-01-01T02:00:00Z")
    assert len(events) == 1
    return events[0]


def _macros() -> str:
    return textwrap.dedent("""
        {% macro t(en, zh='') -%}
        <span class="l-en">{{ en }}</span><span class="l-zh">{{ zh if zh else en }}</span>
        {%- endmacro %}
        {% macro tone(tone) -%}
        {{- 'tone-up' if tone == 'bull' else ('tone-down' if tone == 'bear' else 'tone-flat') -}}
        {%- endmacro %}
    """)


def _render(source: str, **ctx) -> str:
    env = Environment(autoescape=False)
    return env.from_string(_macros() + source).render(
        fmt_money=lambda v, compact=False: "—" if v is None else f"{v}",
        fmt_pct=lambda v: "—" if v is None else f"{v}%",
        **ctx,
    )


def _vector_flow_source(text: str) -> str:
    fact_at = text.index('<div class="fact funding-qualification"')
    line_start = text.rfind('\n', 0, fact_at) + 1
    line_end = text.find('\n', fact_at)
    flow_at = text.index('{% set flow = derivatives_flow')
    end = text.index('</section>', flow_at) + len('</section>')
    return text[line_start:line_end] + "\n" + text[flow_at:end]


def _section(html: str, marker: str, stop: str) -> str:
    return html.split(marker, 1)[1].split(stop, 1)[0]


def test_33h_window_carries_exact_elapsed_coverage_and_is_not_complete(monkeypatch, tmp_path):
    frame = _span(list(range(23)) + [33])
    monkeypatch.setattr(CVD.store, "read", _read_okx(frame))
    raw = CVD.compute(as_of="2026-01-02T09:00:00Z")
    assert raw["elapsed_coverage"] == SPAN_33
    assert raw["window_24h_complete"] is False
    assert raw["flow_state"] == "unavailable"
    assert raw["net_flow_24h_mn"] is None and raw["volume_unit"] is None

    from scripts.build_vector import _derivatives_flow_view
    current = _derivatives_flow_view({"context_legs": {"intraday_cvd": raw}})
    assert current["state"] == "coverage_gap"
    assert current["window_24h_complete"] is False
    assert current["buy_share_pct"] is None

    view = _patched_view(tmp_path)
    projected = view({"context_legs": {"intraday_cvd": raw}})
    assert projected["elapsed_coverage"] == SPAN_33
    assert projected["state"] == "coverage_gap"
    assert projected["window_24h_complete"] is False
    assert projected["buy_share_pct"] is None
    assert projected["venue"] == "OKX"
    assert projected["instrument"] == "BTC derivatives"
    assert projected["unit"] == "unavailable"
    assert "net_flow_usd" not in projected

    hostile = dict(raw, n_hours=24, window_24h_complete=True, ok=True, buy_share_24h=0.5, flow_state="buy_dominant")
    refused = view({"context_legs": {"intraday_cvd": hostile}})
    assert refused["elapsed_coverage"] == SPAN_33
    assert refused["window_24h_complete"] is False
    assert refused["state"] == "coverage_gap"
    assert refused["buy_share_pct"] is None

    patched_tpl = _apply(TEMPLATE_PATCH, "templates/vector.html.j2", tmp_path / "tpl").read_text(encoding="utf-8")
    html = _render(_vector_flow_source(patched_tpl), derivatives_flow=projected)
    panel = _section(html, "data-flow-context", "</section>")
    assert "Incomplete 24-hour window" in panel and "24 小时窗口不完整" in panel
    assert "24" in panel and "2026-01-01 00:00:00" in panel and "2026-01-02 09:00:00" in panel
    assert "33.0" in panel and "incomplete" in panel and "不完整" in panel
    coverage_label = panel.split("24h / 72h", 1)[1].split("</dd>", 1)[0]
    assert "Complete" not in coverage_label and "完整" not in coverage_label
    assert "Unavailable" in coverage_label and "不可用" in coverage_label


def test_complete_hourly_window_still_projects_elapsed_coverage(monkeypatch, tmp_path):
    frame = _span(range(24))
    monkeypatch.setattr(CVD.store, "read", _read_okx(frame))
    raw = CVD.compute(as_of="2026-01-01T23:00:00Z")
    assert raw["elapsed_coverage"]["completeness"] == "complete"
    assert raw["elapsed_coverage"]["elapsed_hours"] == 23.0
    assert raw["window_24h_complete"] is True
    view = _patched_view(tmp_path)({"context_legs": {"intraday_cvd": raw}})
    assert view["state"] == "available"
    assert view["buy_share_pct"] == 66.7
    assert view["elapsed_coverage"]["completeness"] == "complete"
    assert view["window_24h_complete"] is True
    assert view["unit"] == "unavailable"


def test_malformed_complete_flag_does_not_invent_a_24h_window(tmp_path):
    view = _patched_view(tmp_path)
    raw = {
        "ok": True, "display_only": True, "causally_qualified": False,
        "scope": "OKX/BTC/CONTRACTS", "stale": False,
        "asof": "2026-01-02 09:00:00", "evaluated_at": "2026-01-02 09:00:00",
        "n_hours": 24, "window_24h_complete": True, "window_72h_complete": False,
        "gap_detected": False, "flow_state": "buy_dominant", "buy_share_24h": 0.5,
        "elapsed_coverage": dict(SPAN_33, completeness="complete"),
    }
    out = view({"context_legs": {"intraday_cvd": raw}})
    assert out["state"] == "unavailable"
    assert out["buy_share_pct"] is None
    assert out["elapsed_coverage"] is None
    assert out["window_24h_complete"] is False


def test_predicted_and_settled_funding_are_never_substituted():
    both = _funding("-0.0004", "0.00015")
    assert both["predicted_rate"] == pytest.approx(-0.0004)
    assert both["settled_rate"] == pytest.approx(0.00015)
    assert both["predicted_rate"] != both["settled_rate"]
    assert set(("predicted_rate", "settled_rate")) <= set(both)

    missing_settled = _funding("0.0002", "")
    assert missing_settled["predicted_rate"] == pytest.approx(0.0002)
    assert missing_settled["settled_rate"] is None

    missing_predicted = _funding("", "-0.00015")
    assert missing_predicted["predicted_rate"] is None
    assert missing_predicted["settled_rate"] == pytest.approx(-0.00015)
    assert "rate" not in missing_predicted
    assert "kind" not in missing_predicted or missing_predicted.get("kind") in ("predicted", "settled")


def test_negative_rate_and_genuine_zero_are_not_missing():
    zero_settled = _funding("-0.0002", "0")
    assert zero_settled["predicted_rate"] == pytest.approx(-0.0002)
    assert zero_settled["settled_rate"] == 0.0
    assert zero_settled["settled_rate"] is not None

    zero_predicted = _funding("0", "")
    assert zero_predicted["predicted_rate"] == 0.0
    assert zero_predicted["settled_rate"] is None

    negative_settled = _funding("0", "-0.0008")
    assert negative_settled["settled_rate"] == pytest.approx(-0.0008)
    assert negative_settled["predicted_rate"] == 0.0


def test_unknown_settlement_interval_withholds_annualization():
    event = _funding("0.0001", "-0.0002", interval="8")
    assumed_8h = event["settled_rate"] * 3 * 365 * 100
    assert event["interval_hours"] is None
    assert event["annualized_settled_pct"] is None
    assert event["annualized_settled_pct"] != assumed_8h
    assert assumed_8h != 0
    # A supplied interval string is still not evidence on this surface.
    again = _funding("0.0001", "0", interval="28800000")
    assert again["settled_rate"] == 0.0
    assert again["interval_hours"] is None
    assert again["annualized_settled_pct"] is None


def test_rendered_flow_names_scope_and_does_not_claim_usd_or_absorption(tmp_path):
    template = (ROOT / "templates" / "vector.html.j2").read_text(encoding="utf-8")
    desk = _section(template, 'id="derivatives-desk"', 'id="onchain-lab"')
    for phrase in FORBIDDEN:
        assert phrase not in desk
    assert "OKX" in desk and "BTC" in desk
    assert "Absolute units" in desk and "绝对单位" in desk
    assert "Not spot flow or a trading signal" in desk
    assert "并非现货资金流" in desk

    flow = {
        "state": "available", "buy_share_pct": 66.7,
        "observed_at": "2026-01-01 23:00 UTC", "evaluated_at": "2026-01-01 23:00 UTC",
        "window_24h_complete": True, "window_72h_complete": False, "n_hours": 24,
        "historical_gap": False, "venue": "OKX", "instrument": "BTC derivatives",
        "unit": "unavailable",
        "elapsed_coverage": {
            "rows": 24, "first_ts": "2026-01-01 00:00:00",
            "last_ts": "2026-01-01 23:00:00", "elapsed_hours": 23.0,
            "completeness": "complete",
        },
    }
    patched = _apply(TEMPLATE_PATCH, "templates/vector.html.j2", tmp_path).read_text(encoding="utf-8")
    html = _render(_vector_flow_source(patched), derivatives_flow=flow)
    panel = _section(html, "data-flow-context", "</section>")
    assert "66.7" in panel
    assert "Venue OKX · instrument BTC derivatives · unit unavailable" in panel
    assert "场所 OKX · 品种 BTC 衍生品 · 单位暂不可用" in panel
    for phrase in FORBIDDEN:
        assert phrase not in panel
    share = panel.split("data-flow-share", 1)[1].split("</div></div>", 1)[0]
    assert "66.7" in share and "Venue OKX" in share and "unit unavailable" in share

    builder = (ROOT / "scripts" / "build_vector.py").read_text(encoding="utf-8")
    fn = builder.split("def _derivatives_flow_view", 1)[1].split("\ndef main", 1)[0]
    crypto = (ROOT / "scripts" / "build_crypto.py").read_text(encoding="utf-8")
    for phrase in FORBIDDEN:
        assert phrase not in fn and phrase not in crypto


def test_funding_absent_leaves_flow_valid_and_withholds_only_funding_sentence(monkeypatch, tmp_path):
    frame = _span(range(24))
    monkeypatch.setattr(CVD.store, "read", _read_okx(frame))
    raw = CVD.compute(as_of="2026-01-01T23:00:00Z")
    assert raw["ok"] is True and raw["buy_share_24h"] == pytest.approx(2 / 3)
    assert obs.funding_asof(pd.DataFrame(), "2026-01-01T02:00:00Z") == []

    view = _patched_view(tmp_path)({"context_legs": {"intraday_cvd": raw}})
    assert view["state"] == "available" and view["buy_share_pct"] == 66.7
    patched = _apply(TEMPLATE_PATCH, "templates/vector.html.j2", tmp_path / "funding-absent")
    html = _render(_vector_flow_source(patched.read_text(encoding="utf-8")), derivatives_flow=view)
    assert "66.7" in html
    assert "Participation observed" in html and "成交参与度已观测" in html
    assert "Settlement interval not established" in html
    assert "结算间隔尚未确定" in html
    assert "data-funding-qualification" in html
    funding = html.split("data-funding-qualification", 1)[1].split("data-flow-context", 1)[0]
    assert "—" in funding and "66.7" not in funding

    crypto = (ROOT / "templates" / "crypto.html.j2").read_text(encoding="utf-8")
    etf = crypto.split('<div class="sensor {{ tone(market.flows.etf.tone) }}">', 1)[1]
    etf = '<div class="sensor {{ tone(market.flows.etf.tone) }}">' + etf.split('<div class="sensor {{ tone(market.flows.stablecoins.tone) }}">', 1)[0]
    heat = crypto.split('<div class="sensor tone-flat" data-crypto-funding-state="interval-unqualified">', 1)[1]
    heat = '<div class="sensor tone-flat" data-crypto-funding-state="interval-unqualified">' + heat.split('<div class="sensor {{ tone(market.heat.open_interest.tone) }}">', 1)[0]
    rendered = _render(etf + heat, market={"flows": {"etf": {
        "tone": "bull", "value": 150, "state": "Rising", "state_zh": "上升",
    }}})
    assert "$+150M" in rendered
    assert "Settlement interval not established" in rendered
    assert "尚未确认结算间隔" in rendered
    assert "fmt_pct(market.heat.funding.value)" not in heat
    withheld = rendered.split("data-crypto-funding-state", 1)[1]
    assert "150" not in withheld
    assert "—" in withheld


def test_cvd_absent_leaves_funding_event_and_withholds_only_flow_sentence(monkeypatch, tmp_path):
    monkeypatch.setattr(CVD.store, "read", lambda ns, nm: None)
    raw = CVD.compute(as_of="2026-01-02T09:00:00Z")
    assert raw["ok"] is False
    event = _funding("-0.0003", "0")
    assert event["predicted_rate"] == pytest.approx(-0.0003)
    assert event["settled_rate"] == 0.0
    assert event["annualized_settled_pct"] is None

    from scripts.build_vector import _derivatives_flow_view
    assert _derivatives_flow_view({"context_legs": {"intraday_cvd": raw}})["state"] == "unavailable"
    patched = _apply(TEMPLATE_PATCH, "templates/vector.html.j2", tmp_path).read_text(encoding="utf-8")
    html = _render(_vector_flow_source(patched), derivatives_flow={"state": "unavailable"})
    panel = _section(html, "data-flow-context", "</section>")
    assert "Activity unavailable" in panel and "成交活动暂不可用" in panel
    assert "Participation observed" not in panel
    assert "66.7" not in panel
    assert "—" in panel
    assert "Settlement interval not established" in html
    assert "结算间隔尚未确定" in html
    assert "data-elapsed-coverage" in panel
    assert "unavailable" in panel and "不可用" in panel


def test_patches_are_the_only_builder_and_template_delta():
    assert VECTOR_PATCH.is_file() and TEMPLATE_PATCH.is_file()
    vector = VECTOR_PATCH.read_text(encoding="utf-8")
    template = TEMPLATE_PATCH.read_text(encoding="utf-8")
    assert "elapsed_coverage" in vector and "venue='OKX'" in vector
    assert "Venue OKX · instrument BTC derivatives · unit unavailable" in template
    assert "场所 OKX · 品种 BTC 衍生品 · 单位暂不可用" in template
    assert "Elapsed coverage" in template and "已覆盖时长" in template
    assert "incomplete" in template and "不完整" in template
