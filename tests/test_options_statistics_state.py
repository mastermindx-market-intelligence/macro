"""Synthetic state-boundary checks, not producer or market acceptance."""

from copy import deepcopy
from decimal import Decimal, localcontext
import json

import pytest

from engine.options_statistics_state import advance_statistics, statistics_snapshot


SESSION = "2026-10-23"
CLOCK = "2026-10-23T14:00:00Z"


def row(**kwargs):
    return {"root": "SPY", "expiration": "2026-10-30", "strike": 745,
            "right": "P", "sequence": 1, "size": 2, "price": 1.01,
            "trade_timestamp": "2026-10-23T13:59:00Z", "exchange": 4,
            "bid": 1, "ask": 1.02, "quote_timestamp": "2026-10-23T13:58:59Z",
            **kwargs}


def advance(prior, rows, **kwargs):
    return advance_statistics(prior, rows, session_date=kwargs.pop("session_date", SESSION),
                              root=kwargs.pop("root", "SPY"),
                              observed_at=kwargs.pop("observed_at", CLOCK), **kwargs)


def test_multi_cycle_roots_partitions_and_input_immutability():
    rows = [row(), row(sequence=2, right="C", bid=None)]
    original = deepcopy(rows)
    first = advance(None, rows)
    retained = deepcopy(first)
    second = advance(first, [row(root="QQQ", sequence=3, size=9)], root="QQQ",
                     observed_at="2026-10-23T14:01:00Z")
    third = advance(second, [row(sequence=4, size=5)], observed_at="2026-10-23T14:02:00Z")
    assert rows == original and first == retained
    snapshot = statistics_snapshot(third)
    spy, qqq = snapshot["roots"]["SPY"], snapshot["roots"]["QQQ"]
    assert spy["totals"]["print_count"] == 3
    assert spy["totals"]["contract_volume"] == 9
    assert qqq["totals"]["contract_volume"] == 9
    assert spy["locations"]["UNKNOWN"]["print_count"] == 1
    assert spy["nbbo_print_coverage"] == 2 / 3
    assert spy["totals"]["qualified_premium_usd"] is None
    for root in snapshot["roots"].values():
        for dimension in ("rights", "locations", "venues"):
            for count in ("print_count", "contract_volume", "premium_qualified_print_count"):
                assert sum(bucket[count] for bucket in root[dimension].values()) == root["totals"][count]


def test_duplicate_identity_is_not_arbitrary_first_wins():
    one = row()
    state = advance(None, [one, dict(one), row(sequence=2), row(sequence=2, size=3), row(sequence=3)])
    root = state["roots"]["SPY"]
    assert root["totals"]["print_count"] == 2
    assert root["input_row_count"] == 5
    assert root["duplicate_row_count"] == 1
    assert root["conflicting_identity_count"] == 1
    assert root["ambiguous_row_count"] == 2
    reverse = advance(None, list(reversed([one, dict(one), row(sequence=2), row(sequence=2, size=3), row(sequence=3)])))
    assert state == reverse


def test_quote_or_terms_conflicts_remain_explicit_ambiguity():
    state = advance(None, [row(), row(bid=None)])
    root = statistics_snapshot(state)["roots"]["SPY"]
    assert root["totals"]["print_count"] == 0
    assert root["ambiguous_row_count"] == 2
    assert root["status"] == "NO_UNAMBIGUOUS_VALID_ROWS"


def test_empty_observation_is_distinct_from_absence_and_no_valid_rows():
    assert statistics_snapshot(None)["status"] == "UNAVAILABLE"
    empty = statistics_snapshot(advance(None, []))
    assert empty["roots"]["SPY"]["status"] == "OBSERVED_EMPTY"
    assert "QQQ" not in empty["roots"]
    invalid = statistics_snapshot(advance(None, [row(size=True), row(sequence=None), None]))
    assert invalid["roots"]["SPY"]["status"] == "NO_UNAMBIGUOUS_VALID_ROWS"
    assert invalid["roots"]["SPY"]["rejected_row_count"] == 3


def test_clocks_are_prospective_not_backdated_to_source():
    state = advance(None, [row()])
    root = state["roots"]["SPY"]
    assert state["first_observed_at"] == "2026-10-23T14:00:00+00:00"
    assert root["first_trade_at"] == "2026-10-23T13:59:00+00:00"
    next_state = advance(state, [], observed_at="2026-10-23T14:05:00Z")
    assert next_state["first_observed_at"] == state["first_observed_at"]
    assert next_state["roots"]["SPY"]["first_trade_at"] == root["first_trade_at"]
    assert next_state["roots"]["SPY"]["last_observed_at"] == "2026-10-23T14:05:00+00:00"


