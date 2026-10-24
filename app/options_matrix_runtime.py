"""Deployment capture on existing Matrix/identity/registry interfaces, no grants.

Startup installs a concrete lazy reader. Only authenticated requests read files
or the explicitly configured immutable R2 object. Missing enrollment refuses;
config.yml supplies audited bindings, never request data or policy-derived facts.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import threading
import time
import urllib.request
from urllib.parse import urlsplit
from datetime import datetime, timezone

from engine.options_matrix_retention import MAX_MATRIX_BYTES, SnapshotReference, verify_snapshot


class MatrixCaptureUnavailable(RuntimeError):
    """Safe named missing fact for server diagnostics, never a rights verdict."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _fail(code):
    raise MatrixCaptureUnavailable(code)


def _budget(deadline, monotonic):
    if monotonic() >= deadline:
        _fail("capture_deadline_exceeded")


def _regular_bytes(repo, relative, limit, deadline, monotonic=time.monotonic):
    """Bounded regular-file read under trusted repo, no symlink/FIFO traversal.

    Checks an elapsed budget between <=64KiB local syscalls. This cannot interrupt
    an OS/filesystem stall; the HTTP owner separately drops late thread results.
    """
    parts = relative.split("/")
    if any(p in ("", ".", "..") or "\\" in p or any(ord(c) < 32 for c in p) for p in parts):
        _fail("capture_path_invalid")
    directory = fd = None
    try:
        _budget(deadline, monotonic)
        directory = os.open(repo, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for part in parts[:-1]:
            _budget(deadline, monotonic)
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
            _fail("capture_file_invalid_or_oversize")
        body = bytearray(info.st_size)
        offset = 0
        while offset < len(body):
            _budget(deadline, monotonic)
            part = os.read(fd, min(65536, len(body) - offset))
            if not part:
                _fail("capture_file_changed")
            body[offset:offset+len(part)] = part
            offset += len(part)
        _budget(deadline, monotonic)
        if os.read(fd, 1):
            _fail("capture_file_changed")
        after = os.fstat(fd)
        if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
                info.st_size, info.st_mtime_ns, info.st_ctime_ns):
            _fail("capture_file_changed")
        _budget(deadline, monotonic)
        return bytes(body)
    except FileNotFoundError:
        _fail("capture_file_missing:" + relative.split("/")[-1])
    except OSError:
        _fail("capture_file_unreadable")
    finally:
        if fd is not None:
            os.close(fd)
        if directory is not None:
            os.close(directory)


def _yaml(raw):
    import yaml

    class UniqueLoader(yaml.SafeLoader):
        pass

    def unique(loader, node):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=True)
            if key in result:
                _fail("configuration_duplicate_key")
            result[key] = loader.construct_object(value_node, deep=True)
        return result

    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique)
    try:
        value = yaml.load(raw.decode("utf-8"), Loader=UniqueLoader)
        if type(value) is not dict:
            _fail("configuration_invalid")
        return value
    except MatrixCaptureUnavailable:
        raise
    except Exception:
        _fail("configuration_invalid")


def _configuration(config):
    from lib.dataos.registry import RIGHTS_KEYS

    row = config.get("options_matrix_display")
    keys = {"source_mode", "root", "vendor", "dataset_id", "dataset_version", "source_family",
            "inputs", "required_rights_rationale", "evidence_sha256", "registry_revision", "registry_sha256"}
    if type(row) is not dict:
        _fail("configuration_missing:options_matrix_display")
    missing = sorted(keys - set(row))
    if missing:
        _fail("configuration_missing:" + ",".join(missing))
    if set(row) != keys:
        _fail("configuration_unknown_fields")
    if row["source_mode"] not in ("local_retained", "r2_public"):
        _fail("source_mode_unavailable")
    # The existing native identity writer admits SPY/thetadata only.
    if row["root"] != "SPY" or row["vendor"] != "thetadata":
        _fail("identity_scope_unavailable")
    for key in keys - {"inputs", "required_rights_rationale"}:
        value = row[key]
        if type(value) is not str or not 0 < len(value) <= 256 or any(ord(c) < 32 for c in value):
            _fail("configuration_invalid:" + key)
    if any(not re.fullmatch(r"[0-9a-f]{64}", row[k]) for k in ("evidence_sha256", "registry_sha256")):
        _fail("configuration_invalid:digest_pin")
    inputs = row["inputs"]
    if type(inputs) is not dict or set(inputs) != {"oi", "eod", "greeks"}:
        _fail("native_input_roles_unavailable")
    if any(type(v) is not dict or set(v) != {"dataset_id", "version"} or
           any(type(x) is not str or not 0 < len(x) <= 256 for x in v.values()) for v in inputs.values()):
        _fail("native_input_roles_invalid")
    rights = row["required_rights_rationale"]
    if type(rights) is not dict or not rights or not set(rights) <= set(RIGHTS_KEYS) or any(
            type(v) is not str or not v.strip() or len(v) > 256 for v in rights.values()):
        _fail("audited_output_rights_unavailable")
    return row


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _public_retained(base, ref, deadline, monotonic=time.monotonic, opener=None):
    try:
        parsed = urlsplit(base)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or any(c.isspace() for c in base)):
            _fail("retained_origin_unavailable")
        _budget(deadline, monotonic)
        request = urllib.request.Request(base.rstrip("/") + "/" + ref.key,
            headers={"User-Agent": "mastermind-feed/1.0", "Accept-Encoding": "identity"})
        # No ambient proxy credentials, cookies, bearer or redirect follow.
        opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        with opener.open(request, timeout=2) as response:
            _budget(deadline, monotonic)
            if (response.status != 200 or response.headers.get("Content-Encoding")
                    or response.geturl() != request.full_url):
                _fail("retained_response_invalid")
            lengths = response.headers.get_all("Content-Length") or []
            if len(lengths) != 1 or lengths[0] != str(ref.byte_length):
                _fail("retained_length_mismatch")
            body = bytearray(ref.byte_length)
            offset = 0
            while offset < len(body):
                _budget(deadline, monotonic)
                # read1 performs one underlying socket read, avoiding unbounded
                # drip accumulation inside a buffered read(size).
                part = response.read1(min(65536, len(body) - offset))
                _budget(deadline, monotonic)
                if not part or len(part) > len(body) - offset:
                    _fail("retained_length_mismatch")
                body[offset:offset+len(part)] = part
                offset += len(part)
            if response.read1(1):
                _fail("retained_length_mismatch")
            _budget(deadline, monotonic)
            return bytes(body)
    except MatrixCaptureUnavailable:
        raise
    except Exception:
        _fail("retained_read_unavailable")


