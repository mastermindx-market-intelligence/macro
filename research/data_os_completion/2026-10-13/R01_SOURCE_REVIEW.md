# R01 — exact-source review of the merged Data OS wave-1/2 commits (programme DATA-OS-COMPLETION)

## Scope

Independent read-only source review of the 21 squash commits that landed on `main` for
DATA-OS-COMPLETION (waves 1–2 plus the two wave-3 commits named by the commission).
Evidence class per row is stated; no CI or PR-state fact is claimed — every such check is
`ORCHESTRATOR-FILLED`.

- Main under review (start commit): `15bc4a7b392f152518c9fb8b822bd336ddc108b5`
- All 21 subject commits resolved to full SHAs and proven ancestors of HEAD (`git merge-base --is-ancestor`).
- Blob pins at HEAD (all four matched the commission exactly):
  - `lib/dataos/read_contract.py` = `460fc9403c28eefc771710cbd5b2ecd43bedfdd5`
  - `lib/dataos/price_views.py` = `9ceb782f6426bc8d701341f433d0d0eb7e8dedb8`
  - `lib/dataos/registry.py` = `65b0d69036da97760f20241468f2549b21d9c686`
  - `research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md` = `784b6c259815ccdc1324bd7345499699d3c6122c`
- Method: per-commit `git show --stat` census + laws grep on each diff; landed-blob trace
  (`git rev-parse <sha>:<path>` vs `HEAD:<path>`); executable fix proof for every prior
  finding in `tests/verification/test_r01_prior_findings.py` (hermetic, in-memory rows only);
  pre-heal discrimination runs in a detached worktree.
- Reviewer lane: `lane/dataos-r01-1` (read-only; no production code touched).

## Per-commit table

| # | PR | Squash | Files (+/−) | Evidence class | rights / new-infra / Tiingo / books / held-PR | Verdict |
|---|---|---|---|---|---|---|
| 1 | #9133 | `52af4108676b` | 2 (+151/−0) | DOCS-ONLY (research/) | PASS / PASS / PASS (prose only) / PASS / PASS — cites held plan PR #9121 as provenance text only, no act on it | CLEAN |
| 2 | #9135 | `f30746d115ff` | 3 (+278/−0) | DOCS-ONLY (agentos/) | PASS / PASS / PASS (prose restates the Tiingo ownership boundary) / PASS / PASS — names Terminal #955 in do_not_redo prose only | CLEAN |
| 3 | #9136 | `65135e2cbbe5` | 3 (+1718/−6) | CODE+TESTS | PASS / PASS / PASS / PASS / see held-PR note below — `token` hits are a validation parameter and a vendor-symbol loop variable, not secrets | CLEAN-WITH-NOTES |
| 4 | #9142 | `6a79d3d88907` | 3 (+312/−6) | CODE+TESTS | PASS / PASS / PASS / PASS / PASS | CLEAN |
| 5 | #9143 | `4c2830929e36` | 6 (+2232/−1) | CODE+TESTS | PASS / PASS (one `app/deploy/update.sh` regex token — see hits) / PASS / PASS / PASS | CLEAN-WITH-NOTES |
| 6 | #9144 | `b5ddaff7f645` | 2 (+263/−0) | TESTS-ONLY (+ research doc) | PASS ×5 — no product code; docs+tests are not product proof (R01.04) | CLEAN |
| 7 | #9148 | `4ce86075b7ac` | 3 (+459/−0) | TESTS-ONLY (+CI wiring, + research doc) | PASS ×5 — credential/token/grant hits are the REFUSED request-key names the matrix proves are refused | CLEAN |
| 8 | #9150 | `9ec07085eb0e` | 6 (+974/−1) | CODE+TESTS | rights PASS (only `unverified`/`not_granted` declarations; `granted` requires DEC:/DSC: evidence — no widening) / PASS (one registry extended, no second registry; R00.03 test) / Tiingo PASS (see stanza proof) / books PASS (`trial_ledger` hit is a CI watched-path entry) / PASS | CLEAN-WITH-NOTES |
| 9 | #9154 | `a135d3cd7c70` | 1 (+331/−0) | DOCS-ONLY (research/) | PASS ×5 — not product proof (R01.04) | CLEAN |
| 10 | #9165 | `76b5be9ece65` | 1 (+1/−1) | CI-ONLY (.github/) | PASS ×5 — a timeout widen is not product proof (R01.04) | CLEAN |
| 11 | #9156 | `383a3bc772e6` | 3 (+690/−2) | CODE+TESTS | PASS ×5 — `rights_limited` is the corporate-action capture vocabulary (a rights ISSUE is an event family); `provider="tiingo"` appears only as test-fixture labels that assert UNQUALIFIED verdicts | CLEAN |
| 12 | #9152 | `0f8ecf0bd6be` | 4 (+2764/−0) | CODE+TESTS (includes closed #9147) | PASS ×5 — `RIGHTS_ISSUE` enum member and price-token heuristic only | CLEAN |
| 13 | #9172 | `fb637c85a6eb` | 8 (+423/−19) | DOCS-ONLY (agentos/ + research/) | PASS ×5 — not product proof (R01.04) | CLEAN |
| 14 | #9179 | `5b5f4d6a280a` | 2 (+988/−1) | CODE+TESTS | PASS ×5 — `publishing_receipt_sha256` is view-receipt vocabulary, not a new publisher | CLEAN |
| 15 | #9183 | `9a68900218f1` | 1 (+1/−0) | CI-ONLY (.github/) | PASS ×5 — curated-scope widen is not product proof (R01.04) | CLEAN |
| 16 | #9168 | `0d6e05ec49f2` | 3 (+66/−1) | CODE-ONLY (export wiring, no tests) | PASS / PASS (second `update.sh` regex token) / PASS / PASS / PASS | CLEAN-WITH-NOTES |
| 17 | #9184 | `2df04150e530` | 5 (+687/−115) | CODE+TESTS | PASS ×5 | CLEAN |
| 18 | #9186 | `bc16f8944583` | 3 (+189/−47) | DOCS-ONLY (agentos/) | PASS ×5 — not product proof (R01.04) | CLEAN |
| 19 | #9185 | `d65c9abbeeeb` | 1 (+30/−0) | CODE-ONLY (exports) | PASS ×5 | CLEAN |
| 20 | #9188 | `6b154e093573` | 3 (+632/−0) | CODE+TESTS (engine/) | PASS ×5 — opt-in canonical read on price_ladder; legacy bytes unchanged per diff | CLEAN |
| 21 | #9210 | `5a7d43b9ba04` | 2 (+848/−0) | CODE+TESTS | PASS ×5 | CLEAN |

