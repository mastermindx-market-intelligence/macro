"""Canonical visual evidence for the existing MRI component, using synthetic data.

Run from repository root:
  python3 mockups/evidence/mri-surprise-confirmation-20261113/capture.py
This uses the existing capture_page_evidence owner. It does not access production,
read browser credentials, create a data writer, or claim native authenticated proof.
"""
from pathlib import Path
import hashlib
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from jinja2 import Environment, FileSystemLoader
from scripts.capture_page_evidence import main as capture_main
from tests.test_release_surprise_ui import evidence_fixture


def main():
    target = Path(__file__).resolve().parent
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))
    component = env.get_template("_release_surprise_confirmation.html.j2").render()
    skin = (ROOT / "templates/theme.css").read_text()
    payload = evidence_fixture()
    html = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<link rel="icon" href="data:,"><title>MRI synthetic component verification</title>'
            '<style>' + skin + '</style><style>'
            'body{margin:0;padding:20px;background:var(--bg);color:var(--text);font-family:var(--font-ui);}'
            'main{max-width:760px;margin:auto}.panel{padding:20px}'
            'html[data-lang="en"] .l-zh{display:none!important}'
            'html[data-lang="zh"] .l-en{display:none!important}'
            '</style></head><body class="page-macro"><main><section class="panel">'
            '<h2><span class="l-en">Release Radar - synthetic verification</span>'
            '<span class="l-zh">\u6570\u636e\u53d1\u5e03\u96f7\u8fbe - \u5408\u6210\u6570\u636e\u9a8c\u8bc1</span></h2>'
            + component + '</section></main><script>'
            'window.MMXReleaseSurprise.render(document.getElementById("rr-confirmation"),'
            + json.dumps(payload, ensure_ascii=True).replace('</', '<\\/')
            + ');</script></body></html>')
    (target / "fixture.html").write_text(html)
    inputs = ["templates/_release_surprise_confirmation.html.j2",
              "templates/release_surprise_confirmation.js", "templates/theme.css",
              "tests/test_release_surprise_ui.py", "scripts/capture_page_evidence.py"]
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in inputs}
    (target / "README.md").write_text(
        '# MRI component visual evidence\n\n'
        'Local, explicitly synthetic source data; no authenticated production claim.\n'
        'The canonical capture owner records all eight desktop/mobile x en/zh x dark/light rest cells, '
        'plus real keyboard-focus captures for the changed summary focus treatment. '
        'Desktop is the required 1440px, not the earlier 1280px research screenshots.\n\n'
        'This repairs the discovered CI registration gap without modifying the guard or component. '
        'Existing native-dialog and P4 integration receipts remain separate and valid.\n\n'
        'The fixture was rendered from the actual component and shared theme. The fixture is not '
        'a production page; generated source bytes and input hashes make its scope inspectable.\n\n'
        '## Captured input SHA-256\n\n```json\n' + json.dumps(hashes, indent=2) + '\n```\n')
    with tempfile.TemporaryDirectory(prefix="msc-canonical-evidence-") as temp:
        site = Path(temp)
        (site / "mri-confirmation.html").write_text(html)
        return capture_main([
            "--registry", str(site / "explicit-local-fixture-registry-not-used.yml"),
            "--site-dir", str(site), "--routes", "/mri-confirmation.html",
            "--output-dir", str(target / "screenshots"),
            "--manifest", str(target / "manifest.json"),
            "--smells", str(target / "smells.json"),
            "--emit-md", str(target / "smells.md"),
            "--viewports", "desktop,mobile", "--locales", "en,zh", "--themes", "dark,light",
            "--max-pages", "1", "--delay-ms", "0", "--timeout-s", "12",
            "--force-state", "focus:focus(#rr-confirmation summary)"])


if __name__ == "__main__":
    raise SystemExit(main())
