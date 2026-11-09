"use client";
/**
 * LevelsView — the Terminal "Levels" board (Voltick Gamma-Levels WP-A3).
 *
 * A gamma weather map: a vertical strike-altitude column where each strike is
 * tinted by where dealer hedging concentrates. Named nodes (Keystone, Ceiling,
 * Floor, Flip, Cluster, Backstop, Void, Trapdoor, Launchpad, Stack) are pinned
 * along the column at their strike, over a sticky/slippery terrain tint.
 *
 * DISPLAY-ONLY DOCTRINE:
 *   - Levels are LOCATIONS where dealer hedging concentrates — positioning, not
 *     prophecy. Nothing here forecasts direction or advises a trade.
 *   - The dealer-sign convention (sticky = positive net gamma, slippery =
 *     negative) is ASSUMED, not measured — the ribbon and the source line say so.
 *   - Open interest updates once a day, so the map is a snapshot, not a live tape.
 *   - Absent levels render honestly as "not present" — never a fabricated strike.
 *   - A read that did not land is not an absence: only a 404/410 (or a published payload
 *     with no map for the root) shows the empty-root copy (lvNoLevels). A failed first read is
 *     a load error with a Retry; a failed refresh keeps the map and says it is the last read.
 *
 * Data:
 *   /api/flow?f=levels:<ROOT>  →  levels.v1 payload (see schema below).
 *   Read via the shared flowGetResult client; polled ~60s while the tab is visible.
 *   In dev (FLOW_FIXTURE=1) the route serves public/data/levels_fixture.json.
 */

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { flowGetResult, flowInvalidate, type FlowOutcome } from "@/lib/flowClientCache";
import { isValidRoot } from "@/lib/flowRoot";
import { useLang, useT } from "@/lib/i18n";
import { trackSearch } from "@/lib/searchTrack";
import {
  ROLE_GLYPH,
  STACK_GLYPH,
  levelsReadLabel,
  notPresentLabel,
  roleLabel,
  stackLabel,
  type LevelsReadKey,
  type Role,
} from "./levelsLabels";

// ─── levels.v1 schema (pinned to engine/levels_engine.py origin/main) ──────────

interface LevelNode {
  role: Role;
  strike: number | null;
  weight: number | null;
  sticky: boolean | null;
  brightness: number | null;
  note: string;
  // void-only extras
  strike_lo?: number | null;
  strike_hi?: number | null;
  n_strikes?: number | null;
}

interface LevelStack {
  strike: number;
  roles: string[];
  note: string;
}

interface LevelsPayload {
  schema: string;
  root: string | null;
  asof: string | null;
  spot: number | null;
  regime: {
    net_gamma: number | null;
    net_gamma_unit: string | null;
    label: "sticky" | "slippery" | null;
    ribbon: string;
  } | null;
  nodes: LevelNode[];
  stacks: LevelStack[];
  palette_hint: {
    colorblind?: boolean;
    sticky: string;
    slippery: string;
    law?: string;
  } | null;
  source: {
    source_schema?: string | null;
    source_asof?: string | null;
    source_convention?: string | null;
    note?: string;
  } | null;
}

// The order named nodes sit in the side rail (matches the engine emission order,
// most-magnetic first). Voids are ranges and get their own band overlay.
const RAIL_ORDER: Role[] = [
  "anchor", "call_wall", "put_wall", "flip",
  "cluster", "launchpad", "counter", "trapdoor",
];

// ─── Palette / color law ──────────────────────────────────────────────────────
//
// Sticky = price tends to hold (green); slippery = price tends to slide (red).
// The colorblind toggle repaints via the payload's blue/orange hint. We map the
// payload's CSS color-NAME hints ("green"/"red"/"blue"/"orange") onto the
// Terminal's theme tokens so the board flips with the app's up/down convention
// and stays on-brand, rather than using raw web colors.

interface Palette {
  stickyRGB: string;   // "r,g,b" for rgba() terrain fills
  slipperyRGB: string;
  stickyVar: string;   // solid color for glyphs/labels
  slipperyVar: string;
  neutralVar: string;  // flips/voids — no dealer sign
}

const PALETTE_THEME: Palette = {
  stickyRGB: "var(--up-rgb)",
  slipperyRGB: "var(--down-rgb)",
  stickyVar: "var(--up)",
  slipperyVar: "var(--down)",
  neutralVar: "var(--text-2)",
};
// Colorblind: the payload swaps green→blue, red→orange. We honor that with
// fixed, high-contrast blue/orange that read distinctly for deuteranopia.
const PALETTE_CB: Palette = {
  stickyRGB: "77,130,255",     // brand blue
  slipperyRGB: "232,163,61",   // warn orange
  stickyVar: "#4d82ff",
  slipperyVar: "#e8a33d",
  neutralVar: "var(--text-2)",
};

// ─── Ticker selector roots (mirror the GEX desk) ──────────────────────────────

