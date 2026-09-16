# VPS and site AI integration with the existing capacity fabric

Status: CEO architecture decision and source implementation scope; NOT production acceptance.
Operation: vps-site-fabric-integration-20260915-sol-001.
Parent: WS:EXECUTIVE-CAPACITY-FABRIC; incumbent integration operation
agent-fabric-end-to-end-fable-integration-20260913-sol-001.
Carrier: Slack C0BSBM78V1N / 1789324397.992989.

## 0. Acceptance and authority

The outcome is one governed AI workforce serving development and Mastermind's product,
not a second router and not an OAuth proxy. Completion requires real service admission,
capacity reservation, execution, result consumption and failure recovery. This first
source slice only adds an opt-in purpose/transport boundary to the existing Macro gateway.
It does not arm a service, enroll an account, copy credentials, spend on a provider,
claim Executive readiness, authorize live trades or authorize autonomous deployment.

The Chairman reports four remaining Claude accounts, three 20x Codex accounts and two
Business Premium Codex accounts. Those totals are desired inventory evidence, not verified
native enrollments, independent quota domains or production API entitlements. Do not delete
numbered slots by guessing which three Claude accounts retired. Claude developer capacity
is reserved primarily for Fable, not ordinary site inference.

## 1. Verified starting point

Sources initially pinned at Macro bd33e0340c7066673cfb81d17b57fab965623c5b and
Mastermind e1f752a58df8f874efa12e30957d911627a0c4f8. This source workspace is based on
fresh Macro e9d469383c68aec55cf4c2723112fdf204f667cf; llm_auth.py and the capability
manifest are unchanged between those Macro pins.

- Macro engine/llm_auth.py builds a configurable provider waterfall, automatically adds
  attached Codex, and expands Claude OAuth credentials. The weekly brain ceiling is a
  soft preference, not a hard Fable reserve.
- engine/neuralweb/key_pool.py enumerates seven Claude slots and three Codex slots.
  Mastermind key-event federation is explicitly display-only for rotation decisions.
  Missing or wholly invalid METAB_KEYS_ENABLED means all enabled in the legacy code.
- Mastermind brain/provider_waterfall.py separately chooses native Codex then Claude.
  It calls _oauth_pool_candidates directly, NOT Macro build_providers. This first slice
  therefore does not cover the portfolio's native waterfall.
- A bounded VPS read found mastermind.service active in /opt/mastermind at
  e61f2951136bdc03a7ec2f5f12f960af26656a4c. Health reported waterfall,
  codex_available=false, reasoning_policy_ok=true and scheduled_runtime_ok=true.
  Green process health is not proof that developer reserves are protected.
- Macro's service unit advertises three isolated Codex homes; presence, enrollment,
  refreshed auth, quota and end-to-end readiness are separate facts.
- This CEO's Executive connector reported mode=fixture with its runtime database absent.
  No fixture submission was represented as a real job.

## 2. Ownership and execution architecture

Provider Control in Macro remains the account/credential-reference/availability/quota
owner. Model Router remains the stateless suitability filter. Existing Capacity and
Executive OS own eligible placement and atomic Job/Attempt/Worker claims. Existing
brokers and native harnesses execute. Agent OS is organizational memory; Relay/Wake and
Slack are transport/attention. No new provider database, scheduler, queue, retry ledger,
refresh daemon, host registry or lifecycle plane is introduced.

There are two execution classes behind this one governance system:

1. Inference: existing Macro site gateway, bounded request/response or streaming,
   commercial API adapters or explicitly qualified local inference. Product requests do
   not inherit filesystem, shell, deployment, OAuth-store or Chairman credentials.
2. Durable agent work: existing Executive admission with authenticated service principals,
   bounded capabilities and existing native adapters. Lobe research/maintenance submits a
   job, not an arbitrary shell prompt and not a request impersonating the Chairman.

The production website must not depend on an attended Mac being awake for every answer.
Keep production-capable execution available on the service side under approved budgets;
local workers are additional capacity, not a silent reliability dependency. Do not move
or clone Executive state to the VPS for convenience. Physical placement stays with the
incumbent runtime owner and its current H0/P0/CF2-I proof sequence.

