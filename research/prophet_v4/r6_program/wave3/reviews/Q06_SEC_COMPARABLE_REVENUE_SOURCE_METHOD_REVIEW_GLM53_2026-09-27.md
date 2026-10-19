# Q06-SCR-01/v0.1 independent source-method review — GLM-5.3

- REVIEW ID: `q06-8069-source-method-review-glm-20260927-001`
- OPERATION: `q06-8069-source-method-review-glm-20260927-001`
- REVIEWER: GLM-5.3, bounded independent source-method reviewer.
- REVIEW TARGET HEAD: `1b063d3a843e8f031d8de811fc54007835f16bd1`.
- REVIEW TARGET TREE: `e75403b9c81604df1c4f00d68c9f2ee4b8b1173d`.
- COMPARISON BASE: `b95cfc873a4de44e0f2fae15be30f777077a8151`.
- CANDIDATE FILE SHA-256:
  - Markdown: `566de5f30dbdeecdc1dc1d06aafcbd67c932fb3c576c5019d39ca0f1c6e438f7`.
  - Manifest: `f542cf5406672ecc2f6f067e0094c23ee47723b137119b3956b504460e1b7311`.
  - Revision receipt: `3800cb3f6c6082ff3a05b825bd61a965115f6d1280a660aea188f2162bf34ef4`.
  - Agent OS checkpoint: `4a32579f46aff7262d8c194ee94c9689c5a0355efb5871971e3d766836f44ea0`.

## DISPOSITION

DISPOSITION: **FIX_REQUIRED**

This review grants no merge, release, trial, ranking, trading, source-collection, evaluation, or adapter authority. It reviewed semantic head `1b063d3a843e8f031d8de811fc54007835f16bd1`; every downstream gate named by the candidate remains closed.

## FINDINGS

### BLOCKERS

None.

### MAJORS

**M1 — source-revision wording is not decision-safe.** The receipt's `source_sha256` is the SHA-256 of the entire supplied Exhibit 99.1 string, not a composite source package or regenerated metadata. That identity is exact, but ten distinct full-string hashes do not prove ten issuer-authored exhibit-body revisions. The current live SEC response is 173,604 bytes with SHA-256 `6595b2425e503a5cf2f6c2b74506954784e4f7834d6682501265324d7fb657cb`; removing its sole 120-byte injected delivery script restores byte-for-byte the frozen 173,484-byte body and SHA-256 `070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb`. Direct replays of the same URL also now return `6595b242…`, not the nine later recorded hashes, while the stable selected spans remain `109,417` and `94,036`. The daily changes are therefore at least consistent with mutable delivery-wrapper bytes and cannot be labeled immutable issuer-body revisions.

Effect: `candidate.md:97-99`, `candidate.md:105`, and `receipt.json:13-21` overstate correction lineage and immutable-body status.

Smallest lawful repair: relabel the ten rows as distinct supplied-envelope/source-object identities; add a separately defined deterministic normalization and an envelope-diff receipt that identifies exactly what changed; hash both the fetched envelope and normalized exhibit body; call a revision issuer-body only when normalized body bytes change.

**M2 — economic-field provenance versioning is incomplete.** `candidate.md:118-123` versions identity, fiscal period, metric, value, unit, currency, basis, and selected-text hash, but omits the exact source object/document identity, current/prior byte spans, admissibility decision, and rights state. Those can change while value and text remain unchanged, so `SOURCE_BYTES_CHANGED / ECONOMIC_FIELDS_UNCHANGED` can silently preserve an inadmissible or differently located field.

Effect: correction classification is not sufficient for a decision-time field contract.

Smallest lawful repair: version a field-provenance record containing source-object and document identity, both spans and span encoding, normalization rule, text hashes, admissibility state, and pinned rights-record identity; change class 2 whenever that record changes, while retaining the separate economic-value identity.

