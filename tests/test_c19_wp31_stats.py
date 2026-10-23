"""C19 WP31 STATS lane — synthetic tests for scripts/c19_wp31_stats.py.

Synthetic episode dicts only (prereg §0-§6 shapes, invented values): no network,
no data/ read, no real EPS/price/return/label value for AAPL, DHI, PHM, KBH or TOL,
no trial ledger. Every number below is hand-constructible from the helper.
"""
from __future__ import annotations

import copy
from fractions import Fraction

import pytest

from scripts import c19_wp31_stats as st

CUTOFF = "2026-10-16T20:00:00Z"          # a Friday 16:00 ET scheduled close, as UTC
T_REL = "2026-10-20T12:05:00Z"           # Tuesday's release, after the cutoff
FRESH_K = "2026-10-14T21:00:00Z"         # cutoff - ~2 days: inside STALE_DAYS(4)
ACCESSION = "0000032019-26-000123"      # synthetic accession id, not a real filing


def episode(**over) -> dict:
    """A fully backed episode: K-backed AND S-backed, A2 = A1 = +1, A2[-K] = A0 = -1.

    Nested overrides pass a partial dict, e.g. ``k={"average": None}``, and are
    merged one level deep so a test can change a single field.
    """
    base = {
        "issuer": "DHI",
        "cluster": "HOMEBUILDERS",
        "q": "2026Q4",
        "period_end": "2026-09-30",
        "t_rel": T_REL,
        "cutoff": CUTOFF,
        "status": "ELIGIBLE",
        "not_evaluable_reason": None,
        "label": 1,
        "k": {"average": 2.10, "year_ago": 2.00, "observed_at": FRESH_K,
              "expectation_state": "CURRENT", "identity_status": "CHECKED",
              "rights_class": "UNKNOWN", "attempt_status": "success",
              "period_end": "2026-09-30", "abstain_reason": None,
              "record_ids": ["K-1", "K-2"]},
        "s": {"q_minus_1_resolved": True, "source_sha256": "sha-synthetic-s",
              "generation_id": "gen-1", "record_ids": ["S-1", "S-2"]},
        "a0": {"sign": -1, "period": "2026Q3", "accession": ACCESSION,
               "accepted_at": "2026-07-21T20:05:00Z"},
    }
    for nested in ("k", "s", "a0"):
        value = over.pop(nested, None)
        if isinstance(value, dict):
            merged = dict(base[nested])
            merged.update(value)
            base[nested] = merged
        elif value is not None:
            base[nested] = value
    base.update(over)
    return base


def unbacked_k(ep: dict) -> dict:
    """Make A1 abstain (period_mismatch), so A2 falls through to the S leg."""
    out = copy.deepcopy(ep)
    out["k"] = {**out["k"], "average": None, "year_ago": None,
                "abstain_reason": "period_mismatch"}
    return out


def row(label: int, a0_sign: int, k_emits: bool, k_sign: int = 1, **over) -> dict:
    """One common-support row: A2[-K] = a0_sign; A2 = k_sign when the K leg emits,
    else A2 falls through to a0_sign."""
    ep = episode(label=label, a0={"sign": a0_sign},
                 k={"average": 2.10 if k_sign > 0 else 1.90, "year_ago": 2.00}, **over)
    if not k_emits:
        return unbacked_k(ep)
    return ep


# --------------------------------------------------------------------------- #
# constants
# --------------------------------------------------------------------------- #
def test_constants_match_prereg():
    assert st.ARMS == ("A0", "A1", "A2", "A2-K", "A2-S")
    assert st.FAMILY == "c19_wp31_incremental_information"
    assert st.BUDGET == 6
    assert st.HEDGE == {"AAPL": "XLK", "HOMEBUILDERS": "XHB"}
    assert st.COST_PER_EPISODE == pytest.approx(0.0040)
    assert st.NONBLOCKING_RIGHTS == frozenset({"UNKNOWN"})
    assert st.USEFUL_EFFECT_EXACT == Fraction(1, 10)
    assert issubclass(st.AblationError, RuntimeError)
    assert st.Emission == tuple[int | None, str | None]


# --------------------------------------------------------------------------- #
# A0
# --------------------------------------------------------------------------- #
def test_a0_emits_stored_prior_filing_sign():
    assert st.arm_a0(episode(a0={"sign": 1})) == (1, None)
    assert st.arm_a0(episode(a0={"sign": -1})) == (-1, None)


