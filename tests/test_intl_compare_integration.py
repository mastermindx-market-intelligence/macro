"""Real owner projections compose Compare with the incumbent Library/Inspector."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from lib import intl_library_mount as mount

_spec = importlib.util.spec_from_file_location(
    'compare_integration_fixture', Path(__file__).with_name('test_intl_inspector_mount.py'))
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)
supplied = _fixture.supplied
Document = _fixture.Document
ActualShell = _fixture.ActualShell
workspace = _fixture.workspace
CATALOGUE = json.loads((Path(__file__).resolve().parents[1] / 'config/intl_library_catalogue.json').read_text())


def test_real_composition_preserves_all_views_and_stock_bytes(supplied):
    ws = workspace(supplied[0]); before = deepcopy(ws)
    macro, stocks = mount.render_international_pages(ActualShell(), {'intl_workspace': ws}, catalogue=CATALOGUE)
    doc = Document(macro)
    assert stocks == 'Incumbent stocks' and ws == before
    assert len(doc.with_attr('data-im-compare-panel')) == 2
    assert len(doc.with_attr('data-im-inspector-payload')) == 4
    assert len(doc.with_attr('data-im-library-static')) == 1
    assert len(doc.with_attr('data-im-compare-slot')) == 4
    ids = [a['id'] for _, a in doc.nodes if 'id' in a]
    assert len(ids) == len(set(ids))
    compare = [a for _, a in doc.nodes if a.get('data-im-view') == 'compare' or a.get('value') == 'compare']
    assert len(compare) == 2 and all('disabled' not in a for a in compare)


@pytest.mark.parametrize('error', [ValueError, KeyError, TypeError])
def test_compare_failure_keeps_library_inspector_and_overview(supplied, monkeypatch, error):
    def fail(_): raise error('synthetic failure')
    monkeypatch.setattr(mount, 'attach_compares', fail)
    macro, stocks = mount.render_international_pages(ActualShell(), {'intl_workspace': workspace(supplied[0])}, catalogue=CATALOGUE)
    doc = Document(macro)
    assert stocks == 'Incumbent stocks'
    assert not doc.with_attr('data-im-compare-panel')
    assert len(doc.with_attr('data-im-inspector-payload')) == 4
    assert len(doc.with_attr('data-im-library-static')) == 1
    assert all('disabled' in a for _, a in doc.nodes if a.get('data-im-view') == 'compare')


def test_inspector_failure_keeps_valid_compare_and_library(supplied, monkeypatch):
    def fail(*args, **kwargs): raise ValueError('synthetic failure')
    monkeypatch.setattr(mount, 'attach_inspectors', fail)
    macro, _ = mount.render_international_pages(ActualShell(), {'intl_workspace': workspace(supplied[0])}, catalogue=CATALOGUE)
    doc = Document(macro)
    assert len(doc.with_attr('data-im-compare-panel')) == 2
    assert len(doc.with_attr('data-im-library-static')) == 1
    assert not doc.with_attr('data-im-inspector-payload')


def test_picker_contains_only_public_slots_and_is_native_hidden(supplied):
    def deny(receipts):
        for receipt in receipts:
            if receipt['binding']['market_id'] == 'JP': receipt['disclosure']['metadata'] = 'denied'
    macro, _ = mount.render_international_pages(ActualShell(), {'intl_workspace': workspace(supplied[0], edit=deny)})
    doc = Document(macro)
    assert len(doc.with_attr('data-im-compare-controls')) == 2
    assert all('hidden' in a for _, a in doc.with_attr('data-im-compare-controls'))
    # Public option labels are the only identity introduced by the picker.
    options = [a for tag, a in doc.nodes if tag == 'option' and a.get('value') in ('0', '1')]
    assert len(options) == 2 and all(a['value'] == '1' for a in options)
    assert all(a.get('data-im-label-en') and a.get('data-im-label-zh') for a in options)
