# OPUS ADVERSARIAL REVIEW R2 — PR #7950 (T04a) @ ac2db2907ac56ac0ff2b44f15f42bc3ffc2fe5b0
Reviewer: Opus, ROUTE: review / AUDIT, MODE: READ_ONLY. Date 2026-09-24.
Repairs judged: `aa1cd7247a16..ac2db2907ac5` (8 commits). Base merge-base `7d843a4d1760`; `origin/main` `0293b9cfd76f`.
R1 report consumed: `research/mining/m1_integration_program/reviews/OPUS_T04A_PR_REVIEW_R1_2026-09-24.md`.

## VERDICT: REJECT (1 new BLOCKER, 5 new MAJOR; 3 of the nine R1 findings closed outright)

The repair is real work — the dead `expectations` path now executes, the suppression rule is on the
limitation vocabulary, the schema is tightened, the subclass bypass is gone. But the central
deliverable is now surfaced with a **fabricated value**: the domain legs carry no number, and
`_leg()` substitutes the leg's `period_kind`, so every composed management comparison publishes
`earlier_point_estimate.value == later_actual.value == "quarter"`. The frozen probe passes because it
asserts count, `is_range/is_consensus` and a non-empty `comparison` — never a leg value. Mutant MU6
(`raw_value = 0`) leaves the whole 129-test suite green: "unknown data never becomes zero" is now
unkillable by any test in this PR.

---

## 1. NINE-ROW CLOSURE TABLE

| R1 | State | Closing line | Probe run + observed output |
|---|---|---|---|
| **BLOCKER-1** expectations dead code | **PARTIAL** | `mining_theme_research.py` expectations section: `slice_def = MINING_DEFINITIONS[query.slice_key]` / `mev = slice_def.get("management_estimate_vs_actual") or {}`; `pairs = mev.get("pairs", []) or []` → second `_expectation_row` | dump (§3 cmd D1): `copper_complete … exp_n= 2`, rows `management_issued_copper_sales_estimate` and `…unit_net_cash_cost_estimate`, `is_range= False`; W-R: `rare_earth_complete lims= ['missing_derivation']`, `exp_n= 1`, `epe= null la = null` (limitations, not zeros). **But** both legs' `value` = `"quarter"` → NEW-BLOCKER-A; slice-keyed, not case-keyed (verified: `query.slice_key` is the only selector). |
| **BLOCKER-2** signed block on `same_horizon_revision` | **CLOSED** | `_suppress_native_blocks = bool(set(limitations) & set(OMISSION_TO_LIMITATION.values()))` — vocabulary-derived, no case name anywhere in the module | dump: `same_horizon_revision … blocks= []`; `signed_loss … blocks= [('0000000421','reported operating income',-375,'-', …)]` (negative value **and** sign `-`, no suppressing limitation); every omission-mapped case (`missing_basis/missing_issuer/source_only/missing_stream_threshold/changed_source/denied_source`) → `blocks= []`. MU4 (drop `denied_source` from the suppressing set) → `FAILED …probes.py::test_probe_blocker2b…[denied_source]`. Residual inconsistency = NEW-MAJOR-C. |
| **BLOCKER-3** open `limitations` | **CLOSED** | schema `limitations.items` now `"type": "string"` at item level **and** `{"type":"string","pattern":…}` on the pattern branch | `129 passed` incl. `test_probe_blocker3_limitations_rejects_every_non_string[…]` for object/int/None/list. (Enum branch itself still untyped — redundant given the item-level type; NIT-L.) |
| **MAJOR-4** point-estimate law uncontracted | **PARTIAL** | schema `required` += `is_range,is_consensus,comparison`; `"is_range": {"type":"boolean","const": false}` (same for `is_consensus`); `"comparison": {…,"minLength":1}` | cmd D2: `A is_range=true REJECTED: False was expected` → const is non-overridable. **But** `B one-null-leg + zero limitations ACCEPTED (BAD)`, and the code mints only when BOTH legs are null: `B code guard: True` for `if main_epe is None and main_la is None`. Standard "a null leg forces `missing_derivation`" unmet. |
| **MAJOR-5** inverted guard, never mints | **OPEN (inverted the other way)** | `del defined_fields  # no longer a skip filter` in `_summarize_expectations` | Helper is fixed (probe `test_probe_major5…` green). Production now maps `definition_fields_required` → `definition_unqualified_fields`, so the *fully qualified* case emits: `copper_complete … lims= ['definition_unqualified:unit','definition_unqualified:perimeter','definition_unqualified:basis']`. MU7 (production mint → `[]`) → `129 passed` = the production path is still unpinned. NEW-MAJOR-D. |
| **MAJOR-6** tautological test | **CLOSED** | `tests/test_mining_composition.py` diff: `-    headlines["limitations"].append("definition_unqualified:basis")` removed; assert now reads helper-minted state | `129 passed` with the self-append gone (`git diff aa1cd724..HEAD -- tests/test_mining_composition.py`). |
| **MAJOR-7** `industry_total_unknown` unreachable | **PARTIAL** | `slice_limit_vocab = list(MINING_DEFINITIONS[query.slice_key].get("limitations_vocabulary") or [])` + `and not bundle.identity_results` | Vocabulary half is governed (domain md:268-278 lists it under W-R only). The **condition is invented**: `grep -n "industry_total_unknown" …DOMAIN_DEFINITIONS…md` → single hit `278:  - industry_total_unknown`, a bare vocabulary entry, no condition. Fires on **no** casebook case (dump: absent from all 11); only under a synthetic `_replace(identity_results=())`. NEW-MAJOR-E. |
| **MAJOR-8** CI `paths:` misses the domain file | **CLOSED** | `.github/ci/legacy-jobs.yml:16867  - "research/mining/m1_integration_program/domain/MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md"` | `grep -n mining .github/ci/legacy-jobs.yml | tail -12` shows the entry; both suites in `run:` (`:16894`, `:16896`) are in `paths:` (`:16864-16866`). Dated filename pin = NIT-L. |
| **MAJOR-9** degenerate ordering / no identity | **PARTIAL** | `identity_sid` loop (`str(ident.get("stable_subject_id") or ident.get("cik") or "")`) + `packet_sid` fallback; new `test_economics_rows_ordered_through_compose_mining_research` (tests:180-215) | dump: block ids `0000000421` / `0000000732`, no `subject:unknown`. MU8 (`packet_sid = "subject:unknown"`) → `FAILED …test_probe_major9_native_blocks_bind_to_a_real_subject_identity`. **But** every composed *expectation* row still reads `row sid= subject:unknown` in all 11 cases — the expectations `subject_id` loop omits the `cik` fallback. NEW-MAJOR-F. |

