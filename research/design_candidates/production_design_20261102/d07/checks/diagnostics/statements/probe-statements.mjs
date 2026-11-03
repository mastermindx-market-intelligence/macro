import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const directory = dirname(fileURLToPath(import.meta.url));
const sourceRoot = resolve(process.argv[2] ?? resolve(directory, "sources"));
const metadata = JSON.parse(readFileSync(resolve(directory, "sources.json"), "utf8"));
const sourceUrl = (path) => pathToFileURL(resolve(sourceRoot, path)).href;

for (const source of metadata.files) {
  const bytes = readFileSync(resolve(sourceRoot, source.path));
  const blob = createHash("sha1").update(`blob ${bytes.length}\0`).update(bytes).digest("hex");
  const sha256 = createHash("sha256").update(bytes).digest("hex");
  assert.equal(blob, source.git_blob, `${source.path} Git blob`);
  assert.equal(sha256, source.sha256, `${source.path} SHA-256`);
  assert.equal(bytes.length, source.bytes, `${source.path} byte length`);
}

const mathUrl = sourceUrl("terminal/lib/finStatementMath.ts");
const historyUrl = sourceUrl("terminal/lib/finStatements.ts");

// Resolve only the two extensionless runtime imports from these exact source modules.
// Node strips TypeScript types. The upstream modules remain byte-for-byte unchanged.
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (context.parentURL === mathUrl && specifier === "./markets") {
      return nextResolve(sourceUrl("terminal/lib/markets.ts"), context);
    }
    if (context.parentURL === historyUrl && specifier === "./finStatementMath") {
      return nextResolve(mathUrl, context);
    }
    return nextResolve(specifier, context);
  },
});

const math = await import(mathUrl);
const history = await import(historyUrl);
const results = [];
let assertions = 0;

function equal(actual, expected, label) {
  assertions += 1;
  assert.deepStrictEqual(actual, expected, label);
}

function sameReference(actual, expected, label) {
  assertions += 1;
  assert.strictEqual(actual, expected, label);
}

function runCase(id, task, label, body, expectation = "SOURCE_BEHAVIOR") {
  const before = assertions;
  try {
    const observed = body();
    results.push({ id, task, label, expectation, status: "BASELINE_REPRODUCED", assertions: assertions - before, observed });
  } catch (error) {
    results.push({ id, task, label, expectation, status: "MISMATCH", assertions: assertions - before, error: error.message });
  }
}

const incomeFields = [
  "revenue", "cogs", "gross_profit", "opex", "op_income", "nonop_income",
  "pretax_income", "taxes", "net_income", "eps_basic", "eps_diluted", "ebitda",
];
const balanceFields = [
  "assets", "assets_st", "assets_lt", "liabilities", "liab_st", "liab_lt",
  "equity", "debt", "cash", "net_debt",
];
const cashflowFields = ["cfo", "cfi", "cff", "capex", "fcf"];

function emptyBlock(fields, length) {
  return Object.fromEntries(fields.map((field) => [field, Array(length).fill(null)]));
}

function periodSet(periods, ends, income = {}, metadataFields = {}) {
  return {
    periods,
    period_end: ends,
    income: { ...emptyBlock(incomeFields, periods.length), ...income },
    balance: emptyBlock(balanceFields, periods.length),
    cashflow: emptyBlock(cashflowFields, periods.length),
    ...metadataFields,
  };
}

function annualSet(values, years = values.map((_, index) => String(2025 + index))) {
  return periodSet(
    years.map((year) => `FY${year}`),
    years.map((year) => `${year}-12-31`),
    { revenue: values },
    {
      period_start: years.map((year) => `${year}-01-01`),
      fiscal_year: years,
      period_kind: years.map(() => "full_year"),
      period_number: years.map(() => null),
      period_duration_months: years.map(() => 12),
      comparison_basis: years.map(() => "synthetic_uniform_basis"),
      reporting_cadence: "annual",
    },
  );
}

function legacyQuarterSet(revenue, extraIncome = {}) {
  const periods = revenue.map((_, index) => `Q${index % 4 + 1} ${2025 + Math.floor(index / 4)}`);
  const ends = revenue.map((_, index) => {
    const year = 2025 + Math.floor(index / 4);
    return `${year}-${["03-31", "06-30", "09-30", "12-31"][index % 4]}`;
  });
  return periodSet(periods, ends, { revenue, ...extraIncome });
}

