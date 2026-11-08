# Paper audit and build plan — 8 November 2026

## Authority, scope and state

Chairman assignment: audit and improve the existing Paper estate for architecture, feature viability, implementation clarity, visual quality, navigation, workflows, illustrations and motion; consolidate safely and compare with existing code.

Canonical programme: Macro PR #10617, branch `design/paper-production-audit-20261102-ryan`. This is an additive audit return in the existing programme. Existing draft/release holds remain. No production code, deployment, runtime or trading authority is changed.

Source pins:
- Mastermind protected master: `5c3d3885234358aefb97ecdbc59be0864df14f8b`.
- Macro protected main: `338a10852dcefa5d2bd07e5c6be0955c2b1e83fd`.

**Current execution state:** material Paper edits applied to Expectation Surface and the International entry directory. Paper then returned repeated connection timeouts on read-only inspection calls. The last write before those timeouts was acknowledged. No GMI, Terminal, Hub, News or AI edits have yet been attempted by this session. Final visual QA of the last ES semantic/build-contract changes remains owed. This file is a recoverable implementation brief, not an estate-wide acceptance claim.

## Inventory and audit coverage

The current resource inventory returned 35 files and 2 folders. This includes active product files, archived designs, copies and technical test files; it is not a count of 35 products. The earlier programme census remains historical evidence rather than a fresh full-artboard inspection.

Representative visual/source audit covered Expectation Surface, Mastermind AI, Market Guide, MarketOntology, Intelligence Hub, News Intelligence, GMI Explorer, Terminal and International Markets. Entry metadata was also inspected for Prophet, Dashboard Popups, Mastermind OS, Canonical Design System, Market Memory and Policy Monitor. Three read-only advisors supplied bounded architecture and taste judgments; they made no mutations.

Preserve:
- MASTERMIND PAGES original and copy: existing lossless-migration/unknown-effect holds.
- Canonical Design System and current shared-shell programme.
- International R14 frozen product boards and source/release controls.
- News recovery amendment `QO-0 → 2F7-0`, dated 8 November.
- Existing recovery, keyboard, source, save and monitoring contracts where already substantial.

No archived/test file was deleted. The unrelated AERLOR file was excluded.

## Applied: Expectation Surface

Paper file: `01M5EX8RTPR7YEZD2A144XED2S`.

### Reading path

- `p-1-0`: **00 · Start · Estimate revisions**.
- `p-3-0`: **01 · Study · Coverage + methods**.
- `p-2-0`: **02 · Build · States + implementation**.

Five primary boards retain their IDs:
`6-0` desktop dark EN; `WI-0` desktop light EN; `1SD-0` desktop dark ZH; `2NZ-0` mobile dark EN; `392-0` mobile light ZH.

The normal screen now contains hero, revision breadth, largest moves and explorer. Existing census, method and state nodes were relocated with their identities preserved. User-readable explanations were added to Study; raw schemas and implementation records live in Build.

Study containers: `3TX-0`, `3U3-0`, `3U9-0`, `3UF-0`, `3UL-0`.
Build containers: `3UR-0` primary EN; `3V9-0` light source reference; `3VF-0` ZH source reference; `3UX-0` EN mobile expansion; `3V3-0` ZH mobile expansion.

Key preserved nodes:
- Census: `25-0, 1OA-0, 2K5-0, 2PG-0, 3AK-0`.
- Method/source reference: `NG-0, 128-0, 1Y3-0, 367-0, 3QV-0`.
- Existing states: `QN-0, 1SF-0, 37R-0, 3SF-0`.
- Mobile exact breadth tables: `2TY-0, 3EQ-0`, now expansion references in Build.
- Additional mobile mover rows remain in the respective Build containers.

### Visible changes

- Shorter answer and subtitle; explicit October 2026 design-example label.
- Coverage has a named destination.
- Snapshot clock uses a neutral icon rather than a green status dot.
- Three mobile movers per direction, with **Show all 20** in this illustrative fixture. Implement the actual available total, not a hardcoded 20; source currently caps each direction at 25.
- Mobile breadth has **Show numbers**. The implementation should switch between the plot and exact table without resetting metric/session/focus.
- Explorer readout carries the sample pair of capture dates.
- Duplicate implementation/state material no longer sits beneath the ordinary analysis.

