# T08 FREEZE PACKET — MGD obligation→test reconciliation + execution-status home

Operation `gmi-mining-fable-ceo-m1-integration-20260924-chairman-001` · seat `664a0650` · 2026-09-27
Status: SEAT-OWNED FINDING, not yet a program record. Lands with the T08 wave.

---

## §1 Why this packet exists

The delegation's acceptance criterion is "all forty MGD obligations executed on the
integrated candidate". T08 cannot discharge that criterion because **the obligation→test
link does not currently resolve**, and because **this program has no lawful place to
record execution status**. Both are structural, not bookkeeping, and both are cheaper to
raise now than at T08 — the same reason R-MIN-27 was raised early for T06.

## §2 The map is complete — that was the clean negative

`scratchpad/mgd_coverage.py` against Audit B §6:

```
assigned total : 40      duplicates : none
missing 1..40  : none    out of range : none
PARTITIONS 1..40 EXACTLY : True
```

**RECEIPT RE-DERIVED INLINE 2026-09-27 (wave 9).** `scratchpad/mgd_coverage.py` no longer
exists, so the block above was unverifiable by a later reader. No gate executed it, so nothing
was broken — but a measurement whose only receipt is a deleted file is prose, and R-MIN-33e
already requires the command inline. Re-measured at HEAD `d985e668c4ab` against the ledger itself,
reproducing the block above exactly (assigned 40, duplicates none, missing none):

```
python3 -c "import json,re;d=json.load(open('research/mining/m1_integration_program/MGD_EXECUTION_STATUS.json'));n=sorted(int(re.match(r'MGD-(\d+)\$',r['obligation_id']).group(1)) for r in d['obligations']);print(len(n),sorted({x for x in n if n.count(x)>1}),sorted(set(range(1,41))-set(n)))"
```

The concern that prompted this audit (only 16 distinct MGD ids appear across all program
records) was unfounded as a *map* defect. Every obligation has an owning task. Recorded so
no later wave re-audits it.

## §3 FINDING 1 — the canonical trace is unreachable from main

`research/mining/MINING_IMPLEMENTATION_TRACE_2026-09-24.json` (40 rows, the only artifact
that names a test per obligation) exists **only on carrier #7795's branch**:

- branch `origin/sol/mining-principal-research-20260923`, commit `eb6f05c0`
- `git merge-base --is-ancestor eb6f05c0 origin/main` → **NO**
- `classification: PLANNING_TRACE_NOT_NATIVE_ADMISSION`; all 40 rows `execution: NOT_RUN`

The seat may not touch that branch (standing constraint). So the artifact that would carry
execution status is one this program can neither update nor cite from a merged path.

**Proposed resolution (needs no new authority):** mint a program-owned artifact on main at
`research/mining/m1_integration_program/MGD_EXECUTION_STATUS.json`, which cites the carrier
trace the same way the trace pins its own spec — by `trace_commit` + `trace_blob` +
`trace_sha256` — and carries one row per obligation with the **delivered** test id, not the
planned one. The carrier trace stays the planning source of truth and is never edited; the
program records its own execution against it. This is the standing idiom, not a new one.

## §4 FINDING 2 — planned test names resolve for 2/40

`scratchpad/trace_reality.py` (measured, not inferred):

```
rows whose test exists on origin/main : 0/40
rows whose test exists at #7950 head  : 2/40
rows still NOT_RUN in the trace       : 40/40
```

Falsified against real files before reporting (`scratchpad/verify_names.py`): on main
`test_mining_shared_contract.py` has 15 tests and **neither** planned name; at #7950
`test_mining_composition.py` has 43 tests and only 2 of the 8 planned T04 names.

