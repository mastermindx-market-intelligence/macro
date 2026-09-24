# Consumer Defensive CDV-1 Task 8 — Release Readiness Census

Operation: `gmi-consumer-defensive-research-20260923-sol-001`  
Date: 2026-09-24  
Mode: read-only census, documentation only  

STATUS: IN PROGRESS

## Q1 — Incumbent producer path

The incumbent lane is `earnings-public-wire`. It is triggered by successful completion of `earnings-story-packets` or `company-intelligence` on `main`, by pushes to its owned code paths, hourly at `cron: "47 * * * *"`, and manually (`.github/workflows/earnings-public-wire.yml:7-24`). Its one `publish` job runs `ubuntu-latest` with a 50-minute hard timeout (`.github/workflows/earnings-public-wire.yml:33-40`). `concurrency.group` is `earnings-public-wire` and in-progress runs are cancelled (`.github/workflows/earnings-public-wire.yml:29-31`).

The production commands are `PRIVATE_STAGE="$RUNNER_TEMP/earnings-wire-private-${PUSH_ATTEMPT}"`, `python -m scripts.build_earnings_public_wire --private-out-dir "$PRIVATE_STAGE"`, and `python -m scripts.publish_earnings_private_store --source-dir "$PRIVATE_STAGE"` (`.github/workflows/earnings-public-wire.yml:122-124`). The private staging directory is therefore outside the checkout, while the subsequent normalization and commit own only `site/stocks/earnings` and content-hashed assets (`.github/workflows/earnings-public-wire.yml:126-165`).

The producer binds these secret/env NAMES only: `ADMIN_GH_TOKEN`; `R2_RESEARCH_ENDPOINT`; `R2_RESEARCH_ACCESS_KEY_ID`; `R2_RESEARCH_SECRET_ACCESS_KEY`; and `R2_RESEARCH_BUCKET` (`.github/workflows/earnings-public-wire.yml:69-78`). No secret values are read by this census. `scripts/publish_earnings_private_store.py` runs on the workflow runner immediately after public-wire staging; it prepares the complete off-repo closure, builds a private Research Vault store, and refuses a public-only publish when that store is unavailable (`scripts/publish_earnings_private_store.py:30-37`).

The store family is `earnings_wire_private/v1`, its current pointer is `earnings_wire_private/v1/current.json`, and private manifests live under `earnings_wire_private/v1/manifests/<generation>.json` (`engine/earnings_narrative/private_publication.py:33-36,59-61`). The runtime `_build_store()` delegates to `engine.research_vault.r2_store.build_store()` (`app/earnings.py:70-80`). That factory selects `RESEARCH_LOCAL_STORE` first, otherwise requires `R2_RESEARCH_BUCKET` plus credentials, with research-specific endpoint/key names falling back to shared `R2_*` names (`engine/research_vault/r2_store.py:1060-1081`; `engine/research_vault/r2_store.py:182-207`). This census did not read environment values, so the live bucket identity is not determinable from the repository.

Two-writer custody is workflow-level, not a distributed CAS protocol. The incumbent protection is the single `earnings-public-wire` concurrency group with cancellation (`.github/workflows/earnings-public-wire.yml:29-31`). Inside one publication call, `_PUBLISH_LOCK` serializes threads (`engine/earnings_narrative/private_publication.py:672-681`). Immutable objects and the manifest are written/read-back first, then `current.json` is advanced last and its complete closure is replayed (`engine/earnings_narrative/private_publication.py:694-745`). The R2 adapter does expose conditional `If-Match`/`If-None-Match` writes (`engine/research_vault/r2_store.py:525-576`), but this publisher uses ordinary `put_bytes` for `current.json` (`engine/earnings_narrative/private_publication.py:725-731`). Consequently, publication custody is safe under the lane's single-workflow concurrency regime, but the current pointer itself does not have a cross-workflow atomic compare-and-swap.

## Q2 — Live private store state

A conformant `current.json` is the strict object `earnings.private_pointer/v1` with exactly `schema`, `generation_id`, `manifest_key`, `manifest_sha256`, `manifest_bytes`, and `published_at` (`engine/earnings_narrative/private_publication.py:483-525`). `generation_id` must match `earnpriv_[a-f0-9]{32}`, `manifest_key` must equal `earnings_wire_private/v1/manifests/<generation_id>.json`, the SHA must be 64 lowercase hex characters, and bytes must be 1–8 MiB (`engine/earnings_narrative/private_publication.py:42-61,509-523`). Reading the pointer resolves the manifest only after exact length/hash validation and binds generation plus `published_at` (`engine/earnings_narrative/private_publication.py:748-772`).

The manifest itself is `earnings.private_manifest/v1` with exactly `schema`, `generation_id`, `published_at`, `source`, `record_count`, `ticker_count`, `records`, and `context` (`engine/earnings_narrative/private_publication.py:250-315`). `published_at` is derived from the context catalog's `knowledge_cutoff`, while `source` binds `wire_manifest_id`, source generation, and source manifest SHA (`engine/earnings_narrative/private_publication.py:422-440`; `engine/earnings_narrative/context_packets.py:380-394`). The record catalog is slug-keyed receipt entries (`object_key`, `sha256`, `bytes`), bounded to 10,000 records (`engine/earnings_narrative/private_publication.py:230-247,286-297,47`).

Without credentials or contacting R2, the exact live generation/counts cannot be determined. The newest evidence visible in repo wire-output history is commit `57210b3a1f1ae7b1d01963e218e9f9d326ad539f`, at `2026-09-24 07:03:29 +0000`, `earnings-wire: publish current verified records [skip ci]` (`git log -5 --format='%h %ad %s' --date=iso -- site/stocks/earnings`). Its only changed artifact is `site/stocks/earnings/route-catalog.json` (`git show --numstat --format='%H %cI' 57210b3a1f1`), whose committed values include `as_of=2026-09-23T23:40:27Z`, `verified_at=2026-09-24T06:55:45Z`, `source_generation_id=b119ac17635bd813f7a1696486ee4931`, and `article_count=5616`.

No repo-committed artifact reveals a private record. `scripts/build_earnings_public_wire.py` rejects a private output directory inside the checkout (`scripts/build_earnings_public_wire.py:991-999`), stages only member records and context off-repo (`scripts/build_earnings_public_wire.py:1002-1048`), and the latest wire commit contains only the redacted route catalog. The tree scan at `57210b3a1f1 -- site/stocks/earnings` found no `earnings_wire_private`, `earnpriv`, or `private_manifest` path. The prior four listed commits also match the required subject; this census did not infer their private payloads, which remain outside Git.

## Q3 — Real PG source admission

PENDING

## Q4 — Runtime read path

PENDING

## Q5 — Browser proof infrastructure

PENDING

## Q6 — Release ordering hazards

PENDING

## Q7 — Legacy market-decision evidence

PENDING
