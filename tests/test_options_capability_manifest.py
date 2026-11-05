"""Falsifier tests for the options_capability_manifest/v0 read-time adapter.

Eight falsifiers, each asserted RED for the deliberately wrong
``_NaiveAdapter`` (latches failed reads, trusts the transport mtime first,
derives captured counts from the compat alias) and GREEN for
``engine.options_capability_manifest.build_manifest``.  Every timestamp is
fixed in tests/fixtures/options_capability_manifest_v0.json; no test reads
real time.

Run: python3 -m pytest tests/test_options_capability_manifest.py -q
"""
from __future__ import annotations

import copy
import json
import sys
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engine.options_capability_manifest as manifest_module  # noqa: E402
from engine.options_capability_manifest import (  # noqa: E402
    CLAIM_CLASSES,
    READ_STATES,
    SCHEMA,
    build_manifest,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "options_capability_manifest_v0.json"
)
_RAW = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
NOW = datetime.fromisoformat(_RAW["now"])
SESSION = _RAW["session"]
CASES = _RAW["cases"]

TAPE = "option_flow.live_tape"
EOD = "option_flow.eod252_baseline"

_PURITY_TOKENS = (
    "open(",
    "os.stat",
    "Path(",
    "datetime.now",
    "time.time",
    "requests",
    "urllib",
    "built_at",
    "mtime",
    "http_status",
    "_transport",
    "computed_asof",
    "cadence_sec",
    "roots_polled",
    "fastapi",
    "MAX_AGE",
    "poll_floor_sec",
)


# --------------------------------------------------------------------------- harness

def _receipts(live_flow_meta=None, eod=None, session=SESSION):
    receipts = {}
    if session is not None:
        receipts["session"] = session
    if live_flow_meta is not None:
        receipts["live_flow_meta"] = live_flow_meta
    if eod is not None:
        receipts["eod252_baselines"] = eod
    return receipts


def _row_of(manifest, capability_id):
    for row in manifest["rows"]:
        if row["capability_id"] == capability_id:
            return row
    raise AssertionError(f"no row for {capability_id}")


def _tape_row(adapter, **kwargs):
    return _row_of(adapter(_receipts(**kwargs), NOW), TAPE)


class _NaiveAdapter:
    """The deliberately wrong reader: latches, trusts mtime, derives counts."""

    def __init__(self) -> None:
        self._latched: set[str] = set()

    def __call__(self, receipts, now):  # noqa: ARG002 - now ignored on purpose
        return {
            "rows": [
                self._row(TAPE, receipts.get("live_flow_meta")),
                self._row(EOD, receipts.get("eod252_baselines")),
            ]
        }

    def _row(self, capability_id, raw):
        if isinstance(raw, BaseException):
            self._latched.add(capability_id)
        populations = self._populations(raw)
        if capability_id in self._latched:
            return {
                "capability_id": capability_id,
                "read_state": "stale",
                "source_asof": None,
                "populations": populations,
                "reasons": [],
            }
        if not isinstance(raw, Mapping):
            return {
                "capability_id": capability_id,
                "read_state": "missing",
                "source_asof": None,
                "populations": populations,
                "reasons": [],
            }
        transport = raw.get("_transport", {})
        src = (
            transport.get("mtime")
            or raw.get("source_asof")
            or raw.get("asof")
            or raw.get("built_at")
        )
        state = "data" if (transport.get("http_status") == 200 or src) else "missing"
        return {
            "capability_id": capability_id,
            "read_state": state,
            "source_asof": src,
            "populations": populations,
            "reasons": [],
        }

    @staticmethod
    def _populations(raw):
        if not isinstance(raw, Mapping):
            return {
                "requested": 0,
                "configured": 0,
                "captured": 0,
                "qualified": 0,
                "displayed": 0,
            }
        return {
            "requested": raw.get("roots_requested", 0),
            "configured": raw.get("universe_n", 0),
            "captured": raw.get("roots_with_source_payload") or raw.get("universe_n") or 0,
            "qualified": 0,
            "displayed": 0,
        }


def _naive_adapter():
    return _NaiveAdapter()


