---
workstream: "WS:CONSUMER-CYCLICAL-V1"
session: claude/ssd-consumer-cyclical-v1-envelope-integrity-63a750ab8baaba18
model: opus
ended_because: complete
prs: [8054]
decisions:
  - "DEC:CONSUMER-CYCLICAL-REFUSES-FACTS-IT-CANNOT-PUBLISH"
discoveries:
  - "DSC:THE-CASE-A-SUITE-USES-MOST-IS-THE-ONE-IT-NEVER-VALIDATES"
mission: >
  Resume the Consumer Cyclical V1 integration seat after V1-CORE returned to Sol
  on carrier #7804. Establish whether anything is lawfully executable with every
  remaining V1 leg owner-gated, and if so execute it end to end.
state_before: >
  V1-CORE merged (#7942, #7945) and live-verified. All four external gates
  unmoved and no Sol reply on #7804 for ~2 days. The remaining V1 legs (entitled
  transport, company page) are blocked on #7870 T09, #7780, #7669 and native
  source admission. No widening into V2 LTH / V3 LULU / V4 was lawful, and the
  R8 native-staging denial remained sticky.
changed:
  - path: engine/sector_intelligence/consumer_cyclical_projection.py
    what: >
      Added a fact admission gate (_fact_admission_failure /
      _partition_admissible_facts) that withholds any fact whose value_text is
      unparseable or whose period envelope is missing, malformed, or outside the
      published period_kind vocabulary, and declares each refusal into
      degraded_dependencies with a named reason. Deleted the period_start
      derivation (calendar-snapping, wrong for 4-5-4 retail calendars) so
      period_start is read from the source or absent. _withheld_result now
      carries the period provenance it was already handed instead of discarding
      it. Added _assert_document_matches_contract_shape, run at the end of
      project_economic_change, raising CaseShapeError rather than returning a
      contract-violating document. Deleted _envelope_period_end_internal and
      _fact_native_ref_or_default (zero callers repo-wide). Repaired a dedup
      guard that compared against a nonexistent `fact_key` field.
  - path: tests/test_consumer_cyclical_projection.py
    what: >
      Made the _plnt_case() fixture helper contract-valid (period_start now
      sourced from a real fiscal map, not period_end[:4]+"-01-01"; basis, role,
      sign_convention and event set to admitted vocabulary values), and appended
      7 tests covering refusal-not-repair, refusal-not-silent-completion,
      period_start never derived, withheld-result provenance, the module
      constants mirroring the published contract, and the self-check firing on
      facts, results and degraded_dependencies.
  - path: agentos/decisions/DEC-CONSUMER-CYCLICAL-REFUSES-FACTS-IT-CANNOT-PUBLISH.md
    what: New. The refuse-don't-repair ruling with its four rejected alternatives.
  - path: agentos/discoveries/DSC-THE-CASE-A-SUITE-USES-MOST-IS-THE-ONE-IT-NEVER-VALIDATES.md
    what: >
      New. 128 schema violations in the suite's dominant fixture while 65 tests
      passed; sibling of DSC:A-UNIVERSAL-FALLBACK-BRANCH-IS-INVISIBLE-TO-A-VALUE-ONLY-SUITE.
  - path: agentos/workstreams/WS-CONSUMER-CYCLICAL-V1.md
    what: >
      Added wave CC-V1-ENVELOPE-INTEGRITY (done), three landmines, and the open
      _plnt_case() reconciliation as an ungated next_action owned by this
      workstream.
verified:
  - claim: "The defect is real on pristine main, not an artifact of this branch."
    command: "git stash-free extraction of origin/main @90f9fcbe31ff into a scratch tree, then jsonschema Draft202012Validator against contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json"
    result: "value_text '365,223' -> 9 violations; fact missing period_kind -> 18; non-positive ratio denominator -> 3."
  - claim: "Owned suite is green at 72."
    command: "python3 -m pytest tests/test_consumer_cyclical_projection.py tests/test_consumer_cyclical_intelligence_read_model_contract.py -q"
    result: "72 passed in 1.31s (projection file 56, contract file 16)."
  - claim: "The suite grew by exactly 7 tests; nothing was deleted to make it green."
    command: "git show origin/main:tests/test_consumer_cyclical_projection.py | grep -c '^def test_' ; grep -c '^def test_' tests/test_consumer_cyclical_projection.py"
    result: "49 then 56."
  - claim: "The R6 7.1 golden oracle is unchanged by this PR."
    command: "python3 -c harness invoking project_economic_change on both the synthetic _plnt_case() and data/sector_intelligence/fixtures/consumer_cyclical_intelligence_read_model.v1.valid.json"
    result: "24344 / 10141 / 10145 / -4 / 0 / 41.66 exact on both, R6 advertising-flow lead still rendered."
  - claim: "The new tests are non-vacuous."
    command: "9 hand-applied mutants to engine/sector_intelligence/consumer_cyclical_projection.py, suite re-run after each"
    result: >
      8 killed. M10 (reverting the dedup guard to the nonexistent `fact_key`
      field) SURVIVED and was left surviving - the repair is behaviour-neutral
      today because the two sides use disjoint vocabularies, so no test can
      distinguish it. Reported as hygiene, never as a fix.
  - claim: "The deleted functions had no callers anywhere in the repository."
    command: "grep -rn '_envelope_period_end_internal\\|_fact_native_ref_or_default' --include='*.py' --include='*.md' --include='*.json' ."
    result: "No hits outside the definitions being deleted."
  - claim: "The Agent OS store validates."
    command: "python3 scripts/agentos.py validate"
    result: "1292 records, 0 errors, 104 warnings (all pre-existing review-overdue)."
  - claim: "The CI job inventory still validates with these files in it."
    command: "python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only"
    result: "235 legacy jobs validate."
  - claim: "The carrier had not moved before this PR was opened."
    command: "gh pr view 7804 --json comments --jq '[.comments[] | select(.createdAt > \"2026-09-24T18:00:00Z\")]'"
    result: "Empty - no Sol reply, no new receiver assignment, no superseding edge."
