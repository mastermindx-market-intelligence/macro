"""Production join of the private economic stage onto the public wire builder.

Synthetic fixtures only. These tests never fetch a story packet and never call
an EDGAR host. The workflow flag stays off.
"""
from __future__ import annotations

from datetime import datetime, timezone
from inspect import signature
import json
import logging
from pathlib import Path

import pytest

from engine.earnings_narrative.private_economic_stage import PrivateEconomicStageError
from scripts import build_earnings_public_wire as wire_builder
from scripts.build_earnings_public_wire import (
    CONTEXT_FILENAME,
    FEED_FILENAME,
    PRIVATE_CONTEXT_DIRNAME,
    PRIVATE_RECORDS_DIRNAME,
    ROUTE_CATALOG_FILENAME,
    WIRE_SITEMAP_FILENAME,
    BuildResult,
    PublicWireBuildError,
    build,
    publish_public_wire,
)
from tests.test_earnings_economic_refresh import (
    PINNED_NOW_ISO,
    _COMPANY_READER,
    _wire_publication,
)


def _snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _pinned_now() -> datetime:
    return datetime.fromisoformat(PINNED_NOW_ISO).astimezone(timezone.utc)


def test_offline_with_economic_refresh_raises_and_writes_nothing(tmp_path: Path) -> None:
    publication = _wire_publication(tmp_path / "inputs", "w1")
    public = tmp_path / "public"
    private = tmp_path / "private"
    now = _pinned_now()
    publish_public_wire(
        publication,
        out_dir=public,
        private_out_dir=private,
        company_reader=_COMPANY_READER,
        now=now,
    )
    marker = public / "marker.txt"
    marker.write_text("marker", encoding="utf-8")
    before_public = _snapshot(public)
    before_private = _snapshot(private)

    def _fetch(_url: str) -> bytes:
        raise AssertionError("fetch must not run")

    try:
        result = build(
            out_dir=public,
            private_out_dir=private,
            offline=True,
            economic_refresh={"acquisition": {"synthetic": True}},
            now=now,
            fetch=_fetch,
        )
    except PublicWireBuildError as exc:
        assert "offline" in str(exc)
        assert "economic refresh" in str(exc)
        assert _snapshot(public) == before_public
        assert _snapshot(private) == before_private
    else:
        pytest.fail(
            "DID NOT RAISE PublicWireBuildError; "
            f"source={result.source}; marker_unchanged={marker.read_bytes() == b'marker'}"
        )


def test_refresh_omitted_matches_refresh_left_unset(tmp_path: Path) -> None:
    publication = _wire_publication(tmp_path / "inputs", "w1")
    now = _pinned_now()
    omitted = tmp_path / "omitted"
    unset = tmp_path / "unset"
    publish_public_wire(
        publication,
        out_dir=omitted,
        private_out_dir=tmp_path / "omitted-private",
        company_reader=_COMPANY_READER,
        now=now,
    )
    publish_public_wire(
        publication,
        out_dir=unset,
        private_out_dir=tmp_path / "unset-private",
        company_reader=_COMPANY_READER,
        now=now,
        economic_refresh=None,
    )
    assert _snapshot(omitted) == _snapshot(unset)


def test_workflow_commands_stay_flag_off() -> None:
    repo = Path(__file__).resolve().parents[1]
    workflow = (repo / ".github" / "workflows" / "earnings-public-wire.yml").read_text(encoding="utf-8")
    builder = 'python -m scripts.build_earnings_public_wire --private-out-dir "$PRIVATE_STAGE"'
    publisher = 'python -m scripts.publish_earnings_private_store --source-dir "$PRIVATE_STAGE"'
    assert builder in workflow
    assert publisher in workflow
    assert workflow.index(builder) < workflow.index(publisher)
    assert "economic-refresh" not in workflow
    assert "economic-augment" not in workflow
    assert signature(build).parameters["economic_refresh"].default is None


