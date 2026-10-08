# SLR-P0 — historical-source qualification, 2026-10-08

**Research decision: NOT_ADMITTED for the inspected source set.**
**Completed:** current source-contract and seven-file schema qualification; local offline evidence checker and 20 synthetic tests.
**Incomplete:** broader inventory, row-level coverage audit, empirical SLR study, and companion-code publication.
**Parent programme complete: false.** No SLR or protected prospective outcomes were opened.

## Publication and recovery boundary

This qualification report is the canonical continuation artifact on existing Macro PR **8645**, branch `sol/slr-p0-deep-research-20261007-c3`. Its initial report-only commit was `6bfe8df94a2e5ab8609afbc87a4625c2a5a1730c`, blob `8869fb0058c2804f790dd7df348a8b062b4b2107`, verified by readback.

The following GitHub create attempt for `qualification_2026-10-08/check_source_evidence.py` was blocked by OpenAI because its safety status could not be determined. A subsequent same-carrier read of that exact branch/path returned **404**. The refused write was not retried or transported in another form. This revision corrects the initial report's premature wording about published companion tests.

**NOT_CANONICALLY_PERSISTED:** `check_source_evidence.py`, `test_check_source_evidence.py`, `SOURCE_EVIDENCE_2026-10-08.json`, and `SOURCE_REVIEW_RESULT.json` exist as local conversation artifacts only. References below to those files do not claim they exist in GitHub. Their evidence is summarized in this report so the scientific frontier does not depend on an uncommitted code file. The final chat delivery records the report's corrected publication revision. No unresolved modifying effect is claimed: the refused code file was not found on its original carrier.

## 1. Assignment and source continuity

The current Chairman directive assigns this session continued SLR-P0 research leadership and the next qualification step, within the original research-only boundary. No production authority, new vendor purchase, collector, identity allocation, prospective launch or protected-outcome access is granted.

Protected Mastermind was re-read at `c7e47c859eb2925c5626931fd511800773ba09ac`, unchanged from the previously loaded INDEX, COLD_START, ACTIVE_EXECUTION, SESSION_RELIABILITY, WEB_CEO_DELEGATION and CLOSEOUT procedures. INDEX remains Skillpack 1.0.1/bootstrap 1. Macro source pin: `8aa1aca8c593982e722bbc666a221fdd82466f15`. Current AGENTS and CLAUDE blobs matched the previously read complete instructions.

PR 8645 recovered open, mergeable, unmerged, with no review/comment return, no labels, and original head `27632c4e5f8204132d2f8470f31b88d67868f57e`. The existing carrier was retained. The original ten-file package and frozen experiment v1.0.1 at `4136eebc1d57b6d6c682403f1735849c5f9589f4` are unchanged. No new workstream, competing branch, identity reader or execution owner was created. Direct work covered principal source judgment and a small deterministic local helper; no worker was asked to perform any refused operation.

## 2. Two independent demonstrated input failures

### Historical sectors remain unqualified

The observed sector file has 2,589 rows and exactly the same SHA-256 as the preceding audit. The preceding zero-era-correct result therefore applies to these unchanged bytes; it is not a freshly recomputed row statistic. Its collector explicitly describes current GICS/current SEC SIC classifications, not membership-era classification. Historical index membership cannot supply the missing historical sector. [S1]

### Historical issuer lineage is a separate blocker

Current `IssuerMaster` source explicitly states that it supplies current issuer/security relationships, has no `asof` argument, and must not be interpreted as historical lineage. Its D2B1 contract independently states the same limitation. An old security inception/effective date, present CIK/issuer ID, or migration timestamp does not establish the historical security-to-issuer relationship. [S2, S3]

**Consequently, fixing sector history alone cannot admit this experiment.** The study must exclude all listings of the subject's issuer using historically valid identity. Retain the existing Data OS identity authority; do not infer issuer equality from names, ticker roots, embeddings or an LLM. Do not create a second identity reader to make an unqualified mapping appear usable.

### Historical-date lookup is not historical proof

In the inspected `AliasRow.covers` code, legacy aliases with neither bound present can resolve for historical dates. The stronger native `polygon` route additionally requires known-time/evidence binding and decision-cutoff checks. Merely calling `resolve(..., on=past_date)` does not establish historical evidence for an unbounded legacy row. These are source-inspection findings, not executed tests of the canonical identity module or a general production-bug ruling. [S2]

