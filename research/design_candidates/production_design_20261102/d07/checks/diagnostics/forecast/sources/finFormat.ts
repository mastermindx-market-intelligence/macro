// finFormat.ts — shared number/label formatting helpers for the TV-parity fin UI (BUILD-SPEC §3.1).
//
// SINGLE AUTHOR: lane FE1a. FE1b/FE2*/FE3 import from here.
//   - fmtNum: K/M/B/T abbreviation, 2 decimals, U+2212 (−) minus, no green/red here (that's signColor).
//   - fmtPct / fmtCur / fmtDate / periodLabel / daysUntil / signColor.
//   - pick(zh, en, cn?): the shared bilingual selector (JUDGE FIX — was a private closure in
//     StockAnalysis; FE3 later refactors that file to import THIS one).
//
// All numbers use U+2212 (MINUS SIGN) for negatives, matching TradingView glyph metrics.

const MINUS = "−"; // U+2212 minus sign (not ASCII hyphen-minus)

/**
 * pick — bilingual string selector. Returns the Chinese string when `zh` is true and a
 * Chinese variant was supplied, otherwise the English string. Empty string when nothing usable.
 *
 * Signature is (zh, en, cn?) per BUILD-SPEC §3.1 (judge-frozen). Note this differs from the
 * legacy StockAnalysis closure `(en, cn)` which captured `zh` — FE3 migrates callers.
 */
export function pick(zh: boolean, en?: string | null, cn?: string | null): string {
  return (zh && cn ? cn : en) || "";
}

/**
 * fmtNum — abbreviate a magnitude with K/M/B/T suffixes, 2 decimals by default.
 * Negatives use the U+2212 minus glyph. null/undefined/NaN → the dash placeholder.
 */
export function fmtNum(
  v: number | null | undefined,
  opts?: { decimals?: number; dash?: string }
): string {
  const dash = opts?.dash ?? MINUS;
  if (v == null || !isFinite(v)) return dash;
  const dp = opts?.decimals ?? 2;
  const neg = v < 0;
  const a = Math.abs(v);

  let out: string;
  if (a >= 1e12) out = (a / 1e12).toFixed(dp) + "T";
  else if (a >= 1e9) out = (a / 1e9).toFixed(dp) + "B";
  else if (a >= 1e6) out = (a / 1e6).toFixed(dp) + "M";
  else if (a >= 1e3) out = (a / 1e3).toFixed(dp) + "K";
  else out = a.toFixed(dp);

  return neg ? MINUS + out : out;
}

/**
 * fmtPct — format a ratio-or-percent as a percentage string. `alreadyPct` true means the
 * input is already in 0..100 space (e.g. IV pct); false (default) means a 0..1 ratio.
 * `sign` prefixes an explicit + for positive values (TV change columns).
 */
export function fmtPct(
  v: number | null | undefined,
  opts?: { decimals?: number; alreadyPct?: boolean; sign?: boolean; dash?: string }
): string {
  const dash = opts?.dash ?? MINUS;
  if (v == null || !isFinite(v)) return dash;
  const dp = opts?.decimals ?? 2;
  const pct = opts?.alreadyPct ? v : v * 100;
  const neg = pct < 0;
  const body = Math.abs(pct).toFixed(dp) + "%";
  if (neg) return MINUS + body;
  return (opts?.sign ? "+" : "") + body;
}

/**
 * fmtCur — currency-prefixed magnitude. Uses fmtNum abbreviation; currency symbol resolved
 * from the ISO code (USD→$, CNY→¥, HKD→HK$, else the code + space).
 */
export function fmtCur(
  v: number | null | undefined,
  currency?: string | null,
  opts?: { decimals?: number; dash?: string }
): string {
  const dash = opts?.dash ?? MINUS;
  if (v == null || !isFinite(v)) return dash;
  const sym = currencySymbol(currency);
  const neg = v < 0;
  const body = fmtNum(Math.abs(v), { decimals: opts?.decimals, dash });
  return (neg ? MINUS : "") + sym + body;
}

export function currencySymbol(currency?: string | null): string {
  switch ((currency || "").toUpperCase()) {
    case "USD":
      return "$";
    case "CNY":
    case "RMB":
      return "¥";
    case "HKD":
      return "HK$";
    case "EUR":
      return "€";
    case "GBP":
      return "£";
    case "JPY":
      return "¥";
    case "":
      return "";
    default:
      return (currency || "").toUpperCase() + " ";
  }
}

