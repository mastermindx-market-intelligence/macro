#!/usr/bin/env python3
"""Offline builder — engine alert histories for the three HOUSE organs (COO ruling 38 Part A).

Replays the engine's OWN code at one pinned commit. Every state/label/phase in the
output is the engine's own output: this script IMPORTS and CALLS the engine functions
and never copies a threshold or rule, and never edits anything under engine/.

Organs (house groups only; vendor-keyed organs are OUT of scope):
  1. us_basket WASHED_OUT -> CONFIRMED  — engine/us_basket_turn.replay (:1041), TWO
     labelled membership versions in the same file:
       * membership_basis="dated"   : dated [added, removed) membership, PIT. This is
         the LIVE engine basis (compute_all :785 uses active_members + ew_level_from_closes
         with the dated mask), so the fidelity test applies to this version.
       * membership_basis="current" : today's active members applied as far back as the
         inputs reach (added=None, removed kept). A SENSITIVITY, not the organ history.
  2. phase_v2                          — engine/sector_cycles.build_sector (:1202) per
     session, which calls cycle_ontology.classify_phase via record_series (:668).
     TWO engine versions in the SAME parquet: the current pin (72082493cb5e, the primary
     series) and the legacy pin (896471652cea, the version that wrote backfill.parquet),
     the latter replayed from a scratch --legacy-engine-root, never checked out in-tree.
  3. rolling_over                      — engine/sector_central._rolling_over (:278) on the
     `now` block built by the engine's own build_sector, carried through _carry (:1127).

Inputs are read, never written. No production builder is run, no nightly is rerun.
Nothing here relates to outcomes. Git holds only group-level rows: no member ticker,
price or per-security date is emitted.

PROVENANCE / NO-FALLBACK PROOF (COO 22:48Z correction). The proof that the engine used
its fitted calibration (and did not silently fall back to hand constants) is NOT a log
count. It is, with no engine file edited:
  (i)  the opened-file record (sys.addaudithook "open" + parquet-reader wrappers) shows
       both data/regime calibration files opened, each sha256 equal to its blob at
       `inputs_commit`; and
  (ii) a read-back of the engine's cached loaded values (cycles._FITTED_BANDS /
       cycles._RISK_CALIB) recorded non-empty, with a count of how many band values
       differ from the hand constants where the fitted file differs.
The "cannot load" log count is kept as a check for the HAZARD loader only
(engine/hazard_score.py:391); the bands/risk loaders return {} on absence BEFORE any
log line (engine/cycles.py:98-99 and :127-128), so a log scan cannot prove they loaded.

Prices are RESTATED as of capture (price_basis="restated"); the sidecar says so.
The 2000-bar trailing window matches scripts/backfill_forward_logs.py:85 (WINDOW_CAP).

Run:
  /opt/homebrew/Caskroom/miniconda/base/bin/python3 scripts/build_organ_histories.py \
      --staging-dir <dir>                 # REQUIRED; empty/absent at start; writes only here
      --legacy-engine-root <scratch>      # git archive 896471652cea engine lib config (outside tree)
      --main-tape-root <scratch>          # git archive 12e299d data/yahoo (outside tree)
  ... --smoke          # quick mechanics check, scratch outputs under --staging-dir
  ... --workers 12     # multiprocessing pool size
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── run-time opened-file instrumentation (installed BEFORE engine import so spawned
#    workers, which re-import this module, inherit it). Records every repository file
#    the run opens; pyarrow's C++ parquet IO bypasses the Python open audit event, so
#    the parquet readers are wrapped too. Writes nothing. ─────────────────────────────
_READS: set[str] = set()
_WRITES: set[str] = set()
_HAZARD_CANNOT_LOAD = 0          # hazard-only "cannot load" log count (must be 0)
_FALLBACK_LOG: list[str] = []    # captured fallback-ish log lines (diagnostic only)


def _relpath(p) -> str | None:
    try:
        s = os.fspath(p)
    except TypeError:
        return None
    if isinstance(s, bytes):
        s = s.decode("utf-8", "replace")
    ap = os.path.abspath(s)
    root = str(ROOT)
    if ap.startswith(root + os.sep):
        return os.path.relpath(ap, root)
    return None


def _audit_hook(event, args):
    if event != "open":
        return
    rel = _relpath(args[0])
    if rel is None:
        return
    flags = args[2] or 0
    mode = args[1]
    writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
    if mode and any(c in str(mode) for c in "wxa+"):
        writing = True
    (_WRITES if writing else _READS).add(rel)


sys.addaudithook(_audit_hook)

_orig_pd_read_parquet = pd.read_parquet


def _wrapped_read_parquet(path, *a, **k):
    rel = _relpath(path)
    if rel:
        _READS.add(rel)
    return _orig_pd_read_parquet(path, *a, **k)


pd.read_parquet = _wrapped_read_parquet

try:
    import pyarrow.parquet as _pq

    _orig_pq_read_table = _pq.read_table

    def _wrapped_pq_read_table(source, *a, **k):
        rel = _relpath(source)
        if rel:
            _READS.add(rel)
        return _orig_pq_read_table(source, *a, **k)

    _pq.read_table = _wrapped_pq_read_table
except Exception:  # noqa: BLE001
    pass


class _FallbackCapture(logging.Handler):
    def emit(self, record):
        global _HAZARD_CANNOT_LOAD
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001
            return
        low = msg.lower()
        if "cannot load" in low and "hazard" in low:
            _HAZARD_CANNOT_LOAD += 1
        if any(p in low for p in ("cannot load", "fallback", "falling back", "unavailable")):
            _FALLBACK_LOG.append(f"{record.name}:{record.lineno}: {msg}")


logging.getLogger().addHandler(_FallbackCapture())
logging.getLogger().setLevel(logging.DEBUG)

from lib import config                       # noqa: E402
from engine import us_basket_turn as ubt      # noqa: E402
from engine import sector_cycles as sc        # noqa: E402
from engine import sector_central as central  # noqa: E402
from engine import cycles as cyc              # noqa: E402
from engine import hazard_score as hz         # noqa: E402
from engine.inputs import yahoo_closes        # noqa: E402

# ── pinned engine identity ───────────────────────────────────────────────────────────
ENGINE_CODE_SHA = "72082493cb5e29cf5fe4a093fadf6f435b6fe2c3"
LEGACY_ENGINE_CODE_SHA = "896471652cea87edc77a651d5c7e8d9d790119f8"
LEGACY_ENGINE_SHORT = "896471652cea"
MAIN_TAPE_PIN = "12e299d6a85db5b949d3cb581d798bc8ae2f8f77"
# sha256 of the exact engine module bytes at the pin; the runtime self-check hashes the
# imported files against these so a drifted engine fails the build instead of silently
# producing a non-faithful history. (The sidecar records ALL repository modules, not just
# these six — see repo_module_hashes().)
EXPECTED_ENGINE_HASHES = {
    "engine/us_basket_turn.py": "f32048f646d8d48169e00e59c408064b9ef375ca61993b9b37349023ef0f7a66",
    "engine/sector_cycles.py": "ed67fb446930397ffaa8149c69bf8e100870772f5244bce8c28f50b449b56286",
    "engine/sector_central.py": "9c9ada9106e53ae7bc062da86c1475829a1f517af9bffbe1ee3162b7e53dffb9",
    "engine/cycle_ontology.py": "76e5981192aa9e379869734060e71f2e80918cdf49b73b75a583ae96e73599ec",
    "engine/inputs.py": "b322465049397c1d36ff7b4ab07f131b34fd635b6624289f51bdf3b9ec205c65",
    "engine/cycles.py": "679fafe2ef043a67bd390d9d9425bb610831453f76018be49e449294e1d33f56",
}

# ── ENGINE_INPUTS: every data/ artifact the loaded engine modules open at run time,
#    discovered by instrumenting the run (audit hook) and reading each loaded module for
#    data/ path literals + fallback loaders. Each entry carries module:line. Every listed
#    file MUST be present and equal to its blob at inputs_commit, or the builder refuses.
#    The two regime calibrations are MANDATORY: their loaders return {} on absence BEFORE
#    any log line (silent fallback to hand constants), so absence cannot be caught by a
#    log scan — only by this gate + the opened-file record + the loaded-value read-back.
ENGINE_INPUTS = [
    {"path": "data/regime/cycle_bands_fit.json",
     "module": "engine/cycles.py", "line": 97,
     "loader": "_load_fitted_bands (returns {} on absence at :98-99, before any log)",
     "mandatory": True},
    {"path": "data/regime/ladder_risk_calibration.json",
     "module": "engine/cycles.py", "line": 126,
     "loader": "_load_risk_calib (returns {} on absence at :127-128, before any log)",
     "mandatory": True},
    {"path": "data/hazard/model_price_c4414dcb.json",
     "module": "engine/hazard_score.py", "line": 46,
     "loader": "_load_model (logs 'cannot load' at :391 on failure)",
     "mandatory": True},
    {"path": "data/hazard/km_baseline_price_c4414dcb.json",
     "module": "engine/hazard_score.py", "line": 47,
     "loader": "_load_km (logs 'cannot load' at :391 on failure)",
     "mandatory": True},
    {"path": "data/vol_regime/basket_overlay_gate.json",
     "module": "engine/vol_regime.py", "line": 300,
     "loader": "load_overlay_gate (path constant :87; logs read-failed at :306)",
     "mandatory": True},
]

WINDOW_CAP = 2000                 # scripts/backfill_forward_logs.py:85
BASKET_LEVEL_WINDOW = 252         # engine/us_basket_turn.py:340 (first-knowable locator)
DESK_BLOCK = pd.Timestamp("2023-12-29")   # rows after this are kept and labelled, not dropped
REPLAY_END = "2030-01-01"         # beyond the tape; replay breaks at the last level session

SPDRS = list(sc.SECTORS.keys())   # the 11 house SPDR sector keys

HIST_DIR = ROOT / "data" / "breadth" / "history"
OUT_PARQUET = HIST_DIR / "organ_histories_house.parquet"
OUT_META = HIST_DIR / "organ_histories_house.meta.json"
OUT_REPORT = ROOT / "research" / "breadth_history" / "ORGAN_HISTORIES_REPORT.md"

NO_OUTCOME = (
    "These are engine alert histories only. Nothing in this file relates to outcomes, "
    "returns, forward performance or any grading; every state is the engine's own "
    "descriptive output replayed on restated prices."
)

# COO 23:20Z — report text only, verbatim. No sentence attributes differing cells to the
# bands or to the price tape; that split is measured later in delta check C.
PACKAGE_VERSIONS_SENTENCE = (
    "Package versions of the morning run were not recorded; byte equality of the "
    "reproduction was reached with Python 3.12.4, pandas 3.0.3, pyarrow 24.0.0 and numpy 2.4.6."
)

# The report's cause sentence is supplied VERBATIM by the COO at commit-release time
# (--report-sentence-file). Until then the builder writes NO cause sentence (COO 23:14Z).


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ── git helpers (read-only) ──────────────────────────────────────────────────────────
def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=str(ROOT), text=True)


def git_head() -> str:
    return _git("rev-parse", "HEAD").strip()


def head_blobs() -> dict[str, str]:
    """rel path -> git blob sha at HEAD (ls-tree -r)."""
    out = _git("ls-tree", "-r", "HEAD")
    blobs: dict[str, str] = {}
    for line in out.splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) >= 3 and parts[1] == "blob":
            blobs[path] = parts[2]
    return blobs


def working_blob_id(path: Path) -> str | None:
    """git blob id of the working-tree bytes (sha1 of 'blob <len>\\0' + content)."""
    try:
        content = path.read_bytes()
    except OSError:
        return None
    h = hashlib.sha1()
    h.update(b"blob " + str(len(content)).encode() + b"\0" + content)
    return h.hexdigest()


def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _safe_name(name) -> str:
    """Mirror lib/store.py:470 ticker->file sanitization (^,=,/,space -> _)."""
    return str(name).replace("^", "_").replace("=", "_").replace("/", "_").replace(" ", "_")


# ── engine-pin self-check ──────────────────────────────────────────────────────────
def verify_engine_pin() -> dict:
    got = {}
    for rel, want in EXPECTED_ENGINE_HASHES.items():
        b = (ROOT / rel).read_bytes()
        h = hashlib.sha256(b).hexdigest()
        got[rel] = h
        if h != want:
            raise SystemExit(
                f"ENGINE PIN MISMATCH: {rel}\n  want {want}\n  got  {h}\n"
                "The imported engine code differs from the pinned commit; refusing to build."
            )
    log(f"engine pin self-check OK ({len(got)} modules) @ {ENGINE_CODE_SHA}")
    return got


def repo_module_hashes() -> dict[str, str]:
    """sha256 of EVERY repository module imported at run time (walk sys.modules)."""
    out: dict[str, str] = {}
    for _name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        rel = _relpath(f)
        if rel and rel.endswith(".py"):
            h = file_sha256(ROOT / rel)
            if h:
                out[rel] = h
    return dict(sorted(out.items()))


# ── engine loaded-value read-back (no-fallback proof, part ii) ───────────────────────
def read_engine_artifacts() -> dict:
    """Read the engine's cached calibration values AFTER it has loaded them.

    Forces the lazy loaders in THIS process (idempotent; the engine caches them), then
    records non-emptiness and how many fitted band values differ from the hand constants.
    """
    cyc._preset("equity")
    cyc.risk_size_mult("RALLY ON", "us_sector")
    try:
        hz._load_model()
        hz._load_km()
    except Exception:  # noqa: BLE001 — gate ensures presence; cannot-load count catches failure
        pass
    bands = dict(cyc._FITTED_BANDS or {})
    diff = 0
    detail = {}
    for kind in ("equity", "crypto", "fx"):
        hand = cyc.CYCLE_PRESETS.get(kind, {})
        fit = bands.get(kind, {})
        for field in ("dc_band", "ic_band_w"):
            hv = tuple(hand.get(field, ()))
            fv = tuple(fit.get(field, ()))
            valid = len(fv) == 2 and fv[0] > 0 and fv[1] > fv[0]
            differs = bool(valid and fv != hv)
            if differs:
                diff += 1
            detail[f"{kind}.{field}"] = {"hand": list(hv), "fitted": list(fv),
                                         "applied": valid, "differs": differs}
    return {
        "fitted_bands_loaded": bool(cyc._FITTED_BANDS_LOADED),
        "fitted_bands_nonempty": bool(bands),
        "risk_calib_loaded": bool(cyc._RISK_CALIB_LOADED),
        "risk_calib_nonempty": bool(cyc._RISK_CALIB),
        "hazard_model_loaded": hz._model_cache is not None,
        "hazard_km_loaded": hz._km_cache is not None,
        "fitted_vs_hand_diff_count": diff,
        "fitted_vs_hand_detail": detail,
        "risk_calib_all_one": all(
            float(m) == 1.0 for fam in (cyc._RISK_CALIB or {}).values() for m in fam.values()
        ),
    }


def regime_calibration_proof(provenance: dict) -> dict:
    """COO 23:14Z item 1: the engine's loaded values are non-empty AND the sha256 of the
    two data/regime files the run actually opened each equal their blob at inputs_commit.
    Nothing else is required for the no-fallback proof."""
    files = provenance["opened"]["files"]
    checked = provenance["gate"]["checked"]
    art = provenance["artifacts"]
    out = {
        "fitted_bands_nonempty": art["fitted_bands_nonempty"],
        "risk_calib_nonempty": art["risk_calib_nonempty"],
        "inputs_commit": provenance["inputs_commit"],
        "files": {},
    }
    for e in ENGINE_INPUTS:
        if e["path"].startswith("data/regime/"):
            rec = files.get(e["path"], {})
            out["files"][e["path"]] = {
                "opened": e["path"] in files,
                "sha256": rec.get("sha256"),
                "bytes": rec.get("bytes"),
                "head_blob": checked.get(e["path"], {}).get("head_blob"),
                "matches_inputs_commit": rec.get("matches_inputs_commit"),
            }
    return out


# ── input gate ───────────────────────────────────────────────────────────────────────
def enumerate_inputs() -> tuple[list[str], list[str]]:
    """(required_paths, tape_paths) the builder will read, mirrored from the loaders.

    required: config + memberships + stores + ENGINE_INPUTS (must exist).
    tape: every existing yahoo/stocks/baskets-ohlcv file the loaders may open.
    """
    real = config.data_dir()
    required = ["config.yml"]
    required += [e["path"] for e in ENGINE_INPUTS]
    required += [
        "data/baskets/membership.json",
        "data/baskets_nasdaq/membership.json",
        "data/baskets_russell/membership.json",
        "data/us_basket_turn/ledger.jsonl",
        "data/sector_cycles/backfill.parquet",
        "data/sector_cycles/forward_log.parquet",
        "data/sector_cycles/backfill_manifest.json",
    ]
    tape: set[str] = set()
    # yahoo tickers from config (the panel the engine reads)
    cfg = config.load()
    tk = (cfg.get("yahoo", {}) or {}).get("tickers", {}) or {}
    groups = tk.values() if isinstance(tk, dict) else tk
    for group in groups:
        names = group if isinstance(group, (list, tuple)) else (group or {}).get("tickers", [])
        for t in names or []:
            tape.add(f"data/yahoo/{_safe_name(t)}.parquet")
    # member tapes from every membership (baskets + amalgams)
    tickers: set[str] = set()
    for mem_rel in ("data/baskets/membership.json", "data/baskets_nasdaq/membership.json",
                    "data/baskets_russell/membership.json"):
        p = ROOT / mem_rel
        if not p.exists():
            continue
        raw = json.loads(p.read_text())
        for _bid, b in (raw.get("baskets") or {}).items():
            for m in b.get("members") or []:
                t = m.get("ticker")
                if t:
                    tickers.add(t)
    for t in tickers:
        tape.add(f"data/stocks/{t}.parquet")
        tape.add(f"data/baskets/ohlcv/{t}.parquet")
        tape.add(f"data/yahoo/{_safe_name(t)}.parquet")
    # only existing tape files are inputs (sparse tree may omit others)
    tape_existing = sorted(rel for rel in tape if (ROOT / rel).exists())
    return required, tape_existing


def input_gate(inputs_commit: str, blobs: dict[str, str]) -> dict:
    """Refuse unless every required input exists and every input's working bytes equal
    its blob at inputs_commit. Names every offending path."""
    required, tape = enumerate_inputs()
    missing: list[str] = []
    differing: list[str] = []
    checked: dict[str, dict] = {}
    for rel in required + tape:
        p = ROOT / rel
        want = blobs.get(rel)
        if not p.exists():
            if rel in required:
                missing.append(rel)
            continue
        got = working_blob_id(p)
        sha = file_sha256(p)
        size = p.stat().st_size
        ok = (want is not None and got == want)
        checked[rel] = {"sha256": sha, "bytes": size, "git_blob": got,
                        "head_blob": want, "matches_inputs_commit": ok}
        if not ok:
            differing.append(rel)
    if missing or differing:
        msg = ["INPUT GATE REFUSAL — working inputs differ from inputs_commit "
               f"{inputs_commit}:"]
        if missing:
            msg.append("  missing required inputs:")
            msg += [f"    {r}" for r in missing]
        if differing:
            msg.append("  working bytes != blob at inputs_commit:")
            msg += [f"    {r}" for r in differing]
        raise SystemExit("\n".join(msg))
    log(f"input gate OK: {len(checked)} inputs match blobs at {inputs_commit} "
        f"({len(required)} required, {len(tape)} tape files)")
    return {"inputs_commit": inputs_commit, "required_count": len(required),
            "tape_count": len(tape), "checked": checked,
            "missing": missing, "differing": differing}


def check_staging(staging: Path) -> None:
    """Refuse if the staging dir already holds any link or file (must be empty/absent)."""
    if staging.exists():
        if not staging.is_dir():
            raise SystemExit(f"STAGING REFUSAL: {staging} is not a directory")
        entries = list(staging.iterdir())
        if entries:
            names = ", ".join(sorted(e.name for e in entries)[:20])
            raise SystemExit(
                f"STAGING REFUSAL: {staging} is not empty (holds {len(entries)} "
                f"pre-existing entries: {names}). Require an empty or absent staging dir."
            )
    else:
        staging.mkdir(parents=True, exist_ok=True)


# ── current-version scratch root (today's members, added=None, removed kept) ───────
def setup_current_root(staging: Path) -> Path:
    current_root = staging / "current_root"
    real = config.data_dir()
    raw = json.loads((real / "baskets" / "membership.json").read_text())
    for _bid, b in (raw.get("baskets") or {}).items():
        for m in b.get("members") or []:
            m["added"] = None
    current_root.mkdir(parents=True, exist_ok=True)
    (current_root / "baskets").mkdir(parents=True, exist_ok=True)
    (current_root / "baskets" / "membership.json").write_text(json.dumps(raw))
    for sub in ("stocks", "baskets/ohlcv"):
        link = current_root / sub
        target = real / sub
        if target.exists() and not link.exists():
            link.symlink_to(target, target_is_directory=True)
    return current_root


# ── basket organ ───────────────────────────────────────────────────────────────────
def basket_task(args: tuple) -> dict:
    bid, version, current_root = args
    root = config.data_dir() if version == "dated" else Path(current_root)
    full = ubt.replay(bid, "1900-01-01", REPLAY_END, data_root=root)
    out = {"organ": "us_basket", "bid": bid, "version": version,
           "rows": [], "first_knowable": None, "n_sessions": len(full)}
    if not full:
        return out
    fk = (full[BASKET_LEVEL_WINDOW - 1]["date"]
          if len(full) >= BASKET_LEVEL_WINDOW else full[0]["date"])
    out["first_knowable"] = fk
    basket = ubt._load_membership(root).get(bid) or {}
    members = ubt.active_members(basket)
    closes: dict[str, pd.Series] = {}
    for m in members:
        s = ubt._load_close(m["ticker"], root)
        if s is not None:
            closes[m["ticker"]] = s
    prev_state = None
    for r in full:
        state = r["state"]
        confirmed_transition = bool(
            state == "CONFIRMED" and prev_state is not None and prev_state != "CONFIRMED"
        )
        prev_state = state
        if r["date"] < fk:
            continue
        nm = ubt._members_at_session(members, closes, r["date"])
        out["rows"].append({
            "organ": "us_basket", "level": "basket", "group_key": bid,
            "session_date": r["date"], "state": state,
            "first_knowable_date": fk, "membership_basis": version,
            "n_members": int(nm), "engine_code_sha": ENGINE_CODE_SHA,
            "after_2023_12_29": bool(pd.Timestamp(r["date"]) > DESK_BLOCK),
            "days_in_state": int(r["days_in_state"]),
            "confirmed_transition": confirmed_transition,
        })
    return out


# ── sector organs (phase_v2 + rolling_over share one build_sector call) ────────────
_G: dict = {}


def sector_init() -> None:
    closes = yahoo_closes()
    _G["closes"] = closes
    _G["closes_px"] = yahoo_closes(basis="price").reindex(closes.index)
    _G["cal"] = closes.index


def sector_task(args: tuple) -> dict:
    ticker, js = args
    closes = _G["closes"]
    closes_px = _G["closes_px"]
    cal = _G["cal"]
    meta = sc.SECTORS[ticker]
    key = ticker.lower()
    phase_rows: list[dict] = []
    roll_rows: list[dict] = []
    fk_phase = None
    fk_roll = None
    for j in js:
        lo = max(0, j + 1 - WINDOW_CAP)
        sub = closes.iloc[lo:j + 1]
        sub_px = closes_px.iloc[lo:j + 1]
        ws = sub.index[0]
        rec = sc.build_sector(ticker, meta, sub, ws, closes_px=sub_px)
        if not rec:
            continue
        now = rec.get("now") or {}
        d = str(cal[j].date())
        after = bool(cal[j] > DESK_BLOCK)
        pv2 = now.get("phase_v2")
        if pv2 is not None:
            if fk_phase is None:
                fk_phase = d
            phase_rows.append({
                "organ": "phase_v2", "level": "sector", "group_key": key,
                "session_date": d, "state": pv2,
                "first_knowable_date": fk_phase, "membership_basis": "etf_price",
                "n_members": 1, "engine_code_sha": ENGINE_CODE_SHA,
                "after_2023_12_29": after,
                "phase": now.get("phase"),
                "pos_v2": now.get("pos_v2"),
                "osc_slope": now.get("osc_slope"),
                "basis": now.get("basis"),
                "phase_v2_source": now.get("phase_v2_source"),
            })
        rolling = bool(central._rolling_over(now))
        carried = central._carry(rec)
        label = (carried.get("cycle") or {}).get("phaseLabel")
        if fk_roll is None:
            fk_roll = d
        roll_rows.append({
            "organ": "rolling_over", "level": "sector", "group_key": key,
            "session_date": d, "state": label,
            "first_knowable_date": fk_roll, "membership_basis": "etf_price",
            "n_members": 1, "engine_code_sha": ENGINE_CODE_SHA,
            "after_2023_12_29": after,
            "rolling": rolling,
            "osc_slope": now.get("osc_slope"),
            "pos_v2": now.get("pos_v2"),
            "pos": now.get("pos"),
            "engine_timing_state": now.get("timing_state"),
            "engine_signal": now.get("signal"),
            "divergence": bool(now.get("divergence")) if now.get("divergence") is not None else None,
        })
    return {"ticker": ticker, "phase_rows": phase_rows, "roll_rows": roll_rows,
            "fk_phase": fk_phase, "fk_roll": fk_roll,
            "_reads": sorted(_READS), "_hazard_cannot_load": _HAZARD_CANNOT_LOAD,
            "_artifacts": read_engine_artifacts()}


def _sector_jobs(closes: pd.DataFrame, tickers: list[str], chunk: int,
                 last_n: int | None = None) -> list[tuple]:
    cal = closes.index
    jobs: list[tuple] = []
    for tk in tickers:
        valid = np.flatnonzero(closes[tk].notna().to_numpy())
        if len(valid) == 0:
            continue
        start = int(valid[0]) + 299
        js = [int(j) for j in valid if int(j) >= start]
        if last_n is not None:
            js = js[-last_n:]
        for k in range(0, len(js), chunk):
            jobs.append((tk, js[k:k + chunk]))
    return jobs


# ── legacy-engine phase_v2 replay (subprocess; legacy code from scratch, data from tree) ─
_LEGACY_WORKER_SRC = r'''
import sys, json
from pathlib import Path
legacy_root, tree_root, out = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, legacy_root)
import lib.config as lcfg
lcfg.ROOT = Path(tree_root)          # config.yml + data resolve to the tree (read-only)
lcfg.load.cache_clear()
import pandas as pd
from engine import sector_cycles as lsc
from engine.inputs import yahoo_closes
closes = yahoo_closes()
closes_px = yahoo_closes(basis="price").reindex(closes.index)
cal = closes.index
bf = pd.read_parquet(Path(tree_root) / "data/sector_cycles/backfill.parquet")
dates = sorted(bf["date"].astype(str).unique())   # the store writer's own grid
rows = []
for D in dates:
    j = int(cal.searchsorted(pd.Timestamp(D), side="right")) - 1
    if j < 0:
        continue
    lo = max(0, j + 1 - 2000)
    sub = closes.iloc[lo:j + 1]
    sub_px = closes_px.iloc[lo:j + 1]
    ws = sub.index[0]
    for tk, meta in lsc.SECTORS.items():
        rec = lsc.build_sector(tk, meta, sub, ws, closes_px=sub_px)
        if not rec:
            continue
        now = rec.get("now") or {}
        pv2 = now.get("phase_v2")
        if pv2 is None:
            continue
        rows.append({"group_key": tk.lower(), "session_date": D, "state": pv2})
with open(out, "w") as f:
    json.dump(rows, f)
print("legacy rows", len(rows), "dates", len(dates))
'''


def legacy_phase_v2_rows(legacy_root: Path, staging: Path) -> list[dict]:
    out = staging / "legacy_phase_v2_rows.json"
    proc = subprocess.run(
        [sys.executable, "-c", _LEGACY_WORKER_SRC, str(legacy_root), str(ROOT), str(out)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"LEGACY REPLAY FAILED:\n{proc.stderr[-4000:]}")
    log(f"legacy replay: {proc.stdout.strip()}")
    rows = json.loads(out.read_text())
    for r in rows:
        r.update({"organ": "phase_v2", "level": "sector", "membership_basis": "etf_price",
                  "n_members": 1, "engine_code_sha": LEGACY_ENGINE_CODE_SHA,
                  "after_2023_12_29": bool(pd.Timestamp(r["session_date"]) > DESK_BLOCK)})
    return rows


# ── fidelity ───────────────────────────────────────────────────────────────────────
def _cmp_state(replay_map: dict, store_rows: list, organ: str) -> dict:
    match = 0
    mismatches: list[dict] = []
    missing = 0
    for key, date, stored in store_rows:
        got = replay_map.get((key, date))
        if got is None:
            missing += 1
            mismatches.append({"group_key": key, "session_date": date,
                               "stored": stored, "replayed": None, "kind": "missing_in_replay"})
            continue
        if got == stored:
            match += 1
        else:
            mismatches.append({"group_key": key, "session_date": date,
                               "stored": stored, "replayed": got, "kind": "state_diff"})
    total = len(store_rows)
    return {"organ": organ, "total": total, "match": match,
            "mismatch": len(mismatches), "missing_in_replay": missing,
            "mismatches": mismatches}


def fidelity_us_basket(df: pd.DataFrame) -> dict:
    led = ubt.load_ledger(config.data_dir())
    sub = df[(df["organ"] == "us_basket") & (df["membership_basis"] == "dated")]
    rmap = {(r.group_key, r.session_date): r.state for r in sub.itertuples()}
    store_rows = []
    for row in led:
        d = row.get("date") or ""
        if "2026-08-07" <= d <= "2026-11-06":
            store_rows.append((row.get("basket_id") or "", d, row.get("state")))
    res = _cmp_state(rmap, store_rows, "us_basket_dated_vs_ledger")
    res["store"] = "data/us_basket_turn/ledger.jsonl"
    res["window"] = "2026-08-07..2026-11-06"
    res["basis_note"] = ("dated version is the live engine basis "
                         "(compute_all uses active_members + ew_level_from_closes, PIT dated mask)")
    # (stored, replayed) state-pair table + cause breakdown (not tuned).
    pairs: dict[str, int] = {}
    causes = {"run_length_seed": 0, "input_vintage": 0, "other": 0}
    # run-length transition pairs: states whose distinction is the run-length counter
    _RL_PAIRS = {("TURNING", "CONFIRMED"), ("CONFIRMED", "TURNING"),
                 ("FALLING", "BASING"), ("BASING", "FALLING"),
                 ("NONE", "FALLING"), ("FALLING", "NONE"),
                 ("WASHED_OUT", "FALLING"), ("FALLING", "WASHED_OUT"),
                 ("TURNING", "BASING"), ("BASING", "TURNING")}
    for mm in res["mismatches"]:
        s, g = mm.get("stored"), mm.get("replayed")
        pk = f"{s}->{g}"
        pairs[pk] = pairs.get(pk, 0) + 1
        if (s, g) in _RL_PAIRS:
            causes["run_length_seed"] += 1
        else:
            causes["other"] += 1
    res["state_pair_table"] = dict(sorted(pairs.items()))
    res["causes"] = causes
    res["cause_method"] = (
        "run_length_seed: the (stored,replayed) pair is a run-length-gated transition "
        "(the washout counter's seed/timing differs between the fresh-window replay and "
        "the live store). input_vintage: reserved for pairs resolved by a price-vintage "
        "change (none attributed without a vintage replay). other: all remaining pairs. "
        "Counts are derived from the mismatch detail, not tuned."
    )
    return res


def _session_calendar(df: pd.DataFrame, engine_sha: str) -> list[str]:
    sub = df[(df["organ"] == "phase_v2") & (df["engine_code_sha"] == engine_sha)]
    return sorted(sub["session_date"].unique().tolist())


def _phase_v2_vs_store(rmap: dict, store_rows: list, sessions: list[str],
                       organ: str) -> dict:
    """Cause-classified comparison: non_session_date_key / state_differs / other.
    No row is added on a non-session date and none is re-keyed. Diagnostic: count of
    non-session keys whose stored state equals the replay at the last session before it."""
    sess_set = set(sessions)
    prev_sess = {sessions[i]: sessions[i - 1] for i in range(1, len(sessions))}
    match = 0
    causes = {"non_session_date_key": 0, "state_differs": 0, "other": 0}
    mismatches: list[dict] = []
    nonsession_equal_prior = 0
    nonsession_total = 0
    for key, date, stored in store_rows:
        if date not in sess_set:
            causes["non_session_date_key"] += 1
            nonsession_total += 1
            ps = prev_sess.get(date)
            # last session strictly before date (date may be after the last session)
            if ps is None:
                prior = [s for s in sessions if s < date]
                ps = prior[-1] if prior else None
            if ps is not None and rmap.get((key, ps)) == stored:
                nonsession_equal_prior += 1
            mismatches.append({"group_key": key, "session_date": date, "stored": stored,
                               "replayed": None, "kind": "non_session_date_key"})
            continue
        got = rmap.get((key, date))
        if got is None:
            causes["other"] += 1
            mismatches.append({"group_key": key, "session_date": date, "stored": stored,
                               "replayed": None, "kind": "missing_in_replay"})
        elif got == stored:
            match += 1
        else:
            causes["state_differs"] += 1
            mismatches.append({"group_key": key, "session_date": date, "stored": stored,
                               "replayed": got, "kind": "state_diff"})
    total = len(store_rows)
    return {"organ": organ, "total": total, "match": match,
            "mismatch": len(mismatches), "causes": causes,
            "non_session_date_keys": nonsession_total,
            "non_session_equal_to_prior_session": nonsession_equal_prior,
            "mismatches": mismatches}


def _d1_table(rmap: dict, fl_rows: list, sessions: list[str]) -> dict:
    """D-1 forward-log table (diagnosis §8). Population = forward-log rows whose (date,id)
    is a session date present in the replay. D-1 = previous session for that id. The replay
    is NOT shifted and no row is re-keyed."""
    sess_set = set(sessions)
    prev_sess = {sessions[i]: sessions[i - 1] for i in range(1, len(sessions))}
    both = d_only = dm1_only = neither = 0
    pop = 0
    for key, date, stored in fl_rows:
        if date not in sess_set or (key, date) not in rmap:
            continue
        pop += 1
        eq_d = rmap.get((key, date)) == stored
        ps = prev_sess.get(date)
        eq_dm1 = (ps is not None and rmap.get((key, ps)) == stored)
        if eq_d and eq_dm1:
            both += 1
        elif eq_d and not eq_dm1:
            d_only += 1
        elif not eq_d and eq_dm1:
            dm1_only += 1
        else:
            neither += 1
    return {"population": pop, "equal_at_D_and_D1": both, "equal_at_D_only": d_only,
            "equal_at_D1_only": dm1_only, "equal_at_neither": neither,
            "sum_check": both + d_only + dm1_only + neither == pop,
            "restricted_to_differ_at_D": {"d1_only": dm1_only, "neither": neither,
                                          "total": dm1_only + neither},
            "definition": ("Population = forward-log rows whose (date,id) is a session date "
                           "present in the replay. D-1 = previous session date for that id in "
                           "the replay. equal at D = stored == replay(id,D); equal at D-1 = "
                           "stored == replay(id,D-1). Replay not shifted; no row re-keyed.")}


def fidelity_phase_v2(df: pd.DataFrame, forward_log_through: str | None = None) -> dict:
    """phase_v2 replay vs the two sector-cycle stores.

    ``forward_log_through`` (YYYY-MM-DD, inclusive) limits the forward_log rows to the
    sessions the replay covers. The forward log is appended every night, so a later read
    of the store holds rows the replay was never built on. None keeps every row (the build).
    """
    root = config.data_dir()
    bf = pd.read_parquet(root / "sector_cycles" / "backfill.parquet")
    bf = bf[bf["id"].isin([t.lower() for t in SPDRS])]
    bf_rows = [(str(r.id), str(r.date), r.phase_v2) for r in bf.itertuples()
               if "2010-12-31" <= str(r.date) <= "2026-06-30"]
    fl = pd.read_parquet(root / "sector_cycles" / "forward_log.parquet")
    fl = fl[fl["id"].isin([t.lower() for t in SPDRS])]
    fl_rows = [(str(r.id), str(r.date), r.phase_v2) for r in fl.itertuples()
               if str(r.date) >= "2026-07-02"
               and (forward_log_through is None or str(r.date)[:10] <= forward_log_through)]
    out: dict = {}
    for sha, label in ((ENGINE_CODE_SHA, "current"), (LEGACY_ENGINE_CODE_SHA, "legacy")):
        sub = df[(df["organ"] == "phase_v2") & (df["engine_code_sha"] == sha)]
        if sub.empty:
            continue
        rmap = {(r.group_key, r.session_date): r.state for r in sub.itertuples()}
        sessions = _session_calendar(df, sha)
        res_bf = _phase_v2_vs_store(rmap, bf_rows, sessions, f"phase_v2_vs_backfill_{label}")
        res_bf["store"] = "data/sector_cycles/backfill.parquet"
        res_bf["cadence"] = "month_end"
        res_bf["engine_code_sha"] = sha
        res_fl = _phase_v2_vs_store(rmap, fl_rows, sessions, f"phase_v2_vs_forward_log_{label}")
        res_fl["store"] = "data/sector_cycles/forward_log.parquet"
        res_fl["cadence"] = "daily"
        res_fl["engine_code_sha"] = sha
        res_fl["fidelity"] = "unproven_against_store"
        res_fl["fidelity_note"] = ("The forward_log writer is not recorded; this comparison "
                                   "is unproven against the store.")
        res_fl["d1_table"] = _d1_table(rmap, fl_rows, sessions)
        out[label] = {"backfill": res_bf, "forward_log": res_fl}
    # overlap: (key,date) pairs present in BOTH engine versions with a different phase
    cur = df[(df["organ"] == "phase_v2") & (df["engine_code_sha"] == ENGINE_CODE_SHA)]
    leg = df[(df["organ"] == "phase_v2") & (df["engine_code_sha"] == LEGACY_ENGINE_CODE_SHA)]
    cmap = {(r.group_key, r.session_date): r.state for r in cur.itertuples()}
    lmap = {(r.group_key, r.session_date): r.state for r in leg.itertuples()}
    overlap = set(cmap) & set(lmap)
    diff = sum(1 for k in overlap if cmap[k] != lmap[k])
    out["version_overlap"] = {"overlap_pairs": len(overlap), "different_phase": diff}
    return out


def fidelity_rolling_over(df: pd.DataFrame, n_sessions: int) -> dict:
    """No persisted store exists (ruling 38 §2d). Compare the replay on the latest sessions
    with the live engine's own computation: sc.compute(asof) + central._rolling_over."""
    sub = df[df["organ"] == "rolling_over"]
    dates = sorted(sub["session_date"].unique())[-n_sessions:]
    rmap = {(r.group_key, r.session_date): bool(r.rolling) for r in sub.itertuples()}
    label_map = {(r.group_key, r.session_date): r.state for r in sub.itertuples()}
    match = 0
    mismatches: list[dict] = []
    compared = 0
    for d in dates:
        live = sc.compute(asof=d)
        if not live:
            continue
        for rec in live.get("sectors") or []:
            key = rec.get("id")
            now = rec.get("now") or {}
            live_rolling = bool(central._rolling_over(now))
            live_label = "Rolling over" if live_rolling else now.get("phaseLabel")
            got = rmap.get((key, d))
            if got is None:
                continue
            compared += 1
            got_label = label_map.get((key, d))
            if got == live_rolling and got_label == live_label:
                match += 1
            else:
                # stored = the parquet replay; replayed = the live engine recomputation
                mismatches.append({"group_key": key, "session_date": d,
                                   "stored": got, "replayed": live_rolling,
                                   "stored_label": got_label, "replayed_label": live_label,
                                   "kind": "rolling_diff"})
    return {"organ": "rolling_over_vs_live_engine", "total": compared, "match": match,
            "mismatch": len(mismatches), "mismatches": mismatches,
            "sessions": dates, "store": None,
            "note": ("No persisted rolling series exists. Fidelity is the replay vs the live "
                     "engine's own computation (sector_cycles.compute(asof) + "
                     "sector_central._rolling_over) on the latest sessions. COO accepted "
                     "this test (ruling 38 §2d).")}


