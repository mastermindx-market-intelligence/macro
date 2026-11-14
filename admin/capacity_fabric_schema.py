"""Closed, content-free telemetry contract shared by the router and admin.

This is an observation format, never an admission, billing or agent registry.
"""
from __future__ import annotations

import math
import re

SCHEMA = "mastermind.capacity.router.observatory.v1"
MAX_BYTES = 2 * 1024 * 1024
MAX_ACTIVE = 256
MAX_RECENT = 400
MAX_ROUTES = 128
MAX_ATTEMPTS = 12
MAX_FAMILIES = 16
MAX_KEYS = 32
MAX_ACCOUNTS = 16
MAX_LANES = 8
MAX_OVERFLOW_EVENTS = 20
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")
CLIENTS = {"T3", "Paperclip", "Hermes", "Subagent Fabric", "Claude SDK", "OpenAI SDK", "Python client", "Unknown client"}
STATES = {"routing", "waiting", "streaming", "completed", "failed", "cancelled", "interrupted"}
RESET_SOURCES = {"provider", "estimated"}
_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _./:()+@-]{0,127}$")
_ID = re.compile(r"^[a-f0-9]{16,64}$")
_SECRET = re.compile(r"xox[baprs]-|xapp-|github_pat_|gh[pousr]_|sk-[A-Za-z0-9_-]{16,}|bearer\s", re.I)


def label(value, fallback="unknown"):
    if isinstance(value, str) and _SECRET.search(value):
        return fallback
    return value if isinstance(value, str) and _SAFE.fullmatch(value) else fallback


def identifier(value):
    return value if isinstance(value, str) and _ID.fullmatch(value) else None


def number(value, default=None, maximum=10**15):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return value if 0 <= value <= maximum and math.isfinite(value) else default


def count(value, default=0):
    result = number(value, default)
    return int(result) if result is not None else None


def _usage(value):
    value = value if isinstance(value, dict) else {}
    return {key: count(value.get(key), None) for key in TOKEN_FIELDS}


def _clean_peak(raw):
    """Z.ai peak-window gate state. Observation only; never a routing grant."""
    if not isinstance(raw, dict):
        return None
    return {
        "active": raw.get("active") is True,
        "tz": label(raw.get("tz"), ""), "start": label(raw.get("start"), ""),
        "end": label(raw.get("end"), ""),
        "wait_s": number(raw.get("wait_s")), "next_send_in_s": number(raw.get("next_send_in_s")),
    }


def _clean_overflow(raw):
    """Family overflow ladders and seat pressure. Local estimates, never provider balances."""
    if not isinstance(raw, dict):
        return None
    families = {}
    for name, fam in list((raw.get("families") or {}).items())[:MAX_FAMILIES]:
        if not isinstance(fam, dict):
            continue
        families[label(name)] = {
            "overflowing": fam.get("overflowing") is True,
            "signal": label(fam.get("signal"), "") if fam.get("signal") else None,
            "overflowing_for_s": number(fam.get("overflowing_for_s"), 0),
            "healthy_in_s": number(fam.get("healthy_in_s"), 0),
            "proactive_window_open": fam.get("proactive_window_open") is True,
            "targets": [label(v) for v in (fam.get("targets") or [])[:8]],
        }
    keys = {}
    for name, key in list((raw.get("keys") or {}).items())[:MAX_KEYS]:
        if not isinstance(key, dict):
            continue
        keys[label(name)] = {
            "input_tpm_limit": number(key.get("input_tpm_limit")),
            "target": number(key.get("target")),
            "used_or_reserved": number(key.get("used_or_reserved"), 0),
            "used_pct_of_limit": number(key.get("used_pct_of_limit"), None, 10**6),
            "over_target": key.get("over_target") is True,
            "cooling_s": number(key.get("cooling_s"), 0),
        }
    events = []
    for event in (raw.get("recent") or [])[-MAX_OVERFLOW_EVENTS:]:
        if not isinstance(event, dict):
            continue
        events.append({
            "event": label(event.get("event")), "kind": label(event.get("kind"), ""),
            "family": label(event.get("family"), ""),
            "requested_model": label(event.get("requested_model"), ""),
            "served_model": label(event.get("served_model"), ""),
            "route": label(event.get("route"), ""), "t": number(event.get("t")),
        })
    return {
        "enabled": raw.get("enabled") is True, "version": label(raw.get("version"), ""),
        "diverted_requests": count(raw.get("diverted_requests")),
        "diversion_share": number(raw.get("diversion_share"), None, 1),
        "diverted_sessions": count(raw.get("diverted_sessions")),
        "diverted_inflight": count(raw.get("diverted_inflight")),
        "families": families, "keys": keys, "recent": events,
    }


