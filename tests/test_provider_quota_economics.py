"""Executable intent cases for quota economics; all provider figures are synthetic."""
from __future__ import annotations
import copy
import dataclasses as dc
import json
from pathlib import Path
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone

from engine.provider_quota_economics import (
    INPUT_SCHEMA, Option, Policy, QuotaEconomicsError, Resource, Task,
    native_usage_amount, preview, preview_document,
)

NOW = datetime(2026, 9, 13, 16, tzinfo=timezone.utc)

def stamp(hours=0):
    return (NOW + timedelta(hours=hours)).isoformat()


def resource(key, applies, **changes):
    row = Resource(key, "synthetic-generation", tuple(applies), "credits", "fixed", "weekly",
                   100, 99, stamp(), stamp(1), "provider_reported", stamp(9), 604800)
    return dc.replace(row, **changes)


def option(key, resources, **changes):
    costs = {r.resource_id: {"amount": 1, "unit": r.unit} for r in resources if key in r.applies_to}
    row = Option(key, key, key, key, costs, 3600, 0, True, True, True, 0)
    return dc.replace(row, **changes)


def task(aliases, **changes):
    row = Task("build", "READY", True, 100, ({"tier_id": "qualified", "model_aliases": list(aliases)},))
    return dc.replace(row, **changes)


def scenario():
    rows = [resource("grok-week", ["grok"]),
            resource("cursor-month", ["cursor"], horizon="monthly", reset_at=stamp(24 * 28)),
            resource("host-slots", ["grok", "cursor"], unit="concurrent_sessions",
                     window_type="instant", horizon="concurrency", limit=7, remaining=7,
                     reset_at=None, window_seconds=None)]
    opts = [option("grok", rows), option("cursor", rows)]
    policy = Policy(7, False, ({"preferred": "grok", "fallback": "cursor", "task_kinds": ["build"]},))
    return rows, opts, task(["grok", "cursor"]), policy


