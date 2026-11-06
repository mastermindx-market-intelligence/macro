"""Shared Options Hub source read and single TTL cache for the HTTP and Brain consumers."""
from __future__ import annotations

import json
import hashlib
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import HTTPException

# --------------------------------------------------------------------------- #
# TTL cache (mirrors app/main.py _FLOW_CACHE pattern)
# --------------------------------------------------------------------------- #
_HUB_CACHE: dict[str, tuple[dict, float]] = {}
_HUB_CACHE_TTL = 30.0       # seconds
_HUB_UA = "mastermind-feed/1.0"

# --------------------------------------------------------------------------- #
# R2 base URL resolver (mirrors app/main.py _flow_r2_base)
# --------------------------------------------------------------------------- #

def _hub_r2_base() -> str:
    base = os.environ.get("R2_PUBLIC_BASE", "")
    if base:
        return base.rstrip("/")
    try:
        import yaml  # noqa: PLC0415
        _cfg_path = Path(os.environ.get("MACRO_REPO", "/opt/macro")) / "config.yml"
        if _cfg_path.exists():
            with open(_cfg_path) as f:
                c = yaml.safe_load(f)
            return (c.get("r2_data_plane", {}).get("public_base") or "").rstrip("/")
    except Exception:  # noqa: BLE001
        pass
    return ""


# --------------------------------------------------------------------------- #
# R2 read-through with TTL/stale fallback (mirrors app/main.py _flow_fetch)
# --------------------------------------------------------------------------- #

def fetch_hub(key: str, *, cache=None, base_provider=None) -> dict:
    """Fetch options_hub/<key> from R2 with TTL caching and stale fallback.

    Returns the parsed JSON dict. On failure returns last-cached dict with
    {"stale": true} merged. Raises HTTPException(503) only if never fetched.
    """
    if cache is None:
        cache = _HUB_CACHE
    cached = cache.get(key)
    now = time.monotonic()

    # Fresh cache hit
    if cached is not None and (now - cached[1]) < _HUB_CACHE_TTL:
        return cached[0]

    base = (base_provider or _hub_r2_base)()
    if not base:
        if cached:
            return {**cached[0], "stale": True}
        raise HTTPException(503, f"hub/{key}: R2 base URL not configured")

    url = f"{base}/options_hub/{key}"
    req = urllib.request.Request(url, headers={"User-Agent": _HUB_UA})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read()
            data: dict = json.loads(raw)
            # Acquisition identity only: hash ORIGINAL producer bytes, never this
            # router's reserialized response. It confers no retention/use rights.
            if key.startswith("gex/") and type(data) is dict:
                data.pop("_scenario_source_identity", None)
                if (data.get("schema") == "options_hub.gex/v1"
                        and key == f"gex/{data.get('root')}.json"
                        and type(data.get("asof")) is str and 0 < len(raw) <= 8 * 1024 * 1024):
                    data["_scenario_source_identity"] = {
                        "schema": "options_hub.acquired_bytes/v1", "kind": "gex",
                        "root": data["root"], "session": data["asof"][:10],
                        "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)}
        cache[key] = (data, now)
        return data
    except Exception:  # noqa: BLE001
        if cached:
            return {**cached[0], "stale": True}
        raise HTTPException(503, f"hub/{key} unavailable and no cached copy") from None


# --------------------------------------------------------------------------- #
# parameter sanitization helpers
# --------------------------------------------------------------------------- #

_ROOT_RE = re.compile(r"(?:[A-Z0-9^]{1,16}|[A-Z0-9]{1,10}[.-][A-Z0-9]{1,4})")


def _sanitize_root(root: str) -> str:
    """Uppercase, strip whitespace, validate against safe root pattern.

    Raises HTTPException(400) on invalid input to prevent path traversal.
    """
    root = root.strip().upper()
    if not _ROOT_RE.fullmatch(root):
        raise HTTPException(400, f"Invalid root symbol: {root!r}")
    return root


def read_vol(root: str) -> dict:
    return fetch_hub(f"vol/{_sanitize_root(root)}.json")
