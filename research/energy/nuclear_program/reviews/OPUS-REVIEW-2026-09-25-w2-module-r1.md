# Opus READ_ONLY review — Energy W2 nuclear vertical module, round 1

Artifact: PR #8002 (DRAFT; base `claude/energy-stack-base-b-6cd958e9` = #7870 @ `6cd958e92b259f7221690547e7076f4a0de4ed33`) at head `1071dd9de3e9857278424e06b6270bb82161b9e2`. Its three lane commits are `3bf11062fc` (pure composer), `37ece12659` (synthetic assertion corpus) and `1071dd9de3` (law tests). Reviewer: Opus `reviewer`, MODE READ_ONLY, 2026-09-25, finished before the fix round was dispatched at 09:06Z.

Verdict: **FIX_REQUIRED** — 1 blocker (B1), 5 major (M1–M5), 7 minor (m1–m7) and 3 nits. Shell fit and registration shape hold.

Seat adjudication: rulings R-ENE-10..16 in `research/energy/nuclear_program/rulings/R-ENE-2026-09-25-w2-module-r1.md`. Where a ruling and the text below differ, the ruling binds. m3 is promoted to MAJOR (R-ENE-11); m6 and the loader-import nit are overridden (R-ENE-13, R-ENE-14).

Everything below the rule is the reviewer's return, verbatim. It reported `STATUS: FAIL` only because its return contract admits nothing but PASS/PARTIAL/BLOCKED/FAIL. Its probe support files lived only in the reviewer's `$TMPDIR`.

---

STATUS: FAIL

RESULT:
Verdict on PR #8002 at head `1071dd9de3e9857278424e06b6270bb82161b9e2`: **FIX_REQUIRED** (reported as STATUS FAIL because the return contract only accepts PASS/PARTIAL/BLOCKED/FAIL). There is 1 blocker, 5 major and 9 minor/nit findings. The module fits B's shell cleanly (no mirror, direct imports, registration reconciles). The problems are one missing Robotics behaviour and several tests that stay green for the wrong reason.

**BLOCKER**
- **B1 — Republished stories are not collapsed, while the contract says they are (round-1 lead, confirmed).**
  - The composer has no `_apply_syndication` step. `engine/market_ontology/nuclear_theme_research.py:341-342` hard-codes `"independent_source_count": 1, "corroboration_refs": []`.
  - The contract promises the collapse:
    - `contracts/market_ontology/nuclear_theme_research.v1.schema.json:1293`: "Syndicated copies collapse into the original's count and are listed under corroboration_refs, never counted."
    - `:483` says the same ("…supersession or syndication collapse").
  - Failing input: N04 plus a copy with publisher "Synthetic Wire" and `source_dependence="syndicated_copy_of:Synthetic Energy Filings"`. The nuclear composer emits two independent rows (both value 100, `corr []`) and no `syndicated_collapsed`. Robotics on origin/main, given the same input, emits one row with the copy under `corroboration_refs`, plus `syndicated_collapsed`. Output is in EVIDENCE P1/P1b.
  - Why it blocks: one story reads as two independent sources in a new public contract that later Energy verticals will copy. The packet asked to mirror Robotics' section builders and did not authorise dropping this.

**MAJOR**
- **M1 — L5: a passed target can still read as live.** `nuclear_theme_research.py:97-105` marks a passed target only when `query.source_cutoff` is a string. The route's default `latest` body sends no cutoff.
  - N03B (window ended 2026-01-31) in latest mode with no cutoff gets `retrospective: False`, so it reads as a live target.
  - The reverse also happens: in `source_history`, N03 (window 2027-12-31, not passed) gets `retrospective: True`. The shared archival rule (`retained_at` 09-20 &gt; `published_at` 09-19 in every fixture) sets the same flag.
  - The flag now carries two meanings and neither is reliable.
- **M2 — The L5 temporal test passes for the wrong reason.**
  - `tests/test_nuclear_research_temporal.py:20-21` builds `{value: retrospective}`. N03 and N03B share value 6, so the dict collapses them into one entry and it asserts `{6: True}`, which the archival rule produces on its own.
  - Mutant "delete the passed-target branch" (`_is_passed_target = _is_retrospective`): this test SURVIVES.
  - `test_passed_forward_target_stays_a_retrospective_target` only kills it because it feeds `source_cutoff` into a latest-mode query, which the production default never sends.
