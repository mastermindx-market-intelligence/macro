---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-l1b-rule-pack-415
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task L1, packet L1b (research/capital_structure/e2e_20261013/
  MASTERPLAN.md, acceptance rows A12, A13, A14 and A20; depends on L0):
  retrieve the primary-source text of 17 CFR 230.415(a)(1)(x), (a)(4), (a)(5)
  and (a)(6), 17 CFR 230.462(e) and Securities Act Section 10(a)(3), qualify it
  into the L0 rule-applicability pack as version 1.1.0 with byte-traceable
  provenance, attempt the pre-2016 Form S-3/F-3 editions, and leave the two L0
  gaps in an evidence-true state. No pull request.
state_before: >
  L0 landed on branch claude/cs-v2-l0-rule-applicability at
  6d5871500760acd2379d81528dc4bec89e833f2d with pack
  capital-structure-rule-applicability/1.0.0: 22 sources, 30 spans, 18 rules,
  the eight E0 examples and two gaps owed by L1. Nothing in the pack carried
  Rule 415 or Section 10(a)(3) text, so L1a's three-year shelf-window predicate
  (Rule 415(a)(5)) and its automatic-effectiveness predicate (Rule 462(e)) had
  no qualified text to become conditional against.
changed:
  - path: config/capital_structure_rule_applicability_pack.v1.json
    what: >
      Reissued as capital-structure-rule-applicability/1.1.0 (schema id, file
      name and "task": "L0" unchanged; sha256
      2be52749456bddcd54bdfe973268b933313e11763f23d227688875efba2417e3). Now 38
      sources, 78 spans, 24 rules, 18 findings. Six new binding rules:
      cfr.17.230.415.a.1.x, cfr.17.230.415.a.4, cfr.17.230.415.a.5,
      cfr.17.230.415.a.6, cfr.17.230.462.e and usc.15.77j.a.3, all
      binding_class binding_rule, enforceable true, form null, instruction null,
      reference_span_labels and required_issuer_facts empty,
      interpretation_date null. 16 new sources (the two edition indices, the
      current 2026-10-09 edition and every point-in-time edition each index
      lists for both sections, Release 33-8591 with its pdftotext -layout 24.02.0
      derived text, and the govinfo USCODE-2024-title15 granule). 48 new spans:
      17 stored texts and 31 same_as edition aliases. Windows: point at
      2005-12-01 plus bracket 2005-12-01..2016-11-21 on the release span for all
      five CFR rules; version_index 2016-11-21..2026-10-09, split into
      2016-11-21..2020-07-31 and 2020-08-01..2026-10-09 for (a)(1)(x) and into
      2016-11-21..2022-01-30 and 2022-01-31..2026-10-09 for (a)(6); a single
      point at 2026-10-14 for 77j(a)(3). not_in_force_before 2005-12-01 for the
      three provisions the release ADDS - (a)(5), (a)(6) and 462(e); withheld
      with not_in_force_before null for (a)(1)(x) and (a)(4), which the release
      REVISES, and for 77j(a)(3). Gap
      rule_415_and_section_10_a_3_text closed with closed_by L1; gap
      pre_2016_form_editions left open with a four-row attempts list.
      request_policy: requests_made 37 to 60, refused_requests 15 to 18, and a
      new l1_requests list with one row per request including the refusals.
  - path: engine/capital_structure/rule_applicability.py
    what: >
      RULE_APPLICABILITY_PACK_VERSION changed from
      capital-structure-rule-applicability/1.0.0 to
      capital-structure-rule-applicability/1.1.0 and nothing else. The reader
      already expressed every fact L1b needed, so no parser change was made.
  - path: tests/test_capital_structure_rule_applicability.py
    what: >
      88 tests (53 L0 plus 35 appended). New: pack version 1.1.0 parses and the
      33-11418 exclusion survives; a rule-shape test per new rule id; one
      rule_status_as_of ladder per new rule id (verified at the 2026-10-09
      edition, bracketed inside the release-to-eCFR interval, not_in_force on
      2005-11-30 for the three added provisions, withheld on 2005-11-30 for the
      two revised ones, beyond_window after the last window end); window
      ordering, window-to-span sha pinning and the not_in_force_before equals
      first-window-start invariant; the bracket is earned by a shared
      normalized_digest between the release span and the 2016-11-21 span; the
      release text separates "Revise paragraph (a)(1)(x)" and "Revise paragraph
      (a)(4)" from "Add paragraph (a)(5)", "Add paragraph (a)(6)" and "adding
      paragraphs (e) and (f)"; span digest recomputation for all 48 new spans
      with same_as resolution; a per-served-edition span exists and only
      (a)(1)(x) and (a)(6) change across editions; the 2026-10-14 refusal means
      no point at today; the 23-row request log with its three refusals; the
      closed gap under report["closed"] with closed_by L1; the open gap's four
      attempts; and build_rule_pack gains the new rules at 2026-10-14 with no
      unknowns while at 2005-01-01 the three added rules are absent rather than
      unknown. One existing line changed by orchestrator ruling: the open-gap
      set literal in test_gap_report_names_open_l1_debts.
  - path: agentos/decisions/DEC-CS-V2-RULE-PACK-415-L1.md
    what: The decision record for the L1b qualification and the five alternatives it rejected.
