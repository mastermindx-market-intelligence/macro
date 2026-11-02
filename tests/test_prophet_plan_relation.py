from __future__ import annotations

import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("book", [
    [], 7, True, "plans",
    {"plans": None}, {"plans": {}}, {"plans": "LFUS"}, {"plans": 7},
    {"plans": [], "lifecycle_counts": [1]},
    {"plans": [], "lifecycle_counts": []},
    {"plans": [], "lifecycle_counts": "counts"},
    {"plans": [], "lifecycle_counts": 7},
    {"plans": [], "lifecycle_counts": False},
    {"plans": [], "intake": 7},
    {"plans": [], "intake": True},
    {"plans": [], "intake": 1.5},
    {"plans": [None]}, {"plans": ["LFUS"]},
    {"plans": [{"id": "P1", "asset": "LFUS"}, None]},
    {"plans": [{"asset": "LFUS"}]},
    {"plans": [{"id": " ", "asset": "LFUS"}]},
    {"plans": [{"id": [], "asset": "LFUS"}]},
    {"plans": [{"id": "P1", "asset": []}]},
    {"plans": [{"id": "P1", "asset": " "}]},
    {"plans": [{"id": [], "asset": "LFUS", "closed": True}]},
    {"plans": [{"id": "P1", "asset": "LFUS", "lifecycle_state": ["entered"]}]},
    {"plans": [{"id": "P1", "asset": "LFUS", "lifecycle_state": {"state": "entered"}}]},
    {"plans": [{"id": "P1", "asset": "LFUS", "entry_date": 7},
               {"id": "P2", "asset": "LFUS", "entry_date": "2026-10-01"}]},
])
def test_invalid_plan_book_reaches_existing_stock_route_unavailable(tmp_path, book):
    import json
    from scripts.build_site import (
        _read_us_prophet_book, _split_us_prophet_board, _us_prophet_episode_map,
        _us_life_repair_context, _plan_relations_for, _plan_relation_for_row,
    )
    from tests.test_dashboard_template_render import _base_vm, _env

    path = tmp_path / "index.json"
    path.write_text(json.dumps(book))
    admitted, error = _read_us_prophet_book(path)
    assert (admitted, error) == (None, True)
    vm = _base_vm()
    vm.update(us_prophet_book=admitted, us_prophet_book_error=error)
    shell, gate, locked = _split_us_prophet_board(admitted, 1)
    episodes = _us_prophet_episode_map((admitted or {}).get("plans") or [])
    context = _us_life_repair_context(vm, shell, gate, 1)
    relations = _plan_relations_for(admitted, error)
    assert relations == ("unknown", {})
    assert _plan_relation_for_row(relations, {"ticker": "LFUS"}) == {
        "state": "unknown", "plans": []}
    vm.update(context, us_prophet_book=shell, life_gate=gate,
              us_prophet_episodes=episodes,
              plan_rel={"state": relations[0], "plans": []},
              plan_rel_by_ticker=relations[1])
    page = BeautifulSoup(_env().get_template("dashboard.html.j2").render(
        **vm, mode="stocks"), "html.parser")
    assert page.select_one("#us-plan-block .mx-error")
    assert not locked
    relation_sections = page.select(".pvs-plan-relation")
    assert relation_sections, "the existing candidate details must exercise the relation"
    for section in relation_sections:
        assert section["data-plan-relation"] == "unknown"
        assert "Plan records could not be read for this candidate." in section.get_text()
        assert not section.select(".pvs-plan-link, .pvs-plan-rec")


def test_plan_book_reader_distinguishes_missing_from_unreadable(tmp_path):
    from scripts.build_site import _read_us_prophet_book, _plan_relations_for

    path = tmp_path / "index.json"
    assert _read_us_prophet_book(path) == (None, False)
    path.write_text("{broken")
    assert _read_us_prophet_book(path) == (None, True)
    assert _plan_relations_for(None, False) == ("unknown", {})
    from tests.test_dashboard_template_render import _env
    ladder = BeautifulSoup(str(_env().get_template("_prophet_card.html.j2").module.mx_ladder(
        None, error=False)), "html.parser")
    assert ladder.select_one('[aria-busy="true"]')
    assert not ladder.select_one('.mx-error')


