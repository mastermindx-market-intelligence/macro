/**
 * finStatementMath — the statement arithmetic every financials surface shares.
 *
 * WHY THIS MODULE EXISTS (two reasons, both defects):
 *
 *  1. NORMALIZATION MUST BE MARKET-AWARE, NOT PATTERN-MATCHED. Quarterly income used to be
 *     routed through a cumulative-YTD detector that looked only at the VALUES: if revenue
 *     rose in 2 of 3 quarters across 2 of the trailing 3 fiscal years, the whole income
 *     statement was differenced. That heuristic was dormant only because it also required
 *     ≥8 quarterly periods and every US name carried exactly 5. The Massive backfill takes
 *     US names to ~69 quarters, at which point ordinary secular growth (NVDA, MSFT — live
 *     revenue is strictly rising) satisfies the pattern and the tab prints as-reported
 *     69.6B as 4.0B on every income row.
 *
 *     US filings on this path are discrete-quarter BY CONSTRUCTION: the 10-Q income
 *     statement reports the quarter, and the vendor's XBRL rows carry the same. So the gate
 *     is now the issuer's MARKET, not the shape of its numbers — differencing is
 *     structurally unreachable outside the markets that genuinely file cumulative
 *     year-to-date interims. No amount of growth can turn it on for a US filer.
 *
 *  2. ONE SERIES, EVERY SURFACE. The mini bar chart read `set.income.*` raw while the table
 *     read a differenced copy, so the same quarter could plot at 82.9B and print at 1.6B.
 *     `incomeView()` is now the single normalization point: the chart, the table, and the
 *     Revenue tab's history all read the SAME arrays out of it (reference-identical — see
 *     `incomeChartValues`), so they cannot drift apart again.
 *
 * Pure, dependency-light, and in `lib/` on purpose: vitest only collects
 * `lib/__tests__/**` (terminal/vitest.config.ts), so component-private math is untestable
 * by construction. Anything here can be pinned; anything left in the page cannot.
 */
import type {
  IncomeBlock,
  NumArr,
  StatementPeriodSet,
  StatementReportingCadence,
  StatementSourceFamily,
} from "./fund";
import { marketOf, type MarketId } from "./markets";

export type StatementMarket = MarketId;

/**
 * Markets whose INTERIM statements are filed cumulative year-to-date, so a "quarter" column
 * holds the year so far and only differencing recovers the discrete quarter.
 *
 * Mainland-China (tushare, `gen_fund_cn.py`) and Hong Kong (akshare, `gen_fund_hk.py`)
 * report this way. US filings (yfinance + the Massive/XBRL backfill), Canada, and the
 * international tail report the period itself. Adding a market here is a deliberate act:
 * it turns differencing ON for every income row of every name in that market.
 *
 * HK MEASURED, NOT ASSUMED (2026-08-08). The entry above first shipped as a prose claim, and
 * the obvious objection is that some HK issuers — Tencent being the stock example — publish
 * DISCRETE quarters in their own results announcements, while `isCumulativeShape` is satisfied
 * by any strictly-rising series. Checked against the 2,798 real cached akshare payloads that
 * feed this contract: 98.7% of 35,984 fiscal years are monotone non-decreasing, the
 * annual÷earliest-interim ratio is ≈2x for 80.7% and ≈4x for 12.5% against only 3.4% at ≈1x,
 * and just 3 names of 2,567 look discrete. The objection inverts on contact with the data —
 * Tencent's announcements are discrete, but the rows this feed carries are the cumulative
 * ladder, and differencing is what RECOVERS the published quarter (0700.HK Q3 2024: as-filed
 * 487.81B is the nine-month total; differenced 167.19B is the quarter Tencent reported).
 * Pinned end-to-end in lib/__tests__/hkCumulativeReporting.test.ts.
 *
 * Current HK artifacts carry producer-owned fiscal identity and normalized additive flows. This
 * market gate remains only as a compatibility fallback for older HK/CN artifacts with no period
 * metadata; explicit producer receipts always win and are never differenced twice.
 */
