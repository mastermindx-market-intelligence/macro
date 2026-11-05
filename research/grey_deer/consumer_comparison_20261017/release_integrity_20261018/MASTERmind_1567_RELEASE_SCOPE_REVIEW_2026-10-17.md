# Mastermind #1567 — full release scope review

**17 October 2026 · Independent, local read-only evidence review**

**Disposition: preserve source acceptance; full release qualification and runtime acceptance remain open.** The evidence supports the merged source repair and identifies an exact archive. It does not qualify the full archive for production, prove rollback or activation behavior, or establish current book, policy, prompt, ledger or user-delivery parity. No deployment, live read, provider call or production mutation was performed for this review.

## Evidence examined and its limits

The primary evidence is [SOURCE_RELEASE_PREFLIGHT_20261017.json](../SOURCE_RELEASE_PREFLIGHT_20261017.json), **213,956 bytes**, SHA256 **e1aa32bb50cd59103c58fe9275bfca861f50ae3a66f733658ac92132b790f49e**. The adjacent [consumer reproduction README](../README.md), [source repair receipt](../SOURCE_CLOCK_REPAIR_20261017.json), and [source-consumer audit](../../risk_radar_source_consumer_audit_20261017.md) were also read. Their older pending statements remain historical; the later merge proof controls the source disposition.

| Boundary | What the retained evidence establishes | Remaining limitation |
|---|---|---|
| Source repair | Reviewed head `1e6a8a23fac1153eaef6c5b2f97525f0d960980f`; merge `b08223680180dcffdca7de10b03831dee3e1c287` at 10:59:54Z; successful native queue run `39025482211`; 184 native tests recorded. | This review verifies the receipt and scope, and does not independently repeat the code review or tests. |
| Merge readback | At 11:02:02Z, the fetched master was the merge commit; the candidate and merged trees matched; both owned blobs matched. | This is a dated observation, not proof of the current remote ref. |
| Owned source | `brain/market_view.py` blob `68c923556b0342c725dd7e208709a9421e2dbafd`, SHA256 `bdd2b29821c891f72a2c65b3f487d02b3bba31d2bb5058cd50ca96d9876daf66`; test blob `fae0f27b322b35f03a94556f8fa96d7c8fd9d340`. | The test file is not itself a production transfer requirement. The surrounding release includes other changes. |
| Archive | `git archive --format=tar b08223680180dcffdca7de10b03831dee3e1c287`, Git 2.46.1; 96,542,720 bytes; SHA256 `32afa2d1e43767d0130ed01dbf3ca5663291af5eec8227ac214261a3a68c324b`. | `stored:false`: the receipt binds a streamed archive, not a locally retained artifact inspected here. It contains no archive member, mode, symlink or transport manifest. |
| Observed runtime | Marker and health commit `732cf7be88e7159b4995a8885fbd381cd1484e3e`; active service; a six-second timeout followed by a successful 20-second-bounded health request; reasoning-policy and scheduled-runtime checks true. | The runtime subsection has no independent observation timestamp. The receipt's top-level time is 10:48:50Z and its checkpoint update is 11:06:32Z. Neither establishes runtime identity now. |
| Installed repair | The two installed source hashes matched the pre-repair reproduction; `market_view.py` SHA256 was `0dbf3c0dfd6beb0dec09cf7566967e4c0729a75d108bf3041145c76da2789e2b`. | The repair was not installed at that observation. A healthy old revision does not prove corrected behavior or current portfolio invariants. |

The receipt declares `autonomous_production_deploy: prohibited` and an exact-current-`origin/master` requirement for `scripts/deploy_from_git.sh`. The parent supplies current canonical procedure authority at `ad125292b34f313924f9719b8de772027f0ea225`; this local review does not re-read or supersede that procedure. The receipt's historical protected source base is `a552a5e506ae808efa575c2e13cb56f478c72b87`. These identities must not be conflated.

## Complete inventory census

Every object in `release.candidate_changes_since_live` was parsed and included below: **1,507 unique paths**, one path per object, each object containing only `status` and `paths`. There are **1,205 additions and 302 modifications**, with no recorded deletions or renames. No row contains a patch, source bytes, blob hash, file mode or deployment classification.