## 3. Credential and entitlement boundary

Development subscription availability is not a general-purpose production API license.
Use provider-supported native authentication for authorized developer work. Use approved
API/cloud credentials for product inference; a transport allowlist is necessary but not
proof of entitlement, budget, data rights, model suitability or availability.

Official sources checked 2026-09-15:
- https://code.claude.com/docs/en/legal-and-compliance : product integrations and OAuth
  credential restrictions; do not intermediate Free/Pro/Max credentials for end users.
- https://developers.openai.com/codex/auth : native Codex authentication, workspace policy,
  API-key-based general API work and separate billing. Its headless bootstrap guidance
  does permit a supported auth-cache copy; the no-continuous-copy choice below is an
  architectural custody rule, not a claim that all provider bootstrap copies are banned.
- https://help.openai.com/en/articles/9793128-what-is-chatgpt-pro/ : plan limits and
  third-party-service restrictions; do not equate a plan multiplier to an API quota.

Preserve the incumbent MiniMax/Go eligibility rulings. Do not route unattended production
through interactive-only plans or manufacture one quota bucket per model/profile. API
spend is never newly authorized by this architecture or by fallback convenience.

## 4. Local-to-VPS propagation

One logical control plane does not require one machine holding every credential. Native
credential custodians own native refresh and enrollment; service-side API credentials
remain in the existing restricted secret store. Synchronize reviewed metadata and
observations, not OAuth caches, entire environment files or append-only quota ledgers.

Extend the existing acquisition/enrollment contracts, including the incumbent Family-B
native-realm and multihost work. A projected account needs a stable capability identity,
verified quota-domain binding, enrollment generation, enable/revoke state, supported
execution surface, model capabilities and freshness evidence. Unknown is not zero usage.
A credential replacement cannot silently retain a stale enrollment attestation.

Publish reviewed catalog/policy revisions through the existing authenticated release and
capacity-acquisition paths. Consumers acknowledge the adopted revision/content hash and
observation time. A hash identifies content; it does not authenticate it, prove freshness
or synchronize anything by itself. Retired IDs get tombstones. New claims must reject old
or revoked generations; in-flight attempts retain their original immutable evidence and
follow existing drain/cancel/effect-reconciliation rules. No bidirectional last-writer-wins
sync and no two owners refreshing the same native token behind each other's backs.

One atomic reservation must cover every shared quota resource and concurrency identity
before execution. After START, a timeout is not permission to replay on another account.
EFFECT_UNKNOWN stays on its carrier. An unavailable capacity owner closes admission to
new shared-subscription work; it does not unlock a secret Claude fallback.

## 5. First source slice: workload transport guard

Files: config/provider_workloads.v1.json, engine/provider_workload_policy.py,
engine/llm_auth.py, tests/test_provider_workload_policy.py and the existing LLM CI job.

Inputs are trusted server configuration only:
- cfg.workload_profile selects a declared purpose.
- MM_PROVIDER_WORKLOAD_PROFILE is an optional server-wide floor. A caller profile can
  narrow its permitted transports but cannot broaden the host floor.
- A profiled request must provide an explicit provider_order list. An empty list stays
  empty. No implicit paid rung, local downgrade or attached Codex insertion is permitted.
- Missing both selectors preserves the existing unprofiled behavior during migration.
  An explicitly empty, null or unknown selector is an error, never a legacy escape.

Inference profiles site_interactive, site_batch, portfolio_analysis and lobe_analysis
can allow only the existing anthropic API, deepseek API and explicitly configured ollama
adapters. Provider order and model parameters remain the caller's existing quality policy;
normal existing cooling behavior remains unchanged. Filtering happens before reading any
provider secret or probing attached Codex accounts. Raw OAuth and attached Codex are
excluded regardless of fallbacks, quota or a malformed attempt to broaden the manifest.

