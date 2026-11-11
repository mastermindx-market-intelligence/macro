# Alert Intelligence Fabric — Sol review and design-entry ruling

**Ruling: PASS FOR VISUAL DESIGN. Capability state: SPEC_ONLY.** This closes the architecture-to-Figma review gate only. It is not PR merge acceptance, independent review, implementation completion, a database authorization, an email activation, or production acceptance.

**Current authority:** Chris explicitly directed this session to conduct the review itself and continue without spawning subagents. Sol performed the review. The previous requirement to wait for another reviewer is superseded for this design-entry decision, not for later implementation or release gates. No new reviewer was invoked.

**Carrier:** Macro Draft PR #7135, `sol/alert-fabric-architecture-20260913`; reconciled pickup head `b75ed814563c512482343aeb7c0a01d349cc5acb`. Operation: `alert-fabric-design-entry-20260914-sol-001`. No new branch, workstream or runtime Job.

## 1. Exact basis and source reconciliation

The controlling design basis is the existing v0.3 functional specification, the committed `V03_REVIEW_AMENDMENTS_20260913.md`, and the specific choices below. The existing `FIGMA_EXECUTION_BRIEF_20260913.md` is the execution brief, subject to this ruling. Earlier v0.1/v0.2 are background. The attached v0.3.1 packet is reviewed input, not a replacement for newer repository amendments.

- v0.3: blob `648079977f71f2efa96a2d940e7468c8a214f439`; SHA256 `57845f1b7dd4c36063c74f6c73d3861362540d9ad0f8685e7d17f322ce8ca945`.
- Committed amendments: blob `368a51d347731a33ef8066a9a791d53b5831405f` at pickup head.
- Canvas brief: blob `5040865deecb40fe7d48f7da8a427e8ed0b95713` at pickup head.
- Attached v0.3.1: SHA256 `ab10af5eca299a554267896a862354b2ed78cb7cee86eab14dfe49658ed9e794`; author-side report SHA256 `009d3c7c8133fb4e5bede710437619a20cfbd533dbdc480a9260c339d575834a`.
- Current procedure: compatible Skillpack 1.0.1, Mastermind protected commit `6f77fb69494958cd984f3c03d4f8f9cc2b20b878`; INDEX, REVIEW_RETURN, RECONCILE_STATE and CLOSEOUT read at that pin.
- Source review: Macro `a9aa2ef69943d635af19c4149a78e91b72e465c0`; Terminal `1aca671d93c965a7cc9c3a92c5d28b1ae836ee77`. Historical fixtures remain at their declared pins, not relabeled as current inputs.

Six material Macro implementation blobs were checked individually at the current pin: Prophet producer, board reader, card stance helper, private source router, alert drain and mailer match their v0.3 recorded blobs. F08 and the active Terminal theme decision were reread. Terminal's single-commit movement changes research-view/account evidence, AI quota copy and i18n; it does not replace the alert/schema owners inspected here. This is bounded source compatibility, not a full integrated-candidate or production proof. The large Macro comparison is not used as an exhaustive changed-file census.

The repository already contains a completed one-shot review record and newer amendments. They are preserved. The unobserved `...-003` tools-disabled report at Studio PID 82781 remains unobserved; no PASS, cancellation or process completion is inferred. The Studio is currently reported offline. This task does not retry that invocation or wait for it as a design prerequisite under the current Chairman directive. Any subsequently recovered material finding must still be evaluated on its merits.

## 2. Final review dispositions

| Concern | Final design decision | Disposition |
|---|---|---|
| Source change versus monitor baseline | Native event identity or the source adapter's canonical predecessor/successor defines the change; a user's last visit/checkpoint never re-keys it. A method-era rollout needs a baseline/adoption rule and a single active delivery owner or proven identity bridge. | Closed for design. |
| Overlapping notification modes | Keep the committed amendment's stronger order: global refusal/access/category rules, positive request, account digest-only cap, then the most immediate permitted request; quiet hours/interruption limits determine actual time. Local v0.3.1 wording does not override the account cap. | Closed for design. |
| Temporarily unreadable policy | For an authorized notice and a persisted positive email request, preserve an `awaiting_policy` intent in the existing outbox in the same transaction as notice/progress. No send until eligibility resolves. Known opt-out is not unknown policy and creates no retrospective mail obligation. | Closed by clarification below. |
| Trusted monitor progress | Select separate `evaluation_state` and database-maintained `definition_version` on the existing `alerts` owner for the new subtype. Do not store trusted progress in client-editable definition JSON. Database and API controls must enforce this; a stale-definition evaluation cannot advance progress. | Closed for design; implementation proof owed. |
| Digest time identity | One schedule version plus UTC half-open window boundaries, IANA zone and resolved offset. One slot per intended local date/time; use the first repeated occurrence and first valid instant after a skipped time, shown in preview. Timezone changes apply prospectively. | Closed for design. |
| Email identity and uncertainty | Keep the committed outbox `fire_event_id` to existing mailer-key mapping. Membership/prose changes do not change that identity. A possibly attempted envelope stays fixed; an unknown result is not retried under a new key merely to clear it. | Closed for design. |
| Interpretation correction | Keep the committed owner-adopted correction identity even when market source bytes do not change. It produces a linked explanation correction, not a fictional new market event. Cosmetic rewriting produces none. | Closed for design. |
| Reachable host/theme states | Macro: dark/light, EN/ZH, desktop/mobile. Current Terminal shell: dark, EN/ZH, desktop/mobile under its active decision. No local Terminal light-theme fork. | Closed for design. |

