"""The public native archive feed describes the same articles as the editorial registry."""
import json
from pathlib import Path

from scripts import build_reports


def test_published_archive_matches_the_editorial_index(tmp_path):
    reports = sorted(build_reports.REPORTS, key=lambda report: report["date"], reverse=True)
    build_reports.write_archive_manifest(tmp_path, reports)
    path = Path("research/editorial-reports.json")
    actual = (tmp_path / path).read_bytes()
    site = Path(__file__).resolve().parents[1] / "site"
    assert actual == (site / path).read_bytes()
    manifest = json.loads(actual)
    assert manifest["version"] == 1
    assert len(manifest["reports"]) == len(reports)
    for article, source in zip(manifest["reports"], reports, strict=True):
        assert article == {key: source[key] for key in (
            "slug", "date", "read_min", "title_en", "title_zh", "dek_en", "dek_zh", "tags"
        )}
        assert (site / (article["slug"] + ".html")).is_file()


def test_archive_uses_the_existing_public_teaser_prefix():
    from tests.test_regwall_json_gate import (
        _extract_block, _path_tokens, _public_policy_tokens, _read_caddyfile,
    )

    path = "/research/editorial-reports.json"
    prefix = "/research/*"
    assert path.startswith(prefix[:-1])
    assert prefix in _public_policy_tokens()
    for matcher in ("@reg_asset", "@reg_asset_err"):
        assert prefix in _path_tokens(_extract_block(_read_caddyfile(), matcher))
