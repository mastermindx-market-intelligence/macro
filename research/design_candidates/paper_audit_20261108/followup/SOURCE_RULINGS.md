# Source rulings and implementation status

These rulings bind to inspected commits, not to a moving “current” branch or a claimed live deployment.

| Repository | Inspected reference | Role |
|---|---|---|
| Mastermind | 5c3d3885234358aefb97ecdbc59be0864df14f8b | Governing procedure and authority |
| Macro | b5674d8ef898e503d6164922654f5ff89be9981c | Product doctrine, producer and consumer comparison |
| mastermind-terminal | d7a83d3348a4fcb762d93221f19c4e94cbe4505e | Options implementation and fixture |
| Macro | 07977b85ab171ee9aad3e4a04bb80566642878a9 | Delivery-controller and Agent OS schema refresh; does not retroactively refresh every product claim |

## R1 — Expectations breadth and explorer are not the same comparison path

[Builder](https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/scripts/build_expectation_surface.py) and [explorer template](https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/templates/expectation_surface.html.j2).

The builder's _comparable_pairs requires equal known period_end for the same security/metric/raw horizon. The explorer's previous-value/history selection does not establish the complete same-period/context guarantee. Its mover binding and horizon fallback require integration work as recorded in Paper 480-0.

The leading-class predicate uses down > up ×1.2, the converse for raises, otherwise balanced. Consequently a four-capture cut-led streak and five visible captures with more cuts than raises need not conflict. The new glance text states only the latest simple comparison. No source classification was changed.

**State:** source rule exists; explorer/navigation/request-generation extension is specified in Paper, not implemented by this audit.

## R2 — Options interpolation already has an owner

[volTenorComparison.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d7a83d3348a4fcb762d93221f19c4e94cbe4505e/terminal/lib/volTenorComparison.ts), blob da5b3aafc658ede5cfa67d5ec53fdb43e771b189.

Constant-tenor comparison interpolates total variance with calendar DTE. Skew interpolates IV in actual strike. Auto uses puts at/below the reference and calls above. A supplied-strike match has <0.5 percentage-point tolerance. Missing legs are not bridged.

For 14D 32.2% and 30D 29.4%, 21D is 30.48015748%, displayed 30.5%. The expected-move helper separately uses its declared trading-day annualization; it is not the tenor convention.

**State:** implemented at the inspected Terminal pin. Historical Macro build-pending prose does not supersede that source.

## R3 — The selected-expiry smile governs the current specimen

[Fixture](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d7a83d3348a4fcb762d93221f19c4e94cbe4505e/terminal/e2e/fixtures/options-r1-w3b-vol.json), blob c9c99492fbe3393906061823d7a3ec5c11b2a3aa; [VolComparePanel](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d7a83d3348a4fcb762d93221f19c4e94cbe4505e/terminal/components/vol/VolComparePanel.tsx), blob c08bc6e61c4cd97f81018bc9634ac06f355350dc.

The component first chooses a supplied selected-expiry smile, falling back near 30D only when absent. At the fixture's 21 October source date, selected 23 October points include:

| Strike | Call IV | Put IV | Used in the selected Auto read |
|---|---:|---:|---|
| 224.5 | 41.2 | 40.8 | 95% supplied put IV 40.8 |
| 236.5 | 37.1 | 36.9 | ATM supplied put IV 36.9 |
| 248 | 34.0 | 34.6 | 105% supplied call IV 34.0 |

The 236.5 reference is an ATM proxy, not spot. Missing 90%/110% points remain unavailable. The old 30D 32.4% entry was unsupported by either the selected 2D path or the inspected 30D fixture. A deliberately selected 30D specimen would need its own supported values, including 95% 33.8187234→33.8 and 105% 28.1 with supplied strike255.

Expected move for IV36.9, T2/252 and spot236.14 is 3.2873132755%; endpoints 228.3773384312 and 243.9026615688 become $228.38 and $243.90 via the component's two-decimal formatter. ±3.3% remains correct.

**State:** Paper fixture and wording repaired; no new calculator, live market-data proof or event-calendar verification.

## R4 — Standalone Flow/Volatility Save is not established by chart Save

[VolView mount](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d7a83d3348a4fcb762d93221f19c4e94cbe4505e/terminal/components/vol/VolView.tsx) and [R1 freeze](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d7a83d3348a4fcb762d93221f19c4e94cbe4505e/docs/OPTIONS_R1_W2_FREEZE.md).

