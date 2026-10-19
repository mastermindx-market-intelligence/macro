"""SPEC_U2 §2 gates 21-30: the U2-2 API lane over the private router.

The change desk, the saved-scenario save/list/restore/delete and the two exact
export routes are exercised THROUGH the FastAPI app with the U2-1 fake PostgREST
transport (imported, never copied), the U1a/U1B-2 fixtures (imported, never
copied) and the real producer for the published change ledger.  The second
state generation below is built by the real builders over the fixture world
plus one new issuer filing, so a ``new_event`` on the desk is a real diff.

Every response asserts through the U1B-2 shared helper (private, no-store, no
validators, no advisory vocabulary); 204 and the two attachments get the same
policy through the two shape-specific helpers.  No float literal anywhere; no
digest, id or generation is hard-coded.
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
from pathlib import Path
from typing import Any, NamedTuple

import pytest

pytest.importorskip("fastapi", reason="capital structure API tests need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import capital_structure as api  # noqa: E402
from engine.capital_structure import saved_scenario_store as store  # noqa: E402
from engine.capital_structure.issuer_state_contracts import (  # noqa: E402
    PriceAssumption,
)
from engine.capital_structure.saved_scenarios import (  # noqa: E402
    SavedScenario,
    result_digest_of,
)
from engine.capital_structure.scenario_inputs import CAPACITY_INPUTS_FILENAME  # noqa: E402
from engine.capital_structure.scenario_export import export_scenario_envelope  # noqa: E402
from engine.capital_structure.state_changes import CHANGE_KINDS  # noqa: E402
from engine.fundamental_forensics.query_exports import (  # noqa: E402
    CSV_MEDIA_TYPE,
    PARQUET_MEDIA_TYPE,
)
import tests.test_capital_structure_funding as F  # noqa: E402
import tests.test_capital_structure_saved_scenarios as contract_suite  # noqa: E402
import tests.test_capital_structure_scenario_inputs as inputs_suite  # noqa: E402
import tests.test_capital_structure_state_api as evaluate_suite  # noqa: E402
from scripts.build_capital_structure_state_changes import build_from_disk  # noqa: E402
from tests.test_capital_structure_registration_lifecycle import _event  # noqa: E402
from tests.test_capital_structure_saved_scenarios import (  # noqa: E402
    USER_ALPHA,
    USER_BETA,
    _FakePostgREST,
    _row_for,
)
from tests.test_capital_structure_saved_scenarios import composed  # noqa: F401,E402 — fixture below
from tests.test_capital_structure_state_api import (  # noqa: F401,E402 — fixtures below
    built,
    client,
    pack,
    served,
    with_inputs,
)

PREFIX = evaluate_suite.PREFIX
ISSUER_ONE = evaluate_suite.ISSUER_ONE
ISSUER_TWO = evaluate_suite.ISSUER_TWO
SAVED_LABEL = "u2 api lane fixture"
SAVED_PATH = f"{PREFIX}/issuers/{ISSUER_ONE}/scenarios/saved"
CHANGES_PATH = f"{PREFIX}/issuers/{ISSUER_ONE}/changes"
EVALUATE_EXPORT_PATH = f"{PREFIX}/issuers/{ISSUER_ONE}/scenarios/evaluate/export"
LEDGER_GENERATED_AT = "2026-10-19T08:00:00Z"
#: The second generation's stamp: the same as_of, published later the same day.
SECOND_GENERATED_AT = "2026-10-14T09:00:00Z"
_STATE_UNAVAILABLE = evaluate_suite._STATE_UNAVAILABLE
_INPUTS_UNAVAILABLE = evaluate_suite._INPUTS_UNAVAILABLE


def _client_for(user_id: str) -> TestClient:
    """A client authenticated as one specific entitled user."""
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": user_id}
    return TestClient(app)


class _PartitionedStore(_FakePostgREST):
    """The U2-1 canned fake, answering like the real store: only the rows the
    query's ``user_id=eq.`` names (a real PostgREST filter), so one store can
    hold every user's rows without tripping the adapter's partition alarm.
    Same recording, same canned failures — everything delegates to the fake."""

    def __call__(self, method: str, path: str, body: Any = None, prefer: str | None = None, timeout: int = 6) -> Any:
        rows = super().__call__(method, path, body=body, prefer=prefer, timeout=timeout)
        if isinstance(rows, list):
            for marker in path.split("&"):
                if marker.startswith("user_id=eq."):
                    wanted = urllib.parse.unquote(marker[len("user_id=eq.") :])
                    rows = [row for row in rows if row.get("user_id") == wanted]
                elif marker.startswith("saved_id=neq."):
                    excluded = urllib.parse.unquote(marker[len("saved_id=neq.") :])
                    rows = [row for row in rows if row.get("saved_id") != excluded]
                elif marker.startswith("saved_id=eq."):
                    wanted = urllib.parse.unquote(marker[len("saved_id=eq.") :])
                    rows = [row for row in rows if row.get("saved_id") == wanted]
        return rows


def _save_body(**over: Any) -> dict[str, Any]:
    """The POST-saved body: the evaluate body's scenario, a view anchor, a label."""
    body: dict[str, Any] = {
        "scenario": evaluate_suite._scenario_body(),
        "view": {"mode": "scenario", "cutoff": None},
        "label": SAVED_LABEL,
    }
    body.update(over)
    return body


