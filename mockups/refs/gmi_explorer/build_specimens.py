#!/usr/bin/env python3
"""GMI Explorer design-reference specimen builder.

REFERENCE ONLY, not product code. Reads inputs/fixture.json (a frozen, cited
data snapshot) and inputs/nav.html (the shipped _site_nav markup) and writes
six static specimen pages next to this file, then renders the evidence matrix
(dark/light x EN/ZH x 1440/390) into png/.

    python3 build_specimens.py              # html + png
    python3 build_specimens.py --html-only  # html only
    python3 build_specimens.py --only s2_theme_map

The pages link ../../../templates/theme.css + navigation-refresh.css and the
reference sheet gmi_explorer.css. Theme/lang/lens come from the URL hash
(#theme=light&lang=zh&lens=chain) so one file renders every matrix cell.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import pathlib
from collections import Counter, OrderedDict

HERE = pathlib.Path(__file__).resolve().parent
F = json.loads((HERE / "inputs/fixture.json").read_text())
NAV = (HERE / "inputs/nav.html").read_text()
E = html.escape
M = F["micros"]
CATS = F["cats"]

# ------------------------------------------------------------------ helpers
def t(en: str, zh: str) -> str:
    """Dual-language text; theme.css hides the inactive language."""
    return f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>'


def tip(en: str, zh: str, rc_en: str | None = None, rc_zh: str | None = None) -> str:
    """Tier-2 lens trigger. Text lives in data-tip-*, never title= (doctrine §13)."""
    rc = ""
    if rc_en:
        rc = f' data-tip-rc-en="{E(rc_en)}" data-tip-rc-zh="{E(rc_zh or rc_en)}"'
    return (f'<button class="lens-q gmi-tip" type="button" data-tip-en="{E(en)}" data-tip-zh="{E(zh)}"{rc}>'
            f'<span aria-hidden="true">?</span><span class="gmi-vh">{t("More detail", "更多说明")}</span></button>')


ICONS = {
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    "chev": '<path d="M9 6l6 6-6 6"/>',
    "arrow": '<path d="M4.5 12h15M13.5 6l6 6-6 6"/>',
    "refresh": '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v4h-4"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.2M12 7.8h.01"/>',
    "alert": '<path d="M12 4.2l8.6 15.3H3.4z"/><path d="M12 10v4.2M12 17h.01"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "ext": '<path d="M14 4.5h5.5V10M19.5 4.5L11 13"/><path d="M17.5 14v5.5h-13v-13H10"/>',
    "eyeoff": '<path d="M3.5 3.5l17 17"/><path d="M10.6 6.1c.5-.1.9-.1 1.4-.1 5 0 8.4 4.4 9.4 6-.5.8-1.5 2.2-3 3.5M6.5 7.5C4.7 8.8 3.4 10.6 2.6 12c1 1.6 4.4 6 9.4 6 1.6 0 3-.4 4.2-1"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
    "pause": '<circle cx="12" cy="12" r="8.5"/><path d="M10 9v6M14 9v6"/>',
    "file": '<path d="M7 3.5h7l4 4v13H7z"/><path d="M14 3.5v4h4"/>',
    "question": '<circle cx="12" cy="12" r="8.5"/><path d="M9.8 9.6a2.3 2.3 0 1 1 3.1 2.1c-.6.3-.9.8-.9 1.5M12 16.6h.01"/>',
    "list": '<path d="M9 6.5h11M9 12h11M9 17.5h11"/><path d="M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01"/>',
}


def ic(name: str, size: int = 24) -> str:
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


ARROW_LONG = ('<svg viewBox="0 0 28 12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
              'stroke-linejoin="round" aria-hidden="true"><path d="M1 6h25M21 1.5L26 6l-5 4.5"/></svg>')

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def de(iso: str) -> str:
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {MON[int(m) - 1]} {y}"


def dz(iso: str) -> str:
    y, m, d = iso[:10].split("-")
    return f"{y}年{int(m)}月{int(d)}日"


def d(iso: str) -> str:
    return t(de(iso), dz(iso))


def fy_zh(label: str) -> str:
    return label.replace("FY", "") + "财年" if label.startswith("FY") else label


def mark(kind: str, xl: bool = False) -> str:
    return f'<span class="gmi-sm gmi-sm--{kind}{" gmi-sm--xl" if xl else ""}" aria-hidden="true"></span>'


def micro_kind(mid: str) -> str:
    m = M[mid]
    if m.get("disposition") == "PROPOSED_ONLY":
        return "held"
    if m.get("admitted"):
        return "adm"
    return "acc" if m["tier"] == "acceptance" else "disp"


KIND_ORDER = {"held": 0, "adm": 1, "acc": 2, "disp": 3}
KIND_TAG = {"held": ("Held", "待审核"), "adm": ("Admitted", "已纳入"), "acc": ("Core", "核心"), "disp": ("Extended", "扩展")}


def ordered(mids):
    return sorted(mids, key=lambda m: (KIND_ORDER[micro_kind(m)], M[m]["en"].lower()))


def n(x: int) -> str:
    return f"{x:,}"


# theme id -> (en, zh)
THEME_NAMES = {}
for c in CATS:
    for th in c["themes"]:
        THEME_NAMES[th["id"]] = (th["en"], th["zh"])
CAT_NAMES = {c["id"]: (c["en"], c["zh"]) for c in CATS}

TOTAL = len(M)
CORE = sum(1 for v in M.values() if v["tier"] == "acceptance")
EXT = TOTAL - CORE
HELD = sum(1 for k in M if micro_kind(k) == "held")
ADMITTED = 0  # fixture: coverage numerator 0, disposition ledger 67 EMPTY + 1 PROPOSED_ONLY
assert TOTAL == 371 and CORE == 68 and EXT == 303 and HELD == 1, (TOTAL, CORE, EXT, HELD)
assert sum(len(c["micros"]) for c in CATS) == TOTAL

# ------------------------------------------------------------------ copy (Tier 2 tips)
TIP_CORE = ("The original 68 micro-themes. Coverage and accuracy are measured on this set only.",
            "最初的68个细分主题。覆盖率与准确性仅在此集合上衡量。")
TIP_EXT = ("303 micro-themes added on 21 Oct 2026 to help you find your way around. They are shown but not counted in coverage.",
           "2026年10月21日新增的303个细分主题，用于帮助浏览。予以显示，但不计入覆盖率。")
TIP_ADM = ("A company joins a micro-theme only after a curator admits it from its own filings. None has been admitted yet.",
           "公司须经审核员依据其自身申报文件批准后才纳入细分主题。目前尚无公司获准纳入。")
TIP_HELD = ("A proposed link waiting for a curator. Held links are not members and are left out of every count.",
            "等待审核员处理的拟议关联。待审核关联不是成员，不计入任何统计。",
            "Micron → HBM & advanced packaging · first seen 11 Oct 2026",
            "美光科技 → HBM 与先进封装 · 首次收录2026年10月11日")

# ------------------------------------------------------------------ page shell
HASH_JS = """(function(){var h=new URLSearchParams(location.hash.slice(1)),r=document.documentElement;
var th=h.get('theme'),lg=h.get('lang'),ln=h.get('lens');
if(th)r.setAttribute('data-theme',th);
if(lg){r.setAttribute('data-lang',lg);r.setAttribute('lang',lg==='zh'?'zh-Hans':'en');}
if(ln)r.setAttribute('data-gmi-lens',ln);})();"""

TABS_JS = """(function(){var r=document.documentElement,bs=[].slice.call(document.querySelectorAll('[data-gmi-set-lens]'));
function sync(){bs.forEach(function(b){b.setAttribute('aria-selected',String(r.getAttribute('data-gmi-lens')===b.getAttribute('data-gmi-set-lens')));});}
bs.forEach(function(b){b.addEventListener('click',function(){var v=b.getAttribute('data-gmi-set-lens');r.setAttribute('data-gmi-lens',v);sync();
var h=new URLSearchParams(location.hash.slice(1));h.set('lens',v);history.replaceState(null,'','#'+h.toString());});});sync();})();"""


JUMP_JS = """(function(){var nav=document.querySelector('.gmi-jump');if(!nav)return;
var tr=nav.querySelector('.gmi-jump-track'),links=[].slice.call(nav.querySelectorAll('a'));
links.forEach(function(a){a.addEventListener('click',function(e){var g=document.getElementById(a.getAttribute('href').slice(1));
if(!g)return;e.preventDefault();g.setAttribute('open','');g.scrollIntoView({block:'start'});});});
if(!('IntersectionObserver' in window))return;var cur=null;
var io=new IntersectionObserver(function(es){es.forEach(function(en){if(!en.isIntersecting)return;var id=en.target.id;
links.forEach(function(a){var on=a.getAttribute('href')==='#'+id;if(on)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current');
if(on&&cur!==a){cur=a;if(tr.scrollWidth>tr.clientWidth)tr.scrollLeft=a.offsetLeft-16;}});});},{rootMargin:'-60px 0px -70% 0px'});
[].forEach.call(document.querySelectorAll('[data-gmi-index] > details'),function(g){io.observe(g);});})();"""
INDEX_JS = """(function(){var gs=[].slice.call(document.querySelectorAll('[data-gmi-index] > details'));
var all=new URLSearchParams(location.hash.slice(1)).get('open')==='all';
if(!all&&window.matchMedia('(max-width:640px)').matches){gs.forEach(function(g,i){if(i>0)g.removeAttribute('open');});}})();"""


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en" data-theme="dark" data-lang="en" data-gmi-lens="coverage">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<!-- REFERENCE SPECIMEN (mockups/refs/gmi_explorer). Not product code. -->
<link rel="stylesheet" href="../../../templates/theme.css">
<link rel="stylesheet" href="../../../templates/navigation-refresh.css">
<link rel="stylesheet" href="gmi_explorer.css">
<script>{HASH_JS}</script>
</head>
<body class="gmi-page">
{NAV}
<main class="gmi-wrap" id="main">
{body}
</main>
<script>{TABS_JS}</script>
</body>
</html>
"""


