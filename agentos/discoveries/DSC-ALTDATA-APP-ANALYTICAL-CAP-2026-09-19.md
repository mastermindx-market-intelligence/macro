---
key: ALTDATA-APP-ANALYTICAL-CAP-2026-09-19
claim: On the pinned app dataset, an availability-screened reconstruction at the 2026-09-18 feed cutoff yields 732 legacy-eligible ticker keys and 312 strong-rule keys, but the normal top-15 limit retains only 15 strong keys and excludes 297 from that app-summary route.
falsifier: Re-run research/intelligence_network/demand_audit.py against Macro a1334a1a6c154b9b49664ee892d9710742fc6018 with observed-by 2026-09-18T18:41:09.971423Z and the unchanged baseline function; different eligible, strong, displayed or excluded counts on the recorded data/function hashes falsify this fixed-snapshot claim.
so_what: Separate analytical/context coverage from presentation caps through the incumbent source and product owners. Preserve availability clocks and test that broader context cannot silently add convergence votes, ranking authority or unvalidated candidates. Do not call the excluded names missed trades.
kind: data
verified_at: 2026-09-19
verified_by: python3 research/intelligence_network/demand_audit.py --git-repo . --source-ref a1334a1a6c154b9b49664ee892d9710742fc6018 --observed-by 2026-09-18T18:41:09.971423Z; immutable input blob 507c9fb0f356ac4117dbe47d117c2e1c98b6f4d0; aggregate receipt research/intelligence_network/demand_audit_feed_cutoff_2026-09-18.json.
scope:
  - engine/altdata.py
  - engine/altdata_models.py
  - research/intelligence_network/
confidence: verified
---

The raw parquet has 178,845 rows. Exactly 1,810 were first observed after the feed cutoff and are excluded, leaving 177,035 available observations and Sep 17 as the latest source snapshot. A second explicit cutoff after the newest collection yields 731 eligible ticker keys but the same 312/15/297 strong-rule split.

Neither reconstruction attests the deployed browser or a specific historical production invocation. No investment performance was estimated. Provider ticker labels are not a substitute for canonical issuer identity. Fewer observations in a display are not necessarily absent everywhere else in Mastermind; this finding is scoped to the app-summary/convergence route.

The diagnostic also distinguishes changed app cohorts, missing current/prior groups and counter decreases. A negative cumulative-counter delta is not automatically a decline in business demand. The collector's keep-first behavior preserves original observations but cannot establish absence of later source corrections.
