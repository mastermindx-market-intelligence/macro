# Healthcare R9 — implementation decisions and review contract

**Status: REVIEW_READY / SHARED AMENDMENTS NOT ACCEPTED / NO EXECUTION COMMISSION.**

Operation: `gmi-healthcare-deep-research-20260923-sol-001`. Carrier: Macro #7788, `claude/healthcare-theme-research-20260923`. Research date: 2026-09-23. This is original principal synthesis. It does not supersede the Robotics owner, change production, enroll a source, resolve a security, or dispatch Fable.

## 1. The outcome we are freezing for review

The investor starts at Theme Tracker, enters the existing GLP-1 basket, and leaves able to explain a material development, the business mechanism, the evidenced participants, the strongest offsetting evidence, and the next useful observation. Market leadership and entry context remain distinct owner outputs. The machine preserves source scope, contractual denominators, dates, corrections, audience restrictions and missing identity. The advantage is a maintained economic argument, not an encyclopedia or a new composite score.

The full Healthcare objective remains all twelve research families with granular company roles, therapeutic/platform and care-setting facets, supply/access constraints, expectation revisions and later validated forecasting. The first current-evidence workflow does not complete that broader mission. No price target, underpricing, trade size or historical alpha claim belongs to the descriptive release without its separate data and validation.

R9 freezes a review candidate: eight implementation tasks in four useful releases, with every R8 acceptance case assigned. “Frozen” means reviewers have an exact proposal to judge; it does not mean the proposal is accepted or that code may start. Current Chairman continuation authorizes this planning work. Shared-owner changes and final independent acceptance remain unproved.

## 2. Narrow current-state verification

