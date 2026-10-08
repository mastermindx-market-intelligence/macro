# SLR-P0 — historical-source qualification, 2026-10-08

**Research decision: NOT_ADMITTED for the inspected source set.**
**Phase result: current source-contract and schema qualification completed; broader inventory and row-level coverage audit were not completed because their tool calls were refused.**
**Parent programme: incomplete; SLR outcomes remain unopened.**

## 1. Leadership and exact scope

The current Chairman directive assigns this session continued SLR-P0 research leadership and the next source-qualification step. It does not expand the original research-only commission into production changes. The existing carrier remains Macro PR **8645**, branch `sol/slr-p0-deep-research-20261007-c3`. At recovery its head was `27632c4e5f8204132d2f8470f31b88d67868f57e`, open, mergeable, unmerged, with no review/comment return. No new competing branch, workstream, identity reader, collector, ledger or runtime job was created.

Protected Mastermind was re-read at `c7e47c859eb2925c5626931fd511800773ba09ac`, unchanged from the already-loaded INDEX, COLD_START, ACTIVE_EXECUTION, SESSION_RELIABILITY, WEB_CEO_DELEGATION and CLOSEOUT procedures. INDEX remains Skillpack 1.0.1/bootstrap 1. Macro source was pinned to `8aa1aca8c593982e722bbc666a221fdd82466f15`; AGENTS/CLAUDE blob checks matched the previously read complete instructions. The frozen experiment remains **v1.0.1 at `4136eebc1d57b6d6c682403f1735849c5f9589f4`**. It is neither amended nor rerun here.

This phase answers whether the identified historical-sector and identity inputs meet that frozen study. It does not inspect CR1/AF1/RH1 states or forward outcomes, SLR labels, live signals, or portfolio/trading controls. Direct work was retained for principal source judgment and a small deterministic local checker; no worker was commissioned to perform a refused operation.

## 2. What changed from the previous frontier

The previous frontier emphasized sector history. This phase establishes **two independent demonstrated input failures**, not one: current sector labels and current-only issuer lineage. It also distinguishes usable alias mechanics from evidence that an alias was historically correct.

### Historical sectors: the blocker is still present

The mounted sector Parquet has 2,589 rows and SHA-256 `cba7fc07da53a6230122fec5797b15163bbe3b31f78918839f5722e885c00de3`, identical to the previous audited file. Consequently the previous zero-era-correct finding still applies to these exact bytes; it is not a freshly recomputed row statistic. Its collector explicitly describes current GICS/current SEC SIC labels, not membership-era classification. Historical membership cannot supply the missing sector history. [S1]

### Historical issuer lineage: an independent blocker is now pinned

The current `IssuerMaster` implementation explicitly says that it answers current issuer/security relationships, supplies no `asof` argument, and must not be interpreted as historical lineage. The frozen D2B1 contract says the same thing. An old security inception/effective date, current CIK, present issuer ID, or migration timestamp does not establish which issuer a historical security belonged to at the study landmark. [S2, S3]

This changes sequencing: sourcing historical sectors alone cannot authorize the experiment. The source must also support historical security-to-issuer relationships so every listing of the subject's issuer can be excluded from peers. Keep the existing Data OS allocator/reader authority; do not infer equality from company names, ticker roots or an LLM. The canonical reader remains the incumbent owner, not a new SLR identity implementation.

### A historical-date alias lookup is not itself historical evidence

The inspected `AliasRow.covers` implementation accepts a legacy row with both bounds absent for historical dates. Its stronger native `polygon` route checks `known_at`, evidence/binding digests and a decision cutoff; the legacy route does not acquire those facts simply because `resolve(..., on=past_date)` is callable. These are code-inspection findings, not an executed test of the canonical module or a general production bug claim. [S2]

The current alias Parquet has `valid_from`, `valid_to` and `ingested_at`, but its observed schema does not include `known_at`, `evidence_sha256` or `binding_sha256`. Their absence does not establish that every company source lacks native bindings. It does mean the legacy table is not automatically a complete native-reference receipt. New facts must come from the existing source owner, not be synthesized by filling fields with today's timestamp or the whole-file digest.

## 3. Actual successful source observation

One read-only Studio Direct call completed with process receipt **94629**. It computed file digests and read Parquet footer/schema metadata from the seven exact files below. No decoded market outcome values were read. The root was `/Users/chriswong/Documents/Cluade/macro-main`; no Git revision of that mounted data was inferred. Repository source pins and mounted data digests are separate evidence.

