// Market taxonomy + the user's market preference — the ONE contract both properties read.
//
// Background: onboarding (macro-side templates/onboard.js) has always written
// `user_metadata.market_focus` — an array of "us" | "cn" | "hk" | "ca" | "global" — and
// OnboardingProvider faithfully pushes the stashed copy into user_metadata on first authed
// mount. Nothing ever READ it. The write path was complete and the read path did not exist,
// so a user who picked "China only" got a US-shaped product anyway. This module is the read
// path, and it is deliberately pure so both the Next.js Terminal and the static macro site
// can agree on what "my markets" means without sharing a runtime.
//
// Two ideas that are easy to conflate and must not be:
//   • FOLLOWED set  — "markets you follow" (`user_metadata.market_focus`, the field the macro
//                     dashboard's settings modal owns). Promotes those markets' surfaces:
//                     search ranking boost, watchlist seed. Zero, one, or many.
//   • ENABLED set   — every market the user can see at all. A market that is not enabled is
//                     not searchable; its symbols behave as though they are not in the
//                     universe. Terminal-only; the macro side has no UI for it.
//
// `home` (a single MarketId, or null) is what FOLLOWED used to be. It survives as a DERIVED
// compatibility field — the macro dashboard still reads and writes `markets.home`, so we keep
// it in sync (first followed country) rather than dropping it from the shared object. Nothing
// in the Terminal UI lets a user choose it any more, and search ranking no longer reads it:
// a user who follows both HK and the US gets BOTH boosted, which is the whole point.
//
// Crypto is a market in the taxonomy (it classifies symbols) but NOT a country: it is not a
// candidate for `home` or for a follow. Every market is searchable by default; users can still
// narrow the enabled set themselves in Terminal settings.

export type MarketId = "us" | "cn" | "hk" | "ca" | "intl" | "crypto";

export const MARKET_IDS: readonly MarketId[] = ["us", "cn", "hk", "ca", "intl", "crypto"] as const;

const MARKET_SET = new Set<string>(MARKET_IDS);
export const isMarketId = (v: unknown): v is MarketId => typeof v === "string" && MARKET_SET.has(v);

// ── followed markets — the `market_focus` contract shared with the macro dashboard ────────
//
// The ids here are NOT MarketIds: the shared vocabulary (written by macro's settings modal and
// by our own onboarding) says "global" where the Terminal taxonomy says "intl". Both sides read
// the same array, so the wire vocabulary wins and the mapping lives here rather than in a
// component. Crypto is absent by design — it is not a country and is never a follow target.

export type FollowId = "us" | "cn" | "hk" | "ca" | "global";

export const FOLLOW_IDS: readonly FollowId[] = ["us", "cn", "hk", "ca", "global"] as const;

const FOLLOW_SET = new Set<string>(FOLLOW_IDS);
export const isFollowId = (v: unknown): v is FollowId => typeof v === "string" && FOLLOW_SET.has(v);

// For RANKING purposes "global" means the `intl` bucket — every venue we don't map to a named
// country. (It does NOT mean "everything": `enabled` is what decides what exists at all.)
const FOLLOW_TO_MARKET: Record<FollowId, MarketId> = { us: "us", cn: "cn", hk: "hk", ca: "ca", global: "intl" };

export const followToMarket = (f: FollowId): MarketId => FOLLOW_TO_MARKET[f];

/** MarketId → FollowId for the legacy `markets.home` fallback. Crypto has no follow id. */
export function marketToFollow(m: MarketId | null | undefined): FollowId | null {
  if (!m || m === "crypto") return null;
  return m === "intl" ? "global" : m;
}

// Spellings seen in the wild across two properties' onboarding generations. Normalized rather
// than dropped, because dropping one silently un-follows a market the user did pick.
const FOLLOW_ALIAS: Record<string, FollowId> = {
  china: "cn", canada: "ca", international: "global", intl: "global", all: "global", worldwide: "global",
};