const QUICK_ROOTS = ["SPY", "QQQ", "IWM", "NVDA", "TSLA", "META", "AAPL"];
const AUTOCOMPLETE_ROOTS = [
  "SPY", "QQQ", "IWM", "DIA", "SPX", "NDX", "RUT",
  "NVDA", "TSLA", "AAPL", "META", "AMZN", "MSFT", "GOOGL", "GOOG", "AMD", "NFLX",
  "AVGO", "MU", "PLTR", "COIN", "SMCI", "MSTR", "BABA", "INTC", "CRM", "ORCL",
];

// ─── Polling ──────────────────────────────────────────────────────────────────

const POLL_MS = 60_000;

async function readFlow(f: string): Promise<FlowOutcome> {
  try {
    return await flowGetResult(f);
  } catch {
    return { status: "unavailable", reason: "network" };
  }
}

/** What the latest read for the current root established. `loading` until it settles. */
type LevelsRead = "loading" | "data" | "absent" | "unavailable";

/**
 * The map for `root` in a /api/flow answer. A published object that carries no map for
 * the root is the honest empty (FLOW_FIXTURE serves `{}` for a root it has none for);
 * anything that is not an object at all is a read that did not land.
 */
function levelsFor(data: unknown, root: string): LevelsPayload | null | "malformed" {
  if (!data || typeof data !== "object" || Array.isArray(data)) return "malformed";
  const rec = data as Record<string, unknown>;
  if ("nodes" in rec && String(rec.root ?? "").toUpperCase() === root) return rec as unknown as LevelsPayload;
  if (rec[root] && typeof rec[root] === "object") return rec[root] as LevelsPayload;
  return null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtStrike(x: number | null | undefined): string {
  if (x == null) return "—";
  return x >= 100 ? x.toFixed(2).replace(/\.00$/, "") : x.toFixed(2);
}

const LEVEL_RUNG_MIN_GAP = 26 / 360;
const LEVEL_RUNG_EDGE_GUTTER = 14 / 360;

/**
 * Spread display labels apart while preserving each level's exact raw price Y.
 * This only moves the readable rung/button when two prices project too close to
 * fit without overlap (or into the edge gutter). An unmoved rung is centred on its
 * own price; a moved one keeps an exact-price tick on the axis (RUNG_ANCHOR).
 */
function spreadLevelYs(rawYs: readonly number[]): number[] {
  if (rawYs.length === 0) return [];
  const floor = LEVEL_RUNG_EDGE_GUTTER;
  const ceiling = 1 - LEVEL_RUNG_EDGE_GUTTER;
  const sorted = rawYs
    .map((raw, index) => ({
      index,
      raw: Math.max(floor, Math.min(ceiling, Number.isFinite(raw) ? raw : 0.5)),
    }))
    .sort((a, b) => a.raw - b.raw || a.index - b.index);

  if (sorted.length === 1) return [sorted[0].raw];

  const gap = Math.min(
    LEVEL_RUNG_MIN_GAP,
    (ceiling - floor) / (sorted.length - 1),
  );
  const placed = new Array<number>(sorted.length);
  placed[0] = sorted[0].raw;
  for (let i = 1; i < sorted.length; i += 1) {
    placed[i] = Math.max(sorted[i].raw, placed[i - 1] + gap);
  }
  if (placed[placed.length - 1] > ceiling) {
    placed[placed.length - 1] = ceiling;
    for (let i = placed.length - 2; i >= 0; i -= 1) {
      placed[i] = Math.min(placed[i], placed[i + 1] - gap);
    }
  }

  const out = new Array<number>(rawYs.length);
  sorted.forEach((item, index) => { out[item.index] = placed[index]; });
  return out;
}

/** Rounded band [min,max] across every located strike + spot, padded a touch. */
function priceBand(payload: LevelsPayload | null): [number, number] | null {
  if (!payload) return null;
  const xs: number[] = [];
  if (payload.spot != null) xs.push(payload.spot);
  for (const n of payload.nodes) {
    if (n.strike != null) xs.push(n.strike);
    if (n.strike_lo != null) xs.push(n.strike_lo);
    if (n.strike_hi != null) xs.push(n.strike_hi);
  }
  if (xs.length === 0) return null;
  let lo = Math.min(...xs);
  let hi = Math.max(...xs);
  if (lo === hi) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.06;
  return [lo - pad, hi + pad];
}

// ─── Component ────────────────────────────────────────────────────────────────

export function LevelsView() {
  const { lang } = useLang();
  const t = useT();
  const tRead = (key: LevelsReadKey) => levelsReadLabel(key, lang);

  const [ticker, setTicker]     = useState("SPY");
  const [inputVal, setInputVal] = useState("SPY");
  const [payload, setPayload]   = useState<LevelsPayload | null>(null);
  const [read, setRead]         = useState<LevelsRead>("loading");
  const [colorblind, setColorblind] = useState(false);
  const [selected, setSelected] = useState<{ key: string; label: string; note: string } | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const colorHintAppliedRef = useRef(false);
  // Every read takes a sequence number; only the latest may paint. A root the user has
  // left, or a poll a newer read overtook, never lands on the board.
  const readSeqRef = useRef(0);

  const fetchLevels = useCallback(async (root: string, force = false) => {
    if (!force && typeof document !== "undefined" && document.visibilityState === "hidden") return;
    const seq = ++readSeqRef.current;
    const outcome = await readFlow(`levels:${root}`);
    if (readSeqRef.current !== seq) return;
    const levels = outcome.status === "data" ? levelsFor(outcome.data, root) : null;
    if (outcome.status === "unavailable" || levels === "malformed") {
      // Keep whatever map is on screen — it is the last read, and the board says so.
      if (levels === "malformed") flowInvalidate(`levels:${root}`);
      setRead("unavailable");
    } else if (outcome.status === "absent" || levels === null) {
      setPayload(null);
      setRead("absent");
    } else {
      setPayload(levels);
      setRead("data");
    }
  }, []);

  const loadTicker = useCallback(async (root: string) => {
    setRead("loading");
    setPayload(null);
    setSelected(null);
    await fetchLevels(root, true);
  }, [fetchLevels]);

  // Retry re-reads in place. With no map held the column returns to its reading state;
  // with one held the map stays up until the new read lands.
  const retryLevels = useCallback(() => {
    flowInvalidate(`levels:${ticker}`);
    if (!payload) setRead("loading");
    void fetchLevels(ticker, true);
  }, [fetchLevels, payload, ticker]);

  useEffect(() => {
    void loadTicker(ticker);
    pollRef.current = setInterval(() => void fetchLevels(ticker), POLL_MS);
    const onVis = () => { if (document.visibilityState === "visible") void fetchLevels(ticker); };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [fetchLevels, loadTicker, ticker]);

  const loading = read === "loading";
  const loadFailed = read === "unavailable" && !payload;
  const refreshFailed = read === "unavailable" && payload != null;
  // The rail may call a level "not present" only when a map was read (it lacks the role)
  // or the store proved it has no map. Unread is "—", never an absence.
  const absenceKnown = payload != null || read === "absent";

  // Honor the payload's own colorblind hint the first time it loads.
  useEffect(() => {
    if (!colorHintAppliedRef.current && payload?.palette_hint?.colorblind) {
      colorHintAppliedRef.current = true;
      setColorblind(true);
    }
  }, [payload]);

  const commitTicker = useCallback(() => {
    const root = inputVal.trim().toUpperCase();
    // The route's own root rule: a root /api/flow would refuse is never committed.
    if (isValidRoot(root) && root !== ticker) {
      trackSearch(root, "levels-board", inputVal.trim() || undefined);
      setTicker(root);
    }
  }, [inputVal, ticker]);

  const palette = colorblind ? PALETTE_CB : PALETTE_THEME;
  const band = useMemo(() => priceBand(payload), [payload]);

  // Project a price onto the column (0 = top / highest strike, 1 = bottom).
  const projY = useCallback((price: number): number => {
    if (!band) return 0.5;
    const [lo, hi] = band;
    return hi === lo ? 0.5 : (hi - price) / (hi - lo);
  }, [band]);

  // Located, weighted nodes for the terrain column (exclude flips/voids/nulls).
  const terrainNodes = useMemo(
    () => (payload?.nodes ?? []).filter(
      (n) => n.strike != null && n.sticky != null && n.brightness != null
    ),
    [payload]
  );
  const terrainLayout = useMemo(() => {
    const rawYs = terrainNodes.map((n) => projY(n.strike as number));
    const displayYs = spreadLevelYs(rawYs);
    return terrainNodes.map((node, index) => ({
      node,
      index,
      rawY: rawYs[index],
      displayY: displayYs[index],
    }));
  }, [projY, terrainNodes]);
  const voidNodes = useMemo(
    () => (payload?.nodes ?? []).filter((n) => n.role === "void" && n.strike_lo != null && n.strike_hi != null),
    [payload]
  );
  const flipNode = useMemo(
    () => (payload?.nodes ?? []).find((n) => n.role === "flip" && n.strike != null) ?? null,
    [payload]
  );

  // The side-rail entries: one per named role, in RAIL_ORDER. Multiple clusters
  // collapse to their brightest representative on the rail (all still show as
  // markers on the column). Absent roles render as an honest "not present" row.
  const railEntries = useMemo(() => {
    const nodes = payload?.nodes ?? [];
    const out: { role: Role; node: LevelNode | null }[] = [];
    for (const role of RAIL_ORDER) {
      const matches = nodes.filter((n) => n.role === role);
      if (matches.length === 0) { out.push({ role, node: null }); continue; }
      const located = matches.filter((n) => n.strike != null);
      if (located.length === 0) { out.push({ role, node: matches[0] }); continue; }
      located.sort((a, b) => (b.brightness ?? 0) - (a.brightness ?? 0));
      out.push({ role, node: located[0] });
    }
    return out;
  }, [payload]);

  const regime = payload?.regime ?? null;
  const isSticky = regime?.label === "sticky";

  // as-of / staleness read (OI updates once a day — say so honestly).
  const { asofStr, asofStale } = useMemo(() => {
    const asof = payload?.asof;
    if (!asof) return { asofStr: "", asofStale: false };
    try {
      const d = new Date(asof);
      const s = d.toLocaleString("en-US", {
        weekday: "short", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit", hour12: false,
        timeZone: "America/New_York",
      }) + " ET";
      const etDay = (dt: Date) => dt.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
      const ageDays = Math.round((Date.parse(etDay(new Date())) - Date.parse(etDay(d))) / 86_400_000);
      return { asofStr: s, asofStale: ageDays > 0 };
    } catch {
      return { asofStr: asof.slice(0, 16).replace("T", " "), asofStale: false };
    }
  }, [payload]);

  const roleColor = (n: LevelNode): string => {
    if (n.sticky == null) return palette.neutralVar;
    return n.sticky ? palette.stickyVar : palette.slipperyVar;
  };

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div style={OUTER} className="obs obs-ambient levels-board">

      {/* ── Controls bar ──────────────────────────────────────────────────── */}
      <div style={CONTROLS_BAR} className="levels-controls">
        <div style={TICKER_GROUP} className="levels-ticker-group">
          <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="var(--muted)" strokeWidth="2"
              style={{ position: "absolute", left: 8, pointerEvents: "none" }}>
              <circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" strokeLinecap="round" />
            </svg>
            <input
              style={TICKER_INPUT}
              list="levels-roots"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value.toUpperCase())}
              onBlur={commitTicker}
              onKeyDown={(e) => { if (e.key === "Enter") commitTicker(); }}
              placeholder="SPY"
              aria-label={t("lvTicker")}
              spellCheck={false}
              maxLength={12}
            />
            <datalist id="levels-roots">
              {AUTOCOMPLETE_ROOTS.map((r) => <option key={r} value={r} />)}
            </datalist>
          </div>
          <div style={{ display: "flex", gap: 4 }} className="levels-quick-roots">
            {QUICK_ROOTS.map((r) => (
              <button
                key={r}
                className={`chip${ticker === r ? " on" : ""}`}
                style={{ height: 24, fontSize: 11, fontWeight: 700, letterSpacing: "0.03em" }}
                onClick={() => { if (r !== ticker) trackSearch(r, "levels-board"); setInputVal(r); setTicker(r); }}
              >
                {r}
              </button>
            ))}
          </div>
          {payload?.spot != null && (
            <span style={SPOT_DISPLAY}>{fmtStrike(payload.spot)}</span>
          )}
        </div>

        <div style={CONTROLS_RIGHT}>
          {asofStr && (
            <span style={asofStale ? { ...ASOF_BADGE, color: "var(--warn)" } : ASOF_BADGE}>
              {t("lvAsOf")} {asofStr}{asofStale && <span style={{ marginLeft: 5, fontWeight: 600 }}>{t("lvPriorSession")}</span>}
            </span>
          )}
          <button
            className={`chip${colorblind ? " on" : ""}`}
            style={{ height: 24, fontSize: 11, fontWeight: 700, letterSpacing: "0.02em" }}
            onClick={() => setColorblind((v) => !v)}
            aria-pressed={colorblind}
            title={t("lvColorblindTitle")}
          >
            ◑ {colorblind ? t("lvColorblindOn") : t("lvColorblindOff")}
          </button>
          {loading && <span style={LOADING_BADGE}>{t("lvLoading")}</span>}
          {read === "absent" && <span style={ERROR_BADGE}>{t("lvNoLevels")}</span>}
          {refreshFailed && (
            <span style={REFRESH_FAILED_BADGE} data-testid="levels-refresh-failed" role="status">
              {tRead("lvRefreshFailed")}
              <button type="button" className="btn btn-ghost load-retry" style={RETRY_INLINE} onClick={retryLevels}>
                {tRead("lvRetry")}
              </button>
            </span>
          )}
        </div>
      </div>

      {/* ── Ribbon (plain-English regime read) ────────────────────────────── */}
      {regime && (
        <div style={{ ...RIBBON, borderLeft: `3px solid ${isSticky ? palette.stickyVar : palette.slipperyVar}` }}>
          <span style={{
            ...RIBBON_TAG,
            color: isSticky ? palette.stickyVar : palette.slipperyVar,
            borderColor: isSticky ? `rgba(${palette.stickyRGB},0.4)` : `rgba(${palette.slipperyRGB},0.4)`,
          }}>
            {isSticky ? t("lvSticky") : t("lvSlippery")}
          </span>
          <span style={RIBBON_TEXT}>{regime.ribbon}</span>
        </div>
      )}

      {/* ── Body: terrain column + node rail ──────────────────────────────── */}
      <div style={BODY_ROW} className="levels-body">

        {/* ── Terrain column (the gamma weather map) ─────────────────────── */}
        <div style={COLUMN_PANE} className="levels-column">
          {loading && !payload ? (
            <div style={COLUMN_LOADING}>{t("lvReadingMap")}</div>
          ) : loadFailed ? (
            <div style={COLUMN_ERROR} data-testid="levels-load-error" role="alert">
              <div style={COLUMN_ERROR_TITLE}>{tRead("lvLoadError").replace("{ticker}", ticker)}</div>
              <div>{tRead("lvLoadErrorWhy")}</div>
              <button type="button" className="btn btn-ghost load-retry" onClick={retryLevels}>
                {tRead("lvRetry")}
              </button>
            </div>
          ) : !payload || terrainNodes.length === 0 ? (
            <div style={COLUMN_LOADING}>
              {t("lvEmptyMap").replace("{ticker}", ticker)}
            </div>
          ) : (
            <div style={COLUMN_STAGE}>
              {/* void bands (thin, low-friction stretches) */}
              {band && voidNodes.map((v, i) => {
                const yTop = projY(v.strike_hi as number) * 100;
                const yBot = projY(v.strike_lo as number) * 100;
                return (
                  <button
                    key={`void-${i}`}
                    style={{
                      ...VOID_BAND,
                      top: `${yTop}%`,
                      height: `${Math.max(yBot - yTop, 1.5)}%`,
                    }}
                    onClick={() => setSelected({ key: `void-${i}`, label: `${roleLabel("void", lang)} ${ROLE_GLYPH.void}`, note: v.note })}
                    title={v.note}
                  >
                    <span style={VOID_LABEL}>{ROLE_GLYPH.void} {roleLabel("void", lang)}</span>
                  </button>
                );
              })}

              {/* strike terrain rungs — collision-free readable labels; a moved label keeps
                  an exact-price tick on the axis, joined to it by a leader */}
              {band && terrainLayout.map(({ node: n, index: i, rawY, displayY }) => {
                const b = n.brightness ?? 0;
                const rgb = n.sticky ? palette.stickyRGB : palette.slipperyRGB;
                const fillA = 0.10 + b * 0.42;
                const w = 30 + b * 60;
                const shifted = Math.abs(displayY - rawY) > 0.002;
                const leaderTop = Math.min(rawY, displayY) * 100;
                const leaderHeight = Math.abs(displayY - rawY) * 100;
                return (
                  <React.Fragment key={`rung-${i}`}>
                    {shifted && (
                      <>
                        <span
                          aria-hidden="true"
                          data-testid="levels-rung-leader"
                          style={{
                            ...RUNG_LEADER,
                            top: `${leaderTop}%`,
                            height: `${leaderHeight}%`,
                            background: `rgba(${rgb},0.42)`,
                          }}
                        />
                        <span
                          aria-hidden="true"
                          data-testid="levels-rung-anchor"
                          data-strike={fmtStrike(n.strike)}
                          style={{
                            ...RUNG_ANCHOR,
                            top: `${rawY * 100}%`,
                            background: `rgba(${rgb},${0.72 + b * 0.24})`,
                          }}
                        />
                      </>
                    )}
                    <button
                      data-testid="levels-rung"
                      data-strike={fmtStrike(n.strike)}
                      data-raw-y={rawY.toFixed(6)}
                      data-display-y={displayY.toFixed(6)}
                      style={{
                        ...RUNG,
                        top: `${displayY * 100}%`,
                        width: `${w}%`,
                        background: `linear-gradient(90deg, rgba(${rgb},${fillA}) 0%, rgba(${rgb},${fillA * 0.25}) 100%)`,
                        borderLeft: `2px solid rgba(${rgb},${0.5 + b * 0.5})`,
                      }}
                      onClick={() => setSelected({
                        key: `rung-${i}`,
                        label: `${roleLabel(n.role, lang)} ${ROLE_GLYPH[n.role]}`,
                        note: n.note,
                      })}
                      title={n.note}
                    >
                      <span style={{ ...RUNG_GLYPH, color: roleColor(n) }}>
                        {ROLE_GLYPH[n.role]}
                      </span>
                      <span style={RUNG_STRIKE}>{fmtStrike(n.strike)}</span>
                      <span style={{ ...RUNG_ROLE, color: roleColor(n) }}>
                        {roleLabel(n.role, lang)}
                      </span>
                    </button>
                  </React.Fragment>
                );
              })}

              {/* flip boundary line (calm above / wild below) */}
              {band && flipNode && (
                <button
                  style={{ ...FLIP_LINE, top: `${projY(flipNode.strike as number) * 100}%` }}
                  onClick={() => setSelected({ key: "flip", label: `${roleLabel("flip", lang)} ${ROLE_GLYPH.flip}`, note: flipNode.note })}
                  title={flipNode.note}
                >
                  <span style={FLIP_TAG}>{ROLE_GLYPH.flip} {roleLabel("flip", lang)} {fmtStrike(flipNode.strike)}</span>
                </button>
              )}

              {/* spot marker */}
              {band && payload.spot != null && (
                <div style={{ ...SPOT_LINE, top: `${projY(payload.spot) * 100}%` }}>
                  <span style={SPOT_TAG}>{t("lvSpot")} {fmtStrike(payload.spot)}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Right rail: named levels + legend + node detail ─────────────── */}
        <div style={RAIL_PANE} className="levels-rail">

          {/* node detail (tap a level) */}
          <div style={DETAIL_CARD}>
            {selected ? (
              <>
                <div style={DETAIL_HEAD}>{selected.label}</div>
                <div style={DETAIL_NOTE}>{selected.note}</div>
              </>
            ) : (
              <div style={DETAIL_EMPTY}>{t("lvTapLevel")}</div>
            )}
          </div>

          {/* named-levels rail */}
          <div style={RAIL_SCROLL} className="obs-scroll levels-rail-scroll">
            <div style={RAIL_TITLE}>{t("lvNamedLevels")}</div>
            {railEntries.map(({ role, node }) => {
              const present = node != null && node.strike != null;
              const c = node ? roleColor(node) : "var(--text-dim)";
              return (
                <button
                  key={role}
                  style={{ ...RAIL_ROW, opacity: present ? 1 : 0.55 }}
                  onClick={() => node && setSelected({ key: role, label: `${roleLabel(role, lang)} ${ROLE_GLYPH[role]}`, note: node.note })}
                >
                  <span style={{ ...RAIL_GLYPH, color: c }}>{ROLE_GLYPH[role]}</span>
                  <span style={RAIL_LABEL}>{roleLabel(role, lang)}</span>
                  <span style={{ ...RAIL_STRIKE, color: present ? "var(--text)" : "var(--text-dim)" }}>
                    {present ? fmtStrike(node!.strike) : absenceKnown ? notPresentLabel(lang) : fmtStrike(null)}
                  </span>
                </button>
              );
            })}

            {/* stacks (confluence strikes) */}
            {(payload?.stacks?.length ?? 0) > 0 && (
              <>
                <div style={{ ...RAIL_TITLE, marginTop: 12 }}>{t("lvConfluence")}</div>
                {payload!.stacks.map((s, i) => (
                  <button
                    key={`stack-${i}`}
                    style={RAIL_ROW}
                    onClick={() => setSelected({ key: `stack-${i}`, label: `${stackLabel(lang)} ${STACK_GLYPH}`, note: s.note })}
                  >
                    <span style={{ ...RAIL_GLYPH, color: "var(--signal)" }}>{STACK_GLYPH}</span>
                    <span style={RAIL_LABEL}>{stackLabel(lang)}</span>
                    <span style={{ ...RAIL_STRIKE, color: "var(--text)" }}>{fmtStrike(s.strike)}</span>
                  </button>
                ))}
              </>
            )}

            {/* legend + color law */}
            <div style={LEGEND}>
              <div style={{ ...RAIL_TITLE, marginTop: 0 }}>{t("lvReadingLegend")}</div>
              <div style={LEGEND_ROW}>
                <span style={{ ...LEGEND_SWATCH, background: `rgba(${palette.stickyRGB},0.6)` }} />
                <span style={LEGEND_TXT}><b style={{ color: palette.stickyVar }}>{t("lvSticky")}</b> {t("lvStickyHint")}</span>
              </div>
              <div style={LEGEND_ROW}>
                <span style={{ ...LEGEND_SWATCH, background: `rgba(${palette.slipperyRGB},0.6)` }} />
                <span style={LEGEND_TXT}><b style={{ color: palette.slipperyVar }}>{t("lvSlippery")}</b> {t("lvSlipperyHint")}</span>
              </div>
              <div style={LEGEND_ROW}>
                <span style={{ ...LEGEND_SWATCH, background: `linear-gradient(90deg, rgba(${palette.stickyRGB},0.15), rgba(${palette.stickyRGB},0.7))` }} />
                <span style={LEGEND_TXT}>{t("lvBrightnessHint")}</span>
              </div>
            </div>

            {/* honesty note + source lineage */}
            <div style={HONESTY}>
              {t("lvHonesty")}
              {payload?.source?.source_convention && (
                <span style={{ display: "block", marginTop: 4, color: "var(--text-dim)" }}>
                  {t("lvConvention")} {payload.source.source_convention}
                </span>
              )}
            </div>

            <a href="/learn" style={LEARN_LINK}>{t("lvLearnCta")}</a>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Styles (all colors via theme tokens; see app/globals.css) ────────────────

const OUTER: React.CSSProperties = {
  display: "flex", flexDirection: "column", flex: 1, height: "100%",
  overflow: "hidden", background: "var(--bg)",
};
const CONTROLS_BAR: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: 12, padding: "8px 14px",
  borderBottom: "1px solid var(--line)", background: "var(--panel)", flexShrink: 0, flexWrap: "wrap",
};
const TICKER_GROUP: React.CSSProperties = { display: "flex", alignItems: "center", gap: 10 };
const TICKER_INPUT: React.CSSProperties = {
  width: 118, height: 30, padding: "0 10px 0 26px", background: "var(--inset)",
  border: "1px solid var(--line)", borderRadius: "var(--r-md)", color: "var(--text)",
  fontSize: 13, fontWeight: 700, textAlign: "left", textTransform: "uppercase",
  letterSpacing: "0.06em", outline: "none", fontVariantNumeric: "tabular-nums",
};
const SPOT_DISPLAY: React.CSSProperties = {
  fontSize: 14, fontWeight: 700, color: "var(--text)", fontVariantNumeric: "tabular-nums",
};
const CONTROLS_RIGHT: React.CSSProperties = {
  marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
};
const ASOF_BADGE: React.CSSProperties = { fontSize: 10, color: "var(--muted)", fontVariantNumeric: "tabular-nums" };
const LOADING_BADGE: React.CSSProperties = { fontSize: 10, color: "var(--brand-2)" };
const ERROR_BADGE: React.CSSProperties = { fontSize: 10, color: "var(--muted)" };
const REFRESH_FAILED_BADGE: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: 6, fontSize: 10, color: "var(--warn)",
};
const RETRY_INLINE: React.CSSProperties = { padding: "2px 10px", fontSize: 11 };

const RIBBON: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: 10, padding: "9px 14px",
  background: "var(--panel-2)", borderBottom: "1px solid var(--line)", flexShrink: 0,
};
const RIBBON_TAG: React.CSSProperties = {
  fontSize: 10, fontWeight: 800, letterSpacing: "0.10em", padding: "2px 7px",
  borderRadius: "var(--r-pill)", border: "1px solid", flexShrink: 0,
};
const RIBBON_TEXT: React.CSSProperties = { fontSize: 12.5, color: "var(--text-2)", lineHeight: 1.4 };

const BODY_ROW: React.CSSProperties = {
  display: "flex", flex: 1, minHeight: 0, overflow: "hidden", flexWrap: "wrap", alignItems: "stretch",
};

const COLUMN_PANE: React.CSSProperties = {
  flex: "1 1 0px", minWidth: 360, minHeight: 0, alignSelf: "stretch",
  display: "flex", flexDirection: "column", overflow: "hidden",
  padding: "18px 24px 18px 14px", position: "relative",
};
const COLUMN_STAGE: React.CSSProperties = {
  position: "relative", flex: 1, minHeight: 360,
  marginLeft: 8, // room for the moved labels' exact-price ticks (RUNG_ANCHOR)
  borderLeft: "1px solid var(--line-3)",
};
const COLUMN_LOADING: React.CSSProperties = {
  flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
  fontSize: 12.5, color: "var(--muted)", textAlign: "center", padding: "0 32px", lineHeight: 1.6, maxWidth: 460, margin: "0 auto",
};
const COLUMN_ERROR: React.CSSProperties = { ...COLUMN_LOADING, flexDirection: "column", gap: 8 };
const COLUMN_ERROR_TITLE: React.CSSProperties = { fontSize: 13, fontWeight: 600, color: "var(--text)" };

const RUNG: React.CSSProperties = {
  position: "absolute", left: 0, height: 22, transform: "translateY(-50%)", zIndex: 3,
  display: "flex", alignItems: "center", gap: 8, paddingLeft: 8,
  borderRadius: "0 var(--r) var(--r) 0", cursor: "pointer", textAlign: "left",
  fontFamily: "var(--font-num)",
};
const RUNG_LEADER: React.CSSProperties = {
  position: "absolute", left: 0, width: 1, pointerEvents: "none", zIndex: 1,
};
// A moved label's exact-price tick. It sits on the axis line and in the stage's left margin
// (COLUMN_STAGE marginLeft), where no rung is ever drawn, so it cannot cross any label's text.
// A moved price usually lies inside a neighbour's label — that crowding is why it moved.
const RUNG_ANCHOR_TICK = 8;
const RUNG_ANCHOR: React.CSSProperties = {
  position: "absolute", left: -RUNG_ANCHOR_TICK, width: RUNG_ANCHOR_TICK, height: 2,
  transform: "translateY(-50%)", borderRadius: "1px 0 0 1px", pointerEvents: "none", zIndex: 2,
};
const RUNG_GLYPH: React.CSSProperties = { fontSize: 13, fontWeight: 700, width: 14, textAlign: "center" };
const RUNG_STRIKE: React.CSSProperties = {
  fontSize: 12, fontWeight: 700, color: "var(--text)", fontVariantNumeric: "tabular-nums",
};
const RUNG_ROLE: React.CSSProperties = {
  fontSize: 11, fontWeight: 700, letterSpacing: "0.02em", fontFamily: "var(--font-ui)",
};

const VOID_BAND: React.CSSProperties = {
  position: "absolute", left: 0, right: 8,
  background: "repeating-linear-gradient(45deg, rgba(113,122,142,0.05) 0 6px, rgba(113,122,142,0.12) 6px 12px)",
  border: "1px dashed var(--line-3)", borderRadius: "var(--r)",
  display: "flex", alignItems: "center", justifyContent: "flex-end",
  paddingRight: 8, cursor: "pointer",
};
const VOID_LABEL: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, color: "var(--muted)", letterSpacing: "0.04em",
};

