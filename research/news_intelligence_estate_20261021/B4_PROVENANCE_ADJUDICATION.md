# B4 provenance adjudication — gated_v3 (PR #10063 head 01f9e0a50f17)

Adjudicating lane: NEWS-ORCH3-PROV (Fabric review-grade worker, glm-5.3), seat 602cd180,
2026-10-31. Subject: the registered gated_v3 draw at macro PR #10063 head
`01f9e0a50f17879f5a13a5fe10eff14c52fb4cc2` (base `64ef5131a5f50fb65f0ad25a049a457e18258495`),
under `research/prophet_v4/news_to_business_impact_20261006/benchmark/`. All numbers below
are read from a file produced by the registered run or from a git object, cited by path.
`$W/b4/` = this lane's read-only extracts of the nine benchmark files from the PR head
(`$W` = `~/lanes/tmp/news-orch3-prov-r2`); `$R3` = the registered run directory
`/home/ubuntu3/lanes/tmp/ne-b4-gated-v3-20261022-r3/` (read-only host scratch).

PROVENANCE LABEL: RECONSTRUCTION

## Strict separation

600 registration cases / gated_v2 99 drawn of which 74 routed MATCH (scorable) / gated_v3
135 drawn / 40 NEW cases routing-pending / 0 prospective. The 135 drawn are not 135 scored
or gold cases; a shared group id does not transfer a label, a verdict or independence
across versions, assets, clocks or horizons; cluster/group ids are never evidence of
independence.

## Recovered vs reconstructed