Per-commit census facts (each verified with the §Commands greps):

- `git show --stat --format= <sha> | grep -iE 'tiingo'` — EMPTY for all 21 commits (no file path mentions Tiingo).
- `git show --stat --format= <sha> | grep -E '(^| )data/'` — EMPTY for all 21 commits (no historical book touched).
- Forward-ledger grep `^\+.*(trial_ledger|forward_ledger|_ledger\.jsonl|prophet.*book)` — exactly one hit, in #9150: the added line `- engine/trial_ledger.py` is an entry in a CI job's watched-file list in `.github/ci/legacy-jobs.yml` (the job runs pytest on dataos tests); it writes nothing.
- `config/dataset_registry.yml` was touched only by #9150. Proof no `tiingo` stanza line changed: the diff has ZERO content `-` lines (only the `--- a/` header) — a pure insertion; the hunk headers are `@@ -61,80,372,455,574` (all inside rows that precede the Tiingo block, which starts at old line 1032) and `@@ -1554,3 +1604,191 @@` whose three context lines are the tail `notes:` of the LAST Tiingo row (`vendor.tiingo.research.distribution_yield`, old lines 1535–1556 of a 1556-line file) — the 191 new lines are appended AFTER the end of that stanza, at end of file. On main the Tiingo ids run `config/dataset_registry.yml:1032`–`1203+` (`grep -n -i tiingo` = 40+ rows, 20 PROPOSED + 4 PRODUCED measured ids also pinned by test R00.04).

Held-PR evidence (R01.03, source half):

