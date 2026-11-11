"""Synthetic integration witness for the predictive-learning expansion.

Run from the repository root:
    PYTHONPATH=. python research/market_memory/predictive_learning_20261109/verify_incumbent_contracts.py

Uses the existing Data OS contract without changing it. No network, collector,
production store, outcome loader, training, or authority mutation is invoked.
Fixture receipt hashes are synthetic: passing proves mechanics, not provenance,
live capture, sector enrollment, strategy performance, or study admission.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

from lib.dataos import read_contract as owner
from lib.dataos.temporal import PointInTimeError, TemporalError, TemporalProfile


SOURCE_PIN = "f3a547cc09872d9aaa719759a6a2daa2832edad5"
CUTOFF = "2026-11-09T15:00:00Z"
CONTRACT = owner.ViewContract(
    purpose="synthetic market-sector-security temporal integration witness",
    identity={"security_id": "SYNTHETIC_SECURITY_A", "listing_id": "SYNTHETIC_LISTING_A"},
    field_units={"sector_id": "synthetic category", "value": "synthetic index points"},
    adjustment_reference={"basis": "raw"},
    coverage="synthetic only; no producer enrollment or historical completeness claim",
)


def release(*, published="2026-11-09T14:00:00Z", ingested="2026-11-09T14:01:00Z",
            revision=0, sector="SYNTHETIC_SECTOR_A"):
    return {
        "security_id": "SYNTHETIC_SECURITY_A",
        "period_end": "2026-11-06T21:00:00Z",
        "sector_id": sector,
        "value": 100,
        "revision_seq": revision,
        "published_at": published,
        "ingested_at": ingested,
    }


def reconstruct(rows, *, clock="ingested_at", cutoff=CUTOFF):
    request = owner.ReadRequest(owner.ReadMode.RECONSTRUCT, CONTRACT, cutoff=cutoff, clock=clock)
    dependency = owner.Dependency(
        name="sector_source", profile=TemporalProfile.REVISABLE_RELEASE,
        rows=rows, key_fields=("security_id", "period_end"),
    )
    return owner.reconstruct(request, {"sector_source": dependency},
                             required=("sector_source",), code_version=SOURCE_PIN)


def retained_fixture():
    # These are fixture decision bytes, NOT a valid enrolled Prophet record.
    payload = json.dumps({
        "fixture_only": True, "decision_cutoff": CUTOFF,
        "sector_id": "SYNTHETIC_SECTOR_A", "signal": "abstain",
        "training_eligible": False, "promotion_eligible": False,
    }, sort_keys=True, separators=(",", ":")).encode()
    return owner.RetainedOutput(
        output_id="synthetic-decision-a", payload=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
        publishing_receipt_sha256=hashlib.sha256(b"synthetic receipt, not authentication").hexdigest(),
    )


class IncumbentContractWitness(unittest.TestCase):
    def test_late_arrival_distinguishes_publication_from_system_observation(self):
        row = release(ingested="2026-11-09T16:00:00Z")
        public = reconstruct([row], clock="published_at")
        observed = reconstruct([row], clock="ingested_at")
        self.assertEqual(len(public.values["sector_source"]), 1)
        self.assertEqual(len(observed.values["sector_source"]), 0)
        self.assertEqual(public.evidence["knowledge"], "publisher_availability")
        self.assertEqual(observed.evidence["knowledge"], "system_observation")
        self.assertEqual(public.label, "reconstruction")
        self.assertEqual(observed.label, "reconstruction")

    def test_future_revision_cannot_change_earlier_selected_inputs(self):
        first = release()
        later = release(published="2026-11-09T16:00:00Z", ingested="2026-11-09T16:01:00Z",
                        revision=1, sector="SYNTHETIC_SECTOR_B")
        earlier = reconstruct([first])
        augmented = reconstruct([first, later])
        self.assertEqual(dict(earlier.values), dict(augmented.values))
        self.assertEqual(dict(owner.selected_input_sha256s(earlier)),
                         dict(owner.selected_input_sha256s(augmented)))
        self.assertEqual(augmented.values["sector_source"][0]["sector_id"], "SYNTHETIC_SECTOR_A")

    def test_revision_becomes_visible_only_at_its_own_observation_cut(self):
        rows = [release(), release(published="2026-11-09T16:00:00Z",
                                  ingested="2026-11-09T16:01:00Z", revision=1,
                                  sector="SYNTHETIC_SECTOR_B")]
        result = reconstruct(rows, cutoff="2026-11-09T16:01:00Z")
        self.assertEqual(len(result.values["sector_source"]), 1)
        self.assertEqual(result.values["sector_source"][0]["sector_id"], "SYNTHETIC_SECTOR_B")

    def test_known_future_schedule_is_not_discarded_as_a_future_result(self):
        schedule = {"event_at": "2026-11-12T21:00:00Z",
                    "published_at": "2026-11-06T12:00:00Z",
                    "ingested_at": "2026-11-06T12:01:00Z", "kind": "scheduled_release"}
        rows = owner.eligible_rows([schedule], TemporalProfile.EVENT,
                                   cutoff=CUTOFF, clock="ingested_at")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "scheduled_release")

    def test_requested_clock_never_falls_back_to_a_more_convenient_clock(self):
        row = release()
        del row["published_at"]
        with self.assertRaises(owner.ReadRefusal) as caught:
            reconstruct([row], clock="published_at")
        self.assertIs(caught.exception.code, owner.RefusalCode.MISSING_CLOCK_VALUE)

    def test_missing_sector_dependency_refuses_before_inventing_context(self):
        request = owner.ReadRequest(owner.ReadMode.RECONSTRUCT, CONTRACT,
                                    cutoff=CUTOFF, clock="ingested_at")
        with self.assertRaises(owner.ReadRefusal) as caught:
            owner.reconstruct(request, {}, required=("sector_source",), code_version=SOURCE_PIN)
        self.assertIs(caught.exception.code, owner.RefusalCode.UNBOUND_DEPENDENCY)

    def test_later_identity_generation_cannot_substitute_for_earlier_generation(self):
        generations = (
            owner.GenerationRef("synthetic-g0", published_at="2026-11-06T12:00:00Z",
                                ingested_at="2026-11-06T12:01:00Z"),
            owner.GenerationRef("synthetic-g1", published_at="2026-11-09T16:00:00Z",
                                ingested_at="2026-11-09T16:01:00Z", supersedes="synthetic-g0"),
        )
        selected = owner.select_generation(generations, cutoff=CUTOFF, clock="ingested_at")
        self.assertEqual(selected.generation_id, "synthetic-g0")
        with self.assertRaises(owner.ReadRefusal) as caught:
            owner.select_generation(generations, cutoff=CUTOFF, clock="ingested_at",
                                    pinned_generation_id="synthetic-g1")
        self.assertIs(caught.exception.code, owner.RefusalCode.STALE_GENERATION)

    def test_replay_returns_exact_retained_decision_bytes(self):
        retained = retained_fixture()
        request = owner.ReadRequest(owner.ReadMode.REPLAY, CONTRACT, output_id=retained.output_id)
        result = owner.replay(request, retained)
        self.assertEqual(result.payload, retained.payload)
        self.assertEqual(result.label, "replay")
        self.assertEqual(result.values, {})
        decoded = json.loads(result.payload)
        self.assertIs(decoded["training_eligible"], False)
        self.assertIs(decoded["promotion_eligible"], False)

    def test_absent_replay_does_not_recompute_or_substitute_latest(self):
        request = owner.ReadRequest(owner.ReadMode.REPLAY, CONTRACT, output_id="missing-decision")
        with self.assertRaises(owner.ReadRefusal) as caught:
            owner.replay(request, None)
        self.assertIs(caught.exception.code, owner.RefusalCode.NO_RETAINED_OUTPUT)

    def test_replay_rejects_changed_bytes(self):
        original = retained_fixture()
        corrupt = owner.RetainedOutput(original.output_id, original.payload + b" ",
                                      original.sha256, original.publishing_receipt_sha256)
        request = owner.ReadRequest(owner.ReadMode.REPLAY, CONTRACT, output_id=original.output_id)
        with self.assertRaises(owner.ReadRefusal) as caught:
            owner.replay(request, corrupt)
        self.assertIs(caught.exception.code, owner.RefusalCode.RETAINED_DIGEST_MISMATCH)

    def test_fixed_population_keeps_uninspected_and_halted_members(self):
        population = ("SYNTHETIC_LISTING_A", "SYNTHETIC_LISTING_B", "SYNTHETIC_LISTING_C")
        dispositions = (
            owner.MemberDisposition(population[0], owner.Disposition.SERVED,
                segments=(owner.SourceSegment("synthetic-source", "raw", population[0]),)),
            owner.MemberDisposition(population[1], owner.Disposition.NEVER_INSPECTED),
            owner.MemberDisposition(population[2], owner.Disposition.NO_TRADE,
                                    detail="synthetic confirmed halt receipt"),
        )
        result = owner.account_coverage(CONTRACT, population, dispositions)
        self.assertEqual(result.requested, 3)
        self.assertEqual(sum(result.counts.values()), 3)
        self.assertEqual(result.qualified, (population[0],))
        self.assertEqual(result.population, population)
        # This is DATA coverage, not a replacement for forecast/no-call accounting.
        with self.assertRaises(owner.ReadRefusal) as caught:
            owner.account_coverage(CONTRACT, population, dispositions[:-1])
        self.assertIs(caught.exception.code, owner.RefusalCode.COVERAGE_UNRECONCILED)

    def test_naive_time_and_derived_replay_claims_are_refused(self):
        with self.assertRaises(TemporalError):
            reconstruct([release()], cutoff="2026-11-09T15:00:00")
        with self.assertRaises(PointInTimeError):
            owner.eligible_rows([], TemporalProfile.DERIVED, cutoff=CUTOFF, clock="computed_at")

    def test_owner_inputs_remain_unchanged(self):
        rows = [release()]
        before = copy.deepcopy(rows)
        result = reconstruct(rows)
        self.assertEqual(rows, before)
        with self.assertRaises(TypeError):
            result.values["sector_source"][0]["sector_id"] = "rewritten"


class RecordingResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.checks = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.checks.append({"case": test._testMethodName, "result": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.checks.append({"case": test._testMethodName, "result": "FAIL"})

    def addError(self, test, err):
        super().addError(test, err)
        self.checks.append({"case": test._testMethodName, "result": "ERROR"})


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IncumbentContractWitness)
    result = RecordingResult()
    suite.run(result)
    root = Path(__file__).resolve().parents[3]
    sources = ("lib/dataos/read_contract.py", "lib/dataos/temporal.py", "lib/dataos/nulls.py")
    report = {
        "scope": "SYNTHETIC_INCUMBENT_CONTRACT_PROOF_ONLY",
        "census_source_pin": SOURCE_PIN,
        "tested_source_sha256": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sources},
        "cases_run": result.testsRun,
        "passed": result.wasSuccessful(),
        "checks": result.checks,
        "production_capture_proven": False,
        "sector_producer_enrolled": False,
        "historical_coverage_proven": False,
        "training_or_promotion_authorized": False,
        "predictive_skill_measured": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    for _, detail in result.failures + result.errors:
        print(detail, file=sys.stderr)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
