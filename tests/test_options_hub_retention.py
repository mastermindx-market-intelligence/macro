"""Tests for typed Options Hub exact-byte retention.

Narrow, meaningful checks only: exact-byte survival across mutable head/date
changes, absence without fallback, strict binding refusals, conditional-create
reconciliation, retention-before-publication ordering, and the two fail-closed
seams — trusted SERVER destination qualification (required before any get or
put on every IO surface) and the fresh trusted native retention decision
(required before any retain/publish; the RetentionAction record alone never
authorizes). All IO is a fake in-memory object store; no network and no
external backend is touched or claimed. The controlled destination and decision
doubles below are explicitly NOT live authority: a green run here proves
orchestration only and never qualifies a private bucket, a real destination
receipt or production rights.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from datetime import date

import pytest


from engine import options_hub_retention as ohr

TODAY = date(2026, 10, 23)
SESSION = "2026-10-22"
FUTURE = "2999-01-01"


class Body:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0
        self.closed = False

    def read(self, n: int) -> bytes:
        if self._pos >= len(self._data):
            return b""
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True


class FakeS3:
    """Bounded fake: records every operation and never touches a network."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.declared: dict[str, int] = {}
        self.log: list[tuple] = []
        self.put_error: str | None = None
        self.put_reveal: bytes | None = None

    def get_object(self, Bucket, Key):
        self.log.append(("get", Key))
        if Key not in self.objects:
            err = OSError("no such key")
            err.response = {"Error": {"Code": "NoSuchKey"}}
            raise err
        data = self.objects[Key]
        return {"Body": Body(data), "ContentLength": self.declared.get(Key, len(data))}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.log.append(("put", Key))
        if self.put_reveal is not None:
            self.objects[Key] = self.put_reveal
        if self.put_error == "always" or (self.put_error == "conflict" and Key in self.objects):
            err = OSError("conditional create failed")
            err.response = {"Error": {"Code": "ConditionalRequestFailed"}}
            raise err
        self.objects[Key] = bytes(Body)


def controlled_destination(*, bucket="b", status="qualified", overrides=None, fail=False):
    """CONTROLLED stand-in for the trusted server destination qualification
    backend. It echoes the exact binding and answers ``qualified``. This is
    explicitly NOT live authority: no real bucket, no genuine destination
    receipt, no private-ACL proof — orchestration evidence for tests only."""
    def qualifier(request):
        if fail:
            raise RuntimeError("destination backend down")
        out = dict(request)
        out.update(overrides or {})
        return {"status": status, "binding": out}
    return qualifier


def controlled_decision(*, status="allowed", overrides=None, fail=False):
    """CONTROLLED stand-in for the fresh trusted native retention decision
    backend. Explicitly NOT live authority and not a minted rights receipt."""
    def decide(binding):
        if fail:
            raise RuntimeError("decision backend down")
        out = dict(binding)
        out.update(overrides or {})
        return {"status": status, "binding": out}
    return decide


def gex_bytes(root="SPY", session=SESSION, schema=None, spot=600.25):
    payload = {"schema": schema or ohr.GEX_SCHEMA, "root": root, "asof": session,
               "spot_ref": spot, "by_strike": [{"strike": 600.0, "net": -1.5}]}
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def moves_bytes(root="SPY", session=SESSION, schema=None):
    payload = {"schema": schema or ohr.MOVES_SCHEMA, "root": root, "asof": session,
               "atm_iv": 13.71, "expected_move": {"pct": 1.1, "lo": 593.4, "hi": 606.6}}
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def ref_for(raw, root="SPY", kind="gex"):
    return ohr.reference_for_bytes(root, kind, raw, today=TODAY)


def seed_head_and_dated(s3, root="SPY"):
    """The mutable head and dated objects the incumbent publisher maintains."""
    s3.objects[f"options_hub/gex/{root}.json"] = gex_bytes()
    s3.objects[f"options_hub/gex_history/{root}/{SESSION}.json"] = gex_bytes()


def test_exact_bytes_survive_mutable_head_and_date_changes():
    s3, raw = FakeS3(), gex_bytes()
    ref = ref_for(raw)
    ohr.retain_snapshot(s3, "b", ref, raw, today=TODAY,
                        destination=controlled_destination())
    assert s3.log == [("get", ref.key), ("put", ref.key)]
    seed_head_and_dated(s3)
    # The mutable head and dated object change afterwards, as the nightly run does.
    s3.objects["options_hub/gex/SPY.json"] = gex_bytes(spot=999.0)
    s3.objects[f"options_hub/gex_history/SPY/{SESSION}.json"] = gex_bytes(spot=888.0)
    assert ohr.load_snapshot(s3, "b", ref, today=TODAY,
                             destination=controlled_destination()) == raw
    # Only the exact sha256 key was ever written; no head, no dated key.
    assert [op for op in s3.log if op[0] == "put"] == [("put", ref.key)]


