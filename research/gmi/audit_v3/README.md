# GMI audit v3 — evidence and reproduction index

This is the evidence appendix for the [standard-Pro audit](../GMI_THEME_SUBTHEME_NORMAL_PRO_AUDIT_2026-10-03.md) and [Master Plan v3](../../../docs/superpowers/plans/2026-10-03-gmi-theme-subtheme-end-to-end-completion.md). No new Deep Research run was used.

## Contents

| File | What it establishes |
|---|---|
| [GRAPH_AND_TEMPORAL_AUDIT.md](GRAPH_AND_TEMPORAL_AUDIT.md) | Exact graph/PIT/rights/state findings, positive reader behaviors and remaining acceptance limits |
| [CONSUMER_AND_ECONOMIC_AUDIT.md](CONSUMER_AND_ECONOMIC_AUDIT.md) | Existing CTE/Terminal delivery, closed-schema migration, STSI/economics/leadership/Prophet seams |
| [GRAPH_SOURCE_MANIFEST.json](GRAPH_SOURCE_MANIFEST.json) | 48 files at the Macro census pin; paths, Git blob identities, SHA-256 and byte verification |
| [CONSUMER_SOURCE_MANIFEST.json](CONSUMER_SOURCE_MANIFEST.json) | 36 files with exact repository/ref/path and hashes; four explicitly absent planned STSI paths |
| [CARRIER_CENSUS.json](CARRIER_CENSUS.json) | 27 initial PR records and publication-boundary metadata recheck; no head/state/merge change observed |
| [SOURCE_RECHECK.json](SOURCE_RECHECK.json) | Macro root-tree comparison, changed site subtree, same-pin protected procedure reload and unchanged Terminal |
| [GRAPH_BOUNDARY_REPRODUCTIONS.json](GRAPH_BOUNDARY_REPRODUCTIONS.json) | Ten isolated checks, including two positive D2D/strict-reader checks |
| [PROPHET_BOUNDARY_REPRODUCTION.json](PROPHET_BOUNDARY_REPRODUCTION.json) | Six rights-string cases and one null case from #8240's existing synthetic fixture |
| [W2_RANK_INVARIANCE_CHECK.json](W2_RANK_INVARIANCE_CHECK.json) | Exact common-shrinkage function preserves ranks and Spearman while reducing dispersion |
| [REVIEW_AND_VERIFICATION.json](REVIEW_AND_VERIFICATION.json) | Review dispositions, accepted corrections and local evidence/document verification |
| [ARTIFACT_MANIFEST.json](ARTIFACT_MANIFEST.json) | Final published artifact paths, bytes and SHA-256, excluding the manifest itself |
| [INPUT_LATEST_REPORT_2026-10-03.md](INPUT_LATEST_REPORT_2026-10-03.md) | Byte-preserved user input, 65,630 bytes; historical claims/citations remain input, not authority |

## Reproduce the bounded source checks

Use isolated source snapshots/checkouts at the exact revisions below. Do not run against a working production directory, substitute a moving default branch, or interpret an expected changed result after a repair as evidence that the audit was false. These probes intentionally assert the old behavior, including defects; a passing probe is an audit reproduction, **not a passing product regression suite**.

The probes have an explicit source-root argument, write fixture data only in temporary directories, and print their JSON to stdout. They do not fetch providers, dispatch workflows or publish product artifacts. Graph/PIT writer checks inject a Parquet decode exception and intercept the replacement write. They prove the control flow, not real Parquet corruption or a production incident. Other graph checks inspect exact committed JSON or use pure fixtures. The Prophet probe extracts its checked-in synthetic fixture through AST. The W2 probe extracts only the named shrinkage function, without importing/running its historical probe program.

Requirements are Python with pandas and PyYAML for the graph probe, standard library for the Prophet probe, and pandas/SciPy for the W2 Spearman probe. The audit runtime lacked pyarrow, pytest and jsonschema; no full suite or binary Parquet recount is claimed.

### Graph and temporal checks

Required source: Macro **bebcb24db8707f93c3acca470590fead13e78dbd**, including the paths in the graph source manifest.

```bash
python graph_boundary_probe.py --source-root /path/to/macro-at-bebcb24
```

Compare the JSON result to GRAPH_BOUNDARY_REPRODUCTIONS.json. The injected failure warnings on stderr are expected. Checks G1 and G1b cover the two writer paths; G2/G3 membership; G4 rights-cache revision; G5 real artifact shape; G6 the documented daily-history constraint; G7 future freshness; G8 positive dual-clock/local/proposal semantics; G9 duplicate-key refusal.

### Prophet research-admission checks

Required source: Macro PR #8240 at **6d920952dc07731139cefc8a41cbd9bf92be5acf**, including its compiler and tests/test_prophet_fusion_w3_structural.py.

```bash
python prophet_boundary_probe.py --source-root /path/to/macro-at-6d92095
```

Compare with PROPHET_BOUNDARY_REPRODUCTION.json. UNKNOWN, REVOKED and lowercase rights_blocked admit research readiness in the inspected source; all decision flags remain false. Null acceleration refuses. This is not a legal determination or observed disclosure incident.

### W2 rank-invariance check

Required source: Macro **bebcb24db8707f93c3acca470590fead13e78dbd**, scripts/probe_theme_exposure_axes.py.

```bash
python w2_rank_invariance_probe.py --source-root /path/to/macro-at-bebcb24
```

Compare with W2_RANK_INVARIANCE_CHECK.json. Both Spearman values are 0.9746794344808963 in the audit runtime. Common positive affine shrinkage preserves rank in exact arithmetic; rounding, clipping, observation changes or noncommon coefficients would be different constructions. Historical raw-beta outputs and preregistration are retained; the explanation needs an appended erratum.

## Verification boundary

The publication versions of all three probes were rerun against the unchanged pinned source corpus. Every process exited zero and each parsed JSON matched its saved receipt exactly. Four independent reviewers checked their specialist portions of the plan; material corrections were integrated and the final scope/handoff gate passed after a mechanical successor-writer clarification.

Document checks cover JSON validity, expected hashes, internal Markdown paths/reference labels, preserved attachment/blueprint content and final publication content readback. External sources are exact primary publication/author/provider links with retrieval limits stated in the scientific review. An inaccessible methodology was not treated as inspected full text.

Nothing in these receipts establishes full CI, current production freshness, release acceptance of open PRs, a new runtime job, legal entitlement or predictive usefulness. Those are the implementation owners' remaining gates in the master plan.
