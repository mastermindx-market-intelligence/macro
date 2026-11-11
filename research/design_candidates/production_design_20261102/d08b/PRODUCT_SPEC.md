# Product specification

## Job, user and completion

The primary user is an options researcher investigating a dated observation before committing it to a research plan. The user needs to answer: **where is the exposure, what exactly contributes to it, how does it compare with a compatible observation, and what source evidence survives the transition into another analytical view?**

The first useful screen must identify the exact underlying and dated book, expose the matrix and spot reference, qualify the known subtotal, and offer a clear selected-node action. Analytical depth remains reachable through deliberate controls. No probability, flow, freshness or tradability claim is implied merely because a shape is compelling.

Design completion means editable compositions and source contracts cover both assigned journeys, protected controls, exceptions and cross-slice transitions. Reference acceptance requires the existing review process. Implementation completion will additionally require actual keyboard/touch/browser paths, accepted foundation integration, source truth and access tests. This commission supplies the former package and the latter acceptance contract; it does not implement or deploy the product.

## Product model: related views, different meanings

| Object | Question | Meaning that must survive |
| --- | --- | --- |
| Exposure matrix | Which strike/expiry carries which exposure? | Qualified source projection; explicit metric/unit/sign, missing cells and selected scope |
| Selected node | What contributes to this cell? | Aggregate flag, constituent qualification, source clocks and exact coordinate |
| GEX price profile | How does the modeled gamma curve change across spot? | Model parameters, assumed signs, sampled grid and source date |
| Matched observation comparison | What changed among the same qualified contracts? | Same identity/definition/scope, finite intersection, lawful cutoff, separate membership differences |
| Flow Surface | How do field snapshots vary across strike and session time? | Existing temporal snapshot grain; candle interval does not resample the field |
| Volatility term/smile | What is reported for this exact expiry/strike? | Percent units, exact expiry, nullable observations, method and cadence |
| Qualified gamma 3D | Can spatial structure help investigate the same matrix? | Discrete source-derived columns; same projection/selection and exact 2D alternative |
| Published chain Lab | How do published volume/OI/ΔOI coordinates differ? | Mirrored side, ordinal expiry depth, hollow negative ΔOI and full-snapshot scale |
| Levels/positioning | Which dated model levels and structural context are relevant? | Exact price anchors, source roles/scores, separate quote/model clocks; no unproved probability |

“Surface” cannot collapse these objects into one model or source namespace. The design uses descriptive subtitles and metric units to disambiguate them, while retaining the existing route aliases and source owners.

## Journey J1 — Underlying to a qualified selected node

**Entry:** valid exact underlying from an existing Options root control or an A→B handoff. Preserve originating evidence and return context. When only a root transfers, state that the receiving book is broader than the originating print; do not manufacture a same-contract link.

1. Validate the exact source root/listing. On root change, clear old-root numbers and selection immediately; show an identity-bound skeleton. The old response may not repaint under the new root.
2. Load the appropriate dated source book and show its session separately from spot time, OI position session, OI report date, availability and build/retrieval times.
3. Present a qualified known subtotal when only some rows are supplied. Say which denominator is reported rows, rendered grid positions or source collection. Unknown collection coverage remains unknown.
4. Navigate or tap to a strike/ISO-expiry cell. Selection is independent from hover; keyboard focus and selected state are visibly distinct.
5. Inspect the node: signed net, its unit, call/put contributions where supplied, selected expiry versus all-expiry strike aggregate, qualification, distance to dated spot and matched-comparison eligibility.
6. Resolve actual source contracts before any C-owned pin. An aggregate with two rights is not a single contract. Missing adjusted-root/terms/series evidence remains explicit.

**Exit:** either continue to J2/J3/J4 or return to the exact originating scan/view. Restore root, book, filters, node, focus and scroll when still valid; otherwise name the unavailable original and an explicit fallback. B01–B03 and B10–B11 compose this path.

## Journey J2 — Compare the same qualified observation basis

**Entry:** selected node or explicit book-history comparison. B chooses presentation; the incumbent archive/coordinator owns available vintages.

The user selects previous and current source sessions. The **existing temporal/coordinator owner supplies the effective knowledge cutoff**. A comparison entered without historical context defaults only to an owner-stamped current-knowledge comparison; an inherited historical cutoff is retained across navigation and is never silently replaced with the current clock. The basis shows the actual cutoff, timezone and current-knowledge/historical mode. Unknown cutoff or availability keeps the existing unavailable result.

The comparator first validates identity, security/root, scope, definition and time. Both observations must be known by that cutoff; source dates must advance strictly. It then intersects actual member keys `(expiry, strike, right)` whose values are finite in both observations. The common cohort is computed globally before visual breakdown, not independently per displayed strike. The example compares with knowledge as of **Nov 3, 2026 at 04:15 ET**; its Nov 2 observation became available Nov 3 at 03:52 ET. It is therefore not a claim that the comparison was knowable during Nov 2.

The comparison view shows previous and current values, signed net change, gross change and net-magnitude change as different quantities. It separately counts previous-only/current-only reported rows, qualification gained/lost and unavailable members. Set differences are reported differences, not economic entry/exit. Empty finite intersection or incompatible methods leaves both observations inspectable but withholds a numeric delta.

The illustrative selected node has call `+380M → +400M` and put `−156M → −132M`. The matched net changes `+224M → +268M`, or `+44M`. Gross changes `536M → 532M`, or `−4M`. Neither number is a trade-flow measurement. B07 renders the evidence and B09 renders refusal. Percent change and velocity are not added when the existing comparator leaves them null.

**Exit:** return to the same node/lens/vintage. A compare-plan action goes to C's existing owner after exact contracts have been admitted; B creates no plan or saved scenario.

## Journey J3 — Explain the node with volatility and positioning