export const CUMULATIVE_YTD_MARKETS: readonly MarketId[] = ["cn", "hk"] as const;
const CUMULATIVE_SET = new Set<string>(CUMULATIVE_YTD_MARKETS);

/**
 * The market whose filing conventions govern a symbol's statements.
 *
 * Delegates to `markets.marketOf` — the same classification search and the data-fetch router
 * use — rather than growing a third copy of the suffix table. An unknown or empty symbol
 * resolves to "us", which is the SAFE default here: "us" never differences.
 */
export function statementMarket(sym: string | null | undefined): MarketId {
  return marketOf((sym ?? "").trim());
}

/** True when this symbol's market files cumulative year-to-date interim statements. */
export function filesCumulativeQuarters(sym: string | null | undefined): boolean {
  return CUMULATIVE_SET.has(statementMarket(sym));
}

/**
 * Shape check for a cumulative year-to-date quarterly array — the SECOND gate, never the
 * first. Reached only for markets in `CUMULATIVE_YTD_MARKETS`, where it exists to catch a
 * feed that has already been differenced upstream (differencing twice is as wrong as not
 * differencing at all) rather than to discover cumulative reporting on its own.
 *
 * Within each of the trailing 3 fiscal years (4-period blocks from the newest end), count
 * the non-decreasing Q→Q transitions; 2 of 3 in at least 2 years reads as cumulative.
 */
export function isCumulativeShape(vals: NumArr | undefined): boolean {
  if (!vals || vals.length < 8) return false;
  let cumulativeYears = 0;
  const n = vals.length;
  for (let yr = 0; yr < 3; yr++) {
    const base = n - (yr + 1) * 4;
    if (base < 0) break;
    const q = [vals[base], vals[base + 1], vals[base + 2], vals[base + 3]];
    if (q.some((v) => v == null)) continue;
    let risingCount = 0;
    for (let i = 1; i < 4; i++) {
      if ((q[i] as number) >= (q[i - 1] as number)) risingCount++;
    }
    if (risingCount >= 2) cumulativeYears++;
  }
  return cumulativeYears >= 2;
}

/**
 * Fiscal-year token from a period label, for detecting a year boundary the labels cross
 * without a "Q1" column. Both label shapes in the contract end in the year:
 * "Q1 2023" (CN/HK generators) → "2023", "Q3 '26" (US backfill) → "26". Compared for
 * equality only — never parsed into a date — so the two shapes never have to agree.
 */
function fiscalYearToken(label: string | undefined): string | null {
  const m = /(\d{2,4})\s*$/.exec(label ?? "");
  return m ? m[1] : null;
}

/**
 * Cumulative year-to-date quarters → discrete quarters, oldest→newest.
 *
 * A cell is emitted ONLY when its cumulative base is known:
 *   • label starts with "Q1"            → as-is (Q1 IS the first quarter of the fiscal year)
 *   • same fiscal year as the prior cell → raw[i] − raw[i−1]
 *   • otherwise (array starts mid-year, or a year boundary with no Q1 column) → null
 *
 * WHAT CHANGED AND WHY: this used to fall back to the RAW cumulative value both when the
 * difference came out negative (`d >= 0 ? d : cur`) and whenever a base was missing. That
 * put a year-to-date total in the same row as discrete quarters, under one label, with no
 * tell — the reader cannot see which cells are which. Two consequences, both wrong:
 * a genuine loss quarter (cumulative net income legitimately FALLS) was overwritten by the
 * year-to-date figure, and every undifferenceable leading period printed a total as a
 * quarter. A negative difference is now emitted as the negative quarter it is, and an
 * unknown base shows a dash — the house stance is a dash over a number we cannot stand
 * behind.
 */