| Top-level path | Added | Modified | Total |
|---|---:|---:|---:|
| `tests` | 386 | 88 | 474 |
| `integrations` | 361 | 50 | 411 |
| `research` | 180 | 0 | 180 |
| `control_plane` | 53 | 51 | 104 |
| `docs` | 79 | 15 | 94 |
| `app` | 55 | 32 | 87 |
| `ops` | 36 | 25 | 61 |
| `scripts` | 19 | 12 | 31 |
| `plugins` | 3 | 13 | 16 |
| `common` | 6 | 5 | 11 |
| `skills` | 11 | 0 | 11 |
| `brain` | 7 | 1 | 8 |
| `config` | 4 | 2 | 6 |
| `patches` | 4 | 0 | 4 |
| `requirements` | 1 | 2 | 3 |
| `.github` | 0 | 2 | 2 |
| `.codex` | 0 | 1 | 1 |
| `AGENTS.md` | 0 | 1 | 1 |
| `CLAUDE.md` | 0 | 1 | 1 |
| `pyproject.toml` | 0 | 1 | 1 |
| **Total** | **1,205** | **302** | **1,507** |

Reproducible inventory identity: SHA256 **a42cb27b4c2eb62b2f21c0315313337c7ecaf13f75322c1ea44638d4b59cf51b** of the array serialized with Python `json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()` and no newline. This derived hash supplements the unchanged original receipt.

The 411 integration paths include **302 under `integrations/session_bridge`**, with base/candidate snapshots, fixtures, tests, patches and qualification artifacts mixed with modules. There are also tests outside top-level `tests`. Consequently, subtracting 474 from 1,507 does not establish the production transfer count. Likewise, 897 `.py` paths do not establish 897 active runtime modules. The absence of repository deletions does not prove that the release transport cannot delete destination files; that depends on its actual synchronization flags and exclusions.

## Concrete review priorities

These are **risks to resolve from the observed path inventory**, not findings that the named changes are defective or activated.

| Priority / surface | Concrete evidence in the inventory | Evidence needed for qualification |
|---|---|---|
| 1. Release scope and state transitions | The receipt names a full-source archive, synchronization, backup/rollback, service stop/restart and a forward-evaluation marker/baseline/activation transaction. The release wrapper is not among the changed paths. | Read the exact wrapper and referenced helpers anyway. Bind source root, destination, exclusions, delete/mode/symlink handling, dependency steps and restart/activation order. A changed-path list cannot supply these facts. |
| 2. Portfolio risk consumption | `brain/market_view.py` changes; seven `brain/liquidity_lab` modules are added, including adapter, estimator, eventization, ledger and validation. | Establish which shipped modules the installed portfolio service actually imports or activates. For the accepted repair, prove future-source facts remain visible as stale/advisory and cannot enter validated posture tilt; preserve ordinary clock behavior. Addition alone does not establish liquidity model activation. |
| 3. Runtime compatibility | `pyproject.toml`, Linux and macOS gate locks change; a research-producer lock is added. Rust manifests and desktop update code also change under `app`. | Identify the dependency source actually used by the production wrapper and the installed environment. Bind the relevant Linux/Python dependency changes and any generated/build artifacts. Do not assume gate locks are installed at release, or desktop files are executed by the portfolio service. |
| 4. Authority and execution surfaces | 104 `control_plane` paths, 61 `ops` paths and 11 `common` paths include privileged broker/client, worker execution, runtime/service, routing, wake ledger, installer and service-control changes. Configured capabilities and worker routes change. | Map actual service entry points, imports, consumed configuration and invoked subprocesses to transferred changes. Reuse exact-commit owner qualification for affected surfaces; otherwise inspect the concrete delta. Names alone cannot prove authority expansion or safe inactivity. |
| 5. Interfaces and installed integrations | Changes include company authorization, MCP adapters, Studio gateway/private services, session bridge runtime ownership/return, web authentication and browser relay/deployment. | Determine whether the standard archive reaches or is consumed by these installed services, whether the wrapper restarts them, and which version contracts cross the boundary. Review only the resulting active dependencies before expanding the release claim. |
| 6. Embedded evidence and instructions | Research, documentation, skills, plugins, root instruction files, fixtures and patches are part of the source inventory. | Apply the real transport rules. Confirm which instruction/configuration files are consumed at runtime; do not discard all documentation as inert or treat retained patches as applied code. Existing studies and evidence remain preserved. |

