"""CLI for the Catalyst SEC source cycle writer (off-render, scheduled).

Runs as ``python -m scripts.run_catalyst_source_cycle``.  Prints exactly ONE
JSON line to stdout and returns the cycle exit code.  The SEC user agent is
never printed, logged or included in any exception text.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

_RESULT_FIELDS = (
    "outcome", "exit_code", "requests_used", "events", "issuers_ok",
    "issuers_incomplete", "issuers_failed", "issuers_not_checked",
    "snapshot_id", "reason",
)


def _resolve_user_agent(args: argparse.Namespace) -> str | None:
    """UA precedence: --user-agent, then env SEC_USER_AGENT; nothing else.

    The writer's contact is an explicit operator setting, never inherited
    from another collector's tracked config.  Returns None when neither is
    set (the cycle then refuses without ever naming or echoing a value).
    """
    if args.user_agent:
        return args.user_agent
    env_agent = os.environ.get("SEC_USER_AGENT")
    if env_agent:
        return env_agent
    return None


def _emit(result) -> int:
    print(json.dumps({field: getattr(result, field) for field in _RESULT_FIELDS}))
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_catalyst_source_cycle",
        description="Catalyst SEC source cycle writer (publishes the index snapshot)",
    )
    parser.add_argument("--local-store", metavar="DIR", default=None,
                        help="use a local filesystem store instead of production R2")
    parser.add_argument("--universe", metavar="PATH", default=str(REPO_ROOT / "config" / "catalyst_pilot_universe.json"),
                        help="pilot universe JSON path")
    parser.add_argument("--max-requests", type=int, default=150,
                        help="SEC GET budget for the cycle (1..150)")
    parser.add_argument("--user-agent", default=None,
                        help="SEC contact user agent (never printed)")
    args = parser.parse_args(argv)

    from engine.marketing.catalyst_source_cycle import run_cycle
    from engine.marketing.catalyst_source_store import (
        CatalystSourceUnavailable,
        open_local_store,
        open_production_store,
    )

    if args.local_store:
        store = open_local_store(args.local_store)
    else:
        try:
            store = open_production_store()
        except CatalystSourceUnavailable as exc:
            print(json.dumps({
                "outcome": "REFUSED", "exit_code": 2, "requests_used": 0,
                "events": [], "issuers_ok": 0, "issuers_incomplete": 0,
                "issuers_failed": 0, "issuers_not_checked": 0,
                "snapshot_id": None, "reason": str(exc),
            }))
            return 2

    try:
        universe = load_universe_or_refuse(args.universe)
    except ValueError:
        print(json.dumps({
            "outcome": "REFUSED", "exit_code": 2, "requests_used": 0,
            "events": [], "issuers_ok": 0, "issuers_incomplete": 0,
            "issuers_failed": 0, "issuers_not_checked": 0,
            "snapshot_id": None, "reason": "universe_invalid",
        }))
        return 2

    import engine.marketing.catalyst_source_cycle as cycle_module

    user_agent = _resolve_user_agent(args)
    if user_agent is None:
        print(json.dumps({
            "outcome": "REFUSED", "exit_code": 2, "requests_used": 0,
            "events": [], "issuers_ok": 0, "issuers_incomplete": 0,
            "issuers_failed": 0, "issuers_not_checked": 0,
            "snapshot_id": None, "reason": "user_agent_unresolved",
        }))
        return 2
    result = run_cycle(
        store=store,
        universe=universe,
        user_agent=user_agent,
        clock=cycle_module._utc_now,
        max_requests=args.max_requests,
    )
    return _emit(result)


def load_universe_or_refuse(path: str):
    from engine.marketing.catalyst_source_cycle import load_universe

    return load_universe(path)


if __name__ == "__main__":  # pragma: no cover - process entrypoint
    raise SystemExit(main())
