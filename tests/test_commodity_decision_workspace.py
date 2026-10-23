"""Decision-workspace boundary tests. No collectors, production writes or model runs."""
from copy import deepcopy
from datetime import date
import ast
from hashlib import sha256
import importlib.util
import json
import logging
import re
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from engine.commodity_decision_workspace import build_workspace, validate_condition, number
from engine.commodity_workspace_adapter import read_publication, workspace_from_publications


def snapshot():
    return {"asof": "2026-10-16", "index": {"chg_1m_pct": -2.7},
            "breadth": {"n_members": 6, "n_up_trend": 6}, "members": [
        {"name": k, "class": f, "chg_1m_pct": v, "velocity": {"r5": 0, "r20": v, "r60": -2, "r252": 3},
         "ts_trend": "up", "momentum_state": "neutral"}
        for k, f, v in [("oil", "energy", 4), ("gold", "precious", -4.9), ("silver", "precious", -14.5),
                        ("platinum", "precious", -9), ("palladium", "precious", -15.2), ("copper", "industrial", -2.4)]]}


def chain(confirmed=False):
    return {"chain": "real_rate_peak_gold_rerate", "rev": 1, "state": "arming", "title": {"en": "Gold", "zh": "黄金"},
            "episode_id": "gold@r1:2026-10-01", "falsifier_fired": None,
            "nodes": [{"id": "real_rate_rolldown", "resolved": True, "confirmed": confirmed,
                       "receipts": [{"series": "DFII10", "metric": "ret_bp", "window": 22, "value": 33,
                                     "op": "lt", "threshold": -12, "passed": False}]}],
            "hops": [{"id": "a->b", "from": "a", "to": "b", "confirmed": True, "asof": "2026-10-03", "lag_d": [0,180]}]}


def condition(w):
    return {"schema": "mmx.commodities.research_condition.v1", "asset": "oil", "metric": "return_pct", "unit": "%",
            "window_sessions": 20, "operator": "gte", "threshold": 0, "expires_on": "2026-11-01",
            "snapshot_fingerprint": w["fingerprint"], "hypothesis": "supply"}