runCase("ST01", "S01", "Canonical annual comparison and Revenue history agree", () => {
  const set = annualSet([100_000_000, 120_000_000]);
  const prior = math.priorComparableIndex(set, 1, "annual");
  const changes = math.comparablePeriodChanges(set.income.revenue, set, "annual");
  const points = history.revenueHistory({ ticker: "NVDA", statements: { annual: set, quarterly: null } });
  equal(prior, 0, "unique prior fiscal year");
  equal(changes, [null, 20], "annual growth");
  equal(points, [{ period: "FY2025", value: 100_000_000, yoy: null }, { period: "FY2026", value: 120_000_000, yoy: 20 }], "history uses same comparison");
  return { prior, changes, points };
});

runCase("ST02", "S03", "True zero, null slot and zero denominator stay distinct", () => {
  const set = annualSet([100_000_000, 0, 50_000_000, null]);
  const points = history.revenueHistory({ ticker: "NVDA", statements: { annual: set, quarterly: null } });
  const changes = math.comparablePeriodChanges(set.income.revenue, set, "annual");
  equal(changes, [null, -100, null, null], "known zero and undefined denominators");
  equal(points.map((point) => point.value), [100_000_000, 0, 50_000_000, null], "zero retained and null slot retained");
  equal(history.revenueCoverage(points), 3, "zero counts as real coverage");
  return { changes, points, coverage: history.revenueCoverage(points) };
});

runCase("ST03", "S03", "A real flat comparison remains numeric zero", () => {
  const set = annualSet([100, 100]);
  const changes = math.comparablePeriodChanges(set.income.revenue, set, "annual");
  equal(changes, [null, 0], "flat change");
  return { changes };
});

runCase("ST04", "S02", "Duration mismatch blocks otherwise matching identity", () => {
  const set = annualSet([100, 120]);
  set.period_duration_months = [9, 12];
  const prior = math.priorComparableIndex(set, 1, "annual");
  const changes = math.comparablePeriodChanges(set.income.revenue, set, "annual");
  equal(prior, null, "duration guard");
  equal(changes, [null, null], "withheld growth");
  return { prior, changes };
});

runCase("ST05", "S02", "Different or unknown comparison bases block growth", () => {
  const observed = [];
  for (const basis of [["synthetic_A", "synthetic_B"], [null, "synthetic_B"], ["synthetic_A", null]]) {
    const set = annualSet([100, 120]);
    set.comparison_basis = basis;
    const prior = math.priorComparableIndex(set, 1, "annual");
    equal(prior, null, "basis guard");
    observed.push({ basis, prior });
  }
  return observed;
});

runCase("ST06", "S02", "Quarter identity cannot substitute for a full year", () => {
  const set = annualSet([100, 120]);
  set.period_kind[0] = "quarter";
  set.period_number[0] = 4;
  const prior = math.priorComparableIndex(set, 1, "annual");
  equal(prior, null, "period-kind and number identity");
  return { prior };
});

runCase("ST07", "S02", "Ambiguous prior fiscal identity blocks order-based choice", () => {
  const set = annualSet([100, 105, 120], ["2025", "2025", "2026"]);
  const prior = math.priorComparableIndex(set, 2, "annual");
  equal(prior, null, "duplicate prior identity");
  equal(math.comparablePeriodChanges(set.income.revenue, set, "annual"), [null, null, null], "all ambiguous/absent comparisons withheld");
  return { prior };
});

runCase("ST08", "S02", "Ambiguous current fiscal identity is also refused", () => {
  const set = annualSet([100, 120, 125], ["2025", "2026", "2026"]);
  const prior = math.priorComparableIndex(set, 1, "annual");
  equal(prior, null, "duplicate current identity");
  equal(math.priorComparableIndex(set, 2, "annual"), null, "second current duplicate");
  return { prior };
});

runCase("ST09", "S02", "Partial identity cannot fall back when qualification metadata exists", () => {
  const set = annualSet([100, 120]);
  delete set.period_number;
  equal(math.priorComparableIndex(set, 1, "annual"), null, "partial identity with duration and basis");
  const missingDuration = annualSet([100, 120]);
  missingDuration.period_duration_months = [12, null];
  equal(math.priorComparableIndex(missingDuration, 1, "annual"), null, "unknown explicit duration");
  return { partialIdentityPrior: null, unknownDurationPrior: null };
});

