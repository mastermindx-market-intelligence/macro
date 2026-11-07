from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "research" / "financial_intelligence_fabric" / "FIF_P0_VIEW_CONTRACT.json"
DOC = ROOT / "research" / "financial_intelligence_fabric" / "FIF_P0_ANALYST_JOURNEYS.md"
TEMPLATE = ROOT / "templates" / "fundamental_forensics.html.j2"
SCRIPT = ROOT / "templates" / "fundamental_forensics.js"
API = ROOT / "app" / "forensics.py"

FROZEN_TOP_LEVEL = [
    "schema",
    "frozen_at_commit",
    "amendment_rule",
    "surface",
    "journeys",
    "panels",
    "page_endpoints",
    "api_not_called_by_page",
    "payload_contract",
    "first_viewport",
    "i18n",
    "authority",
]
PAYLOAD_LISTS = [
    "state_keys",
    "company_keys",
    "period_keys",
    "finding_keys",
    "disclosure_finding_keys",
    "evidence_receipt_keys",
    "health_keys",
    "attested_history_latest_keys",
    "query_cell_keys",
]
JOURNEY_IDS = ["J1", "J2", "J3", "J4", "J5"]
STATUS_ENUM = {"exists", "partial", "missing"}
GET_ROUTE_RE = re.compile(r"@router\.get\(\s*\"([^\"]+)\"", re.S)
POST_ROUTE_RE = re.compile(r"@router\.post\(\s*\"([^\"]+)\"", re.S)
LITERAL_SCRIPT = "check_validated_claims.py"
CI_GUARDED_CLAIM = LITERAL_SCRIPT[len("check_") :].split("_", 1)[0]


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _js() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _api() -> str:
    return API.read_text(encoding="utf-8")


def _word_in_js(key: str, js: str) -> bool:
    return re.search(r"\b" + re.escape(key) + r"\b", js) is not None


def _js_knows_endpoint(path: str, js: str) -> bool:
    if "{" not in path:
        if path in js:
            return True
        attested = "/api/forensics/v1/attested-history"
        if path.startswith(attested + "/") and attested in js:
            return path[len(attested):] in js
        return False
    prefix = path.split("{", 1)[0]
    if prefix in js:
        return True
    attested = "/api/forensics/v1/attested-history"
    if not path.startswith(attested + "/") or attested not in js:
        return False
    remainder = path[len(attested):]
    static_bits = [bit for bit in re.split(r"\{[^}]+\}", remainder) if bit]
    return all(bit in js for bit in static_bits)


def _evidence_line(ref: str) -> tuple[Path, int]:
    path_str, loc = ref.rsplit(":", 1)
    line = int(loc.split("-")[-1])
    return ROOT / path_str, line


def test_manifest_parses_and_schema_frozen_commit_shape():
    data = _contract()
    assert data["schema"] == "fundamental_forensics.p0_view_contract/v1"
    commit = data["frozen_at_commit"]
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    assert commit == "5267c66846e7733bc1eb30edc1524daff51598ca"
    assert isinstance(data["amendment_rule"], str) and data["amendment_rule"].strip()
    surface = data["surface"]
    assert surface == {
        "template": "templates/fundamental_forensics.html.j2",
        "script": "templates/fundamental_forensics.js",
        "styles": "templates/fundamental_forensics.css",
        "api": "app/forensics.py",
    }
    for rel in surface.values():
        assert (ROOT / rel).is_file()


def test_top_level_keys_are_exactly_the_frozen_set():
    data = _contract()
    assert list(data.keys()) == FROZEN_TOP_LEVEL


def test_five_journeys_in_masterplan_order():
    journeys = _contract()["journeys"]
    assert [row["journey_id"] for row in journeys] == JOURNEY_IDS
    assert len(journeys) == 5
    for row in journeys:
        assert set(row) >= {
            "journey_id",
            "name_en",
            "name_zh",
            "status",
            "evidence",
            "gap",
            "p2_question",
        }
        assert row["name_en"].strip()
        assert row["name_zh"].strip()
        assert row["p2_question"].strip()
        assert isinstance(row["evidence"], list) and row["evidence"]
        # P2 amendment: every journey records the seat ruling that resolved it.
        assert row["p2_ruling"].strip()


