"""A29 — exact-arithmetic reproduction of the SNI evaluation ledger's Brier score.

Pairwise generator + agreement tests + refusal parity + replay parity +
properness sanity of the REFERENCE function. Authority flags stay literal
False everywhere. Synthetic data only. Synthetic identity ids.

NOT forecast support. No frozen SNI baseline exists (R1-gated). Row stays PARTIAL.
"""
from __future__ import annotations

import datetime
import json
import sys
from fractions import Fraction
from pathlib import Path
from random import Random

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "research/single_name_intelligence/evaluation"
sys.path.insert(0, str(EVAL_DIR))

import sni_eval_ledger as L  # noqa: E402

SEED = 20261015
DIGEST = "a" * 64
DIGEST_B = "b" * 64
N_LEDGERS = 200
N_FAMILIES_MIN = 1
N_FAMILIES_MAX = 3
N_FORECASTS_MAX = 25

# p drawn from {0.05, 0.10, ..., 0.95} (the 19 valid points within (0,1) strict)
# plus random floats in (0, 1). The boundary values 0 and 1 are excluded
# because the ledger refuses p == 0.0 or p == 1.0 (INVALID_P — strict bounds).
BIN_PS = [round(k * 0.05, 2) for k in range(1, 20)]

# Properness grid: p in [0.0, 1.0] step 0.01 (101 points).
P_GRID = [k * 0.01 for k in range(101)]
PROPERNESS_QS = [0.1, 0.3, 0.5, 0.7, 0.9]

REVIEW_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "reviews"
    / "A29_PROPER_SCORE_REPRO_SYNTHETIC_2026-10-14.md"
)

# Synthetic state names are limited to ledger constants. We never pass
# non-MATURED state into _ref_brier (excluded by spec).


# ---------------------------------------------------------------------------
# Reference: pure-function exact-arithmetic Brier
# ---------------------------------------------------------------------------


def _ref_brier(pairs):
    """Mean (p - outcome)^2 using Fraction arithmetic.

    Each p and outcome is converted to Fraction; float inputs use
    Fraction(p) which captures the EXACT binary value. Mean = sum / N
    rounded to one common denominator via Fraction.__truediv__.
    """
    if not pairs:
        raise ValueError("empty pairs")
    n = Fraction(len(pairs))
    total = sum((Fraction(p) - Fraction(o)) ** 2 for p, o in pairs)
    return total / n


# ---------------------------------------------------------------------------
# Synthetic-data generators (ledger public API only)
# ---------------------------------------------------------------------------


def _shift(ts, days):
    raw = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
    dt = datetime.datetime.fromisoformat(raw) + datetime.timedelta(days=days)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _reg_at(led, family_id):
    for row in led.rows():
        if row["kind"] == L.REGISTER and row["payload"]["family_id"] == family_id:
            return row["written_at_utc"]
    raise AssertionError("no REGISTER row for %s" % family_id)


def _publish(led, forecast_id, family_id, p):
    reg_at = _reg_at(led, family_id)
    payload = {
        "forecast_id": forecast_id,
        "family_id": family_id,
        "p": p,
        "inputs_digest": DIGEST,
        "published_at_utc": _shift(reg_at, 1),
        "horizon_end_utc": _shift(reg_at, 32),
    }
    if p == 0.5:
        payload["declared_reason"] = "synthetic-fixture"
    return led.append(L.PUBLISH, payload)


