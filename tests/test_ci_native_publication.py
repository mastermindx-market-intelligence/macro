#!/usr/bin/env python3
"""Discriminating tests for native_publication (stdlib unittest only).

Run:  python3 -m unittest test_native_publication -v
"""

from __future__ import annotations

import copy
import dataclasses
import unittest

from scripts.ci.native_publication import (
    ABSENT,
    UNKNOWN,
    ClosedUnmergedError,
    ExpectedOutput,
    ExpectedPublication,
    IdentityMismatchError,
    IncompleteReadbackError,
    MalformedEvidenceError,
    ObservedOutput,
    ObservedPublication,
    PublicationOutcome,
    UnknownAncestryError,
    UnattestedRouteError,
    validate_publication,
)

OWNER = "acme"
NAME = "macro"
REF = "refs/heads/main"
PR = 4242
SRC = "a" * 40
MERGE = "b" * 40
TARGET = "c" * 40
DESCENDANT = "d" * 40
BLOB_A = "1" * 40
BLOB_B = "2" * 40

DEL_SITE = "site/theme.js"


def expected_outputs():
    return (
        ExpectedOutput("site/index.html", "100644", BLOB_A),
        ExpectedOutput("site/data/bonds.json", "100644", BLOB_B),
        ExpectedOutput(DEL_SITE, ABSENT, ABSENT),  # required deletion (absent mode+blob)
    )


def expected():
    return ExpectedPublication(OWNER, NAME, REF, PR, SRC, expected_outputs())


def observed(**over):
    fields = dict(
        repo_owner=OWNER,
        repo_name=NAME,
        target_ref=REF,
        pr_number=PR,
        source_head=SRC,
        pr_state="closed",
        merged=True,
        merge_sha=MERGE,
        observed_target_sha=TARGET,
        ancestor_proof=True,
        output_readback=(
            ObservedOutput("site/index.html", "100644", BLOB_A),
            ObservedOutput("site/data/bonds.json", "100644", BLOB_B),
            ObservedOutput(DEL_SITE, ABSENT, ABSENT),  # deletion confirmed
        ),
        protected_route_attestation=True,
    )
    fields.update(over)
    return ObservedPublication(**fields)


class PublishedTests(unittest.TestCase):
    def test_numeric_truthiness_never_supplies_ancestry_evidence(self):
        for value in (0, 1, 0.0, 1.0):
            with self.subTest(value=value, value_type=type(value).__name__):
                with self.assertRaises(MalformedEvidenceError):
                    observed(ancestor_proof=value)

    def test_real_published_including_exact_deletion(self):
        receipt = validate_publication(expected(), observed())
        self.assertIs(PublicationOutcome.PUBLISHED, receipt.outcome)
        self.assertEqual(MERGE, receipt.merge_sha)
        self.assertEqual(TARGET, receipt.observed_target_sha)
        self.assertTrue(receipt.attestation_relied_upon)
        self.assertTrue(any("QLedger" in note for note in receipt.notes))

    def test_legitimate_later_target_descendant_is_published(self):
        # main moved on after the merge; the merge SHA is still in ancestry.
        receipt = validate_publication(
            expected(), observed(observed_target_sha=DESCENDANT, ancestor_proof=True)
        )
        self.assertIs(PublicationOutcome.PUBLISHED, receipt.outcome)
        self.assertEqual(DESCENDANT, receipt.observed_target_sha)

    def test_merge_and_source_sha_are_distinct_obligations(self):
        # PUBLISHED carries the merge SHA, not a relabelled source head.
        receipt = validate_publication(expected(), observed())
        self.assertEqual(MERGE, receipt.merge_sha)
        self.assertNotEqual(receipt.merge_sha, receipt.source_head)
        # Reporting the source head as the merge commit is malformed evidence.
        with self.assertRaises(MalformedEvidenceError) as caught:
            validate_publication(expected(), observed(merge_sha=SRC))
        self.assertIn("source_head", caught.exception.reason)

    def test_inputs_are_immutable_and_validation_is_pure(self):
        exp, obs = expected(), observed()
        exp_copy, obs_copy = copy.deepcopy(exp), copy.deepcopy(obs)
        validate_publication(exp, obs)
        self.assertEqual(exp_copy, exp)
        self.assertEqual(obs_copy, obs)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            exp.pr_number = 7  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            obs.merged = False  # type: ignore[misc]


