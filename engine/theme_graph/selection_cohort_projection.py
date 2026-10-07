"""Read-only product projection over a finalized selection-cohort read packet."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from engine.theme_graph import rights
from engine.theme_graph.selection_cohort import (
    FLAGS,
    SCHEMA as READ_SCHEMA,
    validate_selection_cohort,
)

SCHEMA = "mastermind.selection_cohort_projection.v1"
SOURCE_SCHEMA = READ_SCHEMA
PROJECTION_LIMITATIONS: tuple[str, ...] = (
    "Read-only nightly projection; it never ranks, sizes, gates, or mutates the cohort.",
    "Concepts appear only when display rights resolve; withheld concepts leave no public identifiers.",
    "Not an input to ranking, readiness, sizing, or board mutation.",
    "Derived from the canonical read packet and may be honestly unavailable when the source is.",
)

_WITHHELD_INTERNAL = "RIGHTS_INTERNAL_ONLY"
_WITHHELD_UNRESOLVED = "RIGHTS_FAMILY_UNRESOLVED"


def _authority_block() -> dict[str, Any]:
    return dict(
        authority_ceiling="research_internal_only",
        **{flag: False for flag in FLAGS},
    )


def _concept_display_rights(
    concepts: list[Mapping[str, Any]], *, rights_path: str | Path | None
) -> tuple[dict[str, str], dict[str, int]]:
    """Map node_id -> withheld reason or displayable; aggregate withheld_reason counts."""
    withheld_reasons = {_WITHHELD_INTERNAL: 0, _WITHHELD_UNRESOLVED: 0}
    disposition: dict[str, str] = {}
    for entry in concepts:
        node_id = entry.get("node_id")
        if not isinstance(node_id, str):
            withheld_reasons[_WITHHELD_UNRESOLVED] += 1
            continue
        family = rights.family_for_node_id(node_id)
        if family is None:
            withheld_reasons[_WITHHELD_UNRESOLVED] += 1
            disposition[node_id] = _WITHHELD_UNRESOLVED
            continue
        try:
            _internal, display_ok, _redist = rights.licensing_for_family(
                family, path=rights_path
            )
        except Exception:
            withheld_reasons[_WITHHELD_UNRESOLVED] += 1
            disposition[node_id] = _WITHHELD_UNRESOLVED
            continue
        if not display_ok:
            withheld_reasons[_WITHHELD_INTERNAL] += 1
            disposition[node_id] = _WITHHELD_INTERNAL
        else:
            disposition[node_id] = "DISPLAY"
    return disposition, withheld_reasons


def _unavailable_document(unavailable_reason: str) -> dict[str, Any]:
    return dict(
        schema=SCHEMA,
        source_schema=SOURCE_SCHEMA,
        availability=dict(status="UNAVAILABLE", overlap="UNAVAILABLE"),
        unavailable_reason=unavailable_reason,
        **_authority_block(),
        explanation_id=None,
        selection_sha256=None,
        generation_id=None,
        cohort_scope=None,
        effective_at=None,
        known_at=None,
        version=None,
        n_selected=0,
        selected=[],
        coverage={},
        concept_rights=dict(
            n_concepts_total=0,
            n_concepts_displayable=0,
            n_concepts_withheld=0,
            withheld_reasons={
                _WITHHELD_INTERNAL: 0,
                _WITHHELD_UNRESOLVED: 0,
            },
        ),
        limitations=list(PROJECTION_LIMITATIONS),
    )


def _resolve_read_packet(wrapper: Any) -> tuple[dict[str, Any] | None, str | None]:
    if wrapper is None or not isinstance(wrapper, dict):
        return None, "WRAPPER_MISSING"
    if wrapper.get("status") != "AVAILABLE":
        codes = wrapper.get("reason_codes")
        suffix = ""
        if isinstance(codes, list) and codes:
            suffix = ":" + ",".join(str(c) for c in codes)
        return None, "SOURCE_UNAVAILABLE" + suffix
    explanation = wrapper.get("explanation")
    if not isinstance(explanation, dict):
        return None, "EXPLANATION_UNAVAILABLE"
    if explanation.get("schema") != SOURCE_SCHEMA:
        return None, "READ_PACKET_INVALID"
    try:
        validate_selection_cohort(explanation)
    except Exception:
        return None, "READ_PACKET_INVALID"
    return explanation, None


def project_selection_cohort_for_product(
    wrapper: Any, *, rights_path: str | Path | None = None
) -> dict[str, Any]:
    read_packet, unavailable = _resolve_read_packet(wrapper)
    if read_packet is None:
        return _unavailable_document(unavailable or "WRAPPER_MISSING")

    concepts = read_packet.get("concepts") or []
    if not isinstance(concepts, list):
        concepts = []
    disposition, withheld_reasons = _concept_display_rights(
        concepts, rights_path=rights_path
    )
    n_displayable = sum(1 for v in disposition.values() if v == "DISPLAY")
    n_withheld = len(disposition) - n_displayable

    selected_out: list[dict[str, Any]] = []
    for row in read_packet.get("selected") or []:
        if not isinstance(row, Mapping):
            continue
        source = row.get("source") or {}
        selection_id = source.get("selection_id")
        concept_ids = row.get("concept_node_ids") or []
        if not isinstance(concept_ids, list):
            concept_ids = []
        concepts_display: list[dict[str, str]] = []
        for concept in concepts:
            if not isinstance(concept, Mapping):
                continue
            node_id = concept.get("node_id")
            if disposition.get(node_id) != "DISPLAY":
                continue
            selected_ids = concept.get("selected_ids") or []
            if selection_id in selected_ids:
                concepts_display.append(
                    dict(node_id=node_id, kind=str(concept.get("kind", "")))
                )
        n_concepts = len(concept_ids)
        selected_out.append(
            dict(
                selection_id=selection_id,
                original_identity=source.get("original_identity"),
                security_id=row.get("security_id"),
                reason_codes=list(row.get("reason_codes") or []),
                original_reasons=source.get("original_reasons"),
                n_concepts=n_concepts,
                concepts_display=concepts_display,
                n_concepts_withheld=n_concepts - len(concepts_display),
            )
        )

    source_selection = read_packet.get("source_selection") or {}
    version = read_packet.get("version")
    limitations = list(read_packet.get("limitations") or []) + list(PROJECTION_LIMITATIONS)

    return dict(
        schema=SCHEMA,
        source_schema=SOURCE_SCHEMA,
        availability=dict(read_packet.get("availability") or {}),
        unavailable_reason=None,
        **_authority_block(),
        explanation_id=read_packet.get("explanation_id"),
        selection_sha256=read_packet.get("selection_sha256"),
        generation_id=source_selection.get("generation_id"),
        cohort_scope=source_selection.get("cohort_scope"),
        effective_at=source_selection.get("effective_at"),
        known_at=source_selection.get("known_at"),
        version=copy_version(version),
        n_selected=(
            int(source_selection["n_selected"])
            if isinstance(source_selection, Mapping)
            and isinstance(source_selection.get("n_selected"), int)
            else len(selected_out)
        ),
        selected=selected_out,
        coverage=dict(read_packet.get("coverage") or {}),
        concept_rights=dict(
            n_concepts_total=len(disposition),
            n_concepts_displayable=n_displayable,
            n_concepts_withheld=n_withheld,
            withheld_reasons=withheld_reasons,
        ),
        limitations=limitations,
    )


def copy_version(version: Any) -> dict[str, Any] | None:
    if not isinstance(version, Mapping):
        return None
    return dict(
        number=int(version.get("number", 1)),
        corrects=version.get("corrects"),
        basis="AS_KNOWN_AT_SELECTION",
    )


def write_product_projection(
    site_dir: str | Path,
    market: str,
    wrapper: Any,
    *,
    rights_path: str | Path | None = None,
) -> Path:
    if market not in {"us", "cn"}:
        raise ValueError(f"unsupported market: {market}")
    doc = project_selection_cohort_for_product(wrapper, rights_path=rights_path)
    root = Path(site_dir)
    out_dir = root / "neuralwebdata" / "selection_cohort"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{market}.json"
    payload = (
        json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        + b"\n"
    )
    path.write_bytes(payload)
    return path
