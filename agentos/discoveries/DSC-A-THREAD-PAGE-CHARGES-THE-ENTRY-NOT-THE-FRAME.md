---
key: A-THREAD-PAGE-CHARGES-THE-ENTRY-NOT-THE-FRAME
claim: >
  Capacity arithmetic over a message-API page must charge each item the size of the OBJECT that
  carries it, never the size of the payload it contains, and an API that keeps edit history
  charges some items twice. Measured 2026-09-25 on Mastermind
  `common/agent_dialogue_consultation_contract.py` at `87117418`: `replies_page_has_room` charges a
  candidate its bare rendered frame (4,499 bytes) and therefore admits 14 replies into a 64 KiB
  page. Using the SMALLEST object the incumbent parser accepts (`type`/`user`/`text`/`ts` only) and
  the most generous serialisation, those 14 replies really cost 66,220 bytes - over the ceiling by
  684. A `message_changed` entry, which the same parser accepts, carries the text in BOTH `message`
  and `previous_message`: 9,594 bytes for one reply, 2.13x the charge. Under the API's own wire form
  the same entry is 9,799 bytes and 14 of them cost 137,186.
falsifier: >
  Set `page_ceiling_bytes` to one byte less than a single minimal real entry and ask whether there
  is room. A correct helper refuses; this one admits, because it charges only the payload. The test
  needs no live API call and no assumption about the API's escaping: the defect fires even under the
  most generous encoding, which is what makes it provable offline.
so_what: >
  Derive a page charge from the consumer's own parser - which fields it REQUIRES, and which entry
  subtypes it accepts - not from the payload the producer rendered. Where the parser accepts
  edit/delete entries that retain a previous copy, the charge must express "stored copies", because
  no constant fudge factor is right: the ratio moves with the entry subtype. And check what the
  overflow actually does before ranking it: here the reader RAISES above its response ceiling rather
  than truncating, so an over-capacity page is an unreadable thread, not a degraded one. Separately,
  the adapter discards the raw response body after decoding, so no caller can measure the true page
  size - a capacity law that cannot be validated against a real page is a second, quieter defect.
kind: law
verified_at: 2026-09-25
verified_by: >
  Read `SlackWebApiAdapter._standard_message` and `_parse_message` at Mastermind `87117418` for the
  required field set and the accepted `message_changed` / `message_deleted` subtypes; measured entry
  costs with `json.dumps(..., ensure_ascii=False, separators=(",",":"))` as a strict lower bound and
  with the default `ensure_ascii=True` as the wire form. A 14-test instrument written before the
  repair failed exactly the three page falsifiers (4,730 / 9,594 / 66,220) and passed all nine
  controls, including one proving a full page still admits at least one ceiling-sized frame.
scope:
  - common/agent_dialogue_consultation_contract.py
  - integrations/slack_agent_dialogue/slack_web_api.py
  - any paging or capacity law over an external message API
confidence: verified
---

The bare-payload charge is seductive because it is the only number the producer has in hand. The
number that matters belongs to the consumer, and it is knowable without calling the API at all -
by reading which fields that consumer's parser insists on.
