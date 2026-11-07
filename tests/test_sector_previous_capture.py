"""Observed bootstrap absence and previous-Central publication fences."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path

import pytest

from lib import sector_input_capture as capture
from scripts import vps_live_orchestrator as owner
from tests.test_vps_live_orchestration import _gen_orchestrator, _gen_request, _gen_store_root

NOW = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)
CENTRAL = "sectordata/sector_central.json"


def publish(tmp_path, *, generation="g1", expected=None):
    orch = _gen_orchestrator(tmp_path, now=NOW)
    request = _gen_request(tmp_path, generation_id=generation, source_dir=generation,
        artifacts=((CENTRAL, {"as_of": "2026-11-05", "sectors": [
            {"id": "xlk", "name_zh": "科技", "score": 70}]}),))
    result = orch.publish_generation(request, expected_current_content_id=expected)
    assert result.status == "published", result.detail
    return orch, result


def read(root, *, bootstrap=False, clock=lambda: NOW + timedelta(seconds=1)):
    return capture.read_previous_sector_capture(generations_root=root,
        allow_bootstrap=bootstrap, clock=clock)


@pytest.mark.parametrize("make_domain,reason", [(False, "domain_absent"), (True, "selection_absent")])
def test_initialized_store_has_typed_positive_absence(tmp_path, make_domain, reason):
    root = tmp_path / "generations"
    root.mkdir()
    if make_domain:
        (root / "sector").mkdir()
    before = tuple(root.rglob("*"))
    with pytest.raises(owner.SelectedGenerationAbsent) as error:
        owner.read_selected_generation(generations_root=root, domain="sector", members=(CENTRAL,))
    assert isinstance(error.value, owner.SelectedGenerationUnavailable)
    assert error.value.reason == reason
    assert tuple(root.rglob("*")) == before
    with pytest.raises(capture.SectorInputCaptureError, match="bootstrap_not_enabled"):
        read(root)
    absent = read(root, bootstrap=True)
    assert absent.snapshot is None
    assert absent.expected_current_content_id is None
    assert absent.prior_sector_text is None
    assert absent.central_document() is None
    assert absent.input_lineage()["outcome"] == "observed_absent"
    assert absent.input_lineage()["absence_reason"] == reason
    assert tuple(root.rglob("*")) == before


@pytest.mark.parametrize("damage", [
    "missing_root", "root_file", "root_link", "domain_file", "domain_link",
    "dangling_pointer", "pointer_directory", "corrupt_pointer",
])
def test_unsafe_or_unavailable_store_is_never_bootstrap_absence(tmp_path, damage):
    root = tmp_path / "generations"
    if damage == "root_file":
        root.write_text("not a store")
    elif damage == "root_link":
        root.symlink_to(tmp_path / "missing-root", target_is_directory=True)
    elif damage != "missing_root":
        root.mkdir()
        domain = root / "sector"
        if damage == "domain_file":
            domain.write_text("not a domain")
        elif damage == "domain_link":
            domain.symlink_to(tmp_path / "missing-domain", target_is_directory=True)
        else:
            domain.mkdir()
            pointer = domain / "current.json"
            if damage == "dangling_pointer":
                pointer.symlink_to(tmp_path / "missing-pointer")
            elif damage == "pointer_directory":
                pointer.mkdir()
            else:
                pointer.write_text("{")
    with pytest.raises(owner.SelectedGenerationUnavailable) as error:
        owner.read_selected_generation(generations_root=root, domain="sector", members=(CENTRAL,))
    assert not isinstance(error.value, owner.SelectedGenerationAbsent)
    with pytest.raises(capture.SectorInputCaptureError, match="previous_selection_unavailable"):
        read(root, bootstrap=True)


def test_pointer_permission_failure_never_becomes_absence(tmp_path, monkeypatch):
    root = tmp_path / "generations"
    (root / "sector").mkdir(parents=True)
    pointer = root / "sector/current.json"
    pointer.write_text("{}")
    real_open = owner.os.open
    def denied(path, *args, **kwargs):
        if Path(path) == pointer or (Path(path).name == "current.json" and kwargs.get("dir_fd") is not None):
            raise PermissionError("fixture denied")
        return real_open(path, *args, **kwargs)
    monkeypatch.setattr(owner.os, "open", denied)
    with pytest.raises(owner.SelectedGenerationUnavailable) as error:
        owner.read_selected_generation(generations_root=root, domain="sector", members=(CENTRAL,))
    assert not isinstance(error.value, owner.SelectedGenerationAbsent)


def test_domain_disappearance_during_absence_capture_is_unavailable(tmp_path, monkeypatch):
    root = tmp_path / "generations"
    domain = root / "sector"
    domain.mkdir(parents=True)
    original = owner._read_json_state
    def disappear(path, **kwargs):
        state = original(path, **kwargs)
        domain.rmdir()
        return state
    monkeypatch.setattr(owner, "_read_json_state", disappear)
    with pytest.raises(owner.SelectedGenerationUnavailable) as error:
        owner.read_selected_generation(generations_root=root, domain="sector", members=(CENTRAL,))
    assert not isinstance(error.value, owner.SelectedGenerationAbsent)


def test_previous_capture_keeps_verified_bytes_clock_and_one_pointer_read(tmp_path, monkeypatch):
    _, published = publish(tmp_path)
    root = _gen_store_root(tmp_path)
    original = owner.read_selected_generation
    calls = []
    def observed(**kwargs):
        selected = original(**kwargs)
        calls.append(kwargs)
        return selected
    def clock():
        assert len(calls) == 1
        return NOW + timedelta(seconds=3)
    monkeypatch.setattr(owner, "read_selected_generation", observed)
    value = read(root, clock=clock)
    assert len(calls) == 1
    assert calls[0]["members"] == (CENTRAL,)
    assert value.expected_current_content_id == published.content_id
    assert value.input_lineage()["published_at"] == published.published_at
    assert value.captured_at == NOW + timedelta(seconds=3)
    assert value.input_lineage()["sha256"] == hashlib.sha256(value.central_bytes).hexdigest()
    assert value.input_lineage()["byte_length"] == len(value.central_bytes)
    document = value.central_document()
    document["sectors"][0]["score"] = -100
    assert value.central_document()["sectors"][0]["score"] == 70
    (root / "sector/g1" / CENTRAL).write_bytes(b"changed after capture")
    assert json.loads(value.prior_sector_text)["sectors"][0]["score"] == 70
    assert len(calls) == 1


def test_observed_absence_retains_none_fence_against_a_concurrent_publication(tmp_path):
    root = _gen_store_root(tmp_path)
    root.mkdir(parents=True)
    previous = read(root, bootstrap=True)
    orch, first = publish(tmp_path)
    rejected = orch.publish_generation(_gen_request(tmp_path, generation_id="g2", source_dir="g2"),
        expected_current_content_id=previous.expected_current_content_id)
    assert rejected.status == "rejected"
    assert "expected" in rejected.detail
    current = owner.read_selected_generation(generations_root=root, domain="sector", members=(CENTRAL,))
    assert current.content_id == first.content_id


def test_selected_capture_retains_original_fence_after_a_concurrent_publication(tmp_path):
    _, first = publish(tmp_path)
    previous = read(_gen_store_root(tmp_path))
    orch, second = publish(tmp_path, generation="g2", expected=first.content_id)
    rejected = orch.publish_generation(_gen_request(tmp_path, generation_id="g3", source_dir="g3"),
        expected_current_content_id=previous.expected_current_content_id)
    assert rejected.status == "rejected"
    assert "expected" in rejected.detail
    assert previous.expected_current_content_id == first.content_id
    assert second.content_id != previous.expected_current_content_id


def test_future_publication_cannot_be_relabelled_with_an_earlier_capture(tmp_path):
    publish(tmp_path)
    with pytest.raises(capture.SectorInputCaptureError, match="previous_publication_after_capture"):
        read(_gen_store_root(tmp_path), clock=lambda: NOW - timedelta(seconds=1))


def test_corrupt_selected_member_is_not_replaced_by_absent_bootstrap(tmp_path):
    publish(tmp_path)
    root = _gen_store_root(tmp_path)
    (root / "sector/g1" / CENTRAL).write_bytes(b"corrupt")
    with pytest.raises(capture.SectorInputCaptureError, match="previous_selection_unavailable"):
        read(root, bootstrap=True)


def test_selected_generation_read_refuses_an_ancestor_symlink(tmp_path):
    real = tmp_path / "real"
    (real / "generations").mkdir(parents=True)
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(owner.SelectedGenerationUnavailable) as error:
        owner.read_selected_generation(generations_root=alias / "generations",
            domain="sector", members=(CENTRAL,))
    assert not isinstance(error.value, owner.SelectedGenerationAbsent)


def test_selected_generation_read_pins_domain_across_path_aba(tmp_path, monkeypatch):
    _, published = publish(tmp_path)
    root = _gen_store_root(tmp_path)
    domain = root / "sector"
    aside = root / "sector-moved-for-fixture"
    original = owner._read_json_state
    reads = []
    def moved_domain(path, **kwargs):
        if Path(path).name != "current.json":
            return original(path, **kwargs)
        domain.rename(aside)
        try:
            reads.append((path, kwargs.get("dir_fd")))
            return original(path, **kwargs)
        finally:
            aside.rename(domain)
    monkeypatch.setattr(owner, "_read_json_state", moved_domain)
    selected = owner.read_selected_generation(generations_root=root,
        domain="sector", members=(CENTRAL,))
    assert selected.content_id == published.content_id
    assert len(reads) == 1
    assert reads[0][0] == Path("current.json")
    assert type(reads[0][1]) is int
