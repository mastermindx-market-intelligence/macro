"""Adversarial, synthetic chronology checks. No market data or empirical activation."""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path
import unittest
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pilot_chronology_subject", ROOT / "scripts/options_pilot_study_adapter.py")
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
UTC = timezone.utc

def at(hour, minute=0, day=1):
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)

def p1(**updates):
    row = {"pilot": "P1", "decision_at": at(15), "label_mature_at": at(15, 35)}
    row.update(updates)
    return row

def calendar():
    # Deliberately synthetic session list; not a certified exchange calendar.
    days = []
    x = date(2026, 10, 1)
    while len(days) < 24:
        if x.weekday() < 5:
            days.append(x)
        x += timedelta(days=1)
    return days

def p3(sessions, **updates):
    row = {"pilot": "P3", "formation_session": sessions[0],
           "label_mature_at": datetime.combine(sessions[20], datetime.min.time(), UTC) + timedelta(hours=23)}
    row.update(updates)
    return row

class ChronologyTests(unittest.TestCase):
    def purge(self, row, **kwargs):
        args = dict(training_cutoff=at(15,45), validation_start=at(16), sessions=[])
        args.update(kwargs)
        return a.purge_training_rows([row], **args)

    def test_future_outcome_cannot_be_rescued_by_claimed_maturity(self):
        row = p1(label_mature_at=at(15,5))
        self.assertEqual(self.purge(row, training_cutoff=at(15,10)), ([], [row]))

    def test_maturity_cannot_precede_actual_label_end(self):
        row = p1(label_mature_at=at(15,5))
        self.assertEqual(self.purge(row), ([], [row]))

    def test_exact_end_and_maturity_at_fit_is_valid(self):
        row = p1(label_mature_at=at(15,30))
        self.assertEqual(self.purge(row, training_cutoff=at(15,30)), ([row], []))

    def test_missing_maturity_stays_purged(self):
        row = p1(label_mature_at=None)
        self.assertEqual(self.purge(row), ([], [row]))

    def test_late_maturity_stays_purged(self):
        row = p1(label_mature_at=at(15,50))
        self.assertEqual(self.purge(row), ([], [row]))

    def test_end_reaching_validation_is_purged(self):
        row = p1(decision_at=at(15,30), label_mature_at=at(16,5))
        self.assertEqual(self.purge(row), ([], [row]))

    def test_naive_decision_is_typed_refusal(self):
        with self.assertRaises(a.Refusal):
            self.purge(p1(decision_at=at(15).replace(tzinfo=None)))

    def test_naive_cutoff_is_typed_refusal(self):
        with self.assertRaises(a.Refusal):
            self.purge(p1(), training_cutoff=at(15,45).replace(tzinfo=None))

    def test_naive_maturity_is_typed_refusal(self):
        with self.assertRaises(a.Refusal):
            self.purge(p1(label_mature_at=at(15,35).replace(tzinfo=None)))

    def test_naive_validation_is_typed_refusal(self):
        with self.assertRaises(a.Refusal):
            self.purge(p1(), validation_start=at(16).replace(tzinfo=None))

    def test_invalid_validation_type_is_typed_refusal(self):
        with self.assertRaises(a.Refusal):
            self.purge(p1(), validation_start="2026-10-01T16:00Z")

    def test_invalid_cutoff_type_is_typed_refusal(self):
        with self.assertRaises(a.Refusal):
            self.purge(p1(), training_cutoff=date(2026,10,1))

    def test_fit_not_before_validation_is_refused(self):
        with self.assertRaises(a.Refusal):
            self.purge(p1(), training_cutoff=at(17))

    def test_different_offsets_compare_as_instants(self):
        row = p1(decision_at=at(15).astimezone(timezone(timedelta(hours=-4))),
                 label_mature_at=at(15,35).astimezone(timezone(timedelta(hours=2))))
        self.assertEqual(self.purge(row), ([row], []))

    def test_duration_is_elapsed_minutes_across_dst_fold(self):
        start = datetime(2026,11,1,1,45,tzinfo=ZoneInfo("America/New_York"),fold=0)
        lo, hi = a.label_interval(p1(decision_at=start), sessions=[])
        self.assertEqual(hi.astimezone(UTC)-lo.astimezone(UTC), timedelta(minutes=30))

    def test_overflow_is_typed_refusal(self):
        with self.assertRaises(a.Refusal):
            a.label_interval(p1(decision_at=datetime.max.replace(tzinfo=UTC)), sessions=[])

    def test_missing_p3_horizon_stays_refused(self):
        ss=calendar()
        with self.assertRaises(a.Refusal):
            a.label_interval(p3(ss), sessions=ss[:20])

    def test_duplicate_sessions_refused(self):
        ss=calendar()
        with self.assertRaises(a.Refusal):
            a.label_interval(p3(ss), sessions=[ss[0]]*21)

    def test_unsorted_sessions_refused(self):
        ss=calendar();ss[5],ss[6]=ss[6],ss[5]
        with self.assertRaises(a.Refusal):
            a.label_interval(p3(ss), sessions=ss)

    def test_reversed_endpoint_refused(self):
        ss=calendar();ss[20]=ss[0]-timedelta(days=1)
        with self.assertRaises(a.Refusal):
            a.label_interval(p3(calendar()), sessions=ss)

    def test_non_date_calendar_entries_refused(self):
        for bad in ["2026-10-09", True, None, at(16), float("nan")]:
            with self.subTest(bad=repr(bad)):
                ss=calendar();ss[5]=bad
                with self.assertRaises(a.Refusal):
                    a.label_interval(p3(calendar()), sessions=ss)

    def test_calendar_container_malformed_refused(self):
        for bad in [None, 3, "2026-10-01"]:
            with self.subTest(bad=bad), self.assertRaises(a.Refusal):
                a.label_interval(p3(calendar()), sessions=bad)

    def test_valid_tuple_calendar_counts_twenty_supplied_sessions(self):
        ss=calendar()
        self.assertEqual(a.label_interval(p3(ss), sessions=tuple(ss)), (ss[0],ss[20]))
        self.assertNotEqual(ss[20], ss[0]+timedelta(days=20))

    def test_calendar_generator_is_frozen_once_for_multiple_rows(self):
        ss=calendar();row=p3(ss)
        cutoff=datetime.combine(ss[22],datetime.min.time(),UTC)
        validation=ss[23]
        rows=[row,dict(row)]
        kept,purged=a.purge_training_rows(rows,training_cutoff=cutoff,validation_start=validation,sessions=(x for x in ss))
        self.assertEqual(kept,rows);self.assertEqual(purged,[])

    def test_p3_label_after_fit_is_purged_despite_early_maturity(self):
        ss=calendar();row=p3(ss,label_mature_at=at(23))
        self.assertEqual(self.purge(row,training_cutoff=at(12,day=2),validation_start=ss[23],sessions=ss),([], [row]))

    def test_p3_maturity_day_before_label_end_is_purged(self):
        ss=calendar();row=p3(ss,label_mature_at=at(23))
        cutoff=datetime.combine(ss[22],datetime.min.time(),UTC)
        self.assertEqual(self.purge(row,training_cutoff=cutoff,validation_start=ss[23],sessions=ss),([], [row]))

    def test_input_objects_not_mutated(self):
        ss=calendar();row=p3(ss);before=copy.deepcopy((row,ss))
        self.purge(row,training_cutoff=datetime.combine(ss[22],datetime.min.time(),UTC),validation_start=ss[23],sessions=ss)
        self.assertEqual((row,ss),before)

    def test_empirical_execution_remains_refused(self):
        with self.assertRaises(a.Refusal) as error:
            a.run_empirical()
        self.assertEqual(error.exception.code,"EMPIRICAL_GATES_UNSATISFIED")
        self.assertEqual(a.EMPIRICAL_GATES,("G0","G1","G2","G3","G4","G5","G6"))

if __name__ == "__main__":
    unittest.main()
