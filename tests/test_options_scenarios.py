"""Source-qualified route tests for the Macro scenario-source ingress.

Every test drives the REAL mounted FastAPI route (``app.options_scenarios.router``)
through TestClient, which in turn drives the REAL native resolver
(``engine.intelligence_workspace.scenario_source_resolution``) and the REAL
protected retention library. Only the boundaries are controlled doubles, and
each is explicitly NOT live authority: the uncached Auth reader (a fake
getUser transport), the uncached billing read (a fake PostgREST row), the
exact caller-token Supabase RPC (a fake no-redirect transport), the retained
object store (an in-memory fake S3), the trusted destination seam and the
native source-use callback (controlled test seams), and the clock.

A green run proves route + native ORCHESTRATION only. It is never evidence of
a live database right, a real RLS policy, a qualified private destination or
an actual source-use authorization: the parent repo's own check owns that
judgment, and nothing here substitutes a SHIM result for it.
"""
from __future__ import annotations

import base64
import hashlib
import inspect
import io
import json
import sys
import urllib.error
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import billing, options_auth as M, options_scenarios as S, paywall
from engine import options_hub_retention as ohr
from engine.intelligence_workspace import scenario_source_resolution as ssr

UID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
SID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
URL = "https://supabase-fixture.invalid"
ISS = URL + "/auth/v1"
ANON = "fixture-public-anon-key"
INV = "3f2b8a4c-9d1e-4a57-b6c8-72e5f0a1d934"
INV_B = "4c2b8a4c-9d1e-4a57-b6c8-72e5f0a1d934"
GRANT = "7d3c1f0a-8b2e-4c5d-9a6b-1e0f2a3b4c5d"
OP = "9d3c1f0a-8b2e-4c5d-9a6b-1e0f2a3b4c5d"
SESSION = "2026-10-22"
CAPTURED = "2026-10-22T20:15:00Z"
EXPIRY = "2026-12-18"
ECONOMIC = "2026-12-18T16:00:00-05:00"
SELECTION = f"{EXPIRY}|{ECONOMIC}"
LENS = {"kind": "one", "exp": EXPIRY}
BUCKET = "controlled-scenario-bucket"
TODAY = ohr.date(2026, 10, 23)


def token(**changes):
    claims = dict(sub=UID, iss=ISS, session_id=SID, role="authenticated",
                  exp=2000, is_anonymous=False)
    claims.update(changes)
    return raw_token(json.dumps(claims))


def raw_token(payload):
    return "e30." + base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=") + ".c2ln"


class Body:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read(self, n: int) -> bytes:
        if self._pos >= len(self._data):
            return b""
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def close(self) -> None:
        pass


class FakeS3:
    def __init__(self, trace: list):
        self.objects: dict[str, bytes] = {}
        self.trace = trace

    def get_object(self, Bucket, Key):
        self.trace.append(("get", Key))
        if Key not in self.objects:
            err = OSError("no such key")
            err.response = {"Error": {"Code": "NoSuchKey"}}
            raise err
        data = self.objects[Key]
        return {"Body": Body(data), "ContentLength": len(data)}


def gex_raw(session=SESSION, spot=600.25):
    payload = {"schema": ohr.GEX_SCHEMA, "root": "SPY", "asof": session, "spot_ref": spot,
               "by_strike": [{"strike": 600.0, "net": -1.5}]}
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def moves_raw(session=SESSION):
    payload = {"schema": ohr.MOVES_SCHEMA, "root": "SPY", "asof": session,
               "atm_iv": 13.71, "expected_move": {"pct": 1.1, "lo": 593.4, "hi": 606.6}}
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


class FakeRpcResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")
        self.status = 200

    def read(self, limit=-1):
        if limit is None or limit < 0:
            return self._body
        return self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class World:
    """One controlled world around the real mounted route.

    Every transport and callback here is a controlled test double and proves
    orchestration only; none of them is live authority.
    """

    def __init__(self):
        self.trace: list = []
        self.s3 = FakeS3(self.trace)
        self.gex_bytes = gex_raw()
        self.gex_ref = ohr.reference_for_bytes("SPY", "gex", self.gex_bytes, today=TODAY)
        self.moves_bytes = moves_raw()
        self.moves_ref = ohr.reference_for_bytes("SPY", "moves", self.moves_bytes,
                                                 today=TODAY)
        self.s3.objects[self.gex_ref.key] = self.gex_bytes
        self.s3.objects[self.moves_ref.key] = self.moves_bytes
        self.resource_results = [True, True]
        self.resource_calls = 0
        self.source_calls = 0
        self.source_status = "allowed"
        self.source_overrides: dict = {}
        self.destination_calls = 0
        self.destination_status = "qualified"
        self.destination_overrides: dict = {}
        self.destination_raises = False
        self.seen_source_bindings: list = []
        self.clock = lambda: BASE
        self.state = SimpleNamespace(
            auth_calls=0, fail_auth_at=frozenset(), product_reads=0, operator=False,
            row=dict(tier="pro", features=["terminal_live_options"], status="active"),
            user=dict(id=UID, email="fixture@example.invalid", is_anonymous=False),
            auth_error=None, rpc_calls=0, rpc_urls=[], rpc_headers=[], rpc_bodies=[],
            rpc_responses=[], rpc_error=None, now=1000, decided_at=DECIDED)

    # ---- transports (recorded into the shared ordered trace) --------------

    def patch(self, monkeypatch):
        state = self.state

        def http(req, timeout):
            state.auth_calls += 1
            self.trace.append(("auth", state.auth_calls))
            assert req.full_url == URL + "/auth/v1/user" and timeout == 4
            if state.auth_error is not None:
                raise state.auth_error
            if state.auth_calls in state.fail_auth_at:
                raise urllib.error.HTTPError(URL, 401, "synthetic", {}, None)

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

                def read(self):
                    return json.dumps(state.user).encode()

            return Response()

        def pg(method, path, **kwargs):
            state.product_reads += 1
            self.trace.append(("product", state.product_reads))
            assert method == "GET" and path.startswith("user_entitlements?user_id=eq.")
            return [] if state.row is None else [state.row]

        def rpc_open(req, timeout):
            state.rpc_calls += 1
            state.rpc_urls.append(req.full_url)
            state.rpc_headers.append({k.lower(): v for k, v in req.header_items()})
            state.rpc_bodies.append(json.loads(req.data.decode("utf-8")))
            self.trace.append(("rpc", req.full_url))
            assert timeout == S._RPC_TIMEOUT
            if state.rpc_error is not None:
                raise state.rpc_error
            response = state.rpc_responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return FakeRpcResponse(response)

        main = SimpleNamespace(
            SUPABASE_URL=URL, SUPABASE_ANON_KEY=ANON,
            _brain_module=lambda: SimpleNamespace(
                _unlimited_allowed=lambda email: state.operator))
        monkeypatch.setitem(sys.modules, "app.main", main)
        monkeypatch.setattr(M.time, "time", lambda: state.now)
        monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", "synthetic")
        monkeypatch.setattr(paywall.urllib.request, "urlopen", http)
        monkeypatch.setattr(billing, "_pg", pg)
        monkeypatch.setattr(S, "_open_rpc", rpc_open)

        def forbidden(*args, **kwargs):
            raise AssertionError("cache/grace used")

        monkeypatch.setattr(paywall, "_resolve_identity", forbidden)
        monkeypatch.setattr(paywall, "_entitled", forbidden)

    # ---- controlled native seams -----------------------------------------

    def resource_access(self, binding):
        self.resource_calls += 1
        self.trace.append(("resource", self.resource_calls))
        result = self.resource_results[min(self.resource_calls - 1,
                                           len(self.resource_results) - 1)]
        if result == "raise":
            raise RuntimeError("resource callback failed")
        return result

    def source_use_decision(self, binding):
        self.source_calls += 1
        self.trace.append(("source", self.source_calls))
        self.seen_source_bindings.append(binding)
        if self.source_status == "raise":
            raise RuntimeError("decision callback failed")
        decided = self.state.decided_at
        if decided == "now":
            decided = datetime.now(timezone.utc).isoformat()
        out = dict(binding)
        out.update(self.source_overrides)
        return {"status": self.source_status, "binding": out,
                "policy_id": "policy-1", "policy_revision": "p-rev-2",
                "registry_revision": "registry-3",
                "decided_at": decided}

    def destination_qualifier(self, request):
        """CONTROLLED trusted-server destination seam; NOT live authority."""
        self.destination_calls += 1
        self.trace.append(("destination", self.destination_calls))
        if self.destination_raises:
            raise RuntimeError("destination backend down")
        out = dict(request)
        out.update(self.destination_overrides)
        return {"status": self.destination_status, "binding": out}

    # ---- app/route wiring --------------------------------------------------

    def client(self, *, bind=True, partial=False):
        app = FastAPI()
        app.include_router(S.router)
        if bind:
            kwargs = dict(s3=self.s3, bucket=BUCKET,
                          destination=self.destination_qualifier,
                          resource_access=self.resource_access,
                          source_use_decision=self.source_use_decision,
                          clock=self.clock)
            if partial:
                kwargs["destination"] = None
            app.state.options_scenario_source_bindings = S.SourceScenarioBindings(**kwargs)
        self.app = app
        return TestClient(app)

    def post(self, client, payload, *, token_value=None, params=None):
        headers = {"Content-Type": "application/json"}
        if token_value is not None:
            headers["Authorization"] = "Bearer " + token_value
        return client.post(S.ROUTE, content=json.dumps(payload), headers=headers,
                           params=params or {})

    # ---- fixture builders ---------------------------------------------------

    def capture(self, *, with_moves=True, gex_ref=None, moves_ref=None,
                model_version=None, schema=None, **source_over):
        gex = gex_ref if gex_ref is not None else self.gex_ref
        moves = (moves_ref if moves_ref is not None else self.moves_ref) \
            if with_moves else None
        source = {"owner": "options_hub", "root": "SPY", "session": SESSION,
                  "source_as_of": None, "evaluated_at": CAPTURED, "lens": dict(LENS),
                  "selection_key": SELECTION,
                  "basis_sha256": hashlib.sha256(b"captured basis").hexdigest(),
                  "gex": {"sha256": gex.sha256, "byte_length": gex.byte_length},
                  "moves": None if moves is None
                  else {"sha256": moves.sha256, "byte_length": moves.byte_length}}
        source.update(source_over)
        return {"schema": schema or "investigation_scenario_reference.v1",
                "model_version": model_version or "exposure-scenario/v1",
                "inputs": {"targetSpot": 600.25, "deltaSigmaPts": 0.0, "days": 1},
                "source": source}

    def row(self, revision=4, inv=INV, capture=None, **extra):
        # Actual0028 caller-token RPC wire; no flattened scenario alias.
        capture = self.capture() if capture is None else capture
        if "scenario_capture" in extra:
            capture = extra.pop("scenario_capture")
        row = {"status": "found", "id": inv, "revision": revision,
               "current_revision": revision, "lifecycle": "active",
               "manifest": {"schema": "investigation_manifest.v2", "scenario_capture": capture}}
        row.update(extra)
        return row

    def handoff(self, **extra):
        row = {"schema": "mm.research_handoff.v1", "investigation_id": INV,
               "revision": 4, "grant_id": GRANT, "scenario_capture": self.capture()}
        if "id" in extra:
            extra["investigation_id"] = extra.pop("id")
        row.update(extra)
        return {"status": "found", "handoff": row}

    def resolve_payload(self, revision=4, grant=None, inv=INV):
        return {"mode": "resolve", "investigation_id": inv, "revision": revision,
                "grant_id": grant}

    def qualify_payload(self, *, expected=0, inv=INV, capture=None, grant=None,
                        operation_id=OP, revision=None):
        expected = expected
        return {"mode": "qualify", "investigation_id": inv,
                "revision": (expected + 1) if revision is None else revision,
                "grant_id": grant, "expected_revision": expected,
                "operation_id": operation_id,
                "capture": self.capture() if capture is None else capture}

    def gets(self):
        return [entry[1] for entry in self.trace if entry[0] == "get"]


BASE = datetime(2026, 10, 23, 14, 0, tzinfo=timezone.utc)
DECIDED = "2026-10-23T14:00:00Z"


@pytest.fixture
def world(monkeypatch):
    w = World()
    w.patch(monkeypatch)
    return w


# ---------------------------------------------------------------------------
# Happy path: the exact private success body over the real route + native flow
# ---------------------------------------------------------------------------


