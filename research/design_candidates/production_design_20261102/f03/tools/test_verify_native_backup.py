"""Adversarial, no-network F03 native clone readback tests."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from verify_native_backup import EvidenceInvalid, REQUIRED_NATIVE_PROPERTIES, evaluate_pair


SOURCE_ID = "01M2WGNCX9475G79JRKJTCM08P"
COPY_ID = "01M5HVW84WZFE62DREB6QB9ZDJ"
MISSING = ["p-27-0", "p-26-1", "p-25-0", "p-29-0", "p-28-0"]
WARNING = "Warning: Your file is too large. Further changes will result in data loss. Please start a new file."


def fixture():
    pages = [dict(type="page", id=f"p-BASE{i}-0", name=f"Page {i}", icon="blueprint")
             for i in range(57)]
    pages.extend(dict(type="page", id=p, name=p, icon="line-chart") for p in MISSING)
    source = dict(file_id=SOURCE_ID, file_name="MASTERMIND PAGES", page_count=62,
                  pages=pages, tokens_hash="cfd3d65c", warnings=[WARNING])
    candidate = dict(file_id=COPY_ID, file_name="MASTERMIND PAGES (copy)",
                     page_count=57, pages=copy.deepcopy(pages[:57]),
                     tokens_hash="cfd3d65c", warnings=[])
    return dict(kind="F03_native_file_pair_readback_v1", source=source, candidate=candidate)


class TestNativeBackupFailClosed(unittest.TestCase):
    def test_exact_historical_62_vs_57_is_not_backup(self):
        r = evaluate_pair(fixture())
        self.assertEqual(r["decision"], "HOLD_NOT_A_NATIVE_BACKUP")
        self.assertEqual(r["missing_source_page_ids"], MISSING)
        self.assertEqual((r["source_page_count"], r["candidate_page_count"]), (62, 57))
        self.assertTrue(r["token_hash_equal_not_sufficient"])
        self.assertTrue(r["original_oversize_warning"])
        self.assertFalse(r["restore_test_executed"])
        self.assertIn("MISSING_SOURCE_PAGES", r["blockers"])

    def test_equal_pages_and_tokens_still_not_a_native_restore(self):
        d = fixture()
        d["candidate"]["pages"] = copy.deepcopy(d["source"]["pages"])
        d["candidate"]["page_count"] = 62
        r = evaluate_pair(d)
        self.assertTrue(r["page_metadata_equal"])
        self.assertTrue(r["token_hash_equal_not_sufficient"])
        self.assertEqual(r["decision"], "HOLD_NOT_A_NATIVE_BACKUP")
        self.assertEqual(r["unverified_native_properties"], list(REQUIRED_NATIVE_PROPERTIES))
        self.assertIn("UNVERIFIED_REVISION_HISTORY", r["blockers"])

    def test_reorder_mismatch(self):
        d = fixture()
        d["candidate"]["pages"].reverse()
        self.assertIn("PAGE_IDS_OR_ORDER_DIFFER", evaluate_pair(d)["blockers"])

    def test_name_and_icon_mismatch(self):
        d = fixture()
        d["candidate"]["pages"][0]["name"] = "Renamed"
        self.assertIn("PAGE_NAMES_ICONS_OR_ORDER_DIFFER", evaluate_pair(d)["blockers"])

    def test_token_mismatch(self):
        d = fixture()
        d["candidate"]["tokens_hash"] = "deadbeef"
        self.assertFalse(evaluate_pair(d)["token_hash_equal_not_sufficient"])

    def test_page_count_mismatch_is_invalid(self):
        d = fixture()
        d["candidate"]["page_count"] = 62
        with self.assertRaises(EvidenceInvalid):
            evaluate_pair(d)

    def test_duplicate_ids_refused(self):
        d = fixture()
        d["candidate"]["pages"][1] = copy.deepcopy(d["candidate"]["pages"][0])
        with self.assertRaises(EvidenceInvalid):
            evaluate_pair(d)

    def test_source_as_clone_refused(self):
        d = fixture()
        d["candidate"]["file_id"] = SOURCE_ID
        with self.assertRaises(EvidenceInvalid):
            evaluate_pair(d)

    def test_unknown_candidate_page(self):
        d = fixture()
        d["candidate"]["pages"][0]["id"] = "p-NEW-0"
        self.assertEqual(evaluate_pair(d)["unexpected_candidate_page_ids"], ["p-NEW-0"])

    def test_invalid_divider_schema_refused(self):
        d = fixture()
        d["source"]["pages"][0]["type"] = "divider"
        with self.assertRaises(EvidenceInvalid):
            evaluate_pair(d)

    def test_fake_verified_receipt_does_not_grant_restoration(self):
        d = fixture()
        d["vendor_attested"] = True
        d["restore_passed"] = True
        self.assertEqual(evaluate_pair(d)["decision"], "HOLD_NOT_A_NATIVE_BACKUP")

    def test_cli_fails_closed_with_require_restored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "readback.json"
            path.write_text(json.dumps(fixture()))
            cmd = [sys.executable, str(Path(__file__).with_name("verify_native_backup.py")), str(path)]
            r = subprocess.run(cmd + ["--require-restored"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 3)
            self.assertIn("HOLD_NOT_A_NATIVE_BACKUP", r.stdout)
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
