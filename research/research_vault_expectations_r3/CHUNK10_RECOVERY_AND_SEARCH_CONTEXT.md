# Research Vault — Chunk 10: recovered candidate and connected search context

**2026-09-16. Customer upgrade remains SPEC_ONLY; selected repair candidate is locally tested, not adopted, merged, deployed or production-proven.** This records a bounded continuation of the institutional-intelligence program, not a replacement search platform.

## Mission and authority

Make permitted institutional evidence useful in Prophet/company research, Mastermind AI, private portfolio context, news and original editorial. Search reliability supports that outcome; it is not the finished moat. Existing source, identity, entitlement, publication and market-signal owners remain authoritative. Research does not alter Prophet signals, rankings, sizing or execution.

Protected procedure: Mastermind@8ba7deedde164c90298d3e88785d98e02fa5e2d2, Skillpack1.0.1/bootstrap1. INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION, RECONCILE_STATE and CLOSEOUT fetched at that pin; compact rereads matched immutable full procedures already loaded. Current live Chairman direction is intent, not a waiver of source/permission/runtime gates.

Same carrier: Macro #7182 / sol/research-vault-intelligence-design-r2-20260915. Recovered head e62f39677466b0c342b750357b0e3aa10e13a708. Direct work: PRINCIPAL_JUDGMENT for cross-layer behavior and LOWER_TOTAL_OVERHEAD for the bounded isolated review. No new workstream, Job, Attempt, worker, watcher, provider call or control plane.

Runtime inspection pin: macro@e729d0fd9d48868b49a1911d4098c689b3d373bd. Client ranges1390–1473 and1470–1750 returned blob1f0b673da6c3d6a44ad3d74b2994f70b9a4311c8. Whole upstream client/API source and whole-application integration remain unverified.

## 1. Recovery: R9 survived; the PR body lagged

The branch and Agent OS handoff contained R9 while the PR body still described R8 at1b1543ff98a333d3c80ca465a54937f035859d59. This is projection lag, not permission to reset the branch or rebuild the previous candidate.

Recovered records: corpus_search_r9.patch, component_candidates_r9.md, CHUNK9_TESTED_REPAIR_CANDIDATE.md, verification_r9.json and the handoff. R9's receipt records60 local checks passed. **Those60 checks were not rerun here.** The referenced R9 ZIP was not among this turn's mounted attachments; only its report was present. Do not infer that the ZIP never existed elsewhere or fabricate the missing test execution.

The selected R9 client and renderer code blocks were recovered and matched the retained receipt hashes exactly:
- client2460075492f450fda043f1ddd69b32a720d0e622b5bbe7880fde2bfb2325cf48;
- rendererb6d96b80ccab06226075318bbaade85bfe578aaad45fbfbd9b8678cca6caa686.

The recovered core corpus patch remains unchanged. Matching selected proposal bytes is not full runtime-file parity.

## 2. Newly tested gap: rejecting old work is not starting replacement work

Current source wiring calls onSearchInput for an institution facet selection, but clearing a filter chip and several other context transitions render without calling that input handler. R9's stronger context guard prevents stale answers, yet its renderer could merely tell the user to refresh instead of scheduling the new scoped request.

R10 adds syncResearchSearch to the SAME selected client and calls it at the start of the SAME selected renderer. It starts a debounced request on changed scope, cancels queued work on query clear, and does not start another request on an unchanged redraw. The helper does not recursively render. Completion returns through the existing renderer.

This is not a new scheduler service or auto-retry controller. A failed search redrawn repeatedly stays unavailable; only changed scope or explicit resubmission starts another request. Production event coverage still requires whole-client integration and browser proof.

## 3. Two other failure-completion corrections

**JSON null:** R9 used null for internal ignored-response control flow and also ignored a real JSON null reply. A successful HTTP response could remain pending indefinitely. R10 uses a private object sentinel. Wire null takes the unavailable path and is labelled incomplete retrieval, not successful no-match.

**Synchronous helper exception:** R9 invoked withAuth before entering the promise rejection chain. R10 invokes it within a promise callback, so a synchronous throw and a rejected promise reach the same unavailable behavior. This changes error handling, not authentication or permission authority.

No network deadline was added. A never-settling promise remains outside this bounded amendment. Do not describe every possible hang as fixed.

## 4. Actual verification

New suite on retained R9:31 checks,16 pass,15 fail. R10:31 checks,31 pass,0 fail. The15 failures are checks across three failure families, not15 independent production bugs.

Final full reproduction:2026-09-16T09:48:49.890Z, Nodev22.16.0. Candidate syntax checks pass. Selected new client SHA256:01b29d4261def1168f735b79814a6aaa7e21e13e2453d222347e052ae47511f0. Selected new renderer:ba1f242c38cbda8307da1583dbd5aca24912da73501c2c5d5ad603e1eb07e031.

Tests exercise null/malformed replies; healthy/empty/unavailable/denied states; institution/theme/side/lane/catalog/tier/principal transitions; out-of-order results; returning to earlier context; query clear; coalescing; language-only redraw; labelled permitted fallback; and no source-record mutation. The terminal-newline ID case already passed against R9 and is not claimed as a new red-green repair.