def test_journey_status_enum_and_gaps():
    for row in _contract()["journeys"]:
        assert row["status"] in STATUS_ENUM
        gap = row["gap"]
        assert isinstance(gap, str)
        if row["status"] in {"partial", "missing"}:
            assert gap.strip()


def test_panel_dom_ids_occur_once_in_template():
    html = _template()
    seen = []
    for panel in _contract()["panels"]:
        dom_id = panel["dom_id"]
        assert re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", dom_id)
        needle = f'id="{dom_id}"'
        assert html.count(needle) == 1, dom_id
        seen.append(dom_id)
        assert panel["panel_id"].strip()
        assert isinstance(panel["data_source"], str) and panel["data_source"].strip()
        assert isinstance(panel["journeys"], list)
        for journey_id in panel["journeys"]:
            assert journey_id in JOURNEY_IDS
    assert len(seen) == len(set(seen))


def test_page_endpoints_in_js_and_registered_gets():
    js = _js()
    gets = set(GET_ROUTE_RE.findall(_api()))
    posts = set(POST_ROUTE_RE.findall(_api()))
    endpoints = _contract()["page_endpoints"]
    assert endpoints
    for item in endpoints:
        method = item["method"]
        assert method in {"GET", "POST"}
        path = item["path"]
        assert isinstance(path, str) and path.startswith("/api/forensics/")
        assert _js_knows_endpoint(path, js), path
        if method == "GET":
            assert path in gets, path
        else:
            assert path in posts, path


def test_api_not_called_by_page_are_posts_absent_from_js():
    js = _js()
    posts = set(POST_ROUTE_RE.findall(_api()))
    unused = _contract()["api_not_called_by_page"]
    assert len(unused) == 1
    for item in unused:
        assert item["method"] == "POST"
        path = item["path"]
        assert path in posts, path
        assert path not in js, path
        assert "/api/forensics/v1/financial/" in path


def test_payload_contract_keys_occur_in_js():
    js = _js()
    payload = _contract()["payload_contract"]
    assert list(payload.keys()) == PAYLOAD_LISTS
    for list_name in PAYLOAD_LISTS:
        keys = payload[list_name]
        assert isinstance(keys, list) and keys
        assert len(keys) == len(set(keys))
        for key in keys:
            assert isinstance(key, str) and key
            assert _word_in_js(key, js), f"{list_name}:{key}"


def test_journey_evidence_paths_exist():
    for row in _contract()["journeys"]:
        for ref in row["evidence"]:
            assert ":" in ref, ref
            path, line = _evidence_line(ref)
            assert path.is_file(), ref
            assert line >= 1
            assert len(path.read_text(encoding="utf-8").splitlines()) >= line, ref


def test_i18n_template_title_attribute_count():
    html = _template()
    live = len(re.findall(r"\btitle=", html))
    i18n = _contract()["i18n"]
    assert i18n["template_title_attributes"] == live
    assert live == 0
    assert "t(en, zh)" in i18n["mechanism"]
    assert "pair(" in i18n["mechanism"]


FOLD_RECEIPT = "mockups/evidence/fundamental_forensics_p2/populated/fold_measurement.json"
SPEC = ROOT / "research" / "financial_intelligence_fabric" / "FIF_P2_DESIGN_SPEC.md"


def test_first_viewport_measured_records_the_fold_receipt():
    viewport = _contract()["first_viewport"]
    assert viewport["desktop_1440"].strip()
    assert viewport["mobile_390"].strip()
    measured = viewport["measured"]
    assert isinstance(measured, dict)
    assert measured["receipt"] == FOLD_RECEIPT
    assert measured["desktop_1440"]["viewport_height"] == 900
    assert measured["mobile_390"]["viewport_height"] == 844
    assert measured["desktop_1440"]["meets_contract"] is True
    # Recorded as measured, not as hoped: after the seat repair round the lead brief
    # ends inside the 390 fold (it crossed it before the desk header was compacted).
    assert measured["mobile_390"]["meets_contract"] is True