@pytest.mark.parametrize("book", [{}, {"source_asof": "2026-10-01"}, {"plans": []}])
def test_plan_book_reader_preserves_legacy_empty_books(tmp_path, book):
    import json
    from scripts.build_site import _read_us_prophet_book, _plan_relations_for

    path = tmp_path / "index.json"
    encoded = json.dumps(book, indent=2)
    path.write_text(encoded)
    admitted, error = _read_us_prophet_book(path)
    assert admitted == book and error is False
    assert path.read_text() == encoded
    assert _plan_relations_for(admitted, error) == ("none", {})


def test_plan_book_reader_preserves_valid_full_book_and_native_projection(tmp_path, monkeypatch):
    import json
    import scripts.build_site as build

    book = _lfus_book()
    encoded = json.dumps(book, indent=2)
    path = tmp_path / "index.json"
    path.write_text(encoded)
    # JSON decoding returns this exact object: admission must not copy or rewrite it.
    monkeypatch.setattr(build.json, "loads", lambda raw: book)
    admitted, error = build._read_us_prophet_book(path)
    assert admitted is book and error is False
    assert path.read_text() == encoded
    before = json.dumps(book, sort_keys=True)
    shell, gate, locked = build._split_us_prophet_board(admitted, 1)
    assert shell["plans"] == book["plans"][:1]
    assert gate["total"] == 2 and gate["preview"] == 1 and gate["locked"] == 1
    assert locked == book["plans"][1:]
    # Existing episode grouping uses raw asset identity; preserve that behavior.
    assert build._us_prophet_episode_map(admitted["plans"]) == {}
    vm = {"us_prophet_book": admitted, "us_standouts": {"buy": [{"ticker": "LFUS"}]}}
    assert build._us_life_repair_context(vm, shell, gate, 1) == {
        "us_candidate_map": {"LFUS": {"ticker": "LFUS"}},
        "cand_no_plan": {"sample": [{"ticker": "LFUS"}], "all_no_plan": False},
        "life_gate_visible_preview": 0, "life_gate_visible_locked": 2,
    }
    state, by_ticker = build._plan_relations_for(admitted, error)
    assert state == "none" and [row["id"] for row in by_ticker["LFUS"]] == ["LFUS-BULL-20260810"]
    assert json.dumps(book, sort_keys=True) == before


def test_native_plan_book_read_assigns_existing_book_and_error_state():
    import ast
    import inspect
    from scripts.build_site import main

    tree = ast.parse(inspect.getsource(main))
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and isinstance(node.value, ast.Call)
                   and isinstance(node.value.func, ast.Name)
                   and node.value.func.id == "_read_us_prophet_book"]
    assert len(assignments) == 1
    target = assignments[0].targets[0]
    assert isinstance(target, ast.Tuple)
    assert [item.id for item in target.elts] == ["us_prophet_book", "us_prophet_book_error"]


def _detail():
    from tests.test_dashboard_template_render import _env

    return _env().get_template("_prophet_setup_detail.html.j2").module


def _relation(book, error=False):
    from scripts.build_site import _plan_relations_for

    default, by_ticker = _plan_relations_for(book, error)
    return {
        "state": ("related_security" if by_ticker.get("LFUS") else default),
        "plans": by_ticker.get("LFUS", []),
    }


def _lfus_book():
    return {
        "plans": [
            {
                "id": "LFUS-CLOSED-20260801",
                "asset": " lfus ",
                "lifecycle_state": "resolved",
                "formation_date": "2026-08-05",
                "signal_date": "2026-08-10",
                "plan_asof": "2026-08-11",
                "closed": True,
            },
            {
                "id": "LFUS-BULL-20260810",
                "asset": "LFUS",
                "lifecycle_state": "entered",
                "formation_date": "2026-08-10",
                "signal_date": "2026-08-15",
                "plan_asof": "2026-08-16",
                "closed": False,
            },
        ]
    }


def test_plan_relation_pure_function_is_open_same_security_and_sorted():
    from scripts.build_site import _plan_relations_for

    default, by_ticker = _plan_relations_for(_lfus_book(), False)
    assert default == "none"
    assert list(by_ticker) == ["LFUS"]
    assert [plan["id"] for plan in by_ticker["LFUS"]] == ["LFUS-BULL-20260810"]
    assert by_ticker["LFUS"][0] == {
        "id": "LFUS-BULL-20260810",
        "lifecycle_state": "entered",
        "formation_date": "2026-08-10",
        "signal_date": "2026-08-15",
        "signal_date_basis": None,
        "observed_date": None,
        "price_basis_date": None,
        "recorded_at": None,
        "plan_asof": "2026-08-16",
    }
    assert _plan_relations_for(None, True)[0] == "unknown"
    assert _plan_relations_for({}, False) == ("none", {})


