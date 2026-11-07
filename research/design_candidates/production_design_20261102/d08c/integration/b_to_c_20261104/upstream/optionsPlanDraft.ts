import { buildPin, SHORTLIST_MAX, type ShortlistPin } from "./optionsContractShortlist";

/** A research draft, prepared for an explicitly versioned Investigation adapter.
 * This is neither an admitted save payload nor a quote, order or valuation. */
export const OPTIONS_PLAN_DRAFT_SCHEMA = "options_plan_draft.v1" as const;
export interface OptionsPlanDraft {
  schema: typeof OPTIONS_PLAN_DRAFT_SCHEMA;
  legs: readonly {
    snapshot: ShortlistPin;
    assumptions: {
      side: "buy" | "sell" | null;
      quantity: number | null;
      entry: { kind: "user_assumption"; premium_per_unit: number; currency: "USD" } | null;
    };
  }[];
  research: { thesis: string; invalidation: string; horizon: string };
}
export type PlanDraftResult = { ok: true; value: OptionsPlanDraft } | { ok: false; reason: string };
type Obj = Record<string, unknown>;
const bad = (reason: string): PlanDraftResult => ({ ok: false, reason });
const object = (v: unknown): v is Obj => v !== null && typeof v === "object" && !Array.isArray(v);
const exact = (v: Obj, keys: readonly string[]) => Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v, k));
const bytes = (v: unknown) => new TextEncoder().encode(JSON.stringify(v)).length;
const text = (v: unknown, max: number, singleLine = false): v is string => typeof v === "string" && v.length <= max * 2
  && [...v].length <= max && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\ud800-\udfff]/u.test(v)
  && (!singleLine || !/[\r\n\t\u2028\u2029]/u.test(v));

/** Inspect descriptors before reading accessor values; getters are not invoked.
 * Proxy traps are not certified by this check. Row fields are retained, including
 * nested data, without coercion. Rejected graphs are not serialized. */
function cloneData(raw: unknown): unknown {
  let nodes = 0;
  let textBytes = 0;
  const ancestors = new Set<object>();
  function clone(v: unknown, depth: number): unknown {
    if (++nodes > 2048 || depth > 12) throw new Error("data_limit");
    if (v === null || typeof v === "boolean" || typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string" && text(v, 65536)) {
      textBytes += new TextEncoder().encode(v).length;
      if (textBytes > 65536) throw new Error("data_limit");
      return v;
    }
    if (!v || typeof v !== "object" || ancestors.has(v)) throw new Error("data_only");
    const array = Array.isArray(v);
    if (Object.getPrototypeOf(v) !== (array ? Array.prototype : Object.prototype) && Object.getPrototypeOf(v) !== null) throw new Error("data_only");
    const descriptors = Object.getOwnPropertyDescriptors(v);
    if (Reflect.ownKeys(v).some(k => typeof k !== "string")) throw new Error("data_only");
    ancestors.add(v);
    let result: unknown;
    if (array) {
      const length = v.length;
      if (Object.keys(descriptors).length !== length + 1 || length > 2048) throw new Error("data_only");
      result = Array.from({ length }, (_, i) => {
        const d = descriptors[String(i)];
        if (!d || !Object.hasOwn(d, "value") || !d.enumerable) throw new Error("data_only");
        return clone(d.value, depth + 1);
      });
    } else {
      const copy: Obj = {};
      for (const [key, d] of Object.entries(descriptors)) {
        if (["__proto__", "prototype", "constructor"].includes(key) || !text(key, 65536) || !Object.hasOwn(d, "value") || !d.enumerable) throw new Error("data_only");
        textBytes += new TextEncoder().encode(key).length;
        if (textBytes > 65536) throw new Error("data_limit");
        copy[key] = clone(d.value, depth + 1);
      }
      result = copy;
    }
    ancestors.delete(v);
    return Object.freeze(result);
  }
  return clone(raw, 0);
}