**RE-MEASURED 2026-09-27 (wave 9); the CONCLUSION is unchanged and now rests on a current
number.** Both cited scripts (`scratchpad/trace_reality.py`, `scratchpad/verify_names.py`) are
gone, and the `0/40 on main` figure was taken before #7950 merged — so the head it described no
longer exists. At HEAD `d985e668c4ab`: **40 of 40 rows carry a planned name and 2 resolve, so a
name-matching audit would report 38 false gaps TODAY** — the same figure §4 reported, which is
why the rule `status_is_never_inferred_from_a_test_name` is vindicated rather than merely
restated. The ledger's `authority.rationale` carries the dated re-measurement, and its
`measured_against.pin_integrity` block carries the converse check the original pair never ran:
every `delivered_test` ref resolving to a real `def`. That check has its own trap — the field is
sometimes a LIST and sometimes ONE string holding several comma-separated refs, and treating a
multi-ref string as one ref reports false dead pins (it did, on MGD-34 and MGD-39, both of which
resolve).

This is mostly a NAMING divergence, not a coverage hole — the delivered suites named their
tests after the *mechanism* pinned rather than the *obligation*. §5 resolves it per row.
**Consequence for T08: a name-matching audit would report 38 false gaps.** Never audit this
criterion by test name; audit it by the §5 table.

## §5 Reconciliation — T01' + T04 obligations against delivered tests

`COVERED` = a delivered test pins the obligation's full claim. `PARTIAL` = one clause pinned,
another not. `GAP` = no delivered test pins it.

