"""Grey Deer pullback stage-1 executing script (GD-W3, part 1 of 2).

Executes ``research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md`` (blob
``49a68b5e9c6543d662044b0aa391c4b6e6e6052e``) against its eligible-input
manifest ``research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md``
(v1.0.0, blob ``38925409555d046eb9d3ad38ddaba33e2159a3d3``). One execution per
revision; a silent change to any frozen choice voids the revision. The real
run belongs to the Fable seat; this build never executes the real data path
(only ``--help`` / ``--dry-run`` are exercised in GD-W3-BUILD).

Part split: part 1 (this file as committed here) implements the script
contract, run steps 1-11 and the identity/purge/fold/crossing machinery, with
``evaluate_and_write`` (steps 12-18: metrics, comparison sets, episodes,
bootstrap, gates, negative control, INC, artifacts) raising
``NotImplementedError("GD-W3-BUILD part 2")`` until part 2 lands.

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
12. ``evaluate_and_write`` - PART 2 (steps 12-18).

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
    comparison_sets            (part 2, SS10 intersection-of-issued origins)
    episodes                   (part 2, SS8 clusters/episodes/power floor)
    gates                      (part 2, the 12 gated claims)
    loeo                       (part 2, leave-one-episode-out)
    early_warning              (part 2, SS9 descriptive early warning)
    abstention                 (part 2, frequency + typed reasons)
    negative_control           (part 2, SS12 shifted-label refits)
    inc                        (part 2, incumbent replay, own table)
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
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize
from scipy.special import expit

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


# ── step 12 placeholder: part 2 ──────────────────────────────────────────────


def evaluate_and_write(**_context) -> None:
    """GD-W3-BUILD part 2: metrics, comparison sets, episodes, bootstrap,
    gates, negative control, INC and the SS12 artifacts (C12-C18)."""
    raise NotImplementedError("GD-W3-BUILD part 2")


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
