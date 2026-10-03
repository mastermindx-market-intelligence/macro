# Codex quota, resets and model economics - 2026-10-01

Status: BUILT_NOT_PRODUCTION_PROVEN. This is a bounded implementation and research
candidate under WS:EXECUTIVE-CAPACITY-FABRIC, not new operating authority.
The parent mission is incomplete. No account was enrolled, switched, purchased,
reset, dispatched or reauthorized by this work. No production model default changed.

## Current evidence, not assumed readiness

Protected source pins at task admission: Mastermind
`abcd5edc99e78f59b3dce0ec4ef31b6aeb578704`; Macro
`912c06cd84f8461c8b449520fac32b4b18cb82da`.

A redacted inspection of M2's existing Codex Switcher v0.2.12 store found six
ChatGPT entries with auth_data present: four cached `pro` plan labels and two
`self_serve_business_prolite` labels. This establishes stored entries, not six
currently authenticated provider identities, entitlements, independently reservable
quota resources, or worker enrollments. No email, token or auth_data was exported.
The legacy Macro Codex capacity registry contains three named account slots;
headless convergence describes four Codex realms. Neither proves six are enrolled.

At 2026-10-01T23:38:08Z, the connected installed Executive reader remained readonly
on Mastermind `c7407c6c77ef82cc6590401e80cc8f1868dc9085` and Macro
`88804ed7079700c598bb8e04aa64307d1335402d`. It reported one AVAILABLE registry
worker, zero active Attempts, and zero queued/running Jobs. Registry AVAILABLE
is not a worker-process or inference-readiness proof. Mastermind #703 comment
5925327180 records that all four worker services were intentionally disabled,
the UID451 process was distnoted rather than an Executive worker, company readiness
was necessarily stale, and the Pro readiness receipts were absent. Comment
5925357177 retains the installed-reader grounding gate. Do not enable workers by
hand or retry the rejected native metadata/queue command described in #703.

The current host CLI is 0.159.2. A local schema export completed successfully and
contains ConsumeAccountRateLimitResetCreditParams (required idempotencyKey,
optional creditId) and ConsumeAccountRateLimitResetCreditResponse (required
outcome). This establishes local protocol support, not compatibility of the older
installed broker, account entitlement, or permission to execute a reset.

## Provider semantics that change the optimization

A banked reset is a finite promotional entitlement, not a renewable daily button.
Its own expiry is separate from the account's weekly renewal. Applying a full reset
refreshes the relevant five-hour and weekly windows and replaces the previous
weekly schedule; the old weekly date does not also refill. A no-op does not consume
a banked entitlement. Future grants are not guaranteed. The observed post-reset
provider timestamps, not a locally added seven days, are authoritative. [1]

Paid resets are a different purchase. OpenAI explicitly documents their weekly
clock as starting on the first subsequent Work/Codex request, not the payment
instant. They are not bankable; unused included allowance can be forfeited. No
purchase authority is included in this implementation. [2]

The supported native protocol now exposes account/rateLimits/read, optional
multi-bucket rateLimitsByLimitId, nullable reset-credit inventory, and
account/rateLimitResetCredit/consume. availableCount is authoritative even when
credit detail rows are partial or null. The consume call accepts an idempotencyKey
and optional opaque creditId. reset and alreadyRedeemed require a fresh limits
read; nothingToReset and noCredit do not justify inventing a new token. A network
failure is not evidence of non-consumption. [3]

The practical objective is useful accepted work, not burning every quota unit.
No fake work should be created to start a clock. A fixed 24-hour priority bucket
misses the important counterfactual: a manual reset can throw away both remaining
allowance and a near-term free refill. Conversely, delaying a reset that real work
requires can delay the replacement weekly clock. Both require demand, expiry and
provider semantics, not an account-name round robin.

## Implemented conservative reset counterfactuals

`engine/provider_codex_reset_economics.py` is a pure Provider Control helper.
It supplements, and does not replace, the generic quota-economics owner in held
Macro #7116. Its frozen inputs are qualified account/model observations, independent
shared-resource identities, one or two applicable native window budgets and
reserves, individually known banked entitlements, measured task costs/durations,
and the existing owner's ordered task prefix. It creates no queue or lease and
performs no I/O. Each window key is mandatory; an explicit null means the native
owner attests that constraint is not applicable. Missing, malformed or unknown
observations are not null. Costs for a non-applicable window must also be null;
at least one real native constraint is required.

Before any comparison it requires the first lawful suitability tier, verified
binding and eligibility, native evidence, no active claim, a CLEAR effect state,
known renewal semantics and a fresh observation. A reset boundary crossed since
observation requires a new native read. Unknown cost is not zero cost; duplicate
account/shared-resource aliases cannot manufacture capacity.

