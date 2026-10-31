"""Read-only USDA report installation acceptance; stdlib, no HTTP or provider.

Send over existing SSH to /opt/macro/.venv/bin/python -B - /opt/macro.
Missing output is PENDING, never PASS. Source drift requires review before rebinding.
This does not establish browser acceptance, article rights or Press publication.
"""
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
import json
import subprocess
import sys

SOURCE_ID = "usda-nass-2026-10-13-crop-progress"
SLUG = "crop-progress-october-13-2026-ogress"
CANONICAL = "https://www.mastermind-x.com/research/" + SLUG + ".html"
DATE = "2026-10-13"
SOURCE_HASHES = {'scripts/build_research_pages.py': '7338c4dda666cac90291a4ba41b0d415fdfaa13ecec52513d97d67f3ec1d9930', 'lib/pages.py': '2673025c9729d5665936dbe6cafd461e8dff200feacc3e0081f0f378df2fd28b', 'lib/config.py': 'fa22ec934ec5294072b6bb4bf081d787f3f8ad5da4702ce3f4818b1674dbd53f', 'lib/seo.py': '5e09e9e278ddb914cfcb9fa0085c5d0724ecb03789d65eef94ef155d96c74064', 'engine/research_vault/sidecar.py': 'ee8201bb38c86235cc2d17d0bfffafe00f559dd511a3426d5f999cb7ed55caa7', 'engine/research_vault/slugs.py': '584f6947b4d012bc5f3b7c6a62d046a9f95ab6d0ecd3fb068c54e243cffd7bd7', 'engine/research_vault/excerpt.py': '0060b346fc933d22a5a76391198b9477d93b26672730059587797849315f8393', 'templates/data_base.js': '2aaceaf98a0f534aa342bdc6e64c831a2261a04fafebab4becf50f2d7c82620a', 'templates/research_report.html.j2': '4f17d3eccefb6eaa926375b9a125555aa8f8df8b3ad5317cdb27970ed1a69304', 'templates/research_index.html.j2': '9538e4973dfd7e31cb2107a5b1b622d2a95a833e46458ddf73f587d3ac6afc67', 'templates/_site_nav.html.j2': '164f3119fd04b8886d2d29703dc9c017e13bceeae1ecc49a36f9842353d9e482', 'templates/_navlinks.html.j2': '5318e6f11db80e225707cd02b0776f590c3defcaf6aaca81085e9bd956981242'}
SUMMARY_SHA = 'b5e2f720a12a6bd56535b5bc84405e74eb5850d23e9b961e0962d23f82c47171'
EXCERPT_SHA = 'fff4ba6360b5663b35519f4c9baec6f1eea599b2300dfbe6f8397a0d2ccb204c'


def digest(blob):
    return sha256(blob).hexdigest()


