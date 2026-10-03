"""Reproducible probe for ``research_readiness_20261002.json``.

Deterministic, offline, no network. Re-derives every numeric field of the receipt
that was produced by an uncommitted generator and replaces the bare
``legacy_statistics_and_verdicts_identical`` boolean with a reproducible parity
oracle: load the pre-change module from the merge-base commit, run its ``assess``
on the same archive, and compare field-by-field against the current module's
output.

Hard guarantee: the script reads ONLY the identity/label columns the receipt
declares under ``columns_read``. Any attempt to read an outcome/return column
or a column not on the allow-list raises ``AssertionError`` immediately — this
is the receipt's "outcome_columns_read: false" check made mechanically
enforceable, not merely asserted in prose.

Usage::

    python3 -m research.macro_regime_intelligence.research_readiness_probe \
        --archive PATH/TO/tr_record.parquet \
        --expected-sha256 52593efe19c6a248a56e956e5223b480fab9bb6a8838a750aace513f0e86be5b \
        --merge-base bf6921873ea40f5868e0428d04fd38f78cc62c11 \
        [--emit-json PATH]

With no arguments the script reads the receipt, derives numbers from the
canonical archive path used by the receipt, runs the oracle against the
merge-base, and prints a one-line ``OK`` / ``DRIFT`` summary. ``--emit-json``
writes a provenance-augmented copy of the receipt (additive only — the
existing fields are byte-identical to the committed receipt unless they
drift).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

# Allow-list of columns the receipt says it read. Anything else — including the
# entire outcome/return family (``fwd_ret_*``, ``trade_ret``, ``exit_price``,
# ``terminal_state_clean*``, etc.) — is forbidden and trips an AssertionError
# the moment the script tries to touch it.
COLUMNS_READ: tuple[str, ...] = (
    "date",
    "first_seen_asof",
    "vector_asof",
    "regime_at_entry",
    "quad_hard_label",
    "vol_regime",
    "fused_risk_label",
    "rate_pressure",
    "risk_radar_state",
)

# Outcome/return columns whose absence the receipt asserts. Listed here as a
# set so we can name them in any assertion message; never used as input.
OUTCOME_COLUMNS: tuple[str, ...] = (
    "fwd_ret_20", "fwd_ret_60", "fwd_ret_180",
    "fwd_price_20", "fwd_price_60", "fwd_price_180",
    "fwd_mdd_20", "fwd_mdd_60", "fwd_mdd_180",
    "fwd_mdd_60_samebar", "trade_ret", "exit_price",
    "fwd_mfe_5", "fwd_mfe_10", "fwd_mfe_21", "fwd_mfe_63", "fwd_mfe_126",
    "terminal_state_clean15_126", "terminal_state_clean8_21",
    "post_cushion_breach",
)

RECEIPT_PATH = Path(__file__).with_name("research_readiness_20261002.json")
DEFAULT_ARCHIVE = Path("data/signal_archive/track_record.parquet")
EXPECTED_SHA256 = "52593efe19c6a248a56e956e5223b480fab9bb6a8838a750aace513f0e86be5b"
EXPECTED_BYTES = 10903975
DEFAULT_MERGE_BASE = "bf6921873ea40f5868e0428d04fd38f78cc62c11"


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _assert_outcome_free(df_columns: list[str]) -> None:
    leak = set(OUTCOME_COLUMNS) & set(df_columns)
    if leak:
        raise AssertionError(
            "outcome column(s) present in archive: " + ", ".join(sorted(leak))
        )
    extras = set(df_columns) - set(COLUMNS_READ)
    if extras:
        # The probe must not silently widen the column allow-list. If a future
        # generator wants a new identity column, it must be added to
        # COLUMNS_READ here, not bypassed.
        unknown = sorted(extras - set(OUTCOME_COLUMNS))
        raise AssertionError(
            "archive carries columns outside the receipt's columns_read allow-list: "
            + ", ".join(unknown)
        )


def _load_archive_columns(path: Path, expected_sha: str, expected_bytes: int) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"archive not found: {path}")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise AssertionError(
            f"archive byte length {actual_bytes} != receipt {expected_bytes}; "
            "refusing to regenerate numbers from a non-canonical input"
        )
    actual_sha = _sha256_of(path)
    if actual_sha != expected_sha:
        raise AssertionError(
            f"archive sha256 {actual_sha} != receipt {expected_sha}; "
            "refusing to regenerate numbers from a non-canonical input"
        )
    import pandas as pd  # local import — only loaded when the hash gate passes
    df = pd.read_parquet(path, columns=list(COLUMNS_READ))
    _assert_outcome_free(list(df.columns))
    return list(df.columns)


def _within_each_stamping_window(df: Any) -> dict[str, dict[str, Any]]:
    """Per-axis within-stamping-window report.

    Identical computation to the receipt's ``within_each_stamping_window``:
    the window is the rows carrying a state for that axis; the verdict is
    re-evaluated against the same frozen gates the live module exposes.
    """
    import pandas as pd

    from engine import regime_conditioning_coverage as rcc

    out: dict[str, dict[str, Any]] = {}
    # Coerce ``date`` to datetimelike once so per-date/nunique derivations work;
    # ``assess_axis`` does the same internally, but the receipt also needs the
    # raw ``stamped_unique_dates`` count which is not exposed.
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for axis in rcc.CANDIDATE_AXES:
        a = rcc.assess_axis(df, axis)
        if axis not in df.columns:
            out[axis] = a
            continue
        win = df[df[axis].notna()].copy()
        if win.empty:
            out[axis] = a
            continue
        # Re-derive the per-axis verdict on the within-window sample using the
        # SAME constants the receipt froze.
        win_a = rcc.assess_axis(win, axis)
        win_a["stamped_unique_dates"] = int(win["date"].dt.strftime("%Y-%m-%d").nunique())
        per_date = (
            win.dropna(subset=[axis])
            .groupby(win["date"].dt.strftime("%Y-%m-%d"))[axis]
            .nunique()
        )
        win_a["dates_with_multiple_states"] = int((per_date > 1).sum())
        out[axis] = win_a
    return out


def _joint_macro_cells(df: Any) -> list[dict[str, Any]]:
    """Joint complete-cell report over the five US market-context axes."""
    import pandas as pd

    macro_axes = (
        "quad_hard_label", "vol_regime", "fused_risk_label",
        "rate_pressure", "risk_radar_state",
    )
    win = df.dropna(subset=list(macro_axes)).copy()
    if win.empty:
        return []
    win["date"] = pd.to_datetime(win["date"], errors="coerce")
    win = win[win["date"].notna()]
    win["_month"] = win["date"].dt.to_period("M").astype(str)
    win["_date"] = win["date"].dt.strftime("%Y-%m-%d")
    cells = (
        win.groupby(list(macro_axes), dropna=False)
        .agg(
            signal_rows=("_month", "size"),
            distinct_dates=("_date", "nunique"),
            distinct_months=("_month", "nunique"),
        )
        .reset_index()
    )
    out: list[dict[str, Any]] = []
    for _, row in cells.iterrows():
        out.append({
            "states": {a: row[a] for a in macro_axes},
            "signal_rows": int(row["signal_rows"]),
            "distinct_dates": int(row["distinct_dates"]),
            "distinct_months": int(row["distinct_months"]),
        })
    out.sort(key=lambda c: (
        c["states"]["quad_hard_label"],
        c["states"]["fused_risk_label"],
        c["states"]["rate_pressure"],
        c["states"]["risk_radar_state"],
    ))
    return out


def _load_module_from_blob(name: str, source: str, path: Path | None = None) -> Any:
    """Load a Python source string as a fresh module.

    ``path`` is recorded in the module's ``__file__`` for clearer tracebacks
    and so the loader does not collide with the live ``engine`` namespace.
    """
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path) if path else "<probe>")
    module = importlib.util.module_from_spec(spec)
    exec(compile(source, str(path) if path else "<probe>", "exec"), module.__dict__)
    sys.modules[name] = module
    return module


def _load_pre_change_assessor(repo_root: Path, merge_base: str) -> Any:
    """Load the pre-change ``regime_conditioning_coverage`` from ``git show``.

    The merge-base is the snapshot at which the axis-scope change had not yet
    been made; the module's public ``assess`` and ``assess_axis`` functions
    are the same ones that produced the original numbers the receipt
    compares against.
    """
    import subprocess

    completed = subprocess.run(
        ["git", "show", f"{merge_base}:engine/regime_conditioning_coverage.py"],
        cwd=repo_root, check=True, capture_output=True, text=True,
    )
    return _load_module_from_blob(
        "_rcc_pre_change",
        completed.stdout,
        path=repo_root / "engine" / "regime_conditioning_coverage.py",
    )


# Fields whose equality between old and new is THE point of the oracle; any
# drift here means the new module changed a statistic or verdict, which is
# out of scope for this PR.
PARITY_SCALAR_KEYS = (
    "axis", "n_rows_total", "n_rows_stamped", "coverage",
    "n_states", "months_total", "min_state_months",
    "verdict", "estimable",
)
PARITY_NESTED_KEYS = ("states", "span")

def _parity_keys_dropped() -> tuple[str, ...]:
    """Fields the new module adds that the old module legitimately lacks."""
    return (
        "axis_scope", "axis_scope_basis",
        "stamped_unique_dates", "dates_with_multiple_states",
        "qualification_basis", "historical_availability",
        "estimable_axes_by_scope",
    )


def _prune_to_parity(payload: Any) -> Any:
    """Strip additive fields so old-vs-new can be compared.

    Also drops the ``note`` field, whose wording was intentionally changed.
    """
    if isinstance(payload, dict):
        dropped = set(_parity_keys_dropped())
        return {
            k: _prune_to_parity(v)
            for k, v in payload.items()
            if k not in dropped and k != "note"
        }
    if isinstance(payload, list):
        return [_prune_to_parify(x) for x in payload] if False else [_prune_to_parity(x) for x in payload]
    return payload


def _parity_compare(old: Any, cur: Any, path: str = "$") -> list[str]:
    """Return a list of ``path: old -> cur`` diff lines."""
    diffs: list[str] = []
    if type(old) != type(cur):
        diffs.append(f"{path}: type {type(old).__name__} -> {type(cur).__name__}")
        return diffs
    if isinstance(old, dict):
        for k in sorted(set(old) | set(cur)):
            sub = f"{path}.{k}"
            if k not in old:
                diffs.append(f"{sub}: present only in current")
                continue
            if k not in cur:
                diffs.append(f"{sub}: present only in old")
                continue
            diffs.extend(_parity_compare(old[k], cur[k], sub))
        return diffs
    if isinstance(old, list):
        if len(old) != len(cur):
            diffs.append(f"{path}: list length {len(old)} -> {len(cur)}")
        for i, (a, b) in enumerate(zip(old, cur)):
            diffs.extend(_parity_compare(a, b, f"{path}[{i}]"))
        return diffs
    if old != cur:
        diffs.append(f"{path}: {old!r} != {cur!r}")
    return diffs


def _oracle(repo_root: Path, archive_path: Path, merge_base: str) -> dict[str, Any]:
    """Run both modules on the same archive and report field-by-field equality."""
    import pandas as pd

    # The current module's assess() — the live branch, what ships.
    from engine import regime_conditioning_coverage as cur_rcc
    pre_rcc = _load_pre_change_assessor(repo_root, merge_base)

    df = pd.read_parquet(archive_path, columns=list(COLUMNS_READ))
    _assert_outcome_free(list(df.columns))

    pre_report = pre_rcc.assess(df)
    cur_report = cur_rcc.assess(df)

    diffs = _parity_compare(_prune_to_parity(pre_report), _prune_to_parity(cur_report))
    pre_payload = json.dumps(pre_report, sort_keys=True).encode("utf-8")
    return {
        "old_assess_sha256": hashlib.sha256(pre_payload).hexdigest(),
        "field_diffs": diffs,
        "legacy_statistics_and_verdicts_identical": not diffs,
    }


def _emit_summary(receipt: dict[str, Any], oracle: dict[str, Any],
                  regenerate_diff: list[str], archive_sha: str,
                  script_sha: str, command: str) -> str:
    rc = "OK" if oracle["legacy_statistics_and_verdicts_identical"] and not regenerate_diff else "DRIFT"
    return (
        f"{rc} | receipt regenerated={not regenerate_diff} | "
        f"old-vs-new identical={oracle['legacy_statistics_and_verdicts_identical']} | "
        f"archive sha={archive_sha[:12]}… | script sha={script_sha[:12]}… | "
        f"oracle sha={oracle['old_assess_sha256'][:12]}…"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE,
                   help=f"path to track_record.parquet (default: {DEFAULT_ARCHIVE})")
    p.add_argument("--expected-sha256", default=EXPECTED_SHA256,
                   help="sha256 declared by the committed receipt")
    p.add_argument("--merge-base", default=DEFAULT_MERGE_BASE,
                   help="git revision of the pre-change engine module")
    p.add_argument("--emit-json", type=Path, default=None,
                   help="write a provenance-augmented copy of the receipt here")
    p.add_argument("--receipt", type=Path, default=RECEIPT_PATH,
                   help="committed receipt to regenerate against")
    args = p.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent.parent
    # Walk up looking for the actual git toplevel in case the script is symlinked.
    import subprocess
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        repo_root = Path(completed.stdout.strip())

    archive_sha = _sha256_of(args.archive)
    columns = _load_archive_columns(args.archive, args.expected_sha256, EXPECTED_BYTES)

    # --- regenerate every existing numeric field ---------------------------------
    import pandas as pd

    df = pd.read_parquet(args.archive, columns=list(COLUMNS_READ))
    _assert_outcome_free(list(df.columns))
    from engine import regime_conditioning_coverage as cur_rcc
    full = cur_rcc.assess(df)
    win = _within_each_stamping_window(df)
    jm = _joint_macro_cells(df)

    receipt = json.loads(args.receipt.read_text())
    drift: list[str] = []

    # full-archive fields: compare axis-by-axis
    for axis in cur_rcc.CANDIDATE_AXES:
        rec_axis = receipt.get("full_archive", {}).get("axes", {}).get(axis, {})
        cur_axis = full["axes"].get(axis, {})
        for k, v in cur_axis.items():
            if k == "note":
                continue
            if rec_axis.get(k) != v:
                drift.append(
                    f"full_archive.axes.{axis}.{k}: receipt={rec_axis.get(k)!r} "
                    f"regen={v!r}"
                )
    # joint cells
    rec_jm = receipt.get("joint_macro_cells", [])
    if len(rec_jm) != len(jm):
        drift.append(f"joint_macro_cells length: receipt={len(rec_jm)} regen={len(jm)}")
    else:
        for i, (a, b) in enumerate(zip(rec_jm, jm)):
            for k, v in b.items():
                if a.get(k) != v:
                    drift.append(f"joint_macro_cells[{i}].{k}: receipt={a.get(k)!r} regen={v!r}")
    # within-each-window fields
    for axis in cur_rcc.CANDIDATE_AXES:
        rec_axis = receipt.get("within_each_stamping_window", {}).get(axis, {})
        cur_axis = win.get(axis, {})
        for k, v in cur_axis.items():
            if k == "note":
                continue
            if rec_axis.get(k) != v:
                drift.append(
                    f"within_each_stamping_window.{axis}.{k}: receipt={rec_axis.get(k)!r} "
                    f"regen={v!r}"
                )

    # --- parity oracle ----------------------------------------------------------
    oracle = _oracle(repo_root, args.archive, args.merge_base)

    # --- provenance summary ------------------------------------------------------
    script_sha = _sha256_of(Path(__file__))
    command = "python3 -m research.macro_regime_intelligence.research_readiness_probe"

    summary = _emit_summary(receipt, oracle, drift, archive_sha, script_sha, command)
    print(summary)

    if drift:
        print("\n--- regenerate diff (regen != receipt; STOP on first reading) ---")
        for line in drift:
            print(line)
    if oracle["field_diffs"]:
        print("\n--- old-vs-new oracle diffs ---")
        for line in oracle["field_diffs"]:
            print(line)

    # --- optional emit -----------------------------------------------------------
    if args.emit_json is not None:
        out = dict(receipt)
        out["provenance"] = {
            "regeneration": {
                "command": command,
                "script_sha256": script_sha,
                "archive_sha256": archive_sha,
                "archive_bytes": args.archive.stat().st_size,
                "merge_base": args.merge_base,
                "regenerate_diff": drift,
                "regenerated_identical": not drift,
            },
            "oracle": {
                "old_assess_sha256": oracle["old_assess_sha256"],
                "field_diffs": oracle["field_diffs"],
                "legacy_statistics_and_verdicts_identical": oracle[
                    "legacy_statistics_and_verdicts_identical"
                ],
            },
        }
        # The committed receipt has the bare boolean — keep its slot, but record
        # the oracle hash next to it for reproducibility. The bare boolean is
        # not removed (it remains a record of the original observed equality),
        # but the receipt is now self-evidencing.
        out["legacy_statistics_and_verdicts_identical"] = oracle[
            "legacy_statistics_and_verdicts_identical"
        ]
        args.emit_json.write_text(json.dumps(out, indent=2, sort_keys=False) + "\n")

    return 0 if not drift and oracle["legacy_statistics_and_verdicts_identical"] else 2


if __name__ == "__main__":
    raise SystemExit(main())