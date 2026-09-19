"""One-shot operator for deep-reading the deterministic Research Vault head.

This command creates no scheduler. It reads the existing strict catalog, reuses
research_triage ordering, resolves each selected report from its canonical private
PDF, then invokes W1/W2. Output is metadata-only; source text and RIO quote text
are never printed.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.research_intelligence.store import ResearchIntelligenceStoreError
from engine.research_intelligence.vault_head import (
    DEFAULT_HEAD_SIZE,
    MAX_HEAD_SIZE,
    deep_read_candidate,
    rank_vault_head,
)
from engine.research_vault import catalog as catalog_mod
from engine.research_vault.r2_store import StrictConditionalWriteStore, build_store


def _emit(value: dict[str, Any], *, stream=sys.stdout) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
        file=stream,
        flush=True,
    )


def _parse_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    return date.fromisoformat(value)


def _load_press_config(path: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError("press config must be an object")
    return value


def _require_store(local_dir: str | None) -> StrictConditionalWriteStore:
    store = build_store(local_dir=local_dir)
    if not isinstance(store, StrictConditionalWriteStore):
        raise ResearchIntelligenceStoreError(
            "store_unavailable",
            "Research Vault strict conditional store is not configured",
        )
    store.validate_strict_conditional_write_capability()
    return store


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deep-read and persist the deterministic head of Research Vault"
    )
    parser.add_argument("--model", required=True, help="requested model id routed by llm_auth")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_HEAD_SIZE,
        help=f"deep-read head size, 1-{MAX_HEAD_SIZE}",
    )
    parser.add_argument("--as-of", help="ranking date YYYY-MM-DD; defaults to UTC today")
    parser.add_argument("--config", default=str(_ROOT / "config" / "press.yml"))
    parser.add_argument("--local", metavar="DIR", help="local Research Vault store")
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-run the model even when the exact source/model/prompt artifact is current",
    )
    parser.add_argument(
        "--selection-only",
        action="store_true",
        help="print the ranked deep-read head without PDF reads, model calls, or writes",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        now = datetime.now(tz=timezone.utc)
        as_of = _parse_date(args.as_of, now.date())
        store = _require_store(args.local)
        catalog = catalog_mod.read_strict(store, now=now)
        cfg = _load_press_config(Path(args.config).expanduser())
        head, triage = rank_vault_head(
            catalog.get("items") or [],
            as_of=as_of,
            root=_ROOT,
            cfg=cfg,
            limit=args.limit,
        )
        if not head:
            _emit(
                {
                    "state": "no_candidates",
                    "as_of": as_of.isoformat(),
                    "triage_reconciled": triage.get("reconciled"),
                }
            )
            return 3

        if args.selection_only:
            for candidate in head:
                item = candidate["item"]
                row = candidate["triage"]
                _emit(
                    {
                        "state": "selected",
                        "report_id": item.get("id"),
                        "rank": row.get("rank"),
                        "w_score": row.get("w_score"),
                        "institution": item.get("institution"),
                        "title": item.get("title"),
                    }
                )
            _emit(
                {
                    "state": "selection_complete",
                    "selected": len(head),
                    "as_of": as_of.isoformat(),
                    "triage_reconciled": triage.get("reconciled"),
                }
            )
            return 0

        failures = 0
        current = 0
        persisted = 0
        for candidate in head:
            result = deep_read_candidate(
                candidate,
                store=store,
                model_id=args.model,
                force=args.force,
            )
            _emit(result, stream=sys.stderr if result["state"] == "effect_unknown" else sys.stdout)
            if result["state"] == "effect_unknown":
                _emit(
                    {
                        "state": "aborted_effect_unknown",
                        "report_id": result["report_id"],
                        "note": "dependent writes stopped; reconcile this exact W2 carrier before retry",
                    },
                    stream=sys.stderr,
                )
                return 4
            if result["state"] == "persisted":
                persisted += 1
            elif result["state"] == "already_current":
                current += 1
            else:
                failures += 1

        _emit(
            {
                "state": "complete" if failures == 0 else "partial",
                "as_of": as_of.isoformat(),
                "selected": len(head),
                "persisted": persisted,
                "already_current": current,
                "failures": failures,
                "triage_reconciled": triage.get("reconciled"),
            },
            stream=sys.stdout if failures == 0 else sys.stderr,
        )
        return 0 if failures == 0 else 2
    except (OSError, TypeError, ValueError, ResearchIntelligenceStoreError) as exc:
        _emit(
            {
                "state": "error",
                "code": getattr(exc, "code", type(exc).__name__),
            },
            stream=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