| Observed file | Rows | Bytes | What this establishes |
|---|---:|---:|---|
| `data/reference/security_master.parquet` | 2,382 | 79,371 | Current master exists; schema has security/issuer axes but no historical lineage interval or instrument-type field |
| `data/reference/issuer_master.parquet` | 1,213 | 43,772 | Issuer metadata exists; not proof of historically dated issuer memberships |
| `data/reference/vendor_aliases.parquet` | 6,037 | 41,898 | Alias rows and validity-bound columns exist; dated-row coverage was not measured this phase |
| `data/reference/security_migrations.parquet` | 1 | 5,675 | A correction receipt exists; one migration is not complete security history |
| `data/reference/issuer_migrations.parquet` | 3 | 5,549 | Issuer corrections exist; three receipts are not a general issuer-lineage table |
| `data/breadth/sp1500_pit_sectors.parquet` | 2,589 | 53,409 | Byte-identical to the previously audited current-classification artifact |
| `data/breadth/sp1500_pit_membership.parquet` | 3,286 | 42,778 | Byte-identical to the previous membership artifact; membership and classification are distinct |

Full SHA-256 values and field inventories are in `SOURCE_EVIDENCE_2026-10-08.json`. These counts are file rows, not distinct securities, qualified parent episodes, eligible shocks or statistical power. No updated parent cohort count is claimed.

An earlier September 23 source-readiness study reported mostly undated aliases and limited historical issuer coverage. It is retained as dated corroboration, not presented as today's row-level result. The older security-master specification also identifies an OpenFIGI type-mapping source. That reference is a candidate pointer, not proof that its current contents or historical coverage qualify. [S4, S5]

## 4. What could not be observed

Two distinct read-only Studio calls were blocked by OpenAI because their safety status could not be determined: a cross-repository source-name inventory, and a current-reference row/alias/parent-join audit. Neither returned execution results or a process ID. They were not replayed, delegated, or rephrased through another carrier. Further host investigation was stopped.

Therefore **company-wide discovery remains incomplete**, and current issuer-state counts, alias date-range counts, parent-symbol coverage, and OpenFIGI row qualification are unknown. In particular, do not reuse the old seven-dated-alias count as a current observation. Do not classify a refused read as proof that the data are absent.

An optional download of the pinned identity source for local runtime characterization also failed a URL-viewing precondition and was not retried. The published synthetic tests are of the new offline evidence checker, **not** runtime tests of `IssuerMaster` or `VendorAliasTable`.

These refusals do not invalidate the successful seven-file metadata observation or the independent GitHub source/contract reads. They do limit the completeness of the source census. No specific administrator fix is established by the generic refusal text; no new account, permission bypass or provider switch is proposed.

## 5. Rights: do not invent another blanket licensing gate

The existing Massive entitlement record continues to document operator-confirmed historical/reference research rights. This phase does not reopen that global licensing decision or claim the enterprise licence is absent. The same record reserves dataset-specific conditions where a provider designates them. [S6]

The narrower unresolved question is whether an **identified historical classification/lineage dataset** both satisfies the scientific contract and falls within its existing permitted use. No such replacement dataset was positively qualified here. A family-level entitlement does not prove a historical GICS file exists; an inability to inspect the estate is not a reason to recommend another purchase. No credential, agreement text, new feed or subscription was accessed or changed.

## 6. Independent work completed: an offline evidence-review checker

`check_source_evidence.py` checks a supplied JSON research receipt. It never opens a Parquet file, joins market rows, fetches data, resolves/mints identities, calls a provider, reads outcomes or grants admission. It is an artifact-consistency helper, not a second Data OS reader or execution/control gate.

It distinguishes current-only from historically supported claims, verifies that asserted coverage and provenance are structurally complete, preserves unknown evidence, rejects generic provider rights as proof about an unidentified dataset, and prevents row counts from being reported as qualified events. It also preserves the important distinction that **recent ingestion is not itself leakage in a properly sourced final-vintage historical study**. As-observed claims require a separate original-clock proof reference.

Even its best result is `READY_FOR_INDEPENDENT_REVIEW`, always with `admission_granted=false`. It cannot determine whether supplied assertions are true, validate per-event lookbacks, establish economic identity, verify contracts, or authorize this study.