**M3 — Q06-SCR-01/v0.1 is preparatory, not genuinely preregisterable.** `candidate.md:164-227` says the mechanism "may retain opportunity," lists five broad arms, and defers exact selection/model details. It supplies no exact directional sign or threshold; association-versus-selection estimand; candidate/no-entry denominator; exact comparator, training/calibration and validation split; origin and first lawful fill rule; endpoint arithmetic; benchmark and sector construction; costs; multiplicity owner; numeric failure/rejection threshold; minimum independent dates; or stopping/maturity rule. Those choices remain post-outcome degrees of freedom even though H42 is named and H21/H63 are descriptive.

Effect: Packet3 cannot register a confirmatory trial from this record without inventing decision-changing choices.

Smallest lawful repair: keep this record a source/protocol candidate and write a complete preregistration packet with every element above fixed before outcomes, while preserving excluded, unpriced, delisted, duplicate-issuer/date, foreign-private-issuer, and not-matured rows in the denominator ledger.

### MINORS

**m1 — malformed fixture clock is underdiagnosed.** `candidate.md:50-51` calls `2026-07-30T16:30:00Z` a conflict. SEC submissions API acceptance is `2026-07-30T20:30:28.000Z` (`data.sec.gov/submissions/CIK0000320193.json`). The fixture value is best identified as timezone/truncation malformed, not an equal-clock alternative. Repair the wording and retain the production clock.

**m2 — accounting-basis label needs the exact source title.** `candidate.md:62-63` labels the rows GAAP, but does not quote the table title "Unaudited Condensed Consolidated Statements of Operations." Repair by quoting that title and state that this study maps it to its GAAP basis rather than relying on the manifest's lowercase `gaap` token alone.

**m3 — candidate validation command is not reproducible from the PR.** The handoff's deterministic command names a temporary Python script that is not committed. Independent checks reproduce the result, but future readers cannot run the stated command. Repair by citing a committed checker or replacing the claim with the exact bounded commands and outputs.

## REQUIRED CHALLENGES A–H

### A. RIGHTS AND SOURCE AUTHORITY — NOT FOUND

The exact SEC register at frozen base `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md:113-121` records acquisition, processing, storage, model use, and citation/trademark-limited redistribution as user-facing. Its base blob is `a9ee6f288bfb2716facd88dcf2c5135ca8125303`. The candidate states those limits at `candidate.md:26-31`.

The Massive entitlement is pinned to `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md` at base blob `3969a9aae918141b51baffbb0e17d8a2ec2485a0`, not current mutable text. Lines 8-11 identify the enterprise instrument; lines 21-46 cover bars, historical archives, derived materials, AI/ML, redistribution, and retention; lines 52-55 preserve feed-specific written designations. The candidate honors that condition.

Current SEC/HKEX/SEDAR+ page facts in `manifest.json` are limited to access/public-use boundaries and explicitly deny collector, blanket exhibit rights, clocks, parsing, history, and revision authority. `authority_change` and `collector_authorized` are false. No unauthorized right is claimed.

### B. SOURCE IDENTITY, FISCAL COMPARABILITY, AND FIELD CONSTRUCTION — FOUND

The deterministic checker verified CIK `0000320193`, accession `0000320193-26-000018`, form `8-K`, Exhibit 99.1, quarter ended 2026-06-27, prior quarter ended 2025-06-28, table headings `Three Months Ended` and `Nine Months Ended`, USD millions, current `109,417`, prior `94,036`, spans `[19519,19526)` and `[20003,20009)`, both text hashes, and `(109417 / 94036 - 1) * 100 = 16.356501765281383`.

The cohort contract at `candidate.md:133-152` requires one same-table pair and identical currency/unit/basis/period role; it names GAAP/adjusted, continuing/discontinued, quarterly/YTD, currency, and fiscal-role exclusions, and keeps excluded rows visible. These exclusions are construction rules, not evidence of population coverage. The record itself correctly calls AAPL one exact exemplar, not a materialized production field (`candidate.md:71-75`) or a historical cohort (`candidate.md:154-162`). Repairs M1/m2 and M2 are required before the exact exemplar becomes a reusable field contract.

### C. DECISION CLOCKS AND POINT-IN-TIME HONESTY — FOUND

