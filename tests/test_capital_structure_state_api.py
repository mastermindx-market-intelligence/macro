"""Offline contract tests for the U1a Capital Structure state API (SPEC_U1_API §0 13-23, §25).

The state routes are a transport boundary over ONE published generation: they
answer what one issuer's registration state is as published tonight, or as it was
then known at an earlier cutoff, and every number they return is traceable to an
exact evidence span.  These tests pin that boundary -- entitlement before a read,
private/no-store responses, a server-normalized view identity, fail-closed
cutoffs, an unavailable or unbound bundle, the exact-span evidence route, the
then-known ticker resolver, coverage denominators, and no recommendation
vocabulary anywhere in a response.

The fixture is the producer lane's own: the integration suite's S-1 lifecycle for
issuer A, a later shelf filing that moves ticker ABC to issuer B, and a second
issuer-A shelf whose only event arrives after the then-known cutoff.  The
projection is built by the real builder so the API's own validation accepts it.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from pathlib import Path
from typing import Any, NamedTuple

import pytest

pytest.importorskip("fastapi", reason="capital structure API tests need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import capital_structure as api  # noqa: E402
from engine.capital_structure.issuer_state_contracts import (  # noqa: E402
    AUTHORITY,
    PROJECTION_COMPATIBILITY,
)
from engine.capital_structure.projection import build_projection_bundle  # noqa: E402
from engine.capital_structure.rule_applicability import (  # noqa: E402
    load_rule_applicability_pack,
)
from engine.capital_structure.state_bundle import (  # noqa: E402
    build_state_bundle,
    validate_state_bundle,
)
from engine.capital_structure.verified_projection_generation import (  # noqa: E402
    VerifiedProjectionGeneration,
)
from tests.test_build_capital_structure_projection import _manifest  # noqa: E402
from tests.test_capital_structure_api import _headers  # noqa: E402
from tests.test_capital_structure_registration_integration import (  # noqa: E402
    AS_OF,
    GENERATED_AT,
    _s1_filed_amended_effective_withdrawn,
)
from tests.test_capital_structure_registration_lifecycle import _event  # noqa: E402
from tests.test_capital_structure_state_bundle import (  # noqa: E402
    HEALTH,
    ISSUER_ONE,
    ISSUER_TWO,
    _family_record,
    _rewrite_json,
    _state_record,
    _telemetry,
)


PREFIX = "/api/capital-structure/v1"
TICKER = "ABC"

#: End of 2026-08-04 in New York.  Issuer A's EFFECT notice (2026-08-04T18:00:00Z)
#: is already house knowledge; its withdrawal (2026-08-05T18:00:00Z) and the whole
#: of its second shelf lifecycle (2026-08-06T12:00:00Z) are not.
CUTOFF_DAY = "2026-08-04"
CUTOFF_INSTANT = "2026-08-05T03:59:59Z"
#: After issuer A's first observation and before issuer B takes the ticker over.
HOLDER_DAY = "2026-08-05"
#: After issuer B's first observation of the same ticker.
REASSIGNED_DAY = "2026-08-07"
STATE_GENERATED_AT = "2026-10-14T07:00:00Z"
LATER_PROJECTION_AT = "2026-10-14T06:30:00Z"
_STATE_UNAVAILABLE = "capital structure state unavailable"
_STATE_NOT_BOUND = "state generation does not bind served projection"

_FORBIDDEN = re.compile(r"\b(should|probability|score|rank|target|buy|sell)\b", re.I)
_SEC_ORIGIN = "https://www.sec.gov"


@pytest.fixture(scope="module")
def pack():
    return load_rule_applicability_pack()


def _fixture_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Issuer A's S-1 lifecycle, issuer B's later shelf, and A's late shelf."""
    events, edges = _s1_filed_amended_effective_withdrawn()
    events.append(
        _event(
            61,
            "S-3",
            accepted_at="2026-08-06T10:00:00Z",
            seen_at="2026-08-06T18:00:00Z",
            issuer_id=ISSUER_TWO,
            cik="2",
            ticker=TICKER,
            file_number="333-777",
        )
    )
    events.append(
        _event(
            71,
            "S-3",
            accepted_at="2026-08-06T09:00:00Z",
            seen_at="2026-08-06T12:00:00Z",
            file_number="333-999",
        )
    )
    return events, list(edges)


def _write_json(path: Path, value: Any) -> str:
    body = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.write_text(body, encoding="utf-8")
    return body


