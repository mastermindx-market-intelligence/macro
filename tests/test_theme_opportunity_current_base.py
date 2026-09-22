from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Exact blocking shapes introduced by Macro #7571 at current main
# 2042b2f4ca5bcd84da47f0937f3b6a1e3d488b77.
FUNC_COLOR_RE = re.compile(
    r"\b(?:rgba?|hsla?)\s*\("
    r"|\b(?:color-mix|hwb|oklab|oklch|light-dark|device-cmyk)\("
    r"|\b(?:lab|lch)\(\s*(?:from\b|none\b|var\(|calc\(|[+-]?\.?\d)"
    r"|\bcolor\(\s*(?:from\b|srgb-linear\b|srgb\b|display-p3\b|a98-rgb\b"
    r"|prophoto-rgb\b|rec2020\b|xyz(?:-d50|-d65)?\b)"
)
FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;}\n]+)")


def test_lane_e_new_template_assets_pass_current_design_ratchet() -> None:
    findings: list[str] = []
    for rel in (
        "templates/theme_opportunity_card.css",
        "templates/theme_opportunity_card.js",
        "templates/_theme_opportunity_card.html.j2",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if FUNC_COLOR_RE.search(line):
                findings.append(f"{rel}:{line_no}:color-function")
            for match in FONT_FAMILY_RE.finditer(line):
                value = match.group(1).strip()
                if not value.startswith("var("):
                    findings.append(f"{rel}:{line_no}:font-family={value}")
    assert findings == []

import copy
import json
import subprocess

from lib.theme_opportunity_card import compose_from_owner_context, render_card

FIXTURE = ROOT / "tests" / "fixtures" / "theme_opportunity_owner_envelopes.json"
JS_PATH = ROOT / "templates" / "theme_opportunity_card.js"


def current_owner_envelope() -> dict:
    value = copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8"))[0])
    owner = value["theme_context"]
    owner["evidence_identity"] = {
        "available": False,
        "reason_code": "OWNER_IDENTITY_NOT_JOINED",
        "records": [],
    }
    owner["independent_evidence_families"] = []
    owner["correction_lineage"] = {
        "supersedes": None,
        "first_observed": None,
        "first_displayed": None,
    }
    owner["dimensions"]["entry"] = {
        "state": "QUALIFIED_PENDING_CONFIRMATION",
        "reason_code": "GROUP_ENTRY_QUALIFIED_PENDING_CONFIRMATION",
        "value": "T1",
        "band": "EXTENDED",
        "reason_codes": [
            "GROUP_CLASS_ENTRY_NOW",
            "ENTRY_TIER_T1",
            "CONFIRMATION_PENDING",
            "REGIME_EXTENDED",
        ],
        "source_records": [
            {"ref": "site/marketdata/subsector_confluence.json"}
        ],
        "clocks": {
            "observation": {"value": "2026-09-18", "reason": None},
            "availability": {
                "value": None,
                "reason": "owner_record_has_no_availability_clock",
            },
            "computation": {
                "value": None,
                "reason": "owner_record_has_no_computation_clock",
            },
            "publication": {
                "value": None,
                "reason": "owner_record_has_no_publication_clock",
            },
        },
    }
    return value


def run_js_current(method: str, value: dict) -> subprocess.CompletedProcess[str]:
    script = f"""
const fs = require('fs');
const vm = require('vm');
const sandbox = {{ window: {{}} }};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync({json.dumps(str(JS_PATH))}, 'utf8'), sandbox);
try {{
  const out = sandbox.window.ThemeOpportunityCard[{json.dumps(method)}]({json.dumps(value)});
  process.stdout.write(typeof out === 'string' ? out : JSON.stringify(out));
}} catch (error) {{
  process.stderr.write(String(error.message || error));
  process.exit(7);
}}
"""
    return subprocess.run(["node", "-e", script], capture_output=True, text=True)


def test_python_consumes_current_lane_a_flattened_lane_d_dimension() -> None:
    model = compose_from_owner_context(current_owner_envelope())
    entry = model["axes"]["entry"]
    assert entry["state"] == "QUALIFIED_PENDING_CONFIRMATION"
    assert entry["source_refs"] == ["site/marketdata/subsector_confluence.json"]
    assert entry["clock_reasons"]["availability"] == "owner_record_has_no_availability_clock"
    assert model["receipts"]["evidence_identity"] == {
        "available": False,
        "reason_code": "OWNER_IDENTITY_NOT_JOINED",
        "records": [],
    }
    html = render_card(model)
    assert "owner_record_has_no_availability_clock" in html
    assert "OWNER_IDENTITY_NOT_JOINED" in html


def test_javascript_consumes_current_lane_a_flattened_lane_d_dimension() -> None:
    result = run_js_current("fromOwnerContext", current_owner_envelope())
    assert result.returncode == 0, result.stderr
    model = json.loads(result.stdout)
    assert model["axes"]["entry"]["source_refs"] == [
        "site/marketdata/subsector_confluence.json"
    ]
    assert model["axes"]["entry"]["clock_reasons"]["availability"] == (
        "owner_record_has_no_availability_clock"
    )
    assert model["receipts"]["evidence_identity"]["reason_code"] == (
        "OWNER_IDENTITY_NOT_JOINED"
    )

import pytest

from lib.theme_opportunity_card import (
    COMPONENT_VERSION,
    CardPresentationError,
)


def test_current_base_repair_has_new_immutable_component_version() -> None:
    assert COMPONENT_VERSION == "theme-opportunity-card.presentation.v5"
    js = JS_PATH.read_text(encoding="utf-8")
    assert 'var COMPONENT_VERSION = "theme-opportunity-card.presentation.v5";' in js


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["theme_context"].update({
                "evidence_identity": {
                    "available": True,
                    "reason_code": None,
                    "records": [],
                }
            }),
            "available cannot be true without owner records",
        ),
        (
            lambda value: value["theme_context"]["dimensions"]["entry"][
                "source_records"
            ][0].update({"may_trade": "true"}),
            "unsupported provenance",
        ),
        (
            lambda value: value["theme_context"]["dimensions"]["entry"][
                "clocks"
            ]["availability"].update({"extra": "smuggled"}),
            "must contain value and reason",
        ),
        (
            lambda value: value["theme_context"]["dimensions"]["entry"][
                "clocks"
            ]["availability"].pop("reason"),
            "must contain value and reason",
        ),
    ],
)
def test_current_owner_receipts_fail_closed_in_python_and_javascript(
    mutate, message: str
) -> None:
    value = current_owner_envelope()
    mutate(value)
    with pytest.raises(CardPresentationError, match=message):
        compose_from_owner_context(value)
    result = run_js_current("fromOwnerContext", value)
    assert result.returncode == 7
    assert message in result.stderr


def test_available_evidence_identity_survives_as_one_owner_identity_not_a_score() -> None:
    value = current_owner_envelope()
    value["theme_context"]["evidence_identity"] = {
        "available": True,
        "reason_code": None,
        "records": [{
            "source_family": "subsector_confluence",
            "parent_identity": "semiconductors",
            "observation_session": "2026-09-18/EOD",
            "input_hash": "sha256:" + "a" * 64,
            "observation_id": "semiconductors/2026-09-18",
        }],
    }
    value["theme_context"]["independent_evidence_families"] = [
        "subsector_confluence"
    ]

    model = compose_from_owner_context(value)
    receipt = model["receipts"]["evidence_identity"]
    assert receipt["available"] is True
    assert len(receipt["records"]) == 1
    assert model["receipts"]["independent_evidence_families"] == [
        "subsector_confluence"
    ]
    assert "evidence_score" not in model["receipts"]
    assert "confidence" not in model["receipts"]

    result = run_js_current("fromOwnerContext", value)
    assert result.returncode == 0, result.stderr
    js_model = json.loads(result.stdout)
    assert js_model["receipts"]["evidence_identity"] == receipt
    assert "evidence_score" not in js_model["receipts"]
