"""Red-first tests for scripts/check_p0b_receipt_closure.py.

A synthetic diff touching templates/hk.html.j2 alone must fail; the same
diff also touching the receipts that pin it must pass. The pin set is
derived from the receipts at runtime — a receipt that pins a path the
checker never names still gates that path.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.check_p0b_receipt_closure as guard

EVIDENCE = guard.EVIDENCE_DIR_REL
HK_RECEIPT = f"{EVIDENCE}/mobile-layout.json"
CA_RECEIPT = f"{EVIDENCE}/mobile-layout-canada.json"
FIXTURE = f"{EVIDENCE}/{guard.FIXTURE_NAME}"
# ci-trigger-closure: data — fixture path names fed to a temp tree, never opened
# from this suite's checkout.
HK_TEMPLATE = "templates/hk.html.j2"
CA_TEMPLATE = "templates/canada.html.j2"
MADE_UP = "templates/zz-not-a-real-dashboard.html.j2"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _plant_receipts(
    root: Path,
    *,
    hk_pins: dict | None = None,
    ca_pins: dict | None = None,
    fixture_inputs: list[dict] | None = None,
) -> None:
    _write_json(
        root / FIXTURE,
        {
            "schema": guard.FIXTURE_SCHEMA,
            "proof_class": "rendered_fixture",
            "markets": {
                "hk": {
                    "inputs": fixture_inputs
                    or [
                        {"path": HK_TEMPLATE, "sha256": "a" * 64},
                        {
                            "path": "scripts/render_stock_dashboard_fixture.py",
                            "sha256": "b" * 64,
                        },
                    ]
                }
            },
        },
    )
    _write_json(
        root / HK_RECEIPT,
        {
            "schema": guard.RECEIPT_SCHEMA,
            "construction_inputs": hk_pins or {HK_TEMPLATE: "a" * 64},
            "loaded_assets": {"site/stock-dashboard.css": "c" * 64},
            "verifier": {
                "path": "scripts/verify_stock_dashboard_mobile_layout.cjs",
                "sha256": "d" * 64,
            },
            "fixture_receipt": {"path": FIXTURE, "sha256": "e" * 64},
        },
    )
    _write_json(
        root / CA_RECEIPT,
        {
            "schema": guard.RECEIPT_SCHEMA,
            "construction_inputs": ca_pins or {CA_TEMPLATE: "f" * 64},
            "loaded_assets": {"site/stock-dashboard.css": "c" * 64},
            "verifier": {
                "path": "scripts/verify_stock_dashboard_mobile_layout.cjs",
                "sha256": "d" * 64,
            },
            "fixture_receipt": {"path": FIXTURE, "sha256": "e" * 64},
        },
    )


def _eval(root: Path, changed: set[str]) -> list[str]:
    pin_sets, refuse = guard.derive_pin_sets(root)
    assert refuse is None, refuse
    return guard.evaluate(changed, pin_sets)


def test_hk_template_alone_fails(tmp_path: Path) -> None:
    """Red-first: a synthetic diff touching templates/hk.html.j2 alone must fail."""
    _plant_receipts(tmp_path)
    findings = _eval(tmp_path, {HK_TEMPLATE})
    assert findings, "hk.html.j2-only diff must fail"
    joined = "\n".join(findings)
    assert HK_TEMPLATE in joined
    assert HK_RECEIPT in joined


def test_hk_template_with_receipts_passes(tmp_path: Path) -> None:
    """The same diff also touching the receipts that pin the template must pass."""
    _plant_receipts(tmp_path)
    findings = _eval(tmp_path, {HK_TEMPLATE, HK_RECEIPT, CA_RECEIPT})
    assert findings == []


def test_hk_template_with_canada_receipt_only_still_fails(tmp_path: Path) -> None:
    """Touching only one market's receipt does not close a path both receipts pin."""
    _plant_receipts(tmp_path)
    findings = _eval(tmp_path, {HK_TEMPLATE, CA_RECEIPT})
    assert findings
    assert any(HK_RECEIPT in row for row in findings)


def test_pin_set_is_derived_from_receipts_not_hardcoded(tmp_path: Path) -> None:
    """A path the checker never names is still gated when a receipt pins it."""
    _plant_receipts(tmp_path, hk_pins={MADE_UP: "a" * 64})
    pin_sets, refuse = guard.derive_pin_sets(tmp_path)
    assert refuse is None
    assert MADE_UP in pin_sets[HK_RECEIPT]
    findings = guard.evaluate({MADE_UP}, pin_sets)
    assert findings
    assert any(MADE_UP in row for row in findings)
    closed = guard.evaluate({MADE_UP, HK_RECEIPT}, pin_sets)
    assert closed == []


def test_unrelated_path_passes(tmp_path: Path) -> None:
    _plant_receipts(tmp_path)
    assert _eval(tmp_path, {"engine/unrelated.py"}) == []


def test_parse_planner_changed_file_json_and_refuse_null() -> None:
    planner = json.dumps([HK_TEMPLATE, HK_RECEIPT, ""])
    assert guard.parse_changed_paths(planner) == {HK_TEMPLATE, HK_RECEIPT}
    with pytest.raises(ValueError, match="null / unavailable"):
        guard.parse_changed_paths("null\n")
    with pytest.raises(ValueError, match="array of strings"):
        guard.parse_changed_paths(json.dumps({"paths": [HK_TEMPLATE]}))


def test_parse_name_only_and_unified_diff() -> None:
    names = guard.parse_changed_paths(f"{HK_TEMPLATE}\n{HK_RECEIPT}\n")
    assert names == {HK_TEMPLATE, HK_RECEIPT}
    unified = (
        f"diff --git a/{HK_TEMPLATE} b/{HK_TEMPLATE}\n"
        f"--- a/{HK_TEMPLATE}\n"
        f"+++ b/{HK_TEMPLATE}\n"
        "@@ -1,0 +2,1 @@\n"
        "+x\n"
    )
    assert guard.parse_changed_paths(unified) == {HK_TEMPLATE}


