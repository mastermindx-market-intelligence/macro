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
        for function in (os.open, os.stat, os.unlink, os.link, os.mkdir)
    )
    and os.stat in os.supports_follow_symlinks
    and os.link in os.supports_follow_symlinks
)


_DirectoryIdentity = tuple[int, int]
_ProtectedNameIdentities = dict[str, _DirectoryIdentity | None]
_ProtectionState = tuple[
    int,
    Path,
    _DirectoryIdentity,
    _ProtectedNameIdentities,
]


def _identity(value: os.stat_result) -> _DirectoryIdentity:
    return value.st_dev, value.st_ino


def _require_descriptor_publication_support() -> None:
    if not _DESCRIPTOR_PUBLICATION_SUPPORTED:
        raise ValueError(
            "descriptor-bound immutable publication is unavailable on this platform"
        )


def _open_bound_parent(
    directory: Path,
    *,
    forbidden_identities: frozenset[_DirectoryIdentity] = frozenset(),
    create_missing: bool = True,
) -> tuple[int, _DirectoryIdentity]:
    _require_descriptor_publication_support()
    # The caller resolves and guards this path once. Re-resolving here would let
    # a swapped ancestor redirect the descriptor walk after that guard returns.
    frozen = directory
    if not frozen.is_absolute() or not frozen.anchor:
        raise ValueError("immutable output parent must be an absolute path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(frozen.anchor, flags)
    except OSError as error:
        raise ValueError("could not bind immutable output filesystem root") from error
    try:
        for component in frozen.parts[1:]:
            try:
                child_descriptor = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not create_missing:
                    raise ValueError(
                        "immutable output parent component disappeared while binding"
                    )
                try:
                    os.mkdir(component, 0o777, dir_fd=descriptor)
                except FileExistsError:
                    pass
                except OSError as error:
                    raise ValueError(
                        "could not create immutable output parent directory safely"
                    ) from error
                try:
                    child_descriptor = os.open(component, flags, dir_fd=descriptor)
                except OSError as error:
                    raise ValueError(
                        "could not bind immutable output parent directory safely"
                    ) from error
            except OSError as error:
                raise ValueError(
                    "could not bind immutable output parent without following symbolic links"
                ) from error
            try:
                child = os.fstat(child_descriptor)
                if not stat.S_ISDIR(child.st_mode):
                    raise ValueError(
                        "immutable output parent component must be a directory"
                    )
                if _identity(child) in forbidden_identities:
                    raise ValueError(
                        "immutable output parent enters canonical protected directory"
                    )
            except BaseException:
                os.close(child_descriptor)
                raise
            os.close(descriptor)
            descriptor = child_descriptor
        opened = os.fstat(descriptor)
        named = os.stat(frozen, follow_symlinks=False)
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


def _bind_protected_directory_identities(
    root: Path,
) -> tuple[
    tuple[int, ...],
    frozenset[_DirectoryIdentity],
    _ProtectionState,
]:
    try:
        frozen_root = root.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError("could not bind canonical protection root") from error
    root_descriptor, _root_identity = _open_bound_parent(
        frozen_root, create_missing=False
    )
    descriptors = [root_descriptor]
    identities: set[_DirectoryIdentity] = set()
    named_identities: _ProtectedNameIdentities = {}
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        for name in ("data", "site"):
            try:
                descriptor = os.open(name, flags, dir_fd=root_descriptor)
            except FileNotFoundError:
                named_identities[name] = None
                continue
            except OSError as error:
                raise ValueError(
                    f"could not bind canonical protected directory: {name}"
                ) from error
            try:
                opened = os.fstat(descriptor)
                named = os.stat(name, dir_fd=root_descriptor, follow_symlinks=False)
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or not stat.S_ISDIR(named.st_mode)
                    or _identity(opened) != _identity(named)
                ):
                    raise ValueError(
                        f"canonical protected directory changed while binding: {name}"
                    )
                identity = _identity(opened)
                identities.add(identity)
                named_identities[name] = identity
                descriptors.append(descriptor)
            except BaseException:
                os.close(descriptor)
                raise
        return (
            tuple(descriptors),
            frozenset(identities),
            (root_descriptor, frozen_root, _root_identity, named_identities),
        )
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _require_protected_directory_identities(
    protection_state: _ProtectionState,
) -> None:
    (
        root_descriptor,
        root_path,
        root_identity,
        named_identities,
    ) = protection_state
    try:
        opened_root = os.fstat(root_descriptor)
        named_root = os.stat(root_path, follow_symlinks=False)
    except OSError as error:
        raise ValueError("canonical protection root changed during publication") from error
    if (
        not stat.S_ISDIR(opened_root.st_mode)
        or not stat.S_ISDIR(named_root.st_mode)
        or _identity(opened_root) != root_identity
        or _identity(named_root) != root_identity
    ):
        raise ValueError("canonical protection root changed during publication")
    for name, expected_identity in named_identities.items():
        try:
            named = os.stat(name, dir_fd=root_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            if expected_identity is None:
                continue
            raise ValueError(
                f"canonical protected directory disappeared during publication: {name}"
            )
        except OSError as error:
            raise ValueError(
                f"could not revalidate canonical protected directory: {name}"
            ) from error
        if expected_identity is None:
            raise ValueError(
                f"canonical protected directory appeared during publication: {name}"
            )
        if not stat.S_ISDIR(named.st_mode) or _identity(named) != expected_identity:
            raise ValueError(
                f"canonical protected directory changed during publication: {name}"
            )


def _close_descriptors(descriptors: tuple[int, ...]) -> None:
    for descriptor in reversed(descriptors):
        os.close(descriptor)


def _require_bound_parent(
    descriptor: int, directory: Path, identity: _DirectoryIdentity
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


def _require_publication_bindings(
    descriptor: int,
    directory: Path,
    identity: _DirectoryIdentity,
    protection_state: _ProtectionState,
) -> None:
    _require_protected_directory_identities(protection_state)
    _require_bound_parent(descriptor, directory, identity)
    _require_protected_directory_identities(protection_state)


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
) -> _DirectoryIdentity:
    try:
        value = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
    except OSError as error:
        raise ValueError(f"could not inspect {label}") from error
    if not stat.S_ISREG(value.st_mode):
        raise ValueError(f"{label} must be a regular file")
    return _identity(value)


def _remove_owned_output_at(
    descriptor: int, name: str, identity: _DirectoryIdentity
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


_CaseSemanticsEntry = tuple[str, _DirectoryIdentity, int]
_CaseSemanticsCensus = tuple[_DirectoryIdentity, int, tuple[_CaseSemanticsEntry, ...]]


def _case_semantics_census(directory: Path) -> _CaseSemanticsCensus:
    try:
        directory_before = os.stat(directory, follow_symlinks=False)
        entries = sorted(directory.iterdir(), key=lambda entry: entry.name)
        rows: list[_CaseSemanticsEntry] = []
        for entry in entries:
            witness = os.stat(entry, follow_symlinks=False)
            rows.append(
                (entry.name, _identity(witness), stat.S_IFMT(witness.st_mode))
            )
        directory_after = os.stat(directory, follow_symlinks=False)
    except OSError as error:
        raise ValueError(
            "could not establish output-path filesystem case semantics"
        ) from error
    directory_mode = stat.S_IFMT(directory_before.st_mode)
    if (
        not stat.S_ISDIR(directory_before.st_mode)
        or _identity(directory_after) != _identity(directory_before)
        or stat.S_IFMT(directory_after.st_mode) != directory_mode
    ):
        raise ValueError(
            "could not establish output-path filesystem case semantics"
        )
    return _identity(directory_before), directory_mode, tuple(rows)


def _filesystem_is_case_insensitive(existing_directory: Path) -> bool:
    directory = existing_directory.resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("output-path filesystem probe requires a directory")
    census = _case_semantics_census(directory)
    entry_names = {entry_name for entry_name, _, _ in census[2]}
    for entry_name, _, entry_mode in census[2]:
        alternate_name = _alternate_ascii_case(entry_name)
        if alternate_name is None or stat.S_ISLNK(entry_mode):
            continue
        # Coexisting exact case-variant names prove that the namespace
        # distinguishes case. Their inode relationship is irrelevant:
        # hard links must not be mistaken for case-insensitive lookup.
        if alternate_name in entry_names:
            result = False
        else:
            result = _same_filesystem_object(
                directory / entry_name, directory / alternate_name
            )
        # Both the selected witness and the complete sorted directory census
        # are authority-bearing. Refuse if either changed while samefile()
        # followed the two pathnames; otherwise a removed or substituted
        # witness could be misclassified as proof of case-sensitive semantics.
        if _case_semantics_census(directory) != census:
            raise ValueError(
                "could not establish output-path filesystem case semantics"
            )
        return result
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


def _assert_research_output_path(
    output: Path,
    *,
    root: Path | None = None,
    protection_state: _ProtectionState | None = None,
) -> None:
    """Keep research artifacts out of canonical data and generated product paths."""
    if protection_state is not None:
        _require_protected_directory_identities(protection_state)
    protected_root = ROOT if root is None else root
    for directory in ("data", "site"):
        if _path_is_within_protected(output, protected_root / directory):
            raise ValueError(
                "output must remain outside canonical data/ and generated site/ paths"
            )
    if protection_state is not None:
        _require_protected_directory_identities(protection_state)


def _publish_immutable(
    output: Path, content: bytes, *, root: Path | None = None
) -> None:
    protected_root = ROOT if root is None else root
    (
        protection_descriptors,
        protected_identities,
        protection_state,
    ) = _bind_protected_directory_identities(protected_root)
    try:
        _publish_immutable_with_protected_identities(
            output,
            content,
            root=root,
            protected_identities=protected_identities,
            protection_state=protection_state,
        )
    finally:
        _close_descriptors(protection_descriptors)


def _publish_immutable_with_protected_identities(
    output: Path,
    content: bytes,
    *,
    root: Path | None,
    protected_identities: frozenset[_DirectoryIdentity],
    protection_state: _ProtectionState,
) -> None:
    if output.is_symlink():
        raise ValueError("immutable output cannot be a symbolic link")
    destination = output.resolve(strict=False)
    if root is None:
        _assert_research_output_path(
            destination, protection_state=protection_state
        )
    else:
        _assert_research_output_path(
            destination, root=root, protection_state=protection_state
        )
    parent_descriptor, parent_identity = _open_bound_parent(
        destination.parent, forbidden_identities=protected_identities
    )
    temporary_name: str | None = None
    installed_identity: _DirectoryIdentity | None = None
    try:
        try:
            _require_publication_bindings(
                parent_descriptor,
                destination.parent,
                parent_identity,
                protection_state,
            )
            if root is None:
                _assert_research_output_path(
                    destination, protection_state=protection_state
                )
            else:
                _assert_research_output_path(
                    destination, root=root, protection_state=protection_state
                )
            _require_publication_bindings(
                parent_descriptor,
                destination.parent,
                parent_identity,
                protection_state,
            )
            if _existing_matches_at(parent_descriptor, destination.name, content):
                _require_publication_bindings(
                    parent_descriptor,
                    destination.parent,
                    parent_identity,
                    protection_state,
                )
                return
            temporary_name = _write_temporary_at(
                parent_descriptor, destination.name, content
            )
            temporary_identity = _regular_identity_at(
                parent_descriptor, temporary_name, label="immutable output temporary file"
            )
            _require_publication_bindings(
                parent_descriptor,
                destination.parent,
                parent_identity,
                protection_state,
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
            _require_publication_bindings(
                parent_descriptor,
                destination.parent,
                parent_identity,
                protection_state,
            )
            if not _existing_matches_at(
                parent_descriptor, destination.name, content
            ):
                raise ValueError("immutable output changed during publication")
            _require_publication_bindings(
                parent_descriptor,
                destination.parent,
                parent_identity,
                protection_state,
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