From the selected exposure node, the researcher opens Volatility with its exact root and intended expiry. If the source lacks that expiry, the selection remains visible and unavailable; an explicit chooser offers other dates. Nearest-tenor data is never silently substituted.

The term structure and smile retain distinct purposes. Term structure compares reported expiry observations; a missing point leaves a genuine gap. The smile displays nullable call/put IV by strike for the selected expiry; call and put receive distinct shapes/line styles as well as color. IV input method and quote inputs remain “not supplied” when absent. Default trimming of unreliable deep-ITM wings is visible and reversible; it cannot turn trimmed data into absent source data.

Headline IV, realized volatility and published VRP retain their specific horizons and source methods. A display difference is not automatically a cheap/rich verdict. History, rank windows, long-window coverage/since and source values remain reachable. Macro `iv_rank` and Terminal `iv_rank_252` are not renamed into a single method. Opposite RR25 subtraction orders are preserved as explicit methods rather than normalized by label.

Positioning and Levels remain related context with their own source/session. The researcher can inspect price map nodes, confluence, void ranges, named roles, source notes and dated positioning/flow/volatility context, then return to the original exposure node. Exact price ticks survive label displacement. A null regime remains Unknown. Brightness, stability, magnets or pin targets do not establish calibrated probabilities unless the owning producer supplies that evidence. B04, B08 and B14 compose this path; B07 preserves a separate context transition.

## Journey J4 — Investigate 3D without losing the exact 2D task

### Qualified exposure columns

B05 renders actual qualified gamma-cell values as discrete signed columns. The builder retains net/gross/absolute-net modes, 2/4/8% windows, 5/9/15 expiry caps, elevation presets and full-lens tiers. The selected cell remains bound to ISO expiry, strike, source snapshot, population, lens and unit. Cropping cannot change a retained cell's magnitude tier. The standard matrix's P95/square-root color scale and the Surface's full-lens tier scale must retain separate explicit legend identities; one is not substituted for the other.

The exact 2D path is a peer representation of the same projection. It exposes all admitted coordinates, including zero and unavailable cells, the same filters/mode/cap, full-lens totals, source qualification, comparison and inspector. Phone may show one expiry at a time or page a contained table; every expiry and row remains reachable. It may not silently reduce the source population. B06 and B11 demonstrate exact values; B02 preserves the dense slice. Reordering, paging and representation changes retain selection by identity rather than row index.

### Published chain point cloud

B13 retains the separate Research Lab. X separates calls and puts using magnitude, Y is strike, and depth is ordinal expiry. Negative ΔOI is hollow, not moved to the opposite side. Marker area reflects magnitude under the incumbent square-root/minimum/density-cap rules. Full admitted snapshot scale remains fixed across filters. Zero/null produce no 3D mark but remain distinct in the exact table. The draw cap is 20,000 nonzero marks; it does not truncate the exact admitted dataset.

Retain volume/OI/ΔOI, side and expiry filters, reset/front/top views, orbit/zoom, arrow selection, three-item comparison, 50-row pagination, source-coordinate inspector and focus restoration. The table remains available in 3D mode; below 600px it is the initial representation. The coordinate is not an exchange-qualified instrument. OI reference session and availability remain unknown when the adapter supplies null. IV may join only on exact coordinate and matching source session; no fitted IV surface is promised when `fit` is null.

### Accessible and resilient completion

No task requires rotation, hover, color discrimination or WebGL. Reduced motion starts without auto-orbit; camera transitions are immediate or short and user-initiated. WebGL/context failure leaves the exact table, filters and selected inspector usable. Replay and scenario links retain their current admission boundaries: missing chain/availability evidence is an honest unavailable lens; Scenario opens the C-owned Plan without transferring an unqualified coordinate. Saved Investigation remains unavailable until its existing owner admits options evidence.

## Information hierarchy and composition

The desktop uses one primary analytical object with a selected inspector when the actual available width permits it. A small summary row distinguishes the known subtotal, largest strike and source qualification. Long methodological detail belongs in Source & calculations, while essential clock, scope and missing-total qualification stays beside the observation.

Phone stacks readable summaries and qualification, then metric/lens/expiry controls. Complete Views and Research controls replace clipped horizontal navigation. The dense matrix supports scanning; Exact values provides a reliable 48px row target for precise selection. The inspector uses full-width details, with an explicit return control and retained context. A longer page is preferable to hidden horizontal controls or fabricated collapsed analytics. No unseen desktop inspector is left consuming phone width.

Light/dark and EN/ZH are demonstrated across the candidate. Translation must retain ISO identity, sign, scale, units and source semantics; concise localized labels may wrap. The shell geometry is F01/F02 candidate.4 pending release, not a new global shell fork.

## Product success measurement plan

Measure task completion and interpretation, not screenshot preference. Proposed moderated tasks ask users to find a selected node, explain the subtotal limitation, identify the correct exact contract, compare two valid sessions, recognize an incompatible comparison, preserve expiry through a missing-data state, and complete the same 3D task in exact 2D on phone and keyboard.

Record successful completion, wrong-node/expiry selections, unsupported-flow or probability interpretations, abandoned controls, return-context loss, and time to the first correct source-qualified answer. Establish a baseline from the current served experience before setting improvement targets. No measured usability improvement is claimed by this design return. Instrument only existing approved telemetry pathways; do not create a new analytics or identity plane.

## Explicit limits

No new market data, fitted volatility model, observed dealer inventory, calibrated probability, durable save, replay engine or entitlement is supplied by the design. These are conditional capabilities under their existing owners. The [retention ledger](CAPABILITY_LEDGER.md) preserves the useful controls and source-specific meanings while identifying unavailable dependencies. Foundation release, admitted review and future functional acceptance remain separate gates.
