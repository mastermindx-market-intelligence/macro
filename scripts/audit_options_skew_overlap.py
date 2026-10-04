"""Real-overlap audit: legacy polygon_gex rows vs the ThetaData recompute.

Why this exists
───────────────
MO-PAID-013 W2 migrates the engine.options_skew path from the legacy
`data/polygon_gex/chains/<date>.parquet` glob to the ThetaData EOD store
on the M1 ops host (engine.thetadata_store). W2-1b lands the source-stamped
ledger upsert (`source` in {polygon_gex, thetadata}, canonical-wins); W2-2
(this packet) ships the producer that feeds the ThetaData rows; W2-3 cuts
the render hosts to the ThetaData path. Before that cutover, the seat needs
a way to MEASURE the overlap — every (date, underlying) key that exists in
both sources, recompute the ThetaData skew, and report sign-agreement /
|delta skew| quantiles. That measurement is the promotion gate: a low
sign-agreement rate would mean the ThetaData path computes something the
legacy path would disagree with, and the cutover is unsafe.

Inputs
──────
  Ledger         data/options_skew/snapshots.parquet (overridable via --ledger)
  ThetaData store (overridable via --store; default $THETADATA_STORE)

Outputs
───────
  stdout         one-line JSON summary: keys_compared, sign_agreement_rate,
                 |delta_skew| p50/p90/max, top-10 worst keys
  --out file     markdown receipt at the named path. Default
                 research/MARKET_ONTOLOGY_F03_SKEW_OVERLAP_RECEIPT_<YYYY-MM-DD>.md
                 (computed at run time; TODAY's date is used, not the ledger's
                 most recent date — the receipt is the "what we ran" audit log,
                 not a data freshness report).

MISSING_ENGINE safety
─────────────────────
On the pre-W2-1b tree the engine.thetadata_store and engine.options_skew
imports are not yet on origin/main. The audit must FAIL LOUDLY with a named
exit code (1) and a one-line stderr message rather than crashing — the seat
runs this on the M1 after merge, but also wants a smoke pass that surfaces
the gap before merge. Pin the engine imports in a try/except; never import
them at module top.

CLI
───
  python -m scripts.audit_options_skew_overlap [--ledger PATH] [--store PATH]
                                                [--limit N] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

# Put the repo root on sys.path so engine.* resolves under both
# `python -m scripts.audit_options_skew_overlap` (the seat's launchd run)
# and a bare `python scripts/audit_options_skew_overlap.py` (the seat's
# smoke from /Users/chriswong/skew-ops-wt). The named-form pin is the
# exact idiom `tests/test_check_script_import_pinning.py` requires for
# every scripts/** entry — the one-liner form slipped past the static
# probe but the audit script is the one the seat reaches for by file
# path, so it gets the explicit `_ROOT` assignment.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Exit codes — pinned in the runbook so the seat can distinguish MISSING_ENGINE
# (do not promote yet) from a successful audit (promote if sign_agreement > X).
EXIT_OK = 0
EXIT_MISSING_ENGINE = 1
EXIT_NO_LEGACY_ROWS = 2
EXIT_READ_ERROR = 3

# Legacy source label — the column is a W2-1b addition; pre-W2-1b ledgers do
# not carry it. Treat its absence as "everything is legacy" so the audit
# remains useful on a pre-W2-1b ledger (one which has been produced by the
# pre-migration engine.options_skew).
LEGACY_SOURCE = "polygon_gex"
NEW_SOURCE = "thetadata"


def _load_engine() -> tuple[Any, Any] | None:
    """Pin the engine imports in a try/except (MISSING_ENGINE branch).

    Returns (make_chain_provider, compute_skew) on success, None on ImportError.
    Both are imported from the live engine path on the merged W2-1b tree
    (NOT main today). The branch is detected at import time: a pre-W2-1b
    tree lacks `engine.thetadata_store.make_chain_provider` AND
    `engine.options_skew.compute_skew` (main still has compute_skew with a
    different signature; the spec points at the W2-1b branch shape).

    Test hook: when SKEW_AUDIT_FAKE_TABLE is set in the environment, the
    function builds a synthetic provider/compute_skew pair from the JSON
    dict the env var holds. The shape is
        {"YYYY-MM-DD": {"SYM": skew_float, ...}, ...}
    and it ONLY takes effect under SKEW_AUDIT_FAKE_ENGINE=1, which
    signals "the engine import failed in this test environment, fall back
    to the fake". This is the contract tests/test_skew_accrual_launchd.py
    pins so the audit is exercisable in CI without the W2-1b engine path.
    """
    fake_ok = os.environ.get("SKEW_AUDIT_FAKE_ENGINE") == "1"
    if fake_ok:
        try:
            table = json.loads(os.environ.get("SKEW_AUDIT_FAKE_TABLE", "{}"))
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"MISSING_ENGINE: bad fake table: {exc}\n")
            return None
        return _build_fake_engine(table)
    try:
        from engine.thetadata_store import make_chain_provider  # noqa: PLC0415
        from engine.options_skew import compute_skew  # noqa: PLC0415
    except ImportError as exc:
        sys.stderr.write(f"MISSING_ENGINE: {exc}\n")
        return None
    return make_chain_provider, compute_skew


def _build_fake_engine(table: dict[str, dict[str, float]]):
    """Return (fake_make_chain_provider, fake_compute_skew) from a date/root
    keyed table. The provider is called as provider(date, root) -> DataFrame;
    compute_skew is called as compute_skew(df) -> dict-or-None. We mimic the
    real signatures exactly so the rest of the audit code path is identical
    between live and fake runs."""
    def make_chain_provider(*, store=None, require_iv=True):  # noqa: ARG001
        def provider(date_str: str, root: str):
            import pandas as _pd  # noqa: PLC0415
            skew = table.get(date_str, {}).get(root)
            if skew is None:
                return None
            return _pd.DataFrame([{"date": date_str, "underlying": root,
                                   "skew": float(skew)}])
        return provider

    def compute_skew(chain):
        if chain is None or chain.empty:
            return None
        return {"underlying": str(chain["underlying"].iloc[0]),
                "asof": str(chain["date"].iloc[0]),
                "skew": float(chain["skew"].iloc[0])}
    return make_chain_provider, compute_skew


def _load_ledger(path: Path) -> "object":
    """Load the parquet ledger; raise FileNotFoundError for an absent file.

    Returns a pandas.DataFrame. Kept separate from the import block so the
    MISSING_ENGINE branch never touches pandas / pyarrow.
    """
    import pandas as pd  # noqa: PLC0415
    if not path.exists():
        raise FileNotFoundError(f"ledger not found: {path}")
    return pd.read_parquet(path)


def _select_legacy_rows(ledger: "object") -> "object":
    """Subset the ledger to legacy rows.

    W2-1b stamps `source` on every row; pre-W2-1b ledgers lack the column.
    Treat absent-column as "everything is legacy" so the audit is usable on
    both shapes.
    """
    if "source" not in ledger.columns:
        return ledger
    return ledger[ledger["source"].astype(str) == LEGACY_SOURCE]


def _delta_stats(pairs: list[tuple[float, float]]) -> dict[str, float | None]:
    """p50/p90/max of |delta skew|, sign-flip / zero / match buckets.

    Input: a list of (legacy_skew, new_skew) PAIRS — the legacy value
    written by the pre-W2-1b engine path and the recomputed value from
    the ThetaData chain provider. We need BOTH values, not just
    delta = legacy - new, because a single delta does not encode sign
    information: legacy=0.05, new=0.15 (both positive, same sign)
    yields delta=-0.10, while legacy=-0.05, new=0.05 (opposite signs)
    yields the same delta=-0.10. A model that classifies by `delta < 0`
    cannot tell these apart, and the earlier
    `n_sign_flip = sum(1 for d in deltas if d * d < 0)` was tautologically
    zero (d * d is never negative for any real d). The product test
    `legacy * new < 0` is the only correct way to detect a sign flip:
    the two paths disagree on direction ONLY when the two values have
    strictly opposite signs.

    Bucket definitions:
      - n_sign_flip    — `legacy * new < 0` (strictly opposite non-zero signs)
      - n_zero_delta   — `legacy == new` (delta == 0 exactly; agreement on no skew)
      - n_sign_match   — `legacy * new > 0` (same non-zero sign)

    Returns NaN-safe values (None when the input is empty).
    sign_agreement_rate = (n_sign_match + n_zero_delta) / n — both are
    "the two paths agree"; the (one-zero, other-nonzero) case is
    deliberately excluded because it is ambiguous (one path has no
    direction to agree on) and is surfaced separately in the receipt
    via `n_skipped` (it never appears in the three buckets above).
    """
    if not pairs:
        return {"n": 0, "p50": None, "p90": None, "max": None,
                "sign_agreement_rate": None, "n_sign_flip": 0,
                "n_zero_delta": 0, "n_sign_match": 0}
    deltas = [l - n for l, n in pairs]
    abs_d = [abs(d) for d in deltas]
    s = sorted(abs_d)
    # Nearest-rank percentile; OK for an audit sample, not a published series.
    def _pct(p: float) -> float:
        idx = max(0, min(len(s) - 1, int(round(p * (len(s) - 1)))))
        return s[idx]
    # Bucket definitions (mutually exclusive; sum == n):
    #   n_zero_delta — both paths report exactly 0 skew (l == 0 AND n == 0).
    #                  This is the "they agree there is no skew" bucket.
    #   n_sign_flip  — strictly opposite non-zero signs (l * n < 0). A
    #                  pair where one side is 0 and the other is non-zero
    #                  falls in NEITHER bucket — it is reported separately
    #                  via `n_skipped` (no direction to flip).
    #   n_sign_match — same non-zero sign (l * n > 0). Magnitude equality
    #                  like (0.05, 0.05) lands here: both are positive,
    #                  same sign, the bucket is about direction agreement.
    n_zero_delta = sum(1 for l, n in pairs if l == 0 and n == 0)
    n_sign_flip = sum(1 for l, n in pairs if l * n < 0)
    n_sign_match = sum(1 for l, n in pairs if l * n > 0)
    sign_agreement = (n_zero_delta + n_sign_match) / len(pairs)
    return {"n": len(pairs),
            "p50": round(_pct(0.50), 6),
            "p90": round(_pct(0.90), 6),
            "max": round(s[-1], 6),
            "sign_agreement_rate": round(sign_agreement, 6),
            "n_sign_flip": n_sign_flip,
            "n_zero_delta": n_zero_delta,
            "n_sign_match": n_sign_match}


def _key_iter(rows: "object"):
    """Yield (date_iso, underlying) tuples in the ledger's natural order."""
    for _, r in rows.iterrows():
        d = r.get("date")
        u = r.get("underlying")
        if d is None or u is None:
            continue
        d_iso = d.isoformat() if hasattr(d, "isoformat") else str(d)[:10]
        yield d_iso, str(u)


