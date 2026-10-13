"""Grey Deer pullback stage-1b: pooled 14-ticker panel runner (W4, D1–D13).

Reuses ``grey_deer_pullback_stage1`` by call. Stage 1 is one SPY close
series: its loader, its row-index fit, its comparison-set index, its
bootstrap seed (221011) and its event definition do not describe a panel.
Those pieces are panel functions below. Everything that is the same
science — labels, features, purge predicate, fold arithmetic, logistic
and quantile fits, intersection of issued masks, block length, draw
statistics, quantile bounds, leave-one-episode-out and the 12-claim
gate — is a stage-1 function.

Prereg v1.1 is FROZEN: the identity pins, the trial budget (66) and the
manifest/prereg blob pins below are filled from the seat's ``--blocks-only``
pass over the pinned Massive store. A pin put back to ``PREREG_V11_PENDING``
still refuses a run before any feature, label or outcome. A real run
registers family ``grey_deer_pullback_v11`` (budget 66, itemized) in the
checkout's ``data/trial_ledger.jsonl`` before any outcome is computed and
refuses when that file is absent (a sparse worktree: opt in with
``python3 scripts/worktree_sparse.py add data``). ``--blocks-only`` and every
refusal never touch the ledger.

Decisions implemented:

* D1  stage-1 target, configurations, fold constants, purge, metrics
* D2  14 tickers, SPY excluded, window 2021-07-06..2026-10-07, no trim
* D3  common axis = intersection per D15, pinned exclusion ``2026-08-18``;
      any other difference is ``CALENDAR_MISALIGNED`` (never forward-filled)
* D4  per-ticker normalized-subframe pins; pending refuses first
* D5  pinned splits adjusted per D14 (table in
      ``grey_deer_panel_adjust.PINNED_SPLITS``); dividends unadjusted;
      a remaining break on adjusted closes is ``SPLIT_DISCONTINUITY``
* D6  pooled training is the union of date-purged rows; no ticker feature
* D7  intersection-of-issued on ``(ticker, date)``
* D8  circular block bootstrap on the DATE index, seed root 221012
* D9  event date = any ticker with Y=1; LOEO drops that date everywhere
* D10 12 claims; P-active ``OBSERVER_NOT_ON_MAIN``; INC ``NOT_APPLICABLE``
* D11 family ``grey_deer_pullback_v11``; budget 66 (22 × 3, INC removed
      from v1's 23), frozen with prereg v1.1 and registered before outcomes
* D12 schema ``grey_deer_pullback_stage1b/v1``; ``main`` writes only under
      the directory it was given
* D13 pending pins / budget refuse before any panel outcome
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine import trial_ledger
from scripts.research import grey_deer_pullback_stage1 as s1
from scripts.research.grey_deer_panel_adjust import (
    PINNED_CALENDAR_EXCLUSIONS,
    PINNED_SPLITS,
    prepare_panel,
)

# ── seat constants (D2, D4, D5, D8, D11, D12) ────────────────────────────────

PANEL_TICKERS = (
    "QQQ",
    "IWM",
    "DIA",
    "XLB",
    "XLC",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLRE",
    "XLU",
    "XLV",
    "XLY",
)
WINDOW_START = s1.WINDOW_START
AS_OF = s1.AS_OF
PIN_PENDING = "PREREG_V11_PENDING"
SEED_ROOT = 221012
N_DRAWS = s1.N_DRAWS
SCHEMA = "grey_deer_pullback_stage1b/v1"
TRIAL_FAMILY = "grey_deer_pullback_v11"
# v1 §6 counts 23 per horizon including INC. D11 drops INC (SPY-only incumbent):
# 22 per horizon, 66 in total. Frozen with prereg v1.1 (checklist (c)).
TRIALS_PER_HORIZON = 22
TRIALS_TOTAL = 66
TRIAL_BUDGET = 66
DEFAULT_OUT_DIR = "research/grey_deer/pullback_stage1b"
RESULTS_JSON_NAME = "PULLBACK_STAGE1B_RESULTS.json"
RESULTS_MD_NAME = "PULLBACK_STAGE1B_RESULTS.md"
DIVIDEND_BASIS = "unadjusted"
DIVIDEND_DISCLOSURE = (
    "Pinned splits are adjusted per D14 "
    "(table in grey_deer_panel_adjust.PINNED_SPLITS). "
    "Dividends are unadjusted. "
    "The common axis is the intersection per D15 "
    "with pinned exclusion 2026-08-18."
)
# D15. The seat's intersection of the 14 tickers over the frozen window.
EXPECTED_COMMON_SESSIONS = 1320
MANIFEST_PATH = "research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_V1_1_2026-10-12.md"
MANIFEST_VERSION = "1.1.0"
MANIFEST_BLOB_SHA = "c52d93e98f4e4a776a7cf38fce46bcf4a84c52d7"
PREREG_PATH = "research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md"
PREREG_BLOB_SHA = "53837859164ab1d33785101dc0b464272acd5704"
SCRIPT_REL = "scripts/research/grey_deer_pullback_stage1b.py"
TEST_REL = "tests/test_grey_deer_pullback_stage1b.py"
ADJUST_REL = "scripts/research/grey_deer_panel_adjust.py"
_EXCLUDED_SESSION = "2026-08-18"


def _pending_pin() -> dict:
    return {
        "subframe_sha256": PIN_PENDING,
        "rows": PIN_PENDING,
        "first_date": PIN_PENDING,
        "last_date": PIN_PENDING,
    }


# Prereg v1.1 §3, copied from the seat's --blocks-only PIN lines over the
# pinned Massive store (manifest v1.1.0 §4). ``_pending_pin`` stays for the
# refusal tests.
IDENTITY_PINS: dict[str, dict] = {
    "QQQ": {
        "subframe_sha256": "d6bd7575c5db3f0fb5d63e6baa2892a5a9d3610a8885562f8ead677a4444373f",
        "rows": 1320,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "IWM": {
        "subframe_sha256": "ca2df002ee03ed68c19cd77e73b702c057be11f92435936b1f7d4fd57e218b8b",
        "rows": 1320,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "DIA": {
        "subframe_sha256": "f11d142d015fca21c404e4a96524791d17ecaee4eb08f489f620ac47a753d618",
        "rows": 1321,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLB": {
        "subframe_sha256": "0863d459e79a40b0943b2ced0aeea42801e81d9a989b8df07823ee6445055628",
        "rows": 1321,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLC": {
        "subframe_sha256": "121c9b52c6ef4231540b73ad15362cf5927e7e5ae3c8df073ae231cbd158374d",
        "rows": 1321,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLE": {
        "subframe_sha256": "ebf4be8c9f7f53b2472b1a032d5f105f7ed5ce7f439411f468b6435939176ba3",
        "rows": 1320,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLF": {
        "subframe_sha256": "da3a5aa47a06f469dd6a99288e7be423ff63e9a8b9dc10d6832dc7a4af5b1491",
        "rows": 1320,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLI": {
        "subframe_sha256": "d153ab22f333d536bdf7c8ef84c981b9c5614e8f62969687d765f043e35e596c",
        "rows": 1320,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLK": {
        "subframe_sha256": "7dc854d1e340f1619340c1c26c9be4cc17fd0c925a0bbe036c74c058d53d0e63",
        "rows": 1321,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLP": {
        "subframe_sha256": "a480545513732922a2be49c2cf807f7500baf923beb909cdf8d59eae70ef885b",
        "rows": 1320,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLRE": {
        "subframe_sha256": "c578f88c142f67a237f45a324097fc912c6994abd2aaa355080b5e94ca41fcae",
        "rows": 1320,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLU": {
        "subframe_sha256": "238dbbd6d68fa71ae074020ad83a2bbc4ffcd0a45cc087ca1982d56fb4a5b2f1",
        "rows": 1320,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLV": {
        "subframe_sha256": "64f9d9b448b7e93b9e11137db11d9860c1c61d4682b0c685f43a6ff73db5d251",
        "rows": 1321,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
    "XLY": {
        "subframe_sha256": "870fa4c0b19e31d5ef33b2d0702b9e9815b89285f3e3eb925434afb36b758ed5",
        "rows": 1320,
        "first_date": "2021-07-06",
        "last_date": "2026-10-07",
    },
}


def _refuse(type_: str, detail: str, **extra) -> None:
    err = s1.Blocked(type_, detail)
    for key, value in extra.items():
        setattr(err, key, value)
    raise err


def freeze_block_reason() -> str | None:
    """D4 + D11. Pending pins or a pending budget block a real run.

    Returned text is None only when every pin field is a real value and
    ``TRIAL_BUDGET`` is no longer the literal ``PREREG_V11_PENDING``.
    """
    pending_pins: list[str] = []
    for ticker in PANEL_TICKERS:
        pin = IDENTITY_PINS.get(ticker)
        if not isinstance(pin, dict):
            pending_pins.append(ticker)
            continue
        for field, value in pin.items():
            if value == PIN_PENDING:
                pending_pins.append(f"{ticker}.{field}")
    budget_pending = TRIAL_BUDGET == PIN_PENDING
    manifest_pending = MANIFEST_BLOB_SHA == PIN_PENDING
    prereg_pending = PREREG_BLOB_SHA == PIN_PENDING
    if not pending_pins and not budget_pending and not manifest_pending and not prereg_pending:
        return None
    parts: list[str] = []
    if pending_pins:
        shown = ", ".join(pending_pins[:6])
        more = f" (+{len(pending_pins) - 6} more)" if len(pending_pins) > 6 else ""
        parts.append(f"identity pins hold {PIN_PENDING} ({shown}{more})")
    if budget_pending:
        parts.append(
            f"TRIAL_BUDGET is {PIN_PENDING} "
            f"({TRIALS_PER_HORIZON} per horizon, {TRIALS_TOTAL} total, INC removed; not frozen)"
        )
    if manifest_pending:
        parts.append(
            f"MANIFEST_BLOB_SHA is {PIN_PENDING} ({MANIFEST_PATH} version {MANIFEST_VERSION})"
        )
    if prereg_pending:
        parts.append(f"PREREG_BLOB_SHA is {PIN_PENDING} ({PREREG_PATH})")
    return "; ".join(parts)


def _raise_if_unfrozen() -> None:
    reason = freeze_block_reason()
    if reason is not None:
        _refuse("PREREG_V11_PENDING", reason)


def trial_ledger_scope(ledger_path: Path | None = None) -> trial_ledger.register_trials:
    """Prereg v1.1 §6: register the v11 family before any outcome is computed.

    The ledger is the checkout's own ``data/trial_ledger.jsonl`` (never the
    process cwd). A missing file means a sparse worktree; appending there
    would create a one-row file that replaces the committed ledger, so the
    run refuses instead.
    """
    _raise_if_unfrozen()
    path = ledger_path if ledger_path is not None else ROOT / trial_ledger.DEFAULT_PATH
    if not path.is_file():
        raise RuntimeError(
            f"{path} is absent; the trial family cannot be registered. "
            "Opt this checkout into data/ with `python3 scripts/worktree_sparse.py add data`."
        )
    return trial_ledger.register_trials(
        family=TRIAL_FAMILY,
        budget=TRIAL_BUDGET,
        basis="itemized",
        ledger=trial_ledger.TrialLedger(path),
    )


# ── D2–D5: load the panel ────────────────────────────────────────────────────


def _normalize_ticker(ticker: str, path: Path) -> pd.DataFrame:
    """Stage-1 normalize/sha recipe, applied to one ticker file.

    ``normalize_subframe`` is the frozen identity recipe (dates through
    ``AS_OF`` on the stage-1 constant, identity columns, sorted). The panel
    does not grow a second hash function.
    """
    try:
        raw = pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001 — unreadable input is a coverage refusal
        _refuse("PANEL_COVERAGE", f"{ticker} unreadable ({type(exc).__name__}: {exc})")
    if raw is None or len(raw) == 0:
        _refuse("PANEL_COVERAGE", f"{ticker} has no rows")
    try:
        sub = s1.normalize_subframe(raw)
    except Exception as exc:  # noqa: BLE001 — a frame that cannot be normalised does not cover
        _refuse("PANEL_COVERAGE", f"{ticker} subframe refused ({type(exc).__name__}: {exc})")
    if sub is None or len(sub) == 0:
        _refuse("PANEL_COVERAGE", f"{ticker} has no rows on or before {s1.AS_OF}")
    dupes = sorted(sub.loc[sub["date"].duplicated(), "date"].unique().tolist())
    if dupes:
        _refuse(
            "CALENDAR_MISALIGNED",
            f"{ticker} duplicate session dates: {', '.join(dupes[:8])}",
            symmetric_difference=dupes,
            ticker=ticker,
        )
    return sub


def _coverage_refusal(ticker: str, sub: pd.DataFrame) -> None:
    """D2: a late first row refuses. The runner never trims the window start.

    Rows strictly before ``WINDOW_START`` are outside the frozen window (v1
    drops them after the identity hash). A first row after the window start,
    or a last row before the window end, is ``PANEL_COVERAGE``.
    """
    first = str(sub["date"].iloc[0])
    last = str(sub["date"].iloc[-1])
    if first > WINDOW_START:
        _refuse(
            "PANEL_COVERAGE",
            f"{ticker} first date {first} is after window start {WINDOW_START}; not trimming",
            ticker=ticker,
            date=first,
        )
    if last < AS_OF:
        _refuse(
            "PANEL_COVERAGE",
            f"{ticker} last date {last} is before window end {AS_OF}",
            ticker=ticker,
            date=last,
        )


def _close_array(frame: pd.DataFrame, ticker: str) -> np.ndarray:
    close = frame["close"].to_numpy(dtype=float)
    bad = ~np.isfinite(close) | (close <= 0)
    if bad.any():
        i = int(np.argmax(bad))
        _refuse("PRICE_INVALID", f"{ticker} non-positive or non-finite close at {frame['date'].iloc[i]}")
    return close


def _verify_filled_pins(normalized: dict[str, pd.DataFrame]) -> None:
    """D4: a filled pin must match stage-1's normalized subframe, byte for byte."""
    for ticker in PANEL_TICKERS:
        sub = normalized[ticker]
        sha = s1.subframe_sha256(sub)
        pin = IDENTITY_PINS[ticker]
        got = {
            "subframe_sha256": sha,
            "rows": str(len(sub)),
            "first_date": str(sub["date"].iloc[0]),
            "last_date": str(sub["date"].iloc[-1]),
        }
        want = {field: str(pin[field]) for field in got}
        if got != want:
            _refuse(
                "SAMPLE_IDENTITY_MISMATCH",
                f"{ticker} pin {want} != computed {got}; not re-hashed into agreement",
                ticker=ticker,
            )


