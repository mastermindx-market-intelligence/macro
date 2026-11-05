// fund.ts — TS contracts + client getters for the fundamentals / options / transcript files
// (BUILD-SPEC §1 + §3.1). SINGLE AUTHOR: lane FE1a.
//
//   - Types mirror the frozen §1 contracts EXACTLY (quote_currency + stmt_currency, 2-period
//     estimates, gzip transcripts).
//   - getFund/getOpts route through dataCache (dedupes with the chart's inflight fetch) BUT add a
//     local negative-cache (JUDGE FIX: dataCache deletes the key on !r.ok, so long-tail symbols
//     would re-404 on every render — we remember misses for 10 min).
//   - getTx fetches the gzipped per-call file and inflates via DecompressionStream("gzip").
//   - getBars re-exports dataCache's OHLC getter so rail widgets share the chart's fetch.

import { getJSON, getOhlc } from "./dataCache";

// ─────────────────────────────────────────────────────────────────────────────
// §1.1  <SYM>.fund.json — mastermind.fund/v1
// ─────────────────────────────────────────────────────────────────────────────

export type NumArr = (number | null)[];

export interface FundProfile {
  website: string | null;
  employees: number | null;
  sector: string | null;
  industry: string | null;
  description: string | null;
  founded: string | null;
  hq: string | null;
}

export interface FundStats {
  mktcap: number | null;
  shares_out: number | null;
  float_shares: number | null;
  inst_pct: number | null;
  insider_pct: number | null;
  beta: number | null;
  num_holders: number | null;
}

export interface IncomeBlock {
  revenue: NumArr;
  cogs: NumArr;
  gross_profit: NumArr;
  opex: NumArr;
  op_income: NumArr;
  nonop_income: NumArr;
  pretax_income: NumArr;
  taxes: NumArr;
  net_income: NumArr;
  eps_basic: NumArr;
  eps_diluted: NumArr;
  ebitda: NumArr;
}

export interface BalanceBlock {
  assets: NumArr;
  assets_st: NumArr;
  assets_lt: NumArr;
  liabilities: NumArr;
  liab_st: NumArr;
  liab_lt: NumArr;
  equity: NumArr;
  debt: NumArr;
  cash: NumArr;
  net_debt: NumArr;
}

export interface CashflowBlock {
  cfo: NumArr;
  cfi: NumArr;
  cff: NumArr;
  capex: NumArr;
  fcf: NumArr;
}

export type StatementPeriodKind = "quarter" | "half_year" | "full_year" | "year_to_date";
export type StatementReportingCadence = "annual" | "quarterly" | "semiannual" | "mixed";
export type StatementNormalizationMethod =
  | "as_reported"
  | "as_reported_ytd"
  | "difference_from_prior_ytd"
  | "unavailable_missing_base";
export type StatementSourceFamily =
  | "industrial"
  | "bank"
  | "insurer"
  | "financial_services"
  /** One vendor row carries multiple complete statement formats; family-specific fields fail closed. */
  | "ambiguous"
  | "other";

export interface StatementPeriodSet {
  periods: string[]; // canonical display labels, oldest→newest (FY/Q/H/9M as applicable)
  /** Canonical period start; derived periods begin the day after their cumulative base. */
  period_start?: (string | null)[];
  /** Vendor START_DATE before normalization, retained as source evidence. */
  source_period_start?: (string | null)[];
  period_end: string[];
  /** Explicit fiscal-cycle identity; avoids grouping a March-end FY by calendar year. */
  fiscal_year?: string[];
  /** Economic duration of each displayed column. A six-month value can never silently be a Q. */
  period_kind?: StatementPeriodKind[];
  /** Q=1..4, H=1..2; null for FY/YTD. Used for comparable-period YoY without label parsing. */
  period_number?: (number | null)[];
  /** Label of the vendor row before normalization (for example H1/FY behind displayed H1/H2). */
  source_period_label?: string[];
  /** Cadence represented by this transport set. `.quarterly` remains the v1 key for compatibility. */
  reporting_cadence?: StatementReportingCadence;
  /** Whether each SOURCE flow row was cumulative YTD before the producer adapter normalized it. */
  is_cumulative?: boolean[];
  /** Per-column producer normalization receipt. Presence makes the canonical values authoritative. */
  normalization_method?: StatementNormalizationMethod[];
  /** Basis of the emitted values. Canonical HK interim artifacts are discrete_period. */
  flow_basis?: "as_reported" | "cumulative_ytd" | "discrete_period" | "mixed_period";
  source_market?: "us" | "cn" | "hk" | "ca" | "intl" | "crypto";
  source_family?: StatementSourceFamily;
  /** Evidence used when Terminal supplies a conservative family for a legacy artifact. */
  source_family_basis?: "profile_sector_absent_industrial_structure";
  /** Historical vendor family, aligned per period; a minority of issuers change schema family. */
  source_family_by_period?: StatementSourceFamily[];
  income: IncomeBlock;
  balance: BalanceBlock;
  cashflow: CashflowBlock;

