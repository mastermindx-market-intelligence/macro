from __future__ import annotations

"""Q09 hermetic tests: one test group per acceptance requirement (req1..req6)
plus the module's own no-silent-activation contract. Synthetic data only,
relative integer clocks, no repository reads."""

import math

import numpy as np
import pytest

from engine import offexchange_venue_concentration as m


# ---- req1: reporting week is never the information-availability date -------

def test_req1_unknown_availability_is_never_admitted_even_after_reporting_week():
    recs = [{"week": 0, "available_at": None}, {"week": 7, "available_at": 21}]
    out = m.admit_weeks(recs, query_at=10)
    assert out["admitted"] == []
    reasons = {r["week"]: r["reason"] for r in out["withheld"]}
    assert reasons == {0: "availability_unknown", 7: "not_yet_available"}


def test_req1_witness_reporting_period_cannot_replace_publication():
    # reporting period 0, published at +21, queried at +9 -> not admissible
    assert m.admissible(9, 21) is False
    assert m.admissible(21, 21) is True
    assert m.admissible(30, None) is False
    assert m.admissible(30, float("nan")) is False


def test_req1_release_identity_qualification_separates_store_bound_from_publisher():
    q = m.qualify_release_identity([
        {"week": 0, "store_first_seen_at": 35, "n_vintages": 1},
        {"week": 7, "store_first_seen_at": None, "n_vintages": 1},
    ])
    assert q["n_with_store_first_seen_upper_bound"] == 1
    assert q["n_with_publisher_release_identity"] == 0
    assert q["vintage_claims_supported"] is False
    assert q["revision_claims_supported"] is False


# ---- req2: staggered tiers are never combined as simultaneously complete ----

def test_req2_t1_only_state_is_partial_and_combination_refused():
    cov = m.coverage_snapshot({"T1": 14, "T2": 28}, query_at=20)
    assert cov["complete"] is False
    assert cov["missing_required_tiers"] == ("T2",)
    with pytest.raises(ValueError):
        m.combine_tier_volumes({"T1": {"A": 1.0}, "T2": {"A": 5.0}}, cov)
    part = m.combine_tier_volumes({"T1": {"A": 1.0}, "T2": {"A": 5.0}}, cov, allow_partial=True)
    assert part["complete"] is False and part["volumes"] == {"A": 1.0}
    assert part["label"] == "partial:T1"


def test_req2_complete_state_uses_latest_tier_time_as_of():
    cov = m.coverage_snapshot({"T1": 14, "T2": 28, "OTCE": 28}, query_at=28)
    assert cov["complete"] is True and cov["as_of"] == 28
    full = m.combine_tier_volumes({"T1": {"A": 1.0}, "T2": {"A": 5.0, "B": 2.0}}, cov)
    assert full["volumes"] == {"A": 6.0, "B": 2.0}


# ---- req3: shares conserve the reported denominator --------------------------

def test_req3_unknown_and_unmapped_mass_is_kept_not_dropped():
    r = m.venue_shares({"X": 60.0, "Y": 20.0, "De Minimis Firms": 10.0, "": 5.0},
                       reported_total=100.0)
    assert math.isclose(r["unknown_mass"], 20.0)
    assert math.isclose(r["unmapped_gap"], 5.0)
    assert math.isclose(sum(r["shares"].values()) + r["unknown_share"], 1.0)
    assert set(r["shares"]) == {"X", "Y"}


def test_req3_reported_total_below_rows_raises():
    with pytest.raises(ValueError):
        m.venue_shares({"X": 60.0, "Y": 50.0}, reported_total=100.0)


def test_req3_incumbent_style_empty_mpid_filter_would_lose_all_nonats_mass():
    # non-ATS rows carry an empty mpid; keying on it would drop everything.
    rows = {"": 100.0}
    r = m.venue_shares(rows)
    assert r["shares"] == {} and math.isclose(r["unknown_share"], 1.0)


# ---- req4: corrections create a new vintage, earlier state preserved ---------

