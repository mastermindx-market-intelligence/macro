# OpenCode Go: dynamic offer discovery and bounded adaptation

## Outcome and capability boundary

The user job is uninterrupted, understandable coding work without manually maintaining model menus, token prices or quota resets. The machine job is to discover provider changes, distinguish advertised capacity from usable entitlements, estimate future consumption, and preserve one agent's workspace, transcript and effect history. The moat is effective work per prepaid resource, not the number of API keys or the size of a catalog.

This increment supplies a read-only metadata producer, change classifier and machine-readable preview. It does not claim a running self-healing router. State: BUILT_NOT_PROVEN for the metadata slice; PARTIAL for the full Go integration. No provider inference, account enrollment, scheduled service, persistent catalog, new quota ledger or worker was created.

Procedure: Mastermind protected master 935f8d05d7f855f810c5f14c005ab845305f235f; Skillpack 1.0.1, bootstrap 1. Source operation: opencode-go-offer-discovery-20260914-sol-001. Carrier: Macro PR #7143, sol/opencode-go-subscription-usage. Implementation: 74eb5e946963f87e284ae37f3307eaeab0f93e7d, parent d8127bded3a9a35bc501e786d27fa32f0ecdd923. The prior authenticated usage parser is unchanged.

## Verified public interfaces

1. GET https://opencode.ai/zen/go/v1/models: the public response observed on 2026-09-14 contains 37 IDs. Each record has id, object, created and owned_by, not token prices, allowances, context sizes, tool capabilities or account-specific access. OpenCode's modelsHandler.ts generates created from Date.now(); it is not a release timestamp. Ignore created and ordering in semantic change detection, but preserve source provenance.
2. GET https://opencode.ai/zen/go/v1/usage: current published source authenticates a Bearer key and returns rolling, weekly and monthly status/percent/resetsAt. It does not supply absolute limits or a safe durable enrollment-identity witness. This turn did not use a real key. Source code may proxy to newer infrastructure, so a native account canary is still required.
3. https://opencode.ai/docs/go/: the requested published page provides model-equivalent allowances, token-rate variants, endpoint mapping, training/retention policies, and conditional footnotes. Its endpoint table contains 28 IDs and its pricing table 36 variants. Nine IDs in the API do not have matching current offer rows; the preview exposes them as unknown rather than inferring aliases. MiniMax M2.5 has endpoint/rate rows but no matching privacy row in this page.
4. Models.dev additionally publishes https://models.dev/api.json (provider details), /models.json (underlying model metadata), and /catalog.json (combined). OpenCode uses Models.dev. It is a useful source of capability hypotheses and serving overrides, not Go account quota truth. The inspected Go DeepSeek V4.1 Flash TOML has one input/output/cache price and no Go allowance, peak schedule or promotion contract. Never substitute that flat rate for the complete Go offer. The Models.dev JSON response could not be read through this environment; the website and exact repository TOMLs were inspected instead. A Models.dev importer is not implemented in this increment.

The v2 Go documentation page surfaced by search gives a different, older-looking lineup and universal-dollar presentation. Do not merge facts across URL variants because one search result ranks higher. Bind each claim to its exact source URL, source revision and observation time; conflicts are explicit evidence, not a vote.

## What a dollar limit means

Keep four quantities separate: subscription cash paid, advertised token-valued consumption, normalized quota debit, and provider-reported remaining usage. They are not interchangeable currencies.

For a model with advertised monthly equivalent L, current documented fractions are 0.2 for five-hour, 0.5 for weekly and 1 for monthly. Thus L=60 gives 12/30/60, L=30 gives 6/15/30, and L=15 gives 3/7.5/15. This is not an independent balance for each model. The inspected upstream shared subscription ledger applies model cost multipliers.

Let C be a future request's dollar-valued usage quote from the existing model-economics owner. Estimated percentage-point debit for horizon h is 100*C/(L*f_h). A 0.60 quote under L=60 predicts 5/2/1 points; under L=15 it predicts 20/8/4 points. These are estimates, never provider observations. Changing models does not refill account usage. Under unchanged fractions, five completely consumed short-window allocations also consume a whole monthly allowance; short-window resets do not imply unlimited sustained capacity.