def test_owner_resolve_happy_path_exact_success_body(world):
    h = world
    h.state.rpc_responses = [h.row(), h.row()]
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "private, no-store"
    assert "authorization" in response.headers.get("Vary", "").lower()
    body = response.json()
    assert set(body) == {"status", "mode", "investigation_id", "revision",
                         "grant_id", "capture", "gex", "moves"}
    assert (body["status"], body["mode"], body["investigation_id"], body["revision"],
            body["grant_id"]) == ("resolved", "resolve", INV, 4, None)
    # The canonical row capture is echoed exactly — never request metadata.
    assert body["capture"] == h.capture()
    # Exact verified raw bytes, strict base64, exact digest and length.
    assert body["gex"]["sha256"] == h.gex_ref.sha256
    assert body["gex"]["byte_length"] == len(h.gex_bytes)
    gex_decoded = base64.b64decode(body["gex"]["base64"], validate=True)
    assert gex_decoded == h.gex_bytes
    assert hashlib.sha256(gex_decoded).hexdigest() == body["gex"]["sha256"]
    assert body["moves"]["base64"] == base64.b64encode(h.moves_bytes).decode("ascii")
    # Fixed configured origin, public anon key, exact caller token, exact RPC
    # and parameters — no service role, no caller URL, no other host.
    assert h.state.rpc_urls == [f"{URL}/rest/v1/rpc/read_investigation_v2"] * 2
    headers = h.state.rpc_headers[0]
    assert headers["authorization"] == "Bearer " + token()
    assert headers["apikey"] == ANON
    assert h.state.rpc_bodies[0] == {"p_id": INV, "p_revision": 4}
    # Ordered composition: auth, RLS row, resource + source qualification, then
    # the protected reads, then the actor/product/row rechecks.
    kinds = [entry[0] for entry in h.trace]
    assert kinds[0] == "auth"
    assert kinds.index("rpc") < kinds.index("resource") < kinds.index("source")
    assert kinds.index("source") < kinds.index("get")
    assert kinds.count("get") == 2
    rpc_positions = [i for i, kind in enumerate(kinds) if kind == "rpc"]
    assert len(rpc_positions) == 2 and rpc_positions[1] > kinds.index("get")
    assert h.state.product_reads >= 2
    # The native callbacks saw the exact caller identity and pinned action.
    binding = h.seen_source_bindings[0]
    assert binding["viewer_id"] == UID and binding["viewer_issuer"] == ISS
    assert binding["auth_epoch"] == SID and binding["action"] == "evaluate"
    assert binding["model_version"] == "exposure-scenario/v1"
    assert binding["investigation_id"] == INV and binding["investigation_revision"] == 4
    assert binding["sha256"] == h.gex_ref.sha256
    # The destination seam qualified the exact bucket and ref set.
    assert h.destination_calls >= 3


def test_success_round_trip_through_real_route_survives_repost(world):
    # Save/reopen semantics: the SAME canonical capture taken from a resolved
    # success body re-qualifies as a prospective REVISE of the next revision,
    # and the stored bytes still read exactly (held, not recomputed).
    h = world
    h.state.rpc_responses = [h.row(), h.row()]
    body = h.post(h.client(), h.resolve_payload(), token_value=token()).json()
    h.trace.clear()
    h.state.rpc_responses = [h.row(revision=4), None, h.row(revision=4), None]
    h.state.rpc_urls.clear()
    h.state.rpc_bodies.clear()
    payload = {"mode": "qualify", "investigation_id": INV, "revision": 5,
               "grant_id": None, "expected_revision": 4, "operation_id": OP,
               "capture": body["capture"]}
    qualified = h.post(h.client(), h.qualify_payload(expected=4,
                                                     capture=body["capture"]),
                       token_value=token())
    assert qualified.status_code == 200
    qbody = qualified.json()
    assert qbody["status"] == "resolved" and qbody["mode"] == "qualify"
    assert qbody["revision"] == 5 and qbody["capture"] == body["capture"]
    assert [b["p_revision"] for b in h.state.rpc_bodies] == [4, 5, 4, 5]
    assert h.gets() == [h.gex_ref.key, h.moves_ref.key]


def test_moves_absent_is_explicit_null_not_a_substitute(world):
    h = world
    h.moves_bytes = None
    h.s3.objects.pop(h.moves_ref.key)
    capture = h.capture(with_moves=False)
    h.state.rpc_responses = [h.row(capture=capture), h.row(capture=capture)]
    body = h.post(h.client(), h.resolve_payload(), token_value=token()).json()
    assert body["status"] == "resolved" and body["moves"] is None
    assert body["capture"]["source"]["moves"] is None
    assert h.gets() == [h.gex_ref.key]


# ---------------------------------------------------------------------------
# Absent backend: typed refusal with literally zero IO
# ---------------------------------------------------------------------------


def test_absent_backend_refuses_with_zero_io(world):
    h = world
    client = h.client(bind=False)
    response = h.post(client, h.resolve_payload(), token_value=token())
    assert response.status_code == 200
    assert response.json() == {"status": "unavailable",
                               "reason": "source_binding_unavailable"}
    assert h.state.auth_calls == 0 and h.state.rpc_calls == 0
    assert h.state.product_reads == 0
    assert h.trace == []
    # A default (all-None) binding instance is equally unbound.
    h.app.state.options_scenario_source_bindings = S.SourceScenarioBindings()
    assert h.post(client, h.resolve_payload(), token_value=token()).json() == \
        {"status": "unavailable", "reason": "source_binding_unavailable"}
    assert h.state.auth_calls == 0 and h.state.rpc_calls == 0 and h.trace == []


def test_incomplete_binding_missing_destination_is_unavailable(world):
    h = world
    client = h.client(partial=True)
    response = h.post(client, h.resolve_payload(), token_value=token())
    assert response.json() == {"status": "unavailable",
                               "reason": "source_binding_unavailable"}
    assert h.state.auth_calls == 0 and h.state.rpc_calls == 0 and h.trace == []


# ---------------------------------------------------------------------------
# Authentication and product authority (existing readers, uncached)
# ---------------------------------------------------------------------------


def test_missing_or_malformed_bearer_is_typed_without_any_io(world):
    h = world
    client = h.client()
    payload = h.resolve_payload()
    assert h.post(client, payload).json() == {
        "status": "unavailable", "reason": "authentication_unavailable"}
    assert h.post(client, payload, token_value="").json()["reason"] == \
        "authentication_unavailable"
    assert h.post(client, payload, token_value="not-a-jwt").json()["reason"] == \
        "authentication_unavailable"
    assert h.post(client, payload, token_value=token() + " ").json()["reason"] == \
        "authentication_unavailable"
    assert h.state.auth_calls == 0 and h.state.rpc_calls == 0 and h.gets() == []


def test_auth_outage_refuses_without_rpc_or_reads(world):
    h = world
    h.state.auth_error = urllib.error.HTTPError(URL, 500, "synthetic", {}, None)
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.json() == {"status": "unavailable",
                               "reason": "authentication_unavailable"}
    assert h.state.auth_calls == 1 and h.state.rpc_calls == 0 and h.gets() == []


def test_product_denial_is_a_denied_body_with_zero_rpc(world):
    h = world
    h.state.row = dict(tier="pro", features=["site_full"], status="active")
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.json() == {"status": "unavailable", "reason": "product_unavailable"}
    assert h.state.auth_calls == 2 and h.state.rpc_calls == 0 and h.gets() == []