def head(crumb: list[tuple[str, str]], h1: str, sub: str, side: str, extra: str = "") -> str:
    cr = '<i aria-hidden="true">›</i>'.join(t(a, b) for a, b in crumb)
    return f"""<header class="gmi-head">
  <div class="gmi-head-main">
    <nav class="gmi-crumb" aria-label="Breadcrumb">{cr}</nav>
    {extra}<h1 class="gmi-h1">{h1}</h1>
    <p class="gmi-sub">{sub}</p>
  </div>
  <div class="gmi-head-side">{side}</div>
</header>"""


def asof(iso: str) -> str:
    return f'<span class="gmi-asof">{t("Read as of " + de(iso), "数据截至" + dz(iso))}</span>'


def sec(h_en: str, h_zh: str, level: int = 2, right: str = "", tipx: str = "") -> str:
    r = f'<span class="mx-asof">{right}</span>' if right else ""
    return f'<div class="mx-sec"><h{level}>{t(h_en, h_zh)}</h{level}>{tipx}{r}</div>'


def search_box(en: str, zh: str) -> str:
    return (f'<div class="gmi-search" role="search">{ic("search", 18)}'
            f'<span class="gmi-search-ph">{t(en, zh)}</span><kbd aria-hidden="true">/</kbd></div>')


def tally() -> str:
    """Ledger line, not a KPI row: one lead population, then its composition, then the core set's status.
    Each figure is one integer for one population (doctrine section 9)."""
    def fig(kind, num, en, zh, tp):
        mk = mark(kind) if kind else ""
        tq = tip(*tp) if tp else ""
        return (f'<div class="gmi-tally-fig"><span class="gmi-tally-num">{n(num)}</span>'
                f'<span class="gmi-tally-lab">{mk}<span class="gmi-tally-txt">{t(en, zh)}</span>{tq}</span></div>')
    lead = (f'<div class="gmi-tally-lead"><span class="gmi-tally-num gmi-tally-num--lead">{n(TOTAL)}</span>'
            f'<span class="gmi-tally-lab">{t("micro-themes mapped", "个细分主题已绘制")}</span></div>')
    comp = (f'<div class="gmi-tally-group"><span class="gmi-tally-cap">{t("Made up of", "构成")}</span>'
            f'<div class="gmi-tally-figs">{fig("acc", CORE, "Core set", "核心集", TIP_CORE)}'
            f'{fig("disp", EXT, "Extended · not counted", "扩展 · 不计入", TIP_EXT)}</div></div>')
    stat = (f'<div class="gmi-tally-group"><span class="gmi-tally-cap">{t("Core set so far", "核心集进展")}</span>'
            f'<div class="gmi-tally-figs">{fig("adm", ADMITTED, "Admitted", "已纳入", TIP_ADM)}'
            f'{fig("held", HELD, "Held for review", "待审核", TIP_HELD)}</div></div>')
    return f'<div class="gmi-tally">{lead}{comp}{stat}</div>'


def key() -> str:
    return ('<div class="gmi-key">'
            f'<span>{mark("acc")}{t("Core set", "核心集")}</span>'
            f'<span>{mark("disp")}{t("Extended · not counted", "扩展 · 不计入")}</span>'
            f'<span>{mark("adm")}{t("Admitted", "已纳入")}</span>'
            f'<span>{mark("held")}{t("Held for review", "待审核")}</span></div>')


def vh_counts(mids) -> str:
    c = Counter(micro_kind(m) for m in mids)
    en = f"{len(mids)} micro-themes: {c['acc']} core, {c['disp']} extended, {c['held']} held, {c['adm']} admitted"
    zh = f"{len(mids)}个细分主题：核心{c['acc']}个，扩展{c['disp']}个，待审核{c['held']}个，已纳入{c['adm']}个"
    return f'<span class="gmi-vh">{t(en, zh)}</span>'


# ------------------------------------------------------------------ S2 theme map
def census_coverage() -> str:
    bands = []
    cells_total = 0
    for c in CATS:
        mids = ordered(c["micros"])
        core = sum(1 for m in mids if M[m]["tier"] == "acceptance")
        focus = " gmi-cband--focus" if c["id"] == "theme:semiconductors_hardware" else ""
        if not mids:
            bands.append(f'<div class="gmi-cband gmi-cband--empty"><div class="gmi-cband-label">'
                         f'<span class="gmi-cband-name">{t(E(c["en"]), E(c["zh"]))}</span>'
                         f'<span class="gmi-cband-meta">0</span></div>'
                         f'<div class="gmi-cells">{t("No micro-themes mapped yet", "尚未绘制细分主题")}</div></div>')
            continue
        cells_total += len(mids)
        meta = t(f"{len(mids)} · {core} core", f"{len(mids)} · 核心 {core}")
        kinds = [micro_kind(m) for m in mids]
        core_cells = "".join(mark(k) for k in kinds if k != "disp")
        ext_cells = "".join(mark(k) for k in kinds if k == "disp")
        sep = '<i class="gmi-cells-sep" aria-hidden="true"></i>' if core_cells and ext_cells else ""
        cells = core_cells + sep + ext_cells
        bands.append(f'<div class="gmi-cband{focus}"><div class="gmi-cband-label">'
                     f'<span class="gmi-cband-name">{t(E(c["en"]), E(c["zh"]))}</span>'
                     f'<span class="gmi-cband-meta">{meta}</span></div>'
                     f'<div class="gmi-cells">{vh_counts(mids)}{cells}</div></div>')
    assert cells_total == TOTAL, cells_total
    return '<div class="gmi-census gmi-census--coverage">' + "".join(bands) + "</div>"


LANES = [("upstream", "Upstream", "上游"), ("midstream", "Midstream", "中游"),
         ("downstream", "Downstream", "下游"), ("enabler", "Enabler", "赋能")]


def census_chain() -> str:
    bands = []
    total = 0
    for vcp, en, zh in LANES + [(None, "Not set yet", "尚未设定")]:
        mids = ordered([k for k, v in M.items() if v["vcp"] == vcp])
        total += len(mids)
        meta = t(f"{len(mids)}", f"{len(mids)}")
        cells = "".join(mark(micro_kind(m)) for m in mids)
        bands.append(f'<div class="gmi-cband"><div class="gmi-cband-label">'
                     f'<span class="gmi-cband-name">{t(en, zh)}</span><span class="gmi-cband-meta">{meta}</span></div>'
                     f'<div class="gmi-cells">{vh_counts(mids)}{cells}</div></div>')
    assert total == TOTAL
    note = t("Value-chain position is recorded for the extended set only. The core set’s positions are not recorded yet.",
             "仅扩展集记录了价值链位置；核心集的位置尚未记录。")
    return ('<div class="gmi-census gmi-census--chain">' + "".join(bands) +
            f'<p class="gmi-note" style="padding:8px 12px 0">{note}</p></div>')


