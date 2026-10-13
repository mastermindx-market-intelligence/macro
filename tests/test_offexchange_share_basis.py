from __future__ import annotations

"""Hermetic tests for engine.offexchange_share_basis (Q03 research reference).

Synthetic data only, integer positions only, no repo file access.
"""

import copy
import math
import sys

import numpy as np
import pytest

from engine import offexchange_share_basis as sb


def _series(n, split_at, ratio, true_part=0.2, base_vol=1_000_000.0):
    """FINRA raw shares and vendor volume ADJUSTED_AS_OF the last row.

    Truth: participation is ``true_part`` on every session. FINRA reports the
    shares traded that day; the vendor re-based every pre-split row by ``ratio``.
    """
    pos = list(range(n))
    raw_cons = [base_vol if i < split_at else base_vol * ratio for i in pos]
    finra = [true_part * v for v in raw_cons]
    vendor = [v * ratio if i < split_at else v for i, v in zip(pos, raw_cons)]
    return pos, finra, vendor


def _vintage(ticker, actions, vid="v1", attested=True, through=None):
    return sb.FactorVintage(ticker=ticker, vintage_id=vid, source="fixture",
                            actions=tuple(actions), attested=attested,
                            attested_through=through)


# ── req1 ───────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ratio", [2.0, 10.0])
def test_req1_known_split_cannot_change_same_basis_participation(ratio):
    pos, finra, vendor = _series(60, 30, ratio)
    v = _vintage("T", [sb.CorporateAction(30, ratio)])
    r = sb.normalize_participation("T", pos, finra, vendor, v,
                                   denominator_convention=sb.ADJUSTED_AS_OF,
                                   denominator_as_of=59)
    # the mismatch the incumbent sees: pre-split raw reads true/ratio
    assert r.raw_participation[0] == pytest.approx(0.2 / ratio)
    assert r.raw_participation[45] == pytest.approx(0.2)
    # same basis: flat at the truth on both sides
    assert all(c == sb.VALID for c in r.row_class)
    assert np.allclose(r.participation, 0.2, rtol=0, atol=1e-12)
    shift = sb.window_level_shift(r.participation, 30, pre=20, post=20, min_valid=15)
    assert abs(shift) < 1e-12
    raw_shift = sb.window_level_shift(r.raw_participation, 30, pre=20, post=20, min_valid=15)
    assert raw_shift == pytest.approx(math.log(ratio))
    assert r.level_status == "ABSOLUTE"


# ── req2 ───────────────────────────────────────────────────────────────────────
def test_req2_reverse_split_is_distinguished_and_corrected():
    assert sb.classify_ratio(0.1) == sb.REVERSE_SPLIT
    assert sb.classify_ratio(10.0) == sb.FORWARD_SPLIT
    assert sb.classify_ratio(1.0) == sb.NO_OP
    pos, finra, vendor = _series(40, 20, 0.1)
    v = _vintage("R", [sb.CorporateAction(20, 0.1)])
    r = sb.normalize_participation("R", pos, finra, vendor, v,
                                   denominator_convention=sb.ADJUSTED_AS_OF,
                                   denominator_as_of=39)
    assert r.raw_participation[0] == pytest.approx(2.0)   # 0.2 / 0.1: >1, impossible
    assert np.allclose(r.participation, 0.2)


def test_req2_multiple_actions_compose():
    # 2:1 at 10 then 3:1 at 20: pre-10 rows need 6x, 10..19 need 3x
    n = 30
    pos = list(range(n))
    mult = [1.0 if i < 10 else (2.0 if i < 20 else 6.0) for i in pos]
    raw_cons = [1e6 * m for m in mult]
    finra = [0.2 * c for c in raw_cons]
    vendor = [c * (6.0 / m) for c, m in zip(raw_cons, mult)]
    v = _vintage("M", [sb.CorporateAction(10, 2.0), sb.CorporateAction(20, 3.0)])
    r = sb.normalize_participation("M", pos, finra, vendor, v,
                                   denominator_convention=sb.ADJUSTED_AS_OF,
                                   denominator_as_of=29)
    assert r.factor_applied[0] == pytest.approx(6.0)
    assert r.factor_applied[15] == pytest.approx(3.0)
    assert r.factor_applied[25] == pytest.approx(1.0)
    assert np.allclose(r.participation, 0.2)
    assert sb.cumulative_factor(v.actions, 0, 29) == pytest.approx(6.0)


