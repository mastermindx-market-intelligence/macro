"""#10534 projected-month parity between legacy sector_cycles.js and the SC_FACE port (A2_D29).

The legacy projPast/cardNextTxt/detailNextLabel block stays byte-identical to the wave BASE, the face port
(templates/sector_cycles_face.js, called as SC_FACE.projPast(p, {today: t})) returns the same boolean on a
dense calendar grid, and every next-turn string the face emits matches the legacy renderer. Both sides run in
a bare node vm sandbox; the legacy functions and their L/curLang/MONTHS helpers are extracted by text.
"""
from __future__ import annotations

import calendar
import copy
import datetime as dt
import hashlib
import html
import json
import random
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FACE = ROOT / "templates" / "sector_cycles_face.js"
BASE_JS = ROOT / "templates" / "sector_cycles.js"
DS = ROOT / "design_refs" / "sector-paper-20261021" / "cycles_repair" / "example_dataset.json"

# sha256 of `  function projPast(p) {` .. the closing `  }` of detailNextLabel (plus a trailing newline), taken
# from `git show 098637a4:templates/sector_cycles.js` (A2 BASE, lines 122-167).
BASE_BLOCK_SHA256 = "f5d42c8f7b08e82119d4540aa39e622e22295fa34a1fe907be044b170e4e4985"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run the projPast parity seam")

LEGACY_SRC = BASE_JS.read_text(encoding="utf-8")
FACE_SRC = FACE.read_text(encoding="utf-8")


def _fn_block(src: str, head: str, last_head: str | None = None) -> str:
    lines = src.split("\n")
    s = lines.index(head)
    d = s if last_head is None else next(i for i in range(s, len(lines)) if lines[i].startswith(last_head))
    e = next(i for i in range(d + 1, len(lines)) if lines[i] == "  }")
    return "\n".join(lines[s:e + 1]) + "\n"


def _line(src: str, pattern: str) -> str:
    m = re.search(pattern, src, re.M)
    assert m, pattern
    return m.group(0) + "\n"


LEGACY_BLOCK = _fn_block(LEGACY_SRC, "  function projPast(p) {", "  function detailNextLabel(p) {")
LEGACY_JS = (_line(LEGACY_SRC, r"^  var MONTHS = \[.*\];$") + _line(LEGACY_SRC, r"^  function curLang\(\) \{.*\}$")
             + _line(LEGACY_SRC, r"^  function L\(en, zh\) \{.*\}$") + _fn_block(LEGACY_SRC, "  function fmtMon(t) {")
             + LEGACY_BLOCK)
FACE_PORT = _fn_block(FACE_SRC, "  function projPast(p, ctx) {")