class DeployedMatrixCapture:
    def __init__(self, repo):
        self.repo = Path(repo)
        # Held by actual work, including a reader whose HTTP owner timed out.
        # This bounds retained native threads; it queues/retries nothing.
        self._slots = threading.BoundedSemaphore(2)

    def __call__(self, ref):
        if not self._slots.acquire(blocking=False):
            _fail("capture_capacity_unavailable")
        try:
            return self._capture(ref)
        finally:
            self._slots.release()

    def _capture(self, ref):
        # Contract/identity dependencies are mandatory at capture, not startup.
        from engine.intelligence_workspace.entity import IdentityArtifactRead
        from engine.intelligence_workspace.options_matrix_context import MatrixDatasetBinding
        from engine.intelligence_workspace.options_matrix_delivery import (
            MatrixDisplaySource, MatrixInputContract, bind_matrix_contracts, capture_matrix_provenance,
        )
        from lib.dataos.registry import DatasetContract, Registry
        from app.options_matrix_http import MatrixHTTPInputs
        from scripts.observe_options_matrix_publication import capture_spy_identity_inputs

        if type(ref) is not SnapshotReference:
            _fail("snapshot_reference_invalid")
        # Validate before building a path or allocating the expected response.
        from engine.options_matrix_retention import _checked_ref
        _checked_ref(ref)
        deadline = time.monotonic() + 6
        read = lambda path, limit: _regular_bytes(self.repo, str(Path(path).relative_to(self.repo)), limit, deadline)
        config = _yaml(read(self.repo / "config.yml", 2 * 1024 * 1024))
        row = _configuration(config)
        if ref.root != row["root"]:
            _fail("identity_scope_unavailable")
        registry_raw = read(self.repo / "config/dataset_registry.yml", 2 * 1024 * 1024)
        if hashlib.sha256(registry_raw).hexdigest() != row["registry_sha256"]:
            _fail("native_registry_digest_mismatch")
        payload = _yaml(registry_raw)
        if type(payload.get("datasets")) is not list:
            _fail("native_registry_unavailable")
        registry = Registry(DatasetContract.from_mapping(item) for item in payload["datasets"])
        binding = MatrixDatasetBinding(ref, row["dataset_id"], row["dataset_version"], row["vendor"], row["source_family"])
        inputs = tuple(MatrixInputContract(role, value["dataset_id"], value["version"]) for role, value in row["inputs"].items())
        # Resolve configured contracts before any source read; no guessed IDs.
        from engine.intelligence_workspace.options_source_use import _resolve_contract
        try:
            _resolve_contract(registry, binding.dataset_id, binding.vendor)
            for item in inputs:
                _resolve_contract(registry, item.dataset_id, binding.vendor)
        except Exception:
            _fail("native_produced_contracts_unavailable")
        if row["source_mode"] == "local_retained":
            raw = read(self.repo / "data/live_flow_out/options_matrix/history" / ref.root / (ref.sha256 + ".json"), MAX_MATRIX_BYTES)
        else:
            base = os.environ.get("R2_PUBLIC_BASE") or config.get("r2_data_plane", {}).get("public_base")
            if type(base) is not str or not base:
                _fail("retained_origin_unavailable")
            raw = _public_retained(base, ref, deadline)
        verify_snapshot(ref, raw)
        bind_matrix_contracts(capture_matrix_provenance(ref, raw), binding, inputs, registry)
        matrix = IdentityArtifactRead(raw, hashlib.sha256(raw).hexdigest(), datetime.now(timezone.utc))
        identity = capture_spy_identity_inputs(self.repo, vendor=row["vendor"], read_bytes=read)
        _budget(deadline, time.monotonic)
        source = MatrixDisplaySource(registry, binding, inputs, tuple(row["required_rights_rationale"].items()),
                                     row["evidence_sha256"], row["registry_revision"], self.repo)
        return MatrixHTTPInputs(matrix, identity["aliases"], identity["security_master"], identity["root_evidence"], source)


def install_matrix_display_runtime(app, *, repo):
    """Install concrete lazy capture without reading credentials/files/network."""
    from app.options_matrix_http import MatrixHTTPRuntime
    app.state.options_matrix_display_runtime = MatrixHTTPRuntime(DeployedMatrixCapture(repo))