def test_a0_abstains_without_prior_filing():
    assert st.arm_a0(episode(a0={"sign": None})) == (None, "no_prior_filing")


# --------------------------------------------------------------------------- #
# A1
# --------------------------------------------------------------------------- #
def test_a1_abstain_reason_wins_over_values():
    assert st.arm_a1(episode(k={"abstain_reason": "period_mismatch"})) == (
        None, "period_mismatch")
    assert st.arm_a1(episode(k={"abstain_reason": "query_refusal:rights_denied",
                                 "average": 3.0, "year_ago": 2.0})) == (
        None, "query_refusal:rights_denied")


def test_a1_abstains_when_a_value_is_missing():
    assert st.arm_a1(episode(k={"average": None})) == (None, "k_missing")
    assert st.arm_a1(episode(k={"year_ago": None})) == (None, "k_missing")


def test_a1_abstains_on_equal_values():
    assert st.arm_a1(episode(k={"average": 2.0, "year_ago": 2.0})) == (None, "k_equal")


def test_a1_signs_both_directions():
    assert st.arm_a1(episode(k={"average": 2.05, "year_ago": 2.00})) == (1, None)
    assert st.arm_a1(episode(k={"average": 1.95, "year_ago": 2.00})) == (-1, None)


# --------------------------------------------------------------------------- #
# K-backed / S-backed (prereg §4 gates)
# --------------------------------------------------------------------------- #
def test_k_backed_stale_by_one_second():
    fresh = episode(k={"observed_at": "2026-10-12T20:00:00Z"})   # == cutoff - 4d
    stale = episode(k={"observed_at": "2026-10-12T19:59:59Z"})   # cutoff - 4d - 1s
    assert st.k_backed(fresh) is True
    assert st.k_backed(stale) is False


@pytest.mark.parametrize("field,value", [
    ("expectation_state", "STALE"),
    ("identity_status", "UNCHECKED"),
    ("rights_class", "RIGHTS_BLOCKED"),
    ("rights_class", "DISPLAY_ONLY"),
    ("rights_class", "blocked"),
    ("rights_class", "restricted"),
    ("rights_class", " unlicensed "),
    ("rights_class", "public"),
    ("rights_class", "LICENSED"),
    ("rights_class", "MIXED:PUBLIC,UNKNOWN"),
    ("rights_class", "MIXED:DISPLAY_ONLY,UNKNOWN"),
    ("attempt_status", "error"),
    ("attempt_status", None),
])
def test_k_backed_false_on_each_gate(field, value):
    assert st.k_backed(episode(k={field: value})) is False


def test_every_k_surface_blocked_label_is_blocked():
    # prereg §10 A1: an allow-list; every label the engine itself blocks or demotes to
    # display-only must also fail the gate, in any case and with surrounding space.
    from engine.k3e_expectation_surface import BLOCKED_RIGHTS, DISPLAY_ONLY_RIGHTS
    labels = BLOCKED_RIGHTS | DISPLAY_ONLY_RIGHTS
    assert labels
    for label in labels:
        assert st.rights_blocked(label) is True
        assert st.rights_blocked(f" {label.lower()} ") is True
        assert "UNKNOWN" not in label.upper().split(":")


@pytest.mark.parametrize("value", ["UNKNOWN", "unknown", " Unknown ", None, ""])
def test_k_backed_true_only_on_unknown_rights(value):
    # UNKNOWN is the producer's labeled absence (engine: SOURCE_USE_RIGHTS_UNKNOWN), not a block.
    assert st.rights_blocked(value) is False
    assert st.k_backed(episode(k={"rights_class": value})) is True


def test_unrecognized_rights_label_fails_closed():
    # A deny-list failed open on "public"; the allow-list blocks any label nobody anticipated.
    for value in ("public", "LICENSED", "OPEN", "MIXED:PUBLIC,UNKNOWN", "UNKNOWN_PLUS"):
        assert st.rights_blocked(value) is True
        assert st.k_backed(episode(k={"rights_class": value})) is False


def test_k_backed_false_when_a1_abstains():
    assert st.k_backed(unbacked_k(episode())) is False
    assert st.k_backed(episode(k={"observed_at": None})) is False
    assert st.k_backed(episode(cutoff=None)) is False


def test_s_backed_false_on_unresolved_q_minus_1():
    assert st.s_backed(episode(s={"q_minus_1_resolved": False})) is False
    assert st.s_backed(episode(s={"q_minus_1_resolved": None})) is False


