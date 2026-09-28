# HK macro parity acceptance — #8112 / #8136

This continues the existing R1–R3 design and R5 source carrier. It is not new research or a replacement implementation branch. The native Codex integrator is session `01a0e68a-c06f-7651-805f-bd92f2c95bd5`.

## Source and custody

- Parent: https://github.com/mastermindx-market-intelligence/macro/issues/8112
- Implementation: https://github.com/mastermindx-market-intelligence/macro/pull/8136
- Single remote source branch: `sol/hk-macro-parity-20260928`; pickup head `02f0e717f12da2273cdd2070cfdfe011f42e9a78`.
- R1/R2/R3/R4 comments: `5861094343`, `5861316152`, `5862180343`, `5863057467`; handoff `5864128388`; later successful R5 source publication `5864195250`.
- Retained R3 SHA-256: `3a6cea2e11b64c0056f574dbb9a8c000005bca4f1506a22609ccb822bd6eb645`, freshly read with `ssh m1 'shasum -a 256 /private/tmp/hk-macro-parity-20260927-audit/hk.r3.html.j2'`. This diagnostic file is not the release candidate.
- Current-source comparison/input pin: `4549507e5cbc8c60ab17c18656af8de8e51520fc`. The HK template, US/China template references, shared risk and theme dependencies and HK builder/producer paths did not move between the historical input and this pin. New source is a bounded continuation of the existing PR, not a full-file overlay on main.
- Protected procedure refresh: Mastermind `5c6b010a6157895d4f697548c75263cdff641ea6`; INDEX blob remains `94d1af402598894372858793a5b1931019c5fa77`. Its five commits since the admission pin changed 36 files and no `docs/sol_skills/` procedures. Macro main refreshed to `03e8961d22b48cc65666f6318ee8c8bd610f3caa`; none of this change's template, producer, test or CI-registration dependencies moved from the prior comparison pin. A second prepublication refresh to `7878cc44564e677057c220fea7f01811ddc32c6c` also found those dependencies unchanged.
- The shared local `macro-main` checkout is untouched. Source custody is an isolated external-SSD worktree made by the required storage helper.
- Adjacent #7700 remains separate. Its two HK 40px hero/ticker control rules are retained; its Canada product changes and CI ownership are not copied.

## R4 dispositions

1. Restore the producer's detailed `flip_en` / `flip_zh` threshold explanation inside the factor popup, keeping the main face's producer-derived plain wording.
2. Preserve those explanations when component readings are absent, and retain an actual reachable Factor details button without a fabricated 0-of-0 count.
3. Keep VHSI separate from native Fear–Euphoria and restore `range_plain_en` / `range_plain_zh` beside the VHSI value; precise percentile stays in detail.
4. Explicit wording adjudication: use **Factor data unavailable / 因子数据暂不可用** when the owner provides no readings or thresholds. There is no evidence of an active build. The inherited wording assertion changes deliberately; unrelated assertions stay intact.

The same existing HK modal controller now handles semantic dialog labelling, focus entry/trapping/return, preserved body overflow, background inertness and rapid reopen. It delegates the nested heatmap's opening/closing to its existing owner while retaining the parent panel's scroll lock and restoring focus when the child closes. No new modal, design-token or runtime stylesheet system is introduced.

## Art direction retained from R1–R3

**DARK TREATMENT:** graphite surfaces, restrained luminance depth, faint borders and state-coloured instrument emphasis. Bars and numerals retain one semantic owner; the gauge and score path form the primary hierarchy. Dense mechanics stay in progressive disclosure.

**LIGHT TREATMENT:** cool page canvas, white/translucent research panels, darker reading ink, hairlines and restrained shadow. Existing light overrides suppress score text glow and use surface/border contrast for depth. This is assessed separately from the dark design. The information order, controls and semantic data are identical across themes.

**Intentional differences:** dark uses luminance/glow for emphasis; light uses ink, white material, border and shadow. Neither theme changes the meaning of state or direction. EN/ZH direction colours remain owned by shared tokens. Unavailable scores/gauges are neutral text/dashes without invented zero, Calm state or a trading instruction in either theme.

**References:** the US `site/macro.html` is primary for hierarchy and progressive depth; China `site/china.html` is secondary for country-panel composition. Both are captured in the same language/theme/viewport axes. Their bytes are committed rendered references, not assertions that today's remote production was captured.

## Reproduce actual browser evidence

From a site-enabled isolated checkout with Python Playwright/Chromium:

