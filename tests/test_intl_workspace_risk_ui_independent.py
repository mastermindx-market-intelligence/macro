"""Independent C2 review of repaired Risk HTML plus actual attach_risks.

Uses real Jinja, lib.intl_risk_mount.attach_risks, and build_risk_section.
No stubs, source edits, network, git, providers, or publisher execution.
"""
from __future__ import annotations

import ast
import copy
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from lib.intl_risk_mount import attach_risks
from lib.intl_workspace_risk_section import build_risk_section
from tests.test_intl_risk_mount import fixture as mount_fixture
from tests.test_intl_workspace_risk_section import inputs as section_inputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "intl_workspace" / "risk_render.json"
TEMPLATE = "templates/intl_workspace/risk.html.j2"
PUBLISHER_PATH = ROOT / "scripts" / "build_intl.py"

UNSAFE_DESTINATIONS = [
    " javascript:alert(1)",
    "\tjavascript:alert(1)",
    "\njavascript:alert(1)",
    "\u00a0javascript:alert(1)",
    "\ufeffjavascript:alert(1)",
    " JavaScript:alert(document.cookie)",
    "javascript:alert(1)",
    "JAVASCRIPT:alert(1)",
    "vbscript:msgbox(1)",
    "data:text/html,<script>alert(1)</script>",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    "file:///etc/passwd",
    "https://example.test",
    "http://example.test",
    "//example.test",
    "/\\example.test",
    "/%2fexample.test",
    "/research/../company",
    "/research/./company",
    "/research//company",
    "/research/company\n",
    " # ",
    "# ",
    " #",
    "\t#",
    "#\t",
    "#",
    None,
    1,
    [],
    {},
    {"key": "company_research", "destination": " javascript:alert(1)"},
]


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.hrefs = []
        self.tags = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append((tag, values))
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "a" and "href" in values:
            self.hrefs.append(values["href"])


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def render(
    risk_section,
    registry,
    context_id="im-overview-0",
    panel_context=None,
    generation="im-workspace-generation:12345678-1234-4123-8123-123456789012",
):
    environment = Environment(
        loader=FileSystemLoader(ROOT),
        autoescape=False,
        undefined=StrictUndefined,
    )
    return environment.get_template(TEMPLATE).render(
        risk_section=risk_section,
        registry=registry,
        context_id=context_id,
        panel_context=panel_context
        or {
            "horizon": "1m",
            "currency_basis": "usd_unhedged",
            "return_basis": "price",
            "selected_market": None,
        },
        generation=generation,
    )


def collect(html):
    collector = Collector()
    collector.feed(html)
    return collector


def packet():
    data = load_fixture()
    return copy.deepcopy(data["risk_section"]), copy.deepcopy(data["registry"]), data


def company_block(html):
    return html.split("intl-risk__exposure", 1)[1].split("intl-risk__pressure", 1)[0]


def us_block(html):
    marker = 'data-im-risk-domain="us_transmission"'
    rest = html.split(marker, 1)[1]
    nxt = rest.find("data-im-risk-domain=")
    return rest if nxt < 0 else rest[:nxt]


def assert_no_script_scheme(hrefs):
    for href in hrefs:
        lowered = href.lower().lstrip()
        assert not lowered.startswith("javascript:")
        assert not lowered.startswith("data:")
        assert not lowered.startswith("vbscript:")
        assert not lowered.startswith("file:")
        assert href.startswith("/") or href.startswith("#")


def as_v1(workspace):
    workspace.pop("binding_version", None)
    workspace["panels"][0].pop("generation", None)
    workspace["config"]["source_reference"] = workspace["panels"][0]["overview"]["context"][
        "source_reference"
    ]
    return workspace




@pytest.mark.parametrize("payload", UNSAFE_DESTINATIONS)
def test_unsafe_destinations_use_fallback_not_direct_action(payload):
    section, registry, _ = packet()
    section["exposure_boundary"]["destination"] = payload
    html = render(section, registry)
    hrefs = collect(html).hrefs
    block = company_block(html)
    assert hrefs == []
    assert "javascript:" not in html.lower()
    assert "data:text/html" not in block.lower()
    assert 'href="#"' not in block
    assert "<a " not in block
    assert "data-im-risk-close-context" in block
    assert '<button type="button" data-im-risk-close-context' in block


