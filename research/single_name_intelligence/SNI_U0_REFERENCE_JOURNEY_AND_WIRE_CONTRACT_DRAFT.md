# SNI U0: Reference journey and wire contract (DRAFT)

**Status:** DRAFT for the P0 design spec. This document decides nothing beyond `SNI_U0_COMPOSITION_SEAM_DECISION.md`, which is recommendation (b). Every SLO in it is **PROPOSED-NOT-RATIFIED**. Every authority flag is `false`.

**Evidence base**
- Macro `origin/main` @ `c50af4eb0421`. The identity rows were rechecked there, and the masters now hold 3,103 security rows and 1,931 issuer rows. The other macro facts were read at `e44069e306fd`, and the owner paths listed in §2 exist at `c50af4eb0421`.
- Terminal `origin/master` pinned @ `fc76cf495781`. During this lane it moved to `707648d5`, and the diff over every Terminal path cited here is empty.
- The SNI masterplan sections (§5.1, §5.2, §5.3, §5.5, §7, §9) come from the commission's scratch bundle `SNI_Fable_Masterplan_2026-10-11/MASTERPLAN.md`. That masterplan is **not** on `origin/main`.

**Identity rule:** each identity value is either copied verbatim from macro `data/reference/{security,issuer}_master.parquet` or set to the literal `"UNRESOLVED"`. Nothing in this document mints a canonical ID.

---

## 1. Reference journey on existing surfaces

The reference name is **9988.HK**, because it exercises the most of the contract. It has an HK listing, its issuer is unresolved, and it has a bridge-paired US ADR. The 0700.HK and BABA variants follow each step.

| # | Step | Existing surface (Terminal `origin/master` @ `fc76cf495`) | What SNI adds |
|---|---|---|---|
| J1 | The user opens a company and picks the Intelligence tab. | `terminal/components/fin/MegaPane.tsx` mounts `CompanyIntelligencePage` at L288–289 when `page === "intelligence"`. The tab is reflected in `?pane=intelligence` (L211–212), and transcripts in `?tx=` (L223). | Nothing. There is no new nav entry, no new URL family and no new param in P0. |
| J2 | The page loads its two existing readers. | `CompanyIntelligencePage.tsx` fetches company intelligence (L216) and the event workspace (L222). | Nothing. |
| J3a | **9988.HK / 0700.HK:** CI has no fixture or coverage at the pin. | The page renders the `Company intelligence unavailable` EmptyState (L350) or `${ticker} is not covered yet` (L365). | Mount **M3/M4**: `SingleNameReferenceBand placement="fallback"` renders **above** the unchanged EmptyState. |
| J3b | **BABA**, when the event workspace is ok. | The page early-returns `CompanyIntelligenceV2Current` (L311), whose Brief lens is at L715. | Mount **M2**: the band sits in the V2 Brief. |
| J3c | Any v1-covered name. | The v1 Brief lens is at L731. The sibling cards are at L750 and L763. | Mount **M1**: the band sits after `CompanyInstitutionalContextCard`. |
| J4 | The band fetches its own reader. | Sibling idiom: `CompanyInstitutionalContextCard` with `companyInstitutionalContext.ts` (L660/L708). | `GET /api/single-name-intelligence/9988.HK`, which returns `SingleNameIntelligenceResult` (§2). |
| J5 | The identity strip renders. | — | `9988.HK · XHKG · SEC:HK-XHKG-09988 · issuer UNRESOLVED`. The state chip reads `identity-unresolved`, scoped to the issuer and never to the listing. |
| J6 | The main viewport answers the masterplan §9 questions. | Receipt grammar: delta spec §3 (`terminal/docs/COMPANY_INTELLIGENCE_V2_DELTA_SPEC.md` L100). The absence card is §3.5 (L186) and the stance line is §3.6 (L199). | The viewport has five rows: **what changed · current state · what is unusual · next events · what would change the read**. A row with nothing to show renders the absence card with a typed reason and is never blank. |
| J7 | Linked listings. | `engine/hk_adr_bridge.py` (macro) pairs 9988.HK↔BABA as `direct` at L75 and 0700.HK↔KWEB as `proxy` at L85. | The BABA row is labelled "bridge pair (display), not an identity join" with `identity_link: "UNRESOLVED"`. It has a separate clock and currency for each listing, with **no pooled price**. For 0700.HK the KWEB row is labelled "proxy, not a Tencent quote". |
| J8 | Deep lenses open lazily. | The evidence rail is `EvidenceRail` (selection L15, props L26). Its `event: CompanyIntelligenceEvent` is required. | The first payload carries only lens descriptors. A lens body is fetched on open. Non-event evidence on the rail is **gap N4**: the P0 design spec must rule on it. |
| J9 | Language switch. | The `mm.lang` localStorage key is set in the e2e spec (`terminal/e2e/company-intelligence.spec.ts` L837). Copy uses `useLang` + `pick(zh)`. | EN/ZH copy lives in the band's own copy table, following delta spec §7 (L433). Quotations are never translated, per §3.4 (L178). |
| J10 | A correction arrives. | Reference composition `04-corrected` (copy keys `band.corrected.*`). | `corrections[]` is append-only. The correction band renders before the new value, per delta spec §9: "invalidates, does not silently re-render". |
| J11 | The SNI owner or route is down. | Delta spec §9 provider-timeout row. | The band resolves to `unavailable` **inside its own frame**. It never empties or blocks the host page or a sibling card, and a skeleton is never terminal. |
| J12 | Authority fence. | Delta spec §10 (L542): the footer reads "Context for research. Nothing here ranks, sizes or gates a position." | The band adds no second footer. The page footer covers it. The payload's `authority` block is all `false` (§2). |

