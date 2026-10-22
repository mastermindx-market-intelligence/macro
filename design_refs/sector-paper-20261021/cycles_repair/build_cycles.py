#!/usr/bin/env python3
"""Build cycles.html — the Cycles corrections specimen (RIG boards 28–31, 34–36) from the
committed example dataset (three production rows captured at d86344b93a0bd), the copy
deck and the canonical rendered chrome (shared shell: ../components/si_shell.py).

Wave 2 (verdict REVISE round 2, SIC-V2-C01..C14):
  C01  the face draws ONE stance vocabulary — the six doctrine stances
       (docs/DESIGN_DOCTRINE.md:44) via STANCE_MAP from the engine's resolved_stance
       (engine/cycle_ontology.py:113-123); the engine string + tone live in the drawer.
  C04  producer field paths, codes, hashes, verdict strings and the Built table render only
       inside a closed `<details class="cyc-prov">` drawer; the ZH face carries no English
       enum (enum_zh.json: direction, turn kind, kind, basis, status).
  C06  incompatible_generation: wrapping banner, muted clock chips, dated qualifier.
  C07  "(cycle position N/100)" and "Next projected …" are stripped from the face copy of
       the legacy read and kept verbatim in the drawer (cycles.read_legacy_withheld).
  C11  the producer `proj` window is drawer-only under cycles.proj_label.
Every visible string is bound to copy_deck.json, example_dataset.json (producer values
verbatim, fixture labeled) or enum_zh.json. Nothing user-facing is typed in this file.
Run:  python3 build_cycles.py
"""
import html, json, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "components"))
from si_shell import nav as shell_nav, page_header, workflow_nav, prov
DECK = json.loads((HERE.parent / "copy_deck.json").read_text(encoding="utf-8"))
DS = json.loads((HERE / "example_dataset.json").read_text(encoding="utf-8"))
ZH = json.loads((HERE / "enum_zh.json").read_text(encoding="utf-8"))
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
def code(s): return f'<code>{esc(s)}</code>'
def zh(v): return ZH[v]  # ZH form of a producer enum; KeyError is a deliberate build failure

SPRITE = ('<svg style="display:none" aria-hidden="true">'
          '<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.2"/><polyline points="12,7 12,12 15.4,14"/></symbol>'
          '<symbol id="i-alert" viewBox="0 0 24 24"><path d="M10.3 4.2 2.4 18a2 2 0 0 0 1.72 3h15.76a2 2 0 0 0 1.72-3L13.7 4.2a2 2 0 0 0-3.4 0Z"/>'
          '<line x1="12" y1="9.4" x2="12" y2="13.4"/><circle cx="12" cy="16.7" r="1" fill="currentColor" stroke="none"/></symbol></svg>')
PHASE_CHIP = {"Downturn": "phase_rolling_chip", "Trough": "phase_bottoming_chip", "Peak": "phase_topping_chip",
              "Expansion": "phase_trending_chip", "Recovery": "phase_prime_chip"}
HZ = (("1m", "hz_1m_chip"), ("3m", "hz_3m_chip"), ("6m", "hz_6m_chip"))
# C01 — engine resolved_stance (engine/cycle_ontology.py:113-123) -> doctrine stance (docs/DESIGN_DOCTRINE.md:44).
# Grouping follows the doctrine ink: Act / Get ready -> --ink-ok; Watch / Protect -> --ink-warn; Stand aside / Ignore -> --muted.
STANCE_MAP = {"BUY": "act", "GET READY": "get_ready", "HOLD": "watch", "HIGH-RISK BOUNCE": "watch",
              "TRIM": "protect", "SELL": "protect", "WAIT": "aside", "AVOID": "aside", "COUNTERTREND ONLY": "aside", None: "ignore"}
# C07 — legacy-family numerals withheld from the face (kept verbatim in the drawer).
STRIP_EN = (re.compile(r"\s*\(cycle position \d+/100\)"), re.compile(r"\s*Next projected (?:peak|trough): [0-9-]+\."))
STRIP_ZH = (re.compile(r"（周期位置 ?\d+/100）"), re.compile(r"预计下一(?:顶部|底部)：[0-9-]+。"))
def strip_read(s, pats):
    for p in pats: s = p.sub("", s)
    return s.strip()

def asof():
    return (f'<p class="cyc-asof spc-asof-stamp">{icon("i-clock")}'
            f'{D("components", "asof_pattern", date=META["asOf"], source=SOURCE_LABEL)}</p>')

