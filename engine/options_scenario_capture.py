"""Deliberate exact-source capture at the existing Options Hub producer boundary.

Private source composition only. Producer files, a descriptor, and a paid feature
are not authority. Fresh Save and retention decisions plus a qualified private
server destination are required. No production bindings are installed here.
This retains exact sources and emits reference metadata; native TS basis/math
verification and the canonical Investigation CAS save remain separate duties.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable

from engine import options_hub_retention as retention
from engine.intelligence_workspace import scenario_source_resolution as source

SAVE_ACTION = "save_scenario_sources"
SAVE_PURPOSE = "investigation_scenario_capture/v1"
# Provenance label echoed into action bindings/receipts; never opened or imported.
PRODUCER = "scripts/build_options_hub_nightly.py"  # ci-trigger-closure: data
# A whole artifact is authorized, including fields outside ScenarioBasis. These
# are source classification, not a rights grant or a live destination measurement.
SOURCE_SCOPE = "options_hub/nightly_gex_and_optional_moves_whole_artifacts"


class ProducerCaptureRefused(ValueError):
    def __init__(self, code: str, *, status: str = "unavailable", effect_stage: str = "before_retention"):
        self.code, self.status, self.effect_stage = code, status, effect_stage
        super().__init__(code)


@dataclass(frozen=True)
class RetainedProducerCapture:
    """Transient metadata, never a persisted scenario or calculation receipt."""
    descriptor: source.ScenarioSourceDescriptor
    operation_id: str
    policy_id: str
    policy_revision: str
    registry_revision: str

    def boundary(self) -> dict:
        d = self.descriptor
        ref = lambda value: None if value is None else {
            "sha256": value.sha256, "byte_length": value.byte_length,
            "kind": value.kind, "session": value.session, "version_ref": value.version_ref}
        return {"status": "sources_retained", "producer": PRODUCER,
                "investigation_id": d.investigation_id,
                "revision": d.investigation_revision, "operation_id": self.operation_id,
                "model_version": d.model_version, "root": d.root,
                "session": d.gex.session, "source_as_of": d.source_as_of,
                "evaluated_at": d.evaluated_at, "lens": dict(d.lens),
                "selection_key": d.selection_key, "gex": ref(d.gex), "moves": ref(d.moves),
                "declared_basis_sha256": d.basis_sha256,
                "basis_calculation_verified": False, "canonical_save_performed": False}


def _now(clock) -> datetime:
    try:
        value = clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError()
        return value
    except Exception:
        raise ProducerCaptureRefused("clock_unavailable") from None


def _actor(current_viewer, expected) -> None:
    try:
        actual = current_viewer()
    except Exception:
        raise ProducerCaptureRefused("current_actor_unavailable") from None
    if not isinstance(actual, source.ViewerIdentity):
        raise ProducerCaptureRefused("current_actor_unavailable")
    if actual != expected:
        raise ProducerCaptureRefused("current_actor_changed", status="denied")


def _save_decision(callback, binding: dict, clock) -> dict:
    expected = deepcopy(binding)
    start = _now(clock)
    try:
        decision = callback(deepcopy(binding))
    except Exception:
        raise ProducerCaptureRefused("save_decision_unavailable") from None
    end = _now(clock)
    keys = {"status", "binding", "policy_id", "policy_revision", "registry_revision", "decided_at"}
    if type(decision) is not dict or set(decision) != keys or end < start:
        raise ProducerCaptureRefused("save_decision_invalid")
    echo = decision["binding"]
    if type(echo) is not dict or set(echo) != set(expected) or any(
            type(echo[key]) is not type(value) or echo[key] != value for key, value in expected.items()):
        raise ProducerCaptureRefused("save_decision_invalid")
    for field in ("policy_id", "policy_revision", "registry_revision"):
        if not source._is_valid_scalar(decision[field]):
            raise ProducerCaptureRefused("save_decision_invalid")
    instant = source._instant_order(decision["decided_at"])
    if instant is None or not source._instant_order(start.isoformat()) <= instant <= source._instant_order(end.isoformat()):
        raise ProducerCaptureRefused("save_decision_invalid")
    if decision["status"] == "denied":
        raise ProducerCaptureRefused("save_denied", status="denied")
    if decision["status"] == "unavailable":
        raise ProducerCaptureRefused("save_unavailable")
    if decision["status"] != "allowed":
        raise ProducerCaptureRefused("save_decision_invalid")
    return {field: decision[field] for field in ("policy_id", "policy_revision", "registry_revision")}


def capture_producer_sources(
    descriptor: source.ScenarioSourceDescriptor, viewer: source.ViewerIdentity, *,
    operation_id: str, producer_read: Callable[[str], bytes] | None = None,
    s3: Any = None, bucket: str | None = None, destination=None,
    source_save_decision=None, retention_decision=None, current_viewer=None, clock=None,
) -> RetainedProducerCapture:
    """Retain an intentional expected producer version, then emit metadata only.

    No browser bytes, automatic nightly retention, public source read or latest
    fallback. Existing retention exceptions (including partial/uncertain effect)
    propagate unchanged; this function never replays a write or claims rollback.
    """
    if not all(callable(fn) for fn in (producer_read, destination, source_save_decision,
                                      retention_decision, current_viewer)) or s3 is None or not bucket:
        raise ProducerCaptureRefused("capture_binding_unavailable")
    source._validate_descriptor(descriptor)
    if (descriptor.moves is not None and descriptor.moves.session != descriptor.gex.session):
        raise ProducerCaptureRefused("capture_intent_invalid")
    if descriptor.grant_id is not None or type(operation_id) is not str or not source._UUID.fullmatch(operation_id):
        raise ProducerCaptureRefused("capture_intent_invalid")
    if not isinstance(viewer, source.ViewerIdentity) or not all(source._is_valid_scalar(value)
            for value in (viewer.viewer_id, viewer.viewer_issuer, viewer.auth_epoch)):
        raise ProducerCaptureRefused("current_actor_unavailable")
    descriptor = replace(descriptor, lens=MappingProxyType(dict(descriptor.lens)))
    clock = clock or (lambda: datetime.now(timezone.utc))
    if source._instant_order(descriptor.evaluated_at) > source._instant_order(_now(clock).isoformat()):
        raise ProducerCaptureRefused("capture_clock_future")
    _actor(current_viewer, viewer)
    refs = [descriptor.gex] + ([] if descriptor.moves is None else [descriptor.moves])
    binding = {"action": SAVE_ACTION, "purpose": SAVE_PURPOSE, "producer": PRODUCER,
               "source_scope": SOURCE_SCOPE, "bucket": bucket, "viewer_id": viewer.viewer_id,
               "viewer_issuer": viewer.viewer_issuer, "auth_epoch": viewer.auth_epoch,
               "investigation_id": descriptor.investigation_id,
               "revision": descriptor.investigation_revision, "operation_id": operation_id,
               "grant_id": None, "model_version": descriptor.model_version,
               "root": descriptor.root, "session": descriptor.gex.session,
               "source_as_of": descriptor.source_as_of, "evaluated_at": descriptor.evaluated_at,
               "lens": dict(descriptor.lens), "selection_key": descriptor.selection_key,
               "declared_basis_sha256": descriptor.basis_sha256,
               "refs": [ref.version_ref for ref in refs]}
    policy = _save_decision(source_save_decision, binding, clock)
    retention.qualify_destination(destination, bucket, "retain", refs)
    _actor(current_viewer, viewer)
    pairs = []
    for ref in refs:
        try:
            raw = producer_read(ref.kind)
        except Exception:
            raise ProducerCaptureRefused("producer_source_unavailable") from None
        # Strict native schema/root/session/hash/length validation; preserve exact bytes.
        payload = retention.verify_snapshot(ref, raw, today=_now(clock).date())
        if ref.kind == "gex":
            projection = payload.get("exposure_projection")
            actual_clock = (projection.get("clocks") or {}).get("option_observed_at") if type(projection) is dict else None
            if actual_clock != descriptor.source_as_of:
                raise ProducerCaptureRefused("producer_source_clock_mismatch")
        pairs.append((ref, raw))
    result = RetainedProducerCapture(descriptor, operation_id, **policy)

    def emit_metadata():
        try:
            _actor(current_viewer, viewer)
        except ProducerCaptureRefused as exc:
            raise ProducerCaptureRefused(exc.code, status=exc.status,
                effect_stage="after_retention_metadata_withheld") from None
        # This is transient metadata emission, not a DB/grant/manifest publication.
        return result.boundary()

    retention.retain_before_publish(
        s3, bucket, pairs, emit_metadata,
        action=retention.RetentionAction(authority=viewer.viewer_id, purpose=SAVE_PURPOSE),
        retention_decision=retention_decision, destination=destination, today=_now(clock).date())
    return result


def capture_built_scenario_sources(descriptor, viewer, *, operation_id: str,
                                  out_dir: Path, s3=None, bucket=None,
                                  destination=None, source_save_decision=None,
                                  retention_decision=None, current_viewer=None, clock=None):
    """Deliberate PRIVATE capture of expected bytes already serialized by this producer.

    This is not called by the nightly loop and does not build/recompute/fetch or
    upload a public head. A native caller must supply current Save/retention and
    private-destination bindings. No binding is configured by importing this file.
    Browser bytes and arbitrary source paths are not accepted. The composer
    checks exact expected identities before retention and emits metadata only;
    it does not verify native TS scenario math or apply a canonical save.
    """
    import os
    import stat

    def producer_read(kind):
        ref = descriptor.gex if kind == "gex" else descriptor.moves if kind == "moves" else None
        if ref is None:
            raise ValueError("source kind unavailable")
        # Hold directory descriptors and refuse symlink/FIFO source leaves. The
        # root and expected length have already passed native descriptor checks.
        with_fd = os.open(out_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        kind_fd = file_fd = None
        try:
            kind_fd = os.open(kind, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=with_fd)
            file_fd = os.open(f"{descriptor.root}.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=kind_fd)
            info = os.fstat(file_fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size != ref.byte_length:
                raise ValueError("producer source changed")
            with os.fdopen(file_fd, "rb") as handle:
                file_fd = None
                return handle.read(ref.byte_length + 1)
        finally:
            if file_fd is not None:
                os.close(file_fd)
            if kind_fd is not None:
                os.close(kind_fd)
            os.close(with_fd)

    return capture_producer_sources(descriptor, viewer, operation_id=operation_id,
        producer_read=producer_read, s3=s3, bucket=bucket, destination=destination,
        source_save_decision=source_save_decision, retention_decision=retention_decision,
        current_viewer=current_viewer, clock=clock)
