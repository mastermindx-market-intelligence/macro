# Sector Intelligence v1.1 — adoption return from the active v1.0 build team

**Date:** 2026-11-10 (07:15Z) · **From:** Orchestrator COO, T3 thread `2f136a11-91f9-4bca-bf10-8a1d8b7f4e5d`
· **Programme:** Macro #7646 / `WS:SECTOR-INTELLIGENCE-COMPLETION` (#10915 → #10922 lineage)
· **Source adopted:** macro #10939, handoff `FABLE_V11_AMENDMENT_HANDOFF_2026-11-09.md`

This is the return the handoff's §8 asks for. It records adoption of a source delta into the
existing team. It is not a new Executive root, a second team, a fresh START, a migration APPLY or a
release authorization. Rungs are reported separately: delivery ≠ ACK ≠ adoption ≠ START ≠ CI ≠
merge ≠ served proof ≠ acceptance.

## 1. Received / adopted source

| Fact | State |
|---|---|
| Delivery | Routing message received in the COO thread. |
| ACK | Handoff @`aa89465d4494`, consolidated checkpoint @`5ffd227f249b`, Prophet v5.1 @`1f645a751ea2` (§18, §18.14) fetched and read by the COO. |
| Protected source | #10939 is **merged**; main @`f860c2810223` carries the handoff, the Prophet integration amendment, the R6 build spec, manifest, JSX and `V11_VERIFICATION_2026-11-09.json`. |
| Adoption by the team | The lane-specific delta (`/tmp/si_plan/v11/LANE_DELTAS_V11.md`, contents mirrored in §3 below) was sent to the seven existing lane threads at 07:10–07:12Z; all seven show a running run. **Routing sent and runs started is the rung reached.** No lane has yet returned an amended head, so no amended contract is adopted in source yet. |
| Not done | No new team, root, START, APPLY or release. Lane 2 (design) was not re-opened: R6-01..11 + RN3-0 are bound by reference to the merged manifest. Lane 9 (integrated proof) has not started. |

## 2. Current ownership, and effects that are protected

- **Root:** the existing COO thread above. **Shared-file writer:** lane 3 alone writes
  `SectorIntelligenceWorkspace.tsx`, `sectorIntelligenceLex.ts`, `sectorIntelligence.ts`,
  `app/api/sector-intelligence/route.ts` (and `sectorDepthReturn.ts`); other lanes return hunks.
  **Investigation contract:** lane 6 alone integrates it.
- **Live writer outside this team:** `mastermidx4` (Chairman-authorized Terminal PR-duty recovery)
  pushed `baeae997d788` onto lane 6's branch at 06:59Z (tests only) and enabled protected
  auto-merge on Terminal #1410. Lane 6 was told to read it first and not to revert, force-push or
  disarm.
- **Arms left as found:** #10923 and Terminal #1413 and #1410 carry `merge-on-green`. #10929 is
  draft with `hold`, `merge-blocked`, `do-not-merge`.
- **Fenced, unchanged:** `.github/ci/legacy-jobs.yml` and `tests/test_ci_pack.py` (#10839
  proposal, `ACTION_BLOCKED_NO_REPLAY`). Lane 1 asked to carry registration edits there; the COO
  ruled **not authorized**. The registration gap on #10929 has no executing owner and is an open
  decision for the Chairman / capability owner.
- **Prophet Paper holds untouched:** `prophet-sector-20261109-sx05-attribution` and
  `prophet-four-turn-t2-20261109-mplans-tabs`. No read, retry, recreation or finish was attempted.
- **Unknown, stated as unknown:** the installed database state (§5); whether any other open PR
  claims migration prefix 0049.

## 3. Carriers reused, and what changed

| Lane | Carrier and head at adoption | Retained output | Contract changed by v1.1 |
|---|---|---|---|
| 1 Macro generation | macro #10929 @`eabee55527a3` (moved from `64cba740` by the lane's own copy-deck re-anchor) | Composed generation, eleven sector rows, API closure (denied-before-read, no-store, one-reader, 4 MiB) | Max-five-member example reclassified LEGACY. Adds full membership / industry / source-cut through the owner's bounded versioned cursor, finite JSON from the ordinary producer, captured Prophet compatibility tuple, original-ref resolver, no mid-read pointer mixing. Also carries lane 7 and lane 8 field requests as optional typed blocks. |
| 2 Design | macro #10923 @`8abe28febaf0` | Accepted as-is | None routed. R6 boards bound by reference. |
| 3 Terminal workspace | Terminal #1414 @`df92e9a1712b` | Job shell, Brief / Explore / dossier, codec, identity fences | Adds context → full members → Prophet Setup → original evidence → precise return; mounts lane 4, 6, 7 hunks; first entitled capture. |
| 4 Cycles | Terminal #1413 @`f1196159479d` | C01–C28 accepted as-is | Withdrawal state, confirmed vs first-known, fixed windows, per-head capability, "not qualified today" wording. |
| 5 Research v2 | macro #10931 @`b25fd58e351e` | Accepted as-is | Original issuer economics, cohort denominators, all-alias exclusion, shared roots and concentration. |
| 6 Investigations | Terminal #1410 @`baeae997d788` (moved from `e3169b21` by the recovery writer) | v2 validators, actor fence, four action components, source-only 0049 | Observe installed preimage first; one v2→v3 sequence with Prophet D05; TS/Python `review` parity; retained bytes and rights. |
| 7 Retained depth | Terminal **#1419** (opened 07:12Z during recovery; branch `claude/ssd-si-lane7-42c9c92701b014ab`) | Five depth components + legacy map. The lane's carrier had failed three runs on a provider error with its commit unpushed; it was moved to another model and recovered on the same thread. | Full-population continuation, native identity per row, independent-emergence path. |
| 8 Analytics | macro #10924 @`4cdebe92d9dd` | Hazard and row-weighted prior withheld — accepted as-is | No inherited 4/6 badges; four heads qualified or withheld individually; predeclared protocol; LOO / peer exclusion; seven comparators; independent statistical review. |
| 9 Integrated proof | not started | — | SI/SP evidence join, served consumer, update, correction, rollback — opens when lanes 1, 3 and 6 return. |

## 4. First next proof

One entitled native Sector capture → complete, correctly joined membership → a real
Prophet-covered member's Setup → exact original evidence → restored Sector origin, with no
mid-read latest-pointer mixing.

- **Owner:** lane 3 (consumer) with lane 1 (producer).
- **State today:** never exercised. The only live observation so far is an unauthenticated `401
  access_denied`; the admitted path has run on a SHA-pinned fixture only.
- **Now in motion:** lane 3 has a member login and is attempting the entitled capture against the
  live route first, before building further. Full membership beyond the first page does not exist
  in the producer yet (lane 1 delta), so the membership and Setup legs of this proof cannot be real
  until lane 1 returns.
- **Evidence destination:** captured wire, SHA-pinned, in Terminal #1414; summary in the PR body
  and in this programme directory.

## 5. Persistence composition (lane 6)

- **Installed preimage: not observed.** Nobody in this programme has read the installed database.
  The earlier "0040 applied; 0042 / 0047 unapplied" was a lane report, not an observation. Lane 6
  is commissioned to read `md5(pg_proc.prosrc)` against `a554c15c1ae58dfbd34d04bcda9b5e48` (0047
  body) and `75f2b7feba6b3c9f177f4cda6c3605e9` (exact 0049) through an existing read path, or to
  return the exact refusal.
- **0049 reservation:** Terminal master ends at `0048_brief_delivery_team_sharing.sql`. The only
  0049 known to this team is lane 6's source-only
  `0049_sector_intelligence_investigation_admission.sql` on #1410, unmerged and unapplied. No second
  0049 was allocated. Whether another open PR also claims 0049 is not yet checked — lane 6 owns
  that check.
- **One v2 / v3 sequence:** commissioned, not yet composed. Constraints passed verbatim: no second
  0049, no v3 against old 0047, no guessed prefix, no APPLY; compatible readers before new writes;
  rollback stops new creation while created-record readers stay.
- **Timing risk:** #1410 is armed to auto-merge. If it merges before v3 is composed, 0049 lands as
  structural admission only and v3 must take the next prefix from the existing allocator.

## 6. Remaining, and acceptance

Remaining capabilities are those in §3's right-hand column plus lane 9. Acceptance stays the
original 134 / B / P / J items plus SI01–SI20 and SP01–SP24 evidence; "tests pass" on a fixture is
not acceptance. Lane returns land in each lane's PR and are joined here by the COO.

## 7. Status at 09:20Z (first adjudication pass)

Sections 1–6 are the 07:15Z record and are left as written. This section supersedes them where it
differs. Nothing below is merged, served, applied or accepted unless it says so.

### 7.1 Lane returns