Profiles development_agent, fable_orchestration and lobe_maintenance require the existing
Executive/native execution path. Passing them to the generic inference builder is a typed
refusal, not an automatic worker spawn. Browser input must never populate these selectors.

The manifest is closed-schema, size-bounded, duplicate-key rejecting and freshly loaded
for each opted-in build. It contains no credentials, account IDs, quota or authority grants.
A pure decision contains only schema, policy revision/hash, applied profiles, execution
surface and permitted/denied transport names. Attach this receipt to internal descriptors;
never serialize the descriptors themselves because legacy descriptors contain credentials.
The receipt alone is not a quota claim, entitlement proof or production activation.

Failure behavior: invalid configuration raises a bounded ProviderWorkloadPolicyError
before secret access; no eligible configured transport yields an empty provider list with
no automatic restoration of a forbidden rung. Existing callers retain their typed degraded
response. Legacy callers and direct native bridges remain migration debt, explicitly.

### Configuration rollback distinction

An absent `MM_PROVIDER_WORKLOAD_PROFILE` leaves legacy behavior unchanged only
when the consumer also has no workload profile. An explicitly empty value is
invalid, not absent: `MM_PROVIDER_WORKLOAD_PROFILE=""` fails closed for callers
on that host. To remove a deliberately applied host floor during an approved
rollback, REMOVE the environment entry from the service configuration; do not
set it to an empty string. Removing the host floor does not remove a caller's
own profile. Consumers must surface typed refusals and must not catch them and
retry through an unprofiled/native path. These are rollout instructions, not
permission to change the running VPS configuration.

## 6. Integration order and proof obligations

A. Deliver this additive opt-in guard with red/green tests and existing gateway regressions.
   Keep the source PR Draft/HOLD-FOR-SOL until independent review and composition. Do not
   set the host profile on the running VPS until eligible replacement providers, consumer
   failure semantics, budgets and rollback have been proven.
B. Incumbent Fable resolves existing H0 native proof, independent P0 and CF2-I atomic claims,
   plus authenticated Executive admission/arm. #7116 is an economic preview, not allocator.
   Preserve #7103/#7142/#7143/#662/#7162 and active writer custody; compose, do not rewrite.
C. Reconcile the reported 4+5 development-account inventory through native owner receipts,
   retire exact old generations and distinguish account, workspace and shared quota limits.
D. Admit a least-privileged service principal through existing Executive OS. Require
   tenant/purpose binding, idempotency, expiry, maximum fanout/depth/turns, budget and
   capability envelope. Verify a real parent -> worker -> normalized result -> parent
   consumption path; a fixture result or CLI PONG is not acceptance.
E. Shadow one AI Brief via eligible inference and one bounded read-only lobe task via
   Executive. Compare factual grounding, latency, error rate, actual cost and reserve use.
   Then migrate site chat and paper-portfolio analysis with per-consumer rollback.
F. Adapt Mastermind's native provider_waterfall and remaining direct SDK/CLI callers to
   the same purpose/claim boundary. Only after coverage proof may unprofiled routes be
   rejected globally and legacy OAuth service dependencies removed.
G. Lobe maintenance starts observation-only, then bounded branch/test/PR repair. Independent
   review and existing release authority remain required. No autonomous live capital,
   self-granted credentials, governor edits or unrestricted production patching.

Acceptance matrix: exact retired generation never starts; caller cannot broaden host
policy; concurrent local/VPS requests cannot double-reserve; Mac offline degrades safely;
revocation during work respects effect state; policy revision adoption is visible; no
credentials in receipts; no untrusted request reaches native tools; each production
consumer proves real result consumption and rollback; Fable capacity is not a fallback.

## 7. Out of scope for this source slice

No global capacity claim, fleet-wide inventory truth, physical transport deployment,
credential rotation, API spend, new model registration, UI redesign or provider canary.
No assertion that the website already uses the subagent fabric. Source proof must not be
reported as production completion. The next boundary after this patch is incumbent runtime
readiness plus one genuinely entitled and budgeted service-consumer canary.
