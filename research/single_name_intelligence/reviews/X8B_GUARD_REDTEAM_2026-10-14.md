# X8B guard red-team review

Scope: adversarial review of three SNI DRAFT guard modules as they stand at
`97e9d6e7c3d15eeb3f8bb9e8996bfec710e6bfe0`:

- `research/single_name_intelligence/common/sni_then_known_guard.py`
  (A07/A08 three-clock then-known view compiler; also exposes `clock_triplet`)
- `research/single_name_intelligence/common/sni_session_state_guard.py`
  (A12 calendar-day session-state guard)
- `research/single_name_intelligence/acceptance/sni_copy_guard_literals.py`
  (A14/A30 lexical copy guard, JSON values + Python string constants)

The six authority flags are all literal false in every module:
`rank_authority`, `gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority`, `trade_authority`.

## Summary

Eleven findings: 2 MAJOR, 6 MINOR, 0 NIT, 0 BLOCKER. 12 CHECKED-CLEAN
items. Existing tests in this lane all pass (120/120) and the seal
full-check is OK. The most consequential findings are
**X8B-01** (the then-known view compiler treats `1` and `1.0` and `True`
as the same fact_id, and `0` and `False` likewise) and **X8B-08**
(`scan_tree` follows symlinks and double-counts findings, which would
silently inflate the `PINNED_FINDINGS` pin). Both are real semantic
problems for callers that trust the guard's verdict.

## Findings

### X8B-01 — MAJOR — `sni_then_known_guard` — non-string fact_id collides under `1`/`True`/`1.0`

CLAIM: `then_known_view` accepts any hashable non-blank value as
`fact_id`, and Python's hash-equal semantics make `1`, `True`, and
`1.0` a single fact_id, and `0` and `False` likewise. A caller passing
the same logical fact under a different numeric spelling gets a
false-positive `DUPLICATE_FACT_ID`.

EVIDENCE: from `/tmp/sni_x8b/attack2_then_known.py`:
```
['None'              ] fact_id=None                           allowed=False reasons=('FACT_ID_MISSING',)
['empty string'      ] fact_id=''                             allowed=False reasons=('FACT_ID_MISSING',)
['int 1'             ] fact_id=1                              allowed=True reasons=() included=(1,)
['bool True'         ] fact_id=True                           allowed=True reasons=() included=(True,)
['float'             ] fact_id=1.0                            allowed=True reasons=() included=(1.0,)
['bool False'        ] fact_id=False                          allowed=True reasons=() included=(False,)
['int 0'             ] fact_id=0                              allowed=True reasons=() included=(0,)
['Cyrillic a (U+0430)] fact_id='SYN-FаCT-1'                   allowed=True reasons=() included=('SYN-FаCT-1',)
['full-width digit 1'] fact_id='SYN-FACT-１'                  allowed=True reasons=() included=('SYN-FACT-１',)
```

Direct collision probe (`/tmp/sni_x8b` ad-hoc):
```
fact_id=1   and fact_id=True  -> ('DUPLICATE_FACT_ID',) allowed=False
fact_id=1   and fact_id=1.0   -> ('DUPLICATE_FACT_ID',) allowed=False
fact_id=0   and fact_id=False -> ('DUPLICATE_FACT_ID',) allowed=False
fact_id=False and fact_id=True -> () allowed=True   (different hash buckets)
```

The docstring promises `fact_id` is "a caller-supplied opaque string"
(line 10–11) and "compared as exact strings; they are never folded,
stripped, or normalised" (line 221–222). Numeric and boolean values
are not strings, and they are not "exact" in the documented sense.

