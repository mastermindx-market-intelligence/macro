---
key: CHINA-PRIMARY-ROUTE-FAMILY-PARITY-2026-09-19
question: >
  Should china.html remain the estate's standalone first Archetype-D six-block regime
  dashboard while the US, Hong Kong, and Canada primary macro routes still expose the
  established regional dashboard composition?
answer: >
  No. The Chairman rejected the production divergence on 2026-09-19. Restore the primary
  china.html macro route to the pre-#7054 regional composition (parent
  e0e2600d6228af074c56b7ce7d46928db7442538), keep regime_dashboard as the long-term
  archetype assignment, and mark the surface design-system non-compliant until the regional
  primary-route family can migrate coherently. A future D migration may move
  macro.html/china.html/hk.html/canada.html together, or use an explicitly authorized
  non-primary canary; it must not strand one normal geography route on a materially
  different core experience.
rationale: >
  PR #7054 deliberately compressed China from the existing dense regional dashboard into a
  VerdictHero plus five first-level bands (What to do / What changed / four drivers /
  watching / Go deeper). That implementation was internally consistent with the Wave-0 D
  reference, but it was released to China alone. Production therefore looked like a
  different product from the other regional macro dashboards, which the Chairman explicitly
  rejected. The defect is release sequencing/family coherence, not the existence of the D
  archetype itself. Restoring the last accepted China template is the smallest reversible
  repair; retaining the archetype target avoids creating a rival product architecture.
  The rollback is composition-scoped rather than byte-for-byte: orthogonal #7054 truth and
  accessibility fixes (CNH/CGB Jinja namespace retention, USD/CNH quote-orientation copy,
  D/W/M cell semantics, keyboard focus rings, robust light-mode aurora gating, and locale-safe
  CNY/sentiment copy) remain carried forward so family parity does not reintroduce known defects.
alternatives:
  - option: "Keep #7054 live and wait for HK/Canada/US to catch up"
    why_not: "Directly contradicts the Chairman's production correction and leaves the normal China route divergent in the meantime."
  - option: "Delete the regime_dashboard archetype assignment for China"
    why_not: "Conflates current release state with long-term design architecture; the Chairman rejected the standalone rollout, not the D concept."
  - option: "Blanket-revert merge commit a8def4c / PR #7054"
    why_not: "The merge carried evidence and producer/test work beyond the visible composition. A full revert has a much larger blast radius than restoring the primary template and replacing the release lock."
evidence:
  - "origin/main template history: a8def4c24d584afe63f148c0d5ba6d8bf95ee506 is the only templates/china.html.j2 change after 4327fcd6242037edf810412a2f2d082c5d74c9e3; its subject is '[MO-A S1] china.html → Archetype-D regime_dashboard migration (#7054)'."
  - "a8def4c parent e0e2600d6228af074c56b7ce7d46928db7442538 is the pre-migration China template used for this restoration; seven newly-added historical color/glyph literals were converted to design tokens/non-emoji glyphs so the current design-system ratchet stays green without changing the composition."
  - "PR #7054 explicitly pins the 14→6 L1 composition and tests/test_china_archetype_d_s1.py enforced the five band-label sequence beneath the hero."
  - "research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md keeps china/hk/macro/canada in the regime_dashboard family; research/DESIGN_MIGRATION_FACTORY_V1.md listed China/HK as follower migrations rather than a separate product family."
  - "Chairman production review 2026-09-19: China dashboard is materially different from US/HK/Canada and must be fixed."
affects:
  - macro:china
  - templates/china.html.j2
  - config/product_experience/page_registry_overrides.yml
  - research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md
  - research/DESIGN_MIGRATION_FACTORY_V1.md
  - tests/test_china_archetype_d_s1.py
confidence: high
reversibility: easy
decided_by: chairman
decided_at: 2026-09-19
---

# China primary-route family parity

This decision records the production correction and the boundary for any future redesign.
Historical #7054 screenshots, fixture renderers, and evidence remain audit material; they do
not authorize replaying the standalone release onto `china.html`.
