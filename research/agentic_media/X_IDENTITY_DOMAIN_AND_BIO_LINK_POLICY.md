# X identity chain — domain and bio-link policy

**Status:** draft for the Chairman's one-line approval. No registration has been made.
**Authority:** `research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md` @ `13ac6b49e`
(branch `feat/xguerrilla-harness`, HEAD checked out at that commit on 2026-11-07).
**Owner lane:** marketing. **Card:** `t_d1277717` — head of the identity chain.
**Terminal action of this document:** settles `bio_link_policy`; leaves `domain` in one of two named
states (existing host = usable today; new registration = awaiting approval). Nothing downstream may
provision an email identity, TOTP seed, proxy, account or browser slot until `domain` is non-empty.

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
- **(c) But the chain is not blocked on the approval.** The estate already owns `mastermind-x.com` and
  serves it behind an edge that 301s apex → `www` (`app/deploy/Caddyfile`, cited at `config/press.yml:97`).
  A path ref on the owned host costs **$0** and needs no registration. So `domain` can be filled today
  with an existing, approved, already-paid-for host, and the optional registration becomes an
  improvement rather than a prerequisite. **This is the recommendation.**

§18.1 states exactly these two branches by design ("choose an approved existing domain/subdomain or
authorize a new registration; no purchase has been made by this PR"). This document takes branch one
and parks branch two behind the Chairman.

## 2. Line-ref readback (card said provisional)

| Ref | Status | Text |
|---|---|---|
| `:155` | **CONFIRMED verbatim** | "One organisation-controlled email identity and a recovery owner; domain acquisition remains open." |
| `:205` | **CONFIRMED verbatim** | "**No URLs in child posts** … Links remain in the approved bio." |
| `:278` | **CONFIRMED, but not a chain step** | §12.7(5) "Proxy inventory and credential custody were unqualified." The chain itself is §7(1)–(7) at `:155–161`; the pinned-proxy step is §8 (`:174`). Cite `:155–161` for the chain, not `:278`. |

## 3. Fields this settles

Lands as registry data, per §18.2, not as prose:

```yaml
domain: https://www.mastermind-x.com/x            # base; child ref appends /<child-id>
recovery_owner: marketing                         # accountable; login holder named in the approval
bio_link_policy: v1                               # §4 below, machine-checkable
posts_carry_urls: false                           # validator-enforced, no per-account exceptions
```

## 4. Bio-link policy v1

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
  exactly `www.mastermind-x.com`; single link; path must match `^/x/[a-z0-9]{4,32}$`; reject query
  strings, trailing slash variants, uppercase, and any redirecting shortener host. Post validator: the
  existing no-URL rule (§26.4), extended to replies.

**Why this host and not a new one.** The live link validator classifies hosts by name and only treats
`www.mastermind-x.com` and `mastermind-x.com` as internal (`engine/press/validators.py:1339`); everything
else is "genuinely external" and **skipped unchecked** (`:1340`). A brand-new registration would sail
through as external and be enforced by nothing until the bio validator lands. Path prefixes live at
`config/press.yml:225-229` (`/research/`, `/blog/`, `/stocks/`) — `/x/` must be added there, which is the
only code change this policy requires and is engineer-owned, not marketing's.

## 5. Candidates, pricing and availability (checked 2026-11-08T04:52–04:58Z)

Method: registry RDAP first (`rdap.verisign.com`, `rdap.identitydigital.services`,
`pubapi.registry.google`), registry WHOIS where RDAP was absent, prices read live from Cloudflare
Registrar search results and Porkbun's public pricing API. **VERIFIED** = read this session, URL known.
Nothing carted.

| Domain | Live status | Cloudflare reg / renew | Porkbun reg / renew | Note |
|---|---|---|---|---|
| `mastermindx.com` | **TAKEN** 2017-10-30, exp 2027-10-30, GoDaddy | — | — | Close near-miss of the house name; handle `@mastermindx` is also a private person |
| `mastermind-x.net` | **AVAILABLE** (RDAP 404, WHOIS no-match 04:53:43Z) | **$11.86 / $11.86** VERIFIED | **$12.52 / $12.52** VERIFIED | Flat renewals, brand-safe, `.net` reads infrastructural |
| `mastermindx.io` | **TAKEN** 2026-04-20, exp 2027-04-20, Cloudflare, speculative registrant | — | — | Young holding; will not drop soon |
| `guerrilla-x.com` | **TAKEN** 2021-09-16, exp 2027-09-16, GoDaddy | — | — | Also a holding |
| `xguerrilla.com` | **AVAILABLE** (RDAP 404, WHOIS no-match 04:53:28Z) | **$11.17 / $11.17** VERIFIED | **$11.81 / $11.81** VERIFIED | Matches the programme's own name; handle `@xguerrilla` squatted since 2010 (irrelevant to domain) |
| `mastermindx.co` | **AVAILABLE** (WHOIS `DOMAIN NOT FOUND` 04:53:48Z) | **$30.00 / $30.00** VERIFIED | **$15.76 / $31.20** VERIFIED | Colombia ccTLD; year-one discount hides a $31 renewal |
| `mastermindx.dev` | **AVAILABLE** (RDAP 404) | **$8.20 (list $12.20) / renew $12.20** VERIFIED | **$8.75 / $12.87** VERIFIED | Cheapest; `.dev` is HSTS-preloaded (cert mandatory) and reads "developer" |

Handle availability for the matching name is **likely-free, not reserved** — an X 404 is not a hold;
re-confirm at signup. Full evidence URLs and registrar quotes: child research log, reproduced in §8.

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

1. **Settle `domain` today at $0** on the owned host: `https://www.mastermind-x.com/x/<child-id>`. No
   registration, no approval, chain unblocked. Add `/x/` to `public_link_prefixes` (engineer).
2. **Ask the Chairman for one line, optionally: approve `xguerrilla.com` at Cloudflare, 5-year term,
   ≈$56 one-time, $11.17/yr thereafter, org registrant, privacy on.** If approved it is a vanity alias
   that 301s to the canonical `www` path — never the canonical, and only if a persona-family surface
   separate from the house brand is wanted. `mastermind-x.net` ($11.86 flat) is the brand-safe runner-up
   if the Chairman dislikes the "guerrilla" framing; `mastermindx.dev` is cheapest but mis-signals the
   beat. `mastermindx.co` is skipped: 2× renewal for a ccTLD with broken RDAP.
3. **`bio_link_policy` is v1 as written in §4 and does not depend on step 2.** Both branches land the
   same BL-1…BL-10; step 2 only decides whether a second host ever exists to alias.

## 7. Not settled here

Child handle naming (identity card), disclosure wording (Chairman's voice), the redirect/consent owner's
implementation of `/x/`, and confirmation of the estate registrar account holder. None of these are
purchases and none block step 1.

## 8. Evidence

- Prices: `https://www.cloudflare.com/domains/search?q=<domain>` (rendered) and
  `https://api.porkbun.com/api/json/v3/pricing/get` (POST, TLD-level), both read 2026-11-08T04:52–04:58Z.
  Namecheap search 403s to curl and headless; not used. All figures above are VERIFIED by those reads;
  the *registry* status is VERIFIED by RDAP/WHOIS, distinct from handle status which is likely-free only.
- Validator behaviour: `engine/press/validators.py:1318-1340`, `:1413`, `:1444-1467`; prefix config
  `config/press.yml:225-229`; apex-301 rationale `config/press.yml:97`. Executed readback:
  `https://www.mastermind-x.com/x/abc123` currently returns `ok=False, offenders=[…]` — proof `/x/` needs
  the config entry, not evidence the approach fails.
- Estate host facts: `config/press.yml:84,93,99` (`blog.mastermind-x.com`, `mastermind-x.com`,
  `https://www.mastermind-x.com`).
