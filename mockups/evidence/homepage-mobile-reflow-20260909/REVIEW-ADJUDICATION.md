# Sol adjudication of independent review R1

R1 returned PARTIAL. Its source-layout reasoning was accepted, but visual acceptance and cache delivery were not. This is a repair request, not a waived PASS.

**320px evidence and legible crops — accepted and repaired.** The original 406px-wide baseline at a 320px viewport, two full 320px after captures and a baseline footer crop now live in this same repository. `capture-narrow.py` captures footer, situation-card and date-caption crops for EN/ZH × light/dark preference × 320/390. It asserts actual document width equals viewport width. `narrow-layout.json` records each result. These are reproducible diagnostics beside the unchanged canonical manifest schema.

**Shared cache delivery — accepted and repaired.** All seven HTML references across the five landing-family pages are restamped from the existing `optimize_assets._hash_bytes` owner. The regression test first failed on all five stale references, then passed after the repair. No render-time heal is assumed and no new caching plane exists.

**Intentional wide elements — measured, not guessed.** The three wide descendants at the standard mobile viewport are `#ph-track` and its two `.ph-set` children. They are the existing carousel's clipped strip, with `.ph-clip` as their clipping ancestor. The new 320px inspection also found a genuinely clipped `.ph-tag` date caption. That additional finding is repaired by wrapping the existing caption within the 680px media block, without changing or hiding any words. Its two source tests failed before the fix. The inspection retains every measured descendant and clipping ancestor for independent checking.

**Selector tests — accepted and repaired.** The media reader now preserves selector whitespace, skips comments and respects quoted braces. Exact-selector negative controls reject `.sit.early`, an out-of-breakpoint meter rule and malformed brace boundaries. Source-text tests are explicitly complementary to the real browser assertions, not substitutes for them.

**Potential future long footer tokens — deferred, bounded.** The current bilingual inventory passes the actual 320px browser matrix. This repair does not invent future labels or claim every possible translation fits. A new label must repeat the same narrow-width check; adding arbitrary global word breaking now would change current typography without an observed failing label.

**Review access and exactness — repaired.** `SOURCE-DIFF.patch` is committed inside the worktree the reviewer can read. `source-snapshot.sha256` binds tested source bytes. The re-review will name the newly committed exact head and read only committed artifacts inside this repository. No denied external directory permission is broadened.

Public light-only art direction remains deliberate in both preference settings. All new code concerns geometry and cache delivery. Production acceptance, complete CI and current-base composition remain separate gates. No conversion improvement is asserted.
