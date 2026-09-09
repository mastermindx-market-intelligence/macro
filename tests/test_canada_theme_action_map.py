"""Canada Stocks theme-action projection: reuse owners, never invent authority."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts.build_canada import _canada_theme_action_map


def _write_payload(site: Path) -> None:
    out = site / "canadabasketdata"
    out.mkdir(parents=True)
    payload = {
        "as_of": "2026-09-04",
        "baskets": [
            {"id": "oil", "members": [{"symbol": "AAA.TO"}, {"symbol": "BBB.TO"}]},
            {"id": "banks", "members": [{"symbol": "CCC.TO"}]},
        ],
        "theme_intel": {
            "as_of": "2026-09-03",
            "themes": [
                {"id": "oil", "rank": 2, "leadership": {"top": [{"ticker": "AAA.TO"}]}},
                {"id": "banks", "rank": 7, "leadership": {"top": [{"ticker": "CCC.TO"}]}},
            ],
            "act_now": {
                "buy": [],
                "add_on_pullback": [{"id": "oil", "name": "Oil", "action": "accumulate", "score": 69}],
                "conflicted": [],
                "reduce": [{"id": "banks", "name": "Banks", "action": "avoid", "score": 40}],
            },
        },
    }
    (out / "baskets.json").write_text(json.dumps(payload))


def test_theme_action_map_preserves_owner_lanes_rank_and_clock(tmp_path: Path) -> None:
    _write_payload(tmp_path)
    result = _canada_theme_action_map({"buy": [{"ticker": "AAA.TO"}, {"ticker": "ZZZ.TO"}], "watch": [{"ticker": "CCC.TO"}]}, tmp_path)
    assert result is not None
    assert result["as_of"] == "2026-09-03"
    assert result["authority"] == "descriptive_rotation"
    assert list(result["lanes"]) == ["buy_now", "in_favour", "watch", "reduce"]
    oil = result["lanes"]["in_favour"][0]
    assert (oil["id"], oil["rank"], oil["score"], oil["action"]) == ("oil", 2, 69, "accumulate")
    assert oil["leaders"] == ["AAA.TO"]
    assert oil["members"] == ["AAA.TO", "BBB.TO"]
    assert oil["prophet_count"] == 1
    assert result["lanes"]["reduce"][0]["prophet_count"] == 1
    assert result["n_prophet_current"] == 3
    assert result["n_distinct_members"] == 3
    assert result["lanes"]["reduce"][0]["id"] == "banks"


def test_theme_action_map_fails_open_on_missing_or_malformed_owner(tmp_path: Path) -> None:
    assert _canada_theme_action_map({"buy": [], "watch": []}, tmp_path) is None
    out = tmp_path / "canadabasketdata"
    out.mkdir()
    (out / "baskets.json").write_text('{"theme_intel":{"act_now":{}}}')
    assert _canada_theme_action_map({"buy": [], "watch": []}, tmp_path) is None


def test_template_keeps_theme_and_sector_authority_visibly_separate() -> None:
    text = (Path(__file__).resolve().parents[1] / "templates/canada.html.j2").read_text()
    assert "Canadian themes" in text
    assert "descriptive rotation · does not originate Prophet picks" in text
    assert "Sector ETF pulse" in text
    assert "Canadian Opportunity Map" in text
    assert "Canadian themes below" in text
    assert "tracked proxies" in text
    assert "_ca_theme.get('as_of')" in text
    assert "{{ latest.date }}" in text


def test_theme_layer_does_not_reuse_sector_action_control_hooks() -> None:
    text = (Path(__file__).resolve().parents[1] / "templates/canada.html.j2").read_text()
    prophet = text.index('id="ca-v36-prophet"')
    start = text.index('id="ca-theme-action"')
    evidence = text.index('id="ca-v36-evidence"', start)
    assert prophet < start < evidence
    theme = text[start:evidence]
    assert "data-ca-an-lane" not in theme
    assert "data-action-lane-body" not in theme
    assert 'data-ca-lead-kind="theme"' in theme
    assert "data-ca-members" in theme
    assert "ca-theme-action-go" in theme


def test_composer_reconciles_theme_filter_after_optional_owner_load() -> None:
    text = (Path(__file__).resolve().parents[1] / "site/canada-stock-v36.js").read_text()
    needle = "state.themes = collectThemes(parts[0], parts[1]);"
    start = text.index(needle)
    block = text[start:start + 180]
    assert "renderLeadership();" in block
    assert "applyFilter();" in block
    assert "function staticThemeForFilter" in text
    assert "data-ca-members" in text


ROOT = Path(__file__).resolve().parents[1]
SUCCESSOR_EVIDENCE = ROOT / "mockups/evidence/canada-opportunity-map-20260909"
SUCCESSOR_RENDERER = ROOT / "scripts/render_canada_opportunity_map_fixture.py"
SUCCESSOR_VERIFIER = ROOT / "scripts/verify_canada_opportunity_map.cjs"
P0B_EVIDENCE = ROOT / "mockups/evidence/prophet-p0b-zero-fouc"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_successor_fixture_is_current_source_bound_and_reproducible(tmp_path: Path) -> None:
    committed = json.loads((SUCCESSOR_EVIDENCE / "rendered-fixture.json").read_text())
    receipts = []
    for name in ("a", "b"):
        out = tmp_path / name
        receipt = out / "receipt.json"
        run = subprocess.run(
            [sys.executable, str(SUCCESSOR_RENDERER), "--market", "ca",
             "--out-dir", str(out), "--receipt", str(receipt)],
            cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
        )
        assert run.returncode == 0, run.stderr
        receipts.append(json.loads(receipt.read_text()))
    assert receipts[0] == receipts[1] == committed
    market = committed["markets"]["ca"]
    inputs = {row["path"]: row["sha256"] for row in market["inputs"]}
    assert inputs["templates/canada.html.j2"] == _sha256(ROOT / "templates/canada.html.j2")
    assert inputs["scripts/render_canada_opportunity_map_fixture.py"] == _sha256(SUCCESSOR_RENDERER)
    assert market["owner_population"] == {
        "board": 9, "watch": 8, "intersection": [], "unique_total": 17,
    }


def test_successor_browser_receipt_proves_theme_to_prophet_journey() -> None:
    receipt = json.loads((SUCCESSOR_EVIDENCE / "mobile-layout-canada.json").read_text())
    fixture = json.loads((SUCCESSOR_EVIDENCE / "rendered-fixture.json").read_text())
    assert receipt["proof_class"] == "browser_fixture_proof_reproducible"
    assert receipt["claims"] == {
        "source_contract": "browser_fixture",
        "browser_fixture": "reproducible",
        "canonical_build": "unavailable",
        "production": "none",
    }
    assert receipt["verifier"] == {
        "path": "scripts/verify_canada_opportunity_map.cjs",
        "sha256": _sha256(SUCCESSOR_VERIFIER),
    }
    assert receipt["fixture_receipt"] == {
        "path": "mockups/evidence/canada-opportunity-map-20260909/rendered-fixture.json",
        "sha256": _sha256(SUCCESSOR_EVIDENCE / "rendered-fixture.json"),
    }
    assert receipt["input_html"]["sha256"] == fixture["markets"]["ca"]["output_sha256"]
    assert receipt["construction_inputs"]["templates/canada.html.j2"] == _sha256(ROOT / "templates/canada.html.j2")
    assert receipt["loaded_assets"]["site/canada-stock-v36.js"] == _sha256(ROOT / "site/canada-stock-v36.js")
    assert receipt["pass"] is True
    assert receipt["desktop"]["pass"] is True
    assert receipt["owner_projection_matrix"]["pass"] is True
    assert all(row["pass"] for row in receipt["states"])
    theme = next(row for row in receipt["desktop"]["sequence"] if row["label"] == "theme-group")
    assert theme["source"] == "all" and theme["source_unchanged"] is True
    assert theme["theme_filter"] == "ca_oil_gas"
    assert theme["expected"] == theme["visible"] == ["SU.TO", "TOU.TO"]
    cleared = next(row for row in receipt["desktop"]["sequence"] if row["label"] == "theme-clear")
    assert cleared["filter"] is False and cleared["theme_filter"] is None
    shot = receipt["opportunity_map_screenshot"]
    assert shot and shot["path"] == "mockups/evidence/canada-opportunity-map-20260909/canada-opportunity-map-desktop.png"
    assert _sha256(ROOT / shot["path"]) == shot["sha256"]


def test_p0b_canada_evidence_remains_immutable_predecessor() -> None:
    # The successor must not rewrite the accepted P0B evidence carrier.
    assert _sha256(P0B_EVIDENCE / "mobile-layout-canada.json") == (
        "8c29c4858c7841035bafb2bcd6ff047c263832bc2ea506091733d4b3d9c3fa94"
    )
