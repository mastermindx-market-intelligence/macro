# US OHLC delivery to the existing site origin

## Purpose and boundary

Portfolio reads per-symbol chart JSON from the existing authenticated site origin.
The daily engine already builds those files from retained price stores, but
`site/ohlc` is ignored by Git. Publishing the ordinary site checkout therefore
cannot deliver that directory. The R2 publisher remains a separate destination.

This delivery leg moves only the existing producer's completed US chart output.
It does not collect prices, select another provider, change `STOCKDATA_BASE`,
change Caddy or authentication, acquire credentials, or create a research store.
A delivered file is not proof that its price window satisfies Portfolio's
coverage requirements. Missing prices or Treasury observations retain the
consumer's existing unavailable state.

## Producer completion

`scripts/build_chart_data.py:build_us` captures the actual source commit before
the daily output-commit/rebase tail. Only the canonical repository's main-branch
`daily.yml` execution receives a delivery receipt. Run ID, run number and attempt
must be positive decimal identities.

The producer invalidates its prior completion receipt, validates the stock
index and output filenames, and writes a fresh temporary directory. A manifest
binds the index's exact SHA-256, source commit, workflow/run identity, every
produced file's size and SHA-256, and the complete expected-symbol census.
A symbol with no retained price is explicitly classified
`no_retained_price`; it is not silently dropped from the census.

Existing chart schemas, retained sources, rounding and bar limits are unchanged.
The previous payload survives a failed or empty build. Duplicate or unsafe
filename identities, symbolic-link outputs and foreign entries are refused.
A successful directory switch precedes the final completion-receipt rename.
The receipt is `site/_tmp/ohlc-complete.json`, outside the payload directory.

Local and other-workflow chart builds can still produce chart JSON, but cannot
produce a receipt authorizing this delivery lane. A receipt from another run or
attempt must not authorize a current publication.

## Transfer and identity

The daily engine's delivery tail invokes:

```sh
python -m scripts.publish_ohlc publish \
  --manifest site/_tmp/ohlc-complete.json \
  --payload-dir site/ohlc \
  --evidence-dir <persistent-directory-for-this-run-and-attempt> \
  --ssh-key <ephemeral-existing-deploy-key-file>
```

The step is `if: always()`, after the output-commit attempt. A failed output push
does not suppress delivery of a separately verified complete generation, and
delivery refusal does not prevent the remaining always-run tail steps.
Delivery failure remains visible as a nonzero step status.

The workflow uses the existing `VPS_DEPLOY_KEY` secret. It creates a mode-0600
temporary key, removes that file on shell exit, and removes the secret environment
variable before launching the publisher. It neither prints nor persists the key.

The destination is fixed to the existing `root@146.190.142.17` carrier.
`app/deploy/ohlc_origin_known_hosts` contains the existing trusted ED25519 host
identity. SSH requires that pin with strict checking and no global fallback.
The publisher must not learn a new host identity with a network key scan or
accept-on-first-use mode.

Pin qualification on 2026-10-22T07:54:26.618300Z used only the candidate pin and
the existing carrier, executing the metadata-only command `true`:

- Fingerprint: `SHA256:U7EME9HvtMm7vT+Bv57mJF2VB/f/NS16SV/4OJNrvOk`.
- File SHA-256: `eca7a93ca24295b31034c4926a70ed2e3cc522b39b10a24bddc808f6e121942e`.
- Strict-check connection exit: 0.

This is server-identity evidence, not a data-access or price-freshness receipt.

## Receiver and atomic selection

The box-only generation store is outside both site trees:

```text
/opt/macro/ohlc.served/generations/<generation>/payload/
/opt/macro/ohlc.served/generations/<generation>/manifest.json
/opt/macro/ohlc.served/current
```

The selected `current` link refers to one verified generation's payload.
Both `site/ohlc` and `site.served/ohlc` use the fixed relative link
`../ohlc.served/current`. One atomic pointer selection therefore changes the
whole generation for both paths; the manifest is outside the served payload.

Before selection, the receiver checks the versioned manifest, exact file census,
sizes, digests and configured resource bounds. Archive extraction must reject
traversal, duplicate members, unexpected files, directories, links, devices and
non-regular entries. No archive-wide unchecked extraction is permitted.
The archive uses strict USTAR regular-file headers and filenames of at most 100 bytes.
GNU/PAX extensions are refused before their declared bodies are read. USTAR prefix
fields are validated as part of the complete member path. Staging and incomplete
generations cannot become a serving path.

The receiver checks store custody under the lock, then stages and validates the
upload outside it. It reacquires the lock and rechecks store identity, predecessor,
operation receipt, payload and ordering immediately before promotion. A slow or
broken upload therefore does not occupy the updater lock. A missing watermark
in a previously used store is a refusal, including after a rollback.

Receiver mutation and the ordinary updater serialize through the existing
`/var/lock/macro-update.lock`. A busy lock is a bounded visible outcome; no
lock deletion or competing-lock workaround is permitted. A publisher's expected
predecessor and manifest digest fence the transition. Monotonic daily run order
prevents an older run from replacing a newer selection. The same generation and
digest are idempotent; reuse of an operation identity with different bytes is a
conflict.

Existing unrecognized directories or links are refused rather than adopted.
A verified predecessor remains available for a fenced rollback; rollback must
refuse if another writer has advanced the current pointer.

## Updater behavior

The updater borrows its already-held descriptor 9:

```sh
/usr/bin/python3 "$APP_DIR/scripts/publish_ohlc.py" reconcile --lock-fd 9
```

The helper validates the descriptor's device/inode against the expected regular
lock file and must not unlock it or acquire a separate descriptor that would
deadlock against its parent.

Reconciliation runs before the main site copy and again outside the
Git-change branch. It therefore repairs recognized artifact links even on a
repository no-op. With no installed generation, it reports that state without
claiming publication.

The main site copy excludes the root `ohlc` path from `rsync --delete`.
This also preserves a foreign path when reconciliation refuses it.
A reconciliation failure is carried to the updater's final status while
unrelated deployment work continues. A later successful check cannot erase that
failure, and an existing failure status from another deployment lane is
preserved.

The generation store and the `site/ohlc` symlink are ignored by Git. Generated
payloads, private keys and operation state are not source commits.

## Unknown effects and release acceptance

The sender keeps operation identity and outcome evidence in a persistent
per-run/per-attempt directory outside the worktree. A lost transport
acknowledgment does not authorize a new operation or blind resend. Reconcile
the original receiver identity/digest and predecessor through the same carrier;
preserve unknown status when no definitive readback is available.

Release acceptance is ordered:

1. Pass focused synthetic producer, receiver, archive, concurrency, rollback,
   workflow and updater tests, plus the unchanged OHLC authentication guards.
2. Complete independent source review and the repository's full protected CI.
3. Merge normally, then observe the incumbent cron/updater install the reviewed
   helper and updated updater. The predecessor updater's first tick may install
   its successor; confirm the new updater is installed before any first payload
   publication.
4. Allow the existing trusted daily engine to create and deliver a completed
   generation. Do not manufacture a completion receipt for old files or rerun a
   broad collector merely to obtain delivery.
5. Verify generation identity and selected links through metadata receipts.
   This proves delivery only.
6. Complete authenticated Portfolio price-window and Treasury acceptance through
   the existing approved session and same-box transport. A server file count,
   file modification time or empty fixture is not positive metric acceptance.

No step reauthorizes a previously denied data source or requires replay of the
already completed live Portfolio mutation/cleanup fixture.
