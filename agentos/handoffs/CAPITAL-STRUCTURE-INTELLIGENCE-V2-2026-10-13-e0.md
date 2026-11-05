---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-e0-reference-qualification
model: fable
ended_because: ci_handoff
mission: >
  Masterplan task E0 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A07 and A09): qualify the exact reference documents,
  source policy, rights, issuer identities and labelled term/adjudication gold
  that later waves bind to, as one byte-exact machine-readable pack with a
  validating reader and tests, with no new collector and no guessed facts, and
  ship it through the ordinary chain.
state_before: >
  R1 CLOSED by the masterplan. R2 open as PR #9146 (head c443fa8fde62) and C0
  open as PR #9159 (head e7f1a2f0fe81), both red only on main's inherited
  ci-pack-0 until the heal PR #9141 merged at 2026-10-13T14:11Z (merged by the
  repository owner, not this seat); main has since concluded four green ci.yml
  runs that postdate the heal, so both PRs were updated from main at
  2026-10-14T04:4xZ with one watcher each. No V2 code recorded which edition
  of the SEC C&DI, which Nasdaq rule text, which release status of 33-11418,
  which registrant names or which gold fixture bytes the program relies on;
  the six archetype labels dated from the 2026-08-18 masterplan §16.
changed:
  - path: config/capital_structure_reference_pack.v1.json
    what: >
      New reference pack (capital_structure.reference_pack.v1,
      capital-structure-reference-qualification/1.0.0): 13 sources with url,
      retrieved_at, http_status, bytes and sha256 (SEC Securities Act Forms
      C&DI edition 2026-09-25 with six exact question spans 116.21-116.26 and
      interpretation dates; the 2026-03-19 C&DI update; Nasdaq 5600 Series
      browser-qualified after a plain-client HTTP 403, five excerpt-limited
      spans; Release 33-11418 as proposed_reform; 2026 rulemaking index; SEC
      developer fair access; company_tickers.json; six submissions indices),
      8 official rule examples (3 negative), 6 identity bindings (WHK label
      drift, case unsupplied, replacement owed), 11 gold fixtures by sha256
      with consumers and reviewed expectations, source policy and rights
      mirrored from docs/CAPITAL_STRUCTURE_INTELLIGENCE_CONTRACT.md, request
      policy (13 paced research-seat requests, reserves 500/20/20/540
      unchanged, no collector added), typed fact origins, four owned gaps and
      the requalification procedure.
  - path: engine/capital_structure/reference_qualification.py
    what: >
      Reader and validator: typed frozen records for sources, spans, rule
      examples, identity bindings and gold cases; span chars/sha256 and
      excerpt-cap checks; proposed_reform can never be enforceable or back an
      example; browser-qualified sources need a rendered receipt; identity
      label-drift law (drift flag must agree with the names, drifted labels
      need a former-name witness, an unsupplied case owes a replacement that
      is never guessed); gold path/sha256 law; fact-origin law; helpers
      load_reference_pack, verify_gold_fixtures, enforceable_sources,
      rule_sources, identity_for, rule_examples, qualification_report. No
      network code.
  - path: tests/test_capital_structure_reference_qualification.py
    what: >
      32 tests pinning the pack facts (editions, dates, 116.23 arithmetic,
      116.26 staff position, S-3/F-3 numbering, Nasdaq approval context,
      IM-5635-3 negative, WHK drift, reserves, rights, fact origins, gold
      hashes against the checked-in fixtures) and the tamper failures (span
      text, gold hash, drift flag, guessed replacement, reform enforceable,
      collector flag, LLM origin flag).
  - path: .github/ci/legacy-jobs.yml
    what: Register the new suite in the capital-structure contracts step.
  - path: agentos/decisions/DEC-CS-V2-REFERENCE-QUALIFICATION-E0.md
    what: Record what E0 qualified, the gaps it owns and what later waves may not do.
verified:
  - claim: The pack loads, every gold fixture hash matches the checked-in bytes, and the new suite passes.
    command: /opt/homebrew/bin/python3.12 -m pytest tests/test_capital_structure_reference_qualification.py -q
    result: 32 passed in 1.74s.
  - claim: The two existing capital-structure suites that share the registration step still pass apart from one local-interpreter fingerprint test family.
    command: >
      /opt/homebrew/bin/python3.12 -m pytest
      tests/test_capital_structure_reference_qualification.py
      tests/test_capital_structure_legacy_compat.py
      tests/test_capital_structure_document_terms.py -q
    result: >
      184 passed, 2 failed; both failures are the [cpython-3.12.2-python-org]
      parametrisation of
      test_clean_preimport_forged_stdlib_method_imports_but_parser_fails_closed
      and test_clean_preimport_forged_html_helper_imports_but_parser_fails_closed,
      which spawn the local python.org 3.12.2 interpreter whose document-term
      parser runtime fingerprint is not released on this host (ValueError
      "document-term parser runtime fingerprint is not released"). This branch
      does not touch engine/capital_structure/document_terms.py.
  - claim: The new suite is registered and no test is left unrun.
    command: python3 scripts/audit_unrun_tests.py
    result: exit 0 (two pre-existing stale-baseline warnings unrelated to this change).
  - claim: All twelve legacy packs validate after the registration edit.
    command: >
      python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml
      --pack-index N --pack-count 12 --validate-only, N = 0..11
    result: rc=0 for every pack.
  - claim: The Agent OS records validate.
    command: python3 scripts/agentos.py validate
    result: exit 0 with the decision and this handoff present.