def test_req2_volume_conventions_are_distinguished():
    v = _vintage("C", [sb.CorporateAction(10, 2.0)])
    pos = list(range(20))
    raw_cons = [1e6 if i < 10 else 2e6 for i in pos]
    finra = [0.2 * c for c in raw_cons]
    # RAW vendor: both sides already session-basis -> no factor, flat truth
    raw_r = sb.normalize_participation("C", pos, finra, raw_cons, v,
                                       denominator_convention=sb.RAW_AS_REPORTED)
    assert all(f == 1.0 for f in raw_r.factor_applied)
    assert np.allclose(raw_r.participation, 0.2)
    # ADJUSTED vendor: factor 2 before the action
    adj = [c * 2.0 if i < 10 else c for i, c in enumerate(raw_cons)]
    adj_r = sb.normalize_participation("C", pos, finra, adj, v,
                                       denominator_convention=sb.ADJUSTED_AS_OF,
                                       denominator_as_of=19)
    assert adj_r.factor_applied[0] == 2.0 and np.allclose(adj_r.participation, 0.2)
    # adjusted only as of a position BEFORE the action: no factor for anyone
    early = sb.normalize_participation("C", pos, finra, raw_cons, v,
                                       denominator_convention=sb.ADJUSTED_AS_OF,
                                       denominator_as_of=5)
    assert all(f == 1.0 for f in early.factor_applied)
    # UNKNOWN convention: rows behind a known action are incompatible, not guessed
    unk = sb.normalize_participation("C", pos, finra, adj, v,
                                     denominator_convention=sb.UNKNOWN_CONVENTION)
    assert unk.row_class[:10] == (sb.BASIS_INCOMPATIBLE,) * 10
    assert unk.row_class[10:] == (sb.VALID,) * 10
    assert len({raw_r.result_id, adj_r.result_id, early.result_id, unk.result_id}) == 4
    with pytest.raises(ValueError):
        sb.normalize_participation("C", pos, finra, adj, v,
                                   denominator_convention=sb.ADJUSTED_AS_OF)


def test_req2_ambiguous_ratio_is_a_boundary_not_a_factor():
    for r in (1.253, 1.327, 0.602, 1.04, 1.05):
        assert sb.classify_ratio(r) == sb.AMBIGUOUS
    for r in (1.5, 2.2, 1.25, 0.25, 15.0, 0.05):
        assert sb.classify_ratio(r) != sb.AMBIGUOUS
    pos, finra, vendor = _series(30, 15, 1.253)
    v = _vintage("G", [sb.CorporateAction(15, 1.253)])
    r = sb.normalize_participation("G", pos, finra, vendor, v,
                                   denominator_convention=sb.ADJUSTED_AS_OF,
                                   denominator_as_of=29)
    assert r.row_class[:15] == (sb.BASIS_INCOMPATIBLE,) * 15
    assert r.row_class[15:] == (sb.VALID,) * 15
    assert r.segment[0] != r.segment[20]
    assert r.level_status == "RELATIVE_WITHIN_SEGMENT"
    with pytest.raises(ValueError):
        sb.cumulative_factor(v.actions, 0, 29)


