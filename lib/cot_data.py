"""Pure CFTC row validation, revision metadata and bounded source evidence.

Uses the existing cot store. Immutable raw responses preserve observed versions;
latest Parquet is a projection, never evidence of original release-time vintages.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from lib.cot_contracts import BY_CODE, COHORT_FIELDS, DATASETS, source_fields
from lib.cot_publication import NY, scheduled_release, utc_timestamp


class CotDataError(ValueError):
    """Invalid source row: preserve last good data, never invent a zero."""


def _integer(value: object, field: str) -> int:
    if value is None or isinstance(value, bool):
        raise CotDataError(f"missing/invalid {field}")
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number != number.to_integral_value() or number < 0:
            raise CotDataError(f"invalid {field}")
        return int(number)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CotDataError(f"invalid {field}") from exc


def normalize_row(raw: dict, family: str, *, observed_at: object) -> dict:
    observed = utc_timestamp(observed_at)
    if pd.isna(observed) or family not in DATASETS:
        raise CotDataError("explicit observed instant and known family required")
    code = raw.get("cftc_contract_market_code")
    if code not in BY_CODE:
        raise CotDataError("unknown exact CFTC contract")
    market = BY_CODE[code]
    if family != "legacy" and family != market.detail_family:
        raise CotDataError("report family does not cover this market")
    try:
        asof = pd.Timestamp(raw.get("report_date_as_yyyy_mm_dd"))
    except (TypeError, ValueError) as exc:
        raise CotDataError("invalid report date") from exc
    if pd.isna(asof) or asof.tzinfo is not None or asof != asof.normalize():
        raise CotDataError("report date must be a date, not an instant")
    if asof.date() > observed.tz_convert(NY).date():
        raise CotDataError("report date is in the future")
    name = raw.get("market_and_exchange_names")
    if not isinstance(name, str) or not name.strip():
        raise CotDataError("market/exchange identity absent")
    oi = _integer(raw.get("open_interest_all"), "open interest")
    if oi == 0:
        raise CotDataError("zero open interest cannot be normalized")
    row = {
        "report_asof_date": asof.date().isoformat(), "market_id": market.key,
        "cftc_contract_market_code": code, "market_and_exchange_names": name,
        "report_family": family, "contract_basis": "futures_only",
        "open_interest": oi,
    }
    total_long = total_short = 0
    for cohort, (long_f, short_f, spread_f) in COHORT_FIELDS[family].items():
        long = _integer(raw.get(long_f), long_f)
        short = _integer(raw.get(short_f), short_f)
        spread = _integer(raw.get(spread_f), spread_f) if spread_f else 0
        if max(long + spread, short + spread) > oi:
            raise CotDataError(f"{cohort} exceeds open interest")
        total_long += long + spread
        total_short += short + spread
        row.update({f"{cohort}_long": long, f"{cohort}_short": short,
                    f"{cohort}_spread": spread, f"{cohort}_net": long - short,
                    f"{cohort}_net_pct_oi": 100.0 * (long - short) / oi})
    if total_long != oi or total_short != oi:
        raise CotDataError("cohort totals do not reconcile to open interest")
    if family == "legacy":
        row["net_spec"] = row["noncommercial_net"]
        row["net_spec_pct_oi"] = row["noncommercial_net_pct_oi"]
    # Fingerprint only source-derived fields, not clocks or presentation fields.
    digest = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    row.update(source_record_sha256=digest, source_dataset=DATASETS[family],
               source_url=f"https://publicreporting.cftc.gov/resource/{DATASETS[family]}.json",
               first_observed_at=observed.isoformat(), version_observed_at=observed.isoformat(),
               revised_at=None, scheduled_release_at=scheduled_release(asof).isoformat(),
               actual_release_at=None, availability_basis="observed_source_version",
               original_vintage_certified=False)
    return row


def normalize_frame(raw_rows: list[dict], family: str, *, code: str,
                    observed_at: object, previous: pd.DataFrame | None = None) -> pd.DataFrame:
    if not raw_rows:
        raise CotDataError("empty source response")
    rows = []
    dates = set()
    for raw in raw_rows:
        if raw.get("cftc_contract_market_code") != code:
            raise CotDataError("mixed contracts cannot be one market history")
        row = normalize_row(raw, family, observed_at=observed_at)
        date = pd.Timestamp(row["report_asof_date"])
        if date in dates:
            raise CotDataError("duplicate report identity")
        dates.add(date)
        if previous is not None and date in previous.index:
            old = previous.loc[date]
            if isinstance(old, pd.DataFrame):
                raise CotDataError("duplicate stored report identity")
            if old.get("cftc_contract_market_code") != code or old.get("report_family") != family:
                raise CotDataError("stored contract/family changed")
            old_seen = utc_timestamp(old.get("first_observed_at"))
            if not pd.isna(old_seen):
                row["first_observed_at"] = old_seen.isoformat()
            if old.get("source_record_sha256") == row["source_record_sha256"]:
                for key in ("version_observed_at", "revised_at"):
                    value = utc_timestamp(old.get(key))
                    row[key] = value.isoformat() if not pd.isna(value) else None
                if not row["version_observed_at"]:
                    row["version_observed_at"] = utc_timestamp(observed_at).isoformat()
            else:
                row["revised_at"] = utc_timestamp(observed_at).isoformat()
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame.index = pd.to_datetime(frame["report_asof_date"])
    frame.index.name = "report_asof_date_index"
    return frame.sort_index()


def preserve_source(rows: list[dict], family: str, *, observed_at: object, data_root: Path) -> str:
    """Create one immutable hash-addressed response in the existing cot store.

    Stable payloads reuse their original record; changed records preserve both
    old and new responses. No credentials, hidden source or new queue is added.
    """
    if family not in DATASETS or pd.isna(utc_timestamp(observed_at)):
        raise CotDataError("invalid source evidence identity")
    fields = source_fields(family)
    selected = [{f: row.get(f) for f in fields} for row in rows]
    selected.sort(key=lambda row: (str(row.get("cftc_contract_market_code")), str(row.get("report_date_as_yyyy_mm_dd"))))
    payload = json.dumps(selected, sort_keys=True, separators=(",", ":"), allow_nan=False)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    directory = Path(data_root) / "cot" / "raw" / family
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{digest}.json.gz"
    envelope = json.dumps({"schema": "cot_source_response.v1", "family": family,
        "first_observed_at": utc_timestamp(observed_at).isoformat(),
        "payload_sha256": digest, "records": selected}, separators=(",", ":"))
    try:
        with target.open("xb") as handle:
            handle.write(gzip.compress(envelope.encode(), mtime=0))
    except FileExistsError:
        with gzip.open(target, "rt", encoding="utf-8") as handle:
            stored = json.load(handle)
        actual = hashlib.sha256(json.dumps(stored["records"], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if actual != digest or stored.get("family") != family:
            raise CotDataError("immutable source evidence digest mismatch")
    return digest


def read_legacy_frame(alias: str) -> pd.DataFrame | None:
    """Prefer exact-contract history; old aliases remain explicitly unverified.

    Existing consumers keep their filename/API contract. The oil canonical
    history is NYMEX only, never the older mixed-exchange alias projection.
    """
    from lib import store
    from lib.cot_contracts import BY_KEY, store_name

    market = BY_KEY.get(alias.removeprefix("cot_"))
    if market:
        frame = store.read("cot", store_name(market.code))
        if frame is not None and not frame.empty:
            return frame
    frame = store.read("cot", alias)
    if frame is not None:
        frame.attrs["legacy_contract_identity_unverified"] = True
    return frame
