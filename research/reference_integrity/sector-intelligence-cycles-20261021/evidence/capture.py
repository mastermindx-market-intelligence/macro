#!/usr/bin/env python3
"""RIG evidence capture — sector-intelligence-cycles-20261021 (verdict C03/C10 coverage cells + J13 compositions).

Captures the PRODUCTION render tree (site/ at d86344b93a0b, served over http on :8931) through evidence_frame.html,
which seeds localStorage theme/lang before the page's head boot reads them. Two headless-Chrome passes per cell:
dump-dom (height + probe facts) then screenshot at that height, cropped to the iframe width. Writes PNGs + cells.yml.
Usage: python3 capture.py <out_dir> [cell_id ...]   (no ids = all cells)
"""
import hashlib, json, os, re, subprocess, sys, tempfile, time, urllib.parse
from PIL import Image
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE = "http://localhost:8931/__sic_evidence_frame.html"
VIEWPORT = {"desktop": 1440, "mobile": 390}
ROUTE = {"rotation": "sector_central.html#map", "lenses": "sector_central.html#moving",
         "research": "sector_central.html#tm-mount", "watches": "sector_central.html#accumulation-section",
         "dossier": "sectors/XLK.html", "brief": "sector_central.html#overview", "cycles": "sector_cycles.html"}
LIMITED = {  # the 31 PAPER_CAPACITY_LIMITED cells of proposal.yml coverage (viewport, theme, locale)
 "rotation": [("desktop","dark","en"),("desktop","dark","zh"),("desktop","light","zh"),("mobile","dark","en"),("mobile","light","en"),("mobile","light","zh")],
 "lenses":   [(v,t,l) for v in ("desktop","mobile") for t in ("dark","light") for l in ("en","zh")],
 "dossier":  [("desktop","dark","zh"),("desktop","light","en"),("desktop","light","zh"),("mobile","dark","en"),("mobile","dark","zh"),("mobile","light","en")],
 "research": [("desktop","dark","en"),("desktop","dark","zh"),("desktop","light","zh"),("mobile","dark","en"),("mobile","light","en"),("mobile","light","zh")],
 "watches":  [("desktop","dark","zh"),("desktop","light","zh"),("mobile","dark","en"),("mobile","light","en"),("mobile","light","zh")],
}
def cells():
    out = []
    for view, combos in LIMITED.items():
        for v, t, l in combos:
            out.append(dict(id=f"{view}-{v}-{t}-{l}", kind="coverage", view=view, viewport=v, theme=t, lang=l, w=VIEWPORT[v], src=ROUTE[view]))
    for lens in ("money", "explore", "confluence"):  # the other three lenses, two corner cells each
        for v, t, l in (("desktop","dark","en"), ("mobile","light","zh")):
            out.append(dict(id=f"lens-{lens}-{v}-{t}-{l}", kind="composition", view="lenses", viewport=v, theme=t, lang=l, w=VIEWPORT[v], src=f"sector_central.html#{lens}"))
    for w in (320, 430, 768):  # J13 widths, dark/en
        for view in ("brief", "rotation", "cycles"):
            out.append(dict(id=f"w{w}-{view}-dark-en", kind="composition", view=view, viewport=f"w{w}", theme="dark", lang="en", w=w, src=ROUTE[view]))
    return out
def chrome(args, timeout=90):
    return subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                           "--no-first-run", "--disable-extensions", f"--user-data-dir={PROFILE}"] + args,
                          capture_output=True, text=True, timeout=timeout)
def attrs(html):
    m = re.search(r"<html([^>]*)>", html); d = {}
    if m:
        for k, v in re.findall(r'data-([a-z-]+)="([^"]*)"', m.group(1)): d[k] = v.replace("&quot;", '"').replace("&amp;", "&")
    return d