def test_plan_relation_excludes_every_truthy_closed_value():
    from scripts.build_site import _plan_relations_for

    book = {"plans": [
        {"id": "AAA-TEXT", "asset": "AAA", "closed": "true", "formation_date": "2026-08-01"},
        {"id": "AAA-NUMBER", "asset": "AAA", "closed": 1, "formation_date": "2026-08-02"},
    ]}
    assert _plan_relations_for(book) == ("none", {})


@pytest.mark.parametrize("lifecycle", [["entered"], {"state": "entered"}])
def test_direct_relation_rejects_unrenderable_lifecycle_collection(lifecycle):
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row

    relations = _plan_relations_for({"plans": [
        {"id": "P1", "asset": "LFUS", "lifecycle_state": lifecycle}]})
    assert relations == ("unknown", {})
    relation = _plan_relation_for_row(relations, {"ticker": "LFUS"})
    section = BeautifulSoup(str(_detail().body({"ticker": "LFUS"}, "board", None, relation)),
                            "html.parser").select_one(".pvs-plan-relation")
    assert section["data-plan-relation"] == "unknown"
    assert not section.select(".pvs-plan-link, .pvs-plan-rec")


def test_plan_relation_sorts_multiple_open_plans_and_matches_normalized_tickers():
    from scripts.build_site import _plan_relations_for

    book = {"plans": [
        {"id": "AAA-EARLY", "asset": " aa ", "closed": False, "formation_date": "2026-08-01"},
        {"id": "AAA-LATE-B", "asset": "AA", "closed": False, "formation_date": "2026-08-10"},
        {"id": "AAA-LATE-A", "asset": "aA", "closed": False, "formation_date": "2026-08-10"},
    ]}
    default, by_ticker = _plan_relations_for(book)
    assert default == "none"
    assert list(by_ticker) == ["AA"]
    assert [plan["id"] for plan in by_ticker["AA"]] == [
        "AAA-LATE-B", "AAA-LATE-A", "AAA-EARLY"]


def test_missing_plan_book_is_unknown_and_presenters_render_none_without_a_match():
    from scripts.build_site import _plan_relations_for
    from tests.test_dashboard_template_render import _env

    assert _plan_relations_for(None, False)[0] == "unknown"

    env = _env()
    row = {"ticker": "AAA", "name": "AAA", "sector": "Industrials"}
    relation = {"state": "none", "plans": []}
    by_ticker = {"BBB": relation["plans"]}
    pool = env.get_template("_us_candidate_pool_rows.html.j2").render(
        rows=[row], plan_rel=relation, plan_rel_by_ticker=by_ticker)
    board = env.get_template("_us_board_cards.html.j2").render(
        items=[row], sg_any=False, bs_adj=False, xu_allfeat=False, trg_map={},
        rw_en="", rw_zh="", plan_rel=relation, plan_rel_by_ticker=by_ticker)
    assert 'data-plan-relation="none"' in pool
    assert 'data-plan-relation="none"' in board


def test_setup_detail_reuses_the_existing_plan_lifecycle_vocabulary():
    setup = (ROOT / "templates" / "_prophet_setup_detail.html.j2").read_text(encoding="utf-8")
    plan_cards = (ROOT / "templates" / "_us_prophet_plan_cards.html.j2").read_text(encoding="utf-8")
    assert "{% from '_us_prophet_plan_cards.html.j2' import life_label_en, life_label_zh %}" in setup
    assert "_LIFE_LABEL_EN" not in setup
    assert "_LIFE_LABEL_ZH" not in setup
    assert "{% macro life_label_en(code) -%}" in plan_cards
    assert "{% macro life_label_zh(code) -%}" in plan_cards


def test_setup_detail_renders_related_security_record():
    html = str(_detail().body({"ticker": "LFUS"}, "board", "2026-09-24", _relation(_lfus_book())))
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one(".pvs-plan-relation")
    assert section["data-plan-relation"] == "related_security"
    assert section["data-plan-exact"] == "unavailable"
    assert section.select_one("h3").get_text(" ", strip=True) == "Related model record 相关模型记录"
    records = section.select(".pvs-plan-rec")
    assert len(records) == 1
    assert records[0]["data-plan-id"] == "LFUS-BULL-20260810"
    assert records[0]["data-plan-lifecycle"] == "entered"
    assert "Entered" in records[0].get_text(" ", strip=True)
    assert "入场" in records[0].get_text(" ", strip=True)
    assert "Formation anchor 形成锚点 2026-08-10" in records[0].get_text(" ", strip=True)
    assert "Source signal date · basis unavailable 来源信号日期 · 日期依据不可用 2026-08-15" in records[0].get_text(" ", strip=True)
    assert "Plan as of 计划截至 2026-08-16" in records[0].get_text(" ", strip=True)
    button = records[0].select_one(".pvs-plan-link")
    assert button["data-pvs-plan-target"] == "pv-LFUS-BULL-20260810"
    text = section.get_text(" ", strip=True)
    assert "It is not this candidate's plan and not a position you hold." in text
    assert "这是同一证券的模型记录，不是此候选的计划，也不是您持有的仓位。" in text
    assert "Exact plan relation: not available from the source." in text
    assert "精确计划关联：来源未提供。" in text


