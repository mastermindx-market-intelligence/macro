---
key: A-BLOCKLIST-ENUMERATES-THE-RULES-NOUNS-NOT-THE-VIOLATIONS-VOCABULARY
claim: >
  A blocklist written while reading the rule it enforces tends to contain the rule's own
  nouns rather than the words a violating field would actually be called, and the gap is
  invisible to review because every entry looks obviously correct. Measured on Consumer
  Cyclical V1 (`engine/sector_intelligence/consumer_cyclical_projection.py`
  `_FORBIDDEN_BARE_KEYS`): frozen-spec section 6 rule 10 forbids "ranking, entry, gating,
  sizing or origination" fields, and the guard's eight entries were `rank, score, entry,
  gate, sizing, origination, attractiveness, composite` -- five of them the rule's own
  category labels. Probed with 30 keys drawn from those five categories, the guard
  refused 4. `sizing` was refused; `position_size`, `weight`, `allocation`, `notional`
  and `exposure` were not. `origination` was refused; `signal`, `recommendation` and
  `action` were not. The docstring meanwhile asserted the full five-category guarantee.
falsifier: >
  Run `python3 -m pytest tests/test_consumer_cyclical_projection.py -k authority -q`
  (4 tests). Revert `_FORBIDDEN_BARE_KEYS` to the original eight names and
  `test_the_authority_guard_refuses_implementation_vocabulary` must go red; if it stays
  green the widening is not load-bearing and this record is wrong. The original measurement
  reproduces by calling `_assert_no_forbidden_authority_keys({"facts": [{"position_size": 1}]})`
  against `engine/sector_intelligence/consumer_cyclical_projection.py:151` as of
  `origin/main` at `020beaafadb8`, which returns None instead of raising.
so_what: >
  (1) Generate blocklist candidates from the IMPLEMENTATION side -- what would a field
  that violates this actually be named -- never by transcribing the rule. (2) The
  category label is the one word a real violator will not use, because it names the
  prohibition rather than the thing. (3) Probe every blocklist with N representative
  members per declared category and report the ratio; "it contains the right words" is
  not a measurement. (4) A blocklist's docstring must state its coverage as measured, not
  as intended -- the false confidence, not the gap, is what ships. (5) Ask which gate is
  actually load-bearing before widening: here `additionalProperties:false` already
  refused all 26 leaks, so the widening is defense in depth, and saying so honestly is
  more useful than implying the blocklist was the wall.
kind: landmine
verified_at: 2026-09-27
verified_by: claude-opus-5 (CC-V1 wave 8) — engine/sector_intelligence/consumer_cyclical_projection.py:160 and tests/test_consumer_cyclical_projection.py:1799
scope: >
  Consumer Cyclical V1 read-model projection. The leaks were NOT reachable: the root and
  every composite `$defs` carry `additionalProperties:false`, so the shape gate refused
  all of them. Verified by injecting each key into a real emitted document -- `rank` was
  refused at the authority gate, `position_size`/`weight`/`recommendation` at the shape
  gate. Sibling check NOT yet run against the Finance / Mining / Industrials verticals,
  whose guards carry the comment "mirrors the finance idiom"; that comment is the reason
  to expect the same shape there, and it is an open lead, not a finding.
confidence: verified
---

Related: [[DSC-TWO-ENDS-OF-ONE-POINTER-VALIDATED-IN-ISOLATION-BOTH-PASS-WHILE-IT-DANGLES]]
-- same family, one level up. There the property was spelled in two schema locations and
only the join was unchecked. Here the property is enforced in two CODE locations and the
documented one is the weaker, so the danger is not a dangling relation but misplaced
confidence: a future change that unseals a definition drops the real protection while the
guard that appears to cover it still passes review.