/** `market_focus` → FollowId[]: deduped, order-preserving, unknown ids dropped. Never throws. */
export function sanitizeFollowed(raw: unknown): FollowId[] {
  if (!Array.isArray(raw)) return [];
  const out: FollowId[] = [];
  for (const v of raw) {
    if (typeof v !== "string") continue;
    const k = v.trim().toLowerCase();
    const id = isFollowId(k) ? k : FOLLOW_ALIAS[k];
    if (id && !out.includes(id)) out.push(id);
  }
  return out;
}

/** The MarketIds that get the follow boost in search ranking. Hoisted once per sort by callers —
 *  building this inside the scoring loop would allocate a Set per manifest row. */
export function followedMarketSet(followed: readonly FollowId[] | null | undefined): Set<MarketId> {
  const s = new Set<MarketId>();
  for (const f of followed || []) s.add(FOLLOW_TO_MARKET[f]);
  return s;
}

/** The derived `markets.home`: the first followed COUNTRY. "global" is not a country, so a user
 *  who follows only "global" has no home — which is correct, and what null has always meant. */
export function homeFromFollowed(followed: readonly FollowId[]): MarketId | null {
  for (const f of followed) if (f !== "global") return FOLLOW_TO_MARKET[f];
  return null;
}

// ── manifest `mkt` → market group ────────────────────────────────────────────────────────
// The manifest's `mkt` is an EXCHANGE/venue string, not a market group: the production
// manifest carries NYSE, NASDAQ, AMEX, US, SSE, SZSE, HKEX, TSX plus a long tail of country
// names (United Kingdom, Japan, India, South Korea, Taiwan, Australia, France, Germany,
// Switzerland, Netherlands, Italy, Spain, …). Anything not named here falls to "intl", which
// is the correct default: the tail is genuinely international and new venues should not
// silently land in "us" just because they are unmapped.
const VENUE_GROUP: Record<string, MarketId> = {
  // United States
  NYSE: "us", NASDAQ: "us", AMEX: "us", US: "us", ARCA: "us", BATS: "us", OTC: "us",
  // Mainland China
  SSE: "cn", SZSE: "cn", BSE: "cn", CN: "cn",
  // Hong Kong
  HKEX: "hk", HK: "hk", SEHK: "hk",
  // Canada
  TSX: "ca", TSXV: "ca", CA: "ca", NEO: "ca",
  // Crypto — the production manifest sets mkt:"Crypto" alongside sec:"Crypto". `sec` already
  // wins in marketOf, but mapping the venue too keeps a row with only `mkt` set from falling
  // through to "intl".
  CRYPTO: "crypto", Crypto: "crypto",
};

// Symbol-suffix fallback, for rows whose `mkt` is missing. Mirrors intradayShared.classify()'s
// routing rules so a symbol can never be classified into one market for data-fetching and a
// different one for search. Kept in sync deliberately — see lib/__tests__/markets.test.ts.
function groupFromSymbol(sym: string): MarketId {
  if (/-USD(T)?$/i.test(sym)) return "crypto";
  if (/\.(SS|SZ|BJ)$/i.test(sym)) return "cn";
  if (/\.HK$/i.test(sym)) return "hk";
  if (/\.(TO|V|NE)$/i.test(sym)) return "ca";
  // Any other dotted suffix is a foreign venue (.L, .T, .PA, .DE, .AX, .KS, .TW, …).
  if (/\.[A-Z]{1,3}$/i.test(sym)) return "intl";
  return "us";
}

/** Market group for a manifest row. `sec === "Crypto"` wins over venue — a crypto pair listed
 *  against a US venue is still crypto to a user choosing what to see. */