class _Built(NamedTuple):
    """The pristine module-scoped artifacts every test copies from."""

    events: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    generation: VerifiedProjectionGeneration
    projection: dict[str, Any]
    bundle: dict[str, Any]
    projection_body: str
    state_body: str
    manifest_id: str
    span_id: str

    @property
    def evidence_key(self) -> str:
        return f"{self.manifest_id}/{self.span_id}"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory, pack) -> _Built:
    root = tmp_path_factory.mktemp("cs-v2-u1a-state-api")
    events, edges = _fixture_rows()
    telemetry = _telemetry(events, edges)
    telemetry["counts"] = {
        "event_versions": len(events),
        "event_edges": len(edges),
        "review_queue": 0,
    }
    generation = VerifiedProjectionGeneration(tuple(events), tuple(edges), (), telemetry)
    projection = build_projection_bundle(
        list(events), list(edges), (), telemetry, as_of=AS_OF, generated_at=GENERATED_AT
    )
    projection_body = _write_json(root / "projection.json", projection)
    first = events[0]["evidence"][0]
    row = _manifest(role="primary")
    resolved_row = {
        **row,
        "manifest_id": first["manifest_id"],
        "spans": [
            {
                **row["spans"][0],
                "span_id": first["span_id"],
                "text_sha256": first["text_sha256"],
            }
        ],
    }
    bundle = build_state_bundle(
        generation=generation,
        projection=projection,
        health=HEALTH,
        rule_pack=pack,
        as_of=AS_OF,
        generated_at=STATE_GENERATED_AT,
        projection_sha256=hashlib.sha256(projection_body.encode("utf-8")).hexdigest(),
        source_manifests=(resolved_row,),
    )
    validate_state_bundle(bundle)
    state_body = _write_json(root / "state_bundle.json", bundle)
    return _Built(
        events=events,
        edges=edges,
        generation=generation,
        projection=projection,
        bundle=bundle,
        projection_body=projection_body,
        state_body=state_body,
        manifest_id=str(first["manifest_id"]),
        span_id=str(first["span_id"]),
    )


