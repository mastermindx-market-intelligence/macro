"""Q13 evaluation harness — risk-neutral tail density, PROXY comparison.

Research harness only. It is never imported, scheduled, wired or promoted.
It refuses to run unless sha256(PREREG.md) equals the hash in FREEZE.log, and
it appends every run (command, exit code, input and output sha256s) to
RUNS.log.

Stages (PREREG sections 13-15, amendment A1):

    absence   scan for any in-repo RN-density incumbent
    baseline  reproduce engine.options_skew.compute_skew against the ledger
    compare   the single preregistered PROXY comparison (runs once)

Every quantity is a risk-neutral (Q) pricing-measure quantity. Nothing here
is a physical (P) probability, crash odds or a forecast. The verdict is fixed
by PREREG section 0: INSUFFICIENT_DATA (M1-M4), whatever the proxy shows.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import shlex
import sys
import traceback
import types
from datetime import date
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREREG = HERE / "PREREG.md"
FREEZE = HERE / "FREEZE.log"
AMEND = HERE / "PREREG_AMENDMENT.md"
RUNS = HERE / "RUNS.log"
RESULTS = HERE / "results"
MODULE_REL = "engine/options_rn_tail_density.py"
TEST_REL = "tests/test_options_rn_tail_density.py"
INCUMBENT_REL = "engine/options_skew.py"
DEFAULT_DATA_ROOT = Path("/Users/chriswong/Documents/Cluade/macro-main/data")

INCUMBENT_SHA = "8f68ad06c29ff9e05d6f4a710912b12a8523344d3b84a22524867e4711b38dce"
SOFR_REL = "ofr/FNYR-SOFR-A.parquet"
SOFR_SHA = "02dca610d9d4857a002beee07aef0a3f96af943131efba5d0861c0d5b1ddc620"
SNAP_REL = "options_skew/snapshots.parquet"
SNAP_SHA = "18a16c9f72a3f6ac1548a22efaaebaa348265fe783d93ca29da1a8d4c2a53b56"

# PREREG section 5: the frozen input table (file name -> sha256).
CHAIN_SHA: dict[str, str] = {
    "2026-06-15": "b3b64a15a058f60fd3f83e5be23b9c500b720ce9719f2acf67068826fdc98f21",
    "2026-06-17": "3b764b176fadd2c0d9018df4b572cd92aa33eba8262c94f8b73c9321e08fc5d2",
    "2026-06-18": "91dfe4034235a5d47544ea8ecf69692593a6a1a9224598496b0c256856e561b5",
    "2026-06-24": "3425ac28473f3ec53690284bc5b969e33cab2e60dfb7d2ab3a6df0f9b7ccf846",
    "2026-06-26": "b295c88c375e92809f16e5d0a47ade28ab64ffa47d1bd61defe90255769b504d",
    "2026-06-30": "475ff75749f18d9250f257af7c8506dc78058b6efe785e55cbd2f6364071c450",
    "2026-07-01": "2e5ec91417d811d7282a8de69134d39a19800af4172c25f33849e5de2e786aa7",
    "2026-07-02": "27c8f4c9768480b892a3f377e37510b3a1a23156b5389212e1a5b557b7288f06",
    "2026-07-07": "0f37eaa140c4a6ad4d1576b93938ac7c829c955e096aee5804ec8c821bacba9d",
    "2026-07-08": "0e5086480bbd38e0b862c784ee85c6879ad90fdc48432d5c6046d7896366122e",
    "2026-07-09": "f80811096a2e0a5cd6df506c5ada7f600cb9e9901618b4b26302b5fe8d89678c",
    "2026-07-10": "b48992f0b89f58c4b5f9706a89aa51b5b8e33fe41a02a43174fd47bc8a289fe4",
    "2026-07-13": "e3f4f5bc20863d2add0c7f075f1604b646f4bcba6d5a33d4c98105da9019effa",
    "2026-07-15": "0dbb288cd3f98c7d0dc4b6139239ff57e6724dc70b5831f04f5046433cd83cf0",
    "2026-07-17": "846f60b395c0c16a9d4f45f0c371e05aceefba5b120c7f632e08bfd92ee98c7f",
    "2026-07-20": "0b5e48eb981fe04a90035f2992444607b59467e085717bef9e948367a75ec25e",
    "2026-07-21": "22951e0788fd642d49e5096203f3cc99402c70c87c0a716c412a8924dad8f850",
    "2026-07-22": "d6edd7c50b149857803940894d862dfeecb5c683e56650962ccfc6a18d715deb",
    "2026-07-23": "f018d9506be417001937bee33a95d4007417b3d8ad5919c5be9d9f1bf61e14bf",
    "2026-07-24": "a263ed1a46c52f44d967b4b6ba5cbd69a89b861c3c29262ad3bebdc7411c3117",
    "2026-07-27": "7023fde67dda28bd3ab7d4c430e3ca75936f7bad151a514cb22926a962825eb8",
    "2026-07-28": "dcffd24ecb49d4fb0fd11b19d86fc73b129564d38919256a353de1de97fb408a",
    "2026-07-29": "a77f545f68e2f90674bc32a55c3c94d57b01c5b0c0b30dae140e068176822c07",
    "2026-07-30": "f941d5ebd512b3df356daaac88365c5892bf1176d7845f8c99dc67609bd30636",
    "2026-08-06": "d4a486c94b274e9419d09639e51f25d1c4fc1cde759612ab14fc536a05577d92",
    "2026-08-10": "c2488d33c7ff96c7ffeaa7386fb494794ef13d73998f1187c8b14ca1296ac267",
    "2026-08-12": "68782399b571feafa34bdeb5171c4da03f71fa72b57f17e608d63c6d2390153f",
    "2026-08-13": "846a8f144a3b6315cebabdec7c7eb85d81ea70a2d2a6b064b3beacb0dc84cc28",
}

# PREREG section 10: ISO-week blocks (checked against the calendar at run time).
TRAIN_BLOCKS = ("W25", "W26", "W27", "W28", "W29")
TEST_BLOCKS = ("W30", "W31", "W32", "W33")

# Frozen protocol constants (PREREG sections 3, 6, 8, 9, 11, 13, 14).
K_STAR_RATIO = 0.90
K_SECONDARY_RATIO = 0.95
IV_MIN, IV_MAX = 0.02, 2.5
TRUTH_LO, TRUTH_HI = 0.75, 1.00
TRUNC_LO, TRUNC_HI = 0.95, 1.10
FULL_LO, FULL_HI = 0.75, 1.25
N_NODES = 1601
LAMS = (0.0, 1e-4, 1e-3, 1e-2, 1e-1)
MS = (3, 5, 8, 12)
TIE_TOL = 1e-12
B_BOOT = 4000
SEED = 13013
BAND_SCALES = (0.5, 1.0, 2.0)
CUTS = (0.93, 0.95, 0.97)
N_DRAWS = 100
COVERAGE_MIN = 0.80
MEDIAN_REL_WIDTH_MAX = 0.5
ATTRITION_MAX = 0.50
EFFECT_RATIO = 0.75
EFFECT_ABS = 0.002
BASELINE_TOL = 1e-4 + 1e-9
N_TEST_DATES = 13

ABSENCE_PATTERNS = (
    r"breeden",
    r"litzenberger",
    r"risk[-_ ]?neutral[-_ ]?(density|distribution|pdf)",
    r"state[-_ ]?price[-_ ]?density",
    r"\brnd\b",
    r"rn[-_]density",
    r"tail[-_ ]density",
    r"implied[-_ ](density|distribution|pdf)",
)


# ---------------------------------------------------------------------------
# Hashing, logging, loading
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_hash() -> str:
    for line in FREEZE.read_text(encoding="utf-8").splitlines():
        if line.startswith("PREREG_SHA256="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("FREEZE.log carries no PREREG_SHA256 line")


def previous_runs() -> list[dict[str, str]]:
    if not RUNS.exists():
        return []
    blocks: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        if line.startswith("=== RUN "):
            cur = {}
            blocks.append(cur)
        elif cur is not None and "=" in line and not line.startswith(" "):
            key, val = line.split("=", 1)
            cur.setdefault(key.strip(), val.strip())
    return blocks


def append_run(record: dict[str, Any]) -> None:
    n = len(previous_runs()) + 1
    lines = [f"=== RUN {n} ==="]
    for key in ("utc_stamp", "stage", "command", "thread_env", "prereg_sha256", "freeze_sha256",
                "amendment_sha256", "evaluate_sha256", "module_sha256", "incumbent_sha256"):
        lines.append(f"{key}={record.get(key, '')}")
    lines.append("inputs:")
    for rel, sha in record.get("inputs", []):
        lines.append(f"  {rel} {sha}")
    lines.append("outputs:")
    for rel, sha in record.get("outputs", []):
        lines.append(f"  {rel} {sha}")
    if record.get("note"):
        lines.append(f"note={record['note']}")
    lines.append(f"exit_code={record['exit_code']}")
    lines.append("")
    with open(RUNS, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def load_from_path(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_incumbent() -> types.ModuleType:
    """Load engine/options_skew.py with an in-memory lib.config stub (PREREG section 15)."""
    path = ROOT / INCUMBENT_REL
    got = sha256_file(path)
    if got != INCUMBENT_SHA:
        raise InputHashError(f"{INCUMBENT_REL} sha256 {got} != frozen {INCUMBENT_SHA}")
    if "lib" not in sys.modules:
        lib_stub = types.ModuleType("lib")
        cfg_stub = types.ModuleType("lib.config")
        lib_stub.config = cfg_stub  # type: ignore[attr-defined]
        sys.modules["lib"] = lib_stub
        sys.modules["lib.config"] = cfg_stub
    return load_from_path("q13_incumbent_options_skew", path)


def load_module() -> types.ModuleType:
    return load_from_path("q13_options_rn_tail_density", ROOT / MODULE_REL)


class InputHashError(RuntimeError):
    pass


class StopRuleRefusal(RuntimeError):
    pass


def check_input(data_root: Path, rel: str, expected: str, inputs: list[tuple[str, str]]) -> Path:
    path = data_root / rel
    if not path.is_file():
        raise InputHashError(f"missing input data/{rel}")
    got = sha256_file(path)
    inputs.append((f"data/{rel}", got))
    if got != expected:
        raise InputHashError(f"data/{rel} sha256 {got} != frozen {expected}")
    return path


def jclean(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): jclean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jclean(v) for v in x]
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        v = float(x)
        if math.isnan(v):
            return None
        if math.isinf(v):
            return "inf" if v > 0 else "-inf"
        return v
    return x


def write_json(path: Path, obj: Any, outputs: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jclean(obj), indent=1, sort_keys=False, allow_nan=False) + "\n", encoding="utf-8")
    outputs.append((str(path.relative_to(ROOT)), sha256_file(path)))


def write_csv(path: Path, df: pd.DataFrame, outputs: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, lineterminator="\n", float_format="%.10g")
    outputs.append((str(path.relative_to(ROOT)), sha256_file(path)))


# ---------------------------------------------------------------------------
# Calendar blocks (from file names; no wall clock)
# ---------------------------------------------------------------------------


def iso_block(d: str) -> str:
    return f"W{date.fromisoformat(d).isocalendar()[1]:02d}"


def split_of(block: str) -> str:
    if block in TRAIN_BLOCKS:
        return "TRAIN"
    if block in TEST_BLOCKS:
        return "TEST"
    raise RuntimeError(f"block {block} is in neither split")


def check_blocks() -> None:
    expected = {
        "W25": 3, "W26": 2, "W27": 3, "W28": 4, "W29": 3, "W30": 5, "W31": 4, "W32": 1, "W33": 3,
    }
    got: dict[str, int] = {}
    for d in CHAIN_SHA:
        got[iso_block(d)] = got.get(iso_block(d), 0) + 1
    if got != expected:
        raise RuntimeError(f"ISO-week blocks {got} differ from PREREG section 10 {expected}")


# ---------------------------------------------------------------------------
# Absence stage
# ---------------------------------------------------------------------------


def stage_absence(args: argparse.Namespace, inputs: list, outputs: list) -> None:
    scan_root = Path(args.scan_root).resolve()
    pats = [re.compile(p, re.IGNORECASE) for p in ABSENCE_PATTERNS]
    manifest: list[str] = []
    hits: list[dict[str, Any]] = []
    n_files = 0
    for sub in ("engine", "scripts", "tests"):
        base = scan_root / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            rel = str(path.relative_to(scan_root))
            if rel in (MODULE_REL, TEST_REL):
                continue
            n_files += 1
            raw = path.read_bytes()
            manifest.append(f"{rel} {hashlib.sha256(raw).hexdigest()}")
            text = raw.decode("utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), 1):
                for pat in pats:
                    if pat.search(line):
                        hits.append({"path": rel, "line": lineno, "pattern": pat.pattern,
                                     "text": line.strip()[:200]})
                        break
    manifest_sha = hashlib.sha256("\n".join(manifest).encode("utf-8")).hexdigest()
    inputs.append((f"scan_manifest[{n_files} files under {scan_root}]", manifest_sha))
    out = {
        "stage": "absence",
        "scan_root": str(scan_root),
        "scanned_dirs": ["engine", "scripts", "tests"],
        "n_py_files": n_files,
        "manifest_sha256": manifest_sha,
        "patterns": list(ABSENCE_PATTERNS),
        "n_hits": len(hits),
        "hit_files": sorted({h["path"] for h in hits}),
        "hits": hits,
        "q13_module_present_in_scan_root": (scan_root / MODULE_REL).exists(),
        "q13_test_present_in_scan_root": (scan_root / TEST_REL).exists(),
        "note": "Hits are listed for manual classification (VERDICT.md); a hit is not an incumbent by itself.",
    }
    write_json(RESULTS / "absence.json", out, outputs)


# ---------------------------------------------------------------------------
# Baseline stage
# ---------------------------------------------------------------------------


def spy_rows(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return df[df["underlying"].astype(str).str.upper() == "SPY"].copy()


def stage_baseline(args: argparse.Namespace, inputs: list, outputs: list) -> None:
    data_root = Path(args.data_root)
    sk = load_incumbent()
    snap = pd.read_parquet(check_input(data_root, SNAP_REL, SNAP_SHA, inputs))
    snap = snap[(snap["underlying"].astype(str).str.upper() == "SPY") & (snap["source"].astype(str) == "polygon_gex")]
    snap_date = snap["date"].astype(str).str[:10]
    rows: list[dict[str, Any]] = []
    for d, sha in CHAIN_SHA.items():
        chain = spy_rows(check_input(data_root, f"polygon_gex/chains/{d}.parquet", sha, inputs))
        got = sk.compute_skew(chain)
        ref = snap[snap_date == d]
        row: dict[str, Any] = {"date": d, "n_ledger_rows": int(len(ref)), "computed": got is not None}
        if got is not None:
            for key in ("spot", "tenor_days", "otm_put_iv", "atm_call_iv", "skew", "n_strikes"):
                row[f"computed_{key}"] = got[key]
        if len(ref) and got is not None:
            r0 = ref.iloc[0]
            ok = True
            for key in ("otm_put_iv", "atm_call_iv", "skew"):
                diff = abs(float(got[key]) - float(r0[key]))
                row[f"ledger_{key}"] = float(r0[key])
                row[f"absdiff_{key}"] = diff
                ok = ok and diff <= BASELINE_TOL
            for key in ("spot", "tenor_days", "n_strikes"):
                row[f"ledger_{key}"] = r0[key]
            row["status"] = "match" if ok else "mismatch"
        elif got is None:
            row["status"] = "not_computed"
        else:
            row["status"] = "ledger_row_missing"
        rows.append(row)
    df = pd.DataFrame(rows)
    write_csv(RESULTS / "baseline_repro.csv", df, outputs)
    counts = df["status"].value_counts().to_dict()
    summary = {
        "stage": "baseline",
        "incumbent": INCUMBENT_REL,
        "incumbent_sha256": INCUMBENT_SHA,
        "function": "compute_skew",
        "fields": ["otm_put_iv", "atm_call_iv", "skew"],
        "tolerance_abs": BASELINE_TOL,
        "n_dates": int(len(df)),
        "status_counts": counts,
        "all_match": bool(counts.get("match", 0) == len(df)),
        "max_absdiff": {k: float(df[f"absdiff_{k}"].max()) if f"absdiff_{k}" in df else None
                        for k in ("otm_put_iv", "atm_call_iv", "skew")},
        "lib_config": "in-memory stub (PREREG section 15); no .env read",
    }
    write_json(RESULTS / "baseline_summary.json", summary, outputs)


def stage_baseline_census(args: argparse.Namespace, inputs: list, outputs: list) -> None:
    """Amendment A2: a diagnostic census of the SPY skew ledger. No verdict effect."""
    data_root = Path(args.data_root)
    sk = load_incumbent()
    snap = pd.read_parquet(check_input(data_root, SNAP_REL, SNAP_SHA, inputs))
    spy = snap[snap["underlying"].astype(str).str.upper() == "SPY"].copy()
    spy["d10"] = spy["date"].astype(str).str[:10]
    ledger_rows = []
    for _, r in spy.sort_values(["d10", "source"]).iterrows():
        ledger_rows.append({
            "source": str(r["source"]), "date": r["d10"], "asof": str(r["asof"])[:10],
            "weekday": pd.Timestamp(r["d10"]).day_name(), "chain_file_retained": r["d10"] in CHAIN_SHA,
        })
    by_source: dict[str, Any] = {}
    for src, g in spy.groupby(spy["source"].astype(str)):
        dates = sorted(g["d10"].tolist())
        by_source[src] = {
            "n_rows": int(len(g)), "first_date": dates[0], "last_date": dates[-1],
            "weekday_counts": {k: int(v) for k, v in
                               pd.Series([pd.Timestamp(x).day_name() for x in dates]).value_counts().items()},
            "n_chain_dates_covered": int(sum(1 for d in CHAIN_SHA if d in set(dates))),
        }
    cross = []
    for d, sha in CHAIN_SHA.items():
        chain = spy_rows(check_input(data_root, f"polygon_gex/chains/{d}.parquet", sha, inputs))
        asofs = sorted({str(a)[:10] for a in chain["asof"].tolist()})
        got = sk.compute_skew(chain)
        ref = spy[(spy["d10"] == d) & (spy["source"].astype(str) == "thetadata")]
        row: dict[str, Any] = {"date": d, "chain_asof_values": asofs, "thetadata_row": bool(len(ref))}
        if got is not None and len(ref):
            r0 = ref.iloc[0]
            for key in ("otm_put_iv", "atm_call_iv", "skew"):
                row[f"absdiff_{key}"] = abs(float(got[key]) - float(r0[key]))
            row["computed_n_strikes"] = int(got["n_strikes"])
            row["thetadata_n_strikes"] = int(r0["n_strikes"])
        cross.append(row)
    cdf = pd.DataFrame(cross)
    med = {k: (float(cdf[f"absdiff_{k}"].median()) if f"absdiff_{k}" in cdf and cdf[f"absdiff_{k}"].notna().any()
               else None) for k in ("otm_put_iv", "atm_call_iv", "skew")}
    summary = {
        "stage": "baseline_census",
        "amendment": "A2 (diagnostic only; PREREG section 15 rule and RUN 2 result unchanged)",
        "ledger": SNAP_REL,
        "spy_rows_by_source": by_source,
        "chain_dates": len(CHAIN_SHA),
        "chain_dates_with_polygon_gex_row": int(sum(1 for d in CHAIN_SHA
                                                    if ((spy["d10"] == d) & (spy["source"] == "polygon_gex")).any())),
        "chain_dates_with_thetadata_row": int(cdf["thetadata_row"].sum()),
        "polygon_gex_rows_with_retained_chain_file": int(sum(1 for r in ledger_rows
                                                             if r["source"] == "polygon_gex" and r["chain_file_retained"])),
        "cross_source_diagnostic": {
            "label": "CROSS-SOURCE DIAGNOSTIC - thetadata rows come from a different vendor chain; not a reproduction",
            "median_absdiff": med,
            "per_date": cross,
        },
        "ledger_spy_rows": ledger_rows,
    }
    write_json(RESULTS / "baseline_ledger_census.json", summary, outputs)


# ---------------------------------------------------------------------------
# Compare stage
# ---------------------------------------------------------------------------


class DateCtx:
    """Per-date inputs shared by every estimator (one basis per date)."""

    def __init__(self, d: str) -> None:
        self.d = d
        self.block = iso_block(d)
        self.split = split_of(self.block)
        self.reasons: list[str] = []
        self.basis: Any = None
        self.leg: pd.DataFrame | None = None
        self.expiry = ""
        self.otm: pd.DataFrame | None = None       # collapsed usable OTM rows
        self.raw_otm: pd.DataFrame | None = None   # usable OTM rows before collapse
        self.both: pd.DataFrame | None = None      # collapsed usable rows, both legs
        self.info: dict[str, Any] = {"date": d, "block": self.block, "split": self.split}


def prepare(ctx: DateCtx, chain: pd.DataFrame, sofr: pd.Series, rn: Any, sk: Any) -> None:
    leg = sk._nearest_expiry(chain)
    if leg is None or leg.empty:
        ctx.reasons.append("no_expiry")
        return
    ctx.leg = leg
    ctx.expiry = str(pd.Timestamp(leg["expiry"].iloc[0]).date())
    T = float(np.median(leg["T"].astype("float64").to_numpy()))
    spot = float(np.float64(leg["spot"].iloc[0]))
    prior = sofr[sofr.index < pd.Timestamp(ctx.d)]
    if prior.empty:
        ctx.reasons.append("no_rate")
        return
    r = float(prior.iloc[-1]) / 100.0
    ctx.basis = rn.make_forward_basis(spot, r, T, 0.0, label=f"SPY {ctx.d} SOFR/100 q=0 Black-76")
    F = ctx.basis.forward
    ctx.info.update({"expiry": ctx.expiry, "T": T, "spot": spot, "sofr_date": str(prior.index[-1].date()),
                     "rate": r, "forward": F, "discount": ctx.basis.discount})
    K = pd.to_numeric(leg["K"], errors="coerce").astype("float64")
    iv = pd.to_numeric(leg["iv"], errors="coerce").astype("float64")
    usable = np.isfinite(iv) & (iv >= IV_MIN) & (iv <= IV_MAX) & np.isfinite(K) & (K > 0)
    is_call = leg["is_call"].astype(bool)
    otm_mask = usable & ((is_call & (K >= F)) | (~is_call & (K < F)))
    ctx.raw_otm = leg.loc[otm_mask].copy()
    ctx.raw_otm["_K64"] = K[otm_mask]
    frame = pd.DataFrame({"K": K[usable], "is_call": is_call[usable], "iv": iv[usable]})
    both = frame.groupby(["K", "is_call"], as_index=False)["iv"].median().sort_values(["K", "is_call"])
    ctx.both = both.reset_index(drop=True)
    otm = both[(both["is_call"] & (both["K"] >= F)) | (~both["is_call"] & (both["K"] < F))]
    ctx.otm = otm.sort_values("K").reset_index(drop=True)
    ctx.info.update({"n_rows_leg": int(len(leg)), "n_usable": int(usable.sum()), "n_otm_collapsed": int(len(ctx.otm))})


def truth_puts(ctx: DateCtx) -> pd.DataFrame:
    F = ctx.basis.forward
    o = ctx.otm
    m = (~o["is_call"]) & (o["K"] >= TRUTH_LO * F) & (o["K"] < TRUTH_HI * F)
    return o[m]


def truth_bounds(ctx: DateCtx, rn: Any, k_ratio: float, scale: float) -> dict[str, Any] | None:
    tp = truth_puts(ctx)
    if tp.empty:
        return None
    F = ctx.basis.forward
    K = tp["K"].to_numpy(float)
    iv = tp["iv"].to_numpy(float)
    hw = rn.iv_half_width(np.log(K / F), scale)
    _, lo, hi = rn.call_equivalent_bands(ctx.basis, K, iv, np.zeros(K.size, dtype=bool), hw)
    return rn.tail_probability_bounds(K, lo, hi, ctx.basis, k_ratio * F)


def truth_support(ctx: DateCtx) -> tuple[int, int]:
    F = ctx.basis.forward
    tp = truth_puts(ctx)
    k_star = K_STAR_RATIO * F
    return int((tp["K"] <= k_star).sum()), int((tp["K"] >= k_star).sum())


def trunc_rows(ctx: DateCtx, cut: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    F = ctx.basis.forward
    o = ctx.otm
    col = o[(o["K"] >= cut * F) & (o["K"] <= TRUNC_HI * F)]
    raw = ctx.raw_otm
    rawsel = raw[(raw["_K64"] >= cut * F) & (raw["_K64"] <= TRUNC_HI * F)].drop(columns=["_K64"])
    return col, rawsel


def trunc_support_ok(col: pd.DataFrame) -> tuple[bool, int, int]:
    n_put = int((~col["is_call"]).sum())
    n_call = int(col["is_call"].sum())
    return (len(col) >= 4 and n_put >= 2 and n_call >= 2), n_put, n_call


def smile_C(ctx: DateCtx, col: pd.DataFrame, rn: Any, lam: float, m: int) -> Any:
    F = ctx.basis.forward
    K = col["K"].to_numpy(float)
    return rn.fit_smile(np.log(K / F), col["iv"].to_numpy(float), ctx.basis.T, lam, m)


def incumbent_legs(rawsel: pd.DataFrame, sk: Any) -> tuple[dict | None, dict | None]:
    put = sk._iv_selection_at_delta(rawsel, sk._PUT_DELTA, want_call=False)
    call = sk._iv_selection_at_delta(rawsel, sk._CALL_DELTA, want_call=True)
    return put, call


def smiles_B(ctx: DateCtx, rawsel: pd.DataFrame, rn: Any, sk: Any) -> tuple[Any, Any, dict]:
    F, T = ctx.basis.forward, ctx.basis.T
    put, call = incumbent_legs(rawsel, sk)
    meta: dict[str, Any] = {"b1_put": put, "b1_call": call}
    b1 = b0 = None
    if put is not None and call is not None:
        b1 = rn.two_point_smile(math.log(put["strike"] / F), put["iv"], math.log(call["strike"] / F), call["iv"], T)
    if call is not None:
        b0 = rn.flat_smile(call["iv"], T)
    return b1, b0, meta


def safe_q(smile: Any, ctx: DateCtx, rn: Any, k_ratio: float) -> float:
    if smile is None:
        return float("nan")
    try:
        return float(rn.q_tail_probability(smile, ctx.basis, k_ratio * ctx.basis.forward, N_NODES))
    except Exception:  # noqa: BLE001 - A1.3: a raising estimator fails
        return float("nan")


def select_config(train: list[DateCtx], rn: Any) -> tuple[tuple[float, int], list[dict[str, Any]]]:
    grid_rows: list[dict[str, Any]] = []
    scoring = [c for c in train if c.info.get("truth_ok") and c.info.get("trunc_ok")]
    for lam in LAMS:
        for m in MS:
            dists = []
            n_finite = 0
            for c in scoring:
                col, _ = trunc_rows(c, TRUNC_LO)
                try:
                    q = safe_q(smile_C(c, col, rn, lam, m), c, rn, K_STAR_RATIO)
                except Exception:  # noqa: BLE001 - A1.3: a raising estimator fails
                    q = float("nan")
                dist = rn.distance_to_interval(q, c.info["L"], c.info["U"])
                if math.isfinite(dist):
                    n_finite += 1
                dists.append(dist)
            score = float(np.mean(dists)) if (dists and n_finite == len(dists)) else float("inf")
            grid_rows.append({"lam": lam, "m": m, "n_scoring_dates": len(scoring), "n_finite": n_finite,
                              "mean_train_dist_C": score,
                              "train_coverage_C": (float(np.mean([x == 0.0 for x in dists])) if dists else None)})
    best = min(r["mean_train_dist_C"] for r in grid_rows)
    cands = [r for r in grid_rows if r["mean_train_dist_C"] <= best + TIE_TOL]
    pick = max(cands, key=lambda r: (r["lam"], r["m"]))
    for r in grid_rows:
        r["selected"] = (r["lam"] == pick["lam"] and r["m"] == pick["m"])
    return (pick["lam"], pick["m"]), grid_rows


def block_bootstrap(blocks: dict[str, list[float]], seed: int) -> dict[str, Any]:
    names = list(TEST_BLOCKS)
    rng = np.random.default_rng(seed)
    stats = []
    dropped = 0
    for _ in range(B_BOOT):
        idx = rng.integers(0, len(names), size=len(names))
        vals = [v for i in idx for v in blocks.get(names[i], [])]
        if not vals:
            dropped += 1
            continue
        stats.append(float(np.mean(vals)))
    if not stats:
        return {"B": B_BOOT, "seed": seed, "n_valid_draws": 0, "n_dropped_empty": dropped,
                "ci95": [None, None]}
    lo, hi = np.quantile(np.asarray(stats), [0.025, 0.975])
    return {"B": B_BOOT, "seed": seed, "n_valid_draws": len(stats), "n_dropped_empty": dropped,
            "ci95": [float(lo), float(hi)]}


def sign_counts(blocks: dict[str, list[float]]) -> dict[str, int]:
    out = {"below_0": 0, "at_0": 0, "above_0": 0, "empty": 0}
    for b in TEST_BLOCKS:
        v = blocks.get(b, [])
        if not v:
            out["empty"] += 1
            continue
        mu = float(np.mean(v))
        if mu < -TIE_TOL:
            out["below_0"] += 1
        elif mu > TIE_TOL:
            out["above_0"] += 1
        else:
            out["at_0"] += 1
    return out


def stage_compare(args: argparse.Namespace, inputs: list, outputs: list) -> None:
    data_root = Path(args.data_root)
    rn = load_module()
    sk = load_incumbent()
    sofr_df = pd.read_parquet(check_input(data_root, SOFR_REL, SOFR_SHA, inputs))
    sofr = sofr_df["sofr"].astype("float64").dropna().sort_index()
    sofr.index = pd.to_datetime(sofr.index)

    ctxs: list[DateCtx] = []
    for d, sha in CHAIN_SHA.items():
        chain = spy_rows(check_input(data_root, f"polygon_gex/chains/{d}.parquet", sha, inputs))
        ctx = DateCtx(d)
        prepare(ctx, chain, sofr, rn, sk)
        if ctx.basis is not None:
            n_left, n_right = truth_support(ctx)
            b = truth_bounds(ctx, rn, K_STAR_RATIO, 1.0)
            ctx.info.update({"truth_n_left": n_left, "truth_n_right": n_right})
            if b is not None:
                ctx.info.update({"L": b["L"], "U": b["U"], "consistent": b["consistent"],
                                 "relative_width": b["relative_width"], "width": b["width"]})
            support_ok = n_left >= 2 and n_right >= 2
            if not support_ok:
                ctx.reasons.append("truth_support")
            elif b is None or not b["consistent"]:
                ctx.reasons.append("arbitrage_inconsistent")
            ctx.info["truth_ok"] = bool(support_ok and b is not None and b["consistent"])
            col, rawsel = trunc_rows(ctx, TRUNC_LO)
            ok, n_put, n_call = trunc_support_ok(col)
            ctx.info.update({"trunc_n": int(len(col)), "trunc_n_put": n_put, "trunc_n_call": n_call, "trunc_ok": ok})
            if not ok:
                ctx.reasons.append("truncated_support")
        ctxs.append(ctx)

    train = [c for c in ctxs if c.split == "TRAIN"]
    test = [c for c in ctxs if c.split == "TEST"]
    (lam_sel, m_sel), grid_rows = select_config(train, rn)

    # Estimators at the selected configuration (every date with a basis).
    for c in ctxs:
        if c.basis is None:
            continue
        col, rawsel = trunc_rows(c, TRUNC_LO)
        sm_c = None
        if len(col) >= 1:
            try:
                sm_c = smile_C(c, col, rn, lam_sel, m_sel)
            except Exception:  # noqa: BLE001 - A1.3: a raising estimator fails
                sm_c = None
        try:
            b1, b0, meta = smiles_B(c, rawsel, rn, sk) if len(rawsel) else (None, None, {"b1_put": None, "b1_call": None})
        except Exception:  # noqa: BLE001 - A1.3: a raising estimator fails
            b1, b0, meta = None, None, {"b1_put": None, "b1_call": None}
        q = {"C": safe_q(sm_c, c, rn, K_STAR_RATIO), "B1": safe_q(b1, c, rn, K_STAR_RATIO),
             "B0": safe_q(b0, c, rn, K_STAR_RATIO)}
        c.info.update({f"q_{e}": v for e, v in q.items()})
        c.info["b1_put_strike"] = (meta["b1_put"] or {}).get("strike")
        c.info["b1_put_iv"] = (meta["b1_put"] or {}).get("iv")
        c.info["b1_put_method"] = (meta["b1_put"] or {}).get("selection_method")
        c.info["b1_call_strike"] = (meta["b1_call"] or {}).get("strike")
        c.info["b1_call_iv"] = (meta["b1_call"] or {}).get("iv")
        c.info["b1_call_method"] = (meta["b1_call"] or {}).get("selection_method")
        for e, v in q.items():
            if not math.isfinite(v):
                c.reasons.append(f"estimator_failure_{e}")
        if "L" in c.info:
            for e, v in q.items():
                c.info[f"dist_{e}"] = rn.distance_to_interval(v, c.info["L"], c.info["U"])
        if sm_c is not None:
            try:
                dens = rn.density_from_smile(sm_c, c.basis, N_NODES)
                c.info.update({"C_total_mass": dens.total_mass, "C_negative_mass_after_repair": dens.negative_mass,
                               "C_raw_negative_mass": dens.raw_negative_mass, "C_forward_ok": dens.forward_ok,
                               "C_forward_ok_raw": dens.forward_ok_raw, "C_max_repair_change": dens.max_repair_change,
                               "C_k_star_extrapolated": bool(sm_c.extrapolated([math.log(K_STAR_RATIO)])[0])})
            except Exception as exc:  # noqa: BLE001 - diagnostic only, recorded
                c.info["C_density_error"] = str(exc)[:200]
        c._smiles = (sm_c, b1, b0)  # type: ignore[attr-defined]

    for c in ctxs:
        c.info["supported"] = not c.reasons
        c.info["attrition_reasons"] = ";".join(c.reasons)
        c.info["primary_reason"] = c.reasons[0] if c.reasons else ""

    sup = [c for c in test if c.info["supported"]]
    blocks: dict[str, list[float]] = {}
    blocks_b0: dict[str, list[float]] = {}
    for c in sup:
        blocks.setdefault(c.block, []).append(c.info["dist_C"] - c.info["dist_B1"])
        blocks_b0.setdefault(c.block, []).append(c.info["dist_C"] - c.info["dist_B0"])
    diffs = [c.info["dist_C"] - c.info["dist_B1"] for c in sup]
    n_sup = len(sup)
    mean_c = float(np.mean([c.info["dist_C"] for c in sup])) if sup else float("nan")
    mean_b1 = float(np.mean([c.info["dist_B1"] for c in sup])) if sup else float("nan")
    mean_b0 = float(np.mean([c.info["dist_B0"] for c in sup])) if sup else float("nan")
    delta = float(np.mean(diffs)) if diffs else float("nan")
    boot = block_bootstrap(blocks, SEED)
    boot_b0 = block_bootstrap(blocks_b0, SEED)
    ci_hi = boot["ci95"][1]
    bar1 = bool(ci_hi is not None and ci_hi < 0)
    bar2 = bool(sup and mean_c <= EFFECT_RATIO * mean_b1)
    bar3 = bool(sup and (mean_b1 - mean_c) >= EFFECT_ABS)
    coverage_c = float(np.mean([c.info["dist_C"] == 0.0 for c in sup])) if sup else float("nan")
    med_rel_w = float(np.median([c.info["relative_width"] for c in sup])) if sup else float("nan")
    attrition = 1.0 - n_sup / N_TEST_DATES
    fal = {
        "coverage_C": coverage_c,
        "coverage_below_80pct": bool(not (coverage_c >= COVERAGE_MIN)),
        "median_relative_width": med_rel_w,
        "median_relative_width_above_0p5": bool(not (med_rel_w <= MEDIAN_REL_WIDTH_MAX)),
        "attrition_fraction": attrition,
        "attrition_above_50pct": bool(attrition > ATTRITION_MAX),
    }
    fal["fires"] = bool(fal["coverage_below_80pct"] or fal["median_relative_width_above_0p5"]
                        or fal["attrition_above_50pct"])

    def attr_table(cs: list[DateCtx]) -> dict[str, Any]:
        prim: dict[str, int] = {}
        anyr: dict[str, int] = {}
        for c in cs:
            if c.reasons:
                prim[c.reasons[0]] = prim.get(c.reasons[0], 0) + 1
            for r in set(c.reasons):
                anyr[r] = anyr.get(r, 0) + 1
        return {"n_dates": len(cs), "n_supported": sum(1 for c in cs if c.info["supported"]),
                "primary_reason_counts": prim, "any_reason_counts": anyr}

    summary = {
        "stage": "compare",
        "label": rn.PROXY_LABEL,
        "measure": rn.MEASURE,
        "measure_label": rn.MEASURE_LABEL,
        "verdict": rn.VERDICT,
        "verdict_basis": "PREREG section 0: missing M1-M4; the proxy result cannot change the verdict",
        "missing_inputs": list(rn.MISSING_INPUTS),
        "selected_config": {"lam": lam_sel, "m": m_sel, "selected_on": "TRAIN only (W25-W29)"},
        "honest_n": {
            "test_blocks": len(TEST_BLOCKS),
            "test_dates": len(test),
            "supported_test_dates": n_sup,
            "supported_test_blocks": sum(1 for b in TEST_BLOCKS if blocks.get(b)),
            "distinct_test_expiries_all": sorted({c.expiry for c in test if c.expiry}),
            "distinct_test_expiries_supported": sorted({c.expiry for c in sup}),
            "train_scoring_dates": int(sum(1 for c in train if c.info.get("truth_ok") and c.info.get("trunc_ok"))),
        },
        "primary": {
            "hypothesis": "H1: C extrapolates the RN left tail at K*=0.90F closer to [L,U] than incumbent skew B1",
            "delta_mean_dist_C_minus_B1": delta,
            "mean_dist_C": mean_c,
            "mean_dist_B1": mean_b1,
            "bootstrap": boot,
            "block_sign_counts": sign_counts(blocks),
            "effect_bar": {"ci_upper_below_0": bar1, "mean_C_le_0p75_mean_B1": bar2,
                           "abs_improvement_ge_0p002": bar3},
            "h1_supported_on_proxy": bool(bar1 and bar2 and bar3),
        },
        "descriptive_C_vs_B0": {
            "delta_mean_dist_C_minus_B0": float(np.mean([c.info["dist_C"] - c.info["dist_B0"] for c in sup])) if sup else float("nan"),
            "mean_dist_B0": mean_b0,
            "bootstrap": boot_b0,
            "block_sign_counts": sign_counts(blocks_b0),
        },
        "falsifier": fal,
        "output_restriction": ("PRICE_BOUNDS_ONLY (falsifier fired)" if fal["fires"]
                               else "falsifier did not fire; verdict still INSUFFICIENT_DATA"),
        "attrition": {"TRAIN": attr_table(train), "TEST": attr_table(test)},
        "coverage_B1": float(np.mean([c.info["dist_B1"] == 0.0 for c in sup])) if sup else float("nan"),
        "coverage_B0": float(np.mean([c.info["dist_B0"] == 0.0 for c in sup])) if sup else float("nan"),
    }

    diagnostics = run_diagnostics(ctxs, train, test, sup, rn, sk, lam_sel, m_sel, grid_rows)

    per_date = pd.DataFrame([{k: (json.dumps(jclean(v)) if isinstance(v, (dict, list)) else v)
                              for k, v in c.info.items()} for c in ctxs])
    write_csv(RESULTS / "per_date.csv", per_date, outputs)
    write_csv(RESULTS / "training_grid.csv", pd.DataFrame(grid_rows), outputs)
    write_json(RESULTS / "diagnostics.json", diagnostics, outputs)
    write_json(RESULTS / "compare_summary.json", summary, outputs)


def run_diagnostics(ctxs: list[DateCtx], train: list[DateCtx], test: list[DateCtx], sup: list[DateCtx],
                    rn: Any, sk: Any, lam: float, m: int, grid_rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"label": rn.PROXY_LABEL, "measure": rn.MEASURE,
                           "note": "Descriptive only (PREREG section 14); cannot change the verdict."}

    # 14.1 band scaling on the fixed supported TEST set.
    scaling = []
    for s in BAND_SCALES:
        rows = []
        for c in sup:
            b = truth_bounds(c, rn, K_STAR_RATIO, s)
            q = c.info["q_C"]
            rows.append({"date": c.d, "L": b["L"], "U": b["U"], "width": b["width"],
                         "relative_width": b["relative_width"], "consistent": b["consistent"],
                         "C_inside": bool(b["consistent"] and b["L"] <= q <= b["U"])})
        widths = [r["width"] for r in rows]
        rws = [r["relative_width"] for r in rows]
        scaling.append({"scale": s, "n": len(rows),
                        "median_width": float(np.median(widths)) if rows else None,
                        "median_relative_width": float(np.median(rws)) if rows else None,
                        "n_inconsistent": int(sum(not r["consistent"] for r in rows)),
                        "coverage_C": float(np.mean([r["C_inside"] for r in rows])) if rows else None,
                        "per_date": rows})
    out["14_1_band_scaling"] = scaling

    # 14.2 full-chain module report on TEST with the selected configuration.
    full = []
    for c in test:
        if c.basis is None:
            full.append({"date": c.d, "error": "no_basis"})
            continue
        F = c.basis.forward
        o = c.otm[(c.otm["K"] >= FULL_LO * F) & (c.otm["K"] <= FULL_HI * F)]
        K = o["K"].to_numpy(float)
        iv = o["iv"].to_numpy(float)
        calls = o["is_call"].to_numpy(bool)
        rec: dict[str, Any] = {"date": c.d, "n_quotes": int(K.size)}
        try:
            rep = rn.rn_tail_report(c.basis, K, iv, calls, K_STAR_RATIO, lam, m, 1.0, N_DRAWS, SEED, N_NODES)
            hw = rn.iv_half_width(np.log(K / F), 1.0)
            mid, _, _ = rn.call_equivalent_bands(c.basis, K, iv, calls, hw)
            arb = rn.static_arbitrage_report(K, mid, c.basis)
            pert = rep["perturbation_interval"]
            pert_src = "module_report"
            if pert is None:
                def fitter(kk: np.ndarray, vv: np.ndarray) -> Any:
                    return rn.fit_smile(kk, vv, c.basis.T, lam, m)
                pert = rn.perturbation_interval(c.basis, np.log(K / F), iv, hw, K_STAR_RATIO * F, fitter,
                                                N_DRAWS, SEED, N_NODES)
                pert_src = "direct_diagnostic_only (report withheld it under PRICE_BOUNDS_ONLY)"
            rec.update({
                "identification": rep["identification"],
                "identification_reasons": rep["identification_reasons"],
                "identified_bounds": rep["identified_bounds"],
                "point_estimate": rep["point_estimate"],
                "quoted_surface_arbitrage": {k: arb[k] for k in ("n_nodes", "n_butterfly_violations",
                                                                 "n_monotonicity_violations", "n_slope_floor_violations",
                                                                 "n_price_bound_violations", "negative_atom_mass",
                                                                 "max_butterfly_violation", "arbitrage_free")},
                "density": rep["density"],
                "reintegration": rep["reintegration"],
                "smile": rep["smile"],
                "perturbation_interval": pert,
                "perturbation_source": pert_src,
            })
        except Exception as exc:  # noqa: BLE001 - diagnostic only, recorded
            rec["error"] = str(exc)[:200]
        full.append(rec)
    out["14_2_full_chain_report_TEST"] = full

    # 14.3 ATM call/put iv discrepancy.
    atm = []
    for c in ctxs:
        if c.basis is None:
            continue
        F = c.basis.forward
        bt = c.both
        piv = bt.pivot_table(index="K", columns="is_call", values="iv", aggfunc="median")
        if True not in piv.columns or False not in piv.columns:
            continue
        piv = piv.dropna()
        if piv.empty:
            continue
        piv = piv.assign(_dist=np.abs(piv.index.to_numpy(float) - F)).sort_values("_dist").head(3)
        disc = np.abs(piv[True].to_numpy(float) - piv[False].to_numpy(float))
        atm.append({"date": c.d, "split": c.split, "n_strikes": int(len(piv)),
                    "median_abs_iv_call_minus_put": float(np.median(disc))})
    out["14_3_atm_call_put_iv_gap"] = {
        "per_date": atm,
        "median_by_split": {s: (float(np.median([a["median_abs_iv_call_minus_put"] for a in atm if a["split"] == s]))
                                if any(a["split"] == s for a in atm) else None) for s in ("TRAIN", "TEST")},
    }

    # 14.4 TRAIN-only sensitivity: grid + truncation cuts.
    cuts = []
    for cut in CUTS:
        rows = []
        for c in train:
            if c.basis is None or not c.info.get("truth_ok"):
                continue
            col, rawsel = trunc_rows(c, cut)
            ok, _, _ = trunc_support_ok(col)
            if not ok:
                continue
            try:
                sm_c = smile_C(c, col, rn, lam, m)
                b1, b0, _ = smiles_B(c, rawsel, rn, sk)
            except Exception:  # noqa: BLE001 - A1.3: a raising estimator fails
                continue
            qs = [safe_q(x, c, rn, K_STAR_RATIO) for x in (sm_c, b1, b0)]
            if not all(math.isfinite(v) for v in qs):
                continue
            rows.append([rn.distance_to_interval(v, c.info["L"], c.info["U"]) for v in qs])
        arr = np.asarray(rows, dtype=float) if rows else np.zeros((0, 3))
        cuts.append({"cut": cut, "n_train_dates": int(arr.shape[0]),
                     "mean_dist_C": float(arr[:, 0].mean()) if rows else None,
                     "mean_dist_B1": float(arr[:, 1].mean()) if rows else None,
                     "mean_dist_B0": float(arr[:, 2].mean()) if rows else None})
    out["14_4_train_sensitivity"] = {"grid": grid_rows, "cuts_selected_config": cuts}

    # 14.5 secondary strike 0.95F on the supported TEST set.
    sec = []
    for c in sup:
        b = truth_bounds(c, rn, K_SECONDARY_RATIO, 1.0)
        sm_c, b1, b0 = c._smiles  # type: ignore[attr-defined]
        qs = {"C": safe_q(sm_c, c, rn, K_SECONDARY_RATIO), "B1": safe_q(b1, c, rn, K_SECONDARY_RATIO),
              "B0": safe_q(b0, c, rn, K_SECONDARY_RATIO)}
        sec.append({"date": c.d, "L": b["L"], "U": b["U"], "consistent": b["consistent"],
                    "relative_width": b["relative_width"],
                    **{f"q_{e}": v for e, v in qs.items()},
                    **{f"dist_{e}": rn.distance_to_interval(v, b["L"], b["U"]) for e, v in qs.items()}})
    out["14_5_secondary_0p95F_TEST"] = {
        "per_date": sec,
        "mean_dist": {e: (float(np.mean([r[f"dist_{e}"] for r in sec])) if sec else None) for e in ("C", "B1", "B0")},
        "note": "Estimators see quotes at this strike; not an extrapolation test.",
    }
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", required=True, choices=("absence", "baseline", "baseline_census", "compare"))
    ap.add_argument("--utc-stamp", required=True, help="from `date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ`")
    ap.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    default_scan = ROOT.parent / "_base"
    ap.add_argument("--scan-root", default=str(default_scan if default_scan.is_dir() else ROOT))
    args = ap.parse_args(argv)

    record: dict[str, Any] = {
        "utc_stamp": args.utc_stamp,
        "stage": args.stage,
        "command": " ".join(shlex.quote(a) for a in [sys.executable] + (sys.argv if argv is None else ["evaluate.py", *argv])),
        "thread_env": " ".join(f"{k}={os.environ.get(k, '')}" for k in
                               ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")),
        "inputs": [],
        "outputs": [],
    }
    prereg_sha = sha256_file(PREREG)
    record["prereg_sha256"] = prereg_sha
    record["freeze_sha256"] = frozen_hash()
    record["amendment_sha256"] = sha256_file(AMEND) if AMEND.exists() else "absent"
    record["evaluate_sha256"] = sha256_file(Path(__file__).resolve())
    record["module_sha256"] = sha256_file(ROOT / MODULE_REL) if (ROOT / MODULE_REL).exists() else "absent"
    record["incumbent_sha256"] = sha256_file(ROOT / INCUMBENT_REL) if (ROOT / INCUMBENT_REL).exists() else "absent"
    if prereg_sha != record["freeze_sha256"]:
        record["exit_code"] = 2
        record["note"] = "REFUSED: sha256(PREREG.md) != FREEZE.log PREREG_SHA256"
        append_run(record)
        print(record["note"], file=sys.stderr)
        return 2

    try:
        check_blocks()
        if args.stage == "compare":
            prior = [r for r in previous_runs() if r.get("stage") == "compare"]
            if any(r.get("exit_code") == "0" for r in prior):
                raise StopRuleRefusal("compare already completed (PREREG section 13: runs once)")
            if sum(1 for r in prior if r.get("exit_code") == "1") >= 3:
                raise StopRuleRefusal("compare crashed 3 times; no further reruns (PREREG section 13)")
        RESULTS.mkdir(parents=True, exist_ok=True)
        stage = {"absence": stage_absence, "baseline": stage_baseline, "baseline_census": stage_baseline_census,
                 "compare": stage_compare}[args.stage]
        stage(args, record["inputs"], record["outputs"])
    except StopRuleRefusal as exc:
        record["exit_code"] = 4
        record["note"] = f"REFUSED: {exc}"
        append_run(record)
        print(record["note"], file=sys.stderr)
        return 4
    except InputHashError as exc:
        record["exit_code"] = 3
        record["note"] = f"REFUSED: {exc}"
        append_run(record)
        print(record["note"], file=sys.stderr)
        return 3
    except Exception as exc:  # noqa: BLE001 — every crash is logged (stop rule)
        record["exit_code"] = 1
        tb = traceback.extract_tb(exc.__traceback__)
        where = f"{Path(tb[-1].filename).name}:{tb[-1].lineno}" if tb else "?"
        record["note"] = f"CRASH {type(exc).__name__} at {where}: {str(exc)[:300]}"
        append_run(record)
        traceback.print_exc()
        return 1
    record["exit_code"] = 0
    append_run(record)
    for rel, sha in record["outputs"]:
        print(f"{rel} {sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
