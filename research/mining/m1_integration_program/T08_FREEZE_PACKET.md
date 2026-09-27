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
| 08 | Workflow | `test_copper_complete_is_ready_and_authority_literal_false`, `test_rare_earth_complete_is_ready_and_authority_literal_false` | **PARTIAL — clause 2 UNPINNED.** Both positive witnesses are pinned. The clause "a wholly empty economic path **fails**" has no test: every `ready` assertion in the suite is positive (`== "ready"`, or `in {"ready","degraded"}`). Measured behaviour is `degraded` + named absence, which R-MIN-34 (§6.2) rules as satisfying "fails". Needs the pin, not a code change. |
| 09 | Identity | `test_missing_issuer_refuses_financial_join` | COVERED (renamed). |
| 10 | Identity | — | UNPINNED, satisfied by absence of capability; becomes live at **T03**. See §6.1. |
| 11 | Identity | `test_source_only_business_stays_useful` | COVERED (planned name shipped verbatim). |
| 12 | Identity | `test_duplicate_local_asset_labels_are_not_additional_supply` | COVERED (renamed); pins both the "additional physical supply" and "independent corroboration" readings via the same dedup path. |
| 18 | Rights | `test_missing_threshold_keeps_contract_explanation` (verbatim), `test_stream_threshold_omission_propagates_as_limitation`, `test_unsupported_contract_calculation_is_missing_derivation_not_invented_value` | PARTIAL — clause 2 (missing threshold blocks entitlement calculation) is pinned three ways. Clause 1 ("a royalty or stream is not encoded as physical mine ownership") is **satisfied by construction**: the engine models a stream only as the limitation code `stream_threshold_unknown` and carries **no ownership field at all**, so there is nothing to mis-encode. Standing condition, not a gap — see §6.3. |
| 34 | Safety | `test_copper_complete_is_ready_and_authority_literal_false`, `test_rare_earth_complete_is_ready_and_authority_literal_false`, `test_every_fixture_is_synthetic_and_all_authority_flags_are_false` (main) | COVERED ×3. |
| 39 | Coverage | `test_partial_coverage_industry_total_stays_null`, `test_industry_total_unknown_is_minted_iff_slice_vocab_contracts_it`, `test_industry_total_unknown_is_absent_on_w_c_slice` | COVERED — the `industry_total_unknown` family pins exactly "two witnesses do not imply complete coverage". |

T02/T03/T05/T06/T07/T08 rows are not reconciled here: their tasks have not delivered, so
their rows are legitimately `NOT_RUN` and a reconciliation would be fiction.

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

### 6.2 MGD-08 clause 2 — R-MIN-34: `degraded` + named absence satisfies "fails"

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
3. MGD-08 and MGD-10 are carried as `UNPINNED` with their owning task (T04b and T03
   respectively), never as `PASSED`. Silently reconciling either into `PASSED` by pointing at
   a neighbouring test is the failure this packet exists to prevent — and neither may be
   recorded as a code defect, because §6 measured that it is not one.
4. R-MIN-34 is tabled in the rulings file before any lane implements the §6.2 pin.
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