def one(c, out_dir):
    url = f"{BASE}?src={urllib.parse.quote(c['src'], safe='/')}&theme={c['theme']}&lang={c['lang']}&w={c['w']}"
    hostw = max(c["w"], 500)
    r = chrome(["--window-size=%d,1000" % hostw, "--virtual-time-budget=20000", "--dump-dom", url])
    a = attrs(r.stdout)
    if a.get("ready") != "1":
        return dict(c, status="error", error="frame never reported ready (dump-dom)", url=url)
    h = min(int(a.get("h") or 1000), 14000)
    png = os.path.join(out_dir, c["id"] + ".png")
    r2 = chrome(["--window-size=%d,%d" % (hostw, h), "--virtual-time-budget=20000", f"--screenshot={png}", url], timeout=150)
    if not os.path.exists(png):
        return dict(c, status="error", error="screenshot missing: " + (r2.stderr or "")[-200:], url=url)
    im = Image.open(png)
    if im.width > c["w"] or im.height > h:
        im = im.crop((0, 0, min(c["w"], im.width), min(h, im.height))); im.save(png)
    im = Image.open(png)
    sha = hashlib.sha256(open(png, "rb").read()).hexdigest()
    return dict(c, status="captured", url=url, png=os.path.basename(png), px=[im.width, im.height], sha256=sha,
                doc_h=int(a.get("h") or 0), scroll_w=int(a.get("sw") or 0), horizontal_overflow=int(a.get("sw") or 0) > c["w"],
                overflow_candidates=[x for x in (a.get("ovf") or "").split(" ") if x][:6],
                data_theme=a.get("theme"), data_lang=a.get("lang"), hash=a.get("hash"), title=a.get("title"), asof=a.get("asof"),
                incompatible_generation_text=a.get("incompat") == "1", sections=json.loads(a.get("sections") or "{}"))
def q(s):  # single-quoted YAML scalar
    return "'" + str(s).replace("'", "''") + "'"
def emit(rows, out_dir, head_sha):
    L = ["# RIG evidence cells — sector-intelligence-cycles-20261021 — generated by evidence/capture.py", 
         f"# production render tree site/ at {head_sha}, served http://localhost:8931 ; frame = evidence/evidence_frame.html",
         f"captured_at: '{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}'", f"production_sha: {head_sha}",
         "capture: production-render-tree-chrome-headless-1x", "cells:"]
    for r in rows:
        L.append(f"  - id: {r['id']}"); 
        for k in ("kind","view","viewport","theme","lang","src","status"): L.append(f"    {k}: {q(r[k])}")
        if r["status"] != "captured": L.append(f"    error: {q(r.get('error'))}"); continue
        L.append(f"    png: evidence/{r['png']}"); L.append(f"    sha256: {r['sha256']}"); L.append(f"    px: [{r['px'][0]}, {r['px'][1]}]")
        L.append(f"    doc_h: {r['doc_h']}"); L.append(f"    scroll_w: {r['scroll_w']}"); L.append(f"    horizontal_overflow: {str(r['horizontal_overflow']).lower()}")
        L.append("    overflow_candidates: [" + ", ".join(q(x) for x in r["overflow_candidates"]) + "]")
        for k in ("data_theme","data_lang","hash","title","asof"): L.append(f"    {k}: {q(r.get(k) or '')}")
        L.append(f"    incompatible_generation_text: {str(r['incompatible_generation_text']).lower()}")
        L.append("    sections: " + json.dumps(r["sections"], separators=(",", ":")))
    open(os.path.join(out_dir, "cells.yml"), "w", encoding="utf-8").write("\n".join(L) + "\n")
if __name__ == "__main__":
    out_dir = sys.argv[1]; want = set(sys.argv[2:]); os.makedirs(out_dir, exist_ok=True)
    PROFILE = tempfile.mkdtemp(prefix="sic-ev-")
    head_sha = subprocess.run(["git", "-C", os.environ.get("RT", "."), "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
    rows = []
    for c in cells():
        if want and c["id"] not in want: continue
        t0 = time.time(); r = one(c, out_dir); rows.append(r)
        print(f"{r['status']:9} {c['id']:34} {r.get('px') or r.get('error','')!s:14} sw={r.get('scroll_w','-')} theme={r.get('data_theme','-')} lang={r.get('data_lang','-')} hash={r.get('hash','-')} {time.time()-t0:.1f}s", flush=True)
    emit(rows, out_dir, head_sha)
    print("cells:", len(rows), "captured:", sum(r['status']=='captured' for r in rows))
