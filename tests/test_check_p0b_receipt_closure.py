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
