"""Nightly private Trade Memory runner.

Reads only the explicitly configured operator's closed episodes from Supabase,
builds point-in-time evidence, writes private LLM autopsies back to the same rows,
then rebuilds the private pattern-candidate view.  No personal trade content or
derived personal pattern is written to git or stdout.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.neuralweb import trade_memory  # noqa: E402
from engine.neuralweb.trade_memory_store import SupabaseTradeMemoryStore, build_store  # noqa: E402

log = logging.getLogger("run_trade_memory")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_prophet_pick_autopsies(root: str | Path | None = None) -> list[dict[str, Any]]:
    """Project canonical Prophet pick autopsies into the private pattern rebuild."""
    repo = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    base = repo / "data" / "standout_audit" / "pick_autopsies"
    out: list[dict[str, Any]] = []
    if not base.exists():
        return out
    for path in sorted(base.glob("*/*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            llm = doc.get("llm") if isinstance(doc.get("llm"), dict) else {}
            hypotheses = llm.get("signal_hypotheses")
            if not isinstance(hypotheses, list) or not hypotheses:
                continue
            attribution = (
                doc.get("attribution") if isinstance(doc.get("attribution"), dict) else {}
            )
            excess = attribution.get("excess_spy")
            if excess is None:
                excess = attribution.get("excess_21d")
            if excess is None:
                excess = attribution.get("excess_sector")
            try:
                numeric_excess = float(excess)
            except (TypeError, ValueError):
                continue
            outcome = (
                "win" if numeric_excess > 0
                else "loss" if numeric_excess < 0
                else "flat"
            )
            pick_id = str(doc.get("pick_id") or path.stem)
            out.append({
                "episode_ref": f"prophet:{pick_id}",
                "entry_date": doc.get("entry_date"),
                "outcome": outcome,
                "signal_hypotheses": hypotheses,
                "authority": "research_only",
                "direct_authority": False,
            })
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "trade_memory: one Prophet autopsy could not join pattern rebuild (%s)",
                type(exc).__name__,
            )
    return out


def _rebuild_patterns(store, root):
    pattern_n = 0
    rows = store.fetch_autopsied()
    autopsies: list[dict[str, Any]] = []
    for row in rows:
        item = row.get("autopsy")
        if not isinstance(item, dict):
            continue
        # Re-attach immutable episode facts needed by the deterministic
        # repetition/time-cluster gate.
        item = dict(item)
        item["episode_ref"] = str(row.get("id") or item.get("episode_ref") or "")
        item["entry_date"] = row.get("entry_date") or item.get("entry_date")
        item["outcome"] = row.get("outcome") or item.get("outcome")
        autopsies.append(item)
    # One private derived view, two canonical sources: owner rows above plus
    # Prophet's existing git-backed pick autopsies. Personal rows never move in
    # the other direction and no second episode store is created.
    autopsies.extend(_load_prophet_pick_autopsies(root))
    patterns = trade_memory.build_pattern_candidates(autopsies)
    if store.replace_patterns(patterns):
        pattern_n = len(patterns)

    return pattern_n


def run(
    store: SupabaseTradeMemoryStore | None,
    *,
    root: str | Path | None = None,
    cap: int = 8,
    model_caller: Callable[[str, str], Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Process owner rows; selected completion requires the original conditional receipt."""
    result = {"ok": True, "configured": bool(store is not None and store.available),
              "processed": 0, "completed": 0, "failed": 0, "patterns": 0, "held": 0}
    if not result["configured"]:
        return result
    from scripts.metabolism_journal import (
        FabricHeld, selected_factory, operation_record, fabric_digest,
    )
    from engine.neuralweb.trade_memory_store import fabric_claim_present, PrivateFabricInvocation
    repo = Path(root).absolute() if root is not None else _ROOT
    selection = ("MM_PROVIDER_APPLICATION_MODE" in os.environ,
                 os.environ.get("MM_PROVIDER_APPLICATION_MODE"),
                 os.environ.get("MM_PROVIDER_WORKLOAD_PROFILE"))
    try:
        # Read the incumbent originals before selection. Real rows include held
        # running claims; legacy injected test stores retain their old interface.
        pending = (store.fetch_fabric_candidates(limit=cap)
                   if isinstance(store, SupabaseTradeMemoryStore)
                   else store.fetch_pending(limit=cap))
        eligible = []
        for row in pending:
            if fabric_claim_present(row) or row.get("autopsy_state") == "running":
                result["processed"] += 1
                result["failed"] += 1
                result["held"] += 1
            else:
                eligible.append(row)
        factory, cfg = selected_factory(repo, "trade_memory", {"max_tokens": 7000})
        if (selection != ("MM_PROVIDER_APPLICATION_MODE" in os.environ,
                          os.environ.get("MM_PROVIDER_APPLICATION_MODE"),
                          os.environ.get("MM_PROVIDER_WORKLOAD_PROFILE"))
                or (factory is not None) != selection[0]):
            raise FabricHeld("trade_memory_selection_changed")
        if factory is not None and (dry_run or model_caller is not None
                or not isinstance(store, SupabaseTradeMemoryStore)):
            raise FabricHeld("trade_memory_durable_owner_required")
    except Exception:
        result.update(ok=False, held=max(1, result["held"]))
        return result
    for row in eligible:
        result["processed"] += 1
        episode_id = str(row.get("id") or "")
        context = None
        try:
            packet = trade_memory.build_evidence_packet(row, root=repo)
            packet["episode"]["id"] = episode_id
            if factory is not None:
                system, user = trade_memory.autopsy_messages(packet)
                record = operation_record(repo, "trade_memory", episode_id,
                    {"operator": store.operator_user_id, "episode": episode_id,
                     "facts": trade_memory.normalize_episode(row), "packet_digest": fabric_digest(packet)},
                    ["episode:"+episode_id], system, user, 7000, factory, cfg)
                context = PrivateFabricInvocation(store, row, packet, record, factory, cfg)
                autopsy, provider = trade_memory.invoke_autopsy(packet, _fabric_context=context)
                if autopsy is None:
                    result["failed"] += 1
                    result["held"] += 1
                    continue
                context.publication_intent(autopsy)
                context.complete(autopsy)
                result["completed"] += 1
                continue
            if selection != ("MM_PROVIDER_APPLICATION_MODE" in os.environ,
                             os.environ.get("MM_PROVIDER_APPLICATION_MODE"),
                             os.environ.get("MM_PROVIDER_WORKLOAD_PROFILE")):
                raise FabricHeld("trade_memory_selection_changed")
            autopsy, provider = trade_memory.invoke_autopsy(packet, model_caller=model_caller)
            if autopsy is None:
                result["failed"] += 1
                if not dry_run:
                    if not store.update_episode(episode_id, {"evidence_packet": packet, "autopsy_state": "retry",
                            "autopsy_model": provider, "autopsy_error": "no_structured_reply", "updated_at": _now()}):
                        result["held"] += 1
                continue
            if not dry_run:
                if not store.update_episode(episode_id, {"evidence_packet": packet, "autopsy": autopsy,
                    "autopsy_state": "complete", "autopsy_model": provider, "autopsied_at": _now(),
                        "autopsy_error": None, "updated_at": _now()}):
                    result["held"] += 1
                    result["failed"] += 1
                    continue
            result["completed"] += 1
        except Exception as exc:
            result["failed"] += 1
            if factory is not None or isinstance(exc, FabricHeld):
                result["held"] += 1
                # The original row and known observations remain with their owner.
                # An exception never changes a selected row back to retry.
                continue
            log.warning("trade_memory: one private episode failed (%s)", type(exc).__name__)
            if not dry_run:
                store.update_episode(episode_id, {"autopsy_state": "retry",
                    "autopsy_error": type(exc).__name__[:80], "updated_at": _now()})
    if not dry_run and not result["held"]:
        result["patterns"] = _rebuild_patterns(store, repo)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the private Prophet Trade Memory lane")
    parser.add_argument("--cap", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run(build_store(), cap=max(1, min(25, args.cap)), dry_run=args.dry_run)
    # Count-only output. Never print a ticker, date, note, price, packet, or autopsy.
    if not result["configured"]:
        print("trade_memory: private store not configured — clean no-op")
    else:
        print(
            "trade_memory: processed={processed} completed={completed} "
            "failed={failed} patterns={patterns}".format(**result)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
