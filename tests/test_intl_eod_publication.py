"""End-to-end owner-evaluator checks for source-bound delayed R10 returns."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pandas as pd
import pytest

from engine import intl_inputs
from engine.intl_workspace_overview import build_workspace_overviews
from lib.intl_eod_publication import build_eod_inputs

EVALUATED = "2026-10-09T20:30:00+00:00"
GRANT = {
    "status": "confirmed",
    "scope": "intl-index-fx-eod-user-facing-v1",
    "decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
}
GENERATION = "im-workspace-generation:df4a2d6b-aed5-4d0c-a211-68f3a4627eb4"


def _setup(tmp_path, *, omit=None, late=True):
    # Last bar is 2026-10-07: a completed historical session, never the
    # 2026-10-09 developing daily bar. Use real configured identifiers.
    dates = pd.bdate_range(end="2026-10-07", periods=280)
    series = []
    for cc, market in intl_inputs.countries().items():
        for symbol in (market["index"], market["fx"]):
            if symbol not in series:
                series.append(symbol)
    cols = {}
    for slot, symbol in enumerate(series):
        if symbol == omit:
            continue
        value = [float(100 + slot * 4 + 0.125 * i) for i in range(len(dates))]
        cols[symbol] = pd.Series(value, index=dates)
        path = tmp_path / "intl" / (symbol.replace("^","_").replace("=","_").replace("/","_") + ".parquet")
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"close": value}, index=dates).to_parquet(path)
    frame = pd.DataFrame(cols).sort_index()
    status = {"sources": {"intl_prices": {
        "source": "intl_prices", "status": "ok",
        "checked_at": "2026-10-09T15:00:00+00:00" if late else "2026-10-06T15:00:00+00:00",
        "last_date": "2026-10-07",
    }}}
    (tmp_path / "run_status.json").write_text(json.dumps(status), encoding="utf-8")
    return frame, series


def _overview(frame, inputs):
    return build_workspace_overviews(
        frame, production_inputs=inputs, workspace_generation=GENERATION)


def _panel(workspace, horizon="1m", basis="usd_unhedged"):
    return next(p["overview"] for p in workspace["panels"]
                if p["overview"]["context"]["horizon"] == horizon
                and p["overview"]["context"]["currency_basis"] == basis)


def test_all_seven_real_owner_pair_returns_admit_with_source_receipts(tmp_path):
    frame, series = _setup(tmp_path)
    result = build_eod_inputs(frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT)
    assert result is not None
    delayed, inputs = result
    assert len(inputs["source_evidence"]) == len(series) == 14
    assert len(inputs["disclosure_decisions"]) == 7 * 5 * 2 * 3
    assert all(q["calendar_ref"].startswith("intl-conservative-observed-eod")
               for q in inputs["source_evidence"])
    built = _overview(delayed, inputs)
    usd = _panel(built)
    local = _panel(built, basis="local")
    assert usd["eligible_count"] == local["eligible_count"] == 7
    for u, l in zip(usd["rows"], local["rows"]):
        assert u["market_id"] == l["market_id"]
        assert u["metric"]["quality"] == l["metric"]["quality"] == "qualified"
        assert u["usd"]["value"] is not None
        assert l["local"]["value"] is not None
        assert u["fx_contribution"]["value"] == pytest.approx(
            u["usd"]["value"] - u["local"]["value"], abs=1e-10)
    assert usd["ranking_status"] == "available"
    assert delayed.index[-1].date().isoformat() == "2026-10-07"


@pytest.mark.parametrize("bad", [
    {}, {"status": "unknown", "scope": GRANT["scope"], "decision_ref": GRANT["decision_ref"]},
    {"status": "confirmed", "scope": "any-data", "decision_ref": GRANT["decision_ref"]},
    {"status": "confirmed", "scope": GRANT["scope"], "decision_ref": ""},
])
def test_no_unconfirmed_or_overbroad_grant(tmp_path, bad):
    frame, _ = _setup(tmp_path)
    assert build_eod_inputs(frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=bad) is None


def test_stale_or_failed_collector_does_not_grant_any_values(tmp_path):
    frame, _ = _setup(tmp_path, late=False)
    assert build_eod_inputs(frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT) is None
    status_path = tmp_path / "run_status.json"
    status = json.loads(status_path.read_text())
    status["sources"]["intl_prices"].update(checked_at="2026-10-09T15:00:00+00:00", status="failed")
    status_path.write_text(json.dumps(status))
    assert build_eod_inputs(frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT) is None


def test_mismatched_persisted_series_is_withheld_without_poisoning_other_markets(tmp_path):
    frame, _ = _setup(tmp_path)
    path = tmp_path / "intl" / "_N225.parquet"
    stored = pd.read_parquet(path)
    stored.iloc[-1, 0] = 123456.0
    stored.to_parquet(path)
    delayed, inputs = build_eod_inputs(
        frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT)
    assert not any(e["series_id"] == "^N225" for e in inputs["source_evidence"])
    o = _panel(_overview(delayed, inputs), basis="local")
    japan = next(r for r in o["rows"] if r.get("market_id") == "JP")
    korea = next(r for r in o["rows"] if r.get("market_id") == "KR")
    assert japan["metric"]["value"] is None
    assert korea["metric"]["value"] is not None


def test_missing_fx_keeps_local_prices_but_withholds_usd(tmp_path):
    frame, _ = _setup(tmp_path, omit="USDJPY=X")
    delayed, inputs = build_eod_inputs(
        frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT)
    o_local = _panel(_overview(delayed, inputs), basis="local")
    o_usd = _panel(_overview(delayed, inputs))
    loc = next(r for r in o_local["rows"] if r.get("market_id") == "JP")
    usd = next(r for r in o_usd["rows"] if r.get("market_id") == "JP")
    assert loc["metric"]["value"] is not None
    assert usd["metric"]["value"] is None


def test_developing_bar_is_not_published_or_used_to_forge_completion(tmp_path):
    frame, _ = _setup(tmp_path)
    # A partial tip today is explicitly excluded even if the saved file holds it.
    today = pd.Timestamp("2026-10-09")
    frame.loc[today, frame.columns] = 999999.0
    for symbol in frame:
        path = tmp_path / "intl" / (symbol.replace("^","_").replace("=","_").replace("/","_") + ".parquet")
        stored = pd.read_parquet(path)
        stored.loc[today, "close"] = 999999.0
        stored.to_parquet(path)
    delayed, inputs = build_eod_inputs(
        frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT)
    assert delayed.index[-1].date().isoformat() == "2026-10-07"
    assert all("2026-10-09" not in e["latest_completed_observation"]
               for e in inputs["source_evidence"])
    assert _panel(_overview(delayed, inputs))["eligible_count"] == 7


def test_future_collector_stamp_and_invalid_frame_refused(tmp_path):
    frame, _ = _setup(tmp_path)
    status_path = tmp_path / "run_status.json"
    status = json.loads(status_path.read_text())
    status["sources"]["intl_prices"]["checked_at"] = "2026-10-10T15:00:00+00:00"
    status_path.write_text(json.dumps(status))
    assert build_eod_inputs(frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT) is None
    status["sources"]["intl_prices"]["checked_at"] = "2026-10-09T15:00:00+00:00"
    status_path.write_text(json.dumps(status))
    bad = frame.iloc[::-1]
    assert build_eod_inputs(bad, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT) is None


def test_normal_international_publisher_consumes_completed_eod_package(tmp_path):
    from scripts import build_intl as publisher
    frame, _ = _setup(tmp_path)
    ws = publisher._publication_workspace(
        frame, data_root=tmp_path, evaluated_at=EVALUATED)
    assert ws is not None
    usd = _panel(ws)
    assert usd["eligible_count"] == 7
    assert ws["binding_version"] == 2
    assert "intl-supplied-close:sha256:" in usd["context"]["source_reference"]


def test_normal_publisher_keeps_safe_unavailable_on_status_failure(tmp_path):
    from scripts import build_intl as publisher
    frame, _ = _setup(tmp_path, late=False)
    ws = publisher._publication_workspace(
        frame, data_root=tmp_path, evaluated_at=EVALUATED)
    assert ws is not None
    usd = _panel(ws)
    assert usd["eligible_count"] == 0
    assert usd["ranking_reason"] == "no_qualified_returns"


def test_delayed_source_notice_and_actual_window_dates_are_rendered(tmp_path):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    frame, _ = _setup(tmp_path)
    delayed, inputs = build_eod_inputs(
        frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT)
    panel = _panel(_overview(delayed, inputs))
    loader = FileSystemLoader(str(Path(__file__).resolve().parents[1] / "templates"))
    page = Environment(loader=loader, autoescape=True).get_template(
        "intl_workspace/overview.html.j2").render(
        overview=panel, context_id="test-eod", generation=GENERATION)
    assert 'data-im-eod-disclosure' in page
    assert "at least 2 calendar days" in page
    assert "2026-10-07" in page
    assert "<time " in page