| Lane | Head now | Rung reached | What the return established |
|---|---|---|---|
| 1 | macro #10929 @`8c3fed6ffa34`, draft, held | DELIVERED, reviewed, third pass running | Entitled `GET /api/sector-generation/population` with signed cursors; finite JSON in both ordinary writers; seven typed blocks carried from existing artifacts. Review result in §7.3. |
| 3 | Terminal #1414 @`3004b74f48bc` | RUNNING | No v1.1 return yet. Entitled capture still unreported. Auto-merge was enabled on this PR by the Terminal PR-duty recovery writer at 08:09Z. |
| 4 | Terminal #1413 @`3445b49a3cd1` | RUNNING | No v1.1 return yet. |
| 5 | macro #10931 @`b25fd58e351e` | RUNNING | No v1.1 return, nothing pushed. Three provider failures; resumed on the same thread each time. |
| 6 | Terminal #1410 @`dc02f1c28879` | DELIVERED (a, b, c); v3 build running | §7.2. |
| 7 | Terminal #1419 @`f6f2bfac4ef8` | RUNNING | No v1.1 return yet. Asked to check lane 1's carried blocks against its components. |
| 8 | macro #10924 @`3e6b51ef09fc`, armed | DELIVERED, armed, not merged | Four forecast heads judged individually on real US tapes: remaining-return distribution failed and is withheld; adverse tail, target-before-invalidation and transition time qualify in research only and stay withheld on live records (no live record carries the protocol epoch). Comparators: sector allocation did not beat passive SPY; member-selection comparators unavailable for lack of point-in-time constituents. Independent statistical review returned and adjudicated. Out-of-scope finding filed as macro #10943. |
| 9 | not started | — | Waits on lane 3's return. |

### 7.2 Persistence (lane 6) — replaces §5

- **Installed preimage, observed.** One read-only catalog SELECT through Terminal's documented
  census path: `public.valid_investigation_manifest_v2` has `md5(prosrc) =
  16f7838c8e797663d64783cff92fb6ef`, the **0040** body. It is neither the 0047 body (`a554c15c…`)
  nor the sector admission body (`75f2b7fe…`). The other guarded functions are absent. 0042 and 0047
  are unapplied; the sector guard would refuse today. Terminal has no migration ledger.
- **0049 was double-claimed.** Terminal #1290 (opened 2026-11-04) holds 0049. Lane 6's file on
  #1410 was a later, second claim made on a wrong census. The COO recorded a `hold` and disabled
  auto-merge on #1410 (issuecomment-6762436659). Lane 6 renumbered through the README allocator to
  **`0052_sector_intelligence_investigation_admission.sql`** (commit `dc02f1c28879`; body, md5 pins,
  guards and rollback unchanged). The COO verified the PR file list, removed the hold and restored
  auto-merge (issuecomment-6763279738). #1410 is not merged.
- **One v2 → v3 sequence, written, not built.** (1) Python/TS `review` parity — done. (2) Prefix —
  done. (3) v3 readers in TS and Python, no writes. (4) Sector carrier, operator order
  0042 → 0047 → 0052. (5) One additive v3 migration composed over the sector body, prefix taken from
  the allocator when authored. (6) Retention and current-rights qualification before v3 writes open.
  (7) Rollback in reverse; created-record readers stay. Steps 3 and 5 are commissioned on a new PR
  stacked on #1410, source-only. No APPLY.
- **Open dependency.** Terminal #1312 (prefix 0051) pins bodies of
  `apply_investigation_revision_v2`, which the v3 migration also changes. Whichever merges later
  composes over the earlier one's exact body.

### 7.3 Independent review of lane 1's route (`eabee55527a3..5129620204c4`)

Read-only reviewer, separate context; report at `/tmp/si_plan/reviews/lane1_population_review.md`,
adjudicated by the COO. Passed: denied-before-read and gate order, no arbitrary generation / path /
domain reads, cursor signing, one capture per read (SP01), the 4 MiB bound, one reader, `no-store`,
finite JSON. Upheld against the lane:

- **Blocker — the population is reported complete when it is not.** `complete` can never be false
  because the producer's member count is the count of listed members. Five current configured
  members are not served and not counted; two removed members are reported as "missing". SP02 and
  the "full membership" requirement are therefore **not** evidenced yet.
- **Should-fix.** With no cursor secret configured, a restart turns every cursor and context
  reference into `400` instead of a reset, and the "retained original" reference is not durable.
  Tests for those paths were missing.
- **Factual correction.** A current GICS industry field exists for 617 of 698 symbols
  (`site/stagedata/screener.json`); the lane had reported 424 from a different source. Neither is
  point-in-time, so SI02's point-in-time identity remains unsatisfied.

Lane 1 is fixing all of these on the same PR; a follow-up review of the new commits is owed.

### 7.4 Carriers and platform

- The local inference gateway refused `glm-5.3` routes at 07:42–07:59Z (`FABRIC_ALL_ROUTES_COOLING`)
  and dropped a connection at 08:53Z. Lanes 1, 5 and 6 failed mid-delta and were recovered on their
  own threads; no duplicate worker and no new team was started. Lanes 1, 6 and 7 now run on
  `claude-sonnet-5-5`; lanes 3, 4 and 5 on `glm-5.3`.
- `gemini-4-argon` was withdrawn by the Chairman on 2026-11-10 and is removed from the lane charter.

### 7.5 Open, with owners

- **#10929 cannot be served while held.** It stays draft on the CI-registration check that needs
  edits to the fenced `.github/ci/legacy-jobs.yml` and `tests/test_ci_pack.py`. Until it merges,
  the first entitled proof (§4) and lane 9 can only run on fixtures. Decision owed by the Chairman:
  lift the fence for lane 1 on those two files, or name the owner who registers the checks.
- **`SECTOR_GENERATION_CURSOR_SECRET`** must be provisioned for durable cursors; no owner yet.
- **Point-in-time constituent membership** does not exist in any producer. It blocks SI02's
  identity requirement (lane 1) and comparators C4 / C5 (lane 8).
- **Prophet eligibility** is not produced on any member row.

## 8. Status at 10:30Z (second adjudication pass)

Nothing in this section is merged, served or accepted unless it says so. No migration was applied.

### 8.1 Lane 1 — review response delivered, second review running

Macro #10929 is at `9c5db069856d` (draft, held). The range `5129620204c4..9c5db069856d` holds three
commits: `8c3fed6ffa34` (typed blocks, first industry map), `cd5f7e1afb9e` (producer-side industry
and removed-member carry) and `9c5db069856d` (the review fixes). The lane's own claims, not yet
independently confirmed:

- **Completeness.** The denominator is now the owner's configured current roster, read from the
  captured generation. On real committed bytes: 1,020 configured current members (1,046 less 26
  removed), 1,015 served, 5 accounted for without a row (`not_observed_at_effective_as_of`), 0
  unaccounted. `complete: true` therefore means "all 1,020 accounted for", not "1,020 served".
- **Stale or forged reference.** A well-formed token with an unrecognised signature now answers
  `409 CURSOR_RESET` for a page cursor and `404 ORIGINAL_UNAVAILABLE` for a context reference. A
  short or empty signing secret answers `503` on mint and on open.
- **Durability is stated on the wire.** `retained_resolver_ref_durability` reads `durable` only
  when the signing secret is configured, otherwise `process_lifetime_only`.
- **Industry.** `industry` (617 of 698, current GICS) and `sub_industry` (424 of 698) are separate
  fields. Neither is point-in-time.

Still open by the lane's own account: no cursor expiry, qualification is re-read per page, a cursor
chain crossing a qualification change is untested, and the committed `site/` files predate the new
writers, so a nightly proof is owed. A second independent review of the range (Opus, read-only)
started in this pass; its report will be `/tmp/si_plan/reviews/lane1_population_review_r2.md`.

### 8.2 Lane 6 — complete for the adjudicated scope

- Terminal #1410 is unchanged at `dc02f1c28879` (migration 0052, armed, clean).
- New Terminal **#1425** at `57d63a5e6d8f`, stacked on #1410: v3 readers, the durable identity, and
  a source-only migration **0053** taken from the allocator. Nothing applied; v3 writes stay closed.
  It is expected red on one PR-state test until #1410 merges.
- The durable reference is the generation id plus content id, plus the v3 member hash. Lane 1's
  `context_ref` is stored as a hint only.
- **Observation for the Chairman.** Production's `apply_investigation_revision_v2` body hashes to
  `a14a4abf290ca9dc99f89b19617c7e9c`. That is the 0029 body from the still-open Terminal #804
  (applied 2026-10-05), not master's 0028 body, and not either body that #1312's 0051 guard
  accepts. Reported only; no lane acted on it.
- Executed: SI10 on a real PostgreSQL 17 engine. SI09 is contract and fixture only. SI15, SP14 and
  SP15 were not executed.