def tree() -> str:
    rows = []
    caret = ic("chev", 16).replace("<svg ", '<svg class="gmi-trow-caret" ', 1)
    blank = '<span class="gmi-trow-caret" aria-hidden="true"></span>'
    for c in CATS:
        mids = ordered(c["micros"])
        is_open = c["id"] == "theme:semiconductors_hardware"
        strip = '<span class="gmi-trow-strip" aria-hidden="true">' + "".join(mark(micro_kind(m)) for m in mids) + "</span>"
        if not mids:
            rows.append(f'<div class="gmi-trow gmi-trow--empty" role="treeitem" aria-level="1">{blank}'
                        f'<span class="gmi-trow-name">{t(E(c["en"]), E(c["zh"]))}</span>'
                        f'<span class="gmi-trow-meta">{t("None yet", "暂无")}</span></div>')
            continue
        rows.append(f'<div class="gmi-trow{" gmi-trow--open" if is_open else ""}" role="treeitem" aria-level="1" '
                    f'aria-expanded="{"true" if is_open else "false"}" tabindex="0">{caret}'
                    f'<span class="gmi-trow-name">{t(E(c["en"]), E(c["zh"]))}</span>{strip}'
                    f'<span class="gmi-trow-meta">{len(mids)}</span></div>')
        if not is_open:
            continue
        for th in c["themes"]:
            th_open = th["id"] == "theme:ai_semiconductors"
            rows.append(f'<div class="gmi-trow gmi-trow--l2{" gmi-trow--open" if th_open else ""}" role="treeitem" aria-level="2" '
                        f'aria-expanded="{"true" if th_open else "false"}" tabindex="-1">{caret}'
                        f'<span class="gmi-trow-name">{t(E(th["en"]), E(th["zh"]))}</span>'
                        f'<span class="gmi-trow-meta">{th["micro_count"]}</span></div>')
            if not th_open:
                continue
            empty_subs = []
            for s in th["subs"]:
                if s["micros"]:
                    rows.append(f'<div class="gmi-trow gmi-trow--l3" role="treeitem" aria-level="3" aria-expanded="false" tabindex="-1">'
                                f'{caret}<span class="gmi-trow-name">{t(E(s["en"]), E(s["zh"]))}</span>'
                                f'<span class="gmi-trow-meta">{len(s["micros"])}</span></div>')
                else:
                    empty_subs.append(s)
            for mid in ordered(th["direct_micros"]):
                k = micro_kind(mid)
                rows.append(f'<div class="gmi-trow gmi-trow--l3" role="treeitem" aria-level="3" tabindex="-1">'
                            f'<span class="gmi-trow-caret" style="display:flex;align-items:center;justify-content:center">{mark(k)}</span>'
                            f'<span class="gmi-trow-name">{t(E(M[mid]["en"]), E(M[mid]["zh"]))}</span>'
                            f'<span class="gmi-trow-meta{" gmi-ink-info" if k == "held" else ""}">{t(*KIND_TAG[k])}</span></div>')
            if empty_subs:
                names_en = ", ".join(s["en"] for s in empty_subs)
                names_zh = "、".join(s["zh"] for s in empty_subs)
                rows.append(f'<div class="gmi-trow gmi-trow--l3 gmi-trow--empty">{blank}'
                            f'<span class="gmi-trow-name">{t(f"{len(empty_subs)} sub-themes have no micro-themes yet", f"{len(empty_subs)}个子主题尚无细分主题")}</span>'
                            f'{tip("Not mapped yet: " + names_en + ".", "尚未绘制：" + names_zh + "。")}</div>')
    rows.append(f'<a class="gmi-trow gmi-trow--more" href="s2_index.html">{ic("list", 16).replace("<svg ", "<svg class=\"gmi-trow-caret\" ", 1)}'
                f'<span class="gmi-trow-name">{t(f"See all {TOTAL} in the index", f"在索引中查看全部 {TOTAL} 个")}</span></a>')
    return '<div class="gmi-tree" role="tree">' + "".join(rows) + "</div>"


def s2_theme_map() -> str:
    hd = head([("Research", "研究"), ("Theme map", "主题地图")], t("Theme map", "主题地图"),
              t(f"{TOTAL} micro-themes mapped. None has an admitted company yet.",
                f"已绘制 {TOTAL} 个细分主题，尚无公司获准纳入。"), asof("2026-10-22"))
    tabs = ('<div class="mx-tabset" role="tablist">'
            f'<button type="button" role="tab" data-gmi-set-lens="coverage">{t("Review status", "审核状态")}</button>'
            f'<button type="button" role="tab" data-gmi-set-lens="chain">{t("Value chain", "价值链")}</button></div>')
    note = t("Each square is one micro-theme. Shape carries meaning; colour only repeats it.",
             "每个方块代表一个细分主题。含义由形状表达，颜色仅作重复提示。")
    band = f"""<section class="gmi-band" aria-labelledby="census-h"><div class="gmi-band-card">
{tally()}
<div>
<div class="mx-sec"><h2 id="census-h"><span class="gmi-census--coverage">{t("Every micro-theme, by category", "按类别列出全部细分主题")}</span><span class="gmi-census--chain">{t("Every micro-theme, by value-chain position", "按价值链位置列出全部细分主题")}</span></h2></div>
{tabs}
{key()}
</div>
{census_coverage()}
{census_chain()}
<p class="gmi-note">{note}</p>
</div></section>"""
    held_panel = f"""<section class="gmi-panel">
{sec("Held for review", "待审核", 2, tipx=tip(*TIP_HELD))}
<div class="gmi-status">{mark("held", xl=True)}<div>
<div class="gmi-status-t">{t("Micron → HBM &amp; advanced packaging", "美光科技 → HBM 与先进封装")}</div>
<div class="gmi-status-s">{t("Proposed, not a member. Not counted until reviewed.", "拟议关联，尚非成员。审核前不计入统计。")}</div>
</div></div>
<div><a class="gmi-btn gmi-btn--quiet" href="s1_issuer.html">{t("Open Micron", "查看美光科技")}{ic("arrow", 16)}</a></div>
</section>"""
    kinds = f"""<section class="gmi-panel">
{sec("Two kinds of micro-theme", "两类细分主题")}
<ul class="gmi-list gmi-list--prose">
<li>{mark("acc")}<span><b class="tnum">{CORE}</b> {t("Core set — the original set. Coverage is measured here.", "核心集 —— 最初的集合，覆盖率在此衡量。")}</span></li>
<li>{mark("disp")}<span><b class="tnum">{EXT}</b> {t("Extended — added 21 Oct 2026 for orientation. Not counted in coverage.", "扩展 —— 2026年10月21日新增，用于浏览，不计入覆盖率。")}</span></li>
</ul>
<div><a class="gmi-btn gmi-btn--quiet" href="s4_coverage.html">{t("How coverage is measured", "覆盖率如何衡量")}{ic("arrow", 16)}</a></div>
</section>"""
    tree_panel = f"""<section class="gmi-panel">
{sec("Browse the tree", "浏览主题树")}
{search_box(f"Search {TOTAL} micro-themes", f"搜索 {TOTAL} 个细分主题")}
</section>"""
    tree_panel = tree_panel.replace("</section>", f'<div class="gmi-panel gmi-panel--flush" style="box-shadow:none">{tree()}</div></section>')
    body = f"""{hd}
{band}
<div class="gmi-cols">
<div class="gmi-col-main">{tree_panel}</div>
<div class="gmi-col-side">{held_panel}{kinds}</div>
</div>"""
    return page("GMI Explorer — Theme map (reference)", body)


