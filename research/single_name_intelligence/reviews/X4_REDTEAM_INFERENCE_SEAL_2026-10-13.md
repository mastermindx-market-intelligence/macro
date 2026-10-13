# X4 red-team: SNI inference (A1R1) + seal (A2R1)

Heads: inference `ecd7ad9b66aa8c4c1887ee21bd6766b3f87932fe`, seal
`714d2e90a0de909668723b74901d3de12d9a73ac`. Lane X4. Review date 2026-10-13.
Probes live under `/tmp/x4probe/`; tests ran from `/tmp/x4inf` and `/tmp/x4seal`.

This document is a read-only red-team of conclusions those two shared libraries
will print into every later SNI study. Residual and stress numbers remain
descriptive sample summaries.

## Summary

Finding counts: **BLOCKER 4**, **MAJOR 5**, **MINOR 3**, **NIT 0**.

(a) **Yes.** `label_for` prints `TESTED` for a cell with fewer than 2 clusters.
Input: `label_for(wilson_ci(0, 1), min_episodes=1)` → `TESTED` with
`n_clusters=1`. A constructed `InferenceResult(n_obs=0, n_clusters=0,
abstained=False, …)` with `min_episodes=0` also returns `TESTED` (0 episodes).

(b) **No.** Mutating any single field of a `build_seal` object (every top-level
key, every cell key `protocol`/`version`/`split`/`h`, every budget entry,
`sealed_at_utc`, `content_digest`) and calling `verify_seal` without recomputing
the digest produced a non-empty problem list in every case (`silent_count=0`).
File bytes that differ by one byte, a trailing newline, or CRLF also report
`input_manifest sha256 mismatch`. Schema/code holes that appear only after a
digest recompute are X4-07; silent *file* replacement is X4-04.

Merge of these two libraries into a shared SNI import is blocked by X4-01
(TESTED on a 1-observation Wilson cell), X4-02 (empty sign test returns p=1.0),
X4-03 (binomial tails crash for n≥1030), and X4-04 (write_seal overwrite).

## Findings

### X4-01 — BLOCKER — `label_for` prints TESTED for a 1-cluster Wilson cell

- **CLAIM:** `label_for` returns `TESTED` for `wilson_ci(0, 1)` (n_obs=1,
  n_clusters=1, abstained=False) when `min_episodes=1`, contradicting the
  module's own label law that n_clusters < min_clusters is
  `ABSTAIN_INSUFFICIENT_CLUSTERS`.
- **EVIDENCE:** `sni_inference.py:20-24` (label law), `:425-429`
  (`wilson_ci` sets `n_clusters=n_i` and `abstained=False` for n≥1),
  `:478-483` (`label_for` returns `TESTED` iff `n_obs >= min_episodes` once
  `abstained` is false). Probe `/tmp/x4probe/a04_label_for.py`:

  ```
  wilson(0,1) min_ep=1: label='TESTED' n_obs=1 n_clusters=1 abstained=False TESTED=True
  0ep_not_abstained_min0: label='TESTED' n_obs=0 n_clusters=0 abstained=False TESTED=True
  1cluster_not_abstained_min1: label='TESTED' n_obs=10 n_clusters=1 TESTED=True
  ```
- **FALSIFIER:** `label_for(wilson_ci(0, 1), min_episodes=1)` returns
  `ABSTAIN_INSUFFICIENT_CLUSTERS`, and `label_for` on any `n_obs==0` result
  returns `ABSTAIN_NO_EPISODES` even when `abstained is False`.
- **REPAIR:** Commission `label_for` to enforce n_obs==0 and
  n_clusters < MIN_CLUSTERS from the result fields themselves, and have
  `wilson_ci` abstain when n < MIN_CLUSTERS.

### X4-02 — BLOCKER — empty sign test returns p=1.0

- **CLAIM:** `sign_test_two_sided(0, 0)` returns `1.0`, so an unestimable
  (pos+neg==0) family is reported as a tested p-value of 1 rather than an
  abstain with a named reason.
