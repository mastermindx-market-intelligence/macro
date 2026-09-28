# R3 executed outcome-access specimens

Review evidence only. These are not a production patch, evaluator, registered trial, or H1 smoke. The source-copied function executes only against fictional I/O. No production module or store was loaded. Companion: `OUTCOME_ACCESS_REVIEW_R3.md`.

## native_load_grades_excerpt.py

SHA256 `0a8101b4272838adab053810b27af5fc10c0b06fa4f518f8abbfc2d200bcadde`

```python
def load_grades(root: Any = None, *, months: Iterable[str] | None = None,
                columns: Iterable[str] | None = None) -> pd.DataFrame:
    """Read the grade store as ONE frame — the only supported way to consume it.

    Mirrors :func:`engine.us_context_vector.load_candidates`: parts are concatenated in
    filename order (chronological), columns unify across parts, and ``months`` restricts to
    ``YYYY-MM`` run-month keys.  ``columns`` projects at the parquet level, so the
    idempotence check can read four key columns out of a store that is growing by ~66k rows
    a month without materialising the rest.

    A part that names a column the caller asked for and a part that does not are both
    handled: the projection is intersected per part and the union is reindexed at the end,
    so a column introduced in a later month reads back null for earlier months.
    """
    store = _store_dir(root)
    if not store.exists():
        return pd.DataFrame()
    wanted_months = {str(m) for m in months} if months is not None else None
    wanted_cols = [str(c) for c in columns] if columns is not None else None
    frames: list[pd.DataFrame] = []
    # ``YYYY-MM/YYYY-MM-DD.parquet`` — sorted() over the relative path is chronological
    # because both grains are zero-padded ISO.
    for part in sorted(store.glob("*/*.parquet")):
        if wanted_months is not None and part.parent.name not in wanted_months:
            continue
        try:
            if wanted_cols is None:
                frames.append(pd.read_parquet(part))
            else:
                try:
                    frame = pd.read_parquet(part, columns=wanted_cols)
                except Exception:  # noqa: BLE001 — column absent from an older part
                    frame = pd.read_parquet(part)
                frames.append(frame.reindex(columns=wanted_cols))
        except Exception as exc:  # noqa: BLE001 — one bad part must not blind the rest
            log.warning("us_prophet_grades: part %s unreadable (%s)", part.name, exc)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

```

## label_access_probe.py

SHA256 `b44e4ce30cdfc45db6ec47b2f152c771715ccd90b743be1ad39542e05fa07eb8`