def test_stage_runs_after_private_files_and_before_the_feed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _wire_publication(tmp_path / "inputs", "w1")
    public = tmp_path / "public"
    private = tmp_path / "private"
    seen: dict[str, bool] = {}

    def fake_stage(stage_dir, *, acquisition, prior_closure, observed_at, previous_manifest=None):
        root = Path(stage_dir)
        seen["context"] = (root / PRIVATE_CONTEXT_DIRNAME / CONTEXT_FILENAME).is_file()
        seen["records"] = any((root / PRIVATE_RECORDS_DIRNAME).glob("*.json"))
        seen["feed"] = (public / FEED_FILENAME).exists()
        seen["sitemap"] = (public / WIRE_SITEMAP_FILENAME).exists()
        seen["catalog"] = (public / ROUTE_CATALOG_FILENAME).exists()
        return {"wrote": False}

    monkeypatch.setattr(wire_builder, "augment_private_stage", fake_stage)
    publish_public_wire(
        publication,
        out_dir=public,
        private_out_dir=private,
        company_reader=_COMPANY_READER,
        now=_pinned_now(),
        economic_refresh={"acquisition": None},
    )
    assert seen["context"] is True
    assert seen["records"] is True
    assert seen["feed"] is False
    assert seen["sitemap"] is False
    assert seen["catalog"] is False


def test_stage_raise_leaves_feed_sitemap_and_catalog_unwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _wire_publication(tmp_path / "inputs", "w1")
    public = tmp_path / "public"
    private = tmp_path / "private"

    def fake_stage(stage_dir, *, acquisition, prior_closure, observed_at, previous_manifest=None):
        raise PrivateEconomicStageError("unsafe_path")

    monkeypatch.setattr(wire_builder, "augment_private_stage", fake_stage)
    with pytest.raises(PrivateEconomicStageError, match="unsafe_path"):
        publish_public_wire(
            publication,
            out_dir=public,
            private_out_dir=private,
            company_reader=_COMPANY_READER,
            now=_pinned_now(),
            economic_refresh={"acquisition": None},
        )
    assert (private / PRIVATE_CONTEXT_DIRNAME / CONTEXT_FILENAME).is_file()
    assert not (public / FEED_FILENAME).exists()
    assert not (public / WIRE_SITEMAP_FILENAME).exists()
    assert not (public / ROUTE_CATALOG_FILENAME).exists()


def _install_build_spy(monkeypatch: pytest.MonkeyPatch, captured: dict[str, object]) -> None:
    def fake_build(**kwargs: object) -> BuildResult:
        captured.clear()
        captured.update(kwargs)
        out = kwargs.get("out_dir")
        return BuildResult("manifest", "fresh", 0, Path(out) if out is not None else Path("."))

    monkeypatch.setattr(wire_builder, "build", fake_build)


def test_cli_without_the_flag_does_not_pass_economic_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    _install_build_spy(monkeypatch, captured)
    assert wire_builder.main([]) == 0
    assert captured.get("economic_refresh") is None


def test_cli_economic_refresh_forwards_a_synthetic_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "acquisition": {"synthetic": True},
        "prior_closure": None,
        "observed_at": "2026-07-31T00:00:00Z",
    }
    refresh = tmp_path / "refresh.json"
    refresh.write_text(json.dumps(payload), encoding="utf-8")
    captured: dict[str, object] = {}
    _install_build_spy(monkeypatch, captured)
    assert wire_builder.main(["--economic-refresh", str(refresh)]) == 0
    assert captured["economic_refresh"] == payload


def test_cli_economic_refresh_with_offline_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    refresh = tmp_path / "refresh.json"
    refresh.write_text(json.dumps({"acquisition": {"synthetic": True}}), encoding="utf-8")
    public = tmp_path / "public"
    public.mkdir()
    marker = public / "marker.txt"
    marker.write_text("marker", encoding="utf-8")
    before = _snapshot(public)

    def _fetch(*_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("fetch must not run")

    monkeypatch.setattr(wire_builder.requests, "get", _fetch)
    with caplog.at_level(logging.ERROR, logger="build_earnings_public_wire"):
        code = wire_builder.main([
            "--out-dir", str(public),
            "--offline",
            "--economic-refresh", str(refresh),
        ])
    assert code == 1
    assert "offline public wire build cannot apply an economic refresh" in caplog.text
    assert _snapshot(public) == before
    assert marker.read_text(encoding="utf-8") == "marker"
