# Caddy updater phase deferred

The updater compares the repository Caddyfile with the saved Caddyfile, but
neither file establishes the complete live configuration or excludes other
writers. A valid candidate can still remove live-only routes or TLS settings.
The updater therefore leaves Caddy untouched for every comparison outcome:

- Equal saved bytes: no effect; this does not establish live equality.
- Different bytes: report that whole-config preservation and publication
  custody are not qualified, then continue independent updater phases.
- Comparison/read error: report the error separately and likewise continue
  without a Caddy effect.

This phase does not validate, install, call the admin API, reload, restart, or
mark itself reconciled. There is no bypass switch. A prior independent phase's
reconciled state is preserved. Refusal is not durable route publication, CAS
qualification, or response-loss recovery.

## Bootstrap the protective updater separately

An existing updater invocation continues its old inode after installing a new
file at `/usr/local/bin/macro-update`. Merely replacing that file cannot prevent
the old invocation from reaching its old Caddy effect block.

The assigned physical owner must qualify an installation procedure that holds
the existing `/var/lock/macro-update.lock` exclusively after the old cooperating
invocation releases it, and through installation and verification of the exact
protected updater. Bind the lock's device/inode, ownership/mode and stable path,
the source and installed executable, and the saved Caddyfile. Do not kill the
old invocation, unlink/recreate the lock, recursively run the updater under its
inherited descriptor, or substitute another lock. If no supported installation
procedure retains that custody, hold bootstrap rather than run the old updater.

Lock ownership alone does not settle an old interpreter or scheduler wrapper
paused before its lock call. Before replacement, the physical owner must bind
and close the actual cooperating scheduled and manual entry paths, retain the
exact scheduler-table preimage under its existing writer custody, and reconcile
already-dispatched wrappers and pre-lock script images through their original
owners. Preserve unrelated scheduler entries and the original lock. A single
process-name scan, missing lock holder, or elapsed cron interval is not proof
that those entrants have drained. Other provisioners using blocking acquisition
of the same lock retain their separate pending effects and owners.

Only after entry is closed and that admitted set is settled may the owner use
the existing single-file installation primitive and verify the protected file
while retaining lock custody. Restore the exact original entry only after those
checks and a fresh scheduler-table comparison; do not overwrite unrelated edits
or automatically restore after an uncertain result. Do not run the full setup
script, stop the global scheduler, kill processes, wrap the unchanged updater in
another lock, or claim a new entry-control service exists. If current interfaces
cannot establish entry closure and complete drain, bootstrap remains held.

This boundary also applies before exposing the guard through the automatically
adopted protected default branch. A reviewed draft and green CI alone do not
establish safe first adoption. Actual entry-maintenance custody or separately
qualified old-path equality is still required before release promotion.

The old self-copy route is only eligible if actual candidate-to-saved byte
equality is maintained throughout its comparison window under qualified writer
custody. An unchanged Caddyfile in a Git diff is insufficient. Keep Caddyfile
changes out of this protective bootstrap release.

## Changed-configuration effects remain held

The existing updater lock excludes cooperating updater invocations only. It
does not exclude other configuration, admin API, or service writers. Future
publication needs qualified complete-config preservation, generation matching,
saved-file/startup consistency and custody across those effects. A check before
`systemctl reload` is not CAS; separate filesystem and live-config writes are
not an atomic transaction. Stop on uncertain publication without retry,
compensating restart, or inferred rollback. This document authorizes no physical
invocation, deployment, or adoption/removal of live-only configuration.
