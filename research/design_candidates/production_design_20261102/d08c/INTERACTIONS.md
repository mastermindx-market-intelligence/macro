# Interaction and state contract

This is the D08C design contract over existing owners. Logical actions below are not new API names or wire fields. Source semantics are pinned in [SOURCE_AUDIT.md](SOURCE_AUDIT.md). Proposed controls remain gated until the incumbent host and owner support them.

## State model

Keep four independent state dimensions: **draft/admission**, **calculation**, **Save/revision readback**, and **watch/firing/delivery**. A loading calculator cannot erase a saved revision; a failed watch cannot unsave the Plan; a missing receipt cannot establish non-application. Do not compress these dimensions into one green/red overall status.

### Research and calculation

| State | Visible result and copy | Allowed next action |
| --- | --- | --- |
| R0 Empty / first use | “Start with an exact contract.” Explain aggregate-only context | Return to investigation or select a valid source pin |
| R1 Incomplete | “Complete each leg's assumptions.” Inline missing/invalid fields; no numeric result | Edit side, quantity, entry or research text; blank differs from zero |
| R2 Loading | “Calculating expiry payoff…” tied to current draft revision | Edit/cancel viewing; edits invalidate old result and late response |
| R3 Unsupported | “Keep the plan; calculation is unavailable.” State mixed expiry/unsupported root reason | Inspect limits or explicitly edit; no silent leg removal |
| R4 Reference unavailable | “Dated contract reference is not qualified.” | Inspect available coverage; keep draft and all original evidence |
| R5 Stale evidence | Original snapshot and date remain visible | Fetch current inputs explicitly and show beside original |
| R6 Partial source | Name the missing source/panel; retain available panels with independent dates | Inspect available data; scoped refresh through existing reader |
| R7 Access unverified | “Options is temporarily unavailable. We couldn't verify access.” | Existing access-check recovery; no subscription inference |
| R8 Invalid/error result | “No usable calculation returned.” Clear current numerical result, retain authored draft | Inspect reason; a deliberate calculation request is distinct from Save |
| Qualified result | Return curve, cost and extrema with model/clock/source boundary | Values table, supported focus/full view, compare if compatible |

Guest, known denied/plan-required and expired-session variants share the access pattern but must use the actual owner result. Guest: “Sign in to continue this research.” Known denied: “Your current access does not include this feature.” Access-check failure must not display either of those stronger claims. Preserve a lawful local draft only under its current owner/custody rules; never expose former-account data. These are future variants, not states observed in this browser audit.

### Save and exact readback (C07)

| ID | Entry condition | Feedback / permitted recovery |
| --- | --- | --- |
| P0 Draft-only | No native Plan admission | “Account saving unavailable.” No request; clearly session draft; Copy draft remains a local escape |
| Local admission | Fresh native New, current owner/selection guards pass | Transfer complete draft; no ID generation, storage, calculation, watch or Save effect |
| P1 Pending | Native owner has verified retained command, then transmitted once | “Saving research…”; prevent second operation; immutable payload and identity |
| P2 Verifying reopen | Exact matching committed receipt exists | “Saved · verifying reopen.” Preserve known commitment; read exact revision |
| P3 Verified | Exact record/revision readback matches retained manifest | “Research saved · revision N.” Reopen that revision; watch still unarmed |
| P4 Unknown | Transmission could have applied, response/lookup inconclusive | “Save outcome unknown.” Reconcile original owner/operation; no Save again while unknown; Copy draft does not resolve the original effect |
| P5 Definite rejection | Exact owner evidence establishes not applied | Preserve draft and owner reason; Copy draft remains available; only owner-supported correction; no automatic retry |
| P6 Receipt/revision mismatch | Returned identity, revision, lifecycle or manifest differs | “Returned revision needs review.” Preserve any already proven commitment; no latest fallback or note-only substitute |
| P7 Session/owner changed before confirmation | Access lost before the original command is confirmed | Generic access recovery; hide A's data from B; retain A's original custody. If commitment was already proved, keep that fact and use P12; access loss never downgrades it to unknown |
| P12 Commit known, readback unavailable | Matching committed receipt, exact revision read fails | “Saved; unable to reopen.” Retry read only; never resend Save |
| P14 Scoped source unavailability | Complete revision verified, linked original source cannot open | “Saved; source unavailable.” Keep original reference, label which source is unavailable |

`not_found`, 401, timeout, malformed response and result-only receipts in legacy owner-recheck cases do not settle the original command. Session storage is custody, not server persistence; failed journal write/readback yields zero Save requests. An incomplete Plan return is never a successful whole-case save. “Partial” must name the independent part: source availability or watch activation, not an ambiguous overall success.

### Watch, firing and delivery (C07)

