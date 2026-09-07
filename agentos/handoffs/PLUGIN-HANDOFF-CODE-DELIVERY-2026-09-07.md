# Plugin Integration Handoff — Code + Delivery

Date: 2026-09-07
Parent: `WS:CHAIRMAN-CONTROL-ROOM`
Read first: `agentos/handoffs/CHAIRMAN-CONTROL-ROOM-PLUGIN-INTEGRATION-INDEX-2026-09-07.md`
Scope: GitHub, GitLab, Vercel, Render, BasicDeploy

## Mission

Make source-control and deployment plugins useful to Sol and bounded workers while preserving one canonical implementation/evidence path and explicit per-service deployment ownership.

## Why it matters

These connectors can let a CEO session inspect code, PRs, CI, deployments, services, logs, and production evidence directly. Their largest risk is false completion or accidental multiplication of source-control/deployment authorities.

## Authority precedence

- GitHub remains canonical implementation/evidence for the current Mastermind estate.
- Merge, CI green, deploy, production proof, and final acceptance are distinct states.
- GitLab is an optional interoperability/secondary SCM edge only unless the Chairman explicitly changes the authority ruling.
- Vercel/Render/BasicDeploy are deployment carriers. Ownership is per service; two platforms must not silently own the same production service.

## Verified state

- GitHub: `PROVEN_LIVE`; repository and protected Mastermind skillpack reads succeeded, and this handoff branch itself is being written through the GitHub connector.
- GitLab: `PROVEN_LIVE`; two private projects named `MastermindX-project` were found in two different namespaces, both newly created on 2026-09-07.
- Vercel: `PROVEN_LIVE`; team listing succeeded.
- Render: `PROVEN_LIVE`; workspace listing succeeded.
- BasicDeploy: `PROVEN_LIVE`; container listing succeeded.

Connector availability does not establish what is currently deployed where. Before any deployment mutation, perform estate archaeology against GitHub configuration and the target platform.

## Exact scope

### GitHub

Use GitHub directly for repository archaeology, issues/PRs, evidence, reviews, CI status, and bounded modifications under the current source-writer/branch rules.

Startup/order for modifying engineering work:

1. Recover current protected skillpack and governing handoff.
2. Read current default/protected branch state and recent relevant PRs.
3. Search existing implementation before adding a new path.
4. Create or use one bounded branch/carrier.
5. Make the smallest independently useful vertical slice.
6. Review against intent and no-rebuild boundaries, not just code style.
7. Validate CI/tests.
8. Merge only under appropriate review/permission gates.
9. Prove production behavior separately.
10. Record acceptance and exact next action.

Acceptance:

- PR/commit evidence exists.
- Intended capability is visible through a real consumer.
- Production proof exists where required.
- No spec/foundation-only change is called shipped.

### GitLab

Current ruling: **do not migrate, mirror, or split Mastermind's canonical SCM into GitLab by default**.

Two duplicate-looking private projects currently exist. A future session should first determine whether either has an intentional purpose before creating repos, pushing mirrors, or wiring CI.

Approved possible roles only after a named need:

- interoperability with a partner/team that requires GitLab,
- testing the GitLab plugin capability in a sandbox,
- importing/exporting a bounded artifact where GitHub remains canonical,
- a future explicit Chairman-directed SCM migration program.

Rejected by default:

- automatic GitHub mirror,
- second canonical PR/review history,
- split CI authority,
- duplicative issue/project management.

Next setup action:

1. Inspect both existing GitLab projects for contents/default-branch history.
2. Determine why two same-named projects were created.
3. If unused test artifacts, propose cleanup/archive rather than building on both.
4. Do not delete/archive without explicit scope and effect reconciliation.

### Vercel

Likely role: web/frontend/serverless deployment where the existing repository configuration proves Vercel owns that service. Do not infer service ownership from account connectivity.

Setup/order:

1. List teams/projects and identify projects actually linked to Mastermind repos/domains.
2. Inspect deployment/configuration and map repository -> project -> environment -> domain.
3. Record which service is production-owned by Vercel.
4. Use read-only deployment/log/diagnostic workflows first.
5. A deploy/redeploy/config/env-var mutation requires explicit scope and effect reconciliation.
6. Prove the real production URL/path after any accepted change.

Acceptance:

- A real service ownership map exists.
- Production deployment proof ties back to a specific Git commit/build.
- Browser-visible proof exists for user-facing work.

### Render

Use Render for services/datastores that repository + platform archaeology proves are owned there.

Setup/order:

1. List workspace/services/data stores.
2. Map each relevant service to repository, branch, environment, URL, dependencies, and deploy policy.
3. Identify overlap with Vercel or other carriers.
4. Read logs/metrics/deploy state before any write.
5. Trigger/deploy/configure only for a named service where Render is the established owner.
6. Verify production behavior after deployment.

Acceptance:

- Service ownership is explicit.
- No service is accidentally dual-deployed as canonical across Render and Vercel.
- Real production request/response or visible output proves the change.

### BasicDeploy

Default role: **sandbox/prototype carrier**, not production authority.

Use cases:

- isolated proof-of-concept web app,
- throwaway integration demo,
- temporary environment for a bounded artifact when it does not collide with existing production.

Before use:

1. List existing containers.
2. Name the prototype and its expiration/ownership.
3. Confirm no production domain/data/state is being silently duplicated.
4. Use synthetic/safe data where possible.
5. If a prototype is worth promoting, hand it back to the canonical repo/deployment architecture rather than letting BasicDeploy become an untracked production island.

Acceptance:

- Prototype has a real visible result.
- It is clearly labeled sandbox/non-authoritative.
- Promotion path points to canonical GitHub + owning production platform.

## Deployment ownership matrix to produce

A future session should materialize a table for every Mastermind service it touches:

`service | repo | canonical branch | carrier | project/service id | prod domain | env | deploy trigger | observability | last proven production SHA | owner`

Do not invent values. Populate by repository/platform reads.

## Data / time / null / correction behavior

- Preserve commit SHA, deployment/build ID, environment, and timestamp in proof.
- `latest deployment` is meaningless without environment/project context.
- Missing deployment linkage is a null requiring archaeology, not permission to redeploy.
- A rollback/redeploy changes evidence; update the production-proof record accordingly.

## Deterministic vs model method

Deterministic:

- commit/tree SHA,
- PR state,
- CI check result,
- deployment ID/state,
- project/service/domain mapping,
- HTTP/browser production proof.

Model:

- architecture review,
- scope decomposition,
- intent preservation,
- deciding whether evidence is sufficient for acceptance.

## Failure handling

- CI green but no production proof: remain BUILT_NOT_PROVEN.
- Deploy reports success but app path fails: not accepted; investigate real production path.
- Unknown deploy/config write effect: re-read the same carrier before retrying.
- Conflicting platform ownership: stop and reconcile; never auto-failover by creating another production deployment.
- GitLab/GitHub divergence: GitHub wins under current ruling unless explicit migration authority says otherwise.

## Non-goals

- No multi-SCM architecture because two SCM plugins are connected.
- No duplicate CI pipeline authority.
- No universal deploy abstraction that hides which carrier owns a service.
- No calling infrastructure setup “product complete.”

## Continuation handoff

After material work, record: repo/branch/PR/commit, deployment carrier/project/environment, production evidence, capability unlocked, unresolved issue, and exact next action.

## Stop condition

Stop when source-control authority, service ownership, environment, production target, or previous modifying effect is ambiguous and cannot be reconciled from the canonical repo plus same deployment carrier.
