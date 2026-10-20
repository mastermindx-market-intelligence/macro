---
key: PORTFOLIO-CURRENCY-APPLICATION-RECEIPT-RECOVERED
claim: >
  Terminal Portfolio migration 0036 was applied through the original applier on
  2026-10-19T01:13:16Z, although its subsequent handoff and PR metadata continued
  to say unapplied; the original receipt and matching live catalog were recovered
  on 2026-10-20 without reapplying the migration.
falsifier: >
  From a mastermind-terminal checkout, run `git show
  51d8820530cbe4f47614199bb7e0eb3daa748410:terminal/docs/verification/portfolio-workspace/0036-production-receipt.json
  | sha256sum` and require
  511faa4788ca35b8946070bdc8420057fcd0bd62be96fa289c058609e3fe3ff1.
  Run `git show
  51d8820530cbe4f47614199bb7e0eb3daa748410:supabase/migrations/0036_portfolio_entry_currency.sql
  | sha256sum` and require
  9c09540e7b4e451e55a39d8229b3a73eb93c997578f3dadfdc3f24b47a7f7f4c.
  A hash mismatch disproves receipt identity or source binding respectively;
  a conflicting current read-only catalog disproves continued compatibility,
  not by itself the historical application event in Terminal #1044.
so_what: >
  Do not apply 0036 or the superseded old #866 currency candidate again. Recover
  the original receipt before reasoning from a stale handoff. Reconcile only
  #1044's applied metadata while its row remains open, preserve other migration
  records and applied SQL bytes, and retain the separate application-review,
  current-base CI, solo-merge, ledger-follow-up, deployment and live-proof gates.
kind: landmine
verified_at: 2026-10-20
verified_by: >
  Terminal #1044 issuecomment-6283607982 publishes the complete original
  4,419-byte receipt and its independently matched SHA-256, the original
  before/after estate-preservation binding, and the 2026-10-20
  04:42:23-04:44:49 UTC SELECT-only production catalog readback.
scope:
  - "WS:MARKET-OS"
  - "mastermindx-market-intelligence/mastermind-terminal"
  - "supabase/migrations/0036_portfolio_entry_currency.sql"
  - "supabase/migrations/RESERVATIONS.json"
confidence: verified
---

# Original effect recovered; no second application

The original implementation carrier remains Terminal PR #1044. Its historical
source head is `75eaabd1ebc4af3bf7e43b8488d519da9024dd45`. The earlier
[Portfolio handoff](../handoffs/MARKET-OS-2026-10-18-PORTFOLIO-WORKSPACE-IMPLEMENTATION.md)
and subsequent PR prose retained an outdated unapplied state. They are not a
reason to repeat a production mutation.

## Exact evidence

The [complete recovered receipt and current catalog reconciliation](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1044#issuecomment-6283607982)
bind:

| Fact | Evidence |
| --- | --- |
| Original application | `2026-10-19T01:13:16Z`, status `applied`, one statement, five successful readbacks, no missing object or error |
| Applied SQL SHA-256 | `9c09540e7b4e451e55a39d8229b3a73eb93c997578f3dadfdc3f24b47a7f7f4c` |
| Original receipt SHA-256 | `511faa4788ca35b8946070bdc8420057fcd0bd62be96fa289c058609e3fe3ff1` |
| Original receipt size | 4,419 UTF-8 bytes, including final newline |
| Original runner SHA-256 | `938349bba26a848508a579835245d77a70c01baa7e9b641d9163d4f3c8ec0b55` |
| Original estate comparison | Before `01:13:11.882652Z`, after `01:13:16.774276Z` on 2026-10-19; ACL, RLS and all eight owner policies equal |
| Independent current observation | SELECT-only catalog checks on 2026-10-20, 04:42:23-04:44:49 UTC |

The original files were recovered from the retained verification directory:
`/tmp/terminal-portfolio-verification-20261018/0036-production-receipt.json`
and `0036-production-estate-preservation.json`. The GitHub receipt publication
preserves the application JSON independently of those temporary host paths.
The recovered JSON was hashed separately and matched the hash recorded by the
original estate receipt.

Current catalog reads confirmed the two nullable/default-free receipt columns
(`text` and `jsonb`), validated currency constraint, enabled trigger, invoker
function and its fixed search path/body, column comments, RLS enabled and not
forced, and unchanged owner-policy and table-ACL shapes. These queries read no
holdings or account rows and performed no DDL.

## Consequence and boundaries

The [narrow currency disposition](../decisions/DEC-PORTFOLIO-CURRENCY-FORWARD-DISPOSITION-2026-10-18.md)
was normally accepted through Macro #9593, merge
`97261c2a319e62faec05690c04e6fae180540235`. It makes #1044/0036 the sole
application candidate for this delivery while preserving applied #946/0032 and
the incumbent #778/0035 claim. It does not authorize applying both currency
filenames.

The original effect is reconciled as applied. The next source metadata update
must record that original application date and receipt while retaining
`pr: 1044` and `pr_state: open` until the actual merge. Do not pre-flip the
row to merged, change unrelated reservations, or modify the applied SQL bytes
merely to restamp its history. Follow the accepted
[solo migration and immediate ledger-follow-up procedure](../decisions/DEC-TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP.md)
for the later release.

This discovery is not acceptance of the remaining Portfolio application
repairs, current-base integration, release, deployment, authenticated persistence,
or production performance/accessibility. Their exact continuation remains on
the [existing cumulative implementation checkpoint](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1044#issuecomment-6282836784).
It creates no new runtime, lease, migration ledger or authority plane.