class PendingTests(unittest.TestCase):
    def test_queued_open_unmerged_is_pending_never_published(self):
        receipt = validate_publication(
            expected(),
            observed(
                pr_state="open",
                merged=False,
                merge_sha=None,
                observed_target_sha=None,
                ancestor_proof=UNKNOWN,
                output_readback=(),
                protected_route_attestation=False,
            ),
        )
        self.assertIs(PublicationOutcome.PENDING, receipt.outcome)
        self.assertFalse(receipt.attestation_relied_upon)
        self.assertIsNone(receipt.merge_sha)
        self.assertTrue(any("not published output" in note for note in receipt.notes))

    def test_pending_requires_well_formed_identity(self):
        with self.assertRaises(IdentityMismatchError):
            validate_publication(
                expected(),
                observed(
                    pr_state="open",
                    merged=False,
                    merge_sha=None,
                    observed_target_sha=None,
                    ancestor_proof=UNKNOWN,
                    output_readback=(),
                    protected_route_attestation=False,
                    source_head="e" * 40,
                ),
            )

    def test_closed_unmerged_is_refused(self):
        with self.assertRaises(ClosedUnmergedError) as caught:
            validate_publication(
                expected(),
                observed(
                    merged=False,
                    merge_sha=None,
                    ancestor_proof=False,
                    output_readback=(),
                    protected_route_attestation=False,
                ),
            )
        self.assertIn("refused", caught.exception.reason)


class AncestryTests(unittest.TestCase):
    def test_unknown_ancestry_refuses(self):
        with self.assertRaises(UnknownAncestryError) as caught:
            validate_publication(expected(), observed(ancestor_proof=UNKNOWN))
        self.assertIn("UNKNOWN", caught.exception.reason)

    def test_false_ancestry_refuses(self):
        with self.assertRaises(UnknownAncestryError) as caught:
            validate_publication(expected(), observed(ancestor_proof=False))
        self.assertIn("False", caught.exception.reason)

    def test_missing_ancestor_proof_value_refuses(self):
        with self.assertRaises(MalformedEvidenceError):
            validate_publication(expected(), observed(ancestor_proof=None))


class IdentityTests(unittest.TestCase):
    def test_mismatched_repo_refuses(self):
        with self.assertRaises(IdentityMismatchError):
            validate_publication(expected(), observed(repo_name="other"))

    def test_mismatched_owner_refuses(self):
        with self.assertRaises(IdentityMismatchError):
            validate_publication(expected(), observed(repo_owner="other"))

    def test_mismatched_target_ref_refuses(self):
        with self.assertRaises(IdentityMismatchError):
            validate_publication(expected(), observed(target_ref="refs/heads/staging"))

    def test_mismatched_pr_number_refuses(self):
        with self.assertRaises(IdentityMismatchError):
            validate_publication(expected(), observed(pr_number=99))

    def test_mismatched_source_head_refuses(self):
        with self.assertRaises(IdentityMismatchError):
            validate_publication(expected(), observed(source_head="e" * 40))

    def test_spoofed_identity_never_succeeds(self):
        for over in (
            {"repo_owner": "evil"},
            {"repo_name": "evil"},
            {"target_ref": "refs/heads/evil"},
            {"pr_number": PR + 1},
            {"source_head": "e" * 40},
        ):
            with self.assertRaises(IdentityMismatchError):
                validate_publication(expected(), observed(**over))


class MalformedEvidenceTests(unittest.TestCase):
    def test_bad_sha_shapes_refuse(self):
        for bad in ("", "ABCDEF", "g" * 40, "a" * 39, "a" * 41, "A" * 40, 12345, None):
            with self.assertRaises(MalformedEvidenceError):
                validate_publication(expected(), observed(merge_sha=bad))
            with self.assertRaises(MalformedEvidenceError):
                validate_publication(expected(), observed(observed_target_sha=bad))

    def test_uppercase_or_garbage_source_head_refuses_at_construction(self):
        for bad in ("A" * 40, "zz", "0x" + "a" * 38):
            with self.assertRaises(MalformedEvidenceError):
                expected().__class__(OWNER, NAME, REF, PR, bad, expected_outputs())
            with self.assertRaises(MalformedEvidenceError):
                observed(source_head=bad)

    def test_merged_requires_merge_sha(self):
        with self.assertRaises(MalformedEvidenceError):
            validate_publication(expected(), observed(merge_sha=None))

    def test_merged_without_attestation_refuses(self):
        with self.assertRaises(UnattestedRouteError) as caught:
            validate_publication(expected(), observed(protected_route_attestation=False))
        self.assertIn("attestation", caught.exception.reason)

    def test_state_and_merged_flag_must_agree(self):
        with self.assertRaises(MalformedEvidenceError):
            validate_publication(expected(), observed(pr_state="open"))
        with self.assertRaises(MalformedEvidenceError):
            validate_publication(
                expected(),
                observed(merged=False, merge_sha=MERGE),
            )
        with self.assertRaises(MalformedEvidenceError):
            observed(pr_state="merged")  # not an open/closed state

    def test_non_bool_flags_refuse(self):
        with self.assertRaises(MalformedEvidenceError):
            observed(merged="yes")
        with self.assertRaises(MalformedEvidenceError):
            observed(protected_route_attestation=1)

    def test_wrong_types_refuse(self):
        with self.assertRaises(MalformedEvidenceError):
            validate_publication(expected(), "not an observation")  # type: ignore[arg-type]
        with self.assertRaises(MalformedEvidenceError):
            validate_publication("not an expectation", observed())  # type: ignore[arg-type]
        with self.assertRaises(MalformedEvidenceError):
            ExpectedPublication(OWNER, NAME, REF, "4242", SRC, expected_outputs())
        with self.assertRaises(MalformedEvidenceError):
            ExpectedPublication(OWNER, NAME, REF, True, SRC, expected_outputs())


