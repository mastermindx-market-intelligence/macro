"""A record outside native selections is not an economic closure.

Synthetic fixtures only. These tests never fetch a filing and never call an
EDGAR host. Native selections are the membership list: ``load_economic_closure``
refuses any slug they omit with ``unknown_record``, a v2 dossier included, and
full validation refuses a dossier carried outside them with
``malformed_native_section``. A v1 wire article that is absent from selections
stays unknown_record too; that pin lives in the publication suite.
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


def _store_all(tmp_path: Path, payloads: dict) -> LocalStore:
    store = LocalStore(tmp_path / "store")
    for key, body in payloads.items():
        assert store.put_bytes(key, body) is True
    return store


def test_record_outside_selections_is_unknown_record(tmp_path: Path) -> None:
    manifest, payloads, slug = _prepared_valid(tmp_path, "outside")
    # CONTROL: while selected, the same stored bytes load as a closure.
    store = _store_all(tmp_path, payloads)
    assert pp.load_economic_closure(store, manifest=manifest, slug=slug)["record"]["slug"] == slug

    manifest = _drop_selection(manifest, slug)
    with pytest.raises(pp.EarningsEconomicNotFound) as raised:
        pp.load_economic_closure(store, manifest=manifest, slug=slug)
    assert raised.value.reason == "unknown_record"


def _corrupt_first_workspace(manifest: dict, payloads: dict, slug: str) -> dict:
    record = json.loads(payloads[manifest["records"][slug]["object_key"]])
    generation_ids = [
        observation["handle"]["workspace_generation_id"]
        for observation in record["economic_interpretation"]["observations"]
        if type(observation.get("handle")) is dict
        and type(observation["handle"].get("workspace_generation_id")) is str
    ]
    assert generation_ids
    receipt = manifest["native"]["workspaces"][generation_ids[0]]
    body = bytearray(payloads[receipt["object_key"]])
    body[-1] ^= 0x01
    return {**payloads, receipt["object_key"]: bytes(body)}


@pytest.mark.parametrize("workspace_bytes", ["intact", "corrupted"])
def test_a_dossier_outside_selections_is_malformed_in_full_and_scoped_validation(
    tmp_path: Path, workspace_bytes: str,
) -> None:
    """Membership decides the refusal, not the dossier's chain bytes.

    The corrupted case pins that no chain is walked for an unselected slug: the
    refusal is the membership invariant, never ``digest_mismatch``.
    """
    manifest, payloads, slug = _prepared_valid(tmp_path, f"unselected-{workspace_bytes}")
    # CONTROL: the sealed manifest validates while the dossier is selected.
    assert slug in pp.validate_native_closure(manifest, payloads, slugs=(slug,))

    if workspace_bytes == "corrupted":
        payloads = _corrupt_first_workspace(manifest, payloads, slug)
    manifest = _drop_selection(manifest, slug)
    for slugs in ((slug,), None):
        with pytest.raises(pp.EarningsPrivateClosureError) as raised:
            pp.validate_native_closure(manifest, payloads, slugs=slugs)
        assert raised.value.reason == "malformed_native_section", slugs