_RUNNER = r"""
const fs = require('fs'), vm = require('vm');
const job = JSON.parse(fs.readFileSync(0, 'utf8'));
const lg = { LANG: 'en', META: undefined };
lg.document = { documentElement: { getAttribute: function () { return lg.LANG; } } };
vm.createContext(lg);
vm.runInContext(job.legacy + '\nthis.projPast = projPast; this.cardNextTxt = cardNextTxt; this.detailNextLabel = detailNextLabel;', lg);
const sb = { window: {} }; vm.createContext(sb); vm.runInContext(fs.readFileSync(job.face, 'utf8'), sb);
const F = sb.window.SC_FACE;
function legacyPast(p, meta) { lg.META = meta; return lg.projPast(p); }
function legacyText(p, meta, lang) { lg.META = meta; lg.LANG = lang; return [lg.cardNextTxt(p), lg.detailNextLabel(p)]; }
function cases(port, onlyOverdue) {
  const metas = [[undefined, undefined], [{}, {}], [{ today: NaN }, { today: NaN }], [{ today: '2026.5' }, { today: '2026.5' }]];
  const ovs = onlyOverdue ? [true] : [true, false, undefined];
  let n = 0, nTrue = 0, nBad = 0; const bad = [];
  function one(p, meta, c) {
    const a = legacyPast(p, meta), b = port(p, c); n++; if (a) nTrue++;
    if (a !== b) nBad++;
    if (a !== b && bad.length < 20) bad.push({ p: p, today: c && c.today, legacy: a, face: b });
  }
  for (const t of job.grid) for (const central of job.centrals) for (const ov of ovs) for (const nt of ['peak', 'trough']) {
    const p = { central: central, nextTurn: nt }; if (ov !== undefined) p.overdue = ov;
    one(p, { today: t }, { today: t });
  }
  for (const m of metas) for (const central of job.centrals.slice(0, 6)) one({ central: central, overdue: true, nextTurn: 'peak' }, m[0], m[1]);
  for (const t of job.grid.slice(0, 40)) one(null, { today: t }, { today: t });
  return { n: n, nTrue: nTrue, nBad: nBad, bad: bad };
}
const out = {};
if (job.mode === 'grid') out.grid = cases(function (p, c) { return F.projPast(p, c); }, false);
if (job.mode === 'mutants') {
  out.mutants = job.mutants.map(function (srcText) {
    const ms = {}; vm.createContext(ms); vm.runInContext(srcText + '\nthis.port = projPast;', ms);
    return cases(ms.port, true);
  });
}
if (job.mode === 'text') {
  out.text = job.cases.map(function (c) {
    const meta = { today: c.today }, ctx = { lang: c.lang, today: c.today, meta: job.meta, asof: job.meta.asOf };
    return { past: legacyPast(c.rec.proj, meta), en: legacyText(c.rec.proj, meta, 'en'), zh: legacyText(c.rec.proj, meta, 'zh'),
             agrees: F.legFamily(c.rec).rhythmAgrees, rhythm: F.rhythm(c.rec, ctx), card: F.card(c.rec, ctx) };
  });
}
process.stdout.write(JSON.stringify(out));
"""


def _node(job: dict) -> dict:
    job = dict(job, legacy=LEGACY_JS, face=str(FACE))
    proc = subprocess.run(["node", "-e", _RUNNER], input=json.dumps(job), capture_output=True, text=True, cwd=str(ROOT))
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


def _yf(d: dt.date) -> float:
    # META.today producer: engine/sector_cycles.py `round(_yf(last_ts), 3)`, _yf = year + (dayofyear - 1) / 365.25
    return round(d.year + (d.timetuple().tm_yday - 1) / 365.25, 3)


def _grid() -> list[float]:
    ts, d = [], dt.date(2025, 1, 1)
    while d <= dt.date(2028, 12, 31):
        ts.append(_yf(d))
        d += dt.timedelta(days=1)
    for y in range(2025, 2029):
        for m in range(1, 13):
            for day in (1, calendar.monthrange(y, m)[1]):
                t = _yf(dt.date(y, m, day))
                ts += [round(t - 0.001, 3), round(t + 0.001, 3)]
    return ts


def _centrals() -> list[str]:
    out, y, m = [], 2024, 11
    while (y, m) <= (2029, 2):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out + ["2026", "x-13", "2026-00", "2026-13", ""]


GRID, CENTRALS = _grid(), _centrals()
MALFORMED = {"2026", "x-13", "2026-00", "2026-13", ""}


def test_legacy_block_byte_identical():
    assert hashlib.sha256(LEGACY_BLOCK.encode("utf-8")).hexdigest() == BASE_BLOCK_SHA256
    assert "\\u2014" in LEGACY_BLOCK and "was proj. " in LEGACY_BLOCK


def test_port_boolean_parity():
    assert _yf(dt.date(2028, 2, 29)) in GRID
    res = _node({"mode": "grid", "grid": GRID, "centrals": CENTRALS})["grid"]
    expected = len(GRID) * len(CENTRALS) * 3 * 2 + 4 * 6 + 40
    print(f"projPast parity: {res['n']} cases, {res['nTrue']} legacy-past, {len(res['bad'])} mismatches")
    assert res["n"] == expected
    assert res["bad"] == []
    assert 0 < res["nTrue"] < res["n"]