- **EVIDENCE:** `sni_inference.py:464-466` (`if n == 0: return 1.0`).
  Probe `/tmp/x4probe/a03_sign.py`:

  ```
  pos=0 neg=0 -> 1.0
  type <class 'float'>
  equals 1.0 True
  binom_p_two_sided(0,0) -> 1.0
  ```

  Tests pin the behaviour: `tests/test_sni_common_inference.py:90` includes
  `(0, 0)` in the symmetry pairs.
- **FALSIFIER:** `sign_test_two_sided(0, 0)` raises `ValueError` or returns an
  abstain token; it never equals `1.0`.
- **REPAIR:** Commission the function to refuse n=0 (or return a named abstain)
  and drop `(0, 0)` from the symmetry test.

### X4-03 — BLOCKER — binomial tails raise OverflowError for n≥1030

- **CLAIM:** `_binom_tail_ge` / `_binom_tail_le` multiply `math.comb(n, i)` by
  a float, which overflows for n≥1030 at typical k, so
  `binom_p_one_sided_greater` / `binom_p_two_sided` / `sign_test_two_sided`
  crash on episode counts that US/Mag-7 daily families will hit.
- **EVIDENCE:** `sni_inference.py:230-231`. Probe `/tmp/x4probe/a02_binom.py`
  plus follow-up:

  ```
  k=1000 n=2000 p0=0.5: RAISED OverflowError: int too large to convert to float
  k=1 n=2000 p0=0.5: RAISED OverflowError: int too large to convert to float
  n=1020 ok
  n=1030 RAISED OverflowError
  ```

  Small-n brute-force sums for n=10 p0=0.5 matched exactly (attack 2
  checked-clean below).
- **FALSIFIER:** `binom_p_two_sided(1000, 2000, 0.5)` returns a Python float in
  `[0, 1]` with no exception.
- **REPAIR:** Commission log-space / `math.lgamma` tails (or Decimal) and add
  an n=2000 regression pin.

### X4-04 — BLOCKER — `write_seal` silently replaces an existing seal

- **CLAIM:** A second `write_seal` to the same `out_dir` overwrites `SEAL.json`
  and `SEAL.md` in place, so a sealed prereg/budget can be replaced after the
  fact without `verify_seal` running.
- **EVIDENCE:** `sni_seal.py:467-476` (`Path.write_text` with no existence
  check). Probe `/tmp/x4probe/a13_write_seal.py`:

  ```
  second write: DID_NOT_RAISE
  paths same True True
  json replaced True
  lane in new file True
  wrote unverified tampered seal DID_NOT_RAISE
  ```

  `tests/test_sni_common_seal.py::test_write_seal_round_trip` writes once into
  an empty `tmp_path`.
- **FALSIFIER:** The second `write_seal(seal2, out)` raises and the original
  `SEAL.json` bytes are unchanged.
- **REPAIR:** Commission an existence refusal (immutable write) and a
  `verify_seal` check before any bytes are written.

### X4-05 — MAJOR — `label_for` prints TESTED with NaN/None CI and leaks custom reasons

- **CLAIM:** `label_for` returns `TESTED` for a non-abstained result whose CI
  bounds are `NaN` or `None`, and returns caller-supplied `reason` strings
  outside `{TESTED, DESCRIPTIVE_ONLY, ABSTAIN_NO_EPISODES,
  ABSTAIN_INSUFFICIENT_CLUSTERS}`.
- **EVIDENCE:** `sni_inference.py:478-484`. Probe a04:

  ```
  nan_ci_min1: label='TESTED' n_obs=10 n_clusters=5 TESTED=True
  none_ci_not_abstained_min1: label='TESTED' ci absent TESTED=True
  abstained_custom_reason: label='ABSTAIN_CUSTOM' in_four=False
  labels_seen includes 'OTHER'; outside_four_count=48
  ```
- **FALSIFIER:** `label_for` on `ci_lo=float("nan")` / `ci_lo=None` with
  `abstained=False` returns an abstain token, and a non-contract `reason`
  raises.
- **REPAIR:** Treat missing or non-finite CI as unestimable; restrict the
  return value to the four contract tokens.

### X4-06 — MAJOR — cluster keys `1` and `True` (and `1` / `1.0`) collapse