| MGD | family | delivered test(s) | verdict |
|---|---|---|---|
| 01 | Reuse | `test_shared_contract_is_probed_lazily_and_is_two_armed_on_the_unmerged_base`, `test_shared_contract_degrade_is_typed_when_the_import_itself_fails`, `test_mining_code_and_tests_never_import_the_semiconductor_module`, `test_no_import_of_semiconductor_theme_research_anywhere` | PARTIAL by construction — the "no Mining copy" half is pinned four ways; the "one accepted shared validator **is imported**" half is pinned only as a lazy two-armed probe, because #7870 is not on main. Completes when #7870 merges; no action before then. |
| 04 | Reuse | — | DEFERRED-LAWFUL — legacy Robotics/Semiconductor parity cannot run until #7870 is on main. Audit B already ruled the shape: `xfail(strict=True)`. Not a gap. |
| 08 | Workflow | `test_copper_complete_is_ready_and_authority_literal_false`, `test_rare_earth_complete_is_ready_and_authority_literal_false`, `test_mgd08_clause2_wholly_empty_economic_path_degrades_on_both_slices` | **CLOSED 2026-09-27 — COVERED_SUITE_GREEN (R-MIN-35). The "PARTIAL — clause 2 UNPINNED" verdict below is SUPERSEDED, and its "measured behaviour is `degraded`" reading held on W-C only; W-R returned `ready` and a behaviour change shipped.** Historical verdict:  **PARTIAL — clause 2 UNPINNED.** Both positive witnesses are pinned. The clause "a wholly empty economic path **fails**" has no test: every `ready` assertion in the suite is positive (`== "ready"`, or `in {"ready","degraded"}`). Measured behaviour is `degraded` + named absence, which R-MIN-34 (§6.2) rules as satisfying "fails". Needs the pin, not a code change. |
| 09 | Identity | `test_missing_issuer_refuses_financial_join` | COVERED (renamed). |
| 10 | Identity | — | UNPINNED, satisfied by absence of capability; becomes live at **T03**. See §6.1. |
| 11 | Identity | `test_source_only_business_stays_useful` | COVERED (planned name shipped verbatim). |
| 12 | Identity | `test_duplicate_local_asset_labels_are_not_additional_supply` | COVERED (renamed); pins both the "additional physical supply" and "independent corroboration" readings via the same dedup path. |
| 15 | Measures | `test_composition_matches_the_frozen_truth_table[signed_loss-row9]`, `test_expected_oracle_shape_is_pinned_per_case[signed_loss-shape9]` | **ADDED 2026-09-27 — PARTIAL by construction.** Trace task **T03**, but the subject is T04a's native financial route, MERGED at #7950. Clause 1 (negatives keep their sign) pinned green through the real compose+validate route: −375 in → −375 out, `sign='-'`, no coercion. Clause 2 ("shared nonnegative fields are not bypassed") NOT EXPRESSIBLE on main — same #7870 shared-contract seam as row 01. Delivered contract's only nonnegative numerics are `request.page` (≥1) and the derived `context_block_count` (≥0), neither a financial value. |
| 16 | Measures | `test_packet_driven_missing_required_field_withholds_row_and_mints_unqualified`, `test_ir01_both_null_definitions_no_badge_no_model_readable_field` | **ADDED 2026-09-27 — PARTIAL by construction.** Subject is the COMPARISON channel, delivered by T04a (`mining_theme_research.py:802`), not unlanded T03 code: a leg missing a required definition field withholds the row and mints `definition_unqualified:<field>`. Pinned green both ways. `currency` and `attribution` are not definition fields on main (reserved set = unit / perimeter / basis / mev), so those two clauses arrive with T03. |
| 17 | Measures | `test_mgd17_refused_comparison_does_not_delete_the_supported_facts` | **ADDED 2026-09-27 — PARTIAL by construction.** The operative verb is "refuse dependent arithmetic" and no dependent arithmetic can exist: `economics['derived']` is literal `[]` on all 11 cases. Owes a pin in the PR that first populates `derived`. Its second clause ("without deleting supported facts") IS delivered and measured — a refused comparison leaves the supported block intact (expectations 0, blocks 1 @ 1250) — and is now **pinned green** by a test delivered in this wave, with a positive control arm; see §6.4. |
| 19 | Economics | `test_mgd19_an_intragroup_elimination_reaches_the_payload_with_its_sign` (do NOT credit `test_internal_transfer_keeps_elimination_sign`) | **ADDED 2026-09-27 — PARTIAL by construction; clause 2 PINNED in this wave.** The construct EXISTS on main (a packet `measure='intersegment elimination', value=-120` composes a block with sign `-`), so this is not absence of capability; what is missing is a casebook FIXTURE plus T03's product-sales vs contractual-support definitions. The existing test carries an MGD-19 docstring but calls the helper `_signed_value` directly and its own comment concedes the casebook "exposes no internal-transfer row" — **a helper pin is not a pin on the composed payload.** A PAYLOAD pin was therefore written in this wave: the elimination is submitted as a native packet and must reach `native_blocks` with `-120` / `sign='-'`, against two control arms (one block fewer without it; the neighbouring measurement identical). Clause 1 still needs T03's definitions. |
| 20 | Economics | — | **ADDED 2026-09-27 — SATISFIED by absence of capability.** `derived` is literal `[]` on all 11 cases, so no displayed derivation can lack receipts. Worth recording: the contract ALREADY mandates them — `derived[]` requires `formula_version` + `inputs` with `additionalProperties: false`, validated on every return path — so the first derivation cannot ship receiptless. The "browser does not invent arithmetic" half is unlanded T06. |
| 21 | Economics | `test_unsupported_contract_calculation_is_missing_derivation_not_invented_value`, `test_composition_matches_the_frozen_truth_table[same_horizon_revision-row8]` | **ADDED 2026-09-27 — PARTIAL by construction.** The protected behaviour is delivered and pinned green: a same-horizon revision is refused a derivation (`next_period_outlook` → `missing_derivation`, 0 expectations, 0 blocks) rather than relabeled. PARTIAL for one honest reason — the obligation is phrased "to satisfy `assess_management_sequence`" and **that symbol does not exist anywhere in the tree**, so the motive clause cannot be tested and must not be counted. |
| 22 | Economics | `test_rare_earth_usable_case_carries_slice_definitional_codes_only` | **ADDED 2026-09-27 — PARTIAL by construction.** Distinctness is enforced by the DELIVERED contract: `expectations[].is_range` and `.is_consensus` are `const: false`, validated on every return path, so a payload asserting consensus fails validation rather than shipping. The "labels and summaries" half is delivered too — `_BADGE_VOCABULARY` (beat/miss/improvement/above/below/confirmed/surprise) mints `definition_unqualified:headline`. PARTIAL because "house forecasts" has no delivered field at all. |
| 23 | Economics | — | **ADDED 2026-09-27 — GAP, reason corrected.** The composer is a PASSTHROUGH for `measure` (submitted 'financing proceeds' composes verbatim), and non-interpretation is not enforcement: it can neither substitute the four kinds nor keep them distinct. Needs T03 to mint the kind vocabulary first. A test asserting the passthrough would NOT pin this. |
| 18 | Rights | `test_missing_threshold_keeps_contract_explanation` (verbatim), `test_stream_threshold_omission_propagates_as_limitation`, `test_unsupported_contract_calculation_is_missing_derivation_not_invented_value` | PARTIAL — clause 2 (missing threshold blocks entitlement calculation) is pinned three ways. Clause 1 ("a royalty or stream is not encoded as physical mine ownership") is **satisfied by construction**: the engine models a stream only as the limitation code `stream_threshold_unknown` and carries **no ownership field at all**, so there is nothing to mis-encode. Standing condition, not a gap — see §6.3. |
| 34 | Safety | `test_copper_complete_is_ready_and_authority_literal_false`, `test_rare_earth_complete_is_ready_and_authority_literal_false`, `test_every_fixture_is_synthetic_and_all_authority_flags_are_false` (main) | COVERED ×3. |
| 39 | Coverage | `test_partial_coverage_industry_total_stays_null`, `test_industry_total_unknown_is_minted_iff_slice_vocab_contracts_it`, `test_industry_total_unknown_is_absent_on_w_c_slice` | COVERED — the `industry_total_unknown` family pins exactly "two witnesses do not imply complete coverage". |