def test_port_mutation_controls():
    assert FACE_PORT.count(") < (") == 1 and FACE_PORT.count(" + 0.25") == 1
    mutants = [FACE_PORT, FACE_PORT.replace(") < (", ") <= ("), FACE_PORT.replace(" + 0.25", "")]
    res = _node({"mode": "mutants", "mutants": mutants, "grid": GRID, "centrals": CENTRALS})["mutants"]
    print(f"projPast mutation kills: `<=` {res[1]['nBad']} of {res[1]['n']}, no-nudge {res[2]['nBad']} of {res[2]['n']}")
    assert res[0]["bad"] == [], "the extracted port must agree with legacy before mutation"
    assert res[1]["bad"], "`) < (` -> `) <= (` survived the grid"
    assert res[2]["bad"], "removing `+ 0.25` survived the grid"


def _text_cases() -> tuple[list[dict], dict]:
    base = json.loads(DS.read_text(encoding="utf-8"))
    xlf = next(s for s in base["sectors"] if s["id"] == "xlf")
    rnd, out = random.Random(7646), []
    days = GRID[:1461]
    for i in range(640):
        t = rnd.choice(days)
        yr, frac = int(t), t - int(t)
        mo = min(12, int(frac * 12.0) + 1)
        k = yr * 12 + mo - 1 + rnd.choice([-4, -2, -1, -1, 0, 0, 1, 2, 4])
        central = f"{k // 12}-{k % 12 + 1:02d}" if i % 40 else rnd.choice(sorted(MALFORMED - {""}))
        p = {"central": central, "nextTurn": rnd.choice(["peak", "trough"]), "low": central, "high": central}
        ov = rnd.choice([True, True, True, False, None])
        if ov is not None:
            p["overdue"] = ov
        r = copy.deepcopy(xlf)
        r["now"]["phase_v2"] = rnd.choice(["Expansion", "Recovery", "Downturn", "Trough", None])
        r["rhythm"] = {"kind": "descriptive_rhythm", "overdue": p.get("overdue"), "next_turn": p["nextTurn"],
                       "window": {"low": central, "central": central, "high": central}}
        r["proj"] = p
        out.append({"rec": r, "today": t, "lang": "zh" if i % 2 else "en"})
    return out, base["meta"]


def _mon(central: str) -> tuple[str, str]:
    y, m = central.split("-")
    return calendar.month_abbr[int(m)] + " ’" + y[2:], f"{y}年{int(m)}月"


def test_port_text_parity():
    cases, meta = _text_cases()
    res = _node({"mode": "text", "cases": cases, "meta": meta})["text"]
    counted = excluded = n_past = n_fresh = 0
    for c, r in zip(cases, res):
        p = c["rec"]["proj"]
        out = html.unescape(r["rhythm"] + r["card"])
        if r["agrees"] is False:
            excluded += 1
            assert r["rhythm"] == ""
            continue
        counted += 1
        en_card, zh_card = r["en"][0], r["zh"][0]
        if r["past"]:
            n_past += 1
            mon_en, mon_zh = _mon(p["central"])
            for frag in ("Next ▲ " + mon_en, "Next ▼ " + mon_en, "下次▲ " + mon_zh,
                         "下次▼ " + mon_zh):
                assert frag not in out, (p, c["today"], frag)
            assert out.count("was proj.") == out.count(en_card) >= 2, (p, c["today"])
            assert out.count("原预计") == out.count(zh_card) >= 2, (p, c["today"])
            assert r["en"][1] in ("Peak was projected", "Trough was projected")
            assert r["zh"][1] in ("顶部原预计", "底部原预计")
            assert 'data-past="true"' in r["rhythm"]
        else:
            n_fresh += 1
            for frag in ("— elapsed", "— 已过", "was proj.", "原预计"):
                assert frag not in out, (p, c["today"], frag)
            assert 'data-past="false"' in r["rhythm"]
            if p["central"] not in MALFORMED:
                assert en_card in out and zh_card in out, (p, c["today"], en_card, zh_card)
    print(f"projPast text parity: {counted} counted ({n_past} past, {n_fresh} fresh), {excluded} excluded (rhythmAgrees false)")
    assert counted >= 200 and n_past >= 60 and n_fresh >= 60


def test_no_wallclock_in_face():
    assert "Date.now(" not in FACE_SRC
    assert not re.search(r"new Date\(\s*\)", FACE_SRC)