Twenty synthetic tests were written before implementation. The API scaffold produced **20 assertion failures / exit 1**; the implemented checker produced **20 passes / exit 0**. The tests include current-only sector/issuer rejection, missing type evidence, unproven alias bounds, duplicate evidence, partial date coverage, malformed dates/booleans, final-vintage timing, as-observed clock requirements, outcome/production boundaries, generic rights and input immutability. Only this isolated package was tested; the Macro-wide suite and canonical identity runtime were not run.

The real supplied-evidence packet yields two blockers (`historical_sector`, `historical_security_issuer`), three unresolved requirements (`historical_instrument_type`, `historical_vendor_alias`, `dataset_use_rights`), zero receipt-format errors, and no admission. Rights uncertainty is dataset identification/qualification, not cancellation of existing licensing. `SOURCE_REVIEW_RESULT.json` preserves the output.

## 7. Exact remaining frontier

**No empirical SLR outcome run is justified.** The original 21-session endpoint, D+21..D+63 event search, first-challenge rule, issuer exclusion and protected prospective boundaries remain unchanged. A source failure is still not a null or a kill of the hypothesis.

The next critical input is an immutable, owner-qualified historical reference package through an approved access path: dated classification semantics; security-to-issuer lineage; historical instrument types; period-correct vendor aliases; dataset-specific permitted-use evidence; and coverage/exclusion receipts. Historical dates must describe economic validity, not merely current observations. Relevant pre-2014 estimation lookbacks must also be covered; a cohort-period header alone is insufficient.

The existing Data OS/identity and classification owners should provide or qualify that package without changing their production allocator or propagating current mappings backward. The operative acceptance tests include genuine same-issuer share classes, ticker reuse, rename versus issuer change, delisted securities, classification changes, end-exclusive alias bounds and ambiguous/missing evidence. Positive typed fields alone are not acceptance.

Only after source review, applicable access/authority gates, and the frozen mechanical fixtures pass may the same research project construct an outcome-blind first-shock manifest. No worker has been dispatched for the refused reads. A future session must observe a permitted recovery condition or receive independently qualified evidence; a new chat or this handoff does not grant replay permission.

PR 8645 also still needs independent research review and ordinary repository acceptance. This addendum is publication of the qualification result, not a merge, adoption, executed study or production proof.

## 8. Recovery and no-redo

Continue from this directory and the original frozen protocol, not another literature review. Do not recreate the original ten-file report or the old empty branch. Do not relabel current CIK/SIC/GICS, mint another identity, relax the cohort, open CR1/AF1/RH1 outcomes, or send the refused host operations to another worker.

Confirmed effects are limited to local research artifacts and their separately verified GitHub publication. No production/market-data files, remote process configuration, runtime jobs, protected experiments or source identities were modified. No modifying effect is unresolved. The inherited research PR is retained; the final publication receipt records the new head.

**Stop reason:** the next data-dependent experiment step is not admitted, wider/row-level observations were refused, and the independent source-contract/checker work is complete. **Mission complete: false.** This is not an all-company claim that no historical source exists. Current mode metadata were not attested; no model switch or continuing background execution is claimed.

## Source references (all Macro source at the pinned revision)

S1. `collectors/sp1500_pit_sectors.py`, blob `04e9570f3984b3a298ff0949d19e1a8c9dd77a5f`; previous audit and matching mounted source digest.
S2. `lib/dataos/identity.py`, blob `ea8485596e57fd1e686bfdb9d75708a3a3845fda`, inspected ranges 1–70, 730–865 and 865–1010.
S3. `research/prophet_v4/d2/D2B1_FROZEN_CONTRACT_2026-08-19.md`, blob `3f981f636df04c78867b9605e6d0a5262a6f92d8`, sections 1–5.
S4. `research/prophet_v4/r6_program/wave2/D03_SOURCE_READINESS_MATRIX_2026-09-23.md`, section 4; dated audit, not fresh table counts.
S5. `research/MASTERMIND_SECURITY_MASTER_SPEC.md`, blob `48da25169f5b3a71d548cc203541330a867c4d48`, sections 0–1; historical specification, not current liveness.
S6. `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`, blob `3969a9aae918141b51baffbb0e17d8a2ec2485a0`; repository entitlement record only, no private agreement accessed.

Use the immutable prefix `https://github.com/mastermindx-market-intelligence/macro/blob/8aa1aca8c593982e722bbc666a221fdd82466f15/` plus each path. Sources support only the stated bounded claims; source comments are not a substitute for missing content-level observations.