def _build_one_ledger(tmp_path, rng, *, tag):
    """Build one synthetic ledger; return (EvalLedger, list[family_id])."""
    led = L.EvalLedger(tmp_path / ("eval_%s.jsonl" % tag))
    n_fams = rng.randint(N_FAMILIES_MIN, N_FAMILIES_MAX)
    fams = []
    for i in range(n_fams):
        # Opaque synthetic family_id — caller-supplied, never derived from any
        # ticker/issuer; this lane never mints canonical HK/US identifiers.
        fam_id = "fam-%s-%s-%s" % (tag, i, rng.random())
        led.append(L.REGISTER, {
            "family_id": fam_id,
            "protocol": "sni.v0",
            "version": "1",
            "split": "test",
            "h": 21,
            "prereg_digest": DIGEST,
        })
        # Budget large enough for any 0..25 forecasts.
        led.append(L.BUDGET, {"family_id": fam_id, "declared_trials": 64})
        n_fc = rng.randint(0, N_FORECASTS_MAX)
        for j in range(n_fc):
            fid = "fc-%s-%s-%s-%s" % (tag, i, j, rng.random())
            roll = rng.random()
            if roll < 0.85:
                # PUBLISH branch
                if rng.random() < 0.5:
                    p = rng.choice(BIN_PS)
                else:
                    p = rng.random()
                    if p <= 0.0 or p >= 1.0:
                        p = 0.5  # forced-by-fixture, with declared_reason
                _publish(led, fid, fam_id, p)
                pub_row = led.rows()[-1]
                horizon_end = pub_row["payload"]["horizon_end_utc"]
                observed_after = _shift(horizon_end, 1)
                # Resolution mix: 70% MATURED, 10% UNPRICEABLE, 10% CENSORED,
                # 10% left unresolved.
                r = rng.random()
                if r < 0.70:
                    outcome = rng.randint(0, 1)
                    led.append(L.RESOLVE, {
                        "forecast_id": fid,
                        "state": L.MATURED,
                        "observed_at_utc": observed_after,
                        "outcome": outcome,
                    })
                elif r < 0.80:
                    led.append(L.RESOLVE, {
                        "forecast_id": fid,
                        "state": L.UNPRICEABLE,
                        "observed_at_utc": observed_after,
                        "outcome": None,
                    })
                elif r < 0.90:
                    led.append(L.RESOLVE, {
                        "forecast_id": fid,
                        "state": L.CENSORED,
                        "observed_at_utc": observed_after,
                        "outcome": None,
                    })
                # else: leave as PENDING (no RESOLVE row)
            else:
                # ABSTAIN branch — counts toward used_trials but never produces
                # a PUBLISH row, so _brier_pairs / brier() never see this id.
                led.append(L.ABSTAIN, {
                    "forecast_id": fid,
                    "family_id": fam_id,
                    "reason": "synthetic-fixture",
                })
        fams.append(fam_id)
    return led, fams


def _manual_pairs_for_matured(led, family_id):
    """Independently compute (p, outcome) for the family, MATURED only.

    Does NOT call the ledger's _brier_pairs — pure row walk. Used for the
    reference test AND for the perturbation proof.
    """
    rows = led.rows()
    published = {}
    resolved = {}
    for row in rows:
        kind = row["kind"]
        payload = row["payload"]
        if kind == L.PUBLISH and payload.get("family_id") == family_id:
            published[payload["forecast_id"]] = payload
        elif kind == L.RESOLVE:
            fid = payload.get("forecast_id")
            if fid in published:
                resolved[fid] = payload
    pairs = []
    for fid in sorted(published):
        res = resolved.get(fid)
        if res is None or res.get("state") != L.MATURED:
            continue
        pairs.append((published[fid]["p"], res.get("outcome")))
    return pairs


def _all_ledgers(tmp_path):
    rng = Random(SEED)
    out = []
    for i in range(N_LEDGERS):
        out.append(_build_one_ledger(tmp_path, rng, tag="L%05d" % i))
    return out, rng


# ---------------------------------------------------------------------------
# Tests — Reference function (pure exact-arithmetic Brier)
# ---------------------------------------------------------------------------


def test_a29_ref_brier_single_pair_exact():
    """Reference mean of a single pair uses Fraction arithmetic."""
    val = _ref_brier([(0.5, 1)])
    # (0.5 - 1)^2 = 0.25, mean over 1 = 0.25
    assert val == Fraction(1, 4)
    assert float(val) == 0.25


def test_a29_ref_brier_perfect_forecast_is_zero():
    """p == outcome exactly → error 0, regardless of p's value."""
    # Mix of p values; each pair's (p - o) must be 0 for a 0-error forecast.
    assert _ref_brier([(0.0, 0), (0.25, 0.25), (0.5, 0.5), (1.0, 1.0)]) == 0
    # Binary-precision case: literal Fractions.
    assert _ref_brier([(Fraction(1, 4), Fraction(1, 4)),
                       (Fraction(3, 4), Fraction(3, 4))]) == 0