- #9136's subject says it adopted #8637's identity candidate by cherry-pick. Commit body records `cherry picked from commit a77677a891ebc2cfa85757bc27ed06effda4cb26` and `138d5bb1d45b2881e510f5cfbdadc850aa674513` (both objects present in this clone). What was copied: `lib/dataos/identity.py` (+837/−6), `tests/test_dataos_identity.py` (+881, new), plus +6 export lines in `lib/dataos/__init__.py`; the squash message states the RS-pullback programme documents that rode along on the #8637 branch were restored to origin/main content. A cherry-pick copies CONTENT and performs no act on #8637 itself — no merge, label, close, comment or edit of that PR is evidenced anywhere in these 21 diffs. #8637's PR state: ORCHESTRATOR-FILLED.
- #9121 is cited by #9133/#9135 commit-message prose as the masterplan text D00 packages; #7299 and #8076 are not referenced by any of the 21 commits (message grep clean); Terminal #955 appears only as do_not_redo context in #9135's agentos prose. No file owned by any held PR is touched by any subject diff. All PR-state checks: ORCHESTRATOR-FILLED.

## Hard-law hits

Every laws-grep hit (pattern per §5.1) classified; hits group into the classes below —
no hit is a law concern.

- DOCS prose restating the laws (commits 1, 2, 9, 13, 18; ~45 hits): "no rights widened",
  "grants no execution authority", the WS:TIINGO-DATA-OS ownership boundary, "no new
  store/auth/registry/collector/queue/scheduler/publisher", "statv1: token unchanged",
  heal/boundary narratives. Benign: documentation of the laws, not acts.
- `published_at` / `publisher` / `publishing_receipt_sha256` vocabulary (commits 5, 14, 17, 21;
  ~75 hits, the bulk of commit 5): these are the D00.D1 knowledge clocks and the
  retained-view receipt field — Data OS domain nouns, not a new publisher or scheduler. Benign.
- `app/deploy/update.sh` (commits 5 and 16, one line each): adds `read_contract` (5) then
  `price_views` (16) to an EXISTING restart-trigger regex for the admin unit. The pre-existing
  mechanism is untouched; no new daemon/scheduler/publisher is created, and the adjacent comment
  states "No entitlement rows are changed here." Benign, noted.
- `token` identifiers in #9136 (`_ob_text(value, label, *, token=False)`, `"attempt ID token"`,
  and `token` as the vendor-symbol loop variable building `vendor_symbol` rows): naming, not
  credentials; no secret values. Benign.
- `rights` declarations and vocabulary (commit 8, ~40 hits): the registry rows declare
  `purchase_access`/`internal_computation`/`redistribution` = `unverified`/`not_granted` with an
  evidence law that REFUSES `granted` without a DEC:/DSC: pointer (R00.02) — adverse
  declarations narrow, they do not widen. `RIGHTS_VALUES`/`TIINGO_IDS` are closed vocabularies
  the validation and test R00.04 enforce. Benign.
- `rights_limited` / `RIGHTS_ISSUE` / `"rights"` fixture key (commits 11, 12): corporate-action
  vocabulary — a rights issue is an unsupported event family; `rights_limited=True` routes to
  UNCAPTURED/RIGHTS_LIMITED. Benign.
- `provider="tiingo"` in #9156 tests: fixture labels asserting the gate returns UNQUALIFIED /
  SOURCE_NOT_PRODUCED for Tiingo sources — refusing, not using, Tiingo. Benign.
- K01 credential-shaped names (commit 7; `credential`, `token`, `grant`, `entitlement`,
  `secret`, SENTINEL_VALUE...): the tested BEHAVIOUR is that request keys of these shapes are
  REFUSED, not ignored; sentinels are synthetic canaries local to the test. Benign.
- `queue`/`schedule:`/`cron`/`sqlite`/`boto3`/`s3://`/`requests.`/: zero hits in any of the 21
  diffs (the `media_publish`/`reply_queue` strings inside the pre-existing update.sh regex line
  are the unchanged remainder of that line, not additions).

## Landed-blob trace (R01.01, source half)