@dataclass
class LoadedPanel:
    """Adjusted intersection frames plus the raw identity hashes.

    ``raw`` is the normalized subframe hashed before any split adjustment.
    ``frames`` is ``prepare_panel``'s adjusted intersection.
    """

    frames: dict[str, pd.DataFrame]
    calendar: list[str]
    raw: dict[str, pd.DataFrame]
    subframe_sha256: dict[str, str]


def _known_hashes(normalized: dict[str, pd.DataFrame]) -> dict[str, str]:
    """Stage-1 subframe hash of each raw normalized frame already in hand."""
    out: dict[str, str] = {}
    for ticker in PANEL_TICKERS:
        frame = normalized.get(ticker)
        if frame is None:
            out[ticker] = "UNKNOWN: ticker not normalized"
        else:
            out[ticker] = s1.subframe_sha256(frame)
    return out


def _prepare_block_message(result) -> str:
    """Name the first ticker and date carried by a ``prepare_panel`` refusal."""
    detail = result.detail or {}
    for row in detail.get("mismatches") or []:
        return f"{row.get('ticker')} {row.get('date')}"
    for row in detail.get("breaks") or []:
        return f"{row.get('ticker')} {row.get('date')}"
    missing = detail.get("missing_by_ticker") or {}
    if missing:
        ticker = sorted(missing)[0]
        dates = list(missing[ticker])
        return f"{ticker} {dates[0] if dates else 'unknown-date'}"
    unexpected = list(detail.get("unexpected") or [])
    if unexpected:
        return f"calendar {unexpected[0]}"
    absent = list(detail.get("pinned_absent") or [])
    if absent:
        return f"pinned exclusion {absent[0]}"
    return str(result.reason)


def nyse_sessions(start, end) -> list[str]:
    """NYSE session dates in the inclusive range, as ISO strings.

    The import stays inside the function. ``lib.nyse_calendar`` may import
    ``lib.config``, and that needs pyyaml; tests replace this function.
    """
    import lib.nyse_calendar as nyse_calendar

    start_d = start if isinstance(start, date) else date.fromisoformat(str(start)[:10])
    end_d = end if isinstance(end, date) else date.fromisoformat(str(end)[:10])
    sessions = nyse_calendar.sessions_between(start_d, end_d)
    return [session.isoformat() for session in sessions]


