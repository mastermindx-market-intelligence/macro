"""HTTP-facing wrappers over the existing financial-query export encoders.

CSV is :meth:`MetricMatrix.export` unchanged. Parquet is the snapshot
cells projection :func:`_encode_cells_parquet`. Neither path is a second
pipeline.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .query import DeterministicExport, MetricMatrix
from .query_snapshots import _encode_cells_parquet

CSV_MEDIA_TYPE = "text/csv"
PARQUET_MEDIA_TYPE = "application/vnd.apache.parquet"
EXPORT_FORMATS = ("csv", "parquet")


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
