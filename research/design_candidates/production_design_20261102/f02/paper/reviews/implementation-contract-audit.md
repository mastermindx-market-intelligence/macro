# F02 native implementation-contract audit

**Scope:** bounded, author-informed architecture and source check of the new native repair inputs.  
**Audit frozen:** 2026-11-03T06:07:36.111077+00:00  
**Disposition:** two concrete source inconsistencies require correction before the affected native candidate freeze. Both were reported promptly and accepted by the assignment owner; a separate agent is preparing versioned repairs. No correction is counted as applied or verified by this audit.

This is not a blind product/taste critique, admitted RIG review, native visual acceptance, browser test or release approval. No Paper, Browser or external service was called. No source/design file was changed. Only this report was written. Product/taste report contents were not read; their hashes appearing as provenance inside an authored input packet were not review input.

## Findings

### FCA-001 — Major: selected Macro source identity changes across width variants

**Observed source:** `paper/repairs/fixture-coherence-v1/effective-spaced/consumer-boards.json`, boards `macro-dark` and `macro-light`, step `evidence-field-0`.

Both desktop panels label this literal as **Source identity**:

`f02.fixture.v3/macro/sector/communication_services`

The 1280/1600 dock, 768/1024 modal, Chinese evidence/return and unavailable-source inspector identify the same selected observation with the full key:

`f02.fixture.v3/macro/sector/communication_services/share_above_50d/2026-10-30`

The selected entity, value, date and derived comparison otherwise agree. The short string is an entity prefix; it omits the metric and observation date. Treating it as the record identity would make a future builder infer an alias or change the selected evidence key when crossing the dock/overlay threshold. That conflicts with the stable evidence and return contracts in SOURCE_AND_DATA_CONTRACT §4 and INTERACTION_STATES §Focus, overlays and input details.

**Bounded correction:** use the full metric/date identity in both desktop `evidence-field-0` groups, with wrapping appropriate to the 320px inspector. Update the exact native Text bindings through the sole writer after a current target check. Preserve the row identity, amounts, clocks and return behavior; no producer ID or route is invented.

**Status at this audit freeze:** root accepted the finding and held the two affected native text updates. `/root/continuation_dependencies` was assigned a versioned source/key overlay. Prepared correction, native application, final rendered fit and immutable capture remain separate evidence.

### FCA-002 — Major: Company failure examples introduce an unsupported point-time observation clock

**Observed source:** `paper/repairs/fixture-coherence-v1/effective-spaced/fault-composition-inputs.json`, board `fault-compositions`.

| Step | Current conflicting copy |
| --- | --- |
| `empty-table-context` | `Source observed 30 Oct 2026, 20:00 UTC` |
| `retained-table-context` | `Original source 30 Oct 2026, 20:00 UTC · last successful retrieval 20:03 UTC` |
| `tabs-empty-panel` | `observation time 30 Oct 2026, 20:00 UTC` |
| `retained-table-error` | Refers generically to the rows' `original source date`, which should name the preserved clock after the correction. |

The same packet binds the retained Company rows to `fixtures/company-history.json`. That fixture supplies fiscal-period observations, publication `2026-10-30T20:02:00Z` and retrieval `2026-10-30T20:03:00Z`; it explicitly does not turn fiscal labels into calendar observation timestamps. The new 20:00 point time is not supplied for those Company records. It is used elsewhere as the Macro observation clock, but that does not establish a Company clock. Although these are illustrative fault scenarios, the packet describes the retained rows as keeping their original identities and facts, and does not define a separate Company point-time source record.

**Bounded correction:** preserve `FY 2025–2026` as the observation basis, state the known fixture publication at 20:02 UTC, and label 20:03 UTC as retrieval or last successful retrieval. Keep the requested periods and filters. Change the retained-error description to the original fiscal periods and publication clock. The unavailable table/chart already say `read attempted` and unavailable source time; those branches need no fabricated successful retrieval or observation clock.

**Status at this audit freeze:** root accepted the finding and held the affected Company fault groups. Exact keys/current strings were sent to the repair agent. The remedy must remain Company-scoped; Macro's actual synthetic 20:00 observation clock is not affected.

## Checks that reconciled