  // ── deep-history provenance (OPTIONAL — added by the Massive/polygon.io backfill,
  // ingest/backfill_fund_statements_massive.py). Files emitted before that pass, and the
  // CN/HK generators, carry neither key, so every consumer must treat them as absent-by-
  // default rather than assuming the backfill ran. ──
  /**
   * Per-period source, index-aligned to `periods`: "yfinance" | "massive" |
   * "yfinance+massive" (or the CN/HK base source). Drives the coverage disclosure — a
   * "massive"-only period carries statement TOTALS but not the derived rows below.
   */
  src_by_period?: string[];
  /**
   * Contract fields the vendor payload cannot fill, by block — e.g.
   * `{income: ["ebitda"], balance: ["cash","debt","net_debt"], cashflow: ["capex","fcf"]}`.
   * These are null on vendor-only periods BY DESIGN; they are never zero-filled or
   * estimated. See lib/finStatements.vendorGapNotice.
   */
  vendor_gaps?: Record<string, string[]>;
  /**
   * Filing provenance, index-aligned to `periods`: the ISO date of the vendor filing whose
   * figures this column took, or null where no vendor row supplied a value (a yfinance-only
   * column, or a file that predates the backfill). Written by
   * `backfill_fund_statements_massive.merge_period_set` — when two filings report the same
   * fiscal label, the LATER one wins and its date lands here.
   */
  filed_by_period?: (string | null)[];
  /**
   * True where more than one distinct vendor filing was seen for that fiscal label — i.e. the
   * period has been restated. The column shows the LATEST filing's figures; this flag is what
   * lets a surface say so. Not full point-in-time: the superseded figures are not retained.
   */
  restated_by_period?: boolean[];
}

export interface FundStatements {
  /** A source gap can leave either basis unavailable; consumers must preserve that null honestly. */
  annual: StatementPeriodSet | null;
  quarterly: StatementPeriodSet | null;
}

export interface RatiosCurrent {
  pe_ttm: number | null;
  pe_fwd: number | null;
  ps: number | null;
  pb: number | null;
  ev_ebitda: number | null;
  ev_sales: number | null;
  ev_ebit: number | null;
  p_fcf: number | null;
  div_yield: number | null;
  payout: number | null;
  gross_margin: number | null;
  net_margin: number | null;
  roe: number | null;
  roa: number | null;
  debt_to_equity: number | null;
  current_ratio: number | null;
}

export interface FundRatios {
  periods: string[];
  pe: NumArr;
  ps: NumArr;
  pb: NumArr;
  pcf: NumArr;
  ev: NumArr;
  ev_ebitda: NumArr;
  current: RatiosCurrent;
}

export interface EarningsQuarter {
  period: string; // "Q3 2026"
  end: string;
  report_date: string | null; // null on synthesized tx-carrier rows (transcript with no earnings_dates row)
  eps_a: number | null;
  eps_e: number | null;
  rev_a: number | null; // null for US/HK (yfinance carries no per-quarter revenue)
  rev_e: number | null;
  surp_pct: number | null;
  tx: string | null; // defeatbeta fiscal id "2026Q3" — transcript join key; null when none
}

