---
workstream: "WS:PROPHET-US-V4-RECOVERY"
session: "01a11e89-b35d-7a81-9404-5fce2c6170cb / claude/ssd-prophet-source-status-copy-767522d27143674f"
model: codex
ended_because: ci_handoff
mission: >-
  Deliver the existing four-market Daily Desk, including native evidence and
  authenticated production journeys. Repair known source-code labels in the
  adopted detail consumer while the separate consumer PR8801 runs hosted CI.
state_before: >-
  Authenticated production MCK detail showed Unmapped status twice for stage
  live and lane continuation. Both are published board codes with existing
  bilingual board labels. This carrier starts from main
  c810578541dc4545ee912a548b0dc238d7140b66 and does not adopt held P1a source.
changed:
  - path: templates/_prophet_setup_detail.html.j2
    what: Completes the five known stage and five known lane labels using existing board wording, retaining the already accepted Developing and Base formation labels.
  - path: tests/test_prophet_card_shared.py
    what: Adds ten cases for the published code pairs across distinct Buy and Near entry reads, preserving raw fields, dates and source immutability.
prs: [8801, 8798, 8762]
verified:
  - claim: The new regression distinguishes missing code mappings from already supported labels.
    command: python3 -m pytest -q tests/test_prophet_card_shared.py -k recognizes_published_board_codes_without_rewriting_entry
    result: Eight RED failures and two passing controls before the template repair; all ten pass afterward.
  - claim: Affected card and Plan relation checks pass with the existing source/site runtime check exercised.
    command: python3 scripts/worktree_sparse.py add site; python3 -m pytest -q tests/test_prophet_card_shared.py tests/test_prophet_plan_relation.py -k 'not evidence_manifest and not plv_evidence_states'
    result: 70 passed, two unchanged capture-manifest checks intentionally deselected, zero skips. The first run had only a missing sparse site/theme.js failure; proper site materialization resolved it without changing that test.
  - claim: Existing unknown and absent source values remain distinct and entry reads are not rewritten.
    command: The same affected pytest invocation includes test_r22_neutral_status_names_preserve_exact_raw_fields_in_one_disclosure and the ten new source-code cases.
    result: Unknown codes retain Unmapped status, missing values retain Not supplied, raw stage/lane fields and entry status/headline/date remain unchanged.
  - claim: The copy-only delta adds no material styling or JavaScript system.
    command: python3 scripts/check_design_system.py --mode enforce-added --diff-file /Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89/source-status-copy-20261011.diff; python3 scripts/check_ui_visual_evidence.py --diff-file /Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89/source-status-copy-20261011.diff; python3 scripts/check_runtime_style_injection.py
    result: Design added-zero, visual guard passed, runtime budget unchanged at 212 files, 44 injecting files, 89 hits.
unverified:
  - claim: Independent source review, hosted CI, merge and served corrected labels are accepted.
    what_would_verify: Same-head scoped review and concluded canonical CI, normal expected-head release, generated publication and authenticated MCK source-detail readback.
unresolved:
  - B03 and entry-copy PR8798 are source-merged but still await combined render38137913516 and authenticated served acceptance. The cancelled predecessor did not commit or publish.
  - PR8801 is separate at2e6c220683cb026818485a719f5cdc2165ae1eac; preserve its accepted source and running CI38139213791/fences38139213539.
  - Candidate-to-related-Plan return affordance is a separately observed gap. A bounded coordinator advised implementing after8801 lands; preserve exact DOM/generation/access and never equate a same-security relation with an exact episode.
next_actions:
  - Obtain one scoped independent review and normal hosted proof for this carrier, then merge and verify authenticated known-status labels through the existing publication owner.
  - Continue PR8801 normal release and combined B03/8798 live proof under the same existing observer; do not synchronously poll pending runs.
do_not_redo:
  - Do not alter native stage or lane values, ranking, entry authority, clocks, price levels, populations, Plan identity or source producers for a presentation fix.
  - Do not reopen accepted B03, B04, B06, entry-copy or scoped P1a reviews and consumed CI.
  - Do not retry or reroute P1a8444 integration refusal6029541334 or DailyBrief8249 source refusal5924461491; preserve exact selection and scientific gates.
danger_areas:
  - Active setups is a grouping label, not entry clearance. Near still requires its own dated confirmation.
  - Source and CI acceptance do not prove a new generated site or authenticated production behavior.
---

The live MCK detail exposed the raw `live` and `continuation` values immediately
below two incomplete human labels. The repair completes only those existing
label dictionaries. It preserves source facts, unknown/missing distinctions,
progressive disclosure, both languages, and all entry/Plan disclaimers.

This work implements an observed native-evidence gap from the existing Studio
Paper assessment. It does not create another Daily Brief assembler, change
Paper, or transfer any held source lane. The authoritative moving delivery
frontier is the existing [programme checkpoint](https://github.com/mastermindx-market-intelligence/macro/issues/6817#issuecomment-6107291350).
