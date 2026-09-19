# B-F07-3 smells — 8 cells captured, 0 smells

## What was captured

8 cells of the B-F07-3 event-to-assumption bridge line, populated state
(Tender Offers → "usually lifts the multiple people pay"):

- desktop 1440 / mobile 390
- dark + light
- EN + ZH

The crops depict the `#va-event-bridge` element only — Tier-2 receipt,
one plain-word line under the controls.

## Hosts

Three hosts in `mockups/evidence/b-f07-3-event-bridge/hosts/`, regenerated from the live template at code head `3923b693d367`:

1. `valuation-event-bridge-tender-offer.html` — bridge populated with
   `engine/valuation_event_bridge.bridge("Tender Offers")`. EN: "Latest
   filing on file (Tender Offers) usually lifts the multiple people pay."
   ZH: "最新备案（要约收购）通常推升市盈率倍数。"
2. `valuation-event-bridge-restructuring.html` — same shape with
   `bridge("Restructuring")`. Used for non-default event-class sanity;
   not separately screenshotted (8 cells are reserved for the
   Tender-Offer receipt).
3. `valuation-event-bridge-null.html` — `latest_event_bridge = None`
   (the typed-null render path). Verified by tests, not screenshotted.

The event line is 11px while the FY footnote is 11.5px. The event direction uses the production muted type, not a bold direction word.

## Smells

None. The host pages render without console errors and the crops depict
the bridge line in all 8 cells. The bilingual event sentences use one
`t()` twin per language.
