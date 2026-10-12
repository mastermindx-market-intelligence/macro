#!/usr/bin/env python3
"""Isolated older-candidate qualification for scripts.build_options_matrix.


Exercises the reviewed publisher main() withholding branch in a temporary
directory. Does not reimplement that branch. Does not publish, restart,
backdate, or bypass freshness. A pair of supplied files is not production
provenance; the caller must bind refs and digests to retained publication
evidence externally.

Preparatory only. A successful run is not genuine older-candidate acceptance
and is not live or production proof.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import math
import os
import re
import stat
import sys
import tempfile
import traceback
import types
from contextlib import redirect_stderr, redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "options_structure.matrix.older_candidate_qualification.v1"
REVIEWED_COMMIT = "6361f5e0e071dfc050c503e225afe8a4897f0e8d"
SOURCE_FILES = (
    "scripts/build_options_matrix.py",
    "engine/options_matrix_retention.py",
    "engine/thetadata_store.py",
)
_COMMIT = re.compile(r"[0-9a-f]{40}")
_SHA = re.compile(r"[0-9a-f]{64}")
_REL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
_WITHHOLD_NEEDLE = "older than existing artifact"
_MAX_SOURCE_BYTES = 2 * 1024 * 1024
_DUMMY_BUCKET = "dummy-qualify-older-bucket"
_DUMMY_ENDPOINT = "https://qualify-older.example.invalid"
_DUMMY_ACCESS = "dummy-not-a-secret-access-key"
_DUMMY_SECRET = "dummy-not-a-secret-secret-key"
_ISOLATED_ENV_PREFIXES = ("R2_", "AWS_", "BOTO")
_ISOLATED_ENV_KEYS = (
    "THETADATA_STORE",
    "THETADATA_STORE_PROBE_S",
    "MATRIX_FRESHNESS_BYPASS",
    "AWS_PROFILE",
    "AWS_SHARED_CREDENTIALS_FILE",
    "AWS_CONFIG_FILE",
)


class QualifyError(Exception):
    """Input, source-identity, or isolation failure before/around publisher main()."""


class QualifyFailed(QualifyError):
    """Publisher exercise did not prove older-candidate withholding."""

    def __init__(self, message: str, report: dict[str, Any]):
        super().__init__(message)
        self.report = report


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_lnk(path: Path) -> bool:
    try:
        return stat.S_ISLNK(os.lstat(path).st_mode)
    except FileNotFoundError:
        return False


def _abspath(path: Path) -> Path:
    return Path(os.path.abspath(os.fsdecode(path)))


def _reject_symlink_leaf(path: Path, label: str, *, must_exist: bool = False) -> Path:
    path = _abspath(path)
    if ".." in Path(os.fsdecode(path)).parts:
        raise QualifyError(f"{label} must not contain relative components")
    if _is_lnk(path):
        raise QualifyError(f"{label} rejects symlink {path}")
    if must_exist and not path.exists():
        raise QualifyError(f"{label} does not exist")
    return path


def _open_regular(path: Path, label: str, *, write: bool = False, exclusive: bool = False, mode: int = 0o600) -> int:
    _reject_symlink_leaf(path, label, must_exist=not write)
    flags = os.O_NOFOLLOW | os.O_CLOEXEC
    if write:
        flags |= os.O_WRONLY | os.O_CREAT
        if exclusive:
            flags |= os.O_EXCL
        fd = os.open(str(path), flags, mode)
    else:
        flags |= os.O_RDONLY
        fd = os.open(str(path), flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise QualifyError(f"{label} is not a regular file")
        return fd
    except Exception:
        os.close(fd)
        raise


def _bounded_read(path: Path, label: str, limit: int) -> bytes:
    fd = _open_regular(path, label)
    try:
        info = os.fstat(fd)
        if info.st_size <= 0:
            raise QualifyError(f"{label} is empty")
        if info.st_size > limit:
            raise QualifyError(f"{label} exceeds byte bound {limit}")
        raw = os.read(fd, limit + 1)
        if len(raw) > limit:
            raise QualifyError(f"{label} exceeds byte bound {limit}")
        if not raw:
            raise QualifyError(f"{label} is empty")
        return raw
    finally:
        os.close(fd)


def _digest_source_file(repo: Path, rel: str) -> dict[str, Any]:
    if not isinstance(rel, str) or not _REL.fullmatch(rel) or ".." in rel.split("/"):
        raise QualifyError(f"invalid source relative path {rel!r}")
    path = repo.joinpath(*rel.split("/"))
    raw = _bounded_read(path, f"source {rel}", _MAX_SOURCE_BYTES)
    return {"path": str(path), "sha256": _sha256(raw), "byte_length": len(raw)}


def _parse_expected_source(items: Iterable[str]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for item in items:
        if not isinstance(item, str) or "=" not in item:
            raise QualifyError("expected source file must be RELPATH=sha256")
        rel, _, digest = item.partition("=")
        if rel in expected:
            raise QualifyError(f"duplicate expected source file {rel}")
        if not _SHA.fullmatch(digest):
            raise QualifyError(f"invalid expected digest for {rel}")
        if not isinstance(rel, str) or not _REL.fullmatch(rel) or ".." in rel.split("/"):
            raise QualifyError(f"invalid expected source relative path {rel!r}")
        expected[rel] = digest
    return expected


def _measured_spot_and_cells(payload: Mapping[str, Any], label: str) -> tuple[float, int]:
    if not isinstance(payload, dict):
        raise QualifyError(f"{label} payload is not an object")
    cells = payload.get("cells")
    if not isinstance(cells, list) or not cells:
        raise QualifyError(f"{label} is not a measured nonempty payload")
    spot = payload.get("spot")
    if isinstance(spot, bool) or not isinstance(spot, (int, float)):
        raise QualifyError(f"{label} spot is missing or not a finite number")
    value = float(spot)
    if not math.isfinite(value) or not value > 0:
        raise QualifyError(f"{label} spot is not positive finite")
    return value, len(cells)


def _verify_snapshot(retention, root: str, raw: bytes, version_ref: str, label: str):
    digest = _sha256(raw)
    try:
        ref = retention.parse_reference(root, version_ref, digest)
        payload = retention.verify_snapshot(ref, raw)
    except retention.HistoricalUnavailable as exc:
        raise QualifyError(f"{label} failed retention verification: {exc}") from exc
    if ref.session is None:
        raise QualifyError(f"{label} session is unknown; dated session required")
    spot, n_cells = _measured_spot_and_cells(payload, label)
    return ref, payload, {
        "path_label": label,
        "sha256": ref.sha256,
        "byte_length": ref.byte_length,
        "session": ref.session,
        "version_ref": ref.version_ref,
        "root": ref.root,
        "spot": spot,
        "n_cells": n_cells,
        "production_provenance_bound": False,
    }


def _receipt_forbidden(receipt: Path, *trees: Path) -> None:
    resolved = receipt
    for tree in trees:
        if tree is None:
            continue
        try:
            receipt.relative_to(tree)
        except ValueError:
            continue
        raise QualifyError(f"receipt path {receipt} is inside forbidden tree {tree}")
    if resolved.exists():
        raise QualifyError("receipt path already exists; exclusive new creation required")


def _validate_receipt_location(receipt: Path, *, repo: Path, candidate: Path, existing: Path) -> None:
    receipt = _abspath(receipt)
    parent = _reject_symlink_leaf(receipt.parent, "receipt parent", must_exist=True)
    if not parent.is_dir() or _is_lnk(parent):
        raise QualifyError("receipt parent must be a real directory")
    _reject_symlink_leaf(receipt, "receipt", must_exist=False)
    _receipt_forbidden(receipt, repo, candidate.parent, existing.parent, candidate, existing)
    if receipt.exists() or _is_lnk(receipt):
        raise QualifyError("receipt path already exists or is a symlink")


def _write_receipt(receipt: Path, report: Mapping[str, Any]) -> None:
    raw = json.dumps(report, allow_nan=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    fd = _open_regular(receipt, "receipt", write=True, exclusive=True, mode=0o600)
    try:
        if os.write(fd, raw) != len(raw):
            raise QualifyError("short receipt write")
        os.fsync(fd)
    finally:
        os.close(fd)


class _R2Spy:
    """Reject every client method; construction itself is not a network attempt."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.network_attempts = 0
        self.remote_writes = 0
        self.constructions = 0

    def _reject(self, name: str, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        self.network_attempts += 1
        if name in {
            "put_object", "upload_file", "upload_fileobj", "copy_object",
            "delete_object", "create_multipart_upload", "upload_part",
        }:
            self.remote_writes += 1
        raise RuntimeError(f"isolated R2 spy rejected {name}")

    def __getattr__(self, name: str):
        def method(*args, **kwargs):
            return self._reject(name, *args, **kwargs)
        return method


def _load_publisher(repo: Path):
    engine = types.ModuleType("engine")
    engine.__path__ = [str(repo / "engine")]
    sys.modules["engine"] = engine

    retention_path = repo / "engine" / "options_matrix_retention.py"
    spec = spec_from_file_location(
        "engine.options_matrix_retention", str(retention_path),
    )
    if spec is None or spec.loader is None:
        raise QualifyError("unable to load engine.options_matrix_retention")
    retention = module_from_spec(spec)
    sys.modules["engine.options_matrix_retention"] = retention
    spec.loader.exec_module(retention)
    engine.options_matrix_retention = retention

    options_matrix = types.ModuleType("engine.options_matrix")

    def _unpatched_build(*_a, **_k):
        raise RuntimeError("build_matrix was not patched to the validated older payload")

    options_matrix.build_matrix = _unpatched_build
    sys.modules["engine.options_matrix"] = options_matrix
    engine.options_matrix = options_matrix

    store = types.ModuleType("engine.thetadata_store")

    def _unpatched_resolve(**_k):
        raise RuntimeError("resolve_thetadata_store was not patched to an inert path")

    store.resolve_thetadata_store = _unpatched_resolve
    store.clear_parquet_cache = lambda: None
    sys.modules["engine.thetadata_store"] = store
    engine.thetadata_store = store

    scripts = types.ModuleType("scripts")
    scripts.__path__ = [str(repo / "scripts")]
    sys.modules["scripts"] = scripts

    builder_path = repo / "scripts" / "build_options_matrix.py"
    bspec = spec_from_file_location(
        "scripts.build_options_matrix", str(builder_path),
    )
    if bspec is None or bspec.loader is None:
        raise QualifyError("unable to load scripts.build_options_matrix")
    builder = module_from_spec(bspec)
    builder.__package__ = "scripts"
    sys.modules["scripts.build_options_matrix"] = builder
    bspec.loader.exec_module(builder)
    scripts.build_options_matrix = builder
    return builder, retention, store


def _isolate_env() -> None:
    for key in list(os.environ):
        if key.startswith(_ISOLATED_ENV_PREFIXES) or key in _ISOLATED_ENV_KEYS:
            del os.environ[key]
    os.environ["R2_ENDPOINT"] = _DUMMY_ENDPOINT
    os.environ["R2_ACCESS_KEY_ID"] = _DUMMY_ACCESS
    os.environ["R2_SECRET_ACCESS_KEY"] = _DUMMY_SECRET
    os.environ["R2_BUCKET"] = _DUMMY_BUCKET


def _history_files(out_dir: Path) -> list[Path]:
    history = out_dir / "history"
    if not history.exists():
        return []
    found = []
    for dirpath, dirnames, filenames in os.walk(history):
        dirnames[:] = sorted(dirnames)
        for name in sorted(filenames):
            found.append(Path(dirpath) / name)
    return found


def qualify_older_snapshot(
    *,
    root: str,
    candidate_json: str | os.PathLike[str],
    candidate_version_ref: str,
    existing_json: str | os.PathLike[str],
    existing_version_ref: str,
    repo: str | os.PathLike[str],
    source_commit: str,
    receipt: str | os.PathLike[str],
    expected_source_files: Mapping[str, str] | Iterable[str] | None = None,
) -> dict[str, Any]:
    """Run isolated older-candidate qualification and write a new receipt.

    Synthetic or caller-supplied files remain unbound to production provenance.
    """
    if not isinstance(source_commit, str) or not _COMMIT.fullmatch(source_commit):
        raise QualifyError("source commit must be a 40-character lowercase hex sha")
    repo_path = _reject_symlink_leaf(Path(repo), "repo", must_exist=True)
    if not repo_path.is_dir() or _is_lnk(repo_path):
        raise QualifyError("repo must be a real directory")
    candidate_path = _reject_symlink_leaf(Path(candidate_json), "candidate json", must_exist=True)
    existing_path = _reject_symlink_leaf(Path(existing_json), "existing json", must_exist=True)
    receipt_path = _abspath(Path(receipt))
    _validate_receipt_location(
        receipt_path, repo=repo_path, candidate=candidate_path, existing=existing_path,
    )
    if isinstance(expected_source_files, Mapping):
        expected = dict(expected_source_files)
        for rel, digest in expected.items():
            if not _SHA.fullmatch(str(digest)):
                raise QualifyError(f"invalid expected digest for {rel}")
    elif expected_source_files is None:
        expected = {}
    else:
        expected = _parse_expected_source(expected_source_files)

    source_identity = {}
    for rel in SOURCE_FILES:
        source_identity[rel] = _digest_source_file(repo_path, rel)
    for rel, digest in expected.items():
        if rel not in source_identity:
            source_identity[rel] = _digest_source_file(repo_path, rel)
        measured = source_identity[rel]["sha256"]
        if measured != digest:
            raise QualifyError(
                f"source file {rel} digest {measured} disagrees with expected {digest}"
            )

    saved_modules = {
        name: sys.modules[name]
        for name in list(sys.modules)
        if name == "scripts" or name.startswith("scripts.")
        or name == "engine" or name.startswith("engine.")
    }
    for name in saved_modules:
        del sys.modules[name]
    saved_path = sys.path[:]
    saved_argv = sys.argv[:]
    saved_env = os.environ.copy()
    owned_temp = None
    builder = retention = store_mod = None
    try:
        sys.path.insert(0, str(repo_path))
        builder, retention, store_mod = _load_publisher(repo_path)
        try:
            retention.validate_root(root)
        except retention.HistoricalUnavailable as exc:
            raise QualifyError(f"invalid canonical producer root: {exc}") from exc

        limit = retention.MAX_MATRIX_BYTES
        candidate_raw = _bounded_read(candidate_path, "candidate json", limit)
        existing_raw = _bounded_read(existing_path, "existing json", limit)
        candidate_ref, candidate_payload, candidate_info = _verify_snapshot(
            retention, root, candidate_raw, candidate_version_ref, "candidate",
        )
        existing_ref, _existing_payload, existing_info = _verify_snapshot(
            retention, root, existing_raw, existing_version_ref, "existing",
        )
        if candidate_ref.root != root or existing_ref.root != root:
            raise QualifyError("snapshot root does not match requested root")
        if not (candidate_ref.session < existing_ref.session):
            raise QualifyError(
                f"candidate session {candidate_ref.session} is not strictly earlier "
                f"than existing session {existing_ref.session}"
            )

        payload_fn = builder._payload_session
        existing_fn = builder._existing_usable_session
        if not callable(payload_fn) or not callable(existing_fn):
            raise QualifyError("publisher is missing _payload_session or _existing_usable_session")
        builder_file = os.path.normpath(str(repo_path / "scripts" / "build_options_matrix.py"))
        if os.path.normpath(payload_fn.__code__.co_filename) != builder_file \
                or os.path.normpath(existing_fn.__code__.co_filename) != builder_file:
            raise QualifyError("publisher session helpers are not the verified source functions")

        owned_temp = Path(tempfile.mkdtemp(prefix="qualify-older-matrix-"))
        os.chmod(owned_temp, 0o700)
        out_dir = owned_temp / "out"
        store_dir = owned_temp / "inert-store"
        out_dir.mkdir(mode=0o700)
        store_dir.mkdir(mode=0o700)
        _receipt_forbidden(receipt_path, owned_temp, out_dir, store_dir)
        head_path = out_dir / f"{root}.json"
        head_path.write_bytes(existing_raw)
        head_before = head_path.read_bytes()
        if head_before != existing_raw:
            raise QualifyError("temporary current head copy failed")

        spy = _R2Spy()

        def _inert_resolve(**_kwargs):
            return store_dir

        def _return_older(*_args, **_kwargs):
            return candidate_payload

        def _r2_client():
            spy.constructions += 1
            return spy

        def _upload_r2(*args, **kwargs):
            spy.remote_writes += 1
            spy.network_attempts += 1
            spy.calls.append(("_upload_r2", args, kwargs))
            raise RuntimeError("isolated R2 transport spy rejected upload")

        builder.build_matrix = _return_older
        store_mod.resolve_thetadata_store = _inert_resolve
        builder._r2_client = _r2_client
        builder._upload_r2 = _upload_r2
        if builder._payload_session is not payload_fn or builder._existing_usable_session is not existing_fn:
            raise QualifyError("publisher session helpers were replaced")

        _isolate_env()
        os.environ["THETADATA_STORE"] = str(store_dir)
        sys.argv = [
            "build_options_matrix",
            "--publish",
            "--roots",
            root,
            "--out",
            str(out_dir),
        ]
        log_buf = io.StringIO()
        handler = logging.StreamHandler(log_buf)
        handler.setLevel(logging.DEBUG)
        root_logger = logging.getLogger()
        previous_level = root_logger.level
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)
        stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
        exit_code: int | None = 0
        unexpected = None
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                try:
                    builder.main()
                except SystemExit as exc:
                    code = exc.code
                    if code is None:
                        exit_code = 0
                    elif isinstance(code, int):
                        exit_code = code
                    else:
                        exit_code = 1
                        unexpected = f"non-integer SystemExit {code!r}"
        except Exception as exc:  # noqa: BLE001
            exit_code = None
            unexpected = f"{type(exc).__name__}: {exc}"
        finally:
            root_logger.removeHandler(handler)
            root_logger.setLevel(previous_level)

        if builder._payload_session is not payload_fn or builder._existing_usable_session is not existing_fn:
            raise QualifyError("publisher session helpers changed during main()")

        head_after = head_path.read_bytes() if head_path.exists() else b""
        history = _history_files(out_dir)
        combined = "\n".join([
            stdout_buf.getvalue(), stderr_buf.getvalue(), log_buf.getvalue(),
        ])
        expected_reason = (
            f"resolved session {candidate_ref.session} older than existing artifact "
            f"{existing_ref.session}"
        )
        withheld = (
            expected_reason in combined
            and f"withheld {root}" in combined
            and _WITHHOLD_NEEDLE in combined
        )
        extra = [
            path for path in out_dir.rglob("*")
            if path.is_file() and path != head_path
        ]
        report = {
            "schema": SCHEMA,
            "qualification_kind": "preparatory_isolated_withholding",
            "genuine_older_candidate_acceptance": False,
            "live_acceptance": False,
            "natural_session_proof": False,
            "production_invocation": False,
            "production_provenance_bound": False,
            "runtime_claim_verified": False,
            "provenance_note": (
                "A pair of merely supplied files is not proof of production provenance. "
                "Caller must bind version_ref and digests to retained publication evidence "
                "externally. This receipt records isolated preparatory qualification only."
            ),
            "root": root,
            "source": {
                "claimed_commit": source_commit,
                "commit_verified": False,
                "expected_file_digests_verified": sorted(expected),
                "reviewed_commit": REVIEWED_COMMIT,
                "files": source_identity,
            },
            "candidate": {**candidate_info, "path": str(candidate_path)},
            "existing": {**existing_info, "path": str(existing_path)},
            "exercise": {
                "publisher": "scripts.build_options_matrix.main",
                "publish_flag": True,
                "dummy_bucket": _DUMMY_BUCKET,
                "used_payload_session": True,
                "used_existing_usable_session": True,
                "reimplemented_withholding_branch": False,
                "exit_code": exit_code,
                "unexpected": unexpected,
                "withheld": withheld,
                "withholding_reason": expected_reason if withheld else None,
                "head_unchanged": head_after == existing_raw,
                "head_byte_length_after": len(head_after),
                "history_writes": len(history),
                "extra_output_files": len(extra),
                "remote_writes": spy.remote_writes,
                "network_attempts": spy.network_attempts,
                "r2_constructions": spy.constructions,
                "spy_calls": [c[0] for c in spy.calls],
                "stdout": stdout_buf.getvalue()[-4000:],
                "log": log_buf.getvalue()[-4000:],
            },

        }
        failures = []
        if unexpected is not None:
            failures.append(f"unexpected publisher failure: {unexpected}")
        if exit_code is None:
            failures.append("publisher did not produce an exit code")
        elif exit_code != 1:
            failures.append("publisher must exit 1 for older-candidate withholding")
        if not withheld:
            failures.append("missing specific older-candidate withholding reason from real main()")
        if head_after != existing_raw:
            failures.append("current head bytes changed")
        if history:
            failures.append(f"history writes observed: {len(history)}")
        if extra:
            failures.append(f"unexpected output writes: {len(extra)}")
        if spy.remote_writes:
            failures.append(f"remote writes observed: {spy.remote_writes}")
        if spy.network_attempts:
            failures.append(f"network attempts observed: {spy.network_attempts}")
        if spy.constructions < 1:
            failures.append("publication obligation path did not construct the R2 spy client")
        if candidate_path.read_bytes() != candidate_raw or existing_path.read_bytes() != existing_raw:
            failures.append("input snapshot bytes changed")
        if failures:
            report["exercise"]["failures"] = failures
            raise QualifyFailed("; ".join(failures), report)
        _write_receipt(receipt_path, report)
        report["receipt"] = str(receipt_path)
        return report
    finally:
        builder = retention = store_mod = None
        sys.argv[:] = saved_argv
        os.environ.clear()
        os.environ.update(saved_env)
        sys.path[:] = saved_path
        for name in list(sys.modules):
            if name == "scripts" or name.startswith("scripts.") \
                    or name == "engine" or name.startswith("engine."):
                sys.modules.pop(name, None)
        sys.modules.update(saved_modules)
        if owned_temp is not None:
            _cleanup_owned(owned_temp)


