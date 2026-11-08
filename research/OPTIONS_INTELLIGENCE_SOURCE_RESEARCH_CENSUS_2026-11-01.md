# Options Intelligence: source-truth and research-qualification census, 2026-11-01

Records only. This census is not a signal, a ranking, a sizing input or a trade
instruction. It activates no producer, flag, daemon or release, and it releases
no hold.

## Scope and method

- **Producer.** ORCH-1, the Opus sub-orchestrator under the Options Intelligence
  CEO seat (root `a1c77f0e-56b9-4edf-8d4f-3d31a338a8ed`).
- **Rows.** The source-truth and research-qualification half of the acceptance
  matrix: AC07, AC08, AC12-AC25, AC28-AC36, AC57 and AC58, 27 rows in all.
  - The product and integration rows (AC37-AC56 and AC60) belong to the sibling
    orchestrator and are not covered here.
- **Baseline.** Every repository citation is at origin/main
  `021af584204c9fb00ad516c2dbc9467503a84083` unless a PR head is named.
- **PR state.** PR facts come from one GraphQL read at 2026-11-01T08:20:51Z. No
  PR head was checked out.
- **Labour.** Census labour ran on Mastermind Subagent Fabric lanes; see the lane
  table. ORCH-1 opened each cited primary line itself before writing a
  disposition. A worker report was treated as a pointer only.
- **Claim classes.** OBSERVED means read from a named path or command.
  CALCULATED means the arithmetic is stated. INTERPRETED is labelled as such.
- **Reading rules.** `null` means not observed, never zero. A read failure is not
  empty, and stale is not live.

Each row has exactly one disposition:

| Disposition | Meaning |
| --- | --- |
| `DO_NOT_REDO_ACCEPTED` | Accepted work, with evidence. |
| `OWNER_HELD` | A named owner or hold reference controls the next act. |
| `ACTIONABLE_NOW` | A bounded act this seat may take now. |
| `GATED` | A named gate blocks the row, with a reachable resolution. |

## Disposition table