P8 is verified research with watch not armed. Setup opens the incumbent preview and requires supported condition semantics. P9 requires confirmed active status. P10 is activation outcome unknown and retains the original condition/operation; no duplicate activation. P11 is owner-confirmed activation failure with Plan Save unchanged. P13 keeps a confirmed firing even when delivery readback is unavailable. Rearm is a separate explicit action; it never follows navigation or review automatically.

Revisit keeps the full supplied firing history reachable through the existing receipt-detail view. Every receipt preserves its own `payload.value`, source vintage, condition and firing identity. An older receipt never borrows the alert row's latest trigger reading. A correcting receipt follows its original without replacing it. Distinguish queue `read`, `unavailable` and `absent`; absence from a capped readable queue is not proof of nondelivery. A latest-firing summary must not discard the underlying receipt list.

Current supported previews are price threshold and options-wall proximity. The price comparator is strict and evaluates on the incumbent hub cadence; copy must not claim a crossing event. Wall proximity is EOD and cannot stand in for an exact selected strike. Exposure change, rotation and event-time conditions remain unsupported until their existing owner admits an evaluator. D08C adds no poller, queue, outbox or alert service.

## Primary interaction table

All ordinary navigation is read/local UI only. Route bytes and return metadata must be validated by the existing owner, same-origin and non-sensitive. “No route change” means no newly invented query/hash; it does not override an incumbent admitted host transition.

| Control / action | Precondition and effect | Feedback / route | Focus, keyboard, scroll and failure |
| --- | --- | --- | --- |
| Back to SPY exposure / originating investigation | Validated return context; no writes | Restore original node/lens/vintage and filters; disclose named fallback if gone | Restore focus to actual surviving trigger/row; retain origin scroll anchor |
| Views picker | D08 native panes available | Existing destinations and aliases only; Plan task does not create `tab=plan` | Keyboard menu, Escape closes, focus returns to Views; phone full-height list if needed |
| Build research plan | 1–4 unambiguous actual contract pins, same exact root; no duplicate identity | Create detached local draft; original rows unchanged | On refusal name aggregate/ambiguity/root issue; return to originating selection |
| Edit contracts | Existing local draft | Existing exact-contract selector; no Save and no implicit source refresh | Dirty-state review before destructive replacement; cancel keeps inputs |
| Entry summary / Adjust | Open one assumptions dialog using native host | Per-leg prices, not aggregate debit input; no route payload | Focus first relevant field; focus trap; Escape/Cancel preserve original; Apply restores trigger if still present |
| Side / quantity / entry edit | Draft validator and producer-bound checks distinct | Inline errors; zero price valid; quantity whole positive; invalidate old current result | Preserve entered string while invalid; do not coerce blank/locale commas silently |
| Research details | Thesis/invalidation/horizon existing fields | Reachable from plan and C06; no silent deletion | Textareas grow/scroll, labelled counters only at actual schema limit; errors linked to field |
| Apply to draft | Complete valid form or explicit supported incomplete draft handling | Local canonical update, old calculation cleared; no Save/watch | Announce change once; request calculation separately through supported control |
| Calculate expiry payoff | Prepared request plus owner access | Existing expiry POST; input fingerprint/request guard | Loading announced politely; late response discarded after edit/context change |
| Before-expiry / model limits | Existing endpoint lacks pre-expiry path | Unavailable explanation; do not expose operative IV/date/rate sliders | Disabled controls have adjacent reason reachable without hover |
| Focus/full curve | Qualified curve | Subset/full existing producer samples only | Keyboard-accessible range; preserve selected sample; no interpolated values |
| Values table | Same qualified curve/units | Table alternative, exact returned samples; break-even annotation separate | Semantic headers, keyboard navigation, bounded component scroll; no whole-page horizontal overflow |
| Compare assumptions | Proposed branch comparison admitted by D08; baseline retained | Local alternatives and compatibility header; no Save | Focus comparison heading; Back returns exact baseline and scroll |
| Select baseline/alternative | Explicit local choice with dirty-state review | Copy exact per-leg assumptions into draft only; show which changed | Cancel leaves baseline untouched; never Save implicitly |
| Open original evidence | Retained reference and owner permission | Original snapshot/reference; label unavailable instead of replacing | Return focus to original link; preserve Plan draft/context |
| Get current inputs | Explicit separate read, correct exact identity | New observation alongside original with independent clock | Late wrong-root response discarded; partial/error does not overwrite saved evidence |
| Save research | Admitted incumbent owner protocol; current owner; fresh/expected revision | One native immutable command; P1→known/unknown outcomes | Prevent duplicate keyboard/click submission; aria-live state; never create a new operation on timeout |
| Check original save | Original owner and operation retained | Existing owner reconciliation only | Disable effectful resubmission; unresolved lookup remains unknown |
| Copy draft | Currently authorized visible research; deliberate clipboard action | Copy readable exact identities, assumptions, provenance and research text; label “Draft copied — not saved to account” | Clipboard denial/failure is explicit; no API, operation ID, Save settlement or account transfer; do not expose retained data from another owner |
| Open saved research | Exact owner record + revision | Exact-revision reader; not “latest” | Mismatch withholds content; read failure preserves known commitment |
| Set up watch | Saved revision and supported owner condition | Independent preview then explicit owner activation | One overlay; release Save dialog first; no automatic arm |
| Inspect firing history / correction | Existing owner-linked receipt list | Read each supplied firing with its own value, source vintage and delivery evidence; preserve correction links | Exact original remains reachable; missing receipt data is labelled; no borrowed latest reading or invented event ID |
| Draft revision from current inputs | Explicit adoption after showing change/basis | New local draft retaining provenance; later native Save creates new revision | Review authored entry separately; current marks do not become entry silently |
| Assess research | Exact original revision + authored assessment | Confirmed / contradicted / inconclusive becomes new native revision | Preserve original evidence and linked correction; no overwrite |