# ── req3 ───────────────────────────────────────────────────────────────────────
def test_req3_revised_factor_changes_identity_and_preserves_earlier_vintage():
    pos, finra, vendor = _series(40, 20, 4.0)
    v1 = _vintage("X", [sb.CorporateAction(20, 2.0)], vid="snap-1")   # wrong early record
    v2 = _vintage("X", [sb.CorporateAction(20, 4.0)], vid="snap-2")   # revised record
    r1 = sb.normalize_participation("X", pos, finra, vendor, v1,
                                    denominator_convention=sb.ADJUSTED_AS_OF,
                                    denominator_as_of=39)
    r2 = sb.normalize_participation("X", pos, finra, vendor, v2,
                                    denominator_convention=sb.ADJUSTED_AS_OF,
                                    denominator_as_of=39)
    assert r1.result_id != r2.result_id
    assert r1.vintage_hash != r2.vintage_hash
    ledger = sb.append_read((), r1)
    ledger2 = sb.append_read(ledger, r2)
    assert ledger == (r1,)                       # earlier ledger value untouched
    assert ledger2 == (r1, r2)                   # earlier vintage preserved
    assert sb.append_read(ledger2, r2) is ledger2  # idempotent
    assert r1.participation[0] == pytest.approx(0.1)
    assert r2.participation[0] == pytest.approx(0.2)
    forged = sb.BasisRead(**{**r2.__dict__, "participation": r1.participation})
    with pytest.raises(ValueError):
        sb.append_read(ledger2, forged)
    with pytest.raises(Exception):
        r1.participation = ()                    # frozen
    # same vintage id but revised content still changes identity
    v3 = _vintage("X", [sb.CorporateAction(20, 4.0)], vid="snap-1")
    r3 = sb.normalize_participation("X", pos, finra, vendor, v3,
                                    denominator_convention=sb.ADJUSTED_AS_OF,
                                    denominator_as_of=39)
    assert r3.result_id not in {r1.result_id, r2.result_id}


# ── req4 ───────────────────────────────────────────────────────────────────────
def test_req4_unknown_factor_is_never_estimated_from_the_jump():
    pos, finra, vendor = _series(60, 30, 10.0)
    v = _vintage("U", [], attested=False)
    r = sb.normalize_participation("U", pos, finra, vendor, v,
                                   denominator_convention=sb.ADJUSTED_AS_OF,
                                   denominator_as_of=59)
    assert r.attestation == sb.UNATTESTED
    assert r.level_status == "NONCOMPARABLE"
    assert all(f is None for f in r.factor_applied)
    assert all(p is None for p in r.participation)
    assert all(c == sb.BASIS_INCOMPATIBLE for c in r.row_class)
    # the observed x10 jump is still visible raw, untouched
    assert r.raw_participation[0] == pytest.approx(0.02)
    assert r.raw_participation[59] == pytest.approx(0.2)
    # an attested record silent past its horizon does not license a factor either
    v_h = _vintage("U", [], attested=True, through=10)
    rh = sb.normalize_participation("U", pos, finra, vendor, v_h,
                                    denominator_convention=sb.ADJUSTED_AS_OF,
                                    denominator_as_of=59)
    assert all(f in (1.0, None) for f in rh.factor_applied)
    assert rh.level_status == "RELATIVE_WITHIN_SEGMENT"
    assert rh.segment[5] != rh.segment[40]


# ── req5 ───────────────────────────────────────────────────────────────────────
def test_req5_denominator_classes_are_separate():
    assert sb.classify_denominator(None) == sb.DENOM_MISSING
    assert sb.classify_denominator(float("nan")) == sb.DENOM_MISSING
    assert sb.classify_denominator(float("inf")) == sb.DENOM_NONFINITE
    assert sb.classify_denominator(-5) == sb.DENOM_NEGATIVE
    assert sb.classify_denominator(0) == sb.DENOM_ZERO
    assert sb.classify_denominator("x") == sb.DENOM_MISSING
    assert sb.classify_denominator(3.0) == sb.VALID
    pos = list(range(8))
    finra = [1.0, 1.0, 1.0, 1.0, 1.0, -1.0, 1.0, 1.0]
    vendor = [None, float("nan"), float("inf"), -10.0, 0.0, 5.0, 5.0, 5.0]
    v = _vintage("D", [sb.CorporateAction(7, 2.0)])
    r = sb.normalize_participation("D", pos, finra, vendor, v,
                                   denominator_convention=sb.UNKNOWN_CONVENTION)
    assert r.row_class == (sb.DENOM_MISSING, sb.DENOM_MISSING, sb.DENOM_NONFINITE,
                           sb.DENOM_NEGATIVE, sb.DENOM_ZERO, sb.NUMERATOR_INVALID,
                           sb.BASIS_INCOMPATIBLE, sb.VALID)
    assert r.counts[sb.DENOM_ZERO] == 1 and r.counts[sb.BASIS_INCOMPATIBLE] == 1
    assert all(p is None for p in r.participation[:7])