For each idle account, memoized bounded lookahead compares natural-window waits,
work before resetting, and a finite banked reset immediately before useful demand.
It keeps the owner's task order and checks every applicable rolling window and
reserve. Manual reset simulations discard each old renewal date; original-window
expiry rewards stop independently after natural renewal or redemption. The
forecast rechecks natural refills at reset completion, avoiding a reset that would
be a no-op after the configured latency. Clock calculations are forecasts only.
State-budget exhaustion refuses the candidate rather than presenting a truncated
search as optimal.

The resource-value heuristic uses joint capacity rather than adding overlapping
windows. For each remaining ordered task prefix, compute the number of complete
plus fractional tasks supported by each window's spendable balance, using each
task's measured cost in that window's units. Joint capacity is the minimum across
applicable constraints. Reset gain is joint full capacity minus joint current
capacity; forfeiture is joint current capacity. Cancelled free-refill opportunity
is the maximum, not the sum, of urgency-weighted window prefix capacities. Each
completed task earns only the maximum relevant original-window expiry reward,
never two rewards for consuming the same task through two limits. These are
conservative ranking heuristics, not monetary values or independent additive
quota pools. Identical duplicated constraints, exchanging window labels and
rescaling native units must leave the economic decision invariant.

Core and CLI regression cases have one owning import in
`tests/test_codex_runner_budget.py`, which is executed by the existing
`codex-research-engine` PR code gate. The data-gated provider-capacity suite does
not substitute for PR-hosted execution. A collection guard requires every case
function to be exported through that code-gate owner; no workflow or CI manifest
is changed by this repair. Actual hosted collection/execution remains a separate
acceptance check after the repaired head is published.

The deterministic lexicographic objective is: completed approved utility and task
count; preserve resets that outlive the supplied horizon when outcomes are equal;
recover imminent expiring resources net of forfeiture/free-refill opportunity;
fewer reset entitlements spent; lower measured normalized native burn; lower
weighted completion delay. Before account focus, depletion fraction and stable
identity, an otherwise-equal path uses a final mean-original-window-urgency
comparison (`expiry_tiebreak_forecast`). This is dimensionless preference, not
additional rescued quota: each task contributes at most one, identical duplicate
constraints preserve the mean, and cancelled/renewed originals contribute zero.
It cannot overrule utility, reset scarcity, normalized burn or completion delay.
This closes the dominance blind spot where equal short resets at +12000 seconds
masked weekly resets at +43200 versus +500000 seconds: both maximum resource
scores were 31/36, but the sooner weekly account now wins the final comparison
(49/72 versus 31/72) rather than losing to its account name or current focus.
A 24-hour continuous urgency horizon is a policy parameter, not a discontinuous
switch at hour 24.
Hashes make a decision replayable; they are not authentication or approval.

Important limitation: this is a conservative per-account, finite-prefix forecast,
not a proved global optimum across concurrent accounts or unknown future demand.
Its default horizon is at most seven days and it does not assign speculative
terminal value to another week of future demand. Therefore it must not be promoted
as the final portfolio scheduler or as proof that preserving a non-expiring reset
always dominates advancing its future weekly clock. The generic owner must compare
that cross-account opportunity using measured demand and outcomes before promotion.
One qualified model offer per account is accepted; Model Router resolves model
alternatives before this helper, so alias rows cannot double-count shared quota.

`python scripts/preview_codex_reset_economics.py <owner-evidence.json> --format text`
provides a read-only limits/decision viewer. JSON output is also supported. The
request schema is `mastermind.codex_reset_request/v1`; required fields are schema,
now, first_lawful_tier and observations. Dataclass field definitions specify each
closed record; optional policy and preferred_account_id are explicit. Input is
bounded to 512 KiB and duplicate/unknown fields are refused. Output labels balances
as supplied native units, not a live account refresh. This is not an installed GUI.

## Reset execution integration contract - not activated

Executive remains the sole account-claim/effect owner. The existing native broker
and admitted account home remain the authentication owner; do not copy Switcher
tokens into another refresh writer. Agent OS records references and outcomes only.

The intended sequence is native read -> owner-qualified model/cost cohort ->
preview -> current native revalidation -> existing exclusive account claim ->
persist one logical redemption identity in the existing operation -> supported
native consume call -> native limits readback -> resume the same authorized job.
A reset proposal cannot grant any of these gates. Keep the exact logical
idempotency key on same-carrier reconciliation; do not create another key, switch
accounts or resubmit a job because a response was lost. Never persist a locally
assumed 100 percent balance in place of provider readback. No paid reset fallback.

A proposed Mastermind consumer-bridge write was blocked before dispatch by the
tool safety-status check. Inspection confirmed the original projection file was
unchanged and the proposed cross-repo fixture absent. That bridge is NOT built;
the denied operation was not retried through another tool/account or encoded
payload. Resolve the tool restriction before resuming that affected lane.

