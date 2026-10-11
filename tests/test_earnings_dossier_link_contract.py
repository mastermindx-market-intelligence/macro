from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import json

import pytest

from engine.earnings_narrative.admission import build_press_admission, build_story_root_audit_binding
from engine.earnings_narrative.contracts import ContractError, canonical_json_sha256
from engine.earnings_narrative.story_packets import validate_story_packet
from engine.earnings_narrative.story_store import verify_story_packet_store, write_story_packet_generation
from engine.press import earnings_adapter
from scripts.stage_earnings_story_press import _derive_slot
from scripts import stage_earnings_story_press as ingress
from tests.test_earnings_story_packets import _body, _current_packet, _write_evidence
from tests.test_earnings_story_press_ingress import _R2, _ids, _r2_objects, _stub_stage


def _site(tmp_path: Path) -> Path:
    root = tmp_path / "site-repository"
    root.mkdir()
    page = root / "site/stocks/AAPL.html"
    page.parent.mkdir(parents=True)
    page.write_text("<!doctype html><title>AAPL dossier</title>", encoding="utf-8")
    for args in (
        ["init", "-q"], ["add", "site/stocks/AAPL.html"],
        ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "commit", "-qm", "Fixture dossier"],
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return root


def _compile(tmp_path: Path, *, dossier_root: Path | None = None):
    evidence, store = tmp_path / "evidence", tmp_path / "packets"
    _write_evidence(evidence, _body(), generated_at="2026-02-01T00:00:00Z")
    kwargs = {"dossier_root": dossier_root} if dossier_root is not None else {}
    _, manifest = write_story_packet_generation(store, evidence, **kwargs)
    return evidence, store, manifest, _current_packet(store, manifest)


def test_legacy_packet_bytes_and_generation_remain_identical(tmp_path: Path) -> None:
    _, _, manifest, packet = _compile(tmp_path)
    assert canonical_json_sha256(packet) == "a60afe811fbf9d066bc17dac327a8276ecf966115de342b98ec162acfbeff39e"
    assert manifest["generation_id"] == "e12b6a615770382a1d903cb225b1ad93"
    assert packet["press_slot"]["allowed_links"] == []


def test_link_is_immutable_before_admission_and_replays_after_site_changes(tmp_path: Path) -> None:
    root = _site(tmp_path)
    evidence, store, first, packet = _compile(tmp_path, dossier_root=root)
    assert packet["schema"] == "earnings.story_packet/v2"
    assert packet["press_slot"]["allowed_links"] == ["https://mastermind-x.com/stocks/AAPL.html"]
    assert packet["press_slot"]["canonical_emit_allowed"] is False
    frozen = canonical_json_sha256(packet)
    # The historical binding cannot depend on the mutable rendered filesystem.
    (root / "site/stocks/AAPL.html").unlink()
    validate_story_packet(packet, policy=first["policy"]["snapshot"])
    assert _derive_slot(packet) == packet["press_slot"]
    admission = build_press_admission(build_story_root_audit_binding(first, marker_etag="stable"), packet)
    assert admission["packet"]["schema"] == "earnings.story_packet/v2"
    assert admission["allow_emit"] is False
    assert canonical_json_sha256(packet) == frozen
    # Even explicit opt-in cannot churn an unchanged source or old hashes.
    _, same = write_story_packet_generation(store, evidence, dossier_root=root)
    assert same == first


@pytest.mark.parametrize("field,value", [
    ("url", "https://evil.example/stocks/AAPL.html"),
    ("url", "https://mastermind-x.com/stocks/MSFT.html"),
    ("url", "https://mastermind-x.com/stocks/AAPL.html?next=evil"),
    ("ticker", "MSFT"),
    ("extra", "caller-controlled"),
])
def test_link_binding_rejects_unplanned_destinations(tmp_path: Path, field: str, value: str) -> None:
    _, _, manifest, packet = _compile(tmp_path, dossier_root=_site(tmp_path))
    forged = deepcopy(packet)
    forged["dossier_link"][field] = value
    with pytest.raises(ContractError):
        validate_story_packet(forged, policy=manifest["policy"]["snapshot"])


def test_construction_rejects_unshipped_dossier_and_slot_append(tmp_path: Path) -> None:
    root = _site(tmp_path)
    subprocess.run(["git", "-C", str(root), "rm", "-q", "site/stocks/AAPL.html"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture",
                    "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Remove dossier"], check=True)
    with pytest.raises(ContractError, match="dossier"):
        _compile(tmp_path, dossier_root=root)
    _, _, manifest, legacy = _compile(tmp_path)
    legacy["press_slot"]["allowed_links"].append("https://mastermind-x.com/stocks/AAPL.html")
    with pytest.raises(ContractError, match="adapter"):
        validate_story_packet(legacy, policy=manifest["policy"]["snapshot"])


