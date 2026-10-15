"""Labeler tool: turn excerpt-only spans into byte-exact spans (stdlib only).

usage: python3 fill_spans.py BUNDLE_DIR DRAFT.json OUT.json

DRAFT.json is a label_return.v1 object in which each source_span may carry only
"excerpt" (the exact text you cite, copied from source.txt) and optionally
"occurrence" (1-based, default 1, which occurrence of that excerpt to cite).
This tool locates the excerpt in BUNDLE_DIR/source.txt, sets text_sha256,
segment_index, byte_start and byte_end, drops "occurrence", and writes OUT.json.
It never changes a value, an absence or an excerpt. Exit 2 with a message naming
the field when an excerpt is not found, the occurrence does not exist, or the
excerpt crosses a segment boundary; fix the excerpt and rerun.
"""
import json
import sys
from pathlib import Path


def main(bundle_dir, draft_path, out_path):
    bundle_dir = Path(bundle_dir)
    source = (bundle_dir / "source.txt").read_bytes()
    bundle = json.loads((bundle_dir / "bundle.json").read_text())
    segs = bundle["segments"]
    draft = json.loads(Path(draft_path).read_text())
    errors = []
    for name, entry in sorted(draft.get("fields", {}).items()):
        span = entry.get("source_span")
        if not span:
            continue
        excerpt = span.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt:
            errors.append(f"{name}: source_span needs a non-empty excerpt")
            continue
        want = int(span.pop("occurrence", 1))
        needle = excerpt.encode("utf-8")
        pos, k = -1, 0
        while k < want:
            pos = source.find(needle, pos + 1)
            if pos < 0:
                break
            k += 1
        if pos < 0:
            errors.append(f"{name}: excerpt occurrence {want} not found verbatim in source.txt")
            continue
        end = pos + len(needle)
        seg = next((s for s in segs if s["byte_start"] <= pos and end <= s["byte_end"]), None)
        if seg is None:
            errors.append(f"{name}: excerpt crosses a segment boundary; cite within one document")
            continue
        span.update({"text_sha256": bundle["source_sha256"], "segment_index": seg["segment_index"],
                     "byte_start": pos, "byte_end": end})
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 2
    Path(out_path).write_text(json.dumps(draft, indent=1, ensure_ascii=False) + "\n")
    print(f"ok {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:4]))
