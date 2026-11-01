"""Actual Overview projections reach the shell without new financial authority."""
from copy import deepcopy
from pathlib import Path
import importlib.util

import jinja2
import pytest

from lib.intl_inspector_mount import attach_inspectors
from lib.intl_library_mount import render_international_pages

_spec = importlib.util.spec_from_file_location('inspector_mount_fixture', Path(__file__).with_name('test_intl_workspace_inspector_render.py'))
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)
supplied = _fixture.supplied
Document = _fixture.Document


def workspace(project, **kwargs):
    panels = [{'context_id': 'context-' + basis,
               'overview': project(basis=basis, **kwargs)}
              for basis in ['local', 'usd_unhedged']]
    return {'config': {'markets': ['JP', 'GB'], 'horizons': ['1m'],
                       'bases': ['local', 'usd_unhedged'], 'default_horizon': '1m',
                       'default_basis': 'usd_unhedged', 'source_reference': panels[0]['overview']['context']['source_reference'],
                       'anchor_ids': ['intl-legacy-research'], 'library_group_ids': []},
            'panels': panels}


class ActualShell:
    """Render the real shell with minimal incumbent destination surroundings."""
    def __init__(self, destinations='<h2 id="lb-board">Incumbent</h2>'):
        self.destinations = destinations
        self.calls = []
        self.template = jinja2.Environment(loader=jinja2.FileSystemLoader(
            Path(__file__).resolve().parents[1] / 'templates'), autoescape=False).get_template('intl_workspace/shell.html.j2')

    def render(self, **vm):
        self.calls.append(vm)
        if vm['mode'] == 'stocks':
            return 'Incumbent stocks'
        return self.template.render(**vm, t=lambda en, zh: f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>') + self.destinations


def test_all_contexts_keep_exact_owner_values_and_detached_input(supplied):
    ws = workspace(supplied[0]); before = deepcopy(ws)
    result = attach_inspectors(ws)
    assert ws == before and result['panels'] == before['panels']
    assert len(result['inspectors']) == 4
    for p in result['inspectors']:
        row = next(x for x in ws['panels'] if x['context_id'] == p['context_id'])
        source = next(x for x in row['overview']['rows'] if x['market_id'] == p['binding']['market_id'])
        assert all(p['inspector']['metrics'][k] == source[k] for k in ('local', 'usd', 'fx_contribution'))
        assert p['binding']['currency_basis'] == row['overview']['context']['currency_basis']
    result['inspectors'][0]['inspector']['market']['name_en'] = 'edited'
    assert ws == before


def test_denied_rows_have_no_inspector_or_identifier(supplied):
    def deny(receipts):
        for r in receipts:
            if r['binding']['market_id'] == 'JP':
                r['disclosure']['metadata'] = 'denied'
    result = attach_inspectors(workspace(supplied[0], edit=deny))
    assert len(result['inspectors']) == 2
    assert all(p['binding']['market_id'] == 'GB' for p in result['inspectors'])


def test_unknown_market_does_not_borrow_other_markets_source(supplied):
    result = attach_inspectors(workspace(supplied[0], edit=lambda rs: rs.__setitem__(slice(None), [r for r in rs if r['binding']['market_id'] == 'GB'])))
    jp = next(p['inspector'] for p in result['inspectors'] if p['binding']['market_id'] == 'JP')
    assert jp['context']['source_reference'] is None
    assert jp['market']['index_label'] is None
    assert all(jp['metrics'][k]['value'] is None for k in ('local', 'usd', 'fx_contribution', 'selected'))


@pytest.mark.parametrize('identifier', ['context-local', 'unsafe id', '', '<unsafe>'])
def test_ambiguous_or_unsafe_context_rejected_atomically(supplied, identifier):
    ws = workspace(supplied[0]); ws['panels'][1]['context_id'] = identifier
    before = deepcopy(ws)
    with pytest.raises(ValueError):
        attach_inspectors(ws)
    assert ws == before


def test_real_shell_one_dialog_unique_ids_and_exact_binding(supplied):
    ws = workspace(supplied[0]); before = deepcopy(ws)
    template = ActualShell()
    macro, stocks = render_international_pages(template, {'intl_workspace': ws})
    doc = Document(macro)
    assert stocks == 'Incumbent stocks' and ws == before
    assert len(doc.with_attr('data-im-inspector-shell')) == 1
    assert len(doc.with_attr('data-im-inspector-payload')) == 4
    ids = [a['id'] for _, a in doc.nodes if 'id' in a]
    assert len(ids) == len(set(ids))
    links = [a.get('href') for tag, a in doc.nodes if tag == 'a']
    assert '/intl.html#lb-board' in links and '/intl_stocks.html' in links
    assert not any('country=' in link for link in links if link)
    assert 'Nikkei 225' in macro and 'TOPIX' not in macro


@pytest.mark.parametrize('destinations', ['', '<!-- <h2 id="lb-board">text</h2> -->', '<h2 id="lb-board"></h2><h2 id="lb-board"></h2>'])
def test_missing_or_ambiguous_destination_never_advertised(supplied, destinations):
    macro, _ = render_international_pages(ActualShell(destinations), {'intl_workspace': workspace(supplied[0])})
    assert 'href="/intl.html#lb-board"' not in macro
    assert 'href="/intl_stocks.html"' in macro


def test_invalid_inspector_preserves_complete_incumbent_render(supplied):
    ws = workspace(supplied[0]); ws['panels'][1]['context_id'] = 'bad id'
    template = ActualShell(); expected = template.render(intl_workspace=ws, mode='macro')
    macro, stocks = render_international_pages(template, {'intl_workspace': ws})
    assert macro == expected and stocks == 'Incumbent stocks'
    assert 'data-im-inspector-payload' not in macro


def test_library_failure_does_not_disable_valid_inspectors(supplied):
    macro, _ = render_international_pages(ActualShell(), {'intl_workspace': workspace(supplied[0])}, catalogue={})
    assert len(Document(macro).with_attr('data-im-inspector-payload')) == 4


def test_no_workspace_does_not_create_one():
    assert attach_inspectors(None) is None