def _check_common_sessions(calendar: list[str]) -> None:
    """D15: the intersection must be the pinned length and the NYSE list."""
    got = len(calendar)
    if got != EXPECTED_COMMON_SESSIONS:
        _refuse(
            "CALENDAR_MISALIGNED",
            f"common sessions {got} != expected {EXPECTED_COMMON_SESSIONS}",
            expected=EXPECTED_COMMON_SESSIONS,
            got=got,
        )
    observed = sorted(set(calendar) | set(PINNED_CALENDAR_EXCLUSIONS))
    expected = nyse_sessions(date(2021, 7, 6), date(2026, 10, 7))
    if observed != expected:
        unexpected = sorted(set(observed) - set(expected))
        missing = sorted(set(expected) - set(observed))
        _refuse(
            "CALENDAR_MISALIGNED",
            (
                "panel calendar plus pinned exclusions does not match the NYSE list "
                f"({len(unexpected)} unexpected, {len(missing)} missing)"
            ),
            unexpected=unexpected,
            missing=missing,
        )


def _load_panel_body(
    paths: dict[str, Path],
    normalized: dict[str, pd.DataFrame],
    state: dict,
    *,
    check_freeze: bool,
) -> LoadedPanel:
    missing = [t for t in PANEL_TICKERS if t not in paths or not Path(paths[t]).is_file()]
    if missing:
        _refuse("PANEL_COVERAGE", "missing tickers: " + ", ".join(missing), tickers=missing)

    for ticker in PANEL_TICKERS:
        sub = _normalize_ticker(ticker, Path(paths[ticker]))
        _coverage_refusal(ticker, sub)
        normalized[ticker] = sub

    # Identity bytes are the raw normalized subframe. Adjustment is next,
    # and it copies; ``normalized`` stays the pin input.
    result = prepare_panel(
        normalized,
        WINDOW_START,
        AS_OF,
        splits=PINNED_SPLITS,
        excluded=PINNED_CALENDAR_EXCLUSIONS,
    )
    if result.status != "OK":
        _refuse(result.reason, _prepare_block_message(result), **result.detail)
    if result.frames is None or result.calendar is None:
        _refuse("CALENDAR_MISALIGNED", "prepare_panel returned OK without a calendar")

    state["calendar"] = list(result.calendar)
    _check_common_sessions(state["calendar"])
    for ticker in PANEL_TICKERS:
        _close_array(result.frames[ticker], ticker)

    # D4 / D11 / D13. After the frame is a panel, before features or labels.
    # ``--blocks-only`` skips this so a pending pin can still be recorded.
    if check_freeze:
        _raise_if_unfrozen()
        _verify_filled_pins(normalized)

    return LoadedPanel(
        frames=result.frames,
        calendar=state["calendar"],
        raw=normalized,
        subframe_sha256=_known_hashes(normalized),
    )


def load_panel(paths: dict[str, Path], *, check_freeze: bool = True) -> LoadedPanel:
    """Load the 14 ticker parquets. Refusals raise ``s1.Blocked``.

    Order: coverage, then ``prepare_panel`` (D14 pinned splits, D15
    intersection), then the common-session count and the NYSE list, then
    the non-positive close check on adjusted closes. Those steps read
    prices and refuse; they do not build a feature, a label or an outcome.
    The pending-pin check, when ``check_freeze`` is set, is still before
    any feature, label or outcome. The hash is the raw normalized subframe.
    """
    normalized: dict[str, pd.DataFrame] = {}
    state: dict = {"calendar": None}
    try:
        return _load_panel_body(paths, normalized, state, check_freeze=check_freeze)
    except s1.Blocked as exc:
        if not hasattr(exc, "subframe_sha256"):
            exc.subframe_sha256 = _known_hashes(normalized)
        if not hasattr(exc, "fold_block_table") and state["calendar"] is not None:
            exc.fold_block_table = block_table(state["calendar"])
        raise


# ── D1 / D6: folds and pooled fits ───────────────────────────────────────────


def panel_fold_calendar(n_dates: int, h: int) -> list[tuple[int, int]]:
    """Stage-1 fold calendar on the common DATE axis (D1).

    ``fold_calendar_for_population`` takes one series' length. Every ticker
    shares the session index, so that length is ``n_dates`` and the same
    warm-up, first test index, block length and final-block rule apply.
    The returned ``(start, end)`` pair is inclusive, matching stage 1.
    """
    return s1.fold_calendar_for_population(int(n_dates), int(h))


def block_table(calendar: list[str]) -> list[dict]:
    """One row per horizon and fold. Dates only: no feature, label or outcome.

    ``end_index`` is the inclusive end from ``panel_fold_calendar``.
    ``after_excluded_session`` is true when the fold starts after the
    pinned exclusion ``2026-08-18``.
    """
    rows: list[dict] = []
    n_dates = len(calendar)
    for h in s1.HORIZONS:
        folds = panel_fold_calendar(n_dates, h)
        for fold, (start, end) in enumerate(folds, start=1):
            start_date = calendar[int(start)]
            end_date = calendar[int(end)]
            rows.append(
                {
                    "h": int(h),
                    "fold": int(fold),
                    "start_index": int(start),
                    "end_index": int(end),
                    "start_date": start_date,
                    "end_date": end_date,
                    "after_excluded_session": start_date > _EXCLUDED_SESSION,
                }
            )
    return rows


def _block_line(row: dict) -> str:
    return (
        "BLOCK "
        f"h={row['h']} fold={row['fold']} "
        f"start_index={row['start_index']} end_index={row['end_index']} "
        f"start_date={row['start_date']} end_date={row['end_date']} "
        f"after_excluded_session={str(bool(row['after_excluded_session'])).lower()}"
    )


def training_date_indices(n_dates: int, s0: int, h: int) -> np.ndarray:
    """Warm, mature, purged positions on the shared date index.

    The purge predicate is stage-1's ``purged_training_indices``: admit
    ``t`` only when ``idx(t) + h <= idx(s0)``. The index is the common
    DATE axis, not a position inside one ticker's stacked rows.
    """
    idx = np.arange(int(n_dates))
    candidates = idx[(idx >= s1.WARM_IDX) & (idx < int(s0)) & (idx <= int(n_dates) - 1 - int(h))]
    return s1.purged_training_indices(int(s0), int(h), candidates)


def training_union(n_dates: int, tickers, s0: int, h: int) -> list[tuple[str, int]]:
    """Pooled training keys ``(ticker, date_index)``.

    A date inside the purge gap is absent for every ticker. Stage-1 purges
    one series; applying that date predicate to each member of the union
    is what drops another ticker's in-gap row (D6). Stacking rows first
    and purging by stacked position would keep that row.
    """
    kept = training_date_indices(n_dates, s0, h)
    return [(str(ticker), int(i)) for ticker in tickers for i in kept]


def _y_array(Y: pd.Series) -> np.ndarray:
    return Y.to_numpy(dtype=float, na_value=np.nan)


def _stacked_design(features, names: tuple[str, ...], train_idx, test_idx, tickers):
    """Scale-free feature matrix. No ticker column is appended (D6)."""
    train_cols = [
        np.concatenate([features[t][name].to_numpy(dtype=float)[train_idx] for t in tickers])
        for name in names
    ]
    X_tr = np.column_stack(train_cols)
    X_te_parts = [
        np.column_stack([features[t][name].to_numpy(dtype=float)[test_idx] for name in names])
        for t in tickers
    ]
    return X_tr, X_te_parts


def _split_rows(values: np.ndarray, tickers, n_te: int) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    offset = 0
    for ticker in tickers:
        out[ticker] = np.asarray(values[offset : offset + n_te])
        offset += n_te
    return out


def _blank(tickers, n_te: int, reason: str) -> tuple[dict, dict]:
    issued = {t: np.zeros(n_te, dtype=bool) for t in tickers}
    reasons = {t: np.full(n_te, reason, dtype=object) for t in tickers}
    return issued, reasons


def _issued_all(tickers, n_te: int) -> tuple[dict, dict]:
    issued = {t: np.ones(n_te, dtype=bool) for t in tickers}
    reasons = {t: np.full(n_te, None, dtype=object) for t in tickers}
    return issued, reasons