def _null_adapter():
    """Second negative control: every value null except the capability_id lookup key."""
    names = ("census_observed_state", "source_family", "source_owner", "cohort", "session",
             "claim_class", "source_asof", "clock_provenance", "read_state", "entitlement",
             "accepted_use", "reasons")
    pops = ("requested", "configured", "captured", "qualified", "displayed")

    def adapter(receipts, now):  # noqa: ARG001 - inputs ignored on purpose
        rows = [
            {"capability_id": cid, **dict.fromkeys(names), "populations": dict.fromkeys(pops)}
            for cid in (TAPE, EOD)
        ]
        return {"rows": rows}

    return adapter


def _reasons(row) -> list:
    return list(row.get("reasons") or [])


# --------------------------------------------------------------------------- falsifiers

def _check_a(adapter) -> bool:
    row = _tape_row(adapter, live_flow_meta=CASES["v2_last_3h_old_fresh_mtime"])
    return (
        row["read_state"] == "data"
        and row["source_asof"] == "2026-10-21T16:00:00+00:00"
        and "no_threshold_source" in row["reasons"]
    )


def _check_b(adapter) -> bool:
    row = _tape_row(adapter, live_flow_meta=CASES["v1_meta_http200"])
    return row["read_state"] == "unknown" and row["source_asof"] is None


def _check_c(adapter) -> bool:
    row = _tape_row(adapter, live_flow_meta=CASES["v2_zero_captured"])
    return row["populations"]["captured"] == 0


def _check_d(adapter) -> bool:
    row = _tape_row(adapter, live_flow_meta=CASES["v2_counts_absent"])
    pops, reasons = row["populations"], _reasons(row)
    return (
        row["read_state"] == "data"
        and all(pops[f] is None for f in ("requested", "configured", "captured", "qualified"))
        and all("count_absent:" + f in reasons for f in ("requested", "configured", "captured"))
    )


def _check_e(adapter) -> bool:
    row = _tape_row(adapter, live_flow_meta=OSError("read failed"))
    return row["read_state"] == "failed_read"


def _check_f(adapter) -> bool:
    ooo = _tape_row(adapter, live_flow_meta=CASES["v2_out_of_order"])
    fut = _tape_row(adapter, live_flow_meta=CASES["v2_future_dated"])
    return (
        ooo["read_state"] == "unknown"
        and ooo["source_asof"] is None
        and fut["read_state"] == "unknown"
        and fut["source_asof"] is None
        and "clock_out_of_order" in _reasons(ooo)
        and "future_dated_clock" in _reasons(fut)
    )


def _check_g(adapter) -> bool:
    adapter(_receipts(live_flow_meta=OSError("read failed")), NOW)
    after_valid = adapter(_receipts(live_flow_meta=CASES["valid_v2_fresh"]), NOW)
    return _row_of(after_valid, TAPE)["read_state"] == "data"


def _check_h(adapter) -> bool:
    row = _tape_row(adapter, live_flow_meta=CASES["built_at_only"])
    return (
        row["read_state"] == "unknown"
        and row["source_asof"] is None
        and row.get("clock_provenance") is None
        and "no_accepted_clock" in _reasons(row)
    )


def test_falsifier_a_mtime_source_clock_wins():
    assert _check_a(build_manifest)
    assert not _check_a(_naive_adapter())


def test_falsifier_b_v1_schema_has_no_accepted_clock():
    assert _check_b(build_manifest)
    assert not _check_b(_naive_adapter())


def test_falsifier_c_zero_captured_is_kept():
    assert _check_c(build_manifest)
    assert not _check_c(_naive_adapter())


def test_falsifier_d_absent_counts_stay_null():
    assert _check_d(build_manifest)
    assert not _check_d(_naive_adapter())


def test_falsifier_e_raised_receipt_is_failed_read():
    assert _check_e(build_manifest)
    assert not _check_e(_naive_adapter())


def test_falsifier_f_out_of_order_and_future_are_unknown():
    assert _check_f(build_manifest)
    assert not _check_f(_naive_adapter())


def test_falsifier_g_no_latch_across_calls():
    assert _check_g(build_manifest)
    assert not _check_g(_naive_adapter())


def test_falsifier_h_built_at_is_not_a_clock():
    assert _check_h(build_manifest)
    assert not _check_h(_naive_adapter())