def test_javascript_url_with_leading_space_must_fallback_not_direct_action():
    section, registry, _ = packet()
    section["exposure_boundary"]["destination"] = " javascript:alert(1)"
    html = render(section, registry)
    assert collect(html).hrefs == []
    assert "javascript:" not in html.lower()
    assert "data-im-risk-close-context" in company_block(html)


def test_padded_hash_must_not_emit_dead_anchor():
    section, registry, _ = packet()
    section["exposure_boundary"]["destination"] = " # "
    html = render(section, registry)
    block = company_block(html)
    assert collect(html).hrefs == []
    assert 'href="#"' not in block
    assert "<a " not in block
    assert "data-im-risk-close-context" in block


def test_data_uri_is_not_a_direct_research_action():
    section, registry, _ = packet()
    section["exposure_boundary"]["destination"] = "data:text/html,<script>alert(1)</script>"
    html = render(section, registry)
    assert collect(html).hrefs == []
    assert "data:" not in company_block(html)
    assert "data-im-risk-close-context" in company_block(html)


@pytest.mark.parametrize(
    "destination",
    [
        "/research/company",
        "/research/us?market=KR&view=risk",
        "#intl-legacy-research",
        {"key": "company_research", "title_en": "Company", "title_zh": "企业", "destination": "/research/ok"},
    ],
)
def test_ordinary_local_destination_is_a_real_anchor(destination):
    section, registry, _ = packet()
    section["exposure_boundary"]["destination"] = destination
    html = render(section, registry)
    hrefs = collect(html).hrefs
    expected = destination["destination"] if isinstance(destination, dict) else destination
    assert hrefs == [expected]
    assert_no_script_scheme(hrefs)
    assert "data-im-risk-close-context" not in company_block(html)


def test_fragment_and_path_with_javascript_text_are_not_javascript_scheme():
    section, registry, _ = packet()
    section["exposure_boundary"]["destination"] = "#javascript:alert(1)"
    html = render(section, registry)
    hrefs = collect(html).hrefs
    assert hrefs == ["#javascript:alert(1)"]
    assert_no_script_scheme(hrefs)

    section, registry, _ = packet()
    section["exposure_boundary"]["destination"] = "/javascript:alert(1)"
    html = render(section, registry)
    hrefs = collect(html).hrefs
    assert hrefs == ["/javascript:alert(1)"]
    assert_no_script_scheme(hrefs)


def test_qualified_us_statement_survives_real_destination():
    section, registry, _ = packet()
    section["domain_panels"]["us_transmission"]["destination"] = {
        "key": "us_transmission",
        "title_en": "US research",
        "title_zh": "美国研究",
        "destination": "/research/us",
    }
    section["domain_panels"]["us_transmission"]["summary"] = {
        "quality": "qualified",
        "state": "contained",
        "reason_codes": [],
        "evidence_refs": ["public/overall"],
        "diagnostic": {"reported_state": "contained"},
    }
    html = render(section, registry)
    block = us_block(html)
    assert "Current statement" in block
    assert "Contained" in block and "受控" in block
    assert 'href="/research/us"' in block
    assert "data-im-risk-close-context" not in block
    assert "us_from_others" not in html
    assert "raw-secret" not in html


def test_qualified_us_statement_survives_javascript_destination_without_emitting_it():
    section, registry, _ = packet()
    section["domain_panels"]["us_transmission"]["destination"] = " javascript:alert(1)"
    section["domain_panels"]["us_transmission"]["summary"] = {
        "quality": "qualified",
        "state": "transmitting",
        "reason_codes": [],
        "evidence_refs": [],
        "diagnostic": {"reported_state": "watching"},
    }
    html = render(section, registry)
    block = us_block(html)
    assert "Transmitting" in block
    assert "Reported diagnostic only" in block
    assert "Watching" in block
    assert "javascript:" not in html.lower()
    assert "data-im-risk-close-context" in block
    assert collect(html).hrefs == []


def test_unqualified_us_statement_says_unavailable_on_both_action_branches():
    section, registry, _ = packet()
    section["domain_panels"]["us_transmission"]["summary"] = {
        "quality": "unknown",
        "state": None,
        "reason_codes": ["support_unavailable"],
        "evidence_refs": [],
        "diagnostic": None,
    }
    fallback = render(section, registry)
    assert "Transmission assessment unavailable" in us_block(fallback)
    section["domain_panels"]["us_transmission"]["destination"] = "/research/us"
    linked = render(section, registry)
    block = us_block(linked)
    assert 'href="/research/us"' in block
    assert "Transmission assessment unavailable" in block
    assert "Current statement" not in block


