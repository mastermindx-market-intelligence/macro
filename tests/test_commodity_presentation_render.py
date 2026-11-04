"""The presentation renderer must preserve the published data and its siblings."""
import json
from unittest.mock import patch

import pytest

from scripts import render_commodity_workspace_review as renderer


@pytest.fixture
def publication(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "commodity-workspace.css").write_text(".cw { padding: 24px; }")
    (templates / "commodity-workspace.js").write_text("window.newWorkspace = true;")
    (templates / "_commodity_decision_workspace.html.j2").write_text(
        '<section id="commodity-workspace"><section><h2>New composition</h2></section>'
        '<script id="cw-data" type="application/json">{{ commodity_workspace|tojson }}</script></section>'
    )
    data = {"as_of":"2026-10-21", "fingerprint":"preserved", "assets":[], "chains":[], "unavailable":None, "zero":0}
    payload = json.dumps(data, sort_keys=True)
    legacy = '<details id="commodity-advanced"><section>Accepted legacy</section><script>const text="</section>";</script></details>'
    html = ('<head><link rel="stylesheet" href="theme.css?v=aaa">'
            '<link rel="stylesheet" href="assets/css/old.css?v=old"></head><body>'
            '<section id="commodity-workspace"><section>Old</section>'
            '<script id="cw-data" type="application/json">'+payload+'</script></section>'
            +legacy+'<script>window.oldWorkspace = true;</script>'
            '<script>window.sharedOwner = true;</script></body>')
    files = {"site/commodities.html":html, "templates/commodity-workspace.js":"window.oldWorkspace = true;",
             "templates/commodity-workspace.css":".cw { padding: 0; }", "site/assets/css/old.css":".cw { padding: 0; }",
             "site/theme.css":":root { --line: gray; }"}
    return tmp_path, files, payload, legacy


def render(publication):
    root, files, *_ = publication
    with patch.object(renderer, "ROOT", root), patch.object(renderer, "git_bytes", side_effect=lambda base, path: files[path].encode()):
        return renderer.render_published_workspace("a" * 40)


def test_recompose_keeps_exact_payload_legacy_and_other_owners(publication):
    _, _, payload, legacy = publication
    html, receipt, _ = render(publication)
    assert payload in html
    assert legacy in html
    assert '<link rel="stylesheet" href="theme.css?v=aaa">' in html
    assert '<script>window.sharedOwner = true;</script>' in html
    assert "window.oldWorkspace" not in html
    assert "window.newWorkspace = true;" in html
    assert html.count('id="commodity-workspace"') == 1
    assert receipt["payload_bytes_unchanged"] is True
    assert receipt["economic_recomputation"] is False
    assert receipt["production_acceptance"] is False


def test_duplicate_consumer_script_fails_closed(publication):
    files = publication[1]
    files["site/commodities.html"] += '<script>window.oldWorkspace = true;</script>'
    with pytest.raises(ValueError, match="script binding"):
        render(publication)


def test_template_data_change_fails_closed(publication):
    template = publication[0] / "templates/_commodity_decision_workspace.html.j2"
    template.write_text(template.read_text().replace("commodity_workspace|tojson", "{}|tojson"))
    with pytest.raises(ValueError, match="payload bytes"):
        render(publication)


def company_journey_component(workspace, *, linked=True):
    """Render a test-owned identity fixture through the real production component.

    Published data may legitimately have no active equity cohorts. Navigation
    coverage must not require manufacturing one in the production publication.
    """
    from copy import deepcopy
    from datetime import date
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    from engine.commodity_decision_workspace import fingerprint
    from engine.transmission_company_continuation import ContinuationLink, continuation_for
    from lib.dataos.identity import VendorAliasTable

    fixture = deepcopy(workspace)
    for chain in fixture["chains"]:
        chain["cohorts"] = []
    gold = next(chain for chain in fixture["chains"] if chain["id"] == "real_rate_peak_gold_rerate")
    aliases = VendorAliasTable.from_records([{
        "vendor": "store", "vendor_symbol": "AAPL", "security_id": "SEC:0:AAPL",
        "valid_from": None, "valid_to": None,
    }])
    continuation = continuation_for("AAPL", aliases, date.fromisoformat(gold["as_of"]),
        chain_id=gold["id"], channel_id="test_company_return", chain_asof=gold["as_of"])
    assert isinstance(continuation, ContinuationLink)
    if linked:
        gold["cohorts"] = [{
            "id": "test_company_return", "label": {"en": "Test company", "zh": "测试企业"},
            "note": {"en": "Synthetic navigation fixture", "zh": "合成导航测试"},
            "count": 1, "unevaluable": 0, "ranked": False,
            "companies": {"linked": [continuation.as_dict()], "linked_count": 1},
        }]
    fixture["fingerprint"] = fingerprint({"test_fixture": "company_return_journey", "workspace": fixture})
    env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1] / "templates"),
                      autoescape=True, undefined=StrictUndefined)
    macro = '{% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}'
    component = env.from_string(macro + '{% include "_commodity_decision_workspace.html.j2" %}').render(commodity_workspace=fixture)
    return component, fixture, continuation.href


@pytest.mark.parametrize("linked", [True, False])
def test_real_company_component_positive_and_empty_cohorts(linked):
    from copy import deepcopy
    from html.parser import HTMLParser
    from pathlib import Path
    import re

    html = (Path(__file__).resolve().parents[1] / "site/commodities.html").read_text()
    payloads = re.findall(r'<script\b[^>]*\bid="cw-data"[^>]*>(.*?)</script>', html, re.S)
    assert len(payloads) == 1
    original = json.loads(payloads[0])
    before = deepcopy(original)
    component, fixture, href = company_journey_component(original, linked=linked)
    assert original == before
    assert fixture["assets"] == original["assets"] and fixture["as_of"] == original["as_of"]
    assert fixture["fingerprint"] != original["fingerprint"]

    class Links(HTMLParser):
        def __init__(self):
            super().__init__(); self.rows = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if "data-cw-company-href" in attrs:
                assert tag == "a"
                self.rows.append(attrs)
    parsed = Links(); parsed.feed(component)
    assert [row["data-cw-company-href"] for row in parsed.rows] == ([href] if linked else [])
    for row in parsed.rows:
        assert row["href"] == href and row["target"] == "_blank" and row["rel"] == "noopener"
    rendered = json.loads(re.findall(r'<script\b[^>]*\bid="cw-data"[^>]*>(.*?)</script>', component, re.S)[0])
    assert rendered == fixture


if __name__ == "__main__":
    import sys
    if sys.argv[1:] != ["--company-journey-fixture"]:
        raise SystemExit("expected --company-journey-fixture")
    component, _, _ = company_journey_component(json.load(sys.stdin))
    sys.stdout.write(component)
