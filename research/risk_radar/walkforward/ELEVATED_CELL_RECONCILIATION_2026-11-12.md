# Elevated-cell reconciliation (ruling 2026-11-12, item 4)

**Result: the September figures reproduce exactly, but only when the `global_breadth` leg is
switched off. They describe an engine configuration that is not the one running today.**

| Configuration (2020-01-01 → 2026-09-18, H21 ≥5% day labels) | elevated | risk-off | caution | watch |
|---|---|---|---|---|
| September study (`RISK_RADAR_STATE_LADDER_CALIBRATION_RESULTS_2026-09-21.md`, y2020 rows) | 30.3% (n=33) | 43.8% (n=224) | 16.5% (n=1,072) | 4.6% (n=196) |
| Today's code, `global_breadth` leg removed | **30.3% (n=33)** | **43.8% (n=224)** | 16.4% (n=1,082) | 4.5% (n=199) |
| Today's code, all legs (the live configuration) | **3.2% (n=31)** | **44.8% (n=239)** | 16.6% (n=1,039) | 6.1% (n=229) |

Small differences in the caution and watch counts come from data revisions since September.

## Cause

`global_breadth` is a Tier-B leg built from `data/intl_etf/`. The engine zeroes the leg when
that store is stale (more than 8 days old) or thin (fewer than 10 ETFs), at
`engine/risk_radar.py:89-90`. When the leg is present, its Tier-B escalation moves about 15 days
up from elevated to risk-off (risk-off goes from 224 to 239 days). The elevated days that remain
are mostly ones that were not followed by a loss.

The September run evidently had the leg absent. The study script records
`missing_optional_inputs`, which is consistent with this, but its JSON output is not in the
repository, so the cause is inferred from the exact reproduction, not read from a receipt.

## Consequences (applied in the plan)

- **"Elevated 30.3%" is withdrawn** for the current engine. Under the live configuration the
  elevated state is followed by a ≥5% loss within 21 sessions on 3.2% of its days (n=31), below
  the 17.5% base.
- **"Risk-off 43.8% (n=224)" is superseded** by 44.8% (n=239, 28 runs) for the live configuration.
- **Any Radar hit rate quoted from now on names its leg configuration.** It comes from
  `engine/risk_radar_eval/scorecard.py` and names its episode count.
- **The state ladder is not monotone in the live configuration** (elevated sits below caution).
  This is another reason the public read must not present the loud state as a forecast.
- **New finding for slice 1:** a Tier-B leg that is supposed to "escalate only" changes the
  distribution of the Tier-A states it escalates from. The leg set is the same in every fold.
  Leg availability, meaning store freshness, has to be recorded per date in the walk-forward
  series.