def test_am7_amends_the_desktop_fold_clause():
    """AM7 (seat ruling 10-12): at >=1100px the tab rail is navigation chrome."""
    measured = _contract()["first_viewport"]["measured"]
    desktop = measured["desktop_1440"]
    assert desktop["amended_by"] == "AM7"
    assert "AM7" in desktop["note"]
    for viewport in (desktop, measured["mobile_390"]):
        assert "tabs" not in viewport["within_first_viewport"]
    assert desktop["navigation_chrome_in_first_viewport"] == ["tabs"]
    spec = SPEC.read_text(encoding="utf-8")
    assert any(
        line.startswith("- **AM7 (1440 tab rail in the first viewport;")
        for line in spec.splitlines()
    )
    assert "Tab bar and panels start below the fold (amended by AM7)." in spec


@pytest.mark.needs_full_checkout("mockups")
def test_first_viewport_measured_matches_the_committed_receipt():
    measured = _contract()["first_viewport"]["measured"]
    probes = set(measured["probes"])
    for cell in _rest_cells(measured):
        want = measured[CONTRACTED_VIEWPORTS[cell["viewport"]]]
        found = {m["name"]: m for m in cell["measurements"] if m["found"] and m["height"] > 0}
        inside = sorted(
            n
            for n, m in found.items()
            if m["within_first_viewport"] and n not in probes
        )
        assert inside == want["within_first_viewport"], cell["cell_id"]
        lead = found["lead"]
        assert lead["viewport_height"] == want["viewport_height"]
        span = [int(round(lead["top"])), int(round(lead["bottom"]))]
        assert span == want["lead_px"][cell["locale"]], cell["cell_id"]
        tabs = found["tabs"]
        if cell["viewport"] == "desktop":
            # AM7: the rail may sit inside the fold as navigation chrome, its top
            # pinned by the receipt, with every glance module ending above it.
            assert tabs["within_first_viewport"] is True, cell["cell_id"]
            assert [
                int(round(tabs["top"])),
                int(round(tabs["bottom"])),
            ] == want["tabs_px"][cell["locale"]], cell["cell_id"]
            for name in want["within_first_viewport"]:
                assert found[name]["bottom"] <= tabs["top"], (cell["cell_id"], name)
        else:
            # §1.1 at 390 is unchanged by AM7: the tab bar starts below the fold.
            assert tabs["within_first_viewport"] is False, cell["cell_id"]


# The first-viewport contract pins two viewports. Since A43 r2 the populated set is
# captured at desktop, tablet and mobile, so the receipt also records four tablet
# rest cells; they are evidence for the tablet desk-header fit, not contracted here.
CONTRACTED_VIEWPORTS = {"desktop": "desktop_1440", "mobile": "mobile_390"}
RECEIPT_REST_CELLS_PER_VIEWPORT = {"desktop": 4, "tablet": 4, "mobile": 4}


def _rest_cells(measured: dict) -> list[dict]:
    cells = json.loads((ROOT / measured["receipt"]).read_text(encoding="utf-8"))
    rest = [c for c in cells if c["force_state"] is None and c["mode"] == "populated"]
    per_viewport = {
        viewport: sum(1 for c in rest if c["viewport"] == viewport)
        for viewport in RECEIPT_REST_CELLS_PER_VIEWPORT
    }
    assert per_viewport == RECEIPT_REST_CELLS_PER_VIEWPORT, per_viewport
    assert len(rest) == sum(RECEIPT_REST_CELLS_PER_VIEWPORT.values())
    contracted = [c for c in rest if c["viewport"] in CONTRACTED_VIEWPORTS]
    assert len(contracted) == 8
    return contracted


