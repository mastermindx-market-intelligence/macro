"""Render contracts for the supplied-field Macro projection."""

import copy
import json
import sys
import re
from html.parser import HTMLParser
from html import unescape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from bs4 import BeautifulSoup
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_intl_workspace_macro import components, cycle, inputs, measure


SOURCE_NOTICE = {
    "market_id": "EZ",
    "field": "policy_rate",
    "instrument_id": "deposit_facility",
    "origin_url": "https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV",
}


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.ids = []
        self.hrefs = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append((tag, values))
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "a" and "href" in values:
            self.hrefs.append(values["href"])


def build_fixture():
    # Endpoint copied from the official owner store on 2026-10-07; render grants are synthetic.
    latest_ecb_observation = {"date": "2026-10-06T00:00:00", "value": 2.5}
    packet = inputs(
        context={
            "selected_market": None,
            "horizon": "1y",
            "currency_basis": "local",
            "return_basis": "price",
        },
        registry={
            "markets": [
                {
                    "market_id": "EZ",
                    "name_en": 'Euro Area <span lang="evil">names</span>',
                    "name_zh": "欧元区 & 欧洲央行",
                },
                {
                    "market_id": "JP",
                    "name_en": "Japan",
                    "name_zh": "日本",
                },
                {
                    "market_id": "GB",
                    "name_en": "United Kingdom",
                    "name_zh": "英国",
                },
            ],
            "horizons": ["1y"],
            "bases": ["local", "usd_unhedged"],
        },
        measures={},
        cycle_evidence={},
        destinations={
            "economic_cycle": {
                "key": "economic_cycle",
                "title_en": "Economic research",
                "title_zh": "经济研究",
                "destination": "/research/economic",
            },
            "market_response": {
                "key": "market_response",
                "title_en": "Market response",
                "title_zh": "市场反应",
                "destination": None,
            },
        },
    )
    packet["measures"]["EZ.policy_rate"] = measure(
        value=latest_ecb_observation["value"],
        observation_at=latest_ecb_observation["date"],
        source_reference="ECB FM.D.U2.EUR.4F.KR.DFR.LEV & provenance",
        evidence_key="ECB deposit facility / 欧洲央行存款便利",
    )
    packet["measures"]["EZ.gdp_yoy"] = measure(
        value=0,
        instrument={"kind": "macro_yoy", "id": 'gdp<">&report', "market_id": "EZ"},
        source_reference="gdp owner text & provenance",
        evidence_key="ez-gdp-zero",
    )
    packet["measures"]["JP.cpi_yoy"] = measure(
        quality="stale",
        reason="source_stale",
        value=1.25,
        instrument={"kind": "macro_yoy", "id": "cpi", "market_id": "JP"},
        observation_at="2025-01-31",
        source_reference="https://example.invalid/cpi?x=1&y=<script>",
        evidence_key="jp-cpi-stale",
    )
    packet["measures"]["JP.policy_proxy"] = measure(
        quality="denied",
        reason="value_denied",
        value_permission="denied",
        value=3,
        instrument={"kind": "effective_rate", "id": "secret-proxy", "market_id": "JP"},
        observation_at="2026-01-01",
        source_reference="secret proxy source",
        evidence_key="secret-proxy",
    )
    packet["measures"]["GB.policy_rate"] = measure(
        quality="denied",
        reason="metadata_denied",
        metadata="denied",
        value_permission="denied",
        value=None,
        unit=None,
        instrument=None,
        period=None,
        observation_at=None,
        calculation_at=None,
        source_reference=None,
        evidence_key=None,
    )
    packet["cycle_evidence"]["EZ"] = cycle(
        method_ref="owner/mixed@7",
        method_kind="mixed_composite",
        economic_support=None,
    )
    from lib.intl_workspace_macro import build_macro_section

    return build_macro_section(**packet), packet["registry"]


