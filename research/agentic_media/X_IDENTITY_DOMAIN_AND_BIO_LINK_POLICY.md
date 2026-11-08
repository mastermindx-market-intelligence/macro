# X identity chain — domain and bio-link policy

**Status:** planning proposal. Merging this document does not approve a domain choice, bio-link policy,
registration, registry revision or live action. No registration receipt is established here.
**Governing decisions:** the accepted [X Guerrilla masterplan](X_GUERRILLA_NETWORK_MASTERPLAN.md),
especially §§7, 13, 18 and 26. The original authoring reference was `13ac6b49e` on
`feat/xguerrilla-harness`; that historical branch is not a new grant of authority.
**Owner lane:** marketing. **Card:** `t_d1277717` — head of the identity chain.
**Document outcome:** record a proposed host and bio-link policy for the existing domain decision.
An existing host avoids a new registration purchase; it does not establish destination readiness or
approval for this use. The domain decision, incumbent registry/schema owners, DNS P0 #10717 and all
identity, account, browser and activation gates remain open. A non-empty proposed field admits no action.

---

## 1. The spend question, answered first

The card requires this before any "go". §12.5 refuses unapproved purchase inside this programme, and
`config/marketing.yml` carries **ad-spend** budgets only (`ad_center.*`), no registration line. §12.2
further excludes domain from the $350 ceiling ("Browser hardware, operator time, domain, mobile pool …
outside this table"). So:

- **(a) Is there a pre-existing approved line covering registration?** **No.** No approved domain line
  exists anywhere I could find. UNVERIFIED beyond `config/marketing.yml` keyword sweep (`budget`) and
  a docs/research grep for approved-budget language — one hit, an unrelated repository-cutover plan.
- **(b) Therefore:** this document produces candidates and a recommendation only. **Purchase is held
  for the Chairman as a one-line approval.**
- **(c) Existing-host option.** The author identifies the estate's `mastermind-x.com` host and its
  apex → `www` redirect (`app/deploy/Caddyfile`, cited at `config/press.yml:97`). Reusing an owned
  host avoids a new registration charge. That source observation does not approve this destination,
  establish the `/x/` route or clear DNS P0 #10717. **The recommendation is conditional on the
  existing domain decision and incumbent destination, redirect/consent and registry qualification.**

Masterplan §18 item 1 retains two options: choose an approved existing domain/subdomain or authorize
a new registration. This document recommends the first and records the second as an optional purchase
proposal. Neither option is selected or approved by this source merge.

## 2. Line-ref readback (card said provisional)

| Ref | Status | Text |
|---|---|---|
| `:155` | **CONFIRMED verbatim** | "One organisation-controlled email identity and a recovery owner; domain acquisition remains open." |
| `:205` | **CONFIRMED verbatim** | "**No URLs in child posts** … Links remain in the approved bio." |
| `:278` | **CONFIRMED, but not a chain step** | §12.7(5) "Proxy inventory and credential custody were unqualified." The chain itself is §7(1)–(7) at `:155–161`; the pinned-proxy step is §8 (`:174`). Cite `:155–161` for the chain, not `:278`. |

## 3. Proposed fields for the incumbent registry owner

This YAML is illustrative proposal data; no registry was edited. Masterplan §18 item 2 concerns
affiliate parents and does not grant registry-write authority. Engineering retains the existing
identity schema, lifecycle validator and binding contract; marketing proposes these values:

```yaml
domain: https://www.mastermind-x.com/x            # proposed base, pending the domain decision
recovery_owner: marketing                         # proposed accountability; actual custody unresolved
bio_link_policy: v1                               # §4 proposal, not an admitted registry value
posts_carry_urls: false                           # existing programme rule; enforcement is separately qualified
```

## 4. Proposed bio-link policy v1

Voice/positioning first, purchase second — the bio is the only URL surface in the whole network, so
one destination shape decides what every child can say.

- **BL-1 — One link, one host.** The bio holds exactly one URL and its host is `www.mastermind-x.com`.
  Apexis excluded: the apex 301s, so it burns a hop and doubles the host strings a validator must know.
- **BL-2 — The path is the attribution key.** Destination is `https://www.mastermind-x.com/x/<child-id>`.
  `<child-id>` is the registry's immutable account id, not the handle (handles get renamed; refs must not
  rot). No `?utm_*`: the path segment carries attribution, matching the bio rather than a campaign. One
  ref layer only — a child linking to a parent's ref page is still one hop.
