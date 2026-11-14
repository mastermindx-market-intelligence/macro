"""Bounded authenticated SSE delivery of the incumbent router's observations."""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time

from . import capacity_router

# One browser uses one stream, not a connection for every panel. Keep ordinary
# admin requests serviceable even when a browser or reverse proxy stalls.
_STREAM_SLOTS = threading.BoundedSemaphore(8)


def delta(previous, current):
    """A complete cursor plus changed rows; reconnect always receives a snapshot."""
    if not previous or previous.get("epoch") != current.get("epoch") or not current.get("ok"):
        return "snapshot", current
    result = {k: v for k, v in current.items() if k not in {"active", "recent", "routes", "aliases", "series", "claude", "overflow", "controls"}}
    for field in ("active", "recent"):
        prior = {r["id"]: r for r in previous.get(field, [])}
        rows = current.get(field, [])
        result[field + "_ids"] = [r["id"] for r in rows]
        result[field + "_upsert"] = [r for r in rows if prior.get(r["id"]) != r]
    for field in ("routes", "aliases", "series", "claude", "overflow", "controls"):
        if previous.get(field) != current.get(field):
            result[field] = current.get(field)
    return "delta", result


def _identity(path):
    try:
        s = os.stat(path, follow_symlinks=False)
        return s.st_ino, s.st_mtime_ns, s.st_size
    except OSError:
        return None


def serve(handler, minutes=15, *, authorized=lambda: True, duration=240, interval=.25):
    """Called only after the admin's existing Origin/session gate; never public."""
    if not _STREAM_SLOTS.acquire(blocking=False):
        return handler._json({"ok": False, "error": "Live stream capacity reached; polling remains available."}, 429)
    try:
        handler.close_connection = True
        handler.connection.settimeout(5)
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
        handler.send_header("Cache-Control", "no-store, no-transform")
        handler.send_header("X-Accel-Buffering", "no")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.send_header("Connection", "close")
        handler.end_headers()
        handler.wfile.write(b"retry: 1500\n\n")
        handler.wfile.flush()
        path = Path(os.environ.get("CAPACITY_OBSERVATORY_PATH", str(capacity_router.DEFAULT_PATH)))
        previous, identity = None, object()
        deadline = time.monotonic() + max(1, min(240, duration))
        heartbeat, auth_at = 0.0, 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - auth_at >= 5:
                if not authorized():
                    handler.wfile.write(b"event: auth-expired\ndata: {}\n\n")
                    handler.wfile.flush()
                    return
                auth_at = now
            current_identity = _identity(path)
            if current_identity != identity:
                current = capacity_router.panel(minutes, path=path)
                event, body = delta(previous, current)
                event_id = str(current.get("epoch") or "unavailable") + ":" + str(current.get("sequence", 0))
                payload = json.dumps(body, separators=(",", ":"), allow_nan=False).encode()
                handler.wfile.write(b"event: " + event.encode() + b"\nid: " + event_id.encode() + b"\ndata: " + payload + b"\n\n")
                handler.wfile.flush()
                previous, identity = current, current_identity
                heartbeat = now
            elif now - heartbeat >= 10:
                handler.wfile.write(b": heartbeat\n\n")
                handler.wfile.flush()
                heartbeat = now
            time.sleep(max(.1, interval))
    except (BrokenPipeError, ConnectionError, OSError, TimeoutError):
        # Closing a tab, expired session or slow reader is not an inference error.
        return
    finally:
        _STREAM_SLOTS.release()
