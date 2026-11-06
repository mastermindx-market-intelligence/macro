"""Tests for the protected scenario source resolution boundary.

Narrow, meaningful checks: authorization strictly precedes protected IO, zero
protected reads on every refusal path, exact binding enforcement, typed
denied/unavailable distinction (including a false resource answer = denied but
None/unknown/malformed = unavailable), native canonical revision/grant types,
the captured multi-expiry lens/selection contract, the trusted SERVER
destination seam in front of every protected read, concurrent-revoke and
actor-change re-checks, explicit moves absence, and the captured-clock /
current-auth separation. All IO is a fake in-memory object store and all
callbacks are controlled test doubles; no network, no external backend, and no
real rights qualification is claimed or exercised. A green run proves
orchestration only — never a qualified private destination or live authority.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest


from engine import options_hub_retention as ohr
from engine.intelligence_workspace import scenario_source_resolution as ssr

TODAY = ohr.date(2026, 10, 23)
SESSION = "2026-10-22"
BASE = datetime(2026, 10, 23, 14, 0, tzinfo=timezone.utc)
CAPTURED = "2026-10-22T20:15:00Z"
DECIDED = "2026-10-23T14:00:00Z"
EXPIRY = "2026-12-18"
ECONOMIC = "2026-12-18T16:00:00-05:00"
SELECTION = f"{EXPIRY}|{ECONOMIC}"
LENS = {"kind": "one", "exp": EXPIRY}
INVESTIGATION = "3f2b8a4c-9d1e-4a57-b6c8-72e5f0a1d934"
GRANT = "7d3c1f0a-8b2e-4c5d-9a6b-1e0f2a3b4c5d"
BASIS = hashlib.sha256(b"captured protected basis").hexdigest()


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


class SeqClock:
    """Controlled aware clock; pops scripted moments, then holds the last."""

    def __init__(self, moments):
        self._moments = list(moments)

    def __call__(self) -> datetime:
        if len(self._moments) > 1:
            return self._moments.pop(0)
        return self._moments[0]


def gex_raw(session=SESSION, spot=600.25):
    payload = {"schema": ohr.GEX_SCHEMA, "root": "SPY", "asof": session, "spot_ref": spot,
               "by_strike": [{"strike": 600.0, "net": -1.5}]}
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def moves_raw(session=SESSION):
    payload = {"schema": ohr.MOVES_SCHEMA, "root": "SPY", "asof": session,
               "atm_iv": 13.71, "expected_move": {"pct": 1.1, "lo": 593.4, "hi": 606.6}}
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


class Harness:
    """One controlled world: trace, fake store, callbacks, clock, destination.

    Every double here is explicitly NOT live authority: the destination
    qualifier and the source-use decision are controlled test seams that
    evidence orchestration only.
    """

    def __init__(self, *, with_moves=True, gex_bytes=None, moves_bytes=None):
        self.trace: list = []
        self.s3 = FakeS3(self.trace)
        self.gex_bytes = gex_bytes if gex_bytes is not None else gex_raw()
        self.gex_ref = ohr.reference_for_bytes("SPY", "gex", self.gex_bytes, today=TODAY)
        self.moves_ref = None
        if with_moves:
            self.moves_bytes = moves_bytes if moves_bytes is not None else moves_raw()
            self.moves_ref = ohr.reference_for_bytes("SPY", "moves", self.moves_bytes, today=TODAY)
            self.s3.objects[self.moves_ref.key] = self.moves_bytes
        self.s3.objects[self.gex_ref.key] = self.gex_bytes
        self.resource_calls = 0
        self.source_calls = 0
        self.destination_calls = 0
        self.resource_results = [True, True]
        self.source_status = "allowed"
        self.destination_status = "qualified"
        self.binding_overrides: dict = {}
        self.destination_overrides: dict = {}
        self.decided_at = DECIDED
        self.clock = SeqClock([BASE, BASE, BASE])

    @property
    def descriptor(self):
        return ssr.ScenarioSourceDescriptor(
            root="SPY", gex=self.gex_ref, moves=self.moves_ref,
            investigation_id=INVESTIGATION, investigation_revision=4,
            grant_id=GRANT, model_version=ssr.MODEL_VERSION,
            lens=LENS, selection_key=SELECTION, source_as_of=None,
            basis_sha256=BASIS, evaluated_at=CAPTURED, action="evaluate")

    @property
    def viewer(self):
        return ssr.ViewerIdentity("viewer-A", "issuer-1", "epoch-9")

    def resource_access(self, binding):
        self.resource_calls += 1
        self.trace.append(("resource", self.resource_calls))
        result = self.resource_results[min(self.resource_calls - 1, len(self.resource_results) - 1)]
        if result == "raise":
            raise RuntimeError("resource callback failed")
        return result

    def source_use_decision(self, binding):
        self.source_calls += 1
        self.trace.append(("source", self.source_calls))
        if self.source_status == "raise":
            raise RuntimeError("callback failed")
        out = dict(binding)
        out.update(self.binding_overrides)
        return {"status": self.source_status, "binding": out, "policy_id": "policy-1",
                "policy_revision": "p-rev-2", "registry_revision": "registry-3",
                "decided_at": self.decided_at}

    def destination_qualifier(self, request):
        """CONTROLLED trusted-server destination seam; NOT live authority."""
        self.destination_calls += 1
        if self.destination_status == "raise":
            raise RuntimeError("destination backend down")
        out = dict(request)
        out.update(self.destination_overrides)
        return {"status": self.destination_status, "binding": out}

    def resolve(self, **kwargs):
        params = dict(s3=self.s3, bucket="b", destination=self.destination_qualifier,
                      resource_access=self.resource_access,
                      source_use_decision=self.source_use_decision,
                      clock=self.clock)
        params.update(kwargs)
        return ssr.resolve_scenario_source(self.descriptor, self.viewer, **params)


def test_happy_path_resolves_exact_payloads_and_minimal_boundary():
    h = Harness()
    resolved = h.resolve()
    assert resolved.gex == json.loads(h.gex_bytes)
    assert resolved.moves == json.loads(h.moves_bytes)
    assert resolved.moves_status == "resolved"
    assert resolved.evaluated_at == datetime(2026, 10, 22, 20, 15, tzinfo=timezone.utc)
    assert resolved.decided_at == BASE
    assert len(resolved.request.request_id) == 32
    assert uuid.UUID(resolved.request.request_id).version == 4
    boundary = resolved.boundary()
    assert set(boundary) == {"model_version", "action", "investigation_id",
                             "investigation_revision", "moves_status", "source"}
    assert set(boundary["source"]) == {"owner", "root", "session", "source_as_of",
                                       "evaluated_at", "lens", "selection_key",
                                       "basis_sha256", "gex", "moves"}
    serialized = json.dumps(boundary)
    assert "by_strike" not in serialized and "600.25" not in serialized
    source = boundary["source"]
    assert source["gex"] == {"sha256": h.gex_ref.sha256, "byte_length": h.gex_ref.byte_length}
    assert source["moves"] == {"sha256": h.moves_ref.sha256, "byte_length": h.moves_ref.byte_length}
    assert source["evaluated_at"] == CAPTURED
    assert source["lens"] == {"kind": "one", "exp": EXPIRY}
    assert source["selection_key"] == SELECTION
    assert source["source_as_of"] is None  # unknown source clock stays explicit null
    assert source["owner"] == "options_hub" and source["session"] == SESSION


def test_both_authorizations_strictly_precede_any_protected_read():
    h = Harness()
    h.resolve()
    kinds = [entry[0] for entry in h.trace]
    assert kinds.index("resource") == 0
    assert kinds.index("source") == 1
    assert kinds.index("get") > kinds.index("source")
    # The post-IO re-check is the last authorization event.
    assert kinds[-1] == "resource" and kinds.count("resource") == 2
    assert h.resource_calls == 2 and h.source_calls == 1
    # The destination seam qualified the bulk ref set up front and every read.
    assert h.destination_calls >= 3


def test_missing_callbacks_are_typed_unavailable_with_zero_reads():
    for kwargs in ({"resource_access": None}, {"source_use_decision": None}):
        h = Harness()
        with pytest.raises(ssr.ScenarioSourceRefused) as err:
            h.resolve(**kwargs)
        assert err.value.code == "authorization_unavailable"
        assert h.trace == []


def test_historical_grant_alone_never_authorizes():
    # A pinned grant identity is binding context only; with no backend and with
    # a denying backend alike, nothing is read and nothing resolves.
    h = Harness()
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve(resource_access=None, source_use_decision=None)
    assert err.value.code == "authorization_unavailable"
    h2 = Harness()
    h2.resource_results = [False]
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h2.resolve()
    assert err.value.code == "resource_denied"
    assert h2.trace == [("resource", 1)]


def test_resource_false_is_denied_but_none_unknown_and_error_are_unavailable():
    h = Harness()
    h.resource_results = [False]
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    assert err.value.code == "resource_denied"
    assert h.trace == [("resource", 1)]
    for answer, code in ((None, "resource_unavailable"), ("unknown", "resource_unavailable"),
                         ({"granted": True}, "resource_unavailable"), ("raise", "resource_unavailable")):
        h = Harness()
        h.resource_results = [answer]
        with pytest.raises(ssr.ScenarioSourceRefused) as err:
            h.resolve()
        assert err.value.code == code
        assert h.trace == [("resource", 1)]


def test_source_denied_unavailable_and_unknown_are_distinct_with_zero_reads():
    for status, code in (("denied", "source_denied"), ("unavailable", "source_unavailable"),
                         ("whatever", "source_decision_invalid"), ("raise", "source_unavailable")):
        h = Harness()
        h.source_status = status
        with pytest.raises(ssr.ScenarioSourceRefused) as err:
            h.resolve()
        assert err.value.code == code
        assert not any(entry[0] == "get" for entry in h.trace)


@pytest.mark.parametrize("field,value", [
    ("viewer_id", "viewer-B"),
    ("investigation_revision", 999),
    ("model_version", "exposure-scenario/v0"),
    ("lens", "week"),
    ("selection_key", f"{EXPIRY}|{ECONOMIC},{EXPIRY}|2026-12-19T16:00:00-05:00"),
    ("source_as_of", "2026-10-22"),
    ("basis_sha256", "b" * 64),
    ("sha256", "0" * 64),
    ("action", "export"),
    ("evaluated_at", "2026-10-21T20:15:00Z"),
])
def test_any_binding_mismatch_refuses_before_protected_read(field, value):
    h = Harness(with_moves=False)
    h.binding_overrides[field] = value
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    assert err.value.code == "source_decision_invalid"
    assert not any(entry[0] == "get" for entry in h.trace)


def test_moves_ref_binding_mismatch_refuses_before_protected_read():
    h = Harness(with_moves=True)
    h.binding_overrides["moves_ref"] = None  # decision drops the bound moves reference
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    assert err.value.code == "source_decision_invalid"
    assert not any(entry[0] == "get" for entry in h.trace)


def test_wrong_pinned_model_version_refuses_before_any_callback():
    h = Harness()
    descriptor = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=None, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=GRANT, model_version="exposure-scenario/v0",
        lens=LENS, selection_key=SELECTION, source_as_of=None, basis_sha256=BASIS,
        evaluated_at=CAPTURED, action="evaluate")
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        ssr.resolve_scenario_source(descriptor, h.viewer, s3=h.s3, bucket="b",
                                    destination=h.destination_qualifier,
                                    resource_access=h.resource_access,
                                    source_use_decision=h.source_use_decision)
    assert err.value.code == "model_version_unsupported"
    assert h.trace == []


def test_wrong_kind_references_refuse():
    h = Harness(with_moves=False)
    moves_ref = ohr.reference_for_bytes("SPY", "moves", moves_raw(), today=TODAY)
    bad = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=moves_ref, moves=None, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=GRANT, model_version=ssr.MODEL_VERSION,
        lens=LENS, selection_key=SELECTION, source_as_of=None, basis_sha256=BASIS,
        evaluated_at=CAPTURED, action="evaluate")
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        ssr.resolve_scenario_source(bad, h.viewer, s3=h.s3, bucket="b",
                                    destination=h.destination_qualifier,
                                    resource_access=h.resource_access,
                                    source_use_decision=h.source_use_decision)
    assert err.value.code == "request_invalid"
    # A gex reference can never ride in the moves slot either.
    bad2 = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=h.gex_ref, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=GRANT, model_version=ssr.MODEL_VERSION,
        lens=LENS, selection_key=SELECTION, source_as_of=None, basis_sha256=BASIS,
        evaluated_at=CAPTURED, action="evaluate")
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        ssr.resolve_scenario_source(bad2, h.viewer, s3=h.s3, bucket="b",
                                    destination=h.destination_qualifier,
                                    resource_access=h.resource_access,
                                    source_use_decision=h.source_use_decision)
    assert err.value.code == "request_invalid"


def test_captured_clock_is_distinct_from_and_bounded_by_current_auth():
    h = Harness()
    future = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=None, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=GRANT, model_version=ssr.MODEL_VERSION,
        lens=LENS, selection_key=SELECTION, source_as_of=None, basis_sha256=BASIS,
        evaluated_at="2026-10-24T00:00:00Z", action="evaluate")
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        ssr.resolve_scenario_source(future, h.viewer, s3=h.s3, bucket="b",
                                    destination=h.destination_qualifier,
                                    resource_access=h.resource_access,
                                    source_use_decision=h.source_use_decision,
                                    clock=h.clock)
    assert err.value.code == "clock_invalid"
    assert h.trace == []
    naive = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=None, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=GRANT, model_version=ssr.MODEL_VERSION,
        lens=LENS, selection_key=SELECTION, source_as_of=None, basis_sha256=BASIS,
        evaluated_at="2026-10-22 20:15:00", action="evaluate")
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        ssr.resolve_scenario_source(naive, h.viewer, s3=h.s3, bucket="b",
                                    destination=h.destination_qualifier,
                                    resource_access=h.resource_access,
                                    source_use_decision=h.source_use_decision)
    assert err.value.code == "request_invalid"
    # On success the two clocks travel separately and differ.
    resolved = h.resolve()
    assert resolved.evaluated_at != resolved.decided_at
    assert resolved.boundary()["source"]["evaluated_at"] == CAPTURED


def test_decided_at_outside_observed_window_refuses():
    h = Harness()
    h.decided_at = "2026-10-23T15:00:00Z"  # after the held decision clock
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    assert err.value.code == "source_decision_invalid"
    assert not any(entry[0] == "get" for entry in h.trace)


def test_backwards_clock_refuses():
    h = Harness()
    h.clock = SeqClock([BASE, BASE - timedelta(seconds=1), BASE])
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    assert err.value.code == "clock_invalid"
    assert not any(entry[0] == "get" for entry in h.trace)


def test_revocation_during_read_refuses_and_yields_no_output():
    h = Harness()
    h.resource_results = [True, False]  # revoked between the read and the re-check
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    assert err.value.code == "resource_revoked"
    # The protected read genuinely happened, and its result was discarded.
    assert sum(1 for entry in h.trace if entry[0] == "get") == 2
    h = Harness()
    h.resource_results = [True, "raise"]
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    assert err.value.code == "resource_unavailable"
    h = Harness()
    h.resource_results = [True, None]  # an answerless re-check is unavailable, not denied
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    assert err.value.code == "resource_unavailable"


def test_current_actor_change_after_read_refuses():
    h = Harness()
    changed = ssr.ViewerIdentity("viewer-B", "issuer-1", "epoch-9")
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve(current_viewer=lambda: changed)
    assert err.value.code == "current_actor_changed"
    h = Harness()
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve(current_viewer=lambda: (_ for _ in ()).throw(RuntimeError("seam down")))
    assert err.value.code == "resource_unavailable"
    h = Harness()
    resolved = h.resolve(current_viewer=lambda: h.viewer)
    assert resolved.request.viewer_id == "viewer-A"


def test_supplied_moves_absence_is_explicit_never_silent():
    h = Harness(with_moves=False)
    moves_bytes = moves_raw()
    moves_ref = ohr.reference_for_bytes("SPY", "moves", moves_bytes, today=TODAY)
    supplied = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=moves_ref, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=GRANT, model_version=ssr.MODEL_VERSION,
        lens=LENS, selection_key=SELECTION, source_as_of=None, basis_sha256=BASIS,
        evaluated_at=CAPTURED, action="evaluate")
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        ssr.resolve_scenario_source(supplied, h.viewer, s3=h.s3, bucket="b",
                                    destination=h.destination_qualifier,
                                    resource_access=h.resource_access,
                                    source_use_decision=h.source_use_decision,
                                    clock=h.clock)
    assert err.value.code == "retained_missing"
    # The gex object was read, the exact moves key was attempted once, and the
    # missing supplied reference refuses explicitly — never a silent
    # substitution with a null basis.
    gets = [entry[1] for entry in h.trace if entry[0] == "get"]
    assert gets == [h.gex_ref.key, moves_ref.key]


def test_not_supplied_moves_is_explicit_not_a_substitute():
    h = Harness(with_moves=False)
    resolved = h.resolve()
    assert resolved.moves is None and resolved.moves_status == "not_supplied"
    assert resolved.boundary()["source"]["moves"] is None


def test_corrupt_moves_payload_refuses_verification():
    h = Harness(with_moves=False)
    moves_bytes = moves_raw()
    moves_ref = ohr.reference_for_bytes("SPY", "moves", moves_bytes, today=TODAY)
    h.s3.objects[moves_ref.key] = gex_raw()  # wrong artifact under the moves key
    supplied = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=moves_ref, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=GRANT, model_version=ssr.MODEL_VERSION,
        lens=LENS, selection_key=SELECTION, source_as_of=None, basis_sha256=BASIS,
        evaluated_at=CAPTURED, action="evaluate")
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        ssr.resolve_scenario_source(supplied, h.viewer, s3=h.s3, bucket="b",
                                    destination=h.destination_qualifier,
                                    resource_access=h.resource_access,
                                    source_use_decision=h.source_use_decision,
                                    clock=h.clock)
    assert err.value.code == "retained_unavailable"


def test_missing_gex_object_is_typed_after_full_authorization():
    h = Harness(with_moves=False)
    h.s3.objects.pop(h.gex_ref.key)
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    assert err.value.code == "retained_missing"
    # Both authorizations and the destination seam qualified first; the revoke
    # re-check never runs.
    assert h.resource_calls == 1 and h.source_calls == 1 and h.destination_calls >= 2


def test_refusals_never_carry_protected_contents():
    h = Harness()
    h.resource_results = [False]
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    text = str(err.value)
    assert "by_strike" not in text and "600.25" not in text
    h = Harness()
    h.s3.objects.pop(h.gex_ref.key)
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve()
    assert "by_strike" not in str(err.value)


def test_no_network_and_no_serialized_projection_surface():
    source = inspect.getsource(ssr) + inspect.getsource(ohr)
    for token in ("urllib", "requests", "socket", "http.client", "boto3", "botocore",
                  "subprocess", "os.environ", "supabase"):
        assert token not in source
    assert "except ImportError" not in inspect.getsource(ssr)
    assert ssr.__name__ == "engine.intelligence_workspace.scenario_source_resolution"
    assert "engine.intelligence_workspace.scenario_source_resolution" in sys.modules


def test_missing_qualified_destination_blocks_protected_resolution():
    h = Harness()
    with pytest.raises(ssr.ScenarioSourceRefused, match="destination") as err:
        h.resolve(destination=None)
    assert err.value.code == "destination_unavailable"
    assert not any(event[0] == "get" for event in h.trace)
    # Unqualified, unknown, exceptional, mismatched and refusing answers are
    # typed unavailable/denied with zero protected reads.
    for status, overrides, code in (("unknown", {}, "destination_unavailable"),
                                    ("denied", {}, "destination_denied"),
                                    ("raise", {}, "destination_unavailable"),
                                    ("qualified", {"bucket": "other-plane"}, "destination_unavailable"),
                                    ("qualified", {"refs": []}, "destination_unavailable")):
        h = Harness()
        h.destination_status = status
        h.destination_overrides = overrides
        with pytest.raises(ssr.ScenarioSourceRefused, match="destination") as err:
            h.resolve()
        assert err.value.code == code
        assert not any(event[0] == "get" for event in h.trace)


@pytest.mark.parametrize("revision,grant", [
    ("rev-7", GRANT),          # the old textual revision string
    (4, "grant-42"),           # the old textual grant id
    (True, GRANT),             # bool is not an exact positive integer
    (0, GRANT), (-3, GRANT),   # non-positive revisions
    (2147483648, GRANT),       # beyond the native bound
    (4.0, GRANT),              # float is not an exact integer
    (4, "3F2B8A4C-9D1E-4A57-B6C8-72E5F0A1D934"),  # uppercase is not canonical
    (4, "not-a-uuid"),
])
def test_native_canonical_revision_and_grant_types_required(revision, grant):
    h = Harness()
    bad = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=None, investigation_id=INVESTIGATION,
        investigation_revision=revision, grant_id=grant, model_version=ssr.MODEL_VERSION,
        lens=LENS, selection_key=SELECTION, source_as_of=None, basis_sha256=BASIS,
        evaluated_at=CAPTURED, action="evaluate")
    with pytest.raises(ssr.ScenarioSourceRefused, match="request_invalid") as err:
        ssr.resolve_scenario_source(bad, h.viewer, s3=h.s3, bucket="b",
                                    destination=h.destination_qualifier,
                                    resource_access=h.resource_access,
                                    source_use_decision=h.source_use_decision,
                                    clock=h.clock)
    assert h.trace == [] and h.destination_calls == 0


def test_owner_context_none_grant_resolves_with_genuine_resource_callback():
    h = Harness()
    owner = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=None, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=None, model_version=ssr.MODEL_VERSION,
        lens=LENS, selection_key=SELECTION, source_as_of=None, basis_sha256=BASIS,
        evaluated_at=CAPTURED, action="evaluate")
    resolved = ssr.resolve_scenario_source(owner, h.viewer, s3=h.s3, bucket="b",
                                           destination=h.destination_qualifier,
                                           resource_access=h.resource_access,
                                           source_use_decision=h.source_use_decision,
                                           clock=h.clock)
    assert resolved.request.grant_id is None
    assert "grant" not in json.dumps(resolved.boundary())


def test_selection_key_contract_is_native_captured_and_never_flattened():
    # A one-expiry lens with two captured pairs refuses.
    h = Harness(with_moves=False)
    wide = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=None, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=None, model_version=ssr.MODEL_VERSION,
        lens={"kind": "one", "exp": EXPIRY}, selection_key=(f"{EXPIRY}|{ECONOMIC},2026-12-19|2026-12-19T16:00:00-05:00"),
        source_as_of=None, basis_sha256=BASIS, evaluated_at=CAPTURED, action="evaluate")
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        ssr.resolve_scenario_source(wide, h.viewer, s3=h.s3, bucket="b",
                                    destination=h.destination_qualifier,
                                    resource_access=h.resource_access,
                                    source_use_decision=h.source_use_decision,
                                    clock=h.clock)
    assert err.value.code == "request_invalid"
    # Unsorted, duplicated, malformed and oversize captured selections refuse.
    for key in (f"2026-12-19|2026-12-19T16:00:00-05:00,{EXPIRY}|{ECONOMIC}",
                f"{EXPIRY}|{ECONOMIC},{EXPIRY}|{ECONOMIC}",
                f"{EXPIRY}|{ECONOMIC};2026-12-19|2026-12-19T16:00:00-05:00",
                f"{EXPIRY}|2026-12-18", "2026-13-40|2026-12-18T16:00:00-05:00",
                ",".join([f"2027-01-{day:02d}|2027-01-{day:02d}T16:00:00-05:00"
                          for day in range(1, 130)]),
                "x" * (16 * 1024 + 1),
                f"2026-10-01|{ECONOMIC}"):  # expiry precedes the captured session
        bad = ssr.ScenarioSourceDescriptor(
            root="SPY", gex=h.gex_ref, moves=None, investigation_id=INVESTIGATION,
            investigation_revision=4, grant_id=None, model_version=ssr.MODEL_VERSION,
            lens={"kind": "week"}, selection_key=key, source_as_of=None, basis_sha256=BASIS,
            evaluated_at=CAPTURED, action="evaluate")
        with pytest.raises(ssr.ScenarioSourceRefused, match="request_invalid"):
            ssr.resolve_scenario_source(bad, h.viewer, s3=h.s3, bucket="b",
                                        destination=h.destination_qualifier,
                                        resource_access=h.resource_access,
                                        source_use_decision=h.source_use_decision,
                                        clock=h.clock)
    assert h.trace == []
    # A genuine multi-expiry week selection resolves and stays intact: the
    # captured lens/selection is preserved exactly, never flattened to one
    # expiry and never re-evaluated on the current clock.
    week = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=None, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=None, model_version=ssr.MODEL_VERSION,
        lens={"kind": "week"}, selection_key=f"{EXPIRY}|{ECONOMIC},2026-12-19|2026-12-19T16:00:00-05:00",
        source_as_of=None, basis_sha256=BASIS, evaluated_at=CAPTURED, action="evaluate")
    resolved = ssr.resolve_scenario_source(week, h.viewer, s3=h.s3, bucket="b",
                                           destination=h.destination_qualifier,
                                           resource_access=h.resource_access,
                                           source_use_decision=h.source_use_decision,
                                           clock=h.clock)
    source = resolved.boundary()["source"]
    assert source["lens"] == {"kind": "week"}
    assert source["selection_key"] == f"{EXPIRY}|{ECONOMIC},2026-12-19|2026-12-19T16:00:00-05:00"
    assert "," in source["selection_key"]


def test_known_source_clock_is_ordered_and_unknown_stays_null():
    h = Harness(with_moves=False)
    known = ssr.ScenarioSourceDescriptor(
        root="SPY", gex=h.gex_ref, moves=None, investigation_id=INVESTIGATION,
        investigation_revision=4, grant_id=None, model_version=ssr.MODEL_VERSION,
        lens=LENS, selection_key=SELECTION, source_as_of=SESSION, basis_sha256=BASIS,
        evaluated_at=CAPTURED, action="evaluate")
    resolved = ssr.resolve_scenario_source(known, h.viewer, s3=h.s3, bucket="b",
                                           destination=h.destination_qualifier,
                                           resource_access=h.resource_access,
                                           source_use_decision=h.source_use_decision,
                                           clock=h.clock)
    assert resolved.boundary()["source"]["source_as_of"] == SESSION
    for bad_as_of in ("2026-10-24", "2026-02-30", "20261022", 20261022):
        bad = ssr.ScenarioSourceDescriptor(
            root="SPY", gex=h.gex_ref, moves=None, investigation_id=INVESTIGATION,
            investigation_revision=4, grant_id=None, model_version=ssr.MODEL_VERSION,
            lens=LENS, selection_key=SELECTION, source_as_of=bad_as_of,
            basis_sha256=BASIS, evaluated_at=CAPTURED, action="evaluate")
        with pytest.raises(ssr.ScenarioSourceRefused, match="request_invalid"):
            ssr.resolve_scenario_source(bad, h.viewer, s3=h.s3, bucket="b",
                                        destination=h.destination_qualifier,
                                        resource_access=h.resource_access,
                                        source_use_decision=h.source_use_decision,
                                        clock=h.clock)


def test_boundary_never_carries_payload_grant_or_decision_metadata():
    h = Harness()
    resolved = h.resolve()
    serialized = json.dumps(resolved.boundary())
    for forbidden in ("by_strike", "600.25", "atm_iv", GRANT, "policy-1", "p-rev-2",
                      INVESTIGATION.upper()):
        assert forbidden not in serialized


def test_boundary_uses_frozen_reference_lens_object():
    h = Harness()
    source = h.resolve().boundary()["source"]
    assert source["lens"] == {"kind": "one", "exp": EXPIRY}

def test_native_resolution_preserves_aware_source_clock():
    from dataclasses import replace
    h = Harness()
    descriptor = replace(h.descriptor, source_as_of=CAPTURED)
    out = ssr.resolve_scenario_source(descriptor, h.viewer, s3=h.s3, bucket="b",
        destination=h.destination_qualifier, resource_access=h.resource_access,
        source_use_decision=h.source_use_decision, clock=h.clock)
    assert out.boundary()["source"]["source_as_of"] == CAPTURED

def test_zero_lens_rejects_other_expiries_in_captured_selection():
    from dataclasses import replace
    h = Harness()
    selection = f"{SESSION}|{SESSION}T20:00:00Z," + SELECTION
    descriptor = replace(h.descriptor, lens={"kind": "zero"}, selection_key=selection)
    with pytest.raises(ssr.ScenarioSourceRefused, match="request_invalid"):
        ssr.resolve_scenario_source(descriptor, h.viewer, s3=h.s3, bucket="b",
            destination=h.destination_qualifier, resource_access=h.resource_access,
            source_use_decision=h.source_use_decision, clock=h.clock)

def test_one_lens_preserves_multiple_economic_instants_for_one_expiry():
    from dataclasses import replace
    h = Harness()
    selection = f"{EXPIRY}|{EXPIRY}T09:30:00-05:00," + SELECTION
    descriptor = replace(h.descriptor, selection_key=selection)
    out = ssr.resolve_scenario_source(descriptor, h.viewer, s3=h.s3, bucket="b",
        destination=h.destination_qualifier, resource_access=h.resource_access,
        source_use_decision=h.source_use_decision, clock=h.clock)
    assert out.boundary()["source"]["selection_key"] == selection
    assert out.boundary()["source"]["lens"] == {"kind": "one", "exp": EXPIRY}


def test_lowercase_and_fraction_captured_clocks_resolve_verbatim():
    # The capture parser's clock grammar: lowercase t/z and 1-9 fraction digits
    # are accepted and preserved verbatim, never normalized.
    from dataclasses import replace
    h = Harness()
    descriptor = replace(h.descriptor,
                         evaluated_at="2026-10-22t20:15:00.123456789z",
                         selection_key=f"{EXPIRY}|2026-12-18t16:00:00.5-05:00")
    out = ssr.resolve_scenario_source(descriptor, h.viewer, s3=h.s3, bucket="b",
        destination=h.destination_qualifier, resource_access=h.resource_access,
        source_use_decision=h.source_use_decision, clock=h.clock)
    source = out.boundary()["source"]
    assert source["evaluated_at"] == "2026-10-22t20:15:00.123456789z"
    assert source["selection_key"] == f"{EXPIRY}|2026-12-18t16:00:00.5-05:00"
    # Naive and compact-offset forms still refuse with zero reads.
    for bad in ("2026-10-22T20:15:00", "2026-10-22T20:15:00+2400", "2026-10-22T20:15:00.1234567890Z"):
        h2 = Harness()
        with pytest.raises(ssr.ScenarioSourceRefused, match="request_invalid"):
            ssr.resolve_scenario_source(replace(h2.descriptor, evaluated_at=bad), h2.viewer,
                s3=h2.s3, bucket="b", destination=h2.destination_qualifier,
                resource_access=h2.resource_access,
                source_use_decision=h2.source_use_decision, clock=h2.clock)
        assert h2.trace == []


def test_offset_aware_source_clock_is_ordered_exactly_not_by_date_text():
    from dataclasses import replace
    h = Harness()
    # 15:15-05:00 IS 20:15Z — equal to the captured evaluation, so it resolves
    # and stays verbatim.
    ok = replace(h.descriptor, source_as_of="2026-10-22T15:15:00-05:00")
    out = ssr.resolve_scenario_source(ok, h.viewer, s3=h.s3, bucket="b",
        destination=h.destination_qualifier, resource_access=h.resource_access,
        source_use_decision=h.source_use_decision, clock=h.clock)
    assert out.boundary()["source"]["source_as_of"] == "2026-10-22T15:15:00-05:00"
    # 21:15-05:00 IS 2026-10-23T02:15Z — after the captured evaluation, so it
    # refuses even though its declared date text sorts before the evaluation's.
    h2 = Harness()
    late = replace(h2.descriptor, source_as_of="2026-10-22T21:15:00-05:00")
    with pytest.raises(ssr.ScenarioSourceRefused, match="request_invalid"):
        ssr.resolve_scenario_source(late, h2.viewer, s3=h2.s3, bucket="b",
            destination=h2.destination_qualifier, resource_access=h2.resource_access,
            source_use_decision=h2.source_use_decision, clock=h2.clock)
    assert h2.trace == []


def test_source_decision_cannot_mutate_received_request_to_self_approve():
    # A hostile decision seam rewrites the request dict it was handed and
    # answers "allowed": the echo must still be judged against the untouched
    # expected binding, so the tampering is a typed refusal with zero reads.
    h = Harness()
    def evil_decision(binding):
        binding["sha256"] = "0" * 64
        binding["lens"] = "week"
        binding["evaluated_at"] = "2026-10-21T20:15:00Z"
        return {"status": "allowed", "binding": binding, "policy_id": "policy-1",
                "policy_revision": "p-rev-2", "registry_revision": "registry-3",
                "decided_at": DECIDED}
    with pytest.raises(ssr.ScenarioSourceRefused) as err:
        h.resolve(source_use_decision=evil_decision)
    assert err.value.code == "source_decision_invalid"
    assert not any(entry[0] == "get" for entry in h.trace)
    # The trusted descriptor/request state itself is untouched afterwards.
    assert h.descriptor.gex.sha256 != "0" * 64


def test_boundary_rebuild_is_fresh_and_never_aliases_descriptor():
    h = Harness()
    resolved = h.resolve()
    first = resolved.boundary()
    first["source"]["gex"]["sha256"] = "tampered"
    first["source"]["lens"]["exp"] = "1999-01-01"
    second = resolved.boundary()
    assert second is not first and second["source"] is not first["source"]
    assert second["source"]["gex"]["sha256"] == h.gex_ref.sha256
    assert second["source"]["lens"] == {"kind": "one", "exp": EXPIRY}
    assert resolved.descriptor.gex.sha256 == h.gex_ref.sha256


def test_joined_descriptor_accepts_exact_wire_lens_object():
    from dataclasses import replace
    h = Harness()
    d = replace(h.descriptor, lens={"kind": "one", "exp": EXPIRY})
    out = ssr.resolve_scenario_source(d, h.viewer, s3=h.s3, bucket="b", destination=h.destination_qualifier,
        resource_access=h.resource_access, source_use_decision=h.source_use_decision, clock=h.clock)
    assert out.boundary()["source"]["lens"] == d.lens
    assert out.request.as_dict()["lens"] == d.lens


def test_joined_source_clock_before_session_is_retained_not_reinterpreted():
    from dataclasses import replace
    h = Harness()
    d = replace(h.descriptor, source_as_of="2026-10-21")
    out = ssr.resolve_scenario_source(d, h.viewer, s3=h.s3, bucket="b", destination=h.destination_qualifier,
        resource_access=h.resource_access, source_use_decision=h.source_use_decision, clock=h.clock)
    assert out.boundary()["source"]["source_as_of"] == "2026-10-21"


def test_joined_session_floor_uses_declared_evaluation_date_not_utc_date():
    from dataclasses import replace
    h = Harness()
    d = replace(h.descriptor, evaluated_at="2026-10-22T00:15:00+14:00")
    out = ssr.resolve_scenario_source(d, h.viewer, s3=h.s3, bucket="b", destination=h.destination_qualifier,
        resource_access=h.resource_access, source_use_decision=h.source_use_decision, clock=h.clock)
    assert out.boundary()["source"]["evaluated_at"] == d.evaluated_at


def test_joined_lens_binding_is_detached_from_mutating_authorizer():
    h = Harness()
    def mutating_decision(binding):
        binding["lens"]["exp"] = "1999-01-01"
        return {"status": "allowed", "binding": binding, "policy_id": "policy-1",
                "policy_revision": "p-rev-2", "registry_revision": "registry-3", "decided_at": DECIDED}
    with pytest.raises(ssr.ScenarioSourceRefused, match="source_decision_invalid"):
        h.resolve(source_use_decision=mutating_decision)
    assert not any(entry[0] == "get" for entry in h.trace)
    assert h.descriptor.lens == {"kind": "one", "exp": EXPIRY}


def test_joined_one_lens_exp_is_explicit_and_string_lens_refuses_before_io():
    from dataclasses import replace
    for lens in ("one", {"kind": "one", "exp": "2026-12-19"}, {"kind": "all", "exp": EXPIRY}):
        h = Harness()
        with pytest.raises(ssr.ScenarioSourceRefused, match="request_invalid"):
            ssr.resolve_scenario_source(replace(h.descriptor, lens=lens), h.viewer, s3=h.s3, bucket="b",
                destination=h.destination_qualifier, resource_access=h.resource_access,
                source_use_decision=h.source_use_decision, clock=h.clock)
        assert h.trace == []


def test_joined_wire_root_refuses_nonterminal_alphabet_before_io():
    from dataclasses import replace
    for root in ("SPY.X-X", "ABCDEFGHIJKLM"):
        h = Harness()
        d = replace(h.descriptor, root=root, gex=replace(h.gex_ref, root=root), moves=None)
        with pytest.raises(ssr.ScenarioSourceRefused, match="request_invalid"):
            ssr.resolve_scenario_source(d, h.viewer, s3=h.s3, bucket="b", destination=h.destination_qualifier,
                resource_access=h.resource_access, source_use_decision=h.source_use_decision, clock=h.clock)
        assert h.trace == []


def test_joined_captured_clock_cannot_be_nanoseconds_after_current_authorization():
    from dataclasses import replace
    h = Harness()
    d = replace(h.descriptor, evaluated_at="2026-10-23T14:00:00.000000001Z")
    with pytest.raises(ssr.ScenarioSourceRefused, match="clock_invalid"):
        ssr.resolve_scenario_source(d, h.viewer, s3=h.s3, bucket="b", destination=h.destination_qualifier,
            resource_access=h.resource_access, source_use_decision=h.source_use_decision, clock=h.clock)
    assert h.trace == []


def test_protected_transport_retains_exact_bytes_but_generic_boundary_never_does():
    h = Harness()
    resolved = h.resolve()
    assert resolved.gex_bytes == h.gex_bytes
    assert resolved.moves_bytes == h.moves_bytes
    boundary = json.dumps(resolved.boundary())
    assert "gex_bytes" not in boundary and "moves_bytes" not in boundary
    assert "by_strike" not in boundary and "atm_iv" not in boundary
    assert repr(h.gex_bytes) not in repr(resolved)
    assert "spot_ref" not in repr(resolved) and "atm_iv" not in repr(resolved)
