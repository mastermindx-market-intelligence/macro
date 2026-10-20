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

## Optional sealed expression commitment

The expression publication seam keeps the current v2 candidate feed and v1 receipt
JSON bodies unchanged. It retains a versioned expression manifest in the incumbent
publisher's existing fsynced transaction and sealed cache. Both existing objects
commit that manifest's SHA256 in their metadata. It creates no object key, store,
collector or scheduler. The intended consumer is the same private research owner
with the original retained manifest; this is publication of its commitment, not
public distribution of the full private terms observation.

`make_expression_intent` requires the original preparation binding, its candidate,
an explicit `options.contract_terms_observation/v1` and a new actual decision clock.
The terms observation supplies exact contract, actual multiplier/deliverable,
effective interval, source availability/observation clocks and original source
provenance. It is a required normalized source interface, not proof that a producer
is authenticated or admitted. There is currently no provisioned terms producer in
this lane. Missing terms cannot be replaced with policy constants or an analyst
assertion. The intent stays research-only with every authority false.

The owner can pass validated intents through the existing optional
`publish_pair(..., expression_intents=[intent])` interface. A new expression requires
a new canonical feed generation. Reusing an old identical payload cannot attach an
expression or refresh its clock. Later generations automatically carry original
intents and their expression-specific first receipt identity/clock. Candidate time
is never expression time. The actual first receipt object's observed `LastModified`
establishes the commitment's availability; if its coarse clock precedes the intent
decision, availability remains unavailable, without clamping or backdating.

`read_expression_pair(..., lock_path=the_existing_publisher_lock)` reads the existing
journal/cache under the existing lock and verifies the exact retained manifest
against both objects' GET/HEAD metadata and ETags. `resolve_intent_availability(pair, id)`
returns the exact resolved intent bytes, their hash and the commitment publication
time for this private owner, or a named unavailable reason. A manifest passed to
legacy `read_pair` alone does not establish owner readback. The result explicitly
keeps `public_consumer_available=false`; this seam does not distribute the expression
bytes to a public consumer. Missing retained state remains unavailable. Source
admission, activation, capture eligibility and training eligibility stay false.
A legacy `read_pair` still reads the same v2/v1 bodies without the private manifest.

The optional path uses a versioned local publisher state so an old binary on the
same host rejects rather than ignores an expression transaction. Upgrade the single
incumbent writer before enabling this option; no concurrent old writer is supported.
Missing original retained state, changed intent/history, partial commitments,
metadata/ETag races, same-body receipt rewrites and unknown foreign generations
refuse writes. The private reader refuses a pending transaction; only original
publisher recovery can settle its effect. Recovery consumes
only the original durable transaction. Provider metadata is not covered by an ETag;
the protocol separately checks both commitments and retains the original manifest,
while requiring a new payload generation for new intents. It does not claim protection
against an arbitrary storage administrator forging a complete source history.

This change does not call the daily publisher, activate a policy, query quotes or
change campaign outcome persistence. The original correction/review boundary remains.

`publish_pair` reports the commitment effect, not positive intent availability.
Always resolve the private availability result separately: a coarse or inverted
provider clock is never rounded, clamped, backdated or replaced with a local time.
An invalid provider history after effects is retained on its original transaction
for reconciliation; automatic replay, state deletion and a new transaction are not
recovery. The manifest has a 16 MiB pre-effect bound and retains immutable history;
retirement would require a separate versioned history contract.
