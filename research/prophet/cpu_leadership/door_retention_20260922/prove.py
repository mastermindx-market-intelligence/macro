"""Exact Git inputs -> existing identity/intake/core; no canonical writes."""
from pathlib import Path, PurePosixPath
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import argparse, importlib.util, json, re, subprocess, sys, tempfile, time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from engine.us_candidate_episode import (load_candidate_episode_store_snapshot,
    reconcile_observations, canonical_json, _ordinary_source_key, DEFAULT_DEFINITION_ERA)
from engine.us_candidate_episode_intake import load_identity_spine, door_observations
from scripts import reconcile_us_candidate_episodes as writer


def verify_fixture_inputs(expected, bodies):
    """An accepted-source control is exact evidence, never a same-date substitute."""
    if not isinstance(expected, dict) or not isinstance(bodies, dict) or set(expected) != set(bodies):
        raise ValueError('accepted source set must be exact')
    if not 1 <= len(bodies) <= 60:
        raise ValueError('accepted source count bound exceeded')
    total = 0
    for path, raw in bodies.items():
        parsed = PurePosixPath(path)
        if (parsed.is_absolute() or '..' in parsed.parts or parsed.as_posix() != path
                or not path.startswith('data/')):
            raise ValueError('accepted source path is not a canonical data path')
        if not isinstance(raw, bytes):
            raise ValueError('accepted source content must be bytes')
        total += len(raw)
        if total > 256 * 1024 * 1024:
            raise ValueError('accepted source byte bound exceeded')
        if expected[path] != 'sha256:' + sha256(raw).hexdigest():
            raise ValueError('accepted source hash mismatch: ' + path)
    return dict(expected)


def verify_full_lineage(submitted, events, suppressions, *,
                        previous_events=(), previous_suppressions=()):
    """Verify source retention in the FULL computed output, without assigning policy.

    Canonical identity and serialization remain owned by the episode module.
    The caller supplies the unmodified nonwriting builder's event/suppression lists.
    An isolated Door-core result is not an acceptable substitute for these lists.
    """
    owned = {}
    for row in (*events, *suppressions):
        key = _ordinary_source_key(row)
        if key in owned:
            raise ValueError('duplicate full-writer source ownership')
        owned[key] = row
    required = {_ordinary_source_key(row): row for row in submitted}
    for key, row in required.items():
        if key not in owned:
            raise ValueError('submitted source is missing from full-writer output')
        if owned[key].get('source_receipt') != row.get('source_receipt'):
            raise ValueError('full-writer source receipt mismatch')
    prior = (*previous_events, *previous_suppressions)
    full_bytes = {canonical_json(row) for row in (*events, *suppressions)}
    if any(canonical_json(row) not in full_bytes for row in prior):
        raise ValueError('prior immutable record changed in full-writer output')
    prior_keys = {_ordinary_source_key(row) for row in prior}
    new_keys = set(required) - prior_keys
    event_keys = {_ordinary_source_key(row) for row in events}
    suppression_keys = {_ordinary_source_key(row) for row in suppressions}
    case_fields = ('source_system', 'source_schema', 'source_event_id', 'source_receipt',
                   'event_type', 'episode_id', 'occurred_at', 'known_at',
                   'recorded_at', 'observation_session', 'reason')
    cases = [{field: owned[key].get(field) for field in case_fields}
             for key in sorted(required)
             if key[0] == 'doors' and key[2].rsplit(':', 1)[-1] in ('AMD', 'INTC', 'ARM', 'MU')]
    return {'submitted': len(required), 'all_accounted': True,
            'source_receipts_match': True, 'prior_records_preserved': True,
            'new_events': len(new_keys & event_keys),
            'new_suppressions': len(new_keys & suppression_keys),
            'motivating_cases': cases, 'entry_authority_changed': False,
            'scope': 'exact submitted source keys in the complete nonwriting output; not trades'}


