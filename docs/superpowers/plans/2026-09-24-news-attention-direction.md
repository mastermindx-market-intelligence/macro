# News attention-direction repair — implementation and proof

Parent: Macro #7953. Operation: `news-attention-direction-repair-20260924-sol-001`.
Chairman approved end-to-end News/ticker intelligence delivery on 2026-09-24.
Protected Skillpack: `Mastermind@819abc8c23609cdded2b33f6e1bfc7854bd5c847`.

## Goal and boundary
A fall in article volume must not look like a burst in the actual News display ordering.
The legacy field `novelty_z` is qbus attention-volume deviation, NOT factual novelty.
Keep its schema and raw diagnostics, the existing weights and positive finite scale.
No trading scores, model activation, source acquisition, article rejection, template,
mobile controls, source identity, corpus, publication service or lifecycle changes.

## Implementation plan (executed directly; lower total overhead)
1. Extend existing `tests/test_news_rank_aging.py`, not a new CI registry: compare
   negative anomalies (-100, -3, -.1 and numeric string -3) with the zero-credit baseline;
   require neutral credit for NaN/infinities/booleans/invalid values and numeric overflow.
2. Freeze the positive scale: z=0/.75/1.5/3/9 -> 33.6/37.6/41.6/49.6/49.6 for quality=60
   at the injected clock. Preserve the input mapping unchanged.
3. Invoke real `scripts.build_news._enrich` with only the optional LLM boundary disabled:
   genuine burst -> higher-quality fact -> quiet subject. No mocked ranker.
4. Observe RED on pinned production source; then accept only positive finite float
   contributions in `engine/news_common.py`. Preserve the rest of rank_score byte-for-byte.
5. Run the complete existing test file, restore the original bad block as a mutation,
   require RED again, restore the candidate, and require a final clean GREEN run.

## Source and test evidence
Validation uses selected, Git-blob-verified GitHub source files at
`43d8dac58743e22f2acc802db9c436bc0e523e13`, not an occupied checkout. No .env,
provider credentials, data tree, global hooks, or source workspace was accessed.
Runtime: Python 3.9.6 on m1studio, installed pytest.

Command: `python3 -m pytest tests/test_news_rank_aging.py -q --tb=short -p no:cacheprovider`

- RED: **13 failed, 32 passed**, pytest exit 1. Includes the real build_news ordering path.
- GREEN: **45 passed**, pytest exit 0.
- Original-bug mutation restored: **13 failed, 32 passed**, pytest exit 1.
- Correct candidate restored: **45 passed**, pytest exit 0.
- Candidate news_common.py SHA-256:
  `0d67da7512881a8a2f380c2178f1efbc95b26ace5354f3dc6ae541ab6d5ba8bf`.

This is complete test-file verification in a selected-source snapshot, NOT the
repository-wide suite or its conftest/data guard, a full build, or production/browser proof.
Hosted required CI, independent review, merge and real-path acceptance remain owed.

## Review focus
A negative volume deviation remains a valid diagnostic but earns zero positive burst
credit. Missing/nonfinite observations must not become maximum credit. Positive finite
scores, quality fallback, raw inputs, and all other weights stay unchanged. The LLM-off
consumer regression must fail on the old function. Existing precomputed rank artifacts
must not be presented as re-ranked until their normal owning publication refresh occurs.

## Next product slice
Company Intelligence already owns guidance_item.v1 and source receipts. Reuse that owner
and its workspaces. Its documented AAPL example lacks a prior comparable; do not invent
one. #7575's vehicle-guidance work and #7591 mobile controls remain separate incumbent
carriers. The News upgrade is incomplete; this repair is a first deterministic-trust leaf.