def _saved_of_public(public: dict[str, Any], user_id: str) -> SavedScenario:
    """The contract object behind a served public record, for one owner."""
    body = {key: value for key, value in public.items() if key not in ("schema", "saved_id")}
    return SavedScenario(**{**body, "user_id": user_id})


def _rejected_row(saved_public: dict[str, Any], user_id: str) -> dict[str, Any]:
    """A real saved row whose scenario body no longer reconstructs."""
    row = _row_for(_saved_of_public(saved_public, user_id))
    record = json.loads(row["record"])
    del record["scenario"]["price"]
    row["record"] = json.dumps(record, sort_keys=True)
    return row


def _write_inputs(served: evaluate_suite._Served, record: dict[str, Any]) -> None:
    """Publish one inputs bundle next to the served state and drop the caches."""
    path = served.state_path.parent / CAPACITY_INPUTS_FILENAME
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    served.reset()


def _checked_empty(response, *, status: int) -> None:
    """The 204 shape of the shared policy: private, no-store, no validators."""
    assert response.status_code == status, (status, response.text[:200])
    evaluate_suite._headers(response)
    assert response.headers.get("etag") is None
    assert response.headers.get("last-modified") is None
    assert response.content == b""


def _checked_attachment(
    response, *, export, media_prefix: str, filename: str
) -> bytes:
    """The ONE attachment helper: the shared private policy, then the exact
    attachment contract (filename, hash, bytes — and the advisory scan over a
    csv's decoded text)."""
    assert response.status_code == 200, response.text[:200]
    evaluate_suite._headers(response)
    assert response.headers.get("etag") is None
    assert response.headers.get("last-modified") is None
    assert response.headers["content-disposition"] == f'attachment; filename="{filename}"'
    assert response.headers["x-content-sha256"] == export.sha256
    assert response.headers["content-type"].startswith(media_prefix)
    assert response.content == export.payload
    if media_prefix == CSV_MEDIA_TYPE:
        decoded = response.content.decode("utf-8")
        for word in api._RECOMMENDATION_WORDS:
            assert word not in decoded.lower()
    return response.content


@pytest.fixture()
def store_transport(monkeypatch: pytest.MonkeyPatch) -> _FakePostgREST:
    """The U2-1 fake PostgREST transport, recording every call."""
    fake = _FakePostgREST()
    monkeypatch.setattr(store, "_transport", fake)
    yield fake