def render(
    macro_section,
    registry,
    context_id="intl-macro-one",
    panel_context=None,
    generation="macro-v2",
    source_notice=SOURCE_NOTICE,
):
    environment = Environment(
        loader=FileSystemLoader(Path(__file__).resolve().parents[1]),
        autoescape=False,
        undefined=StrictUndefined,
    )
    template = environment.get_template("templates/intl_workspace/macro.html.j2")
    return template.render(
        macro_section=macro_section,
        registry=registry,
        context_id=context_id,
        panel_context=panel_context
        or {"horizon": "1y", "currency_basis": "local", "return_basis": "price"},
        generation=generation,
        source_notice=source_notice,
    )


def collect(html):
    collector = Collector()
    collector.feed(html)
    return collector


def source_reference_measure(**overrides):
    return measure(**{
        "quality": "stale", "reason": "source_stale", "source_reference": None,
        "instrument": {"kind": "macro_yoy", "id": "gdp", "market_id": "EZ"},
        "evidence_key": "synthetic:gdp-zero", **overrides,
    })


def source_reference_slot(**overrides):
    from lib.intl_workspace_macro import build_macro_section
    packet = inputs(measures={"EZ.gdp_yoy": source_reference_measure(**overrides)},
                    cycle_evidence={}, destinations={})
    section = build_macro_section(**packet)
    before = copy.deepcopy(section)
    soup = BeautifulSoup(render(section, packet["registry"]), "html.parser")
    assert section == before
    return soup.select_one('[data-im-macro-market="EZ"] .intl-macro__metric-slot[id$="-gdp_yoy"]')


@pytest.mark.parametrize("quality,reason,permission", [
    ("stale", "source_stale", "allowed"), ("missing", "not_supplied", "allowed"),
    ("failed", "source_failed", "allowed"), ("denied", "value_denied", "denied"),
])
def test_absent_measure_source_reference_is_bilingual_without_borrowing(quality, reason, permission):
    slot = source_reference_slot(quality=quality, reason=reason, value_permission=permission)
    reference = slot.select_one(".intl-macro__source-reference")
    assert reference.select_one(".l-en").get_text(strip=True) == "Not supplied"
    assert reference.select_one('.l-zh[lang="zh"]').get_text(strip=True) == "未提供"
    assert "None" not in reference.get_text()
    assert not reference.select("a")
    assert "2026-09-10" in slot.get_text()
    assert "synthetic:gdp-zero" in slot.get_text()
    value = slot.select_one("[data-im-macro-value]")
    assert (value.get_text() if value else None) == ("0" if quality == "stale" else None)


@pytest.mark.parametrize("reference", ["None", 'synthetic:<script>alert(1)</script>&"owner"'])
def test_supplied_measure_source_reference_remains_exact_escaped_text(reference):
    slot = source_reference_slot(source_reference=reference)
    node = slot.select_one(".intl-macro__source-reference")
    assert node.get_text() == reference
    assert not node.select("script, a, .l-en, .l-zh")


@pytest.mark.parametrize("metadata", ["denied", "unknown"])
def test_measure_source_reference_does_not_open_withheld_metadata(metadata):
    slot = source_reference_slot(metadata=metadata, quality="denied", reason="metadata_denied",
                                 value_permission="denied", source_reference="private-source")
    assert not slot.select(".intl-macro__evidence")
    assert "private-source" not in slot.get_text()


def render_source_reference_page():
    """Synthetic permitted metadata through the existing native publication path."""
    from uuid import uuid4
    from engine.intl_inputs import countries
    from engine.intl_workspace_overview import build_workspace_overviews
    from lib.intl_macro_mount import attach_macros
    from tests.test_intl_workspace_integration import render_fixture
    workspace = build_workspace_overviews(None, workspace_generation=f"im-workspace-generation:{uuid4()}")
    registry = {
        "markets": [{"market_id": key, "name_en": row["name"], "name_zh": row["name_zh"]}
                    for key, row in countries().items()],
        "horizons": workspace["config"]["horizons"], "bases": workspace["config"]["bases"],
    }
    workspace = attach_macros(workspace, registry=registry,
                              measures={"EZ.gdp_yoy": source_reference_measure()},
                              cycle_evidence={}, destinations={})
    workspace["macro_registry"] = registry
    return render_fixture(workspace_payload=workspace)