- **CLAIM:** Date-cluster grouping uses Python dict equality, so keys `1` and
  `True` (and `1` and `1.0`) become one cluster and the cell abstains as
  insufficient clusters even though two keys were supplied.
- **EVIDENCE:** `sni_inference.py:328-337` (group then `n_clusters < min_c`
  abstain). Probe `/tmp/x4probe/a05_clusters.py`:

  ```
  1 == True True; hash(1)==hash(True) True
  mixed 1 and True: n_clusters=1 abstained=True reason=ABSTAIN_INSUFFICIENT_CLUSTERS
  mixed 1 and 1.0: n_clusters=1 abstained=True
  mixed 1 and '1': n_clusters=2 abstained=False
  ```
- **FALSIFIER:** `cluster_mean_ci([10.0, 20.0], [1, True], draws=100, seed=0)`
  reports `n_clusters=2`.
- **REPAIR:** Group clusters by `_cluster_sort_key` (type name, repr), matching
  the documented mixed-key order.

### X4-07 — MAJOR — `verify_seal` accepts a digest-recomputed object that the schema rejects

- **CLAIM:** After deleting a required field (`lane`, `identity_facts`,
  `sealed_at_utc`, `prereg_digest`, `protocol_ids`, `repo_ref`, `extra`,
  `input_manifest`, `not_supported`) or adding `unexpected_field` / a cell
  extra key, and recomputing `content_digest`, `verify_seal` returns `[]`
  while `jsonschema` rejects the same object (`additionalProperties: false`).
- **EVIDENCE:** Schema `sni_seal.v1.schema.json` required list and
  `"additionalProperties": false`. `sni_seal.py:300-376` checks digest,
  authority flags, outcome_free, and budgets; it does not check presence of
  `lane` / `identity_facts` / `sealed_at_utc`. Malformed cells set
  `well_formed=False` and skip cell violations (`:329-335`). Probe
  `/tmp/x4probe/a12_schema.py`:

  ```
  jsonschema: VALID
  verify extra top-level (digest ok): [] empty True
  jsonschema extra top-level: INVALID Additional properties are not allowed
  DEL identity_facts recompute verify empty=True
  DEL sealed_at_utc recompute verify empty=True
  DEL lane recompute verify empty=True
  cell extra prop verify empty= True []
  ```
- **FALSIFIER:** `verify_seal` of a `build_seal` output with `identity_facts`
  deleted and digest recomputed is a non-empty list, and an extra top-level
  key is a non-empty list.
- **REPAIR:** Commission `verify_seal` to enforce the schema's required keys
  and `additionalProperties: false` (including exact cell keys).

### X4-08 — MAJOR — tests pass while `label_for` has no MIN_CLUSTERS check

- **CLAIM:** Deleting or inverting the MIN_CLUSTERS gate in `cluster_mean_ci`
  is caught, but `label_for` itself contains no cluster check, and the
  inference suite still reports 23 passed, so a 1-cluster TESTED label
  (X4-01) has no test that would fail.
- **EVIDENCE:** Mutation (a3) in `/tmp/x4mut` copies. `label_for` body
  (`sni_inference.py:470-484`) contains neither `MIN_CLUSTERS` nor
  `n_clusters`.

  ```
  label_for contains MIN_CLUSTERS? False
  label_for contains n_clusters? False
  (a3) unmodified label_for (no cluster check) tests: exit=0 summary=23 passed
  ```

  `(a)` deleting the `cluster_mean_ci` gate: 1 failed
  (`test_abstain_empty_and_one_cluster`). `(a4)` inverting `n_obs >= m`:
  1 failed (`test_label_for_descriptive_vs_tested`).
- **FALSIFIER:** A committed test that asserts
  `label_for(wilson_ci(0, 1), min_episodes=1) != TESTED` and fails on this
  head.
- **REPAIR:** Add that pin (and a constructed `n_obs=0, abstained=False`
  pin) before merging.

### X4-09 — MAJOR — deleting the cells-not-sorted check leaves 17 tests passing

- **CLAIM:** Removing `verify_seal`'s `cells not sorted` branch does not fail
  any seal test, so unsorted cells with a matching recomputed digest would
  ship.
