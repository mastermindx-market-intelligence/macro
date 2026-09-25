```yaml
role: visual_taste
reviewer_identity: "R3-007d fresh Opus visual critic B"
pass: 1
verdict: PASS_WITH_CONDITIONS
findings:
  - id: VTC-001
    severity: major
    finding: "The rendered page frame is not the product's frame — reference-r3.html:228-241 paints an 'M MASTERMIND' wordmark with a six-item text nav and four always-on Dark/Light/EN/中文 pills, while the production shell visible in every baseline and in stocks-preservation-desktop-dark-en.png is 'MASTERMINDX' with flag menus, global search, the Terminal button and a settings gear, so the identity-bearing band a builder would copy from this reference is the wrong one despite the data-preserve-shell attestation."
  - id: VTC-002
    severity: major
    finding: "The page teaches two contradictory chart color languages for byte-identical data — the South Korea polyline at reference-r3.html:302 and the one at :427 are the same point set, stroked neutral var(--link) in Act 2 under a caveat insisting the chart is neutral (proposal-r3-fixed-charts-desktop-dark-en.png) and stroked semantic var(--up)/var(--down) in Act 3's 'Recent path' column (proposal-r3-desktop-dark-en.png), so a user who learns blue-means-no-claim meets green and red versions of the same curve 1,500px later."
  - id: VTC-003
    severity: major
    finding: "The fixed chart sits directly beneath the 1M–YTD control inside a card whose own subtitle reads 'Selected return window 3M', and the resulting mismatch is paid for with three separate disclosures rather than designed away (help-note at reference-r3.html:293, a per-card '84-session price path · fixed' label, and the closing caveat), with proposal-r3-desktop-dark-en-horizon-12m.png confirming all seven shapes sit unchanged while the numbers swing to +93.1%."
  - id: VTC-004
    severity: major
    finding: "Production's most distinctive visual device — the five-asset risk-off↔risk-on track board under 'Where this shows up' in baseline-r2-desktop-dark-en.png, each row carrying a positioned marker plus MOVES and WHAT TO DO — is rendered in the reference as four flat text tiles (reference-r3.html:250-253), dropping the positional encoding entirely and three of the five asset rows with it."
  - id: VTC-005
    severity: major
    finding: "The same market-state vocabulary that is color-coded in Acts 2 and 3 (state-danger/state-caution at reference-r3.html:301-444) is forced to uniform state-neutral in the Country Inspector's widest table (:545-569), so 'Breaking down', 'Crash damage unresolved' and 'Downtrend' read as identical slate pills across 7 rows × 13 columns in proposal-r3-country-jp-dark-en.png and proposal-r3-country-jp-light-zh.png — exactly where color would do the most scanning work."
  - id: VTC-006
    severity: major
    finding: "Visual compression regresses against production in the transmission organ — production renders the five US transmission channels as a one-line chip strip, while reference-r3.html:481-485 expands them into five full-width rows whose second and third columns are the constant strings 'Transmission channel' and 'Observe', and the adjacent fragility map at :513-526 spends seven rows repeating the identical chip 'No concurrent structural warning' six times to say that only the UK is flagged."
  - id: VTC-007
    severity: minor
    finding: "All four organ states share one dashed neutral box (.organ-state, reference-r3.html:149), so 'Performance decomposition failed to render' in proposal-r3-organ-error-dark-en.png is visually indistinguishable from the empty state in proposal-r3-organ-empty-dark-en.png — no danger ink and no retry affordance on a surface whose whole identity is semantic state color."
  - id: VTC-008
    severity: minor
    finding: "The return-window help-note sits outside .organ-content (reference-r3.html:293 vs :298) and the 1M–YTD control stays live above it, so in proposal-r3-organ-error-dark-en.png the page is still explaining how the selected horizon governs USD, local and FX figures directly above a box saying those figures failed to render."
  - id: VTC-009
    severity: minor
    finding: "Grid composition is ragged in the flagship section of proposal-r3-fixed-charts-desktop-dark-en.png — the seven pulse cards fill a four-column grid as 4+3 leaving a conspicuous empty eighth cell, and in the turn-state board below, the China cell's three-line note runs roughly twice the height of its nine neighbours."
  - id: VTC-010
    severity: minor
    finding: "At 390px the primary comparison table keeps min-width:1180px inside an overflow-x wrap with sticky th but no frozen first column (reference-r3.html:114-116,:179), so horizontal scrolling strands the numbers without their economy name, and the same five stance strings are restated 45 times across the page in Acts 2, 2b, 2c, 3, 5 and 6."
strengths:
  - "Six numbered acts, each with a single-sentence question, give the page a spine production lacks, and every organ uses one panel grammar (eyebrow → H3 → count chip → content → caveat), so proposal-r3-desktop-light-en.png reads as one instrument rather than production's sequence of differently-shaped modules."
  - "Act 2's market card is a real compression win — chart, USD/Local/FX decomposition, turn-state chip and engine stance inside one 192px card — where production split the same facts between the turn-rotation grid and a separate 'Performance in US dollars' table (baseline-r2-desktop-dark-en.png)."
  - "Organ-local failure is genuine and calm: in proposal-r3-organ-error-dark-en.png only the performance organ collapses while the turn board, risk radar, rotation table, country inspector and deep desks stay fully painted at full fidelity, and the stale capture keeps values visible under its disclosure rather than blanking them."
  - "EN/ZH integrity is unusually thorough — direction ink flips to the Chinese red-up/green-down convention while status chips stay locale-invariant (reference-r3.html:32-39), CJK letter-spacing is zeroed (:43), and the ZH page renders complete and tighter at 6607px with no clipped or English-leaking labels."
  - "Typed nulls are honest and consistent rather than zero-filled: the em-dash carries every absent series in the cross-country table, visible on the Taiwan and India rows of proposal-r3-country-jp-dark-en.png."
  - "The country inspector is well-reasoned as a composition — compare all seven above, inspect one below, identical field order in both halves, 40px-minimum tab targets, and a vertical fact list that still works at 390px."
  - "Light is a real light theme rather than an inverted dark one: ink and status tokens are independently re-derived (reference-r3.html:20-31) and hold visible separation between up, down, warn and muted text in proposal-r3-desktop-light-en.png."
  - "Arithmetic is shown and reconciled instead of asserted — Local + FX equals the displayed USD return on each card (-5.3 + 9.8 = +4.5 for South Korea) and the 0.1pp rounding gap against the engine's unrounded total is disclosed rather than hidden."
```
