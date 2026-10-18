"""Tests for the M0 coherent-target retrospective requalification runner.

E0 §2.H1 (frozen protocol, sha 87b51dca…): re-score the 13 inherited MRI
release-forecast evaluations against one coherent first-print target per
release.  Everything here is synthetic: adapters, target loaders, parity and
defect files live under tmp_path; owners are monkeypatched where a default
adapter is exercised.  No file outside tmp_path is written.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO / "research" / "rates_inflation_command" / "seat_20261014" / "m0_requal.py"
PROTOCOL_REL = Path("research/rates_inflation_command/seat_20261014/E0_RESEARCH_PROTOCOL.md")
PROTOCOL_SHA = "87b51dcad66c6f84989675e9cce91eb5b46b3888d60b2e599a8736d87e2309df"

EVAL_IDS = [
    "cpi_headline.v2",
    "cpi_headline.v3_factor",
    "cpi_headline.cpi_bridge",
    "cpi_headline.mf_energy_t1",
    "cpi_headline.coherent_ridge_v1",
    "cpi_core.v2",
    "cpi_core.v3_factor",
    "cpi_core.coherent_ridge_v1",
    "nfp.v1",
    "nfp.v3_factor",
    "pce_headline.champion",
    "pce_core.champion",
    "ppi_final_demand.champion",
]
FAMILY_OF = {eid: eid.rsplit(".", 1)[0] for eid in EVAL_IDS}
CHAMPIONS = {
    "cpi_headline": "cpi_headline.v2",
    "cpi_core": "cpi_core.v2",
    "nfp": "nfp.v1",
    "pce_headline": "pce_headline.champion",
    "pce_core": "pce_core.champion",
    "ppi_final_demand": "ppi_final_demand.champion",
}

# 48 monthly periods: 36 in 2021-2023 (tested), 12 in 2024-2025H1 (current).
PERIODS = [
    f"{y}-{m:02d}" for y in (2021, 2022, 2023) for m in range(1, 13)
] + [f"{y}-{m:02d}" for y in (2024, 2025) for m in range(1, 7)]


def _load_module():
    spec = importlib.util.spec_from_file_location("m0_requal_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def m0():
    return _load_module()


# --------------------------------------------------------------------------
# synthetic world
# --------------------------------------------------------------------------
def _t(i: int) -> float:
    return 0.40 + 0.30 * math.sin(0.7 * i)


def _series():
    target = {p: round(_t(i), 6) for i, p in enumerate(PERIODS)}
    naive = {p: round(_t(i - 1), 6) for i, p in enumerate(PERIODS)}
    trailing = {
        p: round((_t(i - 1) + _t(i - 2) + _t(i - 3)) / 3.0, 6)
        for i, p in enumerate(PERIODS)
    }
    ar = {p: round(0.5 * naive[p] + 0.5 * trailing[p], 6) for p in PERIODS}
    return target, naive, trailing, ar


def good_model(target, naive):
    """|e_model| = 0.8 |e_naive| uniformly -> R = 0.8, mean d < 0, p ~ 0."""

    def model(p):
        return round(target[p] - 0.8 * (target[p] - naive[p]), 6)

    return model


def naive_model(naive):
    def model(p):
        return naive[p]

    return model


class World:
    """Synthetic adapters + target loader rooted in tmp_path."""

    def __init__(
        self,
        tmp_path,
        *,
        models=None,
        target_override=None,
        target_missing=(),
        owner_actual_fn=None,
        owner_release_day=None,
        parity_cases=None,
        defect_files=None,
        protocol_bytes=None,
        extra_periods=(),
    ):
        self.root = tmp_path / "root"
        self.root.mkdir(parents=True, exist_ok=True)
        proto = self.root / PROTOCOL_REL
        proto.parent.mkdir(parents=True, exist_ok=True)
        if protocol_bytes is None:
            shutil.copy(REPO / PROTOCOL_REL, proto)
        else:
            proto.write_bytes(protocol_bytes)
        self.out_dir = tmp_path / "out"
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.target, self.naive, self.trailing, self.ar = _series()
        self.models = dict(models or {})
        self._model_fns = {}
        for eid in EVAL_IDS:
            self._model_fns[eid] = self.models.get(eid, good_model(self.target, self.naive))
        self.target_missing = set(target_missing)
        self.target_override = dict(target_override or {})
        self.owner_actual_fn = owner_actual_fn
        self.owner_release_day = owner_release_day
        self.parity_cases = parity_cases
        self.defect_files = defect_files or {}
        # extra_periods behave as nonpublication months: rows exist, the
        # coherent truth file has no target for them.
        self.row_periods = list(PERIODS) + list(extra_periods)
        if parity_cases is not None:
            ppath = self.root / "data/release_forecast/cpi_truth/parity_report.json"
            ppath.parent.mkdir(parents=True, exist_ok=True)
            ppath.write_text(json.dumps(parity_cases), encoding="utf-8")
        for name, payload in self.defect_files.items():
            dpath = self.root / "data/release_forecast" / name
            dpath.parent.mkdir(parents=True, exist_ok=True)
            dpath.write_text(json.dumps(payload), encoding="utf-8")

    # -- target loader ------------------------------------------------------
    def target_loader(self, release, period):
        if period in self.target_missing and period not in self.target_override:
            return None
        if period in self.target_override:
            value = self.target_override[period]
            if value is None:
                return None
        else:
            if period not in self.target:
                return None
            value = self.target[period]
        return {
            "status": "ok",
            "value": value,
            "release_date": f"{period}-13",
            "release_selection": "initial_for_period",
        }

    # -- adapters -----------------------------------------------------------
    def _rows_for(self, eid):
        fam = FAMILY_OF[eid]
        model = self._model_fns[eid]
        rows = []
        for p in self.row_periods:
            if self.owner_release_day is not None:
                rdate = f"{p}-{self.owner_release_day:02d}"
            else:
                rdate = f"{p}-13"
            if self.owner_actual_fn is not None:
                oactual = self.owner_actual_fn(eid, p)
            else:
                oactual = self.target.get(p)
            predicted = model(p) if p in self.target else 0.2
            rows.append(
                {
                    "eval_id": eid,
                    "family": fam,
                    "period": p,
                    "release_date": rdate,
                    "predicted": predicted,
                    "owner_actual": oactual,
                }
            )
        return rows

    def _baselines(self):
        return [
            {
                "period": p,
                "release_date": f"{p}-13",
                "naive": self.naive[p],
                "trailing_3m": self.trailing[p],
                "ar_model": self.ar[p],
            }
            for p in PERIODS
        ]

    def adapters(self):
        out = {}
        for eid in EVAL_IDS:
            is_champion = CHAMPIONS[FAMILY_OF[eid]] == eid
            rows = self._rows_for(eid)
            baselines = self._baselines() if is_champion else []
            out[eid] = lambda champion_rows=None, _rows=rows, _b=baselines: (_rows, _b)
        return out

    def run(self, m0mod, **kwargs):
        kwargs.setdefault("adapters", self.adapters())
        kwargs.setdefault("target_loader", self.target_loader)
        return m0mod.run(
            self.root, self.out_dir, "2026-10-14", **kwargs
        )


def _eval(result, eid):
    matches = [e for e in result["evaluations"] if e["eval_id"] == eid]
    assert len(matches) == 1, f"expected exactly one row for {eid}"
    return matches[0]


def _first_ok(result):
    return _eval(result, "cpi_headline.coherent_ridge_v1")


# --------------------------------------------------------------------------
# Group A — core
# --------------------------------------------------------------------------
def test_protocol_sha_mismatch_blocks_before_any_computation(m0, tmp_path):
    world = World(tmp_path, protocol_bytes=b"not the protocol\n")

    def boom(release, period):
        raise AssertionError("target loader must not be called on a sha mismatch")

    class LedgerBoom:
        def __init__(self, *a, **k):
            raise AssertionError("budget must not be declared on a sha mismatch")

    import engine.trial_ledger as tl

    original = tl.TrialLedger
    tl.TrialLedger = LedgerBoom
    try:
        result = m0.run(
            world.root,
            world.out_dir,
            "2026-10-14",
            declare_budget=True,
            adapters=world.adapters(),
            target_loader=boom,
        )
    finally:
        tl.TrialLedger = original
    assert result["status"] == "blocked"
    assert result["reason"] == "protocol_sha_mismatch"
    assert result["evaluations"] == []
    assert result["holm"]["family_size"] == 13


def test_evaluations_are_exactly_the_thirteen_in_protocol_order(m0):
    ids = tuple(e.eval_id for e in m0.EVALUATIONS)
    assert ids == tuple(EVAL_IDS)
    assert len(ids) == 13
    for e in m0.EVALUATIONS:
        assert e.family == FAMILY_OF[e.eval_id]


def test_headline_and_core_never_pool(m0, tmp_path):
    world = World(tmp_path)
    # headline model: perfect (d < 0 everywhere); core model: worse than naive.
    world._model_fns["cpi_headline.v2"] = lambda p: world.target[p]
    core = naive_model(world.naive)
    world._model_fns["cpi_core.v2"] = core
    result = world.run(m0)
    headline = _eval(result, "cpi_headline.v2")
    core_ev = _eval(result, "cpi_core.v2")
    assert core_ev["verdict"] == "FALSIFIED_UNDER_COHERENT_TARGET"
    assert headline["verdict"] != "FALSIFIED_UNDER_COHERENT_TARGET"
    # pooled rows would drag the headline mean d to the average of both families
    assert headline["windows"]["tested"]["vs_naive"]["mean_d"] < 0
    assert core_ev["windows"]["tested"]["vs_naive"]["mean_d"] >= 0
    assert headline["n_rows"]["tested"] == 48
    assert core_ev["n_rows"]["tested"] == 48


def test_target_is_coherent_first_print_not_owner_actual(m0, tmp_path):
    world = World(tmp_path)
    # coherent target differs from the owner actual by a fixed offset
    shifted = {p: world.target[p] + 0.25 for p in PERIODS}
    world.target_override = shifted
    result = world.run(m0)
    ev = _first_ok(result)
    # errors are target - predicted; with the shifted target and a good model
    # built against the unshifted one, mean d must reflect the 0.25 shift.
    mean_d = ev["windows"]["tested"]["vs_naive"]["mean_d"]
    assert mean_d is not None
    # manual recomputation on the coherent target
    ds = []
    for i, p in enumerate(PERIODS):
        if p < "2021-01":
            continue
        pred = world._model_fns["cpi_headline.coherent_ridge_v1"](p)
        e_model = abs(shifted[p] - pred)
        e_naive = abs(shifted[p] - world.naive[p])
        ds.append(e_model - e_naive)
    assert mean_d == pytest.approx(sum(ds) / len(ds), abs=1e-9)


def test_missing_source_excluded_from_accuracy_and_counted_in_coverage(m0, tmp_path):
    world = World(tmp_path, target_missing={"2022-06"})
    result = world.run(m0)
    ev = _first_ok(result)
    missing = [m for m in ev["missing_source"] if m["period"] == "2022-06"]
    assert missing and missing[0]["reason"] == "missing_source"
    # coverage: the period still counts in n_rows; accuracy drops one episode
    assert ev["n_rows"]["tested"] == 48
    scored_tested = ev["windows"]["tested"]["n_scored"]
    assert scored_tested == 47
    assert ev["verdict"] != "INSUFFICIENT"


def test_cpi_nonpublication_period_is_missing_source(m0, tmp_path):
    world = World(tmp_path, extra_periods=("2025-10",))
    result = world.run(m0)
    ev = _eval(result, "cpi_headline.v2")
    assert any(m["period"] == "2025-10" for m in ev["missing_source"])
    # counted in coverage: the row is present in n_rows but never scored
    assert ev["n_rows"]["tested"] == 49
    assert ev["windows"]["tested"]["n_scored"] == 48


def test_units_mismatch_blocks_the_evaluation(m0, tmp_path):
    world = World(tmp_path)
    world.owner_actual_fn = lambda eid, p: world.target[p] * 100.0
    result = world.run(m0)
    ev = _first_ok(result)
    assert ev["status"] == "blocked"
    # E0 §7: a blocked evaluation is a recorded deviation, never verdict None
    assert ev["verdict"] == "NOT_DEMONSTRATED"
    assert "units_mismatch" in ev["reasons"]
    assert "deviation_blocked_evaluation" in ev["reasons"]
    assert ev["units_ratio"] == pytest.approx(100.0)
    assert any(d["eval_id"] == ev["eval_id"] for d in result["deviations"])
    # the Holm family still has 13 members, this one at 1.0
    assert result["holm"]["raw"]["cpi_headline.coherent_ridge_v1"] == 1.0


def test_units_guard_tolerates_revision_noise(m0, tmp_path):
    # owner_actual is a mixed-vintage change: revision noise near the old
    # 0.5*median|target| difference threshold must not block (SF1).
    world = World(tmp_path)
    world.owner_actual_fn = lambda eid, p: world.target[p] * 1.6
    result = world.run(m0)
    ev = _eval(result, "cpi_headline.coherent_ridge_v1")
    assert ev["status"] == "ok"
    assert ev["units_check"] == "ok"
    assert ev["units_ratio"] == pytest.approx(1.6)
    assert "units_mismatch" not in ev["reasons"]


def test_mf_energy_carries_its_prereg_revision_optimistic_leg(m0):
    legs = m0.PIT_LEGS["cpi_headline.mf_energy_t1"]
    assert any(l["pit_class"] == "revision_optimistic" for l in legs)
    assert any(l["leg"] == "cpi_ri_weights" for l in legs)


def test_release_date_mismatch_is_listed_and_target_date_keys_the_episode(m0, tmp_path):
    world = World(tmp_path, owner_release_day=20)  # owner dates all on the 20th
    result = world.run(m0)
    ev = _first_ok(result)
    assert ev["release_date_mismatches"], "mismatch must be listed"
    first = ev["release_date_mismatches"][0]
    assert first["owner"] == "2021-01-20"
    assert first["target"] == "2021-01-13"
    assert first["period"] == "2021-01"
    # honest-N counts distinct TARGET release dates (48), not owner dates
    assert ev["honest_n"]["tested"] == 48
    assert ev["n_rows"]["tested"] == 48


def test_bridge_rows_take_champion_release_date_and_unmatched_rows_are_excluded(
    m0, tmp_path, monkeypatch
):
    world = World(tmp_path)
    target, naive, trailing, ar = _series()

    def champion_rows():
        return [
            {
                "idx": i,
                "predicted": round(target[p] - 0.8 * (target[p] - naive[p]), 6),
                "actual": target[p],
                "baseline_naive": naive[p],
                "baseline_trailing3m": trailing[p],
                "baseline_ar3": ar[p],
                "period": p,
                "release_date": f"{p}-13",
            }
            for i, p in enumerate(PERIODS[:-1])  # champion lacks the last period
        ]

    def bridge_rows():
        return [
            {
                "period": p,
                "release_date": f"{p}-99",  # implausible owner date; join must override
                "predicted": round(target[p] - 0.7 * (target[p] - naive[p]), 6),
                "actual": target[p],
                "baseline_naive": naive[p],
                "baseline_trailing3m": trailing[p],
            }
            for p in PERIODS
        ]

    import engine.release_cpi_bridge as bridge_mod
    import engine.release_forecast as rf_mod

    monkeypatch.setattr(rf_mod, "run_walk_forward_full", lambda release, root: {"results": champion_rows()})
    monkeypatch.setattr(
        bridge_mod, "run_bridge_walk_forward", lambda release, root: {"results": bridge_rows()}
    )
    adapters = world.adapters()
    defaults = m0.default_adapters(world.root, "2026-10-14")
    adapters["cpi_headline.v2"] = defaults["cpi_headline.v2"]
    adapters["cpi_headline.cpi_bridge"] = defaults["cpi_headline.cpi_bridge"]
    result = m0.run(
        world.root, world.out_dir, "2026-10-14",
        adapters=adapters, target_loader=world.target_loader,
    )
    bridge_ev = _eval(result, "cpi_headline.cpi_bridge")
    excluded = [e for e in bridge_ev["excluded"] if e["reason"] == "no_release_date"]
    assert [e["period"] for e in excluded] == [PERIODS[-1]]
    assert bridge_ev["n_rows"]["tested"] == 47
    assert bridge_ev["honest_n"]["tested"] == 47
    # the champion eval itself is fine and shares the champion baselines
    v2 = _eval(result, "cpi_headline.v2")
    assert v2["n_rows"]["tested"] == 47


def test_naive_absent_blocks_and_holm_uses_one(m0, tmp_path):
    world = World(tmp_path)
    adapters = world.adapters()
    good_rows = world._rows_for("pce_headline.champion")

    def no_naive_adapter(champion_rows=None):
        baselines = [
            {
                "period": p,
                "release_date": f"{p}-13",
                "naive": None,
                "trailing_3m": world.trailing[p],
                "ar_model": world.ar[p],
            }
            for p in PERIODS
        ]
        return good_rows, baselines

    adapters["pce_headline.champion"] = no_naive_adapter
    result = m0.run(
        world.root, world.out_dir, "2026-10-14",
        adapters=adapters, target_loader=world.target_loader,
    )
    ev = _eval(result, "pce_headline.champion")
    assert ev["status"] == "blocked"
    assert "naive_prior_absent" in ev["reasons"]
    assert result["holm"]["raw"]["pce_headline.champion"] == 1.0
    assert result["holm"]["family_size"] == 13


def test_strongest_baseline_tie_order_and_not_available(m0):
    maes = {"naive": 1.0, "trailing_3m": 1.0, "ar_model": 1.0}
    strongest, unavailable = m0.choose_strongest_baseline(maes)
    assert strongest == "naive"
    assert unavailable == []
    maes = {"naive": 1.2, "trailing_3m": 1.0, "ar_model": 1.1}
    strongest, unavailable = m0.choose_strongest_baseline(maes)
    assert strongest == "trailing_3m"
    maes = {"naive": 1.2, "ar_model": 1.1}  # trailing not emitted
    strongest, unavailable = m0.choose_strongest_baseline(maes)
    assert strongest == "ar_model"
    assert unavailable == ["trailing_3m"]
    maes = {}
    strongest, unavailable = m0.choose_strongest_baseline(maes)
    assert strongest is None
    assert set(unavailable) == {"naive", "trailing_3m", "ar_model"}


def test_dm_matches_newey_west_definition(m0):
    import numpy as np

    from engine.challenger_spa_comparison import newey_west_lag, newey_west_lrvar

    rng = np.random.default_rng(7)
    d = np.concatenate([-np.abs(rng.normal(0.2, 0.5, 60)), np.abs(rng.normal(0.1, 0.4, 20))])
    out = m0.dm_pvalues(d)
    n = len(d)
    lrvar = newey_west_lrvar(d, newey_west_lag(n))
    dm = math.sqrt(n) * float(np.mean(d)) / math.sqrt(lrvar)
    assert out["dm"] == pytest.approx(dm, rel=1e-12)
    from scipy.stats import norm, t as tdist

    assert out["p_normal"] == pytest.approx(norm.cdf(dm), rel=1e-12)
    assert out["p_t"] == pytest.approx(tdist.cdf(dm, df=n - 1), rel=1e-12)
    # degenerate series -> uncomputable
    assert m0.dm_pvalues([0.0, 0.0]) is None or m0.dm_pvalues([0.0, 0.0])["p_normal"] is None
    assert m0.dm_pvalues([1.0]) is None


def test_holm_family_is_always_thirteen(m0, tmp_path):
    world = World(tmp_path)
    # three blocked evaluations (adapter errors) must not shrink the family
    adapters = world.adapters()

    def raising(champion_rows=None):
        raise RuntimeError("owner exploded")

    adapters["nfp.v1"] = raising
    adapters["nfp.v3_factor"] = raising
    adapters["ppi_final_demand.champion"] = raising
    result = m0.run(
        world.root, world.out_dir, "2026-10-14",
        adapters=adapters, target_loader=world.target_loader,
    )
    assert result["holm"]["family_size"] == 13
    assert len(result["holm"]["raw"]) == 13
    assert len(result["holm"]["adjusted"]) == 13
    assert result["holm"]["raw"]["nfp.v1"] == 1.0
    blocked = _eval(result, "nfp.v1")
    assert blocked["status"] == "blocked"
    assert "adapter_error:RuntimeError" in blocked["reasons"]


def test_borderline_requires_both_normal_and_t_to_clear(m0):
    pvals = {f"e{i}": 0.20 for i in range(13)}
    pvals["e0"] = 0.003  # smallest
    p_t = {k: v for k, v in pvals.items()}
    p_t["e0"] = 0.005
    adj_normal = m0.holm_adjusted(pvals)["e0"]
    adj_t = m0.holm_adjusted({**pvals, "e0": p_t["e0"]})["e0"]
    assert adj_normal < 0.05
    assert adj_t >= 0.05
    clear, borderline = m0.holm_clear_and_borderline(adj_normal, adj_t)
    assert clear is False
    assert borderline is True
    # both clear -> not borderline
    clear, borderline = m0.holm_clear_and_borderline(0.01, 0.02)
    assert clear is True and borderline is False
    # neither clears -> not borderline
    clear, borderline = m0.holm_clear_and_borderline(0.5, 0.6)
    assert clear is False and borderline is False


def test_bootstrap_ci_is_null_below_thirty_and_seeded(m0):
    import pandas as pd

    short = pd.Series([0.1 * (i % 5 - 2) for i in range(29)])
    assert m0.bootstrap_ci(short) is None
    long = pd.Series([0.05 * ((i % 7) - 3) - 0.2 for i in range(40)])
    ci1 = m0.bootstrap_ci(long)
    ci2 = m0.bootstrap_ci(long)
    assert ci1 is not None
    assert ci1 == ci2
    lo, hi = ci1
    assert lo <= hi


def test_verdict_order_insufficient_first(m0):
    verdict, reasons = m0.decide_verdict(
        n_tested=29,
        mean_d_naive_full=0.5,
        mean_d_naive_tested=0.5,
        holm_clear=True,
        r_tested=0.5,
        r_full=0.5,
        r_current=0.5,
        has_revision_optimistic_leg=False,
    )
    assert verdict == "INSUFFICIENT"
    assert reasons == []


def test_falsified_requires_both_windows_against_naive(m0):
    args = dict(
        n_tested=48,
        holm_clear=True,
        r_tested=0.5,
        r_full=0.5,
        r_current=0.5,
        has_revision_optimistic_leg=False,
    )
    verdict, _ = m0.decide_verdict(
        mean_d_naive_full=0.4, mean_d_naive_tested=0.4, **args
    )
    assert verdict == "FALSIFIED_UNDER_COHERENT_TARGET"
    # failing in tested only -> not falsified
    verdict, _ = m0.decide_verdict(
        mean_d_naive_full=-0.4, mean_d_naive_tested=0.4, **args
    )
    assert verdict != "FALSIFIED_UNDER_COHERENT_TARGET"
    # failing in full only -> not falsified
    verdict, _ = m0.decide_verdict(
        mean_d_naive_full=0.4, mean_d_naive_tested=-0.4, **args
    )
    assert verdict != "FALSIFIED_UNDER_COHERENT_TARGET"


def test_strongest_baseline_never_falsifies(m0):
    # mean d vs NAIVE is negative in both windows; versus strongest it is
    # positive in both.  Falsification must not fire.
    verdict, _ = m0.decide_verdict(
        n_tested=48,
        mean_d_naive_full=-0.4,
        mean_d_naive_tested=-0.4,
        holm_clear=False,
        r_tested=1.3,
        r_full=1.2,
        r_current=1.1,
        has_revision_optimistic_leg=False,
    )
    assert verdict != "FALSIFIED_UNDER_COHERENT_TARGET"
    assert verdict == "NOT_DEMONSTRATED"


@pytest.mark.parametrize(
    "kwargs,code",
    [
        (dict(has_revision_optimistic_leg=True), "non_pit_inputs"),
        (dict(holm_clear=False), "holm_not_cleared"),
        (dict(r_tested=0.96), "r_tested_above_0_95"),
        (dict(r_full=1.0), "r_full_not_below_1"),
        (dict(r_current=1.01), "r_current_above_1"),
    ],
)
def test_qualified_requires_every_condition(m0, kwargs, code):
    base = dict(
        n_tested=48,
        mean_d_naive_full=-0.4,
        mean_d_naive_tested=-0.4,
        holm_clear=True,
        r_tested=0.90,
        r_full=0.90,
        r_current=0.95,
        has_revision_optimistic_leg=False,
    )
    verdict, reasons = m0.decide_verdict(**{**base, **kwargs})
    assert verdict == "NOT_DEMONSTRATED"
    assert reasons == [code]
    # the untouched baseline qualifies
    verdict, reasons = m0.decide_verdict(**base)
    assert verdict == "QUALIFIED_RETROSPECTIVE"
    assert reasons == []


def test_current_window_empty_is_its_own_reason(m0):
    base = dict(
        n_tested=48,
        mean_d_naive_full=-0.4,
        mean_d_naive_tested=-0.4,
        holm_clear=True,
        r_tested=0.90,
        r_full=0.90,
        r_current=None,
        has_revision_optimistic_leg=False,
        current_window_empty=True,
    )
    verdict, reasons = m0.decide_verdict(**base)
    assert verdict == "NOT_DEMONSTRATED"
    assert reasons == ["current_window_empty"]


def test_revision_optimistic_leg_caps_at_not_demonstrated(m0, tmp_path):
    world = World(tmp_path)
    # v3_factor evaluations carry revision-optimistic legs; make them otherwise
    # perfect so only the PIT cap can hold them back.
    world._model_fns["cpi_headline.v3_factor"] = lambda p: world.target[p]
    result = world.run(m0)
    ev = _eval(result, "cpi_headline.v3_factor")
    assert ev["verdict"] == "NOT_DEMONSTRATED"
    assert ev["reasons"] == ["non_pit_inputs"]
    assert any(
        leg["pit_class"] == "revision_optimistic" for leg in ev["pit_legs"]
    )
    # a clean model on the same numbers qualifies
    clean = _eval(result, "cpi_headline.coherent_ridge_v1")
    assert clean["verdict"] == "QUALIFIED_RETROSPECTIVE"


def test_windows_by_period_month_and_honest_n_counts_distinct_release_dates(m0, tmp_path):
    # two CPI episodes share one target release date -> honest-N < row count
    world = World(tmp_path)

    loader = world.target_loader

    def sharing_loader(release, period):
        receipt = loader(release, period)
        if receipt is not None and period in ("2021-05", "2021-06"):
            receipt = dict(receipt, release_date="2021-06-13")
        return receipt

    result = m0.run(
        world.root, world.out_dir, "2026-10-14",
        adapters=world.adapters(), target_loader=sharing_loader,
    )
    ev = _first_ok(result)
    assert ev["n_rows"]["tested"] == 48
    assert ev["honest_n"]["tested"] == 47
    assert ev["n_rows"]["current"] == 12
    assert ev["honest_n"]["current"] == 12
    # pre-2021 periods would not enter tested
    world2 = World(tmp_path)
    result2 = world2.run(m0)
    ev2 = _first_ok(result2)
    assert ev2["n_rows"]["full"] == 48


def test_adapter_error_blocks_only_that_evaluation(m0, tmp_path):
    world = World(tmp_path)
    adapters = world.adapters()

    def raising(champion_rows=None):
        raise ValueError("bridge data absent")

    adapters["cpi_headline.cpi_bridge"] = raising
    result = m0.run(
        world.root, world.out_dir, "2026-10-14",
        adapters=adapters, target_loader=world.target_loader,
    )
    blocked = _eval(result, "cpi_headline.cpi_bridge")
    assert blocked["status"] == "blocked"
    assert "adapter_error:ValueError" in blocked["reasons"]
    assert "bridge data absent" in json.dumps(blocked)
    others = [e for e in result["evaluations"] if e["eval_id"] != "cpi_headline.cpi_bridge"]
    assert all(e["status"] == "ok" for e in others)


def test_declare_budget_logs_thirteen_once_only_with_flag(m0, tmp_path):
    world = World(tmp_path)
    calls = []

    class RecordingLedger:
        def __init__(self, *a, **k):
            pass

        def log_declared_budget(self, n, *, family=None, reason=None):
            calls.append((n, family, reason))
            return True

    import engine.trial_ledger as tl

    original = tl.TrialLedger
    tl.TrialLedger = RecordingLedger
    try:
        world.run(m0, declare_budget=False)
        assert calls == []
        world.run(m0, declare_budget=True)
    finally:
        tl.TrialLedger = original
    assert len(calls) == 1
    n, family, reason = calls[0]
    assert n == 13
    assert family == "ric_mri_coherent_requal_v1"
    assert PROTOCOL_REL.as_posix() in reason and PROTOCOL_SHA in reason


# --------------------------------------------------------------------------
# Group B — sensitivities, H4, receipt surface
# --------------------------------------------------------------------------
def test_s1_drops_only_non_match_cpi_periods_and_is_not_applicable_elsewhere(m0, tmp_path):
    parity = {
        "schema": "release_cpi_truth_parity.v1",
        "cases": [
            {"period": "2022-03", "classification": "sample", "status": "passed",
             "comparisons": [{"release": "cpi_headline", "status": "match"}]},
            {"period": "2022-07", "classification": "explicit_gap", "status": "passed",
             "comparisons": []},
        ],
    }
    world = World(tmp_path, parity_cases=parity)
    result = world.run(m0)
    cpi_ev = _first_ok(result)
    s1 = cpi_ev["sensitivities"]["S1"]
    assert s1["n_dropped"] == 1
    assert s1["windows"]["tested"]["n_scored"] == 47
    assert s1["parity_sha256"]
    nfp_ev = _eval(result, "nfp.v1")
    assert nfp_ev["sensitivities"]["S1"]["status"] == "not_applicable"
    # a period the report does not mention is kept
    assert s1["dropped_periods"] == ["2022-07"]


def test_s2_no_applicable_errata_without_explicit_corrected_value(m0, tmp_path):
    defects = {
        "notices": [
            {"release": "cpi_headline", "period": "2022-04", "corrected_value": 0.55},
            {"release": "cpi_headline", "period": "2022-05", "note": "no numeric value"},
        ]
    }
    world = World(tmp_path, defect_files={"defect_notices.json": defects})
    result = world.run(m0)
    ev = _first_ok(result)
    s2 = ev["sensitivities"]["S2"]
    assert s2["n_affected"] == 1
    assert s2["affected_periods"] == ["2022-04"]
    assert len(s2["files"]) >= 1

    quiet = World(tmp_path, defect_files={"defect_notices.json": {"notices": [
        {"release": "cpi_headline", "period": "2022-05", "note": "prose only"}
    ]}})
    result2 = quiet.run(m0)
    s2b = _first_ok(result2)["sensitivities"]["S2"]
    assert s2b["status"] == "NO_APPLICABLE_ERRATA"
    assert s2b["n_affected"] == 0


def test_sensitivity_flag_on_sign_flip_or_ratio_shift(m0, tmp_path):
    # erratum flips the sign of mean d in tested vs strongest for one eval
    world = World(tmp_path)
    eval_id = "cpi_headline.coherent_ridge_v1"

    # amplify one episode's corrected target so the good model becomes worse
    # than the strongest baseline on enough mass to flip the tested sign
    bad = dict(world.target)
    for p in PERIODS[:30]:
        bad[p] = world.target[p] + 5.0
    world.target_override = bad
    # primary run first (no errata)
    result_primary = world.run(m0)
    # now the same world, with the corrections delivered as errata
    world2 = World(tmp_path)
    notices = [
        {"release": "cpi_headline", "period": p, "corrected_value": bad[p]}
        for p in PERIODS[:30]
    ]
    world2.defect_files = {}
    dpath = world2.root / "data/release_forecast/defect_notices.json"
    dpath.parent.mkdir(parents=True, exist_ok=True)
    dpath.write_text(json.dumps({"notices": notices}), encoding="utf-8")
    result_s2 = world2.run(m0)
    ev = _eval(result_s2, eval_id)
    flags = ev["sensitivity_flags"]
    assert "verdict sensitive to S2" in flags


def test_sensitivities_never_change_verdict_or_holm(m0, tmp_path):
    defects = {
        "notices": [
            {"release": "cpi_headline", "period": "2022-04", "corrected_value": 0.9},
        ]
    }
    parity = {
        "schema": "release_cpi_truth_parity.v1",
        "cases": [
            {"period": "2022-07", "classification": "explicit_gap", "status": "passed",
             "comparisons": []},
        ],
    }
    with_errata = World(tmp_path, defect_files={"defect_notices.json": defects}, parity_cases=parity)
    plain = World(tmp_path / "plain")
    r1 = with_errata.run(m0)
    r2 = plain.run(m0)
    for e1, e2 in zip(r1["evaluations"], r2["evaluations"]):
        assert e1["verdict"] == e2["verdict"]
        assert e1["status"] == e2["status"]
    assert r1["holm"]["adjusted"] == r2["holm"]["adjusted"]


def test_h4_complexity_not_earned_at_ratio_one(m0, tmp_path):
    world = World(tmp_path)
    # bridge identical to the champion v2 -> contrast R = 1.0 in tested
    world._model_fns["cpi_headline.cpi_bridge"] = world._model_fns["cpi_headline.v2"]
    # v3 slightly better than v2 (|e| = 0.7 vs 0.8 of naive) -> R < 1
    world._model_fns["cpi_headline.v3_factor"] = (
        lambda p: round(world.target[p] - 0.7 * (world.target[p] - world.naive[p]), 6)
    )
    result = world.run(m0)
    contrasts = {
        c["contrast"]: c for c in result["h4"]["contrasts"]
    }
    bridge = contrasts["cpi_headline.cpi_bridge_vs_cpi_headline.v2"]
    assert bridge["windows"]["tested"]["R"] == pytest.approx(1.0, abs=1e-9)
    assert "COMPLEXITY_NOT_EARNED" in bridge["labels"]
    v3 = contrasts["cpi_headline.v3_factor_vs_cpi_headline.v2"]
    assert v3["windows"]["tested"]["R"] < 1.0
    assert "COMPLEXITY_NOT_EARNED" not in v3["labels"]


def test_holm_multiplicity_gate_uses_adjusted_p_not_raw(m0, tmp_path):
    world = World(tmp_path)
    # every other evaluation becomes exactly the naive prior (d = 0, p = 0.5)
    # so the evaluation under test carries the SMALLEST raw p and sits at the
    # strictest Holm step (multiplier 13).
    def neutral(p):
        return world.naive[p]

    for eid in EVAL_IDS:
        if eid != "cpi_headline.coherent_ridge_v1":
            world._model_fns[eid] = neutral

    def borderline(p):
        i = PERIODS.index(p)
        e_naive = world.target[p] - world.naive[p]
        sign = 1.0 if i % 2 == 0 else -1.0
        e_model = 0.9 * abs(e_naive) * (1.0 + 1.0 * sign)
        return round(world.target[p] - e_model, 6)

    world._model_fns["cpi_headline.coherent_ridge_v1"] = borderline
    result = world.run(m0)
    ev = _first_ok(result)
    p_raw = ev["primary"]["p_normal"]
    adj = ev["primary"]["holm_adj"]
    # preconditions: raw p clears alpha, the Holm-adjusted p does not
    assert p_raw is not None and p_raw < 0.05
    assert adj is not None and adj >= 0.05
    assert ev["verdict"] == "NOT_DEMONSTRATED"
    assert ev["reasons"] == ["holm_not_cleared"]


def test_h4_interval_uses_only_strictly_prior_residuals(m0, tmp_path):
    world = World(tmp_path)
    result = world.run(m0)
    intervals = {row["eval_id"]: row for row in result["h4"]["intervals"]}
    base = intervals["cpi_headline.coherent_ridge_v1"]

    # perturb the LAST episode's owner actual; earlier bands must not move
    world2 = World(tmp_path / "again")

    def perturbed(eid, p):
        value = world2.target[p]
        if p == PERIODS[-1]:
            return value + 3.0
        return value

    world2.owner_actual_fn = perturbed
    result2 = world2.run(m0)
    intervals2 = {row["eval_id"]: row for row in result2["h4"]["intervals"]}
    moved = intervals2["cpi_headline.coherent_ridge_v1"]
    assert base["n_interval_scored"] == moved["n_interval_scored"]
    assert base["covered_k"] == moved["covered_k"]
    # with 48 distinct release dates the first 24 episodes have no band
    assert base["n_interval_scored"] == len(PERIODS) - 24

    # a world where every episode shares ONE target release date: strictly
    # prior residuals do not exist, so nothing is interval-scored.  (A <=
    # comparison would score 24 episodes from same-date residuals.)
    world3 = World(tmp_path / "sameday")
    loader = world3.target_loader

    def one_day_loader(release, period):
        receipt = loader(release, period)
        if receipt is not None:
            receipt = dict(receipt, release_date="2021-01-13")
        return receipt

    result3 = m0.run(
        world3.root, world3.out_dir, "2026-10-14",
        adapters=world3.adapters(), target_loader=one_day_loader,
    )
    same_day = {
        row["eval_id"]: row for row in result3["h4"]["intervals"]
    }["cpi_headline.coherent_ridge_v1"]
    assert same_day["n_interval_scored"] == 0
    assert same_day["covered_k"] == 0


def test_h4_coverage_wilson_and_not_comparable_without_naive_band(m0, tmp_path):
    from engine.grading_stats import wilson_ci

    world = World(tmp_path)
    result = world.run(m0)
    fam = result["h4"]["family_coverage"]["cpi_headline"]
    lo, hi = wilson_ci(fam["covered_k"], fam["n"])
    assert fam["wilson_lo"] == lo and fam["wilson_hi"] == hi
    # naive band unavailable: with a fresh world the naive residuals exist, so
    # construct the not-comparable case by giving naive None on early periods
    world2 = World(tmp_path / "nc")
    adapters = world2.adapters()
    champion = CHAMPIONS["cpi_headline"]

    def patchy_baselines(champion_rows=None):
        rows = world2._rows_for(champion)
        baselines = []
        for j, p in enumerate(PERIODS):
            baselines.append({
                "period": p,
                "release_date": f"{p}-13",
                "naive": world2.naive[p] if j >= len(PERIODS) - 5 else None,
                "trailing_3m": world2.trailing[p],
                "ar_model": world2.ar[p],
            })
        return rows, baselines

    adapters[champion] = patchy_baselines
    result2 = m0.run(
        world2.root, world2.out_dir, "2026-10-14",
        adapters=adapters, target_loader=world2.target_loader,
    )
    intervals = {row["eval_id"]: row for row in result2["h4"]["intervals"]}
    champ = intervals[champion]
    assert champ["sharpness_status"] == "NOT_COMPARABLE"
    assert champ["calibrated"] is False


def test_receipt_carries_target_model_basis_and_protocol_identity(m0, tmp_path):
    world = World(tmp_path)
    result = world.run(m0)
    receipt = (world.out_dir / "m0_requal_2026-10-14.json")
    assert receipt.exists()
    on_disk = json.loads(receipt.read_text(encoding="utf-8"))
    assert on_disk == json.loads(json.dumps(result))
    assert result["schema"] == "ric_m0_requal.v1"
    assert result["protocol"]["path"].endswith("E0_RESEARCH_PROTOCOL.md")
    assert result["protocol"]["sha256"] == PROTOCOL_SHA
    assert result["trial"]["family"] == "ric_mri_coherent_requal_v1"
    assert result["trial"]["n"] == 13
    assert result["decision_asof"] == "2026-10-14"
    for ev in result["evaluations"]:
        assert ev["target"]["basis"] == "same_release_first_print"
        assert ev["model_id"]
        assert ev["family"] == FAMILY_OF[ev["eval_id"]]
        assert ev["target"]["id"] == FAMILY_OF[ev["eval_id"]] + ".same_release_first_print"
    assert any(
        entry["path"].endswith("E0_RESEARCH_PROTOCOL.md") for entry in result["inputs"]
    )


def test_runner_writes_only_under_out_dir_and_never_the_forward_ledger(m0, tmp_path):
    world = World(tmp_path)
    before = {p for p in world.root.rglob("*") if p.is_file()}
    world.run(m0)
    after = {p for p in world.root.rglob("*") if p.is_file()}
    assert before == after  # root untouched
    written = sorted(p.name for p in world.out_dir.iterdir())
    assert written == ["m0_requal_2026-10-14.json", "m0_requal_2026-10-14.md"]
    assert not (world.root / "data/release_forecast/forward_ledger.jsonl").exists()
    assert not (world.root / "data/trial_ledger.jsonl").exists()


def test_markdown_prints_nulls_and_never_says_validated(m0, tmp_path):
    world = World(tmp_path)
    # force a null: nfp evaluated with too few episodes
    adapters = world.adapters()
    few_rows = world._rows_for("nfp.v1")[:20]
    adapters["nfp.v1"] = lambda champion_rows=None: (few_rows, world._baselines())

    def empty_loader(release, period):
        if release == "nfp":
            return None
        return world.target_loader(release, period)

    result = m0.run(
        world.root, world.out_dir, "2026-10-14",
        adapters=adapters, target_loader=empty_loader,
    )
    md = (world.out_dir / "m0_requal_2026-10-14.md").read_text(encoding="utf-8")
    low = md.lower()
    assert "validated" not in low
    assert "not computed" in md
    nfp = _eval(result, "nfp.v1")
    assert nfp["verdict"] == "INSUFFICIENT"
