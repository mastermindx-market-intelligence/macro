from __future__ import annotations

from datetime import date, datetime, timezone
import json
import stat

import pandas as pd
import pytest

from engine import china_heatmap_live as contract
from scripts import build_china_heatmap_live as producer


NOW = datetime(2026, 9, 28, 2, 15, 40, tzinfo=timezone.utc)


def baseline_payload(asof: str = "2026-09-24") -> dict:
    return {
        "market": "china", "map_type": "stocks", "source": "daily-close",
        "asof": asof, "n_tiles": 2,
        "tiles": [
            {"t": "600519.SS", "sector": "Consumer", "size": 100.0, "perf": {"1D": 1.0}},
            {"t": "000001.SZ", "sector": "Financial", "size": 50.0, "perf": {"1D": -1.0}},
        ],
    }


def live_quotes(observed: datetime = datetime(2026, 9, 28, 2, 15, 30, tzinfo=timezone.utc)) -> dict:
    ts = int(observed.timestamp() * 1000)
    return {
        "600519.SS": {"price": 1412.8, "prevClose": 1398.0, "changePct": (1412.8 / 1398.0 - 1) * 100, "ts": ts, "open": 1399.5, "high": 1418.0, "low": 1390.1, "vol": 10, "amount": 100.0},
        "000001.SZ": {"price": 11.1, "prevClose": 11.2, "changePct": (11.1 / 11.2 - 1) * 100, "ts": ts - 1000, "open": 11.2, "high": 11.25, "low": 11.0, "vol": 20, "amount": 200.0},
    }


def pin_clock(monkeypatch, expected: datetime = NOW) -> None:
    monkeypatch.setattr(contract.cn_clock, "session_date", lambda now=None: date(2026, 9, 28))
    monkeypatch.setattr(contract.cn_clock, "last_completed_session", lambda now=None: "2026-09-24")
    monkeypatch.setattr(contract.cn_clock, "expected_latest_quote_time", lambda now=None: expected)


def test_fetch_tushare_snapshot_uses_one_whole_market_rt_k_call(monkeypatch) -> None:
    baseline = contract.validate_baseline(baseline_payload())
    seen = {}

    def query(api_name, fields="", **kwargs):
        seen.update(api_name=api_name, fields=fields, kwargs=kwargs)
        return pd.DataFrame([
            {"ts_code": "600519.SH", "pre_close": 1398.0, "close": 1412.8,
             "open": 1399.5, "high": 1418.0, "low": 1390.1, "vol": 10,
             "amount": 100.0, "trade_time": "2026-09-28 10:15:30"},
        ])

    monkeypatch.setattr(producer.tushare_client, "query", query)
    quotes = producer.fetch_tushare_snapshot(baseline)
    assert quotes and quotes["600519.SS"]["price"] == 1412.8
    assert seen["api_name"] == "rt_k"
    assert seen["kwargs"]["ts_code"] == "6*.SH,3*.SZ,0*.SZ"
    assert seen["kwargs"]["_timeout"] == 5.0
    assert seen["kwargs"]["_retries"] == 0
    assert seen["kwargs"]["_return_empty"] is True
    assert "trade_time" in seen["fields"].split(",")


@pytest.mark.parametrize("answer", [None, pd.DataFrame(columns=["ts_code", "trade_time"])])
def test_empty_or_unavailable_tushare_response_is_a_miss(monkeypatch, answer) -> None:
    baseline = contract.validate_baseline(baseline_payload())
    monkeypatch.setattr(producer.tushare_client, "query", lambda *a, **k: answer)
    assert producer.fetch_tushare_snapshot(baseline) is None


def test_one_shot_step_publishes_valid_atomic_payload(tmp_path, monkeypatch) -> None:
    pin_clock(monkeypatch)
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "live" / "china_heatmap.json"
    base.write_text(json.dumps(baseline_payload()), encoding="utf-8")
    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out,
        tushare_fetch=lambda baseline: live_quotes(),
        tencent_fetch=lambda baseline: pytest.fail("fallback must not run"),
        phase_fn=lambda now: "morning",
    )
    payload = instance.step(NOW, require_usable=True)
    assert json.loads(out.read_text(encoding="utf-8")) == payload
    assert payload["source"] == "tushare-rt-k" and payload["usable"] is True
    assert stat.S_IMODE(out.stat().st_mode) == 0o644
    assert not list(out.parent.glob(f".{out.name}.*"))


