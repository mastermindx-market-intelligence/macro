# Plugin Integration Handoff — Research + Design + Host Access

Date: 2026-09-07
Parent: `WS:CHAIRMAN-CONTROL-ROOM`
Read first: `agentos/handoffs/CHAIRMAN-CONTROL-ROOM-PLUGIN-INTEGRATION-INDEX-2026-09-07.md`
Scope: Firecrawl, Context7, Canva, Figma, Opera Browser Connector, Remote Desktop Commander

## Mission

Give Sol and bounded workers reliable research, current technical documentation, design-production, visual-browser, and authorized-Mac capabilities without confusing capability with authority or creating a second evidence/control plane.

## Why it matters

This family materially improves research depth, product/design execution, and the ability to operate on authorized host resources. It also contains the highest-risk surfaces for stale web evidence, proprietary/right-restricted content, design drift, browser-session assumptions, and accidental interference with another worker's local state.

## Authority precedence

- Repository + primary sources own implementation/evidence.
- Agent OS owns durable organizational conclusions.
- Firecrawl/Context7 are evidence acquisition helpers, not self-authorizing truth.
- Canva/Figma own their design artifacts only; product thesis and acceptance remain with Sol/Chairman.
- Opera is browser transport/session control only.
- Remote Desktop Commander is host capability only; host access never expands organizational permission.

## Verified state

- Firecrawl: `PROVEN_LIVE` connector; monitor list call succeeded; no monitors exist.
- Context7: `PROVEN_LIVE`; current Next.js library resolution succeeded against a high-reputation library.
- Canva: `PARTIAL`; account is connected, root includes a dedicated `Mastermind-X` folder, but no Brand Kit is exposed.
- Figma: `PARTIAL`; authenticated account is visible, but current plan seat is **View** on Starter.
- Opera Browser Connector: `DARK_OR_DISCONNECTED`; call reports browser not connected and requires browser-side **Allow AI connection** plus Opera sign-in.
- Remote Desktop Commander: `DARK_OR_DISCONNECTED`; connector returned HTTP 401 Authentication failed during connectivity verification.

## Exact scope

### Firecrawl

Use Firecrawl when native web search is insufficient and the job specifically needs deep page extraction, site mapping, crawling, document parsing, or recurring website monitoring.

Implementation/order:

1. Define research question and lawful source scope first.
2. Prefer primary/first-party sources and preserve URL/timestamp/provenance.
3. Use map to locate pages before crawling a whole site when the relevant URL is unknown.
4. Use crawl/scrape only for the minimum needed pages/data.
5. Create a monitor only when a named continuing research need exists; do not create broad monitors merely because the capability exists.
6. Feed structured findings into the existing research/intelligence architecture rather than creating a Firecrawl-native truth store.

Acceptance:

- Real source material is retrieved.
- Important claims retain source provenance and date.
- Rights-sensitive/proprietary content is not copied into a corpus merely because it is technically reachable.
- A monitor, if created, has a defined consumer and action threshold.

### Context7

Use Context7 before coding against fast-changing libraries/APIs when freshness matters.

Implementation/order:

1. Resolve the official library ID.
2. Prefer high-reputation official docs with version match where available.
3. Query only the API surface relevant to the bounded implementation.
4. Reconcile documentation against the actual repository dependency/version before changing code.

Acceptance:

- The implementation uses an API documented for the repo's actual/current version.
- Context7 does not override repository code, tests, or production behavior when they disagree.

### Canva

Current account is usable for design discovery/production, and a `Mastermind-X` folder already exists.

Setup actions:

1. Use `Mastermind-X` as the default organizational folder unless an existing more-specific project folder is found.
2. Decide whether a Mastermind Brand Kit is needed for repeatable production. The connector currently returns no Brand Kits; do not pretend branding is centrally configured.
3. Before creating an on-brand design, verify current brand assets/rules from canonical brand artifacts rather than hallucinating them.
4. For edits, follow Canva transaction semantics: start -> perform operations -> preview -> commit/cancel. Draft edits are not completion.