### 8.3 Lane 3 — first live attempt

A real member sign-in succeeded with no second factor. The deployed Terminal route answered
`400 {"error":"invalid_source"}`: #1414 is not merged, so the deployed route table has no
`generation` source. This is deployment lag, not a refusal. #1414 is clean and armed at
`3004b74f48bc`; the v1.1 consumer work goes on a new stacked PR and the live attempt is repeated
after the deploy. Lane 3's v1.1 return was not yet written at 10:30Z.

### 8.4 Lane 8 — merge refused on a real regression

The merge controller refused macro #10924 at `3e6b51ef09fc`:
`tests/test_sector_metric_definitions.py::test_b04_doc_citations_resolve_to_lines_that_name_the_row`
fails on the PR. The fix is with lane 8 on the same PR. Lane 1's one-line `hazard_qualification`
carry waits on this merge.

### 8.5 Carriers

- Lane 5 failed at 09:37Z on a refused connection and lane 7 failed twice on a message-format
  error after a model-family switch. Both were resumed on their own threads; lane 7 is back on
  `glm-5.3`. No duplicate worker was started.
- Lane 9 (integrated proof) started at 10:30Z as one read-only child under the existing programme:
  phase A joins every SI and SP row to its evidence class and writes the live run-sheet. Phase B,
  the served checks, cannot run until #1414 is deployed and #10929 is served.

### 8.6 Open, with owners

The four items in §7.5 stand. Added: the production apply-body mismatch in §8.2 (Chairman / the
owner of Terminal #804 and #1312), and Terminal #1413 (lane 4), which the controller has marked
`merge-blocked` at `a8cf1f5d7250` for a cause not yet read.

## 9. Status at 10:55Z (integrated-proof census)

### 9.1 Nothing is served

Lane 9's phase A join is committed beside this file as `LANE9_EVIDENCE_JOIN_2026-11-10.md`. It is
that lane's output, spot-checked by the lane and not independently reviewed. It classes the 44
acceptance rows (SI01–SI20, SP01–SP24) by the best evidence that exists today:

| Class | Rows |
|---|---|
| Served on a deployed host | 0 |
| Real committed data through real code, not served | 7 |
| Real engine, fixture inputs | 6 |
| Fixture | 7 |
| Contract only | 10 |
| Not executed | 13 |
| No producer emits it | 1 |

A signed-in member sees none of this programme's work today. The ordered live checks for later
(phase B) are written at `/tmp/si_plan/v11/LANE9_PHASE_B_RUNSHEET.md` and have not been run.

### 9.2 Changes since section 8

- **Terminal #1414 merged** at `3004b74f48bc`: the first programme PR on a default branch. Its
  deploy is not observed. Lane 3 repeats the live attempt after the deploy; an upstream refusal is
  expected while #10929 is unserved.
- **Correction to §8.3.** Lane 3's partial v1.1 return was written at 10:26Z. Its v1.1 consumer is
  on the local branch `claude/ssd-si-lane3-v11-consumer-20261110` with no PR; the lane was told to
  publish it.
- **Macro #10924.** Lane 8 pushed the regression fix at `f1337bdd8738`. Checks are running and the
  controller has not yet cleared `merge-blocked`.
- **Terminal #1413.** The sweeper paused it at 09:45Z on a red typecheck at `3445b49a3cd1`. The
  PR-duty account then merged master into the branch (`a8cf1f5d7250`); those checks are running.
- **Macro #10931.** Another Chairman-assigned session (Macro PR healing duty, issue #10912,
  account `MastermindX1`) pushed `3290bfe75f96` at 08:27Z and recorded a HOLD. That commit edits
  `.github/ci/legacy-jobs.yml`, a file this programme's lanes are barred from editing. It is not
  this programme's act. Lane 5 was told to carry its v1.1 delta on a stacked branch. A routing note
  is at Macro issue #10912, comment 6765368384.

### 9.3 Ownership rulings

- The five forecast-head reason lines (EN and ZH) are lane 4's, in `sectorCycleLex.ts`. Lane 3
  mounts them.
- Lane 1's wire is the single location of the carried blocks
  (`projection.data.typed_blocks.<name>`). Lane 7 adapts its parser to it.
- `etf_flows`: lane 7 lists the fields its matrix needs that the carried value lacks. Until a
  producer emits them the component shows the unavailable state with the carried date.
- A context reference is not stored as durable until the signing secret is provisioned.
- Saved-investigation reopen, account switch during save, and a real Follow (SP14, SP15, SI15,
  SP17) are lane 6's second pass, on #1425, without APPLY.
- Correction lineage (SP18, part of SI18) is lane 1's, after the second review reports.
- Point-in-time membership has no owner. One read-only census child was started to establish what
  the repository's existing data can produce; it decides whether SI02's identity half, SP08 and
  comparators C4 / C5 are a producer change or need an outside source.
- Outside this programme: `prophet_eligibility` and the native-sector crosswalk (Prophet
  programme); the signing secret and any migration apply (Chairman); the ungated hazard callers in
  `scripts/build_cycle.py` and `engine/commodity_cycle_state.py` found by lane 8.

## 10. Status at 10:56Z (second review of lane 1)

### 10.1 Verdict: not ready

An independent read-only reviewer (Claude Opus 5.5 child) attacked `5129620204c4..9c5db069856d`
on Macro #10929. Both reports are committed beside this file:
`LANE1_POPULATION_REVIEW_R1_2026-11-10.md` and `LANE1_POPULATION_REVIEW_R2_2026-11-10.md`.

| Item | Round 2 verdict |
|---|---|
| F1 completeness | Partial. Two blockers remain |
| S1 token answers | Fixed |
| S2 durability on the wire | Fixed. "Durable" covers the signature only, not retention or a changed secret |
| S3 tests | Fixed for items (a) to (e). No test covers the two blockers |
| Carried blocks | Pass with notes. Size cap enforced; nothing readable anonymously |
| Industry fields | Pass. 617 / 698 and 424 / 698 reproduced, kept separate, current basis |
| Regressions | None. Every round 1 pass still passes |

The real numbers were reproduced: 1,020 configured current members, 1,015 served, 5 unserved with
a reason, 0 unaccounted, 26 removed. The reviewer ran the author's suites at the head (541 passed,
3 skipped), the neighbouring suites (283 passed) and four probes of its own.

In both blockers the real route answers `complete: true` while configured current members are
missing:

- **R2-B1** (`lib/sector_population.py:259-260`). A member the owner observed with a price at the
  as-of date, but with no served row, is labelled `empty_price_tape` and counted as explained. The
  producer cannot create that state (`engine/baskets.py:216,241-250`), so the label appears only
  when a row was lost after the owner's observation. With one real member dropped from the suite's
  own fixture the route answers served 1,014, unserved 6, unaccounted 0, complete true.
- **R2-B2.** The route never reads `observation_refusals` in the captured `baskets.json`. When the
  owner refuses a basket for low coverage (`engine/baskets.py:217-228`), that basket's whole
  configured roster leaves the denominator. Moving one real basket there gives 1,002 configured,
  complete true, with 18 members gone.

Not verified by the reviewer: the live host, a nightly run, the real web-server configuration, a
real central build with the carried blocks, and the nightly ordering of the screener and
confluence producers against the central builder.

### 10.2 Routing

- Both blockers went to lane 1 on its own thread at 10:53Z, with the required behaviour and a test
  for each: a lost row counts as `unaccounted_by_owner` and `complete` is false; a refused basket's
  members stay in the denominator under a new closed reason, and `complete` is null when the
  refusal list is missing or malformed. If lane 1 reads the producer differently it answers with
  evidence instead of applying the change.
- Sent with them: five notes (a temporary identity-lookup failure answers 401 and should answer
  503; `q` does not find unserved members; a date mismatch in `removed_members`; blocks carried
  with a null date; reads missing from `config/dag.yml`), the `etf_flows` windows question, and
  correction lineage (SP18).
- The author's return names commit `cd5f7e1afb9e`. The PR range holds `01c661b0e448` instead. The
  reviewer reviewed what is on the PR. Lane 1 was told to correct its return.
- A third review, limited to the two blockers and the notes, starts after lane 1 pushes. #10929
  stays draft and held at `9c5db069856d`.
- No consumer should rely on `complete` until that review passes. Lane 3 gets the new reason name
  when lane 1 fixes it in the wire document.

### 10.3 Corrections to this record

- Section 9's heading reads 10:55Z. It was committed at 10:49Z.
- The message to lane 1 is headed 11:05Z. It was sent at 10:53Z.

### 10.4 Unchanged since section 9

Macro #10923 is armed and open at `8abe28febaf0` with only the non-binding pilot check red; why it
has not merged is not yet read. Macro #10924 is open at `f1337bdd8738` and still carries
`merge-blocked`. The point-in-time membership census has not returned. Terminal #1414's deploy is
not observed.

