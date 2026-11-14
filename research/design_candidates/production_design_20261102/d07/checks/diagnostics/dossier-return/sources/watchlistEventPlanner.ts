/**
 * Watchlist event planner — the pure model behind the cross-company agenda (E14).
 *
 * SOURCE. There is exactly one accepted company-event source in the Terminal: each company's
 * `<SYM>.fund.json` → `earnings.next_date` / `earnings.next_period`, written by the fundamentals
 * emitters through `ingest/earnings_calendar.py::select_next_earnings_date`. That contract is a
 * DATE-ONLY calendar day (`YYYY-MM-DD`, the earliest report day not before the current UTC day).
 * It carries no time of day, no time zone, no confirmation status and no revision history. This
 * module consumes exactly what the source carries and labels every missing field as missing; it
 * never invents a time, a confirmation or a quiet day. It is not a second calendar producer: no
 * file is written, nothing is scheduled, no reminder exists.
 *
 * TRUTH RULES (the acceptance contract):
 *   1. A date-only record stays a calendar day. It is formatted with `timeZone: "UTC"` from
 *      `Date.UTC`, so no viewer zone can shift it or attach a clock time to it.
 *   2. An exact instant (an ISO date-time WITH an explicit offset) is kept as one epoch value;
 *      the exchange-zone and viewer-zone renderings are both formatted from that same value.
 *      A date-time WITHOUT an offset cannot be placed on the timeline, so it is "unreadable".
 *   3. Event identity is `earnings:<SYMBOL>:<period>`. A later read of the same identity replaces
 *      the earlier one (a reschedule or correction), and the agenda dedupes by identity.
 *   4. Coverage is explicit. A company that was not read, could not be read, is not covered by the
 *      source, or carries a date the reader cannot interpret is UNKNOWN — never "no events".
 *      So is a company whose answer is not current: a saved copy the network has not confirmed
 *      yet, an earlier copy whose refresh failed, or a report date that has already passed with
 *      no new one. Only when every company in the list has a current answer may the planner say
 *      that none of them has an upcoming date, and even then it never calls a day "quiet".
 */
import type { CacheOutcome, GetOpts } from "./dataCache";
import { canonicalChartSymbol } from "./terminalBoot";
import { marketOf, type MarketId } from "./markets";
import { isComposite } from "./composite";
import { nextDateCountdown } from "./finFormat";

// ── bounds ─────────────────────────────────────────────────────────────────────────────────

/** Companies read per batch. A larger list is read in user-requested batches, never all at once. */
export const EVENT_READ_LIMIT = 50;
/** Concurrent fund-file reads. */
export const EVENT_READ_CONCURRENCY = 4;

// ── types ──────────────────────────────────────────────────────────────────────────────────

export type EventKind = "earnings";

export type EventWhen =
  /** A calendar day with no time of day. `day` is `YYYY-MM-DD`. */
  | { precision: "date"; day: string }
  /**
   * One exact instant. `day` is the calendar day on the exchange's clock (UTC when the exchange
   * zone is unknown), so the agenda groups an after-hours report under the exchange's day.
   */
  | { precision: "instant"; day: string; epochMs: number; exchangeTz: string | null };

export interface PlannerEvent {
  /** Stable identity: `earnings:<SYMBOL>:<period|next>`. */
  id: string;
  symbol: string;
  kind: EventKind;
  /** The source's own period label ("Q4 2026"), or null when the source does not state one. */
  period: string | null;
  when: EventWhen;
  /** The source carries no confirmation field, so this is always "unstated". */
  confirmation: "unstated";
  /** The fund file's own `asof` day, when it states one. */
  sourceAsOf: string | null;
  /** The day this same identity carried earlier in this tab session, when it has since moved. */
  previousDay: string | null;
}

/**
 * How current an "event"/"no-date" answer is. Both flags false is a current answer.
 *   stale          served from a saved copy older than the cache TTL whose background refresh has
 *                  not confirmed it (still running, or replaced before it answered).
 *   refreshFailed  a later read of this company failed, so the answer on screen is an earlier copy.
 */
