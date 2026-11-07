export {
  incomeView, incomeChartValues, comparablePeriodChanges, priorComparableIndex,
  incomeViewFamilyMode, isIndustrialIncomeView, incomeViewTopLineLabel,
  incomeViewOperatingExpenseLabel, incomeViewFamilyDisclosure,
  cumulativeQuarterNote, statementCadence, statementCadenceLabel,
  statementPeriodCountLabel, statementBasisAvailable, resolveStatementBasis,
} from "./vendor/terminal/finStatementMath";
export { applyLegacyStatementFamilyFallback } from "./vendor/terminal/fund";
export { vendorGapNotice, historySpan } from "./vendor/terminal/finStatements";
export const version = "terminal-statements-38723cef-v1";
