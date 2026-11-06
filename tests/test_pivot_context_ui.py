"""Escaping and source-isolation checks for the incumbent QA evidence detail."""
import json
from pathlib import Path
import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
from scripts import build_qa_bottom_sensors as qa

ROOT = Path(__file__).resolve().parents[1]


def context(quality="partial"):
    return {"schema": "bottom_pivot_context.v1", "symbol": "ABC", "quality": quality,
        "decision_at": "2026-11-05T22:00:00Z", "is_display_only": True, "probability": None,
        "explanation": {"en": "Daily evidence only <script>alert(1)</script>",
                        "zh": "\u4ec5\u65e5\u7ebf\u8bc1\u636e <script>alert(1)</script>"}}


def row(ctx=None):
    return {"symbol":"ABC", "bottom_state":"WATCH", "coiled":False, "star":False,
            "pivot_context":ctx}


def render(ctx=None):
    env=Environment(loader=ChoiceLoader([DictLoader({"_site_nav.html.j2":""}),
        FileSystemLoader(str(ROOT/"templates"))]),autoescape=False)
    return env.get_template(qa.TEMPLATE_NAME).render(rows=[row(ctx)], n_rows=1,
        state_counts={"WATCH":1}, overlay_counts={}, as_of="2026-11-05",
        computed_at="2026-11-05",labels_version="labels_v2",
        sponsorship_populated=0,sponsorship_unavailable=1)


@pytest.mark.parametrize("quality", ["available","partial","unavailable"])
def test_escaped_bilingual_context(quality):
    html=render(context(quality))
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
    assert 'data-pivot-symbol="ABC"' in html
    assert 'not a live entry signal' in html
    assert 'A moving-average reclaim is not required' in html
    assert 'summary:focus-visible' in html
    assert '<details class="pivot-detail"' in html


def test_legacy_payload_degrades_without_fabricated_evidence():
    html=render()
    assert 'Not captured' in html
    assert 'data-pivot-symbol=' not in html


def test_wrong_schema_not_rendered():
    ctx=context();ctx['schema']='wrong'
    assert 'data-pivot-symbol=' not in render(ctx)


def test_explicit_root_never_writes_configured_site(tmp_path, monkeypatch):
    (tmp_path/'templates').mkdir()
    (tmp_path/'templates'/'qa_bottom_sensors.html.j2').write_text('{{ rows[0].pivot_context.quality }}')
    p=tmp_path/'site/neuralwebdata';p.mkdir(parents=True)
    r=row();r['pivot_context_json']=json.dumps(context())
    (p/'bottom_sensors.json').write_text(json.dumps({'rows':[r],'n_rows':1}))
    forbidden=tmp_path/'forbidden'
    monkeypatch.setattr(qa,'_site_dir',lambda:forbidden)
    monkeypatch.setattr(qa,'write_page',lambda path,html:path.write_text(html))
    out=qa.build(tmp_path)
    assert out == tmp_path/'site/qa_bottom_sensors.html'
    assert out.read_text()=='partial'
    assert not forbidden.exists()


def test_corrupt_parquet_context_has_no_crash(tmp_path,monkeypatch):
    (tmp_path/'templates').mkdir()
    (tmp_path/'templates'/'qa_bottom_sensors.html.j2').write_text('{{ rows[0].pivot_context is none }}')
    r=row();r['pivot_context_json']='{broken'
    monkeypatch.setattr(qa,'_load_payload',lambda root:{'rows':[r]})
    monkeypatch.setattr(qa,'write_page',lambda path,html:path.write_text(html))
    assert qa.build(tmp_path).read_text()=='True'


def test_non_sortable_evidence_heading_does_not_break_existing_sort_controls():
    html=render(context())
    assert "var indicator = th.querySelector('.sort-ind');" in html
    assert "if(indicator) indicator.textContent" in html


def test_native_select_labels_are_one_language_not_invalid_nested_spans():
    html=render(context())
    assert 'data-label-en="All states"' in html
    assert '<option value=""><span' not in html
    assert 'Source notes and limits' in html