def test_req4_correction_appends_vintage_and_keeps_history():
    led = m.VintageLedger()
    v0 = led.record("wk0", 21, {"hhi": 0.10})
    v1 = led.record("wk0", 40, {"hhi": 0.12}, note="publisher correction")
    assert (v0, v1) == (0, 1)
    hist = led.history("wk0")
    assert [h["payload"]["hhi"] for h in hist] == [0.10, 0.12]
    assert hist[1]["supersedes"] == 0
    assert led.as_of("wk0", 30)["payload"]["hhi"] == 0.10
    assert led.as_of("wk0", 40)["payload"]["hhi"] == 0.12
    assert led.as_of("wk0", 5) is None
    hist[0]["payload"]["hhi"] = 99.0  # returned copies cannot mutate the ledger
    assert led.history("wk0")[0]["payload"]["hhi"] == 0.10
    assert not hasattr(led, "delete") and not hasattr(led, "overwrite")


def test_req4_out_of_order_or_unknown_time_vintage_refused():
    led = m.VintageLedger()
    led.record("wk0", 40, {"hhi": 0.1})
    with pytest.raises(ValueError):
        led.record("wk0", 30, {"hhi": 0.2})
    with pytest.raises(ValueError):
        led.record("wk1", None, {"hhi": 0.2})


# ---- req5: one-venue and equal-venue limits ----------------------------------

@pytest.mark.parametrize("n", [1, 2, 5, 40])
def test_req5_equal_venue_limit(n):
    s = [1.0] * n
    assert math.isclose(m.hhi(s), 1.0 / n)
    eff = m.effective_venue_count(s)
    assert math.isclose(eff["inverse_hhi"], n) and math.isclose(eff["exp_entropy"], n)


def test_req5_one_venue_limit_and_bounds_bracket():
    assert m.hhi([7.0]) == 1.0 and m.entropy([7.0]) == 0.0
    r = m.venue_shares({"A": 50.0, "B": 30.0, "De Minimis Firms": 20.0})
    sep = m.hhi_bounds(r, unknown_may_overlap_known=False)
    ovl = m.hhi_bounds(r, unknown_may_overlap_known=True)
    assert math.isclose(sep["lower"], 0.25 + 0.09)
    assert math.isclose(sep["upper"], 0.25 + 0.09 + 0.04)
    assert math.isclose(ovl["upper"], 0.49 + 0.09)
    assert sep["lower"] <= sep["upper"] <= ovl["upper"]
    no_unknown = m.hhi_bounds(m.venue_shares({"A": 1.0}))
    assert no_unknown["lower"] == no_unknown["upper"] == 1.0


def test_req5_decomposition_is_exact_and_bootstrap_is_block_based():
    d = m.decompose_hhi_change({"A": 50, "B": 50}, {"A": 50, "C": 25, "D": 25})
    assert math.isclose(d["delta"], d["within_common"] + d["entry"] - d["exit"])
    assert (d["n_common"], d["n_entry"], d["n_exit"]) == (1, 2, 1)
    bs = m.moving_block_bootstrap_mean(np.arange(8, dtype=float), block_len=2, n_boot=200, seed=0)
    assert bs["n_units"] == 8 and bs["n_blocks_effective"] == 4
    assert bs["ci_lo"] <= bs["mean"] <= bs["ci_hi"]
    tr, ho = m.chronological_split([0, 1, 2, 3], 3)
    assert tr == [0, 1, 2] and ho == [3]
    with pytest.raises(ValueError):
        m.chronological_split([2, 1, 3], 1)


# ---- req6: no accumulation / net buying / live-print / short-interest output -

@pytest.mark.parametrize("bad", [
    "institutional accumulation in AAA", "net buying by funds", "live print",
    "short interest rising", "smart money", "owner intent",
])
def test_req6_vocabulary_guard_rejects(bad):
    with pytest.raises(ValueError):
        m.assert_no_forbidden_interpretation({"note": [bad]})