class ReadbackCompletenessTests(unittest.TestCase):
    def test_missing_expected_output_path_refuses(self):
        short = observed(
            output_readback=(
                ObservedOutput("site/index.html", "100644", BLOB_A),
                ObservedOutput("site/data/bonds.json", "100644", BLOB_B),
            )
        )
        with self.assertRaises(IncompleteReadbackError) as caught:
            validate_publication(expected(), short)
        self.assertIn(DEL_SITE, caught.exception.reason)

    def test_unknown_unresolved_entry_refuses(self):
        unresolved = observed(
            output_readback=(
                ObservedOutput("site/index.html", "100644", BLOB_A),
                ObservedOutput("site/data/bonds.json", UNKNOWN, UNKNOWN),
                ObservedOutput(DEL_SITE, ABSENT, ABSENT),
            )
        )
        with self.assertRaises(IncompleteReadbackError) as caught:
            validate_publication(expected(), unresolved)
        self.assertIn("site/data/bonds.json", caught.exception.reason)

    def test_extra_readback_path_refuses(self):
        extra = observed(
            output_readback=(
                ObservedOutput("site/index.html", "100644", BLOB_A),
                ObservedOutput("site/data/bonds.json", "100644", BLOB_B),
                ObservedOutput(DEL_SITE, ABSENT, ABSENT),
                ObservedOutput("site/rogue.html", "100644", BLOB_B),
            )
        )
        with self.assertRaises(IncompleteReadbackError) as caught:
            validate_publication(expected(), extra)
        self.assertIn("site/rogue.html", caught.exception.reason)

    def test_duplicate_readback_path_refuses(self):
        # Duplicate paths fail closed at construction, before validation.
        with self.assertRaises(MalformedEvidenceError):
            observed(
                output_readback=(
                    ObservedOutput("site/index.html", "100644", BLOB_A),
                    ObservedOutput("site/index.html", "100644", BLOB_A),
                    ObservedOutput("site/data/bonds.json", "100644", BLOB_B),
                    ObservedOutput(DEL_SITE, ABSENT, ABSENT),
                )
            )

    def test_duplicate_expected_path_refuses_at_construction(self):
        with self.assertRaises(MalformedEvidenceError):
            ExpectedPublication(
                OWNER,
                NAME,
                REF,
                PR,
                SRC,
                expected_outputs() + (ExpectedOutput("site/index.html", "100644", BLOB_A),),
            )

    def test_empty_expected_outputs_refuse(self):
        with self.assertRaises(MalformedEvidenceError):
            ExpectedPublication(OWNER, NAME, REF, PR, SRC, ())


class UnsafePathTests(unittest.TestCase):
    def test_unsafe_expected_paths_refuse_at_construction(self):
        unsafe = [
            "/etc/passwd",
            "../escape.js",
            "site/../../escape.js",
            "site//theme.js",
            "site/./theme.js",
            "site/",
            "",
            "C:\\theme.js",
            "site\\theme.js",
            "site/\x00theme.js",
            "site/theme.js\n",
        ]
        for path in unsafe:
            with self.assertRaises(MalformedEvidenceError):
                ExpectedOutput(path, "100644", BLOB_A)

    def test_unsafe_observed_path_refuses(self):
        with self.assertRaises(MalformedEvidenceError):
            observed(
                output_readback=(
                    ObservedOutput("../evil", "100644", BLOB_A),
                    ObservedOutput("site/data/bonds.json", "100644", BLOB_B),
                    ObservedOutput(DEL_SITE, ABSENT, ABSENT),
                )
            )


