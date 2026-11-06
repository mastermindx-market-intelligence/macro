"""Finite callback orchestration; no provider, credential, archive or retry code.

Admission is recorded immediately before the supplied capture callback. These
local monotonic timestamps bound wrapper admissions, not vendor arrival times.
The caller still owns source, quota, prior-settlement and disjoint-scope checks.
"""
from __future__ import annotations

from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from threading import Condition
from time import monotonic
from typing import Any, Callable, Sequence

MAX_INFLIGHT = 4
ROLLING_SECONDS = 5.0
MAX_RESPONSE_BYTES = 512 * 1024**2  # unchanged original collector bound


@dataclass(frozen=True)
class CaptureOutcome:
    index: int
    admitted_at: float | None
    value: Any = None
    error: BaseException | None = None


@dataclass(frozen=True)
class FiniteCaptureResult:
    selected_count: int
    outcomes: tuple[CaptureOutcome, ...]
    admissions: tuple[tuple[int, float], ...]
    raw_bytes: int
    stop_reason: str | None
    orchestration_error: BaseException | None

    @property
    def complete(self) -> bool:
        return (
            len(self.admissions) == len(self.outcomes) == self.selected_count
            and all(o.admitted_at is not None and o.error is None for o in self.outcomes)
            and self.orchestration_error is None
        )


class _AdmissionGate:
    def __init__(self, budget: int, clock: Callable[[], float], wait_on: Callable):
        self.condition = Condition()
        self.clock = clock
        self.wait_on = wait_on
        self.not_before = clock() + ROLLING_SECONDS
        self.recent: deque[float] = deque(maxlen=MAX_INFLIGHT)
        self.admissions: list[tuple[int, float]] = []
        self.raw_bytes = 0
        self.budget = budget
        self.stop_reason: str | None = None

    def close(self, reason: str) -> None:
        with self.condition:
            if self.stop_reason is None:
                self.stop_reason = reason
            self.condition.notify_all()

    def _delay(self, now: float) -> float:
        earliest = self.not_before
        if len(self.recent) == MAX_INFLIGHT:
            earliest = max(earliest, self.recent[0] + ROLLING_SECONDS)
        return max(0.0, earliest - now)

    def admit(self, index: int, check_space: Callable[[], None]) -> float | None:
        while True:
            with self.condition:
                if self.stop_reason is not None:
                    return None
                delay = self._delay(self.clock())
                if delay:
                    self.wait_on(self.condition, delay)
                    continue
            # A slow disk check must not prevent another worker closing admission.
            check_space()
            with self.condition:
                if self.stop_reason is not None:
                    return None
                now = self.clock()
                if self._delay(now):
                    continue  # another worker used this slot; recheck after waiting
                self.recent.append(now)
                self.admissions.append((index, now))
                return now

    def settle_bytes(self, count: int) -> None:
        with self.condition:
            self.raw_bytes += count
            if self.raw_bytes >= self.budget and self.stop_reason is None:
                self.stop_reason = "raw_budget_reached"
                self.condition.notify_all()


def run_finite_capture(
    tasks: Sequence[Any],
    capture: Callable[[Any], Any],
    check_space: Callable[[], None],
    *,
    raw_budget_bytes: int,
    clock: Callable[[], float] = monotonic,
    wait_on: Callable = lambda condition, delay: condition.wait(delay),
) -> FiniteCaptureResult:
    """Settle a finite selection once, with at most four unsettled futures.

    The raw budget is a stop threshold, as in the incumbent finite orchestrator.
    Up to four already admitted responses can settle beyond that threshold;
    each is bounded by the original collector's 512 MiB response cap. The caller
    must retain its 40 GiB free-space floor and 5 GiB in-flight headroom.
    A capture error closes the shared latch before any caller diagnostics run.
    No task is retried, cancelled or replaced. Unexpected errors remain in the
    result for same-operation reconciliation; they never imply a full capture.
    """
    if not 1 <= len(tasks) <= 5000:
        raise ValueError("finite selection must contain 1..5000 tasks")
    if type(raw_budget_bytes) is not int or raw_budget_bytes <= 0:
        raise ValueError("raw stop threshold must be a positive integer")
    selected = tuple(tasks)
    gate = _AdmissionGate(raw_budget_bytes, clock, wait_on)
    outcomes: dict[int, CaptureOutcome] = {}
    pending: dict[Any, int] = {}
    next_index = 0
    orchestration_error: BaseException | None = None

    def invoke(index: int) -> CaptureOutcome:
        try:
            admitted = gate.admit(index, check_space)
        except BaseException as error:
            gate.close("resource_check_error")
            return CaptureOutcome(index, None, error=error)
        if admitted is None:
            return CaptureOutcome(index, None)
        try:
            value = capture(selected[index])
        except BaseException as error:
            gate.close("capture_error")  # before diagnostics or result formatting
            return CaptureOutcome(index, admitted, error=error)
        try:
            count = value["raw_bytes"]
            if type(count) is not int or not 0 <= count <= MAX_RESPONSE_BYTES:
                raise ValueError("capture response byte count violates collector bound")
            gate.settle_bytes(count)
        except BaseException as error:
            gate.close("result_contract_error")
            return CaptureOutcome(index, admitted, value, error)
        return CaptureOutcome(index, admitted, value)

    def consume(future: Any, index: int) -> None:
        nonlocal orchestration_error
        try:
            outcomes[index] = future.result()
        except BaseException as error:
            gate.close("executor_error")
            orchestration_error = orchestration_error or error
            admitted = next((stamp for i, stamp in gate.admissions if i == index), None)
            outcomes[index] = CaptureOutcome(index, admitted, error=error)

    # No excess executor queue: pending includes every submitted but unconsumed task.
    with ThreadPoolExecutor(max_workers=MAX_INFLIGHT) as pool:
        try:
            while next_index < len(selected) or pending:
                # Drain every completed result before any replacement submission.
                for future in tuple(pending):
                    if future.done():
                        consume(future, pending.pop(future))
                while (gate.stop_reason is None and next_index < len(selected)
                       and len(pending) < MAX_INFLIGHT):
                    pending[pool.submit(invoke, next_index)] = next_index
                    next_index += 1
                if not pending:
                    break
                wait(tuple(pending), return_when=FIRST_COMPLETED)
        except BaseException as error:
            gate.close("executor_error")
            orchestration_error = error
        finally:
            # Even an orchestration interruption settles all previously submitted work.
            for future, index in pending.items():
                consume(future, index)
    return FiniteCaptureResult(
        len(selected), tuple(outcomes[i] for i in sorted(outcomes)),
        tuple(gate.admissions), gate.raw_bytes, gate.stop_reason, orchestration_error,
    )
