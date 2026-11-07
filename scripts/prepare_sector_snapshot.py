"""Prepare one Sector snapshot in a bounded child; publish nothing.

The snapshot lane owns the private temporary directory and final publication.
This module reads the exact native chain, captures local/holdings inputs and
runs the five existing document owners. The ephemeral handoff is not a selected
generation, cache, scheduler, ledger or publication receipt.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sys

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

PREPARED_SCHEMA = "sector_snapshot_prepared.v1"
PREPARED_NAME = "prepared.json"
MAX_PREPARED_METADATA_BYTES = 8 * 1024 * 1024


def _encode_deferred_effects(effects):
    """Preserve the owner's dated data without a pickle or a replay channel."""
    from copy import deepcopy
    import pandas as pd
    rows = deepcopy(list(effects))
    for row in rows:
        value = row.get("as_of")
        if isinstance(value, pd.Timestamp):
            if pd.isna(value):
                raise ValueError("invalid_deferred_effect_clock")
            row["as_of"] = {"timestamp": value.isoformat()}
        elif isinstance(value, datetime):
            row["as_of"] = {"datetime": value.isoformat()}
    return rows


def _decode_deferred_effects(rows):
    from copy import deepcopy
    import pandas as pd
    result = deepcopy(rows)
    for row in result:
        value = row.get("as_of")
        if type(value) is dict:
            if set(value) == {"timestamp"} and type(value["timestamp"]) is str:
                row["as_of"] = pd.Timestamp(value["timestamp"])
                if pd.isna(row["as_of"]):
                    raise ValueError("invalid_deferred_effect_clock")
            elif set(value) == {"datetime"} and type(value["datetime"]) is str:
                row["as_of"] = datetime.fromisoformat(value["datetime"])
            else:
                raise ValueError("invalid_deferred_effect_clock")
    return tuple(result)


