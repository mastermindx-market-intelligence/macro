#!/usr/bin/env python3
"""Append a P0B browser-proof extension without rewriting historical evidence.

The canonical browser verifier owns the measurements and PNGs. This utility
only validates, binds, and records its newly generated HK/Canada receipts.
Refuses incomplete or stale source bindings, reused screenshots, and duplicate
history updates. It cannot turn a failing browser case into a passing claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "mockups/evidence/prophet-p0b-zero-fouc"
RECEIPTS = {"hk": "mobile-layout.json", "ca": "mobile-layout-canada.json"}
EXPECTED_BROWSER = {
    "playwright": "1.61.1", "platform": "darwin", "arch": "arm64",
    "version": "149.0.7827.55",
    "sha256": "11e393326c7d20a7c56641a7c65def33ea9c280da3b0b74cf8563b07989a0ee3",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bound_file(relative: str, expected: str) -> Path:
    assert isinstance(relative, str) and relative and not relative.startswith("/")
    target = (ROOT / relative).resolve()
    assert target.is_relative_to(ROOT) and target.is_file(), f"missing bound file: {relative}"
    assert re.fullmatch(r"[0-9a-f]{64}", expected or "")
    assert digest(target) == expected, f"source or image drift: {relative}"
    return target


def collect(market: str, fixture: dict, fixture_sha: str) -> tuple[dict, list[dict]]:
    relative = f"mockups/evidence/prophet-p0b-zero-fouc/{RECEIPTS[market]}"
    receipt_file = EVIDENCE / RECEIPTS[market]
    rec = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert rec["schema"] == "mastermind.stock_dashboard_mobile_layout.v1"
    assert rec["proof_class"] == "browser_fixture_proof_reproducible"
    assert rec["pass"] is True and rec["fixture_market"] == market
    assert rec["claims"] == {
        "source_contract": "browser_fixture", "browser_fixture": "reproducible",
        "canonical_build": "unavailable", "production": "none",
    }
    browser = rec["browser"]
    assert {key: browser[key] for key in ("playwright", "platform", "arch", "version")} == {
        key: EXPECTED_BROWSER[key] for key in ("playwright", "platform", "arch", "version")
    }
    assert browser["executable"]["sha256"] == EXPECTED_BROWSER["sha256"]
    assert browser["executable"]["name"] == "chrome-headless-shell"
    assert rec["fixture_receipt"] == {
        "path": "mockups/evidence/prophet-p0b-zero-fouc/rendered-fixture.json",
        "sha256": fixture_sha,
    }
    assert rec["input_html"]["sha256"] == fixture["markets"][market]["output_sha256"]
    assert rec["historical_baseline"]["candidate_head"] == "3fb76ea810a8e9ef6a05fe808bb6eaee87eb1f86"
    for relative_asset, sha in {**rec["construction_inputs"], **rec["loaded_assets"]}.items():
        bound_file(relative_asset, sha)
    projection = rec["owner_projection_matrix"]
    assert projection["pass"] is True and len(projection["cases"]) == 64
    assert projection["primary_passed"] == 48
    assert projection["degraded_controls_passed"] == 16
    images = []
    for case in projection["cases"]:
        shot = case.get("screenshot")
        if shot is None:
            continue
        assert case["owner_case"] == "watch-only" and case["mode"] == "loaded"
        assert shot["width"] == case["viewport"]["width"]
        assert shot["path"].startswith("mockups/evidence/prophet-p0b-zero-fouc/recapture-20261104-c2/")
        bound_file(shot["path"], shot["sha256"])
        images.append({"path": shot["path"], "sha256": shot["sha256"]})
    assert len(images) == 8 and projection["screenshot_count"] == 8
    assert len({row["path"] for row in images}) == 8
    return {
        "path": relative,
        "sha256": digest(receipt_file),
        "primary_cases": 48,
        "degraded_control_cases": 16,
        "screenshots": 8,
        "pass": True,
    }, images


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    assert re.fullmatch(r"[0-9a-f]{40}", args.source_head)
    actual_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert actual_head == args.source_head, (actual_head, args.source_head)
    fixture_file = EVIDENCE / "rendered-fixture.json"
    fixture_sha = digest(fixture_file)
    fixture = json.loads(fixture_file.read_text(encoding="utf-8"))
    assert fixture["schema"] == "mastermind.stock_dashboard_rendered_fixture.v1"
    assert set(fixture["markets"]) == {"hk", "ca"}
    manifest_file = EVIDENCE / "manifest.json"
    previous_bytes = manifest_file.read_bytes()
    manifest = json.loads(previous_bytes)
    previous = manifest["repair_extension"]
    assert previous["schema"] == "mastermind.prophet_p0b_owner_empty_repair_extension.v1"
    assert previous["pass"] is True and len(previous["screenshots"]) == 16
    # Historical screenshots stay at their original paths and bytes.
    for image in previous["screenshots"]:
        bound_file(image["path"], image["sha256"])
    bindings: dict[str, dict] = {}
    images: list[dict] = []
    for market in RECEIPTS:
        row, shots = collect(market, fixture, fixture_sha)
        bindings[market] = row
        images.extend(shots)
    images.sort(key=lambda row: row["path"])
    assert len({row["path"] for row in images}) == 16
    assert not {row["path"] for row in images} & {row["path"] for row in previous["screenshots"]}
    assert previous["fixture_receipt"]["sha256"] != fixture_sha or any(
        previous["browser_receipts"][market]["sha256"] != bindings[market]["sha256"]
        for market in RECEIPTS
    ), "already bound to these exact receipts; refusing duplicate history"
    history = manifest["repair_extension_history"]
    assert isinstance(history, list)
    new_extension = dict(previous)
    new_extension.update({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixture_receipt": {"path": previous["fixture_receipt"]["path"], "sha256": fixture_sha},
        "browser_receipts": bindings,
        "screenshots": images,
    })
    assert new_extension["totals"] == {
        "markets": 2, "owner_cases_per_market": 3, "primary_cases": 96,
        "degraded_control_cases": 32, "total_cases": 128, "screenshots": 16,
    }
    if args.check_only:
        print(json.dumps({"ready": True, "fixture_sha256": fixture_sha,
                          "receipts": bindings, "screenshots": len(images)}))
        return
    history.append({
        "source_head": actual_head,
        "prior_manifest_sha256": hashlib.sha256(previous_bytes).hexdigest(),
        "extension": previous,
    })
    manifest["repair_extension"] = new_extension
    encoded = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    temporary = manifest_file.with_name("manifest.json.p0b-recapture.tmp")
    assert not temporary.exists(), "a previous manifest write has not been reconciled"
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, manifest_file)
    print(json.dumps({"updated": str(manifest_file.relative_to(ROOT)),
                      "prior_manifest_sha256": hashlib.sha256(previous_bytes).hexdigest(),
                      "new_manifest_sha256": digest(manifest_file),
                      "history_count": len(history), "screenshots": len(images)}))


if __name__ == "__main__":
    main()