CYCLE_LABELS = [
    ("Q1", "goldilocks", "Goldilocks", "金发女孩"),
    ("Q2", "reflation", "Reflation", "再通胀"),
    ("Q3", "stagflation", "Stagflation", "滞胀"),
    ("Q4", "growth_scare", "Growth-scare", "增长恐慌"),
]


def cycle_label_packet(quad, key):
    packet = inputs()
    evidence = packet["cycle_evidence"]["EZ"]
    evidence.update(reported_quad=quad, raw_quad=quad)
    evidence["economic_support"]["heading_key"] = key
    return packet


@pytest.mark.parametrize("quad,key,en,zh", CYCLE_LABELS)
def test_supported_cycle_heading_has_bilingual_reading_and_selected_link(quad, key, en, zh):
    from lib.intl_workspace_macro import build_macro_section
    packet = cycle_label_packet(quad, key)
    section = build_macro_section(**packet)
    before = copy.deepcopy(section)
    soup = BeautifulSoup(render(section, packet["registry"]), "html.parser")
    composite = soup.select_one(".intl-macro__composite section")
    heading = composite.find("p")
    link = soup.select_one(".intl-macro__reads > section:first-child a")
    for node in (heading, link):
        assert node.select_one(".l-en").get_text(strip=True) == en
        assert node.select_one('.l-zh[lang="zh"]').get_text(strip=True) == zh
    assert link["href"] == "/research/euro-area"
    assert section == before
    assert section["cycle_rows"][0]["supported_heading"] == key
    assert "owner/economic-cycle@1" in composite.get_text()


@pytest.mark.parametrize("kind", ["mixed", "stale", "disagreement"])
def test_cycle_labels_do_not_promote_unqualified_source(kind):
    from lib.intl_workspace_macro import build_macro_section
    packet = cycle_label_packet("Q1", "goldilocks")
    evidence = packet["cycle_evidence"]["EZ"]
    if kind == "mixed":
        evidence.update(method_kind="mixed_composite", economic_support=None)
    elif kind == "stale":
        evidence.update(quality="stale", reason="source_stale")
    else:
        evidence["economic_support"]["disagreement"] = True
    section = build_macro_section(**packet)
    assert section["cycle_rows"][0]["supported_heading"] is None
    soup = BeautifulSoup(render(section, packet["registry"]), "html.parser")
    assert not soup.select_one(".intl-macro__reads > section:first-child a")
    assert "no economic-cycle diagnosis is claimed" in soup.get_text()
    for _, _, en, zh in CYCLE_LABELS:
        assert en not in soup.get_text()
        assert zh not in soup.get_text()


def render_cycle_label_page():
    """Synthetic admitted headings through the native publisher, not live qualification."""
    from uuid import uuid4
    from engine.intl_inputs import countries
    from engine.intl_workspace_overview import build_workspace_overviews
    from lib.intl_macro_mount import attach_macros
    from tests.test_intl_workspace_integration import render_fixture
    workspace = build_workspace_overviews(None, workspace_generation=f"im-workspace-generation:{uuid4()}")
    registry = {
        "markets": [{"market_id": key, "name_en": row["name"], "name_zh": row["name_zh"]}
                    for key, row in countries().items()],
        "horizons": workspace["config"]["horizons"], "bases": workspace["config"]["bases"],
    }
    measures, cycles = {}, {}
    for market, (quad, key, _, _) in zip(countries(), CYCLE_LABELS):
        packet = cycle_label_packet(quad, key)
        evidence = packet["cycle_evidence"]["EZ"]
        evidence["economic_support"]["dependency_keys"] = [f"{market}.gdp_yoy", f"{market}.cpi_yoy"]
        cycles[market] = evidence
        for field in ("gdp_yoy", "cpi_yoy"):
            metric = packet["measures"][f"EZ.{field}"]
            metric["value"] = 2
            metric["instrument"]["market_id"] = market
            measures[f"{market}.{field}"] = metric
    workspace = attach_macros(workspace, registry=registry, measures=measures,
                              cycle_evidence=cycles, destinations={})
    workspace["macro_registry"] = registry
    return render_fixture(workspace_payload=workspace)


