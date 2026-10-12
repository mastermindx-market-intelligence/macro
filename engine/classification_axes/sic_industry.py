"""sic_industry classification-axis reader (WS:GMI-THEME-GRAPH Taxonomy V2, lane L05).

Answers "what SEC SIC industry is this US company filed under, as of date
D?" by wrapping the profile artifact written by collectors/equity_profile.py
(``data/profile/profiles.parquet``, column ``sic_description``). SIC is the
SEC industry code text, not a GICS sub-industry.

Pure and read-only: one AxisCell per call, no producer, no cache, no
network, no LLM. ``as_of`` is the only clock. Invalid subject ids are
caller errors and raise; every other outcome is a typed-null cell.
"""
from __future__ import annotations

import datetime
import re
from pathlib import Path

import pandas as pd

from engine.classification_axes import cell

AXIS = "sic_industry"
SOURCE_OWNER = "collectors/equity_profile.py"
SOURCE_ARTIFACT = "data/profile/profiles.parquet"
SOURCE_FIELD = "sic_description"
MAX_AGE_DAYS = 365
SUBJECT_KINDS = ("co",)
RIGHTS_CONTEXT = {
    "license_class": "direct_display_ok",
    "basis": (
        "SEC EDGAR submissions sicDescription (US government public-domain "
        "content) via collectors/equity_profile.py; keyless_public"
    ),
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _source() -> dict:
    return {"owner": SOURCE_OWNER, "artifact": SOURCE_ARTIFACT, "field": SOURCE_FIELD}


def _cell_missing(
    subject_id: str,
    as_of: str,
    status: str,
    reason_code: str,
    provenance: list[str],
) -> dict:
    return cell.missing(
        axis=AXIS,
        subject_id=subject_id,
        status=status,
        reason_code=reason_code,
        as_of=as_of,
        source=_source(),
        provenance=provenance,
        rights_context=RIGHTS_CONTEXT,
    )


def _alias(symbol: str) -> str | None:
    """The ``.``/``-`` swapped ticker (BRK.B <-> BRK-B), or None when pure."""
    if "." in symbol:
        return symbol.replace(".", "-")
    if "-" in symbol:
        return symbol.replace("-", ".")
    return None


def _row_for(frame: pd.DataFrame, symbol: str) -> tuple[pd.Series | None, list[str]]:
    """The profile row for ``symbol`` (exact first, then the alias), or None.

    Keyed by the ``ticker`` column when present, else the index. The last
    occurrence wins so a duplicated key still answers deterministically.
    """
    keys = frame["ticker"] if "ticker" in frame.columns else frame.index
    alias = _alias(symbol)
    attempts: list[tuple[str, list[str]]] = [(symbol, [])]
    if alias is not None:
        attempts.append((alias, [f"symbol_alias:{alias}"]))
    for key, provenance in attempts:
        matches = frame[keys == key]
        if len(matches):
            return matches.iloc[-1], provenance
    return None, attempts[-1][1]


def _observed_text(row: pd.Series) -> str | None:
    """The row's ``as_of`` as YYYY-MM-DD, or None when absent/unparseable."""
    text = str(row.get("as_of"))[:10]
    if _DATE_RE.fullmatch(text) is None:
        return None
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return None
    return text


def _sic_text(row: pd.Series) -> str | None:
    """The stripped ``sic_description``, or None when null/NaN/blank."""
    raw = row.get("sic_description")
    if raw is None or (isinstance(raw, float) and raw != raw):
        return None
    text = str(raw).strip()
    return text or None


def read_sic_industry(
    subject_id: str,
    *,
    as_of: str,
    root: str | Path | None = None,
    profiles: pd.DataFrame | None = None,
) -> dict:
    """Return the SEC SIC industry reading for a US company as one AxisCell.

    ``profiles`` injects the ticker-keyed profile table (index, or a
    ``ticker`` column); when it is None the reader opens SOURCE_ARTIFACT
    under ``root`` (default: the repo root) with ``pandas.read_parquet`` on
    every call and caches nothing.
    """
    kind, _ = cell.parse_subject(subject_id)
    if kind not in SUBJECT_KINDS:
        return _cell_missing(subject_id, as_of, "not_applicable", "not_applicable", [])
    market, symbol, epoch = cell.company_parts(subject_id)
    if market != "us":
        return _cell_missing(
            subject_id, as_of, "not_applicable", "not_applicable", [f"market:{market}"]
        )
    if epoch is not None:
        return _cell_missing(
            subject_id, as_of, "unknown", "value_missing", ["identity_epoch_not_supported"]
        )
    as_of_date = datetime.date.fromisoformat(as_of)

    if profiles is None:
        path = (Path(root) if root is not None else _REPO_ROOT) / SOURCE_ARTIFACT
        if not path.exists():
            return _cell_missing(subject_id, as_of, "unavailable", "owner_missing", [])
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001 — a corrupt artifact is a typed null
            return _cell_missing(
                subject_id,
                as_of,
                "unavailable",
                "owner_degraded",
                [f"read_error:{type(exc).__name__}"],
            )
    else:
        frame = profiles

    missing_columns = [
        name for name in (SOURCE_FIELD, "as_of") if name not in getattr(frame, "columns", [])
    ]
    if missing_columns:
        return _cell_missing(
            subject_id,
            as_of,
            "unavailable",
            "owner_degraded",
            [f"missing_column:{name}" for name in missing_columns],
        )

    row, provenance = _row_for(frame, symbol)
    if row is None:
        return _cell_missing(subject_id, as_of, "unknown", "value_missing", provenance)

    observed = _observed_text(row)
    if observed is None:
        return _cell_missing(
            subject_id,
            as_of,
            "unavailable",
            "owner_degraded",
            provenance + ["row_as_of_unparseable"],
        )
    observed_date = datetime.date.fromisoformat(observed)
    if observed_date > as_of_date:
        return _cell_missing(
            subject_id, as_of, "unknown", "history_not_supported", provenance
        )

    text = _sic_text(row)
    if text is None:
        return _cell_missing(subject_id, as_of, "unknown", "value_missing", provenance)

    freshness = {
        "age_days": (as_of_date - observed_date).days,
        "max_age_days": MAX_AGE_DAYS,
    }
    if freshness["age_days"] > MAX_AGE_DAYS:
        return cell.missing(
            axis=AXIS,
            subject_id=subject_id,
            status="stale",
            reason_code="owner_stale",
            as_of=as_of,
            source=_source(),
            value={"sic_description": text},
            observed_at=observed,
            freshness=freshness,
            labels=("source_local",),
            provenance=provenance,
            rights_context=RIGHTS_CONTEXT,
        )
    return cell.available(
        axis=AXIS,
        subject_id=subject_id,
        value={"sic_description": text},
        as_of=as_of,
        source=_source(),
        observed_at=observed,
        freshness=freshness,
        labels=("source_local",),
        provenance=provenance,
        rights_context=RIGHTS_CONTEXT,
    )
