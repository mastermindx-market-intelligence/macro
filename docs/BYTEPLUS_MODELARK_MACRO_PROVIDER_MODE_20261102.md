# BytePlus ModelArk commercial Responses provider (source-only)

**Owner:** Macro Shared AI Provider Control, through existing `engine.provider_production_modes`. **Downstream:** Mastermind #1824, root `modelark-commercial-integration-20261023`.

This code adds three *metered commercial* model identities, a provider-specific
Responses API adapter, and no new Capacity, scheduler, worker, retry, or
authorization plane.

| Mode | Pinned served model |
| --- | --- |
| `modelark_glm_flash_api` | `glm-5-3-flash-260828` |
| `modelark_deepseek_flash_api` | `deepseek-v4-1-flash-261017` |
| `modelark_dola_coding_api` | `dola-seed-2-1-turbo-260628` |

All three modes ship `enabled=false`. Each source request profile is
`UNQUALIFIED_PENDING_CANARY`; enabling a config record alone cannot read a
credential or invoke the transport. Commercial production use requires a
genuine private provider canary, owner-bound transport/account qualification,
and any actually applicable protected review and release requirements. The transport
uses `BYTEPLUS_MODELARK_API_KEY` only at the existing credential boundary
and the pinned commercial endpoint
`https://ark.ap-southeast.bytepluses.com/api/v3`.

The existing `requests` HTTP client sends one `POST /api/v3/responses`
with a 512-token source ceiling, `store=false`, `HTTPAdapter(max_retries=0)`,
and `allow_redirects=false`. No new OpenAI SDK dependency or provider retry
service is installed. A missing/mismatching served model, incomplete response, or missing text
cannot be reported as a successful provider call. Usage and price-state flow
through the existing Provider Health/`lib.ai_costs` writers; unknown price
or missing token counts are not fabricated.

**Critical isolation:** BytePlus Personal Coding Plan is a different
entitlement and uses `/api/coding` or `/api/coding/v3`. This route refuses
that path, never borrows subscription usage, and never falls back to it.

## Provider Control price source (estimated, not billed truth)

The existing `lib.ai_costs` price owner and `config/ai_pricing.yml`
now include the documented **commercial Standard** rate-card estimates
from BytePlus's October 30, 2026 publication:
- GLM 5.3 Flash 260828: input $0.15/M, output $0.50/M,
  cached input $0.03/M.
- DeepSeek V4.1 Flash 261017: **off-peak** input $0.15/M,
  output $0.60/M, cache hit $0.003/M; **peak** $0.30/M,
  $1.20/M, cache hit $0.006/M. Peak is Asia/Shanghai local
  Monday-Friday 09:00-12:00 and 14:00-18:00. Cost estimation for this
  model requires an explicit timezone-aware observation instant;
  omission returns UNKNOWN, not a fabricated constant price.
- Dola Seed 2.1 Turbo 260628: provisional family-published
  `dola-seed-2-1-turbo` Standard input $0.50/M, output
  $2.50/M, cache hit $0.10/M; the commercial issuer must confirm the
  versioned alias against actual billed usage.

These are **estimates** for economic selection and bounded issuer canary.
Provider invoice/debit is the separate owner of actual paid cost.
No pricing source silently authorizes credentials, quota, eligibility,
worker START or model activation. Cache storage per token-hour is
**not** treated as cache-creation token price, and such unknown
writes refuse an estimate.

Source: https://console.byteplus.com/ark/region:ap-southeast-1/docs/model-pricing
(updated 2026-10-30).

## Operator-only commercial canary (source stage)

`python3 -m engine.modelark_commercial_canary` is an explicit **one-request**
issuer qualification helper, not production activation. It requires all
checked-in provider modes OFF, an exact source SHA-256 pin, an independently
qualified `ai_costs` estimate at or below $0.01 for 256 input + 32 output
tokens, and both `--execute` plus `MM_MODELARK_COMMERCIAL_CANARY_MODE`
matching one of the three pinned mode IDs. Without these it refuses before
reading any commercial credential. A successful request does NOT prove
account-level debit, quota, Worker registration or entitlement.

Only the private credential owner may run the real canary in a single-use
operator process with the commercial key supplied by its existing private
secret mechanism. The runner temporarily enables one mode and marks one
profile qualified **only in that isolated process**, calls through the
existing `call_mode`/receipt writer, and immediately restores the original
source globals. It does not edit shipped configuration, deploy, enable
normal traffic, or authorize Fabric. It never prints the credential,
response text, or subscription account data. A caller-injected fake
transport is always reported as unverified rehearsal, never as an issuer
canary.

No actual canary is executed or billed by this source PR. The preflight
cost estimate is not a provider-enforced spending limit; the credential
owner must verify the console account spend cap and independently
reconcile real provider billing/usage after the call.