Acceptance:

- Final design is visible in the intended Canva folder.
- Brand consistency is traceable to approved assets/rules.
- Design output is a real user-facing artifact, not just a generated candidate.

### Figma

Do not start a write-oriented integration until the current **View** seat limitation is resolved.

Setup actions:

1. Future session calls `whoami` first.
2. If the intended workflow requires file creation/editing/code-to-design writes, obtain the appropriate seat or file/team permission.
3. Re-test on the actual Mastermind design file/project.
4. Once write-capable, integrate against existing components/design-system assets; do not create a parallel design system.

Acceptance:

- A real Mastermind file is readable.
- For write workflows, a bounded edit/file creation succeeds under authorized permissions.
- User-facing work gets visual proof and is reconciled with implemented product behavior.

### Opera Browser Connector

Setup blocker is outside the model session: the Opera browser-side connector is not connected.

Setup actions for a future session:

1. In Opera Browser Connector, enable **Allow AI connection**.
2. Sign in with the intended Opera account.
3. Call `list-tabs` and confirm the intended browser/session is visible.
4. Read the target tab before navigation/action.
5. Never infer that browser access grants permission to perform unrelated account changes.

Acceptance:

- `list-tabs` succeeds on the intended browser.
- One harmless page read succeeds.
- Any modifying browser action is separately authorized by the user's task.

### Remote Desktop Commander

Current blocker: HTTP 401 authentication failure. Do not ask Chris to relay shell commands while a reconnect could restore the authorized host bridge, but do not claim host access until verification succeeds.

Required startup sequence after reconnect:

1. Discover current Remote Desktop Commander schemas if needed.
2. `list_devices`.
3. Select the intended authorized Mac/device.
4. `ping` that exact device.
5. Only then use native file tools for files and process/terminal tools for shell/process work.

Host operating rules:

- Connected Mac != ChatGPT sandbox.
- Do not touch another worker's worktree/process.
- Do not broaden permissions.
- File/shell access does not prove browser/provider-session control.
- Timeout/cancellation does not prove no effect; reconcile before retry.

Acceptance:

- Intended device is online and pinged.
- A harmless read on an authorized path succeeds.
- The exact device/path/process scope is recorded in the continuation handoff.

## Data / time / null / correction behavior

- Web/design/browser evidence is timestamped and potentially mutable; record retrieval time for material decisions.
- Missing pages/components/assets are nulls, not license to synthesize invisible state.
- For visual design, distinguish design spec, implementation, deployment, and production visual proof.
- For source corrections, update derived conclusions rather than preserving stale scraped claims as current.

## Deterministic vs model method

Deterministic: connector capability checks, file/page/component IDs, retrieved source metadata, tool-permission state, transaction commit status.

Model: research synthesis, design critique, source prioritization, UX judgment. Model interpretation never overrides explicit source/permission state.

## Failures

- Firecrawl retrieval failure: fall back to another lawful source or native web only if it satisfies the same evidence need; do not fabricate missing content.
- Figma permission failure: stop at permission boundary; do not duplicate the artifact elsewhere to evade access controls.
- Opera/RDC auth failure: report exact app/connection/auth issue.
- Unknown-effect edit: re-read the design/host/browser state before retry.

## Non-goals

- No proprietary competitor corpus replication.
- No second research database merely for crawler output.
- No parallel design system.
- No assumption that visual mock = shipped product.
- No unattended host control without verified device/session authority.

## Continuation handoff

Record the exact connector, account/workspace/device/file used, permission state, evidence/proof, unresolved blocker, and exact next action in Agent OS after material work.

## Stop condition

Stop if rights, permissions, account identity, target device, write effect, or canonical artifact ownership is ambiguous and cannot be resolved by a read on the same carrier.