- **BL-3 — No shorteners, no third-party hosts.** `t.co` / `bit.ly` / `buff.ly` all resolve to a host the
  estate does not own; with the child posts carrying no URLs (BL-9) the bio is the single point of failure
  and must be org-controlled. §13 already routes the ref through the existing redirect/consent owner —
  that owner, not a shortener, does the hop-counting.
- **BL-4 — Nothing else linkable in the profile.** No URL in the display name, no second URL in the bio
  text, including in the disclosure line.
- **BL-5 — Disclosure is mandatory and adjacent.** The bio states organisation control in the parent's
  voice (start "An editorial account of Mastermind-X"), per §7(4) and §20.2. Wording is the Chairman's;
  the *presence* of disclosure is a hard rule, and it sits before the link, never after.
- **BL-6 — Bio links do not rotate.** A destination is chosen once at provisioning and changes only by a
  registry edit with a reason. Swapping hosts is what lesson 9 forbids mid-flight.
- **BL-7 — Lapse behaviour is a 301, never a bio edit.** If a destination path must move, the old path
  301s to the new one; no child re-writes its bio in flight.
- **BL-8 — Persona voice stays in the bio text, not the URL.** No persona-specific subdomain per child:
  forty subdomains means forty certificate names and forty renewal surfaces for zero attribution the
  path does not already give.
- **BL-9 — The no-URLs rule is absolute.** Posts and replies carry no URLs at all (§10 `:205`, §11 reply
  desk), enforced deterministically by the engineer-owned validator (§26.4). No "just this once" reply
  link: the moment a URL is permitted in a reply, every child is one guideline away from the house
  account's habit and the validator's determinism collapses into advisory.
- **BL-10 — Enforcement shape for the engineer.** Bio validator: scheme `https` only; host allowlist
  exactly `www.mastermind-x.com`; single link. The candidate path format `^/x/[a-z0-9]{4,32}$`
  needs incumbent identity/schema qualification: it excludes current masterplan examples such as
  `c-beat-001` and `c-desk-001` and must not silently rename or invalidate those identifiers.
  Query strings, trailing slash variants, uppercase and shortener hosts are proposed exclusions,
  subject to that owner review. Post/reply validation retains the existing no-URL rule (§26.4).

**Why this host and not a new one.** The live link validator classifies hosts by name and only treats
`www.mastermind-x.com` and `mastermind-x.com` as internal (`engine/press/validators.py:1339`); everything
else is "genuinely external" and **skipped unchecked** (`:1340`). A brand-new registration would sail
through as external and be enforced by nothing until the bio validator lands. Path prefixes live at
`config/press.yml:225-229` (`/research/`, `/blog/`, `/stocks/`). A prospective `/x/` enrollment is
one identified engineering integration point, not proof that all validator, redirect/consent and
destination work is complete. This proposal authorizes no configuration or DNS change.

## 5. Author-reported candidates, pricing and availability (2026-11-08T04:52–04:58Z)

The original author reports registry RDAP (`rdap.verisign.com`, `rdap.identitydigital.services`,
`pubapi.registry.google`), WHOIS where RDAP was absent, and Cloudflare/Porkbun price lookups.
**VERIFIED** in the retained table means the original author's reported observation at that time;
these claims were not independently reverified in this source correction. Quotes and availability
are historical, may change and require fresh evidence for any authorized purchase. No purchase or
reservation receipt is established here.

| Domain | Live status | Cloudflare reg / renew | Porkbun reg / renew | Note |
|---|---|---|---|---|
| `mastermindx.com` | **TAKEN** 2017-10-30, exp 2027-10-30, GoDaddy | — | — | Close near-miss of the house name; handle `@mastermindx` is also a private person |
| `mastermind-x.net` | **AVAILABLE** (RDAP 404, WHOIS no-match 04:53:43Z) | **$11.86 / $11.86** VERIFIED | **$12.52 / $12.52** VERIFIED | Flat renewals, brand-safe, `.net` reads infrastructural |
| `mastermindx.io` | **TAKEN** 2026-04-20, exp 2027-04-20, Cloudflare, speculative registrant | — | — | Young holding; will not drop soon |
| `guerrilla-x.com` | **TAKEN** 2021-09-16, exp 2027-09-16, GoDaddy | — | — | Also a holding |
| `xguerrilla.com` | **AVAILABLE** (RDAP 404, WHOIS no-match 04:53:28Z) | **$11.17 / $11.17** VERIFIED | **$11.81 / $11.81** VERIFIED | Matches the programme's own name; handle `@xguerrilla` squatted since 2010 (irrelevant to domain) |
| `mastermindx.co` | **AVAILABLE** (WHOIS `DOMAIN NOT FOUND` 04:53:48Z) | **$30.00 / $30.00** VERIFIED | **$15.76 / $31.20** VERIFIED | Colombia ccTLD; year-one discount hides a $31 renewal |
| `mastermindx.dev` | **AVAILABLE** (RDAP 404) | **$8.20 (list $12.20) / renew $12.20** VERIFIED | **$8.75 / $12.87** VERIFIED | Cheapest; `.dev` is HSTS-preloaded (cert mandatory) and reads "developer" |

