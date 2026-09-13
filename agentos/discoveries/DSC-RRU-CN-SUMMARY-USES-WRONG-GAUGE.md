---
key: RRU-CN-SUMMARY-USES-WRONG-GAUGE
claim: >
  At Macro eb9e91961ddc4f3043d0dad358602525e66eccda, the China summary row
  labelled Deep-drawdown gauge reads the recession/slowdown score with 60/40
  thresholds instead of the actual drawdown gauge and its engine band.
falsifier: >
  Run python3 research/grey_deer/RRU_CN_GAUGE_PROBE_2026_09_08.py;
  inspect its immutable template fragment and scripts/build_china.py _DD_READ.
  Different source-field attribution or agreement in the four declared cases
  would refute the documented mechanism on that pin.
so_what: >
  Repair the summary to consume the existing radar_dlg gauge view-model, not
  another threshold table. The mismatch can overstate risk or falsely show calm.
  Keep unavailable distinct from calm; verify both languages and real publication.
kind: landmine
verified_at: 2026-09-08
verified_by: >
  python3 research/grey_deer/RRU_CN_GAUGE_PROBE_2026_09_08.py;
  research/grey_deer/RRU_CN_GAUGE_RESULTS_2026_09_08.json;
  templates/china.html.j2:2158-2163 and scripts/build_china.py:1126-1168 at eb9e919.
scope: ["WS:GREY-DEER-RISK-INTELLIGENCE", "templates/china.html.j2", "scripts/build_china.py"]
confidence: verified
---
# Boundary
Four controlled renders reproduced the screenshot-shaped discrepancy and the
inverse false-calm case. This is source/fragment proof, not a fresh production
browser witness or a measurement of historical user harm. No product was changed.
