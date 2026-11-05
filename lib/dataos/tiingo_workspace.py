"""Bounded Tiingo statement comparison through the existing host root binding."""
from __future__ import annotations

from typing import Any

from lib.dataos.web_workspace import DataWorkspace, WorkspaceError, _bound_int


def compare_statements(
    workspace: DataWorkspace, *, root: str, vendor_symbol: str,
    as_reported_capture: str, restated_capture: str,
    start: str, end: str, observed_before: str,
    acknowledge_hindsight: bool, offset: int = 0, limit: int = 20,
) -> dict[str, Any]:
    """No arbitrary path, provider access, execution or admission is accepted.

    Only the host's already-bound canonical Tiingo archive can be selected.
    Its directory identity is held and rechecked by the incumbent workspace
    confinement path. The existing reader verifies exact receipt/raw/output
    lineage, request dimensions, dates and capture cutoffs before returning.
    """
    from collectors.tiingo_archive import DEFAULT_ARCHIVE
    from scripts.tiingo_research_query import compare_statements as read_comparison

    _bound_int(offset, 0, 2**63 - 1)
    _bound_int(limit, 1, 50)
    binding = workspace._root(root)
    if binding.path != DEFAULT_ARCHIVE:
        raise WorkspaceError("TIINGO_ARCHIVE_NOT_BOUND")
    with workspace._directory(binding, ()):
        try:
            result = read_comparison(
                binding.path, vendor_symbol=vendor_symbol,
                as_reported_capture=as_reported_capture,
                restated_capture=restated_capture, start=start, end=end,
                observed_before=observed_before,
                acknowledge_hindsight=acknowledge_hindsight, max_rows=20_000,
            )
        except (ValueError, OSError, TypeError, OverflowError):
            raise WorkspaceError("TIINGO_STATEMENT_COMPARISON_REFUSED") from None
        comparison = dict(result["statement_comparison"])
        rows = comparison["comparison_rows"]
        page = rows[offset:offset + limit]
        comparison["comparison_rows"] = page
        comparison["pagination"] = {
            "offset": offset, "limit": limit, "returned": len(page),
            "total_comparison_keys": len(rows),
            "next_offset": offset + len(page) if offset + len(page) < len(rows) else None,
            "exact_capture_references_required_on_every_page": True,
        }
        return workspace._result(
            action="tiingo_compare_statements", root_alias=root,
            evidence_kind=binding.evidence_kind,
            **{k: v for k, v in result.items() if k != "statement_comparison"},
            statement_comparison=comparison,
        )