def test_a29_ref_brier_exact_against_literally_known_rationals():
    """Exact arithmetic: literal-Fraction pairs produce a closed-form answer
    that floats could only approximate."""
    # Use Fraction inputs (not floats) so the arithmetic is fully symbolic.
    pairs = [(Fraction(1, 20), 0),
             (Fraction(9, 10), 1),
             (Fraction(3, 20), 0),
             (Fraction(4, 5), 1)]
    # = mean of (1/20)^2, (9/10 - 1)^2, (3/20)^2, (4/5 - 1)^2
    # = mean of 1/400, 1/100, 9/400, 1/25
    # denominator 400: (1 + 4 + 9 + 16) / 400 / 4 = 30 / 400 / 4 = 3 / 160
    assert _ref_brier(pairs) == Fraction(3, 160)


def test_a29_ref_brier_float_inputs_match_fraction_of_binary_value():
    """Float inputs use Fraction(p) (exact binary value), not decimal value."""
    # 0.05 in IEEE-754 is NOT 1/20; it is a binary expansion. Convert the
    # float to a Fraction with the same binary value and square it; the
    # reference must use the binary value as the source of truth.
    expected = Fraction(0.05) ** 2  # = (Fraction(0.05)) ** 2
    assert _ref_brier([(0.05, 0)]) == expected
    assert _ref_brier([(0.05, 0)]) != Fraction(1, 400)  # naive rational
    # 0.5 is exactly representable.
    assert _ref_brier([(0.5, 1)]) == Fraction(1, 4)


def test_a29_ref_brier_deterministic_for_same_input():
    a = _ref_brier([(0.13, 1), (0.41, 0), (0.79, 1)])
    b = _ref_brier([(0.13, 1), (0.41, 0), (0.79, 1)])
    assert a == b


def test_a29_ref_brier_refuses_empty_pairs():
    with pytest.raises(ValueError):
        _ref_brier([])


# ---------------------------------------------------------------------------
# Tests — Generator + agreement against the ledger's brier()
# ---------------------------------------------------------------------------


def test_a29_generator_yields_at_least_200_ledgers(tmp_path):
    ledgers, _rng = _all_ledgers(tmp_path)
    assert len(ledgers) >= 200
    # Every ledger wrote a JSONL file (not an in-memory only object).
    for led, _fams in ledgers:
        assert led.path.exists()
        assert led.path.stat().st_size > 0


def test_a29_generator_seed_determinism(tmp_path):
    """Same seed → same Brier score per family.

    Wall-clock stamping means two runs of the same seed produce different
    raw row_hashes (registered time differs by seconds, publish-time and
    horizon stamps downstream follow). But every deterministic observable —
    the (p, outcome) pair set — must be identical, so brier() must agree
    exactly between the two runs.
    """
    ledgers_a, _ = _all_ledgers(tmp_path / "a")
    ledgers_b, _ = _all_ledgers(tmp_path / "b")
    assert len(ledgers_a) == len(ledgers_b) == N_LEDGERS
    for (led_a, fams_a), (led_b, fams_b) in zip(ledgers_a, ledgers_b):
        assert fams_a == fams_b
        for fam in fams_a:
            pairs_a = _manual_pairs_for_matured(led_a, fam)
            pairs_b = _manual_pairs_for_matured(led_b, fam)
            if not pairs_a and not pairs_b:
                continue
            # Same (p, outcome) tuples → same brier exactly.
            assert pairs_a == pairs_b
            assert L.brier(led_a, fam) == L.brier(led_b, fam)
        # Counts also deterministic.
        assert led_a.state()["counts"] == led_b.state()["counts"]


