"""Narrow tests for the default-inert native read-observation seam."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lib.intl_macro_publication import (
    _native_read_observer,
    _read_stable_once,
    observe_native_reads,
)
from lib.intl_macro_publication import _read_stable_once as _imported_read_stable_once

_PAYLOAD = b"ezb-native-read-payload"


def _write_payload(tmp_path: Path) -> Path:
    target = tmp_path / "probe.bin"
    target.write_bytes(_PAYLOAD)
    return target


def test_default_scope_is_inert(tmp_path: Path) -> None:
    target = _write_payload(tmp_path)
    assert _native_read_observer.get() is None
    assert _read_stable_once(target, 1024) == _PAYLOAD
    with pytest.raises(FileNotFoundError):
        _read_stable_once(tmp_path / "absent.bin", 1024)


def test_observer_invoked_before_file_is_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _write_payload(tmp_path)
    events: list[tuple[str, str]] = []
    real_open = os.open

    def spy_open(path: object, *args: object, **kwargs: object) -> int:
        try:
            events.append(("open", os.fspath(path)))
        except TypeError:
            pass
        return real_open(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "open", spy_open)

    def observer(path: Path) -> None:
        events.append(("observe", os.fspath(path)))

    with observe_native_reads(observer):
        assert _read_stable_once(target, 1024) == _PAYLOAD

    assert [event for event in events if event[1] == str(target)] == [
        ("observe", str(target)),
        ("open", str(target)),
    ]


def test_missing_dependency_is_observed(tmp_path: Path) -> None:
    absent = tmp_path / "absent.bin"
    observed: list[Path] = []
    with observe_native_reads(observed.append):
        with pytest.raises(FileNotFoundError):
            _read_stable_once(absent, 1024)
    assert observed == [absent]
    assert isinstance(observed[0], Path)


def test_observer_failure_propagates(tmp_path: Path) -> None:
    target = _write_payload(tmp_path)

    def failing_observer(path: Path) -> None:
        raise RuntimeError("observer refused the native read")

    with observe_native_reads(failing_observer):
        with pytest.raises(RuntimeError, match="observer refused"):
            _read_stable_once(target, 1024)
    assert target.read_bytes() == _PAYLOAD


def test_imported_alias_still_observes(tmp_path: Path) -> None:
    target = _write_payload(tmp_path)
    observed: list[Path] = []
    with observe_native_reads(observed.append):
        assert _imported_read_stable_once(target, 1024) == _PAYLOAD
    assert observed == [target]


def test_nested_scopes_restore_previous_observer(tmp_path: Path) -> None:
    target = _write_payload(tmp_path)
    outer_seen: list[Path] = []
    inner_seen: list[Path] = []

    with observe_native_reads(outer_seen.append):
        with observe_native_reads(inner_seen.append):
            assert _read_stable_once(target, 1024) == _PAYLOAD
        assert _read_stable_once(target, 1024) == _PAYLOAD

    assert inner_seen == [target]
    assert outer_seen == [target]
    assert _native_read_observer.get() is None


def test_observer_reset_after_scope_exits(tmp_path: Path) -> None:
    target = _write_payload(tmp_path)
    seen: list[Path] = []
    with observe_native_reads(seen.append):
        assert _read_stable_once(target, 1024) == _PAYLOAD
    assert seen == [target]
    assert _native_read_observer.get() is None
    assert _read_stable_once(target, 1024) == _PAYLOAD
    assert seen == [target]


def test_observer_reset_when_scope_body_raises(tmp_path: Path) -> None:
    target = _write_payload(tmp_path)
    seen: list[Path] = []
    with pytest.raises(ValueError, match="scope aborted"):
        with observe_native_reads(seen.append):
            assert _read_stable_once(target, 1024) == _PAYLOAD
            raise ValueError("scope aborted")
    assert seen == [target]
    assert _native_read_observer.get() is None
    assert _read_stable_once(target, 1024) == _PAYLOAD
    assert seen == [target]