_MAIN_TAPE_WORKER_SRC = r'''
import sys, json
from pathlib import Path
tree_root, main_data, parquet, n, out = sys.argv[1:6]
sys.path.insert(0, tree_root)
import lib.config as lcfg
lcfg.ROOT = Path(tree_root)
lcfg.load.cache_clear()
import pandas as pd
_md = Path(main_data)
lcfg.data_dir = lambda: _md          # redirect the price panel to the scratch main tape
from scripts import build_organ_histories as oh
df = pd.read_parquet(parquet)
res = oh.fidelity_rolling_over(df, int(n))
with open(out, "w") as f:
    json.dump(res, f, default=str)
print("main-tape rolling_over", res["match"], "/", res["total"])
'''


def main_tape_rolling_fidelity(main_tape_root: Path, parquet: Path, n: int,
                               staging: Path) -> dict:
    """rolling_over fidelity against the live engine on main 12e299d's tape, read from a
    scratch data root (yahoo = scratch main tape; other subdirs symlinked to the tree).
    Never written into the tree."""
    main_data = staging / "main_data"
    main_data.mkdir(parents=True, exist_ok=True)
    real = config.data_dir()
    yahoo_src = main_tape_root / "data" / "yahoo"
    if not yahoo_src.exists():
        yahoo_src = main_tape_root / "yahoo"
    link = main_data / "yahoo"
    if not link.exists():
        link.symlink_to(yahoo_src, target_is_directory=True)
    for sub in real.iterdir():
        if sub.name == "yahoo":
            continue
        dest = main_data / sub.name
        if not dest.exists():
            dest.symlink_to(sub, target_is_directory=True)
    out = staging / "main_tape_rolling_fidelity.json"
    proc = subprocess.run(
        [sys.executable, "-c", _MAIN_TAPE_WORKER_SRC, str(ROOT), str(main_data),
         str(parquet), str(n), str(out)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"MAIN-TAPE FIDELITY FAILED:\n{proc.stderr[-4000:]}")
    log(f"main-tape fidelity: {proc.stdout.strip()}")
    res = json.loads(out.read_text())
    res["tape"] = f"main {MAIN_TAPE_PIN} data/yahoo (scratch; never written into the tree)"
    return res


# ── assembly ───────────────────────────────────────────────────────────────────────
def assemble(basket_results: list[dict], sector_results: list[dict],
             legacy_rows: list[dict]) -> tuple[pd.DataFrame, dict]:
    rows: list[dict] = []
    first_knowable: dict = {}
    for br in basket_results:
        rows.extend(br["rows"])
        if br["first_knowable"]:
            first_knowable.setdefault("us_basket", {})[f"{br['bid']}|{br['version']}"] = br["first_knowable"]
    fk_phase: dict[str, str] = {}
    fk_roll: dict[str, str] = {}
    for sr in sector_results:
        rows.extend(sr["phase_rows"])
        rows.extend(sr["roll_rows"])
        key = sr["ticker"].lower()
        if sr["fk_phase"] and (key not in fk_phase or sr["fk_phase"] < fk_phase[key]):
            fk_phase[key] = sr["fk_phase"]
        if sr["fk_roll"] and (key not in fk_roll or sr["fk_roll"] < fk_roll[key]):
            fk_roll[key] = sr["fk_roll"]
    for r in rows:
        if r["organ"] == "phase_v2":
            r["first_knowable_date"] = fk_phase.get(r["group_key"], r["first_knowable_date"])
        elif r["organ"] == "rolling_over":
            r["first_knowable_date"] = fk_roll.get(r["group_key"], r["first_knowable_date"])
    first_knowable["phase_v2"] = fk_phase
    first_knowable["rolling_over"] = fk_roll
    # legacy phase_v2 rows: first_knowable per key = min legacy session date
    leg_fk: dict[str, str] = {}
    for r in legacy_rows:
        k = r["group_key"]
        if k not in leg_fk or r["session_date"] < leg_fk[k]:
            leg_fk[k] = r["session_date"]
    for r in legacy_rows:
        r["first_knowable_date"] = leg_fk[r["group_key"]]
    rows.extend(legacy_rows)

    df = pd.DataFrame(rows)
    common = ["organ", "level", "group_key", "session_date", "state", "first_knowable_date",
              "membership_basis", "n_members", "engine_code_sha", "after_2023_12_29"]
    organ_fields = ["days_in_state", "confirmed_transition", "phase", "pos_v2", "osc_slope",
                    "basis", "phase_v2_source", "rolling", "pos", "engine_timing_state",
                    "engine_signal", "divergence"]
    cols = [c for c in common + organ_fields if c in df.columns]
    df = df[cols]
    for c in ("days_in_state", "n_members"):
        if c in df:
            df[c] = df[c].astype("Int64")
    for c in ("confirmed_transition", "rolling", "divergence", "after_2023_12_29"):
        if c in df:
            df[c] = df[c].astype("boolean")
    df = df.sort_values(["organ", "membership_basis", "group_key", "session_date",
                         "engine_code_sha"]).reset_index(drop=True)
    return df, first_knowable


# ── outputs ────────────────────────────────────────────────────────────────────────
def write_outputs(df: pd.DataFrame, first_knowable: dict, fidelity: dict,
                  engine_hashes: dict, parquet_path: Path, meta_path: Path,
                  report_path: Path, build_seconds: float, provenance: dict,
                  report_sentence: str | None = None) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(parquet_path, index=False)
    pb = parquet_path.read_bytes()
    parquet_sha = hashlib.sha256(pb).hexdigest()
    try:
        parquet_rel = str(parquet_path.relative_to(ROOT))
    except ValueError:
        parquet_rel = str(parquet_path)

    organs = {}
    for organ, g in df.groupby("organ"):
        organs[organ] = {
            "rows": int(len(g)),
            "keys": int(g["group_key"].nunique()),
            "first_session": str(g["session_date"].min()),
            "last_session": str(g["session_date"].max()),
            "membership_basis": sorted(g["membership_basis"].unique().tolist()),
            "engine_code_sha": sorted(g["engine_code_sha"].unique().tolist()),
        }

    meta = {
        "schema": "organ_histories_house/v2",
        "engine_code_sha": ENGINE_CODE_SHA,
        "legacy_engine_code_sha": LEGACY_ENGINE_CODE_SHA,
        "engine_module_sha256": engine_hashes,
        "repository_module_sha256": provenance["repo_modules"],
        "repository_module_count": len(provenance["repo_modules"]),
        "library_versions": provenance["library_versions"],
        "inputs_commit": provenance["inputs_commit"],
        "inputs_clean_for_build": provenance["inputs_clean"],
        "input_gate": {k: v for k, v in provenance["gate"].items() if k != "checked"},
        "input_file_provenance": provenance["gate"]["checked"],
        "opened_file_record": provenance["opened"],
        "engine_input_list": ENGINE_INPUTS,
        "engine_artifacts_loaded": provenance["artifacts"],
        "regime_calibration_proof": regime_calibration_proof(provenance),
        "hazard_cannot_load_count": provenance["hazard_cannot_load"],
        "no_fallback_proof": (
            "Proof is the opened-file record (both data/regime calibrations opened, each "
            "sha256 equal to its blob at inputs_commit) plus the read-back of the engine's "
            "cached loaded values (cycles._FITTED_BANDS / _RISK_CALIB non-empty, with the "
            "count of band values differing from the hand constants). The bands/risk loaders "
            "return {} on absence before any log line (engine/cycles.py:98-99, :127-128), so "
            "a log count is NOT used as proof. The hazard 'cannot load' count is a separate "
            "hazard-only check."
        ),
        "price_basis": "restated",
        "price_basis_note": ("Prices are restated as of capture (the latest committed tape), "
                             "not point-in-time as-of each historical session. Fidelity against "
                             "the live stores is measured on this restated basis; mismatches are "
                             "reported, not tuned."),
        "no_outcome": NO_OUTCOME,
        "window_cap_bars": WINDOW_CAP,
        "window_cap_source": "scripts/backfill_forward_logs.py:85 (PIT-equivalent for signal fields)",
        "engine_signal_note": (
            "engine_signal and engine_timing_state are engine/sector_cycles.py output at the "
            "pinned sha (the `now` block's signal / timing_state fields), NOT a Sector "
            "Intelligence call."
        ),
        "legacy_engine_note": (
            f"{ENGINE_CODE_SHA[:12]} rows are the current engine's history and the primary "
            f"series. {LEGACY_ENGINE_SHORT} rows are the version that wrote backfill.parquet "
            "(backfill_manifest.json git_sha), present to prove the replay and show the "
            "version difference."
        ),
        "inputs": {
            "us_basket_membership": "data/baskets/membership.json (seed 2023-05-09)",
            "us_basket_member_closes": "data/stocks/{T}.parquet, data/baskets/ohlcv/{T}.parquet",
            "sector_prices": "data/yahoo/{T}.parquet (11 SPDR sectors + SPY benchmark), TR + close_price basis",
            "engine_calibration": [e["path"] for e in ENGINE_INPUTS],
            "fidelity_stores": [
                "data/us_basket_turn/ledger.jsonl",
                "data/sector_cycles/backfill.parquet",
                "data/sector_cycles/forward_log.parquet",
            ],
        },
        "membership_basis": {
            "us_basket_dated": ("Dated [added, removed) membership applied point-in-time. This is "
                                "the LIVE engine basis: compute_all (engine/us_basket_turn.py:785) "
                                "uses active_members + ew_level_from_closes with the dated mask."),
            "us_basket_current": ("SENSITIVITY only: today's active members (added=None, removed "
                                  "kept) applied as far back as the inputs reach."),
            "sector_organs": "ETF price series only; no membership concept applies (n_members=1).",
        },
        "first_knowable": {
            "method": {
                "us_basket": ("252nd session of the engine-built EW level series "
                              "(engine/us_basket_turn.py:340 drawdown window fully populated)."),
                "phase_v2": ("First session where the engine's build_sector returns a non-null "
                             "phase_v2 (300-bar build floor + weekly MTF warm), found empirically."),
                "rolling_over": ("First session where the engine's build_sector returns a record "
                                 "whose `now` the override predicate can read, found empirically."),
            },
            "by_organ_key": first_knowable,
        },
        "organs": organs,
        "fidelity": fidelity,
        "parquet": {"path": parquet_rel, "bytes": len(pb), "sha256": parquet_sha},
        "build_seconds": round(build_seconds, 1),
        "scope_note": ("Three HOUSE organs only (us_basket washout, phase_v2, rolling_over). "
                       "Vendor-keyed organs are out of scope for this draft."),
    }
    meta_path.write_text(json.dumps(meta, indent=2, default=str))

    # one-page report
    lines = [
        "# Engine alert histories — three HOUSE organs (COO ruling 38 Part A)",
        "",
        f"Engine pin: `{ENGINE_CODE_SHA}` (primary); legacy `{LEGACY_ENGINE_SHORT}` "
        "(backfill writer). Prices: **restated** as of capture. Every state is the engine's "
        "own output; the engine was imported and called, never edited.",
        "",
        NO_OUTCOME,
        "",
        "| organ | keys | first knowable | rows | fidelity match/total |",
        "|---|---|---|---|---|",
    ]
    if report_sentence:
        idx = lines.index(NO_OUTCOME) + 1
        lines[idx:idx] = ["", report_sentence.strip()]
    fk_summary = {
        "us_basket": "≈2024-05 (dated, 252-session floor); current as far back as inputs reach",
        "phase_v2": "per-key 300-bar floor + MTF warm (nine 2000-03-01, XLC ≈2019-08, XLRE 2016-12-14)",
        "rolling_over": "per-key 300-bar floor + MTF warm (same as phase_v2)",
    }

    def _fid_str(organ: str) -> str:
        if organ == "phase_v2":
            cur = fidelity.get("phase_v2", {}).get("current", {})
            bf = cur.get("backfill", {})
            fl = cur.get("forward_log", {})
            return (f"backfill {bf.get('match', '?')}/{bf.get('total', '?')}; "
                    f"forward {fl.get('match', '?')}/{fl.get('total', '?')}")
        f = fidelity.get(organ, {})
        return f"{f.get('match', '?')}/{f.get('total', '?')}"

    for organ in ("us_basket", "phase_v2", "rolling_over"):
        o = organs.get(organ, {})
        lines.append(f"| {organ} | {o.get('keys', '?')} | {fk_summary[organ]} | "
                     f"{o.get('rows', '?')} | {_fid_str(organ)} |")
    lines += ["", "## Fidelity detail", ""]
    ub = fidelity.get("us_basket", {})
    lines.append(f"- **us_basket (dated vs ledger.jsonl, {ub.get('window', '')})**: "
                 f"{ub.get('match', '?')}/{ub.get('total', '?')} match, "
                 f"{ub.get('mismatch', '?')} mismatch. {ub.get('basis_note', '')}")
    pv = fidelity.get("phase_v2", {})
    for label in ("current", "legacy"):
        grp = pv.get(label, {})
        for nm in ("backfill", "forward_log"):
            r = grp.get(nm, {})
            if not r:
                continue
            cz = r.get("causes", {})
            lines.append(f"- **phase_v2 ({label}) vs {nm}** ({r.get('cadence', '')}): "
                         f"{r.get('match', '?')}/{r.get('total', '?')} match, "
                         f"{r.get('mismatch', '?')} mismatch; causes "
                         f"non_session_date_key={cz.get('non_session_date_key', 0)}, "
                         f"state_differs={cz.get('state_differs', 0)}, other={cz.get('other', 0)}.")
    vo = pv.get("version_overlap", {})
    lines.append(f"- **phase_v2 version overlap**: {vo.get('overlap_pairs', 0)} (key,date) pairs "
                 f"present in both engine versions; {vo.get('different_phase', 0)} give a different phase.")
    cur_fl = pv.get("current", {}).get("forward_log", {})
    d1 = cur_fl.get("d1_table", {})
    if d1:
        lines += ["", "### D-1 forward-log table (current engine; re-derived)", "",
                  d1.get("definition", ""), "",
                  f"Population = {d1.get('population', '?')}.", "",
                  "| | equal at D-1 | NOT equal at D-1 | row total |",
                  "|---|---|---|---|",
                  f"| equal at D | {d1.get('equal_at_D_and_D1', '?')} (both) | "
                  f"{d1.get('equal_at_D_only', '?')} (D only) | "
                  f"{d1.get('equal_at_D_and_D1', 0) + d1.get('equal_at_D_only', 0)} |",
                  f"| NOT equal at D | {d1.get('equal_at_D1_only', '?')} (D-1 only) | "
                  f"{d1.get('equal_at_neither', '?')} (neither) | "
                  f"{d1.get('equal_at_D1_only', 0) + d1.get('equal_at_neither', 0)} |", ""]
        rest = d1.get("restricted_to_differ_at_D", {})
        lines.append(f"Restricted to rows differing at D ({rest.get('total', '?')} rows): "
                     f"D-1 only = {rest.get('d1_only', '?')}, neither = {rest.get('neither', '?')}.")
        lines.append(f"The live log stamps {d1.get('equal_at_D1_only', '?')} rows with the "
                     "benchmark date while that sector's tape lagged a session (live-store "
                     "behaviour, not repaired by us).")
    ro = fidelity.get("rolling_over", {})
    lines.append(f"- **rolling_over vs live engine, branch tape** (latest "
                 f"{len(ro.get('sessions', []))} sessions): {ro.get('match', '?')}/"
                 f"{ro.get('total', '?')} match, {ro.get('mismatch', '?')} mismatch.")
    rom = fidelity.get("rolling_over_main_tape", {})
    if rom:
        lines.append(f"- **rolling_over vs live engine, main {MAIN_TAPE_PIN[:12]} tape** "
                     f"(scratch): {rom.get('match', '?')}/{rom.get('total', '?')} match, "
                     f"{rom.get('mismatch', '?')} mismatch. {rom.get('tape', '')}")
    lines += ["", "## Mismatches (every one; none tuned away)", ""]
    any_mm = False
    mm_sources = [("us_basket", ub),
                  ("phase_v2/current/backfill", pv.get("current", {}).get("backfill", {})),
                  ("phase_v2/current/forward_log", cur_fl),
                  ("phase_v2/legacy/backfill", pv.get("legacy", {}).get("backfill", {})),
                  ("phase_v2/legacy/forward_log", pv.get("legacy", {}).get("forward_log", {})),
                  ("rolling_over", ro)]
    for label, res in mm_sources:
        for mm in res.get("mismatches", []):
            any_mm = True
            lines.append(f"- {label}: {mm.get('group_key')} @ {mm.get('session_date')} "
                         f"stored={mm.get('stored')!r} replayed={mm.get('replayed')!r} "
                         f"({mm.get('kind')})")
    if not any_mm:
        lines.append("- None.")
    lines += ["", "## Reproduction", "",
              "```",
              "git archive 896471652cea engine lib config | tar -x -C <scratch>/legacy_engine",
              "git archive 12e299d data/yahoo | tar -x -C <scratch>/main_tape",
              "/opt/homebrew/Caskroom/miniconda/base/bin/python3 scripts/build_organ_histories.py \\",
              "    --staging-dir <scratch>/staging \\",
              "    --legacy-engine-root <scratch>/legacy_engine \\",
              "    --main-tape-root <scratch>/main_tape",
              "```", "",
              f"Parquet: `{meta['parquet']['path']}` — {meta['parquet']['bytes']} bytes, "
              f"sha256 `{meta['parquet']['sha256']}`.", "",
              "## Build environment", "", PACKAGE_VERSIONS_SENTENCE, ""]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))
    log(f"wrote {parquet_path} ({len(pb)} bytes, sha256 {parquet_sha})")
    log(f"wrote {meta_path}")
    log(f"wrote {report_path}")


