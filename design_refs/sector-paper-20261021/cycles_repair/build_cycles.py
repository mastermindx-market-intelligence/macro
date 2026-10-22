#!/usr/bin/env python3
"""Build cycles.html — the Cycles corrections specimen (RIG boards 28–31) from the
committed example dataset (three production rows captured at d86344b93a0bd), the copy
deck and the canonical rendered chrome.
Every visible string is bound to copy_deck.json (cycles.*, components.*, states.*,
authority.*), to example_dataset.json (producer values rendered verbatim, including the
labeled fixture) or to enum_zh.json (ZH forms of producer enums that deck placeholders
consume). Producer field paths, codes and deck `source` citations render in mono as data.
Nothing user-facing is typed in this file. Run:  python3 build_cycles.py
"""
import html, json, pathlib
HERE = pathlib.Path(__file__).resolve().parent
DECK = json.loads((HERE.parent / "copy_deck.json").read_text(encoding="utf-8"))
DS = json.loads((HERE / "example_dataset.json").read_text(encoding="utf-8"))
ZH = json.loads((HERE / "enum_zh.json").read_text(encoding="utf-8"))
NAV = (HERE.parent / "brief_repair" / "nav_static.html").read_text(encoding="utf-8")
SOURCE_LABEL = "Sector Cycles"
META = DS["meta"]

def esc(s): return html.escape(str(s), quote=True)
def bi(en, zh): return f'<span class="l-en">{esc(en)}</span><span class="l-zh">{esc(zh)}</span>'
def D(sec, key, **fmt):
    e = DECK[sec][key]; en, zh = e["en"], e["zh"]
    if fmt: en, zh = en.format(**fmt), zh.format(**fmt)
    return bi(en, zh)
def D2(sec, key, en_fmt, zh_fmt):
    e = DECK[sec][key]; return bi(e["en"].format(**en_fmt), e["zh"].format(**zh_fmt))
def SRC(sec, key): return f'<code>{esc(DECK[sec][key]["source"])}</code>'
def icon(name): return f'<svg class="spc-icon" aria-hidden="true"><use href="#{name}"/></svg>'
def chip(inner, cls="", **data):
    attrs = "".join(f' data-{k}="{esc(v)}"' for k, v in data.items())
    return f'<span class="spc-chip {cls}"{attrs}>{inner}</span>'
def mono(s): return f'<span class="mono">{esc(s)}</span>'

SPRITE = ('<svg style="display:none" aria-hidden="true">'
          '<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.2"/><polyline points="12,7 12,12 15.4,14"/></symbol>'
          '<symbol id="i-alert" viewBox="0 0 24 24"><path d="M10.3 4.2 2.4 18a2 2 0 0 0 1.72 3h15.76a2 2 0 0 0 1.72-3L13.7 4.2a2 2 0 0 0-3.4 0Z"/>'
          '<line x1="12" y1="9.4" x2="12" y2="13.4"/><circle cx="12" cy="16.7" r="1" fill="currentColor" stroke="none"/></symbol></svg>')
PHASE_CHIP = {"Downturn": "phase_rolling_chip", "Trough": "phase_bottoming_chip", "Peak": "phase_topping_chip",
              "Expansion": "phase_trending_chip", "Recovery": "phase_prime_chip"}
HZ = (("1m", "hz_1m_chip"), ("3m", "hz_3m_chip"), ("6m", "hz_6m_chip"))

def asof():
    return (f'<p class="cyc-asof spc-asof-stamp">{icon("i-clock")}'
            f'{D("components", "asof_pattern", date=META["asOf"], source=SOURCE_LABEL)}</p>')

def head():
    lp = META["live_hazard_parity"]
    return f'''<header class="cyc-head">
<div class="cyc-panel">
<p class="cyc-eyebrow">{D("cycles","r1_header")}</p>
<h1>{D("cycles","title")}</h1>
<p class="cyc-tagline">{D("cycles","tagline")}</p>
<p class="cyc-intro">{D("cycles","intro_body")}</p>
{asof()}
</div>
<aside class="cyc-panel cyc-basis">
<div class="cyc-chips">{chip(D("authority","basis_price_only"))}{chip(D("cycles","rhythm_kind"))}{chip(D("cycles","hazard_parity_chip"), "cyc-warn")}</div>
<p class="cyc-foot">{mono(f'live_hazard_parity {lp["verdict"]} · {len(lp["failing"])} features · measured_on {lp["measured_on"][:8]}')}</p>
<p class="cyc-foot">{D("components","footnote_pattern")}</p>
</aside>
</header>'''

