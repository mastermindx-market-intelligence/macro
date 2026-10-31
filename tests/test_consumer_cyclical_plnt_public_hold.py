"""The PLNT synthetic fixture card is held from the public carrier.

Every ``*.html`` under ``site/`` is served anonymously, so the committed
synthetic fixture card must never be written to a public root. The builder
raises ``PublicCarrierHold`` for the repository root and ``lib.config.ROOT``
BEFORE the packet is built or any byte is written; ``main`` treats the hold
as a designed outcome (exit 0, one stderr line). These tests pin that hold.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lib.config  # noqa: E402
import lib.pages  # noqa: E402
import scripts.build_consumer_cyclical_plnt_page as plnt  # noqa: E402
from scripts.build_consumer_cyclical_plnt_page import (  # noqa: E402
    PAGE_NAME,
    PublicCarrierHold,
    _REPO_ROOT,
    main,
    render,
)

ROOT = Path(__file__).resolve().parents[1]


def _recording_write_page(writes: list[Path]):
    """A ``lib.pages.write_page`` stub that records destinations."""

    def _write(path: Path, html: str, **kwargs: object) -> Path:
        writes.append(Path(path))
        return Path(path)

    return _write


def test_render_refuses_the_repo_root_and_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The repository root raises the hold; nothing reaches write_page.

    The same directory spelled relatively (cwd + ``Path(".")``) must resolve
    to the same refusal, so a caller cannot dodge the hold by path spelling.
    """
    writes: list[Path] = []
    monkeypatch.setattr(lib.pages, "write_page", _recording_write_page(writes))
    with pytest.raises(PublicCarrierHold):
        render(_REPO_ROOT)
    assert writes == []
    monkeypatch.chdir(_REPO_ROOT)
    with pytest.raises(PublicCarrierHold):
        render(Path("."))
    assert writes == []


def test_render_refuses_before_reading_the_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hold fires BEFORE build_packet: no fixture read on a public root."""

    def _must_not_run(*args: object, **kwargs: object) -> dict:
        raise AssertionError("build_packet ran on a public carrier root")

    monkeypatch.setattr(plnt, "build_packet", _must_not_run)
    with pytest.raises(PublicCarrierHold):
        render(_REPO_ROOT)


def test_render_refuses_the_config_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``lib.config.ROOT`` is also a held carrier; other roots render."""
    config_root = tmp_path / "carrier"
    config_root.mkdir()
    monkeypatch.setattr(lib.config, "ROOT", config_root)
    with pytest.raises(PublicCarrierHold):
        render(config_root)
    # The checkout stays held on its own, even when the configured root differs.
    with pytest.raises(PublicCarrierHold):
        render(_REPO_ROOT)
    elsewhere = tmp_path / "out-repo"
    page = render(elsewhere)
    assert page == elsewhere / "site" / PAGE_NAME
    assert page.exists()


def test_main_default_root_holds_quietly(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``main()`` treats the hold as designed: exit 0, stderr line, no page."""
    writes: list[Path] = []
    monkeypatch.setattr(lib.pages, "write_page", _recording_write_page(writes))
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "held" in captured.err
    assert writes == []


def test_committed_tree_has_no_public_card() -> None:
    """No committed public card, and no sitemap entry naming it."""
    assert not (ROOT / "site" / PAGE_NAME).exists()
    sitemap = ROOT / "site" / "sitemap.xml"
    if sitemap.exists():
        assert PAGE_NAME not in sitemap.read_text(encoding="utf-8")