def test_one_shot_failure_never_replaces_last_accepted_file(tmp_path) -> None:
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "china_heatmap_live.json"
    base.write_text("{}", encoding="utf-8")
    out.write_text('{"accepted":true}\n', encoding="utf-8")
    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out,
        tushare_fetch=lambda baseline: live_quotes(),
        tencent_fetch=lambda baseline: {},
        phase_fn=lambda now: "morning",
    )
    with pytest.raises(contract.LiveContractError):
        instance.step(NOW, require_usable=True)
    assert out.read_text(encoding="utf-8") == '{"accepted":true}\n'


def test_fallback_is_throttled_and_reuses_original_source_clock(tmp_path, monkeypatch) -> None:
    pin_clock(monkeypatch)
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "china_heatmap_live.json"
    base.write_text(json.dumps(baseline_payload()), encoding="utf-8")
    calls = []

    def fallback(baseline):
        calls.append(True)
        return live_quotes()

    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out,
        tushare_fetch=lambda baseline: None,
        tencent_fetch=fallback,
        phase_fn=lambda now: "morning",
        fallback_interval=15,
    )
    first = instance.step(NOW)
    second = instance.step(NOW.replace(second=45))
    third = instance.step(NOW.replace(second=56))
    assert len(calls) == 2
    assert first["source"] == second["source"] == third["source"] == "tencent"
    assert first["source_observed_at"] == second["source_observed_at"]
    assert first["generated_at"] != second["generated_at"]


def test_failed_fallback_retains_last_good_without_restamping(tmp_path, monkeypatch) -> None:
    pin_clock(monkeypatch)
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "china_heatmap_live.json"
    base.write_text(json.dumps(baseline_payload()), encoding="utf-8")
    answers = iter([live_quotes(), {}])
    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out,
        tushare_fetch=lambda baseline: None,
        tencent_fetch=lambda baseline: next(answers),
        phase_fn=lambda now: "morning",
        fallback_interval=15,
    )
    first = instance.step(NOW)
    later = datetime(2026, 9, 28, 2, 15, 56, tzinfo=timezone.utc)
    second = instance.step(later)
    assert second["source"] == "tencent" and second["fallback"] is True
    assert second["source_observed_at"] == first["source_observed_at"]


@pytest.mark.parametrize("phase", ["session_break", "pre_open", "weekend", "holiday"])
def test_nontrading_phases_never_call_vendors(tmp_path, monkeypatch, phase: str) -> None:
    pin_clock(monkeypatch)
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "china_heatmap_live.json"
    base.write_text(json.dumps(baseline_payload()), encoding="utf-8")
    calls = []
    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out,
        tushare_fetch=lambda baseline: calls.append("tushare") or live_quotes(),
        tencent_fetch=lambda baseline: calls.append("tencent") or live_quotes(),
        phase_fn=lambda now: phase,
    )
    payload = instance.step(NOW)
    assert calls == []
    assert payload["usable"] is False and payload["source"] is None


def test_run_forever_uses_two_second_trading_cadence(tmp_path, monkeypatch) -> None:
    pin_clock(monkeypatch)
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "china_heatmap_live.json"
    base.write_text(json.dumps(baseline_payload()), encoding="utf-8")
    sleeps = []
    instance = None

    def sleeper(seconds):
        sleeps.append(seconds)
        instance.request_stop()

    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out,
        tushare_fetch=lambda baseline: live_quotes(),
        tencent_fetch=lambda baseline: {},
        phase_fn=lambda now: "morning", clock=lambda: NOW,
        sleeper=sleeper, interval=2,
    )
    instance.run_forever()
    assert sleeps == [2.0]
    assert json.loads(out.read_text())["source"] == "tushare-rt-k"


