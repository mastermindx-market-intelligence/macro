# Opus adversarial RE-REVIEW (round 2) — T7 spec on PR #7904 @ 9f8cb6486c15

MODE: READ_ONLY. Artifact: origin/claude/cdv1-t7-design-spec:research/consumer_defensive/cdv1_program/design/T7_DOSSIER_DESIGN_SPEC_2026-09-24.md (453 lines; cited as `spec:N`).
Rulings: SEAT_RULING_T7_SPEC_R1 (R1-R10), SEAT_RULING_T7_SPEC_R1A (A1-A4). Plan pin 88970a1a (cited `plan:N`). Round-1 review: scratchpad/opus_t7_spec_review.md.

## 1. Round-1 blockers

- RB1 (F4.1 fictional Theme Tracker `us_sector_staples` row) — RESOLVED. No Theme Tracker / `us_sector_staples` / `data-theme-id` string remains; spec:15 "The slot has no dossier-specific page..."; spec:445 records the mount as resolved by R1A. No replacement mount is invented.
- RB2 (F4.2 drawer click-collapse) — RESOLVED BY REMOVAL. The state_of_themes host is gone; there is no host handler left to break. Residual requirement transferred to host is only implicit (spec:23-24 focus/lifecycle); see F9 (NOTE) — the host-interaction clause does not say the host's disclosure must ignore clicks originating inside the dossier content, which is exactly the RB2 failure class on any collapsible host.
- RB3 (F2 no light art direction) — RESOLVED AS A HOST REQUIREMENT (per R1A A1). spec:137-155 states DARK (luminance depth, restrained glow, dark scrim, layered panel luminance, glow/light response on controls) and LIGHT (cool canvas, white/near-white material, hairline structure, shadow not glow, NO dark scrim, crisp hairline + tight shadow on raised controls) with per-theme degraded-state clauses (spec:141, 147) and spec:155 "token substitution alone is not acceptance evidence"; evidence matrix spec:405 + B20 spec:430. Residual gaps are MINOR (F7, F8 below), not blocker.

## 2. Ruling discharge (R1-R10, R1A A1-A4)

