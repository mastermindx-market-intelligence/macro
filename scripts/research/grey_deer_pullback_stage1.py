"""Grey Deer pullback stage-1 executing script (GD-W3, part 1 of 2).

Executes ``research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md`` (blob
``49a68b5e9c6543d662044b0aa391c4b6e6e6052e``) against its eligible-input
manifest ``research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md``
(v1.0.0, blob ``38925409555d046eb9d3ad38ddaba33e2159a3d3``). One execution per
revision; a silent change to any frozen choice voids the revision. The real
run belongs to the Fable seat; this build never executes the real data path
(only ``--help`` / ``--dry-run`` are exercised in GD-W3-BUILD).

Part split history: GD-W3-BUILD part 1 delivered the script contract, run
steps 1-11 and the identity/purge/fold/crossing machinery; part 2 completed
``evaluate_and_write`` (steps 12-18: comparison sets, metrics, episodes and
the power floor, the paired bootstrap and the 12 gated claims, LOEO, the
negative control, the INC replay and the SS12 artifacts).

Run order in :func:`main` (each step a named, separately testable function):

1.  ``verify_identities``  - prereg sha256 + blob, manifest blob + version,
    script/test blob == HEAD (bypassed only under ``--allow-dirty`` as
    deviation ``DIRTY_TREE``); records run commit/blob shas.
2.  ``hydrate``            - ``python -m scripts.fetch_r2 --dirs massive_stock_day``
    (rc != 0 -> ``HYDRATE_FAILED``; rc 0 is not success by itself - only step 3
    establishes readability).
3.  ``load_sample``        - ``load_ticker("SPY")``; empty -> ``SOURCE_UNREADABLE``.
    Deferred import: ``collectors.massive_stock_day`` pulls ``requests``/``yaml``
    (via ``collectors.base``/``lib.config``), so it is imported inside the
    function to keep the module import thin for the dedicated test file's CI
    environment. Tests patch ``sys.modules["collectors.massive_stock_day"]``.
4.  ``sample_identity``    - the prereg SS3 identity recipe applied to the frame
    ``load_ticker`` returned (never a second read); mismatch ->
    ``SAMPLE_IDENTITY_MISMATCH`` (never re-hashed into agreement). Rows before
    ``WINDOW_START`` are dropped only after hashing and counted.
5.  ``integrity_checks``   - sessions/closes/price-basis (``ABSENT_SESSION``,
    ``PRICE_INVALID``, ``PRICE_BASIS_DISCONTINUITY``) then manifest SS7
    refusals 1-6 as named checks (``MANIFEST_REFUSAL_UNEVALUABLE`` records a
    refusal that cannot be evaluated; nothing silently passes).
6.  ``trial_ledger_scope`` - ``register_trials(family="grey_deer_pullback_v1",
    budget=69, basis="itemized")`` wraps everything from here on.
7.  ``build_labels``       - ``A_h = forward_max_loss(close, h)``,
    ``Y_h = loss_event(A_h)``; incomplete windows are IMMATURE (NaN), never 0.
8.  ``build_features``     - rv20/rv63 (``realized_vol``), log rv, sma_gap21/63,
    dd63, r5, r10; any non-finite feature at idx >= 63 ->
    ``FEATURE_UNDEFINED_AFTER_WARMUP`` (refuse, never impute).
9.  ``build_populations`` / ``census_populations`` - P-all = warm (idx >= 63)
    and mature; P-active is recorded ``OBSERVER_NOT_ON_MAIN`` (observer on
    draft PR #8188, not main) and never run; census typed exclusions:
    ``PRE_ENTITLEMENT``, ``WARMUP``, ``IMMATURE`` (``TRAINING_FOLD_THIN`` is
    counted per block in step 11 and merged into the final census).
10. ``build_fold_calendar`` / ``purged_training_indices`` - expanding folds;
    first test origin idx 315 (= the 253rd warm origin), blocks of 126, a
    final block shorter than 63 merges into its predecessor; purge keeps
    training origins with ``idx(t) + h <= idx(s0)``; embargo 0; a purged
    training set with < 20 origins or < 2 events is ``TRAINING_FOLD_THIN``
    for every configuration except B0 (B0 always issues).
11. ``run_fits`` - per-block standardisation (mean/std ddof=0 of that block's
    purged training rows of that population; std 0 -> deviation
    ``FEATURE_DEGENERATE`` and that config abstains the block); B0
    ``(k+0.5)/(n+1)``; L2 logistic (B1-20/63, B2-21/63, M3-ALL C=1.0, plus the
    M3-ALL C=0.1 sensitivity row - never a gate) with intercept unpenalised;
    Q0 training-prefix empirical quantiles; Q0-within-rv20-tercile cells with
    ``TRAINING_CELL_THIN_FALLBACK`` to the block's Q0 (raw rv20, exactly as
    prereg SS6 names the feature); Q3-ALL per-tau linear quantile regression
    by LP (``linprog(method="highs")``), crossing check on UNCLIPPED
    predictions (crossing origin abstains ``QUANTILE_CROSSING``), then clip
    below at 0 - Q0/Q1 are never clipped. Solver failures abstain the block
    as ``FIT_NONCONVERGENCE``.
12. ``build_comparison_sets``      - SS7 comparison set per (h, pop, family):
    the intersection of origins where EVERY compared configuration issued
    (binary: B0, B1-20, B1-63, B2-21, B2-63, M3-ALL C=1.0; quantile: Q0, Q1,
    Q3-ALL); per-config issued/abstained counts by type; N_common reported.
13. ``compute_point_metrics``     - SS9 metrics on the comparison set (Brier,
    BSS vs B0, CITL, WACE/RWSCE over bins with n_b >= 100, AUC ties 1/2,
    Richardson V at alpha in {0.5 b_h, b_h, 2 b_h}; quantile pinball,
    coverage, width, tail, crossings), each also by calendar year, by test
    block and by training rv20 tercile (quantile: year and block; tercile
    bounds are that block's purged-training rv20 bounds, the SS6 Q1 rule).
14. ``compute_episodes``         - SS8: clusters merge on session-index gaps
    <= h; episode window [first-21, last+h]; episodes are unions of clusters
    whose windows overlap; honest-N (origins, events, clusters, episodes,
    distinct event months) and the power floor (>= 10 episodes AND >= 10
    event months, else UNDERPOWERED_DISCLOSED whatever the bounds say).
15. ``bootstrap_and_gates``      - SS10/SS11: paired circular moving-block
    bootstrap (L = max(21, 2h), sensitivity L = h; N_DRAWS 10,000;
    SeedSequence([221011, h, pop, fam, var]); one index matrix per
    (h, pop, family, variant) cell reused for every configuration and
    statistic; every statistic, including the best-baseline maximum in ΔV
    and the better-reference minimum in pinball skill, recomputed inside
    each draw; undefined statistics at their failing extreme; bounds with
    np.quantile at 0.05/12).  The 12 gated claims (binary/quantile x
    P-all/P-active x 5/10/21): binary conditions 1-7, quantile conditions
    1-5, intersection-union; blocked P-active claims stay
    ``underpowered/blocked claim`` (OBSERVER_NOT_ON_MAIN) and keep their
    share of the family level.  LOEO drops each episode window from the
    evaluation set (point estimates only, no draws, no refit) -> FRAGILE.
    Baseline-against-baseline differences (B1/B2 vs B0, Q1 vs Q0 on P-all)
    carry intervals as descriptive measurement, never claims.
16. ``run_negative_control``     - SS12: M3-ALL (C=1) and Q3-ALL refit per
    block with the training labels/targets rolled by half their length
    (``np.roll(y, len(y) // 2)``, deterministic, no seed); BSS, V at
    alpha = b_h, pinball skill - expected at or below 0; never a gate.
17. ``run_inc``                  - SS6 INC: the 2026-09-22 displayed-
    probability replay built exactly as
    ``risk_radar_displayed_probability_audit.py`` (blob pinned) does it,
    scored against its OWN CURRENT_VINTAGE native labels on the P-all
    evaluation origins it covers; own table, never pooled, never a gate;
    the artifact records the calibration.json overlay blob sha; any import
    or data failure -> {"blocked": "INC_SOURCE_UNAVAILABLE", ...}.
18. ``evaluate_and_write``       - assembles the SS12 artifacts: the JSON
    (key tree below) and the markdown GENERATED from it (aggregates only),
    prints the gate table, returns None (a failed gate is a result).

Typed refusals print ``BLOCKED / <TYPE>`` as the FIRST stdout line, write
``<out-dir>/PULLBACK_STAGE1_RESULTS_2026-10-11.json`` with ``{"blocked":
[{"type", "detail"}]}`` plus every identity already established, and return 2.
Nothing else prints before either completion or a refusal line.

Seed codes (assigned by prereg SS10 "Seeds"; centralised here for part 2):
``SeedSequence([SEED_ROOT, h, pop, fam, var])`` with pop 0 = P-all, 1 =
P-active; fam 0 = binary, 1 = quantile; var 0 = primary (L = max(21, 2h)),
1 = the L = h sensitivity rerun.

Artifact key tree (``PULLBACK_STAGE1_RESULTS_2026-10-11.json``; the markdown
is generated from the JSON, aggregates only, no per-day prices / raw closes /
Massive terms):

    schema                     "grey_deer_pullback_stage1/v1"
    prereg                     {path, blob_sha, sha256}
    manifest                   {path, blob_sha, version}
    run                        {utc, commit_sha, script_blob_sha, test_blob_sha,
                               python, numpy, pandas, scipy, hydrate{performed, rc}}
    sample                     {subframe_content_sha256, rows, first_date,
                               last_date, integrity[]}
    trial_budget               {family, budget, basis}
    census                     per (h, pop) typed-exclusion counts
    folds                      per-h block calendar + purge/thin facts
    configs                    per-config issued/abstained counts by type
    comparison_sets            per (h, family): compared configs, N_common,
                               per-config issued/abstained by type + point
                               metrics + slices (year / block / rv20 tercile),
                               baseline-vs-B0 and Q1-vs-Q0 differences with
                               intervals (descriptive, never claims), the
                               M3-ALL C=0.1 sensitivity row, bootstrap report
                               (primary L=max(21,2h) + sensitivity L=h)
    episodes                   per (h, family): honest-N (origins, events,
                               clusters, episodes, event months) + power floor
    gates                      the 12 gated claims, each row {id, h, pop,
                               claim, statistic, point, lb, threshold, flags,
                               verdict} + per-condition detail; P-active rows
                               are OBSERVER_NOT_ON_MAIN
    loeo                       per P-all claim: per-episode dropped point
                               estimates, minima, FRAGILE flag
    early_warning              per h: SS9 block for M3-ALL C=1.0 and INC
                               (cluster recall, lead, missed damage,
                               false-alarm share/time, alarm runs, censoring)
    abstention                 per (h, config): rate over the evaluation
                               origins, typed reasons, event vs non-event gap
    negative_control           per h: shifted-refit BSS, V at alpha=b_h,
                               pinball skill (expected at or below 0)
    inc                        incumbent replay: own CURRENT_VINTAGE table,
                               never pooled, never a gate; calibration.json
                               blob sha; or {"blocked": "INC_SOURCE_UNAVAILABLE"}
    deviations[]               {code, detail} for every logged departure
    blocked[]                  non-empty only on a typed refusal

Fit output shape (consumed by part 2): ``run_fits`` returns
``{"fits": {(h, block_idx, config_id): {"issued": bool ndarray over the
block's test origins, "reasons": object ndarray (None or the abstention
type), "binary": float ndarray p or "quantile": {"0.5"|"0.8"|"0.9": ndarray
q}, "train": {origins, events}}, ...}, "blocks": {(h, block_idx):
{"range": [s0, e0], "train_origins": n, "train_events": k, "thin": bool}},
"populations_blocked": {"P-active": "OBSERVER_NOT_ON_MAIN"},
"config_rows": [(h, config_id, abstention_type)] for the stage-2 blocked
M3-ACT / Q3-ACT and P-active rows}``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize
from scipy.special import expit
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import trial_ledger
from engine.vol_forecast import realized_vol
from lib import nyse_calendar
from lib import observed_moves as om

# ── frozen constants (prereg SS3-SS12; never flags) ──────────────────────────

AS_OF = "2026-10-07"
WINDOW_START = "2021-07-06"
HORIZONS = (5, 10, 21)
WARM_IDX = 63
FIRST_TEST_IDX = 315
BLOCK_LEN = 126
MIN_FINAL_BLOCK = 63
THRESHOLD = 0.05
TAUS = (0.5, 0.8, 0.9)
BASE_RATES = {5: 0.036, 10: 0.082, 21: 0.176}
C_MAIN = 1.0
C_SENS = 0.1
WACE_BINS = (0.0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 1.0)
WACE_MIN_BIN = 100
N_DRAWS = 10_000
SEED_ROOT = 221011
GATE_Q = 0.05 / 12
MIN_TRAIN_ORIGINS = 20
MIN_TRAIN_EVENTS = 2
MIN_CELL = 20
POWER_MIN_EPISODES = 10
POWER_MIN_MONTHS = 10
EPISODE_PRE = 21
TRIAL_FAMILY = "grey_deer_pullback_v1"
TRIAL_BUDGET = 69
PREREG_PATH = "research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md"
PREREG_BLOB = "49a68b5e9c6543d662044b0aa391c4b6e6e6052e"
PREREG_SHA256 = "b50ab2430b3450900d87f42d71b8accd61c30f0a326a795a9b2856a4115b07ee"
MANIFEST_PATH = "research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md"
MANIFEST_BLOB = "38925409555d046eb9d3ad38ddaba33e2159a3d3"
MANIFEST_VERSION = "1.0.0"
SUBFRAME_SHA256 = "c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb"
AUDIT_SCRIPT_BLOB = "b5b4f753a5e80d19e7e7a7b21f580146c4d02a29"

SCRIPT_PATH = "scripts/research/grey_deer_pullback_stage1.py"
TEST_PATH = "tests/test_grey_deer_pullback_stage1.py"
SCHEMA = "grey_deer_pullback_stage1/v1"
RESULTS_JSON_NAME = "PULLBACK_STAGE1_RESULTS_2026-10-11.json"
RESULTS_MD_NAME = "PULLBACK_STAGE1_RESULTS_2026-10-11.md"
IDENTITY_COLUMNS = ("date", "open", "high", "low", "close", "volume", "transactions")

# Seed codes assigned by prereg SS10 "Seeds" (documented in the module docstring).
SEED_CODES = {
    "pop": {"P-all": 0, "P-active": 1},
    "fam": {"binary": 0, "quantile": 1},
    "var": {"primary": 0, "L=h": 1},
}

FEATURE_COLUMNS = (
    "rv20",
    "rv63",
    "log_rv20",
    "log_rv63",
    "sma_gap21",
    "sma_gap63",
    "dd63",
    "r5",
    "r10",
)

# Frozen configurations (prereg SS6). "each" runs per population: P-all now,
# P-active blocked as OBSERVER_NOT_ON_MAIN until the observer is on main.
CONFIGURATIONS = (
    {"id": "B0", "kind": "binary", "population": "each", "features": (), "params": {}},
    {"id": "B1-20", "kind": "binary", "population": "each", "features": ("log_rv20",), "params": {"C": C_MAIN}},
    {"id": "B1-63", "kind": "binary", "population": "each", "features": ("log_rv63",), "params": {"C": C_MAIN}},
    {"id": "B2-21", "kind": "binary", "population": "each", "features": ("sma_gap21",), "params": {"C": C_MAIN}},
    {"id": "B2-63", "kind": "binary", "population": "each", "features": ("sma_gap63",), "params": {"C": C_MAIN}},
    {
        "id": "M3-ALL",
        "kind": "binary",
        "population": "P-all",
        "features": ("dd63", "r5", "r10", "log_rv20"),
        "params": {"C": C_MAIN},
    },
    {
        "id": "M3-ALL-C0.1",
        "kind": "binary",
        "population": "P-all",
        "features": ("dd63", "r5", "r10", "log_rv20"),
        "params": {"C": C_SENS},
        "sensitivity": True,  # SS6: sensitivity row only, never a gate
    },
    {"id": "Q0", "kind": "quantile", "population": "each", "features": (), "params": {}},
    {"id": "Q1", "kind": "quantile", "population": "each", "features": (), "params": {}},
    {
        "id": "Q3-ALL",
        "kind": "quantile",
        "population": "P-all",
        "features": ("dd63", "r5", "r10", "log_rv20"),
        "params": {},
    },
)
# Stage-2 / replay rows: recorded, never run in stage 1 (prereg SS5, SS12).
BLOCKED_CONFIG_ROWS = (
    {"id": "M3-ACT", "kind": "binary", "population": "P-active", "type": "OBSERVER_NOT_ON_MAIN"},
    {"id": "Q3-ACT", "kind": "quantile", "population": "P-active", "type": "OBSERVER_NOT_ON_MAIN"},
    {"id": "INC", "kind": "binary", "population": "P-all origins it covers", "type": None},  # part 2
)


class Blocked(RuntimeError):
    """A typed refusal: prints ``BLOCKED / <type>``, writes the artifact, rc 2."""

    def __init__(self, type_: str, detail: str = "") -> None:
        super().__init__(f"{type_}: {detail}")
        self.type = type_
        self.detail = detail


class _FitFailure(Exception):
    """Per-block/config fit abstention (never a run-level refusal)."""

    def __init__(self, type_: str, detail: str = "") -> None:
        super().__init__(f"{type_}: {detail}")
        self.type = type_
        self.detail = detail


def _git(*args: str) -> tuple[bool, str]:
    """Run git in ROOT; return (ok, stdout-or-stderr-tail)."""
    proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    out = (proc.stdout if proc.returncode == 0 else (proc.stderr or proc.stdout)).strip()
    return proc.returncode == 0, out


def _deviation(deviations: list[dict] | None, code: str, detail: str) -> None:
    if deviations is None:
        return
    deviations.append({"code": code, "detail": detail})


# ── step 1: identities ───────────────────────────────────────────────────────


def verify_identities(*, allow_dirty: bool = False, deviations: list[dict] | None = None) -> dict:
    """Prereg SS3 check 5 identities; first failure raises ``Blocked``."""
    prereg_file = ROOT / PREREG_PATH
    sha = hashlib.sha256(prereg_file.read_bytes()).hexdigest()
    if sha != PREREG_SHA256:
        raise Blocked("PREREG_IDENTITY_MISMATCH", f"file sha256 {sha} != frozen {PREREG_SHA256}")
    ok, out = _git("rev-parse", f"HEAD:{PREREG_PATH}")
    if not ok or out != PREREG_BLOB:
        raise Blocked("PREREG_IDENTITY_MISMATCH", f"git blob {out!r} != frozen {PREREG_BLOB} ({out[:120]})")

    ok, out = _git("rev-parse", f"HEAD:{MANIFEST_PATH}")
    if not ok or out != MANIFEST_BLOB:
        raise Blocked("MANIFEST_IDENTITY_MISMATCH", f"git blob {out!r} != frozen {MANIFEST_BLOB} ({out[:120]})")
    manifest_text = (ROOT / MANIFEST_PATH).read_text(encoding="utf-8")
    if MANIFEST_VERSION not in manifest_text:
        raise Blocked("MANIFEST_IDENTITY_MISMATCH", f"manifest file does not contain version {MANIFEST_VERSION}")

    ok, script_work = _git("hash-object", SCRIPT_PATH)
    ok2, script_head = _git("rev-parse", f"HEAD:{SCRIPT_PATH}")
    ok3, test_work = _git("hash-object", TEST_PATH)
    ok4, test_head = _git("rev-parse", f"HEAD:{TEST_PATH}")
    dirty = not (ok and ok2 and ok3 and ok4) or script_work != script_head or test_work != test_head
    if dirty:
        if not allow_dirty:
            raise Blocked(
                "DIRTY_TREE",
                "script/test working blobs != HEAD (run at the committed HEAD, or pass --allow-dirty "
                "to log the deviation and continue)",
            )
        _deviation(
            deviations,
            "DIRTY_TREE",
            f"script {script_work} vs HEAD {script_head}; test {test_work} vs HEAD {test_head}",
        )

    ok, commit = _git("rev-parse", "HEAD")
    if not ok:
        raise Blocked("PREREG_IDENTITY_MISMATCH", f"git rev-parse HEAD failed: {commit[:120]}")

    import scipy

    return {
        "schema": SCHEMA,
        "prereg": {"path": PREREG_PATH, "blob_sha": PREREG_BLOB, "sha256": PREREG_SHA256},
        "manifest": {"path": MANIFEST_PATH, "blob_sha": MANIFEST_BLOB, "version": MANIFEST_VERSION},
        "run": {
            "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "commit_sha": commit,
            "script_blob_sha": script_work if ok else "unavailable",
            "test_blob_sha": test_work if ok3 else "unavailable",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
        },
    }


# ── steps 2-3: hydrate + load ────────────────────────────────────────────────


def hydrate(*, skip: bool = False, deviations: list[dict] | None = None) -> dict:
    """Prereg SS3: fetch_r2 restore; rc != 0 blocks. rc 0 is not success."""
    if skip:
        _deviation(deviations, "HYDRATE_SKIPPED", "--skip-hydrate: using the existing store object")
        return {"performed": False, "rc": None}
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.fetch_r2", "--dirs", "massive_stock_day"],
        cwd=ROOT,
    )
    if proc.returncode != 0:
        raise Blocked("HYDRATE_FAILED", f"fetch_r2 rc={proc.returncode}")
    return {"performed": True, "rc": proc.returncode}


def load_sample() -> pd.DataFrame:
    """``load_ticker("SPY")``; empty frame blocks as SOURCE_UNREADABLE.

    The collectors import is deferred so importing this module stays thin
    (see module docstring); tests patch ``sys.modules`` at this exact name.
    """
    import collectors.massive_stock_day as massive_stock_day

    df = massive_stock_day.load_ticker("SPY")
    if df is None or df.empty:
        raise Blocked("SOURCE_UNREADABLE", "load_ticker('SPY') returned an empty frame (missing object or read error)")
    return df


# ── step 4: sample identity ──────────────────────────────────────────────────


def _enc(v) -> str:
    """The SS3 encoding: str as-is, NaN -> 'NA', else float hex."""
    if isinstance(v, str):
        return v
    if pd.isna(v):
        return "NA"
    return float(v).hex()


def normalize_subframe(df: pd.DataFrame) -> pd.DataFrame:
    """The SS3 normalisation applied to the in-memory frame (never a second read)."""
    df = df.reset_index(drop=("date" in df.columns))
    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    cols = list(IDENTITY_COLUMNS)
    return df[df["date"] <= AS_OF][cols].sort_values("date").reset_index(drop=True)


def subframe_sha256(sub: pd.DataFrame) -> str:
    """The SS3 content hash: header line, then one encoded line per row."""
    h = hashlib.sha256()
    h.update(("|".join(IDENTITY_COLUMNS) + "\n").encode())
    for row in sub.itertuples(index=False):
        h.update(("|".join(_enc(v) for v in row) + "\n").encode())
    return h.hexdigest()


def sample_identity(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Hash the frame, refuse on mismatch, then drop/count pre-window rows."""
    sub = normalize_subframe(df)
    sha = subframe_sha256(sub)
    if sha != SUBFRAME_SHA256:
        raise Blocked(
            "SAMPLE_IDENTITY_MISMATCH",
            f"computed subframe_content_sha256 {sha} != frozen {SUBFRAME_SHA256}; "
            "never re-hashed into agreement - the fix is a new prereg revision",
        )
    pre = int((sub["date"] < WINDOW_START).sum())
    window = sub[sub["date"] >= WINDOW_START].reset_index(drop=True)
    info = {
        "subframe_content_sha256": sha,
        "rows_hashed": int(len(sub)),
        "pre_window_rows_dropped": pre,
        "rows": int(len(window)),
        "first_date": str(window["date"].iloc[0]),
        "last_date": str(window["date"].iloc[-1]),
    }
    return info, window


