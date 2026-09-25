from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.sector_intelligence.contracts import (
    ContractValidationError,
    canonical_json_sha256,
    validate_contract,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/sector_intelligence/fixtures/sector_dossier_read_model.v1.valid.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def rehash(doc: dict) -> None:
    doc.pop("dossier_hash", None)
    doc["dossier_hash"] = canonical_json_sha256(doc)


def test_valid_sector_dossier_contract() -> None:
    validate_contract("sector_dossier_read_model.v1", load_fixture())


def test_dossier_hash_binds_canonical_payload() -> None:
    doc = load_fixture()
    expected = doc.pop("dossier_hash")
    assert canonical_json_sha256(doc) == expected


def test_dossier_rejects_authority_escalation() -> None:
    doc = load_fixture()
    doc["authority_caps"]["may_rank"] = True
    rehash(doc)
    with pytest.raises(ContractValidationError, match="authority"):
        validate_contract("sector_dossier_read_model.v1", doc)


def test_dossier_rejects_packet_binding_mismatch() -> None:
    doc = load_fixture()
    doc["governance"]["lobe_run"]["authority_manifest_ref"] = "authority:forged"
    rehash(doc)
    with pytest.raises(ContractValidationError, match="governance"):
        validate_contract("sector_dossier_read_model.v1", doc)


def test_dossier_rejects_unknown_conflict_class() -> None:
    doc = load_fixture()
    doc["conflicts"][0]["class"] = "MYSTERY_CONFLICT"
    rehash(doc)
    with pytest.raises(ContractValidationError):
        validate_contract("sector_dossier_read_model.v1", doc)


def test_dossier_preserves_null_concentration() -> None:
    doc = load_fixture()
    doc["concentration"].update(state="unavailable", value=None, n_members=3)
    rehash(doc)
    validate_contract("sector_dossier_read_model.v1", doc)