def test_unlimited_tier_and_operator_overlay_use_the_same_readers(world):
    h = world
    h.state.rpc_responses = [h.row(), h.row()]
    h.state.row = dict(tier=" unlimited ", features=[], status="active")
    assert h.post(h.client(), h.resolve_payload(), token_value=token()).json()["status"] == \
        "resolved"
    h.trace.clear()
    h.state.row = None
    h.state.operator = True
    h.state.rpc_responses = [h.row(), h.row()]
    assert h.post(h.client(), h.resolve_payload(), token_value=token()).json()["status"] == \
        "resolved"


# ---------------------------------------------------------------------------
# RLS ingress: exact owner revision / grant recipient / honest not_found
# ---------------------------------------------------------------------------


def test_owner_revision_is_exact_and_absent_revision_is_not_found(world):
    h = world
    h.state.rpc_responses = [None]
    response = h.post(h.client(), h.resolve_payload(revision=5), token_value=token())
    assert response.json() == {"status": "not_found"}
    assert h.state.rpc_bodies[0] == {"p_id": INV, "p_revision": 5}
    assert h.gets() == []


@pytest.mark.parametrize("row_extra", [
    {"status": "archived"},
    {"revoked_at": "2026-10-23T00:00:00Z"},
    {"grant_id": GRANT},  # an owner read must never be a grant-bound row
    {"scenario_capture": None},
])
def test_nonlive_owner_rows_are_honestly_not_found(world, row_extra):
    h = world
    h.state.rpc_responses = [h.row(**row_extra)]
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.json() == {"status": "not_found"}
    assert h.gets() == []


def test_foreign_or_mismatched_row_identity_is_not_found(world):
    h = world
    h.state.rpc_responses = [h.row(inv=INV_B)]
    assert h.post(h.client(), h.resolve_payload(), token_value=token()).json() == \
        {"status": "not_found"}
    h.trace.clear()
    h.state.rpc_responses = [h.row(revision=9)]
    assert h.post(h.client(), h.resolve_payload(), token_value=token()).json() == \
        {"status": "not_found"}
    assert h.gets() == []


def test_recipient_grant_uses_the_handoff_view_with_same_token(world):
    h = world
    row = h.handoff()
    h.state.rpc_responses = [row, row]
    response = h.post(h.client(), h.resolve_payload(grant=GRANT), token_value=token())
    body = response.json()
    assert body["status"] == "resolved" and body["grant_id"] == GRANT
    assert h.state.rpc_urls == [f"{URL}/rest/v1/rpc/read_investigation_handoff_v1"] * 2
    assert h.state.rpc_bodies == [{"p_grant_id": GRANT}] * 2
    assert h.state.rpc_headers[0]["authorization"] == "Bearer " + token()


@pytest.mark.parametrize("row_extra", [{"id": INV_B}, {"revision": 2},
                                       {"grant_id": OP},
                                       {"revoked_at": "2026-10-23T00:00:00Z"}])
def test_stale_or_foreign_grant_rows_are_not_found(world, row_extra):
    h = world
    row = h.handoff(**row_extra)
    h.state.rpc_responses = [row]
    assert h.post(h.client(), h.resolve_payload(grant=GRANT),
                  token_value=token()).json() == {"status": "not_found"}
    assert h.gets() == []


def test_wire_cannot_override_identity_or_read_absent_fields(world):
    h = world
    # Extra and missing keys, wrong types and uppercase uuids all refuse.
    assert h.post(h.client(), {**h.resolve_payload(), "source": "override"},
                  token_value=token()).json()["reason"] == "request_invalid"
    assert h.post(h.client(), {k: v for k, v in h.resolve_payload().items()
                               if k != "grant_id"},
                  token_value=token()).json()["reason"] == "request_invalid"
    assert h.post(h.client(), h.resolve_payload(revision="4"),
                  token_value=token()).json()["reason"] == "request_invalid"
    assert h.post(h.client(), h.resolve_payload(revision=True),
                  token_value=token()).json()["reason"] == "request_invalid"
    assert h.post(h.client(), h.resolve_payload(inv=INV.upper()),
                  token_value=token()).json()["reason"] == "request_invalid"
    assert h.post(h.client(), h.resolve_payload(grant="not-a-uuid"),
                  token_value=token()).json()["reason"] == "request_invalid"
    # Query parameters are never an authority: the body pins the revision.
    h.state.rpc_responses = [None]
    response = h.post(h.client(), h.resolve_payload(revision=4),
                      token_value=token(), params={"revision": "1", "grant_id": GRANT})
    assert response.json() == {"status": "not_found"}
    assert h.state.rpc_bodies[-1] == {"p_id": INV, "p_revision": 4}


def test_rpc_outage_redirect_and_malformed_rows_are_typed_unavailable(world):
    h = world
    h.state.rpc_error = urllib.error.HTTPError(URL, 302, "redirect", {}, io.BytesIO(b""))
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.json() == {"status": "unavailable", "reason": "rpc_unavailable"}
    h.trace.clear()
    h.state.rpc_error = None
    h.state.rpc_responses = [urllib.error.HTTPError(URL, 500, "down", {}, None)]
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json()["reason"] == "rpc_unavailable"
    h.trace.clear()
    h.state.rpc_responses = [[h.row(), h.row()]]  # ambiguous multi-row answer
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json()["reason"] == "rpc_unavailable"


def test_rpc_redirects_are_never_followed_by_the_transport(world):
    handler = S._NoRedirect()
    assert handler.redirect_request(None, None, 302, "found", {},
                                    URL + "/elsewhere") is None
    assert handler.redirect_request(None, None, 301, "moved", {}, "http://x.invalid") is None


def test_bad_configured_origin_never_reaches_the_network(world, monkeypatch):
    h = world
    main = sys.modules["app.main"]
    monkeypatch.setattr(main, "SUPABASE_URL", "http://insecure-fixture.invalid")
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.json() == {"status": "unavailable",
                               "reason": "authentication_unavailable"}
    assert h.state.rpc_calls == 0 and h.gets() == []


# ---------------------------------------------------------------------------
# Native refusals over the route: mismatch, denial, revoke, actor change
# ---------------------------------------------------------------------------


def test_source_use_denied_and_unavailable_are_distinct_with_zero_reads(world):
    h = world
    for status, expected in (("denied", ("denied", "source_denied")),
                             ("unavailable", ("unavailable", "source_unavailable")),
                             ("raise", ("unavailable", "source_unavailable"))):
        h.trace.clear()
        h.source_status = status
        h.state.rpc_responses = [h.row()]
        body = h.post(h.client(), h.resolve_payload(), token_value=token()).json()
        assert (body["status"], body.get("reason")) == expected
        assert h.gets() == []
    h.source_status = "allowed"