**Variants**
- **0700.HK:** J5 shows `SEC:HK-XHKG-00700 · issuer UNRESOLVED`. J7 shows only the KWEB proxy, because TCEHY, 80700 and 89988 are absent from the masters. `ISS:US-XNYS-TME` is Tencent **Music** and is never linked.
- **BABA:** J5 shows `SEC:US-XNYS-BABA · ISS:US-XNYS-BABA · CIK 0001577552`, which is `RESOLVED`. J7 shows 9988.HK as a bridge pair with `identity_link: "UNRESOLVED"`, because the masters hold no BABA↔9988 link.

---

## 2. Wire contract: `mastermind.single_name.reference_twin/v1`

The transport is `SingleNameIntelligenceResult`, as fixed in the seam decision:
- success: `{ ok: true; state: SniState; context: SingleNameReferenceTwin }`
- failure: `{ ok: false; state: "error"; error: { code: "invalid_symbol"|"not_found"|"upstream_unavailable"|"invalid_payload"|"rights_blocked"; message: string; retryable: boolean } }`

Symbol normalisation reuses `normalizeCompanyIntelligenceSymbol` (`terminal/lib/companyIntelligence.ts`, `SAFE_SYMBOL` L191).

Column key for the table below:
- **Null?** says whether the field may be `null`.
- **Owner** names the system that originates the value. SNI composes it and never re-derives it.
- **Privacy** classes are defined in §4.

### 2.1 Envelope

| Field | Type | Null? | Owner / provenance | Privacy |
|---|---|---|---|---|
| `schema` | const `"mastermind.single_name.reference_twin/v1"` | no | SNI (masterplan §5.1) | PUBLIC |
| `generation_id` | string; the generation is immutable once published | no | SNI producer | PUBLIC |
| `spec_hash` | string, sha256 hex of the producing spec | no | SNI producer | PUBLIC |
| `as_of` | RFC 3339 UTC; the market-state instant the twin describes | no | SNI producer | PUBLIC |
| `produced_at` | RFC 3339 UTC | no | SNI producer | PUBLIC |
| `state` | `SniState` (§3) | no | SNI reader; page-level rule in §3.2 | PUBLIC |
| `authority` | `{ may_rank:false, may_gate:false, may_size:false, may_signal:false, may_escalate:false, may_trade:false }`, all **const `false`** | no | SNI; the validator rejects any `true` | PUBLIC |

