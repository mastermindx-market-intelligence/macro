# Canonical MarketDesk Extractor Source

This directory is the canonical Git lineage for the production MarketDesk paper
extractor that publishes into Research Vault. It was recovered from the M1 Studio
after the September 2026 external-storage incident and imported under the existing
`macro` collector owner. It does **not** create another collector, queue, scheduler,
database, bucket, catalog, or publication authority.

The live Research Vault was already recovered and proven healthy before this source
import. This import is a durability and governance change only. The import PR must
remain **Draft / HOLD-FOR-SOL** until independent review releases the deployment gate.
It does not alter, restart, or cut over the live M1 runtime.

## Provenance

- Operation: `research-vault-source-lineage-r1-20260914-sol-001`
- Source issue: `mastermindx-market-intelligence/Mastermind#631`
- Recovery packet: `research-vault-recovery-source-20260914-v3.tar.gz`
- Packet SHA-256: `2019c38650493e4cfa40f7ed87c175a91ea939ca57d1f404ec73c5572c340e7a`
- Payload manifest: `SHA256SUMS`
- Payload files: 58

`IMPORT_RECEIPT.json` records the frozen ownership decision, runtime mapping,
excluded mutable state, and non-goals. `SHA256SUMS` covers only the immutable packet
payload under `extractor/` and `runtime/`; canonical metadata and deployment tooling
live alongside it and are deliberately outside that recovered manifest.

## Layout

```text
collectors/marketdesk_extractor/
  SHA256SUMS                 # hashes for all 58 recovered payload files
  IMPORT_RECEIPT.json        # canonical ownership and provenance receipt
  extractor/                 # standalone Python package, tests, docs, deploy templates
  runtime/                   # installed feed bridge and production launchd plists
  feed.sh -> runtime/feed.sh # compatibility link for the recovered package test layout
  tools/install_runtime.py   # verify, install, read back, and roll back source bytes
```

The standalone distribution remains intact at `extractor/`: its own
`pyproject.toml`, `src/marketdesk_extractor/`, tests, docs, and deploy templates are
preserved rather than translated into duplicate root-level modules.

## Verify the recovered bytes

From the repository root:

```bash
python3 collectors/marketdesk_extractor/tools/install_runtime.py verify-source
(cd collectors/marketdesk_extractor && shasum -a 256 -c SHA256SUMS)
```

Both commands must report all 58 payload files intact. A missing, changed, extra, or
symlinked payload beneath `extractor/` or `runtime/` fails closed.

Run the recovered extractor suite independently:

```bash
python3 -m venv /tmp/marketdesk-extractor-test
/tmp/marketdesk-extractor-test/bin/pip install -e \
  'collectors/marketdesk_extractor/extractor[dev]'
/tmp/marketdesk-extractor-test/bin/python -m pytest \
  collectors/marketdesk_extractor/extractor/tests -q
python3 -m pytest tests/test_marketdesk_extractor_lineage.py -q
```

## Deterministic runtime mapping

After merge and independent deployment approval, the installer maps only these
source-owned files:

| Canonical source | Existing M1 destination |
|---|---|
| `extractor/**` | `~/mastermind-research/marketdesk_paper_extractor/**` |
| `runtime/feed.sh` | `~/mastermind-research/feed.sh` |
| `runtime/com.mastermindx.research-feed.plist` | `~/Library/LaunchAgents/com.mastermindx.research-feed.plist` |
| `runtime/com.mastermindx.research-trickle.plist` | `~/Library/LaunchAgents/com.mastermindx.research-trickle.plist` |

The files `extractor/deploy/ai.marketdesk.*.plist` and
`extractor/docs/DEPLOY_MAC_STUDIO.md` are recovered historical templates preserved
for lineage only. The `ai.marketdesk.*` launchd namespace is superseded and must not
be activated. The sole production launchd authority is the two
`runtime/com.mastermindx.research-*.plist` files mapped above, and even those remain
inactive until the separate post-merge activation gate is approved.

The installer replaces only package source, package tests/docs/deploy templates,
package metadata, the feed bridge, and those two exact launchd plist files. It
preserves `.env`, `.venv`, the persistent browser profile, SQLite state, PDFs,
parsed artifacts, logs, credentials, cookies, watermarks, locks, and every external
storage path.

It never invokes `launchctl`, opens Chromium, dispatches GitHub Actions, or starts a
second producer. Installing bytes and activating those bytes are intentionally
separate reviewable acts.

## Post-merge installation and readback

Do not run this section from an unmerged branch. After an accepted commit is checked
out on the M1, choose a new backup directory outside the managed package root:

```bash
backup="$HOME/mastermind-research/recovery-backups/marketdesk-source-$(date -u +%Y%m%dT%H%M%SZ)"
python3 collectors/marketdesk_extractor/tools/install_runtime.py install \
  --backup-dir "$backup"
python3 collectors/marketdesk_extractor/tools/install_runtime.py verify-installed
```

Run this offline import smoke before activation; it starts no browser, touches no
Research Vault data, and changes no launchd state:

```bash
"$HOME/mastermind-research/marketdesk_paper_extractor/.venv/bin/python" \
  -c 'import marketdesk_extractor; print(marketdesk_extractor.__file__)'
```

Destination overrides are for hermetic tests and rehearsals only. The recovered
launchd plists retain their packet-exact absolute production paths and are not
rewritten by the installer, so production install, readback, and rollback commands
must omit `--runtime-root`, `--feed-script`, and `--launch-agents-dir`.

`install` refuses to reuse an existing backup directory or operate through symlinked
runtime/control roots. It snapshots every source-owned destination, removes stale
files only inside the managed package source directories, copies through sibling
temporary files plus atomic rename, and performs immediate hash plus executable-mode
readback. Any failed readback triggers rollback before the command returns an error.

Activation remains a separate gate. Before changing launchd state, prove that the
accepted Git commit is the deployed source, that the sole producer owns the one
persistent browser profile, and that no competing MarketDesk process exists. Then
follow the accepted Research Vault deployment runbook for one controlled restart,
one no-new-row cycle, one later natural publication, and unchanged collector/API
health.

## Rollback

The backup receipt records every destination that existed before installation and
every newly introduced source file, with each preserved payload's SHA-256 and mode.
Rollback prevalidates the whole receipt, requires its recorded runtime, feed-script,
and launch-agent roots to match the caller-requested destinations, and permits only
the source-owned package paths, the exact feed script, and the two exact launch-agent
files. Runtime state such as `.env`, `.venv`, browser profiles, data, logs, credentials,
and cookies remains outside rollback authority even when it sits below the recorded
runtime root. Restored hashes and modes are verified before success. To restore those
exact pre-install bytes at the production-default destinations:

```bash
python3 collectors/marketdesk_extractor/tools/install_runtime.py rollback \
  --backup-dir "$backup"
```

Rollback also does not restart launchd. After restoring bytes, use the same controlled
runtime procedure and verify the collector, feed bridge, SQLite integrity, ingest,
and public catalog. Keep both the immutable M1 recovery evidence and the deployment
backup until canonical deployment has passed its natural-event proof.
