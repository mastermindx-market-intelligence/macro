"""business_model classification axis — house-curated archetype groups.

Lane L08 of WS:GMI-THEME-GRAPH Taxonomy V2. A pure, read-only display-tier
reader over the ``archetype_groups`` section of the incumbent Nasdaq basket
membership file (``data/baskets_nasdaq/membership.json``). It writes nothing,
caches nothing, calls nothing on the network, and takes no clock but
``as_of``. Gate #2: internal-only vendor sources are never subjects or
inputs here. Gate #8: no producer, no
selection store, no rights resolver — the incumbent file stays the only
owner of archetype-group truth.
"""
from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

from engine.classification_axes import cell

AXIS = "business_model"
SOURCE_OWNER = "data/baskets_nasdaq/membership.json (house-curated archetype_groups)"
SOURCE_ARTIFACT = "data/baskets_nasdaq/membership.json"
MAX_AGE_DAYS = 7
SUBJECT_KINDS = ("co",)
RIGHTS_CONTEXT = None

_SOURCE: dict = {
    "owner": SOURCE_OWNER,
    "artifact": SOURCE_ARTIFACT,
    "field": "archetype_groups",
}
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_iso_date(text: object) -> datetime.date | None:
    """Parse the leading ``YYYY-MM-DD`` of a string, else None."""
    if not isinstance(text, str):
        return None
    head = text[:10]
    if not _DATE_RE.fullmatch(head):
        return None
    try:
        return datetime.date.fromisoformat(head)
    except ValueError:
        return None


def _refuse(
    subject_id: str,
    as_of: str,
    *,
    status: str,
    reason_code: str,
    provenance: list[str] | None = None,
) -> dict:
    return cell.missing(
        axis=AXIS,
        subject_id=subject_id,
        status=status,
        reason_code=reason_code,
        as_of=as_of,
        source=dict(_SOURCE),
        provenance=tuple(provenance or ()),
    )


def _degraded(subject_id: str, as_of: str, note: str) -> dict:
    return _refuse(
        subject_id, as_of, status="unavailable", reason_code="owner_degraded",
        provenance=[note],
    )


def _member_tickers(members: object) -> set[str]:
    """Tickers from a members list of dicts with ``ticker`` or bare strings."""
    found: set[str] = set()
    if not isinstance(members, (list, tuple)):
        return found
    for entry in members:
        ticker = entry.get("ticker") if isinstance(entry, dict) else entry
        if isinstance(ticker, str) and ticker:
            found.add(ticker)
    return found


def _section_tickers(sections: object) -> set[str]:
    found: set[str] = set()
    if not isinstance(sections, dict):
        return found
    for section in sections.values():
        if isinstance(section, dict):
            found |= _member_tickers(section.get("members"))
    return found


def _group_rows(groups: dict, symbol: str) -> list[dict]:
    """The groups containing ``symbol``, sorted by group_id. Labels only —
    never ``rationale`` and never the member lists."""
    rows: list[dict] = []
    for group_id, group in groups.items():
        if not isinstance(group, dict):
            continue
        members = group.get("members")
        if not isinstance(members, (list, tuple)) or symbol not in members:
            continue
        rows.append({
            "group_id": group_id,
            "label_en": group.get("label_en"),
            "label_zh": group.get("label_zh"),
        })
    rows.sort(key=lambda row: row["group_id"])
    return rows


def read_business_model(
    subject_id: str,
    *,
    as_of: str,
    root: str | Path | None = None,
    membership: dict | None = None,
) -> dict:
    """Which house-curated archetype groups is this US company in, as of ``as_of``?

    ``membership`` is an optional injected document (the parsed file); when
    omitted the default path is read fresh under ``root`` (default repo root)
    on every call. Returns one AxisCell; a missing reading is a typed null
    with a reason, never a zero and never a guess.
    """
    kind, _rest = cell.parse_subject(subject_id)
    if kind not in SUBJECT_KINDS:
        return _refuse(
            subject_id, as_of, status="not_applicable", reason_code="not_applicable",
        )
    market, symbol, epoch = cell.company_parts(subject_id)
    if market != "us":
        return _refuse(
            subject_id, as_of, status="not_applicable", reason_code="not_applicable",
        )
    if epoch is not None:
        return _refuse(
            subject_id, as_of, status="unknown", reason_code="value_missing",
            provenance=["identity_epoch_not_supported"],
        )

    doc: object = membership
    if doc is None:
        base = Path(root) if root is not None else _REPO_ROOT
        path = base / SOURCE_ARTIFACT
        if not path.is_file():
            return _refuse(
                subject_id, as_of, status="unavailable", reason_code="owner_missing",
            )
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return _degraded(subject_id, as_of, f"read_error:{type(exc).__name__}")

    if not isinstance(doc, dict):
        return _degraded(subject_id, as_of, "archetype_groups_missing")
    archetypes = doc.get("archetype_groups")
    groups_map = archetypes.get("groups") if isinstance(archetypes, dict) else None
    if not isinstance(groups_map, dict):
        return _degraded(subject_id, as_of, "archetype_groups_missing")

    observed = _parse_iso_date(doc.get("as_of"))
    if observed is None:
        return _degraded(subject_id, as_of, "asof_unparseable")
    as_of_date = _parse_iso_date(as_of)
    if as_of_date is not None and observed > as_of_date:
        # The document speaks from after the caller's point in time: no
        # history is carried, so the reading is refused, not back-dated.
        return _refuse(
            subject_id, as_of, status="unknown", reason_code="history_not_supported",
        )

    universe = _section_tickers(doc.get("subsectors"))
    universe |= _section_tickers(doc.get("amalgamations"))
    for group in groups_map.values():
        if isinstance(group, dict):
            universe |= _member_tickers(group.get("members"))
    if symbol not in universe:
        return _refuse(
            subject_id, as_of, status="unknown", reason_code="value_missing",
        )

    rows = _group_rows(groups_map, symbol)
    value = {"groups": rows}
    labels = ["house_curated"] if rows else ["NO_MAPPING", "house_curated"]
    age_days = (as_of_date - observed).days if as_of_date is not None else 0
    freshness = {"age_days": age_days, "max_age_days": MAX_AGE_DAYS}
    if age_days > MAX_AGE_DAYS:
        return cell.missing(
            axis=AXIS,
            subject_id=subject_id,
            status="stale",
            reason_code="owner_stale",
            as_of=as_of,
            source=dict(_SOURCE),
            value=value,
            unit=None,
            observed_at=observed.isoformat(),
            freshness=freshness,
            labels=labels,
        )
    return cell.available(
        axis=AXIS,
        subject_id=subject_id,
        value=value,
        as_of=as_of,
        source=dict(_SOURCE),
        unit=None,
        observed_at=observed.isoformat(),
        freshness=freshness,
        labels=labels,
    )