### 2.2 `identity` (owner: Data OS, `lib/dataos/identity.py` + `data/reference/*_master.parquet`)

| Field | Type | Null? | Owner / provenance | Privacy |
|---|---|---|---|---|
| `identity.query_symbol` | string, as normalised | no | the request | PUBLIC |
| `identity.listing.symbol` | string | no | request, cross-checked to `security_master.inception_code` | PUBLIC |
| `identity.listing.mic` | string | yes | `security_master.mic` | PUBLIC |
| `identity.listing.country` | string | yes | `security_master.country` | PUBLIC |
| `identity.listing.currency` | string, or `"UNRESOLVED"` | no | **No Data OS column at `c50af4eb`** (the security_master columns are `security_id, issuer_id, issuer_state, issuer_cik, issuer_evidence_snapshot, listing_key, country, mic, inception_code, effective_at, ingested_at, security_state, superseded_by`). The value is `"UNRESOLVED"` until Data OS owns it. Gap G-W1. | PUBLIC |
| `identity.security_id` | string, or `"UNRESOLVED"` | no | `security_master.security_id`, verbatim | PUBLIC |
| `identity.security_state` | string, passed through | yes | `security_master.security_state` | PUBLIC |
| `identity.canonical_issuer_id` | string, or `"UNRESOLVED"` | no | `security_master.issuer_id` / `issuer_master.issuer_id`, verbatim. **Never derived from a ticker, name or CIK.** | PUBLIC |
| `identity.issuer_state` | string, passed through (observed values: `RESOLVED`, `NO_ISSUER_EVIDENCE`) | no | `security_master.issuer_state` | PUBLIC |
| `identity.issuer_cik` | string | yes | `security_master.issuer_cik` (US-only today) | PUBLIC |
| `identity.issuer_evidence_snapshot` | date | yes | `security_master.issuer_evidence_snapshot` | PUBLIC |
| `identity.resolution_state` | `"resolved"` \| `"listing_only"` \| `"unresolved"` | no | SNI, derived by a fixed rule: `resolved` when both IDs are held; `listing_only` when the security is held and the issuer is `UNRESOLVED`; `unresolved` when the security is `UNRESOLVED` | PUBLIC |
| `identity.linked_listings[]` | array | no (may be empty) | — | PUBLIC |
| `…[].symbol` | string | no | `engine/hk_adr_bridge.py` pair table | PUBLIC |
| `…[].relation` | `"direct_adr"` \| `"proxy"` | no | `hk_adr_bridge` pair kind (`direct` → `direct_adr`; `proxy` → `proxy`) | PUBLIC |
| `…[].identity_link` | security_id, or `"UNRESOLVED"` | no | Data OS. `"UNRESOLVED"` whenever the masters hold no link, which is every row today. | PUBLIC |
| `…[].pooled` | const `false` | no | SNI (masterplan §5.2: never pool HKD/RMB counters; KWEB is never a Tencent quote) | PUBLIC |
| `…[].clock` | RFC 3339 | yes | the linked listing's own price owner | PUBLIC |

### 2.3 `source_clocks` (one entry per owner consulted)

`source_clocks: { [owner_key: string]: { as_of: string|null; observed_at: string; state: SniState; reason: string|null } }`. The owner keys are exactly the §2.5 lens keys plus `identity`. A clock that cannot be read is `state: "unavailable"` with a reason. It is never omitted.

### 2.4 `viewport` (masterplan §9, first payload, ≤ 5 rows)

