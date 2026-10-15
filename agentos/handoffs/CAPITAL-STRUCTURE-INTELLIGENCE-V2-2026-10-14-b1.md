---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-b1-share-basis
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task B1 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A16, A18, A19, A28, A48): ship
  engine/capital_structure/share_basis.py with
  select_share_basis(observations: ShareInputs, actions: CorporateActionInputs,
  as_of: str) -> ShareBasisResult on the frozen C0 contract, deterministic, no
  network, no collector, every result receipted, plus direct tests for
  contradictory dates, units and actions, review class 3 (old or unconfirmed
  share basis), A16 non-substitution and A18/A19 split evidence.
state_before: >
  C0 (issuer_state_contracts.py) and E0 (reference pack) on origin/main; B0
  share-source admission PR #9264 open and armed. C0 declared ShareInputs,
  CorporateActionInputs and ShareBasisResult but no selector existed, and
  COMPATIBLE_INPUT_SCHEMAS carried no corporate_actions family, so a
  four-stage split record had no admitted input family. The seat accepted a
  C0 delta adding corporate_actions to COMPATIBLE_INPUT_SCHEMAS, the
  input_schema enum and the state schema $defs.input_family, sequenced after
  #9266, with the seat as the single writer.
changed:
  - path: engine/capital_structure/share_basis.py
    what: >
      New deterministic selector. select_share_basis picks the latest clean
      observed common-stock common_shares_outstanding fact (unit shares, scale
      1) visible at as_of; public float, non-affiliate float and
      weighted-average EPS shares are rejected notes, never candidates;
      same-instant disagreement or an unclean fact at the selected instant is
      a conflict; an unclean later fact or a basis older than 150 days
      refuses; corrections and supersessions drop out. evaluate_split_actions
      (public, pure) requires four separately observed stages per action, one
      effective date, ratio, kind and security, effective strictly after the
      count and on or before as_of, and scales by an exact fraction (a
      non-integral result refuses). The split path runs only for the
      corporate_actions family once C0 admits it; the events family path
      refuses on a post-count charter-amendment candidate and treats votes and
      authorizations as notes. Support capped at partial with the nine B0
      limits; CalculationReceipt on every result; RULES and RULE_DIGEST
      published.
  - path: tests/test_capital_structure_share_basis.py
    what: >
      44 tests (2 skipped until the C0 corporate_actions delta lands): fixture
      schema validity against the v2 share-count schema, interface shape,
      latest-clean selection, DEI versus us-gaap instants, same-instant and
      unit contradictions, ambiguity, deferred and stale refusals, public
      float and EPS and non-affiliate rejection, point-in-time invisibility,
      correction supersession, authority-claim and mixed-issuer refusal, event
      path (charter amendment, vote, proxy), each split stage required,
      disagreeing ratio, unmatched security, effective before, on and after
      the window, ratio direction, unmodeled kind, two splits, non-terminating
      ratio, determinism, receipt digests, forbidden keys and B0 limit parity;
      every result round-trips validate_state_record.
  - path: .github/ci/legacy-jobs.yml
    what: Register the new suite in the capital-structure contracts step after the reference-qualification suite.
  - path: agentos/decisions/DEC-CS-V2-SHARE-BASIS-B1.md
    what: Record the selection law, the split evidence law and the conservative path pending the C0 delta.
verified:
  - claim: The new suite passes with the two end-to-end split tests skipped pending the C0 delta.
    command: /opt/homebrew/bin/python3.12 -m pytest tests/test_capital_structure_share_basis.py -q -p no:warnings
    result: 42 passed, 2 skipped.
  - claim: The C0 and E0 suites still pass beside it.
    command: >
      /opt/homebrew/bin/python3.12 -m pytest tests/test_capital_structure_share_basis.py
      tests/test_capital_structure_issuer_state_contracts.py
      tests/test_capital_structure_reference_qualification.py -q -p no:warnings
    result: 170 passed, 2 skipped (on base cb1c0ebb37d1).
  - claim: The suite is registered and no test is left unrun.
    command: python3 scripts/audit_unrun_tests.py
    result: exit 0.
  - claim: All twelve legacy packs validate after the registration edit.
    command: >
      python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml
      --pack-index N --pack-count 12 --validate-only, N = 0..11
    result: rc=0 for every pack.
unverified:
  - claim: Hosted ci.yml is green on the exact pushed head.
    what_would_verify: The ci.yml run for the pushed head concluding with every pack green (the Workers Builds X excluded).
  - claim: The positive A19 end-to-end path (four observed stages scaling a real count) runs in CI.
    what_would_verify: >
      The seat's corporate_actions C0 delta landing on origin/main, B1 rebased
      onto it, and test_end_to_end_split_scales_only_the_pre_split_matched_count plus the
      fractional case passing un-skipped.
  - claim: B1 is merged and landed on origin/main.
    what_would_verify: Squash-merge on concluded green, a bare git fetch and a per-path blob comparison against origin/main.
unresolved:
  - >
    ShareInputs carries no issuer identity, so the issuer is derived from the
    records and mixed issuers raise ShareBasisInputError.
  - >
    The corporate-action security class convention is
    <issuer_id>:security:common_stock; a producer of corporate_actions records
    must use it until C0 names a security-class identifier.
  - >
    Fractional-share treatment (cash in lieu, rounding) is not modelled; a
    non-integral post-split count refuses.
  - >
    The legacy-jobs.yml edit is a CI-authority change; one main ci.yml
    baseline is owed after merge, dispatched by the seat over a clear field.
  - >
    All fabric labor lanes were exhausted (GLM 429 until 2026-10-19, Grok and
    Codex unavailable), so O4 implemented B1 directly under the continuation law.
next_actions:
  - Merge B1 by hand with --match-head-commit on concluded green after checking reviewDecision; verify landing by blob comparison.
  - After the seat's corporate_actions delta lands, rebase B1 (or a follow-up) so the two end-to-end split tests run un-skipped.
  - Consumers of a share denominator read ShareBasisResult; they never re-select from raw share facts.
do_not_redo:
  - Add a public-float, non-affiliate or weighted-average fallback for a missing outstanding count.
  - Break a same-instant disagreement by size or recency.
  - Apply a split from a vote, an authorization, a charter amendment or a press release without all four observed stages.
  - Edit issuer_state_contracts.py or the state schema from a B-lane PR; the seat writes C0 deltas.
danger_areas:
  - The split path activates automatically when corporate_actions enters COMPATIBLE_INPUT_SCHEMAS; a producer emitting stage records with a different security_class_id convention will refuse every split.
  - _available_instant falls back to the end of the filed day when available_at, public_available_at and accepted_at are absent; a producer that omits all three shifts point-in-time visibility.
  - MAX_BASIS_AGE_DAYS (150) is part of RULE_DIGEST; changing it changes every receipt.
prs: [9277]
---

# Capital Structure V2 — B1 share basis handoff

select_share_basis is the only selector of a share denominator. Ship state at
write time: branch committed, PR to be opened NOT armed (CI-authority edit),
hand-merge with --match-head-commit on concluded green, then one main baseline
owed to the seat.
