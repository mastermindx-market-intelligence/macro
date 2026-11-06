"""Bridge RATIFIED activity proposals to activity-history APPEND events (GMI M1 step 2).

This CLI is a bridge for two existing owners: it reads the probation activity
proposal ledger, checks the seat's curation receipt for each RATIFIED proposal,
qualifies graph-membership use against Chairman ruling REVISION files, and appends
exactly one validated APPEND event per granted proposal to the activity history
events file, with one bridge receipt row per written/HELD decision.

It writes ONLY its two output files (``data/theme_graph/probation/
activity_history_events.jsonl`` and ``.../activity_history_bridge_receipts.jsonl``
by default): never the proposal ledger, never a ruling, never a curation receipt.
It ratifies nothing, grants nothing and curates nothing: ``graph_membership_use``
comes only from a Chairman ruling revision file, found at the default glob
``research/theme_graph/*/*GRAPH_MEMBERSHIP_USE_RULING*.json``. Until such a file
exists a RATIFIED proposal is HELD with ``GRAPH_MEMBERSHIP_USE_NOT_GRANTED`` — no
event is written. Fixture grants (``ruling_id`` prefixed ``FIXTURE``) can never be
used here: the fixture door is open only to tests, never to this CLI.

Run:
  python3 scripts/bridge_activity_history.py --recorded-at 2026-10-21T23:00:00Z --dry-run
  python3 scripts/bridge_activity_history.py --recorded-at 2026-10-21T23:00:00Z \
      --use-ruling research/theme_graph/issuer_disclosures_20261011/C01_GRAPH_MEMBERSHIP_USE_RULING.json

Every refusal is typed and printed as one ``REFUSED: <code>: <detail>`` line with
exit 2 — never a traceback. A per-proposal REFUSED outcome prints the plan and
exits 3, writing nothing in that run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.theme_graph import probation  # noqa: E402
from engine.theme_graph import activity_history_bridge as bridge  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _default_ruling_paths() -> list[str]:
    """Sorted ruling revisions at the default glob under the repo root (absolute)."""
    return sorted(str(p) for p in ROOT.glob(bridge.DEFAULT_USE_RULING_GLOB))


def _cmd(args: argparse.Namespace) -> int:
    if probation._activity_zoned(args.recorded_at) is None:
        raise bridge.BridgeRefusal("RECORDED_AT_INVALID", repr(args.recorded_at))
    ledger = Path(args.ledger) if args.ledger else probation.ACTIVITY_PROPOSALS_PATH
    receipts_dir = (Path(args.receipts_dir) if args.receipts_dir
                    else ROOT / bridge.DEFAULT_RECEIPTS_DIR)
    events_out = Path(args.events_out) if args.events_out else ROOT / bridge.DEFAULT_EVENTS_PATH
    receipts_out = (Path(args.bridge_receipts_out) if args.bridge_receipts_out
                    else ROOT / bridge.DEFAULT_BRIDGE_RECEIPTS_PATH)
    ruling_paths = list(args.use_ruling) if args.use_ruling else _default_ruling_paths()
    ledger_rows = probation.read_activity_proposals(ledger)
    existing_events = bridge.read_events(events_out)
    plan = bridge.plan_bridge(
        ledger_rows, receipts_dir=receipts_dir, ruling_paths=ruling_paths,
        recorded_at=args.recorded_at, existing_events=existing_events,
        allow_fixture=False)
    refused = any(d["outcome"] == "REFUSED" for d in plan)
    if args.dry_run or refused:
        counts = bridge.plan_counts(
            plan, existing_events=existing_events,
            existing_receipts=bridge.read_bridge_receipts(receipts_out))
        print(json.dumps({"decisions": plan, "counts": counts}))
        return 3 if refused else 0
    counts = bridge.apply_plan(plan, events_path=events_out,
                               receipts_path=receipts_out, recorded_at=args.recorded_at)
    print(json.dumps({"decisions": plan, "counts": counts}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", default=None,
                        help=f"default: {probation.ACTIVITY_PROPOSALS_PATH}")
    parser.add_argument("--receipts-dir", default=None,
                        help=f"curation receipt directory (default: {bridge.DEFAULT_RECEIPTS_DIR})")
    parser.add_argument("--use-ruling", action="append", default=None, metavar="PATH",
                        help="Chairman ruling revision file; repeatable (default: sorted glob "
                             f"{bridge.DEFAULT_USE_RULING_GLOB})")
    parser.add_argument("--recorded-at", required=True, help="zoned ISO-8601 instant")
    parser.add_argument("--events-out", default=None,
                        help=f"default: {bridge.DEFAULT_EVENTS_PATH}")
    parser.add_argument("--bridge-receipts-out", default=None,
                        help=f"default: {bridge.DEFAULT_BRIDGE_RECEIPTS_PATH}")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and counts; write nothing")
    args = parser.parse_args(argv)
    try:
        return _cmd(args)
    except (bridge.BridgeRefusal, probation.ActivityProposalRefusal) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