def test_source_decision_binding_mismatch_never_reads(world):
    h = world
    h.source_overrides = {"sha256": "0" * 64}
    h.state.rpc_responses = [h.row()]
    body = h.post(h.client(), h.resolve_payload(), token_value=token()).json()
    assert body == {"status": "unavailable", "reason": "source_decision_invalid"}
    assert h.gets() == []
    h.source_overrides = {"action": "export"}  # the pinned action cannot drift
    h.state.rpc_responses = [h.row()]
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json()["reason"] == "source_decision_invalid"
    assert h.gets() == []


def test_destination_denied_unavailable_and_down_are_distinct(world):
    h = world
    h.destination_status = "denied"
    h.state.rpc_responses = [h.row()]
    body = h.post(h.client(), h.resolve_payload(), token_value=token()).json()
    assert body == {"status": "denied", "reason": "destination_denied"}
    assert h.gets() == []
    h.destination_status = "unknown"
    h.state.rpc_responses = [h.row()]
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json()["reason"] == "destination_unavailable"
    h.destination_raises = True
    h.state.rpc_responses = [h.row()]
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json()["reason"] == "destination_unavailable"
    assert h.gets() == []
    h.destination_raises = False
    h.destination_status = "qualified"


def test_resource_false_is_denied_and_none_is_unavailable_with_zero_reads(world):
    h = world
    h.resource_results = [False]
    h.state.rpc_responses = [h.row()]
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json() == {"status": "denied",
                                                  "reason": "resource_denied"}
    assert h.gets() == []
    h.resource_results = [None]
    h.state.rpc_responses = [h.row()]
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json()["reason"] == "resource_unavailable"
    assert h.gets() == []


def test_revocation_between_read_and_recheck_discards_the_result(world):
    h = world
    h.resource_results = [True, False]
    h.state.rpc_responses = [h.row(), h.row()]
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json() == {"status": "denied",
                                                  "reason": "resource_revoked"}
    assert len(h.gets()) == 2  # the read happened; nothing was emitted
    assert "by_strike" not in json.dumps(h.trace)


def test_current_viewer_change_after_read_is_denied(world):
    h = world
    h.state.rpc_responses = [h.row()]
    bindings_clock = h.clock
    client = h.client()
    h.app.state.options_scenario_source_bindings = S.SourceScenarioBindings(
        s3=h.s3, bucket=BUCKET, destination=h.destination_qualifier,
        resource_access=h.resource_access,
        source_use_decision=h.source_use_decision, clock=bindings_clock,
        current_viewer=lambda: ssr.ViewerIdentity("other-viewer", ISS, SID))
    body = h.post(client, h.resolve_payload(), token_value=token()).json()
    assert body == {"status": "denied", "reason": "current_actor_changed"}
    assert len(h.gets()) == 2
    # A failing current-viewer seam is unavailable, never a fabricated denial.
    h.trace.clear()
    h.state.rpc_responses = [h.row()]

    def broken():
        raise RuntimeError("seam down")

    h.app.state.options_scenario_source_bindings = S.SourceScenarioBindings(
        s3=h.s3, bucket=BUCKET, destination=h.destination_qualifier,
        resource_access=h.resource_access,
        source_use_decision=h.source_use_decision, clock=bindings_clock,
        current_viewer=broken)
    assert h.post(client, h.resolve_payload(),
                  token_value=token()).json()["reason"] == "resource_unavailable"


def test_post_read_authentication_uncertainty_withholds_bytes(world):
    h = world
    h.state.rpc_responses = [h.row(), h.row()]
    # The 4th auth observation is the post-read actor recheck.
    h.state.fail_auth_at = frozenset({4})
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.json() == {"status": "unavailable", "reason": "authentication_unavailable"}
    # The 5th is the post-read product authentication recheck; uncertainty cannot borrow.
    h.trace.clear()
    h.state.auth_calls = 0
    h.state.fail_auth_at = frozenset({5})
    h.state.rpc_responses = [h.row(), h.row()]
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json() == {"status": "unavailable",
                                                  "reason": "product_unavailable"}


def test_canonical_row_change_during_read_is_a_resource_revoke(world):
    h = world
    changed = h.row(capture=h.capture(basis_sha256=
                                      hashlib.sha256(b"revised").hexdigest()))
    h.state.rpc_responses = [h.row(), changed]
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json() == {"status": "denied",
                                                  "reason": "resource_revoked"}
    h.trace.clear()
    h.state.rpc_responses = [h.row(), None]  # removed mid-flight
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json()["reason"] == "resource_revoked"
    h.trace.clear()
    h.state.rpc_responses = [h.row(), urllib.error.HTTPError(URL, 500, "down", {}, None)]
    assert h.post(h.client(), h.resolve_payload(),
                  token_value=token()).json()["reason"] == "rpc_unavailable"


# ---------------------------------------------------------------------------
# Retained bytes: only exact verified bytes are ever emitted
# ---------------------------------------------------------------------------


def test_tampered_retained_bytes_are_never_emitted(world):
    h = world
    h.s3.objects[h.gex_ref.key] = gex_raw(spot=1.0)  # same schema, wrong bytes
    h.state.rpc_responses = [h.row(), h.row()]
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    body = response.json()
    assert body == {"status": "unavailable", "reason": "retained_unavailable"}
    assert "base64" not in response.text and "gex" not in body
    assert "by_strike" not in response.text


def test_native_binding_epoch_is_the_presented_caller_session(world):
    # The session binding seen by the native callbacks is the auth_epoch of
    # the exact token presented on THIS request — never a cached or inferred
    # session. A different session claim yields a different binding.
    h = world
    other = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    h.state.rpc_responses = [h.row()]
    h.post(h.client(), h.resolve_payload(), token_value=token())
    assert h.seen_source_bindings[0]["auth_epoch"] == SID
    h.trace.clear()
    h.state.rpc_responses = [h.row()]
    h.post(h.client(), h.resolve_payload(), token_value=token(session_id=other))
    assert h.seen_source_bindings[-1]["auth_epoch"] == other


def test_missing_retained_object_is_typed_after_authorization(world):
    h = world
    del h.s3.objects[h.gex_ref.key]
    h.state.rpc_responses = [h.row()]
    body = h.post(h.client(), h.resolve_payload(), token_value=token()).json()
    assert body == {"status": "unavailable", "reason": "retained_missing"}
    # Both callbacks and the destination seam qualified first; the revoke
    # recheck never ran.
    assert h.resource_calls == 1 and h.source_calls == 1 and h.destination_calls >= 2