Independent arithmetic was calculated directly from integer/Fraction source values and Decimal rounding, without importing either authoring generator. The checks passed:

- All **45 Company annual amount/comparison cases**, including six supplied FY2021 baselines for the first displayed year, three absent priors, one missing current EPS, raw income/revenue margin differences, and four absolute zero dividend changes. All 45 table amounts match the retained fixture. The repair preserves the complete 17×5 history.
- **48 breadth display-label calculations** across the independent Universe, core component-sector and populated Macro-sector cohorts. Current/prior rates and pp differences reconcile; Energy has no numerator/rate when coverage is 0/82. The Universe and Communication sector remain different exact cohorts despite both displaying 66.7% at one decimal.
- Four decisive width calculations: 768px →384px hypothetical docked primary; 1024px →444px; 1280px →664px; 1600px →984px. The first two are below the proposed 640px primary minimum and therefore use overlays. The larger two support the proposed dock. Header/rail values match the documented source baseline, while F01 release remains explicitly provisional.
- Historical EPS selection maps to `rows[6][5] = 2.07`, compares with `rows[6][4] = 1.20`, and yields **+72.5%**. The return contract correctly requires the new annual-row descendant identity after replacement, rather than an obsolete positional native ID.
- Editorial balances **10,000 →15,000 →7,500**, total return **−25%**, and CAGR **−13.3974596…%**, displayed about **−13.4%**, reconcile under the stated two-period/no-cash-flow assumptions. Publication/example-update dates remain document dates, not market freshness.
- The density pair keeps the same three Company rows, values, changes, units, column widths and evidence actions. The row difference is 40px versus 52px; the separate important-phone-control target remains 44px. The 52px annual Company rows legitimately accommodate their additional comparison line instead of suppressing information to meet a single-line dense target.

The input contracts keep availability, coverage, freshness, transport, access and mutation outcome separate. The retained-error/source-unavailable/empty branches do not infer zero activity, account denial or saved success. Options access-provider failure remains distinct from a plan denial, and its protected workspace is not painted as a public-reading entitlement. The authoring inputs do not introduce a new API, persistence store or generic domain score.

## Qualification boundaries and closeout precautions

The existing F01 release, actual browser focus/keyboard/touch/400% behavior, source/producer and entitlement wiring, saved-request readback, and four retained domain/source roles remain explicit open gates. Their absence is not a new source contradiction found by this audit, and painted native controls do not close them.

The editorial companion deliberately uses the source specimen's illustrative anchors and records the actual emitted article's canonical route/original-heading binding as unresolved with its existing owner. That is an honest remaining integration dependency, not proof that those candidate anchor names are the production slugs.

Before final handoff, bind one explicit current construction order: participation `effective-spaced` inputs plus the forthcoming source/key-clock overlay; Company annual rows/caveat **v2**; companion **v1**; actual native alignment/layout corrections and returned replacement IDs. The broader participation consumer packet intentionally leaves unrelated Company/Options input subtrees unchanged, so it must not overwrite the subsequent Company repairs. Keep the unapplied Company v1 supersession visible. Final native export/capture and source manifests, rather than a packet's word “effective,” identify the actual result.

## Inspected artifact identities

The table records bytes available at the audit's close. Native source files may receive subsequent versioned fixes; those do not retroactively change the two findings above. The actual Paper candidate was not read or reviewed by this task.

