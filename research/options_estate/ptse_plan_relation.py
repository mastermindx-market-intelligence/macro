"""Pure PTSE relation from an incumbent Prophet plan to canonical B1 identity.

Consumes one immutable prophet.origination_receipt/v1 plus one validated B1
snapshot. It does not migrate prophet.trade_plan/v1, infer a portfolio position,
read ticker equality as identity, create a lifecycle, or grant action authority.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from research.options_estate.ptse_candidate_relation import (
    CandidateEpisodeRelation,
    PTSECandidateRelationError,
    resolve_candidate_episode_relation,
)

_RECEIPT_SCHEMA = "prophet.origination_receipt/v1"
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class PTSEPlanRelationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PlanEpisodeRelation:
    relation_id: str
    plan_id: str
    plan_asset: str
    plan_sha256: str
    origination_receipt_id: str
    origination_receipt_sha256: str
    source_board_sha256: str
    board_row_sha256: str
    candidate_source_event_id: str
    candidate_generation_id: str
    episode_id: str
    security_id: str
    company_id: str
    identity_epoch: str


def _fail(code: str) -> None:
    raise PTSEPlanRelationError(code)


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        _fail(code)
    if any(ord(ch) < 32 for ch in value):
        _fail(code)
    return value


def _digest(value: object, code: str) -> str:
    text = _text(value, code)
    if _HASH.fullmatch(text) is None:
        _fail(code)
    return text


def _raw_receipt(raw: bytes | str) -> tuple[dict[str, Any], str]:
    if isinstance(raw, str):
        wire = raw.encode("utf-8")
    elif isinstance(raw, bytes):
        wire = raw
    else:
        _fail("ORIGINATION_RECEIPT_BYTES_REQUIRED")
    try:
        text = wire.decode("utf-8")
        payload = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("ORIGINATION_RECEIPT_INVALID")
    if not isinstance(payload, dict):
        _fail("ORIGINATION_RECEIPT_INVALID")
    return payload, hashlib.sha256(wire).hexdigest()


def _canonical_row_sha256(row: Mapping[str, Any]) -> str:
    try:
        wire = json.dumps(
            dict(row),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        _fail("ORIGINATION_BOARD_ROW_INVALID")
    return hashlib.sha256(wire).hexdigest()


def _definition(row: Mapping[str, Any]) -> str:
    prophet = row.get("prophet")
    if not isinstance(prophet, Mapping):
        _fail("ORIGINATION_BOARD_DEFINITION_UNAVAILABLE")
    version = prophet.get("version")
    fusion = prophet.get("fusion")
    fusion_definition = (
        fusion.get("definition") if isinstance(fusion, Mapping) else None
    )
    if version is not None and fusion_definition is not None and version != fusion_definition:
        _fail("ORIGINATION_BOARD_DEFINITION_CONFLICT")
    return _text(
        version if version is not None else fusion_definition,
        "ORIGINATION_BOARD_DEFINITION_UNAVAILABLE",
    )


def resolve_plan_episode_relation(
    *,
    plan_id: str,
    origination_receipt: bytes | str,
    b1_snapshot: object,
    expected_episode_id: str | None = None,
) -> PlanEpisodeRelation:
    """Resolve one exact plan through its frozen admitted row into B1."""

    plan_id = _text(plan_id, "PLAN_ID_REQUIRED")
    receipt, receipt_sha = _raw_receipt(origination_receipt)
    if receipt.get("schema") != _RECEIPT_SCHEMA:
        _fail("ORIGINATION_RECEIPT_SCHEMA_INVALID")
    receipt_id = _text(
        receipt.get("receipt_id"),
        "ORIGINATION_RECEIPT_ID_REQUIRED",
    )
    source = receipt.get("source")
    if not isinstance(source, Mapping):
        _fail("ORIGINATION_SOURCE_INVALID")
    source_board_sha = _digest(
        source.get("sha256"),
        "ORIGINATION_SOURCE_DIGEST_INVALID",
    )
    board_asof = _text(
        source.get("board_asof"),
        "ORIGINATION_BOARD_ASOF_REQUIRED",
    )
    if _DATE.fullmatch(board_asof) is None:
        _fail("ORIGINATION_BOARD_ASOF_REQUIRED")

    ids = receipt.get("originated_plan_ids")
    origins = receipt.get("originations")
    if (
        not isinstance(ids, list)
        or not all(isinstance(item, str) and item for item in ids)
        or not isinstance(origins, list)
    ):
        _fail("ORIGINATION_RECEIPT_SHAPE_INVALID")
    if plan_id not in ids:
        _fail("PLAN_ORIGINATION_RECEIPT_UNAVAILABLE")

    matched = [
        raw for raw in origins
        if isinstance(raw, Mapping) and raw.get("plan_id") == plan_id
    ]
    if len(matched) != 1:
        _fail(
            "PLAN_ORIGINATION_RELATION_AMBIGUOUS"
            if matched
            else "PLAN_ORIGINATION_RECEIPT_UNAVAILABLE"
        )
    origin = matched[0]
    asset = _text(origin.get("asset"), "ORIGINATION_ASSET_REQUIRED").upper()
    plan_sha = _digest(
        origin.get("plan_sha256"),
        "ORIGINATION_PLAN_DIGEST_INVALID",
    )
    row_sha = _digest(
        origin.get("board_row_sha256"),
        "ORIGINATION_BOARD_ROW_DIGEST_INVALID",
    )
    row = origin.get("board_row")
    if not isinstance(row, Mapping):
        _fail("ORIGINATION_BOARD_ROW_INVALID")
    if _canonical_row_sha256(row) != row_sha:
        _fail("ORIGINATION_BOARD_ROW_DIGEST_MISMATCH")
    ticker = _text(
        row.get("ticker"),
        "ORIGINATION_BOARD_TICKER_REQUIRED",
    ).upper()
    if ticker != asset:
        _fail("ORIGINATION_ASSET_TICKER_MISMATCH")
    definition = _definition(row)

    candidate_row = {
        "stamp_date": board_asof,
        "ticker": asset,
        "board_definition": definition,
    }
    try:
        b1: CandidateEpisodeRelation = resolve_candidate_episode_relation(
            candidate_row,
            b1_snapshot,
            expected_episode_id=expected_episode_id,
        )
    except PTSECandidateRelationError as exc:
        raise PTSEPlanRelationError(exc.code) from exc

    semantic = {
        "plan_id": plan_id,
        "plan_asset": asset,
        "plan_sha256": plan_sha,
        "origination_receipt_id": receipt_id,
        "origination_receipt_sha256": receipt_sha,
        "source_board_sha256": source_board_sha,
        "board_row_sha256": row_sha,
        "candidate_source_event_id": b1.source_event_id,
        "candidate_generation_id": b1.candidate_generation_id,
        "episode_id": b1.episode_id,
        "security_id": b1.security_id,
        "company_id": b1.company_id,
        "identity_epoch": b1.identity_epoch,
    }
    relation_id = "ptse-plan-rel:" + hashlib.sha256(
        json.dumps(
            semantic,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return PlanEpisodeRelation(relation_id=relation_id, **semantic)


__all__ = [
    "PTSEPlanRelationError",
    "PlanEpisodeRelation",
    "resolve_plan_episode_relation",
]
