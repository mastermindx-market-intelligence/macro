"""Canada Stocks theme-action projection: reuse owners, never invent authority."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from scripts import canada_theme_action_map as theme_action_module
from scripts.canada_theme_action_map import _canada_theme_action_map


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


def _load_payload(site: Path) -> dict:
    return json.loads((site / "canadabasketdata" / "baskets.json").read_text())


def _store_payload(site: Path, payload: dict) -> None:
    (site / "canadabasketdata" / "baskets.json").write_text(json.dumps(payload))


def _oil_projection(result: dict | None) -> dict:
    assert result is not None
    return result["lanes"]["in_favour"][0]


@pytest.mark.parametrize(
    "leadership",
    ["not-a-mapping", {"top": {"ticker": "AAA.TO"}}],
    ids=["leadership-not-mapping", "top-not-list"],
)
def test_theme_action_map_ignores_truthy_malformed_leadership(
    tmp_path: Path, leadership: object,
) -> None:
    _write_payload(tmp_path)
    payload = _load_payload(tmp_path)
    payload["theme_intel"]["themes"][0]["leadership"] = leadership
    _store_payload(tmp_path, payload)

    oil = _oil_projection(
        _canada_theme_action_map({"buy": [{"ticker": "AAA.TO"}], "watch": []}, tmp_path)
    )

    assert oil["leaders"] == []
    assert oil["members"] == ["AAA.TO", "BBB.TO"]
    assert oil["prophet_count"] == 1


def test_theme_action_map_drops_malformed_optional_reason_without_aborting(
    tmp_path: Path,
) -> None:
    _write_payload(tmp_path)
    payload = _load_payload(tmp_path)
    payload["theme_intel"]["act_now"]["add_on_pullback"][0]["reasons"] = [
        "valid text",
        {"unexpected": "mapping"},
    ]
    _store_payload(tmp_path, payload)

    oil = _oil_projection(
        _canada_theme_action_map({"buy": [{"ticker": "AAA.TO"}], "watch": []}, tmp_path)
    )

    assert oil["reason_en"] is None
    assert oil["members"] == ["AAA.TO", "BBB.TO"]


def test_theme_action_projection_call_seam_fails_open_on_unexpected_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(_setups: dict | None, _site: Path) -> dict | None:
        raise RuntimeError("optional projection exploded")

    monkeypatch.setattr(theme_action_module, "_canada_theme_action_map", explode)

    assert theme_action_module._safe_canada_theme_action_map(
        {"buy": [], "watch": []}, tmp_path
    ) is None


@pytest.mark.parametrize(
    "members",
    [
        [None, {}, " "],
        [{"symbol": 123}],
    ],
    ids=["all-invalid", "numeric-symbol"],
)
def test_theme_action_map_marks_malformed_nonempty_membership_unknown(
    tmp_path: Path, members: list[object],
) -> None:
    _write_payload(tmp_path)
    payload = _load_payload(tmp_path)
    payload["baskets"][0]["members"] = members
    _store_payload(tmp_path, payload)

    oil = _oil_projection(
        _canada_theme_action_map({"buy": [{"ticker": "AAA.TO"}], "watch": []}, tmp_path)
    )

    assert oil["membership_known"] is False
    assert oil["members"] is None
    assert oil["n_members"] is None
    assert oil["prophet_count"] is None


def test_theme_action_map_preserves_legitimate_empty_membership_as_known_zero(
    tmp_path: Path,
) -> None:
    _write_payload(tmp_path)
    payload = _load_payload(tmp_path)
    payload["baskets"][0]["members"] = []
    _store_payload(tmp_path, payload)

    oil = _oil_projection(
        _canada_theme_action_map({"buy": [{"ticker": "AAA.TO"}], "watch": []}, tmp_path)
    )

    assert oil["membership_known"] is True
    assert oil["members"] == []
    assert oil["n_members"] == 0
    assert oil["prophet_count"] == 0


@pytest.mark.parametrize("duplicate_owner", ["baskets", "themes"])
def test_theme_action_map_disables_filter_for_duplicate_native_id(
    tmp_path: Path, duplicate_owner: str,
) -> None:
    _write_payload(tmp_path)
    payload = _load_payload(tmp_path)
    if duplicate_owner == "baskets":
        payload["baskets"].append(
            {"id": "oil", "members": [{"symbol": "ZZZ.TO"}]}
        )
    else:
        payload["theme_intel"]["themes"].append(
            {"id": "oil", "rank": 99, "leadership": {"top": [{"ticker": "ZZZ.TO"}]}}
        )
    _store_payload(tmp_path, payload)

    oil = _oil_projection(
        _canada_theme_action_map({"buy": [{"ticker": "AAA.TO"}], "watch": []}, tmp_path)
    )

    assert oil["membership_known"] is False
    assert oil["members"] is None
    assert oil["prophet_count"] is None


def test_theme_action_map_counts_full_valid_membership_universe(
    tmp_path: Path,
) -> None:
    _write_payload(tmp_path)
    payload = _load_payload(tmp_path)
    payload["theme_intel"]["themes"].append(
        {"id": "uranium", "rank": 8, "leadership": {"top": []}}
    )
    payload["baskets"].append(
        {
            "id": "uranium",
            "members": [{"symbol": "DML.TO"}, {"symbol": "NXE.TO"}],
        }
    )
    _store_payload(tmp_path, payload)

    result = _canada_theme_action_map({"buy": [], "watch": []}, tmp_path)

    assert result is not None
    assert result["n_themes"] == 3
    assert result["n_distinct_members"] == 5


def test_template_keeps_theme_and_sector_authority_visibly_separate() -> None:
    text = (Path(__file__).resolve().parents[1] / "templates/canada.html.j2").read_text()
    assert "Canadian themes" in text
    assert "descriptive rotation · does not originate Prophet picks" in text
    assert "Sector ETF pulse" in text
    assert "Canadian Opportunity Map" in text
    assert "Canadian themes below" in text
    assert "tracked proxies" in text
    assert "distinct constituents" in text
    assert "个不同主题成分" in text
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


def test_theme_action_attributes_escape_owner_strings_with_autoescape_disabled() -> None:
    from engine import i18n
    from jinja2 import Environment, FileSystemLoader
    from scripts import render_canada_opportunity_map_fixture as fixture_renderer

    root = Path(__file__).resolve().parents[1]
    setups, _ = fixture_renderer.load_owner_fixture("ca")
    actions, _ = fixture_renderer.load_action_fixture("ca")
    context = fixture_renderer.canada_context(setups, actions)
    row = context["theme_actions"]["lanes"]["in_favour"][0]
    hostile_text = {
        "rank": '<rank data-rank="yes">',
        "name": '<name data-name="yes">',
        "name_zh": '<name-zh data-name-zh="yes">',
        "category": '<category data-category="yes">',
        "category_zh": '<category-zh data-category-zh="yes">',
        "leaders": ['<leader data-leader="yes">'],
        "action_en": '<action data-action="yes">',
        "action_zh": '<action-zh data-action-zh="yes">',
    }
    row.update({
        "id": 'oil" data-injected="yes<',
        "members": ['AAA.TO" data-member="yes<'],
        "href": 'baskets_canada.html?x=" data-href="yes<',
        **hostile_text,
    })
    context["theme_actions"]["as_of"] = '<as-of data-as-of="yes">'

    env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    html = env.get_template("canada.html.j2").render(**context)

    assert 'data-ca-lead-id="oil" data-injected=' not in html
    assert 'data-ca-members="AAA.TO" data-member=' not in html
    assert 'href="baskets_canada.html?x=" data-href=' not in html
    assert 'aria-label="Oil" data-label=' not in html
    assert 'data-ca-lead-id="oil&#34; data-injected=&#34;yes&lt;"' in html
    assert 'data-ca-members="AAA.TO&#34; data-member=&#34;yes&lt;"' in html
    assert 'href="baskets_canada.html?x=&#34; data-href=&#34;yes&lt;"' in html
    assert 'aria-label="&lt;name data-name=&#34;yes&#34;&gt; theme research"' in html

    from markupsafe import escape

    for value in [
        hostile_text["rank"], hostile_text["name"], hostile_text["name_zh"],
        hostile_text["category"], hostile_text["category_zh"],
        hostile_text["leaders"][0], hostile_text["action_en"],
        hostile_text["action_zh"], context["theme_actions"]["as_of"],
    ]:
        assert value not in html
        assert str(escape(value)) in html


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
THEME_ACTION_OWNER = ROOT / "scripts/canada_theme_action_map.py"
P0B_EVIDENCE = ROOT / "mockups/evidence/prophet-p0b-zero-fouc"
CLIENT_CONTRACT_HARNESS = ROOT / "tests/canada_theme_client_contract_harness.cjs"
CLIENT_COMPOSER = ROOT / "site/canada-stock-v36.js"


def _client_theme_contract(scenario: str) -> dict:
    run = subprocess.run(
        ["node", str(CLIENT_CONTRACT_HARNESS), str(CLIENT_COMPOSER), scenario],
        cwd=ROOT, capture_output=True, text=True, timeout=10, check=False,
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_production_builder_uses_the_fail_open_projection_seam_in_pr_code_gate() -> None:
    result = _client_theme_contract("builder-seam")
    assert result["errors"] == []
    assert result["builder_safe_import"] is True
    assert result["builder_safe_call"] is True


@pytest.mark.parametrize(
    "scenario",
    [
        "duplicate-basket",
        "duplicate-theme",
        "numeric-symbol",
        "malformed-members",
        "numeric-id",
        "blank-id",
    ],
)
def test_client_theme_parser_never_makes_ambiguous_or_invalid_membership_actionable(
    scenario: str,
) -> None:
    result = _client_theme_contract(scenario)
    assert result["errors"] == []
    assert result["actionable"] is False


def test_client_theme_parser_degrades_malformed_leadership_only() -> None:
    result = _client_theme_contract("malformed-leadership")
    assert result["errors"] == []
    assert result["actionable"] is True
    assert result["leaders"] == "—"


def test_client_theme_parser_preserves_valid_empty_membership() -> None:
    result = _client_theme_contract("valid-empty")
    assert result["errors"] == []
    assert result["actionable"] is True
    assert result["count"] == "0"


def test_server_rendered_membership_remains_filter_authority_after_owner_fetch() -> None:
    result = _client_theme_contract("server-wins")
    assert result["errors"] == []
    assert result["visible"] == ["AAA.TO"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_successor_renderer_uses_the_production_theme_projection() -> None:
    from scripts import render_canada_opportunity_map_fixture as fixture_renderer

    setups, _ = fixture_renderer.load_owner_fixture("ca")
    owner_root = SUCCESSOR_EVIDENCE / "inputs/browser-data"
    expected = _canada_theme_action_map(setups, owner_root)

    assert expected is not None
    assert fixture_renderer.canada_theme_actions(setups) == expected
    assert expected["n_themes"] == 2
    assert expected["n_distinct_members"] == 3


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
    assert inputs["scripts/canada_theme_action_map.py"] == _sha256(THEME_ACTION_OWNER)
    theme_owner = (
        "mockups/evidence/canada-opportunity-map-20260909/inputs/"
        "browser-data/canadabasketdata/baskets.json"
    )
    assert inputs[theme_owner] == _sha256(ROOT / theme_owner)
    assert market["owner_population"] == {
        "board": 9, "watch": 8, "intersection": [], "unique_total": 17,
    }


def test_successor_verifier_fails_closed_when_theme_control_is_missing() -> None:
    text = SUCCESSOR_VERIFIER.read_text()
    assert 'if (await themeButton.count())' not in text
    assert 'if ((await themeButtons.count()) === 0)' in text
    assert 'Canada Opportunity Map theme control is missing' in text


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
    assert receipt["construction_inputs"][
        "scripts/canada_theme_action_map.py"
    ] == _sha256(THEME_ACTION_OWNER)
    theme_owner = (
        "mockups/evidence/canada-opportunity-map-20260909/inputs/"
        "browser-data/canadabasketdata/baskets.json"
    )
    assert receipt["construction_inputs"][theme_owner] == _sha256(ROOT / theme_owner)
    assert receipt["loaded_assets"]["site/canada-stock-v36.js"] == _sha256(ROOT / "site/canada-stock-v36.js")
    for relative, digest in receipt["loaded_assets"].items():
        assert _sha256(ROOT / relative) == digest
    owner_screenshots = [
        case["screenshot"]
        for case in receipt["owner_projection_matrix"]["cases"]
        if case.get("screenshot") is not None
    ]
    assert len(owner_screenshots) == 8
    assert {shot["filename"] for shot in owner_screenshots} == {
        f"owner-empty-ca-watch-only-{locale}-{theme}-{width}.png"
        for locale in ("en", "zh")
        for theme in ("dark", "light")
        for width in (390, 1440)
    }
    for shot in owner_screenshots:
        assert _sha256(ROOT / shot["path"]) == shot["sha256"]
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
    top_theme = next(row for row in receipt["desktop"]["sequence"] if row["label"] == "theme-top-group")
    assert top_theme["source"] == "top" and top_theme["source_unchanged"] is True
    assert top_theme["theme_filter"] == "ca_oil_gas"
    assert top_theme["expected"] == top_theme["visible"] == ["SU.TO"]
    shot = receipt["opportunity_map_screenshot"]
    assert shot and shot["path"] == "mockups/evidence/canada-opportunity-map-20260909/canada-opportunity-map-desktop.png"
    assert _sha256(ROOT / shot["path"]) == shot["sha256"]


def _historical_baseline_preflight(receipt: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir=SUCCESSOR_EVIDENCE, delete=False
    ) as handle:
        temp_receipt = Path(handle.name)
        receipt["historical_baseline"]["receipt"]["path"] = temp_receipt.relative_to(ROOT).as_posix()
        json.dump(receipt, handle)
    try:
        return subprocess.run(
            [
                "node", str(SUCCESSOR_VERIFIER),
                "--html", str(ROOT / "site/canada_stocks.html"),
                "--site-dir", str(ROOT / "site"),
                "--fixture-receipt", str(SUCCESSOR_EVIDENCE / "missing-fixture.json"),
                "--fixture-assets-dir", str(SUCCESSOR_EVIDENCE / "inputs/browser-data"),
                "--out", str(temp_receipt),
                "--historical-head", "5c9138b35221dc42d5d44a642f83043a505a9c90",
                "--historical-tree", "719f97810b8ea22282a77a72b3e8d4ec9a8bcbea",
            ],
            cwd=ROOT, capture_output=True, text=True, timeout=10, check=False,
        )
    finally:
        temp_receipt.unlink(missing_ok=True)


def test_historical_baseline_accepts_declared_zero_screenshots() -> None:
    receipt = json.loads((SUCCESSOR_EVIDENCE / "mobile-layout-canada.json").read_text())
    assert receipt["historical_baseline"]["screenshots"] == []
    assert receipt["historical_baseline"]["result"]["bound_screenshots"] == 0
    run = _historical_baseline_preflight(receipt)
    assert run.returncode == 2
    assert "--fixture-receipt is not a file" in run.stderr
    assert "conflicting historical baseline" not in run.stderr


@pytest.mark.parametrize("mutation", ["cardinality", "path", "sha"])
def test_historical_baseline_rejects_screenshot_binding_mismatch(mutation: str) -> None:
    receipt = json.loads((SUCCESSOR_EVIDENCE / "mobile-layout-canada.json").read_text())
    baseline = receipt["historical_baseline"]
    if mutation == "cardinality":
        baseline["result"]["bound_screenshots"] = 1
    else:
        baseline["result"]["bound_screenshots"] = 1
        baseline["screenshots"] = [{
            "state": "fixture",
            "path": "scripts/verify_canada_opportunity_map.cjs",
            "sha256": _sha256(SUCCESSOR_VERIFIER),
        }]
        if mutation == "path":
            baseline["screenshots"][0]["path"] = "mockups/evidence/does-not-exist.png"
        else:
            baseline["screenshots"][0]["sha256"] = "0" * 64
    run = _historical_baseline_preflight(receipt)
    assert run.returncode == 2
    expected = (
        "conflicting historical baseline"
        if mutation == "cardinality"
        else "historical screenshot binding is unavailable"
    )
    assert expected in run.stderr


def test_successor_preserves_frozen_zero_screenshot_historical_baseline() -> None:
    receipt = json.loads((SUCCESSOR_EVIDENCE / "mobile-layout-canada.json").read_text())
    historical = receipt["historical_baseline"]
    path = "mockups/evidence/canada-opportunity-map-20260909/mobile-layout-canada.json"
    assert historical["schema"] == "mastermind.stock_dashboard_browser_historical_baseline.v1"
    assert historical["candidate_head"] == "5c9138b35221dc42d5d44a642f83043a505a9c90"
    assert historical["candidate_tree"] == "719f97810b8ea22282a77a72b3e8d4ec9a8bcbea"
    assert historical["receipt"] == {
        "path": path,
        "sha256": "02976f4e68c55de8011c189ab70983cf6c12d2303321912b008bbb2eaf2d07fc",
        "recovery": f"git show 5c9138b35221dc42d5d44a642f83043a505a9c90:{path}",
    }
    assert historical["screenshots"] == []
    assert historical["result"]["bound_screenshots"] == 0
