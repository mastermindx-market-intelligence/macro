# Product brief and retention ledger

## Product and job

The primary user is an options researcher moving from an observed signal to a reproducible hypothetical plan. The user needs to answer: **Which exact contracts and observations informed this plan? Which values did I assume? What happens at expiry under those assumptions? What changed when I return?** This experience supports research judgment; it places no order and creates no position.

The first useful view should show the analytical result or its exact unavailability reason, the selected legs and the next deliberate action. Deep inspection remains available without requiring the user to read a chain of explanatory cards before comparing two hypotheses. Research thesis, invalidation and horizon are first-class authored information, not decoration beneath a payoff chart.

The current consumer, producer, persistence and Paper sources are pinned in [SOURCE_AUDIT.md](SOURCE_AUDIT.md). Status labels below mean **current source**, **held implementation**, **proposed UX** or **unavailable dependency**. They are not interchangeable.

## Complete journeys

### A. Investigation to an authored research plan

1. From D08B exposure/structure, inspect the selected node and its scope, unit and source date. An aggregated cell can supply context, but only separately resolved unambiguous contracts can become legs.
2. Select one to four exact source pins. Preserve each copied row, raw clock, list/session and terms; reject duplicate exact contract identities within the draft. Do not normalize SPY1 into SPY.
3. Open the contextual Research plan through the incumbent host. Its title names the exact root and visible strategy summary; the exact-leg view preserves complete identities even when a title is abbreviated.
4. Author side, whole quantity and entry premium for each leg. Existing marks remain evidence. Editing a net debit summary opens the leg editor; it is not a new aggregate-price request field.
5. Add thesis, invalidation and horizon. The draft can remain incomplete or contain a research structure the expiry calculator does not support.
6. Request the supported hold-to-expiry calculation. Eligibility is narrower than draft validity: supported ordinary root, common expiry, complete assumptions, exact qualified dated reference and matching response contract. Unsupported drafts remain intact with a reason.
7. Inspect payoff and a values table. Read the calculation basis, signed units, costs status and source/reference clocks. Before-expiry prices, POP and trade fills are not implied.

### B. Compare hypotheses without changing the baseline

1. Select Compare from the plan. Create a detached alternative in the same transient editing context; do not create a durable record or Save operation on navigation.
2. Show the changed inputs first. For C02, the alternatives use the same legs, expiry, quantities and fixed spot axis; only the long-leg authored premium changes: 5.20, 5.40 or 5.00, with short-leg 2.00 unchanged.
3. Display unqualified/evidence-only plans without a numerical overlay. A field-by-field observation comparison remains useful even when an economic comparison is unavailable.
4. For compatible qualified results, show total USD values, baseline-relative differences and line styles. No “best trade” ranking or unprovided return-on-margin/POP measure.
5. Returning to the plan preserves the baseline. Selecting an alternative, if later admitted by the D08 host, is an explicit local draft action with dirty-state review. Save is still separate.

Comparison of authored Plan branches is a **proposed UX extension**, not a claim that current pin comparison implements it. The existing pin comparison remains reachable and retains its richer per-cell missingness states.

### C. Explicit Save, independent watch, later review

1. While native Plan admission is unavailable, show session draft status and the precise unavailable account-saving action. Do not route around the incumbent gate.
2. When the original owner admits Plan persistence, transfer the complete draft into a fresh native Investigation draft. Local admission is not Save and performs no request.
3. On explicit Save, the owner retains and verifies one immutable command before transmission. Disable duplicate submission; preserve owner, operation ID, record ID, expected revision, manifest and original intent.
4. Distinguish uncertain effect from a matching committed receipt. Verify the exact revision before claiming a complete reopen. If commitment is known but readback fails, say the research is saved and recover readback only.
5. Offer watch setup separately. Only existing supported condition semantics may be previewed; arming needs an explicit action and owner confirmation. A verified Plan may coexist with an uncertain watch.
6. Reopen the exact saved revision. Show original evidence alongside separately fetched current inputs. An observed mark does not overwrite an authored entry.
7. A new assessment or adoption of changed inputs creates an explicit new native revision after review. Reopening, navigation or viewing current evidence never mutates the original.

### D. Save timeout or session change

After a lost response, do not classify the write from network failure alone. Keep the original owner command, show outcome unknown, and reconcile the original operation through the existing owner. `not_found`, malformed output or expired authentication is not proof of non-application. A different account sees no former owner's Plan or receipt. Returning to the original account can resume the same custody; it does not create a fresh request. This assignment executes none of these writes or replays.

## Information architecture

