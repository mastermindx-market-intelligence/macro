# Legacy migration and native Paper receipt

The R30 product has eight routes. Its five specification atlases, four responsive references and two start guides provide implementation coverage rather than extra daily destinations.

All **28** earlier artboards were moved, preserving node IDs, to [ARCHIVE · Bonds + Transmission · pre-R30](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1Y-1). None was deleted. No node from Forex p-1F-0 was targeted.

The page names in the Paper sidebar retain their existing R18–R25 / Studies wording because page rename is not an admitted operation of the current carrier. The prominent R30 start guides identify the current sequence at the top of both pages. No unsupported rename or deletion path was used.

## Every predecessor is accounted for

| Original node | Original study | R30 destination | Supporting implementation reference |
| --- | --- | --- | --- |
| 5PXK-1 | 105 · R18 · Bonds · Duration review · Desktop Light EN | 02 Curve & duration | I02 |
| 5Q85-1 | 106 · R18 · Bonds · Invalid shock · Mobile Dark ZH | 02 Curve & duration | S03 invalid input / I02 |
| 5Q9Q-1 | 107 · R19 · Bonds · Transmission Intelligence · Desktop | 05 Transmission | I03 |
| 5QO2-1 | 108 · R19 · Bonds · Transmission Decision Thread · Mobile | 05 Transmission | M02 |
| 5X5Q-1 | 107 · R19 · Bonds · Mechanism Transmission & Counterevidence | 05 Transmission | I03 |
| 5XKY-1 | 108 · R19 · Bonds · Transmission Decision Thread · Mobile | 05 Transmission | M02 |
| 5XXZ-1 | 107 · R19 · Bonds · Cross-Market Transmission & Decision Matrix | 05 Transmission | Confluence matrix / I03 |
| 5QSD-1 | 109 · R20 · Bonds · Historical Regime Memory · Desktop | 07 Replay | I09 / I12 |
| 5R67-1 | 110 · R20 · Bonds · Historical Evidence Insufficient · Mobile | 07 Replay | S03 valid empty / unavailable history |
| 5Y8L-1 | 108 · R20 · Bonds · Transmission Decision Journey · Mobile | 05 Transmission | M02 |
| 5YLJ-1 | 109 · R20 · Bonds · Transmission Decision Journey · Tablet | 04 Capital competition / 05 Transmission | T01 responsive pattern |
| 5XRB-1 | 109 · R20 · Bonds · Data & Evidence Contract Map | S05 Implementation map | Data contract |
| 5SHO-1 | 111 · R21 · Bonds · Cross-Market Confluence · Desktop | 05 Transmission | Confluence matrix |
| 5SWN-1 | 112 · R21 · Bonds · Confluence Decision Thread · Mobile | 05 Transmission | M02 |
| 5U8A-1 | 113 · R22 · Bonds · Economy & Earnings Transmission · Desktop | 03 Credit / 05 Transmission | Issuer relationships and earnings evidence |
| 5UEX-1 | 114 · R22 · Bonds · Economy Transmission Decision Thread · Mobile | 03 Credit / 05 Transmission | M02 and evidence sheet |
| 5US2-1 | 115 · R23 · Bonds · State Transition Monitor · Desktop | 08 Saved cases | I04 / S03 |
| 5UXZ-1 | 116 · R23 · Bonds · State Transition Decision Thread · Mobile | 08 Saved cases | I04 mobile sheet / S03 |
| 5V7A-1 | 117 · R24 · Bonds · Unified Decision Workspace · Desktop | 01 Bonds / 05 Transmission / 06 Scenario / 08 Saved cases | Shared case journey |
| 5VDX-1 | 118 · R24 · Bonds · Unified Decision Thread · Mobile | 01 Bonds / 05 Transmission | M01 / M02 |
| 5X3V-1 | HELD · R25 Credit Alert · Empty · NOT FOR BUILD | 08 Saved cases | Held predecessor stays reference-only; S03 empty and I04 define replacement |
| 5VV3-1 | 107 · R19 · Bonds × Forex · Cross-Market Transmission | 05 Transmission | I03 |
| 5W4N-1 | 108 · R19 · Bonds × Forex · Transmission · Tablet | 05 Transmission / 04 Capital | T01 responsive contract |
| 5WF2-1 | 109 · R19 · Bonds × Forex · Transmission · Mobile | 05 Transmission | M02 |
| 5WO5-1 | 110 · R20 · Bonds × Forex · Transmission · Desktop Light EN | 05 Transmission | Light desktop |
| 5WUY-1 | 111 · R20 · Bonds × Forex · Transmission · Mobile Dark ZH | 05 Transmission | M03 dark Chinese sheet |
| 5YXN-1 | 110A · R21 · Confluence Bridge · Forex Entry | 05 Transmission | Existing Forex destination bridge; no destination edit |
| 5YTA-1 | 110B · R21 · Confluence Bridge · Cross-Asset | 05 Transmission | Cross-asset entry / case context |

A responsive predecessor is mapped to the new responsive contract, not represented as a separate product feature. Economy/earnings, counterevidence, confluence and state-transition material was absorbed into the connected case, evidence and saved-review workspaces. The held R25 empty-credit-alert board remains historical reference only and is not promoted to a build source.

## Current layout

| Page | Product routes | Supporting references | New board count |
| --- | --- | --- | --- |
| p-1H-0 Bonds | 01, 02, 03, 04 | START, S02, S05, M01, T01 | 9 |
| p-1E-0 Cross-Asset | 05, 06, 07, 08 | START, S01, S03, S04, M02, M03 | 10 |
| p-1Y-1 Archive | None | 28 preserved predecessors | 28 |

Start guides are at canvas origin. Product routes use x = 0 / 1560 and y = 700 / 2350. Builder references begin at y = 4100; the research-tools atlas is at y = 6300. Mobile/tablet references occupy the right side. Archive Bonds boards retain their earlier positions; archived Cross-Asset boards shift 4000 px right to avoid collisions.

The final page inventory was read back and all nineteen new positions and all twenty-eight archived IDs were verified. Current node identities, locations and source/reference exports are recorded in manifest.json and the JSX directory.