def test_cli_refuses_null_planner_handle(tmp_path: Path) -> None:
    _plant_receipts(tmp_path)
    handle = tmp_path / "changed.json"
    handle.write_text("null\n", encoding="utf-8")
    assert guard.main(["--repo-root", str(tmp_path), "--diff-file", str(handle)]) == 2


def _null_handle(root: Path) -> Path:
    handle = root / "changed.json"
    handle.write_text("null\n", encoding="utf-8")
    return handle


@pytest.mark.parametrize("event", sorted(guard.NO_DIFF_SUBJECT_EVENTS))
def test_cli_accepts_null_handle_on_a_main_role_event(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], event: str
) -> None:
    # A main proof and the base replay publish `null` for a full-suite plan.
    # Refusing it redded every main ci.yml proof after #7237.
    _plant_receipts(tmp_path)
    argv = [
        "--repo-root", str(tmp_path),
        "--diff-file", str(_null_handle(tmp_path)),
        "--event", event,
    ]
    assert guard.main(argv) == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines() if "p0b-receipt-closure" in ln]
    assert lines and all(ln.startswith("::notice ") for ln in lines), lines


@pytest.mark.parametrize("event", ["pull_request", "", "push", "local"])
def test_cli_still_refuses_null_handle_off_the_main_role_events(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], event: str
) -> None:
    # A PR plan must carry an exact inventory; `null` there means the planner
    # failed, so the gate must not pass vacuously.
    _plant_receipts(tmp_path)
    argv = [
        "--repo-root", str(tmp_path),
        "--diff-file", str(_null_handle(tmp_path)),
        "--event", event,
    ]
    assert guard.main(argv) == 2
    out = capsys.readouterr().out
    assert any(
        ln.startswith("::error title=p0b-receipt-closure::REFUSED") for ln in out.splitlines()
    ), out


def test_cli_never_reads_the_event_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # This suite runs inside the main proof's own pack, where
    # GITHUB_EVENT_NAME=workflow_dispatch. An env default would let every
    # refusal test here pass the null handle on exactly that run.
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    _plant_receipts(tmp_path)
    argv = ["--repo-root", str(tmp_path), "--diff-file", str(_null_handle(tmp_path))]
    assert guard.main(argv) == 2


def test_a_main_role_event_relaxes_only_the_null_token(tmp_path: Path) -> None:
    # A real list on a main-role event still gates: a pinned path moving
    # without its receipts reds whatever the event.
    _plant_receipts(tmp_path)
    red_list = tmp_path / "red.json"
    red_list.write_text(json.dumps([HK_TEMPLATE]), encoding="utf-8")
    argv = [
        "--repo-root", str(tmp_path),
        "--diff-file", str(red_list),
        "--event", "workflow_dispatch",
    ]
    assert guard.main(argv) == 1
    assert guard.parse_changed_paths("null\n", null_is_no_diff=True) == set()
    with pytest.raises(ValueError, match="malformed"):
        guard.parse_changed_paths("[oops", null_is_no_diff=True)


FONT_MANIFEST = f"{EVIDENCE}/inputs/browser-data/p0b-font-pin/font-pin.json"


def _pin_fonts_and_browser(root: Path, version: str) -> None:
    for receipt in (HK_RECEIPT, CA_RECEIPT):
        path = root / receipt
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["browser"] = {"engine": "chromium", "version": version}
        payload["font_pin"] = {"manifest": {"path": FONT_MANIFEST, "sha256": "9" * 64}}
        _write_json(path, payload)


def test_font_pin_manifest_alone_fails(tmp_path: Path) -> None:
    """Changing the pinned fonts moves glyph metrics, so both receipts re-mint."""
    _plant_receipts(tmp_path)
    _pin_fonts_and_browser(tmp_path, "1.2.3.4")
    findings = _eval(tmp_path, {FONT_MANIFEST})
    assert findings
    assert any(HK_RECEIPT in row for row in findings)
    assert any(CA_RECEIPT in row for row in findings)
    assert _eval(tmp_path, {FONT_MANIFEST, HK_RECEIPT, CA_RECEIPT}) == []


def test_environment_hint_names_the_receipt_browser_pin_and_fonts(tmp_path: Path) -> None:
    _plant_receipts(tmp_path)
    _pin_fonts_and_browser(tmp_path, "1.2.3.4")
    verifier = tmp_path / guard.DEFAULT_VERIFIER
    verifier.parent.mkdir(parents=True, exist_ok=True)
    verifier.write_text('const CHROMIUM_PIN = "1.2.3.4";\n', encoding="utf-8")
    hint = guard.environment_hint(tmp_path)
    assert "measured on chromium 1.2.3.4" in hint
    assert "pins Chromium 1.2.3.4" in hint
    assert FONT_MANIFEST in hint


def test_environment_hint_survives_receipts_without_a_browser(tmp_path: Path) -> None:
    """Receipts minted before the pin carry no browser block; the hint still prints."""
    _plant_receipts(tmp_path)
    hint = guard.environment_hint(tmp_path)
    assert hint.startswith("re-mint environment:")


def test_cli_red_then_green(tmp_path: Path) -> None:
    _plant_receipts(tmp_path)
    red_list = tmp_path / "red.txt"
    red_list.write_text(HK_TEMPLATE + "\n", encoding="utf-8")
    red = guard.main(["--repo-root", str(tmp_path), "--diff-file", str(red_list)])
    assert red == 1
    green_list = tmp_path / "green.txt"
    green_list.write_text(f"{HK_TEMPLATE}\n{HK_RECEIPT}\n{CA_RECEIPT}\n", encoding="utf-8")
    green = guard.main(["--repo-root", str(tmp_path), "--diff-file", str(green_list)])
    assert green == 0