def test_qualified_premium_decimal_cumulative_and_caller_context_isolation():
    params = {"premium_basis": "qualified_contract_terms", "premium_multiplier": 100}
    with localcontext() as ctx:
        ctx.prec = 1
        ctx.Emax = 1
        ctx.Emin = -1
        ctx.clamp = 1
        for signal in ctx.traps:
            ctx.traps[signal] = True
        before = ctx.copy()
        state = advance(None, [row(price=1e100, **params)])
        state = advance(state, [row(sequence=2, price=0.1, **params)], observed_at="2026-10-23T14:01:00Z")
        snapshot = statistics_snapshot(state)
        assert ctx.prec == before.prec and ctx.Emax == before.Emax
        assert ctx.flags == before.flags and ctx.traps == before.traps
    expected = "2" + "0" * 100 + "20"
    assert Decimal(state["roots"]["SPY"]["totals"]["premium_decimal"]) == Decimal(expected)
    assert snapshot["roots"]["SPY"]["totals"]["premium_qualified_print_count"] == 2
    json.dumps(state, allow_nan=False)
    json.dumps(snapshot, allow_nan=False)


def test_serialization_roundtrip_and_snapshot_do_not_mutate_state():
    state = advance(None, [row(premium_basis="qualified_contract_terms", premium_multiplier=100)])
    raw = json.dumps(state, allow_nan=False, sort_keys=True)
    snapshot = statistics_snapshot(json.loads(raw))
    assert snapshot == statistics_snapshot(state)
    assert json.dumps(state, allow_nan=False, sort_keys=True) == raw
    assert snapshot["roots"]["SPY"]["totals"]["qualified_premium_usd"] == 202


@pytest.mark.parametrize("kwargs", [
    {"session_date": "2026-10-26"}, {"observed_at": "2026-10-23T13:00:00Z"},
    {"observed_at": "2026-10-23T14:00:00"},
])
def test_bad_continuation_refuses_without_mutation(kwargs):
    state = advance(None, [row()])
    before = deepcopy(state)
    with pytest.raises(ValueError):
        advance(state, [row(sequence=2)], **kwargs)
    assert state == before


@pytest.mark.parametrize("mutate", [
    lambda s: s["roots"]["SPY"]["totals"].update(print_count=-1),
    lambda s: s["roots"]["SPY"]["rights"].pop("C"),
    lambda s: s["roots"]["SPY"]["totals"].update(premium_decimal="NaN"),
    lambda s: s["roots"]["SPY"].update(input_row_count=0),
    lambda s: s.update(schema="unknown"),
])
def test_corruption_never_resets_the_population(mutate):
    state = advance(None, [row()])
    mutate(state)
    before = deepcopy(state)
    with pytest.raises(ValueError):
        advance(state, [])
    assert state == before


def test_invalid_row_and_future_print_do_not_abort_or_invent_counts():
    state = advance(None, [row(size=2**64), row(price=float("inf")),
                           row(trade_timestamp="2026-10-23T14:01:00Z"), row(root="QQQ"),
                           row(sequence=5, exchange=None, bid=2, ask=1)])
    root = statistics_snapshot(state)["roots"]["SPY"]
    assert root["rejected_row_count"] == 4
    assert root["totals"]["print_count"] == 1
    assert root["locations"]["UNKNOWN"]["print_count"] == 1
    assert root["venues"]["UNKNOWN"]["print_count"] == 1


def test_parallel_root_completion_order_is_not_processing_order():
    later = advance(None, [row()], observed_at="2026-10-23T14:05:00Z")
    earlier = advance(later, [row(root="QQQ")], root="QQQ", observed_at="2026-10-23T14:01:00Z")
    assert earlier["first_observed_at"] == "2026-10-23T14:01:00+00:00"
    assert earlier["last_observed_at"] == "2026-10-23T14:05:00+00:00"
    assert earlier["roots"]["SPY"]["first_observed_at"] == "2026-10-23T14:05:00+00:00"
    assert statistics_snapshot(earlier)["roots"]["QQQ"]["totals"]["print_count"] == 1


def _engine(prior=None, rows=None):
    import pandas as pd
    from engine import live_flow
    return live_flow.process_batch(
        pd.DataFrame(rows if rows is not None else [row(bid=None, ask=None)]),
        pd.DataFrame(), SESSION, CLOCK, prior_state=prior,
        names_sectors={}, statistics_root="SPY",
    )["state"]