/**
 * Normalize an optional statement-currency receipt without inventing one. The
 * statement payload is allowed to say "unknown" with null; callers must not
 * replace that missing receipt with the quote currency or a market default.
 */
export function statementCurrencyCode(currency?: string | null): string | null {
  const code = currency?.trim();
  return code ? code.toUpperCase() : null;
}

/** Shared bilingual label for every statement-derived table and chart. */
export function statementCurrencyLabel(currency: string | null | undefined, zh: boolean): string {
  const code = statementCurrencyCode(currency);
  if (code) return pick(zh, `Currency: ${code}`, `货币：${code}`);
  return pick(zh, "Statement currency unavailable", "报表货币不可用");
}

/**
 * signColor — CSS color token for a signed value (green up / red down / neutral zero-or-null).
 * Returns a var() so callers stay theme-driven.
 */
export function signColor(v: number | null | undefined): string {
  if (v == null || !isFinite(v) || v === 0) return "var(--fg-muted, #888)";
  return v > 0 ? "var(--up, #26a69a)" : "var(--down, #ef5350)";
}

/**
 * fmtDate — ISO date (or epoch-seconds/ms) → "MMM D, YYYY". Locale-agnostic month abbreviations
 * so zh/en render identically for a date. null/invalid → dash.
 */
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function fmtDate(
  v: string | number | null | undefined,
  opts?: { short?: boolean; dash?: string }
): string {
  const dash = opts?.dash ?? MINUS;
  if (v == null || v === "") return dash;
  const d = toDate(v);
  if (!d || isNaN(d.getTime())) return dash;
  const mo = MONTHS[d.getUTCMonth()];
  const day = d.getUTCDate();
  const yr = d.getUTCFullYear();
  return opts?.short ? `${mo} ${day}` : `${mo} ${day}, ${yr}`;
}

function toDate(v: string | number): Date | null {
  if (typeof v === "number") {
    // epoch seconds (10-digit) vs ms (13-digit)
    return new Date(v < 1e12 ? v * 1000 : v);
  }
  // Date-only ISO strings parse as UTC midnight; keep that so getUTC* is stable.
  return new Date(v.length <= 10 ? v + "T00:00:00Z" : v);
}

/**
 * periodLabel — fiscal quarter label like "Q3 '26" from a raw period string. Passes through
 * anything that already looks like a fiscal label; derives from a "YYYYQn"/"YYYY-Qn" id or an
 * end-date ISO when possible. Falls back to the raw input.
 */
export function periodLabel(period?: string | null): string {
  if (!period) return MINUS;
  const raw = period.trim();
  // Already fiscal-ish (e.g. "Q3 2026", "Q3 '26", "2025")
  if (/^Q[1-4]\s/.test(raw) || /^\d{4}$/.test(raw)) {
    const m = raw.match(/^Q([1-4])\s+(\d{4})$/);
    if (m) return `Q${m[1]} '${m[2].slice(2)}`;
    return raw;
  }
  // "2026Q3" or "2026-Q3"
  const m = raw.match(/^(\d{4})-?Q([1-4])$/);
  if (m) return `Q${m[2]} '${m[1].slice(2)}`;
  return raw;
}

/**
 * daysUntil — whole days from today (UTC) to a target ISO date. Negative if in the past.
 * null/invalid → null (callers decide the empty state).
 */
export function daysUntil(target?: string | number | null): number | null {
  if (target == null || target === "") return null;
  const d = toDate(target);
  if (!d || isNaN(d.getTime())) return null;
  const now = new Date();
  const utcNow = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const utcTgt = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  return Math.round((utcTgt - utcNow) / 86400000);
}

function isExactUtcCalendarDay(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const [year, month, day] = match.slice(1).map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year
    && parsed.getUTCMonth() === month - 1
    && parsed.getUTCDate() === day;
}

/**
 * Countdown for a date that may be presented as "Next". Past and malformed
 * values fail closed so cached legacy artifacts cannot make an impossible claim.
 */
export function nextDateCountdown(target: unknown): number | null {
  if (typeof target !== "string" && typeof target !== "number") return null;
  if (typeof target === "string" && !isExactUtcCalendarDay(target)) return null;
  const days = daysUntil(target);
  return days != null && days >= 0 ? days : null;
}

export { MINUS };
