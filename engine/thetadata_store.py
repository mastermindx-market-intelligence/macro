"""Reader over the ThetaData EOD historical store.

Store layout (T1 backfill, accumulates in ops worktree):
  {THETADATA_STORE}/eod/{ROOT}/{YYYY}.parquet
  {THETADATA_STORE}/oi/{ROOT}/{YYYY}.parquet
  {THETADATA_STORE}/greeks/{ROOT}/{YYYY}.parquet   (optional — vendor IV starts ~2015+)

EOD columns  : root, expiration, strike, right, date, open, high, low, close,
               volume, count, bid, ask
OI columns   : root, expiration, strike, right, date, open_interest
Greeks cols  : root, expiration, strike, right, date, bid, ask, underlying_price,
               delta, theta, vega, rho, epsilon, lambda, implied_vol, iv_error

OI TIMING LAW (LIVE_ORDER_FLOW_BRAINSTORM_BY_FABLE §8 ¶1):
  OPRA reports OI once per day at ~06:30 ET representing end-of-PREVIOUS-day positions.
  oi[t] = positions as of EOD t-1.  For any day-t signal, the correct OI input is
  oi[t-1] (i.e. shift(1) on the OI series).  Using same-day OI is a lookahead bug.
  doi_series() enforces this via pandas shift(1) BEFORE computing deltas.

STORE ROOT:
  resolve_thetadata_store() is THE canonical resolver (WP-RESOLVER): env
  THETADATA_STORE → lib.config data_dir()/thetadata_eod → the ops-host worktree
  store — every candidate existence- AND content-checked (must contain at least
  one of eod/, oi/, greeks/). An empty stub dir does NOT resolve: that is the
  exact shape of the options_witness 0/18 incident, where a GH runner resolved
  an empty repo-local store and published an all-suppressed artifact.
  store_root() remains as a back-compat wrapper (always returns a Path, may not
  exist — it warns when it doesn't); new callers should use the resolver.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# parquet load cache                                                            #
# --------------------------------------------------------------------------- #
# _PARQUET_CACHE: (tier, root, year_file_path_str) -> pd.DataFrame
#
# A full-universe run calls chain() for every (date, root) combination.
# Without caching, _load_parquets re-reads the year file on EVERY date within
# the same year, turning the run into O(dates × full reads). With this cache,
# each year file is read exactly once — O(roots × years × reads).
#
# Memory tradeoff: each cached DataFrame is the full year of one (tier, root)
# pair (typically a few MB for SPY eod; smaller for oi/greeks). At 3 tiers ×
# N roots × Y years the peak footprint is 3NY DataFrames in memory.  For a
# broad universe (hundreds of roots, 12 years) this can reach several GB; for
# typical backtests (tens of roots) it is comfortably under 1 GB.  Call
# clear_parquet_cache() to release all frames after a batch run.
_PARQUET_CACHE: dict[str, pd.DataFrame] = {}

# The live poller needs only one session's prior-day OI.  Keep that narrow
# contract explicit so it cannot accidentally grow back into chain()'s three
# full-year tiers.  The order is also the stable public return shape.
_OI_COLUMNS = (
    "root", "expiration", "strike", "right", "date", "open_interest",
)
_EOD_MATRIX_COLUMNS = (
    "root", "expiration", "strike", "right", "date", "volume", "close",
)
_EOD_VOLUME_COLUMNS = (
    "root", "expiration", "strike", "right", "date", "volume",
)
_EOD_SESSION_COLUMNS = ("root", "date")
_CANONICAL_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def clear_parquet_cache() -> None:
    """Release all cached year-parquet DataFrames.

    Call after a full-universe batch run to reclaim memory.  Not needed for
    single-date queries or for tests (the fixture store is tiny).
    """
    _PARQUET_CACHE.clear()


# --------------------------------------------------------------------------- #
# store root resolution                                                         #
# --------------------------------------------------------------------------- #

# Canonical ops-host store path (the launchd theta-ops worktree). This constant
# lives HERE and only here — per-module copies of this path were the fragmented
# resolution that enabled the options_witness empty-store incident.
_OPS_WT_STORE = Path("/Users/chriswong/theta-ops-wt/data/thetadata_eod")

# A directory only counts as a store when at least one tier subdir is present.
_STORE_TIERS = ("eod", "oi", "greeks")


# Bounded store probe (AD-1T2b). Deciding "does this store hold any data" needs a
# readdir, and on the ops host the three tier dirs are SYMLINKS onto an external
# volume (scripts/publish_r2.py::_walk_files). Listing them is the operation that
# hangs or is denied under launchd — scripts/build_options_hub_nightly.py::
# preflight_store exists solely to bound it, with os._exit(4) on timeout. That
# guard runs AFTER resolution, so an unbounded readdir in here would sit in front
# of the only thing protecting against it, in the one function every consumer
# calls. Hence: bounded, and three-valued so ambiguity is never mistaken for
# emptiness.
def _probe_budget() -> float:
    """The probe budget, read defensively — a bad value must never break imports.

    This is module scope in THE resolver every consumer imports, so a ValueError
    here takes down the whole build. The realistic shape is a workflow `env:` key
    declared with no value (""), not a typo. NaN gets its own branch because it
    passes every `<= 0` comparison and then makes `Thread.join(nan)` raise.
    """
    raw = os.environ.get("THETADATA_STORE_PROBE_S", "10")
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 10.0
    return 10.0 if v != v else v      # v != v is True only for NaN


_STORE_PROBE_S: float = _probe_budget()

_HAS_ROOT = "has_root"   # a tier provably holds at least one root directory
_DRAINED = "drained"     # tier dirs exist and provably hold no roots
_NO_TIERS = "no_tiers"   # empty stub: no eod/ oi/ greeks/ at all
_UNKNOWN = "unknown"     # denied, blocked or errored — emptiness NOT established
_UNMOUNTED = "unmounted" # path or a tier entry lands on a volume that is not mounted

# THE fail-open rule, in exactly one place. Both the public predicate and the
# resolver loop read it, so they cannot drift apart: only a PROVABLY empty
# candidate (_DRAINED / _NO_TIERS) is skipped. _UNMOUNTED is deliberately
# absent — a store on a volume that is not mounted stops the chain.
_RESOLVABLE = (_HAS_ROOT, _UNKNOWN)

# Tests monkeypatch these two. Production uses the real volumes root.
_VOLUMES_ROOT = Path("/Volumes")


def _is_mount(p: Path) -> bool:
    return os.path.ismount(p)


def _unmounted_volume(p: Path) -> Path | None:
    """Return the unmounted volume `p` or one of its tier entries lands on.

    Candidates are `p` itself and every tier entry that lexists, so a dangling
    symlink counts. Only lstat / readlink / stat — no directory listing.
    OSError propagates; the caller fails that open to `_UNKNOWN`.
    """
    candidates: list[Path] = [p]
    for t in _STORE_TIERS:
        tier = p / t
        if os.path.lexists(tier):
            candidates.append(tier)
    vroot = Path(os.path.realpath(_VOLUMES_ROOT))
    for c in candidates:
        r = Path(os.path.realpath(c))
        try:
            parts = r.relative_to(vroot).parts
        except ValueError:
            continue
        if not parts:
            continue
        vol = vroot / parts[0]
        if not _is_mount(vol):
            return vol
    return None


def _classify_store(p: Path) -> str:
    """Classify a store candidate without ever mistaking "cannot read" for "empty".

    Returns one of _HAS_ROOT / _DRAINED / _NO_TIERS / _UNKNOWN / _UNMOUNTED.

    `_UNMOUNTED` is decided first, from lstat/readlink/stat only, when the path
    or a tier entry resolves onto a volume that is not mounted. An OSError from
    that check fails open to `_UNKNOWN`, same as the `is_dir()` stats.

    Only the `is_dir()` calls and that volume check happen on the calling
    thread — those are stats, the same class of syscall the pre-AD-1T2b
    predicate made, and they are not the operation that hangs. The readdir
    runs in a daemon thread under a join budget so a blocked external volume
    cannot wedge the resolver; on timeout the thread is
    abandoned (daemon, so it never holds up interpreter exit) and the answer is
    _UNKNOWN.
    """
    try:
        if _unmounted_volume(p) is not None:
            return _UNMOUNTED
        if not p.is_dir():
            return _NO_TIERS
        tiers = [p / t for t in _STORE_TIERS if (p / t).is_dir()]
    except OSError:
        return _UNKNOWN
    if not tiers:
        return _NO_TIERS

    outcome: dict[str, object] = {}

    def _probe() -> None:
        try:
            for t in tiers:
                for child in t.iterdir():
                    if child.is_dir():
                        outcome["verdict"] = _HAS_ROOT
                        return
            outcome["verdict"] = _DRAINED
        except OSError as e:
            outcome["err"] = e

    if _STORE_PROBE_S <= 0:      # probe disabled — never claim emptiness
        return _UNKNOWN
    th = threading.Thread(target=_probe, name="thetadata-store-probe", daemon=True)
    try:
        th.start()
        th.join(_STORE_PROBE_S)
    except (RuntimeError, ValueError) as e:
        # Thread.start() raises RuntimeError when the process cannot create one
        # more thread. Before this check existed the resolver could not raise at
        # all, and callers document that (engine/options_skew.py load_chain).
        # Refusing to resolve because we could not START the probe would be the
        # same false-RED the probe exists to avoid.
        log.warning(
            "thetadata_store: could not run the bounded probe on %s (%s). "
            "Emptiness is NOT established, so the store is treated as PRESENT.",
            p, e)
        return _UNKNOWN
    if th.is_alive():
        log.warning(
            "thetadata_store: listing the tier dirs under %s did not return "
            "within %.0fs — the read is blocked, not slow (TCC/removable-volume "
            "shape: the tier dirs are symlinks onto an external volume). Treating "
            "the store as PRESENT so behaviour is unchanged from before this "
            "check existed; readability is enforced downstream by "
            "build_options_hub_nightly.preflight_store.", p, _STORE_PROBE_S)
        return _UNKNOWN
    if "err" in outcome:
        log.warning(
            "thetadata_store: listing the tier dirs under %s failed (%s). "
            "Emptiness is NOT established, so the store is treated as PRESENT — "
            "an unreadable store must never be reported as a drained one.",
            p, outcome["err"])
        return _UNKNOWN
    return str(outcome.get("verdict", _UNKNOWN))


def _has_store_content(p: Path) -> bool:
    """True when `p` exists and is not provably empty.

    An empty stub directory (exists, no tier subdirs) does NOT count — resolving
    one silently yields empty frames everywhere downstream, which is the exact
    incident shape (options_witness published 0/18 themes from a stub store).

    AD-1T2b (2026-09-29): a directory whose tier subdirs all EXIST but hold no
    root is the same incident wearing a better disguise, so it does not count
    either. Observed live on the store-bearing M1 (m1studio) that day: eod/, oi/
    and greeks/ all present and all holding zero roots, beside a _manifest.json
    still reading ``"status": "healthy", "complete_t1_roots": 372`` from
    2026-09-25 — while a control directory on the same host and filesystem
    (data/yahoo/) held 728 entries. The old directory-existence-only predicate
    admitted that store, so the options-intel producer resolved it, took
    build()'s ``anchor_str is None`` branch, and published a blank
    DEGRADED/MIXED_VINTAGE brief OVER the last good one while exiting 0 — even
    under ``--require-store``.

    FAILS OPEN BY CONSTRUCTION. Only a PROVABLY drained store is refused; a
    candidate whose tiers could not be listed (denied, blocked, errored, probe
    disabled) resolves exactly as it did before this check existed. That
    asymmetry is deliberate: the cost of a false "drained" is every nightly lane
    losing a store that is actually intact, which is worse than the bug this
    catches. See _classify_store.

    SCOPE — one level deep, and no further. A root is a DIRECTORY, matching how
    the store is actually walked (``universe()`` and ``iv_coverage()`` below both
    count ``is_dir()`` children; ``_load_parquets()`` then globs inside a root).
    So a stray ``.DS_Store`` or a leftover lock file cannot revive the false
    positive — but a drain that deletes every ``*.parquet`` while LEAVING the
    root directories is NOT caught here and still reaches the builders, which
    must keep handling empty frames honestly. This predicate answers only "does
    any tier hold a root directory", never "is there usable data".

    NOT a health or freshness check — a store holding real but thin or stale data
    still resolves, and publishing that honestly (NO_SIGNAL, INSUFFICIENT_COVERAGE,
    STALE_SOURCE) remains the contract.
    """
    return _classify_store(p) in _RESOLVABLE


def _drained_store(p: Path) -> bool:
    """True only for a PROVABLY drained store. Diagnostic; resolution is decided
    by ``_has_store_content``. Prefer ``_classify_store`` when you also need the
    resolution answer — this re-probes."""
    return _classify_store(p) == _DRAINED


def _store_candidates() -> list[tuple[str, Path]]:
    """The canonical fallback chain, in order. One definition, two readers."""
    out: list[tuple[str, Path]] = []
    env = os.environ.get("THETADATA_STORE")
    if env:
        out.append(("env", Path(env)))
    try:
        from lib import config  # noqa: PLC0415
        out.append(("data_dir", config.data_dir() / "thetadata_eod"))
    except Exception:  # noqa: BLE001
        out.append(("data_dir", Path("data") / "thetadata_eod"))
    out.append(("ops-wt", _OPS_WT_STORE))
    return out


def drained_store_candidates() -> list[Path]:
    """Every candidate in the canonical chain that is PROVABLY drained.

    Exists because ``resolve_thetadata_store() is None`` is ambiguous after
    AD-1T2b: it means "nothing resolved", which is a FRESH INSTALL when no store
    exists anywhere, and a DRAINED CANONICAL STORE otherwise. A writer that
    treats both as fresh-install will happily mint a second store beside the
    drained one — see scripts/backfill_thetadata_eod.py, whose second-store
    guard depends on telling these apart.

    Never raises; an unreadable candidate is not drained (fail open, as always).
    """
    return [path for _src, path in _store_candidates()
            if _classify_store(path) == _DRAINED]


def unmounted_store_candidates() -> list[Path]:
    """Every candidate in the canonical chain that sits on an unmounted volume.

    ``resolve_thetadata_store() is None`` is otherwise ambiguous: a fresh
    install, a drained store, or a store whose volume is not mounted. A writer
    that treats the unmounted case as a fresh install will mint a second store
    on another disk — see scripts/backfill_thetadata_eod.py.

    Never raises; an unreadable candidate is not unmounted (fail open, as
    ``_classify_store`` does).
    """
    return [path for _src, path in _store_candidates()
            if _classify_store(path) == _UNMOUNTED]


def resolve_thetadata_store(required: bool = False,
                            purpose: str = "") -> Path | None:
    """THE canonical ThetaData store resolver (WP-RESOLVER) — single fallback chain.

    Chain (first content-bearing hit wins):
      1. THETADATA_STORE env — warns loudly when set but missing/stub, then
         falls through (a misconfigured env var must not silently win).
      2. lib.config data_dir()/thetadata_eod (the repo-local store / symlink).
      3. the ops-host worktree store (_OPS_WT_STORE).

    A candidate resolves unless it is PROVABLY empty — either a stub (exists, no
    eod/ oi/ greeks/ at all) or drained (tier dirs present, no root inside any of
    them). A candidate whose tiers cannot be listed is treated as present, never
    as drained: see _has_store_content, which fails open by construction. A
    candidate on an unmounted volume (`_UNMOUNTED`) is refused and the chain
    stops — later candidates are not tried.

    Args:
        required: when True and nothing resolves, raise RuntimeError naming
                  every path tried and the purpose. Builders that would
                  otherwise publish empty/suppressed artifacts should either
                  pass required=True or exit nonzero themselves on None.
        purpose:  short caller tag, included in every log line.

    Returns the resolved store root Path, or None (required=False only).
    """
    candidates = _store_candidates()
    env = os.environ.get("THETADATA_STORE")

    tried: list[str] = []
    drained: list[str] = []
    unmounted_vols: list[str] = []
    for source, path in candidates:
        verdict = _classify_store(path)
        if verdict in _RESOLVABLE:
            if verdict == _UNKNOWN:
                # Fail-open is correct, but SILENT fail-open is exactly how the
                # blank-board incident repeats: if the M1's tier dirs cannot be
                # listed under launchd this is the branch that runs, the drained
                # store resolves, and a blank brief publishes with exit 0. This
                # annotation is the only thing that makes that visible. Bare
                # print at line start + flush: a logger prefixes the line and
                # GitHub silently drops the annotation (tests/test_gh_annotation_line_start.py).
                print(f"::warning title=thetadata-store-unverified::"
                      f"resolved {path} (source={source}, purpose={purpose or '-'}) "
                      f"WITHOUT verifying its tier dirs are readable. If this store "
                      f"is drained, the artifact built from it will be blank.",
                      flush=True)
            log.info("thetadata_store: resolved store=%s source=%s purpose=%s%s",
                     path, source, purpose or "-",
                     " (readability unverified — see the warning above)"
                     if verdict == _UNKNOWN else "")
            return path

        if verdict == _UNMOUNTED:
            # Any source. Stop the chain: falling through would let a writer
            # mint a second store on a different disk.
            try:
                vol = _unmounted_volume(path)
            except OSError:
                vol = None
            vol_s = str(vol) if vol is not None else str(path)
            unmounted_vols.append(vol_s)
            log.error(
                "thetadata_store: %s=%s is on unmounted volume %s — refusing "
                "this store and not falling through to a later candidate "
                "(purpose=%s)",
                source, path, vol_s, purpose or "-")
            tried.append(f"{source}:{path}")
            break

        if verdict == _DRAINED:
            # AD-1T2b: two failures an operator must treat differently. "No store
            # on this host" is a PLACEMENT fault — move the job. "The store is
            # here but drained" is a DATA fault, and which remedy applies depends
            # on WHICH candidate is drained, so state the observation and the
            # candidate rather than prescribing a fix for all three.
            drained.append(f"{source}:{path}")
            log.error(
                "thetadata_store: %s=%s EXISTS with tier directories but holds "
                "ZERO roots — a DRAINED store, not a missing one (purpose=%s). "
                "If this is the canonical store, moving the job to another host "
                "cannot fix it: the bytes have to be rewritten, and after this "
                "check the daily top-up can no longer bootstrap them, so "
                "scripts/backfill_thetadata_eod.py is the writer that refills it.",
                source, path, purpose or "-")
        elif source == "env":
            if not path.exists():
                log.warning(
                    "thetadata_store: THETADATA_STORE=%s is SET but the path does "
                    "not exist — ignoring the env override and falling through "
                    "(purpose=%s)", env, purpose or "-")
            else:
                # Not drained and not resolvable: the true stub, no tier dirs.
                log.warning(
                    "thetadata_store: THETADATA_STORE=%s exists but contains none "
                    "of eod/ oi/ greeks/ — empty stub, not a store; falling "
                    "through (purpose=%s)", env, purpose or "-")
        tried.append(f"{source}:{path}")

    # The drained fact has to ride on THIS line, not only on the per-candidate
    # ERROR above: scripts/build_options_intel_brief.py captures these records and
    # publishes splitlines()[-1] as its CI annotation, so a diagnostic emitted
    # earlier in the loop never reaches the operator who needs it.
    why = (f" — DRAINED (tier dirs present, zero roots): {', '.join(drained)}"
           if drained else "")
    if unmounted_vols:
        why += "".join(f" — UNMOUNTED: {v}" for v in unmounted_vols)
    log.error("thetadata_store: resolved store=NONE purpose=%s — tried %s%s",
              purpose or "-", ", ".join(tried), why)
    if required:
        raise RuntimeError(
            f"ThetaData store required (purpose={purpose or '-'}) but no path "
            f"resolves. Tried: {', '.join(tried)}. A path resolves unless it is "
            f"provably empty — a store whose tier directories are all present but "
            f"hold no root is DRAINED, not resolvable"
            + (f" (drained: {', '.join(drained)}; refill it with "
               f"scripts/backfill_thetadata_eod.py)" if drained else "")
            + (f" UNMOUNTED: {', '.join(unmounted_vols)}."
               if unmounted_vols else "")
            + ". Set THETADATA_STORE or point the caller at a real store."
        )
    return None


def _default_store_root() -> Path:
    """Resolve the default store root: THETADATA_STORE env, else data/thetadata_eod."""
    env = os.environ.get("THETADATA_STORE")
    if env:
        return Path(env)
    # Try lib.config first; fall back to CWD-relative for hermetic tests
    try:
        from lib import config  # noqa: PLC0415
        return config.data_dir() / "thetadata_eod"
    except Exception:  # noqa: BLE001
        return Path("data") / "thetadata_eod"


# store_root() paths already warned about (once per process, not per read)
_WARNED_MISSING_ROOTS: set[str] = set()


def store_root(override: str | Path | None = None) -> Path:
    """Back-compat wrapper: always returns a Path, which may NOT exist.

    Downstream loaders return empty frames on a missing root, so this warns
    (once per path per process) when the result does not exist. New callers
    should use resolve_thetadata_store(), which fails loud instead of empty.
    """
    p = Path(override) if override is not None else _default_store_root()
    if not p.exists():
        key = str(p)
        if key not in _WARNED_MISSING_ROOTS:
            _WARNED_MISSING_ROOTS.add(key)
            log.warning(
                "thetadata_store.store_root: %s does not exist — parquet reads "
                "will silently return EMPTY frames; prefer "
                "resolve_thetadata_store() for fail-loud resolution", p)
    return p


# --------------------------------------------------------------------------- #
# low-level parquet loader (graceful on missing root/year)                     #
# --------------------------------------------------------------------------- #

def _load_parquets(tier: str, root: str, years: list[int] | None,
                   store: str | Path | None = None) -> pd.DataFrame:
    """Load all parquets for (tier, root), optionally filtered to `years`.
    Missing files are silently skipped (partial store is normal during backfill).

    Results are memoized in _PARQUET_CACHE keyed by the resolved file path string.
    This means consecutive chain() calls for different dates in the same year pay
    one disk read, not N reads.  Call clear_parquet_cache() after a batch run to
    release memory.

    Defensive dedup: full-row drop_duplicates() is applied to each parquet frame
    before caching.  This protects downstream consumers (Phase-B gate runs, backtest
    loops) against parquets written before the 2026-07-05 API-dedup fix landed in
    _normalize_eod_df.  Any rows dropped are logged at WARN level with a pointer to
    the repair script.  The cache stores the already-deduped frame so repeated calls
    pay the dedup cost only once per (tier, root, year) file.  Call
    clear_parquet_cache() after running the repair script to force fresh reads.
    """
    base = store_root(store) / tier / root
    if not base.exists():
        return pd.DataFrame()
    files = sorted(base.glob("*.parquet"))
    if years is not None:
        year_set = {str(y) for y in years}
        files = [f for f in files if f.stem in year_set]
    if not files:
        return pd.DataFrame()
    frames = []
    for f in files:
        key = str(f.resolve())
        if key in _PARQUET_CACHE:
            frames.append(_PARQUET_CACHE[key])
            continue
        try:
            df = pd.read_parquet(f)
            # Defensive dedup before caching: drop full-row duplicates introduced by the
            # ThetaData v3 API (see collectors/thetadata.py _normalize_eod_df docstring).
            # Parquets written before 2026-07-05 may contain duplicates; this ensures all
            # reads are clean regardless of when the file was written.
            n_before = len(df)
            df = df.drop_duplicates()
            n_dropped = n_before - len(df)
            if n_dropped > 0:
                log.warning(
                    "thetadata_store: %s/%s/%s — dropped %d full-row duplicates on load "
                    "(%d → %d rows); run scripts/repair_thetadata_dedup.py --apply to fix "
                    "the parquet on disk",
                    tier, root, f.name, n_dropped, n_before, len(df),
                )
            _PARQUET_CACHE[key] = df
            frames.append(df)
        except Exception as e:  # noqa: BLE001
            log.debug("skip %s: %s", f, e)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _normalise_date(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    """Ensure the date column is a date-only string 'YYYY-MM-DD'."""
    if col not in df.columns:
        return df
    df = df.copy()
    df[col] = pd.to_datetime(df[col]).dt.date.astype(str)
    return df


# --------------------------------------------------------------------------- #
# public API                                                                    #
# --------------------------------------------------------------------------- #

def universe(date: str | None = None, store: str | Path | None = None) -> list[str]:
    """All roots with EOD data. If `date` supplied, only roots with at least one
    row on that date. Graceful on empty store."""
    base = store_root(store) / "eod"
    if not base.exists():
        return []
    roots = [p.name for p in sorted(base.iterdir()) if p.is_dir()]
    if date is None:
        return roots
    # Filter to roots that have a parquet for the year
    year = str(pd.Timestamp(date).year)
    result = []
    for r in roots:
        f = base / r / f"{year}.parquet"
        if f.exists():
            result.append(r)
    return result


def oi_for_date(date: str, root: str,
                store: str | Path | None = None) -> pd.DataFrame:
    """Point-in-time OI rows for one exact ``(date, root)`` without broad caching.

    This is the live-safe narrow reader.  It opens only
    ``oi/{ROOT}/{YEAR}.parquet``, projects the six OI contract columns at read
    time, and applies an exact timestamp predicate before normalising the small
    selected frame.  It deliberately bypasses ``_load_parquets`` and never reads
    or mutates ``_PARQUET_CACHE``: a long-lived intraday process must not retain
    full-year EOD/OI/greeks frames merely to obtain prior-session OI.

    Defensive full-row dedup remains in force for pre-2026-07-05 parquets.  A
    missing root, year, date, or malformed file returns the stable empty shape;
    partial historical stores are normal while backfill is in progress.
    """
    if not isinstance(date, str) or _CANONICAL_DATE_RE.fullmatch(date) is None:
        raise ValueError("date must be canonical YYYY-MM-DD")
    try:
        stamp = pd.Timestamp(date)
    except Exception as exc:  # noqa: BLE001 — normalise parser errors to the public contract
        raise ValueError("date must be a real canonical YYYY-MM-DD date") from exc
    if stamp.date().isoformat() != date:
        raise ValueError("date must be a real canonical YYYY-MM-DD date")
    date_str = stamp.date().isoformat()
    root_key = root.upper()
    path = store_root(store) / "oi" / root_key / f"{stamp.year}.parquet"
    if not path.is_file():
        return pd.DataFrame(columns=_OI_COLUMNS)

    try:
        frame = pd.read_parquet(
            path,
            columns=list(_OI_COLUMNS),
            filters=[("date", "==", stamp), ("root", "==", root_key)],
        )
    except Exception as exc:  # noqa: BLE001 — partial/corrupt store degrades to absent OI
        log.debug("skip %s: %s", path, exc)
        return pd.DataFrame(columns=_OI_COLUMNS)

    if frame.empty:
        return pd.DataFrame(columns=_OI_COLUMNS)

    # Re-prove the exact date after the parquet predicate.  This is both a
    # defensive engine-compatibility fence and the canonical string date shape
    # used by the rest of this store API.
    frame = _normalise_date(frame)
    frame = frame[
        (frame["date"] == date_str)
        & (frame["root"].astype(str).str.upper() == root_key)
    ].copy()
    if frame.empty:
        return pd.DataFrame(columns=_OI_COLUMNS)

    n_before = len(frame)
    frame = frame.drop_duplicates().reset_index(drop=True)
    n_dropped = n_before - len(frame)
    if n_dropped > 0:
        log.warning(
            "thetadata_store: oi/%s/%s — dropped %d full-row duplicates on "
            "point-in-time load (%d → %d rows); run "
            "scripts/repair_thetadata_dedup.py --apply to fix the parquet on disk",
            root_key, path.name, n_dropped, n_before, len(frame),
        )
    return frame.loc[:, list(_OI_COLUMNS)]


def eod_matrix_for_date(
    date: str,
    root: str,
    store: str | Path | None = None,
) -> pd.DataFrame:
    """Read one session's projected EOD matrix columns without broad caching.

    This is the EOD companion to :func:`oi_for_date`: it reads only the exact
    root/year shard, projects the fields required for matrix spot fallback and
    current call/put volume, and never touches ``_PARQUET_CACHE``.
    """
    if not isinstance(date, str) or _CANONICAL_DATE_RE.fullmatch(date) is None:
        raise ValueError("date must be canonical YYYY-MM-DD")
    stamp = pd.Timestamp(date)
    if stamp.date().isoformat() != date:
        raise ValueError("date must be a real canonical YYYY-MM-DD date")
    root_key = root.upper()
    path = store_root(store) / "eod" / root_key / f"{stamp.year}.parquet"
    if not path.is_file():
        return pd.DataFrame(columns=_EOD_MATRIX_COLUMNS)

    try:
        frame = pd.read_parquet(
            path,
            columns=list(_EOD_MATRIX_COLUMNS),
            filters=[("date", "==", stamp), ("root", "==", root_key)],
        )
    except Exception as filtered_exc:  # noqa: BLE001
        # Older fixture/store shards may encode date as a string instead of a
        # timestamp.  Preserve projection and post-filtering without falling
        # back to the broad cached loader.
        try:
            frame = pd.read_parquet(path, columns=list(_EOD_MATRIX_COLUMNS))
        except Exception as exc:  # noqa: BLE001
            log.debug("skip %s: filtered=%s fallback=%s", path, filtered_exc, exc)
            return pd.DataFrame(columns=_EOD_MATRIX_COLUMNS)

    if frame.empty:
        return pd.DataFrame(columns=_EOD_MATRIX_COLUMNS)
    frame = _normalise_date(frame)
    frame = frame[
        (frame["date"] == date)
        & (frame["root"].astype(str).str.upper() == root_key)
    ].copy()
    return frame.loc[:, list(_EOD_MATRIX_COLUMNS)].reset_index(drop=True)


def eod_volume_history_before(
    date: str,
    root: str,
    *,
    strike_min: float,
    strike_max: float,
    expiration_max: str,
    date_min: str | None = None,
    store: str | Path | None = None,
) -> pd.DataFrame:
    """Read projected current/prior-year EOD volume rows strictly before date.

    The matrix cohort supplies its current strike and expiration window.  Those
    predicates are pushed into parquet when the shard schema permits, then
    re-proven after reading.  Only six volume-identity columns are materialized,
    and this reader deliberately bypasses ``_PARQUET_CACHE`` so the nightly
    matrix lane cannot retain a second full-year EOD frame.
    """
    if not isinstance(date, str) or _CANONICAL_DATE_RE.fullmatch(date) is None:
        raise ValueError("date must be canonical YYYY-MM-DD")
    stamp = pd.Timestamp(date)
    end_stamp = pd.Timestamp(expiration_max)
    start_stamp = pd.Timestamp(date_min) if date_min is not None else None
    if stamp.date().isoformat() != date or end_stamp.date().isoformat() != expiration_max:
        raise ValueError("date and expiration_max must be real canonical dates")
    if date_min is not None and (
        _CANONICAL_DATE_RE.fullmatch(date_min) is None
        or start_stamp.date().isoformat() != date_min
        or start_stamp >= stamp
    ):
        raise ValueError("date_min must be a real canonical date before date")
    if not np.isfinite(strike_min) or not np.isfinite(strike_max) or strike_min > strike_max:
        raise ValueError("strike window must be finite and ordered")

    root_key = root.upper()
    frames: list[pd.DataFrame] = []
    for year in (stamp.year - 1, stamp.year):
        path = store_root(store) / "eod" / root_key / f"{year}.parquet"
        if not path.is_file():
            continue
        filters = [
            ("root", "==", root_key),
            ("date", "<", stamp),
            ("strike", ">=", float(strike_min)),
            ("strike", "<=", float(strike_max)),
            ("expiration", ">=", stamp),
            ("expiration", "<=", end_stamp),
        ]
        if start_stamp is not None:
            filters.append(("date", ">=", start_stamp))
        try:
            frame = pd.read_parquet(
                path,
                columns=list(_EOD_VOLUME_COLUMNS),
                filters=filters,
            )
        except Exception as filtered_exc:  # noqa: BLE001
            try:
                frame = pd.read_parquet(path, columns=list(_EOD_VOLUME_COLUMNS))
            except Exception as exc:  # noqa: BLE001
                log.debug("skip %s: filtered=%s fallback=%s", path, filtered_exc, exc)
                continue
        if not frame.empty:
            frames.append(frame)

    if not frames:
        return pd.DataFrame(columns=_EOD_VOLUME_COLUMNS)
    frame = _normalise_date(pd.concat(frames, ignore_index=True))
    expiry = pd.to_datetime(frame["expiration"], errors="coerce").dt.date.astype(str)
    strike = pd.to_numeric(frame["strike"], errors="coerce")
    frame = frame[
        (frame["root"].astype(str).str.upper() == root_key)
        & (frame["date"] < date)
        & ((frame["date"] >= date_min) if date_min is not None else True)
        & strike.between(float(strike_min), float(strike_max), inclusive="both")
        & (expiry >= date)
        & (expiry <= expiration_max)
    ].copy()
    frame["expiration"] = expiry.loc[frame.index]
    return frame.loc[:, list(_EOD_VOLUME_COLUMNS)].reset_index(drop=True)


def eod_sessions_before(
    date: str,
    root: str,
    *,
    limit: int,
    store: str | Path | None = None,
) -> list[str]:
    """Return the latest distinct prior root EOD sessions without broad caching."""
    if not isinstance(date, str) or _CANONICAL_DATE_RE.fullmatch(date) is None:
        raise ValueError("date must be canonical YYYY-MM-DD")
    stamp = pd.Timestamp(date)
    if stamp.date().isoformat() != date:
        raise ValueError("date must be a real canonical YYYY-MM-DD date")
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be a positive integer")
    root_key = root.upper()
    frames: list[pd.DataFrame] = []
    for year in (stamp.year - 1, stamp.year):
        path = store_root(store) / "eod" / root_key / f"{year}.parquet"
        if not path.is_file():
            continue
        try:
            frame = pd.read_parquet(
                path,
                columns=list(_EOD_SESSION_COLUMNS),
                filters=[("root", "==", root_key), ("date", "<", stamp)],
            )
        except Exception as filtered_exc:  # noqa: BLE001
            try:
                frame = pd.read_parquet(path, columns=list(_EOD_SESSION_COLUMNS))
            except Exception as exc:  # noqa: BLE001
                log.debug("skip %s: filtered=%s fallback=%s", path, filtered_exc, exc)
                continue
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return []
    frame = _normalise_date(pd.concat(frames, ignore_index=True))
    frame = frame[
        (frame["root"].astype(str).str.upper() == root_key)
        & (frame["date"] < date)
    ]
    return sorted(frame["date"].dropna().astype(str).unique().tolist())[-limit:]


def chain(date: str, root: str,
          store: str | Path | None = None) -> pd.DataFrame:
    """Per-contract frame for (date, root) joining eod + oi (+greeks/IV where present).

    Returns a DataFrame with columns:
      root, expiration, strike, right, date,
      open, high, low, close, volume, count, bid_eod, ask_eod,
      open_interest,                              (from oi, may be NaN)
      implied_vol, delta, theta, vega, rho,       (from greeks, may be NaN)
      iv_error                                    (from greeks, may be NaN)

    OI is NOT shifted here — chain() returns raw point-in-time data.
    Use doi_series() which applies the oi[t-1] law for signal construction.

    Returns empty DataFrame gracefully when root or year is absent.
    """
    year = pd.Timestamp(date).year
    years = [year]

    eod = _load_parquets("eod", root, years, store)
    if eod.empty:
        return pd.DataFrame()
    eod = _normalise_date(eod)
    eod = eod[eod["date"] == date].copy()
    if eod.empty:
        return pd.DataFrame()

    # rename bid/ask to avoid collision with greeks bid/ask
    if "bid" in eod.columns:
        eod = eod.rename(columns={"bid": "bid_eod", "ask": "ask_eod"})

    oi = _load_parquets("oi", root, years, store)
    if not oi.empty:
        oi = _normalise_date(oi)
        oi = oi[oi["date"] == date][
            ["root", "expiration", "strike", "right", "date", "open_interest"]
        ].copy()
        eod = eod.merge(oi, on=["root", "expiration", "strike", "right", "date"],
                        how="left")
    else:
        eod["open_interest"] = np.nan

    greeks = _load_parquets("greeks", root, years, store)
    if not greeks.empty:
        greeks = _normalise_date(greeks)
        greeks = greeks[greeks["date"] == date].copy()
        # greeks may have bid/ask for the bid-ask at greeks snapshot time — keep separately
        gcols = ["root", "expiration", "strike", "right", "date"]
        extra = [c for c in ("implied_vol", "iv_error", "delta", "theta",
                              "vega", "rho", "underlying_price")
                 if c in greeks.columns]
        if extra:
            eod = eod.merge(greeks[gcols + extra], on=gcols, how="left")
        else:
            for c in ("implied_vol", "iv_error", "delta", "theta", "vega", "rho"):
                eod[c] = np.nan
    else:
        for c in ("implied_vol", "iv_error", "delta", "theta", "vega", "rho"):
            eod[c] = np.nan

    return eod.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# ΔOI series with the oi[t-1] law                                              #
# --------------------------------------------------------------------------- #

def doi_series(root: str, put_call: str = "both",
               window: int = 5,
               store: str | Path | None = None) -> pd.DataFrame:
    """Per-date ΔOI (5-session default) for one root, aggregated over all strikes/expiries.

    OI TIMING LAW (cite: LIVE_ORDER_FLOW_BRAINSTORM_BY_FABLE §8 ¶1):
      OPRA reports OI at ~06:30 ET representing end-of-PREVIOUS-day positions.
      We shift(1) so that day-t's signal uses oi[t-1], not oi[t].
      Same-day OI in a day-t signal is a lookahead bug — see §8 ¶1.

    Args:
        root      : option root symbol (e.g. "SPY")
        put_call  : "C" (calls only), "P" (puts only), or "both"
        window    : rolling window for delta (default 5 sessions)
        store     : store root override

    Returns DataFrame indexed by date (str 'YYYY-MM-DD') with columns:
        total_oi  : total open interest across all active contracts
        doi_raw   : total_oi - total_oi.shift(window)  (window-session delta)
        doi_z     : doi_raw normalised by its 63-day rolling std (cross-time z)
    """
    oi_all = _load_parquets("oi", root, None, store)
    if oi_all.empty:
        return pd.DataFrame(columns=["date", "total_oi", "doi_raw", "doi_z"])

    oi_all = _normalise_date(oi_all)
    if put_call in ("C", "P"):
        oi_all = oi_all[oi_all["right"] == put_call]

    daily = (oi_all.groupby("date")["open_interest"].sum()
             .sort_index()
             .rename("total_oi"))

    # CRITICAL: shift(1) — OI at t is reported next morning, so it represents
    # EOD t-1 positions. Using oi[t] for day-t signals would be a lookahead.
    # We shift BEFORE computing the delta so that doi_raw[t] =
    #   oi_as_reported_on_t (=EOD t-1 position) - oi_as_reported_on_{t-window}
    # which is fully known by the start of session t. — LIVE_ORDER_FLOW §8 ¶1
    oi_shifted = daily.shift(1)  # oi[t-1] law

    doi_raw = oi_shifted - oi_shifted.shift(window)
    doi_z = doi_raw / doi_raw.rolling(63, min_periods=21).std()

    out = pd.DataFrame({"total_oi": oi_shifted, "doi_raw": doi_raw, "doi_z": doi_z})
    out.index.name = "date"
    return out.reset_index()


# --------------------------------------------------------------------------- #
# IV coverage                                                                   #
# --------------------------------------------------------------------------- #

def iv_coverage(store: str | Path | None = None) -> dict[str, dict]:
    """Per-root first/last date where greeks IV exists.

    Returns {root: {"first": "YYYY-MM-DD", "last": "YYYY-MM-DD", "n_dates": int}}.
    Empty dict when no greeks data is present at all.

    The vendor greeks history starts LATER than EOD/OI (vendor greeks were
    empty through at least 2015; the exact start year is visible in backfill
    logs as the first 'greeks rows>0' year).
    """
    base = store_root(store) / "greeks"
    if not base.exists():
        return {}
    result = {}
    for root_dir in sorted(base.iterdir()):
        if not root_dir.is_dir():
            continue
        root = root_dir.name
        frames = []
        for f in sorted(root_dir.glob("*.parquet")):
            try:
                df = pd.read_parquet(f, columns=["date", "implied_vol"])
                df = df[df["implied_vol"].notna() & (df["implied_vol"] > 0)]
                if not df.empty:
                    frames.append(_normalise_date(df)[["date"]])
            except Exception as e:  # noqa: BLE001
                log.debug("iv_coverage skip %s: %s", f, e)
        if not frames:
            continue
        all_dates = pd.concat(frames)["date"].unique()
        all_dates = sorted(all_dates)
        result[root] = {
            "first": all_dates[0],
            "last": all_dates[-1],
            "n_dates": len(all_dates),
        }
    return result


# --------------------------------------------------------------------------- #
# chain-provider factory (for refactored skew/ivspread validators)             #
# --------------------------------------------------------------------------- #

def make_chain_provider(
    store: str | Path | None = None,
    require_iv: bool = False,
) -> Callable[[str, str], pd.DataFrame | None]:
    """Return a chain-frame provider that matches the polygon_gex chain schema.

    The returned callable: provider(date_str, root) -> pd.DataFrame | None

    The returned frame has the columns the existing skew/ivspread engines expect:
      underlying, expiry, K, T, iv, delta, is_call, spot, oi, volume, asof

    IV (implied_vol) is sourced from the greeks tier when present; when absent
    and require_iv=False the iv column is NaN (allowing IV-free signals like ΔOI
    to still use this provider). When require_iv=True and IV is absent, returns None.

    NOTE on spot: the ThetaData EOD store has no separate underlying_price column
    in the eod tier; we derive spot from the volume-weighted mid strike (the strike
    at maximum total volume), which is an approximation. When greeks are present,
    underlying_price from the greeks tier is used as the authoritative spot.
    """
    def provider(date_str: str, root: str) -> pd.DataFrame | None:
        df = chain(date_str, root, store=store)
        if df.empty:
            return None

        # spot: prefer greeks underlying_price; fall back to volume-weighted strike
        if "underlying_price" in df.columns and df["underlying_price"].notna().any():
            spot = float(df["underlying_price"].dropna().median())
        else:
            total_vol = df.groupby("strike")["volume"].sum()
            spot = float(total_vol.idxmax()) if not total_vol.empty else float("nan")

        if np.isnan(spot) or spot <= 0:
            return None

        # map right → is_call
        df = df.copy()
        df["is_call"] = df["right"].str.upper() == "C"

        # compute T (years to expiry from this date)
        dt_date = pd.Timestamp(date_str)
        df["expiry"] = pd.to_datetime(df["expiration"]).dt.date.astype(str)
        df["T"] = (pd.to_datetime(df["expiry"]) - dt_date).dt.days / 365.0
        df["T"] = df["T"].clip(lower=0.0)

        # IV: from greeks tier if present; NaN otherwise
        if "implied_vol" in df.columns:
            df["iv"] = pd.to_numeric(df["implied_vol"], errors="coerce")
        else:
            df["iv"] = np.nan

        if require_iv and df["iv"].isna().all():
            return None

        # OI: raw point-in-time (caller applies oi[t-1] law at the signal level)
        df["oi"] = pd.to_numeric(df.get("open_interest", np.nan), errors="coerce")

        df["K"] = pd.to_numeric(df["strike"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df["underlying"] = root
        df["spot"] = spot
        df["asof"] = date_str

        keep = ["underlying", "expiry", "K", "T", "iv", "delta", "is_call",
                "spot", "oi", "volume", "asof"]
        # delta may come from greeks; otherwise NaN
        if "delta" not in df.columns:
            df["delta"] = np.nan
        else:
            df["delta"] = pd.to_numeric(df["delta"], errors="coerce")

        return df[[c for c in keep if c in df.columns]].reset_index(drop=True)

    return provider