# ── step 5: integrity checks ─────────────────────────────────────────────────


def _manifest_refusal_checks(window: pd.DataFrame) -> list[dict]:
    """Manifest SS7 refusals 1-6 as named checks in the manifest's own wording.

    A refusal that cannot be evaluated from the frame (plus the pinned
    identities of step 1) is recorded ``MANIFEST_REFUSAL_UNEVALUABLE`` with its
    number - never silently passed.
    """
    out: list[dict] = []
    dates = window["date"].tolist()
    volume = window["volume"].to_numpy(dtype=float)

    def add(number: int, wording: str, evidence_fn) -> None:
        try:
            out.append({"refusal": number, "check": wording, "verdict": "pass", "evidence": str(evidence_fn())})
        except Exception as exc:  # noqa: BLE001 - unevaluable is a recorded outcome
            out.append(
                {
                    "refusal": number,
                    "check": wording,
                    "verdict": "MANIFEST_REFUSAL_UNEVALUABLE",
                    "evidence": f"{type(exc).__name__}: {exc}",
                }
            )

    add(
        1,
        "Refuse any input whose manifest row is source_unavailable for the declared use",
        lambda: "sole input is manifest row 1 (US SPY Massive RAW closes) read via "
        "collectors.massive_stock_day.load_ticker('SPY'); its disposition 'recorded' for internal "
        "fitting/evaluation is pinned by the manifest blob identity verified in step 1 (a property "
        "of the pinned manifest, not of the frame bytes)",
    )
    add(
        2,
        "Refuse an origin before coverage.first_day or after latest_date; refuse non-session dates",
        lambda: f"window {dates[0]}..{dates[-1]} inside [2021-07-06, 2026-10-07]; every row date equals "
        "an NYSE session by check 1 (set equality with sessions_between)",
    )
    add(
        3,
        "Refuse an outcome series whose basis, market or units differ from the origin's row",
        lambda: "origin features and outcome labels (SS4) are computed from the SAME close column of "
        "this one RAW-basis frame; basis/market/units shared by construction",
    )
    add(
        4,
        "Refuse on price_basis_discontinuity (S08 guard) rather than re-adjusting",
        lambda: "assert_price_basis ran as check 3 and refused nothing; this run never re-adjusts closes",
    )
    add(
        5,
        "Record absent sessions; never fill; never treat a printed zero as absent",
        lambda: f"absent sessions: 0 (check 1 set equality); nothing filled; printed zeros recorded as "
        f"data: {int((volume == 0.0).sum())} zero-volume rows kept as values, not absence",
    )
    add(
        6,
        "Emit the manifest version it was evaluated against (1.0.0) in every result artifact",
        lambda: "every artifact this run writes carries manifest.version="
        f"{MANIFEST_VERSION} (completed-run and blocked-run templates alike)",
    )
    return out


def integrity_checks(window: pd.DataFrame) -> list[dict]:
    """Prereg SS3 checks 1-4 in order; first failure raises ``Blocked``."""
    dates = window["date"].tolist()
    checks: list[dict] = []

    strictly_increasing = all(a < b for a, b in zip(dates, dates[1:]))
    expected = {d.isoformat() for d in nyse_calendar.sessions_between(dt.date(2021, 7, 6), dt.date(2026, 10, 7))}
    got = set(dates)
    if not strictly_increasing or got != expected:
        missing = sorted(expected - got)
        extra = sorted(got - expected)
        raise Blocked(
            "ABSENT_SESSION",
            f"dates not strictly-increasing-unique-session-set: {len(missing)} missing "
            f"(first {missing[:3]}), {len(extra)} extra (first {extra[:3]})",
        )
    checks.append(
        {
            "check": "dates_strictly_increasing_unique_equal_to_nyse_sessions",
            "verdict": "pass",
            "detail": f"{len(dates)} rows == {len(expected)} sessions 2021-07-06..2026-10-07",
        }
    )

    close = window["close"].to_numpy(dtype=float)
    bad = ~np.isfinite(close) | (close <= 0)
    if bad.any():
        i = int(np.argmax(bad))
        raise Blocked("PRICE_INVALID", f"non-positive or non-finite close at {dates[i]}")
    checks.append({"check": "closes_positive_and_finite", "verdict": "pass", "detail": f"{len(close)} closes"})

    close_series = pd.Series(close, index=pd.Index(dates, name="date"))
    try:
        om.assert_price_basis(close_series)
    except om.PriceBasisDiscontinuity as exc:
        raise Blocked("PRICE_BASIS_DISCONTINUITY", str(exc)) from exc
    except om.ObservedMoveRefusal as exc:
        raise Blocked(getattr(exc, "code", "OBSERVED_MOVE_REFUSAL"), str(exc)) from exc
    checks.append(
        {
            "check": "price_basis_discontinuity_guard (SPLIT_LIKE_RATIO=0.75, refuses, never re-adjusts)",
            "verdict": "pass",
            "detail": "all day-over-day close ratios inside [0.75, 1/0.75]",
        }
    )

    checks.extend(_manifest_refusal_checks(window))
    return checks


# ── step 6: trial ledger scope ───────────────────────────────────────────────


def trial_ledger_scope():
    """The prereg SS6 trial-budget registration wrapping steps 7-18."""
    return trial_ledger.register_trials(family=TRIAL_FAMILY, budget=TRIAL_BUDGET, basis="itemized")


# ── steps 7-8: labels + features ─────────────────────────────────────────────


def build_labels(close: pd.Series) -> dict[int, dict]:
    """SS4: A(t,h) = forward_max_loss; Y = loss_event; immature stays NaN/NA."""
    out: dict[int, dict] = {}
    for h in HORIZONS:
        A = om.forward_max_loss(close, h)
        out[h] = {"A": A, "Y": om.loss_event(A, threshold=THRESHOLD)}
    return out


def build_features(close: pd.Series) -> pd.DataFrame:
    """SS6 features; any non-finite feature at idx >= 63 refuses the run."""
    rv20 = realized_vol(close, 20)
    rv63 = realized_vol(close, 63)
    feats = pd.DataFrame(
        {
            "rv20": rv20,
            "rv63": rv63,
            "log_rv20": np.log(rv20),
            "log_rv63": np.log(rv63),
            "sma_gap21": om.sma_gap(close, 21),
            "sma_gap63": om.sma_gap(close, 63),
            "dd63": om.trailing_drawdown(close, om.DRAWDOWN_WINDOW),
            "r5": om.log_return(close, 5),
            "r10": om.log_return(close, 10),
        }
    )
    arr = feats.to_numpy(dtype=float)
    for j, name in enumerate(feats.columns):
        rows = np.nonzero(~np.isfinite(arr[WARM_IDX:, j]))[0]
        if rows.size:
            i = WARM_IDX + int(rows[0])
            raise Blocked(
                "FEATURE_UNDEFINED_AFTER_WARMUP",
                f"feature {name} non-finite at row idx {i} (date {close.index[i]}); "
                "refusing, never imputing",
            )
    return feats


# ── step 9: populations + census ─────────────────────────────────────────────


def build_populations(n_rows: int) -> dict:
    """SS5: P-all executable now; P-active blocked until the observer is on main."""
    idx = np.arange(n_rows)
    warm = idx >= WARM_IDX
    p_all = {h: warm & (idx <= n_rows - 1 - h) for h in HORIZONS}
    return {
        "P-all": p_all,
        "P-active": {"blocked": "OBSERVER_NOT_ON_MAIN", "detail": "lib/pullback_observation.py close_path.v1 lives on draft PR #8188, not main"},
    }


