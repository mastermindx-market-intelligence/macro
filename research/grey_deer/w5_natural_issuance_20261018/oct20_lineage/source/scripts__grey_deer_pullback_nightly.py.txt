"""scripts/grey_deer_pullback_nightly.py — Grey Deer pullback prospective lane, nightly.

Issues tonight's SPY rows with the frozen writer
(``engine/grey_deer_pullback_forward.py``), then grades every matured row with
the frozen grader (``engine/grey_deer_pullback_forward_grade.py``). Both append
to ``data/grey_deer_pullback/`` and gate themselves on ``COLLECT_LANE=nightly``
plus their ``daily.yml:engine`` identity pins, so this file holds no model,
label, gate or clock logic of its own. It sits outside the writer's
``RECIPE_FILES`` on purpose: wiring changes here never move the recipe
fingerprint.

Store identity is the stable SOURCE name, not a content hash. It is part of
the inputs digest, so a per-night hash would flag every grade as revised and
the floor (which counts only unrevised gated grades) could never be met. A
data revision still surfaces, because the digest carries the close and every
feature value at the issue session.

Never fatal. A load failure, an unexpected exception, or a refusal other than
the two expected every night (OBSERVER_NOT_ON_MAIN, DUPLICATE_KEY) becomes a
line-start ``::warning`` annotation, and the process exits 0.

Run: python -m scripts.grey_deer_pullback_nightly [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import grey_deer_pullback_forward as fw  # noqa: E402
from engine import grey_deer_pullback_forward_grade as fg  # noqa: E402

TICKER = "SPY"
STORE_IDENTITY = "collectors.massive_stock_day:SPY"
# Expected on a healthy night: one OBSERVER_NOT_ON_MAIN per issue call, and a
# DUPLICATE_KEY whenever a rerun meets rows the first run already issued.
_QUIET_WRITER_REASONS = frozenset({"OBSERVER_NOT_ON_MAIN", "DUPLICATE_KEY"})


def _warn(slug: str, message: str) -> None:
    print(f"::warning title={slug}::{message}", flush=True)


def load_close(ticker: str = TICKER) -> pd.Series:
    """One ticker's session closes from the Massive store, chronological.

    Same normalisation as stage 1's ``normalize_subframe`` minus its AS_OF
    cut: the prospective lane wants every session the store holds.
    """
    import collectors.massive_stock_day as massive_stock_day

    df = massive_stock_day.load_ticker(ticker)
    if df is None or df.empty:
        raise LookupError(f"load_ticker({ticker!r}) returned an empty frame")
    df = df.reset_index(drop=("date" in df.columns))
    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date"})
    if "close" not in df.columns:
        raise LookupError(f"load_ticker({ticker!r}) has no close column")
    dates = pd.to_datetime(pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d"))
    close = pd.Series(df["close"].to_numpy(dtype=float), index=pd.DatetimeIndex(dates.to_numpy()))
    return close.sort_index(kind="mergesort")


def recompute_inputs_digest(prefix, t, h, ticker, store_identity, training_end_asof):
    """The writer's own digest over the grader's prefix; None when it cannot form.

    None never equals a stored digest, so an unformable recompute flags the
    grade as revised rather than passing it as clean.
    """
    try:
        return fw.inputs_digest(prefix, t, h, ticker, store_identity, training_end_asof)
    except fw._DigestMissing:
        return None


def _run_issue(close: pd.Series, out_dir: Path | None) -> dict:
    result = fw.issue(close, ticker=TICKER, store_identity=STORE_IDENTITY, out_dir=out_dir)
    if "issued" not in result:
        # LANE / IDENTITY: returned in memory, nothing written.
        _warn("grey-deer-pullback-issue-refused", f"writer refused {result.get('reason')} (nothing written)")
        return {"refused": result.get("reason")}
    loud = [r for r in result.get("refusals", []) if r not in _QUIET_WRITER_REASONS]
    if loud:
        _warn("grey-deer-pullback-issue-refused", f"writer refusals {sorted(set(loud))}; issued={result['issued']}")
    return {
        "issued": result["issued"],
        "duplicates": result["duplicates"],
        "refusals": result.get("refusals", []),
    }


def _run_grade(close: pd.Series, out_dir: Path | None) -> dict:
    result = fg.grade(
        close,
        ticker=TICKER,
        store_identity=STORE_IDENTITY,
        log_dir=out_dir,
        recompute_inputs_digest=recompute_inputs_digest,
    )
    reasons = [r.get("reason") for r in result.get("refusals", []) if isinstance(r, dict)]
    if reasons:
        _warn("grey-deer-pullback-grade-refused", f"grader refusals {sorted(set(map(str, reasons)))}")
    summary = {key: result.get(key, 0) for key in fg._COUNT_KEYS}
    summary["refusals"] = reasons
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="log directory (default: data/grey_deer_pullback)")
    args = parser.parse_args(argv)

    report: dict = {"ticker": TICKER, "store_identity": STORE_IDENTITY}
    try:
        close = load_close(TICKER)
    except Exception as exc:  # noqa: BLE001 — a bad store degrades the lane, never the band
        _warn("grey-deer-pullback-store-unreadable", f"{type(exc).__name__}: {exc}")
        report["error"] = "store_unreadable"
        print(json.dumps(report, sort_keys=True), flush=True)
        return 0

    for step, fn in (("issue", _run_issue), ("grade", _run_grade)):
        try:
            report[step] = fn(close, args.out_dir)
        except Exception as exc:  # noqa: BLE001 — grading still runs if issuing raised
            _warn(f"grey-deer-pullback-{step}-error", f"{type(exc).__name__}: {exc}")
            report[step] = {"error": type(exc).__name__}

    print(json.dumps(report, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