# --------------------------------------------------------------------------- laws

def test_key_order_is_exact():
    manifest = build_manifest(
        _receipts(live_flow_meta=CASES["valid_v2_fresh"], eod=CASES["eod252_baselines"]),
        NOW,
    )
    assert list(manifest) == ["schema", "evaluated_at", "cohort", "session", "rows"]
    assert manifest["schema"] == SCHEMA
    assert manifest["evaluated_at"] == "2026-10-21T19:00:00+00:00"
    assert manifest["cohort"] == "live_flow.configured_root_universe@d533508a4e66"
    assert manifest["session"] == SESSION
    assert len(manifest["rows"]) == 2
    assert [row["capability_id"] for row in manifest["rows"]] == [TAPE, EOD]
    for row in manifest["rows"]:
        assert list(row) == [
            "capability_id",
            "census_observed_state",
            "source_family",
            "source_owner",
            "cohort",
            "session",
            "claim_class",
            "populations",
            "source_asof",
            "clock_provenance",
            "read_state",
            "entitlement",
            "accepted_use",
            "reasons",
        ]
        assert list(row["populations"]) == [
            "requested",
            "configured",
            "captured",
            "qualified",
            "displayed",
        ]


def test_enums_and_unbound_fields():
    manifest = build_manifest(
        _receipts(live_flow_meta=CASES["valid_v2_fresh"], eod=CASES["eod252_baselines"]),
        NOW,
    )
    for row in manifest["rows"]:
        assert row["read_state"] in READ_STATES
        assert row["claim_class"] in CLAIM_CLASSES
        assert row["census_observed_state"] == "ACCEPTED_SLICE"
        assert row["entitlement"] == "unbound"
        assert row["accepted_use"] == "unbound"
        assert row["populations"]["displayed"] is None
        assert row["session"] == SESSION
        assert row["cohort"] == manifest["cohort"]
    tape = _row_of(manifest, TAPE)
    assert tape["claim_class"] == "OBSERVED"
    assert tape["source_owner"] == "scripts/live_flow_poller.py"
    eod = _row_of(manifest, EOD)
    assert eod["claim_class"] == "DERIVED"
    assert eod["source_owner"] == "scripts/build_live_flow_baselines.py"


def test_valid_v2_data_row():
    row = _tape_row(build_manifest, live_flow_meta=CASES["valid_v2_fresh"])
    assert row["read_state"] == "data"
    assert row["source_asof"] == "2026-10-21T18:54:50+00:00"
    assert row["clock_provenance"] == "live_flow.meta/v2:asof"
    assert row["populations"] == {
        "requested": 40,
        "configured": 40,
        "captured": 37,
        "qualified": None,
        "displayed": None,
    }
    assert "configured_via_compat_alias:universe_n" in row["reasons"]
    assert "no_threshold_source" in row["reasons"]
    assert "qualified_not_receipted" in row["reasons"]
    assert "displayed_unbound_v0" in row["reasons"]


def test_missing_and_failed_rows_are_null():
    missing = _tape_row(build_manifest)
    assert missing["read_state"] == "missing"
    assert "receipt_absent" in missing["reasons"]
    failed = _tape_row(build_manifest, live_flow_meta=KeyError("read failed"))
    assert failed["read_state"] == "failed_read"
    assert "read_raised:KeyError" in failed["reasons"]
    unparseable = _tape_row(build_manifest, live_flow_meta=["not", "a", "mapping"])
    assert unparseable["read_state"] == "failed_read"
    assert "receipt_unparseable" in unparseable["reasons"]
    for row in (missing, failed, unparseable):
        assert row["source_asof"] is None
        assert row["clock_provenance"] is None
        assert all(v is None for v in row["populations"].values())