def json_digest(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


class Report(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical = []
        self.structured = []
        self.links = []
        self.ctas = []
        self.tickers = 0
        self.gates = 0
        self.script = None
        self.script_text = []
        self.stack = []
        self.excerpts = []
        self.para = None
        self.teaser = None
        self.teaser_text = ""
        self.excerpt_inside_gate = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = (attrs.get("class") or "").split()
        ancestors = {c for _, cs in self.stack for c in cs}
        if "rr-x" in classes and "rr-gate" in ancestors:
            self.excerpt_inside_gate = True
        if tag == "p" and "rr-x-body" in ancestors:
            self.excerpt_inside_gate |= "rr-gate" in ancestors or "rr-gate" in classes
            self.para = []
        if "rr-teaser" in classes:
            self.teaser = []
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, classes))
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical.append(attrs.get("href"))
        if tag == "a":
            self.links.append(attrs.get("href") or "")
            if "rr-cta" in classes:
                self.ctas.append(attrs.get("href"))
        self.tickers += int("rr-tk" in classes or "rr-tks" in classes)
        self.gates += int("rr-gate" in classes)
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.script = True
            self.script_text = []

    def handle_data(self, data):
        if self.script:
            self.script_text.append(data)
        if self.para is not None:
            self.para.append(data)
        if self.teaser is not None:
            self.teaser.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script:
            self.structured.append(json.loads("".join(self.script_text)))
            self.script = None
        if tag == "p" and self.para is not None:
            self.excerpts.append("".join(self.para))
            self.para = None
        if tag == "p" and self.teaser is not None:
            self.teaser_text = "".join(self.teaser)
            self.teaser = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def inspect(root, *, fixture=False):
    root = Path(root)
    files = {}

    def read(rel):
        p = root / rel
        blob = p.read_bytes() if p.is_file() else None
        files[rel] = digest(blob) if blob is not None else None
        return blob

    def stable():
        return all((digest((root / p).read_bytes()) if (root / p).is_file() else None) == h
                   for p, h in files.items())

    result = {"observed_at": datetime.now(timezone.utc).isoformat(), "source_id": SOURCE_ID,
              "canonical": CANONICAL, "fixture": fixture, "files": files,
              "state": "PENDING_INCUMBENT_RENDER", "writes": 0, "network_calls": 0,
              "browser_accepted": False, "press_publication": False, "cutover": False}
    for rel, expected in SOURCE_HASHES.items():
        assert digest(read(rel) or b"") == expected, "render source drift: " + rel
    raw_catalog = read("data/research_vault/catalog.json")
    assert raw_catalog, "installed catalog missing"
    rows = [r for r in json.loads(raw_catalog)["items"] if r.get("id") == SOURCE_ID]
    assert len(rows) == 1, "canonical source missing or duplicated"
    row = rows[0]
    assert row["published_at"] == DATE and row["pages"] == 16 and row["tickers"] == [], "source identity/date/issuer drift"
    assert json_digest(row["summary_points"]) == SUMMARY_SHA, "accepted summary drift"
    raw_excerpt = read("data/research_vault/excerpts.json")
    assert raw_excerpt, "installed excerpts missing"
    excerpt = json.loads(raw_excerpt)["excerpts"].get(SOURCE_ID)
    assert json_digest(excerpt) == EXCERPT_SHA, "accepted excerpt drift"
    original = read("site/research/" + SLUG + ".html")
    served = read("site.served/research/" + SLUG + ".html")
    if original is None or served is None:
        assert stable(), "inputs changed during pending inspection"
        result.update(input_stable=True, source_dependencies=len(SOURCE_HASHES))
        return result
    assert original == served, "site/site.served mismatch"
    report = Report()
    report.feed(original.decode("utf-8"))
    assert report.canonical == [CANONICAL], "wrong canonical link"
    articles = [s for s in report.structured if isinstance(s, dict) and s.get("@type") == "Article"]
    assert len(articles) == 1, "missing or duplicate article metadata"
    article = articles[0]
    assert article.get("url") == CANONICAL and article.get("datePublished") == DATE, "article date/url drift"
    assert article.get("author", {}).get("name") == 'U.S. Department of Agriculture, National Agricultural Statistics Service', "source attribution drift"
    assert not article.get("about") and report.tickers == 0, "invented issuer association"
    assert article.get("isAccessibleForFree") is False and article.get("hasPart", {}).get("isAccessibleForFree") is False and article.get("hasPart", {}).get("cssSelector") == ".rr-gate" and report.gates == 1, "paywall metadata mismatch"
    assert report.excerpts == excerpt and not report.excerpt_inside_gate, "rendered excerpt drift or wrong gate placement"
    assert row["summary_points"][0] in report.teaser_text, "attributed observation teaser drift"
    assert report.ctas == ["../research_vault.html?doc=" + SOURCE_ID], "wrong acquisition route"
    assert not any(".pdf" in href.lower() or "research_inbox/" in href for href in report.links), "private/direct PDF link"
    assert stable(), "inputs changed during inspection"
    result.update(state="REPORT_FILES_VERIFIED", page_sha256=digest(original),
                  report_date=DATE, input_stable=True, source_dependencies=len(SOURCE_HASHES))
    return result


def main():
    root = Path(sys.argv[1]).resolve()
    assert root == Path("/opt/macro"), "production CLI requires the existing installed root"
    head = lambda: subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    before = head()
    result = inspect(root)
    after = head()
    assert before == after, "installed HEAD moved during inspection"
    result.update(installed_head_before=before, installed_head_after=after, stable_head=True)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
