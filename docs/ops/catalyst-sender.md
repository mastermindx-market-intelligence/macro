# Catalyst sender — one message per (user, event, generation)

Owner: `engine/marketing/catalyst_lifecycle.py` (`FunnelService.deliver_generation`,
`format_generation`) and `app/catalyst_optin.py` (`ExistingMailerDelivery`,
`deliver_update`). Decision: `DEC:MX-CATALYST-B2-CONSOLIDATED-SENDER-20261102`.

## Contract

- The producer hands over **every per-ticker revision of one event+generation at once**
  (`load_public_revisions(event_id, generation) -> tuple[PublicRevision, ...]`). A
  single-revision loader is not accepted by the seam (`REVISION_OWNER_NOT_READY`), and
  `FunnelService.deliver(revision)` refuses (`INVALID_REVISION_SET`) when the authority
  reports more than one ticker in that generation: a ticker-by-ticker drip would mail the
  first ticker and leave the rest `ALREADY_CLAIMED`.
- The lifecycle refuses a set that mixes events or generations, repeats a ticker, is
  empty, exceeds 12 items or holds an unapproved revision (`INVALID_REVISION_SET`).
- A reader's bundle is the followed tickers whose evidence (`as_of_utc`) is newer than
  that reader's consent. No followed ticker: `SUPPRESSED`. Nothing newer than the consent:
  `NOT_SECOND_VALUE`. Live rights are read for every item before the roster, and again for
  each item of the reader's bundle before the sender; one item without rights holds the
  whole message (`SOURCE_RIGHTS_NOT_CURRENT` / `SOURCE_RIGHTS_UNAVAILABLE`).
- The ledger key is `catalyst:<event>:<generation>:<user>`. The incumbent `email_log`
  unique key is the only delivery claim: a second claim is `ALREADY_CLAIMED`, never a
  second email. A producer that drips one generation ticker by ticker therefore gets
  `ALREADY_CLAIMED` from the second call on; the drip is not a supported contract.
- Copy: one item renders as before (`Update:`/`Correction:` heading, message, evidence
  clock, sources, unsubscribe). Several items keep each ticker's own block in ticker
  order under the subject `N updates: T1, T2`, prefixed `Correction:` when any block is a
  correction or retraction; the subject carries the count and tickers only. The mailer
  and the formatter re-validate any bundle they did not assemble.

## Before the mail flag is ever turned on

- The ledger key no longer carries a ticker. Confirm the incumbent `email_log` holds no
  row whose `idem_key` starts with `catalyst:` under the old
  `catalyst:<event>:<generation>:<ticker>:<user>` shape (expected zero: the host has never
  had SMTP). An old-shape claim would not collide with the new key, so a reader claimed
  under it could be mailed again for the same generation.

## Gates that stay closed

- `MAIL_CATALYST_ENABLED` is OFF on the host; the adapter also needs the incumbent
  mailer configured and an https unsubscribe pair. With any of them missing the lane is
  `SEND_BLOCKED` and nothing is claimed.
- Docket B2 acceptance needs an SMTP provider on the macro-api host and a designated
  consenting test recipient. That is the Chairman's spend and the one human gate of this
  program; it is named once and not re-asked.