def head():
    return f'''<header class="cyc-head">
<div class="cyc-panel">
<h2 class="cyc-h1">{D("cycles","title")}</h2>
<p class="cyc-tagline">{D("cycles","tagline")}</p>
<p class="cyc-intro">{D("cycles","intro_body")}</p>
{asof()}
</div>
<aside class="cyc-panel cyc-basis">
<div class="cyc-chips">{chip(D("authority","basis_price_only"))}{chip(D("cycles","rhythm_kind"))}{chip(D("cycles","hazard_parity_chip"), "cyc-warn")}</div>
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
    rowlab = f'<span class="spc-hz-rowlab">{D2("cycles","hazard_row_pattern", dict(direction=h["direction"], turn=h["turn_kind"]), dict(direction=zh(h["direction"]), turn=zh(h["turn_kind"])))}</span>'
    parity = ""; muted = ""
    if h.get("unavailable"):
        cells = "".join('<span class="spc-hz-cell" data-source="none"><span class="spc-hz-val cyc-hz-gap" aria-hidden="true"></span></span>' for _ in HZ)
        note = f'<span class="spc-hz-note">{D("cycles","hazard_unavailable")}</span>'
    else:
        cells = ""
        for hk, _ in HZ:
            c = h[hk]; src = c["source"].lower()
            badge = D("components", "badge_model" if src == "model" else "badge_prior")
            cells += (f'<span class="spc-hz-cell" data-source="{src}"><span class="spc-hz-val">{c["p"]*100:.0f}%</span>'
                      f'<span class="spc-model-prior-badge" data-source="{src}">{badge}</span></span>')
        if ek.get("model_cell_current_claim"):
            muted = " cyc-hz-muted"
            parity = chip(D("cycles","hazard_parity_chip"), "cyc-warn")
        note = f'<span class="spc-hz-note">{D("cycles","hazard_face_note")}</span>'
    return f'''<section class="cyc-sec"><div class="cyc-sec-ttl"><h3>{D("cycles","hazard_label")}</h3>{parity}</div>
<div class="spc-hazard-ladder{muted}" role="group"><span class="spc-hz-head"></span>{heads}{rowlab}{cells}{note}</div></section>'''

def rhythm(s):
    r = s["rhythm"]; w = r["window"]; unit = s["kind"]
    chips = chip(D("cycles","rhythm_kind")) + (chip(D("cycles","overdue_chip"), "cyc-warn") if r.get("overdue") else "")
    win = "".join(f'<div data-central="{str(k == "central").lower()}"><span class="k">{D("cycles", "win_" + k)}</span><span class="v">{esc(w[k])}</span></div>'
                  for k in ("low", "central", "high"))
    fn = D2("cycles", "forecast_footnote",
            dict(turn=r["next_turn"], month=w["central"], low=w["low"], high=w["high"], unit=unit),
            dict(turn=zh(r["next_turn"]), month=w["central"], low=w["low"], high=w["high"], unit=zh(unit)))
    return f'''<section class="cyc-sec"><div class="cyc-sec-ttl"><h3>{D("cycles","r6_timing")}</h3></div>
<div class="cyc-rhythm-row">{chips}</div><div class="cyc-win">{win}</div><p class="cyc-foot">{fn}</p></section>'''

def read(now):
    en = strip_read(now["read"], STRIP_EN); zh_ = strip_read(now["read_zh"], STRIP_ZH)
    return f'''<section class="cyc-sec"><div class="cyc-sec-ttl"><h3>{D("cycles","r5_read")}</h3></div>
