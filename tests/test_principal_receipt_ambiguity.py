"""Principal source-contract counterexample; exact submitted candidate only."""
import json
from scripts.build_themes_heatmap import select_membership_receipt
from tests.test_themes_heatmap import _tree, _receipt


def test_conflicting_same_instant_membership_receipts_do_not_bind_by_filename(tmp_path):
    first = _receipt(_tree())
    second = dict(first, asof="2026-08-14")
    (tmp_path / "first.json").write_text(json.dumps(first))
    (tmp_path / "second.json").write_text(json.dumps(second))
    assert select_membership_receipt(tmp_path, _tree(), "2026-10-10 14:38") is None


def test_equivalent_duplicate_receipts_can_bind(tmp_path):
    receipt = _receipt(_tree())
    for name in ["first.json", "second.json"]:
        (tmp_path / name).write_text(json.dumps(receipt))
    assert select_membership_receipt(tmp_path, _tree(), "2026-10-10 14:38") == receipt


def test_conflicting_timezone_equivalent_receipts_do_not_fall_back_to_older(tmp_path):
    first = _receipt(_tree())
    second = dict(first, asof="2026-08-14", refreshed_at_utc="2026-08-15T03:01:34+01:00")
    older = dict(first, refreshed_at_utc="2026-08-15T01:00:00Z")
    for name, receipt in [("first.json", first), ("second.json", second), ("older.json", older)]:
        (tmp_path / name).write_text(json.dumps(receipt))
    assert select_membership_receipt(tmp_path, _tree(), "2026-10-10 14:38") is None
