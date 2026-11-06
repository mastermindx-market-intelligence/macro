---
key: A-REQUIRED-ENUM-FIELD-CAN-HAVE-ONE-PRODUCIBLE-VALUE-AND-ZERO-READERS
claim: >
  Consumer Cyclical v1 declares `degraded_dependency.state` as a REQUIRED
  string whose enum admits three values (available / partial / unavailable),
  but the producer can emit exactly one. `_degraded` carries
  `state: str = "unavailable"` as a default and all seven call sites omit the
  argument, so `unavailable` is the only value any consumer can ever observe;
  `available`, on an entry inside a list OF degraded dependencies, would
  contradict the list it sits in, and `partial` is simply unreachable. The
  field also has zero readers -- no non-test file outside the producing module
  names `degraded_dependencies` at all. The granularity a consumer actually
  needs lives in the sibling `reason` field, which is measurably varied: five
  distinct reasons across two independent degradation branches. Note the
  vocabulary is NOT an echo of the top-level `availability` enum, which is a
  different, binary set (ready / unavailable). Censused across ALL TWELVE enums
  in the contract, `state` is the ONLY one a module-authored value cannot fully
  exercise: seven are fully exercised, and the four others that look narrow
  (`fact.basis`, `fact.role`, `fact.perimeter`, `source_record.retention_state`)
  are CALLER-authored passthroughs whose enums correctly constrain input, not
  output. The discriminator is the wave-7 rule -- who WRITES the value.
falsifier: >
  `grep -n '_degraded(' engine/sector_intelligence/consumer_cyclical_projection.py
  | grep -v 'def _degraded' | grep -c ', *"[a-z_]*" *, *"'` must print 0 -- no call
  site passes a state. If it ever prints more, a second state became producible and
  this record is void. Positive control that the grep reaches the right symbol at
  all: `grep -c '_degraded(' <same file>` prints 8 (one definition plus seven call
  sites). Reader count: `grep -rl 'degraded_dependencies' --include='*.py'
  --include='*.js' --include='*.j2' . | grep -v '^tests/'` must name only the
  producing module. Beware -- that `grep -rl` emits paths with NO `./` prefix, so a
  `^./tests/` filter silently excludes nothing and the census reads as if consumers
  existed; this bit twice before it was noticed.
so_what: >
  A contract that permits more than its producer emits is LOOSE, not FALSE. The
  document never claims anything untrue, so this is materially weaker than a guard
  that claims to refuse what it does not -- do NOT escalate it as a vulnerability,
  and do not narrow a published v1 enum over it on aesthetics alone. What it does
  change is consumer code: a future session wiring CC-V1-ENTITLED would read the
  three-value enum and write a three-way branch, two arms of which are dead and one
  of which is self-contradictory. Branch on `reason`, treat `state` as a constant.
  Generally: an enum's WIDTH is a statement about what the contract tolerates, never
  evidence of what the producer varies -- census the call sites before believing it.
  And when censusing, split the enums by AUTHOR first: a caller-authored enum that
  the module never writes is not loose at all, it is an input constraint doing its
  job. Skipping that split produced four false positives out of five flags here.
kind: landmine
verified_at: 2026-09-28
verified_by: claude-opus-5 (CC-V1 wave 10) — engine/sector_intelligence/consumer_cyclical_projection.py:1183 and tests/test_consumer_cyclical_projection.py:1911
scope: >
  Measured on Consumer Cyclical v1 only. The zero-reader half is a property of V1
  not yet being wired to a page consumer (CC-V1-ENTITLED is unstarted, five owner
  heads OPEN DRAFT) and will go stale the moment that lane lands -- re-run the
  reader census rather than trusting this line then. Whether sibling sector
  projection modules carry the same shape is NOT measured here and is not implied;
  `finance_projection.py` is seat 938d17d6's custody and was not touched.
confidence: verified
---

The pin that makes this visible is
`tests/test_consumer_cyclical_projection.py:1911`. It drives two independent
degradation branches, asserts each mutation actually changed the case, and
requires more than one distinct `reason` before asserting the state set --
without that guard a stale fact-key filter makes every assertion pass on an
empty list.
