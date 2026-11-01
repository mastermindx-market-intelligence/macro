# Prophet WP03 — point-in-time entry-zone versus ledger-trigger contract

**Status:** source-backed discrepancy census and frozen prospective verification plan. **NOT a merged behavior change or trading instruction.**
**Program:** SignalsEngine Masterplan §9.2 / §14 WP03, Mastermind PR #1803 head `35e0a38c0a4fa2833435725c12b26b4271b55ab4`.
**Macro source base:** `main@1e0a6406f21a8197e13d572b9a2306661401b0a7` (2026-10-23); the observed source blobs were `engine/prophet_bridge.py@cb04c6157a080f36063280dc70c35267e1cccd1f` and `scripts/build_prophet.py@7e0b36da6522af1e652857960077166db3969474`.

## 1. Native owners and non-goals

- `prophet.trade_plan/v1` is the immutable originated **conditional** plan. It carries `entry`, `trigger`, `entry_zone`, `price_basis_date`, horizon and directional targets. Plan origination uses the **price-basis session close** as the entry-price and evaluation clock; not a hypothetical fill price.
- `engine.prophet_bridge.evaluate_entry_zone` derives a *display-level zone-state observation* from OHLC inputs (zone high, low, expiry and conversion rule). It MUST NOT automatically become evidence of an executed position or a scored forward-ledger trigger.
- `scripts.build_prophet._determine_outcome` owns the live forward **close-based scalar-trigger** episode and eventual first-close outcome; `engine.prophet_arena.replay_closure` owns its bounded replay analog. These intentionally scan daily closes **strictly after** the price-basis clock, then wait for the plan's scalar `trigger` (BULL close >= trigger; BEAR close <= trigger). The live first terminal event closes the episode; `NO_ENTRY` carries null performance and is excluded from scored wins.
- Preserve the ledger writer, existing grades and historic plan geometry; no backfilled P&L, calibration claim, signal origination, authority promotion or new lifecycle/ledger plane. Alternate executable-fill evaluation requires a separately versioned method and independent validation.

**Other live source owners:** Macro PR #10109 is the existing draft owner of `engine/prophet_bridge.py` for WP04 confidence handoff. Macro PR #10107 owns `scripts/build_prophet.py` (WP02) and remains release-review gated. Macro PR #6996 owns separate `engine/entry_signal.py` instructional copy. Do not silently modify these paths or merge speculative zone behavior into their work.

## 2. Observed code distinctions (not inferred backend behavior)

| Exact path / lines on pinned Macro base | Observed behavior | Source implication |
|---|---|---|
| `engine/prophet_bridge.py:2516-2538` | `frame.index >= price_basis_date`, then `hits = series[series <= zone.high]`; uses `low`, else `close`. | The *price-basis day* itself, including intraday lows before its close-based plan existed, can qualify as a zone touch. A candle entirely below the zone also qualifies solely because its low is below the upper boundary. |
| `engine/prophet_bridge.py:2543-2572` | Any found hit immediately returns `state=filled` **before** expiry is considered. | A touch after the declared zone expiry can be called filled; whether late touches should count requires the named policy owner to decide. |
| `scripts/build_prophet.py:1313-1375,1397-1460` | Evaluation starts at `index > plan_clock_date`, reads closes and a scalar trigger; `NO_ENTRY` means no confirmed activation before horizon. | A displayed zone touch, scalar activation, position fill and outcome are DIFFERENT measurement objects. They must not be collapsed into one “trade filled” claim. |
| `engine/prophet_arena.py:459-597` | Replay of close-based method also starts strictly after price-basis close. | Preserve live/Arena parity for the **existing** grader; new zone logic must not secretly rewrite either ruler. |

## 3. Frozen discriminating fixtures / expected semantic ruling

All listed dates are NYSE trading sessions for the explicit fixture; July 3, 2026 is observed as the Independence Day market holiday. Zone is `[93.00, 95.00]`; origin price-basis is `2026-07-02`, whose close is `100.00`. Unless otherwise stated, plan direction is BULL, zone class pullback, no conversion, expiry `2026-07-10`, scalar trigger `110.00`. In these fixtures, **zone state is descriptive**; a scalar-trigger episode is graded only by the existing ledger.

