# Public research qualification — correction to the flagship R2 packet

Observation epoch: host receipts 2026-09-16T04:28–04:39Z; official documentation read during the same continuation. Owner: Sol, existing `macro-mastermind-ai` / `WS:MASTERMIND-AI-FLAGSHIP`. Procedure pin: Mastermind `11101d420179525678449820cbfd6228191c37ee`, compatible Skillpack 1.0.1/bootstrap1. This is a design correction and qualification contract, not a new service, provider activation, worker assignment, production feature or signal authority.

## 1. Correct the consequential assumption

This supersedes only the statement in section 6 of `R2_META_CEO_PROGRAM_PACKET_2026-09-14.md` that DeepSeek's current Responses API documents server-side web search. That earlier statement must not guide implementation now.

The current official DeepSeek Responses guide explicitly lists built-in `web_search`, `file_search`, `code_interpreter`, `computer_use`, and `mcp` tools as ignored. Unsupported fields can be silently ignored without an error. Function tools are supported. `max_tool_calls` is ignored; continuation state is client-owned. It also says historical `web_search_call` input items can be restored into context. Accepting prior search-shaped input is not performing a new search.

Primary sources:
- https://api-docs.deepseek.com/guides/responses_api/ — Compatibility Details / Tools; checked current page rather than older third-party claims.
- https://api-docs.deepseek.com/api/create-response/ — tool schema likewise states built-in types are ignored.
- https://api-docs.deepseek.com/guides/anthropic_api/ — application-defined tool schemas and tool choices are supported; compatibility does not provide the tool implementation.

No live DeepSeek capability experiment was executed in this continuation. The finding is documentation-backed and version-sensitive, not a universal claim about every historical model or reseller endpoint. A future contrary claim requires exact endpoint/model/account evidence; an HTTP200 answer is not enough.

## 2. Resulting architecture ruling

Do not switch the Brain transport merely to add `tools:[{type:web_search}]` to a DeepSeek request. That can leave exactly the current data-only experience while appearing successfully configured.

Keep the analyst model and evidence-retrieval capability separate. Use the existing Brain function-tool registration, dispatcher, request lifecycle, budgets, citations and authorized provider/workload owners. A retrieval tool must invoke a real, qualified search/open backend and return normalized evidence to the analyst. DeepSeek may remain an analyst if measured task quality warrants it; it does not need to supply the search index itself.

OpenAI's current Responses web-search documentation provides a candidate backend with domain filters, source-list return and live-versus-cache-only control. It is a qualification candidate, not an account/budget/rights grant. Do not turn the user's ChatGPT or engineering-Codex subscription into a customer-service credential. An independently licensed search provider plus the existing approved source reader is another candidate. Evaluate coverage and useful source recovery before vendor selection.

Reference: https://developers.openai.com/api/docs/guides/tools-web-search — Domain filtering, Sources, Live internet access, Limitations. `tool_choice:auto` can finish without searching. Requiring search for a qualification case and actually observing its result are separate conditions. Citation URLs do not by themselves prove that an exact supporting source passage was opened.

The existing #7179 workload-policy and #7185 AI Brief adoption owners remain responsible for shared provider/customer-workload separation. Do not build a competing credential pool, router, inference supervisor, cache store, quota ledger or CEO ingress. Customer research traffic must not become Chairman-authenticated Executive intent.

## 3. One useful first journey

User asks what a recent public company disclosure changes about an existing thesis. The task resolver fixes issuer/listing, economic period, requested cutoff and public evidence scope. The analyst identifies a material missing fact or contradiction. A minimal public query goes to the qualified backend; a relevant primary source is opened and checked for identity, event/publication dates and correction status. Existing deterministic financial tools perform applicable reconciliation. The answer explains which premise changes and why, names contrary evidence and uncertainty, and attaches inspectable sources. It does not claim a new calibrated signal.

Self-contained calculations do not need compulsory web search. A current-catalyst question must not be answered with a stale internal snapshot merely because search is unavailable. Published-only Research keeps its existing closed-corpus guarantee. Source absence, search failure, access denial, a weak snippet and contradictory disclosures are different results.

## 4. Freeze proof before adding the adapter

The qualification unit is endpoint + actual model + supported tool contract + caller entitlement/workload profile + source access + observed execution. A requested tool, model prose saying it searched, HTTP200, a source URL, and a completed request are not interchangeable evidence.

