---
key: ASTRA-FABRIC-LIVE-CLIENT-AND-SUBSCRIPTION-GATES
claim: >
  The first Astra -> Executive external-Fabric vertical currently has two independent live
  installation gates despite current protected Mastermind source containing the approved client
  architecture and Alibaba subscription-harness binding. First, the one live Auth0 Dynamic Client
  Registration attempt for the Codex Executive client is EFFECT_UNKNOWN: a pre-effect Keychain
  pending marker exists, no usable DCR response was received, and the available Chrome profile reaches
  the Auth0 Dashboard login page rather than an authenticated tenant. Second, the live Executive host
  config exposes only the existing worker-codex[-pro-*] generation and no reviewed v5 subscription
  worker config carrying harness_binding_id, so the protected Alibaba binding is not yet installed or
  provider-realm-enrolled on this host.
falsifier: >
  For the client gate, authenticate an authorized Auth0 tenant-admin surface and inspect Applications
  for the exact public client name "Mastermind Codex Astra" and callback
  http://127.0.0.1:8769/oauth/callback. If an exact client exists, reconcile its public tpc_ client ID
  into the existing pending registration; if the tenant proves no such client exists, the prior DCR
  effect can be re-admitted once. For the worker gate, show an installed root-reviewed
  mastermind.executive_worker_broker_config/v5 subscription worker configuration bound to
  alibaba-token-plan-personal.codex-responses plus owner-minted enrolled provider-realm and
  Capacity-available facts accepted by subscription_canary_admission. Protected source or a merged PR
  alone does not falsify the live-installation claim.
so_what: >
  Do not retry /oidc/register, delete the pending DCR marker, weaken the Executive OAuth resource, or
  copy ChatGPT credentials. Reconcile the exact Auth0 effect first. Independently, do not call the
  Alibaba lane production-ready or flip autonomous_allowed: install/enroll the reviewed v5
  subscription worker and satisfy the existing interactive-canary admission gates. Only after both
  paths are serviceable should Astra submit the real token-relief canary and measure exact-parent
  return plus the >=50% Astra/internal-Codex usage target.
kind: runtime
verified_at: 2026-09-14
verified_by: >
  Mastermind protected master bffe2ca8506346ea278c8ee469bf1ac30a4de008; merged PR #583
  7868e2c2727a8871f64f387de9ce00dc6a67cff9; Codex 0.154.0 live registration and native-login
  resource-mismatch canary; one guarded DCR call through
  ops.codex_fabric.enroll_executive_mcp.ensure_client_registration leaving PendingRegistration;
  targeted Chrome navigation to the Auth0 Applications dashboard returning the Auth0 login page;
  list_directory /Library/Application Support/MastermindExecutive/config; protected
  config/subscription_harness_bindings.v1.json and ops/executive_os/subscription_provider_credential.py.
scope:
  - WS:EXECUTIVE-CAPACITY-FABRIC
confidence: verified
---

## Evidence

Protected Mastermind `bffe2ca8506346ea278c8ee469bf1ac30a4de008` includes the merged Astra external-Fabric
architecture (#618), subscription plan-to-harness binding (#583), and the later bounded offline-delivery
autonomy source. The client implementation branch proves the existing five-tool Executive MCP ->
CeoIngress-v2 contract, exact-parent Wake discrimination, secret-free Codex registration, Keychain-backed
header injection, PKCE enrollment contracts, and fail-closed DCR reconciliation tests.

The installed Executive MCP is live at its reviewed loopback transport and Codex 0.154.0 has an enabled
`mastermind-executive` Streamable HTTP registration. Native `codex mcp login` cannot be used for this
installation: Codex refuses because the loopback transport reference differs from the protected
Secure-MCP-Tunnel OAuth resource identity. The client therefore keeps the server verifier unchanged and
uses a separate Keychain-backed public-client PKCE path.

The first DCR effect was guarded by writing a pending registration marker before the network call. That
call raised at the HTTP boundary before a usable response was available, so automatic retry is forbidden.
There is no authenticated Auth0 CLI/session available for reconciliation, and the targeted Chrome profile
lands on the Auth0 Dashboard login page. This is genuine effect uncertainty, not evidence of absence.

Separately, the protected Alibaba binding is intentionally `BUILT_NOT_PROVEN` and source-disarmed. Its
interactive canary requires an owner-minted provider-realm enrollment receipt and Capacity fact. The
live Executive config directory contains only the existing `worker-codex.json` and
`worker-codex-pro-{01,02,03}.json` generation; no installed v5 subscription config is visible. The
reviewed subscription credential CLI refuses enrollment/verification without a root-reviewed v5 config
carrying `harness_binding_id`.

## Consequence

There are two separate blockers and neither should be used to bypass the other:

1. reconcile the existing Auth0 DCR operation before any new registration or PKCE authorization;
2. install/enroll the protected Alibaba subscription worker through the existing v5 provider-realm path
   before claiming Capacity eligibility or running the real external provider canary.

Once both gates clear, the next product proof is the frozen closed loop: authenticated five-tool read,
exact Executive-owned Astra RuntimeBinding, one sealed interactive subscription-canary admission, one
substantive external worker result + independent review, exact-parent Wake/consumption, final Astra
acceptance, and a comparable baseline demonstrating at least 50% lower Astra + internal-Codex usage.