| Case | PIT OHLC continuation | Source behavior as currently expressed | Proposed acceptance, subject to owner confirmation |
|---|---|---|---|
| **Z1 pre-publication low** | Jul 02 (basis): low 94, high 104, close 100; Jul 06: low 103, high 108, close 105 | Zone `filled_date=Jul 02`, because the basis day is included | Do **not** record an actionable post-issuance fill from a low occurring before the issuance close. Consider a separate `at_zone_at_issuance` context if relevant. |
| **Z2 gap completely below band** | Basis low 99, close 100; Jul 06: open 87, high 90, low 80, close 86 | Zone `filled_date=Jul 06`, because 80 <= 95 | A candle wholly below the band did **not trade into** the band (its high is below 93). Do not call it a verified touch or executable fill. |
| **Z3 post-expiry touch** | Basis low 99; no touch through expiry Jul 07; Jul 08 low 94, high 101, close 99 | Latest zone is `filled` even though all qualifying lows occurred after expiry | Require a documented decision: after-expiry touches must not retroactively prove an in-window entry if expiry is an eligibility cutoff; preserve historical expiry/conversion record. |
| **Z4 in-window intersection, positive control** | Basis low 99; Jul 06 low 94, high 105, close 103; Jul 07 close 104 | Zone `filled` (after issuance and the OHLC range intersects) | Zone touch can be affirmed, **but** ledger is still untriggered while no close >= 110; do not convert descriptive touch into graded P&L. |
| **Z5 touch on expiry day** | Jul 07 low 94, high 106, close 102, expiry Jul 07 | Source prioritizes found fill | Clarify that `<= expiry` touch counts only if the zone's eligibility policy includes its expiry session; test this boundary explicitly. |
| **Z6 missing high, close-only history** | Session has `close` only, or `low` without `high` | Source falls back to close only when low is absent, with `fill_basis` disclosed | Do not fabricate an intraday band intersection when OHLC cannot prove it. Preserve a named approximation/unknown state for deficient tapes. |
| **Z7 old plan without `entry_zone`** | Legacy plan | `state=none`, reason says no zone | Keep the legacy named-null behavior; no forced migration. |
| **Z8 Arena/live parity** | Identical close series, identical scalar trigger and horizons | Distinct implementations, tested elsewhere | `_determine_outcome` and `replay_closure` retain existing method/version parity; a zone-display change cannot alter their grades. |

The expected acceptance for Z1/Z2/Z3 is a **prospective policy decision**, not an authorized backward regrade. An actual broker fill requires quotes/orders not present in this OHLC display engine.

## 4. Implementation sequencing and pre-registered tests

1. Owner of WP04 / `prophet_bridge.py` finishes PR #10109 or explicitly releases the shared source path. Then create a **single** source-writer repair for `evaluate_entry_zone`; do not use this records-only PR to touch its branch.
2. **Reproduce** Z1–Z3 on the current immutable source in the existing `tests/test_prophet_anticipation_intake.py::TestZoneExpiryToStarter`, with OHLC records whose full dates and zone boundaries are explicit. Verify that old source fails new expected assertions; do not mark expected failures as success.
3. Adjudicate the date eligibility and incomplete-OHLC policy before code. Candidate logic may filter session observations strictly after close-based issuance, require `low <= zone.high` AND `high >= zone.low` when both observed, and bound touch by expiry. If missing high/low, disclose observability limits; do not silently map unknown to true or neutral.
4. Add positive/control cases Z4–Z8; preserve unmodified plans, prices and ledger outcomes, and verify both EN/ZH render copy for `live/filled/expired/converted` remains truthful. If a term currently says “filled”, qualify it as **observed band visit** unless actual fill evidence exists.
5. Run the existing owning suite, Prophet close/clock parity suite, hosted CI, independent code/domain review, and the ordinary protected integration gate. No historical ledger rewrite or production claim without separate consumer proof.

## 5. Evidence classification and release decision

**Proven by pinned source inspection:** the zone computation includes the price-basis session, tests `low <= high` without validating the lower band boundary, and checks expiry after searching all observed bars. The live ledger excludes the basis close and uses a separate trigger.

**Not yet proven:** actual affected production plan count, reliable intraday fill/execution semantics, expected treatment of gaps over zone, acceptable zone-expiry cutoff, full consumer-language behavior, or trading utility. A browser screenshot or green fixture alone will not prove those.

**Decision:** WP03 is **research/contract candidate**, not implementation acceptance. This PR records a testable next repair with original source ownership and avoids contradictory activation, duplicate grader or lookahead claims. Carry the WP03 code fix only after the shared bridge ownership boundary is free and the owner resolves the semantic choices.
