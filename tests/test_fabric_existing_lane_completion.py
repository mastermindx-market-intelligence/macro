"""An existing Fabric worktree returns a commission, not a production release.

Synthetic local repositories only. These tests never contact GitHub, a broker,
a provider, an installed lane, or production. Tool admission stays separate.
"""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'fabric_existing_lane_guard', ROOT / '.claude/hooks/ship_loop_guard.py')
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class ExistingLaneCompletion(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.home = self.directory / 'home'
        self.root = self.home / 'lanes/wt/original-run'
        source = self.directory / 'source'
        source.mkdir()
        def git(*args):
            subprocess.run(['git', '-C', str(source), *args], check=True,
                           capture_output=True, timeout=10)
        git('init', '-b', 'main')
        git('config', 'user.name', 'Fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        git('commit', '--allow-empty', '-m', 'fixture')
        self.root.parent.mkdir(parents=True)
        git('worktree', 'add', '-b', 'claude/fixture-repair', str(self.root))
        self.state_path = self.directory / 'guard-state.json'
        self.scope_env = {
            'REMOTE_SUB_RUN_ID': 'repair-r2',
            'POOL_USAGE_RUN_ID': 'repair-r2',
            'POOL_OUTCOME_FILE': str(self.home / 'lanes/ext/lanes/repair-r2.provider.json'),
            'POOL_LEASE_ID': 'fixture-lease',
            'POOL_ORCHESTRATOR_ID': 'fixture-root',
            'POOL_PARENT_RUN_ID': 'fixture-parent',
            'LANE_REMOTE_HOST': 'fixture-host',
            'POOL_TASK_COMPLEXITY': 'C0_MECHANICAL',
            'POOL_TASK_CLASS': 'mechanical',
        }
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('POOL_', 'FABRIC_', 'REMOTE_SUB_', 'LANE_'))}
        env.update(self.scope_env)
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = mock.patch.object(Path, 'home', return_value=self.home)
        patcher.start(); self.addCleanup(patcher.stop)

    def start(self):
        output = io.StringIO()
        with redirect_stdout(output):
            GUARD._session_start(self.root, self.state_path, {'source': 'startup'})
        return output.getvalue(), json.loads(self.state_path.read_text())

    def test_existing_linked_lane_captures_return_scope_not_new_admission(self):
        text, state = self.start()
        self.assertTrue(state['root_admitted'])
        self.assertEqual(state['fabric_completion_scope']['run_id'], 'repair-r2')
        self.assertEqual(state['fabric_completion_scope']['workspace'], str(self.root))
        self.assertIn('FABRIC BOUNDED WORKER', text)
        self.assertNotIn('MANDATORY SHIP LOOP', text)
        self.assertIn('not acceptance', text)

    def test_stop_returns_without_git_delivery_network_or_wait_loop(self):
        self.start()
        with mock.patch.object(GUARD, '_fingerprint', side_effect=AssertionError('delivery scan')):
            with mock.patch.object(GUARD, '_get_json', side_effect=AssertionError('network')):
                output = io.StringIO()
                with redirect_stdout(output):
                    GUARD._stop(self.root, self.state_path,
                                {'last_assistant_message': 'STATUS: PARTIAL; parent review needed'})
        self.assertNotIn('"decision": "block"', output.getvalue())
        self.assertIn('not acceptance', output.getvalue())
        self.assertEqual(json.loads(self.state_path.read_text()).get('block_count', 0), 0)

    def test_legacy_root_without_parent_still_returns_to_its_existing_controller(self):
        os.environ.pop('POOL_PARENT_RUN_ID')
        os.environ['POOL_TASK_CLASS'] = ''
        text, state = self.start()
        self.assertIn('FABRIC BOUNDED WORKER', text)
        self.assertIsNone(state['fabric_completion_scope']['parent_run_id'])
        self.assertNotIn('parent identity verified', text)

    def test_parent_delivery_session_does_not_inherit_worker_completion(self):
        os.environ.pop('REMOTE_SUB_RUN_ID')
        text, state = self.start()
        self.assertNotIn('fabric_completion_scope', state)
        self.assertIn('MANDATORY SHIP LOOP', text)
        with mock.patch.object(GUARD, '_fingerprint', side_effect=RuntimeError('PARENT_SHIP_CHAIN')):
            with self.assertRaisesRegex(RuntimeError, 'PARENT_SHIP_CHAIN'):
                GUARD._stop(self.root, self.state_path, {})

    def test_changed_run_or_lease_cannot_reuse_saved_scope(self):
        self.start()
        for field in ('REMOTE_SUB_RUN_ID', 'POOL_LEASE_ID', 'POOL_ORCHESTRATOR_ID'):
            with self.subTest(field=field), mock.patch.dict(os.environ, {field: 'another'}):
                with mock.patch.object(GUARD, '_fingerprint', side_effect=RuntimeError('PARENT_SHIP_CHAIN')):
                    with self.assertRaisesRegex(RuntimeError, 'PARENT_SHIP_CHAIN'):
                        GUARD._stop(self.root, self.state_path, {})

    def test_missing_binding_or_invalid_output_refuses_scope(self):
        for field in ('REMOTE_SUB_RUN_ID', 'POOL_USAGE_RUN_ID', 'POOL_OUTCOME_FILE',
                      'POOL_LEASE_ID', 'POOL_ORCHESTRATOR_ID', 'LANE_REMOTE_HOST',
                      'POOL_TASK_COMPLEXITY'):
            with self.subTest(field=field), mock.patch.dict(os.environ, {field: ''}):
                self.assertIsNone(GUARD._fabric_existing_lane_completion(self.root))
        for output in ('/tmp/repair-r2.provider.json',
                       str(self.home / 'lanes/ext/lanes/another.provider.json')):
            with self.subTest(output=output), mock.patch.dict(os.environ, {'POOL_OUTCOME_FILE': output}):
                self.assertIsNone(GUARD._fabric_existing_lane_completion(self.root))

    def test_operator_or_frontier_scope_is_never_downgraded(self):
        for patch in ({'POOL_TASK_CLASS': 'orchestration'},
                      {'POOL_TASK_CLASS': 'domain_orchestration'},
                      {'POOL_TASK_COMPLEXITY': 'C3_FRONTIER_JUDGMENT'},
                      {'FABRIC_OPERATOR_CAPSULE': 'present'},
                      {'FABRIC_OPERATOR_CAPABILITY': 'present'}):
            with self.subTest(patch=patch), mock.patch.dict(os.environ, patch):
                self.assertIsNone(GUARD._fabric_existing_lane_completion(self.root))

    def test_outside_lane_and_symlink_are_not_a_worker_scope(self):
        self.assertIsNone(GUARD._fabric_existing_lane_completion(self.directory / 'source'))
        alias = self.root.parent / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.assertIsNone(GUARD._fabric_existing_lane_completion(alias))

    def test_custody_failure_is_not_repaired_by_completion_metadata(self):
        with mock.patch.object(GUARD, '_delivery_root_admission', return_value=(False, 'fixture quarantine')):
            text, state = self.start()
        self.assertFalse(state['root_admitted'])
        self.assertNotIn('fabric_completion_scope', state)
        self.assertNotIn('FABRIC BOUNDED WORKER', text)

    def test_stop_requires_fresh_source_admission(self):
        self.start()
        with mock.patch.object(GUARD, '_delivery_root_admission', return_value=(False, 'changed root')):
            with mock.patch.object(GUARD, '_fingerprint', side_effect=RuntimeError('PARENT_SHIP_CHAIN')):
                with self.assertRaisesRegex(RuntimeError, 'PARENT_SHIP_CHAIN'):
                    GUARD._stop(self.root, self.state_path, {})

    def test_hold_wrapper_delegates_resumed_worker_without_parent_probes(self):
        self.start()
        state = json.loads(self.state_path.read_text())
        state['last_blocker'] = 'unmerged'
        self.state_path.write_text(json.dumps(state))
        spec = importlib.util.spec_from_file_location(
            'fixture_hold_wrapper', ROOT / 'scripts/ship_loop_hold_wrapper.py')
        wrapper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wrapper)
        payload = {'cwd': str(self.root), 'hook_event_name': 'Stop',
                   'last_assistant_message': 'STATUS: PASS; parent owns release'}
        with mock.patch.object(GUARD, '_state_path', return_value=self.state_path):
            with mock.patch.object(wrapper, '_git', side_effect=AssertionError('PARENT_HOLD_PROBE')):
                self.assertIsNone(wrapper._hold_probe(GUARD, payload))
        with mock.patch.dict(os.environ, {'POOL_LEASE_ID': 'another-lease'}):
            with mock.patch.object(GUARD, '_state_path', return_value=self.state_path):
                with mock.patch.object(wrapper, '_git', side_effect=RuntimeError('PARENT_HOLD_PROBE')):
                    with self.assertRaisesRegex(RuntimeError, 'PARENT_HOLD_PROBE'):
                        wrapper._hold_probe(GUARD, payload)


if __name__ == '__main__':
    unittest.main()
