"""Synthetic unit and real-consumer tests of the stateless group projection.

The original cases retain their injected pure counter. Added integration cases
use the default live-breadth counter and the accepted per-member qualifier,
without provider I/O or a production source-clock or threshold-basis claim.
"""
import copy
import math
import unittest
from datetime import datetime

from engine.breadth_intelligence_projection import project_groups
from engine.live_breadth import qualify_snapshot_members

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


    def real_calc(self, **kw):
        """Exercise project_groups' actual default counter without a substitute."""
        args = dict(groups=self.groups, last_by_symbol=self.prices,
                    thresholds_by_symbol=self.thresholds, source_asof=NOW,
                    known_at=KNOWN, session="rth", upstream_usable=True)
        args.update(kw)
        return project_groups(**args)

    def test_real_default_counter_and_explicit_none_preserve_denominators(self):
        before = copy.deepcopy((self.prices, self.thresholds, self.groups))
        for options in ({}, {"aggregate_tier": None}):
            with self.subTest(options=options):
                r = self.real_calc(**options)["groups"][0]
                self.assertEqual(r["state"], "measured")
                self.assertEqual((r["adv"], r["dec"], r["unch"]), (2, 2, 1))
                self.assertEqual(r["observed_n"], 5)
                self.assertEqual(r["positive_pct_of_observed"], 40)
                self.assertEqual(r["adv_pct_excluding_unchanged"], 50)
                self.assertEqual(r["pct_above_50"], 60)
                self.assertEqual(r["pct_above_200"], 60)
                self.assertEqual(r["logical_identification_bounds_pct"], [40, 40])
        self.assertEqual((self.prices, self.thresholds, self.groups), before)

    def test_real_counter_filters_invalid_price_and_prior_close(self):
        for field in ("price", "prev_close"):
            for value in (None, True, math.nan, math.inf, -math.inf, 0, -1, "100"):
                with self.subTest(field=field, value=repr(value)):
                    prices = dict(self.prices)
                    levels = copy.deepcopy(self.thresholds)
                    if field == "price":
                        prices["C"] = value
                    else:
                        levels["C"]["prev_close"] = value
                    before = copy.deepcopy((prices, levels))
                    r = self.real_calc(
                        last_by_symbol=prices, thresholds_by_symbol=levels,
                        minimum_coverage_pct=80, minimum_observed=4)["groups"][0]
                    self.assertEqual(r["state"], "measured")
                    self.assertEqual(r["observed_n"], 4)
                    self.assertEqual(r["coverage_pct"], 80)
                    self.assertEqual((r["adv"], r["dec"], r["unch"]), (2, 2, 0))
                    self.assertEqual(r["positive_pct_of_observed"], 50)
                    self.assertEqual(r["adv_pct_excluding_unchanged"], 50)
                    self.assertEqual(r["logical_identification_bounds_pct"], [40, 60])
                    self.assertEqual((prices, levels), before)

    def test_real_counter_excludes_invalid_optional_thresholds(self):
        for value in (None, True, math.nan, math.inf, -math.inf, 0, -1, "99"):
            with self.subTest(value=repr(value)):
                levels = copy.deepcopy(self.thresholds)
                for field in ("ma50", "ma200", "hi52", "lo52"):
                    levels["C"][field] = value
                before = copy.deepcopy(levels)
                r = self.real_calc(thresholds_by_symbol=levels)["groups"][0]
                self.assertEqual((r["adv"], r["dec"], r["unch"]), (2, 2, 1))
                self.assertEqual(r["observed_n"], 5)
                self.assertEqual(r["pct_above_50"], 50)
                self.assertEqual(r["pct_above_200"], 50)
                self.assertEqual((r["new_highs"], r["new_lows"]), (0, 0))
                self.assertEqual(levels, before)

    @staticmethod
    def qualified_cohort_rows():
        members = [f"S{i:04d}" for i in range(1500)]
        quotes = {
            symbol: {
                "price": 101 if i == 0 else 100,
                "source": "polygon",
                "native_quote_identity": {
                    "schema": "native_quote_identity.v1",
                    "vendor": "polygon",
                    "vendor_symbol": symbol,
                    "response_field": "tickers[].ticker",
                },
                "price_basis": "trade" if i % 2 == 0 else "minute",
                "quote_ts": NOW,
                "quote_ts_synthetic": False,
            }
            for i, symbol in enumerate(members)
        }
        return members, quotes

    def qualified_projection(self, members, quotes):
        cutoff = datetime.fromisoformat(KNOWN)
        qualified = qualify_snapshot_members(
            quotes, members, observed_at=cutoff, asof=cutoff,
            session_start=datetime.fromisoformat("2026-10-30T09:30:00-04:00"),
            session_end=datetime.fromisoformat("2026-10-30T16:00:00-04:00"))
        levels = {
            symbol: dict(prev_close=100, ma50=99, ma200=98, hi52=110, lo52=70)
            for symbol in members
        }
        # Deliberately keep a separately supplied, fresh top-level envelope.
        # It must not turn excluded member prices into measured breadth.
        # NOW is not an invented admitted clock when qualification returns none.
        result = self.real_calc(
            groups=[make_group(members=members)],
            last_by_symbol=qualified["last_by_symbol"],
            thresholds_by_symbol=levels, source_asof=NOW)
        return qualified, result

    def assert_unmeasured_counts(self, row, observed_n):
        self.assertEqual(row["state"], "unmeasured")
        self.assertEqual(row["unmeasured_reason"], "coverage_insufficient")
        self.assertEqual(row["eligible_n"], 1500)
        self.assertEqual(row["observed_n"], observed_n)
        for key in (
            "adv", "dec", "unch", "positive_pct_of_observed",
            "adv_pct_excluding_unchanged", "pct_above_50", "pct_above_200",
            "new_highs", "new_lows", "logical_identification_bounds_pct",
        ):
            self.assertIsNone(row[key], key)

    def test_real_qualifier_one_fresh_1499_stale_cannot_create_flat_votes(self):
        members, quotes = self.qualified_cohort_rows()
        for symbol in members[1:]:
            quotes[symbol]["quote_ts"] = "2026-10-30T09:31:00-04:00"
        before = copy.deepcopy(quotes)
        qualified, result = self.qualified_projection(members, quotes)
        self.assertEqual(qualified["qualified_n"], 1)
        self.assertEqual(qualified["last_by_symbol"], {members[0]: 101})
        self.assertEqual(len(qualified["excluded_by_symbol"]), 1499)
        self.assertEqual(set(qualified["excluded_by_symbol"].values()), {"stale_quote"})
        self.assertEqual(qualified["oldest_source_asof"], "2026-10-30T18:42:00+00:00")
        self.assertEqual(qualified["newest_source_asof"], qualified["oldest_source_asof"])
        row = result["groups"][0]
        self.assert_unmeasured_counts(row, 1)
        self.assertEqual(row["coverage_pct"], 0.067)
        self.assertEqual(quotes, before)

    def test_real_qualifier_synthetic_trade_minute_clocks_cannot_create_counts(self):
        members, quotes = self.qualified_cohort_rows()
        for quote in quotes.values():
            # Keep valid trade/minute shapes: this isolates the synthetic flag.
            quote["quote_ts_synthetic"] = True
        qualified, result = self.qualified_projection(members, quotes)
        self.assertEqual(qualified["qualified_n"], 0)
        self.assertEqual(qualified["last_by_symbol"], {})
        self.assertEqual(qualified["source_asof_by_symbol"], {})
        self.assertEqual(len(qualified["excluded_by_symbol"]), 1500)
        self.assertEqual(
            set(qualified["excluded_by_symbol"].values()), {"synthetic_quote_ts"})
        self.assertIsNone(qualified["oldest_source_asof"])
        self.assertIsNone(qualified["newest_source_asof"])
        self.assertEqual(result["source_asof"], NOW)
        row = result["groups"][0]
        self.assert_unmeasured_counts(row, 0)
        self.assertEqual(row["coverage_pct"], 0)

    def test_real_qualifier_fresh_cohort_preserves_unchanged_denominator(self):
        members, quotes = self.qualified_cohort_rows()
        qualified, result = self.qualified_projection(members, quotes)
        self.assertEqual(qualified["qualified_n"], 1500)
        self.assertEqual(qualified["excluded_by_symbol"], {})
        self.assertEqual(len(qualified["source_asof_by_symbol"]), 1500)
        row = result["groups"][0]
        self.assertEqual(row["state"], "measured")
        self.assertEqual((row["eligible_n"], row["observed_n"]), (1500, 1500))
        self.assertEqual(row["coverage_pct"], 100)
        self.assertEqual((row["adv"], row["dec"], row["unch"]), (1, 0, 1499))
        self.assertEqual(row["positive_pct_of_observed"], 0.067)
        self.assertEqual(row["adv_pct_excluding_unchanged"], 100)
        self.assertEqual(row["logical_identification_bounds_pct"], [0.067, 0.067])
        self.assertFalse(row["aggregable_with_other_groups"])


if __name__ == "__main__":
    unittest.main()
