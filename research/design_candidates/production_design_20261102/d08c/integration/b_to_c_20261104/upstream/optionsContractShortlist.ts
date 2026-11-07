/**
 * Exact-contract shortlist + side-by-side comparison for the Options Screener
 * (E15). Pure, React-free, and read-only over rows the screener already
 * fetched — no quote feed, no pricing model, no score, no payoff.
 *
 * Source semantics this module encodes (Macro `engine/options_hub.py`,
 * `scripts/build_options_hub_nightly.py`):
 *
 * - "Open-interest builds" (`options_hub.oi_movers/v1`, preset `doi`):
 *     `oi`      — open-interest report dated `asof` (positions at the close
 *                 BEFORE the `asof` session; OI is reported a day late).
 *     `oi_prev` — the earlier report; `d_oi = oi - oi_prev`.
 *     `mid`     — (EOD bid + EOD ask) / 2 at the `asof` close. A reference
 *                 mark, never an executable quote. May be null.
 * - "Hot contracts" (`options_hub.hot/v1`, preset `hot`):
 *     `close`   — last trade at the `asof` close. A reference mark.
 *     `vol`     — contracts traded in the `asof` session.
 *     `premium` — the source's estimate close × vol × 100. The 100 is the
 *                 producer's assumption, not a confirmed contract term.
 *     `oi_prev` — open-interest report dated `asof` (nullable).
 *     `vol_gt_oi` — boolean or null.
 *
 * Neither list supplies a bid, ask, quote size/depth, spread, multiplier,
 * deliverable, settlement or exercise style. Those comparison rows therefore
 * stay `not_supplied` — they are never defaulted to a "standard" contract.
 * When a future row DOES carry `multiplier` / `deliverable` / `settlement` /
 * `exercise_style`, those values become part of the exact identity key so two
 * adjusted deliverables can never collapse into one ticker/strike label.
 */

import type { ScreenerHotView } from "./optionsScreener";

export type ShortlistFamily = "doi" | "hot";

/** Maximum pinned contracts; comparison needs at least two. */
export const SHORTLIST_MAX = 4;
export const SHORTLIST_COMPARE_MIN = 2;

/** Contract terms a source MAY supply. `null` = not supplied. Never defaulted. */
export interface ContractTerms {
  multiplier: number | null;
  deliverable: string | null;
  settlement: string | null;
  exercise_style: string | null;
}

export interface ContractIdentity {
  /** Root exactly as the source printed it — never trimmed, upper-cased or stripped. */
  root: string;
  right: "C" | "P";
  /** Full ISO expiry date (YYYY-MM-DD). */
  exp: string;
  strike: number;
  terms: ContractTerms;
  /** Exact key over every identity part, supplied terms included. */
  key: string;
  /**
   * The root ends in a digit (e.g. `NVDA1`). By OCC convention that is how an
   * adjusted, non-standard deliverable is usually listed. A hint to show, not
   * a fact to compute with.
   */
  adjustedRootHint: boolean;
}

export type IdentityRefusal =
  | "root"      // missing / empty / whitespace-bearing root
  | "right"     // not exactly "C" or "P"
  | "exp"       // not a full, real YYYY-MM-DD date
  | "strike"    // not a finite positive number
  | "terms"     // a supplied term is malformed (cannot be bound safely)
  | "ambiguous" // the same list carries this exact identity more than once
  | "session"   // (pin only) the source snapshot has no as-of date at all
  | "full";     // (pin only) the shortlist already holds SHORTLIST_MAX contracts

export type IdentityResult =
  | { ok: true; identity: ContractIdentity }
  | { ok: false; reason: IdentityRefusal };

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

