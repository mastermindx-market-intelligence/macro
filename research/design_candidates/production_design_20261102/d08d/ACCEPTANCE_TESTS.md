# Acceptance tests and verification status

**The cases below are acceptance requirements for a later authorized build. They are not executed product test results.** Executed work in this design assignment is limited to immutable source inspection, guarded Paper reads, connected-browser access observations, static-study rendering and artifact integrity/visual review. Those observations are recorded separately.

Use the existing Terminal unit/component/e2e suites and governed source fixtures. Do not create an alternative replay test engine. Extend only the changed owner boundaries and discriminating failures below. Production access and data proof must use an authorized actual session/source; synthetic fixture success is reported separately.

## Full user journeys

| ID | Given / action | Required outcome |
| --- | --- | --- |
| J01 | D06 chart has exact instrument, view, filters, source session, selected observation, scroll and focus; open replay, select, inspect evidence, Return | All qualified origin state restores; selected listing never changes; no plan/save mutation |
| J02 | D08 Options has an exact row/cohort; open futures replay, change local display controls, inspect, Return | Original row/filter/cohort restores after its data loads; replay-local controls do not mutate Options |
| J03 | Source/cohort changed while away | Exact restoration declines honestly; named fallback opens with reason; no false “Restored” |
| J04 | Direct replay URL, new tab, lost history context or external previous page | Safe named Options/chart fallback; no blind Back based only on history length |
| J05 | Malformed, cross-origin or credential-bearing return metadata | Reject unsafe context; preserve same-origin D08 boundary and incumbent cross-Macro owner; no redirect authority expansion |
| J06 | Symbol/pair changes use history replacement | Framework state, original owned origin context and existing company-search field survive through owner codec; no new storage bucket |
| J07 | Sign-in/plan round trip | Existing account owner restores intended validated selection only if its protocol supports it; otherwise explain fallback; no invented callback query |
| J08 | Entry carries validated futures cutoff, exact IEX artifact/native position, or time-only equity request | Resolve each under the initial-selection table; time alone never claims an exact IEX match; latest fallback retains and visibly distinguishes the original request |

## Request, access and ownership

| ID | Falsifying input / action | Required outcome |
| --- | --- | --- |
| Q01 | Futures extra/repeated keys, ES→SPY substitution, interval2, rows2, invalid expiry calendar date, zero/negative/exponential/oversize `at` | Incumbent parser rejects; no broad source query or default substitution |
| Q02 | Valid ES/NQ, interval1/5, rows1/4/8 and accepted lenses/methods | Round-trip serialization retains every selected dimension |
| Q03 | Equity repeated symbol, lowercase, >8 chars, or extra `at/ret/session/cursor` | Page grammar rejects after access gate; default NVDA applies only to absent direct-entry symbol |
| Q04 | Shared Large Trades API valid symbol accepted by its wider grammar | Do not accidentally narrow unrelated consumers by using the page parser |
| A01 | Trusted guest result | Sign-in copy with requested instrument/return; no protected values or upgrade-only message |
| A02 | Verified non-entitled account | Plan-required copy; no promise an archive exists after upgrade |
| A03 | Generic futures `access_required` or entitlement-service uncertainty | Access-unverified copy; no guessed guest/plan reason |
| A04 | Source distribution withheld with a valid plan | Source-specific refusal; no upgrade CTA and no alternate publisher |
| A05 | Account changes while old read is in flight | Old response cannot paint; stale protected data clears immediately |
| A06 | Malformed-body 401/403 on futures | Stop automatic reads and clear data regardless of JSON parsing |
| A07 | 400/429/source restriction | Incumbent stop behavior; no request loop or made-up retry countdown |
| A08 | Equity page/API policy | Actual server behavior matches an explicit incumbent-owner ruling; page gating is not counted as API-gate proof |
| A09 | `/dev/options-plan` in production and nav/search/registry inventory | 404 and excluded; no replay fallback or new customer admission |
| A10 | `/dev/futures` and `/dev/futures-sample` under production | Existing notFound guards remain; development fixture/sample imports never become customer data fallbacks |

## Futures temporal and quantitative cases