def test_missing_exact_object_has_no_fallback_to_head_or_date():
    s3, raw = FakeS3(), gex_bytes()
    ref = ref_for(raw)
    seed_head_and_dated(s3)  # same payload sits under the mutable keys
    with pytest.raises(ohr.MissingRetainedObject):
        ohr.load_snapshot(s3, "b", ref, today=TODAY, destination=controlled_destination())
    # One attempt, the exact key only; no head, dated or cache substitute read.
    assert s3.log == [("get", ref.key)]


def test_digest_length_and_contentlength_mismatch_refused():
    s3, raw = FakeS3(), gex_bytes()
    ref = ref_for(raw)
    dest = controlled_destination()
    s3.objects[ref.key] = gex_bytes(spot=1.0)
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.load_snapshot(s3, "b", ref, today=TODAY, destination=dest)
    s3.objects[ref.key] = raw[:-1]
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.load_snapshot(s3, "b", ref, today=TODAY, destination=dest)
    s3.objects[ref.key] = raw
    s3.declared[ref.key] = len(raw) - 1
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.load_snapshot(s3, "b", ref, today=TODAY, destination=dest)


def test_trailing_stream_hidden_by_declared_length_refused():
    s3, raw = FakeS3(), gex_bytes()
    ref = ref_for(raw)
    s3.objects[ref.key] = raw + b'{"trail":true}'
    s3.declared[ref.key] = len(raw)
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.load_snapshot(s3, "b", ref, today=TODAY, destination=controlled_destination())


def test_session_mismatch_refused_on_canonical_reference():
    raw = gex_bytes()
    ref = ref_for(raw)
    wrong = ohr.SnapshotReference(ref.root, ref.kind, ref.sha256, ref.byte_length, "2026-10-21")
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.verify_snapshot(wrong, raw, today=TODAY)


def test_root_schema_and_kind_mismatch_refused():
    s3 = FakeS3()
    foreign_root = gex_bytes(root="QQQ")
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(foreign_root)  # payload root disagrees with the requested root
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(gex_bytes(schema="options_structure.matrix/v1"))
    # A gex payload is never accepted as moves and the reverse.
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(gex_bytes(), kind="moves")
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(moves_bytes(schema="options_structure.matrix/v1"), kind="moves")
    moves_ref = ref_for(moves_bytes(), kind="moves")
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.parse_reference(moves_ref.root, "gex", moves_ref.version_ref, moves_ref.sha256)
    # The incumbent untyped matrix reference grammar never parses here.
    digest = hashlib.sha256(gex_bytes()).hexdigest()
    untyped = f"sha256:{digest}:bytes:{len(gex_bytes())}:session:{SESSION}"
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.parse_reference("SPY", "gex", untyped, digest)


def test_duplicate_nonfinite_and_malformed_json_refused():
    head = b'{"schema":"options_hub.gex/v1","schema":"options_hub.gex/v1","root":"SPY","asof":"%s"}' % SESSION.encode()
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(head)
    nan = ('{"schema":"%s","root":"SPY","asof":"%s","spot_ref":NaN}'
           % (ohr.GEX_SCHEMA, SESSION)).encode()
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(nan)
    huge = ('{"schema":"%s","root":"SPY","asof":"%s","spot_ref":1e400}'
            % (ohr.GEX_SCHEMA, SESSION)).encode()
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(huge)
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(b"{not json")


def test_future_and_malformed_session_refused():
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(gex_bytes(session=FUTURE))
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(gex_bytes(session="20261022"))
    missing = json.dumps({"schema": ohr.GEX_SCHEMA, "root": "SPY"}).encode()
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(missing)


def test_oversize_refused():
    big = b"x" * (ohr.MAX_MOVES_BYTES + 1)
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(big, kind="moves")
    digest = hashlib.sha256(gex_bytes()).hexdigest()
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.parse_reference("SPY", "gex",
                            f"sha256:{digest}:bytes:{ohr.MAX_GEX_BYTES + 1}:kind:gex:session:{SESSION}",
                            digest)