## 11. Status at 11:45Z (Chairman's delegation, decisions, lane 1 fourth pass)

### 11.1 The delegation

Four open items went to the Chairman: what to do with #10929 and the CI registration fence, who
provisions the cursor secret, the production saved-investigation function that matches no merged
migration, and which model carries lane 1. He answered in this thread on 2026-11-10: "you decide,
we may need to just override it?" on the first, that he did not know what the second and third
were, "moves to GLM if GLM is able to do this task" on the fourth, and "Many decisions, u can make
for me". He also said the "Implement CI Lightning" session had traced failing PR checks to stale
checkouts and was fixing that.

The decisions below are the COO's, taken under that delegation. They are scoped to this programme.

### 11.2 Decisions

| # | Item | Decision | Reason |
|---|---|---|---|
| 1 | CI registration fence | Each programme PR carries the registration of the files it adds, in `.github/ci/legacy-jobs.yml` and `tests/test_ci_pack.py`. This supersedes the 08:05Z "stay fenced" note. | The 227 `contract-delta` findings on #10929 are introduced by the PR ("227 introduced, 0 inherited"). They are real registration debt, not a stale-checkout effect. The CI Lightning lead declined to deliver them and stated that ceiling re-bases are carried by the breaching PR. |
| 2 | #10929 release | The hold stays until the third review returns ready and `contract-delta` passes. The COO then releases it, as the hold's own release condition allows ("Sol (or the delegated COO)"), lifts the labels, marks it ready and arms `merge-on-green`. The controller merges. | Release on the merits only. No self-merge. |
| 3 | Cursor secret (`SECTOR_GENERATION_CURSOR_SECRET`) | Not provisioned by this programme. Not needed to merge or serve: without it the route works and labels every reference `process_lifetime_only`. It is needed before a saved investigation can reopen its original after a server restart. | A production secret is a real boundary. A one-line request goes to the Chairman or ops when #10929 is about to be served. |
| 4 | Production `apply_investigation_revision_v2` body | No action here. Any future apply re-reads the installed body first. | Lane 6's migration 0053 does not replace that function. The mismatch belongs to Terminal #804 and #1312, where lane 6 already reported it. No APPLY in this programme. |
| 5 | Lane 1 model | The Sonnet thread is retired. New lane 1 work goes to fresh GLM 5.3 workers with a written handoff. | Chairman's instruction. A fresh worker avoids the cross-family history fault seen on lane 7. The Opus review is the test of whether GLM is good enough. |
| 6 | Lane 6's request for an open-by-identity path | Denied. | The amendment says "add no arbitrary generation/path/domain reads". A stored signed `context_ref` is the only way to name a retained capture. |
| 7 | Sector Follow producer (SI15) | A later wave in a Macro lane, extending the existing B21 producer. Not started. | No Sector material-change producer exists. The gate `INVESTIGATION_V3_WRITES_OPEN` is false, so a saved preference claims no notification (SP17 holds). |

Limits on decision 1, as sent to the carriers: only findings the check lists as introduced by the
PR; no allowlist, exemption or skip entry; no assertion removed or loosened; ceilings re-based to
the measured value with the recorded comment; #10839 untouched and its refused command not
replayed; a hook or tool refusal ends the step and is reported, with no retry by another route.

The standing constraint "fenced CI-registration files untouched" is changed by decision 1 and by
nothing else. No APPLY, no second 0049, the Prophet Paper holds and no self-merge stand unchanged.

### 11.3 What was done

- The ruling is on #10929 (issuecomment-6766308701).
- Two GLM 5.3 carriers started at 11:40Z, one for #10929 at `595fe6b75af2` and one for #10924 at
  `f1337bdd8738`. Each owns only the registration files. Returns go to
  `/tmp/si_plan/returns/lane1_ci_registration.md` and `lane8_ci_registration.md`. Neither has
  returned. START, not DELIVERED.
- #10923: the merge had been stopped by lane 2's own comment "HOLD — merge custody: program COO",
  which the controller reads as a hold. Released by the named custodian with a `HOLD-RELEASED`
  comment (issuecomment-6765621595). Still armed at `8abe28febaf0`. Merge not yet observed.

### 11.4 Lane 1, fourth pass

Head `595fe6b75af2cd36ab447d4987e3c410abe4cca0`; review range `9c5db069856d..595fe6b75af2`.

- R2-B1 fixed: the `empty_price_tape` reason is deleted. A row lost after the owner's observation
  is `unaccounted_by_owner` and `complete` is false. Real-bytes test: 1,020 configured, 1,014
  served, 5 accounted, 1 unaccounted.
- R2-B2 fixed: refused baskets stay in the denominator under the new closed reason
  `group_refused_by_owner_observation`. A missing or malformed refusal list makes
  `configured_current` and `complete` null. Real-bytes test with housing refused: 1,020
  configured, 997 served, 23 accounted, 0 unaccounted.
- Notes N1, N2, N3, N4, N5, N7 and N8 fixed. N6 (the carried lane 7 blocks also sit in the static
  estate) is unchanged and is a tier decision outside this lane.
- `etf_flows` is now real: the committed producer `collectors.sponsors.sector_flow_periods()`
  gives five windows (1, 3, 5, 10 and 21 trading days) for 11 sector funds in USD millions.
- Correction lineage (SP18) stays `unavailable`. The publisher emits no duplicate on a
  same-context refresh (tested) but records no predecessor.
- Author's suites: 601 passed, 3 skipped. Sample sha256 `dbb09959…49d80`.
- Not tested: a cursor chain across a qualification change; the real
  `build_sector_central.main()` end to end.

These are the author's claims. A third independent review (Opus, narrow) is running and has not
returned. No consumer relies on `complete` until it does.

### 11.5 Other lanes

- Lane 6, second pass: Terminal #1425 at `fbc0925d98a9`. SP15 run on the PostgreSQL 17 harness
  (real engine). The reopen seam `terminal/lib/sectorInvestigationReopen.ts` is built and tested
  over captured bytes with a fixture transport. Follow census: production `alert_outbox` has 0
  rows and no Sector producer exists.
- Lane 5: partial. #10931 untouched at `3290bfe75f96`. The issuer-economics block is drafted,
  uncommitted, on a new stacked branch. All evidence is fixture.
- Lane 3: opened Terminal #1429 for the v1.1 consumer. Sent at 11:40Z: the wire changes above,
  the `etf_flows` pass-through, the reopen mount with `openByIdentity` unset, and the Follow state.
- Lane 7: told the real `etf_flows` shape and asked to overwrite its 9 November return.
- Lane 4: return still dated 9 November. One steer sent at 11:42Z for lane 3's five reason-code
  tuples and a current return.
- Lane 8: idle. #10924's registration is with the GLM carrier.
- Point-in-time membership census: not returned.

### 11.6 Rung reached

Nothing of v1.1 is merged or served. The integrated-proof count stays 0 of 44 rows. Terminal
#1414's deploy is not observed.

## 12. Status at 12:05Z (third review of lane 1: ready)

### 12.1 Verdict

The third independent review (Opus, separate context, read-only) returned `VERDICT: READY` for
#10929 at `595fe6b75af2`, range `9c5db069856d..595fe6b75af2`. The report is
`LANE1_POPULATION_REVIEW_R3_2026-11-10.md` beside this file.