| ID | Falsifier | Required outcome |
| --- | --- | --- |
| F01 | Requested cutoff falls between published observations | Select greatest admitted matching cutoff ≤ request and show both times |
| F02 | Request precedes retained window, is future, or has no matching interval/rows | Typed no-frame/unavailable outcome; no newer/nearest unrelated fill |
| F03 | Two equally eligible views or mismatched definition/contract | Fail closed; no arbitrary first-match identity |
| F04 | Bar end/availability exceeds cutoff, overlaps prior bar, or violates definition validity | Parser rejects; evidence never includes it |
| F05 | Latest source exceeds freshUntil; archive is merely old | Clear stale current claim only for latest nonhistorical mode; historical remains labeled historical |
| F06 | Historical successful read / explicit `at`; tab hidden then visible | No scheduled historical polling loop; preserve existing single visibility-triggered guarded read and no overlap |
| F07 | Latest success/transient error/hidden tab | Existing five-second success / fifteen-second transient scheduling, deadline and abort ownership preserved |
| F08 | No captured executions but independently valid depth | Null OHLC/no candle; depth remains; zero captured executions does not assert zero market activity |
| F09 | Depth coverage gap/partial/fractional means | Gap nulls/hatching, partial qualification and fractional precision survive; no integer rounding or fill |
| F10 | Buy+sell+unknown totals or CVD mismatch | Strict validation rejects; known-side and full-CVD semantics remain distinct |
| F11 | Unknown-side volume or incomplete coverage | Unknown remains visible; full-CVD/imbalance not overclaimed |
| F12 | GEX unavailable or cash index closed | Withhold only projection; valid futures activity remains visible |
| F13 | Narrow expiry lens with all-expiry landmarks | Landmark scope remains all-expiry; no implied lens filtering |
| F14 | Ratio versus basis, projected strike near tick boundary | Original strike/mapped precision/unit retained; rounded display tick is separate |
| F15 | Price zoom and footprint visible-count change | Source totals unchanged, visible window disclosed, POC/level tags do not cover final numeric cells |
| F16 | Producer/parser byte, frame, cutoff and cell ceilings | Boundaries enforced without partial silent truncation or larger frontend grants |
| F17 | COT at historical cursor; report retrieved later | Separate report/retrieval clocks and replayEligible:false; excluded from selected evidence |
| F18 | Prior COT date not comparable, missing field or stale report | Null comparison/unavailable state, never zero positioning |

## IEX selection, sequence and artifact cases

| ID | Falsifier | Required outcome |
| --- | --- | --- |
| E01 | Two samples in one displayed millisecond | Original nanosecond/native positions remain distinct; no Number cursor collapse |
| E02 | Same timestamp, different source sequence | Correct sequence-specific state |
| E03 | Equal native tuple at two positions in the same artifact | Exact artifact index + copied-field verification disambiguates, or exact reconstruction declines |
| E04 | Same source digest, changed sampled artifact | Old evidence never rebinds by array index to new bytes |
| E05 | Refresh inserts/removes retained samples | Explicit new-publication transition; selected old evidence identity preserved or unavailable stated |
| E06 | Later execution/break has older event timestamp but higher sequence | Earlier selected state unchanged; later selection applies incumbent correction accounting |
| E07 | Native sequence from another session/channel | Not comparable; reject/join refusal rather than mixed book |
| E08 | Unavailable sample with zero structural totals | Dashes/withheld book; no zero-liquidity claim; executions remain separately qualified |
| E09 | Future sample has extreme price/quantity | Earlier price bounds, color scale, totals and annotations do not reveal it |
| E10 | Near/all price window or retained levels differ | View changes only; all observed-order totals remain qualified and unchanged |
| E11 | More than 64 execution price rows / 1,000 clusters | Existing row-limit disclosure retained; full eligible print totals remain; marker cap does not trim profile input |
| E12 | Broken chain, prefix gap, multiple streams, sample/level retention cap | Preserve exact gap reason and partial/truncated scope; no interpolated books |
| E13 | Missing artifactSha256 or unsupported formatter timezone | Exact artifact/session qualification is withheld where required; explicit fallback, no invented hash/zone |
| E14 | Invalid schema, wrong venue, different dataset, fixture envelope | Existing source/reader admission refuses; no alternate synthetic data |
| E15 | Archive available later than historical market event | Evidence displays separate clocks and HISTORICAL_REPLAY; no original-as-seen assertion |
| E16 | Native known-side totals, duplicates, conflicting IDs and unmatched cancels | Existing accounting result and qualification preserved; resting-order quantities never become executions |
| E17 | Open evidence on A, preview B, commit B, then refresh into different artifact C | Preview leaves all committed surfaces on A; commit updates heading/chart/totals/inspector together to B; C remains pending explicit transition; never mix observations or artifact bytes; access loss clears immediately |
| E18 | Choose sample 7 directly from sample 480 on desktop and mobile; duplicate tuple at another ordinal; cancel once | Full retained array is selectable beyond drawn prefix; exact ordinal/native evidence agrees; duplicate tuple remains distinct; Cancel preserves prior selection |

