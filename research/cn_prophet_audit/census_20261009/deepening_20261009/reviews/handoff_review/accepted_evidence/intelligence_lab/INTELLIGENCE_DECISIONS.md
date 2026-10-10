# Intelligence population, temporal replay and calibration decisions

## Decision

The bounded intelligence contract is accepted at `contract_lab.py` SHA-256 **`f2f5aeeb27b87809123148a642b9d6b848290a82033b7118614288432c8af014`**. It reproduces all 56 principal controls and passes **79 independent acceptance cases**, including all thirteen counterexamples from the first review. This settles the tested population, numeric, duplicate, revision, cadence and normalization boundaries. It does not establish a better investment policy, temporal qualification of current caches, or an installed generation contract. The independent acceptance explicitly identifies the existing owners' remaining input premises. [Evidence: results.json; ../reviews/intelligence_contract_review/acceptance_f2f5aeeb/ACCEPTANCE.md.]

The implementation recommendation is to repair existing source and generation contracts while preserving the incumbent ranking and baseline weights. Any proposed intelligence-first selection is a separately versioned challenger with complete qualified-population evidence and prospective evaluation. The historical ranking assessment supplies no promotion case. A four-name overlap demonstrates selection influence, not investment improvement.

## 1. The competing population is determined before either cap

