# Rights classification request: SEC EDGAR 8-K Item 2.02 documents as the Catalyst producer consumes them

Status: REQUEST ONLY. This grants nothing, proposes no grant YAML and edits no registry. A GMI/source steward decides it.
Facts reviewed at integration base `55dc7cab50c95d74406a61beb1d8aa2ae179a8a5` (lane/mx-cat-a1-base). Also read: the #7870 candidate registry at `225ede0a90747899cb764d558549e3bc61433ffa` and the partner factory at `6b4e3b8846cabce47b7501ce66ae507f84164500`.
Fact lane: `mx-cat-rights-rec-r2b` (host ubuntu2, glm-5.3, read-only review), sentinel `RIGHTS-REC-r2: PASS-WITH-GAPS 55dc7cab50c95d74406a61beb1d8aa2ae179a8a5`. The orchestrator re-verified the key citations against the commits above in its own judge tree.
Path aliases used below:
- `p` = engine/marketing/catalyst_packets.py
- `adm` = engine/marketing/catalyst_admission.py
- `sc` = engine/marketing/catalyst_scan.py
- `w` = engine/marketing/edgar_earnings_wire.py
- `ci` = app/catalyst_integration.py
- `r` = engine/theme_graph/rights.py
- `t` = config/theme_sources.yml
- `g` = config/growth_events.yml

## The decision requested

Is display of a fact card derived from a specific SEC EDGAR 8-K Item 2.02 filing permitted on the anonymous public Catalyst surface? The scope is the item (i) document, under the conditions below.
- **Channel:** web display only. This is the `/api/catalyst` human HTML page and its `/api/catalyst/scan` JSON. It includes link, title and stated figures, plus a link-only outbound partner pack.
- **Email:** none. Opt-in email is a separate Session-02 consent seam.
- **Rehost:** none. Bytes are never stored or re-served and nothing is excerpted. The pack is link-only.
- **Attribution:** "SEC Form 8-K Item 2.02" plus the sec.gov /Archives/ link.

Please answer each of these:
- **D1.** Is the grant at family level (`sec_edgar`), filing level (`sec:<cik10d>:<accession>`) or exhibit level?
- **D2.** Are issuer-authored exhibits such as EX-99.1 covered, or only SEC-generated index pages? The candidate row's own notes say issuer exhibits are NOT section 105 US-Government works.
- **D3.** Third-party documents attached under the same /Archives/ prefix are admitted by the URL gate (gap G5 in the candidate notes). Are they excluded?
- **D4.** What are the retention and expiry rules, which `PublicSourceGrant.expires_at_utc` would encode?
- **D5.** Which owner mints the runtime `PublicSourceGrant` (`owner_ref`), and under what receipt id scheme?

## (i) Exact document identity the producer binds

- **Source.** Event `source == "edgar_8k_202"` (p:24, enforced at adm:103, producer at w:103). The public source_id is `"sec:"+filing_key` (p:210).
- **filing_key.** Matches `^\d{10}:\d{10}-\d{2}-\d{6}$` (p:26, matched at p:208). The producer builds it as `f"{cik:010d}:{accession}"` (w:753-755).
- **event_id.** Formed as `"sec-earnings-"+sha256(filing_key)[:24]` (p:209).
- **Issuer binding.** CIK is a positive int; `issuer_id == f"cik:{cik:010d}"`; filing_key starts with the CIK prefix (p:240-244). The ticker goes through `safe_ticker` (p:225-230). Universe rows need `supported: True` (adm:87-94).
- **Exhibit selection is heuristic.** It uses the hint regex `ex.{0,4}99|99.{0,4}1|earn|press|release` over the filing index (w:996-1016), with base `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}` (w:111). The packet title is fixed: "SEC Form 8-K Item 2.02" (p:298).
- **URL gate.** https only; host in {sec.gov, www.sec.gov}; path starts with `/Archives/`; port 443 or none; no credentials, IP literal or whitespace; at most 2048 chars (p:112-141, applied at p:325).
- **Byte binding today is NONE.** Nothing in p/adm/sc/w uses a document sha256, length or fetched_at. The intended `VerifiedDocumentObservation` contract (document_sha256, receipt_id, owner_ref, first_verified/checked_at, snapshot version, verified figures) exists only in tests/test_catalyst_admission.py:63-80. The class is defined nowhere at this commit.
- **Fixtures are synthetic.** The issuer name is "Synthetic issuer (NOT live)" and the accession is `0000078003-26-000094` (test_catalyst_admission.py:23-33). The fixture URL is the filing INDEX page, not an exhibit (test_catalyst_packet_public.py:16). The receipts `fixture-rights:<sid>` (packet_public:46) and `fixture-receipt:` (test_catalyst_scan.py:30) are test-only. The CIK 78003/PFE carrier identifiers are real, the documents are not.

## (ii) Admission path and TODAY'S NEGATIVE BEHAVIOUR (no grant)