| Item | Result |
|---|---|
| R2-B1 (default label for a lost row) | Fixed |
| R2-B2 (refused baskets left the denominator) | Fixed; every malformed refusals list tried gives null for the count and for `complete` |
| Preserved limits | Hold: 0 reader calls on every denial, `private, no-store` on every answer, largest page 112 KB |
| `etf_flows` carry | Acceptable: entitled-only, values as produced, local parquet only |
| Round-2 notes | N1, N2, N5, N7, N8 fixed; N4 partly fixed |
| Regressions | None found |
| Mutation check | Putting either blocker back fails two of the new tests each time |
| Suites (reviewer's run) | 602 passed, 3 skipped; central builder neighbours 279 passed |
| Fenced files and new parameters | Range touches neither CI file and adds no parameter that names a generation, path or domain |

Not verified by the review: the live host, the nightly build, CI, `build_sector_central.main()`
end to end, and the author's exact test selections.

### 12.2 Open findings and disposition

- R3-S1, should-fix. A basket the producer drops at `engine/baskets.py:233` is in neither the
  live list nor the refusals list, and the route answers `complete: true` with its members
  missing. The reviewer's probe through the real route gave `configured_current 1002, complete
  True` with all 18 housing members gone. Not reachable on current data: all 49 roster baskets
  are present.
- Eight notes: refusal text has no length limit (N1); `full_window` and `as_of` for ETF flows are
  taken across all funds (N2); window lengths are restated, not imported (N3); one malformed
  ETF-flow row drops every carried block (N4); the two industry blocks are outside the
  undated-block rule (N5); `group_index` has no `refused_by_owner` (N6); two owner states the
  producer cannot emit would read complete (N7); more than 500 unserved members answers 503 (N8).

Disposition: #10929 is released at the reviewed head, so the merged bytes are the reviewed bytes
plus registration-only commits. R3-S1 and notes N1, N3, N4, N5 and N6 go to a follow-up pull
request stacked on #10929, carried by a fresh GLM 5.3 worker started at 12:03Z (branch
`claude/si-lane1-r3-followup-20261110`; return `/tmp/si_plan/returns/lane1_r3_followup.md`). N2
and N8 are stated as limits in the wire document. N7 needs no change. The follow-up gets its own
review before it merges. Until it merges, no consumer renders `complete` as "all members"; lane 3
has that instruction. The same worker reports, read-only, how the Macro server receives its
production secrets.

The verdict and this disposition are on #10929 (issuecomment-6766826217).

### 12.3 Release state of #10929

Unchanged: draft, labels `hold`, `do-not-merge`, `merge-blocked`. One condition of two is met
(review ready). The other, `contract-delta` passing, waits on the registration carrier started
at 11:40Z, which has not returned.

### 12.4 Lane 5

The lane 5 session failed at 11:18Z on a provider error (502), its second failed run in a row.
Observed after the failure: the branch `claude/si-research-v11-issuer-econ-20261110` does not
exist on the remote, #10931 is unchanged at `3290bfe75f96`, and the drafted
`engine/market_ontology/issuer_economics.py` (17,621 bytes) is on disk, uncommitted, in that
session's worktree. Nothing was pushed, so there is no unknown effect to reconcile. A fresh GLM
5.3 worker started at 11:50Z with a written handoff: copy the draft, wire it into the query path,
run SP04, SP05 and SP12, and open one pull request stacked on #10931. It commits and pushes early.

### 12.5 Running at 12:05Z

Registration carriers for #10929 and #10924; the lane 1 follow-up worker; the lane 5 worker; the
point-in-time membership census; lanes 3, 4 and 7 on their own threads. Nothing of v1.1 is merged
or served.

## 13. Status at 12:30Z (point-in-time membership census; #10924 carrier resumed)

### 13.1 Census result

The read-only census is `PIT_MEMBERSHIP_CENSUS_2026-11-10.md` beside this file. It read
`origin/main` at `7e115b6f1f10`.

| Question | Answer |
|---|---|
| Basket and theme membership as known at a past date | Partly. `data/baskets/membership.json` holds effective dates only, and its `added` field is back-dated. First-known is recoverable from 2026-06-14 by commit, and from 2026-08-13 from the four stored snapshots in `membership_history.parquet`. |
| Sector, industry and sub-industry labels at a past date | No. Every surface is current-basis. `sp1500_pit_sectors` receipts `era_correct_count: 0` by design. |
| S&P index membership at a past date | Yes. `data/breadth/sp1500_pit_membership.parquet`: 500 from 1996, 400 from 2012, 600 from 2019. Floored starts are lower bounds. |
| Existing owner | `engine/basket_membership_pit.py`: append-only, keep-first store with `members_sha` and the `members_asof` reader, whose `pit=False` flag already models "not known at that date". |
| Not producible from this repository | Era-correct historical labels and taxonomy revision dates; historical add-announcement dates; mid- and small-cap membership before 2012 and 2019; basket first-known before 2026-06-14. |
| Survivorship | Partly. The ledger keeps all 26 removed members with dates. GATO and MAG have no price tape anywhere in the repository. |

Not verified by the census: 12 of the 26 removed members' tapes were not individually checked;
`data/baskets/extras.parquet` was not opened.

### 13.2 Decisions

1. **Lane 8 comparators C4 and C5 stay `unavailable: no_pit_constituent_membership`.** Index
   membership at a past date exists; the sector label at that date does not, and the comparators
   need the join. A small producer change cannot supply it. Lane 8 changes nothing.
2. **No outside data source is sought by this programme.** Era-correct labels need a licensed
   point-in-time classification dataset. That is a purchase, which is the Chairman's decision, and
   v1.1 does not need it: SP08 accepts "original or explicitly unretained", and the rows are
   emitted as `unavailable`. It is put to the Chairman as an optional item.
3. **What is producible gets carried, through the existing owner.** A lane 1 increment exposes,
   from `engine/basket_membership_pit.py` and nothing new: `membership_first_known` per member
   (earliest stored snapshot, labelled a lower bound, never the back-dated `added`); the stored
   member set and `members_sha` of the newest snapshot at or before the capture date; and a
   taxonomy stamp that states the current label basis with the historical revision `unavailable`.
   It starts after the round 3 follow-up returns, because both edit `lib/sector_population.py`.
4. **Survivorship is disclosed, not repaired.** Any analytics over baskets that had removals
   states that removed members' price histories are incomplete (GATO and MAG absent).

### 13.3 #10924 registration carrier

Failed at 12:20Z on a provider error (502) before editing anything. #10924 was unchanged at
`f1337bdd8738`. Its partial return had the diagnosis: 83 findings introduced, 0 inherited: 81
closure rows across 21 jobs (four new files) and two unwired suites; no packing ceiling breached.
Resumed on the same thread at 12:23Z. Second 502 from the local gateway in about an hour (lane 5
at 11:18Z).

### 13.4 Unchanged

#10929 draft and held at `595fe6b75af2`, review ready, registration not yet returned. #10923 armed
and open. Nothing of v1.1 is merged or served.

## 14. Status at 12:50Z (provider errors on five workers; all resumed)

### 14.1 What failed

| Worker | Started | Failed | Pushed before failing | Resumed |
|---|---|---|---|---|
| Lane 5, original thread | 02:00Z | 11:18Z (second failed run) | nothing new | retired; successor started 11:46Z |
| #10924 CI registration | 11:37Z | about 12:20Z | nothing | 12:23Z, same thread, by the COO |
| Lane 1 round 3 follow-up | 12:04Z | about 12:30Z | nothing | 12:35Z, same thread, by the COO |
| #10929 CI registration | 11:37Z | 12:34Z | nothing | 12:47Z, same thread, by the COO |
| Lane 5 successor | 11:46Z | 12:36Z | nothing | 12:39Z, same thread, by the Chairman (typed `resume` in the thread) |

Every failure carried the same text: `502 upstream transport failure; result may be ambiguous`,
naming the local inference gateway at `127.0.0.1:8313`. All five workers ran on GLM 5.3. Opus and
Sonnet runs in the same hours did not fail. The gateway's `/healthz` answered `{"ok":true}` when
probed after the 12:30Z failure. Four of the five failures fell between 12:20Z and 12:37Z. Cause: not established. The
timing fits one upstream interruption on the GLM route better than five separate faults.

### 14.2 What was observed before each resume

The error text says the result may be ambiguous, so each resume followed a read of the remote
and of the worker's files, not an assumption.

- Remote heads were unchanged: #10929 at `595fe6b75af2`, #10924 at `f1337bdd8738`. The branches
  `claude/si-research-v11-issuer-econ-20261110` (lane 5) and the lane 1 follow-up branch were
  not on the remote. No push, comment or label from a failed run was found.
- #10929 registration: its partial return holds the diagnosis at head `595fe6b75af2` against
  `origin/main` `e11afd6d8549`: 251 findings introduced, 0 inherited. 240 are closure rows
  across 33 jobs. 8 are new suites named by no run step. One packing probe is over its ceilings
  by one job (132 against 131) and by 8 weight-seconds (5,724 against 5,716). One suite skips
  because `healthcare-fda-supply` does not install `openpyxl`. No CI file had been edited.
- Lane 5: one local commit, `d0eb847ac359`, the 415-line draft module. Not pushed. No PR.

### 14.3 Decisions

1. A first failure is resumed on the same thread and the same model. The thread keeps what the
   worker had already read. A thread is never moved to another model family.
2. A worker that fails again after a resume is replaced by a fresh worker on another authorised
   model (Sonnet 5.5 or DeepSeek Flash 4.1), started from a written handoff.
3. No second lane 5 worker was started. The Chairman resumed the existing one at 12:39Z; a
   second would duplicate a started run.
4. Resumed workers were told to commit locally after each step and to update their return file
   with the commit, so a further error costs minutes, not the run.
5. `gemini-4-argon` remains unused.

### 14.4 State at 12:50Z

- #10923: open, armed, at `8abe28febaf0`. Hold released earlier by comment. Merge not observed.
- #10924: open, armed, `merge-blocked`, at `f1337bdd8738`. Registration carrier running; a
  path-addition script of its own appeared at 12:42Z.
- #10929: draft, held, at `595fe6b75af2`. Third review ready (section 12). Registration carrier
  running again. The hold stays until `contract-delta` passes (section 11.2, decision 2).
- Lane 1 follow-up and lane 5: running. Neither has pushed.
- Lane 3 (return of 12:11Z): the Terminal population fetch is in progress on its branch. It sets
  `audience=entitled` on the server side and never takes it from the caller. The deploy of
  #1414 is still not observed, so lane 9's phase B run-sheet has not been executed.
- Lanes 4 and 7: running. Lane 6: idle after its last return.

### 14.5 Rung reached

Unchanged. Nothing of v1.1 is merged or served. Integrated-proof count: 0 of 44 rows.

## 15. Status at 12:55Z (lane 7 return and rulings)

### 15.1 Lane 7 return

Terminal #1419 at `6f4f7844f4adc795af67e0c922577b9d5067d019`: open, not draft, not armed, behind
its base. Lane 7 reports its v1.1 delta as PARTIAL. Its own gates: 171 unit tests, `tsc` 0,
`eslint` 0, e2e desktop and mobile 26 passed. Not re-run by the COO and not independently
reviewed at this head.

- Flows: the Terminal reader now takes lane 1's carried `etf_flows` block as carried (labels
  1D/3D/1W/2W/1M, unit `usd_mn`, `full_window: false` marks a partial window, an absent window
  is no reading and never zero, a malformed block is unavailable).
- Bottoming Watch: the carried block matches the consumer field for field.
- Evidence label: the flows fixture is the committed producer's run over `data/flows`
  (2026-11-05, 11 funds). It is not a nightly run and not served bytes.

### 15.2 What the carried blocks do not yet give the Terminal

| Block | Carried today | What the consumer needs | Ruling |
|---|---|---|---|
| `confluence` | Per-universe id lists and coverage | Full per-universe payloads: scored group rows with members, entry and regime | Stays typed-unavailable. Queued as a lane 1 increment. |
| `theme_table` | A 49-key state dict with no names, links or series | A row array with `name`, `name_zh`, `href` and window measures for all 49 ids | Stays typed-unavailable. Same increment. |
| `etf_flows` funds | Tickers only | Optional display names | No change. Ticker is the identity. |

Neither block is sourced client-side and the Terminal reads no Macro file directly.

### 15.3 Decisions

1. Fourth universe: curated Baskets. The frozen packet fixes the order S&P, Nasdaq, Russell,
   Baskets (packet section 5.1; rows R3A-63 and R3A-64). The carried `china` lists are not
   mounted and no China tab is added.
2. Lane 1 increment queue, in order: the round 3 follow-up (running); point-in-time fields
   (section 13.2); full confluence payloads and theme rows (this section); the one-line
   `hazard_qualification` carry after #10924 merges. Each stays inside the existing owner
   route and the 4 MiB encoded bound, and each gets its own review.
3. Lane 7 next: emergence rendering to the bound R6-09 board, driven only by owner-carried
   fields, then the e2e tablet run. Strings that must live in lane 3's lex file go to lane 3
   as written hunks.
4. #1419 gets an independent review at the head lane 7 returns next. It is not armed before
   that.
5. Lane 3 was told the mount rules: `etf_flows` and `bottoming_watch` from the carried blocks
   behind an availability check; `confluence` and `theme_table` unavailable; and `complete:
   true` is not to be shown as "all members" (R3-S1).

### 15.4 Rung reached

Unchanged. Lane 7's delta is delivered to its PR. Nothing of v1.1 is merged or served.

## 16. Status at 13:35Z — returns, the main-baseline circuit breaker, two reviews started

### 16.1 What returned between 12:55Z and 13:35Z

| Lane | PR and exact head | State reported | Still owed |
|---|---|---|---|
| 7 | Terminal #1419 `6778c61594b9736f73f132fa4a6f4bcb30c2a9d1` | Emergence rendering complete. Unit 191 passed; e2e desktop and mobile 30 passed, 6 skipped; tablet 15 passed, 3 skipped. | No owner emits `emerging` yet, so every visible instance is a labelled harness mount. The board's second action has no destination route and is not rendered. The native-identity audit waits on lane 3's population mount. |
| 4 | Terminal #1431 `fb60cb3e0f8280875a7e38375b92f1fa7f4e12a3` | Master merged in (no rebase). Nine of its own files conflicted; none of lane 3's single-writer files. 14 files in the diff. 100 unit tests passed, `tsc` and `eslint` exit 0. #1413 is merged. | No live producer carries forecast heads; every state is a labelled fixture. |
| 8 (CI registration) | Macro #10924 `d70025383c2d` | One file changed (`.github/ci/legacy-jobs.yml`). The curated-closure guard test passed alone at this head (1 passed, 639 s). | The full local `contract-delta` and the full `tests/test_ci_pack.py` run had not finished. The shared host was at load 107. |
| 1 (CI registration) | Macro #10929 `07a9eafac6fb` | Pushed fast-forward from `595fe6b75af2`. Two files changed (`.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py`). | Final gates not finished. Two orders from 16.3 are outstanding. |
| 1 (round 3 follow-up) | Macro #10954 `e809e7ae7071` | R3-S1 fixed: the owner's roster is carried, and a missing roster basket makes its members `unserved` and `complete` false. Probe before `1002/997/5/0/True`, after `1020/997/5/18/False`. | Notes N1, N3, N4, N5, N6, the wire document and the full ten-file test run. |
| 5 (successor) | no PR yet | Implementation and tests green locally (10, 8 and 436 passed; 4 skipped). CI registration running. | Push and the stacked PR on `claude/si-research-v11-issuer-econ-20261110`. |

### 16.2 Why the armed PRs had not merged

The cause was outside this programme. The merge controller's log (run 42821456733) says
"source main baseline is red; leaving it armed behind the circuit breaker". The
`integration-baseline` workflow failed at main `e11afd6d8549`: one test,
`test_curated_exclusive_scopes_cover_their_own_import_closure`, on job `eval-os-a1`
(two `admin/capacity_*` files not in its path list). That sweep left 127 PRs
baseline-blocked. Another party merged the repair as #10951 (main `cbf9d99ac70d`). The
baseline run at that head (42822991031) was still in progress at 13:25Z. This programme
took no action on it. #10923 and #10945 stay armed and should merge once the baseline is
green.

### 16.3 Decisions

1. **Reviews of #1419 and #1431 started.** Each gets one independent Opus reviewer, read-only,
   at the exact head in 16.1. They run as threads in the Terminal project, because a child
   of this thread cannot be placed in another project (the orchestrator refused
   `target.projectId`, twice) and a Macro-pinned session cannot run git in the Terminal
   repo. Verdicts return as files: `/tmp/si_plan/reviews/lane7_1419_review.md` and
   `/tmp/si_plan/reviews/lane4_1431_review.md`. Neither PR is armed before its verdict.
2. **#10929 registration: path additions accepted, pack-limit change not accepted.** I read
   the diff from `595fe6b75af2` to `07a9eafac6fb`. It adds path lines, eight run steps and
   `openpyxl` to one install line. It removes nothing else. It also raises
   `PACKING_PROBE_MAX_PACKS` from 10 to 11. That limit is a guard on how many CI packs a
   common PR shape needs. The 11th pack comes only from 22 weight-seconds that six new steps
   add to `tier-gate`, a job every index and free-content PR selects. The worker was ordered
   to move those six steps into an existing job those probes do not select, and to restore
   the limit to 10. One attempt. If no existing job fits without new closure findings, the
   re-base stays and the return states the measured reason. No new job, no allowlist, no skip.
3. **#10929 registration must merge main first.** #10951 edited the same job (`eval-os-a1`)
   that this registration widens. `git merge-tree` shows both registration heads merge with
   main `cbf9d99ac70d` without conflict. The worker merges (never rebases) and re-measures
   on the merged tree.
4. **#10924 keeps `merge-blocked`** until the local `contract-delta` reports no introduced
   finding and `tests/test_ci_pack.py` passes at its head. The label then comes off with a
   visible comment that names this session and the reason.
5. **Release of #10929 is unchanged from 11.2**, and waits on decision 2 and 3 and the final
   gates.

### 16.4 Rung reached

Unchanged. Three more deltas are delivered to their PRs (#1419, #1431, #10954). Nothing of
v1.1 is merged or served. Integrated-proof count: 0 of 44 rows.

## 17. Status at 13:55Z — three more returns, `merge-blocked` removed from #10924, two more reviews

### 17.1 What returned between 13:35Z and 13:55Z

| Lane | PR and exact head | State reported | Still owed |
|---|---|---|---|
| 1 (round 3 follow-up) | Macro #10954 `0d43d893cc704fae94abbae9fe6dc319cf0f949f` | Complete. All six items closed (R3-S1, N1, N3, N4, N5, N6). Five owned files, +292/−19 against base `07a9eafac6fb`. Ten-file suite 610 passed, 3 skipped. Wire document updated. | Independent review (started, 17.3). It is stacked on #10929 and cannot merge before it. |
| 8 (CI registration) | Macro #10924 `f9cb2c6535eaa6306defda22011a35ac50b53fd4` | Complete. Two files. Local `contract-delta`: 0 introduced, 0 inherited (868 s). Probe test and closure guard each passed alone. Three probe weight ceilings re-based to measured values: 5,958→5,963, 5,979→5,998, 5,716→5,721. Pack ceiling unchanged at 10. | GitHub CI at this head (six ci-pack jobs running at 13:55Z). The full local `tests/test_ci_pack.py` run had not finished. |
| 3 | Terminal #1429 `93a760a7d935702d0b2d01e11c702b6577ab7fef` | Source-complete. Population reader and BFF `source=population` branch; lane 4, 6 and 7 heads merged in and mounted; master merged. `tsc` exit 0; 351 of 351 focused unit tests. | Independent review (started, 17.3). One lint error the author calls a false positive. The deployed site still runs the build before #1414, so the live step stays deferred. |
| 5 (successor) | Macro #10956 `60e7a019651c` | PR open, not draft, not armed. Cut from #10931's head, so its range to main includes #10931's commits. Its own two suites: 10 and 8 passed. CI registration for its own file pushed. | Its worker is still running. Review follows its return. It cannot merge before #10931, which another session holds. |

The lane 1 follow-up worker rebased its own unreviewed branch onto the moved base and pushed
with `--force-with-lease`. It reported this as a deviation. Accepted: its own branch, no
review had started, no other session's work was on it.

The lane 1 follow-up also answered what the "cursor secret" needs, read-only: the API loads
`/etc/macro-api.env` at service start (`app/deploy/macro-api.service:10`). One line,
`SECTOR_GENERATION_CURSOR_SECRET=<value of at least 32 bytes>`, then a service restart.
This programme does not create, print or set that value. It is one operator step, owed only
when #10929 is about to be served.

### 17.2 Main baseline

The baseline run at `cbf9d99ac70d` (42822991031) finished green. A newer run at
`0267bf8fffc0` was in progress at 13:55Z. #10923 and #10945 were still open and armed.

### 17.3 Decisions

1. **`merge-blocked` removed from #10924 at 13:56Z, with a visible comment**
   (issuecomment-6769164978). This amends 16.3 decision 4. The one condition not yet met was
   the full local `tests/test_ci_pack.py` run. GitHub CI runs the same suite at the same head,
   and the controller requires it green before it merges. Waiting for a second local copy of
   that result protected nothing and would have held the PR until the next wake. The label's
   original cause was fixed at `f1337bdd8738`. `merge-on-green` was not touched. I read the
   registration diff first: path additions, one run step, three measured ceiling re-bases, no
   allowlist, skip, selector or assertion change.
2. **#10924 merges before #10929, and that changes the #10929 suite move.** Both PRs edit the
   same three probe lines. After #10924 the free-content probe sits 2 weight-seconds under the
   11-pack line. #10924 also made `cycle-forward-log` selected by that probe, so it is not a
   home for lane 1's six suites. The rule sent to the #10929 worker: a suite whose import
   closure reaches the index or free-content files stays in `tier-gate`, because that weight is
   its true cost; a suite whose closure does not reach them moves to a job those probes do not
   select. If the total still crosses the line, 11 packs is the measured cost and is accepted
   with the reason recorded. The worker finishes against current main now. One short final
   pass follows after #10924 is in main.
3. **Review of #10954 started** (Opus, child of this thread, read-only, narrow: the five-file
   diff against R3-S1 and the five notes, plus exposure of the carried roster and the 4 MiB
   bound). Verdict file: `/tmp/si_plan/reviews/lane1_population_review_r4.md`.
4. **Review of #1429 started** (Opus, Terminal-project thread, read-only). Unit: lane 3's own
   three commits and the mounts. The BFF `source=population` branch is the first item: denied
   before read, forced audience, closed parameters, no caller-controlled upstream. Verdict
   file: `/tmp/si_plan/reviews/lane3_1429_review.md`.
5. **Terminal merge order.** #1429 contains the branches of #1419, #1425 and #1431. It is not
   armed until each of those is reviewed and merged, or their reviews are ready and it is the
   chosen carrier. That choice is made when the four verdicts are in.

### 17.4 Rung reached

Unchanged. Five deltas are delivered to PRs and under or awaiting review (#1419, #1431,
#1429, #10954, #10956). Nothing of v1.1 is merged or served. Integrated-proof count: 0 of 44.

## 18. Status at 14:05Z — two review verdicts, both NOT READY, fixes ordered

### 18.1 Verdicts

| PR | Head reviewed | Verdict | Findings |
|---|---|---|---|
| Terminal #1419 (lane 7) | `6778c61594b9` | NOT READY | 0 blockers, 5 should-fix, 8 notes |
| Terminal #1431 (lane 4) | `fb60cb3e0f82` | NOT READY | 2 blockers, 4 should-fix, 7 notes |

Verdict files: `/tmp/si_plan/reviews/lane7_1419_review.md`,
`/tmp/si_plan/reviews/lane4_1431_review.md`. Probe files sit beside them.

No finding is reachable on a served product path today. #1419's components are mounted only
on a dev page that returns 404 in production, and no producer emits forecast heads yet. Both
sets sit in code that lane 3's #1429 mounts, so they are fixed before merge.

The main defects, in plain terms:

- **#1419 S1.** The Baskets tab reads the wrong array on the real owner file, so 49 scored
  baskets would show as "no groups". The test fixture used an invented universe id.
- **#1419 S2.** A malformed calls-board or Watch payload crashes the page, and an absent total
  prints the word "undefined".
- **#1419 S3, S4.** The flows reader accepts wrong-typed values as a partial read, and does
  not check that a window label matches its trading-day count.
- **#1419 S5.** A few raw English strings and internal field names reach Chinese readers.
- **#1431 B1.** One odd reason-code string (`__proto__`) crashes the whole route.
- **#1431 B2.** First-known turn dates are keyed by date across all sectors, so one sector's
  date can appear on another sector's turn, including an unconfirmed one.
- **#1431 S1, S2.** The reader accepted a `withdrawn` status, a `withdrawn_asof` date and a
  `known_since` field. The producer emits none of the three.

### 18.2 Decisions

1. **Both lanes fix on their own branch and PR.** New commits only. Each reviewer probe that
   exposed a defect becomes a permanent test. Orders sent at 14:02Z to the lane 4 and lane 7
   threads.
2. **The producer is the contract for #1431.** The reader accepts only the status the
   producer emits at #10924's head (`withheld`). `withdrawn` and `qualified` read as an
   invalid head. Withdrawal shows through the reason code that `withdraw()` writes, with no
   date. A dated withdrawal waits for lane 8's `withdrawn_asof` increment. This also keeps a
   head from showing an implied pass, which the amendment forbids.
3. **First-known date field is `confirmed_at`.** That is the producer's name
   (`engine/sector_heads.py:50`, `engine/cycle_ontology.py`). `known_since` is removed.
4. **Emergence and row links accept only a same-site relative path.** Anything else renders
   with no link.
5. **Each fix gets a narrow second review at the new head.** Lane 3 then merges the new
   heads into #1429. The #1429 review in progress is on `93a760a7d935`; its findings in lane 4
   or lane 7 files route to those lanes, not to lane 3.

### 18.3 Other state at 14:00Z

- Macro #10924 at `f9cb2c6535ea`: armed, `merge-blocked` off, hosted contract-delta green at
  13:53Z, six CI packs still running. Full local `tests/test_ci_pack.py` finished:
  278 passed, 2 skipped.
- Macro #10923 and #10945: still open and armed. #10929: draft, held, worker running.
  #10954: review r4 running. #10956: lane 5 worker running.
- Terminal #1410: clean and armed, not merged. #1425: behind master, no review recorded yet.

### 18.4 Rung reached

Unchanged. Nothing of v1.1 is merged or served. Integrated-proof count: 0 of 44.

## 19. Status at 14:08Z — fourth review of lane 1 ready; next lane 1 increment started

### 19.1 Verdict on Macro #10954

READY WITH FOLLOW-UP at head `0d43d893cc70` (`/tmp/si_plan/reviews/lane1_population_review_r4.md`).
The reviewer reproduced both of the author's numbers on real bytes: with one basket missing
from both lists, the base answers `complete: true`; the head answers 18 unaccounted and
`complete: false`. R3-S1 and notes N1, N3, N4, N5 and N6 are closed. The carried roster never
appears in a response, is 7,405 bytes against a 60 KiB block cap, and adds no file read.
Serving guards are unchanged.

Six new notes, none a blocker or should-fix, none reachable on today's data:

| Note | In plain terms |
|---|---|
| R4-N1 | One malformed roster entry could drop all ten carried blocks. It fails closed. |
| R4-N2 | The roster date cut matches the owner's rule only for plain dates and the `ticker` key. |
| R4-N3 | The read side would serve an undated industry block as available. |
| R4-N4 | The roster's date is not compared with the capture's session date. |
| R4-N5 | The wire document overstates what the committed file reads before a nightly run. |
| R4-N6 | A NaN in a refusal raises the wrong error type. Route behaviour not probed. |

Not checked by the reviewer: CI, the live host, a nightly builder run.

### 19.2 Decisions

1. **#10954 is review-complete and stays at its reviewed head.** It is armed after #10929
   merges and #10954 retargets to main. The six notes do not go onto it; adding commits would
   move a reviewed head.
2. **The six notes go into the next lane 1 increment as its first part.** That increment
   edits the same two files, and its own review covers them.
3. **Next lane 1 increment started at 14:08Z** (glm-5.3, child of this thread, own worktree,
   new PR stacked on #10954): the R4 notes, then the point-in-time facts ruled in 13.2
   decision 3. Per member, a first-known date from the earliest stored snapshot, labelled a
   lower bound. Per group, the stored snapshot stamp and `members_sha`. One taxonomy stamp
   saying labels are current-basis and the historical revision is unavailable. Source is the
   existing `engine/basket_membership_pit.py` only. Nothing is read at request time, the
   block cap is not raised, and nothing new enters the legacy response or `typed_blocks`.
   Return file: `/tmp/si_plan/returns/lane1_pit_fields.md`.
4. **Lane 3 was sent the #10954 wire changes at 14:08Z**: `refused_by_owner` in
   `group_index`, nullable `configured_current` and `complete`, the `unaccounted_by_owner`
   reason, bounded refusal strings. Lane 3 had said its decoder refuses the new field until
   told. It was also told lane 4 and lane 7 heads will move.

### 19.3 Housekeeping

The reviewer left one of its own setup worktrees detached at `0d43d893cc70` with no file
changes. It is a finished child's worktree and is left to the storage helper's reclaim.

### 19.4 Rung reached

Unchanged. Nothing of v1.1 is merged or served. Integrated-proof count: 0 of 44.

## 20. Status at 14:23Z — lane 5 delivered, #1429 review NOT READY, two reviews started, push rule for this record

### 20.1 What returned

| Item | Result | Head |
|---|---|---|
| Lane 5, issuer-economics delta (Macro #10956) | Delivered. Stacked on #10931, which another session holds and which is unmerged, so #10956 cannot merge yet. Own diff after `3290bfe75f96`: 7 files, +1446/-1 (verified with `git diff --stat`). Author's tests: 10 passed, 8 passed, 436 passed / 4 skipped. | `95aa439d0a8a` |
| Lane 3, mounted surface (Terminal #1429), independent review | **NOT READY**: 2 blockers, 3 should-fix, 8 notes, reviewed at `93a760a7d935`. | lane 3 has since moved to `42ee6278c8c0` |
| Lane 1 CI registration pass (Macro #10929) | Pass complete; contract-delta "0 introduced, 0 inherited" at `c5d8c31db57d`. All six sector-generation suites stay in their current job (moving them measured worse). The full packing test result is still being written into the return. Final pass waits for #10924 to merge. | `c5d8c31db57d` (draft, held) |

The #1429 defects in plain terms:

- B1: after the user applies one filter, the group picker goes dead and cannot be changed or cleared.
- B2: pressing search again with the same text leaves the table on "Loading…" for good. This arrived in a commit the lane had described as type-only; that description was wrong.
- S2: the reader checks each field's type but not whether a page agrees with itself (for example "complete" together with a next-page cursor).
- S3: the server route passes the upstream refusal body to the browser as received.
- N7: a test fixture holds real signed cursor tokens and an actor digest.
- No route tests and no component tests exist for this surface.
- #1429 carries lane 6's branch at an older head (`fbc0925d98a9`) than lane 6's current head (`0fd16f5bc4e0`).

### 20.2 Decisions

1. Lane 3 fixes B1, B2, S2, S3 and notes N2, N4, N5, N6, N7 as new commits; N1 is accepted as designed but pinned by route tests; N3 and N8 are recorded as known limits. The reviewer's probe tests become permanent tests. Lane 3 merges lane 6's current head now. A narrow second review of `93a760a7d935` → new head follows. Order sent 14:21Z.
2. Lane 5 gets an independent review limited to its own four commits (started 14:21Z, verdict to `/tmp/si_plan/reviews/lane5_10956_review.md`). #10931 is not reviewed, not pushed to and not armed by this programme. #10956 is not armed until #10931 has merged and the review is READY.
3. Lane 6 (#1425) had no independent review on record. One started 14:21Z (verdict to `/tmp/si_plan/reviews/lane6_1425_review.md`). It re-runs the migration-prefix census, checks the migration against the installed production state recorded by lane 6, and may write only to a disposable local database. No APPLY.
4. Terminal landing order is unchanged: #1425, #1419, #1431, then master merged into #1429, then #1429. None is armed before its review reads READY.

### 20.3 Push rule for this status record

Every push to this branch cancels the CI run in progress for the previous head (runs 42829286555 and 42830350986 were cancelled this way), which is why #10945 has not merged. At 14:23Z run 42831237204 is in progress on `3a5a6b422d57`.

Arrangement from 14:25Z: the first status branch (`claude/si-v11-adoption-status-20261110`, #10945) stays at `3a5a6b422d57` and receives no further pushes, so its CI run can finish and the controller can merge it. Section 20 and every later section go on a second branch, `claude/si-v11-adoption-status-b-20261110`, stacked on the first, with its own pull request. That pull request is not armed while #10945 is open, because merging it would move #10945's head and cancel its run again. Once #10945 has merged, the second branch merges main, its pull request is pointed at main, and it is armed.

### 20.4 Observed pull request state, 14:22Z

Macro: #10923 open, armed; #10924 open, armed, `f9cb2c6535ea`; #10945 open, armed, `3a5a6b422d57`; #10929 draft, held, `c5d8c31db57d`; #10954 open, reviewed, not armed, `0d43d893cc70`; #10956 open, not armed, `95aa439d0a8a`.
Terminal: #1410 open, armed, clean, `dc02f1c28879`; #1419 `6778c61594b9`; #1425 `0fd16f5bc4e0`; #1429 `42ee6278c8c0`; #1431 `fb60cb3e0f82`. None merged.

### 20.5 Rung

Unchanged. Nothing of v1.1 is merged or served. Integrated proof: 0 of 44.

## 21. Status at 14:30Z — lane 4 repair returned, second review started; #10929 registration pass fully measured

### 21.1 What returned

| Item | Result | Head |
|---|---|---|
| Lane 4, cycle forecast heads (Terminal #1431), repair of the NOT READY verdict | Author reports all 2 blockers, 4 should-fix and 7 notes repaired on the same branch: one fix commit `cbe8175e7` plus a merge of master. Author's gates: 112 tests passed in 11 files; type check clean; lint clean on the 14 changed files; browser test 14 passed, 6 skipped by design. | `4449e5873e3f` (was `fb60cb3e0f82`) |
| Lane 1 CI registration pass (Macro #10929) | The one open gate from section 20 is now filled: full packing test "278 passed, 2 skipped in 1151.20s", exit 0. With the contract check at "0 introduced, 0 inherited" and the nine wired suites green, this pass is complete. | `c5d8c31db57d` (draft, held) |

What lane 4 changed, in plain terms: an unknown or hostile reason code now shows the generic line instead of crashing the panel; first-known dates are tied to the sector, the date and the kind of turn, so one sector's date can no longer appear on another; a forecast head is only ever "withheld", and a head claiming "withdrawn" or "qualified" reads as invalid; the first-known field is `confirmed_at`; one bad head no longer hides the other three.

### 21.2 Decisions

1. A narrow second review of #1431 (`fb60cb3e0f82` → `4449e5873e3f`) started 14:28Z. It re-runs every probe of the first review and tries to break each repair. Verdict to `/tmp/si_plan/reviews/lane4_1431_review_r2.md`.
2. Lane 3 was told at 14:28Z to merge lane 4's new head together with lane 6's current head, and what changed for it as the consumer.
3. #10929 stays a held draft. Its final pass (merge main after #10924 lands, keep main's three probe values, add only the measured excess) is still owed before release.

### 21.3 Status record branches

This record now lives on two branches. #10945 (first branch) is frozen at `3a5a6b422d57` and waits on its CI run. #10959 (second branch, stacked on the first) carries sections 20 onward, is not armed, and carries a HOLD comment with its release condition (#10945 merged).

### 21.4 Rung

Unchanged. Nothing of v1.1 is merged or served. Integrated proof: 0 of 44.