def test_actual_engine_counts_before_sign_and_repull_counts_once():
    original = [row(bid=None, ask=None), row(bid=None, ask=None)]
    state = _engine(rows=original)
    assert state["options_statistics"]["roots"]["SPY"]["totals"]["print_count"] == 1
    assert state["options_statistics"]["roots"]["SPY"]["duplicate_row_count"] == 1
    before = deepcopy(state)
    second = _engine(prior=state, rows=original)
    assert second["options_statistics"]["roots"]["SPY"]["totals"] == state["options_statistics"]["roots"]["SPY"]["totals"]
    assert second["options_statistics"]["roots"]["SPY"]["source_non_novel_row_count"] == 2
    assert state == before
    assert list(state["seen_sequences"].values()) == [1]


def test_old_day_state_starts_prospective_stats_without_resetting_highwater():
    prior = {"seen_sequences": {("SPY", "2026-10-30", 745.0, "P"): 10}}
    state = _engine(prior=prior, rows=[row(sequence=9), row(sequence=11, bid=None)])
    assert list(state["seen_sequences"].values()) == [11]
    assert state["options_statistics"]["roots"]["SPY"]["totals"]["print_count"] == 1
    assert list(prior["seen_sequences"].values()) == [10]


@pytest.mark.parametrize("fault", ["before_replace", "after_replace"])
def test_original_atomic_save_keeps_stats_and_highwater_together(tmp_path, monkeypatch, fault):
    import scripts.live_flow_poller as poller
    monkeypatch.setattr(poller, "_state_dir", lambda: tmp_path)
    old = _engine()
    poller._save_day_state(SESSION, old)
    new = _engine(prior=old, rows=[row(sequence=2, bid=None)])
    with monkeypatch.context() as patcher:
        def fail(*args, **kwargs):
            raise OSError("injected commit boundary")
        if fault == "before_replace":
            patcher.setattr(poller.os, "replace", fail)
        else:
            patcher.setattr(poller, "_fsync_directory", fail)
        with pytest.raises(OSError, match="injected commit boundary"):
            poller._save_day_state(SESSION, new)
    recovered = poller._load_day_state(SESSION)
    expected = 1 if fault == "before_replace" else 2
    assert recovered["options_statistics"]["roots"]["SPY"]["totals"]["print_count"] == expected
    assert list(recovered["seen_sequences"].values()) == [expected]
    replayed = _engine(prior=recovered, rows=[row(sequence=2, bid=None)])
    assert replayed["options_statistics"]["roots"]["SPY"]["totals"]["print_count"] == 2


def _poller_fixture(monkeypatch):
    import pandas as pd
    from engine import live_flow
    import scripts.live_flow_poller as poller
    monkeypatch.setattr(poller, "_fetch_root", lambda root, *args: (
        root, pd.DataFrame([row(root=root, bid=None, ask=None)]), pd.DataFrame()))
    monkeypatch.setattr(poller, "_utc_now_iso", lambda: CLOCK)
    monkeypatch.setattr(poller, "_load_prev_close", lambda *args: None)
    monkeypatch.setattr(poller, "_load_oi_prev", lambda *args: None)
    monkeypatch.setattr(live_flow, "_load_names_sectors", lambda: {})
    return poller, live_flow


def _cycle(poller, state=None, watermarks=None, enabled=True):
    return poller.run_cycle(roots=["SPY", "QQQ"], session_date=SESSION,
        delta_mode="time_window", day_state=state or {}, baselines={},
        cfg={"max_concurrent": 2, "cadence_sec": 120, "etf_floor": 0,
             "name_floor": 0, "etf_anchors": ["SPY", "QQQ"],
             "observed_statistics_enabled": enabled},
        cycle_watermarks=watermarks if watermarks is not None else {})


def test_partial_root_failure_and_existing_poller_publication_contract(monkeypatch):
    poller, live_flow = _poller_fixture(monkeypatch)
    original = live_flow.process_batch
    def fail_spy(**kwargs):
        result = original(**kwargs)
        if kwargs["statistics_root"] == "SPY":
            raise RuntimeError("after isolated calculation")
        return result
    monkeypatch.setattr(live_flow, "process_batch", fail_spy)
    watermarks = {}
    _, _, meta, state, _ = _cycle(poller, watermarks=watermarks)
    assert set(state["options_statistics"]["roots"]) == {"QQQ"}
    assert "SPY" not in watermarks
    assert meta["observed_statistics"]["roots"]["QQQ"]["totals"]["print_count"] == 1
    monkeypatch.setattr(live_flow, "process_batch", original)
    _, _, _, following, _ = _cycle(poller, state, watermarks)
    assert following["options_statistics"]["roots"]["SPY"]["totals"]["print_count"] == 1
    assert following["options_statistics"]["roots"]["QQQ"]["totals"]["print_count"] == 1


