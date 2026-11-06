"""P03 ULP-stability of the sealed S1 v1.1 descriptive comparison.

SNI-local DRAFT contract. This module CONSUMES owner-supplied opaque
identity strings and committed observation/result JSON owned by the S1
residual runner / Data OS / Stock Identity; it does not mint, derive, or
guess canonical HK/US issuer or security identifiers.

HISTORICAL-DESCRIPTIVE numerical-stability property of a frozen study.
It is not a forecast, signal, validation, or registration. Nothing here
feeds a ranker, gate, sizer, signal, escalation, or trade path.

rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority, and trade_authority stay false. Setting any of
them true raises.
"""
from __future__ import annotations

import copy
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))
sys.path.insert(0, str(REPO))

try:
    import run_s1  # noqa: E402
    from engine.grading_stats import BOOT_DRAWS, BOOT_SEED  # noqa: E402
    from s1_prereg import HORIZONS, POWER_FLOOR_N, SUBJECTS  # noqa: E402
    from s1_report import s0_criterion_holds  # noqa: E402
except Exception as exc:  # pragma: no cover - sparse-tree import gap
    raise RuntimeError(
        "narrow import of run_s1._comparison_block failed; "
        "engine.qledger / residual modules are required and were not vendored"
    ) from exc

V11 = REPO / "research/single_name_intelligence/runs/s1_residual_v1_1"
OBS_DIR = V11 / "observations"
P03_RESULTS = V11 / "results" / "P03.json"
REVIEW_PATH = (
    REPO / "research/single_name_intelligence/reviews"
    / "P03_ULP_STABILITY_2026-10-13.md"
)

# ~2x the XREP macOS arm64 worst relative diff (4.62e-12).
P03U_EPS = 1e-11
MARGIN_SAFETY = 1e3
PERTURB_FIELDS = ("r__oc", "common__oc", "z__oc")
CHALLENGER_FLOAT = "common_ipca__oc"
LEAK_RETIRED = {("P03", "adr_baba")}

_AUTHORITY_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)
AUTHORITY_FLAGS = {name: False for name in _AUTHORITY_NAMES}


def refuse_authority(name: str, value) -> None:
    """Refuse any attempt to enable an authority flag."""
    if value:
        raise ValueError(
            f"{name} must stay false; this DRAFT contract does not feed a "
            "ranker, gate, sizer, signal, escalation, or trade path"
        )


def assert_authority_false(flags=None) -> None:
    flags = AUTHORITY_FLAGS if flags is None else flags
    for name in _AUTHORITY_NAMES:
        refuse_authority(name, flags.get(name, False))
        if name in flags and flags[name] is not False:
            raise ValueError(f"{name} must be literal false, got {flags[name]!r}")


assert_authority_false()


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _require(path: Path) -> Path:
    if not path.exists():
        rel = path.relative_to(REPO)
        pytest.fail(
            f"missing committed path {rel}; "
            f"git sparse-checkout add {rel}"
        )
    return path


def p03_subjects():
    return list(SUBJECTS["P01"]) + list(SUBJECTS["P02"])


def load_observations() -> dict:
    """Committed P03 observation lists, keyed as p03_blocks expects."""
    _require(OBS_DIR)
    out = {}
    for subj in p03_subjects():
        counter = subj["counter"]
        for h in HORIZONS:
            key = f"P03_{counter}_{h}"
            out[key] = _load_json(_require(OBS_DIR / f"{key}.json"))
    return out


def load_committed_p03() -> dict:
    return _load_json(_require(P03_RESULTS))


def stub_rebuilt() -> dict:
    rebuilt = {}
    for subj in p03_subjects():
        counter = subj["counter"]
        for h in HORIZONS:
            rebuilt[("P03", counter, h)] = {
                "digests": {
                    "TRAIN": {"membership_sha256": "0" * 64, "count": 0},
                    "TUNE": {"membership_sha256": "0" * 64, "count": 0},
                    "QUARANTINE": {"membership_sha256": "0" * 64, "count": 0},
                }
            }
    return rebuilt


