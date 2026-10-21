#!/usr/bin/env python3
"""Build brief.html — the R3 Brief specimen (RIG boards 23–26) from the committed
example dataset, the copy deck and the canonical rendered chrome.

Every visible string is bound to copy_deck.json (brief.*, components.*, states.*)
or to example_dataset.json (production rows rendered at d86344b93a0bd). Nothing
user-facing is typed in this file. Run:  python3 build_brief.py
"""
import html
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
DECK = json.loads((HERE.parent / "copy_deck.json").read_text(encoding="utf-8"))
DS = json.loads((HERE / "example_dataset.json").read_text(encoding="utf-8"))
NAV = (HERE / "nav_static.html").read_text(encoding="utf-8")
STAT_ZH = {k: v for k, v in json.loads((HERE / "stat_zh.json").read_text(encoding="utf-8")).items()
           if not k.startswith("_") and v}

SITE = "../../../site/"                    # row links resolve against a full checkout
COVERAGE = {"sectors": 11, "baskets": 49}  # render log at d86344b93a0bd: 11 sectors / 49 baskets
SOURCE_LABEL = "Sector Central"           # {source} of components.asof_pattern
BOTTOM_POS = {  # position in cycle range (N/100), read from the rendered bottoming strip
    "Nuclear & SMR Power": 2, "Power & Grid Buildout": 3, "Data-Center Power & Cooling": 6,
    "AI Infrastructure": 7, "Semiconductor Equipment (WFE)": 13,
    "Reshoring & Industrial Capex": 16, "Industrial Distribution & Capital Goods": 23}
LANE_STANCE = {  # production fold id -> (stance key, components.* stance string)
    "ab-buy-fold": ("act", "stance_act"), "ab-soon-fold": ("get_ready", "stance_get_ready"),
    "ab-run-fold": ("watch", "stance_watch"), "ab-trim-fold": ("protect", "stance_protect"),
    "dash-hold-fold": ("aside", "stance_aside")}
LOCKED_VISIBLE = 3   # rows the tier gate leaves visible (production: 3 + "23 more here")
FULL_VISIBLE = 8     # rows shown before "See all N"

DIAMOND = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.2 20.4 12 12 20.8 3.6 12Z"/></svg>'
SQUARE = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>'


def esc(s):
    return html.escape(str(s), quote=True)


def bi(en, zh):
    return f'<span class="l-en">{esc(en)}</span><span class="l-zh">{esc(zh)}</span>'


def D(sec, key, **fmt):
    e = DECK[sec][key]
    en, zh = e["en"], e["zh"]
    if fmt:
        en, zh = en.format(**fmt), zh.format(**fmt)
    return bi(en, zh)


def direction(v):
    if not v:
        return "flat"
    return "up" if v.startswith("+") else "down" if v.startswith("-") else "flat"


def stat_zh(r):
    return r.get("stat_zh") or STAT_ZH.get(r.get("stat_en") or "", "") or (r.get("stat_en") or "")


def row(r, stance, pos=None):
    theme = r["kind"] == "theme"
    badge = f'<span class="brf-bdg{" theme" if theme else ""}" aria-hidden="true">{DIAMOND if theme else SQUARE}</span>'
    name = f'<span class="brf-nm">{bi(r["name_en"], r["name_zh"])}</span>'
    lens = f'<span class="brf-lens">{D("brief", "lens_chip")}</span>' if r.get("lens_en") else ""
    if pos is not None:
        stat = f'<span class="brf-pos"><b>{pos}</b>/100<span class="b">{D("brief", "bottoming_basis")}</span></span>'
    elif r.get("stat_value"):
        stat = (f'<span class="brf-delta" data-dir="{direction(r["stat_value"])}">{esc(r["stat_value"])}'
                f'<span class="b">{bi(r.get("stat_en") or "", stat_zh(r))}</span></span>')
    else:
        stat = f'<span class="brf-delta" data-dir="flat">—<span class="b">{D("brief", "not_measured_chip")}</span></span>'
    if r.get("score") is not None:
        cls = {"act-score-hi": "hi", "act-score-mid": "mid", "act-score-lo": "lo"}.get(r.get("score_cls") or "", "mid")
        score = f'<span class="brf-score {cls}">{esc(r["score"])}<span class="b">{D("brief", "score_label")}</span></span>'
    else:
        score = f'<span class="brf-score none">—<span class="b">{D("brief", "not_measured_chip")}</span></span>'
    return (f'<a class="brf-row" href="{SITE}{esc(r["href"])}" data-stance="{stance}">'
            f'{badge}<span class="brf-cell">{name}{lens}</span>{stat}{score}</a>')