def stale_component_fixture(method_ref="owner/mixed@7"):
    from lib.intl_workspace_macro import build_macro_section
    packet = inputs(measures={}, cycle_evidence={"EZ": cycle(
        quality="stale", reason="source_stale", method_kind="mixed_composite",
        method_ref=method_ref, asof=None, components=None, economic_support=None,
    )})
    return build_macro_section(**packet), packet["registry"]


@pytest.mark.parametrize("method_ref", ["owner/mixed@7", None])
def test_stale_composite_without_components_keeps_panel_readable(method_ref):
    section, registry = stale_component_fixture(method_ref)
    before = copy.deepcopy(section)
    html = render(section, registry)
    composite = BeautifulSoup(html, "html.parser").select_one(".intl-macro__composite")
    text = composite.get_text(" ", strip=True)
    assert "Component evidence not supplied." in text
    assert "未提供分项依据。" in text
    assert "Stale data" in text and "数据过期" in text
    assert "None" not in text
    assert "As of" not in text and "2026-09-10" not in text
    assert ("owner/mixed@7" in text) == (method_ref is not None)
    assert "Available macro observations" in html
    assert section == before


def test_supplied_composite_keeps_its_original_components_and_clock():
    section, registry = build_fixture()
    html = render(section, registry)
    composite = BeautifulSoup(html, "html.parser").select_one(".intl-macro__composite")
    text = composite.get_text(" ", strip=True)
    assert "Component evidence not supplied." not in text
    for axis in ("growth", "inflation"):
        for component in section["cycle_rows"][0]["components"][axis]:
            assert component["key"] in text
    assert section["cycle_rows"][0]["components"]["asof"] in text


def component_values_fixture(score, weight, *, zero_inflation=False, empty_axes=()):
    from lib.intl_workspace_macro import build_macro_section
    supplied = components()
    supplied["growth"] = [{"key": "gdp_trend", "score": score, "weight": weight}]
    supplied["inflation"] = [{"key": "cpi_direction", "score": score, "weight": weight}]
    if zero_inflation:
        supplied["inflation"][0].update(score=0, weight=0)
    for axis in ("growth", "inflation"):
        if axis in empty_axes:
            supplied[axis] = []
        supplied[f"{axis}_score"] = supplied[axis][0]["score"] if supplied[axis] else None
        supplied[f"{axis}_n_components"] = int(bool(supplied[axis]) and supplied[axis][0]["score"] is not None)
    packet = inputs(measures={}, cycle_evidence={"EZ": cycle(
        method_kind="mixed_composite", economic_support=None, components=supplied,
    )})
    return build_macro_section(**packet), packet["registry"]


@pytest.mark.parametrize("axis_index", [0, 1])
@pytest.mark.parametrize("score,weight", [(None, None), (0, 0), (-1.0, 0.75), (None, 1.0)])
def test_component_readings_distinguish_missing_from_zero(axis_index, score, weight):
    section, registry = component_values_fixture(score, weight)
    before = copy.deepcopy(section)
    soup = BeautifulSoup(render(section, registry), "html.parser")
    for translation in soup.select(".l-zh"):
        translation.decompose()
    reading = soup.select(".intl-macro__composite dd")[axis_index].get_text(" ", strip=True)
    assert "None" not in reading
    expected_score = "Not supplied" if score is None else str(score)
    expected_weight = "Not supplied" if weight is None else str(weight)
    assert re.search(r"Score\s*:\s*" + re.escape(expected_score) + r"(?:\s|$)", reading)
    assert re.search(r"Weight\s*:\s*" + re.escape(expected_weight) + r"(?:\s|$)", reading)
    assert section == before


