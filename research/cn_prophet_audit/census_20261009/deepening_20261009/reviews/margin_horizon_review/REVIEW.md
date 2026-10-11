# Independent acceptance of the margin-horizon addendum

**Accepted as a bounded research addendum. There are no remaining review blockers.** The review binds the final principal manifest `d21ce925119d58094c3248a399374ddd43a4292332588eb92e06046ccb7e8ada` and study source `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. It does not authorize a production change, recalibrate the feature, or establish historical availability. The isolated implementation repair remains to be made through the existing collector and feature owners.

The corrected independent execution passes **39 of 39 checks**. It exactly reproduces the final probe's eight synthetic scenarios and separately executes the native current lookup, selected-current index, candidate slice and prior lookup with recorded source-call order. It also executes the native stored-row construction and the exact existing feature consumer. All 62 reported date-pair aggregates reconcile to their totals, and the two data receipts match earlier pinned inventories. The executable evidence is in `review_margin_horizon.py` and `REVIEW_RESULTS.json`; the final reviewed addendum and its earlier slice-only development run are retained in `reviewed_addendum/`.

## What the source establishes

The collector explicitly sets `LOOKBACK_TD = 20`. It uses the first nonempty index store in the existing `000001.SS`, `510300.SS`, `399001.SZ` order and takes its tail. An independent fixture confirms that it does not switch to a longer secondary history when the first index is nonempty but short. Current source data are selected newest first from the final three dates. With sufficient prior history, the subsequent source lookup tries positions 20, 21 and 22 before the selected current observation, newest first. These are positions in the chosen source index; calendar completeness and historical first-seen availability are separate premises. [Source: `reviewed_addendum/pinned_margin_collector.py`; checks in families `source` and `lookup`.]

The precise current lookup matters to the underfilled-history finding. The final probe and this review agree on all eight cases:

| Synthetic case | Native current index | Native prior index | Native gap | Proposed bounded prior index |
| --- | ---: | ---: | ---: | ---: |
| Full history, target available | 39 | 19 | 20 | 19 |
| Full history, first fallback | 39 | 18 | 21 | 18 |
| Full history, second fallback | 39 | 17 | 22 | 17 |
| Full history, prior unavailable | 39 | Unavailable | Unavailable | Unavailable |
| 21 rows, oldest recent observation, stable source | 18 | 18 | 0 | Unavailable |
| 21 rows, newer date appears between lookups | 18 | 19 | −1 | Unavailable |
| 21 rows, middle recent observation | 19 | 0 | 19 | Unavailable |
| 21 rows, latest observation | 20 | 0 | 20 | 0 |

The future-selection case explicitly changes source availability between the two lookups. Its call trace shows index 19 unpopulated during current selection and populated during the prior lookup. A separate stable-response counterexample, with indices 18 and 19 already available, selects index 19 as current. It cannot support the same future-selection claim. Stable underfilled responses do support selection of the current date as its own prior. The collector's 21-row guard admits these synthetic cases. The preserved initial slice-only run is superseded for the claim involving both lookups. [Evidence: the eight `independent_native_sequence_*` checks and `future_claim_requires_second_call_availability_change` in `REVIEW_RESULTS.json`.]

The bounded replacement agrees with an independently enumerated set of positions satisfying `20 <= current_index - prior_index <= 22`. It preserves every tested valid target and fallback and yields an empty candidate list when fewer than 20 earlier positions exist. No new lookback, universe, metadata owner or source store is needed to express this repair.

## Stored rows and measured feature coverage

The native producer stores the actual date pair and balances. The chosen prior date applies to the whole source response. An issuer absent from that response can have a populated `prior_date` and a missing `fin_balance_prior`; there is no per-issuer search for another date. The independent fixture confirms this distinction. [Evidence: `global_prior_date_can_be_present_when_issuer_balance_missing`.]

The exact `engine/china_extras.py` source is retained as `pinned_china_extras.py`, SHA256 `136ad143dc88aec330085f00f61e1900b5e0f643870a549a22801861163057f1`, Git blob `11219d650fc06f685b5effbd14f809b97cdcad74`. Its consumer computes the rounded balance change when the prior is positive, retains the current date, and drops `prior_date`. A synthetic 100/80 balance pair yields 25.0 percent. A missing or zero prior does not yield a measured `chg_pct`. The repaired underfilled case passes through the native stored-row and consumer path with both prior fields null and no change key. The native self-selection case produces the same stored date twice and a 0.0 change. These consumer effects were tested with synthetic inputs; no actual board or return effect is claimed.

The final memo correctly distinguishes a previously retained source identity from custody of this particular function's text. The exact consumer bytes are now included here. The initial prose identities are recorded in `INPUT_FREEZE.json`; the initial memo and manifest bytes were not separately captured before the principal's prose-only correction, so this review does not claim to retain those bytes.

## Frozen data and the limit of this recount

The **62 retained date-pair aggregate rows** sum to **155,688 rows**, of which **154,772 have a nonmissing prior balance** and **916 do not**. The latest observation, October 8, has **3,530 rows and 9 missing prior balances**. The aggregate contains no missing prior dates; its reported source-index gaps reproduce exactly **155,688 rows at a gap of 20**. All pair dates are valid, unique by observation date, and earlier on the prior side. [Evidence: the `aggregate` checks and `observations.paired_aggregate` in `REVIEW_RESULTS.json`.]

The detail Parquet receipt matches the earlier intelligence source inventory, and the index receipt matches the corrected native tradability census. The detail row count and date domain also agree with that prior inventory. The detail SHA256 is `64b752ada586acd6af7ac19985a3ee4aa9b8e2bebf686de7ab66471cb29097e4`; the index SHA256 is `3482108489339b7dccbe3529ea3e391bca9424725509fb177bdbe29fb49b8c9b`. [Evidence: `CROSSCHECK_INPUTS.json` and the `receipt` checks.]

This review did not reread the raw Parquet rows or independently reconstruct their index positions. The unique-ticker count, raw index shape and underlying per-row gap computation remain the retained, hash-bound producer census. The review independently reconciles the complete 62-row aggregate and custody links. No discrepancy justified a second full host census. None of the synthetic underfilled failures is observed in the frozen stored-pair evidence. Nonmissing prior balances are not automatically positive usable priors or qualified feature counts.

## Minimum implementation implications

Apply the bounded candidate slice in the existing collector and validate the resolved prior against the declared source-index window before emitting a measured change. Preserve the nullable behavior when no valid prior exists. Carry the actual current/prior date pair and feature-contract identity through the incumbent feature owner so downstream calibration can identify the measurement it receives. Keep publication and first-seen clocks distinct from the stored pair and collection `asof`.

This review supports the addendum's narrow horizon clarification and boundary repair. It supplies no evidence to change the accepted baseline coefficients, and it does not repeat the broader weight audit or any score, rank, board or investment-return calculation. The collector, vendor interfaces and production writer were never invoked.

The first review harness execution failed before producing accepted output because an AST selector matched the tuple prior lookup instead of the scalar prior default. `HARNESS_NOTE.md` records the correction. The corrected execution exited 0; the candidate was unchanged throughout. Final custody verification covers the eight addendum payloads and the earlier sealed review packages.