export function discreteQuarters(vals: NumArr, periods: readonly string[]): NumArr {
  const out: NumArr = [];
  for (let i = 0; i < vals.length; i++) {
    const label = periods[i] ?? "";
    if (label.startsWith("Q1")) {
      out.push(vals[i] ?? null);
      continue;
    }
    const yr = fiscalYearToken(label);
    const prevYr = i > 0 ? fiscalYearToken(periods[i - 1]) : null;
    // i === 0, or a fiscal year we entered without seeing its Q1 → no base to difference.
    if (i === 0 || yr == null || prevYr == null || yr !== prevYr) {
      out.push(null);
      continue;
    }
    const cur = vals[i];
    const prev = vals[i - 1];
    out.push(cur != null && prev != null ? cur - prev : null);
  }
  return out;
}

/** Every field of the income contract, so normalization can never skip one. */
const INCOME_FIELDS: readonly (keyof IncomeBlock)[] = [
  "revenue",
  "cogs",
  "gross_profit",
  "opex",
  "op_income",
  "nonop_income",
  "pretax_income",
  "taxes",
  "net_income",
  "eps_basic",
  "eps_diluted",
  "ebitda",
] as const;

/** Additive flow fields. EPS is a per-share ratio and must never be subtracted across YTD windows. */
const ADDITIVE_INCOME_FIELDS = new Set<keyof IncomeBlock>([
  "revenue",
  "cogs",
  "gross_profit",
  "opex",
  "op_income",
  "nonop_income",
  "pretax_income",
  "taxes",
  "net_income",
  "ebitda",
]);

const EMPTY_INCOME: IncomeBlock = INCOME_FIELDS.reduce((acc, k) => {
  acc[k] = [];
  return acc;
}, {} as IncomeBlock);

/**
 * Operating expenses EXCLUDING cost of revenue, derived rather than trusted.
 *
 * The contract's `opex` field is not one thing: `gen_fund_us.py` maps it from yfinance's
 * "Operating Expense" (already excludes cost of revenue) with "Total Expenses" as the
 * SECONDARY label (COGS-inclusive), and the Massive backfill maps it from the vendor's
 * `operating_expenses`. Rendering the raw field under an "excl. COGS" label therefore ships
 * a COGS-inclusive total under a label that says it is not, on exactly the rows where we
 * cannot tell which variant we got. Subtracting COGS from it unconditionally is the mirror
 * mistake — that is what printed AAPL FY2025 at −158.8B before this row was derived.
 *
 * Two source-agnostic identities, in order, then a dash:
 *   1. gross_profit − op_income          (AAPL FY2025: 195.2B − 133.1B = 62.1B, as reported)
 *   2. revenue − cogs − op_income        (same identity where gross_profit itself is null)
 *   3. null                              (nothing derivable — a dash, never a guess)
 *
 * Inputs come from ONE already-normalized block, so a differenced statement can never mix a
 * discrete gross profit with a cumulative operating income.
 */
export function opexExclCogs(inc: IncomeBlock | undefined): NumArr {
  const gp = inc?.gross_profit ?? [];
  const oi = inc?.op_income ?? [];
  const rev = inc?.revenue ?? [];
  const cogs = inc?.cogs ?? [];
  const n = Math.max(gp.length, oi.length, rev.length, cogs.length);
  const out: NumArr = [];
  for (let i = 0; i < n; i++) {
    const o = oi[i];
    if (o == null) {
      out.push(null);
      continue;
    }
    const g = gp[i];
    if (g != null) {
      out.push(g - o);
      continue;
    }
    const r = rev[i];
    const c = cogs[i];
    out.push(r != null && c != null ? r - c - o : null);
  }
  return out;
}

/**
 * The income statement every income surface renders, normalized once.
 *
 * `income` is the block to display: the raw contract arrays for a discrete-quarter market
 * (same array references — nothing is copied), or the differenced arrays for a cumulative
 * one. `opexExclCogs` is the derived row, built from that same block.
 */
export interface IncomeView {
  /** Market whose filing conventions were applied. */
  market: MarketId;
  /** True when the source interim flows were cumulative YTD (normalization may be producer-owned). */
  cumulative: boolean;
  /** Canonical display axis supplied by the producer. */
  periods: string[];
  cadence: StatementReportingCadence;
  sourceFamily: StatementSourceFamily;
  /** Vendor statement family aligned to each period; historical HK issuers can change schema. */
  sourceFamilies: StatementSourceFamily[];
  /** True when this artifact explicitly says its values are already presentation-ready. */
  producerNormalized: boolean;
  income: IncomeBlock;
  /** Family-aware operating-expense row; raw vendor total for financial families. */
  operatingExpenses: NumArr;
  /** Compatibility alias used by existing industrial surfaces. */
  opexExclCogs: NumArr;
}