export interface EarningsFY {
  period: string;
  eps_a: number | null;
  eps_e: number | null;
  rev_a: number | null;
  rev_e: number | null;
  surp_pct: number | null;
}

export interface FundEarnings {
  next_date: string | null;
  next_period: string | null;
  next_eps_est: number | null;
  next_rev_est: number | null;
  q: EarningsQuarter[]; // oldest→newest, ≥8 where available
  fy: EarningsFY[];
}

export interface EstimateSeries {
  periods: string[];
  avg: NumArr;
  high: NumArr;
  low: NumArr;
  n: NumArr;
}

export interface FundEstimates {
  // JUDGE FIX: yfinance provides EXACTLY 4 rows — two forward quarters (eps_q) and two fiscal
  // years (eps_fy / rev_fy). No third year.
  eps_fy: EstimateSeries; // 0y, +1y
  rev_fy: EstimateSeries; // 0y, +1y
  eps_q: EstimateSeries; // 0q, +1q
  growth: { rev_yoy: number | null; eps_yoy: number | null };
}

export interface AnalystDist {
  strongBuy: number;
  buy: number;
  hold: number;
  sell: number;
  strongSell: number;
}

export interface FundAnalyst {
  dist: AnalystDist;
  rating_label: string | null;
  target: {
    mean: number | null;
    high: number | null;
    low: number | null;
    n: number | null;
  };
}

export interface DividendEvent {
  ex: string;
  amount: number | null;
  pay: string | null;
  type: string; // "regular" | "special" | …
}

export interface SplitEvent {
  date: string;
  ratio: string; // "4:1"
}

export interface FundDividends {
  never_paid: boolean;
  yield_ttm: number | null;
  payout_ratio: number | null;
  events: DividendEvent[]; // full history oldest→newest
  splits: SplitEvent[];
}

export interface InstHolder {
  name: string;
  pct: number | null;
  value: number | null;
}

export interface FundOwnership {
  free_float_pct: number | null;
  closely_held_pct: number | null;
  top_inst: InstHolder[]; // ≤10
}

export interface FundGuidance {
  type: string; // e.g. "预增"
  chg_min: number | null;
  chg_max: number | null;
  period: string;
}

export interface SegmentSeries {
  periods: string[];
  series: { name: string; values: NumArr }[];
}

export interface FundSegments {
  by_source: SegmentSeries | null;
  by_country: SegmentSeries | null;
}

export interface Fund {
  schema: string; // "mastermind.fund/v1"
  ticker: string;
  asof: string;
  quote_currency: string; // trading currency (price/mktcap/dividends)
  stmt_currency: string | null; // financial-reporting currency (statements/estimates); null = unknown
  src: {
    statements: string;
    estimates: string | null;
    dividends: string;
  };
  profile: FundProfile;
  stats: FundStats;
  statements: FundStatements;
  ratios: FundRatios;
  earnings: FundEarnings;
  estimates: FundEstimates | null; // null for CN
  analyst: FundAnalyst | null; // null for CN
  dividends: FundDividends;
  ownership: FundOwnership;
  guidance: FundGuidance | null; // CN only
  segments: FundSegments | null; // deferred (R6)
}

// ─────────────────────────────────────────────────────────────────────────────
// §1.2  <SYM>.opts.json — mastermind.opts/v1
// ─────────────────────────────────────────────────────────────────────────────

export interface OptsTenor {
  label: string; // "1W" | "2W" | "1M" | "2M" | "3M" | "6M" | "9M" | "1Y"
  dte: number;
  expiry: string;
  iv: number; // raw decimal (0.412 = 41.2%) — frontend ×100 at render
}

export interface OptsSmile {
  expiry: string;
  dte: number;
  strikes: number[];
  iv: number[]; // raw decimals, aligned to strikes
  delta_call: number[];
}

