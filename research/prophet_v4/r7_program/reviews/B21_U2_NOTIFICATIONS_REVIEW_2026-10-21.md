VERDICT: FAIL

# B21 U2 — adversarial review of 6e6798aa (PR #9999), pure journey-notification producer

- Reviewer: ROUTE review, opus, MODE READ_ONLY. The artifact and seat worktree were not edited.
- Tree: U2TREE (merged tree dea1119e, origin/main + U2).
- Suite in U2TREE: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=U2TREE python3 -W ignore -m pytest tests/test_prophet_journey_notifications.py -q -p no:cacheprovider` gave **18 passed in 3.38s**.
- Private mutation copy: scratchpad/rv_u2mut (baseline 18 passed). Probe script: rv_u2mut/tests/rv_probe.py.
- Standard: B21_ALERT_STATE_MACHINE_CONTRACT_2026-10-21.md, plus the seat rulings (tier "essential"; episode_opened not minted; U2 is pure, with B1/B3 shapes replicated) and the frozen build packet pk/pro-source-b21u2-20261021.md.

Blocking count: **1 blocker, 4 major.** Each of the four majors is independently enough to fail the review.

## 1. Identity / dedupe key — BLOCKING

**B1 [blocker] The fire_event_id for `retracted` and `superseded` drifts across runs, so the same notice is sent twice.**
- Where: engine/prophet_journey_notifications.py:741 and :756. Both use `from_state = prev_lifecycle.get(episode_id, _LIFECYCLE_BY_SOURCE["ACTIVE"])`. That value comes from the *previous B3 projection*, which changes after the transition is applied. The causing B1 event, meanwhile, stays in the cumulative ledger and is re-derived on every run.
- Run N: prev lifecycle is ACTIVE, giving the key `…|ACTIVE->SUPERSEDED|…`.
- Run N+1: prev lifecycle is now SUPERSEDED (B3 `_expected_lifecycle_state`, a successor forces SUPERSEDED), giving `…|SUPERSEDED->SUPERSEDED|…`. This is a new key, so UNIQUE(fire_event_id) does not dedupe it and a second email goes out.
- `retracted` has the same defect. Once the episode is popped from the projection, the default flips from_state back to ACTIVE.
- This violates contract §2: the key must be a stateless function of the cumulative replay, with generation excluded for exactly this reason.
- Repro (rv_probe.py P1): derive the same ledger [OPENED, EXPIRED, IDENTITY_SUPERSEDED] with prev_rows lifecycle ACTIVE, then with SUPERSEDED.
  - Output: `run1 fid: ACTIVE->SUPERSEDED  run2 fid: SUPERSEDED->SUPERSEDED  equal: False`.
  - After run 1's row is marked sent, run 2 still mints `['SUPERSEDED->SUPERSEDED']`.
- Fix: derive from_state from the B1 replay state *before* the causing event, in ledger order, never from projection_prev. `episode_terminal` already hard-codes ACTIVE (:692-708) and is stable, but only because it ignores the actual prior state.
- Related nit, also on the side of correctness: the replay chain sorts by (recorded_at, event_id) at :617-620. B1's canonical replay order is (known_at, source_system, source_event_id) (us_candidate_episode.py:385-391). Any replay-state-derived from_state must use B1's order.

PASS items on this surface:
- Key literal shape `prophet|kind|episode|from->to|b1_event_id|user_id` (:281-295).
- The parse round-trip (:298-324).
- The uuid5 synthetic alert_id is deterministic (:327-334).
- Dropping user_id is caught by the tests (mutation M1).

## 2. Eligibility vs contract (incl. seat rulings) — BLOCKING (major) + NOTES

PASS:
- `episode_opened` is not minted in v1. OPENED is counted as ineligible at :770-774, and test 10 pins it.
- Terminal transitions map through the B3 table (:163-180).
- U2 is pure. It imports only re, uuid, dataclasses and typing; test 17 checks this. It does not drain, send, persist or schedule.
- No trade, sizing or recommendation language appears in any template (:363-405).

**E1 [major] Stale replay: historical events mint with a fresh send window.**
- Where: `_not_after` at :862-877 anchors on the *run's* `inputs.market_session`. Contract §5 (:318-320) says the end of the session following the *transition's* market_session.
- There is also no mint-time recency gate. Contract §5 (:310-317) requires an unknown/stale event to be suppressed at mint, in the fif R3 shape.
- Effect: on a first run, a backfill, or a user adding a ticker, every historical eligible B1 event for that ticker mints a sendable row.
- Repro (P4): an INVALIDATED transition recorded 2026-08-25, with run session 2027-03-01, gives `fired_at 2026-08-25T03:00:00Z not_after 2027-03-02T21:00:00Z`. An event six months old would be emailed.
- The build packet froze "calendar row whose market_session == inputs.market_session". If the seat ratifies that, a recency gate is still owed by contract §5.

**E2 [major] Banned-glance false positive suppresses every notice for any ticker ending in "PE".**
- Where: `_GLANCE_MACHINE_TOKENS` contains `"pe:"` (:140). `_glance_is_clean` lowercases the text and substring-matches it (:408-418). Every template begins `f"{ticker}: …"` (:375-404).
- So "HPE: …", "CPE: …" and similar always match `pe:`.
- Repro (P3): an OPENED+INVALIDATED episode for ticker HPE gives `rows: 0 banned_term: 1`, with text `HPE: the Prophet research journey you follow has closed …`.
- Fix: match the `pe:`/`pee:` id shapes anchored on a regex such as `\bpee?:[0-9a-f]`. Do not test the composed glance by lowercase substring.

**E3 [major, test discrimination] Non-terminal STATE_TRANSITIONED is not pinned.**
- Mutation M3 replaced `if target not in _TERMINAL_SOURCE_STATES:` (:694) with `if not target:`. The mutant mints `('episode_terminal','ACTIVE','ACTIVE')` for a STATE_TRANSITIONED→ACTIVE and the suite still passes (**18 passed**). The eligibility gate is untested.

NOTES:
- N1 [minor] prev UNESTIMABLE → TRIGGERED is derived (:787-797; test 7 at :489-500). Contract :112-115 says UNESTIMABLE on *either side* is never eligible. The implementation is a pragmatic reading: the B3 default emergence is UNESTIMABLE, so otherwise the kind would be dead. It matches the build packet's "NOT TRIGGERED in prev (or absent)". The seat must ratify it explicitly as a contract deviation.
- N2 [minor] A READ_UNAVAILABLE projection_prev degrades to empty (:530-539) instead of failing closed. With B1 above, that silently shifts from_state and emergence diffs.
- N3 [nit] Emergence is not gated on the curr lifecycle being ACTIVE (:777-818).
- N4 [minor] `_episode_identity` (:546-564) takes the ticker and company only from the OPENED payload and never applies a CORRECTED patch. A corrected ticker keeps routing to subscribers of the old ticker and keeps the old ticker in the glance.

## 3. Correction table — BLOCKING (major)

PASS:
- The quarantined branch (failed, attempts ≥3, effect_unknown_after_smtp) mints nothing (:989-998), and mutation M5 is caught.
- The unsent branch patches the original to suppressed (:999-1011), and mutation M4 is caught.

**C1 [major] The producer's own patch-suppression feeds back into "suppressed ⇒ mint anyway", so a retraction is sent for a notice the user never received.**
- Where: run 1 has the original pending, so the code PATCHes it to `suppressed / superseded_by_prophet_correction` and mints no row (:999-1011; the build packet's freeze). Run 2 sees status `suppressed`, takes the `("sent","suppressed")` branch (:984-988), and mints the correction.
- Contract §4 (:286) says that for unsent, exactly one email is ever sent. Contract :291-295 says a retraction is minted only when the original was sent.
- Repro (P6):
  - run 1 gives `patches: 1 rows: []`;
  - run 2, with outbox `suppressed / superseded_by_prophet_correction`, gives `('retracted', 'XYZ: this name is no longer tracked; the earlier notice is withdrawn.')`, about a notice never sent.
  - corrected_material copy likewise says "the journey you were shown".
- Fix: treat `last_error == "superseded_by_prophet_correction"` as producer-suppressed and do not mint, distinct from a user opt-out suppression.
- Also note: the build packet ("unsent ⇒ patch, no correction row") deviates from contract §4:286 ("PATCH the original … then insert the correction row"). The seat should state which one governs. Under the packet's reading, the fix above is mandatory.

**C2 [major] The corrects chain cannot target emergence_triggered originals.**
- Where: :820-853. `emergence_triggered` is derived only in the run where the prev→curr diff fires, so a later run's chain never contains it.
- A later RETRACTED or IDENTITY_SUPERSEDED therefore gets corrects=None (or an older event) and lands in `no_original`. A user told "turn triggered" is never told about the withdrawal or supersession.
- Repro (P5): run 1 gives `['emergence_triggered']`, sent. Run 2 adds IDENTITY_SUPERSEDED and gives `rows: [] no_original: 1 corrects: [None]`.
- A retraction of an OBSERVED relation targets "the latest prior event of the episode", not the notice keyed on that relation.

**C3 [minor] The retracted copy is wrong for a relation-level retraction.**
- Retracting an OBSERVED relation leaves the episode tracked, but the copy at :391-394 says "this name is no longer tracked".
- Repro (P7): `[('retracted', 'XYZ: this name is no longer tracked; the earlier notice is withdrawn.')]`.

## 4. Tier — PASS

- `REQUIRES_TIER = "essential"` (:84) is stamped on every row (:476). Test 2 ranks it against the tiers module.
- compose_payload emits exactly the 17 contract §6 keys (:442-486).

## 5. Test discrimination — NOTE (gaps feed the findings above)

- Caught: M1 (identity user_id), M4 (unsent→row), M5 (quarantine fall-through), M6 (glance check disabled).
- Survived: **M3 (eligibility gate)**. See E3.
- M2 (from_state made stateless) fails 1 test. The suite therefore *pins* the projection-dependent from_state that causes B1, which means the suite asserts the bug.
- Missing tests:
  - a two-consecutive-run identity test with an evolving prev projection;
  - a ticker containing "PE" before the colon;
  - derive_events input-order shuffling (test 18 shuffles only plan_enqueue inputs);
  - the patched-suppressed second run (C1);
  - an emergence original followed by a later correction (C2);
  - a non-terminal STATE_TRANSITIONED (E3).
- The B1 envelope check is complete. The test fixtures mint real `make_event` envelopes. The engine reads recorded_at, definition_era, correction_of, payload.patch, payload.episode_state and successor_episode_id, and all match B1 make_event/replay (us_candidate_episode.py:293-311, :582-616).

## Mutation reruns

All were run in scratchpad/rv_u2mut with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$M python3 -W ignore -m pytest tests/test_prophet_journey_notifications.py -q -p no:cacheprovider`. The engine was restored from rv_engine_orig.py after each run (diff verified).