```sh
python3 scripts/capture_hk_macro_parity.py \
  --source-ref 4549507e5cbc8c60ab17c18656af8de8e51520fc \
  --scratch .verification/hk-8112/macro
```

`manifest.json` uses the existing `mastermind.p0_evidence.v2` schema. It binds the capture script, HK template, test VM, frozen regime/market-state/score-log inputs and rendered HTML. `interactions.json` records the actual assertions and any failures. `--quick` is diagnostic only and emits a partial manifest.

The fixture uses native sentiment, market-state and sector relative-strength snapshots, the existing plain-copy helper, and the committed score history. The sentiment chart uses the existing renderer. All five table types are populated with explicitly declared layout exemplars, including long EN/ZH names. Other VM fields are ordinary test exemplars or explicitly unavailable; they are not a canonical production build. No collectors, engines or ledger writers run for these captures.

The matrix covers EN/ZH × dark/light × desktop1440/mobile390. Every one of the15 panels is opened through a real keyboard or touch control and exercised for focus, scrolling, disclosures, Escape/close/backdrop, and chart reveal. The nested heatmap is checked on desktop, where its existing owner offers full-screen expansion; that owner intentionally hides expansion on touch/mobile. Reduced-motion, rapid reopen and unavailable states are exercised at320,430 and768px. Dialog screenshots use the actual viewport; the parent page is inert behind them. After keyboard traversal, the harness returns focus to the close control, leaves help triggers, waits for the shared LENS tooltip to dismiss through its ordinary handlers, and verifies the panel is unobscured before capture.

The primary manifest also records real browser hover/focus states on the hero controls in both themes. Earlier diagnostic captures are retained outside the committed acceptance packet.

The existing `prophet-p0b-zero-fouc` fixture recipe and both stock-browser receipts are reminted by their normal renderer/verifier because their construction inputs include the HK template. Canada product source remains unchanged. Stock fixture proof, hosted CI, independent review, release-owner acceptance and normal production readback are distinct gates; these screenshots alone establish none of the latter gates.

## Verification and independent review dispositions

- The final macro capture records **130 passing interaction cases, zero failures**, all eight primary states and four genuine hover/focus states. Its 148 content-addressed PNGs include all 15 expanded panels and both reference routes.
- Relevant ordinary tests: **207 passed, one warning** across `test_hk_tier1_shell`, `test_hk_macro_parity_8112`, `test_hk_signal_stack`, `test_hk_conditions`, `test_risk_radar_dlg_partial`, and `test_risk_radar_dlg_country_wiring`.
- Stock first-frame suite: **115 passed** on the final receipts. Both ordinary HK/Canada browser verifiers report pass, including 48 primary plus16 degraded owner cases per market. The current stock manifest extension binds those actual reruns; its historical baseline and prior extension remain preserved. An initially stale manifest binding was caught and repaired without changing the test.
- Visual evidence and P0B receipt-closure gates: pass.
- Design added-line ratchet: zero blocking findings. Runtime style injection remains within the existing budgets. CI contract delta against `03e8961d22b48cc65666f6318ee8c8bd610f3caa`: zero introduced and zero inherited findings; all 237 legacy CI jobs validate. The new parity suite is registered in the existing job's paths and command.
- Independent native Opus source review session `5983c017-d03b-4841-9b7b-9eab10f6157c` returned PARTIAL on the earlier uncommitted source. Its three major findings are repaired: escaped hero/playbook flip prose under the production non-autoescaped environment; risk popup anchored to its actual trigger and clamped to the viewport; rendered sector value/zero/missing/trend/breadth assertions. Its publication blocker is resolved only by publishing these bytes and obtaining the subsequent exact-head review; this record does not transfer the old review to the new head.
- Other review repairs: missing sentiment is not neutral or a synthetic zero; native confirmation/dissent is preserved; coverage says gauges with readings; owner thresholds survive absent/malformed component rosters; unknown radar suppresses a contradictory calm driver; degraded factors are disclosed; all five tables receive populated long-name browser fixtures; ratio trend and breadth dates are explicitly labelled.
- Two deliberate visual choices remain: the source's own as-of date stays readable at full opacity, and the two #7700 40px control floors remain intact. “Preserved” refers to the admitted R5/#7700 source, not a claim that #7700 is merged into main. Specimen-compatible spacing/radius fallbacks are documented in governed CSS; no parallel token root is introduced.

Local fixture and test results do not constitute independent final visual approval, hosted CI acceptance, a release-hold lift, or production proof. Those exact-head receipts belong on #8136 and #8112 as they become available.
