"""Durable-publication manifest/consistency helper (stdlib only).

Bounded, side-effect-free support for sealing international publication
generations: capture stable snapshots of input files, prove they stay
unchanged, prove them against a Git commit tree, and seal/validate a
strict manifest of consumed inputs and produced outputs.

Design constraints honored by this module:

- stdlib only; no producer/collector/cloud/worker delegation.
- Relative, normalized repository paths only. Traversal, absolute paths,
  NUL/backslash, symlink path components and non-regular files are
  refused.
- Bounded stable bytes/stat/hash reads plus read-only Git metadata reads
  (``git ls-tree`` under ``GIT_NO_LAZY_FETCH=1``). No Git mutation, no
  fetch, never ``shell=True``.
- The manifest is a truthful JSON-shaped receipt. No timestamp-as-progress,
  no authority claims, no persistent registry, no generated global
  currentness claim.

The caller (publisher workflow) owns the actual RiskPublication run and
any source/rights grants; this helper only proves bytes and tree state.
"""

import hashlib
import os
import re
import stat
import subprocess

__all__ = [
    "DurablePublicationError",
    "SCHEMA",
    "PER_FILE_BYTES_CAP",
    "AGGREGATE_BYTES_CAP",
    "REQUIRED_OUTPUT_PATHS",
    "GENERATIONS_DIR",
    "capture_inputs",
    "validate_unchanged",
    "validate_at_ref",
    "build_manifest",
    "validate_manifest",
]


class DurablePublicationError(Exception):
    """Refusal: a bounded durable-publication invariant was violated."""


SCHEMA = "intl.durable_publication.v1"
PER_FILE_BYTES_CAP = 16 * 1024 * 1024
AGGREGATE_BYTES_CAP = 256 * 1024 * 1024
REQUIRED_OUTPUT_PATHS = ("site/intl.html", "data/intl_risk/latest.json")
GENERATIONS_DIR = "data/intl/publication/generations"

_IDENTITY_FIELDS = ("dev", "ino", "mode", "uid", "gid", "size", "mtime_ns", "ctime_ns")
_IDENTITY_KEYS = frozenset(_IDENTITY_FIELDS)
_RECORD_KEYS = frozenset(("path", "exists", "sha256", "git_blob", "size", "identity"))
_MANIFEST_KEYS = frozenset(("schema", "source_sha", "inputs", "outputs"))

_HEX40_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_HEX64_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_UUID4 = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
# Exact managed generation filenames. Immutable ones carry their own
# SHA-256 in the name and are checked against the file bytes.
_IMMUTABLE_NAME_RES = (
    re.compile(r"\Aintl_generation_%s_(?P<sha>[0-9a-f]{64})\.json\Z" % _UUID4),
    re.compile(r"\Aintl_generation_descriptor_(?P<sha>[0-9a-f]{64})\.json\Z"),
    re.compile(r"\Aintl_policy_points_%s_(?P<sha>[0-9a-f]{64})\.json\Z" % _UUID4),
)
_CURRENT_GENERATION_NAME = "intl_generation_current.json"

_READ_CHUNK = 1 << 20
_LS_TREE_TIMEOUT_S = 60


# ---------------------------------------------------------------------------
# path normalization and safety


def _norm_repo_path(path):
    """Validate a relative, normalized repo path and return it unchanged."""
    if not isinstance(path, str) or not path:
        raise DurablePublicationError("path must be a nonempty str, got: %r" % (path,))
    if "\0" in path:
        raise DurablePublicationError("path contains NUL: %r" % (path,))
    if "\\" in path:
        raise DurablePublicationError("path contains a backslash: %r" % (path,))
    if path.startswith("/"):
        raise DurablePublicationError("absolute path refused: %r" % (path,))
    if path.endswith("/"):
        raise DurablePublicationError("trailing slash refused: %r" % (path,))
    parts = path.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise DurablePublicationError(
                "non-normalized or traversal path refused: %r" % (path,)
            )
    return path


def _check_root(root):
    if isinstance(root, (bytes, bytearray)):
        raise DurablePublicationError("root must be a str filesystem path")
    try:
        root = os.path.abspath(os.fspath(root))
    except TypeError:
        raise DurablePublicationError("root must be a filesystem path: %r" % (root,))
    if not os.path.isdir(root):
        raise DurablePublicationError("root is not an existing directory: %r" % (root,))
    return root