Measured after structural edits, before the final semantic copy pass:
- Dark EN desktop: 4061 → 2258 px, about 44% shorter.
- Dark EN mobile: 6376 → 3346 px, about 48% shorter.
- Light ZH mobile: 6130 → 3255 px, about 47% shorter.
These are Paper layout measurements, not performance or user-testing results.

### Material source corrections

**P0 — prior capture semantics.** The comparison key is `(ticker_compat, metric, horizon_label_raw)`. Each estimate is paired with its own immediately previous valid observation. Both `period_end` values must be equal and non-null. Collection rotates through ticker subsets, so a global previous-session window is wrong.

Copy now says “Compared with each estimate’s previous valid capture.” First captures and fiscal rollovers have no comparable change. Implementation must expose `prior_at` and `latest_at`, plus fiscal period and absolute values.

**P0 — identity denominator mismatch.** The source builder computes `_comparable_pairs(obs)`, `_breadth(comp)`, `_movers(comp, ...)` and `_census(obs, clk)` independently from `_identity(obs, aliases)`. However, the existing template still says unmatched names and undated aliases are excluded from all counts. The pinned page contract confirms a captured ticker universe with identity projected separately.

Paper now says identity coverage is incomplete, reports identity separately from captured tickers, and removes the old 724/777 identity totals from current census specimens. Those values were already superseded by the page contract; under the current definitions they also cannot be treated as valid totals for the 845-ticker fixture. The two omitted values display a dash, with the example omission labeled. Do not solve the copy problem by silently adding a population filter.

**P0 — percentage/breadth distinction.** Zero priors still contribute a breadth direction but cannot enter percentage movers. The denominator is comparable estimate keys, not companies or individual analysts. One company can contribute multiple fiscal horizons. Flat uses `1e-9 * max(1, abs(prior))`; it is not merely screen rounding.

**Source availability is separate from freshness and identity.** `LIVE` means the source was available to render; it does not establish streaming. `COMPLETE_DEGRADED` is a standing identity condition. Missing observations, no comparison, no matching ticker, failed ticker fetch, stale capture and measured zero are different states.

### Existing architecture and plan

| Work | Incumbent owner | Required change/proof |
|---|---|---|
| Projection, comparisons, census and JSON | `scripts/build_expectation_surface.py` | Preserve same-key/same-period pairing and runtime counts. |
| Layout, search, disclosure and explorer | `templates/expectation_surface.html.j2` | Correct denominator copy; expose both capture dates; implement compact mobile disclosure and same-context return. |
| Output contract | `research/alpha_intelligence/expectation_market_dynamics/EXPECTATION_SURFACE_PAGE_CONTRACT_2026-10-21.md` | Treat as source of data semantics; never hardcode Paper fixture counts. |
| Historical cutoff inspection | `engine/k3e_expectation_surface.py` | Reuse only with immutable revisions, paired hashes, aliases, UTC visibility clocks and refusal states. |
| Existing inspection entry | `scripts/query_k3e_expectation_surface.py` | Extend incumbent query path if historical study is commissioned. |
| Site integration | `build_site.py` | Reuse existing guarded build invocation. |

Inputs remain observations, attempts and vendor aliases parquet. Outputs remain regenerated `site/expectation_surface.html`, summary, ticker index and safe ticker JSON. Render does not fetch the network or append a ledger. `financial_influence=false` and `k3e_admissible=false` remain false.

Present deep-link support restores **ticker only** with `?t=<ticker>#es-explorer`. Full metric/horizon/snapshot/scroll restoration is a required extension, not shipped behavior established by the designs. A saved historical study or monitoring lifecycle needs a separate implemented owner and receipt; no new competing service or ledger is justified.

The native Build page now includes:
- Selection and interaction contract `3XP-0`.
- Editable vector motion storyboard `3YE-0`.
- Source-checked phased build plan `3ZI-0`.