def test_setup_detail_renders_none_wrong_ticker_and_unknown_states():
    module = _detail()
    other_only = {"plans": [{"id": "BBB-BULL-20260801", "asset": "BBB", "closed": False,
                             "lifecycle_state": "watch", "formation_date": "2026-08-01"}]}
    none = BeautifulSoup(str(module.body({"ticker": "AAA"}, "board", None, _relation(other_only))),
                         "html.parser").select_one(".pvs-plan-relation")
    assert none["data-plan-relation"] == "none"
    notes = " ".join(node.get_text(" ", strip=True) for node in none.select("p.pvs-note"))
    assert "No open same-security model record found. No plan or position is created here." in notes
    assert "未找到同一证券的未平仓模型记录，不在此创建计划或持仓。" in notes
    assert "Exact plan relation: not available from the source." in notes
    assert "精确计划关联：来源未提供。" in notes
    assert not none.select(".pvs-plan-rec")

    unknown = BeautifulSoup(str(module.body({"ticker": "AAA"}, "board", None, _relation(None, True))),
                            "html.parser").select_one(".pvs-plan-relation")
    assert unknown["data-plan-relation"] == "unknown"
    assert "Plan records could not be read for this candidate." in unknown.get_text(" ", strip=True)
    assert "无法读取此候选的计划记录。" in unknown.get_text(" ", strip=True)


def test_three_presenters_render_the_same_plan_relation_body():
    from tests.test_dashboard_template_render import _env

    env = _env()
    relation = _relation(_lfus_book())
    row = {"ticker": " lfus ", "name": "LFUS", "sector": "Industrials"}
    module = env.get_template("_prophet_setup_detail.html.j2").module
    expected = str(module.body(row, "pool", None, relation))
    pool = env.get_template("_us_candidate_pool_rows.html.j2").render(
        rows=[dict(row, lane_reasons=["cleared_admission"])], plan_rel=relation,
        plan_rel_by_ticker={"LFUS": relation["plans"]})
    board = env.get_template("_us_board_cards.html.j2").render(
        items=[row], sg_any=False, bs_adj=False, xu_allfeat=False, trg_map={}, rw_en="", rw_zh="",
        plan_rel=relation, plan_rel_by_ticker={"LFUS": relation["plans"]})
    table = str(module.table_action(row, None, plan_rel=relation))
    rendered = [BeautifulSoup(fragment, "html.parser").select_one(".pvs-plan-relation") for fragment in
                (expected, pool, board, table)]
    normalized = [" ".join(str(node).split()) for node in rendered]
    assert normalized[0] == normalized[1] == normalized[2] == normalized[3]


def test_dashboard_has_delegated_plan_link_handler_without_pool_state_writes():
    source = (ROOT / "templates" / "dashboard.html.j2").read_text(encoding="utf-8")
    match = re.search(r"document\.addEventListener\('click', function\(event\)\{.*?pvsPlanLinkResult='ok'.*?\}\);", source, re.S)
    assert match, "delegated plan-link handler is missing"
    handler = match.group(0)
    for expected in (
        "pv-setup-dialog", ".pvs-close", "USProphetSource.set('plans')",
        "document.getElementById(target)", "pvsPlanLinkResult='missing'",
        "sm-hidden", "sm-reveal", "scrollIntoView", "focus({preventScroll:true})",
        "setAttribute('tabindex','-1')", "pvsPlanLinkResult='ok'"):
        assert expected in handler
    assert "createElement" not in handler
    assert "us-candidate-pool" not in handler
    assert "ucp-" not in handler