export function marketOf(sym: string, row?: { mkt?: string; sec?: string } | null): MarketId {
  if (row?.sec === "Crypto") return "crypto";
  const venue = (row?.mkt || "").trim();
  if (venue) {
    const hit = VENUE_GROUP[venue] || VENUE_GROUP[venue.toUpperCase()];
    if (hit) return hit;
    return "intl"; // named venue we don't map == international, never a silent "us"
  }
  return groupFromSymbol(sym);
}

// ── the preference itself ────────────────────────────────────────────────────────────────

export type MarketPrefs = {
  /** DERIVED, not chosen — the first followed country, kept only because the macro dashboard
   *  reads `markets.home`. Search ranking uses `followed`; nothing boosts off this field. */
  home: MarketId | null;
  enabled: MarketId[];        // markets the user can see and search; always contains `home`
  /** Legacy migration marker for the retired US-only automatic narrowing. New/default and
   *  user-edited preferences are always false. */
  autoNarrowed: boolean;
  /** "Markets you follow" — the boosted set. Serialized as `user_metadata.market_focus`, NOT
   *  inside the `markets` object, because that is where the macro dashboard reads it. */
  followed: FollowId[];
};

export const ALL_MARKETS: MarketId[] = [...MARKET_IDS];

/** MarketId → i18n key. Lives here, next to the taxonomy, so the settings pane and the search
 *  filter notice name a market identically without settings having to import the search dialog. */
export const MARKET_TKEY: Record<MarketId, string> = {
  us: "mktUs", cn: "mktCn", hk: "mktHk", ca: "mktCa", intl: "mktIntl", crypto: "mktCrypto",
};

/** FollowId → i18n key. These are the ONBOARDING chip labels ("US markets", "Global", …), not
 *  the MARKET_TKEY venue names: the account panel asks the same question the signup chips ask,
 *  and a user who picked "Global" at signup must see "Global" when they come back to change it. */
export const FOLLOW_TKEY: Record<FollowId, string> = {
  us: "obMktUs", cn: "obMktCn", hk: "obMktHk", ca: "obMktCa", global: "obMktGlobal",
};

export const DEFAULT_PREFS: MarketPrefs = { home: null, enabled: [...MARKET_IDS], autoNarrowed: false, followed: [] };

// Legacy onboarding chip ids → MarketId. "global" is the onboarding's word for "I trade
// everywhere", which enables everything rather than mapping to the `intl` bucket alone.
const LEGACY_CHIP: Record<string, MarketId | "all"> = {
  us: "us", cn: "cn", china: "cn", hk: "hk", ca: "ca", canada: "ca",
  intl: "intl", international: "intl", global: "all",
};

/**
 * Operator rule (2026-07-29): home/followed markets affect ranking, not visibility. Every account
 * starts with the complete searchable universe and can opt into a narrower enabled set later.
 */
export function defaultEnabledFor(picks: MarketId[]): { enabled: MarketId[]; autoNarrowed: boolean } {
  void picks; // retained for the onboarding migration call sites; picks now affect ranking only
  return { enabled: [...MARKET_IDS], autoNarrowed: false };
}

type MetaShape = {
  markets?: { home?: unknown; enabled?: unknown; autoNarrowed?: unknown } | null;
  market_focus?: unknown;
} | null | undefined;

/**
 * Read the canonical preference out of Supabase `user_metadata`, migrating the legacy
 * `market_focus` array when the new `markets` object is absent.
 *
 * Precedence: an explicit `markets` object always wins, even if a stale `market_focus` is
 * still sitting next to it — otherwise a user who narrows their markets in settings would be
 * silently reverted on next load by the signup-time array.
 *
 * Never throws: malformed metadata degrades to DEFAULT_PREFS (everything visible), because the
 * failure mode of "show too much" is recoverable and "show nothing" is not.
 */
