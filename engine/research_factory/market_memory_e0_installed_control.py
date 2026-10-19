"""Fixed administrator inspection of an installed E0 control selection.

The trust origin is protected deployment plus the existing authenticated OS
administrator, not self-consistent JSON or a caller's path/hash/permission flag.
The public entry accepts only a study identity and uses fixed production paths.
Private helpers are test/composition seams inside that trusted process, not an
authorization API or a sandbox against a malicious administrator.

This implements selected CONTROL metadata inspection only. It never loads
domain payloads, reservations, labels, annotations or provider output; never
initializes, publishes, repairs or activates a study; and never infers genuine
reviewer independence from a metadata reference. Missing selection fails closed.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from . import market_memory_contextual_registration as control
from .market_memory_e0_access_history import (
    MAX_ACCESS_HISTORY_BYTES, MAX_ACCESS_RECORDS, validate_access_history,
)

INSTALLED_ROOT = Path("/opt/macro")
CONTROL_ROOT = INSTALLED_ROOT / "data/research_factory/market_memory_e0"
SELECTED_SCHEMA = "research_factory.market_memory_e0_selected_control.v1"
_CONTROL_KEYS = {"registration": ("registration", "study_id"),
                 "closure": ("prelabel_closure", "closure_id"),
                 "publication": ("publication", "publication_id"),
                 "installation": ("installed_binding", "installation_id"),
                 "access": ("access_state", "access_state_id")}
_MODULE_PATH = "engine/research_factory/market_memory_e0_installed_control.py"
_SOURCE_PATHS = (
    "engine/__init__.py",
    "scripts/inspect_market_memory_e0_control.py",
    "engine/research_factory/__init__.py", "engine/research_factory/schema.py",
    "engine/research_factory/state.py", "engine/research_factory/ledger.py",
    "engine/research_factory/codegen_boundary.py",
    "engine/research_factory/market_memory_contextual_registration.py",
    "engine/research_factory/market_memory_e0_access_history.py",
    "engine/research_factory/market_memory_e0_reservations.py",
    _MODULE_PATH,
) + tuple(f"contracts/market_memory/e0_{kind}.v1.schema.json" for kind in control.KINDS)


class E0InstalledControlError(ValueError):
    """Stable reason only. No paths, raw exception text or private bodies."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise E0InstalledControlError(reason)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
            info.st_mode, info.st_uid, info.st_nlink)


@contextmanager
def _directory(path: Path, *, private: bool):
    """Hold every nonsymlink ancestor and recheck names before releasing them."""
    _require(path.is_absolute() and all(p not in (".", "..") for p in path.parts),
             "absolute_metadata_path_required")
    chain = []
    try:
        current = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        chain.append((current, None, None))
        for component in path.parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=current)
            chain.append((child, current, component))
            current = child
        for descriptor, _parent, _name in chain:
            info = os.fstat(descriptor)
            _require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, os.geteuid())
                     and not stat.S_IMODE(info.st_mode) & 0o022, "unsafe_metadata_ancestor")
        if private:
            info = os.fstat(current)
            _require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700,
                     "private_metadata_directory_required")
        yield current
        for descriptor, parent, name in chain[1:]:
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            held = os.fstat(descriptor)
            _require(held.st_uid in (0, os.geteuid()) and not stat.S_IMODE(held.st_mode) & 0o022,
                     "unsafe_metadata_ancestor")
            if private and descriptor == current:
                _require(held.st_uid == os.geteuid() and stat.S_IMODE(held.st_mode) == 0o700,
                         "private_metadata_directory_required")
            _require((held.st_dev, held.st_ino) == (named.st_dev, named.st_ino),
                     "metadata_directory_changed")
    except OSError as exc:
        raise E0InstalledControlError("metadata_directory_unavailable") from exc
    finally:
        for descriptor, _parent, _name in reversed(chain):
            os.close(descriptor)


