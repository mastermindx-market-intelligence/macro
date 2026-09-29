import os
import shutil
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build_site import _plan_relations_for
from tests.test_dashboard_template_render import _base_vm, _board_row, _env, _prophet_book

ROOT = Path.cwd()
SITE = Path(os.environ["TMPDIR"]) / "pri_ui_c1_site"
env = _env()
vm = _base_vm()
row = _board_row(
    ticker="LFUS", name="LFUS", lane=None, dossier=None, featured=True,
    stage="setting_up", entry_signal={"status": "watch", "headline": "Wait for the base"},
    signal={}, hold={},
)
vm["us_standouts"] = {"buy": [row], "eligible": 1}
vm["us_prophet_book"] = _prophet_book(
    [{
        "id": "LFUS-BULL-20260810", "asset": " lfus ", "lifecycle_state": "entered",
        "entry_status": "buy_now", "board_read": None, "_priority_score": 72.0,
        "entry_zone": None, "entry_zone_state": None, "closed": False,
        "plan_asof": "2026-08-16", "recorded_at": "2026-08-16",
        "entry_date": "2026-08-10", "signal_date": "2026-08-15",
        "formation_date": "2026-08-10",
    }],
    asof="2026-09-24", source_board_asof="2026-09-23",
)
state, by_ticker = _plan_relations_for(vm["us_prophet_book"], False)
vm["plan_rel"] = {"state": state, "plans": []}
vm["plan_rel_by_ticker"] = by_ticker
from engine.us_candidate_lanes import project_candidate_visibility
pool_row = {
    "ticker": "LFUS", "name": "LFUS", "sector": "Industrials", "pool_rank": 1,
    "in_buy_lane": True, "lane": "bottoming", "headline_reason": "already_open",
    "lane_reasons": ["cleared_admission", "already_open"], "tier_cascade": None,
    "admission_class": None, "prophet_score_basis": None, "prophet": None,
}
vm["us_candidate_visibility"] = project_candidate_visibility({
    "as_of": "2026-09-24",
    "candidate_pool": {"as_of": "2026-09-24", "pool_definition": "us_candidate_pool_v1",
                       "eligible": 1, "rows": [pool_row]},
})
html = env.get_template("dashboard.html.j2").render(**vm, mode="stocks")
soup = BeautifulSoup(html, "html.parser")
related = soup.select_one("#us-cand-grid .pvs-plan-relation[data-plan-relation=\"related_security\"]")
assert related is not None, "related plan relation did not render"
for details in soup.find_all("details"):
    if "ucp-receipt" in (details.get("class") or []) or "pv-setup-inline" in (details.get("class") or []):
        details["open"] = ""
for script in list(soup.find_all("script")):
    text = script.string or script.get_text()
    if not any(key in text for key in ("USProphetSource", "_plvRender", "setLang", "setTheme")):
        script.decompose()
related = soup.select_one("#us-cand-grid .pvs-plan-relation[data-plan-relation=\"related_security\"]")
assert related is not None, "related plan relation did not render"
base_plv = soup.select_one("#plv-asof")
states = {
    "today": ("quotes as of 10:12 am ET", "报价截至 美东 10:12"),
    "prior": ("last read Jul 29, 4:12 pm ET", "上次判读 07-29 美东 16:12"),
    "unavailable": ("quote time unavailable", "报价时间不可用"),
}
for key, (english, chinese) in states.items():
    paragraph = soup.new_tag("p", attrs={"class": "plv-state-crop", "data-force-state": key})
    english_node = soup.new_tag("span", attrs={"class": "l-en"}); english_node.append(english)
    chinese_node = soup.new_tag("span", attrs={"class": "l-zh"}); chinese_node.append(chinese)
    paragraph.extend([english_node, chinese_node])
    base_plv.parent.append(paragraph)

related = soup.select_one("#us-cand-grid .pvs-plan-relation[data-plan-relation=\"related_security\"]")
assert related is not None, "related plan relation did not render"
none_crop = soup.new_tag("div", attrs={"class": "pvs-none-crop", "data-force-state": "none"})
none_crop.append(BeautifulSoup(str(related), "html.parser"))
none_rel = none_crop.select_one(".pvs-plan-relation")
none_rel["data-plan-relation"] = "none"
none_rel.find("h3").clear()
none_rel.find("h3").append(BeautifulSoup('<span class="l-en">Plan connection</span><span class="l-zh">计划关联</span>', "html.parser"))
note = none_rel.find("p", class_="pvs-note")
note.clear()
note.append(BeautifulSoup('<span class="l-en">No model plan is linked to this candidate. No plan or position is created here.</span><span class="l-zh">此候选暂无关联的模型计划，不在此创建计划或持仓。</span>', "html.parser"))
for record in none_rel.find_all("div", class_="pvs-plan-rec"):
    record.decompose()
related.parent.append(none_crop)
style = soup.new_tag("style")
style.string = "body{margin:0} #content{display:block !important;margin:16px auto;max-width:1180px;padding:0 16px} #plv-panel{display:block !important;margin:12px 0} .plv-state-crop{font:12px/1.4 ui-monospace,monospace;margin:6px 0} .pvs-none-crop{margin:12px 0}"
soup.head.append(style)
SITE.joinpath("fixture.html").write_text(str(soup), encoding="utf-8")
for asset in ("theme.css", "theme.js"):
    shutil.copy2(ROOT / "templates" / asset, SITE / asset)
print(SITE / "fixture.html")
