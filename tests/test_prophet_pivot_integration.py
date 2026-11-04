"""Optional timing observations use the incumbent pass, artifact and event spool.

All inputs are synthetic. Tests stub R2/vendor boundaries; no production data or
publication proof is implied. These tests cover integration boundaries, not the
pure engine's causal correctness; that separate acceptance remains required.
"""
from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timezone

import pytest

from scripts import prophet_live_evaluator as E

NOW = datetime(2026, 11, 3, 19, 45, tzinfo=timezone.utc)
STAMP = "2026-11-03T19:45:00Z"


def envelope():
    value = E._unavailable_pivot("synthetic_fixture", NOW)
    value.update(status="ok", source_admitted=True, input_kind="OBSERVED_MARKET",
                 tickers={"DEMO": {"state": "testing"}}, events=[event("e1")])
    return value


def event(identity):
    return {"event_id": identity, "kind": "pivot_checklist", "ticker": "DEMO",
            "at": STAMP, "state": "testing", "reason": "synthetic_fixture"}


def inputs_file(tmp_path):
    path = tmp_path / "pivot-inputs.json"
    path.write_text(json.dumps({"schema": "prophet.pivot_inputs/v1",
                               "quotes": {"DEMO": {"price": 100, "basis_id": "owner-basis",
                                                  "asof": STAMP}}}))
    return {"pivot_input_path": str(path)}


@pytest.mark.parametrize(("content", "reason"), [
    ("[]", "intraday_input_schema_mismatch"),
    ('{"schema":"other"}', "intraday_input_schema_mismatch"),
    ('{"schema":"prophet.pivot_inputs/v1","x":NaN}', "intraday_input_unreadable"),
    ("{broken", "intraday_input_unreadable"),
])
def test_input_parse_failures_are_typed(tmp_path, content, reason):
    path = tmp_path / "inputs.json"
    path.write_text(content)
    assert E.load_pivot_inputs({"pivot_input_path": str(path)}) == (None, reason)


def test_missing_disabled_and_oversized_inputs_are_distinct(tmp_path, monkeypatch):
    assert E.load_pivot_inputs({"pivot_input_path": ""}) == (None, "intraday_input_not_configured")
    assert E.load_pivot_inputs({"pivot_input_path": str(tmp_path / "absent")}) == (None, "intraday_input_missing")
    path = tmp_path / "large"
    path.write_bytes(b" " * 33)
    monkeypatch.setattr(E, "PIVOT_INPUT_MAX_BYTES", 32)
    assert E.load_pivot_inputs({"pivot_input_path": str(path)}) == (None, "intraday_input_too_large")


def test_missing_input_cannot_reuse_previous_positive_state(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "_assess_pivot", lambda *a, **k: pytest.fail("no qualified input"))
    previous = {"pivot_checklist": {**envelope(), "recent_events": [event("old")]}}
    art = {"meta": {}, "states": {"DEMO": {"state": "holding"}}}
    assert E.attach_pivot_checklist(art, previous, {"pivot_input_path": ""}, NOW) == []
    assert art["pivot_checklist"]["status"] == "unavailable"
    assert art["pivot_checklist"]["tickers"] == {}
    assert art["pivot_checklist"]["recent_events"] == [event("old")]
    assert all(v is False for v in art["pivot_checklist"]["authority"].values())
    assert art["states"]["DEMO"]["state"] == "holding"


def test_qualified_quote_input_is_forwarded_without_relabelling(tmp_path, monkeypatch):
    block = inputs_file(tmp_path)
    seen = {}

    def assess(inputs, quotes, prior, *, now):
        seen.update(inputs=inputs, quotes=quotes, prior=prior, now=now)
        return envelope()

    monkeypatch.setattr(E, "_assess_pivot", assess)
    prior = {"recent_events": [event(str(n)) for n in range(100)] + [event("e1")]}
    art = {"meta": {}}
    events = E.attach_pivot_checklist(art, {"pivot_checklist": prior}, block, NOW)
    assert seen["quotes"] == seen["inputs"]["quotes"]
    assert seen["quotes"]["DEMO"]["basis_id"] == "owner-basis"
    assert events == [event("e1")]
    assert len(art["pivot_checklist"]["recent_events"]) == 64
    assert sum(e["event_id"] == "e1" for e in art["pivot_checklist"]["recent_events"]) == 1


@pytest.mark.parametrize("failure", ["exception", "authority", "nan", "event_id", "not_json"])
def test_optional_engine_failure_is_isolated(tmp_path, monkeypatch, failure):
    def assess(*args, **kwargs):
        if failure == "exception":
            raise RuntimeError("broken optional evaluator")
        result = envelope()
        if failure == "authority":
            result["authority"]["may_trade"] = True
        elif failure == "nan":
            result["tickers"]["DEMO"]["price"] = float("nan")
        elif failure == "event_id":
            del result["events"][0]["event_id"]
        elif failure == "not_json":
            result["unexpected"] = object()
        return result
    monkeypatch.setattr(E, "_assess_pivot", assess)
    art = {"meta": {}, "states": {"DEMO": {"state": "holding"}}}
    assert E.attach_pivot_checklist(art, None, inputs_file(tmp_path), NOW) == []
    assert art["pivot_checklist"]["reason"] == "pivot_evaluation_failed"
    assert art["pivot_checklist"]["status"] == "unavailable"
    assert art["pivot_checklist"]["tickers"] == {}
    assert art["states"]["DEMO"]["state"] == "holding"
    json.dumps(art, allow_nan=False)


