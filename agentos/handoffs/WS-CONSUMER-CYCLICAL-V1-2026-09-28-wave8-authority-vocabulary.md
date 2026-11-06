---
workstream: "WS:CONSUMER-CYCLICAL-V1"
session: claude/consumer-cyclical-wave8-authority-vocabulary
model: opus
ended_because: complete
mission: >
  Continue the V1 correctness lane after wave 7 (#8106) merged and proved. Sweep the last
  unexamined surface named by the wave-6/7 thesis "the module states things it does not
  check": the authority/scoring guard that enforces frozen-spec section 6 rule 10.
state_before: >
  #8106 merged at squash 020beaafadb8 and proven from main's re-extracted bytes (114
  passed, both cases oracle-exact, envelope sweep 17 REFUSED / 4 MINTED). The three
  surfaces wave 6 named were all swept: source_records (predicted defect refuted, real
  defect found adjacent), explanation (null), availability (null). The authority guard
  had never been probed against its own docstring.
state_after: >
  Two defects found in _assert_no_forbidden_authority_keys and both repaired, plus four
  tests, all four mutation-probed. The guard now refuses 28 of 30 category-representative
  keys (was 4) and its compound pattern actually fires (it previously could not). The
  docstring now names additionalProperties:false as the primary mechanism, which it
  always was. NEITHER defect was reachable -- the schema seal refused every leak -- so
  this is a false-confidence repair, not a vulnerability fix, and the records say so.
changed:
  - path: engine/sector_intelligence/consumer_cyclical_projection.py
    what: >
      _FORBIDDEN_BARE_KEYS widened from 8 policy nouns to 33 implementation-vocabulary
      names grouped by the five declared categories, with "action"/"call" deliberately
      excluded and the reason recorded inline. _FORBIDDEN_COMPOUND_KEY_RE call changed
      from re.fullmatch to re.search (it matched nothing compound under fullmatch) and
      given the sizing|entry|gate stems only a live pattern can reach. Guard docstring
      rewritten to state that the schema seal is the first line and this guard the second.
  - path: tests/test_consumer_cyclical_projection.py
    what: >
      Four tests added: implementation-vocabulary refusal; the seal (not the blocklist)
      refusing an unlisted key; a negative control that ordinary names like sample_size
      stay unrefused; and the compound pattern actually catching compound keys, each key
      first asserted absent from the bare set so a pass can only mean the pattern fired.
  - path: agentos/discoveries/DSC-A-BLOCKLIST-ENUMERATES-THE-RULES-NOUNS-NOT-THE-VIOLATIONS-VOCABULARY.md
    what: new landmine record, confidence verified, sibling probe left explicitly OPEN
  - path: agentos/discoveries/DSC-FULLMATCH-ON-A-BOUNDARY-STEM-PATTERN-IS-A-DEAD-GUARD-THAT-LOOKS-ALIVE.md
    what: new landmine record, confidence verified, generic Python idiom trap
verified:
  - claim: suite green on the repair, 118 passed
    command: python3 -m pytest tests/test_consumer_cyclical_projection.py tests/test_consumer_cyclical_intelligence_read_model_contract.py -q
  - claim: guard refuses 28 of 30 category-representative keys, was 4 of 30
    command: python3 -c "import sys;sys.path.insert(0,'.');from engine.sector_intelligence import consumer_cyclical_projection as M;ks='rank ranking score percentile tier grade conviction entry entry_price buy_price trigger_price timing gate gating eligible approved tradeable pass_fail size position_size weight allocation notional exposure signal recommendation action call thesis_direction originated_by'.split();print(sum(1 for k in ks if k.lower() in M._FORBIDDEN_BARE_KEYS or M._FORBIDDEN_COMPOUND_KEY_RE.search(k)),'of',len(ks))"
  - claim: no legal contract property name is refused by the widened guard
    command: python3 -c "import sys,json;sys.path.insert(0,'.');from engine.sector_intelligence import consumer_cyclical_projection as M;d=json.load(open('contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json'));n=set();w=lambda x:[n.update((x.get('properties') or {}).keys()),[w(v) for v in x.values() if isinstance(v,(dict,list))]] if isinstance(x,dict) else [w(v) for v in x] if isinstance(x,list) else None;w(d);print([k for k in n if M._FORBIDDEN_COMPOUND_KEY_RE.search(k) or k.lower() in M._FORBIDDEN_BARE_KEYS])"
  - claim: the compound pattern was dead under fullmatch and is live under search
    command: python3 -c "import re;p=re.compile(r'(^|_)(rank|score)(_|$)');print(bool(p.fullmatch('composite_score')),bool(p.search('composite_score')))"
  - claim: no regression -- both cases oracle-exact, envelope sweep unchanged 17 REFUSED / 4 MINTED
    command: python3 proof8078.py && python3 sweep3.py
  - claim: 4 of 4 mutations caught (blocklist reverted, $defs/fact unsealed, size|weight added to the live pattern, search reverted to fullmatch)
    command: python3 -m pytest tests/test_consumer_cyclical_projection.py -k "authority or compound or widening or seal" -q