Motion: 160 ms control feedback; 200 ms settled view crossfade after the response; labels/units and series commit together; reduced motion commits immediately. No freshness pulse. Keep the last settled view during a new load and reject obsolete responses. Paper keyframes are static; they are not proof of runtime animation.

Required consumer proof: comparable key with a non-global prior date; first capture; period rollover; zero prior; unavailable observations; unavailable aliases; out-of-order responses; keyboard expansion and focus; same-context return; 320/390px; 200% text; EN/ZH and dark/light parity. Existing stale UI uses capture-to-render age >9 days; confirm collector policy before changing its meaning.

Sources, all at the Macro pin:
- [Builder](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/scripts/build_expectation_surface.py)
- [Template](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/expectation_surface.html.j2)
- [Page contract](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/research/alpha_intelligence/expectation_market_dynamics/EXPECTATION_SURFACE_PAGE_CONTRACT_2026-10-21.md)
- [Historical inspection engine](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/engine/k3e_expectation_surface.py)

## Applied: International entry clarity

File `01M3P1TW5Y3XWQC37ADDS8K5AG` is now **International Markets · Core + Global Surveillance**. Page `p-1-0` is **00 · Start · Core + Global Surveillance**.

Edited only existing entry/directory text:
- `3S0-0`: “International starts here.”
- `3S1-0`: separate R10 core and R14 surveillance scopes.
- `3S3-0`: neutral two-scope label.
- `3TB-0`: core routes and R14 frozen scope.
- `420-0`: two-scope reading path and source availability.

R14 is frozen for Waves2–5 / IM13–IM18. It must not be demoted merely because R10 is called “current,” nor should every depicted feature be presented as deployed. Frozen R14 product boards were not edited. Production tokens and the written specification/amendments take precedence over differing Paper glyphs.

Source already uses one International workspace. `scripts/build_intl.py` attaches surveillance; `templates/intl_workspace/shell.html.j2` mounts core and surveillance views and enables qualified surveillance payloads only when status is available. Existing currency bases are USD unhedged and local. A Hedged control requires an explicit availability/viability contract. Keep index/FX observation clocks separate from macro observation dates. Do not create another surveillance app or persistence/watch owner.

The file-rename operation `paper-estate-20261108-intl-file-reading-path-v1` returned adapter `EFFECT_UNKNOWN` despite an upstream result. It was **not replayed**. Two same-carrier reads of the original ID subsequently observed the exact new name, through `get_basic_info` and `list_resources`. The rename effect is reconciled as observed.

A fresh directory read also showed unrelated row text had changed since the initial JSX read. This session preserved that row and limited its own changes to the named targets above.

Sources:
- [Frozen design decision and amendments](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/agentos/decisions/DEC-INTL-GS-R14-DESIGN-FREEZE.md)
- [Written R14 specification](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/research/INTL_GLOBAL_SURVEILLANCE_DESIGN_SPEC_R14_2026-10-21.md)
- [Workspace shell](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/intl_workspace/shell.html.j2)

## Next native repairs, precisely scoped

### GMI — historical source status

File `01M5H6EARN9YHQV17JC6ZG9BRY`, page `p-1-0`. Current evidence depicts a 26 February 2024 Micron/HBM3E/H200 source inside a November2026 research snapshot. “Planned” can be mistaken for present supply status.

Change to **Planned in source** / **来源当时的计划**. Retain assertion date beside it and preserve the useful three-node relationship illustration. Do not assert current shipment/revenue status from that old source. Current exact English badge nodes:
`6EW-0,6H0-0,68Q-0,6BJ-0,6XJ-0`.
Chinese:
`6QC-0,6S9-0,6JI-0,6N2-0,6Z5-0`.

The English desktop header `68N-0` already exposes `6A2-0` (“Source · 26 Feb 2024”). Validate layout after the longer badge on mobile and all corresponding variants. Consolidate footer `6A0-0` missing-classification text into existing coverage disclosure `69T-0` only after inspecting exact parents. No mutation attempted before the transport failure.

### Terminal — qualify quote and bar returns

