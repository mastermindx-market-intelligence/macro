"""engine.neuralweb.capability_broker — Metabolism capability broker (F3, §3 of masterplan).

Sibling of governance.py with the same NEVER-RAISE contract.

The broker knows WHAT capabilities exist and WHO is allowed to use them.
It never reads, holds, or returns secret values — only ref names.

REDLINE (the single unforgivable defect):
    A secret value MUST NEVER appear in a git artifact.  This module enforces
    that at every layer:
      - resolve() returns the ref NAME ('CLAUDE_CODE_OAUTH_TOKEN'), never the value.
      - The caller reads os.environ[ref_name] independently — the broker is not in
        that path and cannot see the value.
      - audit() records attribution from the Actions env (run_id, actor, sha) but
        no secret values.
      - CI (check_capability_redline.py) scans this file for high-entropy strings.

NEVER-RAISE CONTRACT (mirrors governance.py):
    resolve() and audit() catch ALL exceptions, log a warning, and return a safe
    fallback.  They NEVER propagate exceptions to the caller.
    A broker failure must never abort the lane that invoked it.

Usage:
    from engine.neuralweb.capability_broker import resolve, audit

    result = resolve("claude_code_oauth", lane="whitehouse-sentinel")
    if not result["allowed"]:
        print(f"Capability denied: {result['reason']}")
        sys.exit(1)

    # Read the actual value yourself -- the broker never touches it:
    # (do not assign here in example: read os.environ[result["ref_name"]] at call site)

    # Record this use:
    audit(
        capability_id="claude_code_oauth",
        lane="whitehouse-sentinel",
        workflow="whitehouse-sentinel",
    )
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_MANIFEST_REL = "config/capability_manifest.yml"
_AUDIT_REL = "data/neuralweb/capability_audit.jsonl"
_SCHEMA = "neuralweb.capability_broker.v1"


# ── Path helpers (mirrors governance.py pattern) ──────────────────────────────

def _repo_root() -> Path:
    """Auto-detect the repository root from this file's location."""
    # engine/neuralweb/capability_broker.py → repo root is two levels up
    return Path(__file__).resolve().parent.parent.parent


def _manifest_path(root: Path | None = None) -> Path:
    base = root if root is not None else _repo_root()
    return base / _MANIFEST_REL


def _audit_path(root: Path | None = None) -> Path:
    base = root if root is not None else _repo_root()
    return base / _AUDIT_REL


# ── Coherent reference-manifest read (no retained grants, NEVER-RAISE) ────────

_MAX_MANIFEST_BYTES = 1_048_576
_MAX_MANIFEST_NODES = 32768
_MAX_MANIFEST_DEPTH = 32
_REF_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,255}\Z")


def _manifest_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


