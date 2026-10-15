#!/usr/bin/env python3
"""One-shot private administrator inspector for retained SPY price-source coverage.

This is the installed administrator CLI composed with the current
metadata-purpose policy.  It is intentionally not an HTTP API, not a user-facing
permission grant, not an E0 study owner, and not a security boundary against a
malicious administrator.  Its trust origin is the approved source deployed by
the incumbent release path plus the existing authenticated OS administrator
invocation; matching euid/path/hash values are consistency evidence only.

Production ``main`` runs on Linux as euid 0 from the exact installed script
under ``/opt/macro`` against the fixed private store
``/var/lib/macro-market-memory/state/technicals-v1``.  There are no caller
root/path/module/allow flags and no environment-based grants; the four exact
immutable IDs are the only input.  The command pins one exact published
generation (never current-HEAD discovery, never a latest fallback), reads and
discloses the retained source-bar metadata for exactly one source observation
under one outer 64 MiB owner-read budget, and prints one canonical JSON line
not larger than 1 MiB.  Price values, the feature body, network transport,
runtime writes, evaluation, and operational-study admission are all forbidden
and reported as absent flags.  Failures are typed, contain no raw exception
text, private body, or path, and exit nonzero.

No access ledger, reservation, study installation, scheduler, service, or
registry is created: this reads authorized preparatory metadata only.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import resource
import signal
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.neuralweb import market_memory_pit as pit  # noqa: E402
from engine.neuralweb import (  # noqa: E402
    market_memory_price_metadata_use as use,
)
from engine.neuralweb import market_memory_technical_store as store  # noqa: E402

INSPECTION_SCHEMA = "market_memory.price_metadata_coverage_inspection.v1"
FAILURE_SCHEMA = "market_memory.price_metadata_coverage_inspection_failure.v1"
INSTALLED_SCRIPT_PATH = Path(
    "/opt/macro/scripts/inspect_market_memory_price_coverage.py"
)
CANONICAL_STORE_ROOT = Path("/var/lib/macro-market-memory/state/technicals-v1")
_OWNER_READ_BUDGET_BYTES = 64 * 1024 * 1024
_PIN_CAPTURE_BUDGET = 256
_OUTPUT_BYTE_LIMIT = 1024 * 1024
_CPU_LIMIT_SECONDS = 30
_CPU_LIMIT_HARD_SECONDS = 32
_WALL_LIMIT_SECONDS = 60

_FEATURE_REF_FIELDS = ("snapshot_id", "sha256", "bytes")


class _ProductionEnvironmentError(Exception):
    """The invocation is not the exact installed administrator production main."""


class _WallClockExceeded(Exception):
    """The one-shot inspection exceeded its wall-clock bound."""


class _UsageError(Exception):
    """The administrator supplied a malformed command line."""


def _failure_payload(reason: str) -> bytes:
    payload = {
        "schema": FAILURE_SCHEMA,
        "failure": reason,
        "policy_id": use.POLICY_ID,
    }
    return json.dumps(
        payload, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8") + b"\n"


def _verify_production_environment() -> None:
    if sys.platform != "linux":
        raise _ProductionEnvironmentError("non-Linux production main")
    if os.geteuid() != 0:
        raise _ProductionEnvironmentError("production main requires euid 0")
    script = Path(__file__).resolve()
    if script != INSTALLED_SCRIPT_PATH:
        raise _ProductionEnvironmentError("script is not the exact installed path")
    if not sys.argv:
        raise _ProductionEnvironmentError("missing invocation context")
    if Path(os.path.realpath(sys.argv[0])) != INSTALLED_SCRIPT_PATH:
        raise _ProductionEnvironmentError("invocation path is not the installed script")


def _apply_production_bounds() -> None:
    try:
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (_CPU_LIMIT_SECONDS, _CPU_LIMIT_HARD_SECONDS),
        )
    except (OSError, ValueError) as exc:
        raise _ProductionEnvironmentError("CPU bound cannot be applied") from exc
    signal.signal(signal.SIGALRM, _raise_wall_clock_exceeded)
    signal.alarm(_WALL_LIMIT_SECONDS)


def _raise_wall_clock_exceeded(signum: int, frame: object) -> None:
    del signum, frame
    raise _WallClockExceeded


def _parse_invocation(argv: list[str]) -> argparse.Namespace:
    class PrivateArgumentParser(argparse.ArgumentParser):
        def error(self, message):
            # Do not echo caller text or private paths to stderr.
            raise _UsageError("malformed administrator invocation")

    parser = PrivateArgumentParser(
        add_help=False,
        prog=INSTALLED_SCRIPT_PATH.name,
        allow_abbrev=False,
        description=(
            "Disclose retained SPY price-source coverage metadata for one exact "
            "pinned generation and source observation (administrator only)."
        ),
    )
    parser.add_argument("--store-id", required=True)
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--generation-sha256", required=True)
    parser.add_argument("--source-observation-id", required=True)
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        raise _UsageError("malformed administrator invocation") from exc


def _whitelisted_output(
    policy: "use.RetainedSourceBarMetadataUsePolicy",
    value: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": INSPECTION_SCHEMA,
        "policy_id": policy.policy_id,
        "profile": value["profile"],
        "store_id": value["store_id"],
        "generation_id": value["generation_id"],
        "generation_sha256": value["generation_sha256"],
        "source_observation_id": value["source_observation_id"],
        "capture_id": value["capture_id"],
        "capture_receipt_sha256": value["capture_receipt_sha256"],
        "revision_id": value["revision_id"],
        "source_commit": value["source_commit"],
        "session": value["source_observation"]["session"],
        "bar_sessions": list(value["bar_sessions"]),
        "first_observed_at": value["first_observed_at"],
        "available_at": value["available_at"],
        "freshness": copy.deepcopy(value["freshness"]),
        "subject": copy.deepcopy(value["subject"]),
        "calendar": copy.deepcopy(value["calendar"]),
        "price_basis": copy.deepcopy(value["price_basis"]),
        "transform_version": value["transform_version"],
        "source_observation_sha256": value["source_observation_sha256"],
        "source_bodies": {
            role: {"sha256": ref["sha256"], "bytes": ref["bytes"]}
            for role, ref in value["source_bodies"].items()
        },
        "feature_ref": {
            key: value["feature_ref"][key] for key in _FEATURE_REF_FIELDS
        },
        "feature_body_read": False,
        "source_closure": policy.qualified_closure,
        "flags": {
            "price_values_read": False,
            "feature_body_read": False,
            "writes": False,
            "evaluation": False,
            "operational_study_admission": False,
        },
    }


def _serialize(output: dict[str, Any]) -> bytes:
    line = json.dumps(
        output, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if len(line) + 1 > _OUTPUT_BYTE_LIMIT:
        raise OverflowError("inspection output exceeds its byte bound")
    return line + b"\n"


def _classify_store_failure(exc: Exception) -> str:
    seen: BaseException | None = exc
    while seen is not None:
        if isinstance(seen, pit.OwnerReadBudgetError):
            return "read_budget_exhausted"
        seen = seen.__cause__
    return "store_unavailable"


def _run_inspection(
    *,
    repository_root: str | Path,
    store_root: str | Path,
    argv: list[str],
) -> tuple[int, bytes]:
    """Injectable synthetic seam: identical composition without the production gate.

    Production ``main`` calls this with the fixed installed repository root and
    the canonical store root only.  Synthetic tests call it with explicitly
    constructed fixtures; no CLI flag, argument, or environment variable can
    select an alternate root, module, or path.
    """
    try:
        parsed = _parse_invocation(argv)
        policy = use.RetainedSourceBarMetadataUsePolicy(
            repository_root=repository_root,
            store_id=parsed.store_id,
            generation_id=parsed.generation_id,
            generation_sha256=parsed.generation_sha256,
            source_observation_id=parsed.source_observation_id,
        )
        resource = policy.resource
        # The current policy authorizes this exact identity before any private
        # pin or store IO occurs.
        policy.check("read_retained_source_bar_metadata", resource)
        with pit.bounded_owner_reads(maximum_bytes=_OWNER_READ_BUDGET_BYTES):
            pin = store.pin_technical_actual_output_generation(
                store_root,
                generation_id=parsed.generation_id,
                maximum_capture_count=_PIN_CAPTURE_BUDGET,
            )
            if (
                pin.store_id != parsed.store_id
                or pin.generation_id != parsed.generation_id
                or pin.generation_sha256 != parsed.generation_sha256
            ):
                raise store.MarketMemoryTechnicalStoreError(
                    "pinned generation differs from the requested exact identity"
                )
            capability = store.read_retained_source_bar_metadata(
                store_root,
                technical_pin=pin,
                source_observation_id=parsed.source_observation_id,
                policy=policy,
            )
            value = store.disclose_retained_source_bar_metadata(
                capability, policy=policy
            )
        output = _whitelisted_output(policy, value)
        payload = _serialize(output)
        # Recheck after serialization, immediately before returning to stdout.
        policy.check("disclose_retained_source_bar_metadata", resource)
        return 0, payload
    except _UsageError:
        return 2, _failure_payload("usage")
    except PermissionError:
        return 1, _failure_payload("policy_denied")
    except pit.OwnerReadBudgetError as exc:
        return 1, _failure_payload(_classify_store_failure(exc))
    except store.MarketMemoryTechnicalStoreError as exc:
        return 1, _failure_payload(_classify_store_failure(exc))
    except use.MarketMemoryPriceMetadataPolicyError:
        return 1, _failure_payload("policy_qualification_failed")
    except _WallClockExceeded:
        return 1, _failure_payload("wall_clock_limit_exceeded")
    except OverflowError:
        return 1, _failure_payload("output_limit_exceeded")
    except Exception:
        return 1, _failure_payload("inspection_failed")


def _emit(payload: bytes) -> None:
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def main(argv: list[str] | None = None) -> int:
    try:
        _verify_production_environment()
        _apply_production_bounds()
    except _ProductionEnvironmentError:
        _emit(_failure_payload("environment"))
        return 1
    code, payload = _run_inspection(
        repository_root=use.INSTALLED_REPOSITORY_ROOT,
        store_root=CANONICAL_STORE_ROOT,
        argv=sys.argv[1:] if argv is None else list(argv),
    )
    _emit(payload)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
