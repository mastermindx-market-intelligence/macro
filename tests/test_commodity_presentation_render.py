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
