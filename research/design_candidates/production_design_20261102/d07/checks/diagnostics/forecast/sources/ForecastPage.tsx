"use client";
/**
 * ForecastPage — the TradingView "Forecast" dashboard (BUILD-SPEC §3.4 FE2c,
 * spec/forecast.md). Two sibling tabs:
 *   - "Price target": price-history line + forward fan to mean/high/low targets,
 *     a low—mean—high target band with a current-price marker, summary sentence,
 *     analyst-rating ArcGauge + distribution bars (sell zone in --down tints),
 *     consensus forward-growth chips, then EPS & Revenue reported/estimate
 *     Dumbbell (FORECAST hatch + "E"-suffixed estimate columns) + surprise MiniTable.
 *   - "Actuals and estimates": estimate-fan LineSeries + statement pills +
 *     Actual/Avg/High/Low/#estimates MiniTable from fund.estimates.
 *
 * JUDGE-FIXED constraints honored here:
 *   - The forecast fan spans current-FY→next-FY ONLY (fund.estimates carries
 *     exactly 2 FY periods; §1.1). We never invent a third estimate period.
 *   - Price-history line comes from the `bars` prop (getBars) — never a raw fetch.
 *   - CN (fund.estimates == null / fund.analyst == null) renders the analyst
 *     empty-state, surfacing fund.guidance as a company-guidance chip when present.
 *
 * Standalone page: default export, receives narrow props; MegaPane wires them.
 * Everything null-guarded (fund=null, bars=[]).
 */
import { memo, useMemo, useState } from "react";
import type { Fund } from "../../lib/fund";
import type { Bar } from "../../lib/fund";
import {
  fmtNum,
  fmtPct,
  fmtCur,
  fmtDate,
  pick,
  signColor,
  statementCurrencyLabel,
} from "../../lib/finFormat";
import {
  Dumbbell,
  LineSeries,
  MiniTable,
  type DumbbellPoint,
  type Series,
  type MiniRow,
} from "./FinCharts";
import { ArcGauge, type ArcState } from "../ui/ArcGauge";
import { arcStateLabel } from "../../lib/plainLabels";
import type { FundEarnings, AnalystDist } from "../../lib/fund";
import { incomeViewTopLineLabel, incomeView, isIndustrialIncomeView } from "../../lib/finStatementMath";

interface ForecastPageProps {
  sym: string;
  fund: Fund | null;
  bars?: Bar[];
  zh?: boolean;
  /**
   * Loading gate: when true the async fund fetch is still in flight, so the pane
   * renders a skeleton instead of the false "No analyst coverage" empty state.
   * Distinguishes "not yet loaded" (skeleton) from "loaded, no coverage" (empty).
   * Wired by the shell (MegaPane/TerminalShell — SHELL lane) which knows fetch
   * status; defaults false so untouched callers keep working.
   */
  loading?: boolean;
}

/**
 * analystReading — rating distribution → gauge reading in [-1, 1] (weighted mean
 * of buckets). SINGLE SOURCE OF TRUTH: the rail AnalystGauge (StockAnalysis.tsx)
 * imports this so both surfaces compute the identical reading.
 */
export function analystReading(dist: AnalystDist): number | null {
  const w = dist.strongBuy * 1 + dist.buy * 0.5 + dist.hold * 0 + dist.sell * -0.5 + dist.strongSell * -1;
  const n = dist.strongBuy + dist.buy + dist.hold + dist.sell + dist.strongSell;
  return n > 0 ? w / n : null;
}

/**
 * readingToArc — the SINGLE mapping from a [-1, +1] rating/consensus reading to
 * an ArcGauge {value 0–100, state}. Every gauge across ForecastPage,
 * TechnicalsPage and the StockAnalysis rail routes through this so they never
 * disagree on where "buy" ends and "hold"/"sell" begin. Thresholds match
 * zoneWord: ≥0.15 leans buy (bull), ≤−0.15 leans sell (bear), the ±0.15 band is
 * hold (neutral → grey, so a flat consensus reads as no signal, not red).
 * value maps −1→0, 0→50, +1→100 (50 = neutral centre).
 */
export function readingToArc(reading: number | null): { value: number; state: ArcState } {
  if (reading == null || !Number.isFinite(reading)) return { value: 50, state: "neutral" };
  const r = Math.max(-1, Math.min(1, reading));
  const state: ArcState = r >= 0.15 ? "bull" : r <= -0.15 ? "bear" : "neutral";
  return { value: Math.round(((r + 1) / 2) * 100), state };
}

/** Zone word for a reading — the fallback when no engine rating_label is given. */
function zoneWord(reading: number | null, zh: boolean): string {
  if (reading == null) return "";
  if (reading >= 0.5) return pick(zh, "Strong buy", "强烈买入");
  if (reading >= 0.15) return pick(zh, "Buy", "买入");
  if (reading > -0.15) return pick(zh, "Hold", "持有");
  if (reading > -0.5) return pick(zh, "Sell", "卖出");
  return pick(zh, "Strong sell", "强烈卖出");
}

/**
 * ratingVerdict — the ONE verdict word shared by the rail AnalystGauge and the
 * ForecastPage gauge. Prefers the engine's `rating_label` (translated when zh);
 * falls back to the reading's zone word so it is NEVER empty (the old rail
 * gauge showed a word while the pane showed none — this reconciles them).
 */
export function ratingVerdict(label: string | null, reading: number | null, zh: boolean): string {
  if (label) {
    if (!zh) return label;
    const map: Record<string, string> = {
      "Strong buy": "强烈买入",
      Buy: "买入",
      Hold: "持有",
      Neutral: "中性",
      Sell: "卖出",
      "Strong sell": "强烈卖出",
    };
    return map[label] ?? label;
  }
  return zoneWord(reading, zh);
}

