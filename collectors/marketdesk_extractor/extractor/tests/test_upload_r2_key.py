"""Tests for upload_r2.R2Uploader.key() — no network, no boto3 calls."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from marketdesk_extractor.config import Config
from marketdesk_extractor.upload_r2 import R2Uploader


# ---------------------------------------------------------------------------
# fixture: disabled R2 config (no boto3 client instantiated)
# ---------------------------------------------------------------------------

@pytest.fixture()
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """Config with R2 disabled — R2Uploader.key() does NOT require credentials."""
    monkeypatch.setenv("R2_ENABLED", "false")
    monkeypatch.setenv("R2_PREFIX", "marketdesk")
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "db" / "t.sqlite"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RAW_PDF_DIR", str(tmp_path / "raw"))
    monkeypatch.setenv("MARKDOWN_DIR", str(tmp_path / "md"))
    monkeypatch.setenv("METADATA_DIR", str(tmp_path / "meta"))
    monkeypatch.setenv("MANIFEST_DIR", str(tmp_path / "manifests"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    return Config.from_env()


@pytest.fixture()
def uploader(cfg: Config) -> R2Uploader:
    # R2 disabled — __init__ does not import boto3
    return R2Uploader(cfg)


# ---------------------------------------------------------------------------
# key() — normal kinds
# ---------------------------------------------------------------------------

def test_key_raw_pdfs(uploader: R2Uploader) -> None:
    k = uploader.key("raw_pdfs", "2026-07-07", "paper.pdf")
    assert k == "marketdesk/raw_pdfs/2026-07-07/paper.pdf"


def test_key_markdown(uploader: R2Uploader) -> None:
    k = uploader.key("markdown", "2026-07-07", "paper.md")
    assert k == "marketdesk/markdown/2026-07-07/paper.md"


def test_key_metadata(uploader: R2Uploader) -> None:
    k = uploader.key("metadata", "2026-07-07", "paper.json")
    assert k == "marketdesk/metadata/2026-07-07/paper.json"


# ---------------------------------------------------------------------------
# key() — manifests special case (no date segment)
# ---------------------------------------------------------------------------

def test_key_manifests_omits_date_segment(uploader: R2Uploader) -> None:
    k = uploader.key("manifests", "2026-07-07", "2026-07-07.jsonl")
    assert k == "marketdesk/manifests/2026-07-07.jsonl"
    # must NOT have a double date
    assert k.count("2026-07-07") == 1


def test_key_manifests_filename_preserved(uploader: R2Uploader) -> None:
    k = uploader.key("manifests", "2026-07-08", "2026-07-08.jsonl")
    assert k.endswith("/2026-07-08.jsonl")


# ---------------------------------------------------------------------------
# key() — custom prefix
# ---------------------------------------------------------------------------

def test_key_uses_configured_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("R2_ENABLED", "false")
    monkeypatch.setenv("R2_PREFIX", "my-custom-prefix")
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "db" / "t.sqlite"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RAW_PDF_DIR", str(tmp_path / "raw"))
    monkeypatch.setenv("MARKDOWN_DIR", str(tmp_path / "md"))
    monkeypatch.setenv("METADATA_DIR", str(tmp_path / "meta"))
    monkeypatch.setenv("MANIFEST_DIR", str(tmp_path / "manifests"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg2 = Config.from_env()
    u2 = R2Uploader(cfg2)
    k = u2.key("raw_pdfs", "2026-07-07", "file.pdf")
    assert k.startswith("my-custom-prefix/")


# ---------------------------------------------------------------------------
# enabled property (no credentials -> False)
# ---------------------------------------------------------------------------

def test_enabled_false_when_r2_disabled(uploader: R2Uploader) -> None:
    assert uploader.enabled is False


def test_enabled_false_when_credentials_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("R2_ENABLED", "true")
    monkeypatch.setenv("R2_ACCOUNT_ID", "")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "")
    monkeypatch.setenv("R2_BUCKET", "")
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "db" / "t.sqlite"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RAW_PDF_DIR", str(tmp_path / "raw"))
    monkeypatch.setenv("MARKDOWN_DIR", str(tmp_path / "md"))
    monkeypatch.setenv("METADATA_DIR", str(tmp_path / "meta"))
    monkeypatch.setenv("MANIFEST_DIR", str(tmp_path / "manifests"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg2 = Config.from_env()
    u2 = R2Uploader(cfg2)
    assert u2.enabled is False
