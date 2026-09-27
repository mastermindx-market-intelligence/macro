"""Research-plan integrity only; does not execute planned application functions."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
EXPECTED = {f'IND-D{x:02}' for x in range(1,31)} | {f'IND-R2{x:02}' for x in range(1,19)} | {f'IND-SF{x:02}' for x in range(1,9)}
FLAGS = {'can_rank','can_gate','can_size','can_originate','can_open_entry'}


def git_blob(body: bytes) -> str:
    return hashlib.sha1(f'blob {len(body)}\0'.encode()+body).hexdigest()


def find_spec(name: str) -> Path:
    options=(ROOT/'specifications'/name,
             ROOT.parent.parent/'docs'/'superpowers'/'specs'/name,
             ROOT/name)
    for p in options:
        if p.is_file():return p
    raise FileNotFoundError(name)


def find_plan(data: dict) -> Path:
    for p in (ROOT/data['plan_file'],ROOT.parent.parent/'docs'/'superpowers'/'plans'/data['plan_file']):
        if p.is_file(): return p
    raise FileNotFoundError(data['plan_file'])


def graph_valid(tasks: list[dict]) -> bool:
    graph={t['id']:set(t['depends_on']) for t in tasks}
    if len(graph)!=len(tasks):return False
    done=set()
    while len(done)<len(graph):
        newly={key for key,deps in graph.items() if key not in done and deps<=done}
        if not newly:return False
        done |= newly
    return True


class PlanIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'WAVE13_IMPLEMENTATION_TRACEABILITY.json').read_text())
        cls.plan=find_plan(cls.data).read_text()
        cls.rows=[{'requirement_id':rid, 'task':t['id'], 'test_file':t['test_file'], 'test_name':'test_'+rid.lower().replace('-','_'), 'status':t['test_status']} for t in cls.data['tasks'] for rid in t['requirements']]

    def test_01_research_boundary(self):
        for field in ('research_only','not_a_native_schema','not_a_queue'):
            self.assertIs(self.data[field],True)
        self.assertIs(self.data['implementation_started'],False)
        self.assertIs(self.data['fable_dispatched'],False)
        self.assertEqual(self.data['plan_status'],'PROPOSED_FOR_REVIEW')

    def test_02_exact_refs(self):
        self.assertEqual(self.data['carrier'],7789)
        for key in ('entry_head','procedure_pin','main_read_pin','foundation_candidate'):
            self.assertRegex(self.data[key],r'^[a-f0-9]{40}$')
            self.assertIn(self.data[key],self.plan)

    def test_03_original_blobs(self):
        for name,expected in self.data['original_blobs'].items():
            self.assertEqual(git_blob(find_spec(name).read_bytes()),expected)

    def test_04_all_requirements_exactly_once(self):
        rows=self.rows; ids=[x['requirement_id'] for x in rows]
        self.assertEqual(len(ids),56); self.assertEqual(len(set(ids)),56)
        self.assertEqual(set(ids),EXPECTED)

    def test_05_requirement_words_unchanged(self):
        original={}
        for name in self.data['original_blobs']:
            for line in find_spec(name).read_text().splitlines():
                m=re.match(r'\| (IND-(?:D\d{2}|R2\d{2}|SF\d{2})) \| (.*?) \| (.*?) \|',line)
                if m:original[m[1]]=(m[2],m[3])
        self.assertEqual(set(original),EXPECTED)
        # Definitions stay in the unchanged, hash-bound original specifications.
        for row in self.rows:
            self.assertTrue(all(original[row['requirement_id']]))

    def test_06_nine_tasks_dag(self):
        tasks=self.data['tasks']
        self.assertEqual({x['id'] for x in tasks},{f'T{i:02}' for i in range(1,10)})
        self.assertTrue(graph_valid(tasks))
        for t in tasks:self.assertIn(f"### {t['id']} — {t['title']}",self.plan)

    def test_07_crosswalk_parity(self):
        actual={m[1]:(m[2],m[3]) for m in re.finditer(r'^\| (IND-(?:D\d{2}|R2\d{2}|SF\d{2})) \| (T\d{2}) \| `([^`]+)` \|$',self.plan,re.M)}
        self.assertEqual(set(actual),EXPECTED)
        for r in self.rows:
            self.assertEqual(actual[r['requirement_id']],(r['task'],r['test_file']+'::'+r['test_name']))
            self.assertEqual(r['status'],'NOT_EXECUTED')

    def test_08_gates_unproven(self):
        self.assertIsNone(self.data['accepted_foundation_release'])
        self.assertEqual(set(self.data['release_gates'].values()),{'UNPROVEN','NOT_EXECUTED'})
        self.assertEqual(set(self.data['authority']),FLAGS)
        self.assertTrue(all(v is False for v in self.data['authority'].values()))

    def test_09_syntax_of_proposed_examples(self):
        blocks=re.findall(r'```python\n(.*?)\n```',self.plan,re.S)
        self.assertEqual(len(blocks),9)
        for block in blocks:ast.parse(block)

    def test_10_each_task_deliverable_and_test_cycle(self):
        for i in range(1,10):
            start=self.plan.index(f'### T{i:02} —')
            end=self.plan.find('\n### T',start+5)
            if end<0:end=self.plan.index('\n## 6.',start)
            section=self.plan[start:end]
            for token in ('**Files:**','**Consumes:**','**Produces:**','- [ ]','```python','Commit' if i==1 else ''):
                if token:self.assertIn(token,section)
            self.assertIn('test_',section)

    def test_11_no_placeholder_claim(self):
        for pattern in (r'\bTBD\b',r'\bTODO\b',r'fill in details',r'implement later',r'add appropriate error handling'):
            self.assertIsNone(re.search(pattern,self.plan,re.I))
        self.assertIn('No product code goes onto this research branch',self.plan)
        self.assertIn('NOT_EXECUTED',self.plan)

    def test_12_next_run_and_cross_sector_obligations(self):
        for word in ('next ordinary refresh','mixed-issuer preservation','Semiconductor, Robotics, existing Wire','No ticker branches','required_basis_unknown','same_outcome_distinct_editions','financial loss retains its sign'):
            self.assertIn(word,self.plan)

    def test_13_scope_not_shrunk_to_two(self):
        for word in ('twenty-four-task/six-dossier','not all of Industrials','historical Street consensus','both actual witnesses','final Fable packet'):
            self.assertIn(word,self.plan)

    def test_14_dag_rejects_cycle_and_missing_parent(self):
        self.assertFalse(graph_valid([{'id':'A','depends_on':['B']},{'id':'B','depends_on':['A']}]))
        self.assertFalse(graph_valid([{'id':'A','depends_on':['MISSING']}]))

    def test_15_every_requirement_has_owning_suite(self):
        tasks={t['id']:t for t in self.data['tasks']}
        for row in self.rows:
            self.assertEqual(row['test_file'],tasks[row['task']]['test_file'])
            self.assertRegex(row['test_name'],r'^test_ind_(?:d\d{2}|r2\d{2}|sf\d{2})$')

    def test_16_guidance_consumes_financial_qualification(self):
        task=next(t for t in self.data['tasks'] if t['id']=='T05')
        self.assertIn('T04',task['depends_on'])
        self.assertIn('T04 operand qualification',self.plan)

if __name__=='__main__':unittest.main(verbosity=2)