export interface ReadCurrency {
  stale: boolean;
  refreshFailed: boolean;
}

/**
 * What one list symbol contributed. Every state other than "event"/"no-date" is UNKNOWN coverage,
 * and an "event"/"no-date" answer counts as current only when `isCurrentAnswer` says so.
 */
export type SymbolRead =
  | { state: "pending" }
  | ({ state: "event"; event: PlannerEvent } & ReadCurrency)
  | ({ state: "no-date"; reason: "none" | "past" } & ReadCurrency)
  | { state: "unreadable" }
  | { state: "absent" }
  | { state: "unavailable" }
  | { state: "not-read" }
  | { state: "not-company" };

export type SymbolReadState = SymbolRead["state"];

export interface SymbolProfile {
  /** True when the symbol can carry company report dates (not an index, crypto pair or basket). */
  company: boolean;
  exchangeTz: string | null;
}

// ── symbols ────────────────────────────────────────────────────────────────────────────────

const EXCHANGE_ZONES: Partial<Record<MarketId, string>> = {
  us: "America/New_York",
  ca: "America/Toronto",
  cn: "Asia/Shanghai",
  hk: "Asia/Hong_Kong",
};

/** The IANA zone a market's exchange clock runs on, or null when the venue group is not mapped. */
export function exchangeZoneFor(market: MarketId): string | null {
  return EXCHANGE_ZONES[market] ?? null;
}

/**
 * Whether a list symbol can carry company report dates, and on which exchange clock.
 * Indexes (`^GSPC`), futures/FX (`ES=F`, `EURUSD=X`), crypto pairs and `+` baskets have no
 * company fundamentals file, so they are never fetched and never counted as unread companies.
 */
export function profileSymbol(symbol: string, row?: { mkt?: string; sec?: string } | null): SymbolProfile {
  const canonical = canonicalChartSymbol(symbol);
  if (!canonical) return { company: false, exchangeTz: null };
  if (canonical.startsWith("^") || canonical.includes("=") || canonical.includes("+") || isComposite(canonical)) {
    return { company: false, exchangeTz: null };
  }
  const market = marketOf(canonical, row ?? null);
  if (market === "crypto") return { company: false, exchangeTz: null };
  return { company: true, exchangeTz: exchangeZoneFor(market) };
}

/** The fund-file URL for one company, or null when the value is not a usable symbol. */
export function companyEventUrl(symbol: string): string | null {
  const canonical = canonicalChartSymbol(symbol);
  return canonical ? `/data/${encodeURIComponent(canonical)}.fund.json` : null;
}

/** List entries → unique canonical symbols, in list order. */
export function uniqueListSymbols(entries: readonly { symbol?: unknown }[] | null | undefined): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const entry of entries ?? []) {
    const canonical = canonicalChartSymbol(entry?.symbol);
    if (!canonical || seen.has(canonical)) continue;
    seen.add(canonical);
    out.push(canonical);
  }
  return out;
}

// ── date parsing ───────────────────────────────────────────────────────────────────────────

const DAY_RE = /^(\d{4})-(\d{2})-(\d{2})$/;
const INSTANT_RE = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,9})?)?(Z|[+-]\d{2}:?\d{2})$/i;

function isCalendarDay(value: string): boolean {
  const match = DAY_RE.exec(value);
  if (!match) return false;
  const [year, month, day] = match.slice(1).map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day;
}