- **EVIDENCE:** Mutation (b4) on `/tmp/x4mut/seal`:

  ```
  (b4) delete cells-not-sorted: patched=True exit=0 summary=17 passed in 0.48s
  NOT CAUGHT
  ```

  `test_verify` only tampers `cells[1]["h"]` without recomputing the digest,
  so it is a digest test.
- **FALSIFIER:** A committed test that feeds unsorted cells, recomputes
  `content_digest`, and expects a non-empty `verify_seal` list, failing on
  this head.
- **REPAIR:** Add unsorted-cell and extra-cell-key verify pins with
  recomputed digest.

### X4-10 — MINOR — case-variant authority keys are stored and verify as empty

- **CLAIM:** `build_seal(extra={"Trade_Authority": True})` succeeds and
  `verify_seal` of that seal (and of a top-level `Trade_Authority` key with
  recomputed digest) returns `[]`; only exact lowercase flag names are
  refused.
- **EVIDENCE:** `sni_seal.py:115-116` (`key in AUTHORITY_FLAG_KEYS`). Probe
  `/tmp/x4probe/a10_authority.py`:

  ```
  seal.extra Trade_Authority=True: DID_NOT_RAISE dict SEAL_BUILT
    verify_seal extra.Trade_Authority: []
  verify Trade_Authority in extra (digest ok): []
  verify top-level Trade_Authority (digest ok): []
  ```

  Exact keys `trade_authority=True/"true"/1/"yes"`, nested two levels, and
  list-smuggled keys all raised (attack 10 checked-clean).
- **FALSIFIER:** `build_seal(..., extra={"Trade_Authority": True})` raises
  `ValueError`.
- **REPAIR:** Refuse authority-shaped keys case-insensitively (or after
  underscore/camel folding) in extra, identity_facts, and top-level.

### X4-11 — MINOR — `np.float64` values are accepted and leak into the CI

- **CLAIM:** `cluster_mean_ci` accepts NumPy `float64` observations
  (`isinstance(np.float64, float)` is true) and returns `ci_lo`/`ci_hi` as
  `np.float64`, so a JSON dump of `InferenceResult.to_dict()` can fail the
  seal's finite-float canonicalization path downstream.
- **EVIDENCE:** Probe `/tmp/x4probe/a06_validation.py`:

  ```
  cluster values np.float64: DID_NOT_RAISE -> InferenceResult(..., ci_lo=np.float64(1.0), ci_hi=np.float64(2.0), ...)
  cluster values np.int64: RAISED ValueError: values must be finite real numbers
  wilson np.int64: RAISED ValueError: k must be an int
  ```
- **FALSIFIER:** `cluster_mean_ci([np.float64(1.0), np.float64(2.0)], ["a","b"])`
  raises `ValueError`, or returns builtin `float` CI bounds.
- **REPAIR:** Reject (`type(v) is not float and type(v) is not int`) or coerce
  with `v + 0.0` after a finite check and store builtin floats only.

### X4-12 — MINOR — SNI `wilson_ci` reprints the owner statistic at a different z

- **CLAIM:** `sni_inference.wilson_ci` is a second copy of
  `engine.grading_stats.wilson_ci` (same name, same binomial Wilson interval)
  using z=1.959964 and full precision, while the owner uses z=1.96 and rounds
  to 3 decimals, so the same (k, n) can print different bounds.
- **EVIDENCE:** Owner `engine/grading_stats.py:56-60`; SNI
  `sni_inference.py:382-386` and `_Z_ALPHA_0_05 = 1.959964`. Probe:

  ```
  k=5 n=10 sni=(0.23659308901147935, 0.7634069109885206) eng_z1.96=(0.237, 0.763)
  k=0 n=10 sni hi=0.2775328030260577 eng=(0.0, 0.278)
  ```

  `test_wilson_cross_check_engine` accepts either full-precision equality or
  `round(..., 3)`. Module docstring (`sni_inference.py:1-12`) declares an
  SNI-local DRAFT and also says it is not an owner re-implementation.
- **FALSIFIER:** SNI `wilson_ci(5, 10)` bounds equal the owner tuple
  `(0.237, 0.763)` (or the owner is imported rather than re-coded).