def test_v2_clock_field_failures():
    incomplete = dict(CASES["v2_zero_captured"])
    row = _tape_row(build_manifest, live_flow_meta=incomplete)
    assert row["read_state"] == "unknown"
    assert row["source_asof"] is None
    assert "clock_incomplete:source_response_at_first" in row["reasons"]
    bad_type = dict(CASES["valid_v2_fresh"])
    bad_type["cycle_started_at"] = 42
    row = _tape_row(build_manifest, live_flow_meta=bad_type)
    assert row["read_state"] == "unknown"
    assert "clock_unparseable:cycle_started_at" in row["reasons"]
    naive_stamp = dict(CASES["valid_v2_fresh"])
    naive_stamp["asof"] = "2026-10-21T18:54:50"
    row = _tape_row(build_manifest, live_flow_meta=naive_stamp)
    assert row["read_state"] == "unknown"
    assert "clock_unparseable:asof" in row["reasons"]
    absent_interval = dict(CASES["valid_v2_fresh"])
    del absent_interval["observed_start_to_start_sec"]
    row = _tape_row(build_manifest, live_flow_meta=absent_interval)
    assert row["read_state"] == "unknown"
    assert "clock_incomplete:observed_start_to_start_sec" in row["reasons"]


def test_zero_observed_interval_is_unknown():
    meta = dict(CASES["valid_v2_fresh"])
    meta["observed_start_to_start_sec"] = 0
    row = _tape_row(build_manifest, live_flow_meta=meta)
    assert row["read_state"] == "unknown"
    assert row["source_asof"] is None
    assert "clock_unparseable:observed_start_to_start_sec" in row["reasons"]


def test_population_order_violation_kept():
    meta = dict(CASES["valid_v2_fresh"])
    meta["roots_with_source_payload"] = 45
    row = _tape_row(build_manifest, live_flow_meta=meta)
    assert row["read_state"] == "unknown"
    assert row["populations"]["captured"] == 45
    assert row["populations"]["requested"] == 40
    assert "population_order_violated" in row["reasons"]


def test_malformed_counts_are_unknown():
    bool_count = dict(CASES["valid_v2_fresh"])
    bool_count["universe_n"] = True
    row = _tape_row(build_manifest, live_flow_meta=bool_count)
    assert row["read_state"] == "unknown"
    assert row["populations"]["configured"] is None
    assert "count_malformed:configured" in row["reasons"]
    float_count = dict(CASES["valid_v2_fresh"])
    float_count["roots_with_source_payload"] = 40.5
    row = _tape_row(build_manifest, live_flow_meta=float_count)
    assert row["read_state"] == "unknown"
    assert row["populations"]["captured"] is None
    assert "count_malformed:captured" in row["reasons"]
    negative = dict(CASES["valid_v2_fresh"])
    negative["roots_requested"] = -1
    row = _tape_row(build_manifest, live_flow_meta=negative)
    assert row["read_state"] == "unknown"
    assert "count_malformed:requested" in row["reasons"]


def test_eod252_log_only_row():
    manifest = build_manifest(_receipts(eod=CASES["eod252_baselines"]), NOW)
    row = _row_of(manifest, EOD)
    assert row["read_state"] == "unknown"
    assert row["source_asof"] is None
    assert row["clock_provenance"] is None
    assert all(v is None for v in row["populations"].values())
    for reason in ("population_counts_log_only", "no_accepted_clock", "no_threshold_source"):
        assert reason in row["reasons"]


def test_eod_accepted_clock_still_unknown():
    manifest = build_manifest(
        _receipts(eod={"source_asof": "2026-10-21T18:00:00+00:00"}), NOW
    )
    row = _row_of(manifest, EOD)
    assert row["read_state"] == "unknown"
    assert row["source_asof"] == "2026-10-21T18:00:00+00:00"
    assert row["clock_provenance"] == "eod252_baselines:source_asof"
    assert "no_threshold_source" in row["reasons"]
    assert "population_counts_log_only" in row["reasons"]


def test_eod_future_dated():
    manifest = build_manifest(
        _receipts(eod={"source_asof": "2026-10-21T19:30:00+00:00"}), NOW
    )
    row = _row_of(manifest, EOD)
    assert row["read_state"] == "unknown"
    assert row["source_asof"] is None
    assert "future_dated_clock" in row["reasons"]


def test_empty_receipts_missing_rows():
    manifest = build_manifest({}, NOW)
    assert manifest["session"] is None
    for row in manifest["rows"]:
        assert row["read_state"] == "missing"
        assert row["source_asof"] is None
        assert row["clock_provenance"] is None
        assert all(v is None for v in row["populations"].values())
        assert "receipt_absent" in row["reasons"]
        assert "session_not_supplied" in row["reasons"]


