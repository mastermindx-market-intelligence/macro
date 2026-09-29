"""Non-writing preflight for the existing shared daily options universe.

Example: python -B -m scripts.plan_options_coverage --as-of 2026-09-28 \
    --target-stocks 1000 --max-total-roots 1500 --priority MU --priority ARM

Selection is not acquisition, qualification, or production activation. This
command invokes no provider, collector, scheduler, or publication path.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Sequence
from pathlib import Path

# Pin this checkout before any repo import, including file-path invocation from
# another directory where PYTHONPATH may name an unrelated engine package.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.options_universe import (
    DEFAULT_ANCHORS,
    OptionsUniverseError,
    gex_symbols,
    plan_daily_expansion,
)
from lib import config


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="Completed US-equity session, YYYY-MM-DD")
    parser.add_argument("--target-stocks", required=True, type=int, help="Stock selection target, 1..1500")
    parser.add_argument("--max-total-roots", required=True, type=int,
                        help="Total ceiling including retained and priority roots, 1..2000")
    parser.add_argument("--priority", action="append", default=[], metavar="ROOT",
                        help="Priority input supplied by the existing candidate owner; repeatable")
    args = parser.parse_args(argv)
    try:
        document = config.load()
        cfg = copy.deepcopy(((document.get("polygon") or {}).get("gex") or {}))
        if not isinstance(cfg, dict):
            raise OptionsUniverseError("invalid_config", field="polygon.gex")
        # Recover exactly the legacy cohort. Never execute a configured expansion
        # as an accidental prerequisite of previewing another selection.
        cfg.pop("daily_expansion", None)
        legacy = gex_symbols(cfg)
        anchors = list(cfg.get("symbols") or DEFAULT_ANCHORS)
        result = plan_daily_expansion(
            {"target_stocks": args.target_stocks, "max_total_roots": args.max_total_roots,
             "priority_symbols": args.priority},
            legacy_symbols=legacy, anchor_symbols=anchors, as_of=args.as_of,
        )
        result["configuration_changed"] = False
        result["production_activation"] = "not_requested"
        exit_code = 0
    except OptionsUniverseError as exc:
        result = {"schema": "options_daily_universe_plan.v1", "status": "refused",
                  "reason": exc.code, "details": exc.details,
                  "collection_started": False, "configuration_changed": False}
        exit_code = 2
    except (OSError, TypeError, AttributeError, ValueError) as exc:
        # Never print provider credentials or arbitrary parser error contents.
        result = {"schema": "options_daily_universe_plan.v1", "status": "refused",
                  "reason": "configuration_unavailable", "error_type": type(exc).__name__,
                  "collection_started": False, "configuration_changed": False}
        exit_code = 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