def test_artifact_limits_align_with_frozen_reference_bounds():
    assert ohr.MAX_GEX_BYTES == 8 * 1024 * 1024
    assert ohr.MAX_MOVES_BYTES == 1 * 1024 * 1024
    # A body that the old 2 MiB bound would have allowed is now refused.
    with pytest.raises(ohr.RetentionUnavailable):
        ref_for(b"x" * (2 * 1024 * 1024), kind="moves")


def test_retain_idempotent_and_collision_refused():
    s3, raw = FakeS3(), gex_bytes()
    ref = ref_for(raw)
    dest = controlled_destination()
    ohr.retain_snapshot(s3, "b", ref, raw, today=TODAY, destination=dest)
    ohr.retain_snapshot(s3, "b", ref, raw, today=TODAY, destination=dest)
    assert [op for op in s3.log if op[0] == "put"] == [("put", ref.key)]
    # A corrupted object under the exact key is a collision, never overwritten.
    s3.objects[ref.key] = gex_bytes(spot=2.0)
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.retain_snapshot(s3, "b", ref, raw, today=TODAY, destination=dest)
    assert bytes(s3.objects[ref.key]) == gex_bytes(spot=2.0)


def test_same_key_conflict_reconciles_once_without_overwrite():
    s3, raw = FakeS3(), gex_bytes()
    ref = ref_for(raw)
    s3.put_error = "conflict"
    s3.put_reveal = raw  # a racing writer commits the same exact bytes at the put
    ohr.retain_snapshot(s3, "b", ref, raw, today=TODAY, destination=controlled_destination())
    assert [op for op in s3.log if op[0] == "put"] == [("put", ref.key)]
    assert s3.objects[ref.key] == raw


def test_committed_but_errored_put_reconciles_same_key():
    s3, raw = FakeS3(), gex_bytes()
    ref = ref_for(raw)
    s3.put_error = "always"
    s3.put_reveal = raw  # the store committed before the error was returned
    ohr.retain_snapshot(s3, "b", ref, raw, today=TODAY, destination=controlled_destination())
    assert s3.objects[ref.key] == raw


def test_lost_put_response_is_typed_uncertain_without_new_key():
    s3, raw = FakeS3(), gex_bytes()
    ref = ref_for(raw)
    s3.put_error = "always"
    with pytest.raises(ohr.RetentionUncertain):
        ohr.retain_snapshot(s3, "b", ref, raw, today=TODAY,
                            destination=controlled_destination())
    assert [op for op in s3.log if op[0] == "put"] == [("put", ref.key)]
    assert ref.key not in s3.objects


def test_retain_before_publish_orders_and_publishes_once():
    s3 = FakeS3()
    gex_raw, moves_raw = gex_bytes(), moves_bytes()
    gex_ref, moves_ref = ref_for(gex_raw), ref_for(moves_raw, kind="moves")
    artifacts = [(gex_ref, gex_raw), (moves_ref, moves_raw)]

    def publish():
        s3.log.append(("publish", None))

    outcome = ohr.retain_before_publish(
        s3, "b", artifacts, publish,
        action=ohr.RetentionAction("caller-x", "saved replay"),
        retention_decision=controlled_decision(),
        destination=controlled_destination())
    assert outcome.published is True
    assert outcome.retained == (gex_ref.version_ref, moves_ref.version_ref)
    assert s3.log == [("get", gex_ref.key), ("put", gex_ref.key),
                      ("get", moves_ref.key), ("put", moves_ref.key),
                      ("publish", None)]


def test_zero_publish_on_retention_failure():
    # Every ref and body is validated BEFORE the first effect, so a malformed
    # second artifact leaves zero IO at all — never a partial first effect.
    s3 = FakeS3()
    gex_ref, moves_ref = ref_for(gex_bytes()), ref_for(moves_bytes(), kind="moves")
    corrupt = gex_bytes(spot=7.0)  # a gex payload can never verify as the moves artifact
    artifacts = [(gex_ref, gex_bytes()), (moves_ref, corrupt)]
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.retain_before_publish(s3, "b", artifacts, lambda: s3.log.append(("publish", None)),
                                  action=ohr.RetentionAction("caller-x", "saved replay"),
                                  retention_decision=controlled_decision(),
                                  destination=controlled_destination())
    assert ("publish", None) not in s3.log
    assert s3.log == []