```python
"""R3 isolated source-review specimens. NOT a grader, model, or native smoke.

Only the copied load_grades function executes. Its pd.read_parquet, store, and
logger are test doubles. No production modules, files, network, prices, or real
outcomes are opened. Fictional dates are labels, not asserted exchange sessions.
"""
from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import ast
import json
import sys
import pandas as real_pd

ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / 'native_load_grades_excerpt.py'
SOURCE = SOURCE_PATH.read_text(encoding='utf-8')
TREE = ast.parse(SOURCE)
assert len(TREE.body) == 1 and isinstance(TREE.body[0], ast.FunctionDef)
assert TREE.body[0].name == 'load_grades'
assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(TREE))
KEY = ['stamp_date', 'ticker', 'board_definition', 'horizon']
METADATA = [*KEY, 'fill_date', 'mark_date', 'graded_asof']
OUTCOME = 'excess_spy'
TRAIN_KEY = ('2030-04-01', 'SYN_A', 'fictional_v1', 10)
ROWS = [
    dict(stamp_date='2030-04-01', ticker='SYN_A', board_definition='fictional_v1', horizon=10,
         fill_date='2030-04-02', mark_date='2030-04-16', graded_asof='2030-06-21',
         excess_spy=0.0123),
    dict(stamp_date='2030-06-02', ticker='SYN_B', board_definition='fictional_v1', horizon=10,
         fill_date='2030-06-03', mark_date='2030-06-17', graded_asof='2030-06-21',
         excess_spy=-0.0234),
    dict(stamp_date='2030-06-04', ticker='SYN_C', board_definition='fictional_v1', horizon=10,
         fill_date='2030-06-05', mark_date='2030-06-19', graded_asof='2030-06-21',
         excess_spy=0.0345),
    dict(stamp_date='2030-04-01', ticker='SYN_A', board_definition='fictional_v1', horizon=42,
         fill_date='2030-04-02', mark_date='2030-05-30', graded_asof='2030-06-21',
         excess_spy=-0.0456),
    dict(stamp_date='2030-04-01', ticker='SYN_A', board_definition='fictional_other', horizon=10,
         fill_date='2030-04-02', mark_date='2030-04-16', graded_asof='2030-06-21',
         excess_spy=0.0567),
]
# Dates are only fictional partition labels. No exchange/calendar validity is
# asserted; no fixture outcome ends after its declared fictional grading run.
PART = '2030-06/2030-06-21.parquet'

@dataclass(frozen=True, order=True)
class FakePart:
    path: str
    @property
    def name(self):
        return self.path.rsplit('/', 1)[-1]
    @property
    def parent(self):
        return SimpleNamespace(name=self.path.split('/')[0])

class FakeStore:
    def __init__(self, paths):
        self.paths = paths
    def exists(self):
        return True
    def glob(self, pattern):
        assert pattern == '*/*.parquet'
        return [FakePart(p) for p in self.paths]

class FakeLog:
    def __init__(self):
        self.warnings = []
    def warning(self, fmt, *args):
        self.warnings.append(fmt % args)

class SpyPandas:
    DataFrame = real_pd.DataFrame
    concat = staticmethod(real_pd.concat)
    def __init__(self, frames, *, fail_projection_once=False, deny_full=False):
        self.frames = frames
        self.fail_projection_once = fail_projection_once
        self.deny_full = deny_full
        self.calls = []
        self.materialized = []
    def read_parquet(self, part, columns=None):
        assert isinstance(part, FakePart), 'No real filesystem reads permitted.'
        entry = {'part': part.path, 'columns': columns, 'status': 'ATTEMPT'}
        self.calls.append(entry)
        if columns is None and self.deny_full:
            entry['status'] = 'FICTIONAL_GUARD_REFUSED'
            raise PermissionError('fictional guard: full read prohibited')
        if columns is not None and self.fail_projection_once:
            self.fail_projection_once = False
            entry['status'] = 'FICTIONAL_PROJECTION_IO_ERROR'
            raise OSError('fictional projected read error')
        frame = self.frames[part.path]
        if columns is not None and not set(columns).issubset(frame.columns):
            entry['status'] = 'FICTIONAL_SCHEMA_MISMATCH'
            raise KeyError('fictional requested metadata column absent')
        result = frame.copy() if columns is None else frame.loc[:, columns].copy()
        entry['status'] = 'MATERIALIZED'
        entry['row_count'] = len(result)
        if OUTCOME in result.columns:
            keys = [tuple(row[k] for k in KEY) for _, row in frame.iterrows()]
            self.materialized.extend(keys)
        return result

def exercise(*, columns, months=('2030-06',), fail_once=False, deny_full=False,
             admitted_only=False):
    frame = real_pd.DataFrame(ROWS[:1] if admitted_only else ROWS)
    spy = SpyPandas({PART: frame}, fail_projection_once=fail_once, deny_full=deny_full)
    logger = FakeLog()
    env = {'Any': Any, 'Iterable': Iterable, 'pd': spy,
           '_store_dir': lambda root=None: FakeStore([PART]), 'log': logger}
    exec(compile(SOURCE, '<source-pinned-load_grades>', 'exec'), env)
    output = env['load_grades'](months=months, columns=columns)
    return output, spy, logger

def summary(name, output, spy, logger, assertion):
    assertion()
    return {'case': name, 'result': 'WITNESS_PASS', 'returned_rows': len(output),
            'returned_columns': list(output.columns), 'io_calls': spy.calls,
            'fictional_outcome_keys_materialized': spy.materialized,
            'warnings': logger.warnings}

def require(condition, message):
    if not condition:
        raise AssertionError(message)

results = []
out, spy, log = exercise(columns=METADATA)
results.append(summary('P01_valid_metadata_projection_does_not_materialize_outcomes', out, spy, log,
    lambda: require(len(out) == 5 and not spy.materialized and len(spy.calls) == 1,
                    'positive metadata projection witness failed')))

out, spy, log = exercise(columns=METADATA + ['bench_calendar_state'])
results.append(summary('P02_missing_metadata_fallback_materializes_hidden_outcomes', out, spy, log,
    lambda: require(len(spy.materialized) == 5 and OUTCOME not in out.columns
                    and out['bench_calendar_state'].isna().all()
                    and spy.calls[-1]['columns'] is None,
                    'expected full fallback read with clean final projection')))

out, spy, log = exercise(columns=METADATA, fail_once=True)
results.append(summary('P03_non_schema_error_also_widens_to_full_read', out, spy, log,
    lambda: require(spy.calls[0]['status'] == 'FICTIONAL_PROJECTION_IO_ERROR'
                    and len(spy.materialized) == 5 and OUTCOME not in out.columns,
                    'broad exception fallback was not demonstrated')))

out, spy, log = exercise(columns=[*METADATA, OUTCOME])
results.append(summary('P04_run_month_does_not_restrict_stamp_horizon_or_definition', out, spy, log,
    lambda: require(len(out) == 5 and {r[3] for r in spy.materialized} == {10,42}
                    and len({r[2] for r in spy.materialized}) == 2
                    and len({r[0] for r in spy.materialized}) == 3,
                    'run-month mixture witness failed')))

out, spy, log = exercise(columns=[*METADATA, OUTCOME])
returned_keys = out[KEY].apply(tuple, axis=1)
filtered = out.loc[returned_keys == TRAIN_KEY].copy()
results.append(summary('P05_post_return_training_filter_cannot_undo_materialization', filtered, spy, log,
    lambda: require(len(filtered) == 1 and len(spy.materialized) == 5
                    and any(key != TRAIN_KEY for key in spy.materialized),
                    'post-filter access mismatch was not demonstrated')))

out, spy, log = exercise(columns=[*METADATA, OUTCOME], months=('2030-04',))
results.append(summary('P06_stamp_month_used_as_run_month_silently_misses_training_key', out, spy, log,
    lambda: require(out.empty and not spy.calls and not spy.materialized,
                    'run-month vs stamp-month exclusion witness failed')))

out, spy, log = exercise(columns=METADATA + ['bench_calendar_state'], deny_full=True)
results.append(summary('P07_outer_failsoft_catches_fictional_access_refusal', out, spy, log,
    lambda: require(out.empty and not spy.materialized and len(log.warnings) == 1
                    and spy.calls[-1]['status'] == 'FICTIONAL_GUARD_REFUSED',
                    'swallowed guard refusal witness failed')))

out, spy, log = exercise(columns=[*METADATA, OUTCOME], admitted_only=True)
results.append(summary('P08_pre_admitted_fixture_domain_only_materializes_training_key', out, spy, log,
    lambda: require(len(out) == 1 and spy.materialized == [TRAIN_KEY],
                    'positive pre-admitted domain witness failed')))

receipt = {
    'evidence_class': 'isolated_native_function_with_fictional_io_trace',
    'native_module_imported': False, 'real_parquet_read': False,
    'real_market_or_protected_outcome_read': False, 'model_fit': False,
    'native_repair_implemented': False, 'independent_review': False,
    'accepted_h1_smoke': False, 'outcome_value_printed': False,
    'native_source': {
        'repo': 'mastermindx-market-intelligence/macro',
        'path': 'engine/us_prophet_grades.py',
        'main_pin': '7878cc44564e677057c220fea7f01811ddc32c6c',
        'main_blob': 'da7d1f625dc3d20431806502d9f36be82973ffa2',
        'prospective_pin': 'c72d5d7e5defc9582e032f72fa23a8fc90737aac',
        'prospective_blob': '0653dd6fecbdb484557c101a634f2188dacf10a5',
        'function': 'load_grades',
        'excerpt_sha256': sha256(SOURCE.encode()).hexdigest(),
        'excerpt_binding': 'exact displayed function transcribed from native connector reads; no full module copy claimed',
    },
    'python': sys.version.split()[0], 'pandas': real_pd.__version__,
    'passed': len(results), 'failed': 0, 'cases': results,
}
(ROOT/'label_access_receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: receipt[k] for k in ['evidence_class','passed','failed','python','pandas']}))

```

