# Post-run calculation audit

The first completed result was SHA256 `e7f13e4e06bb61d178f071f583b719d71a3f46cdaf0c4fac2090174ee464cfd1`. Its fixed membership receipt was `88421899efd56f2d101e60d7fbdd48de0c86c58f3f5739224d2782e225eb16b5`. All accepted reconstruction controls and the original 17-date / 82-of-102-slot feasibility control passed.

Two reporting/reproducibility refinements were made after inspecting that output:

1. Identical date cohorts now share the same IID-date resampling draws, and equal calendar spans share the same block draws. The first implementation keyed random seeds by arm label, causing small Monte Carlo endpoint differences even when featured and score, or stored and intended intelligence, had identical numerical series. Shared draws remove that irrelevant numerical difference. This does not change selection, matching counts, exact expected outcomes, cohorts, block lengths, estimator definitions, or power inputs.
2. Circular blocks at least as long as the entire observed span necessarily rotate the whole span and yield a degenerate distribution. The fixed raw diagnostic remains recorded, but now explicitly carries `degenerate_due_to_span: true` and an instruction not to interpret its zero-width range as uncertainty. All block outputs also expose calendar-span/block-length equivalents. No block length is changed in response to a result.

These refinements add no hypothesis, threshold, arm or outcome exclusion. The original design remains byte-identical and all exact estimates remain unchanged. The final manifest binds the resulting script and result bytes. The source archive and accepted dossier files are untouched.
