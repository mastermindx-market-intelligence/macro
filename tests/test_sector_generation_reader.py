"""Real captured-generation → semantic admission → projection → gated API checks.

All publication uses isolated temporary roots. Gate identities are controlled test
fixtures; these tests do not assert authenticated beta or live provider acceptance.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import main as macro_main, paywall, sector_generation as api
from app.sector_generation_reader import SectorGenerationReader
from engine.sector_native_view import SectorViewUnavailable
from lib import sector_generation_contract as contract
from lib import sector_generation_wire as wire
from scripts import check_sector_intelligence_freshness as freshness
from scripts import vps_live_orchestrator as publisher

SOURCE = "2026-11-03"
PUBLISHED = datetime(2026, 11, 3, 23, tzinfo=timezone.utc)
MEMBERS = contract.SECTOR_GENERATION_MEMBERS


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode()


@pytest.fixture
def bundle():
    rows = lambda lane, n: [{"ticker": f"{lane}-{i}", "name": f"{lane}-{i}",
        "kind": "theme", "href": f"basket/{lane}-{i}.html",
        "private_debug": "PRIVATE_SOURCE_VALUE"} for i in range(n)]
    documents = [
        {"as_of": SOURCE, "sectors": [{"id": "xlv", "ticker": "XLV", "kind": "sector", "name": "Health Care"}]},
        {"meta": {"asOf": SOURCE, "rs_history": {"schema": "sector_cycles.rs_history.v1", "mode": "reconstructed_price_history", "naturally_observed": False, "basis": "tr", "benchmark": "SPY", "horizons_sessions": [21, 63], "max_points_per_sector": 252}}, "sectors": [{"id": "xlv", "ticker": "XLV", "kind": "sector", "rs_history": [], "turns": []}]},
        {"as_of": SOURCE, "theme_intel": {"as_of": SOURCE}},
        {"theme_context": {"as_of": SOURCE, "leadership": {
            "state": "rotating", "days_in_state": 3,
            "stance_en": "version-one", "strength": [
                {"id": "us_sector_health", "name": "Health Care"}],
        }}, "private_manifest": {"secret": "PRIVATE_SOURCE_VALUE"}},
        {"schema": "sector_intelligence_action_board.v1", "as_of": SOURCE,
         "action_board": {lane: rows(lane, count) for lane, count in {
             "buy_now": 4, "buy_soon": 0, "on_the_run": 0,
             "take_profits": 0, "hold": 2, "avoid": 3,
         }.items()}},
    ]
    documents[-1]["baskets_sha256"] = hashlib.sha256(_encoded(documents[2])).hexdigest()
    identity = {"sector_view": {
        "schema": "sector.view_inputs.v1", "source_session": SOURCE,
        "input_version": "sector-inputs-v1", "baseline_session": None,
        "source_qualification": "accepted",
    }, "private_inputs": {"path": "PRIVATE_SOURCE_VALUE"}}
    return dict(zip(MEMBERS, map(_encoded, documents))), identity


def _arguments(bundle, **changes):
    raw, identity = bundle
    return {"member_bytes": raw, "input_identity": identity,
            "generation_id": "g1", "published_at": PUBLISHED.isoformat(),
            "now": PUBLISHED, **changes}


def _sources(tmp_path, raw, generation_id):
    result = {}
    for name, data in raw.items():
        path = tmp_path / "sources" / generation_id / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        result[name] = path
    return result


def _publish(tmp_path, bundle, *, generation_id="g1", expected=None,
             semantic=True, now=PUBLISHED):
    raw, identity = bundle
    sources = _sources(tmp_path, raw, generation_id)
    orch = publisher.Orchestrator(live_dir=tmp_path / "public/live",
        state_dir=tmp_path / "state", data_dir=tmp_path / "data", now=now)
    if semantic:
        request = contract.prepare_sector_generation_request(
            sources=sources, input_identity=identity, generation_id=generation_id,
            source_revision="fixture-revision", lane="snapshot",
        )
    else:
        # Deliberately byte-valid negative fixtures: the generic owner cannot
        # establish Sector semantics from the mere presence of a callback.
        request = publisher.GenerationRequest(
            generation_id=generation_id, domain="sector", lane="snapshot",
            source_revision="fixture-revision", input_identity=identity,
            artifacts=tuple(publisher.GenerationArtifact(name=name, source=source,
                validator=lambda captured: None) for name, source in sources.items()),
        )
    result = orch.publish_generation(request, expected_current_content_id=expected)
    return orch, result, tmp_path / "state/generations"


@pytest.fixture(autouse=True)
def gates(monkeypatch):
    monkeypatch.delenv("PAYWALL_ENABLED", raising=False)
    monkeypatch.setenv("REGWALL_ENABLED", "1")
    uid = "11111111-1111-1111-1111-111111111111"
    monkeypatch.setattr(macro_main, "_mm_supabase_access_token",
                        lambda request: "fixture-token" if request.cookies else None)
    monkeypatch.setattr(macro_main, "_mm_verify_uid_cached", lambda token: uid)
    monkeypatch.setattr(paywall, "_fetch_supabase_user", lambda token:
                        paywall._Identity(uid, "reader@example.test", {"id": uid}, "ok"))
    monkeypatch.setattr(paywall, "_store_entitlement", lambda uid:
        ({"tier": "essential", "status": "active", "features": ["site_full"]}, True))
    paywall._AUTH_CACHE.clear()
    paywall._ENT_CACHE.clear()
    yield
    paywall._AUTH_CACHE.clear()
    paywall._ENT_CACHE.clear()


def _client(reader):
    app = FastAPI()
    app.include_router(api.create_router(reader))
    return TestClient(app)


@pytest.mark.parametrize("audience", ["preview", "entitled"])
def test_real_published_snapshot_flows_through_actual_gates_and_wire(tmp_path, bundle, audience):
    _, published, root = _publish(tmp_path, bundle)
    assert published.status == "published", published.detail
    reader = SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED)
    response = _client(reader).get("/api/sector-generation?audience=" + audience,
                                  cookies={"sb-fixture-auth-token": "fixture"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema"] == "sector_generation.read/v1"
    assert body["source_session"] == SOURCE
    assert body["published_at"] == published.published_at
    assert body["qualification"] == "accepted"
    assert body["projection"]["receipt"]["generation_id"] == "g1"
    assert body["projection"]["data"]["audience"] == audience
    assert "PRIVATE_SOURCE_VALUE" not in response.text
    assert "baskets_sha256" not in response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Cookie"
    if audience == "preview":
        assert "buy_now-3" not in response.text
        assert body["projection"]["data"]["action_board"]["locked"] == 3
    else:
        assert "buy_now-3" in response.text


def test_denied_request_never_resolves_selected_snapshot(tmp_path):
    calls = []
    reader = SectorGenerationReader(generations_root=tmp_path / "absent",
        snapshot_reader=lambda **kw: calls.append(kw), clock=lambda: PUBLISHED)
    response = _client(reader).get("/api/sector-generation")
    assert response.status_code == 401
    assert calls == []
    assert not (tmp_path / "absent").exists()


def test_pointer_change_after_capture_does_not_mix_generations(tmp_path, bundle):
    _, first, root = _publish(tmp_path, bundle)
    assert first.status == "published"
    changed = deepcopy(bundle)
    handoff = json.loads(changed[0][MEMBERS[3]])
    handoff["theme_context"]["leadership"]["stance_en"] = "version-two"
    changed[0][MEMBERS[3]] = _encoded(handoff)
    calls = []
    def snapshot(**kwargs):
        calls.append(kwargs)
        captured = publisher.read_selected_generation(**kwargs)
        _, result, _ = _publish(tmp_path, changed, generation_id="g2", expected=first.content_id)
        assert result.status == "published", result.detail
        return captured
    reader = SectorGenerationReader(generations_root=root, snapshot_reader=snapshot,
                                    clock=lambda: PUBLISHED)
    result = reader.read_selected_generation(api.SectorGenerationRequest("preview"))
    assert len(calls) == 1
    assert calls[0]["domain"] == "sector" and tuple(calls[0]["members"]) == MEMBERS
    assert result.payload["receipt"]["generation_id"] == "g1"
    assert result.payload["data"]["brief"]["leadership"]["stance_en"] == "version-one"
    next_result = SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED).read_selected_generation(
        api.SectorGenerationRequest("preview"))
    assert next_result.source_session == result.source_session
    assert next_result.payload["receipt"]["generation_id"] == "g2"
    assert next_result.payload["data"]["brief"]["leadership"]["stance_en"] == "version-two"


def test_reader_uses_captured_bytes_without_unchecked_member_reread(tmp_path, bundle):
    _, published, root = _publish(tmp_path, bundle)
    assert published.status == "published"
    def snapshot(**kwargs):
        captured = publisher.read_selected_generation(**kwargs)
        (root / "sector/g1" / MEMBERS[3]).write_bytes(b'{"corrupt":true}')
        return captured
    reader = SectorGenerationReader(generations_root=root, snapshot_reader=snapshot,
                                    clock=lambda: PUBLISHED)
    result = reader.read_selected_generation(api.SectorGenerationRequest("preview"))
    assert result.payload["data"]["brief"]["leadership"]["stance_en"] == "version-one"
    with pytest.raises(publisher.SelectedGenerationUnavailable):
        SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED).read_selected_generation(
            api.SectorGenerationRequest("preview"))


def test_retained_generation_ages_without_republication_or_read_side_writes(tmp_path, bundle):
    _, published, root = _publish(tmp_path, bundle)
    assert published.status == "published"
    before = {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
              for p in root.rglob("*") if p.is_file()}
    clock = [PUBLISHED]
    reader = SectorGenerationReader(generations_root=root, clock=lambda: clock[0])
    initial = reader.read_selected_generation(api.SectorGenerationRequest("preview"))
    clock[0] = datetime(2026, 11, 4, 23, tzinfo=timezone.utc)
    tolerated = reader.read_selected_generation(api.SectorGenerationRequest("preview"))
    clock[0] = datetime(2026, 11, 5, 23, tzinfo=timezone.utc)
    old = reader.read_selected_generation(api.SectorGenerationRequest("preview"))
    assert initial.qualification == tolerated.qualification == "accepted"
    assert old.qualification == "stale"
    assert old.published_at == initial.published_at == published.published_at
    assert old.payload["receipt"]["content_sha256"] == initial.payload["receipt"]["content_sha256"]
    assert {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()} == before


def test_current_core_cannot_hide_an_expired_declared_brief_baseline(bundle):
    raw, identity = deepcopy(bundle)
    central, cycles = json.loads(raw[MEMBERS[0]]), json.loads(raw[MEMBERS[1]])
    central["as_of"] = cycles["meta"]["asOf"] = "2026-11-05"
    raw[MEMBERS[0]], raw[MEMBERS[1]] = _encoded(central), _encoded(cycles)
    identity["sector_view"].update(source_session="2026-11-05", baseline_session=SOURCE)
    projected = contract.project_sector_bundle(**_arguments((raw, identity),
        now=datetime(2026, 11, 5, 23, tzinfo=timezone.utc),
        published_at="2026-11-05T23:00:00Z"), audience="preview")
    assert projected["receipt"]["source_session"] == "2026-11-05"
    assert projected["receipt"]["qualification"] == "stale"
    assert projected["data"]["brief"]["status"] == "declared_older_baseline"
    assert projected["data"]["brief"]["as_of"] == SOURCE


@pytest.mark.parametrize("qualification", ["stale", "degraded"])
def test_recent_dates_never_upgrade_declared_source_qualification(bundle, qualification):
    bundle[1]["sector_view"]["source_qualification"] = qualification
    view = contract.project_sector_bundle(**_arguments(bundle), audience="preview")
    assert view["receipt"]["qualification"] == qualification


def test_developing_session_is_not_accepted_as_completed(bundle):
    now = datetime(2026, 11, 3, 16, tzinfo=timezone.utc)
    view = contract.project_sector_bundle(**_arguments(bundle, now=now,
        published_at="2026-11-03T15:00:00Z"), audience="preview")
    assert view["receipt"]["qualification"] == "degraded"


@pytest.mark.parametrize("change", [
    {"schema": "unknown"}, {"source_session": "today"},
    {"input_version": "private/version"}, {"baseline_session": ""},
    {"baseline_session": False}, {"baseline_session": "2026-11-04"},
    {"source_qualification": "current"},
])
def test_invalid_domain_identity_is_not_inferred_or_repaired(bundle, change):
    bundle[1]["sector_view"].update(change)
    with pytest.raises((contract.SectorGenerationContractError, SectorViewUnavailable)):
        contract.project_sector_bundle(**_arguments(bundle), audience="preview")


@pytest.mark.parametrize("field", ["schema", "source_session", "input_version",
                                   "baseline_session", "source_qualification"])
def test_missing_domain_identity_field_refuses(bundle, field):
    del bundle[1]["sector_view"][field]
    with pytest.raises(contract.SectorGenerationContractError, match="missing_sector_identity"):
        contract.project_sector_bundle(**_arguments(bundle), audience="preview")


@pytest.mark.parametrize("generation_id", ["sector:g1", "sector@g1"])
def test_publisher_token_cannot_be_sanitized_into_public_identity(tmp_path, bundle, generation_id):
    _, published, root = _publish(tmp_path, bundle, generation_id=generation_id, semantic=False)
    assert published.status == "published", published.detail
    with pytest.raises(SectorViewUnavailable, match="invalid_receipt"):
        SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED).read_selected_generation(
            api.SectorGenerationRequest("preview"))


@pytest.mark.parametrize("raw", [b'{"as_of":"2026-11-03","unused":NaN}',
    b'{"as_of":"2026-11-03","unused":1e999}',
    b'{"as_of":"2026-11-03","as_of":"2026-11-04"}', b'[]', b'\xff'])
def test_malformed_or_nonfinite_captured_json_refuses(bundle, raw):
    bundle[0][MEMBERS[0]] = raw
    with pytest.raises(contract.SectorGenerationContractError):
        contract.project_sector_bundle(**_arguments(bundle), audience="preview")


def test_corrupt_dependency_is_unavailable_without_private_error_details(tmp_path, bundle, caplog):
    action = json.loads(bundle[0][MEMBERS[4]])
    action["baskets_sha256"] = "PRIVATE_WRONG_HASH"
    bundle[0][MEMBERS[4]] = _encoded(action)
    _, published, root = _publish(tmp_path, bundle, semantic=False)
    assert published.status == "published"
    caplog.clear()
    response = _client(SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED)).get(
        "/api/sector-generation", cookies={"sb-fixture-auth-token": "fixture"})
    assert response.status_code == 503
    assert response.json()["code"] == "SECTOR_GENERATION_UNAVAILABLE"
    assert "PRIVATE_WRONG_HASH" not in response.text + caplog.text
    assert str(root) not in response.text + caplog.text


def test_calendar_uncertainty_is_unavailable_not_stale_or_accepted(bundle, monkeypatch):
    def unavailable(*args, **kwargs):
        raise RuntimeError("PRIVATE_CALENDAR_PATH")
    monkeypatch.setattr(freshness.market_session, "missed_sessions", unavailable)
    with pytest.raises(contract.SectorGenerationContractError, match="calendar_unavailable"):
        contract.project_sector_bundle(**_arguments(bundle), audience="preview")


def test_absent_selection_never_creates_roots_or_uses_static_fallback(tmp_path):
    root = tmp_path / "absent"
    with pytest.raises(publisher.SelectedGenerationUnavailable):
        SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED).read_selected_generation(
            api.SectorGenerationRequest("preview"))
    assert not root.exists()
    with pytest.raises(ValueError, match="absolute"):
        SectorGenerationReader(generations_root=Path("relative"))


def _with_hidden_name(bundle, name):
    raw, identity = deepcopy(bundle)
    action = json.loads(raw[MEMBERS[4]])
    action["action_board"]["buy_now"][3]["name"] = name
    raw[MEMBERS[4]] = _encoded(action)
    return raw, identity


def test_preflight_checks_entitled_whole_http_body_not_only_projection(bundle):
    small = _with_hidden_name(bundle, "")
    projection = contract.project_sector_bundle(**_arguments(small), audience="entitled")
    overhead = len(_encoded(projection))
    large = _with_hidden_name(bundle, "x" * (wire.MAX_ENCODED_BYTES - overhead - 10))
    projection = contract.project_sector_bundle(**_arguments(large), audience="entitled")
    assert len(_encoded(projection)) == wire.MAX_ENCODED_BYTES - 10
    assert contract.project_sector_bundle(**_arguments(large), audience="preview")
    with pytest.raises(wire.SectorGenerationTooLarge):
        contract.preflight_sector_bundle(**_arguments(large))


def test_preflight_reserves_retained_receipt_and_qualification_width(bundle):
    small = _with_hidden_name(bundle, "")
    projection = contract.project_sector_bundle(**_arguments(small), audience="entitled")
    facts = projection["receipt"]
    overhead = len(wire.encode_sector_generation(audience="entitled",
        source_session=facts["source_session"], published_at=facts["published_at"],
        qualification=facts["qualification"], projection=projection))
    large = _with_hidden_name(bundle, "x" * (wire.MAX_ENCODED_BYTES - overhead - 100))
    projection = contract.project_sector_bundle(**_arguments(large), audience="entitled")
    assert len(wire.encode_sector_generation(audience="entitled",
        source_session=facts["source_session"], published_at=facts["published_at"],
        qualification=facts["qualification"], projection=projection)) < wire.MAX_ENCODED_BYTES
    with pytest.raises(wire.SectorGenerationTooLarge):
        contract.preflight_sector_bundle(**_arguments(large))


@pytest.mark.parametrize("failure", ["dependency", "identity", "stale", "degraded", "core", "history"])
def test_semantic_admission_rejection_preserves_previous_selection(tmp_path, bundle, failure):
    _, prior, root = _publish(tmp_path, bundle)
    assert prior.status == "published"
    pointer = root / "sector/current.json"
    before = pointer.read_bytes()
    changed = deepcopy(bundle)
    if failure == "dependency":
        action = json.loads(changed[0][MEMBERS[4]])
        action["baskets_sha256"] = "wrong"
        changed[0][MEMBERS[4]] = _encoded(action)
    elif failure == "identity":
        del changed[1]["sector_view"]
    elif failure in ("core", "history"):
        index = 0 if failure == "core" else 1
        document = json.loads(changed[0][MEMBERS[index]])
        document["sectors"][0]["ticker"] = "XLK"
        changed[0][MEMBERS[index]] = _encoded(document)
    else:
        changed[1]["sector_view"]["source_qualification"] = failure
    _, refused, _ = _publish(tmp_path, changed, generation_id="g2", expected=prior.content_id)
    assert refused.status == "rejected", refused.detail
    assert pointer.read_bytes() == before
    assert not (root / "sector/g2").exists()


def test_incomplete_artifact_set_cannot_skip_final_semantic_admission(tmp_path, bundle):
    sources = _sources(tmp_path, bundle[0], "g1")
    del sources[MEMBERS[-1]]
    with pytest.raises(contract.SectorGenerationContractError, match="invalid_member_set"):
        contract.prepare_sector_generation_request(sources=sources,
            input_identity=bundle[1], generation_id="g1", source_revision="fixture",
            lane="snapshot")


def test_aware_clock_is_required_and_publication_time_cannot_be_future(bundle):
    with pytest.raises(contract.SectorGenerationContractError, match="aware_evaluation_clock"):
        contract.project_sector_bundle(**_arguments(bundle, now=PUBLISHED.replace(tzinfo=None)),
                                       audience="preview")
    with pytest.raises(contract.SectorGenerationContractError, match="future_publication_clock"):
        contract.project_sector_bundle(**_arguments(bundle, published_at="2026-11-04T23:00:00Z"),
                                       audience="preview")


@pytest.mark.parametrize("source", ["2026-11-04", "2026-11-01"])
def test_future_or_non_session_source_is_not_an_accepted_clock(bundle, source):
    bundle[1]["sector_view"]["source_session"] = source
    with pytest.raises(contract.SectorGenerationContractError, match="invalid_source_session"):
        contract.project_sector_bundle(**_arguments(bundle), audience="preview")


def test_mutating_request_identity_cannot_change_the_preflight_contract(tmp_path, bundle):
    request = contract.prepare_sector_generation_request(
        sources=_sources(tmp_path, bundle[0], "g1"), input_identity=bundle[1],
        generation_id="g1", source_revision="fixture", lane="snapshot",
    )
    request.input_identity["sector_view"]["input_version"] = "changed-after-capture"
    orch = publisher.Orchestrator(live_dir=tmp_path / "public/live",
        state_dir=tmp_path / "state", data_dir=tmp_path / "data", now=PUBLISHED)
    result = orch.publish_generation(request, expected_current_content_id=None)
    assert result.status == "rejected"
    assert "sector_identity_changed_during_admission" in result.detail
    assert not (tmp_path / "state/generations/sector/current.json").exists()


@pytest.mark.parametrize("publication", [
    datetime(2026, 11, 2, 23, tzinfo=timezone.utc),
    datetime(2026, 11, 5, 23, tzinfo=timezone.utc),
])
def test_actual_publisher_clock_refuses_backdated_or_delayed_admission(tmp_path, bundle, publication):
    _, result, root = _publish(tmp_path, bundle, now=publication)
    assert result.status == "rejected", result.detail
    assert not (root / "sector/current.json").exists()


def test_original_publication_cannot_precede_the_source_session(tmp_path, bundle):
    _, result, root = _publish(tmp_path, bundle, semantic=False,
        now=datetime(2026, 11, 2, 23, tzinfo=timezone.utc))
    assert result.status == "published"
    with pytest.raises(contract.SectorGenerationContractError, match="source_after_publication"):
        SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED).read_selected_generation(
            api.SectorGenerationRequest("preview"))


def test_developing_at_publication_never_matures_only_because_time_passes(tmp_path, bundle):
    _, result, root = _publish(tmp_path, bundle, semantic=False,
        now=datetime(2026, 11, 3, 16, tzinfo=timezone.utc))
    assert result.status == "published"
    read = SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED).read_selected_generation(
        api.SectorGenerationRequest("preview"))
    assert read.qualification == "degraded"
    assert read.published_at == result.published_at


def test_bundle_callback_receives_the_actual_publication_clock_and_verified_bytes(tmp_path, bundle):
    from dataclasses import replace
    request = contract.prepare_sector_generation_request(
        sources=_sources(tmp_path, bundle[0], "g1"), input_identity=bundle[1],
        generation_id="g1", source_revision="fixture", lane="snapshot")
    seen = []
    original = request.bundle_validator
    def capture(context):
        seen.append(context)
        return original(context)
    request = replace(request, bundle_validator=capture)
    orch = publisher.Orchestrator(live_dir=tmp_path / "public/live",
        state_dir=tmp_path / "state", data_dir=tmp_path / "data", now=PUBLISHED)
    result = orch.publish_generation(request, expected_current_content_id=None)
    assert result.status == "published", result.detail
    assert len(seen) == 1
    assert seen[0].published_at == result.published_at
    assert seen[0].admission_time == PUBLISHED
    assert dict(seen[0].members) == bundle[0]
    with pytest.raises(TypeError):
        seen[0].members[MEMBERS[0]] = b"wrong"
    seen[0].input_identity["sector_view"]["input_version"] = "consumer-change"
    snapshot = publisher.read_selected_generation(generations_root=tmp_path / "state/generations",
        domain="sector", members=MEMBERS)
    assert snapshot.manifest["input_identity"]["sector_view"]["input_version"] == "sector-inputs-v1"


def test_final_bundle_callback_cannot_rewrite_staged_artifacts(tmp_path, bundle):
    from dataclasses import replace
    request = contract.prepare_sector_generation_request(
        sources=_sources(tmp_path, bundle[0], "g1"), input_identity=bundle[1],
        generation_id="g1", source_revision="fixture", lane="snapshot")
    original = request.bundle_validator
    def mutate(context):
        assert original(context) is None
        for member in (tmp_path / "state/generations/sector/.staging").glob("*/" + MEMBERS[0]):
            member.write_bytes(b'{"changed":true}')
        return None
    request = replace(request, bundle_validator=mutate)
    orch = publisher.Orchestrator(live_dir=tmp_path / "public/live",
        state_dir=tmp_path / "state", data_dir=tmp_path / "data", now=PUBLISHED)
    result = orch.publish_generation(request, expected_current_content_id=None)
    assert result.status == "rejected", result.detail
    assert not (tmp_path / "state/generations/sector/current.json").exists()


def test_published_half_day_settlement_reuses_current_owner_without_changing_legacy():
    from lib import nyse_calendar
    source = date(2026, 11, 27)
    before = datetime(2026, 11, 27, 18, 59, tzinfo=timezone.utc)
    after = datetime(2026, 11, 27, 19, tzinfo=timezone.utc)
    assert freshness.evaluate_session_age(source, now=before)["developing"] is True
    settled = freshness.evaluate_session_age(source, now=after)
    assert settled["expected_session"] == source
    assert settled["developing"] is False
    assert settled["calendar_verified"] is True
    assert nyse_calendar.expected_last_session(after) == date(2026, 11, 25)
    full_day = date(2026, 11, 30)
    assert freshness.evaluate_session_age(full_day,
        now=datetime(2026, 11, 30, 21, 59, tzinfo=timezone.utc))["developing"] is True
    assert freshness.evaluate_session_age(full_day,
        now=datetime(2026, 11, 30, 22, tzinfo=timezone.utc))["developing"] is False


@pytest.mark.parametrize("year", [2024, 2025, 2028])
def test_unverified_annual_calendar_never_becomes_verified_fallback(year):
    with pytest.raises(ValueError, match="calendar"):
        freshness.evaluate_session_age(date(year, 11, 3),
            now=datetime(year, 11, 5, 23, tzinfo=timezone.utc))


def test_verified_current_year_does_not_qualify_unverified_prior_year_target():
    with pytest.raises(ValueError, match="coverage"):
        freshness.evaluate_session_age(date(2025, 12, 31),
            now=datetime(2026, 1, 2, 15, tzinfo=timezone.utc))


@pytest.mark.parametrize("original_clock", [
    datetime(2026, 11, 2, 23, tzinfo=timezone.utc),
    datetime(2026, 11, 3, 16, tzinfo=timezone.utc),
    datetime(2026, 11, 4, 23, tzinfo=timezone.utc),
])
@pytest.mark.parametrize("currently_selected", [True, False])
def test_reuse_admits_actual_retained_publication_receipt(tmp_path, bundle,
                                                       original_clock, currently_selected):
    _, original, root = _publish(tmp_path, bundle, semantic=False, now=original_clock)
    assert original.status == "published"
    current = original
    if not currently_selected:
        _, current, _ = _publish(tmp_path, bundle, generation_id="g2",
            expected=original.content_id)
        assert current.status == "published"
    pointer = (root / "sector/current.json").read_bytes()
    _, attempted, _ = _publish(tmp_path, bundle, expected=current.content_id)
    assert attempted.status == "rejected", attempted.detail
    assert (root / "sector/current.json").read_bytes() == pointer


def test_valid_retained_reuse_preserves_original_time_and_checks_current_age(tmp_path, bundle):
    _, original, root = _publish(tmp_path, bundle)
    _, reused, _ = _publish(tmp_path, bundle, expected=original.content_id,
        now=datetime(2026, 11, 4, 23, tzinfo=timezone.utc))
    assert reused.status == "unchanged", reused.detail
    assert reused.published_at == original.published_at
    pointer = (root / "sector/current.json").read_bytes()
    _, stale, _ = _publish(tmp_path, bundle, expected=original.content_id,
        now=datetime(2026, 11, 5, 23, tzinfo=timezone.utc))
    assert stale.status == "rejected", stale.detail
    assert (root / "sector/current.json").read_bytes() == pointer
