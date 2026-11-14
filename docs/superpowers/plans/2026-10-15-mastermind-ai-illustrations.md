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

## HM — Scenario matrices (Chairman extension, 2026-11-04)

Spec: docs/superpowers/specs/2026-11-04-brain-scenario-illustrations.md. This is an additive extension on protected main after merged PR10069; it does not replace PR9447 or PR10208.

- [x] HM1: persist contract; preserve original-root accounting and isolated source custody.
- [ ] HM2: closed numeric heatmap and qualitative scenario_matrix compiler, schema and replay validation.
- [ ] HM3: native responsive matrix renderer with accessible axes/cells, semantic legend, assumptions and exact-value disclosure.
- [ ] HM4: teach the model template selection; prevent text-only illustrative matrices from evading current/historical data guards.
- [x] HM4a: recognize heatmap/matrix presentation requests in Fast EN/ZH without widening upstream tool authorization; clarify explicitly requested financial teaching scope and qualify deterministic regressions. Actual model selection remains in HM6.
- [ ] HM5: integrated shared-widget browser proof in both themes/languages, 1440/390 and 320 robustness; unchanged source/history/CSV semantics.
- [ ] HM6: exact-head review/CI, normal protected release and served model-to-visual/history acceptance.

Editorial labels are not runtime or production status. Initial source pin: affa0fd2e68723efc9e2cbc0e7c791ab70f5a53d. Existing accepted eleven-template and financial/math behavior is DO_NOT_REDO unless the extension invalidates it.