**CORRECTED 2026-09-27 — the sentence that stood here was wrong and is withdrawn. It caused
six wrong statuses.** It read: ~~"T02/T03/T05/T06/T07/T08 rows are not reconciled here: their
tasks have not delivered, so their rows are legitimately `NOT_RUN` and a reconciliation would
be fiction."~~

That is a TASK-level rule applied to an obligation-level question — the denying-direction twin
of the hazard `MGD_EXECUTION_STATUS.json`'s authority block already names in the crediting
direction. **An obligation's OWNING TASK and the task delivering its SUBJECT are different
facts.** The carrier trace's `task` field is the planned delivery slot for the TEST; it never
says which code the obligation governs. Rows 15/16/17/19/20/21/22/23 above are the witnesses:
every one carries trace task T03, and six of them have subjects delivered by T04a with green
delivered tests, while this sentence told the ledger to record all of them `NOT_RUN`.

**The rule that replaces it:** reconcile every row by SUBJECT, clause by clause, never by
owning task. For each clause ask which of four places its subject lives in — (i) merged code,
(ii) the shared assertion contract, absent until #7870, (iii) an unlanded task's code, (iv) an
unlanded UI — and status from the closed vocabulary accordingly. `NOT_RUN` is lawful only when
NO clause's subject is on main. Two corollaries, each of which cost a wrong verdict this wave:
a delivered test whose docstring cites an obligation may still not PIN it (check it exercises
the composed payload, not a helper — row 19), and a clause may be pinned while the
obligation's OPERATIVE clause is not (row 15 clause 2). Rows whose subjects are wholly
unlanded — the T05/T06/T07 route, client, mount and update families, and the T08 real-source
journeys, which additionally need G2 before any live figure — remain `NOT_RUN` on that measured
basis. **COMPLETED the same day (wave 7).** The caveat that stood here — *"do not read this table as a completed 40-row subject audit"* — is withdrawn, because the audit it warned about is
finished. Every one of the 40 rows now carries a SUBJECT-level measurement in
`MGD_EXECUTION_STATUS.json`, and **no row explains its status by whether a task has landed.**
Wave 7 measured the 14 rows wave 6 had left plus the 8 it had read without writing their
evidence onto the rows:

