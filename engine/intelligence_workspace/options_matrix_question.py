"""Source-only Matrix question preparation and final attempted-disclosure check.

Uses the incumbent retained capture, Options auth/identity and source-use backend.
No route, reader, policy store, credential, model call or installation is created.
The gateway supplies its actual destination and a strict payload attachment reader.
Those callbacks must be audited server integrations, never browser/policy inputs.
A returned value is not a transferable capability or an exactly-once send receipt.
"""
from __future__ import annotations

import hashlib
import importlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock

from app import options_auth
from app.options_matrix_http import MatrixHTTPInputs, MatrixHTTPRuntime
from engine.intelligence_workspace.options_identity import resolve_option_matrix_selection
from engine.intelligence_workspace.options_matrix_delivery import (
    MatrixDisplaySource, bind_matrix_contracts, capture_matrix_provenance,
)
from engine.intelligence_workspace.options_source_use import (
    MATRIX_OWNER, MATRIX_SCHEMA, OptionsSourceUseBackend, ProcessorDestination,
    ServerUseContext, SourceUseRefused, validate_processor,
)
from engine.options_matrix_retention import verify_snapshot
from lib.dataos.registry import RIGHTS_KEYS

_CHANNELS = ("/api/brain/chat", "/api/brain/stream")
_MAX_PAYLOAD = 2 * 1024 * 1024


def _refuse():
    raise SourceUseRefused("question_dispatch_unavailable")


@dataclass(frozen=True)
class QuestionPolicyBinding:
    """Trusted enrollment pins; construction does not grant any source rights."""
    evidence_sha256: str
    registry_revision: str
    required_rights_rationale: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class VerifiedQuestionDispatch:
    """Exact bytes checked for ONE synchronous gateway attempt, never persist.

    Gateway must send these bytes to this destination immediately and must not
    reuse the value for a fallback. No external send or success is attested.
    """
    payload: bytes
    payload_sha256: str
    processor: ProcessorDestination
    channel: str


class PreparedMatrixQuestion:
    """Ephemeral preparation; only authorize_dispatch performs the final check."""
    def __init__(self, *, context, check, decision, request, destination, channel,
                 token, lock):
        self.prompt_block = context.prompt_block
        self.receipt = context.receipt
        self._source_block = context.prompt_block.encode("utf-8")
        self._check = check
        self._decision = decision
        self._request = request
        self._destination = destination
        self._channel = channel
        self._token = token
        self._lock = lock
        self._used = False

    def authorize_dispatch(self, payload, *, processor, channel, extract_source_block):
        """Consume once; verify exact actual payload attachment before disclosure.

        extract_source_block is the gateway's trusted strict parser for ITS actual
        outbound payload, returning the single attachment bytes or refusing. It
        must reject absent, duplicate or ambiguous attachments. This module does
        not guess a vendor wire schema or accept a browser-supplied extractor.
        Changing destinations requires a new preparation and policy evaluation.
        """
        with self._lock:
            if self._used:
                _refuse()
            self._used = True  # failure is consumed too; no ambiguous local replay
            token, self._token = self._token, None
        self._check()
        if (type(payload) is not bytes or not 0 < len(payload) <= _MAX_PAYLOAD
                or type(processor) is not ProcessorDestination
                or processor != self._destination or channel != self._channel
                or not callable(extract_source_block)):
            _refuse()
        try:
            block = extract_source_block(payload)
        except Exception:
            _refuse()
        if type(block) is not bytes or block != self._source_block:
            _refuse()
        # Product/session and the actual pinned policy are re-read at disclosure,
        # not borrowed from preparation. The earlier immutable prompt stays dated.
        if options_auth.fresh_options_entitlement(self._request, access_token=token) is not True:
            _refuse()
        decision = self._decision(self._request)
        if decision.get("status") != "allowed":
            _refuse()
        self._check()  # late Auth/evidence/parser results cannot release bytes
        return VerifiedQuestionDispatch(payload, hashlib.sha256(payload).hexdigest(),
                                        processor, channel)


