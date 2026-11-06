# R14: integrate the original clock and pivot candidate with adopted source readers

Same WS:LIVE-ENTRY-RADAR / Macro PR #8649 and original branch. This is an integration of existing implementations, not a new trading model or source-admission result. Original candidate 4d7bf67efeee17c2661a2ad0fa00f53e2f5e1448 joins main f4da7548b6ddfcc3e41794f1a040c184e9ddcdc0, including the v3 minute reader, adopted Data OS identity contracts, and merged actual-clock identity-file adapter #9199.

## Exact implementation preservation
The eight named source/test files for the phase1 clock and two pivot descriptors are blob-identical to the reviewed source. Identity and raw-v3 reader changes come from incoming main, not a replacement implementation. The only automatic text composition is the existing CI manifest; its prior dependency entries are preserved. No source endpoint, provider finalization, identity/basis refusal, authority flag, capture cadence or numerical trading threshold is changed.

## Actual verification
The first local merge could not find a common ancestor because this original R7 clone ended at d0beadc. The real ancestor 123eda091dfd0d83c4c303f7f138d4c8a2c7e128 was verified in the existing administrative object store. Deepening the original branch by ten commits recovered that exact ancestor; no unrelated-histories override was used. Normal history-preserving merge then succeeded without conflicts.

The first test invocation selected two new dependency suites that were tracked but not materialized in the old sparse checkout. It ran zero tests and exited4. Only those two exact paths were added to the sparse specification. The unchanged selected command then passed **565 ordinary tests plus113 subtests**, with zero failures/errors/skips. JUnit counts678 including those subtests; this is not678 newly authored tests. One warning concerned pytest cleanup of an unrelated earlier protected temporary directory, which this operation did not modify.

Tested index tree: 9dc962f00bf7cfd1dc000f9e3e6610a60b970d4f (before these two evidence documents). Exact XML SHA256148c3360d6015719f5befdb45f8937b891e8060cc79e5d0cbc3777ebede2cf20. Eight ordinary suites cover phase1, first-green, undercut descriptor/progress/edges, v3 minute observations, actual-clock identity-file reads and native Data OS identity. Source whitespace check relative to incoming main passed. The new merge head still needs its own hosted CI; old green runs are not substituted for it.

## Source acceptance is not market admission
Parent #8649's recorded Chairman review waiver6069276063 remains scoped to this mission. #9199 separately received an actual independent Fabric review and parent adjudication6183461333 before merge. No independent review of a newly invented strategy is claimed. Real identity publication/history is still missing, and price/action basis remains unqualified. Existing raw minute data is not assigned fictional historical arrival times. No production command, feed acquisition, collector, score, alert or trade was introduced by this integration. Explicit R9 VPS-conformance and R13 initial-generation-staging denials remain untouched.

Full private execution evidence remains under /Users/chriswong/agent-evidence/rs-pullback-r14-20261015-c1/. Source files and reproducible test command are in this repository; the XML hash identifies retained native execution, not a market outcome.