# ------------------------------------------------------------------ S2 full index (371-on-390 proof)
def s2_index() -> str:
    hd = head([("Research", "研究"), ("Theme map", "主题地图"), ("Index", "索引")], t("All micro-themes", "全部细分主题"),
              t(f"Every one of the {TOTAL}, grouped by category.", f"全部 {TOTAL} 个，按类别分组。"), asof("2026-10-22"))
    jump = (f'<nav class="gmi-jump" aria-label="{E("Categories")}"><div class="gmi-jump-track">' + "".join(
        f'<a href="#{c["id"].split(":")[1]}">{t(E(c["en"]), E(c["zh"]))}<small>{len(c["micros"])}</small></a>' for c in CATS)
        + "</div></nav>")
    groups = []
    rows_total = 0
    for c in CATS:
        gid = c["id"].split(":")[1]
        inner = []
        if not c["micros"]:
            inner.append(f'<div class="gmi-irow gmi-muted">{t("No micro-themes mapped yet", "尚未绘制细分主题")}</div>')
        bytheme: OrderedDict[str, list] = OrderedDict()
        for th in c["themes"]:
            bytheme[th["id"]] = []
        for mid in c["micros"]:
            bytheme.setdefault(M[mid]["primary_path"][1], []).append(mid)
        for thid, mids in bytheme.items():
            if not mids:
                continue
            en, zh = THEME_NAMES[thid]
            inner.append(f'<h3 class="gmi-index-t"><span>{t(E(en), E(zh))}</span><small>{len(mids)}</small></h3>')
            for mid in ordered(mids):
                k = micro_kind(mid)
                rows_total += 1
                tag_cls = "gmi-vh" if k == "disp" else "gmi-irow-tag"  # extended is the default tier: mark + group count carry it
                inner.append(f'<div class="gmi-irow{" gmi-irow--held" if k == "held" else ""}">{mark(k)}'
                             f'<span class="gmi-irow-name">{t(E(M[mid]["en"]), E(M[mid]["zh"]))}</span>'
                             f'<span class="{tag_cls}">{t(*KIND_TAG[k])}</span></div>')
        nc = sum(1 for mid in c["micros"] if M[mid]["tier"] == "acceptance")
        ne = len(c["micros"]) - nc
        comp = (t(f"{nc} core · {ne} extended", f"核心 {nc} · 扩展 {ne}") if c["micros"] else t("none yet", "暂无"))
        groups.append(f'<details class="gmi-index-group" id="{gid}" open>'
                      f'<summary class="gmi-index-h"><span class="gmi-index-hn">{t(E(c["en"]), E(c["zh"]))}</span>'
                      f'<span class="gmi-index-hc">{comp}</span><b>{len(c["micros"])}</b>{ic("chev", 16)}</summary>'
                      + "".join(inner) + "</details>")
    assert rows_total == TOTAL, rows_total
    body = f"""{hd}
<section class="gmi-panel">
{search_box(f"Search {TOTAL} micro-themes", f"搜索 {TOTAL} 个细分主题")}
{key()}
</section>
<div class="gmi-indexwrap">{jump}
<div class="gmi-index" data-gmi-index>{"".join(groups)}</div></div>
<script>{INDEX_JS}</script>
<script>{JUMP_JS}</script>
<p class="gmi-foot">{t(f"{TOTAL} rows: {CORE} core, {EXT} extended. Held and admitted links are marked on their row.", f"共 {TOTAL} 行：核心 {CORE} 个，扩展 {EXT} 个。待审核与已纳入的关联在所在行标注。")}</p>"""
    return page("GMI Explorer — All micro-themes (reference)", body)


# ------------------------------------------------------------------ S1 issuer explainer (Micron)
def chain(steps, kind="ladder") -> str:
    """One node grammar for the explorer (round 2, D4). Each step: pip + words; a connector joins
    pip to pip. pip in {doc, held, none}; cls adds gmi-chain-step--<cls> modifiers; edge labels
    the connector to the NEXT step."""
    out = []
    for st in steps:
        cls = "gmi-chain-step" + "".join(f" gmi-chain-step--{c}" for c in st.get("cls", ()))
        lvl = f'<span class="gmi-chain-lvl">{st["lvl"]}</span>' if st.get("lvl") else ""
        note = f'<span class="gmi-chain-note">{st["note"]}</span>' if st.get("note") else ""
        edge = f'<span class="gmi-chain-edge">{st["edge"]}</span>' if st.get("edge") else ""
        out.append(f'<li class="{cls}"><span class="gmi-chain-slot" aria-hidden="true"><span class="gmi-pip gmi-pip--{st["pip"]}"></span></span>'
                   f'<div class="gmi-chain-body">{lvl}<span class="gmi-chain-name">{st["name"]}</span>{note}</div>{edge}</li>')
    return f'<ol class="gmi-chain gmi-chain--{kind}">' + "".join(out) + "</ol>"


def s1_issuer() -> str:
    P = F["micron_proposal"]
    ev = P["evidence"]
    hbm = M["theme:hbm_packaging"]
    ident = '<div class="gmi-ident" style="margin-bottom:6px"><span class="gmi-ticker">MU · Nasdaq</span></div>'
    side = asof("2026-10-21") + f'<span class="gmi-chip gmi-chip--ghost">{t("Update history not tracked yet", "尚未跟踪更新记录")}</span>'
    hd = head([("Research", "研究"), ("Companies", "公司")], t("Micron Technology", "美光科技"),
              t("One proposed theme link, not yet a member.", "一个拟议主题关联，尚未成为成员。"), side, extra=ident)
    ladder = chain([
        dict(cls=("anchor",), pip="held", lvl=t("Micro-theme", "细分主题"), name=t(E(hbm["en"]), E(hbm["zh"])),
             note=t("Proposed place for Micron", "美光科技的拟议位置")),
        dict(cls=("void", "none"), pip="none", lvl=t("Sub-theme", "子主题"),
             name=t("None — sits directly under its theme", "无 —— 直接隶属于主题")),
        dict(cls=("theme",), pip="doc", lvl=t("Theme", "主题"), name=t(*THEME_NAMES["theme:ai_semiconductors"]),
             note=t("Also listed under Memory, HBM &amp; Storage", "亦列于：存储与HBM")),
        dict(cls=("cat",), pip="doc", lvl=t("Category", "类别"), name=t(*CAT_NAMES["theme:semiconductors_hardware"]),
             note=t("Its theme also sits in Technology &amp; software", "所属主题亦归入：科技与软件")),
    ], kind="ladder")
    hero = f"""<section class="gmi-band gmi-hero1" aria-labelledby="where-h">
<div class="gmi-hero1-top"><h2 id="where-h">{t("Where it would sit", "拟归属位置")}</h2>
<span class="gmi-hero1-st"><span class="gmi-pip gmi-pip--held" aria-hidden="true"></span>{t("Held for review", "待审核")} {tip(*TIP_HELD)}</span></div>
{ladder}
<p class="gmi-answer gmi-hero1-ans">{t("<b>Proposed, not a member.</b> Not used on the map or in any count until a curator reviews it.", "<b>拟议关联，尚非成员。</b>审核员审核前，不会用于主题地图或任何统计。")}</p>
</section>"""
    nd = t("Not disclosed", "未披露")
    sc = ev.get("scope", {})
    dl_rows = [
        (("Source", "来源"), f'<a href="#receipt">{t("Micron press release", "美光科技新闻稿")} · {d("2024-02-26")} {ic("ext", 14)}</a>'),
        (("Product", "产品"), E(sc.get("product", "24GB 8H HBM3E"))),
        (("Platform", "平台"), E(sc.get("platform", "NVIDIA H200"))),
        (("Customer named", "所提及客户"), t("NVIDIA", "英伟达")),
        (("Stage", "阶段"), t("Planned", "计划中")),
        (("On file since", "收录日期"), d("2026-10-11")),
    ]
    dl = '<dl class="gmi-dl gmi-dl--ledger">' + "".join(f"<div><dt>{t(*a)}</dt><dd>{b}</dd></div>" for a, b in dl_rows) + "</dl>"
    rail = '<div class="gmi-rail">' + "".join(
        f'<div class="gmi-rail-seg"><span class="gmi-rail-bar"></span><span class="gmi-rail-lab">{t(en, zh)}</span></div>' for _, en, zh in LANES) + \
        f'<div class="gmi-rail-seg gmi-rail-seg--unset gmi-rail-seg--on"><span class="gmi-rail-bar"></span><span class="gmi-rail-lab">{t("Not set yet", "尚未设定")}</span></div></div>'
    does = f"""<section class="gmi-flat">{sec("What Micron does", "美光科技的业务")}
<div class="gmi-facet"><div class="gmi-facet-h">{t("Principal activity", "主营业务")}</div>
<div class="gmi-facet-v gmi-facet-v--unset">{t("Not set yet", "尚未设定")}</div>
<p class="gmi-note">{t("No reviewed description of Micron’s main business is on file. It will appear here, with its source, once reviewed.", "目前没有经审核的美光科技主营业务描述。审核后将连同来源显示于此。")}</p></div>
<div class="gmi-facet"><div class="gmi-facet-h">{t("Value-chain position", "价值链位置")}</div>{rail}
<p class="gmi-note">{t("Not recorded for HBM &amp; advanced packaging yet.", "HBM与先进封装的价值链位置尚未记录。")}</p></div>
</section>"""
    main = f"""<section class="gmi-flat">{sec("Why it was proposed", "提议依据")}{dl}
<details class="mx-disc" id="receipt"><summary>{t("Receipt", "凭证")}<small>{t("proposal record, dates, permissions", "提议记录、日期、权限")}</small></summary>
<div class="mx-disc-body gmi-mono">proposal_status: PROPOSED · authority_caps: all false · graph_membership_use: NOT_GRANTED<br>
role: component_supplier · lifecycle: planned · relation: planned_product_integration<br>
clocks — publication 2024-02-26 · observation 2026-10-09 · knowledge 2026-10-11 · effective UNDISCLOSED<br>
magnitudes — amount UNDISCLOSED · economic_share UNDISCLOSED · rights: RIGHTS_FAMILY_UNRESOLVED</div></details>
<p class="gmi-note">{t("Nothing here is inferred beyond the cited text.", "以上内容均来自引文，未作推断。")}</p>
</section>
{does}"""
    unknowns = [("Whether Micron belongs here", "美光科技是否属于该主题", "Awaiting review", "待审核"),
                ("Deal size", "规模", "Not in the source", "来源未披露"),
                ("Start date", "开始日期", "Not in the source", "来源未披露"),
                ("Business segment", "业务分部", "Not in the source", "来源未披露")]
    ul = '<ul class="gmi-list">' + "".join(f"<li><span>{t(a, b)}</span><span>{t(c, e)}</span></li>" for a, b, c, e in unknowns) + "</ul>"
    sidecol = f"""<aside class="gmi-sheet">{sec("What we don’t know yet", "尚不清楚的信息")}{ul}
<div class="gmi-sheet-div">{sec("Documented relationships", "已记录的关系", 3)}
<p class="gmi-note">{t("None documented for Micron yet.", "美光科技暂无已记录的关系。")}</p>
<a class="gmi-btn gmi-btn--quiet" href="s3_relationships.html">{t("See documented relationships", "查看已记录的关系")}{ic("arrow", 16)}</a></div></aside>"""
    body = f"""{hd}
{hero}
<div class="gmi-cols gmi-cols--wide"><div class="gmi-col-main gmi-col-main--flat">{main}</div><div class="gmi-col-side">{sidecol}</div></div>"""
    return page("GMI Explorer — Micron Technology (reference)", body)


