# TOI W2-0 Data/Clock Architecture Freeze

**Operation:** `TOI-W2-0-DATA-CLOCK-V1`  
**Result:** `HOLD`  
**Combined capability:** `PARTIAL`

## Frozen contracts

- `4H-CLOCK`: RTH only; 09:30 ET anchor; first bucket 09:30–13:30; final bucket 13:30–actual exchange close; on a 13:00 early close there is exactly one 09:30–13:00 bucket. A source row whose bar start is at or after the actual close is excluded.
- `195M-RTH`: 09:30–12:45 and 12:45–actual close, independent method/trial identity.
- Monthly: completed-month context only, after the accepted daily source is final.
- Missing intervals remain missing. No forward fill.
- Raw and adjusted series are separate basis classes. No cross-basis splice.
- Historical corrections never backdate their availability.
- Identity comes from Data OS; ticker is a projection.
- Tactical 5m ownership remains Live Entry Radar.

## Blocking mismatch

Terminal's current static US regular-session filter uses 09:30≤t<16:00 and does not apply the date's actual early close. The 2025-11-28 production path therefore admitted a 13:00-stamped 5m row into the 4H bar, while Macro's canonical session owner closes the session at 13:00 and admits only bars knowable by then. Five of five measured early-close symbols diverged.

The current whole-universe fallback is also not a parity substitute: when stored 5m history is absent, Terminal falls back to provider-built 1h history. A 20-name production sample exposed six hourly rows beginning at 10:00 ET. That is sufficient evidence to keep broad 4H admission held until exact 09:30-open coverage is proven.

## Smallest lawful W2 architecture

Do not create another minute plane. Reuse:

- `engine.session_digest.session_window_et` + `engine.entry_radar.four_hour` as the Macro clock/grid owner;
- the existing Massive/Polygon source owner for source-qualified bars;
- Terminal's existing intraday-history owner for rendering, repaired or explicitly versioned to the same actual-session-close contract;
- Data OS identity/PIT owners for subjects and historical denominator.

W2 must return real source receipts on a same-basis Daily+4H corpus and at least 20 parity cases after the early-close repair before W3 can be reconsidered.
