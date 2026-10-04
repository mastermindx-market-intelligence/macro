# Risk Radar Probability Evidence Depth — 2026-09-22

## Outcome

Risk Radar keeps the existing displayed pullback probabilities unchanged and now carries a display-only evidence-depth contract derived from the accepted post-parity probability audit.

The user-facing US Risk Radar adds one compact metadata item inside its existing **Market internals** block:

- well-populated current cell: `Odds evidence · 21d history · n=746 · observed 12%`
- thin cell: `Odds evidence · 21d thin history · n=34`

No new panel, score, alert, or polling path is added. The existing expandable evidence area remains the place for deeper provenance.

## Why

The accepted audit in `research/grey_deer/evidence/displayed-probability-audit-20260922/result.json` found that the complete displayed probability surface has positive Brier skill and a useful risk gradient, but exact cells are not precision-grade actuarial probabilities. Some cells are evidence-thin and the low-state 13% floor materially overstates reconstructed modern realized frequency.

The product should therefore expose how much historical support sits behind the current number instead of pretending every percentage has equal evidentiary depth.

## Contract

Producer: `scripts/build_risk_radar_probability_evidence.py`

Projection: `data/risk_radar/probability_evidence.json`

Runtime: `engine/risk_radar.py` may attach `drawdown_prob.calibration_evidence` only when explicitly requested by the live `compute()` path. Historical trajectory/replay calls keep evidence lookup disabled.

View-models:
- `engine/market_state._radar_to_rd()` -> `rd.dd_evidence`
- `scripts/build_macro_context._build_risk_radar()` -> `dd_evidence`

Visible consumer: `templates/_risk_envelope_band.html.j2`, already embedded inside the US `#dlg-risk` Market internals block. The collision-held `templates/dashboard.html.j2` is deliberately untouched.

## Evidence boundary

This metadata is reconstructed historical evidence. It does not:
- change H5/H10/H21 probabilities;
- change state, score, band, conjunction, gate or authority;
- change sizing, policy, ranking or capital treatment;
- convert reconstructed history into issued/prospective validation.

The accepted audit source hash is `eb9d4bfd75a18199789a8306ea948aba17e84693ad24e081134feba0751c09ea`.

On the current committed-input US snapshot (as of 2026-09-18), the Radar remains `caution` with 3% / 8% / 16% displayed odds. The evidence attachment maps the 16% H21 cell to n=746, 91 qualifying outcomes, 12.2% observed frequency, 90% moving-block interval 7.4%–17.5%, non-thin. A paired call with evidence disabled produces identical probability/model fields.

## UI proof

The browser proof is captured from the real US Risk Radar dialog path after the
engine → Market State → dashboard render projection. Its evidence receipt is kept
on the existing governed UI-evidence plane; the source receipt under
`research/grey_deer/evidence/probability-evidence-depth-20260922/` remains
model/source provenance only, not a second UI evidence plane.