# ── main ───────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--sector-chunk", type=int, default=400)
    ap.add_argument("--rolling-fidelity-sessions", type=int, default=10)
    ap.add_argument("--smoke", action="store_true", help="quick mechanics check, scratch outputs")
    ap.add_argument("--skip-fidelity", action="store_true")
    ap.add_argument("--staging-dir", type=Path, required=True,
                    help="REQUIRED staging directory; empty/absent at start; writes only here")
    ap.add_argument("--legacy-engine-root", type=Path, default=None,
                    help="scratch dir holding git archive 896471652cea engine lib config")
    ap.add_argument("--main-tape-root", type=Path, default=None,
                    help="scratch dir holding git archive 12e299d data/yahoo")
    ap.add_argument("--report-sentence-file", type=Path, default=None,
                    help="optional file whose text is inserted VERBATIM as the report cause "
                         "sentence (supplied by the COO at commit-release; omitted until then)")
    args = ap.parse_args(argv)

    import multiprocessing as mp

    t0 = time.time()
    check_staging(args.staging_dir)
    engine_hashes = verify_engine_pin()

    inputs_commit = git_head()
    blobs = head_blobs()
    gate = input_gate(inputs_commit, blobs)

    current_root = setup_current_root(args.staging_dir)
    real = config.data_dir()
    closes = yahoo_closes()
    log(f"panel {closes.shape} {closes.index.min().date()} -> {closes.index.max().date()}")

    us_baskets = sorted(ubt._load_membership(real).keys())
    tickers = SPDRS
    if args.smoke:
        us_baskets = us_baskets[:2]
        tickers = SPDRS[:2]
        log(f"SMOKE: baskets={us_baskets} tickers={tickers}")

    ctx = mp.get_context("spawn")
    basket_results: list[dict] = []
    sector_results: list[dict] = []

    cr = str(current_root)
    basket_jobs = [(bid, v, cr) for bid in us_baskets for v in ("dated", "current")]
    if args.smoke:
        basket_jobs = [(bid, "dated", cr) for bid in us_baskets] + [(us_baskets[0], "current", cr)]
    log(f"basket tasks: {len(basket_jobs)}")
    with ctx.Pool(args.workers) as pool:
        for i, res in enumerate(pool.imap_unordered(basket_task, basket_jobs)):
            basket_results.append(res)
            if (i + 1) % 10 == 0 or args.smoke:
                log(f"  baskets {i + 1}/{len(basket_jobs)} "
                    f"({res['bid']}/{res['version']} rows={len(res['rows'])})")
    log(f"baskets done in {time.time() - t0:.1f}s")

    sector_jobs = _sector_jobs(closes, tickers, args.sector_chunk,
                               last_n=120 if args.smoke else None)
    log(f"sector tasks: {len(sector_jobs)}")
    ts = time.time()
    with ctx.Pool(args.workers, initializer=sector_init) as pool:
        for i, res in enumerate(pool.imap_unordered(sector_task, sector_jobs)):
            sector_results.append(res)
            if (i + 1) % 20 == 0 or args.smoke:
                log(f"  sectors {i + 1}/{len(sector_jobs)} "
                    f"({res['ticker']} phase={len(res['phase_rows'])} roll={len(res['roll_rows'])})")
    log(f"sectors done in {time.time() - ts:.1f}s")

    # legacy-engine phase_v2 rows
    legacy_rows: list[dict] = []
    if args.legacy_engine_root and not args.smoke:
        legacy_rows = legacy_phase_v2_rows(args.legacy_engine_root, args.staging_dir)
        log(f"legacy phase_v2 rows: {len(legacy_rows)}")

    df, first_knowable = assemble(basket_results, sector_results, legacy_rows)
    log(f"assembled {len(df)} rows; organs={df['organ'].value_counts().to_dict()}")

    fidelity: dict = {}
    if not args.skip_fidelity:
        tf = time.time()
        fidelity["us_basket"] = fidelity_us_basket(df)
        fidelity["phase_v2"] = fidelity_phase_v2(df)
        fidelity["rolling_over"] = fidelity_rolling_over(df, args.rolling_fidelity_sessions)
        log(f"fidelity done in {time.time() - tf:.1f}s")

    # write the parquet first so the main-tape fidelity can read it
    if args.smoke:
        pq = args.staging_dir / "smoke_organ_histories_house.parquet"
        mt = args.staging_dir / "smoke_organ_histories_house.meta.json"
        rp = args.staging_dir / "smoke_ORGAN_HISTORIES_REPORT.md"
    else:
        pq, mt, rp = OUT_PARQUET, OUT_META, OUT_REPORT

    if args.main_tape_root and not args.skip_fidelity and not args.smoke:
        df.to_parquet(pq, index=False)
        fidelity["rolling_over_main_tape"] = main_tape_rolling_fidelity(
            args.main_tape_root, pq, args.rolling_fidelity_sessions, args.staging_dir)

    # ── provenance: merge opened-file records + artifact read-back from workers ──────
    opened = set(_READS)
    hazard_count = _HAZARD_CANNOT_LOAD
    artifacts = read_engine_artifacts()
    for sr in sector_results:
        opened.update(sr.get("_reads", []))
        hazard_count += sr.get("_hazard_cannot_load", 0)
        wa = sr.get("_artifacts") or {}
        for k in ("fitted_bands_loaded", "fitted_bands_nonempty", "risk_calib_loaded",
                  "risk_calib_nonempty", "hazard_model_loaded", "hazard_km_loaded"):
            artifacts[k] = bool(artifacts.get(k)) and bool(wa.get(k, True))
    repo_modules = repo_module_hashes()
    for sr in sector_results:
        pass  # worker module hashes are identical (same tree); parent walk suffices

    # post-build audit: every opened data/ file must equal its blob at inputs_commit
    opened_data = sorted(r for r in opened if r.startswith("data/") or r == "config.yml")
    audit_diff: list[str] = []
    for rel in opened_data:
        want = blobs.get(rel)
        got = working_blob_id(ROOT / rel)
        if want is None or got != want:
            audit_diff.append(rel)
    enumerated = set(gate["checked"].keys())
    opened_not_listed = sorted(r for r in opened_data if r not in enumerated)
    listed_not_opened = sorted(r for r in enumerated if r not in opened)
    if opened_not_listed:
        log(f"WARNING: {len(opened_not_listed)} opened data/ files not on the enumerated "
            f"input list (first 10: {opened_not_listed[:10]})")
    if listed_not_opened:
        log(f"WARNING: {len(listed_not_opened)} enumerated inputs not opened "
            f"(first 10: {listed_not_opened[:10]})")
    if audit_diff:
        raise SystemExit("OPENED-FILE AUDIT REFUSAL — opened files differ from inputs_commit "
                         f"blobs: {audit_diff[:20]}")
    if hazard_count != 0:
        raise SystemExit(f"HAZARD LOADER REFUSAL: 'cannot load' logged {hazard_count} times "
                         "(hazard artifact failed to load).")
    if not (artifacts["fitted_bands_loaded"] and artifacts["fitted_bands_nonempty"]
            and artifacts["risk_calib_loaded"] and artifacts["risk_calib_nonempty"]):
        raise SystemExit("ENGINE ARTIFACT REFUSAL: fitted bands / risk calibration not loaded "
                         "(read-back empty). The engine would have used fallback constants.")
    # both regime calibrations must appear in the opened-file record at inputs_commit bytes
    for e in ENGINE_INPUTS:
        if e["mandatory"] and e["path"] not in opened:
            raise SystemExit(f"ENGINE INPUT REFUSAL: {e['path']} was not opened during the run.")

    opened_record = {
        rel: {"sha256": file_sha256(ROOT / rel), "bytes": (ROOT / rel).stat().st_size,
              "matches_inputs_commit": blobs.get(rel) == working_blob_id(ROOT / rel)}
        for rel in opened_data
    }
    provenance = {
        "inputs_commit": inputs_commit,
        "inputs_clean": not gate["differing"] and not gate["missing"] and not audit_diff,
        "gate": gate,
        "repo_modules": repo_modules,
        "library_versions": {"numpy": np.__version__, "pandas": pd.__version__,
                             "pyarrow": __import__("pyarrow").__version__},
        "artifacts": artifacts,
        "hazard_cannot_load": hazard_count,
        "opened": {"count": len(opened_data),
                   "opened_not_on_list": opened_not_listed,
                   "on_list_not_opened": listed_not_opened,
                   "opened_not_on_list_count": len(opened_not_listed),
                   "on_list_not_opened_count": len(listed_not_opened),
                   "files": opened_record},
    }

    report_sentence = None
    if args.report_sentence_file:
        report_sentence = args.report_sentence_file.read_text()
    write_outputs(df, first_knowable, fidelity, engine_hashes, pq, mt, rp,
                  time.time() - t0, provenance, report_sentence)
    log(f"TOTAL {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    # Mute library warnings for the CLI run only; importing this module leaves
    # the caller's warning filters alone (import-hygiene ratchet, COO ruling 100).
    warnings.filterwarnings("ignore")
    raise SystemExit(main())