unverified:
  - claim: Hosted ci.yml is green on the exact pushed head.
    what_would_verify: The ci.yml run for the pushed head concluding with every pack green (the Workers Builds X excluded).
  - claim: The two document_terms failures are environment-only.
    what_would_verify: >
      The same two tests passing in hosted CI on this head, or failing
      identically on origin/main in this host environment.
  - claim: E0 is merged and landed on origin/main.
    what_would_verify: >
      Squash-merge on concluded green, then a bare git fetch and a per-path
      blob comparison of the five changed paths against origin/main.
  - claim: A later wave consumes the pack instead of re-qualifying by prose.
    what_would_verify: >
      L0 reading rule_examples and the binding_form_instruction_text gap, T0
      reading fact_origins, G0 reading gold_cases, each by import of
      engine.capital_structure.reference_qualification.
unresolved:
  - >
    Four owned gaps: binding_form_instruction_text (L0 must qualify the
    current 17 CFR 239.13 / 239.33 edition and effective date before encoding
    applicability beyond the official examples), whk_replacement_issuer (WHK
    is WhiteHawk Minerals Corp. with no S-3-family registration; the old
    witness is preserved and a sourced replacement is owed),
    foreign_issuer_f3_witness and held_out_pattern_witness (§10 requires one
    foreign-issuer form/venue case and one held-out pattern).
  - >
    The raw retrieved bodies (SEC pages, Nasdaq rendered text, submissions
    JSON) are not committed; the pack carries their sha256, byte counts and
    retrieval times, and the requalification_procedure re-derives them.
  - >
    The workstream record (decisions and handoffs lists, next_action) is not
    patched here; a records PR after #9146, #9159 and this PR merge owes it,
    together with prs lists on the r2/c0/e0 handoffs and the stale r2 line
    about the Company Facts head-witness test.
  - >
    The legacy-jobs.yml edit is a CI-authority change; one main ci.yml
    baseline is owed after merge, dispatched only over a clear field, and may
    cover #9146, #9159 and this PR together.
  - >
    Fabric lane hosts were ineligible or scarce; the Opus domain
    suborchestrators O1-O6 are not yet spawned, so the seat executed E0
    directly under the continuation law.
next_actions:
  - Merge E0 by hand with --match-head-commit on concluded green after checking reviewDecision; verify landing against origin/main by blob comparison.
  - Hand-merge #9159 and #9146 the same way once their post-update runs conclude green; then preflight and dispatch ONE main ci.yml baseline over a clear field.
  - Open the records PR (workstream record refresh, prs lists, r2 handoff correction).
  - Start T0 (deps E0, C0) and L0 (deps E0, C0; consumes rule_examples and owns the binding_form_instruction_text gap), then B0 (R0, E0) and F0 (E0, C0) per §13.
  - Spawn the Opus domain suborchestrators when host_pick admits hosts.
do_not_redo:
  - Re-fetch or re-hash the thirteen sources without recording a new edition witness; a changed span hash is a new edition, not a correction.
  - Reuse the 2026-08-18 WHK label (WhiteHawk Income Corp) as a supplied case, or guess a replacement issuer without source_ids.
  - Mark Release 33-11418 enforceable or back a rule example with it; it is proposed_reform.
  - Add a collector, raise an SEC request reserve, or let a nightly lane fetch these reference pages.
  - Commit the full Nasdaq rulebook text or any span above 500 characters from an excerpt-limited source.
  - Dispatch daily.yml to manufacture proof, lift the #8673 UI hold by inference, or heal ci-pack-0 inside a capital-structure PR.
danger_areas:
  - verify_gold_fixtures resolves paths against the repository root; in a sparse worktree every gold path is under tests/fixtures and present, but a fixture edit anywhere changes a hash the pack pins.
  - The C&DI spans are exact text extracted from the 2026-09-25 edition; whitespace normalisation in the extractor is part of the span identity, so a re-extraction must use the same normalisation to compare hashes.
  - IdentityBinding.label_drift is derived from normalised names (casefold, punctuation stripped); a registrant that changes only punctuation is not drift, a suffix change is.
prs: [9244]
---

# Capital Structure V2 — E0 reference qualification handoff

The reference pack in config/capital_structure_reference_pack.v1.json is the only
binding a later wave may read reference documents, staff examples, issuer identities
and gold expectations from; read it through engine.capital_structure.reference_qualification.
Ship state at write time: branch pushed, pull request open and NOT armed (CI-authority
edit), hand-merge with --match-head-commit on concluded green, then one main baseline.
