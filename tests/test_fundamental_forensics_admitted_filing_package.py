"""FIF D1: issuer-generic admitted filing packages from already-captured bytes."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import socket
from datetime import datetime, timezone
from pathlib import Path

import pytest

from collectors.sec_filing_parser import SEC_FILING_PARSER_ALGORITHM_FINGERPRINT
from engine.fundamental_forensics import admitted_filing_package as AFP
from engine.fundamental_forensics import production_datasets as PDS
from engine.fundamental_forensics.admitted_filing_package import (
    ADMITTED_FILING_PACKAGE_SCHEMA,
    REQUIRED_STORED_ROLES,
    AdmittedFilingPackage,
    AdmittedFilingPackageError,
    admit_retained_filing_package,
)
from engine.fundamental_forensics.financial_intelligence_packet import EntityInput
from engine.fundamental_forensics.filing_package import _MEMBER_STATES
from engine.fundamental_forensics.ixbrl_raw_ledger import (
    GOLDEN_AAPL_QUERY_ACCESSIONS,
    parse_and_convert_golden_packages,
)
from engine.fundamental_forensics.query_service import (
    CanonicalEntityBinding,
    execute_financial_query,
    fip1_fixture_dataset,
)
from engine.fundamental_forensics.sec_document_spine import (
    HARD_MAX_ARCHIVE_DOCUMENT_BYTES,
    HARD_MAX_ARCHIVE_INDEX_MEMBERS,
    archive_document_url,
    archive_index_url,
)
from engine.fundamental_forensics.statement_graph import (
    GOLDEN_AAPL_FIXTURES,
    load_golden_aapl_package,
)

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_RECORDED_AT = "2026-10-12T00:00:00Z"
INVENTED_NS = "http://example.invalid/fake-gaap/2099"
T_ADMITTED = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
T_FLOOR = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)

# Captured on this branch at de6ee6a2 before the passthrough edit. Golden
# manifests lack capture_basis/capture_recorded_at, so these ids/bytes must
# stay identical after the additive D3 field list change.
#
# Re-pinned 2026-10-19 by seat ruling R-9761-CLK (c), as G0 #9603 re-pinned for
# its registry change: the generation ids and the AAPL manifest bind the
# registry_json role, so the metric registry 1.1.0 pack (#9761) moves them while
# the statement-package index and the query bytes stay identical. The
# *_REGISTRY_V1_0_0 values are the previous pins; the golden test re-derives them
# exactly from the committed byte-copy of the 1.0.0 registry, so any drift other
# than the registry is still caught. Re-pinned again for the formula pack 1.1.0
# (F3 not-presented policy): only the generation ids and the manifest move; the
# index, the query bytes and every *_REGISTRY_V1_0_0 value re-derive unchanged.
_REGISTRY_V1_0_0_ROOT = ROOT / "tests" / "fixtures" / "fundamental_forensics_registry_v1_0_0"
_FIP1_GENERATION_ID = "ffprods_66cf00a6136b5b79ee4194294903e4affc565e928db6dca29f67be3a2e862069"
_FIP1_GENERATION_ID_REGISTRY_V1_0_0 = (
    "ffprods_099a50f4a0f65f632bdf197af27c4a3dd0f6bbc86d1cc3aee805dd12c191154e"
)
_FIP1_INDEX_SHA = "22376a6171015e6efe1857a289edd36a657bf7762bcb37bc08efe14ab548f4d7"
# re-pinned 2026-10-12 by seat ruling: P1 #8992 R2 added the optional
# statement_trees_json role (packages-bearing generations only)
# (re-pinned 2026-10-19 by R-9761-CLK (c); previous pins kept as *_REGISTRY_V1_0_0)
_AAPL_GOLDEN_GENERATION_ID = "ffprods_0c22ee6bf81f0e0dfa254427ee1f1ad69d21594941d21956bc67c178d71afe86"
_AAPL_GOLDEN_GENERATION_ID_REGISTRY_V1_0_0 = (
    "ffprods_e0cc353b1372f883ab481c76dda453e6903cd03e9ef10bfd6cd5d387e2317866"
)
_AAPL_GOLDEN_INDEX_SHA = "74c2975c1903ae026e2971490571463551ce33bf18cd9e40593e75b1e213bb3f"
_AAPL_GOLDEN_MANIFEST_SHA = "548e72417ecb54df70cce76bfbf82a2d1e5ebde2d484f239328f264930c01bbb"
_AAPL_GOLDEN_MANIFEST_SHA_REGISTRY_V1_0_0 = (
    "65dd20e2ad55737c35c75656b15af699fa3e1b99392a24c8c1a14b8d70bc3b1e"
)
_FIP1_QUERY_SHA = {
    "as_reported": "bf8e9099e0f94d891f8b739adf15eee8651a0478b55ecbed746ac19a734e2c02",
    "latest_known_as_of": "2d9964257abbe545322c54e4572956dffeddae257fc49ff11cef7264d0bd79d7",
    "latest_restated": "7ba7a23305a1284ddf6e75eba582eb58791922c46cd1d63b0147560888350c0a",
}
T1_SOURCE = "2024-12-31T23:59:59Z"
T2_RECORDED = "2026-08-03T12:00:00Z"


def _load_capture(accession: str) -> tuple[dict, bytes, dict[str, bytes], bytes]:
    relative = GOLDEN_AAPL_FIXTURES[accession]
    fixture = ROOT / relative
    manifest = json.loads((fixture / "package_manifest.json").read_text(encoding="utf-8"))
    index_bytes = (fixture / "index.json").read_bytes()
    witness_bytes = (fixture / "sec_submissions_witness.json").read_bytes()
    members: dict[str, bytes] = {}
    for item in manifest["members"]:
        if item.get("state") == "stored":
            members[item["name"]] = (fixture / item["path"]).read_bytes()
    return manifest, index_bytes, members, witness_bytes


def _admit(accession: str, **kwargs) -> AdmittedFilingPackage:
    manifest, index_bytes, members, witness_bytes = _load_capture(accession)
    return admit_retained_filing_package(
        index_bytes=index_bytes,
        manifest=manifest,
        members=members,
        witness_bytes=witness_bytes,
        capture_recorded_at=kwargs.pop("capture_recorded_at", CAPTURE_RECORDED_AT),
        capture_basis=kwargs.pop("capture_basis", "reconstruction"),
        **kwargs,
    )


def _retarget_member(manifest: dict, name: str, payload: bytes) -> None:
    for item in manifest["members"]:
        if item.get("name") == name:
            item["content_sha256"] = hashlib.sha256(payload).hexdigest()
            item["byte_length"] = len(payload)
            return
    raise AssertionError(f"member not in inventory: {name}")


def _rebind_index(manifest: dict, index_bytes: bytes) -> None:
    manifest["index_sha256"] = hashlib.sha256(index_bytes).hexdigest()
    manifest["index_byte_length"] = len(index_bytes)


def _rebind_witness(manifest: dict, witness_bytes: bytes) -> None:
    meta = dict(manifest["acceptance_witness"])
    meta["content_sha256"] = hashlib.sha256(witness_bytes).hexdigest()
    meta["byte_length"] = len(witness_bytes)
    manifest["acceptance_witness"] = meta


def _aapl_binding() -> CanonicalEntityBinding:
    return CanonicalEntityBinding(
        entity_id="ISS:US-XNAS-AAPL",
        cik="0000320193",
        ticker="AAPL",
        source_entity_id="0000320193",
    )


def _aapl_entity() -> EntityInput:
    return EntityInput(
        entity_id="ISS:US-XNAS-AAPL",
        cik="0000320193",
        ticker="AAPL",
        name="Apple Inc.",
        identity_basis="sec-cik",
        source_entity_id="0000320193",
    )


def _fip1_material(registry_root: Path = ROOT) -> PDS.ProductionDatasetMaterial:
    base = fip1_fixture_dataset(ROOT)
    return PDS.ProductionDatasetMaterial(
        binding=base.binding,
        entity=EntityInput(
            entity_id=base.binding.entity_id,
            cik=base.binding.cik,
            ticker=base.binding.ticker,
            name="FIP1 Fixture",
            identity_basis="sec-cik",
            source_entity_id=base.binding.source_entity_id,
        ),
        ledger=base.ledger,
        filing_metadata=base.filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(registry_root),
        admitted_at=T_ADMITTED,
        source_recorded_at_floor=T_FLOOR,
    )


def _query_body(*, selection: str) -> bytes:
    return json.dumps(
        {
            "schema": "fundamental_forensics.financial_query_request/v1",
            "entity_id": "mmx.issuer.fip1",
            "policy": {
                "selection": selection,
                "source_snapshot_at": T1_SOURCE,
                "recorded_at": T2_RECORDED,
            },
            "metric_ids": ["revenue"],
            "periods": [
                {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}
            ],
        },
        separators=(",", ":"),
    ).encode("utf-8")


class _StaticProvider:
    def __init__(self, dataset) -> None:
        self._dataset = dataset

    def resolve(self, entity_id: str):
        del entity_id
        return self._dataset


def test_aapl_golden_bytes_admit_as_reconstruction() -> None:
    for accession in GOLDEN_AAPL_QUERY_ACCESSIONS:
        admitted = _admit(accession)
        assert admitted.manifest["attested"] is False
        assert admitted.manifest["capture_basis"] == "reconstruction"
        assert admitted.manifest["schema"] == ADMITTED_FILING_PACKAGE_SCHEMA
        assert admitted.manifest["capture_recorded_at"] == CAPTURE_RECORDED_AT
        assert admitted.manifest["fixture_recorded_at"] == CAPTURE_RECORDED_AT
        assert admitted.manifest["source_accepted_at"]
        assert admitted.manifest["source_accepted_at"] != admitted.manifest["capture_recorded_at"]
        assert set(REQUIRED_STORED_ROLES).issubset(
            {
                item["role"]
                for item in admitted.manifest["members"]
                if item.get("state") == "stored"
            }
        )


def test_admitted_package_feeds_incumbent_ledger_converter() -> None:
    for accession in GOLDEN_AAPL_QUERY_ACCESSIONS:
        golden = load_golden_aapl_package(ROOT, accession=accession)
        admitted = _admit(accession)
        _, _, golden_report = parse_and_convert_golden_packages([golden])
        _, _, admitted_report = parse_and_convert_golden_packages([admitted])
        assert admitted_report.filings[0].parser_numeric_fact_count == (
            golden_report.filings[0].parser_numeric_fact_count
        )
        assert admitted_report.filings[0].ledger_occurrence_count == (
            golden_report.filings[0].ledger_occurrence_count
        )


def test_admitted_package_publishes_through_d3_store_as_reconstruction() -> None:
    packages = tuple(_admit(accession) for accession in GOLDEN_AAPL_QUERY_ACCESSIONS)
    ledger, filing_metadata, _report = parse_and_convert_golden_packages(packages)
    material = PDS.ProductionDatasetMaterial(
        binding=_aapl_binding(),
        entity=_aapl_entity(),
        ledger=ledger,
        filing_metadata=filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=T_ADMITTED,
        source_recorded_at_floor=T_FLOOR,
        packages=packages,
        security_id="SEC:US-XNAS-AAPL",
        listing_key="US-XNAS-AAPL",
    )
    store = PDS.InMemoryStrictConditionalStore()
    publication = PDS.publish_production_dataset(store, material)
    generation = PDS.load_generation(store, "ISS:US-XNAS-AAPL", publication.generation_id)
    delivery = generation.delivery()
    assert delivery["attested"] is False
    assert delivery["capture_basis"] == "reconstruction"
    index = json.loads(generation.role_payloads["statement_packages_index_json"])
    assert index["accessions"]
    for item in index["accessions"]:
        stored_manifest = item["manifest"]
        assert stored_manifest["capture_basis"] == "reconstruction"
        assert stored_manifest["capture_recorded_at"] == CAPTURE_RECORDED_AT


def test_ambiguous_write_keeps_effect_unknown_on_original_target() -> None:
    packages = tuple(_admit(accession) for accession in GOLDEN_AAPL_QUERY_ACCESSIONS)
    ledger, filing_metadata, _report = parse_and_convert_golden_packages(packages)
    material = PDS.ProductionDatasetMaterial(
        binding=_aapl_binding(),
        entity=_aapl_entity(),
        ledger=ledger,
        filing_metadata=filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=T_ADMITTED,
        source_recorded_at_floor=T_FLOOR,
        packages=packages,
        security_id="SEC:US-XNAS-AAPL",
        listing_key="US-XNAS-AAPL",
    )
    store = PDS.InMemoryStrictConditionalStore()
    store.raise_on_conditional_after_commit = True
    publication = PDS.publish_production_dataset(store, material)
    assert publication.generation_id
    assert store.unconditional_writes == []

    store2 = PDS.InMemoryStrictConditionalStore()
    store2.raise_on_conditional_after_commit = True
    store2.drop_after_commit = True
    with pytest.raises(PDS.ProductionDatasetEffectUnknownError):
        PDS.publish_production_dataset(store2, material)
    assert store2.unconditional_writes == []


def test_refusal_index_digest_mismatch() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    hostile = index_bytes[:-1] + bytes([index_bytes[-1] ^ 0x01])
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=hostile,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "index_digest_mismatch"


def test_refusal_index_malformed_duplicate() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    payload = json.loads(index_bytes.decode("utf-8"))
    payload["directory"]["item"].append(payload["directory"]["item"][0])
    hostile = json.dumps(payload).encode("utf-8")
    manifest = copy.deepcopy(manifest)
    _rebind_index(manifest, hostile)
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=hostile,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "index_malformed"


def test_refusal_index_malformed_unnamed() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    payload = json.loads(index_bytes.decode("utf-8"))
    payload["directory"]["item"].append({"name": "", "type": "text.gif", "size": ""})
    hostile = json.dumps(payload).encode("utf-8")
    manifest = copy.deepcopy(manifest)
    _rebind_index(manifest, hostile)
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=hostile,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "index_malformed"


def test_refusal_inventory_mismatch() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    manifest["members"].append(
        {"name": "not-in-the-archive.fake", "state": "not_requested", "role": "archive"}
    )
    manifest["member_count"] = int(manifest["member_count"]) + 1
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "inventory_mismatch"


def test_refusal_required_role_missing() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    members = dict(members)
    dropped = None
    for item in manifest["members"]:
        if item.get("role") == "presentation" and item.get("state") == "stored":
            dropped = item["name"]
            item["state"] = "not_requested"
            item.pop("content_sha256", None)
            item.pop("byte_length", None)
            item.pop("path", None)
            break
    assert dropped is not None
    members.pop(dropped, None)
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "required_role_missing"


def test_refusal_member_digest_mismatch() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    members = dict(members)
    name = next(iter(members))
    original = members[name]
    members[name] = original[:-1] + bytes([original[-1] ^ 0x01])
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "member_digest_mismatch"


def test_refusal_member_oversize(monkeypatch) -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    monkeypatch.setattr(AFP, "HARD_MAX_ARCHIVE_DOCUMENT_BYTES", 16)
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "member_oversize"
    monkeypatch.setattr(AFP, "HARD_MAX_ARCHIVE_DOCUMENT_BYTES", HARD_MAX_ARCHIVE_DOCUMENT_BYTES)
    monkeypatch.setattr(AFP, "HARD_MAX_ARCHIVE_INDEX_MEMBERS", 1)
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "member_oversize"
    assert HARD_MAX_ARCHIVE_INDEX_MEMBERS >= 1


def test_refusal_witness_mismatch() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    witness = json.loads(witness_bytes.decode("utf-8"))
    witness["accessionNumber"] = "0000320193-99-999999"
    hostile = json.dumps(witness, separators=(",", ":")).encode("utf-8")
    manifest = copy.deepcopy(manifest)
    _rebind_witness(manifest, hostile)
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=hostile,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "witness_mismatch"


def test_refusal_clock_order_violation() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at="2020-01-01T00:00:00Z",
        )
    assert caught.value.code == "clock_order_violation"


def test_refusal_unlawful_capture_basis() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
            capture_basis="attested",
        )
    assert caught.value.code == "unlawful_capture_basis"


def test_refusal_attestation_claim_refused() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    manifest["attested"] = True
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "attestation_claim_refused"


def test_refusal_identity_mismatch() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    manifest["cik"] = "0000999999"
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "identity_mismatch"


def test_partial_package_is_never_returned(monkeypatch) -> None:
    constructed: list[AdmittedFilingPackage] = []
    real = AFP.AdmittedFilingPackage

    def _spy(*args, **kwargs):
        obj = real(*args, **kwargs)
        constructed.append(obj)
        return obj

    monkeypatch.setattr(AFP, "AdmittedFilingPackage", _spy)
    test_refusal_index_digest_mismatch()
    test_refusal_required_role_missing()
    test_refusal_member_digest_mismatch()
    test_refusal_attestation_claim_refused()
    test_refusal_identity_mismatch()
    test_doctype_and_entity_declarations_refused()
    assert constructed == []


def test_doctype_and_entity_declarations_refused() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    members = dict(members)
    primary = manifest["primary_document"]
    hostile = members[primary].replace(
        b"<html",
        b"<!DOCTYPE html [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><html",
        1,
    )
    assert b"<!DOCTYPE" in hostile and b"<!ENTITY" in hostile
    members[primary] = hostile
    _retarget_member(manifest, primary, hostile)
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "primary_unparseable"
    assert "DTD" in str(caught.value) or "entity" in str(caught.value).lower()


def test_script_content_is_inert(monkeypatch) -> None:
    calls: list[str] = []

    def _blocked(*_args, **_kwargs):
        calls.append("executed")
        raise AssertionError("script must not execute")

    monkeypatch.setattr("builtins.exec", _blocked, raising=False)
    monkeypatch.setattr("builtins.eval", _blocked, raising=False)
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", _blocked, raising=False)
    monkeypatch.setattr(subprocess, "run", _blocked, raising=False)
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    members = dict(members)
    primary = manifest["primary_document"]
    injected = members[primary].replace(
        b"<head>",
        b"<head><script>throw new Error('executed')</script>",
        1,
    )
    members[primary] = injected
    _retarget_member(manifest, primary, injected)
    try:
        admitted = admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    except AdmittedFilingPackageError as exc:
        assert exc.code == "primary_unparseable"
    else:
        assert admitted.parse_evidence["taxonomy_validation_complete"] is False
    assert calls == []


def test_no_network_during_admission(monkeypatch) -> None:
    def _blocked(*_args, **_kwargs):
        raise AssertionError("admission must not open a network connection")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    for accession in GOLDEN_AAPL_QUERY_ACCESSIONS:
        admitted = _admit(accession)
        assert admitted.manifest["attested"] is False


def test_module_performs_no_io_imports() -> None:
    source = (
        ROOT / "engine" / "fundamental_forensics" / "admitted_filing_package.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_modules = {
        "urllib",
        "urllib.request",
        "urllib.parse",
        "requests",
        "http.client",
        "httpx",
        "socket",
        "subprocess",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".", 1)[0] if alias.name != "urllib.parse" else alias.name)
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.add(node.module.split(".", 1)[0])
    assert forbidden_modules.isdisjoint(imported)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in {"now", "time", "system"}:
            if isinstance(node.value, ast.Name) and node.value.id in {"datetime", "time", "os"}:
                raise AssertionError(f"forbidden clock or process call: {node.value.id}.{node.attr}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            for keyword in node.keywords:
                if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
                    assert "w" not in str(keyword.value.value)
                    assert "a" not in str(keyword.value.value)
                    assert "x" not in str(keyword.value.value)


def test_invented_namespace_is_reported_with_original_uri() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    members = dict(members)
    primary = manifest["primary_document"]
    original = members[primary]
    marker = b'name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"'
    idx = original.find(marker)
    assert idx != -1
    tag_start = original.rfind(b"<ix:nonFraction", 0, idx)
    assert tag_start != -1
    insert_at = tag_start + len(b"<ix:nonFraction")
    injected = (
        original[:insert_at]
        + b' xmlns:us-gaap="'
        + INVENTED_NS.encode("ascii")
        + b'"'
        + original[insert_at:]
    )
    members[primary] = injected
    _retarget_member(manifest, primary, injected)
    admitted = admit_retained_filing_package(
        index_bytes=index_bytes,
        manifest=manifest,
        members=members,
        witness_bytes=witness_bytes,
        capture_recorded_at=CAPTURE_RECORDED_AT,
    )
    listed = admitted.parse_evidence["unadmitted_namespaces"]
    uris = [row["uri"] for row in listed]
    assert INVENTED_NS in uris
    matching = next(row for row in listed if row["uri"] == INVENTED_NS)
    assert matching["uri"] == INVENTED_NS
    assert matching["uri"].encode("ascii") == INVENTED_NS.encode("ascii")
    assert matching["fact_count"] >= 1
    ledger, _metadata, _report = parse_and_convert_golden_packages([admitted])
    invented = [event.concept_qname for event in ledger.events if INVENTED_NS in event.concept_qname]
    for qname in invented:
        assert qname.startswith("{" + INVENTED_NS + "}")
        assert not qname.startswith("us-gaap:")
    mapped = [event.concept_qname for event in ledger.events if event.concept_qname.startswith("us-gaap:")]
    assert INVENTED_NS not in "".join(mapped)


def test_parse_evidence_retains_unsupported_states() -> None:
    admitted = _admit(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    evidence = admitted.parse_evidence
    assert evidence["taxonomy_validation_complete"] is False
    assert evidence["algorithm_fingerprint"] == SEC_FILING_PARSER_ALGORITHM_FINGERPRINT
    assert evidence["profile"]
    assert evidence["version"]
    assert evidence["schema"]
    assert evidence["fact_count"] >= 1
    assert evidence["context_count"] >= 1
    assert evidence["unit_count"] >= 1
    assert "diagnostics" in evidence
    assert evidence["coverage"]["taxonomy_validation_complete"] is False
    apple_ns = "http://www.apple.com/20250927"
    unadmitted_uris = {row["uri"] for row in evidence["unadmitted_namespaces"]}
    assert apple_ns not in unadmitted_uris


def test_golden_generation_bytes_unchanged() -> None:
    # R-9761-CLK (c): the live registry carries the new pins; the same inputs
    # against the committed 1.0.0 registry root re-derive the previous pins
    # exactly, so the only moved input is the registry itself.
    for registry_root, fip1_generation_id in (
        (ROOT, _FIP1_GENERATION_ID),
        (_REGISTRY_V1_0_0_ROOT, _FIP1_GENERATION_ID_REGISTRY_V1_0_0),
    ):
        material = _fip1_material(registry_root)
        store = PDS.InMemoryStrictConditionalStore()
        publication = PDS.publish_production_dataset(store, material)
        assert publication.generation_id == fip1_generation_id, registry_root
        generation = PDS.load_generation(store, "mmx.issuer.fip1", publication.generation_id)
        assert (
            hashlib.sha256(generation.role_payloads["statement_packages_index_json"]).hexdigest()
            == _FIP1_INDEX_SHA
        )
    base = fip1_fixture_dataset(ROOT)
    for selection, expected in _FIP1_QUERY_SHA.items():
        result = execute_financial_query(
            body=_query_body(selection=selection),
            provider=_StaticProvider(base),
        )
        assert result.sha256 == expected, selection

    packages = [load_golden_aapl_package(ROOT, accession=a) for a in GOLDEN_AAPL_QUERY_ACCESSIONS]
    ledger, filing_metadata, _report = parse_and_convert_golden_packages(packages)

    def _aapl_material(registry_root: Path) -> PDS.ProductionDatasetMaterial:
        return PDS.ProductionDatasetMaterial(
            binding=_aapl_binding(),
            entity=_aapl_entity(),
            ledger=ledger,
            filing_metadata=filing_metadata,
            registry_payload=PDS.snapshot_core_registry_payload(registry_root),
            admitted_at=T_ADMITTED,
            source_recorded_at_floor=T_FLOOR,
            packages=tuple(packages),
            security_id="SEC:US-XNAS-AAPL",
            listing_key="US-XNAS-AAPL",
        )

    store_v1_0_0 = PDS.InMemoryStrictConditionalStore()
    publication_v1_0_0 = PDS.publish_production_dataset(
        store_v1_0_0, _aapl_material(_REGISTRY_V1_0_0_ROOT)
    )
    assert publication_v1_0_0.generation_id == _AAPL_GOLDEN_GENERATION_ID_REGISTRY_V1_0_0
    assert hashlib.sha256(store_v1_0_0.get_bytes(publication_v1_0_0.manifest_key)).hexdigest() == (
        _AAPL_GOLDEN_MANIFEST_SHA_REGISTRY_V1_0_0
    )
    generation_v1_0_0 = PDS.load_generation(
        store_v1_0_0, "ISS:US-XNAS-AAPL", publication_v1_0_0.generation_id
    )
    assert (
        hashlib.sha256(generation_v1_0_0.role_payloads["statement_packages_index_json"]).hexdigest()
        == _AAPL_GOLDEN_INDEX_SHA
    )

    store2 = PDS.InMemoryStrictConditionalStore()
    publication2 = PDS.publish_production_dataset(store2, _aapl_material(ROOT))
    assert publication2.generation_id == _AAPL_GOLDEN_GENERATION_ID
    generation2 = PDS.load_generation(store2, "ISS:US-XNAS-AAPL", publication2.generation_id)
    index_payload = generation2.role_payloads["statement_packages_index_json"]
    assert hashlib.sha256(index_payload).hexdigest() == _AAPL_GOLDEN_INDEX_SHA
    assert hashlib.sha256(store2.get_bytes(publication2.manifest_key)).hexdigest() == (
        _AAPL_GOLDEN_MANIFEST_SHA
    )
    assert [role["role"] for role in json.loads(store2.get_bytes(publication2.manifest_key))["roles"]] == [
        "ledger_json",
        "filing_metadata_json",
        "registry_json",
        "entity_json",
        "statement_packages_index_json",
        "lineage_evidence_json",
        "statement_trees_json",
    ]
    index = json.loads(index_payload)
    for item in index["accessions"]:
        assert "capture_basis" not in item["manifest"]
        assert "capture_recorded_at" not in item["manifest"]


# --- D1 amendment r2: agent-filed issuers, as-filed identity, closed states ---


def test_agent_filed_accession_prefix_is_admitted() -> None:
    # The accession prefix names the transmitting filing agent (Donnelley
    # 0000950170), never the issuer. Identity binds through the archive URLs,
    # the witness, and the filing's dei facts instead.
    accession = GOLDEN_AAPL_QUERY_ACCESSIONS[0]
    manifest, index_bytes, members, witness_bytes = _load_capture(accession)
    manifest = copy.deepcopy(manifest)
    cik = manifest["cik"]
    agent_accession = "0000950170-25-000079"
    assert agent_accession[:10] != cik

    witness = json.loads(witness_bytes.decode("utf-8"))
    witness["accessionNumber"] = agent_accession
    hostile_witness = json.dumps(witness, separators=(",", ":")).encode("utf-8")
    _rebind_witness(manifest, hostile_witness)

    index_payload = json.loads(index_bytes.decode("utf-8"))
    for entry in index_payload["directory"]["item"]:
        entry["name"] = entry["name"].replace(accession, agent_accession)
    hostile_index = json.dumps(index_payload).encode("utf-8")
    _rebind_index(manifest, hostile_index)

    renamed_members: dict[str, bytes] = {}
    for item in manifest["members"]:
        old_name = item["name"]
        new_name = old_name.replace(accession, agent_accession)
        item["name"] = new_name
        if "archive_url" in item:
            item["archive_url"] = archive_document_url(cik, agent_accession, new_name)
        if item.get("state") == "stored":
            renamed_members[new_name] = members[old_name]

    manifest["accession"] = agent_accession
    manifest["archive_index_url"] = archive_index_url(cik, agent_accession)
    admitted = admit_retained_filing_package(
        index_bytes=hostile_index,
        manifest=manifest,
        members=renamed_members,
        witness_bytes=hostile_witness,
        capture_recorded_at=CAPTURE_RECORDED_AT,
    )
    assert admitted.manifest["cik"] == "0000320193"
    assert admitted.manifest["accession"] == agent_accession
    assert admitted.manifest["issuer_identity_as_of"]["registrant_name_as_filed"] == "Apple Inc."
    assert admitted.manifest["issuer_identity_as_of"]["cik"] == "0000320193"


def test_member_archive_url_for_other_cik_is_identity_mismatch() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    victim = next(
        item
        for item in manifest["members"]
        if item.get("role") == "primary" and item.get("state") == "stored"
    )
    victim["archive_url"] = victim["archive_url"].replace("/320193/", "/999999/")
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "identity_mismatch"


def test_archive_index_url_for_other_cik_is_identity_mismatch() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    manifest["archive_index_url"] = manifest["archive_index_url"].replace("/320193/", "/999999/")
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "identity_mismatch"


def test_witness_source_url_cik_mismatch_is_identity_mismatch() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    witness = json.loads(witness_bytes.decode("utf-8"))
    witness["source_url"] = "https://data.sec.gov/submissions/CIK0000999999.json"
    hostile = json.dumps(witness, separators=(",", ":")).encode("utf-8")
    manifest = copy.deepcopy(manifest)
    _rebind_witness(manifest, hostile)
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=hostile,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "identity_mismatch"


def test_dei_central_index_key_mismatch_is_identity_mismatch() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    members = dict(members)
    primary = manifest["primary_document"]
    original = members[primary]
    marker = b'name="dei:EntityCentralIndexKey"'
    marker_at = original.find(marker)
    assert marker_at != -1
    value_start = original.find(b">", marker_at) + 1
    value_end = original.find(b"<", value_start)
    assert original[value_start:value_end] == b"0000320193"
    hostile = original[:value_start] + b"0000999999" + original[value_end:]
    members[primary] = hostile
    _retarget_member(manifest, primary, hostile)
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "identity_mismatch"


def test_issuer_identity_as_of_comes_from_the_filing_not_the_caller() -> None:
    for accession in GOLDEN_AAPL_QUERY_ACCESSIONS:
        manifest, index_bytes, members, witness_bytes = _load_capture(accession)
        manifest = copy.deepcopy(manifest)
        later_name = "Apple Corporation (renamed 2026)"
        manifest["legal_name"] = later_name
        admitted = admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
        identity = admitted.manifest["issuer_identity_as_of"]
        assert identity["cik"] == "0000320193"
        assert identity["registrant_name_as_filed"] == "Apple Inc."
        assert identity["registrant_name_as_filed"] != later_name
        assert identity["name_basis"] == "primary_document_dei"
        assert identity["as_of_clock"] == "source_accepted_at"
        assert identity["as_of"] == manifest["source_accepted_at"]
        # The caller's current-master label stays a separate passthrough.
        assert admitted.manifest["legal_name"] == later_name


def test_issuer_identity_absent_in_filing_when_primary_carries_no_dei_name() -> None:
    manifest, index_bytes, members, witness_bytes = _load_capture(GOLDEN_AAPL_QUERY_ACCESSIONS[0])
    manifest = copy.deepcopy(manifest)
    members = dict(members)
    primary = manifest["primary_document"]
    original = members[primary]
    marker = b'name="dei:EntityRegistrantName"'
    marker_at = original.find(marker)
    assert marker_at != -1
    start = original.rfind(b"<ix:nonNumeric", 0, marker_at)
    end = original.find(b"</ix:nonNumeric>", marker_at) + len(b"</ix:nonNumeric>")
    assert original[start:end].endswith(b"Apple Inc.</ix:nonNumeric>")
    stripped = original[:start] + original[end:]
    members[primary] = stripped
    _retarget_member(manifest, primary, stripped)
    admitted = admit_retained_filing_package(
        index_bytes=index_bytes,
        manifest=manifest,
        members=members,
        witness_bytes=witness_bytes,
        capture_recorded_at=CAPTURE_RECORDED_AT,
    )
    identity = admitted.manifest["issuer_identity_as_of"]
    assert identity["registrant_name_as_filed"] is None
    assert identity["name_basis"] == "absent_in_filing"
    assert identity["cik"] == "0000320193"
    assert identity["as_of"] == manifest["source_accepted_at"]


def test_dei_identity_helper_reads_parsed_facts_alone() -> None:
    parsed = {
        "facts": [
            {
                "concept_qname": "{http://xbrl.sec.gov/dei/2024}EntityCentralIndexKey",
                "status": "available",
                "transformed_value": "320193",
                "raw_value": "320193",
            },
            {
                "concept_qname": "{http://xbrl.sec.gov/dei/2024}EntityRegistrantName",
                "status": "available",
                "transformed_value": "Acme, Inc.",
                "raw_value": "Acme, Inc.",
            },
            {
                "concept_qname": "{http://xbrl.sec.gov/dei/2024}DocumentType",
                "status": "available",
                "transformed_value": "10-K",
                "raw_value": "10-K",
            },
            {
                "concept_qname": "{http://example.invalid/x}EntityRegistrantName",
                "status": "available",
                "transformed_value": "IMPOSTOR",
                "raw_value": "IMPOSTOR",
            },
            {
                "concept_qname": "{http://xbrl.sec.gov/dei/2024}EntityCentralIndexKey",
                "status": "invalid_value",
                "transformed_value": None,
                "raw_value": "garbage",
            },
        ]
    }
    dei = AFP._dei_identity(parsed)
    assert dei["entity_cik_values"] == ("320193",)
    assert dei["registrant_name_as_filed"] == "Acme, Inc."
    empty = AFP._dei_identity({"facts": []})
    assert empty["entity_cik_values"] == ()
    assert empty["registrant_name_as_filed"] is None


def test_module_never_binds_through_current_issuer_master() -> None:
    source = (
        ROOT / "engine" / "fundamental_forensics" / "admitted_filing_package.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_modules = {"lib", "lib.dataos", "dataos"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
                imported.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(forbidden_modules)
    referenced: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
    assert referenced.isdisjoint(
        {"IssuerMaster", "security_master", "statement_service", "IssuerIdentity"}
    )


def test_unknown_member_state_is_inventory_mismatch() -> None:
    for junk in ("garbage", "stored ", None):
        manifest, index_bytes, members, witness_bytes = _load_capture(
            GOLDEN_AAPL_QUERY_ACCESSIONS[0]
        )
        manifest = copy.deepcopy(manifest)
        victim = next(
            item for item in manifest["members"] if item.get("state") == "not_requested"
        )
        if junk is None:
            victim.pop("state", None)
        else:
            victim["state"] = junk
        with pytest.raises(AdmittedFilingPackageError) as caught:
            admit_retained_filing_package(
                index_bytes=index_bytes,
                manifest=manifest,
                members=members,
                witness_bytes=witness_bytes,
                capture_recorded_at=CAPTURE_RECORDED_AT,
            )
        assert caught.value.code == "inventory_mismatch"


def test_member_states_reuse_the_incumbent_vocabulary() -> None:
    assert AFP._MEMBER_STATES is _MEMBER_STATES
    assert "stored" in AFP._MEMBER_STATES
    assert AFP._MEMBER_STATES == frozenset(
        {"stored", "missing", "not_requested", "rejected_by_policy"}
    )


# ---------------------------------------------------------------------------
# C0-c ERRATA-4 R7: form-keyed admission of the 8-K member set (a1..a6, a8)
# ---------------------------------------------------------------------------

_EIGHT_K_DROP = ("_cal.xml", "_def.xml")


def _eight_k_capture(
    accession: str,
    *,
    drop_suffixes: tuple[str, ...] = _EIGHT_K_DROP,
    record_absent: bool = True,
    form: str = "8-K",
) -> tuple[dict, bytes, dict[str, bytes], bytes]:
    """A golden capture reshaped into the C0-c 8-K member-set shape.

    Form re-bound in BOTH the manifest and the witness (R8 makes them equal);
    the dropped members removed from the index, the inventory, and the member
    dict; absent_members recorded per R2 when ``record_absent``.
    """
    manifest, index_bytes, members, witness_bytes = _load_capture(accession)
    manifest = json.loads(json.dumps(manifest))
    stem = str(manifest["primary_document"]).rsplit(".", 1)[0]
    payload = json.loads(index_bytes.decode("utf-8"))
    dropped_names = [f"{stem}{suffix}" for suffix in drop_suffixes]
    payload["directory"]["item"] = [
        item
        for item in payload["directory"]["item"]
        if item.get("name") not in dropped_names
    ]
    new_index = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
    _rebind_index(manifest, new_index)
    manifest["members"] = [
        item for item in manifest["members"] if item.get("name") not in dropped_names
    ]
    manifest["member_count"] = len(payload["directory"]["item"])
    manifest["retained_count"] = sum(
        1 for item in manifest["members"] if item.get("state") == "stored"
    )
    members = {name: value for name, value in members.items() if name not in dropped_names}
    manifest["form"] = form
    witness = json.loads(witness_bytes.decode("utf-8"))
    witness["form"] = form
    new_witness = (json.dumps(witness, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _rebind_witness(manifest, new_witness)
    if record_absent and drop_suffixes:
        role_of = {"_cal.xml": "calculation", "_def.xml": "definition"}
        manifest["absent_members"] = sorted(
            (
                {"role": role_of[suffix], "name": f"{stem}{suffix}", "reason": "absent_in_archive_index"}
                for suffix in drop_suffixes
            ),
            key=lambda entry: entry["name"],
        )
    return manifest, new_index, members, new_witness


def _admit_capture(capture: tuple[dict, bytes, dict[str, bytes], bytes]) -> AdmittedFilingPackage:
    manifest, index_bytes, members, witness_bytes = capture
    return admit_retained_filing_package(
        index_bytes=index_bytes,
        manifest=manifest,
        members=members,
        witness_bytes=witness_bytes,
        capture_recorded_at=CAPTURE_RECORDED_AT,
    )


def test_c0c_a1_eight_k_with_recorded_absent_optionals_admits() -> None:
    """(a1) An 8-K with _cal and _def recorded absent is admitted."""
    accession = sorted(GOLDEN_AAPL_FIXTURES)[0]
    admitted = _admit_capture(_eight_k_capture(accession))
    assert admitted.manifest["form"] == "8-K"
    assert "absent_members" in admitted.manifest


def test_c0c_a2_absent_entry_naming_an_indexed_member_refuses() -> None:
    """(a2) An absent entry naming a member that IS in the index ->
    ``inventory_mismatch``."""
    accession = sorted(GOLDEN_AAPL_FIXTURES)[0]
    capture = _eight_k_capture(accession, drop_suffixes=("_def.xml",))
    manifest, index_bytes, members, witness_bytes = capture
    stem = str(manifest["primary_document"]).rsplit(".", 1)[0]
    # The entry claims _cal absent while the index still names AND stores it.
    manifest["absent_members"] = [
        {
            "role": "calculation",
            "name": f"{stem}_cal.xml",
            "reason": "absent_in_archive_index",
        }
    ]
    with pytest.raises(AdmittedFilingPackageError) as caught:
        _admit_capture((manifest, index_bytes, members, witness_bytes))
    assert caught.value.code == "inventory_mismatch"


def test_c0c_a3_eight_k_missing_optional_without_record_refuses() -> None:
    """(a3) An 8-K missing _def with no record (silence) -> refused."""
    accession = sorted(GOLDEN_AAPL_FIXTURES)[0]
    capture = _eight_k_capture(
        accession, drop_suffixes=("_def.xml",), record_absent=False
    )
    with pytest.raises(AdmittedFilingPackageError) as caught:
        _admit_capture(capture)
    assert caught.value.code == "inventory_mismatch"


def test_c0c_a4_ten_k_carrying_absent_members_refuses() -> None:
    """(a4) A 10-K carrying ``absent_members`` -> refused (R7 bounds: the map
    relaxes exactly "8-K")."""
    accession = sorted(GOLDEN_AAPL_FIXTURES)[0]
    manifest, index_bytes, members, witness_bytes = _load_capture(accession)
    manifest = json.loads(json.dumps(manifest))
    stem = str(manifest["primary_document"]).rsplit(".", 1)[0]
    manifest["absent_members"] = [
        {
            "role": "calculation",
            "name": f"{stem}_cal.xml",
            "reason": "absent_in_archive_index",
        }
    ]
    with pytest.raises(AdmittedFilingPackageError) as caught:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=members,
            witness_bytes=witness_bytes,
            capture_recorded_at=CAPTURE_RECORDED_AT,
        )
    assert caught.value.code == "inventory_mismatch"


def test_c0c_a5_eight_k_missing_label_refuses() -> None:
    """(a5) An 8-K missing _lab -> ``required_role_missing`` (label is
    required for the form)."""
    accession = sorted(GOLDEN_AAPL_FIXTURES)[0]
    capture = _eight_k_capture(
        accession, drop_suffixes=("_lab.xml",), record_absent=False
    )
    with pytest.raises(AdmittedFilingPackageError) as caught:
        _admit_capture(capture)
    assert caught.value.code == "required_role_missing"


def test_c0c_a6_every_golden_admission_unchanged() -> None:
    """(a6) Every existing golden admission passes unchanged: each committed
    golden capture still admits exactly as before the R7 edit."""
    for accession in sorted(GOLDEN_AAPL_FIXTURES):
        admitted = _admit(accession)
        assert admitted.manifest["schema"] == ADMITTED_FILING_PACKAGE_SCHEMA
        assert admitted.manifest["capture_basis"] == "reconstruction"
        for role in REQUIRED_STORED_ROLES:
            assert role in {
                item.get("role")
                for item in admitted.manifest["members"]
                if item.get("state") == "stored"
            }, (accession, role)


def test_c0c_a8_eight_k_a_carrying_absent_members_refuses() -> None:
    """(a8) An 8-K/A carrying ``absent_members`` -> refused: every form string
    other than exactly "8-K" resolves to the strict policy."""
    accession = sorted(GOLDEN_AAPL_FIXTURES)[0]
    capture = _eight_k_capture(accession, form="8-K/A")
    with pytest.raises(AdmittedFilingPackageError) as caught:
        _admit_capture(capture)
    assert caught.value.code == "inventory_mismatch"
