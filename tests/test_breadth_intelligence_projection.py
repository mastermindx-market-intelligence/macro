"""Isolated synthetic tests of the stateless group projection.

These unit tests inject the existing pure counter interface for local execution;
the repository CI must also execute an integration test with its real counter.
"""
import copy
import math
import unittest

from engine.breadth_intelligence_projection import project_groups

NOW = "2026-10-30T14:42:00-04:00"
KNOWN = "2026-10-30T14:43:00-04:00"
BEFORE = "2026-10-29T20:00:00Z"


def make_group(**kw):
    v = {"id": "gics:IT", "kind": "sector", "name": "Technology", "source": "GICS",
         "membership_revision": "rev1", "membership_belief_at": BEFORE,
         "rights_status": "display_allowed", "members": ["A", "B", "C", "D", "E"]}
    v.update(kw)
    return v


def counter(key, univ, label, levels, prices):
    adv = dec = unch = above50 = above200 = hi = lo = 0
    b50 = b200 = 0
    for s, p in prices.items():
        t = levels[s]
        if p > t["prev_close"]:
            adv += 1
        elif p < t["prev_close"]:
            dec += 1
        else:
            unch += 1
        if t.get("ma50") is not None:
            b50 += 1
            above50 += p > t["ma50"]
        if t.get("ma200") is not None:
            b200 += 1
            above200 += p > t["ma200"]
        hi += t.get("hi52") is not None and p >= t["hi52"]
        lo += t.get("lo52") is not None and p <= t["lo52"]
    return dict(n=len(prices), adv=adv, dec=dec, unch=unch,
                adv_pct=100*adv/(adv+dec) if adv+dec else None,
                pa50=100*above50/b50 if b50 else None,
                pa200=100*above200/b200 if b200 else None,
                nh=hi, nl=lo)


class Tests(unittest.TestCase):
    def setUp(self):
        self.prices = dict(A=101, B=95, C=100, D=104, E=80)
        self.thresholds = {m: dict(prev_close=100, ma50=99, ma200=98, hi52=110, lo52=70)
                           for m in self.prices}
        self.groups = [make_group()]

    def calc(self, **kw):
        args = dict(groups=self.groups, last_by_symbol=self.prices,
                    thresholds_by_symbol=self.thresholds, source_asof=NOW,
                    known_at=KNOWN, session="rth", upstream_usable=True,
                    aggregate_tier=counter)
        args.update(kw)
        return project_groups(**args)

    def test_source_math_and_non_mutation(self):
        before = copy.deepcopy((self.prices, self.thresholds, self.groups))
        r = self.calc()["groups"][0]
        self.assertEqual((r["adv"], r["dec"], r["unch"]), (2, 2, 1))
        self.assertEqual(r["positive_pct_of_observed"], 40)
        self.assertEqual(r["adv_pct_excluding_unchanged"], 50)
        self.assertEqual(r["pct_above_50"], 60)
        self.assertEqual(r["logical_identification_bounds_pct"], [40, 40])
        self.assertEqual((self.prices, self.thresholds, self.groups), before)

    def test_nonfinite_ma_does_not_pollute_denominator(self):
        levels = copy.deepcopy(self.thresholds)
        levels["C"]["ma50"] = math.nan
        r = self.calc(thresholds_by_symbol=levels)["groups"][0]
        # C's invalid MA is excluded from its denominator, never a negative vote.
        self.assertEqual(r["pct_above_50"], 50)

    def test_missingness_refuses_instead_of_zero(self):
        p = dict(self.prices)
        p.pop("C")
        r = self.calc(last_by_symbol=p)["groups"][0]
        self.assertEqual(r["state"], "unmeasured")
        self.assertEqual(r["unmeasured_reason"], "coverage_insufficient")
        self.assertEqual(r["coverage_pct"], 80)
        self.assertIsNone(r["adv"])

    def test_can_count_partial_only_if_explicit_floor_allows(self):
        p = dict(self.prices)
        p.pop("C")
        r = self.calc(last_by_symbol=p, minimum_coverage_pct=80,
                      minimum_observed=4)["groups"][0]
        self.assertEqual(r["state"], "measured")
        self.assertEqual(r["logical_identification_bounds_pct"], [40, 60])
        self.assertFalse(r["aggregable_with_other_groups"])

    def test_rights_unknown_hides_cohort_count(self):
        r = self.calc(groups=[make_group(rights_status="unknown")])["groups"][0]
        self.assertIsNone(r["eligible_n"])
        self.assertIsNone(r["coverage_pct"])
        self.assertEqual(r["unmeasured_reason"], "rights_unknown")

    def test_rights_denial_hides_cohort_count(self):
        r = self.calc(groups=[make_group(rights_status="not_authorized")])["groups"][0]
        self.assertEqual(r["unmeasured_reason"], "rights_not_authorized")
        self.assertIsNone(r["observed_n"])

    def test_future_belief_refused(self):
        r = self.calc(groups=[make_group(membership_belief_at="2026-10-30T16:00:00-04:00")])["groups"][0]
        self.assertEqual(r["unmeasured_reason"], "future_membership")

    def test_unbound_membership_refused(self):
        r = self.calc(groups=[make_group(membership_revision=None)])["groups"][0]
        self.assertEqual(r["unmeasured_reason"], "unbound_membership")

    def test_unusable_upstream_and_closed_session_refused(self):
        self.assertEqual(self.calc(upstream_usable=False)["groups"][0]["state"], "unmeasured")
        self.assertEqual(self.calc(session="closed")["groups"][0]["state"], "unmeasured")

    def test_empty_not_falsely_full(self):
        r = self.calc(groups=[make_group(members=[])])["groups"][0]
        self.assertEqual(r["unmeasured_reason"], "empty_cohort")

    def test_overlap_is_explicitly_not_aggregable(self):
        r = self.calc(groups=[make_group(), make_group(id="theme:ai", kind="curated_theme")])["groups"]
        self.assertEqual(len(r), 2)
        self.assertTrue(all(v["aggregable_with_other_groups"] is False for v in r))

    def test_duplicate_group_and_member_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate group id"):
            self.calc(groups=[make_group(), make_group()])
        with self.assertRaisesRegex(ValueError, "duplicate member"):
            self.calc(groups=[make_group(members=["A"]*5)])

    def test_price_and_clock_invariants(self):
        p = dict(self.prices)
        p["D"] = math.nan
        self.assertEqual(self.calc(last_by_symbol=p)["groups"][0]["state"], "unmeasured")
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            self.calc(source_asof="2026-10-30T12:00:00")
        with self.assertRaisesRegex(ValueError, "known_at cannot precede"):
            self.calc(known_at="2026-10-29T14:43:00-04:00")

    def test_same_members_in_sector_and_theme_cannot_be_aggregated(self):
        groups = [make_group(), make_group(id="theme:energytech", kind="micro_theme")]
        r = self.calc(groups=groups)["groups"]
        self.assertEqual(r[0]["positive_pct_of_observed"], r[1]["positive_pct_of_observed"])
        self.assertFalse(r[0]["aggregable_with_other_groups"])


if __name__ == "__main__":
    unittest.main()