export type IncomeStatementFamilyMode = "industrial" | "financial" | "mixed";
export type StatementBasis = "annual" | "quarterly";

const NONINDUSTRIAL_FAMILIES = new Set<StatementSourceFamily>([
  "bank",
  "insurer",
  "financial_services",
  "ambiguous",
]);

/** Financial families do not share the industrial gross-profit/COGS statement geometry. */
export function isIndustrialStatement(family: StatementSourceFamily | null | undefined): boolean {
  return !family || !NONINDUSTRIAL_FAMILIES.has(family);
}

/**
 * Presentation scope for a complete income view.
 *
 * A small number of HK issuers change vendor taxonomy over their retained history. A scalar
 * `source_family` describes only the latest row and must never make industrial-only geometry
 * appear across earlier financial-family columns (or vice versa). The per-period receipt is
 * therefore authoritative for view-wide presentation; industrial treatments require every
 * displayed period to be industrial-compatible.
 */
export function incomeViewFamilyMode(
  view: Pick<IncomeView, "sourceFamily" | "sourceFamilies">,
): IncomeStatementFamilyMode {
  const families = view.sourceFamilies.length > 0
    ? view.sourceFamilies
    : [view.sourceFamily];
  // A dual-schema source row proves neither one family nor comparable industrial geometry.
  // Route it through the conservative mixed presentation even when it is the only row.
  if (families.includes("ambiguous")) return "mixed";
  const hasIndustrial = families.some(isIndustrialStatement);
  const hasFinancial = families.some((family) => !isIndustrialStatement(family));
  return hasIndustrial && hasFinancial
    ? "mixed"
    : hasFinancial
      ? "financial"
      : "industrial";
}

/** Industrial-only rows and charts are safe only when every displayed period shares that form. */
export function isIndustrialIncomeView(
  view: Pick<IncomeView, "sourceFamily" | "sourceFamilies">,
): boolean {
  return incomeViewFamilyMode(view) === "industrial";
}

function sourceFamilyOf(set: StatementPeriodSet | null | undefined): StatementSourceFamily {
  return (
    set?.source_family ??
    [...(set?.source_family_by_period ?? [])].reverse().find((family) => family !== "other") ??
    "other"
  );
}

/** A basis is navigable only when its statement transport carries at least one period. */
export function statementBasisAvailable(set: StatementPeriodSet | null | undefined): boolean {
  return (set?.periods?.length ?? 0) > 0;
}

/**
 * Keep a mounted consumer on a real basis as symbols change or one source endpoint is absent.
 * The requested basis wins when available; otherwise the other real basis wins. If neither is
 * available, retain the request so the caller can render its ordinary empty state deterministically.
 */
export function resolveStatementBasis(
  requested: StatementBasis,
  annualAvailable: boolean,
  interimAvailable: boolean,
): StatementBasis {
  if (requested === "annual" && !annualAvailable && interimAvailable) return "quarterly";
  if (requested === "quarterly" && !interimAvailable && annualAvailable) return "annual";
  return requested;
}

/** Canonical cadence, with a conservative quarterly fallback for pre-metadata artifacts. */
export function statementCadence(
  set: StatementPeriodSet | null | undefined,
  timeframe: "annual" | "quarterly",
): StatementReportingCadence {
  if (timeframe === "annual") return "annual";
  if (set?.reporting_cadence) return set.reporting_cadence;
  const kinds = new Set(set?.period_kind ?? []);
  if (kinds.size > 0 && [...kinds].every((kind) => kind === "half_year")) return "semiannual";
  if (kinds.size > 0 && [...kinds].every((kind) => kind === "quarter")) return "quarterly";
  if (kinds.size > 0) return "mixed";
  return "quarterly";
}

