"""Trusted full Matrix display capture -> source-use context; no route or grant.

The admitted server injects its exact captured Matrix/selection/identity, actual
principal, snapshot-to-dataset binding and audited rights determination. None of
these Python objects authenticates its origin. Policy/browser values must never
supply these inputs. Missing real bindings remain unavailable.

The existing /api/flow?f=matrix:<ROOT> delivery sends the whole JSON document.
Every returned top-level member denotes its ENTIRE subtree, including all cell
metrics, levels, heat_seeker and build metadata. Selection/view filters cannot
narrow this release. Matrix combines OI, volume/history and Greeks into derived
outputs (engine/options_matrix.py); a source-layer relabel is refused. There is
no native Matrix export handler to resolve here.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from engine.options_matrix_retention import SnapshotReference, verify_snapshot
from lib.dataos.registry import Layer, Registry, RIGHTS_KEYS

from .entity import IdentityArtifactRead
from .options_identity import (
    OptionMatrixSelectionIdentity, OptionCoordinate, _parse_selection_document,
    _selection_documents, _selection_hidden,
)
from .options_source_use import (
    MATRIX_OWNER, MATRIX_SCHEMA, ServerUseContext, SourceUseRefused,
    _is_valid_scalar, _resolve_contract, _validate_context, _validate_request,
)
from .options_use import OptionUseRequest


@dataclass(frozen=True)
class MatrixDatasetBinding:
    """Trusted native lineage binding, supplied independently of the policy.

    Native Matrix JSON does not contain dataset_id/version/source_family. The
    admitted integration must bind these genuine external facts to this exact
    snapshot; matching Python values prove consistency only, not provenance.
    No production values are supplied or discovered by this module.
    """

    snapshot: SnapshotReference
    dataset_id: str
    dataset_version: str
    vendor: str
    source_family: str


@dataclass(frozen=True)
class MatrixDisplayContextResolver:
    """One server-captured full-payload display, callable for each fresh nonce.

    ``identity`` must be the existing native selection resolver's result for
    ``matrix`` and ``selection``. Auth/entitlement still run in the composed
    consumer. The three principal fields come from the authenticated handler.
    ``required_rights_rationale`` is the separately audited determination for
    the ACTUAL full payload/customer/channel, never copied from policy scope.
    A nonempty rationale is an explicit input, not proof of legal sufficiency.
    No right is inferred here from display, derived, purchase or upstream rows.
    """

    identity: OptionMatrixSelectionIdentity
    matrix: IdentityArtifactRead
    selection: bytes
    release_body: bytes
    principal_id: str
    principal_issuer: str
    auth_epoch: str
    registry: Registry
    dataset_binding: MatrixDatasetBinding | None = None
    required_rights_rationale: tuple[tuple[str, str], ...] = ()

    def __call__(self, request: OptionUseRequest) -> ServerUseContext:
        request = _validate_request(request)
        if type(self.identity) is not OptionMatrixSelectionIdentity:
            raise SourceUseRefused("context_unavailable", "native selection identity is absent")
        if (type(self.matrix) is not IdentityArtifactRead or type(self.selection) is not bytes
                or type(self.release_body) is not bytes):
            raise SourceUseRefused("context_unavailable", "native captured bytes are absent")
        ref = self.identity.matrix.snapshot
        try:
            payload = verify_snapshot(ref, self.matrix.body)
        except Exception:
            raise SourceUseRefused("context_binding_mismatch", "captured Matrix bytes do not match") from None
        if (self.release_body != self.matrix.body or self.matrix.sha256 != ref.sha256
                or hashlib.sha256(self.selection).hexdigest() != request.selection_sha256):
            raise SourceUseRefused("context_binding_mismatch", "captured artifact digest does not match")
        # Reuse the native closed selection parser. The identity object carries
        # coordinates/view rather than a byte digest, so request-hash equality
        # alone would not join a mismatched identity-A/selection-B capture.
        try:
            primary, comparisons, view = _selection_documents(
                _parse_selection_document(self.selection))
            if (self.identity.primary != OptionCoordinate(*primary)
                    or self.identity.comparisons != tuple(OptionCoordinate(*c) for c in comparisons)
                    or self.identity.view != view
                    or self.identity.primary_hidden != _selection_hidden(primary[0], primary[2], view)
                    or self.identity.comparisons_hidden != tuple(
                        _selection_hidden(c[0], c[2], view) for c in comparisons)):
                raise ValueError("selection identity mismatch")
        except Exception:
            raise SourceUseRefused("context_binding_mismatch", "native identity is not this selection") from None
        expected = dict(
            principal_id=self.principal_id, principal_issuer=self.principal_issuer,
            auth_epoch=self.auth_epoch, owner=MATRIX_OWNER, schema=MATRIX_SCHEMA,
            root=ref.root, sha256=ref.sha256, byte_length=ref.byte_length,
            session=ref.session, vendor=self.identity.matrix.underlying.binding.vendor,
            underlying_id=self.identity.matrix.underlying.binding.security_id,
            action="display",
        )
        for name, value in expected.items():
            actual = getattr(request, name)
            if type(actual) is not type(value) or actual != value:
                raise SourceUseRefused("context_binding_mismatch", "request is not this captured display")
        binding = self.dataset_binding
        if type(binding) is not MatrixDatasetBinding:
            raise SourceUseRefused("context_unavailable", "native snapshot-to-dataset binding is absent")
        if binding.snapshot != ref or binding.vendor != request.vendor:
            raise SourceUseRefused("context_binding_mismatch", "native dataset binding is not this capture")
        for value in (binding.dataset_id, binding.dataset_version, binding.source_family):
            if not _is_valid_scalar(value):
                raise SourceUseRefused("context_unavailable", "native dataset binding is incomplete")
        contract = _resolve_contract(self.registry, binding.dataset_id, binding.vendor)
        if contract.layer is not Layer.L3_DERIVED:
            raise SourceUseRefused("context_dataset_mismatch", "Matrix composition is not a source dataset")
        if contract.version != binding.dataset_version:
            raise SourceUseRefused("dataset_version_mismatch", "native captured dataset version changed")
        rationale = self.required_rights_rationale
        if (type(rationale) is not tuple or not rationale
                or any(type(item) is not tuple or len(item) != 2
                       or item[0] not in RIGHTS_KEYS or not _is_valid_scalar(item[1])
                       for item in rationale)
                or len({item[0] for item in rationale}) != len(rationale)):
            raise SourceUseRefused("context_unavailable", "audited full-output rights determination is absent")
        context = ServerUseContext(
            binding=request, dataset_id=contract.dataset_id, vendor=contract.vendor,
            source_family=binding.source_family, fields=tuple(sorted(payload)),
            output="derived", channel=f"/api/flow?f=matrix:{ref.root}",
            recipients=("authenticated_customer",), customer_id=self.principal_id,
            required_rights=tuple(item[0] for item in rationale),
        )
        return _validate_context(context, request)
