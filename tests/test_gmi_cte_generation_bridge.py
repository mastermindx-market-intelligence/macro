"""Actual sealed ThemeState -> unchanged CTE wire qualification, synthetic only.

This is compatibility evidence, not a production/model-use rights grant. The
legacy projection intentionally dates its assembly; source effective/known clocks
stay on the richer state identity. Tests must not silently relabel that contract.
All source observations and publication stores live in pytest temporary roots.
"""
from __future__ import annotations

import copy
import json

import pytest
import yaml

from engine.company_intelligence.contracts import ContractError
from engine.company_intelligence.views import build_bundle as build_company
from engine.company_intelligence.views import write_generation as write_company
from engine.company_theme_exposure.contracts import (
    canonical_json_bytes, canonical_json_sha256, validate_exposure, validate_manifest,
)
from engine.company_theme_exposure.health import validate_generation
from engine.company_theme_exposure.views import load_company_generation
from scripts.build_company_theme_exposure import main as build_sidecar_cli
from engine.neuralweb import thematic_state, theme_state_adapter
from engine.neuralweb import theme_state_generation as generation
from engine.neuralweb import theme_state_generation_reader as reader
from tests.test_theme_state_generation import AcceptedFixture, nightly
from tests.test_theme_state_generation_reader import ReadFixture
from tests.test_theme_state_production import EFFECTIVE, production_world


@pytest.fixture
def bridge_world(production_world):
    """Put both owners on one valid common synthetic crosswalk before capture."""
    root = production_world
    path = root / "config/theme_crosswalk.yml"
    crosswalk = yaml.safe_load(path.read_text())
    crosswalk.update(version=1, unmapped_baskets=[])
    for row in crosswalk["themes"]:
        row["foresight_id"] = row["id"]
    path.write_text(yaml.safe_dump(crosswalk, allow_unicode=True))
    forecast = root / thematic_state._FORESIGHT_PATH
    value = json.loads(forecast.read_text())
    value["themes"][0]["theme"] = "grid"
    forecast.write_text(json.dumps(value))
    membership = root / "data/baskets/membership.json"
    value = json.loads(membership.read_text())
    value["baskets"]["travel"] = {"members": []}  # genuine empty membership
    membership.write_text(json.dumps(value))
    return root


def _publish(root, emitted_at, *, correction=False):
    bundle = theme_state_adapter.capture_owner_bundle(
        root, effective_at=EFFECTIVE, known_at=emitted_at,
    )
    plan = generation.prepare_generation(
        bundle, root=root, generated_at=emitted_at, activation_at=emitted_at,
        entry=generation.entry_preflight(root, legacy_api=not correction),
        **({"correction_reason": "controlled later-generation comparison"} if correction else {}),
    )
    generation.publish_generation(root, plan, controlled_verifier=AcceptedFixture())
    return plan


