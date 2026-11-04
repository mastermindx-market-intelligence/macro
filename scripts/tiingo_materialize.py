"""Offline materialization of Tiingo raw receipts to research-only Parquet.

This is a Data OS L1 candidate reader, not L2 enrollment or an alternate
identity/backtest/PIT authority. One input hash -> one immutable view artifact.
Every input is verified before use, no vendor requests, no API credential reads,
no internal SSD fallback. Unsupported product families remain RAW_ONLY.

Usage:
  python -m scripts.tiingo_materialize --dry-run --max-receipts 500
  python -m scripts.tiingo_materialize --max-receipts 500
"""
from __future__ import annotations

import argparse
import gzip
import io
import stat
from contextlib import contextmanager
import hashlib
import json
import sys
import os
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.tiingo_archive import (
    DEFAULT_ARCHIVE, MIN_FREE_BYTES, TiingoArchiveError, _publish_once,
    require_external_root, require_space, validate_receipt, receipt_identity, capture_day,
)
from lib.dataos.tiingo_views import SCHEMA_VERSION, research_rows

MAX_RAW_MATERIALIZE_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_ROWS = 1_000_000

# Opt-in read budgets for an observational census. These are evidence-byte
# ceilings, not a claim about total process RSS or an atomic archive snapshot.
MAX_CENSUS_METADATA_BYTES = 16 * 1024 * 1024
MAX_CENSUS_RAW_BYTES = 64 * 1024 * 1024
MAX_CENSUS_COMPRESSED_BYTES = 64 * 1024 * 1024
MAX_CENSUS_NORMALIZED_BYTES = 64 * 1024 * 1024
MAX_CENSUS_METADATA_FILE_BYTES = 1_000_000


