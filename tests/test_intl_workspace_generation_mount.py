"""Generation binding for actual owner publications without financial changes."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import uuid

import pytest

from lib.intl_compare_mount import attach_compares
from lib.intl_inspector_mount import attach_inspectors
from lib.intl_library_mount import attach_public_library, render_international_pages


_spec = importlib.util.spec_from_file_location(
    'generation_owner_fixture', Path(__file__).with_name('test_intl_compare_mount.py'))
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)

_render_spec = importlib.util.spec_from_file_location(
    'generation_shell_fixture', Path(__file__).with_name('test_intl_inspector_mount.py'))
_render_fixture = importlib.util.module_from_spec(_render_spec)
_render_spec.loader.exec_module(_render_fixture)

_owner_spec = importlib.util.spec_from_file_location(
    'actual_workspace_owner_fixture', Path(__file__).with_name('test_intl_workspace_overview.py'))
_owner_fixture = importlib.util.module_from_spec(_owner_spec)
_owner_spec.loader.exec_module(_owner_fixture)

Document = _render_fixture.Document
ActualShell = _render_fixture.ActualShell
CATALOGUE = json.loads((Path(__file__).resolve().parents[1] /
                        'config/intl_library_catalogue.json').read_text())
GENERATION_UUID = '9e1a5667-47f3-4a69-a784-b971e3ba74ba'
SECOND_GENERATION_UUID = '018f1d99-7b26-4d69-a509-77f1ffca929f'
GENERATION_REFERENCE = 'im-workspace-generation:' + GENERATION_UUID


def versioned(generation=GENERATION_REFERENCE, version=2,
              source='synthetic:inspector-source', **kwargs):
    workspace = _fixture.workspace(**kwargs)
    workspace['config']['source_reference'] = generation if version == 2 else source
    workspace['binding_version'] = version
    if version == 2:
        for panel in workspace['panels']:
            panel['generation'] = generation
    return workspace


def rendered(workspace):
    return render_international_pages(
        ActualShell(), {'intl_workspace': workspace}, catalogue=CATALOGUE)


def actual_production_workspace():
    frame, inputs, _ = _owner_fixture._production_fixture()
    return _owner_fixture._production_workspace(frame, inputs)


def attach_all(workspace, macro_html):
    return attach_compares(attach_inspectors(attach_public_library(
        workspace, catalogue=CATALOGUE, macro_html=macro_html, stocks_rendered=True)))


def test_actual_backend_contract_supersedes_rejected_r1_fixture():
    workspace = actual_production_workspace()
    before = deepcopy(workspace)
    assert workspace['binding_version'] == 2
    assert 'generation' not in workspace
    assert workspace['config']['source_reference'] == GENERATION_REFERENCE
    assert all(panel['generation'] == GENERATION_REFERENCE for panel in workspace['panels'])
    macro, stocks = rendered(workspace)
    result = attach_all(workspace, macro)
    assert [item['generation'] for item in result['compares']] == [
        GENERATION_REFERENCE] * len(workspace['panels'])
    assert {item['generation'] for item in result['inspectors']} == {GENERATION_REFERENCE}
    assert result['library']['context']['source_reference'] is None
    assert 'library_generation' not in result['library']
    assert result['library_generation'] == GENERATION_REFERENCE
    assert workspace == before
    doc = Document(macro)
    assert all(attrs['data-im-generation'] == GENERATION_REFERENCE
               for _, attrs in doc.with_attr('data-im-generation'))
    assert stocks == 'Incumbent stocks'


@pytest.mark.parametrize('shape', [
    [], {'binding_version': 2}, {'config': []}, {'panels': []},
])
def test_malformed_envelopes_are_rejected_structurally_by_every_mount(shape):
    for attach in (attach_compares, attach_inspectors,
                   lambda value: attach_public_library(
                       value, catalogue=CATALOGUE, macro_html='', stocks_rendered=True)):
        with pytest.raises((ValueError, TypeError)):
            attach(shape)


def test_v2_binding_composes_all_mounts_and_actual_shell():
    workspace = versioned()
    before = deepcopy(workspace)
    macro, stocks = rendered(workspace)
    result = attach_all(workspace, macro)
    doc = Document(macro)
    assert doc.with_attr('data-im-workspace')[0][1]['data-im-binding-version'] == '2'
    assert [item['generation'] for item in result['compares']] == [GENERATION_REFERENCE] * 4
    assert {item['generation'] for item in result['inspectors']} == {GENERATION_REFERENCE}
    assert result['library_generation'] == GENERATION_REFERENCE
    assert {attrs['data-source'] for _, attrs in doc.with_attr('data-im-compare-panel')} == {
        'synthetic:inspector-source'}
    assert all(attrs['data-im-generation'] == GENERATION_REFERENCE
               for _, attrs in doc.with_attr('data-im-generation'))
    assert workspace == before and stocks == 'Incumbent stocks'


def test_v2_local_qualified_usd_null_and_other_horizon_null():
    compared = attach_compares(actual_production_workspace())
    contexts = [item['compare_catalogue']['context'] for item in compared['compares']]
    local_sources = {context['source_reference'] for context in contexts
                     if context['currency_basis'] == 'local'}
    usd_sources = {context['source_reference'] for context in contexts
                   if context['currency_basis'] == 'usd_unhedged'}
    assert local_sources and None not in local_sources
    assert local_sources != usd_sources and None in usd_sources
    other_horizon = next(context for context in contexts
                         if context['horizon'] == '3m'
                         and context['currency_basis'] == 'usd_unhedged')
    assert other_horizon['source_reference'] is None


def test_v2_metadata_value_denied_unknown_and_nullable_inspector_states():
    def deny(receipts, field):
        for receipt in receipts:
            if receipt['binding']['market_id'] == 'JP':
                receipt['disclosure'][field] = 'denied'

    def unknown(receipts):
        receipts[:] = [receipt for receipt in receipts
                       if receipt['binding']['market_id'] == 'GB']

    metadata_denied = attach_inspectors(versioned(edit=lambda value: deny(value, 'metadata')))
    value_denied = attach_inspectors(versioned(edit=lambda value: deny(value, 'value')))
    unknown = attach_inspectors(versioned(edit=unknown))
    assert all(item['binding']['market_id'] == 'GB' for item in metadata_denied['inspectors'])
    assert all(item['inspector']['status'] in {'partial', 'unavailable'}
               for item in value_denied['inspectors']
               if item['binding']['market_id'] == 'JP')
    for denied in (metadata_denied, value_denied):
        assert all(item['generation'] == GENERATION_REFERENCE
                   for item in denied['inspectors'])
        assert next(item['inspector']['context']['source_reference']
                    for item in denied['inspectors']
                    if item['binding']['market_id'] == 'GB') == 'synthetic:inspector-source'
    nullable = [item for item in unknown['inspectors']
                if item['binding']['market_id'] == 'JP']
    assert {item['generation'] for item in nullable} == {GENERATION_REFERENCE}
    assert nullable[0]['inspector']['context']['source_reference'] is None


def test_v2_generation_change_survives_same_financial_source():
    first = attach_compares(versioned())
    second = attach_compares(versioned(
        'im-workspace-generation:' + SECOND_GENERATION_UUID))
    assert first['compares'][0]['generation'] != second['compares'][0]['generation']
    first_source = first['compares'][0]['compare_catalogue']['context']['source_reference']
    second_source = second['compares'][0]['compare_catalogue']['context']['source_reference']
    assert first_source == second_source == 'synthetic:inspector-source'


@pytest.mark.parametrize('version', [1, 2, '1', '2', 3, True, False, None], ids=[
    'one', 'two', 'string-one', 'string-two', 'unknown', 'true', 'false', 'explicit-null'])
def test_binding_version_has_exact_integer_semantics(version):
    workspace = versioned(version=version)
    expected = type(version) is int and version in (1, 2)
    mounts = (attach_compares, attach_inspectors,
              lambda value: attach_public_library(
                  value, catalogue=CATALOGUE, macro_html='', stocks_rendered=True))
    for attach in mounts:
        if expected:
            assert attach(workspace) is not None
        else:
            with pytest.raises(ValueError):
                attach(workspace)


@pytest.mark.parametrize('generation', [
    None, 'im-workspace-generation:' + SECOND_GENERATION_UUID,
    GENERATION_REFERENCE.upper(),
    'im-workspace-generation:' + str(uuid.uuid5(uuid.NAMESPACE_DNS, 'x')),
    'not-a-uuid', '', 2,
], ids=['missing', 'mismatch', 'noncanonical-upper', 'wrong-v4-version',
        'noncanonical-text', 'empty', 'numeric'])
def test_v2_sidecars_are_validated_atomically(generation):
    workspace = versioned()
    workspace['panels'][1]['generation'] = generation
    before = deepcopy(workspace)
    with pytest.raises(ValueError):
        attach_compares(workspace)
    assert workspace == before


@pytest.mark.parametrize('generation', [
    None, '', 'synthetic:inspector-source',
    'im-workspace-generation:' + GENERATION_UUID.upper(),
    'im-workspace-generation:' + str(uuid.uuid5(uuid.NAMESPACE_DNS, 'x')),
    'im-workspace-generation:', 2,
], ids=['missing', 'empty', 'wrong-prefix', 'noncanonical-upper', 'wrong-v4-version',
        'empty-uuid', 'numeric'])
def test_v2_root_generation_is_validated_before_copy(generation):
    workspace = versioned()
    workspace['config']['source_reference'] = generation
    before = deepcopy(workspace)
    with pytest.raises(ValueError):
        attach_compares(workspace)
    assert workspace == before


@pytest.mark.parametrize('mutation', ['missing', 'mixed', 'extra-prefix'])
def test_v2_panel_generation_is_required_before_attachments(mutation):
    workspace = versioned()
    if mutation == 'missing':
        del workspace['panels'][1]['generation']
    elif mutation == 'mixed':
        workspace['panels'][1]['generation'] = 'im-workspace-generation:' + SECOND_GENERATION_UUID
    else:
        workspace['panels'][1]['generation'] = GENERATION_UUID
    before = deepcopy(workspace)
    with pytest.raises(ValueError):
        attach_compares(workspace)
    assert workspace == before


def test_v1_absent_and_explicit_retain_strict_source():
    absent = _fixture.workspace()
    legacy = attach_compares(absent)
    explicit = attach_compares(versioned(version=1))
    inspected = attach_inspectors(explicit)
    assert absent['panels'] == legacy['panels']
    assert 'generation' not in legacy['compares'][0]
    assert 'generation' not in inspected['inspectors'][0]


@pytest.mark.parametrize('stray_location', ['workspace', 'compare', 'inspector'])
def test_v1_generation_strays_never_become_valid_v2_markers(stray_location):
    workspace = versioned(version=1)
    if stray_location == 'workspace':
        workspace['generation'] = GENERATION_REFERENCE
    elif stray_location == 'compare':
        workspace = attach_compares(workspace)
        workspace['compares'][0]['generation'] = GENERATION_REFERENCE
    else:
        workspace = attach_inspectors(workspace)
        workspace['inspectors'][0]['generation'] = GENERATION_REFERENCE
    workspace['binding_version'] = 2
    mounts = (attach_compares, attach_inspectors,
              lambda value: attach_public_library(
                  value, catalogue=CATALOGUE, macro_html='', stocks_rendered=True))
    for attach in mounts:
        with pytest.raises(ValueError):
            attach(workspace)


def test_v2_library_source_is_null_and_generation_is_outside_public_view():
    workspace = versioned()
    result = attach_public_library(
        workspace, catalogue=CATALOGUE, macro_html='', stocks_rendered=True)
    assert result['library']['context']['source_reference'] is None
    assert 'library_generation' not in result['library']
    assert result['library_generation'] == GENERATION_REFERENCE
    assert result['library']['catalogue_generation'].startswith('public-copy:sha256:')


def test_v2_rendering_marks_every_enhanced_surface_and_keeps_catalogue_clean():
    macro, _ = rendered(versioned())
    doc = Document(macro)
    assert len(doc.with_attr('data-im-panel')) == 9
    assert len([attrs for _, attrs in doc.with_attr('data-im-inspector-payload')]) == 8
    assert len([attrs for _, attrs in doc.with_attr('data-im-inspector-origin')]) == 8
    assert len([attrs for _, attrs in doc.with_attr('data-im-inspector-trigger')]) == 8
    assert len(doc.with_attr('data-im-generation')) == 33
    assert all(attrs['data-im-generation'] == GENERATION_REFERENCE
               for _, attrs in doc.with_attr('data-im-generation'))
    catalogue_node = next((tag, attrs) for tag, attrs in doc.nodes
                          if 'data-im-library-catalogue' in attrs)
    catalogue = json.loads(catalogue_node[1].get('value', '{}'))
    assert GENERATION_REFERENCE not in json.dumps(catalogue)
    assert all('source_reference' not in item for item in catalogue)


def test_v2_overview_emits_actual_escaped_return_basis_and_stable_identity():
    unsafe = 'price"><script>evil()</script>'
    workspace = versioned()
    workspace['panels'][0]['overview']['context']['return_basis'] = unsafe
    macro, _ = rendered(workspace)
    overview = next(attrs for _, attrs in Document(macro).with_attr('data-view')
                    if attrs['data-view'] == 'overview')
    assert overview['data-return-basis'] == unsafe
    assert '<script>evil()</script>' not in macro
    assert overview['id'].endswith('-overview')


def test_unknown_version_marker_is_visible_and_native_overview_remains_readable():
    workspace = versioned()
    workspace['binding_version'] = 3
    macro, _ = rendered(workspace)
    doc = Document(macro)
    assert doc.with_attr('data-im-workspace')[0][1]['data-im-binding-version'] == '3'
    assert len([attrs for _, attrs in doc.with_attr('data-view')
                if attrs['data-view'] == 'overview']) >= 1
    assert 'Market overview' in macro


def test_legacy_render_has_no_invented_marker():
    macro, stocks = rendered(_fixture.workspace())
    doc = Document(macro)
    assert stocks == 'Incumbent stocks'
    assert not doc.with_attr('data-im-binding-version')
    assert not doc.with_attr('data-im-generation')


@pytest.mark.parametrize('mount', ['compare', 'inspector', 'library'])
@pytest.mark.parametrize('mutation', ['v2_missing', 'v2_mixed', 'v1_panel', 'v1_library', 'v1_inspector'])
def test_every_composition_owner_rejects_mixed_generation_before_output(mount, mutation):
    workspace = actual_production_workspace() if mutation.startswith('v2') else _fixture.workspace()
    if mutation == 'v2_missing':
        del workspace['panels'][0]['generation']
    elif mutation == 'v2_mixed':
        workspace['panels'][0]['generation'] = 'im-workspace-generation:' + SECOND_GENERATION_UUID
    elif mutation == 'v1_panel':
        workspace['panels'][0]['generation'] = GENERATION_REFERENCE
    elif mutation == 'v1_library':
        workspace['library_generation'] = GENERATION_REFERENCE
    else:
        workspace = attach_inspectors(workspace)
        workspace['inspectors'][0]['generation'] = GENERATION_REFERENCE
    before = deepcopy(workspace)
    call = {'compare': attach_compares, 'inspector': attach_inspectors,
            'library': lambda ws: attach_public_library(ws, catalogue=CATALOGUE, macro_html='', stocks_rendered=True)}[mount]
    with pytest.raises(ValueError):
        call(workspace)
    assert workspace == before


@pytest.mark.parametrize('mutation', ['v1_stray', 'v2_missing', 'v2_mixed', 'malformed_list'])
def test_macro_sidecars_participate_in_shared_generation_validation(mutation):
    from lib.intl_workspace_binding import binding_version
    workspace = versioned(version=1) if mutation == 'v1_stray' else versioned()
    workspace['macros'] = [{'context_id': 'macro-test', 'generation': GENERATION_REFERENCE}]
    if mutation == 'v2_missing': workspace['macros'][0].pop('generation')
    elif mutation == 'v2_mixed': workspace['macros'][0]['generation'] = 'im-workspace-generation:' + SECOND_GENERATION_UUID
    elif mutation == 'malformed_list': workspace['macros'] = {}
    with pytest.raises(ValueError): binding_version(workspace)


def test_valid_macro_sidecars_do_not_replace_financial_provenance():
    from lib.intl_workspace_binding import binding_version
    workspace = versioned()
    before = deepcopy(workspace['panels'])
    workspace['macros'] = [{'context_id': 'macro-test', 'generation': GENERATION_REFERENCE}]
    assert binding_version(workspace) == (2, GENERATION_REFERENCE)
    assert workspace['panels'] == before
