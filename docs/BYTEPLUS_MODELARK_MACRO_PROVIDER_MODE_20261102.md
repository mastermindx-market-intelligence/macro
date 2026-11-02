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
credential or invoke the transport. A genuine private provider canary and
separately reviewed qualification must precede any live call. The transport
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

**Not yet proven:** Commercial issuer entitlement, correct account/region,
actual API key presence, authoritative quota/debit, real price for the model,
WorkerRegistry + Capacity admission, Executive Job/Attempt, or a production
caller for Mastermind's advisory quota projection. Do not flip the modes ON,
register workers or claim user-path delivery on these source-only tests.

References:
- https://docs.byteplus.com/en/docs/modelark/create-model-responses-api
- https://docs.byteplus.com/en/docs/modelark/model-list
- https://github.com/mastermindx-market-intelligence/Mastermind/pull/1824#issuecomment-6570322461