# ------------------------------------------------------------------ S3 relationships
DECK = F["deck"]
EDGE = F["edge"]
EXC = F["excerpt"]


def fill(tpl: str, **kw) -> str:
    out = tpl
    for k, v in kw.items():
        out = out.replace("{" + k + "}", v)
    assert "{" not in out, out
    return out


REASON = ("Part III only amendment", "仅修订第三部分")


def thread() -> str:
    cor = DECK["corrections"]
    hist = EDGE["magnitude_history"]
    fy24 = [h for h in hist if h["period"]["label"] == "FY2024"]
    fy25 = [h for h in hist if h["period"]["label"] == "FY2025"][0]
    cl = EDGE["correction_lineage"][0]
    items = []

    def acc(h):
        return h["source_ref"]["accession"]

    def pct(h):
        return f"{round(h['value'] * 100)}%"
    first24 = [h for h in fy24 if h["revision_kind"] == "new_period"][0]
    re24 = [h for h in fy24 if h["revision_kind"] == "reassertion"][0]
    items.append(("", first24["known_at"], fill(cor["first_published"]["en"], party="Skyworks", value=pct(first24), period="FY2024", form="10-K", accession=acc(first24), date=de(first24["known_at"])),
                  fill(cor["first_published"]["zh"], party="思佳讯", value=pct(first24), period=fy_zh("FY2024"), form="10-K", accession=acc(first24), date=dz(first24["known_at"]))))
    items.append(("re", re24["known_at"], fill(cor["reassertion"]["en"], form="10-K", accession=acc(re24), date=de(re24["known_at"]), value=pct(re24)),
                  fill(cor["reassertion"]["zh"], form="10-K", accession=acc(re24), date=dz(re24["known_at"]), value=pct(re24))))
    items.append(("", fy25["known_at"], fill(cor["first_published"]["en"], party="Skyworks", value=pct(fy25), period="FY2025", form="10-K", accession=acc(fy25), date=de(fy25["known_at"])),
                  fill(cor["first_published"]["zh"], party="思佳讯", value=pct(fy25), period=fy_zh("FY2025"), form="10-K", accession=acc(fy25), date=dz(fy25["known_at"]))))
    am = cl.get("accession") or "0000004127-26-000003"
    amends = cl.get("amends_accession") or cl.get("amends") or "0000004127-25-000085"
    known = cl.get("known_at") or "2026-01-30"
    items.append(("am", known, fill(cor["amendment_not_restated"]["en"], accession=am, amends_accession=amends, reason=REASON[0]),
                  fill(cor["amendment_not_restated"]["zh"], accession=am, amends_accession=amends, reason=REASON[1])))
    def monoacc(x):
        return re.sub(r"(\d{10}-\d{2}-\d{6})", r'<span class="gmi-mono">\1</span>', E(x))
    lis = "".join(f'<li><span class="gmi-node{" gmi-node--" + k if k else ""}"></span><div><time>{d(when)}</time>{t(monoacc(en), monoacc(zh))}</div></li>'
                  for k, when, en, zh in items)
    lead = t(fill(DECK["corrections"]["as_known_at"]["en"], as_of=de(known)), fill(DECK["corrections"]["as_known_at"]["zh"], as_of=dz(known)))
    return f'<p class="gmi-note" style="color:var(--text);font-weight:600">{lead}</p><ul class="gmi-thread">{lis}</ul>'


def hist_cols() -> str:
    by = OrderedDict()
    for h in EDGE["magnitude_history"]:
        by[h["period"]["label"]] = h["value"]
    cols = []
    labels = list(by.keys())
    for i, (lab, v) in enumerate(by.items()):
        now = i == len(labels) - 1
        cols.append(f'<div class="gmi-hist-col{" gmi-hist-col--now" if now else ""}"><span class="gmi-hist-v">{round(v * 100)}%</span>'
                    f'<span class="gmi-hist-bar" style="height:{round(v * 90)}px"></span><span class="gmi-hist-p">{t(lab.replace("FY20", "FY"), fy_zh(lab))}</span></div>')
    return '<div class="gmi-hist" aria-hidden="true">' + "".join(cols) + "</div>"


def species() -> str:
    counts = F["edge_package"]["counts"]["edges_by_species"]
    sp = [("supplier_customer", "Supplier → customer", "供应商 → 客户"),
          ("contract_manufacturing", "Contract manufacturing (foundry, CDMO)", "代工制造（晶圆代工、CDMO）"),
          ("licensing", "Licensing", "授权许可"), ("distribution", "Distribution", "分销"),
          ("component_dependency", "Component dependency", "零部件依赖")]
    out = []
    for k, en, zh in sp:
        c = counts.get(k, 0)
        cls = " gmi-spec--on" if k == "supplier_customer" else (" gmi-spec--zero" if c == 0 else "")
        out.append(f'<button type="button" class="gmi-spec{cls}" aria-pressed="{"true" if k == "supplier_customer" else "false"}">{t(en, zh)}<b>{c}</b></button>')
    return '<div class="gmi-species">' + "".join(out) + "</div>"


