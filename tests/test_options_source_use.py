"""Fail-closed Options source-use policy adapter; synthetic evidence in tmp only.

Every positive answer below traces to exact synthetic bytes written into the
test's own tmp tree, digest-pinned by the test acting as the operator, plus a
test-owned trusted resolver that synthesizes the intended
``ServerUseContext`` from a captured intended request. Real registry
vocabulary (``lib.dataos.registry``), no network, no repo policy rows, no
persisted decisions. The composed-resolver tests need the repo's selection
fixtures and skip cleanly where those are absent.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.intelligence_workspace import options_source_use as M
from engine.intelligence_workspace.options_use import OptionUseRequest
from lib.dataos.registry import DatasetContract, Registry

NOW = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)

DATASET_ID = "options_matrix_raw"
VENDOR = "syntheticvendor"
DATASET_VERSION = "1"
FAMILY = "synthetic.options-matrix"
POINTER = "docs/research/options/matrix-use.policy.json"
PRINCIPAL = "principal-alice"
ISSUER = "https://auth.synthetic.invalid"
EPOCH = "epoch-77"
RESPONSE_KEYS = {
    "status", "binding", "source_family", "policy_id",
    "policy_revision", "registry_revision", "decided_at",
}
_UNSET = object()


def policy_record(**changes):
    record = {
        "policy_id": "pol-options-matrix-2026-10",
        "policy_revision": "rev-2026-10-21a",
        "registry_revision": "reg-2026-10-21",
        "source_family": FAMILY,
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "vendor": VENDOR,
        "state": "active",
        "known_at": "2026-09-01T00:00:00Z",
        "effective_from": "2026-10-01T00:00:00Z",
        "effective_until": "2026-11-01T00:00:00Z",
        "evidence_revision": "ev-7",
        "source_sessions": None,
        "actions": {
            "display": {
                "allowed": True,
                "fields": ["strike", "bid_raw"],
                "output": "derived",
                "channel": "server_display",
                "recipients": ["authenticated_customer"],
                "customer_scope": "named_authenticated_principal",
                "principal_id": PRINCIPAL,
                "principal_issuer": ISSUER,
                "auth_epoch": EPOCH,
                "customer_id": PRINCIPAL,
                "required_rights": {
                    "internal_computation": (
                        "rendering the captured matrix inside the product for this signed-in principal"
                    ),
                },
            },
            "export": {
                "allowed": True,
                "fields": ["strike", "ask_raw"],
                "output": "raw",
                "channel": "server_file_export",
                "recipients": ["authenticated_customer"],
                "customer_scope": "named_authenticated_principal",
                "principal_id": PRINCIPAL,
                "principal_issuer": ISSUER,
                "auth_epoch": EPOCH,
                "customer_id": PRINCIPAL,
                "required_rights": {
                    "redistribution": (
                        "handing the captured snapshot bytes to this signed-in customer as a file"
                    ),
                },
            },
        },
    }
    record.update(changes)
    return record


def source_contract(pointer=None, **changes):
    lawful = pointer if pointer is not None else POINTER
    data = {
        "dataset_id": DATASET_ID,
        "layer": "L0",
        "owner": "options_structure.matrix",
        "producer": "collectors.options_matrix",
        "storage": "object",
        "format": "jsonl",
        "grain": ["security_id", "expiry", "strike"],
        "temporal_profile": "SNAPSHOT_SERIES",
        "version": "1",
        "status": "PRODUCED",
        "vendor": VENDOR,
        "schema": {
            "strike": {"type": "number"},
            "bid_raw": {"basis": "raw"},
            "ask_raw": {"basis": "raw"},
        },
        "rights": {
            "purchase_access": "unverified",
            "internal_computation": "granted",
            "redistribution": "granted",
            "evidence": {
                "internal_computation": lawful,
                "redistribution": lawful,
            },
        },
    }
    data.update(changes)
    return DatasetContract.from_mapping(data)


def make_request(**changes):
    values = {
        "request_id": uuid.uuid4().hex,
        "principal_id": PRINCIPAL,
        "principal_issuer": ISSUER,
        "auth_epoch": EPOCH,
        "owner": "options_structure.matrix",
        "schema": "options_structure.matrix/v1",
        "root": "SYN",
        "sha256": "a" * 64,
        "byte_length": 4096,
        "session": "session-2026-10-21",
        "vendor": VENDOR,
        "underlying_id": "SEC:US-XXXX-SYNTH",
        "selection_sha256": "b" * 64,
        "action": "display",
    }
    values.update(changes)
    return OptionUseRequest(**values)


_INTENDED_PER_ACTION = {
    "display": {
        "fields": ("strike", "bid_raw"),
        "output": "derived",
        "channel": "server_display",
        "recipients": ("authenticated_customer",),
        "required_rights": ("internal_computation",),
    },
    "export": {
        "fields": ("strike", "ask_raw"),
        "output": "raw",
        "channel": "server_file_export",
        "recipients": ("authenticated_customer",),
        "required_rights": ("redistribution",),
    },
}


def intended_context(request, **changes):
    """The test-owned trusted server's intended use for *request*.

    Synthetic scope records only: this is the test acting as the audited
    server integration, never a mapping the adapter itself could infer.
    """
    values = {
        "binding": request,
        "dataset_id": DATASET_ID,
        "vendor": request.vendor,
        "source_family": FAMILY,
        "customer_id": request.principal_id,
    }
    values.update(_INTENDED_PER_ACTION[request.action])
    values.update(changes)
    return M.ServerUseContext(**values)


def fresh_resolver(**overrides):
    """A trusted resolver synthesizing the intended use per incoming request."""
    def resolve(request):
        return intended_context(request, **overrides)
    return resolve


def pinned_resolver(context):
    """A trusted resolver captured before the call: it answers with one context."""
    def resolve(_request):
        return context
    return resolve


def policy_bytes(record=None):
    return json.dumps(record or policy_record(), indent=2, sort_keys=True).encode(
        "utf-8"
    ) + b"\n"


def write_policy(tmp_path: Path, payload: bytes) -> str:
    tree = tmp_path / "docs" / "research" / "options"
    tree.mkdir(parents=True, exist_ok=True)
    (tree / "matrix-use.policy.json").write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def make_backend(
    tmp_path,
    *,
    record=None,
    payload=None,
    registry=None,
    dataset_id=DATASET_ID,
    pointer=None,
    digest=None,
    registry_revision=None,
    evidence_root=None,
    clock=None,
    source_family=None,
    resolver=_UNSET,
):
    data = policy_bytes(record) if payload is None else payload
    written = write_policy(tmp_path, data)
    pinned = written if digest is None else digest
    rec = record or policy_record()
    return M.OptionsSourceUseBackend(
        registry=registry if registry is not None else Registry([source_contract(pointer=pointer)]),
        dataset_id=dataset_id,
        expected_evidence_sha256=pinned,
        expected_registry_revision=(
            rec["registry_revision"] if registry_revision is None else registry_revision
        ),
        expected_source_family=(
            rec["source_family"] if source_family is None else source_family
        ),
        use_context_for_request=(
            fresh_resolver() if resolver is _UNSET else resolver
        ),
        evidence_root=tmp_path if evidence_root is None else evidence_root,
        clock=clock or (lambda: NOW),
    )


def refuses(backend, request=_UNSET):
    with pytest.raises(M.SourceUseRefused) as exc:
        backend.decision(make_request() if request is _UNSET else request)
    assert type(exc.value.code) is str and exc.value.code
    return exc.value


def with_action(record, action, **changes):
    block = dict(record["actions"][action])
    block.update(changes)
    actions = dict(record["actions"])
    actions[action] = block
    return dict(record, actions=actions)


def thin_row(right, state):
    """A row like the base one with one right moved to *state* (evidence kept)."""
    contract = source_contract()
    rights = dict(contract.rights, **{right: state})
    return DatasetContract.from_mapping({
        **{f: getattr(contract, f) for f in (
            "dataset_id", "owner", "producer", "storage", "format", "version", "vendor")},
        "layer": "L0", "grain": list(contract.grain),
        "temporal_profile": "SNAPSHOT_SERIES", "status": "PRODUCED",
        "schema": dict(contract.schema), "rights": rights,
    })


# ── positive: exact scoped synthetic join ────────────────────────────────────

def test_allowed_display_exact_join_and_closed_response(tmp_path):
    b = make_backend(tmp_path)
    request = make_request()
    r = b.decision(request)
    assert set(r) == RESPONSE_KEYS
    assert r["status"] == "allowed"
    rec = policy_record()
    assert r["source_family"] == rec["source_family"]
    assert r["policy_id"] == rec["policy_id"]
    assert r["policy_revision"] == rec["policy_revision"]
    assert r["registry_revision"] == rec["registry_revision"]
    assert r["decided_at"] == "2026-10-21T12:00:00Z"
    assert set(r["binding"]) == set(request.as_dict())
    assert r["binding"] == request.as_dict()
    assert type(r["binding"]["byte_length"]) is int


def test_export_allowed_through_its_context_rights_only(tmp_path):
    b = make_backend(tmp_path)
    assert b.decision(make_request(action="export"))["status"] == "allowed"
    # Independence: this export's context names redistribution only, so a row
    # without it refuses; a display whose context names only computation is
    # still served by the same thin row.
    display_only = make_backend(tmp_path / "d1", registry=Registry([thin_row("redistribution", "not_granted")]))
    assert display_only.decision(make_request())["status"] == "allowed"
    assert refuses(display_only, make_request(action="export")).code == "right_not_granted"


def test_no_right_is_inferred_from_the_verb_or_another_flag(tmp_path):
    # Purchase granted AND evidenced, computation unverified: the display
    # context still needs internal_computation, so it refuses (K01.02) —
    # a purchase is not a licence, and no flag substitutes for another.
    contract = source_contract()
    rights = dict(contract.rights, purchase_access="granted", internal_computation="unverified")
    purchased = DatasetContract.from_mapping({
        **{f: getattr(contract, f) for f in (
            "dataset_id", "owner", "producer", "storage", "format", "version", "vendor")},
        "layer": "L0", "grain": list(contract.grain),
        "temporal_profile": "SNAPSHOT_SERIES", "status": "PRODUCED",
        "schema": dict(contract.schema),
        "rights": dict(rights, evidence=dict(rights["evidence"], purchase_access=POINTER)),
    })
    b = make_backend(tmp_path, registry=Registry([purchased]))
    assert refuses(b).code == "right_not_granted"
    # And conversely a context that genuinely requires the purchased right is
    # served: purchase_access is consulted only when the context names it.
    request = make_request()
    context = intended_context(request, required_rights=("purchase_access",))
    rec = with_action(
        policy_record(),
        "display",
        required_rights={"purchase_access": "metered fulfilment of the purchased feed"},
    )
    b2 = make_backend(tmp_path / "p", record=rec, registry=Registry([purchased]),
                      resolver=pinned_resolver(context))
    assert b2.decision(request)["status"] == "allowed"


def test_export_derived_internal_customer_needs_exact_scope(tmp_path):
    # No hardcoded public/raw mapping: an export whose TRUSTED context is a
    # derived rendering to the internal customer is allowed only when the
    # synthetic record, the context and the required rights match exactly.
    request = make_request(action="export")
    context = intended_context(
        request,
        fields=("strike", "bid_raw", "ask_raw"),
        output="derived",
        channel="internal_portal",
        recipients=("internal_customer",),
        required_rights=("internal_computation", "redistribution"),
    )
    rec = with_action(
        policy_record(),
        "export",
        fields=["strike", "bid_raw", "ask_raw"],
        output="derived",
        channel="internal_portal",
        recipients=["internal_customer"],
        customer_scope="named_authenticated_principal",
        principal_id=PRINCIPAL,
        principal_issuer=ISSUER,
        auth_epoch=EPOCH,
        customer_id=PRINCIPAL,
        required_rights={
            "internal_computation": "deriving the rendering served internally",
            "redistribution": "serving that rendering to the internal customer",
        },
    )
    b = make_backend(tmp_path, record=rec, resolver=pinned_resolver(context))
    assert b.decision(request)["status"] == "allowed"
    cases = [
        with_action(rec, "export", output="raw"),
        with_action(rec, "export", channel="server_file_export"),
        with_action(rec, "export", recipients=["authenticated_customer"]),
        with_action(rec, "export", fields=["strike", "ask_raw"]),
        with_action(rec, "export",
                    required_rights={"internal_computation": "computation alone"}),
        with_action(rec, "export",
                    required_rights={
                        "internal_computation": "deriving the rendering served internally",
                        "redistribution": "serving that rendering to the internal customer",
                        "purchase_access": "extra",
                    }),
    ]
    for i, bad_rec in enumerate(cases):
        bi = make_backend(tmp_path / f"m{i}", record=bad_rec, resolver=pinned_resolver(context))
        assert refuses(bi, request).code == "scope_mismatch", i
    # Same context on a row where redistribution is absent: the required right
    # is not granted, so it closes even though everything else matches.
    thin = make_backend(
        tmp_path / "thin", record=rec,
        registry=Registry([thin_row("redistribution", "not_granted")]),
        resolver=pinned_resolver(context),
    )
    assert refuses(thin, request).code == "right_not_granted"


def test_display_needing_redistribution_is_refused_absent_that_right(tmp_path):
    # display is NOT inherently computation: a context that needs
    # redistribution for a display closes when the row lacks it.
    request = make_request()
    context = intended_context(
        request, required_rights=("internal_computation", "redistribution")
    )
    rec = with_action(
        policy_record(),
        "display",
        required_rights={
            "internal_computation": "rendering inside the product",
            "redistribution": "the rendering is forwarded onward",
        },
    )
    b = make_backend(
        tmp_path, record=rec,
        registry=Registry([thin_row("redistribution", "not_granted")]),
        resolver=pinned_resolver(context),
    )
    assert refuses(b, request).code == "right_not_granted"


def test_policy_metadata_is_minted_only_from_verified_bytes(tmp_path):
    b = make_backend(tmp_path)
    request = make_request()
    policy = M.load_options_source_policy(
        request=request,
        registry=b.registry,
        dataset_id=b.dataset_id,
        expected_evidence_sha256=b.expected_evidence_sha256,
        expected_registry_revision=b.expected_registry_revision,
        expected_source_family=b.expected_source_family,
        use_context_for_request=b.use_context_for_request,
        evidence_root=tmp_path,
        clock=lambda: NOW,
    )
    rec = policy_record()
    assert policy.policy_id == rec["policy_id"]
    assert policy.state == "active"
    assert policy.source_family == FAMILY
    assert policy.dataset_version == DATASET_VERSION
    assert policy.known_at == datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert policy.source_sessions is None
    assert policy.evidence_revision == rec["evidence_revision"]
    assert policy.evidence_sha256 == b.expected_evidence_sha256
    assert policy.evidence_pointer.endswith("matrix-use.policy.json")
    assert policy.scope_for("export").fields == ("strike", "ask_raw")
    export_rights = rec["actions"]["export"]["required_rights"]
    assert policy.scope_for("export").required_rights == tuple(sorted(export_rights.items()))
    assert policy.scope_for("save") is None
    # The token is a construction guard, not authentication: it still gates
    # accidental metadata assembly, and it grants no authority by existing.
    with pytest.raises(TypeError):
        M.OptionsSourcePolicy(
            token=None, policy_id="x", policy_revision="x", registry_revision="x",
            source_family="x", dataset_id="x", dataset_version="x", vendor="x",
            state="active", known_at=NOW, effective_from=NOW, effective_until=NOW,
            evidence_revision="x", evidence_sha256="x", evidence_pointer="x",
            source_sessions=None, scopes=(),
        )


def test_frozen_types_authenticate_nothing(tmp_path):
    # A hand-built ServerUseContext is trivially constructible: frozen types
    # and private tokens prove nothing. The adapter accepts one only because
    # its CONTENT is the audited intended use bound to THIS request — never
    # because of its type — and refuses the same construction for any other.
    request = make_request()
    forged = M.ServerUseContext(
        binding=request, dataset_id=DATASET_ID, vendor=VENDOR, source_family=FAMILY,
        fields=("strike", "bid_raw"), output="derived", channel="server_display",
        recipients=("authenticated_customer",), customer_id=request.principal_id,
        required_rights=("internal_computation",),
    )
    b = make_backend(tmp_path, resolver=pinned_resolver(forged))
    assert b.decision(request)["status"] == "allowed"
    assert refuses(b, make_request()).code == "context_binding_mismatch"
    with pytest.raises(AttributeError):
        forged.dataset_id = "mutated"


@pytest.mark.parametrize("action", ["display", "export"])
def test_fresh_decision_and_binding_per_call(tmp_path, action):
    b = make_backend(tmp_path)
    first = b.decision(make_request(action=action))
    second = b.decision(make_request(action=action))
    assert first is not second and first["binding"] is not second["binding"]
    first["binding"]["root"] = "MUTATED"
    first["status"] = "denied"
    assert second["binding"]["root"] == "SYN" and second["status"] == "allowed"


def test_fresh_context_per_call_allows_new_nonce_but_no_replay(tmp_path):
    b = make_backend(tmp_path)
    first = b.decision(make_request())
    second = b.decision(make_request())
    assert second["status"] == "allowed"
    assert second["binding"]["request_id"] != first["binding"]["request_id"]
    first["status"] = "denied"
    first["binding"]["root"] = "MUTATED"
    third = b.decision(make_request())
    assert third["status"] == "allowed" and third["binding"]["root"] == "SYN"


def test_fresh_clock_read_per_call(tmp_path):
    ticks = iter([NOW, NOW + timedelta(seconds=5)])
    b = make_backend(tmp_path, clock=lambda: next(ticks))
    assert b.decision(make_request())["decided_at"] == "2026-10-21T12:00:00Z"
    assert b.decision(make_request())["decided_at"] == "2026-10-21T12:00:05Z"


def test_explicit_false_is_a_genuine_denied_with_real_metadata(tmp_path):
    rec = with_action(policy_record(), "display", allowed=False)
    b = make_backend(tmp_path, record=rec)
    request = make_request()
    r = b.decision(request)
    assert set(r) == RESPONSE_KEYS and r["status"] == "denied"
    assert r["policy_id"] == rec["policy_id"]
    assert r["binding"] == request.as_dict()
    assert r["decided_at"] == "2026-10-21T12:00:00Z"


# ── negatives: all 14 request fields, nonce/snapshot included ────────────────

def test_each_malformed_request_field_is_a_structured_refusal(tmp_path):
    b = make_backend(tmp_path)
    bad_values = [
        ("request_id", "deadbeef"),
        ("request_id", ""),
        ("principal_id", ""),
        ("principal_id", None),
        ("principal_issuer", " leading"),
        ("auth_epoch", 7),
        ("owner", "options_structure.other"),
        ("schema", "options_structure.matrix/v2"),
        ("root", ""),
        ("sha256", "A" * 64),
        ("sha256", "a" * 63),
        ("byte_length", 0),
        ("byte_length", True),
        ("session", 9),
        ("vendor", ""),
        ("underlying_id", None),
        ("selection_sha256", "b" * 65),
        ("action", "save"),
        ("action", "display "),
        ("action", "Display"),
    ]
    for field, bad in bad_values:
        assert refuses(b, make_request(**{field: bad})).code == "request_invalid", field
    assert refuses(b, None).code == "request_invalid"
    assert refuses(b, {"binding": "not a request"}).code == "request_invalid"
    assert refuses(b, make_request(vendor="othervendor")).code == "dataset_vendor_mismatch"


def test_stale_context_binding_is_refused_field_by_field(tmp_path):
    # The trusted resolver captured its context BEFORE these calls, from one
    # intended request. A well-formed request that differs in ANY of the
    # fourteen fields is not that request: every one refuses on the binding.
    request0 = make_request()
    context0 = intended_context(request0)
    b = make_backend(tmp_path, resolver=pinned_resolver(context0))
    assert b.decision(request0)["status"] == "allowed"
    wellformed = {
        "request_id": uuid.uuid4().hex,
        "principal_id": "principal-bob",
        "principal_issuer": "https://other.synthetic.invalid",
        "auth_epoch": "epoch-78",
        "root": "OTHER",
        "sha256": "c" * 64,
        "byte_length": 4097,
        "session": "session-2026-10-22",
        "vendor": "othervendor",
        "underlying_id": "SEC:US-YYYY-SYNTH",
        "selection_sha256": "d" * 64,
    }
    for field, value in wellformed.items():
        mutated = make_request(**{field: value})
        assert refuses(b, mutated).code == "context_binding_mismatch", field
    # The remaining three fields are well-formed vocabulary changes.
    assert refuses(b, make_request(action="export")).code == "context_binding_mismatch"
    assert refuses(b, make_request(owner="options_structure.other")).code == "request_invalid"
    assert refuses(b, make_request(schema="options_structure.matrix/v2")).code == "request_invalid"


# ── negatives: trusted context shape and resolver ───────────────────────────

def test_context_shape_and_resolver_failures(tmp_path):
    missing = make_backend(tmp_path, resolver=None)
    assert refuses(missing).code == "context_unavailable"

    def broken(request):
        raise RuntimeError("resolver down")
    b = make_backend(tmp_path / "r2", resolver=broken)
    assert refuses(b).code == "context_unavailable"

    dicty = make_backend(tmp_path / "r3", resolver=lambda req: {"binding": req, "output": "derived"})
    assert refuses(dicty).code == "context_invalid"
    browsery = make_backend(
        tmp_path / "r4",
        resolver=lambda req: {"binding": req.as_dict(), "dataset_id": DATASET_ID,
                              "output": "derived", "channel": "server_display"},
    )
    assert refuses(browsery).code == "context_invalid"


def test_trusted_context_content_mutations(tmp_path):
    request = make_request()
    base = intended_context(request)
    cases = [
        (dataclasses.replace(base, output="raw"), "scope_mismatch"),
        (dataclasses.replace(base, channel="email_delivery"), "scope_mismatch"),
        (dataclasses.replace(base, recipients=("internal_customer",)), "scope_mismatch"),
        (dataclasses.replace(base, fields=("strike", "secret_col")), "scope_mismatch"),
        (dataclasses.replace(base, fields=("strike", "bid_raw", "ask_raw")), "scope_mismatch"),
        (dataclasses.replace(base, required_rights=("purchase_access",)), "right_not_granted"),
        (dataclasses.replace(base, required_rights=("redistribution",)), "scope_mismatch"),
        (dataclasses.replace(base, customer_id="principal-bob"), "context_invalid"),
        (dataclasses.replace(base, dataset_id="other_dataset"), "context_dataset_mismatch"),
        (dataclasses.replace(base, vendor="othervendor"), "dataset_vendor_mismatch"),
        (dataclasses.replace(base, source_family="other.family"), "policy_family_mismatch"),
        (dataclasses.replace(base, source_family="options_structure.matrix"), "policy_family_mismatch"),
    ]
    for i, (context, code) in enumerate(cases):
        b = make_backend(tmp_path / f"x{i}", resolver=pinned_resolver(context))
        assert refuses(b, request).code == code, (i, code)


def test_context_version_and_row_joins(tmp_path):
    # A context for another dataset version cannot be stretched onto this row:
    # the policy's dataset_version must join the native row version, and the
    # operator's family/dataset pins join the context, row and request.
    request = make_request()
    b = make_backend(tmp_path / "v1", record=policy_record(dataset_version="9"))
    assert refuses(b, request).code == "dataset_version_mismatch"
    assert refuses(make_backend(tmp_path / "v2", record=policy_record(dataset_version="")),
                   request).code == "evidence_invalid"
    both = policy_record(dataset_version="7")
    b2 = make_backend(tmp_path / "v3", record=both,
                      registry=Registry([source_contract(version="7")]))
    assert b2.decision(request)["status"] == "allowed"


# ── negatives: policy scope, identity, currency ─────────────────────────────

def test_scope_field_and_output_and_channel_and_recipient_mutations(tmp_path):
    good = make_backend(tmp_path / "good")
    assert good.decision(make_request())["status"] == "allowed"
    cases = [
        (with_action(policy_record(), "display", fields=["strike", "secret_col"]), "scope_mismatch", "display"),
        (with_action(policy_record(), "display", fields=[]), "evidence_invalid", "display"),
        (with_action(policy_record(), "display", fields=["strike", "strike"]), "evidence_invalid", "display"),
        (with_action(policy_record(), "display", output="raw"), "scope_mismatch", "display"),
        (with_action(policy_record(), "display", channel="email_delivery"), "scope_mismatch", "display"),
        (with_action(policy_record(), "display", recipients=[]), "evidence_invalid", "display"),
        (with_action(policy_record(), "display", recipients=["mailing_list"]), "evidence_invalid", "display"),
        (with_action(policy_record(), "display", recipients=["authenticated_customer", "authenticated_customer"]), "evidence_invalid", "display"),
        (with_action(policy_record(), "display", customer_scope="any_customer"), "evidence_invalid", "display"),
        (with_action(policy_record(), "display", allowed="true"), "evidence_invalid", "display"),
        (with_action(policy_record(), "export", output="derived"), "scope_mismatch", "export"),
        (with_action(policy_record(), "export", channel="server_display"), "scope_mismatch", "export"),
        (with_action(policy_record(), "export", fields=["strike", "undeclared_col"]), "scope_mismatch", "export"),
    ]
    for i, (rec, code, action) in enumerate(cases):
        b = make_backend(tmp_path / f"c{i}", record=rec)
        assert refuses(b, make_request(action=action)).code == code, (action, code)


def test_scope_identity_and_required_rights_mutations(tmp_path):
    cases = [
        (with_action(policy_record(), "display", principal_id="principal-bob"), "scope_mismatch", "display"),
        (with_action(policy_record(), "display",
                     principal_issuer="https://other.synthetic.invalid"), "scope_mismatch", "display"),
        (with_action(policy_record(), "display", auth_epoch="epoch-78"), "scope_mismatch", "display"),
        (with_action(policy_record(), "display", customer_id="principal-bob"), "scope_mismatch", "display"),
        (with_action(policy_record(), "display", customer_scope="any_customer"), "evidence_invalid", "display"),
        (with_action(policy_record(), "display", principal_id=""), "evidence_invalid", "display"),
        (with_action(policy_record(), "display", required_rights={}), "evidence_invalid", "display"),
        (with_action(policy_record(), "display",
                     required_rights=["internal_computation"]), "evidence_invalid", "display"),
        (with_action(policy_record(), "display",
                     required_rights={"internal_computation": ""}), "evidence_invalid", "display"),
        (with_action(policy_record(), "display",
                     required_rights={"internal_computation": 7}), "evidence_invalid", "display"),
        (with_action(policy_record(), "display",
                     required_rights={"not_a_native_right": "why not"}), "scope_mismatch", "display"),
        (with_action(policy_record(), "export",
                     required_rights={"internal_computation": "computation",
                                      "redistribution": "sharing"}), "scope_mismatch", "export"),
    ]
    for i, (rec, code, action) in enumerate(cases):
        b = make_backend(tmp_path / f"s{i}", record=rec)
        assert refuses(b, make_request(action=action)).code == code, (action, code)


def test_policy_identity_and_currency_mutations(tmp_path):
    cases = [
        (policy_record(source_family="other.family"), "policy_family_mismatch"),
        (policy_record(source_family="options_structure.matrix"), "policy_family_mismatch"),
        (policy_record(dataset_id="other_dataset"), "policy_dataset_mismatch"),
        (policy_record(vendor="othervendor"), "policy_vendor_mismatch"),
        (policy_record(dataset_version="9"), "dataset_version_mismatch"),
        (policy_record(registry_revision="reg-OTHER"), "registry_revision_mismatch"),
        (policy_record(state="revoked"), "policy_revoked"),
        (policy_record(state="compromised"), "evidence_invalid"),
        (policy_record(known_at="2026-10-22T00:00:00Z"), "policy_known_at_future"),
        (policy_record(known_at="2026-10-21T12:00:01Z"), "policy_known_at_future"),
        (policy_record(known_at="2026-10-20"), "policy_known_at_invalid"),
        (policy_record(effective_from="2026-11-02T00:00:00Z",
                       effective_until="2026-12-01T00:00:00Z"), "policy_not_current"),
        (policy_record(effective_until="2026-10-20T00:00:00Z"), "policy_not_current"),
        (policy_record(effective_until="2026-10-21T12:00:00Z"), "policy_not_current"),
        (policy_record(effective_until="2026-09-01T00:00:00Z"), "policy_window_invalid"),
        (policy_record(effective_from="2026-10-01"), "policy_window_invalid"),
        (policy_record(effective_until=None), "policy_window_invalid"),
        (policy_record(source_sessions=[]), "evidence_invalid"),
        (policy_record(source_sessions=["s1", "s1"]), "evidence_invalid"),
        (policy_record(source_sessions=7), "evidence_invalid"),
        (policy_record(source_sessions=["session-2026-10-22"]), "source_session_excluded"),
        (policy_record(policy_id=""), "evidence_invalid"),
        (policy_record(policy_revision=None), "evidence_invalid"),
        (policy_record(evidence_revision=""), "evidence_invalid"),
        (policy_record(actions={}), "evidence_invalid"),
        (policy_record(actions={"save": policy_record()["actions"]["display"]}), "evidence_invalid"),
        (dict(policy_record(), surprise="default_allow"), "evidence_invalid"),
    ]
    base_revision = policy_record()["registry_revision"]
    for i, (rec, code) in enumerate(cases):
        # The operator pin stays at the BASE revision, so a policy claiming a
        # different registry revision cannot self-certify.
        b = make_backend(
            tmp_path / f"p{i}", record=rec, registry_revision=base_revision
        )
        assert refuses(b).code == code, rec
    removed = policy_record()
    del removed["policy_id"]
    assert refuses(make_backend(tmp_path / "pdel", record=removed)).code == "evidence_invalid"
    removed_known = policy_record()
    del removed_known["known_at"]
    assert refuses(make_backend(tmp_path / "pkn", record=removed_known)).code == "evidence_invalid"
    export_missing = policy_record()
    del export_missing["actions"]["export"]
    b = make_backend(tmp_path / "pact", record=export_missing)
    assert b.decision(make_request())["status"] == "allowed"
    assert refuses(b, make_request(action="export")).code == "action_not_licensed"


def test_known_at_and_session_coverage_positives(tmp_path):
    # known_at exactly at the fresh decision clock is current; an explicit
    # session list covers exactly its own historical sessions.
    rec = policy_record(
        known_at="2026-10-21T12:00:00Z",
        source_sessions=["session-2026-10-20", "session-2026-10-21"],
    )
    b = make_backend(tmp_path, record=rec)
    assert b.decision(make_request())["status"] == "allowed"
    assert refuses(b, make_request(session="session-2026-10-22")).code == "source_session_excluded"
    assert refuses(b, make_request(session=None)).code == "source_session_excluded"
    # A null session list covers any session, including the absence of one.
    b2 = make_backend(tmp_path / "n", record=policy_record())
    assert b2.decision(make_request(session=None))["status"] == "allowed"
    # An old snapshot whose known_at is one second AFTER the fresh clock fails.
    b3 = make_backend(tmp_path / "f", record=policy_record(known_at="2026-10-21T12:00:01Z"))
    assert refuses(b3).code == "policy_known_at_future"


# ── negatives: registry rows ────────────────────────────────────────────────

def test_dataset_row_mutations(tmp_path):
    base = source_contract()
    def row(**changes):
        return source_contract(**changes)
    cases = [
        (Registry([]), None, "dataset_missing"),
        (Registry([row(), row(version="2")]), None, "dataset_ambiguous"),
        (Registry([row(status="PROPOSED")]), None, "source_not_produced"),
        (Registry([row(status="RETIRED")]), None, "source_not_produced"),
        (Registry([row(layer="L3")]), None, "source_layer_unsupported"),
        (Registry([row(vendor="othervendor")]), None, "dataset_vendor_mismatch"),
        (Registry([row(owner="")]), None, "registry_contract_invalid"),
        (Registry([row(rights={"internal_computation": "granted"})]), None,
         "registry_contract_invalid"),
    ]
    for i, (registry, _x, code) in enumerate(cases):
        b = make_backend(tmp_path / f"r{i}", registry=registry)
        assert refuses(b).code == code, code


# ── negatives: evidence pointers, capture, bytes ────────────────────────────

def test_evidence_pointer_forms(tmp_path):
    # Pointer forms the registry itself refuses (R00.02) close at the row
    # validation; forms that are LAWFUL syntax but unusable here close in the
    # adapter.  Both fail closed before any allow.
    cases = [
        (None, "registry_contract_invalid"),                      # no pointer at all
        ("data/captured/matrix-use.policy.json", "registry_contract_invalid"),
        ("https://cdn.synthetic.invalid/policy.json", "registry_contract_invalid"),
        ("docs/research/options/", "registry_contract_invalid"),
        ("Unverified per vendor contract", "registry_contract_invalid"),
        ("DEC:2026-10-OPTIONS-MATRIX", "evidence_unresolvable"),
        ("DSC:2026-10-OPTIONS-MATRIX", "evidence_unresolvable"),
        ("docs/research/options/missing.policy.json", "evidence_unreadable"),
        ("docs/research/options/../../secrets/matrix-use.policy.json",
         "evidence_path_forbidden"),
        ("docs/research/./options/matrix-use.policy.json", "evidence_path_forbidden"),
    ]
    for i, (pointer, code) in enumerate(cases):
        row = None
        if pointer is None:
            contract = source_contract()
            row = DatasetContract.from_mapping({
                **{f: getattr(contract, f) for f in (
                    "dataset_id", "owner", "producer", "storage", "format",
                    "version", "vendor")},
                "layer": "L0", "grain": list(contract.grain),
                "temporal_profile": "SNAPSHOT_SERIES", "status": "PRODUCED",
                "schema": dict(contract.schema),
                "rights": {
                    "purchase_access": "unverified",
                    "internal_computation": "granted",
                    "redistribution": "granted",
                },
            })
        b = make_backend(
            tmp_path / f"e{i}",
            pointer=pointer,
            registry=None if row is None else Registry([row]),
        )
        assert refuses(b).code == code, pointer


def test_rights_pointing_at_different_evidence_files_refuse(tmp_path):
    # Each required right must point at ONE shared evidence file: two grants
    # evidenced by different files are not one verification.
    contract = source_contract()
    rights = dict(
        contract.rights,
        evidence=dict(contract.rights["evidence"], redistribution="docs/other/policy.json"),
    )
    row = DatasetContract.from_mapping({
        **{f: getattr(contract, f) for f in (
            "dataset_id", "owner", "producer", "storage", "format", "version", "vendor")},
        "layer": "L0", "grain": list(contract.grain),
        "temporal_profile": "SNAPSHOT_SERIES", "status": "PRODUCED",
        "schema": dict(contract.schema), "rights": rights,
    })
    request = make_request()
    context = intended_context(
        request, required_rights=("internal_computation", "redistribution")
    )
    rec = with_action(
        policy_record(),
        "display",
        required_rights={
            "internal_computation": "rendering inside the product",
            "redistribution": "the rendering is forwarded onward",
        },
    )
    b = make_backend(tmp_path, record=rec, registry=Registry([row]),
                     resolver=pinned_resolver(context))
    assert refuses(b, request).code == "evidence_pointer_mismatch"


def test_symlink_escape_is_refused_even_with_matching_digest(tmp_path):
    payload = policy_bytes()
    outside = tmp_path / "outside.policy.json"
    outside.write_bytes(payload)
    tree = tmp_path / "docs" / "research" / "options"
    tree.mkdir(parents=True, exist_ok=True)
    link = tree / "linked.policy.json"
    link.symlink_to(outside)
    b = make_backend(
        tmp_path,
        pointer="docs/research/options/linked.policy.json",
        digest=hashlib.sha256(payload).hexdigest(),
    )
    assert refuses(b).code == "evidence_path_forbidden"


def test_symlinked_intermediate_directory_is_refused(tmp_path):
    payload = policy_bytes()
    secret = tmp_path / "secret"
    secret.mkdir()
    (secret / "matrix-use.policy.json").write_bytes(payload)
    tree = tmp_path / "docs" / "research" / "options"
    tree.mkdir(parents=True, exist_ok=True)
    (tree / "sub").symlink_to(secret)
    b = make_backend(
        tmp_path,
        pointer="docs/research/options/sub/matrix-use.policy.json",
        digest=hashlib.sha256(payload).hexdigest(),
    )
    assert refuses(b).code == "evidence_path_forbidden"


def test_symlink_swapped_after_open_is_refused(tmp_path):
    # The dirfd walk opens every component O_NOFOLLOW from the root: swapping
    # a real directory for a symlink after the tree is built cannot redirect
    # an open that never follows links in the first place.
    payload = policy_bytes()
    tree = tmp_path / "docs" / "research"
    tree.mkdir(parents=True, exist_ok=True)
    real = tmp_path / "real_options"
    real.mkdir()
    (real / "matrix-use.policy.json").write_bytes(payload)
    link = tree / "options"
    link.symlink_to(real)
    b = make_backend(
        tmp_path,
        pointer="docs/research/options/matrix-use.policy.json",
        digest=hashlib.sha256(payload).hexdigest(),
    )
    assert refuses(b).code == "evidence_path_forbidden"


def test_digest_pin_mutations(tmp_path):
    payload = policy_bytes()
    flipped = payload.replace(b'"active"', b'"REVOKED"')
    stale = make_backend(tmp_path / "s", payload=payload, digest=hashlib.sha256(flipped).hexdigest())
    assert refuses(stale).code == "evidence_digest_mismatch"
    reboxed = policy_record(state="revoked")
    new_bytes = policy_bytes(reboxed)
    pinned_old = make_backend(
        tmp_path / "n", payload=new_bytes, digest=hashlib.sha256(payload).hexdigest()
    )
    # The operator pin holds even when the file itself claims a new state.
    assert refuses(pinned_old).code == "evidence_digest_mismatch"


def test_evidence_bytes_shapes(tmp_path):
    cases = [
        (b"not json at all", "evidence_invalid"),
        (b"[]", "evidence_invalid"),
        (policy_bytes().replace(b'"active"', b"NaN"), "evidence_invalid"),
        (b'{"policy_id": "a", "policy_id": "b"}', "evidence_invalid"),
        (policy_bytes() + b" " * (256 * 1024), "evidence_unbounded"),
    ]
    for i, (payload, code) in enumerate(cases):
        b = make_backend(
            tmp_path / f"j{i}", payload=payload,
            digest=hashlib.sha256(payload).hexdigest(),
        )
        assert refuses(b).code == code, code


def test_missing_evidence_file_and_root(tmp_path):
    b = make_backend(tmp_path, evidence_root=tmp_path / "nowhere")
    assert refuses(b).code == "evidence_root_invalid"
    empty = tmp_path / "emptytree"
    empty.mkdir()
    b2 = make_backend(tmp_path / "t2", evidence_root=empty)
    assert refuses(b2).code == "evidence_unreadable"


# ── negatives: clock and trusted backend configuration ──────────────────────

def test_clock_refusals(tmp_path):
    for clock in (
        lambda: NOW.replace(tzinfo=None),
        lambda: "2026-10-21T12:00:00Z",
        lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_CLOCK_SECRET")),
    ):
        b = make_backend(tmp_path, clock=clock)
        assert refuses(b).code == "clock_invalid"


def test_backend_configuration_validation(tmp_path):
    resolver = fresh_resolver()
    with pytest.raises(ValueError):
        M.OptionsSourceUseBackend(
            registry=Registry([]), dataset_id=DATASET_ID,
            expected_evidence_sha256="nothex", expected_registry_revision="r",
            expected_source_family=FAMILY,
        )
    with pytest.raises(ValueError):
        M.OptionsSourceUseBackend(
            registry=object(), dataset_id=DATASET_ID,
            expected_evidence_sha256="a" * 64, expected_registry_revision="r",
            expected_source_family=FAMILY,
        )
    with pytest.raises(ValueError):
        M.OptionsSourceUseBackend(
            registry=Registry([]), dataset_id="",
            expected_evidence_sha256="a" * 64, expected_registry_revision="r",
            expected_source_family=FAMILY,
        )
    with pytest.raises(ValueError):
        M.OptionsSourceUseBackend(
            registry=Registry([]), dataset_id=DATASET_ID,
            expected_evidence_sha256="a" * 64, expected_registry_revision="r",
            expected_source_family="",
        )
    with pytest.raises(ValueError):
        M.OptionsSourceUseBackend(
            registry=Registry([]), dataset_id=DATASET_ID,
            expected_evidence_sha256="a" * 64, expected_registry_revision="r",
            expected_source_family=FAMILY, use_context_for_request="not callable",
        )
    with pytest.raises(ValueError):
        M.OptionsSourceUseBackend(
            registry=Registry([]), dataset_id=DATASET_ID,
            expected_evidence_sha256="a" * 64, expected_registry_revision="r",
            expected_source_family=FAMILY, use_context_for_request=resolver,
            clock="not callable",
        )


def test_trusted_scalars_refuse_closed(tmp_path):
    b = make_backend(tmp_path)
    with pytest.raises(ValueError):
        M.OptionsSourceUseBackend(
            registry=b.registry,
            dataset_id=DATASET_ID,
            expected_evidence_sha256="z" * 64,
            expected_registry_revision=b.expected_registry_revision,
            expected_source_family=b.expected_source_family,
            use_context_for_request=b.use_context_for_request,
            evidence_root=tmp_path,
            clock=lambda: NOW,
        )
    # The function form carries the same gates for a directly misconfigured call.
    with pytest.raises(M.SourceUseRefused) as exc:
        M.resolve_options_source_use_decision(
            make_request(),
            registry=b.registry,
            dataset_id=DATASET_ID,
            expected_evidence_sha256="z" * 64,
            expected_registry_revision=b.expected_registry_revision,
            expected_source_family=b.expected_source_family,
            use_context_for_request=b.use_context_for_request,
            evidence_root=tmp_path,
            clock=lambda: NOW,
        )
    assert exc.value.code == "trust_invalid"
    with pytest.raises(M.SourceUseRefused) as exc:
        M.resolve_options_source_use_decision(
            make_request(),
            registry=b.registry,
            dataset_id=DATASET_ID,
            expected_evidence_sha256=b.expected_evidence_sha256,
            expected_registry_revision=b.expected_registry_revision,
            expected_source_family="",
            use_context_for_request=b.use_context_for_request,
            evidence_root=tmp_path,
            clock=lambda: NOW,
        )
    assert exc.value.code == "trust_invalid"
    # A missing resolver is a decision-time refusal, never a permissive default.
    with pytest.raises(M.SourceUseRefused) as exc:
        M.resolve_options_source_use_decision(
            make_request(),
            registry=b.registry,
            dataset_id=DATASET_ID,
            expected_evidence_sha256=b.expected_evidence_sha256,
            expected_registry_revision=b.expected_registry_revision,
            expected_source_family=b.expected_source_family,
            use_context_for_request=None,
            evidence_root=tmp_path,
            clock=lambda: NOW,
        )
    assert exc.value.code == "context_unavailable"


def test_no_secrets_in_refusal_details(tmp_path):
    def bad_clock():
        raise RuntimeError("PRIVATE_EVIDENCE_SECRET")
    b = make_backend(tmp_path, clock=bad_clock)
    assert "PRIVATE_EVIDENCE_SECRET" not in str(refuses(b))

    def bad_resolver(request):
        raise RuntimeError("PRIVATE_RESOLVER_SECRET")
    b2 = make_backend(tmp_path / "r", resolver=bad_resolver)
    assert "PRIVATE_RESOLVER_SECRET" not in str(refuses(b2))


def test_no_decision_state_is_kept_on_the_module(tmp_path):
    b = make_backend(tmp_path)
    first = b.decision(make_request())
    # Decisions leave no residue: the module holds no dict/list/set state at
    # all beyond its own import-time vocabulary constants.
    containers = {
        name: value for name, value in vars(M).items()
        if not name.startswith("__") and isinstance(value, (dict, list, set))
    }
    assert containers == {}
    assert first["status"] == "allowed"


# ── composed resolver (repo fixtures; skipped standalone) ────────────────────

def composed_record(vendor, **changes):
    """Synthetic policy whose scope names the composed fixture's principal."""
    record = policy_record(
        dataset_id=DATASET_ID,
        vendor=vendor,
        registry_revision="reg-composed",
        actions={
            "display": {
                "allowed": True,
                "fields": ["strike", "bid_raw"],
                "output": "derived",
                "channel": "server_display",
                "recipients": ["authenticated_customer"],
                "customer_scope": "named_authenticated_principal",
                "principal_id": "fixture-alice",
                "principal_issuer": "https://fixture.invalid",
                "auth_epoch": "fixture.epoch1",
                "customer_id": "fixture-alice",
                "required_rights": {
                    "internal_computation": "rendering the composed fixture selection in-process",
                },
            },
        },
    )
    record.update(changes)
    return record


