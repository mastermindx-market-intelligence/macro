"""ROR-1 banner mount guard characterization — synthetic HTML only."""
from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_banner_mount_census import audit_mounts, MountAuditError


def html(script=''):
    return f'<!doctype html><html><head></head><body><main>Market view</main>{script}</body></html>'


def mount(prefix='', extra=''):
    return f'<script defer data-whb data-root="{prefix}" src="{prefix}wh_banner.js?v=deadbeef"></script>' + extra


class BannerMountCensusTests(unittest.TestCase):
    def test_all_core_pages_with_sitewide_mount_means_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for page in ("index", "macro", "china", "hk", "markets", "status"):
                (root/f"{page}.html").write_text(html(mount()))
            report = audit_mounts(root, ("index.html","macro.html","china.html","hk.html"),
                                  ("markets.html","status.html"))
        self.assertTrue(report["core_all_mounted"])
        self.assertEqual(report["core_missing"], [])
        self.assertEqual(report["mounts_observed"], 6)
        self.assertFalse(report["installed_browser_proven"])

    def test_missing_four_core_but_two_controls_mounted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for page in ("index","macro","china","hk"):
                (root/f"{page}.html").write_text(html())
            for page in ("markets","status"):
                (root/f"{page}.html").write_text(html(mount()))
            report=audit_mounts(root,("index.html","macro.html","china.html","hk.html"),
                                ("markets.html","status.html"))
        self.assertFalse(report["core_all_mounted"])
        self.assertEqual(report["core_missing"], ["index.html","macro.html","china.html","hk.html"])
        self.assertEqual(report["mounts_observed"], 2)
        self.assertEqual(report["status"], "CORE_ALERT_CLIENT_UNMOUNTED_IN_SITE_SOURCE")

    def test_marker_without_real_script_does_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"index.html").write_text(html("<p>data-whb wh_banner.js</p>"))
            v=audit_mounts(root,("index.html",),())
        self.assertEqual(v["core_missing"], ["index.html"])

    def test_duplicate_mount_is_invalid_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"index.html").write_text(html(mount(extra=mount())))
            v=audit_mounts(root,("index.html",),())
        self.assertEqual(v["status"],"DUPLICATE_OR_INVALID_ALERT_MOUNT")
        self.assertFalse(v["core_all_mounted"])

    def test_missing_file_is_distinct_from_empty_healthy(self):
        with tempfile.TemporaryDirectory() as d:
            r=audit_mounts(Path(d),("index.html",),())
        self.assertEqual(r["core_missing"],["index.html"])
        self.assertEqual(r["pages"]["index.html"]["state"],"SOURCE_FILE_MISSING")

    def test_bad_source_path_is_not_mounted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"index.html").write_text(html('<script defer data-whb src="elsewhere.js"></script>'))
            v=audit_mounts(root,("index.html",),())
        self.assertFalse(v["core_all_mounted"])
        self.assertEqual(v["pages"]["index.html"]["state"],"INVALID_MOUNT")

    def test_relative_nested_prefix_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"stocks").mkdir()
            (root/"stocks"/"A.html").write_text(html(mount("../")))
            v=audit_mounts(root,("stocks/A.html",),())
        self.assertTrue(v["core_all_mounted"])

    def test_empty_unbounded_or_unsafe_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for paths in [(("../secrets.html",),()), ((),()), (("bad.txt",),()),(( "index.html",)*20,())]:
                with self.subTest(paths=paths), self.assertRaises(MountAuditError):
                    audit_mounts(root,*paths)


    def test_untrusted_string_and_comment_cannot_fake_script_mount(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"index.html"
            p.write_text(html('<!-- ' + mount() + ' --><p>wh_banner.js data-whb</p>'))
            result = audit_mounts(Path(d), ("index.html",), ())
        self.assertEqual(result["pages"]["index.html"]["state"], "UNMOUNTED")
        self.assertFalse(result["alert_payload_qualified"])
        self.assertFalse(result["authenticated_user_delivery_proven"])

    def test_real_script_without_data_marker_fails_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"index.html").write_text(html('<script defer src="wh_banner.js?v=deadbeef"></script>'))
            result = audit_mounts(root, ("index.html",), ())
        self.assertEqual(result["pages"]["index.html"]["state"], "INVALID_MOUNT")

    def test_nested_mismatched_data_root_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"deep").mkdir()
            (root/"deep"/"A.html").write_text(
                html('<script defer data-whb data-root="" src="../wh_banner.js?v=deadbeef"></script>'))
            result = audit_mounts(root, ("deep/A.html",), ())
        self.assertEqual(result["pages"]["deep/A.html"]["state"], "INVALID_MOUNT")

    def test_source_symlink_escape_does_not_count(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/"root"
            root.mkdir()
            outside = Path(d)/"secret.html"
            outside.write_text(html(mount()))
            (root/"index.html").symlink_to(outside)
            with self.assertRaises(MountAuditError):
                audit_mounts(root, ("index.html",), ())


if __name__ == "__main__":
    unittest.main()