- **REPAIR:** Consume `engine.grading_stats.wilson_ci` when present, or pin
  z and rounding to the owner contract in the DRAFT docstring.

## Checked-clean

Each entry is an attack that produced no finding in the stated bounds.

### Attack 1 — wilson_ci boundaries (except the n=1 label, which is X4-01)

Bounds: `k∈{0,n}`, `n∈{0,1,10}`, `alpha∈{0,1,1e-12,0.999999,0.1,0.05,0.01,nan,inf,-0.1}`,
misspelled `alhpa=0.01`, and a full (k,n,alpha) grid n=1..30, k=0..n, three
alphas. Probe `a01_wilson.py`.

- n=0 abstains (`ABSTAIN_NO_EPISODES`); no division by zero.
- alpha 0/1/nan/inf raise `alpha must be in (0, 1)`; 1e-12 and 0.999999 raise
  `alpha must be one of 0.1, 0.05, 0.01`.
- Bounds always in [0,1] with lo≤hi (`bad_bound_count=0`).
- `alhpa=0.01` raises `TypeError: unexpected keyword arguments: alhpa`
  (`_reject_authority` does not swallow unknown kwargs).

### Attack 2 — binomial definition, cap, small-n exactness

Bounds: docstring at `sni_inference.py:447-448`; brute-force `math.comb` sums
for n=10 p0=0.5, all k; p0 in {0, 1, 1e-15, 1-1e-15, 0.5} at n∈{0,1,10};
two-sided ≤ 1.0. Overflow at n≥1030 is X4-03.

- Two-sided definition is doubling: `min(1, 2 * min(P[X>=k], P[X<=k]))`.
- p is capped at 1.0 (`two>1=False` on every small-n case).
- n=10 p0=0.5: `one` matched brute `sum(comb)` for every k; two-sided matched
  the stated formula.

### Attack 5 — cluster shuffle and `1` vs `"1"` / `"01"`

Bounds: string-key shuffle 8 permutations; mixed int/str keys 8 permutations;
keys `{1,"1","01",1.0,True}`. Probe `a05_clusters.py`. Collision of `1`/`True`
is X4-06.

- `1` and `"1"` are distinct clusters (`n_clusters=2`).
- `"1"` and `"01"` are distinct clusters.
- String-key shuffle: `string_shuffle_identical=True` (ci_lo/ci_hi/estimate).
- Two unshuffled runs with the same seed are identical.

### Attack 6 — input validation (bool / NaN / inf / negative / k>n / numpy ints)

Bounds: `wilson_ci`, `binom_p_*`, `sign_test_two_sided`, `cluster_mean_ci`,
`label_for`. Probe `a06_validation.py`. np.float64 leak is X4-11.

- `True`/`False` as k, n, pos, min_episodes, draws, seed, min_clusters: all
  `ValueError` (`type(value) is not int`).
- NaN/inf alpha, p0, and cluster values: `ValueError`.
- negative n, k>n: `require n >= k >= 0`.
- `np.int64` / `np.int32` as k or n: `ValueError` (raise, no coerce).

### Attack 7 — `plain_word_null` / module language

Bounds: regex over all of `sni_inference.py` for `validated|causal|impact|forecast|predict|signal|\bedge\b|50/50|significant|news impact|coin flip`;
all four `plain_word_null` contract strings. Probe `a07_language.py`.

- `validated`, `forecast`, `predict`, `impact`, `50/50`, `significant`,
  `edge`, `news impact`, `coin flip`: 0 hits in the module.
- `causal`: 1 hit, required negation ("never causal", L5).
- `signal`: 4 hits, all authority-flag refusal text (`signal_authority`,
  "does not feed a … signal").
- `alpha` hits are the CI level parameter / z table, not an edge claim.
- Four contract strings contain none of the forbidden phrases.

### Attack 8 — canonical_json (NaN/inf refuse; distinctness is the right seal answer)

Bounds: NaN, inf, -inf, -0.0 vs 0.0, NFC vs NFD `"café"`, key order, `1` vs
`1.0`, `True` vs `1`. Probe `a08_canonical.py`.