def fit_configurations_on_block(features, y_by, a_by, train_idx, test_idx, tickers) -> dict:
    """One pooled fit for one test block.

    Training rows are the union, over tickers, of ``train_idx`` (the
    date-purged common index). Standardisation uses that pooled training
    matrix (stage-1 ``_standardise``, ddof 0). Predictions are split back
    per ticker and line up with ``test_idx``, so each forecast is a
    ``(ticker, date)`` pair. Configurations, logistic, Q0/Q1/Q3 and the
    crossing-then-clip rule are stage-1 functions.

    Stage-1 ``run_fits`` cannot be called: it takes one close series and
    indexes one row position.
    """
    train_idx = np.asarray(train_idx, dtype=int)
    test_idx = np.asarray(test_idx, dtype=int)
    n_te = int(len(test_idx))
    y_tr = np.concatenate([np.asarray(y_by[t], dtype=float)[train_idx] for t in tickers])
    a_tr = np.concatenate([np.asarray(a_by[t], dtype=float)[train_idx] for t in tickers])
    rv_tr = np.concatenate([features[t]["rv20"].to_numpy(dtype=float)[train_idx] for t in tickers])
    rv_te = np.concatenate([features[t]["rv20"].to_numpy(dtype=float)[test_idx] for t in tickers])
    thin, stats = s1.training_fold_is_thin(np.arange(len(y_tr)), y_tr)
    by_config: dict[str, dict] = {}
    q1_fallbacks: list[dict] = []

    for cfg in s1.CONFIGURATIONS:
        names = tuple(cfg["features"])
        record: dict = {
            "config": cfg["id"],
            "kind": cfg["kind"],
            "feature_names": names,
            "population": "P-all",
        }
        if thin and cfg["id"] != "B0":
            issued, reasons = _blank(tickers, n_te, "TRAINING_FOLD_THIN")
            record["issued"] = issued
            record["reasons"] = reasons
            by_config[cfg["id"]] = record
            continue
        try:
            if cfg["id"] == "B0":
                p0 = s1.fit_b0(y_tr)
                issued, reasons = _issued_all(tickers, n_te)
                record["p"] = {t: np.full(n_te, p0) for t in tickers}
                record["issued"] = issued
                record["reasons"] = reasons
            elif cfg["kind"] == "binary":
                X_tr, X_te_parts = _stacked_design(features, names, train_idx, test_idx, tickers)
                X_te = np.vstack(X_te_parts)
                _mean, std, X_tr_s, X_te_s = s1._standardise(X_tr, X_te)
                if (std == 0).any():
                    issued, reasons = _blank(tickers, n_te, "FEATURE_DEGENERATE")
                    record["issued"] = issued
                    record["reasons"] = reasons
                    by_config[cfg["id"]] = record
                    continue
                design_tr = np.column_stack([np.ones(len(X_tr_s)), X_tr_s])
                design_te = np.column_stack([np.ones(len(X_te_s)), X_te_s])
                beta = s1.fit_logistic(design_tr, y_tr, float(cfg["params"]["C"]))
                p_hat = expit(design_te @ beta)
                issued, reasons = _issued_all(tickers, n_te)
                record["p"] = _split_rows(p_hat, tickers, n_te)
                record["issued"] = issued
                record["reasons"] = reasons
                if cfg["id"] == "M3-ALL":
                    try:
                        p_shift = s1.fit_shifted_binary_block(X_tr, y_tr, X_te)
                        record["p_shift"] = _split_rows(p_shift, tickers, n_te)
                        record["shift_issued"] = True
                    except s1._FitFailure:
                        record["shift_issued"] = False
            elif cfg["id"] == "Q0":
                q0 = s1.fit_q0(a_tr)
                issued, reasons = _issued_all(tickers, n_te)
                record["q"] = {
                    t: {str(tau): np.full(n_te, q0[tau]) for tau in s1.TAUS} for t in tickers
                }
                record["issued"] = issued
                record["reasons"] = reasons
            elif cfg["id"] == "Q1":
                q0 = s1.fit_q0(a_tr)
                preds, fb = s1.fit_q1(rv_tr, a_tr, rv_te, q0)
                if fb.get("fallback_cells"):
                    q1_fallbacks.append(fb)
                issued, reasons = _issued_all(tickers, n_te)
                record["q"] = {
                    t: {} for t in tickers
                }
                for tau in s1.TAUS:
                    parts = _split_rows(preds[tau], tickers, n_te)
                    for t in tickers:
                        record["q"][t][str(tau)] = parts[t]
                record["issued"] = issued
                record["reasons"] = reasons
            elif cfg["id"] == "Q3-ALL":
                X_tr, X_te_parts = _stacked_design(features, names, train_idx, test_idx, tickers)
                X_te = np.vstack(X_te_parts)
                _mean, std, X_tr_s, X_te_s = s1._standardise(X_tr, X_te)
                if (std == 0).any():
                    issued, reasons = _blank(tickers, n_te, "FEATURE_DEGENERATE")
                    record["issued"] = issued
                    record["reasons"] = reasons
                    by_config[cfg["id"]] = record
                    continue
                q_unclipped: dict[float, np.ndarray] = {}
                for tau in s1.TAUS:
                    intercept, beta = s1.fit_quantile_lp(X_tr_s, a_tr, tau)
                    q_unclipped[tau] = X_te_s @ beta + intercept
                issued_stack, clipped, reasons_stack = s1.quantile_output_policy(
                    q_unclipped[0.5], q_unclipped[0.8], q_unclipped[0.9]
                )
                q50, q80, q90 = clipped
                record["issued"] = _split_rows(issued_stack.astype(bool), tickers, n_te)
                record["reasons"] = _split_rows(reasons_stack, tickers, n_te)
                record["q"] = {}
                parts = {
                    "0.5": _split_rows(q50, tickers, n_te),
                    "0.8": _split_rows(q80, tickers, n_te),
                    "0.9": _split_rows(q90, tickers, n_te),
                }
                for t in tickers:
                    record["q"][t] = {k: parts[k][t] for k in s1.TAU_KEYS}
                try:
                    issued_q, q_hat = s1.fit_shifted_quantile_block(X_tr, a_tr, X_te)
                    record["q_shift"] = {}
                    record["shift_issued"] = _split_rows(np.asarray(issued_q, dtype=bool), tickers, n_te)
                    shift_parts = {k: _split_rows(q_hat[k], tickers, n_te) for k in s1.TAU_KEYS}
                    for t in tickers:
                        record["q_shift"][t] = {k: shift_parts[k][t] for k in s1.TAU_KEYS}
                except s1._FitFailure:
                    record["shift_issued"] = {t: np.zeros(n_te, dtype=bool) for t in tickers}
            else:  # pragma: no cover — configuration table is stage 1's
                raise AssertionError(f"unhandled configuration {cfg['id']}")
        except s1._FitFailure as exc:
            issued, reasons = _blank(tickers, n_te, exc.type)
            record["issued"] = issued
            record["reasons"] = reasons
        by_config[cfg["id"]] = record

    return {
        "train": {"origins": int(stats["origins"]), "events": float(stats["events"]), "thin": bool(thin)},
        "by_config": by_config,
        "q1_fallbacks": q1_fallbacks,
    }


def run_pooled_fits(features, labels, n_dates: int, tickers) -> dict:
    """Pooled walk-forward over the common date axis (D1, D6)."""
    y_all = {
        t: {h: _y_array(labels[t][h]["Y"]) for h in s1.HORIZONS} for t in tickers
    }
    a_all = {
        t: {h: labels[t][h]["A"].to_numpy(dtype=float) for h in s1.HORIZONS} for t in tickers
    }
    fits: dict[tuple, dict] = {}
    blocks: dict[tuple, dict] = {}
    q1_fallbacks: list[dict] = []
    for h in s1.HORIZONS:
        for block_i, (s0, e0) in enumerate(panel_fold_calendar(n_dates, h), start=1):
            train_idx = training_date_indices(n_dates, s0, h)
            test_idx = np.arange(int(s0), int(e0) + 1)
            fitted = fit_configurations_on_block(
                features,
                {t: y_all[t][h] for t in tickers},
                {t: a_all[t][h] for t in tickers},
                train_idx,
                test_idx,
                tickers,
            )
            blocks[(h, block_i)] = {"range": [int(s0), int(e0)], **fitted["train"]}
            for fb in fitted["q1_fallbacks"]:
                q1_fallbacks.append({"h": int(h), "block": int(block_i), **fb})
            for cfg_id, rec in fitted["by_config"].items():
                rec["test_idx"] = test_idx
                rec["block"] = [int(s0), int(e0)]
                fits[(h, block_i, cfg_id)] = rec
    return {"fits": fits, "blocks": blocks, "q1_fallbacks": q1_fallbacks}


# ── D7: comparison sets on (ticker, date) ────────────────────────────────────


def intersect_issued(masks: dict[str, np.ndarray]) -> np.ndarray:
    """Stage-1 intersection, on masks aligned to ``(ticker, date)`` (D7).

    ``intersection_of_issued`` does not know what a row is. The panel's
    row is a pair, in date-major then ticker order, not a SPY origin.
    """
    return s1.intersection_of_issued(masks)


def _abst_row(issued: np.ndarray, reasons: np.ndarray, y: np.ndarray) -> dict:
    if len(issued) == 0:
        return {"rate": 0.0, "gap_pp": 0.0, "counts": {"issued": 0, "abstained": 0, "by_type": {}}}
    counts = s1.abstention_breakdown(issued, reasons)
    abstained = ~np.asarray(issued, dtype=bool)
    rate = float(abstained.mean())
    events = np.asarray(y, dtype=bool)
    ev_rate = float(abstained[events].mean()) if events.any() else 0.0
    nonev_rate = float(abstained[~events].mean()) if (~events).any() else 0.0
    return {"rate": rate, "gap_pp": (ev_rate - nonev_rate) * 100.0, "counts": counts}