- **M3 — The L8 test cannot see a sort by size.** The mutant `_row_sort_key = -(observation.value)` SURVIVES `test_rows_order_is_deterministic_never_by_magnitude` (`tests/test_nuclear_research_composition.py:105-112`). The correct selector order is already [200, 100], i.e. largest first, so the fixture cannot tell the two apart.
  - The test also asserts against a key the code does not use. Nuclear's `_ROW_ORDER` at `nuclear_theme_research.py:64` is unused, because the code sorts with the imported semiconductor `_row_sort_key` (selector, source_business_label, configuration, stage, curation_revision).
  - The L8 behaviour itself holds; the test does not prove it.
- **M4 — The L7 test only proves the backup path, and never checks evidence.**
  - `test_unmapped_rights_source_is_excluded_from_rows_and_evidence` (`composition.py:91-95`) asserts only `rows == []` and `unmapped_rights_source_excluded:1`. It never checks `evidence_refs` or `select_authorized_evidence`, despite its name.
  - It exercises only the composer's defence-in-depth branch. In production, the route's `_filter_bundle_for_rights` drops X02 first and the limitation is `rights_refused_families_hidden` (EVIDENCE P7), so the tested branch is never reached.
  - Per the seat note, this is MAJOR.
  - The composer code itself is acceptable: it calls the shared `engine.theme_graph.rights.family_for_source_ref` (`:156`) with no local prefix table.
- **M5 — Drop counts are hard-coded and false.** `nuclear_theme_research.py:154` emits `"witness_cohort_excluded:1"` and `:157` emits `"unmapped_rights_source_excluded:1"`, whatever the actual number of drops.
  - Two mis-faceted CCJ assertions give `['witness_cohort_excluded:1']`.
  - Two nrc.gov assertions give `['unmapped_rights_source_excluded:1']`.
  - The packet requires drops to be counted, so these tokens state a wrong number.

**MINOR / NIT**
- **m1 — "Robotics" wording in the Nuclear contract (round-1 lead).** Lines 378, 943, 966, 1094 and 1098 say "Robotics v1…". None of it is emitted or tested, and each statement is true for Nuclear apart from the vertical's name. Rewording fixes it; this cannot stay in a public contract at merge. (The false statements at :483 and :1293 belong to B1.)
- **m2 — The L1 tests miss the paths they claim.**
  - `composition.py:37-41` checks rows only; the packet says rows AND evidence.
  - `composition.py:22-28` never reaches the cohort gate, because fuel_cycle rows fail the facet gate first.
  - The check `"nuclear_power membership" not in str(payload)` cannot fail in practice.
- **m3 — L2: the milestone leaks outside `limitations`.** The summary echoes `establishes[0]` as `next_evidence` with `label: "target"`: "a separate test reactor reached first criticality (technical milestone)". This happens even for the passed N03B. It is inherited from Robotics' `_text_of`.
- **m4 — Wrong label for business-only subjects.** `_native_subjects` gives `source_label: "biz:BWX Technologies"` (`nuclear_theme_research.py:432`); Robotics strips the prefix. `app:` selectors are also dropped.
- **m5 — Summary and companies are thinner than Robotics, without packet authority.**
  - The summary ignores `interpretation_blocks` (no mechanism/offset/falsifier, no stale marking) and omits `reason` when nothing is current.
  - `_companies` never reports `degraded`/`identity_incomplete`.
  - `_ownership_role` is missing, so OWNERSHIP_EVENT roles are always "subject".
- **m6 — The contract does not pin the new limitation codes.** The limitations field is pattern-only, as in Robotics. The packet asked for an extended enum; `supplemental_basket_witnesses` and `milestone_predicate_unavailable` appear only in a description.
- **m7 — L4 test is empty.** `test_equity_method_investee_never_consolidated` uses N09, which carries no figure, so there is nothing that could be added or netted.
- **nit — Owner-bundle test name.** `test_bundle_declares_exactly_three_absent_surfaces` asserts two omissions.
- **nit — Loader imports.** `nuclear_owner_bundle.py:8` imports `OwnerBundle`/`ResearchQuery` through the nuclear composer and does not import the cohort (round-1 MINOR-2). The cohort lives once in the composer, but the "imported by the other" wording is not met.
- **nit — Selector with no business.** `_subject_selector` can produce `"prd:None/&lt;product&gt;"` when the business label is missing (`:77`).

