"""Static contract pins for the Sector Central shell (SIC-I01).

Pure-python text checks against research/sector_completion_20261021/INTEGRATION_CONTRACT.md:
no browser, no network, no site/ or data/ fixtures, no engine imports (keeps the suite on
the tier-gate job's minimal venv line — see the comment above
.github/ci/legacy-jobs.yml:6284). If one of these fails, the CONTRACT changed or the
observed shell drifted from it; update both together.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = ROOT / "templates" / "sector_central.html.j2"
ROUTER = ROOT / "templates" / "si_workspace.js"
BUILDER = ROOT / "scripts" / "build_sector_central.py"
CONTRACT = ROOT / "research" / "sector_completion_20261021" / "INTEGRATION_CONTRACT.md"
LEGACY_JOBS = ROOT / ".github" / "ci" / "legacy-jobs.yml"

#: route ids the contract's Routes table records (observed set == expected set).
ROUTES = ["overview", "map", "moving", "money", "explore", "confluence"]

#: fixed mount points the contract records.
MOUNT_IDS = ["tm-mount", "accumulation-section", "si-measured"]

#: every builder input/output path string the contract lists (inputs and outputs
#: of scripts/build_sector_central.py::main, china variant excluded — separate builder).
BUILDER_PATH_STRINGS = [
    # inputs
    "si_handoff.json",
    "action_board.json",
    "baskets.json",
    "subsector_rotation.json",
    "us_standouts.json",
    "foresight_cascade.json",
    # outputs
    "sector_central_data.js",
    "sector_central.json",
    "sector_central.html",
    "premiumdata",
]

#: contract section headings, in the frozen order.
CONTRACT_SECTIONS = [
    "## Routes",
    "## Mount points",
    "## Builder inputs/outputs",
    "## Generation/session fields",
    "## Navigation family + render lane",
    "## Sector Cycles counterpart",
    "## Gaps",
    "## Evidence",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_router_source_declares_every_contract_route():
    """Each route id appears in the VIEWS literal of the router the template loads."""
    js = _read(ROUTER)
    m = re.search(r"var VIEWS=\[([^\]]*)\]", js)
    assert m, "VIEWS literal not found in templates/si_workspace.js"
    declared = re.findall(r"'([a-z]+)'", m.group(1))
    assert declared == ROUTES, f"router VIEWS drifted from the contract: {declared}"


def test_template_mounts_every_contract_route_section():
    """Each route id has exactly one si-view section carrying it in the template."""
    tpl = _read(TEMPLATE)
    found = re.findall(r'<section class="si-view[^"]*" data-view="([a-z]+)"', tpl)
    assert found == ROUTES, f"template si-view sections drifted from the contract: {found}"


def test_router_is_the_script_the_template_loads():
    tpl = _read(TEMPLATE)
    assert '<script src="si_workspace.js"></script>' in tpl


def test_mount_ids_exist_exactly_once():
    tpl = _read(TEMPLATE)
    for mid in MOUNT_IDS:
        n = len(re.findall(f'id="{mid}"', tpl))
        assert n == 1, f'mount id "{mid}" expected exactly once in template, found {n}'


def test_popstate_handler_present_in_template():
    """The contract cites the mr-panel popstate at templates/sector_central.html.j2:4028."""
    tpl = _read(TEMPLATE)
    assert "window.addEventListener('popstate'" in tpl


def test_router_binds_hashchange():
    js = _read(ROUTER)
    assert "window.addEventListener('hashchange',route);" in js


def test_builder_source_names_every_contract_path():
    src = _read(BUILDER)
    missing = [p for p in BUILDER_PATH_STRINGS if p not in src]
    assert not missing, f"builder no longer names these contract paths: {missing}"


def test_navigation_family_is_site_nav():
    tpl = _read(TEMPLATE)
    assert '{% include "_site_nav.html.j2" %}' in tpl
    assert "_public_nav" not in tpl


def test_contract_file_sections_in_frozen_order():
    text = _read(CONTRACT)
    pos = -1
    for heading in CONTRACT_SECTIONS:
        idx = text.find(heading)
        assert idx > pos, f"contract section {heading!r} missing or out of order"
        pos = idx


def test_contract_records_observed_route_set_and_verdict():
    text = _read(CONTRACT)
    assert "RESTORES_VIEW" in text
    # the observed route set is stated as equal to the expected six (wrap-insensitive)
    flat = " ".join(text.split())
    assert "overview, map, moving, money, explore, confluence" in flat


def test_legacy_jobs_gate_line_lists_contract_suite():
    """The one CI line this packet edits must keep the gate suite and add this file.

    SIC-RCV appended tests/test_sector_receiver_contracts.py to the same run line;
    the pin tracks the line as registered (update together with the yml edit).
    SIC-I09A appended tests/test_sector_central_history.py to the same line;
    SIC-I05R appended tests/test_research_receiver_entry.py.
    """
    yml = _read(LEGACY_JOBS)
    line = (
        "run: python -m pytest tests/test_sector_central_gate.py "
        "tests/test_sector_central_contract.py tests/test_sector_receiver_contracts.py "
        "tests/test_sector_central_history.py tests/test_research_receiver_entry.py -q"
    )
    assert line in yml, "tier-gate run line no longer registers test_sector_central_contract.py"
    # the neighbouring suite's registration is untouched
    assert "run: python -m pytest tests/test_sector_central.py -q" in yml