def test_no_threshold_bound_in_v0():
    for asof in (
        "2026-10-21T16:00:00+00:00",
        "2026-10-20T19:00:00+00:00",
        "2026-10-14T19:00:00+00:00",
    ):
        end = datetime.fromisoformat(asof)
        meta = {
            "schema": "live_flow.meta/v2",
            "asof": asof,
            "cycle_started_at": (end - timedelta(seconds=60)).isoformat(),
            "source_response_at_first": (end - timedelta(seconds=55)).isoformat(),
            "source_response_at_last": asof,
            "observed_start_to_start_sec": 60.0,
            "roots_requested": 40,
            "roots_with_source_payload": 37,
            "universe_n": 40,
        }
        row = _tape_row(build_manifest, live_flow_meta=meta)
        assert row["read_state"] == "data", asof
        assert row["source_asof"] == asof
        assert "no_threshold_source" in row["reasons"]
    for case in CASES.values():
        if not isinstance(case, Mapping) or "_transport" not in case:
            continue
        manifest = build_manifest(_receipts(live_flow_meta=case), NOW)
        for row in manifest["rows"]:
            assert row["read_state"] != "stale"


def test_module_purity_tokens_absent():
    source = Path(manifest_module.__file__).read_text(encoding="utf-8")
    for token in _PURITY_TOKENS:
        assert token not in source, token


def test_naive_now_raises():
    with pytest.raises(ValueError):
        build_manifest(
            _receipts(live_flow_meta=CASES["valid_v2_fresh"]),
            datetime(2026, 10, 21, 19, 0, 0),
        )


def test_non_mapping_receipts_raise():
    with pytest.raises(TypeError):
        build_manifest(["not", "a", "mapping"], NOW)


def test_deterministic_and_no_mutation():
    receipts = _receipts(
        live_flow_meta=CASES["valid_v2_fresh"], eod=CASES["eod252_baselines"]
    )
    frozen = copy.deepcopy(receipts)
    first = build_manifest(receipts, NOW)
    second = build_manifest(receipts, NOW)
    assert first == second
    assert receipts == frozen


# --------------------------------------------------------------------------- r2 hardening

_CHECKS = (_check_a, _check_b, _check_c, _check_d, _check_e, _check_f, _check_g, _check_h)
_V2_CLOCKS = ("cycle_started_at", "source_response_at_first", "source_response_at_last", "asof")
_AWARE = "2026-10-21T18:30:00+00:00"
_LOW = "0001-01-01T00:00:00+05:00"
_UNKNOWN = ("unknown", None, None)


def _clock(row):
    return row["read_state"], row["source_asof"], row["clock_provenance"]


def test_negative_controls_fail_every_falsifier():
    green = [check(build_manifest) for check in _CHECKS]
    naive = [check(_naive_adapter()) for check in _CHECKS]
    null = [check(_null_adapter()) for check in _CHECKS]
    print("CHECKS build_manifest", green, "naive", naive, "null", null)
    assert green == [True] * 8
    assert naive == [False] * 8
    assert null == [False] * 8


def test_producer_form_z_microseconds_is_data():
    case = CASES["v2_producer_form"]
    assert all(case[f].endswith("Z") for f in _V2_CLOCKS + ("built_at",))
    row = _tape_row(build_manifest, live_flow_meta=case)
    assert _clock(row) == ("data", "2026-10-21T18:54:50.123456+00:00", "live_flow.meta/v2:asof")
    assert "no_threshold_source" in row["reasons"]
    assert not [r for r in row["reasons"] if r.startswith("clock_")]


def test_z_suffix_parses_without_native_z_support(monkeypatch):
    class _NoZDatetime(datetime):
        @classmethod
        def fromisoformat(cls, value):
            if value.endswith("Z"):
                raise ValueError("fromisoformat without Z support")
            return datetime.fromisoformat(value)

    monkeypatch.setattr(manifest_module, "datetime", _NoZDatetime)
    stamp = manifest_module._parse_aware("2026-10-21T18:54:50.123456Z")
    assert stamp is not None
    assert (stamp.utcoffset(), stamp.microsecond) == (timedelta(0), 123456)
    assert manifest_module._parse_aware("2026-10-21T18:54:50.123456") is None
    assert manifest_module._parse_aware("Z") is None