**L1–L9**

| Law | Verdict | Evidence / note |
|---|---|---|
| L1 | HOLDS in code | Cohort gate `:153` feeds rows and evidence; `supplemental_basket_witnesses` added `:131-132`. Tests weak (m2); count false (M5). |
| L2 | HOLDS for rows | Summary leak m3. |
| L3 | HOLDS | Totals null; both backlog rows echoed verbatim (`composition.py:62-71`). |
| L4 | HOLDS | No arithmetic anywhere; test empty (m7). |
| L5 | **BROKEN** | M1, M2. |
| L6 | HOLDS | Expectations/economics stay typed-unavailable; nulls stay null. |
| L7 | HOLDS in code; proof inadequate | Shared resolver, no local table; route drops X02 (P7). Test gap M4; count M5. |
| L8 | HOLDS in code | `AUTHORITY` all false; no score/rank/size field. Test cannot catch a size sort (M3). |
| L9 | HOLDS | Import-closure test pins the Robotics forbidden set. Composer does no I/O. The loader reads the rights registry only when no snapshot is passed, as Robotics does. |

**Shell fit (review standard point 2): holds.**
- Top-level `required` is identical to the semiconductor and Robotics contracts.
- The contract is a structural clone of Robotics: it differs only in `$id`, `definition_version`, `slice_key` enum and `schema` const.
- Compose and select are module-level.
- `grep except ImportError` over the owned files is empty.
- `theme_node_id` is imported directly (`:28`).
- Omissions pass `wire_omission`.
- The name-only diff contains only owned files.
- Refusal codes are only the shared set.

**Registration (review standard point 7): holds.**
- `VerticalRegistration` and `MountFacts` pass their `__post_init__` validation, and the route accepted the entry (P7).
- `entry.compose.__module__` resolves to a module that carries `SCHEMA_ID`, `DEFINITION_VERSION` and `EVIDENCE_SCHEMA_ID`, so `test_every_registration_reconciles_with_its_own_vertical_module` would pass.
- Adding it to `_ENTRIES` later needs a module-level lazy loader wrapper; the test's `load_bundle` is a nested closure.

**Fixtures (review standard point 5):** every value is round and labelled synthetic (77 MWe, 100/200 USD million, 50/40 CAD/kgU, 3/1 USD billion, 5 kg), and every URI is `.../edgar/data/synthetic/...`. Nothing looks copied from a real filing. The 77 MWe rating is the real public NuScale module figure, which the packet itself specifies.

EVIDENCE:
- **Head and diff.**
  - `git rev-parse HEAD` returned `1071dd9de3e9857278424e06b6270bb82161b9e2`.
  - Name-only diff `6cd958e9...1071dd9d`: `contracts/market_ontology/nuclear_theme_research.v1.schema.json`, `engine/market_ontology/nuclear_owner_bundle.py`, `engine/market_ontology/nuclear_theme_research.py`, `tests/nuclear_research_helpers.py`, `tests/test_market_ontology_nuclear_theme_research.py`, `tests/test_nuclear_owner_bundle.py`, `tests/test_nuclear_research_composition.py`, `tests/test_nuclear_research_inputs.py`, `tests/test_nuclear_research_temporal.py`. Stat: "9 files changed, 2779 insertions(+)".
