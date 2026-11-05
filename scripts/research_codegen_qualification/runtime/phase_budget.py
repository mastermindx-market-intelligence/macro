"""Pure phase-budget accounting for the Research Factory qualification.

Policy accounting only.  This module performs no subprocess, filesystem,
socket, environment, network or external clock access: time is supplied by
a caller-injected monotonic callable.  It does not observe hosts, receipts
or real phase success; it accounts only the fixed qualification budget.
"""

import math
from collections import namedtuple

PHASE_ORDER = ("cli", "archive", "install", "image", "smoke")
PHASE_SECONDS = {"cli": 60, "archive": 240, "install": 180, "image": 240, "smoke": 130}
PHASE_RAW_BYTES = {"cli": 16384, "archive": 0, "install": 16384, "image": 16384, "smoke": 16384}
TOTAL_SECONDS = 900
TOTAL_BYTES = 65536
METADATA_RESERVE_BYTES = 2048
RAW_AGGREGATE_BYTES = TOTAL_BYTES - METADATA_RESERVE_BYTES


class BudgetRefused(Exception):
    """Refusal carrying a fixed, non-secret reason string."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


BudgetSnapshot = namedtuple(
    "BudgetSnapshot",
    "activephase nextphase usedraw usedmetadata totalused frozen complete",
)
PhaseGrant = namedtuple("PhaseGrant", "phase deadline raw_allowance")


class QualificationBudget:
    """Immutable-start, ordered phase budget with byte and time ceilings."""

    def __init__(self, clock):
        if not callable(clock):
            raise BudgetRefused("invalid-clock")
        self._clock = clock
        self._last_reading = None
        self._start = self._read_clock()
        self._overall_deadline = self._start + TOTAL_SECONDS
        self._index = 0
        self._active = None
        self._phase_deadline = None
        self._phase_raw_used = 0
        self._raw_used = 0
        self._meta_used = 0
        self._frozen = False
        self._complete = False

    # -- injected clock -------------------------------------------------
    def _read_clock(self):
        try:
            value = self._clock()
        except Exception:
            value = None
        try:
            valid = type(value) in (int, float) and math.isfinite(value)
        except (OverflowError, ValueError, TypeError):
            valid = False
        if not valid or (self._last_reading is not None and value < self._last_reading):
            self._frozen = True
            raise BudgetRefused("invalid-clock")
        self._last_reading = value
        return value

    # -- validation -----------------------------------------------------
    @staticmethod
    def _check_count(byte_count):
        if type(byte_count) is not int or byte_count < 0:
            raise BudgetRefused("invalid-count")
        return byte_count

    def _freeze(self, reason):
        self._frozen = True
        raise BudgetRefused(reason)

    def _guard_clock(self):
        now = self._read_clock()
        if self._frozen:
            raise BudgetRefused("frozen")
        if now >= self._overall_deadline:
            self._freeze("total-deadline-exhausted")
        if self._active is not None and now >= self._phase_deadline:
            self._freeze("deadline-exhausted")
        return now

    def _raw_allowance(self, name):
        return max(
            0,
            min(
                PHASE_RAW_BYTES[name] - self._phase_raw_used,
                RAW_AGGREGATE_BYTES - self._raw_used,
                TOTAL_BYTES - self._raw_used - self._meta_used,
            ),
        )

    # -- public policy API ----------------------------------------------
    def begin(self, name):
        now = self._guard_clock()
        if self._complete:
            raise BudgetRefused("already-complete")
        if self._active is not None:
            raise BudgetRefused("phase-active")
        if not isinstance(name, str) or name not in PHASE_RAW_BYTES:
            raise BudgetRefused("unknown-phase")
        if PHASE_ORDER.index(name) != self._index:
            raise BudgetRefused("phase-order")
        required = sum(PHASE_SECONDS[p] for p in PHASE_ORDER[self._index:])
        if now + required > self._overall_deadline:
            self._freeze("insufficient-time")
        self._active = name
        self._phase_deadline = now + PHASE_SECONDS[name]
        self._phase_raw_used = 0
        return PhaseGrant(name, self._phase_deadline, self._raw_allowance(name))

    def charge_raw(self, byte_count):
        self._guard_clock()
        self._check_count(byte_count)
        if self._frozen:
            raise BudgetRefused("frozen")
        if self._active is None:
            raise BudgetRefused("no-active-phase")
        if byte_count > PHASE_RAW_BYTES[self._active] - self._phase_raw_used:
            self._freeze("phase-raw-limit")
        if byte_count > RAW_AGGREGATE_BYTES - self._raw_used:
            self._freeze("aggregate-raw-limit")
        if byte_count > TOTAL_BYTES - self._raw_used - self._meta_used:
            self._freeze("total-limit")
        self._phase_raw_used += byte_count
        self._raw_used += byte_count

    def charge_metadata(self, byte_count):
        self._guard_clock()
        self._check_count(byte_count)
        if self._frozen:
            raise BudgetRefused("frozen")
        if byte_count > TOTAL_BYTES - self._raw_used - self._meta_used:
            self._freeze("total-limit")
        self._meta_used += byte_count

    def finish(self, name, confirmed_success):
        now = self._guard_clock()
        if self._active is None or name != self._active:
            raise BudgetRefused("no-active-phase")
        if type(confirmed_success) is not bool:
            self._freeze("invalid-success")
        if not confirmed_success:
            self._freeze("phase-failed")
        if now >= self._phase_deadline:
            self._freeze("deadline-exhausted")
        self._active = None
        self._phase_deadline = None
        self._phase_raw_used = 0
        self._index += 1
        if self._index == len(PHASE_ORDER):
            self._complete = True

    def snapshot(self):
        try:
            self._guard_clock()
        except BudgetRefused:
            # Observing an invalid/expired clock latches failure; inspection of
            # that frozen state remains available without reopening any phase.
            pass
        index = self._index + (1 if self._active is not None else 0)
        return BudgetSnapshot(
            activephase=self._active,
            nextphase=PHASE_ORDER[index] if index < len(PHASE_ORDER) else None,
            usedraw=self._raw_used,
            usedmetadata=self._meta_used,
            totalused=self._raw_used + self._meta_used,
            frozen=self._frozen,
            complete=self._complete,
        )
