"""Verify the successor R3 browser matrix without mutating historical receipts."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "mockups/refs/reference_integrity/intl-vnext-20260924"
PROOF = EVIDENCE / "proposal-r3-successor-browser-proof.json"
ARTIFACT_REL = "mockups/refs/institutionalize/intl/reference-r3.html"
ARTIFACT = ROOT / ARTIFACT_REL
STOCKS_REL = "site/intl_stocks.html"
STOCKS = ROOT / STOCKS_REL


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_sha256(commit: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def _proof() -> dict:
    return json.loads(PROOF.read_text(encoding="utf-8"))


def test_r3_repair_receipt_binds_exact_immutable_source_and_stocks() -> None:
    proof = _proof()
    source_commit = proof["source_commit"]
    assert proof["schema"] == "mastermind.intl_r3_browser_evidence.v4"
    assert source_commit == "UNFROZEN_WORKTREE" or re.fullmatch(r"[0-9a-f]{40}", source_commit)
    assert proof["artifact"] == ARTIFACT_REL
    if source_commit == "UNFROZEN_WORKTREE":
        assert proof["artifact_sha256"] == _sha256(ARTIFACT)
    else:
        subprocess.run(
            ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
            cwd=ROOT,
            check=True,
        )
        assert proof["artifact_sha256"] == _git_blob_sha256(source_commit, ARTIFACT_REL)
        assert proof["artifact_sha256"] == _sha256(ARTIFACT)
    assert proof["stocks_artifact"] == STOCKS_REL
    assert proof["stocks_sha256"] == _sha256(STOCKS)
    assert len(proof["captures"]) == 41
    for row in proof["captures"]:
        path = EVIDENCE / row["file"]
        assert path.is_file(), row["file"]
        assert row["sha256"] == _sha256(path)
        assert not row.get("console_errors"), row["file"]
        assert not row.get("request_failures"), row["file"]


def test_r3_repair_default_and_stocks_matrices_are_complete() -> None:
    captures = _proof()["captures"]
    expected = {
        (viewport, theme, locale)
        for viewport in ("desktop", "mobile")
        for theme in ("dark", "light")
        for locale in ("en", "zh")
    }
    for kind in ("r3-successor-default", "stocks-successor-preservation"):
        actual = {
            (row["viewport"], row["theme"], row["locale"])
            for row in captures
            if row["kind"] == kind
        }
        assert actual == expected
    for row in captures:
        if row["kind"] != "stocks-successor-preservation":
            continue
        assert row["settled"] is True
        assert row["stable_samples"] >= 3
        assert row["busy_visible"] == 0
        assert row["loading_visible"] == 0
        assert row["stocks_sha256"] == _sha256(STOCKS)


def test_r3_repair_captures_every_country_and_keyboard_progression() -> None:
    rows = [row for row in _proof()["captures"] if row["kind"] == "r3-successor-country"]
    all_countries = {"JP", "KR", "TW", "IN", "AU", "GB", "EZ"}
    combinations = {(row["country"], row["theme"], row["locale"]) for row in rows}
    assert {row["country"] for row in rows} == all_countries
    assert combinations >= {(code, "dark", "en") for code in all_countries}
    assert combinations >= {
        (code, theme, locale)
        for code in ("JP", "GB")
        for theme in ("dark", "light")
        for locale in ("en", "zh")
    }
    expected_next = {
        "JP": "KR",
        "KR": "TW",
        "TW": "IN",
        "IN": "AU",
        "AU": "GB",
        "GB": "EZ",
        "EZ": "JP",
    }
    assert all(row["keyboard_next"] == expected_next[row["country"]] for row in rows)
    assert all(row["selected_panel_visible"] is True for row in rows)


def test_r3_repair_horizons_fixed_paths_and_direct_initial_zh() -> None:
    captures = _proof()["captures"]
    horizons = {
        (row["viewport"], row["theme"], row["locale"], row["horizon"])
        for row in captures
        if row["kind"] == "r3-successor-horizon"
    }
    assert horizons == {
        ("desktop", "dark", "en", "12m"),
        ("mobile", "light", "zh", "1m"),
    }
    fixed = [row for row in captures if row["kind"] == "r3-successor-fixed-paths"]
    assert len(fixed) == 1
    assert fixed[0]["market_count"] == 7
    assert fixed[0]["horizons_verified"] == ["1m", "3m", "6m", "12m", "ytd"]
    assert fixed[0]["horizon_independent"] is True
    assert fixed[0]["semantic_direction_ink"] is True
    direct_zh = [row for row in captures if row["kind"] == "r3-successor-initial-locale"]
    assert len(direct_zh) == 1
    assert direct_zh[0]["viewport"] == "mobile"
    assert direct_zh[0]["locale"] == "zh"
    assert direct_zh[0]["selected_horizon_labels"] == ["3月"]
    assert direct_zh[0]["english_leaks"] == []
    assert direct_zh[0]["missing_chinese"] == []


def test_r3_repair_organ_states_are_local_and_full_page() -> None:
    rows = [row for row in _proof()["captures"] if row["kind"] == "r3-successor-organ-state"]
    assert {(row["state"], row["theme"]) for row in rows} == {
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
        assert row["active_state_visible"] is True
        assert row["image_dimensions"]["width"] == 1440
        assert row["image_dimensions"]["height"] == row["dimensions"]["scrollHeight"]


def test_r3_repair_semantic_route_contrast_and_integrity_checks() -> None:
    checks = _proof()["checks"]
    for key in (
        "zero_page_overflow",
        "zero_console_errors",
        "zero_request_failures",
        "zero_external_dependencies",
        "all_links_resolved",
        "status_locale_invariant",
        "direction_ink_locale_switches",
        "fixed_chart_horizon_independent",
        "direct_initial_zh_synchronized",
        "canonical_light_ink_tokens",
        "no_invented_quantitative_displays",
        "organ_state_locality",
        "stocks_mode_non_regression",
    ):
        assert checks[key] is True, key
    assert checks["resolved_link_count"] >= 30
    assert checks["unresolved_links"] == []
    assert min(checks["light_theme_contrast_en"].values()) >= 4.5


def test_r3_repair_and_stocks_have_exact_page_widths() -> None:
    width_kinds = {
        "r3-successor-default",
        "r3-successor-horizon",
        "r3-successor-initial-locale",
        "r3-successor-organ-state",
        "stocks-successor-preservation",
    }
    for row in _proof()["captures"]:
        if row["kind"] not in width_kinds:
            continue
        expected = 1440 if row["viewport"] == "desktop" else 390
        dimensions = row["dimensions"]
        assert dimensions["scrollWidth"] == expected
        assert dimensions["clientWidth"] == expected
        if row["kind"].startswith("r3-repair"):
            assert dimensions["actCount"] == 6


def test_r3_successor_critic_driven_browser_checks_are_green() -> None:
    proof = _proof()
    checks = proof["checks"]
    for key in (
        "heatmap_high_contrast",
        "search_focus_visible",
        "shell_locale_accessibility_sync",
        "mobile_act_navigation",
        "no_regional_indicator_emoji",
        "fixed_path_grid_aligned",
        "direct_initial_pixel_distinct",
        "country_inspector_unobscured",
    ):
        assert checks[key] is True, key
    assert checks["heatmap_high_contrast_light"] >= 4.5
    assert checks["heatmap_high_contrast_dark"] >= 4.5


def test_r3_successor_direct_zh_and_organ_locality_cover_critic_failures() -> None:
    proof = _proof()
    direct = next(row for row in proof["captures"] if row["kind"] == "r3-successor-initial-locale")
    assert direct["search_placeholder"] == "搜索任意股票"
    assert direct["search_aria"] == "搜索股票"
    assert direct["settings_aria"] == "设置"
    assert direct["locale_focus_style"]["outlineStyle"] != "none"
    for row in proof["captures"]:
        if row["kind"] == "r3-successor-organ-state":
            assert row["independent_turn_board_visible"] is True
        if row["kind"] == "r3-successor-country":
            assert row["inspector_top"] >= row["sticky_bottom"] + 4


def test_r3_successor_fixed_path_capture_is_shape_only_and_aligned() -> None:
    row = next(
        row for row in _proof()["captures"] if row["kind"] == "r3-successor-fixed-paths"
    )
    assert row["scale_mode"] == "per-market-normalized-shape-only"
    assert row["sparkline_top_spread"] <= 2