- **Nuclear suites:** `python3 -m pytest tests/test_market_ontology_nuclear_theme_research.py tests/test_nuclear_research_composition.py tests/test_nuclear_research_temporal.py tests/test_nuclear_research_inputs.py tests/test_nuclear_owner_bundle.py -q -p no:cacheprovider` gave `29 passed, 89 warnings in 4.28s`.
- **Adjacent shared suites** (the 7 `.py` files from the packet's `git ls-files` grep) gave `10 failed, 298 passed, 101 skipped, 99 warnings in 12.28s`. Nine of the ten failures read `ENOENT … site/assets/js/theme-research.js` or a matching FileNotFoundError, because site/ is absent in this sparse tree; I did not open the tenth. The nuclear diff touches no shared file.
- **Checks.**
  - `/opt/homebrew/bin/pyflakes` over the 8 owned `.py` files gave `pyflakes_rc=0`.
  - `grep -n "except ImportError"` over the owned files returned nothing (`grep_rc=1`).
  - The contract structural diff against Robotics gave `required n==r True n==s True`, `props n==r True`, `defs n-r [] r-n []`.
- **Probe** (`$TMPDIR/probe_nuclear_8002.py`, second run), verbatim:
  - P1 (nuclear): `row gmirca_05e700cef 100 isc 1 corr [] dep syndicated_copy_of:Synthetic Energy Filings` / `row gmirca_19e5946e5 100 isc 1 corr [] …` / `syndicated_collapsed in limitations: False`
  - P1b (Robotics, origin/main): `row gmirca_27b49fcb7 100 isc 1 corr ['gmi-curation://theme:robotics_automation/gmirca_28b21896…']` / `syndicated_collapsed in limitations: True`
  - P2: `MUTANT SURVIVES (test green under magnitude-desc sort)` / `real order values: [200, 100]`
  - P3: `latest/no-cutoff N03B(valid_to 2026-01-31) retrospective: False` / `source_history N03(valid_to 2027-12-31, NOT passed) retrospective: True` / `mutant(passed-target branch deleted) SURVIVES temporal.test_source_history_preserves_rows_and_passed_target_is_retrospective` / `mutant killed by temporal.test_passed_forward_target_stays_a_retrospective_target`
  - P4: `two misfaceted -&gt; limitations: ['witness_cohort_excluded:1']` / `two nrc.gov -&gt; limitations: ['unmapped_rights_source_excluded:1']`
  - P5: `next_evidence: [{'text': 'a separate test reactor reached first criticality (technical milestone)', 'label': 'target', …}]`
  - P6: `[('biz:BWX Technologies', 'biz:BWX Technologies'), …]`
  - P7 (FastAPI 0.141.1 TestClient; the probe replaced `route.registration_for`, and the entry's own `load_bundle` supplied the bundle):
    - Synthetic bundle (N04 + X02): query `200 Cache-Control= private, no-store X-Robots-Tag= noindex, noarchive`; limitations `['milestone_predicate_unavailable', 'rights_refused_families_hidden', 'slice_scope_unowned']`; economics rows `[(100, …N04)]`; evidence_refs = N04 only. X02 was excluded by the route.
    - Real declared-absent loader: `200`, same headers; limitations `['milestone_predicate_unavailable', 'omitted:private_assertions_unbound', 'omitted:public_assertions_uncurated', 'slice_scope_unowned']`; coverage `unavailable 0`.
    - Evidence route for N04 and X02: `400 private, no-store noindex, noarchive` with `string_pattern_mismatch` on `assertion_ref`. See GAPS.
  - `git status --short` after the probe was empty.

GAPS:
- **Nuclear evidence cannot be reached end to end.** B's shell pattern at `app/theme_research.py:207` (`^gmi-curation://[a-z0-9_]+/gmirca_…`) rejects the `theme:nuclear_power` segment that the identity owner puts in every ref. It is not caused by this PR and needs B's owner. I could not observe the route's evidence-level rights refusal for X02 because of it; the query-level refusal was observed.
- **10 adjacent failures** from the missing site/ tree in this sparse checkout (9 confirmed as the missing `theme-research.js`, the tenth not opened). They need a full checkout to clear.
- **PR body not read.** I did not open the PR body (no `gh` call made), so I cannot confirm or refute its claims or the seat's HOLD-line check.
- **Not proven by mutant:** the claimed mutants (a), (b) and (e) were not re-run. I inferred from the test bodies that (a) and (b) would be caught.
- **L1 limit:** the shared company-row shape cannot carry the supplemental-basket relation, so L1 rests only on the limitation code and the slice label.

DEVIATIONS:
- STATUS is FAIL only because the return contract refuses FIX_REQUIRED; the verdict is FIX_REQUIRED.
- I used `/opt/homebrew/bin/pyflakes`, because `python3 -m pyflakes` is not installed for Python 3.14.
- The first adjacent-suite command passed JSON fixture paths to pytest and ran no tests; I re-ran it with an explicit `.py` list.
- The probe needed two attempts; the first failed in my own `ResearchQuery` constructor call for Robotics.
- Probe support files (`robotics_theme_research_main.py`, `robotics_schema.json`, `probe_nuclear_8002.py`) were written only under `$TMPDIR`. Nothing was edited, committed or posted in the worktree or on the network.
