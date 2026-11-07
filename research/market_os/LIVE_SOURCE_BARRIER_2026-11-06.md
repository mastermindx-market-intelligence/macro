# Live source update barrier — core three lanes

Date: 2026-11-06. Status: SOURCE QUALIFIED; NOT DEPLOYED.
Source base: `5a8513cab16dd0a7fe2a10a5960fd2c4c1b9ac58`.
Governing Mastermind pin: `770837b4317287fb36a3e7e3948ea701de67bbab`.
Mission: https://github.com/mastermindx-market-intelligence/macro/issues/10779

## Consumer and boundary

The existing fast, snapshot and bars services execute through the installed `macro-update --live-lane` owner. Their shared source lock survives exec into the existing Python orchestrator. The incumbent updater alone holds the exclusive source lock while resetting the checkout and publishing the corresponding existing mirrors. The existing updater fd9 serialization and Options safety guards remain authoritative.

This fences three services and their three timers. It is not estate-wide source or virtual-environment isolation. The separate live-setup integration is still required before activation; no new daemon, watcher, scheduler or separately installed helper was introduced.

## Recovery contract

The updater embeds its bounded standard-library control code and captures its executing Bash descriptor, original Git HEAD and exact three-helper closure before importing mutable checkout helpers. One durable pending journal binds the original OLD/NEW pair, immutable capsule, six target units, timer intent and original service cgroups. A recovered invocation uses that original target; FETCH_HEAD cannot redirect the interrupted transaction.

The stable fd8 lock file is never replaced or unlinked. Pending state is parsed strictly and fails closed on malformed, duplicate, symlink, FIFO, inaccessible, unknown or incomplete input. File publication uses same-parent atomic replacement plus file and parent-directory fsync. A failure after a visible rename reports that readback is required; it does not claim no effect.

For enrolled installations, exact guarded unit definitions are installed, reloaded and attested before source mutation. Old services and their original/current/default cgroups must drain. Partial enrollment, unexpected loaded fragments, drop-ins and masks refuse. An absent enrollment is not silently armed.

The source transaction retains the existing Options pre-reset gate and all corresponding mirror copies. It records each mirror completion, checks exact target HEAD and clean source/configuration, then records SOURCE_READY before releasing the exclusive lock. Only SOURCE_READY/RESTORING with exact owner, capsule and current source permit new readers.

Timer restoration is independent per timer. Disabled intent remains disabled; already-active timers are accepted without restarting. Ambiguous start effects, changed enabled state and disabled manual activation across a boot retain the journal. Ready recovery skips fetch, reset and mirrors. Owner replacement and new target selection remain blocked until the original journal completes.

## First adoption and owner replacement

`setup.sh --install-source-owner --source-revision <full SHA>` copies the exact Git object into a temporary candidate, checks shell syntax, and invokes its closed atomic owner-install mode under fd9 and fd8. The ordinary updater is a separate invocation after readback. Existing live installations cannot pass through the old full setup/bootstrap direct-reset route. Both existing owner-install sites use atomic replacement; they do not truncate the executing installed owner.

## Qualification

The Linux suite exercises real flock, exec, descriptor lifetime, minimal Git repositories and extracted transaction code against an isolated fake systemd manager. Thirty-three cases passed. It includes original-target crash recovery, mirror failure, malformed pending state, wrong loaded fragments, old cgroups, closed unit execution hooks, all four independent timer intent combinations, ambiguous restoration, and post-rename durability failure.

The affected five-suite run returned 482 passed, 28 skipped and two environment-specific fixture failures. Those exact two cases then passed under Bash 5.3.9 and process-local umask 022. The first used the Mac's Bash 3.2 empty-array behavior; the other inherited Studio's restrictive umask into a fixture asserting mode 0755. Their assertions and the corresponding production helper/Caddy gate bytes were preserved. These are separate receipts, not a claimed single all-green run.

The tests also exposed seven newly introduced API dependencies missing from the incumbent updater's restart path set; those exact paths are now included. Source-extraction fixture anchors follow the captured helpers and exact NEW reset.

See [machine-readable source review](LIVE_SOURCE_BARRIER_SOURCE_REVIEW_2026-11-06.json) for exact hashes and retained proof references.

## Required next phase

Integrate live-setup into this same installed owner and journal, with an explicit setup purpose, the existing setup finalizer, captured timer intent, package mutation while the journal remains non-admitting, qualified readiness before smoke, and recovery that cannot promote interrupted package work merely because Git HEAD matches. Then qualify first adoption, crash/resume and the actual loaded-unit path through the existing release owner.

CI registration remains held by the earlier explicit Studio command denial; no denied action was replayed. PR10780 remains unarmed. No production unit, timer, checkout or installed owner was changed by this qualification. Existing original Fabric effects, protected holdings ownership and Terminal allocation uncertainty remain separate.
