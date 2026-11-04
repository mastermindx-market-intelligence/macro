"""Transport contract tests for the authenticated policy preview route.

The FastAPI app is isolated and the only stubs are the auth owner and the
publication helper. No app.main import, no provider, no network and no
published-data read happens here; these tests say nothing about the publisher's
own reads or the comparator's arithmetic.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi", reason="policy preview API tests need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import lib  # noqa: E402
from app import macro_command, macro_policy_preview  # noqa: E402

GENERATION = "im-workspace-generation:9e1a5667-47f3-4a69-a784-b971e3ba74ba"
FINGERPRINT = "a" * 64
TOKEN = "Bearer synthetic-qualified"
ACCESS_TOKEN = "synthetic-access-token"
PRIVATE = {"cache-control": "private, no-store", "x-robots-tag": "noindex, noarchive"}
ENVELOPE_KEYS = {
    "schema",
    "state",
    "source_generation",
    "artifact_sha256",
    "mapping_identity",
    "qualification_identity",
    "result",
}


def _settings(**overrides):
    settings = {
        "economy_a": "JP",
        "economy_b": "US",
        "lens": "nominal_policy_point_gap",
        "definition": "absolute_gap_change_bp",
        "method_version": "nominal-point/v1",
        "period": {"mode": "fixed_dates", "start": "2026-08-31", "end": "2026-09-30"},
        "instrument_a_ref": "JP-policy-point",
        "instrument_b_ref": "US-policy-point",
        "revision_policy": "latest_vintage",
    }
    settings.update(overrides)
    return settings


def _payload(**overrides):
    payload = {
        "generation": GENERATION,
        "fingerprint": FINGERPRINT,
        "settings": _settings(),
    }
    payload.update(overrides)
    return payload


def _typed_result(**overrides):
    result = {
        "schema": "intl.policy_preview.v1",
        "state": "qualified",
        "source_generation": GENERATION,
        "artifact_sha256": FINGERPRINT,
        "mapping_identity": "mapping/synthetic",
        "qualification_identity": "qualification/synthetic",
        "result": {
            "state": "qualified",
            "signed_start_bp": -300,
            "signed_end_bp": -250,
            "signed_change_bp": 50,
            "absolute_change_bp": -50,
            "direction": "narrowed",
            "crosses_zero": False,
        },
    }
    result.update(overrides)
    return result


@pytest.fixture
def preview(monkeypatch, tmp_path):
    """Isolated app with the auth owner and the source helper stubbed."""
    calls: list[dict] = []
    auths: list[str | None] = []
    order: list[str] = []

    def fake_require_user(authorization=None):
        auths.append(authorization)
        order.append("auth")
        if authorization != TOKEN:
            raise HTTPException(401, "missing bearer token")
        return {"id": "synthetic-user", "email": "synthetic@example.invalid",
                "_access_token": ACCESS_TOKEN}

    def fake_helper(**kwargs):
        calls.append(kwargs)
        order.append("helper")
        return _typed_result()

    module = types.ModuleType("lib.intl_policy_publication")
    module.preview_published_policy_points = fake_helper
    monkeypatch.setitem(sys.modules, "lib.intl_policy_publication", module)
    # Keep the parent package attribute consistent with the substituted module.
    monkeypatch.setattr(lib, "intl_policy_publication", module, raising=False)
    monkeypatch.setattr(macro_command, "require_user", fake_require_user)
    monkeypatch.setattr(macro_policy_preview, "_feed_base", lambda: "https://feeds.example.invalid")

    app = FastAPI()
    app.include_router(macro_policy_preview.router)
    return SimpleNamespace(client=TestClient(app), calls=calls, auths=auths, order=order,
                           root="https://feeds.example.invalid", monkeypatch=monkeypatch)


def _post(preview, payload=None, *, raw=None, headers=None, params=None):
    body = raw if raw is not None else json.dumps(payload if payload is not None else _payload())
    request_headers = {"Authorization": TOKEN}
    if headers is not None:
        request_headers.update(headers)
    return preview.client.post("/api/macro/policy-preview", content=body,
                               headers=request_headers, params=params)


def _exact_body(size: int) -> bytes:
    """A valid request body of exactly `size` bytes."""
    return _padded_body(size, "x", 1)


def _multibyte_body(size: int) -> bytes:
    """A valid request body of exactly `size` UTF-8 bytes with fewer characters."""
    return _padded_body(size, "é", 2)


def _padded_body(size: int, filler: str, width: int) -> bytes:
    payload = _payload(settings=_settings(period={"mode": "owner_horizon", "key": "x"}))
    fields = [
        (payload["settings"], "method_version"),
        (payload["settings"], "instrument_a_ref"),
        (payload["settings"], "instrument_b_ref"),
        (payload["settings"]["period"], "key"),
    ]
    for container, key in fields:
        container[key] = filler
    # Every padded field is plain text, so the encoded body grows width bytes per character.
    need = size - len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    for container, key in fields:
        if need <= 0:
            break
        grow = min(4096 - 1, need // width)
        container[key] = filler * (1 + grow)
        need -= grow * width
    if need:
        container, key = fields[-1]
        container[key] = container[key] + "x"
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    assert len(raw) == size
    return raw


def test_qualified_preview_publishes_the_exact_envelope(preview):
    response = _post(preview)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == ENVELOPE_KEYS
    assert body["schema"] == "intl.policy_preview.v1"
    assert body["state"] == "qualified"
    assert body["source_generation"] == GENERATION
    assert body["artifact_sha256"] == FINGERPRINT
    assert body["mapping_identity"] == "mapping/synthetic"
    assert body["qualification_identity"] == "qualification/synthetic"
    assert body["result"]["absolute_change_bp"] == -50
    assert body["result"]["direction"] == "narrowed"
    for header, value in PRIVATE.items():
        assert response.headers[header] == value


def test_helper_receives_the_fixed_root_requested_generation_and_settings(preview):
    _post(preview)
    assert preview.auths == [TOKEN]
    assert preview.order == ["auth", "helper"]
    assert len(preview.calls) == 1
    call = preview.calls[0]
    assert set(call) == {"feed_base", "source_generation", "artifact_sha256",
                         "settings", "evaluated_at"}
    assert call["feed_base"] == preview.root
    assert call["source_generation"] == GENERATION
    assert call["artifact_sha256"] == FINGERPRINT
    assert call["settings"] == _settings()
    assert call["evaluated_at"].endswith("+00:00")
    assert "T" in call["evaluated_at"]


def test_revision_policy_and_owner_horizon_are_forwarded_unchanged(preview):
    settings = _settings(revision_policy="original_known",
                         period={"mode": "owner_horizon", "key": "1m"})
    response = _post(preview, _payload(settings=settings))
    assert response.status_code == 200
    forwarded = preview.calls[0]["settings"]
    assert forwarded == settings
    assert forwarded["revision_policy"] == "original_known"
    assert "vintage_policy" not in forwarded
    assert forwarded["period"] == {"mode": "owner_horizon", "key": "1m"}


def test_latest_vintage_is_forwarded_unchanged(preview):
    response = _post(preview, _payload(settings=_settings(revision_policy="latest_vintage")))
    assert response.status_code == 200
    assert preview.calls[0]["settings"]["revision_policy"] == "latest_vintage"
    assert preview.calls[0]["settings"]["period"] == {
        "mode": "fixed_dates", "start": "2026-08-31", "end": "2026-09-30"}


def test_unauthenticated_caller_is_refused_before_body_and_source(preview):
    consumed = []

    def body():
        consumed.append(True)
        yield b"{" * 100

    response = preview.client.post("/api/macro/policy-preview", content=body(),
                                    headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401
    assert consumed == []
    assert preview.calls == []
    for header, value in PRIVATE.items():
        assert response.headers[header] == value


def test_unauthenticated_caller_with_an_oversized_body_is_refused_not_truncated(preview):
    response = preview.client.post("/api/macro/policy-preview", content=b"x" * 20000,
                                    headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401
    assert preview.calls == []


def test_missing_authorization_is_refused(preview):
    response = preview.client.post("/api/macro/policy-preview", content=b"{}")
    assert response.status_code == 401
    assert preview.calls == []


def test_auth_upstream_failure_keeps_the_canonical_502(preview, monkeypatch):
    def fail(authorization=None):
        raise HTTPException(502, "auth check failed, please try again")

    monkeypatch.setattr(macro_command, "require_user", fail)
    response = _post(preview)
    assert response.status_code == 502
    assert response.json()["detail"] == "auth check failed, please try again"
    for header, value in PRIVATE.items():
        assert response.headers[header] == value


def test_body_at_the_cap_is_accepted_and_one_byte_over_is_refused(preview):
    accepted = _post(preview, raw=_exact_body(16384))
    assert accepted.status_code == 200
    refused = _post(preview, raw=_exact_body(16385))
    assert refused.status_code == 413
    assert len(preview.calls) == 1


def test_the_cap_counts_utf8_bytes_not_characters(preview):
    accepted = _post(preview, raw=_multibyte_body(16384))
    assert accepted.status_code == 200
    refused = _post(preview, raw=_multibyte_body(16385))
    assert refused.status_code == 413
    assert len(preview.calls) == 1


def test_chunked_body_is_capped_on_the_bytes_that_arrive(preview):
    response = _post(preview, raw=iter([b"x" * 10000, b"y" * 10000]))
    assert response.status_code == 413
    assert preview.calls == []


def test_understated_content_length_cannot_smuggle_an_oversized_body(preview):
    response = _post(preview, raw=b"x" * 20000, headers={"Content-Length": "10"})
    assert response.status_code == 413
    assert preview.calls == []


def test_query_parameters_cannot_select_the_source(preview):
    response = _post(preview, params={"served_root": "/etc", "generation": "other"})
    assert response.status_code == 200
    assert preview.calls[0]["feed_base"] == preview.root
    assert preview.calls[0]["source_generation"] == GENERATION


@pytest.mark.parametrize("raw", [
    b"",
    b"not json",
    b"[]",
    b'"text"',
    b"null",
    b"123",
    b"{",
    b"\xff\xfe",
    b'{"generation": "%s"}' % GENERATION.encode(),
    b'{"generation": "%s", "fingerprint": "%s"}' % (GENERATION.encode(), FINGERPRINT.encode()),
    b'{"settings": %s}' % json.dumps(_settings()).encode(),
])
def test_malformed_bodies_are_refused(preview, raw):
    response = _post(preview, raw=raw)
    assert response.status_code == 400
    assert preview.calls == []
    for header, value in PRIVATE.items():
        assert response.headers[header] == value


def test_the_request_is_never_echoed(preview):
    payload = _payload()
    payload["settings"]["method_version"] = "PRIVATE-SECRET"
    response = _post(preview, payload)
    assert response.status_code == 200
    assert "PRIVATE-SECRET" not in response.text


def test_a_refused_body_is_never_echoed(preview):
    payload = _payload()
    payload["settings"]["method_version"] = " PRIVATE-SECRET"
    response = _post(preview, payload)
    assert response.status_code == 400
    assert "PRIVATE-SECRET" not in response.text


@pytest.mark.parametrize("body", [
    {"generation": GENERATION.upper()},
    {"generation": "im-workspace-generation:" + GENERATION.split(":")[1].upper()},
    {"generation": "im-workspace-generation:not-a-uuid"},
    {"generation": "im-workspace-generation:9e1a5667-47f3-1a69-a784-b971e3ba74ba"},
    {"generation": "im-workspace-generation:9e1a5667-47f3-4a69-c784-b971e3ba74ba"},
    {"generation": "generation-1"},
    {"generation": 1},
    {"fingerprint": "A" * 64},
    {"fingerprint": "a" * 63},
    {"fingerprint": "g" * 64},
    {"fingerprint": None},
])
def test_wrong_generation_or_fingerprint_is_refused(preview, body):
    response = _post(preview, _payload(**body))
    assert response.status_code == 400
    assert preview.calls == []


@pytest.mark.parametrize("settings", [
    {"economy_a": "us"},
    {"economy_a": "USA"},
    {"economy_a": "J"},
    {"economy_b": "jp"},
    {"economy_a": "US", "economy_b": "US"},
    {"lens": "real_rate"},
    {"definition": "signed"},
    {"revision_policy": "latest"},
    {"revision_policy": "LATEST_VINTAGE"},
    {"revision_policy": None},
    {"method_version": ""},
    {"method_version": " v1"},
    {"method_version": "x" * 4097},
    {"method_version": {"nested": "object"}},
    {"method_version": ["list"]},
    {"instrument_a_ref": ""},
    {"instrument_b_ref": " "},
    {"period": {"mode": "fixed_dates", "start": "2026-08-31"}},
    {"period": {"mode": "fixed_dates", "start": "2026-08-31", "end": "2026-09-30", "x": "1"}},
    {"period": {"mode": "owner_horizon"}},
    {"period": {"mode": "owner_horizon", "key": ""}},
    {"period": {"mode": "owner_horizon", "key": "1m", "extra": "1"}},
    {"period": {"mode": "unknown", "key": "1m"}},
    {"period": "2026-08-31"},
])
def test_wrong_or_extra_settings_are_refused(preview, settings):
    response = _post(preview, _payload(settings=_settings(**settings)))
    assert response.status_code == 400
    assert preview.calls == []


def test_extra_top_level_keys_are_refused(preview):
    payload = _payload()
    payload["user_id"] = "synthetic-user"
    assert _post(preview, payload).status_code == 400
    payload = _payload()
    payload["saved_id"] = "saved-1"
    assert _post(preview, payload).status_code == 400


def test_client_supplied_numbers_receipts_and_paths_are_refused(preview):
    payload = _payload()
    payload["settings"]["values"] = [1, 2, 3]
    assert _post(preview, payload).status_code == 400
    payload = _payload()
    payload["settings"]["receipt_id"] = "receipt-1"
    assert _post(preview, payload).status_code == 400
    payload = _payload()
    payload["settings"]["served_root"] = "/etc"
    assert _post(preview, payload).status_code == 400


def test_duplicate_keys_are_refused(preview):
    raw = ('{"generation": "%s", "generation": "%s", "fingerprint": "%s", "settings": %s}'
           % (GENERATION, GENERATION, FINGERPRINT, json.dumps(_settings())))
    response = _post(preview, raw=raw.encode("utf-8"))
    assert response.status_code == 400
    assert preview.calls == []


@pytest.mark.parametrize("raw", [
    b'{"generation": NaN, "fingerprint": "%s", "settings": %s}' % (FINGERPRINT.encode(), json.dumps(_settings()).encode()),
    b'{"generation": "%s", "fingerprint": Infinity, "settings": %s}' % (GENERATION.encode(), json.dumps(_settings()).encode()),
    b'{"generation": "%s", "fingerprint": 1e999, "settings": %s}' % (GENERATION.encode(), json.dumps(_settings()).encode()),
])
def test_nonfinite_numbers_are_refused(preview, raw):
    response = _post(preview, raw=raw)
    assert response.status_code == 400
    assert preview.calls == []


@pytest.mark.parametrize("period", [
    {"mode": "fixed_dates", "start": "2026-02-29", "end": "2026-09-30"},
    {"mode": "fixed_dates", "start": "2024-02-30", "end": "2026-09-30"},
    {"mode": "fixed_dates", "start": "2026-13-01", "end": "2026-09-30"},
    {"mode": "fixed_dates", "start": "2026-8-31", "end": "2026-09-30"},
    {"mode": "fixed_dates", "start": "2026-08-31T00:00:00Z", "end": "2026-09-30"},
    {"mode": "fixed_dates", "start": "2026-09-30", "end": "2026-08-31"},
    {"mode": "fixed_dates", "start": 20260831, "end": 20260930},
])
def test_invalid_dates_are_refused(preview, period):
    response = _post(preview, _payload(settings=_settings(period=period)))
    assert response.status_code == 400
    assert preview.calls == []


def test_equal_dates_are_accepted(preview):
    period = {"mode": "fixed_dates", "start": "2024-02-29", "end": "2024-02-29"}
    response = _post(preview, _payload(settings=_settings(period=period)))
    assert response.status_code == 200
    assert preview.calls[0]["settings"]["period"] == period


def test_unavailable_helper_state_is_typed_and_preserved(preview, monkeypatch):
    module = sys.modules["lib.intl_policy_publication"]

    def unavailable(**kwargs):
        return _typed_result(state="unavailable", mapping_identity=None,
                             qualification_identity=None,
                             result={"state": "unavailable",
                                     "reasons": ["original_known_unavailable"],
                                     "missing_refs": []})

    monkeypatch.setattr(module, "preview_published_policy_points", unavailable)
    response = _post(preview)
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "unavailable"
    assert body["mapping_identity"] is None
    assert body["qualification_identity"] is None
    assert body["result"] == {"state": "unavailable",
                               "reasons": ["original_known_unavailable"],
                               "missing_refs": []}


def test_helper_failure_returns_the_fixed_error_without_detail(preview, monkeypatch):
    module = sys.modules["lib.intl_policy_publication"]

    def explode(**kwargs):
        raise RuntimeError("PRIVATE-FAILURE-DETAIL")

    monkeypatch.setattr(module, "preview_published_policy_points", explode)
    response = _post(preview)
    assert response.status_code == 503
    assert response.json() == {"error": "policy preview unavailable"}
    assert "PRIVATE-FAILURE-DETAIL" not in response.text
    for header, value in PRIVATE.items():
        assert response.headers[header] == value


def test_a_helper_http_error_does_not_escape_as_a_client_answer(preview, monkeypatch):
    module = sys.modules["lib.intl_policy_publication"]

    def refuse(**kwargs):
        raise HTTPException(404, "not published")

    monkeypatch.setattr(module, "preview_published_policy_points", refuse)
    response = _post(preview)
    assert response.status_code == 503
    assert response.json() == {"error": "policy preview unavailable"}


def test_an_absent_publication_owner_is_unavailable(preview, monkeypatch):
    # A None entry makes the lazy import raise, whatever is on disk.
    monkeypatch.setitem(sys.modules, "lib.intl_policy_publication", None)
    response = _post(preview)
    assert response.status_code == 503
    assert response.json() == {"error": "policy preview unavailable"}


@pytest.mark.parametrize("overrides", [
    {"source_generation": "im-workspace-generation:11111111-1111-4111-8111-111111111111"},
    {"artifact_sha256": "b" * 64},
    {"state": "partial"},
    {"mapping_identity": 7},
    {"result": "not-a-dict"},
])
def test_helper_identity_mismatch_is_refused(preview, monkeypatch, overrides):
    module = sys.modules["lib.intl_policy_publication"]
    monkeypatch.setattr(module, "preview_published_policy_points",
                        lambda **kwargs: _typed_result(**overrides))
    response = _post(preview)
    assert response.status_code == 503
    assert response.json() == {"error": "policy preview unavailable"}


def test_helper_non_json_numbers_are_refused(preview, monkeypatch):
    module = sys.modules["lib.intl_policy_publication"]
    monkeypatch.setattr(module, "preview_published_policy_points",
                        lambda **kwargs: _typed_result(
                            result={"state": "qualified", "signed_start_bp": float("nan")}))
    response = _post(preview)
    assert response.status_code == 503
    assert response.json() == {"error": "policy preview unavailable"}


def test_auth_token_is_never_disclosed(preview):
    response = _post(preview)
    assert response.status_code == 200
    assert ACCESS_TOKEN not in response.text
    assert "synthetic-user" not in response.text
    assert ACCESS_TOKEN not in repr(preview.calls[0])
    assert "_access_token" not in repr(preview.calls[0])


def _app_main_imports(source):
    import ast
    return [node for node in ast.walk(ast.parse(source)) if
            (isinstance(node, ast.Import) and any(
                alias.name == "app.main" or alias.name.startswith("app.main.")
                for alias in node.names)) or
            (isinstance(node, ast.ImportFrom) and (
                node.module == "app.main" or
                (node.module == "app" and any(alias.name == "main" for alias in node.names)) or
                (node.level == 1 and (node.module == "main" or
                    (node.module is None and any(alias.name == "main" for alias in node.names))))))]


def test_the_source_helper_is_imported_lazily_inside_the_route():
    import ast
    source = Path(macro_policy_preview.__file__).read_text()
    tree = ast.parse(source)
    route = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                 and node.name == "macro_policy_preview")
    imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
               and node.module == "lib.intl_policy_publication"]
    assert imports
    assert all(node in set(ast.walk(route)) for node in imports)
    assert not _app_main_imports(source)


@pytest.mark.parametrize("statement", ["import app.main", "from app.main import require_user",
    "from app import main", "from .main import require_user", "from . import main"])
def test_import_guard_rejects_real_application_dependency(statement):
    assert _app_main_imports(statement)


def test_import_guard_ignores_explanatory_comments():
    assert not _app_main_imports("# Prefer the narrow interface over an app.main cycle.\npass\n")


@pytest.mark.parametrize("case", ["schema_wrong", "schema_missing", "extra_key",
    "mapping_missing", "qualification_missing", "mapping_null",
    "qualification_blank", "result_state_mismatch"])
def test_parent_closed_helper_envelope(preview, monkeypatch, case):
    output = _typed_result()
    if case == "schema_wrong": output["schema"] = "another.product.v1"
    elif case == "schema_missing": del output["schema"]
    elif case == "extra_key": output["private_debug"] = "must-not-normalize"
    elif case == "mapping_missing": del output["mapping_identity"]
    elif case == "qualification_missing": del output["qualification_identity"]
    elif case == "mapping_null": output["mapping_identity"] = None
    elif case == "qualification_blank": output["qualification_identity"] = " "
    elif case == "result_state_mismatch": output["result"]["state"] = "unavailable"
    module = sys.modules["lib.intl_policy_publication"]
    monkeypatch.setattr(module, "preview_published_policy_points", lambda **kwargs: output)
    response = _post(preview)
    assert response.status_code == 503
    assert response.json() == {"error": "policy preview unavailable"}
    assert "must-not-normalize" not in response.text


def test_parent_auth_response_headers_are_preserved(preview, monkeypatch):
    def refuse(authorization=None):
        raise HTTPException(401, "invalid token", headers={
            "WWW-Authenticate": "Bearer", "Cache-Control": "public"})
    monkeypatch.setattr(macro_command, "require_user", refuse)
    response = _post(preview)
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"
    assert response.headers["cache-control"] == "private, no-store"
    assert preview.calls == []


def test_real_publication_helper_is_mounted_after_auth_and_returns_owner_computation(tmp_path,monkeypatch):
    """Real helper+engine, synthetic published bytes/auth and transport doubles."""
    from tests.test_intl_policy_feed_preview import prepared
    _,_,descriptor,_,args,reader,_=prepared(tmp_path,monkeypatch)
    monkeypatch.setattr(macro_policy_preview,'_feed_base',lambda:args['feed_base'])
    def auth(authorization):
        if authorization!='Bearer internal-test':
            raise HTTPException(401,'missing bearer token',headers={'WWW-Authenticate':'Bearer'})
        return {'id':'internal-test','_access_token':'never-return-this'}
    monkeypatch.setattr(macro_command,'require_user',auth)
    app=FastAPI();app.include_router(macro_policy_preview.router);client=TestClient(app)
    body={'generation':args['source_generation'],'fingerprint':args['artifact_sha256'],'settings':args['settings']}
    denied=client.post('/api/macro/policy-preview',json=body)
    assert denied.status_code==401 and reader.reads==[]
    assert denied.headers['www-authenticate']=='Bearer'
    response=client.post('/api/macro/policy-preview',json=body,headers={'Authorization':'Bearer internal-test'})
    assert response.status_code==200,response.text
    assert response.headers['cache-control']=='private, no-store'
    result=response.json();assert result['state']=='qualified'
    assert result['result']['absolute_change_bp']==-25
    assert result['artifact_sha256']==descriptor['artifact_sha256']
    assert 'never-return-this' not in response.text


def test_main_source_mounts_the_policy_route_without_a_second_service():
    import ast
    tree=ast.parse((Path(__file__).parents[1]/'app/main.py').read_text())
    assert any(isinstance(n,ast.ImportFrom) and n.module=='app.macro_policy_preview'for n in ast.walk(tree))
    assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)and n.func.attr=='include_router'
        and any(isinstance(a,ast.Name)and a.id=='macro_policy_preview_router'for a in n.args)for n in ast.walk(tree))


@pytest.mark.parametrize('refs',[
    {'instrument_a_ref':None},{'instrument_b_ref':None},
    {'instrument_a_ref':None,'instrument_b_ref':None},
])
def test_nullable_native_instrument_refs_are_forwarded_without_invention(preview,refs):
    response=_post(preview,_payload(settings=_settings(**refs)))
    assert response.status_code==200
    for key,value in refs.items():assert preview.calls[0]['settings'][key] is value


@pytest.mark.parametrize('refs',[
    {'instrument_a_ref':True},{'instrument_b_ref':17},
    {'instrument_a_ref':[]},{'instrument_b_ref':{}},
    {'instrument_a_ref':''},{'instrument_b_ref':' '},
])
def test_nullable_refs_still_reject_nontext_and_blank_values(preview,refs):
    response=_post(preview,_payload(settings=_settings(**refs)))
    assert response.status_code==400 and preview.calls==[]


def test_fixed_feed_origin_uses_existing_deployment_env_before_config(monkeypatch):
    from lib import config
    monkeypatch.setenv('R2_PUBLIC_BASE','https://configured.example.invalid/prefix/')
    monkeypatch.setattr(config,'load',lambda:(_ for _ in ()).throw(AssertionError('env takes precedence')))
    assert macro_policy_preview._feed_base()=='https://configured.example.invalid/prefix'


def test_fixed_feed_origin_uses_existing_config_without_request_input(monkeypatch):
    from lib import config
    monkeypatch.delenv('R2_PUBLIC_BASE',raising=False)
    monkeypatch.setattr(config,'load',lambda:{'r2_data_plane':{'public_base':'https://configured.example.invalid/'}})
    assert macro_policy_preview._feed_base()=='https://configured.example.invalid'


def test_missing_fixed_feed_origin_stays_unavailable(monkeypatch):
    from lib import config
    monkeypatch.delenv('R2_PUBLIC_BASE',raising=False)
    monkeypatch.setattr(config,'load',lambda:{})
    assert macro_policy_preview._feed_base()==''
