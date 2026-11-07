"""Native Nasdaq/Russell render and actual-chart namespace proof, controlled fixtures only."""
from pathlib import Path
import copy, datetime, hashlib, importlib.util, json, os, re, shutil, sys
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

work = Path(__file__).resolve().parent
root = Path(os.environ.get("D05_SOURCE_ROOT", str(work.parents[1])))
sys.path.insert(0, str(root))
source = work / "native-index-source"
out = work / "site" / "d05-index-fixtures"
proof = work / "native-index-browser"
out.mkdir(exist_ok=True)
proof.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("d05_native_index_builder", source / "build_subsector_confluence.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
env = Environment(loader=ChoiceLoader([
    DictLoader({"_site_nav.html.j2": ""}),
    FileSystemLoader(str(source)),
    FileSystemLoader(str(root / "templates")),
]), autoescape=True)
def sha(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(), "bytes": len(data)}
expected = {
    "build_subsector_confluence.py": "d5e6b675cb5d05a15d8744c3fbf8639eecb12237",
    "subsector_detail.html.j2": "b595dcf2ed6560d6913c975614ddfae64e9561e5",
    "chart.js": "3e3f538f9ca7fbeba24cd6f4ff2a8943f720ad1e",
    "lightweight-charts-v5.js": "fcd07f3a170237ac48b62d2c45bfc861d213575e",
}
for name, digest in expected.items():
    assert sha(source / name)["git_blob"] == digest, (name, sha(source / name))
for name in ["chart.js", "lightweight-charts-v5.js"]:
    shutil.copyfile(source / name, out / name)
for name in ["theme.css", "theme.js"]:
    shutil.copyfile(work / "site" / name, out / name)

def write_json(path, value):
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n")
fixtures = {}
render_results = []
for ns, date, ticker, base in [
    ("nasdaq", "2026-10-28", "NDQFIX", 100),
    ("russell", "2026-10-29", "RUSFIX", 50),
]:
    days = []
    cursor = datetime.date.fromisoformat(date)
    while len(days) < 70:
        if cursor.weekday() < 5:
            days.append(cursor.isoformat())
        cursor -= datetime.timedelta(days=1)
    days.reverse()
    bars = [[day, round(base+i*.2, 2), round(base+i*.2+1, 2), round(base+i*.2-1, 2), round(base+i*.2+.5, 2), 10000+i] for i, day in enumerate(days)]
    common = {
        "label": ns.upper() + " NATIVE FIXTURE",
        "label_zh": "独立命名空间测试",
        "sector": "Controlled fixture", "class": "forming",
        "n_members": 5 if ns=="nasdaq" else 7,
        "n_priced": 3 if ns=="nasdaq" else 4,
        "n_live": 4, "coverage_pct": 0.5 if ns=="nasdaq" else 0.75,
        "as_of": date, "reliability": "low",
        "entry": {"tier": "T2", "buyable": False},
        "regime": {"label": "Fixture observation", "label_zh": "测试观察", "rs_60d": 2.4},
        "members": [{"ticker": ticker, "price": bars[-1][4], "ret_20d": 4.2, "vs_basket": 1.7,
                     "stock_tier": "T1", "stock_buyable": True, "stock_state": "Fixture stock read"}],
        "has_signals": True,
    }
    groups = []
    for key, kind in [("collision-proof", "subsector"), ("amalg-proof", "sector")]:
        g = dict(copy.deepcopy(common), key=key, chart_key=key, kind=kind)
        groups.append(g)
        write_json(out / ("subsectorohlc_"+ns) / (key+".json"), {
            "t":key, "o":1, "src":"d05-controlled-namespace-fixture", "fixture_namespace":ns,
            "bars":bars, "anchor": builder.bar_derive.chart_anchor(days, "US"),
        })
        write_json(out / ("subsector_signals_"+ns) / (key+".json"), {"markers":[], "fixture_namespace":ns})
    payload = {"ok":True, "as_of":date, "subsectors":[groups[0]], "sectors":[groups[1]]}
    board_path = out / ("marketdata/subsector_confluence_"+ns+".json")
    write_json(board_path, payload)
    detail_dir = out / ("subsector_"+ns)
    detail_dir.mkdir(exist_ok=True)
    (detail_dir / "fixture-orphan.html").write_text("owned stale fixture")
    count = builder.render_index_pages(ns, out, env, "2099-01-01 00:00 UTC")
    assert count == 2
    assert not (detail_dir/"fixture-orphan.html").exists()
    fixtures[ns] = {"date":date, "ticker":ticker, "last_close":bars[-1][4], "payload":payload}
    for group in groups:
        path = detail_dir / (group["key"]+".html")
        html = path.read_text()
        assert '"ohlc_dir":"subsectorohlc_'+ns+'"' in html
        assert '"sig_dir":"subsector_signals_'+ns+'"' in html
        assert ticker in html and ("RUSFIX" if ns=="nasdaq" else "NDQFIX") not in html
        html = html.replace("</body>", '<div style="position:fixed;bottom:0;left:0;z-index:100000;background:var(--panel);color:var(--muted);padding:3px 8px;font:10px sans-serif">D05 NAMESPACE FIXTURE · NOT LIVE · '+ns.upper()+'</div></body>')
        path.write_text(html)
    render_results.append({"namespace":ns,"pages":count,"same_slug_isolated":True,"pruned_only_owned_orphan":True})
# A source failure or empty source must not erase the previous native detail pages.
negative = []
for ns in fixtures:
    bp = out / ("marketdata/subsector_confluence_"+ns+".json")
    paths = sorted((out / ("subsector_"+ns)).glob("*.html"))
    before = {str(p.relative_to(out)):sha(p) for p in paths}
    original_bytes = bp.read_bytes()
    try:
        for mode in ["missing", "malformed", "empty"]:
            if mode=="missing": bp.unlink()
            elif mode=="malformed": bp.write_text("{invalid")
            else: write_json(bp, {"subsectors":[], "sectors":[]})
            assert builder.render_index_pages(ns, out, env, "2099-01-01 00:00 UTC")==0
            assert {str(p.relative_to(out)):sha(p) for p in paths} == before
            negative.append({"namespace":ns,"source_state":mode,"render_count":0,"previous_detail_bytes_preserved":True})
            bp.write_bytes(original_bytes)
    finally:
        bp.write_bytes(original_bytes)

results = {"schema":"d05.native-index-namespace-proof.v1","macro_head":"4802d1b1e2e53061c42f57e78223ab4e45b16c3a",
    "fixture_only":True,"native_builder":"render_index_pages","render_cases":render_results,
    "failure_cases":negative,"sources":{name:sha(source/name) for name in expected},
    "cases":[],"errors":[],
    "limits":["Controlled source and display fixtures; not current index membership or market data.",
              "Shared navigation include omitted in this standalone template proof.",
              "Company href and board return href checked; no new authenticated Company or save acceptance.",
              "Synthetic prices and sessions; native calendar/marker/scientific qualification remains separate."]}
base_url = "http://localhost:8765/d05-index-fixtures/"
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, chromium_sandbox=True)
    for width, height, theme, lang in [(1440,1000,"dark","en"),(390,844,"light","zh")]:
        ctx = browser.new_context(viewport={"width":width,"height":height},reduced_motion="reduce")
        ctx.add_init_script("localStorage.setItem('theme',"+json.dumps(theme)+");localStorage.setItem('lang',"+json.dumps(lang)+");")
        ctx.route("**/*", lambda route: route.continue_() if route.request.url.startswith("http://localhost:8765/") else route.abort())
        page = ctx.new_page()
        page.on("pageerror",lambda error:results["errors"].append(str(error)))
        for ns, f in fixtures.items():
            for key in ["collision-proof","amalg-proof"]:
                requests = []
                capture_request = lambda request, seen=requests: seen.append(request.url) if ".json" in request.url else None
                page.on("request", capture_request)
                path = "subsector_"+ns+"/"+key+".html"
                page.goto(base_url+path,wait_until="domcontentloaded")
                page.wait_for_function("window.StockChart && StockChart._cur && StockChart._cur.chart && StockChart._cur.rows.length===70")
                page.locator("#chart-host canvas").first.wait_for(state="visible")
                page.wait_for_function("document.documentElement.scrollWidth<=innerWidth+1")
                page.evaluate("() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")
                actual = page.evaluate("""() => ({
                    theme:document.documentElement.dataset.theme, lang:document.documentElement.dataset.lang,
                    ohlc:StockChart._cur.ohlcDir, signals:StockChart._cur.opts.signalsDir,
                    source:StockChart._cur.data.fixture_namespace,
                    lastClose:StockChart._cur.rows.at(-1).c,
                    observed:DETAIL.group.as_of, rendered:DETAIL.generated_utc,
                    key:CHART_KEY, kind:DETAIL.kind, kindLabel:DETAIL.kind_label_en,
                    tickerLinks:[...document.querySelectorAll('#members a')].map(a=>a.getAttribute('href')),
                    back:document.querySelector('a.back').getAttribute('href'),
                    body:document.body.innerText, canvasCount:document.querySelectorAll('#chart-host canvas').length
                })""")
                assert actual["theme"]==theme and actual["lang"]==lang
                assert actual["source"]==ns and actual["lastClose"]==f["last_close"]
                assert actual["ohlc"]=="../subsectorohlc_"+ns
                assert actual["signals"]=="../subsector_signals_"+ns
                assert actual["key"]==key
                assert actual["observed"]==f["date"] and "2099-01-01" not in actual["body"]
                assert f["ticker"] in actual["body"] and ("RUSFIX" if ns=="nasdaq" else "NDQFIX") not in actual["body"]
                assert actual["back"]=="../subsectors.html"
                assert all(href=="../stock.html#"+f["ticker"] for href in actual["tickerLinks"]) and actual["tickerLinks"]
                assert "complex" in actual["kindLabel"] if key=="amalg-proof" else "sub-industry" in actual["kindLabel"]
                expected_urls=[base_url+"subsectorohlc_"+ns+"/"+key+".json",base_url+"subsector_signals_"+ns+"/"+key+".json"]
                page.wait_for_function("performance.getEntriesByType('resource').some(x=>x.name.endsWith("+json.dumps("/subsector_signals_"+ns+"/"+key+".json")+"))")
                assert all(url in requests for url in expected_urls), (requests,expected_urls)
                assert not any(("subsectorohlc_"+("russell" if ns=="nasdaq" else "nasdaq")) in url for url in requests)
                page.locator("#structure").scroll_into_view_if_needed()
                name=f"{width}-{theme}-{lang}-{ns}-{key}.png"
                page.screenshot(path=str(proof/name),full_page=False)
                actual.pop("body")
                results["cases"].append({"path":path,"width":width,"height":height,"theme":theme,"lang":lang,
                    "passed":True,"actual":actual,"native_data_requests":list(requests),"screenshot":name,"screenshot_digest":sha(proof/name)})
                page.remove_listener("request", capture_request)
        ctx.close()
    browser.close()
results["passed"] = not results["errors"]
results["recorded_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
(proof/"result.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps({"passed":results["passed"],"browser_cases":len(results["cases"]),"render_cases":len(results["render_cases"]),
"failure_cases":len(results["failure_cases"]),"errors":results["errors"]}))
if not results["passed"]: raise SystemExit(1)
