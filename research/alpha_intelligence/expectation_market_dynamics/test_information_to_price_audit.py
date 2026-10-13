"""Hermetic SRC-A1 audit tests. No providers, writes, outcomes or admission consumers."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

_SPEC = importlib.util.spec_from_file_location("information_to_price_audit", Path(__file__).with_name("information_to_price_audit.py"))
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)

_R1_SPEC = importlib.util.spec_from_file_location(
    "r1_readiness_probe", Path(__file__).with_name("r1_readiness_probe.py")
)
r1 = importlib.util.module_from_spec(_R1_SPEC)
_R1_SPEC.loader.exec_module(r1)

AS_OF = "2026-10-03T12:00:00Z"
PAYLOAD = "a" * 64


def pair(value=1.2, **changes):
    observation = dict.fromkeys(mod.OBSERVATION_COLUMNS)
    observation.update({
        "collection_session_id": "session-a", "provider": "yfinance",
        "provider_record_class": "earnings_estimate", "provider_payload_hash": PAYLOAD,
        "ticker_compat": "ABC", "metric": "EPS", "horizon_label_raw": "+1q",
        "observation_type": "average", "value": value, "aggregation_level": "consensus_snapshot",
        "provider_observed_at": "2026-10-03T10:00:01Z",
        "system_observed_at": "2026-10-03T10:00:02Z", "rights_class": "UNKNOWN",
        "correction_state": "original",
    })
    observation.update(changes)
    observation["attempt_id"] = mod._hash((
        observation["collection_session_id"], observation["provider"],
        observation["ticker_compat"], observation["provider_payload_hash"]))
    observation["observation_id"] = mod._hash(tuple(observation[f] for f in (
        "collection_session_id", "provider", "provider_record_class", "provider_payload_hash",
        "ticker_compat", "metric", "horizon_label_raw", "observation_type")))
    attempt = dict.fromkeys(mod.ATTEMPT_COLUMNS)
    attempt.update({
        "attempt_id": observation["attempt_id"], "collection_session_id": observation["collection_session_id"],
        "provider": observation["provider"], "ticker_compat": observation["ticker_compat"],
        "attempted_at": "2026-10-03T10:00:00Z", "completed_at": "2026-10-03T10:00:03Z",
        "response_payload_hash": observation["provider_payload_hash"],
        "status": "partial", "observation_count": 1, "latency_ms": 3000,
    })
    return observation, attempt


def reasons(report, table="observations"):
    return {r["reason"]: r["count"] for r in report["reasons"] if r["table"] == table}


class TestAudit(unittest.TestCase):
    def test_normal_declared_capture_is_not_rights_or_public_replay(self):
        obs, attempt = pair()
        before = copy.deepcopy((obs, attempt))
        count, _ = pair(5, observation_type="covering_analyst_count")
        attempt["observation_count"] = 2
        before = copy.deepcopy((obs, attempt))
        report = mod.audit([obs, count], [attempt], AS_OF)
        self.assertEqual((obs, attempt), before)
        self.assertEqual(report["populations"]["declared_capture_comparison_partition"],
                         {"structurally_eligible_rows": 2, "excluded_rows": 0})
        self.assertEqual(report["populations"]["central_expectation_rows_with_declared_capture_support"], 1)
        self.assertIn("rights_unknown", reasons(report))
        self.assertIn("missing_public_clock:source_published_at", reasons(report))
        self.assertFalse(report["historical_availability_verified"])
        self.assertFalse(report["predictive_validation"])
        self.assertTrue(all(v is False for v in report["financial_authority"].values()))
        json.dumps(report, allow_nan=False)

    def test_late_knowledge_excluded_even_with_old_publication(self):
        obs, attempt = pair(source_published_at="2026-10-01T00:00:00Z",
                            source_effective_at="2026-09-30T00:00:00Z",
                            system_observed_at="2026-10-03T13:00:00Z")
        attempt["completed_at"] = "2026-10-03T13:00:01Z"
        report = mod.audit([obs], [attempt], AS_OF)
        self.assertIn("clock_after_as_of:system_observed_at", reasons(report))
        self.assertIn("clock_after_as_of:completed_at", reasons(report, "attempts"))
        self.assertEqual(report["populations"]["declared_capture_comparison_partition"]["excluded_rows"], 1)

    def test_false_clocks_naive_and_reversed(self):
        obs, attempt = pair(provider_observed_at="2026-10-03T10:00:04Z")
        report = mod.audit([obs], [attempt], AS_OF)
        self.assertIn("provider_after_system", reasons(report))
        obs["provider_observed_at"] = "2026-10-03T10:00:01"
        attempt["attempted_at"] = "2026-10-03T11:00:00Z"
        report = mod.audit([obs], [attempt], AS_OF)
        self.assertIn("invalid_or_missing_clock:provider_observed_at", reasons(report))
        self.assertIn("attempt_clock_order", reasons(report, "attempts"))
        with self.assertRaises(ValueError):
            mod.audit([obs], [attempt], "2026-10-03T12:00:00")

    def test_source_clocks_not_equated(self):
        obs, attempt = pair(source_effective_at="2026-10-03T11:00:00Z",
                            source_published_at="2026-10-03T09:00:00Z")
        self.assertNotIn("publication_after_capture", reasons(mod.audit([obs], [attempt], AS_OF)))
        obs["source_published_at"] = "2026-10-03T11:00:00Z"
        self.assertIn("publication_after_capture", reasons(mod.audit([obs], [attempt], AS_OF)))

    def test_binding_orphan_and_owner_hash(self):
        obs, attempt = pair()
        for field, value in (("collection_session_id", "other"), ("provider", "other"),
                             ("ticker_compat", "XYZ"), ("response_payload_hash", "b" * 64)):
            changed = dict(attempt, **{field: value})
            report = mod.audit([obs], [changed], AS_OF)
            name = "provider_payload_hash" if field == "response_payload_hash" else field
            self.assertIn("attempt_binding_mismatch:" + name, reasons(report))
        self.assertIn("orphan_attempt_reference", reasons(mod.audit([obs], [], AS_OF)))
        obs["observation_id"] = "wrong-id"
        self.assertIn("owner_id_hash_mismatch", reasons(mod.audit([obs], [attempt], AS_OF)))

    def test_exact_and_conflicting_duplicate_attempts_are_ambiguous(self):
        obs, attempt = pair()
        report = mod.audit([obs], [attempt, dict(attempt)], AS_OF)
        self.assertEqual(reasons(report, "attempts")["duplicate_owner_id_exact"], 2)
        self.assertIn("ambiguous_attempt_reference", reasons(report))
        second = dict(attempt, completed_at="2026-10-03T10:00:04Z")
        report = mod.audit([obs], [attempt, second], AS_OF)
        self.assertEqual(reasons(report, "attempts")["duplicate_owner_id_conflicting"], 2)
        report = mod.audit([obs, dict(obs)], [attempt], AS_OF)
        self.assertEqual(reasons(report)["duplicate_owner_id_exact"], 2)
        self.assertNotIn("observation_count_mismatch", reasons(report, "attempts"))

    def test_zero_null_boolean_nonfinite_and_typed_missingness(self):
        obs, attempt = pair(0)
        self.assertEqual(mod.audit([obs], [attempt], AS_OF)["populations"]["measurement_partition"], {"valid": 1})
        for bad in (True, False, float("nan"), float("inf"), float("-inf"), "1.2"):
            obs, attempt = pair(bad)
            self.assertIn("invalid_measurement", reasons(mod.audit([obs], [attempt], AS_OF)))
        obs, attempt = pair(None, missingness_reason="UNESTIMABLE")
        report = mod.audit([obs], [attempt], AS_OF)
        self.assertIn("missing_measurement", reasons(report))
        self.assertNotIn("missing_value_without_typed_missingness", reasons(report))
        obs["missingness_reason"] = None
        self.assertIn("missing_value_without_typed_missingness", reasons(mod.audit([obs], [attempt], AS_OF)))

    def test_invalid_rows_and_malformed_fields_retained(self):
        obs, attempt = pair()
        del obs["currency"]
        broken = {"attempt_id": [], "observation_id": [], "status": [], "metric": [],
                  "observation_type": [], "missingness_reason": [], "value": {}}
        report = mod.audit([None, 4, obs, broken], [None, attempt, broken], AS_OF)
        self.assertEqual(report["populations"]["observations"]["rows"], 4)
        self.assertEqual(report["populations"]["measurement_partition"]["invalid_row"], 2)
        self.assertEqual(reasons(report)["invalid_row_type"], 2)
        self.assertIn("missing_schema_columns", reasons(report))
        json.dumps(report, allow_nan=False)

    def test_anchor_and_roles_no_horizon_inference_or_permission(self):
        obs, attempt = pair(period_end="2026-12-31", permission_granted=True, rights_class="LICENSED")
        report = mod.audit([obs], [attempt], AS_OF)
        self.assertNotIn("missing_period_mapping:period_end", reasons(report))
        self.assertNotIn("missing_period_mapping:fiscal_year", reasons(report))
        self.assertIn("rights_label_unverified", reasons(report))
        self.assertTrue(all(v is False for v in report["financial_authority"].values()))
        obs, attempt = pair(5, observation_type="covering_analyst_count")
        report = mod.audit([obs], [attempt], AS_OF)
        self.assertEqual(report["populations"]["central_expectation_rows_with_declared_capture_support"], 0)
        self.assertEqual(report["populations"]["observation_role_partition"], {"coverage_count": 1})
        self.assertIn("missing_period_mapping:period_end", reasons(report))

    def test_empty_has_no_readiness_or_percentages(self):
        report = mod.audit([], [], AS_OF)
        self.assertEqual(report["readiness"], "EMPTY_INPUT")
        self.assertEqual(report["populations"]["declared_capture_comparison_partition"]["structurally_eligible_rows"], 0)
        self.assertEqual(report["clock_bounds"], {})
        self.assertNotIn("%", json.dumps(report))
        self.assertFalse(report["predictive_validation"])

    def test_count_mismatch_and_nondata_attempt(self):
        obs, attempt = pair()
        attempt["observation_count"] = 0
        self.assertIn("observation_count_mismatch", reasons(mod.audit([obs], [attempt], AS_OF), "attempts"))
        for count in (True, -1, 1.2, float("inf"), None):
            attempt["observation_count"] = count
            self.assertIn("invalid_observation_count", reasons(mod.audit([obs], [attempt], AS_OF), "attempts"))
        attempt.update(observation_count=1, status="http_429")
        self.assertIn("observations_from_nondata_attempt", reasons(mod.audit([obs], [attempt], AS_OF)))

    def test_lineage_exact_owner_semantics_and_rollover(self):
        first, attempt1 = pair(period_end="2026-12-31")
        second, attempt2 = pair(2, collection_session_id="session-b", period_end="2026-12-31",
                                correction_state="supersedes", supersedes_observation_id=first["observation_id"],
                                provider_observed_at="2026-10-03T11:00:01Z",
                                system_observed_at="2026-10-03T11:00:02Z")
        attempt2.update(attempted_at="2026-10-03T11:00:00Z", completed_at="2026-10-03T11:00:03Z")
        report = mod.audit([first, second], [attempt1, attempt2], AS_OF)
        self.assertNotIn("unknown_correction_state", reasons(report))
        self.assertNotIn("supersedes_later_knowledge", reasons(report))
        self.assertEqual(report["lineage"]["counts"]["declared_supersedes_references"], 1)
        second["period_end"] = "2027-03-31"
        report = mod.audit([first, second], [attempt1, attempt2], AS_OF)
        self.assertIn("supersedes_fiscal_rollover", reasons(report))
        self.assertEqual(report["lineage"]["counts"]["declared_period_end_rollover_pairs"], 1)
        second["correction_state"] = "original"
        self.assertIn("correction_reference_inconsistent", reasons(mod.audit([first, second], [attempt1, attempt2], AS_OF)))
        second["supersedes_observation_id"] = "missing-id"
        self.assertIn("orphan_supersedes_reference", reasons(mod.audit([first, second], [attempt1, attempt2], AS_OF)))

    def test_samples_bounded_and_deterministic(self):
        observations, attempts = zip(*(pair(collection_session_id="s-" + str(i)) for i in range(12)))
        report = mod.audit(observations, attempts, AS_OF)
        self.assertTrue(all(len(r["samples"]) <= 5 for r in report["reasons"]))
        self.assertEqual(report, mod.audit(list(reversed(observations)), list(reversed(attempts)), AS_OF))

    def test_atomic_input_modes_fail_before_io(self):
        kwargs_cases = ({}, {"observations_path": "one"}, {"repo": "repo"},
                        {"repo": "repo", "revision": "main", "git_observations_path": "a", "git_attempts_path": "b"},
                        {"observations_path": "a", "attempts_path": "b", "repo": "repo"})
        for kwargs in kwargs_cases:
            with patch.object(mod, "_git") as git:
                with self.assertRaises(ValueError):
                    mod.load_inputs(**kwargs)
                git.assert_not_called()
        for path in ("../a", "/a", "a:b", "a//b", "a/./b", "a\\b", ""):
            with self.assertRaises(ValueError):
                mod._git_path(path)

    def test_git_exact_revision_pair_and_actual_byte_hashes(self):
        # In-memory parquet avoids filesystem or Git mutations in the tests.
        import pandas as pd
        obs, attempt = pair()
        encoded = {}
        for name, rows in (("obs.parquet", [obs]), ("attempts.parquet", [attempt])):
            buffer = io.BytesIO()
            pd.DataFrame(rows).to_parquet(buffer, index=False)
            encoded[name] = buffer.getvalue()
        revision = "1" * 40
        calls = []
        def fake_git(repo, *args):
            calls.append((repo, args))
            if args == ("rev-parse", "--verify", revision + "^{commit}"):
                return (revision + "\n").encode()
            path = args[-1].split(":", 1)[1]
            if args[0] == "cat-file":
                return b"blob\n"
            if args[0] == "show":
                return encoded[path]
            return (("2" if path == "obs.parquet" else "3") * 40 + "\n").encode()
        with patch.object(mod, "_git", side_effect=fake_git):
            observations, attempts, provenance = mod.load_inputs(repo="repo", revision=revision,
                git_observations_path="obs.parquet", git_attempts_path="attempts.parquet")
        self.assertEqual(provenance["source_revision"], revision)
        self.assertEqual(provenance["inputs"]["observations"]["sha256"], mod.hashlib.sha256(encoded["obs.parquet"]).hexdigest())
        self.assertEqual(len(observations), 1)
        self.assertEqual(len(attempts), 1)
        self.assertTrue(all(args[0] in {"rev-parse", "cat-file", "show"} for _, args in calls))
        with patch.object(mod.subprocess, "run") as run:
            run.return_value.stdout = b"ok"
            mod._git("repo", "show", revision + ":obs.parquet")
            self.assertEqual(run.call_args.kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")
            self.assertNotIn("shell", run.call_args.kwargs)

    def test_latest_retained_lineage_and_unchanged_consistency(self):
        observations = []
        attempts = []
        for i, value in enumerate((1, 2, 3)):
            obs, attempt = pair(value, collection_session_id="session-" + str(i),
                                period_end="2026-12-31",
                                provider_observed_at="2026-10-03T10:" + str(i).zfill(2) + ":01Z",
                                system_observed_at="2026-10-03T10:" + str(i).zfill(2) + ":02Z")
            attempt.update(attempted_at="2026-10-03T10:" + str(i).zfill(2) + ":00Z",
                           completed_at="2026-10-03T10:" + str(i).zfill(2) + ":03Z")
            if i:
                obs.update(correction_state="supersedes", supersedes_observation_id=observations[-1]["observation_id"])
            observations.append(obs)
            attempts.append(attempt)
        report = mod.audit(observations, attempts, AS_OF)
        self.assertNotIn("supersedes_not_latest_retained_present", reasons(report))
        observations[2]["supersedes_observation_id"] = observations[0]["observation_id"]
        self.assertIn("supersedes_not_latest_retained_present", reasons(mod.audit(observations, attempts, AS_OF)))
        observations[2].update(correction_state="unchanged", supersedes_observation_id=None)
        self.assertIn("unchanged_contradicts_retained_predecessor", reasons(mod.audit(observations, attempts, AS_OF)))
        observations[2]["value"] = observations[1]["value"]
        self.assertNotIn("unchanged_contradicts_retained_predecessor", reasons(mod.audit(observations, attempts, AS_OF)))
        observations[2]["period_end"] = "2027-03-31"
        self.assertIn("unchanged_contradicts_retained_predecessor", reasons(mod.audit(observations, attempts, AS_OF)))

    def test_companion_integrity_and_temporal_failure_propagates(self):
        for changes in ({"observation_id": "forged-id"},
                        {"system_observed_at": "2026-10-03T13:00:00Z"},
                        {"provider_payload_hash": "b" * 64},
                        {"missingness_reason": "UNESTIMABLE"}):
            obs, attempt = pair()
            count, _ = pair(5, observation_type="covering_analyst_count")
            count.update(changes)
            attempt["observation_count"] = 2
            report = mod.audit([obs, count], [attempt], AS_OF)
            self.assertIn("unverifiable_covering_count_companion", reasons(report))
            self.assertEqual(report["populations"]["central_expectation_rows_with_declared_capture_support"], 0)

    def test_tied_clock_cycle_has_no_declared_capture_qualification(self):
        first, attempt1 = pair(collection_session_id="one")
        second, attempt2 = pair(2, collection_session_id="two")
        first.update(correction_state="supersedes", supersedes_observation_id=second["observation_id"])
        second.update(correction_state="supersedes", supersedes_observation_id=first["observation_id"])
        count1, _ = pair(5, collection_session_id="one", observation_type="covering_analyst_count")
        count2, _ = pair(5, collection_session_id="two", observation_type="covering_analyst_count")
        attempt1["observation_count"] = attempt2["observation_count"] = 2
        report = mod.audit([first, second, count1, count2], [attempt1, attempt2], AS_OF)
        self.assertEqual(reasons(report)["retained_lineage_order_ambiguous"], 4)
        self.assertEqual(report["populations"]["declared_capture_comparison_partition"]["structurally_eligible_rows"], 0)

    def test_companion_count_source_shape_zero_null_and_positive(self):
        for coverage in (0, None, -1, True, float("nan"), 1.5):
            obs, attempt = pair(0)
            count, _ = pair(coverage, observation_type="covering_analyst_count",
                            missingness_reason="UNESTIMABLE" if coverage is None else None)
            attempt["observation_count"] = 2
            report = mod.audit([obs, count], [attempt], AS_OF)
            self.assertEqual(report["populations"]["central_expectation_rows_with_declared_capture_support"], 0)
            if coverage is None or isinstance(coverage, (int, float)) and not isinstance(coverage, bool) and coverage <= 0:
                self.assertIn("present_measurement_in_nonestimable_group", reasons(report))
        obs, attempt = pair(0)
        count, _ = pair(5, observation_type="covering_analyst_count")
        attempt["observation_count"] = 2
        report = mod.audit([obs, count], [attempt], AS_OF)
        self.assertEqual(report["populations"]["central_expectation_rows_with_declared_capture_support"], 1)
        self.assertEqual(report["populations"]["measurement_partition"], {"valid": 2})
        # Legitimate typed absent estimates remain absent without inventing zero.
        obs["value"] = None
        obs["missingness_reason"] = "UNESTIMABLE"
        count["value"] = 0
        report = mod.audit([obs, count], [attempt], AS_OF)
        self.assertNotIn("present_measurement_in_nonestimable_group", reasons(report))
        self.assertEqual(report["populations"]["measurement_partition"], {"missing": 1, "valid": 1})

    def test_missing_or_ambiguous_companion_is_explicitly_unverified(self):
        obs, attempt = pair()
        report = mod.audit([obs], [attempt], AS_OF)
        self.assertIn("missing_covering_count_companion", reasons(report))
        self.assertEqual(report["populations"]["central_expectation_rows_with_declared_capture_support"], 0)
        count, _ = pair(5, observation_type="covering_analyst_count")
        attempt["observation_count"] = 2
        report = mod.audit([obs, count, dict(count)], [attempt], AS_OF)
        self.assertIn("ambiguous_covering_count_companion", reasons(report))
        self.assertEqual(report["populations"]["central_expectation_rows_with_declared_capture_support"], 0)

    def test_known_future_effective_time_is_not_future_knowledge(self):
        obs, attempt = pair(source_effective_at="2026-12-31T00:00:00Z",
                            source_published_at="2026-10-03T09:00:00Z")
        count, _ = pair(5, observation_type="covering_analyst_count")
        attempt["observation_count"] = 2
        report = mod.audit([obs, count], [attempt], AS_OF)
        self.assertNotIn("clock_after_as_of:source_effective_at", reasons(report))
        self.assertEqual(report["populations"]["central_expectation_rows_with_declared_capture_support"], 1)
        self.assertEqual(report["clock_bounds"]["observations.source_effective_at"]["max"], "2026-12-31T00:00:00Z")
        obs["source_effective_at"] = "2026-12-31T00:00:00"
        self.assertIn("invalid_or_missing_clock:source_effective_at", reasons(mod.audit([obs, count], [attempt], AS_OF)))

    def test_parquet_null_is_distinct_from_ieee_nan(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        obs, attempt = pair(None, missingness_reason="UNESTIMABLE")
        other, _ = pair(float("nan"), collection_session_id="session-b")
        table = pa.Table.from_pylist([obs, other])
        # Explicit Arrow construction preserves a valid IEEE NaN separately
        # from the null bitmap, unlike default pandas numeric conversion.
        field = table.schema.get_field_index("value")
        table = table.set_column(field, "value", pa.array([None, float("nan")], type=pa.float64(), from_pandas=False))
        buffer = io.BytesIO()
        pq.write_table(table, buffer)
        import pandas as pd
        rows = pd.read_parquet(io.BytesIO(buffer.getvalue()), dtype_backend="pyarrow").to_dict("records")
        self.assertIsNone(rows[0]["value"])
        self.assertEqual(mod._measurement(rows[1]["value"]), "invalid")
        report = mod.audit(rows, [attempt], AS_OF)
        self.assertEqual(report["populations"]["measurement_partition"], {"invalid": 1, "missing": 1})

    def test_cli_stdout_only(self):
        obs, attempt = pair()
        output = io.StringIO()
        with patch.object(mod, "load_inputs", return_value=([obs], [attempt], {"mode": "test"})), contextlib.redirect_stdout(output):
            self.assertEqual(mod.main(["--as-of", AS_OF, "--observations-path", "a", "--attempts-path", "b"]), 0)
        self.assertEqual(json.loads(output.getvalue())["scope"], "structural_on_declared_clocks_only")


class R1OwnerReceiptTests(unittest.TestCase):
    HITS = [
        {
            "line": 363,
            "text": (
                '"rights_class": "UNKNOWN",  # R1-OWNER-REFUSAL line 363: '
                "no rights class is assigned"
            ),
        }
    ]

    @staticmethod
    def raw_gaps():
        return {
            "G1": {
                "status": "OPEN",
                "value": {
                    "issuer_id_resolved": 779,
                    "universe_names": 1503,
                    "unresolved": 724,
                    "cik_map_universe_tickers": 1499,
                },
            },
            "G2": {
                "status": "OPEN",
                "value": {
                    "alias_rows_dated_le_cutoff": 2,
                    "undated_alias_rows": 777,
                    "prospective_from_undated_rows": 0,
                },
            },
            "G3": {
                "status": "OPEN",
                "value": {
                    "spine_columns_present": [],
                    "observation_currency_nonnull": 0,
                    "observation_fiscal_year_nonnull": 0,
                    "observation_basis_nonnull": 0,
                },
            },
            "G4": {
                "status": "OPEN",
                "value": {"literal": "UNKNOWN", "line": 363},
            },
            "G5": {
                "status": "OPEN",
                "value": {
                    "source_effective_at_nonnull": 0,
                    "source_published_at_nonnull": 0,
                    "observation_rows": 517384,
                },
            },
        }

    @classmethod
    def receipts(cls):
        raw = cls.raw_gaps()
        out = {}
        for key in ("G1", "G2", "G3", "G4", "G5"):
            counts = {
                k: raw[key]["value"][k] for k in r1.STABLE_COUNT_KEYS[key]
            }
            entry = {
                "owner_ws": "ALPHA-INTELLIGENCE-INTEGRATION",
                "receipt_form": r1.EXPECTED_RECEIPT_FORM[key],
                "cutoff": r1.CUTOFF,
                "counts": counts,
            }
            if key == "G4":
                entry["refusal"] = {
                    "path": "collectors/equity_revisions.py",
                    "line": 363,
                    "same_line_marker": "R1-OWNER-REFUSAL",
                }
            out[key] = entry
        return out

    @staticmethod
    def ws():
        return {
            "status": "active",
            "owns_paths": [
                "data/reference/",
                "data/symbol_directory/",
                "data/openfigi/",
                "data/revisions/expectation_observations.parquet",
                "data/revisions/expectation_attempts.parquet",
                "collectors/equity_revisions.py",
            ],
        }

    @classmethod
    def evaluate_all(cls, raw, rec, ws_fm, hits):
        return {
            g: r1.evaluate_owner_receipt(
                g,
                raw[g],
                rec.get(g),
                ws_fm,
                hits if g == "G4" else None,
            )["status"]
            for g in raw
        }

    def test_t1_all_valid_degraded_accepted(self):
        raw = self.raw_gaps()
        rec = self.receipts()
        ws_fm = self.ws()
        statuses = self.evaluate_all(raw, rec, ws_fm, self.HITS)
        for g in statuses:
            self.assertEqual(statuses[g], "DEGRADED_ACCEPTED")
        self.assertEqual(r1.compute_r1_status(statuses, []), ("COMPLETE_DEGRADED", []))

    def test_t2_g1_count_mismatch(self):
        raw = self.raw_gaps()
        rec = self.receipts()
        rec["G1"]["counts"]["unresolved"] = 723
        result = r1.evaluate_owner_receipt("G1", raw["G1"], rec["G1"], self.ws())
        self.assertEqual(result["status"], "OPEN")
        self.assertTrue(
            any("unresolved" in m for m in result["owner_receipt"]["mismatches"])
        )
        statuses = self.evaluate_all(raw, rec, self.ws(), self.HITS)
        self.assertEqual(r1.compute_r1_status(statuses, [])[0], "INCOMPLETE")

    def test_t3_missing_openfigi_ownership(self):
        raw = self.raw_gaps()
        rec = self.receipts()
        ws_fm = dict(self.ws())
        ws_fm["owns_paths"] = [p for p in ws_fm["owns_paths"] if p != "data/openfigi/"]
        result = r1.evaluate_owner_receipt("G1", raw["G1"], rec["G1"], ws_fm)
        self.assertEqual(result["status"], "OPEN")
        self.assertEqual(result["owner_receipt"]["uncovered_paths"], ["data/openfigi/"])
        statuses = self.evaluate_all(raw, rec, ws_fm, self.HITS)
        for g in ("G2", "G3", "G4", "G5"):
            self.assertEqual(statuses[g], "DEGRADED_ACCEPTED")

    def test_t4_g5_wrong_receipt_form(self):
        raw = self.raw_gaps()
        rec = self.receipts()
        rec["G5"]["receipt_form"] = "DEGRADED_LABELED_ABSENCE"
        result = r1.evaluate_owner_receipt("G5", raw["G5"], rec["G5"], self.ws())
        self.assertEqual(result["status"], "OPEN")

    def test_t5_g3_receipt_removed(self):
        raw = self.raw_gaps()
        rec = self.receipts()
        del rec["G3"]
        result = r1.evaluate_owner_receipt("G3", raw["G3"], None, self.ws())
        self.assertEqual(result["status"], "OPEN")
        self.assertFalse(result["owner_receipt"]["present"])
        statuses = self.evaluate_all(raw, rec, self.ws(), self.HITS)
        self.assertEqual(r1.compute_r1_status(statuses, [])[0], "INCOMPLETE")

    def test_t6_g4_marker_and_hit_count(self):
        raw = self.raw_gaps()
        rec = self.receipts()
        bad_hits = [{"line": 363, "text": '"rights_class": "UNKNOWN",'}]
        result = r1.evaluate_owner_receipt("G4", raw["G4"], rec["G4"], self.ws(), bad_hits)
        self.assertEqual(result["status"], "OPEN")
        two_hits = self.HITS + [{"line": 364, "text": "other"}]
        result2 = r1.evaluate_owner_receipt(
            "G4", raw["G4"], rec["G4"], self.ws(), two_hits
        )
        self.assertEqual(result2["status"], "OPEN")

    def test_t7_g2_closed_without_receipt(self):
        raw = self.raw_gaps()
        raw["G2"]["status"] = "CLOSED"
        result = r1.evaluate_owner_receipt("G2", raw["G2"], None, self.ws())
        self.assertEqual(result["status"], "CLOSED")
        all_closed = {g: "CLOSED" for g in raw}
        self.assertEqual(r1.compute_r1_status(all_closed, []), ("COMPLETE", []))

    def test_t8_g3_unmeasurable_not_upgraded(self):
        raw = self.raw_gaps()
        raw["G3"]["status"] = "UNMEASURABLE"
        rec = self.receipts()
        result = r1.evaluate_owner_receipt("G3", raw["G3"], rec["G3"], self.ws())
        self.assertEqual(result["status"], "UNMEASURABLE")
        statuses = self.evaluate_all(raw, rec, self.ws(), self.HITS)
        self.assertEqual(r1.compute_r1_status(statuses, [])[0], "INCOMPLETE")

    def test_t9_owns_path_prefix(self):
        self.assertTrue(
            r1.owns_path(["data/reference/"], "data/reference/x.parquet")
        )
        self.assertFalse(
            r1.owns_path(["data/reference"], "data/reference/x.parquet")
        )
        self.assertFalse(r1.owns_path(["data/ref/"], "data/reference/x.parquet"))
        self.assertFalse(r1.owns_path(None, "a"))

    def test_t10_growing_counts_ignored(self):
        raw = self.raw_gaps()
        raw["G5"]["value"]["observation_rows"] = 999999
        raw["G1"]["value"]["cik_map_universe_tickers"] = 1
        statuses = self.evaluate_all(raw, self.receipts(), self.ws(), self.HITS)
        for g in statuses:
            self.assertEqual(statuses[g], "DEGRADED_ACCEPTED")

    def test_t11_g2_cutoff_mismatch(self):
        raw = self.raw_gaps()
        rec = self.receipts()
        rec["G2"]["cutoff"] = "2026-10-04T00:00:00Z"
        result = r1.evaluate_owner_receipt("G2", raw["G2"], rec["G2"], self.ws())
        self.assertEqual(result["status"], "OPEN")

    def test_t12_ws_parked(self):
        raw = self.raw_gaps()
        rec = self.receipts()
        ws_fm = {"status": "parked", "owns_paths": self.ws()["owns_paths"]}
        statuses = self.evaluate_all(raw, rec, ws_fm, self.HITS)
        for g in statuses:
            self.assertEqual(statuses[g], "OPEN")

    def test_t13_parse_front_matter(self):
        self.assertEqual(
            r1.parse_front_matter("---\nkey: X\nstatus: active\n---\nbody"),
            {"key": "X", "status": "active"},
        )
        self.assertEqual(r1.parse_front_matter("no front matter"), {})
        self.assertEqual(r1.parse_front_matter("---\n: : bad\n---\n"), {})

    def test_t14_rights_literal_of(self):
        self.assertEqual(
            r1.rights_literal_of('"rights_class": "UNKNOWN",  # note "LICENSED"'),
            "UNKNOWN",
        )
        self.assertEqual(
            r1.rights_literal_of('"rights_class": "LICENSED",  # was UNKNOWN'),
            "LICENSED",
        )
        self.assertIsNone(r1.rights_literal_of("x = 1"))

    def test_t15_headline_forces_incomplete(self):
        self.assertEqual(
            r1.compute_r1_status({"G1": "DEGRADED_ACCEPTED"}, ["universe mismatch"])[0],
            "INCOMPLETE",
        )

    def test_t16_module_constants(self):
        self.assertEqual(r1.SCHEMA_VERSION, "r1-readiness-probe.v2")
        keys = {"G1", "G2", "G3", "G4", "G5"}
        self.assertEqual(set(r1.STABLE_COUNT_KEYS), keys)
        self.assertEqual(set(r1.EXPECTED_RECEIPT_FORM), keys)
        self.assertEqual(set(r1.REQUIRED_OWNER_PATHS), keys)


if __name__ == "__main__":
    unittest.main()
