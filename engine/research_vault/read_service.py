"""Concrete Research Vault read owner implementing ``read_port.py``.

Composes the incumbent catalog, corpus, F5 full-text, and RIO readers under the
gate order in the F10 service spec. This module has no network API: it opens no
sockets, reads no environment, and never talks to R2, HTTP, or an MCP server.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from engine.research_intelligence.store import (
    ResearchIntelligenceInvalid,
    ResearchIntelligenceStoreError,
)
from engine.research_vault import catalog as catalog_mod
from engine.research_vault import corpus as corpus_mod
from engine.research_vault import fulltext
from engine.research_vault import read_port

OPERATIONS = ("status", "search", "fetch", "find_evidence")
_OPERATION_SET = frozenset(OPERATIONS)
_ENTITLEMENTS = frozenset({"anonymous", "preview", "pro"})
_SURFACES = frozenset({"brain", "mcp"})
_SEARCH_FILTER_KEYS = frozenset({"institution", "date_from", "date_to"})
_FETCH_SELECTOR_KEYS = frozenset({"segment_start", "max_segments"})
_HEX = frozenset("0123456789abcdef")

SEARCH_LIMIT_MAX = 50
QUERY_MAX_CHARS = 500
SEGMENT_MAX_BYTES = 4000
FETCH_MAX_SEGMENTS = 4
EVIDENCE_PASSAGE_CAP = corpus_mod.EVIDENCE_PASSAGE_LIMIT
_MAX_TEXT_BYTES = 24_000
_DEFAULT_FETCH_MAX_SEGMENTS = 2


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in _HEX for ch in value)
    )


def _literal_int(value: Any) -> bool:
    return type(value) is int


def _bounded_matched_terms(raw: Any) -> Any:
    """Bound the corpus hit's matched_terms to the port's limits. Truncation only.

    Never invents, reorders or normalizes a term. A non-list/tuple value, or a
    non-str element, is passed through unchanged so the port refuses it."""
    if not isinstance(raw, (list, tuple)):
        return raw
    cap = read_port.EVIDENCE_MATCHED_TERM_MAX_CHARS
    return [t[:cap] if isinstance(t, str) else t for t in raw][: read_port.EVIDENCE_MATCHED_TERMS_MAX]


@dataclass(frozen=True)
class ServerReadContext(Mapping[str, Any]):
    """Trusted server-side caller context. Construction is server-side only."""

    principal_id: str | None
    entitlement: str
    scopes: frozenset[str]
    surface: str

    def __post_init__(self) -> None:
        if self.entitlement not in _ENTITLEMENTS:
            raise ValueError("unknown entitlement")
        if self.surface not in _SURFACES:
            raise ValueError("unknown surface")
        if not isinstance(self.scopes, frozenset):
            raise ValueError("scopes must be a frozenset")
        if any(scope not in _OPERATION_SET for scope in self.scopes):
            raise ValueError("unknown scope")
        if self.entitlement == "anonymous":
            if self.principal_id is not None:
                raise ValueError("anonymous context cannot carry a principal_id")
        else:
            if not isinstance(self.principal_id, str) or not self.principal_id.strip():
                raise ValueError("authenticated context requires a principal_id")
            if len(self.principal_id) > 200:
                raise ValueError("principal_id exceeds bound")

    def _public(self) -> dict[str, Any]:
        return {
            "entitlement": self.entitlement,
            "scopes": tuple(sorted(self.scopes)),
            "surface": self.surface,
            "authenticated": self.entitlement != "anonymous",
        }

    def __getitem__(self, key: str) -> Any:
        return self._public()[key]

    def __iter__(self):
        return iter(self._public())

    def __len__(self) -> int:
        return len(self._public())


def _catalog_items(catalog: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for item in catalog.get("items") or ():
        if not isinstance(item, Mapping):
            continue
        report_id = item.get("id")
        if isinstance(report_id, str) and report_id:
            out[report_id] = item
    return out


def _close_conn(conn: Any) -> None:
    if conn is None:
        return
    closer = getattr(conn, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            return


class ResearchReadService:
    """Concrete ``ResearchReadPort`` over catalog, corpus, F5 text, and RIO."""

    def __init__(
        self,
        *,
        catalog_store: Any,
        corpus_connection: Callable[[], Any],
        preview_selector: Callable[[Mapping[str, Any]], Iterable[str]],
        extracted_text_loader: Callable[[str, Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
        source_digest_reader: Callable[[str], str | None] | None = None,
        rio_reader: Callable[[str], Any] | None = None,
        full_text_inventory: Callable[[], Iterable[str]] | None = None,
        rio_inventory: Callable[[], Iterable[str]] | None = None,
        source_classifier: Callable[..., Mapping[str, Any]] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._catalog_store = catalog_store
        self._corpus_connection = corpus_connection
        self._preview_selector = preview_selector
        self._extracted_text_loader = extracted_text_loader
        self._source_digest_reader = source_digest_reader
        self._rio_reader = rio_reader
        self._full_text_inventory = full_text_inventory
        self._rio_inventory = rio_inventory
        self._source_classifier = source_classifier
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self) -> datetime:
        return self._clock()

    def _classifier(self) -> Callable[..., Mapping[str, Any]]:
        if self._source_classifier is not None:
            return self._source_classifier

        def _evaluate(payload, *, now, source="catalog", **kwargs):
            from scripts.check_research_vault_source_freshness import evaluate
            return evaluate(payload, now=now, source=source, **kwargs)

        return _evaluate

    def _gate_context(self, caller_context: Any, operation: str) -> Mapping[str, Any] | ServerReadContext:
        if not isinstance(caller_context, ServerReadContext):
            return read_port.failure("AUTHENTICATION_REQUIRED")
        if operation not in caller_context.scopes:
            return read_port.failure("INSUFFICIENT_SCOPE")
        return caller_context

    def _read_catalog(self, now: datetime) -> tuple[Mapping[str, Any] | None, Mapping[str, Any]]:
        try:
            document = catalog_mod.read_strict(self._catalog_store, now)
        except catalog_mod.CatalogUnavailable:
            return None, self._source_state(None, now)
        return document, self._source_state(document, now)

    def _source_state(
        self,
        catalog: Mapping[str, Any] | None,
        now: datetime,
        extra: Iterable[str] = (),
    ) -> dict[str, Any]:
        unavailable = read_port.source_state(
            state="CATALOG_UNAVAILABLE",
            catalog_generated_at=None,
            latest_report_published_at=None,
            source_age_hours=None,
            report_count=0,
            known_degradation=(),
        )
        if catalog is None:
            return unavailable
        try:
            report = self._classifier()(catalog, now=now, source="catalog")
            status = report["status"]
            if status not in read_port.SOURCE_STATES:
                return unavailable
        except Exception:
            return unavailable

        degradation: list[str] = []
        if status == "PRODUCER_STALE":
            degradation.append("PRODUCER_STALE")
        try:
            if catalog_mod.health(dict(catalog), now)["state"] == "stale":
                if "PRODUCER_STALE" not in degradation:
                    degradation.append("PRODUCER_STALE")
        except Exception:
            pass
        invalid = report.get("invalid_published_at") or 0
        if isinstance(invalid, int) and invalid > 0:
            degradation.append("METADATA_PARTIAL")
        for code in extra:
            if code in read_port.DEGRADATION_CODES and code not in degradation:
                degradation.append(code)

        age = report.get("age_hours")
        if isinstance(age, bool) or not isinstance(age, (int, float)):
            age = None
        elif age < 0:
            age = 0.0

        latest = report.get("latest_report_at")
        generated = catalog.get("generated_at")
        items = catalog.get("items") or ()
        try:
            return read_port.source_state(
                state=status,
                catalog_generated_at=generated if isinstance(generated, str) else None,
                latest_report_published_at=latest if isinstance(latest, str) else None,
                source_age_hours=age,
                report_count=len(items) if isinstance(items, (list, tuple)) else 0,
                known_degradation=degradation,
            )
        except Exception:
            return unavailable

    def _with_degradation(
        self,
        catalog: Mapping[str, Any] | None,
        now: datetime,
        extra: Iterable[str],
    ) -> dict[str, Any]:
        return self._source_state(catalog, now, extra)

    def _open_corpus(self) -> Any:
        try:
            return self._corpus_connection()
        except Exception:
            return None

    def _corpus_snapshot(
        self,
        conn: Any,
        admitted: set[str],
    ) -> tuple[str, list[str]]:
        if conn is None:
            return "UNAVAILABLE", []
        try:
            found = set(corpus_mod.sha_index(conn).values()) & admitted
        except Exception:
            return "UNAVAILABLE", []
        if len(found) < len(admitted):
            return "PARTIAL", ["PARTIAL_CORPUS"]
        return "AVAILABLE", []

    def _coverage_ratio(
        self,
        inventory: Callable[[], Iterable[str]] | None,
        admitted: set[str],
    ) -> tuple[float, bool]:
        if inventory is None:
            return 0.0, True
        try:
            held = {item for item in inventory() if isinstance(item, str)}
        except Exception:
            return 0.0, True
        if not admitted:
            return 0.0, False
        return len(held & admitted) / len(admitted), False

    def _preview_ids(self, catalog: Mapping[str, Any]) -> set[str]:
        try:
            return {item for item in self._preview_selector(catalog) if isinstance(item, str)}
        except Exception:
            return set()

    def _validate_search(
        self,
        query: Any,
        filters: Any,
        limit: Any,
        cursor: Any,
    ) -> Mapping[str, Any] | tuple[str, dict[str, str], int]:
        if not isinstance(query, str):
            return read_port.failure("INVALID_REQUEST")
        stripped = query.strip()
        if len(stripped) > QUERY_MAX_CHARS:
            return read_port.failure("INVALID_REQUEST")
        if not isinstance(filters, Mapping):
            return read_port.failure("INVALID_REQUEST")
        validated: dict[str, str] = {}
        for key, value in filters.items():
            if key not in _SEARCH_FILTER_KEYS:
                return read_port.failure("INVALID_REQUEST")
            if not isinstance(value, str) or len(value) > 80:
                return read_port.failure("INVALID_REQUEST")
            validated[str(key)] = value
        if not _literal_int(limit) or limit < 1:
            return read_port.failure("INVALID_REQUEST")
        if cursor is not None:
            return read_port.failure("INVALID_REQUEST")
        effective = min(limit, SEARCH_LIMIT_MAX)
        return stripped, validated, effective

    def _validate_report_id(self, report_id: Any) -> Mapping[str, Any] | str:
        if not corpus_mod.valid_doc_id(report_id):
            return read_port.failure("INVALID_REQUEST")
        return report_id

    def _validate_fetch_selectors(self, selectors: Any) -> Mapping[str, Any] | tuple[int, int]:
        if not isinstance(selectors, Mapping):
            return read_port.failure("INVALID_REQUEST")
        for key in selectors:
            if key not in _FETCH_SELECTOR_KEYS:
                return read_port.failure("INVALID_REQUEST")
        segment_start = selectors.get("segment_start", 0)
        max_segments = selectors.get("max_segments", _DEFAULT_FETCH_MAX_SEGMENTS)
        if not _literal_int(segment_start) or segment_start < 0:
            return read_port.failure("INVALID_REQUEST")
        if (
            not _literal_int(max_segments)
            or max_segments < 1
            or max_segments > FETCH_MAX_SEGMENTS
        ):
            return read_port.failure("INVALID_REQUEST")
        return segment_start, max_segments

    def _validate_evidence(
        self,
        query: Any,
        max_passages: Any,
    ) -> Mapping[str, Any] | tuple[str, int]:
        if not isinstance(query, str) or not (1 <= len(query) <= QUERY_MAX_CHARS):
            return read_port.failure("INVALID_REQUEST")
        if not corpus_mod.evidence_query_is_meaningful(query):
            return read_port.failure("INVALID_REQUEST")
        if not _literal_int(max_passages) or max_passages < 1 or max_passages > 12:
            return read_port.failure("INVALID_REQUEST")
        return query, min(max_passages, EVIDENCE_PASSAGE_CAP)

    def _entitle_report(self, ctx: ServerReadContext) -> Mapping[str, Any] | None:
        if ctx.entitlement == "anonymous":
            return read_port.failure("AUTHENTICATION_REQUIRED")
        if ctx.entitlement != "pro":
            return read_port.failure("REPORT_NOT_ENTITLED")
        return None

    def _resolve_text(
        self,
        report_id: str,
        item: Mapping[str, Any],
    ) -> tuple[str, Mapping[str, Any] | None, list[dict[str, Any]] | None, list[str]]:
        extra: list[str] = []
        loader = self._extracted_text_loader
        if loader is None:
            return "EXTRACTION_UNAVAILABLE", None, None, extra
        try:
            extracted = loader(report_id, item)
        except Exception:
            return "EXTRACTION_UNAVAILABLE", None, None, extra
        if extracted is None or not isinstance(extracted, Mapping):
            return "EXTRACTION_UNAVAILABLE", None, None, extra
        if extracted.get("report_id") != report_id:
            return "EXTRACTION_UNAVAILABLE", None, None, extra
        if extracted.get("schema") != fulltext.EXTRACTED_TEXT_SCHEMA:
            return "EXTRACTION_UNAVAILABLE", None, None, extra
        try:
            segments = fulltext.build_segments(
                dict(extracted),
                segmenter_version=fulltext.SEGMENTER_VERSION,
                max_bytes=SEGMENT_MAX_BYTES,
            )
        except ValueError:
            return "EXTRACTION_UNAVAILABLE", None, None, extra

        layer = extracted.get("text_layer_state")
        if layer == "none":
            extra.append("SCAN_NO_TEXT")
            return "NO_TEXT_LAYER", extracted, segments, extra
        if layer == "unavailable":
            return "EXTRACTION_UNAVAILABLE", extracted, segments, extra

        reader = self._source_digest_reader
        if reader is not None:
            try:
                digest = reader(report_id)
            except Exception:
                digest = None
            if _is_sha256(digest) and digest != extracted.get("source_pdf_sha256"):
                return "SOURCE_REVISION_CHANGED", extracted, segments, extra

        if layer == "thin":
            extra.append("FULL_TEXT_PARTIAL")
        return "FULL_TEXT", extracted, segments, extra

    def _rio_state(
        self,
        report_id: str,
        extracted: Mapping[str, Any] | None,
    ) -> tuple[str, Any, list[str]]:
        extra: list[str] = []
        reader = self._rio_reader
        if reader is None:
            return "NOT_REQUESTED", None, extra
        try:
            stored = reader(report_id)
        except ResearchIntelligenceInvalid:
            return "INVALID", None, extra
        except ResearchIntelligenceStoreError:
            extra.append("RIO_PARTIAL")
            return "MISSING", None, extra
        except Exception:
            extra.append("RIO_PARTIAL")
            return "MISSING", None, extra
        if stored is None:
            return "MISSING", None, extra
        extracted_sha = extracted.get("extracted_text_sha256") if extracted is not None else None
        stored_sha = getattr(stored, "source_content_sha256", None)
        if extracted is not None and stored_sha == extracted_sha:
            return "CURRENT", stored, extra
        return "STALE", stored, extra

    def _search_envelope(
        self,
        *,
        available: bool,
        query: str,
        filters: Mapping[str, str],
        limit: int,
        entitlement_view: str,
        source: Mapping[str, Any],
        corpus_state: str,
        coverage_state: str | None,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "schema": read_port.SEARCH_SCHEMA,
            "ok": True,
            "available": available,
            "query": query,
            "filters": dict(filters),
            "limit": limit,
            "entitlement_view": entitlement_view,
            "source": dict(source),
            "corpus_state": corpus_state,
            "coverage_state": coverage_state,
            "candidates": candidates,
            "count": len(candidates),
            "next_cursor": None,
        }

    def _fetch_envelope(
        self,
        *,
        available: bool,
        report_id: str,
        report: dict[str, Any] | None,
        source: Mapping[str, Any],
        coverage_state: str | None,
        text_layer_state: str | None,
        rio_state: str,
        rio_artifact_sha256: str | None,
        segment_count_total: int,
        segments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "schema": read_port.FETCH_SCHEMA,
            "ok": True,
            "available": available,
            "report_id": report_id,
            "report": report,
            "source": dict(source),
            "coverage_state": coverage_state,
            "text_layer_state": text_layer_state,
            "rio_state": rio_state,
            "rio_artifact_sha256": rio_artifact_sha256,
            "segment_count_total": segment_count_total,
            "segments": segments,
        }

    def _report_meta(self, item: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "title": item.get("title") or "",
            "institution": item.get("institution") or "",
            "side": item.get("side") or "",
            "published_at": item.get("published_at") or "",
            "pages": item.get("pages"),
            "language": item.get("language"),
        }

    def _project_segments(
        self,
        segments: list[dict[str, Any]] | None,
        segment_start: int,
        max_segments: int,
    ) -> tuple[int, list[dict[str, Any]]]:
        rows = list(segments or ())
        window = rows[segment_start:segment_start + max_segments]
        projected: list[dict[str, Any]] = []
        total = 0
        for row in window:
            text = row.get("text")
            if not isinstance(text, str):
                continue
            nbytes = len(text.encode("utf-8"))
            if total + nbytes > _MAX_TEXT_BYTES:
                break
            projected.append(
                {
                    "segment_index": row.get("segment_index"),
                    "page_start": row.get("page_start"),
                    "page_end": row.get("page_end"),
                    "start_byte": row.get("start_byte"),
                    "end_byte": row.get("end_byte"),
                    "text": text,
                }
            )
            total += nbytes
        return len(rows), projected

    def _pages_for_span(
        self,
        boundaries: Any,
        start_byte: int,
        end_byte: int,
    ) -> tuple[int | None, int | None]:
        if not isinstance(boundaries, list) or not boundaries:
            return None, None
        touched: list[int] = []
        for boundary in boundaries:
            if not isinstance(boundary, Mapping):
                continue
            b_start = boundary.get("start_byte")
            b_sep = boundary.get("separator_end_byte")
            if not _literal_int(b_start) or not _literal_int(b_sep):
                continue
            if start_byte < b_sep and end_byte > b_start:
                page = boundary.get("page_index", boundary.get("page"))
                if _literal_int(page) and page >= 1:
                    touched.append(page)
        if not touched:
            return None, None
        return touched[0], touched[-1]

    def _segment_index_for(
        self,
        segments: list[dict[str, Any]] | None,
        start_byte: int,
    ) -> int:
        for row in segments or ():
            start = row.get("start_byte")
            end = row.get("end_byte")
            if _literal_int(start) and _literal_int(end) and start <= start_byte < end:
                index = row.get("segment_index")
                if _literal_int(index):
                    return index
        return 0

    def _build_passages(
        self,
        *,
        report_id: str,
        item: Mapping[str, Any],
        extracted: Mapping[str, Any],
        segments: list[dict[str, Any]] | None,
        hits: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        extra: list[str] = []
        text = extracted.get("text")
        if not isinstance(text, str):
            return [], extra
        text_bytes = text.encode("utf-8")
        built: list[dict[str, Any]] = []
        for row in hits.get("passages") or ():
            if not isinstance(row, Mapping):
                continue
            locator = row.get("locator") if isinstance(row.get("locator"), Mapping) else {}
            start_char = locator.get("start_char", row.get("start_char"))
            end_char = locator.get("end_char", row.get("end_char"))
            if not _literal_int(start_char) or not _literal_int(end_char) or end_char <= start_char:
                continue
            if start_char < 0 or end_char > len(text):
                continue
            start_byte = len(text[:start_char].encode("utf-8"))
            span_len = len(text[start_char:end_char].encode("utf-8"))
            raw = text_bytes[start_byte:start_byte + span_len]
            if len(raw) > _MAX_TEXT_BYTES:
                extra.append("FULL_TEXT_PARTIAL")
                continue
            try:
                passage_text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if not passage_text:
                continue
            end_byte = start_byte + len(raw)
            page_start, page_end = self._pages_for_span(
                extracted.get("page_boundaries"), start_byte, end_byte
            )
            match_start_char = locator.get("match_start_char", row.get("match_start_char"))
            match_end_char = locator.get("match_end_char", row.get("match_end_char"))
            match_text = row.get("match_text")
            matched_terms = row.get("matched_terms")
            try:
                passage_kwargs: dict[str, Any] = {}
                if not (
                    match_start_char is None
                    and match_end_char is None
                    and match_text is None
                    and matched_terms is None
                ):
                    passage_kwargs = {
                        "start_char": start_char,
                        "end_char": end_char,
                        "match_start_char": match_start_char,
                        "match_end_char": match_end_char,
                        "match_text": match_text,
                        "matched_terms": _bounded_matched_terms(matched_terms),
                    }
                built.append(
                    read_port.evidence_passage(
                        report_id=report_id,
                        title=str(item.get("title") or "Untitled research"),
                        institution=str(item.get("institution") or "Unknown"),
                        published_at=str(item.get("published_at") or "1970-01-01T00:00:00+00:00"),
                        source_pdf_sha256=str(extracted["source_pdf_sha256"]),
                        extracted_text_sha256=str(extracted["extracted_text_sha256"]),
                        extractor_name=str(extracted["extractor_name"]),
                        extractor_version=str(extracted["extractor_version"]),
                        segmenter_version=fulltext.SEGMENTER_VERSION,
                        segment_index=self._segment_index_for(segments, start_byte),
                        page_start=page_start,
                        page_end=page_end,
                        start_byte=start_byte,
                        end_byte=end_byte,
                        text=passage_text,
                        coverage_state="FULL_TEXT",
                        open_source_ref=None,
                        **passage_kwargs,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue
        return built, extra

    def status(self, *, caller_context: Mapping[str, Any]) -> Mapping[str, Any]:
        gated = self._gate_context(caller_context, "status")
        if not isinstance(gated, ServerReadContext):
            return gated
        now = self._now()
        catalog, source = self._read_catalog(now)
        if catalog is None:
            return read_port.status_result(
                source=source,
                corpus_state="UNAVAILABLE",
                full_text_coverage=0.0,
                rio_coverage=0.0,
            )
        admitted = set(_catalog_items(catalog))
        extra: list[str] = []
        conn = self._open_corpus()
        try:
            corpus_state, corpus_extra = self._corpus_snapshot(conn, admitted)
        finally:
            _close_conn(conn)
        extra.extend(corpus_extra)
        ft_ratio, ft_unknown = self._coverage_ratio(self._full_text_inventory, admitted)
        rio_ratio, rio_unknown = self._coverage_ratio(self._rio_inventory, admitted)
        if ft_unknown:
            extra.append("FULL_TEXT_PARTIAL")
        if rio_unknown:
            extra.append("RIO_PARTIAL")
        source = self._with_degradation(catalog, now, extra)
        return read_port.status_result(
            source=source,
            corpus_state=corpus_state,
            full_text_coverage=ft_ratio,
            rio_coverage=rio_ratio,
        )

    def search(
        self,
        *,
        caller_context: Mapping[str, Any],
        query: str,
        filters: Mapping[str, Any],
        limit: int,
        cursor: str | None,
    ) -> Mapping[str, Any]:
        gated = self._gate_context(caller_context, "search")
        if not isinstance(gated, ServerReadContext):
            return gated
        validated = self._validate_search(query, filters, limit, cursor)
        if not isinstance(validated, tuple):
            return validated
        stripped, filter_map, effective = validated
        now = self._now()
        catalog, source = self._read_catalog(now)
        view = "full" if gated.entitlement == "pro" else "preview"
        if catalog is None:
            return self._search_envelope(
                available=False,
                query=stripped,
                filters=filter_map,
                limit=effective,
                entitlement_view=view,
                source=source,
                corpus_state="UNAVAILABLE",
                coverage_state=None,
                candidates=[],
            )
        admitted = _catalog_items(catalog)
        admitted_ids = set(admitted)
        conn = self._open_corpus()
        try:
            corpus_state, extra = self._corpus_snapshot(conn, admitted_ids)
            if conn is None or corpus_state == "UNAVAILABLE":
                source = self._with_degradation(catalog, now, extra)
                return self._search_envelope(
                    available=False,
                    query=stripped,
                    filters=filter_map,
                    limit=effective,
                    entitlement_view=view,
                    source=source,
                    corpus_state="UNAVAILABLE",
                    coverage_state=None,
                    candidates=[],
                )
            rows = corpus_mod.search(
                conn,
                stripped,
                filter_map.get("institution"),
                filter_map.get("date_from"),
                filter_map.get("date_to"),
                limit=effective,
            )
        finally:
            _close_conn(conn)

        kept: list[Mapping[str, Any]] = []
        for row in rows:
            report_id = row.get("id")
            if report_id in admitted:
                kept.append(row)
        if gated.entitlement != "pro":
            preview = self._preview_ids(catalog)
            kept = [row for row in kept if row.get("id") in preview]

        candidates: list[dict[str, Any]] = []
        for index, row in enumerate(kept, start=1):
            item = admitted[str(row["id"])]
            candidates.append(
                {
                    "report_id": item.get("id"),
                    "title": item.get("title") or "",
                    "institution": item.get("institution") or "",
                    "side": item.get("side") or "",
                    "published_at": item.get("published_at") or "",
                    "rank": index,
                }
            )
        coverage = "PARTIAL_CORPUS" if corpus_state == "PARTIAL" else "PREFIX_ONLY_LEGACY"
        source = self._with_degradation(catalog, now, extra)
        return self._search_envelope(
            available=True,
            query=stripped,
            filters=filter_map,
            limit=effective,
            entitlement_view=view,
            source=source,
            corpus_state=corpus_state,
            coverage_state=coverage,
            candidates=candidates,
        )

    def fetch(
        self,
        *,
        caller_context: Mapping[str, Any],
        report_id: str,
        selectors: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        gated = self._gate_context(caller_context, "fetch")
        if not isinstance(gated, ServerReadContext):
            return gated
        checked = self._validate_report_id(report_id)
        if not isinstance(checked, str):
            return checked
        parsed = self._validate_fetch_selectors(selectors)
        if not isinstance(parsed, tuple):
            return parsed
        segment_start, max_segments = parsed
        entitled = self._entitle_report(gated)
        if entitled is not None:
            return entitled
        now = self._now()
        catalog, source = self._read_catalog(now)
        if catalog is None:
            return self._fetch_envelope(
                available=False,
                report_id=checked,
                report=None,
                source=source,
                coverage_state=None,
                text_layer_state=None,
                rio_state="NOT_REQUESTED",
                rio_artifact_sha256=None,
                segment_count_total=0,
                segments=[],
            )
        items = _catalog_items(catalog)
        item = items.get(checked)
        if item is None:
            return read_port.failure("REPORT_NOT_FOUND")
        coverage, extracted, segments, extra = self._resolve_text(checked, item)
        rio_state, stored, rio_extra = self._rio_state(checked, extracted)
        extra.extend(rio_extra)
        source = self._with_degradation(catalog, now, extra)
        sha = getattr(stored, "artifact_sha256", None) if stored is not None else None
        if not isinstance(sha, str):
            sha = None
        layer = extracted.get("text_layer_state") if extracted is not None else None
        if not isinstance(layer, str):
            layer = None
        if coverage == "FULL_TEXT":
            total, projected = self._project_segments(segments, segment_start, max_segments)
        else:
            total, projected = 0, []
        return self._fetch_envelope(
            available=True,
            report_id=checked,
            report=self._report_meta(item),
            source=source,
            coverage_state=coverage,
            text_layer_state=layer,
            rio_state=rio_state,
            rio_artifact_sha256=sha,
            segment_count_total=total,
            segments=projected,
        )

    def find_evidence(
        self,
        *,
        caller_context: Mapping[str, Any],
        report_id: str,
        query: str,
        max_passages: int,
    ) -> Mapping[str, Any]:
        gated = self._gate_context(caller_context, "find_evidence")
        if not isinstance(gated, ServerReadContext):
            return gated
        checked = self._validate_report_id(report_id)
        if not isinstance(checked, str):
            return checked
        parsed = self._validate_evidence(query, max_passages)
        if not isinstance(parsed, tuple):
            return parsed
        evidence_query, effective = parsed
        entitled = self._entitle_report(gated)
        if entitled is not None:
            return entitled
        now = self._now()
        catalog, source = self._read_catalog(now)
        if catalog is None:
            return read_port.evidence_result(
                report_id=checked,
                evidence_state="UNAVAILABLE",
                coverage_state="EXTRACTION_UNAVAILABLE",
                source=source,
                passages=(),
                rio_state="NOT_REQUESTED",
            )
        items = _catalog_items(catalog)
        item = items.get(checked)
        if item is None:
            return read_port.failure("REPORT_NOT_FOUND")
        coverage, extracted, segments, extra = self._resolve_text(checked, item)
        rio_state, _stored, rio_extra = self._rio_state(checked, extracted)
        extra.extend(rio_extra)
        if coverage != "FULL_TEXT" or extracted is None:
            source = self._with_degradation(catalog, now, extra)
            return read_port.evidence_result(
                report_id=checked,
                evidence_state="UNAVAILABLE",
                coverage_state=coverage if coverage in read_port.COVERAGE_STATES else "EXTRACTION_UNAVAILABLE",
                source=source,
                passages=(),
                rio_state=rio_state,
            )
        text = extracted.get("text") if isinstance(extracted.get("text"), str) else ""
        hits = corpus_mod.find_evidence_passages(
            {
                "body": text,
                "char_count": len(text),
                "content_sha256": extracted.get("extracted_text_sha256"),
                "text_layer": extracted.get("text_layer_state"),
                "pages": extracted.get("page_count"),
            },
            evidence_query,
            limit=effective,
        )
        if hits.get("status") == "body_unavailable":
            extra.append("FULL_TEXT_PARTIAL")
            source = self._with_degradation(catalog, now, extra)
            return read_port.evidence_result(
                report_id=checked,
                evidence_state="UNAVAILABLE",
                coverage_state="EXTRACTION_UNAVAILABLE",
                source=source,
                passages=(),
                rio_state=rio_state,
            )
        passages, drop_extra = self._build_passages(
            report_id=checked,
            item=item,
            extracted=extracted,
            segments=segments,
            hits=hits,
        )
        extra.extend(drop_extra)
        layer = extracted.get("text_layer_state")
        if passages:
            evidence_state = "PARTIAL" if layer == "thin" else "FOUND"
        else:
            evidence_state = "NOT_FOUND"
        source = self._with_degradation(catalog, now, extra)
        return read_port.evidence_result(
            report_id=checked,
            evidence_state=evidence_state,
            coverage_state="FULL_TEXT",
            source=source,
            passages=passages,
            rio_state=rio_state,
        )
