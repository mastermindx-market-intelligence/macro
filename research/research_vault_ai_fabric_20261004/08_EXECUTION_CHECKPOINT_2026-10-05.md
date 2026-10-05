# 08 — Execution checkpoint — 2026-10-05

**Parent:** Research Vault AI Intelligence Fabric / PR #8438  
**Protected procedure pin used for this checkpoint:** Mastermind `7eac3ec252475600147ec9a376b8ca16403ac4c5`, Skillpack 1.0.1  
**Observed Macro main during latest continuation:** `544d3ca021cc64471fc6ae28c0e790b68e73433b` (movement since earlier F4 work was path-disjoint generated/site output for the new F6 carrier).  
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

Adversarial review on head `4df909395c2ef2bd1e4c27f23051940b3823c54a` found the architecture sound but hosted CI exposed three discriminating source regressions:

1. the lineage suite still assumed current `SHA256SUMS` must equal the immutable recovery hash, which is no longer valid after merged #8452;
2. an empty-vault feed fixture still emitted the old 3-field probe contract rather than the new 7-field typed-auth contract;
3. the canonical-dispatch fixture had the same stale probe shape, so dispatch was never reached.

Observed Research Vault source-lineage result: **3 failed, 357 passed**; `ci-gate` was red because that semantic proof was blocking.

Blocking review is recorded on #8472. The active owner must repair those exact tests/contracts on the same carrier. Do not duplicate the source fix elsewhere.

A second acceptance boundary remains: an `AUTH_REQUIRED` line in the incumbent local feed log is useful typed state, but is not by itself externally observed operator-alert proof. Final F4 acceptance still requires host readback, human single-writer re-auth only if actually required, and natural-report proof.

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

Current main has no competing `fulltext.py`; #8453 remains the unique F5 carrier.

Principal review on head `4895b47660d817889556757560c004d00951db80` found two contract blockers before this can become the citation-identity substrate:

1. segment artifacts omit `extractor_name` even though the extracted-text identity and stated contract bind extractor name + version;
2. `replay_segment()` proves an exact byte slice but does not prove the supplied row is the **canonical deterministic segment** for its declared `segment_index / segmenter_version / max_bytes`. A forged alternative exact slice can pass if its text/hash/page fields are recomputed.

Blocking review is recorded on #8453. The preferred correction is to reconstruct canonical segments for the declared algorithm/version/budget and require the supplied row to equal canonical `segments[index]`, with adversarial tests for extractor name, index, segmenter version and alternative valid byte windows.

Do not create a second chunk/segment abstraction.

## 6. F6 subject metadata / Data OS identity bridge — ACTIVE

Draft PR #8475:

**feat(research-vault): add Data OS subject identity bridge**

Current owned head at this checkpoint:

`f163e40505f5b726be3c1be5052e84453347e7f3`

This is a pure, path-disjoint F6 increment. It does not mutate catalog rows or claim the source has canonical ticker metadata today.

It adds:

### `research_vault.subject_candidates.v1`

- source-provided sidecar ticker candidates at highest source confidence;
- existing `engine.entity_resolver` output as context-only candidate evidence;
- title/summary candidate discovery by default;
- licensed body scanning only by explicit opt-in;
- symbol/confidence/method/source-field provenance;
- **no exact `security_id`**;
- no publisher-text copy into the candidate artifact.

### `research_vault.subject_resolution.v1`

Exact binding requires:

- a caller-supplied canonical `lib.dataos.identity.VendorAliasTable`;
- an explicit reviewed alias-vendor namespace;
- the report publication date.

Each candidate becomes either:

```text
RESOLVED -> exact Data OS security_id
UNMAPPED -> security_id = null
```

The bridge refuses to guess whether Research Vault should use `membership`, `store`, `yahoo`, or another Data OS alias namespace. That policy is deliberately left to a reviewed downstream integration decision.

Hardening on the owned carrier also refuses:

- blank forged report IDs;
- NaN/inf confidence;
- accidental bare-string `source_tickers` iteration;
- implicit vendor choice;
- invalid publication clocks;
- malformed provenance.

Data OS remains the only exact security-identity authority. `engine.entity_resolver` remains candidate/context-only.

No catalog/backfill/search-filter activation should occur until #8475 passes review and the alias-namespace policy is frozen.

### F6 alias-namespace ruling

The correct exact-symbol semantics for an institutional report are the Data OS **`exchange` historical naming space**.

This is source-backed by `research/MASTERMIND_SECURITY_MASTER_SPEC.md`:

- §6 lists `exchange` as a vendor namespace with `alias_kind=exchange_symbol`;
- §9.1's MMC→MRSH worked example resolves dated market symbols through `exchange`;
- `membership` instead means "what this repo keyed it on that day";
- `yahoo` means what Yahoo called the security.

Current implementation gap:

`scripts/build_security_master.py` currently materializes historical `yahoo` / `membership` / `ledger`, current-catalog `yahoo_fetch` / `store`, and `theme_graph_native`, but not the spec-defined `exchange` namespace.

Current Data OS receipt at this checkpoint reports 6,037 readable alias rows and no accepted `exchange` materialization.

Therefore:

```text
Research ticker candidate
    -> DO NOT substitute membership/yahoo
    -> Data OS exchange alias namespace required
    -> resolve(exchange, symbol, report_published_date)
    -> exact security_id | typed UNMAPPED
```

The needed Data OS builder path is currently touched by open draft #7299. Do **not** create a competing builder writer. The `exchange` alias addition is a Data OS-owner follow-up after that custody is reconciled.

## 7. Current critical dependency DAG

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

F5 exact text/segment contract  #8453 ACTIVE / BLOCKING REVIEW
        |
        +--> canonical-segment identity corrections
        +--> production materialization waits on measured corpus truth

F6 subject/identity bridge       #8475 ACTIVE
        |
        +--> explicit alias-namespace policy
        +--> provenance-bearing metadata backfill only after review
```

## 8. Exact next actions

### Independent source/review work

1. Keep #8472 source custody with its current owner; require repair of the three recorded Research Vault source-lineage failures before acceptance.
2. Keep #8453 source custody with its current owner; require canonical-segment identity + extractor-name corrections before acceptance.
3. Review/finish #8475, then freeze the explicit Data OS alias namespace policy before any ticker backfill/search exposure.
4. Run the real read-only F2 census through the dedicated operator lane when its merged workflow can be safely dispatched.
5. Classify F3 from that receipt:
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

## 9. Fable handoff effect

The original Fable packet remains useful, but a new Fable principal should **not** restart at F1.

Its current start frontier is:

```text
consume merged F1/F2/#8452
        ->
review/finish #8472 + #8453 + #8475
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