def test_partial_effect_on_mid_io_failure_stays_explicit():
    # The second artifact verifies up front but collides during IO: the first
    # effect genuinely happened and no publication runs.
    s3 = FakeS3()
    gex_ref, moves_ref = ref_for(gex_bytes()), ref_for(moves_bytes(), kind="moves")
    # A different, individually valid payload already sits under the moves key.
    s3.objects[moves_ref.key] = json.dumps(
        {"schema": ohr.MOVES_SCHEMA, "root": "SPY", "asof": SESSION,
         "atm_iv": 0.0, "expected_move": {"pct": 0.0, "lo": 0.0, "hi": 0.0}},
        separators=(",", ":"), sort_keys=True).encode()
    artifacts = [(gex_ref, gex_bytes()), (moves_ref, moves_bytes())]
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.retain_before_publish(s3, "b", artifacts, lambda: s3.log.append(("publish", None)),
                                  action=ohr.RetentionAction("caller-x", "saved replay"),
                                  retention_decision=controlled_decision(),
                                  destination=controlled_destination())
    assert ("publish", None) not in s3.log
    assert [op for op in s3.log if op[0] == "put"] == [("put", gex_ref.key)]


def test_missing_authorization_performs_no_io_and_never_publishes():
    s3 = FakeS3()
    ref = ref_for(gex_bytes())
    for action in (None, True, {"authority": "x"}, ohr.RetentionAction("", "p"),
                   ohr.RetentionAction("a", " ")):
        with pytest.raises(ohr.RetentionUnauthorized):
            ohr.retain_before_publish(s3, "b", [(ref, gex_bytes())],
                                      lambda: s3.log.append(("publish", None)), action=action)
    assert s3.log == []
    # A non-callable dependent publication is refused before any IO too.
    with pytest.raises(ohr.RetentionUnavailable):
        ohr.retain_before_publish(s3, "b", [(ref, gex_bytes())], None,
                                  action=ohr.RetentionAction("a", "p"))
    assert s3.log == []


def test_retention_action_alone_performs_no_io_and_never_publishes():
    # The action record is context only; without a fresh trusted native
    # decision backend nothing is read, written or published.
    s3 = FakeS3()
    ref = ref_for(gex_bytes())
    for decision in (None, "backend", 42):
        with pytest.raises(ohr.RetentionDecisionUnavailable):
            ohr.retain_before_publish(s3, "b", [(ref, gex_bytes())],
                                      lambda: s3.log.append(("publish", None)),
                                      action=ohr.RetentionAction("caller-x", "saved replay"),
                                      retention_decision=decision,
                                      destination=controlled_destination())
    assert s3.log == []


def test_fresh_retention_decision_denied_unavailable_or_mismatched_is_zero_io():
    s3 = FakeS3()
    ref = ref_for(gex_bytes())
    artifacts = [(ref, gex_bytes())]
    publish = lambda: s3.log.append(("publish", None))  # noqa: E731
    with pytest.raises(ohr.RetentionDenied):
        ohr.retain_before_publish(s3, "b", artifacts, publish,
                                  action=ohr.RetentionAction("caller-x", "saved replay"),
                                  retention_decision=controlled_decision(status="denied"),
                                  destination=controlled_destination())
    for kwargs in ({"status": "unavailable"}, {"status": "who-knows"}, {"fail": True},
                   {"overrides": {"principal": "someone-else"}},
                   {"overrides": {"refs": ["sha256:" + "0" * 64 + ":bytes:1:kind:gex:session:" + SESSION]}}):
        with pytest.raises(ohr.RetentionDecisionUnavailable):
            ohr.retain_before_publish(s3, "b", artifacts, publish,
                                      action=ohr.RetentionAction("caller-x", "saved replay"),
                                      retention_decision=controlled_decision(**kwargs),
                                      destination=controlled_destination())
    assert s3.log == []


def test_destination_seam_gates_every_io_surface():
    s3, raw = FakeS3(), gex_bytes()
    ref = ref_for(raw)
    s3.objects[ref.key] = raw
    # The default (no configured backend) is a typed refusal BEFORE any get/put.
    for call in (lambda: ohr.load_snapshot(s3, "b", ref, today=TODAY),
                 lambda: ohr.load_verified(s3, "b", ref, today=TODAY),
                 lambda: ohr.retain_snapshot(s3, "b", ref, raw, today=TODAY),
                 lambda: ohr.retain_before_publish(s3, "b", [(ref, raw)],
                                                   lambda: s3.log.append(("publish", None)),
                                                   action=ohr.RetentionAction("a", "p"))):
        with pytest.raises(ohr.DestinationUnavailable, match="destination"):
            call()
    assert s3.log == []
    # Unqualified, unknown, exceptional and mismatched answers all refuse.
    for dest in (controlled_destination(status="unknown"),
                 controlled_destination(status="public-plane"),
                 controlled_destination(fail=True),
                 controlled_destination(overrides={"bucket": "other-bucket"}),
                 controlled_destination(overrides={"owner": "someone_else"}),
                 controlled_destination(overrides={"refs": []}),
                 "b"):
        with pytest.raises(ohr.RetentionUnavailable, match="destination"):
            ohr.load_snapshot(s3, "b", ref, today=TODAY, destination=dest)
    assert s3.log == []
    # An explicit trusted refusal is a typed denial, still zero IO.
    with pytest.raises(ohr.DestinationDenied, match="destination"):
        ohr.load_snapshot(s3, "b", ref, today=TODAY,
                          destination=controlled_destination(status="denied"))
    assert s3.log == []