unverified:
  - claim: "The sibling sector projections (finance, industrials, energy, healthcare) have the same defect class."
    what_would_verify: >
      Run each vertical's own suite, then validate its emitted document against
      its own contract. NOT done here - those modules belong to other seats and
      this seat has no custody. The DSC exists so they can check cheaply.
  - claim: "102 is the exact residual violation count after this PR merges."
    what_would_verify: >
      It was measured on the branch head before the final records commit, which
      touched no engine or test code. Re-measure with the validator harness
      before starting the reconciliation.
unresolved:
  - >
    _plnt_case() still violates its own contract on definition, display_quantum,
    kind, perimeter, source_records, subject, and duplicate input_refs (two
    facts sharing a key produce non-unique input_refs). ~40 assertions ripple.
    Owned by this workstream, gated on nothing.
  - >
    All four external V1 gates remain unmoved: #7870 T09 rights correction,
    #7780 mount ruling, #7669 page custody, and native source admission of the
    PLNT Q2 2026 exhibit.
next_actions:
  - >
    Watch PR #8054 to merge. It is armed merge-on-green; stay until merged, then
    confirm the merge commit carries the admission gate on main.
  - >
    Reconcile _plnt_case() with the contract (the 102 residual violations). This
    needs no external gate and is the highest-value ungated work left here.
  - >
    Only then, if the carrier has moved: consume the #7870 T09 rights correction
    and the #7780 mount ruling for the entitled/browser legs.
do_not_redo:
  - "R1-R11, the independent reviews, R12/R13 verification, R14 reconciliation."
  - >
    The R8 native application-code staging denial. Sticky: never retry,
    rephrase, re-home to another device/tool/account/model, or delegate around.
  - >
    The V1 boundary adjudication - DEC:CONSUMER-CYCLICAL-V1-CORE-EXTENDS-INCUMBENT-NOT-TRANSPORT.
  - >
    The refuse-vs-normalise question. Settled with four alternatives written
    down in DEC:CONSUMER-CYCLICAL-REFUSES-FACTS-IT-CANNOT-PUBLISH. Do not
    "improve" the module by normalising separators or deriving period
    boundaries; that is the defect, not the fix.
  - >
    Re-deriving period_start by month-subtraction. Considered and rejected: it
    is still a guess for 52/53-week retail calendars, and a guessed boundary is
    indistinguishable from a sourced one once published.
  - >
    Do not widen into V2 LTH / V3 LULU / V4 theme journey. Returning V1 to Sol
    is necessary but not sufficient; acceptance plus a fresh continuation edge
    is required, and ACCEPTANCE is Sol's and is never claimed by this seat.
danger_areas:
  - >
    The suite's fixture builders are the least-validated inputs in the project.
    When a new guard turns tests red, the default reading is "the fixture was
    always wrong", not "the guard is too strict". Narrowing the instrument to
    restore green is the vice this workstream has already committed once.
  - >
    Fact keys and result keys are disjoint vocabularies that read alike. Never
    spell a result key by concatenating onto a FACT_KEY_* constant.
  - >
    period_start must never be derived from period_end in this sector. 4-5-4
    retail quarters are offset from the calendar by design.
  - >
    This worktree materialised data/ (4.6 GiB) to reach the fixture. Re-sparse
    with `python3 scripts/worktree_sparse.py sparse` before leaving it idle -
    the SSD floor is an admission gate for every new worktree on the volume,
    not merely an alarm.
  - >
    A new contracts/sector_intelligence/*.schema.json must expose
    properties.contract_id.const or the shared registry enumeration reds; a new
    exclusive CI job name must be added to CURATED_EXCLUSIVE in
    tests/test_ci_pack.py, which asserts exact set equality.
---

## Why this session did engine work at all

Every remaining V1 leg is owner-gated and the carrier had not moved in two days,
so the honest read was "nothing executable". That read was wrong in a specific
way worth recording: it treated the *merged* work as finished because it was
merged. A line-coverage audit of the module this seat already owns cost about
twenty minutes and found 110 never-executed executable lines, two dead
functions, and then the real finding - that the module publishes documents
violating the contract it authors, on inputs a human would write by hand.

Owned-code auditing is the ungated work that exists when every gate is shut. It
needs no custody this seat does not already hold, and it is where the defects
that survived review live, because review reads the diff and coverage reads the
whole.