def _composed_backend(tmp_path, vendor, registry, record, clock):
    data = policy_bytes(record)
    digest = write_policy(tmp_path, data)
    return M.OptionsSourceUseBackend(
        registry=registry,
        dataset_id=DATASET_ID,
        expected_evidence_sha256=digest,
        expected_registry_revision=record["registry_revision"],
        expected_source_family=record["source_family"],
        use_context_for_request=fresh_resolver(),
        evidence_root=tmp_path,
        clock=clock,
    )


def _composed_row(vendor, pointer=None):
    return source_contract(pointer=pointer, vendor=vendor, dataset_id=DATASET_ID)


def test_composed_resolver_allows_with_real_policy(tmp_path):
    F = pytest.importorskip("tests.test_options_selection_composition")
    f = F.inputs.__wrapped__()
    raw = F.encoded(f["doc"])
    kw = dict(f["kwargs"])
    vendor = kw["vendor"]
    kw.pop("decision_at")
    record = composed_record(vendor)
    backend = _composed_backend(
        tmp_path, vendor, Registry([_composed_row(vendor)]), record, clock=lambda: F.NOW)
    calls = []

    def entitlement(req):
        calls.append(("entitlement", req))
        return True

    def rights(req):
        calls.append(("rights", req))
        return backend.decision(req)

    kw.update(
        principal_id="fixture-alice", principal_issuer="https://fixture.invalid",
        auth_epoch="fixture.epoch1", action="display",
        fresh_entitlement=entitlement, source_use_decision=rights,
        clock=lambda: F.NOW,
    )
    from engine.intelligence_workspace.options_use import resolve_authorized_option_selection
    result = resolve_authorized_option_selection(
        F.R.reference_for_bytes("SPY", raw), F.capture(raw), F.encoded(F.selection()),
        **kw,
    )
    assert result.policy_id == record["policy_id"]
    assert result.policy_revision == record["policy_revision"]
    assert result.registry_revision == record["registry_revision"]
    assert [name for name, _ in calls] == ["entitlement", "rights"]
    assert calls[0][1] is calls[1][1] is result.request


