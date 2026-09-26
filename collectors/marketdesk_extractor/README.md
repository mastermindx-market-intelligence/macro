# Canonical MarketDesk Extractor Source

This directory is the single Git owner for the production MarketDesk paper
extractor that publishes into Research Vault. It extends the existing `macro`
collector and does not create another collector, queue, database, bucket, catalog,
or publication authority.

The source-lineage import was accepted in Macro PR #7164 and production deployment
was proved on M1. Release `research-vault-feed-liveness-r1-20260916` moves the
Research Vault ingest dispatch into the already-running collector and retires the
separate `com.mastermindx.research-feed` launchd carrier. The hourly GitHub Actions
workflow remains the correction backstop.

## Provenance and current release

- Recovery operation: `research-vault-source-lineage-r1-20260914-sol-001`
- Source issue: `mastermindx-market-intelligence/Mastermind#631`
- Accepted import commit: `31981dc66e9a37419b5b7a6aecfde28808785d03`
- Recovery packet: `research-vault-recovery-source-20260914-v3.tar.gz`
- Packet SHA-256: `2019c38650493e4cfa40f7ed87c175a91ea939ca57d1f404ec73c5572c340e7a`
- Frozen recovery manifest: `RECOVERY_SHA256SUMS`
- Current release manifest: `SHA256SUMS`
- Current release receipt: `RELEASE_RECEIPT.json`
- Payload files: 58

`IMPORT_RECEIPT.json` and `RECOVERY_SHA256SUMS` preserve the exact recovery anchor.
Git history at the accepted import commit preserves the packet-exact payload bytes.
`RELEASE_RECEIPT.json` and `SHA256SUMS` own the current deployable release.

## Layout

```text
collectors/marketdesk_extractor/
  RECOVERY_SHA256SUMS        # frozen recovery manifest
  SHA256SUMS                 # current release payload manifest
  IMPORT_RECEIPT.json        # immutable provenance anchor
  RELEASE_RECEIPT.json       # current release and runtime topology
  extractor/                 # standalone Python package, tests, docs, templates
  runtime/                   # recovered runtime artifacts and active collector plist
  feed.sh -> runtime/feed.sh # historical compatibility link only
  tools/install_runtime.py   # verify, install, retire, read back, and roll back
```

The recovered `runtime/feed.sh` and
`runtime/com.mastermindx.research-feed.plist` remain source-controlled for lineage
and rollback evidence, but they are not active release destinations.

## Verify

From the repository root:

```bash
python3 collectors/marketdesk_extractor/tools/install_runtime.py verify-source
(cd collectors/marketdesk_extractor && shasum -a 256 -c SHA256SUMS)
python3 -m pytest tests/test_marketdesk_extractor_lineage.py -q
```

Run the standalone extractor suite:

```bash
python3 -m venv /tmp/marketdesk-extractor-test
/tmp/marketdesk-extractor-test/bin/pip install -e   'collectors/marketdesk_extractor/extractor[dev]'
/tmp/marketdesk-extractor-test/bin/python -m pytest   collectors/marketdesk_extractor/extractor/tests -q
```

## Production topology

The collector is the only active M1 process that opens the external-volume SQLite
state. The collector also owns the post-publication Research Vault ingest dispatch.
After each successful Research Vault publication it dispatches the canonical
`research-ingest.yml` workflow and atomically advances the existing feed watermark.
Dispatch failure is fail-soft: the collector continues and the hourly workflow
reconciles the inbox.

| Canonical source | Existing M1 destination | State |
|---|---|---|
| `extractor/**` | `~/mastermind-research/marketdesk_paper_extractor/**` | active |
| `runtime/com.mastermindx.research-trickle.plist` | `~/Library/LaunchAgents/com.mastermindx.research-trickle.plist` | sole launchd authority |
| `runtime/feed.sh` | former `~/mastermind-research/feed.sh` | retired and removed by install |
| `runtime/com.mastermindx.research-feed.plist` | former `~/Library/LaunchAgents/com.mastermindx.research-feed.plist` | retired and removed by install |

The `ai.marketdesk.*` templates under `extractor/deploy/` remain historical lineage
only and must not be activated. `com.mastermindx.research-feed` is also superseded
and must remain unloaded. The sole production launchd authority is
`com.mastermindx.research-trickle`.

## Install and read back

Run only from an accepted merged commit. The installer never invokes `launchctl` or
opens Chromium. It backs up every managed destination, installs current source,
removes the retired feed script and feed plist, and performs hash/mode readback.

```bash
backup="$HOME/mastermind-research/recovery-backups/marketdesk-source-$(date -u +%Y%m%dT%H%M%SZ)"
python3 collectors/marketdesk_extractor/tools/install_runtime.py install   --backup-dir "$backup"
python3 collectors/marketdesk_extractor/tools/install_runtime.py verify-installed
```

Destination overrides are for hermetic tests and rehearsals only. Production
commands must omit `--runtime-root`, `--feed-script`, and `--launch-agents-dir`.
Mutable state remains outside installer authority: `.env`, `.venv`, browser profile,
SQLite, PDFs, parsed artifacts, logs, credentials, cookies, watermarks, and locks.

Activation is separate: boot out the superseded feed label, perform one controlled
restart of the collector, prove one no-new-row cycle, one later natural publication,
the collector-owned workflow dispatch, successful ingest, and the production API and
browser result.

## Rollback

Rollback restores exact pre-install bytes, including a prior feed script/plist when
they existed. It does not change launchd state.

```bash
python3 collectors/marketdesk_extractor/tools/install_runtime.py rollback   --backup-dir "$backup"
```

After rollback, explicitly reconcile launchd topology before enabling any carrier.
Never activate both the collector-owned dispatch and the superseded feed carrier.