def test_s_backed_false_on_empty_or_missing_sha():
    assert st.s_backed(episode(s={"source_sha256": ""})) is False
    assert st.s_backed(episode(s={"source_sha256": None})) is False


def test_s_backed_requires_a0_to_emit():
    assert st.s_backed(episode(a0={"sign": None})) is False
    assert st.s_backed(episode()) is True


# --------------------------------------------------------------------------- #
# A2 and the two ablations (prereg §4 precedence)
# --------------------------------------------------------------------------- #
def test_a2_prefers_k_then_s_then_abstains():
    both = episode()                                            # K-backed + S-backed
    assert st.arm_a2(both) == st.arm_a1(both) == (1, None)
    s_only = unbacked_k(both)                                   # S-backed only
    assert st.arm_a2(s_only) == st.arm_a0(s_only) == (-1, None)
    neither = unbacked_k(episode(a0={"sign": None}))            # nothing backs A2
    assert st.arm_a2(neither) == (None, "no_backing")


def test_a2_minus_k_is_a0_when_s_backed():
    assert st.arm_a2_minus_k(episode()) == (-1, None)
    assert st.arm_a2_minus_k(episode(a0={"sign": None})) == (None, "no_s_backing")


def test_a2_minus_s_is_a1_when_k_backed():
    assert st.arm_a2_minus_s(episode()) == (1, None)
    assert st.arm_a2_minus_s(unbacked_k(episode())) == (None, "no_k_backing")


def test_emit_dispatch_and_unknown_arm():
    for arm, fn in (("A0", st.arm_a0), ("A1", st.arm_a1), ("A2", st.arm_a2),
                    ("A2-K", st.arm_a2_minus_k), ("A2-S", st.arm_a2_minus_s)):
        assert st.emit(arm, episode()) == fn(episode())
    with pytest.raises(ValueError):
        st.emit("A3", episode())


# --------------------------------------------------------------------------- #
# manifest + ablation assertion (prereg §4)
# --------------------------------------------------------------------------- #
def test_manifest_tracks_the_leg_that_produced_the_value():
    ep = episode()
    assert st.manifest("A1", ep) == frozenset({"K-1", "K-2"})
    assert st.manifest("A0", ep) == frozenset({"S-1", "S-2", ACCESSION})
    assert st.manifest("A2", ep) == frozenset({"K-1", "K-2"})            # K wins
    assert st.manifest("A2", unbacked_k(ep)) == frozenset({"S-1", "S-2", ACCESSION})
    assert st.manifest("A2", unbacked_k(episode(a0={"sign": None}))) == frozenset()
    assert st.manifest("A2-S", ep) == frozenset({"K-1", "K-2"})
    assert st.manifest("A2-S", unbacked_k(ep)) == frozenset()
    assert st.manifest("A2-K", ep) == frozenset({"S-1", "S-2", ACCESSION})
    assert st.manifest("A0", episode(a0={"sign": None})) == frozenset()


def test_manifest_ablation_passes_on_a_good_episode():
    st.assert_ablation(episode())               # does not raise
    st.assert_ablation(unbacked_k(episode()))
    k_ids = set(episode()["k"]["record_ids"])
    assert not (st.manifest("A2-K", episode()) & k_ids)
    s_ids = set(episode()["s"]["record_ids"]) | {ACCESSION}
    assert not (st.manifest("A2-S", episode()) & s_ids)


def test_assert_ablation_raises_when_an_s_id_sits_in_the_k_list():
    tampered = episode(k={"record_ids": ["S-1"]})   # S record declared as a K input
    with pytest.raises(st.AblationError):
        st.assert_ablation(tampered)
    tampered_s = episode(s={"record_ids": ["K-1"]})  # K record inside the S leg
    with pytest.raises(st.AblationError):
        st.assert_ablation(tampered_s)


# --------------------------------------------------------------------------- #
# common support, hit rate, primary delta
# --------------------------------------------------------------------------- #
def test_common_support_excludes_not_evaluable_null_label_and_abstention():
    eps = [episode(q="A"), episode(q="B", status="NOT_EVALUABLE",
                                   not_evaluable_reason="label_unavailable"),
           episode(q="C", label=None), episode(q="D", a0={"sign": None}),
           episode(q="E", status="EXPOSED")]
    rows = st.common_support(eps)
    assert [r["q"] for r in rows] == ["A"]
    assert all(isinstance(r, dict) for r in rows)