def age_line(now):
    a = now.get("phase_v2_age") or {}; st = a.get("status")
    if st == "lower_bound": body = D("cycles", "phase_age_lower_bound", n=a["sessions"], date=a["observed_from"])
    elif st == "measured": body = D("cycles", "phase_age_measured", n=a["sessions"])
    else: body = D("cycles", "phase_age_unknown")
    return f'<p class="cyc-age">{icon("i-clock")}<span>{body}</span></p>'

def hazard(s):
    h = s["now"]["hazard"]; ek = s["estimate_kinds"]
    heads = "".join(f'<span class="spc-hz-head">{D("cycles", k)}</span>' for _, k in HZ)
    rowlab = f'<span class="spc-hz-rowlab mono">{esc(h["direction"])} · {esc(h["turn_kind"])}</span>'
    parity = ""; muted = ""
    if h.get("unavailable"):
        cells = "".join('<span class="spc-hz-cell" data-source="none"><span class="spc-hz-val cyc-hz-gap" aria-hidden="true"></span></span>' for _ in HZ)
        note = f'<span class="spc-hz-note">{D("cycles","hazard_unavailable")} <code>{esc(h["unavailable_reason"])}</code></span>'
    else:
        cells = ""
        for hk, _ in HZ:
            c = h[hk]; src = c["source"].lower()
            badge = D("components", "badge_model" if src == "model" else "badge_prior")
            cells += (f'<span class="spc-hz-cell" data-source="{src}"><span class="spc-hz-val">{c["p"]*100:.0f}%</span>'
                      f'<span class="spc-model-prior-badge" data-source="{src}">{badge}</span>'
                      f'<span class="cyc-hz-cap mono">{esc(c["cell_verdict"])}</span></span>')
        mccc = ek.get("model_cell_current_claim")
        if mccc:
            muted = " cyc-hz-muted"
            parity = f'<div class="cyc-chips">{chip(D("cycles","hazard_parity_chip"), "cyc-warn")}<code>model_cell_current_claim {esc(mccc)}</code></div>'
        note = f'<span class="spc-hz-note">{D("cycles","hazard_footnote", direction=h["direction"])}</span>'
    return f'''<section class="cyc-sec"><div class="cyc-sec-ttl"><h3>{D("cycles","hazard_label")}</h3>{mono("epoch " + h["epoch"])}</div>
{parity}
<div class="spc-hazard-ladder{muted}" role="group"><span class="spc-hz-head"></span>{heads}{rowlab}{cells}{note}</div></section>'''

def rhythm(s):
    r = s["rhythm"]; w = r["window"]; unit = s["kind"]
    chips = chip(D("cycles","rhythm_kind")) + (chip(D("cycles","overdue_chip"), "cyc-warn") if r.get("overdue") else "")
    win = "".join(f'<div data-central="{str(k == "central").lower()}"><span class="k">{esc(k)}</span><span class="v">{esc(w[k])}</span></div>'
                  for k in ("low", "central", "high"))
    fn = D2("cycles", "forecast_footnote",
            dict(turn=r["next_turn"], month=w["central"], low=w["low"], high=w["high"], unit=unit),
            dict(turn=ZH[r["next_turn"]], month=w["central"], low=w["low"], high=w["high"], unit=ZH[unit]))
    stat = mono(f'{r["status"]} · n_confirmed_halves {r["n_confirmed_halves"]} · elapsed_half_cycle_ratio {r["elapsed_half_cycle_ratio"]}')
    return f'''<section class="cyc-sec"><div class="cyc-sec-ttl"><h3>{D("cycles","r6_timing")}</h3>{stat}</div>
<div class="cyc-rhythm-row">{chips}</div><div class="cyc-win">{win}</div><p class="cyc-foot">{fn}</p></section>'''

def read(now):
    return f'''<section class="cyc-sec"><div class="cyc-sec-ttl"><h3>{D("cycles","r5_read")}</h3>{mono("read · legacy family")}</div>
<p class="cyc-read-body">{bi(now["read"], now["read_zh"])}</p><p class="cyc-foot">{D("cycles","read_provenance")}</p></section>'''

