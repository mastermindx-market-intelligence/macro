# Catalyst partner private preview — visual evidence

**Synthetic fixture only. Draft/HOLD.** These screenshots document the isolated
`templates/catalyst_partner.html.j2` presentation, not an installed public scan,
an approved publisher partnership or an issuer event. No deployment, outreach,
email, X activation or external publication occurred. Evidence generated from
the Session 04 source branch at
`d46fa53accce37cbe6a637351025c2fa9016a88b` as the content-addressed source code revision, before updating the three
committed example snapshots and renewing this evidence corpus. The 24 images
are genuine rerun captures of those updated example bytes.

This folder reuses the existing canonical
`mastermind.page_evidence_receipt.v1` and `mastermind.p0_evidence.v2`
formats. `EVIDENCE.yml` owns only the new partner template and points to the
actual `manifest.json` from `scripts/capture_page_evidence.py`.
The standard generator captured **24 of 24** real Chromium screenshots:
desktop 1440 and mobile 390; English and Chinese browser locale; dark and
light themes; at rest, CTA hover and CTA keyboard focus. Screenshot hashes,
byte lengths, actual locale/theme, sizes and forced interaction outcomes are
validated against the manifest; its original `smells.json` is retained.

**Presentation limits:** all three demo profiles, tickers and events are
invented. The language/state observer genuinely applies Chinese browser locale,
but the underlying editorial claims are **still English**; these captures
prove browser-locale state, not finished Chinese copy translation. The light
palette comes unchanged from the canonical `templates/theme.css` light override;
the review-only HTML is standalone. The source URL and deep link use non-live
`.invalid` fixture hosts. No premium/private market data was used.

Reproduce on an isolated checkout with `jinja2`, `PyYAML`, Playwright and
its Chromium browser available:

```sh
python3 scripts/build_catalyst_partner_pack.py --demo --out /tmp/mmx-partner-site
python3 scripts/capture_page_evidence.py \
  --registry /tmp/mmx-nonexistent-capture-registry.json \
  --site-dir /tmp/mmx-partner-site \
  --routes /demo-chip-community/index.html \
  --viewports desktop,mobile --locales en,zh --themes dark,light \
  --force-state 'cta-hover:hover(.read .cta)' \
  --force-state 'cta-focus:focus(.read .cta)' \
  --output-dir mockups/evidence/catalyst-partner-private-20261009/evidence \
  --manifest mockups/evidence/catalyst-partner-private-20261009/manifest.json \
  --smells mockups/evidence/catalyst-partner-private-20261009/smells.json \
  --delay-ms 0 --settle-ms 60 --timeout-s 18
```

The filenames and digests are from this documented capture, not promised
bitwise-reproducible across browser versions or different hosts. The manifest
contains the actual tool and browser observation provenance; the receipt carries
no alternative lifecycle, data-rights or publication authority.

**Next acceptance:** operator visual review, true Chinese copy translation if
Chinese-language distribution is intended, admitted public-event/rights producer,
Session 00 public HTML route and attribution proof, and Session 06 re-review.

## Refresh after evidence and attribution regression repair

This manifest supersedes the preceding historical 24-shot capture at an older
pack identity. The verified sources and partner fixtures remain synthetic and
unapproved; only the content-addressed `pack_id`/CTA and related evidence
receipts changed. All 24 replacement screenshots were produced through the
same canonical Chromium capture tool. They replace, rather than masquerade as,
the earlier source-state screenshots. Re-run the source checker against this
manifest at the eventual exact PR head before making any CI-green claim.