def test_hit_rate_empty_is_none_and_counts_abstention_as_miss():
    assert st.hit_rate("A2", []) is None
    assert st.primary_delta([]) is None
    assert st.bootstrap_interval([]) is None
    eps = [episode(label=1, a0={"sign": 1}), episode(label=1, a0={"sign": -1})]
    assert st.hit_rate("A2-K", eps) == pytest.approx(0.5)
    none_backed = [unbacked_k(episode(q="X"))]     # A2-S abstains -> not a hit
    assert st.hit_rate("A2-S", none_backed) == pytest.approx(0.0)


def test_primary_delta_hand_computed():
    # A2 hits 4/4, A2[-K] hits 3/4  ->  Delta = 0.25.
    eps = [row(1, 1, True), row(-1, 1, True, k_sign=-1),
           row(1, 1, False), row(1, 1, False)]
    rows = st.common_support(eps)
    assert len(rows) == 4
    assert st.hit_rate("A2", rows) == pytest.approx(1.0)
    assert st.hit_rate("A2-K", rows) == pytest.approx(0.75)
    assert st.primary_delta(rows) == pytest.approx(0.25)
    assert st.discordant(rows) == {"b": 1, "c": 0, "p": pytest.approx(1.0)}


def test_cluster_key_is_calendar_quarter_plus_family():
    assert st.cluster_key(episode(t_rel="2026-01-31T21:00:00Z")) == ("2026Q1",
                                                                     "HOMEBUILDERS")
    assert st.cluster_key(episode(t_rel="2025-12-15T21:00:00Z")) == ("2025Q4",
                                                                     "HOMEBUILDERS")
    assert st.cluster_key(episode(t_rel="2026-09-30T12:00:00Z",
                                  cluster="AAPL", issuer="AAPL")) == ("2026Q3", "AAPL")
    assert st.cluster_key(episode(t_rel="not-a-timestamp")) == ("UNKNOWN",
                                                                "HOMEBUILDERS")


# --------------------------------------------------------------------------- #
# cluster bootstrap (lane law S3)
# --------------------------------------------------------------------------- #
def _quarter_rows(months: list[int], per_cluster: int = 4) -> list[dict]:
    """Clusters by calendar quarter, each cluster with an identical Delta = 0.5 mix:
    2 rows where A2 hits and A2[-K] misses, 2 rows where both hit."""
    rows: list[dict] = []
    for idx, month in enumerate(months, start=1):
        for j in range(per_cluster):
            label = 1
            a0_sign = 1 if j >= per_cluster // 2 else -1
            rows.append(episode(q=f"{idx}-{j}",
                                t_rel=f"2026-{month:02d}-15T12:00:00Z",
                                label=label, a0={"sign": a0_sign}))
    return rows


def test_bootstrap_is_deterministic_per_call():
    rows = _quarter_rows([1, 2, 3]) + [episode(q="extra", label=-1,
                                               a0={"sign": -1},
                                               t_rel="2026-04-15T12:00:00Z")]
    rows = st.common_support(rows)
    first = st.bootstrap_interval(rows, seed=31, B=200)
    second = st.bootstrap_interval(rows, seed=31, B=200)
    assert first == second
    assert first is not None and first[0] <= first[1]
    other_seed = st.bootstrap_interval(rows, seed=32, B=200)
    assert isinstance(other_seed, tuple)


def test_bootstrap_constant_delta_over_three_clusters():
    rows = st.common_support(_quarter_rows([1, 4, 7]))
    assert st.primary_delta(rows) == pytest.approx(0.5)
    interval = st.bootstrap_interval(rows, seed=31, B=2000)
    assert interval == pytest.approx((0.5, 0.5))
    assert len({st.cluster_key(r) for r in rows}) == 3


# --------------------------------------------------------------------------- #
# exact sign test (lane law S4)
# --------------------------------------------------------------------------- #
def test_sign_test_p_values():
    assert st.sign_test_p(5, 0) == pytest.approx(0.0625)
    assert st.sign_test_p(0, 0) == 1.0
    assert st.sign_test_p(3, 3) == 1.0
    assert st.sign_test_p(1, 0) == 1.0
    assert st.sign_test_p(0, 5) == pytest.approx(0.0625)
    assert st.sign_test_p(8, 0) == pytest.approx(2 * 1 / 256)


