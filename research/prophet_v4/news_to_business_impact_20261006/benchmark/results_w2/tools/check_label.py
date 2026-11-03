"""Labeler/seat tool: validate one label_return.v1 against its bundle.

usage (from the repository tree root):
  PYTHONPATH=. python3 check_label.py BUNDLE_DIR LABEL.json

Runs engine.news_impact.agreement.parse_label_return (schema + forbidden keys) and
replay_return_spans (byte-exact span replay against BUNDLE_DIR/source.txt with the
bundle's segments). Prints one JSON line {"ok": bool, ...}; exit 0 only when the return
parses, every span replays, case_id and template match the bundle.
"""
import json
import sys
from pathlib import Path

from engine.news_impact.agreement import AgreementError, parse_label_return, replay_return_spans


def check(bundle_dir, label_path):
    bundle_dir = Path(bundle_dir)
    bundle = json.loads((bundle_dir / "bundle.json").read_text())
    source = (bundle_dir / "source.txt").read_bytes()
    try:
        record = json.loads(Path(label_path).read_text())
    except (OSError, ValueError) as exc:
        return {"ok": False, "stage": "json", "error": str(exc)[:300]}
    try:
        parsed = parse_label_return(record)
    except AgreementError as exc:
        return {"ok": False, "stage": "parse", "code": exc.code, "error": exc.message[:600]}
    problems = []
    if parsed.case_id != bundle["case_id"]:
        problems.append(f"case_id {parsed.case_id!r} != bundle {bundle['case_id']!r}")
    if parsed.template != bundle["template"]:
        problems.append(f"template {parsed.template!r} != bundle {bundle['template']!r}")
    segs = [{k: s[k] for k in ("segment_index", "byte_start", "byte_end")} for s in bundle["segments"]]
    rep = replay_return_spans(parsed, source, bundle["source_sha256"], segs)
    ok = not problems and rep["n_failed"] == 0
    return {"ok": ok, "stage": "replay", "problems": problems, "replay": rep}


if __name__ == "__main__":
    res = check(sys.argv[1], sys.argv[2])
    print(json.dumps(res, sort_keys=True))
    raise SystemExit(0 if res["ok"] else 1)
