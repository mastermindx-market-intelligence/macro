---
key: MASSIVE-REST-OPTIONS-SNAPSHOT-NOT-ENTITLED-ON-STOCK-PLAN
claim: >
  The Massive credential installed on the production VPS for the option-OI observer
  (LoadCredential massive-option-oi-api-key, 32 bytes, byte-equal to the estate's
  MASSIVE_API_KEY) is a stock-market-data plan key: the REST stocks snapshot
  (/v3/snapshot/locale/us/markets/stocks/tickers/SPY) returns 200 with it, while the REST
  options snapshot the observer needs (/v3/snapshot/options/SPY) returns 403
  NOT_AUTHORIZED "You are not entitled to this data. Please upgrade your plan". The
  option-OI unit therefore fails closed on a vendor ENTITLEMENT boundary, not on a wrong,
  expired, or mis-mounted key, and no code change, key re-mount, retry, or timer re-arm can
  make it capture.
falsifier: >
  Running the same discriminator (on-VPS curl of GET https://api.massive.com/v3/snapshot/options/SPY
  with the key at the LoadCredential path, printing only the HTTP code and the JSON
  status/message) returns 200 with a results array; or one scheduled
  macro-market-memory-options.service run after a plan/key change persists an option-OI
  observation for a trading day instead of logging the fail-closed stage token.
so_what: >
  The D-options capture is an EXACT_HUMAN_GATE for the Chairman (plan upgrade or an entitled key
  installed at /etc/macro-market-memory-options/massive-option-oi-api-key = money), not a lane
  for any seat or worker: never swap in another estate key, never widen the unit, never re-arm
  the weekday timer before an entitled key exists. #8818's EACCES tolerance and stage token are
  PRODUCTION_PROOF on the failure line (15:00:23Z run), which is why the failure is now
  attributable from journald alone. The 2026-08-20 flat-file 403
  (DSC:MASSIVE-OPTIONS-FLATFILE-ENTITLEMENT-REGRESSION) explicitly excluded this REST case; the two
  records together say the estate has never held an options entitlement on either transport.
kind: constraint
verified_at: 2026-10-11
verified_by: >
  Seat fd47d431, 2026-10-11 15:0xZ, on root@146.190.142.17: key byte length 32 and equality with
  MASSIVE_API_KEY computed via bash process substitution; GET stocks snapshot HTTP 200; GET
  options snapshot HTTP 403 with status NOT_AUTHORIZED. No credential value entered any
  transcript, packet, or log. Corroborated by ORCH-OPS a5ccb27d (EXACT_HUMAN_GATE packet,
  15:10Z) and by the fail-closed stage token in the 15:00:23Z journald line after #8818 pulled.
scope:
  - engine/neuralweb/market_memory_option_oi_observation.py
  - app/deploy/macro-market-memory-options.service
  - research/licenses/MASSIVE_ENTITLEMENT_RECORD.md
confidence: verified
---

Entitlement evidence on file (`research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`) covers stock
market data only. The REST options snapshot path is pinned at
`engine/neuralweb/market_memory_option_oi_observation.py` (SOURCE_HOST api.massive.com,
SOURCE_PATH /v3/snapshot/options/SPY). Release condition: an entitled key at the LoadCredential
path, then one scheduled run; the weekday timer stays disarmed until that run persists a row.