# --------------------------------------------------------------------------- #
# minimum + verdict table (prereg §5)
# --------------------------------------------------------------------------- #
def test_minimum_met_boundaries():
    assert st.minimum_met(39, 12) is False
    assert st.minimum_met(40, 11) is False
    assert st.minimum_met(40, 12) is True
    assert st.minimum_met(80, 12) is True


def test_verdict_table_rows_in_order():
    # row 1: minimum not met
    assert st.verdict(39, 12, 0.20, (0.05, 0.40)) == ("INCONCLUSIVE", "minimum_not_met")
    assert st.verdict(40, 11, 0.20, (0.05, 0.40)) == ("INCONCLUSIVE", "minimum_not_met")
    # row 2: PASS_FOR_REVIEW (Delta >= 0.10 AND p2.5 > 0)
    assert st.verdict(40, 12, 0.12, (0.02, 0.30))[0] == "PASS_FOR_REVIEW"
    # Delta exactly +0.10 is a PASS candidate, not a NULL
    assert st.verdict(40, 12, 0.10, (0.01, 0.30))[0] == "PASS_FOR_REVIEW"
    # row 3: ADVERSE wins over the NULL row even when Delta < 0.10
    assert st.verdict(40, 12, -0.05, (-0.40, -0.01))[0] == "ADVERSE"
    assert st.verdict(40, 12, 0.05, (-0.40, -0.01))[0] == "ADVERSE"
    # row 4: NULL, including an interval entirely above zero but a small Delta
    assert st.verdict(40, 12, 0.09, (0.01, 0.20))[0] == "NULL"
    assert st.verdict(40, 12, 0.00, (0.00, 0.00))[0] == "NULL"
    # row 5: Delta >= 0.10 but the interval includes zero
    assert st.verdict(40, 12, 0.10, (0.00, 0.30)) == (
        "INCONCLUSIVE", "delta_ge_useful_effect_but_interval_includes_zero")
    assert st.verdict(40, 12, 0.20, (-0.05, 0.40))[0] == "INCONCLUSIVE"


def test_exact_boundary_delta_is_a_pass_candidate():
    # 24/40 A2 hits against 20/40 A2[-K] hits is exactly +0.10. The float difference of
    # the hit rates is 0.0999..., which a float comparison would have called NULL.
    rows = []
    for idx in range(40):
        # A2 always emits sign(K)=+1 here; A2[-K] abstains-to-A0 with a0 sign.
        if idx < 20:          # both hit
            rows.append(row(1, 1, True))
        elif idx < 24:        # A2 hits, A2[-K] misses
            rows.append(row(1, -1, True))
        else:                 # both miss
            rows.append(row(-1, 1, True))
    assert st.hits("A2", rows) == 24
    assert st.hits("A2-K", rows) == 20
    assert 0.6 - 0.5 < st.USEFUL_EFFECT                     # the float trap
    exact = st.primary_delta_exact(rows)
    assert exact == Fraction(1, 10)
    assert st.verdict(40, 12, exact, (0.01, 0.30))[0] == "PASS_FOR_REVIEW"
    assert st.verdict(40, 12, Fraction(3, 40), (0.01, 0.30))[0] == "NULL"
    assert st.primary_delta(rows) == pytest.approx(0.1)


# --------------------------------------------------------------------------- #
# looks + stopping (prereg §5, spec rules (1)-(4))
# --------------------------------------------------------------------------- #
def test_classify_look_rule1_stopping_carry_over():
    prior = [{"n": 45, "clusters": 13, "look": "look1", "study_stopped": True,
              "verdict": "ADVERSE"}]
    assert st.classify_look(80, 20, prior) == "monitoring"
    assert st.classify_look(40, 12, prior) == "monitoring"


def test_classify_look_rule2_look2_terminal():
    assert st.classify_look(80, 20, ()) == "look2"
    # 79 with the minimum met is look1, not look2 (rule 2 needs N >= 80)
    assert st.classify_look(79, 20, ()) == "look1"
    prior_look2 = [{"n": 80, "clusters": 20, "look": "look2", "study_stopped": True,
                    "verdict": "NULL"}]
    assert st.classify_look(90, 22, prior_look2) == "monitoring"


def test_classify_look_first_read_meeting_both_thresholds_is_look2():
    # N >= 80 but clusters < 12: look2 by rule (2), and the verdict table still says
    # INCONCLUSIVE minimum_not_met (prereg §5: minimum is 40 episodes AND 12 clusters).
    look = st.classify_look(80, 11, ())
    assert look == "look2"
    assert st.verdict(80, 11, 0.20, (0.05, 0.40)) == ("INCONCLUSIVE", "minimum_not_met")


