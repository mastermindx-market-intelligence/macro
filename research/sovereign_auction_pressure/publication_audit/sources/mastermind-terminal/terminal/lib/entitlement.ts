import { cache } from "react";
import { createHash } from "node:crypto";
import { billingAuth, BILLING_BASE } from "@/app/api/billing/gateway";
import { isPaidSubscriptionTier, normalizeSubscriptionTier } from "@/lib/subscriptionTier";

/**
 * Server-side entitlement checks against the AUTHORITY — macro-api
 * `user_entitlements` (written by app/billing.py from Stripe), surfaced via
 * `GET {BILLING_BASE}/api/me` → `{ tier, features }`.
 *
 * NOT `profiles.is_pro`: terminal/AGENTS.md flags that as a UI hint that can
 * drift from the real subscription (a paid user with a stale hint gets wrongly
 * blocked; an expired one wrongly allowed).
 *
 * All checks FAIL-CLOSED: no session / non-2xx / error → the restrictive answer,
 * so a paid surface is never served on uncertainty.
 */
type Entitlement = { tier: string; features: string[] };

/**
 * Short-TTL, POSITIVE-ONLY entitlement cache.
 *
 * WHY: one cold /options load resolves entitlement SEVEN times — the page render
 * (app/(shell)/options/page.tsx), five /api/flow GETs and the /api/flow/stream
 * open. Each resolution is a cross-origin `GET {BILLING_BASE}/api/me` measured at
 * ~0.5 s TTFB, and because the client's fetch waves are serial those six
 * duplicates land directly on the critical path.
 *
 * THE AUTHORITY DOES NOT MOVE. macro-api still decides; this only stops us asking
 * it the same question about the same access token six more times inside one page
 * load. The contract that keeps that safe:
 *
 *   - keyed by SHA-256 of the caller's access token, so one user's answer can
 *     never satisfy another user's gate — and no raw JWT is retained in the map;
 *   - only a POSITIVE answer is stored. A null (unauthed / non-2xx / network
 *     error) and an answer that fails the calling gate are never cached, so a
 *     fail-closed "no" is always re-derived from the authority and a freshly
 *     upgraded user is never stuck behind the paywall;
 *   - TTL 45 s (inside the specced 30–60 s band): a revocation can lag by at most
 *     one TTL, the same bound the /api/flow payload cache already runs on;
 *   - in-flight dedup collapses the concurrent gates of one page load onto a
 *     single upstream call;
 *   - `isPaidTier()` — the Pine-script SAVE gate — deliberately does NOT use it.
 *     Write paths keep resolving fresh.
 */
const ENT_TTL_MS = 45_000;
/** Bound the map so a long-lived process with many signed-in users cannot grow it forever. */
const ENT_MAX_KEYS = 512;

type CacheEntry = { ent: Entitlement; ts: number };
const CACHE = new Map<string, CacheEntry>();
const INFLIGHT = new Map<string, Promise<Entitlement | null>>();

function tokenKey(token: string): string {
  return createHash("sha256").update(token).digest("base64url");
}

/** Drop expired keys once oversized; hard-reset if that was not enough. */
function sweep(now: number): void {
  if (CACHE.size <= ENT_MAX_KEYS) return;
  for (const [k, v] of CACHE) {
    if (now - v.ts >= ENT_TTL_MS) CACHE.delete(k);
  }
  if (CACHE.size > ENT_MAX_KEYS) CACHE.clear();
}

/** One `/api/me` round trip. null on non-2xx / parse / network error (fail-closed). */
async function fetchEntitlementFor(token: string): Promise<Entitlement | null> {
  try {
    const r = await fetch(`${BILLING_BASE}/api/me`, {
      headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
      cache: "no-store",
    });
    if (!r.ok) return null;
    const d = await r.json();
    return {
      tier: typeof d?.tier === "string" ? d.tier : "free",
      features: Array.isArray(d?.features) ? d.features : [],
    };
  } catch {
    return null;
  }
}

/**
 * Uncached resolution: one auth pair (itself memoized per request by
 * `billingAuth`) plus one live `/api/me`. React `cache()` dedupes repeat gates
 * inside a single render; outside a React request scope it degrades to a plain
 * call, so this is exactly the pre-existing behaviour.
 */