export function statementCadenceLabel(
  set: StatementPeriodSet | null | undefined,
  timeframe: "annual" | "quarterly",
  zh: boolean,
): string {
  if (timeframe === "quarterly" && !set) return zh ? "中期" : "Interim";
  const cadence = statementCadence(set, timeframe);
  if (cadence === "annual") return zh ? "年度" : "Annual";
  if (cadence === "semiannual") return zh ? "半年度" : "Semiannual";
  if (cadence === "mixed") return zh ? "中期" : "Interim";
  return zh ? "季度" : "Quarterly";
}

export function statementPeriodCountLabel(
  set: StatementPeriodSet | null | undefined,
  timeframe: "annual" | "quarterly",
  zh: boolean,
): string {
  const count = set?.periods?.length ?? 0;
  const cadence = statementCadence(set, timeframe);
  if (zh) {
    const noun = cadence === "annual" ? "个财年" : cadence === "quarterly" ? "个季度" :
      cadence === "semiannual" ? "个半年期" : "个报告期";
    return `${count}${noun}`;
  }
  const noun = cadence === "annual" ? "fiscal years" : cadence === "quarterly" ? "quarters" :
    cadence === "semiannual" ? "half-years" : "reporting periods";
  return `${count} ${noun}`;
}

export function incomeTopLineLabel(
  family: StatementSourceFamily | null | undefined,
  zh: boolean,
): string {
  return isIndustrialStatement(family)
    ? (zh ? "营业收入" : "Revenue")
    : (zh ? "经营收入总额" : "Total operating income");
}

/** Top-line label for a whole view, including histories that cross statement taxonomies. */
export function incomeViewTopLineLabel(
  view: Pick<IncomeView, "sourceFamily" | "sourceFamilies">,
  zh: boolean,
): string {
  const mode = incomeViewFamilyMode(view);
  if (mode === "mixed") {
    return zh ? "营业收入 / 经营收入总额" : "Revenue / total operating income";
  }
  return incomeTopLineLabel(mode === "financial" ? "financial_services" : "industrial", zh);
}

export function operatingExpenseLabel(
  family: StatementSourceFamily | null | undefined,
  zh: boolean,
): string {
  return isIndustrialStatement(family)
    ? (zh ? "营业费用（不含成本）" : "Operating expenses (excl. COGS)")
    : (zh ? "营业费用" : "Operating expenses");
}

/** Expense label for a whole view; mixed histories use the neutral label explained below. */
export function incomeViewOperatingExpenseLabel(
  view: Pick<IncomeView, "sourceFamily" | "sourceFamilies">,
  zh: boolean,
): string {
  return incomeViewFamilyMode(view) === "industrial"
    ? operatingExpenseLabel("industrial", zh)
    : operatingExpenseLabel("financial_services", zh);
}

/** Structural disclosure for statement families where industrial subtotals do not apply. */
export function financialFamilyDisclosure(
  family: StatementSourceFamily | null | undefined,
  zh: boolean,
): string | null {
  if (isIndustrialStatement(family)) return null;
  return zh
    ? "金融机构采用供应商披露的经营收入与营业费用总额；营业成本、毛利和 EBITDA 等工业企业项目不适用，因此不显示。"
    : "Financial institutions use vendor-reported operating-income and expense totals; industrial COGS, gross profit, and EBITDA do not apply and are omitted.";
}

/** Structural disclosure for a complete view, without describing mixed history as one family. */
export function incomeViewFamilyDisclosure(
  view: Pick<IncomeView, "sourceFamily" | "sourceFamilies">,
  zh: boolean,
): string | null {
  const families = view.sourceFamilies.length > 0 ? view.sourceFamilies : [view.sourceFamily];
  if (families.includes("ambiguous")) {
    return zh
      ? "来源行同时包含多套完整报表格式，且没有可验证的主格式。该期按不明确来源处理，并隐藏特定报表格式的工业企业项目。"
      : "The source row contains multiple complete statement formats with no verifiable primary format. It is treated as ambiguous and family-specific industrial rows are omitted.";
  }
  const mode = incomeViewFamilyMode(view);
  if (mode === "industrial") return null;
  if (mode === "financial") return financialFamilyDisclosure("financial_services", zh);
  return zh
    ? "该历史区间跨越工业企业与金融服务报表格式。营业费用按各期来源口径显示；营业成本、毛利和 EBITDA 等仅适用于工业企业的项目不在合并视图中显示。"
    : "This history spans industrial and financial-services statement formats. Operating expenses follow each period's source; industrial-only COGS, gross profit, and EBITDA are omitted from the combined view.";
}