## key_scope_counterexample.py

SHA256 `e3fc0bd31b78bc7fe02875c4fc647a11c3ebcbf9f6b484e85524383aabd7509f`

```python
"""One fictional exact-key/predicate check for the proposed native-owner repair."""
from pathlib import Path
import json
allowed={('D1','SYN_A','v1',10),('D2','SYN_B','v1',10)}
universe=allowed | {('D1','SYN_B','v1',10),('D2','SYN_A','v1',10)}
coordinate_sets=[{key[i] for key in allowed} for i in range(4)]
naive={key for key in universe if all(key[i] in coordinate_sets[i] for i in range(4))}
exact={key for key in universe if key in allowed}
assert exact == allowed
assert naive - allowed == {('D1','SYN_B','v1',10),('D2','SYN_A','v1',10)}
receipt={'evidence_class':'fictional_repair_predicate_counterexample', 'passed':1,'failed':0,
 'allowed_keys':sorted(allowed),'independent_column_IN_result':sorted(naive),
 'extra_keys_wrongly_admitted':sorted(naive-allowed),'exact_tuple_result':sorted(exact),
 'current_native_implementation_claim':False, 'market_or_outcome_read':False}
Path(__file__).with_name('key_scope_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'passed':1,'failed':0,'naive_extra_keys':len(naive-allowed)}))

```

