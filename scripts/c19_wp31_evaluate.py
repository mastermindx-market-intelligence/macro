"""C19 WP31 evaluator — MANUAL SEAT CLI (wave-3 spec §2).

Governing documents
-------------------
- Preregistration: ``research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md``
  at PREREG_COMMIT ``8e1950932b29f89a89da94c50ccef4ef5f2d8d1c``
  (amendments A1-A4 in its §10).  §9 binds this module: "owners" are
  the incumbent producers, the "natural clock" is the next scheduled
  quarterly release, and the read is a MANUAL seat run (no workflow,
  no cron, no schedule).  §6 binds the exposure ledger.  The prereg
  wins any conflict with the build spec.
- Frozen wave-3 build spec: ``WP31_WAVE3_SPEC.md`` (seat stage),
  sha256 ``8b3cf32fab638a106921be7ae860a24b6892e71be75d3970eee1702fd31c56fe``.

The CLI is the manual half of wave 3.  It holds an exclusive
``fcntl.flock`` over ``<exposure_path>.lock`` for the WHOLE run
(spec §2 / R5), so concurrent evaluator invocations serialize on the
exposure ledger.  It builds :class:`ProductionInputs`, calls the
injected-I/O :func:`run_evaluation`, and writes only the report —
the ``episodes`` carry LABEL VALUES (prereg §3.3) and must never be
written or printed.

Exit codes:
  0  ok
  2  a gates ``WP31Refusal`` (or the module's refusal type) — single
     stderr line naming the refusal
  3  lock busy — single stderr line

Standard library only at module level; every incumbent is lazy.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import fcntl
import json
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent   # scripts/* -> repo root
sys.path.insert(0, str(_ROOT))

__all__ = ["main"]


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="c19_wp31_evaluate",
        description=(
            "Manual seat run of the C19 WP31 incremental-information "
            "evaluator (wave-3 spec §2). Holds an exclusive flock on "
            "<exposure-path>.lock and writes only the report."
        ),
    )
    p.add_argument("--repo", required=True, type=Path,
                   help="Full checkout that owns the prereg and trial ledger")
    p.add_argument("--exposure-path", required=True, type=Path,
                   help="JSONL ledger of label-read exposure (read+write)")
    p.add_argument("--out", required=True, type=Path,
                   help="Path the JSON report is written to (atomic replace)")
    p.add_argument("--prior-reads", type=Path, default=None,
                   help="Optional JSON list forwarded as prior_reads")
    p.add_argument("--now", default=None,
                   help="Override 'now' (tests only): ISO-8601 with tz offset")
    return p


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_now(value: str | None) -> datetime:
    """ISO-8601 -> aware datetime. ``None`` -> datetime.now(timezone.utc)."""
    if value is None:
        return datetime.now(timezone.utc)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("--now must be timezone-aware (ISO-8601 with offset)")
    return parsed


def _load_prior_reads(path: Path | None) -> Sequence[Mapping[str, Any]]:
    if path is None:
        return ()
    if not path.exists():
        raise FileNotFoundError(f"--prior-reads not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, list):
        raise ValueError("--prior-reads must be a JSON list of read maps")
    return tuple(payload)


def _write_atomic(out: Path, payload: Mapping[str, Any]) -> None:
    """Atomic JSON write — tmp in the same dir, ``os.replace`` over the target.

    A crash between the tmp write and the rename leaves the tmp file but the
    canonical ``out`` untouched (the runner / next invocation sees the
    previous report and is free to overwrite).
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = -1, ""
    try:
        # ``os.path.join`` + ``tempfile.mkstemp`` would import tempfile at
        # module scope; keep the import lazy to honour the "stdlib at module
        # level, anything else lazy" discipline.
        import tempfile

        fd, tmp_path = tempfile.mkstemp(prefix=".c19-wp31-", suffix=".json.tmp",
                                       dir=str(out.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(dict(payload), fh, sort_keys=True)
        os.replace(tmp_path, out)
        tmp_path = ""  # consumed
    finally:
        if tmp_path:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_path)


def _print_summary(out: Path, result: Mapping[str, Any], counts: Mapping[str, int]) -> None:
    report = result.get("report") or {}
    n_episodes = result.get("episode_count", 0)
    label_pending = result.get("label_pending", 0)
    n_exhibit_failures = len(result.get("exhibit_failures") or [])
    n_eligible = report.get("eligible", 0)
    verdict = report.get("verdict", "")
    look = report.get("look", "")
    print(f"episode_count={n_episodes}")
    print(f"label_pending={label_pending}")
    print(f"exhibit_failures={n_exhibit_failures}")
    print(f"report.eligible={n_eligible}")
    print(f"report.verdict={verdict}")
    print(f"report.look={look}")
    for key in sorted(counts):
        print(f"adapter_counts.{key}={counts[key]}")
    print(f"out={out}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    now = _parse_now(args.now)
    prior_reads = _load_prior_reads(args.prior_reads)

    # Lock: fcntl.flock on <exposure-path>.lock for the WHOLE run.  Busy ->
    # exit 3 with one stderr line.  Spec §2.
    lock_path = Path(str(args.exposure_path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fh = lock_path.open("w", encoding="utf-8")
    try:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            print(
                f"c19_wp31_evaluate: exposure ledger is busy ({exc!r}); retry later",
                file=sys.stderr,
            )
            return 3

        from scripts import c19_wp31_production as prod
        from scripts import c19_wp31_runner as runner
        from scripts import c19_wp31_gates as gates

        inputs = prod.ProductionInputs(repo=args.repo, now=now)
        try:
            result = runner.run_evaluation(**inputs.run_kwargs(
                args.exposure_path, prior_reads=prior_reads,
            ))
        except gates.WP31Refusal as exc:
            print(f"c19_wp31_evaluate: refused ({exc.gate}): {exc}", file=sys.stderr)
            return 2

        out_payload = {
            "report": result["report"],
            "gates": result["gates"],
            "label_pending": result["label_pending"],
            "episode_count": result["episode_count"],
            "exhibit_failures": len(result["exhibit_failures"] or []),
            "adapter_counts": dict(inputs.counts),
        }
        _write_atomic(args.out, out_payload)
        _print_summary(args.out, result, inputs.counts)
        return 0
    finally:
        with contextlib.suppress(Exception):
            lock_fh.close()


if __name__ == "__main__":
    raise SystemExit(main())