def observe_full_writer(root, clock, submitted, previous_events, previous_suppressions):
    """Observe one real report call; never substitute its arguments, inputs or result."""
    from unittest.mock import patch
    original = writer._load_and_build
    captured = []
    def observe(*args, **kwargs):
        result = original(*args, **kwargs)
        captured.append(result)
        return result
    with patch.object(writer, '_load_and_build', side_effect=observe):
        receipt = writer.reconcile(repo_root=root, nightly=False, replay=False,
                                   recorded_at=clock, correction_path=None)
    if len(captured) != 1 or captured[0][0] != receipt:
        raise ValueError('full-writer receipt is not bound to one observed computation')
    if receipt.get('mode') != 'report' or receipt.get('durable_write') is not False:
        raise ValueError('full-writer proof must remain nonwriting report mode')
    lineage = verify_full_lineage(submitted, captured[0][2], captured[0][3],
        previous_events=previous_events, previous_suppressions=previous_suppressions)
    return receipt, lineage


def proof_exit_code(full_writer):
    """A diagnostic process returning a refusal must not be mistaken for a pass."""
    return 0 if full_writer.get('status') in ('passed', 'not_requested') else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--source-ref', default='758b052ff0278e9842fd1b392e0b04617124d1bb')
    parser.add_argument('--full-writer', action='store_true', help='Also run the nonwriting report against all pinned source files')
    parser.add_argument('--accepted-input-ref', help='Exact historical source control; must match every accepted generation input hash')
    args = parser.parse_args(argv)
    REF = args.source_ref
    if args.accepted_input_ref and (not args.full_writer or not re.fullmatch(r'[0-9a-f]{40}', args.accepted_input_ref)):
        parser.error('accepted-input-ref requires full-writer and an immutable commit')
    if not re.fullmatch(r'[0-9a-f]{40}', REF):
        parser.error('source-ref must be an immutable commit')
    OUT = args.out.resolve()
    OWNER_PATHS = ('scripts/reconcile_us_candidate_episodes.py',
        'engine/us_candidate_episode.py', 'engine/us_candidate_episode_intake.py',
        'engine/session_digest.py', 'engine/ledger_lane.py', 'lib/nyse_calendar.py')
    implementation_sources = {p: sha256((ROOT / p).read_bytes()).hexdigest() for p in OWNER_PATHS}
    for owner in OWNER_PATHS[1:]:
        frozen = subprocess.check_output(['git', '-C', str(ROOT), 'show', REF + ':' + owner])
        if frozen != (ROOT / owner).read_bytes():
            raise SystemExit(f'core owner differs from source ref: {owner}')
    if OUT.is_relative_to(ROOT / 'data') or OUT.is_relative_to(ROOT / 'site'):
        raise SystemExit('Report output must not target canonical data/site paths')
    receipts = []
    def read(path, source_ref=None):
        source_ref = source_ref or REF
        body = subprocess.check_output(['git', '-C', str(ROOT), 'show', source_ref + ':' + path])
        receipts.append({'source_ref': source_ref, 'path': path, 'sha256': sha256(body).hexdigest(), 'bytes': len(body)})
        return body

    def digest_files(root):
        return {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
                for p in root.rglob('*') if p.is_file()}

    clock = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='door-retention-proof-') as temp:
        root = Path(temp)
        store_rel = 'data/us_prophet_rank/episodes'
        store = root / store_rel
        head_bytes = read(store_rel + '/HEAD.json')
        head = json.loads(head_bytes)
        generation = head['generation_id']
        assert generation.startswith('peg:') and len(generation) == 68
        prefix = store_rel + '/generations/' + generation
        manifest_bytes = read(prefix + '/manifest.json')
        manifest = json.loads(manifest_bytes)
        def put(path, body):
            output = root / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(body)
        put(store_rel + '/HEAD.json', head_bytes)
        put(prefix + '/manifest.json', manifest_bytes)
        total = 0
        for rel in manifest['files']:
            assert not PurePosixPath(rel).is_absolute() and '..' not in PurePosixPath(rel).parts
            body = read(prefix + '/' + rel); total += len(body)
            assert total < 100 * 1024 * 1024
            put(prefix + '/' + rel, body)
        accepted_control = None
        if args.accepted_input_ref:
            accepted = load_candidate_episode_store_snapshot(store).generation.receipt
            accepted_bodies = {path: read(path, args.accepted_input_ref)
                               for path in accepted['source_hashes']}
            matched = verify_fixture_inputs(accepted['source_hashes'], accepted_bodies)
            for path, raw in accepted_bodies.items():
                put(path, raw)
            # A frozen incumbent with newest-date intake must first reproduce this
            # accepted generation. This is an isolated control, NOT a rollback.
            baseline_path = root / '_incumbent_writer.py'
            baseline_path.write_bytes(read('scripts/reconcile_us_candidate_episodes.py'))
            spec = importlib.util.spec_from_file_location('retention_accepted_incumbent', baseline_path)
            incumbent = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(incumbent)
            before_baseline = digest_files(root)
            baseline_receipt = incumbent.reconcile(repo_root=root, nightly=False, replay=False,
                                                  recorded_at=clock, correction_path=None)
            same = {key: baseline_receipt[key] == accepted[key]
                    for key in ('ledger_sha256', 'projection_hashes', 'source_hashes')}
            if not all(same.values()) or baseline_receipt['counts']['appended_events'] != 0:
                raise RuntimeError('accepted-source baseline did not reproduce its saved generation')
            assert digest_files(root) == before_baseline
            accepted_control = {'input_ref': args.accepted_input_ref, 'hash_matched_sources': matched,
                                'baseline_matches': same, 'baseline_appended_events': 0,
                                'scope': 'historical accepted-source control, NOT current-source acceptance'}
            # The ONLY controlled input change is the present pinned Door ledger.
            # Other accepted files remain byte-identical; no current source is rewritten.
            put('data/prophet_doors/flags.jsonl', read('data/prophet_doors/flags.jsonl'))
        else:
            for path in ['data/reference/security_master.parquet', 'data/reference/vendor_aliases.parquet',
                         'data/prophet_doors/flags.jsonl']:
                put(path, read(path))
        if args.full_writer and not args.accepted_input_ref:
            source_paths = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', REF,
                '--', 'data/us_prophet_rank/candidates', 'data/us_prophet_rank/episode_inputs/turn_watch',
                'data/entry_radar/forward.parquet'], text=True).splitlines()
            # Only the owner-selected newest TURN WATCH envelope and existing archive
            # parts are supplied. No producer computation or historical substitution.
            turn_paths = sorted(p for p in source_paths if p.endswith('.json')
                                and p.startswith('data/us_prophet_rank/episode_inputs/turn_watch/'))
            chosen = [p for p in source_paths if p.endswith('.parquet')]
            if turn_paths:
                chosen.append(turn_paths[-1])
            if len(chosen) > 60:
                raise RuntimeError('source file bound exceeded')
            for path in chosen:
                body = read(path); total += len(body)
                if total > 256 * 1024 * 1024:
                    raise RuntimeError('fixture byte bound exceeded')
                put(path, body)
        original = digest_files(root)
        snapshot = load_candidate_episode_store_snapshot(store)
        saved = snapshot.generation
        spine = load_identity_spine(root / 'data')
        door_path = root / 'data/prophet_doors/flags.jsonl'
        baseline = door_observations(door_path, spine)
        candidate = writer._door_backlog_intake(door_path, spine, recorded_at=clock,
            existing_events=saved.events, existing_suppressions=saved.suppressions)
        prior_keys = {_ordinary_source_key(row) for row in (*saved.events, *saved.suppressions)}
        result = reconcile_observations(saved.events, candidate.observations,
            recorded_at=clock, definition_era=DEFAULT_DEFINITION_ERA,
            existing_suppressions=saved.suppressions)
        new_supps = writer._merge_suppressions(saved.suppressions,
            [*candidate.suppressions, *result.suppressions], events=result.events, recorded_at=clock)
        all_keys = {_ordinary_source_key(row) for row in (*result.events, *new_supps)}
        submitted = {_ordinary_source_key(row) for row in (*candidate.observations, *candidate.suppressions)}
        assert submitted <= all_keys
        old_events = {canonical_json(row) for row in saved.events}
        assert old_events <= {canonical_json(row) for row in result.events}
        old_supps = {canonical_json(row) for row in saved.suppressions}
        assert old_supps <= {canonical_json(row) for row in new_supps}
        again = writer._door_backlog_intake(door_path, spine, recorded_at=clock,
            existing_events=result.events, existing_suppressions=new_supps)
        repeat = reconcile_observations(result.events, again.observations,
            recorded_at=clock, definition_era=DEFAULT_DEFINITION_ERA, existing_suppressions=new_supps)
        assert not repeat.new_events
        assert digest_files(root) == original
        def name(row): return str(row.get('source_event_id', '')).rsplit(':', 1)[-1]
        targets = []
        for row in (*result.new_events, *new_supps):
            if row.get('source_system') != 'doors' or _ordinary_source_key(row) in prior_keys:
                continue
            if name(row) in ('AMD','INTC','ARM','MU'):
                targets.append({k:row.get(k) for k in ['source_event_id','source_receipt','event_type',
                    'known_at','occurred_at','recorded_at','observation_session','reason','episode_id']})
        full_writer = {'status': 'not_requested'}
        if args.full_writer:
            before_full = digest_files(root)
            try:
                full_receipt, lineage = observe_full_writer(root, clock,
                    [*candidate.observations, *candidate.suppressions], saved.events, saved.suppressions)
                full_writer = {'status': 'passed', 'receipt': full_receipt, 'lineage': lineage}
            except Exception as exc:
                full_writer = {'status': 'refused', 'error_type': type(exc).__name__, 'error': str(exc)}
                # Frozen fixture stays unchanged; a separate read identifies conflicting
                # source keys rather than using catch-and-ignore to claim acceptance.
                _identities, batches = writer._load_intakes(root / 'data', allow_degraded_identity=False,
                    recorded_at=clock, existing_events=saved.events, existing_suppressions=saved.suppressions)
                old_by = {_ordinary_source_key(row): row for row in (*saved.events, *saved.suppressions)}
                conflicts = []
                for batch in batches:
                    for row in (*batch.observations, *batch.suppressions):
                        old = old_by.get(_ordinary_source_key(row))
                        if old is not None and old.get('source_receipt') != row.get('source_receipt'):
                            conflicts.append({'source_system': row['source_system'],
                                'source_event_id': row['source_event_id'],
                                'committed_receipt': old.get('source_receipt'),
                                'input_receipt': row.get('source_receipt')})
                full_writer['receipt_conflicts'] = conflicts
            full_writer['fixture_unchanged'] = digest_files(root) == before_full
            assert full_writer['fixture_unchanged']
        assert implementation_sources == {p: sha256((ROOT / p).read_bytes()).hexdigest() for p in OWNER_PATHS}
        report = {'source_ref':REF,'ingestion_clock':clock,'source_generation':generation,
            'implementation_sources_sha256':implementation_sources,
            'full_writer':full_writer, 'accepted_source_control':accepted_control,
            'source_generation_recorded_at':saved.receipt['recorded_at'],
            'baseline_latest_only':len(baseline.observations)+len(baseline.suppressions),
            'candidate_completed_unique':len(submitted),'previously_owned':len(submitted & prior_keys),
            'newly_accounted':len(submitted - prior_keys),'new_event_count':len(result.new_events),
            'new_suppression_count':len(new_supps)-len(saved.suppressions),
            'new_suppression_reasons':dict(Counter(r['reason'] for r in new_supps if _ordinary_source_key(r) not in prior_keys)),
            'motivating_cases':targets,'repeat_new_events':len(repeat.new_events),
            'all_submitted_have_owner':True,'original_events_and_suppressions_unchanged':True,
            'all_input_files_unchanged':True,'canonical_writes':False,'provider_requests':False,
            'plan_or_trade_authority_changed':False,'performance_validation':False,
            'limitations':['Nonwriting intake/core proof only; not a scheduled production run.',
                           'Stored event dates are not first publication timestamps.',
                           'Existing TURN WATCH and candidate sources are not rebuilt.'],
            'sources':receipts,'elapsed_seconds':round(time.monotonic()-started,3)}
        OUT.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k not in ('sources', 'full_writer')},indent=2))
        print('FULL_WRITER', full_writer['status'], full_writer.get('error', ''),
              'receipt_conflicts', len(full_writer.get('receipt_conflicts', [])))

    return proof_exit_code(full_writer)


if __name__ == '__main__':
    raise SystemExit(main())