def test_classify_look_rule3_and_rule4():
    assert st.classify_look(40, 12, ()) == "look1"
    assert st.classify_look(39, 12, ()) == "monitoring"
    prior_look1 = [{"n": 45, "clusters": 13, "look": "look1", "study_stopped": False,
                    "verdict": "NULL"}]
    assert st.classify_look(50, 15, prior_look1) == "monitoring"


def test_is_study_stopped():
    assert st.is_study_stopped("look1", "PASS_FOR_REVIEW") is True
    assert st.is_study_stopped("look1", "ADVERSE") is True
    assert st.is_study_stopped("look1", "NULL") is False
    assert st.is_study_stopped("look1", "INCONCLUSIVE") is False
    assert st.is_study_stopped("look2", "NULL") is True
    assert st.is_study_stopped("monitoring", "ADVERSE") is False


def test_build_report_monitoring_carries_stopping_verdict():
    prior = [{"n": 41, "clusters": 12, "look": "look1", "study_stopped": True,
              "verdict": "PASS_FOR_REVIEW"}]
    report = st.build_report([episode(q="only")], prior_reads=prior)
    assert report["look"] == "monitoring"
    assert report["verdict"] == "PASS_FOR_REVIEW"
    assert report["verdict_reason"] == "monitoring_carries_stopping_verdict"
    assert report["study_stopped"] is True
    # monitoring without any prior stop is descriptive only
    fresh = st.build_report([episode(q="only")], prior_reads=())
    assert fresh["look"] == "monitoring"
    assert fresh["verdict"] == "MONITORING"
    assert fresh["verdict_reason"] == "monitoring_descriptive_only"
    assert fresh["study_stopped"] is False


# --------------------------------------------------------------------------- #
# uniqueness assertion (prereg §6)
# --------------------------------------------------------------------------- #
def test_assert_unique_raises_on_duplicate_issuer_quarter():
    st.assert_unique([episode(q="2026Q4"), episode(q="2025Q4", issuer="PHM")])
    with pytest.raises(ValueError):
        st.assert_unique([episode(q="2026Q4"), episode(q="2026Q4", issuer="DHI")])
    with pytest.raises(ValueError):
        st.build_report([episode(q="2026Q4"), episode(q="2026Q4")])


# --------------------------------------------------------------------------- #
# costs (prereg §5, lane law S1)
# --------------------------------------------------------------------------- #
def test_costs_insufficient_n_on_three_episodes():
    rows = st.common_support([
        episode(q="a", a0={"sign": 1}, returns={"ret_issuer": 0.01, "ret_hedge": 0.00}),
        episode(q="b", a0={"sign": 1}, returns={"ret_issuer": -0.02, "ret_hedge": 0.0}),
        episode(q="c", a0={"sign": 1}, returns={"ret_issuer": 0.03, "ret_hedge": 0.01}),
    ])
    out = st.costs(rows)
    assert out["deflated_sharpe"] == "insufficient_n"
    assert out["n_pnl"] == 3
    assert out["note"] == "no decision weight at this sample size"
    assert out["mean"] == pytest.approx(((0.01 - 0.004) + (-0.02 - 0.004)
                                         + (0.02 - 0.004)) / 3)
    assert out["benchmarks"] == {"AAPL": "XLK", "HOMEBUILDERS": "XHB"}
    assert out["cost_per_episode"] == pytest.approx(0.0040)


def test_costs_counts_missing_returns_and_missing_sign():
    rows = st.common_support([episode(q="a", a0={"sign": 1}),
                              unbacked_k(episode(q="b"))])
    out = st.costs(rows)
    assert out["n_rows"] == 2
    assert out["n_without_returns"] == 2
    assert out["n_pnl"] == 0
    assert out["mean"] is None


def test_costs_computes_deflated_sharpe_via_fixed_budget_ledger():
    rows = []
    for i in range(70):
        spread = 0.01 * (1 if i % 3 else -1) + 0.001 * (i % 7)
        rows.append(episode(q=f"2026Q4-{i}", a0={"sign": 1}, label=1,
                            returns={"ret_issuer": spread, "ret_hedge": 0.0}))
    out = st.costs(st.common_support(rows))
    dsr = out["deflated_sharpe"]
    assert isinstance(dsr, dict), dsr
    assert dsr["inputs"]["n_trials"] == st.BUDGET
    assert dsr["inputs"]["family"] == st.FAMILY
    assert dsr["inputs"]["t_eff"] >= 3
    assert dsr["dsr"] is not None and dsr["dsr"]["n_trials"] == st.BUDGET
    assert out["note"] == "no decision weight at this sample size"