<p class="cyc-read-body">{bi(en, zh_)}</p><p class="cyc-foot">{D("cycles","read_provenance")}</p></section>'''

def card_prov(s):
    now = s["now"]; h = now["hazard"]; ek = s["estimate_kinds"]; r = s["rhythm"]; pj = s["proj"]; ck = now["clocks"]; a = now.get("phase_v2_age") or {}; lfp = ek.get("live_feature_parity")
    items = [
        (D("cycles","stance_label"), D2("cycles","stance_engine_pattern", dict(stance=now["stance"], tone=now["tone"]), dict(stance=now["stance_zh"], tone=now["tone"])) + " " + code("resolved_stance · " + DECK["cycles"]["stance_label"]["source"])),
        (code("clocks"), mono(f'phase {ck["phase"]} · ladder {ck["ladder"]} · agree {str(ck["agree"]).lower()}')),
        (code("pos_v2 · phase_v2"), mono(f'{now["pos_v2"]} · {now["phase_v2"]} · source {now["phase_v2_source"]} · age {a.get("status")} · method {a.get("method")}')),
        (code("now.hazard"), mono(f'epoch {h["epoch"]} · direction {h["direction"]} · turn_kind {h["turn_kind"]}')
            + ("".join(" · " + mono(f'{hk} {h[hk]["source"]} {h[hk]["cell_verdict"]}') for hk, _ in HZ) if not h.get("unavailable") else " · " + mono(f'unavailable_reason {h["unavailable_reason"]}'))),
        (code("estimate_kinds"), mono(f'schema {ek["schema"]} · hazard {ek["hazard"]} · model_cell_current_claim {ek.get("model_cell_current_claim")}'
            + (f' · live_feature_parity {lfp["verdict"]} · {len(lfp["failing"])} features' if lfp else ' · live_feature_parity null'))),
        (code("hazard_footnote"), D2("cycles","hazard_footnote", dict(direction=h["direction"]), dict(direction=zh(h["direction"])))),
        (code("rhythm"), mono(f'{r["schema"]} · {r["status"]} · n_confirmed_halves {r["n_confirmed_halves"]} · elapsed_half_cycle_ratio {r["elapsed_half_cycle_ratio"]} · overdue {str(r.get("overdue")).lower()}')),
        (D("cycles","proj_label"), mono(f'{pj["nextTurn"]} · central {pj["central"]} · low {pj["low"]} · high {pj["high"]} · overdue_frac {pj["overdue_frac"]} · period_yrs median {pj["period_yrs"]["median"]}') + " " + code(DECK["cycles"]["proj_label"]["source"].split(";")[0])),
        (D("cycles","read_legacy_withheld"), f'<span class="cyc-prov-read">{bi(now["read"], now["read_zh"])}</span>'),
    ]
    return prov(items)

def card(s):
    now = s["now"]; phase = now["phase_v2"]; pos = now["pos_v2"]; skey = STANCE_MAP[now.get("stance")]
    stance = (f'<div class="cyc-stance-row"><span class="cyc-stance-ttl">{D("components","stance_title")}</span>'
              f'{chip(D("components", "stance_" + skey), "cyc-stance", stance=skey)}')
    note = ""
    if now.get("divergence"):
        stance += chip(D("cycles","clocks_chip"), "cyc-clocks")
        note = f'<p class="cyc-div-note">{bi(now["divergence_note"], now["divergence_note_zh"])}</p>'
    stance += "</div>"
    return f'''<article class="cyc-panel cyc-card" data-sector="{esc(s["id"])}">
<div class="cyc-card-head">
<div class="cyc-id"><h2>{bi(s["name"], s["name_zh"])}</h2><span class="cyc-tk">{esc(s["ticker"])}</span>
<span class="cyc-pos"><b>{pos:.0f}</b>/100<span class="b">{D("cycles","mode_osc_chip")}</span></span>
<span class="cyc-grp">{bi(s["group"], s["group_zh"])} · {D2("cycles","kind_basis_pattern", dict(kind=s["kind"], basis=s["basis"]), dict(kind=zh(s["kind"]), basis=zh(s["basis"])))}</span></div>
<div class="cyc-chips">{chip(D("cycles", PHASE_CHIP[phase]), "spc-phase-chip", phase=phase.lower())}</div>
{stance}{note}
{age_line(now)}
</div>
{hazard(s)}{rhythm(s)}{read(now)}
{card_prov(s)}
</article>'''

def methods():
    lp = META["live_hazard_parity"]; s0 = DS["sectors"][0]
    items = [
        ("now.hazard", D("cycles","hazard_label"), chip(D("cycles","hazard_parity_chip"), "cyc-warn"),
         mono(f'live_hazard_parity {lp["verdict"]} · {len(lp["failing"])} features · measured_on {lp["measured_on"][:8]}')),
        ("rhythm", D("cycles","rhythm_kind"), "", mono(f'rhythm_version {META["rhythm_version"]} · {s0["rhythm"]["schema"]}')),
        ("size_mult", D("cycles","sizing_inert"), "", SRC("cycles","sizing_inert")),
        ("lead_lag", D("cycles","leadlag_stop"), "", SRC("cycles","leadlag_stop")),
    ]
    grid = "".join(f'<div class="cyc-method"><p>{body}</p>{chips}</div>' for _, body, chips, _ in items)
    drawer = prov([(code(k), src) for k, _, _, src in items])
    return f'''<section class="cyc-panel cyc-methods"><h2 class="cyc-sec-h2">{D("cycles","methods_h2")}</h2><div class="cyc-method-grid">{grid}</div>{drawer}</section>'''

def grader():
    return f'''<section class="cyc-panel cyc-grader"><p class="cyc-eyebrow">{D("cycles","r8_grader")}</p>
