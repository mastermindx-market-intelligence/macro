"""Synthetic contract-count checks, including a separately written path oracle."""
from __future__ import annotations

import importlib.util
from itertools import combinations
from pathlib import Path
import unittest

PATH = Path(__file__).with_name("oi_identification.py")
K = None
if PATH.exists():
    spec = importlib.util.spec_from_file_location("oi_bounds_subject", PATH)
    K = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(K)


def all_count_states(volume, initial):
    # State-machine oracle: no closed-form count bounds are used here.
    states = {(initial, 0, 0, 0, 0)}
    for _ in range(volume):
        nxt = set()
        for interest, oo, cc, oc, co in states:
            nxt.add((interest + 1, oo + 1, cc, oc, co))
            if interest > 0:
                nxt.add((interest - 1, oo, cc + 1, oc, co))
                nxt.add((interest, oo, cc, oc + 1, co))
                nxt.add((interest, oo, cc, oc, co + 1))
        states = nxt
    return states


def marginal_oracle(states):
    values = {name: [] for name in ["both_open", "both_close", "mixed", "buyer_open", "seller_open", "opening_sides", "closing_sides"]}
    for _, oo, cc, oc, co in states:
        for name, value in {
            "both_open": oo, "both_close": cc, "mixed": oc + co,
            "buyer_open": oo + oc, "seller_open": oo + co,
            "opening_sides": 2 * oo + oc + co, "closing_sides": 2 * cc + oc + co,
        }.items():
            values[name].append(value)
    return {name: [min(xs), max(xs)] for name, xs in values.items()}


def ordered_oracle(volume, initial, final, removals, selected):
    states = {(initial, 0)}
    for index in range(volume):
        nxt = set()
        mark = int(index in selected)
        for interest, count in states:
            nxt.add((interest + 1, count + mark))
            if interest:
                nxt.add((interest - 1, count))
                nxt.add((interest, count + mark))
                nxt.add((interest, count))
        states = nxt
    hits = [count for interest, count in states if interest == final + removals]
    return [min(hits), max(hits)] if hits else None


class BoundsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(K, "The OI identification reference has not been implemented")

    def test_flat_oi_does_not_identify_buyer_opening(self):
        r = K.exact_bounds(100, 10, 10, removals=0)
        self.assertEqual(r["bounds"]["buyer_open"], [0, 100])
        self.assertEqual(r["bounds"]["opening_sides"], [100, 100])
        self.assertEqual(r["bounds"]["both_open"], [0, 50])

    def test_opening_side_fraction_uses_two_participant_sides(self):
        flat = K.exact_bounds(100, 10, 10, removals=0)
        gain = K.exact_bounds(100, 10, 100, removals=0)
        self.assertEqual(flat["opening_side_fraction"], {"numerator": 1, "denominator": 2})
        self.assertEqual(gain["opening_side_fraction"], {"numerator": 19, "denominator": 20})

    def test_large_oi_gain_is_a_bound_not_a_probability(self):
        r = K.exact_bounds(100, 10, 90, removals=0)
        self.assertEqual(r["bounds"]["buyer_open"], [80, 100])
        self.assertEqual(r["bounds"]["both_open"], [80, 90])
        self.assertIsNone(r["opening_probability"])
        self.assertFalse(r["predictive_authority"])

    def test_large_decline_does_not_identify_closing_prints(self):
        r = K.exact_bounds(100, 100, 20, removals=0)
        self.assertEqual(r["bounds"]["buyer_open"], [0, 20])
        self.assertEqual(r["bounds"]["both_close"], [80, 90])

    def test_zero_start_and_end_require_an_open_and_a_close(self):
        r = K.exact_bounds(2, 0, 0, removals=0)
        self.assertEqual(r["bounds"]["both_open"], [1, 1])
        self.assertEqual(r["bounds"]["both_close"], [1, 1])
        self.assertEqual(r["bounds"]["mixed"], [0, 0])
        self.assertEqual(r["bounds"]["buyer_open"], [1, 1])

    def test_odd_volume_has_parity_constraint(self):
        r = K.exact_bounds(3, 0, 0, removals=0)
        self.assertEqual(r["bounds"]["mixed"], [1, 1])
        self.assertEqual(r["bounds"]["buyer_open"], [1, 2])

    def test_one_mixed_trade_cannot_create_a_position_from_zero(self):
        with self.assertRaises(K.Refusal):
            K.exact_bounds(1, 0, 0, removals=0)

    def test_zero_volume_allows_nontrading_removal(self):
        r = K.exact_bounds(0, 100, 0, removals=100)
        self.assertEqual(r["bounds"]["both_close"], [0, 0])
        self.assertEqual(r["bounds"]["opening_sides"], [0, 0])
        self.assertIsNone(r["opening_side_fraction"])

    def test_removal_changes_the_trading_change(self):
        r = K.exact_bounds(20, 100, 20, removals=80)
        self.assertEqual(r["trade_oi_change"], 0)
        self.assertEqual(r["bounds"]["buyer_open"], [0, 20])
        with self.assertRaises(K.Refusal):
            K.exact_bounds(20, 100, 20, removals=0)

    def test_unknown_removals_are_not_zero(self):
        with self.assertRaises(K.Refusal):
            K.exact_bounds(100, 100, 20, removals=None)

    def test_absent_interest_is_not_zero(self):
        with self.assertRaises(K.Refusal):
            K.exact_bounds(100, 100, None, removals=0)

    def test_counts_are_strict_nonnegative_integers(self):
        for bad in [True, -1, 1.5, "10", float("nan"), float("inf")]:
            with self.subTest(bad=repr(bad)), self.assertRaises(K.Refusal):
                K.exact_bounds(bad, 10, 10, removals=0)

    def test_large_counts_remain_exact(self):
        v = 2 ** 60 + 1
        r = K.exact_bounds(v, 1, 1, removals=0)
        self.assertEqual(r["bounds"]["both_open"], [0, v // 2])
        self.assertEqual(r["bounds"]["mixed"], [1, v])

    def test_subset_count_only_bounds(self):
        r = K.exact_bounds(100, 10, 100, removals=0, subset_count=30)
        self.assertEqual(r["subset_buyer_open_bounds"], [20, 30])
        self.assertEqual(r["subset_basis"], "count_only_unpositioned")

    def test_subset_cannot_exceed_volume(self):
        with self.assertRaises(K.Refusal):
            K.exact_bounds(2, 1, 1, removals=0, subset_count=3)

    def test_known_first_and_last_positions_tighten_bounds(self):
        first = K.ordered_subset_bounds(3, 0, 0, [0], removals=0)
        last = K.ordered_subset_bounds(3, 0, 0, [2], removals=0)
        middle = K.ordered_subset_bounds(3, 0, 0, [1], removals=0)
        self.assertEqual(first["buyer_open_bounds"], [1, 1])
        self.assertEqual(last["buyer_open_bounds"], [0, 0])
        self.assertEqual(middle["buyer_open_bounds"], [0, 1])

    def test_duplicate_or_invalid_subset_indices_refused(self):
        for indices in [[0, 0], [3], [-1], [True], [0.0], None]:
            with self.subTest(indices=indices), self.assertRaises(K.Refusal):
                K.ordered_subset_bounds(3, 1, 1, indices, removals=0)

    def test_ordered_reference_does_not_truncate_large_input(self):
        with self.assertRaises(K.Refusal):
            K.ordered_subset_bounds(257, 1, 1, [], removals=0)

    def test_removal_interval_broadens_instead_of_selecting_a_value(self):
        r = K.removal_interval_bounds(100, 100, 20, removals_low=0, removals_high=80)
        self.assertEqual(r["bounds"]["buyer_open"], [0, 100])
        self.assertEqual(r["feasible_removals"], [0, 80])
        self.assertIsNone(r["opening_probability"])

    def test_bad_removal_interval_refused(self):
        for low, high in [(2, 1), (None, 1), (0, None), (-1, 1), (True, 1)]:
            with self.subTest(low=low, high=high), self.assertRaises(K.Refusal):
                K.removal_interval_bounds(10, 1, 1, removals_low=low, removals_high=high)

    def test_interval_handles_zero_start_infeasible_endpoint(self):
        r = K.removal_interval_bounds(1, 0, 0, removals_low=0, removals_high=1)
        self.assertEqual(r["feasible_removals"], [1, 1])
        self.assertEqual(r["bounds"]["buyer_open"], [1, 1])

    def test_exhaustive_count_bounds_match_admissible_paths(self):
        checked = 0
        for initial in range(4):
            for volume in range(11):
                states = all_count_states(volume, initial)
                for removals in range(5):
                    for final in range(initial + volume + 1):
                        feasible = {s for s in states if s[0] == final + removals}
                        if not feasible:
                            with self.assertRaises(K.Refusal):
                                K.exact_bounds(volume, initial, final, removals=removals)
                        else:
                            r = K.exact_bounds(volume, initial, final, removals=removals)
                            self.assertEqual(r["bounds"], marginal_oracle(feasible), (volume, initial, final, removals))
                        checked += 1
        self.assertGreater(checked, 1000)

    def test_exhaustive_interval_bounds_match_union(self):
        for initial in range(3):
            for volume in range(7):
                states = all_count_states(volume, initial)
                for final in range(initial + volume + 1):
                    for low in range(4):
                        for high in range(low, 5):
                            feasible = {s for s in states if low <= s[0] - final <= high}
                            if not feasible:
                                with self.assertRaises(K.Refusal):
                                    K.removal_interval_bounds(volume, initial, final, removals_low=low, removals_high=high)
                            else:
                                r = K.removal_interval_bounds(volume, initial, final, removals_low=low, removals_high=high)
                                self.assertEqual(r["bounds"], marginal_oracle(feasible), (volume, initial, final, low, high))

    def test_ordered_subset_matches_exhaustive_paths(self):
        for volume in range(6):
            for initial in range(3):
                for count in range(volume + 1):
                    for selection in combinations(range(volume), count):
                        for removals in range(3):
                            for final in range(initial + volume + 1):
                                expected = ordered_oracle(volume, initial, final, removals, set(selection))
                                if expected is None:
                                    with self.assertRaises(K.Refusal):
                                        K.ordered_subset_bounds(volume, initial, final, selection, removals=removals)
                                else:
                                    r = K.ordered_subset_bounds(volume, initial, final, selection, removals=removals)
                                    self.assertEqual(r["buyer_open_bounds"], expected)


if __name__ == "__main__":
    unittest.main()
