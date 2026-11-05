# EW-P2.T1 - rotation observation continuity: successor of #10104 (2026-10-31)

## Census

- #10104: rotation observation continuity (per the EW-P2.T1 commission; `gh` is
  prohibited in this lane, so the PR record itself was not read), branch
  `sol/web-defensive-rotation-notifications-20261023`, head
  `a324b7fc1f15e18393482ab18c4d97e12ebcbabe`, merge-base against main
  `c9608be2efd2f0e56cfb1630b6afe6a3124a6144`, Draft, author session
  `sol/web-defensive-rotation-notifications-20261023` ended
  (`ended_because: ci_handoff`) - orphaned.
- Carrier diff vs merge-base: ` 25 files changed, 4093 insertions(+), 10 deletions(-)`.
- #10103 (the display slice) was already merged 2026-10-23 and was not redone here.
- Successor BASE (origin/main at port time): `f2efb8baf983d3997abb000ecc29e523fbb1bba3`.
- Six conflict files: `.github/ci/legacy-jobs.yml`, `app/deploy/update.sh`,
  `lib/user_prefs.py`, `tests/test_account_prefs.py`,
  `tests/test_alert_delivery_drain.py`, `tests/test_ci_pack.py`. No other file
  conflicted (`git diff --name-only --diff-filter=U` listed exactly these six).

## Method

- `git merge --squash a324b7fc1f15e18393482ab18c4d97e12ebcbabe` onto BASE
  (`f2efb8baf983d3997abb000ecc29e523fbb1bba3`), then one single-parent commit on
  top of BASE. Why: the successor branch's diff vs main is exactly #10104's
  functional diff plus the two records, in one commit with no stale history;
  BASE is the merge parent, so the branch history stays `BASE <- successor`.
- Execution location note: the session root was quarantined by the ship-loop
  guard, so the merge was executed in the guard-minted admissible session tree
  (`claude/*` worktree) at the same BASE commit; the commit is identical in
  content and parentage to the packet's frozen method.

## Conflict resolutions

| file | main-side lines kept | #10104 lines kept | rationale |
|---|---|---|---|
| `.github/ci/legacy-jobs.yml` | all 8 hunks' full HEAD path blocks, in order | `      - "lib/rotation_observation_notification.py"` appended at each hunk end | preserve main's curated closures verbatim and extend them with the one new dependency |
| `app/deploy/update.sh` | 4 lines: 2 comments, `# BEGIN MACRO_API_RESTART_TRIGGER`, main's full trigger `if` line | `rotation_observation_notification` added into main's `lib/(institutional_13f_adapter\|institutional_intelligence)` group via exactly one substitution; theirs' stale trigger line dropped | main's trigger regex is current; only the lib group membership is #10104's intent |
| `lib/user_prefs.py` | `# Explicit delivery preference only; ...` comment + `"options_exposure_node",` | `"sector_rotation_relative",` | union of legal categories; opt-in tuple only, no default enrollment |
| `tests/test_account_prefs.py` | `"options_exposure_node"` inside the assertion | 2 DR3 comment lines + `"sector_rotation_relative"` in the assertion | union assertion covers both categories' availability |
| `tests/test_alert_delivery_drain.py` | main's whole block (node_decisions fixture through the quiet-window wall-clock test) | #10104's whole DR3 block (`_OBS_NOW` through the injected-clock test) | both blocks coexist; two blank lines separate them; `uniq -d` on def/constant names prints nothing |
| `tests/test_ci_pack.py` | 4 CURATED_EXCLUSIVE entries with their comments + trailing blank line | `# DR3: exact closure isolates the observation consumer; no packing ceiling change.` + `"rotation-observation-delivery",` | union of curated exclusive jobs |

## Port deltas

- PORT DELTA: legacy-jobs.yml eval-os-a1 += lib/rotation_observation_notification.py
- PORT DELTA: legacy-jobs.yml ontology-explorer += lib/rotation_observation_notification.py
- PORT DELTA: legacy-jobs.yml options-matrix-code += lib/rotation_observation_notification.py

