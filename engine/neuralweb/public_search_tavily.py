"""Tavily qualification adapter for the provider-neutral public evidence core.

No provider activation, fallback, arbitrary-page fetch or Brain wiring is implied.
Only this module owns the candidate's credentials, service endpoints and payloads.
"""
from __future__ import annotations

import json
import math
import os
from typing import Any, Callable

from engine.neuralweb.public_research import (
    PublicEvidenceRequest, PublicResearchNotConfigured, PublicResearchTransportError,
    _ascii_host, _requested_urls, build_public_query, validate_public_request,
)

SEARCH_ENDPOINT = "https://api.tavily.com/search"
EXTRACT_ENDPOINT = "https://api.tavily.com/extract"
_MAX_SEARCH_RESPONSE_BYTES = 1024 * 1024
_MAX_EXTRACT_RESPONSE_BYTES = 2 * 1024 * 1024
_RESPONSE_LIMITS = {
    SEARCH_ENDPOINT: _MAX_SEARCH_RESPONSE_BYTES,
    EXTRACT_ENDPOINT: _MAX_EXTRACT_RESPONSE_BYTES,
}
_MAX_PROVIDER_ROWS = 64
_MAX_DOMAINS = 20
_SAFE_TOPIC = frozenset({"general", "news", "finance"})
_SAFE_DEPTH = frozenset({"advanced", "basic", "fast", "ultra-fast"})
_SAFE_EXTRACT_DEPTH = frozenset({"basic", "advanced"})
_SAFE_TIME_RANGE = frozenset({"day", "week", "month", "year", "d", "w", "m", "y"})


def _domain(value: object) -> str:
    if type(value) is not str:
        raise ValueError("invalid_public_search_request")
    raw = value.strip()
    if (
        not raw or len(raw) > 253 or any(ch in raw for ch in "/:@?#")
        or any(ord(ch) < 33 or ord(ch) == 127 for ch in raw)
    ):
        raise ValueError("invalid_public_search_request")
    try:
        return _ascii_host(raw)
    except ValueError:
        raise ValueError("invalid_public_search_request") from None


def _domains(values: object) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, (list, tuple)) or len(values) > _MAX_DOMAINS:
        raise ValueError("invalid_public_search_request")
    result: list[str] = []
    for value in values:
        domain = _domain(value)
        if domain not in result:
            result.append(domain)
    return result


def _reject_json_constant(_value: str) -> None:
    raise ValueError("provider_json_invalid")


def _default_post_json(
    url: str, *, headers: dict[str, str], payload: dict[str, Any], timeout: float,
) -> dict:
    """Count decoded bytes before retaining excess bytes or decoding any JSON."""
    response = None
    try:
        if type(url) is not str or url not in _RESPONSE_LIMITS:
            raise PublicResearchTransportError("provider_endpoint_invalid")
        if (
            isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or not 0 < timeout <= 60
        ):
            raise PublicResearchTransportError("provider_timeout_invalid")
        import requests

        response = requests.post(
            url, headers=headers, json=payload, timeout=timeout,
            allow_redirects=False, stream=True,
        )
        if not 200 <= int(response.status_code) < 300:
            raise PublicResearchTransportError("provider_http_error")
        limit = _RESPONSE_LIMITS[url]
        body = bytearray()
        # requests.iter_content yields decoded/decompressed bytes. Content-Length
        # is neither required nor trusted; a lying header cannot enlarge the cap.
        for chunk in response.iter_content(chunk_size=16384):
            if not chunk:
                continue
            if not isinstance(chunk, bytes) or len(chunk) > limit - len(body):
                raise PublicResearchTransportError("provider_response_too_large")
            body.extend(chunk)
        decoded = json.loads(bytes(body), parse_constant=_reject_json_constant)
        if not isinstance(decoded, dict):
            raise PublicResearchTransportError("provider_json_invalid")
        return decoded
    except PublicResearchTransportError:
        raise
    except Exception:
        raise PublicResearchTransportError("provider_unavailable") from None
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


