# Recovery consumer contract and release sequence

Owner: existing Leader Radar producer, Macro PR #8750. No consumer owns a new lifecycle.

## Contract

Each existing `rows[i].display_chips.leader_recovery` includes schema/version, source cut, deterministic definition hash, source fingerprint, state/reason, prior-leader evidence identity, correction episode references, failed-repair count, entry context, expectation observations and explicit evidence limitations. Top-level `recovery_roster` is an alphabetical read-only projection. The old `state`, `raw_state`, fire fields, ordering and RS-high roster remain independent.

Consumers must present price recovery, relative-leadership repair and entry extension independently. UNKNOWN fundamental thesis is not a healthy thesis. Missing observations are not proof of no recovery. An old failed repair remains a historical failed repair after a new attempt succeeds. Current adjusted reconstruction is not the state the system necessarily knew at that historical time.

## Intended UI behavior (not created)

Inside the existing Leader Radar, expose searchable former-leader rows with damage depth and its paired peak/trough dates, current repair stage, failed attempts and last failure, source-date/quality disclosure, expectation changes and separate entry stance. Do not label every recovering name as buyable. A PLTR drilldown must show its June damage, August reconstruction and present extension without implying a June-bottom forecast. Large/short-history/missing-data and completed-but-RS-lagging cases require explicit presentation.

The specific recovery UI write was refused. This is a design contract only, not a replacement UI payload or alternate attempt. The original operation must remain fenced until the real permission/capability boundary changes.

## Integration order and acceptance

1. Release the source through the existing PR after exact-head CI and required independent acceptance; preserve all old owner semantics.
2. Authorized UI work consumes this JSON in the existing surface, with bilingual/keyboard/mobile/stale/empty-state verification. No parallel store or state engine.
3. Natural nightly producer and actual served payload/page must agree on source and definition hashes. A local source run or synthetic fixture is not this acceptance.
4. Optional future capture enrollment is a separate configuration act after review. Confirm the existing nightly history stores actual observed_at, preserves first records on rerun/correction/disarm, and the reader respects knowledge cutoffs. Do not backfill old snapshots with fabricated observation times.
5. Leadership Lab and Live Entry Radar may consume the observations read-only under their existing owners. No changes to their active branches are made by this implementation.
6. Any probabilistic, ranking, entry, sizing or alert promotion requires a new evidence decision, realistic costs and a genuine prospective or untouched/PIT-qualified population. Current empirical comparisons did not show incremental return superiority.

Reproduce focused tests through the existing `leader-radar-unit` compiler-selected CI step. Run historical tools using only explicit research output paths, e.g. `python -m scripts.research.leader_recovery_policy_study --as-of 2026-10-08 --out /tmp/policy.json`. Retain the given source fingerprints or disclose new vintages on rerun.
