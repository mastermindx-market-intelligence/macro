# Market-Intelligence Institutional Buildout — continuation handoff 2026-10-11 (W8)

Successor of `research/MARKET_INTELLIGENCE_BUILDOUT_CONTINUATION_HANDOFF_2026-10-06.md` (W1–W7).
Workstream record: `agentos/workstreams/WS-MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT.md` (W8 wave).
Handoff record: `agentos/handoffs/WS-MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT-2026-10-11.md`.
A cold stranger resumes from this file alone: read §2 (what is running and under which watcher), §3
(what is decided and must not be re-opened), §7 (what to do next), and only then §8.

## 0. Identity and mandate

- Seat: Fable Meta-CEO session `fd47d431` (Claude Code, worktree
  `/Volumes/Mastermind/claude-ssh-worktrees/macro-main-4a794e55c3bdbd60/mastermind-program-handoff-09cdd0`,
  records branch `claude/mi-records-wave5-20261011`).
- Program: Mastermind PR #1258 MERGED (owner-preserving integration overlay of umbrella issue #1202);
  op key `market-intelligence-institutional-buildout-20261004`.
- Mandate (Chairman, verbatim-critical, 2026-10-11): "Resume instead of getting blocked … take
  ownership and get them done since no one else is working on them … Use Suborchestrators natively
  with opus 5.5 and let them orchestrate subagent fabric workers and operators." Earlier directives
  stand: no Claude-native labor children; fabric lanes GLM Flash 5.3 → GLM 5.3 → Grok/Cursor → Opus
  last resort; limitations for the Chairman delivered LAST.
- Topology: seat → two Opus 5.5 orchestrators (`orchestrator` agent type, `fable-mode` skill) →
  GLM fabric lanes via `$K/ext/remote_sub.sh`. Orchestrators judge by artifact and return
  STATUS/RESULT/EVIDENCE/GAPS/DEVIATIONS; they never post, label, ready, merge, arm, or edit a PR
  body — those acts stay with the seat. Cap: 2 orchestrators; ORCH-OPS runs ≤3 fabric lanes,
  ORCH-N ≤2.

## 1. Wave plan and exit gates

