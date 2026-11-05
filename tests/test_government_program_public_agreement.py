"""Documentary agreements have revisable observations, never inferred identities."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json

import pytest

from engine.government_revenue import program_ontology as po
from scripts import curate_government_program_ontology as curator
from tests.fixtures.government_program_ontology import builders as b

CAPTURE = '2026-10-18T02:55:55+00:00'
FIRST = '2026-10-18T04:10:00+00:00'
SECOND = '2026-10-18T04:15:00+00:00'
GRAPH = '2026-10-18T04:20:00+00:00'


def graph():
    g = b.empty_graph(graph_known_at=GRAPH, graph_effective_at=GRAPH)
    g.update(schema_version='1.4.0', public_capacity_assertions=[], public_oversight_assertions=[], public_agreement_assertions=[])
    g['evidence'] = [b.evidence_row('synthetic-agreement-only', claim_scopes=['public_agreement'],
        evidence_class='official_contract_announcement', source_url='https://www.sda.mil/example/',
        retrieved_at=CAPTURE, known_at=CAPTURE)]
    return g


def seal(row):
    body = {k: v for k, v in row.items() if k != 'id'}
    body['evidence_refs'] = sorted(body['evidence_refs'])
    row['id'] = 'prog-agreement:' + sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()[:24]
    return row


def claim(g, **changes):
    row = dict(revision=1, source_url=g['evidence'][0]['source_url'],
        program_label='Synthetic AMDT3 source label', umbrella_label='Synthetic umbrella label',
        agreement_form='firm_fixed_price_ota_prototype',
        parties=[dict(name_literal='Unresolved example party', entity_id=None,
                      potential_value=dict(value=955, unit='USD_million', approximate=True), announced_vehicles=18)],
        collective_value=dict(value=1.75, unit='USD_billion', approximate=True, overlaps_named_party_values=True),
        expected_launch_year=2028, published_on='2026-07-13', known_at=FIRST, verification_state='reviewed',
        evidence_refs=[g['evidence'][0]['evidence_id']], predecessor_id=None, succession_reason=None)
    row.update(changes)
    return seal(row)


def test_new_documentary_contract_loads_without_inventing_programme_or_counterparty():
    g = graph(); g['public_agreement_assertions'] = [claim(g)]
    out = po.load_program_ontology_graph(g)
    assert not out['programs'] and not out['role_assertions'] and not out['milestones']
    assert out['public_agreement_assertions'][0]['parties'][0]['entity_id'] is None
    assert all(not out['authority'][k] for k in ('can_rank', 'can_size', 'can_gate', 'can_originate_signal'))


@pytest.mark.parametrize('version', ['1.0.0', '1.1.0', '1.2.0', '1.3.0'])
def test_new_scope_and_host_are_refused_by_every_legacy_version(version):
    g = graph(); g['schema_version'] = version
    g.pop('public_agreement_assertions')
    if version != '1.3.0': g.pop('public_oversight_assertions')
    if version in ('1.0.0', '1.1.0'): g.pop('public_capacity_assertions')
    with pytest.raises(po.OntologyInputError): po.load_program_ontology_graph(g)


def test_same_publisher_bytes_can_correct_observation_and_replay_prior_cutoff():
    g = graph(); first = claim(g)
    corrected = claim(g, revision=2, known_at=SECOND, predecessor_id=first['id'], succession_reason='corrected',
                      program_label='Corrected literal without a canonical programme ID')
    original_evidence = deepcopy(g['evidence'])
    g['public_agreement_assertions'] = [first, corrected]
    g['overrides'] = [b.override_row(target_row_id=first['id'], known_at=SECOND,
                                    evidence_refs=first['evidence_refs'])]
    out = po.load_program_ontology_graph(g)
    before = po.current_public_agreement_rows(out, analysis_as_of=datetime.fromisoformat(FIRST))
    after = po.current_public_agreement_rows(out, analysis_as_of=datetime.fromisoformat(SECOND))
    assert [r['id'] for r in before] == [first['id']]
    assert [r['id'] for r in after] == [corrected['id']]
    assert out['evidence'] == original_evidence
    assert len(out['public_agreement_assertions']) == 2


@pytest.mark.parametrize('change', [{'revision': 3}, {'source_url': 'https://www.sda.mil/other/'},
                                     {'known_at': CAPTURE}, {'predecessor_id': 'prog-agreement:' + '0'*24}])
def test_invalid_or_dangling_correction_chain_refuses(change):
    g = graph(); first = claim(g)
    second = claim(g, revision=2, known_at=SECOND, predecessor_id=first['id'], succession_reason='corrected')
    second.update(change); seal(second); g['public_agreement_assertions'] = [first, second]
    with pytest.raises(po.OntologyInputError): po.load_program_ontology_graph(g)


def test_curator_owns_migration_and_idempotent_documentary_admission(tmp_path):
    g = graph(); row = claim(g); evidence = g['evidence'].pop()
    g['schema_version'] = '1.3.0'; del g['public_agreement_assertions']
    target = tmp_path / 'program_ontology.json'; target.write_text(json.dumps(g))
    worksheet = b.worksheet(reviewed_at=FIRST, coverage=[dict(scope='public_agreement', subject_type='source_evidence', subject_id=evidence['evidence_id'])],
        rows=[dict(action='admit', target_kind='evidence', candidate_row=evidence),
              dict(action='admit', target_kind='public_agreement_assertion', candidate_row=row)])
    source = tmp_path / 'worksheet.json'; source.write_text(json.dumps(worksheet))
    report = curator.curate_worksheet(source, target_path=target, schema_version='1.4.0')
    assert report['rejected_count'] == 0
    loaded = po.load_program_ontology_graph(json.loads(target.read_text()))
    assert loaded['review_coverage'][0]['admitted_count'] == 1
    assert po.derive_review_coverage(loaded, scope='public_agreement', subject_type='source_evidence', subject_id=evidence['evidence_id'], analysis_as_of=datetime.fromisoformat(FIRST))[0] == 'reviewed'
    before = target.read_bytes(); curator.curate_worksheet(source, target_path=target)
    assert target.read_bytes() == before
    assert 'public_agreement_assertion' not in curator._LOGICAL_TARGET_KINDS


def theme_inputs(g):
    from engine.government_revenue import program_theme_context as t
    raw = json.dumps(g).encode()
    owner = t.OwnerSnapshot('program_ontology', raw, GRAPH, 'synthetic-reviewed-source-only', 'qualified_public_display')
    row = g['public_agreement_assertions'][0]
    ref = dict(owner_key='ontology', pointer='/public_agreement_assertions/0', row_id=row['id'])
    return t, {'ontology': owner}, ref


def test_theme_explains_reported_prototype_terms_without_promoting_any_identity():
    from engine.government_revenue import program_theme_disclosure as d
    g = graph(); g['public_agreement_assertions'] = [claim(g)]
    t, owners, ref = theme_inputs(g)
    assignments = {'golden_dome': dict(funding_stage=dict(state='partial', reason_code='prototype_agreement_only', references=[ref]),
                                     next_event=dict(state='partial', reason_code='reported_launch_availability_target', references=[ref]))}
    payload = t.compose_program_theme_context(assignments, owners=owners, generated_at=GRAPH, as_of=GRAPH)
    public = d.disclose_program_themes(payload, owners=owners, current_owner_receipts={'ontology': dict(state='available', sha256=sha256(owners['ontology'].raw_bytes).hexdigest(), owner_alias_state='unchanged')})
    golden = public['themes'][0]
    assert public['schema_version'] == '1.1.0'
    assert golden['rail_states']['funding_stage'] == 'partial'
    assert golden['research_state'] == 'EVIDENCE_INSUFFICIENT'
    assert '955' in golden['known_en'] and '1.75' in golden['known_en']
    assert 'potential' in golden['known_en'] and 'revenue' in golden['known_en']
    assert '2028' in golden['next_en'] and '预期' in golden['next_zh']
    source = golden['sources'][0]
    assert source['documentary_class'] == 'prototype_agreement'
    assert source['source_publication_date'] == '2026-07-13'
    assert source['source_available_at'] == CAPTURE and source['house_known_at'] == FIRST
    assert source['program_id'] is None and source['issuer_id'] is None and source['security_id'] is None
    legacy = deepcopy(public); legacy['schema_version'] = '1.0.0'; legacy['content_id'] = d.disclosure_content_id(legacy)
    with pytest.raises(ValueError): d.validate_public_theme_disclosure(legacy)


@pytest.mark.parametrize('rail,state,reason', [('funding_stage', 'supported', 'prototype_agreement_only'),
    ('exposure', 'partial', 'prototype_agreement_only'), ('economics', 'partial', 'prototype_agreement_only')])
def test_prototype_reference_cannot_be_promoted_or_reused_as_exposure_or_economics(rail, state, reason):
    g = graph(); g['public_agreement_assertions'] = [claim(g)]
    t, owners, ref = theme_inputs(g)
    with pytest.raises(ValueError):
        t.compose_program_theme_context({'golden_dome': {rail: dict(state=state, reason_code=reason, references=[ref])}},
                                       owners=owners, generated_at=GRAPH, as_of=GRAPH)


def test_reported_target_stays_next_through_target_year_only():
    g = graph(); g['public_agreement_assertions'] = [claim(g)]
    t, owners, ref = theme_inputs(g)
    assignment = {'golden_dome': dict(next_event=dict(state='partial', reason_code='reported_launch_availability_target', references=[ref]))}
    t.compose_program_theme_context(assignment, owners=owners, generated_at='2028-12-31T23:59:59+00:00', as_of='2028-12-31T23:59:59+00:00')
    with pytest.raises(ValueError, match='past_agreement_target'):
        t.compose_program_theme_context(assignment, owners=owners, generated_at='2029-01-01T00:00:00+00:00', as_of='2029-01-01T00:00:00+00:00')


def test_new_graph_canonical_clock_and_schema_remain_consistent():
    from pathlib import Path
    from jsonschema import Draft202012Validator, FormatChecker
    g = graph(); g['public_agreement_assertions'] = [claim(g)]
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / 'contracts/government_revenue/government_program_ontology.v1_4.schema.json').read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(g)
    g['public_agreement_assertions'][0] = claim(g, known_at='2026-10-18T04:10:00Z')
    with pytest.raises(po.OntologyInputError, match='public_agreement_invalid_known_at'):
        po.load_program_ontology_graph(g)


def test_new_graph_preserves_existing_capacity_and_oversight_dossier_views():
    from engine.government_revenue import program_dossier as pd
    from tests import test_government_program_public_capacity as cap
    from tests import test_government_program_oversight as oversight
    g = cap.graph(); g['schema_version'] = '1.4.0'
    g.update(public_oversight_assertions=[], public_agreement_assertions=[])
    g['public_capacity_assertions'] = [cap.claim(g)]
    bundle = pd.compose_program_dossier_bundle(ontology_graph=po.load_program_ontology_graph(g), as_of='2026-08-22', generated_at=b.GRAPH_KNOWN_AT)
    assert pd.is_valid_program_dossier_payload(bundle)
    assert bundle['dossiers'][0]['public_capacity']['announced_target'][0]['quantity'] == 2000
    g = oversight.oversight_graph(); g['schema_version'] = '1.4.0'; g['public_agreement_assertions'] = []
    assert po.load_program_ontology_graph(g)['schema_version'] == '1.4.0'


def test_source_block_is_cutoff_visible_and_does_not_rewrite_evidence():
    g = graph(); first = claim(g); g['public_agreement_assertions'] = [first]
    original_evidence = deepcopy(g['evidence'])
    g['overrides'] = [b.override_row(action='block', subject_type='source_evidence', subject_id=first['evidence_refs'][0], known_at=SECOND, evidence_refs=first['evidence_refs'])]
    out = po.load_program_ontology_graph(g)
    assert len(po.current_public_agreement_rows(out, analysis_as_of=datetime.fromisoformat(FIRST))) == 1
    assert po.current_public_agreement_rows(out, analysis_as_of=datetime.fromisoformat(SECOND)) == []
    assert out['evidence'] == original_evidence


def test_review_delayed_retirement_does_not_revive_visible_predecessor():
    g = graph(); first = claim(g)
    second = claim(g, revision=2, known_at=SECOND, predecessor_id=first['id'], succession_reason='corrected')
    g['public_agreement_assertions'] = [first, second]
    g['overrides'] = [b.override_row(target_row_id=first['id'], known_at='2026-10-18T04:16:00+00:00', evidence_refs=first['evidence_refs'])]
    out = po.load_program_ontology_graph(g)
    assert [r['id'] for r in po.current_public_agreement_rows(out, analysis_as_of=datetime.fromisoformat('2026-10-18T04:15:30+00:00'))] == [second['id']]


def test_two_independent_roots_cannot_hide_prior_overlap_behind_later_retirement():
    g = graph(); first = claim(g)
    independent = claim(g, known_at=SECOND, program_label='Different interpretation with no predecessor')
    g['public_agreement_assertions'] = [first, independent]
    g['overrides'] = [b.override_row(target_row_id=first['id'], known_at='2026-10-18T04:16:00+00:00', evidence_refs=first['evidence_refs'])]
    with pytest.raises(po.OntologyInputError, match='public_agreement_multiplicity_invalid'):
        po.load_program_ontology_graph(g)


def test_review_issuer_pin_path_is_qualified_without_global_official_allowlist():
    g = graph(); e = g['evidence'][0]
    e.update(evidence_class='issuer_disclosure', source_url='https://www.l3harris.com/newsroom/example/', retrieved_from_url='https://www.l3harris.com/newsroom/example/', pinned_issuer_host='www.l3harris.com', pinned_issuer_host_basis='Synthetic first-party source pin')
    g['public_agreement_assertions'] = [claim(g)]
    assert po.load_program_ontology_graph(g)['public_agreement_assertions'][0]['parties'][0]['entity_id'] is None


def test_review_new_source_scope_cannot_become_programme_identity():
    g = graph(); g['public_agreement_assertions'] = [claim(g)]
    g['programs'] = [b.program_row(known_at=FIRST, evidence_refs=[g['evidence'][0]['evidence_id']])]
    with pytest.raises(po.OntologyInputError, match='claim_scope_coverage_missing'):
        po.load_program_ontology_graph(g)