def test_missing_denied_zero_large_and_quality_not_invented():
    section, registry, _ = packet()
    empty = copy.deepcopy(section)
    empty["currency_channels"] = []
    empty["pressure_rows"] = []
    empty_html = render(empty, registry)
    assert "data-im-risk-channel=" not in empty_html
    assert "data-im-risk-row=" not in empty_html

    denied = copy.deepcopy(section)
    denied["currency_channels"][0]["market"] = None
    denied_html = render(denied, registry)
    channel = denied_html.split('data-im-risk-channel="0"', 1)[1].split(
        "data-im-risk-channel=", 1
    )[0]
    assert "data-im-risk-market=" not in channel
    assert "Information withheld" in channel
    assert "South Korea" not in channel
    assert "韩国" not in channel
    assert "South Korea" in denied_html

    zero = copy.deepcopy(section)
    zero["currency_channels"][0]["local_return"]["value"] = 0
    zero["pressure_rows"][0]["country_credit_change"]["value"] = 0
    zero_html = render(zero, registry)
    local = zero_html.split('data-im-risk-card="local"', 1)[1].split(
        "data-im-risk-card=", 1
    )[0]
    assert re.search(r">0(\.0)?<", local.replace(" ", ""))
    credit = zero_html.split('data-im-risk-row="KR"', 1)[1].split("</tr>", 1)[0]
    assert re.search(r"\b0\b", credit)

    missing = copy.deepcopy(section)
    missing["currency_channels"][0]["usd_return"] = {
        "value": None,
        "unit": "percent",
        "quality": "unknown",
        "reason": "not_supplied",
        "window": None,
    }
    missing_html = render(missing, registry)
    usd = missing_html.split('data-im-risk-card="usd"', 1)[1].split(
        "data-im-risk-channel=", 1
    )[0]
    assert "Not supplied" in usd or "Unavailable" in usd
    assert "-2.59" not in usd

    huge = copy.deepcopy(section)
    huge["pressure_rows"][0]["country_credit_change"]["value"] = 10 ** 400
    huge_html = render(huge, registry)
    assert str(10 ** 400) in huge_html
    assert "Infinity" not in huge_html


def test_independent_field_years_and_clocks_do_not_collapse():
    section, registry, _ = packet()
    kr = section["pressure_rows"][0]
    gb = section["pressure_rows"][1]
    kr["annual_current_account"]["support"]["field_year"] = 1999
    kr["annual_current_account"]["support"]["observation_type"] = "actual"
    kr["country_credit_change"]["observation_at"] = "2011-02-03"
    gb["annual_current_account"] = copy.deepcopy(kr["annual_current_account"])
    gb["annual_current_account"]["value"] = 1.25
    gb["annual_current_account"]["quality"] = "qualified"
    gb["annual_current_account"]["reason"] = None
    gb["annual_current_account"]["support"]["field_year"] = 2099
    gb["annual_current_account"]["support"]["observation_type"] = "projection"
    gb["country_credit_change"] = {
        "value": 0,
        "quality": "qualified",
        "reason": None,
        "observation_at": "2008-11-01",
        "period": {
            "start": "2008-01-01",
            "end": "2008-12-31",
            "count": 12,
            "count_basis": "release_periods",
        },
    }
    html = render(section, registry)
    kr_row = html.split('data-im-risk-row="KR"', 1)[1].split("</tr>", 1)[0]
    gb_row = html.split('data-im-risk-row="GB"', 1)[1].split("</tr>", 1)[0]
    assert "1999" in kr_row and "2099" not in kr_row
    assert "2099" in gb_row and "1999" not in gb_row
    assert "Actual" in kr_row and "Projection" in gb_row
    assert "2011-02-03" in kr_row and "2011-02-03" not in gb_row
    assert "2008-11-01" in gb_row
    assert "20 days" not in html.lower()
    assert "current year" not in html.lower()