# ── req6 ───────────────────────────────────────────────────────────────────────
def test_req6_nonsplit_control_unchanged_and_no_pss_af1_surface():
    rng = np.random.default_rng(6)
    n = 300
    pos = list(range(n))
    vendor = list(rng.uniform(5e5, 2e6, n))
    finra = [float(x) * float(p) for x, p in zip(vendor, rng.uniform(0.1, 0.5, n))]
    f0, v0 = copy.deepcopy(finra), copy.deepcopy(vendor)
    ctl = _vintage("N", [])
    for conv, as_of in ((sb.ADJUSTED_AS_OF, n - 1), (sb.RAW_AS_REPORTED, None),
                        (sb.UNKNOWN_CONVENTION, None)):
        r = sb.normalize_participation("N", pos, finra, vendor, ctl,
                                       denominator_convention=conv,
                                       denominator_as_of=as_of)
        assert r.participation == r.raw_participation          # bitwise equal
        assert r.participation == tuple(a / b for a, b in zip(finra, vendor))
    assert finra == f0 and vendor == v0                        # inputs not mutated
    fields = set(sb.BasisRead.__dataclass_fields__)
    assert not any("short" in f for f in fields)               # no short-ratio surface
    assert sb.contract()["computes_short_ratio"] is False
    assert sb.contract()["emits_direction"] is False


def test_bounded_inputs_and_validation():
    with pytest.raises(ValueError):
        sb.normalize_participation("T", [0, 1], [1.0], [1.0, 1.0], _vintage("T", []),
                                   denominator_convention=sb.RAW_AS_REPORTED)
    with pytest.raises(ValueError):
        sb.normalize_participation("T", [1, 0], [1.0, 1.0], [1.0, 1.0], _vintage("T", []),
                                   denominator_convention=sb.RAW_AS_REPORTED)
    with pytest.raises(ValueError):
        sb.normalize_participation("T", [0], [1.0], [1.0], _vintage("Z", []),
                                   denominator_convention=sb.RAW_AS_REPORTED)
    with pytest.raises(ValueError):
        _vintage("T", [sb.CorporateAction(5, 2.0), sb.CorporateAction(1, 2.0)])
    big = list(range(sb.MAX_ROWS + 1))
    with pytest.raises(ValueError):
        sb.normalize_participation("T", big, big, big, _vintage("T", []),
                                   denominator_convention=sb.RAW_AS_REPORTED)
    assert sb.window_level_shift([1.0] * 5, 3, pre=3, post=3, min_valid=3) is None


def test_no_silent_activation():
    assert sb.RESEARCH_ONLY is True
    assert sb.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    c = sb.contract()
    assert c["research_only"] is True
    assert c["registers"] == () and c["writes"] == ()
    # importing the module registered nothing on itself beyond its definitions
    public = {k for k in vars(sb) if not k.startswith("_")}
    assert not any(k.lower().startswith(("register", "schedule", "activate", "promote"))
                   for k in public)
    # pure: repeated identical calls give identical, deterministic identities
    pos, finra, vendor = _series(20, 10, 2.0)
    v = _vintage("P", [sb.CorporateAction(10, 2.0)])
    a = sb.normalize_participation("P", pos, finra, vendor, v,
                                   denominator_convention=sb.ADJUSTED_AS_OF,
                                   denominator_as_of=19)
    b = sb.normalize_participation("P", pos, finra, vendor, v,
                                   denominator_convention=sb.ADJUSTED_AS_OF,
                                   denominator_as_of=19)
    assert a == b and a.result_id == b.result_id
    assert "engine.offexchange_share_basis" in sys.modules