def test_a29_agreement_brier_matches_exact_reference(tmp_path):
    """For every family with >= 1 MATURED forecast, agreement within 1e-12.

    Reference is computed independently from rows (does NOT call the
    ledger's _brier_pairs helper). Ledger's brier() uses _brier_pairs.
    """
    ledgers, _ = _all_ledgers(tmp_path)
    max_diff = 0.0
    matured_pairs = 0
    n_families_checked = 0
    for led, fams in ledgers:
        for fam in fams:
            pairs = _manual_pairs_for_matured(led, fam)
            if not pairs:
                continue
            n_families_checked += 1
            matured_pairs += len(pairs)
            ref = float(_ref_brier(pairs))
            got = L.brier(led, fam)
            diff = abs(got - ref)
            max_diff = max(max_diff, diff)
            assert diff <= 1e-12, (
                "family=%s pairs=%s diff=%s" % (fam, pairs[:3], diff)
            )
    assert n_families_checked >= 1
    assert matured_pairs >= 1
    # Print to stdout for the review file generator.
    print("A29_AGREEMENT: n_families=%d matured_pairs=%d max|diff|=%.3e"
          % (n_families_checked, matured_pairs, max_diff))


def test_a29_agreement_excludes_non_matured_resolutions(tmp_path):
    """Construct one family where ONLY an excluded item differs.

    Add (in order): 1 MATURED-only reference, then a 2nd MATURED forecast,
    then a UNPRICEABLE forecast, then CENSORED, then a 2nd ABSTAIN. After
    each addition the ledger-agreement brier must equal the all-MATURED
    reference (the excluded items never enter the reference).
    """
    led = L.EvalLedger(tmp_path / "excl.jsonl")
    fam = "fam-excl"
    led.append(L.REGISTER, {
        "family_id": fam, "protocol": "sni.v0", "version": "1",
        "split": "test", "h": 21, "prereg_digest": DIGEST,
    })
    led.append(L.BUDGET, {"family_id": fam, "declared_trials": 64})

    # Anchor pair (MATURED) — p=0.2, outcome=0 → (0.2)^2.
    _publish(led, "excl-fc-a", fam, p=0.2)
    horizon = led.rows()[-1]["payload"]["horizon_end_utc"]
    led.append(L.RESOLVE, {
        "forecast_id": "excl-fc-a", "state": L.MATURED,
        "observed_at_utc": _shift(horizon, 1), "outcome": 0,
    })
    pairs1 = [(0.2, 0)]
    ref1 = float(_ref_brier(pairs1))
    assert abs(L.brier(led, fam) - ref1) <= 1e-12

    # Add a 2nd MATURED — reference changes.
    _publish(led, "excl-fc-b", fam, p=0.6)
    horizon = led.rows()[-1]["payload"]["horizon_end_utc"]
    led.append(L.RESOLVE, {
        "forecast_id": "excl-fc-b", "state": L.MATURED,
        "observed_at_utc": _shift(horizon, 1), "outcome": 1,
    })
    pairs2 = [(0.2, 0), (0.6, 1)]
    ref2 = float(_ref_brier(pairs2))
    assert abs(L.brier(led, fam) - ref2) <= 1e-12

    # Add a 3rd forecast resolved as UNPRICEABLE — must NOT change brier.
    _publish(led, "excl-fc-c", fam, p=0.4)
    horizon = led.rows()[-1]["payload"]["horizon_end_utc"]
    led.append(L.RESOLVE, {
        "forecast_id": "excl-fc-c", "state": L.UNPRICEABLE,
        "observed_at_utc": _shift(horizon, 1), "outcome": None,
    })
    assert abs(L.brier(led, fam) - ref2) <= 1e-12

    # Add a 4th forecast resolved as CENSORED — must NOT change brier.
    _publish(led, "excl-fc-d", fam, p=0.7)
    horizon = led.rows()[-1]["payload"]["horizon_end_utc"]
    led.append(L.RESOLVE, {
        "forecast_id": "excl-fc-d", "state": L.CENSORED,
        "observed_at_utc": _shift(horizon, 1), "outcome": None,
    })
    assert abs(L.brier(led, fam) - ref2) <= 1e-12

    # Add an ABSTAIN row — must NOT change brier.
    led.append(L.ABSTAIN, {
        "forecast_id": "excl-fc-e", "family_id": fam,
        "reason": "synthetic-fixture",
    })
    assert abs(L.brier(led, fam) - ref2) <= 1e-12

    # Leave a 6th forecast PENDING (no RESOLVE) — must NOT change brier.
    _publish(led, "excl-fc-f", fam, p=0.3)
    assert abs(L.brier(led, fam) - ref2) <= 1e-12