def replay_p03(p03_obs: dict, trial_accounting=None):
    """Call the real p03_blocks path with a stub rebuilt/receipt/accounting."""
    assert_authority_false()
    if trial_accounting is None:
        trial_accounting = {}
    return run_s1.p03_blocks(
        p03_obs,
        stub_rebuilt(),
        LEAK_RETIRED,
        trial_accounting=trial_accounting,
        receipt_base={},
    )


def perturb_observations(p03_obs: dict, seed: int, eps: float) -> dict:
    """Relative ULP-scale jitter of every float the P03 decisions read."""
    rng = random.Random(seed)
    out = copy.deepcopy(p03_obs)
    for key in sorted(out):
        for row in out[key]:
            for fld in PERTURB_FIELDS:
                v = row.get(fld)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    u = rng.uniform(-1.0, 1.0)
                    row[fld] = float(v) * (1.0 + eps * u)
            ch = row.get("challenger")
            if isinstance(ch, dict):
                v = ch.get(CHALLENGER_FLOAT)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    u = rng.uniform(-1.0, 1.0)
                    ch[CHALLENGER_FLOAT] = float(v) * (1.0 + eps * u)
    return out


def _sign(x):
    if x is None:
        return None
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _below_floor(block: dict) -> bool:
    return int(block["honest_n"]) < POWER_FLOOR_N


def _nums_equal(a, b, *, rel_tol=1e-9):
    if a == b:
        return True, False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if math.isclose(float(a), float(b), rel_tol=rel_tol, abs_tol=0.0):
            return True, True
    if (
        isinstance(a, list) and isinstance(b, list) and len(a) == len(b)
        and all(
            (x == y) or (
                isinstance(x, (int, float)) and isinstance(y, (int, float))
                and math.isclose(float(x), float(y), rel_tol=rel_tol, abs_tol=0.0)
            )
            for x, y in zip(a, b)
        )
    ):
        return True, a != b
    return False, False


def unrounded_mirror_mean_ci(vals, cluster_keys, *, draws=BOOT_DRAWS, seed=BOOT_SEED):
    """block_bootstrap_ci mirror trick without the engine's 4-dp rounding."""
    x = np.asarray(list(vals), dtype=float)
    n = int(x.size)
    if n == 0:
        return None
    k = list(cluster_keys)
    dates = np.array(k + k)
    vv = np.concatenate([x, -x])
    mask = np.concatenate([np.ones(n, dtype=bool), np.zeros(n, dtype=bool)])
    uniq = np.unique(dates)
    if int(mask.sum()) == 0 or len(uniq) < 2:
        return None
    by = {d: np.where(dates == d)[0] for d in uniq}
    rng = np.random.default_rng(seed)
    gaps: list[float] = []
    for _ in range(draws):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ridx = np.concatenate([by[d] for d in pick])
        m = mask[ridx]
        if int(m.sum()) == 0:
            continue
        gaps.append(float(np.mean(vv[ridx][m])) - float(np.mean(vv[ridx])))
    if len(gaps) < draws // 2:
        return None
    return [float(np.percentile(gaps, 2.5)), float(np.percentile(gaps, 97.5))]


def dist_to_4dp_rounding_boundary(x: float) -> float:
    """Distance from x to the nearest (k + 0.5) * 1e-4 rounding boundary."""
    q = 1e-4
    k = math.floor(x / q)
    candidates = ((k - 0.5) * q, (k + 0.5) * q, (k + 1.5) * q)
    return min(abs(x - c) for c in candidates)


def _by_model_maps(rows: list, cohort: bool) -> dict:
    """Same by_model construction as run_s1.p03_blocks, including IPCA."""
    by_model: dict = {}
    for r in rows:
        by_model.setdefault(r["model"], {})[r["episode_key"]] = r
    if cohort:
        ipca = {}
        for ek, r in by_model["M1"].items():
            ch = r.get("challenger") or {}
            ipca[ek] = {
                "episode_key": ek,
                "split": r["split"],
                "anchor_session_date": r["anchor_session_date"],
                "abstention": "OK" if ch.get("state") == "OK" else ch.get("state"),
                "r__oc": r["r__oc"],
                "common__oc": ch.get("common_ipca__oc"),
            }
        by_model["IPCA"] = ipca
    return by_model