Six disposable deliberate regressions were all rejected: disconnected render hook12 failures; null ambiguity2; query-only freshness2; synchronous-helper capture removal1; same-scope coalescing removal20; denial widening3. Direct local challenge, not independent review or extra passing cases in31. The actual candidate was not modified by these tests.

Two separate reproduction guards passed: a changed baseline is refused before output-directory creation; an existing output directory is not overwritten. These are artifact guards, not customer cases.

Scope: selected byte-verified R9 proposal blocks, selected renderer, NodeVM and controlled timers/network/DOM/auth with synthetic records. No actual browser, HTTP application, institutional source, billing, source-rights decision, live database or LLM. No rerun or aggregation of R9's60, R5's111 or the proposed120-question benchmark.

## 5. Durable reproduction, not a missing chat dependency

Three new files under r10/ preserve the actual new runnable work:
- reproduce_r10.py — reads the two JavaScript blocks from existing component_candidates_r9.md, checks retained SHA256 identities, generates selected baseline/candidate files into a NEW isolated directory, and runs red/green/mutation/final checks;
- test_search_context.js — the full31-case harness;
- mutation_review.py — six targeted challenges in disposable copies.

These three files were read back at9636eb0d1b1a5f8a7b268608287de0a9d56393a7 and matched their tested local Git blobs: e57b5cae43673eb29e6634629479e07311e908d1, fe76ee932c5186dea7531af29fce8c27c0aa4698, and3cab2160640271ccb0a230f99d8882950be8a3af respectively.

```sh
python research/research_vault_expectations_r3/r10/reproduce_r10.py \
  --output-dir /tmp/research-vault-r10-review-new
```

The output directory must not exist. Node/Python must already be installed. No network fetch, package install, credential, host, browser or runtime mutation occurs. The generated diff is against selected REVIEW COMPONENTS, not a verified whole-client runtime patch. Markdown code-block extraction here is an exact-hash research-fixture operation, never a runtime ingestion path.

The conversation package includes selected baseline/candidate files and raw outputs for independent offline recovery. The expanded conversation report is not asserted byte-identical to this compact canonical report.

## 6. Integration order, acceptance and stop condition

1. Existing Vault/#7045 and Brain/#7079 owners identify or accept the integration writer and interface. R10 is an amendment to the review proposal, not unilateral adoption into their runtime paths.
2. Adopt/amend R9 corpus/API scoped and strict search plus R10 selected client/renderer against complete current source. Replace superseded declarations exactly once. Preserve catalog/tier eligibility, fixed public preview and legacy callers. Strict opt-in behavior does not repair unrelated callers automatically.
3. Run existing suites and staged failures for real filter/auth/catalog hooks, pre-limit eligibility, correct failed-versus-empty state, no denial widening, coalescing and source-generation changes. Verify deployed SQLite JSON support for the R9 core proposal.
4. After release gates, prove one permitted source through the actual Brain/viewer with source/body identity, locator, allowed/denied/no-match/quota and relevant bilingual behavior. Two originals are necessary for independent reconstruction, not every attributed single-source answer.
5. Complete company-association propagation/server retrieval and correction/removal under existing identity owners. A populated ticker field or successful local fallback is not completion. Keep literal institutional text separate from generated annotations.

Stop the affected lane on writer collision, missing source/use rights, whole-source incompatibility, runtime admission failure or effect uncertainty. Do not bypass a release hold, change another worker's branch, weaken tests or create a parallel service. No authorized original-source customer journey was established here.

## 7. Incumbent and platform facts

Bounded comment reads after R8 returned only our existing advisories: #7079/comment5694391685 and #7045/comment5694395228. No later response or interface acceptance was established in those reads; this is not a census of Slack/provider sessions. No new worker or watcher was created from silence.

The full client download was not obtained: public-source sandbox read failed DNS and web read returned a cache miss. Connector range reads succeeded. Earlier native blocked operations and Chromium ERR_BLOCKED_BY_ADMINISTRATOR were not retried or routed around. No native host tool was invoked.

No subscription, MarketDesk acquisition, vendor communication, model/provider call, source admission, runtime edit, CI launch, merge or deployment occurred. Original-source, company-association, commercial-use and production proof gates remain open. More test cases do not establish incremental account value; three accounts remains a planning hypothesis.

## Exact continuation

Consume the existing owners' actual writer/interface ruling and adopt the reproducible R9+R10 candidate against complete source, then prove the real customer path. Do not restart the earlier diagnosis or describe these selected tests as live intelligence. The overall institutional-analysis vision remains intact; this bounded work removes a concrete consumer blocker and repairs cross-session recoverability.

Sources: component_candidates_r9.md and verification_r9.json at e62f39677466b0c342b750357b0e3aa10e13a708; site/research_vault_app.js at e729d0fd9d48868b49a1911d4098c689b3d373bd; PR7182; existing advisories5694391685/5694395228. No institutional originals, raw research catalog, credentials or private portfolios are included.