No file contents for these 1,507 rows are supplied. This review therefore **does not certify semantic safety of the full bundle**. The narrow repair's successful CI and exact blob readback remain useful evidence without being generalized to every release effect.

## Smallest useful next inspection and acceptance sequence

1. **Read the pinned wrapper, then only its actual helper chain.** Start with `scripts/deploy_from_git.sh` at candidate `b082236…` and the observed installed baseline `732cf7…`. Extract exact referenced deployment, health, backup, rollback and activation helpers, transport filters and service identifiers. Do not execute a presumed “preflight” branch until its no-effect behavior is established from source. Record hashes and resolved references; environment variable names and file references suffice at this stage, without credential values.

2. **Derive the exact release manifest.** From those rules and the bound archive, list included/excluded files, modes, symlinks, destination paths and any generated/dependency effects. Bind a native no-effect itemized transfer plan to an observed installed tree if supported. Separate repository changes, actual transfers and active runtime dependencies. Reconcile a later `origin/master` advance explicitly: the wrapper's exact-master requirement does not authorize silently releasing a successor commit under this archive's evidence.

3. **Qualify the active changed dependency set.** Resolve the installed service's entry point and effective configuration references, then inspect reachable changed code and relevant existing owner evidence at the exact release commit. Reuse the 184 accepted repair tests for their declared scope; add checks only for concrete uncovered release risks. For the changed consumer path, use the existing isolated comparison mechanism with fixed input clocks and no provider, scheduler, policy, book or ledger writes. Full live parity requires separately captured, coherent before/after evidence; fixture output is insufficient.

4. **Make rollback and activation concrete before the production decision.** Identify the retained rollback artifact, checksum, restore scope, dependency compatibility and rollback triggers. Establish which mutable state the backup covers and what must survive restoration. Inspect failure handling and ordering across source installation, restart, health, marker/baseline publication and activation, including retry/idempotency behavior. Restoring code alone cannot be assumed to undo an activation or ledger write; replaying a backup must not lose or duplicate subsequent fills or journal entries. These are open questions, not observed failures.

5. **Present the exact operation for the canonical production decision.** The reviewable package needs the final commit/archive/transport manifest, active-dependency qualifications, installed baseline, expected health and changed-consumer outcomes, activation effects, invariant comparisons and rollback procedure. Current authority and release ownership remain with the parent and the canonical owners. This review creates no deployment permission.

6. **After an authorized release, accept runtime and delivery separately.** Verify installed marker and source hashes, exact-commit health and scheduled/reasoning-policy checks, expected activation evidence, and coherent policy/book/account/fill/prompt/forward-ledger comparisons. Then obtain the real entitled consumer input/output and user-visible result. Record a naturally observed future-dated case only if one actually occurs; controlled regression evidence must remain labeled as such.

**Next action for the parent:** the read-only wrapper/helper inspection in step 1. It is the smallest missing source slice that determines which later inspections are necessary. The full release remains unqualified; the accepted source repair and historical evidence stay intact.

## Addendum — pinned release scripts reviewed, 17 October 2026

The parent supplied [deploy_from_git.sh](source/scripts/deploy_from_git.sh.txt) and [deploy_code_to_vps.sh](source/scripts/deploy_code_to_vps.sh.txt), reporting byte identity between baseline `732cf7be…` and accepted merge `b0822368…`. I read all 47 and 340 lines respectively and verified the supplied local bytes:

| File | Bytes | SHA256 |
|---|---:|---|
| Wrapper | 1,493 | `b983a9e88f6eddeac00929797d1e05c80e09e3c206bcabf4e26342fdb7dbb42f` |
| Deployment helper | 14,934 | `c158fc903121b8c4ad680049ded16000913393039944c6eec3a23d44ca376204` |

This completes the first source inspection proposed above. **It identifies a concrete mismatch between synchronization scope and rollback scope. Full release acceptance remains open.** Neither deployment script, its shell commands, a live dry-run nor any first-party module was executed. Local standard-library text inspection supplied the counts below.

### Exact synchronization and rollback boundary