def _parse_manifest_bytes(raw: bytes) -> dict[str, Any]:
    """Decode one explicit source document, not executable YAML or secrets.

    Alias/merge indirection is refused in this permission-bearing manifest.
    The current source format uses explicit rows. Counts and nesting are bound
    during composition, before constructors can expand a malicious graph.
    """
    import yaml  # optional dependency; the public boundary remains NEVER-RAISE

    class ManifestLoader(yaml.SafeLoader):
        def __init__(self, stream):
            super().__init__(stream)
            self._manifest_depth = 0
            self._manifest_nodes = 0

        def compose_node(self, parent, index):
            if self.check_event(yaml.events.AliasEvent):
                raise ValueError("manifest_alias_refused")
            self._manifest_nodes += 1
            self._manifest_depth += 1
            try:
                if (self._manifest_nodes > _MAX_MANIFEST_NODES
                        or self._manifest_depth > _MAX_MANIFEST_DEPTH):
                    raise ValueError("manifest_shape_over_budget")
                return super().compose_node(parent, index)
            finally:
                self._manifest_depth -= 1

        def construct_mapping(self, node, deep=False):
            if not isinstance(node, yaml.nodes.MappingNode):
                raise ValueError("manifest_mapping_required")
            result = {}
            for key_node, value_node in node.value:
                if key_node.tag == "tag:yaml.org,2002:merge":
                    raise ValueError("manifest_merge_refused")
                key = self.construct_object(key_node, deep=deep)
                if type(key) is not str or key in result:
                    raise ValueError("manifest_mapping_key_invalid")
                result[key] = self.construct_object(value_node, deep=deep)
            return result

    loader = ManifestLoader(raw.decode("utf-8"))
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    if type(data) is not dict:
        raise ValueError("manifest_root_invalid")
    # Keep the existing owner metadata and lane rules. Do not normalize a
    # malformed scalar to an empty/healthy capability observation.
    pending = [data]
    count = 0
    while pending:
        value = pending.pop()
        count += 1
        if count > _MAX_MANIFEST_NODES:
            raise ValueError("manifest_shape_over_budget")
        if type(value) is dict:
            pending.extend(value.values())
        elif type(value) is list:
            pending.extend(value)
        elif type(value) is float and not math.isfinite(value):
            raise ValueError("manifest_nonfinite")
        elif type(value) is str:
            value.encode("utf-8", errors="strict")
    capabilities = data.get("capabilities")
    if type(capabilities) is not list or len(capabilities) > 2048:
        raise ValueError("manifest_capabilities_invalid")
    seen = set()
    for row in capabilities:
        if type(row) is not dict:
            raise ValueError("manifest_capability_invalid")
        identity = row.get("capability_id")
        if (type(identity) is not str or not 1 <= len(identity) <= 256
                or identity != identity.strip() or identity in seen
                or any(ord(char) < 32 for char in identity)):
            raise ValueError("manifest_capability_identity_invalid")
        seen.add(identity)
        ref = row.get("secret_ref")
        if ref is not None and (type(ref) is not str or _REF_NAME.fullmatch(ref) is None):
            raise ValueError("manifest_reference_name_invalid")
    return data