def lane(tmp_path, monkeypatch):
    block = inputs_file(tmp_path)
    served = tmp_path / "public" / "live"
    served.mkdir(parents=True)
    block.update(served_path=str(served / "prophet_live.json"), local_quote_paths=[])
    last = E.LS.last_completed_session(NOW)
    pack = {"schema": "prophet_live.armed/v1", "as_of": last, "names": {
        "DEMO": {"state": "buyable", "center_buyable": True, "as_of_close": 100,
                 "bar_date": last, "probed": True, "buyable_in_band": True,
                 "fade_px": 90, "fade_hi_px": 110, "band_lo_px": 85, "band_hi_px": 115}},
        "meta": {"universe_n": 1, "probed_n": 1, "armed_n": 1}}
    writes = {}
    monkeypatch.setattr(E.r2io, "client", lambda: object())
    monkeypatch.setattr(E.r2io, "get_json", lambda key, **kw: pack if key == E.r2io.PACK_KEY else None)
    monkeypatch.setattr(E.r2io, "put_json", lambda key, payload, **kw:
                        writes.__setitem__(key, copy.deepcopy(payload)) or True)
    monkeypatch.setattr(E, "load_quotes", lambda *a: {
        "quotes": {"DEMO": {"price": 100, "prev_close": 100, "basis": "trade"}},
        "asof": STAMP, "source": "synthetic_fixture", "feed_delay_min": 15})
    monkeypatch.setattr(E, "quote_ager", lambda *a: lambda q: 1)
    monkeypatch.setattr(E, "_assess_pivot", lambda *a, **kw: envelope())
    conf = {"live": {"delayed_min": 15}, "prophet_live": block}
    return conf, writes, served / "prophet_live.json"


def test_real_pass_publishes_same_artifact_and_sibling_observations(tmp_path, monkeypatch):
    conf, writes, served = lane(tmp_path, monkeypatch)
    assert E.run(tmp_path, now=NOW, cfg=conf, require_publish=True) == 0
    live = writes[E.r2io.LIVE_KEY]
    assert live["pivot_checklist"]["status"] == "ok"
    assert live["meta"]["pivot_events_n"] == 1
    assert json.loads(served.read_text()) == live
    spools = [v for k, v in writes.items() if k != E.r2io.LIVE_KEY]
    assert len(spools) == 1
    assert spools[0]["pivot_events"] == [event("e1")]
    assert all(e["kind"] != "pivot_checklist" for e in spools[0]["events"])


def test_missing_optional_core_preserves_real_pass_publication(tmp_path, monkeypatch):
    from engine import prophet_live

    actual_assess = E._assess_pivot
    conf, writes, served = lane(tmp_path, monkeypatch)
    monkeypatch.setattr(E, "_assess_pivot", actual_assess)
    monkeypatch.delattr(prophet_live, "pivot_checklist", raising=False)
    monkeypatch.setitem(sys.modules, "engine.prophet_live.pivot_checklist", None)
    assert E.run(tmp_path, now=NOW, cfg=conf, require_publish=True) == 0
    live = writes[E.r2io.LIVE_KEY]
    pivot = live["pivot_checklist"]
    assert (pivot["status"], pivot["reason"]) == ("unavailable", "pivot_evaluation_failed")
    assert pivot["tickers"] == {}
    assert all(value is False for value in pivot["authority"].values())
    assert live["meta"]["pivot_events_n"] == 0
    assert live["states"]
    assert json.loads(served.read_text()) == live
    assert all(not payload.get("pivot_events") for key, payload in writes.items()
               if key != E.r2io.LIVE_KEY)


def test_dry_run_writes_neither_existing_publication_plane(tmp_path, monkeypatch):
    conf, writes, served = lane(tmp_path, monkeypatch)
    assert E.run(tmp_path, now=NOW, cfg=conf, dry_run=True) == 0
    assert writes == {}
    assert not served.exists()


def test_failed_optional_journal_publication_is_reported(tmp_path, monkeypatch, capsys):
    conf, writes, served = lane(tmp_path, monkeypatch)
    monkeypatch.setattr(E.r2io, "put_json", lambda key, payload, **kw: key == E.r2io.LIVE_KEY)
    assert E.run(tmp_path, now=NOW, cfg=conf, require_publish=True) == 3
    assert "1 pivot observations are not" in capsys.readouterr().out
    assert served.exists()


def test_core_publication_failure_is_not_hidden_by_optional_isolation(tmp_path, monkeypatch):
    conf, writes, served = lane(tmp_path, monkeypatch)

    def broken(*args, **kwargs):
        raise RuntimeError("core publication failed")

    monkeypatch.setattr(E.r2io, "put_json", broken)
    with pytest.raises(RuntimeError, match="core publication"):
        E.run(tmp_path, now=NOW, cfg=conf, require_publish=True)


def test_pivot_observations_do_not_enter_the_incumbent_trade_grader(monkeypatch):
    from scripts import reconcile_prophet_live as R
    spool = {"session_et": "2026-11-03", "pack_as_of": "2026-11-02",
             "events": [{"ticker": "DEMO", "kind": "forming", "price": 100}],
             "pivot_events": [event("research-only")]}
    monkeypatch.setattr(R.r2io, "get_json", lambda *a, **kw: spool)
    rows = R.load_events(["synthetic-spool"], s3=object())
    assert len(rows) == 1
    assert rows[0]["kind"] == "forming"
    assert all(row.get("event_id") != "research-only" for row in rows)
