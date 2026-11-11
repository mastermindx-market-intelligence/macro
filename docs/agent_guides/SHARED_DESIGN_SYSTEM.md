# Shared design system

## Design system (any user-facing surface)

`research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` is the binding visual/composition
law: archetype per route, canonical components (registry = the specimen at
`mockups/design_system/specimen.html`), tokens only (extend `templates/theme.css`,
never a parallel token root), density budgets, dark+light as two art directions,
EN/ZH parity. Content law stays with `docs/DESIGN_DOCTRINE.md` (wins on conflict).
Chairman design rule (2026-10-18): never add a colored left edge or equivalent
accent stripe to a container; do not relocate it to another edge. Use neutral
surface hierarchy, even borders, typography and labeled semantic ink. Preserve
complete focus outlines and meaningful chart series. The doctrine owns this rule.
Migration work follows `research/DESIGN_MIGRATION_FACTORY_V1.md`: builders execute
a committed migration packet exactly and never invent design language — a builder
that believes the packet is wrong stops and escalates.

### Theme art direction — required (TP-0, 2026-08-27)

Dark and light are **two deliberate art directions of one semantic system**, not
a design and its skin. They share information architecture, component semantics,
spacing/type scales, state meanings, user actions, data contracts, ordering and
density law, and interaction behavior. They do **not** have to share material
treatment: dark is a command center (luminance depth, instrument calm, restrained
glow); light is a research workspace (cool canvas, white material, hairline
discipline, shadow instead of glow).

**Token substitution alone is never proof of a light design.** "The same CSS
still renders once the tokens swap" is exactly the failure this law exists to
stop.

Every material UI packet must name: DARK TREATMENT; LIGHT TREATMENT; which
mechanisms intentionally differ and why; the reference/baseline; theme-specific
degraded states; and the evidence matrix (dark/light × EN/ZH × desktop 1440 /
mobile 390). A packet missing the light art direction or its evidence is
`PARTIAL/BLOCKED`, never `PASS`.

- **Designer:** state both art directions separately and supply both evidence
  sets; never approve "same CSS, tokens swap" without arguing why the mechanism
  genuinely works in both luminance environments.
- **Builder:** if a frozen spec lacks LIGHT TREATMENT or its required evidence,
  stop `PARTIAL/BLOCKED` — do not invent or silently translate one, and never
  add an opaque runtime stylesheet to escape a design-system constraint.
- **Reviewer:** `PASS` on a material UI change requires dark and light each
  adjudicated as designs — hierarchy, material depth, semantic color, responsive
  composition, EN/ZH parity. Functional browser success is necessary, never
  sufficient.

**Substantive product styling may not be authored as an opaque runtime
stylesheet system inside page/composer JavaScript** — no multi-kilobyte
`style.textContent` material system, no parallel palette/token family, no
duplicated light/dark stylesheet branches invisible to the design-system
checker. JavaScript may mount and recompose canonical DOM, set state
classes/attributes, select existing variants, and apply genuinely data-dependent
inline geometry; governed presentation source owns the material decisions.

Forward-only enforcement (inherited debt reports, but does not newly block):
`scripts/check_design_system.py --mode enforce-added` on changed lines,
`scripts/check_runtime_style_injection.py` as a ratcheted budget that may only
stay flat or shrink, and `scripts/check_ui_visual_evidence.py` for the committed
dual-theme evidence receipt. CI checks evidence existence and state identity
only — a human/Opus reviewer owns visual taste.

