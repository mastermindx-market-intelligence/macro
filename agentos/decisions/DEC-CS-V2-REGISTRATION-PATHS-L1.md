---
key: CS-V2-REGISTRATION-PATHS-L1
question: >
  Masterplan task L1 row L1a (research/capital_structure/e2e_20261013/MASTERPLAN.md,
  acceptance rows A10, A11, A20 and A23; depends on L0 and on the sealed
  registration lifecycle compiler) must turn observed SEC registration history
  into registration paths that C1 can read without any of them becoming a
  capacity claim. Which of the eight registration facts may be inferred from
  accepted inputs, what does a `supersedes` edge mean, may a precompiled
  lifecycle bundle be re-cut to another house-knowledge cutoff, and on what
  evidence may a Rule 415(a)(5) shelf window be called conditional?
answer: >
  One module, engine/capital_structure/registration_integration.py
  (capital-structure-registration-integration/1.0.0), emits one
  capital_structure.registration_path.v1 record per lifecycle record and answers
  eight DISTINCT predicates -- filed, effect_observed, automatic_shelf_form,
  automatic_effectiveness, offering_role, withdrawn, replaced, shelf_window --
  each with a closed status (observed, not_observed, unknown, not_applicable,
  conditional), its own evidence event ids and accessions, a snake_case reason
  and the rule ids it actually consulted. No predicate alone, and no combination
  of them, carries an amount, a remaining dollar figure or an executable-offering
  claim. offering_role stays value+status `unknown` on every path with reason
  `no_accepted_content_evidence_lifecycle_carries_no_primary_or_resale_classification`:
  primary versus resale is accepted-content evidence the lifecycle deliberately
  does not carry, and a form type never implies one. replaced stays `unknown` on
  every path with reason `rule_415_a_6_carry_forward_rows_not_extracted`, because
  Rule 415(a)(6) carry-forward rows are registration fee-table rows and not a
  document_terms TERM_NAME; a `supersedes` edge is event-version supersession of
  one SEC observation and is never read as a replacement. An automatic shelf form
  token (S-3ASR, F-3ASR, POSASR) is a form fact only
  (`form_fact_only_not_wksi_status`), never WKSI status; automatic_effectiveness
  is `not_applicable` without such a form, `conditional` when the rule pack
  holds cfr.17.230.462.e as verified or bracketed on the origin filing date, and
  `unknown` (`rule_462_e_text_not_in_rule_pack`) otherwise. A precompiled
  lifecycle bundle cannot be re-cut: a bundle whose `as_of` differs from the
  requested house-knowledge cutoff is refused, not filtered, and when
  events+edges are bound beside a bundle the recompiled `records` must be
  canonically equal to the bound ones or the call is refused naming both digests
  (generation_id is never compared, it binds generated_at). The events+edges
  source exists only when BOTH ledgers are bound (spec A.2(5)): events bound
  supported or partial with no event_edges binding and no bundle is refused,
  while an event_edges ledger bound as unavailable or not_built yields an
  unavailable registration family with no records. shelf_window is `not_applicable` outside the
  S-3/F-3/F-10 families and `conditional` only when an initial effectiveness date
  exists -- the earliest EFFECT acceptance, or for an automatic shelf whose
  462(e) answer is itself conditional the origin filing date, carrying the extra
  condition `wksi_status_not_evaluated` -- AND the rule pack holds
  cfr.17.230.415.a.5 as verified or bracketed on that start date (not on the
  as_of date). The window is then
  start plus three calendar years with a Feb-29 start clamped to Feb-28, a
  position of inside_window or after_window_end at the as_of date, and four
  standing conditions naming everything that was not evaluated. Every interval
  keeps valid time (valid_from/valid_to from SEC acceptance) apart from house
  knowledge (known_from/valid_to_known_from from mastermind_available_at), and
  registration_path_at answers valid time only.
rationale: >
  C1 reads these predicates to decide what it may say about a registration. If
  an EFFECT notice, an ASR form token or a shelf window could be combined into a
  capacity fact, a false capacity claim would reach a user with a receipt behind
  it, which is worse than no claim at all -- so each predicate is separately
  evidenced and the closed authority block (is_context_only true, every
  instrument/capacity/risk/probability/rank/sizing/entry/trade/prophet authority
  false) is re-proved on every record. Keeping unknown as a first-class answer
  rather than 0 or infinity is A20: the L0 pack 1.0.0 carried no cfr.17.230.415.*
  and no cfr.17.230.462.e rule at all, so every shelf window and every automatic
  effectiveness answered unknown with a named reason; L1b's pack 1.1.0 qualifies
  both from 2005-12-01 through the last served edition (2026-10-09), and the
  answers moved to conditional with no code change here, while a start date the
  pack does not cover (before 2005-12-01, or after 2026-10-09) still answers
  unknown. Separating valid
  time from house knowledge is A11: the SEC accepted an effectiveness notice on
  one clock and Mastermind observed it on another, and an earlier as_of must
  recompile to exactly the then-known facts, never to a retroactive later fact.
  Refusing to re-cut a precompiled bundle keeps one artifact's generation_id
  bound to the cutoff it was actually compiled at; filtering its timeline would
  publish a cutoff the sealed compiler never produced, with a defer ledger and a
  coverage state that no longer describe it.
