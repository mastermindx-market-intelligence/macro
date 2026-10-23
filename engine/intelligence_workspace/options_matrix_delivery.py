"""Native Matrix metadata/contract composition for an exact display response.

No registry enrollment, route, publisher, store or rights grant is created here.
The producer emits source dates, NOT dataset IDs, input hashes or known-at clocks.
Those missing facts cannot be recovered from the output digest or a policy file.
The server must supply genuine contract bindings independently of the request.
Python objects establish consistency, not the authenticity of that supply path.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re

from engine.options_matrix_retention import SnapshotReference, verify_snapshot
from lib.dataos.registry import Layer, Registry
from .options_matrix_context import MatrixDatasetBinding, MatrixDisplayContextResolver
from .options_source_use import (
    SourceUseRefused, OptionsSourceUseBackend, _resolve_contract, _is_valid_scalar,
)


def _refuse(detail):
    raise SourceUseRefused("context_unavailable", detail)


def _date(value, *, nullable=False):
    if value is None and nullable:
        return None
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        _refuse("native source date unavailable")
    try:
        date.fromisoformat(value)
    except ValueError:
        _refuse("native source date invalid")
    return value


@dataclass(frozen=True)
class MatrixProducerProvenance:
    """Observed producer fields; build_asof is NOT source publication/known-at."""

    snapshot: SnapshotReference
    build_asof: datetime
    eod: str | None
    greeks: str | None
    oi_publication: str
    previous_oi_publication: str | None
    latest_oi_publication: str
    history_start: str | None
    history_end: str | None
    history_sessions: int


def capture_matrix_provenance(ref, raw) -> MatrixProducerProvenance:
    """Read only fields actually emitted by engine.options_matrix.build_matrix.

    Null input dates remain absent. Later observed OI never replaces the selected
    session. An empty history window is distinct from an observed zero volume.
    This does not establish input-byte lineage or historical availability.
    """
    if type(ref) is not SnapshotReference or type(raw) is not bytes:
        _refuse("native capture unavailable")
    try:
        payload = verify_snapshot(ref, raw)
        session = _date(ref.session)
        meta = payload["_build_meta"]
        sources = meta["source_dates"]
        if type(meta) is not dict or type(sources) is not dict:
            _refuse("native metadata unavailable")
        if _date(meta["asof_date"]) != session:
            _refuse("native source session differs")
        stamp = payload["asof"]
        if type(stamp) is not str or "T" not in stamp:
            _refuse("native build clock unavailable")
        built = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if built.tzinfo is None or built.utcoffset() is None:
            _refuse("native build clock is naive")
        eod = _date(sources["eod"], nullable=True)
        greeks = _date(sources["greeks"], nullable=True)
        oi = _date(sources["oi_publication"])
        previous = _date(sources["previous_oi_publication"], nullable=True)
        latest = _date(sources["latest_oi_publication"])
        if (oi != session or any(v not in (None, session) for v in (eod, greeks))
                or latest < session or (previous is not None and previous >= session)
                or _date(meta["t2_date"], nullable=True) != previous):
            _refuse("native source clocks conflict")
        count = meta["unusual_history_sessions_available"]
        start = _date(meta["unusual_history_window_start"], nullable=True)
        end = _date(meta["unusual_history_window_end"], nullable=True)
        if type(count) is not int or not 0 <= count <= 30:
            _refuse("native history count invalid")
        if count == 0:
            if start is not None or end is not None:
                _refuse("empty history has dates")
        elif start is None or end is None or not start <= end < session:
            _refuse("native history window invalid")
        elif (count == 1) != (start == end):
            _refuse("native history bounds conflict with count")
        return MatrixProducerProvenance(ref, built, eod, greeks, oi, previous,
                                       latest, start, end, count)
    except SourceUseRefused:
        raise
    except Exception:
        _refuse("native producer capture invalid")


@dataclass(frozen=True)
class MatrixInputContract:
    """Server-owned role binding to an existing native row, never a new row."""

    role: str  # oi, eod (including history), greeks
    dataset_id: str
    version: str


def bind_matrix_contracts(provenance, binding, inputs, registry):
    """Join observed source roles to explicit produced rows and their exact DAG.

    No name search, default ID or policy-derived lineage is permitted. Missing
    enrollment refuses. The native metadata supplies session cutoffs only; it
    does not claim source artifact hashes or point-in-time known-at evidence.
    """
    if (type(provenance) is not MatrixProducerProvenance
            or type(binding) is not MatrixDatasetBinding
            or binding.snapshot != provenance.snapshot):
        _refuse("native snapshot contract binding unavailable")
    if type(inputs) is not tuple or len(inputs) != 3 or any(
            type(item) is not MatrixInputContract for item in inputs):
        _refuse("native input contract bindings unavailable")
    if any(not _is_valid_scalar(value) for item in inputs
           for value in (item.role, item.dataset_id, item.version)):
        _refuse("native input contract binding malformed")
    if {item.role for item in inputs} != {"oi", "eod", "greeks"}:
        _refuse("native source roles incomplete or duplicated")
    if len({item.dataset_id for item in inputs}) != 3:
        _refuse("distinct native source roles require distinct contracts")
    row = _resolve_contract(registry, binding.dataset_id, binding.vendor)
    if row.layer is not Layer.L3_DERIVED or row.version != binding.dataset_version:
        _refuse("native produced Matrix contract differs")
    if set(row.inputs) != {item.dataset_id for item in inputs} or len(row.inputs) != 3:
        _refuse("native Matrix input DAG differs from captured roles")
    for item in inputs:
        source = _resolve_contract(registry, item.dataset_id, binding.vendor)
        if source.version != item.version or source.layer not in (Layer.L0_SOURCE, Layer.L1_NORMALIZED):
            _refuse("native input contract version or layer differs")
    return binding


@dataclass(frozen=True)
class MatrixDisplaySource:
    """Server configuration/captures, supplied without reading policy for context.

    Construction alone does not validate or authorize anything. decision() binds
    the actual handler response bytes before the existing policy evaluator runs.
    Registry, pins and input role mapping must come from an audited native reader;
    there are deliberately no production defaults in this module.
    """

    registry: Registry
    binding: MatrixDatasetBinding | None
    inputs: tuple[MatrixInputContract, ...]
    required_rights_rationale: tuple[tuple[str, str], ...]
    evidence_sha256: str
    registry_revision: str
    evidence_root: object

    def decision(self, request, *, principal, identity, matrix, selection, release_body, clock):
        provenance = capture_matrix_provenance(identity.matrix.snapshot, matrix.body)
        binding = bind_matrix_contracts(provenance, self.binding, self.inputs, self.registry)
        resolver = MatrixDisplayContextResolver(
            identity=identity, matrix=matrix, selection=selection, release_body=release_body,
            principal_id=principal.principal_id, principal_issuer=principal.principal_issuer,
            auth_epoch=principal.auth_epoch, registry=self.registry, dataset_binding=binding,
            required_rights_rationale=self.required_rights_rationale,
        )
        return OptionsSourceUseBackend(
            registry=self.registry, dataset_id=binding.dataset_id,
            expected_evidence_sha256=self.evidence_sha256,
            expected_registry_revision=self.registry_revision,
            expected_source_family=binding.source_family,
            use_context_for_request=resolver, evidence_root=self.evidence_root,
            clock=clock,
        ).decision(request)
