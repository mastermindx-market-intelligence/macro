"""Tushare public-fund portfolio accrual — CIE-12 owner-native source tape.

Source: Tushare Pro fund_portfolio (official doc 121). The endpoint is gated by
the existing TUSHARE_TOKEN technical gate and is already covered by the
Chairman-verified private compliance decision. This module creates no new rights,
purchase, score, rank, manager identity, company master or trading authority.

PIT contract:
- ann_date is the vendor-stated announcement/availability date.
- end_date is the reporting-period end and is NEVER an availability clock.
- first_collected_at is Mastermind's own first observation of this exact row
  version. A later correction is retained as a new version, never backdated.
- collection is prospective by announcement date with a bounded calendar lookback;
  historical backfill is a separate explicitly chartered operation.

The current official endpoint page publishes rate limits but no row cap. Therefore
a successful response is evidence for the returned rows and requested date only; it
is NOT a population-completeness receipt. The health companion states that refusal
explicitly.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import pandas as pd

from collectors import tushare_client as tc
from collectors.china_tushare_spine import SpineError, canonical_identity
from lib import config

log = logging.getLogger("tushare_fund_portfolio")

_ASIA_SHANGHAI = ZoneInfo("Asia/Shanghai")
_LOOKBACK_DAYS = 8
_OFFICIAL_DOC = "https://tushare.pro/document/2?doc_id=121"
_FIELDS = (
    "ts_code,ann_date,end_date,symbol,mkv,amount,"
    "stk_mkv_ratio,stk_float_ratio"
)
_VENDOR_COLUMNS = (
    "ts_code",
    "ann_date",
    "end_date",
    "symbol",
    "mkv",
    "amount",
    "stk_mkv_ratio",
    "stk_float_ratio",
)
_VERSION_KEY = ("fund_code", "ann_date", "period_end", "security_id")
_STORE_COLUMNS = (
    "fund_code",
    "ann_date",
    "period_end",
    "source_symbol",
    "symbol",
    "security_id",
    "source_exchange",
    "market_value_cny",
    "shares",
    "fund_stock_mkv_ratio_pct",
    "float_share_pct",
    "source_known_at_date",
    "source_known_at_quality",
    "first_collected_at",
    "queried_ann_date",
    "payload_sha256",
    "version_ordinal",
    "supersedes_payload_sha256",
    "correction_observed",
)


def _out_path() -> Path:
    return config.data_dir() / "tushare" / "fund_portfolio.parquet"


def _health_path() -> Path:
    return config.data_dir() / "tushare" / "fund_portfolio_health.json"


def _clean(value: Any) -> str:
    try:
        if value is None or pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text in ("", "nan", "None", "NaT", "<NA>") else text


def _number(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if pd.notna(out) else None


def _canonical_hash(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _observation_time(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _announcement_dates(
    now: datetime | None = None,
    lookback_days: int = _LOOKBACK_DAYS,
) -> list[str]:
    """Newest-first Shanghai calendar dates, including today."""
    observed = _observation_time(now).astimezone(_ASIA_SHANGHAI).date()
    n = max(int(lookback_days), 1)
    return [(observed - timedelta(days=i)).strftime("%Y%m%d") for i in range(n)]


def _normalize_frame(
    frame: pd.DataFrame,
    *,
    queried_ann_date: str,
    observed_at: str,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Normalize only positively resolved mainland A-share identities.

    The vendor's symbol field is evidence, not canonical identity authority.
    Reuse Data OS canonical_identity so bare/malformed/off-venue values are
    excluded and accounted rather than entering the tape as if canonical.
    """
    missing = [name for name in _VENDOR_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError(f"fund_portfolio schema missing fields: {missing}")

    records: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for raw in frame.loc[:, list(_VENDOR_COLUMNS)].to_dict("records"):
        ann_date = _clean(raw.get("ann_date"))
        period_end = _clean(raw.get("end_date"))
        fund_code = _clean(raw.get("ts_code"))
        symbol_raw = _clean(raw.get("symbol"))

        if len(ann_date) != 8 or not ann_date.isdigit():
            raise ValueError("fund_portfolio row has invalid ann_date")
        if ann_date != queried_ann_date:
            raise ValueError(
                f"fund_portfolio response escaped ann_date scope: "
                f"{ann_date} != {queried_ann_date}"
            )
        if len(period_end) != 8 or not period_end.isdigit():
            raise ValueError("fund_portfolio row has invalid end_date")
        if not fund_code:
            raise ValueError("fund_portfolio row missing fund identity")

        try:
            identity = canonical_identity(symbol_raw)
        except SpineError:
            exclusions.append({
                "queried_ann_date": queried_ann_date,
                "source_symbol": symbol_raw,
                "reason": "unresolved_or_offscope_a_share_identity",
            })
            continue

        version_payload = {
            "fund_code": fund_code,
            "ann_date": ann_date,
            "period_end": period_end,
            "symbol": identity.ticker,
            "security_id": identity.security_id,
            "market_value_cny": _number(raw.get("mkv")),
            "shares": _number(raw.get("amount")),
            "fund_stock_mkv_ratio_pct": _number(raw.get("stk_mkv_ratio")),
            "float_share_pct": _number(raw.get("stk_float_ratio")),
        }
        records.append({
            **version_payload,
            "source_symbol": symbol_raw,
            "source_exchange": identity.source_exchange,
            "source_known_at_date": ann_date,
            "source_known_at_quality": "vendor_announcement_date_date_only",
            "first_collected_at": observed_at,
            "queried_ann_date": queried_ann_date,
            "payload_sha256": _canonical_hash(version_payload),
        })

    return pd.DataFrame(records), exclusions


def _with_lineage(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=list(_STORE_COLUMNS))

    out = frame.copy()
    for col in _VERSION_KEY + ("payload_sha256", "first_collected_at"):
        if col not in out.columns:
            raise ValueError(f"fund_portfolio store missing {col}")

    same_observation = out.groupby(
        [*_VERSION_KEY, "first_collected_at"],
        sort=False,
        dropna=False,
    )["payload_sha256"].nunique(dropna=False)
    if bool((same_observation > 1).any()):
        raise ValueError(
            "fund_portfolio conflicting payloads share one observation instant"
        )

    out = out.drop_duplicates(
        subset=[*_VERSION_KEY, "payload_sha256"],
        keep="first",
    )
    out = out.sort_values(
        [*_VERSION_KEY, "first_collected_at", "payload_sha256"],
        kind="stable",
    ).reset_index(drop=True)
    groups = out.groupby(list(_VERSION_KEY), sort=False, dropna=False)
    out["version_ordinal"] = groups.cumcount() + 1
    out["supersedes_payload_sha256"] = groups["payload_sha256"].shift(1).fillna("")
    out["correction_observed"] = out["version_ordinal"] > 1
    return out.reindex(columns=list(_STORE_COLUMNS))


def _read_existing() -> pd.DataFrame:
    path = _out_path()
    if not path.exists():
        return pd.DataFrame(columns=list(_STORE_COLUMNS))
    return _with_lineage(pd.read_parquet(path))


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def refresh(
    *,
    query_fn: Callable[..., pd.DataFrame | None] | None = None,
    now: datetime | None = None,
    lookback_days: int = _LOOKBACK_DAYS,
) -> int:
    """Accrue bounded announcement-date observations; return rows observed this run."""
    if not tc.enabled():
        return 0

    query = query_fn or tc.query
    observed = _observation_time(now)
    observed_at = observed.isoformat()
    requested = _announcement_dates(observed, lookback_days)

    successful: list[str] = []
    empty: list[str] = []
    unavailable: list[str] = []
    frames: list[pd.DataFrame] = []
    identity_exclusions: list[dict[str, Any]] = []
    source_rows_observed = 0

    for ann_date in requested:
        result = query(
            "fund_portfolio",
            ann_date=ann_date,
            fields=_FIELDS,
            _return_empty=True,
            _retries=0,
        )
        if result is None:
            unavailable.append(ann_date)
            continue
        successful.append(ann_date)
        if result.empty:
            empty.append(ann_date)
            continue
        source_rows_observed += len(result)
        normalized, excluded = _normalize_frame(
            result,
            queried_ann_date=ann_date,
            observed_at=observed_at,
        )
        identity_exclusions.extend(excluded)
        if not normalized.empty:
            frames.append(normalized)

    observed_rows = sum(len(frame) for frame in frames)
    existing = _read_existing()
    before_versions = len(existing)
    combined = pd.concat([existing, *frames], ignore_index=True) if frames else existing
    merged = _with_lineage(combined)
    new_versions = max(len(merged) - before_versions, 0)

    if frames:
        _atomic_parquet(merged, _out_path())

    if unavailable and not successful:
        window_state = "source_unavailable"
    elif unavailable:
        window_state = "partial_request_window"
    elif identity_exclusions:
        window_state = "observed_with_identity_exclusions"
    else:
        window_state = "observed_request_window"

    exclusion_reasons: dict[str, int] = {}
    exclusions_by_ann_date: dict[str, int] = {}
    for row in identity_exclusions:
        reason = str(row.get("reason") or "unknown")
        ann_date = str(row.get("queried_ann_date") or "")
        exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1
        if ann_date:
            exclusions_by_ann_date[ann_date] = exclusions_by_ann_date.get(ann_date, 0) + 1

    if source_rows_observed == 0:
        identity_state = "NO_SOURCE_ROWS"
    elif not identity_exclusions:
        identity_state = "ALL_SOURCE_ROWS_CANONICAL_A_SHARE"
    elif observed_rows == 0:
        identity_state = "ALL_SOURCE_ROWS_IDENTITY_EXCLUDED"
    else:
        identity_state = "PARTIAL_IDENTITY_EXCLUSIONS"

    health = {
        "schema": "tushare_fund_portfolio.health.v1",
        "endpoint": "fund_portfolio",
        "official_document": _OFFICIAL_DOC,
        "generated_at": observed_at,
        "authority": {
            "tier": "context_input_only",
            "may_rank": False,
            "may_trade": False,
            "may_redistribute_raw": False,
        },
        "request_window": {
            "lookback_calendar_days": max(int(lookback_days), 1),
            "requested_ann_dates": requested,
            "successful_ann_dates": successful,
            "successful_empty_ann_dates": empty,
            "unavailable_ann_dates": unavailable,
            "state": window_state,
        },
        "known_at_contract": {
            "source_known_at": "ann_date",
            "forbidden_as_known_at": "end_date",
            "source_known_at_quality": "vendor_announcement_date_date_only",
            "mastermind_first_seen": "first_collected_at",
        },
        "population_completeness": {
            "state": "UNVERIFIED_ENDPOINT_ROW_CAP",
            "reason": (
                "official doc 121 publishes rate limits but no row cap; "
                "returned rows are not a full-population completeness receipt"
            ),
        },
        "identity_accounting": {
            "state": identity_state,
            "source_rows_observed": source_rows_observed,
            "accepted_a_share_rows": observed_rows,
            "excluded_identity_rows": len(identity_exclusions),
            "excluded_reasons": exclusion_reasons,
            "excluded_by_ann_date": exclusions_by_ann_date,
            "excluded_source_symbols_sample": [
                str(row.get("source_symbol") or "")
                for row in identity_exclusions[:8]
            ],
            "identity_owner": "collectors.china_tushare_spine.canonical_identity",
        },
        "source_rows_observed_this_run": source_rows_observed,
        "rows_observed_this_run": observed_rows,
        "new_distinct_versions": new_versions,
        "stored_distinct_versions": len(merged),
    }
    _atomic_json(health, _health_path())

    if unavailable and not successful:
        raise RuntimeError(
            "fund_portfolio unavailable for every requested ann_date; "
            "endpoint access/tier/transport state remains unverified"
        )

    log.info(
        "tushare fund_portfolio: observed=%d new_versions=%d success_dates=%d "
        "empty_dates=%d unavailable_dates=%d",
        observed_rows,
        new_versions,
        len(successful),
        len(empty),
        len(unavailable),
    )
    return observed_rows


def main() -> int:
    return 0 if refresh() >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
