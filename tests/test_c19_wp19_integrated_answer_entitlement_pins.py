"""C19 WP19 — offline pins for the integrated-answer path proof.

The v0 composer suite (``tests/test_integrated_answer_v0.py``) always overrides
``require_site_full_user``, so the REAL entitlement wrapper in ``app/forensics.py``
and its ``_private_error`` boundary were never exercised on a denial.  This file
drives the real wrapper with stubbed ``app.main`` / ``app.paywall`` modules installed
into ``sys.modules`` (the wrapper resolves them through function-local imports), and
pins the observable contract: the response SHA header, the private headers on 200,
401 and 403, and the dependency ordering.

Test-only.  No network, no wall clock, no randomness, and ``app.main`` /
``app.paywall`` are never imported for real here.
"""
from __future__ import annotations

import hashlib
import json
import sys
import types

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.integrated_answer as integrated_answer
from app.forensics import _PRIVATE_HEADERS
from app.integrated_answer import router as integrated_answer_router
from engine.company_intelligence.contracts import ContractError, safe_ticker
from tests.test_integrated_answer_v0 import _client, _page, _patch_all_seams

_PATH = "/api/integrated-answer/v1/AAPL"


def _real_client(monkeypatch, *, flag_on: bool = True) -> TestClient:
    """A bare router app with NO dependency overrides — the real wrapper must run.

    The env flag is set only through monkeypatch, the existing v0 idiom.
    """
    monkeypatch.delenv("MACRO_INTEGRATED_ANSWER_ENABLED", raising=False)
    if flag_on:
        monkeypatch.setenv("MACRO_INTEGRATED_ANSWER_ENABLED", "1")
    app = FastAPI()
    app.include_router(integrated_answer_router)
    assert app.dependency_overrides == {}
    return TestClient(app)


def _stub_auth(monkeypatch, *, require_user, enforce_site_full) -> None:
    """Replace ``app.main`` / ``app.paywall`` with recording stub modules.

    ``require_site_full_user`` resolves both names through function-local imports,
    so ``sys.modules`` entries are what the real wrapper actually calls.
    """
    main_module = types.ModuleType("app.main")
    main_module.require_user = require_user
    paywall_module = types.ModuleType("app.paywall")
    paywall_module.enforce_site_full = enforce_site_full
    monkeypatch.setitem(sys.modules, "app.main", main_module)
    monkeypatch.setitem(sys.modules, "app.paywall", paywall_module)


def _forbid_compose(monkeypatch) -> None:
    """Any attempt to build a page during a denial test is a hard failure.

    The route calls ``_compose_page_with_receipts`` directly, so patching only
    ``_compose_page`` would never fire; both seams are forbidden.
    """

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("composed")

    monkeypatch.setattr(integrated_answer, "_compose_page", _forbidden)
    monkeypatch.setattr(integrated_answer, "_compose_page_with_receipts", _forbidden)


def _allowing_stubs(monkeypatch):
    """Install stubs that authenticate and entitle, recording every call."""
    auth_calls: list = []
    entitlement_calls: list = []

    def _require_user(authorization=None, *_args, **_kwargs) -> dict:
        auth_calls.append(authorization)
        return {"id": "u-wp19"}

    def _enforce_site_full(user, *, always=False) -> dict:
        entitlement_calls.append((user, always))
        return user

    _stub_auth(monkeypatch, require_user=_require_user, enforce_site_full=_enforce_site_full)
    return auth_calls, entitlement_calls


