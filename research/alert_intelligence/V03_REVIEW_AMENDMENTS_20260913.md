# Alert Intelligence Fabric v0.3 — bounded review amendments

**Status: SPEC_ONLY / REPAIRED_CANDIDATE.** These are specific architecture clarifications for design and later implementation, not deployed changes or permission to send email. This document amends the named clauses of `../ALERT_INTELLIGENCE_FABRIC_FUNCTIONAL_FREEZE_CANDIDATE_20260913.md`. Read both; all unamended owner, privacy, source and release boundaries remain.

**Carrier:** Macro Draft PR #7135, `sol/alert-fabric-architecture-20260913`. Reviewed v0.3 source at `91b077a8ced592781c71a65855d08a0305e0d789`, content SHA256 `57845f1b7dd4c36063c74f6c73d3861362540d9ad0f8685e7d17f322ce8ca945`. Sol owns adjudication under Chris's current continuation request. Compatible Skillpack pin: Mastermind `381d1ce9acd98143e2cb50f83747ed19162dddd8`.

## 1. Independent review and disposition

A fixed-packet, tools-disabled independent Sonnet review of v0.3 plus accepted F08 law returned **REQUEST_REPAIR**: an explicit delivery-key mapping, correction identity without a new market publication, and conflicting monitor delivery preferences. It also noted the need to specify withheld digest membership. This was a technical document review, not current-code inspection, production proof or domain-owner release approval.

Review operation `alert-fabric-v03-independent-review-20260913-sol-002`; provider session `0b0716ac-34b9-4d1d-9463-6ff83179283e`; parent-verified input SHA256 `8a42b14dee399cfed8c0b2620b23932efd6cb79877af03f93e95126f4a5fb25c`; completed exit 0, one turn, 172.68 seconds. Provider reported `claude-sonnet-5`. The reviewer quoted v0.3's historical pickup field as its source SHA; the wrapper, not the reviewer, verified the actual supplied immutable file/hash above.

The preceding operation `...-001` finished with exit 0 but returned no usable verdict/report. It is **INVALID_REVIEW_RETURN**, not a pass. It used plan permission mode despite having no tools. Its process was reconciled complete before the corrected one-shot invocation. Neither invocation changed project files or customer state; neither created a continuing worker/watch relationship. The two resulting reports do not constitute two successful independent reviews.

**Sol disposition:** accept the three missing-choice concerns, but do not copy the suggested fixes blindly. A notice must not acquire a mutable fire ID that changes when digest membership changes; the existing outbox remains the delivery identity owner. A correction's shared semantic identity must not be based on a private recipient's notice ID. A per-monitor request must not override the user's global delivery refusal or quiet hours. Sections 2–5 provide the narrower consistent rules.

## 2. Delivery identity: amend v0.3 sections 5.2, 6.1 and 6.3

A source change, a personal notice and an email envelope have different grains. Preserve those grains.

The existing **`alert_outbox.fire_event_id`** is the delivery identity for both legacy fires and the new recognized notice-bundle subtype. For the new subtype, let `bundle_id` be the existing outbox row UUID allocated in its creation transaction. Define:

`fire_event_id = "notice_bundle:v1:" + sha256(canonical_json([user_id, "email", bundle_id]))`

This key is fixed when that outbox row is created. A competing collector reconciles the winner through the existing user/channel/window or per-notice assignment constraint rather than keeping its losing newly allocated ID. Adding members before sealing, removing ineligible content, changing language or rerendering does not change the bundle's delivery key. Attempts bind their actual content hash separately.

The drain passes that **exact outbox `fire_event_id`** to the existing `app.mailer.alert_idem_key(fire_event_id, attempt=n)` helper. At `n=0`, this is the current `alert_fire:<fire_event_id>` form. No second uniqueness ledger or alternative mail key is created. Existing one-shot fire IDs and their email keys remain byte-identical. The versioned bundle namespace cannot collide with them.

An automatic later attempt number is permitted only after the earlier attempt is proved definitely not accepted under v0.3 section 6.3. Unknown external effect preserves the exact previous key/result for reconciliation; it does not advance `n` to escape a duplicate claim. A requested resend after uncertainty is a separate, explicitly recorded risk decision under the existing mail owner, never silent timer-based retry.

`alert_notices.email_outbox_id` resolves this delivery identity when email is scheduled. No redundant `fire_event_id` column is added to a notice: one digest may contain many notices, and a notice may exist entirely on site without any email. The original source event reference remains in its evidence/semantic references, not relabeled as the bundle UUID.

For continuous `source_subscription`, creating the notice and assigning it to an outbox row is the notification-admission transaction; it does not disarm the subscription. This is the explicit F08 subtype amendment already selected in v0.3, not an assertion that a continuous source subscription went through the legacy one-shot `Supa.fire` path. Legacy one-shot disarm/re-arm behavior is unchanged.

