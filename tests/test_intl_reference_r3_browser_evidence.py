"""Verify the committed R3 browser-evidence receipt and screenshot matrix."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "mockups/refs/reference_integrity/intl-vnext-20260924"
PROOF = EVIDENCE / "proposal-r3-browser-proof.json"
ARTIFACT_REL = "mockups/refs/institutionalize/intl/reference-r3.html"
ARTIFACT = ROOT / ARTIFACT_REL
STOCKS = ROOT / "site/intl_stocks.html"
SOURCE_COMMIT = "007d88824cb6831eb534685371ffa5999d577d91"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _proof() -> dict:
    return json.loads(PROOF.read_text(encoding="utf-8"))


def _git_blob_sha256(commit: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def test_r3_browser_receipt_binds_to_exact_source_and_preserved_stocks():
    proof = _proof()
    assert proof["schema"] == "mastermind.intl_r3_browser_evidence.v2"
    assert proof["source_commit"] == SOURCE_COMMIT
    assert proof["artifact_sha256"] == _git_blob_sha256(SOURCE_COMMIT, ARTIFACT_REL)
    assert proof["stocks_artifact"] == "site/intl_stocks.html"
    assert proof["stocks_sha256"] == _sha256(STOCKS)
    assert len(proof["captures"]) == 41
    assert all(not row.get("console_errors") for row in proof["captures"])
    for row in proof["captures"]:
        path = EVIDENCE / row["file"]
        assert path.is_file(), row["file"]
        assert row["sha256"] == _sha256(path)


def test_r3_browser_receipt_covers_default_and_preserved_stocks_matrices():
    captures = _proof()["captures"]
    expected = {
        (vp, theme, locale)
        for vp in ("desktop", "mobile")
        for theme in ("dark", "light")
        for locale in ("en", "zh")
    }
    default = {
        (r["viewport"], r["theme"], r["locale"])
        for r in captures
        if r["kind"] == "r3-default"
    }
    stocks = {
        (r["viewport"], r["theme"], r["locale"])
        for r in captures
        if r["kind"] == "stocks-preservation"
    }
    assert default == expected
    assert stocks == expected
    for row in captures:
        if row["kind"] != "stocks-preservation":
            continue
        assert row["settled"] is True
        assert row["stable_samples"] >= 3
        assert row["busy_visible"] == 0
        assert row["loading_visible"] == 0
        assert row["stocks_sha256"] == _sha256(STOCKS)


def test_r3_browser_receipt_covers_every_inspector_and_keyboard_progression():
    rows = [r for r in _proof()["captures"] if r["kind"] == "r3-country"]
    all_countries = {"JP", "KR", "TW", "IN", "AU", "GB", "EZ"}
    countries = {(r["country"], r["theme"], r["locale"]) for r in rows}
    assert {r["country"] for r in rows} == all_countries
    assert countries >= {
        (cc, theme, locale)
        for cc in ("JP", "GB")
        for theme in ("dark", "light")
        for locale in ("en", "zh")
    }
    assert countries >= {(cc, "dark", "en") for cc in all_countries}
    expected_next = {"JP": "KR", "KR": "TW", "TW": "IN", "IN": "AU", "AU": "GB", "GB": "EZ", "EZ": "JP"}
    assert all(row["keyboard_next"] == expected_next[row["country"]] for row in rows)


def test_r3_browser_receipt_proves_horizons_fixed_charts_and_direct_initial_zh():
    captures = _proof()["captures"]
    horizons = {
        (r["viewport"], r["theme"], r["locale"], r["horizon"])
        for r in captures
        if r["kind"] == "r3-horizon"
    }
    assert horizons == {
        ("desktop", "dark", "en", "12m"),
        ("mobile", "light", "zh", "1m"),
    }
    fixed = [r for r in captures if r["kind"] == "r3-fixed-charts"]
    assert len(fixed) == 1
    assert fixed[0]["market_count"] == 7
    assert fixed[0]["horizons_verified"] == ["1m", "3m", "6m", "12m", "ytd"]
    assert fixed[0]["horizon_independent"] is True
    assert fixed[0]["neutral_link_ink"] is True
    initial_zh = [r for r in captures if r["kind"] == "r3-initial-locale"]
    assert len(initial_zh) == 1
    assert initial_zh[0]["viewport"] == "mobile"
    assert initial_zh[0]["locale"] == "zh"
    assert initial_zh[0]["selected_horizon_labels"] == ["3月"]
    assert initial_zh[0]["english_leaks"] == []
    assert initial_zh[0]["missing_chinese"] == []


def test_r3_browser_receipt_proves_full_page_organ_locality():
    rows = [r for r in _proof()["captures"] if r["kind"] == "r3-organ-state"]
    assert {(r["state"], r["theme"]) for r in rows} == {
        (state, theme)
        for state in ("loading", "empty", "stale", "error")
        for theme in ("dark", "light")
    }
    for row in rows:
        assert row["capture_scope"] == "full-page"
        assert row["act_count"] == 6
        assert row["all_acts_visible"] is True
        assert row["unrelated_rotation_visible"] is True
        assert row["unrelated_country_visible"] is True
        assert row["unrelated_deep_desks_visible"] is True
        assert row["image_dimensions"]["width"] == 1440
        assert row["image_dimensions"]["height"] == row["dimensions"]["scrollHeight"]


def test_r3_browser_receipt_records_semantic_style_and_route_checks():
    checks = _proof()["checks"]
    assert checks["zero_page_overflow"] is True
    assert checks["zero_console_errors"] is True
    assert checks["status_locale_invariant"] is True
    assert checks["direction_ink_locale_switches"] is True
    assert checks["fixed_chart_horizon_independent"] is True
    assert checks["direct_initial_zh_synchronized"] is True
    assert checks["all_links_resolved"] is True
    assert checks["resolved_link_count"] >= 30
    assert min(checks["light_theme_contrast_en"].values()) >= 4.5


def test_r3_and_preserved_stocks_have_exact_page_widths():
    captures = _proof()["captures"]
    width_kinds = {
        "r3-default",
        "r3-horizon",
        "r3-initial-locale",
        "r3-organ-state",
        "stocks-preservation",
    }
    for row in captures:
        if row["kind"] not in width_kinds:
            continue
        expected = 1440 if row["viewport"] == "desktop" else 390
        dims = row["dimensions"]
        assert dims["scrollWidth"] == expected
        assert dims["clientWidth"] == expected
        if row["kind"].startswith("r3-"):
            assert dims["actCount"] == 6
