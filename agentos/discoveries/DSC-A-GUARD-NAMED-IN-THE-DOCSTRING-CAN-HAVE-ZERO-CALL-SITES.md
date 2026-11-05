---
key: A-GUARD-NAMED-IN-THE-DOCSTRING-CAN-HAVE-ZERO-CALL-SITES
claim: >
  A module can define a named guard constant, advertise it in its own module docstring,
  and never call it. Measured 2026-09-28 on
  `engine/sector_intelligence/finance_projection.py`: line 296 defines
  `_FORBIDDEN_KEY_RE = re.compile(r"(^|_)(score|rank|attractiveness|composite)(_|$)")`
  and line 15 of the module docstring advertises the protection ("emits a forbidden
  authority / score / rank / attractiveness / composite field") -- but the constant has
  ZERO call sites. Repo-wide the name returns 7 hits: this definition, plus SIX in two
  unrelated modules (`lib/project_runtime_state.py:43,210,667,1366` and
  `tests/test_market_ontology_exposure_map.py:399,426`) that each define their OWN local
  copy and DO use it. Subtract the definition line and the finance guard is never read.
  This is the sibling shape to DSC:FULLMATCH-ON-A-BOUNDARY-STEM-PATTERN-IS-A-DEAD-GUARD-THAT-LOOKS-ALIVE
  one notch deader: Consumer had a live call with the wrong method; Finance has no call.
falsifier: >
  `grep -rn '_FORBIDDEN_KEY_RE' --include='*.py' . | grep -c 'finance_projection'` must
  print 1 -- the definition and nothing else. If a call site is ever added the count
  rises and this record is void. Positive control that the grep works at all: the same
  command against `lib/project_runtime_state.py` prints 4 (one definition, three uses).
so_what: >
  (1) A guard's NAME in a docstring is a claim about behaviour, and like any claim it
  needs a call site before it is believed. The cheapest possible check -- grep the
  constant repo-wide and subtract the definition line -- is cheaper than READING the
  guard, and strictly more informative, yet review habitually does the expensive one.
  (2) Two modules in one package now show the same failure in two forms (wrong method,
  no call). That is a pattern, not a coincidence: a guard constant is written, the real
  enforcement lands elsewhere (the contract seal), and nobody re-reads the constant.
  (3) When a guard IS dead, find what is actually holding the property before calling it
  a vulnerability. Finance's protection is real -- a 43/43-sealed contract -- but it runs
  in the TEST (`validate_contract`, tests/test_finance_intelligence_contract.py:95), not
  at emit; Consumer asserts shape at emit and is stronger. Neither the dead constant nor
  the seal is what the docstring describes.
  (4) Generalized method note: a ROSTER IS NOT A CENSUS. The lead that produced this
  finding named five sibling guards because five sibling seats exist; three of those
  modules do not exist. Enumerate from the filesystem, never from the org chart.
kind: landmine
verified_at: 2026-09-28
verified_by: claude-opus-5 (CC-V1 wave 9) — engine/sector_intelligence/finance_projection.py:296 and tests/test_finance_intelligence_contract.py:95
scope: >
  Verified by static reference census, NOT by execution. What is PROVEN: the constant has
  no call site, the module imports only stdlib (hashlib, json, re, dataclasses, datetime,
  typing) so it cannot validate at emit, and the contract is 43/43 definition
  object-nodes `additionalProperties: false` (if/then subschemas excluded -- sealing
  those would be a bug). What is NOT PROVEN and is explicitly left open: whether the dead
  guard is REACHABLE. That requires confirming `validate_contract` at
  tests/test_finance_intelligence_contract.py:95 receives the real composer output on
  every emit path and mutation-probing it. Until then this is FALSE CONFIDENCE, not a
  demonstrated leak. `finance_projection.py` is seat 938d17d6's custody: this record is
  knowledge routed to that seat, and this seat did not edit the module.
confidence: verified
superseded_by: "DSC:A-LEAK-TEST-OVER-A-CLEAN-FIXTURE-CANNOT-FAIL-PLANT-THE-OWNER-KEYS"
---

## How it was found

Not by reading `finance_projection.py`. The wave-8 handoff filed a lead to probe five
sibling authority guards; running it found that three of the five modules do not exist,
and the census that replaced the lead — grep the constant, subtract the definition line —
answered in one command what reading the module would not have made obvious at all.

## The cheap standing check

```
grep -rn '<GUARD_CONST>' --include='*.py' . | grep -c '<owning_module>'
```

One hit means the guard is never read. Always pair it with the same command against a
module known to use the constant, so a zero can be distinguished from a broken pattern.