def _check_ancestors(root, parts, path):
    """Every existing prefix must be a real directory, never a symlink."""
    for i in range(1, len(parts)):
        prefix = os.path.join(root, *parts[:i])
        try:
            lst = os.lstat(prefix)
        except FileNotFoundError:
            # Missing parents are acceptable as long as nothing along the
            # way is a symlink (checked above up to the first absence).
            return
        except OSError as exc:
            raise DurablePublicationError(
                "unreadable path component %r for %r: %s"
                % (prefix, path, exc)
            )
        if stat.S_ISLNK(lst.st_mode):
            raise DurablePublicationError(
                "symlink path component refused for %r: %s" % (path, prefix)
            )
        if not stat.S_ISDIR(lst.st_mode):
            raise DurablePublicationError(
                "non-directory path component refused for %r: %s" % (path, prefix)
            )


def _resolve_checked(root, path):
    """Return (parts, abspath, lstat-or-None) with all symlink checks done."""
    _norm_repo_path(path)
    parts = path.split("/")
    _check_ancestors(root, parts, path)
    full = os.path.join(root, *parts)
    try:
        lst = os.lstat(full)
    except FileNotFoundError:
        return parts, full, None
    except OSError as exc:
        raise DurablePublicationError("unreadable path %r: %s" % (path, exc))
    if stat.S_ISLNK(lst.st_mode):
        raise DurablePublicationError("symlink refused: %r" % (path,))
    if not stat.S_ISREG(lst.st_mode):
        raise DurablePublicationError("non-regular file refused: %r" % (path,))
    return parts, full, lst


# ---------------------------------------------------------------------------
# identity, hashing and stable reads


def _identity_from_stat(st):
    return {
        "dev": st.st_dev,
        "ino": st.st_ino,
        "mode": st.st_mode,
        "uid": st.st_uid,
        "gid": st.st_gid,
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
        "ctime_ns": st.st_ctime_ns,
    }


def _sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def _git_blob_hex(data):
    digest = hashlib.sha1()
    digest.update(b"blob %d\0" % len(data))
    digest.update(data)
    return digest.hexdigest()


def _stable_read(path, full, before_lst, remaining_budget):
    """Read exact bytes under before/after identity plus no-follow checks."""
    size = before_lst.st_size
    if size > PER_FILE_BYTES_CAP:
        raise DurablePublicationError(
            "file exceeds %d-byte per-file cap: %r" % (PER_FILE_BYTES_CAP, path)
        )
    if size > remaining_budget:
        raise DurablePublicationError(
            "aggregate %d-byte cap exceeded at %r" % (AGGREGATE_BYTES_CAP, path)
        )
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(full, flags)
    except OSError as exc:
        raise DurablePublicationError(
            "cannot open %r without following symlinks: %s" % (path, exc)
        )
    try:
        if _identity_from_stat(os.fstat(fd)) != _identity_from_stat(before_lst):
            raise DurablePublicationError(
                "path identity changed between lstat and open: %r" % (path,)
            )
        chunks = []
        total = 0
        while True:
            try:
                chunk = os.read(fd, _READ_CHUNK)
            except OSError as exc:
                raise DurablePublicationError("read failed for %r: %s" % (path, exc))
            if not chunk:
                break
            total += len(chunk)
            if total > PER_FILE_BYTES_CAP:
                raise DurablePublicationError(
                    "file grew past %d-byte per-file cap while reading: %r"
                    % (PER_FILE_BYTES_CAP, path)
                )
            if total > remaining_budget:
                raise DurablePublicationError(
                    "aggregate cap exceeded while reading %r" % (path,)
                )
            chunks.append(chunk)
    finally:
        os.close(fd)
    after_lst = os.lstat(full)
    identity = _identity_from_stat(after_lst)
    if identity != _identity_from_stat(before_lst):
        raise DurablePublicationError(
            "file identity changed during bounded read: %r" % (path,)
        )
    data = b"".join(chunks)
    if len(data) != size:
        raise DurablePublicationError("read length mismatch for %r" % (path,))
    return data, identity


def _absent_record(path):
    return {
        "path": path,
        "exists": False,
        "sha256": None,
        "git_blob": None,
        "size": None,
        "identity": None,
    }


def _existing_record(path, data, identity):
    return {
        "path": path,
        "exists": True,
        "sha256": _sha256_hex(data),
        "git_blob": _git_blob_hex(data),
        "size": len(data),
        "identity": identity,
    }


def _capture_paths(root, paths, allow_missing):
    budget = AGGREGATE_BYTES_CAP
    records = []
    for path in paths:
        _parts, full, lst = _resolve_checked(root, path)
        if lst is None:
            if not allow_missing:
                raise DurablePublicationError("required path missing: %r" % (path,))
            records.append(_absent_record(path))
            continue
        data, identity = _stable_read(path, full, lst, budget)
        budget -= len(data)
        records.append(_existing_record(path, data, identity))
    return records


