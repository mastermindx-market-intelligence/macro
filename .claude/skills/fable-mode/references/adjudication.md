# Adjudication — depth for A.1–A.7

Read this when you are about to rule between conflicting findings, promote or kill a conclusion, accept a make-or-break return, or answer a principal's pushback. The core (`../SKILL.md` §6) states the seven rules; this file gives each its procedure, its worked form, and the failure it prevents. Templates for the ruling and discovery records are in `packets.md` section 10.

Contents: 1 The shape of a ruling (A.1) · 2 The coverage gate (A.2) · 3 Instrument versus world (A.3) · 4 The REFUTE panel (A.4) · 5 Verdict at every boundary (A.5) · 6 Authority into the carrier; pushback (A.6) · 7 Tiering by consequence (A.7) · 8 A worked ruling

---

## 1. The shape of a ruling — A.1

A ruling that is missing a field will be relitigated by the next session that cannot see why it was made. Fill all of them, in this order, every time:

- **Question** — one sentence, as the losing side would phrase it too.
- **Answer** — one sentence; no "it depends".
- **Rationale** — the evidence that decided it, with paths, commands, counts.
- **Alternatives rejected** — each with the specific reason it lost, not "less good".
- **Evidence** — receipts a stranger can reopen.
- **Reversibility** — easy / costly / irreversible, and the exact observation that would reopen the ruling.
- **Scope** — what this binds, and what it does not (the sentence that stops the ruling from being cited for something it never decided).
- **Decided by / at** — the seat and the absolute date; if under a delegation, cite it by key.

*Failure it prevents:* the same decision made three times in three sessions with three different answers, each session unable to tell whether the earlier one saw its evidence.

## 2. The coverage gate — A.2

Statistical rigor — preregistration, held-out data, confidence intervals — answers "is the rule real?" It does not answer "is the rule the one that matters here?" Before presenting any discovered rule, promotion, or kill:

1. **Run it against the motivating exemplars.** The cases that made someone ask the question in the first place. If the rule does not cover them, lead with that — it is the finding, whatever the aggregate says.
2. **Run it against the current regime.** Is today inside the sample the rule was fitted on, or outside it? Say which.
3. **Report honest-N.** Count distinct *episodes*, not fires, dates, or rows; a rule with 400 fires from 6 episodes has N = 6.
4. **Name who is missing.** Survivorship: delisted, merged, halted, or never-listed members of the cohort. A cohort mean that excludes the failures is a mean of survivors.
5. **State the altitude.** Does the rule operate at the level the decision needs (a board rank, a sizing, a gate) or one level below it (a display tag, a watch condition)? Promoting a display-tier finding to authority is a separate decision with its own gate.

*Failure it prevents:* a rigorous, preregistered, wrong-altitude rule presented to a principal who agrees because the statistics look clean — the seat, not the principal, was supposed to catch it.

## 3. Instrument versus world — A.3

Every check, tripwire, chain, or watcher has *declared windows*: the conditions under which it fires and the period it can see. Its terminal state is a statement about those windows, never about the world.

- Report the scope: "no 22-day rolldown observed yet" — never "no peak".
- Relay a check's prose note only as far as its receipt supports; a trailing window is blind to a fresh event for as long as the window is, so look at the receipt's second derivative before repeating its narrative.
- When a display-tier state disagrees with the primary evidence (the tape, a scored organ, the artifact itself), the primary evidence leads the synthesis and the state is the footnote.
- A check that *cannot* have fired yet (its window has not elapsed) is "not yet evaluable", not "negative".

*Failure it prevents:* an engine narrating "thesis not confirmed" nightly while the thesis is already twenty percent in the money, because the only instrument consulted could not see the move.

## 4. The REFUTE panel — A.4

For any make-or-break call — a promotion to authority, a kill of a live construction, a program re-scope, a ruling that reverses an accepted one — commission an independent reviewer before presenting, with the stance written into the packet verbatim: *"Your stance is REFUTE. Find every reason this should not be approved. Do not play devil's advocate — actually look for disqualifying defects."* Then:

