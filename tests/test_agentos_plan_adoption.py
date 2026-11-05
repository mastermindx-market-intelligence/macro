"""Pure recipes against the real Agent OS owner; no publisher or adoption effect."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compiler = load('plan_adoption_compiler_test', 'agentos_plan_adoption.py')
owner = load('plan_adoption_real_owner', 'agentos.py')
WORK = 'WS:PLAN-TEST'
WS_PATH = 'agentos/workstreams/WS-PLAN-TEST.md'
MACRO = compiler.MACRO
COMMIT = 'a' * 40
LATER = 'b' * 40
REQUEST_ID = 'mmos-project-adopt-' + '1' * 40


def capture(path, raw, commit=COMMIT):
    return {'source': {'repository': MACRO, 'path': path, 'commit': commit,
                       'content_sha256': hashlib.sha256(raw).hexdigest()}, 'raw_bytes': raw}


def record(value, body=b'\n  Exact body\r\n\xef\xbb\xbfTail\n'):
    return owner._yaml_frontmatter(value).encode() + body


@pytest.fixture
def inputs():
    ws = {'key': 'PLAN-TEST', 'title': 'Plan fixture', 'objective': 'Deliver exact content.',
          'status': 'active', 'program': 'executive-os', 'repos': ['macro'], 'owner': 'ceo',
          'class': 'build', 'blast_radius': 'user_facing', 'ambiguity': 'scoped',
          'waves': [{'id': 'W0', 'title': 'Read', 'status': 'todo'}],
          'next_action': 'Read actual content.', 'artifacts': ['macro:planning/proposal.md']}
    base = capture('planning/base.md', b'# The retained baseline\r\n', 'c' * 40)
    meta = {'schema': 'agentos.project_plan_adoption.v1', 'work_ref': WORK,
            'adopted_source': base['source'], 'predecessor': None,
            'proposal_source': None, 'display_revision': None}
    dec = {'key': 'PLAN-FIRST', 'question': 'Which plan?', 'answer': 'The exact source.',
           'rationale': 'An explicit fixture decision.',
           'alternatives': [{'option': 'Infer', 'why_not': 'No.'}], 'evidence': ['Fixture'],
           'affects': [WORK], 'confidence': 'high', 'reversibility': 'easy',
           'decided_by': 'fixture-owner', 'decided_at': '2026-11-04', 'project_plan_adoption': meta}
    candidate_ws = deepcopy(ws)
    candidate_ws['objective'] = 'Deliver the proposed exact content.'
    candidate = record(candidate_ws, b'\nCandidate body preserves CRLF\r\n')
    header = {'schema': 'agentos.project_plan_proposal.v1', 'proposal_id': 'PLAN-PROPOSAL',
              'work_ref': WORK, 'base_adoption': 'DEC:PLAN-FIRST', 'base_source': base['source'],
              'candidate_sha256': hashlib.sha256(candidate).hexdigest(),
              'rationale': 'A concrete proposed change.', 'evidence': []}
    proposal = capture('planning/proposal.md', record(header, candidate))
    candidate_path = 'planning/proposal.candidate-' + header['candidate_sha256'][:20] + '.md'
    decision_path = 'agentos/decisions/DEC-PLAN-ADOPTION-' + '1' * 40 + '.md'
    snapshot = {'schema': 'agentos.plan_adoption_snapshot.v1', 'repository': MACRO, 'commit': COMMIT,
                'workstream': capture(WS_PATH, record(ws)),
                'decisions': [capture('agentos/decisions/DEC-PLAN-FIRST.md', record(dec))],
                'proposal': proposal, 'base': base,
                'candidate_target': {'path': candidate_path, 'state': 'ABSENT'},
                'decision_target': {'path': decision_path, 'state': 'ABSENT'}}
    request = {'schema': 'agentos.plan_adoption_request.v1', 'request_id': REQUEST_ID,
               'work_ref': WORK, 'expected_commit': COMMIT, 'expected_adoption': 'DEC:PLAN-FIRST',
               'proposal_source': proposal['source'], 'base_source': base['source'],
               'candidate_sha256': header['candidate_sha256']}
    actor = {'principal_id': 'qualified-fixture-principal', 'decided_by': 'fixture-owner',
             'decided_at': '2026-11-04', 'decision_rationale': 'Adopt the reviewed exact candidate.'}
    return locals()


def phase_one(i):
    return compiler.compile_candidate_recipe(request=i['request'], snapshot=i['snapshot'], actor=i['actor'], owner=owner)


def after_candidate(i, recipe=None):
    recipe = recipe or phase_one(i)
    current = deepcopy(i['snapshot'])
    current['commit'] = LATER
    for cap in [current['workstream'], *current['decisions'], current['proposal']]:
        cap['source']['commit'] = LATER
    candidate = capture(i['candidate_path'], i['candidate'], LATER)
    current['candidate_target'] = {'path': i['candidate_path'], 'state': 'CAPTURED', 'capture': candidate}
    publication = {'schema': 'agentos.plan_candidate_publication.v1', 'state': 'VERIFIED_DEFAULT',
                   'request_id': recipe['request_id'], 'request_sha256': recipe['request_sha256'], **candidate}
    return current, publication


def phase_two(i, current=None, publication=None):
    default_current, default_publication = after_candidate(i)
    return compiler.compile_adoption_recipe(request=i['request'], initial_snapshot=i['snapshot'],
        current_snapshot=default_current if current is None else current, actor=i['actor'],
        candidate_publication=default_publication if publication is None else publication, owner=owner)


def test_phase_one_is_candidate_only_and_does_not_mutate_inputs(inputs):
    before = deepcopy(inputs)
    value = phase_one(inputs)
    assert value['phase'] == 'CANDIDATE' and value['status'] == 'PREVIEW_ONLY'
    assert len(value['edits']) == 1
    edit = value['edits'][0]
    assert edit['path'] == inputs['candidate_path'] and not edit['path'].startswith('agentos/')
    assert edit['content_utf8'].encode() == inputs['candidate']
    assert edit['expected_sha256'] is None
    assert value['preview']['changed_frontmatter_fields'] == ['objective']
    assert value['preview']['qualification_required'] == 'VERIFIED_ADOPT_PLAN_GRANT_FOR_EXACT_RECIPE'
    assert inputs == before
    assert phase_one(inputs) == value
    assert not {'authorized', 'adopted', 'may_run'} & value.keys()


def test_phase_two_exact_recipe_roundtrips_real_reciprocal_owner(inputs):
    result = phase_two(inputs)
    assert result['request_sha256'] == phase_one(inputs)['request_sha256']
    assert result['request_id'] == REQUEST_ID and result['phase'] == 'ADOPTION_DECISION'
    assert result['expected_commit'] == LATER and result['status'] == 'PREVIEW_ONLY'
    edits = {e['path']: e for e in result['edits']}
    assert set(edits) == {WS_PATH, inputs['decision_path'], 'agentos/decisions/DEC-PLAN-FIRST.md'}
    assert edits[WS_PATH]['content_utf8'].encode() == inputs['candidate']
    assert edits[WS_PATH]['expected_sha256'] == inputs['snapshot']['workstream']['source']['content_sha256']
    records = []
    for path in [inputs['decision_path'], 'agentos/decisions/DEC-PLAN-FIRST.md']:
        raw = edits[path]['content_utf8'].encode()
        parsed, _ = owner.parse_record(compiler._Record(raw))
        assert not [p for p in owner.check_decision(parsed, Path(path)) if p.hard]
        records.append(parsed)
    current = owner.select_project_plan_adoption(records, work_ref=WORK)
    assert current['decision_ref'] == result['decision_ref']
    assert current['adoption']['adopted_source'] == result['candidate_source']
    assert current['adoption']['proposal_source'] == inputs['proposal']['source']
    old_raw = inputs['snapshot']['decisions'][0]['raw_bytes']
    new_raw = edits['agentos/decisions/DEC-PLAN-FIRST.md']['content_utf8'].encode()
    assert compiler._body(old_raw) == compiler._body(new_raw)
    assert edits['agentos/decisions/DEC-PLAN-FIRST.md']['expected_sha256'] == hashlib.sha256(old_raw).hexdigest()


def test_first_real_decision_has_no_invented_predecessor(inputs):
    i = inputs
    i['snapshot']['decisions'] = []
    i['request']['expected_adoption'] = None
    header = deepcopy(i['header']); header['base_adoption'] = None
    i['snapshot']['proposal'] = capture('planning/proposal.md', record(header, i['candidate']))
    i['request']['proposal_source'] = i['snapshot']['proposal']['source']
    result = phase_two(i)
    assert len(result['edits']) == 2 and result['expected_adoption'] is None


def test_exact_existing_candidate_can_skip_only_candidate_publication(inputs):
    i = inputs
    i['snapshot']['candidate_target'] = {'path': i['candidate_path'], 'state': 'CAPTURED',
                                       'capture': capture(i['candidate_path'], i['candidate'])}
    value = phase_one(i)
    assert value['edits'] == [] and value['requires_publication'] is False
    assert value['candidate_source'] == i['snapshot']['candidate_target']['capture']['source']


@pytest.mark.parametrize('state', ['UNKNOWN', 'PR_OPEN', 'QUEUED', 'LOCAL_DEFAULT', 'CANDIDATE_ONLY'])
def test_crash_or_unknown_between_phases_does_not_emit_adoption(inputs, state):
    current, proof = after_candidate(inputs)
    proof['state'] = state
    with pytest.raises(compiler.PlanAdoptionError, match='^CANDIDATE_NOT_VERIFIED$'):
        phase_two(inputs, current, proof)
    assert inputs['snapshot']['decisions'][0]['raw_bytes'] == record(inputs['dec'])


@pytest.mark.parametrize('field', ['request_id', 'request_sha256'])
def test_publication_identity_cannot_be_retargeted(inputs, field):
    current, proof = after_candidate(inputs)
    proof[field] = ('mmos-project-adopt-' if field == 'request_id' else '') + '2' * (40 if field == 'request_id' else 64)
    with pytest.raises(compiler.PlanAdoptionError, match='^OPERATION_CONFLICT$'):
        phase_two(inputs, current, proof)


def test_same_id_changed_actor_conflicts_with_retained_phase_one(inputs):
    current, proof = after_candidate(inputs)
    inputs['actor']['decision_rationale'] = 'Changed rationale under the same ID.'
    with pytest.raises(compiler.PlanAdoptionError, match='^OPERATION_CONFLICT$'):
        phase_two(inputs, current, proof)


@pytest.mark.parametrize('target', ['candidate_target', 'decision_target'])
def test_existing_conflicting_target_refuses(inputs, target):
    path = inputs['snapshot'][target]['path']
    inputs['snapshot'][target] = {'path': path, 'state': 'CAPTURED', 'capture': capture(path, b'conflict')}
    with pytest.raises(compiler.PlanAdoptionError, match='^TARGET_CONFLICT$'):
        phase_one(inputs)


@pytest.mark.parametrize('which', ['proposal', 'workstream', 'base'])
def test_bytes_changed_after_candidate_refuses_without_retarget(inputs, which):
    current, proof = after_candidate(inputs)
    cap = current[which]
    raw = cap['raw_bytes'] + b'\nChanged\n'
    cap['raw_bytes'] = raw; cap['source']['content_sha256'] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(compiler.PlanAdoptionError) as error:
        phase_two(inputs, current, proof)
    assert error.value.code in {'STALE_PROPOSAL', 'STALE_SOURCE'}


def test_predecessor_changed_after_candidate_refuses(inputs):
    current, proof = after_candidate(inputs)
    dec = deepcopy(inputs['dec']); dec['rationale'] = 'Changed retained decision'
    current['decisions'][0] = capture('agentos/decisions/DEC-PLAN-FIRST.md', record(dec), LATER)
    with pytest.raises(compiler.PlanAdoptionError, match='^STALE_PREDECESSOR$'):
        phase_two(inputs, current, proof)


@pytest.mark.parametrize('field,value', [('expected_adoption', 'DEC:FOREIGN'), ('expected_commit', 'd' * 40),
    ('candidate_sha256', 'e' * 64), ('work_ref', 'WS:FOREIGN')])
def test_stale_or_foreign_request_refuses(inputs, field, value):
    inputs['request'][field] = value
    with pytest.raises(compiler.PlanAdoptionError):
        phase_one(inputs)


@pytest.mark.parametrize('field,value', [('request_id', 'not-the-original-operation'), ('expected_adoption', True),
    ('candidate_sha256', 'UPPER'), ('proposal_source', {'path': '/secret'}), ('unknown_grant', True)])
def test_malformed_request_is_closed_value_free(inputs, field, value):
    inputs['request'][field] = value
    with pytest.raises(compiler.PlanAdoptionError, match='^INVALID_REQUEST$'):
        phase_one(inputs)


@pytest.mark.parametrize('field,value', [('decided_at', '2026-02-30'), ('principal_id', ''), ('decision_rationale', '')])
def test_actor_facts_are_validated_but_never_grant_authority(inputs, field, value):
    inputs['actor'][field] = value
    with pytest.raises(compiler.PlanAdoptionError, match='^INVALID_REQUEST$'):
        phase_one(inputs)


def test_forged_capture_hash_fails_before_recipe(inputs):
    inputs['snapshot']['proposal']['raw_bytes'] += b'forged'
    with pytest.raises(compiler.PlanAdoptionError, match='^SOURCE_BYTES_MISMATCH$'):
        phase_one(inputs)


def test_candidate_absent_after_claimed_publication_refuses(inputs):
    current, proof = after_candidate(inputs)
    current['candidate_target'] = {'path': inputs['candidate_path'], 'state': 'ABSENT'}
    with pytest.raises(compiler.PlanAdoptionError, match='^CANDIDATE_NOT_VERIFIED$'):
        phase_two(inputs, current, proof)


def test_canonical_files_are_untouched_by_recipe(inputs):
    paths = [ROOT / WS_PATH, ROOT / inputs['candidate_path'], ROOT / inputs['decision_path']]
    assert not any(p.exists() for p in paths)
    phase_one(inputs); phase_two(inputs)
    assert not any(p.exists() for p in paths)


@pytest.mark.parametrize('path', ['agentos/proposal.md', 'AgentOS/proposal.md', '.git/proposal.md', '.GIT/proposal.md'])
def test_candidate_artifact_never_targets_owner_or_git_namespace(inputs, path):
    i = inputs
    proposal = capture(path, i['proposal']['raw_bytes'])
    ws = deepcopy(i['ws']); ws['artifacts'] = ['macro:' + path]
    i['snapshot']['proposal'] = proposal
    i['snapshot']['workstream'] = capture(WS_PATH, record(ws))
    i['request']['proposal_source'] = proposal['source']
    with pytest.raises(compiler.PlanAdoptionError, match='^UNSUPPORTED_CANDIDATE$'):
        phase_one(i)


def test_unassociated_proposal_does_not_acquire_authority_from_valid_header(inputs):
    ws = deepcopy(inputs['ws']); ws['artifacts'] = []
    inputs['snapshot']['workstream'] = capture(WS_PATH, record(ws))
    with pytest.raises(compiler.PlanAdoptionError, match='^STALE_PROPOSAL$'):
        phase_one(inputs)


def test_plain_markdown_candidate_is_not_silently_used_to_replace_workstream(inputs):
    i = inputs; candidate = b'# A prose-only proposal\n'
    header = deepcopy(i['header']); header['candidate_sha256'] = hashlib.sha256(candidate).hexdigest()
    i['snapshot']['proposal'] = capture('planning/proposal.md', record(header, candidate))
    i['request']['proposal_source'] = i['snapshot']['proposal']['source']
    i['request']['candidate_sha256'] = header['candidate_sha256']
    with pytest.raises(compiler.PlanAdoptionError, match='^UNSUPPORTED_CANDIDATE$'):
        phase_one(i)


def test_competing_current_decisions_fail_instead_of_timestamp_election(inputs):
    other = deepcopy(inputs['dec']); other['key'] = 'COMPETING'; other['decided_at'] = '2026-11-03'
    inputs['snapshot']['decisions'].append(capture('agentos/decisions/DEC-COMPETING.md', record(other)))
    with pytest.raises(compiler.PlanAdoptionError, match='^STALE_PREDECESSOR$'):
        phase_one(inputs)


def test_candidate_commit_cannot_be_confused_with_proposal_artifact_hash(inputs):
    current, proof = after_candidate(inputs)
    proof['source'] = deepcopy(inputs['proposal']['source'])
    with pytest.raises(compiler.PlanAdoptionError):
        phase_two(inputs, current, proof)


def test_exact_recipe_has_no_source_timestamp_or_generated_operation_id(inputs):
    a = phase_one(inputs); b = phase_one(deepcopy(inputs))
    assert a == b
    assert 'now' not in a and 'created_at' not in a and 'operation_id' not in a
    assert a['request_id'] == inputs['request']['request_id']