@pytest.mark.parametrize("empty_axes", [("growth",), ("inflation",), ("growth", "inflation")])
def test_empty_component_axes_are_explicit_without_erasing_supplied_zero(empty_axes):
    section, registry = component_values_fixture(0, 0, empty_axes=empty_axes)
    before = copy.deepcopy(section)
    composite = BeautifulSoup(render(section, registry), "html.parser").select_one(".intl-macro__composite")
    readings = composite.select("dd")
    for axis, reading in zip(("growth", "inflation"), readings[:2], strict=True):
        text = reading.get_text(" ", strip=True)
        if axis in empty_axes:
            assert text == "No components supplied. 未提供分项。"
        else:
            assert "No components supplied" not in text
            assert re.search(r"Score:\s*评分：\s*0", text)
            assert re.search(r"Weight:\s*权重：\s*0", text)
    assert readings[2].get_text(strip=True) == before["cycle_rows"][0]["components"]["asof"]
    assert composite.select_one("[data-im-macro-components-unavailable]") is None
    assert section == before


def component_workspace_fixture(*, missing_components=False, empty_axes=()):
    """Native mount and full page with explicitly synthetic component inputs."""
    from uuid import uuid4
    from engine.intl_inputs import countries
    from engine.intl_workspace_overview import build_workspace_overviews
    from lib.intl_macro_mount import attach_macros
    from tests.test_intl_workspace_integration import render_fixture
    workspace = build_workspace_overviews(
        None, workspace_generation=f"im-workspace-generation:{uuid4()}",
    )
    registry = {
        "markets": [{"market_id": key, "name_en": row["name"], "name_zh": row["name_zh"]}
                    for key, row in countries().items()],
        "horizons": workspace["config"]["horizons"],
        "bases": workspace["config"]["bases"],
    }
    supplied = components()
    supplied.update(growth=[{"key": "gdp_trend", "score": None, "weight": None}],
                    inflation=[{"key": "cpi_direction", "score": 0, "weight": 0}],
                    growth_score=None, growth_n_components=0,
                    inflation_score=0, inflation_n_components=1)
    for axis in empty_axes:
        supplied[axis] = []
        supplied[f"{axis}_score"] = None
        supplied[f"{axis}_n_components"] = 0
    evidence = cycle(method_kind="mixed_composite", economic_support=None,
                     components=supplied, method_ref="synthetic:component-reading")
    if missing_components:
        evidence.update(quality="stale", reason="source_stale", components=None,
                        method_ref=None, asof=None)
    workspace = attach_macros(workspace, registry=registry, measures={},
                              cycle_evidence={"EZ": evidence}, destinations={})
    workspace["macro_registry"] = registry
    return render_fixture(workspace_payload=workspace)


def test_actual_projection_positive_zero_stale_and_denied_render():
    macro_section, registry = build_fixture()
    html = render(macro_section, registry)

    assert "2.5" in html
    assert 'data-im-macro-value>0<' in html
    assert "1.25" in html and "2025-01-31" in html
    assert "Value withheld" in html
    assert "Metadata withheld" in html
    assert "Not supplied" in html
    assert "欧元区 &amp; 欧洲央行" in html
    assert 'gdp&lt;&#34;&gt;&amp;report' in html
    assert "https://example.invalid/cpi?x=1&amp;y=&lt;script&gt;" in html
    assert "<script>" not in html


def test_semantic_panel_table_roster_reads_and_native_evidence():
    macro_section, registry = build_fixture()
    html = render(macro_section, registry)
    collector = collect(html)
    panel = next(values for tag, values in collector.tags if tag == "section")

    assert "data-im-panel" in panel
    assert panel["data-view"] == "macro"
    assert panel["data-horizon"] == "1y"
    assert panel["data-basis"] == "local"
    assert panel["data-return-basis"] == "price"
    assert panel["data-source"] == ""
    assert panel["data-im-generation"] == "macro-v2"
    assert panel["id"] == "intl-macro-one-macro"
    assert html.count('<tr class="intl-macro__market"') == 3
    assert '<caption id="intl-macro-one-table-caption"' in html
    assert html.count('scope="col"') == 7
    assert html.count('scope="row"') == 3
    assert 'data-im-action="select_market"' in html
    assert '<option value=""' in html
    assert '<option value="EZ"' in html
    assert '<option value="JP"' in html
    assert '<option value="GB"' in html
    assert 'data-im-action="set_view" data-im-view="overview"' in html
    assert html.count('<summary class="intl-macro__evidence-summary">') >= 4
    assert "Economic evidence" in html and "经济依据" in html
    assert "Realized policy" in html and "已公布政策利率" in html
    assert "Market context" in html and "市场背景" in html
    assert "mixed_composite" in html and "owner/mixed@7" in html
    assert "Goldilocks" not in html and "Q1" not in html