def _clean_claude(raw):
    """Gateway family-lane budgets. Content-free scalars only; no account secrets."""
    if not isinstance(raw, dict):
        return None
    accounts = []
    for account in (raw.get("accounts") or [])[:MAX_ACCOUNTS]:
        if not isinstance(account, dict):
            continue
        lanes = {}
        for name, lane in list((account.get("families") or {}).items())[:MAX_LANES]:
            if not isinstance(lane, dict):
                continue
            lanes[label(name)] = {
                "used_weekly": number(lane.get("used_weekly"), 0),
                "budget_weekly": number(lane.get("budget_weekly")),
                "remaining_weekly": number(lane.get("remaining_weekly")),
                "pressure": number(lane.get("pressure"), None, 1),
                "cooldown_until": number(lane.get("cooldown_until")),
                "weekly_resets_at": number(lane.get("weekly_resets_at")),
                "weekly_reset_source": lane.get("weekly_reset_source")
                    if lane.get("weekly_reset_source") in RESET_SOURCES else None,
                "expiring_soon": lane.get("expiring_soon") is True,
            }
        accounts.append({
            "id": label(account.get("id")), "label": label(account.get("label")),
            "used_5h": number(account.get("used_5h"), 0),
            "budget_5h": number(account.get("budget_5h")),
            "remaining_5h": number(account.get("remaining_5h")),
            "inflight": count(account.get("inflight")),
            "last_status": label(account.get("last_status"), ""),
            "drain": account.get("drain") is True,
            "cooldown_until": number(account.get("cooldown_until")),
            "families": lanes,
        })
    return {
        "reachable": raw.get("reachable") is True,
        "observed_at": number(raw.get("observed_at")),
        "stranded_family": label(raw.get("stranded_family"), "") if raw.get("stranded_family") else None,
        "preferences": [label(v) for v in (raw.get("preferences") or [])[:16]],
        "accounts": accounts,
    }


def clean_request(raw):
    if not isinstance(raw, dict) or not identifier(raw.get("id")):
        return None
    attempts = []
    for a in (raw.get("attempts") or [])[:MAX_ATTEMPTS]:
        if not isinstance(a, dict):
            continue
        attempts.append({
            "route_id": label(a.get("route_id")), "model": label(a.get("model")),
            "started_at": number(a.get("started_at")), "ended_at": number(a.get("ended_at")),
            "state": label(a.get("state")), "reason": label(a.get("reason"), ""),
            "status_code": count(a.get("status_code"), None),
        })
    return {
        "id": raw["id"], "started_at": number(raw.get("started_at")),
        "ended_at": number(raw.get("ended_at")), "last_activity_at": number(raw.get("last_activity_at")),
        "first_content_at": number(raw.get("first_content_at")),
        "state": raw.get("state") if raw.get("state") in STATES else "interrupted",
        "status_code": count(raw.get("status_code"), None),
        "requested_model": label(raw.get("requested_model")),
        "served_model": label(raw.get("served_model"), ""), "wire_model": label(raw.get("wire_model"), ""),
        "route_id": label(raw.get("route_id"), ""), "provider": label(raw.get("provider"), ""),
        "lane": label(raw.get("lane"), "direct"),
        "client": raw.get("client") if raw.get("client") in CLIENTS else "Unknown client",
        "session_id": identifier(raw.get("session_id")), "agent_id": identifier(raw.get("agent_id")),
        "parent_agent_id": identifier(raw.get("parent_agent_id")), "project_id": identifier(raw.get("project_id")),
        "identity_source": raw.get("identity_source") if raw.get("identity_source") in
            {"caller_reported", "sdk_session", "unattributed"} else "unattributed",
        "usage": _usage(raw.get("usage")), "usage_final": raw.get("usage_final") is True,
        "usage_source": "provider_reported" if raw.get("usage_source") == "provider_reported" else "unavailable",
        "streaming": raw.get("streaming") is True, "content_events": count(raw.get("content_events")),
        "attempts": attempts, "observation_errors": count(raw.get("observation_errors")),
    }