**Not yet proven:** Commercial issuer entitlement, correct account/region,
actual API key presence, authoritative quota/debit, real price for the model,
WorkerRegistry + Capacity admission, Executive Job/Attempt, or a production
caller for Mastermind's advisory quota projection. Do not flip the modes ON,
register workers or claim user-path delivery on these source-only tests.

References:
- https://docs.byteplus.com/en/docs/modelark/create-model-responses-api
- https://docs.byteplus.com/en/docs/modelark/model-list
- https://github.com/mastermindx-market-intelligence/Mastermind/pull/1824#issuecomment-6570322461

## Capacity contract reconciliation (2026-11-07 UTC)

This integration preserves the existing commercial transport and price owners.
The provider receipt now supplies its timezone-aware observation instant to
`lib.ai_costs.estimate_cost_usd`, including the DeepSeek temporal price owner.
The same estimate is passed to the existing usage writer; a known estimate
does not assert an observed provider debit. Peak and off-peak regression tests
exercise the real rate owner and one temporary usage-ledger row through an
injected, explicitly unverified canary transport. The three ModelArk test
suites are included in the existing provider CI job.

The downstream contracts were checked at immutable source heads:

| Owner | Source | Required boundary |
| --- | --- | --- |
| Shared Model Pool Control | Mastermind #2109, `8dc8eb42df7ed1f3c79f434da30df9ad12dafe14` | Logical model routing is separate from physical pool/account enrollment. Native Fabric retains selection, account eligibility, quota and admission; Macro retains application inference and provider-usage accounting. |
| Application admission and settlement | Mastermind #2175, `312be66141bf58c564a11818d63ddd3f958ca0c0` | A startup-registered transport and its exact recipe/account grants must exist before a route is offered. Selection is not execution authority. The incumbent broker atomically admits the turn/request, and the original handler settles the dispatch or preserves its unknown effect. |
| Commercial source | Mastermind #1824, merged `1e5f77a4e7aa5131ecbaef9bb00487882dec4d79` | Original source access was restored, the retained P2 repair applied, and current protected Capacity source integrated. The protected queue merged it at 2026-11-07T05:37:19Z; all 18 owned postimages were verified in the merged tree. Native commercial enrollment and consumer acceptance remain unproven. |
| Application consumer composition | Macro #10740, `abab96df55f82cb5c26459a6f51b568d73a6a6f8` | The existing application Fabric factory/client narrows an exact model within an already authorized route scope and validates its exact-request receipt. Native admission and account claims remain in the Capacity owner; narrowing does not enroll ModelArk. Compose this provider transport and temporal usage settlement with that owner without adding a lease, retry or second usage ledger. |

At those heads, #2175 has no registered BytePlus ModelArk application pool
or commercial transport recipe. Its native HTTP broker admits Bailian, while
the sealed HTTP projection permits only the reviewed Bailian/MiniMax
subscription drivers. The commercial realm requires a deliberate successor
contract and real account qualification; inert registration is not admission.
The merged ordinary Codex Worker adapter also explicitly refuses commercial
ModelArk START, even if transport registry membership is changed. Its eventual
successor must consume actual owner-bound Executive admission facts.

The existing native `glm` pool in #2175 must not be reinterpreted as a commercial BytePlus account. Likewise, the three Macro
mode IDs above must not be advertised as enrolled Fabric capacity merely
because their source records exist. The BytePlus commercial identity and
Personal Coding Plan identity remain separate, with their own eligibility,
credential boundary, quota and settlement evidence. No second pool controller,
Hermes-side selector, quota registry or usage ledger is introduced here.

Source release and live acceptance are separate. The existing credential
owner must first establish the commercial account, region, activated issuer
model and private key availability, authorize the bounded issuer canary,
and reconcile its authentic served-model/account/usage evidence. The
incumbent Capacity owners must then qualify and register the corresponding
transport recipe and exact grants through their existing publication and
admission path. Any uncertain request is reconciled on its original account
and dispatch before further execution; no provider fallback or replay is
authorized by this document.

Completion still requires a real canonical Fabric selection, its original
admitted consumer turn, a bounded successful commercial response, and
settlement against the same account/request with authentic provider usage.
The offline tests, source CI, merged code, or configured aliases cannot
substitute for those receipts. Until that evidence exists, all commercial
modes remain OFF and the live enrollment hold remains explicit.

Source references:
- https://github.com/mastermindx-market-intelligence/Mastermind/pull/2109
- https://github.com/mastermindx-market-intelligence/Mastermind/pull/2175
- https://github.com/mastermindx-market-intelligence/Mastermind/pull/1824#issuecomment-6702909104
- https://github.com/mastermindx-market-intelligence/Mastermind/blob/1e5f77a4e7aa5131ecbaef9bb00487882dec4d79/docs/runbooks/BYTEPLUS_MODELARK_COMMERCIAL_CANARY_HANDOFF.md
- https://github.com/mastermindx-market-intelligence/macro/pull/10740