def test_missing_qualified_destination_blocks_retention_and_publication():
    s3 = FakeS3()
    raw = gex_bytes()
    ref = ref_for(raw)
    with pytest.raises(ohr.RetentionUnavailable, match="destination"):
        ohr.retain_before_publish(s3, "unqualified-public-plane", [(ref, raw)],
                                  lambda: s3.log.append(("publish", None)),
                                  action=ohr.RetentionAction("caller-string", "scenario"))
    assert s3.log == []


def test_missing_qualified_destination_blocks_exact_get():
    s3 = FakeS3()
    raw = gex_bytes()
    ref = ref_for(raw)
    s3.objects[ref.key] = raw
    with pytest.raises(ohr.RetentionUnavailable, match="destination"):
        ohr.load_snapshot(s3, "unqualified-public-plane", ref, today=TODAY)
    assert s3.log == []


def test_moves_roundtrip_and_load_verified_payload():
    s3, raw = FakeS3(), moves_bytes()
    ref = ref_for(raw, kind="moves")
    ohr.retain_snapshot(s3, "b", ref, raw, today=TODAY, destination=controlled_destination())
    loaded, payload = ohr.load_verified(s3, "b", ref, today=TODAY,
                                        destination=controlled_destination())
    assert loaded == raw and payload["schema"] == ohr.MOVES_SCHEMA
    assert ohr.verify_snapshot(ref, raw, today=TODAY)["asof"] == SESSION


def test_destination_callback_cannot_mutate_shared_refs_to_self_approve():
    # A hostile seam appends a foreign ref to the very list it was handed and
    # answers "qualified": the echo must be judged against the refs frozen
    # before the call, so the shared-list mutation is a typed refusal with
    # zero IO — never a self-approved binding.
    s3, raw = FakeS3(), gex_bytes()
    ref = ref_for(raw)
    s3.objects[ref.key] = raw
    seen = []

    def evil_destination(request):
        seen.append({"refs": list(request["refs"])})
        request["refs"].append("sha256:" + "f" * 64 + ":bytes:1:kind:gex:session:" + SESSION)
        return {"status": "qualified", "binding": request}

    with pytest.raises(ohr.RetentionUnavailable, match="destination"):
        ohr.load_snapshot(s3, "b", ref, today=TODAY, destination=evil_destination)
    assert s3.log == []
    assert seen[0]["refs"] == [ref.version_ref]  # the request itself was exact


def test_decision_callback_cannot_mutate_shared_binding_refs_to_self_approve():
    # The same attack against the fresh retention decision: rewriting the
    # handed-down refs list in place must not rewrite the expected binding.
    s3 = FakeS3()
    ref = ref_for(gex_bytes())
    seen = []

    def evil_decision(binding):
        seen.append({"refs": list(binding["refs"])})
        binding["refs"][:] = ["sha256:" + "0" * 64 + ":bytes:1:kind:gex:session:" + SESSION]
        return {"status": "allowed", "binding": binding}

    with pytest.raises(ohr.RetentionDecisionUnavailable):
        ohr.retain_before_publish(s3, "b", [(ref, gex_bytes())],
                                  lambda: s3.log.append(("publish", None)),
                                  action=ohr.RetentionAction("caller-x", "saved replay"),
                                  retention_decision=evil_decision,
                                  destination=controlled_destination())
    assert s3.log == []
    assert seen[0]["refs"] == [ref.version_ref]  # the request itself was exact


def test_no_network_and_no_storage_sdk_surface_and_no_flat_fallback():
    source = inspect.getsource(ohr)
    for token in ("urllib", "requests", "socket", "http.client", "boto3", "botocore",
                  "subprocess", "os.environ"):
        assert token not in source
    # The production module imports only through the normal package path; the
    # broad flat-layout ImportError fallback is gone, so unrelated shadow
    # modules can never stand in for engine.options_hub_retention.
    assert "except ImportError" not in source
    assert ohr.__name__ == "engine.options_hub_retention"
    assert "engine.options_hub_retention" in sys.modules