def _run_plan_navigation(assertions: str) -> None:
    """Execute both existing owners; DOM doubles expose their observable effects.

    A real Chromium check additionally covers the production CSS visibility and
    native focus behavior. This dependency-light regression runs in the source job.
    """
    import shutil
    import subprocess

    source = (ROOT / "templates/dashboard.html.j2").read_text()

    def script_after(marker):
        start = source.index("<script>", source.index(marker)) + len("<script>")
        return source[start:source.index("</script>", start)]

    lifecycle = script_after("P-MP1-SHELL §7 — the lifecycle ladder's filter + URL law")
    # This marker is inside its script, unlike the lifecycle marker above.
    start = source.rfind("<script>", 0, source.index("P0 #6185 — Candidates | Plans source toggle"))
    navigation = source[start + len("<script>"):source.index("</script>", start)]
    harness = r'''
const assert = require('node:assert/strict');
const historyCalls = [], effects = [];
let focused = null;
function element(attrs, classes=[]) {
  const tokens = new Set(classes);
  return {
    attrs, listeners:{}, dataset:{}, hidden:false,
    classList:{contains:x=>tokens.has(x), remove:x=>tokens.delete(x)},
    getAttribute(name){return this.attrs[name] ?? null;},
    setAttribute(name,value){this.attrs[name]=String(value);},
    removeAttribute(name){delete this.attrs[name];},
    addEventListener(name,fn){this.listeners[name]=fn;},
    querySelectorAll(){return [];},
    closest(){return null;},
  };
}
const panel=element({'data-lifef':'resolved','data-prophet-src':'candidates'});
const grid=element({id:'us-life-grid'});
const card=element({id:'pv-LFUS-BULL-20260810','data-life':'entered','data-record-only':'1'},
                   ['pvcard','pv-record','sm-hidden','sm-reveal']);
const sibling=element({id:'pv-LFUS-BULL-20260801','data-life':'resolved','data-record-only':'1'},
                      ['pvcard','pv-record']);
card.dataset.recordOnly=sibling.dataset.recordOnly='1';
let withheld=false;
card.closest=selector=>selector==='#us-life-grid'?grid:(withheld?card:null);
function visible(row) {
  // Boundary double for the already-tested lifecycle CSS; checked in Chromium too.
  return panel.getAttribute('data-prophet-src')==='plans' && !withheld &&
    panel.getAttribute('data-lifef')===row.getAttribute('data-life');
}
card.getClientRects=()=>visible(card)?[{}]:[];
card.scrollIntoView=()=>effects.push(['scroll',card.getAttribute('id')]);
card.focus=()=>{if(visible(card))focused=card; effects.push(['focus',card.getAttribute('id')]);};
const toggle=element({});
const clear=element({});
const zero=element({});
grid.querySelectorAll=()=>[card];
const button=element({'data-pvs-plan-target':'pv-LFUS-BULL-20260810'});
button.closest=()=>button;
const close={click(){dialog.open=false; effects.push(['close']);}};
const dialog={open:true,querySelector:()=>close};
const elements={'us-standouts':panel,'us-src-toggle':toggle,'us-life-grid':grid,
  'us-life-clear':clear,'us-life-filter-zero':zero,'pv-setup-dialog':dialog,
  'pv-LFUS-BULL-20260810':card,'pv-LFUS-BULL-20260801':sibling};
global.document={body:{dataset:{}},listeners:{},getElementById:id=>elements[id]||null,
  addEventListener(name,fn){this.listeners[name]=fn;}};
global.window={getComputedStyle:row=>({display:visible(row)?'flex':'none'})};
global.location={pathname:'/us_stocks.html',search:'?foo=keep&life=resolved',hash:''};
global.history={replaceState(_a,_b,url){historyCalls.push(url);location.search=url.slice(url.indexOf('?'));}};
''' + lifecycle + navigation + r'''
historyCalls.length=0;
function activate(){document.listeners.click({target:button});}
''' + assertions
    node = shutil.which("node")
    assert node, "existing Node runtime is required for Plan navigation behavior"
    proc = subprocess.run([node, "-e", harness], capture_output=True, text=True, timeout=15)
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_view_in_plans_selects_exact_target_lifecycle_before_visibility_and_focus():
    _run_plan_navigation(r'''
activate();
assert.equal(document.body.dataset.pvsPlanLinkResult,'ok');
assert.equal(visible(card),true,'exact entered Plan stayed hidden behind resolved filter');
assert.equal(focused,card,'focus must land on the exact Plan, not its same-ticker sibling');
assert.equal(panel.getAttribute('data-lifef'),'entered');
assert.deepEqual(historyCalls,['/us_stocks.html?foo=keep&life=entered']);
assert.equal(clear.hidden,false);
assert.equal(zero.hidden,true);
assert.equal(card.classList.contains('sm-hidden'),false);
assert.equal(card.classList.contains('sm-reveal'),false);
assert.equal(sibling.getAttribute('data-life'),'resolved');
assert.deepEqual(effects,[['close'],['scroll','pv-LFUS-BULL-20260810'],['focus','pv-LFUS-BULL-20260810']]);
''')