- **MOVED to `PARTIAL_BY_CONSTRUCTION` on delivered, green, controlled pins** — MGD-05 (the
  `SLICE_ANCHORS` binding plus `slice_theme_mismatch`), MGD-24 (`time_mode` separates `latest`
  from `system_replay`, and replay without a cutoff refuses), MGD-27 (a refresh pairing changed
  quantities with stale causal text refuses), MGD-28 (`expected_generation_required` /
  `generation_changed`), MGD-29 (`route_unbound` with `read_count == 0`, identical for entitled
  and unentitled callers, **with a positive control that sets the counter to 3**), MGD-30
  (`live_admission == 'refused'` across the whole parametrized casebook).
- **Measured SUBJECT-ABSENT** — MGD-03/26/31/32/33/36/40: each obligation's own vocabulary
  occurs ZERO times across the delivered module, binding, schema and all seven suites.
- **Measured G2-GATED** — MGD-06/07/37/38: the unit is a real-source demonstration, which no
  test this program may write could satisfy, because every case is synthetic and live admission
  is refused by design. These are admission gates, not coverage gaps.
- **Measured OPERATIVE-CLAUSE-BLOCKED** — MGD-02/13/14/25: a later clause is already
  unviolatable (`ownership` 0 occurrences; `measure` copied verbatim; ordering by
  `stable_subject_id` only, never by time) while the FIRST clause needs T02's unlanded
  vocabulary. The unviolatable half must not be read as the row.

Two deliberate NON-moves are recorded on their own rows so a later lane does not "fix" them:
**MGD-35** stays `NOT_RUN` although the wiring that could violate it is absent, because the
hazard is entirely future and the row's whole value to a T07 lane is that it is still owed;
**MGD-38** stays `NOT_RUN` although half its vocabulary is delivered, because its unit is a
demonstration and half a demonstration is none. Counts after wave 7:
`COVERED_SUITE_GREEN 6 · DEFERRED_LAWFUL 1 · NOT_RUN 18 · PARTIAL_BY_CONSTRUCTION 12 ·
SATISFIED_BY_ABSENCE_OF_CAPABILITY 3 = 40`, `UNPINNED 0`, rederived from rows.

## §6.4 The one unblocked pin this program could still write — DELIVERED 2026-09-27

MGD-17's second clause — "refuses dependent arithmetic **without deleting supported facts**"
— is delivered and MEASURED but asserted nowhere. On the missing-`unit` shape the composer
returns `expectations == []` while the supported native block survives (measured: blocks 1 @
value 1250, limitations `['definition_unqualified:unit','omitted:expectations']`, status
`ready`), and the delivered test for that shape asserts only the withheld row. **DELIVERED in this wave** as
`tests/test_mining_composition.py::test_mgd17_refused_comparison_does_not_delete_the_supported_facts`,
which needed no upstream gate, no fixture and no ruling — it was the one piece of MGD coverage
work available while #7870 and #7905 are both closed. It carries a positive CONTROL arm: the
same bundle is composed without the bad comparison and the two native-block lists must be
identical, because "the block survived" proves nothing if the pipeline keeps blocks
unconditionally. Suite: **175 passed** (was 174). MGD-17 moved to `PARTIAL_BY_CONSTRUCTION`
as a result; its operative clause stays absence-of-capability and owes a pin in the PR that
first populates `derived`.

## §6 The two unpinned obligations, measured — neither is a code defect

