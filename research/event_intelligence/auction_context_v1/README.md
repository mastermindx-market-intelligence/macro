# Auction context: bounded acceptance evidence

This is **local component proof**, not deployment or authenticated production
acceptance. Four natural coupon/FRN auction records were projected from the
captured official Treasury API (seven total records, including excluded bills).
The surrounding full-template view-model is synthetic. The full application
correctly redirected an unauthenticated local navigation; no authentication was
bypassed. Browser proof isolates the actual rendered event component and executes
its actual production date selector and renderer.

## Observed capability

No forecast payload is supplied. Selecting September 23 displays both the FRN
reopening and the five-year note, their actual supplied dollar amounts and their
different 11:30/13:00 ET deadlines. Same-date interaction does not duplicate
cards. Selecting September 22 changes the dossier. Native keyboard disclosure
works. Eight screenshots cover 1440/390 widths, dark/light and EN/ZH. No page
errors or horizontal overflow in these cases. Light-mode heading/date ink was
repaired after visual inspection found inherited white-on-white text.

## Source truth discovered during implementation

The live API uses `closingTimeCompetitive`, not the initially assumed field
name. It also represents an FRN as `securityType=Note`, `type=FRN`,
`floatingRate=Yes`. The existing generic calendar had displayed a nominal-note
label/default time. Both the family label and actual deadline now survive.
CUSIP alone is not auction identity: reopenings reuse it. Conflicting rows for
the same auction withhold terms instead of letting the first row win.

## Reproduce

Install the repository test dependencies plus Playwright in an isolated developer
environment. Use a compatible installed Chromium, then run:

```sh
python research/event_intelligence/auction_context_v1/reproduce.py \
  --out /tmp/event-context-proof \
  --browser /absolute/path/to/chromium
```

The script uses the committed public-source capture, not live credentials or
network data. Source receipt and SHA256 are in `source-receipt.json`; image and
candidate source hashes are in `browser-manifest.json`. Do not call a local
screenshot production acceptance or these reference playbooks LLM assessments.

## Still required

Exact-head independent review and hosted CI; fresh production render through its
existing owner; authenticated browser readback; then official results/corrections
and grounded model assessment under the existing RIC/F05/AI consumer contracts.
The old June cached site view-model was inspected and rejected for publication.
It was not used to regenerate or overwrite production pages.