def lane_head(lid, title_html, count, sub_en, sub_zh, chip=""):
    return (f'<header class="brf-lane-head"><div class="brf-lane-top">'
            f'<h3 class="brf-lane-title" id="lane-{lid}">{title_html} <span class="cnt">{count}</span></h3>{chip}</div>'
            f'<p class="brf-lane-sub">{bi(sub_en, sub_zh)}</p></header>')


def lane(l):
    stance, skey = LANE_STANCE[l["fold_id"]]
    body = "".join(row(r, stance) for r in l["rows"])
    return (f'<section class="brf-lane" data-stance="{stance}" aria-labelledby="lane-{l["fold_id"]}">'
            f'{lane_head(l["fold_id"], bi(l["name_en"], l["name_zh"]), l["count"], l["sub_en"], l["sub_zh"])}'
            f'<div class="brf-rows">{body}</div></section>')


def stand_aside(l):
    stance, skey = LANE_STANCE[l["fold_id"]]
    allrows = l["rows"] + [r for w in DS["withheld"] for r in w["rows"]]
    assert len(allrows) == l["count"], (len(allrows), l["count"])
    full = "".join(row(r, stance) for r in allrows[:FULL_VISIBLE])
    locked = "".join(row(r, stance) for r in allrows[:LOCKED_VISIBLE])
    return (f'<section class="brf-lane" data-stance="{stance}" aria-labelledby="lane-{l["fold_id"]}">'
            f'{lane_head(l["fold_id"], bi(l["name_en"], l["name_zh"]), l["count"], l["sub_en"], l["sub_zh"])}'
            f'<div class="brf-rows brf-full">{full}'
            f'<button type="button" class="brf-more" aria-expanded="false">{D("components", "see_all_link", n=len(allrows))}</button></div>'
            f'<div class="brf-rows brf-locked">{locked}'
            f'<p class="brf-gate">{D("brief", "gate_more", n=len(allrows) - LOCKED_VISIBLE)}</p>'
            f'<div class="brf-lockrow"><span class="spc-lock-chip">{D("components", "lock_chip")}'
            f'<span class="spc-lock-why">{D("states", "locked_body")}</span></span></div></div></section>')


def bottoming(l):
    stance, skey = "watch", "stance_watch"
    body = "".join(row(r, stance, BOTTOM_POS[r["name_en"]]) for r in l["rows"])
    chip = f'<span class="brf-chip" data-stance="{stance}">{D("components", skey)}</span>'
    return (f'<section class="brf-lane brf-lane-bottoming" data-stance="{stance}" aria-labelledby="lane-bottoming">'
            f'{lane_head("bottoming", D("brief", "bottoming_title"), l["count"], l["sub_en"], l["sub_zh"], chip)}'
            f'<div class="brf-rows">{body}</div></section>')


def asof():
    return (f'<p class="brf-asof spc-asof-stamp"><span class="brf-health" aria-hidden="true"></span>'
            f'{D("components", "asof_pattern", date=DS["as_of"], source=SOURCE_LABEL)}</p>')


def hero():
    rg = DS["regime"]
    en = rg["rvx-vword"]["en"].replace("Leadership", '<span class="brf-key">Leadership</span>', 1)
    zh = rg["rvx-vword"]["zh"].replace("领涨格局", '<span class="brf-key">领涨格局</span>', 1)
    days = 1  # production stance qualifier at d86344b93a0bd: "1 days in / 已持续1天"
    return f'''
<section class="brf-hero" aria-labelledby="brf-h1">
  <div class="brf-panel brf-read">
    <p class="brf-eyebrow">{D("brief", "eyebrow")}</p>
    <h1 id="brf-h1"><span class="l-en">{en}</span><span class="l-zh">{zh}</span></h1>
    <p class="brf-stance"><span class="brf-chip" data-stance="watch">{bi(rg["rvx-stance"]["en"], rg["rvx-stance"]["zh"])}</span>
      <span class="brf-days">{D("brief", "stance_days", n=days)}</span></p>
    <p class="brf-method">{bi(rg["rvx-vsub"]["en"], rg["rvx-vsub"]["zh"])}</p>
    <div class="brf-hero-actions"><a href="#board">{D("brief", "leaders_link")}</a><a href="#board">{D("brief", "changed_link")}</a></div>
    {asof()}
    <p class="brf-foot spc-panel-footnote">{D("components", "footnote_pattern")}</p>
  </div>
  <aside class="brf-panel brf-handoff" aria-labelledby="brf-ho">
    <p class="brf-eyebrow" id="brf-ho">{D("brief", "handoff_label")}</p>
    <div class="brf-ho">
      <span class="lbl">{D("brief", "trailing_label")}</span><span class="nm">{bi("Energy", "能源")}</span>
      <span class="arrow" aria-hidden="true">→</span><span class="spc-sr">{D("brief", "handoff_to_sr")}</span>
      <span class="lbl">{D("brief", "current_label")}</span><span class="nm">{bi("Health Care", "医疗保健")}</span>
    </div>
    <p class="meta">{D("brief", "distinction_body")}</p>
    <p class="brf-foot spc-panel-footnote">{D("brief", "basket_footnote")}</p>
  </aside>
</section>'''