Mastermind's allowed source changes add native reset-credit metadata to the existing
account_readiness projection, including authoritative count, nullable expiry,
partial/inconsistent details and explicit no-execution authority. New model price
records remain production_armed=false. Neither source change installs itself.

## Astra 6 versus Sol 6.1

Official Standard API prices, USD per million tokens, verified 2026-10-01: [4,5]

| Model | Uncached input | Cached input | Cache write | Output |
|---|---:|---:|---:|---:|
| GPT-6 Astra | 10 | 1 | 12.50 | 50 |
| GPT-6.1 Sol | 2 | 0.10 | 2.50 | 10 |

Both list a 1,050,000-token context and 128,000 maximum output. Above 272,000 input
tokens, the full request uses twice the input/cache rates and 1.5 times the output
rate. Fast API rates are separate from included-plan multipliers. Sol 6.1 tool
calling requires Responses rather than Chat Completions. The exact installed
harness and authorized model list still need qualification. [4,5]

For a request with 20K uncached input, 80K cached input and 10K output, the token
cost is $0.78 Astra versus $0.148 Sol. With 50K uncached, 250K cached and 10K output,
the long-context totals are $2.25 versus $0.40. These are arithmetic examples,
exclude tools/speed/regional premiums, and treat token categories as disjoint.
The catalog regression suite pins the exact 272000/272001 boundary.

Work/Codex Standard paid-credit rates per million input/cached/output tokens are
250/25/1250 for Astra, 50/2.5/250 for Sol 6.1 and 100/10/500 for Sol 5.6. Codex has
no separate cache-write charge. Paid-credit prices do NOT specify the rate of
included subscription depletion. A universal API-dollar-to-weekly-percent
conversion would be fabricated. [6]

OpenAI's Sol 6.1 release reports DeepSWE v1.1 parity with Astra around one-fifth
cost and an OSWorld 2 offline result within 2.1 percentage points around one-seventh
cost. It reports Terminal-Bench Science task costs of $5.47 versus $23.80. These
are vendor task/harness results, not measurements of this fleet, nor proof that
Sol 6.1 matches Astra on every long-horizon orchestration task. [7]

Design recommendation: qualify Sol 6.1 as the routine builder/debugger/research
executor; reserve Astra for ambiguous cross-system judgment, difficult unresolved
failures and work where its measured success premium outweighs extra burn. Do not
make every orchestrator call Astra by inheritance. Keep the main context bounded
and send small explicit work packets. Suitability and required verification come
before economics; a cheaper failed task plus repair may cost more than Astra.
No runtime default was changed by the price-catalog update.

## Promotion and real-world verification still owed

Use matched task cohorts, identical tools, input artifact and acceptance criteria,
separate model/effort/speed/context bins, and blinded outcome review. Measure
accepted completion, repair/retry count, wall time, uncached/cached/output tokens,
and actual before/after native short/weekly deltas. Exclude concurrent account
usage and windows spanning a reset from isolated burn attribution. Zero apparent
rounded quota change is censored, not free work. Preserve failures and refused
runs; do not benchmark only surviving easy jobs.

Compare total cost per accepted result, including failed attempts and repairs,
with conservative uncertainty bounds and a held-out representative cohort.
A small initial canary can establish wiring, not general model dominance. Promote
only through existing Model Router/Provider Control owners; keep the safer qualified
fallback without replaying unresolved effects. Standard speed is the evaluation
baseline; faster modes require a measured latency objective worth their burn.

Required final proof: approved source heads and review; exact installed release;
real per-account principal/entitlement and model access; fresh native usage/reset
inventory; one admitted useful job and its isolated burn delta; one genuinely
needed authorized banked redemption with idempotent result/readback; original-parent
consumption; and recovery without duplicate execution. Existing #703/#8237 owner
custody, #7116 HOLD and #633 EFFECT_UNKNOWN remain intact. Unit tests and a local
CLI preview do not satisfy this chain.

## Sources

[1] https://help.openai.com/en/articles/20001498-how-banked-codex-resets-work
[2] https://help.openai.com/en/articles/20001507-paid-weekly-work-and-codex-rate-limit-resets
[3] https://learn.chatgpt.com/docs/app-server (account API, rate limits and earned resets)
[4] https://developers.openai.com/api/docs/models/gpt-6-astra
[5] https://developers.openai.com/api/docs/models/gpt-6.1-sol
[6] https://learn.chatgpt.com/docs/pricing
[7] https://openai.com/index/introducing-gpt-6-1-sol/

Private operational evidence: redacted local store metadata; native CLI schema
export; connected Executive state at 23:38:08Z; Mastermind #703 comments
5925327180 and 5925357177; Macro #8237 and held #7116. Future status must be freshly
read from the existing owners rather than inferred from this dated report.
