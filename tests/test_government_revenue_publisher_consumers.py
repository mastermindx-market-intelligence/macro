"""Derived consumer bytes must travel inside the sealed publisher generation.

Staging checks execute extracted workflow commands against real Git fixtures;
argument captures test the existing guards' call sites, not production acceptance.
"""
from pathlib import Path
import subprocess
import shlex
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/government-revenue-live.yml'
DERIVED_PATHS = (
    'data/government_revenue/defense_economics.json',
    'data/government_revenue/candidate_research_state.json',
    'site/government-revenue-data/defense-economics.json',
    'site/government-revenue-data/research-state.json',
    'site/government-revenue-investor.js', 'site/government-revenue-investor.css',
    'site/government-revenue-investor-start.js', 'site/government-revenue-page.js',
    'site/government-revenue-critical-theme.css', 'site/theme.js',
    'site/government-revenue-sbir.js', 'site/government-revenue-sbir.css',
    'site/government-revenue-briefcase.js', 'site/government-revenue-briefcase-ui.js',
    'site/government-revenue-parity.css', 'site/government-revenue-dossiers.js',
    'site/government-revenue-candidate-radar.js',
)
CANDIDATE_PATHS = tuple('data/government_revenue/' + name for name in (
    'candidate_ledger.jsonl', 'candidate_queue.json', 'candidate_projection_state.json',
    'candidate_projection_status.json'))


def _steps():
    return {step.get('name', str(i)): step for i, step in
            enumerate(yaml.safe_load(WORKFLOW.read_text())['jobs']['refresh']['steps'])}


def _commit_run():
    return _steps()['commit complete evidence projection']['run']


def _calls(script, command):
    lines = script.splitlines()
    calls = []
    for i, line in enumerate(lines):
        if line.strip().startswith(command + ' '):
            chunk = [line]
            while chunk[-1].rstrip().endswith('\\'):
                i += 1
                chunk.append(lines[i])
            calls.append('\n'.join(chunk))
    return calls


def _staging_blocks():
    run = _commit_run()
    initial = run[run.index('stage_candidates=('):run.index('python scripts/ci/govrev_candidate_proof.py verify')]
    retry = run[run.index('while push_attempt; do'):]
    clean = _calls(run, 'push_staged_clean')
    assert len(clean) == 2
    return initial, _calls(retry, 'git add')[0], clean


def _git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          capture_output=True, text=True).stdout


def _repo(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    _git(root, 'init', '-q')
    _git(root, 'config', 'user.name', 'publisher wiring test')
    _git(root, 'config', 'user.email', 'publisher-wiring@test')
    _, retry, _ = _staging_blocks()
    retry_paths = shlex.split(retry)[2:]
    for path in sorted(set((*CANDIDATE_PATHS, *DERIVED_PATHS, *retry_paths))):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('baseline\n')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'last good generation')
    return root


