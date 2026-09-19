"""Credential-free payload and response adapters for public-search qualification.

These helpers do not perform HTTP, read credentials, choose accounts, route models,
retry, fail over, or decide investment conclusions. They translate the normalized
public evidence request to provider contracts and normalize discovery results only.
"""
from __future__ import annotations

from typing import Any, Mapping

_REQUEST_SCHEMA = "brain.public_evidence_request.v1"
_OPENAI_MODELS = {"gpt-5.6-luna", "gpt-5.6-terra"}


class PublicSearchBackendError(ValueError):
    """A provider payload/response violates the qualification contract."""


def _require_request(request: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(request, Mapping) or request.get("schema") != _REQUEST_SCHEMA:
        raise PublicSearchBackendError("normalized public evidence request required")
    query = request.get("query")
    cutoff = request.get("information_cutoff")
    if not isinstance(query, str) or not query.strip():
        raise PublicSearchBackendError("public search query is missing")
    if not isinstance(cutoff, str) or len(cutoff) < 10:
        raise PublicSearchBackendError("information cutoff is missing")
    return request


def _search_instruction(request: Mapping[str, Any]) -> str:
    start = request.get("start_date") or "unbounded"
    end = request.get("end_date") or request["information_cutoff"][:10]
    preference = {
        "primary_first": "Prefer primary or official sources.",
        "official_first": "Prefer official issuer, regulator, exchange, or government sources.",
        "independent_first": "Prefer independent reporting, then verify against primary sources where available.",
    }.get(request.get("source_preference"))
    if preference is None:
        raise PublicSearchBackendError("source preference is not admitted")
    return (
        f"Find public evidence for: {request['query']}. "
        f"Evidence window: {start} through {end}; information cutoff: "
        f"{request['information_cutoff']}. {preference} "
        "Return search evidence only; do not make an investment recommendation."
    )


def openai_web_search_payload(
    request: Mapping[str, Any], *, model: str = "gpt-5.6-luna"
) -> dict[str, Any]:
    """Build a Responses API request that requires an actual web-search tool call."""
    request = _require_request(request)
    if model not in _OPENAI_MODELS:
        raise PublicSearchBackendError("OpenAI qualification model is not admitted")
    return {
        "model": model,
        "input": _search_instruction(request),
        "tools": [{"type": "web_search"}],
        "tool_choice": "required",
        "include": ["web_search_call.action.sources"],
    }


def _bounded(value: object, maximum: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:maximum]


def parse_openai_web_search_response(response: object) -> dict[str, Any]:
    """Normalize only observed completed SEARCH calls; ignore assistant prose."""
    if not isinstance(response, Mapping):
        return {"executed": False, "backend": "openai_responses_web_search", "candidates": []}
    response_id = _bounded(response.get("id"), 160)
    candidates: list[dict[str, Any]] = []
    search_ids: list[str] = []
    for item in response.get("output") or []:
        if not isinstance(item, Mapping):
            continue
        action = item.get("action")
        if (
            item.get("type") != "web_search_call"
            or item.get("status") != "completed"
            or not isinstance(action, Mapping)
            or action.get("type") != "search"
        ):
            continue
        search_id = _bounded(item.get("id"), 160)
        if search_id:
            search_ids.append(search_id)
        for source in action.get("sources") or []:
            if not isinstance(source, Mapping):
                continue
            url = _bounded(source.get("url"), 2048)
            if not url:
                continue
            candidates.append({
                "url": url,
                "title": _bounded(source.get("title"), 300),
                "snippet": "",
                "published_at": None,
            })
    executed = bool(search_ids)
    execution_id = None
    if executed:
        execution_id = f"{response_id}:{search_ids[0]}" if response_id else search_ids[0]
    return {
        "executed": executed,
        "backend": "openai_responses_web_search",
        "execution_id": execution_id,
        "candidates": candidates if executed else [],
    }


def brave_web_search_payload(
    request: Mapping[str, Any],
    *,
    count: int = 10,
    country: str = "US",
    search_lang: str = "en",
) -> dict[str, Any]:
    """Build credential-free Brave Web Search query parameters."""
    request = _require_request(request)
    if type(count) is not int or not 1 <= count <= 20:
        raise PublicSearchBackendError("Brave result count must be from 1 through 20")
    if country != "US" or search_lang != "en":
        raise PublicSearchBackendError("R1 qualification is pinned to US/en")
    params: dict[str, Any] = {
        "q": request["query"],
        "count": count,
        "country": country,
        "search_lang": search_lang,
    }
    start = request.get("start_date")
    end = request.get("end_date") or request["information_cutoff"][:10]
    if start:
        params["freshness"] = f"{start}to{end}"
    return params


def parse_brave_web_search_response(
    response: object, *, execution_id: str | None = None
) -> dict[str, Any]:
    """Normalize Brave Web Search results without trusting provider prose as evidence."""
    if not isinstance(response, Mapping) or response.get("type") != "search":
        return {
            "executed": False,
            "backend": "brave_web_search",
            "execution_id": None,
            "candidates": [],
        }
    web = response.get("web")
    if not isinstance(web, Mapping):
        return {
            "executed": True,
            "backend": "brave_web_search",
            "execution_id": _bounded(execution_id, 160) or None,
            "candidates": [],
        }
    candidates: list[dict[str, Any]] = []
    for row in web.get("results") or []:
        if not isinstance(row, Mapping):
            continue
        url = _bounded(row.get("url"), 2048)
        if not url:
            continue
        candidates.append({
            "url": url,
            "title": _bounded(row.get("title"), 300),
            "snippet": _bounded(row.get("description"), 1200),
            "published_at": (
                _bounded(row.get("page_age") or row.get("age"), 64) or None
            ),
        })
    return {
        "executed": True,
        "backend": "brave_web_search",
        "execution_id": _bounded(execution_id, 160) or None,
        "candidates": candidates,
    }
