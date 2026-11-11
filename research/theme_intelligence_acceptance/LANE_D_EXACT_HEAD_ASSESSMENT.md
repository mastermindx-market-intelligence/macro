# Lane D Exact-Head Acceptance — Lane F

**Lane F operation:** `theme-intelligence-f-evaluation-and-independent-acceptance-20260919-sol-001`
**Lane D operation:** `theme-intelligence-d-entry-and-stock-routing-20260919-sol-001`
**Carrier:** Macro Draft/HOLD PR #7508
**Candidate head:** `4d6e047c34fc86b744aeaca09454470af126085d`
**Candidate tree:** `d414cba7ead0fc07a766a4287466d54e672a2d36`
**Latest main reviewed:** `05523caeeabdb124d910988349877285fd6fd2d1`
**Integration tree:** `91cbd63c11e669f76c1d4e5dce61f402d6995b14`
**Disposition:** **SEMANTIC PASS / BUILT_NOT_PROVEN**

## Why this is a fresh review

The prior Lane F review covered `0ce6bbf54b9c623891274e278a6ff581b602bfef`. Lane D later changed `engine/subsector_confluence.py` to publish a flat group `entry_context`, so semantic review reuse was invalid. This assessment reviews the new exact head rather than carrying forward the old PASS.

## Independent proof

- Exact-head owner suites: **59 passed**.
- Agent OS validation: **1,140 records, 0 errors, 51 inherited warnings**.
- `git diff --check`: PASS.
- Latest-main movement is path-disjoint across D source, tests and immediate consumers.
- Conflict-free current-main integration tree: `91cbd63c11e669f76c1d4e5dce61f402d6995b14`.
- Proof-only integrated owner suites: **59 passed**.
- Fences run `35506964924`: SUCCESS.
- Hosted CI `35506965096`: still running at the review observation.

The prior Agent OS carrier blocker is closed.

## Producer semantics

The new group projection is additive and descriptive. It preserves:

- entry qualification separately from confirmation;
- confirmation separately from regime/extension;
- the owner observation clock and group source reference;
- explicit context-only framing;
- `may_rank=false`, `may_gate=false`, `may_size=false`, `may_escalate=false`, and `may_trade=false`.

## Freshness boundary

A deliberate stale-observation probe calls the exact production projection with `as_of=2000-01-01` and an historical `entry_now` owner state. The producer returns `QUALIFIED_PENDING_CONFIRMATION` **together with observation clock 2000-01-01**.

Lane F does not classify that as a D producer defect: the object reports the historical observed entry state, preserves its old clock, and grants no current action authority. Freshness belongs in the package's separate health dimension rather than rewriting the historical entry observation.

This makes Lane A's clock/health repair a binding integration dependency. Lane A must consume D's owner observation clock and mark stale health before a historical qualified state can be presented as current. Until that shared-consumer repair is accepted, D's end-to-end convergence remains **NOT_PROVEN**.

## GitHub review surface

Lane F attempted to submit a formal GitHub approval, but GitHub rejected it because the connected identity is also PR #7508's author. No bypass was attempted. The semantic result is recorded in PR conversation comment `5749597019` and this independent Lane F receipt.

## Acceptance boundary

Lane D source semantics are **PASS** for this bounded producer contract. The carrier remains Draft/HOLD while hosted CI is unfinished and Lane A's shared freshness/health gate is open.

No merge, deployment, browser proof, entry permission, ranking, sizing, trade authority, or parent Theme Intelligence acceptance is claimed.