def s3_relationships() -> str:
    cm = EDGE["current_magnitudes"][0]
    pct = round(cm["value"] * 100)
    hd = head([("Research", "研究"), ("Relationships", "关系")], t("Documented relationships", "已记录的关系"),
              t("Links a company names in its own filings. One documented so far.", "公司在自身申报文件中写明的关联。目前已记录一条。"),
              asof("2026-10-21"))
    sent_en = fill(DECK["magnitude"]["seller_revenue_share"]["en"], party="Skyworks", numerator_scope=cm["numerator_scope"], pct=str(pct), denominator_scope=cm["denominator_scope"], period="FY2025")
    sent_zh = fill(DECK["magnitude"]["seller_revenue_share"]["zh"], party="思佳讯", numerator_scope=cm["numerator_scope"], pct=str(pct), denominator_scope=cm["denominator_scope"], period=fy_zh("FY2025"))
    acc = EXC["accession"]
    dl_rows = [
        (("Direction", "方向"), t("Skyworks supplies Apple", "思佳讯向苹果供货")),
        (("Period covered", "覆盖期间"), t("Oct 2021 – Oct 2025", "2021年10月 – 2025年10月")),
        (("Conditions", "条件"), t("None stated in the filing", "申报文件未列明条件")),
        (("First known", "首次获知"), d(EDGE["first_known_at"])),
        (("Last stated", "最近一次陈述"), d(EDGE["last_asserted_at"])),
        (("Last checked", "最近核对"), d(EDGE["last_assessed_at"])),
        (("Source", "来源"), f'<a href="#excerpt">10-K <span class="gmi-mono">{acc}</span> {ic("ext", 14)}</a>'),
    ]
    dl = '<dl class="gmi-dl">' + "".join(f"<div><dt>{t(*a)}</dt><dd>{b}</dd></div>" for a, b in dl_rows) + "</dl>"
    excerpt = f"""<details class="mx-disc" id="excerpt"><summary>{t("The filing’s words", "申报文件原文")}<small>10-K <span class="gmi-mono">{acc}</span></small></summary>
<div class="mx-disc-body"><blockquote class="gmi-quote"><span class="gmi-quote-lead">{t(E(DECK["lead_in"]["en"]), E(DECK["lead_in"]["zh"]))}</span>“{E(EXC["span"]["normalized"])}”</blockquote>
<p class="gmi-foot" style="margin-top:8px">{t(E(DECK["footer"]["en"]), E(DECK["footer"]["zh"]))} <span class="gmi-mono">{E(EXC["primary_document"])} · bytes {n(EXC["span"]["byte_start"])}–{n(EXC["span"]["byte_end"])}</span></p></div></details>"""
    hero = f"""<section class="gmi-band" aria-labelledby="rel-h"><div class="gmi-band-card">
<div class="gmi-relgrid"><div class="gmi-relgrid-a">
<div class="gmi-rel-head" id="rel-h"><span class="gmi-party">{t("Skyworks", "思佳讯")}</span>
<span class="gmi-arrow">{ARROW_LONG}{t("supplies", "供货")}</span><span class="gmi-party">{t("Apple", "苹果")}</span>
<span class="gmi-kind">· {t("Supplier → customer", "供应商 → 客户")}</span></div>
<div class="gmi-ident"><span class="gmi-ink-info" style="font-weight:600;font-size:var(--fs-sm)">{t("Proposed · not reviewed yet", "拟议 · 尚未审核")}</span>
<span class="gmi-chip gmi-chip--upd">{ic("refresh", 14)}{t("Read updated · " + de("2026-01-30"), "读取已更新 · " + dz("2026-01-30"))}</span></div>
<div class="gmi-mag"><div><div class="gmi-mag-num">{pct}<small>%</small></div>
<div class="gmi-mag-cap">{t("of Skyworks’ revenue came from Apple in FY2025", "思佳讯2025财年营收来自苹果的占比")}</div></div>
{hist_cols()}</div>
<p class="gmi-scope">{t(E(sent_en), E(sent_zh))}<span class="l-zh"> {E(DECK["scope_note"]["zh"])}</span></p>
</div><div class="gmi-relgrid-b">{dl}</div></div>
{excerpt}
</div></section>"""
    paths = f"""<section class="gmi-panel">{sec("Where this link leads", "关联路径")}
{chain([
    dict(pip="doc", lvl=t("Supplier", "供应商"), name=t("Skyworks", "思佳讯"), edge=t("supplies · no condition stated", "供货 · 未列明条件")),
    dict(cls=("to-none",), pip="doc", lvl=t("Customer", "客户"), name=t("Apple", "苹果"), edge=t("next step", "下一步")),
    dict(cls=("none",), pip="none", name=t("No documented links from Apple yet", "尚无苹果的已记录关联")),
], kind="edges")}
<p class="gmi-note">{t("Paths list documented links only. They do not estimate how far an effect spreads.", "路径仅列出已记录的关联，不估算影响的传导范围。")}</p></section>"""
    main = f"""<section class="gmi-panel">{sec("How this figure was read over time", "该数值的历次读取")}{thread()}</section>
{paths}"""
    micron = f"""<section class="gmi-panel">{sec("Held for review", "待审核", tipx=tip(*TIP_HELD))}
<div class="gmi-status">{mark("held", xl=True)}<div><div class="gmi-status-t">{t("Micron → HBM &amp; advanced packaging", "美光科技 → HBM 与先进封装")}</div>
<div class="gmi-status-s">{t("A proposed theme link, not a member. Not shown on the map.", "拟议主题关联，尚非成员，不在主题地图上显示。")}</div></div></div>
<dl class="gmi-dl"><div><dt>{t("Named customer", "所提及客户")}</dt><dd>{t("NVIDIA · H200 platform", "英伟达 · H200 平台")}</dd></div>
<div><dt>{t("Stage", "阶段")}</dt><dd>{t("Planned", "计划中")}</dd></div>
<div><dt>{t("Size", "规模")}</dt><dd>{t("Not disclosed", "未披露")}</dd></div>
<div><dt>{t("Use on the map", "用于主题地图")}</dt><dd>{t("Not permitted yet", "暂不允许")}</dd></div></dl>
<div><a class="gmi-btn gmi-btn--quiet" href="s1_issuer.html">{t("Open Micron", "查看美光科技")}{ic("arrow", 16)}</a></div></section>"""
    cov = f"""<section class="gmi-panel">{sec("How complete is this?", "覆盖程度")}
<div class="mx-empty" style="padding:8px 0;text-align:left"><div class="mx-empty-line">{t("Not measured yet", "尚未衡量")}</div>
<div class="mx-empty-why">{t("Filings from one company have been read so far. Zero elsewhere means none documented yet, not none exist.", "目前仅读取了一家公司的申报文件。其他处为零，表示尚未记录，而非不存在。")}</div></div></section>"""
    body = f"""{hd}
{species()}
<p class="gmi-foot">{t("Zero means none documented yet, not none exist.", "为零表示尚未记录，而非不存在。")}</p>
{hero}
<div class="gmi-cols"><div class="gmi-col-main">{main}</div><div class="gmi-col-side">{micron}{cov}</div></div>"""
    return page("GMI Explorer — Documented relationships (reference)", body)


# ------------------------------------------------------------------ S4 coverage & receipts
def stack(parts) -> str:
    total = sum(v for v, _, _, _ in parts)
    bar = '<div class="gmi-stack" aria-hidden="true">' + "".join(f'<i class="{cls}" style="flex:{v} 1 0"></i>' for v, cls, _, _ in parts) + "</div>"
    leg = '<div class="gmi-legend">' + "".join(f'<span><i class="{cls}" style="display:inline-block"></i><b>{n(v)}</b>{t(en, zh)}</span>' for v, cls, en, zh in parts) + "</div>"
    return bar.replace('<i class="', '<i class="').replace("</div>", "</div>", 1) + leg, total


