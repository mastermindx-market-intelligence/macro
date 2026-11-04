/**
 * companySearchContext.ts — identity context for P12.T25 alternate listings (BABA vs 9988.HK).
 *
 * WHY A MODULE
 *     Company search can select several listings of one company. The preview card and the
 *     /analysis destination both need the same three facts about the selected listing — the
 *     canonical symbol, where the user's typed query is carried, and which venue/currency the
 *     AUTHORITATIVE row states — and both must fail closed the same way when a row is stale,
 *     malformed, or belongs to a different ticker. SearchModal's Row and searchCategory.ts own
 *     the search dialog itself; this module owns only the selection→destination identity facts,
 *     where they can be tested without mounting the dialog.
 *
 * FAIL-CLOSED RULES (P12.T25)
 *     - Exact canonical tickers. `BABA` and `9988.HK` are distinct listings; a fund row whose
 *       `ticker` is not EXACTLY the requested symbol never answers a question about it. A
 *       stale/cross-listed row therefore degrades to "unknown" instead of mislabelling.
 *     - quote_currency is the trading currency. stmt_currency is the financial-reporting
 *       currency and is NEVER read here (a CNY statement currency must not relabel USD-traded
 *       BABA shares).
 *     - Unknown stays unknown. No exchange↔currency inference, no catalog, no mapping table:
 *       a manifest row without an explicit `sec: "Equities"` and a usable `mkt` answers null.
 *
 * The exported key annotates the existing browser history entry. It creates no persistent
 * storage bucket, route catalog, source registry or instrument alias.
 */

import { normalizeAnalysisSymbol } from "./analysisSymbol";

/** A committed company-search selection: the canonical symbol plus the query typed to find it. */
export type CompanySearchSelection = { symbol: string; query: string };

/** Context carried by the existing origin history entry for browser Back. */
export const COMPANY_SEARCH_HISTORY_KEY = "mmxCompanySearch";

/** A typed query longer than this is rejected, not silently truncated (the user is retyping). */
const MAX_QUERY_CHARS = 160;

/**
 * Plain-object gate shared by every reader below. JSON-produced payloads (manifest, fund file)
 * and React-held state objects are plain; arrays and class instances are not the shapes any
 * producer here documents, so they answer null rather than being probed for fields.
 */
function asPlainRecord(value: unknown): Record<string, unknown> | null {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return null;
  const proto: unknown = Object.getPrototypeOf(value);
  if (proto !== Object.prototype && proto !== null) return null;
  return value as Record<string, unknown>;
}

/** C0 control characters and DEL — clipboard/broker artifacts, never a user's typed query. */
function hasControlCharacter(value: string): boolean {
  for (const ch of value) {
    const code = ch.codePointAt(0) ?? 0;
    if (code < 0x20 || code === 0x7f) return true;
  }
  return false;
}

/**
 * normalizeCompanySearchQuery — the query as the search context will carry it.
 *
 * Accepts strings only; trims surrounding whitespace; allows the empty string (an empty query
 * is a real selection — the browse lists, not a typo); rejects >160 trimmed chars (the caller
 * re-asks, nothing is silently cut) and anything containing a control character. Non-strings
 * (null from an absent URL param, numbers, arrays) are null, never coerced.
 */
export function normalizeCompanySearchQuery(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const query = value.trim();
  if (query.length > MAX_QUERY_CHARS) return null;
  if (hasControlCharacter(query)) return null;
  return query;
}

/** The only fields a selection carries; anything else is not this module's authority. */
const SELECTION_FIELDS = new Set(["symbol", "query"]);

/**
 * readCompanySearchSelection — validate a remembered/prop-passed selection.
 *
 * Plain objects only (no arrays, no class instances); no extra authority fields, so a shape
 * that grew a third field in some other producer is rejected here instead of trusted; the
 * symbol must already be CANONICAL — `normalizeAnalysisSymbol(symbol) === symbol` — so `baba`
 * or a padded string never re-enters the system as if it had been chosen; and the query must
 * normalize. Anything else is null: callers show the generic "selected in company search"
 * rather than a quote of a value that was never typed.
 */