I first classified both as GAPs and prescribed fixes. Probing the module
(`scratchpad/probe_mgd_08_10_v2.py`) refuted both prescriptions. **Recorded because a lane
handed the first version would have implemented the wrong behaviour** — and because the
first probe (`probe_mgd_08_10.py`) was itself wrong: it passed
`synthetic_case(..., bundle={...})`, but the fixture has no `bundle` key, so the override set
a new top-level key `_bundle()` never reads and the economic path was never emptied. The
casebook can only SET fixture keys, never delete them, and `financial_packets` is derived
from the presence of the `economics` key — **so the T04a casebook cannot express an empty
economic path at all.** Whoever writes the §6.2 pin must build the bundle directly
(`dataclasses.replace(case.bundle, financial_packets=())`) or add a fixture.

**RECEIPT RE-DERIVED INLINE 2026-09-27 (wave 9).** Both probes named here are deleted, so the
refutation that saved a lane from implementing the wrong behaviour had no reproducible receipt.
Re-measured at HEAD `d985e668c4ab` — the module shape the refutation turned on:

```
python3 -c "import sys;sys.path.insert(0,'.');from engine.market_ontology import mining_theme_research as c;from tests.mining_casebook import synthetic_case as s;k=s('copper_complete');p=c.compose_mining_research(k.query,k.bundle);b=p['economics']['native_blocks'][0];print(sorted(b),'period' in b,b['stable_subject_id'])"
```

```
['basis', 'measure', 'sign', 'source_label', 'stable_subject_id', 'value']
period present: False
stable_subject_id: '0000000421'
```

The behaviour half of §6 is no longer merely measured: waves 5–6 shipped the MGD-08 clause 2
behaviour fix and its pin, and R-MIN-35 amends R-MIN-34 with the reason the original
measurement generalized a copper-only result to both slices. Read that amendment before
re-using anything in this section.

### 6.1 MGD-10 — satisfied by absence of capability; becomes live at T03

> "Current issuer mapping is not used as historical asset ownership without an accepted
> time-valid bridge."

Measured at #7950 head: **zero occurrences** of `historical`, `time_valid`, `time-valid`,
`ownership`, `owned_at`, `as_of` across all eight mining test modules, the casebook, and the
engine module — and, decisively, **nothing in the payload pairs an issuer with a period**:

- `identity_results` fields are exactly `['cik', 'fictional', 'name']` — no validity window.
- a native economics block carries `['basis','measure','sign','source_label','stable_subject_id','value']`
  — **no `period`**. `stable_subject_id` is the issuer CIK (`'0000000421'`).

So the module makes no historical-ownership claim, because it cannot express a period on a
measurement at all. Same class as §6.3, not a defect. **It becomes falsifiable at T03**,
whose whole job is definition-safe economic inputs and whose `COMPARABILITY_FIELDS` already
names `period` — the first lane to put a period on a row attributed to a current-CIK-derived
`stable_subject_id` creates exactly the confusion MGD-10 forbids. **The pin therefore belongs
in T03's packet, not T04b's**, and `scratchpad/T03_FREEZE_PACKET.md` must carry it:
1. a case whose economics period precedes the issuer mapping's validity → attribution
   refused or degraded to a named limitation, asserted by exact code, never by truthiness;
2. the REVERSED case — same literals plus an accepted time-valid bridge → attribution minted.
   Without arm 2 the pin is satisfiable by refusing everything.

*Adjacent observation, not MGD-10:* "reported operating income" ships with no period at all.
A reported measure without a period is under-specified for a consumer even when it makes no
ownership claim. Raise with T03; do not fold it into this obligation.

### 6.2 MGD-08 clause 2 — **CLOSED 2026-09-27 (R-MIN-35); the claim below is PARTLY REFUTED**