class BoundedTiingoRead:
    """One read-only, descriptor-confined acquisition; use as a context manager.

    Relative paths are Path objects or tuples of literal component names.
    No symlinks, special files, submounts, repair, fetch, or publication.
    Equal observations and binding checks do not establish owner quiescence.
    """

    def __init__(
        self, root: Path, *, check_mount: bool = True,
        metadata_limit: int = MAX_CENSUS_METADATA_BYTES,
        raw_limit: int = MAX_CENSUS_RAW_BYTES,
        compressed_limit: int = MAX_CENSUS_COMPRESSED_BYTES,
        normalized_limit: int = MAX_CENSUS_NORMALIZED_BYTES,
    ):
        required = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")
        if (os.name != "posix" or os.open not in os.supports_dir_fd
                or any(not hasattr(os, name) for name in required)):
            raise TiingoArchiveError("descriptor-confined read is unsupported")
        limits = {
            "metadata": (metadata_limit, MAX_CENSUS_METADATA_BYTES),
            "raw": (raw_limit, MAX_CENSUS_RAW_BYTES),
            "compressed": (compressed_limit, MAX_CENSUS_COMPRESSED_BYTES),
            "normalized": (normalized_limit, MAX_CENSUS_NORMALIZED_BYTES),
        }
        if any(type(value) is not int or not 0 <= value <= maximum
               for value, maximum in limits.values()):
            raise TiingoArchiveError("read budgets may only tighten fixed ceilings")
        self._limits = {name: value for name, (value, _) in limits.items()}
        self._used = dict.fromkeys(self._limits, 0)
        self._files = {}
        self._directories = {}
        self._failed = False
        self._fd = -1
        self._dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        self._file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        self.root = Path(root)
        if not self.root.is_absolute() or ".." in self.root.parts:
            raise TiingoArchiveError("strict archive root must be an absolute lexical path")
        # Open the ORIGINAL spelling first. resolve() must not erase a symlink.
        fd = self._absolute_directory_fd(self.root)
        try:
            approved = require_external_root(self.root, check_mount=check_mount)
            if approved != self.root:
                raise TiingoArchiveError("strict archive root spelling changed")
            st = os.fstat(fd)
            self._root_identity = (st.st_dev, st.st_ino)
            self._device = st.st_dev
            self._mount_checked = check_mount
            self._directories[()] = self._root_identity
        except BaseException:
            os.close(fd)
            raise
        self._fd = fd

    def __enter__(self):
        self._alive()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def close(self) -> None:
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1

    @property
    def used(self) -> dict[str, int]:
        return dict(self._used)

    def _fail(self, message: str):
        self._failed = True
        raise TiingoArchiveError(message)

    def _alive(self) -> None:
        if self._fd < 0 or self._failed:
            raise TiingoArchiveError("bounded read context is closed or refused")

    def _absolute_directory_fd(self, path: Path) -> int:
        fd = os.open("/", self._dir_flags)
        try:
            for name in path.parts[1:]:
                child = os.open(name, self._dir_flags, dir_fd=fd)
                os.close(fd)
                fd = child
            return fd
        except BaseException:
            os.close(fd)
            raise

    def _parts(self, relative: Path | tuple[str, ...]) -> tuple[str, ...]:
        if isinstance(relative, Path):
            if relative.is_absolute():
                self._fail("strict read requires an archive-relative path")
            parts = relative.parts
        elif isinstance(relative, tuple):
            parts = relative
        else:
            self._fail("strict path must be a relative Path or component tuple")
        if any(not isinstance(name, str) or name in ("", ".", "..")
               or "/" in name or "\x00" in name for name in parts):
            self._fail("invalid strict relative path component")
        return parts

    def relative(self, path: Path) -> tuple[str, ...]:
        """Strip only the lexical root; do not resolve any supplied component."""
        self._alive()
        try:
            return self._parts(Path(path).relative_to(self.root))
        except ValueError:
            self._fail("path is outside the bound archive root")

    def assert_root(self, root: Path, *, check_mount: bool = True) -> Path:
        self._alive()
        if Path(root) != self.root or (check_mount and not self._mount_checked):
            self._fail("reader root/mount requirement differs from bound context")
        return self.root

    def _directory_fd(self, parts: tuple[str, ...]) -> int:
        self._alive()
        fd = os.dup(self._fd)
        prefix = ()
        try:
            for name in parts:
                child = os.open(name, self._dir_flags, dir_fd=fd)
                os.close(fd)
                fd = child
                prefix += (name,)
                st = os.fstat(fd)
                if not stat.S_ISDIR(st.st_mode) or st.st_dev != self._device:
                    self._fail("strict directory crosses archive device")
                identity = (st.st_dev, st.st_ino)
                previous = self._directories.setdefault(prefix, identity)
                if previous != identity:
                    self._fail("archive directory binding changed during acquisition")
            return fd
        except BaseException:
            os.close(fd)
            raise

    @contextmanager
    def directory(self, relative: Path | tuple[str, ...]):
        """Yield a held no-follow directory fd; absence is FileNotFoundError.

        The caller bounds scandir entries before filtering. Directory content
        changes are reported by its scans; this checks directory identity only.
        """
        parts = self._parts(relative)
        fd = self._directory_fd(parts)
        try:
            yield fd
            check = self._directory_fd(parts)
            try:
                before, after = os.fstat(fd), os.fstat(check)
                if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                    self._fail("archive directory binding changed during scan")
            finally:
                os.close(check)
        finally:
            os.close(fd)

    @staticmethod
    def _stamp(st) -> tuple[int, ...]:
        return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns,
                st.st_ctime_ns, st.st_mode)

    def _regular_fd(self, parts: tuple[str, ...]):
        if not parts:
            self._fail("a file path is required")
        fd = -1
        try:
            with self.directory(parts[:-1]) as parent:
                # NONBLOCK prevents a FIFO open from hanging before fstat.
                fd = os.open(parts[-1], self._file_flags, dir_fd=parent)
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_dev != self._device:
                self._fail("strict read requires a regular file on the archive device")
            return fd, st
        except BaseException:
            if fd >= 0:
                os.close(fd)
            raise

    def _check_file_binding(self, parts, expected_stamp) -> None:
        try:
            fd, st = self._regular_fd(parts)
        except FileNotFoundError:
            if expected_stamp is None:
                return
            self._fail("observed archive file disappeared")
        try:
            if expected_stamp is None or self._stamp(st) != expected_stamp:
                self._fail("archive file binding changed during acquisition")
        finally:
            os.close(fd)

    def _remember(self, parts, stamp, digest) -> None:
        observation = (stamp, digest)
        previous = self._files.setdefault(parts, observation)
        if previous != observation:
            self._fail("repeated archive read changed identity or bytes")

    def _bounded_stream(self, fp, kind: str, file_limit: int) -> bytes:
        data = bytearray()
        # GzipFile.read() may decode ahead into its BufferedReader. read1()
        # forwards one bounded raw read; ordinary file snapshots are unbuffered.
        read = fp.read1 if kind == "raw" else fp.read
        while True:
            remaining = min(file_limit - len(data),
                            self._limits[kind] - self._used[kind])
            piece = read(min(64 * 1024, remaining + 1))
            if not piece:
                return bytes(data)
            # At most one refusal sentinel byte is consumed beyond an allowance.
            # It is counted and never appended or returned.
            self._used[kind] += len(piece)
            if (len(piece) > remaining or self._used[kind] > self._limits[kind]):
                self._fail("bounded " + kind + " read exceeded its byte allowance")
            data.extend(piece)

    def _file_bytes(self, relative, kind: str, *, file_limit: int,
                    missing_ok: bool = False) -> bytes | None:
        self._alive()
        parts = self._parts(relative)
        try:
            fd, before = self._regular_fd(parts)
        except FileNotFoundError:
            if not missing_ok:
                raise
            self._remember(parts, None, None)
            return None
        try:
            allowance = min(file_limit, self._limits[kind] - self._used[kind])
            if before.st_size < 0 or before.st_size > allowance:
                self._fail("encoded " + kind + " file exceeds remaining allowance")
            # Unbuffered reads keep actual file reads within the charged allowance.
            with os.fdopen(fd, "rb", buffering=0) as fp:
                fd = -1
                data = self._bounded_stream(fp, kind, file_limit)
                after = os.fstat(fp.fileno())
            stamp = self._stamp(before)
            if self._stamp(after) != stamp or len(data) != before.st_size:
                self._fail("archive file changed while being read")
            self._check_file_binding(parts, stamp)
            self._remember(parts, stamp, hashlib.sha256(data).hexdigest())
            return data
        finally:
            if fd >= 0:
                os.close(fd)

    def read_metadata(self, relative, *, missing_ok: bool = False) -> dict[str, Any] | None:
        body = self._file_bytes(relative, "metadata",
                                file_limit=MAX_CENSUS_METADATA_FILE_BYTES,
                                missing_ok=missing_ok)
        if body is None:
            return None

        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    self._fail("duplicate metadata JSON key")
                result[key] = value
            return result

        def invalid_constant(_value):
            self._fail("nonfinite metadata JSON constant")

        try:
            record = json.loads(body.decode("utf-8"), object_pairs_hook=unique_object,
                                parse_constant=invalid_constant)
        except (UnicodeError, ValueError, RecursionError) as exc:
            self._fail("unreadable bounded metadata: " + type(exc).__name__)
        if not isinstance(record, dict):
            self._fail("bounded metadata must be a JSON object")
        return record

    def read_normalized(self, relative) -> bytes:
        return self._file_bytes(relative, "normalized",
                                file_limit=MAX_CENSUS_NORMALIZED_BYTES)

    def read_raw_gzip(self, relative, *, expected_raw_bytes: int,
                      expected_compressed_bytes: int | None = None) -> bytes:
        self._alive()
        if (type(expected_raw_bytes) is not int or expected_raw_bytes < 0
                or expected_raw_bytes > self._limits["raw"] - self._used["raw"]):
            self._fail("raw receipt length exceeds remaining allowance")
        if expected_compressed_bytes is not None and (
                type(expected_compressed_bytes) is not int or expected_compressed_bytes < 0
                or expected_compressed_bytes > self._limits["compressed"] - self._used["compressed"]):
            self._fail("compressed receipt length exceeds remaining allowance")
        compressed = self._file_bytes(relative, "compressed",
                                      file_limit=MAX_CENSUS_COMPRESSED_BYTES)
        if expected_compressed_bytes is not None and len(compressed) != expected_compressed_bytes:
            self._fail("compressed receipt byte-length mismatch")
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as fp:
                raw = self._bounded_stream(fp, "raw", expected_raw_bytes)
        except (OSError, EOFError) as exc:
            self._fail("invalid retained gzip: " + type(exc).__name__)
        if len(raw) != expected_raw_bytes:
            self._fail("source raw receipt byte-length mismatch")
        return raw

    def verify_bindings(self) -> None:
        """Recheck observed bindings; this does not lock or rescan the archive."""
        self._alive()
        current = self._absolute_directory_fd(self.root)
        try:
            st = os.fstat(current)
            if (st.st_dev, st.st_ino) != self._root_identity:
                self._fail("archive root binding changed during acquisition")
        finally:
            os.close(current)
        for parts, identity in tuple(self._directories.items()):
            fd = self._directory_fd(parts)
            try:
                st = os.fstat(fd)
                if (st.st_dev, st.st_ino) != identity:
                    self._fail("archive directory binding changed")
            finally:
                os.close(fd)
        for parts, (stamp, _digest) in tuple(self._files.items()):
            self._check_file_binding(parts, stamp)