export interface Opts {
  schema: string; // "mastermind.opts/v1"
  ticker: string;
  asof: string;
  spot: number;
  term: OptsTenor[];
  smile: OptsSmile;
  iv_source: string; // "yfinance" | "cboe"
}

// ─────────────────────────────────────────────────────────────────────────────
// §1.2b  insider power — public/data/<SYM>.insider.json
// Quality-weighted Form-4 Insider Power score (0..100, 50 = neutral) + the
// buy/sell-volume series and recent open-market trades. The SCORING is owned by
// the Macro pipeline (engine/insider_power.py) and exported per-ticker — the
// Terminal is display-only and never re-derives it. Display / informational,
// not investment advice.
// ─────────────────────────────────────────────────────────────────────────────

/** One month of aggregated open-market insider dollar/share volume. */
export interface InsiderMonth {
  month: string; // "YYYY-MM"
  buy_usd: number;
  sell_usd: number;
  buy_shares: number;
  sell_shares: number;
  net_usd: number;
}

/** One recent open-market Form-4 transaction (newest-first in `trades`). */
export interface InsiderTrade {
  date: string; // filing date "YYYY-MM-DD" (the date it became public)
  trade_date: string | null;
  code: "P" | "S"; // P = open-market purchase, S = sale
  side: "buy" | "sell";
  role: string; // "Top exec" | "Officer" | "Director" | "10% owner" | "Insider"
  title: string; // raw Form-4 reporter title
  shares: number | null;
  price: number | null;
  usd: number | null;
  weight: number; // role conviction weight applied by the engine
}

export interface Insider {
  ticker: string;
  asof: string; // "YYYY-MM-DD"
  window_days: number;
  /** Insider Power score 0..100 (50 = neutral, ≥60 buy tilt, ≤40 sell tilt). */
  score: number;
  /** Display signal from net-dollar flow: "BUY" | "SELL" | "NEUTRAL". */
  signal: "BUY" | "SELL" | "NEUTRAL";
  /** Confidence from flow-vs-score agreement: "High" | "Medium" | "Low" | "None". */
  confidence: string;
  /** Human breakdown (e.g. "SELL SIGNAL — Low Confidence: contradicted by …"). */
  analysis: string;
  insider_buy: boolean; // score ≥ 60
  insider_sell: boolean; // score ≤ 40
  buyers: number; // distinct insiders buying in the window
  sellers: number; // distinct insiders selling in the window
  buy_usd: number;
  sell_usd: number;
  net_usd: number;
  buy_shares: number;
  sell_shares: number;
  series: InsiderMonth[]; // oldest→newest, trailing ~24 months
  trades: InsiderTrade[]; // newest→oldest, capped