> **CORRECTION ISSUED.** MGD-08 clause 2 is no longer UNPINNED: it is
> `COVERED_SUITE_GREEN`, pinned by `tests/test_mining_composition.py::test_mgd08_clause2_wholly_empty_economic_path_degrades_on_both_slices`.
> R-MIN-34's TARGET stands (`degraded` with a named absence, never `refused`), but its
> premise that the delivered code already MET that target was measured on COPPER alone.
> On W-R the path returned `ready` over a wholly empty panel, so a behaviour change was
> owed and has shipped. MGD-18 / R-MIN-15 / plan §6 is untouched and still green: its
> subject is a SUBMITTED block withheld pending a threshold (case
> `missing_stream_threshold` ships one packet), whereas clause 2's subject submits
> nothing. Retained below for the audit trail.


> "…a wholly empty economic path fails."

Measured: `financial_packets=()` → `summary.status == "degraded"`, `native_blocks == []`,
`limitations == ['omitted:expectations']`. With `omissions=()` as well, **identical** — the
absence is named regardless, so the `if not limitations` branch of `_summarize_status` is
unreachable for this input and my concern about an unnamed degradation was unfounded.

**R-MIN-34 (seat ruling, in-scope):** for a wholly empty economic path, `degraded` with
`native_blocks == []` and the absence named in `limitations` SATISFIES clause 2. A hard
refusal is the wrong target: this program's design law is truthful degradation with named
absence (R-MIN-15 keeps the contract explanation and stays `ready` for a missing threshold;
"unknown data is never zero"), and forcing a refusal would destroy the source-only
usefulness MGD-11 requires. My first prescription — assert `status NOT in {"ready","degraded"}`
— is **withdrawn**; a lane implementing it would have broken MGD-11 to satisfy MGD-08.

**Required pin** (test only, no code change): `status == "degraded"` AND
`native_blocks == []` AND the absence limitation present by exact code — with `==` against
the exact status, never `!=`. The reverse arm is already shipped (both complete cases return
`ready` with a populated block), so this closes the pair.

### 6.3 MGD-18 clause 1 — standing condition, not a gap

Satisfied by absence of capability: there is no ownership field to mis-encode. **The moment
any lane mints an ownership or entitlement-quantity field, this clause becomes falsifiable
and needs a pin in the same PR.** Record as a `danger_areas` entry, not as work.

## §7 Delivery gates for the T08 wave

Not done unless:
1. `MGD_EXECUTION_STATUS.json` exists on a `claude/*` branch, cites the carrier trace by
   `commit` + `blob` + `sha256`, and carries 40 rows keyed by MGD id with the **delivered**
   test id per row — planned names appear only in a `planned_test` field, never as the link.
2. Every row's `execution` is one of `PASSED` (named test exists AND the suite ran green on
   that head) / `NOT_RUN` / `DEFERRED` with a reason / `GAP` with an owning task. A row may
   not claim `PASSED` from the presence of a test name alone — R-MIN-33f's lesson applied to
   records: presence is not conclusion.
3. **AMENDED 2026-09-27 by R-MIN-35 — MGD-08 is exempt from this item.** MGD-08 is now
   `COVERED_SUITE_GREEN`, pinned two-armed across both slices, and it WAS a code defect on
   the W-R slice: a wholly empty economic path returned `ready`. Do NOT revert it to
   `UNPINNED` to satisfy this criterion, and do NOT re-open the defect question — the
   measurement is in R-MIN-35 with its falsifying assertion recorded. The clause below
   ("neither may be recorded as a code defect, because §6 measured that it is not one")
   was measured on the COPPER slice alone and is WITHDRAWN for MGD-08. It continues to
   bind MGD-10, whose ledger status is `SATISFIED_BY_ABSENCE_OF_CAPABILITY` until T04b
   mints the `period` field that makes its second arm expressible. Original text, retained
   for the audit trail and still binding for MGD-10: ~~MGD-08 and MGD-10 are carried as
   `UNPINNED` with their owning task (T04b and T03 respectively), never as `PASSED`.
   Silently reconciling either into `PASSED` by pointing at a neighbouring test is the
   failure this packet exists to prevent — and neither may be recorded as a code defect,
   because §6 measured that it is not one.~~ The anti-pattern that clause guards against
   is UNCHANGED and still binds every row: a row may never claim coverage by pointing at a
   neighbouring test. MGD-08 does not claim it that way — it names a test written FOR it,
   which failed before the fix and passes after.