verified:
  - claim: The five named capital-structure suites pass on this head.
    command: >
      PYTHONPATH=. /home/longr/lanes/venvs/w12-flaky-31213/bin/python3 -m pytest -q
      tests/test_capital_structure_rule_applicability.py
      tests/test_capital_structure_registration_lifecycle.py
      tests/test_compile_capital_structure_registration_lifecycles.py
      tests/test_capital_structure_term_integration.py
      tests/test_capital_structure_issuer_state_contracts.py
    result: >
      2 failed, 243 passed. Both failures are
      tests/test_compile_capital_structure_registration_lifecycles.py::
      test_disk_compiler_verifies_generation_and_writes_receipt_bound_artifact
      and ::test_failed_upstream_receipt_verification_preserves_last_good_output,
      and both fail identically at the pristine base commit
      6d5871500760acd2379d81528dc4bec89e833f2d in a separate worktree, so they
      are pre-existing and out of L1b scope.
  - claim: The rule-applicability suite itself is fully green.
    command: >
      PYTHONPATH=. /opt/homebrew/bin/python3.12 -m pytest -q
      tests/test_capital_structure_rule_applicability.py
    result: 88 passed, 14 warnings in 2.52s (O2 re-run after the page-folio review repair).
  - claim: agentos records validate with no errors.
    command: /home/longr/lanes/venvs/w12-flaky-31213/bin/python3 scripts/agentos.py validate
    result: >
      agentos: 1794 records (96 workstreams, 481 decisions, 521 discoveries, 696
      handoffs) - 0 error(s), 149 warning(s); exit 0.
  - claim: The CI pack that owns the capital-structure-intelligence job validates.
    command: >
      /home/longr/lanes/venvs/w12-flaky-31213/bin/python3 scripts/run_ci_pack.py
      --workflow .github/ci/legacy-jobs.yml --pack-index 8 --pack-count 12
      --validate-only --scope-mode off
    result: >
      Validated 317 legacy jobs; 317 in scope (full suite: changed-file set
      unavailable); pack weights=[1400, 897, 896, 897, 897, 897, 896, 896, 896,
      896, 896, 896]; selected pack 8 (31 jobs). Exit 0. Pack 8 is the one whose
      selected jobs include capital-structure-intelligence, the job that lists
      tests/test_capital_structure_rule_applicability.py at
      .github/ci/legacy-jobs.yml:6864.
  - claim: Every span's text is a byte-faithful extraction from bytes retrieved this run.
    command: >
      test_l1_span_digests_recompute_from_the_retrieved_bytes,
      test_l1_windows_are_ordered_and_pinned_to_their_span and
      test_l1_every_served_edition_has_its_own_span
    result: >
      All 48 new spans recompute sha256(text) == span.sha256,
      normalized_digest(text) == span.normalized_sha256 and len(text) == chars;
      all 31 same_as aliases resolve to a stored span with identical digests;
      every window sha equals its span's sha.
unverified:
  - claim: Hosted ci.yml is green on the exact pushed head.
    what_would_verify: The ci.yml run for the pushed head concluding with every pack green (the Workers Builds X excluded).
  - claim: Hosted check_contract_delta.py --base origin/main is green.
    what_would_verify: >
      It is red on this head with exactly one introduced error, and it is red in
      the same way at the pristine base commit (see the verified claim below), so
      a green run needs the leadership-rotation-science paths: widening that
      .github/ci/legacy-jobs.yml:11632 owes - a CI-authority edit L1b does not
      own.
  - claim: check_contract_delta.py's one introduced error is pre-existing and not caused by L1b.
    command: >
      /home/longr/lanes/venvs/w12-flaky-31213/bin/python3
      scripts/check_contract_delta.py --base origin/main, run once in this
      worktree and once in a separate detached worktree at
      6d5871500760acd2379d81528dc4bec89e833f2d with the same sparse profile
    result: >
      Both runs print the identical single error - "leadership-rotation-science:
      import closure now reaches engine/rates_command_basis.py, which
      .github/ci/legacy-jobs.yml's declared paths: for leadership-rotation-science
      does not cover - widen leadership-rotation-science's paths: to include
      engine/rates_command_basis.py (widening is always the safe direction)" -
      and both report "1 introduced, 0 inherited (base 9b4bd85aa4f0)". Head wall
      208.6 s, base wall 209.9 s. L1b touches no Python import graph: only the
      pack JSON, one string constant, one test file and two agentos records.
  - claim: The two pre-existing registration-lifecycle compile failures are environmental rather than a real regression.
    what_would_verify: >
      They reproduce at the base commit in a clean worktree with the configured
      sparse profile applied, and their failure is an event immutable identity
      digest mismatch in engine/capital_structure/registration_lifecycle.py:179,
      a file L1b does not touch. A full (non-sparse) checkout run would confirm
      whether a data/ fixture is the cause.