@pytest.mark.parametrize("condition", ["missing", "malformed", "outside", "withheld", "invalid-life"])
def test_view_in_plans_rejects_unavailable_or_malformed_targets_without_filter_or_focus(condition):
    setup = {
        "missing": "delete elements['pv-LFUS-BULL-20260810'];",
        "malformed": "button.attrs['data-pvs-plan-target']='us-standouts';",
        "outside": "card.closest=()=>null;",
        "withheld": "withheld=true;",
        "invalid-life": "card.attrs['data-life']='unpublished';",
    }[condition]
    _run_plan_navigation(setup + r'''
activate();
assert.equal(document.body.dataset.pvsPlanLinkResult,'missing');
assert.equal(panel.getAttribute('data-prophet-src'),'plans'); // existing missing-target behavior
assert.equal(panel.getAttribute('data-lifef'),'resolved');
assert.deepEqual(historyCalls,[]);
assert.equal(focused,null);
assert.deepEqual(effects,[['close']]);
assert.equal(card.classList.contains('sm-hidden'),true);
''')


@pytest.mark.needs_full_checkout("mockups")
def test_evidence_manifest_is_bound_to_the_captured_ui_head_and_fixture_bytes():
    import json
    import hashlib
    import re

    manifest = json.loads(
        (ROOT / "mockups/evidence/pri_ui_c1/manifest.json").read_text(encoding="utf-8"))
    harness = ROOT / "mockups/evidence/pri_ui_c1/render_fixture.py"
    harness_sha = hashlib.sha256(harness.read_bytes()).hexdigest()
    assert manifest["tool"]["module_sha256"] == harness_sha
    sha_40 = re.compile(r"^[0-9a-f]{40}$")
    assert sha_40.fullmatch(manifest["capture_head"])
    assert manifest["target"]["resolved_sha_or_none"] == manifest["capture_head"]
    assert sha_40.fullmatch(manifest["provenance"]["superseded_capture"])
    for page in manifest["pages"]:
        for state in page["states"]:
            png = ROOT / "mockups/evidence/pri_ui_c1" / state["file"]
            data = png.read_bytes()
            assert state["bytes"] == len(data)
            assert state["sha256"] == hashlib.sha256(data).hexdigest()


@pytest.mark.needs_full_checkout("mockups")
def test_plv_evidence_states_are_distinct_for_every_shell_cell():
    import json
    import itertools

    manifest = json.loads(
        (ROOT / "mockups/evidence/pri_ui_c1/manifest.json").read_text(encoding="utf-8"))
    by_cell = {}
    for page in manifest["pages"]:
        if not page["page_id"].startswith("fixture_plv_"):
            continue
        state_name = page["page_id"][len("fixture_plv_"):-len(".html")].replace("prior", "prior_day")
        for state in page["states"]:
            cell = (state["theme"], state["locale"], state["viewport"])
            by_cell.setdefault(cell, {})[state_name] = state["sha256"]
    assert set(by_cell) == {
        (theme, locale, viewport)
        for theme in ("dark", "light")
        for locale in ("en", "zh")
        for viewport in ("desktop", "mobile")
    }
    duplicates = []
    for cell, hashes in by_cell.items():
        assert set(hashes) == {"today", "prior_day", "unavailable"}, cell
        for left, right in itertools.combinations(sorted(hashes), 2):
            if hashes[left] == hashes[right]:
                duplicates.append(f"{cell}:{left}={right}")
    assert not duplicates, f"pixel-identical PLV state evidence: {', '.join(duplicates)}"


def test_plv_unavailable_body_uses_distinct_locale_sentences():
    source = (ROOT / "templates" / "dashboard.html.j2").read_text(encoding="utf-8")
    render = source[source.index("function _plvRender"):source.index("function _plvFetch")]
    expected = (
        "Nothing crossed today — last check time unavailable.",
        "今日没有出现上穿 — 最近一次检查时间不可用。",
        "Nothing crossing yet — last check time unavailable.",
        "尚无新的上穿 — 最近一次检查时间不可用。",
    )
    for sentence in expected:
        assert sentence in render
    assert render.count("last check time unavailable.") == 2
    assert render.count("最近一次检查时间不可用。") == 2
    assert "最近一次检查 美东 —。" not in render


