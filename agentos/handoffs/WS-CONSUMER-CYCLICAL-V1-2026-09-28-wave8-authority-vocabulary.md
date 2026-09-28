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
  - claim: the same two defects exist in the Finance / Mining / Industrials / Healthcare guards
    what_would_verify: >
      grep -rn "_RE.fullmatch" engine/ for the dead-matcher shape, and probe each sibling
      guard with 30 category-representative keys as done here. The source comment reads
      "mirrors the finance idiom", which is why the lead exists. NOT RUN -- an unrun
      sibling probe is a lead, never a null.
unresolved:
  - >
    Whether the two defects repaired here also exist in the Finance / Mining /
    Industrials / Healthcare / Energy authority guards. The comment at the Consumer
    site reads "mirrors the finance idiom", so the shape is EXPECTED there -- but
    expectation is not measurement and this was not probed. Cheapest discriminator:
    `grep -rn "_RE.fullmatch" engine/` for the dead-matcher shape, then probe each
    guard with 30 category-representative keys as done here. A census question, not a
    V1 widening; until it is run it is a lead, never a null.
next_actions:
  - Merge this PR, then run the production proof from main's re-extracted bytes.
  - Report the wave on carrier #7804 as waves 5-7 were reported. ACCEPTANCE stays Sol's.
  - Optional wave 9 -- run the sibling probe above. It is a census, not a V1 widening.
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
