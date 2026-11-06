---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-l1a-registration-paths
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task L1 row L1a (research/capital_structure/e2e_20261013/MASTERPLAN.md,
  acceptance rows A10, A11, A20 and A23; depends on L0 and on the sealed
  registration lifecycle compiler): implement
  engine/capital_structure/registration_integration.py so C1 can read
  registration paths, keep EFFECT, automatic shelf, primary versus resale,
  withdrawal, replacement and the shelf window as DISTINCT predicates that no
  combination of them turns into a capacity claim, keep valid time and house
  knowledge exact and apart, and ship the suite through the ordinary chain. A
  fabric lane (cs-v2-l1a-20261014T1438Z) wrote the code; the O2 orchestrator
  reviewed it against the frozen spec, repaired it, committed it and opened the
  pull request.
state_before: >
  L0 (PR #9314, squash-merged as d054f60ff43b0ff5e99b0ed56be9263bbf9186d5) carried
  the rule-applicability pack 1.0.0 and its reader, and L1b (PR #9359, head
  c61c5cd7473e4c77969e399f23e3743f7ba57cd2) raised the pack to 1.1.0 with
  Rule 415(a)(5), (a)(6) and 462(e) text. The registration lifecycle compiler
  (engine/capital_structure/registration_lifecycle.py, unchanged since 2026-08-02)
  already produced point-in-time lifecycle records, timelines, coverage and a
  defer ledger. Nothing composed the two: no module turned a lifecycle record
  into separately evidenced registration predicates, so no caller could ask
  whether an effectiveness notice, an automatic shelf form, a withdrawal or a
  Rule 415(a)(5) window had been observed without re-deriving the answer itself.
changed:
  - path: engine/capital_structure/registration_integration.py
    what: >
      New module (capital-structure-registration-integration/1.0.0, record schema
      capital_structure.registration_path.v1). integrate_registration_paths
      selects its source fail-closed: events and event_edges both bound and
      usable recompile; a precompiled bundle alone must validate and must already
      be cut at the requested as_of; both bound means recompile and require
      canonical-JSON equality of the records lists or refuse naming both digests;
      events bound usable with no event_edges binding and no bundle refuses;
      nothing bound refuses; any bound family that is unavailable or not_built
      (including an event_edges ledger bound unavailable beside usable events)
      returns an unavailable family with no records. It emits one path record per
      lifecycle record with origin, amendment_chain, intervals (valid_from and
      valid_to from SEC acceptance, known_from and valid_to_known_from from
      mastermind_available_at) and eight closed predicates, deep-copies the
      lifecycle issuer, registration and coverage, and re-proves the closed
      AUTHORITY block plus FamilyState and FamilyProvenance validation before
      returning. Rule state is read on the window-start or filing day, never on
      as_of. registration_path_at answers valid time only. No lifecycle logic is
      reimplemented; the compiler and its bundle validator are called.
  - path: tests/test_capital_structure_registration_integration.py
    what: >
      26 tests reusing the lifecycle suite's own _event, _edge, _compile and
      _scenario factories by import: the ten frozen-spec cases (A10 S-1 path, A10
      S-3ASR form fact, A11 intervals, A11 then-known versus later-known, repeated
      EFFECT with a corrected root, defer pass-through with partial coverage, the
      source-selection outcomes including the half-bound events/edges pair,
      family-state round-trip and receipt binding, unchanged lifecycle embedding),
      a recursive FORBIDDEN_PROPERTY_PATTERN walk over every key and every string
      value of every path, offering_role and replaced unknown on every path of
      every fixture including a supersedes edge, a textless stub pack that keeps
      shelf_window and automatic_effectiveness unknown, a stub pack built from the
      real ApplicableRule and RuleWindow records proving the 2024-03-01 window
      dates, both positions, the Feb-29 clamp and the automatic-shelf window that
      starts at the origin filing date, and two B.5 cross-tests against the real
      repository pack 1.1.0 (an S-3 EFFECT on 2024-03-01 is conditional with
      window 2024-03-01 to 2027-03-01, the S-3ASR effectiveness is conditional on
      462(e), and a window starting 2026-10-12 stays unknown).
  - path: .github/ci/legacy-jobs.yml
    what: >
      Exactly one added line registering the new suite in the
      capital-structure-intelligence job, immediately after
      tests/test_capital_structure_rule_applicability.py (CI-authority edit,
      same shape as L0).
  - path: agentos/decisions/DEC-CS-V2-REGISTRATION-PATHS-L1.md
    what: >
      The decision that offering_role and replaced stay unknown, that a
      supersedes edge is version supersession and never a replacement, that a
      precompiled bundle cannot be re-cut, that the events+edges source needs
      both ledgers bound, and that shelf_window is conditional only on
      pack-qualified Rule 415(a)(5) text plus an initial effectiveness date; it
      also records the spec-literal reason-name gap.
verified:
  - claim: The new suite passes on its own against the L1b pack 1.1.0.
    command: >
      PYTHONPATH=. /opt/homebrew/bin/python3.12 -m pytest -q
      tests/test_capital_structure_registration_integration.py (in an SSD build
      tree holding origin/main b4e1d4c7 plus L1b's five files from c61c5cd7 plus
      the five L1a files)
    result: 26 passed, 14 warnings in 1.79s.
  - claim: The six named suites run together with no regression attributable to this diff.
    command: >
      PYTHONPATH=. /opt/homebrew/bin/python3.12 -m pytest -q
      tests/test_capital_structure_registration_integration.py
      tests/test_capital_structure_rule_applicability.py
      tests/test_capital_structure_registration_lifecycle.py
      tests/test_compile_capital_structure_registration_lifecycles.py
      tests/test_capital_structure_term_integration.py
      tests/test_capital_structure_issuer_state_contracts.py (same build tree)
    result: >
      2 failed, 270 passed, 14 warnings in 79.81s. Both failures are
      tests/test_compile_capital_structure_registration_lifecycles.py::
      test_disk_compiler_verifies_generation_and_writes_receipt_bound_artifact
      and ::test_failed_upstream_receipt_verification_preserves_last_good_output,
      and both are pre-existing (next claim).
  - claim: >
      Those two failures are pre-existing and independent of this branch; they
      reproduce in trees that do not contain registration_integration.py at all.
    command: >
      The L1b review run of the five named suites other than this one on the L1b
      head c61c5cd7 (no L1a file present), and the fabric lane's run of
      tests/test_compile_capital_structure_registration_lifecycles.py in an
      independent checkout at ee79a5dd58.
    result: >
      2 failed, 244 passed on the L1b head, and 2 failed, 2 passed in the lane's
      checkout, the same two tests each time, with the digest mismatch
      'event:cs:f84dcda0924be74ecce6a475' != 'event:cs:bd962f83c9f7877448227a72'.
      Root cause: scripts/compile_capital_structure_events.py writes events whose
      version.identity_format is 2 and whose event_id is the format-2 digest from
      engine/capital_structure/event_spine.py compute_event_id (commit ecb2d88772,
      2026-08-19), while engine/capital_structure/registration_lifecycle.py
      _validate_immutable_identity recomputes only the format-1 digest. Both files
      are out of scope for L1a.
  - claim: The Agent OS store still validates with both new records present.
    command: python3 scripts/agentos.py validate (same build tree)
    result: exit 0; see the pull request body for the record and warning counts at the pushed head.
  - claim: Every CI pack still validates, and the pack that owns the new suite selects capital-structure-intelligence.
    command: >
      python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml
      --pack-index N --pack-count 12 --validate-only --scope-mode off for N in 0..11
    result: >
      exit 0 for all twelve packs. --validate-only prints job names rather than
      test files, so the suite is located by its owning job name.
unverified:
  - claim: contract-delta is green for this diff.
    what_would_verify: >
      The contract-delta check on the pull request concluding green at the exact
      head. It was not run locally because the build tree is not a git checkout
      and the session worktree carries another row's branch.
  - claim: Hosted CI is green on the pushed head.
    what_would_verify: The pull request's checks concluding green at the exact head.
  - claim: L1a is merged and landed on origin/main.
    what_would_verify: >
      Squash-merge on concluded green after #9359 lands and this branch is
      rebased onto main, then a bare git fetch and a per-path blob comparison
      against origin/main for the five changed paths.
  - claim: >
      C1 reads these predicates without turning any of them into a capacity claim.
    what_would_verify: >
      The C1 row's own suite asserting that a path record's eight predicates,
      alone and combined, produce no amount, no remaining-dollars figure and no
      executable-offering statement.
unresolved:
  - >
    This branch is stacked on L1b (PR #9359) because its B.5 cross-tests read the
    1.1.0 pack. It must not merge before #9359; once #9359 squash-lands, the
    branch is rebased onto origin/main (same five blobs, new parent) and the named
    suites are re-run at the new head.
  - >
    Reason-name gap kept spec-literal: when the pack carries cfr.17.230.415.a.5 or
    cfr.17.230.462.e but holds it as beyond_window or not_in_force on the start
    or filing date, the predicate answers unknown with
    rule_415_a_5_text_not_in_rule_pack or rule_462_e_text_not_in_rule_pack,
    although the text is present. The status is right; the name overstates the
    cause. A distinct reason is a follow-up spec change, pinned today by
    test_b5_real_rule_pack_leaves_a_window_starting_after_the_last_served_edition_unknown.
  - >
    replaced stays unknown because Rule 415(a)(6) carry-forward rows are
    registration fee-table rows and no document_terms TERM_NAME extracts them;
    that extraction is a separate packet, not a predicate change.
  - >
    The frozen spec named reason strings for the negative and conditional branches
    but not for five positive or not_applicable ones. This module chose
    original_registration_filing_observed, effect_notice_observed,
    no_automatic_shelf_form_observed, withdrawal_observed /
    no_withdrawal_observed, registration_family_not_a_shelf_family and
    rule_415_a_5_window_conditional_on_unverified_requirements. A reviewer who
    wants different words changes only those literals and their tests.
  - >
    The pre-existing event identity defect (format-2 producer, format-1-only
    verifier in registration_lifecycle.py) leaves
    scripts/compile_capital_structure_registration_lifecycles.py's disk path red
    at origin/main. It is owned by the event spine and lifecycle compiler, not by
    L1a, and was left untouched.
next_actions:
  - After #9359 squash-lands, rebase this branch onto origin/main with the same five blobs, push with a lease, and re-run the six named suites at the new head.
  - Merge on concluded green only after #9359 is on main; the seat owns the merge and the main ci.yml baseline for this CI-authority edit.
  - C1 consumes RegistrationIntegration.family_state() as the registration family and must never re-derive a predicate or read one as capacity.
  - Route the event identity format-1/format-2 defect to the event spine owner as its own packet; do not heal it inside a capital-structure row.
  - Propose a distinct reason for a rule the pack carries but does not cover on the start date, as a spec amendment with its own test change.
do_not_redo:
  - Do not infer primary versus resale from a form type, a file number or a registration family; offering_role is value+status unknown on every path by design (A10, A23).
  - Do not read a supersedes edge as a Rule 415(a)(6) replacement; it is event-version supersession of one SEC observation, and replaced stays unknown until fee-table carry-forward rows are extracted.
  - Do not re-cut a precompiled lifecycle bundle to another as_of by filtering its timeline; the refusal is the design, and events+edges is the supported way to move a cutoff.
  - Do not treat events bound without event_edges as an events source; spec A.2(5) needs both ledgers, so a missing edges binding refuses and an unavailable one yields an unavailable family.
  - Do not reimplement lifecycle grouping, correction resolution or defer logic in the integration module; call compile_registration_lifecycles and validate_registration_lifecycle_bundle and read their output.
  - Do not compare lifecycle generation_id when reconciling a recompile against a precompiled bundle; generation_id binds generated_at, so only the records lists are comparable.
  - Do not widen the closed AUTHORITY block, add an amount/remaining/price key, or emit any quantity from a predicate; the record is context only.
  - Do not read rule state at as_of; a shelf window and a 462(e) answer read the pack on the window-start or filing day.
  - Do not bypass a fabric host's disabled remote.origin.pushurl by pushing a lane branch straight to the GitHub URL from that host; the disabled pushurl is repo policy, and the sanctioned path is an orchestrator or seat push.
  - Do not "fix" the two red tests in tests/test_compile_capital_structure_registration_lifecycles.py inside a capital-structure packet.
danger_areas:
  - engine/capital_structure/document_terms.py pins a released parser-runtime allowlist keyed on the host's exact stdlib bytes; Ubuntu's patched html/parser.py (python3.12 3.12.3 on the fabric hosts) is not in it, so 28 tests of the T0 and C0 suites fail there and pass on a pristine CPython 3.12. The macOS /opt/homebrew/bin/python3.12 passes.
  - engine/capital_structure/registration_lifecycle.py raises hard ("visible edge has an endpoint unavailable at as_of") when an edge is system-visible before one of its endpoints is, so a fixture's edge observed_at must never precede max(child available_at, parent available_at); the reused _edge factory already guarantees this.
  - The lifecycle validator refuses a withdrawal or amendment that targets an EFFECT notice, so a withdrawal edge must target the registration statement or an amendment, not the effectiveness notice.
  - Corrections only survive into a timeline when the corrected event is a root or the target of a lifecycle edge; correcting a mid-chain amendment defers the whole group with missing_lifecycle_edge. Fixtures that need correction_version 2 in a timeline must correct the root.
  - FamilyProvenance requires input_schema to be None for an unavailable family, a non-empty support_limits for partial, a compiler_version and a generation_id or artifact digest for supported/partial, and generation_id to match the identifier pattern; issuer_state_contracts._assert_safe_keys permits prophet_authority only as the literal False.
  - Any test that pins pack contents must build a stub pack; the repository pack moves with L1b and later rows, so a test written against "the real pack carries no 415 text" goes red the day the text is qualified.
  - scripts/run_ci_pack.py --validate-only prints selected job names, never test-file paths, so a new suite is located by its owning job name (capital-structure-intelligence).
  - A broad pytest run in a sparse or partial checkout produces hundreds of unrelated artifact failures; run only the named suites.
---

# Capital Structure V2 -- L1a registration-path integration handoff

engine/capital_structure/registration_integration.py is the only composer of
registration paths: it reads the sealed lifecycle compiler and the rule pack and
re-proves the closed boundary on every record. The fabric lane
cs-v2-l1a-20261014T1438Z wrote the module, suite, CI line and records, but its
host refuses lane pushes, so the O2 orchestrator recovered the reviewed edits
from the lane log, repaired them (spec A.2(5) events/edges source selection, the
tests that pinned the old pack's contents, and two B.5 cross-tests against pack
1.1.0), committed them by path and opened the pull request. The branch is
stacked on L1b #9359 and is rebased onto main after #9359 lands. The
registration family is `partial` by construction in v1 -- `supported` is
unreachable while offering_role is always unknown -- and a shelf window is a
date bound with named conditions, never an amount.