const FLIP_LINE: React.CSSProperties = {
  position: "absolute", left: 0, right: 8, height: 0,
  borderTop: "1.5px dashed var(--warn)", cursor: "pointer", background: "transparent",
  display: "flex", alignItems: "center",
};
const FLIP_TAG: React.CSSProperties = {
  position: "absolute", right: 0, transform: "translateY(-50%)",
  fontSize: 10, fontWeight: 700, color: "var(--warn)", background: "var(--panel)",
  padding: "1px 6px", borderRadius: "var(--r-pill)", border: "1px solid var(--line-3)",
  fontVariantNumeric: "tabular-nums",
};

const SPOT_LINE: React.CSSProperties = {
  position: "absolute", left: 0, right: 8, height: 0,
  borderTop: "1px solid var(--text-2)", display: "flex", alignItems: "center",
};
const SPOT_TAG: React.CSSProperties = {
  position: "absolute", right: 0, transform: "translateY(-50%)",
  fontSize: 10, fontWeight: 700, color: "var(--bg)", background: "var(--text-2)",
  padding: "1px 6px", borderRadius: "var(--r-pill)", fontVariantNumeric: "tabular-nums",
};

const RAIL_PANE: React.CSSProperties = {
  flex: "0 1 320px", minWidth: 280, alignSelf: "stretch", display: "flex", flexDirection: "column",
  borderLeft: "1px solid var(--line)", background: "var(--panel)", overflow: "hidden",
};
const DETAIL_CARD: React.CSSProperties = {
  padding: "12px 14px", borderBottom: "1px solid var(--line)", background: "var(--panel-2)", minHeight: 78, flexShrink: 0,
};
const DETAIL_HEAD: React.CSSProperties = {
  fontSize: 13, fontWeight: 800, color: "var(--text)", marginBottom: 5, letterSpacing: "0.01em",
};
const DETAIL_NOTE: React.CSSProperties = { fontSize: 12, color: "var(--text-2)", lineHeight: 1.5 };
const DETAIL_EMPTY: React.CSSProperties = { fontSize: 12, color: "var(--muted)", lineHeight: 1.5 };