| artifact | status | hash evidence | where it lives |
|---|---|---|---|
| trading-session calendar (`sessions.json`) | RECONSTRUCTED | run copy and committed copy both sha256 `c029035df267ef4f3cc12ab46723069051f29d04311e8e49c7abb5ec0ac872b4` (`sha256sum $R3/in/sessions.json $W/b4/sessions.json`); the recorded original hash `80495fb43056ec8a8c5253b6a5bfa316f643a0e352e8ac73c4c3bc0105b46f36` (`benchmark/README.md:37`) matches no object found anywhere searched (see next section) | committed in the #10063 tree at `benchmark/body_frame_v3/sessions.json`; run copy at `$R3/in/sessions.json`; both byte-identical to the r2 reconstruction from commit `c6c11400bf44` (per `gated_v3/CENSUS.md` §1) |
| classifier pin (`engine/news_common.py`) | RECOVERED-GIT | pin blob `ea8ada59ea34cbba3b55c2bdaa1f72a5c0a58156` == `git rev-parse 6fc028727a5a:engine/news_common.py` (exact git blob, commit `6fc028727a5a7e870242ab9296a89cac9a9c9b50`, #9381); BASE blob `71e153136d66dad02239325a6927510a965d7026` == `64ef5131a5f5:engine/news_common.py`; both `git cat-file -t` = blob; pin→BASE diff = 132 changed lines in 4 hunks | the pin is an exact git blob at commit `6fc028727a5a`; used as a temporary working-tree pin during registered steps 1–4 and restored before commit (per `gated_v3/CENSUS.md` §2 DEVIATIONS); not present in any committed tree of #10063 |
| body directory (`bodies_v3/`) | RECOVERED-HOST | `sha256sum $R3/bodies_v3/bodies.jsonl` = `59bbeb2251d4e1577003d2eb118672592651b6428904256b098039a04b98c86c`, equal to the value recorded in `gated_v3/CENSUS.md` §10; `texts/` holds 575 files = `body_report.json` `texts_written` 575 = 575 distinct `text_sha256` among the 940 `status:"available"` filing documents (0 missing) | single copy on host `ubuntu3-MS-7E61` at `/home/ubuntu3/lanes/tmp/ne-b4-gated-v3-20261022-r3/bodies_v3/`; not in git (bodies/texts are never committed — DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE) |
| draw inputs (tape + ledgers) | RECOVERED-GIT (by hash against committed sources) | `sha256sum $R3/in/`: `items.parquet` `bab574014865532c63977e44f12be0e8a3234ba9faa8253d2717e43d67580e17` OK, `event_log.parquet` `2345274391433d6e448a5cce9c70bea9c9a1c4efd26f6ef2f7f9106ef185ac18` OK, `reject_sample.parquet` `5aed74fdc6adb208064005ad2b2634a91287d4a43f8eddecae2335cb0f6beeb0` OK, `ticker_cik_ledger.json` `6fe2459b360e16f5da1ac7f659feafb0eee3d11bb6c6477ff4fc05d4bf74621e` OK — each OK/BAD against the Expected column of `gated_v3/CENSUS.md` §1 | committed repo sources (`data/qbus/`, `data/news/`, `data/edgar/` per `gated_v3/CENSUS.md` §1); run copies at `$R3/in/` |

The provenance label is RECONSTRUCTION because exactly one registered-run input — the
trading calendar — could not be produced byte-identical to its recorded original; every
other artifact chain above is hash-recovered.

## Original calendar hunt

Recorded original hash (the hash the benchmark README recorded for the original sessions
calendar): `H = 80495fb43056ec8a8c5253b6a5bfa316f643a0e352e8ac73c4c3bc0105b46f36`.

Citation: `git show HEAD:research/prophet_v4/news_to_business_impact_20261006/benchmark/README.md
| grep -n 80495fb4` → line 37: "| `sessions.json` (trading-session calendar for 8-K matching) |
`80495fb43056ec8a8c5253b6a5bfa316f643a0e352e8ac73c4c3bc0105b46f36` |". The line was introduced
once, by commit `c0a9d097822b9c503e84fdf6648686dbaa4b4077` (2026-10-14, #9290 "news-impact W2
benchmark — tape draw, EDGAR body frame, frozen draws") and never removed (path-restricted
pickaxe `git log --all -S"$H" -- <README path>`).

Every location searched, with its result:

| # | location searched | command (essence) | result |
|---|---|---|---|
| 1 | registered run input `$R3/in/sessions.json` | `sha256sum` | `c029035d…` ≠ H — NOT FOUND (this is the reconstruction the run used) |
| 2 | committed copy in the PR head `$W/b4/sessions.json` (= `01f9e0a50f17:benchmark/body_frame_v3/sessions.json`) | `sha256sum` | `c029035d…` ≠ H — NOT FOUND (same reconstruction, byte-identical to #1) |
| 3 | filesystem `/home/ubuntu3/lanes` (maxdepth 5, `edgar_cache` pruned; `sessions*.json`, `*calendar*.json/csv`, `*sessions*.txt`) | `find … \| xargs sha256sum` | 174 candidate files hashed; no sha256 equals H — NOT FOUND (full list `$W/calfiles.sha`; only `sessions.json` copies found are the three `c029035d…` reconstruction copies at `$R3/in/`, `$W/b4/`, `~/lanes/tmp/ne-b4-gated-v3-20261022-r2/in/`) |
| 4 | deeper paths the maxdepth-5 sweep cannot reach: `/home/ubuntu3/lanes/repos` (incl. primary checkout) and `/home/ubuntu3/lanes/tmp`, no maxdepth, same name patterns | `find … \| xargs sha256sum` | 32 further files hashed (research/site calendars, unrelated); no sha256 equals H — NOT FOUND (`$W/calfiles_deep.sha`) |
| 5 | git history by path: every `sessions*.json` / `calendar*.json` blob in all 227 locally-visible commits touching those pathspecs (uncapped; the frozen spec's `head -60` cap covered 60 commits / 89 blobs, extended to all 227 / 277 distinct blobs) | `git rev-list --all -- <pathspecs>` then per-commit `git rev-parse`/`git cat-file blob \| sha256sum` | 277 distinct blob hashes; none equals H — NOT FOUND; the only `benchmark/body_frame_v3/sessions.json` blobs in history are `c029035d…` at commits `c6c11400bf44` and `01f9e0a50f17` (`$W/calblobs_all`) |
| 6 | the entire local git object store: sha256 of **every** blob of all 40,470 locally-visible commits (47.76 GiB pack) | `git cat-file --batch-all-objects --batch --unordered` piped through sha256 | 2,272,098 blobs hashed; **none** has sha256 == H — NOT FOUND (`$W/fullobjects.txt`) |
| 7 | committed citations of the hash string at specific revisions | `git grep "$H" HEAD / c6c11400bf44 / 01f9e0a50f17` | string present only as the README:37 citation and the two census notes (`gated_v3/CENSUS.md` §1 line 30; r2 census) — citations, never the artifact |
| 8 | unrestricted history pickaxe for the hash string (frozen-spec STEP 2 command) | `git log --all -S"$H"` / `-S80495fb4` | see Evidence §hunt-8: first invocation stopped at the harness 30-minute background cap with no output; restarted with the 2-hour cap; path-restricted pickaxe (#9) completed meanwhile and located every add/remove of the string on the paths that carry it |

| # | location searched (cont.) | result |
|---|---|---|
| 9 | path-restricted pickaxe for the hash string on the paths that carry or could carry it (`benchmark/README.md`, `gated_v3/CENSUS.md`, `body_frame_v3/`) | README: introduced once by `c0a9d097822b` (#9290), never removed; CENSUS.md: cited by `c6c11400bf44` (r2 census) and `01f9e0a50f17` (B4 head); `body_frame_v3/`: no commit ever added/removed the string |

**NOT FOUND.** The original calendar artifact with sha256
`80495fb43056ec8a8c5253b6a5bfa316f643a0e352e8ac73c4c3bc0105b46f36` was not found in any
location searched: not on the ubuntu3 filesystem under `/home/ubuntu3/lanes` (206 hashed
candidates across both sweeps), not as any blob of the 227 calendar-path commits, and not
as any of the 2,272,098 blobs in the entire local object store. This hunt is bounded by
what this lane can lawfully reach: the local filesystem and the locally-visible git history
(40,470 commits); `gh`/GitHub-side search is forbidden to this lane, and history never
fetched locally is invisible to a local scan. What exists everywhere is the reconstruction
(`c029035d…`, 128 sessions), which the r2 lane built from the recorded rule and the r3 run
reused byte-for-byte (`gated_v3/CENSUS.md` §1).

Rule-consistency check of the reconstruction (read-only; never recovery): `$R3/in/sessions.json`
is a dict with the single key `sessions`, a 128-element list of ISO dates 2026-07-01..2026-12-31;
every date is a weekday Mon–Fri, no duplicates, and exactly `2026-07-03`, `2026-09-07`,
`2026-11-26`, `2026-12-25` are omitted from the 132 weekdays in range → PASS on the recorded
reconstruction rule ("every weekday 2026-07-01..2026-12-31 except 2026-07-03, 2026-09-07,
2026-11-26, 2026-12-25", `gated_v3/CENSUS.md` §1). Consistent with a rule is not identical to
the original: the original could differ in date set (other holidays/half-days), ordering,
formatting or extra keys while a rule-based rebuild passes this check.

## What the 1,202 checks establish and do not

What was tested (all from `gated_v3/CENSUS.md` §1, "Step-0c calendar check"): for every
item_id whose committed gated_v2 status (`../body_frame_v2/status_map.json`) was
`body_unavailable:window_open` (113 items) or `body_unavailable:no_qualifying_8k`
(1,089 items) — 1,202 items in total — the run computed
`engine.news_impact.edgar_body.session_window(seendate, sessions, band=(1,4))` (engine/news_impact/edgar_body.py:226)
from this run's `candidates_all.jsonl` **using the reconstructed calendar**, and tested
whether `(window end >= 2026-10-14)` equals `(v2 status is window_open)`. Observed: 113
window_open items all with window end >= 2026-10-14; 1,089 no_qualifying_8k items all with
window end < 2026-10-14; 1,202 examined (expected 1,202), 0 missing from candidates,
0 None windows, 0 untestable, 0 contradictions.

What that establishes: on those 1,202 rows, the reconstruction partitions the rows exactly
as the committed v2 statuses record the original calendar as having partitioned them — the
reconstruction agrees with the original's window-open/window-closed **outcome** on every
tested row.

What that does not establish:

- the identity of the original artifact — nothing about these checks shows the original
  calendar was byte-identical, or even date-identical, to the reconstruction;
- identical windows for the 420 body-available rows (`gated_v3/CENSUS.md` §3) — window
  interiors (start/seen/end session choices) were not compared for any row, only the
  end-vs-2026-10-14 predicate on the 1,202;
- identical filing session offsets — `filings[].session_offset` values in
  `$R3/bodies_v3/bodies.jsonl` were computed under the reconstruction and were never
  checked against original offsets;
- anything about rows outside the 1,202 (the other 1,635 of 2,837 candidates, and every
  row of any other version).

Any calendar that agrees with the original on every session between each tested seendate
and 2026-10-14 passes the same test: the predicate depends only on the session sequence
each tested row's window spans, so the 1,202 checks cannot distinguish the reconstruction
from any other calendar that coincides with it (and with the original) on those spans —
including on holidays inside tested spans. The 1,202 checks are a consistency bound, not
an identification.

## Boundary sensitivity (counts only)

No redraw and no re-windowing was performed; these are read-only counts over the
registered artifacts. Inputs: `$W/b4/cases.jsonl` (135 drawn item_ids; all 135 carry body
status `available` in `$R3/bodies_v3/bodies.jsonl`), `$R3/bodies_v3/bodies.jsonl` (windows
`[start, seen, end]` and `filings[]`), `$R3/in/sessions.json`. Distinct
`filings[].relation` values across all 2,837 body records: `filed_after_seen` 277,
`filed_before_seen` 82, `filed_same_session` 125 (484 filings total); per-filing keys:
`accession, documents, filing_date, form, index_url, items, reason, relation,
session_offset`. Window ends across the 135 drawn cases range 2026-07-22..2026-10-16
(5 ends >= 2026-10-14); window starts range 2026-07-15..2026-10-09.

Counts over the 135 drawn cases:

- (a) window span `[start, end]` contains 2026-07-03 or 2026-09-07 (the reconstructed
  holidays inside the draw window): **7** — `389a49089309246c 55b0f7c87d3facba
  5b6fcf728fb48e27 b1f8439867c811b6 c5e8d851d7c5756a d9cc14d215da6b7a ef84ce873e9a3aa0`
- (b) at least one attached filing with `filing_date` equal to the window start or the
  window end (edge filings; a one-session calendar shift moves them in or out): **43** —
  `0f9b63978a20a381 19b3170d334484c4 1f0c34a6a4af2341 202db9bcfa416a92 24274c667413e1be
  2678be07b33de148 26a0b5728c9f940d 2efd29a51585bc8d 2f759e6bba95116c 389a49089309246c
  4ae628affba0f83d 4ebd7e5286323806 4ec17f189d0724c3 5126d45f9274513c 5b6fcf728fb48e27
  5fa111268385f5a4 67e5571ab44a68af 6e212636947aab91 70c3eca15231c1d4 788a5b3081ccf72c
  853f5d2f9f43c3a6 8a14460d21a3356d 913f696c23cbedaa 92a85df5ccb392a9 933e11b4dc2b8cdd
  947b73a0f2f0baf1 9b1b6db61b46eb60 9f792531cea5c8a8 a6fa29c5d2bc577e ac30ce21b19aca45
  b5e2d02a26c4b10d ba2654d517ab8024 c0d771dbaa34d2e4 c5e8d851d7c5756a d1eeb29c475402b4
  d788b0663745816a d7f5b33520e46491 ddc18d265856ec3b df3cd4b9107de180 eef253de59c12735
  ef84ce873e9a3aa0 f074de5943030d42 f49cd7c25b80b915`
- (c) window end >= 2026-10-21 (within one calendar day of the run's ASOF 2026-10-22):
  **0**
- (d) |window end − 2026-10-14| <= 1 day: **4**
- (e) seendate's UTC date within one day of 2026-07-17 or 2026-10-14 (the manifest window
  bounds, `$W/b4/manifest.json` `window = {start: 2026-07-17, end: 2026-10-14}`): **5**

Script: `$W/boundary_counts.py` (host scratch, never committed). These counts describe
exposure of the registered draw to calendar-boundary effects; they draw no conclusion and
change nothing.

## What this adjudication does not do

- No redraw: `tape_draw`, `edgar_body` and `routing_gates` were not re-run; no window was
  recomputed except read-only rule checks and counts over the registered artifacts.
- No label is minted or promoted beyond the recorded one: the label above restates
  RECONSTRUCTION because the original calendar was not found byte-identical; no case,
  signal, sentiment or LLM confidence is promoted into any authority.
- No verdict on routing or scoring of any case, and no opinion on PR #10063's scoring;
  the 40 NEW cases stay routing-pending, the 135 drawn are not 135 scored or gold cases.
- No change to #10063: the registered draw stays the registered draw; nothing under
  `benchmark/gated_v3/` or `benchmark/body_frame_v3/` is committed by this lane (those
  paths belong to #10063), and no bodies, filing text, headlines or candidates are
  committed (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE: ids, classes, counts and hashes only).

## Evidence

Commands run and values observed, this lane, 2026-10-31. `$W` = `~/lanes/tmp/news-orch3-prov-r2`,
`$R3` = `/home/ubuntu3/lanes/tmp/ne-b4-gated-v3-20261022-r3`, `B4` = `01f9e0a50f17879f5a13a5fe10eff14c52fb4cc2`,
`BASE` = `64ef5131a5f50fb65f0ad25a049a457e18258495`, `P` = `research/prophet_v4/news_to_business_impact_20261006/benchmark`.

- **STEP 0** — `git rev-parse HEAD` → `6135e2c3c64cd62258f176b234c6bb27960e3adb` (required:
  same). `git status --porcelain` → empty. `git branch --show-current` →
  `lane/news-orch3-prov-r2`. `test -d $R3/bodies_v3` → present.
- **STEP 1** — `git fetch origin 01f9e0a50f17…`; `git rev-parse FETCH_HEAD` →
  `01f9e0a50f17879f5a13a5fe10eff14c52fb4cc2` (assert PASS). Nine files extracted from
  `B4:$P/gated_v3/` and `B4:$P/body_frame_v3/` into `$W/b4/` (CENSUS.md, cases.jsonl,
  draw_report.json, manifest.json, body_report.json, gates2_map.json, gates2_report.json,
  sessions.json, status_map.json). `wc -l $W/b4/cases.jsonl` → 135 (required: 135).
  `$W/b4/manifest.json`: `seed` 20261014, `window {start: 2026-07-17, end: 2026-10-14}`,
  `counters {low_value: 4, outside_window: 7856, rights_refused: 0, unresolved_issuer: 0}`
  — all equal to `gated_v3/CENSUS.md` §5.
- **STEP 2 (hunt)** — citation: `README.md:37` (text quoted above). `sha256sum
  $R3/in/sessions.json $W/b4/sessions.json` → both `c029035df267ef4f3cc12ab46723069051f29d04311e8e49c7abb5ec0ac872b4`.
  Filesystem sweep 1 (`find /home/ubuntu3/lanes -maxdepth 5 …`): 174 files hashed, no H
  (`$W/calfiles.sha`). Filesystem sweep 2 (deep, `repos/` + `tmp/`, no maxdepth): 32 files
  hashed, no H (`$W/calfiles_deep.sha`). Blob scan, frozen cap: 60 commits / 89 distinct
  blob hashes, no H (`$W/calblobs`). Blob scan, uncapped: 227 commits / 277 distinct blobs,
  no H; only `benchmark/body_frame_v3/sessions.json` blobs in history are `c029035d…` at
  `c6c11400bf44` and `01f9e0a50f17` (`$W/calblobs_all`). Full object store: 2,272,098 blobs
  hashed via `git cat-file --batch-all-objects --batch --unordered`, none equals H
  (`$W/fullobjects.txt`). `git grep "$H"` at HEAD / `c6c11400bf44` / `01f9e0a50f17`:
  citations only (README:37 at all three; CENSUS.md §1-line-30 notes at the two census
  commits). Path-restricted pickaxe `git log --all -S"$H" -- <path>`: README →
  `c0a9d097822b9c503e84fdf6648686dbaa4b4077` (2026-10-14, #9290) only; `gated_v3/CENSUS.md`
  → `c6c11400bf44f6223f0fd2bddd1606edd66a9222` and `01f9e0a50f17879f5a13a5fe10eff14c52fb4cc2`;
  `body_frame_v3/` → none. Unrestricted pickaxe (hunt-8): see the GAPS entry in the lane
  return packet.
- **STEP 2 (rule check)** — `$R3/in/sessions.json`: dict, key `sessions`, 128 dates
  2026-07-01..2026-12-31; all weekdays; no duplicates; omitted weekdays exactly
  2026-07-03, 2026-09-07, 2026-11-26, 2026-12-25 → PASS (132 weekdays in range − 4 = 128).
- **STEP 3** — `git cat-file -t ea8ada59ea34cbba3b55c2bdaa1f72a5c0a58156` → blob;
  `git cat-file -t 71e153136d66dad02239325a6927510a965d7026` → blob;
  `git rev-parse 6fc028727a5a:engine/news_common.py` → `ea8ada59ea34cbba3b55c2bdaa1f72a5c0a58156`
  (assert PASS; commit `6fc028727a5a7e870242ab9296a89cac9a9c9b50` known locally);
  `git rev-parse 64ef5131a5f5:engine/news_common.py` →
  `71e153136d66dad02239325a6927510a965d7026` (assert PASS). `git diff ea8ada59… 71e15313…
  | grep -c '^[-+][^-+]'` → 132 changed lines in 4 hunks (`@@ -36,6 +36,7 @@ import math`;
  `@@ -155,6 +156,10 @@ _ROUNDUP_RE`; `@@ -738,6 +743,57 @@ def _profiles_names()`;
  `@@ -908,3 +964,94 @@ def gdelt_fetch(`). Direction pin→BASE, BASE *adds* the
  ticker-template/editorial classifier machinery the frozen pin lacks: functions
  `_profile_reference_names`, `company_reference_names`, `ticker_template_reason`,
  `ticker_editorial_reason`, constants `_TICKER_FACT_RE`, `_TICKER_TIMING_RE`, import
  `urllib.parse.unquote/urlsplit`. **Verdict:** the pin is RECOVERED (an exact git blob);
  its effect on the funnel is the census's claim — one item `92238f1f0606b57c` kept as
  not-low-value, funnel `low_value` 4 not 5, s1 `manifest.json` byte-identical to
  committed gated_v2 (`gated_v3/CENSUS.md` §2) — and the registered draw depends on it.
- **STEP 4** — `sha256sum $R3/bodies_v3/bodies.jsonl` →
  `59bbeb2251d4e1577003d2eb118672592651b6428904256b098039a04b98c86c` (required: same,
  and equal to `gated_v3/CENSUS.md` §10). `ls $R3/bodies_v3/texts | wc -l` → 575;
  `$W/b4/body_report.json` `texts_written` → 575. Walk of `bodies.jsonl`: 940 filing
  documents with `status:"available"`; 940 `<text_sha256>.txt` present in `texts/`,
  0 missing; 575 distinct `text_sha256` (940 available documents deduplicate to 575
  distinct texts). Input hashes vs `gated_v3/CENSUS.md` §1 Expected column:
  `items.parquet` OK, `event_log.parquet` OK, `reject_sample.parquet` OK,
  `ticker_cik_ledger.json` OK (values in the table above). **Verdict:** bodies are
  RECOVERED ON ONE HOST (ubuntu3), not in git, single copy; inputs are RECOVERED by hash
  against committed sources.
- **STEP 5** — no new commands; see the dedicated section above (source: `gated_v3/CENSUS.md` §1).
- **STEP 6** — `$W/boundary_counts.py` over `$W/b4/cases.jsonl` + `$R3/bodies_v3/bodies.jsonl`
  + `$R3/in/sessions.json`: relations `filed_after_seen` 277 / `filed_before_seen` 82 /
  `filed_same_session` 125; (a) 7, (b) 43, (c) 0, (d) 4, (e) 5 (lists above). Context
  counts: all 135 drawn cases `status:"available"`; window starts 2026-07-15..2026-10-09,
  ends 2026-07-22..2026-10-16, 5 ends >= 2026-10-14.
- Numbers quoted from the B4 lane's own census are cited as `gated_v3/CENSUS.md §n`:
  §1 inputs + reconstruction record + step-0c (1,202 checks), §2 pin deviation + s1
  identity, §3 body funnel (420 available), §5 draw window/seed/counters, §6 overlap
  (95 both / 40 NEW / 4 dropped), §10 host artifacts. The census's own verdict line is
  `PROVISIONAL pending seat ruling on the classifier pin` with gap = sessions.json
  RECONSTRUCTED (`gated_v3/CENSUS.md` header); this adjudication confirms the
  reconstruction half of that gap is still open (original not found) and that the pin
  itself is an exact recovered git blob.
