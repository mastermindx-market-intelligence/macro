---
key: RELEASE-RADAR-A1-LEGACY-FIELDS-ARE-NOT-THEIR-LABELS
claim: >
  In the Release Radar payload (data/release_forecast/latest.json) the legacy
  per-item fields do not mean what the old card labels said: `confidence` is
  interval-width rank x input completeness and `confidence_v2` is an
  attribution-provenance score (neither is a probability or a calibrated
  coverage), `cutoff_label: "T-1"` is only the nearest-upcoming queue position
  per release type (not a data cutoff or a timestamp), and `components` explain
  the champion model's own point, not the combined_v1 blend the card shows
  when the basis is benchmark-augmented; PPI components are null (never
  zero). The A1 `diagnostics` subtree (schema release_forecast.item_diagnostics.v1)
  is the only field that carries those distinctions.
falsifier: >
  A read of engine/release_forecast.py (the `confidence = round(interval_rank *
  input_completeness, 4)` lines), engine/release_components_cpi.py
  (`confidence_v2 = round(float(c_raw) * input_completeness, 4)`), or
  scripts/build_release_forecast.py `_assign_cutoff_labels` showing a calibrated
  probability, a data-timestamp cutoff, or blend-level components; or
  `python3 -m pytest tests/test_release_diagnostics.py -q` failing its drift pins
  (block roles vs `_BLOCK_CONFIDENCE_WEIGHT`, coherent targets vs
  `_SHADOW_COHERENT_RIDGE_TARGETS`, the T-1 contract line, the renderer's
  selection helpers).
so_what: >
  Any session touching Release Radar labels (A2 intervals, PCE, the renderer)
  reads `item.diagnostics` for band status, calibration, attribution scope and
  inputs-as-of instead of re-deriving them from confidence / cutoff_label /
  components. Never print "Confidence N%", never show T-1 as a cutoff time,
  never present a CPI decomposition as explaining the blend, and never render a
  null PPI attribution as 0. Band labels stay nominal (p10-p90 = 80%,
  p25-p75 = 50%) and "calibration not established" until a scored exact lane
  says otherwise.
kind: data
verified_at: 2026-09-10
verified_by: >
  engine/release_forecast.py:964 and :1174; engine/release_components_cpi.py:454;
  scripts/build_release_forecast.py:1881 (_assign_cutoff_labels); nightly
  latest.json asof 2026-09-10T10:05:21Z through engine/release_diagnostics.py
  (CPI 2026-08 T-1 item: attribution.applies_to_primary=false,
  primary.basis=combined_v1_benchmark_augmented; PPI attribution
  status=unavailable/not_recorded); tests/test_release_diagnostics.py 55 passed.
scope:
  - macro
  - data/release_forecast/latest.json
  - engine/release_diagnostics.py
  - scripts/build_release_forecast.py
  - templates/dashboard.html.j2
  - WS:RATES-INFLATION-COMMAND
confidence: verified
---

Recorded by the Release Radar A1 receiver (macro#6868). The adapter is
additive and display-only: the producer attaches it once, after every ledger,
scoring and scoreboard consumer, so no numerical path can read it back.