The observed alias schema has `valid_from`, `valid_to` and `ingested_at`, but no `known_at`, `evidence_sha256` or `binding_sha256` fields. This does not prove the entire company lacks native reference bindings. It prevents treating this legacy table alone as a fully bound native-reference receipt. Additional evidence must come from its existing owner, not invented timestamps or hashes.

## 3. Successful seven-file observation

One read-only Studio Direct call completed with process receipt **94629**. It computed SHA-256 values and read Parquet footer/schema metadata from these exact files under `/Users/chriswong/Documents/Cluade/macro-main`. No decoded market outcome values were read, and no Git revision was inferred for the mounted data. Repository source revisions and mounted data digests remain separate.

| File | Rows | Bytes |
|---|---:|---:|
| `data/reference/security_master.parquet` | 2,382 | 79,371 |
| `data/reference/issuer_master.parquet` | 1,213 | 43,772 |
| `data/reference/vendor_aliases.parquet` | 6,037 | 41,898 |
| `data/reference/security_migrations.parquet` | 1 | 5,675 |
| `data/reference/issuer_migrations.parquet` | 3 | 5,549 |
| `data/breadth/sp1500_pit_sectors.parquet` | 2,589 | 53,409 |
| `data/breadth/sp1500_pit_membership.parquet` | 3,286 | 42,778 |

SHA-256 values, in the same order:

```text
3579d414734a24b229354ddf805913f9696081cd9878c490acd4b142cbdfa915
691c5c8f40fc797054adc936daa4c03e553d9b02b3f9a4db19f7829a7cd8af16
0045187fa98e00e369f635480ed62506df42460c696e083bbe523560e89783b6
d48e853e88956da229e15d89c5bb71dc3645afb9bffe6427d506e0ca0d99137a
b801b747606e5c48fef8c7f2ef39a7b35ce88063289ea9e8d4db7e42bec0c58e
cba7fc07da53a6230122fec5797b15163bbe3b31f78918839f5722e885c00de3
7b34316c0561619ba052f02036ec1fbe7fff3d00dcda3e7acb7dffda10582eca
```

The security-master schema contains security/issuer axes but no instrument-type field or historical issuer-lineage interval. Issuer/security migration receipts exist; their row counts do not establish complete historical lineage. Alias-bound columns exist, but their populated-row coverage was not measured this phase. Membership and sectors are byte-identical to the prior audit.

These are **file-row counts**, not distinct-security counts, qualified SLR events, independent shocks or statistical power. No updated parent-cohort count is claimed. The September 23 source-readiness audit is dated corroboration only. Its old dated-alias counts must not be reused as current observations. The older security-master specification identifies an OpenFIGI type source, but that pointer is not fresh qualification of its contents or historical coverage. [S4, S5]

## 4. Observation and permission limits

Two distinct read-only Studio calls were blocked by OpenAI because their safety status could not be determined: a cross-repository source-name inventory, and a current-reference row/alias/parent-join audit. Neither returned execution results or a process ID. They were not replayed, delegated or reformulated through another carrier. Further host investigation stopped.

**Company-wide discovery is incomplete.** Current issuer-state counts, dated-alias coverage, parent-symbol join coverage and OpenFIGI row qualification remain unknown. A refused read is not evidence that a dataset does not exist. The independent source/contract reads and successful metadata observation remain valid.

An optional download of the pinned identity source for local characterization failed a URL-viewing precondition and was not retried. The 20 local tests are of the new receipt checker, not runtime tests of `IssuerMaster` or `VendorAliasTable`.

No particular administrator remedy follows from the generic refusal messages. No account/model/provider switch, permission bypass, dummy write, or worker delegation was used to obtain a refused effect. Technical repository push permission, which was observed, did not override the separate code-write refusal.

## 5. Rights are not a new blanket blocker

The existing Massive entitlement record continues to document operator-confirmed historical/reference research rights. This phase does not reopen that global licensing decision, claim the enterprise licence is absent, or request another subscription. Dataset-specific conditions remain distinct where the provider designates them. No private agreement was read or published. [S6]

The narrower unresolved question concerns an identified replacement historical classification/lineage dataset: its scientific suitability, available coverage and permitted use. No replacement dataset was positively qualified. Family-level rights do not prove historical GICS files exist; incomplete discovery does not justify a purchase recommendation.

## 6. Local implementation and verification

`check_source_evidence.py` accepts an explicitly supplied JSON research receipt on stdin. It reads no Parquet files, joins no market rows, makes no network calls, resolves/mints no identity, opens no outcomes and grants no admission. It is an offline consistency helper, not a production/control gate or another Data OS reader.

