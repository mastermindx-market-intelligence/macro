"""Native source editions from the synthetic Industrials fixtures.

``extract_case_cells`` returns fixture cells in their operand shape.
``edition_documents`` builds ``SourceDocument`` values the current
constructor accepts. Edition selection and dossier comparison are not
defined here.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
import re
from typing import Any

from engine.company_intelligence.contracts import canonical_json_sha256
from engine.company_intelligence.documents import (
    RIGHTS_STATES,
    DocumentRevisionChain,
    SourceDocument,
)


_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$", flags=re.ASCII)
_INSTANT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$",
    flags=re.ASCII,
)

# Fixture ``mode`` → constructor pairs that already exist. A filing is not
# rewritten into ``release_amendment``: enrichment is not a correction.
_MODE_BINDING: dict[str, tuple[str, str]] = {
    "release": ("release", "issuer_release"),
    "filing": ("filing", "primary_filing"),
}


@dataclass(frozen=True, slots=True)
class _EditionSpec:
    document_id: str
    kind: str
    source_class: str
    content_sha256: str
    published_at: datetime | None
    available_at: datetime | None
    rights_state: str
    order: tuple[str, str]


def _require_synthetic(case: Mapping[str, Any]) -> None:
    if not isinstance(case, Mapping) or case.get("synthetic") is not True:
        raise ValueError("edition input must be a synthetic case")
    sources = case.get("sources") or []
    if not isinstance(sources, list):
        raise TypeError("sources must be a list")
    for source in sources:
        if not isinstance(source, Mapping):
            raise TypeError("source must be a mapping")
        url = str(source.get("url") or "")
        if not url.startswith("https://example.invalid/"):
            raise ValueError("synthetic source URL must use example.invalid")


def _aware_instant(value: object) -> datetime | None:
    """Timezone-aware UTC instant, or None.

    A ``date`` or a ``YYYY-MM-DD`` string is not midnight. This function
    does not call ``documents._utc``.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return None
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return None
    text = str(value).strip()
    if text == "" or _DATE_ONLY_RE.fullmatch(text):
        return None
    if not _INSTANT_RE.fullmatch(text):
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return None
    return parsed.astimezone(timezone.utc)


def extract_case_cells(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the case cells without minting a cell type.

    ``denominator`` stays on ``business_dimensions``. Equal ``value`` text
    does not merge two selectors.
    """
    _require_synthetic(case)
    raw_cells = case.get("cells") or []
    if not isinstance(raw_cells, list):
        raise TypeError("cells must be a list")
    cells: list[dict[str, Any]] = []
    for cell in raw_cells:
        if not isinstance(cell, Mapping):
            raise TypeError("cell must be a mapping")
        cells.append(deepcopy(dict(cell)))
    return cells


def _sources_by_id(case: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    by_id: dict[str, Mapping[str, Any]] = {}
    for source in case.get("sources") or []:
        source_id = str(source.get("source_id") or "").strip()
        if not source_id or source_id in by_id:
            raise ValueError("each source needs a unique source_id")
        by_id[source_id] = source
    return by_id


def _rights_state(source: Mapping[str, Any]) -> str:
    state = source.get("rights_state")
    if isinstance(state, str) and state in RIGHTS_STATES:
        return state
    return "unknown"


def _content_sha256(document: Mapping[str, Any], source: Mapping[str, Any]) -> str:
    if "recorded_at" in document:
        recorded_at = document.get("recorded_at")
    else:
        recorded_at = source.get("recorded_at")
    return canonical_json_sha256(
        {
            "document_ref": str(document.get("document_ref") or ""),
            "mode": str(source.get("mode") or ""),
            "outcome": document.get("outcome"),
            "recorded_at": recorded_at,
            "source_at": document.get("source_at"),
            "source_id": str(document.get("source_id") or ""),
            "url": str(source.get("url") or ""),
        }
    )


def _event_id(case: Mapping[str, Any], document_ids: list[str]) -> str:
    issuer = case.get("issuer")
    company_id = ""
    if isinstance(issuer, Mapping):
        company_id = str(issuer.get("company_id") or "").strip()
    if not company_id:
        raise ValueError("issuer.company_id is required")
    digest = canonical_json_sha256(
        {"company_id": company_id, "document_ids": document_ids}
    )
    return f"synthetic:event:{digest[:40]}"


def _spec(document: Mapping[str, Any], source: Mapping[str, Any]) -> _EditionSpec:
    document_id = str(document.get("document_ref") or "").strip()
    if not document_id:
        raise ValueError("document_ref is required")
    mode = str(source.get("mode") or "")
    binding = _MODE_BINDING.get(mode)
    if binding is None:
        raise ValueError(f"unsupported source mode: {mode!r}")
    kind, source_class = binding
    published_at = _aware_instant(document.get("source_at"))
    if "recorded_at" in document:
        recorded_raw = document.get("recorded_at")
    else:
        recorded_raw = source.get("recorded_at")
    available_at = _aware_instant(recorded_raw)
    instant = published_at if published_at is not None else available_at
    return _EditionSpec(
        document_id=document_id,
        kind=kind,
        source_class=source_class,
        content_sha256=_content_sha256(document, source),
        published_at=published_at,
        available_at=available_at,
        rights_state=_rights_state(source),
        order=("" if instant is None else instant.isoformat(), document_id),
    )


def edition_documents(case: Mapping[str, Any]) -> tuple[SourceDocument, ...]:
    """One ``SourceDocument`` per fixture document, oldest revision first.

    Every document in the case shares one ``event_id``. ``published_at``
    comes only from a timezone-aware ``source_at``. A recorded clock is
    ``available_at``, and a date-only value is left unknown.
    """
    _require_synthetic(case)
    raw_documents = case.get("documents") or []
    if not isinstance(raw_documents, list):
        raise TypeError("documents must be a list")
    if not raw_documents:
        return ()
    sources = _sources_by_id(case)
    specs: list[_EditionSpec] = []
    for document in raw_documents:
        if not isinstance(document, Mapping):
            raise TypeError("document must be a mapping")
        source_id = str(document.get("source_id") or "").strip()
        source = sources.get(source_id)
        if source is None:
            raise ValueError(f"{document.get('document_ref')!s} names no source")
        specs.append(_spec(document, source))
    specs.sort(key=lambda item: item.order)
    document_ids = [item.document_id for item in specs]
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("document_ref values must be unique")
    event_id = _event_id(case, sorted(document_ids))
    built: list[SourceDocument] = []
    for index, spec in enumerate(specs):
        previous_id = specs[index - 1].document_id if index else None
        next_id = specs[index + 1].document_id if index + 1 < len(specs) else None
        built.append(
            SourceDocument(
                document_id=spec.document_id,
                event_id=event_id,
                document_kind=spec.kind,
                source_class=spec.source_class,
                content_sha256=spec.content_sha256,
                revision=index + 1,
                published_at=spec.published_at,
                available_at=spec.available_at,
                fetched_at=None,
                supersedes_document_id=previous_id,
                superseded_by_document_id=next_id,
                rights_state=spec.rights_state,
                holds_bytes=False,
            )
        )
    return tuple(built)


def edition_chain(case: Mapping[str, Any]) -> DocumentRevisionChain:
    """Contiguous revisions of :func:`edition_documents` for one event."""
    documents = edition_documents(case)
    if not documents:
        raise ValueError("edition chain needs at least one document")
    return DocumentRevisionChain(revisions=documents)