R1 MINOR-10 CLOSED (subclass deleted) but spawns MINOR-G; MINOR-11 PARTIAL → MINOR-H/I; MINOR-12 untouched.

---

## 2. NEW FINDINGS

### BLOCKER-A — the management point estimate publishes a fabricated `value` (the period label)
`engine/market_ontology/mining_theme_research.py`, `_leg()`:
```python
raw_value = leg.get("value")
if raw_value is None:
    raw_value = str(leg.get("period_kind") or leg.get("metric") or "")
```
The domain legs (`domain md:75-108`) carry `metric / source_family / selection_label /
research_locator / definition_fields_required / definition_notes / period_kind` — **no `value`**.
Observed for every W-C case:
`epe= {"metric":"management_issued_copper_sales_estimate","value":"quarter", …}` /
`la = {"metric":"consolidated_copper_sales","value":"quarter", …}`.
Both legs of a `earlier_point_estimate_vs_later_actual` comparison therefore carry the *identical*
string `"quarter"`: a consumer reading the contract sees estimate == actual. No limitation is minted.
This is the same family as the `forbidden_derivations` law (domain md §W-R) — a non-measured token
presented in a measured field — and it is strictly worse than the R1 defect it replaced (dead code
published nothing; this publishes a lie). Mutant **MU6** (`raw_value = 0`) → `129 passed`: a literal
zero in a management point estimate is invisible to every test in this PR, which falsifies R1's
"W-R nulls → zeros … vacuously satisfied" entry — it is now non-vacuously violable.
Probe (FAILS at ac2db290 — assertion contradicted by the observed dump above):
```python
def test_probe_r2_a_leg_values_are_never_synthesised_from_period_kind():
    case = synthetic_case("copper_complete")
    r = composition.compose_mining_research(case.query, case.bundle)
    for row in r["expectations"]:
        for leg in ("earlier_point_estimate", "later_actual"):
            v = (row[leg] or {}).get("value")
            assert v not in ("quarter", 0, "", None), (leg, v)
        assert row["earlier_point_estimate"]["value"] != row["later_actual"]["value"]
    # a leg with no measured value must degrade to a limitation, not to a label
    assert "missing_derivation" in r["limitations"] or all(
        isinstance((row[l] or {}).get("value"), (int, float))
        for row in r["expectations"] for l in ("earlier_point_estimate", "later_actual"))
```