| # | Surface | Mutation | Result |
|---|---|---|---|
| M1 | identity | drop `|{user_id}` from fire_event_id (:294) | 2 failed, 16 passed — caught |
| M2 | identity | from_state at :741/:756 → `"ACTIVE"` | 1 failed, 17 passed. The probe then gives a stable key (`equal: True`, run 2 mints nothing), so the test pins the drift |
| M3 | eligibility | `if target not in _TERMINAL_SOURCE_STATES:` → `if not target:` (:694) | **18 passed — SURVIVED** |
| M4 | correction | remove `continue` after the unsent patch (:1011) | 1 failed, 17 passed — caught |
| M5 | correction | remove `continue` after original_quarantined (:997) | 1 failed, 17 passed — caught |
| M6 | glance | `_glance_is_clean` → `return True` | 1 failed, 17 passed — caught |

Probes P1 and P3 through P7: `cd rv_u2mut && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$M python3 -W ignore tests/rv_probe.py`. Outputs are quoted above.

## CI registration (checked by diff only)

- legacy-jobs.yml adds the module and the suite to the gate:code prophet-lab `paths:` and adds one pytest step. That matches the packet.
- test_ci_pack.py bumps two ceilings by exactly +3 (templates/index.html 5,825→5,828; scripts/build_free_content.py 5,798→5,801), which is consistent with the one-step +3 estimator.
- The commit note says "all three probes", but only two ceilings move. I did not verify whether the third probe has a separate ceiling (see Not reached).

## Not reached

- Running tests/test_ci_pack.py and the CI manifest checker in U2TREE to confirm the ceilings and the exclusive-job import closure. I checked the diff only.
- Order-randomized suite runs: pytest-randomly is not installed (`ModuleNotFoundError`).
- Whether the third probe has its own ceiling that needed a bump.
- A full audit of every compose_payload field value against contract §6 semantics. Only the key set and the tier were checked.
