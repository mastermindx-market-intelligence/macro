"""Capture unaltered #6712 API response bytes using its existing synthetic test cut.
Run only on the pinned candidate; this is contract proof, not live/source admission.
"""
import hashlib
import json
import subprocess
from pathlib import Path

PIN = "ec5c2e2544576f20348c6eadf834fe3cefae8039"
root = Path(__file__).resolve().parents[3]
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
if head != PIN:
    raise SystemExit("Run this capture only on pinned Bio candidate " + PIN)

# The capture depends on the separately pinned owner checkout, not this PR's
# source tree. Resolve its fixture file only after the exact-head guard above.
import runpy
owner_fixture = runpy.run_path(str(root / "tests/test_biocatalyst_wmn_api.py"))
_app, _projection, _wmn_inputs, NOW, GENERATION = (
    owner_fixture[key] for key in ("_app", "_projection", "_wmn_inputs", "NOW", "GENERATION")
)
import app.biocatalyst as api

out = Path(__file__).with_name("fixtures")
out.mkdir(parents=True, exist_ok=True)
inputs = _wmn_inputs()
original_now = api._wmn_now
api._wmn_now = lambda: NOW
receipts = []
def save(name, response):
    assert response.status_code == 200, (name, response.status_code, response.text)
    raw = response.content
    (out / name).write_bytes(raw)
    receipts.append({"file":name,"status":response.status_code,"sha256":hashlib.sha256(raw).hexdigest(),
        "cache_control":response.headers.get("cache-control"),"vary":response.headers.get("vary")})
    return response.json()

try:
    with _app(lambda: (_projection(inputs), {})) as client:
        page = save("company-page.json", client.get("/api/biocatalyst/v1/what-matters-next"))
        for view in ["upcoming", "reconcile", "history"]:
            for horizon in ([7, 30, 90, 180, 365] if view == "upcoming" else [None]):
                save(f"page-{view}-{horizon}.json", client.get("/api/biocatalyst/v1/what-matters-next",
                    params={"view":view,"limit":50,**({"horizon_days":horizon} if horizon is not None else {})}))
        detail = save("company-detail.json", client.get("/api/biocatalyst/v1/what-matters-next/detail",
            params={"generation_id":GENERATION,"event_fact_ref":inputs["events"][0]["event_id"]}))
    receipt = {"candidate_head":head,"fixture_kind":"existing synthetic owner cut through actual API",
        "capture_method":"TestClient; existing _app test auth override; fixed _wmn_now; _read_bundle projection fixture",
        "source_admission":False,"entitled_runtime_verified":False,"responses":receipts}
    (out / "capture-receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(json.dumps({"receipt":receipt}, indent=2))
finally:
    api._wmn_now = original_now