SEC acceptance is `2026-07-30T20:30:28Z`; the malformed fixture clock is addressed by m1. `candidate.md:200-205` correctly sets decision time to `max(source_available_at, system_observed_at)`, forbids a fill in a bar needed to know the source, uses the next lawful action after a post-session publication, and treats missing evidence as unavailable. The current chain observation is `2026-09-26T05:02:59Z`. The historical AAPL case is diagnostic only and cannot be an observed-as-run opportunity; `candidate.md:154-162` and `candidate.md:226-227` preserve that boundary. Publication, source availability, system observation, candidate origin, and fill clocks are not conflated. `candidate.md:89-106` records chain-read time separately.

### D. REVISION/CORRECTION SEMANTICS — FOUND

`source_sha256` hashes the complete supplied exhibit string, as shown by `engine/fundamental_forensics/disclosure_diff.py:921-955` and the source row construction in `engine/company_intelligence/event_workspace_build.py:400-440`. It is neither a composite package nor a regenerated source object.

The compact receipt's 186 predecessor links and ten distinct source/workspace hashes are real: the bounded checker fetched all ten selected generation manifests and workspace objects and verified generation, manifest hash, workspace hash/bytes, clocks, lifecycle, and source hash. Links are not merely repeated generations. However, the "ten source-body revisions" label is not supported (M1), and field provenance is incomplete (M2).

### E. PREREGISTRATION COMPLETENESS AND DENOMINATORS — FOUND

The experiment is not yet preregisterable for the reasons in M3. The candidate does preserve no-entry, unpriced, excluded and not-matured reporting (`candidate.md:187-196`), accepts null/negative/inconclusive results (`candidate.md:226-227`), and supplies discriminating smoke cases for cut clocks, missing prior/zero denominator, basis mismatch, same-bar fill, ordering, costs, duplicate rows, and failed jobs (`candidate.md:229-245`). It does not yet preserve delisting, foreign-private-issuer, or duplicate-issuer/date as named denominator states; they are covered only by generic eligibility/exclusion language and must be explicit in the complete registration.

### F. OUTCOME PRICE CONTRACT AND EXECUTION REALISM — NOT FOUND

The exact Massive manifest at commit `b884cb5053f4196ae7e574c724c275212296ce5f` has SHA-256 `4d631c89e75a4862fb8a625a38c685635f3e6aecca82b2563825dfd147500782`, 21,639 tickers, 1,364 processed days, range 2021-07-06 through 2026-09-25, zero maximum weekday-gap run, and SPY 1,313 rows. The candidate's raw/unadjusted full-session classification and absent timestamp/session/venue/factor table are supported at `candidate.md:302-331`.

Accordingly no H42 absolute, excess, or total-return result and no fill simulation may start. The record forbids same-bar, official-close, RTH, auction, zero-cost, and no-action assumptions, and it leaves canonical identity, session/venue, factor lineage, `adjustment_asof`, derived basis, and cost/fill evidence to the existing Data OS owner. "No new price purchase" is supported as an implementation/source-contract statement, not as evaluation readiness; `trial_may_start` is false.

### G. FOUR-MARKET TRANSPORTABILITY — NOT FOUND

`candidate.md:247-258` does not transfer a US finding by relabeling. It confines CN and HK to prospective metadata/discovery or display because body, revision, and rights planes are absent; Canada is `NOT SOURCE-READY`; SEC-reporting foreign private issuers must independently pass US 6-K identity and source rules and gain no native-market feasibility. The map names native calendars/currencies, listing identity, publication regimes, delistings/trading restrictions, and price readiness as missing rather than solved. Licensed SEDAR+ DDS is a required next decision, not evidence of a completed feed. No product-plan inference is promoted to source evidence.

### H. MACHINE/HUMAN PARITY, SCOPE, AND AUTHORITY — FOUND

Markdown, manifest, receipt, and Agent OS checkpoint agree on `FIRST_SOURCE_UNIT_COMPLETE / RECORDS_ONLY / NUMERICAL_RESULT_UNCOMPUTED`, prospective-only evidence, held D07, held Cycle #7868/#7871, no Packet3/Packet4 effect, and no adapter/UI edit. Every authority field is false. `registration_state=NOT_REGISTERED`, `numerical_result=UNCOMPUTED`, `protected_outcome_read=false`, `outcome_price_source.trial_may_start=false`, `packet4_adapter_edits=false`, and `paper_edits=false`. The base-to-required-head diff is exactly the four named additions. The only parity defect is the non-reproducible temporary validation command (m3).

