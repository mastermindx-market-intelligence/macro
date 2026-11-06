# F2 negative controls — time, revisions, corrections and withdrawal (2026-10-31)

Fabric lane NEWS-W3-F2-TIME under seat 602cd180, MASTERPLAN §7.F row F2
(`research/news_intelligence_estate_20261021/MASTERPLAN.md:387` — "Break
consequential claims with actual negative controls; reviewer independent of
author"), axis TIME AND CORRECTIONS. Branch `lane/news-w3-f2-time-corrections-r1`
at base `6ff08d8e1b093b89a0b7798d6880f7ba2ea25756`.

## Independence and scope

This lane authored none of the attacked modules (`engine/qbus_news_contract.py`,
`engine/qbus_news_reducer.py`, `engine/qbus_news_store.py`,
`engine/qbus_news_receipts.py`, `engine/qbus_news_intake.py`,
`engine/qbus_news_context.py`, `engine/qbus_news_velocity.py`,
`engine/massive_news.py`, `collectors/benzinga_news.py`); they predate this
branch at the base commit. All inputs are synthetic and built inside the
control script (placeholders such as `SYNTH-TITLE-07`, fixed 2026 ISO-8601
instants, no `datetime.now()` anywhere in the controls; the one injected clock
is a fixed lambda). Everything runs offline and deterministic: no network, no
model, no provider API, no real receipt/database/data file was opened. Every
SQLite database, receipt file and temp artifact is written under `--scratch`.
The seat can re-run the script itself; a control whose output does not
reproduce is rejectable. No source file was edited; the only outputs are this
document and the control script. Verdicts: HELD = refused/contained as the
claim requires; BROKEN = claim contradicted by observed behaviour;
NO_MECHANISM = no code path exists for the property; UNTESTABLE_ENV =
environment gap only.

## How to reproduce

From the repo root (worktree at base `6ff08d8e1b0`):

```
PYTHONPATH=. python3 research/news_intelligence_estate_20261021/f2_controls/nc_time_corrections.py --scratch /tmp/f2-time-check
```

Prints one `NC <ID> <VERDICT> <observed>` line per control plus one
`NC SUMMARY` line; exit code 0. Verdicts are deterministic across runs
(verified: two runs, identical verdict columns).

## Control results

| ID | Attack (MASTERPLAN line) | Claim attacked (F1 or estate doc path:line) | Target (path:line) | Verdict | Observed (script line) |
|---|---|---|---|---|---|
| T01 | §5.2 :243 separated clocks | F1:76 row 1 store read path; MP:243 | engine/qbus_news_contract.py:283 (normalize_news); engine/qbus_news_store.py:1562 (commit), :1923 (evidence_for_security) | HELD | `NC T01 HELD pub10:00 upd11:00 evt10:30 rcv12:00 distinct; row+state+evidence carry all four: fields=True row=True surface=True` |
| T02 | §5.2 :243 missing/invalid clock never fabricated | MP:243 (no silent wall-clock) | engine/qbus_news_contract.py:76 (_parse_clock), :283 (normalize_news) | HELD | `NC T02 HELD codes[missing_published_at=True,invalid_updated_at=True,received_at_not_aware=True,missing_updated_at=True] static-no-wallclock-in-contract=True` |
| T03 | §5.2 :243 impossible order recorded, not "normal" | MP:243; author claim tests/test_qbus_news_contract.py:144 | engine/qbus_news_contract.py:209 (_clock_anomalies) | HELD | `NC T03 HELD upd<pub flagged=True; evt<pub flagged=True; normalized+recorded not refused` |
| T04 | §5.2 :243-245 archive retrieved today ≠ possession | MP:243-245 ("A historical news archive retrieved today is not proof that the system possessed it in the past"); F1:76 row 1 read path | engine/qbus_news_store.py:2017-2023 (news_flow as_of); engine/qbus_news_velocity.py:49-68 (_STORY_SQL, no receipt bound), :291-297 (_effective_time prefers published_at) | BROKEN | `NC T04 BROKEN news_flow as_of=1019T00 r24h=1 daily28d=1 basis={'published_at': 1, 'received_at': 0} item rcv1020T12 pub1018T12; first_received kept=True` |
| T05 | §9.3 :504 late/out-of-order revision | F1:110 criterion 2; MP:504 | engine/qbus_news_reducer.py:166 (reduce_revision); engine/qbus_news_store.py:1562 (commit) | HELD | `NC T05 HELD commit v2-then-v1: stale=1 applied=0 current=SYNTH-TITLE-V2 history_rows=2` |
| T06 | §9.3 :504 same ID/new body at same version clock | F1:110; MP:504 | engine/qbus_news_reducer.py:273-281 (same_version_content_conflict); engine/qbus_news_store.py:73 (RevisionCollision) | HELD | `NC T06 HELD same version_at diff body: conflict=1 current=SYNTH-TITLE-A both_persisted=True` |
| T07 | §9.3 :503 duplicate report over another transport | F1:117 criterion 9 (no duplicate effects); MP:503 | engine/qbus_news_store.py:257 (UNIQUE(revision_id, transport, message_id, received_at)), :1083 (_persist_revision), :414-415 (first/last received) | HELD | `NC T07 HELD ws+alpaca same article: dup=1 deliveries=2 first=1018T12 last=1018T15 changes=1` |
| T08 | §5.4 :261 correction creates new history | F1:110; MP:261 | engine/qbus_news_store.py:239-255 (news_revisions append-only), :1562 | HELD | `NC T08 HELD after correction: current=SYNTH-TITLE-CORRECTED prior_row_retrievable=True history_changes=2` |
| T09 | P0-C :156 withdrawal vs correction tested separately | F1:117; MP:156 | engine/qbus_news_reducer.py:76-115 (_state_from_revision blanks :103-110; first_withdrawal :184-186) | HELD | `NC T09 HELD removed blanks title/url/teaser/tickers/channels/tags/body first_withdrawal=True; correction_keeps=True` |
| T10 | P0-C :156 + §9.3 :504 revision after withdrawal | F1:117; MP:156/:504 | engine/qbus_news_reducer.py:232-247 (withdrawn_requires_qualified_restoration) | HELD | `NC T10 HELD older/newer non-removed after withdrawal: stale=1/1 status=withdrawn blank; qualified_flag_restores=True` |
| T11 | §5.4 :261 denial does not delete the rumor | F1:110; MP:261 | engine/qbus_news_store.py:239-270 (per-item state key), :1562 | HELD | `NC T11 HELD after denial commit: rumor active/title/rev unchanged=True snapshot_stories=2 revisions=2` |
| T12 | §9.3 :504 correction after cache/model start | F1:117 (no stale claims); engine/qbus_news_context.py:1-4 ("Revision-bound evidence") | engine/qbus_news_context.py:18 (news_evidence_bundle); engine/qbus_news_store.py:1783-1787 (change_sequence), :1923 | HELD | `NC T12 HELD same now: revision_id differs=True bundle_sha differs=3ccf0ea4!=490c852e gen 1->2` |
| T13 | §9.3 :508 + §9.1 :477 sparse/quiet/unavailable/catch-up/pagination/malformed health | F1:117 criterion 9; F1:76 row 1 health census obligation | engine/qbus_news_receipts.py:248 (parse_health_receipt), :391 (load_health_receipt), :418 (write_health_receipt) | HELD | `NC T13 HELD 9 conditions all non-live when unhealthy; 3 malformed refused; missing/invalid-file->unavailable; write->load roundtrip live mode600=True ok=True` |
| T14 | §9.3 :508 malformed upstream response into intake | F1:117; MP:508 | engine/massive_news.py:303-334 (fail-closed row/JSON gates); engine/qbus_news_intake.py:57 (pump), :52 (_failed) | HELD | `NC T14 HELD client json=MASSIVE_MALFORMED_RESPONSE row=MASSIVE_ROW_MALFORMED; intake state=degraded err=massive_malformed_response stored=0/0/0 cursor_rows=0` |
| T15 | §5.2 :243 future-dated publication vs receipt detectability | MP:243-245 (possession discipline this gap enables) | engine/qbus_news_contract.py:209-217 (_clock_anomalies signature has no received param) | NO_MECHANISM | `NC T15 NO_MECHANISM pub1115 rcv1020 anomalies=(); _clock_anomalies src has no received param=True store 'clock_anomalies' mentions=1 (io only)` |

`NC SUMMARY held=13 broken=1 no_mechanism=1 untestable_env=0 total=15`
(15 executed ≥ the required 12; 0 UNTESTABLE_ENV).

## BROKEN findings

### T04 — `news_flow` reconstructs an as-of window from evidence the system did not possess then

- **Claim contradicted:** MASTERPLAN.md:243-245 — "A later materialised artifact
  may reconstruct an earlier cutoff only when its underlying evidence was
  actually available then. A historical news archive retrieved today is not
  proof that the system possessed it in the past." The flow surface is exactly
  a later materialised artifact that stamps its output with a caller-supplied
  cutoff (`as_of`, engine/qbus_news_store.py:2081) and closed windows
  "[as_of − 24h, as_of]" (engine/qbus_news_store.py:2056-2058).
- **Exact code lines that produce it:**
  engine/qbus_news_velocity.py:291-297 — `_effective_time` returns
  `published, "published_at"` whenever a publication instant exists, so the
  window arithmetic runs on the publisher clock; and `_STORY_SQL`
  (engine/qbus_news_velocity.py:49-68) selects every active state for the
  security with **no `received_at <= now` bound**, so possession is never
  checked. engine/qbus_news_store.py:2017/2023 passes the caller's `now` in as
  `as_of`. The output does label the basis (`time_basis_counts_24h:
  {'published_at': 1, 'received_at': 0}`), but the label does not bound the
  count by receipt.
- **Minimal reproduction** (hand re-derived at
  `~/lanes/tmp/news-w3-f2-time-corrections-r1/repro`, printed during STEP 4):

```python
from datetime import datetime
from engine.qbus_news_contract import normalize_news
from engine.qbus_news_store import NewsStore, NewsReadRights, RoutedRevision
T = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
store = NewsStore('<scratch>/t04.db', source_key='synth-key')
rev = normalize_news({'kind': 'news', 'id': 'SYNTH-MSG-1', 'data': {
    'id': 'SYNTH-ITEM-01', 'action': 'created',
    'timestamp': '2026-10-18T12:00:00Z',
    'content': {'id': 'SYNTH-ITEM-01',
                'created': '2026-10-18T12:00:00Z',
                'updated': '2026-10-18T12:00:00Z',
                'title': 'SYNTH-TITLE-01',
                'url': 'https://synth.example/SYNTH-01',
                'teaser': 'SYNTH-TEASER-01', 'stocks': ['SYNTH']}}},
    transport='benzinga_ws', received_at=T('2026-10-20T12:00:00Z'))
store.commit([RoutedRevision(revision=rev, security_ids=('SYNTH-SEC-1',),
                             universe_revision='SYNTH-UNI-1')],
             expected_cursor=None, next_cursor='SYNTH-CURSOR-1')
store.close()
ro = NewsStore.open_readonly('<scratch>/t04.db', source_key='synth-key')
flow = ro.news_flow('SYNTH-SEC-1', now=T('2026-10-19T00:00:00Z'),
                    rights=NewsReadRights.all_internal())
ro.close()
# -> as_of 2026-10-19T00:00:00Z, reports_24h: 1,
#    basis {'published_at': 1, 'received_at': 0}
```

  An item first received 2026-10-20T12:00Z is counted in the 24h window
  closed at 2026-10-19T00:00Z — presented as known 36 hours before its first
  local receipt. `daily_counts_28d` (sum 1) and `history_days_observed`
  include it the same way. The complementary half of the claim holds: the
  stored state preserves `first_received_at` (state_json), and
  snapshot/story/evidence surfaces expose `received_at = last_received_at`,
  never an earlier instant, so no surface presents the item as known before
  receipt on a *current* read; the break is specifically the as-of
  reconstruction in `news_flow`.
- **Scope note (separation preserved):** 600 registration cases / gated_v2 99
  drawn of which 74 routed MATCH (scorable) / gated_v3 135 drawn / 40 NEW
  cases routing-pending / 0 prospective. This control used none of them; it is
  synthetic-only.

## NO_MECHANISM findings

### T15 — no mechanism flags a publication instant later than first receipt

- Property attacked: detectability of a future-dated publisher clock relative
  to local possession (the precondition that lets T04's window arithmetic
  count pre-receipt evidence without any marker).
- Grep proving absence: `_clock_anomalies`
  (engine/qbus_news_contract.py:209-217) takes only
  `(published, updated, event_at)` — `received` does not appear in its
  signature or body; it can mint only `updated_before_published` and
  `event_before_published`. Runtime check: a revision with
  published/updated 2026-11-15 and received 2026-10-20 normalizes with
  `clock_anomalies == ()`. In `engine/qbus_news_store.py` the token
  `clock_anomalies` occurs exactly once, at :421 inside
  `_TUPLE_REVISION_FIELDS` (serialization io only) — the store mints no
  anomaly of its own. No read surface or receipt exposes a
  future-dated-publication marker.

## Existing author coverage (mapped, not counted — never run as F2 evidence)

- engine/qbus_news_contract.py — tests/test_qbus_news_contract.py (15 tests).
  Nearest: `test_ws_created_normalizes_identity_clocks_and_metadata` (:67),
  `test_clock_anomalies_are_preserved_and_flagged_not_clamped` (:144),
  `test_invalid_provider_clock_is_rejected_without_payload_echo` (:169),
  `test_naive_received_at_is_rejected` (:163). Goes beyond: T02 adds the REST
  `missing_updated_at` case plus the static no-wall-clock proof over the whole
  module; T15 shows the anomaly set has no published-after-receipt member
  (author tests cover only the two flagged kinds).
- engine/qbus_news_reducer.py — tests/test_qbus_news_reducer.py (15).
  Nearest: `test_older_same_domain_update_is_stale` (:61),
  `test_same_version_different_content_is_conflict_not_last_write_wins` (:76),
  `test_stale_direct_update_after_withdrawal_cannot_resurrect` (:98),
  `test_qualified_direct_reinstatement_can_restore_with_new_revision` (:116),
  `test_first_received_at_preserves_earliest_observed_receipt` (:205). Goes
  beyond: T05/T06/T09/T10 drive the same dispositions through the real store
  `commit` path and verify receipt counters and persisted history rows
  together; T10 tests both an older and a newer unqualified post-withdrawal
  revision.
- engine/qbus_news_store.py — tests/test_qbus_news_store.py (13) +
  tests/test_qbus_news_store_lifecycle.py (11). Nearest:
  `test_revision_id_collision_with_different_persisted_bytes_refuses`
  (:314), `test_exact_replay_advances_cursor_but_does_not_emit_duplicate_change`
  (:177), `test_explicit_withdrawal_removes_index_and_emits_remove_change`
  (:219), `test_correction_of_open_story_updates_snapshot_once_and_emits_one_change`
  (lifecycle :128), `test_stale_older_revision_does_not_regress_projected_fields`
  (lifecycle :483), `test_identical_revision_committed_twice_is_duplicate_without_second_change`
  (lifecycle :382), `test_same_revision_via_alpaca_rest_then_ws_is_one_story_and_delivery_only`
  (lifecycle :422). Goes beyond: T07 reads the raw delivery table and state
  clock fields via independent SQL (first/last receipt preserved, one change
  row); T11 covers the denial-vs-rumor pair, which no author test names.
- engine/qbus_news_store.py news_flow — tests/test_qbus_news_flow_store.py
  (7). Nearest: `test_news_flow_as_of_truncated_to_seconds` (:632),
  `test_news_flow_matches_snapshot_rows_under_rights` (:682),
  `test_news_flow_runs_on_query_only_connection` (:358). Goes beyond: T04 is
  the only as-of-before-first-receipt probe; author tests cover truncation,
  parity and connection hygiene, never a possession bound.
- engine/qbus_news_receipts.py — tests/test_qbus_news_receipts.py (20).
  Nearest: `test_fresh_health_can_be_live_without_recent_story_when_catchup_is_fresh`
  (:136), `test_stale_observation_receipt_is_unavailable` (:159),
  `test_gap_forces_degraded_even_when_socket_and_catchup_are_fresh` (:172),
  `test_missing_catchup_never_claims_live` (:181),
  `test_health_file_loader_is_unavailable_on_missing_or_malformed` (:190),
  `test_atomic_health_writer_replaces_file_and_uses_private_mode` (:201),
  `test_health_rejects_future_observation_and_counter_booleans` (:213),
  `test_additional_health_reports_observations_without_inventing_upstream_recency`
  (:273). Goes beyond: T13 exercises all §9.3 :508 conditions (including
  pagination-saturation via `additional_sources`) in one adversarial pass
  with a fixed injected clock and a write→load round trip.
- engine/qbus_news_intake.py + engine/massive_news.py —
  tests/test_qbus_news_intake.py (9) + tests/test_massive_news.py.
  Nearest: `test_malformed_response_shapes_fail_closed` (massive :330),
  `test_malformed_row_blocks_cursor_advancement` (massive :345),
  `test_page_budget_resumes_exact_continuation_without_advancing_completed_coverage`
  (intake :110), `test_periodic_rest_failure_does_not_disconnect_or_disable_live_intake`
  (intake :241). Goes beyond: T14 drives malformed upstream through the full
  real chain client→SupplementalNewsIntake→store in one pass and proves zero
  partial storage plus zero cursor rows via independent SQL.
- engine/qbus_news_context.py — tests/test_shared_news_intelligence.py:426-444
  exercises `news_evidence_bundle` (audience/revocation). Goes beyond: T12
  proves the pre/post-correction identity divergence with one fixed identical
  `now`, so the divergence is content identity, not read time.
- tests/test_chronicle_impact.py (67) — `test_event_time_vs_known_at_are_distinct_and_printed`
  (:49) is the adjacent time-domain claim in the chronicle subsystem; that
  subsystem is outside this lane's attack list and was not attacked here.

## Gaps

Evidence gaps only (no design, no repair proposed):

- T04's break is proven on the `news_flow` surface only. `snapshot`, `story`
  and `evidence_for_security` accept no as-of instant (their cursor is a
  delivery cursor, not a time), so for those surfaces the as-of property is
  absent rather than tested.
- The Benzinga REST/WS live catch-up path (`catch_up_once` /
  `apply_catch_up_batch`) was not driven with a synthetic HTTP transport;
  its contract/reducer/store layers underneath were exercised directly
  instead.
- T15's absence proof is static source inspection plus one runtime payload
  shape; it is not an exhaustive search over future-dated payload variants.
- Author tests were mapped by name and never executed (per commission); their
  pass/fail state at HEAD is unknown to this lane.

## Evidence

STEP 0 (environment, all observed values):

```
$ git rev-parse HEAD
6ff08d8e1b093b89a0b7798d6880f7ba2ea25756
$ git status --porcelain
(empty)
$ test "$(git branch --show-current)" = "lane/news-w3-f2-time-corrections-r1" && echo BRANCH_OK
BRANCH_OK
$ W=~/lanes/tmp/news-w3-f2-time-corrections-r1; mkdir -p $W; df -Pk $W | tail -1
/dev/nvme0n1p4  1392233480  664449404  699456140  49% /     # 699456140 KB free >= 5000000
$ python3 --version
Python 3.12.3
$ python3 -c "import fastapi, starlette, jsonschema" && echo IMPORT_OK
IMPORT_OK                                    # -> PY=python3, no venv needed (STEP 2 skipped)
```

STEP 1 anchors read before writing anything: MASTERPLAN.md sed ranges
241-265 (§5.2 :243, §5.4 :261), 150-157 (P0-C :156), 95-100 (:97), 382-390
(§7.F row F2 :387), 465-515 (§9.1 :475/:477, §9.3 :501-511 — :503/:504/:508);
F1_CLAIM_EVIDENCE_DENOMINATOR_MATRIX.md sed 64-120 (rows :76, criteria :110,
:117, :118); every TARGET grepped (`grep -n "def \|class "`) and the
exercised functions read line-ranged (cited in the table above). Author test
files counted per module (15/15/13/11/7/20/9/4/67) and nearest test names
mapped (section above); the repo test suite was never run.

STEP 4 (compile, dual run, verdict diff, repo cleanliness — W as above):

```
$ python3 -m py_compile research/news_intelligence_estate_20261021/f2_controls/nc_time_corrections.py
$ PYTHONPATH=. python3 <script> --scratch $W/run1 > $W/run1.txt 2>$W/run1.err   # exit 0
$ PYTHONPATH=. python3 <script> --scratch $W/run2 > $W/run2.txt 2>$W/run2.err   # exit 0
$ diff <(cut -d' ' -f1-3 $W/run1.txt) <(cut -d' ' -f1-3 $W/run2.txt)
(empty)                                                                      # verdicts deterministic
$ git status --porcelain
?? research/news_intelligence_estate_20261021/f2_controls/                   # only owned paths
```

`$W/run1.txt` verbatim:

```
NC T01 HELD pub10:00 upd11:00 evt10:30 rcv12:00 distinct; row+state+evidence carry all four: fields=True row=True surface=True
NC T02 HELD codes[missing_published_at=True,invalid_updated_at=True,received_at_not_aware=True,missing_updated_at=True] static-no-wallclock-in-contract=True
NC T03 HELD upd<pub flagged=True; evt<pub flagged=True; normalized+recorded not refused
NC T04 BROKEN news_flow as_of=1019T00 r24h=1 daily28d=1 basis={'published_at': 1, 'received_at': 0} item rcv1020T12 pub1018T12; first_received kept=True
NC T05 HELD commit v2-then-v1: stale=1 applied=0 current=SYNTH-TITLE-V2 history_rows=2
NC T06 HELD same version_at diff body: conflict=1 current=SYNTH-TITLE-A both_persisted=True
NC T07 HELD ws+alpaca same article: dup=1 deliveries=2 first=1018T12 last=1018T15 changes=1
NC T08 HELD after correction: current=SYNTH-TITLE-CORRECTED prior_row_retrievable=True history_changes=2
NC T09 HELD removed blanks title/url/teaser/tickers/channels/tags/body first_withdrawal=True; correction_keeps=True
NC T10 HELD older/newer non-removed after withdrawal: stale=1/1 status=withdrawn blank; qualified_flag_restores=True
NC T11 HELD after denial commit: rumor active/title/rev unchanged=True snapshot_stories=2 revisions=2
NC T12 HELD same now: revision_id differs=True bundle_sha differs=3ccf0ea4!=490c852e gen 1->2
NC T13 HELD 9 conditions all non-live when unhealthy; 3 malformed refused; missing/invalid-file->unavailable; write->load roundtrip live mode600=True ok=True
NC T14 HELD client json=MASSIVE_MALFORMED_RESPONSE row=MASSIVE_ROW_MALFORMED; intake state=degraded err=massive_malformed_response stored=0/0/0 cursor_rows=0
NC T15 NO_MECHANISM pub1115 rcv1020 anomalies=(); _clock_anomalies src has no received param=True store 'clock_anomalies' mentions=1 (io only)
NC SUMMARY held=13 broken=1 no_mechanism=1 untestable_env=0 total=15
```

T04 hand re-derivation (`PYTHONPATH=. python3 -c`, scratch `$W/repro`),
printed output:

```
published 2026-10-18T12:00Z, first received 2026-10-20T12:00Z
news_flow(now=2026-10-19T00:00Z) -> as_of: 2026-10-19T00:00:00Z reports_24h: 1 basis: {'published_at': 1, 'received_at': 0}
VERDICT: item counted at an as_of 36h before possession
```
