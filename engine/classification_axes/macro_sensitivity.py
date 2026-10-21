"""macro_sensitivity classification axis — the per-stock rate/inflation read.

A pure, read-only AxisCell v1 reader that answers "how is this US stock
classified for rate/inflation sensitivity, as of date D?" by passing through
the per-stock payload that ``engine/stock_macro_sensitivity.py`` computes and
``scripts/build_stock_library.py`` writes into ``site/stockdata/<safe>.json``
(top-level ``asof`` date; key ``macro_sensitivity``).

This is a pass-through, not a second classifier: no new computation, no
aggregation across stocks, no new shock/regime read (the incumbent's own
discipline — display-only, never scored — is inherited unchanged). The cell
sizes nothing and gates nothing.

Gate #2: vendor-local theme inputs never enter here — the only subject kinds
are house ``co:`` ids. Gate #8: this module writes nothing, owns no state,
and resolves no rights; the default file path is read fresh on every call,
and ``as_of`` is the only clock.
"""
from __future__ import annotations

import datetime
import json
import math
import re
from pathlib import Path

from engine.classification_axes import cell

AXIS = "macro_sensitivity"
SOURCE_OWNER = "engine/stock_macro_sensitivity.py"
SOURCE_ARTIFACT = "site/stockdata/<symbol>.json"
MAX_AGE_DAYS = 7
SUBJECT_KINDS = ("co",)
RIGHTS_CONTEXT = None
VALUE_KEYS = (
    "rate_beta",
    "rate_beta_se",
    "t_stat",
    "tier",
    "tier_label",
    "duration",
    "duration_label",
    "duration_src",
    "name_diverges",
    "sector_etf",
    "sector_beta",
    "regime",
    "regime_label",
    "inflation",
    "inflation_label",
    "calibrated",
    "persist",
    "caveat",
)

_DATE_HEAD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _source() -> dict:
    return {
        "owner": SOURCE_OWNER,
        "artifact": SOURCE_ARTIFACT,
        "field": "macro_sensitivity",
    }


def _no_cell(
    subject_id: str,
    as_of: str,
    status: str,
    reason_code: str,
    *,
    provenance: tuple = (),
) -> dict:
    return cell.missing(
        axis=AXIS,
        subject_id=subject_id,
        status=status,
        reason_code=reason_code,
        as_of=as_of,
        source=_source(),
        provenance=provenance,
    )


def _finite(value: object) -> object:
    """Replace every non-finite float (NaN/inf, at any depth) with None."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _finite(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite(child) for child in value]
    return value


def _observed_date(doc: dict) -> datetime.date | None:
    """The document's ``asof`` date, or None when missing/unparseable."""
    raw = doc.get("asof")
    if not isinstance(raw, str):
        return None
    head = raw[:10]
    if not _DATE_HEAD_RE.fullmatch(head):
        return None
    try:
        return datetime.date.fromisoformat(head)
    except ValueError:
        return None


def _read_default_doc(symbol: str, root: object):
    """Read ``site/stockdata/<safe>.json`` fresh under ``root``.

    Returns ``(doc, None)`` or ``(None, (status, reason_code, provenance))``
    per the default-path failure ladder: directory absent → owner_missing,
    file absent → value_missing, unreadable → owner_degraded.
    """
    safe = symbol.replace("=", "_").replace("^", "_")
    directory = Path(root or _REPO_ROOT) / "site" / "stockdata"
    path = directory / f"{safe}.json"
    if not directory.is_dir():
        return None, ("unavailable", "owner_missing", ("stockdata_dir_missing",))
    if not path.is_file():
        return None, ("unknown", "value_missing", ("stock_file_missing",))
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, (
            "unavailable",
            "owner_degraded",
            (f"read_error:{type(exc).__name__}",),
        )
    return doc, None


def read_macro_sensitivity(
    subject_id, *, as_of: str, root=None, stock_doc=None
) -> dict:
    """The macro-sensitivity AxisCell for one ``co:`` subject, as of ``as_of``.

    ``stock_doc`` injects the whole stock JSON document (tests); when it is
    None the default artifact ``site/stockdata/<safe>.json`` is read fresh
    under ``root`` (default: the repo root). Pure: reads nothing else, writes
    nothing, never reaches the network, and derives every date from ``as_of``.
    """
    kind, _rest = cell.parse_subject(subject_id)
    if not isinstance(as_of, str) or not _DATE_HEAD_RE.fullmatch(as_of):
        raise cell.AxisCellError(f"as_of must be YYYY-MM-DD, got {as_of!r}")
    try:
        as_of_date = datetime.date.fromisoformat(as_of)
    except ValueError:
        raise cell.AxisCellError(f"as_of must be YYYY-MM-DD, got {as_of!r}") from None
    if kind not in SUBJECT_KINDS:
        return _no_cell(subject_id, as_of, "not_applicable", "not_applicable")
    market, symbol, epoch = cell.company_parts(subject_id)
    if market != "us":
        return _no_cell(
            subject_id,
            as_of,
            "not_applicable",
            "not_applicable",
            provenance=(f"market:{market}",),
        )
    if epoch is not None:
        return _no_cell(
            subject_id,
            as_of,
            "unknown",
            "value_missing",
            provenance=("identity_epoch_not_supported",),
        )

    if stock_doc is not None:
        doc = stock_doc
    else:
        doc, failure = _read_default_doc(symbol, root)
        if failure is not None:
            status, reason, provenance = failure
            return _no_cell(subject_id, as_of, status, reason, provenance=provenance)

    if not isinstance(doc, dict):
        return _no_cell(
            subject_id,
            as_of,
            "unavailable",
            "owner_degraded",
            provenance=("document_not_object",),
        )
    payload = doc.get("macro_sensitivity")
    if not isinstance(payload, dict) or not payload:
        return _no_cell(
            subject_id,
            as_of,
            "unknown",
            "value_missing",
            provenance=("macro_sensitivity_missing",),
        )
    observed = _observed_date(doc)
    if observed is None:
        return _no_cell(
            subject_id,
            as_of,
            "unavailable",
            "owner_degraded",
            provenance=("asof_unparseable",),
        )
    if observed > as_of_date:
        return _no_cell(
            subject_id,
            as_of,
            "unknown",
            "history_not_supported",
            provenance=("observed_after_as_of",),
        )

    value = _finite({key: payload[key] for key in VALUE_KEYS if key in payload})
    if not value:
        return _no_cell(
            subject_id,
            as_of,
            "unknown",
            "value_missing",
            provenance=("macro_sensitivity_empty",),
        )

    age_days = (as_of_date - observed).days
    freshness = {"age_days": age_days, "max_age_days": MAX_AGE_DAYS}
    observed_at = observed.isoformat()
    try:
        if age_days > MAX_AGE_DAYS:
            return cell.missing(
                axis=AXIS,
                subject_id=subject_id,
                status="stale",
                reason_code="owner_stale",
                as_of=as_of,
                source=_source(),
                value=value,
                freshness=freshness,
                observed_at=observed_at,
                labels=("source_local",),
            )
        return cell.available(
            axis=AXIS,
            subject_id=subject_id,
            value=value,
            as_of=as_of,
            source=_source(),
            observed_at=observed_at,
            freshness=freshness,
            labels=("source_local",),
        )
    except cell.AxisCellError:
        return _no_cell(
            subject_id,
            as_of,
            "unavailable",
            "owner_degraded",
            provenance=("invalid_record",),
        )