def test_malicious_strings_and_source_refs_are_escaped():
    section, registry, _ = packet()
    hostile = 'KR"><script>alert(1)</script>'
    registry["markets"][0]["market_id"] = hostile
    registry["markets"][0]["name_en"] = "South Korea <img src=x onerror=alert(1)>"
    registry["markets"][0]["name_zh"] = "韩国 & 注入"
    section["currency_channels"][0]["market"]["market_id"] = hostile
    section["currency_channels"][0]["market"]["name_en"] = 'South Korea <span class="x">'
    section["currency_channels"][0]["input_evidence_refs"][0]["source_reference"] = (
        "https://example.invalid/a?x=1&y=<script>"
    )
    section["pressure_rows"][0]["market_id"] = hostile
    html = render(section, registry, context_id='im"><img src=x onerror=alert(1)>')
    assert "<script>" not in html
    assert "<img src=x" not in html
    assert "韩国 &amp; 注入" in html
    assert "https://example.invalid/a?x=1&amp;y=&lt;script&gt;" in html
    assert "&lt;script&gt;" in html


def test_denied_channel_does_not_borrow_registry_or_alias_names():
    section, registry, _ = packet()
    registry["markets"][0]["name_en"] = "AliasKoreaFromRegistry"
    section["currency_channels"][0]["market"] = None
    html = render(section, registry)
    channel = html.split('data-im-risk-channel="0"', 1)[1].split(
        "data-im-risk-channel=", 1
    )[0]
    assert "AliasKoreaFromRegistry" in html
    assert "AliasKoreaFromRegistry" not in channel
    assert "South Korea" not in channel
    assert "Information withheld" in channel


def test_source_alias_keeps_admitted_channel_identity():
    section, registry, _ = packet()
    registry["markets"][0]["name_en"] = "AliasKorea"
    section["currency_channels"][0]["market"]["name_en"] = "AdmittedKorea"
    html = render(section, registry)
    channel = html.split('data-im-risk-channel="0"', 1)[1].split(
        "data-im-risk-channel=", 1
    )[0]
    assert "AliasKorea" in html
    assert "AliasKorea" not in channel
    assert "AdmittedKorea" in channel


def test_generation_v2_emits_attribute_v1_omits_it():
    section, registry, _ = packet()
    v2 = render(section, registry, generation="im-workspace-generation:aaaa")
    v1 = render(section, registry, generation=None)
    assert 'data-im-generation="im-workspace-generation:aaaa"' in v2
    assert "data-im-generation" not in v1


def test_domain_panels_are_dict_values_and_all_six_keys_render():
    section, registry, _ = packet()
    html = render(section, registry)
    assert html.count("data-im-risk-domain=") == 6
    for key in (
        "origin_stress",
        "us_transmission",
        "statistical_connectedness",
        "return_correlation",
        "directed_pressure",
        "structural_fragility",
    ):
        assert f'data-im-risk-domain="{key}"' in html
    listed = copy.deepcopy(section)
    listed["domain_panels"] = list(section["domain_panels"].values())
    listed_html = render(listed, registry)
    assert listed_html.count("data-im-risk-domain=") == 0


def test_domain_copy_keeps_noncausal_nonissuer_semantics_and_reason_spacing():
    section, registry, _ = packet()
    html = render(section, registry)
    assert "VAR/GFEVD statistical connectedness is not causality." in html
    assert "Directed model pressure is not issuer exposure." in html
    assert "Daily return correlation is distinct from the weekly correlation matrix." in html
    assert "A coincident EM origin aggregate. It is not a country diagnosis." in html
    assert "Slow-moving country balance-sheet indicators" in html
    assert 'class="intl-risk__reason"' in html
    card = html.split("data-im-risk-contribution", 1)[1].split("</p>", 1)[0]
    assert card.count("个百分点") == 1
    assert "pp" in card