- R1 (mount) — SUPERSEDED by A1; discharged by removal: spec:15, spec:445. The surviving R1 lifecycle clause (collapsed by default, mount on first expand, destroy on collapse/logout) is retained as a host requirement at spec:24 (see F1 for the contradiction it creates with the glance tier).
- R2 (assets) — SUPERSEDED by A1; discharged: no asset path anywhere; spec:42-44 lists asset delivery/include/init as DEFERRED foundation items.
- R3 (stance lookup) — DISCHARGED in form: pinned ordered rule-ID table spec:252-262 (first match + default row), chip lookup on `selection.currentness` spec:231-236, "no response field is added" spec:447, "Matching is rendering only" spec:252. Substance problem: F5 (Law 1).
- R4 (two art directions) — DISCHARGED AS HOST REQUIREMENT under A1: scrim vs no-scrim spec:139 vs spec:145; glow/light-response vs hairline+tight-shadow spec:139 vs spec:145; canvas step (layered luminance vs cool canvas + white material) spec:139 vs spec:145; per-theme degraded states spec:141, spec:147; token-only swap refused spec:155. Gaps: F7, F8 (MINOR).
- R5 (neutral chips) — DISCHARGED: spec:151, spec:56, B13 spec:423.
- R6 (wrapper + evidence) — DISCHARGED in shape: wrapper five fields + 14-key check on `interpretation` spec:312-323 (matches plan:144-145, plan:310); evidence route + three pins spec:385-388 (matches plan:178, plan:424-426); click fetches once per open, aborted on close/auth/destroy spec:382-388; field map spec:327-366. Substance problem: F3 (field paths not owned by any upstream contract).
- R7 (host wiring) — SUPERSEDED by A1; retained correctly as host requirements: getSession/Bearer/no-store spec:21, spec:35 (real: templates/earnings_wire/earnings-wire.js:62,102-103 on main); `mdx-auth` + ignore PREFS_SAVED spec:22, spec:36 (real: templates/theme.js:1883); `nativeIssuerId` dropped, ticker is route symbol only spec:34. Residual: F2 (issuer double source).
- R8 (density) — DISCHARGED as host constraint: <=44 px collapsed spec:19, spec:158; 390 px expanded + inner scroll spec:25, spec:158; no header/hero spec:159. Feasibility: F1/F10.
- R9 (copy + a11y) — DISCHARGED: neutral reported/organic wording spec:256, spec:270; "cannot be read as a beat or a miss" + 一致预期 spec:261, spec:275, spec:281; 报告每股收益与核心每股收益 spec:60, spec:290; 已是最新 spec:233; per-row bilingual accessible names spec:113, spec:119; real sign-in control spec:125-131; bilingual accessible labels spec:121.
- R10 (fallback tokens) — SUPERSEDED in ownership by A1; discharged: spec:135, spec:451.
- A1 (no shell of our own) — DISCHARGED: spec:9, spec:15, spec:135, §1.1 host-slot requirements spec:17-25 cover panel/selector/read callback/auth subscription/focus-return/lifecycle exactly as A1 enumerates. Residual MINOR F11: the addressee is never named (A1 names carrier #7870 + `contracts/sector_intelligence/`; the spec says only "foundation owner").
- A2 (binding content) — DISCHARGED: IA §2 spec:48-76; copy tables §5; stance table spec:252; field map §6.2; pinning spec:385-388; privacy spec:392-397; per-row names spec:119; dialog semantics spec:121; evidence matrix as host tests spec:401.
- A3 (naming) — DISCHARGED: adapter signature spec:30 (= plan:463); `data-economic-*` list spec:82-97 incl. plan:467's six selectors.
- A4 (release effect) — DISCHARGED: STATUS line spec:3 verbatim; spec:46; spec:452.

## 3. Fabrication sweep (data / page / row / endpoint / field / asset)

Clean: no Theme Tracker row, no sector page, no asset path, no invented issuer ID. Both API routes are absent on main (`git show origin/main:app/earnings.py` has only `/api/earnings/v1/records/{slug}` at :108 and one more route at :142) but are PLANNED Task 6 routes (plan:176, plan:178, plan:438), and the spec labels them as the Task 6 wrapper (spec:310) — not fabrication. `sb.auth.getSession`, `mdx-auth`, `langchange` (theme.js:646), `.l-en/.l-zh` (theme.css, 9/10 hits) all exist.

F3 [MAJOR] spec:327-365 — claim: "Every source-derived placeholder maps exactly as follows" to paths `observations[].label.{en,zh}`, `.period`, `.basis`, `.value_and_unit.{en,zh}`, `clocks.fiscal_period.{en,zh}`, `clocks.source_accepted.{en,zh}`, `next_evidence.company_link/.gmi_link`, evidence-response `header.{en,zh}`, `period.{en,zh}`, `source_text.{en,zh}`, `precision_note.{en,zh}`. — evidence: the plan defines none of these member paths. plan:148 says only "Each observation is a native handle (workspace_generation_id, event_id, fact_id) and display metadata"; plan:141 names sections only ("clocks/coverage", "next evidence"); the only observation/evidence member any plan test names is `fact_id` and `source_sha256` (plan:421, plan:427); missing_context members are keyed `subject` (plan:278). No T3/T4/T6 branch exists to bind to. So the map is a unilateral schema for three upstream tasks, stated as fact. Worst row: `source_text.{en,zh}` (spec:363) — the permitted excerpt is English SEC-exhibit text (plan:180, plan:617); a ZH twin can only exist by translating private source text, which the plan never authorizes (and an LLM translation would put machine-originated text inside an "evidence" dialog). — falsifier: a Task 3/4/6 commission or frozen view schema that already commits these exact member names. — fix: retitle §6.2 as "REQUIRED view projection — binding on Task 3/4/6" and have the seat carry it into those commissions (or mark PROPOSED pending the Task 6 freeze); make `source_text` single-language original + a fixed ZH note ("原文为英文来源摘录") instead of `{en,zh}`; map missing-context text via `missing_context[].subject` (plan:278).

F12 [MINOR] spec:106 — `class="foundation-neutral-chip"` and `class="sr-only"` inside the binding DOM example. — evidence: both have 0 definitions in origin/main templates/theme.css; #7870 (`gh pr diff 7870 --name-only`) ships no stylesheet at all. The spec says it "owns no ... selector" (spec:135) yet names two non-existent classes. — fix: write them as placeholders (`HOST_NEUTRAL_CHIP_CLASS`, `HOST_VISUALLY_HIDDEN_CLASS`) like the other SERVER_* tokens.

F13 [NOTE] spec:438 — `tests/test_earnings_economic_browser.py` does not exist; it is framed "for example", acceptable as a future lane name.

## 4. Two art directions (TP-0) — requirement form PASSES; no runtime stylesheet; two MINOR gaps

The spec owns no CSS (spec:135) — so no opaque runtime stylesheet in adapter JS is possible by its own terms; the adapter contract (§6.5) only renders text. Dark and light are stated as distinct requirements on the host with named differing mechanisms (see R4 row above), degraded states per theme, B20 separate adjudication, and a 2 themes x 2 langs x 3 widths matrix (spec:405, superset of the required 1440/390). This is the correct R1A form: dual-theme *evidence* cannot exist until the host slot exists (spec:46), so PASS of the eventual UI is correctly deferred to B20/B21.

F7 [MINOR] spec:137-155 — TP-0 (CLAUDE.md house law) requires a packet to name "which mechanisms intentionally differ" and "the reference/baseline". The differences are inferable from prose but not enumerated, and no reference is named. — fix: add a 5-row table (scrim / control hover response / canvas-vs-panel step / dialog depth / degraded-state structure) x dark/light, and cite `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` §12 component table (lines ~594-608: "ring, not glow", "tint step + hairline; shadow only if interactive") as the baseline.

F8 [MINOR] spec:141 vs spec:147 — dark degraded clause is generic ("remain legible ... without a second palette"); light gets concrete per-state requirements. — fix: give dark the same per-state specificity (e.g. loading skeleton luminance step on `--panel`, unentitled state has no glow/bloom, error uses state ink not a new hue).

F14 [MINOR] spec:23 + spec:121 + B02 spec:412 vs spec:145 — "scrim click closes" is mandatory, but light "has no dark scrim; it uses an existing light overlay or transparent separation". If the host picks "transparent separation" with no overlay element, the mandatory close target does not exist. — fix: "light uses a transparent or light overlay element that remains the close target".

## 5. Plain-word law

Clean: title 4 words (doctrine :25 "title <= 4 words"); every stance sentence <= 14 words (longest = missing_consensus, 14); no internal state names on Tier 1 (chips are "Up to date / Newer filing not yet read / Freshness not confirmed / Not available"); generation/manifest/digest only inside the evidence dialog (spec:304); no falsifier/refutation/"validated"/buy/sell (spec:304); absences typed and never "no data/unknown/zero" (spec:68, spec:279-285, B06).

F5 [MAJOR] spec:252-262 — Law 1 (docs/DESIGN_DOCTRINE.md:40-46 "Stance or it doesn't ship"; stance vocabulary Act/Get ready/Watch — don't chase/...) — six of seven stance rows are descriptive facts with no stance; only the `default` row carries "Watch the evidence — do not chase it." And the default is practically unreachable: CDV-1 has no consensus source, the plan's own Task 3 test asserts consensus is always in `missing_context` (plan:278), so `missing_consensus` (or an earlier row) fires on every real render. Net: the glance tier will essentially never answer "so what do I do". — falsifier: a real/synthetic P&G interpretation with an empty findings list. — fix (copy only, no new field, R3-compatible): make every row "<finding clause> — watch the evidence, don't chase." / "…——看证据，勿追。" (still <= 14-ish words; trim clauses where needed), or render the fixed default stance always and demote the matched sentence to the chip subtitle.

F6 [MINOR] spec:256-261 vs spec:270-275 — the glance stance is byte-identical to the first finding row in the read tier, so the expanded panel prints the same sentence twice (doctrine Law 4, :82-87 "no duplicate ..."). Resolved automatically if F5's fix is taken.

F15 [MINOR] spec:190 — "digest | 摘要": 摘要 reads as "summary/abstract", not a hash; use 摘要值/校验值 (SHA-256). spec:234 "Newer filing not yet read" is ambiguous (reads as the *user* not having read it) — "Newer filing not yet processed" / keep ZH 新文件尚未读取 or 新文件尚未处理.

F16 [MINOR] spec:170-171 — the compact toggle hardcodes "P&G"/"宝洁" while spec:20 makes the issuer whatever the host's native selector holds. Any non-PG selection gets a toggle naming the wrong company. CDV-1 admits only PG (plan:214), so latent, but the copy should take the host's issuer display name or drop the name ("Open demand and earnings evidence").

## 6. Data / behaviour contract

Clean: closed 14-key check on `interpretation` + six all-false authority booleans (spec:316-323 = plan:144-150); epoch + single AbortController + no poll/retry (spec:378); evidence URL built only from displayed response (spec:388, B14); text-only DOM writes, no browser arithmetic, no storage/telemetry (spec:392-395); links only from valid owner bindings (spec:397, plan:22). Consistent with `app/earnings.py` on main in the only way it can be: both routes are planned adjacent routes in the same router (plan:176), not yet present.

F1 [MAJOR] spec:52 vs spec:24 + spec:38 — the collapsed glance row "shows the plain-language state chip, one stance sentence", but the adapter mounts only "on first disclosure expansion", requests the view only on mount, and is destroyed on collapse. Chip (from `selection.currentness`) and stance (from `findings[].rule_id`) therefore cannot exist in the collapsed row before first expansion, and are torn down on every collapse. A builder must pick: pre-fetch on page load (breaks the R1/R8-derived lifecycle and fetches private data for every visitor) or show an empty glance row (breaks §2.1). — falsifier: a lifecycle clause permitting a glance-only fetch before expansion. — fix: either (a) collapsed row = title + toggle only, chip/stance appear at the top of the expanded area; or (b) an explicit two-phase lifecycle: lightweight mount on host render that fetches the view once for the glance row, and the read tier/evidence on expansion — and say which. Also F10.

F2 [MAJOR] spec:34 vs spec:37 vs spec:331-332 vs spec:371 — two sources of the ticker: the adapter receives `issuer: {ticker}` (spec:34, used at spec:371 `issuer.ticker`), yet "The adapter selects the source symbol from the host's `data-economic-issuer` attribute" (spec:37) and the field map binds the URL `{ticker}` to that attribute (spec:332). The element that carries `data-economic-issuer` (root? host?) is never stated (spec:83). If the two disagree the contract has no winner. — fix: one source. Recommended: `issuer.ticker` is authoritative; the adapter writes it to `root[data-economic-issuer]` for tests; a mismatch = no-op mount.

F4 [MAJOR] spec:378 + spec:24/36 + spec:131 — auth change is under-specified in both directions. (i) After a user signs in via the unentitled state's sign-in control (identity null -> user), spec:378 says "render the appropriate fixed state" and "Never retry ... refresh, or reload automatically" — so the signed-in, entitled user keeps seeing an empty/unentitled panel with no defined way to load, which breaks the only upsell journey the spec defines. (ii) spec:378 removes `data-economic-mounted` on auth change while the instance (and its auth listener) stays alive; the mount guard (spec:33) keys on that attribute, so a host re-mount now double-mounts. — fix: pin "identity change -> clear -> if the new identity is signed in, perform exactly one fresh view request under the new epoch (this is the load for the new identity, not a retry)"; and keep `data-economic-mounted="1"` until `destroy()`. Also extend "clear private DOM text" to the private-bearing attributes (`data-economic-fact-id`, `-period`, `-basis`, `-rule`) and rows (spec:395 puts private values in those attributes).

F9 [MAJOR] spec:82 + spec:333 — `data-economic-state` is a binding test selector (plan:467) but its value set is never enumerated, and there is no HTTP-status -> state table. The plan's route tests pin 401 anonymous, 403 unentitled, 404 valid-but-absent, 503 corrupt closure, unsupported schema (plan:413); the spec has copy for unavailable/unentitled/unsupported/error (spec:242-248) but no mapping (e.g. is 401 and 403 both `unentitled` with the sign-in control? is 404 `unavailable`? is a network abort `error`?). Test author and builder must invent it. — fix: add a table `{loading, ready, unavailable, unentitled, unsupported, error}` x triggering condition (401/403/404/503/schema/validation/network).

F17 [MINOR] spec:352 + spec:298-299 — currentness footer maps to "`selection.currentness` and matching clock value" and templates use `{source clock}`, which has no payload path. — fix: name the clock member.

F18 [MINOR] spec:323 — "Unknown optional fields elsewhere in the wrapper follow the wrapper contract": no wrapper contract exists beyond five names (plan:310 adds "permitted native evidence handles"). State "ignore unknown wrapper fields; never render them".

F11 [MINOR] spec:15, spec:40-46 — A1 addresses the requirements to a named foundation (carrier #7870 lineage; `contracts/sector_intelligence/`). The spec never names the addressee, nor maps its own clock words ("Source accepted", currentness) to the foundation clock classes that #7870 mints (`contracts/evidence_foundation/vocabulary.v1.json` clock_classes: source_published, knowable, observed, system_recorded, ...; owner_stores already lists `earnings.workspace_generation`). Without that mapping the dossier ships a parallel clock vocabulary the foundation must later reconcile. — fix: one line naming the addressee + an integration requirement "clock labels map to foundation clock classes at integration; the Earnings owner's clock stays the source". Evidence rights: the dialog relies on the Earnings route's read-time rights (plan:180); add a NOTE that the host must not re-expose an excerpt the foundation's rights layer (`engine/theme_graph/rights.py`) would hide.

## 7. Internal contradictions

F10 [MINOR] spec:19/158 vs spec:52 + spec:170 — a <=44 px collapsed row must hold the chip, a stance sentence of up to 14 words, the issuer and a 6-word toggle label; at 390 px width that is 2-3 lines, breaking both the 44 px budget and doctrine "row <= 1 line" (DESIGN_DOCTRINE.md:25). Resolved by F1 option (a).

F19 [MINOR] spec:345 vs spec:82-97 — the field map binds `[data-economic-findings]` items, but §3's binding attribute list has no `data-economic-findings` container (only `data-economic-rule` rows). Add it to §3.

F20 [MINOR] spec:24 "destroys on collapse when the host uses a collapsible slot" (optional) vs spec:19/158 (collapsed control mandatory). Drop the conditional.

F21 [NOTE] spec:74-76 + spec:25 — where the aria-modal dialog renders (inside the 390 px inner-scroll area or over the host page) is unstated; at 390 px mobile an in-panel dialog would be cramped. Host decision, but name it as a host requirement.

F22 [NOTE] spec:166 heading "Fixed shell and actions" — leftover word "shell" after A1; content is copy, not a shell. Rename "Fixed labels and actions". spec:72 typo "manufacture time".

F9-RB2 residue [NOTE] spec:17-25 — add a host requirement that the host's disclosure/drawer toggle ignores clicks originating inside the expanded dossier (buttons, dialog, text) — the round-1 F4.2 failure class generalised to any collapsible host.

## VERDICT: ACCEPT-WITH-FIXES — 0 BLOCKER / 6 MAJOR / 13 MINOR / 4 NOTE

All three round-1 blockers are resolved (RB1/RB2 by removal under R1A; RB3 as a dual art-direction host requirement). Every ruling R1-R10 and A1-A4 is discharged in form. No shell of our own, no asset path, no CSS, no invented mount, no fabricated Theme Tracker row. The six MAJORs are text-level contract fixes, not a redesign:

Minimal fixes (spec text only):
1. F1: pick the glance lifecycle — collapsed row = title + toggle only (chip/stance at the top of the expanded area), or an explicit pre-expansion glance fetch. (This also fixes F10.)
2. F2: one issuer source (`issuer.ticker` authoritative; the attribute is a mirror; a mismatch = no-op).
3. F3: retitle §6.2 as a REQUIRED projection binding on Task 3/4/6 (or PROPOSED pending the Task 6 freeze); `source_text` single-language original + fixed ZH note; missing-context via `missing_context[].subject`.
4. F4: sign-in identity change performs one fresh view load under the new epoch; keep `data-economic-mounted` until `destroy()`; clear private-bearing attributes on logout.
5. F5: every stance row carries the stance ("… — watch the evidence, don't chase."), or always print the default stance and demote the finding.
6. F9: enumerate `data-economic-state` values plus an HTTP status/condition → state table (401/403/404/503/schema/network).
The MINORs can ride the same repair commit. Re-review is needed only for items 1, 3 and 4 (behaviour and contract); the others are copy.

## Return packet
STATUS: PARTIAL
RESULT: ACCEPT-WITH-FIXES; BLOCKER 0 / MAJOR 6 / MINOR 13 (NOTE 4)
EVIDENCE: this file; commands: git fetch origin claude/cdv1-t7-design-spec (head 9f8cb6486c15); git show <ref>:<spec|R1|R1A>; git show 88970a1a:<plan>; git show origin/main:app/earnings.py|grep routes; git show origin/main:templates/{theme.css,theme.js,earnings_wire/earnings-wire.js}|grep; gh pr view/diff 7870 --name-only; git show <7870 ref>:contracts/{theme_graph/evidence.v1.schema.json,evidence_foundation/vocabulary.v1.json}; git show origin/main:docs/DESIGN_DOCTRINE.md, research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md
GAPS: no Task 3/4/6 schema exists yet to verify F3 against; PREFS_SAVED line not re-confirmed (grep head truncated, R7 cites theme.js:3212); sector.html.j2 not re-inspected (R1 superseded); engine/theme_graph/rights.py not read.
DEVIATIONS: none material; one grep batch was backgrounded/timed out (zsh `$M:t` modifier bug) and re-run.