const fetchEntitlement = cache(async (): Promise<Entitlement | null> => {
  const auth = await billingAuth();
  if (!auth) return null;
  return fetchEntitlementFor(auth.token);
});

/**
 * Cached resolution for ONE gate. `gate.ok` is that gate's own predicate: only an
 * entitlement that SATISFIES it is worth remembering, so every "no" is re-asked.
 *
 * The key carries the gate id as well as the token so the positive-only rule can
 * never be subverted by a second gate: if gate A cached an entitlement that gate
 * B reads as "no", B would be serving a cached negative. Separate lanes keep the
 * invariant local. Only `hasLiveOptions` uses this path today, so the extra lane
 * costs nothing.
 */
async function fetchEntitlementCached(
  gate: { id: string; ok: (e: Entitlement) => boolean },
): Promise<Entitlement | null> {
  const auth = await billingAuth();
  if (!auth) return null; // unauthed → fail-closed, never cached

  const key = `${gate.id}:${tokenKey(auth.token)}`;
  const now = Date.now();

  const hit = CACHE.get(key);
  if (hit) {
    if (now - hit.ts < ENT_TTL_MS) return hit.ent;
    CACHE.delete(key); // expired — go back to the authority
  }

  const pending = INFLIGHT.get(key);
  if (pending) return pending;

  const p = fetchEntitlementFor(auth.token).then(
    (ent) => {
      INFLIGHT.delete(key);
      if (ent && gate.ok(ent)) {
        CACHE.set(key, { ent, ts: Date.now() });
        sweep(Date.now());
      } else {
        CACHE.delete(key); // never pin a negative or an error
      }
      return ent;
    },
    () => {
      INFLIGHT.delete(key);
      CACHE.delete(key);
      return null;
    },
  );
  INFLIGHT.set(key, p);
  return p;
}

/** Live-options read gate: catalog feature for customers + the private operator/unlimited overlay. */
const LIVE_OPTIONS = {
  id: "live_options",
  // Macro /api/me applies the private operator/comp allowlist by overriding the
  // effective tier to `unlimited` after reading the billing row; it deliberately
  // does not synthesize customer feature keys into that row. `unlimited` is
  // already the Terminal's Pro-equivalent operator tier (see isProTier below),
  // so it must carry read access here too. Keep the exception exact: ordinary
  // free/essential/pro callers still require the explicit feature authority.
  ok: (e: Entitlement) =>
    e.features.includes("terminal_live_options")
    || e.tier.trim().toLowerCase() === "unlimited",
};

/** Live-options surface — customer feature entitlement plus the private unlimited operator tier. */
export async function hasLiveOptions(): Promise<boolean> {
  const e = await fetchEntitlementCached(LIVE_OPTIONS);
  return !!e && LIVE_OPTIONS.ok(e);
}

/**
 * Human research issuance is deliberately narrower than the paid options read
 * surface.  A paid account may read options evidence; it may never turn a
 * proposal into a research position unless the billing authority supplies this
 * explicit operator capability (or its operator-only unlimited tier).
 *
 * This is a server-side convenience gate only.  The Macro operator endpoint
 * rechecks the same authority before appending a review event.
 */
export async function hasIssueDeskOperator(): Promise<boolean> {
  const e = await fetchEntitlement();
  return !!e && (
    e.tier.trim().toLowerCase() === "unlimited"
    || e.features.includes("options_issue_desk_operator")
  );
}

/**
 * Any PAID account (essential or pro, incl. 7-day trial). Used where the surface
 * isn't broken out as its own feature in config/plans.yml — e.g. Pine-script
 * save — matching the legacy `is_pro` boolean's "any paid" semantics. If a
 * surface should be pro-ONLY, gate on `tier === "pro"` instead.
 *
 * Deliberately UNCACHED beyond the per-request memo: its callers include a write
 * path (app/api/scripts/save), and a write gate resolves fresh every time.
 */
export async function isPaidTier(): Promise<boolean> {
  const e = await fetchEntitlement();
  return !!e && isPaidSubscriptionTier(e.tier);
}

/** Pro-equivalent account, including the billing authority's operator/comp `unlimited` tier. */
export async function isProTier(): Promise<boolean> {
  const e = await fetchEntitlement();
  return !!e && normalizeSubscriptionTier(e.tier) === "pro";
}