`viewport.{what_changed, current_state, unusual, next_events, what_would_change}`. Each is `{ state: SniState; facts: Fact[]; absence: AbsenceReason|null }`.
- `Fact = { kind: string; value: number|string|null; unit: string|null; as_of: string; owner: OwnerKey; evidence_ref: EvidenceRef }`.
- `EvidenceRef = { owner: OwnerKey; ref: string }`. This is an opaque, owner-issued locator, never a document body.
- **The producer emits no prose.** Copy is rendered client-side from the band's EN/ZH copy table, following delta spec §7. This keeps model-originated text out of the wire, and keeps private or licensed text out of the PUBLIC projection by construction.
- `what_would_change` lists **watched conditions**, never falsifier or refutation language (macro design law; delta spec §10).

### 2.5 `lenses` (descriptors only in the first payload; bodies are lazy)

Each lens is `{ state: SniState; owner: OwnerKey; as_of: string|null; ref: string|null; reason: string|null }`.

| Lens key | Owner (named, never forked) | 9988.HK / 0700.HK at P0 | BABA at P0 | Privacy |
|---|---|---|---|---|
| `events` | Company Event / Earnings: `engine/company_intelligence/`, `engine/earnings_release/`, `event_workspace.v1` via the **existing** `/api/event-workspace/[symbol]` (`getCurrentEventWorkspace`, `eventWorkspace.ts` L1603). `WS:EARNINGS-INTELLIGENCE-OS`, `WS:EARNINGS-EVENT-INTELLIGENCE-COMPILER` | `unavailable` (no HK coverage proven, G-U1) | `current` or `stale-last-good`, as the route reports | PUBLIC refs; transcript text stays in `TranscriptDrawer` and is never in this payload |
| `financial_facts` | FIF: `contracts/financial_intelligence_packet.schema.json`, `engine/fundamental_forensics/financial_intelligence_packet.py`, `WS:FINANCIAL-INTELLIGENCE-FABRIC` | `not-applicable` (SEC-scoped; HK filings are not established) | as FIF reports, keyed by CIK `0001577552` (verbatim) | PUBLIC |
| `capital_state` | `engine/capital_structure/`, `WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2` | as the owner reports, else `unavailable` | as the owner reports | PUBLIC |
| `behavioral` | `engine/stock_identity/`, `WS:STOCK-IDENTITY` | `unavailable`, reason `pilot_not_production` | `unavailable`, reason `pilot_not_production`. The BABA pilot is provisional `epoch_0` and ended 2026-08-13, so it is **never rendered as current**. | PUBLIC |
| `options` | `engine/options_*.py`, `WS:ADVANCED-DATA-OPTIONS` | `not-applicable` (US listings only) | ENTITLED (`hasLiveOptions`) | ENTITLED |
| `research` | `engine/research_vault/`, `WS:RESEARCH-VAULT-AI-FABRIC` | state only | state only | **PRIVATE**: the public projection carries `state` only, and never a ref, count, title or text |
| `beliefs` | `engine/qledger.py` + family `sni_belief.v1` (`SNI_V0_EXTENSION_DECISION.md`), `WS:EVAL-OS-MEASUREMENT-LAW` | `not-applicable` until a belief is filed | as qledger reports | PUBLIC, with `label_mode: "directional_summary"` const until the V0 bridge is accepted, and **no probability field** before then |

### 2.6 `rights` and `corrections`

- `rights: { state: SniState; blocked_fields: string[] /* JSON paths */; basis: { owner: OwnerKey; ref: string }[] }`. SNI **aggregates** each owner's own rights statement and mints no rights registry. A blocked field is **omitted**, and its path is listed in `blocked_fields`. A blocked field is never nulled silently.
- `corrections[]` is append-only (masterplan §5.3): `{ superseded_generation_id: string; field_path: string; reason_code: string; corrected_at: string; owner: OwnerKey }`. The array is never rewritten in place.

### 2.7 Fixture skeleton: `sni-9988HK-linked-BABA.json` (values verbatim or `UNRESOLVED`)

