/** Pure display-only W1 projection. No fetching, caching, risk or decision imports. */
type ObjectValue = Record<string, unknown>;
export type AuctionAmount = number | string | null;
export type AuctionEvent = {
  type: "AUCTION"; impact: null; assets: ["bonds"]; settled_payment_observed: null; raw_class_flags: Record<string, string | null>; raw_security_type: string | null; raw_type: string | null;
  episode_id: string; normalized_class: string; label: string; date: string; time_et: string | null;
  auction_date: string; issue_date: string; announcement_date: string | null;
  announced_cusip: string | null; issued_cusip: string | null;
  competitive_deadline_utc: string | null; known_at: string; source: string; source_url: string;
  source_state: string; physical_state: string; issue_calendar_state: string;
  offering_amount_usd: AuctionAmount; result: Record<string, AuctionAmount> | null;
  result_evidence_fields: string[]; null_reasons: string[];
  is_context_only: true; forecast_authority: "RESEARCH_ONLY"; probabilities: null; importance: "NOT_SCORED";
};
export type AuctionSourceHealth = {
  source_kind: string; source_url: string; latest_attempt_at: string; latest_attempt_status: string;
  latest_attempt_states: string[]; last_successful_body_receipt_at: string | null;
  last_valid_observation_at: string | null; last_valid_observation_age_seconds: number | null;
  latest_failure_at: string | null; latest_failure_reasons: string[]; freshness_basis: string;
  stale_after_seconds: null;
};
export type AuctionContext = {
  schema_version: "sovereign_auction_context_v1"; is_context_only: true; forecast_authority: "RESEARCH_ONLY";
  probabilities: null; importance: "NOT_SCORED"; as_of: string; decision_cutoff_utc: string;
  source_observed_at: string | null; asof: string | null; status: string;
  events: AuctionEvent[]; episodes: AuctionEvent[]; source_health: AuctionSourceHealth[];
};
export type AuctionValidation = { ok: true; context: AuctionContext } | { ok: false; reason: "absent" | "invalid" };
const STATES = ["available", "empty", "degraded", "unavailable", "unsupported", "conflicting_source_states"];
const RESULT_KEYS = ["competitive_accepted_usd", "competitive_tendered_usd", "total_accepted_usd", "primary_dealer_accepted_usd", "direct_bidder_accepted_usd", "indirect_bidder_accepted_usd", "bid_to_cover_ratio", "high_discount_rate_pct", "high_discount_margin_pct", "frn_spread_pct", "real_yield_pct", "nominal_yield_pct", "bidder_shares"];
function object(x: unknown): ObjectValue { if (!x || typeof x !== "object" || Array.isArray(x)) throw Error(); return x as ObjectValue; }
function text(x: unknown): string { if (typeof x !== "string" || !x || x.length > 2048) throw Error(); return x; }
// Preserve raw source spelling, including empty fields; W1 treats trimmed empties as missing.
function rawText(x: unknown): string { if (typeof x !== "string" || x.length > 2048) throw Error(); return x; }
function strings(x: unknown): string[] { if (!Array.isArray(x) || x.length > 128) throw Error(); return x.map(text); }
function oneOf(x: unknown, choices: string[]): string { const s = text(x); if (!choices.includes(s)) throw Error(); return s; }
function day(x: unknown): string {
  const s = text(x);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s) || !Number.isFinite(Date.parse(s)) || new Date(s).toISOString().slice(0, 10) !== s) throw Error();
  return s;
}
function clock(x: unknown): string {
  const s = text(x);
  // Mandatory offset, strict civil date/time ranges, and a real calendar day.
  const m = s.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(Z|[+-](\d{2}):(\d{2}))$/);
  if (!m || +m[2] > 23 || +m[3] > 59 || +m[4] > 59 || (m[6] && (+m[6] > 23 || +m[7] > 59)) || !Number.isFinite(Date.parse(s))) throw Error();
  day(m[1]); return s;
}
function nullable<T>(x: unknown, check: (x: unknown) => T): T | null { return x === null ? null : check(x); }
// Date.parse truncates producer microseconds; compare the preserved instant instead.
function instant(s: string): bigint {
  const fraction = s.match(/\.(\d{1,6})(?:Z|[+-]\d{2}:\d{2})$/)?.[1] ?? "";
  return BigInt(Date.parse(s)) * BigInt(1000) + BigInt(fraction.padEnd(6, "0").slice(3));
}
function easternDay(s: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(s));
}
function evidenceClock(x: unknown, cutoff: bigint, now: bigint): string {
  const s = clock(x); if (instant(s) > cutoff || instant(s) > now) throw Error(); return s;
}
function official(x: unknown): string {
  const s = text(x); const u = new URL(s);
  if (u.protocol !== "https:" || u.username || u.password || u.port || !["www.treasurydirect.gov", "treasurydirect.gov", "home.treasury.gov", "api.fiscaldata.treasury.gov"].includes(u.hostname)) throw Error();
  return s;
}
function amount(x: unknown): AuctionAmount {
  if (x === null) return null;
  if (typeof x === "number" && Number.isFinite(x)) return x;
  // W1 preserves decimal dollar strings to avoid a lossy conversion of exact source values.
  if (typeof x === "string" && /^-?\d+(?:\.\d+)?$/.test(x) && Number.isFinite(Number(x))) return x;
  throw Error();
}
function classFlag(x: unknown): boolean | null {
  if (x === null) return null;
  const s = rawText(x).trim().toLowerCase(); if (!s) return null; if (["yes", "y"].includes(s)) return true; if (["no", "n"].includes(s)) return false; throw Error();
}
function validateClass(e: ObjectValue, expected: string, flags: ObjectValue): void {
  const classes: Record<string, string> = { bill: "Bill", cmb: "CMB", note: "Note", bond: "Bond", tips: "TIPS", frn: "FRN" };
  const base = classes[text(e.raw_security_type).trim().toLowerCase()];
  const rawType = e.raw_type === null ? null : rawText(e.raw_type).trim().toLowerCase();
  const explicit = rawType ? classes[rawType] : null;
  if (!["Bill", "Note", "Bond"].includes(base) || (rawType && !explicit)) throw Error();
  const special: Record<string, boolean | null> = { CMB: classFlag(flags.cashManagementBillCMB), TIPS: classFlag(flags.tips), FRN: classFlag(flags.floatingRate) };
  const trueFlags = Object.keys(special).filter(k => special[k] === true);
  const inferred = trueFlags[0] ?? base, kind = explicit ?? inferred;
  const allowed: Record<string, string[]> = { CMB: ["Bill"], TIPS: ["Note", "Bond"], FRN: ["Note"] };
  if (trueFlags.length > 1 || kind !== expected || (trueFlags.length && kind !== inferred) || (allowed[kind] && !allowed[kind].includes(base)) || special[kind] === false || (["Bill", "Note", "Bond"].includes(kind) && kind !== base)) throw Error();
}
function authority(x: ObjectValue): void {
  if (x.is_context_only !== true || x.forecast_authority !== "RESEARCH_ONLY" || x.probabilities !== null || x.importance !== "NOT_SCORED") throw Error();
}
function evidenceTree(x: unknown, cutoff: bigint, now: bigint, depth = 0): void {
  if (depth > 12) throw Error();
  if (Array.isArray(x)) { if (x.length > 2048) throw Error(); x.forEach(v => evidenceTree(v, cutoff, now, depth + 1)); }
  else if (x && typeof x === "object") {
    for (const [key, value] of Object.entries(x)) {
      if (["known_at", "observed_at", "first_observed_at", "publication_time"].includes(key) && value !== null) evidenceClock(value, cutoff, now);
      else if (typeof value === "object" && value !== null) evidenceTree(value, cutoff, now, depth + 1);
    }
  }
}
export function validateSovereignAuctionContext(value: unknown, nowMs: number): AuctionValidation {
  if (value == null) return { ok: false, reason: "absent" };
  try {
    if (!Number.isFinite(nowMs)) throw Error();
    const c = object(value); authority(c);
    if (c.schema_version !== "sovereign_auction_context_v1") throw Error();
    const now = BigInt(Math.floor(nowMs)) * BigInt(1000); // Injected millisecond clock is a conservative lower bound.
    const decision_cutoff_utc = evidenceClock(c.decision_cutoff_utc, now, now);
    const cutoff = instant(decision_cutoff_utc); const as_of = clock(c.as_of);
    if (instant(as_of) !== cutoff) throw Error();
    const cutoffDateET = easternDay(decision_cutoff_utc);
    evidenceTree(c, cutoff, now);
    const source_observed_at = nullable(c.source_observed_at, x => evidenceClock(x, cutoff, now));
    const asof = nullable(c.asof, day);
    if (asof !== (source_observed_at?.slice(0, 10) ?? null)) throw Error();
    const status = oneOf(c.status, ["available", "degraded", "unavailable", "unsupported"]);
    if (!Array.isArray(c.source_health) || c.source_health.length > 128 || !Array.isArray(c.events) || c.events.length > 2048 || !Array.isArray(c.episodes)) throw Error();
    const source_health = c.source_health.map(v => {
      const h = object(v); const ev = (x: unknown) => evidenceClock(x, cutoff, now);
      const latest_attempt_at = ev(h.latest_attempt_at);
      const last_valid_observation_at = nullable(h.last_valid_observation_at, ev);
      const age = h.last_valid_observation_age_seconds;
      if (h.stale_after_seconds !== null || (age !== null && (typeof age !== "number" || !Number.isFinite(age) || age < 0))) throw Error();
      if ((last_valid_observation_at === null) !== (age === null) || (last_valid_observation_at && Math.abs(Number(cutoff - instant(last_valid_observation_at)) / 1_000_000 - (age as number)) > .0000005)) throw Error();
      const last_successful_body_receipt_at = nullable(h.last_successful_body_receipt_at, ev);
      const latest_failure_at = nullable(h.latest_failure_at, ev);
      if ([last_valid_observation_at, last_successful_body_receipt_at, latest_failure_at].some(s => s && instant(s) > instant(latest_attempt_at))) throw Error();
      return { source_kind: text(h.source_kind), source_url: official(h.source_url), latest_attempt_at,
        latest_attempt_status: oneOf(h.latest_attempt_status, STATES), latest_attempt_states: strings(h.latest_attempt_states).map(s => oneOf(s, STATES)),
        last_successful_body_receipt_at, last_valid_observation_at, last_valid_observation_age_seconds: age as number | null,
        latest_failure_at, latest_failure_reasons: strings(h.latest_failure_reasons), freshness_basis: text(h.freshness_basis), stale_after_seconds: null } satisfies AuctionSourceHealth;
    });
    const validClocks = source_health.flatMap(h => h.last_valid_observation_at ? [h.last_valid_observation_at] : []);
    const maxClock = validClocks.sort((a,b) => instant(a) < instant(b) ? 1 : instant(a) > instant(b) ? -1 : 0)[0] ?? null;
    if (source_observed_at !== maxClock) throw Error();
    const ids = new Set<string>();
    const events = c.events.map(v => {
      const e = object(v); authority(e);
      if (e.type !== "AUCTION" || e.impact !== null || JSON.stringify(e.assets) !== '["bonds"]' || e.settled_payment_observed !== null) throw Error();
      const episode_id = text(e.episode_id); if (ids.has(episode_id)) throw Error(); ids.add(episode_id);
      const normalized_class = oneOf(e.normalized_class, ["Bill", "CMB", "Note", "Bond", "TIPS", "FRN"]);
      const auction_date = day(e.auction_date), issue_date = day(e.issue_date), date = day(e.date);
      if (date !== auction_date || issue_date < auction_date) throw Error();
      const announced_cusip = nullable(e.announced_cusip, text), issued_cusip = nullable(e.issued_cusip, text);
      for (const cusip of [announced_cusip, issued_cusip]) if (cusip && !/^[A-Z0-9]{9}$/.test(cusip)) throw Error();
      if (announced_cusip ? episode_id !== `auction:${announced_cusip}:${auction_date}` : !episode_id.startsWith("tentative:")) throw Error();
      const flags = object(e.raw_class_flags);
      validateClass(e, normalized_class, flags);
      const competitive_deadline_utc = nullable(e.competitive_deadline_utc, clock); // Scheduled futures are valid.
      const known_at = evidenceClock(e.known_at, cutoff, now), source_url = official(e.source_url), source = official(e.source);
      if (source !== source_url || !source_health.some(h => h.source_url === source_url && h.last_valid_observation_at && instant(h.last_valid_observation_at) >= instant(known_at))) throw Error();
      const source_state = oneOf(e.source_state, ["ANNOUNCED", "TENTATIVE", "RESULT_OBSERVED"]);
      const physical_state = oneOf(e.physical_state, ["ANNOUNCED", "TENTATIVE", "AWAITING_RESULT", "RESULT_OBSERVED"]);
      const result_evidence_fields = strings(e.result_evidence_fields).map(s => oneOf(s, ["pdfFilenameCompetitiveResults", "xmlFilenameCompetitiveResults", "competitiveAccepted", "competitiveTendered", "bidToCoverRatio", "highYield", "highDiscountRate", "highDiscountMargin"]));
      const expectedPhysical = source_state === "RESULT_OBSERVED" ? "RESULT_OBSERVED"
        : ((competitive_deadline_utc && cutoff >= instant(competitive_deadline_utc)) || auction_date < cutoffDateET) ? "AWAITING_RESULT" : source_state;
      if (physical_state !== expectedPhysical) throw Error();
      if (e.first_observed_at != null && instant(evidenceClock(e.first_observed_at, cutoff, now)) > instant(known_at)) throw Error();
      const issue_calendar_state = oneOf(e.issue_calendar_state, ["ISSUE_DATE_PASSED", "ISSUE_DATE_NOT_PASSED"]);
      if (issue_calendar_state !== (issue_date < cutoffDateET ? "ISSUE_DATE_PASSED" : "ISSUE_DATE_NOT_PASSED")) throw Error();
      let result: Record<string, AuctionAmount> | null = null;
      if (e.result !== null) {
        const r = object(e.result); result = {};
        for (const key of RESULT_KEYS) { result[key] = amount(r[key]); if (key.endsWith("_usd") && result[key] !== null && Number(result[key]) < 0) throw Error(); }
        if (source_state !== "RESULT_OBSERVED" || physical_state !== "RESULT_OBSERVED" || !result_evidence_fields.length || (competitive_deadline_utc && instant(competitive_deadline_utc) > instant(known_at))) throw Error();
        const knownDateET = easternDay(known_at);
        if (auction_date > knownDateET) throw Error();
      } else if (source_state === "RESULT_OBSERVED" || physical_state === "RESULT_OBSERVED" || result_evidence_fields.length) throw Error();
      const offering_amount_usd = amount(e.offering_amount_usd); if (offering_amount_usd !== null && Number(offering_amount_usd) < 0) throw Error();
      const time_et = nullable(e.time_et, text); if (time_et && !/^([01]\d|2[0-3]):[0-5]\d$/.test(time_et)) throw Error();
      return { type: "AUCTION", impact: null, assets: ["bonds"], settled_payment_observed: null, raw_security_type: nullable(e.raw_security_type, rawText), raw_type: nullable(e.raw_type, rawText), raw_class_flags: { tips: nullable(flags.tips, rawText), floatingRate: nullable(flags.floatingRate, rawText), cashManagementBillCMB: nullable(flags.cashManagementBillCMB, rawText) }, episode_id, normalized_class, label: text(e.label), date, time_et, auction_date, issue_date,
        announcement_date: nullable(e.announcement_date, day), announced_cusip, issued_cusip, competitive_deadline_utc, known_at, source, source_url,
        source_state, physical_state, issue_calendar_state,
        offering_amount_usd, result, result_evidence_fields, null_reasons: strings(e.null_reasons),
        is_context_only: true, forecast_authority: "RESEARCH_ONLY", probabilities: null, importance: "NOT_SCORED" } satisfies AuctionEvent;
    });
    return { ok: true, context: { schema_version: "sovereign_auction_context_v1", is_context_only: true, forecast_authority: "RESEARCH_ONLY", probabilities: null, importance: "NOT_SCORED", as_of, decision_cutoff_utc, source_observed_at, asof, status, events, episodes: events, source_health } };
  } catch { return { ok: false, reason: "invalid" }; }
}
/** Scheduled/awaiting first, observed results second; stable chronology within each group. */
export function auctionDisplayRows(context: AuctionContext, limit = 6): { rows: AuctionEvent[]; total: number } {
  const sorted = context.events.map((row, order) => ({ row, order })).sort((a,b) =>
    Number(a.row.result !== null) - Number(b.row.result !== null) || a.row.auction_date.localeCompare(b.row.auction_date) ||
    (a.row.competitive_deadline_utc ?? "").localeCompare(b.row.competitive_deadline_utc ?? "") || a.order - b.order);
  return { rows: sorted.slice(0, Math.max(0, Math.min(24, Math.trunc(limit)))).map(({ row }) => row), total: sorted.length };
}