# ── D8: bootstrap on the DATE index ──────────────────────────────────────────


def bootstrap_date_matrix(n_dates: int, h: int, pop: int, fam: int, var: int, n_draws: int | None = None) -> np.ndarray:
    """Circular moving-block draws on the common DATE index (D8).

    Stage-1 ``bootstrap_index_matrix`` draws positions of one comparison
    set and seeds from 221011. The panel passes ``N = N_dates`` and seed
    root 221012. The draw itself is stage 1's:
    ``starts = rng.integers(0, N_dates, size=ceil(N_dates / L))``,
    blocks ``(start + arange(L)) % N_dates``, keep the first ``N_dates``.
    ``var`` is stage-1's variant code (0 primary ``L=max(21, 2h)``,
    1 the ``L=h`` sensitivity).
    """
    draws = int(N_DRAWS if n_draws is None else n_draws)
    return s1.bootstrap_index_matrix(
        int(n_dates), int(h), int(pop), int(fam), int(var), n_draws=draws, seed_root=SEED_ROOT
    )


def expand_date_draws(date_matrix: np.ndarray, rows_for_date: list[np.ndarray]) -> np.ndarray:
    """Each drawn date contributes every comparison row on that date (D8).

    ``rows_for_date[j]`` is the row positions, in the stacked comparison
    arrays, of date position ``j``. Widths must match; a date with a
    partial cross-section is handled by :func:`panel_family_draws`.
    """
    table = np.vstack([np.asarray(rows, dtype=np.int64) for rows in rows_for_date])
    expanded = table[np.asarray(date_matrix, dtype=int)]
    return expanded.reshape(date_matrix.shape[0], -1)


def _failing_draws(kind: str, n_draws: int) -> dict:
    """Undefined-sample stand-in: −inf where the gate needs large, +inf where small."""
    n = int(n_draws)
    neg = np.full(n, -np.inf)
    if kind == "binary":
        cfgs = s1.BINARY_CLAIM_CONFIGS
        return {
            "brier": {c: np.full(n, np.nan) for c in cfgs},
            "bss": {c: neg.copy() for c in cfgs},
            "v": {c: {lab: neg.copy() for lab in s1.ALPHA_KEYS} for c in cfgs},
            "delta_v": neg.copy(),
            "citl": np.full(n, np.nan),
            "wace": np.full(n, np.inf),
        }
    cfgs = s1.QUANTILE_CLAIM_CONFIGS
    return {
        "pl_sum": {c: np.full(n, np.nan) for c in cfgs},
        "skill": neg.copy(),
        "skill_q1_vs_q0": neg.copy(),
        "coverage": {k: np.full(n, np.nan) for k in s1.TAU_KEYS},
    }


def _binary_on_indices(indices: np.ndarray, y, p, h: int) -> dict:
    indices = np.asarray(indices, dtype=int)
    ident = np.arange(len(indices), dtype=np.int64)[None, :]
    p_sub = {c: np.asarray(p[c])[indices] for c in p}
    return s1.binary_draw_statistics(ident, np.asarray(y)[indices], p_sub, s1.alpha_grid(h))


def _quantile_on_indices(indices: np.ndarray, a, q) -> dict:
    indices = np.asarray(indices, dtype=int)
    ident = np.arange(len(indices), dtype=np.int64)[None, :]
    q_sub = {c: {k: np.asarray(q[c][k])[indices] for k in s1.TAU_KEYS} for c in q}
    return s1.quantile_draw_statistics(ident, np.asarray(a, dtype=float)[indices], q_sub)


def _stack_draw_stats(parts: list[dict], kind: str) -> dict:
    if kind == "binary":
        cfgs = list(parts[0]["brier"])
        return {
            "brier": {c: np.concatenate([p["brier"][c] for p in parts]) for c in cfgs},
            "bss": {c: np.concatenate([p["bss"][c] for p in parts]) for c in cfgs},
            "v": {
                c: {lab: np.concatenate([p["v"][c][lab] for p in parts]) for lab in s1.ALPHA_KEYS}
                for c in cfgs
            },
            "delta_v": np.concatenate([p["delta_v"] for p in parts]),
            "citl": np.concatenate([p["citl"] for p in parts]),
            "wace": np.concatenate([p["wace"] for p in parts]),
        }
    cfgs = list(parts[0]["pl_sum"])
    return {
        "pl_sum": {c: np.concatenate([p["pl_sum"][c] for p in parts]) for c in cfgs},
        "skill": np.concatenate([p["skill"] for p in parts]),
        "skill_q1_vs_q0": np.concatenate([p["skill_q1_vs_q0"] for p in parts]),
        "coverage": {k: np.concatenate([p["coverage"][k] for p in parts]) for k in s1.TAU_KEYS},
    }


def panel_family_draws(rows_for_date, values, configs, h, pop, fam, var, n_draws, kind: str) -> dict:
    """One paired date-index draw applied to every configuration (D8).

    When every date has the same cross-section width, the expanded index
    is rectangular and stage-1's draw statistic runs in one call. When a
    date has lost a ticker to abstention, each draw still concatenates
    that date's whole remaining cross-section and the same stage-1
    statistic is evaluated on those rows. Undefined statistics stay at
    the failing extreme inside those stage-1 functions. Bounds later use
    ``numpy.quantile`` via stage-1 ``gate_lower_bound`` / ``_quantile_all_draws``.
    """
    n_draws = int(n_draws)
    if not rows_for_date or sum(len(r) for r in rows_for_date) == 0:
        return _failing_draws(kind, n_draws)
    date_matrix = bootstrap_date_matrix(len(rows_for_date), h, pop, fam, var, n_draws=n_draws)
    widths = [len(r) for r in rows_for_date]
    equal = all(w == widths[0] for w in widths) and widths[0] > 0
    if equal and widths[0] * len(rows_for_date) == len(values):
        idx = expand_date_draws(date_matrix, rows_for_date)
        if kind == "binary":
            return s1.binary_draw_statistics(idx, np.asarray(values), configs, s1.alpha_grid(int(h)))
        return s1.quantile_draw_statistics(idx, np.asarray(values, dtype=float), configs)
    parts = []
    for draw in range(date_matrix.shape[0]):
        indices = np.concatenate([np.asarray(rows_for_date[int(j)], dtype=int) for j in date_matrix[draw]])
        if kind == "binary":
            parts.append(_binary_on_indices(indices, values, configs, int(h)))
        else:
            parts.append(_quantile_on_indices(indices, values, configs))
    return _stack_draw_stats(parts, kind)


# ── D9: event dates, honest-N, LOEO ──────────────────────────────────────────


