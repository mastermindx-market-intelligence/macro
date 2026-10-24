"""Passive decision helper for the EXISTING TP-1 websocket supervisor.

No socket, lease, admission authority, retry loop or scheduling is created.
Explicit 1008 max_connections and policy close are non-retryable until the
existing service/owner reconciles current socket custody and permissions.
"""

from __future__ import annotations


def classify_socket_close(*, close_code, had_authenticated, observed_max_connections):
    """Classify outcome only; never dispatch a reconnect."""
    if type(close_code) is not int or type(had_authenticated) is not bool or type(observed_max_connections) is not bool:
        return {"verdict":"HOLD","reason":"UNKNOWN_CLOSE_EVIDENCE","may_reconnect":False}
    if close_code == 1008 or observed_max_connections:
        return {"verdict":"HARD_STOP","reason":"POSSIBLE_SLOT_OR_PERMISSION_CONFLICT",
                "may_reconnect":False}
    if close_code in (1000,1001):
        return {"verdict":"STOP","reason":"NORMAL_OR_GOING_AWAY",
                "may_reconnect":False}
    return {"verdict":"EXTERNAL_SUPERVISOR_REQUIRED",
            "reason":"TRANSPORT_FAILURE_REQUIRES_INCUMBENT_RECOVERY",
            "may_reconnect":False}
