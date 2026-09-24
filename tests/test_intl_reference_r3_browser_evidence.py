"""Verify the committed R3 browser-evidence receipt and screenshot matrix."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "mockups/refs/reference_integrity/intl-vnext-20260924"
PROOF = EVIDENCE / "proposal-r3-browser-proof.json"
ARTIFACT = ROOT / "mockups/refs/institutionalize/intl/reference-r3.html"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_r3_browser_receipt_binds_to_exact_artifact_and_has_no_console_errors():
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    assert proof["schema"] == "mastermind.intl_r3_browser_evidence.v1"
    assert proof["source_commit"] == "bdeb338372bf4ef29cb8d683e07ea840acdb4681"
    assert proof["artifact_sha256"] == _sha256(ARTIFACT)
    assert len(proof["captures"]) == 39
    assert all(not row.get("console_errors") for row in proof["captures"])
    for row in proof["captures"]:
        path = EVIDENCE / row["file"]
        assert path.is_file(), row["file"]
        assert row["sha256"] == _sha256(path)


def test_r3_browser_receipt_covers_required_default_and_discriminating_states():
    captures = json.loads(PROOF.read_text(encoding="utf-8"))["captures"]
    default = {(r["viewport"], r["theme"], r["locale"]) for r in captures if r["kind"] == "r3-default"}
    stocks = {(r["viewport"], r["theme"], r["locale"]) for r in captures if r["kind"] == "stocks-preservation"}
    expected = {(vp, theme, locale) for vp in ("desktop", "mobile") for theme in ("dark", "light") for locale in ("en", "zh")}
    assert default == expected
    assert stocks == expected
    country_rows = [r for r in captures if r["kind"] == "r3-country"]
    all_countries = {"JP", "KR", "TW", "IN", "AU", "GB", "EZ"}
    countries = {(r["country"], r["theme"], r["locale"]) for r in country_rows}
    assert {r["country"] for r in country_rows} == all_countries
    assert countries >= {(cc, theme, locale) for cc in ("JP", "GB") for theme in ("dark", "light") for locale in ("en", "zh")}
    assert countries >= {(cc, "dark", "en") for cc in all_countries}
    organ_states = {(r["state"], r["theme"]) for r in captures if r["kind"] == "r3-organ-state"}
    assert organ_states == {(state, theme) for state in ("loading", "empty", "stale", "error") for theme in ("dark", "light")}
    horizons = {(r["viewport"], r["theme"], r["locale"], r["horizon"]) for r in captures if r["kind"] == "r3-horizon"}
    assert horizons == {("desktop", "dark", "en", "12m"), ("mobile", "light", "zh", "1m")}


def test_r3_and_preserved_stocks_have_exact_viewport_widths():
    captures = json.loads(PROOF.read_text(encoding="utf-8"))["captures"]
    for row in captures:
        if row["kind"] not in {"r3-default", "r3-horizon", "stocks-preservation"}:
            continue
        expected = 1440 if row["viewport"] == "desktop" else 390
        dims = row["dimensions"]
        assert dims["scrollWidth"] == expected
        assert dims["clientWidth"] == expected
        if row["kind"] in {"r3-default", "r3-horizon"}:
            assert dims["actCount"] == 6