/* signed % of a target vs the current price, formatted with explicit sign + color. */
function upsidePct(target: number | null, cur: number | null): number | null {
  if (target == null || cur == null || cur === 0) return null;
  return (target - cur) / cur;
}

/* currency-aware money axis: big → K/M/B, small → 2dp. */
function moneyFmt(ccy: string | null | undefined) {
  return (v: number) => fmtCur(v, ccy);
}

export default memo(ForecastPage);   // pure prop-driven page — skip re-render on the 6s live-quote poll
function ForecastPage({ sym, fund, bars = [], zh = false, loading = false }: ForecastPageProps) {
  const [tab, setTab] = useState<"target" | "actuals">("target");
  const [epsFreq, setEpsFreq] = useState<"A" | "Q">("A");
  const [revFreq, setRevFreq] = useState<"A" | "Q">("A");
  const [stmt, setStmt] = useState<"income" | "balance" | "cashflow">("income");

  // Live/last price from the price-history line (last finite close).
  // Hoisted ABOVE the loading early-return: hooks must run on every render —
  // with the memo below the return, the hook count changed when `loading`
  // flipped and React threw (MegaPane renders this page without a key, so it
  // reconciles in place rather than remounting).
  const lastPrice = useMemo(() => {
    for (let i = bars.length - 1; i >= 0; i--) if (isFinite(bars[i]?.c)) return bars[i].c;
    return null;
  }, [bars]);

  // Loading skeleton — while the fund fetch is in flight, show shimmer blocks
  // instead of the false "No analyst coverage" empty state.
  if (loading && !fund) {
    return (
      <div className="fin-fc">
        <div className="fin-fc-tabs fin-toggle fin-skel-tabs" aria-hidden />
        <div className="fin-grid2 fin-fc-top">
          <div className="fin-card"><div className="fin-skel fin-skel-chart" /></div>
          <div className="fin-card"><div className="fin-skel fin-skel-gauge" /><div className="fin-skel fin-skel-rows" /></div>
        </div>
        <div className="fin-sec"><div className="fin-skel fin-skel-chart" /></div>
        <span className="fin-skel-sr" role="status">{pick(zh, "Loading analyst data…", "正在加载分析师数据…")}</span>
      </div>
    );
  }

  const ccy = fund?.quote_currency ?? "USD";
  const stmtCcy = fund?.stmt_currency ?? null;
  const est = fund?.estimates ?? null;
  const analyst = fund?.analyst ?? null;

  return (
    <div className="fin-fc">
      {/* sibling tab bar */}
      <div className="fin-toggle fin-fc-tabs">
        <button className={tab === "target" ? "on" : ""} onClick={() => setTab("target")}>
          {pick(zh, "Price target", "目标价")}
        </button>
        <button className={tab === "actuals" ? "on" : ""} onClick={() => setTab("actuals")}>
          {pick(zh, "Actuals and estimates", "实际与预期")}
        </button>
      </div>

      {tab === "target" ? (
        <PriceTargetTab
          sym={sym}
          fund={fund}
          bars={bars}
          lastPrice={lastPrice}
          ccy={ccy}
          stmtCcy={stmtCcy}
          analyst={analyst}
          est={est}
          epsFreq={epsFreq}
          setEpsFreq={setEpsFreq}
          revFreq={revFreq}
          setRevFreq={setRevFreq}
          zh={zh}
        />
      ) : (
        <ActualsTab fund={fund} est={est} stmt={stmt} setStmt={setStmt} ccy={stmtCcy} zh={zh} />
      )}

      <Disclaimer zh={zh} />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
 * TAB A — Price target
 * ───────────────────────────────────────────────────────────────────────── */

function PriceTargetTab({
  fund,
  bars,
  lastPrice,
  ccy,
  stmtCcy,
  analyst,
  est,
  epsFreq,
  setEpsFreq,
  revFreq,
  setRevFreq,
  zh,
}: {
  sym: string;
  fund: Fund | null;
  bars: Bar[];
  lastPrice: number | null;
  ccy: string;
  stmtCcy: string | null;
  analyst: Fund["analyst"];
  est: Fund["estimates"];
  epsFreq: "A" | "Q";
  setEpsFreq: (f: "A" | "Q") => void;
  revFreq: "A" | "Q";
  setRevFreq: (f: "A" | "Q") => void;
  zh: boolean;
}) {
  const target = analyst?.target ?? null;
  const mean = target?.mean ?? null;
  const high = target?.high ?? null;
  const low = target?.low ?? null;
  const nTargets = target?.n ?? null;

  const avgUp = upsidePct(mean, lastPrice);

  return (
    <>
      <div className="fin-grid2 fin-fc-top">
        {/* left: price-target header + fan */}
        <div className="fin-card">
          <div className="fin-eyebrow">{pick(zh, "PRICE TARGETS", "目标价")}</div>
          <div
            className="fin-sec-h fin-rail fin-rule"
            style={{ "--rail": "var(--brand)" } as React.CSSProperties}
          >
            {pick(zh, "12-month consensus", "12个月一致目标")}
          </div>
          {mean != null ? (
            <>
              <div className="fin-fc-price">
                {fmtNum(mean)} <span className="fin-fc-ccy">{ccy}</span>
              </div>
              {avgUp != null && (
                <div className="fin-fc-chg">
                  {lastPrice != null && (
                    <span className="d" style={{ color: signColor(mean - lastPrice) }}>
                      {fmtNum(mean - lastPrice, { decimals: 2 })}
                    </span>
                  )}
                  <span
                    className="fin-tag num"
                    style={{
                      "--c": avgUp > 0 ? "var(--up)" : avgUp < 0 ? "var(--down)" : "var(--muted)",
                    } as React.CSSProperties}
                  >
                    {fmtPct(avgUp, { sign: true })}
                  </span>
                </div>
              )}
              {nTargets != null && high != null && low != null && (
                <div className="fin-fc-summary">
                  {pick(
                    zh,
                    `The ${nTargets} analysts offering 1-year price forecasts have a max estimate of ${fmtNum(high)} and a min estimate of ${fmtNum(low)}.`,
                    `提供1年价格预测的 ${nTargets} 位分析师，最高目标价 ${fmtNum(high)}，最低目标价 ${fmtNum(low)}。`,
                  )}
                </div>
              )}
              <TargetBand low={low} mean={mean} high={high} cur={lastPrice} zh={zh} />
              <PriceFan bars={bars} cur={lastPrice} mean={mean} high={high} low={low} ccy={ccy} zh={zh} />
            </>
          ) : (
            <AnalystEmpty fund={fund} zh={zh} />
          )}
        </div>

        {/* right: analyst rating gauge + distribution */}
        <div className="fin-card">
          <div className="fin-eyebrow">{pick(zh, "SELL-SIDE CONSENSUS", "卖方一致预期")}</div>
          <div
            className="fin-sec-h fin-rail fin-rule"
            style={{ "--rail": "var(--brand)" } as React.CSSProperties}
          >
            {pick(zh, "Analyst rating", "分析师评级")}
          </div>
          {analyst ? (
            <AnalystRating analyst={analyst} est={est} zh={zh} />
          ) : (
            <AnalystEmpty fund={fund} zh={zh} />
          )}
        </div>
      </div>

      {/* EPS section */}
      <EstimateBarSection
        title="EPS"
        titleZh="每股收益"
        kind="eps"
        fund={fund}
        est={est}
        freq={epsFreq}
        setFreq={setEpsFreq}
        ccy={stmtCcy}
        zh={zh}
      />

      {/* Revenue section — labeled with stmt_currency as revenue comes from statements */}
      <EstimateBarSection
        title="Revenue"
        titleZh="营收"
        kind="rev"
        fund={fund}
        est={est}
        freq={revFreq}
        setFreq={setRevFreq}
        ccy={stmtCcy}
        zh={zh}
      />

      <EstimatesAsOf fund={fund} zh={zh} />
    </>
  );
}

/**
 * EstimatesAsOf — provenance row for the consensus block: which feed produced
 * the estimates and how fresh the snapshot is. Reads only fields already on the
 * fund contract (`src.estimates`, `asof`); renders nothing when neither exists.
 */
function EstimatesAsOf({ fund, zh }: { fund: Fund | null; zh: boolean }) {
  const asof = fund?.asof ?? null;
  const src = fund?.src?.estimates ?? null;
  if (!asof && !src) return null;
  const srcPart = src ? ` · ${src}` : "";
  return (
    <div className="fin-asof">
      {asof
        ? pick(zh, `Consensus estimates${srcPart} · as of ${fmtDate(asof)}`, `一致预期数据${srcPart} · 截至 ${fmtDate(asof)}`)
        : pick(zh, `Consensus estimates${srcPart}`, `一致预期数据${srcPart}`)}
    </div>
  );
}

/**
 * TargetBand — a low—mean—high horizontal band with a current-price marker,
 * so the reader sees where spot sits inside the analyst target range at a
 * glance. Uses only existing fields (target.low/mean/high + last price). The
 * band is non-directional (a range); the current marker is brand.
 */
function TargetBand({
  low,
  mean,
  high,
  cur,
  zh,
}: {
  low: number | null;
  mean: number | null;
  high: number | null;
  cur: number | null;
  zh: boolean;
}) {
  if (low == null || high == null || high <= low) return null;
  const span = high - low;
  const pos = (v: number | null) => (v == null ? null : Math.max(0, Math.min(100, ((v - low) / span) * 100)));
  const meanPos = pos(mean);
  const curPos = pos(cur);
  // The "Now" tag rides a reserved lane ABOVE the track, centred over its dot.
  // Near either end a centred tag would overhang the card, so it flips to
  // edge-aligned instead of being allowed to spill.
  const curEdge = curPos == null ? "" : curPos <= 14 ? " at-lo" : curPos >= 86 ? " at-hi" : "";
  return (
    <div className="fin-fc-band" role="group" aria-label={pick(zh, "Analyst target range", "分析师目标区间")}>
      <div className="fin-fc-band-track">
        {/* mean tick */}
        {meanPos != null && <span className="fin-fc-band-mean" style={{ left: `${meanPos}%` }} />}
        {/* current-price marker */}
        {curPos != null && (
          <span className={"fin-fc-band-cur" + curEdge} style={{ left: `${curPos}%` }}>
            <span className="dot" />
            <span className="tag">
              <span className="k">{pick(zh, "Now", "现价")}</span>
              <span className="v num">{fmtNum(cur)}</span>
            </span>
          </span>
        )}
      </div>
      <div className="fin-fc-band-ends">
        <span className="lo"><span className="k">{pick(zh, "Low", "最低")}</span> {fmtNum(low)}</span>
        {mean != null && <span className="mid"><span className="k">{pick(zh, "Mean", "均值")}</span> {fmtNum(mean)}</span>}
        <span className="hi"><span className="k">{pick(zh, "High", "最高")}</span> {fmtNum(high)}</span>
      </div>
    </div>
  );
}

/* Price history line (from bars) + a 2-period forward fan to mean/high/low. */
function PriceFan({
  bars,
  cur,
  mean,
  high,
  low,
  ccy,
  zh,
}: {
  bars: Bar[];
  cur: number | null;
  mean: number | null;
  high: number | null;
  low: number | null;
  ccy: string;
  zh: boolean;
}) {
  // Trailing ~2y of dailies, sampled to ≤120 points for a clean SVG path.
  const hist = useMemo(() => {
    const tail = bars.slice(-504);
    if (tail.length === 0) return { labels: [] as string[], values: [] as (number | null)[] };
    const step = Math.max(1, Math.ceil(tail.length / 120));
    const pts = tail.filter((_, i) => i % step === 0 || i === tail.length - 1);
    const rawLabels = pts.map((b) => String(b.time).slice(0, 7));
    // Show only ~6 evenly-spaced labels; blank the rest so the axis stays
    // aligned with the data without cramming duplicate month strings.
    const n = rawLabels.length;
    const showCount = Math.min(6, n);
    const showSet = new Set<number>();
    for (let k = 0; k < showCount; k++) {
      showSet.add(Math.round((k / Math.max(showCount - 1, 1)) * (n - 1)));
    }
    const sparseLabels = rawLabels.map((lbl, i) => (showSet.has(i) ? lbl : ""));
    return {
      labels: sparseLabels,
      values: pts.map((b) => b.c),
    };
  }, [bars]);

  if (hist.values.length === 0 || mean == null) {
    return null;
  }

  // Fan: the historical line, plus three forward series that begin at `cur`
  // (the anchor) and end at high / mean / low over TWO synthetic forward slots
  // (current-FY → next-FY, per the judge-fixed 2-period rule).
  const n = hist.values.length;
  const anchor = cur ?? hist.values[n - 1] ?? mean;
  const pad: (number | null)[] = new Array(n - 1).fill(null);
  // Keep "1Y FORECAST" out of the XAxis tick array — it collides with the last
  // date tick when both occupy the same slot. The brackets panel on the right
  // already communicates the 1-year target; a chart-top annotation band is
  // added below the chart instead.
  const labels = [...hist.labels, "", ""];

  const histSeries: Series = {
    name: pick(zh, "Price", "价格"),
    values: [...hist.values, null, null],
    color: "var(--brand)",
  };
  const fan: Series[] = [];
  if (high != null) fan.push({ name: pick(zh, "Max", "最高"), values: [...pad, anchor, null, high], color: "var(--up)" });
  fan.push({ name: pick(zh, "Average", "平均"), values: [...pad, anchor, null, mean], color: "var(--warn)" });
  if (low != null) fan.push({ name: pick(zh, "Min", "最低"), values: [...pad, anchor, null, low], color: "var(--down)" });

  return (
    <div className="fin-fc-fanwrap">
      <div style={{ flex: 1, minWidth: 0, position: "relative" }}>
        <LineSeries
          labels={labels}
          series={[histSeries, ...fan]}
          fmtY={(v) => fmtNum(v)}
          vw={420}
          vh={220}
          zh={zh}
          height={230}
          noLegend
        />
        {/* Forecast band annotation — rendered as an HTML overlay over the rightmost ~16% of the chart */}
        <div className="fin-fc-forecast-ann" aria-hidden>
          {pick(zh, "1Y FORECAST", "1年预测")}
        </div>
      </div>
      {/* end brackets: Max / Avg / Current / Min */}
      <div className="fin-fc-brackets">
        {high != null && <Bracket label={pick(zh, "Max", "最高")} pct={upsidePct(high, cur)} price={high} tone="up" zh={zh} />}
        <Bracket label={pick(zh, "Avg", "平均")} pct={upsidePct(mean, cur)} price={mean} tone="avg" zh={zh} />
        {cur != null && <Bracket label={pick(zh, "Current", "当前")} pct={null} price={cur} tone="cur" zh={zh} />}
        {low != null && <Bracket label={pick(zh, "Min", "最低")} pct={upsidePct(low, cur)} price={low} tone="down" zh={zh} />}
      </div>
    </div>
  );
}

function Bracket({
  label,
  pct,
  price,
  tone,
  zh,
}: {
  label: string;
  pct: number | null;
  price: number | null;
  tone: "up" | "avg" | "cur" | "down";
  zh: boolean;
}) {
  return (
    <div className={"fin-fc-bracket t-" + tone}>
      <span className="lbl">
        {label}
        {pct != null && <span className="pct">{fmtPct(pct, { sign: true })}</span>}
      </span>
      <span className="val">{fmtNum(price)}</span>
    </div>
  );
}

function AnalystRating({ analyst, est, zh }: { analyst: NonNullable<Fund["analyst"]>; est: Fund["estimates"]; zh: boolean }) {
  const dist = analyst.dist;
  const reading = analystReading(dist);
  const total = dist.strongBuy + dist.buy + dist.hold + dist.sell + dist.strongSell;
  // Scale bars to the TOTAL analyst count (share-of-analysts), not the largest
  // bucket — so a thin 3-analyst consensus doesn't render as a "full" bar.
  const denom = Math.max(total, 1);
  const rows: { label: string; labelZh: string; count: number; tone: string }[] = [
    { label: "Strong buy", labelZh: "强烈买入", count: dist.strongBuy, tone: "up" },
    { label: "Buy", labelZh: "买入", count: dist.buy, tone: "up2" },
    { label: "Hold", labelZh: "持有", count: dist.hold, tone: "neu" },
    // Sell zone is RED (--down), not neutral grey — understating bearish
    // consensus was a color-semantics violation.
    { label: "Sell", labelZh: "卖出", count: dist.sell, tone: "down2" },
    { label: "Strong sell", labelZh: "强烈卖出", count: dist.strongSell, tone: "down" },
  ];
  return (
    <>
      <div className="fin-sec-cap">
        {pick(
          zh,
          `Based on ${total} analysts giving stock ratings in the past 3 months.`,
          `基于过去3个月 ${total} 位分析师的评级。`,
        )}
      </div>
      {(() => {
        const arc = readingToArc(reading);
        const arcState = arc.state;
        return (
          <div className="fin-arc-wrap">
            <ArcGauge
              value={arc.value}
              state={arcState}
              size={168}
              label={pick(zh, "Analyst rating", "分析师评级")}
              sublabel={ratingVerdict(analyst.rating_label, reading, zh)}
              stateTitle={arcStateLabel(arcState, zh ? "zh" : "en") as string}
            />
          </div>
        );
      })()}
      <GrowthStrip est={est} zh={zh} />
      <div className="fin-fc-dist">
        {rows.map((r) => (
          <div className="fin-fc-dist-row" key={r.label}>
            <span className="lbl">{pick(zh, r.label, r.labelZh)}</span>
            <span className="track">
              <span className={"bar t-" + r.tone} style={{ width: `${(r.count / denom) * 100}%` }} />
            </span>
            <span className="cnt">{r.count}</span>
          </div>
        ))}
      </div>
    </>
  );
}

/**
 * GrowthStrip — consensus forward-growth chips (EPS / Revenue YoY) from
 * estimates.growth. High-signal, previously unused. `growth` values are stored
 * as fractions (e.g. 0.12 = +12%). Renders nothing when both are absent.
 */
function GrowthStrip({ est, zh }: { est: Fund["estimates"]; zh: boolean }) {
  const g = est?.growth;
  if (!g || (g.eps_yoy == null && g.rev_yoy == null)) return null;
  // Tint formula: --c drives background, ring and text together. Forward growth
  // IS directional, so --c rides --up/--down (never brand) and flips correctly
  // under html[data-updown="east"].
  const chip = (label: string, v: number | null) =>
    v == null ? null : (
      <span
        className="fin-tag num"
        key={label}
        style={{ "--c": v >= 0 ? "var(--up)" : "var(--down)" } as React.CSSProperties}
      >
        <span className="k">{label}</span>
        {fmtPct(v, { sign: true })}
      </span>
    );
  return (
    <div className="fin-fc-growth" role="group" aria-label={pick(zh, "Consensus forward growth", "一致预期未来增长")}>
      <span className="fin-fc-growth-lbl">{pick(zh, "Consensus FY", "一致预期（本财年）")}</span>
      {chip(pick(zh, "EPS", "每股收益"), g.eps_yoy)}
      {chip(pick(zh, "Revenue", "营收"), g.rev_yoy)}
    </div>
  );
}

/* CN / no-coverage empty state; surfaces company guidance chip when present. */
function AnalystEmpty({ fund, zh }: { fund: Fund | null; zh: boolean }) {
  const g = fund?.guidance ?? null;
  return (
    <div className="fin-empty fin-fc-analyst-empty">
      <div className="fin-empty-title">{pick(zh, "No analyst coverage", "暂无分析师覆盖")}</div>
      <div className="fin-empty-why">
        {g
          ? pick(
              zh,
              "No sell-side estimates are published for this listing. The company's own guidance is shown instead.",
              "该标的没有卖方分析师预期数据，以下改为展示公司自身的业绩指引。",
            )
          : pick(
              zh,
              "No sell-side analyst estimates or price targets are published for this listing.",
              "该标的没有卖方分析师预期或目标价数据。",
            )}
      </div>
      {g && (
        <div className="fin-fc-guidance">
          <span className="fin-tag" style={{ "--c": "var(--brand-2)" } as React.CSSProperties}>{g.type}</span>
          <span className="txt">
            {pick(zh, "Company guidance", "公司业绩预告")}
            {g.chg_min != null && g.chg_max != null && (
              <> · {fmtPct(g.chg_min / 100, { sign: true })}…{fmtPct(g.chg_max / 100, { sign: true })}</>
            )}
            {g.period && <> · {g.period}</>}
          </span>
        </div>
      )}
    </div>
  );
}

/* ── EPS / Revenue clustered-bar section (Reported vs Estimate + FORECAST) ── */

function EstimateBarSection({
  title,
  titleZh,
  kind,
  fund,
  est,
  freq,
  setFreq,
  ccy,
  zh,
}: {
  title: string;
  titleZh: string;
  kind: "eps" | "rev";
  fund: Fund | null;
  est: Fund["estimates"];
  freq: "A" | "Q";
  setFreq: (f: "A" | "Q") => void;
  ccy: string | null;
  zh: boolean;
}) {
  // Actuals from fund.earnings (fy annual / q quarterly); forecast tail from estimates.
  const built = useMemo(() => buildEstimateRows(kind, fund, est, freq), [kind, fund, est, freq]);
  const reportedColor = kind === "eps" ? "var(--brand)" : "var(--warn)";
  const fmtV = kind === "eps" ? (v: number) => fmtNum(v, { decimals: 2 }) : moneyFmt(ccy);

  // Estimate-only (forward) columns get the FORECAST hatch + beat/miss dots via
  // Dumbbell — so the reader sees exactly where reported actuals end and
  // consensus begins (the old grey Bars made them indistinguishable).
  const dumbPoints: DumbbellPoint[] = built.labels.map((label, i) => ({
    // estimate-only (no reported actual) columns get an "E" suffix
    label: built.reported[i] == null && built.estimate[i] != null ? `${label} E` : label,
    actual: built.reported[i],
    estimate: built.estimate[i],
    surp_pct: built.surprise[i],
  }));
  const forecastFrom = built.reported.findIndex((v) => v == null);

  const rows: MiniRow[] = [
    { label: pick(zh, "Reported", "实际"), values: built.reported, fmt: fmtV },
    { label: pick(zh, "Estimate", "预期"), values: built.estimate, fmt: fmtV },
    {
      label: pick(zh, "Surprise", "超预期"),
      values: built.surprise,
      fmt: (v) => fmtPct(v, { alreadyPct: true, sign: true }),
    },
  ];

  return (
    <div className="fin-sec">
      <div className="fin-fc-sec-head fin-rule">
        <div
          className="fin-sec-h fin-rail"
          style={{ "--rail": "var(--brand)" } as React.CSSProperties}
        >
          {pick(zh, title, titleZh)}
        </div>
        <div className="fin-toggle">
          <button className={freq === "A" ? "on" : ""} onClick={() => setFreq("A")}>{pick(zh, "Annual", "年度")}</button>
          <button className={freq === "Q" ? "on" : ""} onClick={() => setFreq("Q")}>{pick(zh, "Quarterly", "季度")}</button>
        </div>
      </div>
      {built.labels.length === 0 ? (
        <div className="fin-empty fin-empty-lg">
          <div className="fin-empty-title">{pick(zh, "No estimate data", "暂无预期数据")}</div>
          <div className="fin-empty-why">
            {pick(
              zh,
              `No reported ${kind === "eps" ? "EPS" : "revenue"} history or consensus estimates are filed for this security on the ${freq === "A" ? "annual" : "quarterly"} axis.`,
              `该证券在${freq === "A" ? "年度" : "季度"}口径下既无已报告${titleZh}历史，也无一致预期数据。`,
            )}
          </div>
        </div>
      ) : (
        <>
          <Dumbbell
            points={dumbPoints}
            fmtY={kind === "eps" ? (v) => fmtNum(v, { decimals: 2 }) : (v) => fmtNum(v)}
            forecastFrom={forecastFrom >= 0 ? forecastFrom : undefined}
            actualColor={reportedColor}
            vw={520}
            vh={190}
            zh={zh}
            height={240}
            noWindow
          />
          <MiniTable
            periods={built.labels}
            rows={rows}
            fmt={fmtV}
            pageSize={10}
            zh={zh}
            cornerLabel={statementCurrencyLabel(ccy, zh)}
          />
        </>
      )}
    </div>
  );
}

/**
 * buildEstimateRows — align reported actuals to forward estimates on a shared
 * period axis. Actuals come from fund.earnings; the forward tail (estimate-only
 * columns) comes from fund.estimates and spans EXACTLY the 2 estimate periods
 * the contract carries (current-FY→next-FY, or the 2 forward quarters).
 */
function buildEstimateRows(
  kind: "eps" | "rev",
  fund: Fund | null,
  est: Fund["estimates"],
  freq: "A" | "Q",
) {
  const labels: string[] = [];
  const reported: (number | null)[] = [];
  const estimate: (number | null)[] = [];

  const pickA = (r: { eps_a?: number | null; rev_a?: number | null }) => (kind === "eps" ? r.eps_a ?? null : r.rev_a ?? null);
  const pickE = (r: { eps_e?: number | null; rev_e?: number | null }) => (kind === "eps" ? r.eps_e ?? null : r.rev_e ?? null);

  if (freq === "A") {
    for (const fy of fund?.earnings?.fy ?? []) {
      labels.push(fy.period);
      reported.push(pickA(fy));
      estimate.push(pickE(fy));
    }
  } else {
    // Cap quarterly actuals to the last 12 periods (still generous) so the x-axis
    // isn't crushed; the forward estimate tail below is appended after the cap.
    for (const q of (fund?.earnings?.q ?? []).slice(-12)) {
      labels.push(q.period);
      reported.push(pickA(q));
      estimate.push(pickE(q));
    }
  }

  // Forward tail: the estimate periods that aren't already present as actuals.
  // Revenue has FY estimates only (no quarterly estimate series in the contract).
  const fwd = kind === "eps"
    ? (freq === "A" ? est?.eps_fy : est?.eps_q)
    : (freq === "A" ? est?.rev_fy : null);
  if (fwd) {
    fwd.periods.forEach((rawP, i) => {
      // Map placeholder labels ('0y', '+1y', '0q', '+1q') to real fiscal labels.
      const p = mapRawPeriodLabel(rawP, fund?.earnings);
      if (labels.includes(p)) {
        // patch estimate onto an existing (actual) column
        const idx = labels.indexOf(p);
        if (estimate[idx] == null) estimate[idx] = fwd.avg[i] ?? null;
      } else {
        labels.push(p);
        reported.push(null);
        estimate.push(fwd.avg[i] ?? null);
      }
    });
  }

  const surprise = reported.map((r, i) => {
    const e = estimate[i];
    if (r == null || e == null || e === 0) return null;
    return ((r - e) / Math.abs(e)) * 100;
  });

  return { labels, reported, estimate, surprise };
}

/* ─────────────────────────────────────────────────────────────────────────
 * TAB B — Actuals and estimates
 * ───────────────────────────────────────────────────────────────────────── */

function ActualsTab({
  fund,
  est,
  stmt,
  setStmt,
  ccy,
  zh,
}: {
  fund: Fund | null;
  est: Fund["estimates"];
  stmt: "income" | "balance" | "cashflow";
  setStmt: (s: "income" | "balance" | "cashflow") => void;
  ccy: string | null;
  zh: boolean;
}) {
  const built = useMemo(() => buildActualsTable(fund, est, stmt, zh), [fund, est, stmt, zh]);

  // Top chart plots the EPS estimate fan (Actual / Average / High / Low).
  const chart = useMemo(() => {
    if (!est) return null;
    const fy = est.eps_fy;
    // actual years from earnings.fy + the 2 estimate years
    const actLabels: string[] = [];
    const actual: (number | null)[] = [];
    for (const r of fund?.earnings?.fy ?? []) {
      actLabels.push(r.period);
      actual.push(r.eps_a ?? null);
    }
    const labels = [...actLabels];
    // Map raw placeholder labels ('0y', '+1y') to display labels before use.
    const mappedFyPeriods = fy.periods.map((p) => mapRawPeriodLabel(p, fund?.earnings));
    mappedFyPeriods.forEach((p) => {
      if (!labels.includes(p)) labels.push(p + " E");
    });
    const actualPadded = new Array(labels.length).fill(null) as (number | null)[];
    actual.forEach((v, i) => (actualPadded[i] = v));
    const avg = new Array(labels.length).fill(null) as (number | null)[];
    const high = new Array(labels.length).fill(null) as (number | null)[];
    const low = new Array(labels.length).fill(null) as (number | null)[];
    mappedFyPeriods.forEach((p, i) => {
      const li = labels.indexOf(p + " E") >= 0 ? labels.indexOf(p + " E") : labels.indexOf(p);
      if (li >= 0) {
        avg[li] = fy.avg[i] ?? null;
        high[li] = fy.high[i] ?? null;
        low[li] = fy.low[i] ?? null;
      }
    });
    // bridge Average to the last actual so the cone connects
    const lastActIdx = actual.map((v, i) => (v != null ? i : -1)).filter((i) => i >= 0).pop();
    if (lastActIdx != null && lastActIdx >= 0 && avg[lastActIdx] == null) avg[lastActIdx] = actual[lastActIdx];
    return {
      labels,
      series: [
        { name: pick(zh, "Actual", "实际"), values: actualPadded, color: "var(--brand)" },
        { name: pick(zh, "Average", "平均"), values: avg, color: "var(--warn)" },
        { name: pick(zh, "High", "最高"), values: high, color: "var(--up)" },
        { name: pick(zh, "Low", "最低"), values: low, color: "var(--down)" },
      ] as Series[],
    };
  }, [fund, est, zh]);

  if (!est) {
    return (
      <div className="fin-sec">
        <AnalystEmpty fund={fund} zh={zh} />
      </div>
    );
  }

  return (
    <>
      {chart && (
        <div className="fin-sec">
          {/* Heading so the naked line chart is legible as the EPS estimate trend */}
          <div
            className="fin-sec-h fin-rail fin-rule"
            style={{ "--rail": "var(--brand)" } as React.CSSProperties}
          >
            {pick(zh, "EPS estimate trend", "每股收益预期走势")}
          </div>
          <LineSeries
            labels={chart.labels}
            series={chart.series}
            fmtY={(v) => fmtNum(v, { decimals: 2 })}
            dotted={[pick(zh, "Average", "平均")]}
            vw={640}
            vh={220}
            zh={zh}
            height={210}
          />
        </div>
      )}
      {/* Statement toggle bound to the TABLE it controls (not the EPS chart above) */}
      <div className="fin-sec">
        <div className="fin-fc-sec-head fin-rule">
          <div
            className="fin-sec-h fin-rail"
            style={{ "--rail": "var(--brand)" } as React.CSSProperties}
          >
            {pick(zh, "Estimates table", "预期数据表")}
          </div>
          <div className="fin-toggle">
            <button className={stmt === "income" ? "on" : ""} onClick={() => setStmt("income")}>{pick(zh, "Income statement", "利润表")}</button>
            <button className={stmt === "balance" ? "on" : ""} onClick={() => setStmt("balance")}>{pick(zh, "Balance sheet", "资产负债表")}</button>
            <button className={stmt === "cashflow" ? "on" : ""} onClick={() => setStmt("cashflow")}>{pick(zh, "Cash flow", "现金流量表")}</button>
          </div>
        </div>
        <MiniTable
          periods={built.periods}
          rows={built.rows}
          fmt={(v) => fmtNum(v)}
          pageSize={8}
          zh={zh}
          cornerLabel={statementCurrencyLabel(ccy, zh)}
        />
        <EstimatesAsOf fund={fund} zh={zh} />
      </div>
    </>
  );
}

/**
 * mapRawPeriodLabel — defensively maps emitter placeholder labels
 * ('0y', '+1y', '0q', '+1q') to human-readable fiscal labels derived
 * from the most recent earnings.fy period or the current year.
 */
function mapRawPeriodLabel(p: string, earn: FundEarnings | null | undefined): string {
  const RAW_FY = new Set(["0y", "+1y"]);
  const RAW_Q = new Set(["0q", "+1q"]);
  if (!RAW_FY.has(p) && !RAW_Q.has(p)) return p;

  // Derive the current fiscal year from the last earned FY period or fall back to calendar year.
  const lastFy = earn?.fy ? earn.fy[earn.fy.length - 1]?.period ?? null : null;
  const baseYear = lastFy ? parseInt(lastFy, 10) : new Date().getFullYear();
  const currentFY = isNaN(baseYear) ? new Date().getFullYear() : baseYear + 1;

  if (RAW_FY.has(p)) {
    return p === "0y" ? String(currentFY) : String(currentFY + 1);
  }
  // Quarter labels
  const currentQ = Math.ceil((new Date().getMonth() + 1) / 3);
  const currentYear = new Date().getFullYear();
  if (p === "0q") return `Q${currentQ} '${String(currentYear).slice(2)}`;
  const nextQ = currentQ === 4 ? 1 : currentQ + 1;
  const nextYear = currentQ === 4 ? currentYear + 1 : currentYear;
  return `Q${nextQ} '${String(nextYear).slice(2)}`;
}

/**
 * buildActualsTable — the estimates table: an expandable EPS group
 * (Actual/Average/High/Low/# estimates) plus collapsed statement line-item rows.
 * Estimate detail only exists for EPS + revenue (the only estimate series); other
 * rows show actuals and `—` for the ` E` columns.
 * All row labels are bilingual via pick(zh, en, cn).
 */
function buildActualsTable(fund: Fund | null, est: Fund["estimates"], stmt: "income" | "balance" | "cashflow", zh: boolean) {
  const fyEarn = fund?.earnings?.fy ?? [];
  const actualLabels = fyEarn.map((r) => r.period);
  const rawEstPeriods = est?.eps_fy.periods ?? [];
  // Map any raw yfinance placeholder labels ('0y', '+1y') to real fiscal labels.
  const estPeriods = rawEstPeriods.map((p) => mapRawPeriodLabel(p, fund?.earnings));
  const periods: string[] = [...actualLabels];
  estPeriods.forEach((p) => {
    if (!periods.includes(p)) periods.push(p + " E");
  });

  const alignEst = (series: { periods: string[]; avg: (number | null)[]; high: (number | null)[]; low: (number | null)[]; n: (number | null)[] } | undefined, key: "avg" | "high" | "low" | "n") => {
    const out = new Array(periods.length).fill(null) as (number | null)[];
    if (!series) return out;
    // Map raw periods to display labels before looking up
    series.periods.forEach((rawP, i) => {
      const p = mapRawPeriodLabel(rawP, fund?.earnings);
      const li = periods.indexOf(p + " E") >= 0 ? periods.indexOf(p + " E") : periods.indexOf(p);
      if (li >= 0) out[li] = (series[key] as (number | null)[])[i] ?? null;
    });
    return out;
  };

  const actualEps = new Array(periods.length).fill(null) as (number | null)[];
  fyEarn.forEach((r, i) => (actualEps[i] = r.eps_a ?? null));

  const rows: MiniRow[] = [];

  // Expandable EPS group — ALL labels bilingual via pick(zh, en, cn).
  rows.push({
    label: pick(zh, "Earnings per share", "每股收益"),
    values: actualEps,
    bold: true,
    fmt: (v) => fmtNum(v, { decimals: 2 }),
    children: [
      { label: pick(zh, "Actual", "实际"), values: actualEps, depth: 1, fmt: (v) => fmtNum(v, { decimals: 2 }) },
      { label: pick(zh, "Average", "平均"), values: alignEst(est?.eps_fy, "avg"), depth: 1, fmt: (v) => fmtNum(v, { decimals: 2 }) },
      { label: pick(zh, "High", "最高"), values: alignEst(est?.eps_fy, "high"), depth: 1, fmt: (v) => fmtNum(v, { decimals: 2 }) },
      { label: pick(zh, "Low", "最低"), values: alignEst(est?.eps_fy, "low"), depth: 1, fmt: (v) => fmtNum(v, { decimals: 2 }) },
      { label: pick(zh, "# estimates", "预测机构数"), values: alignEst(est?.eps_fy, "n"), depth: 1, fmt: (v) => fmtNum(v, { decimals: 0 }) },
    ],
  });

  // Statement line items (actuals only; ` E` columns show —).
  const ann = fund?.statements?.annual;
  const annualView = incomeView(fund?.ticker, ann, "annual");
  const alignActual = (series: (number | null)[] | undefined) => {
    const out = new Array(periods.length).fill(null) as (number | null)[];
    if (!series || !ann) return out;
    ann.periods.forEach((p, i) => {
      const li = periods.indexOf(p);
      if (li >= 0) out[li] = series[i] ?? null;
    });
    return out;
  };

  const lineItems: [string, string, (number | null)[] | undefined][] =
    stmt === "income"
      ? [
          [
            incomeViewTopLineLabel(annualView, false),
            incomeViewTopLineLabel(annualView, true),
            annualView.income.revenue,
          ],
          ...(isIndustrialIncomeView(annualView)
            ? [
                ["Cost of goods sold", "营业成本", annualView.income.cogs],
                ["Gross profit", "毛利润", annualView.income.gross_profit],
              ] as [string, string, (number | null)[]][]
            : []),
          ["Operating income", "营业利润", annualView.income.op_income],
          ["Pretax income", "税前利润", annualView.income.pretax_income],
          ...(isIndustrialIncomeView(annualView)
            ? [["EBITDA", "息税折旧摊销前利润", annualView.income.ebitda]] as [string, string, (number | null)[]][]
            : []),
          ["Net income", "净利润", annualView.income.net_income],
        ]
      : stmt === "balance"
        ? [
            ["Total assets", "总资产", ann?.balance.assets],
            ["Total liabilities", "总负债", ann?.balance.liabilities],
            ["Total equity", "股东权益", ann?.balance.equity],
            ["Total debt", "总债务", ann?.balance.debt],
            ["Cash & equivalents", "现金及等价物", ann?.balance.cash],
            ["Net debt", "净债务", ann?.balance.net_debt],
          ]
        : [
            ["Operating cash flow", "经营现金流", ann?.cashflow.cfo],
            ["Investing cash flow", "投资现金流", ann?.cashflow.cfi],
            ["Financing cash flow", "融资现金流", ann?.cashflow.cff],
            ["Capital expenditure", "资本支出", ann?.cashflow.capex],
            ["Free cash flow", "自由现金流", ann?.cashflow.fcf],
          ];

  for (const [en, cn, series] of lineItems) {
    rows.push({ label: pick(zh, en, cn), values: alignActual(series) });
  }

  return { periods, rows };
}

/* ─────────────────────────────────────────────────────────────────────────
 * shared footer
 * ───────────────────────────────────────────────────────────────────────── */

export function Disclaimer({ zh }: { zh: boolean }) {
  return (
    <div className="fin-sec fin-disclaimer">
      <div
        className="fin-sec-h fin-rail"
        style={{ "--rail": "var(--warn)" } as React.CSSProperties}
      >
        {pick(zh, "Disclaimer", "免责声明")}
      </div>
      <p>
        {pick(
          zh,
          "This is not investment advice and doesn't take into account your personal circumstances. It isn't a recommendation to buy, sell, or hold any asset. Always do your own research.",
          "本内容不构成投资建议，也未考虑你的个人情况。它不是对任何资产的买入、卖出或持有的推荐。请始终自行研究。",
        )}
      </p>
    </div>
  );
}