- NaN/inf/-inf raise `canonical_json requires finite floats`.
- Key order: `{"b":1,"a":2}` and `{"a":2,"b":1}` share a digest.
- `1` vs `1.0` produce distinct JSON (`{"x":1}` vs `{"x":1.0}`) — correct for
  a type-preserving seal.
- NFC vs NFD produce distinct digests — correct for a byte seal.
- `-0.0` vs `0.0` produce distinct JSON (`-0.0` vs `0.0`) — correct for a
  bit-level seal (IEEE signed zero).

### Attack 9 — tamper detection without digest recompute

Bounds: every top-level key value change; every `cells[i].{protocol,version,split,h}`;
every budget family; every `identity_facts` field; `extra.fixture`; deletion of
every key; `file_bytes` exact / one-byte / trailing newline / CRLF. Probe
`a09_tamper.py`. Digest-recompute schema holes are X4-07.

```
clean_verify []
silent_count 0
file_bytes one-byte ['input_manifest sha256 mismatch for path a.json']
file_bytes trailing newline ['input_manifest sha256 mismatch for path a.json']
file_bytes CRLF ['input_manifest sha256 mismatch for path a.json']
```

### Attack 10 — authority refusal for exact flag names (case variants: X4-10)

Bounds: six flags × values `{True,"true",1,"yes"}` on `wilson_ci` kwargs and
on `build_seal(extra=…)`; nested two levels in extra and identity_facts; keys
inside a list; case variants as unexpected kwargs. Probe `a10_authority.py`.

- Exact keys with True/"true"/1/"yes" all raise `ValueError` on inference and
  on seal extra (including False-valued extra keys, which are still refused
  by key name).
- Nested `extra.meta.<flag>` and `identity_facts.wrap.<flag>` raise.
- List-smuggled `extra.rows[0].<flag>` raises.
- `wilson_ci(Trade_Authority=True)` raises `TypeError` (unexpected keyword).
- `build_seal(..., trade_authority=True)` raises `TypeError` (unexpected
  keyword).

### Attack 11 — identity ids are opaque pass-through

Bounds: grep of `sni_seal.py` and `sni_inference.py` for
`ticker|cik|isin|cusip|figi|mint|derive`; `_check_identity_id_values` on str /
None / dict-ticker / int; `build_seal` round-trip of a caller-supplied
`issuer_id`. Probe `a11_identity.py`. (`isin` hits are `isinstance` only.)

- No ticker/CIK/CUSIP/FIGI construction path.
- `"mint"` / `"derive"` hits are required negations in the module docstring.
- `issuer_id="caller-opaque-AAA"` is stored unchanged.
- `{"issuer_id": {"ticker": "BABA"}}` raises (must be str or None).
- `ticker` / `cik` fields without `_id` suffix are stored as opaque extras
  (the library does not mint an id from them).

### Attack 12 — field set parity (enforcement hole is X4-07)

Bounds: keys written by `build_seal` vs schema `properties` / `required`.

- `code_keys == schema_props == schema_required` (15 fields).
- `jsonschema.validate(build_seal(...), schema)` succeeds (jsonschema 4.10.3
  present).
- `authority_flags.trade_authority=True` fails jsonschema (`False was expected`).

### Attack 13 — write destination (overwrite is X4-04)

Bounds: `write_seal` output paths vs `out_dir`.

- Writes exactly `out_dir/SEAL.json` and `out_dir/SEAL.md`.
- `out_dir` with `..` resolves via `Path` and still lands under the given
  destination's resolved parent (`/tmp/x4probe/seal_escape/SEAL.json`).

### Attack 14 — owner fork (Wilson numeric delta is X4-12)

Bounds: `grep -n "^def \|^class "` on `engine/grading_stats.py`,
`engine/qledger.py`, `engine/trial_ledger.py`; name-set intersection with
`sni_inference.py` / `sni_seal.py`; docstring DRAFT claims.

- Name overlap: only `wilson_ci` (`sni_inference` ∩ `grading_stats`). Covered
  as X4-12. Duplication is an SNI-local stdlib DRAFT (engine import pulls
  pandas/numpy); unavoidable for a stdlib-only contract, with a cross-check
  test that currently permits the rounding delta.