The exact October 9 board and candidate inputs were read at Macro `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. The source probe retains thirteen input identities and the complete 125-row qualified projection. Coverage under the incumbent measured-value predicate is:

| Population | Names | Measured intelligence | Missing |
| --- | ---: | ---: | ---: |
| All scored | 1,601 | 1,597 | 4 |
| Raw eligible | 180 | 179 | 1 |
| Signal buyable | 164 | 164 | 0 |
| Qualified before sector/featured caps | 125 | 125 | 0 |

The four all-scored missing names are `600606.SS`, `000069.SZ`, `600038.SS` and `603899.SS`; only `603899.SS` is raw eligible. The qualified projection is reconstructed from the public lane decisions: 24 featured names plus 101 exclusions caused only by the two caps. It is not a rerun of every private native qualification predicate. Actual implementation must obtain this population from the existing qualification owner before applying either cap. [Evidence: source_input.json, population_coverage, qualified_rows and limits.]

The incumbent score ordering exactly reproduces the published 24 names. Ordering the same 125 competitors by current measured intelligence, with the declared incumbent tie behavior and unchanged caps, retains four incumbent featured names. The all-zero intelligence control reproduces the actual incumbent order, whose scores and ranks were independently checked for coherence. Contradictory synthetic caller scores and ranks do not inherit that guarantee. [Evidence: results.json; independent ACCEPTANCE.md.]

**Frozen coverage rule:** every qualified competitor contributes to coverage, including a name that would fall below the present cap. A missing qualified value causes whole-population incumbent fallback. A missing noncompeting value does not. Numeric zero remains a measured value; Booleans, strings, nonfinite values and scores outside 0–100 do not. There is no per-row substitution of a V3 score into an intelligence scale. A malformed candidate identity or duplicate rank is refused through the contract error model.

## 2. Source date fields cannot reconstruct system-observed history

The actual reader inventory explains why numeric completeness is insufficient. The analyst cache has 2,912 rows and a single October 9 `asof`; valuation has 1,637 rows over 47 `asof` dates; margin has 155,688 rows over 62 observation dates, with collection `asof` and `prior_date`; other caches carry their own daily or last-observation dates. Those fields are useful observations. They do not supply publication and first-seen timestamps for every current payload. The extras payload reader strips `asof`, while the alternative-data table reader takes the latest snapshot without a decision cutoff. [Evidence: source_input.json, source_clock_inventory and source_functions; source_probe.py.]

The accepted prototype implements **system-observed replay** when qualified records exist. Publication and system first-seen must be timezone-aware and no later than the decision cutoff. Rows provably available only after the cutoff are excluded before malformed identities or payload details can change a past decision. A missing clock is not synthesized from collection date, a Git timestamp, or a Boolean provenance flag.

Choose the latest known revision of each authoritative observation identity **before** evaluating that revision's payload or validity. A known higher revision containing a retraction, invalid value, missing source hash, expired applicability or invalid effective timestamp suppresses the observation. It must not restore an older convenient value. A later revision not yet known at the cutoff leaves the earlier replay unchanged. A valid future-effective revision retains the prior effective value until it applies. Numeric revision ordering is an explicit fixture assumption; a production source needs an authoritative revision relation, not hash order or physical arrival order.

Session families use expected sessions supplied by their own source/calendar owner. Margin's prior-session observation cannot be tested against one universal same-day expectation. Slower facts use an explicitly owner-declared periodic contract and remain effective until superseded or expired by that contract. A row cannot label itself periodic to bypass the expected-session check. Valid ISO date syntax is enforced, while exchange holiday truth remains the existing calendar owner's responsibility. [Evidence: DESIGN.md, contract_lab.py and independent acceptance table.]

## 3. Duplicates and normalization now have explicit identities

The actual analyst duplication experiment is a negative result worth preserving. The 2,912 rows represent 2,437 tickers. There are 475 two-row groups, containing 950 rows, and **zero conflicting payload groups**. Reversing every physical row leaves the native analyst consensus block, raw rating feature, its percentile, qualified-name percentiles and featured-name percentiles unchanged. This falsifies the proposed current-data row-order mechanism within that tested feature. It does not prove source-time correctness or full intelligence/board performance. [Evidence: analyst_duplicates.json; analyst_duplicate_probe.py; source-input SHA-256 a031323d82e99833ffdd5b35140ee6f686e65ca077a038cfaca57e280de00334.]

At the proposed versioned boundary, exact duplicates coalesce deterministically after lossless numeric normalization. Numeric `1` and `1.0` are equivalent; Boolean `True` is distinct. Integers `2**53` and `2**53+1` stay distinct, rather than being rounded into one source identity. Conflicting records claiming the same known version fail closed in either order. The selected-input digest includes unit and feature-contract identity even when the numeric feature values happen to be identical.

The selector returns observations, not aggregated per-issuer features. The existing source owner must first apply its qualified aggregation rule. Cross-sectional normalization then requires one aggregate per canonical issuer, one family, one unit and one feature-contract identity. Freeze that feed's qualified reference population before feature calculation. An unrelated candidate missing intelligence cannot change coverage of an already determined competitor set; a genuinely new source-qualified observation in a feed's normalization population can change relative values and must create a new generation. These are different invariants.

The repaired numeric helper does not verify compatible board, qualification, feature, normalization and calibration generations. The existing generation owner must bind those exact input identities, their cutoff and their coherent incumbent scores/ranks before calling it. A production acceptance fixture should substitute each identity independently and require an explicit mismatch refusal. That is an integration obligation at an existing owner, not permission to construct a parallel feature store or to add asserted labels to legacy caches.

## 4. Adaptive weights: actual priors retained; synthetic boundaries fail

The audit executes unmodified AST-extracted `load_validation` and `leg_weights_for` functions with the exact pinned scorecard, then six explicitly synthetic counterfactual cards. It performs twelve assertions. The exact current card was generated at `2026-10-09T16:15:18.750930+00:00`; feeding that card to the native reader leaves the normalized baseline priors unchanged. This does not prove which card the published board actually consumed. [Evidence: weight_input.json; weight_results.json; WEIGHT_DESIGN.md.]

| Counterfactual | Observed native behavior | Repair implication |
| --- | --- | --- |
| Future scorecard | Changes a leg's weight despite later generation time | Reader needs a decision cutoff and artifact/availability receipt. |
| 120 dense observations, two weeks, one independent window, unproven wrong sign | Zeros a leg using the time-series count threshold | Positive and negative weight actions need equivalent appropriate effective-evidence gates. |
| Qualified whole-market margin verdict | Changes the per-issuer margin leg | Calibration must match the actual feature and target. |
| `NaN` or `Infinity` strings in IC evidence | Still permits a boost | Reject nonfinite or malformed numeric evidence. |
| `"false"` strings for verdict Booleans | Truthiness permits a boost | Require actual Boolean verdicts. |

The source-level margin mismatch is specific: the consumer feature is each issuer's approximately 20-session financing-balance change, with positive orientation. The validation family is a whole-market financing/float timer against CSI300 returns with a contrarian prior. A successful market timer cannot by itself qualify a cross-sectional issuer feature. The later `MARGIN_HORIZON_TRACE.md` binds the producer's actual date-pair logic: all 155,688 frozen rows have a 20-position pair in the pinned index; ordinary fallback can select 21 or 22 positions, and an underfilled-history slice needs a bounded repair. Division by `20.0` in the score function is scaling, separately from that observation window. Current weights do not move in this audit, and no full feature, board or return effect was recalculated. All malformed-payload, future-card and changed-weight witnesses are synthetic.

At the existing calibration reader, bind the exact predictor/target/horizon/benchmark/price basis, source artifact and availability identity, label-maturity cutoff and evidence unit. Preserve the original scorecard receipt. Reject invalid types and require the same defensible evidence standard for turning a leg down as for turning it up. Retain the frozen baseline priors until a qualifying calibration exists. This is a correctness requirement, not a new weighting model or a weight search. The independent assessment in `../tradability_lab/DECISION_MEMO.md` accepts the bounded native audit and reproduces its seven scenarios and twelve checks byte for byte. Its added date-only control confirms that the timestamp itself does not change the weight; changed evidence fields cause the synthetic weight effect while the reader lacks a cutoff gate. The coefficients are signed score contributions, not portfolio allocations.

## 5. What has been resolved and what implementation must demonstrate

The original thirteen intelligence failures and the seven additional failures in the first repair are preserved under their own frozen review snapshots. The final version passes 79 independent cases without relaxing their expectations. No further feature search is needed to settle this bounded admission contract.

Implementation must integrate the accepted checks through existing owners, produce genuine source and generation receipts, and show whole-pipeline refusal on a mixed generation. The current caches cannot retroactively acquire missing first-seen or original revision history. Historical reconstruction should carry its own evidence mode and coverage, while future system-observed replay accumulates real receipts. Ranking promotion waits for untouched, same-policy, same-horizon outcome evidence; the correctness repairs and current negative experiments are not that evidence.