def test_supplied_moves_absence_is_explicit_never_silent(world):
    h = world
    del h.s3.objects[h.moves_ref.key]
    h.state.rpc_responses = [h.row()]
    body = h.post(h.client(), h.resolve_payload(), token_value=token()).json()
    assert body == {"status": "unavailable", "reason": "retained_missing"}
    assert h.gets() == [h.gex_ref.key, h.moves_ref.key]


def test_response_is_private_bounded_and_leaks_nothing(world):
    h = world
    h.state.rpc_responses = [h.row(), h.row()]
    good = h.post(h.client(), h.resolve_payload(), token_value=token())
    text = good.text
    assert token() not in text and ANON not in text and "service_role" not in text
    assert "synthetic" not in text and "atm_iv" not in text and "13.71" not in text
    assert "policy-1" not in text and "expected_move" not in text
    h.state.rpc_responses = [None]
    denial = h.post(h.client(), h.resolve_payload(revision=99), token_value=token())
    assert denial.text == '{"status":"not_found"}'
    assert token() not in denial.text
    error = h.post(h.client(), h.resolve_payload(revision="bad"), token_value=token())
    assert "Exception" not in error.text and "Traceback" not in error.text
    assert S._MAX_RESPONSE_BYTES == 13 * 1024 * 1024
    assert S._retention.MAX_GEX_BYTES == 8 * 1024 * 1024
    assert S._retention.MAX_MOVES_BYTES == 1024 * 1024


def test_not_found_success_body_is_exactly_the_private_shape(world):
    h = world
    h.state.rpc_responses = [None]
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.text == '{"status":"not_found"}'
    assert response.headers.get("Cache-Control") == "private, no-store"


# ---------------------------------------------------------------------------
# QUALIFY: deliberate pre-apply owner intent, canonical vs prospective
# ---------------------------------------------------------------------------


def test_qualify_create_labels_prospective_without_ownership_or_io(world):
    h = world
    h.state.rpc_responses = [None, None]  # prospective check before/after read
    response = h.post(h.client(), h.qualify_payload(expected=0), token_value=token())
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "mode", "investigation_id", "revision",
                         "grant_id", "capture", "gex", "moves"}
    assert body["status"] == "resolved" and body["mode"] == "qualify"
    assert body["revision"] == 1 and body["grant_id"] is None
    assert body["capture"] == h.capture()
    assert h.state.rpc_bodies == [{"p_id": INV, "p_revision": 1}] * 2
    assert h.gets() == [h.gex_ref.key, h.moves_ref.key]
    assert h.source_calls == 1
    binding = h.seen_source_bindings[0]
    assert binding["investigation_revision"] == 1 and binding["grant_id"] is None
    assert binding["action"] == "evaluate"
    assert binding["model_version"] == "exposure-scenario/v1"
    assert binding["sha256"] == h.gex_ref.sha256
    assert binding["moves_ref"] == h.moves_ref.version_ref
    assert binding["evaluated_at"] == CAPTURED
    assert binding["lens"] == {"kind": "one", "exp": EXPIRY}


def test_qualify_create_with_existing_owned_row_is_a_conflict(world):
    h = world
    h.state.rpc_responses = [h.row(revision=1)]
    body = h.post(h.client(), h.qualify_payload(expected=0), token_value=token()).json()
    assert body == {"status": "denied", "reason": "revision_conflict"}
    assert h.gets() == [] and h.destination_calls == 0


def test_qualify_revise_requires_owned_current_head(world):
    h = world
    h.state.rpc_responses = [h.row(revision=4), None, h.row(revision=4), None]
    body = h.post(h.client(), h.qualify_payload(expected=4), token_value=token()).json()
    assert body["status"] == "resolved" and body["mode"] == "qualify"
    assert body["revision"] == 5 and body["grant_id"] is None
    assert [b["p_revision"] for b in h.state.rpc_bodies] == [4, 5, 4, 5]
    assert h.gets() == [h.gex_ref.key, h.moves_ref.key]
    # Not the owner's current head: an existing next revision is a conflict.
    h.trace.clear()
    h.state.rpc_responses = [h.row(revision=4), h.row(revision=5)]
    assert h.post(h.client(), h.qualify_payload(expected=4),
                  token_value=token()).json() == {"status": "denied",
                                                  "reason": "revision_conflict"}
    # No owned active row at the expected revision: honestly not_found.
    h.trace.clear()
    h.state.rpc_responses = [None]
    assert h.post(h.client(), h.qualify_payload(expected=4),
                  token_value=token()).json() == {"status": "not_found"}
    assert h.gets() == []


def test_qualify_revise_with_zero_expected_never_claims_ownership(world):
    # A foreign same-UUID row hidden by RLS reads as not_found here; the label
    # stays PROSPECTIVE_CREATE and only the actual canonical apply can fail.
    h = world
    h.state.rpc_responses = [None, None]
    body = h.post(h.client(), h.qualify_payload(expected=0), token_value=token()).json()
    assert body["status"] == "resolved" and body["mode"] == "qualify"
    assert "owner" not in body


def test_qualify_grant_authority_is_not_accepted(world):
    h = world
    payload = h.qualify_payload(expected=0)
    payload["grant_id"] = GRANT
    assert h.post(h.client(), payload, token_value=token()).json()["reason"] == \
        "request_invalid"
    assert h.state.rpc_calls == 0 and h.gets() == []


def test_qualify_wire_must_be_the_closed_union(world):
    h = world
    base = h.qualify_payload(expected=0)
    assert h.post(h.client(), {**base, "extra": 1},
                  token_value=token()).json()["reason"] == "request_invalid"
    assert h.post(h.client(), {k: v for k, v in base.items() if k != "operation_id"},
                  token_value=token()).json()["reason"] == "request_invalid"
    assert h.post(h.client(), {**base, "operation_id": "not-a-uuid"},
                  token_value=token()).json()["reason"] == "request_invalid"
    mismatch = h.qualify_payload(expected=4, revision=9)
    assert h.post(h.client(), mismatch,
                  token_value=token()).json()["reason"] == "request_invalid"
    assert h.post(h.client(), {**base, "expected_revision": -1},
                  token_value=token()).json()["reason"] == "request_invalid"
    assert h.state.rpc_calls == 0 and h.state.auth_calls == 0


