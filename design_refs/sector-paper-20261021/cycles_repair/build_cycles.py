#!/usr/bin/env python3
"""Build cycles.html — the Cycles corrections specimen (RIG boards 28–31, 34–36, 39–41) from the
committed example dataset (three production rows captured at d86344b93a0bd), the copy
deck and the canonical rendered chrome (shared shell: ../components/si_shell.py).

Wave 2 (verdict REVISE round 2, SIC-V2-C01..C14):
  C01  the face draws ONE stance vocabulary — the six doctrine stances
       (docs/DESIGN_DOCTRINE.md:44). Wave 3 (SIC-ADJ-01 / SIC-V3-C01, C02): the wave-2
       STANCE_MAP is gone from this builder; the producer stamps doctrine_stance* on every
       cell (engine/cycle_ontology.py DOCTRINE_STANCE :147 · doctrine_for :179; dataset
       stamped by stamp_doctrine.py) and the face prints the stamped fields under the
       "Engine mapping" eyebrow; null stance → muted "Stance unavailable", no chip. The
       engine string + tone live verbatim in the drawer.
  C03' (wave 3, SIC-V3-C03) one phase per face: the legacy read sits on the face only on
       family_match (engine short label of now.phase == that of now.phase_v2); otherwise
       the labeled Clocks-disagree state names both clocks (XLC) and the read is drawer-only.
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
SOURCE_LABEL_ZH = DECK["cycles"]["title"]["zh"]  # wave 3 (SIC-V3-C06): bilingual source label on the as-of stamp (production page title zh)
PC = json.loads((HERE / "prod_capture.json").read_text(encoding="utf-8"))  # SIC-V3-C09 capture provenance
BRIEF_ASOF = json.loads((HERE.parent / "brief_repair" / "example_dataset.json").read_text(encoding="utf-8"))["as_of"]
META = DS["meta"]

def esc(s): return html.escape(str(s), quote=True)
def bi(en, zh): return f'<span class="l-en">{esc(en)}</span><span class="l-zh">{esc(zh)}</span>'
def D(sec, key, **fmt):
    e = DECK[sec][key]; en, zh = e["en"], e["zh"]
    if fmt: en, zh = en.format(**fmt), zh.format(**fmt)
    return bi(en, zh)
def DH(sec, key, **fmt):
    # Like D, but the fmt values are trusted HTML fragments (code()/mono()) inserted AFTER escaping the deck text, so an
    # identifier on a ZH face (page, sha, capture id, field name) is a <code> element the SIC-V3-C06 grep exempts (SIC-V4-C05).
    e = DECK[sec][key]; return f'<span class="l-en">{esc(e["en"]).format(**fmt)}</span><span class="l-zh">{esc(e["zh"]).format(**fmt)}</span>'
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
# SIC-ADJ-01 / SIC-V3-C01 (wave 3): no stance is computed or mapped here. The chip prints now.doctrine_stance_en/zh and
# inks by now.doctrine_ink exactly as the producer stamped them (engine/cycle_ontology.py DOCTRINE_STANCE :147 via
# doctrine_for :179, called from resolve_state :948; the specimen dataset is stamped by stamp_doctrine.py from that function).
# SIC-V3-C02: a null doctrine_stance draws the muted "Stance unavailable" line and no chip; there is no None entry anywhere.
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO))
from engine.cycle_ontology import PHASES as ONTO_PHASES  # noqa: E402 — engine/cycle_ontology.py:70-81, sole owner of phase labels/shorts
# SIC-V3-C03: the legacy read may sit on the face only when its phase word belongs to the chip's phase_v2 family.
# Family = the engine short label (engine/cycle_ontology.py:70-81); engine/sector_cycles.py:134-139 and :391-403 emit the
# same (phase, short) pairs. The test is on the labels of both clocks and the read text — never on clocks.agree.
PHASE_SHORT = {k: v["short"] for k, v in ONTO_PHASES.items()}
def family_match(now):
    legacy, v2 = now.get("phase"), now["phase_v2"]
    return legacy in PHASE_SHORT and PHASE_SHORT[legacy] == PHASE_SHORT[v2] and PHASE_SHORT[v2] in now["read"]
# SIC-V4-C02 (wave 4): the hazard leg (direction · turn_kind) and the rhythm projection (next_turn / proj.nextTurn) reach a
# card face only when they agree with the phase_v2 chip's family. Family = the engine's own direction split in classify_phase:
# rising -> Recovery / Expansion / Peak, falling -> Trough / Downturn (engine/cycle_ontology.py:614-629; a Peak is high-position
# AND rising by construction, :990-991). A rising family runs an up leg toward a peak, a falling family a down leg toward a
# trough. Disagreement draws the labeled mismatch state naming both clocks (SIC-V4-C03) and the row's values stay verbatim in
# the provenance drawer. Recorded per sector in the drawer (leg_family row).
LEG_OF = {"Recovery": ("up", "peak"), "Expansion": ("up", "peak"), "Peak": ("up", "peak"),
          "Trough": ("down", "trough"), "Downturn": ("down", "trough")}
assert set(LEG_OF) == set(ONTO_PHASES), "every engine phase names its leg"
def leg_family(s):
    now = s["now"]; h = now["hazard"]; d, t = LEG_OF[now["phase_v2"]]
    return {"direction": d, "turn": t,
            "hazard_agrees": (h["direction"], h["turn_kind"]) == (d, t),
            "rhythm_agrees": s["rhythm"]["next_turn"] == t and s["proj"]["nextTurn"] == t}
# SIC-V4-C04: the ZH face carries the chip's production phase label (回落中 … — templates/sector_cycles.js:600-604 / :1551-1557,
# via the deck phase_*_chip rows); the engine label_zh / short_zh (下行 …) are drawer-only. The EN short equals the production label.
PHASE_FACE_ZH = {p: DECK["cycles"][k]["zh"] for p, k in PHASE_CHIP.items()}
PHASE_LABEL_ZH = {k: v["label_zh"] for k, v in ONTO_PHASES.items()}
# SIC-V4-C03: the ladder state is glossed on the face with the production display label, never the raw enum.
from engine.cycles import STATE_DISPLAY as LADDER_DISPLAY  # noqa: E402 — engine/cycles.py:653 (label / label_zh per ladder state)
def clock_state(chip_key, pattern_key, en_fmt, zh_fmt, withheld_key):
    return (f'<div class="cyc-clocks-state">{chip(D("cycles", chip_key), "cyc-clocks")}<span class="cyc-clocks-both">{D2("cycles", pattern_key, en_fmt, zh_fmt)}</span></div>'
            f'<p class="cyc-read-body cyc-read-withheld">{D("cycles", withheld_key)}</p>')
def phase_pair(v2):
    return (dict(b_name=DECK["cycles"]["clock_phase_v2"]["en"], phase=PHASE_SHORT[v2]), dict(b_name=DECK["cycles"]["clock_phase_v2"]["zh"], phase=PHASE_FACE_ZH[v2]))
# C07 — legacy-family numerals withheld from the face (kept verbatim in the drawer).
STRIP_EN = (re.compile(r"\s*\(cycle position \d+/100\)"), re.compile(r"\s*Next projected (?:peak|trough): [0-9-]+\."))
STRIP_ZH = (re.compile(r"（周期位置 ?\d+/100）"), re.compile(r"预计下一(?:顶部|底部)：[0-9-]+。"))
def strip_read(s, pats):
    for p in pats: s = p.sub("", s)
    return s.strip()

def asof():
    return (f'<p class="cyc-asof spc-asof-stamp">{icon("i-clock")}'
            f'{D2("components", "asof_pattern", dict(date=META["asOf"], source=SOURCE_LABEL), dict(date=META["asOf"], source=SOURCE_LABEL_ZH))}</p>')

def context_card():
    # SIC-V3-C08: the hero context card carries real content — as-of, generation state (toggled by html[data-state]), hazard epoch.
    s0 = DS["sectors"][0]; sf = META["semantic_families"]
    gen = (f'<span class="cyc-gen-fresh">{D("states","fresh_title")}</span>'
           f'<span class="cyc-gen-incompat">{D("states","incompatible_generation_title")}</span> · {code(sf["schema"])}')
    rows = [(D("cycles","context_asof"), f'{mono(META["asOf"])} · {bi(SOURCE_LABEL, SOURCE_LABEL_ZH)}'),
            (D("cycles","context_generation"), gen),
            (D("cycles","context_hazard_epoch"), code(s0["now"]["hazard"]["epoch"]))]
    return '<dl class="cyc-ctx">' + "".join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in rows) + '</dl>'

def head():
    return f'''<header class="cyc-head">
<div class="cyc-panel">
<h2 class="cyc-h1">{D("cycles","hero_h2")}</h2>
<p class="cyc-tagline">{D("cycles","hero_tagline")}</p>
{asof()}
</div>
<aside class="cyc-panel cyc-basis">
{context_card()}
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
    h = s["now"]["hazard"]; ek = s["estimate_kinds"]; lf = leg_family(s)
    if not lf["hazard_agrees"]:
        # SIC-V4-C02: the leg names another family than the phase clock -> labeled hazard-mismatch state; the ladder stays in the drawer.
        en, zh_ = phase_pair(s["now"]["phase_v2"])
        state = clock_state("clocks_hazard_chip", "hazard_mismatch_pattern",
                            dict(a_name=DECK["cycles"]["clock_hazard"]["en"], leg=DECK["cycles"]["leg_" + h["direction"]]["en"], turn=h["turn_kind"], expected=lf["turn"], **en),
                            dict(a_name=DECK["cycles"]["clock_hazard"]["zh"], leg=DECK["cycles"]["leg_" + h["direction"]]["zh"], turn=zh(h["turn_kind"]), expected=zh(lf["turn"]), **zh_),
                            "hazard_withheld_face")
        return f'''<section class="cyc-sec"><div class="cyc-sec-ttl"><h3>{D("cycles","hazard_label")}</h3></div>{state}</section>'''
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
    r = s["rhythm"]; w = r["window"]; unit = s["kind"]; lf = leg_family(s)
    if not lf["rhythm_agrees"]:
        # SIC-V4-C02: the projection names another turn than the phase clock's family -> labeled rhythm-mismatch state; no Overdue chip, no window on the face.
        en, zh_ = phase_pair(s["now"]["phase_v2"])
        state = clock_state("clocks_rhythm_chip", "rhythm_mismatch_pattern",
                            dict(a_name=DECK["cycles"]["clock_rhythm"]["en"], turn=r["next_turn"], expected=lf["turn"], **en),
                            dict(a_name=DECK["cycles"]["clock_rhythm"]["zh"], turn=zh(r["next_turn"]), expected=zh(lf["turn"]), **zh_),
                            "rhythm_withheld_face")
        return f'''<section class="cyc-sec"><div class="cyc-sec-ttl"><h3>{D("cycles","r6_timing")}</h3></div>
<div class="cyc-rhythm-row">{chip(D("cycles","rhythm_kind"))}</div>{state}</section>'''
    chips = chip(D("cycles","rhythm_kind")) + (chip(D("cycles","overdue_chip"), "cyc-warn") if r.get("overdue") else "")
    win = "".join(f'<div data-central="{str(k == "central").lower()}"><span class="k">{D("cycles", "win_" + k)}</span><span class="v">{esc(w[k])}</span></div>'
                  for k in ("low", "central", "high"))
    fn = D2("cycles", "forecast_footnote",
            dict(turn=r["next_turn"], month=w["central"], low=w["low"], high=w["high"], unit=unit),
            dict(turn=zh(r["next_turn"]), month=w["central"], low=w["low"], high=w["high"], unit=zh(unit)))
    return f'''<section class="cyc-sec"><div class="cyc-sec-ttl"><h3>{D("cycles","r6_timing")}</h3></div>
<div class="cyc-rhythm-row">{chips}</div><div class="cyc-win">{win}</div><p class="cyc-foot">{fn}</p></section>'''

def read(s):
    now = s["now"]
    if family_match(now):
        en = strip_read(now["read"], STRIP_EN)
        # SIC-V3-C06: the production ZH read (engine/sector_cycles.py:97-101) interpolates the English sector name and the
        # Latin abbreviation RS into the zh sentence; the face draws the zh sector name and 相对标普 without the abbreviation.
        # Port note (cycles_ia.md R5): the producer's rs_zh/read_zh should emit this directly.
        zh_ = strip_read(now["read_zh"], STRIP_ZH).replace(s["name"], s["name_zh"]).replace("相对标普RS", "相对标普")
        # SIC-V4-C04: the face says the chip's production phase word, not the engine label_zh the producer interpolates
        # (engine/sector_cycles.py:97-101); SIC-V4-C10: 位于200日均线上方 where the EN says above its 200-day. Port notes: cycles_ia.md R5.
        zh_ = zh_.replace(PHASE_LABEL_ZH[now["phase"]] + "阶段", "处于" + PHASE_FACE_ZH[now["phase"]] + "阶段")
        if "above its 200-day" in en: zh_ = zh_.replace("位于200日均线。", "位于200日均线上方。")
        body = f'<p class="cyc-read-body">{bi(en, zh_)}</p><p class="cyc-foot">{D("cycles","read_provenance")}</p>'
    else:
        # SIC-V3-C03: the legacy read and the phase clock name different families -> labeled Clocks-disagree state naming both.
        lg, v2 = now["phase"], now["phase_v2"]
        # SIC-V4-C03/C04: distinct "Read disagrees" label; both phases in the production ZH vocabulary.
        state = D2("cycles", "clocks_disagree_pattern",
                   dict(a_name=DECK["cycles"]["clock_read"]["en"], a=PHASE_SHORT[lg], b_name=DECK["cycles"]["clock_phase_v2"]["en"], b=PHASE_SHORT[v2]),
                   dict(a_name=DECK["cycles"]["clock_read"]["zh"], a=PHASE_FACE_ZH[lg], b_name=DECK["cycles"]["clock_phase_v2"]["zh"], b=PHASE_FACE_ZH[v2]))
        body = (f'<div class="cyc-clocks-state">{chip(D("cycles","clocks_read_chip"), "cyc-clocks")}<span class="cyc-clocks-both">{state}</span></div>'
                f'<p class="cyc-read-body cyc-read-withheld">{D("cycles","read_withheld_face")}</p>')
    return f'''<section class="cyc-sec"><div class="cyc-sec-ttl"><h3>{D("cycles","r5_read")}</h3></div>{body}</section>'''

def card_prov(s):
    now = s["now"]; h = now["hazard"]; ek = s["estimate_kinds"]; r = s["rhythm"]; pj = s["proj"]; ck = now["clocks"]; a = now.get("phase_v2_age") or {}; lfp = ek.get("live_feature_parity"); lf = leg_family(s); w = r["window"]
    items = [
        (D("cycles","stance_label"), D2("cycles","stance_engine_pattern", dict(stance=now["stance"], tone=now["tone"]), dict(stance=now["stance_zh"], tone=zh(now["tone"]))) + " " + code("resolved_stance · " + DECK["cycles"]["stance_label"]["source"])),
        (code("doctrine_stance"), mono(f'{now.get("doctrine_stance")} · ink {now.get("doctrine_ink")}') + " " + code("engine/cycle_ontology.py DOCTRINE_STANCE :147 · doctrine_for :179 · resolve_state :948")),
        (code("clocks"), mono(f'phase {ck["phase"]} · ladder {ck["ladder"]} · agree {str(ck["agree"]).lower()}')
            + (f' <span class="cyc-prov-read">{bi(now["divergence_note"], now["divergence_note_zh"])}</span>' if now.get("divergence") else "")),
        (code("read_family_match"), mono(f'legacy {now["phase"]} ({PHASE_SHORT.get(now["phase"])}) · phase_v2 {now["phase_v2"]} ({PHASE_SHORT[now["phase_v2"]]}) · match {str(family_match(now)).lower()}')),
        (code("leg_family"), mono(f'phase_v2 {now["phase_v2"]} -> {lf["direction"]} leg toward a {lf["turn"]} · hazard {h["direction"]} / {h["turn_kind"]} agrees {str(lf["hazard_agrees"]).lower()} · rhythm next_turn {r["next_turn"]} · proj nextTurn {pj["nextTurn"]} agrees {str(lf["rhythm_agrees"]).lower()}') + " " + code("build_cycles.py leg_family · engine/cycle_ontology.py:614-629")),
        (code("pos_v2 · phase_v2"), mono(f'{now["pos_v2"]} · {now["phase_v2"]} · source {now["phase_v2_source"]} · age {a.get("status")} · method {a.get("method")}')),
        (code("now.hazard"), mono(f'epoch {h["epoch"]} · direction {h["direction"]} · turn_kind {h["turn_kind"]}')
            + ("".join(" · " + mono(f'{hk} {h[hk]["source"]} {h[hk]["cell_verdict"]}') for hk, _ in HZ) if not h.get("unavailable") else " · " + mono(f'unavailable_reason {h["unavailable_reason"]}'))),
        (code("estimate_kinds"), mono(f'schema {ek["schema"]} · hazard {ek["hazard"]} · model_cell_current_claim {ek.get("model_cell_current_claim")}'
            + (f' · live_feature_parity {lfp["verdict"]} · {len(lfp["failing"])} features' if lfp else ' · live_feature_parity null'))),
        (code("hazard_footnote"), D2("cycles","hazard_footnote", dict(direction=h["direction"]), dict(direction=zh(h["direction"])))),
        (code("rhythm"), mono(f'{r["schema"]} · next_turn {r["next_turn"]} · window {w["low"]} / {w["central"]} / {w["high"]} · {r["status"]} · n_confirmed_halves {r["n_confirmed_halves"]} · elapsed_half_cycle_ratio {r["elapsed_half_cycle_ratio"]} · overdue {str(r.get("overdue")).lower()}')),
        (D("cycles","proj_label"), mono(f'{pj["nextTurn"]} · central {pj["central"]} · low {pj["low"]} · high {pj["high"]} · overdue_frac {pj["overdue_frac"]} · period_yrs median {pj["period_yrs"]["median"]}') + " " + code(DECK["cycles"]["proj_label"]["source"].split(";")[0])),
        (D("cycles","read_legacy_withheld"), f'<span class="cyc-prov-read">{bi(now["read"], now["read_zh"])}</span>'),
    ]
    return prov(items)

def stance_row(now):
    # SIC-V3-C01/C02: the chip is the producer-stamped doctrine stance, labeled as the engine's mapping by its source eyebrow.
    ds = now.get("doctrine_stance")
    if ds:
        chipv = chip(bi(now["doctrine_stance_en"], now["doctrine_stance_zh"]), "cyc-stance", stance=ds, ink=now.get("doctrine_ink") or "")
    else:
        chipv = f'<span class="cyc-stance-na">{D("cycles","stance_unavailable")}</span>'
    row = (f'<div class="cyc-stance-row"><span class="cyc-stance-ttl">{D("components","stance_title")}</span>{chipv}'
           f'<span class="cyc-stance-src">{D("cycles","stance_source_eyebrow")}</span>')
    note = ""
    if now.get("divergence"):
        # SIC-V3-C01/C03: the amber chip names the clocks; the ladder state and the engine note (stance words) stay drawer-only.
        # SIC-V4-C03/C04 (wave 4): distinct "Ladder disagrees" label; the ladder state glossed with its production display label.
        row += chip(D("cycles","clocks_ladder_chip"), "cyc-clocks"); v2 = now["phase_v2"]; ld = LADDER_DISPLAY[now["clocks"]["ladder"]]
        note = '<p class="cyc-div-note">' + D2("cycles", "ladder_state_pattern",
            dict(phase_name=DECK["cycles"]["clock_phase_v2"]["en"], phase=PHASE_SHORT[v2], ladder_name=DECK["cycles"]["clock_ladder"]["en"], ladder=ld["label"].lower()),
            dict(phase_name=DECK["cycles"]["clock_phase_v2"]["zh"], phase=PHASE_FACE_ZH[v2], ladder_name=DECK["cycles"]["clock_ladder"]["zh"], ladder=ld["label_zh"])) + '</p>'
    return row + "</div>" + note

def card(s):
    now = s["now"]; phase = now["phase_v2"]; pos = now["pos_v2"]
    stance = stance_row(now); note = ""
    return f'''<article class="cyc-panel cyc-card" data-sector="{esc(s["id"])}">
<div class="cyc-card-head">
<div class="cyc-id"><h2>{bi(s["name"], s["name_zh"])}</h2><span class="cyc-tk">{esc(s["ticker"])}</span>
<span class="cyc-pos"><b>{pos:.0f}</b>/100<span class="b">{D("cycles","mode_osc_chip")}</span></span>
<span class="cyc-grp">{bi(s["group"], s["group_zh"])} · {D2("cycles","kind_basis_pattern", dict(kind=s["kind"], basis=s["basis"]), dict(kind=zh(s["kind"]), basis=zh(s["basis"])))}</span></div>
<div class="cyc-chips">{chip(D("cycles", PHASE_CHIP[phase]), "spc-phase-chip", phase=phase.lower())}</div>
{stance}{note}
{age_line(now)}
</div>
{hazard(s)}{rhythm(s)}{read(s)}
{card_prov(s)}
</article>'''

def methods():
    lp = META["live_hazard_parity"]; s0 = DS["sectors"][0]
    items = [
        ("now.hazard", D("cycles","hazard_label"), chip(D("cycles","hazard_parity_chip"), "cyc-warn"),
         mono(f'live_hazard_parity {lp["verdict"]} · {len(lp["failing"])} features · measured_on {lp["measured_on"][:8]}')),
        ("rhythm", D("cycles","rhythm_kind_body"), "", mono(f'rhythm_version {META["rhythm_version"]} · {s0["rhythm"]["schema"]}')),
        ("size_mult", D("cycles","sizing_inert"), "", SRC("cycles","sizing_inert")),
        ("lead_lag", D("cycles","leadlag_stop"), "", SRC("cycles","leadlag_stop")),
    ]
    grid = "".join(f'<div class="cyc-method"><p>{body}</p>{chips}</div>' for _, body, chips, _ in items)
    drawer = prov([(code(k), src) for k, _, _, src in items])
    return f'''<section class="cyc-panel cyc-methods"><h2 class="cyc-sec-h2">{D("cycles","methods_h2")}</h2><div class="cyc-method-grid">{grid}</div>{drawer}</section>'''

def grader():
    # SIC-V3-C08: the eyebrow promises no rate; no label implies a measured value while no number is drawn; the Neutral-included caption is labeled a definition.
    return f'''<section class="cyc-panel cyc-grader"><p class="cyc-eyebrow">{D("cycles","r8_grader_eyebrow")}</p>
<h2>{D("cycles","grader_face_h2")}</h2>
<p class="spc-grader-caption"><span class="cyc-def-lbl">{D("components","definition_label")}</span> · {D("components","grader_caption")}</p>
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

def fixture_prior():
    # SIC-V3-C17: exactly one labeled FIXTURE state card, outside any live sector card, showing the KM PRIOR cell in producer shape.
    fx = DS["_fixtures"]["prior_cell"]; h = fx["hazard"]
    heads = "".join(f'<span class="spc-hz-head">{D("cycles", k)}</span>' for _, k in HZ)
    rowlab = f'<span class="spc-hz-rowlab">{D2("cycles","hazard_row_pattern", dict(direction=h["direction"], turn=h["turn_kind"]), dict(direction=zh(h["direction"]), turn=zh(h["turn_kind"])))}</span>'
    cells = ""
    for hk, _ in HZ:
        c = h[hk]; src = c["source"].lower()
        cells += (f'<span class="spc-hz-cell" data-source="{src}"><span class="spc-hz-val">{c["p"]*100:.0f}%</span>'
                  f'<span class="spc-model-prior-badge" data-source="{src}">{D("components", "badge_model" if src == "model" else "badge_prior")}</span></span>')
    drawer = prov([(code("_fixtures.prior_cell.hazard"), mono(f'epoch {h["epoch"]} · direction {h["direction"]} · turn_kind {h["turn_kind"]}')
                        + "".join(" · " + mono(f'{hk} {h[hk]["source"]} {h[hk]["cell_verdict"]} p {h[hk]["p"]}') for hk, _ in HZ)),
                   (code("shape_source"), code(fx["shape_source"])), (code("note"), esc(fx["note"]))], hint=False)
    return f'''<section class="cyc-panel cyc-fixture-card" data-fixture="prior_cell" aria-labelledby="cyc-fx-h2">
<div class="cyc-chips">{chip(D("components","fixture_chip"), "cyc-fixture-chip")}</div>
<h2 id="cyc-fx-h2" class="cyc-sec-h2">{D("cycles","fixture_prior_h2")}</h2>
<p class="cyc-fx-id"><span class="cyc-fx-name">{bi(fx["name"], fx["name_zh"])}</span><span class="cyc-tk">{esc(fx["ticker"])}</span></p>
<p class="cyc-fx-body">{D("cycles","fixture_prior_body")}</p>
<div class="spc-hazard-ladder" role="group"><span class="spc-hz-head"></span>{heads}{rowlab}{cells}<span class="spc-hz-note">{D("cycles","hazard_face_note")}</span></div>
{drawer}</section>'''

def fixture_null():
    # SIC-V4-C10: the second labeled FIXTURE card — a record whose producer stamped no doctrine stance (SIC-V3-C02 rendering:
    # the muted "Stance unavailable" line, no chip). stamp_doctrine.py writes the null fields for a null now.stance.
    fx = DS["_fixtures"]["null_stance"]; now = fx["now"]
    assert now.get("stance") is None and now.get("doctrine_stance") is None, fx
    drawer = prov([(code("_fixtures.null_stance.now"), mono(f'stance {now.get("stance")} · doctrine_stance {now.get("doctrine_stance")} · doctrine_ink {now.get("doctrine_ink")} · tone {now.get("tone")}')),
                   (code("shape_source"), code(fx["shape_source"])), (code("note"), esc(fx["note"]))], hint=False)
    return f'''<section class="cyc-panel cyc-fixture-card" data-fixture="null_stance" aria-labelledby="cyc-fx2-h2">
<div class="cyc-chips">{chip(D("components","fixture_chip"), "cyc-fixture-chip")}</div>
<h2 id="cyc-fx2-h2" class="cyc-sec-h2">{D("cycles","fixture_null_h2")}</h2>
<p class="cyc-fx-id"><span class="cyc-fx-name">{bi(fx["name"], fx["name_zh"])}</span><span class="cyc-tk">{esc(fx["ticker"])}</span></p>
<p class="cyc-fx-body">{D("cycles","fixture_null_body")}</p>
{stance_row(now)}
{drawer}</section>'''

def desk(cards):
    # SIC-V3-C09 (board 40; `hidden` unless ?desk=composite): the production chart capture labeled with render source, sha and
    # both as-of dates on the face, beside the specimen correction cards. No desk silently mixes two as-of dates.
    fmt = dict(page=code(PC["page"]), sha=code(PC["sha"]), capture=code("chrome-headless-1x"), asof_prod=PC["asof_prod"], asof_ds=META["asOf"], asof_brief=BRIEF_ASOF)  # identifiers as <code> (SIC-V4-C05)
    cap = DH("cycles", "capture_body", **fmt); alt = DECK["cycles"]["capture_alt"]["en"].format(captured_at=PC["captured_at"])
    drawer = prov([(code("prod_capture.json"), mono(f'{PC["file"]} · {PC["page"]} @ {PC["sha"]} · asof_prod {PC["asof_prod"]} · captured_at {PC["captured_at"]} · px {PC["px"][0]}×{PC["px"][1]} · theme {PC["theme"]}')),
                   (code("specimen"), mono(f'meta.asOf {META["asOf"]} · brief as_of {BRIEF_ASOF}'))], hint=False)
    return f'''<section class="cyc-panel cyc-desk" hidden aria-labelledby="cyc-desk-h2">
<h2 id="cyc-desk-h2" class="cyc-sec-h2">{D("cycles","desk_h2")}</h2>
<div class="cyc-desk-grid">
<figure class="cyc-capture"><div class="cyc-chips">{chip(D("cycles","capture_label"), "cyc-capture-chip")}{chip(D("cycles","capture_theme_chip"), "cyc-capture-chip")}{chip(D("cycles","context_asof") + " " + mono(PC["asof_prod"]))}</div>
<img src="{esc(PC["file"])}" width="{PC["px"][0]}" height="{PC["px"][1]}" alt="{esc(alt)}">
<figcaption>{cap}<span class="cyc-desk-clock">{DH("cycles","desk_clock_note", legacy=code("now.phase"), v2=code("phase_v2"))}</span></figcaption></figure>
<div class="cyc-desk-cards"><div class="cyc-chips">{chip(D("cycles","context_asof") + " " + mono(META["asOf"]))}</div><div class="cyc-cards">{cards}</div></div>
</div>
<p class="cyc-foot">{D("cycles","desk_note")}</p>{drawer}</section>'''

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
<title>Sector Cycles — corrections specimen (RIG boards 28–31, 34–36, 39–41)</title>
<script>(function(){{var q=new URLSearchParams(location.search),d=document.documentElement;
var t=q.get("theme")||"dark",l=q.get("lang")||"en",s=q.get("state");
d.setAttribute("data-theme",t);d.setAttribute("data-lang",l);d.setAttribute("lang",l==="zh"?"zh-Hans":"en");
if(s)d.setAttribute("data-state",s);var dk=q.get("desk");if(dk)d.setAttribute("data-desk",dk);}})();</script>
<link rel="stylesheet" href="../../../templates/theme.css">
<link rel="stylesheet" href="../../../templates/navigation-refresh.css">
<link rel="stylesheet" href="../components/si_shell.css">
<link rel="stylesheet" href="../components/components.css">
<link rel="stylesheet" href="cycles.css">
</head>
<body class="macro-desk page-baskets">
{shell_nav()}
<main class="cyc si-shell" id="main">{page_header(asof())}{workflow_nav("cycles")}{SPRITE}{head()}<div class="cyc-cards">{CARDS}</div>{desk(CARDS)}<div class="cyc-fixtures">{fixture_prior()}{fixture_null()}</div>{methods()}<div class="cyc-two">{grader()}{events()}</div>{metadata()}</main>
<script>(function(){{var d=document.documentElement,w=innerWidth,o=[];
var dk=document.querySelector(".cyc-desk");if(dk&&d.getAttribute("data-desk")==="composite")dk.removeAttribute("hidden");
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
        n = s["now"]; print(f'  {s["ticker"]}: engine {n["stance"]} -> stamped doctrine {n.get("doctrine_stance")} ({n.get("doctrine_stance_en")}) ink {n.get("doctrine_ink")} · phase {n["phase"]}/{n["phase_v2"]} · family_match {family_match(n)} · divergence {n.get("divergence")}')
        print("     face read:" if family_match(n) else "     read WITHHELD (Clocks disagree):", strip_read(n["read"], STRIP_EN)[:100])
    fm = {s["ticker"]: family_match(s["now"]) for s in DS["sectors"]}
    assert fm["XLC"] is False and fm["XLF"] is True, fm  # SIC-V3-C03 demonstration cells
    lf = {s["ticker"]: leg_family(s) for s in DS["sectors"]}
    for t, v in lf.items(): print(f'     {t}: leg_family hazard_agrees {v["hazard_agrees"]} · rhythm_agrees {v["rhythm_agrees"]} (phase_v2 family -> {v["direction"]} / {v["turn"]})')
    assert lf["XLF"]["hazard_agrees"] and not lf["XLC"]["hazard_agrees"] and not any(v["rhythm_agrees"] for v in lf.values()), lf  # SIC-V4-C02 demonstration cells