def prepare_matrix_question(reference, *, access_token, expected_user_id,
                            runtime, processor, channel, policy,
                            clock=None, question_adapter=None):
    """Prepare with existing capture and Lab adapter; no model disclosure yet.

    The Lab dependency is imported lazily because its independent source carrier
    is not this module's installation. Missing dependency/config refuses, never
    falls back to company-source, display-only policy or a ticker-level lookup.
    """
    validate_processor(processor)
    if (channel not in _CHANNELS or type(runtime) is not MatrixHTTPRuntime
            or not callable(runtime.capture) or type(policy) is not QuestionPolicyBinding):
        _refuse()
    rationale = policy.required_rights_rationale
    if (type(rationale) is not tuple or not rationale
            or any(type(x) is not tuple or len(x) != 2 or x[0] not in RIGHTS_KEYS
                   or type(x[1]) is not str or not x[1].strip() for x in rationale)
            or len({x[0] for x in rationale}) != len(rationale)):
        _refuse()
    now = clock if clock is not None else lambda: datetime.now(timezone.utc)
    start = now()
    if type(start) is not datetime or start.tzinfo is None or start.utcoffset() is None:
        _refuse()
    last = start
    deadline = start + timedelta(seconds=10)

    def check():
        nonlocal last
        at = now()
        if (type(at) is not datetime or at.tzinfo is None or at.utcoffset() is None
                or at < last or at >= deadline):
            _refuse()
        last = at
        return at

    # Authenticate before any retained source read; no principal supplied by UI.
    principal = options_auth.resolve_options_principal(access_token)
    if (type(expected_user_id) is not str or principal.principal_id != expected_user_id):
        _refuse()
    check()
    adapter = question_adapter
    if adapter is None:
        try:
            adapter = importlib.import_module("engine.neuralweb.options_selection_context")
        except ImportError:
            _refuse()
    parsed = adapter.parse_options_question(reference)
    captured = runtime.capture(parsed.ref)
    check()
    if type(captured) is not MatrixHTTPInputs or type(captured.source) is not MatrixDisplaySource:
        _refuse()
    source = captured.source
    provenance = capture_matrix_provenance(parsed.ref, captured.matrix.body)
    binding = bind_matrix_contracts(provenance, source.binding, source.inputs, source.registry)
    payload = verify_snapshot(parsed.ref, captured.matrix.body)
    identity = resolve_option_matrix_selection(
        parsed.ref, captured.matrix, parsed.selection, vendor=binding.vendor,
        decision_at=check(), aliases=captured.aliases,
        security_master=captured.security_master, root_evidence=captured.root_evidence)
    request_seen = []

    def context_for(request):
        check()
        expected = dict(
            principal_id=principal.principal_id, principal_issuer=principal.principal_issuer,
            auth_epoch=principal.auth_epoch, owner=MATRIX_OWNER, schema=MATRIX_SCHEMA,
            root=parsed.ref.root, sha256=parsed.ref.sha256, byte_length=parsed.ref.byte_length,
            session=parsed.ref.session, vendor=binding.vendor,
            underlying_id=identity.matrix.underlying.binding.security_id,
            selection_sha256=hashlib.sha256(parsed.selection).hexdigest(), action="export")
        for name, value in expected.items():
            actual = getattr(request, name, None)
            if type(actual) is not type(value) or actual != value:
                _refuse()
        return ServerUseContext(
            binding=request, dataset_id=binding.dataset_id, vendor=binding.vendor,
            source_family=binding.source_family, fields=tuple(sorted(payload)),
            output="derived", channel=channel,
            recipients=("authenticated_customer", "external_processor"),
            customer_id=principal.principal_id,
            required_rights=tuple(x[0] for x in rationale), processor=processor)

    backend = OptionsSourceUseBackend(
        registry=source.registry, dataset_id=binding.dataset_id,
        expected_evidence_sha256=policy.evidence_sha256,
        expected_registry_revision=policy.registry_revision,
        expected_source_family=binding.source_family,
        use_context_for_request=context_for, evidence_root=source.evidence_root, clock=check)

    def decision(request):
        result = backend.decision(request)
        check()
        request_seen.append(request)
        return result

    context = adapter.resolve_options_question(
        reference, access_token=access_token, expected_user_id=expected_user_id,
        captured=adapter.OptionsQuestionCapture(captured.matrix, captured.aliases,
                    captured.security_master, captured.root_evidence),
        vendor=binding.vendor, source_use_decision=decision, clock=check)
    check()
    if (len(request_seen) != 1 or type(context.prompt_block) is not str
            or not 0 < len(context.prompt_block.encode("utf-8")) <= 6144):
        _refuse()
    return PreparedMatrixQuestion(context=context, check=check, decision=backend.decision,
        request=request_seen[0], destination=processor, channel=channel,
        token=access_token, lock=Lock())