  // ── v2 posture fields (OPTIONAL — added by engine/insider_power.py scoring v2;
  // today's exported payloads do NOT carry them, so the Terminal degrades
  // gracefully when they are absent). Semantics only DE-ESCALATE: the existing
  // engine-owned `signal`/`confidence` keys stay authoritative and the Terminal
  // never re-derives or escalates them. `routine_only` marks the null state
  // (window is routine, spread-out, baseline-sized selling only); the engine
  // sets `signal="NEUTRAL"` alongside it. See the Wave-1 spec "Insider scoring
  // v2" and the display shim in InsiderPage. ──
  /** True when the window is routine, spread-out, baseline-sized selling only. */
  routine_only?: boolean;
  /** Plain-word reason for the posture (EN), e.g. "Routine equity-comp selling…". */
  posture_reason?: string;
  /** Plain-word reason for the posture (ZH). */
  posture_reason_zh?: string;
  /** Age in days of the most recent open-market trade (drives the recency gate). */
  last_trade_age_d?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// §1.3  transcripts — public/data/tx/<SYM>/<ID>.json.gz
// ─────────────────────────────────────────────────────────────────────────────

export interface TxSegment {
  speaker: string;
  role: string;
  text: string;
}

export interface Transcript {
  schema: "mastermind.tx/v1";
  ticker: string;
  id: string; // "2026Q3"
  period: string; // "Q3 FY2026"
  date: string | null;
  title: string;
  segments: TxSegment[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Bars (chart OHLC) — shared shape for rail widgets / techRating / realizedVol
// ─────────────────────────────────────────────────────────────────────────────

export interface Bar {
  time: string | number;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Getters
// ─────────────────────────────────────────────────────────────────────────────

// Local negative-cache: sym-key → epoch-ms until which a miss is remembered.
const NEG_TTL = 10 * 60 * 1000; // 10 min
const negCache = new Map<string, number>();

function negHit(key: string): boolean {
  const until = negCache.get(key);
  if (until == null) return false;
  if (Date.now() >= until) {
    negCache.delete(key);
    return false;
  }
  return true;
}

function negMark(key: string): void {
  negCache.set(key, Date.now() + NEG_TTL);
}

const LEGACY_FINANCIAL_SECTORS = new Set(["financial services", "financials"]);

function withFinancialFamilyFallback(set: StatementPeriodSet): StatementPeriodSet {
  // Explicit producer taxonomy, especially a historical by-period receipt, always wins.
  if (set.source_family != null || (set.source_family_by_period?.length ?? 0) > 0) return set;
  // `Financial Services` is a broad profile sector: payment networks and exchanges can carry a
  // conventional cost-of-revenue / gross-profit statement. Any sourced structural value keeps
  // that set industrial-compatible; only a wholly absent industrial structure fails closed.
  const hasIndustrialStructure = [set.income?.cogs, set.income?.gross_profit]
    .some((values) => values?.some((value) => value != null && Number.isFinite(value)));
  if (hasIndustrialStructure) return set;
  return {
    ...set,
    source_family: "financial_services",
    source_family_basis: "profile_sector_absent_industrial_structure",
  };
}

/**
 * Legacy US artifacts predate statement-family metadata. Combine their sourced profile sector
 * with the statement's own structural evidence to fail closed for JPM/BAC-style statements while
 * preserving V/MA/exchange-style industrial rows. This is deliberately a presentation
 * classification, not an attempt to coerce bank/insurer statements into one industrial schema,
 * and it never overrides producer-owned taxonomy.
 */
export function applyLegacyStatementFamilyFallback(fund: Fund): Fund {
  // Both sector vocabularies the profile producer has emitted: the Yahoo-style "Financial
  // Services" and the GICS "Financials" that live JPM.fund.json carries (verified 2026-10-11 —
  // under the old single-name match the live JPM statement rendered as industrial "Revenue").
  if (!LEGACY_FINANCIAL_SECTORS.has(fund.profile?.sector?.trim().toLowerCase() ?? "")) return fund;
  // Some valid source-gap artifacts carry a null annual or interim set even though the frozen
  // v1 TypeScript shape predates that reality. Classify only sets that actually exist.
  const annual = fund.statements?.annual;
  const quarterly = fund.statements?.quarterly;
  if (!annual && !quarterly) return fund;
  const nextAnnual = annual ? withFinancialFamilyFallback(annual) : annual;
  const nextQuarterly = quarterly ? withFinancialFamilyFallback(quarterly) : quarterly;
  if (nextAnnual === annual && nextQuarterly === quarterly) return fund;
  return {
    ...fund,
    statements: {
      ...fund.statements,
      ...(nextAnnual ? { annual: nextAnnual } : {}),
      ...(nextQuarterly ? { quarterly: nextQuarterly } : {}),
    },
  };
}

/** getFund — <SYM>.fund.json, negative-cached against long-tail 404 storms. */
export async function getFund(sym: string): Promise<Fund | null> {
  const key = "fund:" + sym;
  if (negHit(key)) return null;
  const data = (await getJSON("/data/" + sym + ".fund.json")) as Fund | null;
  if (!data) {
    negMark(key);
    return null;
  }
  return applyLegacyStatementFamilyFallback(data);
}

/** getOpts — <SYM>.opts.json, negative-cached (most symbols are not optionable). */
export async function getOpts(sym: string): Promise<Opts | null> {
  const key = "opts:" + sym;
  if (negHit(key)) return null;
  const data = (await getJSON("/data/" + sym + ".opts.json")) as Opts | null;
  if (!data) {
    negMark(key);
    return null;
  }
  return data;
}

/** getInsider — <SYM>.insider.json, negative-cached (most names lack recent Form-4 activity). */
export async function getInsider(sym: string): Promise<Insider | null> {
  const key = "insider:" + sym;
  if (negHit(key)) return null;
  const data = (await getJSON("/data/" + sym + ".insider.json")) as Insider | null;
  if (!data) {
    negMark(key);
    return null;
  }
  return data;
}

const TX_ID_RE = /^\d{4}Q[1-4]$/;
const TX_TICKER_RE = /^[A-Z0-9.^-]+$/;

export function transcriptBodyUrl(sym: string, id: string): string | null {
  const ticker = sym.trim().toUpperCase();
  if (!TX_TICKER_RE.test(ticker) || !TX_ID_RE.test(id)) return null;
  return `/data/tx/${ticker}/${id}.json.gz`;
}

/** Strictly validate an untrusted transcript body before a component reads it. */
export function normalizeTranscript(raw: unknown, expectedSym: string, expectedId: string): Transcript | null {
  if (!raw || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;
  const ticker = expectedSym.trim().toUpperCase();
  if (
    obj.schema !== "mastermind.tx/v1"
    || obj.ticker !== ticker
    || obj.id !== expectedId
    || typeof obj.period !== "string"
    || !obj.period.trim()
    || typeof obj.title !== "string"
    || !obj.title.trim()
    || (obj.date !== null && typeof obj.date !== "string")
    || !Array.isArray(obj.segments)
  ) return null;
  const segments: TxSegment[] = [];
  for (const rawSegment of obj.segments) {
    if (!rawSegment || typeof rawSegment !== "object") return null;
    const segment = rawSegment as Record<string, unknown>;
    if (
      typeof segment.speaker !== "string"
      || typeof segment.role !== "string"
      || typeof segment.text !== "string"
      || !segment.text.trim()
    ) return null;
    segments.push({ speaker: segment.speaker, role: segment.role, text: segment.text });
  }
  return {
    schema: "mastermind.tx/v1",
    ticker,
    id: expectedId,
    period: obj.period.trim(),
    date: obj.date as string | null,
    title: obj.title.trim(),
    segments,
  };
}

/** Fetch, inflate, and validate a transcript without a sticky failure cache. */
export async function getTx(
  sym: string,
  id: string,
  options: { retryNonce?: number } = {},
): Promise<Transcript | null> {
  const baseUrl = transcriptBodyUrl(sym, id);
  if (!baseUrl) return null;
  const url = options.retryNonce ? `${baseUrl}?retry=${options.retryNonce}` : baseUrl;
  try {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok || !r.body) return null;
    // DecompressionStream is standard in modern browsers; guard for older ones.
    const DS = globalThis.DecompressionStream;
    if (typeof DS !== "function") return null;
    const stream = r.body.pipeThrough(new DS("gzip"));
    const text = await new Response(stream).text();
    return normalizeTranscript(JSON.parse(text), sym, id);
  } catch {
    return null;
  }
}

/**
 * getBars — re-export the chart's OHLC getter, normalized to Bar[].
 * The raw file is `{bars: [[date,o,h,l,c,v], ...]}`; we map to the object shape rail widgets use.
 * Shares dataCache's inflight fetch with ChartPanel (never a third raw fetch).
 */
export async function getBars(sym: string): Promise<Bar[]> {
  const raw = await getOhlc(sym);
  const rows: any[] = raw?.bars ?? [];
  if (!Array.isArray(rows)) return [];
  return rows.map((b) =>
    Array.isArray(b)
      ? { time: b[0], o: b[1], h: b[2], l: b[3], c: b[4], v: b[5] }
      : { time: b.time ?? b.t, o: b.o, h: b.h, l: b.l, c: b.c, v: b.v }
  );
}

/** Test/HMR hook — clear the negative cache. */
export function _clearNegCache(): void {
  negCache.clear();
}