export function readCompanySearchSelection(value: unknown): CompanySearchSelection | null {
  const record = asPlainRecord(value);
  if (!record) return null;
  for (const key of Object.keys(record)) {
    if (!SELECTION_FIELDS.has(key)) return null;
  }
  const symbol = record.symbol;
  if (typeof symbol !== "string") return null;
  const canonical = normalizeAnalysisSymbol(symbol);
  if (canonical === null || canonical !== symbol) return null;
  const query = normalizeCompanySearchQuery(record.query);
  if (query === null) return null;
  return { symbol: canonical, query };
}

/**
 * companySearchAnalysisHref — the /analysis destination for a selection.
 *
 * `/analysis?symbol=<full ticker>&company_query=<typed query>`, built through URLSearchParams so
 * the query travels encoded (CJK queries, `&`, `#`). An empty query still emits `company_query=`
 * so the destination can distinguish "arrived from search with no query" from "arrived with a
 * stripped param" (readCompanySearchQuery answers "" for the former, null for the latter).
 * Invalid input → null; callers then link to plain `/analysis` rather than a malformed URL.
 */
export function companySearchAnalysisHref(selection: unknown): string | null {
  const chosen = readCompanySearchSelection(selection);
  if (!chosen) return null;
  const params = new URLSearchParams({ symbol: chosen.symbol, company_query: chosen.query });
  return `/analysis?${params.toString()}`;
}

/**
 * readCompanySearchQuery — the typed query as it arrives at the /analysis destination.
 *
 * Exactly ONE `company_query` param may be present: absent → null (not from search), duplicated
 * → null (a hand-built or hostile URL; never guess which one wins), malformed → null. The empty
 * string is a valid answer — the user searched, then browsed/selected without typing.
 */
export function readCompanySearchQuery(params: URLSearchParams): string | null {
  const values = params.getAll("company_query");
  if (values.length !== 1) return null;
  return normalizeCompanySearchQuery(values[0]);
}

/**
 * tradingCurrencyFor — the listing's trading currency, from the fund row ONLY when it is
 * unambiguously about THIS symbol.
 *
 * The fund row's `ticker` must equal the requested canonical symbol exactly (`9988.HK`'s row
 * never answers for `BABA`); `quote_currency` must be a 3-letter uppercase code. The statement
 * currency is deliberately unreachable — a CN filer's `stmt_currency: "CNY"` says nothing about
 * what its US-listed shares trade in. Wrong ticker, missing/odd currency, non-object: null,
 * and the surface says "trading currency unavailable" instead of guessing.
 */
export function tradingCurrencyFor(value: unknown, symbol: string): string | null {
  const canonical = normalizeAnalysisSymbol(symbol);
  if (canonical === null || canonical !== symbol) return null;
  const fund = asPlainRecord(value);
  if (!fund) return null;
  if (fund.ticker !== symbol) return null;
  const quote = fund.quote_currency;
  if (typeof quote !== "string" || !/^[A-Z]{3}$/.test(quote)) return null;
  return quote;
}

/**
 * venueFor — the source venue, from the public manifest row for THIS exact symbol.
 *
 * Reads `symbols[symbol]` (SymbolPicker's `Manifest` shape — the raw `/data/manifest.json`
 * document), requires the row's explicit `sec === "Equities"` (the same company-search class
 * rule as searchCategory.isCompanySearchRow; nothing is inferred from the ticker), and returns
 * `mkt` verbatim when it is a non-empty ≤80-char string with no control characters. Unknown
 * symbol, non-equity class, malformed venue: null — the strip then says the venue is
 * unavailable rather than printing a market the manifest never stated.
 */
export function venueFor(value: unknown, symbol: string): string | null {
  const canonical = normalizeAnalysisSymbol(symbol);
  if (canonical === null || canonical !== symbol) return null;
  const manifest = asPlainRecord(value);
  if (!manifest) return null;
  const symbols = asPlainRecord(manifest.symbols);
  if (!symbols) return null;
  const row = asPlainRecord(symbols[symbol]);
  if (!row) return null;
  if (row.sec !== "Equities") return null;
  const mkt = row.mkt;
  if (typeof mkt !== "string" || !mkt || mkt.length > 80) return null;
  if (hasControlCharacter(mkt)) return null;
  return mkt;
}