### Policy-recovery assignment: one consistent rule

The awaiting-policy case concerns an already authorized notice and a real saved email request. If source/on-site authorization is itself unknown, restricted content remains withheld and no successful-consumption marker is advanced. Policy recovery never invents consent.

Preserve the awaiting-policy outbox row and assignment. Recovery prepares that row, schedules/defer it, or suppresses it with the actual reason. Do not blindly clear `email_outbox_id`. The general optional transfer language in the attached v0.3.1 is not adopted as permission to reassign possibly attempted or partially sent bundles.

For a required catch-up coalescing before any external attempt, select a **whole-bundle, transactionally recorded reassignment only**: verify both envelopes are unattempted and the receiving bundle is collecting; lock/revalidate versions, move every member with reciprocal references, retire the old unsent bundle using native suppression plus `reassigned_before_attempt` and a replacement reference, and commit atomically. Failed proof or any possible external effect refuses the reassignment. It is not user opt-out, not successful delivery, not deletion of history, and not permission for partial-bundle splitting. The existing queue remains the only delivery owner. Recovery must not release a burst of obsolete messages; the effective summary/time policy is shown to the user.

Within a still-collecting bundle, known refusal can withhold a member and preserve its recorded disposition. Temporary unknown eligibility defers that bundle; separately eligible immediate bundles may proceed. The send boundary must recheck all included content, including any model summary, after membership or permission changes. These specific rules supersede conflicting optional alternatives; no implementation is claimed.

## 3. Review method and limits

Sol read the original architecture and source rules, the newer repository amendment/brief, and the attached report/patch. The counterexamples were evaluated as specification behavior, not marked as executed product tests. The local package verifier was rerun: baseline/candidate/patch hashes matched, exact-preimage patch application in a temporary sandbox matched the candidate bytes, and its 25 declared case rows were present. That result establishes document integrity only.

The two 25-case lists are **different lists**, not 50 independent tests or two copies of one passed suite. The base 18 cases are shared. The committed A19–A25 and attached R1–R5/additional cases are reconciled in the disposition table; neither list is silently deleted or renumbered. Later implementation must map each distinct behavior to an actual discriminating test. No production browser, database concurrency, source-family extraction evaluation, customer email or independent PASS was obtained in this turn.

The author review is intentionally not called independent. It is sufficient for this design-entry gate because Chris explicitly selected Sol to conduct it. The first implementation still owes its ordinary code, source, privacy, data, model and real-path acceptance. The current card-helper precedence mismatch remains an implementation dependency, not a fix accomplished by writing this ruling.

## 4. Frozen product and design direction

The promise is one calm, intelligent attention experience: a useful Prophet-first Now view; complete accessible exploration; situations with before/after facts, qualifications, disagreement and supported relationships; precise monitoring promises; and original-versus-current evidence and delivery history. The fast source-only path must remain useful if deeper AI context fails.

Personal notices, read/archive choices and holdings/thesis relevance stay under the existing authenticated owner. Shared research remains available without a portfolio. A watchlist is not a holding; a candidate is not a currently available entry; a notification is not a trade; current evidence never silently replaces historical evidence. No alternative signal, identity, graph, portfolio, preference, event, scheduler or sender authority is selected.

Use the existing brief's ten compositions, with one connected primary prototype rather than disconnected attractive screens. First finish Now → exact evidence → supported Monitor this → effective delivery confirmation → return → meaningful update/correction. Then complete coverage/failure, History and email compositions. Every simulated behavior is labeled in the handoff; none is represented as shipped.

For the existing screenshot's access tiles, inspect actual component variants before reuse. Different colors with the same “Checking access” text do not express signed-out, restricted, source-unavailable and admitted states. Those states need distinct wording/actions, not just color. This is a design review observation from the supplied screenshot, not a claim that the actual Figma components were inspected.

The accepted product structure does not require enlarging the shared front page, redesigning the Macro dashboard, or adding another header. The two actual Alert Center V2 files must be compared before choosing working/reference roles. Preserve both; no third file or destructive merge of frames.

## 5. Exact next action and release boundary

**Architecture-to-design gate: closed by this Sol ruling.** Do not schedule another review, await a subagent, or repeat broad archaeology as the next step. File/component comparison is next, followed by the existing brief's primary prototype pass.

**Concrete canvas dependency:** both actual Figma Share URLs/file keys are missing. The native identity is `mastermindx6031@gmail.com`, Professional/Full. The historical `QO3CthsB5KzPVKdgfcVPMI` still returns an edit-access error; this says nothing about which newer draft is canonical. No file was edited, guessed or duplicated. The connected Opera browser is unavailable; the verified Studio is offline. Do not switch to unrelated devices or change permissions to guess the links. Chris has been asked for both Share URLs.

**Not release-cleared:** PR #7135 remains Draft; its pickup metadata reports a merge conflict. This ruling does not rebase/merge it or claim green integration checks. PR #7022 remains its separate implementation carrier and source-writer gates. No source code, shared schema, production setting, real email, runtime Job, subagent or watcher is created by this ruling. Capability remains SPEC_ONLY; Figma comparison and edits require the exact accessible file targets.

Once the two links resolve, inspect metadata, tokens, components, prototype paths and handoff notes in both, choose the least-destructive working file, retain the other as reference, and execute the existing design brief. There is no remaining self-imposed independent-review wait before that work.