def test_costs_pnl_uses_a2_sign():
    # label -1, A2 = +1 from the K leg: pnl = +1 * (0.05 - 0.02) - 0.0040
    out = st.costs(st.common_support([episode(q="a", label=-1, a0={"sign": -1},
                                             returns={"ret_issuer": 0.05,
                                                      "ret_hedge": 0.02})]))
    assert out["mean"] == pytest.approx(0.05 - 0.02 - 0.0040)


# --------------------------------------------------------------------------- #
# secondaries + splits
# --------------------------------------------------------------------------- #
def test_secondaries_structure_and_hr_delta():
    eps = [
        episode(q="a", label=1, a0={"sign": 1}),         # A1 +1, A0 +1, label +1
        episode(q="b", label=1, a0={"sign": -1}),        # A1 +1, A0 -1, label +1
        episode(q="c", label=-1, a0={"sign": 1}),        # A1 +1, A0 +1, label -1
    ]
    out = st.secondaries(eps)
    both = out["hr_a1_minus_hr_a0"]
    assert both["n"] == 3
    assert both["hr_a1"] == pytest.approx(2 / 3)
    assert both["hr_a0"] == pytest.approx(1 / 3)
    assert both["delta"] == pytest.approx(1 / 3)
    pair = out["a2_minus_s_vs_a2_minus_k"]
    assert pair["n_eligible_labeled"] == 3
    assert pair["A2-S"]["coverage"] == pytest.approx(1.0)
    assert pair["A2-S"]["hr"] == pytest.approx(2 / 3)
    assert pair["A2-K"]["hr"] == pytest.approx(1 / 3)
    assert out["split_aapl"]["tiny_n"] is True
    assert out["split_homebuilders"]["n"] == 3
    assert out["split_homebuilders"]["delta"] == pytest.approx(1 / 3)


def test_splits_by_driver_family():
    rows = st.common_support([
        episode(q="a", issuer="AAPL", cluster="AAPL", a0={"sign": 1}),
        episode(q="b", issuer="AAPL", cluster="AAPL", a0={"sign": 1}),
        episode(q="c", issuer="DHI", a0={"sign": -1}),
    ])
    out = st.splits(rows)
    assert set(out) == {"AAPL", "HOMEBUILDERS"}
    assert out["AAPL"]["n"] == 2 and out["AAPL"]["delta"] == pytest.approx(0.0)
    assert out["HOMEBUILDERS"]["n"] == 1
    assert out["HOMEBUILDERS"]["tiny_n"] is True


# --------------------------------------------------------------------------- #
# the report itself
# --------------------------------------------------------------------------- #
def test_build_report_carries_every_spec_key():
    report = st.build_report([episode(q="2026Q4")], prior_reads=())
    for key in ("eligible", "exposed", "not_evaluable", "arms", "n_common_support",
                "n_clusters", "delta", "interval", "discordant", "verdict",
                "verdict_reason", "look", "study_stopped", "secondaries", "splits",
                "costs", "family", "budget"):
        assert key in report, key
    assert report["family"] == st.FAMILY
    assert report["budget"] == st.BUDGET
    assert set(report["arms"]) == set(st.ARMS)
    assert report["eligible"] == 1
    assert report["n_common_support"] == 1
    assert report["n_clusters"] == 1
    assert report["delta"] == pytest.approx(1.0)       # A2 hits, A2[-K] misses
    assert report["interval"] == pytest.approx([1.0, 1.0])
    assert report["discordant"] == {"b": 1, "c": 0, "p": pytest.approx(1.0)}
    # one episode cannot be an adjudicating look: it is descriptive monitoring
    assert report["look"] == "monitoring"
    assert report["verdict"] == "MONITORING"
    assert report["verdict_reason"] == "monitoring_descriptive_only"
    assert report["study_stopped"] is False
    assert report["exposed"] == 0
    assert report["not_evaluable"] == {}


