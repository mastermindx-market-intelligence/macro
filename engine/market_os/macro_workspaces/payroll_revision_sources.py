"""Builder-only PAYEMS source projection; existing Release Target truth owns arithmetic."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from engine.market_os.macro_workspaces.payroll_revisions import METHOD, MAX_PERIODS, _day

def project_payroll_revisions(frame: Any, *, cutoff: str, manifest_receipt: Mapping,
                              artifact_receipt: Mapping, limit: int = MAX_PERIODS) -> dict:
    """Use two same-vintage reconstructions per month; never mix prior levels."""
    import pandas as pd
    from engine.release_target_truth import normalize_full_vintage_frame, reconstruct_release_target

    cutoff = _day(cutoff)
    if type(limit) is not int or not 1 <= limit <= MAX_PERIODS:
        raise ValueError("payroll revision period bound is invalid")
    normalized = normalize_full_vintage_frame(frame, series_id="PAYEMS")
    eligible = normalized[(normalized["realtime_start"] <= pd.Timestamp(cutoff)) &
                          (normalized["period"] <= pd.Timestamp(cutoff))].copy()
    # Future supersession endpoints can be used internally to select a row,
    # but no endpoint, future cohort count or maximum is emitted to the view.
    rows = []
    if not eligible.empty:
        selected = eligible["realtime_start"].max().date().isoformat()
        periods = sorted(eligible["period"].unique())[-limit:]
        for period in periods:
            period = pd.Timestamp(period)
            pair = eligible[eligible["period"].isin([period, period - pd.offsets.MonthBegin(1)])]
            earliest = reconstruct_release_target(pair, series_id="PAYEMS", period=period, as_of=cutoff)
            current = reconstruct_release_target(pair, series_id="PAYEMS", period=period,
                                                 release_date=selected, as_of=cutoff)
            first_value = earliest.get("payroll_change_thousands") if earliest["status"] == "ok" else None
            current_value = current.get("payroll_change_thousands") if current["status"] == "ok" else None
            rows.append({
                "period": period.date().isoformat(), "earliest_change": first_value,
                "selected_change": current_value,
                "net_revision": current_value - first_value if first_value is not None and current_value is not None else None,
                "earliest_vintage": earliest.get("release_date"), "selected_vintage": selected,
            })
    return {
        "method": METHOD, "cutoff": cutoff, "rows": rows,
        "source_digest": artifact_receipt["artifact_sha256"],
        "manifest_digest": manifest_receipt["artifact_sha256"],
        "collected_at": manifest_receipt.get("collected_at"),
        "unavailable_reason": None if rows else "INSUFFICIENT_HISTORY",
    }


def load_payroll_revisions(directory: Path | str, *, built_at: str, as_of: str | None = None) -> dict:
    """Missing/incomplete cohort is typed absent; corrupt present data aborts."""
    directory = Path(directory)
    built = datetime.fromisoformat(built_at.replace("Z", "+00:00"))
    if built.utcoffset() is None:
        raise ValueError("payroll build time needs a timezone")
    cutoff = _day(as_of) if as_of is not None else built.astimezone(timezone.utc).date().isoformat()
    if cutoff > built.astimezone(timezone.utc).date().isoformat():
        raise ValueError("payroll cutoff is after the publication day")
    unavailable = {"method": METHOD, "cutoff": cutoff, "rows": [], "source_digest": None,
                   "manifest_digest": None, "collected_at": None, "unavailable_reason": "NOT_COVERED"}
    manifest, parquet = directory / "manifest.json", directory / "PAYEMS_all_vintages.parquet"
    if not manifest.is_file() or not parquet.is_file():
        return unavailable
    from engine.release_target_cohort import ReleaseTargetCohortError, ReleaseTargetCohortUnavailable, read_release_target_cohort
    try:
        frames, _, receipt, artifacts = read_release_target_cohort(manifest, {"PAYEMS": parquet})
    except ReleaseTargetCohortUnavailable:
        return unavailable
    if datetime.fromisoformat(receipt["completed_at"]) > built:
        raise ReleaseTargetCohortError("payroll cohort completed after the publication instant")
    return project_payroll_revisions(frames["PAYEMS"], cutoff=cutoff,
                                    manifest_receipt=receipt, artifact_receipt=artifacts["PAYEMS"])


