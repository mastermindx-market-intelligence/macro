"""Sector Central Cycles view: shell, router and baked-context invariants (L1, #7646).

The cycle map left the market-map view for a seventh workspace view, ``cycles``. That
move is cheap to make and easy to break in ways no other test notices:

* **Bookmarks.** ``#sc-cyclemap`` and ``#dossier`` were map-view deep links. They are
  re-homed ahead of LEGACY_ANCHORS, which must stay byte-identical for every other
  bookmark — so the table is hashed here, not just re-read.
* **The router/renderer seam.** ``#cycles/f=&g=&m=&w=&s=`` belongs to the router; the
  state belongs to sector_cycles.js. The query is parked on ``window`` *before* the
  ``si:cycles-state`` event, so a renderer that boots after the event still reads it.
* **Typed context.** The as-of, generation and coverage line is baked at build time.
  Unknown renders as the typed "— unavailable", never as a blank or a zero; a missing
  sector is named, not silently counted.
* **No sizing language.** Sector Central drops the shared board's HALF SIZE chip (D1b)
  and states the grader's hit rate as "not a win rate" (D3).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_sector_central import cycles_context, drop_sizing_chips  # noqa: E402

TPL = ROOT / "templates"
PAGE = TPL / "sector_central.html.j2"
ROUTER = TPL / "si_workspace.js"
SPDR = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _router() -> str:
    return ROUTER.read_text(encoding="utf-8")


def _views(src: str) -> list[tuple[str, str]]:
    parts = re.split(r'<section class="si-view[^"]*" data-view="([a-z]+)"', src)
    return list(zip(parts[1::2], parts[2::2]))


def _view_body(src: str, view: str) -> str:
    return "".join(b for n, b in _views(src) if n == view)


def _render(**ctx) -> str:
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(TPL)), autoescape=False)
    env.globals.update(
        td=lambda en: en, tr=lambda en: en,
        t=lambda en, zh="": f'<span class="l-en">{en}</span><span class="l-zh">{zh or en}</span>',
    )
    return env.get_template("sector_central.html.j2").render(basket_member_syms=["SPY"], **ctx)


def _cycles_line(html: str) -> str:
    return _view_body(html, "cycles").split('id="sc-cyclemap"', 1)[0]


# ────────────────────────────────────────────────────────────── shell

def test_template_stays_line_neutral() -> None:
    assert len(_page().splitlines()) == 4184, "sector_central.html.j2 must stay 4184 lines"


def test_workflow_rail_links_dossier_and_cycles() -> None:
    s = _page()
    assert ('<a class="si-workflow-link" data-si-workflow="dossier" href="#dossier">'
            "{{ t('Dossier', '档案') }}</a>") in s
    assert ('<a class="si-workflow-link" data-si-workflow="cycles" href="#cycles">'
            "{{ t('Cycles', '周期') }}</a>") in s


def test_cycle_map_and_chart_live_in_the_cycles_view() -> None:
    s = _page()
    cycles, mapped = _view_body(s, "cycles"), _view_body(s, "map")
    for organ in ('id="sc-cyclemap"', 'id="sc-chart"', 'id="si-cycles-h"', 'id="si-cycles-asof"'):
        assert organ in cycles, f"{organ} must sit in the Cycles view"
        assert organ not in mapped, f"{organ} still inside the map view"
    for organ in ('id="sc-board"', 'id="board"', 'id="si-map"', 'id="rotmap-section"'):
        assert organ in mapped, f"{organ} left the map view"


def test_split_map_view_keeps_balanced_sections() -> None:
    s = _page()
    names = [n for n, _ in _views(s)]
    assert names.count("cycles") == 1 and names.count("map") == 2
    assert names.index("map") < names.index("cycles") < len(names) - 1 - names[::-1].index("map")
    for name, body in _views(s):
        # each body runs to the next si-view opener: it closes its own section once more
        # than it opens nested ones, or a view has swallowed (or spilled into) its sibling
        assert body.count("</section>") == body.count("<section") + 1, name
    # a full walk, not just per-view counts: depth never dips below zero and every
    # si-view opens at the page's own section depth, so no view nests inside another
    depth, view_depths = 0, set()
    for m in re.finditer(r"<section\b[^>]*>|</section>", s):
        tag = m.group(0)
        if tag == "</section>":
            depth -= 1
            assert depth >= 0, f"unbalanced </section> at offset {m.start()}"
        else:
            if 'class="si-view' in tag:
                view_depths.add(depth)
            depth += 1
    assert depth == 0 and len(view_depths) == 1, (depth, view_depths)
    assert s.count('id="si-map"') == 1, "the map anchor must stay unique"
    assert s.count('id="sc-asof"') == 1, "the cycle clock's own as-of must stay single"


# ────────────────────────────────────────────────────────────── router

def test_legacy_anchor_table_is_byte_identical() -> None:
    lines = _router().split("\n")
    block = "\n".join(lines[51:76])
    assert block.startswith("var LEGACY_ANCHORS={") and block.endswith("};")
    assert hashlib.sha256(block.encode("utf-8")).hexdigest() == (
        "cd7c08ead0e2ff339f068c58b593b2976f7236c1903a5eb9538bfe592d79edd4")


def test_cycles_is_a_lazy_view_with_the_contract_inject_order() -> None:
    src = _router()
    assert "var VIEWS=['overview','map','moving','money','explore','confluence','cycles'];" in src
    assert "cycles:['@cycles']" in src
    body = src.split("function loadCycles(){", 1)[1].split("\n}", 1)[0]
    files = re.findall(r"'(sector_cycles[a-z_]*\.js|mm_charts\.js)'", body.split("var files=", 1)[1])
    assert files == ["sector_cycles_data.js", "mm_charts.js", "sector_cycles_states.js",
                     "sector_cycles_face.js", "sector_cycles_compare.js",
                     "sector_cycles_platform.js", "sector_cycles.js"]


_HARNESS = textwrap.dedent("""\
    const fs = require('fs');
    const vm = require('vm');
    const src = fs.readFileSync('templates/si_workspace.js', 'utf8');
    const patched = src.replace(
      'function activate(view,target,user){',
      'function activate(view,target,user){globalThis.__lastActivate=[view,target];'
    );
    if (patched === src) throw new Error('activate() signature drifted; capture not injected');
    const events = [], replaced = [], hrefs = [], scripts = [];
    const stub = () => ({
      getAttribute: () => null, setAttribute: () => {}, removeAttribute: () => {},
      querySelectorAll: () => [], querySelector: () => null,
      appendChild: () => {}, scrollIntoView: () => {}, focus: () => {},
      classList: { toggle: () => {}, add: () => {}, remove: () => {}, contains: () => false },
    });
    const dossier = { setAttribute: (k, v) => { if (k === 'href') hrefs.push(v); } };
    const ctx = {
      document: {
        documentElement: { getAttribute: () => null },
        querySelectorAll: () => [],
        querySelector: (q) => q === '[data-si-workflow="dossier"]' ? dossier : null,
        getElementById: () => stub(),
        title: 'Test',
        dispatchEvent: (e) => { events.push([e.type, ctx.__siCyclesPending]); },
        addEventListener: () => {},
        createElement: () => ({
          setAttribute: () => {}, addEventListener: () => {},
          appendChild: () => {}, async: false, getAttribute: () => null,
          hasAttribute: () => false,
        }),
        getElementsByTagName: () => [],
        head: { appendChild: (s) => { scripts.push(s.src); } },
      },
      history: { replaceState: (a, b, u) => { replaced.push(u); } },
      location: { hash: '' },
      console, setTimeout, clearTimeout,
      requestAnimationFrame: () => 0, scrollTo: () => {}, scrollY: 0,
      addEventListener: () => {},
      dispatchEvent: () => {},
      CustomEvent: function (type, init) { return { type: type, detail: init && init.detail }; },
      Event: function (type) { return { type: type }; },
    };
    vm.createContext(ctx);
    ctx.window = ctx;
    vm.runInContext(patched, ctx);
    const out = { routes: {}, events: null, hrefs: null, replaced: null, scripts: null };
    for (const h of process.argv.slice(1)) {
      ctx.__lastActivate = null;
      ctx.location.hash = h;
      ctx.__siRoute();
      out.routes[h] = ctx.__lastActivate;
    }
    out.events = events.filter((e) => e[0] === 'si:cycles-state');
    replaced.length = 0;
    ctx.__siCyclesHash('f=sectors&s=XLK');
    ctx.__siCyclesHash('f=themes&s=QQQ');
    ctx.__siCyclesHash('');
    out.hrefs = hrefs; out.replaced = replaced; out.scripts = scripts;
    process.stdout.write(JSON.stringify(out));
