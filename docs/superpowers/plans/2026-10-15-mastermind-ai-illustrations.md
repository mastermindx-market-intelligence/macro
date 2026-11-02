# Mastermind AI illustration implementation plan

Goal: source-bound native charts and explanation templates inside the existing customer chat.
Architecture: existing Brain tool/stream/history owners, one bounded spec compiler and one native presentation module loaded by the widget. No new service or chart-command bus.
Tech: Python, vanilla JavaScript, native SVG/HTML/CSS, pytest and Playwright.
Spec: docs/superpowers/specs/2026-10-15-mastermind-ai-illustrations.md

## Global constraints
Preserve live writers and PR7151/R8 holds; one source operation/carrier. Strict spec limits 64KiB/80 rows/6 columns/500 characters/4 visuals. No raw model HTML/SVG/CSS/URLs, live facts from screenshots, unbound numeric source claims or new state/control authority. Existing output filters precede visual release. Both host themes and languages, measured responsive layout and native accessibility.

## Review focus
Untrusted history must not expose other metadata or bypass spec checks. Source equality must not become freshness/semantic verification. Null/zero/negative/constant data must remain honest. Duplicated done/reconnect events must not duplicate visuals. Long bilingual labels and CSV formula text must remain safe.

## Tasks
- [x] Compiler: tests/test_brain_visuals.py failing tests, then engine/neuralweb/brain_visuals.py; normalize(params, observations, identity) returns bounded chart wire or error; validate_view validates retained display subset. Test all templates, boundaries, source mismatches, duplicate bindings, unsafe markup and CSV inputs.
- [x] Native templates: templates/mm_brain_visuals.js/.css and paired site assets; exposed MMBrainVisuals.mount(host, chart), clear(host), validate(spec), csv(spec). Playwright must fail before renderer exists, then cover responsive dark/light EN/ZH, all templates, null gaps, invalid input, data disclosure and export.
- [x] Integrate: minimal changes to brain_gateway.py tool catalog, per-turn compilation, final output guard, charts side-channel/message metadata, safe get_thread visual-only projection. Minimal mm_brain.js loader/mount/history/done/retract hooks. Existing tests plus scripted model tool loop prove integration, not only pure functions.
- [ ] Review and delivery: consume existing Fabric contract review, repair blockers, run targeted regressions and design/asset guards, capture real-widget browser evidence. Commit/push using registered workspace fenced tools, open original PR, preserve genuine CI/review/release gates and verify live when admitted. Save current continuation in canonical Agent OS and PR; do not claim production from fixtures or a PR.

Execution ownership: principal retains cross-owner integration and visual judgment (PRINCIPAL_JUDGMENT); bounded independent review delegated through installed M2 Fabric under the same original operation root. No background Web execution claim.
