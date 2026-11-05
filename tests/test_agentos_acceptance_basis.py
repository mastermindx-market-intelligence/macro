"""Existing compiler and real record fixtures; no Runtime grant or acceptance."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/agentos.py'
FROZEN = datetime.datetime(2026, 8, 12, 14, tzinfo=datetime.timezone.utc)


def module():
    spec = importlib.util.spec_from_file_location('acceptance_basis_agentos', CLI)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def ref(path='research/fixture.md', repository='mastermindx-market-intelligence/Mastermind'):
    return dict(repository=repository, commit='a' * 40, path=path, content_sha256='b' * 64)


def contract(ident='fixture-one'):
    return dict(commission_id=ident, commission_ref=ref('docs/superpowers/specs/fixture.md'),
        continuity_ref=ref('agentos/handoffs/TARGET-initial.md', 'mastermindx-market-intelligence/macro'),
        original_intent_ref=ref(), proof_contract_ref=ref(), original_proof_contract_ref=ref(),
        current_intent_revision='initial-v1', correction_state='NO_CORRECTION_DECLARED_AT_THIS_REVISION',
        correction_chain=[], original_source_status='AUTHENTIC_USER_INPUT_CANDIDATE',
        criteria_objective='Original goal [MASTERMIND_ACCEPTANCE_CRITERIA_V1:["Actual visible result"]]',
        criteria_sources=[dict(criterion_index=0, source_ref=ref(), locators=['15: original test'])],
        proof_obligations=[dict(source_ref=ref(), section='15', label='Original test',
                               required_outcome='Actual evidence must satisfy this individual requirement.')])


def write(path, contracts=None):
    data = dict(key='TARGET', title='Shared programme context', objective='Preserve every programme.',
        status='active', program='project-active-build-control', repos=['macro'], owner='ceo-sol',
        **{'class': 'build'}, blast_radius='reversible', ambiguity='scoped',
        waves=[dict(id='W0', title='First wave', status='todo')], next_action='Verify actual result.')
    if contracts is not None:
        data['acceptance_contracts'] = contracts
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('---\n' + yaml.safe_dump(data, sort_keys=False) + '---\n\nSource body.\n')
    return data


@pytest.fixture
def source(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    path = repo / 'agentos/workstreams/WS-TARGET.md'
    write(path, [contract()])
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'add', 'agentos'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'Immutable fixture only'], check=True)
    return repo, path


def compile_source(repo):
    mod = module()
    store = mod.load_store(repo / 'agentos', programs=None)
    bundle = mod.compile_bundle(store, workstream='TARGET', now=FROZEN, budget=700)
    return mod, store, bundle


def entry(bundle, ident='fixture-one'):
    return bundle['acceptance_basis']['by_commission'][ident]


def test_actual_committed_record_identity_and_no_execution_association(source):
    repo, path = source
    _, _, bundle = compile_source(repo)
    actual = entry(bundle)
    assert actual['source_state'] == 'CURRENT'
    assert actual['current_intent_ref'] == actual['source_record_ref']
    assert actual['source_record_ref']['content_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual['source_record_ref']['commit'] == subprocess.check_output(
        ['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    assert actual['execution_commission_refs'] == []
    assert actual['execution_commission_state'] == 'EXECUTION_COMMISSION_NOT_ASSOCIATED'
    assert bundle['acceptance_basis']['authoritative'] is False
    assert actual['current_intent_text'] == actual['criteria_objective']
    assert actual['proof_obligation_digests'] == [hashlib.sha256(json.dumps(
        row, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False,
    ).encode()).hexdigest() for row in actual['proof_obligations']]
    digest = dict(actual)
    digest.pop('acceptance_basis_digest')
    assert actual['acceptance_basis_digest'] == hashlib.sha256(json.dumps(
        digest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def test_shared_workstream_preserves_independent_explicit_commissions(source):
    repo, path = source
    write(path, [contract('first'), contract('second')])
    _, _, bundle = compile_source(repo)
    assert set(bundle['acceptance_basis']['by_commission']) == {'first', 'second'}
    assert all(row['source_state'] == 'UNPUBLISHED' for row in bundle['acceptance_basis']['by_commission'].values())
    assert 'selected_commission' not in bundle['acceptance_basis']


def test_dirty_record_is_unpublished_and_source_digest_changes(source):
    repo, path = source
    _, _, before = compile_source(repo)
    changed = contract()
    changed['criteria_objective'] = 'Changed literal source [MASTERMIND_ACCEPTANCE_CRITERIA_V1:["New proof"]]'
    write(path, [changed])
    _, _, after = compile_source(repo)
    assert entry(after)['source_state'] == 'UNPUBLISHED'
    assert before['source_records_digest'] != after['source_records_digest']
    assert entry(before)['acceptance_basis_digest'] != entry(after)['acceptance_basis_digest']


def test_loaded_record_change_is_stale_instead_of_rebinding(source):
    repo, path = source
    mod = module()
    store = mod.load_store(repo / 'agentos', programs=None)
    changed = contract()
    changed['current_intent_revision'] = 'changed-after-load'
    write(path, [changed])
    bundle = mod.compile_bundle(store, workstream='TARGET', now=FROZEN, budget=700)
    assert entry(bundle)['source_state'] == 'STALE'
    assert entry(bundle)['source_record_ref'] is None


@pytest.mark.parametrize('state,expected', [('MISSING', 'MISSING'), ('UNRESOLVED', 'UNKNOWN')])
def test_correction_missingness_never_becomes_initial_empty_assertion(source, state, expected):
    repo, path = source
    declaration = contract()
    declaration['correction_state'] = state
    write(path, [declaration])
    _, _, bundle = compile_source(repo)
    assert entry(bundle)['correction_state'] == state
    assert entry(bundle)['source_state'] == expected


@pytest.mark.parametrize('failure', ['MISSING', 'DENIED', 'UNKNOWN'])
def test_actual_source_failure_stays_explicit_with_no_current_reference(source, monkeypatch, failure):
    repo, path = source
    mod, store, _ = compile_source(repo)
    record = store.records['WS/TARGET']
    if failure == 'MISSING':
        path.unlink()
    elif failure == 'DENIED':
        original = Path.read_bytes
        def denied(selected):
            if selected == path:
                raise PermissionError('bounded fixture refusal')
            return original(selected)
        monkeypatch.setattr(Path, 'read_bytes', denied)
    else:
        monkeypatch.setattr(mod, '_git', lambda *args, **kwargs: None)
    actual = mod._compile_acceptance_basis(store, record, path)['by_commission']['fixture-one']
    assert actual['source_state'] == failure
    assert actual['current_intent_ref'] is None
    assert actual['source_record_ref'] is None
    assert actual['execution_commission_state'] == 'EXECUTION_COMMISSION_NOT_ASSOCIATED'


@pytest.mark.parametrize('damage', ['duplicate', 'unknown', 'unsafe', 'correction', 'index', 'obligation', 'execution', 'repository-type'])
def test_malformed_declaration_is_a_named_hard_problem(source, damage):
    _, path = source
    value = contract()
    values = [value]
    if damage == 'duplicate': values.append(contract())
    elif damage == 'unknown': value['grant'] = 'CEO'
    elif damage == 'unsafe': value['original_intent_ref']['path'] = '../private.md'
    elif damage == 'correction': value['correction_chain'] = [ref()]
    elif damage == 'index': value['criteria_sources'][0]['criterion_index'] = 2
    elif damage == 'obligation': value['proof_obligations'].append(value['proof_obligations'][0])
    elif damage == 'execution': value['execution_commission_refs'] = [ref('agentos/handoffs/not-runtime.md', 'mastermindx-market-intelligence/macro')]
    else: value['original_intent_ref']['repository'] = []
    data = write(path, values)
    problems = module().check_workstream(data, path, None)
    assert any(problem.hard and problem.rule == 'bad-acceptance-contract' for problem in problems)


def test_literal_objective_is_not_parsed_or_given_criterion_ids_here(source):
    repo, path = source
    declaration = contract()
    declaration['criteria_objective'] = 'Literal malformed suffix [MASTERMIND_ACCEPTANCE_CRITERIA_V1:not-json]'
    write(path, [declaration])
    _, _, bundle = compile_source(repo)
    actual = entry(bundle)
    assert actual['criteria_objective'] == declaration['criteria_objective']
    assert 'criterion_digest' not in json.dumps(actual)
    assert actual['criteria_objective_sha256'] == hashlib.sha256(declaration['criteria_objective'].encode()).hexdigest()


def test_no_contract_keeps_legacy_context_without_selecting_latest_handoff(source):
    repo, path = source
    write(path)
    _, _, bundle = compile_source(repo)
    assert bundle['target']['workstream'] == 'WS:TARGET'
    assert bundle['acceptance_basis']['by_commission'] == {}
    assert {section['id'] for section in bundle['sections']} == {
        'higher_law', 'workstream', 'decisions', 'discoveries', 'handoff', 'artifacts'}


def test_exact_execution_reference_is_only_a_source_association(source):
    repo, path = source
    declaration = contract()
    declaration['execution_commission_refs'] = [ref('COMMISSION.md')]
    write(path, [declaration])
    _, _, bundle = compile_source(repo)
    actual = entry(bundle)
    assert actual['execution_commission_refs'] == declaration['execution_commission_refs']
    assert actual['execution_commission_state'] == 'ASSOCIATED_SOURCE_REFERENCES_ONLY'
    assert bundle['acceptance_basis']['authoritative'] is False


def test_actual_cli_json_and_text_keep_proof_and_budget_honesty(source):
    repo, _ = source
    environ = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                   MACRO_TERMINAL_REPO='/nonexistent-terminal-checkout',
                   MACRO_MASTERMIND_REPO='/nonexistent-mastermind-checkout')
    argv = [sys.executable, '-B', str(CLI), 'compile-context', '--root', str(repo / 'agentos'),
            '--workstream', 'TARGET', '--budget', '500', '--now', FROZEN.isoformat()]
    result = subprocess.run(argv, capture_output=True, text=True, env=environ)
    assert result.returncode == 0, result.stderr
    bundle = json.loads(result.stdout)
    actual = entry(bundle)
    assert actual['proof_obligations'] == contract()['proof_obligations']
    assert bundle['token_estimate'] > bundle['token_budget']
    assert any('exceeds token_budget' in reason for reason in bundle['degraded'])
    text = subprocess.run(argv + ['--text'], capture_output=True, text=True, env=environ)
    assert text.returncode == 0
    rendered = json.loads(next(line for line in text.stdout.splitlines()
                               if line.startswith('{') and '"criteria_objective"' in line))
    assert rendered['criteria_objective'] == actual['criteria_objective']
    assert rendered['proof_obligations'] == actual['proof_obligations']


def test_real_r2_data_retains_every_original_obligation_and_exact_candidate_input():
    mod = module()
    path = ROOT / 'agentos/workstreams/WS-CHAIRMAN-CONTROL-ROOM.md'
    record, _ = mod.parse_record(path)
    declaration = next(row for row in record['acceptance_contracts'] if row['commission_id'] == 'meta-ceo-office-r2-20261012')
    assert not mod._acceptance_contract_problems(record, path)
    assert len(declaration['proof_obligations']) == 48
    assert sum(row['section'] == '15' for row in declaration['proof_obligations']) == 32
    assert sum(row['section'] == '13.1' for row in declaration['proof_obligations']) == 7
    assert sum(row['section'] == '14' for row in declaration['proof_obligations']) == 7
    assert sum(row['section'] == '13.3' for row in declaration['proof_obligations']) == 1
    assert sum(row['section'] == '12' for row in declaration['proof_obligations']) == 1
    assert declaration['original_intent_ref']['content_sha256'] == 'a5c534ddabcd1034372354a1ec645dffe1a2520795035a757e4f7def8300c62d'
    assert declaration['commission_ref']['content_sha256'] == 'f5478e366e1f97eafb4bb0b26f6435944d79fd83223b87ab89f83de0e685509a'
    assert declaration.get('execution_commission_refs', []) == []


def test_real_r2_boundary_and_rollback_prose_are_literal_independent_obligations():
    mod = module()
    path = ROOT / "agentos/workstreams/WS-CHAIRMAN-CONTROL-ROOM.md"
    record, _ = mod.parse_record(path)
    rows = record["acceptance_contracts"][0]["proof_obligations"]
    required = {'zero observed violations plus credible enforcement at the relevant boundary': 'For wrong-target writes, duplicate effects, unauthorized disclosure and stale-principal commands, require zero observed violations plus credible enforcement at the relevant boundary. If the enforcement mechanism is missing, a clean small test sample is insufficient.', 'Rollback': 'Rollback disables new admissions for the affected role/route while preserving in-flight task IDs, effects, results and pending consumption. Uninstalling a UI or stopping a provider does not prove a child stopped. Test administrative pause and exact reconciliation without depending on a responsive Dot.'}
    for label, outcome in required.items():
        row = next(value for value in rows if value["label"] == label)
        assert row["section"] == "15"
        assert row["required_outcome"] == outcome
        assert row["source_ref"]["content_sha256"] == "a5c534ddabcd1034372354a1ec645dffe1a2520795035a757e4f7def8300c62d"