The chain is route -> `scan_with_reader` (ci:391) -> `scan_tickers` (sc:261-268) -> `read_qualified_event_context` (sc:249-258) -> adm.

The flags `CATALYST_PUBLIC_ENABLED`, `CATALYST_OPTIN_ENABLED` and `CATALYST_UX_ENABLED` all default to DISABLED: `_enabled` requires env `== "1"` (ci:114-117). Their use sites are:
- `CATALYST_PUBLIC_ENABLED`: ci:430, 441, 481, 587, 616, 650, 657
- `CATALYST_OPTIN_ENABLED`: ci:442, plus app/catalyst_optin.py:70-71
- `CATALYST_UX_ENABLED`: ci:617, 659

Outcomes today:

| Condition | `/api/catalyst/scan` (machine JSON) | `/api/catalyst` (human HTML) |
|---|---|---|
| Flags off (default) | HTTP 503 "Catalyst scan is not publicly enabled" (ci:119-121) | HTTP 503 (ci:650/657) |
| Flags on, at this commit | admission import fails, so 503 "Qualified event source unavailable" (ci:406-410) | the same 503, rendered as an error-only HTML page (ci:637-645) |
| Flags on, chain healthy, no grant | `t` has no `sec_edgar` row, so `RightsRefusal` (r:135-139) -> empty (adm:117-120) -> `UNAVAILABLE` (sc:239) -> 503 (ci:256-257, 406-410) | the same, as an error-only HTML page at 503 |
| Grant present but invalid | `_allowed` denies unless audience == `public_anonymous`, all three display flags are True, and `effective <= now < expires` (p:144-162); a resolver exception counts as a denial | the same |

Why admission fails at this commit:
- adm:16-18 imports `VerifiedDocumentObservation`, which p does not define, so an ImportError.
- adm:108-111 passes `document_observation=` to `build_event_packet`, which p:182-190 does not accept, so a TypeError. This is a second, independent break.

Both breaks fail closed. Repairing them belongs to the A1 integration lane, not to this request.

**Attestation boundary.** DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023 names only:
- the Research Factory Yahoo/yfinance route
- Massive/Polygon
- Tiingo
- ThetaData options

It does NOT name SEC EDGAR, so it is not a basis for this grant.

## (iii) SHAPE THE RESOLVER READS - NOT A GRANT

**Family registry (`t`, read by `r`).** Only two fields are read:
- `rights_class`, with enum `internal_only|derived_display_ok|direct_display_ok|unresolved` (r:40-41, 140-145). Emission is permitted for the two display classes only (r:45).
- `auth_class`, with enum `house|keyless_public|receipted_scrape|entitled|licensed` (r:148-151; t:12).

`source_route`, `review` and `notes` are documentation that the gate does not read.

**Runtime grant (`PublicSourceGrant`, p:51-67).** It has exactly nine fields, validated at p:144-162:

| Field | Accepted value |
|---|---|
| `source_id` | equals the packet source id |
| `receipt_id` | 1-128 chars |
| `owner_ref` | non-empty |
| `audience` | `"public_anonymous"` |
| `effective_at_utc` | tz-aware |
| `expires_at_utc` | tz-aware |
| `display_link` | must be True |
| `display_title` | must be True |
| `display_facts` | must be True |

**Not expressible today:**
- channel or surface scope ("web display only");
- a no-email flag;
- a rehost or redistribution flag (redistribution is derived only at family level from `auth_class == "house"`, r:197-198);
- per-issuer scope;
- an exhibit-level pin;
- attribution text.

**The #7870 candidate row at 225ede0a (t:43-48).** Its key values are verbatim:
- `sec_edgar: rights_class: direct_display_ok`
- `auth_class: keyless_public`
- `source_route`: fetched under the SEC fair-access policy (declared User-Agent, at most 10 req/s)
- `review`: date 2026-09-24, by gmi-semiconductor-b, citing the SEC Website Dissemination policy and #7870 issuecomments 5809660585/5809192409
- `notes`: issuer exhibits are not section 105 works; house display is "receipted excerpt + attribution"; third-party attachments share the /Archives/ prefix (G5); retention is UNSTATED.

This is a FAMILY/source-name row. It is not an issuer-exhibit display grant, and it does not mint a runtime `PublicSourceGrant`. Its contemplated "receipted excerpt" display is broader than the link-and-facts, no-excerpt display requested here.

**Main today has ZERO `sec_edgar` entries.** At 55dc7cab, `git grep -c sec_edgar -- config/` returns no match. `t` holds only `mastermind_curated`, `finviz_themes` and `ths_concepts`, plus commented `sp_kensho`/`theia` (t:22-52).

## (iv) Attribution keys (opaque; no identity)

