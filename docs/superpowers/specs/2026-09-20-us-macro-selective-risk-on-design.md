# US Macro Selective Risk-On Design

## Outcome

Keep the existing US Market State score and verdict as the macro backdrop, but stop a green RISK_ON verdict from implying a broad rally when the existing breadth component says participation is weak. Users must be told whether risk-on participation is broad, uneven, narrow/selective, or unverified.

This first release is an interpretation and trust repair. It does not change Market State weights, thresholds, Risk Radar authority, Prophet, Sector Confluence, or sector/theme rankings.

## Source of truth

The sole participation input in R1 is the existing breadth component already produced by engine.market_state.market_state_snapshot(). No new collector or parallel breadth score is introduced.

The participation state is display-only:
- broad: breadth component score >= 60
- uneven: breadth component score 42..59
- narrow: breadth component score < 42
- unverified: breadth component absent or malformed

These cuts deliberately reuse the Market State band boundaries. They are copy taxonomy, not trading thresholds.
## Display behavior

Underlying verdict, score, raw_score, color, caps, flip logic and persisted history remain unchanged.

For RISK_ON only:
- broad -> Broad risk-on
- uneven -> Risk-on · uneven participation
- narrow -> Selective risk-on
- unverified -> Risk-on · participation unverified

The headline, subline and What-To-Do copy must carry the same distinction. Narrow participation must explicitly state that green is not a broad buy signal.

MIXED and RISK_OFF keep their existing stance language. Their participation context may remain available in the payload but must not upgrade or soften their verdict.

## Static/live parity

engine/market_state.py owns one pure display-copy helper. The settled snapshot calls it. scripts/build_risk_state.py calls the same helper for the debounced live display verdict. templates/dashboard.html.j2 and templates/risk_state_live.js consume projected copy with existing verdict maps retained only as backward-compatible fallback.

Live score and settled breadth have different clocks. R1 must not pretend breadth is intraday: the existing legs_asof.breadth remains the clock disclosure.
## Failure behavior

Missing or malformed breadth fails to unverified, never broad. A live band held by debounce must render copy for the displayed verdict, not the proposed verdict. A stale or behind live feed keeps the settled page untouched under the existing session-floor law. No participation state may override MIXED/RISK_OFF, score caps, or Risk Radar.

## UI treatment

This release changes words, not layout or material styling. Dark/light and EN/ZH share the existing component treatment. No new token family, runtime stylesheet, card, modal, or control is introduced.

## Acceptance

1. A 61/RISK_ON snapshot with breadth score 0 remains score 61 and verdict RISK_ON, but renders Selective risk-on.
2. RISK_ON with breadth >=60 renders Broad risk-on.
3. Missing breadth renders participation unverified.
4. MIXED/RISK_OFF preserve their existing labels and actions.
5. Static template and intraday patcher consume the same engine-owned copy.
6. Existing live session-floor behavior remains green.
7. Template/site plain-copy JS stay byte-identical.
8. Targeted Market State/live/coherence tests pass and rendered site/macro.html contains the selective copy on the current 2026-09-18 snapshot.
