"""Read-only staging preparation; never invokes writer, provider or staging.

Checks the existing telemetry root mechanisms and retained complete peer cohort.
The positive resolver result is NOT provider admission or a public-page receipt.
"""
from pathlib import Path
from hashlib import sha256
import json
import os
import sys

repo = Path(sys.argv[1]).resolve()
runtime = Path(sys.argv[2]).resolve()
assert repo != runtime and repo.is_dir() and runtime.is_dir()
sys.path.insert(0, str(repo))
sys.dont_write_bytecode = True

def audit(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'subprocess.Popen',
                 'os.remove', 'os.rename', 'os.mkdir', 'os.rmdir', 'os.system'}:
        raise RuntimeError('read-only seam refused ' + event)
    if event == 'open':
        _, mode, flags = args
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or flags & (64 | 512 | 1024):
            raise RuntimeError('read-only seam refused write')

sys.addaudithook(audit)
from lib import ai_costs
from engine import provider_health
from engine.neuralweb import key_pool
from engine.press import desk_planner, validators, writer

for env in ('AI_COSTS_STATE_ROOT', 'METABOLISM_STATE_ROOT', 'PROVIDER_HEALTH_PATH', 'AI_COSTS_SHARD'):
    assert not os.environ.get(env), 'unexpected existing telemetry override: ' + env
paths = {
    'usage': ('data/ai_costs/usage.jsonl', ai_costs._write_ledger_path),
    'health': ('data/ai_costs/provider_health.jsonl', provider_health.health_path),
    'key_pool': ('data/metabolism/key_ledger.jsonl', key_pool._ledger_path),
}
def digest(p):
    return sha256(p.read_bytes()).hexdigest()
before = {rel: digest(runtime/rel) for rel, _ in paths.values()}
defaults = {k: str(fn()) for k, (_, fn) in paths.items()}
assert all(Path(v).is_relative_to(repo) for v in defaults.values())
os.environ['AI_COSTS_STATE_ROOT'] = str(runtime)
os.environ['METABOLISM_STATE_ROOT'] = str(runtime)
resolved = {k: str(fn()) for k, (_, fn) in paths.items()}
assert all(Path(resolved[k]) == runtime/rel for k, (rel, _) in paths.items())

base = repo/'research/agentic_media/public_intelligence_20261011'
phase = base/'usda_research_intake_phase/planner_preflight_20261014_1507'
slot = json.loads((phase/'selected_slot.json').read_text())
cfg = desk_planner.load_config(repo)
assert cfg['cutover'] is False
original_records = [base/'initial_stage.json', base/'research_stage.json',
                    runtime/'data/press/staging/press-official-cd2747adeed2.json',
                    runtime/'data/press/staging/press-research_desk-2026-10-13-6baf3247f154.json']
cohort = []
for p in original_records:
    obj = json.loads(p.read_bytes())
    assert isinstance(obj.get('draft'), dict) and obj['draft'].get('body_html')
    peer_path = runtime/'data/press/staging'/f"{obj['id']}.json"
    if peer_path.exists():
        peer = json.loads(peer_path.read_bytes())
        assert peer['status'] == 'quarantined'
        for field in ('draft', 'slot', 'attempts', 'validator_report'):
            assert peer.get(field) == obj.get(field), 'retained peer changed: ' + field
    cohort.append({'id': obj['id'], 'path': str(p), 'sha256': digest(p),
                   'draft_sha256': sha256(json.dumps(obj['draft'], sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                   'present_in_runtime': peer_path.is_file()})
assert len({r['id'] for r in cohort}) == 4
assert not (runtime/'data/press/staging'/f"{slot['id']}.json").exists()
for row in cohort:
    obj=json.loads(Path(row['path']).read_bytes())
    assert not set(obj.get('sources',[])) & set(slot['sources'])
assert slot['story']['tickers'] == [] and slot['story']['published_at']=='2026-10-09T16:00:00Z'
system, prompt = writer.build_prompt(slot, cfg)
estimate = writer.estimate_tokens(system) + writer.estimate_tokens(prompt) + int(cfg['llm']['max_tokens'])
state = writer.RunState(token_budget=24000, breaker_threshold=1)
assert state.can_start(estimate)
assert before == {rel: digest(runtime/rel) for rel, _ in paths.values()}
assert all(row['sha256'] == digest(Path(row['path'])) for row in cohort)
missing = [r['id'] for r in cohort if not r['present_in_runtime']]
peers = validators.staged_peers(runtime, cfg, exclude_id=slot['id'])
remaining = ['current public report acceptance', 'fresh exact source/slot/input/writer-state fence']
if missing:
    remaining.append('complete preserved peer cohort at validation root')
else:
    assert len(peers) >= 4, 'complete retained cohort must be visible to the validator'
print(json.dumps({'default_paths_wrong_for_original_history': defaults,
                  'existing_override_paths_pass': resolved,
                  'preserved_histories': before, 'cohort': cohort,
                  'runtime_missing_retained_peers': missing,
                  'validator_peer_count': len(peers),
                  'slot_id': slot['id'], 'slot_sha256': digest(phase/'selected_slot.json'),
                  'configured_token_budget': 24000, 'estimated_reservation': estimate,
                  'budget_is_estimate_not_billing_or_hard_cap': True,
                  'single_provider_attempt_required': True, 'max_regenerations_required': 0,
                  'provider_calls': 0, 'runtime_writes': 0,
                  'ready_for_provider': False,
                  'remaining_gates': remaining,
                  'publication': False}, indent=2))
