"""Specialist pack result contract: envelope + per-pack catalogues.

Pure validator. No pack evaluation, mapping, or source I/O beyond reading the
JSON contract files under contracts/. Third-party imports are limited to
jsonschema (yaml is permitted but unused).
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.validators import RefResolver


PACK_IDS = (
    "PK01",
    "PK02",
    "PK03",
    "PK04",
    "PK05",
    "PK06",
    "PK07",
    "PK08",
    "PK09",
    "PK10",
    "PK11",
    "PK12",
)

_CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"
_ENVELOPE_PATH = _CONTRACTS / "specialist_pack_result.v1.schema.json"
_PACK_DIR = _CONTRACTS / "specialist_packs"
_PACKET_SCHEMA_PATH = _CONTRACTS / "financial_intelligence_packet.schema.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} is not a JSON object")
    return payload


def load_envelope_schema() -> dict[str, Any]:
    return _load_json(_ENVELOPE_PATH)


def load_pack_schema(pack_id: str) -> dict[str, Any]:
    if pack_id not in PACK_IDS:
        raise KeyError(f"unknown pack_id: {pack_id}")
    return _load_json(_PACK_DIR / f"pack.{pack_id.lower()}.v1.schema.json")


def pack_schema_digest(pack_id: str) -> str:
    schema = load_pack_schema(pack_id)
    payload = json.dumps(
        schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return sha256(payload).hexdigest()


def _error_path(error: Any) -> str:
    parts = list(error.absolute_path)
    return ".".join(str(part) for part in parts) if parts else "<root>"


def _envelope_validator(schema: Mapping[str, Any]) -> Draft202012Validator:
    packet = _load_json(_PACKET_SCHEMA_PATH)
    store = {
        schema["$id"]: schema,
        packet["$id"]: packet,
    }
    resolver = RefResolver(base_uri=str(schema["$id"]), referrer=schema, store=store)
    return Draft202012Validator(
        schema, resolver=resolver, format_checker=FormatChecker()
    )


def validate_pack_result(obj: Any) -> list[str]:
    """Return Draft 2020-12 errors as ``path: message`` strings; empty means valid.

    Also requires ``pack_schema_digest`` to equal ``pack_schema_digest(pack_id)``
    and ``pack_schema_id`` to equal the pack file's ``pack_schema_id``.
    """
    schema = load_envelope_schema()
    validator = _envelope_validator(schema)
    errors = [
        f"{_error_path(item)}: {item.message}"
        for item in sorted(validator.iter_errors(obj), key=lambda item: list(item.absolute_path))
    ]
    if not isinstance(obj, Mapping):
        return errors or ["<root>: instance is not an object"]
    pack_id = obj.get("pack_id")
    if pack_id in PACK_IDS:
        pack_schema = load_pack_schema(pack_id)
        expected_id = pack_schema.get("pack_schema_id")
        expected_digest = pack_schema_digest(pack_id)
        given_id = obj.get("pack_schema_id")
        given_digest = obj.get("pack_schema_digest")
        if given_id != expected_id:
            errors.append(
                f"pack_schema_id: {given_id!r} does not match pack file {expected_id!r}"
            )
        if given_digest != expected_digest:
            errors.append(
                "pack_schema_digest: value does not equal the recomputed pack schema digest"
            )
    return errors
