---
key: PORTFOLIO-CURRENCY-FORWARD-DISPOSITION-2026-10-18
question: >
  How should Terminal #1044 carry the pending entry-currency change from #866 when
  applied #946 already owns 0032, earlier-opened #778 now claims 0035, and the old
  currency carrier waits for unrelated lower-numbered migrations?
answer: >
  For this Portfolio delivery only, carry the unapplied entry-currency change as
  0036_portfolio_entry_currency.sql on Terminal #1044. The source proposal
  is ea57ad23691df6f848cce65fe814b6cd97f9cfa6 and the executable candidate file SHA-256
  is 9c09540e7b4e451e55a39d8229b3a73eb93c997578f3dadfdc3f24b47a7f7f4c.
  Preserve the applied #946/0032 file and reservation, #778's pending 0035 claim,
  and all other incumbent reservations. The old #866/0032 currency file is
  superseded as an application candidate for this delivery; do not apply both
  names and do not rename any applied migration.

  This is a narrow amendment to
  DEC:SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06, including its
  earlier-opened exception and absolute numeric application-order clauses.
  After independent source ACCEPT at the actual candidate head, normal required
  gates and current-master reconciliation, this one currency migration may be
  applied without first merging or applying the unrelated pending 0029/0030
  (#804), 0031 (#858), or 0035 (#778). Reserved but unwritten 0026 is not a schema
  prerequisite of this file. The existing portfolio_positions table, RLS and
  exact compatible catalog shapes remain mandatory runtime prerequisites.

  Use DEC:TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP for this carrier:
  accepted source and current PR-scoped namespace proof, reviewed applier dry run,
  admitted application with pre/post catalog receipt, receipt publication and
  truthful applied-state update, solo squash when no landing train is mid-CI,
  then immediate minimal merged-ledger follow-up. Do not pre-flip an open row.
  An authentication refusal, unqualified transport, failed catalog proof or
  EFFECT_UNKNOWN still stops that effect. This choice grants no new credentials,
  runtime admission, user authority or waiver of another carrier's release holds.
rationale: >
  Applying the old currency name would collide with an already-applied function
  repair and make the historical ledger ambiguous. Renaming the unapplied
  candidate preserves that history. A refreshed open-PR census found #778's
  newer 0035 claim, so moving Portfolio to 0036 also respects the earlier-opened
  incumbent rather than claiming the same number twice. The currency DDL touches
  only portfolio_positions and its own nullable receipt columns, shape constraint
  and invoker trigger. It consumes no Investigation, drawing or saved-view object.
  Its guarded one-statement envelope is atomic through the existing applier's
  statement-at-a-time interface, with causal rollback, success and replay proved
  against isolated PostgreSQL. Waiting for unrelated application/UI repairs would
  therefore add delay without protecting a schema dependency. The explicit
  amendment records this bounded exception rather than silently treating technical
  independence as a release authorization or weakening the general namespace law.
alternatives:
  - option: "Apply the original pending 0032 currency file or rename applied #946."
    why_not: "Either path obscures the applied ledger. The applied SQL and row must remain unchanged."
  - option: "Keep Portfolio's first forward proposal at 0035."
    why_not: "The refreshed census finds the earlier-opened #778 at a newer head claiming that number; Portfolio moves to the next free number."
  - option: "Wait for every unrelated lower-numbered pending migration."
    why_not: "The original rule and #866 condition require an explicit exception. Source and isolated catalog evidence support this narrow exception; no foreign carrier is adopted or released."
  - option: "Adopt a general out-of-order policy or weaken the namespace checker."
    why_not: "Neither is needed. The exception binds only this candidate's SQL and carrier, and all existing checker and release controls remain."
evidence:
  - "Chairman request in session chatgpt4-terminal-portfolio-20261018: enhance the exact Paper Portfolio design and implement it fully end to end in Terminal."
  - "Mastermind AGENTS.md at ef4be2f5c9b0b82fc11be83f03cf7bcdb8cea6f2: the currently assigned authorized principal resolves in-scope matters; historical model names are not a new live approver or runtime grant."
  - "Terminal #1044 candidate ea57ad23691df6f848cce65fe814b6cd97f9cfa6; current base 367f488e5c67d0871d4a34c2aa7371f327d44c3d; only 0036 differs in RESERVATIONS.json relative to that base."
  - "Terminal terminal/docs/verification/portfolio-workspace/verification.json at the candidate records the 168-open-PR census (2026-10-18T06:58:50Z), all ten paginated full file lists, a 07:10:54Z delta, and the independent 11:04:42Z update covering all 266 filenames in six other updated PRs with no competing 0036 claim."
  - "Terminal #778 at 88f2919a5c2222bcf05f452f2549b9af180dcae6 reserves 0035_saved_view_guard.sql; its SQL changes workspace_settings and its own saved-view guard, with no portfolio_positions reference."
  - "Terminal #946 applied receipt: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/946#issuecomment-6112592004; preserved 0032 SQL SHA-256 9e360ed109d0c3d8ff3345e90515a2f8da443a03c22f9015514a1b18a2f23dd3."
  - "Original currency source: Terminal #866 at 60fd6d997df52d2d8331de85ab63014446e16ef9, SQL SHA-256 fe4def299cf733dd1718bda8ef30f006a6d19c5015f7673cbab05a4b298f99f5; inner business DDL remains byte-identical after the outer atomic-envelope change."
  - "Terminal tests/sql/audit09/run_native_fixture.py and committed native-postgres/wrapper receipts: 27 isolated cases pass through actual scripts.supabase_apply.run_apply, one application statement, five catalog readbacks, no network or production effects."
  - "Terminal PR-scoped namespace, migration-ledger and applier suites: 189 passed after the 0036 rename. Applied 0032 bytes and its reservation remain exact."
  - "At 11:35:53Z the existing CurlRunner and documented primary credential pair returned six production catalog SELECT results. portfolio_positions exists with RLS enabled, forced RLS false, eight owner policies and no currency objects. Grants and policy rows are retained for post-application comparison. No DDL was sent; this is read-only transport/catalog evidence, not application or authenticated-user acceptance."
  - "Terminal #804 at ad80ceff67e9b9f95a131a74e6bf57aa19e97b39 has green required CI and qualified one-statement 0030 source but is draft/unapplied; #858 at 8abe1ff920be0b754f66d918df61f5ca6d7505ef is draft/unapplied with red browser CI and an unadopted repair proposal."
affects:
  - "WS:MARKET-OS"
  - "terminal-user-services"
  - "Terminal #1044 / pending #866 currency supersession"
  - "supabase/migrations/0036_portfolio_entry_currency.sql"
confidence: high
reversibility: costly
decided_by: "session chatgpt4-terminal-portfolio-20261018 (Astra Pro, Chairman-assigned Portfolio implementation)"
decided_at: 2026-10-18
---

## Scope of the amendment

This is a partial amendment, not wholesale supersession of the namespace decision.
The original decision remains the single-ledger and allocation rule. Its historical
allocation and application evidence remain intact. The reciprocal amendment paragraph
in that record points here without retiring unrelated requirements.

The choice takes effect through independent review and normal acceptance of this
decision change into Macro's canonical main. This knowledge record does not create a
runtime grant: the existing principal assignment, tooling admission, credentials,
source review and release controls still govern each effect.

| Object | Disposition |
|---|---|
| Applied #946 / 0032 | Preserve its SQL, row, source and application history exactly. |
| Pending #866 / old currency 0032 | Historical source for #1044; superseded as this delivery's application candidate. Do not apply its old path. |
| Pending #778 / 0035 | Preserve the incumbent claim and carrier. No adoption or release is implied. |
| Pending #1044 / currency 0036 | Sole candidate for the currency delivery described here, subject to actual source acceptance and release proof. |
| #804, #858, and reserved/unwritten 0026 | Preserve their own scope and conditions. This migration has no schema dependency on them. |

The candidate's SQL SHA-256 binds the executable proposal. Later comments or ledger
metadata may record a real application, but must retain the applied source hash and
receipt. A semantic SQL change requires fresh qualification and independent review;
this record is not blanket acceptance of future currency DDL.

## Required operational evidence

The isolated fixture is strong evidence for atomicity and existing-runner integration.
It is not a production HTTP receipt, current catalog inspection, authenticated-user
acceptance or deployment receipt. No production DDL was applied in making this record.

Before application, reconcile the exact current candidate and master, confirm source
ACCEPT and concluded required CI, verify the current reservation census, and use the
existing reviewed applier's dry-run and catalog checks. A production attempt must use
the already-admitted carrier and its existing credential handling. A 401 requires
human PAT rotation under the incumbent procedure; no second carrier or credential
route is authorized by this decision.

Publish the actual receipt before marking application successful. The solo landing
and immediate ledger follow-up retain the open-row ownership invariant and prevent
a false merged declaration. Deployment and authenticated Portfolio verification
remain separate from schema application.

## Source pointers

- [Portfolio candidate and implementation](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1044)
- [Exact currency proposal](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ea57ad23691df6f848cce65fe814b6cd97f9cfa6/supabase/migrations/0036_portfolio_entry_currency.sql)
- [Verification and receipt index](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ea57ad23691df6f848cce65fe814b6cd97f9cfa6/terminal/docs/verification/portfolio-workspace/verification.json)
- [Original namespace decision](DEC-SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06.md)
- [Existing solo migration landing procedure](DEC-TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP.md)
