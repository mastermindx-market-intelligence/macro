---
key: A-DESIGN-RATCHET-REPORTS-WIDER-THAN-IT-BLOCKS
claim: >
  `scripts/check_design_system.py` rule 8 (`emoji`) REPORTS a strictly wider band than it
  BLOCKS, so an adopted emoji finding has a repair that is neither "strip the icon" nor "ask
  for a waiver". `EMOJI_RE` (reporting) spans U+1F300–1FAFF, U+2600–27BF, U+1F000–1F2FF,
  U+FE0F and U+1F900–1F9FF; `EMOJI_BLOCKING_RE` spans ONLY the two pictographic planes
  U+1F300–1FAFF and U+1F900–1F9FF, and `_emoji_finding_is_narrowly_blocking`
  (check_design_system.py:202) re-tests each finding's own codepoint against that narrow
  band before `--mode enforce-added` counts it. Misc Symbols + Dingbats (U+2600–27BF) and
  regional-indicator flags are therefore reported-but-never-blocking by DESIGN, documented
  in that helper's own docstring as "typography". The second half is the trigger: because
  enforce-added scores the lines a diff ADDS, editing a line for an unrelated reason
  re-presents that line's INHERITED glyph as a newly-added forbidden decision. Measured
  2026-09-26 on macro PR #7930: adding a ZH label to one chip
  (`{{ tfs.label }}` → `{{ t(tfs.label, tfs.label_zh) }}`) turned the line's pre-existing
  💊 U+1F48A into `templates/foresight.html.j2:581 [emoji] emoji U+1F48A`, failing
  `design-governance` → `ci-pack-8` → the required `ci-gate`, while 25,431 other estate
  findings stayed silent because nobody touched their lines. The same chip ROW already
  shipped ⚖ U+2696, ⚠ U+26A0, 🛰 U+1F6F0 and ⚑ U+2691 — i.e. three lawful neighbours and
  one that would red the moment it is touched.
falsifier: >
  In a macro checkout, add a line containing ⚕ (U+2695) to any `.j2`/`.html`/`.css`/`.js`
  file, then `git diff > /tmp/d.diff && python3 scripts/check_design_system.py --mode
  enforce-added --diff-file /tmp/d.diff` → exit 0, "0 blocking finding(s)"; repeat with 💊
  (U+1F48A) → exit 1 naming that line. `--mode report` lists BOTH. Disproved if a
  U+2600–27BF glyph ever blocks enforce-added, or if the two regexes are ever unified.
so_what: >
  When a design-governance red names an emoji on a line your diff merely TOUCHED, do not
  strip the glyph (that silently deletes meaning from the UI to satisfy a lint) and do not
  reach for a waiver. Move to the sanctioned KIND: pick the semantically equivalent glyph
  inside U+2600–27BF (💊 → ⚕ U+2695, one codepoint from the ⚖ already in that row) and add
  NO U+FE0F, which re-requests colour presentation and is itself in the reported band. That
  swap is also the better design under the theme art-direction law — a Misc-Symbols glyph is
  monochrome and inherits the component's own text colour, so it renders correctly in both
  the dark command-center and light research-workspace treatments, whereas a colour emoji is
  theme-blind by construction. Corollary for planning: a translation-only or copy-only diff
  can red a DESIGN gate, so never assume "I only touched text" means the design packs are
  out of scope — reproduce `enforce-added` against the full PR diff before pushing.
kind: landmine
verified_at: 2026-09-26
verified_by: >
  direct observation — macro PR #7930: head 4a6cf768 red at
  `##[error]templates/foresight.html.j2:581 [emoji] emoji U+1F48A` +
  `CI_PACK_FAILED_JOBS=["design-governance"]` (run log via
  `gh run view --job <id> --log-failed`); head 871b6d36 (💊→⚕, one glyph, no other change)
  gives `R0 enforce-added: 0 blocking finding(s)` exit 0 against the full 9,374-line PR diff,
  with design-governance's own four unit suites at 190 passed / 2 skipped and all three
  guard selftests OK; source read at scripts/check_design_system.py:92, 197-212, 578-585
scope:
  - mastermindx-market-intelligence/macro
  - scripts/check_design_system.py
  - templates/**
  - .github/ci/legacy-jobs.yml
confidence: verified
---