class _Served(NamedTuple):
    """One test's own writable copy of the served artifacts, wired into the router."""

    built: _Built
    projection_path: Path
    state_path: Path
    generation_calls: dict[str, int]

    @property
    def bundle(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    @property
    def projection(self) -> dict[str, Any]:
        return json.loads(self.projection_path.read_text(encoding="utf-8"))

    @property
    def evidence_url(self) -> str:
        return f"{PREFIX}/issuers/{ISSUER_ONE}/evidence/{self.built.manifest_id}/{self.built.span_id}"

    def state_routes(self) -> tuple[str, ...]:
        return (
            f"{PREFIX}/issuers/{ISSUER_ONE}/state",
            f"{PREFIX}/issuers/{ISSUER_ONE}/state?mode=then_known&cutoff={CUTOFF_DAY}",
            f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration",
            f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration"
            f"?mode=then_known&cutoff={CUTOFF_DAY}",
            self.evidence_url,
            f"{PREFIX}/issuers/resolve?ticker={TICKER}&as_of={HOLDER_DAY}",
        )

    def reset(self) -> None:
        api._reset_cache()
        api._reset_state_cache()


@pytest.fixture()
def served(
    built: _Built, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> _Served:
    projection_path = tmp_path / "projection.json"
    state_path = tmp_path / "state_bundle.json"
    projection_path.write_text(built.projection_body, encoding="utf-8")
    state_path.write_text(built.state_body, encoding="utf-8")
    monkeypatch.setattr(api, "PROJECTION_PATH", projection_path)
    monkeypatch.setattr(api, "STATE_PATH", state_path)
    calls = {"generation": 0}
    generation = built.generation

    def counting_generation():
        calls["generation"] += 1
        return generation

    monkeypatch.setattr(api, "_load_generation", counting_generation)
    api._reset_cache()
    api._reset_state_cache()
    yield _Served(built, projection_path, state_path, calls)
    api._reset_cache()
    api._reset_state_cache()


@pytest.fixture()
def client(served: _Served):
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(app) as test_client:
        yield test_client


def _shift(instant: str, **units: int) -> str:
    """Move a published instant by whole units, staying in its own UTC form."""
    moment = datetime.fromisoformat(instant.replace("Z", "+00:00")) + timedelta(**units)
    return moment.astimezone(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + "Z"


def _earliest_bound(built: _Built, issuer_id: str) -> str:
    return min(
        str(event["point_in_time"]["available_at"])
        for event in built.events
        if event["issuer"]["issuer_id"] == issuer_id
    )


def _detail(response) -> Any:
    return response.json()["detail"]


def _without_excerpt(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _without_excerpt(item) for key, item in value.items() if key != "excerpt"}
    if isinstance(value, list):
        return [_without_excerpt(item) for item in value]
    return value


def _deny_site_full(monkeypatch: pytest.MonkeyPatch) -> None:
    """The existing denial shape: an entitled-only surface refusing a free user."""
    import app.main as main_mod
    import app.paywall as paywall_mod

    monkeypatch.setattr(main_mod, "require_user", lambda _authorization: {"id": "u-free"})

    def deny(_user, *, always=False):
        assert always is True
        raise HTTPException(403, {"locked": True, "required_feature": "site_full"})

    monkeypatch.setattr(paywall_mod, "enforce_site_full", deny)


def _bare_client() -> TestClient:
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Gate 13 — entitlement before any read
# ---------------------------------------------------------------------------


def test_u1_state_routes_require_entitlement_before_any_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _deny_site_full(monkeypatch)

    def refuse(reader: str):
        def _refuse(*_args, **_kwargs):
            raise AssertionError(f"{reader} must follow entitlement")

        return _refuse

    for reader in ("_load", "_load_state", "_load_generation"):
        monkeypatch.setattr(api, reader, refuse(reader))

    urls = (
        f"{PREFIX}/issuers/{ISSUER_ONE}/state",
        f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration",
        f"{PREFIX}/issuers/{ISSUER_ONE}/evidence/manifest:1/span:1",
        f"{PREFIX}/issuers/resolve?ticker={TICKER}&as_of={HOLDER_DAY}",
        f"{PREFIX}/coverage",
    )
    with _bare_client() as test_client:
        for url in urls:
            response = test_client.get(
                url, headers={"Authorization": "Bearer signed-in-free-user"}
            )
            assert response.status_code == 403, url
            _headers(response)
            assert _detail(response)["required_feature"] == "site_full"


# ---------------------------------------------------------------------------
# Gate 14 — private, no-store on success and on error
# ---------------------------------------------------------------------------


def test_u1_state_responses_are_private_no_store(client: TestClient, served: _Served) -> None:
    for url in (*served.state_routes(), f"{PREFIX}/coverage"):
        response = client.get(url)
        assert response.status_code == 200, (url, response.text[:300])
        _headers(response)

    errors = (
        f"{PREFIX}/issuers/{ISSUER_ONE}/state?mode=scenario",
        f"{PREFIX}/issuers/{ISSUER_ONE}/state?mode=then_known",
        f"{PREFIX}/issuers/{ISSUER_ONE}/state?clock=atomic",
        f"{PREFIX}/issuers/not-an-issuer/state",
        f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration?cursor=not-a-cursor",
        f"{PREFIX}/issuers/{ISSUER_ONE}/evidence/not-a-manifest/not-a-span",
        f"{PREFIX}/issuers/resolve?ticker={TICKER}&as_of=not-a-date",
    )
    for url in errors:
        response = client.get(url)
        assert response.status_code in (400, 404), (url, response.status_code)
        _headers(response)


# ---------------------------------------------------------------------------
# Gate 15 — the response echoes the request's view identity
# ---------------------------------------------------------------------------


def test_u1_response_echoes_the_request_view_identity(
    client: TestClient, served: _Served
) -> None:
    bundle = served.built.bundle
    published = _state_record(bundle, ISSUER_ONE)

    current = client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/state")
    assert current.status_code == 200
    body = current.json()
    assert body["view"] == {
        "mode": "current",
        "as_of": bundle["as_of"],
        "clock": "system",
        "state_id": published["state_id"],
        "generation_id": bundle["generation_id"],
        "scenario_id": None,
    }
    assert body["compatibility"] == PROJECTION_COMPATIBILITY
    assert body["authority"] == AUTHORITY
    assert body["not_yet_observed"] == []
    assert body["horizons"] == bundle["horizons"]

    derived = client.get(
        f"{PREFIX}/issuers/{ISSUER_ONE}/state?mode=then_known&cutoff={CUTOFF_DAY}"
    )
    assert derived.status_code == 200
    derived_body = derived.json()
    view = derived_body["view"]
    assert view["as_of"] == CUTOFF_INSTANT
    assert view["as_of"] == api._normalize_instant(CUTOFF_DAY, "cutoff")
    assert view["mode"] == "then_known"
    assert view["clock"] == "system"
    assert view["generation_id"] == bundle["generation_id"]
    assert view["state_id"] != published["state_id"]
    assert view["scenario_id"] is None
    assert derived_body["compatibility"] == PROJECTION_COMPATIBILITY
    assert derived_body["authority"] == AUTHORITY

    pending = derived_body["not_yet_observed"]
    assert len(pending) == 1
    assert set(pending[0]) == {"path_id", "lifecycle_id", "first_available_at", "status"}
    assert pending[0]["status"] == "unknown_at_date"
    assert pending[0]["first_available_at"] == "2026-08-06T12:00:00Z"
    late = next(
        row
        for row in _family_record(bundle, ISSUER_ONE)["records"]
        if row["lifecycle_id"] == pending[0]["lifecycle_id"]
    )
    assert pending[0]["path_id"] == late["path_id"]
    assert len(derived_body["families"]["registration"]["records"]) == 1
    assert len(body["families"]["registration"]["records"]) == 2

    offset = client.get(
        f"{PREFIX}/issuers/{ISSUER_ONE}/state"
        "?mode=then_known&cutoff=2026-08-04T12:00:00-04:00"
    )
    assert offset.status_code == 200
    assert offset.json()["view"]["as_of"] == "2026-08-04T16:00:00Z"


# ---------------------------------------------------------------------------
# Gate 16 — cutoff parsing fails closed
# ---------------------------------------------------------------------------


def test_u1_cutoff_parsing_fails_closed(client: TestClient, served: _Served) -> None:
    bundle = served.built.bundle
    after_generation = _shift(bundle["as_of"], days=1)
    before_first = _shift(_earliest_bound(served.built, ISSUER_ONE), seconds=-1)
    cases = (
        ("not-a-date", "not_iso8601"),
        ("2026-08-04T12:00:00", "not_iso8601"),
        ("2026-08-04T12:00:00.500Z", "not_iso8601"),
        (after_generation, "after_generation_as_of"),
        (before_first, "before_first_bound_event"),
    )
    routes = (
        f"{PREFIX}/issuers/{ISSUER_ONE}/state",
        f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration",
    )
    for route in routes:
        for cutoff, reason in cases:
            response = client.get(f"{route}?mode=then_known&cutoff={cutoff}")
            assert response.status_code == 400, (route, cutoff, response.text[:300])
            assert _detail(response) == {
                "error": "invalid cutoff",
                "parameter": "cutoff",
                "reason": reason,
            }
            _headers(response)

        with_current = client.get(f"{route}?cutoff={CUTOFF_DAY}")
        assert with_current.status_code == 400
        assert _detail(with_current) == {
            "error": "invalid cutoff",
            "parameter": "cutoff",
            "reason": "only_with_then_known",
        }
        _headers(with_current)

        scenario = client.get(f"{route}?mode=scenario&cutoff={CUTOFF_DAY}")
        assert scenario.status_code == 400
        assert _detail(scenario) == {
            "error": "invalid mode",
            "parameter": "mode",
            "reason": "unsupported_mode",
        }
        _headers(scenario)


# ---------------------------------------------------------------------------
# Gate 17 — then_known requires a cutoff, and reads no generation without one
# ---------------------------------------------------------------------------


def test_u1_mode_then_known_requires_a_cutoff(client: TestClient, served: _Served) -> None:
    for route in (
        f"{PREFIX}/issuers/{ISSUER_ONE}/state",
        f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration",
    ):
        response = client.get(f"{route}?mode=then_known")
        assert response.status_code == 400
        assert _detail(response) == {
            "error": "cutoff required for then_known",
            "parameter": "cutoff",
            "reason": "missing",
        }
        _headers(response)
    assert served.generation_calls["generation"] == 0


# ---------------------------------------------------------------------------
# Gate 18 — an unavailable bundle fails closed while the projection keeps serving
# ---------------------------------------------------------------------------


def test_u1_unavailable_bundle_fails_closed_while_projection_keeps_serving(
    client: TestClient, served: _Served, monkeypatch: pytest.MonkeyPatch
) -> None:
    def drop_schema(value: dict[str, Any]) -> None:
        value["schema"] = "capital_structure.state_bundle.v9"

    def drop_a_capability(value: dict[str, Any]) -> None:
        value["unavailable"] = list(value["unavailable"])[1:]

    def assert_withheld() -> None:
        served.reset()
        for url in served.state_routes():
            response = client.get(url)
            assert response.status_code == 503, (url, response.text[:300])
            assert _detail(response) == _STATE_UNAVAILABLE
            _headers(response)
        for url in (f"{PREFIX}/issuers/{ISSUER_ONE}", f"{PREFIX}/overview"):
            assert client.get(url).status_code == 200, url
        coverage = client.get(f"{PREFIX}/coverage")
        assert coverage.status_code == 200
        _headers(coverage)
        assert coverage.json()["state"] == {
            "status": "unavailable",
            "reason": _STATE_UNAVAILABLE,
        }

    missing = served.state_path.parent / "absent_state_bundle.json"
    monkeypatch.setattr(api, "STATE_PATH", missing)
    assert_withheld()

    monkeypatch.setattr(api, "STATE_PATH", served.state_path)
    _rewrite_json(served.state_path, drop_schema)
    assert_withheld()

    served.state_path.write_text(served.built.state_body, encoding="utf-8")
    _rewrite_json(served.state_path, drop_a_capability)
    assert_withheld()


# ---------------------------------------------------------------------------
# Gate 19 — a bundle that does not bind the served projection is a read-time 503
# ---------------------------------------------------------------------------


def test_u1_bundle_projection_mismatch_is_503_at_read_time(
    client: TestClient, served: _Served
) -> None:
    built = served.built
    later = build_projection_bundle(
        list(built.events),
        list(built.edges),
        (),
        built.generation.telemetry,
        as_of=AS_OF,
        generated_at=LATER_PROJECTION_AT,
    )
    assert later["generation_id"] != built.projection["generation_id"]
    served.projection_path.write_text(
        json.dumps(later, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    served.reset()

    for url in served.state_routes():
        response = client.get(url)
        assert response.status_code == 503, (url, response.text[:300])
        assert _detail(response) == _STATE_NOT_BOUND
        _headers(response)
    assert client.get(f"{PREFIX}/issuers/{ISSUER_ONE}").status_code == 200
    coverage = client.get(f"{PREFIX}/coverage")
    assert coverage.status_code == 200
    assert coverage.json()["state"] == {"status": "unavailable", "reason": _STATE_NOT_BOUND}


# ---------------------------------------------------------------------------
# Gate 20 — the evidence route resolves the exact span or withholds
# ---------------------------------------------------------------------------


def test_u1_evidence_route_resolves_the_exact_span_or_withholds(
    client: TestClient, served: _Served
) -> None:
    bundle = served.built.bundle
    entry = bundle["evidence_index"][served.built.evidence_key]
    bodies: list[Any] = []

    response = client.get(served.evidence_url)
    assert response.status_code == 200, response.text[:400]
    body = response.json()
    bodies.append(body)
    _headers(response)
    assert body["manifest_id"] == entry["manifest_id"]
    assert body["span_id"] == entry["span_id"]
    assert body["text_sha256"] == entry["text_sha256"]
    assert body["filing"] == entry["filing"]
    assert body["document"] == entry["document"]
    assert body["anchor"] == entry["anchor"]
    assert body["reason"] is None
    assert body["grade"] == "public_source_link"
    assert body["available_at"] == entry["available_at"]
    assert body["input_generations"] == bundle["input_generations"]
    assert body["view"]["mode"] == "current"
    assert body["view"]["generation_id"] == bundle["generation_id"]
    assert body["compatibility"] == PROJECTION_COMPATIBILITY
    assert body["authority"] == AUTHORITY

    assert body["operands"]
    for operand in body["operands"]:
        assert set(operand) == {"name", "path_id", "value", "unit", "evidence"}
        assert operand["unit"] is None
        assert operand["evidence"] == {
            "manifest_id": entry["manifest_id"],
            "span_id": entry["span_id"],
            "text_sha256": entry["text_sha256"],
        }
    assert body["rule"] is None or set(body["rule"]) == {"rule_id", "class", "pack_version"}

    unknown = client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/evidence/not-a-manifest/not-a-span")
    assert unknown.status_code == 404
    assert _detail(unknown) == "evidence not found"
    _headers(unknown)
    bodies.append(unknown.json())

    other = client.get(
        f"{PREFIX}/issuers/{ISSUER_TWO}/evidence/{served.built.manifest_id}/{served.built.span_id}"
    )
    assert other.status_code == 404
    assert _detail(other) == "evidence not found"
    _headers(other)
    bodies.append(other.json())

    def diverge(value: dict[str, Any]) -> None:
        value["evidence_index"][served.built.evidence_key]["ledger_text_sha256"] = (
            hashlib.sha256(b"retained bytes the ledger no longer holds").hexdigest()
        )

    _rewrite_json(served.state_path, diverge)
    served.reset()
    mismatch = client.get(served.evidence_url)
    assert mismatch.status_code == 409
    assert _detail(mismatch) == "evidence hash mismatch"
    _headers(mismatch)
    bodies.append(mismatch.json())

    accession_digits = str(entry["filing"]["accession"]).replace("-", "")
    for position, candidate in enumerate(bodies):
        serialized = json.dumps(candidate, sort_keys=True)
        found = list(re.finditer(re.escape(_SEC_ORIGIN) + r'[^"\\]*', serialized))
        if position == 0:
            assert found, "the resolved span must carry its accession-specific anchor"
        for match in found:
            url = match.group(0)
            assert "/Archives/" in url, url
            assert accession_digits in url.replace("-", ""), url


# ---------------------------------------------------------------------------
# Gate 21 — retained text is never served without a grade and a grant
# ---------------------------------------------------------------------------


def test_u1_evidence_route_never_returns_retained_text_without_entitlement(
    client: TestClient, served: _Served, monkeypatch: pytest.MonkeyPatch
) -> None:
    retained = "Rule 415(a)(5) retains the exact cited sentence."
    calls = {"excerpt": 0}

    def hook(_entry: dict[str, Any]) -> str:
        calls["excerpt"] += 1
        return retained

    def set_grade(grade: str) -> None:
        def mutate(value: dict[str, Any]) -> None:
            value["evidence_index"][served.built.evidence_key]["grade"] = grade

        served.state_path.write_text(served.built.state_body, encoding="utf-8")
        _rewrite_json(served.state_path, mutate)
        served.reset()

    set_grade("excerpt_permitted")
    body = client.get(served.evidence_url).json()
    assert body["excerpt_status"] == "not_retained"
    assert "excerpt" not in body

    monkeypatch.setattr(api, "_retained_excerpt", hook)
    set_grade("internal_only")
    calls["excerpt"] = 0
    withheld = client.get(served.evidence_url)
    assert withheld.status_code == 200
    body = withheld.json()
    assert body["excerpt_status"] == "withheld"
    assert "excerpt" not in body
    assert calls["excerpt"] == 0

    set_grade("excerpt_permitted")
    calls["excerpt"] = 0
    permitted = client.get(served.evidence_url)
    assert permitted.status_code == 200
    body = permitted.json()
    assert body["excerpt_status"] == "present"
    assert body["excerpt"] == retained
    assert calls["excerpt"] == 1

    _deny_site_full(monkeypatch)
    calls["excerpt"] = 0
    with _bare_client() as bare:
        denied = bare.get(
            served.evidence_url, headers={"Authorization": "Bearer signed-in-free-user"}
        )
    assert denied.status_code == 403
    _headers(denied)
    assert calls["excerpt"] == 0


# ---------------------------------------------------------------------------
# Gate 22 — resolve accepts as_of and returns identity transitions
# ---------------------------------------------------------------------------


def test_u1_resolve_accepts_as_of_and_returns_identity_transitions(
    client: TestClient, served: _Served, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = served.built.bundle
    index = bundle["issuer_index"]
    first_a = index[ISSUER_ONE]["ticker_observations"][0]
    first_b = index[ISSUER_TWO]["ticker_observations"][0]
    projection = api._load()
    envelope = api._envelope(projection)

    def transition(row: dict[str, Any], issuer_id: str, previous: str | None) -> dict[str, Any]:
        return {
            "from": previous,
            "to": issuer_id,
            "effective": row["first_observed_at"],
            "evidence": {"event_id": row["event_id"], "accession": row["accession"]},
        }

    held = client.get(f"{PREFIX}/issuers/resolve?ticker={TICKER}&as_of={HOLDER_DAY}")
    assert held.status_code == 200, held.text[:400]
    body = held.json()
    _headers(held)
    assert body["issuer"] == api._overview_record(api._issuer(projection, ISSUER_ONE))
    assert body["identity_transitions"] == [transition(first_a, ISSUER_ONE, None)]
    assert body["query"]["ticker"] == TICKER
    assert body["query"]["as_of"] == body["view"]["as_of"]
    assert body["view"] == {
        "mode": "then_known",
        "as_of": api._normalize_instant(HOLDER_DAY, "as_of"),
        "clock": "system",
        "state_id": None,
        "generation_id": bundle["generation_id"],
        "scenario_id": None,
    }
    assert {key: body[key] for key in envelope} == envelope

    reassigned = client.get(f"{PREFIX}/issuers/resolve?ticker={TICKER}&as_of={REASSIGNED_DAY}")
    assert reassigned.status_code == 200
    body = reassigned.json()
    assert body["issuer"] == api._overview_record(api._issuer(projection, ISSUER_TWO))
    assert body["identity_transitions"] == [
        transition(first_a, ISSUER_ONE, None),
        transition(first_b, ISSUER_TWO, ISSUER_ONE),
    ]
    assert body["view"]["as_of"] == api._normalize_instant(REASSIGNED_DAY, "as_of")

    before = client.get(f"{PREFIX}/issuers/resolve?ticker={TICKER}&as_of=2026-07-01")
    assert before.status_code == 404
    assert _detail(before) == "ticker not covered"
    _headers(before)

    after = client.get(
        f"{PREFIX}/issuers/resolve?ticker={TICKER}&as_of={_shift(bundle['as_of'], days=1)}"
    )
    assert after.status_code == 400
    assert _detail(after) == {
        "error": "invalid as_of",
        "parameter": "as_of",
        "reason": "after_generation_as_of",
    }
    _headers(after)

    def refuse(*_args, **_kwargs):
        raise AssertionError("the state bundle must not be read without as_of")

    monkeypatch.setattr(api, "_load_state", refuse)
    served.reset()
    plain = client.get(f"{PREFIX}/issuers/resolve?ticker={TICKER}")
    assert plain.status_code == 409
    detail = _detail(plain)
    assert set(detail) == {"code", "ticker", "matches"}
    assert detail["code"] == "ambiguous_ticker"
    assert detail["ticker"] == TICKER
    assert detail["matches"] == [
        {"issuer_id": row["issuer_id"], "identity": row["identity"]}
        for row in api._records(projection)
        if TICKER
        in {
            str(row["identity"].get("ticker") or "").upper(),
            *(str(value).upper() for value in row["identity"].get("observed_tickers") or []),
        }
    ]
    _headers(plain)


# ---------------------------------------------------------------------------
# Gate 23 — coverage reports the state families with their denominators
# ---------------------------------------------------------------------------


def test_u1_coverage_reports_state_families_with_denominators(
    client: TestClient, served: _Served
) -> None:
    bundle = served.built.bundle
    response = client.get(f"{PREFIX}/coverage")
    assert response.status_code == 200
    _headers(response)
    body = response.json()
    envelope = api._envelope(api._load())
    assert {key: value for key, value in body.items() if key != "state"} == envelope

    state = body["state"]
    assert set(state) == {"status", "generation_id", "as_of", "families"}
    assert state["status"] == "available"
    assert state["generation_id"] == bundle["generation_id"]
    assert state["as_of"] == bundle["as_of"]
    assert set(state["families"]) == {"registration"}
    published = bundle["coverage"]["families"]["registration"]
    family = state["families"]["registration"]
    assert set(family) == {"support", "examined", "total", "unexamined_reason_codes"}
    assert family == {key: published[key] for key in family}
    assert family["support"] != "supported"
    assert family["examined"] <= family["total"]


# ---------------------------------------------------------------------------
# Gate 25 — no recommendation vocabulary in any state response
# ---------------------------------------------------------------------------


def test_u1_no_recommendation_vocabulary_in_any_state_response(
    client: TestClient, served: _Served
) -> None:
    bodies = []
    for url in (*served.state_routes(), f"{PREFIX}/coverage"):
        response = client.get(url)
        assert response.status_code == 200, (url, response.text[:300])
        bodies.append(response.json())
    assert len(bodies) == 7

    for row in api._records(api._load()):
        match = _FORBIDDEN.search(json.dumps(row["identity"], sort_keys=True))
        assert match is None, match.group(0) if match else ""

    for body in bodies:
        text = json.dumps(_without_excerpt(body), sort_keys=True)
        match = _FORBIDDEN.search(text)
        assert match is None, match.group(0) if match else ""


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


def test_u1_date_cutoff_normalizes_to_the_end_of_the_new_york_day() -> None:
    assert api._normalize_instant("2026-08-04", "cutoff") == "2026-08-05T03:59:59Z"
    assert api._normalize_instant("2026-12-04", "cutoff") == "2026-12-05T04:59:59Z"
    assert api._normalize_instant("2026-08-04T12:00:00Z", "cutoff") == "2026-08-04T12:00:00Z"
    assert api._normalize_instant("2026-08-04T12:00:00.000Z", "cutoff") == "2026-08-04T12:00:00Z"
    assert api._normalize_instant("2026-08-04T12:00:00-04:00", "cutoff") == "2026-08-04T16:00:00Z"
    for value in ("2026-08-04T12:00:00", "2026-08-04T12:00:00.500Z", "not-a-date", "2026-13-01"):
        with pytest.raises(HTTPException) as caught:
            api._normalize_instant(value, "cutoff")
        assert caught.value.status_code == 400
        assert caught.value.detail == {
            "error": "invalid cutoff",
            "parameter": "cutoff",
            "reason": "not_iso8601",
        }
    with pytest.raises(HTTPException) as named:
        api._normalize_instant("not-a-date", "as_of")
    assert named.value.detail == {
        "error": "invalid as_of",
        "parameter": "as_of",
        "reason": "not_iso8601",
    }


def test_u1_public_clock_is_accepted_echoed_and_noted(
    client: TestClient, served: _Served
) -> None:
    current = client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/state?clock=public")
    assert current.status_code == 200
    body = current.json()
    assert body["view"]["clock"] == "public"
    assert body["view"]["clock_note"] == "public clock not separately modelled in this generation"
    assert body["view"]["mode"] == "current"

    derived = client.get(
        f"{PREFIX}/issuers/{ISSUER_ONE}/state"
        f"?mode=then_known&cutoff={CUTOFF_DAY}&clock=public"
    )
    assert derived.status_code == 200
    assert derived.json()["view"]["clock_note"] == body["view"]["clock_note"]
    assert derived.json()["not_yet_observed"] == (
        client.get(
            f"{PREFIX}/issuers/{ISSUER_ONE}/state?mode=then_known&cutoff={CUTOFF_DAY}"
        )
        .json()["not_yet_observed"]
    )

    system = client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/state")
    assert "clock_note" not in system.json()["view"]

    refused = client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/state?clock=atomic")
    assert refused.status_code == 400
    assert _detail(refused) == {
        "error": "invalid clock",
        "parameter": "clock",
        "reason": "unsupported_clock",
    }
    _headers(refused)


def test_u1_registration_paths_paginate_on_path_id(
    client: TestClient, served: _Served
) -> None:
    url = f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration"
    whole = client.get(url)
    assert whole.status_code == 200
    body = whole.json()
    assert body["page"] == {
        "cursor": None,
        "next_cursor": None,
        "limit": 25,
        "returned": 2,
        "total": 2,
    }
    assert [row["path_id"] for row in body["paths"]] == sorted(
        row["path_id"] for row in body["paths"]
    )
    assert "records" not in body["family"]
    family_record = _family_record(served.built.bundle, ISSUER_ONE)
    assert set(body["family"]) == set(family_record) - {"records"}
    assert body["coverage"] == served.built.bundle["issuer_index"][ISSUER_ONE]["coverage"]["registration"]

    first = client.get(f"{url}?limit=1")
    assert first.status_code == 200
    page = first.json()
    assert page["page"] == {
        "cursor": None,
        "next_cursor": page["paths"][0]["path_id"],
        "limit": 1,
        "returned": 1,
        "total": 2,
    }
    second = client.get(f"{url}?limit=1&cursor={page['page']['next_cursor']}")
    assert second.status_code == 200
    tail = second.json()
    assert tail["page"]["cursor"] == page["page"]["next_cursor"]
    assert tail["page"]["next_cursor"] is None
    assert tail["page"]["returned"] == 1
    assert [row["path_id"] for row in page["paths"]] + [
        row["path_id"] for row in tail["paths"]
    ] == [row["path_id"] for row in body["paths"]]

    unknown = client.get(f"{url}?cursor=not-a-path-id")
    assert unknown.status_code == 400
    assert _detail(unknown) == "invalid cursor"
    _headers(unknown)


def test_u1_every_path_carries_its_evidence_and_rule_status(
    client: TestClient, served: _Served, pack
) -> None:
    url = f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration"
    body = client.get(url).json()
    index = served.built.bundle["issuer_index"][ISSUER_ONE]["path_evidence"]
    evidence_index = served.built.bundle["evidence_index"]
    published = {
        str(row["path_id"]): row for row in _family_record(served.built.bundle, ISSUER_ONE)["records"]
    }
    as_of_day = body["view"]["as_of"][:10]
    assert as_of_day == served.built.bundle["as_of"][:10]
    for row in body["paths"]:
        assert row["evidence"] == [
            {
                "manifest_id": evidence_index[key]["manifest_id"],
                "span_id": evidence_index[key]["span_id"],
                "text_sha256": evidence_index[key]["text_sha256"],
            }
            for key in index[row["path_id"]]
        ]
        assert row["evidence"] == sorted(
            row["evidence"], key=lambda ref: (ref["manifest_id"], ref["span_id"])
        )
        cited = {
            str(rule_id)
            for predicate in published[row["path_id"]]["predicates"].values()
            for rule_id in predicate.get("rule_ids") or ()
        }
        assert set(row["rule_status"]) == cited
        for rule_id, status in row["rule_status"].items():
            assert status["rule_id"] == rule_id
            assert status["as_of"] == as_of_day
            assert status["state"] in ("verified", "bracketed", "beyond_window", "withheld", "not_in_force", None)


def test_u1_rule_status_names_a_rule_the_pack_does_not_carry(pack) -> None:
    absent = api._rule_status_for(pack, "cfr.17.999.not-in-the-pack", "2026-08-04")
    assert absent == {
        "rule_id": "cfr.17.999.not-in-the-pack",
        "as_of": "2026-08-04",
        "state": None,
        "window": None,
        "condition": "rule text not in the applicability pack",
    }
    known = api._rule_status_for(pack, "cfr.17.230.415.a.5", "2026-08-04")
    assert known["state"] is not None
    assert known["window"] is not None


def test_u1_then_known_at_the_bundle_as_of_matches_the_current_evidence(
    client: TestClient, served: _Served
) -> None:
    url = f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration"
    current = client.get(url).json()
    derived = client.get(f"{url}?mode=then_known&cutoff={served.built.bundle['as_of']}").json()
    assert derived["view"]["as_of"] == served.built.bundle["as_of"]
    assert derived["not_yet_observed"] == []
    assert derived["view"]["state_id"] != current["view"]["state_id"]
    assert derived["view"]["generation_id"] == current["view"]["generation_id"]
    assert len(derived["paths"]) == len(current["paths"]) == 2
    assert [row["path_id"] for row in derived["paths"]] == [
        row["path_id"] for row in current["paths"]
    ]
    by_lifecycle = {row["lifecycle_id"]: row for row in current["paths"]}
    for row in derived["paths"]:
        assert row["evidence"] == by_lifecycle[row["lifecycle_id"]]["evidence"]
        assert row["path_id"] == by_lifecycle[row["lifecycle_id"]]["path_id"]


def test_u1_state_route_refuses_an_issuer_the_bundle_does_not_carry(
    client: TestClient, served: _Served
) -> None:
    def drop(value: dict[str, Any]) -> None:
        value["issuers"] = [
            row for row in value["issuers"] if row["request"]["issuer_id"] != ISSUER_TWO
        ]
        value["issuer_index"].pop(ISSUER_TWO, None)

    _rewrite_json(served.state_path, drop)
    served.reset()
    for url in (
        f"{PREFIX}/issuers/{ISSUER_TWO}/state",
        f"{PREFIX}/issuers/{ISSUER_TWO}/state/registration",
    ):
        response = client.get(url)
        assert response.status_code == 404, url
        assert _detail(response) == "issuer not covered"
        _headers(response)
    assert client.get(f"{PREFIX}/issuers/{ISSUER_TWO}").status_code == 200
    assert client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/state").status_code == 200


def test_u1_then_known_reads_the_verified_generation_once_per_request(
    client: TestClient, served: _Served
) -> None:
    assert served.generation_calls["generation"] == 0
    assert client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/state").status_code == 200
    assert client.get(f"{PREFIX}/coverage").status_code == 200
    assert client.get(served.evidence_url).status_code == 200
    assert served.generation_calls["generation"] == 0
    assert (
        client.get(
            f"{PREFIX}/issuers/{ISSUER_ONE}/state?mode=then_known&cutoff={CUTOFF_DAY}"
        ).status_code
        == 200
    )
    assert served.generation_calls["generation"] == 1