Required discriminators:
1. Positive current-source task: actual search activity, actual primary-source access and an answer grounded in a passage or table relevant to the question.
2. Silent-ignore negative: a successful model answer with no search execution must fail the search-required case.
3. Imported-history negative: a `web_search_call` item supplied as prior context must not qualify as new retrieval.
4. Snippet-only negative: failed source opening must be disclosed and must not be labeled full-source review.
5. Temporal negative: new publication about an old event must not become a new catalyst; later corrections cannot rewrite what was known at a historical cutoff.
6. Identity negative: same-name issuer, wrong listing, incompatible period, units or currency must fail the relevant claim.
7. Dependency negative: syndicated copies count as one source family; model agreement does not establish independence.
8. Privacy negative: private portfolio, notes, full conversation, account identifiers and secrets never enter public-search queries.
9. Budget/permission negative: search denial stops that path; no alternate account, provider or tool silently acquires permission. Enforce limits in the application rather than relying on ignored compatibility fields.
10. Completion negative: incomplete/failed terminal status or an unexecuted final tool request must not produce a completed-investigation label.
11. Compatibility negative: public research disabled or published-only mode yields zero external research effects.
12. Source safety negative: redirects/private destinations/injected page instructions cannot broaden the existing reader's permitted actions.

These are acceptance specifications, not executed passing tests. Reuse existing evaluation and response-record owners. Store only necessary source/output evidence through existing authorized retention, correction and rights mechanisms. A source receipt is provenance, not proof that the investment conclusion is correct.

## 5. Logical analysis must consume the evidence

The analyst must connect observation -> expectation gap -> economic mechanism -> financial consequence -> valuation/horizon implication -> competing explanation -> discriminating next observation. Each material link is observed fact, supplied assumption, deterministic calculation, external view, qualified house reading, or model hypothesis. Missing links remain missing.

The first live qualification must demonstrate an evidence-dependent conclusion: remove or change the material source and the affected claim must change or become unavailable. More URLs, longer prose or more worker calls are not success metrics. Compare the same model and question with owned context alone versus owned context plus qualified retrieval, then compare models. This isolates the value of evidence access from model differences.

## 6. Current R0 release boundary — exact observations, not new code

PR #7152 remains at `ba9e7654190934d3f7c8b997eb2b21bd3a077094`, local clean source matching the retained branch. Its previous independent review PASS and 857-test result remain historical evidence; no rerun or deployment is claimed here. Hosted run `35053698483` had all twelve executor packs queued at the fresh check. Job `104660799513` requires `ci-linux` and has no assigned runner.

A fresh organization runner GET (not merely the repository-local list) returned `pc-ci-1`, `pc-ci-2`, and `pc-ci-3` all offline. One read-only SSH attempt via the already configured `winpc-wsl` alias timed out after an 8-second connect limit. No new runner, label change, cancellation, service alteration or retry occurred. Restore the existing host/runner pool through its current owner, then let the same CI run finish; do not waive tests or move this product onto a different trusted-executor boundary.

The earlier Source Continuity `REMOTE_CENSUS_INCOMPLETE` result remains unresolved. Source inspection confirms a bounded global open-PR/files census; it does not establish which budget or branch caused that specific failure. No successful typed checkpoint or invented cause is asserted. Prior tool-denied diagnostics/browser-canary writes were not replayed.

## 7. Native Fabric integration safety finding

Installed `~/.local/bin/pool` resolves to the incumbent `meta-ceo-b-2026-09-08` kit. Wrapper SHA256 `b18b6d46bf22772e880ccd2df547c3f7bf2a5e6528dc67f6dd77f8a0310863cd`; `ext/sub.sh` SHA256 `67953b2a007ab57a6f0c74d98ac15b62ac78426d51b6dfb6fee1316cbc43b28a`.

`_compute_placement` checks a project's blanket Bash denial for several pools, then sets `LAUNCH_CWD` to the checkout parent and `RELOCATED=1`; normal submission calls that function. This is a source-proven permission-boundary risk, not an executed escape. Do not use relocation to overcome an originating denial. No pool command, provider, lease mutation or native worker was invoked here; no incumbent source was modified.

Both the runner evidence and launcher finding were sent as informational intake on the incumbent Fable root, not a new child, ruling or source takeover:
https://mastermindxgroup.slack.com/archives/C0BSBM78V1N/p1789533562479669?thread_ts=1789324397.992989&cid=C0BSBM78V1N
Delivery is not parent consumption or a repair. Existing W1-H3/H0/PF1 and native-kit ownership remain unchanged.

## 8. Next action and stop boundary

R0: restore reachability of the existing PC/WSL CI host through its authorized host owner; retain #7152's source, independent review and same run. Resolve the separate continuity proof, conclude required checks, then release and prove real financial answers. Do not replay historical P2 effect-unknown or tool-denied actions.

R1: qualify one sanctioned retrieval backend using the twelve cases above through the existing workload/provider and tool owners, then add the smallest search/open integration to the existing Brain. A working endpoint, entitlement, private-egress boundary and actual retrieved evidence are prerequisites for a live claim. No provider was qualified by this document. Architecture/code preparation can proceed where genuinely independent, but service activation and customer acceptance remain gated.

The larger flagship program remains incomplete. This continuation established exact release infrastructure unavailability, corrected a material vendor assumption, and raised a native-launcher boundary issue; it did not deliver new production AI behavior.
