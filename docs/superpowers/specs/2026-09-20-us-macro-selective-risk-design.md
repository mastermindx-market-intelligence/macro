# US Macro Selective Risk-On Design

**Status:** Chairman-approved continuation of the 2026-09-20 US Macro diagnosis.

## User outcome

The US Macro hero must distinguish a supportive composite backdrop from broad participation.
A green score must not tell users that breadth agrees when breadth is weak, stale, or unavailable.
The score, caps, historical ledger, Risk Radar authority, and Prophet authority remain unchanged.

## Release A contract

Add a presentation object under the existing Market State owner. It is descriptive only.
For US RISK_ON: breadth <42 => Selective risk-on / weak participation; 42-59 => Selective risk-on / uneven participation; >=60 => Risk-on / breadth supportive.
Missing, duplicate, degraded, non-finite, stale, or wrong-session breadth => participation unverified.
MIXED and RISK_OFF preserve their existing weaker stance regardless of breadth.

The presentation carries stance, headline, subline, action, breadth state, breadth score, and settled breadth as-of.
The underlying machine verdict and numeric score are never rewritten by presentation logic.
A valid numeric zero is weak breadth, never missing.

## Static/live contract

Static first paint consumes the presentation fields.
The intraday builder transports the same presentation after its existing band debounce.
The live browser patcher consumes transported copy and does not re-implement breadth thresholds.
A legacy live payload without presentation uses safe generic copy, never the old claim that breadth and the tape “line up.”
Live score time and settled breadth time remain separate; the breadth observation is not redated intraday.

## Scope and incumbents

Reuse current Market State, risk_state live transport, and dashboard consumers.
Do not build another score, state machine, history ledger, or participation collector.
Macro PR #7060 owns historical sector-participation acquisition and drill-down.
Macro PR #7384 owns fresh Confluence entry-vs-entry-condition semantics.
Macro PR #6685 owns Grey Deer homepage compaction; this slice must remain composable with it.
Macro PR #7040 also edits market_state.py; avoid its radar/_num hunks.

## Files

- engine/market_state.py — presentation projection and static output.
- scripts/build_risk_state.py — debounced live presentation transport.
- templates/dashboard.html.j2 — first-paint stance/subline/action consumption.
- templates/risk_state_live.js + site mirror — live consumption and safe legacy fallback.
- existing owning tests only.

## Acceptance

Score 61 + qualified breadth 0 remains score 61 and renders Selective risk-on with weak-participation language.
Breadth 60+ may say breadth is supportive but never “buy anything.”
Missing/stale breadth says unverified.
RISK_OFF/MIXED are never upgraded.
Legacy live payload is safe.
Same-session/ahead/behind live-floor behavior remains unchanged.
EN/ZH and template/site mirror stay in sync.
