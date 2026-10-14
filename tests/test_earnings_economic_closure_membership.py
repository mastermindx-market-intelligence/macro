"""A carried dossier outside native selections is still a record.

Synthetic fixtures only. These tests never fetch a filing and never call an
EDGAR host. A v1 wire article that is absent from selections stays
unknown_record; that pin lives in the publication suite.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.earnings_narrative import private_publication as pp
from engine.research_vault.r2_store import LocalStore
from tests.earnings_economic_private_fixtures import reseal_manifest, stage_economic_case


def _prepared_valid(tmp_path: Path, name: str):
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid", name=name))
    manifest = json.loads(prepared.manifest_bytes)
    payloads = dict(prepared.payloads)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    return manifest, payloads, slug


def _drop_selection(manifest: dict, slug: str) -> dict:
    assert slug in manifest["records"]
    assert slug in manifest["native"]["selections"]
    manifest["native"]["selections"].pop(slug)
    sealed = reseal_manifest(manifest, pp)
    assert slug in sealed["records"]
    assert slug not in sealed["native"]["selections"]
    return sealed


def test_record_outside_selections_is_not_unknown_record(tmp_path: Path) -> None:
    manifest, payloads, slug = _prepared_valid(tmp_path, "outside")
    manifest = _drop_selection(manifest, slug)
    store = LocalStore(tmp_path / "store")
    receipt = manifest["records"][slug]
    assert store.put_bytes(receipt["object_key"], payloads[receipt["object_key"]]) is True
    try:
        pp.load_economic_closure(store, manifest=manifest, slug=slug)
    except pp.EarningsEconomicNotFound as exc:
        pytest.fail(f"raised {exc.reason}")
    except pp.EarningsPrivateClosureError as exc:
        assert exc.reason == "missing_artifact"


def test_unselected_slug_still_checks_the_chain(tmp_path: Path) -> None:
    manifest, payloads, slug = _prepared_valid(tmp_path, "chain")
    record = json.loads(payloads[manifest["records"][slug]["object_key"]])
    generation_ids: list[str] = []
    for observation in record["economic_interpretation"]["observations"]:
        handle = observation.get("handle") or {}
        generation_id = handle.get("workspace_generation_id")
        if type(generation_id) is str and generation_id not in generation_ids:
            generation_ids.append(generation_id)
    assert generation_ids
    workspace_id = generation_ids[0]
    assert workspace_id in manifest["native"]["workspaces"]
    receipt = manifest["native"]["workspaces"][workspace_id]
    body = bytearray(payloads[receipt["object_key"]])
    body[-1] ^= 0x01
    payloads[receipt["object_key"]] = bytes(body)
    manifest = _drop_selection(manifest, slug)
    try:
        pp.validate_native_closure(manifest, payloads, slugs=(slug,))
    except pp.EarningsPrivateClosureError as exc:
        if exc.reason != "digest_mismatch":
            pytest.fail(f"DID NOT RAISE digest_mismatch; reason={exc.reason}")
    else:
        pytest.fail("DID NOT RAISE digest_mismatch")