class WorkspaceBoundaries(unittest.TestCase):
    def test_missing_values_do_not_become_zero_and_real_zero_survives(self):
        for value in [None, True, False, "0", float("nan"), float("inf")]:
            self.assertIsNone(number(value))
        self.assertEqual(number(0), 0)
        self.assertEqual(number(-2.5), -2.5)
        w = build_workspace(snapshot())
        self.assertEqual(w["assets"][0]["returns"]["5"], 0)
        json.dumps(w, allow_nan=False)

    def test_no_blanket_metals_headline_from_partial_or_undated_coverage(self):
        s = snapshot()
        roster = configured_roster_fixture()
        self.assertEqual(build_workspace(s, expected_members=roster)["headline"]["en"], "Oil holds. Metals retreat.")
        s["members"].pop()
        self.assertNotIn("Metals retreat", build_workspace(s, expected_members=roster)["headline"]["en"])
        self.assertIsNone(build_workspace(s)["breadth"]["n"])
        s = snapshot(); s["asof"] = None
        self.assertEqual(build_workspace(s)["headline"]["en"], "Read each commodity")

    def test_source_dates_are_not_availability_clocks(self):
        for stamp, expected in [("2026-10-16", "available"), ("2020-01-01", "earlier_context"),
                                ("2026-10-17", "newer_than_snapshot"), (None, "undated")]:
            w = build_workspace(snapshot(), transmission={"asof": stamp})
            receipt = w["sources"]["rates"]
            self.assertEqual(receipt["state"], expected)
            self.assertFalse(receipt["point_in_time_verified"])
            self.assertIsNone(receipt["available_at"])

    def test_recorded_hops_do_not_confirm_current_checks(self):
        w = build_workspace(snapshot(), chain_state={"asof": "2026-10-16", "chains": [chain(False)]})
        c = w["chains"][0]
        self.assertEqual(c["recorded_sequence_status"], "dated_episode_record")
        self.assertNotEqual(c["applicability"], "current_checks_met")
        self.assertEqual(c["current_checks_met"], 0)
        self.assertFalse(c["causal_timing_verified"])
        self.assertFalse(c["tradable_signal"])

    def test_current_checks_and_episode_timing_remain_separate(self):
        c = chain(True); c["hops"][0]["asof"] = "2026-10-18"
        w = build_workspace(snapshot(), chain_state={"asof": "2026-10-16", "chains": [c]})
        self.assertEqual(w["chains"][0]["applicability"], "current_checks_met")
        self.assertEqual(w["chains"][0]["recorded_sequence_status"], "incomplete_or_undated")
        w = build_workspace(snapshot(), chain_state={"asof": "2026-10-17", "chains": [c]})
        self.assertEqual(w["chains"][0]["applicability"], "unavailable")

    def test_rate_disagreement_is_preserved_without_averaging(self):
        tx = {"asof": "2026-10-16", "state": {"rates": {"real_10y_chg_22d_bp": 20}}}
        c = chain(True)
        w = build_workspace(snapshot(), transmission=tx, chain_state={"asof": "2026-10-16", "chains": [c]})
        self.assertEqual(w["chains"][0]["conflicts"][0]["rates_value"], 20)
        self.assertEqual(w["chains"][0]["conflicts"][0]["chain_value"], 33)
        self.assertNotEqual(w["chains"][0]["applicability"], "current_checks_met")
        tx["asof"] = "2026-10-15"
        self.assertEqual(build_workspace(snapshot(), transmission=tx, chain_state={"asof": "2026-10-16", "chains": [c]})["chains"][0]["conflicts"], [])

    def test_disputed_rate_values_never_supply_an_agreement_narrative(self):
        for owner, other in [(1, -1), (-1, 1), (1, 2), (-1, -2), (0, 1), (0, -1)]:
            with self.subTest(owner=owner, other=other):
                c = chain(True)
                c["nodes"][0]["receipts"][0]["value"] = owner
                tx = {"asof": "2026-10-16", "state": {"rates": {"real_10y_chg_22d_bp": other}}}
                w = build_workspace(snapshot(), transmission=tx, chain_state={"asof": "2026-10-16", "chains": [c]})
                gold = next(a for a in w["assets"] if a["id"] == "gold")
                self.assertEqual(gold["read"]["headline"]["en"], "Weaker gold. Rate readings differ.")
                self.assertIn("chains", gold["read"]["source_ids"])
                self.assertNotEqual(w["chains"][0]["applicability"], "current_checks_met")
                self.assertEqual(w["chains"][0]["conflicts"][0]["chain_value"], owner)
                self.assertEqual(w["chains"][0]["conflicts"][0]["rates_value"], other)
        for value in [None, float("nan"), float("inf")]:
            c = chain(); c["nodes"][0]["receipts"][0]["value"] = value
            self.assertEqual(build_workspace(snapshot(), transmission=tx, chain_state={"asof": "2026-10-16", "chains": [c]})["chains"][0]["conflicts"], [])
        c = chain(); c["nodes"][0]["receipts"][0]["window"] = 63
        self.assertEqual(build_workspace(snapshot(), transmission=tx, chain_state={"asof": "2026-10-16", "chains": [c]})["chains"][0]["conflicts"], [])

    def test_fx_future_clock_or_missing_method_cannot_qualify_statistics(self):
        fx = {"asof": "2026-10-16", "transmission": {"as_of": "2026-10-18", "usd_dir": "strengthening",
              "assets": {"gold": {"corr_fast": -.4, "corr_slow": -.5, "coverage": {"fast": 20, "slow": 60}}},
              "method": {"estimator": "pearson_return_correlation", "sampling": "aligned_daily_returns",
                         "pair_orientation": "usd_strength_vs_asset", "window_fast": 20, "window_slow": 60, "revision": "fixture-v1"}}}
        self.assertEqual(build_workspace(snapshot(), fx=fx)["fx"]["rows"], [])
        self.assertIsNone(build_workspace(snapshot(), fx=fx)["fx"]["direction"])
        fx["transmission"]["as_of"] = "2026-10-16"
        self.assertEqual(len(build_workspace(snapshot(), fx=fx)["fx"]["rows"]), 1)
        fx["transmission"]["method"].pop("sampling")
        self.assertEqual(build_workspace(snapshot(), fx=fx)["fx"]["rows"], [])
        self.assertEqual(build_workspace(snapshot(), fx=fx)["fx"]["direction"], "strengthening")

    def test_fx_direction_respects_its_optional_observation_clock(self):
        from jinja2 import Environment, FileSystemLoader, StrictUndefined
        root = Path(__file__).resolve().parents[1]
        env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=True, undefined=StrictUndefined)
        template = env.from_string('{% macro t(en,zh) %}{{ en }}{% endmacro %}{% include "_commodity_decision_workspace.html.j2" %}')
        absent = object()
        for nested, parent, expected, state in [
            (absent, "2026-10-16", "strengthening", "available"),
            ("2026-10-16", "2026-10-16", "strengthening", "available"),
            ("2026-10-15", "2026-10-16", "strengthening", "earlier_context"),
            ("2026-10-18", "2026-10-16", None, "date_unqualified"),
            ("2026-10-16", "2026-10-15", None, "date_unqualified"),
            ("2026-10-16", "2026-10-17", "strengthening", "newer_than_snapshot"),
            ("invalid", "2026-10-16", None, "date_unqualified"),
            (None, "2026-10-16", None, "date_unqualified"),
            ("", "2026-10-16", None, "date_unqualified"),
            ("2026-10-16", None, None, "date_unqualified"),
        ]:
            with self.subTest(nested=nested, parent=parent):
                tx = {"usd_dir": "strengthening"}
                if nested is not absent:
                    tx["as_of"] = nested
                w = build_workspace(snapshot(), fx={"asof": parent, "transmission": tx})
                self.assertEqual(w["fx"]["direction"], expected)
                self.assertEqual(w["fx"]["direction_state"], state)
                self.assertEqual(w["fx"]["rows"], [])
                if nested is absent:
                    self.assertIsNone(w["fx"]["direction_as_of"])
                    self.assertEqual(w["fx"]["direction_clock"], "publisher_date_only")
                html = template.render(commodity_workspace=w)
                dollar = html.split("<h3>The dollar</h3>", 1)[1].split('<a href="forex.html">', 1)[0]
                if state == "available":
                    self.assertIn("<strong>Strengthening</strong>", dollar)
                else:
                    self.assertNotIn("<strong>Strengthening</strong>", dollar)
                    self.assertIn("not qualified as same-date evidence", dollar)
                if nested == "2026-10-15":
                    self.assertIn("Dollar observation", dollar)
                    self.assertIn("2026-10-15", dollar)

    def test_no_mutation_or_malformed_receipt_crash(self):
        s = snapshot(); c = chain(); c["nodes"][0]["receipts"] = None
        c["hops"] = [None, "wrong", {"confirmed": "true"}]
        original = deepcopy(s)
        w = build_workspace(s, chain_state={"asof": "2026-10-16", "chains": [c]})
        self.assertEqual(s, original)
        self.assertFalse(w["chains"][0]["hops"][0]["confirmed"])
        self.assertEqual(build_workspace([])["assets"], [])

    def test_condition_round_trip_preserves_saved_evidence_and_exact_owner_field(self):
        w = build_workspace(snapshot())
        value, errors = validate_condition(condition(w), w)
        self.assertEqual(errors, [])
        self.assertEqual(value["threshold"], 0)
        self.assertEqual(value["metric_contract"]["field"], "velocity.r20")
        self.assertEqual(value["as_saved_evidence"]["asset"]["change_1m_pct"], 4)
        self.assertEqual(value["as_saved_evidence"]["hypothesis"]["id"], "supply")
        self.assertEqual(validate_condition(json.loads(json.dumps(value)), w), (value, []))
        self.assertFalse(value["monitoring_active"])
        self.assertFalse(value["metric_contract"]["evaluation_qualified"])

    def test_import_does_not_rebind_or_repair_semantics_silently(self):
        w = build_workspace(snapshot()); value, _ = validate_condition(condition(w), w)
        for key, changed in [("basis", "total_return"), ("contract", "CLZ26"), ("as_of", "2026-10-15"),
                             ("expiry_timezone", "Asia/Shanghai"), ("monitoring_active", True),
                             ("snapshot_fingerprint", "wrong"), ("window_sessions", True)]:
            edited = deepcopy(value); edited[key] = changed
            self.assertIsNone(validate_condition(edited, w)[0], key)
        newer = snapshot(); newer["asof"] = "2026-10-17"
        self.assertIn("snapshot_fingerprint", validate_condition(value, build_workspace(newer))[1])

    def test_unreadable_optional_publisher_is_local_degradation(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "latest.json"
            self.assertIsNone(read_publication(p))
            p.write_text('[1,2,3]'); self.assertIsNone(read_publication(p))
            p.write_text('{broken'); self.assertIsNone(read_publication(p))
            p.write_text('{"asof":"2026-10-16"}'); self.assertEqual(read_publication(p)["asof"], "2026-10-16")


def physical_fixture(values=(-.1, -2, -2), stamp="2026-10-09"):
    evidence = {}
    for stem, z in zip(("crude", "gasoline", "distillate"), values):
        for suffix, value, unit in (
            ("_stocks_mb", 100.0, "million_barrels"),
            ("_z", z, "seasonal_z"),
            ("_chg_4w_mb", 0, "million_barrels"),
        ):
            evidence[stem + suffix] = {
                "value": value, "unit": unit, "observation_at": stamp,
                "window_start": "2026-09-11" if "chg" in suffix else None,
                "window_end": stamp, "release_at": None, "state": "available",
                "reference": {"observations": 265, "start": "2021-09-17", "end": stamp},
                "source_ids": [stem + "_stocks"], "point_in_time_verified": False,
            }
    return {"schema": "mmx.commodities.petroleum_balance.v1", "display_only": True,
            "analysis_cutoff": "2026-10-16", "asof": stamp, "evidence": evidence,
            "method_revision": "fixture-r2", "sources": {}, "point_in_time_verified": False}


class PhysicalInterpretation(unittest.TestCase):
    def test_balance_interpretation_responds_to_product_divergence(self):
        cases = [
            ((-2, -2, -2), "broad_tightness"), ((2, 2, 2), "ample"),
            ((0, -2, -2), "product_tightness"), ((-2, 0, 1), "crude_tightness"),
            ((0, 0, 0), "near_seasonal"), ((0, -2, 2), "mixed"),
        ]
        headlines = set()
        for values, expected in cases:
            with self.subTest(values=values):
                w = build_workspace(snapshot(), physical_context=physical_fixture(values))
                self.assertEqual(w["physical"]["classification"], expected)
                self.assertFalse(w["physical"]["hypothesis_confirmation_eligible"])
                self.assertEqual(w["physical"]["age_days"], 7)
                headlines.add(w["physical"]["headline"]["en"])
                self.assertTrue(all(h["applicability"] == "unassessed" for h in w["hypotheses"]["oil"]))
        self.assertEqual(len(headlines), len(cases))

    def test_missing_or_misaligned_product_evidence_prevents_broad_conclusion(self):
        for variation in ("missing", "different_week", "short_reference", "bad_reference"):
            context = physical_fixture((-2, -2, -2))
            row = context["evidence"]["gasoline_z"]
            if variation == "missing":
                row["value"] = None
            elif variation == "different_week":
                row["observation_at"] = "2026-10-02"
            elif variation == "short_reference":
                row["reference"]["observations"] = 52
            else:
                row["reference"]["observations"] = "265"
            with self.subTest(variation=variation):
                ph = build_workspace(snapshot(), physical_context=context)["physical"]
                self.assertEqual(ph["classification"], "partial")
                self.assertEqual(ph["stocks"][0]["level"]["value"], 100)
                self.assertEqual(ph["stocks"][1]["balance"], "unavailable")

    def test_newer_observation_or_release_cannot_explain_earlier_snapshot(self):
        future = physical_fixture(stamp="2026-10-23")
        ph = build_workspace(snapshot(), physical_context=future)["physical"]
        self.assertEqual(ph["classification"], "unavailable")
        self.assertTrue(all(r["level"]["value"] is None for r in ph["stocks"]))
        future = physical_fixture()
        for r in future["evidence"].values():
            r["release_at"] = "2026-10-17T14:30:00Z"
        self.assertEqual(build_workspace(snapshot(), physical_context=future)["physical"]["classification"], "unavailable")
        future = physical_fixture(); future["analysis_cutoff"] = "2026-10-17"
        self.assertEqual(build_workspace(snapshot(), physical_context=future)["physical"]["classification"], "unavailable")

    def test_physical_tightness_does_not_fill_the_missing_inflation_stage(self):
        tx = {"asof": "2026-10-16", "chains": [{
            "chain": "oil_inflation_duration_derate", "falsifier_fired": None,
            "nodes": [{"id": "breakeven_rise", "resolved": True, "confirmed": False, "receipts": []}],
        }]}
        w = build_workspace(snapshot(), chain_state=tx, physical_context=physical_fixture((-2, -2, -2)))
        self.assertIn("not met", w["physical"]["downstream"]["en"])
        self.assertFalse(w["chains"][0]["nodes"][0]["confirmed"])
        self.assertNotEqual(w["chains"][0]["applicability"], "current_checks_met")

    def test_unqualified_level_cannot_be_rescued_by_its_seasonal_anomaly(self):
        context = physical_fixture((-2, -2, -2))
        context["evidence"]["crude_stocks_mb"]["release_at"] = "2026-10-17T14:30:00Z"
        ph = build_workspace(snapshot(), physical_context=context)["physical"]
        self.assertEqual(ph["classification"], "partial")
        self.assertEqual(ph["stocks"][0]["balance"], "unavailable")
        self.assertIsNone(ph["stocks"][0]["anomaly"]["value"])

    def test_unsigned_price_cannot_choose_the_rising_oil_transmission(self):
        for change in (None, 0):
            s = snapshot()
            s["members"][0]["chg_1m_pct"] = change
            tx = {"asof": "2026-10-16", "chains": [{
                "chain": "oil_inflation_duration_derate",
                "nodes": [{"id": "breakeven_rise", "resolved": True, "confirmed": True, "receipts": []}],
            }]}
            ph = build_workspace(s, chain_state=tx, physical_context=physical_fixture())["physical"]
            self.assertIn("needs its own dated evidence", ph["downstream"]["en"])

    def test_evidence_revision_invalidates_saved_condition_and_preserves_original(self):
        context = physical_fixture()
        w = build_workspace(snapshot(), physical_context=context)
        saved, errors = validate_condition(condition(w), w)
        self.assertEqual(errors, [])
        self.assertEqual(saved["as_saved_evidence"]["physical"]["classification"], "product_tightness")
        self.assertIn("physical", saved["source_dependencies"])
        edited = deepcopy(context)
        edited["evidence"]["gasoline_z"]["value"] = 2
        newer = build_workspace(snapshot(), physical_context=edited)
        self.assertNotEqual(newer["fingerprint"], w["fingerprint"])
        self.assertIn("snapshot_fingerprint", validate_condition(saved, newer)[1])
        self.assertEqual(saved["as_saved_evidence"]["physical"]["stocks"][1]["anomaly"]["value"], -2)
        edited = deepcopy(saved)
        edited["as_saved_evidence"]["physical"]["classification"] = "ample"
        self.assertIn("as_saved_evidence", validate_condition(edited, w)[1])

    def test_missing_physical_input_is_local_and_strict_template_still_renders(self):
        from jinja2 import Environment, FileSystemLoader, StrictUndefined
        root = Path(__file__).resolve().parents[1]
        env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=True, undefined=StrictUndefined)
        macro = '{% macro t(en,zh) %}{{ en }}{% endmacro %}'
        for context in (None, {}, physical_fixture((None, None, None))):
            w = build_workspace(snapshot(), physical_context=context)
            self.assertEqual(len(w["assets"]), 6)
            rendered = env.from_string(macro + '{% include "_commodity_decision_workspace.html.j2" %}').render(commodity_workspace=w)
            self.assertIn("cw-physical-oil", rendered)
            json.dumps(w, allow_nan=False)