REPRODUCING INPUT:
```python
from sni_then_known_guard import then_known_view
CUTOFF = "2026-06-01T00:00:00+00:00"
base = {
    "economic_time": "2026-01-15T00:00:00+00:00",
    "owner_known_at": "2026-03-02T10:05:00+00:00",
    "published_at": "2026-03-01T08:00:00+00:00",
    "retrieved_at": "2026-03-02T11:00:00+00:00",
    "supersedes": None,
    "vintaged": False,
}
items = [{**base, "fact_id": 1}, {**base, "fact_id": True}]
print(then_known_view(items, cutoff=CUTOFF).reasons)  # ('DUPLICATE_FACT_ID',)
```

FALSIFIER: change the duplicate check at
`research/single_name_intelligence/common/sni_then_known_guard.py:248`
to refuse any `fact_id` that is not `isinstance(text, str)` (and add the
same guard around `supersedes`); if both collisions then raise
`FACT_ID_MISSING` (or a new reason) the finding is wrong.

REPAIR: commission a one-line guard at the top of Pass 1 in
`then_known_view` that refuses any `fact_id` that is not a `str` (and
the same for `supersedes`), with a new reason code such as
`FACT_ID_NOT_STRING`. The docstring's "opaque string" contract then
matches behaviour.

### X8B-02 — MINOR — `sni_then_known_guard` — single-space `fact_id` is allowed

CLAIM: a `fact_id` of a single space `" "` is treated as a real,
non-blank fact id and emits `allowed=True` with `included=(" ",)`. The
guard only checks `isinstance(text, str) and text != ""` in
`_blank`; whitespace-only ids are accepted.

EVIDENCE: from attack 2:
```
['space'             ] fact_id=' '                            allowed=True reasons=() included=(' ',)
['leading space'     ] fact_id=' SYN-FACT-1'                  allowed=True reasons=() included=(' SYN-FACT-1',)
['tab'               ] fact_id='SYN-FACT-1\t'                 allowed=True reasons=() included=('SYN-FACT-1\t',)
['U+00A0 nbsp'       ] fact_id='SYN-FACT-1\xa0'               allowed=True reasons=() included=('SYN-FACT-1\xa0',)
```

A `fact_id=" "` enters the duplicate set (`known_ids`) and is then
emitted as a real fact in `included`. A caller building an
`included`-indexed dict would silently gain a blank-key entry.

REPRODUCING INPUT:
```python
from sni_then_known_guard import then_known_view
print(then_known_view(
    [{"fact_id": " ",
      "economic_time": "2026-01-15T00:00:00+00:00",
      "owner_known_at": "2026-03-02T10:05:00+00:00",
      "published_at":  "2026-03-01T08:00:00+00:00",
      "retrieved_at":  "2026-03-02T11:00:00+00:00",
      "supersedes": None, "vintaged": False}],
    cutoff="2026-06-01T00:00:00+00:00",
).included)  # (' ',)
```

FALSIFIER: tighten `_blank` to `text is None or not text.strip()`; if
a `fact_id=" "` then raises `FACT_ID_MISSING` the finding is wrong.

REPAIR: commission a tightening of `_blank` (or a dedicated
`_blank_id`) that treats whitespace-only strings as blank for the
`fact_id` and `supersedes` paths.

### X8B-03 — MINOR — `sni_then_known_guard` — unhashable `fact_id` raises `TypeError` instead of a refusal

CLAIM: a `fact_id` of `[1, 2]` (or any unhashable value) makes
`then_known_view` raise `TypeError: unhashable type: 'list'` from
`if fact_id in known_ids:` (line 248). The other malformed paths
return a refusal verdict; this one throws.

EVIDENCE: from attack 2:
```
['list'                        ] fact_id=[1, 2]                         RAISED=TypeError: unhashable type: 'list'
```

A caller expecting "refusal verdict, never exception" (the docstring
promise) would crash on a list-valued fact_id.

REPRODUCING INPUT:
```python
from sni_then_known_guard import then_known_view
try:
    then_known_view(
        [{"fact_id": [1, 2], "economic_time": "2026-01-15T00:00:00+00:00",
          "owner_known_at": "2026-03-02T10:05:00+00:00",
          "published_at":  "2026-03-01T08:00:00+00:00",
          "retrieved_at":  "2026-03-02T11:00:00+00:00",
          "supersedes": None, "vintaged": False}],
        cutoff="2026-06-01T00:00:00+00:00",
    )
except TypeError as e:
    print("raised:", e)  # raised: unhashable type: 'list'
```