```json
{
  "ok": true,
  "state": "identity-unresolved",
  "context": {
    "schema": "mastermind.single_name.reference_twin/v1",
    "generation_id": "fixture-0001",
    "spec_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "as_of": "2026-10-10T08:00:00Z",
    "produced_at": "2026-10-10T08:05:00Z",
    "state": "identity-unresolved",
    "identity": {
      "query_symbol": "9988.HK",
      "listing": { "symbol": "09988", "mic": "XHKG", "country": "HK", "currency": "UNRESOLVED" },
      "security_id": "SEC:HK-XHKG-09988",
      "security_state": null,
      "canonical_issuer_id": "UNRESOLVED",
      "issuer_state": "NO_ISSUER_EVIDENCE",
      "issuer_cik": null,
      "issuer_evidence_snapshot": null,
      "resolution_state": "listing_only",
      "linked_listings": [
        { "symbol": "BABA", "relation": "direct_adr", "identity_link": "UNRESOLVED", "pooled": false, "clock": null }
      ]
    },
    "source_clocks": { "identity": { "as_of": null, "observed_at": "2026-10-10T08:05:00Z", "state": "current", "reason": null } },
    "viewport": {
      "what_changed":      { "state": "unavailable", "facts": [], "absence": "no_hk_primary_evidence_owner" },
      "current_state":     { "state": "unavailable", "facts": [], "absence": "no_hk_primary_evidence_owner" },
      "unusual":           { "state": "unavailable", "facts": [], "absence": "no_hk_primary_evidence_owner" },
      "next_events":       { "state": "unavailable", "facts": [], "absence": "no_hk_event_coverage" },
      "what_would_change": { "state": "not-applicable", "facts": [], "absence": "no_open_beliefs" }
    },
    "lenses": {
      "events":          { "state": "unavailable",    "owner": "company_event",     "as_of": null, "ref": null, "reason": "no_hk_event_coverage" },
      "financial_facts": { "state": "not-applicable", "owner": "fif",               "as_of": null, "ref": null, "reason": "sec_scoped" },
      "capital_state":   { "state": "unavailable",    "owner": "capital_structure", "as_of": null, "ref": null, "reason": "not_checked_at_p0" },
      "behavioral":      { "state": "unavailable",    "owner": "stock_identity",    "as_of": null, "ref": null, "reason": "pilot_not_production" },
      "options":         { "state": "not-applicable", "owner": "options",           "as_of": null, "ref": null, "reason": "us_listings_only" },
      "research":        { "state": "unavailable",    "owner": "research_vault",    "as_of": null, "ref": null, "reason": null },
      "beliefs":         { "state": "not-applicable", "owner": "qledger",           "as_of": null, "ref": null, "reason": "no_open_beliefs" }
    },
    "rights": { "state": "current", "blocked_fields": [], "basis": [] },
    "corrections": [],
    "authority": { "may_rank": false, "may_gate": false, "may_size": false, "may_signal": false, "may_escalate": false, "may_trade": false }
  }
}
```

In the skeleton, `security_state: null` is a deliberate fixture choice: this lane did not record the row's `security_state` value. The P0 fixture author copies it verbatim from the master. The `spec_hash`, `generation_id` and timestamps are fixture placeholders, not production values. The 0700.HK fixture differs in four places: `security_id` is `SEC:HK-XHKG-00700`; `linked_listings` holds `KWEB`/`proxy`; there is no BABA row; and there is no TME row. The BABA fixture has `security_id` `SEC:US-XNYS-BABA`, `canonical_issuer_id` `ISS:US-XNYS-BABA`, `issuer_cik` `0001577552`, `resolution_state` `resolved`, and the linked listing `09988`/`direct_adr`/`identity_link:"UNRESOLVED"`.

---

## 3. State model

### 3.1 `SniState` and the mapping to existing vocabularies

`SniState = "current" | "stale-last-good" | "unavailable" | "partial" | "rights-blocked" | "identity-unresolved" | "not-applicable"` (masterplan §5.5). There is **no demo-fixture fallback state**, and fixture mode is test/dev only.

