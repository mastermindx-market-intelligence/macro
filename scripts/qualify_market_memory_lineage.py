#!/usr/bin/env python3
"""Verify-only offline qualification; never publish a certificate or proof HEAD.

Invocation requires the existing local operator's owner-root filesystem access,
an exact expected HEAD digest and a declared operation/budget. This does not
authenticate an external user or grant production invocation/release authority.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.neuralweb import market_memory_lineage as lineage
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_trusted as trusted


class _LocalFilesystemOperator:
    """Existing OS filesystem authority; never a web-user policy substitute."""
    def __init__(self, root):
        self.root = root
        self.policy_id = f"local_filesystem_operator_uid:{os.geteuid()}"

    def check(self, action, resource):
        if action != "qualify_market_memory_lineage" or not os.access(self.root, os.R_OK | os.X_OK):
            raise PermissionError("operator lacks owner-root read access")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--profile", required=True, choices=["pit", "trusted"])
    parser.add_argument("--expected-head-sha256", required=True)
    parser.add_argument("--operation-ref", required=True)
    parser.add_argument("--total-byte-limit", required=True, type=int)
    parser.add_argument("--batch-byte-limit", required=True, type=int)
    parser.add_argument("--cpu-seconds", required=True, type=float)
    parser.add_argument("--wall-seconds", required=True, type=float)
    args = parser.parse_args(argv)
    policy = _LocalFilesystemOperator(args.root)
    try:
        # Check OS authorization before reader construction resolves any root.
        policy.check("qualify_market_memory_lineage", {})
        reader = (pit.FileAsKnownAtReader if args.profile == "pit" else trusted.TrustedFileAsKnownAtReader)(args.root)
        result = reader.qualify_published_lineage(policy=policy, operation_ref=args.operation_ref,
            expected_head_body_sha256=args.expected_head_sha256,
            budget=lineage.OfflineQualificationBudget(total_bytes=args.total_byte_limit,
                batch_bytes=args.batch_byte_limit, cpu_seconds=args.cpu_seconds, wall_seconds=args.wall_seconds))
        certificate = lineage.build_lineage_certificate(result)
    except (pit.MarketMemoryPITError, OSError) as exc:
        print(json.dumps({"complete": False, "operation_ref": args.operation_ref,
                          "error_type": type(exc).__name__, "published": False}))
        return 2
    print(json.dumps({"complete": True, "published": False, "certificate": certificate}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
