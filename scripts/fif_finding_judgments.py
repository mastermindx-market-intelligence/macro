#!/usr/bin/env python3
"""FIF Q2 CLI: record and replay finding judgments (A48).

Thin command surface over ``engine.fundamental_forensics.finding_judgments``:

* ``record-state`` adapts a nightly workbench build state at an explicit
  ``--recorded-at`` run clock (the state's ``generated_at`` is recorded as
  the run's source clock; every company in the state is in the withdrawal
  scope);
* ``record-kernel`` records kernel finding rows at an explicit clock with no
  withdrawal scope;
* ``replay`` reconstructs the then-known beliefs at a mandatory cutoff;
* ``history`` prints one subject's full chain.

One JSON document is printed to stdout. Exit 0 on success, 2 on a typed
refusal, 3 on an effect-unknown write; no traceback is ever printed. The
store is a local directory via ``--local-store`` or the configured production
dataset store; recording requires the strict conditional write protocol and
refuses otherwise. Lanes run this only against temporary local stores. No
wall clock is read: every timestamp comes from the arguments.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.fundamental_forensics import finding_judgments as FJ  # noqa: E402
from engine.fundamental_forensics.production_datasets import (  # noqa: E402
    build_production_dataset_store,
)


def _load_json_document(path: Path) -> Any:
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def _emit(document: Any) -> int:
    json.dump(document, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _emit_error(exc: BaseException, exit_code: int) -> int:
    _emit({
        "ok": False,
        "error": {
            "type": type(exc).__name__,
            "code": getattr(exc, "code", None) or "unexpected_error",
            "message": str(exc),
        },
    })
    return exit_code


def _build_store(args: argparse.Namespace):
    store = build_production_dataset_store(args.local_store)
    if store is None:
        raise FJ.FindingJudgmentError(
            "no judgment store is configured; pass --local-store DIR", code="store_required"
        )
    return store


def _build_write_store(args: argparse.Namespace):
    store = _build_store(args)
    capability = getattr(store, "validate_strict_conditional_write_capability", None)
    if not callable(getattr(store, "put_bytes_strict_conditional", None)) or capability is None:
        raise FJ.FindingJudgmentError(
            "store lacks the strict conditional write protocol required for judgment recording",
            code="store_capability",
        )
    try:
        capability()
    except Exception as exc:  # noqa: BLE001 - the store refused its own protocol check
        raise FJ.FindingJudgmentError(
            f"store refused the strict conditional write capability check: {exc}", code="store_capability"
        ) from exc
    return store


def _cmd_record_state(args: argparse.Namespace) -> int:
    store = _build_write_store(args)
    state = _load_json_document(Path(args.state))
    rows, scope_entities, source_generated_at, company_identities = FJ.workbench_rows_and_companies_from_state(state)
    return _emit(
        FJ.record_judgments(
            store,
            kind="workbench",
            rows=rows,
            recorded_at=args.recorded_at,
            source_generated_at=source_generated_at,
            scope_entities=scope_entities,
            company_identities=company_identities,
        )
    )


def _cmd_record_kernel(args: argparse.Namespace) -> int:
    store = _build_write_store(args)
    rows = _load_json_document(Path(args.findings))
    if not isinstance(rows, list):
        raise FJ.FindingJudgmentError("kernel findings document must be a list of rows", code="rows_shape")
    return _emit(
        FJ.record_judgments(
            store,
            kind="kernel",
            rows=rows,
            recorded_at=args.recorded_at,
            source_generated_at=args.source_generated_at,
        )
    )


def _cmd_replay(args: argparse.Namespace) -> int:
    store = _build_store(args)
    return _emit(
        FJ.replay_then_known(
            store,
            recorded_cutoff=args.recorded_cutoff,
            kind=args.kind,
            entity_ref=args.entity_ref,
        )
    )


def _cmd_history(args: argparse.Namespace) -> int:
    store = _build_store(args)
    chain = FJ.history(store, args.subject)
    return _emit({"subject": args.subject, "records": list(chain)})


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fif_finding_judgments", description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    record_state = subparsers.add_parser("record-state", help="record judgments from a workbench build state")
    record_state.add_argument("--state", required=True, help="path to the workbench state JSON (plain or gzipped)")
    record_state.add_argument("--recorded-at", required=True, help="aware UTC ISO timestamp of this run")
    record_state.add_argument("--local-store", default=None, help="local directory store root")
    record_state.set_defaults(handler=_cmd_record_state)

    record_kernel = subparsers.add_parser("record-kernel", help="record kernel finding rows at an explicit clock")
    record_kernel.add_argument("--findings", required=True, help="path to a JSON list of kernel finding rows")
    record_kernel.add_argument("--recorded-at", required=True, help="aware UTC ISO timestamp of this run")
    record_kernel.add_argument(
        "--source-generated-at", default=None, help="aware UTC ISO timestamp of the source build"
    )
    record_kernel.add_argument("--local-store", default=None, help="local directory store root")
    record_kernel.set_defaults(handler=_cmd_record_kernel)

    replay = subparsers.add_parser("replay", help="reconstruct then-known beliefs at a cutoff")
    replay.add_argument("--recorded-cutoff", required=True, help="aware UTC ISO cutoff (mandatory)")
    replay.add_argument("--kind", default=None, choices=["workbench", "kernel"])
    replay.add_argument("--entity-ref", default=None)
    replay.add_argument("--local-store", default=None, help="local directory store root")
    replay.set_defaults(handler=_cmd_replay)

    history_parser = subparsers.add_parser("history", help="print one subject's full judgment chain")
    history_parser.add_argument("--subject", required=True, help="subject key")
    history_parser.add_argument("--local-store", default=None, help="local directory store root")
    history_parser.set_defaults(handler=_cmd_history)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except FJ.FindingJudgmentEffectUnknownError as exc:
        return _emit_error(exc, 3)
    except FJ.FindingJudgmentError as exc:
        return _emit_error(exc, 2)
    except Exception as exc:  # noqa: BLE001 - the CLI never prints a traceback
        return _emit_error(exc, 2)


if __name__ == "__main__":
    sys.exit(main())
