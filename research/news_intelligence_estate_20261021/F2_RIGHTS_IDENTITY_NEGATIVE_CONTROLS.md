# F2 negative controls — rights, security identity and source independence (2026-10-31)

Lane NEWS-W3-F2-RIGHTS (Fabric, seat 602cd180 parent run w3-seat-direct-20261031),
executing MASTERPLAN §7.F row F2 (line 387: "Break consequential claims with actual
negative controls; reviewer independent of author"), axis RIGHTS, IDENTITY AND
INDEPENDENCE. Base HEAD: `6ff08d8e1b093b89a0b7798d6880f7ba2ea25756` on
`lane/news-w3-f2-rights-identity-r1`.

## Independence and scope

This lane authored none of the target modules (`engine/qbus_news_receipts.py`,
`engine/qbus_news_store.py`, `engine/qbus_news_reducer.py`, `engine/qbus_news_cluster.py`,
`engine/qbus_news_quality.py`, `engine/qbus_news_contract.py`, `engine/qbus_news_universe.py`,
`engine/news_impact/issuer.py`, `app/ticker_news.py`); every input is synthetic
(`SYNTH-*` placeholders, fixed ISO-8601 instants in 2026), every SQLite file, receipt,
ledger and universe file lives under `--scratch`, and no network, model or provider call
is made. No real receipt, ledger, news database, data file or credential on the host was
opened. The seat re-runs the control script itself; a control whose output does not
reproduce is rejected. The one BROKEN result below is the intended shape of this lane's
work: finding it is success, not failure. No repair, owner, schema or activation is
proposed here (NO DESIGN).

## How to reproduce

```
PYTHONPATH=. python3 research/news_intelligence_estate_20261021/f2_controls/nc_rights_identity.py --scratch /tmp/nc-rights-any
```

Run twice and compare the first three space-separated fields per line; verdicts are
deterministic. Exit code is 0 unless the script itself crashes.

## Control results

| ID | Attack (MASTERPLAN line) | Claim attacked (F1 or estate doc path:line) | Target (path:line) | Verdict | Observed (script line) |
|---|---|---|---|---|---|
| R01 | expired receipt grants nothing (§9.3:505) | engine/qbus_news_receipts.py:6; F1:76 open obligation "prove corrections and rights changes" | engine/qbus_news_receipts.py:117,202,474 | HELD | `code=rights_expired file_load=True set=0` |
| R02 | future receipt grants nothing (§9.3:505) | engine/qbus_news_receipts.py:6 | engine/qbus_news_receipts.py:117 | HELD | `code=rights_not_effective` |
| R03 | wrong audience grants nothing (§9.3:505) | engine/qbus_news_receipts.py:6 | engine/qbus_news_receipts.py:117,202 | HELD | `code=rights_audience_not_permitted file_load=True` |
| R04 | revocation denies next decision; reads re-checked per call (§9.3:505; §9.1:477; P0-C:156) | F1:76/F1:77 NewsReadRights gate | engine/qbus_news_receipts.py:474; engine/qbus_news_store.py:1751,1923,2104 | HELD | `grant=True read_before=True revoked_set=0 read_after=False` |
| R05 | equivalent renewal: no gap, broadens nothing, no model call (P0-C:156) | engine/qbus_news_receipts.py:6; app/ticker_news.py:344 | engine/qbus_news_receipts.py:117,454 | HELD | `fields_equal=True edge_access=True teaser_stays_denied=True` |
| R06 | duplicate receipts may only narrow, order-independent | engine/qbus_news_store.py:129-131 ("Duplicate receipts may only narrow") | engine/qbus_news_store.py:129; engine/qbus_news_receipts.py:454,474 | HELD | `allows_both_orders=(True, True, False) receipt_set_denies=True` |
| R07 | source outside allowed set / field outside {title,url,teaser} denied | engine/qbus_news_receipts.py:6; engine/qbus_news_store.py:129-131 | engine/qbus_news_store.py:129; engine/qbus_news_receipts.py:186 | HELD | `other_source=True body=True teaser_cap=False_denied=True unknown_field=True` |
| R08 | store reads honour rights; hidden source never leaks in rows/titles/urls/teasers/aggregates | F1:76 row 1 (read path store.py:1751-1830); F1:77 row 2 | engine/qbus_news_store.py:784,798,1751,1923,2104 | HELD | `beta_leak=False sources_alpha_only=True flow24_alpha=2_both=3 cluster_sizes_rights_scoped=True` |
| R09 | rights withdrawn -> served path refuses (503) before any read; renewal slice makes no model call (§9.1:477; P0-C:156) | F1:77 row 2 (app/ticker_news.py:583 gate) | app/ticker_news.py:344,614,689,848 | HELD | `served200=True expired503=True story503=True removed503=True annotations_not_permitted=True` |
| R10 | ticker reuse: one ticker -> issuer A until a date, B after; never "current" (§5.2:245; §9.3:506) | MASTERPLAN:245 "Ticker text is a display label"; F1:76 | engine/news_impact/issuer.py:98,291,331,339; app/ticker_news.py:288 | HELD | `ledger=cik:0000000001/cik:0000000002/cik:0000000002 overlap_absent=True universe=SYN-AAA/SYN-BBB ambiguous_refused=True canon=('SYNQ', 'SYNQ-B')` |
| R11 | issuer/ticker mismatch and delisting: explicit identity or typed absence, never a guess (§9.3:506) | engine/news_impact/issuer.py:10-13 ladder contract | engine/news_impact/issuer.py:339,502 | HELD | `mismatch->explicit_cik=cik:0000000001 note_recorded=True delisted_absent=not_listed_at_asof typed_absence=unjoinable_filing_identity` |
| R12 | copied/mirrored wire is one information family (§5.4:259) | MASTERPLAN:259; reducer mirror domain | engine/qbus_news_reducer.py:72,189-230; engine/qbus_news_store.py:1233 | HELD | `stories=2 counts=[(1, 1, 1), (1, 2, 2)] mirror_disposition=dup1 source_counts=[1, 1]` |
| R13 | Benzinga via Alpaca is not independent (§2.2:97) | MASTERPLAN:97 "Different transports ... do not create independent corroborating sources" | engine/qbus_news_contract.py:379; engine/qbus_news_reducer.py:194 | HELD | `inserted=1+0 duplicate=1 states=1 reports=1` |
| R14 | over-merge: near-identical titles, different items/tickers/times stay separate (§9.3:503) | F1:76; MASTERPLAN:503 | engine/qbus_news_cluster.py:347; engine/qbus_news_store.py:1233 | HELD | `cross_ticker_stories=2 same_security_stories=3 member_counts=[1, 1, 1]` |
| R15 | cluster/group id is never independence; exposed source count on syndicated copies (§5.4:259-261; §9.1:475) | MASTERPLAN:259-261; MASTERPLAN:475 "copied wires do not inflate corroboration" | engine/qbus_news_store.py:1900,2160; engine/qbus_news_quality.py:28 | **BROKEN** | `identical cross-outlet wire=1 story but source_count=2 evidence_source_count=2 reporting_state=no_material_difference` |
| R16 | combined receipts share no fields across sources (added: weakness probe) | app/ticker_news.py:344-346 ("without sharing fields across sources") | engine/qbus_news_receipts.py:454 | HELD | `benzinga_teaser=True massive_teaser=False both_orders_agree=True` |
| R17 | malformed source identity / provider mismatch fails closed (added: weakness probe) | engine/qbus_news_receipts.py:6 | engine/qbus_news_receipts.py:128-134,151 | HELD | `codes=['rights_provider_mismatch', 'rights_source']` |

`NC SUMMARY held=16 broken=1 no_mechanism=0 untestable_env=0 total=17` (16 executed
non-env controls ≥ the required 12).

## BROKEN findings

### R15 — the only per-story source count the estate exposes counts syndicated outlets, not information families

- **Minimal reproduction** (run from repo root; identical title+teaser published by two
  different outlets under different item ids and per-outlet URLs, routed to one security,
  then read through the public store API):

  ```
  PYTHONPATH=. python3 -c "
  from datetime import datetime, timezone
  from pathlib import Path
  import tempfile
  from engine.qbus_news_contract import normalize_massive_news
  from engine.qbus_news_store import NewsReadRights, NewsStore, RoutedRevision
  scratch = Path(tempfile.mkdtemp(prefix='r15-minirepro-'))
  def rev(item, domain, received):
      return normalize_massive_news({'id': item, 'publisher': {'homepage_url': f'https://{domain}'},
          'published_utc': '2026-10-14T09:00:00Z', 'article_url': f'https://{domain}/synth-sy',
          'title': 'SYNTH-TITLE-SYNDICATED-WIRE', 'description': 'SYNTH-TEASER-SAME', 'tickers': ['SYNTH']},
          received_at=received)
  UTC = timezone.utc
  a = rev('SYNTH-SY-A', 'outleta.example.com', datetime(2026,10,14,10,0,tzinfo=UTC))
  b = rev('SYNTH-SY-B', 'outletb.example.com', datetime(2026,10,14,10,5,tzinfo=UTC))
  store = NewsStore(scratch/'mini.sqlite3', source_key='SYNTH-KEY')
  store.commit_observations([RoutedRevision(revision=r, security_ids=('SYNTH-SEC-15',), universe_revision='SYNTH-UNI-R1') for r in (a,b)])
  rights = NewsReadRights(allowed_sources=frozenset({'massive:outleta.example.com','massive:outletb.example.com'}))
  reader = NewsStore.open_readonly(scratch/'mini.sqlite3', source_key='SYNTH-KEY')
  snap = reader.snapshot('SYNTH-SEC-15', limit=10, cursor=None, rights=rights)
  story = reader.story(snap.rows[0].story_id, rights=rights)
  ev = reader.evidence_for_security('SYNTH-SEC-15', limit=10, rights=rights)
  print('clusters', len(snap.rows), '| members', story.item_count, '| story.source_count', story.source_count,
        '| evidence source_count', ev['stories'][0]['source_count'], '| identical title+teaser:', a.title==b.title and a.teaser==b.teaser)"
  ```

  Observed: `clusters 1 | members 2 | story.source_count 2 | evidence source_count 2 | identical title+teaser: True`
  (executed verbatim at `$W/r15-minirepro/`, output above).

- **Exact code line that produces it**: `engine/qbus_news_store.py:2160`
  (`source_count = len({publisher_identity(str(row["source"]), str(row["url"])) for row in rows})`
  in `story()`; the same expression in `snapshot()` at `engine/qbus_news_store.py:1900`,
  surfaced through `evidence_for_security` at `engine/qbus_news_store.py:1967`
  (`"source_count": detail.source_count`) and `StoryRow.source_count` into the
  `/api/ticker-news` payloads). `publisher_identity`
  (`engine/qbus_news_quality.py:28-39`) collapses only same-domain items and
  Benzinga transports (`benzinga` -> `benzinga.com`); two distinct syndicating
  domains remain two identities.

- **Claim it contradicts**: MASTERPLAN §5.4:259-261 — "A copied wire is one
  originating information family. Ten outlets do not create ten independent
  confirmations. Distinguish genuinely independent reporting, official confirmation
  and syndicated repetition." — and §9.1:475 ("copied wires do not inflate
  corroboration"). The clustering itself is correct (one story, `item_count=2`);
  the *only* per-story source aggregate the estate exposes (`source_count`) is
  outlet-count, so a byte-identical syndicated wire surfaces as `source_count=2`
  with `reporting_state=no_material_difference`. No exposed field distinguishes
  syndicated repetition from independent reporting; the collapse mechanisms that do
  exist (reducer mirror domain `engine/qbus_news_reducer.py:72`, same-publisher
  identity `engine/qbus_news_quality.py:28`) are transport/publisher-scoped, which
  R12 and R13 confirm HELD. The finding is scoped exactly to cross-publisher
  syndication, consistent with MASTERPLAN:99 ("no natural fuzzy cross-publisher join
  was observed ... useful natural cross-publisher grouping still needs measured
  evidence").

- Repair is out of scope and belongs to a later seat-commissioned build lane.

## NO_MECHANISM findings

None. Every attacked property had an executable code path; the two probes that could
have been absences (already-materialised output withdrawal in R04; a syndication-aware
count in R15) resolved to "no read path bypasses rights re-evaluation" (HELD) and a
BROKEN exposed count respectively. No `NO_MECHANISM` grep proofs were needed.

## Existing author coverage (mapped, not counted; author tests are never F2 evidence)

| Target | Author test file (count) | Nearest `def test_` | What the F2 control goes beyond it |
|---|---|---|---|
| engine/qbus_news_receipts.py | tests/test_qbus_news_receipts.py (20) | `rights_refuse_wrong_status_source_audience_or_time` (:81), `rights_file_loader_missing_invalid_or_expired_is_none` (:122), `rights_never_infer_teaser_or_source_link_permission` (:100) | R01-R03 use fixed injected `now` after expiry/before effect and assert the parse code plus file/set loaders together; R04 drives revocation through to store reads; R05 checks the exact `expires_at` instant boundary and field-by-field equality; R06 order-independence at both `NewsReadRights` and receipt-set level; R16 cross-source isolation both orders |
| engine/qbus_news_store.py reads | tests/test_qbus_news_store_api_reads.py (9) | `story_returns_grouped_active_members_and_respects_field_rights` (:155), `changes_for_security_does_not_leak_other_tickers` (:127), `snapshot_query_count_is_constant_with_many_clusters` (:242) | R08 hides a whole second publisher and scans snapshot+story+evidence+flow+changes aggregates (blob scan for the hidden source's domain/teaser/item id), not single-source field rights on one ticker |
| store clustering | tests/test_qbus_news_store_clusters.py (9) | `near_duplicate_provider_items_render_as_one_cluster_row` (:69), `same_words_different_security_do_not_cluster` (:88), `material_number_difference_stays_two_stories` (:115), `relevant_candidate_outside_event_window_remains_separate` (:228) | R14 combines the three over-merge axes (cross-ticker identical, number-conflict, 12h window) in one store; R12/R15 assert the *exposed* `source_count` on syndicated members, which author tests do not |
| engine/qbus_news_cluster.py | tests/test_qbus_news_cluster_adversarial.py (53) | `identical_syndicated_headline_joins` (:119), `different_subject_security_ids_do_not_join` (:85), `outside_window_seconds_does_not_join` (:102) | exercised only through the store commit path (R12/R14/R15); no direct pure-matcher control was needed |
| engine/news_impact/issuer.py | tests/test_news_impact_issuer.py (27) | `registry_is_point_in_time_on_a_handoff_ticker` (:197), `delisted_at_asof_is_not_listed_at_asof` (:226), `ambiguous_ticker_lists_every_candidate` (:217), `explicit_cik_wins_over_conflicting_ticker` (:151), `canonical_ticker_one_documented_rule` (:123), `load_ledger_dated_shapes` (:378) | R10 walks one reused ticker across the `valid_to`-exclusive boundary day in a single synthetic ledger and drives the app-side `_security_for_ticker` binding with the same reuse plus an overlap-refusal probe; R11 combines mismatch + delisting and checks the rendered typed-absence payload |
| engine/qbus_news_universe.py | tests/test_qbus_news_universe.py (7) | `membership_windows_and_row_knowledge_are_point_in_time_filtered` (:74), `ambiguous_provider_alias_across_active_securities_holds_universe` (:91) | R10 reaches the qualify path through `app/ticker_news.py:288` with disjoint-window alias reuse, not the pure function alone |
| app/ticker_news.py | tests/test_ticker_news_api.py (21), tests/test_ticker_news_receipt_binding.py (8) | `unknown_source_rights_fail_closed_before_store_open` (:128), `story_detail_respects_store_rights_and_missing_story_is_404` (:174), `sse_revalidates_access_after_cached_read_before_delivery` (:412), `api_rights_binding_fails_closed_on_expired_receipt` (:82) | R09 drives the served snapshot and story functions end-to-end against a synthetic store through withdrawal by expiry AND by file removal, and asserts the derivative-annotation flag stays `not_permitted` (the P0-C:156 no-model-call slice) |

No repo test suite was run by this lane.

## Gaps

- R09 exercised the route functions directly (offline lane; no HTTP server, no real
  sign-in). Installed/production/authenticated-journey verticals are F3's scope, not
  F2's; the observed 200/503 behaviour is the function-level served path.
- The app-layer receipt window (R09) is validated against the host clock inside
  `_current_rights_receipts` (`app/ticker_news.py:341`); the synthetic window
  2026-10-01..2026-12-31 is deterministic on the run day, and every parse-level
  control (R01-R07, R16, R17) injects a fixed `now`.
- `NewsStore.counts()` (`engine/qbus_news_store.py:995`) takes no rights parameter;
  its only caller at HEAD is `scripts/verify_ticker_news.py:177` (operator
  verification), not a rights-gated consumer read path — recorded as a scoped
  observation, not a leak verdict.
- `snapshot.change_sequence` (`engine/qbus_news_store.py:1780`) is a store-global
  watermark over all sources (documented as an opaque delivery cursor); it can
  reveal total change volume but never source identity, titles, urls or teasers —
  recorded, not BROKEN.
- `derivative_permitted` (`engine/qbus_news_annotate.py:73`) re-reads the receipt
  file without re-checking expiry; it is unreachable through served routes because
  `_rights_or_503` (`app/ticker_news.py:614`) raises 503 first (R09 observed the
  refusal). Recorded as an observation from R09.
- Natural cross-publisher grouping remains unproven at HEAD (MASTERPLAN:99); R15's
  BROKEN finding is consistent with, and sharpens, that recorded estate gap.

## Evidence

STEP 0 (fence checks):

```
$ git rev-parse HEAD
6ff08d8e1b093b89a0b7798d6880f7ba2ea25756
$ git status --porcelain
(empty)
$ test "$(git branch --show-current)" = "lane/news-w3-f2-rights-identity-r1" && echo BRANCH_OK
BRANCH_OK
$ W=~/lanes/tmp/news-w3-f2-rights-identity-r1; mkdir -p $W; df -Pk $W | tail -1
/dev/nvme0n1p4  1392233480 664444044 699461500      49% /
$ python3 --version
Python 3.12.3
$ python3 -c "import fastapi, starlette, jsonschema" && echo IMPORT_OK
IMPORT_OK          # -> PY=python3 (system env already has the pins; no venv needed)
                    # jsonschema 4.26.0 (requirements.txt:14), fastapi 0.143.3,
                    # starlette 1.8.0, httpx 0.28.1, pydantic 2.14.1 (pip list)
```

STEP 1: MASTERPLAN anchors read before writing anything — `sed -n 241,265p`
(§5.2 time/identity incl. :245, §5.3 :251-257, §5.4 :259-265), `sed -n 150,157p`
(P0-C, :156), `sed -n 95,100p` (:97), `sed -n 382,390p` (§7.F row F2 :387),
`sed -n 465,515p` (§9.1 incl. :475/:477, §9.3 :501-511); F1 matrix
`sed -n 64,120p` (rows 1-2 at F1:76-77). Every TARGET mapped with
`grep -n "def \|class "` and line-ranged reads of each exercised function. Author
test counts: receipts 20, store_api_reads 9, cluster 13, cluster_adversarial 53,
store_clusters 9, universe 7, universe_snapshot 14, news_impact_issuer 27,
ticker_news_api 21, ticker_news_receipt_binding 8, ticker_news_private_errors 16
(names mapped above; never run, never counted as F2 evidence).

STEP 2: no venv required (STEP 0 import succeeded); `PY=python3`.

STEP 3: script written to
`research/news_intelligence_estate_20261021/f2_controls/nc_rights_identity.py`
(standard library + repo modules only; `--scratch DIR`, default `tempfile.mkdtemp()`;
all sqlite/receipt/ledger/universe files under scratch; fixed 2026 instants; one
`NC <ID> <verdict> <observed>` line per control).

STEP 4:

```
$ python3 -m py_compile research/news_intelligence_estate_20261021/f2_controls/nc_rights_identity.py
(no output; COMPILE_OK)
$ PYTHONPATH=. python3 research/news_intelligence_estate_20261021/f2_controls/nc_rights_identity.py --scratch $W/run1 > $W/run1.txt 2>$W/run1.err   # exit=0, run1.err empty
$ PYTHONPATH=. python3 research/news_intelligence_estate_20261021/f2_controls/nc_rights_identity.py --scratch $W/run2 > $W/run2.txt 2>$W/run2.err   # exit=0, run2.err empty
$ diff <(cut -d' ' -f1-3 $W/run1.txt) <(cut -d' ' -f1-3 $W/run2.txt)
(empty — verdicts deterministic)
$ git status --porcelain
?? research/news_intelligence_estate_20261021/f2_controls/
(only the owned path; nothing written into tracked repo files)
```

`$W/run1.txt` verbatim:

```
NC R01 HELD code=rights_expired file_load=True set=0
NC R02 HELD code=rights_not_effective
NC R03 HELD code=rights_audience_not_permitted file_load=True
NC R04 HELD grant=True read_before=True revoked_set=0 read_after=False
NC R05 HELD fields_equal=True edge_access=True teaser_stays_denied=True
NC R06 HELD allows_both_orders=(True, True, False) receipt_set_denies=True
NC R07 HELD other_source=True body=True teaser_cap=False_denied=True unknown_field=True
NC R08 HELD beta_leak=False sources_alpha_only=True flow24_alpha=2_both=3 cluster_sizes_rights_scoped=True
NC R09 HELD served200=True expired503=True story503=True removed503=True annotations_not_permitted=True
NC R10 HELD ledger=cik:0000000001/cik:0000000002/cik:0000000002 overlap_absent=True universe=SYN-AAA/SYN-BBB ambiguous_refused=True canon=('SYNQ', 'SYNQ-B')
NC R11 HELD mismatch->explicit_cik=cik:0000000001 note_recorded=True delisted_absent=not_listed_at_asof typed_absence=unjoinable_filing_identity
NC R12 HELD stories=2 counts=[(1, 1, 1), (1, 2, 2)] mirror_disposition=dup1 source_counts=[1, 1]
NC R13 HELD inserted=1+0 duplicate=1 states=1 reports=1
NC R14 HELD cross_ticker_stories=2 same_security_stories=3 member_counts=[1, 1, 1]
NC R15 BROKEN identical cross-outlet wire=1 story but source_count=2 evidence_source_count=2 reporting_state=no_material_difference
NC R16 HELD benzinga_teaser=True massive_teaser=False both_orders_agree=True
NC R17 HELD codes=['rights_provider_mismatch', 'rights_source']
NC SUMMARY held=16 broken=1 no_mechanism=0 untestable_env=0 total=17
```

BROKEN re-derivation by hand (R15, `$PY -c`, printed in full under
"BROKEN findings"): `clusters 1 | members 2 | story.source_count 2 | evidence
source_count 2 | identical title+teaser: True`.