def test_build_report_empty_input_still_prints_everything():
    report = st.build_report([])
    assert report["eligible"] == 0 and report["n_common_support"] == 0
    assert report["n_clusters"] == 0
    assert report["delta"] is None and report["interval"] is None
    assert report["discordant"] == {"b": 0, "c": 0, "p": 1.0}
    assert report["costs"]["mean"] is None
    assert report["costs"]["note"] == "no decision weight at this sample size"
    assert report["arms"]["A0"] == {"emit": 0, "abstain": {}}
    assert report["family"] == st.FAMILY and report["budget"] == 6


def test_build_report_counts_exposure_and_not_evaluable_reasons():
    eps = [
        episode(q="1", status="ELIGIBLE", label=1, a0={"sign": 1}),
        episode(q="2", status="EXPOSED"),
        episode(q="3", status="EXPOSED"),
        episode(q="4", status="NOT_EVALUABLE", not_evaluable_reason="label_tie"),
        episode(q="5", status="NOT_EVALUABLE", not_evaluable_reason="pit_unrecoverable"),
        episode(q="6", status="NOT_EVALUABLE", not_evaluable_reason="label_tie"),
    ]
    report = st.build_report(eps)
    assert report["eligible"] == 1
    assert report["exposed"] == 2
    assert report["not_evaluable"] == {"label_tie": 2, "pit_unrecoverable": 1}
    # arms accounting is over ELIGIBLE episodes only
    assert report["arms"]["A0"] == {"emit": 1, "abstain": {}}
    assert report["arms"]["A2-K"] == {"emit": 1, "abstain": {}}
    assert report["arms"]["A2-S"]["emit"] == 1


def test_build_report_look1_first_read_met_with_12_clusters():
    eps = []
    for year in (2024, 2025, 2026):
        for month in (1, 4, 7, 10):
            for j in range(4):
                eps.append(episode(q=f"{year}-{month}-{j}",
                                   t_rel=f"{year}-{month:02d}-15T12:00:00Z",
                                   label=1, a0={"sign": 1},
                                   k={"abstain_reason": "period_mismatch",
                                      "average": None, "year_ago": None}))
    report = st.build_report(eps, prior_reads=())
    assert report["n_common_support"] == 48
    assert report["n_clusters"] == 12
    assert report["look"] == "look1"
    assert report["delta"] == pytest.approx(0.0)
    assert report["verdict"] == "NULL"
    assert report["study_stopped"] is False


def test_build_report_look2_with_too_few_clusters_is_minimum_not_met():
    # Synthetic threshold fixture (80 rows over 10 clusters): q labels are made
    # unique by index so the (issuer, q) assertion passes while the cluster count
    # stays below 12 -- exactly the prereg §5 "look2 with clusters < 12" case.
    eps = []
    for quarter in range(10):
        month = 3 * (quarter % 4) + 1
        year = 2024 + quarter // 4
        for i in range(8):
            eps.append(unbacked_k(episode(q=f"{year}Q{(month - 1) // 3 + 1}-{i}",
                                          t_rel=f"{year}-{month:02d}-15T12:00:00Z",
                                          label=1, a0={"sign": 1})))
    report = st.build_report(eps, prior_reads=())
    assert report["n_common_support"] == 80
    assert report["n_clusters"] == 10
    assert report["look"] == "look2"
    assert report["verdict"] == "INCONCLUSIVE"
    assert report["verdict_reason"] == "minimum_not_met"
    assert report["study_stopped"] is True
    assert report["delta"] == pytest.approx(0.0)


def test_module_is_self_contained_and_never_registers():
    """Lane law S5: no import of the sibling WP31 modules, no trial-ledger use,
    no registration call, no file open, and the honest deflated-Sharpe path."""
    import ast
    import pathlib
    source = pathlib.Path("scripts/c19_wp31_stats.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not [name for name in imported if "c19_wp31_gates" in name
                or "c19_wp31_sources" in name], imported
    assert not [name for name in imported if "trial_ledger" in name], imported
    calls = {node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
             for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, (ast.Name, ast.Attribute))}
    assert "register_trials" not in calls and "open" not in calls, sorted(calls)
    dsr_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and getattr(node.func, "id", getattr(node.func, "attr", None))
                 == "deflated_sharpe"]
    assert len(dsr_calls) == 1
    kwargs = {kw.arg for kw in dsr_calls[0].keywords}
    assert {"ledger", "family", "t_eff"} <= kwargs, kwargs
    assert "n_trials" not in kwargs, kwargs