def s4_coverage() -> str:
    us = F["coverage"]["us"]
    cn = F["coverage"]["cn"]
    ub = us["denominator"]["issuer_count_bounds"]
    cb = cn["denominator"]["issuer_count_bounds"]
    ur = us["remainder_by_reason"]
    hd = head([("Research", "研究"), ("Coverage", "覆盖率")], t("Coverage &amp; receipts", "覆盖率与凭证"),
              t("No company is admitted to a theme yet. Here is why.", "尚无公司获准纳入任何主题。原因如下。"), asof("2026-10-22"))
    us_parts = [(ur["IDENTITY_NOT_QUALIFIED"], "s1", "company identity not confirmed", "公司身份尚未确认"),
                (ur["VENDOR_MEMBERSHIP_ONLY"], "s2", "only on a third-party list", "仅见于第三方名单"),
                (ur["NO_ACTIVITY_EVIDENCE"], "s3", "no activity evidence", "无业务活动证据")]
    cn_parts = [(cn["remainder_by_reason"]["IDENTITY_NOT_QUALIFIED"], "s1", "company identity not confirmed", "公司身份尚未确认")]
    (us_html, us_tot), (cn_html, cn_tot) = stack(us_parts), stack(cn_parts)
    assert us_tot == ub[1] and cn_tot == cb[1], (us_tot, cn_tot)
    unres = us["denominator"].get("eligible_securities_unresolved_issuer", 6)

    def row(mkt_en, mkt_zh, b, parts_html, tp):
        return f"""<div class="gmi-cov-row"><div class="gmi-cov-top"><span class="gmi-cov-mkt">{t(mkt_en, mkt_zh)}</span>
<span class="gmi-cov-num">0</span><span class="gmi-cov-den">{t(f"of {n(b[0])}–{n(b[1])} companies", f"/ 共 {n(b[0])}–{n(b[1])} 家公司")}</span>{tip(*tp)}</div>
<div class="gmi-track"><span class="gmi-track-zero"></span></div>
<p class="gmi-note" style="margin-top:4px">{t("Why none is admitted yet", "尚无公司纳入的原因")}</p>{parts_html}</div>"""
    us_tip = (f"The count is a range because {unres} listed securities are not yet matched to a company.",
              f"该数字为区间，因为有{unres}只上市证券尚未匹配到对应公司。")
    cn_tip = ("The range is wide because none of the 1,019 listed securities is matched to a company yet.",
              "区间较宽，因为1,019只上市证券均尚未匹配到对应公司。")
    hero = f"""<section class="gmi-band" aria-labelledby="cov-h"><div class="gmi-band-card">
<div class="gmi-big0"><span class="gmi-mag-num" id="cov-h">0</span><span class="gmi-mag-cap" style="max-width:none">{t("companies admitted to any theme", "家公司获准纳入任何主题")}</span>{tip(*TIP_ADM)}</div>
<div class="gmi-cov">{row("US", "美国", ub, us_html, us_tip)}{row("China", "中国", cb, cn_html, cn_tip)}</div>
</div></section>"""
    strip = '<div class="gmi-strip68" aria-hidden="true">' + "".join(mark("held") if i == 0 else mark("acc") for i in range(CORE)) + "</div>"
    sets = f"""<section class="gmi-panel">{sec("What is measured", "衡量范围")}
<div class="gmi-tally-lab" style="color:var(--text)">{mark("acc")}<b class="tnum">{CORE}</b>&nbsp;{t("core micro-themes", "个核心细分主题")}{tip(*TIP_CORE)}</div>
{strip}
<p class="gmi-note">{t(f"{F['disposition_counts']['EMPTY']} have no admitted company. 1 has a link held for review.", f"{F['disposition_counts']['EMPTY']}个尚无获准纳入的公司；1个有待审核的关联。")}</p>
<div class="gmi-tally-lab gmi-tally-lab--wrap">{mark("disp")}<b class="tnum" style="color:var(--text)">{EXT}</b>&nbsp;{t("extended micro-themes are shown on the map but not counted.", "个扩展细分主题在地图上显示，但不计入。")}{tip(*TIP_EXT)}</div>
</section>"""
    corr = f"""<section class="gmi-panel">{sec("Corrections log", "更正记录")}
<dl class="gmi-dl"><div><dt>{d("2026-01-30")}</dt><dd>{t("Skyworks 10-K/A amends its 10-K. The Apple revenue share is unchanged.", "思佳讯10-K/A修订其10-K，来自苹果的营收占比未变。")}</dd></div>
<div><dt>{t("Theme links", "主题关联")}</dt><dd class="gmi-muted">{t("Changes are not tracked yet.", "变更尚未跟踪。")}</dd></div></dl></section>"""
    acc = f"""<section class="gmi-panel">{sec("Accuracy check", "准确性抽查")}
<div class="mx-empty" style="padding:8px 0;text-align:left"><div class="mx-empty-line">{t("Not measured yet", "尚未衡量")}</div>
<div class="mx-empty-why">{t("Needs 200 admitted links (100 US, 100 China) before a sample is drawn. Now 0.", "需要200条获准纳入的关联（美国100条、中国100条）后才会抽样。目前为0。")}</div></div></section>"""
    body = f"""{hd}
{hero}
<div class="gmi-cols"><div class="gmi-col-main">{sets}{corr}</div><div class="gmi-col-side">{acc}</div></div>
<p class="gmi-foot">{t("Sources: company filings; exchange symbol directory, 21 Oct 2026; review ledger, 22 Oct 2026.", "来源：公司申报文件；交易所证券代码目录（2026年10月21日）；审核记录（2026年10月22日）。")}</p>"""
    return page("GMI Explorer — Coverage & receipts (reference)", body)


# ------------------------------------------------------------------ S5 states sheet
def state(icon, ink, key_, t_en, t_zh, body, ok_en="", ok_zh="", actions=""):
    ok = f'<p class="gmi-state-ok">{t(ok_en, ok_zh)}</p>' if ok_en else ""
    act = f'<div class="gmi-state-a">{actions}</div>' if actions else ""
    return (f'<article class="gmi-state"><div class="gmi-state-h"><span class="{ink}" style="display:flex">{ic(icon)}</span>'
            f'<span class="gmi-state-t">{t(t_en, t_zh)}</span><span class="gmi-state-k">{key_}</span></div>{body}{ok}{act}</article>')