def card(s):
    now = s["now"]; phase = now["phase_v2"]; pos = now["pos_v2"]
    stance = (f'<div class="cyc-stance-row"><span class="cyc-stance-ttl">{D("cycles","stance_label")}</span>'
              f'{chip(bi(now["stance"], now["stance_zh"]), "cyc-stance", tone=now["tone"])}')
    if now.get("divergence"):
        ck = now["clocks"]
        stance += (chip(D("cycles","clocks_chip"), "cyc-clocks")
                   + f'<p class="cyc-div-note">{bi(now["divergence_note"], now["divergence_note_zh"])} '
                     f'{mono("clocks.phase " + ck["phase"] + " · clocks.ladder " + ck["ladder"])}</p>')
    stance += "</div>"
    return f'''<article class="cyc-panel cyc-card" data-sector="{esc(s["id"])}">
<div class="cyc-card-head">
<div class="cyc-id"><h2>{bi(s["name"], s["name_zh"])}</h2><span class="cyc-tk">{esc(s["ticker"])}</span>
<span class="cyc-pos"><b>{pos:.0f}</b>/100<span class="b">{D("cycles","mode_osc_chip")} · {mono("pos_v2")}</span></span>
<span class="cyc-grp">{bi(s["group"], s["group_zh"])} · {mono(s["kind"] + " · " + s["basis"])}</span></div>
<div class="cyc-chips">{chip(D("cycles", PHASE_CHIP[phase]), "spc-phase-chip", phase=phase.lower())}{mono("phase_v2")}</div>
{stance}
{age_line(now)}
</div>
{hazard(s)}{rhythm(s)}{read(now)}
</article>'''

def methods():
    lp = META["live_hazard_parity"]; s0 = DS["sectors"][0]
    items = [
        ("now.hazard", D("cycles","hazard_label"), chip(D("cycles","hazard_parity_chip"), "cyc-warn"),
         mono(f'{lp["verdict"]} · {len(lp["failing"])} features · measured_on {lp["measured_on"][:8]}')),
        ("rhythm", D("cycles","rhythm_kind"), "", mono(f'rhythm_version {META["rhythm_version"]} · {s0["rhythm"]["schema"]}')),
        ("size_mult", D("cycles","sizing_inert"), "", SRC("cycles","sizing_inert")),
        ("lead_lag", D("cycles","leadlag_stop"), "", SRC("cycles","leadlag_stop")),
    ]
    grid = "".join(f'<div class="cyc-method"><span class="k">{esc(k)}</span><p>{body}</p>{chips}{src}</div>' for k, body, chips, src in items)
    return f'''<section class="cyc-panel cyc-methods"><p class="cyc-eyebrow">{D("cycles","r6_timing")}</p><div class="cyc-method-grid">{grid}</div></section>'''

def grader():
    return f'''<section class="cyc-panel cyc-grader"><p class="cyc-eyebrow">{D("cycles","r8_grader")}</p>
<h2>{D("components","grader_label")}</h2>
<p class="spc-grader-caption">{D("components","grader_caption")}</p>
<p class="cyc-grader-body">{D("authority","grader_body")}</p>
<p class="cyc-foot">{D("components","footnote_pattern")} <code>engine/sector_central_grader.py::grade</code></p></section>'''

def events():
    rc = DS["rotation_context"]; fx = DS["_fixtures"]["incompatible_generation"]
    chips = "".join(chip(mono(f'{k} · {v["status"]} · {v["artifact_session"]}')) for k, v in (("events", rc["events"]), ("fragmentation", rc["fragmentation"])))
    fresh = (f'<div class="cyc-ev-fresh"><span class="t">{icon("i-clock")}<span class="spc-asof-state" data-state="fresh">{D("states","fresh_title")}</span></span>'
             f'<span class="b">{D("states","fresh_body")}</span></div>')
    incompat = (f'<div class="cyc-ev-incompat"><div class="spc-state-banner" data-state="incompatible_generation">{icon("i-alert")}'
                f'<span class="spc-sb-word">{D("states","incompatible_generation_title")}</span>'
                f'<span class="spc-sb-msg">{D("states","incompatible_generation_body", x=fx["x"], y=fx["y"])}</span></div>'
                f'<p class="cyc-fixture">{esc(fx["label"])} · {esc(fx["query"])} · {esc(fx["basis"])}</p></div>')
    return f'''<section class="cyc-panel cyc-events"><p class="cyc-eyebrow">{D("cycles","r7_events")}</p>
<div class="cyc-chips cyc-ev-chips">{chips}</div>{fresh}{incompat}</section>'''