def capture_inputs(root, paths, allow_missing=True):
    """Capture a sorted list of stable records for ``paths`` under ``root``.

    Each record is ``{path, exists, sha256, git_blob, size, identity}``.
    Existing files are read with lstat/fstat identity comparison before and
    after the bounded read plus an O_NOFOLLOW open. Stable absence is
    represented explicitly when ``allow_missing`` is true. ``git_blob`` is
    the ordinary Git SHA-1 over ``b'blob <len>\\0' + bytes``.
    """
    root = _check_root(root)
    if isinstance(paths, (str, bytes, bytearray)):
        raise DurablePublicationError(
            "paths must be an iterable of str paths, not a bare string"
        )
    seen = set()
    for path in paths:
        _norm_repo_path(path)
        if path in seen:
            raise DurablePublicationError("duplicate path refused: %r" % (path,))
        seen.add(path)
    return _capture_paths(root, sorted(seen), allow_missing)


# ---------------------------------------------------------------------------
# record shape validation


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _check_sha256_hex(value, what):
    if not isinstance(value, str) or not _HEX64_RE.match(value):
        raise DurablePublicationError("%s must be 64 lowercase hex chars" % (what,))


def _check_git_blob_hex(value):
    if not isinstance(value, str) or not _HEX40_RE.match(value):
        raise DurablePublicationError("git_blob must be 40 lowercase hex chars")


def _check_identity(identity, path):
    if not isinstance(identity, dict) or set(identity) != _IDENTITY_KEYS:
        raise DurablePublicationError(
            "identity must contain exactly %s for %r"
            % (", ".join(_IDENTITY_FIELDS), path)
        )
    for field in _IDENTITY_FIELDS:
        if not _is_int(identity[field]) or identity[field] < 0:
            raise DurablePublicationError(
                "identity field %s must be a nonnegative int for %r" % (field, path)
            )


def _validate_records(records, allowlist_outputs):
    """Strictly type-check a list of records; returns a list copy."""
    if isinstance(records, (str, bytes, bytearray)) or not isinstance(
        records, (list, tuple)
    ):
        raise DurablePublicationError("records must be a list of record dicts")
    checked = []
    seen = set()
    budget = AGGREGATE_BYTES_CAP
    for record in records:
        if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
            raise DurablePublicationError(
                "record must contain exactly %s" % (", ".join(sorted(_RECORD_KEYS)),)
            )
        path = _norm_repo_path(record["path"])
        if path in seen:
            raise DurablePublicationError("duplicate record path refused: %r" % (path,))
        seen.add(path)
        if allowlist_outputs:
            _check_output_path(path)
        exists = record["exists"]
        if not isinstance(exists, bool):
            raise DurablePublicationError("exists must be a bool for %r" % (path,))
        if exists:
            _check_sha256_hex(record["sha256"], "sha256")
            _check_git_blob_hex(record["git_blob"])
            size = record["size"]
            if not _is_int(size) or size < 0 or size > PER_FILE_BYTES_CAP:
                raise DurablePublicationError(
                    "record size out of bounds for %r" % (path,)
                )
            _check_identity(record["identity"], path)
            budget -= size
            if budget < 0:
                raise DurablePublicationError(
                    "aggregate %d-byte cap exceeded in records"
                    % (AGGREGATE_BYTES_CAP,)
                )
        else:
            for key in ("sha256", "git_blob", "size", "identity"):
                if record[key] is not None:
                    raise DurablePublicationError(
                        "absent record must set %s to null: %r" % (key, path)
                    )
        checked.append(record)
    return checked


def _require_sorted(records):
    paths = [record["path"] for record in records]
    if paths != sorted(paths):
        raise DurablePublicationError("records must be sorted by path")


# ---------------------------------------------------------------------------
# output allowlist


def _check_output_path(path):
    _norm_repo_path(path)
    if path in REQUIRED_OUTPUT_PATHS:
        return
    if path.startswith("site/"):
        return
    prefix = GENERATIONS_DIR + "/"
    if path.startswith(prefix):
        name = path[len(prefix):]
        if "/" in name:
            raise DurablePublicationError(
                "generations filename must be flat: %r" % (path,)
            )
        if name == _CURRENT_GENERATION_NAME:
            return
        for pattern in _IMMUTABLE_NAME_RES:
            if pattern.match(name):
                return
        raise DurablePublicationError(
            "generations filename not in the exact allowlist: %r" % (path,)
        )
    raise DurablePublicationError("output path not in the allowlist: %r" % (path,))