def verified_raw(archive_root: Path, receipt: dict[str, Any], *,
                 read_context: BoundedTiingoRead | None = None) -> bytes:
    if receipt.get("vendor") != "tiingo":
        raise TiingoArchiveError("non-Tiingo receipt")
    rel = Path(receipt["raw_path"])
    if rel.is_absolute() or ".." in rel.parts:
        raise TiingoArchiveError("raw receipt escaped lake root")
    if read_context is not None:
        read_context.assert_root(archive_root, check_mount=False)
        compressed = receipt.get("compressed_bytes")
        if "compressed_bytes" in receipt and type(compressed) is not int:
            raise TiingoArchiveError("invalid compressed receipt byte length")
        raw = read_context.read_raw_gzip(
            rel, expected_raw_bytes=receipt.get("raw_bytes"),
            expected_compressed_bytes=compressed,
        )
    else:
        target = (archive_root / rel).resolve()
        if not target.is_relative_to(archive_root.resolve()):
            raise TiingoArchiveError("raw path escapes external drive")
        if target.stat().st_size > MAX_RAW_MATERIALIZE_BYTES:
            raise TiingoArchiveError("raw compressed partition exceeds research batch limit")
        # Decompress bounded to prevent a tiny gzip bomb from exhausting memory.
        with gzip.open(target, "rb") as fp:
            raw = fp.read(MAX_RAW_MATERIALIZE_BYTES + 1)
        if len(raw) > MAX_RAW_MATERIALIZE_BYTES:
            raise TiingoArchiveError("raw uncompressed partition exceeds research batch limit")
    if hashlib.sha256(raw).hexdigest() != receipt["raw_sha256"]:
        raise TiingoArchiveError("raw source digest mismatch")
    validate_receipt(receipt)
    return raw