function isRealIsoDate(s: string): boolean {
  const m = ISO_DATE.exec(s);
  if (!m) return false;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  const dt = new Date(Date.UTC(y, mo - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === mo - 1 && dt.getUTCDate() === d;
}

type TermRead<T> = { ok: true; value: T | null } | { ok: false };

function readNumberTerm(row: Readonly<Record<string, unknown>>, field: string): TermRead<number> {
  if (!(field in row)) return { ok: true, value: null };
  const v = row[field];
  if (v === null || v === undefined) return { ok: true, value: null };
  if (typeof v === "number" && Number.isFinite(v) && v > 0) return { ok: true, value: v };
  return { ok: false };
}

function readStringTerm(row: Readonly<Record<string, unknown>>, field: string): TermRead<string> {
  if (!(field in row)) return { ok: true, value: null };
  const v = row[field];
  if (v === null || v === undefined) return { ok: true, value: null };
  if (typeof v === "string" && v.trim().length > 0) return { ok: true, value: v };
  return { ok: false };
}

function keyPart(v: string | number | null): string {
  return v === null ? "?" : `=${encodeURIComponent(String(v))}`;
}

/**
 * Bind a source row to its exact contract identity, or refuse with a reason.
 * Nothing is normalized: `NVDA` and `NVDA1` stay two contracts, and a supplied
 * multiplier of 50 and one of 100 stay two contracts.
 */
export function contractIdentity(row: unknown): IdentityResult {
  if (!row || typeof row !== "object") return { ok: false, reason: "root" };
  const r = row as Readonly<Record<string, unknown>>;
  const root = r.root;
  if (typeof root !== "string" || root.length === 0 || /\s/.test(root)) return { ok: false, reason: "root" };
  const right = r.right;
  if (right !== "C" && right !== "P") return { ok: false, reason: "right" };
  const exp = r.exp;
  if (typeof exp !== "string" || !isRealIsoDate(exp)) return { ok: false, reason: "exp" };
  const strike = r.strike;
  if (typeof strike !== "number" || !Number.isFinite(strike) || strike <= 0) return { ok: false, reason: "strike" };

  const multiplier = readNumberTerm(r, "multiplier");
  const deliverable = readStringTerm(r, "deliverable");
  const settlement = readStringTerm(r, "settlement");
  const exercise = readStringTerm(r, "exercise_style");
  if (!multiplier.ok || !deliverable.ok || !settlement.ok || !exercise.ok) return { ok: false, reason: "terms" };

  const terms: ContractTerms = {
    multiplier: multiplier.value,
    deliverable: deliverable.value,
    settlement: settlement.value,
    exercise_style: exercise.value,
  };
  const key = [
    `=${encodeURIComponent(root)}`, right, exp, `=${String(strike)}`,
    keyPart(terms.multiplier), keyPart(terms.deliverable), keyPart(terms.settlement), keyPart(terms.exercise_style),
  ].join("|");
  return {
    ok: true,
    identity: { root, right, exp, strike, terms, key, adjustedRootHint: /\d$/.test(root) },
  };
}

const ambiguityCache = new WeakMap<readonly unknown[], ReadonlySet<string>>();

/**
 * Identity keys that occur more than once in ONE source list. Two rows that
 * bind to the same exact identity mean the source itself collapsed something
 * (or duplicated a row); pinning either would be an unsafe guess.
 */
export function ambiguousIdentityKeys(list: readonly unknown[]): ReadonlySet<string> {
  const hit = ambiguityCache.get(list);
  if (hit) return hit;
  const seen = new Set<string>();
  const dup = new Set<string>();
  for (const row of list) {
    const id = contractIdentity(row);
    if (!id.ok) continue;
    if (seen.has(id.identity.key)) dup.add(id.identity.key);
    else seen.add(id.identity.key);
  }
  ambiguityCache.set(list, dup);
  return dup;
}

/** The declared snapshot a pin was taken from. */
export interface ShortlistSource {
  family: ShortlistFamily;
  /** Payload `asof` exactly as served (ISO date or datetime), or null if absent. */
  asof: string | null | undefined;
  schema?: string | null;
  /** `/api/flow` marks an expired / failed-refresh cache with `stale: true`. */
  stale?: boolean | null;
  /** Hot list the row came from; null for open-interest builds. */
  hotView?: ScreenerHotView | null;
}

export interface ShortlistPin {
  /** identity key + list + session — the same contract from two lists is two pins. */
  pinKey: string;
  identity: ContractIdentity;
  family: ShortlistFamily;
  hotView: ScreenerHotView | null;
  /** Session date (YYYY-MM-DD) taken from the payload `asof`. */
  session: string;
  asofRaw: string;
  schema: string | null;
  sourceStale: boolean;
  /** Frozen copy of the row as it was when pinned. */
  row: Readonly<Record<string, unknown>>;
}

/** Session date of a payload `asof`, or null when it carries no usable date. */
export function sessionOf(asof: string | null | undefined): string | null {
  if (typeof asof !== "string") return null;
  const d = asof.slice(0, 10);
  return isRealIsoDate(d) ? d : null;
}

export function pinKeyFor(identityKey: string, family: ShortlistFamily, session: string): string {
  return `${family}@${session}#${identityKey}`;
}

export type PinBuild = { ok: true; pin: ShortlistPin } | { ok: false; reason: IdentityRefusal };

/**
 * Build a pin for `row` from `source`. `list` is the FULL source list the row
 * came from (unfiltered), used for the ambiguity check.
 */
export function buildPin(row: unknown, source: ShortlistSource, list: readonly unknown[]): PinBuild {
  const id = contractIdentity(row);
  if (!id.ok) return id;
  if (ambiguousIdentityKeys(list).has(id.identity.key)) return { ok: false, reason: "ambiguous" };
  const session = sessionOf(source.asof);
  if (!session) return { ok: false, reason: "session" };
  return {
    ok: true,
    pin: {
      pinKey: pinKeyFor(id.identity.key, source.family, session),
      identity: id.identity,
      family: source.family,
      hotView: source.family === "hot" ? (source.hotView ?? null) : null,
      session,
      asofRaw: String(source.asof),
      schema: source.schema ?? null,
      sourceStale: source.stale === true,
      row: Object.freeze({ ...(row as Record<string, unknown>) }),
    },
  };
}

export type AddResult = "added" | "exists" | "full";

/** Never mutates `pins`. A full shortlist is refused, not silently rotated. */
export function addPin(pins: readonly ShortlistPin[], pin: ShortlistPin): { pins: readonly ShortlistPin[]; result: AddResult } {
  if (pins.some((p) => p.pinKey === pin.pinKey)) return { pins, result: "exists" };
  if (pins.length >= SHORTLIST_MAX) return { pins, result: "full" };
  return { pins: [...pins, pin], result: "added" };
}

export function removePin(pins: readonly ShortlistPin[], pinKey: string): readonly ShortlistPin[] {
  return pins.some((p) => p.pinKey === pinKey) ? pins.filter((p) => p.pinKey !== pinKey) : pins;
}

/** Where a pin's originating row is now, relative to what the table renders. */
export type PinLocation = "present" | "hidden_by_filter" | "not_in_list";

/**
 * Locate a pin in the CURRENT source list without touching any filter, sort
 * or view: `present` means navigating to the originating table will show it.
 */
export function locatePin(
  pin: ShortlistPin,
  currentList: readonly unknown[] | null | undefined,
  rootFilter: string,
): PinLocation {
  if (!currentList) return "not_in_list";
  const found = currentList.some((row) => {
    const id = contractIdentity(row);
    return id.ok && id.identity.key === pin.identity.key;
  });
  if (!found) return "not_in_list";
  if (rootFilter && pin.identity.root !== rootFilter) return "hidden_by_filter";
  return "present";
}

// ── Comparison ────────────────────────────────────────────────────────────────

export type CompareFieldId =
  | "bid_ask" | "spread" | "quote_size"
  | "mid" | "close"
  | "oi" | "oi_earlier" | "oi_change"
  | "volume" | "traded_value" | "vol_above_oi"
  | "multiplier" | "deliverable" | "settlement" | "exercise_style";

/** What kind of evidence a field is. `executable_quote` rows are never filled from a mark. */
export type FieldBasis = "executable_quote" | "reference_mark" | "positions" | "activity" | "source_estimate" | "contract_term";

/** Which observation (and therefore which clock) a value belongs to. */
export type ObservationId =
  | "eod_mid"          // midpoint of EOD bid/ask at the session close
  | "eod_close"        // last trade at the session close
  | "oi_report"        // open-interest report dated the session (positions at the prior close)
  | "oi_report_prior"  // the earlier open-interest report
  | "oi_report_change" // difference between the two reports
  | "session_volume"   // contracts traded in the session
  | "premium_estimate" // source estimate close × volume × 100
  | "vol_vs_oi"        // session volume vs report-dated open interest
  | "term_supplied";   // a contract term the source supplied

export type CompareCell =
  | { state: "value"; value: number | boolean | string; observation: ObservationId; session: string }
  /** The list carries this field, but this row's value is null. Stays null. */
  | { state: "missing"; observation: ObservationId; session: string }
  /** The other list carries this field; this one does not. */
  | { state: "not_in_list" }
  /** No list in this view supplies it (executable quote, depth, contract terms). */
  | { state: "not_supplied" };

export interface CompareRow {
  field: CompareFieldId;
  basis: FieldBasis;
  cells: CompareCell[];
}

export const COMPARE_FIELDS: ReadonlyArray<{ field: CompareFieldId; basis: FieldBasis }> = [
  { field: "bid_ask", basis: "executable_quote" },
  { field: "spread", basis: "executable_quote" },
  { field: "quote_size", basis: "executable_quote" },
  { field: "mid", basis: "reference_mark" },
  { field: "close", basis: "reference_mark" },
  { field: "oi", basis: "positions" },
  { field: "oi_earlier", basis: "positions" },
  { field: "oi_change", basis: "positions" },
  { field: "volume", basis: "activity" },
  { field: "traded_value", basis: "source_estimate" },
  { field: "vol_above_oi", basis: "activity" },
  { field: "multiplier", basis: "contract_term" },
  { field: "deliverable", basis: "contract_term" },
  { field: "settlement", basis: "contract_term" },
  { field: "exercise_style", basis: "contract_term" },
];

/** Which list carries each source-row field: [family, row key, observation]. */
const FIELD_SOURCE: Partial<Record<CompareFieldId, ReadonlyArray<readonly [ShortlistFamily, string, ObservationId]>>> = {
  mid: [["doi", "mid", "eod_mid"]],
  close: [["hot", "close", "eod_close"]],
  oi: [["doi", "oi", "oi_report"], ["hot", "oi_prev", "oi_report"]],
  oi_earlier: [["doi", "oi_prev", "oi_report_prior"]],
  oi_change: [["doi", "d_oi", "oi_report_change"]],
  volume: [["hot", "vol", "session_volume"]],
  traded_value: [["hot", "premium", "premium_estimate"]],
  vol_above_oi: [["hot", "vol_gt_oi", "vol_vs_oi"]],
};

function finiteOrNull(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function cellFor(pin: ShortlistPin, field: CompareFieldId, basis: FieldBasis): CompareCell {
  // An executable quote is never synthesized from a mark, a close or a model.
  if (basis === "executable_quote") return { state: "not_supplied" };
  if (basis === "contract_term") {
    const v = pin.identity.terms[field as keyof ContractTerms];
    return v === null || v === undefined
      ? { state: "not_supplied" }
      : { state: "value", value: v, observation: "term_supplied", session: pin.session };
  }
  const src = FIELD_SOURCE[field]?.find(([fam]) => fam === pin.family);
  if (!src) return { state: "not_in_list" };
  const [, key, observation] = src;
  const raw = pin.row[key];
  if (field === "vol_above_oi") {
    return typeof raw === "boolean"
      ? { state: "value", value: raw, observation, session: pin.session }
      : { state: "missing", observation, session: pin.session };
  }
  const n = finiteOrNull(raw);
  return n === null
    ? { state: "missing", observation, session: pin.session }
    : { state: "value", value: n, observation, session: pin.session };
}

export interface CompareNotes {
  /** Distinct session dates across pins, in pin order. */
  sessions: string[];
  /** More than one session date — values were not observed at the same close. */
  sessionMismatch: boolean;
  /** Pins come from both lists — each carries different fields and clocks. */
  listMix: boolean;
  /** At least one pin came from a snapshot the server flagged stale. */
  stale: boolean;
  /** Identity keys pinned from more than one list. */
  sameContractTwice: string[];
  /** At least one pinned root has the adjusted-contract numeric suffix. */
  adjustedRoot: boolean;
  /** At least one pin has no supplied multiplier (always true on today's sources). */
  termsUnknown: boolean;
  /** True only when every pin shares one session and one list, none stale. */
  likeForLike: boolean;
}

export interface Comparison {
  pins: readonly ShortlistPin[];
  rows: CompareRow[];
  notes: CompareNotes;
  /** False below SHORTLIST_COMPARE_MIN pins. */
  ready: boolean;
}

export function buildComparison(pins: readonly ShortlistPin[]): Comparison {
  const rows: CompareRow[] = COMPARE_FIELDS.map(({ field, basis }) => ({
    field,
    basis,
    cells: pins.map((p) => cellFor(p, field, basis)),
  }));
  const sessions: string[] = [];
  for (const p of pins) if (!sessions.includes(p.session)) sessions.push(p.session);
  const families = new Set(pins.map((p) => p.family));
  const byIdentity = new Map<string, Set<ShortlistFamily>>();
  for (const p of pins) {
    const s = byIdentity.get(p.identity.key) ?? new Set<ShortlistFamily>();
    s.add(p.family);
    byIdentity.set(p.identity.key, s);
  }
  const sessionMismatch = sessions.length > 1;
  const listMix = families.size > 1;
  const stale = pins.some((p) => p.sourceStale);
  return {
    pins,
    rows,
    ready: pins.length >= SHORTLIST_COMPARE_MIN,
    notes: {
      sessions,
      sessionMismatch,
      listMix,
      stale,
      sameContractTwice: [...byIdentity.entries()].filter(([, f]) => f.size > 1).map(([k]) => k),
      adjustedRoot: pins.some((p) => p.identity.adjustedRootHint),
      termsUnknown: pins.some((p) => p.identity.terms.multiplier === null),
      likeForLike: pins.length >= SHORTLIST_COMPARE_MIN && !sessionMismatch && !listMix && !stale,
    },
  };
}