- `cluster_mean_ci` vs `block_bootstrap_ci` / `block_bootstrap_scalar_ci`:
  different estimand (plain clustered mean vs conditional-minus-base / moving
  block on a Series). DRAFT stdlib-only.
- `label_for` vs `derive_state` / `min_n_gate` / `dd_verdict`: different
  tokens (TESTED/DESCRIPTIVE_ONLY/ABSTAIN_* vs UNGRADED/ACCRUING/GRADED and
  accruing/earning/falsified). SNI-local label law.
- `canonical_json`/`sha256_text` vs `trial_ledger._canon`/`_hash` (sha1[:16]
  of a trial config) and `qledger.body_hash` (sha256 of a claim body):
  different ledger semantics. Seal docstring names qledger/Evaluation as an
  owner it consumes, not a ledger it reimplements.
- `write_seal` vs `qledger.register`: register is append-only with claim_id
  dedupe; write_seal is a two-file snapshot (overwrite hole is X4-04).

### Attack 15 — mutations that the tests did catch

See the table. Caught: (a) delete/invert MIN_CLUSTERS in `cluster_mean_ci`;
(a4) invert `label_for` n_obs comparison; (b)(b2) drop `sealed_at_utc`/`extra`
from digest on both sides; (b3) drop `sealed_at_utc` from verify only; (c)
delete inference authority refusal; (c2) delete extra nested authority
refusal; (c3) delete identity_facts authority refusal. Uncaught: (a3)/(b4) as
X4-08 and X4-09.

## Test runs

Commands (from scratch archives, then `cd` back to the worktree):

```
mkdir -p /tmp/x4inf && git archive ecd7ad9b66aa8c4c1887ee21bd6766b3f87932fe | tar -x -C /tmp/x4inf
cd /tmp/x4inf && PYTHONPATH=/tmp/x4inf python3 -m pytest tests/test_sni_common_inference.py -q -p no:cacheprovider
```

```
.......................                                                  [100%]
23 passed in 0.57s
```

passed=23 skipped=0 failed=0

```
mkdir -p /tmp/x4seal && git archive 714d2e90a0de909668723b74901d3de12d9a73ac | tar -x -C /tmp/x4seal
cd /tmp/x4seal && PYTHONPATH=/tmp/x4seal python3 -m pytest tests/test_sni_common_seal.py -q -p no:cacheprovider
```

```
.................                                                        [100%]
17 passed in 0.56s
```

passed=17 skipped=0 failed=0

jsonschema 4.10.3, numpy 2.5.4, pandas 3.0.6 were present. No pip installs.

## Mutation results

Mutations applied only under `/tmp/x4mut/` (copies of the archives). Original
worktree untouched.

| mutation | tests caught |
|---|---|
| (a) delete MIN_CLUSTERS block in `cluster_mean_ci` | yes — 1 failed (`test_abstain_empty_and_one_cluster`) |
| (a2) invert `n_clusters < min_c` in `cluster_mean_ci` | yes — 6 failed |
| (a3) `label_for` has no MIN_CLUSTERS check (unmodified) | **no** — 23 passed (X4-08) |
| (a4) invert `label_for` `n_obs >= m` | yes — 1 failed (`test_label_for_descriptive_vs_tested`) |
| (b) drop `sealed_at_utc` from digest in build+verify | yes — 2 failed (golden + permutation) |
| (b2) drop `extra` from digest in build+verify | yes — 3 failed (golden, permutation, refusals/nan) |
| (b3) drop `sealed_at_utc` from verify digest only | yes — 4 failed (clean verify mismatch) |
| (b4) delete `cells not sorted` check in `verify_seal` | **no** — 17 passed (X4-09) |
| (c) delete inference `_reject_authority` true-refusal | yes — 2 failed (authority flags + r1_06 trade_authority) |
| (c2) delete extra nested authority refusal | yes — 3 failed (refusals, r1_01, r1_06) |
| (c3) delete identity_facts authority refusal | yes — 1 failed (`test_r1_02_authority_in_identity_facts`) |