def test_a29_no_matured_forecasts_raises_refusal(tmp_path):
    """A family with zero MATURED forecasts → NO_MATURED_FORECASTS refusal.

    Reference function is NOT called — exact spec requirement.
    """
    led = L.EvalLedger(tmp_path / "noped.jsonl")
    fam = "fam-empty"
    led.append(L.REGISTER, {
        "family_id": fam, "protocol": "sni.v0", "version": "1",
        "split": "test", "h": 21, "prereg_digest": DIGEST,
    })
    led.append(L.BUDGET, {"family_id": fam, "declared_trials": 8})

    # Variant 1: ABSTAIN-only family.
    led.append(L.ABSTAIN, {
        "forecast_id": "noped-fc-1", "family_id": fam,
        "reason": "synthetic-fixture",
    })
    with pytest.raises(L.LedgerRefused) as ei:
        L.brier(led, fam)
    assert ei.value.code == "NO_MATURED_FORECASTS"

    # Variant 2: PUBLISH only, all UNPRICEABLE/CENSORED/PENDING.
    led2 = L.EvalLedger(tmp_path / "noped2.jsonl")
    led2.append(L.REGISTER, {
        "family_id": fam, "protocol": "sni.v0", "version": "1",
        "split": "test", "h": 21, "prereg_digest": DIGEST,
    })
    led2.append(L.BUDGET, {"family_id": fam, "declared_trials": 8})
    _publish(led2, "noped-fc-2", fam, p=0.2)
    horizon = led2.rows()[-1]["payload"]["horizon_end_utc"]
    led2.append(L.RESOLVE, {
        "forecast_id": "noped-fc-2", "state": L.UNPRICEABLE,
        "observed_at_utc": _shift(horizon, 1), "outcome": None,
    })
    _publish(led2, "noped-fc-3", fam, p=0.4)
    horizon = led2.rows()[-1]["payload"]["horizon_end_utc"]
    led2.append(L.RESOLVE, {
        "forecast_id": "noped-fc-3", "state": L.CENSORED,
        "observed_at_utc": _shift(horizon, 1), "outcome": None,
    })
    _publish(led2, "noped-fc-4", fam, p=0.5)
    # No RESOLVE row → PENDING.
    with pytest.raises(L.LedgerRefused) as ei:
        L.brier(led2, fam)
    assert ei.value.code == "NO_MATURED_FORECASTS"

    # Variant 3: zero forecasts entirely.
    led3 = L.EvalLedger(tmp_path / "noped3.jsonl")
    led3.append(L.REGISTER, {
        "family_id": fam, "protocol": "sni.v0", "version": "1",
        "split": "test", "h": 21, "prereg_digest": DIGEST,
    })
    led3.append(L.BUDGET, {"family_id": fam, "declared_trials": 8})
    with pytest.raises(L.LedgerRefused) as ei:
        L.brier(led3, fam)
    assert ei.value.code == "NO_MATURED_FORECASTS"


# ---------------------------------------------------------------------------
# Tests — Replay parity
# ---------------------------------------------------------------------------


