#!/usr/bin/env python3
"""Build a deterministic research artifact without rewriting historical output.

A destination is create-only: identical replays are idempotent, whereas a
correction or another cutoff requires a different destination. Publication uses
an atomic hard link of a unique, complete sibling temporary file. A filesystem
that cannot provide that operation fails rather than falling back to overwrite.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
ROOT = _ROOT

from engine.macro_turnaround import (  # noqa: E402
    IndicatorSpec,
    MacroTurnaroundEngine,
    Observation,
    Phase,
    TurnaroundConfig,
    build_research_artifact,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON number: {value}")


_DESCRIPTOR_PUBLICATION_SUPPORTED = (
    hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
    and all(
        function in os.supports_dir_fd
        for function in (os.open, os.stat, os.unlink, os.link)
    )
    and os.stat in os.supports_follow_symlinks
    and os.link in os.supports_follow_symlinks
)


def _identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _require_descriptor_publication_support() -> None:
    if not _DESCRIPTOR_PUBLICATION_SUPPORTED:
        raise ValueError(
            "descriptor-bound immutable publication is unavailable on this platform"
        )


def _open_bound_parent(directory: Path) -> tuple[int, tuple[int, int]]:
    _require_descriptor_publication_support()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError as error:
        raise ValueError("could not bind immutable output parent directory") from error
    try:
        opened = os.fstat(descriptor)
        named = os.stat(directory, follow_symlinks=False)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or not stat.S_ISDIR(named.st_mode)
            or _identity(opened) != _identity(named)
        ):
            raise ValueError("immutable output parent changed during publication")
        return descriptor, _identity(opened)
    except BaseException:
        os.close(descriptor)
        raise


def _require_bound_parent(
    descriptor: int, directory: Path, identity: tuple[int, int]
) -> None:
    try:
        opened = os.fstat(descriptor)
        named = os.stat(directory, follow_symlinks=False)
    except OSError as error:
        raise ValueError("immutable output parent changed during publication") from error
    if (
        not stat.S_ISDIR(opened.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or _identity(opened) != identity
        or _identity(named) != identity
    ):
        raise ValueError("immutable output parent changed during publication")


def _existing_matches_at(descriptor: int, name: str, content: bytes) -> bool:
    try:
        named = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise ValueError("could not inspect immutable output") from error
    if stat.S_ISLNK(named.st_mode):
        raise ValueError("immutable output cannot be a symbolic link")
    if not stat.S_ISREG(named.st_mode):
        raise ValueError("immutable output must be a regular file")
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        file_descriptor = os.open(name, flags, dir_fd=descriptor)
    except FileNotFoundError as error:
        raise ValueError("immutable output changed during publication") from error
    except OSError as error:
        raise ValueError("could not open immutable output safely") from error
    try:
        opened = os.fstat(file_descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or _identity(opened) != _identity(named)
            or opened.st_size != named.st_size
            or opened.st_mtime_ns != named.st_mtime_ns
        ):
            raise ValueError("immutable output changed during publication")
        remaining = len(content) + 1
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(file_descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        final_opened = os.fstat(file_descriptor)
        try:
            final_named = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        except OSError as error:
            raise ValueError("immutable output changed during publication") from error
        if (
            _identity(final_opened) != _identity(opened)
            or _identity(final_named) != _identity(opened)
            or final_opened.st_size != opened.st_size
            or final_opened.st_mtime_ns != opened.st_mtime_ns
            or final_named.st_size != opened.st_size
            or final_named.st_mtime_ns != opened.st_mtime_ns
        ):
            raise ValueError("immutable output changed during publication")
    finally:
        os.close(file_descriptor)
    if b"".join(chunks) != content:
        raise ValueError(
            "immutable output already exists with different content; choose a new path"
        )
    return True


def _regular_identity_at(
    descriptor: int, name: str, *, label: str
) -> tuple[int, int]:
    try:
        value = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
    except OSError as error:
        raise ValueError(f"could not inspect {label}") from error
    if not stat.S_ISREG(value.st_mode):
        raise ValueError(f"{label} must be a regular file")
    return _identity(value)


def _remove_owned_output_at(
    descriptor: int, name: str, identity: tuple[int, int]
) -> None:
    try:
        current = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as error:
        raise ValueError("could not inspect installed immutable output for cleanup") from error
    if _identity(current) != identity:
        raise ValueError("installed immutable output identity changed before cleanup")
    try:
        os.unlink(name, dir_fd=descriptor)
    except OSError as error:
        raise ValueError("could not remove installed immutable output after refusal") from error


def _write_temporary_at(descriptor: int, name: str, content: bytes) -> str:
    temporary_name: str | None = None
    temporary_descriptor: int | None = None
    for _attempt in range(16):
        candidate = f".{name}.{os.urandom(16).hex()}.tmp"
        try:
            temporary_descriptor = os.open(
                candidate,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=descriptor,
            )
        except FileExistsError:
            continue
        except OSError as error:
            raise ValueError("could not create immutable output temporary file") from error
        temporary_name = candidate
        break
    if temporary_name is None or temporary_descriptor is None:
        raise ValueError("could not allocate immutable output temporary file")
    try:
        try:
            view = memoryview(content)
            written = 0
            while written < len(view):
                count = os.write(temporary_descriptor, view[written:])
                if count <= 0:
                    raise OSError("immutable output temporary write made no progress")
                written += count
            os.fsync(temporary_descriptor)
        finally:
            os.close(temporary_descriptor)
    except BaseException:
        try:
            os.unlink(temporary_name, dir_fd=descriptor)
        except FileNotFoundError:
            pass
        raise
    return temporary_name


def _same_filesystem_object(left: Path, right: Path) -> bool:
    try:
        return os.path.samefile(left, right)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as error:
        raise ValueError("could not establish output-path filesystem identity") from error


def _relative_parts_from_identity(path: Path, ancestor: Path) -> tuple[str, ...] | None:
    current = path.resolve(strict=False)
    anchor = ancestor.resolve(strict=False)
    suffix: list[str] = []
    while True:
        if _same_filesystem_object(current, anchor):
            return tuple(reversed(suffix))
        if current.parent == current:
            return None
        suffix.append(current.name)
        current = current.parent


def _alternate_ascii_case(name: str) -> str | None:
    for index, character in enumerate(name):
        if "a" <= character <= "z" or "A" <= character <= "Z":
            return name[:index] + character.swapcase() + name[index + 1 :]
    return None


def _filesystem_is_case_insensitive(existing_directory: Path) -> bool:
    directory = existing_directory.resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("output-path filesystem probe requires a directory")
    try:
        entries = sorted(directory.iterdir(), key=lambda entry: entry.name)
    except OSError as error:
        raise ValueError("could not inspect output-path filesystem case semantics") from error
    for entry in entries:
        alternate_name = _alternate_ascii_case(entry.name)
        if alternate_name is not None:
            return _same_filesystem_object(entry, directory / alternate_name)
    raise ValueError("could not establish output-path filesystem case semantics")


def _path_is_within_protected(output: Path, protected: Path) -> bool:
    destination = output.resolve(strict=False)
    protected_resolved = protected.resolve(strict=False)
    if destination == protected_resolved or protected_resolved in destination.parents:
        return True
    if _relative_parts_from_identity(destination, protected_resolved) is not None:
        return True

    protected_parent = protected.parent.resolve(strict=True)
    relative = _relative_parts_from_identity(destination, protected_parent)
    if relative is None or not relative:
        return False
    first_component = relative[0]
    if first_component == protected.name:
        return True
    if first_component.casefold() != protected.name.casefold():
        return False
    return _filesystem_is_case_insensitive(protected_parent)


def _assert_research_output_path(output: Path, *, root: Path | None = None) -> None:
    """Keep research artifacts out of canonical data and generated product paths."""
    protected_root = ROOT if root is None else root
    for directory in ("data", "site"):
        if _path_is_within_protected(output, protected_root / directory):
            raise ValueError(
                "output must remain outside canonical data/ and generated site/ paths"
            )


def _publish_immutable(
    output: Path, content: bytes, *, root: Path | None = None
) -> None:
    if output.is_symlink():
        raise ValueError("immutable output cannot be a symbolic link")
    destination = output.resolve(strict=False)
    if root is None:
        _assert_research_output_path(destination)
    else:
        _assert_research_output_path(destination, root=root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    parent_descriptor, parent_identity = _open_bound_parent(destination.parent)
    temporary_name: str | None = None
    installed_identity: tuple[int, int] | None = None
    try:
        try:
            _require_bound_parent(
                parent_descriptor, destination.parent, parent_identity
            )
            if root is None:
                _assert_research_output_path(destination)
            else:
                _assert_research_output_path(destination, root=root)
            _require_bound_parent(
                parent_descriptor, destination.parent, parent_identity
            )
            if _existing_matches_at(parent_descriptor, destination.name, content):
                _require_bound_parent(
                    parent_descriptor, destination.parent, parent_identity
                )
                return
            temporary_name = _write_temporary_at(
                parent_descriptor, destination.name, content
            )
            temporary_identity = _regular_identity_at(
                parent_descriptor, temporary_name, label="immutable output temporary file"
            )
            _require_bound_parent(
                parent_descriptor, destination.parent, parent_identity
            )
            try:
                # The descriptor confines both names to the verified parent and
                # the hard link cannot replace a winner from another process.
                os.link(
                    temporary_name,
                    destination.name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                installed_identity = temporary_identity
            except FileExistsError:
                if not _existing_matches_at(
                    parent_descriptor, destination.name, content
                ):
                    raise ValueError("immutable output changed during publication")
            _require_bound_parent(
                parent_descriptor, destination.parent, parent_identity
            )
            if not _existing_matches_at(
                parent_descriptor, destination.name, content
            ):
                raise ValueError("immutable output changed during publication")
            _require_bound_parent(
                parent_descriptor, destination.parent, parent_identity
            )
        except BaseException:
            if installed_identity is not None:
                _remove_owned_output_at(
                    parent_descriptor, destination.name, installed_identity
                )
            raise
    finally:
        try:
            if temporary_name is not None:
                try:
                    os.unlink(temporary_name, dir_fd=parent_descriptor)
                except FileNotFoundError:
                    pass
        finally:
            os.close(parent_descriptor)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.output.is_symlink():
            raise ValueError("immutable output cannot be a symbolic link")
        _assert_research_output_path(args.output)
        if args.input.resolve() == args.output.resolve():
            raise ValueError("input and output paths must be distinct")
        payload = json.loads(
            args.input.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(payload, dict):
            raise ValueError("input must be a JSON object")
        expected = {"as_of", "previous_phase", "config", "specs", "observations"}
        unknown = set(payload) - expected
        missing = expected - set(payload)
        if unknown or missing:
            raise ValueError(
                f"input fields mismatch; missing={sorted(missing)}, "
                f"unknown={sorted(unknown)}"
            )
        if not isinstance(payload["specs"], list):
            raise ValueError("specs must be a JSON array")
        if not isinstance(payload["observations"], dict):
            raise ValueError("observations must be a JSON object")
        for key, series in payload["observations"].items():
            if not isinstance(series, list):
                raise ValueError(f"observations[{key}] must be a JSON array")
        config = TurnaroundConfig.from_dict(payload["config"])
        specs = [IndicatorSpec.from_dict(item) for item in payload["specs"]]
        observations = {
            key: [Observation.from_dict(item) for item in values]
            for key, values in payload["observations"].items()
        }
        previous = (
            Phase(payload["previous_phase"])
            if payload["previous_phase"] is not None
            else None
        )
        assessment = MacroTurnaroundEngine(config).assess(
            observations, specs, payload["as_of"], previous_phase=previous,
        )
        artifact = build_research_artifact(assessment)
        content = (json.dumps(artifact, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
        _publish_immutable(args.output, content)
    except (OSError, TypeError, ValueError) as error:
        print(f"build_macro_turnaround_research: ERROR — {error}", file=sys.stderr)
        return 2
    print(
        "build_macro_turnaround_research: OK — "
        f"{artifact['phase']} as of {artifact['as_of']} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