def gold_publication(**overrides):
    premium = {"available": True, "method": "close_proxy", "state": "premium",
               "premium_pct": .2795508933302049, "price_currency": "CNY",
               "source_asof": "2026-10-14T07:30:00+00:00", "source_fresh": True,
               "avg_5_pct": .2562922796566136, "range_30_pct": [-.1792775538, .3826438861],
               "official_canonical_available": False, "context_only": True}
    premium.update(overrides)
    return {"asof": "2026-10-16", "gold_context": {"china_physical_premium": premium}}


class GoldPhysicalInterpretation(unittest.TestCase):
    def test_published_proxy_keeps_its_method_timestamp_and_percent_units(self):
        w = build_workspace(snapshot(), commodity_latest=gold_publication())
        g = w["gold_physical"]
        self.assertEqual(g["state"], "earlier_context")
        self.assertAlmostEqual(g["premium_pct"], .2795508933302049)
        self.assertEqual(g["clock"], "2026-10-14 07:30 UTC")
        self.assertIn("proxy", g["label"]["en"])
        self.assertFalse(g["official_canonical_available"])
        self.assertFalse(g["point_in_time_verified"])
        self.assertFalse(g["hypothesis_confirmation_eligible"])
        self.assertEqual(w["sources"]["gold_physical"]["field"], "gold_context.china_physical_premium")

    def test_sign_describes_relative_pricing_without_asserting_demand(self):
        for value, phrase in [(-.4, "below"), (0, "parity"), (.4, "above")]:
            g = build_workspace(snapshot(), commodity_latest=gold_publication(premium_pct=value))["gold_physical"]
            self.assertIn(phrase, g["headline"]["en"])
            self.assertIn("does not measure global physical demand", g["detail"]["en"])
        for value in [True, ".4", float("nan"), float("inf"), None, -100]:
            g = build_workspace(snapshot(), commodity_latest=gold_publication(premium_pct=value))["gold_physical"]
            self.assertIsNone(g["premium_pct"])

    def test_future_stale_undated_and_unsupported_context_degrade_locally(self):
        cases = [
            {"source_asof": "2026-10-17T07:30:00Z"},
            {"source_asof": "2026-10-16T23:30:00-05:00"},
            {"source_asof": "2026-10-14T07:30:00"},
            {"source_asof": None}, {"source_fresh": False},
            {"method": "unapproved"}, {"method": {}}, {"price_currency": "USD"}, {"context_only": False},
        ]
        for args in cases:
            with self.subTest(args=args):
                w = build_workspace(snapshot(), commodity_latest=gold_publication(**args))
                self.assertIsNone(w["gold_physical"]["premium_pct"])
                self.assertEqual(len(w["assets"]), 6)

    def test_statistics_remain_optional_and_do_not_cross_methods(self):
        g = build_workspace(snapshot(), commodity_latest=gold_publication(avg_5_pct=None, range_30_pct=[2, 1]))["gold_physical"]
        self.assertIsNotNone(g["premium_pct"])
        self.assertIsNone(g["avg_5_pct"])
        self.assertIsNone(g["range_30_pct"])
        g = build_workspace(snapshot(), commodity_latest=gold_publication(method="intraday", price_currency="USD"))["gold_physical"]
        self.assertIsNotNone(g["premium_pct"])
        self.assertIsNone(g["avg_5_pct"])
        self.assertIsNone(g["range_30_pct"])

    def test_proxy_does_not_resolve_rate_disagreement_and_is_saved_for_gold_only(self):
        tx = {"asof": "2026-10-16", "state": {"rates": {"real_10y_chg_22d_bp": -1}}}
        w = build_workspace(snapshot(), transmission=tx, chain_state={"asof": "2026-10-16", "chains": [chain(True)]},
                            commodity_latest=gold_publication())
        gold = next(a for a in w["assets"] if a["id"] == "gold")
        self.assertEqual(gold["read"]["headline"]["en"], "Weaker gold. Rate readings differ.")
        draft = condition(w); draft.update(asset="gold", hypothesis="rates")
        saved, errors = validate_condition(draft, w)
        self.assertEqual(errors, [])
        self.assertIsNone(saved["as_saved_evidence"]["physical"])
        self.assertEqual(saved["as_saved_evidence"]["gold_physical"]["method"], "close_proxy")
        revised = build_workspace(snapshot(), commodity_latest=gold_publication(premium_pct=-.1))
        self.assertIn("snapshot_fingerprint", validate_condition(saved, revised)[1])