Cause: `tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure`
failed on the successor naming exactly those three jobs - on current main their
import closures reach `lib/rotation_observation_notification.py` through files
#10104 touches, which was not yet true at merge-base `c9608be2`. Remedy per the
commission's T1 tripwire: add exactly the named missing path to each job's
`paths:` list (appended at list end); no path removed, no other key touched,
`tests/test_ci_pack.py` itself untouched for this. After the addition the file is
green (238 passed, rc=0).

## Dormancy proof

```
$ grep -n 'ROTATION_OBSERVATION_RECORDING_ENABLED' scripts/build_rotation_events.py engine/rotation_events.py lib/rotation_observation_notification.py
scripts/build_rotation_events.py:121:    if os.environ.get("ROTATION_OBSERVATION_RECORDING_ENABLED") != "1":
$ grep -n -A3 '_write_json(site / "marketdata" / "rotation_events.json"' scripts/build_rotation_events.py
210:    _write_json(site / "marketdata" / "rotation_events.json", payload)
211-    observation_recording = _record_early_observations(
212-        payload, data_dir=data_dir, site=site, art_dir=art_dir, explicit_stamp=explicit_stamp)
213-
$ grep -n -E 'art_dir is not None or explicit_stamp|_ledger_lane_armed|noncanonical_path' scripts/build_rotation_events.py
123:    if art_dir is not None or explicit_stamp:
125:    if not rotation_events._ledger_lane_armed():
131:            return {"status": "noncanonical_path", "receipts": 0}
```

The hook (`_record_early_observations`, scripts/build_rotation_events.py:112-139)
runs only after the JSON is published (line 210 write, line 211 hook), only when
the flag is exactly `"1"` (line 121), never on replay/scratch (`art_dir` or
`explicit_stamp`, line 123), only on the nightly ledger lane
(`rotation_events._ledger_lane_armed()`, line 125), and only on canonical
data/site paths (lines 128-131). Call-site delta: none -
`git log --oneline c9608be2..f2efb8baf983d3997abb000ecc29e523fbb1bba3 --
scripts/build_rotation_events.py engine/rotation_events.py` printed 0 commits.
The staged change set adds no scheduler/cron/launchd/systemd entry, no outbox
table, no SMTP credential, no DB migration, no roster, and no nightly YAML.

## Tests

Per file, `python3 -m pytest <t> -q -p no:cacheprovider`; counts are
passed/failed/skipped. Baseline was taken at BASE before the merge in the same
tree; successor counts are after the merge + conflict resolutions + T1 additions.

REQUIRED:

| file | baseline | successor |
|---|---|---|
| tests/test_account_prefs.py | 59/0/0 rc=0 | 74/0/0 rc=0 |
| tests/test_alert_delivery_drain.py | 100/0/15 rc=0 | 134/0/15 rc=0 |
| tests/test_ci_pack.py | 236/0/2 rc=0 | 238/0/0 rc=0 (after T1; 237/1/0 before) |
| tests/test_mailer_alert_template.py | 8/0/0 rc=0 | 80/0/0 rc=0 |
| tests/test_rotation_observation_builder.py | (file absent at BASE) | 13/0/0 rc=0 |
| tests/test_rotation_observation_integration.py | (file absent at BASE) | 38/0/0 rc=0 |
| tests/test_rotation_observation_notification.py | (file absent at BASE) | 170/0/0 rc=0 |
| tests/test_rotation_observation_state.py | (file absent at BASE) | 72/0/0 rc=0 |
| tests/test_dag_conformance.py | 48/0/0 rc=0 | 48/0/0 rc=0 |
| tests/test_admin_support_tickets.py | 78/0/0 rc=0 | 78/0/0 rc=0 |
| tests/test_alert_delivery_effect_boundary.py | 30/0/0 rc=0 | 30/0/0 rc=0 |
| tests/test_alert_prefs.py | 50/0/0 rc=0 | 50/0/0 rc=0 |
| tests/test_billing_emails.py | 108/1/0 rc=1 | 108/1/0 rc=1 |
| tests/test_brain_gateway.py | 452/0/0 rc=0 | 452/0/0 rc=0 |
| tests/test_capital_structure_saved_scenarios.py | collection error rc=2 | collection error rc=2 |
| tests/test_commercial_path_alerts.py | 21/0/0 rc=0 | 21/0/0 rc=0 |
| tests/test_email_templates.py | 32/0/0 rc=0 | 32/0/0 rc=0 |
| tests/test_frozen_options_account.py | 2/0/0 rc=0 | 2/0/0 rc=0 |
| tests/test_held_material_entitlement.py | 18/0/0 rc=0 | 18/0/0 rc=0 |
| tests/test_mailer.py | 42/0/0 rc=0 | 42/0/0 rc=0 |
| tests/test_mailer_held_material.py | 5/0/0 rc=0 | 5/0/0 rc=0 |
| tests/test_marketing_emails.py | 73/0/0 rc=0 | 73/0/0 rc=0 |
| tests/test_shared_pref_atomics.py | 14/0/0 rc=0 | 14/0/0 rc=0 |
| tests/test_support_api.py | 64/0/0 rc=0 | 64/0/0 rc=0 |
| tests/test_support_tier_routing.py | 18/0/0 rc=0 | 18/0/0 rc=0 |
| tests/test_unsubscribe_api.py | 34/0/0 rc=0 | 34/0/0 rc=0 |
| tests/test_user_prefs.py | 53/0/0 rc=0 | 53/0/0 rc=0 |
| tests/test_portfolio_changes.py | 70/0/0 rc=0 | 70/0/0 rc=0 |