VolView does not pass the optional onOpenResearch callback. The existing accepted Investigation chart entry creates a ready exposure-chart object and matching sector origin. The separately admitted matrix-selection path does not imply arbitrary Flow-print or Volatility-snapshot admission.

Reuse applyInvestigationRevision / apply_investigation_revision_v2, operation_id, expected_revision, readInvestigation and readInvestigationOperation, with terminal.options_exposure as the existing owner. Future adapters must supply an already admitted exact object or extend the incumbent contract through its proper source work.

**State:** current Paper Flow/Volatility Save controls unavailable. No save request was executed by this audit.

## R5 — Watch firing does not answer the timing thesis

The retained Paper inputs and current post snapshots show quote observation 15:40:01Z, firing/receipt15:40:03Z, a saved230.00 threshold and later230→232.5 call-wall evidence. They do not establish the claimed exact relative-trend turn date behind “two sessions after.”

The replacement sentence states the observed quote, and the broader question remains inconclusive while rotation fade is undefined. The current quote retains a separate illustrated21Oct16:30:04ET clock. Re-arm preserves230.00 and requires a fresh qualifying future observation.

**State:** reconciled illustrative presentation and builder contract. No watch, alert or assessment effect was performed.

## R6 — Risk horizon means native closing observations

[Probability evidence builder](https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/scripts/build_risk_radar_probability_evidence.py) and [workspace](https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/templates/risk_radar_workspace.js).

The selected model target uses native SPY closing observations; the workspace labels trading days / 交易日. The separate onset-lift convention uses business-day handling and is not this model's definition. The retained historical cohort's21D designation is not newly matched or calibrated by a wording change.

**State:** twenty Paper text corrections; model, cohort and integration qualification unchanged.

## R7 — Hub rank, edge, stage and coverage are separate

[engine/intel_hub.py](https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/engine/intel_hub.py).

Published command order is descending opportunity_score then composite_conviction. Opportunity incorporates signal magnitude, falsification, remaining edge and relative timing, with admitted de-escalation applied by the producer. Policy is context, not a voting desk. Stage is categorical; edge_remaining×100 is separate.

The no-component branch returns score0.4, n_components0, n_base0, drivers[], despite an older neutral0.5 comment. Full command records carry edge_components; _compact omits it. A default qualifier needs that field from the matching generation. A displayed40 is not proof of missing components.

**State:** bilingual help and a source-specific Build contract added; source scoring and ordering unchanged. Alert activation and draft persistence remain unavailable.

## R8 — Current Sector measurements, priors and model estimates retain distinct meaning

Complete preimages are in before/sector_old.jsx, before/sector_current_desktop.jsx and before/sector_current_mobile.jsx. Current mapping is post/sector_build_mapping.jsx.

The 21-session ETF return comparison is usable. Its stance and cycle interpretation are separate readings. The current unqualified model estimate stays unavailable. Retained14%/33%/52% examples are historical, with their original event definitions and limits. G4P is review-only, BML held, GPL a proposed return extension.

**State:** hierarchy and source mapping repaired in Paper. No model or return-path acceptance.

## R9 — PROPHET verification is per exact subject record

Preserved comparison and contracts: before/prophet_compare.jsx and before/prophet_compare_contract.jsx at a11cf1790bd921811a7242464483e27c5fa88510. Current contracts are in post/prophet_compare_contract.jsx.

Existing13R6 requires candidate occurrence and source generation;10PC owes stable identity across generations;10PE requires an exact candidate-to-Plan link. INTC/MSFT's exact records and Plan links are absent. VBF is explicitly NVDA and cannot serve either.

**State:** per-subject unavailable cues and conditional integration contract. ZE5 and D03/Phase2A fences unchanged.

## R10 — News geometry must not redefine review

The existing R3 contract already requires44px coarse-pointer controls. Current27L implements that design reference; original compact controls are retained in3H7. TickerNewsPanel, NewsLadder and NewsCatchup remain the owners.

**State:** styles and static layout inspected. Actual hit testing, keyboard/accessibility and review persistence are future consumer proof.

## Evidence use

Post JSX snapshots can contain pre-existing and concurrent product content. Only EFFECTS_CURRENT.json identifies this session's actual mutations. A screenshot is evidence of what rendered at capture, not ownership of every visible element or a functioning runtime.

## R11 — Material timestamps and Guide return naming

