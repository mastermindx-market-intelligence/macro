"""Offline callback barriers exercise admission, settlement and resource stops."""
from bisect import bisect_left
from threading import Barrier, Event, Lock

import pytest

from lib.dataos.tiingo_capture_admission import (
    MAX_RESPONSE_BYTES, _AdmissionGate, run_finite_capture,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.lock = Lock()

    def __call__(self):
        with self.lock:
            return self.now

    def wait(self, condition, delay):
        with self.lock:
            self.now += delay
        condition.wait(0.0001)


@pytest.fixture(autouse=True)
def forbid_provider_and_credentials(monkeypatch):
    import socket
    import urllib.request
    import collectors.tiingo_archive as archive

    def forbidden(*args, **kwargs):
        pytest.fail("offline admission test touched credentials or network")

    monkeypatch.setattr(archive, "read_key", forbidden)
    monkeypatch.setattr(archive, "collect_one", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)


def run(tasks, capture, space=lambda: None, budget=24 * 1024**3):
    clock = FakeClock()
    return run_finite_capture(tasks, capture, space, raw_budget_bytes=budget,
                              clock=clock, wait_on=clock.wait)


@pytest.mark.parametrize("next_time", [9.999999, 10.0, 10.000001])
def test_actual_admission_at_rolling_boundary_and_prior_wave_delay(next_time):
    clock = FakeClock()
    gate = _AdmissionGate(100, clock, clock.wait)
    assert [gate.admit(i, lambda: None) for i in range(4)] == [5.0] * 4
    clock.now = next_time
    stamp = gate.admit(4, lambda: None)
    assert stamp == max(10.0, next_time)
    assert stamp - gate.admissions[0][1] >= 5.0


def test_every_five_second_and_hour_window_and_unchanged_finite_selection():
    tasks = [{"symbol": f"SYMBOL{i}", "params": {"startDate": "1990-01-01",
              "endDate": "2026-10-09"}, "request_path": f"/unchanged/{i}"}
             for i in range(5000)]
    called = []
    lock = Lock()

    def capture(task):
        with lock:
            called.append(task)
        return {"raw_bytes": 10}

    result = run(tasks, capture)
    stamps = [stamp for _, stamp in result.admissions]
    assert len(stamps) == 5000 and result.complete
    assert all(stamps[i] - stamps[i - 4] >= 5 for i in range(4, len(stamps)))
    assert all(bisect_left(stamps, stamp + 5) - i <= 4 for i, stamp in enumerate(stamps))
    assert all(bisect_left(stamps, stamp + 3600) - i <= 2880
               for i, stamp in enumerate(stamps))
    assert {id(task) for task in called} == {id(task) for task in tasks}
    assert len(called) == len(set(id(task) for task in called)) == 5000
    assert [o.index for o in result.outcomes] == list(range(5000))
    assert all(o.value == {"raw_bytes": 10} for o in result.outcomes)
    assert result.raw_bytes == 50000


def test_uneven_completion_refills_without_waiting_for_slowest_request():
    slow = Event()
    refilled = Event()
    lock = Lock()
    active = high_water = 0

    def capture(index):
        nonlocal active, high_water
        with lock:
            active += 1
            high_water = max(high_water, active)
        try:
            if index == 0:
                assert slow.wait(3)
            if index == 4:
                refilled.set()
                slow.set()
            return {"raw_bytes": 1}
        finally:
            with lock:
                active -= 1

    result = run(list(range(12)), capture)
    assert refilled.is_set() and result.complete and high_water <= 4


@pytest.mark.parametrize("error_class", [RuntimeError, KeyboardInterrupt])
def test_simultaneous_success_and_error_prevent_post_latch_admission(error_class, monkeypatch):
    together = Barrier(4)
    calls = []
    lock = Lock()
    admitted_at_failure = []
    original_close = _AdmissionGate.close

    def observed_close(gate, reason):
        original_close(gate, reason)
        if reason == "capture_error":
            admitted_at_failure.append(len(gate.admissions))

    monkeypatch.setattr(_AdmissionGate, "close", observed_close)

    def capture(index):
        with lock:
            calls.append(index)
        if index < 4:
            together.wait(3)
        if index == 1:
            raise error_class("synthetic callback failure")
        return {"raw_bytes": 1}

    result = run(list(range(20)), capture)
    assert len(result.admissions) == admitted_at_failure[0]
    assert len(calls) == len(result.admissions) == len(set(calls))
    assert sum(o.admitted_at is not None for o in result.outcomes) == len(calls)
    assert sum(o.error is not None for o in result.outcomes) == 1
    assert not result.complete and result.stop_reason == "capture_error"


def test_delayed_worker_entry_cannot_burst_or_admit_after_failure():
    clock = FakeClock()
    gate = _AdmissionGate(100, clock, clock.wait)
    # Old queued submission times are irrelevant: only these actual entries count.
    clock.now = 100
    assert [gate.admit(i, lambda: None) for i in range(4)] == [100] * 4
    gate.close("capture_error")
    clock.now = 1000
    assert gate.admit(4, lambda: pytest.fail("closed gate checked resources")) is None
    assert len(gate.admissions) == 4


def test_failure_during_resource_check_prevents_admission():
    clock = FakeClock()
    gate = _AdmissionGate(100, clock, clock.wait)

    def space_check():
        gate.close("capture_error")

    assert gate.admit(0, space_check) is None
    assert not gate.admissions


def test_failure_during_pacing_wait_prevents_admission():
    clock = FakeClock()

    def wait_and_fail(condition, delay):
        gate.close("capture_error")

    gate = _AdmissionGate(100, clock, wait_and_fail)
    assert gate.admit(0, lambda: pytest.fail("closed gate checked resources")) is None
    assert not gate.admissions


def test_resource_floor_rechecked_and_already_admitted_requests_settle():
    together = Barrier(4)
    calls = []
    space_calls = 0
    lock = Lock()

    def space_check():
        nonlocal space_calls
        with lock:
            space_calls += 1
            if space_calls > 4:
                raise OSError("40 GiB floor reached")

    def capture(index):
        calls.append(index)
        together.wait(3)
        return {"raw_bytes": 1}

    result = run(list(range(30)), capture, space_check)
    assert sorted(calls) == list(range(4))
    assert result.raw_bytes == 4 and not result.complete
    assert result.stop_reason == "resource_check_error"
    assert all(o.error is None for o in result.outcomes if o.admitted_at is not None)


def test_raw_threshold_with_outstanding_responses_has_bounded_overshoot():
    together = Barrier(4)

    def capture(index):
        together.wait(3)
        return {"raw_bytes": MAX_RESPONSE_BYTES}

    result = run(list(range(20)), capture, budget=1)
    assert result.raw_bytes == 4 * MAX_RESPONSE_BYTES
    assert len(result.admissions) == 4 and not result.complete
    assert result.stop_reason == "raw_budget_reached"
    assert result.raw_bytes <= 1 + 4 * MAX_RESPONSE_BYTES


@pytest.mark.parametrize("bad_count", [True, -1, MAX_RESPONSE_BYTES + 1, None])
def test_invalid_callback_byte_contract_stops_and_never_claims_complete(bad_count):
    result = run([0], lambda _: {"raw_bytes": bad_count})
    assert result.stop_reason == "result_contract_error"
    assert len(result.admissions) == 1 and result.outcomes[0].error is not None
    assert not result.complete


def test_exhausted_exact_scope_accounts_each_actual_admission_once():
    result = run(list(range(7)), lambda _: {"raw_bytes": 1})
    assert result.complete and len(result.admissions) == len(result.outcomes) == 7
    assert len({i for i, _ in result.admissions}) == 7
    assert len({o.index for o in result.outcomes}) == 7


def test_executor_interruption_still_consumes_all_started_results(monkeypatch):
    import lib.dataos.tiingo_capture_admission as module
    together = Barrier(4)

    def interrupted(*args, **kwargs):
        together.wait(3)
        raise RuntimeError("synthetic wait interruption")

    def capture(index):
        if index != 3:
            together.wait(3)
        return {"raw_bytes": 1}

    monkeypatch.setattr(module, "wait", interrupted)
    result = run(list(range(30)), capture)
    assert len(result.outcomes) == 4
    assert result.orchestration_error is not None and not result.complete
    assert len(result.admissions) == 4


@pytest.mark.parametrize("size,budget", [(0, 1), (5001, 1), (1, 0), (1, True)])
def test_invalid_scope_refused_before_capture(size, budget):
    with pytest.raises(ValueError):
        run([0] * size, lambda _: pytest.fail("invalid scope started"), budget=budget)