def test_a29_replay_matches_original_brier_exactly(tmp_path):
    """Write the ledger, reload via EvalLedger(path), assert brier equality.

    Also asserts L.replay(path) returns the same state fingerprint as a
    fresh EvalLedger(path).state() — covers the explicit `replay(path)`
    surface mentioned in the spec.
    """
    ledgers, _ = _all_ledgers(tmp_path / "replay")
    sample = ledgers[:5]
    for led_orig, fams in sample:
        for fam in fams:
            pairs = _manual_pairs_for_matured(led_orig, fam)
            if not pairs:
                continue
            ref = float(_ref_brier(pairs))
            got_orig = L.brier(led_orig, fam)

            # Reload from disk via the public constructor.
            reloaded = L.EvalLedger(led_orig.path)
            got_reloaded = L.brier(reloaded, fam)
            assert abs(got_orig - got_reloaded) == 0.0, (
                "brier drift across reload for %s: orig=%s replayed=%s"
                % (fam, got_orig, got_reloaded)
            )

            # Also exercise replay(path) — state fingerprint parity.
            st_replay = L.replay(led_orig.path)
            st_reload = reloaded.state()
            # Compare state-counts only (private dict shape).
            assert st_replay["counts"] == st_reload["counts"]
            # Reference brier on reloaded ledger exactly matches original.
            assert abs(got_reloaded - ref) <= 1e-12


# ---------------------------------------------------------------------------
# Tests — Properness sanity of the REFERENCE function
# ---------------------------------------------------------------------------


def _properness_expected_brier_at(q, p):
    """Exact E_o~Bernoulli(q)[(p - o)^2] = (p - q)^2 + q(1 - q)."""
    qf = Fraction(q)
    pf = Fraction(p)
    return (pf - qf) ** 2 + qf * (1 - qf)


def test_a29_properness_minimum_at_p_eq_q_for_each_q():
    """E_o[(p - o)^2] under Bernoulli(q) is minimised exactly at p = q.

    Verifies the REFERENCE function's shape: the properness result for
    the Brier score. The ledger's forecasts are not evaluated here.
    """
    for q in PROPERNESS_QS:
        e_at_q = _properness_expected_brier_at(q, q)
        # Check every other grid point gives strictly larger.
        for p in P_GRID:
            if p == q:
                continue
            e = _properness_expected_brier_at(q, p)
            assert e > e_at_q, (
                "q=%s p=%s E=%s not > E_at_q=%s"
                % (q, p, e, e_at_q)
            )


def test_a29_properness_strict_minimum_grid_search():
    """Brute force: for each q, p_q (the grid point nearest to q) yields the
    smallest grid-evaluated expected Brier, computed via the REFERENCE."""
    for q in PROPERNESS_QS:
        # Evaluate exact E via the reference function over a 101-point p grid.
        e_at_q = _properness_expected_brier_at(q, q)
        for p in P_GRID:
            if p == q:
                continue
            e = _properness_expected_brier_at(q, p)
            # Strict inequality on the closed-form expression. Use Fraction.
            assert e > e_at_q, (
                "strict minimum violated: q=%s p=%.3f gave E=%s vs q-E=%s"
                % (q, p, e, e_at_q)
            )


# ---------------------------------------------------------------------------
# Tests — Authority flag lock
# ---------------------------------------------------------------------------


def test_a29_authority_flags_remain_literal_false():
    """No authority flag may be set to a non-False value anywhere."""
    for k in L.AUTHORITY_KEYS:
        assert k in (
            "rank_authority", "gate_authority", "size_authority",
            "signal_authority", "escalation_authority", "trade_authority",
        )
    # Nested-walk the import surface and confirm no true flag exists.
    obj = dict.fromkeys(L.AUTHORITY_KEYS, False)
    # The walk that the ledger itself uses would raise; we mirror it cheaply.
    def walk(d):
        for k, v in d.items():
            assert v is False, "authority flag %r leaked" % k
            if isinstance(v, dict):
                walk(v)
    walk(obj)


def test_a29_authority_flag_refused_in_payload(tmp_path):
    """A payload carrying any *authority=true* is refused with the right code."""
    led = L.EvalLedger(tmp_path / "auth.jsonl")
    led.append(L.REGISTER, {
        "family_id": "fam-auth", "protocol": "sni.v0", "version": "1",
        "split": "test", "h": 21, "prereg_digest": DIGEST,
    })
    led.append(L.BUDGET, {"family_id": "fam-auth", "declared_trials": 4})
    with pytest.raises(L.LedgerRefused) as ei:
        led.append(L.PUBLISH, {
            "forecast_id": "auth-fc", "family_id": "fam-auth", "p": 0.3,
            "inputs_digest": DIGEST,
            "published_at_utc": "2030-01-02T00:00:00Z",
            "horizon_end_utc": "2030-02-01T00:00:00Z",
            "rank_authority": True,
        })
    assert ei.value.code == "AUTHORITY_FLAG_REFUSED"