def census_populations(n_rows: int, pre_entitlement_rows: int) -> list[dict]:
    """Eligibility/maturity census per (h, pop) with typed exclusions (SS12)."""
    idx = np.arange(n_rows)
    warm = idx >= WARM_IDX
    rows: list[dict] = []
    for h in HORIZONS:
        mature = idx <= n_rows - 1 - h
        base = {
            "horizon": h,
            "pre_entitlement": pre_entitlement_rows,
            "warmup": int((idx < WARM_IDX).sum()),
            "immature": int((warm & ~mature).sum()),
            "eligible": int((warm & mature).sum()),
        }
        rows.append({"population": "P-all", **base})
        rows.append(
            {
                "population": "P-active",
                **base,
                "blocked": "OBSERVER_NOT_ON_MAIN",
                "detail": "recorded, not run; TRAINING_FOLD_THIN is counted per block in folds/fits",
            }
        )
    return rows


# ── step 10: folds + purge ───────────────────────────────────────────────────


def build_fold_calendar(
    first_test_idx: int = FIRST_TEST_IDX,
    last_test_idx: int = 0,
    block_len: int = BLOCK_LEN,
    min_final_block: int = MIN_FINAL_BLOCK,
) -> list[tuple[int, int]]:
    """Blocks of ``block_len`` test origins; a final block shorter than
    ``min_final_block`` merges into its predecessor (inclusive [start, end])."""
    blocks: list[tuple[int, int]] = []
    s = int(first_test_idx)
    while s <= last_test_idx:
        e = min(s + block_len - 1, int(last_test_idx))
        blocks.append((s, e))
        s = e + 1
    if len(blocks) >= 2 and (blocks[-1][1] - blocks[-1][0] + 1) < min_final_block:
        _s, e_last = blocks.pop()
        ps, _pe = blocks[-1]
        blocks[-1] = (ps, e_last)
    return blocks


def fold_calendar_for_population(n_rows: int, h: int) -> list[tuple[int, int]]:
    """The test region ends at the last mature origin for ``h`` (prereg SS7)."""
    return build_fold_calendar(FIRST_TEST_IDX, n_rows - 1 - h)


def purged_training_indices(s0: int, h: int, candidate_idx: np.ndarray) -> np.ndarray:
    """SS7 purge: admit training origin t only when idx(t) + h <= idx(s0)."""
    cand = np.asarray(candidate_idx, dtype=int)
    return np.sort(cand[cand + h <= int(s0)])


def training_fold_is_thin(train_idx: np.ndarray, y_train: np.ndarray) -> tuple[bool, dict]:
    n = int(len(train_idx))
    k = float(np.sum(y_train))
    thin = n < MIN_TRAIN_ORIGINS or k < MIN_TRAIN_EVENTS
    return thin, {"origins": n, "events": k}


# ── step 11: fits ────────────────────────────────────────────────────────────


def logistic_objective_and_gradient(beta: np.ndarray, X: np.ndarray, y: np.ndarray, C: float) -> tuple[float, np.ndarray]:
    """SS6 objective sum(logaddexp(0,z) - y*z) + beta-beta'/(2C), intercept
    (column 0) unpenalised; gradient X'(sigma(z)-y) with beta/C on features."""
    z = X @ beta
    nll = float(np.sum(np.logaddexp(0.0, z) - y * z))
    pen = float(beta[1:] @ beta[1:]) / (2.0 * C)
    grad = X.T @ (expit(z) - y)
    grad = grad.astype(float, copy=True)
    grad[1:] += beta[1:] / C
    return nll + pen, grad


def fit_logistic(X: np.ndarray, y: np.ndarray, C: float) -> np.ndarray:
    res = minimize(
        logistic_objective_and_gradient,
        np.zeros(X.shape[1]),
        args=(X, y, C),
        method="L-BFGS-B",
        jac=True,
        options={"gtol": 1e-8, "maxiter": 10000},
    )
    if not res.success:
        raise _FitFailure("FIT_NONCONVERGENCE", str(res.message))
    return np.asarray(res.x, dtype=float)


def fit_quantile_lp(X: np.ndarray, a: np.ndarray, tau: float) -> tuple[float, np.ndarray]:
    """Per-tau linear quantile regression: variables [b, beta(p), u+, u-]."""
    n, n_feat = X.shape
    c = np.concatenate([np.zeros(1 + n_feat), np.full(n, tau), np.full(n, 1.0 - tau)])
    A_eq = np.zeros((n, 1 + n_feat + 2 * n))
    A_eq[:, 0] = 1.0
    A_eq[:, 1 : 1 + n_feat] = X
    A_eq[:, 1 + n_feat : 1 + n_feat + n] = np.eye(n)
    A_eq[:, 1 + n_feat + n : 1 + n_feat + 2 * n] = -np.eye(n)
    bounds = [(None, None)] * (1 + n_feat) + [(0, None)] * (2 * n)
    res = linprog(c, A_eq=A_eq, b_eq=np.asarray(a, dtype=float), bounds=bounds, method="highs")
    if res.status != 0:
        raise _FitFailure("FIT_NONCONVERGENCE", f"linprog status {res.status}: {res.message}")
    return float(res.x[0]), np.asarray(res.x[1 : 1 + n_feat], dtype=float)


def quantile_output_policy(q50: np.ndarray, q80: np.ndarray, q90: np.ndarray):
    """Crossing check on UNCLIPPED predictions, then clip below at 0 (SS6).

    Returns (issued mask, (clipped q50, q80, q90), per-origin reasons).
    """
    q50 = np.asarray(q50, dtype=float)
    q80 = np.asarray(q80, dtype=float)
    q90 = np.asarray(q90, dtype=float)
    crossing = (q50 > q80) | (q80 > q90)
    reasons = np.full(q50.shape, None, dtype=object)
    reasons[crossing] = "QUANTILE_CROSSING"
    clipped = (np.clip(q50, 0.0, None), np.clip(q80, 0.0, None), np.clip(q90, 0.0, None))
    return ~crossing, clipped, reasons


def fit_b0(y_train: np.ndarray) -> float:
    """(k + 0.5) / (n + 1) over the training prefix of that population."""
    k = float(np.sum(y_train))
    n = float(len(y_train))
    return (k + 0.5) / (n + 1.0)


def fit_q0(a_train: np.ndarray) -> dict[float, float]:
    return {tau: float(np.quantile(a_train, tau, method="linear")) for tau in TAUS}


def fit_q1(
    train_rv20: np.ndarray, a_train: np.ndarray, test_rv20: np.ndarray, block_q0: dict[float, float]
) -> tuple[dict[float, np.ndarray], dict]:
    """Q0 within training rv20 tercile cells (raw rv20, exactly as SS6 names it)."""
    bounds = np.quantile(train_rv20, [1 / 3, 2 / 3], method="linear")
    train_cell = np.searchsorted(bounds, train_rv20, side="right")
    per_cell: dict[int, dict[float, float]] = {}
    fallback_cells: list[dict] = []
    for cell in (0, 1, 2):
        members = train_cell == cell
        if int(members.sum()) < MIN_CELL:
            per_cell[cell] = dict(block_q0)  # the block's Q0 value; never abstains on cell size
            fallback_cells.append({"cell": cell, "n_train": int(members.sum())})
        else:
            per_cell[cell] = {tau: float(np.quantile(a_train[members], tau, method="linear")) for tau in TAUS}
    test_cell = np.searchsorted(bounds, np.asarray(test_rv20, dtype=float), side="right")
    preds = {
        tau: np.array([per_cell[int(c)][tau] for c in test_cell], dtype=float) for tau in TAUS
    }
    return preds, {"bounds": [float(b) for b in bounds], "fallback_cells": fallback_cells}


