# Company-first stock assessment v2 (R5)

## User benefit

A company case can now show useful current news and its existing entry context when peer data is absent. When historical owner evidence is missing, current news remains visible and the before/after comparison is explicitly unavailable.

The v1 consumer required peer inputs to establish its subject and returned no news views when either comparison snapshot was missing. V2 makes the shared company/security identity and decision time explicit, without changing v1 behavior.

## Closed v2 request

Schema: `catalyst.stock_research_inputs.v2`. Every field is required; intentional absence uses null.

| Field | Meaning |
| --- | --- |
| focal | security_id, company_id, identity_epoch, identity_source_ref |
| decision_at | Explicit UTC assessment cutoff |
| peer_inputs | Existing supplied-peer input, or null |
| entry | Existing Prophet B4 cut, or null |
| news | fact_log, current_owners, comparison; or null |

News comparison is null when not requested. Otherwise it contains since_at and prior_owners, which may be null to represent unavailable history. Non-null malformed inputs refuse the request.

The existing CLI selects v2 only for the exact v2 schema:

```sh
python -m engine.catalyst_intelligence < request.json
```

## Output behavior

Schema: `catalyst.stock_research_assessment.v2`.

The peer facet wraps the unchanged supplied-cohort result. Missing peers have a null context, not an invented zero denominator or zero return. Supplied peer identity must match all four focal fields; its decision must be the same instant.

News has separate current and comparison results. Current is projected independently through the real NewsImpact owner. A successful empty projection has views=[]; unavailable input has views=null. Comparison-not-requested, prior missing, prior not known at its cut, and current unavailable remain different states.

Qualified comparisons project the prior state independently and call the canonical owner with an explicit prior snapshot. The current proposition keys and all non-trigger fields must agree between the independent current projection and the comparison projection. Duplicate or inconsistent owner results refuse the request.

Pairs use (company_id, original_proposition_fact_id), preserving BOTH_CUTS, CURRENT_ONLY, and PRIOR_ONLY. Historical-only records carry null comparison triggers; they are not reclassified as withdrawn or resolved. Empty owner triggers are not proof of no economic change or no news.

Composition timestamps require complete UTC clocks with at most six fractional digits. Equality compares exact supported instants, including one-microsecond differences. Evidence strings and digests are preserved. An owner payload's decision_cut must retain the exact spelling of its enclosing as_of.

The inherited research source-cut contract requires as_of <= known_at and qualification requires known_at <= the requested cutoff. At an exact requested cut this means equality. This is not a native acquisition receipt model; future native integration must distinguish acquisition/materialization clocks without backdating evidence.

## Verification and source custody

- 88 stock-context tests passed, including 45 added v2 cases.
- A separate composed checkout containing the exact R3 entry and R4 NewsImpact repairs passed 453 tests across the stock-context, B4/strategy, Daily Brief, and NewsImpact suites.
- Initial composed-checkout runs omitted unchanged lib/, scripts/, and app/ dependencies. Those setup omissions were restored; they did not require source repairs.
- The frozen v1 CLI result is equal as parsed JSON, including its IDs and digests. The regression does not claim a separate raw-stdout byte comparison.
- A C3 review accepted the exact v2 module and regression design. Root executed the tests.
- The isolated R5 changes were adopted by exact hashes into the clean R1 carrier at 6cf685047eca56ad236e16fdc84adb4a07646168. The v1 implementation and frozen v1 fixtures remain untouched.

The v2 module, CLI dispatch, tests and research proof extend [PR #9616](https://github.com/mastermindx-market-intelligence/macro/pull/9616). R3 and R4 source remain separate in [#9731](https://github.com/mastermindx-market-intelligence/macro/pull/9731) and [#9732](https://github.com/mastermindx-market-intelligence/macro/pull/9732); their code is not copied into this published consumer branch.

## Four reproducible examples

`capture_replay.py` calls the actual CLI in the documented composed checkout. It refuses a different critical source composition. It writes only this research lane's fixture files.

The source_revision case adds a synthetic numeric-fingerprint correction followed by a known-source mirror. The three expected owner triggers survive. Peers_missing removes only peer input. History_missing removes only the prior snapshot while preserving the current view. Current_unavailable withholds current news and comparison rather than presenting history as current.

These are synthetic research records derived from existing owner tests, with their adaptations recorded. They use no live feed and establish no native source admission, current market fact, economic amount, or economic direction. The captured JSON files are immutable examples, not publisher inputs.

## Next native integration dependencies

1. Acquire current and historical NewsImpact owner cuts from the actual forward-ledger owner, with source-to-decision timing and correction lineage. No qualifying pair was established by this increment.
2. Bind the Company source context through its existing event/document/span and canonical issuer identities. Same-issuer news alone is not support for a particular Bio milestone.
3. Bind native entry geometry, real ATR/anchor provenance, candidate state, quote basis, and existing gates at a coherent read. The native reader still returns availability=None.
4. Admit point-in-time GMI peer membership and synchronized market observations through the existing owners before treating supplied peer arithmetic as a native theme assessment.
5. Carry authenticated corrections through the existing publisher and client; the local replay proves no live delivery path.

Disposition: **DRAFT / HOLD-FOR-SOL**. The consumer remains NONACTIVATED_RESEARCH_CONSUMER, source_admission_established=false, with all authority flags false and all advanced estimates unavailable. Source correctness, replay success and review acceptance do not qualify a best-entry policy or causal theme claim.