| wave | content | exit gate | state |
|---|---|---|---|
| W1–W7 | foundation, contracts, writers, flags, receipts (10-06 file) | merged dark | DONE (merged) |
| W8-N | Package N live: Alpaca-sourced Benzinga headlines (#8809) → P2 VPS enable + canary → P1b minors → P3 Terminal rail | canary `live` with growing rows; anon `/terminal` `newsRailEnabled":true` at the same deployment id | #8809 MERGED `9b1da2b55e6e`; P2/P1b launching |
| W8-I | Package I flag on (#8811) | `/api/integrated-answer/v1/AAPL` 404 → 401 after the VPS pull + restart | CI GREEN; AER review RUNNING |
| W8-MM | market-memory unit recovery: #8807 massive manifest refresh, #8812 sentinel served cap, DX2 torn-pending discard, D-identity idempotent ingest, D-options pit EACCES tolerance + stage token | next SCHEDULED run of each unit logs success (or, for options, a stage token) | #8807 CI GREEN + review PASS; #8812 CI pending; DX2 + DID lanes RUNNING |
| W8-F | #7711 options-audit V2 charter judgment | charter satisfies WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2 and the seat's ten gaps; docs-only merge or REQUEST_REPAIR once | F docs lane RUNNING |
| W8-records | this file + handoff + three DEC records + WS update | PR merged, blob-verified | this PR |

## 2. Lane matrix (14:0xZ)

Scratchpad `$S` = `/private/tmp/claude-501/-Volumes-Mastermind-claude-ssh-worktrees-macro-main-4a794e55c3bdbd60-mastermind-program-handoff-09cdd0/fd47d431-d4f2-42b3-a4ba-a49c110094fa/scratchpad`;
orchestrator outputs `$S/../tasks/<id>.output`; fabric kit
`$K = ~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08`.

| lane | host / branch | PR · head | verdict · seat acts |
|---|---|---|---|
| ORCH-N (Opus `ad8bb35435bc5fe52`) | ledger `$S/orch_n_alpaca_ledger.md`, packet `$S/orch_n_alpaca_return.md` | — | P1 DELIVERED; seat MERGED #8809; "MERGED 9b1da2b55e6e" sent 14:0xZ → P2 + P1b |
| N build r2 / repair r3 | ubuntu1, `claude/mi-n-alpaca-provider-20261011` | #8809 · `1d8a481ce9f4` | MERGED `9b1da2b55e6e` (ready + `--match-head-commit` in one act; 10 paths blob-verified on origin/main) |
| N review r1 | ubuntu3 (independent host) | #8809 | `N-ALPACA-REVIEW: PASS 1d8a481c`, R1–R11, 0 blocker, 4 MINOR (M1–M4 → P1b) |
| N ci-pack0 heal r1 | ubuntu2, `claude/mi-ci-pack0-weight-heal-20261011` | (draft to open) · watcher `blwk9he3d` 150 s | curates the #8630 EVAL-1 step into its own `scope: exclusive` job; ceiling unchanged; seat readies + merges on its own green |
| N P2 (VPS enable + canary) | VPS `146.190.142.17` | — | launching; proof = unit active, canary `live`, rows growing across two reads ≥10 min apart |
| N P1b (M1–M4 minors) | fabric glm-5.3 build, own branch off fresh origin/main | — | launching (cap 2 with the heal lane) |
| N P3 (Terminal rail) | Terminal host drop-in `ticker-news-rail.conf` | — | after P2 canary; proof `newsRailEnabled":true` at `.deployment-id 707648d52014` |
| ORCH-OPS (Opus `a5ccb27d864b1f6cb`) | ledger `$S/orch_ops_ledger.md` | — | RUNNING; rulings 1–4 delivered (§3) |
| OPS-A | ubuntu3, `claude/mi-i-flag-on-20261011` | #8811 · `4efef9278b95` | CI GREEN 13:21Z (21 SUCCESS + 4 SKIPPED; merge-queue-pilot excluded); AER verdict pending → seat merges |
| OPS-B r2 + BR review | ubuntu2 / ubuntu0, `claude/mi-massive-manifest-refresh-20261011` | #8807 · `a8796d2fc08d` | CI GREEN 13:01Z, review PASS; needs `WS:MASSIVE-STOCK-DAY-R2-COHERENCE` citation in body (ONE edit) → seat merges |
| OPS-E | ubuntu3, `claude/mi-sentinel-served-cap-20261011` | #8812 · `ea289855c3b6` | DELIVERED PASS; CI watcher `b3wuf7do7` 300 s; AER verdict pending |
| OPS-AER | ubuntu1 (READ_ONLY, detached `4efef927` + `ea289855`) | #8811 + #8812 | RUNNING since 13:11Z, sentinel `bydk5viaj` |
| OPS-DX2 | ubuntu1, `claude/mi-w2c-torn-pending-recovery-20261011` | — | RUNNING since 13:21Z, sentinel `bwehgexg8`; spec §3 DX |
| OPS-DID | ubuntu1 | — | RUNNING (launched ~13:49Z) under DEC:MM-IDENTITY-INGEST-IDEMPOTENT-OVER-CAPTURED-DATES |
| OPS-F | ubuntu1, `claude/ssd-options-audit-v2-charter-e2c3a19ebf3198a0` (same PR) | #7711 · `cf25af32e3f3` pre-edit | RUNNING since 13:11Z, sentinel `byf837tak`; edits the charter only, push no-force |
| OPS D-options build | not yet launched (cap) | — | under DEC:MM-PIT-UNOWNED-PARENT-FSYNC-EACCES-IS-TOLERATED; launch when a slot frees |

## 3. DECIDED (do not re-open without a material invalidator)

Seat rulings (sent to the orchestrators, binding):
- **R-N-A (Option A):** merge #8809 as built; P1b minors as a follow-on beside P2; P3 after the
  canary. **R-N-MERGE (14:0xZ):** merge on the inherited `ci-pack-0` red. Evidence: PR delta 0 on
  all three packing probes (5799/5799, 5574/5574, 5534/5534); main at `e966b10b` (#8630) = 5802 and
  `4ac1abd0` = 5803 against the 5800 ceiling; main's own newest concluded ci.yml (38139442230 at
  `c8105785`) red on the same job name. The fleet law names main as the cause for such a red; the
  heal lane is the lever; waiting told nothing new.
- **R-OPS-1 (D-identity, option (a)):** ingest idempotent over captured dates; typed
  `upstream_rewrite_after_capture` receipt (line-start `::warning` print, `flush=True`); store
  refusal untouched; PIT correction class deferred OPEN. Tests T1–T3. Record:
  `DEC:MM-IDENTITY-INGEST-IDEMPOTENT-OVER-CAPTURED-DATES`.
- **R-OPS-2 (D-options, fix (b)):** `_ensure_store_directory_chain` tolerates EACCES on
  `root.parent` fsync only for a pre-existing root under a parent not owned by the effective uid;
  never chmod; plus a second commit adding a secret-free stage token (`stage=<credential|fetch|
  http_status_class|validate|persist>` + exception CLASS name) to the option-OI CLI fail-closed
  line. One PR, two commits, one independent review, cite
  `DSC:MASSIVE-OPTIONS-FLATFILE-ENTITLEMENT-REGRESSION`. Live proof = next SCHEDULED run's journald.
  401/403 class ⇒ vendor entitlement, EXACT_HUMAN_GATE. Record:
  `DEC:MM-PIT-UNOWNED-PARENT-FSYNC-EACCES-IS-TOLERATED`.
- **R-OPS-3:** #8807 cites `WS:MASSIVE-STOCK-DAY-R2-COHERENCE` (one body edit) before merge.
- **R-OPS-4:** #7711 judged once; the seat decides takeover; no second charter document.
- **Package N rights basis:** `DEC:TICKER-NEWS-ALPACA-BENZINGA-RIGHTS-BASIS` — headline tier only;
  body/image display needs a NEW receipt on a direct Benzinga contract, never an edit of this one.

ORCH-OPS diagnoses (verified read-only; do not re-diagnose):
- D0 no second charter; #7711 carries it, #7728 parked.
- D1 massive stock-day "store ticker count does not match the publish manifest" is a PRODUCT
  defect: the collector's already-current early return (`collectors/massive_stock_day.py:722-725`)
  never refreshes the committed manifest → fix = idempotent manifest refresh (#8807); publish_r2
  defense deliberately excluded.
- D2 breadth staleness is a PRODUCER gap (no nightly market commit since the 10-09 nightly);
  owner = daily.yml / prophet_rescue / outage issue #8748. No PR from this program.
- D3 experience-v1 + production-records timers are disarmed by `update.sh`
  `stop_reciprocal_market_memory_writers` as a CASCADE of D1 ("refusing W2C activation before
  owner replay completion"); #8807 is necessary to re-arm them; experience is additionally wedged
  on a torn pending file (DX).
- D4 production-records "owner source artifact exceeds its row bound" = CAPACITY CONTRACT
  (29,509 rows > `MAX_SOURCE_ROWS` 25,000 at `market_memory_production_records.py:76`,
  test-pinned); owner = `WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2` / #7711; never widen from here.
- D5 prophet_us/us_standouts INDETERMINATE = INSTRUMENT defect: `freshness_sentinel.py`
  `BODY_CAP=2_000_000` is an HTTP truncation guard reused by `read_served`, which reads whole files
  (5.2 MB prophet index) → #8812 adds `SERVED_BODY_CAP=16_000_000` for `read_served` only.
- D6 (corrected 12:4xZ) us_board_provisional "1 session behind | reader DARK" is producer-side:
  R2 object as_of 2026-10-09 built 2026-10-10T00:25Z with names=[]; close-pass only mirrors;
  the weekend gap is the Mon..Fri `Persistent=false` timer. Not a VPS defect.
- DX (D-experience) spec FROZEN: helper `_discard_torn_prepublication_pending` (digest ≠ name AND
  no final → unlink + dir fsync + one stderr `W2C_TORN_PENDING_DISCARDED {json}`); mismatch beside
  a final stays fail-closed; digest-bound non-JSON stays fail-closed; gated on the writer-lock
  ContextVar so lock-free read chains stay byte-identical (DX r1 STOP rule finding). Residual gap
  named, not fixed: a torn `*_HEAD` pending still trips the existence checks at :2350/:2402.

#7711 charter judgment (F; verdict GAPS, ten; strong parts kept: bounded streaming external-sort,
receipt contract, corrections/replay/NYSE boundary, frozen refusal vocabulary incl. RESOURCE_LIMIT,
8 acceptance tests incl. anti-vacuity and authority isolation):
- F-G1 STALE CENSUS (make-or-break): charter benchmarks 9,641 episodes / 7,843 h60 at `dea0a794`;
  live VPS 12:3xZ: episodes 29,509 rows / 45,982,874 B; h60 25,338 / 50,889,496 B; session 30,327 /
  100.5 MB.
- F-G2 LIVE BREACH of the "retained" 25,000-row / 48 MiB ceilings (29,509 > 25,000; h60 > 48 MiB);
  same 25,000 = `MAX_SOURCE_ROWS` → production-records capture fails today (D4).
- F-G3 no replacement growth envelope (rows + bytes per source, horizon at the measured rate) for
  acceptance fixture #6 and the WS objective.
- F-G4 refusal-before-kill ordering not explicit: v1 dies on `TimeoutStartSec=180` / `CPUQuota=50%`
  before its 4,096 refusal; the unit also carries `MemoryHigh=256M` / `MemoryMax=512M`, unmentioned.
- F-G5 citations by key missing: `DEC:W2C-V1-CONTEXT-OWNER-DECOUPLED-FROM-OPTIONS-AUDIT`,
  `DSC:OPTIONS-CONTEXT-AUDIT-V1-TIMEOUT-PRECEDES-4096-REFUSAL`,
  `DNR:KILL-OPTIONS-CONTEXT-AUDIT-OWNER-EVICTION`, `WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2`.
- F-G6 do_not_redo not enumerated as a binding section (no `_MAX_REFERENCES` widen, no unit-limit
  raise, no owner eviction/window/rotate/truncate, no swallow, no shadow writer).
- F-G7 self-asserted acceptance ("CHARTER ACCEPTED", "decision is now frozen") → must read
  PROPOSED / pending seat acceptance; implementation HELD (#7728 parked).
- F-G8 stale incumbent claim: #6691 is MERGED 2026-09-24, not "open, unstable".
- F-G9 editorial: "the h60 digest above is corrected" points below itself.
- F-G10 nulls printed: receipt must carry per-reason abstain/refusal/retrospective counts per source.
Disposition: GLM docs lane edits ONLY the charter file on the same branch/PR; seat decides takeover
from the return (refresh vs origin/main, four keys cited, docs-only merge if it satisfies the WS).

## 4. FACTS

- origin/main `9b1da2b55e6e` = #8809 squash (14:0xZ). Records branch base `734ab8571d48`.
- VPS `/etc/macro-live.env` holds both `ALPACA_API_KEY_ID` and `ALPACA_API_SECRET_KEY` lines
  (`grep -c` = 2; values never read). Terminal anon `/terminal` `newsRailEnabled":false`,
  `.deployment-id 707648d52014`. `/api/integrated-answer/v1/AAPL` = 404 pre-#8811.
- Fabric: `remote_sub.sh auto glm <packet_FILE> '~/lanes/repos/macro' glm-5.3`; launch policy needs
  `POOL_TASK_CLASS` (build/fix_build/execute additionally `POOL_ESCALATION_REASON` ≥12 chars);
  glm-5.3-flash allowed as cheap executor. ubuntu1 token cannot push `.github/workflows/`. Lane
  pushes that hit receive-pack HTTP 500 succeed via the Git Data REST API or `--no-thin`; verify by
  `ls-remote`.
- CI weight ceiling: `tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs`
  pins `templates/index.html` probe ≤ 5800; main is at 5803 since #8630/#8776; every ordinary PR
  is red on `ci-pack-0` until the heal lands and a main proof runs.
- Identity store last capture `mmidobs_707790b2` observed 2026-08-19T12:18:38Z; the nightly rewrote
  `data/symbol_directory/snapshots/2026-08-19.parquet` at 22:50Z the same day; ingest replays from
  the earliest date and raises at the store refusal (`market_memory_identity_store.py:1537`).
- Options store parent `/var/lib/macro-market-memory-options` root-owned 0710 by design
  (`app/deploy/README.md:74-80`); #5373 (`6e2c3f5e0c`, 2026-08-11T22:43Z) made the chain fsync
  `root.parent`; every option-OI capture since has died at `os.open` EACCES before persistence.
- Review MINOR findings on #8809 (P1b scope): M1 contract alpaca branch accepts source-absent
  payload (unreachable); M2 one invalid item fails its page/frame (same design as the Benzinga
  collector); M3 provider=alpaca not bound to receipt.provider (P2.b installs the alpaca receipt);
  M4 no-op `redact_secrets(str(exc))` at `collectors/alpaca_news.py:200`.

## 5. Lane recipes (B-kit)

```
cd "$K" && export CLAUDE_SESSION_ID=fd47d431-d4f2-42b3-a4ba-a49c110094fa
POOL_TASK_CLASS=build POOL_ESCALATION_REASON='C2_COMPLEX_BOUNDED: <why>' \
  bash ext/remote_sub.sh auto glm <packet_FILE> '~/lanes/repos/macro' glm-5.3
POOL_TASK_CLASS=review bash ext/remote_sub.sh auto glm <packet_FILE> '~/lanes/repos/macro' glm-5.3
```
Packet = frozen spec + owned files + tests + NOT DONE UNLESS + RETURN line; returns land in
`$K/ext/lanes/<id>.remote.stdout`; one watcher per lane at ≥150 s. Never bare `ls $K/ext/`; never
read credential files or shim logs.

## 6. OPEN — gates by owner

| package | gate | owner | this seat's move |
|---|---|---|---|
| N | P2 canary live + growing rows; P1b PR; P3 rail flip | ORCH-N | ready + merge P1b and the heal PR on their own green; verify P2/P3 proofs by artifact |
| I | AER verdict; merge; 404 → 401 live | ORCH-OPS → seat | merge #8811 on ACCEPT; curl proof after the 3-min pull |
| MM-B | #8807 body citation; merge; timers re-arm on next update.sh pass | seat | one body edit; merge; D3 cascade clears |
| MM-E | #8812 CI + AER | seat | merge on green + ACCEPT |
| MM-DX | DX2 PR | ORCH-OPS → seat | judge by artifact (ContextVar gate, byte-identical lock-free paths, T1–T5 + mutants) |
| MM-DID | D-identity PR | ORCH-OPS → seat | judge against DEC T1–T3; merge; proof = hourly run accrues past 08-19 |
| MM-DO | D-options PR | ORCH-OPS → seat | launch when a slot frees; judge; proof = next scheduled run |
| F | #7711 charter edits | ORCH-OPS → seat | takeover decision; docs-only merge or one REQUEST_REPAIR |
| W8-records | this PR | seat | merge, blob-verify |

## 7. NEXT (critical path first)

1. Merge this records PR (ARM LAST or hand-merge on concluded checks; the inherited `ci-pack-0`
   red applies here too until the heal lands — docs-only PRs trigger no pack checks).
2. ORCH-N: P2 canary → P3; P1b + heal PRs → seat ready + merge → blob-verify.
3. ORCH-OPS: AER → merge #8811 (then curl 401), #8807 (after citation), #8812; DX2 → DID → DO
   PRs → merge → scheduled-run proofs; F → takeover decision.
4. ONE #1202 checkpoint at the W8 boundary; memory update; `SESSION END: <STATE>`.

## 8. Blocker list for the Chairman (deliver LAST, verbatim-safe)

Human-only, unchanged by any orchestration:
- `/mcp` OAuth for `mastermind-executive`, `linear-server`, `plugin:figma` (Executive ingress and
  Linear projection stay dark until authorized).
- A direct Benzinga contract ONLY if body/image display on the Terminal rail is wanted; headline
  display is live under the Alpaca receipt without it.
- Vendor entitlement for option-OI ONLY if the stage token on the next scheduled run reads an
  HTTP 401/403 class.
- Package R under #8438, ITP GAP-E-BASIS/ALIAS, and F2–F5 (C19 `req-4a8daf76317cfe92f436991444c58281`)
  remain with their named owners outside this program.