def test_checker_source_does_not_hardcode_template_pins() -> None:
    """Live pin set must come from receipts; template names are test/doc only."""
    source = Path(guard.__file__).read_text(encoding="utf-8")
    # Strip the module docstring and comments so a historical incident mention
    # is not mistaken for a live pin.
    live = []
    in_doc = False
    for i, line in enumerate(source.splitlines()):
        stripped = line.strip()
        if i == 0 and stripped.startswith('"""'):
            in_doc = True
            if stripped.endswith('"""') and len(stripped) > 3:
                in_doc = False
            continue
        if in_doc:
            if '"""' in stripped:
                in_doc = False
            continue
        if stripped.startswith("#"):
            continue
        live.append(line)
    body = "\n".join(live)
    assert "templates/hk.html.j2" not in body
    assert "templates/canada.html.j2" not in body


def test_selftest_passes() -> None:
    assert guard.run_selftest() == 0


# --- Digest-only tier -------------------------------------------------------
# A temp tree whose receipts carry REAL digests of the bytes beside them, so
# the tier logic (which hashes files) runs exactly as it does on the repo.

VERIFIER = "scripts/verify_stock_dashboard_mobile_layout.cjs"
RECIPE = "scripts/render_stock_dashboard_fixture.py"
# Layout tier: anything that can move the measured first frame. Stylesheets,
# fonts, chrome scripts and composers, every one of which a receipt loads.
LAYOUT_ASSETS = [
    "site/tablesort.js",
    "site/stock-dashboard.css",
    "site/fonts/Inter-400.woff2",
    "site/theme.js",
    "site/stocktable.js",
    "site/live.js",
    "site/dashboard-icons.js",
    "site/hk-stock-v36.js",
    "site/nav_market.js",
    "site/account.js",
    "site/stock-logos.js",
]
DIGEST_ASSETS = sorted(guard.REFRESHABLE_LOADED_ASSETS)
CHARTS = "site/charts.js"
MTF = "site/mtf.js"


def _digest(root: Path, rel: str) -> str:
    return guard.sha256_file(root / rel) or ""



@pytest.fixture(autouse=True)
def _isolate_synthetic_qualification(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guard, "QUALIFIED_DIGEST_SCENES", (), raising=False)


def _approve_synthetic(root: Path) -> None:
    """Declare one exact unit-fixture vector/scene, never browser evidence or auto-discovery."""
    row = {
        "basis": "synthetic_unit_fixture_not_browser_evidence",
        "receipts": {p: _digest(root, p) for p in (HK_RECEIPT, CA_RECEIPT)},
        "assets": {p: _digest(root, p) for p in guard.REFRESHABLE_LOADED_ASSETS},
    }
    if row not in guard.QUALIFIED_DIGEST_SCENES:
        guard.QUALIFIED_DIGEST_SCENES += (row,)


def _remint(root: Path) -> None:
    """Stand-in for a browser re-mint: the receipts measure the current bytes."""
    for rel in (HK_RECEIPT, CA_RECEIPT):
        payload = json.loads((root / rel).read_text(encoding="utf-8"))
        for block in ("construction_inputs", "loaded_assets"):
            payload[block] = {path: _digest(root, path) for path in payload[block]}
        for key in ("verifier", "fixture_receipt"):
            payload[key]["sha256"] = _digest(root, payload[key]["path"])
        (root / rel).write_text(json.dumps(payload) + "\n", encoding="utf-8")
    _approve_synthetic(root)


def _real_tree(root: Path) -> Path:
    for rel in [HK_TEMPLATE, CA_TEMPLATE, RECIPE, VERIFIER, *LAYOUT_ASSETS, *DIGEST_ASSETS]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(f"/* {rel} */\n", encoding="utf-8")
    _write_json(
        root / FIXTURE,
        {
            "schema": guard.FIXTURE_SCHEMA,
            "markets": {
                "hk": {"inputs": [{"path": HK_TEMPLATE, "sha256": _digest(root, HK_TEMPLATE)},
                                  {"path": RECIPE, "sha256": _digest(root, RECIPE)}]},
                "ca": {"inputs": [{"path": CA_TEMPLATE, "sha256": _digest(root, CA_TEMPLATE)},
                                  {"path": RECIPE, "sha256": _digest(root, RECIPE)}]},
            },
        },
    )
    for rel, template in ((HK_RECEIPT, HK_TEMPLATE), (CA_RECEIPT, CA_TEMPLATE)):
        _write_json(
            root / rel,
            {
                "schema": guard.RECEIPT_SCHEMA,
                "construction_inputs": {template: "", RECIPE: ""},
                "loaded_assets": {path: "" for path in [*LAYOUT_ASSETS, *DIGEST_ASSETS]},
                "verifier": {"path": VERIFIER, "sha256": ""},
                "fixture_receipt": {"path": FIXTURE, "sha256": ""},
            },
        )
    _remint(root)
    return root


def _rows(root: Path, changed: set[str]) -> list[tuple[str, str]]:
    pin_sets, refuse = guard.derive_pin_sets(root)
    assert refuse is None, refuse
    return guard.evaluate_rows(changed, pin_sets, root)


def _append(root: Path, rel: str, text: str = "/* moved */\n", *, qualify: bool = True) -> None:
    with (root / rel).open("a", encoding="utf-8") as handle:
        handle.write(text)
    if qualify and rel in guard.REFRESHABLE_LOADED_ASSETS:
        _approve_synthetic(root)


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _changed(before: dict[str, bytes], after: dict[str, bytes]) -> set[str]:
    return {rel for rel in before.keys() | after.keys() if before.get(rel) != after.get(rel)}


