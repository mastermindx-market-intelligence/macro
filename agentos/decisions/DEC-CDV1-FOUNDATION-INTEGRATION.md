---
key: CDV1-FOUNDATION-INTEGRATION
question: >
  Does the Consumer Defensive CDV-1 vertical build its own shared dossier shell,
  evidence vocabulary and rights layer, or integrate into the base the
  Semiconductors session is building?
answer: >
  Integrate. The Semiconductors session owns the shared base (macro #7870:
  theme-graph, evidence-foundation and rights layers; the sector-intelligence
  contracts already on main). CDV-1 mints no shell, slot, evidence schema,
  rights profile or asset family. Tasks 1–6 extend the incumbent Earnings owner
  only. Task 7 is a CONTENT + CONTRACT specification whose §6.2 field map binds
  Tasks 3/4/6 and whose UI build waits for the foundation host slot. One rights
  mapping, `rp_public_primary_v1 → sec_edgar`, is declared in Task 2, validated
  fail-closed in Task 4 and gated at read in Task 6 through a single injectable
  registry-reader seam that rebinds to #7870's snapshot gate in one line once it
  merges; production PG publication stays refused until the `sec_edgar` row
  lands on main.
rationale: >
  Chairman-relayed Astra CEO ruling of 2026-09-24 (~07:50Z): parallel sector
  sessions each minting their own shell, evidence and rights vocabularies would
  fork the product — one base, many verticals. The foundation integration map
  (#7917) confirmed that #7870's Theme Tracker family is the only real host
  candidate, that #7777's sector read model is sector-bounded and public-only,
  and that a static rights profile conflicts with source-family rights.
alternatives:
  - option: "Build a CDV-1-native collapsed dossier slot on the sector page now and migrate later"
    why_not: "Forks the shell and the auth/evidence contracts and re-implements what #7870 already owns."
  - option: "Bind Task 7 to #7777's sector dossier read model"
    why_not: "Dossier identity and dimensions are sector-scoped and public-only; issuer display needs a future additive version, not a reinterpretation."
  - option: "Keep rp_public_primary_v1 as a static display permission"
    why_not: "Rights are per source family and fail closed under #7870's registry; a static profile conflicts with them."
evidence:
  - research/consumer_defensive/cdv1_program/integration/FOUNDATION_INTEGRATION_MAP_2026-09-24.md
  - research/consumer_defensive/cdv1_program/design/T7_DOSSIER_DESIGN_SPEC_2026-09-24.md
  - "macro PR #7870 head at census time; macro PRs #7904, #7917"
affects:
  - "WS:CONSUMER-DEFENSIVE-CDV1"
  - templates/earnings_wire/earnings-economic.js
  - templates/earnings_wire/_economic_dossier.html.j2
  - engine/company_intelligence/pg_profile.py
  - app/earnings.py
confidence: high
reversibility: costly
decided_by: fable-meta-ceo
decided_at: 2026-09-24
---

The base is owned elsewhere; CDV-1 is a vertical on it. Any CDV-1 packet that
touches evidence, rights, dossier read models or a shell surface must first
census the foundation refs (`git show <ref>:<path>`, never a checkout) and bind
to their contracts where the concept is the same. Re-opening this decision
requires the foundation owner's contract to change or an explicit Chairman
reversal — a fresh session or a missing memory is not an invalidator.