def panel_event_dates(date_index: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Session indices where at least one ticker has ``Y=1`` (D9).

    Stage-1 ``honest_n`` treats every true row of one series as an event.
    Several tickers lighting up on the same session are one event date,
    so this collapses the cross-section before clustering.
    """
    dates = np.asarray(date_index, dtype=int)
    yy = np.asarray(y, dtype=bool)
    if not yy.any():
        return np.zeros(0, dtype=int)
    return np.unique(dates[yy])


def panel_honest_n(date_index, y, session_dates, h: int, tickers=None) -> dict:
    """Honest-N on the DATE axis (D9).

    Clusters and episode windows are stage-1 ``event_clusters`` /
    ``merge_episodes`` (gap ≤ h merges; window is 21 sessions before the
    first event through h after the last). The power floor uses those
    calendar episodes and the distinct months of event dates
    (``POWER_MIN_EPISODES`` and ``POWER_MIN_MONTHS``). Per-ticker episode
    counts are stored beside the floor and are not an input to it.
    """
    date_index = np.asarray(date_index, dtype=int)
    y = np.asarray(y, dtype=bool)
    event_dates = panel_event_dates(date_index, y)
    clusters = s1.event_clusters(event_dates, int(h))
    episodes = s1.merge_episodes(clusters, int(h))
    months = sorted({str(session_dates[int(i)])[:7] for i in event_dates})
    met = len(episodes) >= s1.POWER_MIN_EPISODES and len(months) >= s1.POWER_MIN_MONTHS
    per_ticker: dict[str, int] = {}
    if tickers is not None:
        ticker_arr = np.asarray(tickers)
        ordered = []
        for t in ticker_arr.tolist():
            if t not in ordered:
                ordered.append(t)
        for t in ordered:
            mask = ticker_arr == t
            ev = panel_event_dates(date_index[mask], y[mask])
            per_ticker[str(t)] = int(len(s1.merge_episodes(s1.event_clusters(ev, int(h)), int(h))))
    return {
        "origins": int(len(date_index)),
        "events": int(len(event_dates)),
        "ticker_events": int(y.sum()),
        "clusters": int(len(clusters)),
        "episodes": int(len(episodes)),
        "event_months": int(len(months)),
        "event_month_list": months,
        "event_dates": [int(i) for i in event_dates],
        "episode_windows": [[int(ep["window"][0]), int(ep["window"][1])] for ep in episodes],
        "power_floor": {
            "min_episodes": int(s1.POWER_MIN_EPISODES),
            "min_months": int(s1.POWER_MIN_MONTHS),
            "met": bool(met),
        },
        "per_ticker_episodes": per_ticker,
        "episodes_detail": episodes,
    }


def loeo_report(date_index, y, a, p, q, episodes, h: int, fam: str) -> dict:
    """Leave-one-episode-out through stage-1 ``loeo_checks`` (D9).

    ``origin_idx`` is the shared DATE index, repeated once per ticker on
    that date. The stage-1 window test then removes the episode's dates
    from every ticker. A per-ticker index would leave the other names in.
    """
    cell = {
        "origin_idx": np.asarray(date_index, dtype=int),
        "y": np.asarray(y, dtype=bool),
        "a": np.asarray(a, dtype=float),
        "episodes": episodes,
        "p": p or {},
        "q": q or {},
    }
    return s1.loeo_checks(cell, fam, int(h))


# ── comparison cells, gates, negative control ────────────────────────────────


def _group_rows_by_date(date_index: np.ndarray) -> list[np.ndarray]:
    """Contiguous date groups. ``date_index`` is date-major."""
    groups: list[np.ndarray] = []
    if len(date_index) == 0:
        return groups
    current = int(date_index[0])
    start = 0
    for i, raw in enumerate(date_index.tolist()):
        d = int(raw)
        if d != current:
            groups.append(np.arange(start, i, dtype=int))
            current = d
            start = i
    groups.append(np.arange(start, len(date_index), dtype=int))
    return groups


def _attach_metrics(cell: dict, fam: str, h: int) -> None:
    """Gate metrics via stage-1 metric functions.

    ``compute_point_metrics`` indexes one close/rv20 vector by origin
    position (year, block and tercile slices). The panel comparison row
    is a ``(ticker, date)`` pair, so the headline metrics — the ones the
    gates read — are computed here with ``binary_metric_set`` and
    ``quantile_metric_set``. Slice tables are not re-derived.
    """
    metrics: dict = {}
    if fam == "binary":
        p0 = cell["p"]["B0"]
        alphas = s1.alpha_grid(h)
        for cid in cell["configs"]:
            metrics[cid] = s1.binary_metric_set(cell["p"][cid], cell["y"], p0=p0, alphas=alphas)
    else:
        for cid in cell["configs"]:
            metrics[cid] = s1.quantile_metric_set(cell["a"], cell["q"][cid])
    cell["metrics"] = metrics


def _attach_bootstrap(cell: dict, h: int, fam: str) -> dict:
    pop = s1.SEED_CODES["pop"]["P-all"]
    fam_code = s1.SEED_CODES["fam"][fam]
    groups = _group_rows_by_date(cell["origin_idx"])
    values = cell["y"] if fam == "binary" else cell["a"]
    configs = cell["p"] if fam == "binary" else cell["q"]
    cell["draws"] = {}
    report = {}
    for variant, name in ((0, "primary"), (1, "sensitivity_L_h")):
        stats = panel_family_draws(
            groups, values, configs, h, pop, fam_code, variant, int(N_DRAWS), fam
        )
        cell["draws"][name] = stats
        headline = None
        if groups:
            headline = s1._headline_bounds(stats, fam)
        report[name] = {
            "L": int(s1.block_length(h, variant)),
            "n_draws": int(N_DRAWS),
            "N_dates": int(len(groups)),
            "seed": [int(SEED_ROOT), int(h), int(pop), int(fam_code), int(variant)],
            "headline": headline,
        }
    return report


def build_panel_comparisons(fits_payload, labels, features, n_dates: int, session_dates, tickers) -> tuple[dict, dict, dict]:
    """Per horizon, binary and quantile comparison cells plus abstention tables."""
    fit_records = fits_payload["fits"]
    comp_by_h: dict = {}
    abst_tables: dict = {}
    extra: dict = {}
    n_t = len(tickers)
    t_pos = {t: j for j, t in enumerate(tickers)}
    binary_ids = list(s1.BINARY_CLAIM_CONFIGS) + [s1.SENSITIVITY_CONFIG]
    quantile_ids = list(s1.QUANTILE_CLAIM_CONFIGS)

    for h in s1.HORIZONS:
        blocks = panel_fold_calendar(n_dates, h)
        eval_idx = s1.evaluation_origin_indices(n_dates, h) if blocks else np.zeros(0, dtype=int)
        n_eval = int(len(eval_idx))
        n_rows = n_eval * n_t
        date_pos = {int(d): i for i, d in enumerate(eval_idx)}

        def row_of(d: int, t: str) -> int:
            return date_pos[int(d)] * n_t + t_pos[t]

        y_by = {t: _y_array(labels[t][h]["Y"]) for t in tickers}
        a_by = {t: labels[t][h]["A"].to_numpy(dtype=float) for t in tickers}
        y_grid = np.zeros(n_rows, dtype=bool)
        a_grid = np.zeros(n_rows, dtype=float)
        date_grid = np.zeros(n_rows, dtype=int)
        ticker_grid = np.empty(n_rows, dtype=object)
        for d in eval_idx:
            for t in tickers:
                r = row_of(int(d), t)
                yv = y_by[t][int(d)]
                y_grid[r] = bool(np.isfinite(yv) and yv > 0)
                a_grid[r] = float(a_by[t][int(d)])
                date_grid[r] = int(d)
                ticker_grid[r] = t

        issued = {cid: np.zeros(n_rows, dtype=bool) for cid in binary_ids + quantile_ids}
        reasons = {cid: np.full(n_rows, "NO_FIT_ROW", dtype=object) for cid in issued}
        p = {cid: np.full(n_rows, np.nan) for cid in binary_ids}
        q = {cid: {k: np.full(n_rows, np.nan) for k in s1.TAU_KEYS} for cid in quantile_ids}
        p_shift = np.full(n_rows, np.nan)
        shift_issued = np.zeros(n_rows, dtype=bool)
        q_shift = {k: np.full(n_rows, np.nan) for k in s1.TAU_KEYS}
        q_shift_issued = np.zeros(n_rows, dtype=bool)

        for (bh, _bi, cid), rec in fit_records.items():
            if bh != h or cid not in issued:
                continue
            for j, d in enumerate(rec["test_idx"]):
                if int(d) not in date_pos:
                    continue
                for t in tickers:
                    r = row_of(int(d), t)
                    issued[cid][r] = bool(rec["issued"][t][j])
                    reasons[cid][r] = rec["reasons"][t][j]
                    if "p" in rec:
                        p[cid][r] = float(rec["p"][t][j])
                    if "q" in rec:
                        for k in s1.TAU_KEYS:
                            q[cid][k][r] = float(rec["q"][t][k][j])
                    if cid == "M3-ALL" and rec.get("shift_issued") and "p_shift" in rec:
                        p_shift[r] = float(rec["p_shift"][t][j])
                        shift_issued[r] = True
                    if cid == "Q3-ALL" and "q_shift" in rec:
                        q_shift_issued[r] = bool(rec["shift_issued"][t][j])
                        for k in s1.TAU_KEYS:
                            q_shift[k][r] = float(rec["q_shift"][t][k][j])

        abst_tables[h] = {cid: _abst_row(issued[cid], reasons[cid], y_grid) for cid in issued}
        fams: dict = {}
        fam_extra: dict = {}
        for fam, cfgs in s1.FAMILY_CONFIGS.items():
            common = intersect_issued({cid: issued[cid] for cid in cfgs})
            cell = {
                "family": fam,
                "configs": cfgs,
                "h": int(h),
                "origin_idx": date_grid[common],
                "ticker": ticker_grid[common],
                "y": y_grid[common],
                "a": a_grid[common],
                "common_mask": common,
                "p": {cid: p[cid][common] for cid in cfgs} if fam == "binary" else {},
                "q": {cid: {k: q[cid][k][common] for k in s1.TAU_KEYS} for cid in cfgs} if fam == "quantile" else {},
            }
            hn = panel_honest_n(cell["origin_idx"], cell["y"], session_dates, h, tickers=cell["ticker"])
            cell["episodes"] = hn.pop("episodes_detail")
            cell["honest_n"] = hn
            _attach_metrics(cell, fam, h)
            fam_extra[fam] = {
                "N_common": int(common.sum()),
                "bootstrap": _attach_bootstrap(cell, h, fam),
                "honest_n": hn,
            }
            if fam == "binary":
                sens_mask = common & issued[s1.SENSITIVITY_CONFIG]
                fam_extra[fam]["sensitivity"] = {
                    "config": s1.SENSITIVITY_CONFIG,
                    "n": int(sens_mask.sum()),
                    "metrics": (
                        s1.binary_metric_set(
                            p[s1.SENSITIVITY_CONFIG][sens_mask],
                            y_grid[sens_mask],
                            p0=p["B0"][sens_mask],
                            alphas=s1.alpha_grid(h),
                        )
                        if sens_mask.any()
                        else None
                    ),
                    "note": "sensitivity row only, never a gate",
                }
            fams[fam] = cell
        # Negative control scores on the same comparison rows (D1 / v1 §12).
        b_common = fams["binary"]["common_mask"]
        q_common = fams["quantile"]["common_mask"]
        b_mask = b_common & shift_issued
        q_mask = q_common & q_shift_issued
        bss = v_at = None
        if b_mask.any():
            bss = s1.brier_skill_score(p_shift[b_mask], y_grid[b_mask], p["B0"][b_mask])
            v_at = s1.richardson_v(p_shift[b_mask], y_grid[b_mask], s1.alpha_grid(h)["b"])
        skill = None
        if q_mask.any():
            ones = np.ones(int(q_mask.sum()), dtype=bool)
            pl_q3 = s1.pinball_loss_sum(a_grid[q_mask], {k: q_shift[k][q_mask] for k in s1.TAU_KEYS}, ones)
            pl_q0 = s1.pinball_loss_sum(a_grid[q_mask], {k: q["Q0"][k][q_mask] for k in s1.TAU_KEYS}, ones)
            pl_q1 = s1.pinball_loss_sum(a_grid[q_mask], {k: q["Q1"][k][q_mask] for k in s1.TAU_KEYS}, ones)
            if pl_q3 is not None and pl_q0 and pl_q1:
                skill = 1.0 - pl_q3 / min(pl_q0, pl_q1)
        fam_extra["negative_control"] = {
            "m3-ALL-shifted": {"bss_vs_b0": bss, "v_at_b_h": v_at, "n_scored": int(b_mask.sum())},
            "q3-ALL-shifted": {"pinball_skill": skill, "n_scored": int(q_mask.sum())},
            "shift": "numpy.roll(y, len(y) // 2) per pooled training block (deterministic, no seed)",
            "expectation": "at or below 0; neither a claim nor a gate",
        }
        comp_by_h[h] = fams
        extra[h] = fam_extra
    return comp_by_h, abst_tables, extra


def inc_row() -> dict:
    """INC is not applicable (D10).

    Stage-1 ``run_inc`` replays the SPY displayed-probability incumbent
    against a current-vintage SPY label. The panel excludes SPY, and the
    incumbent is SPY-only, so there is no INC series to score. The row is
    not one of the 12 claims and is not a gate.
    """
    return {
        "id": "INC",
        "status": "NOT_APPLICABLE",
        "reason": "the incumbent is SPY-only and SPY is excluded from the panel",
        "evidence_class": "NOT_APPLICABLE",
        "gate": False,
    }


def execute_panel(
    panel: dict[str, pd.DataFrame],
    fold_block_table: list[dict] | None = None,
    subframe_sha256: dict[str, str] | None = None,
) -> dict:
    """Labels, features, pooled fits, claims. Refuses first if pins are pending.

    The pending check is the first statement so a monkeypatched feature
    constructor cannot run while pins or the trial budget are still the
    literal ``PREREG_V11_PENDING``. The fold block table is stored on the
    payload before ``run_pooled_fits``.
    """
    _raise_if_unfrozen()
    tickers = list(PANEL_TICKERS)
    session_dates = panel[tickers[0]]["date"].astype(str).tolist()
    n_dates = len(session_dates)
    for ticker in tickers[1:]:
        got = panel[ticker]["date"].astype(str).tolist()
        if got != session_dates:
            _refuse(
                "CALENDAR_MISALIGNED",
                f"{ticker} calendar differs from the intersection axis",
                unexpected=sorted(set(got) - set(session_dates)),
                missing=sorted(set(session_dates) - set(got)),
            )

    table = block_table(session_dates) if fold_block_table is None else fold_block_table
    staged = {"fold_block_table": table}

    labels: dict = {}
    features: dict = {}
    for ticker in tickers:
        close = pd.Series(
            panel[ticker]["close"].to_numpy(dtype=float),
            index=pd.Index(session_dates, name="date"),
        )
        # Attribute lookup (not a local binding) so tests can patch these.
        labels[ticker] = s1.build_labels(close)
        features[ticker] = s1.build_features(close)

    fits = run_pooled_fits(features, labels, n_dates, tickers)
    comp_by_h, abst_tables, extra = build_panel_comparisons(
        fits, labels, features, n_dates, session_dates, tickers
    )
    claims = s1.build_gates(comp_by_h, abst_tables)
    return _assemble_payload(
        fits,
        extra,
        claims,
        n_dates,
        session_dates,
        fold_block_table=staged["fold_block_table"],
        subframe_sha256=subframe_sha256,
    )


def _git_head() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
        )
    except OSError:
        return "unavailable"
    if proc.returncode != 0:
        return "unavailable"
    return proc.stdout.strip()


def _commit_sha() -> str:
    sha = _git_head()
    if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
        return sha
    return "UNKNOWN: git rev-parse HEAD failed"


def _git_blob(relpath: str) -> str:
    """``git hash-object`` of a working-tree file. Never omits a failure."""
    try:
        proc = subprocess.run(
            ["git", "hash-object", "--", relpath],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return f"UNKNOWN: git hash-object failed ({type(exc).__name__})"
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "nonzero status").strip().splitlines()
        tail = err[-1] if err else "nonzero status"
        return f"UNKNOWN: git hash-object {relpath} failed ({tail})"
    sha = proc.stdout.strip()
    if len(sha) != 40:
        return f"UNKNOWN: git hash-object {relpath} returned {sha!r}"
    return sha


def _bootstrap_record() -> dict:
    """D8 record. Per-cell ``n_draws`` stays on each bootstrap cell as well."""
    return {
        "n_draws": int(N_DRAWS),
        "seed_root": int(SEED_ROOT),
        "axis": "date",
        "block_length_rule": "stage-1 block_length(h, variant)",
    }


def provenance_fields(subframe_sha256: dict[str, str] | None) -> dict:
    """Manifest, prereg, commit and blob pins. Unknown values are explicit."""
    if subframe_sha256 is None:
        hashes = {ticker: "UNKNOWN: panel not loaded" for ticker in PANEL_TICKERS}
    else:
        hashes = {
            ticker: subframe_sha256.get(ticker, "UNKNOWN: hash not computed")
            for ticker in PANEL_TICKERS
        }
    return {
        "manifest_path": MANIFEST_PATH,
        "manifest_version": MANIFEST_VERSION,
        "manifest_blob_sha": MANIFEST_BLOB_SHA,
        "prereg_path": PREREG_PATH,
        "prereg_blob_sha": PREREG_BLOB_SHA,
        "commit_sha": _commit_sha(),
        "script_blob_sha": _git_blob(SCRIPT_REL),
        "test_blob_sha": _git_blob(TEST_REL),
        "adjust_module_blob_sha": _git_blob(ADJUST_REL),
        "subframe_sha256": hashes,
    }


def _assemble_payload(
    fits,
    extra,
    claims,
    n_dates: int,
    session_dates: list[str],
    fold_block_table: list[dict] | None = None,
    subframe_sha256: dict[str, str] | None = None,
) -> dict:
    comparison = {}
    episodes = {}
    negative = {}
    bootstrap_cells = {}
    for h in s1.HORIZONS:
        key = f"h{h}"
        comparison[key] = {}
        episodes[key] = {}
        bootstrap_cells[key] = {}
        for fam in ("binary", "quantile"):
            info = extra[h][fam]
            comparison[key][fam] = {"N_common": info["N_common"]}
            if fam == "binary":
                comparison[key][fam]["sensitivity"] = {
                    "config": info["sensitivity"]["config"],
                    "n": info["sensitivity"]["n"],
                    "note": info["sensitivity"]["note"],
                }
            episodes[key][fam] = info["honest_n"]
            bootstrap_cells[key][fam] = info["bootstrap"]
        negative[key] = extra[h]["negative_control"]
    payload = {
        "schema": SCHEMA,
        "status": "OK",
        "trial_family": TRIAL_FAMILY,
        "trial_budget": TRIAL_BUDGET,
        "trial_counting": {
            "per_horizon": TRIALS_PER_HORIZON,
            "total": TRIALS_TOTAL,
            "inc": "removed from v1's 23",
            "note": "frozen with prereg v1.1; registered in data/trial_ledger.jsonl before outcomes",
        },
        "dividend_basis": DIVIDEND_BASIS,
        "dividend_disclosure": DIVIDEND_DISCLOSURE,
        "seed_root": SEED_ROOT,
        "n_draws": int(N_DRAWS),
        "panel": {
            "tickers": list(PANEL_TICKERS),
            "n_dates": int(n_dates),
            "first_date": session_dates[0],
            "last_date": session_dates[-1],
            "spy_excluded": True,
        },
        "folds": {
            f"h{h}/b{b}": {"range": v["range"], "origins": v["origins"], "events": v["events"], "thin": v["thin"]}
            for (h, b), v in sorted(fits["blocks"].items())
        },
        "comparison": comparison,
        "episodes": episodes,
        "bootstrap": _bootstrap_record(),
        "bootstrap_cells": bootstrap_cells,
        "fold_block_table": [] if fold_block_table is None else fold_block_table,
        "negative_control": negative,
        "claims": claims,
        "inc": inc_row(),
        "blocked": [],
        "run_commit": _commit_sha(),
    }
    payload.update(provenance_fields(subframe_sha256))
    return payload


# ── artifacts ────────────────────────────────────────────────────────────────


def _strict(obj):
    """Numpy values become Python. Non-finite floats become ``None``."""
    if isinstance(obj, dict):
        return {str(k): _strict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_strict(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _strict(obj.tolist())
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        value = float(obj)
        if not math.isfinite(value):
            return None
        return value
    if obj is None or isinstance(obj, (str, int)):
        return obj
    return str(obj)


def _markdown_preamble(payload: dict) -> list[str]:
    boot = payload.get("bootstrap") or {}
    lines = [
        "# Pullback stage-1b panel results",
        "",
        f"- schema: `{payload.get('schema')}`",
        f"- status: {payload.get('status')}",
        f"- trial family `{payload.get('trial_family')}`, budget `{payload.get('trial_budget')}`",
        f"- dividend basis: {payload.get('dividend_basis')}",
        (
            f"- bootstrap: n_draws={boot.get('n_draws')} seed_root={boot.get('seed_root')} "
            f"axis={boot.get('axis')} block_length_rule={boot.get('block_length_rule')}"
        ),
        "",
        "## Provenance",
        "",
        (
            f"- manifest: `{payload.get('manifest_path')}` "
            f"version `{payload.get('manifest_version')}` blob `{payload.get('manifest_blob_sha')}`"
        ),
        f"- prereg: `{payload.get('prereg_path')}` blob `{payload.get('prereg_blob_sha')}`",
        f"- commit: `{payload.get('commit_sha')}`",
        f"- script blob: `{payload.get('script_blob_sha')}`",
        f"- test blob: `{payload.get('test_blob_sha')}`",
        f"- adjust module blob: `{payload.get('adjust_module_blob_sha')}`",
        "- subframe_sha256:",
    ]
    hashes = payload.get("subframe_sha256") or {}
    for ticker in PANEL_TICKERS:
        lines.append(f"  - {ticker}: `{hashes.get(ticker, 'UNKNOWN: missing from payload')}`")
    lines.append("")
    return lines


def render_markdown(payload: dict) -> str:
    """Results note generated from the JSON-ready payload. Aggregates only."""
    lines = _markdown_preamble(payload)
    blocked = payload.get("blocked") or []
    if blocked:
        lines.append("## Blocked")
        lines.append("")
        for row in blocked:
            lines.append(f"- `{row.get('type')}`: {row.get('detail')}")
        lines.append("")
        return "\n".join(lines)
    lines.append("## Claims (12) and INC")
    lines.append("")
    lines.append("| claim | statistic | point | lower bound | verdict | flags |")
    lines.append("|---|---|---|---|---|---|")
    for row in payload.get("claims", []):
        flags = ", ".join(str(flag) for flag in (row.get("flags") or [])) or "—"
        lines.append(
            f"| {row.get('id')} | {row.get('statistic')} | {row.get('point')} | {row.get('lb')} | {row.get('verdict')} | {flags} |"
        )
    inc = payload.get("inc") or {}
    lines.append(f"| INC | — | — | — | {inc.get('status')} | {inc.get('reason')} |")
    lines.append("")
    lines.append("## Honest-N (event dates on the common calendar)")
    lines.append("")
    lines.append("| cell | origins | event dates | episodes | event months | power floor |")
    lines.append("|---|---|---|---|---|---|")
    for hkey, fams in (payload.get("episodes") or {}).items():
        for fam, hn in fams.items():
            floor = hn.get("power_floor") or {}
            lines.append(
                f"| {hkey} {fam} | {hn.get('origins')} | {hn.get('events')} | {hn.get('episodes')} | "
                f"{hn.get('event_months')} | {'met' if floor.get('met') else 'not met'} |"
            )
    lines.append("")
    lines.append(payload.get("dividend_disclosure") or "")
    lines.append("")
    return "\n".join(lines)


def write_payload(out_dir: Path, payload: dict) -> tuple[Path, Path]:
    """Write the JSON and the markdown under ``out_dir`` only."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ready = _strict(payload)
    json_path = out_dir / RESULTS_JSON_NAME
    md_path = out_dir / RESULTS_MD_NAME
    json_path.write_text(
        json.dumps(ready, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(ready), encoding="utf-8")
    return json_path, md_path


def _blocked_payload(exc: s1.Blocked) -> dict:
    row = {"type": exc.type, "detail": exc.detail}
    skip = {"type", "detail", "subframe_sha256", "fold_block_table"}
    for key, value in vars(exc).items():
        if key.startswith("_") or key in skip:
            continue
        row[key] = value
    hashes = getattr(exc, "subframe_sha256", None)
    table = getattr(exc, "fold_block_table", None)
    payload = {
        "schema": SCHEMA,
        "status": "BLOCKED",
        "trial_family": TRIAL_FAMILY,
        "trial_budget": TRIAL_BUDGET,
        "dividend_basis": DIVIDEND_BASIS,
        "dividend_disclosure": DIVIDEND_DISCLOSURE,
        "bootstrap": _bootstrap_record(),
        "fold_block_table": (
            table if table is not None else "UNKNOWN: blocked before the fold block table"
        ),
        "blocked": [row],
        "claims": [],
        "inc": inc_row(),
        "run_commit": _commit_sha(),
    }
    payload.update(provenance_fields(hashes))
    return payload


def _resolve_out(path: str | Path) -> Path:
    out = Path(path)
    if not out.is_absolute():
        out = ROOT / out
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grey_deer_pullback_stage1b",
        description="Grey Deer pullback stage-1b pooled panel (synthetic until prereg v1.1 is frozen)",
    )
    parser.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        help="artifact directory (default: research/grey_deer/pullback_stage1b)",
    )
    parser.add_argument("--panel-dir", default=None, help="directory of {TICKER}.parquet files")
    parser.add_argument(
        "--blocks-only",
        action="store_true",
        help="print the fold block table and raw subframe pins, then exit without a fit or an artifact",
    )
    return parser