| SniState | CI v2 reference composition (`terminal/docs/refs/company_intelligence_v2/`) | CI 4-state enum (`companyIntelligence.ts` status L15) | Notes |
|---|---|---|---|
| `current` | `01-populated` | `ready` | — |
| `current` with a non-empty `corrections[]` | `04-corrected` | `ready` | The correction band renders first. |
| `partial` | `02-partial`, `07-provider-down` | `partial` | One owner is down while others answer. That owner's lens is `unavailable`. |
| `stale-last-good` | `03-stale` | `stale` | Shown with the saved-view time. Receipts stay readable. |
| `rights-blocked` | `05-blocked` (withheld shell) | — | Entitlement-locked reuses the same withheld shell, as delta spec §6 notes. |
| `unavailable` | `07-provider-down` (scope chip) | — | Includes the quarantine cause from `05-blocked` when the cause is quarantine rather than rights (reason `quarantined`). |
| `not-applicable` | `06-empty` (typed absence) | `not_covered` maps here only for lenses the owner does not serve | — |
| `identity-unresolved` | **none**. New, need N3 in the reuse map. | — | Uses the absence card (§3.5). It is scoped to the issuer, so listing-scoped rows still render. |

### 3.2 Page-level `state` rule (PROPOSED)

The page-level `state` is a precedence label, not a score. The first matching rule wins:
1. `identity-unresolved` when `resolution_state != "resolved"`.
2. `rights-blocked` when `rights.state == "rights-blocked"`.
3. `stale-last-good` when any served row comes from a last-good generation.
4. `partial` when any row or lens is `unavailable`.
5. `current` otherwise.

Each row and lens always carries its own state, so the page label never hides a lens state. This rule is **not** an aggregation into any ranking or gating quantity.

---

## 4. Privacy boundary, field by field

| Class | Fields | Rule |
|---|---|---|
| **PUBLIC** | everything in §2.1, §2.2, §2.3 and §2.4; all lens descriptors; `beliefs` counts and timestamps; `rights` and `corrections` | Served to any viewer. The payload carries no viewer identity, holdings or watchlist, and no user ID. |
| **ENTITLED** | `options` lens body and any live-options figure | Gated **server-side** in the route through `terminal/lib/entitlement.ts`. That module is server-only (it imports `node:crypto` and `billingAuth`). It provides `hasLiveOptions` (L161), `isPaidTier` (L192) and `isProTier` (L198). **P0 ships the PUBLIC projection only.** ENTITLED fields are omitted, not shown as teasers, until the server-side gate is pinned in the P0 spec (G-W3). |
| **PRIVATE: never in this payload** | Research Vault text, titles, counts or refs; licensed transcript text; private notes; any credential or token | The `research` lens carries `state` only. A transcript is reached only through the existing `TranscriptDrawer` path (`?tx=`), never inlined. The producer emits no prose (§2.4), so there is no free-text channel for a leak. |

The existing sibling routes (`company-intelligence/[symbol]` and `event-workspace/[symbol]`) carry **no auth**, only `rateLimit` max 120 (L56 and L30). The SNI route matches that, which is why it can serve only the PUBLIC class until G-W3 closes.

---

## 5. SLOs: **PROPOSED-NOT-RATIFIED**

| # | Budget | Target | Source | How measured (proposed) |
|---|---|---|---|---|
| S1 | Cached viewport visible | ≤ 3 s at 500 ms RTT / 1.6 Mbps | masterplan §7 (proposed) | Playwright with CDP network throttling on the three fixtures. **No existing harness does this at the pin** (G-W4). |
| S2 | Warm BFF p95 | ≤ 750 ms at 10 concurrent | masterplan §7 (proposed) | Load script against the route in fixture mode, then against R2. |
| S3 | A slow optional owner's impact | ≤ +2 s, then the lens resolves to a **named** `unavailable` | masterplan §7 + delta spec §9 provider-timeout row | Fault injection per owner. |
| S4 | Host-page shell interaction after load | < 150 ms | delta spec §9 (an existing host-page budget, which this band must not regress) | Existing CI e2e. |
| S5 | First-payload size | ≤ 256 KiB hard cap (O3's own proposal; CI's reader cap is 4 MiB at `companyIntelligence.ts` L221) | this draft | Reader validator rejects oversize as `invalid_payload`. |
| S6 | Skeletons | bounded, never terminal | delta spec §9 | e2e asserts that every fixture resolves to a named state. |