def test_publisher_static_wiring_passes_empty_grants_and_preserves_failures():
    source = PUBLISHER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_publication_workspace"
    )
    text = ast.get_source_segment(source, function)
    assert "measures={}" in text
    assert "field_support={}" in text
    assert "summary_eligibility={}" in text
    assert "destinations={}" in text
    assert "risk_desk=risk_desk" in text
    assert "cgl=cgl" in text
    assert "attach_macros" in text
    assert "attach_risks" in text

    tries = [node for node in function.body if isinstance(node, ast.Try)]
    assert len(tries) == 2
    macro_try, risk_try = tries
    macro_calls = [
        node
        for node in ast.walk(macro_try)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert any(call.func.id == "attach_macros" for call in macro_calls)
    assert not any(call.func.id == "attach_risks" for call in macro_calls)
    risk_calls = [
        node
        for node in ast.walk(risk_try)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert any(call.func.id == "attach_risks" for call in risk_calls)
    assert function.body[-1].value.id == "workspace"

    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    payload = None
    cgl = None
    for node in ast.walk(main):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_publication_workspace":
            mapped = {keyword.arg: keyword.value for keyword in node.keywords}
            payload = mapped["risk_desk"]
            cgl = mapped["cgl"]
    assert isinstance(payload, ast.Name) and payload.id == "_intl_risk_payload"
    assert isinstance(cgl, ast.Name) and cgl.id == "_cgl_artifact"


def test_actual_section_and_mount_render_six_domains_and_supported_statement():
    source = section_inputs()
    html = render(build_risk_section(**source), source["registry"])
    assert html.count("data-im-risk-domain=") == 6
    assert "Contained" in html
    assert "-2.59" in html
    assert "/research/company" in collect(html).hrefs
    assert "#us-transmission" in collect(html).hrefs

    workspace, mount_source = mount_fixture()
    mounted = attach_risks(workspace, **mount_source)
    panel = mounted["risks"][0]
    mounted_html = render(
        panel["risk_section"],
        mounted["risk_registry"],
        context_id=panel["context_id"],
        panel_context=panel["context"],
        generation=panel["generation"],
    )
    assert 'data-im-generation="' in mounted_html
    assert "Contained" in mounted_html
    assert "-2.59" in mounted_html


def test_attach_risks_v2_keeps_generation_and_does_not_mutate_owner():
    workspace, source = mount_fixture()
    before = copy.deepcopy((workspace, source))
    mounted = attach_risks(workspace, **source)
    assert (workspace, source) == before
    assert mounted["existing_material"] == {"owner": "untouched"}
    assert mounted["risks"][0]["generation"].startswith("im-workspace-generation:")
    assert mounted["risks"][0]["context"]["selected_market"] is None
    assert mounted["risk_registry"] == source["registry"]
    assert mounted["risks"][0]["risk_section"]["pressure_rows"][0]["country_credit_change"]["value"] == 0
    mounted["risk_registry"]["markets"][0]["name_en"] = "changed"
    assert source["registry"]["markets"][0]["name_en"] == "South Korea"


@pytest.mark.parametrize("value", [10 ** 400, -(10 ** 400), 0])
def test_real_v1_retains_currency_and_withholds_new_fields(value):
    workspace, source = mount_fixture()
    as_v1(workspace)
    source["measures"]["KR.country_credit_change"]["value"] = value
    panel = attach_risks(workspace, **source)["risks"][0]
    section = panel["risk_section"]
    assert "generation" not in panel
    assert section["currency_channels"][0]["local_return"]["value"] == -1.8
    assert section["pressure_rows"][0]["country_credit_change"]["quality"] == "unknown"
    assert section["domain_panels"]["us_transmission"]["summary"]["quality"] == "unknown"
    html = render(section, source["registry"], generation=None)
    assert "data-im-generation" not in html
    assert "-1.8" in html or "-1.80" in html
    assert str(value) not in html or value == 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_v1_nonfinite_grants_remain_invalid_risk_workspace(bad):
    workspace, source = mount_fixture()
    as_v1(workspace)
    source["measures"]["KR.country_credit_change"]["value"] = bad
    with pytest.raises(ValueError, match="^invalid_risk_workspace$"):
        attach_risks(workspace, **source)


def test_v1_unknown_measure_key_is_not_permitted_because_fields_would_be_suppressed():
    workspace, source = mount_fixture()
    as_v1(workspace)
    source["measures"]["CN.country_credit_change"] = copy.deepcopy(
        source["measures"]["KR.country_credit_change"]
    )
    with pytest.raises(ValueError, match="^invalid_risk_workspace$"):
        attach_risks(workspace, **source)


def test_attach_risks_rejects_duplicate_context_and_existing_risks():
    workspace, source = mount_fixture()
    workspace["panels"].append(copy.deepcopy(workspace["panels"][0]))
    with pytest.raises(ValueError, match="^invalid_risk_workspace$"):
        attach_risks(workspace, **source)
    workspace, source = mount_fixture()
    workspace["risks"] = []
    with pytest.raises(ValueError, match="^invalid_risk_workspace$"):
        attach_risks(workspace, **source)
    workspace, source = mount_fixture()
    assert attach_risks(None, **source) is None
