# Native K3-D V2 publication evidence — 2026-10-12 UTC

**BUILT_NOT_PROVEN / DRAFT-HOLD. No production admission or release.**

This continuation recovers `GMI_K3D_Native_Execution_20261011_v2.zip` and verifies
all 197 manifest-listed files. It reuses the accepted R015 library repair at
`d660bc12a9a5748e688fe74191f545aedfba4a6a`; do not apply that fix again.

## Executed evidence

The original complete compiler suite passed 108 cases. With the source-grain
regressions, the original compiler produced 115 passes and 63 expected failures;
the repaired compiler passed all 178. The original monolithic V2 candidate passed
489 cases (108 original + 70 identity + 311 V2), including all original software
fixtures and the two archived real-data abstentions. These earlier results are
retained in the original downloadable packet; they are not new market evidence.

For this publication the code was split into a sibling V2 native module and two
sibling test files, leaving every original test byte intact. A fresh combined
run on Python 3.13.5 executed the complete original suite plus both siblings:
**489 passed, 0 failures, 0 errors, 0 skipped in 4.63 seconds.**

```bash
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python -B -m pytest -q -p no:cacheprovider \
  tests/test_economic_propagation_hypothesis_contract.py \
  tests/test_economic_propagation_source_grain.py \
  tests/test_economic_propagation_v2.py
```

The nine V2 function bodies are AST-identical to the original tested candidate,
apart from its implementation-location/docstring clarification performed before
comparison. The V2 sentinel now explicitly patches the native v1 graph function.
All 26 original non-library files in the source-pinned test layout are byte-
identical, including all 20 frozen fixtures, fixture manifest, original test
file, native contracts and two archived abstentions. The v1 library is exactly
its already-published R015 blob. No fixture was regenerated in this continuation.

The V2 schema was whitespace-compacted after the run. Parsed JSON is exactly
identical; this is serialization-only, not a schema-semantic change.

Run XML: 83,113 bytes, SHA-256
`475892c30e6859cf9b7a547cf6a0d463005bd7dfe480f7c3f86f6bc351046b15`.
Run log: 580 bytes, SHA-256
`8881f6db256e21cd8256fc0bcbfc6dfd88b7a64f0c744d658767c875d764436a`.
Logs remain in the attached source/evidence package, not runtime `data/`.

## Exact source objects

| File | Git blob |
|---|---|
| Published v1 library, unchanged | `de7b6b1990d93e41a7e9e892bd7feade177c2700` |
| Original complete test file, unchanged | `c99536c34282565b50358ae8736f6798e8c0187b` |
| `lib/economic_propagation_v2.py` | `3c87e4d5c6635690edfa1157bb36316cc40082cf` |
| `tests/test_economic_propagation_source_grain.py` | `47d4baafe31651c69d74782122b602ec92328bb6` |
| `tests/test_economic_propagation_v2.py` | `73066adfb12da74de8c92219931131f84ddba618` |
| `contracts/economic_propagation/propagation_hypothesis.v2.schema.json` | `62147ebc4668c885a8c9168784ecaae70cde893d` |

All four newly staged GitHub source blobs matched their locally tested or
serialization-equivalent bytes before the original branch was advanced.

## Meaning and limits

V2 reconstructs generated narrative independently of a submitted hash. Rehashed
trading language, asserted numerical impacts and substituted review/falsifier
text refuse. The incumbent source identity, target, native owner, graph-layer,
rights and cutoff checks still run. V1 is neither overwritten nor silently
promoted. The combinations are proposed construction policy, not quantified
propagation, verified legal relationships or predictive validation.

This is the complete source-pinned native test layout, not all Macro repository
CI and not an authenticated production-user journey. No native source capture,
identity-owner approval, Data OS purpose grant or GMI Graph1 insertion occurred.

## Current gates and effects

The original GitHub coding request returned an environment-required response
(comment 6115286675), not START. This continuation's exact Session Bridge target
read returned `backend_unavailable: installed Session Bridge owner is unavailable`.
No worker was spawned, retried or duplicated. The earlier M2 action denial
remains unbypassed. Direct GitHub source actions are independently available.

Next: review the exact published source on #6514, reconcile the current shared
CI hunk, enroll both sibling tests under the one existing K3-D job, and complete
current-head CI and the normal release procedure. Current-main movement, review
and product proof are separate. The #8793 release and #8803 diagnostic remain
independent; accepted #8711 private capture/replay is DO_NOT_REDO.
