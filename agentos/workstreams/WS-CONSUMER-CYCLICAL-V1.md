---
key: CONSUMER-CYCLICAL-V1
title: "Consumer Cyclical V1 — PLNT economic-change vertical (Fable integration program)"
objective: >
  Take the accepted R15 Consumer economics design to a real source-bound,
  entitled, browser-visible PLNT economic-change experience. Done means an
  entitled user opens PLNT and sees a source-bound explanation of the selected
  reported revenue/advertising change with correct signs, scale and limitations,
  with anonymous users receiving no paid closure. V1-CORE (the deterministic
  composition) is the merged first wave; the entitled/browser legs stay frozen
  behind external owners.
status: blocked
program: earnings-intelligence
repos: [macro]
owner: fable-integration-principal
class: build
blast_radius: reversible
ambiguity: specified
owns_paths:
  - contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json
  - data/sector_intelligence/fixtures/consumer_cyclical_intelligence_read_model.v1.valid.json
  - engine/sector_intelligence/consumer_cyclical_projection.py
  - tests/test_consumer_cyclical_intelligence_read_model_contract.py
  - tests/test_consumer_cyclical_projection.py
  - research/consumer_cyclical/v1/**
decisions:
  - "DEC:CONSUMER-CYCLICAL-V1-CORE-EXTENDS-INCUMBENT-NOT-TRANSPORT"
  - "DEC:CONSUMER-CYCLICAL-REFUSES-FACTS-IT-CANNOT-PUBLISH"
discoveries:
  - "DSC:A-UNIVERSAL-FALLBACK-BRANCH-IS-INVISIBLE-TO-A-VALUE-ONLY-SUITE"
  - "DSC:THE-CASE-A-SUITE-USES-MOST-IS-THE-ONE-IT-NEVER-VALIDATES"
  - "DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE"
  - "DSC:A-DECLARED-BASIS-IS-A-LABEL-UNTIL-SOMETHING-READS-IT"
  - "DSC:AN-ENUMERATED-GUARD-IS-BLIND-OUTSIDE-ITS-ENUMERATION"
  - "DSC:A-MUTATION-THAT-DIES-UPSTREAM-NEVER-TESTS-THE-GATE-YOU-AIMED-AT"
  - "DSC:TWO-ENDS-OF-ONE-POINTER-VALIDATED-IN-ISOLATION-BOTH-PASS-WHILE-IT-DANGLES"
  - "DSC:A-BLOCKLIST-ENUMERATES-THE-RULES-NOUNS-NOT-THE-VIOLATIONS-VOCABULARY"
  - "DSC:FULLMATCH-ON-A-BOUNDARY-STEM-PATTERN-IS-A-DEAD-GUARD-THAT-LOOKS-ALIVE"
  - "DSC:A-GUARD-NAMED-IN-THE-DOCSTRING-CAN-HAVE-ZERO-CALL-SITES"
  - "DSC:A-REQUIRED-ENUM-FIELD-CAN-HAVE-ONE-PRODUCIBLE-VALUE-AND-ZERO-READERS"
waves:
  - id: CC-V1-CORE
    title: "V1-CORE deterministic composition"
    status: done
    next_action: >
      Merged as PR #7942 (squash 6e3e8987c5c6, 2026-09-24T13:07:49Z) and verified
      live from main: all six R6 7.1 golden values exact from native_admitted
      false facts, 0 schema errors, 61 tests green on the merged tree. That live
      verification then found the economic lead unreachable on every input (see
      landmines); repaired plus a same-class hardening pass on PR #7945, 65 tests.
  - id: CC-V1-ENVELOPE-INTEGRITY
    title: "Fact admission gate + document self-check"
    status: done
    next_action: >
      A coverage audit of the merged module (110/723 executable lines never
      executed under the full owned suite) escalated into the finding that the
      projection publishes documents violating the contract it authors, on
      ordinary inputs - most damningly a thousands separator in a financial
      figure. Repaired by refusing rather than repairing: unpublishable facts
      are withheld and declared through the existing degraded_dependencies
      vocabulary, and an end-of-projection self-check raises CaseShapeError
      rather than returning a contract-violating document. See
      DEC:CONSUMER-CYCLICAL-REFUSES-FACTS-IT-CANNOT-PUBLISH. Suite 65 -> 72.
      The 102 residual violations it left open are CLOSED by
      CC-V1-CASE-RECONCILIATION below.
  - id: CC-V1-CASE-RECONCILIATION
    title: "Synthetic case reconciled with its own contract"
    status: done
    next_action: >
      _plnt_case() 102 violations -> 0, golden oracle exact on both the
      synthetic and fixture cases. Six one-key source_record stubs became the
      single real Exhibit 99.1 record the committed fixture asserts (a results
      press release carries the prior-year comparatives in the same table, so
      six facts genuinely share one document); perimeter stopped holding the
      contract id; kind stopped defaulting to "financial", a value its own enum
      does not contain; display_quantum became a quantum instead of a unit
      label; subject lost three keys a closed object rejects and gained
      subject_type; and the two facts of a pair stopped sharing one bare
      FACT_KEY_* spelling, which had been publishing non-unique input_refs.
      One engine change: a refusal now supersedes the
      no_compatible_pair_for_comparison_basis it caused, because
      _compose_changes keys that reason on the METRIC - exactly what a refusal
      is keyed on - so the effect landed first and deduplicated the cause away.
      Suite 72 -> 76.
  - id: CC-V1-MINTED-ENVELOPE-REFUSAL
    title: "Admission gate completes its own class"
    status: done
    next_action: >
      The CC-V1-ENVELOPE-INTEGRITY gate closed 4 of the ~13 holes in its class,
      because it was generalized from readers that answer an absent source value
      with an EMPTY sentinel and is therefore structurally blind to readers that
      MINT one. A sweep of all 21 contract-required fact fields against merged
      main - planting a distinctive value, confirming it propagates, then
      dropping it - measured 9 that produce a "ready" document carrying schema
      violations, 3 that VALIDATE WHILE LYING (unit -> "USD",
      sign_convention -> "signed_as_reported", scale_power10 -> 0 publishing
      thousands as units - all legal values, so no downstream consumer can ever
      recover the truth), 4 that mint the contract's own "unknown" and are
      deliberately left alone, and 1 (event) that killed the whole case with
      CaseShapeError. Closed in the module's existing idiom: nine spelled text
      fields, the kind enum by VALUE, sign_convention, a scale_power10 that
      accepts exactly what _envelope_scale can already read, and an evidence
      mapping - each withholding one fact and declaring it through the open
      degraded_dependencies reason vocabulary, so no contract change was owed
      and event stopped killing its case. The same instrument on the repaired
      tree reads 17 refused / 4 minted-and-honest / 0 violations / 0 cases
      killed. See DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE.
      Suite 76 -> 102; reverting the engine alone fails 26 and passes 76, and
      all 26 are the four new tests; 8 mutants all killed.
  - id: CC-V1-DECLARED-BASIS-BINDING
    title: "The declared basis binds the pair; the guard derives from the contract"
    status: done
    next_action: >
      Four defects, one thesis: the module states things it does not check.
      (A) _select_pair received comparison_basis and never read it, so a prior
      side seven years off, a period ending before it starts, and a 30-day
      "quarter" all published same_quarter_prior_year_change at availability
      ready with zero schema errors - the refusal reason
      no_compatible_pair_for_comparison_basis already existed and was
      unreachable. Repaired with generous period BANDS, never equalities (a
      retail 4-5-4 quarter is 13 or 14 weeks).
      (B) Three of the four definitions say "in USD thousands" while the
      envelope was whatever the source carried; a contradicting pair now
      withholds with result_envelope_contradicts_stated_definition rather than
      converting a value or rewriting prose this module does not own.
      (C) The document self-check walked three collections and read ZERO root
      fields - 0 of the 5 root scalars the contract constrains. Replaced with
      validation against the published schema (the house idiom; 39 engine
      modules already do it), and the constant-mirror test made reflective so a
      new unpinned vocabulary fails it. That found _ALLOWED_COMPARISON_BASIS had
      drifted to three words against the contract's enum of ONE, so two bases
      were admitted and emitted as contract-invalid documents.
      (D) Found BY (C), not suspected: results[*].input_refs published duplicate
      provenance against uniqueItems in five of the module's own tests, green on
      main for the module's whole life. Reproduced against main's unpatched
      bytes before repair, so it is pre-existing. Deduped order-preserving at
      _emit_result, the single point every result passes.
      Mutation round 12/13 killed, the survivor equivalent and now pinned. Both
      live cases unchanged (0 errors, ready, oracle exact). Suite 102 -> 111.
  - id: CC-V1-ENTITLED
    title: "V1 entitled + browser legs"
    status: todo
    next_action: >
      Consume the #7870 T09 rights correction and the #7780 mount ruling when
      they land, then take the shared private transport and company page. Frozen
      behind external owners whose heads have not moved since the R15 freeze.
blocked_by:
  - "#7870 T09 EDGAR-family/fail-closed rights correction plus T08b/T10e/T10f/T11a"
  - "#7780 cross-vertical profile/dispatch/mount ruling (owns the R15 H2 grammar)"
  - "#7669 template/page custody for the company-page consumer"
  - "incumbent source owner must natively admit the PLNT Q2 2026 exhibit"
landmines:
  - >
    A parameter a function RECEIVES is not a property it CHECKS. comparison_basis
    reached _select_pair's signature and nothing in the body read it, which is
    precisely why review passes over it - the signature reads like the check is
    there. Name the line that reads a label before calling it enforced.
  - >
    A guard that hand-enumerates its checks is scoped by the enumeration, never
    by the authority it mirrors. Do not extend the list; derive from the source
    and add one reflective test that fails when a new item is unpinned.
    Extending reproduces the defect at the next field.
  - >
    app/earnings.py LOOKS like an opening (merged, entitled, private/no-store)
    and is not: R15 H1 superseded direct Earnings delivery for this dossier and
    pre-labels it "not a second publisher"; engine/earnings_narrative/** belongs
    to CDV-1 (#7792).
  - >
    native_admitted is a PROVENANCE LABEL, never a suppression gate. Gating on
    it makes the projection structurally incapable of its own golden case,
    because PLNT's exhibit is retained nowhere.
  - >
    Fact keys and result keys are DISJOINT vocabularies that read alike. The
    lead was unreachable on every input because _build_explanation tested
    FACT_KEY_* constants for membership in the set of RESULT keys, and 61 tests
    stayed green because every asserted NUMBER was still exact - only the
    sentence explaining them was missing. Never spell a result key by
    concatenating onto a FACT_KEY_*; the spellings coincide today, so drift
    would be silent. Pinned by test_result_keys_and_fact_keys_are_never_
    interchangeable.
  - >
    A new contracts/sector_intelligence/*.schema.json must expose
    properties.contract_id.const or the shared registry enumeration reds; a new
    exclusive CI job name must be added to CURATED_EXCLUSIVE in
    tests/test_ci_pack.py, which asserts exact set equality.
  - >
    The suite's own fixture builders are the least-validated inputs in the
    project. _plnt_case() drove most of the 65 green tests while producing 128
    schema violations, because every assertion read a computed NUMBER and none
    read the document's SHAPE. When the self-check landed, 26 tests went red -
    the correct reading is "the helper was always wrong", never "the check is
    too strict". Narrowing the instrument to restore green is the vice this
    workstream has already committed once.
  - >
    input_refs names the fact KEY (see _fact_ref) and the contract declares it
    uniqueItems, so the two facts of a pair must not share a key. Spelling both
    sides with one bare FACT_KEY_* constant published
    ["advertising_expense", "advertising_expense"] for every same-metric
    change. Pinned by test_the_two_facts_of_a_pair_never_share_a_key.
  - >
    native_ref and source_records[].record_id are spelled in two places and the
    contract validates each in isolation, so both patterns pass while the
    pointer dangles. Pinned by
    test_every_native_ref_resolves_to_a_declared_source_record.
  - >
    A test that mutates BOTH sides of a pair cannot observe a
    cause-versus-effect collision, because removing the metric entirely means
    _compose_changes never declares anything to collide with. The first version
    of test_a_refusal_names_its_cause_not_only_its_effect did that, passed
    against a mutant that deleted the behaviour it claimed to pin, and the same
    vacuity then made reverting the real engine fix look safe. Mutate one side.
  - >
    An admission gate is scoped by what each READER does on absence, never by
    the list the gate already carries. Four sentinel-returning readers grew a
    gate that asks "is this field empty?" - a question that is unanswerable for
    a reader whose purpose is to never be empty. Enumerate the _envelope_*
    readers, not the existing arms. And a reason spelled missing_or_malformed
    needs BOTH tests: mutant M6 (emptiness half deleted) survived all fourteen
    absence tests that existed then, and died only once present-but-empty
    cases were added.
  - >
    period_start must never be derived from period_end. Consumer Cyclical is
    retail: 4-5-4 fiscal quarters are offset from the calendar by design, so
    calendar-snapping produced valid-looking 32-day "quarters". The derivation
    was unreachable when deleted, which is exactly why it survived review.
do_not_redo:
  - "R1-R11, the independent reviews, R12/R13 verification, R14 reconciliation"
  - "The R8 native-staging denial: never retry, rephrase, re-home or delegate around it"
  - "The V1 boundary adjudication itself - see DEC:CONSUMER-CYCLICAL-V1-CORE-EXTENDS-INCUMBENT-NOT-TRANSPORT"
next_action: >
  No ungated WIRING lane exists and none has appeared: all four blockers below
  are still OPEN or DRAFT, V1-CORE has zero runtime callers on main (git grep
  for consumer_cyclical_projection outside its own suite returns nothing - it is
  merged, correct and inert by design until #7780 rules on the mount), and the
  two gate PRs that moved on 2026-09-27 carry Semiconductor traffic, not a
  Consumer release.
  .
  What that claim did NOT cover, and what CC-V1-MINTED-ENVELOPE-REFUSAL then
  found, is ungated CORRECTNESS work inside owns_paths. Re-testing "nothing
  ungated remains" by observation rather than by memory is the move that found
  it; do that before repeating the claim. As of that wave both cases the
  projection can be handed - the synthetic _plnt_case() and the committed
  fixture - validate at zero violations with the R6 7.1 golden oracle exact,
  AND no contract-required envelope field can be minted from a silent source.
  .
  Returned to Sol on carrier #7804 (comment 5814888647, 2026-09-24) naming the
  four blockers below and correcting that carrier's standing
  RECEIVER_ASSIGNMENT NONE, which would otherwise have licensed a second Fable
  receiver onto the same operation. ACCEPTANCE is Sol's and has not been given.
  Do not widen into V2 LTH / V3 LULU / V4 theme journey - R15 forbids
  self-authorizing them on a V1 pass, and the next modifying wave takes its own
  continuation edge.
  .
  CC-V1-MINTED-ENVELOPE-REFUSAL merged as PR #8099 (squash edf7f0add1b1,
  2026-09-27T22:00:06Z) and was proven from main's re-extracted bytes: 102
  passed, both cases 0 errors / ready / oracle exact, and the envelope sweep 17
  refused / 4 minted-but-honest. CC-V1-DECLARED-BASIS-BINDING follows it.
  .
  CC-V1-DECLARED-BASIS-BINDING merged as PR #8103 (squash 2b98cf7cfc99,
  2026-09-27T22:36:16Z) and was proven from main's re-extracted bytes (blob
  e9026639bf86 == origin/main's): 111 passed, both cases 0 errors / ready /
  oracle exact, envelope sweep 17 refused / 4 minted-but-honest. Mutation 12/13
  with W2 reported as a genuine EQUIVALENT mutant, not gamed away. Reported on
  #7804 (comment 5860482755). ACCEPTANCE remains Sol's.
  .
  The correctness lane is now MUCH closer to exhausted than the previous note
  claimed, and the specific gap that note named is CLOSED. The derive-don't-
  enumerate method HAS since been run on the case admission path, and on pair
  agreement. Both returned NULL, and both nulls are load-bearing. (1) Admission
  does leave four contract-required fact fields unread
  (native_admitted / native_ref / published_at / target), but that is ALREADY
  ADJUDICATED by DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE
  so_what (4) - they publish the contract's own "unknown", native_admitted
  false under-claims, and it is presently ACCURATE because R8 native staging is
  blocked. DO_NOT_REDO: re-deriving it cost this seat ~20 minutes because the
  probe ran before the prior DSC was read. (2) Pair agreement on unit,
  scale_power10, sign_convention and period_kind is CHECKED - every legal-value
  disagreement collapses the pair and declares.
  .
  Swept to date: 21 fact fields; 5 root scalars; basis binding; input_refs;
  pair agreement; and as of wave 7 the native_ref -> source_records pointer.
  Anyone running the remaining sweep must first read
  DSC:A-MUTATION-THAT-DIES-UPSTREAM-NEVER-TESTS-THE-GATE-YOU-AIMED-AT: two
  probes in wave 6 returned a vacuous green because the mutation died at an
  earlier gate or was a no-op.
  .
  CC-V1-PROVENANCE-POINTER (wave 7) is PR #8106. A fact could name a
  source record absent from its own document's source_records ledger and be
  emitted at availability "ready" with ZERO schema errors; separately,
  native_ref carried no pattern while record_id was pinned to
  ^src_[a-z0-9_]+$, so the two ends of one pointer had different grammars and
  "SRC-NOT-LEGAL" was accepted. Repaired at document level because
  _fact_admission_failure structurally cannot see source_records. 22 test
  fixtures using an unsatisfiable hyphenated ref convention were swept. Also
  corrected a FALSE _compose_changes docstring that claimed native_admitted:
  False suppressed a result (citing section 7) while the code 20 lines below
  refuses that gate citing 4a -- a reader who trusted it would have restored a
  gate that breaks the golden oracle; now pinned by a test. 114 passed, both
  cases oracle-exact at 0 schema errors, envelope sweep unchanged 17/4.
  See DSC:TWO-ENDS-OF-ONE-POINTER-VALIDATED-IN-ISOLATION-BOTH-PASS-WHILE-IT-
  DANGLES.
  .
  NOT a defect and DO NOT "fix" it: frozen-spec 4a's literal "native_ref is
  null" is STALE, not violated. V1-CORE facts point at a source record whose
  retention_state is not_retained -- strictly more honest than a bare null and
  exactly the "source-coordinate-bound, not natively admitted" posture 4a
  itself describes. Forcing null destroys information and breaks the oracle.
  .
  CORRECTION 2026-09-28 (wave 8): the sentence that stood here -- "the honest
  unswept remainder is now the explanation object and availability/state
  derivation" -- is SPENT, not wrong-at-the-time. Wave 7 swept both and both
  returned NULL: `explanation` is assembled from frozen constants with no
  number interpolation, and `availability` is derived from READY results and
  makes no independent claim. Wave 8 then swept the authority guard and found
  TWO real defects (see the two DSC keys registered above). Do not re-sweep
  explanation or availability; the open lead is the SIBLING verticals, not
  this module. source_records itself is NOT unswept in the
  passthrough sense first suspected: it is copied verbatim from the case but
  _assert_document_matches_contract_shape runs full jsonschema validation over
  the whole document, so every record is deeply checked against the 12
  required fields of $defs/source_record. What was missing was only the
  RELATION between it and native_ref, which wave 7 closed.
  .
  WAVE 8 (authority vocabulary). _assert_no_forbidden_authority_keys carried a
  docstring asserting the full frozen-spec section 6 rule 10 guarantee -- no
  ranking, entry, gating, sizing or origination field -- and enforced 4 of 30
  category-representative keys. Two distinct defects. (a) The blocklist held
  the RULE'S OWN NOUNS: "sizing" was refused while position_size, weight,
  allocation, notional and exposure were not. (b) The compound pattern was
  applied with re.fullmatch, under which "(^|_)(stem)(_|$)" cannot consume a
  compound name, so composite_score / analyst_rank / conviction_score /
  signal_strength ALL passed the one construct named for catching them; its
  only hits were bare stems the exact-match frozenset already held, so its
  marginal contribution was zero. Both repaired; guard now 28 of 30, pattern
  live, docstring corrected to name additionalProperties:false as the FIRST
  line and itself as the second.
  .
  NEITHER DEFECT WAS REACHABLE. The root and every composite $defs carry
  additionalProperties:false, and injecting each key into a real emitted
  document showed position_size / weight / recommendation refused at the SHAPE
  gate and only rank at the authority gate. So wave 8 is a false-confidence
  repair, not a vulnerability fix, and it must not be described as the latter.
  The risk it removes is that a future change unsealing a $defs would drop the
  real protection while the guard that appears to cover it still passed review.
  .
  Defect (b) was found by a mutation that SURVIVED: a negative-control test
  asserting sample_size stays unrefused should have gone red when size|weight
  was added to the compound pattern, and did not -- impossible unless the
  pattern never fires. The surviving mutation indicted the test first and the
  module second. 118 passed; 4/4 mutations caught; no legal contract property
  name is refused by the widened guard; oracle and envelope sweep unchanged.
  .
  WAVE 8 MERGED + PRODUCTION_PROOF. Squash 2dac71fc659b, 2026-09-28T00:19:08Z,
  merged by the sweeper 9s after the last check concluded (26 checks, 0
  unconcluded; sole red ci-authority/codex/merge-queue-pilot, red by design and
  name-excluded). Proof from main's own re-extracted bytes: 8 of 8 assertions
  OK, 118 passed, oracle exact both cases, sweep unchanged 17 REFUSED / 4
  MINTED. Reported on carrier #7804 (comment 5861199381). ACCEPTANCE remains
  Sol's and is not claimed.
  .
  WAVE 9 (sibling census) -- the wave-8 unresolved lead, RUN, and it refuted its
  own premise. The lead said "probe the Finance / Mining / Industrials /
  Healthcare / Energy authority guards". engine/sector_intelligence/ holds
  exactly TWO projection modules, consumer_cyclical and finance; the other three
  have no module there. That five-name list was written from the PROGRAM ROSTER,
  not from a module census -- A ROSTER IS NOT A CENSUS. The lead's suggested
  discriminator was also wrong: grep -rn "_RE.fullmatch" engine/ returns 475
  hits, nearly all correct format validators where fullmatch is right; the shape
  is a boundary-stem PATTERN under fullmatch, not fullmatch as such.
  .
  The refuted lead sat in THREE records (the wave-8 handoff's unresolved AND its
  unverified, plus the wave-8 DSC's scope). All three are corrected AT SOURCE in
  this same commit, not superseded from a newer file -- a reader travels into
  the wrong record, so that is where the correction has to be.
  .
  FINDING, routed as knowledge and NOT acted on: the one real sibling carries the
  shape in a deader form. finance_projection.py:296 defines _FORBIDDEN_KEY_RE
  with ZERO call sites repo-wide (7 hits total; the other 6 are local copies in
  lib/project_runtime_state.py and a test, each of which DOES use its own), while
  the module docstring line 15 advertises the protection. Finance imports only
  stdlib so it cannot validate at emit; its real protection is a 43/43-sealed
  contract enforced by validate_contract at
  tests/test_finance_intelligence_contract.py:95 -- at CI time, in the test.
  Classified FALSE CONFIDENCE, not a demonstrated reachable leak: reachability
  was NOT verified and needs a mutation probe of that test. finance_projection.py
  is seat 938d17d6's custody and was not edited from this seat. See
  DSC:A-GUARD-NAMED-IN-THE-DOCSTRING-CAN-HAVE-ZERO-CALL-SITES.
  .
  Wave 9 MERGED as #8115 (squash e274e2c5f5be), 11/11 records verified in main's
  bytes.
  .
  Wave 10 measured the last two unswept Consumer surfaces and BOTH returned a
  null against the wave-8 thesis -- recording the null is the result. The
  explanation object cannot carry the defect: _build_explanation selects between
  exactly two module-owned documents, no caller text enters, both directions have
  named tests, and _check_explanation_for_forbidden reads all four emitted keys
  with zero uncovered. degraded_dependency.state is a three-value contract enum
  with exactly ONE producible value -- _degraded defaults state to "unavailable"
  and all seven call sites omit the argument -- and zero readers outside the
  producing module; "available" on an entry in a list OF degraded dependencies is
  self-contradictory. Censused across all twelve contract enums it is the ONLY
  module-authored one that cannot be fully exercised: seven are fully exercised
  and the four others that look narrow (fact.basis / role / perimeter,
  source_record.retention_state) are CALLER-authored passthroughs whose enums
  correctly constrain input -- the wave-7 who-writes-it rule is the
  discriminator, and skipping it gives four false positives out of five flags.
  Classified LOOSE, not false: the document never claims
  anything untrue, so no contract narrowing was opened with no consumer to
  benefit. Shipped one mutation-probed pin
  (tests/test_consumer_cyclical_projection.py:1911) that asserts each mutation
  changed the case and requires >1 distinct reason before asserting the state
  set, so a stale fact-key filter fails loudly instead of passing on an empty
  list. Suite 103 passed (119 with the sibling contract file). This CLOSES the
  Consumer correctness sweep; see do_not_redo in the wave-10 handoff. V1 has not
  returned to Sol and ACCEPTANCE remains Sol's.
  See DSC:A-REQUIRED-ENUM-FIELD-CAN-HAVE-ONE-PRODUCIBLE-VALUE-AND-ZERO-READERS.
---

## Scope

V1-CORE is the maximal lawful V1 subset under current custody, not `V1 PROVEN_LIVE`.
It is the artifact the blocked transport and page legs will later publish unchanged.