It checks current-only versus historical claims, supplied provenance/coverage, unknown evidence, duplicate requirements, dataset-specific rights assertions and the outcome/production boundaries. It never converts file rows to qualified events. A recent ingestion date alone does not invalidate correctly sourced **final-vintage** historical research; an **as-observed** claim needs separate original-clock evidence.

Even a fully consistent packet reaches only `READY_FOR_INDEPENDENT_REVIEW`, always with `admission_granted=false`. The helper cannot verify the truth of claims, contracts, economic identity, event-specific lookbacks or actual permissions.

Twenty synthetic tests were written before implementation. The API scaffold produced **20 assertion failures / exit 1**. The implementation produced **20 passes / exit 0**, including a later full discovery run of this isolated package. The actual supplied evidence JSON reproduced two blockers (`historical_sector`, `historical_security_issuer`), three unresolved requirements (`historical_instrument_type`, `historical_vendor_alias`, `dataset_use_rights`), zero format errors and no admission. Rights uncertainty refers to replacement-dataset identification, not revocation of existing licensing.

Only the local checker package was tested. The Macro-wide suite, canonical identity runtime and empirical signal were not tested. The companion implementation/tests/evidence remain local-only after the GitHub code-write refusal; they are not installed or selected anywhere.

## 7. Exact remaining frontier and stop reason

**Do not open SLR outcomes.** The original 21-session endpoint, D+21..D+63 search, first-challenge rule, issuer exclusion and protected prospective boundaries are unchanged. Failure of source admission is neither a statistical null nor a kill of the hypothesis.

The next critical input is an immutable, owner-qualified historical reference package through an approved access path: dated sector semantics, security-to-issuer lineage, historical instrument types, period-correct vendor aliases, applicable use evidence, and coverage/exclusions. Economic valid-time must not be confused with today's observation or the file's ingestion date. Required pre-2014 estimation lookbacks also need coverage; a cohort-period heading is insufficient.

Use the existing Data OS/identity and classification owners. Acceptance must exercise same-issuer share classes, ticker reuse, rename versus issuer change, delistings, sector changes, end-exclusive aliases and ambiguous/missing evidence. Typed columns alone are not proof. Only after source review, access/authority and mechanical requirements pass may the frozen outcome-blind first-shock manifest be built.

No worker is executing this frontier. A later session must observe an allowed recovery condition or receive independently qualified evidence; a new chat or this report does not grant replay of refused actions. PR 8645 separately still needs independent research review and repository acceptance. Neither this publication nor local green tests prove merge, adoption, scientific validation or production.

**Actual stop reason:** the next data-dependent step is unadmitted; broader and row-level observations were refused; companion code publication was refused and reconciled; independent source-contract and local checker work is complete. **Mission complete: false.** No all-company absence claim, unresolved modifying effect, or background continuation is asserted.

## 8. No-redo and sources

Preserve the original report and protocol. Do not repeat the literature review, reuse the old empty branch, relabel current CIK/SIC/GICS as historical, create another identity system, relax the study, open CR1/AF1/RH1 outcomes, or hand refused commands to another worker.

All source references below use Macro `8aa1aca8c593982e722bbc666a221fdd82466f15`:

- S1: `collectors/sp1500_pit_sectors.py`, blob `04e9570f3984b3a298ff0949d19e1a8c9dd77a5f`; current header verified and data digest matched prior audit.
- S2: `lib/dataos/identity.py`, blob `ea8485596e57fd1e686bfdb9d75708a3a3845fda`; inspected ranges 1–70, 730–865, 865–1010.
- S3: `research/prophet_v4/d2/D2B1_FROZEN_CONTRACT_2026-08-19.md`, blob `3f981f636df04c78867b9605e6d0a5262a6f92d8`; sections 1–5.
- S4: `research/prophet_v4/r6_program/wave2/D03_SOURCE_READINESS_MATRIX_2026-09-23.md`, section 4; dated, not fresh row observations.
- S5: `research/MASTERMIND_SECURITY_MASTER_SPEC.md`, blob `48da25169f5b3a71d548cc203541330a867c4d48`; sections 0–1.
- S6: `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`, blob `3969a9aae918141b51baffbb0e17d8a2ec2485a0`; repository record, not the private agreement.

Immutable URL prefix: `https://github.com/mastermindx-market-intelligence/macro/blob/8aa1aca8c593982e722bbc666a221fdd82466f15/`.
