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
enforceable, not merely asserted in prose. The guard is enforced twice:
BEFORE any data read (the allow-list itself is scanned against the forbidden
rule so a future contributor cannot widen it accidentally), and AFTER each
read (the loaded columns must equal ``columns_read`` exactly). The parquet
schema is read separately and recorded under ``provenance.regeneration`` so a
reviewer can see how many columns the archive carries and which forbidden
ones the script never touched.

Usage::

    git show bf6921873ea40f5868e0428d04fd38f78cc62c11:data/signal_archive/track_record.parquet \
        > /tmp/track_record_canonical.parquet
    python3 -m research.macro_regime_intelligence.research_readiness_probe \
        --archive /tmp/track_record_canonical.parquet \
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
import json
import sys
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

# Outcome/return columns the receipt records as not read. Listed here as a
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

# Module-level forbidden set: the same 20 names the receipt enumerates plus
# three additional names the archive also carries (``outcome``, ``exit_date``,
# ``exit_type``) and any column whose name matches a pattern rule. The script
# cannot read any of these — neither through ``columns_read`` nor through the
# schema enumeration — and the receipt records them under
# ``provenance.regeneration.outcome_columns_in_archive_not_read`` so a
# reviewer can audit the gap from a current checkout.
OUTCOME_FORBIDDEN_NAMES: frozenset[str] = frozenset(OUTCOME_COLUMNS) | frozenset(
    {"outcome", "exit_date", "exit_type"}
)


def _is_forbidden(name: str) -> bool:
    """Return True if ``name`` is an outcome/return column the script may not read.

    A name is forbidden if it is in :data:`OUTCOME_FORBIDDEN_NAMES`, OR if it
    starts with ``fwd_`` or ``exit_``, OR if it contains ``outcome``,
    ``trade_ret``, ``mfe``, ``mdd`` or ``terminal_state`` (as a substring).
    """
    if name in OUTCOME_FORBIDDEN_NAMES:
        return True
    if name.startswith("fwd_") or name.startswith("exit_"):
        return True
    return any(needle in name for needle in ("outcome", "trade_ret", "mfe", "mdd", "terminal_state"))


def _assert_columns_read_safe() -> None:
    """Pre-read guard: no name in :data:`COLUMNS_READ` is forbidden.

    Runs BEFORE any data read so a future contributor who adds an outcome
    column to ``COLUMNS_READ`` hits the assertion immediately rather than
    silently loading the archive's full schema.
    """
    for col in COLUMNS_READ:
        if _is_forbidden(col):
            raise AssertionError(
                f"COLUMNS_READ contains a forbidden outcome column: {col!r}; "
                "remove it from COLUMNS_READ before any data read"
            )


def _archive_schema_names(path: Path) -> list[str]:
    """Return the parquet column names without reading any row data.

    Used to record ``archive_column_count`` and
    ``outcome_columns_in_archive_not_read`` in the receipt's provenance so a
    reviewer can audit, from a current checkout, how many columns the
    archive carries and which forbidden ones this script never touched.
    """
    import pyarrow.parquet as pq
    schema = pq.ParquetFile(str(path)).schema
    return [str(field.name) for field in schema]

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
    """Post-read guard: the loaded columns must equal ``COLUMNS_READ`` exactly.

    The read is performed with ``columns=list(COLUMNS_READ)`` so the loaded
    frame should match one-for-one. If anything else appears — including a
    forbidden outcome column that slipped past the pre-read guard — the
    read went somewhere the script does not authorise; the assertion names
    the discrepancy so a future contributor cannot silently widen the allow
    list.
    """
    loaded = list(df_columns)
    expected = list(COLUMNS_READ)
    if loaded != expected:
        leaked_forbidden = [c for c in loaded if _is_forbidden(c)]
        if leaked_forbidden:
            raise AssertionError(
                "loaded columns include a forbidden outcome column: "
                + ", ".join(repr(c) for c in leaked_forbidden)
            )
        raise AssertionError(
            "loaded columns do not match COLUMNS_READ exactly: "
            f"loaded={loaded!r} expected={expected!r}"
        )