def materialize_one(root: Path, receipt: dict[str, Any], *,
                    free_floor: int = MIN_FREE_BYTES,
                    dry_run: bool = False) -> dict[str, Any]:
    require_space(root, floor=free_floor)
    raw = verified_raw(root, receipt)
    try:
        rows = research_rows(raw, receipt)
    except (TypeError, ValueError, KeyError, OverflowError) as err:
        raise TiingoArchiveError("source payload cannot be normalized") from err
    if rows is None:
        return {"status": "RAW_ONLY", "reason": "NO_REVIEWED_L1_PROJECTOR",
                "source": receipt.get("source")}
    if len(rows) > MAX_OUTPUT_ROWS:
        raise TiingoArchiveError("normalized row cap exceeded")
    if not rows:
        return {"status": "EMPTY_NORMALIZED", "rows": 0,
                "source": receipt.get("source")}
    day = capture_day(receipt.get("observed_at_utc") or receipt.get("first_received_at_utc"))
    source = receipt.get("source") or "boats-firehose"
    digest = receipt["raw_sha256"]
    identity = receipt_identity(receipt)
    # Retain established content paths when unambiguous; context collisions use
    # the exact receipt identity. Never replace or rewrite an older view.
    content_manifest = root / "manifests" / source / day / (digest + ".json")
    previous = None
    if content_manifest.is_symlink() or not content_manifest.resolve().is_relative_to(root.resolve()):
        raise TiingoArchiveError("materialized path escapes archive")
    if content_manifest.is_file():
        try:
            previous = json.loads(content_manifest.read_text())
        except (OSError, ValueError) as exc:
            raise TiingoArchiveError("existing materialized manifest is corrupt") from exc
        if not isinstance(previous, dict):
            raise TiingoArchiveError("existing materialized manifest is invalid")
    collision = False
    for index, file in enumerate((root / "receipts" / source / day).glob(f"*{digest[:24]}*.json")):
        if index >= 2048:
            raise TiingoArchiveError("too many candidate source contexts")
        if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()) or file.stat().st_size > 1_000_000:
            raise TiingoArchiveError("source receipt escapes bounded archive evidence")
        try:
            candidate = json.loads(file.read_text())
        except (OSError, ValueError) as exc:
            raise TiingoArchiveError("source context receipt is unreadable") from exc
        if candidate.get("raw_sha256") == digest and validate_receipt(candidate) != identity:
            collision = True
    artifact_id = digest
    if previous and previous.get("source_receipt_id") == identity:
        pass
    elif collision or (previous and previous.get("source_receipt_id") not in (None, identity)):
        artifact_id = identity
    dest = root / "normalized" / source / day / (artifact_id + ".parquet")
    manifest_path = root / "manifests" / source / day / (artifact_id + ".json")
    for target in (dest, manifest_path):
        if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
            raise TiingoArchiveError("materialized path escapes archive")
    file_exists = dest.is_file()
    if manifest_path.is_file() and not file_exists:
        raise TiingoArchiveError("retained manifest lacks its original Parquet; no rewrite")
    if dry_run:
        return {"status": "WOULD_REPAIR" if file_exists else "WOULD_WRITE",
                "rows": len(rows), "source": source,
                "path": dest.relative_to(root).as_posix()}
    try:
        import pyarrow as pa  # type: ignore[import-not-found]
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError as err:
        raise TiingoArchiveError("pyarrow is required for L1 Parquet") from err

    # Union columns across Q/T/B shapes; pyarrow from_pylist otherwise silently
    # drops fields present only in later rows (loss of sale-condition or quotes).
    keys = sorted({k for row in rows for k in row})
    table = pa.Table.from_pylist([{k: row.get(k) for k in keys} for row in rows])
    if file_exists and manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text())
            legacy = "source_receipt_id" not in manifest and "receipt_id" not in receipt
            expected_rows = table.to_pylist()
            if legacy:
                expected_rows = [{k: v for k, v in row.items() if k != "source_receipt_id"}
                                 for row in expected_rows]
            if (manifest.get("source_sha256") != digest
                    or (not legacy and manifest.get("source_receipt_id") != identity)
                    or manifest.get("source_observed_at_utc") != (receipt.get("observed_at_utc") or receipt.get("first_received_at_utc"))
                    or manifest.get("output_path") != dest.relative_to(root).as_posix()
                    or manifest.get("output_sha256") != hashlib.sha256(dest.read_bytes()).hexdigest()
                    or pq.read_table(dest).to_pylist() != expected_rows):
                raise TiingoArchiveError("existing materialized view disagrees with original source")
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            raise TiingoArchiveError("existing materialized view is corrupt") from exc
        return {"status": "EXISTS", "rows": len(rows), "source": source,
                "path": dest.relative_to(root).as_posix(), "receipt_id": identity}
    if file_exists:
        # A crash may leave a fully written Parquet without its manifest.
        # Repair only after comparing exact normalized source row content.
        if pq.read_table(dest).to_pylist() != table.to_pylist():
            raise TiingoArchiveError("orphaned Parquet disagrees with raw source")
        created = False
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".parquet-", dir=str(dest.parent))
        os.close(fd)
        try:
            pq.write_table(table, tmp, compression="zstd")
            with open(tmp, "rb") as fp:
                os.fsync(fp.fileno())
            try:
                os.link(tmp, dest)
                created = True
            except FileExistsError:
                created = False
        finally:
            Path(tmp).unlink(missing_ok=True)
        if not created and pq.read_table(dest).to_pylist() != table.to_pylist():
            raise TiingoArchiveError("concurrent Parquet disagrees with raw source")
    out = {"status": "WRITTEN" if created else "REPAIRED_MANIFEST",
           "source": source, "rows": len(rows),
           "path": dest.relative_to(root).as_posix()}
    manifest = {
        "schema": "mastermind.tiingo.materialized_receipt.v1",
        "source_sha256": digest,
        "source_receipt_id": identity,
        "source_receipt_schema": receipt["schema"],
        "source_vendor": "tiingo",
        "view_schema": SCHEMA_VERSION,
        "output_path": out["path"],
        "output_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        "rows": len(rows), "columns": keys,
        "dataos_identity_admitted": False,
        "pit_backtest_eligible": False,
        "redistribution_admitted": False,
        "source_observed_at_utc": receipt.get("observed_at_utc")
                                  or receipt.get("first_received_at_utc"),
    }
    _publish_once(
        manifest_path,
        (json.dumps(manifest, sort_keys=True) + "\n").encode("utf-8"))
    try:
        published = json.loads(manifest_path.read_text())
        if published != manifest:
            raise TiingoArchiveError("published manifest disagrees with original source")
    except (OSError, ValueError) as exc:
        raise TiingoArchiveError("published manifest is corrupt") from exc
    return out


