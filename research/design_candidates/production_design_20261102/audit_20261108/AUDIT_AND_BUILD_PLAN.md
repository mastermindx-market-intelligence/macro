# Paper audit and build plan — 8 November 2026

## Authority, scope and state

Chairman assignment: audit and improve the existing Paper estate for architecture, feature viability, implementation clarity, visual quality, navigation, workflows, illustrations and motion; consolidate safely and compare with existing code.

Canonical programme: Macro PR #10617, branch `design/paper-production-audit-20261102-ryan`. This is an additive audit return in the existing programme. Existing draft/release holds remain. No production code, deployment, runtime or trading authority is changed.

Source pins:
- Mastermind protected master: `5c3d3885234358aefb97ecdbc59be0864df14f8b`.
- Macro protected main: `338a10852dcefa5d2bd07e5c6be0955c2b1e83fd`.

**Completed design pass:** native changes were applied to seven existing Paper files: Expectation Surface, International Markets, GMI, Terminal, Intelligence Hub, News and Mastermind AI. The earlier read-only connection interruption recovered on the same native carrier. Changed product regions and new builder references were inspected through native screenshots; this session’s exact working indicators were released. All known write effects are reconciled. This is a completed focused design/source audit, not a claim of full-estate visual certification, shipped runtime behavior or production acceptance.

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

The normal screen now contains hero, revision breadth, largest moves and explorer. Existing census, method and state nodes were relocated with their identities preserved. User-readable explanations were added to Study; raw schemas and implementation records live in Build. **Start / Study / Build is the organization of the Paper file.** Production should expose concise coverage and method disclosure through the existing page; it should not publish a builder tab or raw schema material.

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

Final measured primary layouts:
- Dark EN desktop: 4061 → 2207 px, about 46% shorter.
- Dark EN mobile: 6376 → 3346 px, about 48% shorter.
- Light ZH mobile: 6130 → 3217 px, about 48% shorter.
The light EN desktop is 2207px and the dark ZH desktop is 2166px. These are Paper layout measurements, not performance or user-testing results.

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

## Applied: GMI historical source status