_REPRODUCE_STEP = (
    f"Reproduce the canonical bytes with: "
    f"`git show {DEFAULT_MERGE_BASE}:data/signal_archive/track_record.parquet "
    f"> /tmp/track_record_canonical.parquet`"
)


def _load_archive_columns(path: Path, expected_sha: str, expected_bytes: int) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"archive not found: {path}")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise AssertionError(
            f"archive byte length {actual_bytes} != receipt {expected_bytes}; "
            "refusing to regenerate numbers from a non-canonical input. "
            + _REPRODUCE_STEP
        )
    actual_sha = _sha256_of(path)
    if actual_sha != expected_sha:
        raise AssertionError(
            f"archive sha256 {actual_sha} != receipt {expected_sha}; "
            "refusing to regenerate numbers from a non-canonical input. "
            + _REPRODUCE_STEP
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
        return [_prune_to_parity(x) for x in payload]
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


def _two_way_diff(receipt_val: Any, regen_val: Any,
                  skip_keys: tuple[str, ...] = (),
                  path: str = "$") -> list[str]:
    """Two-way field-by-field diff: a key present on only one side is a failure.

    Used for the receipt-vs-regeneration check. ``skip_keys`` is a tuple of
    dict keys (compared at the current level only) whose values are not
    compared — used to exclude the free-text ``note`` fields whose wording
    is the engine's, not the receipt's, contract.

    Output lines name the dotted path of the divergence and a short reason
    so a reviewer can locate the failure on a single read.
    """
    diffs: list[str] = []
    if type(receipt_val) != type(regen_val):
        diffs.append(
            f"{path}: type {type(receipt_val).__name__} (receipt) != "
            f"{type(regen_val).__name__} (regen)"
        )
        return diffs
    if isinstance(receipt_val, dict):
        for k in sorted(set(receipt_val) | set(regen_val)):
            if k in skip_keys:
                continue
            sub = f"{path}.{k}"
            if k not in receipt_val:
                diffs.append(f"{sub}: present only in regen")
                continue
            if k not in regen_val:
                diffs.append(f"{sub}: present only in receipt")
                continue
            diffs.extend(_two_way_diff(
                receipt_val[k], regen_val[k], skip_keys, sub,
            ))
        return diffs
    if isinstance(receipt_val, list):
        if len(receipt_val) != len(regen_val):
            diffs.append(
                f"{path}: list length {len(receipt_val)} (receipt) != "
                f"{len(regen_val)} (regen)"
            )
        for i in range(min(len(receipt_val), len(regen_val))):
            diffs.extend(_two_way_diff(
                receipt_val[i], regen_val[i], skip_keys, f"{path}[{i}]",
            ))
        return diffs
    if receipt_val != regen_val:
        diffs.append(f"{path}: receipt={receipt_val!r} regen={regen_val!r}")
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

    # --- R1b: pre-read guard on COLUMNS_READ itself ----------------------------
    # Runs before any data read so a future contributor who adds an outcome
    # column to ``COLUMNS_READ`` hits the assertion immediately rather than
    # silently widening the allow-list.
    _assert_columns_read_safe()

    repo_root = Path(__file__).resolve().parent.parent.parent
    # Walk up looking for the actual git toplevel in case the script is symlinked.
    import subprocess
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        repo_root = Path(completed.stdout.strip())

    # --- R3: hash gate runs first; the error message prints the reproduction
    #     step so a reviewer hitting a stale or different archive knows
    #     exactly how to recover the canonical bytes.
    archive_sha = _sha256_of(args.archive)
    _load_archive_columns(args.archive, args.expected_sha256, EXPECTED_BYTES)

    # --- R1c: schema-only read (metadata page, no rows) so the receipt can
    #     record the archive's full column count and the sorted list of
    #     forbidden outcome columns it never read.
    schema_names = _archive_schema_names(args.archive)
    archive_column_count = len(schema_names)
    outcome_columns_in_archive_not_read = sorted(
        n for n in schema_names if _is_forbidden(n)
    )

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

    # --- R2: full, two-way regeneration check --------------------------------
    # The whole ``full_archive`` object (except its free-text ``note``) plus
    # ``joint_macro_cells`` and ``within_each_stamping_window`` are compared
    # in BOTH directions: a key present on only one side is a failure named
    # by its dotted path. The previous one-way check only flagged regen keys
    # the receipt was missing; a receipt-only key was silent.
    drift.extend(_two_way_diff(
        receipt.get("full_archive", {}), full,
        skip_keys=("note",), path="full_archive",
    ))
    drift.extend(_two_way_diff(
        receipt.get("joint_macro_cells", []), jm,
        path="joint_macro_cells",
    ))
    drift.extend(_two_way_diff(
        receipt.get("within_each_stamping_window", {}), win,
        skip_keys=("note",), path="within_each_stamping_window",
    ))

    # --- parity oracle ----------------------------------------------------------
    oracle = _oracle(repo_root, args.archive, args.merge_base)

    # --- provenance summary ------------------------------------------------------
    script_sha = _sha256_of(Path(__file__))
    # R3: command is the two-step reproduction so a reviewer can recover the
    # canonical bytes from a current checkout, not just trust the receipt's
    # bare ``python3 -m ...`` invocation that pointed at a path that no
    # longer matches the size/sha on main.
    command = (
        f"git show {args.merge_base}:data/signal_archive/track_record.parquet "
        f"> /tmp/track_record_canonical.parquet && "
        f"python3 -m research.macro_regime_intelligence.research_readiness_probe "
        f"--archive /tmp/track_record_canonical.parquet "
        f"--expected-sha256 {args.expected_sha256} "
        f"--merge-base {args.merge_base}"
    )

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
        # R2: every regenerable field is rebuilt from the REGENERATED values
        # (not carried from the committed receipt). Non-regenerable narrative
        # fields are carried from the receipt and listed by name in
        # ``provenance.regeneration.carried_fields`` so a reviewer can see,
        # on a single read, which top-level keys the script does not own.
        out = dict(receipt)
        regen_top_level = {
            "full_archive",
            "joint_macro_cells",
            "within_each_stamping_window",
            "legacy_statistics_and_verdicts_identical",
            "provenance",
        }
        out["full_archive"] = full
        out["joint_macro_cells"] = jm
        out["within_each_stamping_window"] = win
        out["legacy_statistics_and_verdicts_identical"] = oracle[
            "legacy_statistics_and_verdicts_identical"
        ]
        carried_fields = sorted(k for k in out if k not in regen_top_level)
        out["provenance"] = {
            "regeneration": {
                "command": command,
                "script_sha256": script_sha,
                "archive_sha256": archive_sha,
                "archive_bytes": args.archive.stat().st_size,
                "merge_base": args.merge_base,
                "archive_source": {
                    "commit": args.merge_base,
                    "path": "data/signal_archive/track_record.parquet",
                    "bytes": EXPECTED_BYTES,
                    "sha256": args.expected_sha256,
                },
                "archive_column_count": archive_column_count,
                "outcome_columns_in_archive_not_read":
                    outcome_columns_in_archive_not_read,
                "regenerate_diff": drift,
                "regenerated_identical": not drift,
                "carried_fields": carried_fields,
            },
            "oracle": {
                "old_assess_sha256": oracle["old_assess_sha256"],
                "field_diffs": oracle["field_diffs"],
                "legacy_statistics_and_verdicts_identical": oracle[
                    "legacy_statistics_and_verdicts_identical"
                ],
            },
        }
        args.emit_json.write_text(json.dumps(out, indent=2, sort_keys=False) + "\n")

    return 0 if not drift and oracle["legacy_statistics_and_verdicts_identical"] else 2


if __name__ == "__main__":
    raise SystemExit(main())