def s5_states() -> str:
    hd = head([("Research", "研究"), ("Theme map", "主题地图")], t("Data states", "数据状态"),
              t("How each surface reads when data is late, missing or held.", "数据延迟、缺失或暂缓时，各页面如何呈现。"), asof("2026-10-22"))
    mini_census = '<div class="gmi-mini">' + "".join(
        f'<div style="display:flex;gap:10px;align-items:center"><span style="flex:0 0 110px">{t(E(c["en"]), E(c["zh"]))}</span>'
        f'<span style="display:flex;flex-wrap:wrap;gap:3px;--gmi-cell:8px">{"".join(mark(micro_kind(m)) for m in ordered(c["micros"]))}</span></div>'
        for c in CATS[:3]) + "</div>"
    cards = [
        state("alert", "gmi-ink-warn", "fetch_failed", "Couldn’t load the theme map", "主题地图加载失败",
              f'<p>{t("The latest read did not arrive.", "最新一次读取未能送达。")}</p>',
              "Search and the full index still work from the last read (22 Oct 2026).", "搜索与完整索引仍可使用上次读取结果（2026年10月22日）。",
              f'<button class="gmi-btn" type="button">{ic("refresh", 16)}{t("Retry", "重试")}</button><a class="gmi-btn gmi-btn--quiet" href="s2_index.html">{t("Open index", "打开索引")}</a>'),
        state("clock", "gmi-muted", "stale", "Showing the 19 Oct read", "显示10月19日的读取结果",
              f'<div><span class="gmi-chip gmi-chip--upd">{ic("refresh", 14)}{t("Read being updated", "读取结果更新中")}</span></div><div class="gmi-degraded"><div class="gmi-degraded-body">{mini_census}</div></div>',
              "Counts and links are as of 19 Oct 2026 until the new read lands.", "新读取结果送达前，计数与关联以2026年10月19日为准。"),
        state("info", "gmi-ink-info", "rights_withheld", "Size withheld", "规模暂不显示",
              f'<div class="gmi-mini"><div class="gmi-rel-head"><b>{t("Skyworks", "思佳讯")}</b><span class="gmi-arrow">{ARROW_LONG}</span><b>{t("Apple", "苹果")}</b></div>'
              f'<div style="display:flex;align-items:baseline;gap:10px"><span class="gmi-mag-num" style="font-size:var(--fs-num-lg)">—</span><span class="gmi-muted">{t("Size withheld", "规模暂不显示")}</span></div></div>'
              f'<p>{t("Display rights for this figure are still being confirmed. The source filing is linked.", "该数值的展示权限仍在确认中。已附来源申报文件链接。")}</p>',
              "The relationship, its dates and the source stay visible.", "关系本身、日期与来源仍然可见。",
              f'<a class="gmi-btn gmi-btn--quiet" href="s3_relationships.html#excerpt">{t("Open the filing", "打开申报文件")}{ic("ext", 16)}</a>'),
        state("eyeoff", "gmi-muted", "purpose_denied", "Limited to research use", "仅限研究用途",
              f'<p>{t("This detail is limited to research use.", "此详情仅限研究用途。")}</p>',
              "The theme map and coverage still work.", "主题地图与覆盖率仍可使用。",
              f'<a class="gmi-btn gmi-btn--quiet" href="s2_theme_map.html">{t("Open the theme map", "打开主题地图")}{ic("arrow", 16)}</a>'),
        state("pause", "gmi-ink-warn", "source_paused", "Paused: source check failed", "已暂停：来源校验未通过",
              f'<p>{t("A source file did not match its record, so this view is paused rather than shown wrong.", "某来源文件与其记录不一致，因此暂停显示，而不是显示错误内容。")}</p>',
              "Everything else on the page still works.", "页面其余部分仍可正常使用。",
              f'<button class="gmi-btn" type="button">{t("Show last verified read · 21 Oct 2026", "显示上次核实的读取结果 · 2026年10月21日")}</button>'),
        state("question", "gmi-muted", "unknown", "Not disclosed · Not set yet", "未披露 · 尚未设定",
              f'<dl class="gmi-dl"><div><dt>{t("Deal size", "规模")}</dt><dd>{t("Not disclosed", "未披露")}</dd></div>'
              f'<div><dt>{t("Value-chain position", "价值链位置")}</dt><dd>{t("Not set yet", "尚未设定")}</dd></div></dl>'
              f'<p>{t("“Not disclosed” means the company did not publish it. “Not set yet” means we have not recorded it.", "“未披露”表示公司未公布；“尚未设定”表示我们尚未记录。")}</p>'),
        state("clock", "gmi-muted", "loading", "Loading", "加载中",
              '<div style="display:flex;flex-direction:column;gap:10px"><span class="skel gmi-skel-line gmi-skel-line--m"></span>'
              '<span class="skel gmi-skel-line"></span><span class="skel gmi-skel-line gmi-skel-line--s"></span></div>',
              "The page frame and navigation are usable while rows load.", "行数据加载期间，页面框架与导航可正常使用。"),
        state("file", "gmi-muted", "empty", "No documented relationships yet", "尚无已记录的关系",
              f'<div class="mx-empty" style="padding:8px 0;text-align:left"><div class="mx-empty-why">{t("Zero means none documented yet, not none exist.", "为零表示尚未记录，而非不存在。")}</div></div>',
              "The company’s themes and filings still show.", "该公司的主题与申报文件仍可查看。",
              f'<a class="gmi-btn gmi-btn--quiet" href="s1_issuer.html">{t("Open the company", "打开公司页")}{ic("arrow", 16)}</a>'),
        state("refresh", "gmi-ink-info", "read_updated", "Read updated", "读取已更新",
              f'<div><span class="gmi-chip gmi-chip--upd">{ic("refresh", 14)}{t("Read updated · 30 Jan 2026", "读取已更新 · 2026年1月30日")}</span></div>'
              f'<p>{t("A later filing touched this figure. Open it to see what changed and what did not.", "后续申报文件涉及该数值。打开即可查看变更与未变更之处。")}</p>', "", "",
              f'<a class="gmi-btn gmi-btn--quiet" href="s3_relationships.html">{t("See what changed", "查看变更")}{ic("arrow", 16)}</a>'),
        state("list", "gmi-muted", "path_template", "Conditioned path · layout only", "附条件路径 · 仅版式",
              f'<p class="gmi-muted">{t("No documented conditioned path exists yet. This shows where a stated condition would sit.", "目前尚无已记录的附条件路径。此处仅示意所述条件的位置。")}</p>'
              + chain([
                  dict(cls=("wide", "to-none"), pip="doc", name=t("Skyworks", "思佳讯"),
                       edge=t(E(fill(DECK["premises"]["concentration_risk"]["en"], counterparty="Apple")), E(fill(DECK["premises"]["concentration_risk"]["zh"], counterparty="苹果")))),
                  dict(cls=("none",), pip="none", name=t("Effect stated in the filing", "申报文件所述影响"),
                       note=t("quoted text appears here", "此处显示引文")),
              ], kind="edges") +
              f'<p class="gmi-foot">{t(E(DECK["lead_in"]["en"]), E(DECK["lead_in"]["zh"]))} …</p>'),
    ]
    body = f"""{hd}
<p class="gmi-note">{t("Every state says what failed, what still works, and one next step. Keys in the corner are for builders and are not shown in the product.", "每种状态都说明：哪里失败、哪些仍可用、下一步做什么。右上角的键名供开发参考，不在产品中显示。")}</p>
<div class="gmi-states">{"".join(cards)}</div>"""
    return page("GMI Explorer — Data states (reference)", body)


PAGES = {
    "s1_issuer": s1_issuer,
    "s2_theme_map": s2_theme_map,
    "s2_index": s2_index,
    "s3_relationships": s3_relationships,
    "s4_coverage": s4_coverage,
    "s5_states": s5_states,
}


def render_png(names):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    out = HERE / "png"
    out.mkdir(exist_ok=True)
    jobs = []
    for nm in names:
        for th in ("dark", "light"):
            for lg in ("en", "zh"):
                for w in (1440, 390):
                    jobs.append((nm, th, lg, w, "coverage", f"{nm}_{th}_{lg}_{w}.png"))
                    if nm == "s2_theme_map":
                        jobs.append((nm, th, lg, w, "chain", f"{nm}_chain_{th}_{lg}_{w}.png"))
                    if nm == "s2_index" and w == 390:
                        # density proof: every one of the 371 leaves expanded on a 390px phone
                        jobs.append((nm, th, lg, w, "coverage&open=all", f"{nm}_all371_{th}_{lg}_{w}.png"))
    with sync_playwright() as p:
        b = p.chromium.launch()
        for nm, th, lg, w, lens, fn in jobs:
            ctx = b.new_context(viewport={"width": w, "height": 900 if w > 500 else 844}, device_scale_factor=1)
            pg = ctx.new_page()
            pg.goto((HERE / f"{nm}.html").as_uri() + f"#theme={th}&lang={lg}&lens={lens}")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(150)
            # capture-only: theme.css paints the aurora wash on a position:fixed body::before, which a
            # full-page capture freezes at the first viewport (a hard band at 844/900px). Stretch it over
            # the document so the reference PNG reads as the page does while scrolling.
            pg.add_style_tag(content="body{position:relative !important} body::before{position:absolute !important;inset:0 !important}")
            if "open=all" in lens:
                vis = pg.evaluate("[...document.querySelectorAll('[data-gmi-index] .gmi-irow-name')].filter(e=>e.getClientRects().length).length")
                assert vis == TOTAL, (fn, vis)
                print(f"PROOF {fn}: {vis} index rows rendered and visible at {w}px")
            sw = pg.evaluate("document.documentElement.scrollWidth")
            if sw > w:
                print(f"WARN horizontal overflow {fn}: scrollWidth={sw}")
            path = out / fn
            pg.screenshot(path=str(path), full_page=True, animations="disabled")
            ctx.close()
            im = Image.open(path).convert("RGB")
            im.quantize(colors=256, method=Image.Quantize.FASTOCTREE).save(path, optimize=True)
            print(fn, im.size)
        b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    names = a.only or list(PAGES)
    for nm in names:
        (HERE / f"{nm}.html").write_text(PAGES[nm]())
        print("wrote", nm + ".html")
    if not a.html_only:
        render_png(names)


if __name__ == "__main__":
    main()