def materialize_many(root: Path = DEFAULT_ARCHIVE, *,
                     max_receipts: int = 500,
                     source_filter: str | None = None,
                     dry_run: bool = True,
                     check_mount: bool = True,
                     free_floor: int = MIN_FREE_BYTES) -> dict[str, Any]:
    if max_receipts < 1 or max_receipts > 100_000:
        raise ValueError("invalid receipt budget")
    base = require_external_root(root, check_mount=check_mount)
    result: dict[str, Any] = {
        "seen": 0, "written": 0, "existing": 0, "raw_only": 0,
        "empty": 0, "would_write": 0, "refused": 0, "errors": [],
        "dry_run": dry_run, "raw_receipts_total": None,
        "scope": "RESEARCH_ONLY_NOT_CANONICAL",
    }
    if not (base / "receipts").exists():
        return result
    for file in sorted((base / "receipts").rglob("*.json")):
        if result["seen"] >= max_receipts:
            result["truncated"] = True
            break
        try:
            receipt = json.loads(file.read_text())
            if source_filter and receipt.get("source", "boats-firehose") != source_filter:
                continue
            result["seen"] += 1
            out = materialize_one(base, receipt, dry_run=dry_run,
                                  free_floor=free_floor)
            status = out["status"]
            bucket = {
                "WRITTEN": "written", "EXISTS": "existing", "RAW_ONLY": "raw_only",
                "EMPTY_NORMALIZED": "empty", "WOULD_WRITE": "would_write",
                "WOULD_REPAIR": "would_write", "REPAIRED_MANIFEST": "written",
            }[status]
            result[bucket] += 1
        except (OSError, ValueError, KeyError, TiingoArchiveError) as err:
            result["refused"] += 1
            if len(result["errors"]) < 20:
                result["errors"].append({
                    "receipt": file.relative_to(base).as_posix(),
                    "reason": type(err).__name__,
                })
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-receipts", type=int, default=500)
    p.add_argument("--source", help="materialize only one vendor product")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    try:
        outcome = materialize_many(max_receipts=args.max_receipts,
                                   source_filter=args.source,
                                   dry_run=args.dry_run)
    except (ValueError, TiingoArchiveError) as err:
        print(json.dumps({"status": "REFUSED", "reason": str(err)}))
        return 2
    print(json.dumps(outcome, indent=2))
    return 2 if outcome["refused"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