def test_mixed_legacy_ancestor_and_linked_correction_keep_full_replay(tmp_path: Path) -> None:
    root = _site(tmp_path)
    evidence, store, first, legacy = _compile(tmp_path)
    _write_evidence(evidence, _body(guidance="For the full year, we expect revenue of 510 million and an operating margin of 21%."),
                    generated_at="2026-02-02T00:00:00Z")
    _, second = write_story_packet_generation(store, evidence, dossier_root=root)
    linked = _current_packet(store, second)
    assert linked["schema"] == "earnings.story_packet/v2"
    assert linked["prior"]["packet_id"] == legacy["packet_id"]
    assert second["parent_generation_id"] == first["generation_id"]
    assert verify_story_packet_store(store)["status"] == "ready"
    assert _current_packet(store, first) == legacy


def test_current_consumer_rejects_removed_route_without_breaking_ancestor_replay(tmp_path: Path) -> None:
    root = _site(tmp_path)
    _, _, manifest, packet = _compile(tmp_path, dossier_root=root)
    subprocess.run(["git", "-C", str(root), "rm", "-q", "site/stocks/AAPL.html"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture",
                    "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Remove dossier"], check=True)
    validate_story_packet(packet, policy=manifest["policy"]["snapshot"])
    with pytest.raises(ContractError, match="dossier"):
        earnings_adapter.assert_dossier_link_current(packet["dossier_link"], ticker="AAPL", root=root)


def test_removed_current_dossier_fails_ingress_before_model_call(tmp_path: Path, monkeypatch) -> None:
    root = _site(tmp_path)
    evidence, store, manifest, packet = _compile(tmp_path, dossier_root=root)
    config = root / "config/press.yml"
    config.parent.mkdir()
    config.write_bytes((Path(__file__).resolve().parents[1] / "config/press.yml").read_bytes())
    subprocess.run(["git", "-C", str(root), "rm", "-q", "site/stocks/AAPL.html"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture",
                    "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Remove dossier"], check=True)
    calls = []

    def unexpected_stage(*args, **kwargs):
        calls.append(kwargs)
        raise AssertionError("model rail must not be reached")

    monkeypatch.setattr(ingress, "run_admitted_earnings_staging", unexpected_stage)
    destination = tmp_path / "isolated-stage"
    with pytest.raises(ContractError, match="dossier"):
        ingress.stage_exact_current_story(
            **_ids(manifest, packet), staging_dir=destination, root=root,
            s3=_R2(_r2_objects(evidence, store, manifest)), bucket="fixture",
        )
    assert calls == []
    assert not destination.exists()


def test_post_call_dossier_removal_quarantines_without_claiming_root_race(tmp_path: Path, monkeypatch) -> None:
    root = _site(tmp_path)
    evidence, store, manifest, packet = _compile(tmp_path, dossier_root=root)
    config = root / "config/press.yml"
    config.parent.mkdir()
    config.write_bytes((Path(__file__).resolve().parents[1] / "config/press.yml").read_bytes())
    calls = []
    _stub_stage(monkeypatch, calls)
    stage = ingress.run_admitted_earnings_staging

    def remove_route_after_stage(*args, **kwargs):
        result = stage(*args, **kwargs)
        subprocess.run(["git", "-C", str(root), "rm", "-q", "site/stocks/AAPL.html"], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Remove dossier"], check=True)
        return result

    monkeypatch.setattr(ingress, "run_admitted_earnings_staging", remove_route_after_stage)
    destination = tmp_path / "isolated-stage"
    with pytest.raises(ingress.EarningsStoryIngressError, match="dossier"):
        ingress.stage_exact_current_story(
            **_ids(manifest, packet), staging_dir=destination, root=root,
            s3=_R2(_r2_objects(evidence, store, manifest)), bucket="fixture",
        )
    summary = json.loads((destination / "_run_summary.json").read_text())
    assert summary["passed"] == 0
    assert summary["story_root_current_after_stage"] is True
    assert summary["dossier_link_current_after_stage"] is False
    staged = json.loads(next(p for p in destination.glob("press-*.json")).read_text())
    assert staged["status"] == "quarantined"
    assert staged["story_root_current_after_stage"] is True
    assert staged["dossier_link_current_after_stage"] is False
