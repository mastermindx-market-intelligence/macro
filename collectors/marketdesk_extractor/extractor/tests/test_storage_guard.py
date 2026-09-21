from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from marketdesk_extractor import storage as storage_mod
from marketdesk_extractor.config import Config
from marketdesk_extractor.download import download_one
from marketdesk_extractor.storage import (
    StorageGuardError,
    VolumeInfo,
)


GIB = 1024 ** 3


def _cfg(tmp_path, monkeypatch, *, outside_raw: bool = False) -> tuple[Config, object, object]:
    volume = tmp_path / "STORAGE"
    root = volume / "MastermindX" / "marketdesk"
    root.mkdir(parents=True)
    paths = {
        "MARKETDESK_STORAGE_VOLUME": str(volume),
        "MARKETDESK_STORAGE_ROOT": str(root),
        "MARKETDESK_STORAGE_VOLUME_UUID": "EXPECTED-UUID",
        "MARKETDESK_STORAGE_MIN_FREE_GIB": "100",
        "MARKETDESK_PROFILE_DIR": str(root / "browser_profile"),
        "DATABASE_URL": str(root / "db" / "marketdesk.sqlite"),
        "OUTPUT_DIR": str(root / "data"),
        "RAW_PDF_DIR": str(
            (tmp_path / "internal-raw") if outside_raw else (root / "data" / "raw_pdfs")
        ),
        "MARKDOWN_DIR": str(root / "data" / "markdown"),
        "METADATA_DIR": str(root / "data" / "metadata"),
        "MANIFEST_DIR": str(root / "data" / "manifests"),
        "LOG_DIR": str(root / "logs"),
        "MARKETDESK_PROFILES": "",
    }
    for name, value in paths.items():
        monkeypatch.setenv(name, value)
    cfg = Config.from_env(tmp_path / "does-not-exist.env")
    return cfg, volume, root


def _volume_info(volume, *, uuid: str = "EXPECTED-UUID", free_gib: int = 500):
    return VolumeInfo(
        mount_point=volume.resolve(),
        volume_uuid=uuid,
        external=True,
        writable=True,
        free_bytes=free_gib * GIB,
        total_bytes=1000 * GIB,
    )


def test_external_guard_accepts_exact_volume_and_creates_only_children(
    tmp_path, monkeypatch
):
    cfg, volume, root = _cfg(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "marketdesk_extractor.storage.inspect_volume",
        lambda path: _volume_info(volume),
    )

    cfg.ensure_dirs()
    status = cfg.assert_storage_ready()

    assert status.volume_uuid == "EXPECTED-UUID"
    assert status.free_gib == 500
    assert cfg.database_url.parent.is_dir()
    assert cfg.raw_pdf_dir.is_dir()
    assert cfg.profile_dir.is_dir()
    assert all(path.resolve().is_relative_to(root.resolve()) for path in cfg.mutable_paths())


def test_external_guard_rejects_any_mutable_path_on_internal_disk(tmp_path, monkeypatch):
    cfg, volume, _ = _cfg(tmp_path, monkeypatch, outside_raw=True)
    monkeypatch.setattr(
        "marketdesk_extractor.storage.inspect_volume",
        lambda path: _volume_info(volume),
    )

    with pytest.raises(StorageGuardError, match="escapes storage root"):
        cfg.ensure_dirs()

    assert not cfg.raw_pdf_dir.exists()


def test_external_guard_rejects_wrong_volume_uuid(tmp_path, monkeypatch):
    cfg, volume, _ = _cfg(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "marketdesk_extractor.storage.inspect_volume",
        lambda path: _volume_info(volume, uuid="WRONG-UUID"),
    )

    with pytest.raises(StorageGuardError, match="wrong storage volume"):
        cfg.ensure_dirs()


def test_external_guard_stops_at_free_space_floor(tmp_path, monkeypatch):
    cfg, volume, _ = _cfg(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "marketdesk_extractor.storage.inspect_volume",
        lambda path: _volume_info(volume, free_gib=99),
    )

    with pytest.raises(StorageGuardError, match="storage safety floor reached"):
        cfg.ensure_dirs()


def test_download_does_not_spend_provider_attempt_when_storage_is_unavailable():
    class GuardedConfig:
        def assert_storage_ready(self, **kwargs):
            raise StorageGuardError("external SSD missing")

    called = False

    class Client:
        def download_blob(self, blob_id):
            nonlocal called
            called = True
            return b"%PDF"

    with pytest.raises(StorageGuardError, match="external SSD missing"):
        download_one(
            GuardedConfig(),
            None,
            Client(),
            {"blob_id": "paper-1"},
        )

    assert called is False


def test_external_guard_times_out_a_hung_diskutil(monkeypatch):
    class FakeParent:
        def stat(self):
            return SimpleNamespace(st_dev=1)

    class FakeMount:
        parent = FakeParent()

        def is_dir(self):
            return True

        def stat(self):
            return SimpleNamespace(st_dev=2)

        def __str__(self):
            return "/Volumes/STORAGE"

    class FakeExecutable:
        def __init__(self, value):
            self.value = str(value)

        def exists(self):
            return True

        def __str__(self):
            return self.value

    observed = {}

    def hang(command, **kwargs):
        observed["timeout"] = kwargs.get("timeout")
        raise subprocess.TimeoutExpired(command, kwargs.get("timeout"))

    mount = FakeMount()
    monkeypatch.setattr(storage_mod, "_resolved", lambda _path: mount)
    monkeypatch.setattr(storage_mod, "Path", FakeExecutable)
    monkeypatch.setattr(storage_mod.os, "access", lambda *_args: True)
    monkeypatch.setattr(storage_mod.sys, "platform", "darwin")
    monkeypatch.setattr(storage_mod.subprocess, "run", hang)

    with pytest.raises(StorageGuardError, match="timed out"):
        storage_mod.inspect_volume("/Volumes/STORAGE")

    assert observed["timeout"] == 10.0