unresolved:
  - >
    pre_2016_form_editions stays OPEN. sec.gov serves only the current (02-25)
    editions: /about/forms/forms-3.pdf and /about/forms/formf-3.pdf are
    byte-identical to the already qualified form_s3_pdf and form_f3_pdf sources,
    /about/forms returns HTTP 301 to its CDN, and /about/forms/ returns the
    "Directory Browsing Not Allowed Here." page. No archive.org or third-party
    mirror was used, so the four-request budget closed nothing.
  - >
    The pre-2005-12-01 text of 415(a)(1)(x) and 415(a)(4) is not qualified. The
    release revises both, so earlier days answer withheld, never not_in_force
    and never verified.
  - >
    15 U.S.C. 77j(a)(3) is verified only on 2026-10-14. The govinfo granule
    prints "United States Code, 2024 Edition" with no "current through" line and
    no edition date, and the enactment history of paragraph (a)(3) was not
    retrieved, so every other day answers withheld.
  - >
    No CFR provision is verified at today. full/2026-10-14/title-17.xml returned
    HTTP 404 for both sections, so the last verified CFR day is the title-17
    up_to_date_as_of date 2026-10-09 and later days answer beyond_window with a
    requalify condition.
  - >
    The Federal Register page for Release 33-8591 itself is not encoded. The
    retrieved PDF prints no FR citation; only the eCFR source notes were
    retrieved (70 FR 44812 for 230.415, 70 FR 44818 for 230.462, both Aug. 3,
    2005).
next_actions:
  - L1a consumes rule_status_as_of for cfr.17.230.415.a.5 and cfr.17.230.462.e; the three-year shelf window and automatic effectiveness are verified 2016-11-21..2026-10-09, bracketed 2005-12-01..2016-11-20 and not_in_force before 2005-12-01.
  - C1 and G0 consume the same as-of states; a day after 2026-10-09 must requalify before it is relied on.
  - Whoever owns the pre-2016 form editions needs a source that actually prints an older "SEC #### (mm-yy)" label; sec.gov does not serve one.
  - The leadership-rotation-science paths: widening and the two registration-lifecycle compile failures belong to their own owners, not to L1b.
do_not_redo:
  - Do not re-derive 415 or 462(e) text from prose, a secondary site or a mirror; the pack's spans are the authority and their sha256 is recomputed by the tests.
  - Do not mark 415(a)(1)(x) or 415(a)(4) not_in_force before 2005-12-01; Release 33-8591 revises them, it does not add them.
  - Do not add a point window at a date the eCFR refused. full/2026-10-14 returned HTTP 404 for both sections.
  - Do not assume a paragraph is unchanged across editions; (a)(1)(x) changes at 2020-08-01 and (a)(6) at 2022-01-31.
  - Do not encode Release 33-11418 or 70 FR 44722 as retrieved fact; neither was retrieved.
  - Do not create a second source entry for the /about/forms/ alias downloads; they are byte-identical to form_s3_pdf and form_f3_pdf and are recorded in the gap's attempts list instead.
danger_areas:
  - RULE_APPLICABILITY_PACK_VERSION and the pack's "version" must move together or load_rule_applicability_pack refuses the file.
  - Every window sha256 must equal the sha256 of the span it names; editing a span's text without re-deriving its windows breaks loading, and the same_as aliases must keep matching their target's three digests.
  - not_in_force_before must equal the first window's start when before_first_window is not_in_force, and must be null otherwise.
  - Windows must be ordered by start; a text change splits a version_index window at the change date, with the earlier window ending the day before.
  - The pack still pins the E0 reference file sha256; any E0 edit forces requalification.
---

# Capital Structure V2 - L1b rule pack handoff

The L0 pack is now 1.1.0 with Rule 415(a)(1)(x), (a)(4), (a)(5) and (a)(6),
Rule 462(e) and 15 U.S.C. 77j(a)(3) qualified from retrieved primary-source
bytes. Every paragraph was compared across every served eCFR edition instead of
being assumed identical, and two of them do change. The bracket from the
adopting release to the first served edition is earned per provision by a shared
normalized digest. Ship state at write time: branch committed and pushed, no
pull request opened, per packet instruction.
