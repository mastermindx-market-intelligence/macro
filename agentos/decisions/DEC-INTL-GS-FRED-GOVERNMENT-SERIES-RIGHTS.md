---
key: INTL-GS-FRED-GOVERNMENT-SERIES-RIGHTS
question: >
  May the International Markets source-rights matrix (config/intl_source_rights_matrix_v1.json)
  carry direct_display_ok rows for the FRED-hosted US-government-authored series IM16 needs
  (DTWEXBGS — Board of Governors broad dollar index; DFII10 — Treasury 10y real yield), and
  what happens to the ICE BofA EM OAS series (BAMLEMCBPIOAS, BAMLEMRACRPIASIAOAS, BAMLEMRLCRPILAOAS)?
answer: >
  PROPOSED, not decided. The seat proposes (a) two rows `fred.board_dollar_index_dtwexbgs` and
  `fred.treasury_real_yield_dfii10`, rights_class direct_display_ok, auth_class keyless_public,
  capability dollar_funding_external / local_rates_credit, scope limited to the user-facing
  International surveillance views, on the basis that both series are US federal government
  works republished by FRED without third-party licence; (b) the three ICE BofA series stay
  WITHOUT a row (rights_unconfirmed) because FRED republishes them under an ICE Data Indices
  licence that restricts redistribution. Until the Chairman confirms (a) once, no row is added,
  IM16 keeps reporting rights_unconfirmed for all five series, and no engine or view claims
  rights it does not hold. This record changes no file in config/.
rationale: >
  The IM11 matrix lists every FRED family as `unresolved / decision_required` ("confirm
  FRED/OECD redistribution terms"), and the IM16 engine states in its own docstring that
  adding a rights row is a rights decision the contract is forbidden from making. The
  2026-10-09 Chairman redistribution ruling covered the Yahoo EOD index/FX family only. A
  rights classification that governs what the public site displays is a consequential
  decision held by the Chairman in every prior instance in this matrix, so the seat records
  the proposal with its evidence and asks once rather than minting rights or waiting silently.
alternatives:
  - option: Add the two rows now under the seat's programme delegation.
    why_not: >
      Redistribution rights are a legal exposure of the company, not an in-programme product
      choice; every existing decided row names a Chairman decision_ref.
  - option: Leave the gap unrecorded and let IM16 abstain forever.
    why_not: >
      The dollar-funding and local-rates capabilities are the heart of IM16 (masterplan §7);
      an unrecorded abstention would silently shrink the product.
evidence:
  - "config/intl_source_rights_matrix_v1.json rows fred.oecd_mirror_rates / fred.oecd_mirror_macro: rights_class unresolved, review.status decision_required (main 63f3bc83)"
  - "PR 9944 engine/intl_global_dollar_credit.py L11–17, L84–86: no rights-matrix row names DTWEXBGS, DFII10 or any ICE BofA series; rights_ref None by fact"
  - "FRED series pages: DTWEXBGS source Board of Governors of the Federal Reserve System (US); DFII10 source Board of Governors / Treasury; BAMLEM* source Ice Data Indices, LLC (licence terms on the series page) — to be re-read by the confirming party, not assumed"
  - "ORCH-3 return 2026-10-21 ~08:1xZ, NEXT SEAT ACT 3: rights rows for DTWEXBGS/DFII10 (and BAMLEM if licensed)"
affects:
  - "config/intl_source_rights_matrix_v1.json (two rows, only after confirmation)"
  - "engine/intl_global_dollar_credit.py rights_ref wiring (follow-up fabric lane after confirmation)"
  - "IM16 acceptance matrix counts for dollar_funding_external and local_rates_credit"
confidence: medium
reversibility: easy
decided_by: fable-meta-ceo-seat-d7c4f490 (proposal only; confirmation reserved to the Chairman)
decided_at: 2026-10-21
review_by: 2026-11-04
---

## Scope

A proposal record. It adds no row, grants no right and changes no engine behaviour. The
confirming act is one Chairman answer ("confirm FRED US-government series rows" or "no");
on yes, a bounded fabric lane adds the two rows with this record as `decision_ref`, wires
`rights_ref` in `engine/intl_global_dollar_credit.py`, and re-runs the IM16 suite. On no,
IM16 keeps its honest `rights_unconfirmed` abstention and this record is marked declined.

## Why ask now

IM16 (#9944) ships with the dollar-funding and local-rates capabilities abstaining for all
63 jurisdictions. The abstention is correct given the matrix, and the matrix itself already
flags the FRED families as a decision that was never taken. Recording the proposal at the
Wave 3 boundary keeps the question visible without stalling Waves 4–5, which do not depend
on it.