/** Index of the prior fiscal year's economically comparable period, or null when unknown. */
export function priorComparableIndex(
  set: StatementPeriodSet | null | undefined,
  index: number,
  timeframe: "annual" | "quarterly",
): number | null {
  const years = set?.fiscal_year;
  const kinds = set?.period_kind;
  const numbers = set?.period_number;
  const n = set?.periods?.length ?? 0;
  if (
    years?.length === n && kinds?.length === n && numbers?.length === n &&
    years[index] != null && kinds[index] != null
  ) {
    const year = Number(years[index]);
    if (!Number.isFinite(year)) return null;
    const sameIdentity = (i: number, targetYear: number) =>
      Number(years[i]) === targetYear &&
      kinds[i] === kinds[index] &&
      (numbers[i] ?? null) === (numbers[index] ?? null);
    // A fiscal-year-end transition can create two H1/FY observations with the same canonical
    // identity. Choosing the nearest one would make YoY depend on array order, so both the current
    // and prior identity must be unique.
    const currentMatches = Array.from({ length: n }, (_, i) => i)
      .filter((i) => sameIdentity(i, year));
    const priorMatches = Array.from({ length: index }, (_, i) => i)
      .filter((i) => sameIdentity(i, year - 1));
    return currentMatches.length === 1 && priorMatches.length === 1
      ? priorMatches[0]
      : null;
  }
  const lag = timeframe === "annual" ? 1 : 4;
  return index >= lag ? index - lag : null;
}

/** Year-over-year percent changes using explicit fiscal identity when available. */
export function comparablePeriodChanges(
  values: NumArr,
  set: StatementPeriodSet | null | undefined,
  timeframe: "annual" | "quarterly",
): NumArr {
  return values.map((current, index) => {
    const priorIndex = priorComparableIndex(set, index, timeframe);
    const prior = priorIndex == null ? null : values[priorIndex];
    return current != null && prior != null && prior !== 0
      ? ((current - prior) / Math.abs(prior)) * 100
      : null;
  });
}

/**
 * Normalize a period set's income statement for display.
 *
 * `cumulative` requires BOTH gates: the symbol's market files cumulative year-to-date
 * interims, AND the timeframe is quarterly, AND the revenue series still looks cumulative.
 * A US symbol can never satisfy the first, whatever its numbers do.
 */