The existing token calculator must preserve disjoint uncached input, cache reads, cache writes, output and provider-reported reasoning billing semantics. Do not double count cached input or assume every next prompt is a cache hit. Context bands, time bands and promotional multipliers belong to the concrete model's provider surface, not just its family name. Request counts in marketing tables are illustrations, not enforced counters.

An offer change triggers a new quote and fresh account observation. Never retroactively multiply already-observed percentages, reset a ledger, or use a price decrease to fabricate free quota. The account API remains the source of current usage; its quantized percentages do not establish an exact number of remaining tokens. Concurrent in-flight reservations still belong to the existing allocation owner.

## Architecture: extend owners, do not create another router

Public inventory and offer readers feed Macro Shared Provider Control's observation surface. Validated offer facts propose updates to the existing subscription-plan and Mastermind model-economics owners. Model Router retains task suitability and quality equivalence; the existing harness catalog retains endpoint/protocol/tool compatibility. Capacity Fabric and Executive retain claim-time allocation and lifecycle. The transport continues to consume an approved account choice; it neither polls every source for every prompt nor maintains its own registry.

A useful route is the intersection of provider listing, known offer and data policy, actual account access and quota, implemented harness compatibility, and approved task suitability. An API listing by itself proves only the first condition.

Keep independent revisions for inventory, offer/rates, data policy, enrollment, membership, usage observation and logical request. A new model or new price must not change the pool-membership generation. A replaced credential must invalidate its enrollment evidence even when its display label is unchanged. A source freshness timestamp is not an entitlement generation.

## Automatic adaptation policy

The runtime target is observe -> validate -> semantic diff -> propose owner change -> existing gates -> publish one accepted snapshot. This increment implements the read/diff/preview portion, not the final publication or routing edges.

- New ID: discover automatically, retain as NOT_BUILT/SPEC_ONLY as appropriate, and evaluate protocol, tool calls, streaming, context, privacy and quality. Existing approved canary recipes can eventually promote routine candidates under preapproved thresholds. Discovery never declares frontier-level suitability.
- Confirmed removed ID: stop new requests/admissions for that route. Do not cancel a completed tool, kill unrelated work, or silently replace the model inside a running request.
- Recognized price/allowance change: re-quote future work and re-observe account usage. Apply only through the existing policy and allocation owner. Unknown billing units or ambiguous bands remain ineligible for economic comparison.
- Promotion expires: apply a pre-reviewed effective-time rule or invalidate the offer lease and revalidate. Current DeepSeek V4.1 Flash promotion says Ends Sep 20, but does not establish an exact cutover timezone here. Do not invent that provider timestamp. This code preserves baseline/current values and requires promotion revalidation; it does not pretend to implement the future-time activation evaluator.
- Privacy/retention change: block new sensitive requests pending applicable policy validation. DeepSeek's published conditional ZDR period and Muse's training consent must not become permanent unconditional flags. No automatic consent, region-setting change or paid-overflow activation.
- Schema change: refuse that observation and emit a repair reason. Never silently accept zero prices, infinite quota or a missing model list. Repair source parsers through the normal code-review path; do not execute fetched text or let an LLM directly rewrite live policy.
- Fetch failure or anomalous empty catalog: keep the last accepted observation only within its existing validity period. Do not overwrite it with an empty list or extend its age by rewrapping it. A strict new parser may reject extra fields; this conservatism is deliberate until a schema version is reviewed.

Suggested owner polling, not a created timer: public inventory every 15 minutes with a one-hour maximum age; public terms hourly with a six-hour maximum age; active account usage roughly every 60-120 seconds, after refusal, near exhaustion and after reset. Respect provider responses and use jitter/backoff at the existing owner. Public reads are provider-wide, not multiplied by each agent or account. ETag/conditional GET can be added only after support is observed. Polling cannot guarantee zero exposure to an unannounced immediate price change; safety reserves and last-moment server enforcement remain necessary.