The wrapper fetches the configured remote/branch, resolves the requested commit and rejects a mismatch, then archives that commit and invokes its executable deployment helper. Its defaults are `origin/master`, but `MASTERMIND_GIT_REMOTE` and `MASTERMIND_BASE_BRANCH` can select other values. Qualification must bind the actual settings to canonical authority; the source does not independently hardcode `origin/master` regardless of environment. The deployment helper has no dry-run-only exit mode: its internal dry-run is followed by potential production mutation.

The helper synchronizes the **entire archive root** with `rsync -az --delete`, using the same exclusions for its preceding `-azn` inspection. It does not limit transfer to `DIRS` and `FILES`. All exclusions are slash-free patterns, applied to matching path components and therefore to descendants of matching directories:

```text
.git .github .worktrees .venv venv data vendor vendor_*
__pycache__ *.pyc *.pyo node_modules *.sqlite *.sqlite-* *.db *.log
.DS_Store *.lock .pytest_cache .mypy_cache .ruff_cache .env .env.*
tmp catboost_info {_DB} tests .deploy_prev .deployed_git_sha
```

`DIRS` and `FILES` instead define the remote `.deploy_prev` snapshot and restoration scope:

```text
DIRS: app brain bot portfolio data_layer loop bridge control_plane scripts
      config ops common integrations .claude .codex
FILES: pyproject.toml DOCTRINE.md README.md AGENTS.md .deployed_git_sha
```

Static component matching against **all 1,507 recorded repository paths** gives:

| Classification | Paths | Interpretation |
|---|---:|---|
| Excluded by the explicit patterns | 498 | 488 contain a `tests` component, four match `*.lock`, four match `*.log`, and two contain `.github`; these groups do not overlap in this inventory. |
| Eligible for synchronization and within named rollback scope | 711 | Includes eight `brain` paths, 401 integration paths, 104 control-plane paths and other named roots. |
| Eligible for synchronization and outside named rollback scope | **298** | **269 additions and 29 modifications** have no snapshot/restore coverage in the helper's lists. |
| **Total** | **1,507** | Complete static partition; no live transfer claim. |

The 298 uncovered eligible paths comprise **research 172; docs 94; plugins 16; skills 11; patches four; and root `CLAUDE.md` one**. A successful code copy can change these paths, while `rollback_release` does not restore or remove them. Their runtime consumption remains to be established; the coverage mismatch itself is visible in source. Restoration of all shipped material therefore cannot be certified. Destination files deleted by `--delete` may introduce additional uncovered restoration needs beyond this repository-delta inventory.

The three recorded requirements locks and `Cargo.lock` are excluded. `pyproject.toml` and `Cargo.toml` are eligible. There is no package installation or environment rebuild command in these two scripts; installation effects inside the separately invoked tag helper or forward-evaluation module have not been reviewed. Existing environment compatibility remains necessary. Tests with names such as `*.test.tsx` or `test_*.py` outside a directory named `tests` are not excluded by a filename test rule.

The 1,009 eligible repository paths are **not** an observed transfer count. The actual source archive, installed destination, modes, existing extra paths and effective options determine the transport. The script's logged `N` counts nonempty dry-run lines after filtering names ending in `/`; that output is not retained in the supplied preflight receipt. Backups use whole-directory `cp -a`, without synchronization exclusions: excluded files nested under a backed-up directory can consequently be restored as part of that directory. The canonical live-data root defaults outside the code root, but effective path overrides and all writer locations still need binding.

### Actual transaction order and remaining risks

1. **Inspect, then back up.** After the internal dry-run, a zero-path result exits only if expected-commit health and `portfolio.forward_evaluation status` pass. Otherwise it reads the previous marker and whether the forward start marker exists, deletes the previous `.deploy_prev`, then copies its named scope. The remote backup loop does not accumulate individual copy failures: a failed earlier iteration can be masked by a successful final iteration. Backup completeness needs explicit evidence; a zero SSH exit alone is insufficient for that claim.

2. **Copy before stopping the old service.** It synchronizes source, writes `.deployed_git_sha`, and conditionally invokes `scripts/refresh_datadog_release_tag.sh`. It then stops the configured service, default `mastermind.service`. Thus the observed order allows the old process to remain running during source replacement; safe lazy imports, subprocess launches and all writers being stopped by that one service command are unproved. The source contains no overall deployment lock or general failure/signal rollback trap; the explicit failure branches call the rollback function.

