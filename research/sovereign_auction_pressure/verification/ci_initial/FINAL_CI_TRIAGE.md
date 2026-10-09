# Final CI triage — sovereign auction first vertical

**CI is not fully green at the supplied heads.** The Macro failure is an inactive branch-specific authority context. The two Terminal failures are Vercel deployment rate limits. Mastermind's CodeQL check reports six security annotations in owned test, evidence, and diagnostic-harness material, alongside an incomplete Rust configuration warning. That check remains a substantive review gate; it cannot be characterized as only an external service failure.

This is a bounded read-only audit. No source edits, CI reruns, dispatches, scanner dismissals, settings changes, paid upgrades, or deployment actions were performed.

## Exact source heads and observation times

| Repository / PR | Supplied source head |
|---|---|
| [Macro #8657](https://github.com/mastermindx-market-intelligence/macro/pull/8657) | `9ea66297a31688123ae62845c655a74db03fa9c1` |
| [Mastermind #1284](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1284) | `42476573407fcb882c65a9388f98ed038801fc50` |
| [Terminal #857](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/857) | `9292c7ca1e19e07ee70514b9a3cfb598ba5dd5b9` |

Every returned check in each captured commit collection has the corresponding supplied head. Terminal's returned status payload also binds to the supplied head. These observations do not establish the state of later commits.

| Snapshot | Retrieval completed UTC | Source |
|---|---|---|
| macro_commit_checks | 2026-10-08T23:54:21.069Z | [Exact endpoint](https://api.github.com/repos/mastermindx-market-intelligence/macro/commits/9ea66297a31688123ae62845c655a74db03fa9c1/check-runs) |
| mastermind_commit_checks | 2026-10-08T23:54:21.072Z | [Exact endpoint](https://api.github.com/repos/mastermindx-market-intelligence/Mastermind/commits/42476573407fcb882c65a9388f98ed038801fc50/check-runs) |
| terminal_commit_status | 2026-10-08T23:54:10.375Z | [Exact endpoint](https://api.github.com/repos/mastermindx-market-intelligence/mastermind-terminal/commits/9292c7ca1e19e07ee70514b9a3cfb598ba5dd5b9/status) |

At the snapshot, Macro reported **7 successful, 1 failed, 4 skipped, and 13 in-progress** checks. Mastermind reported **2 successful, 1 failed, and 3 in-progress** checks. The audit did not poll the running jobs or claim their eventual outcomes.

## 1. Macro — inactive authority context

[Failed check 113596781513](https://github.com/mastermindx-market-intelligence/macro/runs/113596781513), `ci-authority/codex/merge-queue-pilot`, completed at **2026-10-08T23:44:41Z** with title **CI authority context rejected**.

Its emitted JSON states:

```json
{
  "head_sha": "9ea66297a31688123ae62845c655a74db03fa9c1",
  "base_ref": "main",
  "allowed": true,
  "reason": "same_repo_admin_authority_change",
  "check_context": "ci-authority/codex/merge-queue-pilot",
  "context_base_ref": "codex/merge-queue-pilot",
  "context_active": false,
  "context_allowed": false,
  "context_reason": "inactive_base_context"
}
```

The same-head active [`ci-authority/main` check 113596783883](https://github.com/mastermindx-market-intelligence/macro/runs/113596783883) **succeeded**, with `context_active=true` and `context_allowed=true`. Its output recorded three authority-sensitive paths: `.github/workflows/daily.yml`, `scripts/build_feeds.py`, and `scripts/capture_treasury_auction_observations.py`.

**Classification:** the reported failure is the inactive `codex/merge-queue-pilot` authority context on a PR targeting `main`. It does not report a code or test failure, and it is not evidence that the active main authority check rejected the source change. The failed check has **zero annotations**.

This audit does not infer how required-check rules or the eventual merge queue treat that inactive context. It does not change those rules or claim merge clearance. The existing CI/merge owner retains that determination.

## 2. Mastermind — CodeQL review required

[CodeQL check 113599048562](https://github.com/mastermindx-market-intelligence/Mastermind/runs/113599048562) completed at **2026-10-08T23:52:25Z** with title **1 configuration not found**. Its summary names a default `/language:rust` configuration present on `refs/heads/master` but absent from the check's observed configuration set.

The summary also reports **5 high and 1 medium security alerts**. It cautions that large changes can surface alerts not introduced by the PR. Three analyzer/test jobs were still running in the snapshot, including Rust and Python, so this report cannot assume the configuration warning is final. More importantly, later analyzer completion cannot be assumed to clear the six already-emitted source annotations.

The six annotations were read once at **2026-10-08T23:54:40.653144Z** from the exact check's advertised annotations endpoint.

| # | Source at supplied head | Location | Annotation level | Emitted finding |
|---|---|---|---|---|
| 1 | [research/sovereign_auction_context/presentation_final/preimages/test_sovereign_auction_renderer.cjs](https://github.com/mastermindx-market-intelligence/Mastermind/blob/42476573407fcb882c65a9388f98ed038801fc50/research/sovereign_auction_context/presentation_final/preimages/test_sovereign_auction_renderer.cjs) | 8:35 | failure | Bad HTML filtering regexp: This regular expression does not match upper case <SCRIPT> tags. |
| 2 | [tests/test_sovereign_auction_renderer.cjs](https://github.com/mastermindx-market-intelligence/Mastermind/blob/42476573407fcb882c65a9388f98ed038801fc50/tests/test_sovereign_auction_renderer.cjs) | 8:35 | failure | Bad HTML filtering regexp: This regular expression does not match upper case <SCRIPT> tags. |
| 3 | [research/sovereign_auction_context/presentation_final/preimages/market_view.html](https://github.com/mastermindx-market-intelligence/Mastermind/blob/42476573407fcb882c65a9388f98ed038801fc50/research/sovereign_auction_context/presentation_final/preimages/market_view.html) | 361:39 | warning | Incomplete HTML attribute sanitization: Cross-site scripting vulnerability as the output of [this final HTML sanitizer step](1) may contain double quotes when it reaches this attribute definition. |
| 4 | [research/sovereign_auction_context/verification/mastermind_loopback_harness.py](https://github.com/mastermindx-market-intelligence/Mastermind/blob/42476573407fcb882c65a9388f98ed038801fc50/research/sovereign_auction_context/verification/mastermind_loopback_harness.py) | 254:21 | failure | Uncontrolled data used in path expression: This path depends on a [user-provided value](1). |
| 5 | [research/sovereign_auction_context/verification/mastermind_loopback_harness.py](https://github.com/mastermindx-market-intelligence/Mastermind/blob/42476573407fcb882c65a9388f98ed038801fc50/research/sovereign_auction_context/verification/mastermind_loopback_harness.py) | 255:60 | failure | Uncontrolled data used in path expression: This path depends on a [user-provided value](1). |
| 6 | [research/sovereign_auction_context/verification/mastermind_loopback_harness.py](https://github.com/mastermindx-market-intelligence/Mastermind/blob/42476573407fcb882c65a9388f98ed038801fc50/research/sovereign_auction_context/verification/mastermind_loopback_harness.py) | 257:33 | failure | Uncontrolled data used in path expression: This path depends on a [user-provided value](1). |

The CodeQL summary supplies the aggregate security severity counts. The annotation API separately supplies `failure` or `warning`; this receipt preserves both without silently equating these fields.

### What exact source inspection establishes

**The two regexp reports concern renderer test extraction.** The live test reads the owned `app/static/market_view.html` file, calls `page.matchAll(/<script>([\\s\\S]*?)<\\/script>/g)`, selects the script containing `renderAuctions`, and evaluates a bounded prefix in its test VM. It is not a production HTML sanitizer. The same pattern exists in the archived test preimage. The uppercase-tag finding is relevant to extraction robustness; the annotations do not establish a production XSS path through this test.

**The HTML attribute report concerns an archived preimage.** At the annotated line, the archived `statusPill` constructs a CSS class attribute using `esc(s)`. The six annotations do not identify the current `app/static/market_view.html` path. That absence is not a blanket security assessment of the live page. The old preimage must retain its original bytes and hash if it remains part of the audit evidence.

**The three path reports concern a diagnostic loopback server with existing containment.** The annotated function computes a resolved static root, resolves the candidate, and rejects the request unless all of the following hold:

- The candidate is relative to the resolved static root.
- It is a real file.
- Its extension belongs to the explicit static-asset suffix set.

The server binds `127.0.0.1` on an ephemeral port. These controls appear in the exact inspected source before `FileResponse(path)`. The CodeQL annotations identify user-derived path expressions, but do not demonstrate a traversal bypass of the guard. No exploit or bypass test was attempted.

This source evidence is enough to prevent labeling all six alerts as proven exploitable production vulnerabilities. It is not grounds to silently dismiss or ignore them.

### Bounded owner remedies, not executed by this audit

The owner can make the renderer test extraction robust to case, verify that it still executes the actual owned renderer, and rerun the focused renderer test through the normal workflow. The diagnostic server can use an enumerated static-asset lookup constructed from its trusted root, eliminating request-derived filesystem path construction while preserving its loopback and extension restrictions.

Historical preimages should remain byte-identical. If their intended role is inert evidence, explicitly non-executable snapshot filenames with updated manifest references can express that role without editing historical bytes. Any such packaging change should be documented transparently and preserve the original hashes and findings. It must not become a blanket CodeQL exclusion or an unreviewed assertion that the finding never existed.

Any remaining finding belongs with the existing security/CI owner and exact-head verification process. This task did not perform a dismissal, add a scanner exemption, or sweep unrelated security code.

## 3. Terminal — external deployment rate limit

At `9292c7ca1e19e07ee70514b9a3cfb598ba5dd5b9`, both status contexts failed at **2026-10-08T23:51:52Z**:

| Context | State | Exact description |
|---|---|---|
| `Vercel – mastermind-terminal` | failure | Deployment rate limited — retry in 24 hours. |
| `Vercel – macro-eiz4` | failure | Deployment rate limited — retry in 24 hours. |

Their returned target URL points to Vercel's `build-rate-limit` upgrade route. That target was not visited or acted upon.

**Classification:** external deployment/build-rate policy. These status records do not report a compiler failure or test assertion. They also do not prove that a preview deployment succeeded. No paid upgrade, retry, new preview, or deployment was authorized or performed by this audit.

## Source receipt hashes

Source files were read from the exact Mastermind commit using local Git objects, without fetching or checking out another tree.

| Source | Bytes | SHA-256 |
|---|---:|---|
| `tests/test_sovereign_auction_renderer.cjs` | 5870 | `864008961197abac4eb7b1d37e14b86db8f9bda52913052e63e8542374fc82cf` |
| `research/sovereign_auction_context/presentation_final/preimages/test_sovereign_auction_renderer.cjs` | 4589 | `d2ef60d56f7b5301db79c667f529e38fd7fcfd7bad69d2213b3b14099635b97d` |
| `research/sovereign_auction_context/presentation_final/preimages/market_view.html` | 31238 | `b8d84a7313bdd7c9f4bbcc3ddfeadaaeddd85b9976ca143a64acaf5146c8a043` |
| `research/sovereign_auction_context/verification/mastermind_loopback_harness.py` | 16406 | `ac06f0f9b62c0639a140164cf0e441ef2a086a92635e0d9891c50a2f853d1f89` |

## Retrieval scope and remaining truth

The GitHub connector rejected two direct top-level check-run URL reads. Supported commit check-run collections returned the exact output bodies for both requested checks. The advertised Mastermind annotations endpoint was then read once with the existing read-only `gh api` capability through Studio; normal configured authentication was used without reading or emitting credential values. No login, quota loop, or endpoint probing followed.

The saved JSON files contain the exact API payloads, six annotations, source excerpts, source hashes, and observation times. The triage JSON records the classification separately from the evidence. The conclusions apply only to the supplied heads and captured check state.

The parent-reported local tests and browser checks are separate execution evidence and were not rerun here. They do not substitute for the unresolved CodeQL gate or the still-running CI checks. Draft/HOLD remains appropriate until the responsible owners complete the applicable checks and publication decisions.