class TavilyAdapter:
    provider = "tavily"

    def __init__(
        self, *, api_key: str | None = None, post_json: Callable[..., dict] | None = None,
        topic: str = "finance", search_depth: str = "advanced",
        time_range: str | None = None, include_domains: object = (),
        exclude_domains: object = (), filter_by_published_date: bool = False,
        extract_depth: str = "advanced",
    ):
        self._api_key = api_key
        self._post_json = post_json
        self.topic = topic
        self.search_depth = search_depth
        self.time_range = time_range
        self.include_domains = include_domains
        self.exclude_domains = exclude_domains
        self.filter_by_published_date = filter_by_published_date
        self.extract_depth = extract_depth

    def _post(self, endpoint: str, payload: dict, timeout: float) -> dict:
        key = self._api_key if self._api_key is not None else os.environ.get("TAVILY_API_KEY")
        if type(key) is not str or not key.strip():
            raise PublicResearchNotConfigured("provider_not_configured")
        try:
            response = (self._post_json or _default_post_json)(
                endpoint,
                headers={"Authorization": f"Bearer {key.strip()}", "Content-Type": "application/json"},
                payload=payload, timeout=timeout,
            )
            if not isinstance(response, dict):
                raise PublicResearchTransportError("provider_json_invalid")
            return response
        except Exception:
            raise PublicResearchTransportError("provider_unavailable") from None

    def search(self, request: PublicEvidenceRequest, *, max_results: int) -> dict:
        request = validate_public_request(request)
        if type(max_results) is not int or not 1 <= max_results <= 8:
            raise ValueError("invalid_public_search_request")
        if (
            type(self.topic) is not str or self.topic not in _SAFE_TOPIC
            or type(self.search_depth) is not str or self.search_depth not in _SAFE_DEPTH
            or (
                self.time_range is not None
                and (type(self.time_range) is not str or self.time_range not in _SAFE_TIME_RANGE)
            )
            or type(self.filter_by_published_date) is not bool
        ):
            raise ValueError("invalid_public_search_request")
        included, excluded = _domains(self.include_domains), _domains(self.exclude_domains)
        if set(included).intersection(excluded):
            raise ValueError("invalid_public_search_request")
        payload = {
            "query": build_public_query(request), "search_depth": self.search_depth,
            "max_results": max_results, "topic": self.topic, "time_range": self.time_range,
            "start_date": request.start_date, "end_date": request.end_date,
            "include_published_date": True, "filter_by_published_date": self.filter_by_published_date,
            "include_answer": False, "include_raw_content": False, "include_images": False,
            "include_image_descriptions": False, "include_favicon": False,
            "include_domains": included, "exclude_domains": excluded,
            "auto_parameters": False, "include_usage": True,
        }
        if self.search_depth != "ultra-fast":
            payload["chunks_per_source"] = 3
        response = self._post(SEARCH_ENDPOINT, payload, 30.0)
        rows = response.get("results")
        if not isinstance(rows, list):
            raise PublicResearchTransportError("provider_json_invalid")
        results = [
            {
                "url": row.get("url"), "title": row.get("title"),
                "snippet": row.get("content"), "score": row.get("score"),
                "published_date": row.get("published_date"),
            } if isinstance(row, dict) else None
            for row in rows[:_MAX_PROVIDER_ROWS]
        ]
        return {
            "status": "completed", "action": "search", "search_executed": True,
            "results": results, "provider_result_count": len(rows),
            "request_id": response.get("request_id"), "usage": response.get("usage"),
        }

    def open_sources(
        self, urls: list[str], *, request: PublicEvidenceRequest | None,
        max_content_chars: int,
    ) -> dict:
        requested = _requested_urls(urls)
        request = validate_public_request(request) if request is not None else None
        if (
            type(self.extract_depth) is not str or self.extract_depth not in _SAFE_EXTRACT_DEPTH
            or type(max_content_chars) is not int or not 1000 <= max_content_chars <= 50000
        ):
            raise ValueError("invalid_public_source_request")
        payload: dict[str, Any] = {
            "urls": requested, "extract_depth": self.extract_depth,
            "include_images": False, "include_favicon": False, "format": "markdown",
            "include_usage": True,
        }
        if request is not None:
            payload["query"] = build_public_query(request)
            payload["chunks_per_source"] = 3
        response = self._post(EXTRACT_ENDPOINT, payload, 35.0)
        rows, failed = response.get("results"), response.get("failed_results")
        if not isinstance(rows, list):
            rows = []
        if not isinstance(failed, list):
            failed = []
        results = []
        for row in rows[:_MAX_PROVIDER_ROWS]:
            if not isinstance(row, dict):
                continue
            content = row.get("raw_content")
            results.append({
                "url": row.get("url"),
                "content": content[:max_content_chars] if isinstance(content, str) else None,
                "content_truncated": isinstance(content, str) and len(content) > max_content_chars,
                "retrieval_method": "provider_extracted", "content_type": "text/markdown",
                "content_scope": "query_reranked_chunks" if request is not None else "bounded_page_extraction",
            })
        failures = [
            {"url": row.get("url")} for row in failed[:_MAX_PROVIDER_ROWS] if isinstance(row, dict)
        ]
        return {
            "status": "completed", "action": "open", "open_executed": True,
            "results": results, "failed_results": failures,
            "provider_result_count": len(rows), "provider_failed_result_count": len(failed),
            "request_id": response.get("request_id"), "usage": response.get("usage"),
        }