The author described matching handles as **likely-free, not reserved**; this is not confirmed account
availability or permission to sign up. Section 8 records lookup endpoints and source references,
not attached raw registrar quotes, a child research return or a transaction receipt.

### Registrar and recovery plan (applies to either branch)

- **Registrar: Cloudflare Registrar**, if a registration is approved. At-cost pricing with no renewal
  markup (all seven quotes are at-cost; Porkbun's .co/.dev renewals jump), free WHOIS redaction by
  default, free DNS, free Email Routing for the §7 email identity. Trade-offs recorded honestly: it
  refuses foreign nameservers, the registrar API is beta, and a zone admin/super-admin can pull an auth
  code — so the account, not the zone, is the security boundary. Transfers out are self-service.
- **Registrant:** organisation, not person, with redaction on. Ownership proof is the order receipt held
  in the decision record; redaction plus org registrant is only safe because the receipt exists.
- **No circular recovery.** The registrar account's recovery mailbox must **not** live on the domain
  being registered — a lapse takes the recovery address with it. It uses an existing estate mailbox.
- **Custody:** registrar login in the approved secret store, TOTP (not SMS; §7(3)), registrar lock on,
  auto-renew on, expiry watch at T-60/T-30/T-7.
- **`recovery_owner`:** marketing, named for accountability; the human login holder is named in the
  Chairman's approval line. Who holds the estate's existing registrar account today is UNVERIFIED here
  and the chain requires it be org-controlled.
- **Term:** five years initial on any approved registration, to put the first renewal past the pilot
  horizon.

## 6. Recommendation

1. **Propose the owned-host option** `https://www.mastermind-x.com/x/<child-id>` for the existing
   domain decision. It avoids a registration charge; approval for this use, DNS P0 resolution,
   destination readiness and incumbent registry/redirect/consent qualification remain separate.
   Prospective `/x/` enrollment belongs to engineering and is not authorized by this document.
2. **Ask the Chairman for one line, optionally: approve `xguerrilla.com` at Cloudflare, 5-year term,
   ≈$56 one-time, $11.17/yr thereafter, org registrant, privacy on.** If approved it is a vanity alias
   that 301s to the canonical `www` path — never the canonical, and only if a persona-family surface
   separate from the house brand is wanted. `mastermind-x.net` ($11.86 flat) is the brand-safe runner-up
   if the Chairman dislikes the "guerrilla" framing; `mastermindx.dev` is cheapest but mis-signals the
   beat. `mastermindx.co` is skipped: 2× renewal for a ccTLD with broken RDAP.
3. **Propose v1 in §4 under either domain option.** It remains subject to the existing identity,
   schema and destination owners and the open decisions above. An optional alias purchase does not
   establish acceptance of BL-1…BL-10 or permission to write registry data.

## 7. Not settled here

Child handle naming (identity card), disclosure wording (Chairman's voice), the redirect/consent owner's
implementation of `/x/`, and confirmation of the estate registrar account holder. These unresolved
items can affect selection or use of the proposed destination. Avoiding a registration charge does
not clear them, DNS P0 #10717, identity admission or any programme/activation gate.

## 8. Evidence

- Prices: `https://www.cloudflare.com/domains/search?q=<domain>` (rendered) and
  `https://api.porkbun.com/api/json/v3/pricing/get` (POST, TLD-level), both read 2026-11-08T04:52–04:58Z.
  The author reports Namecheap returned403 and was not used; no retry is requested here.
  The table's price and registry-status labels remain author-reported historical observations,
  distinct from the speculative handle-status claim. No fresh price, ownership or availability proof
  is supplied by this source correction.
- Validator behaviour: `engine/press/validators.py:1318-1340`, `:1413`, `:1444-1467`; prefix config
  `config/press.yml:225-229`; apex-301 rationale `config/press.yml:97`. Author-reported local validator readback:
  `https://www.mastermind-x.com/x/abc123` currently returns `ok=False, offenders=[…]` — proof `/x/` needs
  the config entry, not evidence the approach fails.
- Estate host facts: `config/press.yml:84,93,99` (`blog.mastermind-x.com`, `mastermind-x.com`,
  `https://www.mastermind-x.com`).