unverified:
  - claim: >
      SUPERSEDED 2026-09-28 (wave 9). This entry previously read "the same two defects
      exist in the Finance / Mining / Industrials / Healthcare guards ... NOT RUN". It
      HAS now been run and the claim was WRONG AS FRAMED: three of those four guards do
      not exist -- `engine/sector_intelligence/` holds only consumer_cyclical and
      finance. What survives is narrower and unverified in a different direction:
      whether finance_projection.py's dead `_FORBIDDEN_KEY_RE` (zero call sites
      repo-wide, line 296) is REACHABLE past the sealed contract.
    what_would_verify: >
      Mutation-probe tests/test_finance_intelligence_contract.py:95 -- confirm
      validate_contract there receives the REAL composer output on every emit path, not
      only a fixture, then add an authority key to that output and confirm the 43/43
      seal refuses it. Until that runs, the dead guard is false confidence, NOT a
      demonstrated leak. OWNED BY SEAT 938d17d6 (finance_projection.py is its custody);
      this seat routed the finding as knowledge and must not edit that module.
unresolved:
  - >
    CORRECTION 2026-09-28 (wave 9, census RUN): the ORIGINAL LEAD below was REFUTED AT
    ITS PREMISE. It is corrected here, at source, rather than only in a newer file,
    because a reader arrives at THIS record and would otherwise be sent after it.
    `engine/sector_intelligence/` holds exactly TWO projection modules --
    consumer_cyclical_projection.py and finance_projection.py. Mining, Industrials,
    Healthcare and Energy have NO projection module in that package at all: that
    five-name list was written from the PROGRAM ROSTER (five sibling seats exist),
    never from a module census. A roster is not a census. Nor was the dead-matcher
    discriminator right as written -- `grep -rn "_RE.fullmatch" engine/` returns 475
    hits, nearly all correct format validators (sha256, dates, contract ids), so the
    shape is the boundary-stem PATTERN under fullmatch, not fullmatch itself.
    See DSC:A-GUARD-NAMED-IN-THE-DOCSTRING-CAN-HAVE-ZERO-CALL-SITES.
  - >
    STILL OPEN, and it is seat 938d17d6's, NOT this seat's: whether the one real
    sibling's dead guard is REACHABLE. finance_projection.py:296 defines
    `_FORBIDDEN_KEY_RE` with ZERO call sites repo-wide (7 hits total; the other 6 are
    local copies in lib/project_runtime_state.py and a test, each of which DOES use
    its own). Finance imports only stdlib, so it does not validate at emit either; its
    real protection is the sealed contract (43/43 definition object-nodes
    additionalProperties:false) enforced by validate_contract at
    tests/test_finance_intelligence_contract.py:95 -- at CI time, in the test, not at
    emit in the module. I did NOT verify that test exercises the real composer output
    on every path and did NOT mutation-probe it, so this is the same false-confidence
    family, not a demonstrated reachable leak. finance_projection.py is that seat's
    custody: routed as knowledge, never edited from here.
  - >
    ORIGINAL LEAD (refuted above; retained so the refutation has its subject): whether
    the two defects repaired here also exist in the Finance / Mining / Industrials /
    Healthcare / Energy authority guards, on the grounds that the Consumer comment
    reads "mirrors the finance idiom" so the shape is EXPECTED there. Expectation was
    not measurement -- and the measurement refuted the roster, not just the shape.
next_actions:
  - Merge this PR, then run the production proof from main's re-extracted bytes.
  - Report the wave on carrier #7804 as waves 5-7 were reported. ACCEPTANCE stays Sol's.
  - >
    DONE 2026-09-28 (wave 9) -- the sibling probe above was RUN. Result was a FINDING,
    not the null it was filed as, and it refuted the lead's own premise. Do not re-run
    it as specified; read the CORRECTION in `unresolved` first.
do_not_redo:
  - Do not re-sweep source_records, explanation, or availability. Waves 6-7 closed all three; source_records is fully jsonschema-validated, NOT a passthrough.
  - Do not "repair" the module toward frozen-spec section 4a's native_ref prose. It is STALE, marked at source in wave 7, and repairing toward it re-introduces the wave-7 defect.
  - Do not add "action" or "call" to the blocklist. Both were considered and excluded on reason; the seal already refuses them.
  - Do not add size or weight to the COMPOUND pattern. They are in the bare set on purpose; as stems they refuse sample_size and batch_size. A test pins this.
danger_areas:
  - The blocklist and the schema seal are two mechanisms for one property. Unsealing any $defs silently drops the seal's coverage; the new tests are what would notice.
  - re.fullmatch vs re.search on a (^|_)stem(_|$) pattern is invisible to any single-word spot check, because bare stems match under both.
---

## The one thing a cold reader should take

The guard was not weak in the way it looked weak. Its docstring claimed a five-category
guarantee; its blocklist held the five category LABELS; and the thing actually enforcing
the guarantee was `additionalProperties: false` in the contract, which the docstring never
mentioned. So the honest repair was not "make the blocklist stronger" -- it was "stop the
module from misrepresenting which of its two mechanisms is load-bearing", and then widen
the weaker one as genuine defense in depth.

The second defect was found by a mutation that SURVIVED. A test asserting ordinary names
like `sample_size` stay unrefused should have gone red when `size|weight` was added to the
compound pattern. It did not, which is only possible if the pattern never fires -- and it
never fired, because `fullmatch` cannot consume a compound name. The surviving mutation
indicted the test; chasing the reason indicted the module. That ordering is the reusable
part: a mutation that survives is evidence about the instrument before it is evidence
about the code.
