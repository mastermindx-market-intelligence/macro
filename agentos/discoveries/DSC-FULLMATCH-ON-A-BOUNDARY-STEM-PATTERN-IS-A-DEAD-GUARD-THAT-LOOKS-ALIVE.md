---
key: FULLMATCH-ON-A-BOUNDARY-STEM-PATTERN-IS-A-DEAD-GUARD-THAT-LOOKS-ALIVE
claim: >
  A pattern of the shape `(^|_)(stem1|stem2|...)(_|$)` -- the standard idiom for "this
  stem appears as a whole word inside an underscored identifier" -- matches NOTHING
  compound when applied with `re.fullmatch`, because `fullmatch` requires the pattern to
  consume the entire string and the three groups can only span `stem`, `stem_` or
  `_stem`. Measured on Consumer Cyclical V1
  (`engine/sector_intelligence/consumer_cyclical_projection.py`, the
  `_FORBIDDEN_COMPOUND_KEY_RE.fullmatch(k)` call): `composite_score`, `analyst_rank`,
  `rank_percentile`, `conviction_score` and `signal_strength` ALL passed the one
  construct in the module named and commented for catching compound authority keys. The
  bug survives review because a BARE stem does fullmatch -- `rank` returns a match -- so
  any spot check with a single word confirms the guard "works". Every one of those bare
  hits was already covered by the sibling exact-match frozenset, so the pattern's true
  marginal contribution was zero.
falsifier: >
  Run `python3 -m pytest tests/test_consumer_cyclical_projection.py -k compound -q`.
  Change `re.search` back to `re.fullmatch` at the guard's call site and
  `test_the_compound_authority_pattern_actually_catches_compound_keys` must go red. To
  reproduce the original measurement directly:
  `python3 -c "import re; p=re.compile(r'(^|_)(rank|score)(_|$)'); print(bool(p.fullmatch('composite_score')), bool(p.search('composite_score')))"`
  prints `False True`.
so_what: >
  (1) `fullmatch` and `search` are not interchangeable for boundary-anchored stem
  patterns; the pattern's own `(^|_)`/`(_|$)` groups ALREADY encode the anchoring, so
  pairing them with `fullmatch` double-anchors and kills the match. (2) A dead guard whose
  only hits duplicate a sibling guard is indistinguishable from a live one in every
  single-word test -- probe a regex blocklist with COMPOUND members, never bare stems.
  (3) Compute a guard's MARGINAL contribution: if every key it catches is already caught
  elsewhere, it is contributing nothing, and that ratio is a cheap standing check.
  (4) This was found by a SURVIVING mutation, not by reading the code: a test asserting
  that ordinary names like `sample_size` stay unrefused survived adding `size|weight` to
  the pattern, which is impossible if the pattern is live. The surviving mutation
  indicted the test; chasing why indicted the module.
kind: landmine
verified_at: 2026-09-27
verified_by: claude-opus-5 (CC-V1 wave 8) — engine/sector_intelligence/consumer_cyclical_projection.py:1393 and tests/test_consumer_cyclical_projection.py:1880
scope: >
  Verified on the Consumer Cyclical guard. CORRECTED 2026-09-28 (wave 9): this field
  previously said the same call "may exist in the Finance / Mining / Industrials /
  Healthcare verticals -- NOT checked". The probe HAS now been run and that framing was
  wrong twice over. (a) `engine/sector_intelligence/` holds only TWO projection modules,
  consumer_cyclical and finance -- the other three have no module there; the list came
  from the program roster, not a census. (b) The suggested grep is the wrong
  discriminator: `grep -rn "_RE.fullmatch" engine/` returns 475 hits, nearly all CORRECT
  format validators (sha256, dates, contract ids) where fullmatch is exactly right. The
  shape is a BOUNDARY-STEM pattern under fullmatch, not fullmatch as such. The one real
  sibling does NOT have this defect -- finance_projection.py has no fullmatch call at
  all; it has the adjacent one in DSC:A-GUARD-NAMED-IN-THE-DOCSTRING-CAN-HAVE-ZERO-CALL-SITES.
confidence: verified
---

Related: [[DSC-A-BLOCKLIST-ENUMERATES-THE-RULES-NOUNS-NOT-THE-VIOLATIONS-VOCABULARY]] --
found in the same guard, in the same hour, by different means. That one is a content
defect (the list held the wrong words); this one is a mechanism defect (the matcher could
not fire). A guard can be wrong in both ways at once, and fixing either alone still
leaves a guard that does not do what its name says.