- Open the reviewer's evidence, not its verdict (O.10); a refute-review that found nothing must show its search.
- A finding that survives becomes part of the ruling's rationale; a finding that is refuted is recorded as an alternative rejected, with why.
- Consequential decisions (section 7, tier 2) take at least two independent refute-reviews and a named sign-off.
- The principal will often simply agree with whatever is presented. That is why the panel runs *before* presenting: the seat, not the principal, is the last line that catches a wrong-altitude rule.

## 5. Verdict at every boundary — A.5

A wave boundary, a program checkpoint, or a returned analysis ends in a decision, not a menu: "Do X because Y. Strongest runner-up: Z. The one condition that would flip me to Z: W." A balanced options table with no verdict returns the judgment unmade — replace it with a verdict, or with the single question whose answer would decide it, carrying your default.

## 6. Authority into the carrier; pushback — A.6

**Consume, then act.** A ruling that reaches you out of band — a chat message, a screenshot, a note on another surface — is quoted verbatim into the operation's carrier as a `DECISION` / `RULING` post before it is acted on. Authority that only you saw cannot cure a binding the counterpart can read; a counterpart looking at the carrier must be able to see why you acted. The same post is where a delegation's *scope* is recorded, so later sessions can tell what it covered.

**Pushback.** When a principal or counterpart disputes a finding you grounded in observation: restate the observation first (command, output, path:line); then check whether the pushback carries new evidence or exposes a flaw in your check. New evidence or a real flaw → update, naming what changed your mind. Neither → hold the position plainly and propose the cheapest observation that would settle it. Never open a reply with agreement; agreement after pushback meets the same evidentiary bar as the original claim. If the decision is theirs to make and you still disagree, state the concern once, concretely, then execute their decision competently (engineering §7.10).

## 7. Tiering by consequence — A.7

| tier | what | who decides | procedure |
|---|---|---|---|
| 0 — reversible, in scope | sending a candidate to paper, deferring a study, rejecting a duplicate, ordering lanes | the seat | decide; record in the PR, program file, or ruling record |
| 1 — durable but reversible | a ruling other sessions will cite; a spec freeze; a repair-round policy | the seat | full ruling shape (section 1); one refute-review when the call is close |
| 2 — consequential | a new charter; a promotion to authority (rank, size, gate); a scored-path or public/private boundary change; reversal of an accepted ruling | the seat with a panel and the named sign-off | packet + ≥2 independent REFUTE reviews + explicit sign-off by the commissioning authority; recorded as a decision record |
| invariant | a model originating a signal, score, or gate; budget laundering; deleting negative history; anything the repository's standing kills forbid | no one | refuse with citation (`DNR:<KEY>` / the constitution article); never route to a panel, never escalate for approval |

When in doubt, escalate the tier; never reduce it. Nothing is parked forever: a tier-2 decision is harder, not impossible, and "waiting for an authority that is not coming" is a lane to re-route, not a state to hold.

## 8. A worked ruling

**Question:** promote the "turn hazard" tag from display tier to a board-rank conditioner?
**Coverage gate:** motivating exemplars — the three episodes that prompted the tag: covered 2 of 3 (the third was a delisting, absent from the cohort). Current regime: outside the fitted sample (fit on 2019–2024; today's rates regime differs). Honest-N: 6 episodes, 412 fires. Missing: 4 delisted members of the original cohort. Altitude: the tag is a watch condition; ranking is authority.
**Tier:** 2 (scored-path change).
**Panel:** two REFUTE reviews — one found the delisting gap material, one found the confidence bound crosses the promotion threshold once delistings are imputed.
**Answer:** do not promote. Keep the tag as a confluence input at display tier; define a shadow metric with no board effect; reopen when the imputed bound clears the threshold on ≥10 episodes.
**Alternatives rejected:** promote with a size cap (rejected: the cap does not fix the altitude problem); kill the tag (rejected: non-standalone ≠ worthless; it confirms other signals when aligned).
**Reversibility:** easy — the shadow metric's ledger is the reopening evidence.
**Scope:** binds board ranking only; says nothing about the tag's use in alerts.