def test_counts_absent_keeps_data_with_reasons():
    row = _tape_row(build_manifest, live_flow_meta=CASES["v2_counts_absent"])
    assert _clock(row) == ("data", "2026-10-21T18:54:50+00:00", "live_flow.meta/v2:asof")
    for field in ("requested", "configured", "captured"):
        assert row["populations"][field] is None
        assert "count_absent:" + field in row["reasons"]


@pytest.mark.parametrize(
    ("source_asof", "expected", "reason"),
    [
        (_AWARE, ("data", _AWARE, "live_flow_meta:source_asof"), "no_threshold_source"),
        ("2026-10-21T18:30:00", _UNKNOWN, "no_accepted_clock"),
        ("2026-10-21T19:30:00+00:00", _UNKNOWN, "future_dated_clock"),
    ],
)
def test_schemaless_source_asof(source_asof, expected, reason):
    row = _tape_row(build_manifest, live_flow_meta={"source_asof": source_asof})
    assert _clock(row) == expected
    assert reason in row["reasons"]


def test_unrecognized_schema_binds_no_clock():
    for schema, reason in (
        ("live_flow.feed/v1", "unrecognized_schema:live_flow.feed/v1"),
        ("live_flow.heat/v1", "unrecognized_schema:live_flow.heat/v1"),
        (None, "unrecognized_schema:None"),
        ("x" * 100, "unrecognized_schema:" + "x" * 64),
    ):
        row = _tape_row(build_manifest, live_flow_meta={"schema": schema, "source_asof": _AWARE})
        assert _clock(row) == _UNKNOWN, schema
        assert reason in row["reasons"]
    v1 = _tape_row(build_manifest, live_flow_meta=CASES["v1_meta_http200"])
    assert "unrecognized_schema:live_flow.meta/v1" in v1["reasons"]
    huge = _tape_row(build_manifest, live_flow_meta={"schema": 10**5000, "source_asof": _AWARE})
    labels = [r for r in huge["reasons"] if r.startswith("unrecognized_schema:")]
    assert _clock(huge) == _UNKNOWN
    assert len(labels) == 1 and len(labels[0]) <= len("unrecognized_schema:") + 64


def test_unrepresentable_utc_clock_is_unknown_not_raised():
    meta = dict.fromkeys(_V2_CLOCKS, _LOW)
    meta.update(schema="live_flow.meta/v2", observed_start_to_start_sec=60.0)
    eod_ok = {"source_asof": "2026-10-21T18:00:00+00:00"}
    manifest = build_manifest(_receipts(live_flow_meta=meta, eod=eod_ok), NOW)
    tape = _row_of(manifest, TAPE)
    assert _clock(tape) == _UNKNOWN
    assert "clock_unparseable:OverflowError" in tape["reasons"]
    assert "no_threshold_source" not in tape["reasons"]
    eod = _row_of(manifest, EOD)
    assert _clock(eod) == ("unknown", "2026-10-21T18:00:00+00:00", "eod252_baselines:source_asof")
    low = _row_of(build_manifest(_receipts(eod={"source_asof": _LOW}), NOW), EOD)
    assert _clock(low) == _UNKNOWN
    assert "clock_unparseable:OverflowError" in low["reasons"]


def test_huge_interval_is_unknown_not_raised():
    for bad in (10**400, float("inf"), float("nan")):
        meta = dict(CASES["valid_v2_fresh"])
        meta["observed_start_to_start_sec"] = bad
        row = _tape_row(build_manifest, live_flow_meta=meta)
        assert _clock(row) == _UNKNOWN
        assert "clock_unparseable:observed_start_to_start_sec" in row["reasons"]


def test_session_requires_calendar_date_form():
    assert build_manifest(_receipts(session="2026-10-21"), NOW)["session"] == "2026-10-21"
    for label in ("2026-W43-3", "20261021", 20261021):
        manifest = build_manifest(_receipts(session=label), NOW)
        assert manifest["session"] is None, label
        for row in manifest["rows"]:
            assert row["session"] is None
            assert "session_not_supplied" in row["reasons"]