[Paper file](https://app.paper.design/file/01M5H6EARN9YHQV17JC6ZG9BRY/p-1-0).

The current specimen depicts a 26 February 2024 Micron/HBM3E/H200 source inside a November 2026 research snapshot. The undated reading of “Planned” could be mistaken for current supply status.

Changed all ten current EN/ZH badges to **Planned in source** / **来源当时的计划**, preserving the assertion date and useful three-node relationship illustration. This makes the historical claim’s time explicit without asserting current shipment or revenue status.

English nodes: `6EW-0,6H0-0,68Q-0,6BJ-0,6XJ-0`.
Chinese nodes: `6QC-0,6S9-0,6JI-0,6N2-0,6Z5-0`.

Affected current boards:
`61M-0,6A7-0,6DR-0,6FY-0,6I6-0,6LQ-0,6PA-0,6R7-0,6VF-0,6Y9-0`.
The longer status label was visually checked on desktop and English/Chinese mobile specimens. The existing source and evidence-coverage destinations remain. The optional footer consolidation considered during diagnosis was not applied.

## Applied: Terminal quote and selected-bar semantics

[Paper page](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-17-0).

The specimen showed an unqualified +1.53% quote change near a +3.05% selected-bar change. The selected bar had a known 3D open-to-close basis and a 15 October 2026 date; the quote lacked its own as-of time and return interval.

Applied:
- `1UEE-0` and `1V6I-0`: **Snapshot · time unavailable**.
- `1UDL-0` and `1V5P-0`: **3D bar · C 16.54 · +3.05%**.
- `1U03-0`: explicit design-example and selected-bar date.
- New native contract `1XOJ-0`, inside existing behavior board `1W4S-0`.

The historical +1.53% fixture remains in the Build note as an unqualified reference; it is withheld from the normal header. No quote timestamp was invented.

The contract requires quote source time, venue, currency and named return interval beside the value. The selected bar separately carries interval, bar date and open-to-close basis. An older bar selection must not rewrite the independently timed quote. Missing metadata, stale quote, closed market and an evidenced live connection remain separate states under the incumbent quote/chart owners.

Native dark desktop, light tablet and the new contract were visually inspected. Chart-led density, bar navigation, keyboard and volume guidance were retained.

## Applied: Intelligence Hub reading order and score labels

[Current Paper page](https://app.paper.design/file/01M2VWK62FA5S4VVF6G7SBPE5J/p-3-0).
[Build/reference page](https://app.paper.design/file/01M2VWK62FA5S4VVF6G7SBPE5J/p-2-0).

The US introduction repeated the same two setups above the actual setup section. It now has one entry: **Review LRCX and ANET**, followed immediately by the two inspection cards. The compact context retains both price-risk qualification and AXON’s research-only / weaker-price-action / unavailable-source status.

- Final compact heading/context: `6Z9-0`, within existing setup section `G6-0`.
- Original introduction `A8-0`, former section heading `G7-0` and redundant CTA wrapper `6Z8-0` are retained in Build/reference container `6Z2-0`.
- The live-layout copy was consolidated through node moves, without discarding the original references.

The score definitions were checked against the pinned engine before changing labels. The prominent example 51 is `opportunity_score`; the adjacent 85 is `edge_remaining * 100`. The latter is an input to the former, not an independent return forecast. The opportunity calculation incorporates signal, falsifier, remaining-edge and gap factors, then applies its existing cap/governor.

Applied in the US and China specimens:
- `B8-0,NT-0`: **OPPORTUNITY / EDGE INDEX**.
- `B9-0`: **DESK READINGS**.
- `G4-0,UT-0`: null-marker legend now **No directional reading**. A present source with no directional reading is not automatically absent coverage.
- Retained the distinct US/China desk names, including Policy as context rather than a ranking vote.
- Retained “Why it is here,” explicit entry status and links to original desks.

The final China check found that row captions still said “Early-stage” beneath the repaired header. The China producer and template were checked separately before aligning those captions. Its numeric value is also `edge_remaining × 100`, while `stage` is a separate category. Nodes `O7-0,OY-0,PP-0,QG-0,R7-0,RY-0,SP-0,TG-0,U7-0` now say **Edge index**; footer nodes `G5-0,UU-0` use matching terminology.

**Same field name does not mean the same model.** China’s `_edge_remaining` has its own components, weights and CSI300-relative inputs. The US and China engines remain separate; no cross-market calibration or direct score comparability is established by the layout.

The explicitly identified 27 September fixture at `bb310311b716ac3c7db7b7ed64d40039dd02bff7` confirms the first China row `000829.SZ`: `stage=early`, `opportunity_score=74.4`, `edge_remaining=0.811`, displayed as **Edge index 81.1**. Its published inputs also reproduce `100 × 0.798 × 1 × 0.811 × 1.15 = 74.42547`, rounded to 74.4. These are historical fixture values, not the November snapshot.

New native score contract `72N-0` appears before the retained overview blocks in `6Z2-0`. It gives the exact field mapping, incumbent US/China source paths, dated fixture proof and build acceptance criteria. The table headers, row captions and explanations now agree.

No score formula or entry gate was changed. A high research priority still does not establish entry eligibility. The compact US page, final China score-label specimen and new contract were visually inspected.

Sources:
- [US engine](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/engine/intel_hub.py).
- [China engine](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/engine/china_intel_hub.py).
- [China template](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/china_intel.html.j2).
- [27 September fixture](https://github.com/mastermindx-market-intelligence/macro/blob/bb310311b716ac3c7db7b7ed64d40039dd02bff7/site/china_intel/command.json).

## Applied: News comparison before provenance mechanics

[Paper file](https://app.paper.design/file/01M5EXPMQTSBFBAM8KKG83FTZH/p-1-0), current R3 board `27K-0`.

The Northwind specimen’s visible headlines cover venture/talk stage and a $1.4bn valuation. Those displayed headlines alone do not establish a factual contradiction. This is an audit of the design fixture; the underlying news articles were not verified.

Applied to expanded story `29O-0`:
- `29V-0`: transaction scope is explicitly unconfirmed.
- `29X-0`: the short explanation identifies the different details and asks whether they refer to the same transaction.
- `2A5-0`: unsupported “Reports differ” becomes **Scope unverified**.
- Source headlines `2AJ-0` and their existing expansion `2AQ-0` now precede grouping and clocks.
- `2AI-0`: grouping is provisional, with transaction, stage and valuation basis named.
- `2AU-0`: **Do both accounts describe the same transaction and stage?**

The existing report count, source entries, review action and receipt clocks remain. The unrelated next-check node `2BS-0` was left intact. The fresh recovery amendment `QO-0 → 2F7-0` was preserved.

New native Build contract `2FG-0` specifies the threshold for “Reports differ”: two comparable claims, each bound to its source excerpt/report identity, transaction or entity, period, stage, units and valuation basis. The UI must show the conflicting values or outcomes. Different wording, absent detail, or unknown scope does not establish contradiction.

Implementation must extend the incumbent story-group/evidence-ladder owner after checking its producer, preserving source access, membership, clocks and correction behavior. It must not add another ingestion, grouping, review or monitoring lifecycle. Test genuinely conflicting claims, compatible headlines, different periods, unknown scope, unavailable sources and corrected reports. “Mark reviewed” requires the existing save receipt, with interrupted outcomes reconciled before retrying.

The changed expanded story and complete new builder contract were visually inspected.

## Applied: Mastermind AI evidence and save viability

[Build page](https://app.paper.design/file/01M3P1QEHS5XXQY85BJT6QR2E1/p-9-0).
New source-linked Build reference: `5VN-0`, alongside existing `1MO-0` and `5M0-0`.

The complete pinned `templates/chat.html` uses the existing brain thread/history/stream routes and passes selected symbol/page context. It did not contain a `context_receipt` binding. This is an observation about that template; it does not prove that every backend response lacks evidence metadata.

The new reference specifies:
1. Bind Sources to a particular answer receipt: thread, answer/version, citation IDs, source clocks and access outcome. A selected-context badge alone cannot establish what supported an answer.
2. Historical answers without that binding display **Evidence details unavailable**. Opening/closing Sources preserves draft, scroll, selected answer and focus.
3. Verify the existing create-thesis API before promising **Saved · Monitoring off**. The preserved R10 boundary describes an active watched case. A genuine non-monitoring save must use the incumbent thesis/version owner and its correct receipt; creating an active case and then archiving it does not establish the intended state.
4. Build and prove answer receipts first; separately resolve save viability. Exercise old history, quota refusal, partial stream, interrupted save, source-access failures, missing receipts, stale answer states, Escape return and narrow EN/ZH layouts.

Existing brain lifecycle and allowance ownership remain in place. No alternative context, save or monitoring service was introduced. The native Build reference was visually inspected.

[Chat source](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/chat.html).

## Illustrations and motion reference

The ES Build page contains an editable vector storyboard, `3YE-0`, with four interaction moments. It explains settled view, intent/pending feedback, atomic response commit and returned context. The illustration is native editable Paper work.

The companion [expectation-surface-motion-reference.html](expectation-surface-motion-reference.html) is a self-contained implementation reference using explicit Paper fixtures:
- dark/light control;
- MU and INTC example selection;
- delayed and out-of-order responses;
- failure and retry;
- exact-number view;
- detail dialog and return;
- reduced-motion behavior.

It has no external script/assets, API, persistence or monitoring effect. Its plot is explicitly schematic: the file does not fabricate a historical time series or claim live data.

Validation: JavaScript syntax checked successfully with Node; one script and no external asset/script dependency were confirmed. Browser execution was **not verified**. Local Chromium could not launch in this environment. The connected browser then explicitly rejected an inline data-URL navigation under its security policy; no alternative carrier or protocol workaround was attempted. Native Paper screenshots are separate visual evidence and rendered successfully.

The reference is build material, not browser-tested production behavior. Required acceptance remains keyboard/focus, stale-response rejection, failure recovery, reduced motion, narrow layout and same-context return in the actual application.

## Feature viability and build sequence

The changes deliberately strengthen existing surfaces. They do not justify a new state, identity, query, save or monitoring control plane.

| Priority | Work package | Existing implementation or boundary | Done when |
|---|---|---|---|
| P0 | ES data meaning | Existing builder, template and page contract | Visible denominator matches generated data; each change shows its own same-period capture pair; first capture, rollover, zero-prior and missing-identity cases are truthful. |
| P0 | Quote and claim qualification | Incumbent Terminal quote/chart and News story/evidence owners | Unqualified quote changes are withheld or qualified; selected-bar context stays independent; contradiction badges require comparable source-bound claims. |
| P1 | AI answer evidence | Existing brain thread/history/stream and renderer | Sources shows the selected answer’s evidence receipt, with honest historical/missing/access states and preserved return context. |
| P1 | Save viability | Incumbent thesis/version/save owner | The intended non-monitoring save exists and is proven by its actual receipt; interrupted outcomes reconcile without duplicate effects. |
| P1 | Compact navigation and disclosure | Existing ES template, Hub pages and shared shell | Three-row mobile summaries expand correctly; exact numbers preserve selection/focus; existing destinations and per-page source status remain clear. |
| P1 | Interaction and motion | Existing component/chart stack | Last settled content survives pending/error states, obsolete responses cannot commit, labels and plot commit together, and reduced motion behaves correctly. |
| P2 | Optional historical study | Existing K3E inspection engine/query path | Immutable source revisions, paired hashes, UTC visibility clocks, alias provenance and explicit refusal states survive the consumer path. Saving/monitoring is separately implemented if required. |

Sequence the semantic fixes before visual polish in production. Evidence and save boundaries must be proven before their user-facing success states are enabled. Responsive implementation and motion should reuse the resulting state transitions rather than adding parallel local truth.

Exact production entry points not established in this pass—especially News producer details and the non-monitoring save API—remain explicit implementation discovery tasks. The Paper contract does not manufacture an endpoint or claim a capability is already deployed.

## Other inspected surfaces and preservation decisions

Market Guide’s question-led entry remains a useful pattern; no severe source contradiction was established. Ontology has substantial current context, evidence, recovery and retained comparison designs, but a shipped consumer for all proposed assembler behavior was not established. That gap remains explicit.

Prophet and Mastermind OS already separate substantial current/reference material. Canonical Design System and the original MASTERMIND PAGES migration remain protected. A uniform visual rewrite would discard useful product-specific density and current work. Terminal retains its chart-first visual language; GMI retains its relationship illustration.

No archive/delete operation was performed. Existing references were consolidated by relocation where supported and justified, with node identities retained. Archive/delete tools are blocked in this session; protected or uncertain work was never routed through a substitute deletion mechanism.

## Verification and delivery record

### Visual proof

| Surface | Inspected native output | Scope of the proof |
|---|---|---|
| ES | Five primary theme/locale/device variants, Study coverage, motion storyboard and updated Build plan | Visual structure, text fit and explicit data meaning. Final layout heights read back after semantic edits. |
| International | Start board `3RW-0` and directory `41M-0` | Core/surveillance reading path and retained frozen scope. |
| GMI | Desktop plus EN/ZH mobile examples | Longer historical-source labels fit; ten target updates acknowledged. |
| Terminal | Dark desktop, light tablet, new quote/bar contract | Quote qualification, selected-bar context and legible contract. |
| Hub | Final compact US page, China score-label specimen and market-specific score contract | Single setup entry, consistent score names, distinct market formulas and null semantics. |
| News | Expanded story and new comparison contract | Evidence order, unverified scope and precise next check. |
| AI | New source-linked Build reference | Complete, legible implementation sequence and boundaries. |

This is native design QA. It does not establish functional click-through, real data wiring, production browser acceptance, accessibility certification or a complete inspection of every artboard in all 35 files.

### Mutation and recovery evidence

All design writes used the native Mastermind Paper carrier with fresh snapshot guards and unique operation IDs. Representative final receipts:
- ES denominator labels: `paper-estate-20261108-es-final-denominator-labels-v1`.
- ES production/design boundary: `paper-estate-20261108-es-design-versus-runtime-boundary-v1`.
- GMI historical status: `paper-estate-20261108-gmi-historical-plan-status-v1`.
- Terminal labels/contract: `paper-estate-20261108-terminal-qualified-clock-labels-v1`, `paper-estate-20261108-terminal-quote-bar-contract-v1`.
- Hub labels/consolidation: `paper-estate-20261108-hub-score-and-null-labels-v1`, `paper-estate-20261108-hub-single-setup-entry-v1`; final market check: `paper-estate-20261108-hub-market-score-label-consistency-v1`, `paper-estate-20261108-hub-market-score-build-contract-v1`.
- News scope/order/contract: `paper-estate-20261108-news-qualified-comparison-v1`, `paper-estate-20261108-news-claims-before-clocks-v1`, `paper-estate-20261108-news-comparison-build-contract-v1`.
- AI source-linked reference: native node `5VN-0`, acknowledged writes and screenshot readback.

The International rename’s initial uncertain response was reconciled by reading the original target; it was never replayed. Later connection timeouts occurred on reads and recovered. No outstanding write effect from this pass remains unknown.

Working indicators were released only on this session’s exact 39 owned/edited root boards or containers across seven files. All seven `paper-estate-20261108-finish-<surface>-v1` calls returned `APPLIED_RESPONSE_OBSERVED`. The final market-label refinement was then released with `paper-estate-20261108-finish-hub-v2`, also acknowledged.

### Canonical delivery and limits

This directory contains the assignment, cumulative report and motion reference in the existing Macro PR #10617 programme. The HTML file matched its committed source exactly on readback at `52636ee4a8e64548983eea09bf629b6b3156b644`. Documentation updates use current blob SHAs and receive exact-content readback.

The final observed PR remains open and draft. No release hold was cleared, no approval was invented and no merge/deployment was attempted. Source reasoning is explicitly pinned to the SHAs above; advancing repository branches are not silently treated as re-verified source.

DO_NOT_REDO: accepted ES page separation and preserved node moves; reconciled International rename; current R14 freeze; GMI ten-badge repair; Terminal quote qualification; Hub single introduction; News recovery amendment; AI existing brain/thesis/allowance owners. Future implementation should begin with the concrete work packages above and prove real consumer behavior.