def _standardise(train_X: np.ndarray, test_X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = train_X.mean(axis=0)
    std = train_X.std(axis=0, ddof=0)
    return mean, std, (train_X - mean) / std, (test_X - mean) / std


def run_fits(
    close: pd.Series,
    labels: dict[int, dict],
    features: pd.DataFrame,
    deviations: list[dict] | None = None,
) -> dict:
    """One fit per configuration per test block; never refit inside a block."""
    n_rows = len(close)
    rv20_raw = features["rv20"].to_numpy(dtype=float)
    feat_matrix = {name: features[name].to_numpy(dtype=float) for name in FEATURE_COLUMNS}
    fits: dict[tuple[int, int, str], dict] = {}
    blocks_out: dict[tuple[int, int], dict] = {}
    q1_fallbacks: list[dict] = []

    for h in HORIZONS:
        A = labels[h]["A"].to_numpy(dtype=float)
        Y = labels[h]["Y"]
        y = Y.to_numpy(dtype=float, na_value=np.nan)
        blocks = fold_calendar_for_population(n_rows, h)
        idx_all = np.arange(n_rows)
        eligible = (idx_all >= WARM_IDX) & (idx_all <= n_rows - 1 - h)

        for block_i, (s0, e0) in enumerate(blocks, start=1):
            candidates = idx_all[(idx_all >= WARM_IDX) & (idx_all < s0) & (idx_all <= n_rows - 1 - h)]
            train_idx = purged_training_indices(s0, h, candidates)
            test_idx = np.arange(s0, e0 + 1)
            a_tr = A[train_idx]
            y_tr = y[train_idx]
            thin, train_stats = training_fold_is_thin(train_idx, y_tr)
            blocks_out[(h, block_i)] = {"range": [int(s0), int(e0)], **train_stats, "thin": bool(thin)}

            for cfg in CONFIGURATIONS:
                key = (h, block_i, cfg["id"])
                reasons = np.full(test_idx.shape, None, dtype=object)

                if thin and cfg["id"] != "B0":
                    reasons[:] = "TRAINING_FOLD_THIN"
                    fits[key] = {
                        "config": cfg["id"],
                        "kind": cfg["kind"],
                        "population": "P-all",
                        "block": [int(s0), int(e0)],
                        "train": train_stats,
                        "issued": np.zeros(test_idx.shape, dtype=bool),
                        "reasons": reasons,
                    }
                    continue

                try:
                    if cfg["id"] == "B0":
                        p0 = fit_b0(y_tr)
                        fits[key] = _block_result(cfg, (s0, e0), train_stats, p=np.full(test_idx.shape, p0))
                    elif cfg["kind"] == "binary":
                        cols = [feat_matrix[f] for f in cfg["features"]]
                        X_tr_raw = np.column_stack(cols)[train_idx]
                        X_te_raw = np.column_stack(cols)[test_idx]
                        _m, std, X_tr, X_te = _standardise(X_tr_raw, X_te_raw)
                        if (std == 0).any():
                            bad = [f for f, s in zip(cfg["features"], std) if s == 0]
                            _deviation(deviations, "FEATURE_DEGENERATE", f"{cfg['id']} h{h} block {block_i}: zero training std for {bad}; config abstains the block (no epsilon)")
                            reasons[:] = "FEATURE_DEGENERATE"
                            fits[key] = _block_result(cfg, (s0, e0), train_stats, issued=np.zeros(test_idx.shape, dtype=bool), reasons=reasons)
                            continue
                        design_tr = np.column_stack([np.ones(len(train_idx)), X_tr])
                        design_te = np.column_stack([np.ones(len(test_idx)), X_te])
                        beta = fit_logistic(design_tr, y_tr, cfg["params"]["C"])
                        p = expit(design_te @ beta)
                        fits[key] = _block_result(cfg, (s0, e0), train_stats, p=p)
                    elif cfg["id"] == "Q0":
                        q0 = fit_q0(a_tr)
                        fits[key] = _block_result(
                            cfg, (s0, e0), train_stats,
                            q={str(tau): np.full(test_idx.shape, q0[tau]) for tau in TAUS},
                        )
                    elif cfg["id"] == "Q1":
                        q0 = fit_q0(a_tr)
                        preds, fb = fit_q1(rv20_raw[train_idx], a_tr, rv20_raw[test_idx], q0)
                        if fb["fallback_cells"]:
                            q1_fallbacks.append({"h": h, "block": block_i, **fb})
                        fits[key] = _block_result(
                            cfg, (s0, e0), train_stats,
                            q={str(tau): preds[tau] for tau in TAUS},
                            logged={"TRAINING_CELL_THIN_FALLBACK": fb["fallback_cells"]},
                        )
                    elif cfg["id"] == "Q3-ALL":
                        cols = [feat_matrix[f] for f in cfg["features"]]
                        X_tr_raw = np.column_stack(cols)[train_idx]
                        X_te_raw = np.column_stack(cols)[test_idx]
                        _m, std, X_tr, X_te = _standardise(X_tr_raw, X_te_raw)
                        if (std == 0).any():
                            bad = [f for f, s in zip(cfg["features"], std) if s == 0]
                            _deviation(deviations, "FEATURE_DEGENERATE", f"{cfg['id']} h{h} block {block_i}: zero training std for {bad}; config abstains the block (no epsilon)")
                            reasons[:] = "FEATURE_DEGENERATE"
                            fits[key] = _block_result(cfg, (s0, e0), train_stats, issued=np.zeros(test_idx.shape, dtype=bool), reasons=reasons)
                            continue
                        q_unclipped = {}
                        for tau in TAUS:
                            b, beta = fit_quantile_lp(X_tr, a_tr, tau)
                            q_unclipped[tau] = X_te @ beta + b
                        issued, clipped, cross_reasons = quantile_output_policy(
                            q_unclipped[0.5], q_unclipped[0.8], q_unclipped[0.9]
                        )
                        q50c, q80c, q90c = clipped
                        fits[key] = _block_result(
                            cfg, (s0, e0), train_stats,
                            q={"0.5": q50c, "0.8": q80c, "0.9": q90c},
                            issued=issued,
                            reasons=cross_reasons,
                        )
                    else:  # pragma: no cover - configuration table is frozen
                        raise AssertionError(f"unhandled configuration {cfg['id']}")
                except _FitFailure as exc:
                    reasons[:] = exc.type
                    fits[key] = _block_result(cfg, (s0, e0), train_stats, issued=np.zeros(test_idx.shape, dtype=bool), reasons=reasons)

    config_rows = [
        {"horizon": h, "config": row["id"], "population": row["population"], "abstention_type": row["type"]}
        for h in HORIZONS
        for row in BLOCKED_CONFIG_ROWS
        if row["type"] is not None
    ]
    return {
        "fits": fits,
        "blocks": {f"h{h}/b{b}": v for (h, b), v in sorted(blocks_out.items())},
        "q1_fallbacks": q1_fallbacks,
        "populations_blocked": {"P-active": "OBSERVER_NOT_ON_MAIN"},
        "config_rows": config_rows,
    }


def _block_result(
    cfg: dict,
    block: tuple[int, int],
    train_stats: dict,
    p: np.ndarray | None = None,
    q: dict[str, np.ndarray] | None = None,
    issued: np.ndarray | None = None,
    reasons: np.ndarray | None = None,
    logged: dict | None = None,
) -> dict:
    out = {
        "config": cfg["id"],
        "kind": cfg["kind"],
        "population": "P-all",
        "block": [int(block[0]), int(block[1])],
        "train": train_stats,
    }
    if p is not None:
        out["p"] = np.asarray(p, dtype=float)
    if q is not None:
        out["q"] = {k: np.asarray(v, dtype=float) for k, v in q.items()}
    if issued is not None:
        out["issued"] = np.asarray(issued, dtype=bool)
    else:
        out["issued"] = np.ones((out["p"] if p is not None else next(iter(q.values()))).shape, dtype=bool)
    out["reasons"] = reasons if reasons is not None else np.full(out["issued"].shape, None, dtype=object)
    if logged:
        out["logged"] = logged
    return out


# ── steps 12-18 (part 2): comparison sets, metrics, episodes, bootstrap, ─────
# gates, negative control, INC, artifacts

BINARY_CLAIM_CONFIGS = ("B0", "B1-20", "B1-63", "B2-21", "B2-63", "M3-ALL")
QUANTILE_CLAIM_CONFIGS = ("Q0", "Q1", "Q3-ALL")
BASELINE_CONFIGS = ("B1-20", "B1-63", "B2-21", "B2-63")
SENSITIVITY_CONFIG = "M3-ALL-C0.1"
FAMILY_CONFIGS = {"binary": BINARY_CLAIM_CONFIGS, "quantile": QUANTILE_CLAIM_CONFIGS}
ALPHA_KEYS = ("0.5b", "b", "2b")
TAU_KEYS = tuple(str(tau) for tau in TAUS)

# The four SS12 verdict words, and nothing else, ever appear in a verdict field.
VERDICT_DESCRIPTIVE = "accepted descriptive measurement"
VERDICT_REJECTED = "rejected candidate"
VERDICT_BLOCKED = "underpowered/blocked claim"
VERDICT_QUALIFIED = "qualified research evidence (development, reconstructed)"


def alpha_grid(h: int) -> dict[str, float]:
    """Richardson ``alpha_h`` in {0.5 b_h, b_h, 2 b_h} (prereg SS9)."""
    b = BASE_RATES[h]
    return {"0.5b": 0.5 * b, "b": b, "2b": 2.0 * b}


# ── step 12: comparison sets (prereg SS7 "Comparison set") ───────────────────


def evaluation_origin_indices(n_rows: int, h: int) -> np.ndarray:
    """The union of the test blocks = the evaluation origins for ``h``."""
    return np.concatenate(
        [np.arange(s, e + 1) for s, e in fold_calendar_for_population(n_rows, h)]
    )


def gather_config_series(fits: dict, h: int, config_id: str, origin_idx: np.ndarray) -> dict:
    """One configuration's p / q / issued / reasons aligned to ``origin_idx``.

    ``fits`` is the ``run_fits`` result (the ``(h, block, config) -> record``
    mapping lives under its ``"fits"`` key).
    """
    fit_records = fits.get("fits", fits)
    n = len(origin_idx)
    pos = {int(o): i for i, o in enumerate(origin_idx)}
    issued = np.zeros(n, dtype=bool)
    reasons = np.full(n, "NO_FIT_ROW", dtype=object)
    p = np.full(n, np.nan)
    q = {k: np.full(n, np.nan) for k in TAU_KEYS}
    kind = None
    for (bh, _block_i, cid), rec in fit_records.items():
        if bh != h or cid != config_id:
            continue
        kind = rec["kind"]
        s0, e0 = rec["block"]
        for j, o in enumerate(range(s0, e0 + 1)):
            i = pos.get(o)
            if i is None:
                continue
            issued[i] = bool(rec["issued"][j])
            reasons[i] = rec["reasons"][j]
            if rec.get("p") is not None:
                p[i] = rec["p"][j]
            if rec.get("q") is not None:
                for k in TAU_KEYS:
                    q[k][i] = rec["q"][k][j]
    return {"config": config_id, "kind": kind, "issued": issued, "reasons": reasons, "p": p, "q": q}


def intersection_of_issued(masks: dict) -> np.ndarray:
    """The comparison set: origins where EVERY compared configuration issued."""
    it = iter(masks.values())
    common = np.asarray(next(it), dtype=bool).copy()
    for mask in it:
        common &= np.asarray(mask, dtype=bool)
    return common


def abstention_breakdown(issued: np.ndarray, reasons: np.ndarray) -> dict:
    abstained = ~np.asarray(issued, dtype=bool)
    by_type: dict[str, int] = {}
    for reason in np.asarray(reasons, dtype=object)[abstained]:
        if reason is not None:
            key = str(reason)
            by_type[key] = by_type.get(key, 0) + 1
    return {"issued": int((~abstained).sum()), "abstained": int(abstained.sum()), "by_type": by_type}


def comparison_set_report(origin_idx: np.ndarray, masks: dict, reasons: dict) -> dict:
    """``N_common`` plus every configuration's issued / abstained counts by type."""
    common = intersection_of_issued(masks)
    return {
        "n_configs": len(masks),
        "N_common": int(common.sum()),
        "common_origins": np.asarray(origin_idx)[common].tolist(),
        "configs": {
            cid: abstention_breakdown(masks[cid], reasons[cid]) for cid in masks
        },
    }


def build_comparison_sets(fits: dict, n_rows: int, labels: dict[int, dict]) -> dict:
    """Per (h, family): the intersection-of-issued comparison set + arrays."""
    comp_by_h: dict[int, dict] = {}
    all_configs = BINARY_CLAIM_CONFIGS + QUANTILE_CLAIM_CONFIGS + (SENSITIVITY_CONFIG,)
    for h in HORIZONS:
        origin_idx = evaluation_origin_indices(n_rows, h)
        y_full = labels[h]["Y"].to_numpy(dtype=float, na_value=np.nan)
        a_full = labels[h]["A"].to_numpy(dtype=float)
        y_eval = np.isfinite(y_full[origin_idx]) & (y_full[origin_idx] > 0)
        a_eval = a_full[origin_idx]
        series = {cid: gather_config_series(fits, h, cid, origin_idx) for cid in all_configs}
        fams: dict[str, dict] = {}
        for fam, cfgs in FAMILY_CONFIGS.items():
            masks = {cid: series[cid]["issued"] for cid in cfgs}
            reasons = {cid: series[cid]["reasons"] for cid in cfgs}
            common = intersection_of_issued(masks)
            cell = {
                "family": fam,
                "configs": cfgs,
                "h": h,
                "eval_origin_idx": origin_idx,
                "y_eval": y_eval,
                "a_eval": a_eval,
                "common_mask": common,
                "origin_idx": origin_idx[common],
                "y": y_eval[common],
                "a": a_eval[common],
                "report": comparison_set_report(origin_idx, masks, reasons),
                "p_eval": {},
                "q_eval": {},
                "p": {},
                "q": {},
            }
            if fam == "binary":
                for cid in cfgs:
                    cell["p_eval"][cid] = series[cid]["p"]
                    cell["p"][cid] = series[cid]["p"][common]
            else:
                for cid in cfgs:
                    cell["q_eval"][cid] = {k: series[cid]["q"][k] for k in TAU_KEYS}
                    cell["q"][cid] = {k: series[cid]["q"][k][common] for k in TAU_KEYS}
            sens = series[SENSITIVITY_CONFIG]
            cell["sensitivity"] = {
                "config": SENSITIVITY_CONFIG,
                "mask": common & sens["issued"],
                "p": sens["p"],
            }
            fams[fam] = cell
        comp_by_h[h] = fams
    return comp_by_h


# ── step 13: metrics (prereg SS9) ─────────────────────────────────────────────


def brier_score(p: np.ndarray, y: np.ndarray) -> float | None:
    if len(p) == 0:
        return None
    return float(np.mean((np.asarray(p, dtype=float) - np.asarray(y, dtype=float)) ** 2))


def brier_skill_score(p: np.ndarray, y: np.ndarray, p0: np.ndarray) -> float | None:
    """``BSS = 1 - Brier / Brier(B0)`` on the same origins."""
    b = brier_score(p, y)
    b0 = brier_score(p0, y)
    if b is None or b0 is None or b0 == 0.0:
        return None
    return 1.0 - b / b0


def calibration_in_the_large(p: np.ndarray, y: np.ndarray) -> float | None:
    """``CITL = mean(p) - mean(y)``."""
    if len(p) == 0:
        return None
    return float(np.mean(np.asarray(p, dtype=float)) - np.mean(np.asarray(y, dtype=float)))


def _wace_bin_ids(p: np.ndarray) -> np.ndarray:
    """Left-closed bins over ``WACE_BINS`` (last bin closed)."""
    interior = np.asarray(WACE_BINS[1:-1], dtype=float)
    return np.searchsorted(interior, np.asarray(p, dtype=float), side="right")


def wace_and_rwsce(p: np.ndarray, y: np.ndarray) -> dict:
    """WACE / RWSCE over bins with ``n_b >= 100``, weighted ``n_b / N_cov``."""
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=bool)
    n_bins = len(WACE_BINS) - 1
    out = {"wace": None, "rwsce": None, "n": int(len(p)), "n_cov": 0, "coverage_share": 0.0, "bins": []}
    if len(p) == 0:
        return out
    bids = _wace_bin_ids(p)
    n_b = np.bincount(bids, minlength=n_bins).astype(float)
    s_p = np.bincount(bids, weights=p, minlength=n_bins)
    s_y = np.bincount(bids, weights=y.astype(float), minlength=n_bins)
    bins_out = []
    for b in range(n_bins):
        bins_out.append(
            {
                "bin": [WACE_BINS[b], WACE_BINS[b + 1]],
                "n": int(n_b[b]),
                "p_bar": float(s_p[b] / n_b[b]) if n_b[b] else None,
                "o_bar": float(s_y[b] / n_b[b]) if n_b[b] else None,
                "covered": bool(n_b[b] >= WACE_MIN_BIN),
            }
        )
    out["bins"] = bins_out
    covered = n_b >= WACE_MIN_BIN
    n_cov = float(n_b[covered].sum())
    out["n_cov"] = int(n_cov)
    out["coverage_share"] = n_cov / len(p)
    if n_cov == 0:
        return out
    weights = n_b[covered] / n_cov
    p_bar = s_p[covered] / n_b[covered]
    o_bar = s_y[covered] / n_b[covered]
    out["wace"] = float(np.sum(weights * np.abs(p_bar - o_bar)))
    out["rwsce"] = float(np.sqrt(np.sum(weights * (p_bar - o_bar) ** 2)))
    return out