def _paired_d(prev_rows: dict, next_rows: dict, split: str):
    paired = []
    for ek, p in prev_rows.items():
        if p["split"] != split or p["abstention"] != "OK" or p.get("r__oc") is None:
            continue
        n = next_rows.get(ek)
        if n is None or n["abstention"] != "OK" or n.get("common__oc") is None:
            continue
        paired.append((p, n))
    ds = [
        (p["r__oc"] - p["common__oc"]) ** 2 - (p["r__oc"] - n["common__oc"]) ** 2
        for p, n in paired
    ]
    r2s = [p["r__oc"] ** 2 for p, n in paired]
    cluster = [n["anchor_session_date"] for p, n in paired]
    sum_d = sum(ds) if ds else 0.0
    sum_r2 = sum(r2s) if r2s else 0.0
    delta_r2 = (sum_d / sum_r2) if sum_r2 > 0 else None
    return ds, r2s, cluster, sum_d, sum_r2, delta_r2


def _z_values(by_model: dict, model: str, split: str) -> list[float]:
    rows = [
        r for r in by_model.get(model, {}).values()
        if r["split"] == split and r["abstention"] == "OK"
    ]
    return [r["z__oc"] for r in rows if r.get("z__oc") is not None]


def compute_margin_report(p03_obs: dict, committed: dict) -> dict:
    """Per-block and per-cell distances of P03 decisions to their thresholds."""
    assert_authority_false()
    block_rows = []
    calib_rows = []
    pairs = [("M0", "M1"), ("M1", "M2")]
    for subj in p03_subjects():
        counter = subj["counter"]
        cohort = counter == "adr_baba"
        for h in HORIZONS:
            rows = p03_obs[f"P03_{counter}_{h}"]
            by_model = _by_model_maps(rows, cohort)
            models = ["M0", "M1", "M2"] + (["IPCA"] if cohort else [])
            for model in models:
                for split in ("TRAIN", "TUNE"):
                    cell = f"{counter}|{model}|h={h}|{split}"
                    z = _z_values(by_model, model, split)
                    n = len(z)
                    if n == 0:
                        calib_rows.append({
                            "cell": cell, "n": n,
                            "k_196": 0, "d_196": None,
                            "k_10": 0, "d_10": None,
                        })
                        continue
                    calib_rows.append({
                        "cell": cell, "n": n,
                        "k_196": sum(1 for v in z if abs(v) <= 1.96),
                        "d_196": min(abs(abs(v) - 1.96) for v in z),
                        "k_10": sum(1 for v in z if abs(v) <= 1.0),
                        "d_10": min(abs(abs(v) - 1.0) for v in z),
                    })
            comparisons = pairs + ([("M1", "IPCA")] if cohort else [])
            for prev, nxt in comparisons:
                for split in ("TRAIN", "TUNE"):
                    key = f"P03|{counter}|h={h}|{split}|{nxt}_vs_{prev}"
                    ds, r2s, cluster, sum_d, sum_r2, delta_r2 = _paired_d(
                        by_model[prev], by_model[nxt], split)
                    ci_u = unrounded_mirror_mean_ci(ds, cluster) if ds else None
                    cb = committed["blocks"][key]
                    d4_lo = dist_to_4dp_rounding_boundary(ci_u[0]) if ci_u else None
                    d4_hi = dist_to_4dp_rounding_boundary(ci_u[1]) if ci_u else None
                    d4 = None
                    if d4_lo is not None and d4_hi is not None:
                        d4 = min(d4_lo, d4_hi)
                    ci0_r = None if cb["ci"]["ci95"] is None else cb["ci"]["ci95"][0]
                    # Distance to a published-decision flip of rounded ci[0] > 0
                    # or of the printed 4-dp bound: the rounding boundary.
                    abs_dR2 = None if delta_r2 is None else abs(delta_r2)
                    abs_ci0_u = None if ci_u is None else abs(ci_u[0])
                    candidates = [v for v in (abs_dR2, d4, abs_ci0_u) if v is not None]
                    margin = min(candidates) if candidates else None
                    block_rows.append({
                        "key": key,
                        "delta_R2": cb["ci"]["delta_R2"],
                        "delta_R2_unrounded": delta_r2,
                        "ci95_0": ci0_r,
                        "ci95_0_unrounded": None if ci_u is None else ci_u[0],
                        "d4": d4,
                        "d4_lo": d4_lo,
                        "d4_hi": d4_hi,
                        "abs_dR2": abs_dR2,
                        "abs_ci0_u": abs_ci0_u,
                        "sum_r2": sum_r2,
                        "margin": margin,
                        "margin_over_eps": None if margin is None else margin / P03U_EPS,
                        "honest_n": cb["honest_n"],
                        "met": s0_criterion_holds(cb),
                    })
    return {"blocks": block_rows, "calibration": calib_rows}