export function readMarketPrefs(meta: MetaShape): MarketPrefs {
  // `market_focus` is read on EVERY path now, not only as a legacy migration: it is the live
  // "markets you follow" field, edited on both properties. `markets` still wins for home/enabled.
  const focusRaw = meta?.market_focus;
  const followed = sanitizeFollowed(focusRaw);

  const m = meta?.markets;
  if (m && typeof m === "object") {
    const enabled = Array.isArray(m.enabled) ? m.enabled.filter(isMarketId) : [];
    const home = isMarketId(m.home) ? m.home : null;
    // `autoNarrowed:true` was written only by the retired US-only system default. A deliberate
    // settings edit always cleared the marker, so widening this legacy state upgrades old users
    // without overwriting any market filter they chose themselves.
    const retireAutoNarrowing = m.autoNarrowed === true;
    // An empty/garbage enabled list would make the whole product unsearchable — fall back to
    // "home only + crypto" if we at least know the home, else everything.
    const safeEnabled: MarketId[] = retireAutoNarrowing
      ? [...MARKET_IDS]
      : enabled.length ? enabled : home ? [home, "crypto"] : [...MARKET_IDS];
    return {
      home,
      enabled: withHome(safeEnabled, home),
      autoNarrowed: false,
      followed: followedOrHome(followed, home),
    };
  }

  if (Array.isArray(focusRaw) && focusRaw.length) {
    const mapped: MarketId[] = [];
    let all = false;
    for (const raw of focusRaw) {
      const hit = typeof raw === "string" ? LEGACY_CHIP[raw.toLowerCase()] : undefined;
      if (hit === "all") all = true;
      else if (hit) mapped.push(hit);
    }
    if (all) return { home: mapped[0] ?? null, enabled: [...MARKET_IDS], autoNarrowed: false, followed };
    if (mapped.length) {
      const { enabled, autoNarrowed } = defaultEnabledFor(mapped);
      return { home: mapped[0], enabled: withHome(enabled, mapped[0]), autoNarrowed, followed };
    }
  }

  return { ...DEFAULT_PREFS, enabled: [...MARKET_IDS], followed };
}

/** No `market_focus` yet (an account that predates the field, or a Terminal-only signup) — fall
 *  back to the one market we did know about, so ranking is not silently un-personalized. */
function followedOrHome(followed: FollowId[], home: MarketId | null): FollowId[] {
  if (followed.length) return followed;
  const f = marketToFollow(home);
  return f ? [f] : [];
}

/** `enabled` must always contain `home` — a user cannot hide their own home market by accident. */
function withHome(enabled: MarketId[], home: MarketId | null): MarketId[] {
  const set = new Set(enabled);
  if (home) set.add(home);
  return MARKET_IDS.filter((m) => set.has(m));   // canonical order, deduped
}

/** The shape written back to `user_metadata`. Kept separate from readMarketPrefs so the write
 *  is explicit at every call site — this object is shared with the macro site. */
export function serializeMarketPrefs(p: MarketPrefs): { markets: { home: MarketId | null; enabled: MarketId[]; autoNarrowed: boolean } } {
  return { markets: { home: p.home, enabled: withHome(p.enabled, p.home), autoNarrowed: p.autoNarrowed } };
}

/** Toggle one market, refusing to disable the home market or to empty the set entirely. */
export function toggleMarket(p: MarketPrefs, m: MarketId): MarketPrefs {
  const on = p.enabled.includes(m);
  if (on && (m === p.home || p.enabled.length <= 1)) return p;   // never leave the user with nothing
  const next = on ? p.enabled.filter((x) => x !== m) : [...p.enabled, m];
  // Any hand edit means the narrowing is now the user's, not ours — stop explaining it as a default.
  return { ...p, enabled: withHome(next, p.home), autoNarrowed: false };
}