def configured_roster_fixture():
    """Synthetic caller input shaped from config.yml complex_members at 96883381.

    The mapping is a test fixture, not a second production universe owner. No
    return or state in configured_snapshot_fixture is an observed market fact.
    """
    families = {
        "energy": ("oil", "natgas", "gasoline", "heating_oil"),
        "precious": ("gold", "silver", "platinum", "palladium"),
        "industrial": ("copper",), "grain": ("corn", "wheat", "soybeans"),
        "soft": ("coffee", "sugar", "cocoa", "cotton"), "livestock": ("live_cattle",),
    }
    return [{"id": key, "family": family} for family, members in families.items() for key in members]


def configured_snapshot_fixture():
    roster = configured_roster_fixture()
    return {"asof": "2026-10-16", "index": {"chg_1m_pct": 0},
            "breadth": {"n_members": len(roster), "n_up_trend": len(roster)},
            "members": [{"name": row["id"], "class": row["family"], "chg_1m_pct": 0,
                         "velocity": {"r5": 0, "r20": -2, "r60": None, "r252": 3},
                         "ts_trend": "up", "momentum_state": "neutral"} for row in roster]}


class ConfiguredUniverseCoverage(unittest.TestCase):
    """Pure publication coverage; no collection, economic recalculation or UI proof."""

    @staticmethod
    def family(workspace, key="energy"):
        return next(row for row in workspace["families"] if row["id"] == key)

    def test_complete_roster_counts_and_order_independence(self):
        raw, roster = configured_snapshot_fixture(), configured_roster_fixture()
        w = build_workspace(raw, expected_members=roster)
        self.assertEqual(w["projection_revision"], 7)
        universe = w["universe"]
        self.assertEqual(universe["state"], "known")
        self.assertEqual(universe["owner"]["key"], "commodities.complex_members")
        self.assertIsNone(universe["owner"]["immutable_source"])
        self.assertEqual(universe["issues"], [])
        coverage = universe["coverage"]
        self.assertEqual((coverage["expected_n"], coverage["present_n"], coverage["matched_n"],
                          coverage["price_1m_known_n"]), (17, 17, 17, 17))
        self.assertEqual(coverage["state"], "complete")
        self.assertEqual(coverage["price_1m_state"], "complete")
        self.assertEqual({row["id"]: row["coverage"]["expected_n"] for row in w["families"]},
                         {"energy": 4, "precious": 4, "industrial": 1, "grain": 3, "soft": 4, "livestock": 1})
        reordered = build_workspace(raw, expected_members=list(reversed(roster)))
        self.assertEqual(reordered["universe"], universe)
        self.assertEqual(reordered["fingerprint"], w["fingerprint"])

    def test_missing_member_does_not_shrink_expected_family(self):
        raw = configured_snapshot_fixture()
        raw["members"] = [row for row in raw["members"] if row["name"] != "gasoline"]
        w = build_workspace(raw, expected_members=configured_roster_fixture())
        energy = self.family(w)
        self.assertEqual(len(w["assets"]), 16)
        self.assertEqual(len(energy["assets"]), 3)
        self.assertEqual(energy["coverage"]["expected_n"], 4)
        self.assertEqual(energy["coverage"]["present_n"], 3)
        self.assertEqual(energy["coverage"]["matched_n"], 3)
        self.assertEqual(energy["coverage"]["state"], "partial")
        self.assertEqual(energy["coverage"]["price_1m_state"], "partial")
        self.assertEqual(energy["coverage"]["missing_ids"], ["gasoline"])
        self.assertEqual(energy["coverage"]["price_1m_unavailable_ids"], [])
        self.assertNotIn("gasoline", [asset["id"] for asset in w["assets"]])

    def test_absent_family_remains_without_synthetic_assets(self):
        raw, roster = configured_snapshot_fixture(), configured_roster_fixture()
        complete = build_workspace(raw, expected_members=roster)
        raw["members"] = [row for row in raw["members"] if row["class"] != "energy"]
        w = build_workspace(raw, expected_members=roster)
        energy = self.family(w)
        self.assertEqual(len(w["families"]), 6)
        self.assertEqual(len(w["assets"]), 13)
        self.assertEqual(energy["assets"], [])
        coverage = energy["coverage"]
        self.assertEqual((coverage["expected_n"], coverage["present_n"], coverage["price_1m_known_n"]), (4, 0, 0))
        self.assertEqual(coverage["state"], "missing")
        self.assertEqual(coverage["price_1m_state"], "unavailable")
        self.assertEqual(coverage["missing_ids"], ["gasoline", "heating_oil", "natgas", "oil"])
        for family in w["families"]:
            if family["id"] != "energy":
                self.assertEqual(family, self.family(complete, family["id"]))

    def test_present_null_and_actual_zero_have_separate_coverage(self):
        raw = configured_snapshot_fixture()
        next(row for row in raw["members"] if row["name"] == "gasoline")["chg_1m_pct"] = None
        w = build_workspace(raw, expected_members=configured_roster_fixture())
        coverage = self.family(w)["coverage"]
        self.assertEqual((coverage["present_n"], coverage["matched_n"], coverage["price_1m_known_n"]), (4, 4, 3))
        self.assertEqual(coverage["state"], "complete")
        self.assertEqual(coverage["price_1m_state"], "partial")
        self.assertEqual(coverage["missing_ids"], [])
        self.assertEqual(coverage["price_1m_unavailable_ids"], ["gasoline"])
        self.assertEqual(next(asset for asset in w["assets"] if asset["id"] == "oil")["change_1m_pct"], 0)

    def test_unknown_and_invalid_rosters_never_infer_a_denominator(self):
        cases = [(None, "unknown", "roster_unavailable"), ({}, "invalid", "invalid_roster_type"),
                 ([], "invalid", "empty_roster"), ("oil", "invalid", "invalid_roster_type"),
                 ([None], "invalid", "invalid_roster_entry"),
                 ([{"id": [], "family": "energy"}], "invalid", "invalid_roster_entry"),
                 ([{"id": "oil", "family": {}}], "invalid", "invalid_roster_entry"),
                 ([{"id": "oil", "family": "unowned"}], "invalid", "unsupported_family"),
                 ([{"id": "oil", "family": "energy"}] * 2, "invalid", "duplicate_expected_member")]
        raw = configured_snapshot_fixture()
        baseline = build_workspace(raw)
        for roster, state, code in cases:
            with self.subTest(roster=roster):
                w = build_workspace(raw, expected_members=roster)
                self.assertEqual(w["universe"]["state"], state)
                self.assertIn(code, [issue["code"] for issue in w["universe"]["issues"]])
                self.assertEqual(w["assets"], baseline["assets"])
                for coverage in [w["universe"]["coverage"]] + [row["coverage"] for row in w["families"]]:
                    self.assertEqual(coverage["state"], state)
                    self.assertIsNone(coverage["expected_n"])
                    self.assertIsNone(coverage["present_n"])
                    self.assertIsNone(coverage["price_1m_known_n"])
                json.dumps(w, allow_nan=False)

    def test_unsupported_expected_member_is_retained_and_not_fabricated(self):
        raw, roster = configured_snapshot_fixture(), configured_roster_fixture()
        roster.append({"id": "aluminium_fixture", "family": "industrial"})
        for present in (False, True):
            with self.subTest(present=present):
                if present:
                    raw["members"].append({"name": "aluminium_fixture", "class": "industrial", "chg_1m_pct": 8})
                w = build_workspace(raw, expected_members=roster)
                coverage = self.family(w, "industrial")["coverage"]
                self.assertEqual(w["universe"]["state"], "known")
                self.assertEqual(w["universe"]["coverage"]["expected_n"], 18)
                self.assertEqual(coverage["expected_n"], 2)
                self.assertEqual(coverage["present_n"], 2 if present else 1)
                self.assertEqual(coverage["matched_n"], 1)
                self.assertEqual(coverage["state"], "inconsistent")
                self.assertEqual(coverage["missing_ids"], [] if present else ["aluminium_fixture"])
                self.assertEqual(coverage["unqualified_ids"], ["aluminium_fixture"] if present else [])
                self.assertIn("unsupported_expected_member", [issue["code"] for issue in coverage["issues"]])
                self.assertEqual(len(w["assets"]), 17)

    def test_duplicate_and_mismatched_observations_cannot_certify_completeness(self):
        for kind in ("duplicate", "mismatch"):
            with self.subTest(kind=kind):
                raw = configured_snapshot_fixture()
                oil = next(row for row in raw["members"] if row["name"] == "oil")
                if kind == "duplicate":
                    raw["members"].append(dict(oil, chg_1m_pct=99))
                else:
                    oil["class"] = "precious"
                w = build_workspace(raw, expected_members=configured_roster_fixture())
                coverage = self.family(w)["coverage"]
                self.assertEqual((coverage["expected_n"], coverage["present_n"], coverage["matched_n"]), (4, 4, 3))
                self.assertEqual(coverage["state"], "inconsistent")
                self.assertEqual(coverage["price_1m_state"], "inconsistent")
                self.assertEqual(coverage["missing_ids"], [])
                self.assertEqual(coverage["unqualified_ids"], ["oil"])
                code = "duplicate_observation" if kind == "duplicate" else "family_mismatch"
                self.assertIn(code, [issue["code"] for issue in coverage["issues"]])
                projected = next(asset for asset in w["assets"] if asset["id"] == "oil")
                self.assertEqual(projected["change_1m_pct"], 0)
                self.assertEqual(projected["family"], "energy" if kind == "duplicate" else "precious")

    def test_unexpected_observation_does_not_expand_the_owned_denominator(self):
        roster = [row for row in configured_roster_fixture() if row["id"] != "gold"]
        w = build_workspace(configured_snapshot_fixture(), expected_members=roster)
        self.assertEqual(len(w["assets"]), 17)
        self.assertEqual(w["universe"]["coverage"]["expected_n"], 16)
        self.assertEqual(w["universe"]["coverage"]["present_n"], 16)
        self.assertEqual(w["universe"]["coverage"]["state"], "inconsistent")
        self.assertEqual(self.family(w, "precious")["coverage"]["expected_n"], 3)
        self.assertIn({"code": "unexpected_member", "id": "gold", "observed_family": "precious"}, w["universe"]["issues"])

    def test_malformed_observations_are_explicit_and_json_safe(self):
        cases = [(None, "invalid_observation"), ({"name": []}, "invalid_observation"),
                 ({"name": "oil", "class": {}}, "invalid_observation_family")]
        for row, code in cases:
            with self.subTest(row=row):
                raw = configured_snapshot_fixture()
                raw["members"].append(row)
                w = build_workspace(raw, expected_members=configured_roster_fixture())
                self.assertIn(code, [issue["code"] for issue in w["universe"]["issues"]])
                self.assertEqual(w["universe"]["coverage"]["state"], "inconsistent")
                json.dumps(w, allow_nan=False)
        raw = configured_snapshot_fixture()
        raw["members"] = {"oil": {"chg_1m_pct": 4}}
        w = build_workspace(raw, expected_members=configured_roster_fixture())
        self.assertIn({"code": "invalid_observations_type"}, w["universe"]["issues"])
        self.assertEqual(w["assets"], [])

    def test_empty_publication_keeps_all_expected_families(self):
        for raw in ({}, {"members": []}):
            with self.subTest(raw=raw):
                w = build_workspace(raw, expected_members=configured_roster_fixture())
                self.assertEqual(w["assets"], [])
                self.assertEqual(len(w["families"]), 6)
                self.assertEqual(w["universe"]["coverage"]["expected_n"], 17)
                self.assertEqual(w["universe"]["coverage"]["present_n"], 0)
                for family in w["families"]:
                    self.assertEqual(family["assets"], [])
                    self.assertEqual(family["coverage"]["state"], "missing")
                    self.assertEqual(family["coverage"]["price_1m_state"], "unavailable")

    def test_roster_revision_changes_evidence_identity_without_rebinding(self):
        raw, roster = configured_snapshot_fixture(), configured_roster_fixture()
        w = build_workspace(raw, expected_members=roster)
        saved, errors = validate_condition(condition(w), w)
        self.assertEqual(errors, [])
        original = deepcopy(saved)
        changed = [row for row in roster if row["id"] != "gasoline"]
        revised = build_workspace(raw, expected_members=changed)
        self.assertNotEqual(revised["fingerprint"], w["fingerprint"])
        self.assertNotEqual(revised["universe"]["roster_fingerprint"], w["universe"]["roster_fingerprint"])
        self.assertIn("snapshot_fingerprint", validate_condition(saved, revised)[1])
        self.assertEqual(saved, original)
        self.assertEqual(validate_condition(saved, w), (saved, []))

    def test_addition_preserves_observed_r3_fields_and_does_not_mutate_inputs(self):
        raw = snapshot()
        roster = [{"id": row["name"], "family": row["class"]} for row in raw["members"]]
        identity = {"repository": "fixture", "commit": "f" * 40, "path": "config.yml", "file_sha256": "a" * 64}
        kwargs = {"physical_context": physical_fixture(), "commodity_latest": gold_publication(),
                  "chain_state": {"asof": "2026-10-16", "chains": [chain(True)]},
                  "transmission": {"asof": "2026-10-16", "state": {"rates": {"real_10y_chg_22d_bp": -1}}},
                  "source_identities": {"universe": identity}}
        original = deepcopy((raw, roster, kwargs))
        before = build_workspace(raw, **kwargs)
        after = build_workspace(raw, expected_members=roster, **kwargs)
        # The revision-seven collective hero now requires configured coverage;
        # all individual R3 readings and their evidence remain untouched.
        self.assertEqual(before["headline"]["en"], "Read each commodity")
        self.assertEqual(after["headline"]["en"], "Oil holds. Metals retreat.")
        for key in before.keys() - {"universe", "families", "fingerprint", "headline"}:
            self.assertEqual(after[key], before[key], key)
        strip_coverage = lambda families: [{key: value for key, value in family.items() if key != "coverage"}
                                           for family in families]
        self.assertEqual(strip_coverage(after["families"]), strip_coverage(before["families"]))
        self.assertEqual((raw, roster, kwargs), original)
        self.assertEqual(after["universe"]["owner"]["immutable_source"], identity)
        after["universe"]["owner"]["immutable_source"]["commit"] = "changed"
        after["universe"]["expected_members"][0]["family"] = "changed"
        self.assertEqual((raw, roster, kwargs), original)


