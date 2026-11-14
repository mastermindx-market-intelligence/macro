"""Real private HTTP transport -> sealed Macro reader -> Rates owner proof.

The source fixture is composed, finalized and read by the existing owners.
Only identity/entitlement backing services and the fixed served root are local
fixtures. No WTI runtime, live provider, browser or deployed receipt is claimed.
"""
from __future__ import annotations

import copy
import errno
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import macro_command as mc, ontology_explorer as api
from engine.market_os.macro_workspaces import contract, rates_curves as owner
from lib import macro_rates_scenario_contract as wire
from test_macro_rates_scenario_contract import publication_fixture


PATH = "/api/ontology/explorer/scenario/v1"
MEMBER = {"Authorization": "Bearer fixture-member"}


def private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert {part.strip().lower() for part in response.headers["vary"].split(",")} >= {"authorization", "cookie"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


def refusal(response, status, code):
    assert response.status_code == status, response.text
    private(response)
    assert response.json() == {"detail": {"schema": api.ERROR_SCHEMA_ID, "code": code}}


@pytest.fixture
def authority(monkeypatch):
    # Exercise the real require_user -> enforce_site_full(always=True) chain.
    # Fixture the external authorities below that chain, not the dependency.
    from app import main, paywall

    seen = []

    def resolve(token):
        seen.append(("identity", token))
        uid = {"fixture-member": "member", "fixture-free": "free"}.get(token)
        return SimpleNamespace(status="ok", uid=uid, record={"id": uid} if uid else None)

    def entitled(uid, feature):
        seen.append(("entitlement", uid, feature))
        return uid == "member", "fixture-tier"

    monkeypatch.setattr(paywall, "_resolve_identity", resolve)
    monkeypatch.setattr(paywall, "_load_config", lambda: {"premium": {"required_feature": "site_full"}})
    monkeypatch.setattr(paywall, "_entitled", entitled)
    monkeypatch.setattr(paywall, "_enabled", lambda: False)
    return SimpleNamespace(main=main, paywall=paywall, seen=seen)


@pytest.fixture
def client(authority):
    application = FastAPI()
    application.include_router(api.router)
    return TestClient(application)


@pytest.fixture
def published(tmp_path, monkeypatch):
    root = tmp_path / "site.served"
    snapshot, baseline, request, metadata = publication_fixture(root / "macrodata")
    monkeypatch.setattr(mc, "_served_root", lambda: root)
    return SimpleNamespace(
        root=root, data=root / "macrodata", snapshot=snapshot, baseline=baseline,
        request=request, metadata=metadata,
        body=root / "macrodata/workspaces/rates_curves/US/latest.json",
        manifest=root / "macrodata/workspaces/manifest.json",
    )


def files(root):
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


def no_source(monkeypatch):
    seen = []

    def unexpected():
        seen.append("source")
        raise AssertionError("invalid request reached source I/O")

    monkeypatch.setattr(mc, "_served_root", unexpected)
    return seen


def test_actual_assembled_route_has_exact_mechanical_receipt_and_no_writes(published, authority, monkeypatch):
    def no_wti(*_args, **_kwargs):
        pytest.fail("Rates reached the held WTI runtime")

    monkeypatch.setattr(api, "evaluate_current_scenario", no_wti)
    before = files(published.root)
    response = TestClient(authority.main.app).post(PATH, json=published.request, headers=MEMBER)
    assert response.status_code == 200, response.text
    private(response)
    result = response.json()
    assert result["schema"] == wire.RESULT_SCHEMA
    assert result["publication"] == published.metadata
    assert result["baseline"]["baseline_id"] == published.baseline.baseline_id
    assert result["baseline"]["us2y"] == {"value": 3.8, "unit": "percent"}
    assert result["baseline"]["us10y"] == {"value": 4.1, "unit": "percent"}
    assert result["baseline"]["curve_2s10s"] == {"value": 30.0, "unit": "bp"}
    assert result["assumed"] == {
        "us2y": {"value": 4.8, "unit": "percent"},
        "us10y": {"value": 4.35, "unit": "percent"},
        "curve_2s10s": {"value": -45.0, "unit": "bp"},
        "spread_change": {"value": -75, "unit": "bp"},
    }
    assert result["authority"]["display_only"] is True
    assert all(value is False for key, value in result["authority"].items() if key != "display_only")
    assert set(result["effects"].values()) == {0}
    assert files(published.root) == before
    assert published.snapshot["scenario_contract"]["execution_available"] is False
    assert published.snapshot["schema"]["version"] == "1.0.0"
    assert authority.seen == [("identity", "fixture-member"), ("entitlement", "member", "site_full")]


@pytest.mark.parametrize("headers,status", [({}, 401), ({"Authorization": "Bearer invalid"}, 401),
                                                ({"Authorization": "Bearer fixture-free"}, 403)])
def test_auth_and_entitlement_precede_even_body_parsing(client, monkeypatch, headers, status):
    seen = no_source(monkeypatch)

    async def no_body(*_args, **_kwargs):
        seen.append("body")
        raise AssertionError("unauthorized request reached body parser")

    monkeypatch.setattr(api, "_private_post_body", no_body)
    response = client.post(PATH, content="not json", headers=headers)
    assert response.status_code == status
    private(response)
    assert seen == []


def test_upstream_identity_outage_retains_existing_502(client, authority, monkeypatch):
    seen = no_source(monkeypatch)
    monkeypatch.setattr(authority.paywall, "_resolve_identity",
                        lambda _token: SimpleNamespace(status="outage", uid=None, record=None))
    response = client.post(PATH, content="invalid", headers=MEMBER)
    assert response.status_code == 502
    private(response)
    assert seen == []


@pytest.mark.parametrize("method", ["GET", "HEAD", "PUT", "PATCH", "DELETE", "OPTIONS"])
def test_method_gate_is_private_and_authenticated(client, monkeypatch, method):
    seen = no_source(monkeypatch)
    anonymous = client.request(method, PATH)
    assert anonymous.status_code == 401
    private(anonymous)
    response = client.request(method, PATH, headers=MEMBER)
    assert response.status_code == 405
    assert response.headers["allow"] == "POST"
    private(response)
    assert seen == []


@pytest.mark.parametrize("kind", ["client_baseline", "wrong_method", "path_in_expectation", "extra_shift",
                                  "boolean", "nonfinite", "off_step", "out_of_range", "zero_digest"])
def test_closed_v2_request_is_rejected_before_source_io(client, published, monkeypatch, kind):
    request = copy.deepcopy(published.request)
    if kind == "client_baseline":
        request["baseline"] = {"us2y_pct": 0, "us10y_pct": 100}
    elif kind == "wrong_method":
        request["method"] = "ontology_scenario.rates_adapter.v1"
    elif kind == "path_in_expectation":
        request["expected_publication"]["path"] = "../../private.json"
    elif kind == "extra_shift":
        request["assumptions"]["curve_2s10s_bp"] = 100
    elif kind == "zero_digest":
        request["expected_publication"]["manifest_sha256"] = "0" * 64
    else:
        request["assumptions"]["us2y_bp"] = {
            "boolean": True, "nonfinite": float("nan"), "off_step": 1, "out_of_range": 305,
        }[kind]
    seen = no_source(monkeypatch)
    response = client.post(PATH, content=json.dumps(request), headers={**MEMBER, "Content-Type": "application/json"})
    refusal(response, 400, "invalid_rates_request")
    assert seen == []


@pytest.mark.parametrize("body", ['{"schema":1,"schema":2}', '{"assumptions":{"us2y_bp":0,"us2y_bp":5}}', "[]", "{"])
def test_duplicate_keys_and_nonobject_json_use_existing_parser(client, monkeypatch, body):
    seen = no_source(monkeypatch)
    refusal(client.post(PATH, content=body, headers={**MEMBER, "Content-Type": "application/json"}),
            400, "invalid_json_object")
    assert seen == []


@pytest.mark.parametrize("suffix,headers,body,status,code", [
    ("?workspace=rates_curves", {"Content-Type": "application/json"}, "{}", 400, "query_parameters_forbidden"),
    ("", {"Content-Type": "text/plain"}, "{}", 415, "json_required"),
    ("", {"Content-Type": "application/json", "Content-Encoding": "gzip"}, "{}", 415, "content_encoding_forbidden"),
    ("", {"Content-Type": "application/json", "Content-Length": "-1"}, "{}", 400, "invalid_length"),
    ("", {"Content-Type": "application/json"}, " " * 4097, 413, "body_too_large"),
])
def test_existing_transport_bounds_precede_source_io(client, monkeypatch, suffix, headers, body, status, code):
    seen = no_source(monkeypatch)
    refusal(client.post(PATH + suffix, content=body, headers={**MEMBER, **headers}), status, code)
    assert seen == []


def test_streamed_body_without_length_is_bounded(client, monkeypatch):
    seen = no_source(monkeypatch)
    refusal(client.post(PATH, content=iter([b" " * 2048, b" " * 2049]),
                        headers={**MEMBER, "Content-Type": "application/json"}), 413, "body_too_large")
    assert seen == []


@pytest.mark.parametrize("assumptions,expected", [
    ({"us2y_bp": 0, "us10y_bp": 0}, (3.8, 4.1, 30.0, 0)),
    ({"us2y_bp": -300, "us10y_bp": 300}, (0.8, 7.1, 630.0, 600)),
])
def test_zero_and_derived_six_hundred_bp_range_are_preserved(client, published, assumptions, expected):
    request = copy.deepcopy(published.request)
    request["assumptions"] = assumptions
    response = client.post(PATH, json=request, headers=MEMBER)
    assert response.status_code == 200, response.text
    result = response.json()
    actual = tuple(result["assumed"][key]["value"] for key in ("us2y", "us10y", "curve_2s10s", "spread_change"))
    assert actual == expected


@pytest.mark.parametrize("key", ["manifest_sha256", "snapshot_content_sha256"])
def test_qualified_but_different_publication_is_409(client, published, key):
    request = copy.deepcopy(published.request)
    request["expected_publication"][key] = "f" * 64
    refusal(client.post(PATH, json=request, headers=MEMBER), 409, "source_changed")


def test_republication_requires_explicit_new_expectation(client, published):
    first = client.post(PATH, json=published.request, headers=MEMBER).json()
    _, _, next_request, metadata = publication_fixture(published.data, built_at="2026-09-04T13:00:00Z")
    assert metadata["artifact"]["sha256"] == published.metadata["artifact"]["sha256"]
    refusal(client.post(PATH, json=published.request, headers=MEMBER), 409, "source_changed")
    response = client.post(PATH, json=next_request, headers=MEMBER)
    assert response.status_code == 200, response.text
    assert response.json()["calculation_id"] == first["calculation_id"]
    assert response.json()["publication"] == metadata


@pytest.mark.parametrize("kind", ["body_missing", "manifest_missing", "body_digest", "no_common_date"])
def test_unavailable_or_unqualified_baseline_has_no_partial_result(client, published, kind):
    request = copy.deepcopy(published.request)
    if kind == "body_missing":
        published.body.unlink()
    elif kind == "manifest_missing":
        published.manifest.unlink()
    elif kind == "body_digest":
        before = published.body.read_bytes()
        assert b"3.8" in before
        published.body.write_bytes(before.replace(b"3.8", b"3.9", 1))
    else:
        snapshot = contract.finalize(owner.compose({
            owner.SERIES_US2Y: [("2026-09-01", 3.8)],
            owner.SERIES_US10Y: [("2026-09-02", 4.1)],
        }, built_at="2026-09-04T12:00:00Z", code_version="test-fixture"))
        contract.validate(snapshot)
        raw = (json.dumps(snapshot, sort_keys=True) + "\n").encode()
        published.body.write_bytes(raw)
        manifest = json.loads(published.manifest.read_bytes())
        manifest["workspaces"]["rates_curves/US"].update(
            bytes=len(raw), content_sha256=snapshot["generation"]["content_sha256"],
            generation_id=snapshot["generation"]["generation_id"])
        published.manifest.write_text(json.dumps(manifest, sort_keys=True))
        request["expected_publication"] = {
            "manifest_sha256": sha256(published.manifest.read_bytes()).hexdigest(),
            "snapshot_content_sha256": snapshot["generation"]["content_sha256"],
        }
    refusal(client.post(PATH, json=request, headers=MEMBER), 503, "source_unavailable")


@pytest.mark.parametrize("stage", ["calculation", "serialization", "encoding"])
@pytest.mark.parametrize("changed", ["body", "manifest"])
def test_change_through_final_response_encoding_never_returns_result(client, published, monkeypatch, stage, changed):
    target, name = {
        "calculation": (owner, "evaluate_rates_scenario"),
        "serialization": (wire, "serialize_rates_result"),
        "encoding": (api, "_bounded_post_response"),
    }[stage]
    original = getattr(target, name)
    path = published.body if changed == "body" else published.manifest
    before = path.read_bytes()
    mutation = before[:-1] + (b" " if before[-1:] == b"\n" else b"\n") if changed == "body" else before + b" "

    def race(*args, **kwargs):
        result = original(*args, **kwargs)
        path.write_bytes(mutation)
        return result

    monkeypatch.setattr(target, name, race)
    refusal(client.post(PATH, json=published.request, headers=MEMBER), 409, "source_changed")
    if changed == "body":
        assert len(mutation) == len(before)
        assert json.loads(mutation) == json.loads(before)
        assert sha256(published.manifest.read_bytes()).hexdigest() == published.metadata["manifest_sha256"]


@pytest.mark.parametrize("path_name", ["body", "manifest"])
def test_unreadable_exit_fence_is_503_not_evidence_of_change(client, published, monkeypatch, path_name):
    original = mc._bounded_bytes
    count = 0

    def read(path, *args, **kwargs):
        nonlocal count
        if path == getattr(published, path_name):
            count += 1
            if count == 2:
                raise OSError(errno.EIO, "PRIVATE_SOURCE_PATH")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(mc, "_bounded_bytes", read)
    response = client.post(PATH, json=published.request, headers=MEMBER)
    refusal(response, 503, "source_unavailable")
    assert "PRIVATE_SOURCE_PATH" not in response.text
    assert count == 2


def test_read_budget_is_preserved_at_selected_body_recheck(client, published, monkeypatch):
    monkeypatch.setattr(mc, "TOTAL_MAX_BYTES",
                        len(published.manifest.read_bytes()) + mc.BODY_MAX_BYTES + 1)
    refusal(client.post(PATH, json=published.request, headers=MEMBER), 503, "source_unavailable")


def test_stale_expectation_does_not_mask_invalid_server_publication(client, published):
    manifest = json.loads(published.manifest.read_bytes())
    # Accepted by the existing reader, rejected by the stronger Rates receipt.
    manifest["generated_at"] = "2026-09-04 12:00:00+00:00"
    published.manifest.write_text(json.dumps(manifest, sort_keys=True))
    refusal(client.post(PATH, json=published.request, headers=MEMBER), 500, "internal_error")


def test_internal_contract_failure_is_not_replaced_by_later_source_change(client, published, monkeypatch):
    def invalid(*_args, **_kwargs):
        published.manifest.write_bytes(published.manifest.read_bytes() + b" ")
        raise wire.RatesScenarioContractError("invalid_rates_calculation")

    monkeypatch.setattr(wire, "serialize_rates_result", invalid)
    refusal(client.post(PATH, json=published.request, headers=MEMBER), 500, "internal_error")


def test_existing_response_size_refusal_keeps_503(client, published, monkeypatch):
    monkeypatch.setattr(wire, "serialize_rates_result", lambda *_args, **_kwargs: {"oversized": "x" * 262144})
    refusal(client.post(PATH, json=published.request, headers=MEMBER), 503, "response_too_large")


def test_v1_invalid_request_keeps_existing_path_without_wti_execution(client, monkeypatch):
    seen = no_source(monkeypatch)
    refusal(client.post(PATH, json={"schema": "ontology_scenario_request.v1"}, headers=MEMBER),
            400, "invalid_scenario_request")
    assert seen == []