runCase("ST10", "S02", "Mixed YTD and discrete quarters retain their cadence and values", () => {
  const set = periodSet(["9M 2025", "Q3 2026"], ["2025-09-30", "2026-09-30"], { revenue: [300, 120] }, {
    fiscal_year: ["2025", "2026"], period_kind: ["year_to_date", "quarter"],
    period_number: [null, 3], period_duration_months: [9, 3],
    comparison_basis: ["synthetic_uniform_basis", "synthetic_uniform_basis"],
    reporting_cadence: "mixed", flow_basis: "mixed_period", is_cumulative: [true, false],
  });
  const view = math.incomeView("600519.SS", set, "quarterly");
  equal(math.statementCadenceLabel(set, "quarterly", false), "Interim", "source cadence label");
  equal(view.income.revenue, [300, 120], "canonical mixed values retained");
  equal(math.comparablePeriodChanges(view.income.revenue, set, "quarterly"), [null, null], "incomparable periods");
  return { cadence: view.cadence, revenue: view.income.revenue, comparison: [null, null] };
});

runCase("ST11", "S04", "Canonical HK H1/H2 is normalized once and keeps producer EPS null", () => {
  const set = periodSet(["H1 2026", "H2 2026"], ["2025-09-30", "2026-03-31"], { revenue: [60_000_000, 80_000_000], eps_basic: [1.2, null] }, {
    period_start: ["2025-04-01", "2025-10-01"], fiscal_year: ["2026", "2026"],
    period_kind: ["half_year", "half_year"], period_number: [1, 2], period_duration_months: [6, 6],
    comparison_basis: ["synthetic_uniform_basis", "synthetic_uniform_basis"], reporting_cadence: "semiannual",
    flow_basis: "discrete_period", is_cumulative: [true, true],
    normalization_method: ["as_reported", "difference_from_prior_ytd"], source_period_label: ["H1 2026", "FY2026"],
  });
  const view = math.incomeView("0700.HK", set, "quarterly");
  const chart = math.incomeChartValues(view);
  const points = history.revenueHistory({ ticker: "0700.HK", statements: { annual: null, quarterly: set } }, "quarterly");
  equal([view.market, view.cadence, view.producerNormalized, view.cumulative], ["hk", "semiannual", true, true], "canonical HK state");
  equal(math.statementCadenceLabel(set, "quarterly", false), "Semiannual", "cadence label");
  equal(view.income.revenue, [60_000_000, 80_000_000], "no second differencing");
  equal(view.income.eps_basic, [1.2, null], "upstream per-share absence retained");
  sameReference(chart.revenue, view.income.revenue, "chart consumes exact normalized array");
  sameReference(view.income.revenue, set.income.revenue, "canonical source array retained");
  equal(points.map((point) => point.value), [60_000_000, 80_000_000], "Revenue consumer parity");
  equal(points.map((point) => point.yoy), [null, null], "H2 versus H1 is not YoY");
  return { cadence: view.cadence, producerNormalized: view.producerNormalized, revenue: view.income.revenue, eps: view.income.eps_basic, history: points };
});

runCase("ST12", "S04", "Half-year YoY follows fiscal identity across calendar years", () => {
  const set = periodSet(["H1 2025", "H2 2025", "H1 2026", "H2 2026"], ["2024-09-30", "2025-03-31", "2025-09-30", "2026-03-31"], { revenue: [50, 80, 60, 100] }, {
    fiscal_year: ["2025", "2025", "2026", "2026"],
    period_kind: ["half_year", "half_year", "half_year", "half_year"], period_number: [1, 2, 1, 2],
    period_duration_months: [6, 6, 6, 6], comparison_basis: Array(4).fill("synthetic_uniform_basis"),
    reporting_cadence: "semiannual", flow_basis: "discrete_period",
  });
  const changes = math.comparablePeriodChanges(set.income.revenue, set, "quarterly");
  equal(math.priorComparableIndex(set, 2, "quarterly"), 0, "H1 comparable");
  equal(math.priorComparableIndex(set, 3, "quarterly"), 1, "H2 comparable");
  equal(changes, [null, null, 20, 25], "half-year growth");
  return { changes };
});

