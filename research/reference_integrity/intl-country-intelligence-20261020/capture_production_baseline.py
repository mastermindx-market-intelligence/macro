"""Actual anonymous production evidence captured after implementation, before release."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json, re, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture
REF = "intl-country-intelligence-20261020"
OUT = Path(__file__).resolve().parent
SHOTS = ROOT / "mockups/refs/reference_integrity" / REF
BASE_SHA = "a815e54f50e012fd693c9a1ec311f5e814f330bd"
AFTER_SHA = "6ad0c377ed80a8ccf07ecbfb6c7b44530b753cf7"
URL = "https://www.mastermind-x.com/intl.html"

def chrome_driver(*, headless, user_agent, observer_config, settle_ms):
    from playwright.sync_api import sync_playwright
    manager = sync_playwright().start()
    try:
        browser = manager.chromium.launch(channel="chrome", headless=headless)
    except Exception as exc:
        manager.stop()
        raise capture.CaptureUnavailable(str(exc)) from exc
    return capture._PlaywrightDriver(manager, browser, user_agent, observer_config, settle_ms)

def main():
    started = datetime.now(timezone.utc).isoformat()
    for directory in (OUT / "production/source", SHOTS / "before", SHOTS / "after"):
        directory.mkdir(parents=True, exist_ok=True)
    receipt = {"schema":"intl.reference_baseline_capture.v1", "capture_started_at":started,
        "live_url":URL, "source_commit":BASE_SHA, "proposed_artifact_commit":AFTER_SHA,
        "timing":"Actual production capture after implementation, before release.",
        "access":"anonymous", "source_files":[]}
    with urlopen(Request(URL, headers={"User-Agent":"Mastermind-Page-Evidence/1.0"}), timeout=40) as response:
        html = response.read()
        receipt["public_response"] = {"status":response.status, "url":response.url,
            "sha256":sha256(html).hexdigest(), "bytes":len(html),
            "received_at":datetime.now(timezone.utc).isoformat(),
            "origin_baseline_sha256":"9e73a81c020459c0d1d440987670d10cd137480f7660817a83ed176a2aa1862b"}
    (OUT / "production/intl.html").write_bytes(html)
    receipt["public_response"]["matches_read_only_origin_baseline"] = (
        receipt["public_response"]["sha256"] == receipt["public_response"]["origin_baseline_sha256"])
    check = subprocess.run(["git","cat-file","-e",BASE_SHA+"^{commit}"], cwd=ROOT, capture_output=True)
    if check.returncode:
        fetched = subprocess.run(["git","fetch","origin","main"], cwd=ROOT, capture_output=True, timeout=60)
        if fetched.returncode:
            raise RuntimeError("Could not resolve the documented production source commit")
    candidates = {"templates/intl.html.j2","scripts/build_intl.py","engine/intl_run.py"}
    for ref in re.findall(r"""(?:src|href)=["']([^"']+)["']""", html.decode("utf-8")):
        parsed = urlparse(ref)
        if parsed.netloc and parsed.netloc not in {"www.mastermind-x.com","mastermind-x.com"}:
            continue
        asset = parsed.path.lstrip("/")
        if asset and "/" not in asset and asset.endswith((".css",".js")):
            candidates.add("templates/"+asset)
    pending, done = sorted(candidates), set()
    while pending:
        name = pending.pop(0)
        if name in done:
            continue
        done.add(name)
        result = subprocess.run(["git","show",BASE_SHA+":"+name], cwd=ROOT, capture_output=True)
        if result.returncode:
            continue
        target = OUT / "production/source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(result.stdout)
        receipt["source_files"].append({"source_path":name,"path":str(target.relative_to(ROOT)),
            "bytes":len(result.stdout),"sha256":sha256(result.stdout).hexdigest()})
        if name.endswith(".j2"):
            for included in re.findall(r"""{%\s*include\s+["']([^"']+)["']""", result.stdout.decode("utf-8")):
                pending.append("templates/"+included)
    old_path = ROOT / "mockups/evidence/intl-review-repair-20261020/manifest.json"
    prior = json.loads(old_path.read_text())
    after = []
    for state in prior["pages"][0]["states"]:
        source = old_path.parent / state["file"]
        target = SHOTS / "after" / f'{state["viewport"]}-{state["locale"]}-{state["theme"]}.png'
        shutil.copyfile(source, target)
        assert sha256(target.read_bytes()).hexdigest() == state["sha256"]
        after.append({**state,"path":str(target.relative_to(ROOT)),"copied_from":str(source.relative_to(ROOT))})
    (OUT / "proposed_visual_manifest.json").write_text(json.dumps({
        "schema":"intl.reference_proposed_visuals.v1","source_commit":AFTER_SHA,
        "source_manifest":str(old_path.relative_to(ROOT)),
        "source_manifest_sha256":sha256(old_path.read_bytes()).hexdigest(),
        "states":after,"limitations":prior["honesty"]}, indent=2)+"\n")
    args = ["--repo",str(ROOT),"--base-url","https://www.mastermind-x.com",
        "--routes","/intl.html","--output-dir",str(SHOTS/"before"),
        "--manifest",str(OUT/"production_capture_manifest.json"),
        "--smells",str(OUT/"production_capture_census.json"),
        "--viewports","desktop,mobile","--locales","en,zh","--themes","light,dark",
        "--max-pages","1","--delay-ms","500","--settle-ms","700","--timeout-s","30"]
    with (OUT/"production_capture.log").open("w") as log, redirect_stdout(log), redirect_stderr(log):
        code = capture.main(args, driver_factory=chrome_driver)
    receipt.update(capture_exit=code,finished_at=datetime.now(timezone.utc).isoformat())
    (OUT/"production_capture_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"capture_exit":code,"source_files":len(receipt["source_files"]),
        "public_response":receipt["public_response"],"finished_at":receipt["finished_at"]}))
    return code

if __name__ == "__main__":
    raise SystemExit(main())