def test_qualify_source_decision_denial_and_echo_mismatch(world):
    h = world
    h.source_status = "denied"
    h.state.rpc_responses = [None]
    assert h.post(h.client(), h.qualify_payload(expected=0),
                  token_value=token()).json() == {"status": "denied",
                                                  "reason": "source_denied"}
    assert h.gets() == []
    h.source_status = "allowed"
    h.source_overrides = {"selection_key": "2026-12-19|2026-12-19T16:00:00-05:00"}
    h.state.rpc_responses = [None]
    assert h.post(h.client(), h.qualify_payload(expected=0),
                  token_value=token()).json()["reason"] == "source_decision_invalid"
    h.source_overrides = {"decided_at": "2020-01-01T00:00:00Z"}  # outside window
    h.state.rpc_responses = [None]
    assert h.post(h.client(), h.qualify_payload(expected=0),
                  token_value=token()).json()["reason"] == "source_decision_invalid"
    assert h.gets() == []


def test_qualify_destination_must_qualify_before_any_thing_else(world):
    h = world
    h.destination_status = "denied"
    h.state.rpc_responses = [None]
    assert h.post(h.client(), h.qualify_payload(expected=0),
                  token_value=token()).json() == {"status": "denied",
                                                  "reason": "destination_denied"}
    h.destination_status = "unknown"
    h.state.rpc_responses = [None]
    assert h.post(h.client(), h.qualify_payload(expected=0),
                  token_value=token()).json()["reason"] == "destination_unavailable"
    assert h.gets() == [] and h.source_calls == 2


def test_qualify_with_default_native_clock_uses_the_real_window(world):
    h = world
    h.state.rpc_responses = [None, None]
    h.state.decided_at = "now"  # decided inside the observed real-clock window
    app = FastAPI()
    app.include_router(S.router)
    app.state.options_scenario_source_bindings = S.SourceScenarioBindings(
        s3=h.s3, bucket=BUCKET, destination=h.destination_qualifier,
        resource_access=h.resource_access, source_use_decision=h.source_use_decision)
    body = h.post(TestClient(app), h.qualify_payload(expected=0),
                  token_value=token()).json()
    assert body["status"] == "resolved" and body["mode"] == "qualify"


# ---------------------------------------------------------------------------
# Strict capture validation on the untrusted browser wire
# ---------------------------------------------------------------------------


def _qualify_with_capture(h, capture):
    h.state.rpc_responses = [None, None]
    return h.post(h.client(), h.qualify_payload(expected=0, capture=capture),
                  token_value=token()).json()


def test_untrusted_capture_strictness_refuses_before_any_io(world):
    h = world
    assert _qualify_with_capture(h, h.capture(model_version="exposure-scenario/v0")) \
        == {"status": "unavailable", "reason": "capture_invalid"}
    assert _qualify_with_capture(
        h, {**h.capture(), "basis": {"gexMn": -1.0}})["reason"] == "capture_invalid"
    assert _qualify_with_capture(
        h, {**h.capture(), "result": {"value": 1.0}})["reason"] == "capture_invalid"
    assert _qualify_with_capture(h, h.capture(lens="week"))["reason"] == "capture_invalid"
    assert _qualify_with_capture(
        h, h.capture(lens={"kind": "one", "exp": EXPIRY},
                     selection_key=f"{EXPIRY}|{ECONOMIC},2026-12-19|2026-12-19T16:00:00-05:00")
    )["reason"] == "capture_invalid"
    assert _qualify_with_capture(
        h, h.capture(selection_key=f"2026-12-19|2026-12-19T16:00:00-05:00,{EXPIRY}|{ECONOMIC}")
    )["reason"] == "capture_invalid"
    assert _qualify_with_capture(
        h, h.capture(evaluated_at="2026-10-22 20:15:00"))["reason"] == "capture_invalid"
    assert _qualify_with_capture(
        h, h.capture(selection_key=f"2026-10-01|{ECONOMIC}"))["reason"] == "capture_invalid"
    assert _qualify_with_capture(h, h.capture(owner="options_structure.matrix"))[
        "reason"] == "capture_invalid"
    assert _qualify_with_capture(
        h, h.capture(gex={"sha256": "z" * 64, "byte_length": 10}))["reason"] == \
        "capture_invalid"
    float_length = h.capture()
    float_length["source"]["gex"] = {"sha256": h.gex_ref.sha256, "byte_length": 4096.0}
    assert S._parse_capture(float_length) is not None
    assert h.state.rpc_calls == 0 and h.state.auth_calls == 0 and h.gets() == []


def test_untrusted_capture_nanosecond_clocks_and_multi_expiry_week_qualify(world):
    h = world
    nano = h.capture(evaluated_at="2026-10-22t20:15:00.123456789z",
                     selection_key=f"{EXPIRY}|2026-12-18t16:00:00.5-05:00")
    body = _qualify_with_capture(h, nano)
    assert body["status"] == "resolved"
    assert body["capture"]["source"]["evaluated_at"] == "2026-10-22t20:15:00.123456789z"
    week = h.capture(lens={"kind": "week"},
                     selection_key=f"{EXPIRY}|{ECONOMIC},2026-12-19|2026-12-19T16:00:00-05:00")
    body = _qualify_with_capture(h, week)
    assert body["status"] == "resolved"
    assert body["capture"]["source"]["lens"] == {"kind": "week"}
    zero = h.capture(lens={"kind": "zero"},
                     selection_key=f"{SESSION}|{SESSION}T20:00:00Z")
    assert _qualify_with_capture(h, zero)["status"] == "resolved"
    bad_zero = h.capture(lens={"kind": "zero"},
                         selection_key=f"{SESSION}|{SESSION}T20:00:00Z,{EXPIRY}|{ECONOMIC}")
    assert _qualify_with_capture(h, bad_zero)["reason"] == "capture_invalid"
    assert h.gets() == [h.gex_ref.key, h.moves_ref.key] * 3


def test_native_route_rejects_invalid_capture_contract_before_authority(world):
    # The canonical save/parser is Terminal TypeScript/SQL, not a Python api
    # package. Enforce these wire vectors against the actual Macro parser and
    # mounted route; cross-project parity is qualified by the joined tests.
    h = world
    good = h.capture()
    assert S._parse_capture(good) is not None
    for mutate in (
        lambda c: {**c, "schema": "investigation_scenario_reference.v0"},
        lambda c: {**c, "inputs": {**c["inputs"], "targetSpot": 0}},
        lambda c: {**c, "inputs": {**c["inputs"], "deltaSigmaPts": 9}},
        lambda c: {**c, "inputs": {**c["inputs"], "days": 6}},
        lambda c: {**c, "source": {**c["source"], "root": "spy"}},
        lambda c: {**c, "source": {**c["source"], "root": "SPY_XY_ZW"}},
        lambda c: {**c, "source": {**c["source"], "session": "2026-02-30"}},
        lambda c: {**c, "source": {**c["source"], "source_as_of": "2026-10-23"}},
        lambda c: {**c, "source": {**c["source"],
                                   "source_as_of": "2026-10-22T21:15:00-05:00"}},
        lambda c: {**c, "source": {**c["source"], "basis_sha256": "B" * 64}},
        lambda c: {**c, "source": {**c["source"], "moves": {"sha256": "a" * 64}}},
        lambda c: {**c, "source": {**c["source"],
                                   "selection_key": f"{EXPIRY}|naive"}},
        lambda c: {**c, "source": {**c["source"], "lens": {"kind": "one"}}},
    ):
        mutated = mutate(good)
        assert S._parse_capture(mutated) is None, mutated
        assert _qualify_with_capture(h, mutated) == {
            "status": "unavailable", "reason": "capture_invalid"}, mutated
    assert h.state.rpc_calls == 0 and h.state.auth_calls == 0 and h.gets() == []
    # JSON integral numbers share the canonical JS/SQL semantics; the native
    # SnapshotReference receives the normalized Python integer.
    float_length = h.capture()
    float_length["source"]["gex"] = {"sha256": h.gex_ref.sha256,
                                     "byte_length": 4096.0}
    assert S._parse_capture(float_length) is not None