def board():
    lanes = {l["fold_id"]: l for l in DS["lanes"]}
    top = "".join(lane(lanes[k]) for k in ("ab-buy-fold", "ab-soon-fold", "ab-run-fold", "ab-trim-fold"))
    return f'''
<section class="brf-panel brf-board" id="board" aria-labelledby="brf-h2">
  <header class="brf-board-head"><h2 id="brf-h2">{D("brief", "follow_h2")} <span class="cnt">{D("brief", "coverage_count", **COVERAGE)}</span></h2>
    <p class="brf-lane-disclaim">{D("brief", "lanes_disclaimer")}</p></header>
  <div class="brf-lanes">{top}</div>
  <div class="brf-lanes-2">{stand_aside(lanes["dash-hold-fold"])}{bottoming(lanes[None])}</div>
  <p class="brf-foot spc-panel-footnote"><span class="spc-fn-fix" aria-hidden="true">≈</span>{D("brief", "lens_leadership_only")}</p>
  {asof()}
</section>'''


def bottom():
    items = "".join(
        f'<li><span class="brf-nx-t">{D("brief", f"next_0{i}_title")}</span>'
        f'<a href="{href}">{D("brief", link)}</a><span class="brf-nx-d">{D("brief", f"next_0{i}_desc")}</span></li>'
        for i, (href, link) in enumerate([(SITE + "sector_central.html#map", "find_link"),
                                          (SITE + "sector_central.html#participation", "participation_link"),
                                          (SITE + "stocks.html", "companies_link")], 1))
    return f'''
<section class="brf-bottom">
  <div class="brf-panel brf-next" aria-labelledby="brf-h2-next"><h2 id="brf-h2-next">{D("brief", "next_h2")}</h2><ol>{items}</ol></div>
  <div class="brf-panel brf-track" aria-labelledby="brf-h2-track"><h2 id="brf-h2-track">{D("brief", "track_title")}</h2>
    <p class="brf-track-body">{D("brief", "track_body")}</p>
    <p class="spc-grader-caption">{D("components", "grader_caption")}</p>
    <div class="brf-hero-actions"><a href="{SITE}sector_central.html#grader">{D("brief", "track_link")}</a></div>
    {asof()}</div>
  <div class="brf-panel brf-cov" aria-labelledby="brf-cov-t"><div><p class="ttl" id="brf-cov-t">{D("brief", "coverage_unavailable_title")}</p>
    <p class="bd">{D("brief", "coverage_unavailable_body")}</p></div><span class="cnt">{D("brief", "coverage_count", **COVERAGE)}</span></div>
</section>'''


PAGE = f'''<!doctype html>
<html lang="en" data-theme="dark" data-lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sector Intelligence — Brief · R3 specimen</title>
<script>(function(){{var q=new URLSearchParams(location.search),d=document.documentElement;
var t=q.get("theme")||"dark",l=q.get("lang")||"en",s=q.get("state");
d.setAttribute("data-theme",t);d.setAttribute("data-lang",l);d.setAttribute("lang",l==="zh"?"zh-Hans":"en");
if(s)d.setAttribute("data-state",s);}})();</script>
<link rel="stylesheet" href="../../../templates/theme.css">
<link rel="stylesheet" href="../../../templates/navigation-refresh.css">
<link rel="stylesheet" href="../components/components.css">
<link rel="stylesheet" href="brief.css">
</head>
<body class="macro-desk page-baskets">
{NAV}
<main class="brf" id="main">{hero()}{board()}{bottom()}</main>
<script>(function(){{var d=document.documentElement,w=innerWidth,o=[];d.setAttribute("data-h",String(d.scrollHeight));d.setAttribute("data-w",String(d.scrollWidth));
document.querySelectorAll("body *").forEach(function(e){{var r=e.getBoundingClientRect();if(r.right>w+1&&o.length<6)o.push(e.tagName.toLowerCase()+(e.className&&typeof e.className==="string"?"."+e.className.trim().split(/\\s+/).join("."):"")+"@"+Math.round(r.right));}});
d.setAttribute("data-ovf",o.join(" "));}})();</script>
</body>
</html>
'''

if __name__ == "__main__":
    out = HERE / "brief.html"
    out.write_text(PAGE, encoding="utf-8")
    print(out.name, len(PAGE), "bytes")