The current helper name/form is evidenced in Macro `app/mailer.py` at `4c38ee8ac3de801d44d8a36111740fc514ac7cfe`; this amendment specifies the new caller mapping. It does not claim that caller is implemented.

## 3. Correction identity and consumer-independent changes: amend sections 3.3 and 7

### 3.1 Native source correction

An owner-issued correction or withdrawal uses that owner's stable correction event/revision identity through its approved adapter. A correction need not pretend that a second market occurrence happened. Its original event/effective time, correction availability time and our observation time remain separately stated.

### 3.2 Correction of our interpretation with unchanged source facts

A material error in a previously published explanation is not merely a cosmetic rewrite. The existing interpretation/grounding/publication owner must durably adopt a correction that identifies the earlier interpretation revision, affected claims, corrected meaning, source evidence and validation/adjudication basis. A model's new preference for wording or a higher confidence number is not this correction-admission event.

The proposed shared comparison reference is:

`semantic_change_ref = sha256(canonical_json(["interpretation_correction.v1", source_namespace, original_interpretation_ref, correction_ref]))`

Here `correction_ref` is the stable adopted correction identity from that existing owner. It is never a newly chosen user ID, private notice ID, processing timestamp or model text hash. Where the owner cannot yet publish and resolve such a correction, that source family is not admitted to automatic corrective notifications until the owner extension is implemented and proven; show the explicit limitation rather than manufacture a receipt.

The personal correcting notice has its own ID, retains `(user_id, source_namespace, semantic_change_ref)` uniqueness and uses `corrects_notice_id` to link the recipient's affected earlier notice. Source revision relationships also allow the reader to locate other affected notices. Repeat processing of the same adopted correction is a no-op. A later genuinely distinct correction has its own owner revision. Current access and user delivery policy still apply.

Its language is “We corrected our explanation,” not “A new market event occurred.” The source and original message remain recoverable within current rights. This is a factual explanation repair, not new signal, ranking or trading authority. The original financial example's refund contribution has **recurrence unestablished**; no new return, adjusted metric or nonrecurrence claim is introduced.

### 3.3 Consumer baseline cannot change the event key

The inferred transition in v0.3 section 3.3 compares the source owner's canonical prior accepted revision for the same plan/field family with its canonical successor. Those predecessor/successor references are fixed by the source adapter, not selected independently by each user's last visit or monitor baseline. The adapter's relevant field set and method version are fixed for that family.

Monitors with different baselines filter the same canonical changes. They do not invent different semantic identities for the same transition. A catch-up briefing may summarize several canonical change references; it does not re-key those events using its personal baseline. A new monitor cannot reset source history. If intermediate revisions are missing, present a qualified net-change/current-baseline view and missing coverage; do not fabricate individually identified intermediate fires or silently promote a catch-up summary to a newly actionable event.

## 4. Deterministic preference precedence: amend sections 5.2 and 5.4

Compute delivery only from contemporaneously eligible matching monitors/implicit policies and the same user-preference snapshot. Store the resolution and reason in the notice's bounded decision receipt. The evaluator's order of iteration or arrival order is never the deciding factor.

For each supported channel, apply this order:

1. **Global refusal wins.** Account/channel opt-out, address suppression, required entitlement/source-use refusal and an explicitly disallowed category prevent sending through every monitor. Unknown required eligibility is deferred/unevaluable, not treated as permission.
2. **An applicable positive request is necessary.** A monitor requesting on-site only does not itself request email. An eligible second monitor may independently request it; “none” on one monitor is not a global veto. The user-facing explanation identifies the requesting monitor.
3. **Account-level delivery cap wins.** A chosen digest-only mode converts eligible immediate requests to digest. This is a proposed typed extension of the existing account-preference owner, not a field asserted to exist today.
4. **Among remaining eligible affirmative requests, the most immediate permitted mode wins:** immediate, then digest. No affirmative request means on-site only. Two matching monitors still yield one notice and one email assignment, with both contemporaneous reasons retained.
5. **Quiet hours and interruption limits determine the actual permitted send time.** “Immediate” does not bypass them. Existing quiet-hour deferral remains controlling unless a separately authorized policy explicitly changes it.

A user creating a monitor sees its effective outcome: for example, “Immediate email outside quiet hours,” or “Included in your daily summary because your account is digest-only.” Changing account delivery preferences does not re-arm the source condition. Before actual sending, recheck current permissions and preferences; the immutable original decision is retained separately from the new send-time decision.

This is a conflict-resolution rule inside the existing alert policy, not a new engagement ranker. A model cannot make a slower request immediate or override the user's limits. A more time-sensitive source is not itself notification consent.