<h2>{D("components","grader_label")}</h2>
<p class="spc-grader-caption">{D("components","grader_caption")}</p>
<p class="cyc-grader-body">{D("authority","grader_body")}</p>
<p class="cyc-foot">{D("components","footnote_pattern")}</p>
{prov([(code("grader"), code("engine/sector_central_grader.py::grade"))], hint=False)}</section>'''

def events():
    rc = DS["rotation_context"]; fx = DS["_fixtures"]["incompatible_generation"]
    clocks = (("events", "events_chip", rc["events"]), ("fragmentation", "fragmentation_chip", rc["fragmentation"]))
    chips = "".join(chip(D("cycles", dk) + f' · <span class="cyc-ev-st">{bi(v["status"], zh(v["status"]))}</span>', "cyc-ev-chip", clock=k) for k, dk, v in clocks)
    qual = chip(D("cycles","aligned_qualifier", d=fx["x"]), "cyc-ev-qual cyc-warn")
    fresh = (f'<div class="cyc-ev-fresh"><span class="t">{icon("i-clock")}<span class="spc-asof-state" data-state="fresh">{D("states","fresh_title")}</span></span>'
             f'<span class="b">{D("states","fresh_body")}</span></div>')
    incompat = (f'<div class="cyc-ev-incompat"><div class="spc-state-banner" data-state="incompatible_generation">{icon("i-alert")}'
                f'<span class="spc-sb-word">{D("states","incompatible_generation_title")}</span>'
                f'<span class="spc-sb-msg">{D("states","incompatible_generation_body", x=fx["x"], y=fx["y"])}</span></div>'
                f'<p class="cyc-fixture">{chip(D("components","fixture_chip"), "cyc-fixture-chip")}</p></div>')
    drawer = prov([(code(k), mono(f'clock {v["clock"]} · status {v["status"]} · artifact_session {v["artifact_session"]} · consumer_session {v["consumer_session"]}')) for k, _, v in clocks]
                  + [(code("_fixtures.incompatible_generation"), mono(f'{fx["label"]} · {fx["query"]} · {fx["basis"]}'))], hint=False)
    return f'''<section class="cyc-panel cyc-events"><p class="cyc-eyebrow">{D("cycles","r7_events")}</p>
<div class="cyc-chips cyc-ev-chips">{chips}{qual}</div>{fresh}{incompat}{drawer}</section>'''

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
    return f'''<section class="cyc-panel cyc-meta"><p class="cyc-eyebrow">{D("cycles","r9_metadata")}</p>
<h2>{D("authority","built_asof", timestamp=META["asOf"])}</h2>{prov([(code(k), mono(v)) for k, v in rows], "cyc-prov-meta", hint=False)}</section>'''

CARDS = "".join(card(s) for s in DS["sectors"])
PAGE = f'''<!doctype html>
<html lang="en" data-theme="dark" data-lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sector Cycles — corrections specimen (RIG boards 28–31, 34–36)</title>
<script>(function(){{var q=new URLSearchParams(location.search),d=document.documentElement;
var t=q.get("theme")||"dark",l=q.get("lang")||"en",s=q.get("state");
d.setAttribute("data-theme",t);d.setAttribute("data-lang",l);d.setAttribute("lang",l==="zh"?"zh-Hans":"en");
if(s)d.setAttribute("data-state",s);}})();</script>
<link rel="stylesheet" href="../../../templates/theme.css">
<link rel="stylesheet" href="../../../templates/navigation-refresh.css">
<link rel="stylesheet" href="../components/si_shell.css">
<link rel="stylesheet" href="../components/components.css">
<link rel="stylesheet" href="cycles.css">
</head>
<body class="macro-desk page-baskets">
{shell_nav()}
<main class="cyc si-shell" id="main">{page_header(asof())}{workflow_nav("cycles")}{SPRITE}{head()}<div class="cyc-cards">{CARDS}</div>{methods()}<div class="cyc-two">{grader()}{events()}</div>{metadata()}</main>
<script>(function(){{var d=document.documentElement,w=innerWidth,o=[];
var wf=document.querySelector(".si-workflow[data-aria-zh]");if(wf&&d.getAttribute("data-lang")==="zh")wf.setAttribute("aria-label",wf.getAttribute("data-aria-zh"));
d.setAttribute("data-h",String(d.scrollHeight));d.setAttribute("data-w",String(d.scrollWidth));
document.querySelectorAll("body *").forEach(function(e){{var r=e.getBoundingClientRect();if(r.right>w+1&&o.length<6)o.push(e.tagName.toLowerCase()+(e.className&&typeof e.className==="string"?"."+e.className.trim().split(/\\s+/)[0]:""));}});
d.setAttribute("data-ovf",o.join(" "));}})();</script>
</body>
</html>
'''
if __name__ == "__main__":
    out = HERE / "cycles.html"; out.write_text(PAGE, encoding="utf-8"); print(out.name, len(PAGE), "bytes")
    for s in DS["sectors"]:
        n = s["now"]; print(f'  {s["ticker"]}: stance {n["stance"]} -> {STANCE_MAP[n["stance"]]} · phase_v2 {n["phase_v2"]} · pos_v2 {n["pos_v2"]} · clocks agree {n["clocks"]["agree"]}')
        print("     face read:", strip_read(n["read"], STRIP_EN)[:110], "|", strip_read(n["read_zh"], STRIP_ZH)[:60])