- **Scan response.** Opaque `scan_receipt` (app/catalyst_scan_authority.py:109-110), per-source `rights_receipt_id` (sc:133-135) and `event_id`.
- **Client.** It reads only `utm_source/medium/campaign/content`, each matching `^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$`, as untrusted metadata. It forwards them as `first_touch` on opt-in (app/catalyst_scan_ui.js:18-27, 207-209).
- **Partner pack CTA (6b4e3b88).** Exactly six params: `utm_source=partner`, `utm_medium=partner-<slug>`, `utm_campaign=catalyst_scan`, `utm_content=<pack_id>`, `event_id`, `tickers` (catalyst_partner_pack.py:420-435; links.py:56-82).
- **`session.start`.** Its properties are source, campaign, landing_surface, referrer_host and is_first_ever (g:119-130). No emitter in this repo maps utm to it.
- **Website/D07-owned joins.** The signup, billing and auth plane (D07:14); the conversion join, gated on analytics access (D07:23); and the nightly `utm_content == post_id` join to an opaque `user_ref` (D07:25). The full map is in D1_READINESS_NOTE.md.

## (v) UNKNOWN

- The current SEC EDGAR terms-of-use and fair-access status, and whether they support the candidate row's dissemination-policy basis.
- The named GMI/source steward for this decision.
- Whether the grant is meant to be exhibit-level, filing-level or family-level.
- Whether the tests' `VerifiedDocumentObservation`/`document_observation` contract is the accepted Stage-B shape.
- Whether the #7870 candidate row will land in main's `t`.
- Which real issuer and exhibit a first production grant would bind.
- Where `session.start` source and campaign are populated from utm (outside this repo's app/).

## Addendum (2026-10-31T09:52:05Z): grant shape on the composed head (PR #8700 head `ddbb582998f914d453cbfd37d25b6817f77d0636`)

The seat ruled that the composed head carries PR #8700 head ddbb5829's producer files byte-exact. That changes section (iii) "Runtime grant" as follows. Line references are to `p` at ddbb5829.
- **`PublicSourceGrant` has eleven fields.** The nine above are still required. Two defaulted fields are new (p:78-82):
  - `document_url: str = ""`: "EXACT owner-approved document URL, not a filing-level allow-all".
  - `document_sha256: str = ""`: the exact retained document bytes, used when a verified source-read contract exists.
- **`_allowed` refuses a grant in four cases (p:400-410):**
  - its `document_url` is empty;
  - its `document_url` is not a string;
  - its `document_url` differs from the packet source's URL;
  - the caller passes a non-empty `document_sha256` and the grant's `document_sha256` differs.
- **The call site (p:677-679) passes `document_sha256` only for the primary source, and only when a verified document observation exists.** Otherwise it passes "".
- **What happens on refusal:** the source is blocked. When the primary source is blocked, the packet is `BLOCKED_PUBLIC` with `primary_source_public_rights_unavailable`.
- **Consequence for D1:** the producer can consume only a grant bound to one exact document URL, plus exact bytes when observed. A family-level or filing-level decision therefore still needs the minting owner (D5) to issue one runtime grant per displayed document. Please answer D1 and D5 with that in mind:
  - Is a per-document grant minted from a family/filing decision acceptable?
  - Or must each document be reviewed?
- **This addendum grants nothing, proposes no grant YAML and edits no registry.** It also does not change items (i), (ii), (iv) or (v).

## Addendum 2 (2026-10-31T13:3xZ, seat ce215fa3): statements superseded at the committed head

This record's body was pinned to 55dc7cab, but it is committed on a head where `p`
(`engine/marketing/catalyst_packets.py`) carries PR #8700 head ddbb5829 (blob 5b9e2a2a became
428bda74). An independent read-only review (PR #10257, 2026-10-31) found the following body
statements false at head. They are superseded here; the addendum above remains in force.

- **(i) "Byte binding today is NONE" is superseded.** At head, `VerifiedDocumentObservation` is
  defined at p:101 (fields include `document_sha256`), and the `_allowed` call site passes
  `document_sha256` for the primary source when a verified observation exists (p:365, p:384, p:677).
  The binding is as the first addendum describes: exact `document_url`, plus exact bytes when observed.
- **(ii) The row "Flags on: admission import fails" no longer describes head.** `adm` imports
  `VerifiedDocumentObservation`, which `p` now defines; the import resolves. The remaining
  negative behaviour with no grant is unchanged: the resolver returns no grant, the primary source
  is blocked, and the packet is `BLOCKED_PUBLIC` with `primary_source_public_rights_unavailable`.
- **Stale line references.** p:24 (the source constant) is now p:26; the grant and its validation
  at p:51-67 / p:144-162 are now p:69-82 / p:400-412.
- **The config grep claim is narrowed.** At head, `git grep -l sec_edgar -- config/` matches
  `config/capital_structure_*.json` and `config/fundamental_forensics/*` (unrelated packs, not the
  family registry). The claim that matters is unchanged and still true: `config/theme_sources.yml`
  has zero `sec_edgar` rows.

Decisions D1–D5 are unchanged. This addendum grants nothing, proposes no grant YAML and edits no
registry.
