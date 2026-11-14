/**
 * Analysis-route identifier grammar.  It intentionally accepts the forms
 * investors actually share (`BRK.B`, `RDS-A`, `^NDX`) but never a value that
 * could be mistaken for a pathname, query string, or fallback alias.
 */
export const ANALYSIS_SYMBOL = /^(?:\^[A-Z0-9]+|[A-Z0-9]+(?:[.-][A-Z0-9]+)*)$/;

/**
 * The Analysis route's one fallback symbol when nothing else resolves — the single source of
 * truth for both `components/workspaces/AnalysisWorkspace.tsx`'s seeded/invalid-input default
 * and `lib/shellBrainSymbol.ts`'s `SHELL_DEFAULT_BRAIN_SYMBOL`. Previously each file declared
 * its own `"NVDA"` literal, which could silently drift apart (review ruling, PR #490 MINOR:
 * default symbol) — a change to one would not be caught by the other's tests.
 */
export const ANALYSIS_DEFAULT_SYMBOL = "NVDA";

export function normalizeAnalysisSymbol(value: string | undefined): string | null {
  const symbol = value?.trim().toUpperCase() ?? "";
  if (!symbol || symbol.length > 24 || !ANALYSIS_SYMBOL.test(symbol)) return null;
  return symbol;
}