| Row | Capability | Disposition | Evidence opened (at baseline unless stated) | Gate / owner / next act |
| --- | --- | --- | --- | --- |
| AC07 | Failed read vs quiet board | DO_NOT_REDO_ACCEPTED | `scripts/build_intraday_flow.py:1396` (read_failed distinct from no_data); #10003 merged as `8f6bca2ad1c22ca9491c274d190c37bd0b52bf1c`; focused test `tests/test_intraday_flow.py:1097` | None. The #10003 production-proof watcher belongs to the incumbent session and is not touched. |
| AC08 | Population manifest v0 | DO_NOT_REDO_ACCEPTED | `engine/options_capability_manifest.py:34,37`; OPT-011 #10248 merged as `fa06210782d5a34e19fc527e829baf6e85042fc0` (PRODUCTION_PROOF per the commission) | None. Neither a second manifest nor a widened v0 family exists on main. |
| AC12 | Qualified premium | GATED | `research/options_estate/options_alpha_candidate_formation_policy_v2.json:5` (`preregistered_inactive_until_activation`), `:17`, `:20-25` (four activation preconditions); `research/options_intelligence/2026-10-03/SOURCE_ADMISSION_REVIEW.md:24` | Validated contract units plus positive qualified coverage are absent. Gate: the policy-v2 activation preconditions and the AC21 activation receipt. Owner: OA-1C. |
| AC13 | Latency diagnosis | OWNER_HELD | #10201 OPEN draft, head `87035e8928`, no labels; hold record: the #10201 PR body ("DRAFT / release hold" paragraph) | Holder: writer/root `01a10340-ddc1-7e41-9b42-9c8543c28c3d`, under its META-CEO commission. Release act: the holder's own. See the L4 section. |
| AC14 | Coverage expansion | OWNER_HELD | #8191 head `6753d5622555e110a107bd4fd706f478f73b1d24`: `research/options_estate/COVERAGE_EXPANSION_R1_2026-09-29.md:131,135` | Owner: coo-fable (#8191 hold). The 1000/1500 coverage ambition is not reported as actual coverage. |
| AC15 | Measured washout | OWNER_HELD | #6867 (sol/* DRAFT/HOLD) head `1ba8321db28c7ff8458ac2931bd5bcf9bde66809`; main `templates/intraday_flow.html.j2:699-707,729`; `git grep` for the repaired consumer at baseline returns 0 matches | Owner: the #6867 Sol lane. A hold is a merge barrier; read only. |
| AC16 | Known trap | OWNER_HELD | Same #6867 head; `templates/intraday_flow.html.j2:653,660` | Same owner and hold as AC15. |
| AC17 | Timing state | OWNER_HELD | Same #6867 head (repair prepared and held) | Same owner and hold as AC15. |
| AC18 | Three-plane transport | GATED | `research/options_estate/OPTIONS_SUPERSESSION_REGISTER_2026-10.md:132`; `agentos/workstreams/WS-INTRADAY-FLOW-P0-RECOVERY.md:78-80` | The remainder is not globally accepted. One healthy plane does not close all three. Gate: an intraday PR4 per-plane receipt (board, quotes pulse, canonical flow source, desktop and narrow dossier). Owner: WS-INTRADAY-FLOW-P0-RECOVERY. |
| AC19 | Session boundaries | OWNER_HELD | Same #6867 head (partial repair) | Same owner and hold as AC15. Gap: no test of the holiday half-day case was found. |
| AC20 | Campaign integrity | GATED | `agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:316-317` (campaign integrity unearned); `ls-tree data/options_signal_campaign/` holds only `campaigns.jsonl`, `checkpoint.json` and `outcomes.jsonl`, with no correction receipt; #9677 OPEN draft, head `65a230d376` | Gate: #9677 lands and the daily owner binds its canonical correction receipt. Tape proof does not substitute for that receipt. Resolution: the seat assigns the #9677 receiver (another session's PR; not touched here). |
| AC21 | Candidate activation | GATED | `options_alpha_candidate_formation_policy_v2.json:15-25` (activation rule, `permanent_abstain` before policy and before activation, the late-arrival rule, four preconditions); WS `:104-106` (publisher inactive until an activation receipt exists) | Gate: the four preconditions clear, then an accepted activation receipt exists. A pre-activation event can never become a candidate (`:18`). |
| AC22 | Frozen exact expression | GATED | `docs/runbooks/OPTIONS_OA3_RETAINED_EVALUATION.md:46-53` (remaining real-path gate); policy v2 `:45` (`first_qualifying_revision_frozen: true`) and `:49` (identity derivation); #9682 OPEN, labels `merge-on-green` and `merge-blocked`, head `9c7aa19c6a` | Gate: #9682 lands under its own `merge-blocked` condition, plus an accepted active expression-selection contract and a durable OA-3 activation receipt. Owner: OA-1C and #9682. |
| AC23 | Exact NBBO entry/exit | DO_NOT_REDO_ACCEPTED | `engine/options_alpha_exact_option_outcome.py:32-34` (no reuse of the 600-second rule), `:68-69` (60 s entry and exit windows), `:113` (`entry_quote.event_at+PT60M`), `:141-143` (retrieval-after-maturity allowed, actual availability recorded, live-lag rule not inherited); #9663 `1850484b64d0` and #8318 `1df2cc9f692a` are both ancestors of the baseline | The evaluator contract is merged. Real-path outcomes stay gated under AC21, AC22 and AC24; this row does not claim any outcome. |
| AC24 | Outcome attrition | GATED | COUNT-ONLY receipt `research/receipts/options_intelligence/outcome_attrition_20261101.json` (this PR); see the L5 section | The flow-signal ledger stage is counted. The OA-3 and candidate stages are unobserved. Gate: a retained OA-3 outcome table requires AC22 and AC21. |
| AC25 | Calibration authority | OWNER_HELD | WS `:319-322` (Draft #8385 at `0234ea19` UNRATIFIED/REVISE; the 20/200 and block-monotonicity choices are unratified; the required Opus review is unavailable; "No calibration law is invented") | Owner: OA-2 / FS-5 ratification. The handoff quote at `6c543006` is off-lineage (not an ancestor of the baseline); the on-main mirror is the WS file. |
| AC28 | Causal population and history | GATED | Sealed in DRAFT #10390, §8 (S0 family binding) | See the L3 section. Gate: independent review of #10390, then G0-G6. |
| AC29 | Stage-specific power and test seal | GATED | #10390 §9 | As AC28. |
| AC30 | P1 exact interval range label | GATED | #10390 §2 | As AC28. |
| AC31 | P2 signed-flow residual target | GATED | #10390 §3 | As AC28. |
| AC32 | P3 H20 variance | GATED | #10390 §4 | As AC28. |
| AC33 | P4 borrow-adjusted IV spread | GATED | #10390 §5 | As AC28. |
| AC34 | P5 ETF fixed-inventory hedge-notional study | GATED | #10390 §6 | As AC28. Assumed exposure is never relabelled as actual dealer holdings (AC36 stays held). |
| AC35 | P6 relative spread and actual fill cost | GATED | #10390 §7 | As AC28, plus G5 (read authorization for existing order, fill and fee records). No actual fill evidence was added. |
| AC36 | Dealer predictive claims | OWNER_HELD | `research/options_estate/SPX_SOURCE_ADMISSION_2026-10-09.md:25-28` (#8555 `HOLD-FOR-SOL / DO NOT MERGE`, draft head `82bc91ba18`; MAS-260 #7328 head `9515f2558a`, label `hold`); `:205-211` (MAS-260 calibration null preserved; `can_publish` and `r2_published` false; no fitting, probabilities or ranking) | Owner: Sol (#8555) and the #7328 hold. The P5 study in the falsifier is the #10390 P5 pilot (AC34), which cannot promote a dealer forecast. |
| AC57 | Exact NDX/NDXP root family | OWNER_HELD | `docs/ACTIVE_BUILD_MAP.md:92` (#10157, branch `sol/ndxp-family-20261024`, no merge marker); `engine/index_options_family.py` absent at baseline; #10157 OPEN, head `09682d5fe3`, body section "Release and data gates (hold)" | Owner: the #10157 Sol lane (a sol/* branch; read only). The worker proposed GATED; ORCH-1 reclassified because the only progressing act is protected-owner custody. "No silent Index/ETF alias" is certified for main only. |
| AC58 | Source-use rights | DO_NOT_REDO_ACCEPTED | `research/options_estate/OPTIONS_INTELLIGENCE_INTEGRATION_AMENDMENT_2026-09-16/OPTIONS_INTELLIGENCE_INTEGRATION_AMENDMENT.md:451-458` (Q1 rights table; old blanket blocker retired); `docs/OPTIONS_PLAN_PRIVATE_CONSUMER_2026-10-24.md:62-63` (named-provider rights by Chairman attestation, "not a new licensing gate"), `:73-76` (no export of paid contract rows) | None. The blanket licence block is not revived, and private rights are not expanded to export. |

**Counts (CALCULATED):**

| Disposition | Rows | Which rows |
| --- | --- | --- |
| DO_NOT_REDO_ACCEPTED | 4 | AC07, AC08, AC23, AC58 |
| OWNER_HELD | 9 | AC13, AC14, AC15, AC16, AC17, AC19, AC25, AC36, AC57 |
| GATED | 14 | AC12, AC18, AC20, AC21, AC22, AC24, AC28-AC35 |
| ACTIONABLE_NOW | 0 | The bounded acts available here (L2, L5, L3 seal) were executed in this PR and in #10390. |
| **Total** | **27** | 4 + 9 + 14 = 27 |

## L2: ThetaData chain and terms coverage (D107 GAP 1-2)

Receipt `research/receipts/options_intelligence/theta_chain_terms_coverage_20261101.json`
(sha256 `3c27e53553d4733fafaa6b807ba4b7deb9a74ae29f31651cf1a25e82308b9315`,
26,660 B), with its README alongside it. The block as received from the lane
hashed to `ea879b7d…cce015f` (24,245 B); the committed file is that block plus
ORCH-1 annotation keys, named in the README.

- **Path.** The existing ThetaData path only. No new provider, no paid call, and
  no QQQ request. The strike counts came from the local Terminal endpoint
  `list/strikes`, which `collectors/thetadata.py` does not call at the baseline
  (its only `list/*` calls are `list/symbols` at `:279` and `list/expirations`
  at `:296`). It is the same local Terminal.
- **Cohort.** 26 roots, taken from the `root_catalog` core tier of the D107
  `/api/flow/meta` capture, minus QQQ. The cohort is led by SPY. The capture is
  committed byte-exact as
  `research/receipts/options_intelligence/flow_meta_20261101T043626Z.json`
  (sha256 `c03eab46584b0c5ddd9efee32834b61c2423bd1952002dfe536164e0d77dd9db`,
  193,559 B).
- **Expiry selection.** Store chain as-of 2026-10-29 for every root (the newest
  date the store holds). Terminal strikes use, per root, the first listed
  expiration on or after 2026-11-01: 2026-11-02 for 12 roots, 2026-11-04 for
  AAPL, 2026-11-06 for 12 roots, and 2026-11-20 for XLRE. The dates are
  OBSERVED in the request URLs; that each is the first listed one rests on the
  lane report, since the expirations bodies were not retained.
- **Result (OBSERVED).** 26 of 26 roots observed. None is empty, unobserved or
  read-failed. `unavailable_roots` is empty, and no reason was manufactured.
- **Contract terms.**
  - The multiplier and the standard-deliverable filter are policy constants.
  - Exercise style and settlement are not carried on the Theta path.
- **Chain as-of.** 2026-10-29, two sessions stale.
- **Transport integrity.** The lane declared a different sha than the received
  block's sha, and this is unreconciled; see the README. The block was accepted
  on content: every citation was re-checked at the baseline.

## L5: AC24 outcome attrition (COUNT-ONLY)

Receipt `research/receipts/options_intelligence/outcome_attrition_20261101.json`.

- **Flow-signal snapshot (HISTORICAL_COMMITTED, as-of 2026-10-18), CALCULATED.**
  103,893 attempted = 85,603 graded ok + 18,225 not yet matured + 65 with no
  price data. This is the cumulative identity.
- **Per-run gate counts.** The gate's grader block (0 ok, 18,225 not matured,
  65 errors) is labelled per-run in the receipt. `gate.json` has no run id, so
  the run is identified by the commit that wrote it, `6ef6fe67976b`
  (2026-10-18T07:09:10Z).
- **Horizons.** Graded rows split 51,838 at h5 only and 33,765 at h21 only. The
  h63 and h126 outcome columns are null on every row: unobserved, not zero.
- **OA-3 exact-option stage: GAP.** No retained OA-3 outcome table is committed.
- **Candidate stage: GAP.** The candidate feed is stored in R2 only and is
  inactive.
- **What was read.** No outcome value, return, score, hit rate or calibration
  value was read into the receipt.

## L4: #10201 latency (AC13): OWNER_HELD

- **Holder.** Writer/root `01a10340-ddc1-7e41-9b42-9c8543c28c3d`, under its
  META-CEO commission. #10201 is an OPEN draft by `mastermindxryan`, head
  `87035e8928`, created 2026-10-30T14:14:31Z.
- **Durable record of the hold (OBSERVED).** The #10201 PR body, read
  2026-11-01T09:44:40Z. Its "DRAFT / release hold" paragraph says the current
  META-CEO commission permits draft source delivery only. It forbids merge,
  approval, auto-merge arming and deploy, and keeps the original runtime and
  release holds.
  - The PR carries no labels, so the body is the only record cited.
  - `docs/ACTIVE_BUILD_MAP.md:75` lists #10201 as DRAFT. That corroborates the
    draft state only, not the hold.
  - No other durable hold record was found, and none is invented here. Memory
    notes are not records and are not cited.
- **Release act.** The holder's own: its commission is widened beyond draft
  source delivery, and the widening is recorded on #10201. ORCH-1 holds no
  such act.
- **Still missing after release.** An installed-source receipt and natural phase
  timings. The 1261-second figure is not labelled network-only, and it is not
  reported as already improved. In order, after the holder's release: #10201
  merges; the source is installed on the M1 Studio; one natural weekday run
  completes; a read-only phase-timing receipt is taken.
- **Not done.** No comment and no push was made to #10201.

## L3: P1-P6 family preregistration (AC28-AC35): sealed, review pending

| Item | Value |
| --- | --- |
| PR | DRAFT #10390, branch `claude/oi-orch1-prereg`. It is cited by document sha256 and seal commit, not by PR head. |
| Document | `research/options_intelligence/2026-11-01/OIF_P1_P6_FAMILY_PREREG_V1.md`, document_sha256 `aea58e59bf9d2af190a603640a7039c35bed5dcb842fc6ec6e77cb0b613fb0cd` |
| Seal | `OIF_P1_P6_FAMILY_PREREG_V1.seal.json`, sha256 `f68d28089e5e8aba79f4f219db57b4b0690259bb2dc95d0c379a4e08c851812d`, at seal commit `2a97665844be80c8a52a829c26dfb9511b139c0f` |
| Inputs addendum | `OIF_P1_P6_FAMILY_PREREG_V1.inputs_addendum.md`, sha256 `0f1f75cf1f47bbe32884e9c8c3cd994b78643f0c61dc058655217246683c9820`. It is a disclosure only and changes no part of the plan. Cite the seal together with the audit file and this addendum. |
| Status | S0 family binding only. It is not an accepted G3 preregistration of dates and grants no fitting or evaluation authority. |

**Open gates.** Gates G0-G6 (prereg §11.3, copied from R21 §9) remain open, so
all empirical work is GATED.

**Blindness audit and review.** These live in the prereg PR's audit file
(`OIF_P1_P6_FAMILY_PREREG_V1.audit.md`):
- **Lane log audit.** No out-of-packet read was observed. The retained log is
  transport-only, so the audit is limited.
- **Pre-seal reads by ORCH-1.** ORCH-1 discloses one read made before the seal,
  of schema and row counts only, from a separate producer.
- **Independent review.** WAITING_CAPACITY:
  - Three review lanes were refused at admission on ubuntu1 before they
    started. The last refusal record (`ext/lanes/oi1-l3r-r3.remote.stdout`,
    written 2026-11-01T09:20Z) names `host_temperature_at_or_above_limit`.
  - The router placed the next review on ubuntu1/glm-5.3. The cached ubuntu1
    telemetry (`ext/state/hosts/ubuntu1.json`) read tctl 78.0 °C at
    2026-11-01T09:16:32Z, at or above the admission limit then.
  - A later reading of the same file, at 2026-11-01T10:03:30Z, shows tctl
    70.0 °C and risk NORMAL. The thermal block is therefore dated, not
    standing. No review lane was launched after that reading.

## Fabric lane table (ORCH-1)

All lanes ran under parent `oi-a1c77f0e-orch1` and root `a1c77f0e-…a8ed`, and
all requested `C1_ROUTINE_BOUNDED`. "Refused" means admission refused (rc 75)
before start: the id is burned and nothing was retried under it.

| Lane | Class | Placement | Final | Result sha256 (prefix) | Parent verdict |
| --- | --- | --- | --- | --- | --- |
| oi1-l1a-r1 | census | ubuntu1 / minimax | refused (`remote_admission_refused`) | none | n/a |
| oi1-l1a-r2 | census | ubuntu1 / MiniMax-M3 | DONE rc 0 | `1f156746dbd2971c` | ACCEPTED (artifact opened; citations re-read) |
| oi1-l1b-r1 | census | ubuntu1 / minimax | refused | none | n/a |
| oi1-l1b-r2 | census | ubuntu1 / minimax | refused | none | n/a |
| oi1-l1b-r3 | census | m1 / minimax | refused (`ADMISSION_WAIT_EXHAUSTED`, m1 lane limit) | none | n/a |
| oi1-l1b-r4 | census | m1 / MiniMax-M3 | DONE rc 0 | `07fac2a47bb81b1e` | ACCEPTED; AC57 reclassified GATED to OWNER_HELD |
| oi1-l2-r1 | census | m1 / MiniMax-M3 | DONE rc 0 | `ec6146780ad7146a` | ACCEPTED on content; transport sha unreconciled |
| oi1-l3a-r1 | fix_build | m1 / MiniMax-M3 | DONE rc 0 | `250c4968b61fed6e` | ACCEPTED as the draft that was sealed; independent review pending |
| oi1-l3r-r1 | review | ubuntu1 / grok-4.7 | refused (not started) | none | n/a |
| oi1-l3r-r2 | review | ubuntu1 / glm-5.3 | refused (not started) | none | n/a |
| oi1-l3r-r3 | review | ubuntu1 / glm-frontier | refused (`host_temperature_at_or_above_limit`, not started) | none | n/a |

## Carried gaps

1. The AC25 handoff quote is off-lineage (`6c543006` is not an ancestor of
   main). The WS mirror is used instead.
2. PR branch contents beyond #8191 and #6867 were not read. The other PR facts
   come from the 08:20Z state read.
3. AC57 alias safety is certified for main only. `mastermind-terminal#1180` (a
   different repository) was not read.
4. AC36 external pointers W04 and W10 were not fetched.
5. AC20: it is not specified anywhere read whether the canonical correction
   receipt is a committed file or a runtime artifact.
6. AC19: no test of the holiday half-day case was found.
7. L2: the chain as-of is two sessions stale, and the transport sha is
   unreconciled.
8. L5: the OA-3 and candidate stages are unobserved.