class ConfiguredUniverseHeadline(unittest.TestCase):
    """Collective hero language is bounded to the configured oil + metals scope."""

    @staticmethod
    def raw():
        raw = configured_snapshot_fixture()
        for row in raw["members"]:
            if row["name"] == "oil":
                row["chg_1m_pct"] = 1
            elif row["class"] in ("precious", "industrial"):
                row["chg_1m_pct"] = -1
        return raw

    def test_valid_scope_preserves_headline_and_individual_interpretations(self):
        raw = self.raw()
        qualified = build_workspace(raw, expected_members=configured_roster_fixture())
        unknown = build_workspace(raw)
        self.assertEqual(qualified["headline"]["en"], "Oil holds. Metals retreat.")
        self.assertEqual(qualified["headline"]["zh"], "油价坚挺，金属回落。")
        self.assertEqual(qualified["assets"], unknown["assets"])

    def test_unknown_invalid_and_duplicate_rosters_withhold_collective_claim(self):
        duplicate = configured_roster_fixture() + [{"id": "gold", "family": "precious"}]
        for roster in (None, {}, [], duplicate):
            with self.subTest(roster=roster):
                w = build_workspace(self.raw(), expected_members=roster)
                self.assertEqual(w["projection_revision"], 7)
                self.assertEqual(w["headline"]["en"], "Read each commodity")

    def test_duplicate_mismatched_missing_and_null_metals_withhold_collective_claim(self):
        for case in ("duplicate", "mismatch", "missing", "null"):
            with self.subTest(case=case):
                raw = self.raw()
                gold = next(row for row in raw["members"] if row["name"] == "gold")
                if case == "duplicate":
                    raw["members"].append(deepcopy(gold))
                elif case == "mismatch":
                    gold["class"] = "energy"
                elif case == "missing":
                    raw["members"].remove(gold)
                else:
                    gold["chg_1m_pct"] = None
                self.assertEqual(build_workspace(raw, expected_members=configured_roster_fixture())[
                    "headline"]["en"], "Read each commodity")

    def test_additional_configured_metal_does_not_shrink_to_supported_subset(self):
        roster = configured_roster_fixture() + [{"id": "aluminium_fixture", "family": "industrial"}]
        for present in (False, True):
            with self.subTest(present=present):
                raw = self.raw()
                if present:
                    raw["members"].append({"name": "aluminium_fixture", "class": "industrial", "chg_1m_pct": -1})
                w = build_workspace(raw, expected_members=roster)
                self.assertEqual(w["headline"]["en"], "Read each commodity")
                self.assertEqual(ConfiguredUniverseCoverage.family(w, "industrial")["coverage"]["expected_n"], 2)

    def test_missing_nonmetal_does_not_invalidate_qualified_narrow_observation(self):
        raw = self.raw()
        raw["members"] = [row for row in raw["members"] if row["name"] not in ("gasoline", "corn")]
        w = build_workspace(raw, expected_members=configured_roster_fixture())
        self.assertEqual(w["universe"]["coverage"]["state"], "partial")
        self.assertEqual(w["headline"]["en"], "Oil holds. Metals retreat.")

    def test_oil_identity_must_also_match_its_configuration(self):
        for case in ("duplicate", "observed_mismatch", "configured_mismatch"):
            with self.subTest(case=case):
                raw, roster = self.raw(), configured_roster_fixture()
                oil = next(row for row in raw["members"] if row["name"] == "oil")
                if case == "duplicate":
                    raw["members"].append(deepcopy(oil))
                elif case == "observed_mismatch":
                    oil["class"] = "precious"
                else:
                    next(row for row in roster if row["id"] == "oil")["family"] = "precious"
                self.assertEqual(build_workspace(raw, expected_members=roster)["headline"]["en"], "Read each commodity")