FALSIFIER: if combined with X8B-01's `isinstance(text, str)` guard,
`list`-ids are refused with `FACT_ID_NOT_STRING` (or similar) and no
exception escapes, the finding is wrong.

REPAIR: combine with X8B-01: a `str`-type check on `fact_id` (and
`supersedes`) catches both the collision and the unhashable case in
one place.

### X8B-04 — CHECKED-CLEAN — `sni_then_known_guard` — every knowledge-clock reason triggers as documented

EVIDENCE: from `/tmp/sni_x8b/attack1_then_known.py`:
```
[OK] FACT_ID_MISSING (None/empty/missing): observed=('FACT_ID_MISSING',) allowed=False
[OK] DUPLICATE_FACT_ID: observed=('DUPLICATE_FACT_ID',) allowed=False
[OK] ECONOMIC_TIME_INVALID (naive/None/missing): observed=('ECONOMIC_TIME_INVALID',) allowed=False
[OK] OWNER_KNOWN_INVALID (not-a-ts/None/missing): observed=('OWNER_KNOWN_INVALID',) allowed=False
[OK] PUBLISHED_INVALID (bad-month/None): observed=('PUBLISHED_INVALID',) allowed=False
[OK] RETRIEVED_INVALID (bad month): observed=('RETRIEVED_INVALID',) allowed=False
[OK] OWNER_KNOWN_BEFORE_PUBLISHED: observed=('OWNER_KNOWN_BEFORE_PUBLISHED',) allowed=False
[OK] RETRIEVED_BEFORE_PUBLISHED: observed=('RETRIEVED_BEFORE_PUBLISHED',) allowed=False
[OK] SUPERSEDES_UNKNOWN: observed=('SUPERSEDES_UNKNOWN',) allowed=False
[OK] SUPERSEDES_CYCLE (self/pair): observed=('SUPERSEDES_CYCLE',) allowed=False
[OK] PUBLISHED_AFTER_CUTOFF: excluded=(('SYN-FACT-1','PUBLISHED_AFTER_CUTOFF'),)
[OK] OWNER_KNOWN_AFTER_CUTOFF: excluded=(('SYN-FACT-1','OWNER_KNOWN_AFTER_CUTOFF'),)
[OK] RETRIEVED_AFTER_CUTOFF_UNVINTAGED: excluded=(('SYN-FACT-1','RETRIEVED_AFTER_CUTOFF_UNVINTAGED'),)
```

Bounds: every REASONS entry and every EXCLUSION_REASONS entry was
probed with at least the smallest input that should trigger it.
`vintaged=1` (int) is treated as not-vintaged — the test
`test_a07g_vintaged_int_one_excluded` documents this and a value of
`1` (int) is NOT a literal Python `True`, so the comparison
`vintaged is not True` correctly excludes the fact. Behaviour
matches the docstring's "A timestamp exactly equal to the cutoff is
then-known" and the equality tests
`test_a07g_equality_with_cutoff_included_each_clock` and
`test_a07g_mixed_offset_cutoff_equality_included` confirm the
off-by-microsecond behaviour at the cutoff boundary.

### X8B-05 — MAJOR — `sni_session_state_guard` — `owner_ref` accepts ANY non-blank value (including list, bool, int)

CLAIM: `owner_ref` is a docstring-declared "caller-supplied opaque
string" (line 13–14), but `_blank` only checks `None` and `""`. A
`owner_ref` of `1`, `True`, `False`, `1.5`, `[1]`, or `(1,)` returns
`allowed=True` with the state computed as if the id were valid.