@pytest.fixture()
def ledger_path(
    served: evaluate_suite._Served, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """The published ledger lives next to the served state under the test root."""
    path = served.state_path.parent / api.STATE_CHANGES_PATH.name
    monkeypatch.setattr(api, "STATE_CHANGES_PATH", path)
    api._reset_changes_cache()
    yield path
    api._reset_changes_cache()


class _Moved(NamedTuple):
    """A real second published generation: the fixture world plus one new
    issuer-A filing, same as_of, later stamps — and its inputs bundle."""

    projection_body: str
    state_body: str
    bundle: dict[str, Any]
    inputs_record: dict[str, Any]


@pytest.fixture(scope="module")
def moved(built: evaluate_suite._Built, pack) -> _Moved:
    events = list(built.events)
    events.append(
        _event(
            81,
            "S-3",
            accepted_at="2026-08-07T09:00:00Z",
            seen_at="2026-08-07T12:00:00Z",
            issuer_id=ISSUER_ONE,
            cik="1",
            file_number="333-555",
        )
    )
    telemetry = evaluate_suite._telemetry(events, built.edges)
    telemetry["counts"] = {
        "event_versions": len(events),
        "event_edges": len(built.edges),
        "review_queue": 0,
    }
    generation = evaluate_suite.VerifiedProjectionGeneration(
        tuple(events), tuple(built.edges), (), telemetry
    )
    projection = evaluate_suite.build_projection_bundle(
        list(events),
        list(built.edges),
        (),
        telemetry,
        as_of=evaluate_suite.AS_OF,
        generated_at=evaluate_suite.LATER_PROJECTION_AT,
    )
    projection_body = json.dumps(projection, indent=2, sort_keys=True) + "\n"
    first = events[0]["evidence"][0]
    row = evaluate_suite._manifest(role="primary")
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
    bundle = evaluate_suite.build_state_bundle(
        generation=generation,
        projection=projection,
        health=evaluate_suite.HEALTH,
        rule_pack=pack,
        as_of=evaluate_suite.AS_OF,
        generated_at=SECOND_GENERATED_AT,
        projection_sha256=hashlib.sha256(projection_body.encode("utf-8")).hexdigest(),
        source_manifests=(resolved_row,),
    )
    evaluate_suite.validate_state_bundle(bundle)
    assert bundle["generation_id"] != built.bundle["generation_id"]
    assert bundle["as_of"] == built.bundle["as_of"]
    inputs_record = evaluate_suite._inputs_bundle_record(
        built, state_generation_id=bundle["generation_id"]
    )
    state_body = json.dumps(bundle, indent=2, sort_keys=True) + "\n"
    return _Moved(projection_body, state_body, bundle, inputs_record)


def _serve_second_generation(
    served: evaluate_suite._Served,
    built: evaluate_suite._Built,
    moved: _Moved,
    ledger_path: Path,
) -> str:
    """Serve the second generation with the real S1→S2 ledger published."""
    root = served.state_path.parent
    previous = root / "previous_state_bundle.json"
    previous.write_text(built.state_body, encoding="utf-8")
    served.projection_path.write_text(moved.projection_body, encoding="utf-8")
    served.state_path.write_text(moved.state_body, encoding="utf-8")
    _write_inputs(served, moved.inputs_record)
    summary = build_from_disk(root=root, previous=previous, generated_at=LEDGER_GENERATED_AT)
    assert summary["status"] == "diffed", summary
    api._reset_changes_cache()
    return str(moved.bundle["generation_id"])


# ---------------------------------------------------------------------------
# Gate 21 — entitlement before any read on every U2-2 route
# ---------------------------------------------------------------------------


def test_u2_every_route_requires_entitlement_before_any_read(
    monkeypatch: pytest.MonkeyPatch, built: evaluate_suite._Built
) -> None:
    evaluate_suite._deny_site_full(monkeypatch)

    def refuse(name: str):
        def _refuse(*_args, **_kwargs):
            raise AssertionError(f"{name} must follow entitlement")

        return _refuse

    for reader in ("_load", "_load_state", "_load_inputs", "_load_generation", "_load_changes"):
        monkeypatch.setattr(api, reader, refuse(reader))
    monkeypatch.setattr(store, "_transport", refuse("store"))

    routes = (
        ("GET", CHANGES_PATH),
        ("GET", f"{CHANGES_PATH}?since={built.bundle['generation_id']}"),
        ("POST", SAVED_PATH),
        ("GET", SAVED_PATH),
        ("GET", f"{SAVED_PATH}/saved:one"),
        ("DELETE", f"{SAVED_PATH}/saved:one"),
        ("GET", f"{SAVED_PATH}/saved:one/export.csv"),
        ("POST", f"{SAVED_PATH}/saved:one/export.csv"),
        ("POST", f"{EVALUATE_EXPORT_PATH}.csv"),
        ("PUT", f"{EVALUATE_EXPORT_PATH}.csv"),
    )
    with evaluate_suite._bare_client() as test_client:
        for method, url in routes:
            response = test_client.request(
                method,
                url,
                json=_save_body(),
                headers={"Authorization": "Bearer signed-in-free-user"},
            )
            assert response.status_code == 403, (method, url, response.text[:200])
            evaluate_suite._checked(response)
            assert evaluate_suite._detail(response)["required_feature"] == "site_full"


# ---------------------------------------------------------------------------
# Gate 22 — the change desk filters to the issuer and binds the served state
# ---------------------------------------------------------------------------


def test_u2_changes_route_filters_to_issuer_and_binds_served_generation(
    client: TestClient,
    served: evaluate_suite._Served,
    built: evaluate_suite._Built,
    moved: _Moved,
    ledger_path: Path,
) -> None:
    served_generation = _serve_second_generation(served, built, moved, ledger_path)
    saved_generation = str(built.bundle["generation_id"])

    body = evaluate_suite._checked(client.get(CHANGES_PATH), status=200)
    assert set(body) == {
        "from_generation_id",
        "to_generation_id",
        "baseline",
        "changes",
        "counts",
    }
    assert body["from_generation_id"] == saved_generation
    assert body["to_generation_id"] == served_generation
    assert body["baseline"] is False
    kinds = [change["kind"] for change in body["changes"]]
    assert "new_event" in kinds
    assert all(change["issuer_id"] in (None, ISSUER_ONE) for change in body["changes"])
    counted = {kind: 0 for kind in CHANGE_KINDS}
    for change in body["changes"]:
        counted[change["kind"]] += 1
    assert body["counts"] == counted

    other = evaluate_suite._checked(
        client.get(f"{PREFIX}/issuers/{ISSUER_TWO}/changes"), status=200
    )
    assert other["from_generation_id"] == saved_generation
    assert all(change["issuer_id"] is None for change in other["changes"])

    # The desk binds the served generation: roll the state back and it refuses.
    served.state_path.write_text(built.state_body, encoding="utf-8")
    served.reset()
    unbound = client.get(CHANGES_PATH)
    assert unbound.status_code == 503
    assert evaluate_suite._detail(unbound) == api._CHANGE_LEDGER_NOT_BOUND
    evaluate_suite._checked(unbound)

    # An issuer the served state does not cover has no desk.
    missing = client.get(f"{PREFIX}/issuers/sec:cik:9999999999/changes")
    assert missing.status_code == 404
    assert evaluate_suite._detail(missing) == "issuer not covered"
    evaluate_suite._checked(missing)


# ---------------------------------------------------------------------------
# Gate 23 — a since the one retained ledger does not cover is a typed 409
# ---------------------------------------------------------------------------


def test_u2_changes_since_mismatch_is_409_change_ledger_does_not_cover_since(
    client: TestClient,
    served: evaluate_suite._Served,
    built: evaluate_suite._Built,
    moved: _Moved,
    ledger_path: Path,
) -> None:
    _serve_second_generation(served, built, moved, ledger_path)
    saved_generation = str(built.bundle["generation_id"])

    covered = evaluate_suite._checked(
        client.get(f"{CHANGES_PATH}?since={saved_generation}"), status=200
    )
    assert covered["from_generation_id"] == saved_generation

    for since in (str(moved.bundle["generation_id"]), "state_bundle:nowhere"):
        mismatch = client.get(f"{CHANGES_PATH}?since={since}")
        assert mismatch.status_code == 409, (since, mismatch.text[:200])
        assert evaluate_suite._detail(mismatch) == api._CHANGE_LEDGER_DOES_NOT_COVER_SINCE
        evaluate_suite._checked(mismatch)

    # A baseline ledger covers no since at all — honestly, not padded.
    build_from_disk(root=served.state_path.parent, previous=None, generated_at=LEDGER_GENERATED_AT)
    api._reset_changes_cache()
    baseline_since = client.get(f"{CHANGES_PATH}?since={saved_generation}")
    assert baseline_since.status_code == 409
    assert evaluate_suite._detail(baseline_since) == api._CHANGE_LEDGER_DOES_NOT_COVER_SINCE
    evaluate_suite._checked(baseline_since)
    baseline = evaluate_suite._checked(client.get(CHANGES_PATH), status=200)
    assert baseline["baseline"] is True
    assert baseline["changes"] == []
    assert baseline["from_generation_id"] is None


# ---------------------------------------------------------------------------
# Gate 24 — save runs the evaluate internals; an unavailable result is never saved
# ---------------------------------------------------------------------------


def test_u2_save_runs_the_evaluate_internals_and_never_saves_an_unavailable_result(
    client: TestClient,
    served: evaluate_suite._Served,
    built: evaluate_suite._Built,
    store_transport: _FakePostgREST,
    with_inputs,
) -> None:
    saved = evaluate_suite._checked(client.post(SAVED_PATH, json=_save_body()), status=201)
    assert saved["restore"] is None
    assert store_transport.calls == [("POST", store.TABLE)]

    entries = evaluate_suite._fixture_entries(built.bundle["as_of"])
    entries[inputs_suite.FINANCIALS_FAMILY] = inputs_suite.FamilyEntry(
        family=inputs_suite.FINANCIALS_FAMILY,
        support="unavailable",
        reason_codes=("companyfacts_snapshot_unavailable",),
    )
    entries[inputs_suite.SHARE_BASIS_FAMILY] = inputs_suite.FamilyEntry(
        family=inputs_suite.SHARE_BASIS_FAMILY,
        support="unavailable",
        reason_codes=("share_observations_not_admitted",),
    )
    _write_inputs(served, evaluate_suite._inputs_bundle_record(built, entries=entries))
    refused = client.post(SAVED_PATH, json=_save_body())
    assert refused.status_code == 409
    detail = evaluate_suite._checked(refused)["detail"]
    assert detail["code"] == "scenario_inputs_unavailable"
    assert len(store_transport.calls) == 1, "an unavailable result is never saved"

    (served.state_path.parent / CAPACITY_INPUTS_FILENAME).unlink()
    served.reset()
    absent = client.post(SAVED_PATH, json=_save_body())
    assert absent.status_code == 503
    assert evaluate_suite._detail(absent) == _INPUTS_UNAVAILABLE
    evaluate_suite._checked(absent)
    assert len(store_transport.calls) == 1


# ---------------------------------------------------------------------------
# Gate 25 — save is idempotent and the 201 body is the public record only
# ---------------------------------------------------------------------------


def test_u2_save_is_idempotent_and_201_returns_public_record_only(
    client: TestClient,
    served: evaluate_suite._Served,
    built: evaluate_suite._Built,
    store_transport: _FakePostgREST,
    with_inputs,
    pack,
) -> None:
    first = evaluate_suite._checked(client.post(SAVED_PATH, json=_save_body()), status=201)
    again = evaluate_suite._checked(client.post(SAVED_PATH, json=_save_body()), status=201)
    public = first["saved"]
    assert "user_id" not in public
    # idempotent: the same answer twice is the SAME ROW identity (the stamp on
    # each response is that response's own save moment)
    assert again["saved"]["saved_id"] == public["saved_id"]
    for key, value in again["saved"].items():
        if key != "saved_at":
            assert public[key] == value, key
    assert len(store_transport.calls) == 2

    scenario = evaluate_suite._test_scenario()
    recomputed = evaluate_suite._recomputed_result(built, with_inputs.record, scenario, pack)
    expected = SavedScenario(
        user_id="paid-user",
        issuer_id=ISSUER_ONE,
        label=SAVED_LABEL,
        view={"mode": "scenario", "cutoff": None},
        scenario=scenario.as_record(),
        state_generation_id=str(built.bundle["generation_id"]),
        inputs_generation_id=str(with_inputs.record["generation_id"]),
        result_id=str(recomputed["result_id"]),
        result_digest=result_digest_of(recomputed),
        rule_pack_digest=str(recomputed["capacity_envelope"]["rule_pack_digest"]),
        saved_at=str(public["saved_at"]),
    )
    assert json.dumps(expected.public_record(), sort_keys=True) == json.dumps(public, sort_keys=True)
    assert expected.saved_id == _saved_of_public(public, "paid-user").saved_id


# ---------------------------------------------------------------------------
# Gate 26 — the listing serves only the caller's rows
# ---------------------------------------------------------------------------


def test_u2_list_returns_only_the_callers_rows(
    client: TestClient,
    served: evaluate_suite._Served,
    built: evaluate_suite._Built,
    with_inputs,
    composed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakePostgREST()
    monkeypatch.setattr(store, "_transport", fake)
    public = evaluate_suite._checked(client.post(SAVED_PATH, json=_save_body()), status=201)["saved"]
    own = _saved_of_public(public, "paid-user")
    second_own = contract_suite._make_saved(
        composed, view={"mode": "scenario", "cutoff": "2026-10-14T00:00:00Z"}, user_id="paid-user"
    )
    other = _saved_of_public(public, USER_BETA)
    assert len({own.saved_id, second_own.saved_id, other.saved_id}) == 3

    monkeypatch.setattr(
        store,
        "_transport",
        _PartitionedStore(rows=[_row_for(own), _row_for(other), _row_for(second_own)]),
    )
    first_page = evaluate_suite._checked(client.get(f"{SAVED_PATH}?limit=1"), status=200)
    ids = [item["saved_id"] for item in first_page["items"]]
    assert len(ids) == 1
    assert other.saved_id not in ids
    assert first_page["next_after"] == ids[0]
    assert all("user_id" not in item for item in first_page["items"])

    second_page = evaluate_suite._checked(
        client.get(f"{SAVED_PATH}?limit=1&after={ids[0]}"), status=200
    )
    tail = [item["saved_id"] for item in second_page["items"]]
    assert set(ids + tail) == {own.saved_id, second_own.saved_id}
    assert second_page["next_after"] is None

    with _client_for(USER_BETA) as beta_client:
        beta_listed = evaluate_suite._checked(beta_client.get(SAVED_PATH), status=200)
    assert [item["saved_id"] for item in beta_listed["items"]] == [other.saved_id]


# ---------------------------------------------------------------------------
# Gate 27 — every restore outcome is 200 with the typed outcome
# ---------------------------------------------------------------------------


def _unavailable_families_inputs(served: evaluate_suite._Served, built) -> None:
    entries = evaluate_suite._fixture_entries(built.bundle["as_of"])
    entries[inputs_suite.FINANCIALS_FAMILY] = inputs_suite.FamilyEntry(
        family=inputs_suite.FINANCIALS_FAMILY,
        support="unavailable",
        reason_codes=("companyfacts_snapshot_unavailable",),
    )
    entries[inputs_suite.SHARE_BASIS_FAMILY] = inputs_suite.FamilyEntry(
        family=inputs_suite.SHARE_BASIS_FAMILY,
        support="unavailable",
        reason_codes=("share_observations_not_admitted",),
    )
    _write_inputs(served, evaluate_suite._inputs_bundle_record(built, entries=entries))


@pytest.mark.parametrize(
    "outcome",
    (
        "no_change",
        "correction",
        "new_events",
        "inputs_unavailable",
        "source_outage",
        "scenario_rejected",
    ),
)
def test_u2_restore_outcomes_are_200_with_typed_outcome_not_errors(
    outcome: str,
    client: TestClient,
    served: evaluate_suite._Served,
    built: evaluate_suite._Built,
    with_inputs,
    moved: _Moved,
    ledger_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakePostgREST()
    monkeypatch.setattr(store, "_transport", fake)
    saved_public = evaluate_suite._checked(client.post(SAVED_PATH, json=_save_body()), status=201)[
        "saved"
    ]
    saved_id = str(saved_public["saved_id"])
    fake.rows = [_row_for(_saved_of_public(saved_public, "paid-user"))]

    if outcome == "correction":
        entries = evaluate_suite._fixture_entries(built.bundle["as_of"])
        entries[inputs_suite.FINANCIALS_FAMILY] = inputs_suite._entry_for(
            F.financials(F.cash("4321000"), F.ocf()), inputs_suite.FINANCIALS_FAMILY
        )
        _write_inputs(served, evaluate_suite._inputs_bundle_record(built, entries=entries))
    elif outcome == "new_events":
        _serve_second_generation(served, built, moved, ledger_path)
    elif outcome == "inputs_unavailable":
        _unavailable_families_inputs(served, built)
    elif outcome == "source_outage":
        served.state_path.write_text("{not-json", encoding="utf-8")
        served.reset()
    elif outcome == "scenario_rejected":
        monkeypatch.setattr(
            store, "_transport", _FakePostgREST(rows=[_rejected_row(saved_public, "paid-user")])
        )

    response = client.get(f"{SAVED_PATH}/{saved_id}")
    body = evaluate_suite._checked(response, status=200)
    assert set(body) == {"saved", "current", "unavailable", "restore", "changes"}
    restore = body["restore"]
    assert restore["outcome"] == outcome, json.dumps(restore, sort_keys=True)
    if outcome in ("no_change", "correction", "new_events"):
        assert body["current"] is not None
        assert body["current"]["result"]["result_id"]
    else:
        assert body["current"] is None
    if outcome == "no_change":
        assert restore["result_identical"] is True
    if outcome == "correction":
        assert restore["result_identical"] is False
    if outcome == "inputs_unavailable":
        assert body["unavailable"] == {"components": ["financials", "share_basis"]}
    else:
        assert body["unavailable"] is None
    if outcome == "new_events":
        assert any(change["kind"] == "new_event" for change in body["changes"])


# ---------------------------------------------------------------------------
# Gate 28 — a foreign or absent saved_id is 404, never 403
# ---------------------------------------------------------------------------


def test_u2_foreign_or_absent_saved_id_is_404_never_403(
    client: TestClient,
    served: evaluate_suite._Served,
    built: evaluate_suite._Built,
    with_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakePostgREST()
    monkeypatch.setattr(store, "_transport", fake)
    saved_public = evaluate_suite._checked(client.post(SAVED_PATH, json=_save_body()), status=201)[
        "saved"
    ]
    saved_id = str(saved_public["saved_id"])
    monkeypatch.setattr(
        store,
        "_transport",
        _PartitionedStore(rows=[_row_for(_saved_of_public(saved_public, "paid-user"))]),
    )

    with _client_for(USER_BETA) as beta_client:
        foreign = beta_client.get(f"{SAVED_PATH}/{saved_id}")
        assert foreign.status_code == 404
        assert evaluate_suite._detail(foreign) == api._SAVED_SCENARIO_NOT_FOUND
        evaluate_suite._checked(foreign)

        absent = beta_client.get(f"{SAVED_PATH}/saved:nobody")
        assert absent.status_code == 404
        assert evaluate_suite._detail(absent) == api._SAVED_SCENARIO_NOT_FOUND
        evaluate_suite._checked(absent)

        foreign_delete = beta_client.delete(f"{SAVED_PATH}/{saved_id}")
        assert foreign_delete.status_code == 404
        evaluate_suite._checked(foreign_delete)

    absent_delete = client.delete(f"{SAVED_PATH}/saved:nobody")
    assert absent_delete.status_code == 404
    evaluate_suite._checked(absent_delete)

    gone = client.delete(f"{SAVED_PATH}/{saved_id}")
    _checked_empty(gone, status=204)
    # the canned fake records the delete without applying it
    monkeypatch.setattr(store, "_transport", _PartitionedStore(rows=[]))
    missing = client.get(f"{SAVED_PATH}/{saved_id}")
    assert missing.status_code == 404
    evaluate_suite._checked(missing)


# ---------------------------------------------------------------------------
# Gate 29 — the export routes attach private exact bytes
# ---------------------------------------------------------------------------


def test_u2_export_routes_attach_private_bytes_with_sha256_and_result_id_filename(
    client: TestClient,
    served: evaluate_suite._Served,
    built: evaluate_suite._Built,
    with_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "_transport", _FakePostgREST())
    evaluated = evaluate_suite._checked(
        client.post(
            f"{PREFIX}/issuers/{ISSUER_ONE}/scenarios/evaluate",
            json=evaluate_suite._scenario_body(),
        ),
        status=200,
    )
    expected_envelope = {
        **evaluated,
        "scenario": evaluate_suite._test_scenario().as_record(),
        "issuer_id": ISSUER_ONE,
        "inputs_generation_id": str(with_inputs.record["generation_id"]),
    }

    for fmt, media_prefix in (("csv", CSV_MEDIA_TYPE), ("parquet", PARQUET_MEDIA_TYPE)):
        fresh = client.post(f"{EVALUATE_EXPORT_PATH}.{fmt}", json=evaluate_suite._scenario_body())
        export = export_scenario_envelope(expected_envelope, fmt)
        filename = f"{expected_envelope['result']['result_id']}.{fmt}"
        _checked_attachment(fresh, export=export, media_prefix=media_prefix, filename=filename)

    xlsx = client.post(f"{EVALUATE_EXPORT_PATH}.xlsx", json=evaluate_suite._scenario_body())
    assert xlsx.status_code == 404
    evaluate_suite._checked(xlsx)
    saved_xlsx = client.get(f"{SAVED_PATH}/saved:nobody/export.xlsx")
    assert saved_xlsx.status_code == 404
    evaluate_suite._checked(saved_xlsx)

    # A method the export route does not serve is a private 405, like forensics.
    for method, url in (
        ("PUT", f"{EVALUATE_EXPORT_PATH}.csv"),
        ("POST", f"{SAVED_PATH}/saved:nobody/export.csv"),
    ):
        wrong = client.request(method, url, json=_save_body())
        assert wrong.status_code == 405, (method, wrong.text[:200])
        assert evaluate_suite._detail(wrong) == api._METHOD_NOT_ALLOWED
        evaluate_suite._checked(wrong)

    saved_public = evaluate_suite._checked(client.post(SAVED_PATH, json=_save_body()), status=201)[
        "saved"
    ]
    saved_id = str(saved_public["saved_id"])
    monkeypatch.setattr(
        store,
        "_transport",
        _PartitionedStore(rows=[_row_for(_saved_of_public(saved_public, "paid-user"))]),
    )
    restored = evaluate_suite._checked(client.get(f"{SAVED_PATH}/{saved_id}"), status=200)
    current = restored["current"]
    restore_envelope = {
        "view": current["view"],
        "inputs": current["inputs"],
        "result": current["result"],
        "scenario": saved_public["scenario"],
        "issuer_id": ISSUER_ONE,
        "inputs_generation_id": str(saved_public["inputs_generation_id"]),
    }
    for fmt, media_prefix in (("csv", CSV_MEDIA_TYPE), ("parquet", PARQUET_MEDIA_TYPE)):
        attachment = client.get(f"{SAVED_PATH}/{saved_id}/export.{fmt}")
        export = export_scenario_envelope(restore_envelope, fmt)
        filename = f"{current['result']['result_id']}.{fmt}"
        _checked_attachment(attachment, export=export, media_prefix=media_prefix, filename=filename)

    # A restore whose outcome has no result is refused, naming the outcome.
    monkeypatch.setattr(
        store,
        "_transport",
        _FakePostgREST(rows=[_rejected_row(saved_public, "paid-user")]),
    )
    nothing = client.get(f"{SAVED_PATH}/{saved_id}/export.csv")
    assert nothing.status_code == 409
    assert evaluate_suite._detail(nothing) == "nothing to export: scenario_rejected"
    evaluate_suite._checked(nothing)


# ---------------------------------------------------------------------------
# Gate 30 — nothing is persisted, cached or logged on the app host
# ---------------------------------------------------------------------------


def test_u2_routes_never_persist_or_log_scenario_material(
    client: TestClient,
    served: evaluate_suite._Served,
    built: evaluate_suite._Built,
    with_inputs,
    ledger_path: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import logging

    def snapshot() -> list[tuple[str, int]]:
        root = served.state_path.parent
        return sorted(
            (str(path.relative_to(root)), path.stat().st_size)
            for path in root.rglob("*")
            if path.is_file()
        )

    fake = _FakePostgREST()
    monkeypatch.setattr(store, "_transport", fake)
    scenario_body = evaluate_suite._scenario_body()
    before = snapshot()

    with caplog.at_level(logging.DEBUG):
        saved = evaluate_suite._checked(client.post(SAVED_PATH, json=_save_body()), status=201)
        saved_id = str(saved["saved"]["saved_id"])
        # the store now answers reads with the row the save wrote
        fake.rows = [_row_for(_saved_of_public(saved["saved"], "paid-user"))]
        evaluate_suite._checked(client.get(f"{SAVED_PATH}/{saved_id}"), status=200)
        evaluate_suite._checked(client.get(SAVED_PATH), status=200)
        _checked_empty(client.delete(f"{SAVED_PATH}/{saved_id}"), status=204)
        fresh = client.post(f"{EVALUATE_EXPORT_PATH}.csv", json=scenario_body)
        assert fresh.status_code == 200, fresh.text[:200]

    assert snapshot() == before
    methods = [method for method, _path in fake.calls]
    assert methods == ["POST", "GET", "GET", "GET", "DELETE"], fake.calls
    for method, path in fake.calls:
        if method == "GET":
            assert "user_id=eq." in path

    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert SAVED_LABEL not in messages
    assert evaluate_suite.SCENARIO_LABEL not in messages
    assert fresh.content.decode("utf-8")[:64] not in messages
    assert "fixed_price" not in messages