class QuotaEconomicsTests(unittest.TestCase):
    def run_preview(self, rows=None, opts=None, work=None, policy=None):
        base = scenario()
        return preview(rows if rows is not None else base[0], opts if opts is not None else base[1],
                       work if work is not None else base[2], policy if policy is not None else base[3], as_of=stamp())

    def test_grok_before_cursor_even_if_cursor_expiring_sooner(self):
        rows, opts, work, policy = scenario()
        rows[1] = dc.replace(rows[1], reset_at=stamp(2))
        result = self.run_preview(rows, opts, work, policy)
        self.assertEqual(result["suggested_option"], "grok")
        self.assertFalse(result["live_admission"])
        self.assertEqual(result["authority"], "NONE_PREVIEW_ONLY")

    def test_cursor_fallback_only_after_grok_not_eligible(self):
        rows, opts, work, policy = scenario()
        rows[0] = dc.replace(rows[0], remaining=0)
        self.assertEqual(self.run_preview(rows, opts, work, policy)["suggested_option"], "cursor")

    def test_suitability_beats_quota_pressure_and_provider_precedence(self):
        rows, opts, work, policy = scenario()
        work = dc.replace(work, suitability_tiers=({"tier_id": "best", "model_aliases": ["cursor"]},
                                                   {"tier_id": "fallback", "model_aliases": ["grok"]}))
        self.assertEqual(self.run_preview(rows, opts, work, policy)["suggested_option"], "cursor")

    def test_independence_is_not_waived_to_burn_grok(self):
        result = self.run_preview(work=task(["grok", "cursor"], excluded_families=("grok",)))
        self.assertEqual(result["suggested_option"], "cursor")

    def test_no_migration_after_start_or_unknown_effect(self):
        for state in ("STARTED", "EFFECT_UNKNOWN"):
            result = self.run_preview(work=task(["grok", "cursor"], state=state))
            self.assertIsNone(result["suggested_option"])
            self.assertEqual(result["status"], "RECONCILE_EXISTING_ATTEMPT")

    def test_no_invented_work(self):
        for change in ({"ready_jobs": 0}, {"authorized": False}, {"state": "NOT_READY"}):
            self.assertEqual(self.run_preview(work=task(["grok"], **change))["status"], "NO_AUTHORIZED_READY_WORK")

    def test_terms_harness_and_permission_are_hard_gates(self):
        rows, opts, work, policy = scenario()
        for field in ("usage_allowed", "harness_ready", "permitted"):
            changed = [dc.replace(opts[0], **{field: None}), opts[1]]
            self.assertEqual(self.run_preview(rows, changed, work, policy)["suggested_option"], "cursor")

    def test_unknown_stale_future_and_post_reset_do_not_refill(self):
        rows, opts, work, policy = scenario()
        variants = [{"remaining": None}, {"evidence": "estimated"},
                    {"observed_at": stamp(-2), "valid_until": stamp(-1)},
                    {"observed_at": stamp(.1)}, {"reset_at": stamp(-1)}]
        for change in variants:
            changed = [dc.replace(rows[0], **change), *rows[1:]]
            self.assertEqual(self.run_preview(changed, opts, work, policy)["suggested_option"], "cursor")

    def test_cash_spend_is_never_silently_enabled(self):
        rows, opts, work, policy = scenario()
        opts = [dc.replace(o, marginal_cash=1) for o in opts]
        self.assertEqual(self.run_preview(rows, opts, work, policy)["status"], "NO_ELIGIBLE_OPTION")

    def test_shared_parent_exhaustion_blocks_fable_and_opus(self):
        rows = [resource("all-models", ["fable", "opus"], remaining=0),
                resource("fable-subset", ["fable"], limit=50, remaining=40),
                resource("slots", ["fable", "opus"], unit="concurrent_sessions", window_type="instant",
                         limit=7, remaining=7, reset_at=None, window_seconds=None)]
        opts = [option(name, rows) for name in ("fable", "opus")]
        self.assertEqual(self.run_preview(rows, opts, task(["fable", "opus"]), Policy(7))["status"], "NO_ELIGIBLE_OPTION")

    def test_fable_reservation_is_a_subset_not_extra_capacity(self):
        rows = [resource("all-models", ["fable", "opus"], remaining=20, reserves={"fable": 15}),
                resource("fable-subset", ["fable"], limit=50, remaining=40),
                resource("slots", ["fable", "opus"], unit="concurrent_sessions", window_type="instant",
                         limit=7, remaining=7, reset_at=None, window_seconds=None)]
        opts = [option(name, rows) for name in ("fable", "opus")]
        result = self.run_preview(rows, opts, task(["fable", "opus"]), Policy(7))
        by_id = {r["option_id"]: r for r in result["options"]}
        self.assertEqual(by_id["opus"]["estimated_startable_jobs"], 5)
        self.assertEqual(by_id["fable"]["estimated_startable_jobs"], 7)
        parent = next(f for f in by_id["fable"]["forecasts"] if f["resource_id"] == "all-models")
        self.assertLessEqual(parent["jobs_under_declared_scenario"], 20)

    def test_rolling_window_limits_weekly_burn(self):
        rows = [resource("week", ["minimax"]),
                resource("five-hour", ["minimax"], limit=10, remaining=10, window_type="rolling",
                         horizon="five_hour", window_seconds=18000, reset_at=None, release_schedule_complete=True),
                resource("slots", ["minimax"], unit="concurrent_sessions", window_type="instant",
                         limit=2, remaining=2, reset_at=None, window_seconds=None)]
        result = self.run_preview(rows, [option("minimax", rows)], task(["minimax"]), Policy(7))
        advice = result["options"][0]
        self.assertEqual(advice["suggested_parallelism"], 2)
        forecast = advice["forecasts"][0]
        self.assertEqual(forecast["jobs_under_declared_scenario"], 18)
        self.assertEqual(forecast["unspent_under_declared_scenario"], "81")

    def test_source_percentage_is_not_tokens(self):
        from engine.provider_subscription_usage import parse_minimax_quota
        observation = parse_minimax_quota({"model_remains": [{"model_name": "MiniMax-M3",
            "current_interval_status": 1, "current_interval_remaining_percent": 90,
            "current_weekly_status": 1, "current_weekly_remaining_percent": 99}]}, observed_at=stamp())
        weekly = next(r for r in observation.quota_rows if r["horizon"] == "weekly")
        result = native_usage_amount(weekly)
        self.assertEqual(result, {"remaining": "99.0", "limit": "100", "unit": "percentage_points"})

    def test_missing_parent_cost_and_wrong_unit_are_rejected(self):
        rows, opts, work, policy = scenario()
        for costs in ({"grok-week": {"amount": 1, "unit": "credits"}},
                      {"grok-week": {"amount": 1, "unit": "tokens"}, "host-slots": {"amount": 1, "unit": "concurrent_sessions"}}):
            with self.assertRaises(QuotaEconomicsError):
                self.run_preview(rows, [dc.replace(opts[0], costs=costs), opts[1]], work, policy)

    def test_duplicate_shared_pool_is_rejected(self):
        rows, opts, work, policy = scenario()
        with self.assertRaises(QuotaEconomicsError):
            self.run_preview(rows + [rows[0]], opts, work, policy)

    def test_nonfinite_and_bool_costs_rejected(self):
        rows, opts, work, policy = scenario()
        for value in (float("nan"), float("inf"), -1, True):
            with self.assertRaises(QuotaEconomicsError):
                self.run_preview([dc.replace(rows[0], remaining=value), *rows[1:]], opts, work, policy)

    def test_input_is_not_mutated(self):
        args = scenario()
        before = copy.deepcopy(args)
        self.run_preview(*args)
        self.assertEqual(args, before)

    def test_unknown_fields_do_not_grant_authority(self):
        rows, opts, work, policy = scenario()
        doc = {"schema": INPUT_SCHEMA, "as_of": stamp(), "resources": [dc.asdict(r) for r in rows],
               "options": [dc.asdict(o) for o in opts], "task": dc.asdict(work), "policy": dc.asdict(policy)}
        doc["override_authority"] = True
        with self.assertRaises(QuotaEconomicsError):
            preview_document(doc)

    def test_real_cli_consumer(self):
        rows, opts, work, policy = scenario()
        doc = {"schema": INPUT_SCHEMA, "as_of": stamp(), "resources": [dc.asdict(r) for r in rows],
               "options": [dc.asdict(o) for o in opts], "task": dc.asdict(work), "policy": dc.asdict(policy)}
        cli = Path(__file__).resolve().parents[1] / "scripts/preview_provider_quota_economics.py"
        proc = subprocess.run([sys.executable, str(cli), "--input", "-"], input=json.dumps(doc),
                              text=True, capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["suggested_option"], "grok")
        self.assertFalse(json.loads(proc.stdout)["live_admission"])

    def test_cli_rejects_duplicate_json_keys(self):
        cli = Path(__file__).resolve().parents[1] / "scripts/preview_provider_quota_economics.py"
        proc = subprocess.run([sys.executable, str(cli), "--input", "-"], input='{"schema":1,"schema":2}',
                              text=True, capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("DUPLICATE_JSON_KEY", proc.stderr)


    def test_precedence_cycle_refused_and_transitive_order_stable(self):
        rows, opts, work, policy = scenario()
        reverse = {"preferred": "cursor", "fallback": "grok", "task_kinds": ["build"]}
        with self.assertRaises(QuotaEconomicsError):
            self.run_preview(rows, opts, work, dc.replace(policy, provider_precedence=(*policy.provider_precedence, reverse)))
        chain = ({"preferred": "grok", "fallback": "intermediate", "task_kinds": ["build"]},
                 {"preferred": "intermediate", "fallback": "cursor", "task_kinds": ["build"]})
        for edges in (chain, tuple(reversed(chain))):
            self.assertEqual(self.run_preview(rows, opts, work, dc.replace(policy, provider_precedence=edges))["suggested_option"], "grok")

    def test_provider_unlimited_or_unknown_is_not_infinite_budget(self):
        for status in ("provider_unlimited", "unknown"):
            row = {"metric": "provider_allocation", "status": status, "reported_remaining_percent": 100}
            self.assertIsNone(native_usage_amount(row)["remaining"])

    def test_explicit_exhaustion_overrides_inconsistent_positive_count(self):
        row = {"metric": "credits", "status": "exhausted", "limit": 100, "remaining": 100}
        self.assertEqual(native_usage_amount(row)["remaining"], "0")

    def test_missing_release_history_is_disclosed_not_invented(self):
        rows, opts, work, policy = scenario()
        rows[0] = dc.replace(rows[0], window_type="rolling", window_seconds=18000, reset_at=None)
        rows.append(resource("long-window", ["grok"]))
        opts[0] = option("grok", rows)
        result = self.run_preview(rows, opts, work, policy)
        forecast = next(r for r in result["options"] if r["option_id"] == "grok")["forecasts"][0]
        self.assertIn("UNKNOWN_PRIOR_RELEASES_CONSERVATIVELY_OMITTED", forecast["notes"])

    def test_held_unobserved_debits_prevent_double_spending(self):
        rows, opts, work, policy = scenario()
        rows[0] = dc.replace(rows[0], unobserved_holds=99)
        self.assertEqual(self.run_preview(rows, opts, work, policy)["suggested_option"], "cursor")

    def test_burst_limited_by_existing_capacity_not_marketing(self):
        rows, opts, work, policy = scenario()
        rows[2] = dc.replace(rows[2], remaining=1)
        result = self.run_preview(rows, opts, work, dc.replace(policy, burst_cap=128))
        self.assertTrue(all(row["suggested_parallelism"] == 1 for row in result["options"]))

    def test_deadline_prevents_choosing_unfinishable_work(self):
        self.assertEqual(self.run_preview(work=task(["grok", "cursor"], deadline_at=stamp(.5)))["status"], "NO_ELIGIBLE_OPTION")

    def test_normalized_native_depletion_prefers_expiring_useful_capacity(self):
        rows, opts, work, policy = scenario()
        rows[1] = dc.replace(rows[1], reset_at=stamp(2))
        opts[0] = dc.replace(opts[0], useful_jobs_per_hour=7)
        result = self.run_preview(rows, opts, work, Policy(7))
        self.assertEqual(result["suggested_option"], "cursor")


if __name__ == "__main__":
    unittest.main()