File `01M3NSZGE8JWN2EZCSF0DT05RM`, current page `p-17-0`, board `1U01-0`.

Quote group `1UED-0` has price `1UEF-0` =16.54 and `1UEE-0` =“+1.53% · Quote”; counterpart `1V6I-0` shows the same. Selected-bar values show +3.05%. Footer `1U03-0` says the data is illustrative and quote/chart clocks differ, but the basis is not adjacent to the values.

Do not invent a quote as-of time or return interval. If the specimen has no qualified quote metadata, design the explicit unavailable-metadata state and retain the historical value in Build reference. Place a known selected-bar date and basis beside its return. Preserve the chart-led density and existing keyboard/volume guidance.

### Intelligence Hub — density and score meanings

File `01M2VWK62FA5S4VVF6G7SBPE5J`, current `p-3-0 / 86-0`.
Hero `A8-0` repeats “Two setups to review” above the setup section `G6-0`. Fold that introduction into the actual setup heading. Research table `AU-0` pairs prominent 51 and85 values and N·A·R·B·P flags; verify their engine definitions before naming/relocating them. Keep “Why here” visible. Move secondary engine flags into row details without losing the route or evidence.

Do not guess score meanings from their magnitude. Existing builder guidance `p-2-0 / 2P-0,54-0,6S-0` already covers engine/navigation/source ownership.

### News — identify the actual disagreement

File `01M5EXPMQTSBFBAM8KKG83FTZH`, current R3 `p-1-0 / 27K-0`.
Expanded story `29O-0` begins with clocks and grouping mechanics. Put supported claim/scope/source differences before provenance metadata. Avoid conflating different scopes with contradictory facts. Replace generic next-check text with a specific question and existing source destination.

Exact targets: `2A6-0,2A7-0,2AH-0,2AJ-0,2AU-0,2BS-0`.
Preserve the fresh recovery amendment `QO-0 → 2F7-0`; its return/focus/filter guidance need not be reinvented. No underlying source assertion was verified in this pass, so do not invent the disagreement.

### Mastermind AI — answer-bound evidence and non-monitoring save

File `01M3P1QEHS5XXQY85BJT6QR2E1`, Build `p-9-0 / 1MO-0,5M0-0`.

Pinned `templates/chat.html` uses the existing brain thread/history/stream routes and passes selected symbol/page context, but the inspected complete template did not contain `context_receipt` binding. A selected-context badge is not proof of what evidence supported an answer.

Extend the incumbent response/renderer lifecycle so Sources binds to the actual answer receipt. Historical answers without evidence metadata should say **Evidence details unavailable**. Keep draft, scroll and focus on drawer return.

The existing Paper Build reference says create-thesis creates an active watched case and cannot implement **Saved + Monitoring off**. Verify that API and extend its incumbent thesis/version owner for a true non-monitoring save; do not create an active case and then archive it to imitate that state. Allowance ownership remains `lib/chat_allowance.py` / `config/plans.yml`.

[Chat source](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/chat.html)

### Guide / Ontology / other inspected entries

Market Guide’s calm question-led entry is worth preserving; no severe source contradiction was established. Ontology has substantial current context, evidence, recovery and retained comparison designs, but a shipped consumer for all proposed assembler behavior was not established. Keep that gap explicit. Prophet and Mastermind OS have extensive current/reference separation; do not replace them merely to make the estate uniform.

## Recovery, verification and DO_NOT_REDO

1. Paper transport errors are read-only connection timeouts, not a permission denial or evidence of session corruption.
2. No write was replayed or moved to another carrier.
3. Resume with native Paper inspect, then exact requested-file reads. The outer adapter document may describe the foreground file; requested page data is in `result.content`.
4. Inspect final ES primary/Study/Build screenshots and current node content; only repair actual defects. Do not redo the accepted structural moves.
5. Release this session’s working indicators on its exact edited boards when the native connection is available.
6. Apply queued GMI/Terminal repairs only after fresh reads; concurrent content and holds remain protected.
7. Keep the original broad design mission active across checkpoints. This audit return does not establish implementation, deployment, production behavior or full-estate acceptance.
