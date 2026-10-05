# 08 — Execution checkpoint — 2026-10-05

**Parent:** Research Vault AI Intelligence Fabric / PR #8438  
**Protected procedure pin used for this checkpoint:** Mastermind `7eac3ec252475600147ec9a376b8ca16403ac4c5`, Skillpack 1.0.1  
**Observed Macro main during F4 source work:** `dc59164faa9c7126115dc5f3aaba6984560b421a`  
**State:** execution has begun; the parent mission is **not complete**.

This checkpoint records verified capability movement after the original planning packet. It does not claim Fable pickup, production deployment, private ChatGPT installation, Deep Research acceptance, or Research Vault source recovery.

## 1. Verified completed source increments

### F1 — private R2 isolation: MERGED / source-level

PR #8442 merged as:

`94228ca2555c898a183e9d6f99c23e8eeefd5f64`

The canonical Research Vault store now fails closed instead of silently inheriting generic shared/public R2 credentials, and rejects research/shared bucket aliasing. The dedicated Research Vault contract check was green before merge.

This is **source-level isolation**, not proof of live Cloudflare bucket policy, credential scope, deployment, or readback.

### F2 — body-health census + read-only operator lane: MERGED / source-level

PR #8443 merged as:

`1d0c17cf298643e3d62a1632815decc8bef74691`

The incumbent census now distinguishes:

```text
identity completeness
    !=
retrieval/body completeness
```

It measures non-empty/empty bodies, text-layer state, PDF-hash coverage, source-vs-stored character relation, page-boundary coverage, excerpt derivability, and typed bodyless exclusions.

It also adds a separate manual-only `research-vault-census.yml` proof lane with:

- `contents: read`;
- main-only execution;
- separate non-cancelling concurrency;
- dedicated Research R2 secrets;
- no ingest/publisher/git-write path.

A **real live F2 census receipt has not yet been executed/accepted in this checkpoint**.

### RIO correctness prerequisite: MERGED

The former #7461 claim-array identity repair landed through #8446 before this checkpoint base.

Do not redo the structural claim-index repair.

### MarketDesk release-lineage prerequisite: MERGED

PR #8452 merged as:

`8cf8f73296e2b5465048606016a0c49a8886b8aa`

It separates immutable September recovery provenance from the evolvable current release manifest/receipt, allowing F4 runtime source to change without rewriting historical recovery evidence.

## 2. F4 producer diagnosis — materially narrowed

The stale Research Vault source is not an hourly-ingest outage.

Observed catalog history:

```text
2026-09-24 09:27Z generation: count 2771
2026-09-24 10:12Z generation: count 2772
2026-09-24 10:42Z generation: count 2773
2026-09-24 11:57Z generation: count 2777
2026-09-24 12:12:47Z generation: count 2778
later generations: count remains 2778
latest report published_at: 2026-09-24T09:28:05Z
```

Catalog publication continued repeatedly through October 4, so the defect is upstream of the hourly Research Vault ingester:

```text
MarketDesk producer/runtime
        ->
private Research R2 inbox
        ->
research-ingest
```

The last two stages continued publishing an unchanged corpus/catalog.

## 3. Strong recurrence class: auth-required producer can remain alive

Historical incident #6862 established an accepted prior failure with the same external symptom:

- hourly ingest kept republishing an unchanged catalog;
- canonical Mac13,1 producer remained present;
- MarketDesk persistent session had expired;
- recovery required stopping the single-writer producer and interactively re-authenticating the existing profile.

Current source inspection proves the recurrence mechanism still existed before F4 repair:

1. `MarketDeskClient` correctly raises `SessionExpired`.
2. `trickle.run_tick()` catches it and sets the account `authed=False`.
3. discovery also parks an expired account as unauthenticated.
4. the main trickle loop then continues indefinitely.
5. the dead-driver watchdog does not fire because an unauthenticated account makes no download attempts.
6. `research-feed` historically checked only whether a `marketdesk trickle` process existed.
7. therefore **alive process != authenticated producer**.

This does not prove the current Mac13,1 profile is presently expired; the native host tunnel was unavailable during this diagnosis. It proves a real observability defect and a strong recurrence hypothesis.

## 4. F4 source recurrence repair — ACTIVE

Draft PR #8472:

**fix(marketdesk): expose producer auth-required state**

Head at creation:

`4df909395c2ef2bd1e4c27f23051940b3823c54a`

The PR keeps health inside incumbent owners:

```text
com.mastermindx.research-trickle
        |
        | existing SQLite meta KV
        v
AUTHENTICATED / AUTH_REQUIRED / UNKNOWN
        |
        +--> marketdesk status
        |
        +--> existing read-only feed_probe
                  |
                  v
          existing research-feed
```

It does **not** create a new monitor, database, scheduler, auth service, profile, bucket, queue, or publication plane.

Re-authentication remains human-only/single-writer.

Current release manifest verification performed before PR creation:

```text
current manifest sha256:
11951aca2172a5ec55ff69ed21d26ccb6af35e8ac2a54635f5dd11fd6e44133a

immutable recovery manifest:
6209be070fbdfe8b8269bb62c0b6f466dac9b425ba1e9244b9b1bf7d983ba602
```

All nine changed payload files matched their current `SHA256SUMS` entries and the release receipt matched the manifest digest.

At the first bounded CI read:

- PR mergeable;
- `ci-authority/main`: success;
- general fence pack / contract delta still running;
- one auxiliary merge-queue pilot check was red;
- no production acceptance claimed.

Do not poll unchanged CI merely to extend execution.

## 5. F5 exact full-text identity/segment contract — ACTIVE, do not duplicate

Draft PR #8453 already implements the pure contract:

`engine/research_vault/fulltext.py`

with:

### `research_vault.extracted_text.v1`

- report id;
- source PDF SHA-256;
- extractor identity/version;
- extracted UTF-8 text SHA-256;
- exact char/byte counts;
- measured page count;
- literal form-feed byte boundaries;
- text-layer state;
- exact private text.

### `research_vault.segment.v1`

- source PDF identity;
- extracted-text identity;
- segmenter version;
- explicit byte budget;
- deterministic segment index;
- exact UTF-8 byte offsets;
- page start/end;
- segment text SHA;
- exact replay;
- literal private segment text.

Current main has no competing `fulltext.py`; #8453 is mergeable and path-disjoint from later main movement at this checkpoint.

Do not create a second chunk/segment abstraction.

## 6. Current critical dependency DAG

```text
F1 source isolation        MERGED
        |
F2 census tooling          MERGED
        |
        +--> LIVE F2 census receipt still owed
        |       |
        |       +--> F3 measured corpus repair class
        |
        +--> F4 producer freshness
                |
                +--> #8452 lineage prerequisite MERGED
                +--> #8472 auth-health source ACTIVE
                +--> Mac13,1 live diagnosis HUMAN/HOST GATE
                +--> re-auth only if exact profile proven expired
                +--> natural-report recovery proof

F5 exact text/segment contract  #8453 ACTIVE
        |
        +--> production materialization waits on measured corpus truth
```

## 7. Exact next actions

### Independent source/review work

1. Consume #8472 hosted CI once its material checks return; repair only discriminating failures.
2. Review #8453 against the PDF/text identity law and accept/salvage rather than duplicate it.
3. Run the real read-only F2 census through the dedicated operator lane when its merged workflow can be safely dispatched.
4. Classify F3 from that receipt:
   - missing corpus rows;
   - existing rows with unusable bodies;
   - typed no-text scans;
   - mixed.

### Exact host/human gate for F4

When the authorized Mac13,1 host carrier is available:

1. read current `com.mastermindx.research-trickle` and `com.mastermindx.research-feed` launchd state;
2. read current trickle/feed logs;
3. read MarketDesk SQLite producer auth meta/status;
4. prove whether the exact existing persistent profile is authenticated;
5. if expired, stop the existing single-writer trickle daemon;
6. run interactive `marketdesk auth` on the same profile;
7. install the accepted release through the incumbent installer;
8. restart the same existing LaunchAgents;
9. prove a natural new report traverses:
   `MarketDesk -> vault publish -> Research R2 inbox -> ingest -> catalog/corpus -> API/product`;
10. prove Research Vault source freshness becomes `SOURCE_FRESH`.

No alternate producer/profile/scheduler/bucket/database may be created to bypass this gate.

## 8. Fable handoff effect

The original Fable packet remains useful, but a new Fable principal should **not** restart at F1.

Its current start frontier is:

```text
consume merged F1/F2/#8452
        ->
review/finish #8472 + #8453
        ->
obtain live F2 census
        ->
F3 measured repair
        ->
host/human F4 proof
        ->
full-text materialization / canonical Research Read port
```

Fable remains justified for the cross-boundary integration and acceptance work. Routine source/test implementation should remain delegated/least-scarce when a worker lane is available.