def test_composed_resolver_missing_production_row_is_rights_unavailable(tmp_path):
    F = pytest.importorskip("tests.test_options_selection_composition")
    f = F.inputs.__wrapped__()
    raw = F.encoded(f["doc"])
    kw = dict(f["kwargs"])
    vendor = kw["vendor"]
    kw.pop("decision_at")
    record = composed_record(vendor)
    backend = _composed_backend(
        tmp_path, vendor, Registry([]), record, clock=lambda: F.NOW)
    calls = []

    def entitlement(req):
        calls.append(("entitlement", req))
        return True

    kw.update(
        principal_id="fixture-alice", principal_issuer="https://fixture.invalid",
        auth_epoch="fixture.epoch1", action="display",
        fresh_entitlement=entitlement, source_use_decision=backend.decision,
        clock=lambda: F.NOW,
    )
    from engine.intelligence_workspace.options_use import (
        OptionUseRefused as Refused,
        resolve_authorized_option_selection,
    )
    with pytest.raises(Refused) as exc:
        resolve_authorized_option_selection(
            F.R.reference_for_bytes("SPY", raw), F.capture(raw), F.encoded(F.selection()),
            **kw,
        )
    assert exc.value.code == "rights_unavailable"
    # Auth/entitlement ran and succeeded; the missing source row is what closed it.
    assert [name for name, _ in calls] == ["entitlement"]