## Session clocks, responsive behavior and evidence

| ID | Scenario | Required outcome |
| --- | --- | --- |
| T01 | Overnight CME session straddles calendar midnight | Source session date preserved; no browser-date relabel |
| T02 | US DST transition, browser in Asia, holiday/half-day | Existing historical calendar/status owner supplies facts; absolute offset visible; no fixed-hour calendar inferred |
| T03 | User views historical cursor while market now changes | Historical selection remains unchanged; current status is separately labeled |
| U01 | 320/390/600/768/860/861/1024/1200/1255/1256/1280/1440/1600 | No page overflow; inspector mode follows useful width and domain plot minimum; nav never auto-compacts |
| U02 | Dark/light × EN/ZH, long contract/session/hash, dense/empty/partial/error | All essential text readable and unclipped; native glyph/formatting proof; no color-only meaning |
| U03 | Keyboard-only selection | Tabs, slider arrows, Home/End, Previous/Next and non-drag picker complete task; committed selection announced |
| U04 | Touch-only selection and 400% zoom | Important targets ≥44px house rule; controls reflow; chart/table region is independently accessible |
| U05 | Evidence dock→modal→full-width; trigger removed by source change | One overlay owner, correct inert/trap behavior, Escape/close, conditional focus restoration |
| U06 | Pointer hover unavailable or screen reader uses table | Equivalent observation and evidence task possible; no hover-only source access |
| U07 | Reduced motion | Static meaningful state; no automatic playback/numeric tween/gap animation |
| U08 | Contrast and chart series on both materials | Measured final text/control/focus/data contrast; not inferred from token names |
| U09 | Loading/error causes rerender | Reserved geometry and stable origin/selection; no fabricated prices or success |
| U10 | Open actual advanced controls at desktop and 320/390: interval/row/expiry/mapping, GEX/levels, POC/CVD, price zoom, equity near/all and execution rows, weekly positioning | Each retained task is reachable and usable; presentation-only changes preserve native identity, query changes re-resolve explicitly; mobile Apply/Cancel works; COT clocks stay separate |
| U11 | Read each depth/footprint/execution chart and table without hover | Visible key explains true quantity/side ordering, units, normalization, selection and gaps; futures mean depth is not bid/ask or execution-side color; exact readout/table agrees with the selected source |
| S01 | No admitted D23 save contract | No active fake Save/Saved behavior; inspection/navigation does not mutate plans |
| S02 | Future save success | Owner record ID/revision + receipt + readback bind the exact artifact/selection |
| S03 | Future save timeout/ambiguous effect | Reconcile original operation through D23; no duplicate retry/new writer |
| S04 | Exact saved artifact no longer retrievable | Explain unavailable reconstruction; never resolve against newest same-symbol artifact |

## Required proof receipts at later acceptance

Bind each executed suite and real-path run to exact source/deployment identity, fixture/source status, account/access role, selected instrument/session, returned artifact identity, viewport/theme/locale and screenshots or trace as appropriate. Redact private account details without hiding the asserted access state. Native Paper captures bind exact file/page/artboard IDs and immutable exports. Capture failure states as well as successful journeys.

A code unit test, image render, API body, CI check, merge and deployment each establish different facts. No “PASS” roll-up is allowed while a required path remains unproven. The principal acceptance question is whether the researcher can complete the commissioned journey with the exact identity, clocks, evidence and return state intact.
