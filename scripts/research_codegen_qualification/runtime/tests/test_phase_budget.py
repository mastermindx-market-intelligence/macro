"""Adversarial tests for phase_budget: deterministic clocks, no sleeps, no hosts."""

import unittest

from phase_budget import (
    METADATA_RESERVE_BYTES,
    PHASE_ORDER,
    PHASE_RAW_BYTES,
    PHASE_SECONDS,
    RAW_AGGREGATE_BYTES,
    TOTAL_BYTES,
    TOTAL_SECONDS,
    BudgetRefused,
    QualificationBudget,
)

ALL_REASONS = {
    "invalid-clock", "invalid-count", "invalid-success", "unknown-phase",
    "frozen", "phase-active", "phase-order", "already-complete",
    "no-active-phase", "insufficient-time", "deadline-exhausted",
    "phase-failed", "phase-raw-limit", "aggregate-raw-limit", "total-limit",
}


class FakeClock:
    """Deterministic monotonic clock fully controlled by the test."""

    def __init__(self, start=0.0):
        self.value = start

    def __call__(self):
        return self.value

    def advance(self, delta):
        self.value += delta


class FlakyClock(FakeClock):
    """Clock that starts fine, then raises on later readings."""

    def __init__(self, fail_after=1):
        FakeClock.__init__(self)
        self.calls = 0
        self.fail_after = fail_after

    def __call__(self):
        self.calls += 1
        if self.calls > self.fail_after:
            raise RuntimeError("clock exploded")
        return self.value


def budget(start=0.0):
    return QualificationBudget(FakeClock(start))


