"""Seat tool: build A6 labeling lane trees + packets + tars (no symlinks).

usage: python3 build_label_lanes.py REPO BUNDLES_DIR OUT_DIR N_BATCHES FAMILY:VINTAGE:PYTHON [...]
Batches are the same for every family: cases sorted by (template, case_id), dealt
round-robin, so each lane carries a template mix. Writes OUT_DIR/<lane>/tree,
OUT_DIR/<lane>.packet.txt, OUT_DIR/<lane>.tar and OUT_DIR/lanes.json.
"""
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path

A6 = "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A6_labeler"
COPY = [
    f"{A6}/annotation_guide.md",
    f"{A6}/labeler_packet.template.md",
    "contracts/news_impact/label_return.v1.schema.json",
    "contracts/news_impact/adjudication_record.v1.schema.json",
    "contracts/news_impact/news_impact_event.v1.schema.json",
    "engine/__init__.py",
    "engine/news_impact/__init__.py",
    "engine/news_impact/agreement.py",
]
HERE = Path(__file__).resolve().parent


def main():
    repo, bundles, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    n = int(sys.argv[4])
    fams = [a.split(":", 2) for a in sys.argv[5:]]
    tmpl = Path(os.environ.get("LABEL_TEMPLATE", HERE / "label_batch.template.txt")).read_text()
    cases = []
    for d in sorted(bundles.iterdir()):
        if (d / "bundle.json").is_file():
            b = json.loads((d / "bundle.json").read_text())
            assert b["case_id"] == d.name, d
            cases.append((b["template"], d.name))
    cases.sort()
    batches = [cases[i::n] for i in range(n)]
    out.mkdir(parents=True, exist_ok=True)
    lanes = []
    for fam, vintage, py in fams:
        for i, batch in enumerate(batches, 1):
            lane = f"W2_L_{fam}_{i:02d}"
            tree = out / lane / "tree"
            if tree.exists():
                shutil.rmtree(tree)
            for rel in COPY:
                dst = tree / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(repo / rel, dst)
            for t in ("fill_spans.py", "check_label.py"):
                (tree / "tools").mkdir(parents=True, exist_ok=True)
                shutil.copyfile(HERE / t, tree / "tools" / t)
            for _, cid in batch:
                (tree / "bundles" / cid).mkdir(parents=True)
                for f in ("source.txt", "bundle.json"):
                    shutil.copyfile(bundles / cid / f, tree / "bundles" / cid / f)
            (tree / "labels").mkdir()
            (tree / "work").mkdir()
            case_list = "\n".join(f"- {cid}  ({t})" for t, cid in batch)
            pkt = (tmpl.replace("{{LANE_ID}}", lane).replace("{{FAMILY_TOKEN}}", fam)
                   .replace("{{MODEL_VINTAGE}}", vintage).replace("{{PYTHON}}", py)
                   .replace("{{N_CASES}}", str(len(batch))).replace("{{CASE_LIST}}", case_list))
            assert "{{" not in pkt, lane
            (out / f"{lane}.packet.txt").write_text(pkt)
            for p in tree.rglob("*"):
                assert not p.is_symlink(), p
            with tarfile.open(out / f"{lane}.tar", "w") as tf:
                tf.add(tree, arcname=".")
            lanes.append({"lane": lane, "family": fam, "n": len(batch),
                          "cases": [cid for _, cid in batch]})
    (out / "lanes.json").write_text(json.dumps(lanes, indent=1) + "\n")
    print(json.dumps([(l["lane"], l["n"]) for l in lanes]))


if __name__ == "__main__":
    main()
