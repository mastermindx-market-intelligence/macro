"""Server wiring for P052, using the existing private Research Vault transport.

Licensing is settled by the Chairman's named-source attestation. User/resource
authorization is still observed through uncached Auth/billing and caller-token
RLS on every request. Activation and capture are separately default-off; importing
or installing this module does not perform remote IO or change storage policies.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path

from engine.research_vault import r2_store
from engine.options_hub_retention import PrivateScenarioObjects as _PrivateObjects

POLICY_ID = "DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023"
@dataclass(frozen=True)
class ScenarioSourceRuntime:
    store: r2_store.R2Store
    producer_out_dir: Path | None
    capture_enabled: bool

    def for_request(self, *, token, principal, investigation_id, revision,
                    grant_id, capture, mode, expected_revision=None, operation_id=None):
        # Lazy import avoids app.main/router cycles. No token or principal is
        # stored in app.state: these closures belong only to this HTTP request.
        from app import options_scenarios as route
        from engine import options_scenario_capture as producer

        descriptor = route._descriptor(capture, investigation_id, revision, grant_id)
        # Whole moves artifacts may include calibration from the distinct Levels
        # Yahoo index-grading route. The Research Factory attestation does not
        # establish that route's provenance. Preserve its reference and refuse;
        # never strip fields or silently substitute a GEX-only request.
        if descriptor.moves is not None:
            raise route._refuse_unavailable("source_unavailable")
        refs = [descriptor.gex] + ([] if descriptor.moves is None else [descriptor.moves])
        versions = [ref.version_ref for ref in refs]
        bucket = self.store.bucket
        actor = (principal.principal_id, principal.principal_issuer, principal.auth_epoch)
        snapshot = deepcopy(capture)

        def current_access():
            route._recheck_context(token, principal, investigation_id, revision,
                                   grant_id, snapshot if mode == "resolve" else None)
            if mode != "resolve":
                route._check_prospective(token, investigation_id, expected_revision)

        def source_matches(binding):
            return (binding.get("viewer_id"), binding.get("viewer_issuer"),
                    binding.get("auth_epoch")) == actor and all(
                binding.get(k) == v for k, v in {
                    "resource_owner": "options_hub", "resource_kind": "gex",
                    "action": "evaluate", "investigation_id": investigation_id,
                    "investigation_revision": revision, "grant_id": grant_id,
                    "root": descriptor.root, "sha256": descriptor.gex.sha256,
                    "byte_length": descriptor.gex.byte_length, "session": descriptor.gex.session,
                    "moves_ref": None if descriptor.moves is None else descriptor.moves.version_ref,
                    "model_version": descriptor.model_version,
                    "lens": dict(descriptor.lens), "selection_key": descriptor.selection_key,
                    "source_as_of": descriptor.source_as_of,
                    "basis_sha256": descriptor.basis_sha256,
                    "evaluated_at": descriptor.evaluated_at}.items())

        def resource_access(binding):
            if not source_matches(binding):
                return False
            current_access()
            return True

        def decision(binding, allowed):
            return {"status": "allowed" if allowed else "denied",
                    "binding": deepcopy(binding), "policy_id": POLICY_ID,
                    "policy_revision": "2026-10-23", "registry_revision": "p052/v1",
                    "decided_at": datetime.now(timezone.utc).isoformat()}

        def source_use(binding):
            return decision(binding, resource_access(binding))

        def destination(binding):
            requested = binding.get("refs")
            allowed = (binding.get("owner") == "options_hub"
                       and binding.get("bucket") == bucket
                       and binding.get("operation") in ("read", "retain")
                       and type(requested) is list and bool(requested)
                       and len(set(requested)) == len(requested)
                       and all(v in versions for v in requested)
                       and (binding["operation"] == "read" or
                            (mode == "capture" and self.capture_enabled)))
            return {"status": "qualified" if allowed else "denied", "binding": deepcopy(binding)}

        def save(binding):
            expected = {"action": producer.SAVE_ACTION, "purpose": producer.SAVE_PURPOSE,
                        "producer": producer.PRODUCER, "source_scope": producer.SOURCE_SCOPE,
                        "bucket": bucket, "viewer_id": actor[0], "viewer_issuer": actor[1],
                        "auth_epoch": actor[2], "investigation_id": investigation_id,
                        "revision": revision, "operation_id": operation_id, "grant_id": None,
                        "model_version": descriptor.model_version, "root": descriptor.root,
                        "session": descriptor.gex.session, "source_as_of": descriptor.source_as_of,
                        "evaluated_at": descriptor.evaluated_at, "lens": dict(descriptor.lens),
                        "selection_key": descriptor.selection_key,
                        "declared_basis_sha256": descriptor.basis_sha256, "refs": versions}
            allowed = mode == "capture" and self.capture_enabled and grant_id is None and binding == expected
            if allowed:
                current_access()
            return decision(binding, allowed)

        def retain(binding):
            expected = {"owner": "options_hub", "bucket": bucket, "operation": "retain",
                        "principal": actor[0], "purpose": producer.SAVE_PURPOSE, "refs": versions}
            allowed = mode == "capture" and self.capture_enabled and grant_id is None and binding == expected
            if allowed:
                current_access()
            return {"status": "allowed" if allowed else "denied", "binding": deepcopy(binding)}

        return route.SourceScenarioBindings(
            s3=_PrivateObjects(self.store, self.capture_enabled), bucket=bucket,
            destination=destination, resource_access=resource_access, source_use_decision=source_use,
            current_viewer=route._current_viewer_seam(token),
            producer_out_dir=self.producer_out_dir if self.capture_enabled else None,
            source_save_decision=save, retention_decision=retain)


def install_scenario_sources(app):
    """Construct from the existing private store, only on explicit activation.

    RESEARCH_LOCAL_STORE is an offline test route and cannot activate this HTTP
    service. No generic credentials/public bucket fallback or ACL probe exists.
    Deployment owners retain the separate live activation decision.
    """
    if os.environ.get("OPTIONS_SCENARIO_SOURCE_ENABLED") != "1":
        return
    if os.environ.get("RESEARCH_LOCAL_STORE"):
        return
    bucket = (os.environ.get("R2_RESEARCH_BUCKET") or "").strip()
    if not bucket or bucket == (os.environ.get("R2_BUCKET") or "").strip():
        return
    capture = os.environ.get("OPTIONS_SCENARIO_CAPTURE_ENABLED") == "1"
    producer = os.environ.get("OPTIONS_SCENARIO_PRODUCER_DIR")
    path = Path(producer) if producer else None
    if capture and (path is None or not path.is_absolute() or path.is_symlink() or not path.is_dir()):
        return
    store = r2_store.build_store(single_attempt_writes=True)
    if not isinstance(store, r2_store.R2Store) or not store.available or store.bucket != bucket:
        return
    store.validate_strict_conditional_write_capability()
    app.state.options_scenario_source_bindings = ScenarioSourceRuntime(store, path, capture)