def load_manifest_source(path: Path) -> dict[str, Any]:
    """Read the caller's exact incumbent manifest; never cache a grant.

    Used by the capability broker and key pool without changing either
    caller's source-root selection. Missing, malformed, oversized or moving
    source returns {}. Every call gets detached data; no caller can poison
    another read. This resolves no credential and performs no rotation/write.
    """
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode)
                or not 0 < before.st_size <= _MAX_MANIFEST_BYTES):
            raise ValueError("manifest_source_invalid")
        chunks, size = [], 0
        while True:
            chunk = os.read(descriptor, min(65536, _MAX_MANIFEST_BYTES + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > _MAX_MANIFEST_BYTES:
                raise ValueError("manifest_source_over_budget")
            chunks.append(chunk)
        expected = _manifest_identity(before)
        if (size != before.st_size
                or _manifest_identity(os.fstat(descriptor)) != expected
                or _manifest_identity(os.stat(path, follow_symlinks=False)) != expected):
            raise ValueError("manifest_source_changed")
        data = _parse_manifest_bytes(b"".join(chunks))
        # Recheck after parsing/validation, not merely after the byte read.
        if (_manifest_identity(os.fstat(descriptor)) != expected
                or _manifest_identity(os.stat(path, follow_symlinks=False)) != expected):
            raise ValueError("manifest_source_changed")
        return data
    except Exception:  # noqa: BLE001 — preserve the incumbent NEVER-RAISE boundary
        # Do not leak filenames, parser snippets, environment refs or contents.
        log.warning("capability_broker: manifest source unavailable or invalid")
        return {}
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _load_manifest(root: Path | None = None) -> dict[str, Any]:
    """Read current reference policy on each new operation; no stale fallback."""
    try:
        return load_manifest_source(_manifest_path(root))
    except Exception:  # noqa: BLE001
        log.warning("capability_broker: manifest selection unavailable")
        return {}


def _find_capability(capability_id: str, root: Path | None = None) -> dict[str, Any] | None:
    """Return the manifest row for capability_id, or None if not found."""
    try:
        manifest = _load_manifest(root)
        for cap in manifest.get("capabilities", []):
            if isinstance(cap, dict) and cap.get("capability_id") == capability_id:
                return cap
    except Exception as exc:  # noqa: BLE001
        log.warning("capability_broker._find_capability: %s", exc)
    return None


# ── resolve() ─────────────────────────────────────────────────────────────────

def resolve(
    capability_id: str,
    lane: str,
    root: Path | None = None,
) -> dict[str, Any]:
    """Resolve a capability request.

    Returns the ref name (env-var name) and an allowed bool.
    NEVER returns the secret value — only the name.
    NEVER raises — returns a safe denial dict on any error.

    Parameters
    ----------
    capability_id : str
        The capability to look up (e.g. 'claude_code_oauth').
    lane : str
        The calling workflow lane (e.g. 'whitehouse-sentinel').
    root : Path | None
        Repository root for test isolation (None = production paths).

    Returns
    -------
    dict with keys:
        ref_name (str | None)   — the env-var name, or None if not found
        allowed (bool)          — True if the lane is allowed to use this capability
        reason (str)            — human-readable explanation
    """
    try:
        cap = _find_capability(capability_id, root)

        if cap is None:
            return {
                "ref_name": None,
                "allowed": False,
                "reason": (
                    f"Capability '{capability_id}' not found in manifest. "
                    f"Register it in {_MANIFEST_REL} before use."
                ),
            }

        ref_name: str | None = cap.get("secret_ref")
        if not ref_name:
            return {
                "ref_name": None,
                "allowed": False,
                "reason": (
                    f"Capability '{capability_id}' has no secret_ref in manifest — "
                    f"manifest entry is incomplete."
                ),
            }

        # Check kill_state — a killed capability is always denied
        kill_state = cap.get("kill_state", "active")
        if kill_state != "active":
            return {
                "ref_name": ref_name,
                "allowed": False,
                "reason": (
                    f"Capability '{capability_id}' is kill_state='{kill_state}' — "
                    f"denied.  Reset kill_state in the manifest with operator approval."
                ),
            }

        # Check lane allowlist
        allowed_lanes: list[str] = cap.get("allowed_lanes") or []
        if lane not in allowed_lanes:
            return {
                "ref_name": ref_name,
                "allowed": False,
                "reason": (
                    f"Lane '{lane}' is not in the allowed_lanes for capability "
                    f"'{capability_id}' (allowed: {allowed_lanes}).  "
                    f"Update the manifest with operator approval to add this lane."
                ),
            }

        return {
            "ref_name": ref_name,
            "allowed": True,
            "reason": (
                f"Capability '{capability_id}' resolved for lane '{lane}': "
                f"ref_name='{ref_name}' (value NOT returned — read os.environ[ref_name] "
                f"directly)."
            ),
        }

    except Exception as exc:  # noqa: BLE001
        log.warning("capability_broker.resolve failed for %s/%s: %s", capability_id, lane, exc)
        return {
            "ref_name": None,
            "allowed": False,
            "reason": (
                f"capability_broker.resolve raised an exception for '{capability_id}' "
                f"in lane '{lane}': {exc}. Denied by fail-closed policy."
            ),
        }


# ── audit() ──────────────────────────────────────────────────────────────────

def audit(
    capability_id: str,
    lane: str,
    workflow: str = "",
    root: Path | None = None,
) -> bool:
    """Append an audit row to data/neuralweb/capability_audit.jsonl.

    Captures attribution from the GitHub Actions environment.  Never captures
    or logs secret values.

    Parameters
    ----------
    capability_id : str
        The capability that was resolved and used.
    lane : str
        The calling workflow lane.
    workflow : str
        The workflow name (can also be read from GITHUB_WORKFLOW env).
    root : Path | None
        Repository root for test isolation.

    Returns
    -------
    bool
        True if the row was appended; False on any error.  NEVER raises.
    """
    try:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        run_id = os.environ.get("GITHUB_RUN_ID", "")
        wf = workflow or os.environ.get("GITHUB_WORKFLOW", "")
        actor = os.environ.get("GITHUB_ACTOR", "")
        sha = os.environ.get("GITHUB_SHA", "")

        # Deterministic event id (mirrors governance.py pattern)
        raw = f"{capability_id}|{lane}|{run_id}|{ts}"
        event_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

        row: dict[str, Any] = {
            "schema": _SCHEMA,
            "event_id": event_id,
            "ts": ts,
            "run_id": run_id,
            "workflow": wf,
            "actor": actor,
            "sha": sha,
            "capability_id": capability_id,
            "lane": lane,
        }

        p = _audit_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(row, separators=(",", ":"), default=str)
        with p.open("a") as fh:
            fh.write(line + "\n")
        return True

    except Exception as exc:  # noqa: BLE001
        log.warning(
            "capability_broker.audit failed for %s/%s: %s", capability_id, lane, exc
        )
        return False