### MAJOR-B — the expectations channel is never suppressed; a `denied_source` case still publishes the source's selection label
The expectations block is a pure function of `query.slice_key`; no limitation gates it. Observed:
`denied_source … blocks= []` **but** `exp_n= 2` with
`source_label: "Second-quarter consolidated copper sales outlook"`. Identical two-row output for
`missing_issuer`, `source_only`, `changed_source`, `missing_basis`. BLOCKER-2 was closed for the
reported channel only; the withdrawal principle (and, for `denied_source`, the source-rights
omission) does not reach the channel this PR exists to add.
Probe: `for n in ("denied_source","source_only","changed_source","missing_issuer"): assert
compose(...)["expectations"] == []` — FAILS at ac2db290 (observed `exp_n= 2` for each).

### MAJOR-C — the suppression invariant is order-dependent and `missing_derivation` is minted untruthfully on a complete case
`missing_derivation` is appended **after** `_suppress_native_blocks` is computed, so the same
limitation suppresses when it arrives from an omission and does not when the module mints it:
observed `rare_earth_complete … lims= ['missing_derivation'] … blocks= [('0000000732', …, 940, '+', …)]`
versus `same_horizon_revision … lims= ['missing_derivation'] … blocks= []`. The module comment claims
the opposite ("EVERY closed T04 limitation that is mapped from an omission withdraws the
reported-economics channel"). Separately the mint is untruthful: W-R's domain text is *"W-R has no
selected management estimate-versus-actual comparison in M1; separately qualified quarter
observations are reported without inventing one"* (domain md:257-259) — that is not a missing
derivation, and `missing_derivation` is already the mapped code for the `next_period_outlook`
omission (`mining_dependency_binding.py`, `OMISSION_TO_LIMITATION`), so two distinct facts now
collide in one code.
Probe: `assert composition.compose_mining_research(*rare_earth_complete) ["limitations"] == []` and
`assert not (set(r["limitations"]) & set(OMISSION_TO_LIMITATION.values()) and r["economics"]["native_blocks"])`
for all 11 cases — FAILS at ac2db290 on `rare_earth_complete` (observed above).

### MAJOR-D — `definition_unqualified:<field>` now fires on every W-C response, including the fully qualified case
`_unq()` returns the leg's `definition_fields_required` and `_expectation_row` writes it straight into
`definition_unqualified_fields`. "Required" is not "unqualified": the same legs carry
`definition_notes: Million recoverable pounds; consolidated reporting; sales exclude purchases`
(domain md:80-82), i.e. the unit/perimeter/basis *are* supplied, and the domain comparison text says
*"fully qualified compatible inputs are compared normally and never suppressed"*. Observed
`copper_complete … lims= ['definition_unqualified:unit','definition_unqualified:perimeter','definition_unqualified:basis']`
and each row's `unq= ['unit','perimeter','basis','unit','perimeter','basis']` (duplicated across the
two legs). Review standard "mints for a missing `unit`/`perimeter`/`basis` and nothing else" is unmet
in both directions. MU7 shows the production path has no test at all.
Probe: `assert [l for l in compose(copper_complete)["limitations"] if l.startswith("definition_unqualified:")] == []`
— FAILS at ac2db290 (observed three).