---

## 6. EN/ZH and dark/light evidence plan

**Light is NOT APPLICABLE on this surface.** This is a ruled fact about the host, not a skipped cell:
- the Terminal is dark-only by design (`terminal/app/settings.css` L32; `terminal/app/globals.css` L1267);
- the root is `data-theme="dark"` (`terminal/app/layout.tsx` L54);
- the CI v2 delta spec rules light out (§6 L424), quoting the release law's wording "dark/light where the host surface supports both".

The axis that does apply in its place is **red-up east**: `html[data-updown="east"]` (`globals.css` L124; `composition.css` L40). If SNI is ever composed into a macro-site surface, the macro two-art-direction law applies there in full, and that is a separate packet.

| Axis | Values | Mechanism at the pin |
|---|---|---|
| Theme | dark only | `layout.tsx` L54 |
| Language | EN, ZH | `localStorage mm.lang = "zh"` via `addInitScript` (`company-intelligence.spec.ts` L837) |
| Up/down colour | west (default), east | `html[data-updown="east"]` |
| Viewport | 1440×900, 820×1180 (touch), 390×844 (touch) | The default `desktop`/`tablet`/`mobile` projects in `terminal/playwright.config.ts` (L65–67) pick up a new spec **without a config edit**. The `companyIntelligenceSpec` regex (L8) matches only `company-intelligence.spec.ts`. |
| Fixture × state | 0700.HK `identity-unresolved`; 9988.HK `identity-unresolved` + linked BABA; BABA `current`; plus forced `partial`, `stale-last-good`, `rights-blocked`, `unavailable` and correction variants | `page.route("**/api/single-name-intelligence/<SYM>**")`, following the sibling route-mock idiom at `company-intelligence.spec.ts` L262–293 |
| Mount | M1 (v1 Brief), M2 (V2 Brief), M3/M4 (fallback) | Mock CI and event-workspace responses per mount |
| Keyboard / AT | focus order, chip labels, absence-card reachability | Delta spec §8 (L494) |
| Deep link | `?pane=intelligence` reload lands on the band | `MegaPane.tsx` L211–212 |

**Files (all new, so no shared-file edit):**
- `terminal/e2e/single-name-intelligence.spec.ts`
- screenshots via `testInfo.outputPath(\`${testInfo.project.name}-sni-<fixture>-<lang>-<updown>.png\`)`, the sibling idiom at L394

**Minimum PR-body matrix:**
- 3 viewports × 2 languages × 3 reference fixtures = 18 crops;
- plus the east-axis crops at 1440 for each fixture (3 crops);
- plus one crop per forced non-current state at 390 (5 crops);
- **26 crops** in total.

**Run:** `npm run test:e2e:responsive` (`terminal/package.json` L13, `playwright test`).

---

## 7. Gaps this draft surfaces (the cheapest next check for each)