function rowDepth(v: unknown, depth = 0): boolean {
  if (depth > 8) return false;
  return !v || typeof v !== "object" || Object.values(v).every(child => rowDepth(child, depth + 1));
}
function snapshot(raw: unknown): raw is ShortlistPin {
  if (!object(raw) || !exact(raw, ["pinKey", "identity", "family", "hotView", "session", "asofRaw", "schema", "sourceStale", "row"])
      || !object(raw.row) || !rowDepth(raw.row) || bytes(raw.row) > 8192
      || !object(raw.identity) || !exact(raw.identity, ["root", "right", "exp", "strike", "terms", "key", "adjustedRootHint"])
      || !object(raw.identity.terms) || !exact(raw.identity.terms, ["multiplier", "deliverable", "settlement", "exercise_style"])
      || !["doi", "hot"].includes(String(raw.family)) || typeof raw.sourceStale !== "boolean"
      || !text(raw.asofRaw, 128, true) || !raw.asofRaw || !(raw.schema === null || text(raw.schema, 256, true))
      || !(raw.hotView === null || ["by_volume", "by_premium"].includes(String(raw.hotView)))
      || raw.family === "doi" && raw.hotView !== null) return false;
  const bound = buildPin(raw.row, {
    family: raw.family as ShortlistPin["family"], hotView: raw.hotView as ShortlistPin["hotView"],
    asof: raw.asofRaw, schema: raw.schema as string | null, stale: raw.sourceStale,
  }, [raw.row]);
  if (!bound.ok || bound.pin.session !== raw.session || bound.pin.pinKey !== raw.pinKey) return false;
  const id = bound.pin.identity;
  const supplied = raw.identity, terms = supplied.terms as Obj;
  return ["root", "right", "exp", "strike", "key", "adjustedRootHint"].every(k => supplied[k] === id[k as keyof typeof id])
    && Object.keys(id.terms).every(k => terms[k] === id.terms[k as keyof typeof id.terms]);
}

/** Validate and copy source field values before exposing an immutable draft.
 * This confirms a coherent retained observation, not provider authenticity or
 * a fresh ambiguity check against the original full source list. */
export function validateOptionsPlanDraft(raw: unknown): PlanDraftResult {
  let v: unknown;
  try { v = cloneData(raw); } catch { return bad("data_only_or_limit"); }
  if (bytes(v) > 65536) return bad("draft_too_large");
  if (!object(v) || !exact(v, ["schema", "legs", "research"]) || v.schema !== OPTIONS_PLAN_DRAFT_SCHEMA
      || !Array.isArray(v.legs) || v.legs.length < 1 || v.legs.length > SHORTLIST_MAX) return bad("draft_shape");
  if (!object(v.research) || !exact(v.research, ["thesis", "invalidation", "horizon"])
      || !text(v.research.thesis, 4000) || !text(v.research.invalidation, 4000) || !text(v.research.horizon, 160, true)) return bad("research_text");
  const identities = new Set<string>();
  let root: string | null = null;
  for (const leg of v.legs) {
    if (!object(leg) || !exact(leg, ["snapshot", "assumptions"]) || !snapshot(leg.snapshot)) return bad("source_snapshot");
    const pin = leg.snapshot;
    if (root !== null && root !== pin.identity.root) return bad("mixed_root");
    root = pin.identity.root;
    if (identities.has(pin.identity.key)) return bad("duplicate_contract");
    identities.add(pin.identity.key);
    const a = leg.assumptions;
    if (!object(a) || !exact(a, ["side", "quantity", "entry"]) || !(a.side === null || a.side === "buy" || a.side === "sell")
        || !(a.quantity === null || Number.isSafeInteger(a.quantity) && Number(a.quantity) > 0 && Number(a.quantity) <= 1000000)) return bad("leg_assumptions");
    const e = a.entry;
    if (e !== null && (!object(e) || !exact(e, ["kind", "premium_per_unit", "currency"]) || e.kind !== "user_assumption" || e.currency !== "USD"
      || typeof e.premium_per_unit !== "number" || !Number.isFinite(e.premium_per_unit) || e.premium_per_unit < 0)) return bad("entry_assumption");
  }
  return { ok: true, value: v as unknown as OptionsPlanDraft };
}

/** The person must author every assumption; dated reference marks never enter
 * the assumption object. Source clocks and missing terms remain as received. */
export function createOptionsPlanDraft(pins: readonly ShortlistPin[]): PlanDraftResult {
  let safe: readonly ShortlistPin[];
  try { safe = cloneData(pins) as readonly ShortlistPin[]; } catch { return bad("data_only_or_limit"); }
  if (!Array.isArray(safe)) return bad("draft_shape");
  return validateOptionsPlanDraft({
    schema: OPTIONS_PLAN_DRAFT_SCHEMA,
    legs: safe.map(pin => ({ snapshot: pin, assumptions: { side: null, quantity: null, entry: null } })),
    research: { thesis: "", invalidation: "", horizon: "" },
  });
}