def auc_mann_whitney(p: np.ndarray, y: np.ndarray) -> float | None:
    """AUC with ties counted one half; None without both classes."""
    y = np.asarray(y, dtype=bool)
    p = np.asarray(p, dtype=float)
    n1 = int(y.sum())
    n0 = int(len(y) - n1)
    if n1 == 0 or n0 == 0:
        return None
    ranks = rankdata(p)
    return (float(ranks[y].sum()) - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def richardson_v(p: np.ndarray, y: np.ndarray, alpha: float) -> float | None:
    """Richardson value at cost-loss ratio ``alpha`` (prereg SS9); None = undefined."""
    y = np.asarray(y, dtype=bool)
    p = np.asarray(p, dtype=float)
    n = int(len(y))
    if n == 0:
        return None
    s = float(y.mean())
    if s in (0.0, 1.0) or not 0.0 < alpha < 1.0:
        return None
    n1 = int(y.sum())
    n0 = n - n1
    if n1 == 0 or n0 == 0:
        return None
    e_clim = min(alpha, s)
    denom = e_clim - s * alpha
    if denom == 0.0:
        return None
    alarm = p >= alpha
    hit_rate = float((alarm & y).sum()) / n1
    false_rate = float((alarm & ~y).sum()) / n0
    e_fcst = alpha * (hit_rate * s + false_rate * (1.0 - s)) + (1.0 - hit_rate) * s
    return (e_clim - e_fcst) / denom


def binary_metric_set(p, y, p0=None, alphas: dict | None = None) -> dict:
    """The SS9 binary metrics on one origin set (BSS only against a reference)."""
    y = np.asarray(y, dtype=bool)
    p = np.asarray(p, dtype=float)
    n = int(len(p))
    out: dict = {
        "n": n,
        "events": int(y.sum()) if n else 0,
        "base_rate": float(y.mean()) if n else None,
        "brier": brier_score(p, y),
        "citl": calibration_in_the_large(p, y),
        "auc": auc_mann_whitney(p, y),
    }
    wace = wace_and_rwsce(p, y)
    out["wace"] = wace["wace"]
    out["rwsce"] = wace["rwsce"]
    out["wace_coverage_share"] = wace["coverage_share"]
    out["wace_n_cov"] = wace["n_cov"]
    if p0 is not None:
        out["bss"] = brier_skill_score(p, y, p0)
    for label, alpha in (alphas or {}).items():
        out[f"v_{label}"] = richardson_v(p, y, alpha)
    return out


def pinball_loss(a: np.ndarray, q: np.ndarray, tau: float) -> float | None:
    if len(a) == 0:
        return None
    d = np.asarray(a, dtype=float) - np.asarray(q, dtype=float)
    return float(np.mean(np.maximum(tau * d, (tau - 1.0) * d)))


def quantile_metric_set(a, qd: dict) -> dict:
    """The SS9 quantile metrics (pinball per tau and summed, coverage, width, tail)."""
    a = np.asarray(a, dtype=float)
    out: dict = {"n": int(len(a))}
    pl_total = 0.0
    for k in TAU_KEYS:
        loss = pinball_loss(a, qd[k], float(k))
        out[f"pinball_{k}"] = loss
        pl_total += loss or 0.0
        out[f"coverage_{k}"] = float(np.mean(a <= np.asarray(qd[k], dtype=float))) if len(a) else None
    out["pinball_sum"] = pl_total if len(a) else None
    q50 = np.asarray(qd["0.5"], dtype=float)
    q90 = np.asarray(qd["0.9"], dtype=float)
    if len(a):
        out["width_q90_q50"] = float(np.mean(q90 - q50))
        exceed = a > q90
        out["tail_exceedance_rate"] = float(exceed.mean())
        out["tail_mean_excess"] = float(np.mean(a[exceed] - q90[exceed])) if exceed.any() else None
        out["crossing_count"] = int(((q50 > np.asarray(qd["0.8"], dtype=float)) | (np.asarray(qd["0.8"], dtype=float) > q90)).sum())
    else:
        out["width_q90_q50"] = None
        out["tail_exceedance_rate"] = None
        out["tail_mean_excess"] = None
        out["crossing_count"] = 0
    return out


def compute_point_metrics(comp_by_h: dict, n_rows: int, rv20_raw: np.ndarray, dates: list[str]) -> dict:
    """Step 13: attach point metrics + SS9 slices to every comparison cell."""
    report: dict[int, dict] = {}
    for h in HORIZONS:
        alphas = alpha_grid(h)
        blocks = fold_calendar_for_population(n_rows, h)
        idx_all = np.arange(n_rows)
        block_of: dict[int, int] = {}
        tercile_bounds: dict[int, np.ndarray] = {}
        for bi, (s0, e0) in enumerate(blocks, start=1):
            candidates = idx_all[(idx_all >= WARM_IDX) & (idx_all < s0) & (idx_all <= n_rows - 1 - h)]
            train_idx = purged_training_indices(s0, h, candidates)
            bounds = (
                np.quantile(rv20_raw[train_idx], [1 / 3, 2 / 3], method="linear")
                if len(train_idx)
                else np.array([np.inf, np.inf])
            )
            for o in range(s0, e0 + 1):
                block_of[o] = bi
                tercile_bounds[o] = bounds
        fam_report: dict[str, dict] = {}
        for fam, cell in comp_by_h[h].items():
            origin_idx = cell["origin_idx"]
            y, a = cell["y"], cell["a"]
            keys = {
                "calendar_year": [dates[o][:4] for o in origin_idx],
                "test_block": [str(block_of.get(int(o), 0)) for o in origin_idx],
                "training_rv20_tercile": [
                    str(int(np.searchsorted(tercile_bounds[int(o)], rv20_raw[int(o)], side="right")))
                    for o in origin_idx
                ],
            }
            metrics: dict[str, dict] = {}
            slices: dict[str, dict] = {}
            if fam == "binary":
                p0 = cell["p"]["B0"]
                for cid in cell["configs"]:
                    metrics[cid] = binary_metric_set(cell["p"][cid], y, p0=p0, alphas=alphas)
                    slices[cid] = {
                        name: {
                            key: binary_metric_set(
                                cell["p"][cid][np.asarray(members, dtype=int)],
                                y[np.asarray(members, dtype=int)],
                                p0=p0[np.asarray(members, dtype=int)],
                                alphas=alphas,
                            )
                            for key, members in group.items()
                        }
                        for name, group in _slice_groups(keys).items()
                    }
            else:
                for cid in cell["configs"]:
                    metrics[cid] = quantile_metric_set(a, cell["q"][cid])
                    slices[cid] = {
                        name: {
                            key: quantile_metric_set(
                                a[np.asarray(members, dtype=int)],
                                {k: cell["q"][cid][k][np.asarray(members, dtype=int)] for k in TAU_KEYS},
                            )
                            for key, members in group.items()
                        }
                        for name, group in _slice_groups(keys).items()
                    }
            if fam == "binary":
                sens_mask = cell["sensitivity"]["mask"]
                sens = {
                    "config": SENSITIVITY_CONFIG,
                    "n": int(sens_mask.sum()),
                    "metrics": binary_metric_set(
                        cell["sensitivity"]["p"][sens_mask], y[sens_mask], p0=cell["p"]["B0"][sens_mask], alphas=alphas
                    )
                    if sens_mask.any()
                    else None,
                    "note": "sensitivity row only, never a gate (prereg SS6)",
                }
            else:
                sens = {"note": "the M3-ALL C=0.1 sensitivity row is binary-only (prereg SS6)"}
            cell["metrics"] = metrics
            cell["slices"] = slices
            fam_report[fam] = {"metrics": metrics, "slices": slices, "sensitivity": sens}
        report[h] = fam_report
    return report


def _slice_groups(keys: dict[str, list[str]]) -> dict[str, dict[str, list[int]]]:
    grouped: dict[str, dict[str, list[int]]] = {}
    for name, key_list in keys.items():
        groups: dict[str, list[int]] = {}
        for i, key in enumerate(key_list):
            groups.setdefault(key, []).append(i)
        grouped[name] = dict(sorted(groups.items()))
    return grouped


# ── step 14: episodes, honest-N, power floor (prereg SS8) ────────────────────


def event_clusters(event_idx: np.ndarray, h: int) -> list[np.ndarray]:
    """Event-positive origins merged when the session-index gap <= h."""
    events = np.sort(np.asarray(event_idx, dtype=int))
    clusters: list[np.ndarray] = []
    current: list[int] = []
    for e in events:
        if current and int(e) - current[-1] > h:
            clusters.append(np.asarray(current, dtype=int))
            current = []
        current.append(int(e))
    if current:
        clusters.append(np.asarray(current, dtype=int))
    return clusters


def cluster_window(cluster: np.ndarray, h: int) -> list[int]:
    """[first - 21, last + h] in session indices."""
    return [int(cluster[0]) - EPISODE_PRE, int(cluster[-1]) + h]


def merge_episodes(clusters: list[np.ndarray], h: int) -> list[dict]:
    """Episodes: unions of clusters whose episode windows overlap."""
    episodes: list[dict] = []
    for cluster in sorted(clusters, key=lambda c: int(c[0])):
        lo, hi = cluster_window(cluster, h)
        if episodes and lo <= episodes[-1]["window"][1]:
            episodes[-1]["window"][1] = max(episodes[-1]["window"][1], hi)
            episodes[-1]["clusters"].append(cluster)
        else:
            episodes.append({"window": [lo, hi], "clusters": [cluster]})
    return episodes


def honest_n(origin_idx: np.ndarray, y: np.ndarray, dates: list[str], h: int) -> dict:
    """Origins, events, clusters, episodes and distinct event months (SS8)."""
    events = np.asarray(origin_idx, dtype=int)[np.asarray(y, dtype=bool)]
    clusters = event_clusters(events, h)
    episodes = merge_episodes(clusters, h)
    months = sorted({dates[int(i)][:7] for i in events})
    met = len(episodes) >= POWER_MIN_EPISODES and len(months) >= POWER_MIN_MONTHS
    return {
        "origins": int(len(origin_idx)),
        "events": int(len(events)),
        "clusters": int(len(clusters)),
        "episodes": int(len(episodes)),
        "event_months": int(len(months)),
        "event_month_list": months,
        "power_floor": {
            "min_episodes": POWER_MIN_EPISODES,
            "min_months": POWER_MIN_MONTHS,
            "met": bool(met),
        },
    }


def compute_episodes(comp_by_h: dict, dates: list[str]) -> dict:
    """Step 14: attach clusters / episodes / honest-N to every comparison cell."""
    report: dict[int, dict] = {}
    for h in HORIZONS:
        fam_report: dict[str, dict] = {}
        for fam, cell in comp_by_h[h].items():
            events = cell["origin_idx"][cell["y"]]
            clusters = event_clusters(events, h)
            episodes = merge_episodes(clusters, h)
            cell["clusters"] = clusters
            cell["episodes"] = episodes
            cell["honest_n"] = honest_n(cell["origin_idx"], cell["y"], dates, h)
            fam_report[fam] = {
                "honest_n": cell["honest_n"],
                "episode_windows": [list(ep["window"]) for ep in episodes],
                "cluster_sizes": [int(len(c)) for c in clusters],
            }
        report[h] = fam_report
    return report


# ── step 15: bootstrap (prereg SS10) and gates (prereg SS11) ─────────────────


def block_length(h: int, variant: int) -> int:
    """``L = max(21, 2h)``; the ``variant = 1`` sensitivity rerun uses ``L = h``."""
    return int(h) if variant == 1 else max(21, 2 * int(h))


def bootstrap_index_matrix(
    n: int,
    h: int,
    pop: int,
    fam: int,
    variant: int,
    n_draws: int = N_DRAWS,
    seed_root: int = SEED_ROOT,
) -> np.ndarray:
    """One index matrix per (h, pop, family, variant) cell (prereg SS10).

    Per draw: ``starts = rng.integers(0, N, size=ceil(N / L))``; each block is
    ``(start + arange(L)) % N``; concatenate and keep the first ``N``.
    """
    n = int(n)
    L = block_length(h, variant)
    n_blocks = math.ceil(n / L)
    rng = np.random.default_rng(
        np.random.SeedSequence([int(seed_root), int(h), int(pop), int(fam), int(variant)])
    )
    offsets = np.arange(L)
    rows = np.empty((int(n_draws), n), dtype=np.int64)
    for d in range(int(n_draws)):
        starts = rng.integers(0, n, size=n_blocks)
        rows[d] = ((starts[:, None] + offsets[None, :]) % n).reshape(-1)[:n]
    return rows


def binary_draw_statistics(idx_matrix: np.ndarray, y: np.ndarray, p_configs: dict, alphas: dict) -> dict:
    """Paired binary draws: one index row drives every configuration (SS10).

    An undefined statistic on a draw takes its failing extreme: ``-inf`` where
    the gate needs it large (V, ΔV, BSS) and ``+inf`` where small (WACE).
    """
    y = np.asarray(y, dtype=bool)
    n = int(len(y))
    n_draws = int(len(idx_matrix))
    cfgs = list(p_configs)
    baselines = [c for c in BASELINE_CONFIGS if c in p_configs]
    out: dict = {
        "brier": {c: np.empty(n_draws) for c in cfgs},
        "bss": {c: np.empty(n_draws) for c in cfgs},
        "v": {c: {label: np.empty(n_draws) for label in alphas} for c in cfgs},
        "delta_v": np.empty(n_draws),
        "citl": np.empty(n_draws),
        "wace": np.empty(n_draws),
    }
    n_bins = len(WACE_BINS) - 1
    bin_ids = _wace_bin_ids(p_configs["M3-ALL"])
    y_float = y.astype(float)
    for d in range(n_draws):
        row = idx_matrix[d]
        yd = y[row]
        n1 = int(yd.sum())
        s = n1 / n if n else 0.0
        undefined_v = n == 0 or n1 == 0 or n1 == n
        briers = {}
        for c in cfgs:
            pd_ = p_configs[c][row]
            briers[c] = float(np.mean((pd_ - yd) ** 2)) if n else float("nan")
            out["brier"][c][d] = briers[c]
        b0 = briers.get("B0", float("nan"))
        for c in cfgs:
            out["bss"][c][d] = (1.0 - briers[c] / b0) if b0 and b0 > 0 else -np.inf
        for c in cfgs:
            pd_ = p_configs[c][row]
            for label, alpha in alphas.items():
                if undefined_v:
                    out["v"][c][label][d] = -np.inf
                else:
                    alarm = pd_ >= alpha
                    hit = float((alarm & yd).sum()) / n1
                    false = float((alarm & ~yd).sum()) / (n - n1)
                    e_clim = min(alpha, s)
                    e_fcst = alpha * (hit * s + false * (1.0 - s)) + (1.0 - hit) * s
                    out["v"][c][label][d] = (e_clim - e_fcst) / (e_clim - s * alpha)
        if undefined_v or not baselines:
            out["delta_v"][d] = -np.inf
        else:
            best = max(out["v"][c]["b"][d] for c in baselines)
            out["delta_v"][d] = out["v"]["M3-ALL"]["b"][d] - best
        pd_m3 = p_configs["M3-ALL"][row]
        out["citl"][d] = float(pd_m3.mean() - y_float[row].mean()) if n else float("nan")
        n_b = np.bincount(bin_ids[row], minlength=n_bins).astype(float)
        if n == 0:
            out["wace"][d] = np.inf
        else:
            covered = n_b >= WACE_MIN_BIN
            n_cov = float(n_b[covered].sum())
            if n_cov == 0:
                out["wace"][d] = np.inf
            else:
                s_p = np.bincount(bin_ids[row], weights=pd_m3, minlength=n_bins)
                s_y = np.bincount(bin_ids[row], weights=yd.astype(float), minlength=n_bins)
                weights = n_b[covered] / n_cov
                out["wace"][d] = float(
                    np.sum(weights * np.abs(s_p[covered] / n_b[covered] - s_y[covered] / n_b[covered]))
                )
    return out


def quantile_draw_statistics(idx_matrix: np.ndarray, a: np.ndarray, q_configs: dict) -> dict:
    """Paired quantile draws (SS10): pinball sums, skill, coverage per tau.

    The better-reference minimum in the skill is recomputed inside each draw;
    an undefined skill (zero reference loss) takes ``-inf``.
    """
    a = np.asarray(a, dtype=float)
    n = int(len(a))
    n_draws = int(len(idx_matrix))
    cfgs = list(q_configs)
    out: dict = {
        "pl_sum": {c: np.empty(n_draws) for c in cfgs},
        "skill": np.empty(n_draws),
        "skill_q1_vs_q0": np.empty(n_draws),
        "coverage": {k: np.empty(n_draws) for k in TAU_KEYS},
    }
    for d in range(n_draws):
        row = idx_matrix[d]
        ad = a[row]
        pl = {}
        for c in cfgs:
            total = 0.0
            for k in TAU_KEYS:
                q = q_configs[c][k][row]
                diff = ad - q
                total += float(np.mean(np.maximum(float(k) * diff, (float(k) - 1.0) * diff))) if n else float("nan")
            pl[c] = total
            out["pl_sum"][c][d] = total
        reference = min(pl["Q0"], pl["Q1"])
        out["skill"][d] = (1.0 - pl["Q3-ALL"] / reference) if reference > 0 else -np.inf
        out["skill_q1_vs_q0"][d] = (1.0 - pl["Q1"] / pl["Q0"]) if pl["Q0"] > 0 else -np.inf
        for k in TAU_KEYS:
            out["coverage"][k][d] = float(np.mean(ad <= q_configs["Q3-ALL"][k][row])) if n else float("nan")
    return out


def _quantile_all_draws(values, q: float) -> float:
    """``np.quantile`` over ALL draws (never ``nanquantile``).

    numpy's linear interpolation between two EQUAL infinities returns NaN
    (inf - inf); the mathematical quantile at such a position is that infinity,
    so the NaN artifact is repaired, never dropped: the failing extremes stay
    in the bound (prereg SS10 "Bounds are numpy.quantile over all 10,000
    draws; nanquantile is never used").
    """
    values = np.asarray(values, dtype=float)
    with np.errstate(invalid="ignore"):
        result = float(np.quantile(values, q, method="linear"))
    if not math.isnan(result):
        return result
    position = q * (len(values) - 1)
    n_inf_neg = int(np.isneginf(values).sum())
    n_inf_pos = int(np.isposinf(values).sum())
    if position < n_inf_neg:
        return float("-inf")
    if position >= len(values) - n_inf_pos:
        return float("inf")
    return result


def gate_lower_bound(draws) -> float:
    """The one-sided 0.05/12 lower bound (numpy quantile, never nanquantile)."""
    return _quantile_all_draws(draws, GATE_Q)


def interval_90(draws) -> list[float]:
    return [_quantile_all_draws(draws, 0.05), _quantile_all_draws(draws, 0.95)]


def run_bootstrap_cells(comp_by_h: dict) -> dict:
    """One matrix per (h, P-all, family, variant) cell, reused for every statistic."""
    report: dict[int, dict] = {}
    pop_code = SEED_CODES["pop"]["P-all"]
    for h in HORIZONS:
        fam_code_of = {"binary": SEED_CODES["fam"]["binary"], "quantile": SEED_CODES["fam"]["quantile"]}
        fam_report: dict[str, dict] = {}
        for fam, cell in comp_by_h[h].items():
            fam_code = fam_code_of[fam]
            cell["draws"] = {}
            fam_report[fam] = {}
            for variant, name in ((0, "primary"), (1, "sensitivity_L_h")):
                matrix = bootstrap_index_matrix(len(cell["origin_idx"]), h, pop_code, fam_code, variant)
                if fam == "binary":
                    stats = binary_draw_statistics(matrix, cell["y"], cell["p"], alpha_grid(h))
                else:
                    stats = quantile_draw_statistics(matrix, cell["a"], cell["q"])
                cell["draws"][name] = stats
                fam_report[fam][name] = {
                    "L": block_length(h, variant),
                    "n_draws": int(matrix.shape[0]),
                    "N": int(matrix.shape[1]),
                    "seed": [SEED_ROOT, h, pop_code, fam_code, variant],
                    "headline": _headline_bounds(stats, fam),
                }
        report[h] = fam_report
    return report


def _headline_bounds(stats: dict, fam: str) -> dict:
    """Gate bounds / 90% intervals for the headline statistics of a cell."""
    if fam == "binary":
        return {
            "v_m3": {label: {"lb": gate_lower_bound(v), "interval_90": interval_90(v)} for label, v in stats["v"]["M3-ALL"].items()},
            "delta_v": {"lb": gate_lower_bound(stats["delta_v"]), "interval_90": interval_90(stats["delta_v"])},
            "bss_m3": {"lb": gate_lower_bound(stats["bss"]["M3-ALL"]), "interval_90": interval_90(stats["bss"]["M3-ALL"])},
            "citl_m3": {"interval_90": interval_90(stats["citl"])},
            "wace_m3": {"interval_90": interval_90(stats["wace"])},
        }
    return {
        "skill": {"lb": gate_lower_bound(stats["skill"]), "interval_90": interval_90(stats["skill"])},
        "skill_q1_vs_q0": {"interval_90": interval_90(stats["skill_q1_vs_q0"])},
        "coverage": {k: {"interval_90": interval_90(v)} for k, v in stats["coverage"].items()},
    }


# ── step 15b: leave-one-episode-out (prereg SS11 conditions 6 / 4) ───────────


def loeo_checks(cell: dict, fam: str, h: int) -> dict:
    """Drop each episode window from the evaluation set; point estimates only.

    No draws and no refit; an undefined point estimate fails as FRAGILE.
    """
    origin_idx = cell["origin_idx"]
    y, a = cell["y"], cell["a"]
    alphas = alpha_grid(h)
    per_episode: list[dict] = []
    mins: dict[str, float] = {}
    undefined = 0
    for episode in cell["episodes"]:
        lo, hi = episode["window"]
        keep = ~((origin_idx >= lo) & (origin_idx <= hi))
        row: dict = {"window": [int(lo), int(hi)], "n_kept": int(keep.sum())}
        if fam == "binary":
            p0, pm3 = cell["p"]["B0"], cell["p"]["M3-ALL"]
            v_m3 = richardson_v(pm3[keep], y[keep], alphas["b"])
            base = [richardson_v(cell["p"][c][keep], y[keep], alphas["b"]) for c in BASELINE_CONFIGS]
            delta_v = None if v_m3 is None or any(v is None for v in base) else v_m3 - max(base)
            bss = brier_skill_score(pm3[keep], y[keep], p0[keep])
            row["stats"] = {"v_m3@b": v_m3, "delta_v": delta_v, "bss": bss}
            positive = all(v is not None and v > 0 for v in row["stats"].values())
            for key, value in row["stats"].items():
                if value is None:
                    undefined += 1
                elif key not in mins or value < mins[key]:
                    mins[key] = float(value)
        else:
            pl_q3 = pinball_loss_sum(a, cell["q"]["Q3-ALL"], keep)
            pl_q0 = pinball_loss_sum(a, cell["q"]["Q0"], keep)
            pl_q1 = pinball_loss_sum(a, cell["q"]["Q1"], keep)
            skill = None if pl_q0 == 0 or pl_q1 == 0 or pl_q3 is None else 1.0 - pl_q3 / min(pl_q0, pl_q1)
            row["stats"] = {"pinball_skill": skill}
            positive = skill is not None and skill > 0
            if skill is None:
                undefined += 1
            elif "pinball_skill" not in mins or skill < mins["pinball_skill"]:
                mins["pinball_skill"] = float(skill)
        row["positive"] = bool(positive)
        per_episode.append(row)
    n_episodes = len(per_episode)
    fragile = bool(per_episode) and any(not row["positive"] for row in per_episode)
    return {
        "n_episodes": int(n_episodes),
        "per_episode": per_episode,
        "min": mins,
        "undefined_point_estimates": int(undefined),
        "fragile": fragile,
        "note": "point estimates only, no draws, no refit; deletion on the evaluation set"
        + ("; zero episodes -> vacuous" if n_episodes == 0 else ""),
    }


def pinball_loss_sum(a: np.ndarray, qd: dict, mask: np.ndarray) -> float | None:
    total = 0.0
    for k in TAU_KEYS:
        loss = pinball_loss(np.asarray(a)[mask], qd[k][mask], float(k))
        if loss is None:
            return None
        total += loss
    return total


# ── step 15c: the 12 gated claims (prereg SS11) ──────────────────────────────


def _binary_claim_row(h: int, cell: dict, abst_m3: dict) -> dict:
    alphas = alpha_grid(h)
    b_h = BASE_RATES[h]
    draws = cell["draws"]["primary"]
    metrics = cell["metrics"]["M3-ALL"]
    loeo = loeo_checks(cell, "binary", h)
    conditions: list[dict] = []

    for label in ALPHA_KEYS:
        lb = gate_lower_bound(draws["v"]["M3-ALL"][label])
        point = metrics[f"v_{label}"]
        conditions.append(
            {
                "condition": 1,
                "statistic": f"v_m3@alpha={label}",
                "point": point,
                "lb": lb,
                "threshold": 0.0,
                "pass": point is not None and lb > 0.0,
            }
        )
    lb = gate_lower_bound(draws["delta_v"])
    conditions.append(
        {
            "condition": 2,
            "statistic": "delta_v@alpha=b (V(M3) - max(V(B1-20,B1-63,B2-21,B2-63)))",
            "point": _point_delta_v(cell, alphas),
            "lb": lb,
            "threshold": 0.0,
            "pass": lb > 0.0,
        }
    )
    lb = gate_lower_bound(draws["bss"]["M3-ALL"])
    conditions.append(
        {
            "condition": 3,
            "statistic": "bss_m3_vs_b0",
            "point": metrics["bss"],
            "lb": lb,
            "threshold": 0.0,
            "pass": metrics["bss"] is not None and lb > 0.0,
        }
    )
    citl_iv = interval_90(draws["citl"])
    wace_q05 = _quantile_all_draws(draws["wace"], 0.05)
    coverage_share = metrics["wace_coverage_share"]
    undercovered = coverage_share is None or coverage_share < 0.5
    citl_ok = citl_iv[0] <= 0.0 <= citl_iv[1]
    wace_ok = wace_q05 <= 0.5 * b_h
    conditions.append(
        {
            "condition": 4,
            "statistic": "calibration (CITL 90% interval contains 0; WACE 0.05-quantile <= 0.5 b_h)",
            "point": {"citl": metrics["citl"], "wace": metrics["wace"], "wace_q05_draws": wace_q05, "citl_interval_90": citl_iv},
            "lb": None,
            "threshold": {"wace_q05": 0.5 * b_h},
            "pass": bool(citl_ok and wace_ok and not undercovered),
            "flag": "CALIBRATION_UNDERCOVERED" if undercovered else None,
        }
    )
    conditions.append(
        {
            "condition": 5,
            "statistic": "abstention (rate <= 5% of evaluation origins; event-vs-non-event gap <= 5pp)",
            "point": {"rate": abst_m3["rate"], "gap_pp": abst_m3["gap_pp"], **abst_m3["counts"]},
            "lb": None,
            "threshold": {"rate": 0.05, "gap_pp": 5.0},
            "pass": bool(abst_m3["rate"] <= 0.05 and abst_m3["gap_pp"] <= 5.0),
            "flag": None if abst_m3["rate"] <= 0.05 and abst_m3["gap_pp"] <= 5.0 else "ABSTENTION_CONCENTRATED",
        }
    )
    conditions.append(
        {
            "condition": 6,
            "statistic": "leave-one-episode-out keeps V@b, ΔV and BSS point estimates above 0",
            "point": {"min": loeo["min"], "undefined": loeo["undefined_point_estimates"]},
            "lb": None,
            "threshold": 0.0,
            "pass": not loeo["fragile"],
            "flag": "FRAGILE" if loeo["fragile"] else None,
        }
    )
    power = cell["honest_n"]["power_floor"]
    conditions.append(
        {
            "condition": 7,
            "statistic": f"power floor (>= {POWER_MIN_EPISODES} episodes and >= {POWER_MIN_MONTHS} event months)",
            "point": {
                "episodes": cell["honest_n"]["episodes"],
                "event_months": cell["honest_n"]["event_months"],
            },
            "lb": None,
            "threshold": {"episodes": POWER_MIN_EPISODES, "event_months": POWER_MIN_MONTHS},
            "pass": bool(power["met"]),
            "flag": None if power["met"] else "UNDERPOWERED_DISCLOSED",
        }
    )
    flags = [c["flag"] for c in conditions if c.get("flag")]
    if not power["met"]:
        verdict = VERDICT_BLOCKED
    elif all(c["pass"] for c in conditions):
        verdict = VERDICT_QUALIFIED
    else:
        verdict = VERDICT_REJECTED
    headline = conditions[1]
    return {
        "id": f"h{h}/P-all/binary",
        "h": h,
        "pop": "P-all",
        "claim": "binary",
        "statistic": "delta_v@alpha=b_h",
        "point": headline["point"],
        "lb": headline["lb"],
        "threshold": 0.0,
        "flags": flags,
        "verdict": verdict,
        "conditions": conditions,
        "honest_n": cell["honest_n"],
        "loeo": {"fragile": loeo["fragile"], "min": loeo["min"], "n_episodes": loeo["n_episodes"]},
    }


def _point_delta_v(cell: dict, alphas: dict) -> float | None:
    v_m3 = richardson_v(cell["p"]["M3-ALL"], cell["y"], alphas["b"])
    base = [richardson_v(cell["p"][c], cell["y"], alphas["b"]) for c in BASELINE_CONFIGS]
    if v_m3 is None or any(v is None for v in base):
        return None
    return v_m3 - max(base)


def _quantile_claim_row(h: int, cell: dict, abst_q3: dict) -> dict:
    draws = cell["draws"]["primary"]
    metrics = cell["metrics"]["Q3-ALL"]
    loeo = loeo_checks(cell, "quantile", h)
    conditions: list[dict] = []
    lb = gate_lower_bound(draws["skill"])
    point = _point_skill(cell)
    conditions.append(
        {
            "condition": 1,
            "statistic": "pinball_skill (1 - PL(Q3)/min(PL(Q0), PL(Q1)), min inside each draw)",
            "point": point,
            "lb": lb,
            "threshold": 0.0,
            "pass": point is not None and lb > 0.0,
        }
    )
    for k in TAU_KEYS:
        tau = float(k)
        iv = interval_90(draws["coverage"][k])
        conditions.append(
            {
                "condition": 2,
                "statistic": f"coverage@tau={k} 90% interval intersects [tau-0.05, tau+0.05]",
                "point": metrics[f"coverage_{k}"],
                "lb": None,
                "threshold": [tau - 0.05, tau + 0.05],
                "pass": bool(iv[1] >= tau - 0.05 and iv[0] <= tau + 0.05),
                "detail": {"interval_90": iv},
            }
        )
    conditions.append(
        {
            "condition": 3,
            "statistic": "abstention (rate <= 5% of evaluation origins; event-vs-non-event gap <= 5pp)",
            "point": {"rate": abst_q3["rate"], "gap_pp": abst_q3["gap_pp"], **abst_q3["counts"]},
            "lb": None,
            "threshold": {"rate": 0.05, "gap_pp": 5.0},
            "pass": bool(abst_q3["rate"] <= 0.05 and abst_q3["gap_pp"] <= 5.0),
            "flag": None if abst_q3["rate"] <= 0.05 and abst_q3["gap_pp"] <= 5.0 else "ABSTENTION_CONCENTRATED",
        }
    )
    conditions.append(
        {
            "condition": 4,
            "statistic": "leave-one-episode-out keeps the pinball-skill point estimate above 0",
            "point": {"min": loeo["min"], "undefined": loeo["undefined_point_estimates"]},
            "lb": None,
            "threshold": 0.0,
            "pass": not loeo["fragile"],
            "flag": "FRAGILE" if loeo["fragile"] else None,
        }
    )
    power = cell["honest_n"]["power_floor"]
    conditions.append(
        {
            "condition": 5,
            "statistic": f"power floor (>= {POWER_MIN_EPISODES} episodes and >= {POWER_MIN_MONTHS} event months)",
            "point": {"episodes": cell["honest_n"]["episodes"], "event_months": cell["honest_n"]["event_months"]},
            "lb": None,
            "threshold": {"episodes": POWER_MIN_EPISODES, "event_months": POWER_MIN_MONTHS},
            "pass": bool(power["met"]),
            "flag": None if power["met"] else "UNDERPOWERED_DISCLOSED",
        }
    )
    flags = [c["flag"] for c in conditions if c.get("flag")]
    if not power["met"]:
        verdict = VERDICT_BLOCKED
    elif all(c["pass"] for c in conditions):
        verdict = VERDICT_QUALIFIED
    else:
        verdict = VERDICT_REJECTED
    return {
        "id": f"h{h}/P-all/quantile",
        "h": h,
        "pop": "P-all",
        "claim": "quantile",
        "statistic": "pinball_skill",
        "point": point,
        "lb": lb,
        "threshold": 0.0,
        "flags": flags,
        "verdict": verdict,
        "conditions": conditions,
        "honest_n": cell["honest_n"],
        "loeo": {"fragile": loeo["fragile"], "min": loeo["min"], "n_episodes": loeo["n_episodes"]},
    }


def _point_skill(cell: dict) -> float | None:
    mask = np.ones(len(cell["a"]), dtype=bool)
    pl_q3 = pinball_loss_sum(cell["a"], cell["q"]["Q3-ALL"], mask)
    pl_q0 = pinball_loss_sum(cell["a"], cell["q"]["Q0"], mask)
    pl_q1 = pinball_loss_sum(cell["a"], cell["q"]["Q1"], mask)
    if pl_q3 is None or not pl_q0 or not pl_q1:
        return None
    return 1.0 - pl_q3 / min(pl_q0, pl_q1)


def _blocked_claim_row(h: int, claim: str) -> dict:
    return {
        "id": f"h{h}/P-active/{claim}",
        "h": h,
        "pop": "P-active",
        "claim": claim,
        "statistic": None,
        "point": None,
        "lb": None,
        "threshold": None,
        "flags": ["OBSERVER_NOT_ON_MAIN"],
        "verdict": VERDICT_BLOCKED,
        "blocked_type": "OBSERVER_NOT_ON_MAIN",
        "detail": "P-active stays blocked until close_path.v1 (draft PR #8188) is on main; "
        "the claim keeps its 0.05/12 share of the family level",
    }


def build_gates(comp_by_h: dict, abst_tables: dict) -> list[dict]:
    """The 12 SS11 claims: {binary, quantile} x {P-all, P-active} x {5, 10, 21}."""
    rows: list[dict] = []
    for h in HORIZONS:
        rows.append(_binary_claim_row(h, comp_by_h[h]["binary"], abst_tables[h]["M3-ALL"]))
        rows.append(_quantile_claim_row(h, comp_by_h[h]["quantile"], abst_tables[h]["Q3-ALL"]))
    for h in HORIZONS:
        for claim in ("binary", "quantile"):
            rows.append(_blocked_claim_row(h, claim))
    return rows


# ── step 13b: descriptive differences with intervals (prereg SS11 closing) ───


def descriptive_differences(cell: dict, fam: str, h: int) -> dict:
    """B1/B2 against B0 and Q1 against Q0 on P-all: descriptive, never claims."""
    draws = cell["draws"]["primary"]
    alphas = alpha_grid(h)
    out: dict = {"note": "descriptive measurement, not claims (prereg SS11)"}
    if fam == "binary":
        for cfg in BASELINE_CONFIGS:
            point_v = richardson_v(cell["p"][cfg], cell["y"], alphas["b"])
            v_b0 = richardson_v(cell["p"]["B0"], cell["y"], alphas["b"])
            diff = draws["v"][cfg]["b"] - draws["v"]["B0"]["b"]
            # A draw where either V is undefined (-inf) makes the difference
            # undefined: record it at -inf, never NaN (bounds are np.quantile).
            diff[np.isneginf(draws["v"][cfg]["b"]) | np.isneginf(draws["v"]["B0"]["b"])] = -np.inf
            out[cfg] = {
                "delta_v_vs_b0@b": {
                    "point": None if point_v is None or v_b0 is None else point_v - v_b0,
                    "lb": gate_lower_bound(diff),
                    "interval_90": interval_90(diff),
                },
                "bss_vs_b0": {
                    "point": cell["metrics"][cfg]["bss"],
                    "lb": gate_lower_bound(draws["bss"][cfg]),
                    "interval_90": interval_90(draws["bss"][cfg]),
                },
            }
    else:
        out["Q1_vs_Q0"] = {
            "point": _point_skill_q1(cell),
            "lb": gate_lower_bound(draws["skill_q1_vs_q0"]),
            "interval_90": interval_90(draws["skill_q1_vs_q0"]),
        }
    return out


def _point_skill_q1(cell: dict) -> float | None:
    mask = np.ones(len(cell["a"]), dtype=bool)
    pl_q1 = pinball_loss_sum(cell["a"], cell["q"]["Q1"], mask)
    pl_q0 = pinball_loss_sum(cell["a"], cell["q"]["Q0"], mask)
    if pl_q1 is None or pl_q0 is None or pl_q0 == 0:
        return None
    return 1.0 - pl_q1 / pl_q0


# ── step 9b: abstention table (prereg SS9 "Abstention") ──────────────────────


def abstention_tables(fits: dict, n_rows: int, labels: dict[int, dict]) -> dict:
    """Per (h, config): rate over the evaluation origins, typed reasons, gap."""
    tables: dict[int, dict] = {}
    for h in HORIZONS:
        origin_idx = evaluation_origin_indices(n_rows, h)
        y = labels[h]["Y"].to_numpy(dtype=float, na_value=np.nan)[origin_idx]
        events = np.isfinite(y) & (y > 0)
        rows: dict[str, dict] = {}
        for cid in BINARY_CLAIM_CONFIGS + QUANTILE_CLAIM_CONFIGS + (SENSITIVITY_CONFIG,):
            series = gather_config_series(fits, h, cid, origin_idx)
            issued = series["issued"]
            abstained = ~issued
            counts = abstention_breakdown(issued, series["reasons"])
            rate = float(abstained.mean()) if len(abstained) else 0.0
            ev_rate = float(abstained[events].mean()) if events.any() else 0.0
            nonev_rate = float(abstained[~events].mean()) if (~events).any() else 0.0
            rows[cid] = {
                "population": "P-all",
                "evaluation_origins": int(len(origin_idx)),
                "rate": rate,
                "counts": counts,
                "abstention_rate_event_origins": ev_rate,
                "abstention_rate_nonevent_origins": nonev_rate,
                "gap_pp": (ev_rate - nonev_rate) * 100.0,
            }
        tables[h] = rows
    return tables


# ── step 16: negative control (prereg SS12) ──────────────────────────────────


def negative_control_shift(y: np.ndarray) -> np.ndarray:
    """The frozen shift: ``numpy.roll(y, len(y) // 2)`` (deterministic, no seed)."""
    arr = np.asarray(y, dtype=float)
    return np.roll(arr, len(arr) // 2)


def fit_shifted_binary_block(X_tr_raw: np.ndarray, y_tr: np.ndarray, X_te_raw: np.ndarray, C: float = C_MAIN) -> np.ndarray:
    """M3-ALL refit on rolled training labels (same standardisation/design path)."""
    y_shift = negative_control_shift(y_tr)
    _mean, std, X_tr, X_te = _standardise(X_tr_raw, X_te_raw)
    if (std == 0).any():
        raise _FitFailure("FEATURE_DEGENERATE", f"zero training std for shifted negative control")
    design_tr = np.column_stack([np.ones(len(y_shift)), X_tr])
    design_te = np.column_stack([np.ones(len(X_te)), X_te])
    beta = fit_logistic(design_tr, y_shift, C)
    return expit(design_te @ beta)


def fit_shifted_quantile_block(X_tr_raw: np.ndarray, a_tr: np.ndarray, X_te_raw: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Q3-ALL refit on rolled training targets; crossing-then-clip as SS6."""
    a_shift = negative_control_shift(a_tr)
    _mean, std, X_tr, X_te = _standardise(X_tr_raw, X_te_raw)
    if (std == 0).any():
        raise _FitFailure("FEATURE_DEGENERATE", "zero training std for shifted negative control")
    q_unclipped: dict[float, np.ndarray] = {}
    for tau in TAUS:
        b, beta = fit_quantile_lp(X_tr, a_shift, tau)
        q_unclipped[tau] = X_te @ beta + b
    issued, clipped, reasons = quantile_output_policy(q_unclipped[0.5], q_unclipped[0.8], q_unclipped[0.9])
    q50, q80, q90 = clipped
    return issued, {"0.5": q50, "0.8": q80, "0.9": q90, "reasons": reasons}


def run_negative_control(
    labels: dict[int, dict],
    features: pd.DataFrame,
    n_rows: int,
    comp_by_h: dict,
    deviations: list[dict] | None = None,
) -> dict:
    """Refit M3-ALL (C=1) and Q3-ALL per block with rolled labels/targets."""
    feat_matrix = {name: features[name].to_numpy(dtype=float) for name in FEATURE_COLUMNS}
    idx_all = np.arange(n_rows)
    m3_feats = ("dd63", "r5", "r10", "log_rv20")
    report: dict[int, dict] = {}
    for h in HORIZONS:
        A = labels[h]["A"].to_numpy(dtype=float)
        y = labels[h]["Y"].to_numpy(dtype=float, na_value=np.nan)
        binary_cell = comp_by_h[h]["binary"]
        quantile_cell = comp_by_h[h]["quantile"]
        eval_idx = binary_cell["eval_origin_idx"]
        n_eval = len(eval_idx)
        pos = {int(o): i for i, o in enumerate(eval_idx)}
        p_shift = np.full(n_eval, np.nan)
        issued_shift = np.zeros(n_eval, dtype=bool)
        q_shift = {k: np.full(n_eval, np.nan) for k in TAU_KEYS}
        issued_q_shift = np.zeros(n_eval, dtype=bool)
        abstained_blocks: list[str] = []
        for block_i, (s0, e0) in enumerate(fold_calendar_for_population(n_rows, h), start=1):
            candidates = idx_all[(idx_all >= WARM_IDX) & (idx_all < s0) & (idx_all <= n_rows - 1 - h)]
            train_idx = purged_training_indices(s0, h, candidates)
            test_idx = np.arange(s0, e0 + 1)
            y_tr, a_tr = y[train_idx], A[train_idx]
            thin, _stats = training_fold_is_thin(train_idx, y_tr)
            X_cols = np.column_stack([feat_matrix[f] for f in m3_feats])
            X_tr_raw = X_cols[train_idx]
            X_te_raw = X_cols[test_idx]
            if thin:
                abstained_blocks.append(f"b{block_i}:TRAINING_FOLD_THIN")
                continue
            try:
                p_hat = fit_shifted_binary_block(X_tr_raw, y_tr, X_te_raw)
                for j, o in enumerate(test_idx):
                    p_shift[pos[int(o)]] = p_hat[j]
                    issued_shift[pos[int(o)]] = True
            except _FitFailure as exc:
                abstained_blocks.append(f"b{block_i}:binary:{exc.type}")
            try:
                issued_q, q_hat = fit_shifted_quantile_block(X_tr_raw, a_tr, X_te_raw)
                for j, o in enumerate(test_idx):
                    for k in TAU_KEYS:
                        q_shift[k][pos[int(o)]] = q_hat[k][j]
                    issued_q_shift[pos[int(o)]] = bool(issued_q[j])
            except _FitFailure as exc:
                abstained_blocks.append(f"b{block_i}:quantile:{exc.type}")

        # Score on the comparison sets, restricted to the shifted refit's issued
        # origins (every comparison on identical eligibility).
        b_mask = binary_cell["common_mask"] & issued_shift
        y_eval = binary_cell["y_eval"]
        p_b0_eval = binary_cell["p_eval"]["B0"]
        bss = v_b = None
        if b_mask.any():
            bss = brier_skill_score(p_shift[b_mask], y_eval[b_mask], p_b0_eval[b_mask])
            v_b = richardson_v(p_shift[b_mask], y_eval[b_mask], alpha_grid(h)["b"])
        q_mask = quantile_cell["common_mask"] & issued_q_shift
        a_eval = quantile_cell["a_eval"]
        skill = None
        if q_mask.any():
            ones = np.ones(int(q_mask.sum()), dtype=bool)
            pl_q3 = pinball_loss_sum(a_eval[q_mask], {k: q_shift[k][q_mask] for k in TAU_KEYS}, ones)
            pl_q0 = pinball_loss_sum(a_eval[q_mask], {k: quantile_cell["q_eval"]["Q0"][k][q_mask] for k in TAU_KEYS}, ones)
            pl_q1 = pinball_loss_sum(a_eval[q_mask], {k: quantile_cell["q_eval"]["Q1"][k][q_mask] for k in TAU_KEYS}, ones)
            if pl_q3 is not None and pl_q0 and pl_q1:
                skill = 1.0 - pl_q3 / min(pl_q0, pl_q1)
        report[h] = {
            "m3-ALL-shifted": {
                "bss_vs_b0": bss,
                "v_at_b_h": v_b,
                "n_scored": int(b_mask.sum()),
            },
            "q3-ALL-shifted": {"pinball_skill": skill, "n_scored": int(q_mask.sum())},
            "abstained_blocks": abstained_blocks,
            "shift": "numpy.roll(y, len(y) // 2) per training prefix (deterministic, no seed)",
            "expectation": "at or below 0 (prereg SS12); neither a claim nor a gate",
        }
    return report


# ── step 17: INC replay (prereg SS6, own CURRENT_VINTAGE table) ──────────────


def run_inc(comp_by_h: dict, close: pd.Series, deviations: list[dict] | None = None) -> dict:
    """The 2026-09-22 displayed-probability replay; never pooled, never a gate."""
    audit_rel = "scripts/research/risk_radar_displayed_probability_audit.py"
    try:
        ok, blob = _git("rev-parse", f"HEAD:{audit_rel}")
        if not ok or blob != AUDIT_SCRIPT_BLOB:
            _deviation(
                deviations,
                "INC_SOURCE_DRIFT",
                f"{audit_rel} blob {blob!r} != frozen {AUDIT_SCRIPT_BLOB}",
            )
        ok_c, calib_blob = _git("hash-object", "data/risk_radar/calibration.json")
        calib_blob_sha = calib_blob if ok_c else "absent"
        from engine.risk_radar import _calib, leading_signals, subscore_series
        from engine.risk_radar_backtest import _spy, state_series
        from scripts.research.risk_radar_displayed_probability_audit import (
            displayed_probability_series,
            hot_tier_a_count,
        )
        from scripts.research.risk_radar_state_ladder_calibration import native_forward_labels

        calib = _calib()
        sigs = leading_signals()
        if sigs is None or sigs.empty:
            raise RuntimeError("leading_signals returned no usable history")
        subs = subscore_series(sigs, calib)
        if subs is None or subs.empty:
            raise RuntimeError("subscore_series returned no usable history")
        idx = sigs.index
        known = subs.notna().any(axis=1)
        state = state_series(subs, calib, sigs=sigs).reindex(idx).where(known)
        hot_count = hot_tier_a_count(subs, calib).reindex(idx)
        spy = _spy(drop_missing=False)
        if spy is None or spy.empty:
            raise RuntimeError("_spy(drop_missing=False) returned no closes")

        table = {
            "table": "INC",
            "evidence_class": "CURRENT_VINTAGE",
            "look_ahead_disclosed": True,
            "note": "own table, never pooled, never a reference model, never a gate",
            "audit_script_blob": blob if ok else "unavailable",
            "calibration_blob_sha": calib_blob_sha,
            "descriptive_verdict": VERDICT_DESCRIPTIVE,
            "horizons": {},
        }
        close_arr = close.to_numpy(dtype=float)
        for h in HORIZONS:
            cell = comp_by_h[h]["binary"]
            origin_idx = cell["origin_idx"]
            dates = pd.DatetimeIndex([close.index[int(o)] for o in origin_idx])
            labels = native_forward_labels(spy, dates, int(h), THRESHOLD)
            probability = displayed_probability_series(state, hot_count, calib, int(h))
            # Vectorised alignment to the comparison-set dates; absent rows stay NaN.
            p = probability.reindex(dates).to_numpy(dtype=float)
            y_native = (
                labels.drop_duplicates(subset="date")
                .set_index("date")["event"]
                .reindex(dates)
                .to_numpy(dtype=float)
            )
            covered = np.isfinite(p) & np.isfinite(y_native)
            n_covered = int(covered.sum())
            if n_covered == 0:
                raise RuntimeError(f"h{h}: INC covers no P-all evaluation origin")
            y_cov = y_native[covered].astype(bool)
            p_cov = p[covered]
            metrics = binary_metric_set(p_cov, y_cov, alphas=alpha_grid(h))
            # NaN p (uncovered origins) never alarms inside early_warning_table.
            early = early_warning_table(
                p, cell["y"], origin_idx, close_arr, cell["a"], int(h), cell["episodes"], BASE_RATES[h]
            )
            table["horizons"][f"h{h}"] = {
                "evaluation_origins": int(len(origin_idx)),
                "covered": n_covered,
                "coverage_share": n_covered / len(origin_idx),
                "metrics_vs_native_label": metrics,
                "early_warning_vs_protocol_episodes": early,
            }
        return table
    except Exception as exc:  # noqa: BLE001 - a replay failure blocks nothing else
        return {"blocked": "INC_SOURCE_UNAVAILABLE", "detail": f"{type(exc).__name__}: {exc}"}


# ── step 13c: early warning (prereg SS9, descriptive) ────────────────────────


def early_warning_table(
    p: np.ndarray,
    y: np.ndarray,
    origin_idx: np.ndarray,
    close_arr: np.ndarray,
    a_arr: np.ndarray,
    h: int,
    episodes: list[dict],
    b_h: float,
) -> dict:
    """Cluster recall, lead, missed damage, false alarms, runs, censoring."""
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=bool)
    origin_idx = np.asarray(origin_idx, dtype=int)
    alarm = p >= b_h  # NaN (uncovered / INC-absent) never alarms

    events = origin_idx[y]
    clusters = event_clusters(events, h)
    windows = [list(ep["window"]) for ep in episodes]

    def in_some_window(idx: int) -> bool:
        return any(lo <= idx <= hi for lo, hi in windows)

    n_clusters = len(clusters)
    recalled = 0
    leads: list[int] = []
    lead_censored = 0
    missed_damage: list[float] = []
    for cluster in clusters:
        member = np.isin(origin_idx, cluster)
        alarmed_events = alarm & member & y
        if alarmed_events.any():
            recalled += 1
            first = int(origin_idx[alarmed_events].min())
            hits = close_arr[first + 1 :] <= 0.95 * close_arr[first]
            if hits.any():
                leads.append(int(np.argmax(hits)) + 1)
            else:
                lead_censored += 1
        else:
            missed_damage.append(float(np.max(a_arr[member])))

    n_alarms = int(alarm.sum())
    false_alarms = alarm & ~y
    outside = np.array([not in_some_window(int(o)) for o in origin_idx], dtype=bool)
    alarmed_outside = alarm & outside
    positions = np.nonzero(alarm)[0]
    runs: list[dict] = []
    if len(positions):
        start = 0
        for k in range(1, len(positions) + 1):
            if k == len(positions) or origin_idx[positions[k]] != origin_idx[positions[k - 1]] + 1:
                members = positions[start:k]
                runs.append(
                    {
                        "length": int(len(members)),
                        "overlaps_episode": bool(any(in_some_window(int(o)) for o in origin_idx[members])),
                    }
                )
                start = k
    overlapping_runs = [r for r in runs if r["overlaps_episode"]]
    run_lengths = sorted(r["length"] for r in runs)
    first_origin, last_origin = int(origin_idx[0]), int(origin_idx[-1])
    censored_clusters = [
        i
        for i, cluster in enumerate(clusters)
        if cluster_window(cluster, h)[0] <= first_origin or cluster_window(cluster, h)[1] >= last_origin
    ]
    return {
        "alarm": f"p >= b_h = {b_h}",
        "n_clusters": n_clusters,
        "cluster_recall": (recalled / n_clusters) if n_clusters else None,
        "lead": {
            "n": len(leads),
            "median": float(np.median(leads)) if leads else None,
            "min": int(min(leads)) if leads else None,
            "max": int(max(leads)) if leads else None,
            "censored": lead_censored,
        },
        "missed_damage": {
            "clusters_without_alarm": len(missed_damage),
            "max": max(missed_damage) if missed_damage else None,
            "mean": float(np.mean(missed_damage)) if missed_damage else None,
        },
        "false_alarm_share": float(false_alarms.sum() / n_alarms) if n_alarms else None,
        "false_alarm_time": {
            "alarmed_outside_every_episode": int(alarmed_outside.sum()),
            "sessions_outside_every_episode": int(outside.sum()),
            "share": float(alarmed_outside.sum() / outside.sum()) if outside.sum() else None,
        },
        "alarm_runs": {
            "n_runs": len(runs),
            "median_length": float(np.median(run_lengths)) if run_lengths else None,
            "max_length": int(max(run_lengths)) if run_lengths else None,
            "share_overlapping_episode": (len(overlapping_runs) / len(runs)) if runs else None,
        },
        "censoring": {
            "censored_clusters": len(censored_clusters),
            "censored_cluster_ids": censored_clusters,
        },
    }


# ── step 18: artifacts (prereg SS12) ─────────────────────────────────────────


def _f(value, ndigits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return f"[{_f(value[0])}, {_f(value[1])}]"
    try:
        return f"{float(value):.{ndigits}g}"
    except (TypeError, ValueError):
        return str(value)


def render_markdown(payload: dict) -> str:
    """The results note, GENERATED from the JSON (aggregates only)."""
    lines: list[str] = []
    run = payload.get("run", {})
    lines.append("# Pullback stage-1 results (Grey Deer W3, 2026-10-11)")
    lines.append("")
    lines.append(f"- schema: `{payload.get('schema')}`; run commit `{run.get('commit_sha')}`")
    lines.append(f"- prereg blob `{payload['prereg']['blob_sha']}`; manifest v{payload['manifest']['version']} blob `{payload['manifest']['blob_sha']}`")
    sample = payload.get("sample", {})
    lines.append(f"- sample: {sample.get('rows')} rows {sample.get('first_date')}..{sample.get('last_date')}, `subframe_content_sha256` matches")
    lines.append(f"- trial budget: family `{payload['trial_budget']['family']}`, budget {payload['trial_budget']['budget']}, basis `{payload['trial_budget']['basis']}`")
    lines.append("")
    lines.append("## Gates (12 claims; prereg SS11 verdict words only)")
    lines.append("")
    lines.append("| claim | statistic | point | lower bound | verdict | flags |")
    lines.append("|---|---|---|---|---|---|")
    for row in payload.get("gates", []):
        lines.append(
            f"| {row['id']} | {row.get('statistic')} | {_f(row.get('point'))} | {_f(row.get('lb'))} | {row['verdict']} | {', '.join(row.get('flags', [])) or '—'} |"
        )
    lines.append("")
    lines.append("## Episodes and honest-N (prereg SS8)")
    lines.append("")
    lines.append("| h | family | origins | events | clusters | episodes | event months | power floor |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for key, fam_row in payload.get("episodes", {}).items():
        for fam, info in fam_row.items():
            hn = info["honest_n"]
            lines.append(
                f"| {key} | {fam} | {hn['origins']} | {hn['events']} | {hn['clusters']} | {hn['episodes']} | {hn['event_months']} | {'met' if hn['power_floor']['met'] else 'UNDERPOWERED_DISCLOSED'} |"
            )
    lines.append("")
    lines.append("## Comparison sets (descriptive; prereg SS7/SS9)")
    for key, fams in payload.get("comparison_sets", {}).items():
        for fam, info in fams.items():
            lines.append("")
            m3 = info["metrics"].get("M3-ALL") or info["metrics"].get("Q3-ALL")
            ref = info["metrics"].get("B0") or info["metrics"].get("Q0")
            if m3 and ref:
                headline = m3.get("v_b") if m3.get("v_b") is not None else m3.get("pinball_sum")
                lines.append(
                    f"- {key} {fam}: N_common {info['N_common']}, base rate {_f(ref.get('base_rate'))}; "
                    f"candidate Brier {_f(m3.get('brier'))} vs reference {_f(ref.get('brier'))}, "
                    f"BSS {_f(m3.get('bss'))}, V@b_h {_f(headline)}"
                )
    lines.append("")
    lines.append("## Negative control (prereg SS12; never a gate)")
    for key, row in payload.get("negative_control", {}).items():
        b = row.get("m3-ALL-shifted", {})
        q = row.get("q3-ALL-shifted", {})
        lines.append(
            f"- {key}: shifted M3 BSS {_f(b.get('bss_vs_b0'))}, V@b_h {_f(b.get('v_at_b_h'))}; "
            f"shifted Q3 pinball skill {_f(q.get('pinball_skill'))} — expected at or below 0"
        )
    inc = payload.get("inc", {})
    lines.append("")
    lines.append("## INC (incumbent replay; own CURRENT_VINTAGE table, never a gate)")
    if "blocked" in inc:
        lines.append(f"- BLOCKED: {inc['blocked']} — {inc.get('detail')}")
    else:
        for hkey, row in inc.get("horizons", {}).items():
            lines.append(
                f"- {hkey}: covers {row['covered']}/{row['evaluation_origins']} evaluation origins "
                f"({_f(row['coverage_share'])}); Brier vs native label {_f(row['metrics_vs_native_label']['brier'])}"
            )
    deviations = payload.get("deviations", [])
    lines.append("")
    lines.append("## Deviations")
    if deviations:
        for dev in deviations:
            lines.append(f"- `{dev['code']}`: {dev['detail']}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Blocked")
    blocked = payload.get("blocked", [])
    if blocked:
        for b in blocked:
            lines.append(f"- `{b['type']}`: {b['detail']}")
    else:
        lines.append("- none (completed run)")
    lines.append("")
    return "\n".join(lines)


def write_artifacts(out_dir: Path, payload: dict) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / RESULTS_JSON_NAME
    md_path = out_dir / RESULTS_MD_NAME
    json_path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, md_path


def assemble_payload(
    *,
    identities: dict,
    sample_info: dict,
    integrity: list,
    hydrate_info: dict,
    deviations: list,
    census: list,
    fits: dict,
    comp_by_h: dict,
    metrics_report: dict,
    episodes_report: dict,
    bootstrap_report: dict,
    gates: list[dict],
    abst_tables: dict,
    negative_control: dict,
    inc: dict,
    early_warning: dict,
    loeo_report: dict,
) -> dict:
    """The SS12 JSON key tree (aggregates only; no per-day prices, no closes)."""
    comparison_sets: dict = {}
    for h in HORIZONS:
        fams: dict[str, dict] = {}
        for fam in ("binary", "quantile"):
            cell = comp_by_h[h][fam]
            fams[fam] = {
                "compared_configs": list(cell["configs"]),
                "N_common": cell["report"]["N_common"],
                "issued_abstained_by_config": cell["report"]["configs"],
                "metrics": metrics_report[h][fam]["metrics"],
                "slices": metrics_report[h][fam]["slices"],
                "sensitivity_row": metrics_report[h][fam]["sensitivity"],
                "bootstrap": bootstrap_report[h][fam],
                "descriptive_differences": descriptive_differences(cell, fam, h),
                "descriptive_verdict": VERDICT_DESCRIPTIVE,
            }
        comparison_sets[f"h{h}"] = fams

    folds: dict = {}
    for h in HORIZONS:
        blocks = {
            key: value for key, value in fits["blocks"].items() if key.startswith(f"h{h}/")
        }
        folds[f"h{h}"] = {
            "n_blocks": len(blocks),
            "blocks": blocks,
            "thin_blocks": [key for key, value in blocks.items() if value.get("thin")],
            "q1_fallbacks": [
                row for row in fits.get("q1_fallbacks", []) if row.get("h") == h
            ],
        }

    configs: list[dict] = []
    for h in HORIZONS:
        for cid, row in abst_tables[h].items():
            configs.append(
                {
                    "horizon": h,
                    "config": cid,
                    "kind": "binary" if cid in BINARY_CLAIM_CONFIGS or cid == SENSITIVITY_CONFIG else "quantile",
                    "population": "P-all",
                    **row["counts"],
                    "abstention_rate": row["rate"],
                    "abstention_rate_event_origins": row["abstention_rate_event_origins"],
                    "abstention_rate_nonevent_origins": row["abstention_rate_nonevent_origins"],
                    "abstention_gap_pp": row["gap_pp"],
                }
            )
    configs.extend(fits["config_rows"])

    payload = dict(identities)
    payload["run"] = {**identities["run"], "hydrate": hydrate_info}
    payload["sample"] = {**sample_info, "integrity": integrity}
    payload["trial_budget"] = {"family": TRIAL_FAMILY, "budget": TRIAL_BUDGET, "basis": "itemized"}
    payload["census"] = census
    payload["folds"] = folds
    payload["configs"] = configs
    payload["comparison_sets"] = comparison_sets
    payload["episodes"] = {f"h{h}": episodes_report[h] for h in HORIZONS}
    payload["gates"] = gates
    payload["loeo"] = loeo_report
    payload["early_warning"] = early_warning
    payload["abstention"] = {f"h{h}": abst_tables[h] for h in HORIZONS}
    payload["negative_control"] = {f"h{h}": negative_control[h] for h in HORIZONS}
    payload["inc"] = inc
    payload["deviations"] = deviations
    payload["blocked"] = []
    return payload


def evaluate_and_write(
    *,
    out_dir: Path,
    identities: dict,
    sample_info: dict,
    integrity: list,
    hydrate_info: dict,
    deviations: list,
    close: pd.Series,
    labels: dict[int, dict],
    features: pd.DataFrame,
    populations: dict,
    census: list,
    fits: dict,
) -> None:
    """Steps 12-18: comparison sets, metrics, episodes, bootstrap, gates,
    negative control, INC and the SS12 artifacts (C12-C18)."""
    n_rows = len(close)
    dates = [str(d) for d in close.index]
    close_arr = close.to_numpy(dtype=float)
    rv20_raw = features["rv20"].to_numpy(dtype=float)

    comp_by_h = build_comparison_sets(fits, n_rows, labels)              # step 12
    metrics_report = compute_point_metrics(comp_by_h, n_rows, rv20_raw, dates)  # step 13
    episodes_report = compute_episodes(comp_by_h, dates)                 # step 14
    abst_tables = abstention_tables(fits, n_rows, labels)
    bootstrap_report = run_bootstrap_cells(comp_by_h)                    # step 15
    gates = build_gates(comp_by_h, abst_tables)
    loeo_report = {
        f"h{h}": {
            fam: loeo_checks(comp_by_h[h][fam], fam, h) for fam in ("binary", "quantile")
        }
        for h in HORIZONS
    }
    early_warning: dict = {}
    for h in HORIZONS:
        cell = comp_by_h[h]["binary"]
        early_warning[f"h{h}"] = {
            "M3-ALL": early_warning_table(
                cell["p"]["M3-ALL"], cell["y"], cell["origin_idx"], close_arr, cell["a"], h, cell["episodes"], BASE_RATES[h]
            )
        }
    negative_control = run_negative_control(labels, features, n_rows, comp_by_h, deviations)  # step 16
    inc = run_inc(comp_by_h, close, deviations)                          # step 17
    if "horizons" in inc:
        for h in HORIZONS:
            early_warning[f"h{h}"]["INC"] = inc["horizons"][f"h{h}"].pop("early_warning_vs_protocol_episodes", None)

    payload = assemble_payload(                                         # step 18
        identities=identities,
        sample_info=sample_info,
        integrity=integrity,
        hydrate_info=hydrate_info,
        deviations=deviations,
        census=census,
        fits=fits,
        comp_by_h=comp_by_h,
        metrics_report=metrics_report,
        episodes_report=episodes_report,
        bootstrap_report=bootstrap_report,
        gates=gates,
        abst_tables=abst_tables,
        negative_control=negative_control,
        inc=inc,
        early_warning=early_warning,
        loeo_report=loeo_report,
    )
    json_path, md_path = write_artifacts(Path(out_dir), payload)
    print("stage-1 run complete; gate verdicts:")
    for row in gates:
        print(f"  {row['id']:<22} {row['verdict']}" + (f"  [{', '.join(row['flags'])}]" if row["flags"] else ""))
    print(f"artifacts: {json_path}")
    print(f"           {md_path}")


# ── tables + blocked artifact + main ─────────────────────────────────────────


def print_identity_table(identities: dict) -> None:
    run = identities["run"]
    lines = [
        "identity table",
        f"  schema               : {identities['schema']}",
        f"  prereg path          : {identities['prereg']['path']}",
        f"  prereg blob sha      : {identities['prereg']['blob_sha']}",
        f"  prereg sha256        : {identities['prereg']['sha256']}",
        f"  manifest path        : {identities['manifest']['path']}",
        f"  manifest blob sha    : {identities['manifest']['blob_sha']}",
        f"  manifest version     : {identities['manifest']['version']}",
        f"  run commit sha       : {run['commit_sha']}",
        f"  script blob sha      : {run['script_blob_sha']}",
        f"  test blob sha        : {run['test_blob_sha']}",
        f"  frozen sample sha    : {SUBFRAME_SHA256}",
        f"  window               : {WINDOW_START}..{AS_OF} (1,321 sessions expected)",
        f"  python/numpy/pandas  : {run.get('python', '-')} / {run.get('numpy', '-')} / {run.get('pandas', '-')}",
        f"  scipy                : {run.get('scipy', '-')}",
    ]
    print("\n".join(lines))


def print_configuration_table() -> None:
    lines = ["configuration table (prereg SS6; frozen - no re-tuning, no additions)"]
    for cfg in CONFIGURATIONS:
        feats = ", ".join(cfg["features"]) or "-"
        params = " ".join(f"{k}={v}" for k, v in cfg["params"].items()) or "-"
        note = " sensitivity row, never a gate" if cfg.get("sensitivity") else ""
        lines.append(f"  {cfg['id']:<12} {cfg['kind']:<9} pop={cfg['population']:<6} features=[{feats}] {params}{note}")
    lines.append("  M3-ACT       binary    pop=P-active  BLOCKED / OBSERVER_NOT_ON_MAIN (stage 2; observer on draft PR #8188)")
    lines.append("  Q3-ACT       quantile  pop=P-active  BLOCKED / OBSERVER_NOT_ON_MAIN (stage 2)")
    lines.append("  INC          binary    incumbent replay, own CURRENT_VINTAGE table, never pooled, never a gate")
    print("\n".join(lines))


def write_blocked_artifact(out_dir: Path, payload: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / RESULTS_JSON_NAME).write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="grey_deer_pullback_stage1",
        description="Grey Deer pullback stage-1 execution (prereg 2026-10-11; one execution per revision)",
    )
    parser.add_argument("--out-dir", default="research/grey_deer", help="artifact directory (default: research/grey_deer)")
    parser.add_argument("--skip-hydrate", action="store_true", help="use the existing store object (deviation HYDRATE_SKIPPED)")
    parser.add_argument("--allow-dirty", action="store_true", help="skip the script/test blob == HEAD check (deviation DIRTY_TREE)")
    parser.add_argument("--dry-run", action="store_true", help="verify identities, print the identity and configuration tables, exit 0")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    deviations: list[dict] = []
    identities: dict | None = None
    hydrate_info: dict[str, object] = {"performed": False, "rc": None}

    try:
        identities = verify_identities(allow_dirty=args.allow_dirty, deviations=deviations)
        if args.dry_run:
            print_identity_table(identities)
            print_configuration_table()
            return 0

        hydrate_info = hydrate(skip=args.skip_hydrate, deviations=deviations)
        df = load_sample()
        sample_info, window = sample_identity(df)
        integrity = integrity_checks(window)
        close = pd.Series(
            window["close"].to_numpy(dtype=float),
            index=pd.Index(window["date"].tolist(), name="date"),
        )

        with trial_ledger_scope():
            labels = build_labels(close)
            features = build_features(close)
            populations = build_populations(len(close))
            census = census_populations(len(close), int(sample_info["pre_window_rows_dropped"]))
            fits = run_fits(close, labels, features, deviations)
            # Steps 12-18 (metrics, comparison sets, bootstrap, gates, negative
            # control, INC, artifacts) are GD-W3-BUILD part 2.
            evaluate_and_write(
                out_dir=out_dir,
                identities=identities,
                sample_info=sample_info,
                integrity=integrity,
                hydrate_info=hydrate_info,
                deviations=deviations,
                close=close,
                labels=labels,
                features=features,
                populations=populations,
                census=census,
                fits=fits,
            )
    except Blocked as blocked:
        print(f"BLOCKED / {blocked.type}")
        payload: dict = {"schema": SCHEMA}
        if identities is not None:
            payload.update(identities)
        payload["hydrate"] = hydrate_info
        payload["deviations"] = deviations
        payload["blocked"] = [{"type": blocked.type, "detail": blocked.detail}]
        try:
            write_blocked_artifact(out_dir, payload)
        except OSError as exc:
            sys.stderr.write(f"blocked-artifact write failed: {exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
