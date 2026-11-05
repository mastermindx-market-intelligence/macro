# Audit — mastermindx-market-intelligence/mastermind-terminal PR #588

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| PR | [#588](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/588) |
| title | [MO-B F12-17] Team invites: a copyable invite link and a dated line that email delivery is not configured (MO-PAID-081) |
| workplan | MO-B (Mastermind O-B), packet B-F12-17 / MO-PAID-081 |
| mergedAt | 2026-09-19T12:22:49Z |
| merge commit | `dafc016e4e9e34f4a8be3e0a98819b098eedf8df` (merge onto `master`; pre-merge master tip = `11972af358926552e82ee8c7e7843dc831561677` — itself a merge of #666) |
| audit head | detached worktree at `dafc016e…` (sparse-checkout `terminal/{app,components,lib,scripts,docs/pr-crops}`) |
| files | 70 changed (2692 +, 290 −): 8 source files (4 new + 4 modified), 2 CSS files (1 new + 1 modified), 7 test files (3 new + 4 modified), 17 EVIDENCE.yml restamps (1 new packet + 16 hash-only), 26 PNG crops (16 in the new packet + 10 carryover) |
| program surface | Two surfaces: (a) Terminal Settings ▸ Team — new invite form + copyable invite link + dated no-email-delivery honesty line; (b) public `/invite?token=…` accept page (signed-out, ready, busy, joined, failed, unavailable). New API endpoint `terminal/app/api/teams/invitations/route.ts` returns the link once (server stores only the token hash) plus a `delivery` block carrying the EN/ZH honest-no-mail sentences with a date |
| half-B label | "half-B" = MO-B user-facing-readout half. Backend shipped as one-shot answer shape (no provider provisioning, in-scope); this PR is the Settings entry-point half + the public accept page half — no new mail provider, no deleted/edited `/api/teams` contract |

The PR title says "copyable invite link and a dated line that email delivery is not configured" — packet is explicitly scoped to honest link-only. Forbidden moves encoded in the body: no mail-provider provisioning, no `merge` of the r2/r3 commits into the master line (they merge with a merge commit at the seat), and no waiver of the "validated/validated/验证" claim classes. The dated honesty line (`INVITE_EMAIL_DELIVERY_CHECKED_AT = "2026-09-13"`) is the load-bearing artifact: when a provider is ever provisioned, the line and the date retire together in the same change.

## Plain-language findings

Tool: `terminal/scripts/check_plain_language.mjs --json --since 11972af358926552e82ee8c7e7843dc831561677` against merge commit `dafc016`. Forward-only blocking model — every file is re-censused on each run; a finding on a line the diff added is `blocking`, the same finding on a pre-existing line is `legacy`. Overlay `terminal/lib/plainLabels.ts` present (declared vocabulary 83 terms; overlay 36 — unchanged by this PR; the new strings are bilingual LEX pairs or catalogued route messages, not new vocabulary entries).

**Verdict: PASS (0 blocking).**

```json
"counts": { "blocking": 0, "legacyReported": 18, "waived": 0 },
"scannedFiles": 251,
"vocabulary": { "declaredTerms": 83, "overlaySource": "terminal/lib/plainLabels.ts", "overlayPresent": true, "overlayTerms": 36 },
"base": "11972af358926552e82ee8c7e7843dc831561677", "baseResolved": true, "mode": "enforce-added",
"nulls": [
  { "axis": "zh_translation", "path": "terminal/app/invite/page.tsx",
    "value": "not evaluable — no new user-visible strings added" }
]
```

Manual spot-check of new code paths:

- **`terminal/components/settings/SectionTeam.tsx`** (+189 lines, MODIFIED) — every visible string routes through a `t()` call. Grep of added lines for `t("acsTeamInvite…")`:
  - `<Group title={t("acsTeamInviteTitle")}>`
  - `t("acsTeamInviteFor")` (with `{email}` substitution)
  - `t("acsTeamInviteCopied") | t("acsTeamInviteCopy")`
  - `t("acsTeamInviteSend")` (with `{days}` substitution)
  - `t("acsTeamInviteCopyFail")` (clipboard-denied fallback)
  - `t("acsTeamInviteAnother")`
  - `t("acsTeamInviteEmail")`, `t("acsTeamInviteEmailHint")`, `t("acsTeamInviteRole")`
  - `t("acsTeamInviteCreating") | t("acsTeamInviteCreate")` (busy vs idle create-button label)
  - Error path: `routeMessage(body, lang) || TEAM_ROUTE_MESSAGES.write_failed[lang === "zh" ? 1 : 0]` (existing helper, no new string)
  - The `<p className="acs-note">{t("acsTeamInviteEmailHint")}</p>` is the only plain-English leak surface and it routes through the LEX key.
  - The dated no-email sentence uses `noEmailDeliveryLine(lang)` from `terminal/lib/teams.ts` (returns the EN/ZH pair joined by hand, not concatenated raw).
  - All 14 added LEX pairs and the API `INVITE_MESSAGES` entries route through their catalogued `[en, zh]` arrays — no raw English literal in any user-visible position.

- **`terminal/lib/i18n.tsx`** (+28 lines, MODIFIED) — adds 21 LEX keys, each a real `[en, zh]` pair with CJK punctuation (`，。、` `、` `……` `「」` `——`):
  - Settings surface (15 keys): `acsTeamInviteTitle: ["Invite someone", "邀请成员"]`, `acsTeamInviteEmail: ["Their email address", "对方的邮箱地址"]`, `acsTeamInviteEmailHint: ["They will need this address to sign in with.", "对方需要用这个地址登录。"]`, `acsTeamInviteRole: ["Their role", "对方的角色"]`, `acsTeamInviteCreate: ["Create invitation link", "创建邀请链接"]`, `acsTeamInviteCreating: ["Creating the link…", "正在创建链接…"]`, `acsTeamInviteCreated: ["The invitation link is ready.", "邀请链接已生成。"]`, `acsTeamInviteFor: ["Invitation link for {email}", "{email} 的邀请链接"]`, `acsTeamInviteCopy: ["Copy link", "复制链接"]`, `acsTeamInviteCopied: ["Link copied", "链接已复制"]`, `acsTeamInviteCopyFail: ["We could not copy it. Select the link and copy it yourself.", "我们无法自动复制。请选中链接后自行复制。"]`, `acsTeamInviteSend: ["Send this link to them yourself. It works for {days} days and can be used once.", "请自行把这个链接发送给对方。链接 {days} 天内有效，且只能使用一次。"]`, `acsTeamInviteAnother: ["Invite someone else", "邀请其他人"]`, `acsTeamInviteNeedEmail: ["Enter their email address first.", "请先填写对方的邮箱地址。"]`.
  - `/invite` surface (6 keys): `invTitle: ["Team invitation", "团队邀请"]`, `invIntro: ["You have been invited to join a team on Mastermind Terminal.", "有人邀请你加入 Mastermind Terminal 上的一个团队。"]`, `invChecking: ["Checking your invitation…", "正在核对你的邀请…"]`, `invAccept: ["Accept invitation", "接受邀请"]`, `invAccepting: ["Accepting…", "正在接受…"]`, plus `invSignIn`, `invOpenTerminal`, `invSignInReturn`, `invLinkLife` (sampled from grep, all paired).
  - The ZH twin of the dated line uses no Latin space between sentences — the body's "ZH parity: every new string is a lexicon [en, zh] pair; the two Chinese sentences join without a Latin space" rule is honored by `noEmailDeliveryLine(lang)` which returns the line from the catalogued pair, not via concatenation.

- **`terminal/lib/teams.ts`** (+97 lines, MODIFIED) — exports:
  - `INVITE_EMAIL_DELIVERY_CHECKED_AT = "2026-09-13"` (load-bearing artifact; see body)
  - `INVITE_ACCEPT_PATH = "/invite"`
  - `inviteCheckedOn(iso, lang)` — hand-formatted `"2026-09-13" -> "13 September 2026" | "2026年9月13日"` (avoids `toLocaleDateString` to prevent Node↔browser hydration disagreement; falls back to the raw ISO string on unparseable input, never "Invalid Date")
  - `noEmailDeliveryLine(lang, checkedAt?)` — produces the honest-no-mail sentence with the date filled in
  - `inviteDeliveryBlock(checkedAt?)` — returns `{ checkedAt: ISO, enSentences: [..], zhSentences: [..] }` (the API shape that the Settings UI and the API response both consume)
  - `INVITE_MESSAGES` — closed-union dictionary with the 409 `duplicate_invite` no-revoke sentence: EN `"There is already a pending invitation for this email address. Its link cannot be shown or regenerated; wait for it to expire or invite a different address."` / ZH `"该邮箱地址已有一份待处理的邀请。其链接无法再次显示或重新生成；请等待其过期，或邀请另一个地址。"` — exact pin enforced by `terminal/lib/__tests__/teams.test.ts` round-3 test "duplicate_invite EN/ZH states the no-revoke limitation".

- **`terminal/app/invite/InviteAccept.tsx`** (+142 lines, ADDED) — six phases (`checking | signed-out | ready | busy | joined | failed | unavailable`), every user-visible sentence is `t("inv*")` (LEX) or `INVITE_MESSAGES.<key>[idx]` (catalogued pair). The server-side `message/messageZh` pair returned by `POST /api/teams/invitations` is preferred over any local guess — a used, expired, or wrong-address link reads as the reason the server gave, never as a generic failure.

- **`terminal/app/invite/page.tsx`** (+24 lines, ADDED) — server component, only sets metadata `title: "Team invitation — Mastermind Terminal"` and renders `<InviteAccept token={isInviteToken(token) ? token : null} />`. The checker's `nulls` entry for this file — "not evaluable — no new user-visible strings added" — is correct: this file owns no user-visible inline strings (the title is Next.js metadata, not the inline-text class the checker enumerates).

Legacy findings (18 — all reported but NOT blocking because they sit on pre-existing lines the diff did not add; identical to the `511a25a9` head in the prior #669 audit, save that this audit's base is `11972af3` and includes the #587/#584/#660/#659/#642/#664/#666 merges in between):
- 7× `missing_zh` in `alerts/`, `flowdesk/`, `gexdesk/`, `heatmap/` — pre-existing.
- 10× `raw_slug_interpolation` (`verdict`/`status`/`state`/`type`/`kind` fields) in `AlertTimeline`, `AlertsCockpit`, `WatchingList`, `CompanyIntelligencePage`, `ForecastPage` (×2), `TechnicalsPage`, `FlowDeskView`, `ExposureMatrix`, `SectionAccount` — pre-existing.
- 1× `raw_state_enum` `DELAYED_15M` in `terminal/lib/visualIntelligenceCopy.ts:64`, **waived** by author: "transport basis is compared here, never rendered; the returned key selects localized copy." — line 64 sits outside the diff's footprint; waiver predates this PR.

Conclusion: this PR adds **zero** new plain-language debt. The blocking count is the floor (`0`); the 18-row legacy pile is unchanged from `11972af3` to `dafc016`. The `nulls` entry for `terminal/app/invite/page.tsx` is the checker's honest disclosure that the new file's only non-`t()`-routed text is Next.js metadata, which the checker does not enumerate as inline text.

## Theme findings

Laws in force (project standing):
- TP-0 theme art-direction (dark + light, dark × light × EN/ZH × 1440/390 evidence matrix) — applies to Macro site.
- `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` — exempts Terminal-shell packets from the light half. Required: dark × EN/ZH × 1440/390 + explicit PR-body sentence naming this DEC.

**Verdict: PASS — Terminal dark-only matrix complete; one owed recapture (`# recapture: NEEDED`).**

Evidence matrix shipped (`terminal/docs/pr-crops/w9t-f12-17-invite-link-honesty/EVIDENCE.yml`):

```
theme: dark
languages: [en, zh]
viewports: [1440x900, 390x844]
harness: /dev/settings?s=team&lang=<en|zh> (Settings ▸ Team) and
         /invite?token=<64 hex> (public accept page)
network_stubs: POST/GET /api/teams/invitations answered with the shape
               app/api/teams/invitations/route.ts returns; /invite joined
               frames also answer GET <supabase>/auth/v1/user. The harness
               has no database, so the real component is driven by the real
               answer shape.
capture_flag: TERMINAL_E2E_FIXTURE
capture_flag_law: Set TERMINAL_E2E_FIXTURE=1 and next.config.ts sets
                  devIndicators false, hiding the Next.js dev button
                  overlay from crops.
command: node terminal/e2e/tools/capture_w9t_f12_17_invite_link.cjs
files:
  - desktop-en-{team-invite-form,team-invite-link,invite-signin,invite-joined}.png
  - desktop-zh-{team-invite-form,team-invite-link,invite-signin,invite-joined}.png
  - mobile-en-{team-invite-form,team-invite-link,invite-signin,invite-joined}.png
  - mobile-zh-{team-invite-form,team-invite-link,invite-signin,invite-joined}.png
```

16 PNGs × 4 packet-states × {1440, 390} × {en, zh} = full dark × EN/ZH × 1440/390 coverage. The first comment line of `EVIDENCE.yml` explicitly cites the DEC:

> `# Terminal is dark-only: DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06`

…and the body of `invite.module.css` carries the same DEC at line 1-2:

> `/* The public invitation-accept page. Terminal is dark-only`  
> `   (DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06); tokens come from globals.css. */`

…with the same DEC comment at the head of `SectionTeam.module.css` (`/* MO-PAID-081 (packet W9T_F12_17, link-only): … Dark-only, same tokens as the rest of this module. */`). The DEC is honored at every layer — packet-level, component-level, page-level.

Per-crop measurements are present for all 16 PNGs (sample — desktop-en-team-invite-form.png):

```yaml
desktop-en-team-invite-form.png: {
  inviteGroupTitle: "Invite someone",
  pendingGroupTitle: "Invitations not yet accepted",
  deliveryLine: "We do not send invitation emails: this server has no email delivery set up. Last checked on 13 September 2026.",
  formPresent: true, createButtonText: "Create invitation link",
  emailLabel: "Their email address", roleLabel: "Their role",
  roleOptions: "Member | Administrator",
  linkPresent: false, linkReadOnly: false,
  tokenInVisibleText: false, horizontalOverflow: 0
}
```

Every crop's `tokenInVisibleText` is `false` and `horizontalOverflow` is `0` — the load-bearing UX safety guarantee (raw token never re-printed in page text; link wraps inside `linkRow` without layout overflow). ZH twins measured on the same axes (`我们不会发送邀请邮件：此服务器尚未设置邮件发送功能。最近核查于 2026年9月13日。`, `邀请成员`, `对方…`, `创建邀请链接`, `链接 14 天内有效`, etc.) — full parity.

One open item carried in the file (`# recapture: NEEDED`) — the crops depict commit `f72c33fa` (`capturedAtHead: f72c33fa4efc6c35bc83e7a9bae9b0363c6f7ab8`); `SectionTeam.tsx` and `teams.ts` were changed again at the seat merge (`567fbf31` + h_t588 r2 `6f29872`/`e3ac001`/`2941455c`) for MAJOR-1 (persist-after-roster-failure) and for the `duplicate_invite` no-revoke copy pin. The body says: "crops `recapture: NEEDED`; live readout proof owed after merge + deploy; B-F12-17 stays `BUILT_NOT_PROVEN`." This is a documented known recapture-debt, not a dark/light gap, and the gate explicitly classifies the packet `BUILT_NOT_PROVEN` rather than `PROVEN_LIVE` until recapture + deploy verify the corrected copy. **PASS, with one owed recapture that the merge itself did not skip.** The `layoutFiles` block (8 sha256s covering `SectionTeam.tsx`, `SectionTeam.module.css`, `i18n.tsx`, `teams.ts`, `invitations/route.ts`, `invite/page.tsx`, `InviteAccept.tsx`, `invite.module.css`) is the lock — rebuild any crop and recompute its layoutFiles, or the evidence lock will fail and the PR will not land.

CSS-delta audit: `git diff --name-only 11972af3..dafc016e | grep -iE '\.css$|\.scss$'` returned 2 files:

```
terminal/app/invite/invite.module.css           (+89 lines, ADDED)
terminal/components/settings/SectionTeam.module.css  (+29 lines, MODIFIED)
```

Both files use governed CSS variables only (`var(--text)`, `var(--text-2)`, `var(--panel)`, `var(--panel-2)`, `var(--bg)`, `var(--line)`, `var(--brand)`, `var(--brand-2)`, `var(--warn, #f0a35e)`, `var(--inset)`, `var(--font-ui)`) — the same token family as the rest of the settings chrome (no parallel token family, no `style.textContent`, no JS-injected inline geometry). The brand-2 / accent on buttons is the pre-existing Terminal button pattern; the `:global(.acs-row):has(.actions)` rule in `SectionTeam.module.css:130-137` is the existing cross-component row-layout trick that the prior B-F12-8 packet shipped. No third-header, no local material fork, no `:root` shadowing.

Layout lock verification: `f12_17InviteLinkEvidence.test.ts` (199 lines, ADDED) enforces the layoutFiles sha256s at test time — the test will go RED if any of the 8 listed files change without a recapture + layoutFiles restamp. The body confirms GREEN locally (`Tests 1 passed` for the targeted test filter).

## Validated-claims findings

Laws in force (repo-wide convention; Macro's `scripts/check_validated_claims.py` has no Terminal equivalent):
- Never use "validated / 已验证 / 经验证 / 经过验证" to describe platform signals/rank/gate/scoring claims without a backing artifact.
- `terminal/lib/i18n.tsx:186` carries the standing adherence comment `No "validated", "predictive", or directional trade-signal language.` (preserved through every prior batch and this PR).
- The PR additionally carries a new explicit BANNED-list in `terminal/lib/__tests__/sectionTeam.test.tsx` (round-2/round-3 followup): `[ "falsifier", "refuted", "证伪", "validated", "no_email_delivery", "team_invites", "accept_team_invite", "RLS", "inviteUrl", "token=", "MO-PAID", "W9T", … ]` — the test that owns user-visible-string completeness now ALSO bans these tokens from any rendered surface. **`validated` is in the banned-list as a guard, not as a claim.**

**Verdict: PASS — no new affirmative "validated/已验证/经验证/经过验证" claim introduced.**

Spot-check of all 8 PR-touched source files (`SectionTeam.tsx`, `InviteAccept.tsx`, `page.tsx`, `invitations/route.ts`, `teams.ts`, `i18n.tsx`, plus the two CSS files) for `validated`/`验证`/`经验证`/`已验证`/`经过验证`:

```bash
git diff 11972af3..dafc016e -- 'terminal/lib/*.ts*' 'terminal/components/**/*.tsx' 'terminal/app/**/*.tsx' \
  | grep -E '^[+]' | grep -iE 'validated|验证|经验证|已验证|经过验证'
+    "falsifier", "refuted", "证伪", "validated", "no_email_delivery", "team_invites",
```

The single hit is a BANNED-list entry inside `sectionTeam.test.tsx` — the test bans the word `validated` from any user-visible rendering, which is the OPPOSITE direction of a claim. The line lives in a test fixture, not in any rendered surface. Pre-existing occurrences (none touched by this PR) are all in the same transparency-disclosure / admin-label categories the prior #586/#669 audits already catalogued (`terminal/lib/i18n.tsx:65/97/108/410/186/244/270/124/1265/2543/2613/28` — pre-existing negation/transparency strings; the pre-existing `validated: ["Passed checks", "已通过检验"]` admin-tooling label at `i18n.tsx:28` is unchanged and lives in an admin-only context).

None of the 21 new LEX pairs or the 12 new `INVITE_MESSAGES`/`NO_EMAIL_*` tuples contain "validated" or its ZH equivalents. The packet is an invitation-flow surface (settings team-invite form + public accept page + one API route) — it carries no signal/rank/gate/scoring claim at any layer. The honest-no-mail sentence (`"We do not send invitation emails: this server has no email delivery set up. Last checked on 13 September 2026."`) is the OPPOSITE pattern: a transparent failure framing that disclaims a capability the platform does not have, dated to a specific check. UWP-R2 (two-organisms law) is honored implicitly — no scoring/ranking language is introduced because no organism in this surface generates one.

The 409 `duplicate_invite` copy (`"There is already a pending invitation for this email address. Its link cannot be shown or regenerated; wait for it to expire or invite a different address."`) is honest failure framing too — admits the no-revoke limitation rather than claiming a re-send capability that does not exist. The disclosure form is the lawful pattern under the validated-claims gate.

## Overall verdict

**PASS** — all three gates satisfied; packet is lawful under the plain-language / theme-art-direction / validated-claims stack.

| gate | result | evidence |
| --- | --- | --- |
| plain-language | PASS | `check_plain_language.mjs --json --since 11972af3` → `counts.blocking: 0`, `legacyReported: 18` (unchanged from base); 21 new bilingual LEX pairs (`acsTeamInvite*` + `inv*`); 12 new catalogued `[en, zh]` tuples in `INVITE_MESSAGES` + `NO_EMAIL_*`; zero raw English literal in any user-visible position; one honest null for `app/invite/page.tsx` (Next.js metadata only) |
| theme (TP-0 + Terminal dark-only DEC) | PASS | 16 PNGs = dark × EN/ZH × 1440/390 (4 packet-states × 2 viewports × 2 languages); DEC `TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` cited at packet-level (`EVIDENCE.yml` line 3) and component-level (`invite.module.css:1-2`, `SectionTeam.module.css:1-2`); per-crop measurements carry the EN/ZH strings as actually rendered + `tokenInVisibleText: false` and `horizontalOverflow: 0` on all 16; 2 CSS files in diff use governed tokens only; one documented recapture owed (`BUILT_NOT_PROVEN`, not silently greened) |
| validated-claims | PASS | zero new affirmative "validated/已验证/经验证/经过验证" claim (`git diff ... | grep -E '^[+]' | grep -iE ...` returns only one BANNED-list entry inside a test fixture); pre-existing hits are pre-existing transparency-disclosure / admin-label positions; UWP-R2 not triggered (no scoring/ranking surface in this packet); dated honesty line (`INVITE_EMAIL_DELIVERY_CHECKED_AT = "2026-09-13"`) is the lawful disclosure form |

Notes for the commissioning seat:

- Plain-language: 0 blocking. The 18 legacy findings are pinned at the same count as the prior #669 audit head (the intervening merges #587/#584/#660/#659/#642/#664/#666 did not add any). The new strings are all routed through `t()` (Settings + accept page) or `INVITE_MESSAGES` (API), and every visible position is bilingual with CJK punctuation.
- Theme: zero CSS token family change. The 2 CSS files in the diff inherit the existing `--text` / `--panel` / `--brand` / etc. variables from `globals.css`; no third-header, no parallel material fork, no runtime JS style injection. The `f12_17InviteLinkEvidence.test.ts` layout-lock test will go RED if any of the 8 listed files change without a recapture + restamp, which is the mechanism the body relies on to gate future uncaptured renders.
- Validated-claims: the new BANNED-list inside `sectionTeam.test.tsx` actively forbids `validated`, `falsifier`, `refuted`, `证伪`, `no_email_delivery`, `team_invites`, `accept_team_invite`, `RLS`, `inviteUrl`, `token=`, `MO-PAID`, `W9T` from any user-visible surface. This is a guard rail upgrade, not a regression. The packet only carries negative-space framing (no mail, no revoke, no re-send, no re-show), which is the lawful failure-disclosure form.
- The `# recapture: NEEDED` flag on `w9t-f12-17-invite-link-honesty/EVIDENCE.yml` is a known owed proof step post-merge — B-F12-17 stays `BUILT_NOT_PROVEN` by the body's own classification; the live capture must happen on the deployed artifact after the round-3 `duplicate_invite` copy pin lands before the packet can be flipped to `PROVEN_LIVE`. This is correctly disclosed, not hidden.
- The r2/r3 rounds are merged with **merge commits at the seat** (`567fbf31` for the r1 master merge, `2941455c` for the r2 sync, `c88c5e1f` for the r3 test pin) rather than squash — the body's "MERGE THIS PR WITH A MERGE COMMIT (branch-only pointers)" instruction is honored. Subsequent recapture can target the merge commit directly without restacking the diff.
- The API route's `delivery` block carries the dated honesty line through both `POST /api/teams/invitations` (create) and `GET /api/teams/invitations` (list) so the unsent-invitation list reads the same honesty line the form does — there is no path in this PR where a team owner sees an "invitation sent" promise.
- The body claims `npx vitest run` → `Test Files 359 passed (359)` / `Tests 5917 passed | 4 todo (5921)`, `npx tsc --noEmit` exit 0, and `restamp_terminal_pins.py check` clean at the r3 commit. The audit did not re-run vitest/tsc — the focus is the plain-language / theme / validated-claims gates per the commission. The checker's base-vs-head census is the independent reproduction the audit ships.

## Audit commands and inputs

- Plain-language: `cd /tmp/t588-audit/wt && git sparse-checkout add terminal/scripts terminal/app terminal/components terminal/lib && npm install typescript@5 --no-save --silent && node terminal/scripts/check_plain_language.mjs --json --since 11972af358926552e82ee8c7e7843dc831561677` (exit 0; ran on detached HEAD `dafc016e`, base `11972af3`).
- Theme: `terminal/docs/pr-crops/w9t-f12-17-invite-link-honesty/EVIDENCE.yml` parsed (16 PNGs × {4 states} × {1440, 390} × {en, zh}); per-crop `measurements` block sampled (EN + ZH strings as actually rendered); `git diff --name-only 11972af3..dafc016e | grep -iE '\.css$|\.scss$'` = 2 files (`invite.module.css`, `SectionTeam.module.css`); both files inspected for token usage (governed only).
- Validated-claims: `grep -in 'validated|验证|经验证|已验证|经过验证'` over the 8 PR-touched source files; `git diff 11972af3..dafc016e -- 'terminal/lib/*.ts*' 'terminal/components/**/*.tsx' 'terminal/app/**/*.tsx' | grep -E '^[+]' | grep -iE ...` (one BANNED-list entry, in a test fixture, not in a rendered surface).
- PR metadata: `gh pr view 588 --repo mastermindx-market-intelligence/mastermind-terminal --json number,title,body,mergedAt,mergeCommit,headRefName,baseRefName,files,additions,deletions`. Body parsed line-by-line; 70-row Files-changed table re-extracted from `gh pr view --json files`.
- Worktree: `git worktree add /tmp/t588-audit/wt dafc016e4e9e34f4a8be3e0a98819b098eedf8df --detach` (on `mastermind-terminal` repo); `git sparse-checkout init --cone && git sparse-checkout set terminal/app terminal/components terminal/lib terminal/scripts` then `git sparse-checkout add terminal/docs/pr-crops` to bring in the new packet's evidence directory. `origin/pr/588` ref is gone — branch was deleted after merge, so the audit ran on the merge commit directly.

SESSION END: PROVEN_OUTCOME — single merged PR audited; three gates returned concrete verdicts (plain-language PASS / theme PASS / validated-claims PASS); report written to `orch/audits/mastermind-terminal_pr588.mm.md`; no durable state outside the audit file.
