# Terminal IEX Historical Replay — M2 Studio local Codex release handoff

**Date:** 2026-10-24. **Original mission:** Mastermind Terminal PR [#1039](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1039), protected merge `61b84737df09653edc9a11c9c3e1886606abda05`; source head `c08dcb3266f819ef413e280c869ed835bee05787`. The original complete local handoff is also retained as `TERMINAL-IEX-CODEX-HANDOFF-2026-10-24.md` in this chat's generated artifacts (SHA256 `a5722d5390d7f0c69cc69d9c8574d069e7c90bd22cb7d7eb0d4463a5c5ab1bd5`). This is a **Codex execution packet**, not a publisher admission, secret, runtime receipt or authority to bypass host access.

## Accepted work and exact files

- PR #1039 merged into protected Terminal master, green hosted CI run `40077062713`. The public `/options/equity-replay` route returned 404 at the last release probe; do not call source merge a production deployment.
- Retained original IEX artifacts on m2studio: `/Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/iex-depth-replay-20261017/.large-trades-evidence/iex-depth-20261005-v3/`.
- Private, read-tested stage: `/Volumes/Mastermind/agent-workspaces/terminal/iex-1039-stage-20261024/`; manifest `private-publisher-manifest.json` SHA256 `41c8b0d748a05e2ed13cac7630526811b46b06831d765afb56871ce6308ccc73`.
- Only publishable payloads within `stage/large_trades/`: `NVDA.json` 430312 bytes SHA256 `8397753b7ffc3774282f672b012721fece3aea6b7ffd5622f298ae483d885b27`; `SPY.json` 404001 bytes SHA256 `4eff399a2ccd50f56ef017154bc4e98c5cbbcadd3a1e51a5c28e5205d523f77d`; `QQQ.json` 358741 bytes SHA256 `c2614e38eb9dbc98d2be2b9f345e0533da2cacd60ec801b3ffcfff94cc5db9ed`.
- Data is `IEX HIST DEEP+ 1.0`, equities in **shares**, IEX-only venue, 2026-10-05 historical session, archive acquired 2026-10-07. The selected cohort is **partial/truncated**, ~12:50–13:30 UTC and 480 observed sampled book rows/symbol. A different ~13:30–13:33 regular-session cohort exists separately and is **not** selected. Do not blend, substitute or describe either as full-session depth.
- Original retained decoder+source tests accepted. The exact three staged files passed the incumbent Terminal `terminal/lib/__tests__/iexDepthRealSource.local.test.ts` **4/4** with `IEX_DEPTH_REAL_DIR=<stage>/large_trades`. Real NVDA/SPY/QQQ 3-viewport browser tests **9/9**; compiled unsigned route and API privacy tested; those are local source tests, not subscriber proof.

## Previous denied and uncertain effects: preserve

- Original Fabric publication: `run_id=terminal-iex-1039-publish-20261024`, `root_id=terminal-iex-depth-replay-20261017`, `parent_id=terminal-iex-depth-replay-20261017`. Controller TERMINAL rc=1; provider `qwen3.8-flash` returned **HTTP 429** with `QWEN_FINAL_RESPONSE_UNCONFIRMED`; `accepted=false`, `retry_allowed=false`, **execution absence not proven**. Do **not** duplicate or retry this Fabric operation, change model, account, payments, credit limits or assume no effect without target reconciliation.
- The previous m2studio direct `root@146.190.142.17` SSH read-only probe was denied `Permission denied (publickey)`. Do not replay that principal, circumvent a denial or mint a new access path. A local Codex receiver needs its own pre-authorized, verified existing release carrier before any remote write.
- No new data publisher, scheduler, queue, SSH key, auth plane, entitlement grant or source acquisition may be created to shortcut publication.

## Canonical read contract and actual target

Terminal `terminal/app/api/large-trades/route.ts` via `terminal/lib/largeTrades/sourceAdmission.ts` reads **on the Terminal VPS**:
`$MACRO_LIVE_DIR/large_trades/{NVDA,SPY,QQQ}.json`,
default `/var/lib/macro-live/public/live/large_trades/{SYMBOL}.json`. Signed-out read requires denial; live customer authorization and source status are separate.

The M1 Macro `scripts/publish_r2.py` writes to R2 and **is not demonstrated** to write to this host-local directory. Find exactly one incumbent host-file publisher/atomic writer and its active lease, deployment target and authorization before selecting a carrier. The protected Terminal code release uses `/opt/terminal/terminal-build.sh --target-sha <full protected master sha>` with W2A preflight, and is **separate** from data publication. Do not copy local unmerged trees to VPS or treat a green GitHub run as installed.

## Local Codex execution procedure

1. Read protected Mastermind source law/current runtime state; inspect existing release/principal permissions and *real* `MACRO_LIVE_DIR` **read-only**. Check whether anything was affected by the unconfirmed Fabric operation. If the target already has these exact hashes, mark idempotent no-op and preserve receipts.
2. Prove source license/redistribution grant and required IEX attribution, original archive acquisition and decode receipt, availability clocks (never intraday before archive acquisition), exact manifest digest, sizes, SHA256 and non-symlink regular-file types; verify source stage has no unexpected files. Do not publish the private manifest or sidecars.
3. Verify the incumbent publisher's atomic cohort procedure, file ownership, lease and rollback. Before any modification record original target bytes/hashes/inodes and writer activity. Any foreign owner, permission refusal, unsettled effect, license uncertainty, changed target or absent publication mapping means **STOP WITHOUT WRITE**.
4. If and only if every authority/collision gate is satisfied, use the existing admitted publisher to atomically publish **the one selected three-file cohort** into `MACRO_LIVE_DIR/large_trades`, preserving the previous version via the incumbent rollback procedure. No partial mixed-cohort publication.
5. Read back *from the actual serving host* and verify per-file SHA256 matches the three inputs, owner, size, source scope, truncation flags and availability clocks. Record exact publisher operation receipt, lock and rollback point; do not claim results from staging or R2 alone.
6. Independently qualify the installed Terminal code SHA ancestry, `/options/equity-replay` route, authenticated real `/api/large-trades?sym=NVDA|SPY|QQQ` response digest and source state, guest 401/private/no-store, and visible historical replay in a real entitled browser. If permission is missing, record the *exact* missing release-carrier credential; do not impersonate a customer.
7. Return one truthful classification: `PUBLISHED_AND_READBACK_VERIFIED`, or `NOT_PUBLISHED` with exact blocker, source/target identities, effect uncertainty, and next responsible carrier. Update PR #1039 and Agent OS with actual receipts, not just a test.

## Separate NDX work, not a substitute

The existing Macro backfill `scripts/backfill_thetadata_eod.py --roots NDX,NDXP --start 20261023 --end 20261023 --dry-run` produced exactly two pending root-years without API calls. M1 Theta Terminal 25503 already responded for NDX/NDXP Greeks and OI on observed Oct 23 contracts; no local NDX/NDXP EOD shards or complete-chain receipts exist yet. NDX (AM settlement) and NDXP (PM) are separate contracts. Never substitute QQQ for NDX or treat missing data as measured zero. This collector/family integration is tracked in the corresponding draft Macro PR.

**Durability:** This text is staged in Macro `agentos/handoffs/` through the normal protected PR path. A branch file is not accepted protected main or a consumed local Codex assignment.
