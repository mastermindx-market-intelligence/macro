from __future__ import annotations

import json
import re
from pathlib import Path

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
    endpoints = _contract()["page_endpoints"]
    assert endpoints
    for item in endpoints:
        assert item["method"] == "GET"
        path = item["path"]
        assert isinstance(path, str) and path.startswith("/api/forensics/")
        assert _js_knows_endpoint(path, js), path
        assert path in gets, path


def test_api_not_called_by_page_are_posts_absent_from_js():
    js = _js()
    posts = set(POST_ROUTE_RE.findall(_api()))
    unused = _contract()["api_not_called_by_page"]
    assert len(unused) == 4
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


def test_first_viewport_measured_is_false():
    viewport = _contract()["first_viewport"]
    assert viewport["measured"] is False
    assert viewport["desktop_1440"].strip()
    assert viewport["mobile_390"].strip()


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