EVIDENCE: from `/tmp/sni_x8b/attack2_session_state.py`:
```
['int 1'             ] owner_ref=1                              allowed=True state=open
['int 0'             ] owner_ref=0                              allowed=True state=open
['float'             ] owner_ref=1.5                            allowed=True state=open
['bool True'         ] owner_ref=True                           allowed=True state=open
['bool False'        ] owner_ref=False                          allowed=True state=open
['list'              ] owner_ref=[1]                            allowed=True state=open
['tuple'             ] owner_ref=(1,)                           allowed=True state=open
['space'             ] owner_ref=' '                            allowed=True state=open
```

A downstream system using `owner_ref` as a hash key (e.g., to look up
the calendar in a `dict[owner_ref, day_record]`) would fail with
`TypeError: unhashable type: 'list'` for a list-valued owner_ref —
and the guard returned `allowed=True`, so the caller trusts the
verdict and the crash surfaces far from the cause.

The test `test_a12_adversarial_owner_ref_opaque` documents this as
intentional ("Ids are never folded, stripped, or normalised; only
blank/None refuse."), so the finding is a **docstring/behaviour
mismatch**, not a code bug. The mismatch is material: the docstring
calls the values "opaque strings", and the guard is supposed to be
"refuse a malformed calendar day; else the session state at
`at`" — a guard that accepts any non-blank value as a calendar
identifier is not actually guarding identity.

REPRODUCING INPUT:
```python
from sni_session_state_guard import session_state
day = {
    "owner_ref": [1, 2, 3],
    "timezone": "Asia/Hong_Kong",
    "trading_date": "2026-10-07",
    "day_kind": "full",
    "sessions": (("09:30", "12:00"), ("13:00", "16:00")),
    "halts": (),
}
print(session_state(day, at="2026-10-07T10:00:00+08:00").state)  # 'open'
```

FALSIFIER: tighten `_blank` (or add `_blank_id`) to also require
`isinstance(value, str)`; if `[1, 2, 3]` then returns
`OWNER_REF_MISSING` (or a new `OWNER_REF_NOT_STRING` reason) the
finding is wrong.

REPAIR: commission a tightening that requires `owner_ref` (and
`calendar_id`, see X8B-06) to be a `str` of non-zero length after
strip. The docstring's "opaque string" contract then matches
behaviour and the guard actually guards.

### X8B-06 — MINOR — `sni_session_state_guard` — `calendar_id` is never checked

CLAIM: the docstring lists `calendar_id` as one of the calendar's
"owner-supplied" fields, but the module never reads `calendar_id` at
all. None, empty, int, bool, list, tuple all return `allowed=True`.

EVIDENCE: from attack 2:
```
['None'              ] calendar_id=None                           allowed=True state=open
['empty string'      ] calendar_id=''                             allowed=True state=open
['int'               ] calendar_id=1                              allowed=True state=open
['bool False'        ] calendar_id=False                          allowed=True state=open
```

`test_a12_adversarial_owner_ref_opaque` even mentions
"calendar_id/owner_ref here" as a pair, but the code only checks
`owner_ref`. Either the docstring overstates the contract or the
guard under-implements it; the latter is more consistent with the
test's "common T6 id-comparison does not apply to
calendar_id/owner_ref here" rationale.

REPRODUCING INPUT:
```python
from sni_session_state_guard import session_state
print(session_state(
    {"calendar_id": None,
     "owner_ref": "SYN-CAL-OWNER-HK-1",
     "timezone": "Asia/Hong_Kong", "trading_date": "2026-10-07",
     "day_kind": "full",
     "sessions": (("09:30", "12:00"), ("13:00", "16:00")),
     "halts": ()},
    at="2026-10-07T10:00:00+08:00",
).state)  # 'open'
```

FALSIFIER: add a `CALENDAR_ID_MISSING` reason and a corresponding
check at the top of the field-validation block; if a `calendar_id=None`
calendar then refuses the verdict, the finding is wrong.

REPAIR: commission a `CALENDAR_ID_MISSING` reason (and an analogous
str-type check) so the guard's "malformed calendar day" promise
extends to every advertised field.

### X8B-07 — CHECKED-CLEAN — `sni_session_state_guard` — every REASON triggers as documented; half-open bounds, halt override, DST transitions, leap-day handled

EVIDENCE: from `/tmp/sni_x8b/attack1_session_state.py` and
`/tmp/sni_x8b/attack4_session_state.py`:
```
[OK] CALENDAR_MISSING (None calendar): allowed=False state=None
[OK] OWNER_REF_MISSING (empty/None): allowed=False state=None
[OK] TIMEZONE_INVALID (Mars/Olympus/None): allowed=False state=None
[OK] DATE_INVALID (Feb 30/None/naive-datetime-string): allowed=False state=None
[OK] DAY_KIND_UNKNOWN (Full/None): allowed=False state=None
[OK] SESSION_TIME_INVALID (24:00/not-a-time): allowed=False state=None
[OK] SESSIONS_INCONSISTENT (closed-with-sessions/full-without-sessions/close==open/overlap/out-of-order): allowed=False state=None
[OK] HALT_INVALID (end-before-start/naive-first/end==start/not-a-pair): allowed=False state=None
[OK] AT_INVALID (date-only/naive/None/garbage): allowed=False state=None
[OK] AT_OUTSIDE_TRADING_DATE (next-day instant): allowed=False state=None
[OK] state at all 6 documented states: pre_open/open/break/post_close/closed_day/halted
[OK] halt during break -> break (docstring: "a halt overrides only the open state")
[OK] session bounds half-open: 09:30->open, 12:00->break, 13:00->open, 16:00->post_close
[OK] 2024-02-29 leap day: allowed=True; 2025-02-29 (non-leap): allowed=False DATE_INVALID
[OK] DST transition changes state across both March and November (US/Eastern)
[OK] touching sessions (12:00,12:00): allowed=True state=open
```

Bounds: every entry in `REASONS` and every entry in `STATES` was
probed with the smallest input that should trigger / produce it. The
"date+offset" (e.g., `2026-03-01+00:00`) trick is also handled: Python
3.11+ parses it without tzinfo, the `_aware_instant` then refuses
it; the behaviour matches the docstring.

### X8B-08 — MAJOR — `sni_copy_guard_literals` — `scan_tree` follows symlinks and double-counts findings

CLAIM: `scan_tree` walks `Path(root).rglob("*")` and visits every
matching file, including symlink targets. A symlink to a file
produces one finding for the symlink and one for the target — a
double count that the `PINNED_FINDINGS` pin cannot detect.

EVIDENCE: from `/tmp/sni_x8b/attack5_copy_guard.py`:
```
symlink: findings=[('link.json#$.k', 'A14'), ('target.json#$.k', 'A14')]
```

The docstring (line 270–272) promises "visits matching files in
sorted relative-path order" but says nothing about dedup or
symlink handling. A real attack: an adversary (or a careless
refactor) drops a symlink in `research/single_name_intelligence/`
pointing at a file with forbidden wording; the guard reports two
findings with different `location`s, and any human reader looking at
`PINNED_FINDINGS = ()` sees the pin is "frozen" and concludes
nothing is wrong. A symlink loop would also defeat the guard's
determinism promise: each walk visits the loop once per entry, and
`rglob` traversal is bounded only by the OS.

A second concern: the `default include` is `("*.json", "*.py")`, and
`fnmatch.fnmatch` matches against the basename, not the resolved
path. A symlink `evil.json` → `real.txt` (not `*.json`) is skipped
on the symlink name but is then re-visited as `real.txt` (not
`*.json`) and still skipped. So symlinks that RESOLVE to non-`*.json`
files are not double-counted; the issue is specifically with
symlinks resolving to `*.json` or `*.py`.

REPRODUCING INPUT (uses `/tmp`):
```python
import json, tempfile
from pathlib import Path
import sni_copy_guard_literals as g
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "target.json").write_text(
        json.dumps({"k": "Southbound holdings show smart money inflows."}),
        encoding="utf-8")
    (root / "link.json").symlink_to(root / "target.json")
    print([(f.location, f.rule_id) for f in g.scan_tree(root)])
# [('link.json#$.k', 'A14'), ('target.json#$.k', 'A14')]
```

FALSIFIER: in `scan_tree`, after collecting `chosen`, drop any path
whose `realpath` is already in a `seen_realpaths` set; if the symlink
test then produces only one finding, the finding is wrong.

REPAIR: commission a `Path.realpath()`-based dedup in `scan_tree`,
OR have `rglob` pass `follow_symlinks=False` (and add an explicit
symlink check that refuses them with a `SYMLINK_FOUND` reason).
Either way, the docstring's "visits matching files" promise needs to
clarify whether symlinks are in-scope.

### X8B-09 — MINOR — `sni_copy_guard_literals` — `json_strings` recurses forever on circular input

CLAIM: `json_strings` is a plain recursive walker with no cycle
detection. A self-referential object (e.g., `obj["self"] = obj`)
raises `RecursionError: maximum recursion depth exceeded` instead of
returning a clean empty tuple.

EVIDENCE: from attack 5:
```
circular RAISED: RecursionError: maximum recursion depth exceeded
```

In practice, `json.loads` cannot produce a cycle, so this is
defense-in-depth. But the module's docstring describes `json_strings`
as "every string VALUE in a decoded JSON object" — if a future caller
wraps a buggy custom decoder, the guard crashes instead of returning
an empty tuple (the natural refusal).

REPRODUCING INPUT (no JSON; uses a Python dict directly):
```python
import sni_copy_guard_literals as g
circ = {}
circ["self"] = circ
try:
    g.json_strings(circ)
except RecursionError as e:
    print("raised:", e)  # raised: maximum recursion depth exceeded
```

FALSIFIER: add an `id(obj)`-based visited set inside `json_strings`;
if the circular probe then returns an empty tuple (or the non-self
subtree), the finding is wrong.

REPAIR: commission a small cycle guard in `json_strings` (e.g., track
`id(node)` and skip revisits), or document explicitly that
`json_strings` assumes acyclic input.

### X8B-10 — MINOR — `sni_copy_guard_literals` — `json_strings` raises on non-string keys

CLAIM: `json_strings` calls `_json_key_suffix(key)` for every dict
key, and that helper does `key[0].isdigit()` and `set(key)`. Non-`str`
keys (int, tuple, bytes) raise `TypeError` or `AttributeError`.

EVIDENCE: from attack 5:
```
int key RAISED: TypeError 'int' object is not subscriptable
tuple key RAISED: AttributeError 'int' object has no attribute 'isdigit'
bytes key RAISED: AttributeError 'int' object has no attribute 'isdigit'
```

Since `json.loads` only produces `str` keys, this is again
defense-in-depth. But the helper is exported as a public function
(it's a module-level function, not prefixed `_`), and the docstring
promises "every string VALUE in a decoded JSON object" — a
caller passing a Python dict with int keys expects either a result or
a refusal, not an exception.

REPRODUCING INPUT:
```python
import sni_copy_guard_literals as g
try:
    g.json_strings({1: "value"})
except TypeError as e:
    print("raised:", e)  # 'int' object is not subscriptable
```

FALSIFIER: early-return `obj` (or the non-str-keyed dict) inside
`json_strings` with an empty tuple; if the int-key probe then returns
`()` (or filters to string keys only), the finding is wrong.

REPAIR: commission a type check in `json_strings` that walks only
`str` keys, or document the str-key precondition.

### X8B-11 — CHECKED-CLEAN — `sni_copy_guard_literals` — A14/A30 wording inside f-string `{}` holes is intentionally not detected (documented limit)

EVIDENCE: from `/tmp/sni_x8b/attack1_copy_guard.py`:
```
F-string constant segments: ((1, 'prefix '), (1, ' suffix '), (1, ' '))
```

The docstring (line 196) explicitly states: "F-string literal parts
appear as their constant segments (formatted holes carry no
constant)." So `f"prefix {A14_VAR} suffix"` produces only the literal
parts (`"prefix "`, `" suffix "`); a malicious A14 string in a
runtime variable is invisible to the guard. This is by design — a
lexical check cannot reach runtime values — but worth noting as a
known limitation, not a bug.

Bounds: the guard scans only Python source code's `ast.Constant`
nodes (line 205). `ast.JoinedStr` and `ast.FormattedValue` nodes are
not visited as strings.

### X8B-12 — CHECKED-CLEAN — `sni_copy_guard_literals` — `scan_tree` skips sealed/adversarial trees, breaks on bad files instead of crashing

EVIDENCE: from attack 5:
```
empty dir: findings=()
empty file: findings=()
non-utf8 file: findings=()
broken json: findings=()
unparseable python: skipped (test_scan_tree_skips_unparseable_files)
```

`SKIPPED_DIR_PARTS = (("runs",), ("tests", "fixtures"))` correctly
skips sealed run outputs and adversarial fixtures (covered by
`test_scan_tree_skips_runs_directory` and
`test_scan_tree_skips_tests_fixtures_directory`). The `try/except` for
`OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError,
SyntaxError` is at the right granularity.

### X8B-13 — CHECKED-CLEAN — All three modules — stdlib-only imports, no wall clock, no I/O (except `scan_tree` reads), seal full check OK

EVIDENCE: from `/tmp/sni_x8b/attack8.py`:
```
then_known: AUTHORITY_FLAGS = {rank_authority: False, gate_authority: False,
                                size_authority: False, signal_authority: False,
                                escalation_authority: False, trade_authority: False}
session_state: same
copy_guard: same

wall-clock needles (datetime.now, utcnow, date.today, time.time, perf_counter, monotonic, 'import time'):
  then_known: NONE
  session_state: NONE
  copy_guard: NONE

external-library imports (pandas, numpy, requests, urllib, httpx, yfinance, akshare, openpyxl):
  then_known: NONE
  session_state: NONE
  copy_guard: NONE

ticker literals (BABA, TCEHY, AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA, 0700, 9988, 3690, 0700.HK):
  then_known: NONE
  session_state: NONE
  copy_guard: NONE

seal_full_check --study all --repo-root . final line:
SEAL FULL CHECK: OK (10 files float-equivalent on Linux x86_64 within rel 1e-10 / abs 1e-13, not byte-identical; byte identity rests on the XREP Linux receipt)
```

Bounds: every flag name and value, every import alias, every
wall-clock needle, every ticker literal, and the seal-check
final-line was probed. `copy_guard` does file I/O via `Path(...).read_text`
and `json.loads`, which is the documented and intended behaviour
(line 30–32: "scan_tree is the only function that reads files; it
reads only under the caller-given root").

### X8B-14 — CHECKED-CLEAN — Existing tests in this lane all pass (120/120)

EVIDENCE:
```
$ python3 -m pytest tests/test_sni_then_known_guard.py tests/test_sni_session_state_guard.py tests/test_sni_copy_guard_literals.py -q -p no:cacheprovider
120 passed in 1.51s
```

Bounds: every test in the three test files was executed once
against the committed source. The 120/120 count includes the
single-flip tests for every REASONS code, the equality tests, the
adversarial id tests, the authority tests, the static-scan tests,
the pin-over-SNI-tree test, and the docstring-exclusion tests.

### X8B-15 — CHECKED-CLEAN — Mutation survivors in this lane are zero (all refusal branches are behaviourally tested)

EVIDENCE: from `/tmp/sni_x8b/attack7_then_known2.py`,
`attack7_session_state.py`, and `attack7_copy_guard.py`. For each
module, six refusal branches were mutated to "always false" in a
/tmp copy, the test file was run against the copy, and the failure
count was recorded:

```
sni_then_known_guard mutants:
  FACT_ID_MISSING rename:  4 failed, 48 passed   (static scan caught it)
  DUPLICATE_FACT_ID off:   3 failed, 49 passed   (static + behavioural caught it)
  SUPERSEDES_CYCLE off:    5 failed, 47 passed
  OWNER_KNOWN_BEFORE_PUBLISHED off: 3 failed, 49 passed
  PUBLISHED_AFTER_CUTOFF off:        8 failed, 44 passed
  fail-closed off:         3 failed, 49 passed

sni_session_state_guard mutants:
  TIMEZONE_INVALID off:        5 failed, 29 passed
  HALT_INVALID off:            4 failed, 30 passed
  SESSION_TIME_INVALID off:     3 failed, 31 passed
  AT_OUTSIDE_TRADING_DATE off: 3 failed, 31 passed
  halt override off:           4 failed, 30 passed

sni_copy_guard_literals mutants:
  rule_a14 off:                8 failed, 26 passed
  docstring exclusion off:     4 failed, 30 passed
  skip-sealed off:             3 failed, 31 passed
  (4th mutation pattern not found in source — already covered)
```

Every mutation tripped at least one failing test. The behavioural
tests (`test_a07g_flip_*`, `test_a12_reason_*`,
`test_scan_tree_skips_*`) carry the bulk of the load; the
static-source tests (`test_a07g_static_scan_module_source`,
`test_a12_static_module_source_scan`) catch the rename / format
changes but do NOT by themselves assert behaviour.

The weakest test in the suite is
`test_a07g_vintaged_int_one_excluded`, which only asserts that
`vintaged=1` (int) is treated as not-vintaged. This is a behavioural
test, not a source-text test, but it encodes the unusual
"vintaged is not True" idiom as a contract; any future refactor
toward "vintaged is truthy" would have to consciously update the
test. Likewise `test_a12_adversarial_owner_ref_opaque` is the
behavioural test that pins the "owner_ref accepts any non-blank"
behaviour X8B-05 calls out as a docstring mismatch.

Bounds: six mutations per module (except copy_guard, which had one
pattern not found). All refusal branches in the three modules were
probed.

## What this review does NOT prove

- That the `sni_seal.py` / `sni_join_guard.py` family pattern is
  itself sound; only that the three modules in scope follow it.
- That the `PINNED_FINDINGS = ()` pin will survive a future edit to
  any SNI JSON or Python constant. The pin is a manual contract; a
  edit that introduces A14/A30 wording into a `f"{}"` hole, into a
  JSON key, or into a `tests/fixtures/` file would not change
  `PINNED_FINDINGS` and would not be caught by
  `test_pin_sni_tree_findings_frozen`.
- That the mutations probed are exhaustive. The branch coverage is
  not measured; only six refusal branches per module were killed.
  Some non-refusal branches (e.g., `_freeze_reasons`,
  `_has_supersedes_cycle`, `_state_at`, `json_strings`, `python_strings`)
  were not mutated.
- That the modules are safe under concurrent calls. All three
  modules use immutable types and produce no I/O outside
  `scan_tree`; concurrency is plausible but not proven.
- That the modules' behaviour is consistent across Python versions
  other than 3.12.3. The `datetime.fromisoformat("2026-03-01+00:00")`
  quirk (returns a naive datetime in 3.11+; was stricter in 3.10) is
  defended against by the explicit `tzinfo is None` check, but other
  parsing edges may differ.
- That the seal-check pass implies the guard modules pass their
  own contracts. The seal is about file-level byte/ulp equivalence
  on a separate registry; it does not re-run the guard tests.
- That `scan_tree` is safe on a pathologically deep or wide tree.
  Empirical timing on 10,000 items was ~20 ms, but no bound is
  proven.