def _immutable_expected_sha(path):
    """Return the SHA-256 encoded in an immutable output name, else None."""
    prefix = GENERATIONS_DIR + "/"
    if not path.startswith(prefix):
        return None
    name = path[len(prefix):]
    for pattern in _IMMUTABLE_NAME_RES:
        match = pattern.match(name)
        if match:
            return match.group("sha")
    return None


# ---------------------------------------------------------------------------
# Git metadata reads (read-only, no fetch)


def _check_commit_sha(sha, what="sha"):
    if not isinstance(sha, str) or not _HEX40_RE.match(sha):
        raise DurablePublicationError(
            "%s must be a full 40-char lowercase hex sha" % (what,)
        )
    return sha


def _ls_tree_entry(root, sha, path):
    """Read-only single-path ls-tree; None when the path is absent at ref."""
    env = dict(os.environ)
    env["GIT_NO_LAZY_FETCH"] = "1"
    argv = [
        "git",
        "ls-tree",
        "-r",
        "-z",
        sha,
        "--",
        ":(literal)" + path,
    ]
    try:
        proc = subprocess.run(
            argv,
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=_LS_TREE_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise DurablePublicationError("git ls-tree timed out for %r" % (path,))
    except OSError as exc:
        raise DurablePublicationError("git ls-tree failed to run: %s" % (exc,))
    if proc.returncode != 0:
        raise DurablePublicationError(
            "git ls-tree refused ref %s for %r: %s"
            % (
                sha,
                path,
                proc.stderr.decode("utf-8", "replace").strip(),
            )
        )
    entries = [raw for raw in proc.stdout.split(b"\0") if raw]
    if not entries:
        return None
    if len(entries) > 1:
        raise DurablePublicationError("ambiguous ls-tree output for %r" % (path,))
    meta, _, raw_path = entries[0].partition(b"\t")
    fields = meta.split(b" ")
    if len(fields) != 3:
        raise DurablePublicationError("malformed ls-tree entry for %r" % (path,))
    entry_path = os.fsdecode(raw_path)
    if entry_path != path:
        raise DurablePublicationError(
            "ls-tree returned unexpected path %r for %r" % (entry_path, path)
        )
    return (
        fields[0].decode("ascii", "replace"),
        fields[1].decode("ascii", "replace"),
        fields[2].decode("ascii", "replace"),
        entry_path,
    )


def validate_at_ref(root, sha, records):
    """Prove records against the tracked tree at ``sha`` (read-only).

    Every existing record's ``git_blob`` must equal the blob at that exact
    tracked path, and every absent record must be absent at the ref. Other,
    unrelated upstream tree changes are allowed. No cat-file and no lazy
    fetch is performed.
    """
    root = _check_root(root)
    sha = _check_commit_sha(sha, "ref sha")
    _validate_records(records, allowlist_outputs=False)
    for record in records:
        path = record["path"]
        entry = _ls_tree_entry(root, sha, path)
        if record["exists"]:
            if entry is None:
                raise DurablePublicationError(
                    "tracked path missing at ref %s: %r" % (sha, path)
                )
            entry_mode, entry_type, entry_sha, _entry_path = entry
            if entry_type != "blob":
                raise DurablePublicationError(
                    "non-blob entry at ref %s for %r" % (sha, path)
                )
            expected_mode = "100755" if record["identity"]["mode"] & 0o111 else "100644"
            if entry_mode != expected_mode:
                raise DurablePublicationError(
                    "git file mode mismatch at ref %s for %r" % (sha, path)
                )
            if entry_sha != record["git_blob"]:
                raise DurablePublicationError(
                    "git blob mismatch at ref %s for %r: %s != %s"
                    % (sha, path, record["git_blob"], entry_sha)
                )
        elif entry is not None:
            raise DurablePublicationError(
                "absent record exists at ref %s: %r" % (sha, path)
            )


# ---------------------------------------------------------------------------
# unchanged validation


def validate_unchanged(root, records):
    """Prove recorded files are byte- and identity-unchanged at ``root``.

    Refuses changed bytes (including equal-size rewrites), identity or
    length changes, deletion, appearance of a recorded-absent path and
    inode replacement. Does not demand unrelated directory mtimes or
    process quiescence.
    """
    root = _check_root(root)
    _validate_records(records, allowlist_outputs=False)
    budget = AGGREGATE_BYTES_CAP
    for record in records:
        path = record["path"]
        _parts, full, lst = _resolve_checked(root, path)
        if record["exists"]:
            if lst is None:
                raise DurablePublicationError("recorded file now missing: %r" % (path,))
            if _identity_from_stat(lst) != record["identity"]:
                raise DurablePublicationError(
                    "recorded file identity changed or inode replaced: %r" % (path,)
                )
            data, identity = _stable_read(path, full, lst, budget)
            budget -= len(data)
            if _sha256_hex(data) != record["sha256"]:
                raise DurablePublicationError(
                    "recorded file bytes changed: %r" % (path,)
                )
            if identity != record["identity"]:
                raise DurablePublicationError(
                    "recorded file identity changed during validation: %r" % (path,)
                )
        elif lst is not None:
            raise DurablePublicationError(
                "absent record is now present: %r" % (path,)
            )


# ---------------------------------------------------------------------------
# manifest build and validate


def build_manifest(root, source_sha, inputs, output_paths):
    """Seal a durable-publication manifest.

    Validates the inputs unchanged on disk and against ``source_sha`` in
    the upstream tree before sealing, then captures every allowlisted
    output path (which must exist). Immutable sha-named generation files
    must hash exactly to the SHA-256 embedded in their filename. The
    manifest carries no generated global currentness claim.
    """
    root = _check_root(root)
    source_sha = _check_commit_sha(source_sha, "source_sha")
    inputs = _validate_records(inputs, allowlist_outputs=False)
    inputs = sorted(inputs, key=lambda record: record["path"])
    if isinstance(output_paths, (str, bytes, bytearray)):
        raise DurablePublicationError(
            "output_paths must be an iterable of str paths, not a bare string"
        )
    seen = set()
    for path in output_paths:
        _check_output_path(path)
        if path in seen:
            raise DurablePublicationError("duplicate output path refused: %r" % (path,))
        seen.add(path)
    missing = [path for path in REQUIRED_OUTPUT_PATHS if path not in seen]
    if missing:
        raise DurablePublicationError(
            "missing required output paths: %s" % (", ".join(missing),)
        )
    # Source/input validation before sealing.
    validate_unchanged(root, inputs)
    validate_at_ref(root, source_sha, inputs)
    outputs = _capture_paths(root, sorted(seen), allow_missing=False)
    for record in outputs:
        expected = _immutable_expected_sha(record["path"])
        if expected is not None and record["sha256"] != expected:
            raise DurablePublicationError(
                "immutable output bytes do not match the sha in its filename: %r"
                % (record["path"],)
            )
    return {
        "schema": SCHEMA,
        "source_sha": source_sha,
        "inputs": inputs,
        "outputs": outputs,
    }


def validate_manifest(root, manifest, target_sha=None):
    """Strictly validate a sealed manifest against disk and, optionally, a ref.

    Checks the strict typed schema/shape, record sorting, duplicates, byte
    caps, output path allowlist, required outputs, input unchanged, produced
    bytes unchanged and the immutable sha-name binding. When ``target_sha``
    is supplied, also proves the records against that upstream tree via
    ``validate_at_ref``. This helper never creates a source or rights grant;
    the caller owns the RiskPublication receipt and generation semantics.
    """
    root = _check_root(root)
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_KEYS:
        raise DurablePublicationError(
            "manifest must contain exactly %s" % (", ".join(sorted(_MANIFEST_KEYS)),)
        )
    if manifest["schema"] != SCHEMA:
        raise DurablePublicationError(
            "unsupported manifest schema: %r" % (manifest["schema"],)
        )
    source_sha = _check_commit_sha(manifest["source_sha"], "source_sha")
    inputs = _validate_records(manifest["inputs"], allowlist_outputs=False)
    outputs = _validate_records(manifest["outputs"], allowlist_outputs=True)
    _require_sorted(inputs)
    _require_sorted(outputs)
    output_paths = {record["path"] for record in outputs}
    missing = [
        path for path in REQUIRED_OUTPUT_PATHS if path not in output_paths
    ]
    if missing:
        raise DurablePublicationError(
            "manifest missing required outputs: %s" % (", ".join(missing),)
        )
    for record in outputs:
        if not record["exists"]:
            raise DurablePublicationError(
                "output record must exist: %r" % (record["path"],)
            )
        expected = _immutable_expected_sha(record["path"])
        if expected is not None and record["sha256"] != expected:
            raise DurablePublicationError(
                "immutable sha-named output does not match its filename: %r"
                % (record["path"],)
            )
    validate_unchanged(root, inputs)
    validate_unchanged(root, outputs)
    if target_sha is not None:
        validate_at_ref(root, target_sha, inputs)
        validate_at_ref(root, target_sha, outputs)
    return None


class IntlPublicationError(ValueError):
    """No actionable page may be committed after this publication refusal."""


class IntlPublicationUnknown(IntlPublicationError):
    """A PUT may have committed; preserve its original receipt and carrier."""