def metadata():
    s0 = DS["sectors"][0]; sp = s0["series_provenance"]; cc = META["correction_contract"]; lp = META["live_hazard_parity"]; sf = META["semantic_families"]
    rows = [("meta.asOf", META["asOf"]), ("meta.benchmark", META["benchmark"]), ("meta.rebaseDate", META["rebaseDate"]),
            ("series_provenance.structure_basis", sp["structure_basis"]), ("series_provenance.rs_basis", sp["rs_basis"]),
            ("series_provenance.history_mode", sp["history_mode"]), ("series_provenance.point_in_time", str(sp["point_in_time"]).lower()),
            ("meta.phase_age_version", META["phase_age_version"]), ("now.phase_v2_age.method", s0["now"]["phase_v2_age"]["method"]),
            ("meta.rhythm_version", META["rhythm_version"]), ("rhythm.schema", s0["rhythm"]["schema"]),
            ("now.hazard.epoch", s0["now"]["hazard"]["epoch"]), ("meta.live_hazard_parity.verdict", lp["verdict"]),
            ("meta.live_hazard_parity.measured_on", lp["measured_on"]),
            ("meta.correction_contract.status", cc["status"]), ("meta.correction_contract.basis", cc["basis"]),
            ("meta.semantic_families.schema", sf["schema"]), ("meta.semantic_families.legacy", ", ".join(sf["legacy"])),
            ("captured_at", DS["captured_at"])]
    dl = "".join(f'<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k, v in rows)
    return f'''<section class="cyc-panel cyc-meta"><p class="cyc-eyebrow">{D("cycles","r9_metadata")}</p>
<h2>{D("authority","built_asof", timestamp=META["asOf"])}</h2><dl>{dl}</dl></section>'''

CARDS = "".join(card(s) for s in DS["sectors"])
PAGE = f'''<!doctype html>
<html lang="en" data-theme="dark" data-lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sector Cycles — corrections specimen (RIG boards 28–31)</title>
<script>(function(){{var q=new URLSearchParams(location.search),d=document.documentElement;
var t=q.get("theme")||"dark",l=q.get("lang")||"en",s=q.get("state");
d.setAttribute("data-theme",t);d.setAttribute("data-lang",l);d.setAttribute("lang",l==="zh"?"zh-Hans":"en");
if(s)d.setAttribute("data-state",s);}})();</script>
<link rel="stylesheet" href="../../../templates/theme.css">
<link rel="stylesheet" href="../../../templates/navigation-refresh.css">
<link rel="stylesheet" href="../components/components.css">
<link rel="stylesheet" href="cycles.css">
</head>
<body class="macro-desk page-baskets">
{NAV}
<main class="cyc" id="main">{SPRITE}{head()}<div class="cyc-cards">{CARDS}</div>{methods()}<div class="cyc-two">{grader()}{events()}</div>{metadata()}</main>
<script>(function(){{var d=document.documentElement,w=innerWidth,o=[];d.setAttribute("data-h",String(d.scrollHeight));d.setAttribute("data-w",String(d.scrollWidth));
document.querySelectorAll("body *").forEach(function(e){{var r=e.getBoundingClientRect();if(r.right>w+1&&o.length<6)o.push(e.tagName.toLowerCase()+(e.className&&typeof e.className==="string"?"."+e.className.trim().split(/\\s+/).join("."):"")+"@"+Math.round(r.right));}});
d.setAttribute("data-ovf",o.join(" "));}})();</script>
</body>
</html>
'''
if __name__ == "__main__":
    out = HERE / "cycles.html"; out.write_text(PAGE, encoding="utf-8"); print(out.name, len(PAGE), "bytes")
    for s in DS["sectors"]:
        n = s["now"]; print(f'  {s["ticker"]}: phase {n["phase"]} / phase_v2 {n["phase_v2"]} · pos {n["pos"]} / pos_v2 {n["pos_v2"]} · clocks {n["clocks"]}')