/** The calendar day (`YYYY-MM-DD`) an instant falls on in `timeZone`. */
export function dayInZone(epochMs: number, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(epochMs));
  const pick = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${pick("year")}-${pick("month")}-${pick("day")}`;
}

export type ParsedNextDate =
  | { kind: "when"; when: EventWhen }
  | { kind: "none" }
  | { kind: "past" }
  | { kind: "unreadable" };

/**
 * Interpret `earnings.next_date`.
 *
 * - `null` → the source states no known upcoming date ("none").
 * - `YYYY-MM-DD` → a date-only day, admitted by the SAME fail-closed rule the company Earnings page
 *   uses (`nextDateCountdown`): a past day is "past", a non-existent day is "unreadable".
 * - ISO date-time with `Z` or an explicit offset → one exact instant.
 * - Anything else (a date-time with no offset, a number, junk) → "unreadable". Nothing is repaired.
 */
export function parseNextDate(raw: unknown, exchangeTz: string | null, nowMs: number = Date.now()): ParsedNextDate {
  if (raw === null) return { kind: "none" };
  if (typeof raw !== "string") return { kind: "unreadable" };
  const value = raw.trim();
  if (DAY_RE.test(value)) {
    if (!isCalendarDay(value)) return { kind: "unreadable" };
    return nextDateCountdown(value) == null ? { kind: "past" } : { kind: "when", when: { precision: "date", day: value } };
  }
  const instant = INSTANT_RE.exec(value);
  if (instant) {
    if (!isCalendarDay(`${instant[1]}-${instant[2]}-${instant[3]}`)) return { kind: "unreadable" };
    const epochMs = Date.parse(value);
    if (!Number.isFinite(epochMs)) return { kind: "unreadable" };
    if (epochMs < nowMs) return { kind: "past" };
    return { kind: "when", when: { precision: "instant", epochMs, exchangeTz, day: dayInZone(epochMs, exchangeTz ?? "UTC") } };
  }
  return { kind: "unreadable" };
}

// ── identity ───────────────────────────────────────────────────────────────────────────────

export function eventIdentity(symbol: string, period: string | null): string {
  return `earnings:${symbol}:${period && period.trim() ? period.trim() : "next"}`;
}

/** What one identity carried earlier in this tab session. */
export interface SeenDay {
  day: string;
  /** The earlier day this identity moved from, once it has moved. */
  movedFrom: string | null;
}

/**
 * Days each identity carried earlier in this tab session (memory only — nothing is persisted).
 * A later read whose day differs is a reschedule or correction: it REPLACES the earlier entry and
 * records where it moved from, and that note survives later reads of the new day.
 */
export const sessionSeenDays: Map<string, SeenDay> = new Map();

export function noteReschedule(event: PlannerEvent, seen: Map<string, SeenDay> = sessionSeenDays): PlannerEvent {
  const before = seen.get(event.id);
  let movedFrom: string | null = null;
  if (before) movedFrom = before.day === event.when.day ? before.movedFrom : before.day;
  seen.set(event.id, { day: event.when.day, movedFrom });
  return { ...event, previousDay: movedFrom };
}

// ── outcome → read ─────────────────────────────────────────────────────────────────────────

/** Interpret one company's fund payload. A payload without a readable earnings block is unknown. */
export function interpretFundPayload(
  symbol: string,
  data: unknown,
  profile: SymbolProfile,
  opts: { nowMs?: number; seen?: Map<string, SeenDay>; refreshFailed?: boolean; stale?: boolean } = {},
): SymbolRead {
  const currency: ReadCurrency = { stale: !!opts.stale, refreshFailed: !!opts.refreshFailed };
  if (!data || typeof data !== "object") return { state: "unreadable" };
  const earnings = (data as { earnings?: unknown }).earnings;
  if (!earnings || typeof earnings !== "object" || !("next_date" in earnings)) return { state: "unreadable" };
  const block = earnings as { next_date?: unknown; next_period?: unknown };
  const parsed = parseNextDate(block.next_date, profile.exchangeTz, opts.nowMs);
  if (parsed.kind === "unreadable") return { state: "unreadable" };
  if (parsed.kind === "none") return { state: "no-date", reason: "none", ...currency };
  if (parsed.kind === "past") return { state: "no-date", reason: "past", ...currency };
  const period = typeof block.next_period === "string" && block.next_period.trim() ? block.next_period.trim() : null;
  const asof = (data as { asof?: unknown }).asof;
  const event: PlannerEvent = {
    id: eventIdentity(symbol, period),
    symbol,
    kind: "earnings",
    period,
    when: parsed.when,
    confirmation: "unstated",
    sourceAsOf: typeof asof === "string" && isCalendarDay(asof.slice(0, 10)) ? asof.slice(0, 10) : null,
    previousDay: null,
  };
  return { state: "event", event: noteReschedule(event, opts.seen), ...currency };
}

/**
 * Map a cache outcome to a read. A failed read is never an empty result, and a copy the cache
 * served stale is marked stale until its refresh confirms or corrects it.
 */
export function outcomeToRead(
  symbol: string,
  outcome: CacheOutcome,
  profile: SymbolProfile,
  opts: { nowMs?: number; seen?: Map<string, SeenDay> } = {},
): SymbolRead {
  if (outcome.status === "absent") return { state: "absent" };
  if (outcome.status === "unavailable") return { state: "unavailable" };
  return interpretFundPayload(symbol, outcome.data, profile, { ...opts, stale: !!outcome.stale });
}

/**
 * Whether a read is a CURRENT answer: the file was read and interpreted, from a copy that is not
 * stale and not an earlier copy whose refresh failed, and it does not rest on a date that has
 * already passed. Only current answers may support a claim that a company has no upcoming date.
 */
export function isCurrentAnswer(read: SymbolRead): boolean {
  if (read.state !== "event" && read.state !== "no-date") return false;
  if (read.stale || read.refreshFailed) return false;
  return !(read.state === "no-date" && read.reason === "past");
}

/**
 * Settle a new read over the answer already held for that company. A read that could not reach
 * the source never replaces an answer already on screen: the earlier answer stays, marked as an
 * earlier copy whose latest read failed (failure-state truth). Every other read — fresh data, a
 * proven absence, an uninterpretable file — replaces it.
 */
export function settleRead(before: SymbolRead | undefined, next: SymbolRead): SymbolRead {
  if (next.state === "unavailable" && before && (before.state === "event" || before.state === "no-date")) {
    return { ...before, refreshFailed: true };
  }
  return next;
}

// ── bounded reader ─────────────────────────────────────────────────────────────────────────

export interface EventReadJob {
  symbol: string;
  profile: SymbolProfile;
}

export interface EventReadOptions {
  read: (url: string, opts?: GetOpts) => Promise<CacheOutcome>;
  /** Bypass fresh/stale copies and ask the network (a user-requested re-read). */
  force?: boolean;
  concurrency?: number;
  /** False once the list, the batch or the view changed — every late answer is then dropped. */
  isCurrent: () => boolean;
  /**
   * False once the LIST (or the view) changed. A one-shot correction of a stale copy still belongs
   * to its list after a mere batch change (e.g. "read next 50"), so corrections check this instead.
   * Defaults to `isCurrent`.
   */
  isListCurrent?: () => boolean;
  onResult: (symbol: string, read: SymbolRead) => void;
  /** A stale copy was served and its background refresh failed. */
  onRefreshFailed?: (symbol: string) => void;
  seen?: Map<string, SeenDay>;
  now?: () => number;
}

/**
 * Read a batch of companies with at most `concurrency` requests in flight. No timer, no polling:
 * the only follow-up is the cache's own one-shot revalidation of a stale copy. A stale copy is
 * reported with `stale: true`; its revalidation either corrects the row in place (same identity,
 * `stale: false`), marks it as an earlier copy when the refresh fails, or — when the cache replaced
 * that refresh before it answered — leaves it marked stale.
 */
export async function runEventReads(jobs: readonly EventReadJob[], options: EventReadOptions): Promise<void> {
  const concurrency = Math.max(1, Math.min(options.concurrency ?? EVENT_READ_CONCURRENCY, jobs.length));
  const now = options.now ?? Date.now;
  const listIsCurrent = options.isListCurrent ?? options.isCurrent;
  let next = 0;
  const worker = async () => {
    while (options.isCurrent()) {
      const index = next;
      next += 1;
      if (index >= jobs.length) return;
      const job = jobs[index];
      const url = companyEventUrl(job.symbol);
      if (!url) {
        options.onResult(job.symbol, { state: "unavailable" });
        continue;
      }
      const getOpts: GetOpts = options.force
        ? { ttl: 0, swr: false }
        : {
            onRevalidate: (fresh: unknown) => {
              if (!listIsCurrent()) return;
              options.onResult(job.symbol, interpretFundPayload(job.symbol, fresh, job.profile, { nowMs: now(), seen: options.seen }));
            },
          };
      let outcome: CacheOutcome;
      try {
        outcome = await options.read(url, getOpts);
      } catch {
        outcome = { status: "unavailable", reason: "network" };
      }
      if (!options.isCurrent()) return;
      options.onResult(job.symbol, outcomeToRead(job.symbol, outcome, job.profile, { nowMs: now(), seen: options.seen }));
      if (outcome.status === "data" && outcome.stale) {
        // "ok" already delivered the corrected payload through onRevalidate (the cache calls it
        // before settling); "superseded" never answered, so the row stays marked stale.
        void outcome.stale.revalidation.then((result) => {
          if (result === "failed" && listIsCurrent()) options.onRefreshFailed?.(job.symbol);
        });
      }
    }
  };
  await Promise.all(Array.from({ length: concurrency }, worker));
}

// ── agenda + coverage ──────────────────────────────────────────────────────────────────────

export interface AgendaGroup {
  kind: EventKind;
  events: PlannerEvent[];
}

export interface AgendaDay {
  day: string;
  groups: AgendaGroup[];
}

function whenSortKey(when: EventWhen): number {
  // Within a day, exact instants come first in time order; date-only rows follow.
  return when.precision === "instant" ? when.epochMs : Number.MAX_SAFE_INTEGER;
}

/** Group the read events by day, then by event type. One entry per identity. */
export function buildAgenda(reads: Readonly<Record<string, SymbolRead>>): AgendaDay[] {
  const byId = new Map<string, PlannerEvent>();
  for (const read of Object.values(reads)) {
    if (read.state === "event") byId.set(read.event.id, read.event);
  }
  const events = [...byId.values()].sort((a, b) =>
    a.when.day.localeCompare(b.when.day)
    || whenSortKey(a.when) - whenSortKey(b.when)
    || a.symbol.localeCompare(b.symbol));
  const days: AgendaDay[] = [];
  for (const event of events) {
    let day = days[days.length - 1];
    if (!day || day.day !== event.when.day) {
      day = { day: event.when.day, groups: [] };
      days.push(day);
    }
    let group = day.groups.find((g) => g.kind === event.kind);
    if (!group) {
      group = { kind: event.kind, events: [] };
      day.groups.push(group);
    }
    group.events.push(event);
  }
  return days;
}

export interface EventCoverage {
  /** Symbols in the list. */
  symbols: number;
  /** Symbols that can carry company report dates. */
  companies: number;
  /** Companies whose file was read and interpreted (event or stated no-date), current or not. */
  read: number;
  /** Companies with a CURRENT answer (see `isCurrentAnswer`). */
  current: number;
  withEvent: number;
  noDate: number;
  pending: number;
  unavailable: number;
  absent: number;
  unreadable: number;
  notRead: number;
  /** Answers shown from an earlier copy because the latest read failed. */
  refreshFailed: number;
  /** Answers shown from a saved copy the network has not confirmed (and whose read did not fail). */
  stale: number;
  /** Companies whose last known report date has passed with no new date in the source. */
  outdated: number;
  notCompany: number;
  /** Every company has a current answer — the ONLY state that may support an empty claim. */
  complete: boolean;
}

export function summarizeCoverage(symbols: readonly string[], reads: Readonly<Record<string, SymbolRead>>): EventCoverage {
  const c: EventCoverage = {
    symbols: symbols.length, companies: 0, read: 0, current: 0, withEvent: 0, noDate: 0, pending: 0, unavailable: 0,
    absent: 0, unreadable: 0, notRead: 0, refreshFailed: 0, stale: 0, outdated: 0, notCompany: 0, complete: false,
  };
  for (const symbol of symbols) {
    const read = reads[symbol] ?? { state: "pending" };
    if (read.state === "not-company") { c.notCompany += 1; continue; }
    c.companies += 1;
    if (read.state === "event" || read.state === "no-date") {
      c.read += 1;
      if (read.state === "event") c.withEvent += 1; else c.noDate += 1;
      if (read.refreshFailed) c.refreshFailed += 1;
      else if (read.stale) c.stale += 1;
      if (read.state === "no-date" && read.reason === "past") c.outdated += 1;
      if (isCurrentAnswer(read)) c.current += 1;
      continue;
    }
    switch (read.state) {
      case "pending": c.pending += 1; break;
      case "unavailable": c.unavailable += 1; break;
      case "absent": c.absent += 1; break;
      case "unreadable": c.unreadable += 1; break;
      case "not-read": c.notRead += 1; break;
    }
  }
  c.complete = c.companies > 0 && c.current === c.companies;
  return c;
}

/** Companies whose events are UNKNOWN (everything but a current answer). */
export function unknownCount(c: EventCoverage): number {
  return c.companies - c.current;
}

// ── formatting ─────────────────────────────────────────────────────────────────────────────

export type PlannerLang = "en" | "zh";

function locale(lang: PlannerLang): string {
  return lang === "zh" ? "zh-CN" : "en-US";
}

function utcDate(day: string): Date {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, date));
}

/** A calendar day as a heading ("Thu, Oct 29, 2026"). Always formatted in UTC: no clock, no shift. */
export function formatDayHeading(day: string, lang: PlannerLang): string {
  return new Intl.DateTimeFormat(locale(lang), { weekday: "short", month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }).format(utcDate(day));
}

/** A short calendar day ("Oct 29"). Always formatted in UTC. */
export function formatShortDay(day: string, lang: PlannerLang): string {
  return new Intl.DateTimeFormat(locale(lang), { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }).format(utcDate(day));
}

/** Whole UTC days from today to `day` (the source's own day boundary), or null when past/invalid. */
export function daysUntilDay(day: string): number | null {
  return nextDateCountdown(day);
}

export interface InstantRendering {
  epochMs: number;
  timeZone: string;
  /** Clock time with zone ("4:30 PM EDT"). */
  time: string;
  /** Calendar day in that zone (`YYYY-MM-DD`). */
  day: string;
}

/** Render one instant in one zone. Both sides of the dual time come from the SAME epoch value. */
export function renderInstant(epochMs: number, timeZone: string, lang: PlannerLang): InstantRendering {
  const time = new Intl.DateTimeFormat(locale(lang), { hour: "numeric", minute: "2-digit", timeZone, timeZoneName: "short" }).format(new Date(epochMs));
  return { epochMs, timeZone, time, day: dayInZone(epochMs, timeZone) };
}

/** The viewer's own zone (the browser's resolved zone), or UTC when it cannot be resolved. */
export function viewerTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export interface DualTime {
  exchange: InstantRendering | null;
  local: InstantRendering;
}

/** Exchange-clock and viewer-clock renderings of one exact instant. */
export function dualTime(when: Extract<EventWhen, { precision: "instant" }>, lang: PlannerLang, viewerTz: string = viewerTimeZone()): DualTime {
  return {
    exchange: when.exchangeTz ? renderInstant(when.epochMs, when.exchangeTz, lang) : null,
    local: renderInstant(when.epochMs, viewerTz, lang),
  };
}