## COMMAND EVIDENCE

All summaries were bounded; credentials and environment secrets were not printed.

- `gh pr view 8069 -R mastermindx-market-intelligence/macro --json headRefOid,title,isDraft` — rc 0; head `1b063d3a843e8f031d8de811fc54007835f16bd1`.
- `git rev-parse HEAD` — rc 0; `1b063d3a843e8f031d8de811fc54007835f16bd1`.
- `git show -s --format=%T HEAD` — rc 0; `e75403b9c81604df1c4f00d68c9f2ee4b8b1173d`.
- `git diff --name-status b95cfc873a4de44e0f2fae15be30f777077a8151 1b063d3a843e8f031d8de811fc54007835f16bd1` — rc 0; four `A` records, one per candidate file, no other path.
- `python3 -m json.tool research/prophet_v4/r6_program/wave3/q06_sec_comparable_revenue_capture_manifest.v0_1.json >/dev/null` — rc 0.
- `python3 -m json.tool research/prophet_v4/r6_program/wave3/q06_aapl_revision_chain_receipt.v1.json >/dev/null` — rc 0.
- `git diff --check b95cfc873a4de44e0f2fae15be30f777077a8151 1b063d3a843e8f031d8de811fc54007835f16bd1` — rc 0; no output.
- Bounded deterministic Python verifier — rc 0; fixture SHA `070abd6a…`; spans `109,417` and `94,036`; formula `16.356501765281383`; all authority fields false; trial `NOT_REGISTERED/UNCOMPUTED/may_start=false`; Massive `{21639 tickers, 1364 days, 2021-07-06→2026-09-25}`; chain `{186 hops, 186 generations, 10 distinct revisions, 10 receipt rows fetched}`.
- Frozen-base fixture extraction and live SEC fetch — rc 0; frozen 173,484-byte body matches `070abd6a…`; live 173,604-byte body is `6595b242…`; deletion of the sole injected 120-byte script exactly restores the frozen body and selected spans.
- `git ls-tree b95cfc873a4de44e0f2fae15be30f777077a8151 -- <rights record> <Massive record>` — rc 0; blob IDs `a9ee6f28…` and `3969a9aa…`.
- `python3 scripts/agentos.py validate` — run after the review commit; result recorded in the PR return packet.

## WHAT IS ACCEPTABLE NOW

The AAPL source identity, same-table fiscal construction, selected values/spans/text hashes, arithmetic, SEC rights posture, pinned Massive entitlement scope, exact price-manifest coverage facts, raw/full-session limitations, point-in-time decision-clock rule, prospective-only boundary, held downstream gates, and all-false authority state are acceptable as bounded source facts for parent adjudication.

## WHAT REMAINS FORBIDDEN

No trial may register or start; no protected outcome may be read; no H42 return, excess return, total return, ranking, selection, entry, sizing, execution, trade, adapter, Packet3, Packet4, Paper, D07, or Cycle effect may be claimed. No collector is authorized. CN/HK/CA remain non-confirmatory. No current mutable public page may replace the pinned rights or entitlement records.

## LIMITS

This is a semantic source-method review, not legal advice, scientific acceptance, or a live-market feasibility audit. The review did not open protected returns, acquire a new source, audit the private executed Massive instrument, or independently reconstruct all 186 workspace objects; it verified the compact chain and fetched its ten selected revision generations plus their exact manifests and workspace receipts. The account-local Claude memory index named by project startup rules was absent. The PR body was not edited because the binding ruling explicitly superseded the generic body-update request.

## EXACT NEXT ACTION FOR PARENT SOL

Repair M1, M2, and M3 in the candidate PR before any acceptance. Separate fetched-envelope identity from a deterministically normalized immutable exhibit-body identity and publish the envelope-diff receipt; add complete field-provenance versioning; replace the broad experiment sketch with a complete preregistration packet or explicitly downgrade Q06-SCR-01/v0.1 to preparatory status. Also repair m1-m3. Keep every downstream authority false and every outcome gate closed.