@pytest.mark.needs_full_checkout("mockups")
def test_launcher_box_clears_every_first_viewport_module_and_the_coverage_stat():
    """P2 r3 item c: the fab rect inflated by 8px touches no module nor covstat."""
    measured = _contract()["first_viewport"]["measured"]
    probes = set(measured["probes"])
    for cell in _rest_cells(measured):
        want = measured[CONTRACTED_VIEWPORTS[cell["viewport"]]]
        assert set(want["within_first_viewport"]).isdisjoint(probes)
        found = {m["name"]: m for m in cell["measurements"] if m["found"] and m["height"] > 0}
        fab = found["fab"]
        assert fab["found"] is True and fab["rendered"] is True, cell["cell_id"]
        inflated = (fab["left"] - 8, fab["top"] - 8, fab["right"] + 8, fab["bottom"] + 8)
        for name in [*want["within_first_viewport"], "covstat"]:
            other = found[name]
            overlaps = not (
                other["right"] <= inflated[0]
                or other["left"] >= inflated[2]
                or other["bottom"] <= inflated[1]
                or other["top"] >= inflated[3]
            )
            assert not overlaps, (cell["cell_id"], name)


@pytest.mark.needs_full_checkout("mockups")
def test_mobile_latest_button_is_one_line_in_both_locales():
    """P2 r3 item b: ZH 最新 keeps the EN height (no wrap) in both themes."""
    measured = _contract()["first_viewport"]["measured"]
    heights: dict[tuple[str, str], float] = {}
    for cell in _rest_cells(measured):
        if cell["viewport"] != "mobile":
            continue
        latest = next(m for m in cell["measurements"] if m["name"] == "latest")
        assert latest["found"] is True and latest["rendered"] is True, cell["cell_id"]
        heights[(cell["locale"], cell["theme"])] = latest["height"]
    assert set(heights) == {("en", "dark"), ("en", "light"), ("zh", "dark"), ("zh", "light")}
    for theme in ("dark", "light"):
        assert abs(heights[("en", theme)] - heights[("zh", theme)]) <= 0.5, theme


@pytest.mark.needs_full_checkout("mockups")
def test_launcher_clearance_px_equals_the_receipt():
    """P2 r3 item c: the contract clearance is the measured fab/covstat gap."""
    measured = _contract()["first_viewport"]["measured"]
    clearance = measured["mobile_390"]["launcher_clearance_px"]
    assert set(clearance) == {"en", "zh"}
    for cell in _rest_cells(measured):
        if cell["viewport"] != "mobile":
            continue
        found = {m["name"]: m for m in cell["measurements"] if m["found"] and m["height"] > 0}
        fab, covstat = found["fab"], found["covstat"]
        overlaps_vertically = not (
            fab["bottom"] <= covstat["top"] or covstat["bottom"] <= fab["top"]
        )
        if overlaps_vertically:
            gap = round(fab["left"] - covstat["right"])
        elif fab["top"] >= covstat["bottom"]:
            gap = round(fab["top"] - covstat["bottom"])
        else:
            gap = round(covstat["top"] - fab["bottom"])
        assert clearance[cell["locale"]] == gap, cell["cell_id"]


def test_doc_mentions_journeys_and_every_dom_id():
    assert DOC.is_file()
    text = DOC.read_text(encoding="utf-8")
    for journey_id in JOURNEY_IDS:
        assert journey_id in text
    for panel in _contract()["panels"]:
        assert panel["dom_id"] in text
    assert "5267c66846e7733bc1eb30edc1524daff51598ca" in text
    assert "No UI change in P0" in text


def test_owned_files_omit_ci_guarded_claim_token():
    for path in (CONTRACT, DOC):
        body = path.read_text(encoding="utf-8").replace(LITERAL_SCRIPT, "")
        assert CI_GUARDED_CLAIM not in body, path


def test_authority_display_only_and_review_priority():
    authority = _contract()["authority"]
    assert authority["display_only"] is True
    assert authority["finding_authority"] == "review_priority_only"