## Comparison compatibility

Current shortlist `likeForLike` means enough pins, same list family/session and no stale flag. It does not prove matching root, expiry, strike, right or terms. Use “Same observation basis” and list differences. The current `termsUnknown` check covers multiplier only, not all terms.

For a Plan payoff overlay require common exact root, expiry, USD unit basis, qualified applicable terms, compatible model/basis and **identical returned/requested spot axes**. Keep quantity basis explicit. Different fixed grids use separate panels/evidence tables; do not interpolate onto a fabricated shared axis. Different roots/expiries may remain inspectable evidence, not a ranked numerical comparison. At most three visible Plan columns in C02 is a presentation specimen, not a new backend limit; retain current four-pin observation comparison and provide bounded column selection on narrow screens.

C02's total debit is derived from retained per-leg assumptions. A builder must not submit a net debit as an invented request field. Missing costs do not equal zero. A blank break-even array means no discrete roots returned; it does not prove P/L is never zero, because a zero plateau is possible.

## Responsive and access contract

| Viewport | Shell / useful width | D08C behavior |
| --- | --- | --- |
| 320 | Drawer, 56px header, 16px gutters → 288px | One analytical column; stacked metrics/leg rows; full-screen editor; C05 full-scroll light ZH specimen |
| 390 | Drawer, 56px header, 16px gutters → 358px | C04 844px viewport; summary payoff, compact exact legs, evidence/limits, primary compare action |
| 768 | Drawer, 56px header, 20px gutters → 728px | One-column plan; single 440px editor modal shown in C06 |
| 1024 | 196px nav, 64px header, 20px gutters → 788px | C03 two-basis review table; 440px modal, no dock |
| 1280 | 224px nav, 64px header, 24px gutters → 1008px | Primary analysis plus supporting panel; inspector only if 320+24 leaves required analytical width |
| 1440 | 224px nav, 64px header, 24px gutters → 1168px | C01/C02 two-column/three-comparison layout |
| 1600 | 224px nav, 64px header, 24px gutters → 1328px | Maintain readable text and chart density; no uncontrolled card stretching |

F01 dock threshold is useful width ≥984 and remaining content ≥640 (or larger domain minimum), with 320px inspector +24px gap. D08's local hierarchy threshold680 is separate from docking. Never stack inspector, Plan editor and Save sheet. At narrow widths a single full-screen sheet replaces the previous overlay and preserves its conditional return target.

Use F02 mapped neutral surfaces/lines; no colored container borders or accent stripes. Legitimate focus outlines remain visible. Number meaning and direction do not change with EN/ZH or theme. Financial numbers use normal tabular figures rather than globally forcing monospace. Dates show year where identity requires it, exchange timezone and explicit unit/currency; internal identifiers remain unlocalized.

Important mobile controls have a 44px house target; visually small links need a real padded hit area. This is not a claim that WCAG AA requires44px. At 400% zoom, reflow to a single column; complex 2D comparisons may scroll inside a labelled component with a stacked/table alternative. No whole-page overflow. Hover is never the sole way to read an assumption or error.

Focus order follows visual reading: task context, result, assumptions, exact legs, evidence, action. Charts expose a textual summary and values table. Errors use text/icon/status as well as color. No payoff tween that looks like changing data; prefer immediate numeric replacement with a short nonessential crossfade only after a valid result. Respect reduced motion and preserve focus on update. Actual keyboard, screen-reader, touch, zoom and reduced-motion proof remains a future browser gate.