### MAJOR-E — `industry_total_unknown` is minted from an invented condition that contradicts the contract it describes
`if "industry_total_unknown" in slice_limit_vocab and not bundle.identity_results:`. The domain file
names the code once (`md:278`) with no condition; the unbound issuer axis already has a governed code
(`missing_issuer`), and `authorized_coverage.industry_total` is `{"type":"null"}` on **every**
response — so the industry total is unknown whether or not an issuer resolved. The new test asserts
the false converse (`result_bound` → NOT minted, i.e. identifying an issuer makes the industry total
known). MU5 (unconditional mint) is killed only by `test_partial_coverage_industry_total_stays_null`,
which pins the current (untruthful) polarity rather than a governed condition.
Probe: `assert "industry_total_unknown" in compose(rare_earth_complete_with_identity)["limitations"]`
(truthful polarity) — FAILS at ac2db290 (observed absent).

### MAJOR-F — expectation rows still carry the degenerate `subject:unknown`
The expectations `subject_id` loop reads only `ident.get("stable_subject_id")` while the native-block
loop also falls back to `ident.get("cik")`; the fixtures carry the latter. Observed `row sid=
subject:unknown` on all 11 cases, i.e. MAJOR-9's defect survives verbatim in the channel T04a adds,
and the frozen probe only inspects `economics.native_blocks`.
Probe: `assert all(r["stable_subject_id"] != "subject:unknown" for r in compose(copper_complete)["expectations"])`
— FAILS at ac2db290 (observed).

### MINOR-G — IR-04 now raises a mis-typed refusal
`raise MiningResearchRefusal("unknown_slice", f"definition_version {definition_version!r} …")`. The
slice is valid; only the version is unknown, and `unknown_slice` is already the code for a bad
`slice_key` (`test_unknown_slice_refuses`). Closing the bypass was right; the remap makes two
distinct refusals indistinguishable to a consumer. Same for `interpretation_stale` → `generation_changed`
(defensible, since the source generation did change).

### MINOR-H — an empty `source_label` still escapes as a raw `jsonschema.ValidationError`
`str(packet.get("source_label", packet.get("selection_label", "") or "synthetic-source"))` — the `or`
binds inside the inner `get`'s default, so an existing-but-empty `source_label` never reaches the
fallback. Observed (cmd D2): `D empty source_label RAISED ValidationError '' should be non-empty`.
R1's MINOR-11 defect class (crash instead of typed degradation) survives on a sibling field.
Also `basis` silently invents `"fictional reported dollars"` where `missing_basis` is the governed code.

### MINOR-I — `definition_unqualified:value` widens the definition vocabulary to a non-definition field
Observed: `C string value -> blocks [] lims ['definition_unqualified:value', …]`. A missing datum is
reported with a *definition-qualification* marker, and the packet leaves the reported channel with no
omission-mapped limitation.

