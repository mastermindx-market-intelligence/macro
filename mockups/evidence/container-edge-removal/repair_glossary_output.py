"""Render and finalize only the glossary output with the existing publication owners.

The input is the exact PR #10654 candidate page or its CSS-only intermediate.
The committed public-page builder runs only in a temporary root. No collector
is run; executable content, main content, and the daily banner stay unchanged.
All sweeps run in a temporary site root, and only the glossary plus newly
referenced immutable assets are copied back. No global orphan prune is run.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib, json, re, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import build_public_pages, externalize_css, inject_data_base, optimize_assets

E = ROOT / "mockups/evidence/container-edge-removal"
RECEIPTS = E / "glossary-output-repair"
EXPECTED = {"56c82507fa03af6576a3186facd03f37bac98f666c2c80ff0994a3002315202f", "d39252413987969a01dce89a41fcb9a1616012992c0765bdf62016b76320aff1"}
ASSETS = re.compile(r'\b(?:src|href)="([^"?#]+\.(?:css|js))(?:[?#][^"]*)?"')
BANNER = re.compile(r'<script[^>]*\bdata-whb\b[^>]*></script>')
STYLE = re.compile(r'<style\b[^>]*>(.*?)</style>', re.S)
SCRIPT = re.compile(r'<script\b[^>]*>.*?</script>', re.S)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    page = ROOT / "site/glossary.html"
    before_bytes = page.read_bytes()
    assert digest(before_bytes) in EXPECTED, "Exact input page changed; reconcile before applying"
    before = before_bytes.decode()
    banners = BANNER.findall(before)
    assert len(banners) == 1
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    copied = []
    with TemporaryDirectory(prefix="glossary-finalization-") as temporary:
        site = Path(temporary) / "site"
        site.mkdir()
        staged = site / "glossary.html"
        build_public_pages.build(site)
        raw = staged.read_text()
        named = sorted(set(ASSETS.findall(raw)) | set(ASSETS.findall(before)))
        for rel in named:
            if rel.startswith("//") or re.match(r"[a-zA-Z][\w+.-]*:", rel):
                continue
            src = ROOT / "site" / rel
            if src.is_file():
                dst = site / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                copied.append(rel)
        counts = {
            "inject_data_base": inject_data_base.inject(site),
            "externalize_css": externalize_css.externalize(site),
            "optimize_assets": optimize_assets.optimize(site),
        }
        after = staged.read_text()
        assert len(BANNER.findall(after)) == 1
        after = BANNER.sub(lambda _: banners[0], after)
        assert re.search(r'<main\b.*?</main>', before, re.S).group(0) == re.search(r'<main\b.*?</main>', after, re.S).group(0)
        normalize = lambda text: re.sub(r"\?v=[0-9a-f]{8}", "", text)
        assert [normalize(s) for s in SCRIPT.findall(before)] == [normalize(s) for s in SCRIPT.findall(after)]
        assert BANNER.findall(after) == banners
        assert not STYLE.findall(after)
        refs = sorted(set(ASSETS.findall(after)))
        asset_rows = []
        new_assets = []
        for rel in refs:
            if rel.startswith("//") or re.match(r"[a-zA-Z][\w+.-]*:", rel):
                continue
            staged_asset = site / rel
            target = ROOT / "site" / rel
            assert staged_asset.is_file(), rel
            data = staged_asset.read_bytes()
            if target.exists():
                assert target.read_bytes() == data, "Existing immutable asset changed: " + rel
            else:
                assert re.fullmatch(r"assets/(?:css|js)/[0-9a-f]{8}\.(?:css|js)", rel), rel
                assert Path(rel).stem == digest(data)[:8], rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                new_assets.append("site/" + rel)
            asset_rows.append({"path": "site/" + rel, "sha256": digest(data), "new": "site/" + rel in new_assets})
        style_digests = [digest(s.encode()) for s in STYLE.findall(raw)]
        # The canonical externalizer carries the exact style block bytes.
        for css_digest in style_digests:
            assert any(r["sha256"] == css_digest for r in asset_rows), css_digest
        page.write_text(after)
        RECEIPTS.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ".cache/glossary-output-repair/reproducer-before.log", RECEIPTS / "reproducer-before.log")
        receipt = {
            "schema": "mastermind.container_edge_glossary_finalization.v1",
            "parent_native_head": head,
            "published_candidate_head": "0d26e84a15a0578d15bc1521021676d547d2aaf2",
            "ci_run": 43032587201,
            "ci_job": 130564015541,
            "before_sha256": digest(before_bytes),
            "after_sha256": digest(after.encode()),
            "owners": {"build_public_pages": "temporary site root only", **counts},
            "main_content_identical": True,
            "script_tags_identical_except_cache_stamps": True,
            "banner_tag_identical": True,
            "style_bytes_preserved_in_hashed_assets": True,
            "remaining_inline_style_blocks": len(STYLE.findall(after)),
            "copied_named_assets": copied,
            "new_assets": new_assets,
            "referenced_assets": asset_rows,
            "scope": ["site/glossary.html"] + new_assets,
        }
        (RECEIPTS / "repair-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))

if __name__ == "__main__":
    main()
