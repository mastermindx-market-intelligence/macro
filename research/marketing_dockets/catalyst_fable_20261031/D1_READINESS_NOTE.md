# D1 readiness note: catalyst partner pack and scan -> growth registry attribution

Written by MX-ORCH-B (Opus orchestrator, seat ce215fa3). Date: 2026-10-31.
Source pins:
- base `55dc7cab50c95d74406a61beb1d8aa2ae179a8a5` (lane/mx-cat-a1-base)
- partner source `6b4e3b8846cabce47b7501ce66ae507f84164500` (PR #8683 head, four adopted blobs only)

Scope: this note covers only the opaque attribution that marketing hands over. It does not design or claim the commercial join, which D07 and the Website own.

## 1. What the partner pack emits (opaque, content-addressed, no identity)

The CTA is built at `engine/marketing/catalyst_partner_pack.py` @6b4e3b88, lines 417-433. It uses `engine/marketing/links.py::canonical_link` (lines 56-85) and then `is_tagged_canonical`. The route is exactly `/api/catalyst`, the human HTML scan route. It is never `/api/catalyst/scan`. The query string has exactly 6 keys (`_require(len(...)==6)`):

| key | value | nature |
|---|---|---|
| `utm_source` | `partner` (constant) | channel class |
| `utm_medium` | `partner-<slug>`; slug `^[a-z][a-z0-9_-]{1,47}$` (line 26) | partner channel label, operator-chosen, no brand asserted by marketing |
| `utm_campaign` | `catalyst_scan` (constant) | campaign |
| `utm_content` | `pack_id` = `cp_` + first 18 hex of sha256(canonical identity JSON) (lines 417-419) | opaque, content-addressed asset id |
| `event_id` | producer `catalyst.public_event/v1` event id, `_ID`-validated | scan input (preselects the cited event); NOT an attribution key |
| `tickers` | comma-joined selected tickers | scan input; NOT an attribution key |

None of these is a person, email, account, session, device or recipient id. `pack_id` identifies the asset, not the reader.

## 2. What the scan page and lifecycle accept as first touch

- `templates/catalyst_scan.js` @55dc7cab, lines 346-354 (`touch()`): reads ONLY `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `partner_id`. Each must match `^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$`. It is sent as `first_touch` only on a consented opt-in request, after a qualified scan.
- `engine/marketing/catalyst_lifecycle.py` @55dc7cab: the key set `_TOUCH_KEYS` is at line 40, and `first_touch()` (lines 89-104) re-validates server-side. It rejects IP-address values and documents the first touch as "a sanitized referral claim, never an authenticated partner payout".
- Consequences for D1:
  - all four pack `utm_*` values pass both validators (`cp_` hex, `partner-<slug>`, constants);
  - `event_id` and `tickers` are consumed by the scan form, not recorded as attribution;
  - the pack does NOT emit `partner_id`. The partner is identifiable only via `utm_medium=partner-<slug>`. `partner_id` remains an accepted-but-unused key. No new key is needed for D1.

## 3. Growth registry handoff (config/growth_events.yml)

- `session.start` (lines 119-130, status `live`, funnel `visit`) declares the properties `source`, `campaign`, `landing_surface`, `referrer_host` and `is_first_ever`. The natural mapping is:
  - `utm_source` -> `source`
  - `utm_campaign` -> `campaign`
  - landing path `/api/catalyst` -> `landing_surface`
- OBSERVED GAP (Website-owned, not marketing): the live emitter `templates/theme.js` @55dc7cab line 205 calls `track('session_start')` with NO properties. `track()` (lines 178-187) adds only `type`, `site`, `sid`, `fp`, `path` and `t`, and session_start is not sent through `mmTrackGrowth` (envelope v1, typed `meta`).
  - So today the registry-declared `source`/`campaign` are NOT populated from UTM at session start.
  - `utm_content` (the pack_id) has no registry property at all. The only durable carrier of pack_id is the opt-in `first_touch` on the verified lifecycle record.
- Readiness verdict for D1:
  - marketing-side opaque keys are READY and stable (deterministic `pack_id`, closed six-key CTA, validator-compatible);
  - the visit-level join from UTM to `session.start.source/campaign` is NOT wired, and it is Website/D07 work.

## 4. What remains Website / D07 owned (marketing passes opaque attribution only)

1. Mapping the URL `utm_*` onto `session.start` properties (theme.js / growth envelope), including whether `utm_content` gets a registry property.
2. The session -> user join, and any signup, qualified-account, trial or billing linkage. This is D07 W1b `engine/marketing/attribution.py`; the docket `research/marketing_dockets/D07_FUNNEL_LIFECYCLE_MNZ.md` lines 23-31 say it needs operator read access to signup records.
3. Entitlement, checkout and payout. A UTM first touch is a claim, never an authenticated partner payout (lifecycle line 90).
4. Retention and deletion policy for `first_touch` on lifecycle records, plus the decision whether `fp` (the fingerprint in the theme.js beacon) is acceptable alongside partner attribution. This is a Website privacy decision and is flagged here only.

## 5. Not claimed

- No end-to-end attribution is proven.
- No production behavior was observed.
- No flag was changed: `CATALYST_PUBLIC_ENABLED`, `CATALYST_OPTIN_ENABLED` and `CATALYST_UX_ENABLED` are untouched.
- Partner packs remain link-only and depend on the separate SEC EDGAR rights classification (see `RIGHTS_CLASSIFICATION_REQUEST.md`).
