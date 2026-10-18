---
key: CS-V2-SHARE-BASIS-B1
question: >
  Masterplan task B1 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A16, A18, A19, A28, A48) needs one deterministic
  function, select_share_basis(observations, actions, as_of), that turns the
  frozen C0 ShareInputs and CorporateActionInputs into a ShareBasisResult.
  Which share facts may become the denominator, how are contradictions, stale
  facts and corporate actions handled, and what does the function refuse to do
  while the C0 contract has no corporate_actions input family yet?
answer: >
  engine/capital_structure/share_basis.py selects only an observed,
  common-stock, direct Company Facts common_shares_outstanding fact in unit
  shares at scale 1, visible at as_of (available_at, else public_available_at,
  else accepted_at, else end of the filed day). Public float, non-affiliate
  float and weighted-average EPS shares are recorded as rejected notes and are
  never a candidate, never a fallback and never compared by size (A16). The
  latest clean instant wins; two distinct clean values at that instant, or an
  unclean fact (deferred, contradicted, unit or scale mismatch) at that
  instant, is a conflict; an unclean fact after it, or a basis older than 150
  days at as_of, refuses as an old or unconfirmed share basis (review class 3).
  Superseded and corrected records drop out by their own relationships.
  Corporate actions are evaluated by evaluate_split_actions, which requires
  four separately observed stages for one action (authorization, vote,
  effective, exchange_adjustment; A18), one effective date across them, one
  ratio, one kind whose direction matches the ratio, the security class
  <issuer_id>:security:common_stock and an effective date strictly after the
  count and on or before as_of (A19). A split scales only that pre-split
  issued-and-outstanding count, by an exact fraction; a non-integral result
  refuses because fractional-share treatment is not modelled. A split
  effective on the count date, two applicable actions, a missing or duplicated
  stage, or any disagreement refuses. The split path runs only when the
  actions binding is the corporate_actions family and that family is in
  COMPATIBLE_INPUT_SCHEMAS; until the seat's C0 delta lands, the function uses
  the events family conservatively: a charter-amendment candidate filed after
  the count refuses, and a vote or authorization event is a note only, never
  an applied split. Family support is capped at partial with the nine B0
  support limits; every result carries a CalculationReceipt; no probability,
  score, rank or sizing field exists (A48).
rationale: >
  A16 and the review class 3 failure mode both come from choosing a share
  number because it is available, large or recent rather than because it is
  the right concept at the right date. Making the selectable concept a closed
  set and every other concept a rejected note removes the substitution path
  structurally. A19 fails when a split is applied to a count that already
  reflects it or to a different security, so the function demands a strictly
  later effective date, a matched security and four separately evidenced
  stages rather than inferring the split from a vote or a charter amendment.
  The conservative events path lets B1 ship now without forking C0, and the
  split path activates by itself when the accepted contract delta lands.
alternatives:
  - option: Fall back to public float or weighted-average shares when no outstanding count is clean
    why_not: REJECTED_BY_DESIGN. A16 forbids substitution; a missing basis is
      unavailable or refused, never a different concept.
  - option: Pick the largest or newest value when two clean facts disagree at one instant
    why_not: REJECTED_BY_DESIGN. A16 requires a conflict, not a tie-break.
  - option: Apply a split from a proxy vote, an authorization or a charter amendment filing
    why_not: A18 requires each stage separately evidenced; a vote does not
      prove an effective split or an exchange adjustment.
  - option: Add corporate_actions to COMPATIBLE_INPUT_SCHEMAS and the state schema inside B1
    why_not: The seat is the single writer of C0 deltas; B1 keeps the split
      path gated on the family and two end-to-end tests skipped until it lands.
  - option: Round a fractional post-split count
    why_not: Cash-in-lieu and rounding treatment are issuer-specific and not
      evidenced; a guessed count is worse than a refusal.
evidence:
  - engine/capital_structure/share_basis.py (select_share_basis, evaluate_split_actions, SplitDecision, RULES, RULE_DIGEST, SUPPORT_LIMITS)
  - tests/test_capital_structure_share_basis.py (fixtures validate against contracts/capital_structure_share_count_observation_v2.schema.json; every result round-trips validate_state_record share_basis_result)
  - engine/capital_structure/issuer_state_contracts.py (frozen C0 ShareInputs, CorporateActionInputs, ShareBasisResult, CalculationReceipt)
  - config/capital_structure_share_source_admission.v1.json (B0 support limits mirrored and pinned by a parity test)
affects:
  - engine/capital_structure/share_basis.py
  - tests/test_capital_structure_share_basis.py
  - .github/ci/legacy-jobs.yml (capital-structure-intelligence registration)
  - masterplan tasks D0, U0 and any consumer of a share denominator (read ShareBasisResult; never re-select)
confidence: high
reversibility: easy
decided_by: opus-o4-under-fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
review_by: 2026-11-14
---

# Share basis selection for Capital Structure V2 (B1)

A denominator is an observed issued-and-outstanding common-stock count at a
known instant, or nothing. Other share concepts are notes. Disagreement at the
selected instant is a conflict; anything newer and unclean, or anything older
than 150 days, refuses. A split is applied only from four separately evidenced
stages to a strictly earlier count of the matched security, by an exact ratio,
and only through the corporate_actions family once C0 admits it.