def test_composed_resolver_denied_policy_maps_to_source_denied(tmp_path):
    F = pytest.importorskip("tests.test_options_selection_composition")
    f = F.inputs.__wrapped__()
    raw = F.encoded(f["doc"])
    kw = dict(f["kwargs"])
    vendor = kw["vendor"]
    kw.pop("decision_at")
    record = with_action(composed_record(vendor), "display", allowed=False)
    backend = _composed_backend(
        tmp_path, vendor, Registry([_composed_row(vendor)]), record, clock=lambda: F.NOW)
    kw.update(
        principal_id="fixture-alice", principal_issuer="https://fixture.invalid",
        auth_epoch="fixture.epoch1", action="display",
        fresh_entitlement=lambda req: True, source_use_decision=backend.decision,
        clock=lambda: F.NOW,
    )
    from engine.intelligence_workspace.options_use import (
        OptionUseRefused as Refused,
        resolve_authorized_option_selection,
    )
    with pytest.raises(Refused) as exc:
        resolve_authorized_option_selection(
            F.R.reference_for_bytes("SPY", raw), F.capture(raw), F.encoded(F.selection()),
            **kw,
        )
    assert exc.value.code == "source_denied"


def test_source_family_is_opaque_but_must_join_trusted_inputs(tmp_path):
    request = make_request()
    record = policy_record(source_family=M.MATRIX_OWNER)
    backend = make_backend(tmp_path, record=record,
        source_family=M.MATRIX_OWNER,
        resolver=pinned_resolver(intended_context(request, source_family=M.MATRIX_OWNER)))
    assert backend.decision(request)["source_family"] == M.MATRIX_OWNER