def test_plan_relation_preserves_existing_machine_attribute_sets():
    module = _detail()
    row = {"ticker": "LFUS", "entry_signal": {"status": "wait", "headline": "Wait"},
           "signal": {}, "hold": {}}
    attrs = ("data-reason", "data-entry-status", "data-native-id", "data-setup-kind", "data-source-field")
    before = str(module.body(row, "board", None))
    after = str(module.body(row, "board", None, _relation(_lfus_book())))
    extracted = []
    for html in (before, after):
        values = {name: sorted(re.findall(rf'{name}="([^"]*)"', html)) for name in attrs}
        extracted.append(values)
    assert extracted[0] == extracted[1]


@pytest.mark.parametrize(
    'plans_value',
    [None, False, True, 0, 7, '', 'plans', {}, {'stale': True}],
)
def test_appended_plan_relations_reject_malformed_plans_container(plans_value):
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row
    # Explicit null/bool/int/string/mapping plans leave the owner unreadable,
    # without raising; only an absent plans key or an empty list stays "none".
    assert _plan_relations_for({'plans': plans_value}) == ('unknown', {})


@pytest.mark.parametrize(
    'plan_row',
    [
        'p1',
        42,
        None,
        [],
        {'id': 'p1'},
        {'asset': 'LFUS'},
        {'id': '   ', 'asset': 'LFUS'},
        {'id': 'p1', 'asset': '  '},
        {'id': 7, 'asset': 'LFUS'},
        {'id': 'p1', 'asset': 7},
        {'id': 'p1', 'asset': None},
    ],
)
def test_appended_plan_relations_reject_malformed_open_record(plan_row):
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row
    # Open record (no truthy `closed`): id and asset must both be nonblank
    # strings, and a malformed record must surface as unknown, never a skip.
    assert _plan_relations_for({'plans': [plan_row]}) == ('unknown', {})


def test_appended_plan_relations_mixed_valid_and_malformed_record_is_unknown():
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row
    book = {'plans': [
        {'id': 'p1', 'asset': 'LFUS', 'closed': 0, 'lifecycle_state': 'signal',
         'formation_date': '2026-02-02', 'signal_date': '2026-02-03',
         'plan_asof': '2026-02-04'},
        {'id': 'p2', 'asset': '   '},
    ]}
    assert _plan_relations_for(book) == ('unknown', {})


def test_appended_plan_relations_mixed_valid_and_nonmapping_record_is_unknown():
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row
    book = {'plans': [
        {'id': 'p1', 'asset': 'LFUS', 'lifecycle_state': 'signal'},
        'stale-entry',
    ]}
    assert _plan_relations_for(book) == ('unknown', {})


@pytest.mark.parametrize(
    'closed_value',
    [True, 1, 1.0, 'yes', 'true', 'closed', [0], {'x': 1}, (1,)],
)
def test_appended_plan_relations_closed_truthy_forms_excluded(closed_value):
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row
    # Every truthy closed value excludes the record, legacy string/numeric
    # forms included, and exclusion happens before id/asset validation.
    book = {'plans': [{'id': 'old', 'asset': 'LFUS', 'closed': closed_value}]}
    assert _plan_relations_for(book) == ('none', {})


def test_appended_plan_relations_malformed_closed_record_is_skipped():
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row
    # A closed record missing `id` is skipped before validation, so the
    # remaining valid open record still yields a readable owner.
    book = {'plans': [
        {'asset': 'LFUS', 'closed': 'yes'},
        {'id': 'p1', 'asset': 'LFUS', 'closed': False, 'lifecycle_state': 'signal',
         'formation_date': '2026-01-02', 'signal_date': '2026-01-03',
         'plan_asof': '2026-01-04'},
    ]}
    state, by_ticker = _plan_relations_for(book)
    assert state == 'none'
    assert [entry['id'] for entry in by_ticker['LFUS']] == ['p1']


@pytest.mark.parametrize(
    'book',
    [{}, {'plans': []}, {'asof': '2026-01-01'}],
)
def test_appended_plan_relations_empty_or_absent_plans_stay_none(book):
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row
    assert _plan_relations_for(book) == ('none', {})








def test_appended_plan_relations_unknown_propagates_via_row_helper():
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row
    relation = _plan_relations_for({'plans': None})
    assert relation == ('unknown', {})
    assert _plan_relation_for_row(relation, {'ticker': ' lfus '}) == {
        'state': 'unknown', 'plans': []}