def prepare_snapshot(*, repository_root, theme_root, generations_root,
                     generation_id, source_revision, clock):
    from collectors.sector_holdings import SectorHoldingsAdapter
    from engine.sector_basket_documents import compose_sector_documents
    from engine import sector_cycles
    from lib.market_session import market_local_date
    from lib import sector_input_capture as capture
    from lib.yahoo_generation_contract import _instant

    if (not callable(clock) or not re.fullmatch(r"[0-9a-f]{40}", source_revision)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", generation_id)):
        raise ValueError("explicit_sector_attempt_identity_required")
    evaluated = _instant(clock())
    evaluation_date = market_local_date("US", now=evaluated)
    prices = capture.read_sector_price_captures(
        generations_root=generations_root, now=_instant(clock()))
    member = capture.read_sector_member_ohlcv_capture(
        prices=prices, generations_root=generations_root, now=_instant(clock()))
    member_captured_at = _instant(clock())
    previous = capture.read_previous_sector_capture(
        generations_root=generations_root, allow_bootstrap=True, clock=clock)
    local = capture.read_sector_local_captures(
        repository_root=repository_root, theme_root=theme_root, prices=prices,
        evaluation_date=evaluation_date, clock=clock)
    holdings = SectorHoldingsAdapter.capture_from_inputs(
        sponsors=local.auxiliary.document("config")["sponsors"],
        evaluated_at=_instant(clock()), clock=clock)
    assembled = capture.assemble_sector_inputs(
        prices=prices, member_ohlcv=member, member_captured_at=member_captured_at,
        previous=previous, **local.assembly_arguments(), **holdings.assembly_arguments(),
        evaluation_date=evaluation_date, built_at=_instant(clock()),
        input_version="sector-inputs-v1", source_qualification="accepted",
        live_hazard_parity=sector_cycles._resolve_live_hazard_parity())
    composition = compose_sector_documents(**assembled.composition_arguments())
    metadata = {
        "schema": PREPARED_SCHEMA, "generation_id": generation_id,
        "source_revision": source_revision,
        "expected_current_content_id": assembled.expected_current_content_id,
        "input_identity": assembled.input_identity,
        "composition_evidence": composition.evidence,
        "deferred_effects": _encode_deferred_effects(composition.deferred_effects),
    }
    return composition, metadata


def write_prepared(stage, composition, metadata):
    from lib.sector_generation_contract import SECTOR_GENERATION_MEMBERS
    from scripts import vps_live_orchestrator as owner

    stage = Path(stage)
    if (not stage.is_absolute() or stage.is_symlink() or not stage.is_dir()
            or any(stage.iterdir())):
        raise ValueError("empty_private_sector_stage_required")
    if (stage.stat().st_mode & 0o077
            or any(parent.is_symlink() for parent in stage.parents)):
        raise ValueError("private_sector_stage_required")
    if set(composition.member_bytes) != set(SECTOR_GENERATION_MEMBERS):
        raise ValueError("complete_sector_candidate_required")
    for name in SECTOR_GENERATION_MEMBERS:
        target = stage / name
        owner._private_dir(target.parent)
        owner._write_private_bytes(target, composition.member_bytes[name])
    raw = owner._canonical_json(metadata)
    if len(raw) > MAX_PREPARED_METADATA_BYTES:
        raise ValueError("prepared_sector_metadata_bound")
    # Last file is written only after every calculation member is complete.
    owner._write_private_bytes(stage / PREPARED_NAME, raw)


def read_prepared(stage, *, generation_id, source_revision):
    """Read one complete child handoff; the incumbent publisher still admits it."""
    from engine.sector_basket_documents import SectorDocumentComposition
    from lib.sector_generation_contract import SECTOR_GENERATION_MEMBERS, _decode_member
    from scripts import vps_live_orchestrator as owner

    stage = Path(stage)
    if (not stage.is_absolute() or stage.is_symlink() or not stage.is_dir()
            or stage.stat().st_mode & 0o077
            or any(parent.is_symlink() for parent in stage.parents)):
        raise ValueError("private_sector_stage_required")
    expected = set(SECTOR_GENERATION_MEMBERS) | {PREPARED_NAME}
    files, directories, errors = owner._tree_members(stage)
    if errors or files != expected or directories != owner._expected_directories(tuple(expected)):
        raise ValueError("incomplete_or_unsafe_sector_candidate")
    raw_metadata = owner._read_source_bytes(stage / PREPARED_NAME,
        limit=MAX_PREPARED_METADATA_BYTES, require_stable=True)
    metadata = _decode_member(raw_metadata)
    if (type(metadata) is not dict or set(metadata) != {
            "schema", "generation_id", "source_revision", "expected_current_content_id",
            "input_identity", "composition_evidence", "deferred_effects"}
            or metadata["schema"] != PREPARED_SCHEMA
            or metadata["generation_id"] != generation_id
            or metadata["source_revision"] != source_revision):
        raise ValueError("sector_candidate_identity_changed")
    identity = metadata["input_identity"]
    try:
        previous = identity["sector_capture"]["previous"]
        fence = metadata["expected_current_content_id"]
        if (previous["content_id"] != fence
                or previous["outcome"] != ("observed_absent" if fence is None else "selected")
                or (fence is not None and not re.fullmatch(r"[0-9a-f]{64}", fence))):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ValueError("sector_candidate_previous_fence_changed") from None
    members = {name: owner._read_source_bytes(stage / name,
        limit=owner.MAX_GENERATION_ARTIFACT_BYTES, require_stable=True)
        for name in SECTOR_GENERATION_MEMBERS}
    if sum(map(len, members.values())) > owner.MAX_GENERATION_BYTES:
        raise ValueError("sector_candidate_bundle_bound")
    evidence = metadata["composition_evidence"]
    if (type(evidence) is not dict
            or evidence.get("member_sha256") != {
                name: hashlib.sha256(raw).hexdigest() for name, raw in members.items()}
            or evidence.get("member_bytes") != {name: len(raw) for name, raw in members.items()}):
        raise ValueError("sector_candidate_bytes_changed")
    deferred = metadata["deferred_effects"]
    if (type(deferred) is not list or any(type(item) is not dict for item in deferred)
            or evidence.get("deferred_effect_count") != len(deferred)):
        raise ValueError("sector_candidate_deferred_data_changed")
    # Deferred data crosses intact; the sole publisher never executes it.
    composition = SectorDocumentComposition(members, _decode_deferred_effects(deferred), evidence)
    return composition, metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--theme-root", type=Path, required=True)
    parser.add_argument("--generations-root", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--now", default=None, help="Explicit test/replay observation clock")
    args = parser.parse_args(argv)
    fixed = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else None
    if fixed is not None and (fixed.tzinfo is None or fixed.utcoffset() is None):
        parser.error("--now must include a timezone")
    clock = (lambda: fixed) if fixed is not None else (lambda: datetime.now(timezone.utc))
    composition, metadata = prepare_snapshot(
        repository_root=args.repository_root, theme_root=args.theme_root,
        generations_root=args.generations_root, generation_id=args.generation_id,
        source_revision=args.source_revision, clock=clock)
    write_prepared(args.stage, composition, metadata)
    print("sector_snapshot_prepared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