3. **Require no settlement residue.** With that service stopped, the helper checks the `autonomous`, `china` and `hk` book directories. Any existing `paper_transaction.json` or any top-level `settlement_receipts/*.json` blocks release and triggers rollback. The gate does not inspect receipt content or version: its observable rule is presence, despite the explanatory comment about older/unfinalized receipts. It does not itself finalize settlement. The canonical recovery reader must explain which retained objects legitimately remain and how the old runtime clears a blocking object.

4. **Bind US authority bytes, then initialize.** The helper requires readable canonical US `account.json` and `fills.jsonl`, records their SHA256 values, and calls `python3 -m portfolio.forward_evaluation init --deployment-sha … --asof <current UTC date>`. It then restarts the service. Those hashes are also written to the deployment log. This is a useful explicit missing-data refusal and byte baseline, but it covers neither China/HK book hashes nor policy, prompts, other journals or the whole forward ledger.

5. **Check health, then compare under the book lock.** It makes up to eight health attempts, each after a three-second pause, with a six-second HTTP timeout. Success uses `curl -f` and text matches for expected commit, `reasoning_policy_ok:true` and `scheduled_runtime_ok:true`; it is not a deep invariant check. Afterward it acquires `book:autonomous.lock` with a 30-second wait, requires both account/fill hashes to remain equal, and runs `forward_evaluation finalize` followed by `status` while holding that lock. This is an explicit compare-before-activation gate. Its adequacy depends on the module's semantics and all relevant writers honoring the same lock. The earlier retained six-second health timeout followed by a successful longer probe means the release probe's timing has not yet been qualified against this runtime.

6. **Rollback is narrower than activation and weaker than forward health.** For a start marker classified as newly created by this operation, rollback removes `portfolio_forward_evaluation/start.json`. A successful `init` result that says it did not initialize clears that ownership flag, protecting the documented concurrent-initializer case. Other marker/ledger side effects, existing-marker changes and failure-after-finalize behavior depend on the unread module. The function restores only `DIRS`/`FILES`, adjusts a Datadog version drop-in if the base drop-in exists, reloads systemd in that case, and restarts the old service. It probes previous-commit health once after four seconds with the scheduler check disabled. **That health result is logged but not included in the function's return status.** A `503` can therefore accompany a zero rollback return if restoration and restart commands succeeded. `fail_release` exits unsuccessfully regardless, but it suppresses the rollback return; no downstream acceptance should interpret the words “rollback complete” as proof of restored health.

### Next source reads, in risk order

| Priority | Actual source or reference warranted by these scripts | Question it resolves |
|---|---|---|
| 1 | `portfolio/forward_evaluation.py` at `732cf7be…` and `b0822368…`, then only its actual imported state/writer helpers | Exact `status`, `init`, `finalize`, marker ownership, idempotency, schema compatibility, lock interaction and durable effects. Can code restoration plus the stated marker deletion recover every failure point? |
| 1 | The configured service unit and effective drop-ins, beginning with default `mastermind.service`; then its actual entry point and health handler | Which processes/writers stop and restart, what reads the commit marker, whether the health fields attest the intended runtime, and which changed files or instructions are consumed. These source paths are not named by the scripts and must be resolved rather than guessed. |
| 1 | Canonical settlement reader/recovery source located by the exact `paper_transaction.json` and `settlement_receipts` references | Whether the installed revision can clear each blocking state safely before release and how schema/read compatibility is maintained. No settlement recovery should be executed as part of this review. |
| 2 | `scripts/refresh_datadog_release_tag.sh` at both pins | Conditional external changes, service/reload effects and restoration of `/etc/systemd/system/<service>.d/81-datadog-version.conf`. This helper is explicitly invoked before the service stop. |
| 2 | Reachable consumers of eligible but uncovered `CLAUDE.md`, docs, plugins, skills, patches and research paths, determined from the actual service/deployment references | The significance of the demonstrated 298-path rollback gap. A harmless-consumption finding would narrow impact; it would not make those files restored. |

The **highest-value next supplied source is `portfolio/forward_evaluation.py` at both pins**, alongside the effective service definition when available. The parent should carry the rollback coverage mismatch and health-return limitation into the existing release owner's qualification. Unchanged scripts do not establish safe deployment of a materially expanded archive, and this addendum grants no production decision or writer authority.
