"""Synthetic grounding support completeness; no model/corpus/store effects."""
import copy
import hashlib
import json

import pytest

from engine.research_intelligence.extractor import _ground_rio, analyze_document
from engine.research_intelligence.schema import SCHEMA

BODY = 'Factory orders accelerated this quarter. Freight costs declined this quarter.'
VALID_A = 'Factory orders accelerated this quarter.'
INVALID = 'Regional equities trade at lower multiples.'
VALID_B = 'Freight costs declined this quarter.'
LIST_FIELDS = ('assumptions', 'forecasts', 'catalysts', 'falsifiers', 'counterarguments', 'implications', 'uncertainties')
RELATION_FIELDS = ('belief_delta', 'consensus_relation')


def rio(*, thesis_support=(0,), claims=(VALID_A, INVALID, VALID_B)):
    return {
        'schema': SCHEMA,
        'document': {'id': 'synthetic-support', 'source_type': 'other', 'content_sha256': hashlib.sha256(BODY.encode()).hexdigest()},
        'claims': [{'statement': s, 'evidence': [{'quote_span': s}], 'numbers': [], 'entities': [], 'horizon': '', 'explicit': True} for s in claims],
        'analysis': {
            'thesis': {'summary': 'The environment combines faster demand with attractive regional valuations.', 'direction': 'bullish', 'mechanism': [], 'conviction': '', 'support_claim_indices': list(thesis_support)},
            **{k: [] for k in LIST_FIELDS},
            **{k: {'statement': '', 'support_claim_indices': []} for k in RELATION_FIELDS},
        },
    }


def test_partial_thesis_support_loss_rejects_full_assertion_without_mutation():
    value = rio(thesis_support=(0, 1))
    original = copy.deepcopy(value)
    with pytest.raises(ValueError, match='grounded claim support'):
        _ground_rio(value, BODY)
    assert value == original


@pytest.mark.parametrize('field', LIST_FIELDS)
def test_optional_partial_support_loss_drops_only_affected_row(field):
    value = rio()
    value['analysis'][field] = [
        {'statement': 'Demand and cheap regional assets imply a broad opportunity.', 'support_claim_indices': [0, 1]},
        {'statement': 'Lower freight costs may ease delivery pressure.', 'support_claim_indices': [2]},
    ]
    out = _ground_rio(value, BODY)
    assert len(out['analysis'][field]) == 1
    assert out['analysis'][field][0]['statement'] == 'Lower freight costs may ease delivery pressure.'
    assert out['analysis'][field][0]['support_claim_indices'] == [1]


@pytest.mark.parametrize('field', RELATION_FIELDS)
def test_optional_relation_partial_support_loss_clears_statement(field):
    value = rio()
    value['analysis'][field] = {'statement': 'Demand and regional valuations improve the earlier stance.', 'support_claim_indices': [0, 1]}
    assert _ground_rio(value, BODY)['analysis'][field] == {'statement': '', 'support_claim_indices': []}


def test_unreferenced_bad_claim_prunes_and_complete_support_remaps_across_gap():
    value = rio(thesis_support=(2, 0))
    out = _ground_rio(value, BODY)
    assert [c['statement'] for c in out['claims']] == [VALID_A, VALID_B]
    assert out['analysis']['thesis']['support_claim_indices'] == [1, 0]
    assert value['analysis']['thesis']['support_claim_indices'] == [2, 0]


def test_existing_all_thesis_support_loss_still_rejects():
    with pytest.raises(ValueError, match='grounded claim support'):
        _ground_rio(rio(thesis_support=(1,)), BODY)


@pytest.mark.parametrize('unsupported', ['Factory orders accelerated', 'Factory orders did not accelerate this quarter.'])
def test_literal_complete_context_and_polarity_law_still_refuses(unsupported):
    with pytest.raises(ValueError, match='no source claim survived'):
        _ground_rio(rio(claims=(unsupported,)), BODY)


def test_public_analyzer_refuses_missing_selected_support_without_recall():
    value = rio(thesis_support=(0, 1))
    calls = []
    document = {'id': 'synthetic-support', 'source_type': 'other'}
    def call(system, user, *, model_id, max_tokens):
        calls.append(model_id)
        identity = json.loads(user.split('DOCUMENT IDENTITY:\n', 1)[1].split('\n\nOUTPUT SHAPE:', 1)[0])
        value['document'] = identity
        catalog = json.loads(user.split('EVIDENCE CATALOG:\n', 1)[1].split('\n\n', 1)[0])
        selected = {'selector': catalog['catalog_version'], 'document': value['document'],
                    'catalog_sha256': catalog['catalog_sha256'],
                    'selections': [{'evidence_id': catalog['units'][0]['evidence_id']}],
                    'analysis': value['analysis']}
        return json.dumps(selected), 'synthetic', 'synthetic-model'
    result = analyze_document(document, BODY, model_id='synthetic-model', call=call)
    assert result['state'] == 'invalid_model_output'
    assert result['rio'] is None
    assert calls == ['synthetic-model']


