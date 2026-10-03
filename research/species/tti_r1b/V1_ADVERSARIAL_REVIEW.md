# R1-B v1 adversarial prereg review — superseded before registration

Status: **V1 NOT REGISTERED, NOT RUN, NO OUTCOME COLUMN OPENED.** The immutable v1 freeze remains at `0c54e10e20c43827802d3d829505f74f57f8eb5f` as an audit record. This review supersedes its execution target with v2 before any empirical use.

## Finding 1 — future-label conditioning risk in matched controls

The v1 config carried `matched_control_exclude_selected_family=true`. Excluding a BASE candidate because it later became a reclaim/exhaustion event would use a future selector label to define the control pool and can create post-treatment / immortal-time bias. V2 forbids this. Controls are selected from candidate-time covariates only; future family membership cannot admit or exclude a control.

## Finding 2 — candidate/re-entry identity was underspecified

V1 said both “first qualifying event per selector” and “re-entry disabled” without stating whether an earlier raw fresh-low candidate that never qualified RECLAIM consumed the day's opportunity to observe a later qualifying reclaim. V2 makes the law explicit: every selector may emit at most its first qualifying event per symbol/session; an earlier anchor that does not qualify that selector does not consume it. After a selector fires, no second same-selector event is admitted.

The matched-control substrate is separately de-overlapped as the first lawful BASE anchor per symbol/session/30-minute bin. This control census is not a sixth selector or a new trial family.

## Finding 3 — one low anchor was insufficient for confirmation economics

V1 recorded candidate-low LOD survival and candidate-low-to-entry delay only. A reclaim can occur after price undercuts the original candidate without hitting the much wider continuation close threshold, so the actual episode low before confirmation can differ from the candidate low. V2 reports both anchors: candidate low and minimum low from candidate through confirmation. This keeps local-turn profitability, exact candidate-LOD survival and confirmation cost distinct.

## Disposition

No thresholds were changed from market outcomes; no R1-B market data was inspected. The five selectors, four horizons, three cost sensitivities and all price thresholds remain unchanged. V2 changes only causal/control identity and diagnostic bookkeeping. V1 is **DO_NOT_RUN**; only a separately committed v2 prereg/config may be registered.