alternatives:
  - option: Infer offering_role from the form type (S-1/S-3 primary, 424B5 resale)
    why_not: >
      REJECTED_BY_DESIGN. A form token is not accepted content evidence; A23 and
      A10 forbid it, and the lifecycle compiler already defers prospectus forms
      whose financing meaning depends on document content.
  - option: Read a `supersedes` edge as a Rule 415(a)(6) replacement
    why_not: >
      `supersedes` is event-version supersession of one SEC observation (the same
      accession at correction_version 2). Carry-forward replacement is a fee-table
      row that no TERM_NAME extracts, so reading the edge as replacement would
      mint a fact from the wrong ledger.
  - option: Re-cut a precompiled bundle to the requested as_of by filtering its timeline
    why_not: >
      The bundle is a sealed artifact whose generation_id binds its own as_of,
      coverage and defer ledger. Filtering it would publish a house-knowledge
      cutoff the compiler never produced; binding events+edges recompiles it for
      real instead.
  - option: Answer a shelf window from the current Rule 415(a)(5) text, or as open-ended
    why_not: >
      A20: unknown is never 0 and never infinity. The L0 pack qualifies no 415
      text, so an answer would be a guessed rule; an open-ended window would read
      as perpetual capacity.
  - option: Let automatic_shelf_form imply automatic_effectiveness
    why_not: >
      Rule 462(e) turns on WKSI status at the determination date, which is house
      knowledge no accepted input carries; wksi_eligibility stays unavailable and
      the most the module may say is conditional with the reason named.
evidence:
  - engine/capital_structure/registration_integration.py (integrate_registration_paths, registration_path_at, RegistrationIntegration.family_state, the eight predicates and the closed AUTHORITY block)
  - tests/test_capital_structure_registration_integration.py (26 tests; the A10/A11/A20/A23 cases, the recursive FORBIDDEN_PROPERTY_PATTERN key-and-value walk, the events-versus-precompiled source-selection refusals including the half-bound events/edges pair, the textless and stub-pack window dates, and two B.5 cross-tests against the real pack 1.1.0)
  - config/capital_structure_rule_applicability_pack.v1.json (1.0.0 carried no cfr.17.230.415.a.5 and no cfr.17.230.462.e rule; 1.1.0 from L1b holds both as verified from 2005-12-01 to 2026-10-09 and beyond_window after it)
  - engine/capital_structure/registration_lifecycle.py (compile_registration_lifecycles, validate_registration_lifecycle_bundle, the record/timeline/coverage/defer shapes read but never reimplemented)
  - DEC:CS-V2-RULE-APPLICABILITY-L0 (the as-of states verified/bracketed/beyond_window/withheld/not_in_force that shelf_window and automatic_effectiveness consume)
affects:
  - engine/capital_structure/registration_integration.py
  - tests/test_capital_structure_registration_integration.py
  - .github/ci/legacy-jobs.yml
  - masterplan task C1 (consumes registration paths and their predicates; never re-derives one, and never reads a predicate as capacity)
  - masterplan task L1 rows L1b and L1c (the Rule 415(a)(4)/415(a)(6) and Section 10(a)(3) text that would move shelf_window and replaced off unknown)
confidence: high
reversibility: easy
decided_by: claude/cs-v2-l1a-registration-paths
decided_at: 2026-10-14
review_by: 2026-11-14
---

# Registration paths for Capital Structure V2 (L1a)

Eight predicates, each separately evidenced, none of them a capacity fact.
`offering_role` and `replaced` stay unknown until accepted content evidence and
Rule 415(a)(6) carry-forward rows exist; a `supersedes` edge is version
supersession, never replacement. A precompiled bundle is either cut at the
requested house-knowledge cutoff or refused. A shelf window is conditional only
on pack-qualified Rule 415(a)(5) text plus an observed initial effectiveness
date, and it is a date bound with named conditions, never an amount.

One known naming gap is kept on purpose. The frozen spec gives a single reason,
`rule_415_a_5_text_not_in_rule_pack` (and `rule_462_e_text_not_in_rule_pack`),
both for a pack that lacks the rule and for a pack that carries it but holds it
as beyond_window or not_in_force on the start date. With pack 1.1.0 that second
case is real (a window that starts after 2026-10-09 answers unknown with this
reason although the text is present). The status, unknown, is right; the
reason name overstates the cause. This module follows the spec literally and a
test pins the behaviour; a distinct reason for the not-covered-on-that-date case
is a follow-up spec change, not a silent rename.