const RAIL_SCROLL: React.CSSProperties = { flex: 1, overflowY: "auto", padding: "10px 12px 16px" };
const RAIL_TITLE: React.CSSProperties = {
  fontSize: 10, fontWeight: 700, letterSpacing: "0.10em", textTransform: "uppercase",
  color: "var(--muted)", marginBottom: 6,
};
const RAIL_ROW: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "6px 6px",
  background: "transparent", border: "none", borderRadius: "var(--r)", cursor: "pointer", textAlign: "left",
};
const RAIL_GLYPH: React.CSSProperties = { fontSize: 13, width: 16, textAlign: "center", fontWeight: 700 };
const RAIL_LABEL: React.CSSProperties = { fontSize: 12.5, fontWeight: 600, color: "var(--text)", flex: 1 };
const RAIL_STRIKE: React.CSSProperties = { fontSize: 12, fontWeight: 700, fontVariantNumeric: "tabular-nums" };

const LEGEND: React.CSSProperties = {
  marginTop: 14, padding: "10px 10px", background: "var(--inset)",
  borderRadius: "var(--r-md)", border: "1px solid var(--line)",
};
const LEGEND_ROW: React.CSSProperties = { display: "flex", alignItems: "center", gap: 8, marginBottom: 6 };
const LEGEND_SWATCH: React.CSSProperties = { width: 22, height: 10, borderRadius: 2, flexShrink: 0 };
const LEGEND_TXT: React.CSSProperties = { fontSize: 11.5, color: "var(--text-2)", lineHeight: 1.4 };

const HONESTY: React.CSSProperties = {
  marginTop: 12, fontSize: 10.5, lineHeight: 1.55, color: "var(--muted)",
  paddingTop: 10, borderTop: "1px solid var(--line)",
};
const LEARN_LINK: React.CSSProperties = {
  display: "inline-block", marginTop: 10, fontSize: 11.5, fontWeight: 600,
  color: "var(--link)", textDecoration: "none",
};