def clean_snapshot(raw):
    """Drop every unrecognized field; reject ambiguous identity and unbounded shapes."""
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise ValueError("unsupported observation schema")
    if not identifier(raw.get("epoch")) or number(raw.get("started_at")) is None or number(raw.get("generated_at")) is None:
        raise ValueError("invalid observation identity")
    for key, cap in (("routes", MAX_ROUTES), ("active", MAX_ACTIVE), ("recent", MAX_RECENT), ("series", 120)):
        if not isinstance(raw.get(key), list) or len(raw[key]) > cap:
            raise ValueError("invalid observation bounds")
    routes = []
    for r in raw["routes"]:
        if not isinstance(r, dict):
            raise ValueError("invalid route")
        routes.append({
            "id": label(r.get("id")), "provider": label(r.get("provider")),
            "wire": label(r.get("wire")), "models": [label(v) for v in (r.get("models") or [])[:64]],
            "priority": count(r.get("priority")), "weight": number(r.get("weight"), 0),
            "cooling": r.get("cooling") is True, "cooldown_s": number(r.get("cooldown_s")),
            "consecutive_failures": count(r.get("consecutive_failures")),
            "served": count(r.get("served")), "attempt_failed": count(r.get("attempt_failed")),
            "refused": count(r.get("refused")),
        })
    aliases = raw.get("aliases") if isinstance(raw.get("aliases"), dict) else {}
    totals = raw.get("totals") if isinstance(raw.get("totals"), dict) else {}
    truncated = raw.get("truncated") if isinstance(raw.get("truncated"), dict) else {}
    series = []
    for b in raw["series"]:
        if not isinstance(b, dict):
            raise ValueError("invalid observation bucket")
        series.append({k: count(b.get(k)) for k in ("at", "completed", "failed", "usage_known", *TOKEN_FIELDS,
                       *(field + "_known" for field in TOKEN_FIELDS))})
    return {
        "schema": SCHEMA, "epoch": raw["epoch"], "sequence": count(raw.get("sequence")),
        "started_at": raw["started_at"], "generated_at": raw["generated_at"],
        "source": "Capacity Fabric / M2", "version": "1.0",
        "routes": routes,
        "aliases": {label(k): [label(v) for v in values[:32]] for k, values in list(aliases.items())[:32]
                    if isinstance(values, list)},
        "active": [r for v in raw["active"] if (r := clean_request(v)) is not None],
        "recent": [r for v in raw["recent"] if (r := clean_request(v)) is not None],
        "series": series,
        "totals": {k: count(totals.get(k)) for k in ("started", "completed", "failed", "cancelled",
            "usage_known", "attributed", "overflow_active", "dropped_requests", "observer_errors",
            "router_served", "router_refused", "router_attempts", "router_failovers", *TOKEN_FIELDS)},
        "limits": {"active": MAX_ACTIVE, "recent": MAX_RECENT, "history_minutes": 120},
        "truncated": {k: count(truncated.get(k)) for k in ("recent", "attempts", "models")},
        "peak": _clean_peak(raw.get("peak")),
        "overflow": _clean_overflow(raw.get("overflow")),
        "claude": _clean_claude(raw.get("claude")),
        "semantics": {
            "tokens": "Provider-reported cumulative usage; cache tokens are separate, never added to input totals.",
            "flow": "Particles indicate observed response activity, not individual tokens.",
            "identity": "Caller-reported identity or pseudonymous SDK session; not authenticated agent authority.",
            "coverage": "One router process; history begins at observer startup. Failed-attempt usage may be unavailable.",
            "overflow": "Family diversion state and seat pressure are local router estimates, never provider balances.",
            "claude": "Gateway family-lane budgets as observed by the gateway; reset times may be provider-reported or estimated.",
        },
    }
