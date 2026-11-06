/**
 * finStatements — pure helpers for the deep statement history that the Massive
 * (polygon.io) backfill adds to `<SYM>.fund.json`.
 *
 * Why a lib module rather than logic inside the fin/ pages: vitest only collects
 * `lib/__tests__/**` (see terminal/vitest.config.ts), so anything that needs a test lives
 * here and the pages stay presentational.
 *
 * Two jobs:
 *   1. COVERAGE HONESTY. The vendor's XBRL payload carries statement TOTALS but not
 *      EBITDA / cash / total debt / capex / free cash flow (`statements.<tf>.vendor_gaps`,
 *      written by ingest/massive_financials.py). Those rows are null on backfilled periods.
 *      `vendorGapNotice()` turns that into the plain-word disclosure the Statements tab
 *      shows, so a dash is explained rather than read as "zero" or "we lost the data".
 *   2. REVENUE HISTORY. The Revenue tab had no total-revenue series at all — it showed a
 *      segment empty-state plus sell-side estimates. `revenueHistory()` derives the long
 *      series (with YoY) from the statements block that now goes back to 2009.
 *
 * Everything here degrades on pre-backfill files: the new fields are optional, so a symbol
 * whose fund.json predates this pass simply reports no gaps and a shorter history.
 */
import type { Fund, StatementPeriodSet } from "./fund";
import { comparablePeriodChanges, incomeView } from "./finStatementMath";

/** Contract field keys the vendor payload cannot fill, by statement block. */
export type VendorGaps = Record<string, string[]>;

/**
 * EN/ZH labels for the gapped fields. These MUST read identically to the row labels in
 * StatementsPage.buildRows — a disclosure that names rows the user cannot find is worse
 * than none, so both sides read from this one table.
 */
const GAP_LABELS: Record<string, [string, string]> = {
  ebitda: ["EBITDA", "EBITDA"],
  cash: ["Cash & equivalents", "现金及等价物"],
  debt: ["Total debt", "总债务"],
  net_debt: ["Net debt", "净债务"],
  capex: ["Capital expenditure", "资本支出"],
  fcf: ["Free cash flow", "自由现金流"],
};

/** True when this period's values came only from the deep-history vendor backfill. */
function isVendorOnly(src: string | undefined): boolean {
  return !!src && src === "massive";
}

export interface GapNotice {
  /** Localised row names that are blank across the backfilled span. */
  rows: string[];
  /** Label of the OLDEST period that still carries the full row set (e.g. "2021"). */
  fullFrom: string | null;
  /** Number of periods carrying the vendor-only (totals-only) shape. */
  vendorPeriods: number;
}

/**
 * Which rows are blank on the deep-history periods, and from which period the full row set
 * resumes. Returns null when there is nothing to disclose — no backfilled periods, or a
 * file that predates the backfill and therefore has no `vendor_gaps`.
 *
 * `block` scopes the notice to the statement the user is looking at: the Statements tab
 * shows one statement at a time, and listing cash-flow gaps under the income statement
 * would send the reader hunting for rows that are not on screen.
 */
export function vendorGapNotice(
  set: StatementPeriodSet | null | undefined,
  block: "income" | "balance" | "cashflow",
  zh: boolean,
): GapNotice | null {
  if (!set) return null;
  const gaps = set.vendor_gaps?.[block] ?? [];
  if (gaps.length === 0) return null;

  const srcs = set.src_by_period ?? [];
  const periods = set.periods ?? [];
  if (srcs.length === 0) return null;

  let vendorPeriods = 0;
  let fullFrom: string | null = null;
  for (let i = 0; i < periods.length; i++) {
    if (isVendorOnly(srcs[i])) vendorPeriods++;
    else if (fullFrom === null) fullFrom = periods[i] ?? null;
  }
  if (vendorPeriods === 0) return null;

  const rows = gaps.map((f) => GAP_LABELS[f]?.[zh ? 1 : 0] ?? f).filter(Boolean);
  if (rows.length === 0) return null;
  return { rows, fullFrom, vendorPeriods };
}

/** Span summary for a period set: count + first/last label. Null when empty. */
export function historySpan(
  set: StatementPeriodSet | null | undefined,
): { count: number; first: string; last: string } | null {
  const periods = set?.periods ?? [];
  if (periods.length === 0) return null;
  return { count: periods.length, first: periods[0], last: periods[periods.length - 1] };
}

export interface RevenuePoint {
  period: string;
  value: number | null;
  /** Year-over-year change in percent; null at the series start or across a null hole. */
  yoy: number | null;
}

/**
 * Total-revenue history with YoY, oldest→newest.
 *
 * Year-over-year comparison follows the producer's fiscal identity: the same period kind and
 * period number in the prior fiscal year. That works for quarter, half-year and mixed-cadence
 * issuers without inventing a four-column lag. Legacy artifacts with no identity metadata retain
 * the old annual/quarterly fallback. Null periods keep their slot and yield a null comparison.
 *
 * NORMALIZATION: revenue comes from `finStatementMath.incomeView`, the same call the
 * Statements tab makes, NOT from `set.income.revenue` raw. Reading it raw was a live
 * cross-tab contradiction — a cumulative-YTD (CN) name showed 1314.42 here and 307.74 on
 * Statements for the same quarter, because only one of the two tabs differenced. One
 * normalization policy, both consumers.
 */
export function revenueHistory(
  fund: Fund | null,
  timeframe: "annual" | "quarterly" = "annual",
): RevenuePoint[] {
  const set = timeframe === "annual" ? fund?.statements?.annual : fund?.statements?.quarterly;
  const view = incomeView(fund?.ticker, set, timeframe);
  const periods = view.periods;
  const revenue = view.income.revenue;
  if (periods.length === 0) return [];
  const changes = comparablePeriodChanges(revenue, set, timeframe);
  return periods.map((period, i) => {
    const value = revenue[i] ?? null;
    return { period, value, yoy: changes[i] ?? null };
  });
}

/** Count of points carrying a real revenue figure — drives the "enough to plot" check. */
export function revenueCoverage(points: RevenuePoint[]): number {
  return points.reduce((n, p) => n + (p.value != null ? 1 : 0), 0);
}