At Macro b5674d8ef898e503d6164922654f5ff89be9981c, docs/DESIGN_DOCTRINE.md:263 places freshness at its truthful scope and :267 requires consequential limitations at the relevant decision. Paper’s shared Material UI State Contract was narrower than this: its blanket second-clock-in-LENS rule could conceal a time that changes the verdict or action. Nodes 2U8-0/2WI-0 now retain a consequential second clock beside that decision, reusing MX/Freshness and LENS.

Guide D25 44J-0 distinguishes a named dashboard destination from history Back and qualified context return. Three search/recovery headers now inherit “Open Macro dashboard”. R20’s proposed local saved-search return remains unchanged in Paper; R13 maps its implementation gaps. These are source/design clarifications, not proof of an implemented route or timestamp policy.

## R12 — Expected move has a second input for price bounds

At Terminal d7a83d3348a4fcb762d93221f19c4e94cbe4505e, terminal/lib/volTenorComparison.ts:134 defines expectedMoveFromIv. The percentage estimate uses ivPct × sqrt(horizonDays/252). The guard at :143 requires a finite positive spot and a non-empty spot.asOf before :157–158 returns price bounds; otherwise percent can remain available while bounds are null. ivAsOf and spotAsOf remain separate fields. This trading-day horizon is not the calendar-DTE interpolation input.

The native Paper dependency figure 17X-0 and Build binding 18C-0 explain this existing source behavior. Their labels and accessible figure name were read back and the 390px help card was rendered. This is neither a new calculator nor proof that arbitrary source contexts may be combined. The existing Volatility return is retained.

## R13 — Guide return proposals extend the existing Reference and shell owners

At Macro b5674d8ef898e503d6164922654f5ff89be9981c, the production route is `site/reference.html`, rendered by `scripts/build_market_reference.py` from `templates/reference.html.j2`. Root compared the Reference inline script in the committed page with its template: they match exactly within the extracted script boundaries. The template was also fetched at current main 0997d488f73ebe76773ce4d534fa97749a0c1674 and is byte-identical to the comparison pin. This refresh applies to this template finding; it does not silently advance the retained governance or product pins.

The template's `state` at :702 contains `{mode, family, letter, q}`. `applyFilters()` maintains local substring filtering. `?q=` is read on initialization at :874 and is not written by this script. `handleHash()` at :904 resolves an existing canonical `.rf-e` element, opens it and scrolls it into view. It does not remove `.is-off` from a selected lesson or its containing group; a lesson excluded by the current query or filter can therefore remain hidden. Revealing that canonical selection must preserve browse state and must not inflate the true search-match count.

The builder's `search_key()` at :162 includes EN/ZH labels, IDs and aliases in `data-search`; `validate()` at :320 rejects duplicate normalized aliases. That implements alias text search, not alias-to-canonical route resolution or the proposed exact-match ranking. The existing registry and Reference handlers remain the extension points. Canonical lesson IDs and the current route should be preserved.

The shared-shell bridge's `sendViewState()` at :274, `currentFocusId()` at :281 and `applyRestore()` at :795 carry `x`, `y` and optional `focusId`. Reference result and related-link anchors currently have no IDs, so this field cannot identify those particular openers. `handleLocationAccepted()` at :963 dispatches the acknowledged location consumed by the existing Reference listener. The bridge wraps `pushState` and `replaceState`, not `history.back()`. The Reference Back control at :943–949 uses `history.back()` after a same-origin-referrer/initial-hash check; the template expressly preserves that contract and has no custom return store.

Accordingly, R20's preserved-results return, document-recreation behavior and direct-entry fallback remain proposed integration work. D25 already describes the incumbent source owners and unresolved consumer proof; its concurrent Paper content was inspected and preserved. F11 now identifies selected-lesson visibility and stable unique opener IDs as the smallest concrete implementation slice, with fuller return behavior stated separately. A change to query serialization or history semantics must be explicit, and no parallel navigation/control plane is authorized by this design package.

Source blobs: template `9575d5b8ba8a32e5b750ce41f955a5ecc9d91dfa`; registry builder `df2df85714805c14f641794a35664d755f5b12e8`; bridge `00ee9b9fa4d1fba67359d3d6b95c7937aed150b7`; committed page `57268a69f15e22f181631e176d51ef8feea6f312`. The existing `tests/test_market_reference.py:1006` fragment-acknowledgment test proves URL-based expansion and malformed/unknown-hash handling, not filtered-lesson visibility or exact query/filter/scroll/opener restoration.

**State:** source ownership and builder plan corrected; three Paper destination-label edits remain the only new Guide mutations in this continuation. No production Reference, registry or shell source was modified by this design package, and no live return behavior is claimed.
