"""Test the read-only report probe with the retained, accepted USDA render.

Usage: python -B verify_usda_report_install.py REPO LOCAL_STORE RENDER NEW_OUTPUT
All mutations are isolated fixtures. Original inputs and the probe stay unchanged.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys


def main():
    repo, retained, render, output = map(lambda p: Path(p).resolve(), sys.argv[1:])
    assert not output.exists(), "occupied fixture output"
    probe_path = Path(__file__).with_name("inspect_usda_report_install.py")
    spec = importlib.util.spec_from_file_location("report_probe", probe_path)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    inputs = {str(p): probe.digest(p.read_bytes()) for p in (
        probe_path, retained / "research_vault/catalog.json", render / "excerpts.json",
        render / ("site/research/" + probe.SLUG + ".html"),
        *(repo / p for p in probe.SOURCE_HASHES),
    )}
    baseline = {p: (repo / p).read_bytes() for p in probe.SOURCE_HASHES}
    baseline["data/research_vault/catalog.json"] = (retained / "research_vault/catalog.json").read_bytes()
    baseline["data/research_vault/excerpts.json"] = (render / "excerpts.json").read_bytes()
    pages = [prefix + "/research/" + probe.SLUG + ".html" for prefix in ("site", "site.served")]
    html = (render / pages[0]).read_text()
    for p in pages:
        baseline[p] = html.encode()
    output.mkdir(parents=True)
    active = False
    violations = []

    def audit(event, args):
        if not active:
            return
        mutation = event in {"os.remove", "os.mkdir", "os.rmdir", "os.rename"}
        if event == "open":
            mutation |= bool((args[2] or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        if mutation or event.startswith("socket.") or event in {"subprocess.Popen", "os.system"}:
            violations.append(event)
            raise RuntimeError("probe side effect refused: " + event)

    sys.addaudithook(audit)
    cases = []

    def check(name, updates=None, refusal=None, state="REPORT_FILES_VERIFIED"):
        nonlocal active
        root = output / name
        payload = dict(baseline)
        payload.update(updates or {})
        for rel, blob in payload.items():
            if blob is not None:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(blob)
        before = {str(p.relative_to(root)): probe.digest(p.read_bytes()) for p in root.rglob("*") if p.is_file()}
        active = True
        try:
            result = probe.inspect(root, fixture=True)
        except AssertionError as exc:
            assert refusal and refusal in str(exc), (name, str(exc))
            outcome = {"refused": str(exc)}
        else:
            assert refusal is None, name + " was not refused"
            assert result["state"] == state and result["fixture"] and result["input_stable"], name
            assert not result["browser_accepted"] and not result["press_publication"] and not result["cutover"]
            outcome = {"state": result["state"]}
        finally:
            active = False
        after = {str(p.relative_to(root)): probe.digest(p.read_bytes()) for p in root.rglob("*") if p.is_file()}
        assert before == after, name + " mutated fixture"
        cases.append({"name": name, "passed": True, **outcome, "inputs_unchanged": True})

    def alter_page(name, old, new, refusal):
        assert old in html and old != new
        edited = html.replace(old, new).encode()
        check(name, {p: edited for p in pages}, refusal)

    check("accepted_render")
    check("both_pages_pending", {p: None for p in pages}, state="PENDING_INCUMBENT_RENDER")
    check("served_pending", {pages[1]: None}, state="PENDING_INCUMBENT_RENDER")
    check("site_pending", {pages[0]: None}, state="PENDING_INCUMBENT_RENDER")
    rel = next(iter(probe.SOURCE_HASHES))
    check("source_drift", {rel: baseline[rel] + b"\n# drift\n"}, "render source drift")
    check("served_mismatch", {pages[1]: baseline[pages[1]] + b"\n"}, "site/site.served mismatch")
    alter_page("wrong_canonical", 'rel="canonical" href="' + probe.CANONICAL, 'rel="canonical" href="https://example.invalid/', "wrong canonical link")
    alter_page("freshened_date", '"datePublished": "' + probe.DATE, '"datePublished": "2026-10-14T16:00:00Z', "article date/url drift")
    alter_page("wrong_author", '"name": "U.S. Department of Agriculture"', '"name": "Other source"', "source attribution drift")
    alter_page("invented_issuer", '"@type": "Article"', '"@type": "Article", "about": {"tickerSymbol":"ADM"}', "invented issuer association")
    alter_page("changed_excerpt", '<p>WASDE - 676 Approved', '<p>WASDE - 999 Approved', "rendered excerpt drift")
    alter_page("excerpt_under_gate", 'class="rr-x-body"', 'class="rr-x-body rr-gate"', "paywall metadata mismatch")
    # Keep one gate so excerpt placement must be checked independently of its count.
    moved = html.replace('<div class="rr-gate">', '<div class="held-gate">').replace('class="rr-x-body"', 'class="rr-x-body rr-gate"')
    check("single_gate_wrong_placement", {p: moved.encode() for p in pages}, "wrong gate placement")
    alter_page("lost_forecast_qualifier", 'USDA projects U.S. wheat', 'U.S. wheat', "attributed projection teaser drift")
    alter_page("wrong_cta", 'href="../research_vault.html?doc=' + probe.SOURCE_ID, 'href="../research_vault.html?doc=other', "wrong acquisition route")
    alter_page("wrong_paywall", '"isAccessibleForFree": false', '"isAccessibleForFree": true', "paywall metadata mismatch")
    alter_page("private_pdf_link", '</body>', '<a href="research_inbox/private.pdf">PDF</a></body>', "private/direct PDF link")
    catalog = json.loads(baseline["data/research_vault/catalog.json"])
    catalog["items"][0]["summary_points"][0] += " changed"
    check("catalog_summary_drift", {"data/research_vault/catalog.json": json.dumps(catalog).encode()}, "accepted summary drift")
    excerpt = json.loads(baseline["data/research_vault/excerpts.json"])
    excerpt["excerpts"][probe.SOURCE_ID][0] += " changed"
    check("stored_excerpt_drift", {"data/research_vault/excerpts.json": json.dumps(excerpt).encode()}, "accepted excerpt drift")
    assert inputs == {p: probe.digest(Path(p).read_bytes()) for p in inputs}, "original input changed"
    assert not violations
    result = {"source_id": probe.SOURCE_ID, "probe_sha256": inputs[str(probe_path)],
              "cases": cases, "passed": len(cases), "audit_violations": violations,
              "retained_inputs_unchanged": True, "fixture_only": True,
              "production_writes": 0, "provider_calls": 0,
              "browser_accepted": False, "publication": False, "cutover": False}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": len(cases), "result": str(output / "result.json")}))


if __name__ == "__main__":
    main()