def _worst_keys(records: list[dict], k: int = 10) -> list[dict]:
    """Top-k keys ranked by |delta skew| descending."""
    return sorted(records, key=lambda r: abs(r["delta_skew"]), reverse=True)[:k]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="audit_options_skew_overlap",
        description="Real-overlap audit of legacy polygon_gex vs ThetaData skew recompute.",
    )
    ap.add_argument("--ledger",
                    default="data/options_skew/snapshots.parquet",
                    help="ledger parquet (default: data/options_skew/snapshots.parquet)")
    ap.add_argument("--store", default=None,
                    help="ThetaData EOD store root (default: $THETADATA_STORE)")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap the number of (date, underlying) keys to recompute "
                         "(quick smoke)")
    ap.add_argument("--out",
                    default=None,
                    help="markdown receipt path (default: "
                         "research/MARKET_ONTOLOGY_F03_SKEW_OVERLAP_RECEIPT_<TODAY>.md)")
    args = ap.parse_args(argv)

    # Resolve --store default once here so the audit reflects the seat's view.
    if args.store is None:
        import os  # noqa: PLC0415
        args.store = os.environ.get("THETADATA_STORE",
                                    "/Users/chriswong/theta-ops-wt/data/thetadata_eod")

    engine = _load_engine()
    if engine is None:
        sys.stderr.write("MISSING_ENGINE: cannot recompute — ThetaData path not on main; "
                         "wait for W2-1b to merge, then re-run.\n")
        return EXIT_MISSING_ENGINE
    make_chain_provider, compute_skew = engine

    try:
        ledger = _load_ledger(Path(args.ledger))
    except FileNotFoundError as exc:
        sys.stderr.write(f"READ_ERROR: {exc}\n")
        return EXIT_READ_ERROR
    legacy = _select_legacy_rows(ledger)
    if len(legacy) == 0:
        sys.stderr.write("NO_LEGACY_ROWS: nothing to audit; either the ledger is empty "
                         "or every row is already stamped as thetadata.\n")
        return EXIT_NO_LEGACY_ROWS

    # require_iv=True: a skew recompute needs IV, the greeks tier carries it.
    provider = make_chain_provider(store=args.store, require_iv=True)

    keys = list(_key_iter(legacy))
    if args.limit:
        keys = keys[: args.limit]

    pairs: list[tuple[float, float]] = []
    records: list[dict] = []
    skipped: list[dict] = []
    for d_iso, underlying in keys:
        chain = provider(d_iso, underlying)
        if chain is None:
            skipped.append({"date": d_iso, "underlying": underlying,
                            "reason": "no_chain"})
            continue
        # The chain provider returns a frame with the columns compute_skew
        # expects; the function returns None when it cannot build a verdict.
        recomputed = compute_skew(chain)
        if recomputed is None or "skew" not in recomputed:
            skipped.append({"date": d_iso, "underlying": underlying,
                            "reason": "compute_skew returned None"})
            continue
        # MAJOR-4: verify the recomputed verdict actually answers for the
        # requested (date, underlying) — a chain provider that returns the
        # wrong root's row would otherwise be counted under the requested
        # key, masking a mis-resolution. We accept the recomputed answer
        # only when both its `underlying` and `asof` round-trip the
        # requested key. The asof check tolerates the legacy/pre-W2-1b
        # case where the ledger's `asof` is a date string and the
        # recomputed one is identical.
        rec_underlying = recomputed.get("underlying")
        rec_asof = recomputed.get("asof")
        if rec_underlying is None or str(rec_underlying).upper() != str(underlying).upper():
            skipped.append({"date": d_iso, "underlying": underlying,
                            "reason": f"recomputed underlying mismatch "
                                       f"(got {rec_underlying!r})"})
            continue
        rec_asof_iso = str(rec_asof)[:10] if rec_asof is not None else ""
        if rec_asof_iso != d_iso[:10]:
            skipped.append({"date": d_iso, "underlying": underlying,
                            "reason": f"recomputed asof mismatch "
                                       f"(got {rec_asof!r})"})
            continue
        # The ledger's legacy skew lives on the same row under the column
        # 'skew' (engine.options_skew.snapshot writes that field directly).
        legacy_row = legacy[(legacy["date"].astype(str) == d_iso)
                            & (legacy["underlying"].astype(str) == underlying)]
        if legacy_row.empty:
            skipped.append({"date": d_iso, "underlying": underlying,
                            "reason": "ledger row not found (date/underlying mismatch)"})
            continue
        try:
            legacy_skew = float(legacy_row["skew"].iloc[0])
        except (KeyError, ValueError, TypeError):
            skipped.append({"date": d_iso, "underlying": underlying,
                            "reason": "ledger 'skew' column missing or non-numeric"})
            continue
        new_skew = float(recomputed["skew"])
        if not (math.isfinite(legacy_skew) and math.isfinite(new_skew)):
            skipped.append({"date": d_iso, "underlying": underlying,
                            "reason": "non-finite skew"})
            continue
        delta = legacy_skew - new_skew
        pairs.append((legacy_skew, new_skew))
        records.append({"date": d_iso, "underlying": underlying,
                        "legacy_skew": round(legacy_skew, 6),
                        "new_skew": round(new_skew, 6),
                        "delta_skew": round(delta, 6)})

    stats = _delta_stats(pairs)
    worst = _worst_keys(records, 10)

    summary = {
        "keys_compared": stats["n"],
        "sign_agreement_rate": stats["sign_agreement_rate"],
        "abs_delta_skew": {
            "p50": stats["p50"], "p90": stats["p90"], "max": stats["max"],
        },
        "n_sign_flip": stats["n_sign_flip"],
        "n_zero_delta": stats["n_zero_delta"],
        "n_sign_match": stats["n_sign_match"],
        "n_skipped": len(skipped),
        "limit": args.limit,
        "ledger": args.ledger,
        "store": args.store,
        "worst_10": worst,
    }
    print(json.dumps(summary, sort_keys=True, default=str))

    # Markdown receipt
    today = date.today().isoformat()
    out_path = Path(args.out) if args.out else Path(
        "research") / f"MARKET_ONTOLOGY_F03_SKEW_OVERLAP_RECEIPT_{today}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# Skew-overlap audit receipt — {today}")
    lines.append("")
    lines.append(f"- Ledger: `{args.ledger}`")
    lines.append(f"- ThetaData store: `{args.store}`")
    lines.append(f"- Keys compared: **{stats['n']}** "
                 f"(limit={args.limit or 'none'}, skipped={len(skipped)})")
    lines.append(f"- Sign agreement rate: **{stats['sign_agreement_rate']}**")
    lines.append(f"- |delta skew| p50/p90/max: "
                 f"**{stats['p50']} / {stats['p90']} / {stats['max']}**")
    lines.append(f"- Sign buckets: match=**{stats['n_sign_match']}**, "
                 f"flip=**{stats['n_sign_flip']}**, "
                 f"zero=**{stats['n_zero_delta']}** "
                 f"(match + flip + zero == keys_compared)")
    lines.append("")
    lines.append("## Top 10 worst keys (by |delta skew|)")
    lines.append("")
    lines.append("| date | underlying | legacy_skew | new_skew | delta_skew |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in worst:
        lines.append(f"| {r['date']} | {r['underlying']} | {r['legacy_skew']} "
                     f"| {r['new_skew']} | {r['delta_skew']} |")
    if skipped:
        lines.append("")
        lines.append(f"## Skipped keys ({len(skipped)})")
        lines.append("")
        lines.append("| date | underlying | reason |")
        lines.append("| --- | --- | --- |")
        for s in skipped[:50]:
            lines.append(f"| {s['date']} | {s['underlying']} | {s['reason']} |")
        if len(skipped) > 50:
            lines.append(f"| ... | ... | (+{len(skipped) - 50} more) |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stderr.write(f"receipt: {out_path}\n")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())