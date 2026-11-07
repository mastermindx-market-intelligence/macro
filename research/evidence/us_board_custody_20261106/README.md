# US board custody repair — 6 November 2026

PR: https://github.com/mastermindx-market-intelligence/Macro/pull/10432
Original branch: `seat/us-board-rotation-landing-job`
Original published head: `786b247bfcee4c0cb39ce12ae93d5dd78666097d`

## Why this repair is needed

The existing retirement decision treated a changed filename or a newly held filename as proof that its original held content survived. Real local bare-Git fixtures demonstrated that different replacement rows could be published or re-held while the only custody ref for the earlier rows was deleted. An unproved predecessor label could also suppress recovery; a changed non-JSONL projection did not preserve the original value.

The first five regressions produced four failures and one passing partial-coverage control. After the initial correction, focused custody checks passed. A bounded source review then identified retiring destinations, topology-read errors, and delete-result reconciliation as additional concrete risks. Eleven new cases produced nine failures and two passing controls before their narrow correction. The final custody run passes all61 cases. The failed-before evidence is retained without changing its result.

## Preservation contract

The existing held/recovered journals now bind each ref and path to its full immutable custody commit. Recovery verifies that fetched identity matches discovery and proves every original manifest entry in an eligible successor. JSONL content must remain a byte prefix, preserving order and duplicates; other formats require exact bytes. The bounded lineage graph must be acyclic and readable. A predecessor is recorded as recovered only after terminal recovery succeeds.

Settlement reconstructs proof from those immutable records in a fresh process. Published content is proved against a pinned local HEAD that is an ancestor of exact-read remote main. Surviving held destinations are content-verified and excluded if their refs belong to the complete retirement set. Identity conflicts across both journals fail closed. A filename or provenance edge alone does not establish preservation.

Custody deletion compares the original full commit through an exact ref lease. Every client result receives one bounded readback. Confirmed absence establishes retirement; an unchanged ref establishes non-retirement; a moved identity or unreadable/malformed readback remains unresolved. There is no deletion retry or repinning. Recovery may continue past a confirmed unchanged cleanup ref only when its original bytes are already published. All unresolved outcomes remain sticky. No new custody store, queue, publisher or control plane is introduced.

## Actual qualification

- Final source: **61 custody cases passed**,126 unrelated cases deselected; no failed or skipped selected case. Bash syntax, Python parse, unchanged-source verification and diff check passed.
- Unchanged source/workflow wiring: **129 tests passed**, with one pre-existing pytest fixture deprecation warning.
- Canonical curated input-closure case: **1 passed**.
- DAG conformance: **28 lanes passed**; the checker retains two documented inherited W5a drift notices.
- These are **191 distinct passing pytest cases** across the recorded phases, not a sum of repeated runs. Earlier40/50-case passes and the prior C3's46-case qualification remain historical and are not added again.

The final eleven test cases add no imports. The manifest, daily workflow, DAG, builder, committer and the four wiring/test inputs remain as recorded for their successful qualification. The last audit changes only custody helper behavior and regression cases; the receipt binds each phase to its actual input hashes.

## Source composition and delivery

Local qualification composes the original ten-path feature with accepted main `0787c6069951213b6500d7d419cb671a702881e8`. The publication uses accepted main `942c4be064fd80019db2c1349937b446e79124c6` as its full base. Eight existing scoped paths have byte-identical native Git blobs across those two main revisions; both new helpers are absent at both revisions. All other accepted-main paths are preserved. The capped300-file comparison was not used as absence proof.

The qualifier is `github-pr-sweep-2028-c4-pr10432-repair`; its branch must not be pushed. Publication must update the original PR branch once, nonforce and expected-head fenced, after native commit/tree/source readback.

Fresh hosted checks, individual merge admission, actual parent merge before dependent #10471, and the normal production custody/recovery path remain separate delivery conditions. These fixtures use local bare Git repositories and do not claim production execution. No formal GitHub approval, merge, deployment or live acceptance is established by this directory.