class ConfiguredUniverseWiring(unittest.TestCase):
    """Real adapter/helper wiring with synthetic inputs; no market/live proof.

    The review tests replace only pinned-byte retrieval and the UI template. They
    run the actual renderer, pure projection and physical owner on unavailable
    series. They qualify configuration custody, not the real page's appearance.
    """

    @staticmethod
    def configuration():
        return {"complex_members": {row["id"]: ["FIXTURE-" + row["id"], None, row["family"]]
                                    for row in configured_roster_fixture()}}

    @staticmethod
    def publications(root):
        data = root / "fixture-publications"
        for path, value in {
            "transmission/chain_state.json": {},
            "transmission/latest.json": {"asof": "2026-10-16", "state": {"rates": {"real_10y_chg_22d_bp": 0}}},
            "forex/latest.json": {"asof": "2026-10-16", "transmission": {"usd_dir": "flat"}},
            "commodity/latest.json": {"asof": "2026-10-16"},
        }.items():
            target = data / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(value), encoding="utf-8")
        # The adapter must use the supplied owner, never read this competing file.
        (root / "config.yml").write_text('{"commodities":{"complex_members":{}}}', encoding="utf-8")
        return data

    def test_adapter_preserves_absent_family_using_supplied_configuration(self):
        raw, cfg = configured_snapshot_fixture(), self.configuration()
        raw["members"] = [row for row in raw["members"] if row["class"] != "energy"]
        before = deepcopy((raw, cfg))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.publications(root)
            w = workspace_from_publications(raw, root=root, data_root=data, commodity_config=cfg)
            changed_cfg = deepcopy(cfg)
            del changed_cfg["complex_members"]["gasoline"]
            revised = workspace_from_publications(raw, root=root, data_root=data, commodity_config=changed_cfg)
        self.assertEqual((raw, cfg), before)
        self.assertEqual(w["universe"]["coverage"]["expected_n"], 17)
        self.assertEqual(w["universe"]["coverage"]["present_n"], 13)
        self.assertIsNone(w["universe"]["owner"]["immutable_source"])
        energy = ConfiguredUniverseCoverage.family(w)
        self.assertEqual(energy["assets"], [])
        self.assertEqual(energy["coverage"]["state"], "missing")
        self.assertEqual(energy["coverage"]["expected_n"], 4)
        self.assertEqual(len(w["assets"]), 13)
        self.assertEqual(w["rates"]["real_10y_chg_22d_bp"], 0)
        self.assertEqual(w["fx"]["direction"], "flat")
        self.assertEqual(w["projection_revision"], 7)
        self.assertEqual(revised["universe"]["coverage"]["expected_n"], 16)
        self.assertEqual(ConfiguredUniverseCoverage.family(revised)["coverage"]["expected_n"], 3)
        self.assertNotEqual(revised["fingerprint"], w["fingerprint"])

    def test_adapter_never_accepts_malformed_config_as_an_observed_roster(self):
        cases = [(None, "unknown"), ({}, "unknown"), ({"complex_members": None}, "unknown"),
                 ([], "invalid"), ({"complex_members": configured_roster_fixture()}, "invalid"),
                 ({"complex_members": {}}, "invalid"), ({"complex_members": {"oil": "bad"}}, "invalid"),
                 ({"complex_members": {"oil": ["FIXTURE-OIL", None]}}, "invalid"),
                 ({"complex_members": {"oil": ["FIXTURE-OIL", None, "unowned"]}}, "invalid")]
        raw = configured_snapshot_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.publications(root)
            for cfg, expected in cases:
                with self.subTest(config=cfg):
                    w = workspace_from_publications(raw, root=root, data_root=data, commodity_config=cfg)
                    self.assertEqual(w["universe"]["state"], expected)
                    self.assertIsNone(w["universe"]["coverage"]["expected_n"])
                    self.assertEqual(len(w["assets"]), 17)
                    self.assertTrue(w["universe"]["issues"])
                    self.assertIsNone(w["universe"]["owner"]["immutable_source"])

    def test_complete_membership_does_not_repair_publisher_breadth(self):
        raw = configured_snapshot_fixture()
        raw["breadth"] = {"n_members": 12, "n_up_trend": 8}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            w = workspace_from_publications(raw, root=root, data_root=self.publications(root),
                                            commodity_config=self.configuration())
        self.assertEqual(w["universe"]["coverage"]["state"], "complete")
        self.assertEqual(w["universe"]["coverage"]["expected_n"], 17)
        self.assertEqual(w["breadth"], {"n": None, "up": None, "state": "inconsistent_or_missing"})
        self.assertEqual(raw["breadth"], {"n_members": 12, "n_up_trend": 8})

    def test_normal_builder_helper_passes_loaded_configuration(self):
        # Execute the exact render-only helper without importing collector-capable
        # main-module dependencies or calling build_commodities.main().
        source = Path(__file__).resolve().parents[1] / "scripts/build_commodities.py"
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_decision_workspace")
        raw, cfg = configured_snapshot_fixture(), self.configuration()
        raw["members"] = [row for row in raw["members"] if row["class"] != "energy"]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.publications(root)
            owner = SimpleNamespace(ROOT=root, data_dir=lambda: data, load=lambda: {"commodities": cfg})
            namespace = {"config": owner, "log": logging.getLogger(__name__)}
            exec(compile(ast.Module(body=[helper], type_ignores=[]), str(source), "exec"), namespace)
            w = namespace["_decision_workspace"](raw, raw["asof"], physical_fixture())
        self.assertIsNotNone(w)
        self.assertEqual(w["universe"]["coverage"]["expected_n"], 17)
        self.assertEqual(ConfiguredUniverseCoverage.family(w)["coverage"]["state"], "missing")
        self.assertEqual(w["physical"]["classification"], build_workspace(raw, physical_context=physical_fixture())["physical"]["classification"])
        self.assertIsNone(w["universe"]["owner"]["immutable_source"])

    @staticmethod
    def renderer():
        path = Path(__file__).resolve().parents[1] / "scripts/render_commodity_workspace_review.py"
        spec = importlib.util.spec_from_file_location("commodity_coverage_review_fixture", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def review_templates(root):
        templates = root / "templates"
        templates.mkdir()
        (templates / "_commodity_decision_workspace.html.j2").write_text(
            '<section id="commodity-workspace"><script id="cw-data" type="application/json">'
            '{{ commodity_workspace|tojson }}</script></section>', encoding="utf-8")
        (templates / "commodity-workspace.css").write_text(".fixture { display: block; }", encoding="utf-8")
        (templates / "commodity-workspace.js").write_text("window.coverageFixture = 1;", encoding="utf-8")

    @unittest.skipUnless(importlib.util.find_spec("jinja2") is not None, "renderer integration requires Jinja2")
    def test_review_renderer_uses_same_pinned_config_bytes_and_real_content_hash(self):
        review = self.renderer()
        # This is a mocked retrieval address, not a claimed production commit.
        base = "f" * 40
        raw = configured_snapshot_fixture()
        raw["members"] = [row for row in raw["members"] if row["class"] != "energy"]
        config_raw = json.dumps({"commodities": self.configuration(), "eia": {"supply": {}}}).encode()
        files = {path: json.dumps(raw if key == "commodities" else {}).encode()
                 for key, path in review.SOURCE_PATHS.items()}
        files.update({"config.yml": config_raw, "data/reference/vendor_aliases.parquet": b"fixture-not-read",
                      "site/commodities.html": b'<html><head><style>body{}</style></head><body class="page-commod"><div class="wrap"><h1>Fixture legacy heading</h1><p id="fixture-legacy">Retained legacy analysis.</p></div></body></html>',
                      "templates/theme.css": b"body { color: black; }"})
        requests = []

        def pinned_bytes(commit, path):
            requests.append((commit, path))
            if path not in files:
                raise subprocess.CalledProcessError(128, ["fixture-git-show", path])
            return files[path]

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.review_templates(root)
            (root / "config.yml").write_text('{"commodities":{"complex_members":{}}}', encoding="utf-8")
            with patch.object(review, "ROOT", root), patch.object(review, "git_bytes", side_effect=pinned_bytes):
                html, report, component = review.render_review(base)
        w = json.loads(re.search(r'<script id="cw-data"[^>]*>(.*?)</script>', component, re.S).group(1))
        identity = {"repository": "mastermindx-market-intelligence/macro", "commit": base,
                    "path": "config.yml", "file_sha256": sha256(config_raw).hexdigest()}
        self.assertEqual(w["universe"]["owner"]["immutable_source"], identity)
        self.assertEqual(report["source_files"]["universe"], identity)
        self.assertEqual(w["universe"]["coverage"]["expected_n"], 17)
        self.assertEqual(ConfiguredUniverseCoverage.family(w)["coverage"]["state"], "missing")
        self.assertNotIn("universe", w["sources"])
        self.assertTrue(all(commit == base for commit, _ in requests))
        self.assertEqual(requests.count((base, "config.yml")), 1)
        self.assertFalse(report["production_acceptance"])
        self.assertIn('<p id="fixture-legacy">Retained legacy analysis.</p>', html)
        self.assertIn("Detailed commodity analytics", html)

    @unittest.skipUnless(importlib.util.find_spec("jinja2") is not None, "renderer integration requires Jinja2")
    def test_pinned_renderer_replaces_existing_workspace_and_preserves_legacy(self):
        review = self.renderer()
        base = "f" * 40
        raw = configured_snapshot_fixture()
        files = {path: json.dumps(raw if key == "commodities" else {}).encode()
                 for key, path in review.SOURCE_PATHS.items()}
        legacy = '<details id="commodity-advanced"><p>Retained legacy analysis.</p></details>'
        old_payload = '{"projection_revision": 6, "fixture": "old payload"}'
        files.update({
            "config.yml": json.dumps({"commodities": self.configuration(), "eia": {"supply": {}}}).encode(),
            "data/reference/vendor_aliases.parquet": b"fixture-not-read",
            "templates/commodity-workspace.js": b"window.oldWorkspace = true;",
            "templates/commodity-workspace.css": b".old-workspace { color: black; }",
            "site/assets/css/old.css": b".old-workspace { color: black; }",
            "site/commodities.html": ('<html><head><link rel="stylesheet" href="assets/css/old.css"></head><body>'
                '<div class="wrap"><section id="commodity-workspace"><section>Old composition</section>'
                '<script id="cw-data" type="application/json">' + old_payload + '</script></section>'
                + legacy + '</div><script>window.oldWorkspace = true;</script>'
                '<script>window.sharedOwner = true;</script></body></html>').encode(),
        })

        def pinned_bytes(commit, path):
            self.assertEqual(commit, base)
            if path not in files:
                raise subprocess.CalledProcessError(128, ["fixture-git-show", path])
            return files[path]

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.review_templates(root)
            with patch.object(review, "ROOT", root), patch.object(review, "git_bytes", side_effect=pinned_bytes):
                html, report, component = review.render_review(base)
        w = json.loads(re.search(r'<script id="cw-data"[^>]*>(.*?)</script>', component, re.S).group(1))
        self.assertEqual(w["projection_revision"], 7)
        self.assertEqual(w["universe"]["coverage"]["expected_n"], 17)
        self.assertEqual(html.count('id="commodity-workspace"'), 1)
        self.assertEqual(html.count('id="cw-data"'), 1)
        self.assertIn(legacy, html)
        self.assertIn('<script>window.sharedOwner = true;</script>', html)
        self.assertIn("window.coverageFixture = 1;", html)
        self.assertNotIn("window.oldWorkspace", html)
        self.assertNotIn("assets/css/old.css", html)
        self.assertNotIn(old_payload, html)
        self.assertEqual(report["mode"], "pinned_publications_new_projection")
        self.assertFalse(report["normal_publication_renderer_qualified"])
        self.assertFalse(report["production_acceptance"])

    @unittest.skipUnless(importlib.util.find_spec("jinja2") is not None, "renderer integration requires Jinja2")
    def test_presentation_only_renderer_does_not_upgrade_revision_six_payload(self):
        review = self.renderer()
        base = "f" * 40
        w = {"as_of": "2026-10-16", "assets": [], "chains": [], "fingerprint": "fixture-revision-six",
             "projection_revision": 6}
        payload = json.dumps(w, sort_keys=True)
        previous_js, previous_css = b"window.coverageFixture = 0;", b".old-fixture { display: block; }"
        original = ('<html><head><link rel="stylesheet" href="assets/workspace.css"></head><body>'
                    '<section id="commodity-workspace"><script id="cw-data" type="application/json">' + payload +
                    '</script></section><script>' + previous_js.decode() + '</script></body></html>')
        files = {"site/commodities.html": original.encode(), "templates/commodity-workspace.js": previous_js,
                 "templates/commodity-workspace.css": previous_css, "site/assets/workspace.css": previous_css}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.review_templates(root)
            with patch.object(review, "ROOT", root), patch.object(review, "git_bytes", side_effect=lambda commit, path: files[path]), \
                 patch.object(review, "build_workspace", side_effect=AssertionError("presentation-only must not reproject")), \
                 patch.object(review, "configured_members_from_config", side_effect=AssertionError("presentation-only must not add configuration")):
                html, report, component = review.render_published_workspace(base)
        serialized = re.search(r'<script id="cw-data"[^>]*>(.*?)</script>', component, re.S).group(1)
        self.assertEqual(serialized, payload)
        self.assertEqual(json.loads(serialized)["projection_revision"], 6)
        self.assertNotIn("universe", json.loads(serialized))
        self.assertTrue(report["payload_bytes_unchanged"])
        self.assertFalse(report["economic_recomputation"])
        self.assertIn("window.coverageFixture = 1;", html)


def coverage_presentation_fixture(case):
    """Synthetic renderer inputs; none is an observed production publication."""
    raw, roster = configured_snapshot_fixture(), configured_roster_fixture()
    if case == "absent_gasoline":
        raw["members"] = [row for row in raw["members"] if row["name"] != "gasoline"]
        for row in raw["members"]:
            if row["class"] == "energy":
                row["chg_1m_pct"] = 2
    elif case == "absent_energy":
        raw["members"] = [row for row in raw["members"] if row["class"] != "energy"]
    elif case == "null_gasoline":
        next(row for row in raw["members"] if row["name"] == "gasoline")["chg_1m_pct"] = None
    elif case == "invalid_roster":
        roster = {}
    elif case in ("unknown_roster", "revision_six"):
        roster = None
    elif case == "misclassified_oil":
        raw["members"] = [{"name": "oil", "class": "precious", "chg_1m_pct": 0}]
        roster = [{"id": "oil", "family": "energy"}]
    elif case == "unexpected_family":
        raw["members"] = [{"name": "gold", "class": "precious", "chg_1m_pct": 0}]
        roster = [{"id": "oil", "family": "energy"}]
    elif case != "zero":
        raise ValueError("Unknown synthetic coverage case")
    w = build_workspace(raw, expected_members=roster)
    if case == "revision_six":
        # An explicit old-shape fixture, not a new published revision-six identity.
        w.pop("universe")
        for family in w["families"]:
            family.pop("coverage")
        w["projection_revision"] = 6
    return w


class ConfiguredUniversePresentation(unittest.TestCase):
    @staticmethod
    def render(workspace):
        from jinja2 import Environment, FileSystemLoader, StrictUndefined
        env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1] / "templates"),
                          autoescape=True, undefined=StrictUndefined)
        macro = '{% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}'
        return env.from_string(macro + '{% include "_commodity_decision_workspace.html.j2" %}').render(
            commodity_workspace=workspace)

    @classmethod
    def energy(cls, case):
        return re.findall(r'<article class="panel cw-panel cw-family-reading">(.*?)</article>',
                          cls.render(coverage_presentation_fixture(case)), re.S)[0]

    def test_absent_member_keeps_expected_denominator_and_withholds_complete_verdict(self):
        energy = self.energy("absent_gasoline")
        self.assertRegex(energy, r'data-cw-members-present>\s*3 / 4')
        self.assertRegex(energy, r'data-cw-prices-available>\s*3 / 4')
        self.assertIn("Coverage is incomplete.", energy)
        self.assertIn("覆盖不完整", energy)
        self.assertNotIn("Every tracked member rose", energy)
        self.assertNotIn("3 / 3", energy)
        self.assertNotIn('data-cw-open="gasoline"', energy)

    def test_absent_family_is_visible_without_zero_breadth_or_fake_assets(self):
        w = coverage_presentation_fixture("absent_energy")
        html, energy = self.render(w), self.energy("absent_energy")
        self.assertIn("This family is missing from the snapshot.", energy)
        self.assertIn("本快照缺少这一类别", energy)
        self.assertRegex(energy, r'data-cw-members-present>\s*0 / 4')
        self.assertRegex(energy, r'data-cw-prices-available>\s*0 / 4')
        self.assertIn("Price evidence unavailable", energy)
        self.assertIn("Review family coverage", energy)
        self.assertIn('data-cw-family="energy"', html)
        self.assertNotIn("0 / 0", html)
        self.assertNotIn("All recorded changes are flat", energy)
        self.assertNotIn('data-cw-open="oil"', html)
        self.assertNotRegex(html, r'<input[^>]*value="oil"[^>]*data-cw-(?:pick|compare)')
        self.assertEqual(len(w["assets"]), 13)

    def test_present_null_and_real_zero_have_distinct_price_qualification(self):
        partial, zero = self.energy("null_gasoline"), self.energy("zero")
        self.assertRegex(partial, r'data-cw-members-present>\s*4 / 4')
        self.assertRegex(partial, r'data-cw-prices-available>\s*3 / 4')
        self.assertIn("Coverage is incomplete.", partial)
        self.assertNotIn("All recorded changes are flat", partial)
        self.assertRegex(zero, r'data-cw-prices-available>\s*4 / 4')
        self.assertIn("All recorded changes are flat.", zero)
        self.assertIn("+0.0%", zero)

    def test_unknown_invalid_and_old_payloads_never_assert_observed_only_completeness(self):
        for case, expected in (("unknown_roster", "Configured membership is unavailable"),
                               ("invalid_roster", "Configured membership is invalid"),
                               ("revision_six", "Configured membership is unavailable")):
            with self.subTest(case=case):
                w = coverage_presentation_fixture(case)
                before = deepcopy(w)
                html, energy = self.render(w), self.energy(case)
                self.assertIn(expected, energy)
                self.assertNotIn("All recorded changes are flat", energy)
                self.assertNotIn("Every tracked member", energy)
                self.assertNotIn("0 / 0", html)
                self.assertEqual(w, before)
                payload = json.loads(re.search(r'<script\b[^>]*id="cw-data"[^>]*>(.*?)</script>', html, re.S).group(1))
                self.assertEqual(payload, before)

    def test_misclassified_member_is_unconfirmed_not_falsely_absent(self):
        energy = self.energy("misclassified_oil")
        self.assertIn("Member identities disagree with the configured roster", energy)
        self.assertNotIn("This family is missing from the snapshot", energy)
        self.assertRegex(energy, r'data-cw-members-present>\s*1 / 1')
        self.assertRegex(energy, r'data-cw-prices-available>\s*0 / 1')
        self.assertIn("Identity-matched 1-month values", energy)
        self.assertIn("身份核验通过的一个月读数", energy)
        html = self.render(coverage_presentation_fixture("misclassified_oil"))
        self.assertNotIn("0 / 0", html)

    def test_unexpected_family_never_renders_zero_denominator(self):
        html = self.render(coverage_presentation_fixture("unexpected_family"))
        precious = re.findall(r'<article class="panel cw-panel cw-family-reading">(.*?)</article>', html, re.S)[1]
        self.assertIn("Member identities disagree", precious)
        self.assertIn("Expected membership unconfirmed", precious)
        self.assertNotIn("0 / 0", html)
        self.assertNotIn("All recorded changes are flat", precious)