runCase("ST13", "S04", "Legacy HK/CN helper differences additive flows and withholds derived EPS", () => {
  const set = legacyQuarterSet([100, 220, 330, 450, 120, 260, 390, 530], {
    eps_basic: [0.1, 0.22, 0.33, 0.45, 0.12, 0.26, 0.39, 0.53],
    net_income: [10, 15, 5, 20, 12, 18, 7, 24],
  });
  const observed = [];
  for (const ticker of ["0700.HK", "600519.SS"]) {
    const view = math.incomeView(ticker, set, "quarterly");
    equal([view.cumulative, view.producerNormalized], [true, false], "legacy cumulative path");
    equal(view.income.revenue, [100, 120, 110, 120, 120, 140, 130, 140], "additive normalization");
    equal(view.income.eps_basic, [0.1, null, null, null, 0.12, null, null, null], "EPS is not an additive flow");
    equal(view.income.net_income, [10, 5, -10, 15, 12, 6, -11, 17], "real negative discrete flows retained");
    observed.push({ ticker, revenue: view.income.revenue, eps: view.income.eps_basic, netIncome: view.income.net_income });
  }
  return observed;
});

runCase("ST14", "S04", "Legacy missing cumulative base is null at the start and year boundary", () => {
  const values = math.discreteQuarters([220, 330, 450, 260, 390], ["Q2 2025", "Q3 2025", "Q4 2025", "Q2 2026", "Q3 2026"]);
  equal(values, [null, 110, 120, null, 130], "no starting or cross-year cumulative base");
  return { values };
});

runCase("ST15", "S02", "Pre-metadata annual and four-quarter compatibility remains", () => {
  const annual = periodSet(["FY2025", "FY2026"], ["2025-12-31", "2026-12-31"], { revenue: [100, 120] });
  const interim = legacyQuarterSet([10, 20, 30, 40, 15, 30, 45, 60]);
  equal(math.priorComparableIndex(annual, 1, "annual"), 0, "annual positional fallback");
  equal(math.comparablePeriodChanges(annual.income.revenue, annual, "annual"), [null, 20], "annual legacy growth");
  const changes = math.comparablePeriodChanges(interim.income.revenue, interim, "quarterly");
  equal(changes, [null, null, null, null, 50, 50, 50, 50], "quarterly lag-four fallback");
  return { annual: [null, 20], quarterly: changes };
});

runCase("ST16", "S04", "Growing US quarter values cannot activate cumulative differencing", () => {
  const set = legacyQuarterSet([100, 220, 330, 450, 120, 260, 390, 530]);
  const view = math.incomeView("NVDA", set, "quarterly");
  equal(math.isCumulativeShape(set.income.revenue), true, "deliberately cumulative-shaped fixture");
  equal([view.market, view.cumulative, view.producerNormalized], ["us", false, false], "market gate");
  sameReference(view.income.revenue, set.income.revenue, "as-reported US array");
  return { market: view.market, cumulative: view.cumulative, revenue: view.income.revenue };
});

runCase("ST17", "S01/S04", "Statement basis fallback selects only a transport with periods", () => {
  equal(math.statementBasisAvailable(null), false, "null statement basis");
  equal(math.statementBasisAvailable(periodSet([], [])), false, "empty statement basis");
  equal(math.resolveStatementBasis("quarterly", true, false), "annual", "annual-only fallback");
  equal(math.resolveStatementBasis("annual", false, true), "quarterly", "interim-only fallback");
  equal(math.resolveStatementBasis("quarterly", false, false), "quarterly", "deterministic all-empty request");
  return { annualOnly: "annual", interimOnly: "quarterly", neither: "quarterly" };
});

runCase("ST18", "S06", "Bank statement labels and expenses use financial-family semantics", () => {
  const set = annualSet([100]);
  set.source_family = "bank";
  set.income.opex = [70];
  set.income.gross_profit = [60];
  set.income.op_income = [20];
  const view = math.incomeView("0005.HK", set, "annual");
  equal(math.incomeViewTopLineLabel(view, false), "Total operating income", "financial top line");
  equal(math.incomeViewOperatingExpenseLabel(view, false), "Operating expenses", "financial expense label");
  equal(view.operatingExpenses, [70], "raw financial expense retained");
  equal(math.isIndustrialIncomeView(view), false, "industrial-only geometry ineligible");
  return { mode: math.incomeViewFamilyMode(view), topLine: math.incomeViewTopLineLabel(view, false), expenses: view.operatingExpenses, industrial: false };
});