def _read(descriptor: int, name: str, limit: int, *, private=True) -> bytes:
    _require("/" not in name and name not in ("", ".", ".."), "metadata_filename_invalid")
    opened = None
    try:
        opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                         dir_fd=descriptor)
        before = os.fstat(opened)
        mode = stat.S_IMODE(before.st_mode)
        _require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid()
                 and before.st_nlink == 1 and (mode == 0o600 if private else not mode & 0o022),
                 "unsafe_metadata_file")
        _require((0 < before.st_size <= limit) if private else (0 <= before.st_size <= limit),
                 "metadata_file_byte_limit")
        body = bytearray()
        while len(body) <= limit:
            chunk = os.read(opened, min(65536, limit + 1 - len(body)))
            if not chunk:
                break
            body.extend(chunk)
        after = os.fstat(opened)
        named = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        _require(_identity(before) == _identity(after) == _identity(named)
                 and len(body) == before.st_size, "metadata_file_changed")
        return bytes(body)
    except OSError as exc:
        raise E0InstalledControlError("metadata_file_unavailable") from exc
    finally:
        if opened is not None:
            os.close(opened)


def _verify_source(root: Path, commit: str) -> None:
    """Selected source identity must equal installed bytes; never fetch Git data."""
    _require(type(commit) is str and re.fullmatch(r"[a-f0-9]{40}", commit) is not None,
             "selected_source_commit_invalid")
    environment = {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
                   "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1",
                   "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                   "GIT_ALLOW_PROTOCOL": ""}
    try:
        # ls-tree also accepts a raw tree OID. A matching tree is not the
        # selected commit identity promised by the installed-control contract.
        kind = subprocess.run(
            ["/usr/bin/git", "-C", str(root), "cat-file", "-t", commit],
            capture_output=True, timeout=10, check=True, env=environment)
        _require(kind.stdout == b"commit\n" and not kind.stderr,
                 "selected_source_commit_invalid")
        result = subprocess.run(
            ["/usr/bin/git", "-C", str(root), "ls-tree", "-rz", commit, "--", *_SOURCE_PATHS],
            capture_output=True, timeout=10, check=True,
            env=environment)
    except (OSError, subprocess.SubprocessError) as exc:
        raise E0InstalledControlError("selected_source_unavailable") from exc
    _require(not result.stderr and len(result.stdout) <= 65536, "selected_source_listing_invalid")
    expected = {}
    try:
        for row in result.stdout.rstrip(b"\0").split(b"\0"):
            metadata, path = row.split(b"\t")
            mode, kind, digest = metadata.split()
            _require(kind == b"blob" and mode in (b"100644", b"100755"), "selected_source_type_invalid")
            expected[path.decode()] = digest.decode()
    except (ValueError, UnicodeError) as exc:
        raise E0InstalledControlError("selected_source_listing_invalid") from exc
    _require(set(expected) == set(_SOURCE_PATHS), "selected_source_closure_incomplete")
    for relative, expected_digest in expected.items():
        path = root / relative
        with _directory(path.parent, private=False) as descriptor:
            body = _read(descriptor, path.name, 512 * 1024, private=False)
        digest = hashlib.sha1(f"blob {len(body)}\0".encode() + body).hexdigest()
        _require(digest == expected_digest, "installed_source_changed")


def _load_selected_control(directory: Path, study_id: str, verify_source, *, clock) -> dict:
    """Trusted internal composition. Public entry binds every argument itself."""
    _require(type(study_id) is str and control._ID.fullmatch(study_id) is not None,
             "study_identity_invalid")
    with _directory(directory, private=True) as descriptor:
        selected_bytes = _read(descriptor, "SELECTED.json", 16384)
        selected = control._domain_json(selected_bytes)
        _require(type(selected) is dict and set(selected) ==
                 {"schema", "study_id", "source_commit", "control_refs"}, "selected_control_shape_invalid")
        _require(control._snapshot(selected)[1] == selected_bytes
                 and selected["schema"] == SELECTED_SCHEMA and selected["study_id"] == study_id,
                 "selected_control_identity_invalid")
        refs = selected["control_refs"]
        _require(type(refs) is dict and set(refs) == set(_CONTROL_KEYS), "selected_control_refs_invalid")
        _require(verify_source(selected["source_commit"]) is None, "source_verifier_contract")
        cached = {}
        total = 0

        def load(ref, kind, identity):
            nonlocal total
            ref = control._domain_reference(ref)
            _require(ref["schema"] == control.SCHEMAS[kind]
                     and ref["bytes"] <= control.MAX_CONTROL_BYTES, "control_reference_kind_invalid")
            digest = ref["sha256"]
            if digest not in cached:
                body = _read(descriptor, digest + ".json", control.MAX_CONTROL_BYTES)
                total += len(body)
                _require(total <= MAX_ACCESS_HISTORY_BYTES, "selected_control_byte_limit")
                cached[digest] = body
            body = cached[digest]
            _require(len(body) == ref["bytes"] and hashlib.sha256(body).hexdigest() == digest,
                     "selected_control_bytes_mismatch")
            record = control.parse_e0_control_record(body, kind=kind)
            _require(record[identity] == ref["object_id"], "selected_control_object_mismatch")
            return record, body

        records = {key: load(refs[key], *definition)[0] for key, definition in _CONTROL_KEYS.items()}
        _require(records["registration"]["study_id"] == study_id, "selected_study_mismatch")
        now = clock()
        control.validate_e0_control_join(**records, as_of=now)
        reverse = []
        seen = set()
        ref = refs["access"]
        while ref is not None:
            _require(ref["sha256"] not in seen and len(reverse) < MAX_ACCESS_RECORDS,
                     "access_history_cycle_or_limit")
            seen.add(ref["sha256"])
            state, body = load(ref, "access_state", "access_state_id")
            reverse.append(body)
            ref = state["previous_state_ref"]
        _require(verify_source(selected["source_commit"]) is None, "source_verifier_contract")
        _require(_read(descriptor, "SELECTED.json", 16384) == selected_bytes,
                 "selected_control_changed")
        final_now = clock()
        _require(control._clock(final_now) >= control._clock(now), "owner_clock_reversed")
        joined = control.validate_e0_control_join(**records, as_of=final_now)
        checked = validate_access_history(installation=records["installation"],
                                          history=list(reversed(reverse)), as_of=final_now)
        return {"schema": "research_factory.market_memory_e0_installed_control_inspection.v1",
                "authority": "display_only", "study_id": study_id,
                "source_commit": selected["source_commit"], "metadata_consistent": joined["metadata_consistent"],
                "access_history": checked, "domain_payloads_read": False,
                "reservation_store_read": False, "labels_read": False,
                "provider_invoked": False, "runtime_writes": False, "operational_admission": False}


def inspect_selected_control(study_id: str) -> dict:
    """Read one fixed private selection as the deployed OS administrator."""
    _require(sys.platform == "linux" and os.geteuid() == 0
             and Path(__file__).resolve() == INSTALLED_ROOT / _MODULE_PATH,
             "installed_administrator_entry_required")
    _verify_loaded_sources()
    _require(type(study_id) is str and control._ID.fullmatch(study_id) is not None,
             "study_identity_invalid")
    directory = CONTROL_ROOT / hashlib.sha256(study_id.encode()).hexdigest()
    return _load_selected_control(directory, study_id,
                                  lambda commit: _verify_source(INSTALLED_ROOT, commit),
                                  clock=lambda: datetime.now(timezone.utc).isoformat(
                                      timespec="microseconds").replace("+00:00", "Z"))


def _verify_loaded_sources() -> None:
    """Match executed project modules to the source files the owner verifies."""
    for relative in _SOURCE_PATHS:
        if not relative.startswith("engine/") or not relative.endswith(".py"):
            continue
        name = relative.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
        module = sys.modules.get(name)
        # The code-generation guard is in the source dependency closure but
        # is loaded lazily by unrelated Factory functions, not this inspector.
        if module is None and name == "engine.research_factory.codegen_boundary":
            continue
        origin = getattr(module, "__file__", None)
        _require(type(origin) is str and Path(origin).resolve() == INSTALLED_ROOT / relative,
                 "loaded_source_origin_invalid")