## 5. Withheld or uncertain digest members: amend sections 6.1–6.2

**Do not clear `email_outbox_id` as a generic response to withholding.** That could lose assignment history or make a possibly delivered notice independently eligible again.

For v1, select these behaviors:

- A **temporary unknown required eligibility** before any effect defers the affected unattempted bundle, preserving member assignment and an explicit reason. It is not silently converted into terminal suppression. Unrelated subsequent bundles, including a separate immediate alert, can proceed when independently eligible. The user sees that this summary is delayed and why. More elaborate partial-bundle splitting is not required for v1.
- A **known policy/source-use refusal** can withhold that member before sealing while other eligible members are sent. Keep its notice-to-bundle assignment and the member's explicit `withheld` disposition. It was not delivered. If all members are withheld, the outbox can be suppressed with the reasons preserved.
- **Restored consent or entitlement does not auto-send old withheld history.** The current permitted on-site evidence may become readable again; future eligible changes proceed normally. Any intentional replay/resend of the earlier notice requires its own recorded user/owner decision and the existing mail owner's replay-risk rules.
- After **attempting/accepted/unknown external effect**, the attempted envelope and assignment are immutable. Reconcile first; correction or another material update is separate. A rights change never proves that a prior attempt had no effect.

The simpler deferred-bundle policy is an explicit trade-off: one temporarily unverifiable digest member can delay that digest. It cannot hide monitoring degradation or delay separate eligible immediate notifications. The design must show this state rather than claiming a digest was sent. A future partial-bundle split needs an explicit owner contract and linked assignment history before changing this rule; do not improvise it by clearing a foreign key.

## 6. Transaction and mutation boundary clarification

The user transaction operates on a previously validated immutable source publication/reference. It does not pretend to atomically commit an external source publication and the user database. Within the existing user database, notice creation, outbox assignment when requested and guarded advancement of the expected monitor definition/progress version commit together or not at all. Source validation is repeated if the referenced generation or relevant authorization changes before commit.

The new source-subscription envelope is not activated under a client-writable evaluation state. The existing condition API/evaluator owners must supply a guarded mutation contract: user writes can change only the validated definition/allowed action, while evaluator progress and system notice/assignment fields are service-controlled. Existing row-owner RLS alone does not enforce per-field immutability. The implementation must use the existing approved server/RPC and database privilege/guard mechanisms and prove that direct authenticated writes cannot forge progress or system-generated notices. No new auth service or permission bypass is introduced.

## 7. Additional acceptance cases and design consequences

Add these expected behaviors to v0.3's 18 cases; they are **specified cases, not tests run**:

| Case | Expected behavior |
|---|---|
| A19 — continuous notice bundled twice on retry | Same winning outbox row, same `fire_event_id`, same helper-derived attempt key; no subscription disarm or parallel mail key. |
| A20 — interpretation correction, same market source bytes | Owner-adopted correction produces one distinct, linked corrective notice; cosmetic rewrite alone produces none. |
| A21 — immediate and digest monitors plus global quiet/digest policy | Global refusal/cap/quiet policy wins; otherwise most immediate affirmative request wins once; reason visible. |
| A22 — consent restored after a known withheld digest member | History says withheld; no automatic retroactive resend and no cleared assignment to manufacture eligibility. |
| A23 — two user baselines observe one canonical transition | Same source semantic key; personal eligibility differs, not source event identity. |
| A24 — one digest member's required eligibility temporarily unavailable | Digest visibly deferred, assignment retained; a separately eligible immediate alert still proceeds. |
| A25 — authenticated user tries to forge evaluator progress | Rejected by the owned mutation/DB contract; source event is not consumed and system notice fields remain unforgeable by the client. |

The Figma brief should translate these into ordinary language and concrete states, not show hashes or transaction mechanics in the main interface. Relevant visible examples are “Also matched another monitor,” “Included in your summary,” “Summary delayed,” “Not emailed,” and “We corrected our explanation.”

## 8. Review scope and next gate

Eight material Macro source files, including F08, Prophet producer/reader/card helper, private source router, drain and mailer, were compared between v0.3's read pin `321da62b3b0163b6ab5a287fb9847a13ed7f3ed2` and current read pin `4c38ee8ac3de801d44d8a36111740fc514ac7cfe`: their blobs were unchanged. Terminal remained at `3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c`. This is bounded source compatibility, not repository integration or production proof.

The independent review is concluded and consumed; no reviewer is waiting for an inferred reply. Sol requests a fresh one-shot assessment of the original v0.3 plus this exact amendment before recording design-entry acceptance. Neither the reviewer nor this amendment authorizes merge, schema application, source-worker transfer, customer send or production release. Existing PR #7022 and both Figma drafts remain preserved.