def test_missing_engine_statistics_refuses_before_highwater_commit(monkeypatch):
    poller, live_flow = _poller_fixture(monkeypatch)
    monkeypatch.setattr(live_flow, "process_batch", lambda **kwargs: {
        "state": {"seen_sequences": {("SPY", "2026-10-30", 745., "P"): 999}}})
    watermarks = {}
    with pytest.raises(RuntimeError, match="statistics missing"):
        _cycle(poller, watermarks=watermarks)
    assert watermarks == {}


def test_default_disabled_has_no_statistics_publication_or_state(monkeypatch):
    poller, _ = _poller_fixture(monkeypatch)
    _, _, meta, state, _ = _cycle(poller, enabled=False)
    assert "options_statistics" not in state
    assert "observed_statistics" not in meta


def test_pending_wal_drain_preserves_statistics_and_does_not_recount(tmp_path, monkeypatch):
    import scripts.live_flow_poller as poller
    monkeypatch.setattr(poller, "_state_dir", lambda: tmp_path)
    state = _engine()
    state["pending_learning_events"] = [{"id": "statistics-wal-test", "ts": "2026-10-23T13:59:00Z",
        "observed_at": CLOCK, "decision_at": "2026-10-23T14:00:01Z"}]
    expected = deepcopy(state["options_statistics"])
    poller._save_day_state(SESSION, state)
    calls = []
    def stage(session, events):
        calls.append(events)
        return [{**event, "available_at": "2026-10-23T14:00:02Z", "published_at": None,
                 "source_snapshot_asof": "2026-10-23T14:00:02Z",
                 "anchor_strategy": "durable_available_at"} for event in events]
    recovered = poller._load_day_state(SESSION)
    cleared, _ = poller._drain_pending_learning_events(SESSION, recovered, event_stager=stage)
    assert cleared["options_statistics"] == expected
    second = poller._load_day_state(SESSION)
    again, _ = poller._drain_pending_learning_events(SESSION, second, event_stager=stage)
    assert len(calls) == 1
    assert again["options_statistics"] == expected


@pytest.mark.parametrize("rows,status,received,rejected,prints", [
    ([], "OBSERVED_EMPTY", 0, 0, 0),
    ([row(size=True)], "NO_VALID_SOURCE_ROWS", 1, 1, 0),
    ([row(sequence=None)], "NO_VALID_SOURCE_ROWS", 1, 1, 0),
    ([row(bid=None)], "OBSERVED", 1, 0, 1),
    ([row(size=True), row(sequence=2, bid=None)], "OBSERVED", 2, 1, 1),
])
def test_actual_engine_preserves_prefilter_quality_across_restart(
        tmp_path, monkeypatch, rows, status, received, rejected, prints):
    import scripts.live_flow_poller as poller
    monkeypatch.setattr(poller, "_state_dir", lambda: tmp_path)
    state = _engine(rows=rows)
    poller._save_day_state(SESSION, state)
    recovered = poller._load_day_state(SESSION)
    projected = statistics_snapshot(recovered["options_statistics"])["roots"]["SPY"]
    assert projected["status"] == status
    assert projected["source_input_row_count"] == received
    assert projected["source_rejected_row_count"] == rejected
    assert projected["totals"]["print_count"] == prints


def test_actual_cycle_projects_invalid_only_and_mixed_source_quality(monkeypatch):
    import pandas as pd
    poller, _ = _poller_fixture(monkeypatch)
    monkeypatch.setattr(poller, "_fetch_root", lambda root, *args: (
        root, pd.DataFrame([row(root=root, size=True)] +
             ([row(root=root, sequence=2, bid=None)] if root == "QQQ" else [])), pd.DataFrame()))
    _, _, meta, state, _ = _cycle(poller)
    spy = meta["observed_statistics"]["roots"]["SPY"]
    qqq = meta["observed_statistics"]["roots"]["QQQ"]
    assert spy["status"] == "NO_VALID_SOURCE_ROWS"
    assert spy["source_input_row_count"] == spy["source_rejected_row_count"] == 1
    assert spy["totals"]["print_count"] == 0
    assert qqq["source_input_row_count"] == 2 and qqq["source_rejected_row_count"] == 1
    assert qqq["totals"]["print_count"] == 1
    assert state["options_statistics"]["roots"]["SPY"]["source_rejected_row_count"] == 1