def test_run_forever_uses_heartbeat_cadence_off_tape(tmp_path, monkeypatch) -> None:
    pin_clock(monkeypatch)
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "china_heatmap_live.json"
    base.write_text(json.dumps(baseline_payload()), encoding="utf-8")
    sleeps = []
    instance = None

    def sleeper(seconds):
        sleeps.append(seconds)
        instance.request_stop()

    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out,
        tushare_fetch=lambda baseline: pytest.fail("vendor must not run"),
        tencent_fetch=lambda baseline: pytest.fail("vendor must not run"),
        phase_fn=lambda now: "session_break", clock=lambda: NOW,
        sleeper=sleeper, heartbeat_interval=30,
    )
    instance.run_forever()
    assert sleeps == [30.0]


def test_run_forever_stops_cleanly_on_keyboard_interrupt(tmp_path, monkeypatch) -> None:
    pin_clock(monkeypatch)
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "china_heatmap_live.json"
    base.write_text(json.dumps(baseline_payload()), encoding="utf-8")
    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out,
        tushare_fetch=lambda baseline: live_quotes(),
        tencent_fetch=lambda baseline: {},
        phase_fn=lambda now: "morning", clock=lambda: NOW,
        sleeper=lambda seconds: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    instance.run_forever()
    assert instance.stopped is True


def test_baseline_is_reloaded_after_atomic_replacement(tmp_path, monkeypatch) -> None:
    completed = {"day": "2026-09-24"}
    monkeypatch.setattr(contract.cn_clock, "session_date", lambda now=None: date(2026, 9, 28))
    monkeypatch.setattr(contract.cn_clock, "last_completed_session", lambda now=None: completed["day"])
    monkeypatch.setattr(contract.cn_clock, "expected_latest_quote_time", lambda now=None: NOW)
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "china_heatmap_live.json"
    base.write_text(json.dumps(baseline_payload()), encoding="utf-8")
    seen = []

    def fetch(baseline):
        seen.append(baseline.asof)
        return live_quotes()

    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out, tushare_fetch=fetch,
        tencent_fetch=lambda baseline: {}, phase_fn=lambda now: "morning",
    )
    first = instance.step(NOW)
    replacement = tmp_path / "replacement.json"
    replacement.write_text(json.dumps(baseline_payload("2026-09-25")), encoding="utf-8")
    replacement.replace(base)
    completed["day"] = "2026-09-25"
    second = instance.step(NOW)
    assert seen == ["2026-09-24", "2026-09-25"]
    assert first["baseline_asof"] == "2026-09-24"
    assert second["baseline_asof"] == "2026-09-25"


def test_transient_fetch_exception_keeps_valid_last_good_output(tmp_path, monkeypatch) -> None:
    pin_clock(monkeypatch)
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "china_heatmap_live.json"
    base.write_text(json.dumps(baseline_payload()), encoding="utf-8")
    answers = iter([live_quotes(), RuntimeError("temporary")])

    def fetch(baseline):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out, tushare_fetch=fetch,
        tencent_fetch=lambda baseline: {}, phase_fn=lambda now: "morning",
        fallback_interval=60,
    )
    first = instance.step(NOW)
    second = instance.step(NOW.replace(second=41))
    assert second["source_observed_at"] == first["source_observed_at"]
    assert contract.validate_live_payload(second, contract.validate_baseline(baseline_payload()), now=NOW.replace(second=41)) == second


def test_low_coverage_primary_falls_through_to_full_fallback(tmp_path, monkeypatch) -> None:
    pin_clock(monkeypatch)
    base = tmp_path / "china_heatmap.json"
    out = tmp_path / "china_heatmap_live.json"
    base.write_text(json.dumps(baseline_payload()), encoding="utf-8")
    partial = {"600519.SS": live_quotes()["600519.SS"]}
    instance = producer.ChinaHeatmapLiveProducer(
        base_path=base, out_path=out,
        tushare_fetch=lambda baseline: partial,
        tencent_fetch=lambda baseline: live_quotes(),
        phase_fn=lambda now: "morning",
    )
    payload = instance.step(NOW)
    assert payload["source"] == "tencent"
    assert payload["fallback"] is True
    assert payload["coverage"] == 1.0 and payload["usable"] is True