export function incomeView(
  sym: string | null | undefined,
  set: StatementPeriodSet | null | undefined,
  timeframe: "annual" | "quarterly",
): IncomeView {
  const market = statementMarket(sym);
  const src = set?.income;
  const periods = set?.periods ?? [];
  const cadence = statementCadence(set, timeframe);
  const sourceFamily = sourceFamilyOf(set);
  const producerNormalized =
    timeframe === "quarterly" &&
    set?.flow_basis != null &&
    set.flow_basis !== "cumulative_ytd";
  const legacyCumulative =
    timeframe === "quarterly" &&
    !producerNormalized &&
    CUMULATIVE_SET.has(market) &&
    isCumulativeShape(src?.revenue);
  const cumulative =
    timeframe === "quarterly" &&
    ((set?.is_cumulative?.some(Boolean) ?? false) || legacyCumulative);

  if (!src) {
    return {
      market,
      cumulative: false,
      periods,
      cadence,
      sourceFamily,
      sourceFamilies: periods.map((_, i) => set?.source_family_by_period?.[i] ?? sourceFamily),
      producerNormalized,
      income: EMPTY_INCOME,
      operatingExpenses: [],
      opexExclCogs: [],
    };
  }

  const income = {} as IncomeBlock;
  for (const k of INCOME_FIELDS) {
    const arr = (src[k] as NumArr | undefined) ?? [];
    if (!legacyCumulative) {
      income[k] = arr;
    } else if (ADDITIVE_INCOME_FIELDS.has(k)) {
      income[k] = discreteQuarters(arr, periods);
    } else {
      // EPS/per-share fields use a different weighted-share denominator in each filing. Q1 is
      // directly usable; later YTD rows cannot be made discrete by subtraction.
      income[k] = arr.map((value, i) => periods[i]?.startsWith("Q1") ? value ?? null : null);
    }
  }
  const industrialOperatingExpenses = opexExclCogs(income);
  const familyCount = Math.max(periods.length, income.opex.length, industrialOperatingExpenses.length);
  const sourceFamilies = Array.from(
    { length: familyCount },
    (_, i) => set?.source_family_by_period?.[i] ?? sourceFamily,
  );
  const operatingExpenses = sourceFamilies.every(isIndustrialStatement)
    ? industrialOperatingExpenses
    : sourceFamilies.every((family) => !isIndustrialStatement(family))
      ? income.opex
      : sourceFamilies.map((family, i) =>
          isIndustrialStatement(family)
            ? industrialOperatingExpenses[i] ?? null
            : income.opex[i] ?? null,
        );
  return {
    market,
    cumulative,
    periods,
    cadence,
    sourceFamily,
    sourceFamilies,
    producerNormalized,
    income,
    operatingExpenses,
    opexExclCogs: operatingExpenses,
  };
}

/**
 * The five series the mini bar chart plots, taken straight off the normalized block.
 *
 * Returns REFERENCES, not copies: the array the chart plots is the same object the table
 * prints, so "chart says 82.9B, table says 1.6B" cannot recur. Pinned by reference equality
 * in lib/__tests__/finStatementMath.test.ts.
 */
export function incomeChartValues(view: IncomeView): {
  revenue: NumArr;
  gross_profit: NumArr;
  op_income: NumArr;
  pretax_income: NumArr;
  net_income: NumArr;
} {
  return {
    revenue: view.income.revenue,
    gross_profit: view.income.gross_profit,
    op_income: view.income.op_income,
    pretax_income: view.income.pretax_income,
    net_income: view.income.net_income,
  };
}

/**
 * The disclosure line for a differenced quarterly income statement, or null when nothing was
 * differenced. Names the market whose convention is being described — the old copy asserted
 * "(CN/HK reporting style)" and would have shown that sentence on a US filer's tab.
 */
export function cumulativeQuarterNote(view: IncomeView, zh: boolean): string | null {
  if (!view.cumulative) return null;
  if (view.market === "cn") {
    return zh
      ? "中国内地财报按年初至今累计口径披露；可加总项目由相邻期差分得出。缺少累计基数或无法安全差分的每股收益显示为短横线。"
      : "Additive quarterly flows are differenced from the cumulative year-to-date totals mainland-China filings report. Missing bases and EPS that cannot be safely differenced show a dash.";
  }
  if (view.market === "hk") {
    const span = view.cadence === "semiannual"
      ? (zh ? "独立半年期" : "discrete half-years")
      : view.cadence === "quarterly"
        ? (zh ? "独立季度" : "discrete quarters")
        : (zh ? "经来源验证的报告期间" : "source-verifiable reporting periods");
    return zh
      ? `香港数据源按财年初至今累计口径披露；可加总项目已转换为${span}。缺少累计基数或无法安全差分的每股收益显示为短横线。`
      : `Hong Kong source rows are cumulative from the fiscal-year start; additive flows are normalized into ${span}. Missing bases and EPS that cannot be safely differenced show a dash.`;
  }
  // Unreachable while CUMULATIVE_YTD_MARKETS is {cn, hk}; a market added there without copy
  // shows no note rather than a sentence about somebody else's filing convention.
  return null;
}