## Executed result summary

```json
{
  "evidence_class": "isolated_native_function_with_fictional_io_trace",
  "python": "3.13.5",
  "pandas": "2.2.3",
  "passed": 8,
  "failed": 0,
  "source": {
    "repo": "mastermindx-market-intelligence/macro",
    "path": "engine/us_prophet_grades.py",
    "main_pin": "7878cc44564e677057c220fea7f01811ddc32c6c",
    "main_blob": "da7d1f625dc3d20431806502d9f36be82973ffa2",
    "prospective_pin": "c72d5d7e5defc9582e032f72fa23a8fc90737aac",
    "prospective_blob": "0653dd6fecbdb484557c101a634f2188dacf10a5",
    "function": "load_grades",
    "excerpt_sha256": "0a8101b4272838adab053810b27af5fc10c0b06fa4f518f8abbfc2d200bcadde",
    "excerpt_binding": "exact displayed function transcribed from native connector reads; no full module copy claimed"
  },
  "cases": [
    {
      "case": "P01_valid_metadata_projection_does_not_materialize_outcomes",
      "result": "WITNESS_PASS",
      "returned_rows": 5,
      "materialized_outcome_key_count": 0,
      "io_calls": 1,
      "warnings": 0
    },
    {
      "case": "P02_missing_metadata_fallback_materializes_hidden_outcomes",
      "result": "WITNESS_PASS",
      "returned_rows": 5,
      "materialized_outcome_key_count": 5,
      "io_calls": 2,
      "warnings": 0
    },
    {
      "case": "P03_non_schema_error_also_widens_to_full_read",
      "result": "WITNESS_PASS",
      "returned_rows": 5,
      "materialized_outcome_key_count": 5,
      "io_calls": 2,
      "warnings": 0
    },
    {
      "case": "P04_run_month_does_not_restrict_stamp_horizon_or_definition",
      "result": "WITNESS_PASS",
      "returned_rows": 5,
      "materialized_outcome_key_count": 5,
      "io_calls": 1,
      "warnings": 0
    },
    {
      "case": "P05_post_return_training_filter_cannot_undo_materialization",
      "result": "WITNESS_PASS",
      "returned_rows": 1,
      "materialized_outcome_key_count": 5,
      "io_calls": 1,
      "warnings": 0
    },
    {
      "case": "P06_stamp_month_used_as_run_month_silently_misses_training_key",
      "result": "WITNESS_PASS",
      "returned_rows": 0,
      "materialized_outcome_key_count": 0,
      "io_calls": 0,
      "warnings": 0
    },
    {
      "case": "P07_outer_failsoft_catches_fictional_access_refusal",
      "result": "WITNESS_PASS",
      "returned_rows": 0,
      "materialized_outcome_key_count": 0,
      "io_calls": 2,
      "warnings": 1
    },
    {
      "case": "P08_pre_admitted_fixture_domain_only_materializes_training_key",
      "result": "WITNESS_PASS",
      "returned_rows": 1,
      "materialized_outcome_key_count": 1,
      "io_calls": 1,
      "warnings": 0
    }
  ]
}
```