runCase("ST19", "S06", "Mixed historical statement families retain per-period expense meaning", () => {
  const set = annualSet([100, 120]);
  set.source_family = "financial_services";
  set.source_family_by_period = ["industrial", "financial_services"];
  set.income.opex = [999, 80];
  set.income.gross_profit = [60, 70];
  set.income.op_income = [20, 25];
  const view = math.incomeView("0005.HK", set, "annual");
  equal(math.incomeViewFamilyMode(view), "mixed", "mixed family");
  equal(math.incomeViewTopLineLabel(view, false), "Revenue / total operating income", "mixed top line");
  equal(view.operatingExpenses, [40, 80], "industrial derived, financial raw");
  equal(math.isIndustrialIncomeView(view), false, "combined view ineligible for industrial-only geometry");
  return { mode: "mixed", topLine: math.incomeViewTopLineLabel(view, false), expenses: view.operatingExpenses };
});

runCase("ST20", "S06", "Ambiguous source family follows the conservative mixed path", () => {
  const set = annualSet([100]);
  set.source_family = "ambiguous";
  const view = math.incomeView("0005.HK", set, "annual");
  equal(math.incomeViewFamilyMode(view), "mixed", "ambiguous family mode");
  equal(math.isIndustrialIncomeView(view), false, "industrial-only geometry ineligible");
  const disclosure = math.incomeViewFamilyDisclosure(view, false);
  equal(disclosure.includes("multiple complete statement formats"), true, "source ambiguity disclosed");
  return { mode: "mixed", disclosure };
});

runCase("ST21", "S03", "Vendor gap disclosure is scoped to the selected statement block", () => {
  const set = annualSet([100]);
  set.src_by_period = ["massive"];
  set.vendor_gaps = { income: ["ebitda"], balance: ["debt", "net_debt"] };
  const income = history.vendorGapNotice(set, "income", false);
  equal(income, { rows: ["EBITDA"], fullFrom: null, vendorPeriods: 1 }, "income-specific gap");
  equal(history.vendorGapNotice(set, "cashflow", false), null, "unrelated block has no gap notice");
  return { income, cashflow: null, ebitda: set.income.ebitda };
});

runCase("ST22", "S02/S04", "Legacy missing Q2 permits a six-month subtraction under Q3", () => {
  const periods = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024", "Q1 2025", "Q3 2025", "Q4 2025", "Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026"];
  const ends = ["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31", "2025-03-31", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30", "2026-09-30", "2026-12-31"];
  const set = periodSet(periods, ends, { revenue: [100, 220, 330, 450, 120, 390, 530, 130, 280, 420, 570] });
  const view = math.incomeView("0700.HK", set, "quarterly");
  equal(view.cumulative, true, "legacy shape activates normalization");
  equal(view.income.revenue[5], 270, "observed six-month subtraction");
  equal(view.periods[5], "Q3 2025", "unchanged quarter label");
  return {
    inputPrior: { period: periods[4], value: 120 },
    inputCurrent: { period: periods[5], value: 390 },
    selectedOutput: { period: view.periods[5], value: view.income.revenue[5] },
    requiredDisposition: "Source owner must qualify the missing cumulative base or duration before this can be shown as a discrete quarter. No live incidence measured.",
  };
}, "EXPECTED_UNDESIRABLE_BASELINE");

const mismatches = results.filter((result) => result.status === "MISMATCH");
const output = {
  diagnostic: "d07_statement_helper_source_baseline",
  status: mismatches.length === 0 ? "BASELINE_REPRODUCED" : "BASELINE_MISMATCH",
  commit: metadata.commit,
  runtime: process.version,
  fixtureNature: "Synthetic source-shaped inputs. This run does not certify producer outputs, UI wording, browser behavior or visual acceptance.",
  sourceIntegrity: { files: metadata.files.length, checks: metadata.files.length * 3, identities: metadata.files },
  counts: { cases: results.length, assertions, reproduced: results.length - mismatches.length, mismatches: mismatches.length, expectedUndesirableBaselines: results.filter((result) => result.expectation === "EXPECTED_UNDESIRABLE_BASELINE").length, uiAssertions: 0 },
  unsupported: [
    "S05 annual-only CN forecast rendering and optional third target are owned by gen_fund_cn.py and ForecastPage.tsx, outside these statement helpers.",
    "Proposed comparison-reason wording is untested. The comparison helpers return number-or-null without a typed reason.",
    "Canonical HK null EPS retention is tested. The upstream producer's decision to emit that null is not executed here.",
    "Source access, filing clocks, real payload coverage and browser/Paper interactions are outside this isolated helper diagnostic.",
  ],
  cases: results,
};
console.log(JSON.stringify(output, null, 2));
process.exitCode = mismatches.length === 0 ? 0 : 1;
