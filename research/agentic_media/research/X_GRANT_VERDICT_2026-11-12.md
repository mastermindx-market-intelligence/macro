# Verdict — "X grant number is real" gate

**As of:** 2026-11-12 (MST) · **Card:** kanban `t_e305794e` (XG registry content v1) · **Gathered:** read-only, worktree `/Users/chriswong/.hermes/profiles/marketing/cache/scratch/xg-wt` @ branch `xg/runtime-adapter-v1`, HEAD `254d89c473`

VERDICT: **GATE NOT SATISFIED — no real grant on record as of 2026-11-12**

No X/Twitter API grant number, pack number, invoice, paid-tier receipt, entitlement read-back, or vendor Enterprise quote for this programme exists anywhere on disk. Every mention is one of: (a) a recommendation/budget/modelling assumption, (b) a documented limitation with entitlement explicitly *unresolved*, or (c) a proposal explicitly marked unapproved. Category (c) of the brief — a REAL issued/paid entitlement with a number or receipt — has **zero** occurrences.

## Evidence

| # | Citation (exact) | Class | What it establishes |
|---|---|---|---|
| 1 | `research/agentic_media/research/X_API_FOLLOW_LIMITS_BRIEF_2026-11.md:3` | (b) | "This is a planning brief. **No account was accessed, credits purchased or platform action tested.**" |
| 2 | `research/agentic_media/research/X_API_FOLLOW_LIMITS_BRIEF_2026-11.md:13` | (b) | "**Minimum pack and Enterprise quote remain UNRESOLVED.** The earlier $42,000–$50,000 Enterprise figures were third-party reports, not a vendor quote for this programme." — no pack id, no quote number |
| 3 | `research/agentic_media/research/X_API_FOLLOW_LIMITS_BRIEF_2026-11.md:11` | (a) | The $5 credit pack + single-follow probe is "**unapproved future work**" |
| 4 | `research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md:20` | gate def | "Account entitlement and platform permission \| Required before any live action … **a generic price row or vendor endpoint is not permission**" |
| 5 | `research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md:268` (§12.5) | (b) | Self-serve follow/like/quote "unsupported absent **actual account-specific entitlement**"; "Minimum purchase and Enterprise pricing are **unverified**"; the $5 probe "**is not approved here**" |
| 6 | `research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md:466` (§22.3) | (b) | "Actual account checkout, features and eligibility remain **UNVERIFIED**. Do not buy a tier or infer reach from the $8 modelling unit." |
| 7 | `research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md:234` | (a) | Vendor follow/unfollow "60 credits, $0.0006/call — Published endpoint price; **no account action or invoice tested**" |
| 8 | `research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md:384` (§18.6) | (a)/(b) | "$8 unit is an **unverified modelling assumption, not proof of tier eligibility**, checkmark or approved subscription"; seat cap remains a proposal |
| 9 | `research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md:382` (§18.4) | (a) | "$50–75 minimum pack … remain **separate unapproved spend**"; new purchase receipt not established |
| 10 | `research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md:255` | (a) | Buffer $6/$4/$3/$1 bands are "author-reported **illustrative model, not a currently verified checkout**… Actual connected/billed inventory and invoice remain unverified" |
| 11 | `research/agentic_media/research/X_AUTOMATION_RAILS_2026-11.md:66` | (b) | Comparison row: "Current programme status \| **No new account entitlement proved**" |
| 12 | `research/agentic_media/research/X_AUTOMATION_RAILS_2026-11.md:5` | (b) | "A capability comparison **is not an execution grant**"; brief "admits no account, browser, credentials, spending or live action" |
| 13 | `research/agentic_media/research/X_PUBLISHING_SCALE_DECISION_2026-11-07.md:25` | (b) | "Actual connected inventory, plan, tax, billing cycle and invoice must be read before a purchase… **This correction did not access a billing account.**" |
| 14 | kanban `t_da720ee4` comment, engineering, 2026-11-08 04:52:55 | (b) | Preconditions table row: "**X grant number real \| NO**" citing brief `:9,13,28`, masterplan `:268,466`, rails `:66` |
| 15 | kanban `t_e305794e` comment, marketing, 2026-11-10 09:43:55 | (b) | "**X grant number: not real.**" Cites `:20`, `:268`, `:466`; notes this does **not** block a `proposed`-state registry but does block any advance to `admitted`/`suspended` |
| 16 | `tools/xguerrilla/registry.yml:11-14,36,39` (at merge `8f12b4e2a1` and HEAD) | state of record | All five entries + domain `state: proposed`, `admission_receipt: null`; header states "no admission receipt exists on disk for any identity" |
| 17 | commit `8f12b4e2a1` (squash of PR #10947, merged 2026-11-10T10:28:44Z) | disposition | Registry content landed **only** because it is inert: engineering review (`t_e305794e`, 2026-11-10 10:15:32) records "landing it **enables no live action and does not satisfy or waive the grant gate**" |
| 18 | kanban `t_fd170576` ("X posting gate — endpoint permission + entitlement + spend + credential custody") | blocked | Still `blocked`, no `completed_at`, opened 2026-11-08 04:36; the gate item itself has never closed |
| 19 | commit `254d89c473`, 2026-11-11 18:57 MST (HEAD, newest XG work) | (b) | New adapter binds "content-pinned admission receipts ({path, sha256})" before any effect — structurally presumes a receipt that does not exist; adds refusals, not an entitlement |
| 20 | `research/admissions/` | absent | Directory does not exist; `git log --all -- research/admissions` is **empty** — no admission receipt has ever been committed |

Absence checks run and returning nothing: `git grep` over `research/agentic_media/*` and `tools/xguerrilla/*` for `pack[_ -]?id`, `entitlement[_ -]?id`, `invoice`, `order[_ -]?(id|number)`, `purchase receipt`, `credits? purchased`, `billing account`, `INV-[0-9]` — only the "no invoice tested / unverified" prose rows above. Kanban: no task created on/after 2026-11-10 mentioning X API grant, pack, enterprise, or entitlement status change. Git: only one commit touched `tools/xguerrilla/`/`research/agentic_media/` since 2026-11-10 (`254d89c473`), and it contains no entitlement.

## What a marginal reader might mistake for the gate, and why it isn't

- **PR #10947 merged (`8f12b4e2a1`) → `t_e305794e` is `done`.** The card's *content* deliverable was always gated on "proposed"-state records, and every record is `state: proposed` with `admission_receipt: null`. The reviewing engineer stated the sequencing gate "is still unmet" in the same breath as approving. Card completion ≠ gate satisfaction.
- **Published X API unit prices ($0.015 create, $0.200 URL post, $0.010 read).** These are public tariff rows; brief `:5` and masterplan `:20` both say a price row is not an entitlement, and `:13`/`:268` say this account's minimum purchase and Enterprise quote are unresolved.
- **$350 / $347.56 / $8-per-seat figures.** Explicitly labelled recommendation and unverified modelling unit (`:384`, `:466`, §18.3, §22.4) — no purchase, no approval, no checkout.

## What would satisfy the gate

1. **An account-specific entitlement read-back** from the X developer portal for the actual account/app: plan name, tier, and confirmation that follow/like/quote endpoints are enabled for *this* account — stored as a dated receipt (not a screenshot of a price page).
2. **Or a purchase receipt / invoice with an identifier** — pack number, invoice number, or Enterprise order/SOW reference — showing money actually paid to X for the programme's API access, plus the credit balance read back from the account.
3. **Then** at least one `admission_receipt: {path, sha256}` committed under `research/admissions/`, which flips one registry entry from `proposed` to `admitted` and makes `XG-W8` (rail proof) executable.
4. Failing 1–3, an explicit **Chairman waiver** recorded in a decision record — that would satisfy the *programme* gate by ruling it unnecessary, but it must be a written ruling, not an inference from merged docs.

Until one of those exists, the gate is NOT SATISFIED. No grant number, pack id, or price has been invented here.

---
*Method note: prior child attempt (2026-11-10) died on a provider 429 before any tool call; this verdict was gathered fresh. Read-only throughout — no writes in the worktree, no git mutations.*
