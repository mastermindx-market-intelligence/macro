"""Versioned admission of one official publisher; legacy contract stays closed."""
import pytest
from engine.government_revenue import program_ontology as po
from tests.fixtures.government_program_ontology import builders as b

URL = 'https://www.army.mil/article/291670'


def graph(version='1.2.0', **changes):
    g = b.empty_graph(); g['schema_version'] = version
    if version in ('1.2.0', '1.3.0'):
        g['public_capacity_assertions'] = []
    if version == '1.3.0':
        g['public_oversight_assertions'] = []
    row = b.evidence_row('army-source', claim_scopes=['program_identity'], evidence_class='official_contract_announcement', source_url=URL)
    row.update(changes); g['evidence'] = [row]
    return g


@pytest.mark.parametrize('version', ['1.2.0', '1.3.0'])
@pytest.mark.parametrize('scopes', [['program_identity'], ['public_capacity'], ['program_identity', 'public_capacity']])
def test_explicit_new_versions_admit_exact_official_source(version, scopes):
    candidate = graph(version, claim_scopes=scopes)
    loaded = po.load_program_ontology_graph(candidate)
    assert loaded['evidence'] == candidate['evidence']


@pytest.mark.parametrize('version', ['1.0.0', '1.1.0'])
def test_old_versions_keep_publisher_refusal(version):
    with pytest.raises(po.OntologyInputError, match='publisher_host_refused'):
        po.load_program_ontology_graph(graph(version))


@pytest.mark.parametrize('url', ['http://www.army.mil/article/291670', 'https://user:password@www.army.mil/article/291670', 'https://www.army.mil.evil.example/article/291670', 'https://army.mil/article/291670', 'https://news.www.army.mil/article/291670', 'https://www.army.mil:8443/article/291670', ' https://www.army.mil/article/291670', 'https://[invalid/', 'https://www.ar\tmy.mil/article/291670', 'https://www.ar\nmy.mil/article/291670', 'https://www.army.mil/article/291670\x00', 'https://www.army.mil/article/291670\x7f', 'https://www.army.mil/article/291 670'])
def test_noncanonical_origin_refuses(url):
    with pytest.raises(po.OntologyInputError, match='publisher_host_refused'):
        po.load_program_ontology_graph(graph(source_url=url, retrieved_from_url=url))


@pytest.mark.parametrize('changes', [
    {'retrieved_from_url': URL + '#other'}, {'claim_scopes': []},
    {'claim_scopes': ['participants']}, {'claim_scopes': ['public_oversight']},
    {'claim_scopes': 'program_identity'}, {'claim_scopes': [['program_identity']]},
    {'evidence_class': 'official_program_page'},
])
def test_outside_explicit_form_refuses_without_crashing(changes):
    # Malformed scope types are correctly refused by the earlier shape gate.
    malformed = 'claim_scopes' in changes and (not isinstance(changes['claim_scopes'], list) or any(not isinstance(x, str) for x in changes['claim_scopes']))
    expected = 'ontology_row_shape_invalid' if malformed else 'publisher_host_refused'
    with pytest.raises(po.OntologyInputError, match=expected):
        po.load_program_ontology_graph(graph(**changes))


def test_other_approved_publisher_and_pinned_issuer_keep_existing_policy():
    assert po.load_program_ontology_graph(graph(source_url='https://www.defense.gov/example/', retrieved_from_url='https://www.defense.gov/example/'))
    assert po.load_program_ontology_graph(graph(evidence_class='issuer_disclosure', source_url='https://ir.example.com/release', retrieved_from_url='https://ir.example.com/release', pinned_issuer_host='ir.example.com', pinned_issuer_host_basis='Test issuer pin'))
    assert 'www.army.mil' not in po.PUBLISHER_HOST_ALLOWLIST


def test_official_source_cannot_carry_an_issuer_pin():
    with pytest.raises(po.OntologyInputError, match='ontology_row_shape_invalid'):
        po.load_program_ontology_graph(graph(pinned_issuer_host='www.army.mil', pinned_issuer_host_basis='Not an issuer'))


@pytest.mark.parametrize('version', ['1.2.0', '1.3.0'])
@pytest.mark.parametrize('scopes', [['capability_need'], ['role'], ['program_identity', 'capability_need']])
def test_valid_general_scopes_still_refuse_army_scope_expansion(version, scopes):
    with pytest.raises(po.OntologyInputError) as exc:
        po.load_program_ontology_graph(graph(version, claim_scopes=scopes))
    assert 'publisher_host_refused' in exc.value.errors
    assert 'ontology_row_shape_invalid' not in exc.value.errors


@pytest.mark.parametrize('url', ['https://www.army.mil:443/article/291670', 'HTTPS://www.army.mil/article/291670', 'https://WWW.ARMY.MIL/article/291670', 'https://www.army.mil./article/291670', 'https://evil.example/article/291670'])
def test_other_noncanonical_publishers_refuse(url):
    with pytest.raises(po.OntologyInputError, match='publisher_host_refused'):
        po.load_program_ontology_graph(graph(source_url=url, retrieved_from_url=url))


@pytest.mark.parametrize('version', ['1.2.0', '1.3.0'])
def test_existing_nato_policy_exception_stays_class_and_scope_specific(version):
    url = 'https://www.nato.int/example'
    assert po.load_program_ontology_graph(graph(version, evidence_class='official_alliance_policy', claim_scopes=['policy_context'], source_url=url, retrieved_from_url=url))
    with pytest.raises(po.OntologyInputError, match='publisher_host_refused'):
        po.load_program_ontology_graph(graph(version, source_url=url, retrieved_from_url=url))


def test_host_eligibility_does_not_claim_an_article_path_allowlist():
    url = 'https://www.army.mil/news/'
    assert po.load_program_ontology_graph(graph(source_url=url, retrieved_from_url=url))


def test_graph_helper_preserves_the_actual_nonlist_scope_case():
    candidate = graph(claim_scopes='program_identity')
    assert candidate['evidence'][0]['claim_scopes'] == 'program_identity'
    with pytest.raises(po.OntologyInputError, match='ontology_row_shape_invalid'):
        po.load_program_ontology_graph(candidate)