For every path touched by the 9 CODE+TESTS commits under `lib/dataos/` or `tests/test_dataos_*`
(#9136, #9142, #9143, #9150, #9156, #9152, #9179, #9184, #9210) — plus the export commits and
C01 for completeness. "Later changes" lists `git log --oneline <sha>..HEAD -- <path>`:

| Path | Introduced/changed by | Later changes before HEAD | All within the 21? |
|---|---|---|---|
| `lib/dataos/identity.py` | #9136, #9142 | #9184 (P06 venue maps) | YES |
| `lib/dataos/read_contract.py` | #9143 | #9210 (C02 coverage account) | YES |
| `lib/dataos/registry.py` | #9150 | #9156 (P01 qualify_action_input) | YES |
| `lib/dataos/price_views.py` | #9152 | #9179 (P05), #9184 (P06) | YES |
| `lib/dataos/__init__.py` | #9136, #9143 | #9168, #9185 (export wiring only) | YES |
| `engine/price_ladder.py` | #9188 | none (blob identical) | YES |
| `tests/test_dataos_identity.py` | #9136 | #9144, #9184 | YES |
| `tests/test_dataos_reference_read.py` | #9142 | none | YES |
| `tests/test_dataos_read_coherence.py` | #9143 | none | YES |
| `tests/test_dataos_read_contract.py` | #9143 | #9210 | YES |
| `tests/test_dataos_registry_consumers.py` | #9150 | none | YES |
| `tests/test_dataos_action_projection.py` | #9156 | none | YES |
| `tests/test_dataos_price_revisions.py` | #9152 | #9179, #9184 | YES |
| `tests/test_dataos_price_views.py` | #9152 | #9184 | YES |
| `tests/test_price_ladder.py` | #9188 | none | YES |

No path shows a later change outside the 21 subject commits; nothing unexplained. The three
product-module HEAD blobs equal the commission pins exactly.

## Prior findings

All 16 commissioned rows are FIXED on main; every test is a plain PASS pin (no xfail, no skip).
Node ids are in `tests/verification/test_r01_prior_findings.py`.

| Id | Origin | status on main | test node id |
|---|---|---|---|
| T-M1 | #9143 read_contract | FIXED | `test_r01_t_m1_resolution_outcome_is_identical_for_every_permutation` |
| T-M2 | #9143 | FIXED | `test_r01_t_m2_z_and_offset_spell_one_key_and_mixed_kinds_refuse_typed` |
| T-M3 | #9143 | FIXED | `test_r01_t_m3_snapshot_series_duplicate_ratios_never_both_served` |
| T-M4 | #9143 (EXCLUDE) | FIXED | `test_r01_t_m4_row_of_a_non_selected_generation_is_not_served` |
| T-M5 | #9143 (D00 governs) | FIXED | `test_r01_t_m5_current_never_serves_two_revisions_nor_a_superseded_generation` |
| T-M6 | #9143 | FIXED | `test_r01_t_m6_fingerprint_differs_when_the_selected_generation_differs` |
| T-m1 | #9143 | FIXED (pinned inclusive) | `test_r01_t_m1_row_and_generation_stamped_exactly_at_the_cutoff_are_included` |
| T-m7 | #9143 | FIXED (rows immutable) | `test_r01_t_m7_served_rows_cannot_be_mutated` |
| P-M1 | #9147 P02 | FIXED | `test_r01_p_m1_duplicate_event_id_is_a_typed_refusal` |
| P-M2 | #9152 P04 | FIXED (holding_return = 0) | `test_r01_p_m2_ex_date_close_settles_after_every_same_day_event` |
| P-M3 | #9156 P01 | FIXED (registry REQUIRED) | `test_r01_p_m3_registry_is_required_and_an_unregistered_source_is_unqualified` |
| P-m1 | #9147 | FIXED | `test_r01_p_m1_raw_view_refuses_a_float_close` |
| P-m2 | #9147 | FIXED | `test_r01_p_m2_row_after_the_as_at_day_refuses` |
| P-m4 | #9147/#9152 | FIXED | `test_r01_p_m4_non_positive_p0_or_q0_is_a_typed_refusal` |
| P-m5 | #9152 | FIXED | `test_r01_p_m5_two_rows_on_one_date_refuse` |
| P-m3 | #9147 (→ #9184 P06) | FIXED (venue-local day) | `test_r01_p_m3_2100_et_is_still_the_same_us_exchange_day` |

Discrimination (P6, pre-heal proof — details under Commands): the whole suite fails at
collection in the pre-heal tree (`7ab2bc9d`, pre-heal #9147 head: `ReinvestPolicy` absent, and
`lib.dataos.read_contract` did not exist on that branch at all). Per-row pre-heal defects
reproduced directly at the pre-heal heads named in the wave-2 boundary record:
`split_factor` = 4 (P-M1) and float `close_raw` accepted executable (P-m1) at `7ab2bc9d`;
`holding_return` = 1/50 (P-M2) and duplicate-date silently resolved (P-m5) at `bfba67e0`;
`qualify_action_input(obs)` with NO registry returned CONFIRMED/AS_OBSERVED (P-M3) at
`670aeb59`. P-m3 discriminates at `2df04150^` (pre-P06 `sadj_view` takes no `mic` and used the
UTC date). No pre-heal tree contains both `read_contract` and the wave-2 modules, so no single
pre-heal tree can collect the one-file suite — reported as such, per the commission's allowance.

Seat-ACCEPTED / DEFERRED items (no test, per commission) — current status, one line each, with
whether `agentos/` lists it as unresolved (`agentos/handoffs/DATA-OS-COMPLETION-2026-10-13.md:79-92`):

- R00 m7 (string violations — ACCEPT): accepted by seat; NOT listed as unresolved in the records.
- R00 m8 (consumer A `basis: tradj`, XASE venue — DEFER): ruled by D00.A1; the handoff's
  unresolved row "R02 m3/m6/m8" records the venue/census limitation (consumer-A venues
  unmeasurable in-repo) — implementation of the venue clock landed in P06 (#9184); the
  consumer-A census gap (R00 G2/G4) remains a recorded limitation.
- m9 (prose citations — ACCEPT): listed unresolved in the handoff ("R02 m9" — point-in-time
  line citations; only the ADVERSE doc row is test-pinned).
- m10 (K01 wired into the web job — ACCEPT): listed unresolved in the handoff ("R02 m10" —
  right home, departs from programme law 3's letter).
- T01 m3 (empty view contract): listed unresolved in the handoff; verified still open —
  `ViewContract.__post_init__` enforces only `identity`'s `security_id`/`listing_id`, so
  `field_units={}` / `adjustment_reference={}` are accepted.
- T01 m4 (code_version checked late): listed unresolved in the handoff; verified still open —
  `reconstruct()` validates `code_version` after the dependency loops have iterated all rows.
- T01 m5 (one clock per request): listed unresolved in the handoff; behaviour confirmed in code —
  a row missing the requested clock column refuses the whole read with MISSING_CLOCK_VALUE
  (fail-closed), and mixed-clock reads are inexpressible.
- ORCH-1 notes: listed unresolved in the handoff ("T01 (wave-1 orchestrator note)"); verified on
  HEAD — a non-mapping row raises `ReadContractError` (typed error class, not a `ReadRefusal`),
  and `revision_seq` without `key_fields` raises `ReadContractError("key_fields must name at
  least one key column")`.

## Release-gate checklist

- **R01.01 — exact reviewed blobs and required integrated checks correspond to the released
  candidate.** Source half: PASS — the reviewed HEAD is `15bc4a7b392f…`; the four blob pins
  match; the landed-blob trace shows every later change to every touched path is one of the 21
  reviewed commits; `git diff --name-only <base> HEAD` on this lane lists only the three owned
  paths with zero modifications.
  ORCHESTRATOR-FILLED (closed in §Orchestrator-filled remote evidence): merged-head == checked-head on the remote, and the required checks
  concluded on exactly that head.
- **R01.02 — old green CI, an unrelated workflow or a sibling waiver cannot qualify a changed
  candidate.** Source half: PASS — nothing in the 21 diffs qualifies a candidate by reference to
  an old run; the CI-only commits (#9165, #9183) widen an existing job's timeout/curated scope
  and are themselves flagged CI-ONLY (not product proof) in the table above.
  ORCHESTRATOR-FILLED (closed in §Orchestrator-filled remote evidence): no green run predates a changed head; per-head check attribution.
- **R01.03 — no auto-merge/label change on another owner's held PR, no hidden broad conflict
  resolution.** Source half: PASS — #9136's cherry-pick copies content only and restores
  non-identity paths to origin/main content (recorded in its commit body); #9121/#955 appear
  only as prose provenance; #7299/#8076 are unreferenced; no diff touches a path owned by a
  held PR. ORCHESTRATOR-FILLED (closed in §Orchestrator-filled remote evidence): held-PR (#8637, #7299, #9121, #8076, Terminal #955) label,
  auto-merge and review-state history.
- **R01.04 — document-package checks are not counted as product test or independent code
  review.** PASS — evidence classes are stamped per row: the DOCS-ONLY (#9133, #9135, #9154,
  #9172, #9186) and CI-ONLY (#9165, #9183) commits are never product proof; #9144/#9148 are
  TESTS-ONLY (test proof, not independent review); product evidence rests on the CODE+TESTS
  rows and this lane's independent executable reproducers.

## Orchestrator-filled remote evidence

ORCH-4 filled this section on 2026-10-14 from GitHub state. The reviewer lane had no `gh` or CI
view. The evidence class is remote PR/check state plus local blob comparison. No act was taken
on any PR listed here.

Commands used:

- one GraphQL read of `statusCheckRollup` on each PR's merged head
  (`scratchpad/orch/o4/tools/r01_pr_state.py`);
- `git rev-parse <squash>:<path>` against `<merged-head>:<path>` for every path the squash
  touched (`r01_land_proof.sh`);
- for each path whose blob differs, the PR hunk compared with the squash hunk
  (`r01_hunk_proof.sh`).

The table covers all 21 reviewed commits plus the heal #9234.

| PR | squash | merged head | merged (UTC) | checks at merged head | non-passing at head | landing proof | class |
| --- | --- | --- | --- | --- | --- | --- | --- |
| #9133 | `52af4108676b` | `11386de562f0` | 2026-10-13 11:12 | 17 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 2/2 paths blob-identical | DOCS-ONLY |
| #9135 | `f30746d115ff` | `f3f3dcee70e8` | 2026-10-13 11:37 | 17 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 3/3 paths blob-identical | DOCS-ONLY |
| #9136 | `65135e2cbbe5` | `f0f25202c438` | 2026-10-13 15:17 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 3/3 paths blob-identical | PRODUCT |
| #9142 | `6a79d3d88907` | `fab7309e2bbb` | 2026-10-13 16:07 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 2/3 paths blob-identical; legacy-jobs.yml: PR hunk == squash hunk (SAME) | PRODUCT |
| #9143 | `4c2830929e36` | `d394c839971c` | 2026-10-13 17:15 | 27 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 5/6 paths blob-identical; legacy-jobs.yml: PR hunk == squash hunk (SAME) | PRODUCT |
| #9144 | `b5ddaff7f645` | `5b1ac21d41d6` | 2026-10-13 15:45 | 18 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 2/2 paths blob-identical | TEST-ONLY |
| #9148 | `4ce86075b7ac` | `dfcbdbd59960` | 2026-10-13 16:15 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 2/3 paths blob-identical; legacy-jobs.yml: PR hunk == squash hunk (SAME) | TEST-ONLY |
| #9150 | `9ec07085eb0e` | `ccef37925b5a` | 2026-10-13 16:53 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 5/6 paths blob-identical; legacy-jobs.yml: PR hunk == squash hunk (SAME) | PRODUCT |
| #9154 | `a135d3cd7c70` | `d15bfa5d8d3e` | 2026-10-13 13:46 | 17 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 1/1 paths blob-identical | DOCS-ONLY |
| #9165 | `76b5be9ece65` | `1465b8ce7843` | 2026-10-13 18:57 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 1/1 paths blob-identical | CI-ONLY |
| #9156 | `383a3bc772e6` | `c1c79e49a01c` | 2026-10-13 20:11 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 2/3 paths blob-identical; legacy-jobs.yml: PR hunk == squash hunk (SAME) | PRODUCT |
| #9152 | `0f8ecf0bd6be` | `2f36c688802f` | 2026-10-13 20:32 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 3/4 paths blob-identical; legacy-jobs.yml: PR hunk == squash hunk (SAME) | PRODUCT |
| #9172 | `fb637c85a6eb` | `2c10c71ed7c5` | 2026-10-13 21:35 | 18 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 8/8 paths blob-identical | DOCS-ONLY |
| #9179 | `5b5f4d6a280a` | `6355aff8781b` | 2026-10-13 22:15 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 2/2 paths blob-identical | PRODUCT |
| #9183 | `9a68900218f1` | `f0ad11d1035e` | 2026-10-13 22:42 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 1/1 paths blob-identical | CI-ONLY |
| #9168 | `0d6e05ec49f2` | `1cf799b355dc` | 2026-10-13 23:17 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 2/3 paths blob-identical; legacy-jobs.yml: PR hunk == squash hunk (SAME) | PRODUCT |
| #9184 | `2df04150e530` | `1470668dcc71` | 2026-10-13 23:38 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 5/5 paths blob-identical | PRODUCT |
| #9186 | `bc16f8944583` | `10b03f3f52df` | 2026-10-14 00:02 | 17 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 3/3 paths blob-identical | DOCS-ONLY |
| #9185 | `d65c9abbeeeb` | `69443b58c1ec` | 2026-10-14 00:16 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 1/1 paths blob-identical | PRODUCT |
| #9188 | `6b154e093573` | `b2fadd37d807` | 2026-10-14 01:03 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 2/3 paths blob-identical; legacy-jobs.yml: PR hunk == squash hunk (SAME) | PRODUCT |
| #9210 | `5a7d43b9ba04` | `22f638d84814` | 2026-10-14 02:42 | 26 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 2/2 paths blob-identical | PRODUCT |
| #9234 | `80df7978789e` | `6526e5e253e0` | 2026-10-14 04:40 | 16 concluded, rollup FAILURE | ci-authority/codex/merge-queue-pilot (FAILURE) | 1/1 paths blob-identical | TEST-ONLY |

Held PRs observed (state only, no act taken): #8637 OPEN DRAFT auto-merge=null labels=none; #7299 OPEN DRAFT auto-merge=null labels=none; #9121 OPEN DRAFT auto-merge=null labels=none; #8076 OPEN DRAFT auto-merge=null labels=none; #9147 CLOSED DRAFT auto-merge=null labels=none

Terminal #955 (`mastermind-terminal`) was observed separately. It belongs to another programme
("Admit qualified BOATS trades through the existing Quote Hub"). It merged at
2026-10-13T22:25:18Z as merge `140894302f9e`. Its label and auto-merge events were made by the
shared fleet GitHub account, so the session that made them cannot be identified. None of the 21
Data OS diffs touches the Terminal repo; it appears only as do_not_redo prose in #9135.

### Gate closure

- **R01.01 (remote half): PASS.**
  - Every row's checks concluded on the merged head itself.
  - The only non-passing check on any row is `ci-authority/codex/merge-queue-pilot`, the
    standing spurious X recorded in fleet law.
  - The landing proof finds the squash blob byte-identical to the merged-head blob for 14 of
    22 PRs.
  - The other 8 PRs (#9142, #9143, #9148, #9150, #9152, #9156, #9168, #9188) differ only in
    `.github/ci/legacy-jobs.yml`. There the PR's own hunk equals the squash hunk (8/8
    SAME_HUNK), so each difference is a sibling job landing in the same file, not drift in
    this PR's change.
- **R01.02 (remote half): PASS.** For every row, check attribution is to the merged head. No
  row is qualified by a run on an earlier head, an unrelated workflow or a sibling's waiver.
- **R01.03 (remote half): PASS, with one note.**
  - Current state: #8637, #7299, #9121 and #8076 are OPEN, DRAFT, `autoMergeRequest=null`,
    with no labels.
  - History: one GraphQL `timelineItems` read (`r01_held_history.py`, since
    2026-10-12T00:00Z) covering label, unlabel, auto-merge enable/disable, ready-for-review,
    convert-to-draft, review, force-push, close, reopen and merge events. It finds **zero**
    such events on #8637, #7299, #9121 and #8076 across the whole Data OS window.
  - #9147 has exactly one event in that window, a close at 2026-10-13T20:33:21Z. #9147 is
    this programme's own P02 lane PR (`claude/dataos-p02-2026-10-13`), not another owner's
    held PR. It was closed as INCLUDED: its head `cb9f0798` is strictly contained in #9152
    (P04), which squash-merged as `0f8ecf0b` 28 s earlier. No label or arming change was
    made to it.
  - Note: Terminal #955 is MERGED by its own programme's arming, as described above. Because
    the fleet token is shared, the actor cannot be attributed. No Data OS commit refers to it
    or touches it.

## New findings

None in code. One record-hygiene observation (not a code defect, no xfail warranted — it pins
no behaviour): `agentos/handoffs/DATA-OS-COMPLETION-2026-10-13.md:88` still lists "R01 m7 …
the inner rows are plain dicts, and an edit flows into a later selected_input_sha256s call" as
unresolved, but the landed #9143 code already wraps every served row in a read-only
`MappingProxyType` (comment "R01 m7" at `lib/dataos/read_contract.py`, ReadResult
`__post_init__`), and `test_r01_t_m7_served_rows_cannot_be_mutated` pins the fixed behaviour.
The unresolved-list entry is stale relative to main and should be pruned by its owner.

## Not reviewed

- No CI run, check conclusion, PR state, label, merge-queue event or review approval was
  observed (no `gh`, no CI view on this host) — every such item is ORCHESTRATOR-FILLED.
- The 21 diffs were reviewed at census/signature level (file lists, laws greps, hunk
  inspection where flagged) — not every one of the ~15k added test lines was read line-by-line;
  the product modules (`lib/dataos/*`, `engine/price_ladder.py`) were read at the seams this
  lane's findings target.
- `config/dataset_registry.yml` was reviewed for #9150's diff and the Tiingo stanza boundary,
  not in full (1794 lines).
- The Terminal repo (U01/U02, consumer A) is cross-repo and was not accessible; its claims are
  taken only as recorded prose.
- The full product test suites were not run on this lane; only
  `tests/verification/test_r01_prior_findings.py` was executed (16/16 pass, twice, identical).

## Commands

```
git fetch -q origin main && git cat-file -t 15bc4a7b392f152518c9fb8b822bd336ddc108b5   # -> commit
git worktree add -b lane/dataos-r01-1 ~/lanes/wt/dataos-r01-1 15bc4a7b392f…            # HEAD = start commit
git rev-parse HEAD:lib/dataos/read_contract.py HEAD:lib/dataos/price_views.py \
  HEAD:lib/dataos/registry.py HEAD:research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md
PY -c "import pandas, pyarrow, yaml, pytest; print('deps-ok')"
git rev-parse <21 shorts>            # 21 full SHAs, order preserved
git merge-base --is-ancestor <sha> HEAD && echo on-main <sha>   # x21, all on-main
# per-commit census (x21):
git show --stat --format='%H %s' <sha>
git show --format= <sha> | grep -nE '^\+.*(schedule:|cron|sqlite|\.db\b|boto3|r2_|s3://|requests\.|urllib|socket|tiingo|Tiingo|TIINGO|rights|entitle|licen[cs]e|grant|token|secret|password|publish|launchd|plist|daemon|queue)' | head -80
git show --stat --format= <sha> | grep -iE 'tiingo'            # empty x21
git show --stat --format= <sha> | grep -E '(^| )data/'         # empty x21
git show --format= 9ec07085… -- config/dataset_registry.yml | grep -nE '^[-+]'   # zero content minus lines
grep -n -i tiingo config/dataset_registry.yml | head -40
git log -1 --format='%B' 65135e2c…                 # cherry-pick provenance (a77677a8…, 138d5bb1…)
git rev-parse <sha>:<path> / git rev-parse HEAD:<path>; git log --oneline <sha>..HEAD -- <path>   # §5.2 trace
git grep -n -iE 'unresolved|known limitation' HEAD -- research/data_os_completion agentos | head -40
PYTHONDONTWRITEBYTECODE=1 PY -m pytest tests/verification/test_r01_prior_findings.py -q -p no:cacheprovider -rxs   # x2, identical
git diff --name-only 15bc4a7b… HEAD; git diff --name-only --diff-filter=M 15bc4a7b… HEAD   # owned paths only / empty
PY -m py_compile tests/verification/test_r01_prior_findings.py && echo compile-ok
grep -n "datetime.now\|time\.time\|date.today\|requests\|urllib\|socket\|subprocess\|data/" tests/verification/test_r01_prior_findings.py   # zero hits
PY scripts/check_contract_delta.py --base 15bc4a7b…  # pre-commit: 0 introduced, 0 inherited;
                                                     # final HEAD: 1 introduced, 0 inherited — the
                                                     # expected row for this lane's unwired suite
                                                     # ("tests/verification/test_r01_prior_findings.py
                                                     # is a new pytest suite named by no run: step");
                                                     # .github/ci is outside this lane's owned paths,
                                                     # so the wiring is left to the seat
# P6 discrimination (detached, then git worktree remove --force):
git worktree add --detach ~/lanes/wt/dataos-r01-1-old 7ab2bc9d && cp <test file> …/tests/verification/
PY -m pytest … -q   # collection error: cannot import ReinvestPolicy (pre-heal); read_contract absent on that branch
git checkout -q 7ab2bc9d  && PY -c '…split_factor…'   # -> 4            (P-M1) ; raw float executable (P-m1)
git checkout -q bfba67e0 && PY -c '…total_return_view…' # -> 1/50       (P-M2) ; duplicate date resolved (P-m5)
git checkout -q 670aeb59 && PY -c '…qualify_action_input(obs)…' # -> CONFIRMED/AS_OBSERVED (P-M3)
```
