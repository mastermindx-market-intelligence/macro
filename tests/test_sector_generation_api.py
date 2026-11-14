"""Authorization-envelope tests for the coherent Sector read API.

These are TRANSPORT tests. They exercise the real incumbent gates
(``app.regwall.regwall_check`` / ``app.paywall.paywall_check``) with a
qualified-reader fixture standing in for the corrected publisher plus the pure
projection, which are still under implementation upstream.

What these tests do NOT prove: that a generation is actually coherent, fresh
or correctly derived. An injected fixture is a contract fixture, not evidence
of generation correctness. The source-generation truth belongs to the publisher
owner and its own tests.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import paywall, sector_generation as sg
from app import main as macro_main

REPO_ROOT = Path(__file__).resolve().parents[1]

UID = "11111111-1111-1111-1111-111111111111"
TOKEN = "fixture-access-token"
COOKIE_NAME = "sb-fixture-auth-token"

SOURCE_SESSION = "2026-11-03"
PUBLISHED_AT = "2026-11-06T01:12:00Z"


# Independent resource expectation: removing an implementation constant must
# fail the gate tests, rather than changing their expected result too.
EXPECTED_PREVIEW_RESOURCES = (
    "/sectordata/sector_central.json",
    "/sectordata/sector_cycles.json",
    "/basketdata/baskets.json",
    "/basketdata/si_handoff.json",
    "/basketdata/action_board.json",
)
EXPECTED_ENTITLED_RESOURCES = EXPECTED_PREVIEW_RESOURCES + (
    "/premiumdata/sector_central.json",
)


def _payload(data, *, source_session=SOURCE_SESSION, published_at=PUBLISHED_AT,
             qualification="accepted", audience="preview"):
    return {
        "data": {"schema": "sector_native_view.v1", "audience": audience, **data},
        "receipt": {
            "schema": "sector_native_view.receipt.v1",
            "source_session": source_session,
            "published_at": published_at,
            "qualification": qualification,
        },
    }


class FixtureReader:
    """A qualified-reader fixture: counts calls, records what it was asked."""

    def __init__(self, result=None, raises: Exception | None = None):
        self.calls: list[sg.SectorGenerationRequest] = []
        self._result = result
        self._raises = raises

    def read_selected_generation(self, request: sg.SectorGenerationRequest):
        self.calls.append(request)
        if self._raises is not None:
            raise self._raises
        if self._result is not None:
            return self._result
        return sg.SectorGeneration(
            payload=_payload({"sector": "semiconductors", "rows": []}, audience=request.audience),
            source_session=SOURCE_SESSION,
            published_at=PUBLISHED_AT,
            qualification="accepted",
        )


def _client(reader=None, *, state_reader=None) -> TestClient:
    app = FastAPI()
    app.include_router(sg.create_router(reader))
    if state_reader is not None:
        app.state.sector_generation_reader = state_reader
    return TestClient(app)


def _entitled_row() -> dict:
    return {"tier": "essential", "status": "active", "features": ["site_full"]}


def _free_row() -> dict:
    return {"tier": "free", "status": "none", "features": []}


@pytest.fixture(autouse=True)
def _incumbent_gates(monkeypatch):
    """Bind the incumbent gates to a fixture identity/entitlement.

    The gates themselves are NOT replaced: the real classification, the real
    ``site_access.yml`` policy and the real ``premium.enforced_early`` rule run.
    Only the identity lookup and the entitlement row are stubbed, because both
    reach outside this repository.
    """
    monkeypatch.delenv("PAYWALL_ENABLED", raising=False)
    monkeypatch.setenv("REGWALL_ENABLED", "1")
    state = {"row": _entitled_row()}

    monkeypatch.setattr(
        macro_main,
        "_mm_supabase_access_token",
        lambda request: TOKEN if request.cookies else None,
    )
    monkeypatch.setattr(macro_main, "_mm_verify_uid_cached", lambda token: UID)
    monkeypatch.setattr(
        paywall,
        "_fetch_supabase_user",
        lambda token: paywall._Identity(UID, "reader@example.test", {"id": UID}, "ok"),
    )
    monkeypatch.setattr(paywall, "_store_entitlement", lambda uid: (state["row"], True))
    paywall._AUTH_CACHE.clear()
    paywall._ENT_CACHE.clear()
    yield state
    paywall._AUTH_CACHE.clear()
    paywall._ENT_CACHE.clear()


# ---------------------------------------------------------------------------
# Gate behaviour: the incumbent policy is preserved, not re-implemented.
# ---------------------------------------------------------------------------


def test_unregistered_caller_is_denied_before_the_reader_runs(_incumbent_gates):
    reader = FixtureReader()
    response = _client(reader).get("/api/sector-generation")
    assert response.status_code == 401
    assert response.json()["code"] == sg.ERROR_AUTHENTICATION_REQUIRED
    assert reader.calls == []


def test_registered_free_caller_is_denied_while_the_global_paywall_is_on(
    _incumbent_gates, monkeypatch
):
    monkeypatch.setenv("PAYWALL_ENABLED", "1")
    _incumbent_gates["row"] = _free_row()
    paywall._ENT_CACHE.clear()
    reader = FixtureReader()
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 403
    assert response.json()["code"] == sg.ERROR_ENTITLEMENT_REQUIRED
    assert reader.calls == []


def test_preview_is_not_free_access_while_the_global_paywall_is_on(
    _incumbent_gates, monkeypatch
):
    """``preview`` is an audience, not a discount.

    ``/sectordata`` and ``/basketdata`` are unknown to the access policy, so
    they read ``premium`` under the incumbent default and a free registered
    caller is denied exactly as the static artifacts deny them.
    """
    monkeypatch.setenv("PAYWALL_ENABLED", "1")
    _incumbent_gates["row"] = _free_row()
    paywall._ENT_CACHE.clear()
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=preview", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 403
    assert response.json()["code"] == sg.ERROR_ENTITLEMENT_REQUIRED
    assert reader.calls == []


def test_preview_reads_through_for_a_registered_caller_while_the_wall_is_staged_off(
    _incumbent_gates,
):
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=preview", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 200
    assert response.json()["audience"] == "preview"
    assert len(reader.calls) == 1


def test_entitled_audience_requires_the_entitlement_even_while_the_wall_is_off(
    _incumbent_gates,
):
    """``/premiumdata/`` is enforced early; the global switch cannot open it."""
    _incumbent_gates["row"] = _free_row()
    paywall._ENT_CACHE.clear()
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=entitled", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 403
    assert response.json()["code"] == sg.ERROR_ENTITLEMENT_REQUIRED
    assert reader.calls == []


def test_entitled_audience_reads_through_for_an_entitled_caller(_incumbent_gates):
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=entitled", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 200
    assert response.json()["audience"] == "entitled"
    assert len(reader.calls) == 1


def test_registration_wall_off_still_leaves_the_entitlement_wall_in_place(
    _incumbent_gates, monkeypatch
):
    """The registration wall and the paid wall stay independent."""
    monkeypatch.setenv("REGWALL_ENABLED", "0")
    _incumbent_gates["row"] = _free_row()
    paywall._ENT_CACHE.clear()
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=entitled", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 403
    assert response.json()["code"] == sg.ERROR_ENTITLEMENT_REQUIRED
    assert reader.calls == []


# ---------------------------------------------------------------------------
# Caller control: a caller cannot weaken access.
# ---------------------------------------------------------------------------


def test_caller_cannot_spoof_a_public_resource_path_to_pass_the_gates():
    """``/macro.html`` is public; a caller must not be able to name it.

    Without the server-owned ``x-original-uri`` overwrite, the registration
    wall would classify the request as the public funnel and allow it.
    """
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation",
        headers={
            "x-original-uri": "/macro.html",
            "x-original-kind": "document",
            "sec-fetch-dest": "document",
        },
    )
    assert response.status_code == 401
    assert response.json()["code"] == sg.ERROR_AUTHENTICATION_REQUIRED
    assert reader.calls == []


def test_caller_cannot_spoof_a_public_resource_path_to_bypass_the_paid_wall(
    _incumbent_gates, monkeypatch
):
    monkeypatch.setenv("PAYWALL_ENABLED", "1")
    _incumbent_gates["row"] = _free_row()
    paywall._ENT_CACHE.clear()
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=entitled",
        headers={
            "x-original-uri": "/macro.html",
            "x-original-kind": "document",
            "sec-fetch-dest": "document",
        },
        cookies={COOKIE_NAME: "x"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == sg.ERROR_ENTITLEMENT_REQUIRED
    assert reader.calls == []


def test_caller_cannot_downgrade_the_denial_class_to_a_document_redirect():
    """Asset semantics are server-owned: the denial stays a 401, never a 302."""
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation",
        headers={"sec-fetch-dest": "document", "x-original-kind": "document"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert "location" not in {k.lower() for k in response.headers}


def test_caller_cannot_name_a_resource_root_or_generation_through_the_query():
    reader = FixtureReader()
    for query in (
        "?path=/sectordata/sector_central.json",
        "?root=/var/lib/macro-live/public",
        "?generation=2026-11-06",
        "?domain=mastermind-x.com",
        "?audience=preview&audience=entitled",
        "?audience=",
        "?audience=PREVIEW",
    ):
        response = _client(reader).get(f"/api/sector-generation{query}")
        assert response.status_code == 400, query
        assert response.json()["code"] == sg.ERROR_REQUEST_INVALID, query
    assert reader.calls == []


def test_every_required_resource_is_gated_with_a_server_owned_path(monkeypatch):
    """The gate set is the server's, not the caller's."""
    seen_regwall: list[str] = []
    seen_paywall: list[str] = []
    real_regwall = sg.regwall_check
    real_paywall = sg.paywall_check

    def spy_regwall(request):
        seen_regwall.append(request.headers.get("x-original-uri"))
        assert request.headers.get("x-original-kind") == "asset"
        assert request.headers.get("sec-fetch-dest") is None
        return real_regwall(request)

    def spy_paywall(request):
        seen_paywall.append(request.headers.get("x-original-uri"))
        return real_paywall(request)

    monkeypatch.setattr(sg, "regwall_check", spy_regwall)
    monkeypatch.setattr(sg, "paywall_check", spy_paywall)

    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=entitled", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 200
    assert seen_regwall == list(EXPECTED_ENTITLED_RESOURCES)
    assert seen_paywall == list(EXPECTED_ENTITLED_RESOURCES)


def test_preview_does_not_require_the_paid_board_resource(monkeypatch):
    seen: list[str] = []
    real_regwall = sg.regwall_check

    def spy_regwall(request):
        seen.append(request.headers.get("x-original-uri"))
        return real_regwall(request)

    monkeypatch.setattr(sg, "regwall_check", spy_regwall)
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=preview", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 200
    assert seen == list(EXPECTED_PREVIEW_RESOURCES)
    assert "/premiumdata/sector_central.json" not in seen


# ---------------------------------------------------------------------------
# The reader boundary: one call, after authorization, no caller input.
# ---------------------------------------------------------------------------


def test_reader_is_called_exactly_once_per_allowed_request(_incumbent_gates):
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=entitled", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 200
    assert len(reader.calls) == 1


def test_reader_receives_only_the_closed_audience_choice(_incumbent_gates):
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=entitled", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 200
    call = reader.calls[0]
    assert isinstance(call, sg.SectorGenerationRequest)
    assert call.audience == "entitled"
    assert set(vars(call)) == {"audience"}
    assert call.audience in sg.AUDIENCES


def test_default_audience_is_preview_and_is_still_gated(_incumbent_gates, monkeypatch):
    monkeypatch.setenv("PAYWALL_ENABLED", "1")
    _incumbent_gates["row"] = _free_row()
    paywall._ENT_CACHE.clear()
    reader = FixtureReader()
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 403
    assert reader.calls == []


def test_gate_failure_fails_closed_before_the_reader_runs(monkeypatch):
    def exploding_gate(request):
        raise RuntimeError("gate exploded")

    monkeypatch.setattr(sg, "regwall_check", exploding_gate)
    reader = FixtureReader()
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 503
    assert response.json()["code"] == sg.ERROR_SERVICE_UNAVAILABLE
    assert reader.calls == []


def test_reader_exception_is_unavailable_and_never_an_empty_success(_incumbent_gates):
    reader = FixtureReader(raises=RuntimeError("publisher exploded"))
    response = _client(reader).get(
        "/api/sector-generation", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 503
    assert response.json()["code"] == sg.ERROR_GENERATION_UNAVAILABLE
    assert "projection" not in response.json()


def test_absent_reader_is_unavailable_and_never_a_fallback(_incumbent_gates):
    response = _client(None).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 503
    assert response.json()["code"] == sg.ERROR_GENERATION_UNAVAILABLE


def test_reader_installed_as_a_runtime_capability_is_used(_incumbent_gates):
    reader = FixtureReader()
    client = _client(None, state_reader=reader)
    response = client.get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 200
    assert len(reader.calls) == 1


def test_unusable_reader_result_is_reported_as_unavailable(_incumbent_gates):
    for bad in (
        {"payload": {}, "source_session": SOURCE_SESSION, "published_at": PUBLISHED_AT},
        sg.SectorGeneration(
            payload=[],
            source_session=SOURCE_SESSION,
            published_at=PUBLISHED_AT,
            qualification="accepted",
        ),
        sg.SectorGeneration(
            payload={},
            source_session="not-a-date",
            published_at=PUBLISHED_AT,
            qualification="accepted",
        ),
        sg.SectorGeneration(
            payload={},
            source_session=SOURCE_SESSION,
            published_at=PUBLISHED_AT,
            qualification="Not A Word",
        ),
    ):
        reader = FixtureReader(result=bad)
        response = _client(reader).get(
            "/api/sector-generation", cookies={COOKIE_NAME: "x"}
        )
        assert response.status_code == 503, bad
        assert response.json()["code"] == sg.ERROR_GENERATION_UNAVAILABLE


def test_a_mapping_projection_is_served_as_a_json_object(_incumbent_gates):
    """The payload may be any mapping; it is served as a plain JSON object."""
    reader = FixtureReader(
        result=sg.SectorGeneration(
            payload=MappingProxyType(_payload({"sector": "energy", "rows": []})),
            source_session=SOURCE_SESSION,
            published_at=PUBLISHED_AT,
            qualification="accepted",
        )
    )
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 200
    assert response.json()["projection"] == _payload({"sector": "energy", "rows": []})


def test_non_finite_projection_value_is_refused(_incumbent_gates):
    reader = FixtureReader(
        result=sg.SectorGeneration(
            payload=_payload({"score": float("nan")}),
            source_session=SOURCE_SESSION,
            published_at=PUBLISHED_AT,
            qualification="accepted",
        )
    )
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 503
    assert response.json()["code"] == sg.ERROR_GENERATION_UNAVAILABLE
    assert "NaN" not in response.text


def test_non_json_projection_value_is_refused(_incumbent_gates):
    reader = FixtureReader(
        result=sg.SectorGeneration(
            payload=_payload({"rows": {"a", "b"}}),
            source_session=SOURCE_SESSION,
            published_at=PUBLISHED_AT,
            qualification="accepted",
        )
    )
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 503
    assert response.json()["code"] == sg.ERROR_GENERATION_UNAVAILABLE


# ---------------------------------------------------------------------------
# Response contract: bounded, private, and truthful about the source.
# ---------------------------------------------------------------------------


def _encoded_length(payload, audience: str = sg.AUDIENCE_PREVIEW) -> int:
    body = {
        "schema": sg.SCHEMA,
        "audience": audience,
        "source_session": SOURCE_SESSION,
        "published_at": PUBLISHED_AT,
        "qualification": "accepted",
        "projection": payload,
    }
    return len(
        json.dumps(body, allow_nan=False, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )


def test_projection_at_the_four_mebibyte_ceiling_is_served(_incumbent_gates):
    overhead = _encoded_length(_payload({"filler": ""}))
    filler = "x" * (sg.MAX_ENCODED_BYTES - overhead)
    payload = _payload({"filler": filler})
    assert _encoded_length(payload) == sg.MAX_ENCODED_BYTES
    reader = FixtureReader(
        result=sg.SectorGeneration(
            payload=payload,
            source_session=SOURCE_SESSION,
            published_at=PUBLISHED_AT,
            qualification="accepted",
        )
    )
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 200
    assert len(response.content) == sg.MAX_ENCODED_BYTES


def test_projection_one_byte_over_the_ceiling_is_refused(_incumbent_gates):
    overhead = _encoded_length(_payload({"filler": ""}))
    filler = "x" * (sg.MAX_ENCODED_BYTES - overhead + 1)
    reader = FixtureReader(
        result=sg.SectorGeneration(
            payload=_payload({"filler": filler}),
            source_session=SOURCE_SESSION,
            published_at=PUBLISHED_AT,
            qualification="accepted",
        )
    )
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 503
    assert response.json()["code"] == sg.ERROR_GENERATION_TOO_LARGE
    assert "filler" not in response.text


def test_source_session_publication_and_qualification_are_preserved_verbatim(
    _incumbent_gates,
):
    reader = FixtureReader(
        result=sg.SectorGeneration(
            payload=_payload({"sector": "energy"}, source_session="2026-11-04",
                             published_at="2026-11-06T02:31:07Z", qualification="stale"),
            source_session="2026-11-04",
            published_at="2026-11-06T02:31:07Z",
            qualification="stale",
        )
    )
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_session"] == "2026-11-04"
    assert body["published_at"] == "2026-11-06T02:31:07Z"
    assert body["qualification"] == "stale"
    assert body["projection"] == _payload(
        {"sector": "energy"}, source_session="2026-11-04",
        published_at="2026-11-06T02:31:07Z", qualification="stale",
    )


def test_a_stale_projection_keeps_its_explicit_qualification(_incumbent_gates):
    """A healthy but stale generation stays truthfully labelled stale."""
    reader = FixtureReader(
        result=sg.SectorGeneration(
            payload=_payload({"sector": "energy"}, source_session="2026-11-03",
                             published_at="2026-11-06T02:31:07Z", qualification="stale"),
            source_session="2026-11-03",
            published_at="2026-11-06T02:31:07Z",
            qualification="stale",
        )
    )
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 200
    assert response.json()["qualification"] == "stale"
    assert response.json()["source_session"] == "2026-11-03"


def test_success_and_failure_responses_are_private_and_uncacheable(_incumbent_gates):
    ok_client = _client(FixtureReader())
    ok = ok_client.get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert ok.headers["cache-control"] == "private, no-store"
    assert ok.headers["vary"] == "Cookie"

    for response in (
        ok_client.get("/api/sector-generation"),
        ok_client.get("/api/sector-generation?audience=nope"),
        _client(None).get("/api/sector-generation", cookies={COOKIE_NAME: "x"}),
    ):
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Cookie"


def test_error_bodies_carry_no_private_metadata(_incumbent_gates, monkeypatch):
    monkeypatch.setenv("PAYWALL_ENABLED", "1")
    _incumbent_gates["row"] = _free_row()
    paywall._ENT_CACHE.clear()
    denied = [
        _client(FixtureReader()).get("/api/sector-generation"),
        _client(FixtureReader()).get("/api/sector-generation?audience=nope"),
        _client(FixtureReader()).get(
            "/api/sector-generation", cookies={COOKIE_NAME: "x"}
        ),
    ]
    # An entitled row lets a request reach the reader, so its failure classes
    # are observable rather than masked by the paid wall.
    _incumbent_gates["row"] = _entitled_row()
    paywall._ENT_CACHE.clear()
    unavailable = [
        _client(FixtureReader(raises=RuntimeError("boom"))).get(
            "/api/sector-generation", cookies={COOKIE_NAME: "x"}
        ),
        _client(None).get("/api/sector-generation", cookies={COOKIE_NAME: "x"}),
    ]
    for response in denied + unavailable:
        body = response.text
        assert body in {
            json.dumps(
                {"schema": sg.ERROR_SCHEMA, "code": sg.ERROR_AUTHENTICATION_REQUIRED},
                separators=(",", ":"),
            ),
            json.dumps(
                {"schema": sg.ERROR_SCHEMA, "code": sg.ERROR_REQUEST_INVALID},
                separators=(",", ":"),
            ),
            json.dumps(
                {"schema": sg.ERROR_SCHEMA, "code": sg.ERROR_ENTITLEMENT_REQUIRED},
                separators=(",", ":"),
            ),
            json.dumps(
                {"schema": sg.ERROR_SCHEMA, "code": sg.ERROR_GENERATION_UNAVAILABLE},
                separators=(",", ":"),
            ),
            json.dumps(
                {"schema": sg.ERROR_SCHEMA, "code": sg.ERROR_SERVICE_UNAVAILABLE},
                separators=(",", ":"),
            ),
        }
        for leak in (
            "Traceback",
            "boom",
            "/Volumes",
            "app/sector_generation.py",
            str(REPO_ROOT),
            "site_full",
            "/plans.html",
        ):
            assert leak not in body, leak


# ---------------------------------------------------------------------------
# Ownership: the existing application owns the one mounted route.
# ---------------------------------------------------------------------------


def test_the_route_is_mounted_exactly_once_in_the_existing_application():
    from app.main import app
    # Newer FastAPI retains included routers; enumerate their effective routes
    # while preserving the same single mounted GET ownership assertion.
    effective = []
    for route in app.routes:
        contexts = getattr(route, "effective_route_contexts", None)
        effective.extend(contexts() if callable(contexts) else [route])
    routes = [route for route in effective if getattr(route, "path", None) == "/api/sector-generation"]
    assert len(routes) == 1
    assert routes[0].methods == {"GET"}
    response = TestClient(app).get("/api/sector-generation?audience=invalid")
    assert response.status_code == 400
    assert response.json()["code"] == "REQUEST_INVALID"
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("audience", ["preview", "entitled"])
@pytest.mark.parametrize("board_rule", ["deny", "early_premium"])
def test_real_policy_can_deny_only_action_board_before_reader(
    tmp_path, monkeypatch, _incumbent_gates, audience, board_rule
):
    import yaml

    board = "/basketdata/action_board.json"
    allowed = [p for p in EXPECTED_ENTITLED_RESOURCES if p != board]
    policy = {
        "schema": "site_access.v1",
        "public": {"exact": allowed, "prefixes": []},
        "free_registered": {"exact": [], "prefixes": []},
        "deny": {"exact": [board] if board_rule == "deny" else [], "prefixes": []},
        "premium": {
            "required_feature": "site_full",
            "enforced_early": {
                "exact": [board] if board_rule == "early_premium" else [],
                "prefixes": [],
            },
        },
    }
    path = tmp_path / "site_access.yml"
    path.write_text(yaml.safe_dump(policy))
    monkeypatch.setattr(paywall, "ACCESS_CONFIG", path)
    monkeypatch.setattr(paywall, "_CONFIG_CACHE", None)
    monkeypatch.setenv("PAYWALL_ENABLED", "0")
    _incumbent_gates["row"] = _free_row()
    reader = FixtureReader()
    response = _client(reader).get(
        "/api/sector-generation?audience=" + audience, cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == (404 if board_rule == "deny" else 403)
    assert reader.calls == []


@pytest.mark.parametrize("field,value", [
    ("source_session", "2026-02-30"),
    ("source_session", "2026-11-03T00:00:00Z"),
    ("published_at", "2026-02-30T01:00:00Z"),
    ("published_at", "2026-11-06T01:00:00"),
    ("published_at", "2026-11-06T01:00:00Z trailing"),
    ("qualification", "current"),
    ("qualification", "closed"),
    ("qualification", "unavailable"),
])
def test_receipt_must_follow_actual_projection_date_clock_and_state_contract(field, value):
    facts = dict(source_session=SOURCE_SESSION, published_at=PUBLISHED_AT,
                 qualification="accepted")
    facts[field] = value
    reader = FixtureReader(result=sg.SectorGeneration(
        payload=_payload({}, **facts), **facts
    ))
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 503
    assert response.json()["code"] == sg.ERROR_GENERATION_UNAVAILABLE
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("field,value", [
    ("source_session", "2026-11-04"),
    ("published_at", "2026-11-06T02:00:00Z"),
    ("qualification", "stale"),
])
def test_transport_cannot_disagree_with_projection_receipt(field, value):
    facts = dict(source_session=SOURCE_SESSION, published_at=PUBLISHED_AT,
                 qualification="accepted")
    facts[field] = value
    reader = FixtureReader(result=sg.SectorGeneration(
        payload=_payload({"value": 1}), **facts
    ))
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 503
    assert response.json()["code"] == sg.ERROR_GENERATION_UNAVAILABLE


@pytest.mark.parametrize("failure", ["reader_property", "result_property", "mapping", "serialization_recursion"])
def test_entire_reader_envelope_fails_closed_with_private_headers(failure, caplog, monkeypatch):
    from collections.abc import Mapping

    secret = "PRIVATE_READER_PATH_DO_NOT_EMIT"

    class BrokenReader:
        @property
        def read_selected_generation(self):
            raise RuntimeError(secret)

    class BrokenResult:
        @property
        def payload(self):
            raise RuntimeError(secret)

    class BrokenMapping(Mapping):
        def __getitem__(self, key):
            raise RuntimeError(secret)
        def __iter__(self):
            raise RuntimeError(secret)
        def __len__(self):
            return 1

    if failure == "reader_property":
        reader = BrokenReader()
    elif failure == "result_property":
        reader = FixtureReader(result=BrokenResult())
    else:
        if failure == "mapping":
            payload = BrokenMapping()
        else:
            payload = _payload({"value": 1})
            from lib import sector_generation_wire as wire
            real_dumps = wire.json.dumps

            def exhausted_serializer(value, *args, **kwargs):
                # The process recursion limit varies with application imports.
                # Inject this real serializer failure; do not invent a nesting
                # limit for otherwise valid JSON below the response-size bound.
                if isinstance(value, dict) and value.get("schema") == sg.SCHEMA:
                    raise RecursionError(secret)
                return real_dumps(value, *args, **kwargs)

            monkeypatch.setattr(wire.json, "dumps", exhausted_serializer)
        reader = FixtureReader(result=sg.SectorGeneration(
            payload=payload, source_session=SOURCE_SESSION,
            published_at=PUBLISHED_AT, qualification="accepted",
        ))
    response = _client(reader).get("/api/sector-generation", cookies={COOKIE_NAME: "x"})
    assert response.status_code == 503
    assert response.json() == {
        "schema": sg.ERROR_SCHEMA, "code": sg.ERROR_GENERATION_UNAVAILABLE,
    }
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Cookie"
    assert secret not in response.text
    assert secret not in caplog.text


@pytest.mark.parametrize("audience", ["preview", "entitled"])
def test_actual_native_projection_preserves_explicit_older_brief_baseline(audience):
    from engine.sector_native_view import (
        SectorViewInputs, SectorViewReceipt, project_sector_view,
    )

    source, baseline = "2026-11-05", "2026-11-03"
    inputs = SectorViewInputs(
        central={"as_of": source, "sectors": [{"id": "xlv", "ticker": "XLV", "kind": "sector", "name": "Health Care"}]},
        cycles={"meta": {"asOf": source, "rs_history": {"schema": "sector_cycles.rs_history.v1", "mode": "reconstructed_price_history", "naturally_observed": False, "basis": "tr", "benchmark": "SPY", "horizons_sessions": [21, 63], "max_points_per_sector": 252}}, "sectors": [{"id": "xlv", "ticker": "XLV", "kind": "sector", "rs_history": [], "turns": []}]},
        baskets={"as_of": baseline, "theme_intel": {"as_of": baseline}},
        handoff={"theme_context": {"as_of": baseline, "leadership": {
            "state": "steady", "strength": [],
        }}},
        action_board={
            "schema": "sector_intelligence_action_board.v1", "as_of": baseline,
            "action_board": {lane: [] for lane in (
                "buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid"
            )},
        },
    )
    receipt = SectorViewReceipt(
        "actual-projection-g1", source, PUBLISHED_AT, "degraded",
        "actual-projection-input1", baseline_session=baseline,
    )
    projection = project_sector_view(inputs, receipt, audience=audience)
    reader = FixtureReader(result=sg.SectorGeneration(
        payload=projection, source_session=source,
        published_at=PUBLISHED_AT, qualification="degraded",
    ))
    response = _client(reader).get(
        "/api/sector-generation?audience=" + audience, cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["projection"] == projection
    assert body["source_session"] == source
    assert body["qualification"] == "degraded"
    assert body["projection"]["receipt"]["baseline_session"] == baseline
    assert body["projection"]["data"]["brief"]["as_of"] == baseline
    assert body["projection"]["data"]["brief"]["status"] == "declared_older_baseline"
    assert len(reader.calls) == 1


@pytest.mark.parametrize("part,field,value", [
    ("data", "audience", "entitled"),
    ("data", "schema", "another_projection.v1"),
    ("receipt", "schema", "another_receipt.v1"),
])
def test_native_projection_schema_and_audience_bind_the_transport(part, field, value):
    payload = _payload({"private_row": "MUST_NOT_BE_SERVED"})
    payload[part][field] = value
    reader = FixtureReader(result=sg.SectorGeneration(
        payload=payload, source_session=SOURCE_SESSION,
        published_at=PUBLISHED_AT, qualification="accepted",
    ))
    response = _client(reader).get(
        "/api/sector-generation?audience=preview", cookies={COOKIE_NAME: "x"}
    )
    assert response.status_code == 503
    assert response.json()["code"] == sg.ERROR_GENERATION_UNAVAILABLE
    assert "MUST_NOT_BE_SERVED" not in response.text