def _print_block_table(table: list[dict]) -> None:
    for row in table:
        print(_block_line(row))


def main(argv: list[str] | None = None) -> int:
    """Run the panel. Refusals return 2 and write a typed artifact; they do not raise.

    Writes only under ``--out-dir``. The default is
    ``research/grey_deer/pullback_stage1b`` and is not used unless the
    caller leaves the flag off. ``--blocks-only`` prints the block table
    and the 14 raw subframe hashes and writes nothing. A checkout without
    ``data/trial_ledger.jsonl`` raises before any outcome: that is an
    environment error, not a panel refusal, so it writes no artifact.
    """
    args = build_parser().parse_args(argv)
    out_dir = _resolve_out(args.out_dir)
    try:
        if not args.panel_dir:
            _refuse("PANEL_COVERAGE", "panel directory not provided")
        panel_dir = Path(args.panel_dir)
        paths = {t: panel_dir / f"{t}.parquet" for t in PANEL_TICKERS}
        loaded = load_panel(paths, check_freeze=not args.blocks_only)
        table = block_table(loaded.calendar)
        if args.blocks_only:
            _print_block_table(table)
            for ticker in PANEL_TICKERS:
                print(f"PIN {ticker} {loaded.subframe_sha256[ticker]}")
            return 0
        # Print and retain the table before any pooled fit.
        _print_block_table(table)
        with trial_ledger_scope():
            payload = execute_panel(
                loaded.frames,
                fold_block_table=table,
                subframe_sha256=loaded.subframe_sha256,
            )
        write_payload(out_dir, payload)
    except s1.Blocked as exc:
        try:
            write_payload(out_dir, _blocked_payload(exc))
        except OSError as write_exc:
            sys.stderr.write(f"blocked-artifact write failed: {write_exc}\n")
        print(f"BLOCKED / {exc.type}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
