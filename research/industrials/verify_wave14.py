"""Research-handoff integrity checks only; no application, rights or deployment tests.

Read-only and standard-library only. Supports a flat portable packet or the
canonical repository layout. Never invokes planned product functions or tools.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
MANIFEST = 'WAVE14_HANDOFF_MANIFEST.json'
EXPECTED = {f'IND-D{x:02}' for x in range(1, 31)} | {f'IND-R2{x:02}' for x in range(1, 19)} | {f'IND-SF{x:02}' for x in range(1, 9)}
FLAGS = {'can_rank', 'can_gate', 'can_size', 'can_originate', 'can_open_entry'}


def git_blob(body: bytes) -> str:
    return hashlib.sha1(f'blob {len(body)}\0'.encode() + body).hexdigest()


def locate(record: dict) -> Path:
    for candidate in (ROOT / record['portable'], ROOT.parent.parent / record['path']):
        if candidate.is_file():
            return candidate
    raise ValueError('required_artifact_missing:' + record['path'])


def verify_files(manifest: dict) -> None:
    for record in manifest['files']:
        body = locate(record).read_bytes()
        if (len(body) != record['bytes'] or git_blob(body) != record['git_blob']
                or hashlib.sha256(body).hexdigest() != record['sha256']):
            raise ValueError('artifact_identity_mismatch:' + record['path'])


def verify_inventory(trace: dict) -> None:
    ids = [identifier for task in trace['tasks'] for identifier in task['requirements']]
    if len(ids) != 56 or len(set(ids)) != 56 or set(ids) != EXPECTED:
        raise ValueError('requirement_inventory_mismatch')
    if any(task['test_status'] != 'NOT_EXECUTED' for task in trace['tasks']):
        raise ValueError('unsupported_product_test_claim')


class HandoffIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads((ROOT / MANIFEST).read_text(encoding='utf-8'))
        cls.by_role = {r['role']: r for r in cls.m['files']}
        cls.addendum = locate(cls.by_role['mandatory_addendum']).read_text(encoding='utf-8')
        cls.packet = locate(cls.by_role['master_packet']).read_text(encoding='utf-8')
        cls.trace = json.loads(locate(cls.by_role['traceability']).read_text(encoding='utf-8'))

    def test_01_exact_file_identities(self):
        verify_files(self.m)

    def test_02_research_only_and_not_dispatched(self):
        self.assertTrue(self.m['research_only'])
        self.assertFalse(self.m['is_native_contract'])
        self.assertEqual(self.m['packet_state'], 'PREPARED_FOR_PLACEMENT')
        self.assertFalse(self.m['fable_dispatched'])
        self.assertFalse(self.m['implementation_started'])
        self.assertIsNone(self.m['assigned_receiver'])
        self.assertIsNone(self.m['accepted_shared_release'])

    def test_03_preserved_56_requirements(self):
        verify_inventory(self.trace)

    def test_04_nine_tasks_and_existing_dependencies(self):
        tasks = self.trace['tasks']
        sequence = self.m['controlling_task_order']
        self.assertEqual(sequence, [f'T{x:02}' for x in range(1, 10)])
        position = {key: idx for idx, key in enumerate(sequence)}
        self.assertEqual({t['id'] for t in tasks}, set(sequence))
        for task in tasks:
            for dependency in task['depends_on']:
                self.assertLess(position[dependency], position[task['id']])
        self.assertIn('T04', next(t for t in tasks if t['id'] == 'T05')['depends_on'])

    def test_05_seven_bounded_amendments(self):
        ids = re.findall(r'^### (A14-\d{2}) ', self.addendum, flags=re.M)
        self.assertEqual(ids, [f'A14-{x:02}' for x in range(1, 8)])

    def test_06_shared_routes_supersede_old_get(self):
        for route in ('/api/themes/v1/research/query', '/api/themes/v1/research/evidence'):
            self.assertIn(route, self.addendum)
        self.assertIn('Replace the original T07 candidate GET', self.addendum)
        self.assertIn('not a separate external routing', self.addendum)

    def test_07_single_aggregator_and_independent_financial_region(self):
        self.assertIn('templates/_basket_intelligence_mounts.html.j2', self.addendum)
        self.assertIn('outside `#app`', self.addendum)
        self.assertIn('Missing (c) must not suppress valid (a) or (b)', self.addendum)
        self.assertIn('legacy projector', self.addendum)

    def test_08_case_and_library_preservation(self):
        for token in ('Exponent', 'Pentair', '24-investor-task/six-dossier', 'NOT_EXECUTED'):
            self.assertIn(token, self.packet)
        for wave in range(2, 10):
            self.assertIn(f'INDUSTRIALS_WAVE{wave}_', self.packet)
        self.assertIn('not a basket', self.packet)

    def test_09_owner_receipts_and_scoped_rights(self):
        for receipt in ('5809602368', '5808854275', '5808981293', '5808986207'):
            self.assertIn(receipt, self.packet)
        self.assertIn('government-authorship distinction', self.packet)
        self.assertIn('https://www.usa.gov/government-copyright', self.addendum)
        self.assertIn('https://www.copyright.gov/title17/92chap1.html', self.addendum)

    def test_10_assignment_and_no_trade_authority(self):
        self.assertIn('WAITING_CAPACITY / needs_placement', self.packet)
        self.assertIn('Mere discovery of this text is not deliberate delivery', self.packet)
        self.assertEqual(set(self.m['authority']), FLAGS)
        self.assertTrue(all(v is False for v in self.m['authority'].values()))

    def test_11_five_gates_stay_unproved(self):
        self.assertEqual(set(self.m['release_gates']), {f'G{x}' for x in range(1, 6)})
        self.assertTrue(all(x == 'PROOF_REQUIRED' for x in self.m['release_gates'].values()))
        self.assertIn('known-existing', self.packet)
        self.assertIn('next ordinary refresh', self.packet)
        self.assertIn('independent code/security review', self.packet)

    def test_12_tampered_digest_is_detected(self):
        altered = copy.deepcopy(self.m)
        altered['files'][0]['git_blob'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'artifact_identity_mismatch'):
            verify_files(altered)

    def test_13_dropped_requirement_is_detected(self):
        altered = copy.deepcopy(self.trace)
        altered['tasks'][0]['requirements'].pop()
        with self.assertRaisesRegex(ValueError, 'requirement_inventory_mismatch'):
            verify_inventory(altered)

    def test_14_false_test_execution_claim_is_detected(self):
        altered = copy.deepcopy(self.trace)
        altered['tasks'][0]['test_status'] = 'PASS'
        with self.assertRaisesRegex(ValueError, 'unsupported_product_test_claim'):
            verify_inventory(altered)


if __name__ == '__main__':
    unittest.main(verbosity=2)
