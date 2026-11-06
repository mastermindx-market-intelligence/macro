# UK policy desk — a quiet first cycle writes nothing (A-F02-W2-4)

Packet MO-A2 A-F02-W2-4. The defect was read at `148d1bfec8`; this branch
is cut from origin/main `ff4309ee6c` (fast-forward of that commit; `engine/uk_policy_brain.py` is unchanged). Display-tier null
disclosure (doctrine Law 5): a quiet window is not an outage, and it must not
look like the desk is off. No signal change. No model call added.

## Run receipt

GitHub Actions run `35819272085` (2026-09-23 04:52Z) was the first
whitehouse-sentinel cycle after #7351 set `UK_POLICY_DESK_ENABLED: "1"`.
`build_whitehouse` ran normally and committed `86904927`. That commit has no
`site/uk_policy.json`, no `data/uk_policy/`, and the log has no `uk_policy` line.

## Seat probe (live GOV.UK, 2026-09-23 05:04Z)

| Read | Result |
|---|---|
| `_fetch(SEARCH_URL)` | 46,227 bytes |
| `_parse_search_results` | 20 items |
| newest `published` | 2026-09-18T13:53:43Z |
| atom fallback | 20 items |
| `collect(4.0)` | 0 |

Every item was older than `max_age_days` (4.0). `run()` then took `if not items`
with no prior record and returned None. Fetch and parse failures are
`log.debug` only. `scripts/build_policy_watch.py` (around lines 380-384) reads
`site/uk_policy.json` only when the file exists, so the Policy Watch card stays
unrendered. Activation is correct. The first-cycle contract was the defect.

## `run()` before and after

| Branch | Before, on main | After this packet |
|---|---|---|
| Search and atom return nothing, prior exists | persist `source_outage`, silent | same persist, plus a warning, plus one INFO line |
| Search and atom return nothing, no prior | return None, write nothing, silent | return None, write nothing, warning `uk_policy: feed empty` |
| Feed reachable, nothing in the window, no prior | same silent None | persist `no_new` from the newest item; stance stays None; no model call; INFO `uk_policy: state=no_new` |
| Feed reachable, nothing in the window, prior exists | treated as `source_outage` | keep the prior headline; state `no_new` |
| Items in the window, all already seen | `no_new`, no model call | unchanged, plus one INFO line |
| New item inside the window | evaluate as today | unchanged, plus one INFO line |

`collect(..., window=False)` returns every parsed item, newest first.
`window=True` keeps today's age cut. Both paths use `_in_window`.

## Liveness after merge

The next whitehouse-sentinel cycle must commit `site/uk_policy.json` with
`state: no_new` while the window stays quiet, and the sentinel log must show
`uk_policy: state=no_new`. The next Policy Watch render then bakes the card:

```
grep -o 'data-uk-state="[^"]*"' site/policy_watch.html
```

The suite's pull-request home is the new `uk-policy-desk` job (`gate: code`).
The `outcome-spine` and `unrun-register-honesty` mentions stay `gate: data`.