class PhaseBudgetTest(unittest.TestCase):
    maxDiff = None

    # -- helpers --------------------------------------------------------
    def refused(self, call, *args, **kwargs):
        try:
            call(*args, **kwargs)
        except BudgetRefused as exc:
            self.assertIn(exc.reason, ALL_REASONS)
            self.assertEqual(str(exc), exc.reason)
            return exc.reason
        self.fail("expected BudgetRefused")

    def drive(self, start=0.0, raw_by_phase=None, step=1.0):
        clock = FakeClock(start)
        b = QualificationBudget(clock)
        grants = {}
        for name in PHASE_ORDER:
            grants[name] = b.begin(name)
            raw = (raw_by_phase or {}).get(name, 0)
            if raw:
                b.charge_raw(raw)
            clock.advance(step)
            b.finish(name, True)
        return b, clock, grants

    # -- fixed policy ---------------------------------------------------
    def test_fixed_policy_constants(self):
        self.assertEqual(PHASE_ORDER, ("cli", "archive", "install", "image", "smoke"))
        self.assertEqual(
            PHASE_SECONDS,
            {"cli": 60, "archive": 240, "install": 180, "image": 240, "smoke": 130},
        )
        self.assertEqual(
            PHASE_RAW_BYTES,
            {"cli": 16384, "archive": 0, "install": 16384, "image": 16384, "smoke": 16384},
        )
        self.assertEqual((TOTAL_SECONDS, TOTAL_BYTES, METADATA_RESERVE_BYTES), (900, 65536, 2048))
        self.assertEqual(RAW_AGGREGATE_BYTES, TOTAL_BYTES - METADATA_RESERVE_BYTES)
        self.assertEqual(sum(PHASE_SECONDS.values()), 850)

    def test_grant_reports_deadline_and_allowance(self):
        clock = FakeClock(7.0)
        b = QualificationBudget(clock)
        grant = b.begin("cli")
        self.assertEqual(grant.phase, "cli")
        self.assertEqual(grant.deadline, 67.0)
        self.assertEqual(grant.raw_allowance, 16384)
        clock.advance(3.0)
        b.finish("cli", True)
        grant = b.begin("archive")
        self.assertEqual(grant.deadline, 250.0)
        self.assertEqual(grant.raw_allowance, 0)

    # -- phase order / identity ----------------------------------------
    def test_unknown_phase_refused_without_freeze(self):
        b = budget()
        for bad in ("deploy", "", "CLI", 7, None, ("cli",), ["cli"]):
            self.assertEqual(self.refused(b.begin, bad), "unknown-phase")
        self.assertFalse(b.snapshot().frozen)
        b.begin("cli")
        self.assertEqual(b.snapshot().activephase, "cli")

    def test_begin_while_active_refused_and_recovers(self):
        b = budget()
        b.begin("cli")
        self.assertEqual(self.refused(b.begin, "archive"), "phase-active")
        self.assertFalse(b.snapshot().frozen)
        b.finish("cli", True)
        b.begin("archive")
        self.assertEqual(b.snapshot().activephase, "archive")

    def test_wrong_order_and_replay_refused(self):
        b = budget()
        self.assertEqual(self.refused(b.begin, "archive"), "phase-order")
        self.assertFalse(b.snapshot().frozen)
        b.begin("cli")
        b.finish("cli", True)
        self.assertEqual(self.refused(b.begin, "cli"), "phase-order")
        b.begin("archive")

    def test_begin_after_complete_blocked(self):
        b, _, _ = self.drive()
        self.assertTrue(b.snapshot().complete)
        self.assertEqual(self.refused(b.begin, "cli"), "already-complete")
        self.assertEqual(self.refused(b.begin, "smoke"), "already-complete")

    # -- raw byte accounting -------------------------------------------
    def test_phase_raw_cap_equality_ok_breach_freezes(self):
        b = budget()
        b.begin("cli")
        b.charge_raw(16384)
        self.assertEqual(b.snapshot().usedraw, 16384)
        self.assertEqual(self.refused(b.charge_raw, 1), "phase-raw-limit")
        self.assertTrue(b.snapshot().frozen)
        self.assertEqual(self.refused(b.finish, "cli", True), "frozen")

        b2 = budget()
        b2.begin("cli")
        self.assertEqual(self.refused(b2.charge_raw, 16385), "phase-raw-limit")
        self.assertTrue(b2.snapshot().frozen)

    def test_archive_raw_cap_is_zero(self):
        b = budget()
        b.begin("cli")
        b.finish("cli", True)
        grant = b.begin("archive")
        self.assertEqual(grant.raw_allowance, 0)
        b.charge_raw(0)
        self.assertEqual(b.snapshot().usedraw, 0)
        self.assertEqual(self.refused(b.charge_raw, 1), "phase-raw-limit")
        self.assertTrue(b.snapshot().frozen)

    def test_aggregate_raw_refused_while_phase_caps_valid(self):
        raw = {"cli": 16384, "install": 16384, "image": 16384}
        clock = FakeClock()
        b = QualificationBudget(clock)
        for name in ("cli", "archive", "install", "image"):
            b.begin(name)
            b.charge_raw(raw.get(name, 0))
            clock.advance(1.0)
            b.finish(name, True)
        grant = b.begin("smoke")
        self.assertEqual(grant.raw_allowance, RAW_AGGREGATE_BYTES - 49152)
        self.assertEqual(grant.raw_allowance, 14336)
        self.assertEqual(self.refused(b.charge_raw, 14337), "aggregate-raw-limit")
        self.assertTrue(b.snapshot().frozen)
        self.assertEqual(self.refused(b.finish, "smoke", True), "frozen")

    def test_reserve_excluded_from_raw_and_final_metadata_fits(self):
        raw = {"cli": 16384, "install": 16384, "image": 16384, "smoke": 14336}
        b, _, grants = self.drive(raw_by_phase=raw)
        self.assertEqual(grants["smoke"].raw_allowance, 14336)
        self.assertEqual(b.snapshot().usedraw, 63488)
        self.assertTrue(b.snapshot().complete)
        b.charge_metadata(METADATA_RESERVE_BYTES)
        self.assertEqual(b.snapshot().totalused, TOTAL_BYTES)
        self.assertEqual(self.refused(b.charge_metadata, 1), "total-limit")
        self.assertTrue(b.snapshot().frozen)

    def test_prephase_metadata_reduces_later_allowance(self):
        b = budget()
        b.charge_metadata(60000)
        grant = b.begin("cli")
        self.assertEqual(grant.raw_allowance, 5536)
        b.charge_raw(5536)
        self.assertEqual(b.snapshot().totalused, 65536)
        self.assertEqual(self.refused(b.charge_raw, 1), "total-limit")
        self.assertTrue(b.snapshot().frozen)

    def test_phase_counter_resets_but_aggregate_does_not(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        b.begin("cli")
        b.charge_raw(16384)
        self.assertEqual(b.snapshot().usedraw, 16384)
        clock.advance(1.0)
        b.finish("cli", True)
        grant = b.begin("archive")
        self.assertEqual(grant.raw_allowance, 0)
        clock.advance(1.0)
        b.finish("archive", True)
        grant = b.begin("install")
        self.assertEqual(grant.raw_allowance, 16384)
        self.assertEqual(b.snapshot().usedraw, 16384)
        b.charge_raw(16384)
        clock.advance(1.0)
        b.finish("install", True)
        grant = b.begin("image")
        self.assertEqual(grant.raw_allowance, 16384)
        b.charge_raw(16384)
        clock.advance(1.0)
        b.finish("image", True)
        self.assertEqual(b.snapshot().usedraw, 49152)
        grant = b.begin("smoke")
        self.assertEqual(grant.raw_allowance, 14336)

    # -- time accounting ------------------------------------------------
    def test_phase_deadline_equality_fails(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        self.assertEqual(b.begin("cli").deadline, 60.0)
        clock.advance(60.0)
        self.assertEqual(self.refused(b.finish, "cli", True), "deadline-exhausted")
        self.assertTrue(b.snapshot().frozen)

    def test_phase_deadline_just_before_is_ok(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        b.begin("cli")
        clock.advance(59.5)
        b.finish("cli", True)
        self.assertEqual(b.begin("archive").deadline, 299.5)

    def test_phase_ceiling_runs_from_begin_time(self):
        clock = FakeClock(40.0)
        b = QualificationBudget(clock)
        self.assertEqual(b.begin("cli").deadline, 100.0)
        clock.advance(59.0)
        b.finish("cli", True)

    def test_delayed_entry_keeps_overall_total(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        for name, at in (("cli", 55.0), ("archive", 294.0), ("install", 473.0), ("image", 712.5)):
            b.begin(name)
            clock.advance(at - clock.value)
            b.finish(name, True)
        clock.advance(800.0 - clock.value)
        self.assertEqual(self.refused(b.begin, "smoke"), "insufficient-time")
        self.assertTrue(b.snapshot().frozen)

    def test_delayed_entry_still_completes_within_total(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        for name, at in (("cli", 55.0), ("archive", 294.0), ("install", 473.0), ("image", 712.5)):
            b.begin(name)
            clock.advance(at - clock.value)
            b.finish(name, True)
        clock.advance(714.0 - clock.value)
        grant = b.begin("smoke")
        self.assertEqual(grant.deadline, 844.0)
        clock.advance(843.5 - clock.value)
        b.finish("smoke", True)
        self.assertTrue(b.snapshot().complete)

    def test_late_begin_boundary_equality(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        clock.advance(50.0)
        grant = b.begin("cli")
        self.assertEqual(grant.deadline, 110.0)
        self.assertFalse(b.snapshot().frozen)

    def test_late_begin_past_boundary_freezes(self):
        for late in (50.5, 51.0, 100.0):
            clock = FakeClock()
            b = QualificationBudget(clock)
            clock.advance(late)
            self.assertEqual(self.refused(b.begin, "cli"), "insufficient-time")
            self.assertTrue(b.snapshot().frozen)
            self.assertEqual(self.refused(b.begin, "cli"), "frozen")

    # -- finish semantics -----------------------------------------------
    def test_finish_false_fails_and_freezes(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        b.begin("cli")
        clock.advance(5.0)
        self.assertEqual(self.refused(b.finish, "cli", False), "phase-failed")
        snap = b.snapshot()
        self.assertTrue(snap.frozen)
        self.assertEqual(snap.activephase, "cli")
        self.assertFalse(snap.complete)
        self.assertEqual(self.refused(b.begin, "archive"), "frozen")
        self.assertEqual(self.refused(b.finish, "cli", True), "frozen")

    def test_finish_requires_exact_bool(self):
        for bad in (1, 0, "yes", None, 2.0, [True], (True,)):
            clock = FakeClock()
            b = QualificationBudget(clock)
            b.begin("cli")
            clock.advance(1.0)
            self.assertEqual(self.refused(b.finish, "cli", bad), "invalid-success")
            self.assertTrue(b.snapshot().frozen)
            self.assertEqual(self.refused(b.finish, "cli", True), "frozen")
            self.assertEqual(b.snapshot().usedraw, 0)

    def test_finish_name_mismatch_refused(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        b.begin("cli")
        clock.advance(1.0)
        self.assertEqual(self.refused(b.finish, "archive", True), "no-active-phase")
        self.assertFalse(b.snapshot().frozen)
        b.finish("cli", True)

    # -- charge placement -----------------------------------------------
    def test_charge_raw_requires_active_phase(self):
        b = budget()
        self.assertEqual(self.refused(b.charge_raw, 0), "no-active-phase")
        b.begin("cli")
        b.finish("cli", True)
        self.assertEqual(self.refused(b.charge_raw, 0), "no-active-phase")
        for name in PHASE_ORDER[1:]:
            b.begin(name)
            b.finish(name, True)
        self.assertEqual(self.refused(b.charge_raw, 0), "no-active-phase")
        self.assertFalse(b.snapshot().frozen)

    def test_metadata_allowed_before_between_after(self):
        b = budget()
        b.charge_metadata(100)
        b.begin("cli")
        b.charge_metadata(50)
        b.charge_raw(10)
        b.finish("cli", True)
        b.charge_metadata(25)
        for name in PHASE_ORDER[1:]:
            b.begin(name)
            b.finish(name, True)
        b.charge_metadata(5)
        snap = b.snapshot()
        self.assertEqual((snap.usedmetadata, snap.totalused), (180, 190))

    def test_invalid_counts_rejected_without_freeze(self):
        bads = (True, False, -1, -999, 1.0, 0.0, float("inf"), float("nan"), "8", None, (5,), [5])
        clock = FakeClock()
        b = QualificationBudget(clock)
        b.begin("cli")
        for bad in bads:
            self.assertEqual(self.refused(b.charge_raw, bad), "invalid-count")
            self.assertEqual(self.refused(b.charge_metadata, bad), "invalid-count")
        snap = b.snapshot()
        self.assertEqual((snap.usedraw, snap.usedmetadata), (0, 0))
        self.assertFalse(snap.frozen)
        b.charge_raw(5)
        self.assertEqual(b.snapshot().usedraw, 5)

    def test_zero_counts_allowed(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        b.begin("cli")
        b.charge_raw(0)
        b.charge_metadata(0)
        snap = b.snapshot()
        self.assertEqual((snap.usedraw, snap.usedmetadata, snap.totalused), (0, 0, 0))
        clock.advance(1.0)
        b.finish("cli", True)

    # -- clock validation -----------------------------------------------
    def test_non_callable_clock_rejected(self):
        for bad in (None, 0, "clock", object()):
            with self.assertRaises(BudgetRefused):
                QualificationBudget(bad)

    def test_malformed_clock_freezes(self):
        for bad in (float("nan"), float("inf"), -float("inf"), "late", None, True):
            clock = FakeClock()
            b = QualificationBudget(clock)
            b.begin("cli")
            clock.value = bad
            self.assertEqual(self.refused(b.finish, "cli", True), "invalid-clock")
            self.assertTrue(b.snapshot().frozen)

    def test_backwards_clock_freezes(self):
        clock = FakeClock(10.0)
        b = QualificationBudget(clock)
        clock.value = 9.0
        self.assertEqual(self.refused(b.begin, "cli"), "invalid-clock")
        self.assertTrue(b.snapshot().frozen)

    def test_raising_clock_freezes(self):
        b = QualificationBudget(FlakyClock(fail_after=1))
        self.assertEqual(self.refused(b.begin, "cli"), "invalid-clock")
        self.assertTrue(b.snapshot().frozen)

    def test_equal_clock_readings_allowed(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        b.begin("cli")
        b.finish("cli", True)
        b.begin("archive")
        self.assertEqual(b.snapshot().activephase, "archive")

    # -- snapshot -------------------------------------------------------
    def test_snapshot_shape_transitions(self):
        b = budget()
        snap = b.snapshot()
        self.assertIsInstance(snap, tuple)
        self.assertEqual(
            (snap.activephase, snap.nextphase, snap.usedraw, snap.usedmetadata,
             snap.totalused, snap.frozen, snap.complete),
            (None, "cli", 0, 0, 0, False, False),
        )
        b.begin("cli")
        self.assertEqual(
            (b.snapshot().activephase, b.snapshot().nextphase), ("cli", "archive"))
        b.charge_raw(10)
        b.charge_metadata(3)
        snap = b.snapshot()
        self.assertEqual((snap.usedraw, snap.usedmetadata, snap.totalused), (10, 3, 13))
        b.finish("cli", True)
        snap = b.snapshot()
        self.assertEqual((snap.activephase, snap.nextphase), (None, "archive"))
        b2, _, _ = self.drive()
        self.assertEqual(
            (b2.snapshot().activephase, b2.snapshot().nextphase,
             b2.snapshot().frozen, b2.snapshot().complete),
            (None, None, False, True),
        )

    def test_snapshot_cannot_mutate_or_unfreeze(self):
        clock = FakeClock()
        b = QualificationBudget(clock)
        b.begin("cli")
        clock.advance(60.0)
        self.assertEqual(self.refused(b.finish, "cli", True), "deadline-exhausted")
        snap = b.snapshot()
        self.assertTrue(snap.frozen)
        with self.assertRaises(AttributeError):
            snap.frozen = False
        with self.assertRaises(AttributeError):
            snap.activephase = None
        self.assertTrue(b.snapshot().frozen)
        self.assertEqual(self.refused(b.begin, "archive"), "frozen")
        self.assertEqual(self.refused(b.charge_metadata, 1), "frozen")
        self.assertTrue(b.snapshot().frozen)


if __name__ == "__main__":
    unittest.main()
