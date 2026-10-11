// Shared helpers for the terminal → macro-api billing proxy routes.
//
// These routes are thin: validate the caller's Supabase session (except /config,
// which needs none), forward to the billing gateway with the user's access token,
// and pipe the upstream status + JSON straight back. All Stripe secret-key logic
// lives in the gateway (separate repo) — the terminal never sees a secret key.
//
// Contract (gateway, code against verbatim):
//   GET  {BASE}/api/billing/config           → { publishable_key } · 503 unconfigured
//   POST {BASE}/api/billing/subscribe/init    → { client_secret, customer_id }
//   POST {BASE}/api/billing/subscribe/complete→ { status, subscription_id, trial_end }
//   GET  {BASE}/api/me                         → { tier, features, status, current_period_end }
//
// BASE env = BILLING_GATEWAY_BASE (default https://www.mastermind-x.com).

import { cache } from "react";
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const BILLING_BASE =
  process.env.BILLING_GATEWAY_BASE || "https://www.mastermind-x.com";

// Tiers the terminal is allowed to forward. The gateway re-validates, but bounding
// here keeps garbage off the wire and returns a crisp 400 to the UI.
//
// `essential` is now the canonical name for this entitlement and is what the
// Terminal EMITS. `insider` is the pre-rename name and stays accepted (not
// translated) because the gateway takes BOTH names — a cached page or an old
// bookmark can still post it, and bouncing it here would 400 a real checkout.
// Order matters only for readability; canonical first.
export const VALID_TIERS = ["essential", "insider", "pro"] as const;
export const VALID_INTERVALS = ["monthly", "annual"] as const;
export type ValidTier = (typeof VALID_TIERS)[number];
export type ValidInterval = (typeof VALID_INTERVALS)[number];

export function isTier(v: unknown): v is ValidTier {
  return typeof v === "string" && (VALID_TIERS as readonly string[]).includes(v);
}
export function isInterval(v: unknown): v is ValidInterval {
  return typeof v === "string" && (VALID_INTERVALS as readonly string[]).includes(v);
}

/**
 * Resolve the verified user + access token, or null when unauthed.
 *
 * Memoized PER REQUEST with React `cache()`: several gates in one render (page
 * gate + billing read + entitlement check) collapse onto a single
 * getSession()+getUser() pair instead of repeating the Supabase round trip for
 * each. The memo never spans requests, so the verification below still runs on
 * every inbound request and a revoked session is caught immediately. Outside a
 * React request scope (e.g. a plain route handler) `cache()` degrades to a
 * direct call, so behaviour there is byte-for-byte what it was before.
 */
export const billingAuth = cache(async (): Promise<{ token: string } | null> => {
  const supabase = await createClient();
  // getUser() verifies the JWT with Supabase Auth (getSession alone is cookie-trusted);
  // pairing the two catches expired/revoked sessions before we forward.
  const [{ data: sessionData }, { data: userData }] = await Promise.all([
    supabase.auth.getSession(),
    supabase.auth.getUser(),
  ]);
  const session = sessionData.session;
  if (!session || !userData.user) return null;
  return { token: session.access_token };
});

/** Forward to the gateway and pipe its status + JSON back verbatim. */
export async function forward(
  path: string,
  init: { method: "GET" | "POST"; token?: string; body?: unknown; signal?: AbortSignal },
): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (init.token) headers.Authorization = `Bearer ${init.token}`;
  if (init.body !== undefined) headers["Content-Type"] = "application/json";

  let upstream: Response;
  try {
    upstream = await fetch(`${BILLING_BASE}${path}`, {
      method: init.method,
      headers,
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      signal: init.signal,
      cache: "no-store",
    });
  } catch (e: any) {
    return NextResponse.json(
      { error: "Billing service unreachable", detail: e?.message },
      { status: 502 },
    );
  }

  // Pipe upstream status + JSON through unchanged. Non-JSON bodies (rare — a proxy
  // error page) degrade to a generic shape so the UI still gets valid JSON.
  const text = await upstream.text().catch(() => "");
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { error: `Billing service error (${upstream.status})`, detail: text.slice(0, 200) };
  }
  return NextResponse.json(data as Record<string, unknown>, { status: upstream.status });
}