def test_table_option_markup_and_header_associations_use_safe_row_indexes():
    macro_section, registry = build_fixture()
    hostile_registry = copy.deepcopy(registry)
    hostile_registry["markets"][0]["name_en"] = 'Euro Area <span="hostile">'
    hostile_registry["markets"][0]["name_zh"] = "欧元区 <b> hostile </b>"
    hostile_registry["markets"][0]["market_id"] = 'EZ" onmouseover="hostile'
    macro_section["market_rows"][0]["market_id"] = 'EZ" onmouseover="hostile'
    html = render(macro_section, hostile_registry)
    collector = collect(html)

    assert '<option><span' not in html
    option = next(attrs for tag, attrs in collector.tags if tag == "option" and attrs.get("value", "").startswith("EZ"))
    assert "onmouseover" not in option
    assert option["value"] == 'EZ" onmouseover="hostile'
    assert 'Euro Area &lt;span=&#34;hostile&#34;&gt; / 欧元区 &lt;b&gt; hostile &lt;/b&gt;</option>' in html
    for row_index in range(1, len(macro_section["market_rows"]) + 1):
        for field_key in (
            "gdp_yoy", "cpi_yoy", "policy_rate", "policy_proxy",
            "yield_10y", "yield_change",
        ):
            slot_id = f"intl-macro-one-row-{row_index}-{field_key}"
            assert slot_id in collector.ids
    referenced_ids = {
        header_id
        for tag, attrs in collector.tags
        if tag in {"td", "th"} and "headers" in attrs
        for header_id in attrs["headers"].split()
    }
    assert referenced_ids <= set(collector.ids)
    assert not any('onmouseover="hostile"' in id_value for id_value in collector.ids)


def test_exact_source_notice_and_no_dynamic_source_href():
    macro_section, registry = build_fixture()
    html = render(macro_section, registry)
    collector = collect(html)

    assert "Source: European Central Bank (ECB)." in html
    assert "available free of charge at the source" in html
    assert "来源：欧洲中央银行（ECB）" in html
    assert collector.hrefs == [
        "https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV",
        "/research/economic",
    ]
    assert "ECB FM.D.U2.EUR.4F.KR.DFR.LEV &amp; provenance" in html


def test_missing_or_unmatched_notice_reports_boundary_without_link():
    macro_section, registry = build_fixture()

    missing = render(macro_section, registry, source_notice=None)
    unsafe = render(
        macro_section,
        registry,
        source_notice={**SOURCE_NOTICE, "origin_url": "https://evil.invalid/ecb"},
    )
    mismatched = render(
        macro_section,
        registry,
        source_notice={**SOURCE_NOTICE, "instrument_id": "marginal_lending"},
    )

    for html in (missing, unsafe, mismatched):
        assert "Source link unavailable" in html
        assert "来源链接暂无可用" in html
        assert "available free of charge" not in html
        assert "data.ecb.europa.eu" not in html


def test_denied_metadata_slot_leaks_no_private_projection_values():
    macro_section, registry = build_fixture()
    html = render(macro_section, registry)
    denied_cell = html.split('data-im-macro-market="GB"', 1)[1].split("</tr>", 1)[0]

    assert "policy_rate" in denied_cell
    assert "Metadata withheld" in denied_cell
    assert "secret-proxy" not in denied_cell
    assert "secret proxy source" not in denied_cell
    assert "2026-01-01" not in denied_cell
    assert "<details" not in denied_cell.split("<td", 2)[1]