REGRESSION:

| file | baseline | successor |
|---|---|---|
| tests/test_deploy_update_self_heal.py | 384/0/0 rc=0 | 384/0/0 rc=0 |
| tests/test_deploy_git_history.py | 19/0/0 rc=0 | 19/0/0 rc=0 |
| tests/test_market_memory_options_deploy.py | 18/1/0 rc=1 | 18/1/0 rc=1 |
| tests/test_market_memory_source_deploy.py | 3/0/0 rc=0 | 3/0/0 rc=0 |
| tests/test_health_commit_process_pinned.py | 4/0/0 rc=0 | 4/0/0 rc=0 |
| tests/test_rotation_events.py | 54/0/0 rc=0 | 54/0/0 rc=0 |
| tests/test_rotation_events_v2.py | 27/0/0 rc=0 | 27/0/0 rc=0 |
| tests/test_rotation_replay_isolation.py | 3/0/0 rc=0 | 3/0/0 rc=0 |
| tests/test_rotation_early_context.py | 58/0/0 rc=0 | 58/0/0 rc=0 |
| tests/test_account_actions.py | 117/0/0 rc=0 | 117/0/0 rc=0 |
| tests/test_leadership_rotation_contract.py | 67/0/0 rc=0 | 67/0/0 rc=0 |

Pre-existing failures, identical node ids on both sides, none added by the
successor:

- tests/test_billing_emails.py::test_webhook_still_200_in_mail_off_mode -
  `import stripe` raises ImportError (stripe SDK not installed in this
  environment); HTTPException 503 at app/billing.py:234.
- tests/test_capital_structure_saved_scenarios.py - collection error,
  `RuntimeError: document-term authority policy startup self-check failed` caused
  by `ValueError: document-term authority policy closure mismatch` at import of
  engine/capital_structure/document_terms.py:3896; reproduces at BASE with the
  full data/site tree materialized, so it is a main-side defect, unrelated to the
  26 owned files.
- tests/test_market_memory_options_deploy.py::test_legacy_api_dropin_migration_is_exact_and_fail_closed -
  the generated dropin-migration.sh exits 1; reproduces at BASE with the full
  tree materialized.

Environment note: baseline was first taken in the guard-minted sparse session
tree; `data/` (and then mockups/verify_shots) were materialized via
`python3 scripts/worktree_sparse.py add ...` when two rotation-early-context
failures proved to be sparse artifacts. The recorded baseline above is the
re-run in the fully materialized tree; both sparse-artifact failures are green
in the recorded baseline and on the successor.

`python3 scripts/agentos.py validate` -> 0 errors
(`agentos: 1980 records (108 workstreams, 525 decisions, 569 discoveries, 778
handoffs) — 0 error(s), 107 warning(s)`; the warnings are pre-existing
review-overdue notices on unrelated decision records).

## Statement

"This PR enables nothing. Observation recording and the opted-in notification
consumer stay dormant/default-off. Activation (EW-P2.T2+) needs its own gate."