| Path relative to `f02/` | SHA-256 |
| --- | --- |
| `SYSTEM_CONTRACT.md` | `c62e557567735f23554ac3382e764c7211d689b298d5e131ad68af5ed87215ce` |
| `SOURCE_AND_DATA_CONTRACT.md` | `a9d5ad8727feb3d77a054884dc632080a19cfddbfa0909b2081c6008abdbb57c` |
| `INTERACTION_STATES.md` | `7641bee4800d494669e732df8e53435682639e79934f7459890e36a4230cc7ad` |
| `CAPABILITY_LEDGER.md` | `9c522305754c67cc988ac4bf4d1239a489ff49fe6067d3d92aa884a53f4b36ca` |
| `fixtures/company-history.json` | `75a50198c9adfe8f2592aba2d87addd01b17b9c812ef7a4e78d17da567ec7df6` |
| `paper/repairs/fixture-coherence-v1/fixture-contract.json` | `d3329c2608fe14fb4fd592f971c945b6ac5a860d8c9836ee485cfa0151b58433` |
| `paper/repairs/fixture-coherence-v1/effective-spaced/consumer-boards.json` | `45946c8f487284ae0226033a8af9ebf75b9570b51fb94d8000a53842cf75a480` |
| `paper/repairs/fixture-coherence-v1/effective-spaced/mobile-state-boards.json` | `276572f02660d9b6be25473bdf039b28aea10ad31a1d0813bec6812caf804399` |
| `paper/repairs/fixture-coherence-v1/effective-spaced/supplemental-boards.json` | `e65ecfcec783c752651634541d6f9917857e2da42e4686bdae0535cd089aaa2e` |
| `paper/repairs/fixture-coherence-v1/effective-spaced/core-supplement-inputs.json` | `319604bdcc34be7ba21dfdb7812b16f81266fc451adc9d2ec10c528c08b95c40` |
| `paper/repairs/fixture-coherence-v1/effective-spaced/fault-composition-inputs.json` | `e84e18fba7027da31efb0f1981fd47977d51ad14a2313e9e21f4e5b10376e71a` |
| `paper/repairs/fixture-coherence-v1/effective-spaced/foundation-boards.json` | `0317a5e6191cde338ab5677342bec8d7eb80bae02358fef5c5cce41eb6efba71` |
| `paper/repairs/company-annual-growth-v2/company-row-replacements.v2.json` | `4a31896fa786402f3f19c3b7224c6646e4f4347c05f81331cbcecd611dc4260d` |
| `paper/repairs/company-annual-growth-v2/company-growth-arithmetic.v2.json` | `2f5da6df6061ed6b24d8833c780e6e8256b072a4795ae98361ba9a8aa18e3f4d` |
| `paper/repairs/company-annual-growth-v2/company-caveat-replacements.v2.json` | `3ca819564e58948341cf6711ecfea77dc5ba3ffdd8af6f4e8f3c36b54850e225` |
| `paper/repairs/consumer-companions-v1/consumer-companion-inputs.v1.json` | `0e14cb644787ab055f9cb089e40d6f57d4d74735abc6c77a71ed778ee46c294b` |

## Source-correction verification addendum — 2026-11-03 06:08:57 UTC

After the findings above were frozen, the source repair agent supplied the versioned `observation-identity-clocks-v1` overlay. This audit independently compared every ordered board/step in its cumulative consumer and fault packets against the prior `fixture-coherence-v1/effective-spaced` packets. Exactly **six steps changed and 311 steps remained identical**. The changed keys are the two desktop `evidence-field-0` steps and the four Company fault steps named in FCA-001/FCA-002; no other construction steps changed.

- **FCA-001 is corrected in the prepared source inputs.** Both desktop Macro inspectors now name `f02.fixture.v3/macro/sector/communication_services/share_above_50d/2026-10-30`, matching the selected field/date identity.
- **FCA-002 is corrected in the prepared source inputs.** The three completed/retained Company contexts now declare FY 2025–2026 as the fiscal observation basis, publication at 20:02 UTC and retrieval/last successful retrieval at 20:03 UTC. The retained-error copy names original fiscal periods and publication clock. Unsupported Company 20:00 observation text is absent from those affected steps. Unavailable/loading branches and all unrelated Macro clock text remain identical to the prior packets.

This addendum verifies only the versioned input correction. It does not assert that the sole writer has applied the source fixes to native Paper Text nodes, that the full identity wraps acceptably, or that final captures and native bindings have been reviewed. The original findings, owner acceptance, and runtime qualification boundaries remain recorded above.

| Path relative to `f02/paper/repairs/observation-identity-clocks-v1/` | SHA-256 |
| --- | --- |
| `source-overrides.v1.json` | `b94b7db39f4735b2eb749475e4aba1f513792b1c6fe6365b0c15954f994b8512` |
| `effective/consumer-boards.json` | `50238ddb0555f819820d3ee5eeb8e4d78dd33040a02883f4d93c3eb83119510c` |
| `effective/fault-composition-inputs.json` | `52f50a29da27bba24292109fbeee02ef6d7fb7ee8572a618b32b58210a1b9421` |
