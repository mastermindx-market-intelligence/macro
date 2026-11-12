#!/usr/bin/env python3
"""Print a secret-free Grok Build SuperGrok weekly usage observation."""
from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.provider_subscription_usage import SubscriptionUsageError
from engine.provider_subscription_usage_grok import observe_grok_build_usage


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grok-binary", default="grok")
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    args = parser.parse_args(argv)
    try:
        observation = observe_grok_build_usage(
            grok_binary=args.grok_binary,
            timeout_seconds=args.timeout_seconds,
        )
    except SubscriptionUsageError as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "provider": "xai",
                    "product": "supergrok",
                    "capacity_known": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(dataclasses.asdict(observation), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
