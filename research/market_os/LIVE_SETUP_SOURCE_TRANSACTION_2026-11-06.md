# Recoverable live setup under the existing source owner

Date: 2026-11-06.
Mission: https://github.com/mastermindx-market-intelligence/macro/issues/10779
Carrier: Macro PR10780; operation macro-always-on-shared-shell-20261105-c3.
Protected law: Mastermind 770837b4317287fb36a3e7e3948ea701de67bbab.
State: SOURCE_QUALIFIED_NOT_ACTIVATED. This is a continuation milestone, not completion of the live migration.

## Outcome

The existing installed macro-update now owns live setup as a purpose-bound transaction under its existing updater mutex and source barrier. live-setup.sh delegates to that owner; it no longer independently installs core units, starts every timer, or removes publication on failure. Ordinary updater recovery cannot take over a setup transaction.

The implementation preserves the incumbent scheduling, publication, account and release owners. It adds no scheduler, queue, service, database, generic retry controller or alternate deployment path.

## Transaction and source contract

Preflight captures the original source revision and the exact helper closure before imports. Setup reads that original entry revision, rather than recapturing a possibly changed HEAD. A setup manifest has OLD equal to NEW, captures its exact script and six ancillary unit definitions, and records original core/ancillary enrollment and timer intent. Core fast/snapshot/bars services remain the only source-guarded readers; the ancillary services are not advertised as estate-wide source or environment isolation.

The outer invocation holds fd9 throughout setup. Closed controls borrow the same mutex and revalidate the original attempt. Core guard installation and reader draining occur under the stable source lock. Incomplete setup remains nonadmitting to core readers while package preparation runs outside EX. No network/package operation holds the source lock. SOURCE_READY recovery skips package, source and unit mutation.

Full bootstrap/setup also serialize their initial absence check and source/environment mutation under the incumbent fd9. Owner adoption remains install-only and separate from ordinary update. Existing Options/Movers/Caddy fences remain in place.

Stages are PACKAGES, READY, SMOKED, ARMED and CRON_RETIRED. Closed journal validation rejects contradictory stages and incomplete advanced-stage effects. Completion writes the full final journal, manifest hash and journal hash into the original capsule before retiring pending.

## Environment binding

An existing environment is captured by resolved root/device/inode and reused without pip upgrades. Missing dependencies are a maintenance-owner obligation, not permission to mutate an environment serving other consumers.

A fresh environment is prepared privately under the original attempt. Source readiness is verified before importing checkout code. Required imports qualify the candidate; its filesystem is synchronized before atomic no-replacement symlink publication at .venv. An externally appearing destination is preserved. Readback of the original exact binding permits recovery without republishing or reinstalling into a served environment. A visible binding followed by persistence failure requires effect reconciliation.

## Invocation-bound smoke

The single admitted smoke records intent before starting the existing guarded fast service. It requires a new successful same-boot systemd invocation with appropriate monotonic boundaries, inactive/zero-process completion, the private producer's matching INVOCATION_ID, and a successful display_quotes task.

The existing producer now records a SHA256 for the exact streamed bytes it published. Smoke requires its captured quotes bytes to match that private receipt, then applies the incumbent quote-quality validator. A successful coalesced invocation cannot claim another owner's later status/publication. Invocation identifiers and publication hash maps stay out of the public status projection.

A crash after publication may reconcile the original invocation and bytes without another start. An in-flight smoke crossing a boot, a failed invocation, or missing original success proof remains held. This is not automatic recovery of every interrupted setup.

## Timer and cron recovery

Existing core timers restore their captured enabled/active combinations; held siblings do not authorize rearming. Existing ancillary timer intent is preserved. Only timers captured as fresh are explicitly enabled/started, with intent journaled before effects and readback afterward. Reboot activation after this attempt's durable enablement is reconciled without another start. Reconciled enablement receives the same filesystem durability barrier as an issued enable command.

Cron retirement captures private preimage and postimage bytes, preserves unrelated entries, records applying before mutation, and accepts only the exact observed postimage after interruption. A failed crontab read is not an empty crontab. An ambiguous old or foreign postimage is held, not overwritten. The existing cron filesystem is synchronized before final applied acceptance.

The failure finalizer preserves successfully published artifacts and transaction evidence. Caddy's existing per-file existence rules continue falling through for absent external files; no public tree is moved away after partial success.

## Qualification

The source review JSON contains exact receipts and file hashes.

| Qualification | Result | Scope |
|---|---:|---|
| Final Linux source-owner suite | 60 passed | Real flock, exec and Git in isolated fixture trees; fake systemd, no production unit/timer/source mutation |
| Initial six affected suites | 633 passed, 28 skipped, 10 failed | Seven extraction/mutex assertions and three sparse-registry PCE cases were investigated |
| Corrected Git history/store suites | 43 passed, 28 skipped | All seven source-anchor failures resolved without weakening the tests |
| Exact PCE registry qualification | 3 passed | Same baseline watcher/parser/validator and test bodies; supplied exact committed omitted registry in memory |
| Shell/diff checks | Recorded in review | Four affected shell scripts parse; whitespace qualification |

The initial six-suite failures are retained as evidence rather than relabeled as an all-green run. The PCE registry is data/release_forecast/official_actual_defects.json, 1,137 bytes, SHA256 2ea3fbac3770766cd97356cf1d33d2aff1fd248cfe73439bd625711eef512b67, identical to base334b26b. No sparse checkout settings or registry source were changed. Those tests are qualification with captured baseline data, not an ordinary full-checkout result.

The Linux fixtures cover source admission/recovery, timer intent, journal persistence failures, incomplete mirrors, environment publication races, invocation attribution, coalescing, cron failure/recovery, stage contradictions and terminal receipts. They do not prove actual provider freshness, all ancillary processes, production cutover or authenticated browser behavior.

## Controlled first-adoption sequence

The old installed updater does not know this barrier. A source merge followed by its automatic reset is therefore not an acceptable first-adoption proof.

1. Satisfy existing CI/protected-source/release requirements. Keep PR10780 unarmed until ready.
2. Through the existing release owner, pause only the incumbent code-updater scheduling and drain its fd9. Capture scheduling intent. Live data timers remain under their existing owner.
3. Obtain the exact accepted merged Git object without resetting the serving checkout.
4. Execute the captured, qualified setup script's install-only mode against that exact revision. Do not pass new flags to an old checkout script that may ignore them.
5. Verify installed owner bytes/mode and no unresolved transaction.
6. Invoke ordinary update separately. It installs guards, drains the original core readers, resets the captured target and completes mirrors before restoring timer intent.
7. Run live setup through that same installed owner, preserving existing environments and timer intent. Require invocation-bound publication proof and terminal completion evidence.
8. Restore the incumbent code-updater scheduling only after its captured intent and current publication are verified.

This sequence is a source-qualified runbook; none of its production mutations has been performed by this milestone. No unmerged overlay, ad-hoc uvicorn process, alternate updater or raw source reset is authorized.

## Next material work

Finish the fixed auxiliary byte capture and existing input adapter, then bind actual collection/composition/publication to the incumbent lane and mount the already qualified API factory. Terminal's managed operation has now been admitted and its original native candidate is being corrected against actual wrapped Macro fixtures. CI registration remains subject to its explicit capability denial; holdings retains its original uncertain-effect fence. After release, prove consecutive data generations while frontend/code deployment stays unchanged, authenticated beta consumption, failure retention, recovery and the remaining registered page families.