# ---------------------------------------------------------------------------
# The binding cannot be set, env-provided or defaulted into existence
# ---------------------------------------------------------------------------


def test_malformed_duplicate_key_and_oversize_bodies_never_touch_authority(world):
    h = world
    client = h.client()
    auth_headers = {"Content-Type": "application/json",
                    "Authorization": "Bearer " + token()}
    for body in (b"[1,2]", b'"resolve"', b"{", b"null",
                 b'{"mode":"resolve","mode":"resolve"}',
                 b"x" * (S._MAX_BODY_BYTES + 1)):
        response = client.post(S.ROUTE, content=body, headers=auth_headers)
        assert response.json() == {"status": "unavailable",
                                   "reason": "request_invalid"}, body[:40]
    assert h.state.auth_calls == 0 and h.state.rpc_calls == 0 and h.trace == []


def test_no_public_setter_no_env_fallback_and_unmounted_default():
    source = inspect.getsource(S)
    assert "environ" not in source
    assert not any(name.startswith("set_") for name in vars(S))
    assert not hasattr(S, "set_bindings") and not hasattr(S, "configure_bindings")
    assert S.SourceScenarioBindings() == S.SourceScenarioBindings()
    assert S.SourceScenarioBindings().s3 is None
    app = FastAPI()
    app.include_router(S.router)
    response = TestClient(app).post(S.ROUTE, json={
        "mode": "resolve", "investigation_id": INV, "revision": 1, "grant_id": None})
    assert response.json() == {"status": "unavailable",
                               "reason": "source_binding_unavailable"}


def test_route_is_mountable_and_post_only():
    app = FastAPI()
    app.include_router(S.router)
    client = TestClient(app)
    # The single registration line exposes exactly one private POST route that
    # answers in the typed vocabulary, never a framework error page.
    response = client.post(S.ROUTE, json={"mode": "resolve", "investigation_id": INV,
                                          "revision": 1, "grant_id": None})
    assert response.status_code == 200
    assert response.json() == {"status": "unavailable",
                               "reason": "source_binding_unavailable"}
    assert response.headers.get("Cache-Control") == "private, no-store"
    assert client.get(S.ROUTE).status_code == 405
    assert client.put(S.ROUTE, json={}).status_code == 405


def test_native_module_ownership_is_preserved_by_the_wrapper():
    # The wrapper composes the native resolver and retention library; it never
    # re-implements their logic or mints a parallel authority.
    source = inspect.getsource(S)
    assert "def resolve_scenario_source(" not in source.replace(
        "resolve_scenario_source_route", "")
    assert "get_object" not in source
    assert "hmac" not in source and "digestmod" not in source
    assert S._SOURCE_ACTION == "evaluate"
    assert S._MODEL_VERSION == ssr.MODEL_VERSION == "exposure-scenario/v1"

# Parent joined-boundary controls: these are actual canonical RPC wire shapes,
# not the worker's original flattened fixtures. All authorities remain controlled.
def test_joined_real_owner_rpc_envelope_and_private_bytes(world):
    h = world
    row = {"status": "found", "id": INV, "revision": 4, "current_revision": 4,
           "lifecycle": "active", "manifest": {"schema": "investigation_manifest.v2", "scenario_capture": h.capture()}}
    h.state.rpc_responses = [row, row]
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.json()["status"] == "resolved"
    assert response.headers["Cache-Control"] == "private, no-store"


def test_joined_qualify_reads_exact_protected_bytes_for_native_math(world):
    h = world
    h.state.rpc_responses = [{"status": "not_found"}] * 8
    body = h.post(h.client(), h.qualify_payload(expected=0), token_value=token()).json()
    assert body["status"] == "resolved"
    assert body["mode"] == "qualify"
    assert base64.b64decode(body["gex"]["base64"], validate=True) == h.gex_bytes
    assert h.gets() == [h.gex_ref.key, h.moves_ref.key]


def test_joined_recipient_actual_handoff_requires_explicit_pinned_capture(world):
    h = world
    h.state.rpc_responses = [h.handoff(), h.handoff()]
    body = h.post(h.client(), h.resolve_payload(grant=GRANT), token_value=token()).json()
    assert body["status"] == "resolved" and body["grant_id"] == GRANT
    h.trace.clear()
    no_capture = h.handoff()
    no_capture["handoff"].pop("scenario_capture")
    h.state.rpc_responses = [no_capture]
    assert h.post(h.client(), h.resolve_payload(grant=GRANT), token_value=token()).json() == {"status": "not_found"}
    assert h.gets() == []


def test_joined_whole_capture_change_after_read_withholds_bytes(world):
    h = world
    changed = h.capture()
    changed["inputs"]["days"] = 2
    h.state.rpc_responses = [h.row(), h.row(capture=changed)]
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.json() == {"status": "denied", "reason": "resource_revoked"}
    assert "base64" not in response.text


def test_joined_prospective_concurrent_revision_is_not_write_authority(world):
    h = world
    h.state.rpc_responses = [h.row(revision=4), {"status": "not_found"},
                             h.row(revision=4, current_revision=5)]
    response = h.post(h.client(), h.qualify_payload(expected=4), token_value=token())
    assert response.json() == {"status": "denied", "reason": "revision_conflict"}
    assert len(h.gets()) == 2 and "base64" not in response.text


def test_joined_billing_failure_is_unavailable_not_permission_denial(world, monkeypatch):
    h = world
    monkeypatch.setattr(billing, "read_entitlement", lambda _: (_ for _ in ()).throw(RuntimeError("private backend error")))
    response = h.post(h.client(), h.resolve_payload(), token_value=token())
    assert response.json() == {"status": "unavailable", "reason": "product_unavailable"}
    assert h.gets() == []