### MINOR-J — the order of the two comparison rows is unpinned
MU1 (`expectations = expectations[::-1]`) → `129 passed`; the frozen probe asserts only
`len == 2` and `[0] is not [1]`, so the sales pair and the unit-cost pair may swap silently. The
repair packet's "assert exactly one `pairs` entry" was not implemented (`grep -n pairs
tests/test_mining_composition.py` → no hit); the count is pinned only indirectly by `len == 2`.

### NIT-K — dead computation: `defined_fields` (union of every leg's `definition_fields_required`, with a `{"basis","unit","perimeter"}` fallback) is computed in `compose_mining_research` and then `del`-ed by `_summarize_expectations`.
### NIT-L — the `limitations` enum branch is still untyped (harmless under the item-level `type: string`); the CI `paths:` entry pins the dated domain filename, so a renamed successor escapes the selector the module still imports.
### NIT-M — `cik` is accepted as a `stable_subject_id` (identity-vocabulary conflation); synthetic-only today.

---

## 3. MUTANT TABLE (8 new mutants, run against the full 4-file suite)
Harness: mutated source injected as `engine.market_ontology.mining_theme_research` in `sys.modules`,
then `pytest -q -x tests/test_mining_composition.py tests/test_mining_composition_probes.py
tests/test_mining_shared_contract.py tests/test_mining_shared_contract_probes.py`
(`…/scratchpad/mut/run_mutant.py`; worktree untouched).

| # | Mutant | Result | Killing test / consequence |
|---|---|---|---|
| MU1 | swap the order of the two comparison rows | **SURVIVES** `129 passed in 2.54s` | none → MINOR-J |
| MU2 | emit the sales pair twice | KILLED `1 failed, 40 passed` | `probes.py::test_probe_blocker1_management_pair_is_actually_composed` |
| MU3 | delete the `pairs` loop | KILLED `1 failed, 40 passed` | same probe (R1's M2 now dies) |
| MU4 | let `denied_source` keep its native block | KILLED `1 failed, 51 passed` | `probes.py::test_probe_blocker2b…[denied_source]` |
| MU5 | mint `industry_total_unknown` unconditionally | KILLED `1 failed, 9 passed` | `test_partial_coverage_industry_total_stays_null` |
| MU6 | leg `value` becomes literal `0` | **SURVIVES** `129 passed in 2.48s` | none → BLOCKER-A |
| MU7 | drop the production `definition_unqualified_fields` mint | **SURVIVES** `129 passed in 2.74s` | none → MAJOR-D |
| MU8 | unbind block identity (`packet_sid = "subject:unknown"`) | KILLED `1 failed, 61 passed` | `probes.py::test_probe_major9_native_blocks_bind_to_a_real_subject_identity` |

Commands (observed output quoted in §1/§2):
- D1 dump: `TZ=UTC python3 -c '…compose_mining_research for CASE_NAMES…'`
- D2 schema/edge: `TZ=UTC python3 -c '…V.validate(mutated payload); compose with string/empty packets…'`

---

## 4. REGRESSION / SCOPE CHECKS
- **Imports:** `git diff aa1cd7247a16..HEAD | grep '^+.*import'` → only `from dataclasses import replace as _replace` ×2, both inside new tests. No new module import, no `semiconductor`/`theme_graph`.
- **Refusal vocabulary:** widened nowhere — the subclass is deleted; every raise uses
  `MiningResearchRefusal.CODES` (`mining_dependency_binding.py:115-124`, verified: `expected_generation_required`,
  `unknown_slice`, `generation_changed` are all members).
- **Authority:** untouched by the diff (no `AUTHORITY`, `can_rank/gate/size/originate`, `neighborhood`,
  or `authorized_coverage` edit in `git diff aa1cd724..HEAD`).
- **Reads outside the domain file + casebook:** none — `MINING_DEFINITIONS` (domain md) and
  `bundle`/`query` are the only inputs; the schema is read for validation as before.
- **Synthetic only:** `git diff aa1cd7247a16..HEAD | grep -inE '0000831259|0001801368|freeport|fcx|mp materials|mountain pass|morenci|cerro verde|grasberg|lynas'` → **no hits** (exit 1).
- **CI block:** `mining-economic-dossier` starts at `:16844` and its last `run:` is `:16896` = EOF
  (`wc -l` → `16896`) → still the LAST block. `if: ${{ false }}` is the house idiom for pack-executed
  jobs (231 occurrences; annotated at `:16690`, `:16730`), not a disabled gate.
- **Base drift:** `git diff --stat 7d843a4d1760..origin/main -- .github/ci/legacy-jobs.yml tests/test_ci_pack.py` → empty. Neither contested file moved.
- **Contract delta:** NOT re-run to conclusion (tool timeout at 120s; `timeout(1)` unavailable). The
  repair adds no contract file and only narrows `mining_theme_research.v1.schema.json`
  (`required` +3, `const: false` ×2, `minLength` +1, `type: string` +2), so the R1-era "0 introduced"
  cannot have changed — but this is a **GAP**, not an observed result.

---

## 5. REPAIR PACKET (≤10 lines)
1. `_leg()`: never synthesise `value` from `period_kind`/`metric`. A leg with no measured value emits
   `value: null` (widen the schema leg to allow null) **or** the row is withheld with `missing_derivation`.
2. Assert in code and in a test that `earlier_point_estimate.value != later_actual.value` unless both are null.
3. Gate the expectations channel on the same withdrawal rule as the blocks (at minimum `denied_source`,
   `source_only`, `changed_source`, `missing_issuer` publish no row).
4. Move the null-leg / no-mev `missing_derivation` mint ABOVE `_suppress_native_blocks`, or exclude it
   there — one limitation must not mean two things (and W-R "no selected comparison" needs its own code).
5. Drop the `definition_fields_required` → `definition_unqualified_fields` mapping; mint
   `definition_unqualified:<field>` only when the leg's `definition_notes`/field is absent. De-duplicate the list.
6. Require ONE limitation per null leg (not only when both are null), and add it to the schema as a
   dependency or assert it in the suite.
7. `industry_total_unknown`: mint from the coverage contract (industry_total is `const null` → always
   unknown on the W-R slice) or drop the code; delete the test that asserts issuer-binding makes it known.
8. Give the expectations `subject_id` loop the same `cik` fallback as `identity_sid`; assert no
   `subject:unknown` in `expectations` through `compose_mining_research`.
9. Restore a distinct refusal for an unknown `definition_version` (add the code to the T01' CODES tuple
   under a ruling, rather than aliasing `unknown_slice`).
10. Freeze the six §2 probes plus an ordering assert for the two comparison rows; fix the
    `source_label` `or`-binding so an empty label degrades instead of raising.

---

## 6. ATTACKS THAT DID NOT LAND (R2)
- **Probe gaming by input special-casing.** The expectations binding is keyed on `query.slice_key` and
  `MINING_DEFINITIONS` only; no case name, fixture name or `len(fixtures)` switch exists in the module
  (`grep -n "copper_complete\|same_horizon\|denied_source" engine/market_ontology/mining_theme_research.py` → no hit).
  BLOCKER-2's suppression is likewise vocabulary-derived (`set(OMISSION_TO_LIMITATION.values())`).
- **Frozen probes tampered with.** `git diff --stat aa1cd7247a16..HEAD -- tests/test_mining_composition_probes.py` → empty.
- **Kernel copy / import ban / authority / Morenci re-multiplication / real-entity leakage** — re-checked
  over the repair diff only (no hits); R1's findings stand unchanged.
- **`is_range` override.** `const: false` is genuinely non-overridable (`A is_range=true REJECTED`).
- **Signed loss regression.** `signed_loss` still composes `-375` with sign `-` and `research_usable` intact.
- **CI shape.** Block still last; both `run:` suites present in `paths:`; domain md now selected.

---

## 7. THE SIX NEW PROBES, EXECUTED AT ac2db290 (all FAIL) — supersedes the §2 "assertion contradicted" wording
File: `…/scratchpad/mut/r2_probes.py` (ready to freeze as `tests/test_mining_composition_probes_r2.py`).
`TZ=UTC python3 -m pytest -q --no-header --tb=no -p no:cacheprovider …/r2_probes.py` → **`6 failed in 0.12s`**.

| Probe | Finding | Observed failure |
|---|---|---|
| `test_r2_a_leg_values_never_synthesised` | BLOCKER-A | `AssertionError: ('earlier_point_estimate', {'metric':'management_issued_copper_sales_estimate','value':'quarter',…})` / `assert 'quarter' not in ('quarter', 0, '', None)` |
| `test_r2_b_withdrawn_cases_publish_no_expectation_row` | MAJOR-B | `AssertionError: ('denied_source', 2)` — 2 rows published on a denied-source case |
| `test_r2_c_suppression_invariant_holds_for_every_case` | MAJOR-C | `AssertionError: ('rare_earth_complete', ['missing_derivation'])` with `[{'stable_subject_id':'0000000732',…,'value':940,…}]` |
| `test_r2_d_qualified_case_mints_no_definition_unqualified` | MAJOR-D | `assert ['definition_…lified:basis'] == []` — `first extra item: 'definition_unqualified:unit'` |
| `test_r2_e_industry_total_unknown_truthful_polarity` | MAJOR-E | `assert 'industry_total_unknown' in ['missing_derivation']` (coverage is `None`, code absent) |
| `test_r2_f_expectation_rows_bind_a_real_subject_identity` | MAJOR-F | `AssertionError: ['subject:unknown', 'subject:unknown']` |

## 8. CONTRACT DELTA — GAP in §4 CLOSED
`python3 scripts/check_contract_delta.py --base origin/main` (backgrounded, exit 0):
`contract-delta: 0 introduced, 1 inherited (base 29013bf2c43b)` with
`::notice title=contract-delta::tests/test_render_dead_ref_targets.py is already unwired on this PR's base — pre-existing, not introduced by this PR`.
