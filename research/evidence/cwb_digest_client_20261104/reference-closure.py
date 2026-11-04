from __future__ import annotations
import collections, hashlib, json, pathlib, subprocess, sys
from urllib.parse import urlsplit, unquote
ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(sys.argv[2]).resolve()
APPLY = len(sys.argv) > 3 and sys.argv[3] == "--apply"
BASELINE = pathlib.Path(sys.argv[4]) if APPLY else None
sys.path.insert(0, str(ROOT))
from lib.pages import _OPEN_TAG_RE, _SRC_ATTR_RE, _OUR_STAMP_RE, optimize_assets_text
from scripts.optimize_assets import paired_html_pages

SITE = ROOT / "site"
assets = {str((SITE / name).resolve()): name for name in ("account.js", "theme.js")}
versions = {name: hashlib.sha256((SITE / name).read_bytes()).hexdigest()[:8]
            for name in ("account.js", "theme.js")}
pairs = {str(t.relative_to(ROOT)): s for t, s in paired_html_pages(SITE)}
tracked = subprocess.check_output(["git", "ls-files", "-z", "site"], cwd=ROOT).decode().split("\0")
paths = sorted(set(p for p in tracked if p.endswith(".html")) | set(pairs))
counts = collections.Counter()
foreign = collections.Counter()
changed = []
all_refs = []

def sha(data):
    return hashlib.sha256(data).hexdigest()

def target_for(url, parent):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        return None
    path = unquote(parsed.path)
    target = (SITE / path.lstrip("/")) if path.startswith("/") else (parent / path)
    return assets.get(str(target.resolve()))

def neutral(text, parent):
    def tag(match):
        if match.group(1).lower() != "script":
            return match.group(0)
        attr = _SRC_ATTR_RE.search(match.group(2))
        if attr is None or attr.group(1).lower() != "src":
            return match.group(0)
        url = attr.group(2)
        if not target_for(url, parent) or (urlsplit(url).query and not _OUR_STAMP_RE.match(url)):
            return match.group(0)
        attrs = match.group(2)
        return "<" + match.group(1) + attrs[:attr.start()] + 'src="__OWNED_REFERENCE__"' + attrs[attr.end():] + ">"
    return _OPEN_TAG_RE.sub(tag, text)

def transform(text, parent):
    selected = []
    def tag(match):
        if match.group(1).lower() != "script":
            return match.group(0)
        attrs = match.group(2)
        attr = _SRC_ATTR_RE.search(attrs)
        if attr is None or attr.group(1).lower() != "src":
            return match.group(0)
        url = attr.group(2)
        name = target_for(url, parent)
        if not name:
            return match.group(0)
        stamp = _OUR_STAMP_RE.match(url)
        parsed = urlsplit(url)
        if parsed.query and not stamp:
            selected.append({"asset": name, "url": url, "disposition": "foreign_query_preserved"})
            return match.group(0)
        def hash_for(bare):
            resolved = target_for(bare, parent)
            return versions[resolved] if resolved else None
        optimized = optimize_assets_text(match.group(0), hash_for)
        normalized = _OPEN_TAG_RE.fullmatch(optimized)
        assert normalized is not None
        replacement = _SRC_ATTR_RE.search(normalized.group(2))
        assert replacement is not None
        new_url = replacement.group(2)
        assert target_for(new_url, parent) == name
        assert urlsplit(new_url).path == parsed.path
        assert urlsplit(new_url).query == "v=" + versions[name]
        # Take only the canonical owner's selected src attribute. Existing
        # execution attributes and all other markup stay byte-for-byte intact.
        new_attrs = attrs[:attr.start()] + replacement.group(0) + attrs[attr.end():]
        updated = "<" + match.group(1) + new_attrs + ">"
        neutral_before = "<" + match.group(1) + attrs[:attr.start()] + 'src="__OWNED_REFERENCE__"' + attrs[attr.end():] + ">"
        neutral_after = "<" + match.group(1) + new_attrs[:attr.start()] + 'src="__OWNED_REFERENCE__"' + new_attrs[attr.start()+len(replacement.group(0)):] + ">"
        assert neutral_before == neutral_after
        selected.append({"asset": name, "before": url, "after": new_url,
                         "disposition": "changed" if updated != match.group(0) else "current"})
        return updated
    return _OPEN_TAG_RE.sub(tag, text), selected

for rel in paths:
    path = ROOT / rel
    assert path.is_file(), rel
    raw = path.read_bytes()
    text = raw.decode()
    parent = pairs[rel].parent if rel in pairs else path.parent
    new, refs = transform(text, parent)
    for ref in refs:
        counts[ref["asset"] + ":" + ref["disposition"]] += 1
        if ref["disposition"] == "foreign_query_preserved":
            foreign[ref["asset"] + ":" + ref["url"]] += 1
    if refs:
        all_refs.append({"path": rel, "refs": refs})
    data = new.encode()
    assert neutral(text, parent) == neutral(new, parent), rel
    if data != raw:
        changed.append({"path": rel, "before_sha256": sha(raw), "after_sha256": sha(data),
                        "ref_count": len(refs), "neutral_sha256": sha(neutral(text, parent).encode())})
result = {"mode": "DRY_RUN_NO_HTML_WRITES", "base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
          "versions": versions, "scanned_html_files": len(paths), "changed_paths": len(changed),
          "selected_reference_counts": dict(counts), "foreign_queries": dict(foreign),
          "changes": changed, "references": all_refs, "source_pairs": sorted(pairs)}
if APPLY:
    expected = json.loads(BASELINE.read_text())
    assert expected["base"] == result["base"] == "7b3a8d4049fa00f3e498589b5468e82a2d2dc0a3"
    assert expected["versions"] == result["versions"]
    assert expected["references"] == result["references"]
    assert [{k: c[k] for k in ("path", "before_sha256", "after_sha256", "ref_count")} for c in changed] == expected["changes"]
    assert not foreign, foreign
    result["mode"] = "APPLY_VALIDATED"
    result["baseline_sha256"] = sha(BASELINE.read_bytes())
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    for item in changed:
        p = ROOT / item["path"]
        raw = p.read_bytes()
        assert sha(raw) == item["before_sha256"], item["path"]
        parent = pairs[item["path"]].parent if item["path"] in pairs else p.parent
        new, refs = transform(raw.decode(), parent)
        assert sha(new.encode()) == item["after_sha256"], item["path"]
        p.write_bytes(new.encode())
    for rel in paths:
        p = ROOT / rel
        raw = p.read_bytes()
        parent = pairs[rel].parent if rel in pairs else p.parent
        repeat, _ = transform(raw.decode(), parent)
        assert repeat.encode() == raw, rel
    result["mode"] = "APPLIED_COMPLETE"
    result["fixed_point"] = True
    result["unchanged_except_selected_src_attributes"] = True
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k not in ("changes", "references")} |
                 {"receipt": str(OUT), "receipt_sha256": sha(OUT.read_bytes())}))
