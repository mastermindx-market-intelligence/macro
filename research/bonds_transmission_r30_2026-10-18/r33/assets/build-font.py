"""Rebuild the licensed offline CJK subset from the exact upstream OTF."""
from pathlib import Path
import hashlib
import json
import sys
from fontTools import subset
from fontTools.ttLib import TTFont

root = Path(__file__).resolve().parent.parent
source = Path(sys.argv[1])
expected = "2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b"
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
inputs = [root / "source-inspector.js", root / "source-adapter.js", root.parent / "r32/reference/index.html"]
codepoints = sorted({ord(c) for p in inputs for c in p.read_text() if ord(c) > 127})
font = TTFont(source, recalcTimestamp=False)
unavailable = [p for p in codepoints if p not in font.getBestCmap()]
assert not [p for p in unavailable if 0x3400 <= p <= 0x9fff], "Missing Chinese UI glyph"
options = subset.Options()
options.name_IDs = ["*"]
options.name_legacy = True
options.name_languages = ["*"]
subsetter = subset.Subsetter(options=options)
subsetter.populate(unicodes=codepoints)
subsetter.subset(font)
names = {1:"Mastermind Source CJK Subset", 2:"Regular", 3:"MastermindSourceCJKSubset-Regular", 4:"Mastermind Source CJK Subset", 6:"MastermindSourceCJKSubset-Regular", 16:"Mastermind Source CJK Subset", 17:"Regular"}
for record in font["name"].names:
    if record.nameID in names:
        record.string = names[record.nameID].encode(record.getEncoding())
font.flavor = "woff"
target = root / "assets/source-cjk-subset.woff"
font.save(target)
report = {
    "source_url":"https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf",
    "source_sha256":expected,
    "subset_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
    "subset_bytes":target.stat().st_size,
    "requested_codepoints":len(codepoints),
    "unavailable_non_cjk_codepoints":unavailable,
    "license":"SIL Open Font License 1.1",
    "name":"Mastermind Source CJK Subset",
    "use":"Offline reference UI glyphs only; system fallback handles other imported text",
    "rebuild":"python3 r33/assets/build-font.py <verified-upstream-OTF>"
}
(root / "assets/font-provenance.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report))