## Exact-key repair counterexample receipt

```json
{
  "evidence_class": "fictional_repair_predicate_counterexample",
  "passed": 1,
  "failed": 0,
  "allowed_keys": [
    [
      "D1",
      "SYN_A",
      "v1",
      10
    ],
    [
      "D2",
      "SYN_B",
      "v1",
      10
    ]
  ],
  "independent_column_IN_result": [
    [
      "D1",
      "SYN_A",
      "v1",
      10
    ],
    [
      "D1",
      "SYN_B",
      "v1",
      10
    ],
    [
      "D2",
      "SYN_A",
      "v1",
      10
    ],
    [
      "D2",
      "SYN_B",
      "v1",
      10
    ]
  ],
  "extra_keys_wrongly_admitted": [
    [
      "D1",
      "SYN_B",
      "v1",
      10
    ],
    [
      "D2",
      "SYN_A",
      "v1",
      10
    ]
  ],
  "exact_tuple_result": [
    [
      "D1",
      "SYN_A",
      "v1",
      10
    ],
    [
      "D2",
      "SYN_B",
      "v1",
      10
    ]
  ],
  "current_native_implementation_claim": false,
  "market_or_outcome_read": false
}

```

## Unexecuted real-Parquet lane

The planned real-I/O script did not reach fixture creation; its three planned assertions are not included in the executed count.

```json
{
  "planned_cases": 3,
  "executed_cases": 0,
  "passed": 0,
  "first_execution": {
    "exit": 1,
    "failure": "ModuleNotFoundError: No module named pyarrow",
    "stage": "before fixture creation / native reader execution"
  },
  "dependency_recovery": {
    "calls": 1,
    "package": "pyarrow==19.0.1",
    "exit": 1,
    "cause": "DNS/name resolution failure; no successful installation",
    "log_sha256": "5217d9abd62f808e900c243b89e28bebd1b3af497a04d1428fd5d84c94fa17cc"
  },
  "new_dependency_or_fixture_effect_proven": false,
  "disposition": "UNEXECUTED_ENVIRONMENT_GATE; no repeated installation or alternate carrier attempted"
}

```

## Raw evidence identities

These refer to the portable evidence files. Complete executed scripts above regenerate the fictional traces; no market inputs are needed.

- `label_access_receipt.json`: 9586 bytes; SHA256 `594e468208380626831c0fd916a2bdc1c7afca06f0e2d4e80609dcb1ec32bf2c`.
- `key_scope_receipt.json`: 924 bytes; SHA256 `b8793b7f8ce668369ba5fea91a0f1466f289a0c96cadab89fb508b0355518048`.
- `real_parquet_probe.py`: 5073 bytes; SHA256 `623c007946ae191fb00cfdca08cfdbd095d0699b16bb957d80253f852baded91`.
- `real_parquet_unexecuted.json`: 645 bytes; SHA256 `be07bb22bdd10aa6894ab1bb3ca1251f60c618d32e669bd34d64f4037e469e4d`.
- `dependency_install.log`: 2011 bytes; SHA256 `5217d9abd62f808e900c243b89e28bebd1b3af497a04d1428fd5d84c94fa17cc`.