@pytest.mark.parametrize("bad", [
    "Short-Interest proxy", "short_interest", "SHORT  INTEREST", "shortinterest",
    "buying pressure in AAA", "selling-pressure", "net_buying", "Net-Purchase flow",
    "accumulated by funds", "accumulate", "Smart_Money", "live-print", "real time print",
    "dark/pool/print", "whale activity", "institutional distribution",
])
def test_req6_vocabulary_guard_catches_separator_and_inflection_variants(bad):
    assert m.forbidden_terms_in(bad)
    with pytest.raises(ValueError):
        m.assert_no_forbidden_interpretation({"outer": {"inner": [("ok", bad)]}})


def test_req6_guard_walks_keys_and_nested_containers():
    with pytest.raises(ValueError):
        m.assert_no_forbidden_interpretation({"net_buying_ratio": 0.5})
    m.assert_no_forbidden_interpretation({"hhi_upper": 0.3, "subject": ["ATS venues (mpid), tiers T1+T2"],
                                          "n": 4, "split_respects_store_clock": True})


def test_req1_split_clock_enforced_refuses_leaky_split():
    origin = 100
    train = [100, 93]
    hold = [101, 108]
    assert m.split_respects_clock(train, hold, origin) is True
    m.require_split_respects_clock(train, hold, origin)
    for bad_train, bad_hold in (
        (train + [101], hold),                      # a training unit seen after origin
        (train, hold + [100]),                      # a holdout unit already seen at origin
        (train, hold + [None]),                     # unknown holdout availability
        (train + [None], hold),                     # unknown training availability
        (train, []),                                # empty holdout
    ):
        assert m.split_respects_clock(bad_train, bad_hold, origin) is False
        with pytest.raises(ValueError, match="REFUSING"):
            m.require_split_respects_clock(bad_train, bad_hold, origin)


def test_req2_tier_gated_combination_excludes_unrequired_tier():
    vols = {"T1": {"A": 60.0, "B": 20.0}, "T2": {"A": 10.0, "C": 10.0}, "OTCE": {"Z": 500.0}}
    avail = {"T1": 28, "T2": 28}
    cov = m.coverage_snapshot(avail, 28, required=("T1", "T2"))
    comb = m.combine_tier_volumes(vols, cov)
    assert comb["complete"] and comb["tiers"] == ("T1", "T2")
    assert comb["volumes"] == {"A": 70.0, "B": 20.0, "C": 10.0}


def test_req5_ratio_bootstrap_matches_inline_reference_draws():
    num = np.array([0.5, 0.2, 0.9, 0.1, 0.4, 0.3, 0.6])
    den = np.array([1.0, 1.2, 0.8, 1.1, 0.9, 1.0, 1.3])
    out = m.moving_block_bootstrap_ratio(num, den, block_len=2, n_boot=500, seed=909)
    rng = np.random.default_rng(909)
    n, b = 7, 2
    starts, k = np.arange(n - b + 1), math.ceil(n / b)
    ref = np.empty(500)
    for i in range(500):
        s = rng.choice(starts, size=k, replace=True)
        idx = (s[:, None] + np.arange(b)[None, :]).ravel()[:n]
        ref[i] = num[idx].mean() / den[idx].mean()
    assert out["ci_lo"] == float(np.quantile(ref, 0.025))
    assert out["ci_hi"] == float(np.quantile(ref, 0.975))
    assert math.isclose(out["ratio"], num.mean() / den.mean())
    assert out["n_blocks_effective"] == 4 and out["n_units"] == 7
    with pytest.raises(ValueError):
        m.moving_block_bootstrap_ratio(num, den[:3], 2, 10, 0)


def test_req6_descriptive_record_passes_guard_and_names_category():
    rec = m.describe_concentration("AAA ATS venues", {"lower": 0.2, "upper": 0.3}, 5)
    assert "venue/reporting category only" in rec["category_note"]
    m.assert_no_forbidden_interpretation(rec)


# ---- module contract: no silent activation -----------------------------------

def test_no_silent_activation_contract():
    assert m.RESEARCH_ONLY is True
    assert m.WIRED is False
    assert m.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    assert "INSUFFICIENT_DATA" in m.__doc__
    public = {n for n in dir(m) if not n.startswith("_") and callable(getattr(m, n))}
    for forbidden in ("register", "activate", "promote", "schedule", "wire", "publish", "gate"):
        assert not any(n.lower().startswith(forbidden) for n in public), forbidden