SUPPORT_SURFACES = ('thesis',) + LIST_FIELDS + RELATION_FIELDS


def _set_support_surface(value, field, support):
    statement = 'Demand and freight dynamics form a combined opportunity.'
    if field == 'thesis':
        value['analysis']['thesis']['support_claim_indices'] = support
    elif field in RELATION_FIELDS:
        value['analysis'][field] = {'statement': statement, 'support_claim_indices': support}
    else:
        value['analysis'][field] = [{'statement': statement, 'support_claim_indices': support}]


def _assert_unsupported_assertion_removed(value, field):
    if field == 'thesis':
        with pytest.raises(ValueError, match='requires grounded claim support'):
            _ground_rio(value, BODY)
    else:
        out = _ground_rio(value, BODY)
        empty = {'statement': '', 'support_claim_indices': []} if field in RELATION_FIELDS else []
        assert out['analysis'][field] == empty
        assert out['analysis']['thesis']['support_claim_indices'] == [0]


@pytest.mark.parametrize('field', SUPPORT_SURFACES)
@pytest.mark.parametrize('bad_ref', [-1, 3, '2', 2.0, True, None])
def test_partial_raw_support_loss_rejects_instead_of_salvaging_valid_subset(field, bad_ref):
    value = rio()
    _set_support_surface(value, field, [0, bad_ref])
    original = copy.deepcopy(value)
    _assert_unsupported_assertion_removed(value, field)
    assert value == original


@pytest.mark.parametrize('field', SUPPORT_SURFACES)
@pytest.mark.parametrize('malformed', [None, '0', (0,), {'claim': 0}])
def test_supplied_nonlist_support_removes_whole_assertion_on_every_surface(field, malformed):
    value = rio()
    _set_support_surface(value, field, malformed)
    _assert_unsupported_assertion_removed(value, field)


@pytest.mark.parametrize('field', SUPPORT_SURFACES)
@pytest.mark.parametrize('last_ref', [1, 2, 999])
def test_31st_raw_reference_cannot_disappear_through_truncation(field, last_ref):
    value = rio()
    _set_support_surface(value, field, [0] * 30 + [last_ref])
    _assert_unsupported_assertion_removed(value, field)


def test_valid_duplicate_support_deduplicates_then_remaps_without_loss():
    out = _ground_rio(rio(thesis_support=(2, 2, 0, 0)), BODY)
    assert out['analysis']['thesis']['support_claim_indices'] == [1, 0]


def test_exact_30_raw_reference_boundary_keeps_final_valid_reference():
    out = _ground_rio(rio(thesis_support=([0] * 29 + [2])), BODY)
    assert out['analysis']['thesis']['support_claim_indices'] == [0, 1]


def test_empty_support_is_allowed_only_as_existing_optional_empty_content():
    value = rio()
    value['analysis']['assumptions'] = [{'statement': '', 'support_claim_indices': []}]
    value['analysis']['belief_delta'] = {'statement': '', 'support_claim_indices': []}
    out = _ground_rio(value, BODY)
    assert out['analysis']['assumptions'] == []
    assert out['analysis']['belief_delta'] == {'statement': '', 'support_claim_indices': []}


def test_malformed_optional_support_public_analyzer_drops_whole_assertion_without_recall():
    value = rio()
    _set_support_surface(value, 'implications', [0, 999])
    calls = []
    def call(system, user, *, model_id, max_tokens):
        calls.append(model_id)
        value['document'] = json.loads(user.split('DOCUMENT IDENTITY:\n', 1)[1].split('\n\nOUTPUT SHAPE:', 1)[0])
        catalog = json.loads(user.split('EVIDENCE CATALOG:\n', 1)[1].split('\n\n', 1)[0])
        selected = {'selector': catalog['catalog_version'], 'document': value['document'],
                    'catalog_sha256': catalog['catalog_sha256'],
                    'selections': [{'evidence_id': catalog['units'][0]['evidence_id']}],
                    'analysis': value['analysis']}
        return json.dumps(selected), 'synthetic', 'synthetic-model'
    result = analyze_document({'id': 'synthetic-support', 'source_type': 'other'}, BODY, model_id='synthetic-model', call=call)
    assert result['state'] == 'ok'
    assert result['rio']['analysis']['implications'] == []
    assert result['rio']['analysis']['thesis']['support_claim_indices'] == [0]
    assert calls == ['synthetic-model']
