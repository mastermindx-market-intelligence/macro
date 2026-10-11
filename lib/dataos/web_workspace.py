"""Bounded read projection over Data OS and explicitly bound data-only roots.

This module owns no dataset registry, collector, identity, execution queue or
publication state. Bindings are a host access allowlist; registry.py remains the
dataset-contract owner. A discovered file is not a production-qualified dataset.
No environment files are loaded, no network is used, and source files are opened
read-only through directory descriptors without following child symlinks.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import hashlib
import json
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from lib.dataos.registry import load_registry
from lib.dataos.web_readers import ReaderError, inspect_file, read_rows

MAX_RESPONSE_BYTES = 131072
MAX_DIRECTORY_ENTRIES = 30000
MAX_SEARCH_ENTRIES = 5000
READABLE_SUFFIXES = frozenset({".parquet", ".csv", ".json", ".jsonl", ".ndjson"})
HIDDEN_NAMES = frozenset({".git", ".env", ".ssh", ".aws", ".config"})
SENSITIVE_MARKERS = ("credential", "secret", "apikey", "api_key", "access_token",
                     "refresh_token", "private_key")


class WorkspaceError(Exception):
    """A bounded public error; never carries an underlying OS error or path."""
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclasses.dataclass(frozen=True)
class RootBinding:
    alias: str
    path: Path
    evidence_kind: str = "unqualified_snapshot"
    note: str = ""
    required_mount: Path | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.alias, str) or not self.alias or len(self.alias) > 64
                or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in self.alias)):
            raise ValueError("invalid root alias")
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise ValueError("root must be an absolute host-bound path")
        if self.required_mount is not None and (not isinstance(self.required_mount, Path) or not self.required_mount.is_absolute()):
            raise ValueError("required mount must be absolute")
        if self.evidence_kind not in {
            "unqualified_snapshot", "historical_archive", "research_sample",
            "research_capture", "raw_archive", "proposed_source",
        }:
            raise ValueError("invalid evidence kind")
        if not isinstance(self.note, str) or len(self.note) > 2000:
            raise ValueError("root note is too long")


def _json_default(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    raise TypeError("not JSON data")


def _version(s: os.stat_result) -> str:
    identity = [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]
    return "statv1:" + hashlib.sha256(json.dumps(identity).encode()).hexdigest()


def _parts(path: str, *, empty: bool = False) -> tuple[str, ...]:
    if not isinstance(path, str) or len(path) > 2048 or "\x00" in path or "\\" in path:
        raise WorkspaceError("PATH_REFUSED")
    if not path and empty:
        return ()
    parts = path.split("/")
    if (not parts or any(not p or p in {".", ".."} or p.startswith(".")
                         or p in HIDDEN_NAMES for p in parts)):
        raise WorkspaceError("PATH_REFUSED")
    if any(any(marker in p.lower() for marker in SENSITIVE_MARKERS) for p in parts):
        raise WorkspaceError("PATH_REFUSED")
    return tuple(parts)


def _bound_int(value: int, minimum: int, maximum: int, code: str = "INVALID_ARGUMENT") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise WorkspaceError(code)
    return value


class DataWorkspace:
    """Request-local observation service with host-supplied, fixed root bindings."""

    def __init__(self, roots: tuple[RootBinding, ...], registry_path: Path,
                 source_revision: str | None = None) -> None:
        if not roots or len(roots) > 32 or len({r.alias for r in roots}) != len(roots):
            raise ValueError("one to 32 unique roots required")
        self.roots = {root.alias: root for root in roots}
        self.registry_path = Path(registry_path)
        self.registry = load_registry(self.registry_path)
        if self.registry.duplicate_ids():
            raise ValueError("duplicate canonical dataset IDs")
        self.source_revision = source_revision

    def _root(self, alias: str) -> RootBinding:
        if not isinstance(alias, str):
            raise WorkspaceError("INVALID_ROOT_ALIAS")
        if alias not in self.roots:
            raise WorkspaceError("ROOT_NOT_BOUND")
        return self.roots[alias]

    def _result(self, **payload: Any) -> dict[str, Any]:
        result = {
            "schema_version": "mastermind.data_workspace/v1",
            "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "implementation_revision": self.source_revision,
            "source_access": "read_only",
            "production_qualification": "NOT_ESTABLISHED_BY_THIS_ADAPTER",
            **payload,
        }
        try:
            encoded = json.dumps(result, default=_json_default, allow_nan=False,
                                 separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError):
            raise WorkspaceError("INVALID_SOURCE_VALUE") from None
        if len(encoded.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise WorkspaceError("RESULT_TOO_LARGE_REDUCE_COLUMNS_OR_LIMIT")
        return json.loads(encoded)

    @contextmanager
    def _directory(self, root: RootBinding, parts: tuple[str, ...]) -> Iterator[int]:
        if root.required_mount is not None and not os.path.ismount(root.required_mount):
            raise WorkspaceError("REQUIRED_VOLUME_NOT_MOUNTED")
        fds: list[int] = []
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            fds.append(os.open(root.path, flags))
            root_identity = os.fstat(fds[0])
            for part in parts:
                fds.append(os.open(part, flags, dir_fd=fds[-1]))
            yield fds[-1]
            current = os.stat(root.path, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (root_identity.st_dev, root_identity.st_ino):
                raise WorkspaceError("ROOT_BINDING_CHANGED")
        except FileNotFoundError:
            raise WorkspaceError("SOURCE_NOT_FOUND") from None
        except PermissionError:
            raise WorkspaceError("SOURCE_INACCESSIBLE") from None
        except (NotADirectoryError, OSError):
            raise WorkspaceError("PATH_OR_SOURCE_REFUSED") from None
        finally:
            for fd in reversed(fds):
                os.close(fd)

    def _split_ref(self, ref: str) -> tuple[RootBinding, tuple[str, ...]]:
        if not isinstance(ref, str) or ":" not in ref:
            raise WorkspaceError("INVALID_DATA_REF")
        alias, relative = ref.split(":", 1)
        return self._root(alias), _parts(relative)

    @contextmanager
    def _file(self, ref: str, expected_version: str | None = None):
        root, parts = self._split_ref(ref)
        with self._directory(root, parts[:-1]) as parent:
            fd = None
            try:
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                    raise WorkspaceError("REGULAR_PRIVATE_FILE_REQUIRED")
                version = _version(before)
                if expected_version is not None and expected_version != version:
                    raise WorkspaceError("SOURCE_VERSION_MISMATCH")
                source = {
                    "ref": ref, "root_alias": root.alias, "relative_path": "/".join(parts),
                    "evidence_kind": root.evidence_kind, "limitations": root.note,
                    "file_bytes": before.st_size, "file_version": version,
                    "file_version_basis": "device_inode_size_mtime_ctime_not_content_hash",
                    "content_sha256": None,
                    "filesystem_mtime": dt.datetime.fromtimestamp(
                        before.st_mtime, dt.timezone.utc).isoformat(),
                    "filesystem_mtime_is_data_freshness": False,
                    "registry_admission": "NOT_INFERRED_FROM_FILE_PRESENCE",
                }
                with os.fdopen(fd, "rb") as stream:
                    fd = None
                    yield stream, source
                    after = os.fstat(stream.fileno())
                    current = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
                    if _version(after) != version or _version(current) != version:
                        raise WorkspaceError("SOURCE_CHANGED")
            except FileNotFoundError:
                raise WorkspaceError("SOURCE_NOT_FOUND") from None
            except PermissionError:
                raise WorkspaceError("SOURCE_INACCESSIBLE") from None
            except ReaderError as exc:
                raise WorkspaceError(exc.code) from None
            except OSError:
                raise WorkspaceError("PATH_OR_SOURCE_REFUSED") from None
            finally:
                if fd is not None:
                    os.close(fd)

    def _entries(self, fd: int, alias: str, path: str, cap: int):
        records: list[dict[str, Any]] = []
        complete = True
        with os.scandir(fd) as items:
            for examined, entry in enumerate(items):
                if examined >= cap:
                    complete = False
                    break
                try:
                    _parts(entry.name)
                except WorkspaceError:
                    continue
                s = entry.stat(follow_symlinks=False)
                kind = ("directory" if stat.S_ISDIR(s.st_mode) else
                        "file" if stat.S_ISREG(s.st_mode) else "refused_special_or_symlink")
                relative = "/".join(x for x in (path, entry.name) if x)
                records.append({
                    "ref": alias + ":" + relative, "name": entry.name, "kind": kind,
                    "format": Path(entry.name).suffix.lower() if kind == "file" else None,
                    "file_bytes": s.st_size if kind == "file" else None,
                    "file_version": _version(s),
                    "read_supported": kind == "file" and Path(entry.name).suffix.lower() in READABLE_SUFFIXES,
                })
        return sorted(records, key=lambda x: (x["kind"] != "directory", x["name"])), complete

    def search(self, query: str = "", limit: int = 30) -> dict[str, Any]:
        _bound_int(limit, 1, 100)
        if not isinstance(query, str) or len(query) > 256:
            raise WorkspaceError("INVALID_ARGUMENT")
        q = query.casefold()
        hits: list[dict[str, Any]] = []
        for contract in self.registry:
            row = dataclasses.asdict(contract)
            if not q or q in json.dumps(row, default=_json_default).casefold():
                hits.append({
                    "kind": "registered_contract", "ref": "registry:" + contract.dataset_id,
                    "dataset_id": contract.dataset_id, "owner": contract.owner,
                    "status": contract.status, "storage_declaration": contract.storage,
                    "temporal_profile": contract.temporal_profile,
                    "availability": "NOT_ESTABLISHED_BY_DECLARATION",
                })
        root_states = []
        for root in self.roots.values():
            state = {"root_alias": root.alias, "evidence_kind": root.evidence_kind, "note": root.note}
            try:
                with self._directory(root, ()) as fd:
                    entries, complete = self._entries(fd, root.alias, "", MAX_SEARCH_ENTRIES)
                state.update({"state": "PRESENT", "namespace_scan_complete": complete,
                              "namespace_entries_observed": len(entries)})
                for entry in entries:
                    if not q or q in (root.alias + " " + entry["name"]).casefold():
                        hits.append({**entry, "entry_kind": entry["kind"],
                                     "kind": "physical_namespace",
                                     "registry_admission": "NOT_INFERRED"})
            except WorkspaceError as exc:
                state.update({"state": exc.code, "namespace_scan_complete": False})
            root_states.append(state)
        return self._result(
            action="search", query=query, results=hits[:limit],
            matches_observed=len(hits), results_truncated=len(hits) > limit,
            discovery_scope="canonical_contracts_and_bound_root_top_level_namespaces",
            roots=root_states,
            note="Use browse for nested files. Root absence is local to this binding, not all production hosts.",
        )

    def browse(self, root: str, path: str = "", offset: int = 0,
               limit: int = 50, expected_directory_version: str | None = None) -> dict[str, Any]:
        if expected_directory_version is not None and (not isinstance(expected_directory_version, str) or len(expected_directory_version) > 80):
            raise WorkspaceError("INVALID_ARGUMENT")
        _bound_int(offset, 0, MAX_DIRECTORY_ENTRIES)
        _bound_int(limit, 1, 200)
        binding = self._root(root)
        with self._directory(binding, _parts(path, empty=True)) as fd:
            before = _version(os.fstat(fd))
            if expected_directory_version is not None and before != expected_directory_version:
                raise WorkspaceError("DIRECTORY_VERSION_MISMATCH")
            rows, complete = self._entries(fd, root, path, MAX_DIRECTORY_ENTRIES)
            if _version(os.fstat(fd)) != before:
                raise WorkspaceError("DIRECTORY_CHANGED")
        page = rows[offset:offset + limit]
        next_offset = offset + len(page) if offset + len(page) < len(rows) else None
        return self._result(action="browse", root_alias=root, path=path,
                            evidence_kind=binding.evidence_kind, limitations=binding.note,
                            entries=page, entries_observed=len(rows), scan_complete=complete,
                            directory_version=before, next_offset=next_offset,
                            truncated=not complete or next_offset is not None)

    def describe(self, ref: str) -> dict[str, Any]:
        if isinstance(ref, str) and ref.startswith("registry:"):
            contract = self.registry.get(ref.removeprefix("registry:"))
            if contract is None:
                raise WorkspaceError("DATASET_NOT_REGISTERED")
            return self._result(
                action="describe_contract", contract=dataclasses.asdict(contract),
                declared_inputs=self.registry.inputs_of(contract.dataset_id),
                declared_consumers=self.registry.consumers_of(contract.dataset_id),
                availability="NOT_ESTABLISHED_BY_DECLARATION",
            )
        with self._file(ref) as (stream, source):
            suffix = Path(source["relative_path"]).suffix.lower()
            if suffix in READABLE_SUFFIXES:
                details = inspect_file(stream, suffix, file_bytes=source["file_bytes"])
            else:
                details = {"format": suffix, "read_supported": False,
                           "reason": "USE_EXISTING_OWNER_DECODER",
                           "row_count": None, "time_ranges": {}}
            return self._result(action="describe_file", source=source, details=details)

    def read(self, ref: str, columns: list[str] | None = None,
             time_column: str | None = None, start: str | None = None,
             end: str | None = None, equals: dict[str, Any] | None = None,
             offset: int = 0, limit: int = 100,
             expected_version: str | None = None) -> dict[str, Any]:
        _bound_int(limit, 1, 200)
        _bound_int(offset, 0, 2**63 - 1)
        if expected_version is not None and (not isinstance(expected_version, str) or len(expected_version) > 80):
            raise WorkspaceError("INVALID_ARGUMENT")
        with self._file(ref, expected_version) as (stream, source):
            suffix = Path(source["relative_path"]).suffix.lower()
            rows = read_rows(stream, suffix, file_bytes=source["file_bytes"], columns=columns,
                             time_column=time_column, start=start, end=end, equals=equals,
                             offset=offset, limit=limit, max_scan_rows=100000)
            request = {"ref": ref, "file_version": source["file_version"], "columns": columns,
                       "time_column": time_column, "start": start, "end": end,
                       "equals": equals, "offset": offset, "limit": limit}
            receipt = hashlib.sha256(json.dumps(request, sort_keys=True,
                default=_json_default, allow_nan=False, separators=(",", ":")).encode()).hexdigest()
            return self._result(action="read", source=source, query=request,
                                query_receipt_sha256=receipt, result=rows,
                                temporal_caution="Filtering stored rows does not reconstruct point-in-time availability.",
                                price_basis="PRESERVED_AS_STORED_NOT_REBASED")


def load_workspace_config(path: Path, *, source_revision: str | None = None) -> DataWorkspace:
    """Load an explicit host binding. No discovery of credentials or environment."""
    p = Path(path)
    if p.stat().st_size > 65536:
        raise ValueError("host configuration is too large")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != "mastermind.data_workspace_bindings/v1":
        raise ValueError("invalid host binding schema")
    if set(raw) - {"schema_version", "registry_path", "roots", "test_workspace"}:
        raise ValueError("unknown host binding fields")
    if not isinstance(raw.get("roots"), list) or not isinstance(raw.get("registry_path"), str):
        raise ValueError("invalid host bindings")
    roots = []
    for row in raw["roots"]:
        if (not isinstance(row, dict) or set(row) - {"alias", "path", "evidence_kind", "note", "required_mount"}
                or not {"alias", "path"} <= set(row) or not isinstance(row.get("path"), str)):
            raise ValueError("invalid host root binding")
        roots.append(RootBinding(
            alias=row["alias"], path=Path(row["path"]),
            evidence_kind=row.get("evidence_kind", "unqualified_snapshot"),
            note=row.get("note", ""),
            required_mount=Path(row["required_mount"]) if row.get("required_mount") else None,
        ))
    registry_path = Path(raw["registry_path"])
    if not registry_path.is_absolute():
        registry_path = p.parent / registry_path
    return DataWorkspace(tuple(roots), registry_path, source_revision=source_revision)
