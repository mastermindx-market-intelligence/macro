"""Pure Brain and MCP translation shims over one ResearchReadPort.

These adapters own no policy: they do not resolve entitlement, classify
freshness, select visibility, or talk to a store. Entitlement arrives only as
the server-supplied ``server_context`` keyword and is never read from tool
arguments. This module imports no MCP SDK, no ``app`` package, and opens no
network connection.
"""
from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from typing import Any

from engine.research_vault import read_port

TOOL_NAMES = {
    "research_status": "status",
    "research_search": "search",
    "research_fetch": "fetch",
    "research_find_evidence": "find_evidence",
}

FORBIDDEN_ARGUMENT_KEYS = frozenset(
    {
        "principal",
        "principal_id",
        "user_id",
        "user_ctx",
        "caller_context",
        "tier",
        "entitlement",
        "scopes",
        "surface",
        "bucket",
        "root",
        "credential",
        "store",
        "visibility",
    }
)

ARGUMENT_SCHEMAS: dict[str, dict[str, Any]] = {
    "research_status": {
        "type": "object",
        "additionalProperties": False,
        "properties": {},
    },
    "research_search": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "query": {"type": "string"},
            "filters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "institution": {"type": "string"},
                    "date_from": {"type": "string"},
                    "date_to": {"type": "string"},
                },
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            "cursor": {"type": "null"},
        },
    },
    "research_fetch": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "report_id": {"type": "string"},
            "selectors": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "segment_start": {"type": "integer", "minimum": 0},
                    "max_segments": {"type": "integer", "minimum": 1, "maximum": 4},
                },
            },
        },
    },
    "research_find_evidence": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "report_id": {"type": "string"},
            "query": {"type": "string"},
            "max_passages": {"type": "integer", "minimum": 1, "maximum": 12},
        },
    },
}

_TOOL_DESCRIPTIONS = {
    "research_status": "Return Research Vault source, corpus, and coverage status.",
    "research_search": "Search catalog-admitted research reports.",
    "research_fetch": "Fetch catalog metadata and full-text segments for one report.",
    "research_find_evidence": "Find literal source-evidence passages in one report.",
}


def _dispatch(port: Any, tool: Any, arguments: Any, server_context: Any) -> Mapping[str, Any]:
    operation = TOOL_NAMES.get(tool)
    if operation is None:
        return read_port.failure("INVALID_REQUEST")
    if not isinstance(arguments, Mapping):
        return read_port.failure("INVALID_REQUEST")
    allowed = ARGUMENT_SCHEMAS[tool]["properties"]
    for key in arguments:
        if key in FORBIDDEN_ARGUMENT_KEYS or key not in allowed:
            return read_port.failure("INVALID_REQUEST")

    if operation == "status":
        return port.status(caller_context=server_context)
    if operation == "search":
        return port.search(
            caller_context=server_context,
            query=arguments.get("query", ""),
            filters=arguments.get("filters", {}),
            limit=arguments.get("limit", 10),
            cursor=arguments.get("cursor", None),
        )
    if operation == "fetch":
        return port.fetch(
            caller_context=server_context,
            report_id=arguments.get("report_id"),
            selectors=arguments.get("selectors", {}),
        )
    return port.find_evidence(
        caller_context=server_context,
        report_id=arguments.get("report_id"),
        query=arguments.get("query"),
        max_passages=arguments.get("max_passages", 3),
    )


class BrainResearchAdapter:
    """Brain envelope over ``_dispatch``. Owns no policy."""

    def __init__(self, port: Any) -> None:
        self._port = port

    def call(self, tool: str, arguments: Any, *, server_context: Any) -> dict[str, Any]:
        result = _dispatch(self._port, tool, arguments, server_context)
        return {
            "schema": "brain.research_port.v1",
            "tool": tool,
            "result": result,
        }

    def tool_schemas(self) -> dict[str, Any]:
        return copy.deepcopy(ARGUMENT_SCHEMAS)


class McpResearchAdapter:
    """MCP envelope over ``_dispatch``. Owns no policy and imports no MCP SDK."""

    def __init__(self, port: Any) -> None:
        self._port = port

    def call_tool(self, name: str, arguments: Any, *, server_context: Any) -> dict[str, Any]:
        result = _dispatch(self._port, name, arguments, server_context)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, sort_keys=True, ensure_ascii=False),
                }
            ],
            "structuredContent": result,
            "isError": result.get("ok") is not True,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return copy.deepcopy(
            [
                {
                    "name": name,
                    "description": _TOOL_DESCRIPTIONS[name],
                    "inputSchema": ARGUMENT_SCHEMAS[name],
                }
                for name in sorted(TOOL_NAMES)
            ]
        )
