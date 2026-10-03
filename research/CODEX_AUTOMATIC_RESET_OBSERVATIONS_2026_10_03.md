# Codex automatic resets: consume observations, not a gift calendar

Status: SOURCE_IMPLEMENTED / NOT_LIVE. Operation:
`codex-observed-reset-refresh-20261003-sol-001` under the existing
WS:EXECUTIVE-CAPACITY-FABRIC programme. This is a bounded correction to the
existing single-account Codex research lane, not the global allocator in #7116.

## Provider evidence

OpenAI describes occasional one-time resets for eligible users. Coverage and
redemption conditions vary, and future offers are not guaranteed. Automatic
resets apply directly; some offers also provide a separate banked reset. Do not
assume an announcement refilled every account or consumed a banked entitlement.

The account API exposes usedPercent, windowDurationMins and the actual next
resetsAt timestamp, plus account/rateLimits/updated and account/rateLimits/read.
These percentages are not a fixed remaining-token allowance. Current upstream
rounds the percentage when serializing it; an unchanged reading is not zero burn. Token activity is
available separately. Use the observed window duration, not primary/secondary
position, to interpret its period. Preserve null/missing distinctions and select
the account's appropriate named quota bucket. [1, 2]

Current upstream additionally exposes ordinaryUsageAllowed, validated by the
native account owner. Its null value does not establish ordinary-use permission;
percentages and reset timestamps cannot substitute for it. Upstream source pin:
`openai/codex@55b6f282a810c3146a1f79c7c2e6e919cc0aa974`, account protocol lines331-341
and account_processor lines1269-1294. A new upstream field is not proof that an
older installed CLI provides it. [3, 4]

## Deterministic owner behavior

No promotional-event schedule, synthetic refill transaction or manual quota
ledger is needed. On a fresh, correctly bound native read, replace absolute usage
and deadlines and recompute any pending advisory ranking. An unsolicited refill
can already be partly consumed by the time it is observed. Do not force it to
zero usage or derive a new date as observation time plus seven days.

Reject older/equal-time conflicting observations, nonnumeric/negative/nonfinite percentages and
incomplete constraints. Finite usage above 100 is over budget, not discarded or
clamped into a healthy state. A full read supersedes a cache; an old response arriving
later does not. Retain actual failure history. An error containing an old snapshot
is NOT proof the error itself is old: keep the failure, use the newest accepted
clock and require another fresh read to clear its quota pause.

Pending reset effects and claims remain with their original owners. A higher
balance does not prove our prior redemption succeeded. Read the original reset
operation and independently refresh the banked inventory; never retry or debit it
because a gift happened. Invalidate burn-calibration intervals spanning a reset
or otherwise discontinuous observation; a negative delta is not free inference.

## Implemented path and proof boundary

The unchanged codex_research_loop already fetches before can_run on every
iteration. budget.note_rate_limits now preserves observation ordering and allows
only complete readings at most ten minutes old to clear a known quota pause. The
read must not predate the prior persisted state transition. Ten minutes is a
bounded local pause-clear policy, not a provider guarantee or a new scheduler.

runner.fetch_rate_limits validates percentages, retains actual reset times and
selects the named codex bucket. An explicitly present map without that bucket
stays unavailable; it cannot borrow legacy quota. A historical captured response
with an empty map is preserved as a negative compatibility fixture. Normalizer
field tests now use the documented populated-map form.

When supplied, ordinary_usage_allowed survives normalization. False/null block
ordinary local budget admission; a later field-less response cannot erase this
newer-protocol constraint. Legacy field-absent behavior remains compatible, not
proof of permission. No private account identifier is persisted by this addition.

Tests use private temporary roots, fake native transport and a fake useful lane
callback through the REAL loop, budget and JSON normalizer. No real provider,
reset, credential, service, active session or production usage file is touched.
The existing state file is retained; this patch adds no quota store, daemon,
claim manager, retry plane or independent multi-writer lock. Its timestamps order
this existing single-account producer, not arbitrary cross-host writers.

## Remaining programme work

Source acceptance, exact installation, account enrollment, cross-account
reservations, notification/refresh integration and actual original-parent result
consumption remain separate. The existing global owner must join qualified
account identity, apply its native claim-time freshness rules and invalidate old
plans after observation changes. This patch does not clear #7116 or the previously
denied consumer bridge, nor certify the all-account system live. #8255 remains the
separate supplied-evidence reset-economics source; #1158 preserves native window
applicability. Do not use an old forecast as reset execution permission.

## Sources

[1] https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
[2] https://learn.chatgpt.com/docs/app-server
[3] https://github.com/openai/codex/blob/55b6f282a810c3146a1f79c7c2e6e919cc0aa974/codex-rs/app-server-protocol/src/protocol/v2/account.rs
[4] https://github.com/openai/codex/blob/55b6f282a810c3146a1f79c7c2e6e919cc0aa974/codex-rs/app-server/src/request_processors/account_processor.rs