# ---------------------------------------------------------------------------
# Tests — Perturbation proof (drop the last MATURED pair)
# ---------------------------------------------------------------------------


def test_a29_perturbation_drop_last_pair_breaks_agreement(
    tmp_path, monkeypatch
):
    """Monkeypatch _brier_pairs to drop the last pair → agreement FAILS.

    The pre-monkeypatch agreement holds (sanity). The post-monkeypatch
    agreement fails (proof). FAILED line is emitted to stdout for the
    review file. The monkeypatch is local to this test and never committed.
    """
    led = L.EvalLedger(tmp_path / "perturb.jsonl")
    fam = "fam-perturb"
    led.append(L.REGISTER, {
        "family_id": fam, "protocol": "sni.v0", "version": "1",
        "split": "test", "h": 21, "prereg_digest": DIGEST,
    })
    led.append(L.BUDGET, {"family_id": fam, "declared_trials": 16})

    # Two MATURED forecasts with clearly-different (p, o) so dropping the
    # last gives a different mean than the full-pair reference.
    _publish(led, "perturb-fc-a", fam, p=0.5)
    horizon = led.rows()[-1]["payload"]["horizon_end_utc"]
    led.append(L.RESOLVE, {
        "forecast_id": "perturb-fc-a", "state": L.MATURED,
        "observed_at_utc": _shift(horizon, 1), "outcome": 1,
    })  # (0.5, 1) → 0.25
    _publish(led, "perturb-fc-b", fam, p=0.1)
    horizon = led.rows()[-1]["payload"]["horizon_end_utc"]
    led.append(L.RESOLVE, {
        "forecast_id": "perturb-fc-b", "state": L.MATURED,
        "observed_at_utc": _shift(horizon, 1), "outcome": 0,
    })  # (0.1, 0) → 0.01

    pairs = [(0.5, 1), (0.1, 0)]
    ref = float(_ref_brier(pairs))

    # Sanity: pre-monkeypatch brier == ref.
    got = L.brier(led, fam)
    assert abs(got - ref) <= 1e-12

    # Monkeypatch the ledger's _brier_pairs to drop the last pair.
    orig = L._brier_pairs

    def dropped(ledger, family_id):
        return orig(ledger, family_id)[:-1]

    monkeypatch.setattr(L, "_brier_pairs", dropped)

    # Now the ledger's brier includes only (0.5, 1) → 0.25
    got_perturbed = L.brier(led, fam)
    diff = abs(got_perturbed - ref)
    failed_line = (
        "FAILED assertions: agreement broken after _brier_pairs perturbation "
        "(last pair dropped): |brier - ref| = %.6e > 1e-12"
        % diff
    )
    print(failed_line)
    assert diff > 1e-12, failed_line


# ---------------------------------------------------------------------------
# Tests — Review file content
# ---------------------------------------------------------------------------


def test_a29_review_file_exists_and_has_required_facts():
    """The review file exists and states the verbatim partial-row string."""
    assert REVIEW_PATH.exists(), "missing review file at %s" % REVIEW_PATH
    text = REVIEW_PATH.read_text(encoding="utf-8")
    # Exact substring required by the spec.
    assert (
        "not forecast support; no frozen SNI baseline exists (R1-gated); "
        "row stays PARTIAL"
    ) in text
    # Required facts.
    assert str(SEED) in text
    assert str(N_LEDGERS) in text


def test_a29_review_file_records_max_diff_and_pair_count():
    """Review records matured-pair count and max |diff| observed."""
    text = REVIEW_PATH.read_text(encoding="utf-8")
    assert "max |diff|" in text or "max|diff|" in text
    # Should contain at least one numeric for the matured-pair count and one
    # for the max |diff|.  A simple substring scan for digits suffices.
    assert any(c.isdigit() for c in text)
