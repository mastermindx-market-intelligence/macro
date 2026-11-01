"""HTTP-facing wrappers over the existing financial-query export encoders.

CSV is :meth:`MetricMatrix.export` unchanged. Parquet is the snapshot
cells projection :func:`_encode_cells_parquet`. Neither path is a second
pipeline.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from .query import DeterministicExport, MetricMatrix
from .query_snapshots import _encode_cells_parquet

CSV_MEDIA_TYPE = "text/csv"
PARQUET_MEDIA_TYPE = "application/vnd.apache.parquet"
EXPORT_FORMATS = ("csv", "parquet")

# A38/A40 explicit-difference declaration (X1-p).  Field paths are the JSON
# cell-node / provenance leaf paths (``CellNode.to_dict`` /
# ``CellProvenance.to_dict`` in query.py).  ``omitted_cell_fields`` is the
# exact set of those paths the format's per-root-cell rows cannot carry; the
# XLSX column set is byte-derived from the CSV projection
# (excel_export._rows_from_csv_bytes), so its omissions are identical.  This
# mapping is a declaration of what the encoders DO, kept self-checking by
# tests/test_fundamental_forensics_query_exports.py (completeness law: an
# undeclared omission fails, a declared field that is actually carried
# fails).
_CSV_XLSX_OMITTED_CELL_FIELDS = (
    "period.calendar_kind",
    "period.fiscal_year_weeks",
    "period.week_count",
    "period.inferred_week_count",
    "period.semantics",
    "period.label",
    "provenance.evaluation_policy",
    "provenance.policy",
    "provenance.source_snapshot_at",
    "provenance.recorded_cutoff_at",
    "provenance.source_entity_id",
    "provenance.source",
    "provenance.source_url",
    "provenance.source_body_sha256",
    "provenance.filing_metadata_available_at",
    "provenance.computed_at",
    "provenance.published_at",
    "provenance.taxonomy",
    "provenance.concept",
    "provenance.unit",
    "provenance.metric_rule_id",
    "provenance.metric_rule_version",
    "provenance.metric_rule_digest",
    "provenance.mapping_rule_ids",
    "provenance.mapping_rule_versions",
    "provenance.mapping_digests",
    "provenance.catalog_id",
    "provenance.catalog_version",
    "provenance.catalog_digest",
    "provenance.mapping_pack_version",
    "provenance.mapping_pack_digest",
    "provenance.formula_pack_version",
    "provenance.formula_pack_digest",
    "provenance.alias_priority",
    "provenance.selected_raw_fact",
    "provenance.issuer_class",
    "provenance.issuer_class_basis",
    # Not-presented evidence (step 5) is JSON-sidecar-only: the N/A basis
    # word and the linkbase evidence record have no tabular column.  The
    # qualified-sum operand list IS carried, by the reason-column marker.
    "provenance.na_basis",
    "provenance.not_presented",
)
_QUALIFIED_SUM_REASON_MARKER = (
    "a qualified sum (a formula VALUE carrying "
    "provenance.qualified_not_presented) has a null JSON reason; its reason "
    "column carries the in-row marker "
    "query.QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX ('qualified_not_presented: ') "
    "followed by the omitted operand IDs joined by ', ' "
    "(query._export_reason_text), so the row never reads as a plain sum; "
    "every other reason column is the cell reason verbatim"
)
_CSV_XLSX_ENCODING = (
    "receipt-level scalars (query_hash, receipt_authority, proof_scope, "
    "selection_proof, governance_bundle_id) repeat on every row; "
    "receipt_authority is the literal json_sidecar_required",
    "the JSON node's status field duplicates state and provenance.reason "
    "duplicates reason (CellNode.to_dict); the state and reason columns "
    "carry both",
    _QUALIFIED_SUM_REASON_MARKER,
    "the single unit column carries the cell unit; JSON additionally carries "
    "provenance.unit, which is not guaranteed equal on non-value cells, so "
    "it is declared omitted",
    "list fields (source_occurrence_ids, dependency_cell_ids) are "
    "canonical-JSON text columns (raw_ledger.canonical_json spelling)",
    "_csv_safe (query.py) prefixes a text field whose first character is one "
    "of = + - @ TAB CR with an apostrophe; the value column (index 15) is "
    "exempt so a negative Decimal stays numeric text",
    "nulls are the empty string",
    "the JSON sidecar additionally carries the full dependency-DAG node "
    "receipts; each row is one root cell plus its dependency_cell_ids links",
)
SERIALIZATION_DIFFERENCES: Mapping[str, Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "csv": MappingProxyType(
            {
                "omitted_cell_fields": _CSV_XLSX_OMITTED_CELL_FIELDS,
                "encoding": _CSV_XLSX_ENCODING,
            }
        ),
        "xlsx": MappingProxyType(
            {
                "omitted_cell_fields": _CSV_XLSX_OMITTED_CELL_FIELDS,
                "encoding": (
                    *_CSV_XLSX_ENCODING,
                    "columns are byte-derived from the CSV projection "
                    "(excel_export._rows_from_csv_bytes); _CSV_VALUE_INDEX "
                    "stays 15",
                    "a value that round-trips an IEEE-754 double "
                    "(excel_export._fits_ieee754) is a numeric cell; a "
                    "finite value that does not is an inlineStr cell "
                    "holding the exact decimal text verbatim (no `'` "
                    "prefix, negative included) and its A1 reference is "
                    "listed in the Meta sheet exact_text_cells",
                    "the null value column is an omitted cell (no <c> "
                    "element); other empty fields are empty inlineStr text "
                    "cells",
                ),
            }
        ),
        "parquet": MappingProxyType(
            {
                "omitted_cell_fields": (
                    *_CSV_XLSX_OMITTED_CELL_FIELDS,
                    "governance_bundle_id",
                    "provenance.form",
                    "provenance.filed_at",
                    "provenance.mapping_available_at",
                    "provenance.governance_available_at",
                    "provenance.mapping_digest",
                    "provenance.formula_digest",
                    "provenance.confidence",
                    "provenance.filing_metadata_content_sha256",
                ),
                "encoding": (
                    "every column is a Parquet STRING "
                    "(query_snapshots._parquet_schema; "
                    "QUERY_SNAPSHOT_PARQUET_SCHEMA "
                    "fundamental_forensics.query_snapshot_cells/v1)",
                    "the JSON node's status field duplicates state and "
                    "provenance.reason duplicates reason (CellNode.to_dict); "
                    "the state and reason columns carry both",
                    _QUALIFIED_SUM_REASON_MARKER,
                    "the single unit column carries the cell unit; JSON "
                    "additionally carries provenance.unit, which is not "
                    "guaranteed equal on non-value cells, so it is declared "
                    "omitted",
                    "list fields are canonical-JSON text in the *_json "
                    "columns (same raw_ledger.canonical_json spelling as the "
                    "CSV columns)",
                    "no _csv_safe guarding: Parquet is not a spreadsheet "
                    "surface, so text is stored verbatim",
                    "nulls are null STRING values",
                    "the JSON sidecar additionally carries the full "
                    "dependency-DAG node receipts; each row is one root cell "
                    "plus its dependency_cell_ids links",
                ),
            }
        ),
    }
)


class QueryExportError(ValueError):
    """The envelope cannot be exported as the requested format."""


def matrix_from_envelope(envelope: Mapping[str, Any]) -> MetricMatrix:
    """Rebuild the receipt matrix and require an exact ``to_dict`` round-trip."""
    try:
        matrix = MetricMatrix.from_dict(envelope["receipt"])
    except Exception as exc:
        raise QueryExportError("query envelope is not an exportable receipt") from exc
    if matrix.to_dict() != envelope["receipt"]:
        raise QueryExportError("query envelope receipt round-trip mismatch")
    return matrix


def export_query_envelope(envelope: Mapping[str, Any], fmt: str) -> DeterministicExport:
    """Project ``envelope`` through the existing CSV or Parquet encoder."""
    matrix = matrix_from_envelope(envelope)
    if fmt == "csv":
        return matrix.export("csv")
    if fmt == "parquet":
        return DeterministicExport.from_payload(
            media_type=PARQUET_MEDIA_TYPE,
            payload=_encode_cells_parquet(matrix)[0],
        )
    raise QueryExportError(f"unsupported export format: {fmt!r}")