def test_200_sha256_header_matches_body(monkeypatch) -> None:
    _patch_all_seams(monkeypatch)
    client = _client(monkeypatch)
    response = client.get(_PATH)
    assert response.status_code == 200
    assert response.headers["X-Integrated-Answer-SHA256"] == hashlib.sha256(response.content).hexdigest()
    canonical = json.dumps(
        json.loads(response.content),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    assert response.content == canonical


def test_200_carries_every_private_header(monkeypatch) -> None:
    _patch_all_seams(monkeypatch)
    client = _client(monkeypatch)
    response = client.get(_PATH)
    assert response.status_code == 200
    for name, value in _PRIVATE_HEADERS.items():
        assert response.headers[name] == value


def test_real_dependency_401_is_private_and_skips_entitlement(monkeypatch) -> None:
    client = _real_client(monkeypatch)
    _forbid_compose(monkeypatch)
    auth_calls: list = []
    entitlement_calls: list = []

    def _require_user(authorization=None, *_args, **_kwargs):
        auth_calls.append(authorization)
        raise HTTPException(
            status_code=401,
            detail="missing bearer token",
            headers={
                "WWW-Authenticate": "Bearer",
                "Cache-Control": "public, max-age=60",
                "vary": "Cookie",
            },
        )

    def _enforce_site_full(user, *, always=False) -> dict:
        entitlement_calls.append((user, always))
        return user

    _stub_auth(monkeypatch, require_user=_require_user, enforce_site_full=_enforce_site_full)

    response = client.get(_PATH, headers={"Authorization": "Bearer wp19-token"})
    assert response.status_code == 401
    assert response.json() == {"detail": "missing bearer token"}
    for name, value in _PRIVATE_HEADERS.items():
        assert response.headers[name] == value
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert len(auth_calls) == 1
    assert entitlement_calls == []


def test_real_dependency_403_is_private_and_requires_always(monkeypatch) -> None:
    client = _real_client(monkeypatch)
    _forbid_compose(monkeypatch)
    auth_calls: list = []
    entitlement_calls: list = []

    def _require_user(authorization=None, *_args, **_kwargs) -> dict:
        auth_calls.append(authorization)
        return {"id": "u-wp19"}

    def _enforce_site_full(user, *, always=False) -> dict:
        entitlement_calls.append((user, always))
        raise HTTPException(status_code=403, detail="site_full required")

    _stub_auth(monkeypatch, require_user=_require_user, enforce_site_full=_enforce_site_full)

    response = client.get(_PATH, headers={"Authorization": "Bearer wp19-token"})
    assert response.status_code == 403
    assert response.json() == {"detail": "site_full required"}
    for name, value in _PRIVATE_HEADERS.items():
        assert response.headers[name] == value
    assert entitlement_calls == [({"id": "u-wp19"}, True)]


def test_flag_off_404_never_touches_auth(monkeypatch) -> None:
    client = _real_client(monkeypatch, flag_on=False)
    _forbid_compose(monkeypatch)
    auth_calls: list = []
    entitlement_calls: list = []

    def _require_user(authorization=None, *_args, **_kwargs):
        auth_calls.append(authorization)
        raise HTTPException(status_code=401, detail="missing bearer token")

    def _enforce_site_full(user, *, always=False) -> dict:
        entitlement_calls.append((user, always))
        return user

    _stub_auth(monkeypatch, require_user=_require_user, enforce_site_full=_enforce_site_full)

    response = client.get(_PATH, headers={"Authorization": "Bearer wp19-token"})
    assert response.status_code == 404
    assert auth_calls == []
    assert entitlement_calls == []


def test_invalid_ticker_400_after_entitlement_and_before_compose(monkeypatch) -> None:
    with pytest.raises(ContractError):
        safe_ticker("A..B")

    client = _real_client(monkeypatch)
    _forbid_compose(monkeypatch)
    auth_calls, entitlement_calls = _allowing_stubs(monkeypatch)

    response = client.get("/api/integrated-answer/v1/A..B", headers={"Authorization": "Bearer wp19-token"})
    assert response.status_code == 400
    assert response.json() == {"detail": "invalid ticker"}
    assert len(auth_calls) == 1
    assert len(entitlement_calls) == 1


def test_stubs_are_the_dependency_actually_called(monkeypatch) -> None:
    """Positive control: the real wrapper resolves the stubbed modules."""
    client = _real_client(monkeypatch)
    auth_calls, entitlement_calls = _allowing_stubs(monkeypatch)
    _patch_all_seams(monkeypatch)

    page = _page(client, "AAPL")
    assert page["schema"] == "integrated_answer.v0"
    assert len(auth_calls) == 1
    assert len(entitlement_calls) == 1