D08 retains the Options navigation contract. Research plan, Compare, Saved research and Revisit are task-level views within the incumbent host. The Views picker remains reachable on phone and desktop; all 15 native pane families and existing aliases survive. No global navigation item, new route registry or closed-query extension is introduced here.

The visual hierarchy is **payoff or unavailable reason → exact legs and assumptions → evidence and model detail**. Thesis/invalidation/horizon live in the assumption editor and saved review, with an explicit research-details disclosure from the plan. Structure remains an upstream task; all seven existing panels remain accessible from the validated return and Views destinations.

## Capability retention ledger

Every relocation names a reachable successor. No capability has a REMOVE disposition; removal would need a separate authorized product decision. “Reviewer decision pending” is intentional until formal RIG review.

| ID | Existing capability / source or Paper reference | Disposition | Successor and reason | Dependency / interim behavior |
| --- | --- | --- | --- | --- |
| L01 | Options native panes and legacy destinations; `OptionsWorkspace` | RETAIN | D08 Views picker plus existing navigation | D08 route owner; do not add Plan query keys |
| L02 | Default Tape and URL tab restoration | RETAIN | Existing host | Navigation never saves or refreshes a pin |
| L03 | Structure root entry and SPY default; `StructureView` | RETAIN | Structure task via Views and validated back target | Exact root guards and stale-response suppression survive |
| L04 | OI by strike | RETAIN | Structure panel | EOD basis, nondirectional; no live badge |
| L05 | OI by expiry | RETAIN | Structure panel | Missing panel does not suppress other panels |
| L06 | 18-month calls/puts OI history | RETAIN | Structure history view | Preserve range and source dates |
| L07 | Put/call history | RETAIN | Structure history view | No directional inference added |
| L08 | Max-pain intrinsic curve | RETAIN | Structure analytical view | Keep methodology; not a forecast or order |
| L09 | Max pain by expiry | RETAIN | Structure expiry view | Preserve exact expiry identities |
| L10 | Sortable OI changes, root/all scope | RETAIN | Existing `OiChangePanel` | Lazy cross-root load; explicit retry after failed load; no polling |
| L11 | D08B node/cohort evidence | IMPROVE | Visible return + pinned evidence in C01/C04/C05 | Aggregate-only refuses leg admission |
| L12 | Four-pin shortlist and copied observations | RETAIN | Existing shortlist + Plan entry | Cap 4; repeated pin is not a refresh |
| L13 | Exact contract/list/session identity distinction | RETAIN | Full exact-leg disclosure; labels may abbreviate only visually | Unknown terms remain unknown; root suffix preserved |
| L14 | Current pin comparison | IMPROVE | Existing observation comparison, reachable from shortlist | Label `likeForLike` as same observation basis; not economic equivalence |
| L15 | Comparison missing / not in list / not supplied cells | RETAIN | Accessible observation comparison table | Never collapse to 0 or a generic dash without reason |
| L16 | One-to-four-leg detached Plan | RETAIN | C01/C04/C05 plus existing draft editor | Same exact root, unique identities; unsupported research preserved |
| L17 | Buy/sell and quantity per leg | IMPROVE | Exact-leg editor and 44px controls | Whole 1–1,000,000; signs come from side |
| L18 | Per-leg authored USD entry | IMPROVE | C06 explicit leg-price fields | Zero is valid; observed mark never autofills |
| L19 | Thesis, invalidation, horizon | RELOCATE | Research-details disclosure → C06; retained in C03 | No deletion beneath the new payoff hierarchy |
| L20 | Expiry request and qualified result | IMPROVE | C01 payoff/values table; R2–R4/R8 states | Existing fixed-grid endpoint; whole-result qualification |
| L21 | Focus/full curve view | RETAIN | Payoff chart range control and values table | Select existing samples only; no fabricated hover sample |
| L22 | Signed debit/credit, extrema and break-even | IMPROVE | Explicit labelled metrics with raw signed data retained | `max_loss` is signed worst P/L; UNBOUNDED stays unbounded |
| L23 | Fees and slippage uncertainty | RETAIN | Visible “Not supplied / net after costs unavailable” | No zero-cost assumption or hidden net estimate |
| L24 | Pre-expiry scenarios, IV/rate/time controls in old Paper `G9Q-0` etc. | BLOCKED_DATA | Model limits disclosure, descriptive disabled affordance | Existing Plan endpoint is expiry-only; producer owner must admit an extension |
| L25 | Modeled alternatives in old Compare `KD8-0` | IMPROVE | C02 supported entry-assumption comparison; preserve source reference | Old modeled numbers are reference, not current validated output |
| L26 | Authored branch comparison | IMPROVE / PROPOSED | C02, evidence table when incompatible | D08 admission and owner-calculated common axis required |
| L27 | Scenario capture retention | RETAIN | Native Investigation's existing scenario path | Held Plan-v3 conflict must be explicit; never discard scenario_capture |
| L28 | Local Plan host focus/visibility | RETAIN | Existing `OptionsPlanInvestigationHost` | Do not make a second host or storage layer |
| L29 | Native New/admission workflow | BLOCKED_DATA | Original #804 interface after lawful release | Protected composition lacks admission; current UI remains draft only |
| L30 | Whole-case Save `KWI-1` and verification `L6U-1` | IMPROVE | C07 P0–P7, P12/P14; existing owner | No note-only fallback, duplicate Save or new endpoint |
| L31 | Pending journal and legacy custody | RETAIN | Existing Investigation journal | Storage failure blocks transmission; not a durable account Save |
| L32 | Uncertain outcome reconciliation | IMPROVE | P4/P7/P10 and exact owner actions | Original operation only; no blind retry or carrier switch |
| L33 | Exact saved revision reopen `L94-1` | IMPROVE | C03; P12 distinguishes known commit/readback unavailable | No “latest” fallback or N→N+1 substitution |
| L34 | Original vs current observations | IMPROVE | C03 side-by-side dated basis | New acquisition explicit; does not rewrite saved assumptions |
| L35 | Research assessment / evidence-to-decision `LLG-1` | RETAIN | Revisit assessment panel | Confirmed/contradicted/inconclusive create new immutable revision |
| L36 | Included prints and linked packages `NUB-1/NZE-1` | RELOCATE | Original evidence disclosure from C03 | Preserve exact references and source unavailability |
| L37 | Price threshold watch | RETAIN | D23/native watch preview | Existing strict threshold on hub cadence, not proof of a crossing |
| L38 | Options-wall proximity watch | RETAIN | D23/native watch preview | EOD basis; an exact selected strike is not this condition |
| L39 | Exposure/rotation/event watch ideas | BLOCKED_DATA | Unsupported-condition explanation | No current evaluator; no request or invented scheduler |
| L40 | Firing history, corrections and delivery receipts | IMPROVE | P9/P13 → existing Review receipt detail; retain every supplied firing | Each receipt keeps its own observed value/vintage; corrections follow their original without replacing it. Read/unavailable/absent queue states are distinct; capped absence is not nondelivery |
| L41 | Separate arm/rearm | RETAIN | Explicit owner action after preview | Save/revisit never automatically arms or rearms |
| L42 | Actual positions and account exposure | RETAIN (D22) | Existing Portfolio/holdings destination | No conversion from hypothetical Plan to actual holding |
| L43 | D08D replay / return context | RETAIN | Validated original evidence link and return | No cursor conversion, replay authority or archive service added |
| L44 | EN/ZH, dark/light and narrow layouts | IMPROVE | C01–C10 responsive specimens; F01/F02 primitives | Final foundation release and rendered 400%/keyboard proof remain gates |
| L45 | Keyboard, touch, focus and chart access | IMPROVE | Single dialog, conditional focus return, values table | Actual interaction tests are future acceptance, not screenshot proof |
| L46 | Build/reference pages `p-P-1` | RETAIN | Existing references plus new D08C Read me / source package | Old held/empty boards remain untouched |
| L47 | Copy-draft escape in retained Plan/Save references | RETAIN / OWNER BINDING PROPOSED | C07 P0/P4/P5; deliberate readable local copy | Copy is not account persistence, receipt settlement or permission to repeat an uncertain Save; respect current-owner access and clipboard failure |

## New proposals, explicitly separated

Plan-branch comparison, the revised task hierarchy and the new owner-backed revisit composition are design proposals. They reuse existing data and ownership but need integration admission and implementation. No new numerical model, proprietary dataset, order entry, execution instruction, portfolio model or persistence service is proposed.

The C01–C06 numbers are synthetic educational design fixtures. Multipliers are assumptions until the producer qualifies exact reference coverage. The reference price is not an authored entry and is not a live executable quote. A future builder must bind the labels to actual provenance instead of copying these fixture dates.

## Success measurement plan

Future user evaluation should measure whether a researcher can identify the assumed entry versus observed mark, find the exact contract/source date, explain why a curve is unavailable, compare one changed assumption, recover a lost Save response without a duplicate, and reopen the exact assessed revision. Record completion rate, time-to-first-correct-action, misinterpretations and assistance needed, separated by phone/desktop and locale.

No usability, conversion, latency or accessibility result is asserted by this design package. A later owner may use existing telemetry facilities after approval; this package creates no telemetry pipeline or user tracking.