/**
 * Change the followed markets. `home` is re-derived (it is no longer a user choice) and pulled
 * into `enabled`, which is the one and only way follows touch visibility.
 *
 * DELIBERATE DIVERGENCE from the macro dashboard: macro recomputes the whole `enabled` list from
 * the follow picks. We do NOT, because the Terminal has its own explicit enabled UI and a user
 * who narrowed their searchable universe there must not have it silently rewritten by editing an
 * unrelated "markets I follow" list. `autoNarrowed` is preserved for the same reason — this edit
 * did not change the narrowing, so it must not change the explanation of it.
 *
 * Accepted consequence: a macro-side follow edit still overwrites `enabled` wholesale. That is
 * their contract; we tolerate any subset on read rather than fight it.
 */
export function setFollowedMarkets(p: MarketPrefs, next: readonly unknown[]): MarketPrefs {
  const followed = sanitizeFollowed(next);
  const home = homeFromFollowed(followed);
  return { ...p, followed, home, enabled: withHome(p.enabled, home) };
}

/** True when this symbol is visible under the current preference. */
export function isSymbolVisible(sym: string, row: { mkt?: string; sec?: string } | undefined | null, p: MarketPrefs): boolean {
  return p.enabled.includes(marketOf(sym, row));
}

// ── search ranking ───────────────────────────────────────────────────────────────────────

/**
 * Relevance score for a symbol against a lowercased query. Higher is better; -1 means no match.
 *
 * Search was previously an unranked `Object.entries(manifest).filter(...).slice(0, 30)`, so the
 * result order was manifest insertion order and a query of "aa" could bury AA under any name
 * that happened to contain "aa". Ranking fixes that independently of personalization; the follow
 * boost then sits on top as a tiebreak that cannot outrank an exact ticker hit.
 *
 * `boosted` is a PRE-BUILT set (followedMarketSet) rather than the prefs object, so the caller
 * hoists one allocation out of a loop that runs once per manifest row.
 */
export function scoreSymbol(
  sym: string,
  row: { name?: string; zh?: string; mkt?: string; sec?: string },
  ql: string,
  boosted?: ReadonlySet<MarketId> | null,
): number {
  const s = sym.toLowerCase();
  const name = (row.name || "").toLowerCase();
  const zh = row.zh || "";

  let base: number;
  if (s === ql) base = 1000;                              // exact ticker
  else if (s.startsWith(ql)) base = 800 - Math.min(s.length - ql.length, 50);   // ticker prefix, shorter wins
  else if (name.startsWith(ql)) base = 600;               // name prefix
  else if (zh && zh.startsWith(ql)) base = 600;
  else if (s.includes(ql)) base = 400;                    // ticker substring
  else if (name.includes(ql)) base = 200;                 // name substring
  else if (zh && zh.includes(ql)) base = 200;
  else return -1;

  // Followed-market boost: +60 is smaller than the gap between any two match tiers (the tightest
  // gap is 400 → 200), so a followed-market substring hit can never outrank a foreign exact-ticker
  // hit. Personalization reorders ties; it does not override what the user literally typed.
  // Every followed market gets the SAME boost — following HK and the US promotes both.
  if (boosted && boosted.size && boosted.has(marketOf(sym, row))) base += 60;
  return base;
}

/**
 * The display name for a manifest row in the ACTIVE UI language.
 *
 * Rows carry both an English `name` and, for the names that have one, a Chinese `zh`. Every
 * surface used to render `zh || name`, which unconditionally preferred Chinese — so an English
 * user saw "WTI原油" where the row plainly carried "WTI Crude Oil", and the same for every
 * A-share and HK name. The pick is by language, with the other language as the fallback so a
 * row that carries only one of the two still shows something rather than a blank.
 *
 * Pure and hook-free so it can be shared by client components (which pass useLang()'s value)
 * and by imperative code reading the <html data-lang> attribute.
 */
export function displayName(
  row: { name?: string | null; zh?: string | null } | null | undefined,
  lang: string,
): string {
  if (!row) return "";
  const en = row.name || "";
  const zh = row.zh || "";
  return lang === "zh" ? (zh || en) : (en || zh);
}
