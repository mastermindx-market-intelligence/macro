"""Outcome-blind contract tests for the policy-turn-clock R0 coverage audit.

The production change these tests catch is any audit that silently counts daily
rows as episodes, accepts a filesystem timestamp as a decision clock, substitutes
a longer source history, backfills a forward-only source, or emits decision/outcome
vocabulary.  Fixtures are intentionally synthetic and contain metadata only.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

import scripts.policy_turn_clock_monthly_coverage_audit as audit


def record(owner: str, cycles: list[str], **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "owner": owner,
        "path": f"/metadata/{owner}.json",
        "schema": "source.metadata.v1",
        "version": "1",
        "rights": "internal-metadata-only",
        "observed_at": "2026-08-01T00:00:00+00:00",
        "available_at": "2026-08-02T09:30:00+00:00",
        "correction_id": None,
        "correction_at": None,
        "row_count": 3,
        "entity_count": 1,
        "root_count": 1,
        "cycle_ids": cycles,
        "classification": "historical",
        "missingness": "present",
    }
    value.update(overrides)
    return value


class PolicyTurnClockMonthlyCoverageAuditTests(unittest.TestCase):
    def test_uses_unique_monthly_cycles_not_daily_rows(self) -> None:
        report = audit.build_report(
            [record("calendar", ["2024-01", "2024-01", "2024-02"])],
            {"H1": ["calendar"]},
        )
        cell = report["hypotheses"][0]
        self.assertEqual(cell["cycle_count"], 2)
        self.assertEqual(cell["cycles_by_era"]["0DTE_current"], 2)

    def test_rejects_non_explicit_or_filesystem_availability(self) -> None:
        for bad in (
            record("calendar", ["2024-01"], available_at=None),
            record("calendar", ["2024-01"], available_at="2024-01-03"),
            record("calendar", ["2024-01"], mtime="2026-09-03T00:00:00+00:00"),
        ):
            with self.assertRaises(ValueError):
                audit.validate_record(bad)

    def test_requires_the_exact_intersection_and_never_uses_longest_source(self) -> None:
        report = audit.build_report(
            [
                record("calendar", ["2023-01", "2023-02", "2023-03"]),
                record("options", ["2023-02"]),
            ],
            {"H2": ["calendar", "options"]},
        )
        cell = report["hypotheses"][0]
        self.assertEqual(cell["cycle_count"], 1)
        self.assertEqual(cell["availability"], "BELOW_FLOOR")

    def test_missing_required_owner_is_unavailable_not_zero(self) -> None:
        report = audit.build_report(
            [record("calendar", ["2023-01"])],
            {"H1": ["calendar", "treasury"]},
        )
        cell = report["hypotheses"][0]
        self.assertEqual(cell["availability"], "UNAVAILABLE")
        self.assertIsNone(cell["cycle_count"])
        self.assertEqual(cell["missing_owners"], ["treasury"])

    def test_forward_only_source_cannot_be_retrofitted_as_history(self) -> None:
        report = audit.build_report(
            [
                record("calendar", ["2024-01", "2024-02"]),
                record("flow", ["2024-01", "2024-02"], classification="forward_only"),
            ],
            {"H5": ["calendar", "flow"]},
        )
        cell = report["hypotheses"][0]
        self.assertEqual(cell["availability"], "UNAVAILABLE")
        self.assertIn("forward_only", cell["reason"])

    def test_report_is_stably_serializable_and_has_no_decision_fields(self) -> None:
        records = [record("calendar", ["2023-01"]), record("options", ["2023-01"])]
        first = audit.build_report(records, {"H2": ["calendar", "options"]})
        second = audit.build_report(list(reversed(records)), {"H2": ["calendar", "options"]})
        self.assertEqual(audit.canonical_digest(first), audit.canonical_digest(second))
        payload = json.dumps(first).lower()
        for fragment in audit.FORBIDDEN_OUTPUT_FRAGMENTS:
            self.assertNotIn(fragment, payload)

    def test_unknown_availability_is_preserved_without_inventing_a_clock(self) -> None:
        item = record("calendar", ["2024-01"], available_at=None, missingness="unknown")
        report = audit.build_report([item], {"H1": ["calendar"]})
        self.assertEqual(report["sources"][0]["available_at"], None)
        self.assertEqual(report["sources"][0]["row_count"], 3)
        self.assertEqual(report["hypotheses"][0]["availability"], "UNAVAILABLE")


#: The preserved historical artifact must stay byte-for-byte identical.
HISTORICAL_ARTIFACT_RELPATH = "reports/artifacts/policy_turn_clock_monthly_coverage_audit.json"
HISTORICAL_ARTIFACT_SHA256 = "ed7aecc97a12b2b04508c917e28ff9e4ca304f1134baaca59ae2285fb51ef78a"


class PolicyTurnClockMonthlyCoverageAuditMetadataRepairTests(unittest.TestCase):
    """Cases for the 2026-11-05 bounded metadata-validator repair.

    The seven original test methods above are preserved unchanged.  Regression
    cases expose malformed months and invalid counts accepted by the unrepaired
    validator; positive compatibility controls preserve valid months, zero counts,
    unknown availability clocks and the frozen era semantics.  All fixtures are
    explicitly synthetic metadata; no source, provider or host data is read.
    """

    # -- month identifiers ------------------------------------------------

    def test_rejects_malformed_month_identifiers(self) -> None:
        for bad in (
            "2026-99",             # month 99 is not a calendar month
            "2026-00",             # month 0 is not a calendar month
            "2026-13",             # month 13 is not a calendar month
            "9999-99",             # seven characters, still not a month
            "abcd-ef",             # nonnumeric seven-character lookalike
            "2026-٠١",        # non-ASCII numeric lookalike
            "2024-01\n",           # trailing-newline lookalike
            "2026-1",              # not zero padded
            "2026-012",            # over-long month field
        ):
            with self.subTest(cycle=bad):
                with self.assertRaises(ValueError):
                    audit.validate_record(record("calendar", [bad]))

    def test_accepts_genuine_calendar_months(self) -> None:
        for good in (
            "1999-06", "2004-12", "2005-01", "2016-12", "2017-01",
            "2022-12", "2023-01", "2024-01", "2024-12", "9999-12",
        ):
            with self.subTest(cycle=good):
                audit.validate_record(record("calendar", [good]))

    def test_malformed_month_is_reported_not_crashed_by_the_era_classifier(self) -> None:
        with self.assertRaises(ValueError) as caught:
            audit.build_report([record("calendar", ["abcd-ef"])], {"H1": ["calendar"]})
        self.assertIn("cycle_ids", str(caught.exception))

    def test_era_boundaries_are_unchanged_for_genuine_months(self) -> None:
        report = audit.build_report(
            [record("calendar", ["2004-12", "2005-01", "2016-12", "2017-01", "2022-12", "2023-01"])],
            {"H1": ["calendar"]},
        )
        self.assertEqual(
            report["hypotheses"][0]["cycles_by_era"],
            {
                "pre_weeklies": 1,
                "weeklies": 2,
                "modern_pre_0DTE": 2,
                "0DTE_current": 1,
            },
        )

    # -- count fields ----------------------------------------------------

    def test_rejects_non_integer_counts(self) -> None:
        for field in ("row_count", "entity_count", "root_count"):
            for bad in (True, False, 3.0, 1.5, "3", -1):
                with self.subTest(field=field, value=bad):
                    with self.assertRaises(ValueError):
                        audit.validate_record(record("calendar", ["2024-01"], **{field: bad}))

    def test_accepts_zero_and_positive_counts(self) -> None:
        item = record("calendar", ["2024-01"], row_count=0, entity_count=0, root_count=0)
        report = audit.build_report([item], {"H1": ["calendar"]})
        source = report["sources"][0]
        self.assertEqual(source["row_count"], 0)
        self.assertEqual(source["entity_count"], 0)
        self.assertEqual(source["root_count"], 0)

    # -- controls: unknown clock, missingness, outcome-only boundary -----

    def test_unknown_clock_with_zero_counts_remains_valid(self) -> None:
        item = record(
            "calendar",
            ["2024-01"],
            available_at=None,
            missingness="unknown",
            row_count=0,
            entity_count=0,
            root_count=0,
        )
        report = audit.build_report([item], {"H1": ["calendar"]})
        source = report["sources"][0]
        self.assertIsNone(source["available_at"])
        self.assertEqual(source["missingness"], "unknown")
        self.assertEqual(source["row_count"], 0)
        self.assertEqual(report["hypotheses"][0]["availability"], "UNAVAILABLE")

    def test_validator_still_refuses_prohibited_data_domain_fields(self) -> None:
        for bad in ("price_table", "portfolio_book", "prophet_config", "backtest_result"):
            with self.subTest(field=bad):
                with self.assertRaises(ValueError):
                    audit.validate_record(record("calendar", ["2024-01"], **{bad: 1}))

    # -- the real CLI path, on synthetic metadata only -------------------

    def test_cli_writes_synthetic_output_without_touching_the_historical_artifact(self) -> None:
        repo_root = pathlib.Path(__file__).resolve().parents[1]
        artifact = repo_root / HISTORICAL_ARTIFACT_RELPATH
        before = artifact.read_bytes()
        self.assertEqual(hashlib.sha256(before).hexdigest(), HISTORICAL_ARTIFACT_SHA256)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            manifest_path = tmp_path / "synthetic_manifest.json"
            manifest_path.write_text(
                json.dumps({"sources": [record("calendar", ["2024-01", "2024-02"])]})
            )
            json_out = tmp_path / "out" / "audit.json"
            markdown_out = tmp_path / "out" / "audit.md"

            env = dict(os.environ)
            env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.policy_turn_clock_monthly_coverage_audit",
                    "--manifest",
                    str(manifest_path),
                    "--json-out",
                    str(json_out),
                    "--markdown-out",
                    str(markdown_out),
                ],
                cwd=str(repo_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            payload = json.loads(json_out.read_text())
            digest = payload.pop("semantic_digest")
            self.assertEqual(payload["schema"], audit.SCHEMA)
            self.assertEqual(payload["method"], "monthly-cycle-source-coverage-only")
            self.assertEqual(audit.canonical_digest(payload), digest)

            markdown = markdown_out.read_text().lower()
            for fragment in audit.FORBIDDEN_OUTPUT_FRAGMENTS:
                self.assertNotIn(fragment, markdown)

        self.assertEqual(artifact.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