def test_repeated_contexts_have_unique_ids_and_context_does_not_recompute_periods():
    first, registry = build_fixture()
    second = copy.deepcopy(first)
    combined = render(first, registry, context_id="panel-one") + render(
        second,
        registry,
        context_id="panel-two",
        panel_context={
            "horizon": "1y",
            "currency_basis": "usd_unhedged",
            "return_basis": "price",
        },
    )
    ids = collect(combined).ids

    assert len(ids) == len(set(ids))
    assert combined.count("2026-10-06") >= 2
    assert combined.count('data-basis="usd_unhedged"') == 1


def test_research_none_has_no_dead_link_and_css_is_scoped_frozen_design():
    macro_section, registry = build_fixture()
    html = render(macro_section, registry)
    css = Path(__file__).resolve().parents[1].joinpath("templates/intl_workspace_macro.css").read_text(encoding="utf-8")

    assert "Market response" in html
    market_response = html.split('class="intl-macro__research-item"', 2)[2]
    assert "<a " not in market_response
    assert "Not available" in market_response
    for token in (
        "--panel", "--panel2", "--text", "--muted", "--line", "--link",
        "--card-shadow", "--font-ui", "--fs-body", "--fs-h2", "--fs-sm",
        "--fs-num-lg", "--r-card", "--r-ctl",
    ):
        assert token in css
    assert '[data-theme="light"] .intl-macro' in css
    assert '@media (max-width: 768px)' in css
    assert '.intl-macro[data-im-macro-has-selection="true"] .intl-macro__market[data-im-macro-selected="false"]' in css
    assert "animation" not in css.lower()
    assert not re.search(r'(^|\})\s*(html|body|[.#*][^,{]*macro[^,{]*zoom)\s*[,{]', css)


def test_source_notice_stays_with_qualified_or_stale_policy_and_visible_date():
    for quality in ['qualified', 'stale']:
        section, registry = build_fixture()
        policy = section['market_rows'][0]['policy_rate']
        policy['quality'] = quality
        policy['reason'] = None if quality == 'qualified' else 'source_stale'
        html = render(section, registry)
        cell = html.split('id="intl-macro-one-row-1-policy_rate"', 1)[1].split('</td>', 1)[0]
        assert 'https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV' in cell
        assert 'available free of charge' in cell
        before_details = cell.split('<details', 1)[0]
        assert '2026-10-06' in before_details
        if quality == 'stale': assert 'Stale data' in before_details


def test_notice_closed_shape_and_optional_generation():
    section, registry = build_fixture()
    html = render(section, registry, generation=None, source_notice={**SOURCE_NOTICE, 'extra': True})
    assert 'data-im-generation' not in html
    assert 'available free of charge' not in html
    assert 'https://data.ecb.europa.eu/data/datasets/' not in html


def test_no_euro_area_promise_without_euro_area_and_language_wrappers():
    section, registry = build_fixture()
    section['market_rows'] = section['market_rows'][1:]
    section['cycle_rows'] = []
    registry['markets'] = registry['markets'][1:]
    html = render(section, registry)
    assert 'The Euro Area deposit facility row is shown' not in html
    assert '<strong>GDP YoY</strong>' not in html
    assert '<span class="l-en">GDP YoY</span>' in html


def test_context_and_option_copy_localize_without_exposing_internal_basis_names():
    section, registry = build_fixture()
    for basis, english, chinese in [("local", "Local currency", "本币"),
                                     ("usd_unhedged", "USD · Unhedged", "美元 · 未对冲")]:
        html = render(section, registry, panel_context={"horizon": "1y", "currency_basis": basis, "return_basis": "price"})
        context = html.split('class="intl-macro__context"', 1)[1].split('</div>', 1)[0]
        assert english in context and chinese in context
        assert "Price return" in context and "价格回报" in context
        assert "usd_unhedged" not in context
        options = [attrs for tag, attrs in collect(html).tags if tag == "option"]
        assert options[0]["data-im-label-en"] == "All markets"
        assert options[0]["data-im-label-zh"] == "全部市场"
        assert "data-im-label-en" in options[1] and "data-im-label-zh" in options[1]
        assert 'data-im-label-en="Euro Area <span' not in html