class PresentationSemantics(unittest.TestCase):
    """Synthetic source scenarios; they are not observed market or missing-universe proof."""

    @staticmethod
    def render(raw):
        from jinja2 import Environment, FileSystemLoader, StrictUndefined
        env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1] / "templates"),
                          autoescape=True, undefined=StrictUndefined)
        macro = '{% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}'
        return env.from_string(macro + '{% include "_commodity_decision_workspace.html.j2" %}').render(
            commodity_workspace=build_workspace(raw, expected_members=configured_roster_fixture()))

    def test_oil_question_tracks_positive_negative_flat_unknown_and_absent_evidence(self):
        for value, expected in [(4, "Is oil strength confirmed?"), (-4, "Does the physical market explain weaker oil?"),
                                (0, "What does oil’s physical evidence show?"), (None, "What does oil’s physical evidence show?")]:
            with self.subTest(value=value):
                raw = snapshot()
                raw["members"][0]["chg_1m_pct"] = value
                html = self.render(raw)
                prompt = re.search(r'<aside class="panel cw-panel cw-investigation-prompt">(.*?)</aside>', html, re.S).group(1)
                self.assertIn(expected, prompt)
                if value != 4:
                    self.assertNotIn("Is oil strength confirmed?", prompt)
        raw = snapshot()
        oil = raw["members"].pop(0)
        raw["members"].append(dict(oil, name="natgas"))
        rendered = self.render(raw)
        energy = re.search(r'<article class="panel cw-panel cw-family-reading">(.*?)</article>', rendered, re.S).group(1)
        self.assertIn("Explore available energy evidence", energy)
        self.assertNotIn("data-cw-go-physical", energy)
        prompt = re.search(r'<aside class="panel cw-panel cw-investigation-prompt">(.*?)</aside>', self.render(raw), re.S).group(1)
        self.assertIn("Oil is missing from this snapshot", prompt)
        self.assertIn("data-cw-universe-open", prompt)
        self.assertNotIn("data-cw-go-physical", prompt)

    def test_family_interpretation_names_exceptions_and_keeps_flat_and_null_distinct(self):
        cases = [
            ((4, 3, 2, -1), "Gasoline fell; every other tracked member rose.", "汽油下跌，其余覆盖品种全部上涨。"),
            ((4, -3, -2, -1), "WTI crude rose; every other tracked member fell.", "WTI原油上涨，其余覆盖品种全部下跌。"),
            ((1, 2, 3, 4), "Every tracked member rose.", "覆盖品种全部上涨。"),
            ((-1, -2, -3, -4), "Every tracked member fell.", "覆盖品种全部下跌。"),
            ((0, 0, 0, 0), "All recorded changes are flat.", "记录的价格变化全部持平。"),
            ((None, None, None, None), "Price evidence is unavailable.", "价格证据暂不可用。"),
            ((4, -3, 0, None), "Coverage is incomplete.", "覆盖不完整"),
            ((4, -3, 0, 2), "The family is divided.", "同类品种出现分化"),
        ]
        for values, en, zh in cases:
            with self.subTest(values=values):
                raw = snapshot()
                prototype = raw["members"].pop(0)
                raw["members"] += [dict(deepcopy(prototype), name=name, chg_1m_pct=value)
                                   for name, value in zip(("oil", "natgas", "heating_oil", "gasoline"), values)]
                raw["breadth"]["n_members"] = len(raw["members"])
                verdict = re.findall(r'<p class="cw-family-verdict">(.*?)</p>', self.render(raw), re.S)[0]
                self.assertIn(en, verdict)
                self.assertIn(zh, verdict)


if __name__ == "__main__":
    unittest.main()
