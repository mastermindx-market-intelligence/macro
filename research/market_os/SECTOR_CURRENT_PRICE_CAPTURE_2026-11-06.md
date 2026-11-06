# Current Sector price-pair capture

Status: source-qualified price dependency only. Governing issue: [Macro #10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779). Base: `cec642221e01dfc5a496d99f866e9b6fe313cfbb`.

`lib.sector_input_capture.read_sector_price_captures` uses the existing verified Yahoo and breadth readers exactly once each at one explicit aware evaluation instant. Both readers now expose the existing validator's `require_current` option; their default remains false for historical recovery. The Sector price-pair adapter always requests current qualification and passes the captured Yahoo generation into breadth validation. A later current Yahoo selection with an incompatible breadth dependency refuses; the adapter does not reread a pointer, fall back to a historical pair, collect data or write state.

The returned `SectorPriceCaptures` contains the verified source objects and captured instant. `input_lineage()` uses their existing receipt methods over those bytes, including exact content IDs and member hashes. It performs no lookup. Source frames remain values for the downstream trusted adapter; no new manifest or publication authority is introduced.

Controlled acquisitions and the real private publisher prove the current pair, exactly one read per domain, no ambient config/store fallback, usable basket inputs and detached lineage dictionaries. A mismatched new Yahoo selection is refused. At the next completed session the old pair is refused before the breadth pointer is read, while the explicit retained-recovery path continues to work. Both behaviors preserve source files, mtimes and pointers.

The affected Yahoo/breadth run returned 145 passing tests and one new assertion failure because the test expected an inaccurate error-code regex. The source correctly refused with `source_not_current_target`. The assertion was corrected to the exact existing exception type and code; all three new price-pair tests then passed (54 unrelated cases deselected). No production logic was weakened, and no provider request occurred. Exact logs and source hashes are in [the combined source proof](SECTOR_DOCUMENT_COMPOSITION_SOURCE_REVIEW_2026-11-06.json).

## Required closure before a current native canary

This pair is not the full Sector capture adapter. Required source bindings remain:

- Genuine adjusted five-field member OHLCV with exact breadth/membership dependency; the existing private breadth bundle cannot invent open prices for close-only extras.
- Sponsor holdings and corresponding stock inputs; original controller 52778 remains fenced pending effect reconciliation.
- One captured basket calibration document supplying signal, rollover, breadth-divergence and sizing values; captured cycle settings, entry bands, hazard, volatility and Central calibration inputs.
- Existing-owner projection of captured regime, bonds, forex, market state, heatmap and crowding. Unbound is not equivalent to captured absent.
- Actual prior Central, phase history, ThemeContext/Pulse archives, bottoming ledger, grader calls and frozen history with original vintages and no writer effects.
- Explicit Nasdaq/Russell membership if that scope is claimed. Do not substitute thematic membership or invent constituent dates.

Construct the canonical US reference through `session_anchor.capture_reference_sessions("US", asof=cycle_day)`, retaining its established epoch. Do not use the finite SPY input history as a replacement runtime calendar. Build thematic prepared features/enrichment from the verified resolved thematic panel; preserve narrative's distinct primary-plus-extras projection. The same captured membership revision must bind both.

The complete captured-input canary must use an admitted immutable source/configuration closure and the sole publisher in a separate private target, or await the mutable-source updater barrier. Import-time `app.main` defaults and policy paths must not fall back into `/opt/macro`; no second full API lifespan or tape hub may start. Actual publication remains governed by the existing factory's current-time admission.
