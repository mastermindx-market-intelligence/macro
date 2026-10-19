# Exact-expression source preparation

The frozen `oa_exact_campaign_contract_research/v1` rule carries each newly formed,
accepted candidate's original exact campaign contract into a long, one-contract
research intent. It performs no chain search, quote-based optimization, ranking,
sizing or execution. Candidate formation and the OA3 outcome ruler retain their own
policy identities. Selection policy is preregistered and inactive; this source
change does not establish an activation or forward fence.

```sh
python3 scripts/prepare_options_alpha_expression.py \
  --candidate-feed /private/oa/candidate-composer-output.json \
  --campaign-ledger /private/oa/campaigns.jsonl \
  --theta-contracts /private/oa/retained-list-contracts.json
```

The optional Theta input is an already retained list-contracts response, not a
quote response. This command reads local files and emits a preparation to stdout.
It never accesses a quote endpoint, writes a store, activates a policy or appends an
outcome. It records actual local read and preparation clocks. Those clocks do not
assert source publication or durable expression availability.

The candidate input must be the native `compose_candidate_feed` result before
`enrich_candidate_outcomes`. The preparation refuses any candidate carrying
`post_formation_outcomes`. It takes the incumbent campaign `LedgerSnapshot`, verifies
the feed's source prefix, and reuses the candidate owner's immutable-formation
validator. The original qualifying campaign row supplies the contract; optional
later `campaign_context`, shortlist pins and Issue Desk decisions do not select it.
Every candidate is retained in the preparation; ordering serializes identities and
does not rank or prioritize them.

Theta's official list-contracts response supplies symbol, expiration, strike and
right. It can corroborate identity only. The preparation never fills multiplier or
standard deliverable from OA3 constants, OCC formatting, a vanilla-looking root or
an adjusted-root hint. Current terms remain null. A mismatched/ambiguous catalog or
identity is unavailable. Unsupported extra terms fields are not admitted as a new
source contract.

Each record binds the original feed byte hash/count, immutable native campaign row,
formation policy, independent selection policy, unchanged OA3 ruler and actual
preparation decision clock. Its canonical decision digest is a preparation binding,
not a source authentication or a durable activation receipt. It has null expression,
expression availability and capture request, all authority flags false and training
ineligible. Even an upstream activation claim cannot activate this selection rule.
An exit code of zero means the diagnostic was produced, not that formation or quote
capture is scientifically admitted.

The existing owners remain unchanged: `compose_candidate_feed` owns candidate
formation; its daily caller and `publish_pair` own publication. That daily caller is
held under the separate controlled-correction carrier. `options_signal_campaign`
owns the append-only campaign/outcome store, whose current schema explicitly keeps
option returns unavailable. This change adds no ledger, quote store or scheduler.

The remaining integration needs source-native exact multiplier/deliverable evidence,
the real protected-policy and activation forward fences, actual first expression
availability under its durable owner, and a versioned incumbent-owner option-outcome
binding. Only newly formed post-fence candidates may enter that future lane. Old
preparations and history cannot acquire eligibility by later re-observation. Then
the unchanged #8318 ruler and #9663 retained-evidence reader can consume genuine
entry/H+60/exit evidence or explicit source unavailability. No historical replay is
claimed as natural prospective proof here.

Source: [ThetaData contract response schema](https://thetadata.net/docs/operations/option_list_contracts.html).