| # | Gap | Blocker | Cheapest next check |
|---|---|---|---|
| G-W1 | No listing currency in Data OS | `security_master` has no currency column at `c50af4eb` | Data OS owner rules whether currency belongs to the listing row; `grep -n currency lib/dataos/identity.py` |
| G-W2 | No HK primary-evidence owner, so viewport rows for HK are `unavailable` | Masterplan §4 "HK sources" row is unowned at the pin | `ls engine/ | grep -i hkex` plus the owner table ruling |
| G-W3 | Server-side entitlement gate for ENTITLED fields | The sibling routes carry no auth | Read `terminal/lib/entitlement.ts` L1–60 for the request-context contract |
| G-W4 | No throttled-network perf harness | None at the pin | `git grep -n "emulateNetworkConditions\|Network.emulate" origin/master -- terminal/e2e` |
| G-W5 | Symbol deep-link form upstream of MegaPane | Only `pane` and `tx` were pinned | `git grep -n "MegaPane" origin/master -- terminal/app` |
| G-W6 | Non-event evidence on `EvidenceRail` (N4) | `event` is required | P0 design ruling (designer lane) |
| G-W7 | `security_state` value for the fixtures | Not recorded in this lane | Read the row in `security_master.parquet` at the fixture-authoring commit |

---

## 8. Recommendation (one)

Adopt this draft as the **P0 input contract**:
- a PUBLIC-only first payload with prose-free facts and lazy lens descriptors;
- identity copied verbatim from Data OS or set to `"UNRESOLVED"`;
- all-false authority;
- the 7-state model mapped onto the existing CI v2 reference compositions;
- a dark-only × EN/ZH × red-up × three-viewport evidence matrix built entirely from new files.

### Rejected alternatives

1. **Producer-authored EN/ZH prose in the payload.** It opens a model-text channel and a privacy leak path through the PUBLIC projection, and it duplicates the client copy-table idiom (delta spec §7).
2. **Inline lens bodies in the first payload.** This breaks masterplan §9 ("deep lenses lazy") and S1/S5, and it couples the band's latency to the slowest owner.
3. **Reuse `CompanyIntelligenceResult` as the transport.** Its 4-state status enum has no `identity-unresolved` or `rights-blocked`, and its context hard-types `exchange: null` (reuse map N1/N3).
4. **Ship ENTITLED fields nulled with an upgrade hint at P0.** There is no server-side gate on the sibling routes yet, so a hint would advertise fields the route cannot lawfully serve.
5. **Carry a light-theme evidence column.** The host is dark-only by ruling. Running that column would produce theatre evidence for a theme that does not exist.

## Adversarial review

1. **"A precedence page-state is a hidden rollup score."** It is a label with a fixed first-match order and no arithmetic, and every row and lens keeps its own state. It is never consumed by ranking or gating, and the `authority` block is const-false. The residual risk is that a UI might show only the page chip. Mitigation: the P0 spec must render per-row chips (the S6 assertion).
2. **"Omitting the currency (`UNRESOLVED`) makes the never-pool rule unenforceable."** Pooling is prevented structurally instead: `pooled: false` is const, each linked listing has its own clock, and the payload carries no price at all. Currency matters only once a price lens exists, and by then G-W1 must be closed. If P0 adds a price row before G-W1, that is a contract violation.
3. **"Prose-free facts make the main viewport unreadable for a non-earnings name."** That is plausible for HK today. It is mostly `unavailable` rows, because no HK primary-evidence owner exists (G-W2). The honest answer is the typed absence card with plain-word reasons, not generated prose. If the result is too thin, the fix is G-W2 (an owner), not text in the wire.
4. **"Declaring light NOT APPLICABLE dodges the macro two-art-direction law."** That law governs macro-site surfaces. The host here is the Terminal, which is dark-only under three cited files and an existing ruled spec line (delta spec L424). The law re-applies in full if SNI is composed into a macro page.
5. **"The 9988↔BABA `direct_adr` relation from `hk_adr_bridge` smuggles an identity join."** The relation is labelled "bridge pair (display)", and `identity_link` stays `"UNRESOLVED"` until Data OS holds a link. The band must never inherit issuer-scoped lenses across the pair. The P0 test asserts that BABA's `financial_facts` never render under 9988.HK.
6. **"The SLOs are unmeasurable today, so they are decoration."** That is correct, and they are labelled PROPOSED-NOT-RATIFIED with G-W4 named. S4 and S6 are measurable with the existing e2e, so P0 enforces those and records S1–S3 as targets until a harness exists.