4. R-MIN-34 is tabled in the rulings file, **and R-MIN-35 — which amends it and closes
   the §6.2 pin — is tabled beneath it with R-MIN-34's row carrying the `AMENDED BY`
   marker.** No lane implements the §6.2 pin: it is already delivered.
5. The carrier trace at `eb6f05c0` is byte-unchanged — verified by re-reading its sha256, not
   by intent.

---

## §8 ADDED 2026-09-27 — what this wave landed against §3/§6/§7

- **§3's gap is CLOSED.** `MGD_EXECUTION_STATUS.json` is minted beside this packet. It cites the
  carrier trace by `commit` + `blob` + `sha256` (`eb6f05c097c1fd4cd1963945605d7ab7664498e2`,
  blob `37ccaa92c301667b176be80c3fa6fbdcece72665`, sha256
  `04b9635fe62ebb5cf7c2a6a713f01a4cfcbdb44235c4bd0cc0f1773070ada4ca`), records
  `reachable_from_main: false` and `seat_may_modify: false`, and carries one row per obligation id
  with an explicit status word — never `PASSED` inferred from a test name.
- **The partition is re-verified from the trace itself**, not from this packet's prose:
  T01 2, T02 3, T03 8, T04 8, T05 4, T06 4, T07 5, T08 6 = **40 exactly**, ids unique.
  §5's ten T01'/T04 rows resolve as **5 COVERED_SUITE_GREEN** (MGD-09/11/12/34/39),
  MGD-01 PARTIAL_BY_CONSTRUCTION, MGD-04 DEFERRED_LAWFUL, MGD-18 and MGD-10
  SATISFIED_BY_ABSENCE_OF_CAPABILITY, MGD-08 UNPINNED. §5's own table already said 5; a seat
  summary that said "6 COVERED" was wrong and is retracted here.
- **§6's two unpinned obligations are now TABLED, not just measured.** `R-MIN-34` carries
  MGD-08 clause 2 — `degraded` + `native_blocks == []` + the named absence SATISFIES "fails";
  a hard refusal is the wrong target — with the casebook-cannot-express construction note and the
  seat's own silently-ignored-override measurement error recorded against it.
- **A ruling this program had already SHIPPED was corrected in the same wave.** `R-MIN-33f`
  told every future lane to read `pending == 0` as green once the expected pack set is PRESENT.
  `R-MIN-33g` amends it: `ci-plan` COMPUTES the set (a docs-only diff gets a REDUCED set, not an
  empty one) and takes minutes to publish it, so a constant floor is unsatisfiable on a small
  plan; the expected set is the ci.yml RUN's job list for the exact head sha, completion is that
  run's `status == "completed"`, and absence is resolved only against the Actions API. Evidence is
  this seat's own #8060 mid-flight merge.
- **T04a is at PRODUCTION_PROOF.** #7950 merged `aff8b76cba6afa6ed03298a1814b059e317070a0`
  2026-09-27T03:33:28Z on concluded-green (run `36288053731` `completed`/`success`, 26 checks,
  0 pending, sole red the sanctioned `ci-authority/codex/merge-queue-pilot`), and Audit B's frozen
  GREEN gate re-run against main's own bytes gives **53 passed**.
- **Unchanged:** the dispatch position. #7950's merge unblocks no plan TASK — R-MIN-05 orders
  T01' → (T02 ∥ T04a) → T03 → T04b → T07, and **T02 is still gated on #7905** (another seat's
  DRAFT, never polled). What it unblocked was this records lane, which had been deferred only
  because tabling a ruling required a push to #7950 while its CI was in flight.