Protected Mastermind: `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1/bootstrap 1. Macro read-only interface pin: `d7711a0a08db8008ffe5975bfb3e6b242e4c70bd`.

- `engine/theme_graph/store.py` blob `63b58860d35bd183c947c85088f83bd53359bb9f` still has no curation payload in its evidence columns. This is a checked source limitation, not a broad claim that no private infrastructure exists.
- `engine/research_vault/r2_store.py` blob `139fcbe8cf08945a2be1feaa0dca5428c818837b` supplies the existing bounded, exact-version conditional-write protocol. No cloud credentials or objects were used.
- Robotics #7773 remains draft/unmerged at `f10211657c6c31df3c9af73cd4b9484e2dd7690a`. Its written plan supplies shared contract intent; PR text is not an observed running session or exclusive lease.
- The incumbent BioCatalyst client at this pin, blob `565ab98b440f95895e5e4477df2c60a00f38d110`, demonstrates request tokens/controllers and explicitly scoped display states. It is a compatibility reference, not permission to copy its whole client.
- R8 dossier and acceptance package read locally match recorded Git blobs `a5190d329f68e87c3c68424f3df9d5a8be7d55db` and `6e27cc2a97bd6ca13c1983835b5844a62e0db5ce`. Their 41 application cases are still NOT_EXECUTED.

No old FDA or rights-cache probe was rerun. No new source incident was discovered or repaired. No current company valuation, clinical outcome or GLP-1 shortage census was acquired.

## 3. Six decisions that remove ambiguity from the proposed build

### R9-D01 — one logical GMI evidence collection, explicit private tier

Select an opt-in private storage tier for the new native curation subtype within the existing GMI evidence owner. Legacy repository-backed evidence remains readable through its existing reader; current detailed curation rows are stored only in the approved private Research Vault instance, under GMI-owned immutable revisions and one GMI publication selection. Do not put bodies in both places. Do not use Earnings or RIO object identities for these rows.

The shared owner must approve this tiering before its implementation. Proposed `engine/theme_graph/private_evidence.py` is a backend of the native evidence owner, not a second thematic ledger or authority. It must round-trip the same closed native evidence row including the structured payload. K1's subtype names the actual private accessor; its legacy repository pointer remains unchanged for legacy rows. A public export contains no private body or private storage key. A duplicated native evidence ID across tiers is an integrity refusal, not a precedence guess.

An explicit opt-in native accessor composes the legacy and bound private collections only after authorization and validation. Legacy jobs do not acquire cloud credentials by importing the module. One admitted GMI writer uses existing Research Vault strict reads and compare-and-swap; no per-theme pointer, extra bucket, scheduler, queue or policy store is created.

### R9-D02 — capture policy bytes per request; never grant from a path-only cache

Select one bounded, validated policy snapshot from the deployed canonical registry for a request. Its content digest is the cache key and appears in the internal response lineage. Any cache of parsing is bounded and keyed by exact bytes/digest, not by path. Missing or malformed policy refuses the affected body. Preserve the legacy rights vocabulary; new subtype field/purpose checks are an additive function under the same owner.

Validate the effective policy before opening private bodies. Re-read its digest immediately before serializing a protected response; a change aborts with a safe policy-changed unavailable result rather than mixing revisions or retrying indefinitely. Future requests read the new revision. This establishes a request/release-bound behavior, not instantaneous revocation of information already seen by a user or a guarantee across undeployed hosts.

Both revocation and grant arrival need warm-process tests. A caller cannot submit its own policy snapshot as authority. An HTTP authenticated user is not an upstream data-license grant.

### R9-D03 — a complete sweep is not an atomic upstream snapshot

Retain the incumbent bounded page budget initially. A later page error, metadata inconsistency, repeated page, cap hit before all records, malformed page, or ambiguous identity makes acquisition incomplete. No new qualified observation is promoted. Preserve the last qualified observation and expose the failed attempt through the same cache envelope.

Successful counts and consistent generation labels allow the phrase “complete API sweep observed during [interval]”; they do not prove an instantaneous national census. The selected source documents pagination and daily updates but no snapshot-isolation token. Record `atomic_snapshot_proven=false` until a supported upstream mechanism proves otherwise. Sampling the first page twice does not upgrade that fact.

The existing `data/fda/shortages.parquet` stays the one collector artifact. Evolve it in place with observation-version columns and bounded Parquet metadata for the current qualified sweep and latest refresh outcome. Earlier captured rows remain distinct observations; the current reader selects only the chosen sweep. Empty successful observations still carry their receipt in metadata. Legacy rows are retained as unqualified historical material; do not stamp today's capture time on them as if they were newly observed.

This is an additive evolution of the existing source cache, not a new history service. Source-capture identifiers are local artifact identities, not global drug IDs. If a stable source key is absent, retain a content-scoped row and refuse cross-generation identity/absence conclusions for that row.

### R9-D04 — source observations, economic assertions and synthesis have different truth conditions

A regulator row supports the regulator's scoped status; it does not support price, excess capacity, company earnings or clinical advice. A source-reported licensing term supports its disclosed parties, grant and denominator; it does not establish manufacturing or a precise effective rate when tiers are qualitative.

Use the shared union's proposed `REPORTED_ECONOMIC_RIGHT` and `REPORTED_SUPPLY_STATUS` branches. Company-wide measures and source-only counterparties remain source-scoped. A common read model may present their separate evidence blocks together, but must not advertise a compiled security-subject recipe without consumed bridge proof.

The five-part interpretation is reviewed editorial synthesis owned by existing F04/GMI composition, with explicit supporting assertion IDs and required inputs. A runtime language model does not invent the first release's argument or confer source admission. If a required input is withdrawn, stale, unlicensed or superseded, suppress that dependent current conclusion; retain eligible facts with visible missingness.

### R9-D05 — content identity excludes delivery noise and includes meaning

Canonical revision input contains schema version, exact retained source-body digest, locator, source-scoped subject/object, predicate/body, units and denominators, upstream and business dates, review/admission identity and predecessor. Exclude the self-referential digest field, upload attempt ID, request ID and transport receipt time. Re-publishing exactly the same reviewed assertion is idempotent. A new review, changed source bytes, scope or meaning produces a new revision.

Two assertions in one report have distinct selectors. A new interpretation is not an amendment to the real contract. Corrections preserve predecessors. A withdrawal has a typed successor record; an old immutable blob remaining in private storage does not authorize current display or bypass source retention limits.

The five-part synthesis lists exact dependencies. A corrected required assertion invalidates its prior synthesis even when the theme and company labels have not changed. Appending a new source row alone is not correction completion.

### R9-D06 — independent correction first, then one common surface

D1 corrects the incumbent FDA collector/consumer. D2 implements one shared curation/private/K1/authenticated-view path with the Robotics owner. D3 enrolls the Healthcare profile and first real GLP-1 explanation. D4 demonstrates source correction plus a distinct non-metabolic mechanism through that same contract.

Proposed common endpoint: `/api/themes/{theme_id}/research/v1`, inside the existing Macro API. Proposed common client: `site/assets/js/theme-research.js`. These replace proposed per-sector implementation names only after the shared owner accepts the amendment. Existing or already implemented routes must be reconciled, not duplicated or silently broken. No replacement global navigation, auth client or publisher.

Research starts from `state_of_themes.html`; GLP-1 detail remains `basket/obesity_glp1.html`. Do not change `scripts/build_state_of_themes.py` merely to embed paid facts. The shared mount/client may hydrate both pages while preserving native analytical output. D3 cannot pass while an incorrect old supply chip remains unqualified in the same visible journey.

## 4. Self-review findings and dispositions

This is principal self-review, not independent acceptance.

| Finding | R9 disposition | What remains unproved |
|---|---|---|
| “Use private storage” did not identify which native object is authoritative. | R9-D01 freezes one native collection with explicit private subtype tiering and cross-tier collision refusal. | Shared-owner acceptance and implementation. |
| Path-cached policy could outlive a grant/revocation. | R9-D02 specifies content-bound snapshots and pre-serialization revision check. | Warm-service product tests and deployed behavior. |
| Complete pagination risked becoming atomic-snapshot language. | R9-D03 preserves the acquisition interval and an explicit negative atomicity flag. | Real complete sweep; no snapshot guarantee claimed. |
| Historical cache repair risked inventing old knowledge. | Retain old rows as unqualified; append only genuinely acquired forward observations in the existing artifact. | Actual source-history coverage. |
| A licensor label could be promoted to a security via a plausible ticker. | Source-only attribution remains useful; unresolved enrichment/required security recipes refuse. | Real owner bridge where needed. |
| Evidence-rich pages could still fail the user job. | D3 requires the five-part interpretation and a non-leading reader exercise. | Browser/user outcome. |
| Corrections could append evidence without changing the displayed conclusion. | Explicit dependency invalidation and recompiled synthesis required. | Real correction-to-view proof. |
| Interface generalization could overwrite the neighboring Robotics plan. | Exact shared amendment remains pending; no parallel shared writer assigned. | Shared decision receipt and current custody. |

## 5. Review gate versus build gate versus release gate

The package can be reviewed without cloud credentials or browser proof. Shared native tiering, policy and route decisions must be accepted before their implementation. Code and tests use synthetic fixtures before real source admission. Live sources enter only after rights, retention, review and private binding are proven. Production acceptance then requires permitted real input through the actual entitled page, negative public-mirror tests, and exact release identity.

Do not demand production proof before commissioning a lawful build; do not accept a build as production proof. Independent reviewers examine the exact candidate, and their returned receipt is distinct from a posted request or this self-review.

## 6. External source checks used in this plan

- openFDA Drug Shortages Overview: `https://open.fda.gov/apis/drug/drugshortages/`. Daily update and source scope read; not a real source acquisition.
- openFDA Query Parameters: `https://open.fda.gov/apis/query-parameters/`. Generic pagination parameters read; documented limit maximum 1000 and skip maximum 25000 do not require increasing the incumbent operational budget.
- FDA Drug Shortage FAQ: `https://www.fda.gov/drugs/drug-shortages/frequently-asked-questions-about-drug-shortages`. National status differs from manufacturer presentation availability; listing retention means disappearance alone is not a new supply or economic event.

The plan's conservative acquisition rules are design choices, not claims that the documentation guarantees transaction isolation. No PDF, patient data, vendor corpus, metered source or current market price was acquired.

## 7. Exact review requests

Shared owner: accept or amend R9-D01/D02/D05/D06 against Robotics #7773 and the actual GMI/Research Vault/K1/F04 contracts. Identify which incumbent implementation carrier, if any, already owns the shared path; no new assignment follows from this document.

Healthcare independent reviewer: test the eight-task plan against all 41 R8 cases and the five-part user job, especially the economic-right denominator, required-input invalidation, source-only identity and unchanged entry authority. Return exact blocking findings and evidence; do not redo the foundational sector research.

No reviewer is assigned or running by this publication. The final Fable CEO execution handoff is still deferred. The next accepted step is exact-package adjudication, followed by the final handoff on the existing authorized route—not another open-ended discovery wave.
