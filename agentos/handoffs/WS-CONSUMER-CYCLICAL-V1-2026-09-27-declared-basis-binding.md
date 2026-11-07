---
workstream: "WS:CONSUMER-CYCLICAL-V1"
session: claude/consumer-cyclical-declared-basis-is-a-label-not-a-check
model: opus
ended_because: complete
mission: >
  Close the stated-but-unchecked class in the Consumer Cyclical V1 projector: make the
  declared comparison basis bind the pair it names, make a result's envelope answer to the
  definition sentence it ships with, and replace the document guard's hand-written list
  with a derivation from the published contract.
state_before: >
  origin/main at edf7f0add1b1 - CC-V1-MINTED-ENVELOPE-REFUSAL (PR #8099) merged
  2026-09-27T22:00:06Z and proven from main's re-extracted bytes. Owned suite 102 passed;
  both live cases 0 schema errors, availability ready, oracle exact; envelope sweep 17
  refused / 4 minted-but-honest. V1-CORE still has zero runtime callers, so this is
  correctness work on a module that is merged, correct and inert by design until #7780
  rules on the mount.
changed:
  - path: engine/sector_intelligence/consumer_cyclical_projection.py
    what: >
      Four repairs. (A) _pair_can_be_basis + _span_fits_kind + _as_date, wired into
      _select_pair's loop, so the declared basis must be able to describe the pair -
      generous BANDS per period kind (quarter 84-100d, half 175-190d, year 350-385d) and
      a 350-385d prior-year gap, never calendar equalities, because a retail 4-5-4 quarter
      is 13 or 14 weeks. (B) A definition guard in _emit_result: a non-ratio result whose
      unit/scale/source quantum contradicts the "in USD thousands" sentence withholds with
      result_envelope_contradicts_stated_definition rather than converting a value or
      rewriting prose this module does not own. (C) _assert_document_matches_contract_shape
      now validates the whole document against the published schema via a memoized
      Draft202012Validator (lazy import, parents[2] path - the idiom of
      engine/capital_structure/projection.py); _ALLOWED_COMPARISON_BASIS narrowed from
      three words to the contract's one; _ALLOWED_DEGRADED_STATE deleted as its only
      reader was the retired hand list. (D) input_refs deduped order-preserving with
      dict.fromkeys at _emit_result, the single point every result passes.
  - path: tests/test_consumer_cyclical_projection.py
    what: >
      +221/-2, the two deletions being the retired _ALLOWED_DEGRADED_STATE assertion.
      Nine new tests: three parametrized basis-refusal arms, the positive control that the
      real case still passes the bands, two definition-contradiction arms, the period-kind
      label binding, provenance ordering, and a band-coherence invariant.
      test_module_constants_mirror_the_published_contract gained _ALLOWED_COMPARISON_BASIS,
      _ALLOWED_KIND, the basis->period-kind coverage rule, and a REFLECTIVE assertion that
      every _ALLOWED_* frozenset on the module is pinned to the schema.
  - path: agentos/discoveries/DSC-A-DECLARED-BASIS-IS-A-LABEL-UNTIL-SOMETHING-READS-IT.md
    what: New. The unread-parameter landmine and the definition-as-claim rule.
  - path: agentos/discoveries/DSC-AN-ENUMERATED-GUARD-IS-BLIND-OUTSIDE-ITS-ENUMERATION.md
    what: New. The guard-shape landmine, the 0-of-5 root measurement, and the derive-don't-enumerate remedy.
  - path: agentos/workstreams/WS-CONSUMER-CYCLICAL-V1.md
    what: >
      Both DSC keys added; wave CC-V1-DECLARED-BASIS-BINDING (done) inserted before
      CC-V1-ENTITLED; two landmines added; next_action records #8099's merge and proof and
      states plainly that the correctness lane is NOT exhausted.
verified:
  - claim: "The declared basis was a label - three incompatible pairs published as ready before the fix."
    command: >
      python3 - <<'PY' (in the sandbox on main's bytes) - move every *_prior fact to
      Q1 2019 / to an inverted period / to a 30-day span, project, and list
      [r for r in doc["results"] if not r.get("withheld_reason") and r["basis"] ==
      "same_quarter_prior_year_change"]
    result: "Non-empty on all three before the fix; empty after, with no_compatible_pair_for_comparison_basis in degraded_dependencies."
  - claim: "The document self-check guarded 0 of the 5 root scalars the contract constrains."
    command: >
      Mint-a-violation sweep over schema["properties"] - for each non-collection root
      field, confirm Draft202012Validator rejects the mutated document, then call
      mod._assert_document_matches_contract_shape and record whether it raises.
    result: "Before: availability, comparison_basis, contract_id, generated_at, schema_version all UNGUARDED. After: all five guarded."
  - claim: "_ALLOWED_COMPARISON_BASIS had drifted to three words against a contract enum of one, and the extra words emitted invalid documents."
    command: >
      python3 -c comparing mod._ALLOWED_COMPARISON_BASIS with
      schema["properties"]["comparison_basis"]["enum"], then projecting a case declaring
      each of the three and validating the emitted document.
    result: "3 vs 1; explicit_same_year_prior_year and explicit_same_half_prior_year each emitted a document with 1 root enum violation."
  - claim: "Duplicate input_refs is PRE-EXISTING on main, not introduced by this wave."
    command: >
      conftest_probe.py in the main-bytes tree monkeypatches
      mod._assert_document_matches_contract_shape to call main's own guard AND the schema,
      then python3 -m pytest tests/test_consumer_cyclical_projection.py -p conftest_probe
      -k "ratio or withheld_is_never_zero"
    result: "5 failed on main's unpatched engine with results[*].input_refs non-unique - the same five that failed under the new guard."
  - claim: "Every new arm is pinned by a test that dies when the arm is removed."
    command: >
      scratchpad/wave6_mutate2.py - 13 mutants, each asserting exactly one source match and
      each followed by `assert P.read_text() != ORIG, "MUTATION WAS A NO-OP"`, running the
      two owned test files per mutant and restoring the file afterwards.
    result: >
      12 KILLED, 1 SURVIVED. The survivor is `if not start < end` in _span_fits_kind,
      equivalent because every span band's lower bound exceeds zero so a negative span
      already fails the band; kept as fail-closed defence and its precondition pinned by
      test_no_period_band_can_admit_an_incoherent_period (mutant W13 kills that).
  - claim: "The repair does not change either live case or regress the wave-5 gate."
    command: >
      python3 proof8078.py and python3 sweep3.py, both copied INTO the tree under test so
      Path(__file__).parent roots them there
    result: >
      Both cases 0 schema errors, availability ready, degraded [], oracle_exact True with
      total_revenue_change 24344 and advertising_share_of_revenue_change_pct 41.66; sweep
      17 REFUSED / 4 MINTED-SCHEMA-VALID, identical to main.
  - claim: "The shipped engine file is exactly main's bytes plus the five reviewed patches."
    command: >
      Replayed wave6_patch{,_b,_c,_d,_e}.py onto `git show origin/main:<path>` in a clean
      directory and compared sha256 with the proven sandbox file.
    result: "MATCH 33daa58f5ac2a8315cfe814c - no stray edit entered the diff."
  - claim: "The owned suite passes in the worktree, and it is the same suite CI runs for this module."
    command: >
      python3 -m pytest tests/test_consumer_cyclical_projection.py
      tests/test_consumer_cyclical_intelligence_read_model_contract.py -q, cross-checked
      against .github/ci/legacy-jobs.yml:5949
    result: "111 passed; the CI job runs exactly those two files."
  - claim: "V1-CORE still has no runtime caller, so this changes no live behaviour today."
    command: >
      git grep -n consumer_cyclical_projection -- . ':!tests/'
      ':!engine/sector_intelligence/consumer_cyclical_projection.py'
    result: "Only .github/ci/legacy-jobs.yml and agentos records. No importer."
unverified:
  - claim: "Nothing else in the module is stated-but-unchecked."
    what_would_verify: >
      Run the same method on the CASE ADMISSION path: replace _validate_case_shape's
      hand-written checks with validation against a case schema (one would have to be
      derived - the contract describes the document, not the input) and record what turns
      red. This wave only ran it on the document emission path.
  - claim: "The period bands are right for issuers other than PLNT."
    what_would_verify: >
      Project a 4-5-4 retailer with a 53-week fiscal year and confirm the year band
      (350-385d) admits 371 days, and a 14-week quarter (98d) sits inside 84-100.
      Reasoned from the retail calendar and pinned by
      test_the_declared_basis_survives_the_case_it_was_written_for, but only PLNT's real
      periods have been run through it.
unresolved:
  - >
    The contract's comparison_basis enum has ONE value while the module's semantic map
    _BASIS_PERIOD_KIND carries three. That is deliberate (the map answers for a word the
    moment the contract admits it, and the mirror test asserts every ADMITTED basis has a
    row) but it means the half_year and year rows are currently unreachable and untested.
    Whoever widens the contract enum must add an arm per new word.
  - >
    _ALLOWED_KIND matched the contract when pinned, so no drift was corrected there - only
    the freedom to drift was removed. It was found by the reflective assertion on its
    first run, which is evidence the same check belongs in the sibling verticals.
next_actions:
  - >
    Ship this branch: commit, push, open the PR, arm merge-on-green, watch to CONCLUDED,
    re-establish that ci-authority/codex/merge-queue-pilot is base-side by reading the same
    check on >=2 independent sibling heads on the live head (it was FAILURE on 7 of 7
    siblings at 2026-09-27T21:57Z, but that must be re-measured, not assumed), then merge.
  - >
    Prove from main's own bytes as #8054, #8078 and #8099 were: git archive origin/main,
    sha256 against `git show origin/main:<path>`, then the owned suite, proof8078.py and
    sweep3.py copied INTO that tree. Report MERGED then PRODUCTION_PROOF on #7804.
  - >
    Do NOT report ACCEPTANCE. It is Sol's and has not been given on any wave of this
    operation.
  - >
    Then run the unverified method above on the case admission path before claiming the
    correctness lane is exhausted.
do_not_redo:
  - >
    The R8 native application-code staging action is DENIED and the denial is sticky. Do
    not retry it, rephrase it, re-home it to another device, tool, account or model, or
    delegate a workaround.
  - >
    R1-R11, the completed independent reviews, R12/R13 verification and R14 reconciliation
    are accepted. A fresh session is not a material invalidator.
  - >
    Waves CC-V1-CORE (#7942/#7945), CC-V1-ENVELOPE-INTEGRITY (#8054), CC-V1-RESULT-ENVELOPE
    (#8078) and CC-V1-MINTED-ENVELOPE-REFUSAL (#8099) are merged and proven from main's
    bytes. Do not re-derive their measurements; the numbers in this file and in the two
    DSCs are the re-measured ones.
  - >
    Do not "fix" the finance-side rights gate flagged in the 2026-09-27 cross-program note.
    That reading was RETRACTED - SOURCE_RIGHTS_HELD maps to RIGHTS_RESTRICTED, which is the
    conservative pole, not a fail-open default.
danger_areas:
  - >
    A test written for a new arm can pass while a mutant that deletes the arm also passes.
    It happened twice in this wave for two different reasons: _select_pair already requires
    both sides to agree on period_kind (so relabelling ONE side collapses the pair for a
    pre-existing reason), and _emit_result strips comparison_basis as an internal carrier
    (the contract field is `basis`). Run the mutation round; a green test is not evidence.
  - >
    Run a probe script from INSIDE the tree it is meant to measure. sweep3.py and
    proof8078.py root themselves at Path(__file__).parent, so executing a copy that lives
    in another tree silently measures that other tree - this produced a false regression
    report once in the previous wave.
  - >
    This worktree is SPARSE. Never run the full suite here; it yields thousands of
    artifact failures. The owned suite is the two files named in
    .github/ci/legacy-jobs.yml:5949.
  - >
    Widening an admitted vocabulary past the published contract does not extend the
    product, it authors invalid documents. Admission may be narrower than the contract and
    never wider.
prs: [8099]
discoveries:
  - "DSC:A-DECLARED-BASIS-IS-A-LABEL-UNTIL-SOMETHING-READS-IT"
  - "DSC:AN-ENUMERATED-GUARD-IS-BLIND-OUTSIDE-ITS-ENUMERATION"
---

## Why this wave existed

The previous handoff closed with a distinction that turned out to be the whole map:
"nothing ungated remains at this seat" was true about WIRING and false about CORRECTNESS.
Every defect repaired here sat inside `owns_paths`, needed no external gate, and was
reachable by anyone willing to test a claim the module made about itself.