def _cleanup_owned(path: Path) -> None:
    if not path.exists():
        return
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        for name in filenames:
            try:
                os.unlink(os.path.join(dirpath, name))
            except OSError:
                pass
        for name in dirnames:
            try:
                os.rmdir(os.path.join(dirpath, name))
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preparatory isolated older-candidate qualification. "
            "Not genuine older-candidate or live acceptance."
        ),
    )
    parser.add_argument("--root", required=True, help="Canonical producer root (no normalization)")
    parser.add_argument("--candidate-json", required=True, help="Older snapshot JSON path")
    parser.add_argument("--candidate-version-ref", required=True, help="Canonical immutable version_ref")
    parser.add_argument("--existing-json", required=True, help="Newer snapshot JSON path")
    parser.add_argument("--existing-version-ref", required=True, help="Canonical immutable version_ref")
    parser.add_argument("--repo", required=True, help="Product repo path containing verified sources")
    parser.add_argument("--source-commit", required=True, help="Claimed 40-hex source commit")
    parser.add_argument("--receipt", required=True, help="New exclusive receipt path")
    parser.add_argument(
        "--expected-source-file", action="append", default=[],
        help="RELPATH=sha256; fail if the verified source disagrees",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        report = qualify_older_snapshot(
            root=args.root,
            candidate_json=args.candidate_json,
            candidate_version_ref=args.candidate_version_ref,
            existing_json=args.existing_json,
            existing_version_ref=args.existing_version_ref,
            repo=args.repo,
            source_commit=args.source_commit,
            receipt=args.receipt,
            expected_source_files=args.expected_source_file,
        )
    except QualifyFailed as exc:
        print(f"older_candidate_qualify: FAILED (preparatory) {exc}", file=sys.stderr)
        return 1
    except QualifyError as exc:
        print(f"older_candidate_qualify: rejected {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"older_candidate_qualify: internal {type(exc).__name__}", file=sys.stderr)
        traceback.print_exc()
        return 1
    print(
        "older_candidate_qualify: preparatory withholding qualification wrote "
        f"{report.get('receipt')} genuine_older_candidate_acceptance=false "
        "live_acceptance=false production_provenance_bound=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
