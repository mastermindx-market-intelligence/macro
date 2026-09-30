"""Synthetic private-stage fixtures for native economic publication tests.

Every value here is synthetic and every acquisition is replayed from the frozen
Task 2 fixture. The module caches deterministic native evidence per process.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from engine.earnings_narrative import economic_interpretation
from engine.earnings_narrative.context_packets import canonical_json_bytes
from engine.company_intelligence import event_workspace, pg_profile
from scripts import refresh_event_workspaces
from tests.earnings_economic_fixtures import fixture_http_get
from tests.test_earnings_private_store import _staged_publication

CUTOFF = "2026-07-31T00:00:00Z"
_CACHE: dict[str, dict[str, object]] = {}

def _acquire(case: str) -> dict:
    original = refresh_event_workspaces._PACE_S
    refresh_event_workspaces._PACE_S = 0
    try:
        acquisition = refresh_event_workspaces.acquire_results_filing(
            cik="0000080424",
            http_get=fixture_http_get(case),
            trace=[].append,
        )
    finally:
        refresh_event_workspaces._PACE_S = original
    acquisition["currentness"] = {
        "state": "up_to_date",
        "checked_at": "2026-07-30T20:00:00Z",
    }
    return acquisition

def _build_cache() -> dict[str, object]:
    if _CACHE:
        return _CACHE
    v1 = pg_profile.prepare_pg_workspace(
        _acquire("same_source_rebuild"),
        prior=None,
        observed_at="2026-07-29T17:10:00Z",
    )
    v2 = pg_profile.prepare_pg_workspace(
        _acquire("changed_bytes"),
        prior=v1,
        observed_at="2026-07-30T17:20:00Z",
    )
    v3 = pg_profile.prepare_pg_workspace(
        _acquire("amendment_sequence"),
        prior=v1,
        observed_at="2026-07-30T18:01:00Z",
    )
    for letter, result in (("v1", v1), ("v2", v2), ("v3", v3)):
        workspace = result["workspace"]
        document = result["document_metadata"]
        texts = {document["document_id"]: result["decoded_source"]}
        interpretation = economic_interpretation.build_economic_interpretation(
            workspace,
            source_texts=texts,
            fiscal_scope=tuple(result["currentness_context"]["fiscal_scope"]),
            selection={"facts": None, "currentness": result["currentness_context"]["currentness"]},
            semantic_revision=economic_interpretation.SEMANTIC_REVISION,
            code_revision=economic_interpretation.CODE_REVISION,
        )
        _CACHE[letter] = result
        _CACHE[f"{letter}_interpretation"] = interpretation
    return _CACHE

def _copy(value: object) -> object:
    return deepcopy(value)

def _selection_for(result: dict, interpretation: dict) -> dict:
    return {
        "company_id": "cik:0000080424",
        "event_id": result["workspace"]["event_id"],
        "profile_version": pg_profile.PG_PROFILE_VERSION,
        "fiscal_scope": list(result["currentness_context"]["fiscal_scope"]),
        "chain": [{
            "workspace": result["workspace"]["generation_id"],
            "document": sha256(canonical_json_bytes(result["document_metadata"])).hexdigest(),
        }],
        "selection": {"facts": None, "currentness": result["currentness_context"]["currentness"]},
        "interpretation_id": interpretation["interpretation_id"],
    }

def economic_stage_parts(case: str) -> dict:
    cache = _build_cache()
    if case in ("valid", "wire_unavailable", "wire_interpretation", "three_handles", "currentness_none"):
        chain = [cache["v1"]]
        interpretation = _copy(cache["v1_interpretation"])
    elif case == "corrected":
        chain = [cache["v1"], cache["v2"]]
        interpretation = _copy(cache["v2_interpretation"])
    elif case == "amended":
        chain = [cache["v1"], cache["v3"]]
        interpretation = _copy(cache["v3_interpretation"])
    else:
        raise ValueError("unknown synthetic private economic stage case")

    selection = _selection_for(chain[-1], interpretation)
    rebuilt = None
    if case == "currentness_none":
        selection["selection"]["currentness"] = None
    if case == "three_handles":
        selection["selection"]["facts"] = [
            deepcopy(item["handle"]) for item in interpretation["observations"][:3]
        ]
    if case in ("three_handles", "currentness_none"):
        rebuilt = economic_interpretation.build_economic_interpretation(
            chain[-1]["workspace"],
            source_texts={chain[-1]["document_metadata"]["document_id"]: chain[-1]["decoded_source"]},
            fiscal_scope=tuple(chain[-1]["currentness_context"]["fiscal_scope"]),
            selection=selection["selection"],
            semantic_revision=economic_interpretation.SEMANTIC_REVISION,
            code_revision=economic_interpretation.CODE_REVISION,
        )
        selection["interpretation_id"] = rebuilt["interpretation_id"]

    if case == "wire_interpretation":
        record_interpretation = _copy(cache["v1_interpretation"])
    else:
        record_interpretation = {"state": "unavailable", "reason": "no_native_selection"}

    native_interpretation = _copy(rebuilt if rebuilt is not None else interpretation)
    dossier = {
        "schema": "earnings.tier_payload/v2",
        "page": "earnings_economic_dossier",
        "slug": "pg-synthetic-economic-dossier",
        "required_tier": "essential",
        "public_facts": 0,
        "locked_facts": len(native_interpretation["observations"]),
        "facts_html": "",
        "receipt_rows_html": "",
        "economic_interpretation": native_interpretation,
    }
    return {
        "chains": [[{"version": result} for result in chain]],
        "selection": selection,
        "selections": {dossier["slug"]: selection},
        "slots": {"cik:0000080424": {"slug": dossier["slug"], "event_id": selection["event_id"]}},
        "received": {
            result["document_metadata"]["content_sha256"]: result["received_byte_receipt"]
            for result in chain
        },
        "cutoff": CUTOFF,
        "previous_manifest": None,
        "wire_v2": case in ("wire_unavailable", "wire_interpretation"),
        "wire_interpretation": record_interpretation,
        "dossier": dossier,
    }

def write_economic_stage(stage_dir: Path, parts: dict) -> Path:
    _public_dir, private_dir, wire_slug = _staged_publication(stage_dir.parent)
    records_dir = private_dir / "records"
    dossier = parts["dossier"]
    if parts.get("wire_v2"):
        wire_path = records_dir / f"{wire_slug}.json"
        wire = json.loads(wire_path.read_bytes())
        wire["schema"] = "earnings.tier_payload/v2"
        wire["economic_interpretation"] = parts["wire_interpretation"]
        if "interpretation_id" in parts["wire_interpretation"]:
            wire.update({key: dossier.get(key, wire.get(key)) for key in ("page", "public_facts", "locked_facts", "facts_html", "receipt_rows_html")})
        wire_path.write_bytes(canonical_json_bytes(wire))
    native = private_dir / "native"
    workspaces = native / "workspaces"
    documents = native / "documents"
    bodies = native / "source_bodies"
    for directory in (workspaces, documents, bodies):
        directory.mkdir(parents=True, exist_ok=True)
    chain_catalogs: list[dict] = []
    for chain in parts["chains"]:
        entries = []
        for item in chain:
            result = item["version"]
            workspace_body = canonical_json_bytes(result["workspace"])
            document_body = canonical_json_bytes(result["document_metadata"])
            text_body = result["decoded_source"].encode("utf-8")
            (workspaces / f"{result['workspace']['generation_id']}.json").write_bytes(workspace_body)
            document_digest = sha256(document_body).hexdigest()
            (documents / f"{document_digest}.json").write_bytes(document_body)
            (bodies / f"{result['document_metadata']['content_sha256']}.txt").write_bytes(text_body)
            entries.append({"workspace": result["workspace"]["generation_id"], "document": document_digest})
        chain_catalogs.append(entries)
    for slug in parts["selections"]:
        parts["selections"][slug]["chain"] = chain_catalogs[0]
    if "interpretation_id" in parts["wire_interpretation"]:
        old_slug = dossier["slug"]
        dossier["slug"] = wire_slug
        parts["selections"][wire_slug] = parts["selections"].pop(old_slug)
        parts["slots"]["cik:0000080424"]["slug"] = wire_slug
    else:
        (records_dir / f"{dossier['slug']}.json").write_bytes(canonical_json_bytes(dossier))
    stage_manifest = {
        "schema": "earnings.private_native_stage/v1",
        "native_source_cutoff": parts["cutoff"],
        "previous_manifest": parts["previous_manifest"],
        "selections": parts["selections"],
        "economic_slots": parts["slots"],
        "received": parts["received"],
    }
    (native / "latest.json").write_bytes(canonical_json_bytes(stage_manifest))
    return private_dir

def stage_economic_case(tmp_path: Path, case: str) -> Path:
    return write_economic_stage(tmp_path / "economic", economic_stage_parts(case))

def reseal_workspace(workspace: dict) -> dict:
    workspace["generation_id"] = event_workspace.preview_generation_identity(
        {workspace["event_id"]: workspace},
        workspace["generated_at"],
        previous_generation_id=None,
    )
    return workspace

def reseal_manifest(manifest: dict, module: object) -> dict:
    manifest["generation_id"] = module._generation_id(manifest)
    return manifest
