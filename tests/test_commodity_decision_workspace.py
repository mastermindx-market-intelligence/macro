"""Decision-workspace boundary tests. No collectors, production writes or model runs."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from engine.commodity_decision_workspace import build_workspace, validate_condition, number
from engine.commodity_workspace_adapter import read_publication


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
        self.assertEqual(build_workspace(s)["headline"]["en"], "Oil holds. Metals retreat.")
        s["members"].pop()
        self.assertNotIn("Metals retreat", build_workspace(s)["headline"]["en"])
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


if __name__ == "__main__":
    unittest.main()