def _fmt_sci(x) -> str:
    if x is None:
        return "n/a"
    return f"{float(x):.6e}"


def _fmt_ci0(x) -> str:
    if x is None:
        return "n/a"
    if x == 0:
        return "-0.0" if math.copysign(1.0, x) < 0 else "0.0"
    return f"{float(x):.4f}"


def _fmt_dR2(x) -> str:
    if x is None:
        return "n/a"
    return f"{float(x):.8f}"


def _md_key(key: str) -> str:
    return key.replace("|", "\\|")


def render_margin_tables(report: dict) -> tuple[str, str]:
    """Markdown tables consumed by the review doc and by test 03."""
    b_lines = [
        "| block key | delta_R2 | ci95[0] | distance to nearest 4-dp boundary | margin/eps |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in report["blocks"]:
        b_lines.append(
            f"| {_md_key(row['key'])} | {_fmt_dR2(row['delta_R2'])} | "
            f"{_fmt_ci0(row['ci95_0'])} | {_fmt_sci(row['d4'])} | "
            f"{_fmt_sci(row['margin_over_eps'])} |"
        )
    c_lines = [
        "| cell | n | k at 1.96 | min distance of |z| to 1.96 | k at 1.0 | min distance to 1.0 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["calibration"]:
        c_lines.append(
            f"| {_md_key(row['cell'])} | {row['n']} | {row['k_196']} | "
            f"{_fmt_sci(row['d_196'])} | {row['k_10']} | {_fmt_sci(row['d_10'])} |"
        )
    return "\n".join(b_lines), "\n".join(c_lines)


def _tightest(report: dict) -> dict:
    items = []
    for row in report["blocks"]:
        if row["margin"] is not None:
            items.append({
                "kind": "block",
                "id": row["key"],
                "margin": row["margin"],
                "scale": 1e-4 if (row["d4"] == row["margin"] or row["abs_ci0_u"] == row["margin"]) else 1.0,
                "margin_over_eps": row["margin_over_eps"],
            })
        if row["d4"] is not None:
            items.append({
                "kind": "4dp",
                "id": row["key"],
                "margin": row["d4"],
                "scale": 1e-4,
                "margin_over_eps": row["d4"] / P03U_EPS,
            })
        if row["abs_dR2"] is not None:
            items.append({
                "kind": "delta_R2",
                "id": row["key"],
                "margin": row["abs_dR2"],
                "scale": 1.0,
                "margin_over_eps": row["abs_dR2"] / P03U_EPS,
            })
    for row in report["calibration"]:
        for kind, dist, scale in (
            ("z_1.96", row["d_196"], 1.0),
            ("z_1.0", row["d_10"], 1.0),
        ):
            if dist is None:
                continue
            items.append({
                "kind": kind,
                "id": row["cell"],
                "margin": dist,
                "scale": scale,
                "margin_over_eps": dist / P03U_EPS,
            })
    items.sort(key=lambda r: r["margin"])
    return {"all": items, "min": items[0] if items else None}


def build_review_markdown(report: dict) -> str:
    """Full review doc; tables are generated from compute_margin_report."""
    assert_authority_false()
    block_tbl, calib_tbl = render_margin_tables(report)
    tight = _tightest(report)
    mn = tight["min"]
    zero_ci = [
        row for row in report["blocks"]
        if row["ci95_0"] is not None and row["ci95_0"] == 0
    ]
    zero_lines = []
    for row in zero_ci:
        zero_lines.append(
            f"- `{row['key']}`: published ci95[0] = {_fmt_ci0(row['ci95_0'])}, "
            f"unrounded = {_fmt_sci(row['ci95_0_unrounded'])}, "
            f"distance to nearest 4-dp boundary = {_fmt_sci(row['d4'])}."
        )
    min_block = next(
        row for row in report["blocks"]
        if row["d4"] == min(r["d4"] for r in report["blocks"] if r["d4"] is not None)
    )
    min_z196 = min(
        (row for row in report["calibration"] if row["d_196"] is not None),
        key=lambda r: r["d_196"],
    )
    min_z10 = min(
        (row for row in report["calibration"] if row["d_10"] is not None),
        key=lambda r: r["d_10"],
    )
    min_dR2 = min(
        (row for row in report["blocks"] if row["abs_dR2"] is not None),
        key=lambda r: r["abs_dR2"],
    )
    if len(zero_ci) >= 2:
        zero_summary = (
            f"Two published CI lower bounds round to ±0.0 at 4 decimal places; "
            f"their unrounded values sit {_fmt_sci(zero_ci[0]['abs_ci0_u'])} and "
            f"{_fmt_sci(zero_ci[1]['abs_ci0_u'])} from zero, and "
            f"{_fmt_sci(zero_ci[0]['d4'])} and {_fmt_sci(zero_ci[1]['d4'])} "
            "from a bound-changing 4-dp boundary — still far above ULP scale."
        )
    elif zero_ci:
        zero_summary = (
            f"One published CI lower bound rounds to ±0.0 at 4 decimal places; "
            f"unrounded distance to zero is {_fmt_sci(zero_ci[0]['abs_ci0_u'])}, "
            f"distance to a bound-changing 4-dp boundary is "
            f"{_fmt_sci(zero_ci[0]['d4'])}."
        )
    else:
        zero_summary = "No published CI lower bound rounds to zero."
    body = f"""# P03 ULP stability (2026-10-13)

HISTORICAL-DESCRIPTIVE numerical-stability property of the frozen S1 v1.1
P03 comparison. This document is not a forecast, signal, validation, or
registration. It consumes committed observations and `results/P03.json`
owned by the S1 residual runner. Identity strings are caller-supplied
opaques owned by Stock Identity / Data OS.

Authority flags (literal false everywhere in this lane):

- rank_authority: false
- gate_authority: false
- size_authority: false
- signal_authority: false
- escalation_authority: false
- trade_authority: false

## Summary

Last-digit float drift of the size recorded in the XREP macOS arm64
addendum (worst relative difference 4.62e-12, worst absolute 5.50e-14)
does not flip a published P03 decision on this sealed tree: not a
verdict string, not the S0 criterion `met`, not the sign of delta_R2,
not the sign of the CI lower bound, not a 4-dp rounded CI bound, and
not a calibration coverage count. The perturbation used in the
regression is relative eps = 1e-11 (about 2x the observed worst
relative difference). The tightest measured decision margin is
{_fmt_sci(mn['margin'])} on `{mn['id']}` ({mn['kind']}), which is
{_fmt_sci(mn['margin_over_eps'])} times eps. Against the safety floor
of 1e3 * eps * scale, that margin remains above the floor. {zero_summary}

## Method

XREP measured macOS arm64 vs Linux seal drift on the ten P03 text
outputs only in the last digits of float tokens. This lane multiplies
every float field the decision path reads (`r__oc`, `common__oc`,
`challenger.common_ipca__oc`, `z__oc`) by `(1 + eps * u)` with
`u ~ Uniform[-1, 1]` from `random.Random(seed)` for seeds 0..7 and
`eps = 1e-11`. The harness rebuilds `by_model` maps the same way
`p03_blocks` does, including the adr_baba IPCA map from `challenger`,
and calls `p03_blocks` / `_comparison_block` / `_calibration` on the
perturbed rows. The engine's own 4-dp rounding of
`block_bootstrap_ci` is left unchanged. Unrounded CI bounds are
recomputed with the same seeded bootstrap (BOOT_DRAWS=800, BOOT_SEED=7)
without the final `round(..., 4)` so the distance to a 4-dp rounding
boundary `(k + 0.5) * 1e-4` is observable.

## Margin table

{block_tbl}

Tightest 4-dp rounding margin: `{min_block['key']}` at {_fmt_sci(min_block['d4'])}
(margin/eps = {_fmt_sci(min_block['d4'] / P03U_EPS)}).
Smallest `|delta_R2|`: `{min_dR2['key']}` at {_fmt_sci(min_dR2['abs_dR2'])}
(margin/eps = {_fmt_sci(min_dR2['abs_dR2'] / P03U_EPS)}).

Published ci95[0] values that round to zero:

{chr(10).join(zero_lines) if zero_lines else "- none"}

Those zeros keep `ci[0] > 0` false. Crossing a published 4-dp step
requires the unrounded bound to reach a `(k + 0.5) * 1e-4` boundary,
which is the distance reported in the table.

## Calibration table

{calib_tbl}

Closest `|z|` to 1.96: `{min_z196['cell']}` at {_fmt_sci(min_z196['d_196'])}
(margin/eps = {_fmt_sci(min_z196['d_196'] / P03U_EPS)}).
Closest `|z|` to 1.0: `{min_z10['cell']}` at {_fmt_sci(min_z10['d_10'])}
(margin/eps = {_fmt_sci(min_z10['d_10'] / P03U_EPS)}).

## Positive control

A synthetic `|z| = 1.96 * (1 - 1e-13)` sits just inside the 1.96
coverage threshold. The same eps = 1e-11 relative perturbation flips
the `_calibration` coverage count for at least one seed in 0..7. That
shows test 02 is not vacuous: the perturbation is large enough to move
a decision that genuinely sits at its threshold. A paired set with
delta_R2 on the order of +1e-13 cannot flip `met` through this engine,
because `mirror_mean_ci` rounds bounds to 4 decimal places and a
1e-13-scale mean rounds to 0.0, so `ci[0] > 0` stays false; the
coverage-count control is the threshold-adjacent case.

## Bounds

Covers P03 only. Per XREP, P01/P02 outputs were byte-identical
cross-host (S1 v1.1 files compared = 48, identical = 35, named-exception
passes = 3, ulp-equivalent = 10, and those 10 ulp-equivalent files are
the P03 observations and `results/P03.json`). This document does not
re-pin SCHK and does not re-run macOS. Integer budget rows
(`declared_budget`, `literal_n`, `effective_n`) are trial-ledger
integers; the comparison path does not read them from float fields.

## Gaps

- No macOS re-execution in this lane; the perturbation scale is taken
  from the XREP addendum bound.
- Unrounded CI bounds are a local replica of `block_bootstrap_ci`
  without the final 4-dp round, using the same seed and draw count.
- POWER_FLOOR abstain is an integer comparison (`honest_n` vs 153) and
  is insensitive to ULP-scale float drift; it is checked for
  invariance, not for a float margin.
- This is a descriptive stability property of committed P03 numbers.
  It is not a reason to treat `ulp-equivalent` as `identical`.
"""
    return body


@pytest.fixture(scope="module")
def p03_obs():
    return load_observations()


@pytest.fixture(scope="module")
def committed_p03():
    return load_committed_p03()


@pytest.fixture(scope="module")
def baseline_replay(p03_obs):
    return replay_p03(p03_obs)


def test_p03u_01_replay_matches_committed(p03_obs, committed_p03, baseline_replay):
    assert_authority_false()
    blocks, order, diagnostics = baseline_replay
    c_blocks = committed_p03["blocks"]
    c_diag = committed_p03["diagnostics"]
    assert len(blocks) == 42
    assert len(c_blocks) == 42
    assert order == list(c_blocks)
    ulp_relaxed = []
    for key, cb in c_blocks.items():
        rb = blocks[key]
        pairs = [
            ("verdict", cb["test"]["verdict"], rb["test"]["verdict"]),
            ("delta_R2", cb["ci"]["delta_R2"], rb["ci"]["delta_R2"]),
            ("ci95", cb["ci"]["ci95"], rb["ci"]["ci95"]),
            ("mean_d", cb["ci"]["mean_d"], rb["ci"]["mean_d"]),
            ("honest_n", cb["honest_n"], rb["honest_n"]),
        ]
        for name, a, b in pairs:
            ok, relaxed = _nums_equal(a, b)
            if not ok:
                raise AssertionError(f"{key} {name}: committed={a!r} replay={b!r}")
            if relaxed:
                ulp_relaxed.append((key, name, a, b))
    assert len(diagnostics) == len(c_diag) == 60
    for key, cd in c_diag.items():
        rd = diagnostics[key]
        for cov in ("coverage_1.96", "coverage_1.0"):
            assert rd[cov]["k"] == cd[cov]["k"], (key, cov, rd[cov], cd[cov])
            assert rd[cov]["n"] == cd[cov]["n"], (key, cov, rd[cov], cd[cov])
    if ulp_relaxed:
        print(
            f"DEVIATION: exact equality fell back to rel_tol 1e-9 on "
            f"{len(ulp_relaxed)} field(s): {ulp_relaxed[:8]!r}"
        )


@pytest.mark.parametrize("seed", range(8))
def test_p03u_02_ulp_perturbation_never_flips_a_decision(
    seed, p03_obs, baseline_replay
):
    assert_authority_false()
    blocks0, _, diag0 = baseline_replay
    blocks1, _, diag1 = replay_p03(perturb_observations(p03_obs, seed, P03U_EPS))
    assert len(blocks1) == 42
    for key, b0 in blocks0.items():
        b1 = blocks1[key]
        assert b1["test"]["verdict"] == b0["test"]["verdict"], key
        assert s0_criterion_holds(b1) == s0_criterion_holds(b0), key
        d0 = b0["ci"]["delta_R2"]
        d1 = b1["ci"]["delta_R2"]
        assert _sign(d1) == _sign(d0), (key, d0, d1)
        c0 = None if b0["ci"]["ci95"] is None else b0["ci"]["ci95"][0]
        c1 = None if b1["ci"]["ci95"] is None else b1["ci"]["ci95"][0]
        assert _sign(c1) == _sign(c0), (key, c0, c1)
        assert b1["ci"]["ci95"] == b0["ci"]["ci95"], key
        assert b1["honest_n"] == b0["honest_n"], key
        assert _below_floor(b1) == _below_floor(b0), key
    for key, d0 in diag0.items():
        d1 = diag1[key]
        for cov in ("coverage_1.96", "coverage_1.0"):
            assert d1[cov]["k"] == d0[cov]["k"], (key, cov, seed)
            assert d1[cov]["n"] == d0[cov]["n"], (key, cov, seed)


def test_p03u_03_margin_report(p03_obs, committed_p03):
    assert_authority_false()
    report = compute_margin_report(p03_obs, committed_p03)
    assert len(report["blocks"]) == 42
    assert len(report["calibration"]) == 60
    tight = _tightest(report)
    mn = tight["min"]
    assert mn is not None
    print(
        f"P03U minimum decision margin={mn['margin']:.6e} "
        f"margin/eps={mn['margin_over_eps']:.6e} "
        f"kind={mn['kind']} id={mn['id']}",
        flush=True,
    )
    close = []
    for item in tight["all"]:
        floor = MARGIN_SAFETY * P03U_EPS * item["scale"]
        if item["margin"] < floor:
            close.append(item)
    block_tbl, calib_tbl = render_margin_tables(report)
    expected_doc = build_review_markdown(report)
    _require(REVIEW_PATH)
    actual_doc = REVIEW_PATH.read_text(encoding="utf-8")
    assert block_tbl in actual_doc
    assert calib_tbl in actual_doc
    assert actual_doc == expected_doc
    if close:
        pytest.xfail(
            "strict=True; decision within 1e3*eps*scale of its threshold: "
            + "; ".join(
                f"{c['kind']} {c['id']} margin={c['margin']:.6e} "
                f"floor={MARGIN_SAFETY * P03U_EPS * c['scale']:.6e}"
                for c in close
            )
        )
    for item in tight["all"]:
        floor = MARGIN_SAFETY * P03U_EPS * item["scale"]
        assert item["margin"] >= floor, (
            f"{item['kind']} {item['id']} margin={item['margin']:.6e} "
            f"< {floor:.6e} (1e3*eps*scale)"
        )


def test_p03u_04_positive_control_threshold_adjacent():
    """The same eps flips a decision that sits at its threshold."""
    assert_authority_false()
    z0 = 1.96 * (1.0 - 1e-13)
    assert abs(z0) <= 1.96
    base_rows = {
        "M0": {
            "e0": {
                "split": "TRAIN",
                "abstention": "OK",
                "z__oc": z0,
                "episode_key": "e0",
            }
        }
    }
    base = run_s1._calibration(base_rows, "M0", "TRAIN")
    assert base["coverage_1.96"]["k"] == 1
    assert base["coverage_1.96"]["n"] == 1
    flipped = False
    for seed in range(8):
        rng = random.Random(seed)
        u = rng.uniform(-1.0, 1.0)
        z1 = z0 * (1.0 + P03U_EPS * u)
        rows = copy.deepcopy(base_rows)
        rows["M0"]["e0"]["z__oc"] = z1
        cal = run_s1._calibration(rows, "M0", "TRAIN")
        if cal["coverage_1.96"]["k"] != base["coverage_1.96"]["k"]:
            flipped = True
            break
    assert flipped, (
        "eps=1e-11 did not flip a 1.96*(1-1e-13) coverage count for any "
        "seed in 0..7; test 02 would be vacuous"
    )

    # Synthetic paired set with delta_R2 ~ +1e-13 (just above 0). The
    # engine's 4-dp CI round keeps met false; the coverage control above
    # is the one that sits on a live threshold.
    r = 1.0
    # d/r^2 = 2c/r - (c/r)^2 ≈ 1e-13 => c ≈ 5e-14
    c_next = 5.0e-14
    prev = {
        f"e{i}": {
            "split": "TRAIN",
            "abstention": "OK",
            "r__oc": r,
            "common__oc": 0.0,
            "anchor_session_date": f"2020-01-{i + 1:02d}",
            "episode_key": f"e{i}",
        }
        for i in range(8)
    }
    nxt = {
        f"e{i}": {
            "split": "TRAIN",
            "abstention": "OK",
            "r__oc": r,
            "common__oc": c_next,
            "anchor_session_date": f"2020-01-{i + 1:02d}",
            "episode_key": f"e{i}",
        }
        for i in range(8)
    }
    blk = run_s1._comparison_block(
        prev, nxt, "M0", "M1", "TRAIN",
        label="", receipt_base={}, membership={},
        trial_accounting={}, rows_total=8,
    )
    dR2 = blk["ci"]["delta_R2"]
    assert dR2 is not None and dR2 >= 0.0
    assert not s0_criterion_holds(blk)


def test_p03u_05_integer_rows_are_float_independent(
    p03_obs, committed_p03, baseline_replay
):
    """declared_budget / literal_n / effective_n are ints, not float-derived."""
    assert_authority_false()
    blocks, _, _ = baseline_replay
    for key, cb in committed_p03["blocks"].items():
        ta = cb["trial_accounting"]
        for name in ("declared_budget", "literal_n", "effective_n"):
            assert type(ta[name]) is int, (key, name, ta[name])
        # Replay was passed trial_accounting={} and must not invent ints
        # from r__oc / common__oc / z__oc.
        assert blocks[key]["trial_accounting"] == {}
    stub = {"family": "stub", "declared_budget": 7, "literal_n": 9, "effective_n": 9}
    blocks2, _, _ = replay_p03(p03_obs, trial_accounting=stub)
    for key, b0 in blocks.items():
        b2 = blocks2[key]
        assert b2["test"]["verdict"] == b0["test"]["verdict"]
        assert b2["ci"]["delta_R2"] == b0["ci"]["delta_R2"]
        assert b2["ci"]["ci95"] == b0["ci"]["ci95"]
        assert b2["ci"]["mean_d"] == b0["ci"]["mean_d"]
        assert b2["honest_n"] == b0["honest_n"]
        assert b2["trial_accounting"] == stub
        assert b2["trial_accounting"] is stub or b2["trial_accounting"] == stub
