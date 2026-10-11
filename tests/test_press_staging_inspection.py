"""A staging inspection must not generate, publish, or silently pass emptiness."""
import json

from engine.press import desk_planner, validators
from scripts import inspect_press_staging as I
from tests import press_fixtures as F


def _stage(root):
    slot = F.slot()
    draft = F.draft_from_slot(slot, extra_filler=-3)
    obj = {"id": slot["id"], "slot": slot, "draft": draft, "status": "passed"}
    path = root / "data/press/staging/candidate.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))
    return path, obj


def _snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_current_validation_is_read_only_and_not_approval(tmp_path):
    root = F.fixture_root(tmp_path)
    _stage(root)
    before = _snapshot(root)
    report = I.inspect_staging(root)
    assert report["validation_current"] == 1
    assert report["publication_approved"] is False
    assert len(report["items"][0]["sha256"]) == 64
    assert _snapshot(root) == before


def test_mutation_cannot_reuse_passed_status(tmp_path):
    root = F.fixture_root(tmp_path)
    path, obj = _stage(root)
    assert validators.validate(obj["draft"], obj["slot"], desk_planner.load_config(root), root)["ok"]
    obj["draft"]["body_html"] += "<p>The price increased by 987654321%.</p>"
    path.write_text(json.dumps(obj))
    report = I.inspect_staging(root)
    assert report["blocked"] == 1
    assert "current_validation_failed" in report["items"][0]["blockers"]


def test_empty_and_malformed_staging_are_not_green(tmp_path, capsys):
    root = F.fixture_root(tmp_path)
    assert I.main(["--root", str(root)]) == 1
    path = root / "data/press/staging/broken.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]")
    report = I.inspect_staging(root)
    assert report["items"][0]["blockers"] == ["malformed_stage"]


def test_canonical_earnings_remain_approval_required(tmp_path):
    root = F.fixture_root(tmp_path)
    path, obj = _stage(root)
    obj["id"] = "press-earnings-held"
    path.write_text(json.dumps(obj))
    report = I.inspect_staging(root)
    assert report["blocked"] == 1
    assert "immutable_earnings_approval_required" in report["items"][0]["blockers"]