def test_appended_detail_template_unknown_copy_and_no_view_in_plans():
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row
    # One valid record plus one malformed open record: the owner is unreadable,
    # so the real candidate-detail template must show unknown copy and must
    # not offer View in Plans (no silent skip of the malformed record).
    book = {'plans': [
        {'id': 'p1', 'asset': 'LFUS', 'closed': False, 'lifecycle_state': 'signal',
         'formation_date': '2026-01-02', 'signal_date': '2026-01-03',
         'plan_asof': '2026-01-04'},
        {'id': 'p2'},
    ]}
    html = str(_detail().body({"ticker": "LFUS"}, "board", None, _relation(book)))
    assert "Plan records could not be read for this candidate." in html
    assert 'View in Plans' not in html


def test_appended_detail_template_view_in_plans_control_for_valid_book():
    from scripts.build_site import _plan_relations_for, _plan_relation_for_row
    html = str(_detail().body({"ticker": "LFUS"}, "board", None, _relation(_lfus_book())))
    assert 'View in Plans' in html


@pytest.mark.parametrize("counts", [None, {}, {"entered": 3, "resolved": 1}])
def test_plan_book_reader_preserves_valid_lifecycle_counts(tmp_path, counts):
    import json
    from scripts.build_site import _read_us_prophet_book
    book = {"plans": [], "lifecycle_counts": counts}
    path = tmp_path / "index.json"
    original = json.dumps(book).encode()
    path.write_bytes(original)
    assert _read_us_prophet_book(path) == (book, False)
    assert path.read_bytes() == original


@pytest.mark.parametrize("intake", [None, False, 0, {}, [], "", "early_turn_watch", ["early_turn_watch"], {"early_turn_watch": 2}])
def test_plan_book_reader_preserves_supported_intake(tmp_path, intake):
    import json
    from scripts.build_site import _read_us_prophet_book
    from tests.test_dashboard_template_render import _env, _base_vm
    book = {"plans": [], "intake": intake}
    path = tmp_path / "index.json"
    original = json.dumps(book).encode()
    path.write_bytes(original)
    admitted, error = _read_us_prophet_book(path)
    assert (admitted, error) == (book, False)
    assert path.read_bytes() == original
    vm = _base_vm()
    vm.update(us_prophet_book=admitted, us_prophet_book_error=error)
    _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")


@pytest.mark.parametrize("basis,signal,label", [
    ("tier_event_date", "2026-10-20", "Signal event session"),
    ("legacy_formation_alias", "2026-10-16", "Formation alias · signal event unverified"),
    (None, "2026-10-20", "Source signal date · basis unavailable"),
    ("tier_observation", None, "Observation only · no signal event recorded"),
])
def test_related_plan_keeps_clock_meanings_without_entry_or_publication_claim(basis, signal, label):
    from copy import deepcopy
    from scripts.build_site import _plan_relations_for

    # Retained USFD-BULL-20261016 clock values; alternatives exercise legacy/T3 inputs.
    plan = dict(id="USFD-BULL-20261016", asset="USFD", lifecycle_state="ready",
                formation_date="2026-10-16", signal_date=signal, signal_date_basis=basis,
                observed_date="2026-10-22", price_basis_date="2026-10-22",
                recorded_at="2026-10-23", plan_asof="2026-10-23")
    original = deepcopy(plan)
    relation = _plan_relations_for({"plans": [plan]})[1]["USFD"][0]
    for key in ("signal_date_basis", "observed_date", "price_basis_date", "recorded_at"):
        assert relation[key] == plan[key]
    assert plan == original
    html = str(_detail().body({"ticker": "USFD"}, "board", None,
                             {"state": "related_security", "plans": [relation]}))
    section = BeautifulSoup(html, "html.parser").select_one(".pvs-plan-relation")
    en = " ".join(node.get_text(" ", strip=True) for node in section.select(".l-en"))
    zh = " ".join(node.get_text(" ", strip=True) for node in section.select(".l-zh"))
    assert label in en
    assert "Formation anchor" in en and "形成锚点" in zh
    assert "Price observations through" in en and "价格观测截至" in zh
    assert "Recorded date" in en and "记录日期" in zh
    assert "Publication / first-visible time not supplied" in en
    assert "未提供发布／首次可见时间" in zh
    assert "does not establish current entry availability" in en
    assert "2026-10-22" in section.get_text()
    assert "2026-10-23" in section.get_text()
    assert 'data-plan-exact="unavailable"' in str(section)