## Session continuity

Model, protocol, canonical transcript, completed tool results and workspace remain owned by the running harness. Metadata can invalidate future requests or alter eligible capacity, but does not rewrite current context. If the model disappears, preserve the task and request an explicit model-continuation decision under existing authority. Replay only genuinely unexecuted inference after an approved pre-effect refusal. Partial stream, timeout or ambiguous acceptance is never permission for another provider call. A vendor can also change weights behind a stable ID: periodic behavioral canaries are required because the listing exposes no immutable weights revision.

## Source implementation and evidence

Added engine/provider_subscription_catalog_opencode.py, scripts/opencode_go_catalog_preview.py, a dedicated test file and factual fixtures. The module derives all documented model/rate rows dynamically, hashes semantic inventory separately from changing timestamps, parses model-equivalent windows, retains rate variants and policy footnotes, and classifies changes. All preview rows have routing_authorized=false; production_armed=false.

The CLI offers explicit --live public reads or an offline fixture path with a supplied evidence timestamp. Live mode rejects caller-selected clocks or fixture arguments. HTTPS origins and inference-free GET paths are fixed; redirects are refused. No secret is needed. The cost helper takes an existing dollar quote and converts it to estimated quota points, so it does not duplicate the model token calculator.

48 new tests passed. With the previous 84 parser/selector/transport checks, 132 passed in 3.71 seconds using Python 3.13.5 / pytest 9.0.2 in an isolated Linux fixture. Tested and published Git blob identities matched. Factual tables/IDs were transcribed from the sources above; the fixture is not a raw HTTP or HTML capture. HTML decoding is tested against synthetic HTML only. Sandbox networking could not acquire the actual HTML bytes, so default acquisition and actual-page parsing are BUILT_NOT_PROVEN despite successful browser-tool research. Full repository CI, native integration and independent review remain unestablished.

## Existing dependencies and exact continuation

Mastermind #583 merged as 7868e2c2727a8871f64f387de9ce00dc6a67cff9. #622 remains at 097e1bac090be8f254013a2729e0f7ef69c94054, retargeted to master with composition conflicts; do not resurrect its older parent enrollment/ACL code. Macro #7103 remains draft at 297cfa5451f1b9ed2be242e68942adaf0a927692; #7143 stays on its existing base. Model economics #594 remains draft at 52a0c8090df856243c96c713a65a3cc5592a1a72. No sibling source was overwritten or merged here.

Next bounded capability is to validate this public reader against actual response bytes on a permitted execution surface, then compose its metadata into the existing single-account streaming binding on #622 after current-parent reconciliation. Extend the existing #594 offer evaluator with reviewed effective-time/context/promotion rules rather than adding a second calculator. Account enrollment, safe identity, reservations and policy remain separate activation gates. Three user-reported registrations do not themselves satisfy these gates. No worker/Fable assignment, watcher or timer was created; Sol retains acceptance.

## Primary sources

- https://opencode.ai/docs/go/
- https://opencode.ai/zen/go/v1/models
- https://opencode.ai/v2/docs/console/go (conflicting presentation; not merged into the selected source)
- anomalyco/opencode@228e9095ba3988a02664c3816cb51f98584e86c2: packages/console/app/src/routes/zen/go/v1/models.ts; ../usage.ts; ../util/modelsHandler.ts; packages/web/src/content/docs/go.mdx.
- Shared-quota implementation already inspected in anomalyco/opencode@df23b7f9488a38e6f8064a0739d4f8cde86d7cfb: packages/console/app/src/routes/zen/util/handler.ts and packages/console/app/src/lib/lite-usage.ts.
- https://models.dev/ and https://opencode.ai/v2/docs/models
- anomalyco/models.dev@c142a1f8d11298643ebf9313fa889415775b3a4a: providers/opencode-go/provider.toml and providers/opencode-go/models/deepseek-v4.1-flash.toml.