""")


def _replay(*hashes: str) -> dict:
    run = subprocess.run(["node", "-e", _HARNESS, *hashes],
                         capture_output=True, text=True, cwd=str(ROOT))
    assert run.returncode == 0, f"node replay failed: {run.stderr}"
    return json.loads(run.stdout)


def test_rehomed_bookmarks_open_the_cycles_view() -> None:
    out = _replay("#sc-cyclemap", "#dossier", "#cycles", "#map", "#board")
    r = out["routes"]
    assert r["#sc-cyclemap"] == ["cycles", "sc-cyclemap"]
    assert r["#dossier"] == ["cycles", "sc-cyclemap"]
    assert r["#cycles"] == ["cycles", None]
    assert r["#map"] == ["map", None]
    assert r["#board"][0] == "map", "the board bookmark must stay on the map view"


def test_cycles_query_is_parked_before_the_state_event() -> None:
    out = _replay("#cycles/f=sectors&s=XLK")
    assert out["routes"]["#cycles/f=sectors&s=XLK"] == ["cycles", None]
    # the renderer may boot after the event: the query must already be on window
    assert out["events"] == [["si:cycles-state", "f=sectors&s=XLK"]]
    # first activation lazily loads the Cycles bundle in contract order, data first
    names = [u.split("?")[0] for u in out["scripts"]]
    assert names[0] == "sector_cycles_data.js" and names[-1] == "sector_cycles.js"


def test_cycles_query_reaches_the_renderer_still_encoded() -> None:
    """The renderer decodes each value once (_parseQs). The router must hand it the
    query as written: decoding the whole hash first turned an id holding an encoded
    '&' or ',' into two parameters or a split list."""
    out = _replay("#cycles/f=sectors&s=A%26B", "#cycles/m=X%2CY")
    assert out["routes"]["#cycles/f=sectors&s=A%26B"] == ["cycles", None]
    assert out["events"] == [["si:cycles-state", "f=sectors&s=A%26B"],
                             ["si:cycles-state", "m=X%2CY"]]


def test_cycles_hash_writeback_points_dossier_at_the_sector_page() -> None:
    out = _replay()
    assert out["replaced"] == ["#cycles/f=sectors&s=XLK", "#cycles/f=themes&s=QQQ", "#cycles/"]
    # an SPDR sector opens its own dossier's cycle panel; anything else stays in-page
    assert out["hrefs"] == ["sectors/XLK.html#cycle", "#dossier", "#dossier"]


# ────────────────────────────────────────────────────────────── baked context

def _site(tmp_path: Path, tickers, asof="2026-10-30") -> Path:
    d = tmp_path / "sectordata"
    d.mkdir(parents=True)
    payload = {"meta": {"asOf": asof},
               "sectors": [{"ticker": t, "osc": [50.0, 52.0]} for t in tickers]}
    (d / "sector_cycles.json").write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


def test_coverage_names_the_missing_sector(tmp_path: Path) -> None:
    ctx = cycles_context(_site(tmp_path, [t for t in SPDR if t != "XLU"]), {"as_of": "2026-10-30"})
    assert ctx["asof"] == "2026-10-30"
    assert ctx["coverage"] == {"measured": 10, "expected": 11, "missing": ["XLU"]}
    assert ctx["generation"]["status"] == "aligned"
    line = _cycles_line(_render(cycles_ctx=ctx))
    assert '<time datetime="2026-10-30">2026-10-30</time>' in line, "as-of must be baked"
    assert "Partial coverage" in line and "覆盖不完整" in line
    assert "10 / 11" in line and "XLU" in line
    # aligned only says history and the current read share one day; it is not a freshness claim
    assert "History matches the current read" in line and "历史与当前读数一致" in line
    assert "Up to date" not in line
    baked = json.loads(line.split('id="si-cycles-ctx">', 1)[1].split("</script>", 1)[0])
    assert baked["coverage"] == ctx["coverage"] and baked["asof"] == "2026-10-30"


def test_full_coverage_prints_no_partial_line(tmp_path: Path) -> None:
    ctx = cycles_context(_site(tmp_path, SPDR), {"as_of": "2026-10-30"})
    assert ctx["coverage"]["measured"] == 11 and ctx["coverage"]["missing"] == []
    line = _cycles_line(_render(cycles_ctx=ctx))
    assert 'id="si-cycles-cov"' not in line


def test_a_sector_without_an_oscillator_is_not_measured(tmp_path: Path) -> None:
    site = _site(tmp_path, SPDR)
    p = site / "sectordata" / "sector_cycles.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["sectors"][0]["osc"] = []
    p.write_text(json.dumps(doc), encoding="utf-8")
    ctx = cycles_context(site, {"as_of": "2026-10-30"})
    assert ctx["coverage"]["measured"] == 10 and ctx["coverage"]["missing"] == ["XLB"]


def test_mismatched_generation_is_typed_not_drawn(tmp_path: Path) -> None:
    ctx = cycles_context(_site(tmp_path, SPDR), {"as_of": "2026-10-31"})
    assert ctx["generation"]["status"] == "incompatible_generation"
    line = _cycles_line(_render(cycles_ctx=ctx))
    assert "History is from a different day" in line and "历史来自不同日期" in line
    assert 'data-tip-en="History 2026-10-30, current read 2026-10-31.' in line
    assert 'data-tip-zh="历史 2026-10-30，当前读数 2026-10-31。' in line
    assert "History matches the current read" not in line


def test_absent_payload_renders_typed_unavailable(tmp_path: Path) -> None:
    assert cycles_context(tmp_path, {"as_of": "2026-10-30"}) == {}
    (tmp_path / "sectordata").mkdir()
    (tmp_path / "sectordata" / "sector_cycles.json").write_text("[1, 2]", encoding="utf-8")
    assert cycles_context(tmp_path, {"as_of": "2026-10-30"}) == {}
    for html in (_render(), _render(cycles_ctx={})):
        line = _cycles_line(html)
        # both the as-of and the generation slot: unknown is typed, never blank or zero
        assert line.count("— unavailable") == 2 and line.count("— 不可用") == 2
        assert "Sector measurement coverage unavailable" in line
        assert 'data-tip-en="Coverage and its evidence date appear with the measured-sector read."' in line
        assert "<time" not in line and " 0 / " not in line


def test_missing_asof_is_typed_missing_input(tmp_path: Path) -> None:
    ctx = cycles_context(_site(tmp_path, SPDR, asof=None), {"as_of": "2026-10-30"})
    assert ctx["asof"] is None and ctx["generation"]["status"] == "missing_input"
    line = _cycles_line(_render(cycles_ctx=ctx))
    assert line.count("— unavailable") == 2 and "<time" not in line


# ────────────────────────────────────────────────────────────── no sizing language

def _board_rows():
    return [
        {"sym": "XLK", "chip_en": "HALF SIZE", "chip_zh": "半仓", "chip_tone": "warn", "stat_en": "a"},
        {"sym": "XLE", "chip_en": "WATCH", "chip_zh": "观察", "chip_tone": "info", "stat_en": "b"},
    ]


def test_half_size_chip_is_dropped_from_a_row_list() -> None:
    rows = _board_rows()
    out = drop_sizing_chips(rows)
    assert out[0] == {"sym": "XLK", "chip_en": "", "chip_zh": "", "chip_tone": "", "stat_en": "a"}
    assert out[1] == rows[1]
    assert rows == _board_rows(), "the input board must not be mutated"


def test_half_size_chip_is_dropped_from_a_lane_dict() -> None:
    board = {"act_now": _board_rows(), "watch": _board_rows()[1:], "meta": {"n": 2}}
    out = drop_sizing_chips(board)
    assert out["act_now"][0]["chip_en"] == "" and out["act_now"][1]["chip_en"] == "WATCH"
    assert out["watch"] == board["watch"] and out["meta"] == {"n": 2}
    assert board["act_now"][0]["chip_en"] == "HALF SIZE", "the input board must not be mutated"
    assert drop_sizing_chips(None) is None


def test_grader_reads_as_not_a_win_rate() -> None:
    caption = ("Conviction-call hit rate over all resolved calls, Neutral included. Not a win rate.",
               "全部已结算判断（含中性）的条件命中率，并非胜率。")
    assert "L('%s','%s')" % caption in _page()
    src = _router()
    foot = src.split("function paintFoot(){", 1)[1].split("\n}", 1)[0]
    assert " · Not a win rate'" in foot and " · 并非胜率')" in foot
    assert "g.title=isZh()?'%s'" % caption[1] in foot and "'%s';" % caption[0] in foot


def test_what_changed_chips_wrap_inside_the_phone_width() -> None:
    """A What-changed chip can be a whole sentence. Under the old nowrap rule the
    China page's trailing-leader chip measured 469px and gave a 390px phone a 499px
    page. Both pages' chip idiom wraps inside its pill."""
    for name in ("sector_central.html.j2", "sector_central_china.html.j2"):
        rule = re.search(r"\n  \.tc-chip \{[^}]*\}", (TPL / name).read_text(encoding="utf-8"))
        assert rule, f"{name}: the base tc-chip rule is missing"
        assert "white-space:normal;max-width:100%" in rule.group(0), name
        assert "nowrap" not in rule.group(0), name
