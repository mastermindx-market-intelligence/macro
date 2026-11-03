"""Guard a client-visible past projection from masquerading as a future cycle turn.

The test executes the actual inline renderer from the Jinja template using
only static synthetic cycle data, no credentials, provider or browser network.
"""
from pathlib import Path
import subprocess
import textwrap

SOURCE = Path(__file__).parents[1] / "templates/basket_detail.html.j2"


def _run_js(js: str) -> None:
    result = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=12)
    assert result.returncode == 0, result.stderr + result.stdout


def test_theme_detail_cycle_projection_is_time_honest_en_and_zh() -> None:
    text = SOURCE.read_text()
    start = text.index("const CYC_PHASE_ZH=")
    end = text.index("const VH_COLOR=", start)
    renderer = text[start:end]
    assert "function projectionWindowState(" in renderer
    # No real site/endpoint call. Fix date and render both locales.
    cases = r"""
const OldDate = Date;
global.Date = class extends OldDate {
  constructor(...args) { super(...(args.length ? args : ["2026-11-03T00:00:00.000Z"])); }
};
let language = "en";
function L(en, zh) { return language === "zh" ? zh : en; }
function cssv() { return "#456789"; }
function esc(x) { return String(x); }
const make = (pr) => ({
  price: Array.from({length:12}, (_,i)=>({x:2025.15+i*.16,v:90+i})),
  xDomain: [2025, 2027.6], today: 2026.84, turns: [],
  proj: pr, phases: {}, now: {phase:"Expansion",pos:55}
});
const expired = {nextTurn:"peak",central:"2026-01",low:"2025-11",high:"2026-04",central_x:2026.04};
const active = {nextTurn:"peak",central:"2026-10",low:"2026-09",high:"2026-12",central_x:2026.76};
const future = {nextTurn:"peak",central:"2027-01",low:"2026-12",high:"2027-03",central_x:2027.04};
const invalid = {nextTurn:"peak",central:"2026-13",low:"2026-09",high:"2027-02",central_x:2026.95};
function check(ok, reason) { if (!ok) throw Error(reason); }
function forLanguage(lang) {
  language = lang;
  const e = cycleSectionHtml(make(expired),"retail");
  const a = cycleSectionHtml(make(active),"retail");
  const f = cycleSectionHtml(make(future),"retail");
  const u = cycleSectionHtml(make(invalid),"retail");
  const expiredLabel = lang==="en" ? "Historical projection window elapsed" : "历史预测窗口已结束";
  const activeLabel = lang==="en" ? "Projection window in progress" : "预测窗口进行中";
  const futureLabel = lang==="en" ? "Projected next turn" : "推演下一拐点";
  const noProjection = lang==="en" ? "No valid current projection" : "暂无有效当前预测";
  check(e.includes('preserveAspectRatio="xMidYMid meet"'), "chart aspect ratio regression");
  check(e.includes('viewBox="0 0 1080 240"'), "chart geometry regression");
  check(e.includes(expiredLabel), "expired projection not disclosed");
  check(!e.includes(futureLabel) && !e.includes("next peak"), "expired projection falsely called next");
  check(!e.includes("▲</text>"), "expired projection has a future-turn marker");
  check(a.includes(activeLabel) && !a.includes(futureLabel), "active window falsely called next");
  check(!a.includes("▲</text>"), "in-progress projection has future-turn marker");
  check(f.includes(futureLabel) && f.includes(lang==="en" ? "next peak" : "下一顶部"), "genuinely future projection lost");
  check(f.includes("▲</text>"), "genuinely future turn lost marker");
  check(u.includes(noProjection) && !u.includes(futureLabel), "invalid date accepted as projection");
  check(!u.includes("▲</text>"), "invalid projection has a future marker");
}
forLanguage("en"); forLanguage("zh");
check(projectionWindowState(expired,"2026-11")==="expired","expired state");
check(projectionWindowState(active,"2026-11")==="in_progress","in-progress state");
check(projectionWindowState(future,"2026-11")==="future","future state");
check(projectionWindowState(invalid,"2026-11")==="unavailable","invalid date state");
check(projectionWindowState({nextTurn:"peak",central:"2027-01",low:"2026-12",high:"2027-03"},"wrong")==="unavailable","invalid as-of state");
check(projectionWindowState({nextTurn:"peak",central:"2027-01",low:"2027-03",high:"2026-12"},"2026-11")==="unavailable","reversed dates state");
"""
    _run_js(renderer + "\n" + cases)
