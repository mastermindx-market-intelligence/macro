"""Reapply the previously accepted presentation to the current scheduled render.

Uses the original exact-match catalog and cached projection implementation.
No collector, broad CSS rewrite, or direct-source repair is replayed.
"""
from pathlib import Path
import hashlib, json, re, subprocess

R = Path.cwd()
E = R / "mockups/evidence/container-edge-removal"
D = E / "integration-render-refresh"
MAIN = "43b5acdb0d0f264091f5aa33c129625fd0b28b8c"
HEAD = "bac05c4c15f648acb845a67caa54a7103b28fa6b"

def git(*args):
    return subprocess.check_output(["git", *args])

def digest(b):
    return hashlib.sha256(b).hexdigest()

assert git("rev-parse", "HEAD").decode().strip() == HEAD
assert git("rev-parse", "MERGE_HEAD").decode().strip() == MAIN
assert not git("diff", "--name-only", "--diff-filter=U").strip()
D.mkdir(exist_ok=True)
mapping = json.loads((E / "integration/combined-renames.json").read_text())
resolved = {}
for old in mapping:
    target = mapping[old]
    seen = {old}
    while target in mapping and mapping[target] != target:
        assert target not in seen, (old, target)
        seen.add(target)
        target = mapping[target]
    assert (R / "site" / target).is_file(), target
    resolved[old] = target

asset_ref = re.compile(r"(assets/(?:css|js)/[0-9a-f]{8}\.(?:css|js))(?:\?v=([0-9a-f]{8}))?")
rebindings = []
for page in (R / "site").rglob("*.html"):
    before = page.read_text()
    def replace(match):
        old, stamp = match.groups()
        if old not in resolved:
            return match[0]
        target = resolved[old]
        if stamp == Path(old).stem:
            stamp = Path(target).stem
        return target + ("?v=" + stamp if stamp else "")
    after = asset_ref.sub(replace, before)
    if before != after:
        page.write_text(after)
        rebindings.append({
            "path": str(page.relative_to(R)),
            "before_sha256": digest(before.encode()),
            "after_sha256": digest(after.encode()),
        })
subprocess.run(["git", "add", "--", "site"], check=True)
tree = git("write-tree").decode().strip()
(D / "prepared-projection.json").write_text(json.dumps({
    "input_tree": tree,
    "main": MAIN,
    "accepted_reference": HEAD,
    "state": "Complete prepared merge input; no interrupted projection exists",
}, indent=2) + "\n")
(D / "historical-asset-rebinding.json").write_text(json.dumps({
    "main": MAIN,
    "accepted_reference": HEAD,
    "mapping_source": "integration/combined-renames.json",
    "mapping_sha256": digest((E / "integration/combined-renames.json").read_bytes()),
    "resolved_renames": resolved,
    "changes": rebindings,
}, indent=2) + "\n")
print(json.dumps({"historical_asset_rebound_pages": len(rebindings), "prepared_tree": tree}), flush=True)

recipe = E / "project_integrated_consumers.py"
code = recipe.read_text()
def replace_once(old, new):
    global code
    assert code.count(old) == 1, (old[:80], code.count(old))
    code = code.replace(old, new)

replace_once("I=E/'integration'", "I=E/'integration-render-refresh'")
replace_once("MAIN='c58c69bf42786f29c8857550bdb244d08da35240'", "MAIN='" + MAIN + "'")
assert code.count("97abae6fa8f17bdb71f8670d59d1ba43497e3ae7") == 2
code = code.replace("97abae6fa8f17bdb71f8670d59d1ba43497e3ae7", HEAD)
replace_once("(I/'partial-projection-checkpoint.json')", "(I/'prepared-projection.json')")
replace_once("(E/'integration/consumer-projection-receipt.json')", "(E/'integration-render-refresh/consumer-projection-receipt.json')")
replace_once(
    "Matches and changed entries cover this resumed pass only. Seven earlier page mutations are separately byte-bound in partial-projection-checkpoint.json; no interrupted-run rule totals are asserted.",
    "Complete pass over the prepared current-main merge; unchanged accepted blobs are reused only with exact page and asset bindings."
)
replace_once("record['partial_projection_checkpoint']='partial-projection-checkpoint.json'", "record['prepared_projection_checkpoint']='prepared-projection.json'")
(D / "projection-owner-binding.json").write_text(json.dumps({
    "source_recipe": str(recipe.relative_to(R)),
    "source_recipe_sha256": digest(recipe.read_bytes()),
    "adapted_recipe_sha256": digest(code.encode()),
    "main": MAIN,
    "accepted_reference": HEAD,
    "changes": ["explicit refs", "new receipt paths", "prepared input tree", "complete-pass accounting"],
}, indent=2) + "\n")
exec(compile(code, str(recipe), "exec"), {"__name__": "__main__", "__file__": str(recipe)})
