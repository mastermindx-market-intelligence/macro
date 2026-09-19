# Options Signal Campaign Outcome Correction Preregistration v1

**Date:** 2026-09-19  
**Operation:** `oa-campaign-outcome-correction-prereg-20260919-sol-001`  
**Parent:** `options-alpha-product-integration-20260917-sol-001`  
**State:** `PREREGISTERED_INACTIVE / NO HISTORY MUTATION`  
**Machine policy:** `research/options_estate/options_signal_campaign_outcome_correction_prereg_v1.json`

This artifact freezes the lawful correction shape for the September 3 mixed-generation campaign-outcome incident. It changes no campaign code, checkpoint, JSONL data, scorer, candidate, model, Terminal view or production path.

The primary law is:

> **Preserve the bad historical bytes as bad historical bytes; quarantine their authority, not their existence.**

No future session may “repair” this incident by restamping source hashes, backdating a later source row, silently regenerating the same outcome ID, truncating away the incident, or creating a replacement campaign ledger.

## 1. Incident identity

The contaminating publication is immutable:

- commit: `55d267539a7a25b3b941cb7af0d6eb3be98f642c`;
- subject: `data: asia collection 2026-09-03`;
- broad changed-path count: 2,034;
- parent: `dec799d09abd53e6fae0656f919e13082b419305`;
- incident checkpoint: `ocp_e3255025e9e8d98b72c3e9ec`.

The last lawfully published campaign checkpoint before the incident is:

`0b467285660be0834ecf3d96a33655b2b19a0848`.

At the prereg source pin `4e7761e42435622ad8ba181ba617e2a4bae6f015`, the current three campaign artifacts are still byte-identical Git blobs to the September 3 broad commit:

- campaigns blob `c581121767ca51bf20a8917d1a5a394f9db701d9`;
- outcomes blob `a67be30ab30255e62fa01d22f11f8e65417a160d`;
- checkpoint blob `c697a71d2d2d958301897a2135af98d97d140aa7`.

No later canonical campaign writer has superseded the incident generation.

## 2. What is valid and what is not

The incident must not be described as “all campaign history corrupt.”

### Campaign revisions are valid

The 8,385 campaign revisions themselves have clean episode receipts and member-row receipts.

They remain canonical exact-contract/session research revisions.

**Do not quarantine campaign revisions solely because the broad publication carried them.**

### Campaign outcomes contain one invalid suffix

The lawful outcome prefix is rows **1–24,578**.

Its frozen prefix receipt is:

`183c5f5bfc3a5f394c463b527ed2588314e21b9e5a3288fab881f64cd68db75e`.

The incident output is rows **1–28,423** with frozen prefix receipt:

`bfde356d4e54265164840e46f06e391afbed3c35449cda4786013eb95f432160`.

Therefore the exact quarantine is the contiguous suffix:

**rows 24,579–28,423 inclusive = 3,845 rows.**

All 3,845 were computed at:

`2026-09-03T20:37:25.569588Z`.

Observed invalid distribution:

| Horizon | Quarantined rows |
| --- | ---: |
| H+60 | 748 |
| EOD | 756 |
| 1d | 740 |
| 3d | 882 |
| 5d | 719 |
| **Total** | **3,845** |

The suffix affects 2,716 distinct campaign/revision identities.

## 3. Why the receipts are invalid

The incident checkpoint claims source prefixes of:

- episodes: 8,872 rows / `577173f25929afeb245e9a432d69fb7d8e204ccd4d4028ad6273eca3addacab5`;
- H+60: 6,525 rows / `129b56d4c457dbc2789a33e901367f84735d461a8f67790c6661bc2189ccb96c`;
- session outcomes: 23,771 rows / `6b95148d169de919bfb9cfa5e11bcb4fc842e8bc4e9fce0584cae827aa3c604e`.

But the same broad commit did not publish the matching episode-source generation. The campaign artifacts therefore escaped their sole narrow publisher and were committed against a mixed physical generation.

Later canonical source history proves this is not just a Git ordering oddity:

- campaign/episode receipts are clean;
- H+60/session prefix receipts in the bad outcomes do not equal the canonical source prefixes that later landed;
- 2,099 of the 3,845 bad rows cannot be reconstructed within the very source-record cutoff they claim.

Those 2,099 include:

- 1d: 740;
- 3d: 603;
- EOD: 756.

For those rows, the canonical source row lies *after* the claimed source prefix. Using it retroactively would be hindsight/backfill.

## 4. Why even the reconstructable rows stay quarantined

1,746 bad outcomes can be reconstructed from later canonical source within the same nominal record-count limit.

That does **not** make them valid historical rows.

Their source-row/provenance differs; their later reconstruction time differs; and many maturity clocks differ. Replacing the September 3 bytes with later-canonical bytes would turn a known publication error into an apparently clean historical observation.

The correction therefore applies to **all 3,845 incident outcomes**, not only the 2,099 impossible rows.

A valid correction does not ask “can we manufacture a nicer row today?” It asks “what did the system actually publish then, and may that row carry learning authority?” Here the answer to the second question is no.

## 5. Exact quarantine identity without a 3,845-entry replacement ledger

The correction is exact even though this prereg does not enumerate 3,845 row hashes.

The combination of:

1. the exact incident commit;
2. incident outcomes Git blob `a67be30ab30255e62fa01d22f11f8e65417a160d`;
3. the exact 28,423-row incident output prefix SHA-256;
4. the exact lawful 24,578-row prefix SHA-256;
5. the contiguous row boundary 24,579–28,423;

uniquely binds the quarantined byte sequence in the immutable append-only incident generation.

A later activation may additionally materialize per-row semantic identities for diagnostics, but it must not create another authoritative outcome ledger merely to store the quarantine list.

## 6. Correction semantics

After a reviewed owner-native implementation activates this policy, the system must distinguish **physical history** from **effective evidence**.

### Physical history

The incident bytes remain audit-visible.

They are not deleted, truncated, retimed, rewritten or restamped.

### Effective campaign history

All valid campaign revisions continue to validate normally.

### Effective outcome history

- rows 1–24,578: ordinary validation and admission;
- rows 24,579–28,423: exact incident quarantine, retained physically but excluded from effective outcome/calibration evidence;
- rows after 28,423: ordinary validation and admission, subject to normal source receipts and duplicate/identity laws.

The raw physical row count and effective admitted row count must be reported separately.

## 7. Semantic-key law

Every quarantined outcome keeps its original deterministic semantic key occupied.

The later engine may not regenerate that historical `(campaign_revision_id, horizon)` outcome and append a cleaner replacement as though it were the original observation.

This is essential for two reasons:

1. regenerating one of the 2,099 impossible-at-cutoff rows would be direct hindsight;
2. regenerating the other 1,746 would launder changed provenance/clocks into the historical record.

A future independently versioned correction or evaluation policy could discuss such a key, but it cannot relabel the original bad row as valid.

## 8. Checkpoint law

The September 3 checkpoint remains incident evidence, not current authority after correction activation.

Activation must create an owner-native **new correction/checkpoint receipt** that binds:

- this exact correction policy/manifest identity;
- current physical campaign/outcome prefixes;
- quarantined raw prefix identity;
- quarantined count;
- effective admitted count;
- current canonical source prefixes;
- all-false authority.

It must not overwrite or edit `ocp_e3255025e9e8d98b72c3e9ec`.

## 9. Interaction with #7265 deterministic replay

Macro #7265 proved that from the last lawful prefix, the existing campaign writer can deterministically derive a clean current view within the production runtime budget after its digest optimization.

That proof is valuable as:

- evidence that the derivation rules remain deterministic;
- a diagnostic oracle for the current lawful population;
- evidence that no replacement store or longer timeout is necessary.

It is **not authority to replace the raw September 3 rows**.

The production correction must preserve the incident bytes and quarantine their effective authority. A temp restore-from-good-prefix replay is allowed as a verification oracle; it is not the canonical history mutation.

## 10. Activation prerequisites

This prereg is inactive until **all** of the following clear:

1. Macro #7265 durability + campaign-runtime source is protected;
2. Macro #7263 shared publisher recovery is protected and a real publication loop is proven;
3. Macro #7193 broad-writer exclusion is protected and a natural Asia publication proves OIP owner roots are not swept;
4. the existing campaign owner implements and reviews correction-manifest admission/effective-view semantics;
5. the exact lawful/incident identities still match at action time;
6. one normal nightly proves corrected effective history, checkpoint publication and protected-main readback.

The correction implementation **may not start while #7265 remains the active writer on the campaign engine/tests**.

## 11. Implementation constraints

The later implementation remains under the existing `options_signal_campaign` owner.

It must not:

- add another campaign/outcome ledger;
- add another campaign identity;
- hard-code “row 24,579” or the September 3 commit directly into engine logic;
- create a persistent digest database;
- weaken prefix/row validation;
- increase the campaign timeout as the primary fix;
- treat quarantine as a loss, win, null-to-zero conversion or deletion;
- activate scoring/training/promotion.

Incident identity must come from a reviewed versioned correction manifest/policy.

## 12. Authority

Quarantined rows are:

- training-ineligible;
- calibration-ineligible;
- candidate-evidence-ineligible;
- promotion-ineligible;
- option-P&L-authority false.

This correction cannot score, rank, gate, size, issue, trade, publish probability, change #7290 candidate formation or grant option-return authority.

## 13. Acceptance tests owed by the later implementation

Before activation, the implementation must prove at least:

- exact lawful prefix validates unchanged;
- exact incident suffix is quarantined only when every bound incident identity matches;
- one mutated byte in the incident prefix refuses activation;
- one shifted start/end row refuses activation;
- missing/extra incident row refuses activation;
- campaign revisions remain admitted;
- quarantined outcome keys remain occupied and cannot be regenerated;
- later unrelated valid outcomes can append normally;
- quarantined rows never enter calibration/training/effective outcome counts;
- raw/effective counts remain distinct;
- old bad checkpoint is not rewritten;
- correction receipt is deterministic/idempotent;
- a clean history with no matching incident does not activate this correction;
- broad publisher cannot become another OIP writer.

## 14. Completion boundary

Merging this prereg would settle the **correction law only**.

It would not:

- correct production history by itself;
- make campaign v2 accepted;
- make OA-1T PROVEN_LIVE;
- activate OA-1C;
- create a Terminal candidate;
- establish option alpha.

The implementation child begins only after the source-owner prerequisites above are actually released.
