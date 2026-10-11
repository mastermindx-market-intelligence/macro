# China Risk P0 Semantics — Evidence Packet

Operation: `cn-risk-p0-semantics-20260923-solpro-001`

## Scope

Presentation-only repair. No risk score, probability surface, band threshold, authority gate, gross factor, forward log, ranking, selection, or portfolio/Prophet logic is changed.

The China surface must separate:

1. **Measured state** — current tape/liquidity/breadth composite.
2. **Transition hazard** — external-driver hazard configuration and percentile rank.
3. **Forward odds** — historical/model estimate with the normal historical reference.
4. **Evidence / authority** — live evidence maturity and whether the radar may bind capital policy.

## Frozen copy contract

- Market State `39 · RISK-OFF` discloses that it is near the Mixed boundary and names the actual weak legs.
- Risk Radar `98` is rendered as `98th percentile`, never as a probability or bare `/100` score.
- The 21-session pullback estimate is explicitly historical/model-based and paired with the normal rate and odds multiple.
- Live evidence shows matured rows, loud alerts, hits, and rows awaiting maturity.
- `binding=false` is visibly advisory and does not override measured tape.
- `gross=0.62` is an exact advisory risk-budget reference, never “half of normal” or an authoritative suggested size.
- Sizing context never selects stocks.
- English and Chinese carry equivalent meaning.

## Verification

Focused regressions:

```text
python3 -m pytest -q \
  tests/test_risk_radar_dlg_partial.py \
  tests/test_risk_radar_dlg_country_wiring.py \
  tests/test_china_archetype_d_s1.py \
  tests/test_build_china_risk_state.py \
  tests/test_risk_state_live_session_floor.py
```

Browser proof uses the real locally generated `site/china.html`, served without response interception:

```text
python3 research/evidence/cn-risk-p0-semantics-20260923/verify_browser.py \
  --site-dir site \
  --output-dir research/evidence/cn-risk-p0-semantics-20260923/browser
```

The verifier covers desktop/mobile × EN/ZH × dark/light, dialogs and popovers, accessibility names, keyboard entry, banned copy, exact machine values, and horizontal overflow. `browser/browser-results.json` and the screenshots are generated from that run.