def _bash(root, script):
    result = subprocess.run(['/bin/bash', '-euo', 'pipefail', '-c', script], cwd=root,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@pytest.mark.parametrize('changed', DERIVED_PATHS)
def test_consumer_only_change_cannot_false_skip_publication(tmp_path, changed):
    root = _repo(tmp_path)
    (root / changed).write_text('new derived generation\n')
    _git(root, 'diff', '--quiet', '--', *CANDIDATE_PATHS)
    initial, _, _ = _staging_blocks()
    output = _bash(root, 'AWARD_EVENT_BUNDLE_PRESENT=false\n' + initial +
                   '\nprintf "MATERIAL_GENERATION\\n"\n')
    assert 'MATERIAL_GENERATION' in output
    assert _git(root, 'diff', '--cached', '--name-only').splitlines() == [changed]
    _git(root, 'diff', '--cached', '--quiet', '--', *CANDIDATE_PATHS)
    proof = _steps()['prove the candidate projection before publishing it']
    assert proof['if'] == _steps()['build Government Revenue projection']['if']
    assert 'govrev_candidate_proof.py prove' in proof['run']
    assert 'git status' not in proof['run']


@pytest.mark.parametrize('changed', (
    'data/government_revenue/candidate_research_state.json',
    'site/government-revenue-data/defense-economics.json',
    'site/government-revenue-investor.js',
    'site/government-revenue-investor-start.js',
    'site/government-revenue-page.js',
    'site/government-revenue-critical-theme.css', 'site/theme.js',
))
def test_retry_stage_carries_derived_and_copied_assets(tmp_path, changed):
    root = _repo(tmp_path)
    (root / changed).write_text('rebuilt after rebase\n')
    _, retry, _ = _staging_blocks()
    _bash(root, retry)
    assert _git(root, 'diff', '--cached', '--name-only').splitlines() == [changed]


def test_both_existing_staging_guards_receive_all_named_outputs(tmp_path):
    _, _, clean = _staging_blocks()
    for call in clean:
        output = _bash(tmp_path, 'push_staged_clean() { printf "%s\\n" "$@"; }\n' + call)
        assert set(DERIVED_PATHS) <= set(output.splitlines())


def test_research_preparation_precedes_each_generation_proof():
    steps = _steps()
    build = steps['build Government Revenue projection']['run']
    assert build.index('build_government_revenue --live-materialization') < build.index('prepare_candidate_research_state')
    retry = _commit_run()[_commit_run().index('while push_attempt; do'):]
    producer = retry.index('build_government_revenue --live-materialization')
    research = retry.index('prepare_candidate_research_state')
    witness = retry.index('govrev_candidate_proof.py verify')
    reproof = retry.index('govrev_candidate_proof.py prove')
    assert producer < research < witness < reproof
    assert 'prepare_candidate_research_state' not in retry[witness:]
    assert 'build_government_revenue --live-materialization' not in retry[witness:]
    guard = steps['stage reviewed source guards']['run']
    assert 'candidate_projection_state.json' in guard
    assert 'scripts.build_government_revenue_research_state --root . --generated-at "$generated_at"' in guard
    assert 'candidate_issuance_log' not in _commit_run()


def test_existing_proof_budgets_size_and_bash_syntax_remain_armed():
    doc = yaml.safe_load(WORKFLOW.read_text())
    assert doc['jobs']['refresh']['timeout-minutes'] == 90
    run = _commit_run()
    assert 'PUSH_MAX_ATTEMPTS=2' in run and 'PUSH_BUDGET_SECS=2700' in run
    assert 'GOVREV_REPROOFS=0' in run and '[ "$GOVREV_REPROOFS" -ge 1 ]' in run
    assert 'GOVREV_REPROOFS=$((GOVREV_REPROOFS + 1))' in run
    assert 'GOVREV_CANDIDATE_PROOF_FATAL: "1"' in WORKFLOW.read_text()
    assert 'govrev_candidate_proof.py verify --committed' in run
    for job in doc['jobs'].values():
        for step in job.get('steps', []):
            if 'run' in step:
                assert len(step['run']) <= 20563
                result = subprocess.run(['/bin/bash', '-n'], input=step['run'], text=True, capture_output=True)
                assert result.returncode == 0, result.stderr


def test_consumer_source_changes_trigger_the_existing_lane_without_output_loop():
    doc = yaml.safe_load(WORKFLOW.read_text())
    triggers = doc.get('on', doc.get(True))['push']['paths']
    assert 'scripts/build_government_revenue_research_state.py' in triggers
    assert 'research/GOVERNMENT_REVENUE_CANDIDATE_GRADER_PREREG.md' in triggers
    assert 'engine/company_intelligence/defense_profiles.py' in triggers
    assert 'engine/earnings_release/**' in triggers
    for path in DERIVED_PATHS:
        if path.endswith(('.js', '.css')):
            source = path.replace('site/', 'templates/', 1)
            if path == 'site/government-revenue-page.js':
                source += '.j2'
            if path == 'site/government-revenue-critical-theme.css':
                assert path not in triggers
                assert {'templates/theme.css', 'templates/product-nav-icons.css',
                        'templates/government-revenue-sbir.css',
                        'templates/government-revenue-investor.css',
                        'templates/government-revenue-theme-context.css',
                        'templates/government-revenue-parity.css'} <= set(triggers)
                continue
            assert source in triggers
        assert path not in triggers