class SlotConventionTests(unittest.TestCase):
    def test_deletion_requires_absent_mode_and_blob(self):
        with self.assertRaises(MalformedEvidenceError):
            ExpectedOutput(DEL_SITE, "100644", ABSENT)
        with self.assertRaises(MalformedEvidenceError):
            ObservedOutput(DEL_SITE, "100644", ABSENT)

    def test_unknown_is_rejected_in_expected_and_split_entries(self):
        with self.assertRaises(MalformedEvidenceError):
            ExpectedOutput("site/x", UNKNOWN, UNKNOWN)
        with self.assertRaises(MalformedEvidenceError):
            ObservedOutput("site/x", "100644", UNKNOWN)
        with self.assertRaises(MalformedEvidenceError):
            ObservedOutput("site/x", UNKNOWN, BLOB_A)

    def test_present_file_requires_canonical_mode(self):
        for mode in ("644", "100664", "040000", "100777"):
            with self.assertRaises(MalformedEvidenceError):
                ExpectedOutput("site/index.html", mode, BLOB_A)

    def test_absent_vs_unknown_are_distinct(self):
        self.assertIsNot(ABSENT, UNKNOWN)
        self.assertNotEqual(repr(ABSENT), repr(UNKNOWN))
        # Absent expected + absent observed is publishable; unknown is refused.
        receipt = validate_publication(expected(), observed())
        self.assertIs(PublicationOutcome.PUBLISHED, receipt.outcome)
        with self.assertRaises(IncompleteReadbackError):
            validate_publication(
                expected(),
                observed(
                    output_readback=(
                        ObservedOutput("site/index.html", "100644", BLOB_A),
                        ObservedOutput("site/data/bonds.json", "100644", BLOB_B),
                        ObservedOutput(DEL_SITE, UNKNOWN, UNKNOWN),
                    )
                ),
            )


class SupersessionTests(unittest.TestCase):
    def test_changed_output_is_superseded_not_published(self):
        superseded = observed(
            output_readback=(
                ObservedOutput("site/index.html", "100644", "9" * 40),  # target moved on
                ObservedOutput("site/data/bonds.json", "100644", BLOB_B),
                ObservedOutput(DEL_SITE, ABSENT, ABSENT),
            )
        )
        receipt = validate_publication(expected(), superseded)
        self.assertIs(PublicationOutcome.SUPERSEDED, receipt.outcome)
        self.assertTrue(any("site/index.html" in r for r in receipt.reasons))
        self.assertTrue(receipt.attestation_relied_upon)

    def test_absent_protection_present_file_is_superseded(self):
        # The expected deletion was resurrected on the target.
        resurrected = observed(
            output_readback=(
                ObservedOutput("site/index.html", "100644", BLOB_A),
                ObservedOutput("site/data/bonds.json", "100644", BLOB_B),
                ObservedOutput(DEL_SITE, "100755", BLOB_B),
            )
        )
        receipt = validate_publication(expected(), resurrected)
        self.assertIs(PublicationOutcome.SUPERSEDED, receipt.outcome)
        self.assertTrue(any(DEL_SITE in r for r in receipt.reasons))

    def test_mode_change_only_is_superseded(self):
        mode_change = observed(
            output_readback=(
                ObservedOutput("site/index.html", "100755", BLOB_A),
                ObservedOutput("site/data/bonds.json", "100644", BLOB_B),
                ObservedOutput(DEL_SITE, ABSENT, ABSENT),
            )
        )
        receipt = validate_publication(expected(), mode_change)
        self.assertIs(PublicationOutcome.SUPERSEDED, receipt.outcome)

    def test_superseded_still_requires_complete_readback(self):
        partial = observed(
            output_readback=(ObservedOutput("site/index.html", "100644", "9" * 40),)
        )
        with self.assertRaises(IncompleteReadbackError):
            validate_publication(expected(), partial)

    def test_superseded_still_requires_attestation_and_ancestry(self):
        superseded = observed(
            output_readback=(
                ObservedOutput("site/index.html", "100644", "9" * 40),
                ObservedOutput("site/data/bonds.json", "100644", BLOB_B),
                ObservedOutput(DEL_SITE, ABSENT, ABSENT),
            )
        )
        with self.assertRaises(UnattestedRouteError):
            validate_publication(
                expected(), dataclasses.replace(superseded, protected_route_attestation=False)
            )
        with self.assertRaises(UnknownAncestryError):
            validate_publication(expected(), dataclasses.replace(superseded, ancestor_proof=False))


if __name__ == "__main__":
    unittest.main()