def _read(root, plan, *, use_at):
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    value = reader.read_generation(
        root, **plan["query"], purpose="research_internal", use_at=use_at,
        controlled_verifier=ReadFixture(),
    )
    assert value["state"] is not None, value
    assert {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    return value


def _sidecar(root, value, out, *, as_of):
    contexts, descriptor = build_company(
        [{"document_ticker": "HUBB", "fiscal_year": 2026, "fiscal_quarter": 3,
          "call_date": "2026-10-01", "updated_at": "2026-10-02T00:00:00Z",
          "summary": "Controlled company evidence", "raw_source_url": "https://issuer.example/hubb"}],
        tx_index={"schema": "mastermind.tx-index/v1", "documents": []},
        generated_at=as_of + "T13:00:00Z", as_of=as_of,
    )
    write_company(out / "company-source", contexts, descriptor)
    contexts, company_manifest = load_company_generation(out / "company-source")
    # Exercise the shipped CLI, not just the underlying view function. The
    # input bytes are the actual generation projection (or explicit negative).
    input_path = out / "published-theme-state.json"
    input_path.write_bytes(canonical_json_bytes(value))
    assert build_sidecar_cli([
        "--company-intelligence-dir", str(out / "company-source"),
        "--membership", str(root / "data/baskets/membership.json"),
        "--crosswalk", str(root / "config/theme_crosswalk.yml"),
        "--theme-state", str(input_path), "--out-dir", str(out / "cte-sidecar"),
        "--as-of", as_of,
    ]) == 0
    marker = json.loads((out / "cte-sidecar/manifest.json").read_text())
    published = out / "cte-sidecar/generations" / marker["generation_id"]
    manifest = json.loads((published / "manifest.json").read_text())
    payload = json.loads((published / "companies/HUBB.json").read_text())
    validate_exposure(payload)
    validate_manifest(manifest)
    assert json.loads((out / "cte-sidecar/manifest.json").read_text()) == manifest
    assert validate_generation(out / "cte-sidecar")["status"] == manifest["status"]
    assert payload["company_intelligence"]["generation_id"] == company_manifest["generation_id"]
    assert payload["company_intelligence"]["context_sha256"] == canonical_json_sha256(contexts["HUBB"])
    assert payload["theme_state"] == manifest["source"]["theme_state"]
    assert payload["authority"] == "context_only"
    assert set(payload["theme_state"]) == {"status", "as_of", "sha256"}
    assert all(set(x) == {"theme_id", "name_en", "name_zh", "basket_id", "mapping_qualifier"}
               for x in payload["exposures"])
    return payload, manifest


@pytest.mark.parametrize("kind", ["INITIAL", "CORRECTION", "ROLLBACK"])
def test_real_publication_retains_legacy_date_and_source_clock_distinction(bridge_world, tmp_path, kind):
    root = bridge_world
    original = _publish(root, "2026-10-04T12:00:00Z")
    selected = original
    use_at = "2026-10-04T13:00:00Z"
    if kind != "INITIAL":
        selected = _publish(root, "2026-10-05T12:00:00Z", correction=True)
        use_at = "2026-10-05T13:00:00Z"
    if kind == "ROLLBACK":
        generation.rollback_generation(root, original["generation_id"],
            activation_at="2026-10-06T12:00:00Z", controlled_verifier=AcceptedFixture())
        selected = original
        use_at = "2026-10-06T13:00:00Z"
    value = _read(root, selected, use_at=use_at)
    projection = value["compatibility"]["projection"]
    payload, manifest = _sidecar(root, projection, tmp_path, as_of=use_at[:10])
    assert value["publication"]["activation_kind"] == kind
    assert value["state_identity"]["effective_at"] == EFFECTIVE
    assert projection["as_of"] == value["state_identity"]["generated_at"][:10]
    assert payload["theme_state"]["as_of"] == projection["as_of"]
    assert payload["theme_state"]["sha256"] == canonical_json_sha256(projection)
    assert payload["generation_id"] != value["publication"]["generation_id"]
    assert payload["exposures"][0]["theme_id"] == "grid"
    assert manifest["coverage"]["active_member_ticker_count"] == 1
    # Successfully validating the v1 sidecar never authorizes successor model use.
    assert reader.legacy_consumer_barrier(root)["available"] is False
    if kind == "ROLLBACK":
        assert value["publication"]["activation_at"][:10] == "2026-10-06"
        assert payload["theme_state"]["as_of"] == "2026-10-04"


def test_rollback_activation_does_not_make_old_sidecar_fresh(bridge_world, tmp_path):
    root = bridge_world
    original = _publish(root, "2026-10-04T12:00:00Z")
    _publish(root, "2026-10-05T12:00:00Z", correction=True)
    generation.rollback_generation(root, original["generation_id"],
        activation_at="2026-10-11T12:00:00Z", controlled_verifier=AcceptedFixture())
    value = _read(root, original, use_at="2026-10-11T13:00:00Z")
    payload, _ = _sidecar(root, value["compatibility"]["projection"], tmp_path, as_of="2026-10-11")
    assert payload["theme_state"]["as_of"] == "2026-10-04"
    assert payload["theme_state"]["status"] == "stale"
    assert payload["status"] == "partial"
    assert "theme_state_stale" in payload["warnings"]


def test_late_assembly_keeps_native_staleness_visible(bridge_world, tmp_path):
    root = bridge_world
    plan = _publish(root, "2026-10-11T12:00:00Z")
    value = _read(root, plan, use_at="2026-10-11T13:00:00Z")
    projection = value["compatibility"]["projection"]
    assert projection["as_of"] == "2026-10-11"
    assert projection["stale_legs"]  # input observations still date to October 3
    payload, _ = _sidecar(root, projection, tmp_path, as_of="2026-10-11")
    assert payload["theme_state"]["status"] == "stale"
    assert payload["status"] == "partial"


def test_rich_state_is_not_silently_relabelled_as_legacy_cte_input(bridge_world, tmp_path):
    root = bridge_world
    plan = _publish(root, "2026-10-04T12:00:00Z")
    value = _read(root, plan, use_at="2026-10-04T13:00:00Z")
    payload, _ = _sidecar(root, value["state"], tmp_path, as_of="2026-10-04")
    assert payload["theme_state"]["status"] == "invalid"
    assert payload["status"] == "partial"
    assert "theme_state_invalid" in payload["warnings"]


@pytest.mark.parametrize("mutation", ["exposure_stage", "state_generation", "actionable"])
def test_actual_published_sidecar_still_rejects_unversioned_gmi_fields(bridge_world, tmp_path, mutation):
    root = bridge_world
    plan = _publish(root, "2026-10-04T12:00:00Z")
    value = _read(root, plan, use_at="2026-10-04T13:00:00Z")
    payload, _ = _sidecar(root, value["compatibility"]["projection"], tmp_path, as_of="2026-10-04")
    changed = copy.deepcopy(payload)
    if mutation == "exposure_stage":
        changed["exposures"][0]["stage"] = "leading"
    elif mutation == "state_generation":
        changed["theme_state"]["generation_id"] = value["publication"]["generation_id"]
    else:
        changed["authority"] = "actionable"
    with pytest.raises(ContractError):
        validate_exposure(changed)
