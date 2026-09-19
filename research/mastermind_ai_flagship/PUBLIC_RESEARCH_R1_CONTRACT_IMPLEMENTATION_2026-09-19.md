# Mastermind AI R1 — public research contract implementation receipt

Date: 2026-09-19.
Operation: `mastermind-ai-public-research-r1-20260919-sol-001`.
Accountable seat/source writer: Sol / Meta-CEO under the Chairman's continuing commission.
Procedure pin: Mastermind protected `733389933e605e508517732fb6c69b6c18b7fef6`,
Skillpack `mastermind.sol_skillpack.v1` 1.0.1/bootstrap1.
Macro pickup base: `dfcab9236060b22578ed5714ff18debd90647c28`.
State: **BUILT_NOT_PROVEN**. No external provider call, API credential, Brain search tool,
customer request, deployment, signal/ranking authority or trading action is created by this wave.

## Capability built

This wave turns the R1 design from prose into a credential-free contract that the existing Brain
can later consume without binding to one search vendor.

`engine/neuralweb/public_research.py` now owns:

- a closed `brain.public_evidence_request.v1` envelope whose allowed fields are public issuer/listing
  identity, one bounded evidence-need family, time window/cutoff and source preference;
- deterministic public query construction; caller-provided free-form `query`, `prompt`,
  private portfolio/notes/conversation/account fields are refused;
- search-result normalization where search is `discovery_only`, duplicate URLs collapse, literal
  private hosts are dropped, and snippets/titles are explicitly untrusted;
- a fail-closed `open_public_source` contract. It has **no default network transport**. A separately
  qualified transport must receive the exact public-IP set validated by the opener for each hop;
- HTTPS-only, no-userinfo, port-443, public-literal/DNS checks; public redirects are bounded and each
  hop is re-resolved/revalidated, including redirect-cycle refusal;
- text/HTML-only first slice, byte/content-length limits, empty/invalid response refusal, script/style
  omission, exact source hash/fetch-time/final-URL receipt, and untrusted-content labeling.

The absence of an implicit transport is intentional: URL validation followed by a normal high-level
client can re-resolve DNS and create a rebinding gap. The opener therefore supplies an admitted
transport the already-validated addresses rather than pretending a hostname check alone is sufficient.

`engine/neuralweb/public_search_backends.py` now owns pure vendor adapters only:

- OpenAI Responses payload for `web_search`, with an admitted Luna/Terra model choice,
  required tool use, full source-list inclusion and no credential in the payload;
- OpenAI normalization counts only completed `web_search_call` actions whose action type is
  `search`; assistant prose, `open_page` and `find_in_page` do not satisfy search execution;
- Brave Web Search payload with bounded count, US/en qualification profile and optional custom date
  freshness;
- Brave response normalization. Error responses do not become executed search.

Neither module performs provider HTTP search, reads a secret, selects a customer account, retries,
fails over, routes models, opens a browser, persists a new store or changes existing lifecycle owners.

## Why this architecture

Search discovery and source evidence are different capabilities. The search provider can recommend a
URL, but a material investment claim is not grounded until the application-owned opener successfully
retrieves the supporting source. This prevents a model answer, search snippet, citation list or URL
from being represented as full-source research.

The attached Codex subscription provider is not reused: current main explicitly disables its web
search and subagents for the provider turn. Customer web research needs its own admitted workload
credential, not a Chairman/ChatGPT/Codex engineering account.

Current API contracts were rechecked on 2026-09-19:
- OpenAI Responses web search: https://developers.openai.com/api/docs/guides/tools-web-search
- OpenAI Responses tool choice: https://developers.openai.com/api/reference
- Brave Web Search: https://api-dashboard.search.brave.com/app/documentation/web-search
- Brave Web Search reference: https://api-dashboard.search.brave.com/api-reference/web/search/post

These URLs are documentation evidence only; no API/account was qualified by reading them.

## Test evidence

Existing Company Intelligence neural-reader baseline after operation-local Python environment setup:
**17 passed**. The first baseline failure was only the isolated venv missing PyYAML; no source edit
was made to green it.

TDD:
- initial R1 module contract: **7 failed** because the module was absent;
- initial hostile contract pass reproduced **5** defects: post-cutoff search windows, literal-private
  search candidates, missing untrusted-content label, lying Content-Length and redirect cycles;
- each defect was repaired without widening source/provider authority;
- vendor-adapter RED: **4 failed** because the adapter module was absent;
- adapter hostile cases cover non-search web actions, private candidates through the application
  normalizer, empty executed searches, invalid result counts and unadmitted models;
- the opener passes the exact public address set to the transport and rebinds each public redirect to
  the addresses validated for that hop;
- `open_public_source` has no implicit/default transport.

Final local command:
```bash
PYTHONDONTWRITEBYTECODE=1 <operation-venv>/python -m pytest \
  tests/test_company_intelligence_neural_reader.py -q -p no:cacheprovider
```
A principal pre-review adversarial pass then added three discriminators before any
independent reviewer STARTed: listing identity must be present in the search query,
`open_public_source` must reject invalid text/timeout bounds before transport, and
the OpenAI search instruction must honor `source_preference`. All three tests failed
on the first run and were repaired.

Final frozen local command:
```bash
PYTHONDONTWRITEBYTECODE=1 <operation-venv>/python -m pytest \
  tests/test_company_intelligence_neural_reader.py -q -p no:cacheprovider
```
Result: **44 passed**. Fresh `git diff --check` and `py_compile` for both new modules
passed in the same verification cycle. A fresh fetch of current main showed zero
movement on candidate-owned or declared dependency paths.

## Boundaries still owed

This wave does **not** prove:
- a search provider credential/workload is admitted;
- OpenAI, Brave or another backend actually searched for Mastermind;
- a source transport capable of pinning connections to the validated address set is qualified;
- Brain exposes/uses `search_public_sources` or `open_public_source`;
- published-only Research mode remains compatible after future Brain wiring;
- an external-research obligation is produced/enforced on real turns;
- a live answer changes because newly opened evidence changed a thesis premise;
- customer/browser behavior, production latency/cost, entitlement, rights or retention acceptance.

## Exact next action

Freeze and review this provider-neutral contract first. Then qualify one actual search backend and one
address-pinning source transport under the existing provider/workload owner. Only after those gates
may the existing Brain expose the two tools. The first real acceptance is one company question where a
current evidence gap causes observed search, primary-source opening, evidence-dependent analysis, and
an inspectable customer citation; removing the sole material evidence must remove/qualify the affected
claim unless equivalent independent evidence remains.

R0 financial-scope PR #7152 and the retained Studio financial-bridge carrier remain separate operations.
Do not merge their source or use R1 to waive their release/CI/production gates.
