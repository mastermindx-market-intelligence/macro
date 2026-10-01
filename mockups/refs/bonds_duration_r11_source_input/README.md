# Bonds R11 exact-candidate review input

**INPUT ONLY — NOT BROWSER EVIDENCE, NOT DEPLOYED, NOT LIVE MARKET DATA.**

This archive renders the real Bonds route at commit `d3b11fe9be0e67e56ecff40bf25d5e09e85d3d1e`, using the existing `tests/test_bonds_divergence_gate.py::_base_ctx` synthetic fixture. The unchanged duration controller is embedded once. HTML, generated styles and source assets have individual hashes in `SOURCE.json`. The actual build used the existing Jinja template, `lib.pages.write_page`, and `scripts.externalize_css.externalize`; it did not substitute a standalone prototype or change market/source logic.

## What is and is not supplied

`site/bonds.html` and the inventoried non-font styles/scripts/icons are supplied. Six existing Inter font assets are deliberately **not redistributed**. Their exact source paths, expected hashes and sizes are listed under `font_assets_not_bundled`. A permitted reviewer with the repository can materialize those files from the same immutable commit into the matching `site/fonts/` paths and verify their hashes before any visual qualification. Never accept fallback-font screenshots as typography parity.

The existing shared scripts contain external Supabase/analytics references and dynamic API behavior. No external resource was requested during this build. Static asset discovery is **not** a runtime network trace, offline-completeness claim, login/session grant or authorization to call those services. The unresolved `.supabase.js` literal comes from a bundled vendor script and is retained as unresolved, not fabricated as a local file. Browser admission and allowed network/fixture setup must be established by the existing owner before execution.

Do not open this archive's route in a new browser/profile/host/scheme to route around the recorded administrator restriction. No server, browser, screenshot, accessibility scanner, EVIDENCE.yml or deployment was created by this preparation.

## Reconstructing the exact input

Use the immutable source commit above, the recorded fixture function and the recorded renderer/asset source hashes. Render the complete existing template with the unmodified fixture, write through the existing page writer in a temporary output root, and run the existing asset extractor. Restore each non-generated asset by its `source_path` from that same Git commit. `SOURCE.json.rendered_files` and the HTML/module hashes identify the output to compare. File dates are not data-vintage claims.

## Acceptance still owed

After genuine browser admission is restored and an accepting operator is recorded: verify desktop1440×900, mobile390×844 and tablet820×1180, EN/ZH, dark/light; open the actual dialog, inspect +50bp, +350bp invalid clearing, correction, fractional input/slider, reset, return/reopen, no-JavaScript/unsupported states. Verify real focus order, trapping/return, Escape, announcements, contrast, overflow, reduced motion and large text. The entry fixture alone is not all these states.

Use the existing capture_page_evidence.py and accepted evidence schema/guard to produce real receipts. This package intentionally contains **no passing evidence receipt**. Source review PASS5926458015 remains separate from browser/visual acceptance. Reviewer prerequisite5926522290 is advanced by providing retrievable exact source-rendered bytes, not declared completely satisfied before fonts/runtime dependencies and admission are resolved.
