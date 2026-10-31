"""Bounded openFDA device acquisition. No schedule or automatic retry is installed."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import time
from typing import Callable

import requests

from engine.medtech.events import DATASETS, MedTechError, normalize_record, utc

MAX_PAGE_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 10000
PAGE_SIZE = 250
MAX_PAGE_RECORDS = 1000
USER_AGENT = "MastermindMedTech/1.0 (+https://mastermind-x.com)"


@dataclass(frozen=True)
class SourceBatch:
    dataset: str
    start: str
    end: str
    observed_at: str
    dataset_updated_at: str
    total: int
    pages: tuple[bytes, ...]
    request_urls: tuple[str, ...]
    # Retained acquisitions before the bounded-page repair used 1,000 records.
    # New fetches bind their actual request width explicitly without rewriting evidence.
    page_size: int = 1000

    def records(self) -> list[dict]:
        rows = []
        for page in self.pages:
            obj = json.loads(page)
            rows.extend(obj.get("results", []))
        return rows


def _day(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError):
        raise MedTechError("INVALID_DATE_RANGE") from None
    return parsed.isoformat()


def validate_batch(batch: SourceBatch) -> list:
    """Recheck the retained bytes at the evidence-store boundary."""
    if batch.dataset not in DATASETS:
        raise MedTechError("INVALID_DATASET")
    start, end = _day(batch.start), _day(batch.end)
    if start > end or end > datetime.fromisoformat(batch.observed_at.replace("Z", "+00:00")).date().isoformat():
        raise MedTechError("INVALID_DATE_RANGE")
    if type(batch.page_size) is not int or not 1 <= batch.page_size <= MAX_PAGE_RECORDS:
        raise MedTechError("SOURCE_PAGE_SIZE_INVALID")
    if not batch.pages or len(batch.pages) != len(batch.request_urls):
        raise MedTechError("INCOMPLETE_SOURCE_BATCH")
    if type(batch.total) is not int or not 0 <= batch.total <= MAX_RECORDS:
        raise MedTechError("SOURCE_RECORD_LIMIT")
    normalized, identities = [], set()
    count = 0
    for index, raw in enumerate(batch.pages):
        if not isinstance(raw, bytes) or len(raw) > MAX_PAGE_BYTES:
            raise MedTechError("SOURCE_RESPONSE_TOO_LARGE")
        try:
            obj = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise MedTechError("SOURCE_RESPONSE_INVALID") from None
        if not isinstance(obj, dict):
            raise MedTechError("SOURCE_RESPONSE_INVALID")
        expected_url = request_url(batch.dataset, start, end, count, page_size=batch.page_size)
        if batch.request_urls[index] != expected_url:
            raise MedTechError("SOURCE_REQUEST_MISMATCH")
        if batch.total == 0:
            if (len(batch.pages) != 1 or set(obj) != {"error"}
                    or not isinstance(obj["error"], dict)
                    or obj["error"].get("code") != "NOT_FOUND"):
                raise MedTechError("SOURCE_EMPTY_UNVERIFIED")
            continue
        meta = obj.get("meta", {})
        if not isinstance(meta, dict) or not isinstance(meta.get("results"), dict):
            raise MedTechError("SOURCE_RESPONSE_INVALID")
        result_meta, records = meta.get("results", {}), obj.get("results")
        if (meta.get("last_updated") != batch.dataset_updated_at
                or result_meta.get("total") != batch.total
                or result_meta.get("skip") != count
                or not isinstance(records, list)
                or not records or len(records) != min(batch.page_size, batch.total - count)
                or type(result_meta.get("limit")) is not int
                or not len(records) <= result_meta["limit"] <= batch.page_size):
            raise MedTechError("SOURCE_PAGE_MISMATCH")
        for record in records:
            observed = normalize_record(batch.dataset, record,
                observed_at=batch.observed_at, dataset_updated_at=batch.dataset_updated_at)
            decision_date = observed.event["decision"]["date"]
            if not decision_date or not start <= decision_date <= end:
                raise MedTechError("SOURCE_RANGE_MISMATCH")
            if observed.event_id in identities:
                raise MedTechError("SOURCE_DUPLICATE_ID")
            identities.add(observed.event_id)
            normalized.append(observed)
        count += len(records)
    if count != batch.total:
        raise MedTechError("INCOMPLETE_SOURCE_BATCH")
    return normalized


def request_url(dataset: str, start: str, end: str, skip: int, *, page_size: int = PAGE_SIZE) -> str:
    if dataset not in DATASETS:
        raise MedTechError("INVALID_DATASET")
    if type(page_size) is not int or not 1 <= page_size <= MAX_PAGE_RECORDS:
        raise MedTechError("SOURCE_PAGE_SIZE_INVALID")
    params = {
        "search": f"decision_date:[{start.replace('-', '')} TO {end.replace('-', '')}]",
        "sort": "decision_date:asc",
        "limit": page_size, "skip": skip,
    }
    return requests.Request("GET", DATASETS[dataset], params=params).prepare().url


def fetch_batch(dataset: str, *, start: str, end: str,
                max_records: int = MAX_RECORDS,
                session=None, clock: Callable[[], datetime] | None = None,
                pause: Callable[[float], None] = time.sleep) -> SourceBatch:
    start, end = _day(start), _day(end)
    clock = clock or (lambda: datetime.now(timezone.utc))
    if (dataset not in DATASETS or start > end or end > clock().date().isoformat()
            or type(max_records) is not int or not 1 <= max_records <= MAX_RECORDS):
        raise MedTechError("INVALID_ACQUISITION_SCOPE")
    own_session = session is None
    session = session or requests.Session()
    pages, urls, total, updated, count = [], [], None, None, 0
    try:
        while total is None or count < total:
            url = request_url(dataset, start, end, count)
            try:
                with session.get(url, timeout=(5, 30), stream=True, allow_redirects=False,
                                 headers={"User-Agent": USER_AGENT, "Accept": "application/json"}) as response:
                    if response.status_code not in (200, 404):
                        raise MedTechError("SOURCE_HTTP_" + str(response.status_code))
                    chunks, size = [], 0
                    for chunk in response.iter_content(chunk_size=65536):
                        size += len(chunk)
                        if size > MAX_PAGE_BYTES:
                            raise MedTechError("SOURCE_RESPONSE_TOO_LARGE")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                    obj = json.loads(raw)
                    if not isinstance(obj, dict):
                        raise MedTechError("SOURCE_RESPONSE_INVALID")
                    if response.status_code == 404:
                        if count != 0 or obj.get("error", {}).get("code") != "NOT_FOUND":
                            raise MedTechError("SOURCE_RESPONSE_INVALID")
                        # No dataset timestamp is provided on this response. Never invent it.
                        batch = SourceBatch(dataset, start, end, utc(clock().isoformat()),
                                            "", 0, (raw,), (url,), page_size=PAGE_SIZE)
                        validate_batch(batch)
                        return batch
            except (requests.RequestException, ValueError, UnicodeDecodeError) as exc:
                if isinstance(exc, MedTechError):
                    raise
                raise MedTechError("SOURCE_TRANSPORT_UNAVAILABLE") from None
            meta, records = obj.get("meta", {}), obj.get("results")
            if not isinstance(meta, dict) or not isinstance(meta.get("results"), dict):
                raise MedTechError("SOURCE_RESPONSE_INVALID")
            page_total = meta["results"].get("total")
            if type(page_total) is not int or not 0 < page_total <= max_records:
                raise MedTechError("SOURCE_RECORD_LIMIT")
            if (not isinstance(records, list) or len(records) != min(PAGE_SIZE, page_total - count)
                    or meta["results"].get("skip") != count):
                raise MedTechError("SOURCE_RESPONSE_INVALID")
            if total is None:
                total, updated = page_total, meta.get("last_updated")
            if page_total != total or meta.get("last_updated") != updated:
                raise MedTechError("SOURCE_CHANGED_DURING_FETCH")
            pages.append(raw)
            urls.append(url)
            count += len(records)
            if count < total:
                pause(0.35)
        batch = SourceBatch(dataset, start, end, utc(clock().isoformat()),
                            updated, total, tuple(pages), tuple(urls), page_size=PAGE_SIZE)
        validate_batch(batch)
        return batch
    finally:
        if own_session:
            session.close()