def _apply(root: Path, before: dict[str, bytes], after: dict[str, bytes]) -> None:
    """Replay one branch's diff onto another tree (a conflict-free merge)."""
    for rel in _changed(before, after):
        target = root / rel
        if rel in after:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(after[rel])
        else:
            target.unlink()


def test_real_tree_is_clean_and_refresh_writes_nothing(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    assert _rows(root, set()) == []
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 0
    assert _snapshot(root) == before
    assert set(guard.refreshable_measurements(root)) == set(DIGEST_ASSETS)


@pytest.mark.parametrize("path", [HK_TEMPLATE, CA_TEMPLATE, RECIPE, VERIFIER, *LAYOUT_ASSETS])
def test_layout_tier_change_is_red_and_refresh_refuses(tmp_path: Path, path: str) -> None:
    """Red-first, the #7603 class: a layout input moving alone still needs a browser."""
    root = _real_tree(tmp_path)
    _append(root, path)
    rows = _rows(root, {path})
    assert rows and {tier for tier, _ in rows} == {"layout"}, rows
    assert all("browser re-mint required" in finding for _, finding in rows)
    before = _snapshot(root)
    code, lines = guard.refresh_digests(root)
    assert code == 2
    assert any(path in line for line in lines), lines
    assert _snapshot(root) == before, "a refused refresh must write nothing"


def test_template_plus_a_forged_sidecar_is_still_red(tmp_path: Path) -> None:
    """A sidecar can never vouch for a layout input, even one shaped like a sidecar."""
    root = _real_tree(tmp_path)
    _append(root, "site/theme.js")
    forged = guard.sidecar_relpath("site/theme.js")
    (root / forged).parent.mkdir(parents=True, exist_ok=True)
    (root / forged).write_text(
        guard.render_sidecar(
            {"schema": guard.SIDECAR_SCHEMA, "path": "site/theme.js",
             "sha256": _digest(root, "site/theme.js")}
        ),
        encoding="utf-8",
    )
    rows = _rows(root, {"site/theme.js", forged})
    tiers = {tier for tier, _ in rows}
    assert "layout" in tiers and "sidecar" in tiers, rows
    assert any("UNQUALIFIED SIDECAR SCENE" in finding for _, finding in rows)


@pytest.mark.parametrize("asset", DIGEST_ASSETS)
def test_digest_only_change_closes_with_its_sidecar(tmp_path: Path, asset: str) -> None:
    root = _real_tree(tmp_path)
    receipts_before = {rel: (root / rel).read_bytes() for rel in (HK_RECEIPT, CA_RECEIPT)}
    _append(root, asset)
    rows = _rows(root, {asset})
    assert rows and {tier for tier, _ in rows} == {"digest"}, rows
    code, lines = guard.refresh_digests(root)
    assert code == 0, lines
    sidecar = guard.sidecar_relpath(asset)
    assert (root / sidecar).is_file()
    assert _rows(root, {asset, sidecar}) == []
    assert guard.sidecar_findings(root) == []
    for rel, payload in receipts_before.items():
        assert (root / rel).read_bytes() == payload, "refresh must never edit a receipt"
        effective = guard.effective_loaded_assets(root, rel, json.loads(payload))
        assert effective[asset] == _digest(root, asset)
    # A second refresh is a no-op: the sidecar already matches the bytes.
    code, lines = guard.refresh_digests(root)
    assert code == 0 and "0 wrote" in lines[-1], lines


def test_original_two_argument_contract_is_unchanged(tmp_path: Path) -> None:
    """Callers without a root still treat every pin as layout tier."""
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    assert guard.refresh_digests(root)[0] == 0
    pin_sets, _ = guard.derive_pin_sets(root)
    sidecar = guard.sidecar_relpath(CHARTS)
    assert guard.evaluate({CHARTS, sidecar}, pin_sets)
    assert guard.evaluate({CHARTS, sidecar}, pin_sets, root) == []


@pytest.mark.parametrize("order", [(CHARTS, MTF), (MTF, CHARTS)])
def test_sibling_digest_only_prs_merge_in_either_order_without_a_browser(
    tmp_path: Path, order: tuple[str, str]
) -> None:
    """Two PRs off one base, each moving a different digest-only asset."""
    base = _real_tree(tmp_path / "base")
    base_bytes = _snapshot(base)
    branches = {}
    for asset in order:
        branch = tmp_path / asset.replace("/", "_")
        branch.mkdir()
        _apply(branch, {}, base_bytes)
        _append(branch, asset, f"/* sibling edit to {asset} */\n")
        assert guard.refresh_digests(branch)[0] == 0
        assert _rows(branch, _changed(base_bytes, _snapshot(branch))) == []
        branches[asset] = _snapshot(branch)
    first, second = order
    main = tmp_path / "main"
    main.mkdir()
    _apply(main, {}, base_bytes)
    _apply(main, base_bytes, branches[first])
    main_after_first = _snapshot(main)
    # The second PR's merge ref: main (with the first) plus its own diff.
    _apply(main, base_bytes, branches[second])
    second_diff = _changed(main_after_first, _snapshot(main))
    before_qualification = _snapshot(main)
    assert guard.refresh_digests(main)[0] == 2
    assert _snapshot(main) == before_qualification
    _approve_synthetic(main)  # Explicitly qualify this union; no automatic vector mixing.
    assert guard.refresh_digests(main)[0] == 0
    assert _snapshot(main) == before_qualification, "A qualified sibling union must retain both exact sidecar bytes"
    assert guard.sidecar_relpath(second) in second_diff
    assert _rows(main, second_diff) == []
    assert guard.sidecar_findings(main) == []
    # The old all-layout contract would have demanded a browser re-mint here.
    pin_sets, _ = guard.derive_pin_sets(main)
    assert guard.evaluate(second_diff, pin_sets)
    # Nothing to re-mint after the merge either: a refresh is a no-op.
    merged = _snapshot(main)
    code, lines = guard.refresh_digests(main)
    assert code == 0 and "0 wrote" in lines[-1] and "0 pruned" in lines[-1], lines
    assert _snapshot(main) == merged


def test_layout_sibling_requires_scene_and_union_requalification(tmp_path: Path) -> None:
    """A layout sibling's new captured scene cannot inherit an old sidecar qualification."""
    base = _real_tree(tmp_path / "base")
    base_bytes = _snapshot(base)
    digest_branch = tmp_path / "digest"
    digest_branch.mkdir()
    _apply(digest_branch, {}, base_bytes)
    _append(digest_branch, CHARTS)
    assert guard.refresh_digests(digest_branch)[0] == 0
    layout_branch = tmp_path / "layout"
    layout_branch.mkdir()
    _apply(layout_branch, {}, base_bytes)
    _append(layout_branch, "site/theme.js")
    _remint(layout_branch)
    main = tmp_path / "main"
    main.mkdir()
    _apply(main, {}, base_bytes)
    _apply(main, base_bytes, _snapshot(digest_branch))
    after_digest = _snapshot(main)
    _apply(main, base_bytes, _snapshot(layout_branch))
    before = _snapshot(main)
    assert guard.refresh_digests(main)[0] == 2
    assert _snapshot(main) == before
    assert guard.sidecar_findings(main)
    _approve_synthetic(main)
    assert guard.refresh_digests(main)[0] == 0
    assert _rows(main, _changed(after_digest, _snapshot(main))) == []
    assert guard.sidecar_findings(main) == []


def test_remint_that_leaves_a_retired_sidecar_is_red_until_pruned(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    assert guard.refresh_digests(root)[0] == 0
    sidecar = guard.sidecar_relpath(CHARTS)
    _remint(root)
    rows = _rows(root, {HK_RECEIPT, CA_RECEIPT})
    assert any(tier == "sidecar" and "REDUNDANT SIDECAR" in f for tier, f in rows), rows
    code, lines = guard.refresh_digests(root)
    assert code == 0 and any(line == f"pruned {sidecar}" for line in lines), lines
    assert not (root / guard.DIGEST_REFRESH_DIR_REL).exists()
    assert _rows(root, {HK_RECEIPT, CA_RECEIPT, sidecar}) == []


def test_hand_edited_sidecar_is_red(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    assert guard.refresh_digests(root)[0] == 0
    sidecar = root / guard.sidecar_relpath(CHARTS)
    doc = json.loads(sidecar.read_text(encoding="utf-8"))
    doc["claim"] = "browser-measured"
    sidecar.write_text(guard.render_sidecar(doc), encoding="utf-8")
    rows = _rows(root, {guard.sidecar_relpath(CHARTS)})
    assert any("STALE OR HAND-EDITED" in f for _, f in rows), rows
    # A hand-edited sidecar vouches for nothing, so the asset reds too.
    assert any(tier == "digest" for tier, _ in _rows(root, {CHARTS}))


def test_stale_sidecar_is_red_after_the_asset_moves_again(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    assert guard.refresh_digests(root)[0] == 0
    _append(root, CHARTS, "/* again */\n")
    rows = _rows(root, {CHARTS})
    tiers = {tier for tier, _ in rows}
    assert tiers == {"digest", "sidecar"}, rows
    assert guard.refresh_digests(root)[0] == 0
    assert _rows(root, {CHARTS, guard.sidecar_relpath(CHARTS)}) == []


def test_unknown_file_in_the_sidecar_dir_is_red_and_refresh_refuses(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    stray = root / guard.DIGEST_REFRESH_DIR_REL / "notes.txt"
    stray.parent.mkdir(parents=True)
    stray.write_text("hand-written\n", encoding="utf-8")
    rel = f"{guard.DIGEST_REFRESH_DIR_REL}/notes.txt"
    assert any("UNKNOWN FILE" in f for _, f in _rows(root, {rel}))
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


def test_orphan_sidecar_is_red_and_refresh_prunes_it(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    orphan = root / guard.sidecar_relpath("site/retired.js")
    orphan.parent.mkdir(parents=True)
    orphan.write_text(
        guard.render_sidecar({"schema": guard.SIDECAR_SCHEMA, "path": "site/retired.js"}),
        encoding="utf-8",
    )
    rel = guard.sidecar_relpath("site/retired.js")
    assert any("ORPHAN SIDECAR" in f for _, f in _rows(root, {rel}))
    code, lines = guard.refresh_digests(root)
    assert code == 0 and any("(orphan)" in line for line in lines), lines
    assert not orphan.exists()


def test_digest_only_asset_also_pinned_as_construction_input_stays_layout_tier(
    tmp_path: Path,
) -> None:
    root = _real_tree(tmp_path)
    payload = json.loads((root / HK_RECEIPT).read_text(encoding="utf-8"))
    payload["construction_inputs"][CHARTS] = _digest(root, CHARTS)
    (root / HK_RECEIPT).write_text(json.dumps(payload) + "\n", encoding="utf-8")
    _append(root, CHARTS)
    rows = _rows(root, {CHARTS})
    assert ("layout" in {tier for tier, _ in rows}) and any(HK_RECEIPT in f for _, f in rows)
    assert guard.refresh_digests(root)[0] == 2


def test_cli_refresh_digests_exit_codes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _real_tree(tmp_path)
    _append(root, MTF)
    assert guard.main(["--repo-root", str(root), "--refresh-digests"]) == 0
    assert f"wrote {guard.sidecar_relpath(MTF)}" in capsys.readouterr().out
    green = tmp_path / "green.txt"
    green.write_text(f"{MTF}\n{guard.sidecar_relpath(MTF)}\n", encoding="utf-8")
    assert guard.main(["--repo-root", str(root), "--diff-file", str(green)]) == 0
    red = tmp_path / "red.txt"
    red.write_text(f"{HK_TEMPLATE}\n", encoding="utf-8")
    _append(root, HK_TEMPLATE)
    assert guard.main(["--repo-root", str(root), "--diff-file", str(red)]) == 1
    capsys.readouterr()
    assert guard.main(["--repo-root", str(root), "--refresh-digests"]) == 2
    out = capsys.readouterr().out
    assert any(
        ln.startswith("::error title=p0b-receipt-closure::REFUSED") for ln in out.splitlines()
    ), out


def _bind_synthetic_font_manifest(root: Path, path: str = FONT_MANIFEST) -> None:
    """A temporary guard fixture, never a browser or committed font receipt."""
    manifest = root / path
    if not manifest.exists():
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text('{"synthetic_font_control": true}\n', encoding="utf-8")
    for rel in (HK_RECEIPT, CA_RECEIPT):
        payload = json.loads((root / rel).read_text(encoding="utf-8"))
        payload["font_pin"] = {"manifest": {"path": path, "sha256": _digest(root, path)}}
        _write_json(root / rel, payload)


def test_font_manifest_drift_refuses_all_sidecar_writes(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    _bind_synthetic_font_manifest(root)
    _append(root, CHARTS)
    _append(root, FONT_MANIFEST)
    before = _snapshot(root)
    code, lines = guard.refresh_digests(root)
    assert code == 2, lines
    assert any(FONT_MANIFEST in line for line in lines)
    assert _snapshot(root) == before
    assert not (root / guard.DIGEST_REFRESH_DIR_REL).exists()


def test_font_manifest_path_is_never_refreshable(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    _bind_synthetic_font_manifest(root, CHARTS)
    assert CHARTS not in guard.refreshable_measurements(root)
    _append(root, CHARTS)
    before = _snapshot(root)
    rows = _rows(root, {CHARTS})
    assert rows and {tier for tier, _ in rows} == {"layout"}, rows
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


@pytest.mark.parametrize("digest", [None, "not-a-digest", "g" * 64])
def test_font_manifest_missing_or_invalid_digest_refuses_refresh(
    tmp_path: Path, digest: str | None
) -> None:
    root = _real_tree(tmp_path)
    _bind_synthetic_font_manifest(root)
    path = root / HK_RECEIPT
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["font_pin"]["manifest"]["sha256"] = digest
    _write_json(path, payload)
    _append(root, CHARTS)
    before = _snapshot(root)
    code, lines = guard.refresh_digests(root)
    assert code == 2, lines
    assert any("font_pin.manifest" in line for line in lines)
    assert _snapshot(root) == before


def test_tablesort_change_stays_layout_tier(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    asset = "site/tablesort.js"
    _append(root, asset)
    rows = _rows(root, {asset})
    assert rows and {tier for tier, _ in rows} == {"layout"}, rows
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before

# A future source edit never earns the exception by fooling the finite diagnostic.
@pytest.mark.parametrize("edit", [
    "/* even a harmless comment is a new source revision */\n",
    "if (window.innerWidth > 1000) document.body.remove();\n",
    "if (typeof unknownViewport !== 'undefined') document.body.remove();\n",
    "if ('unknownViewport' in window) document.body.remove();\n",
    "Object.getOwnPropertyDescriptor(window, 'unknownViewport');\n",
    "Reflect.ownKeys(window);\n",
    "if (matchMedia('(min-width: 1000px)').matches) document.body.remove();\n",
    "if (getComputedStyle(document.body).display) document.body.remove();\n",
    "Array.prototype.push = function () {};\n",
    "Object.defineProperty(Array.prototype, Symbol.iterator, {value: function () {}});\n",
    "Object.setPrototypeOf(Array.prototype, {});\n",
    "const old = Array.prototype.push; Array.prototype.push = function () {}; Array.prototype.push = old;\n",
    "setInterval(function () {}, 1);\n",
    "function again() { setTimeout(again, 1); } again();\n",
    "Promise.resolve().then(function () { document.body.remove(); });\n",
])
def test_unknown_helper_bytes_are_strict_before_any_refresh_effect(tmp_path: Path, edit: str) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS, edit, qualify=False)
    before = _snapshot(root)
    assert guard.refreshable_measurements(root) == {}
    assert {tier for tier, _ in _rows(root, {CHARTS})} == {"layout"}
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


def test_unknown_scene_refuses_even_orphan_pruning(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    orphan = root / guard.sidecar_relpath("site/retired.js")
    orphan.parent.mkdir(parents=True)
    orphan.write_text(guard.render_sidecar({"schema": guard.SIDECAR_SCHEMA, "path": "site/retired.js"}))
    payload = json.loads((root / HK_RECEIPT).read_text())
    payload["unqualified_annotation"] = "declared file hashes still match"
    _write_json(root / HK_RECEIPT, payload)
    before = _snapshot(root)
    assert guard.refreshable_measurements(root) == {}
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


def test_later_unknown_asset_does_not_partially_refresh_an_earlier_qualified_one(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    _append(root, MTF, "/* unqualified second helper */\n", qualify=False)
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before
    assert not (root / guard.DIGEST_REFRESH_DIR_REL).exists()


def test_missing_qualification_cannot_be_replaced_by_a_sidecar_claim(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    assert guard.refresh_digests(root)[0] == 0
    guard.QUALIFIED_DIGEST_SCENES = ()
    before = _snapshot(root)
    assert guard.refreshable_measurements(root) == {}
    assert guard.sidecar_findings(root)
    assert guard.effective_loaded_assets(root, HK_RECEIPT, json.loads((root / HK_RECEIPT).read_text()))[CHARTS] != _digest(root, CHARTS)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


def test_conflicting_qualification_refuses_without_changes(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    duplicate = dict(guard.QUALIFIED_DIGEST_SCENES[-1])
    duplicate["basis"] = "conflicting synthetic qualification"
    guard.QUALIFIED_DIGEST_SCENES += (duplicate,)
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


def test_invalid_extra_receipt_refuses_without_changes(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    (root / EVIDENCE / "mobile-layout-extra.json").write_text('{"schema":"wrong"}\n')
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


def test_strict_caller_change_invalidates_the_complete_qualification(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    _append(root, "site/theme.js", "document.body.innerHTML = '<div data-mtf></div>';\n")
    before = _snapshot(root)
    assert guard.refreshable_measurements(root) == {}
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before

def test_input_change_during_planning_refuses_before_any_effect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    original = guard.build_sidecar
    def drift_after_plan(*args, **kwargs):
        result = original(*args, **kwargs)
        _append(root, MTF, "/* concurrent unknown input */\n", qualify=False)
        return result
    monkeypatch.setattr(guard, "build_sidecar", drift_after_plan)
    code, lines = guard.refresh_digests(root)
    assert code == 2, lines
    assert not (root / guard.DIGEST_REFRESH_DIR_REL).exists()

def test_known_sidecar_directory_refuses_before_an_earlier_write(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    _append(root, MTF)
    occupied = root / guard.sidecar_relpath(MTF)
    occupied.mkdir(parents=True)
    before = _snapshot(root)
    code, lines = guard.refresh_digests(root)
    assert code == 2, lines
    assert _snapshot(root) == before
    assert occupied.is_dir()
    assert not (root / guard.sidecar_relpath(CHARTS)).exists()


def test_symlinked_sidecar_directory_cannot_write_outside_the_fixture(tmp_path: Path) -> None:
    root = _real_tree(tmp_path / "repo")
    _append(root, CHARTS)
    outside = tmp_path / "outside"
    outside.mkdir()
    canary = tmp_path / "external-canary"
    canary.write_text("unchanged")
    (root / guard.DIGEST_REFRESH_DIR_REL).symlink_to(outside, target_is_directory=True)
    before = _snapshot(root)
    code, lines = guard.refresh_digests(root)
    assert code == 2, lines
    assert _snapshot(root) == before
    assert list(outside.iterdir()) == []
    assert canary.read_text() == "unchanged"


def test_known_sidecar_symlink_refuses_before_an_earlier_write(tmp_path: Path) -> None:
    root = _real_tree(tmp_path / "repo")
    _append(root, CHARTS)
    _append(root, MTF)
    canary = tmp_path / "external-canary"
    canary.write_text("unchanged")
    target = root / guard.sidecar_relpath(MTF)
    target.parent.mkdir(parents=True)
    target.symlink_to(canary)
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before
    assert canary.read_text() == "unchanged"
    assert not (root / guard.sidecar_relpath(CHARTS)).exists()


def test_transient_asset_change_during_planning_cannot_leave_a_stale_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    before = _snapshot(root)
    original_status = guard.qualification_status
    original_digest = guard.sha256_file
    calls = 0
    changed = False
    restored = False
    original_bytes = (root / CHARTS).read_bytes()
    def move_after_preflight(*args, **kwargs):
        nonlocal calls, changed
        result = original_status(*args, **kwargs)
        calls += 1
        if calls == 2:
            (root / CHARTS).write_bytes(original_bytes + b"/* transient input */\n")
            changed = True
        return result
    def read_then_restore(path):
        nonlocal restored
        result = original_digest(path)
        if changed and not restored and path == root / CHARTS:
            (root / CHARTS).write_bytes(original_bytes)
            restored = True
        return result
    monkeypatch.setattr(guard, "qualification_status", move_after_preflight)
    monkeypatch.setattr(guard, "sha256_file", read_then_restore)
    assert guard.refresh_digests(root)[0] == 2
    assert changed and restored
    assert _snapshot(root) == before


def test_replaced_receipt_cannot_pair_new_raw_hash_with_old_measurements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    receipt = root / HK_RECEIPT
    original_bytes = receipt.read_bytes()
    replacement = json.loads(original_bytes)
    replacement["loaded_assets"][CHARTS] = "b" * 64
    _write_json(receipt, replacement)
    replacement_bytes = receipt.read_bytes()
    _approve_synthetic(root)
    receipt.write_bytes(original_bytes)
    original_load = guard.load_browser_receipts
    switched = False
    def old_payload_then_new_bytes(path):
        nonlocal switched
        result = original_load(path)
        if not switched:
            receipt.write_bytes(replacement_bytes)
            switched = True
        return result
    monkeypatch.setattr(guard, "load_browser_receipts", old_payload_then_new_bytes)
    code, lines = guard.refresh_digests(root)
    assert code == 2, lines
    assert switched and receipt.read_bytes() == replacement_bytes
    assert not (root / guard.DIGEST_REFRESH_DIR_REL).exists()
    assert any("receipt payload changed" in line for line in lines)


def test_sidecar_change_during_planning_is_preserved_without_earlier_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _real_tree(tmp_path)
    _append(root, CHARTS)
    _append(root, MTF)
    directory = root / guard.DIGEST_REFRESH_DIR_REL
    directory.mkdir(parents=True)
    canary = directory / Path(guard.sidecar_relpath(MTF)).name
    canary.write_text("original sidecar")
    original_build = guard.build_sidecar
    def concurrent_sidecar(*args, **kwargs):
        result = original_build(*args, **kwargs)
        canary.write_text("another writer")
        return result
    monkeypatch.setattr(guard, "build_sidecar", concurrent_sidecar)
    assert guard.refresh_digests(root)[0] == 2
    assert canary.read_text() == "another writer"
    assert not (root / guard.sidecar_relpath(CHARTS)).exists()


def _remint_without_qualifying(root: Path) -> None:
    previous = guard.QUALIFIED_DIGEST_SCENES
    _remint(root)
    guard.QUALIFIED_DIGEST_SCENES = previous


def _retirement_tree(root: Path) -> tuple[Path, Path]:
    root = _real_tree(root)
    asset = "site/charts.js"
    _append(root, asset)
    assert guard.refresh_digests(root)[0] == 0
    sidecar = root / guard.sidecar_relpath(asset)
    assert sidecar.is_file()
    _append(root, asset, "/* later captured revision */\n", qualify=False)
    _remint_without_qualifying(root)
    assert guard.refreshable_measurements(root) == {}
    return root, sidecar


def test_inactive_scene_without_sidecars_keeps_raw_bindings(tmp_path: Path) -> None:
    root = _real_tree(tmp_path)
    payload = json.loads((root / HK_RECEIPT).read_text())
    payload["new_capture_metadata"] = "strict current scene"
    _write_json(root / HK_RECEIPT, payload)
    assert guard.refreshable_measurements(root) == {}
    assert guard.sidecar_findings(root) == []
    for rel, receipt in guard.load_browser_receipts(root):
        assert guard.effective_loaded_assets(root, rel, receipt) == receipt["loaded_assets"]
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


def test_strict_retirement_removes_only_owned_redundant_overlays(tmp_path: Path) -> None:
    root, sidecar = _retirement_tree(tmp_path)
    assert guard.sidecar_findings(root), "inactive old sidecar is not a valid overlay"
    for rel, receipt in guard.load_browser_receipts(root):
        assert guard.effective_loaded_assets(root, rel, receipt) == receipt["loaded_assets"]
    before = _snapshot(root)
    code, lines = guard.refresh_digests(root)
    assert code == 0 and any("qualification remains inactive" in line for line in lines)
    assert _changed(before, _snapshot(root)) == {str(sidecar.relative_to(root))}
    assert not sidecar.exists()
    assert guard.refreshable_measurements(root) == {}
    assert guard.sidecar_findings(root) == []


@pytest.mark.parametrize("block", ["construction_inputs", "loaded_assets", "verifier", "fixture_receipt"])
def test_strict_retirement_refuses_missing_required_receipt_blocks(tmp_path: Path, block: str) -> None:
    root, _sidecar = _retirement_tree(tmp_path)
    payload = json.loads((root / HK_RECEIPT).read_text())
    del payload[block]
    _write_json(root / HK_RECEIPT, payload)
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


@pytest.mark.parametrize("damage", ["missing_market", "empty_inputs", "malformed_input"])
def test_strict_retirement_refuses_incomplete_recipe_inventory(tmp_path: Path, damage: str) -> None:
    root, _sidecar = _retirement_tree(tmp_path)
    fixture = json.loads((root / FIXTURE).read_text())
    if damage == "missing_market":
        fixture["markets"] = {}
    elif damage == "empty_inputs":
        fixture["markets"]["hk"]["inputs"] = []
    else:
        fixture["markets"]["hk"]["inputs"] = [{}]
    _write_json(root / FIXTURE, fixture)
    _remint_without_qualifying(root)
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


def test_strict_retirement_requires_a_current_loading_receipt(tmp_path: Path) -> None:
    root, _sidecar = _retirement_tree(tmp_path)
    for rel in (HK_RECEIPT, CA_RECEIPT):
        payload = json.loads((root / rel).read_text())
        del payload["loaded_assets"]["site/charts.js"]
        _write_json(root / rel, payload)
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


def test_strict_retirement_refuses_missing_historical_receipt(tmp_path: Path) -> None:
    root, _sidecar = _retirement_tree(tmp_path)
    (root / CA_RECEIPT).unlink()
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


@pytest.mark.parametrize("damage", ["foreign", "forged", "strict_drift", "uncovered_helper"])
def test_strict_retirement_validates_every_input_and_target_before_deleting(tmp_path: Path, damage: str) -> None:
    root, sidecar = _retirement_tree(tmp_path)
    if damage == "foreign":
        (sidecar.parent / "foreign.txt").write_text("preserve this file\n")
    elif damage == "forged":
        doc = json.loads(sidecar.read_text())
        doc["claim"] = "not the canonical tool-owned identity"
        sidecar.write_text(guard.render_sidecar(doc))
    elif damage == "strict_drift":
        _append(root, "site/theme.js", qualify=False)
    else:
        _append(root, "site/mtf.js", qualify=False)
    before = _snapshot(root)
    assert guard.refresh_digests(root)[0] == 2
    assert _snapshot(root) == before


def test_strict_retirement_rechecks_targets_before_deleting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, sidecar = _retirement_tree(tmp_path)
    original = guard._sidecar_inventory
    calls = 0
    def changed_inventory(where):
        nonlocal calls
        calls += 1
        if calls == 2:
            sidecar.write_text(sidecar.read_text() + " ")
        return original(where)
    monkeypatch.setattr(guard, "_sidecar_inventory", changed_inventory)
    code, _lines = guard.refresh_digests(root)
    assert code == 2
    assert sidecar.exists() and sidecar.read_text().endswith(" ")
    assert not (root / guard.sidecar_relpath("site/mtf.js")).exists()


def test_strict_retirement_rechecks_receipts_before_deleting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, sidecar = _retirement_tree(tmp_path)
    original = guard._receipt_inventory
    calls = 0
    def changed_inventory(where, expected=None):
        nonlocal calls
        calls += 1
        if calls == 3:
            payload = json.loads((root / HK_RECEIPT).read_text())
            payload["late_update"] = True
            _write_json(root / HK_RECEIPT, payload)
        return original(where, expected)
    monkeypatch.setattr(guard, "_receipt_inventory", changed_inventory)
    assert guard.refresh_digests(root)[0] == 2
    assert sidecar.exists()
