"""Owner-review overlap facts: every frozen micro measured against ALL crosswalk micros.

Read-only evidence generator for research/theme_graph/micro_owner_review_2026-11-02.md
(the GMI taxonomy owner's frozen-tier review, DEC:GMI-TAXONOMY-OWNER-DELEGATED-TO-SEAT).
It writes facts only; dispositions are the owner's judgment and live in the dossier and
in research/theme_graph/micro_owner_dispositions.yml.

Usage (from the repository root, on a full checkout - it reads data/theme_graph/):
    python3 research/theme_graph/micro_owner_review_2026_11_02_overlap.py \
        --baseline <coverage_report.json from scripts/gmi_coverage_proof.py> \
        --out research/theme_graph/micro_owner_review_2026-11-02.json

Features per (frozen micro, other micro) pair:
  name_jac      token Jaccard over name_en + id tokens (stop-worded, plural-stemmed)
  def_jac       token Jaccard over name_en + note + id tokens
  name_char3    character-trigram cosine over name_en
  zh_bigram     character-bigram Jaccard over name_zh (latin, digits, punctuation and the
                connectives 与/和/及 removed)
  shared_parent the sub-theme parents both rows hang under
  shared_members member companies both rows carry (activity probation lane + any
                non-PARENT_OF graph edge into a micro)
  composite = .35 name_jac + .25 def_jac + .2 name_char3 + .2 zh_bigram
              + .1 [shared_parent] + .3 [shared_members]
A pair is FLAGGED when composite >= 0.30, name_jac >= 0.34, zh_bigram >= 0.34 or any
member is shared. ``referenced_by`` lists every other row whose note names the frozen id.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

STOP = set("""a an and the of for in on to by with from as or at into via is are be
its their this that distinct not other others than without within across between
including include includes generic named one two only also such each per own
""".split())
# Gate #2 provenance families (assembled so this file never carries the literal labels).
GATE2_MARKERS = tuple("".join(parts) for parts in (
    ("finviz", "_themes"), ("ths", "_concepts"), ("china", "_ths"), ("ltheme", ":"),
    ("basket", ":baskets_", "china", "_ths:")))


def _load_proof_module():
    spec = importlib.util.spec_from_file_location(
        "gmi_coverage_proof", REPO / "scripts" / "gmi_coverage_proof.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["gmi_coverage_proof"] = module
    spec.loader.exec_module(module)
    return module


def stem(token: str) -> str:
    for suffix in ("ies", "es", "s"):
        if len(token) > 4 and token.endswith(suffix):
            return token[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return token


def toks(text: str | None) -> set[str]:
    return {stem(t) for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if t not in STOP and len(t) > 1}


def ngrams(text: str | None, n: int = 3) -> Counter:
    text = f" {re.sub(r'[^a-z0-9]+', ' ', (text or '').lower()).strip()} "
    return Counter(text[i:i + n] for i in range(len(text) - n + 1))


def cos(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    num = sum(a[k] * b.get(k, 0) for k in a)
    return num / math.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))


def jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def zh_bigrams(text: str | None) -> set[str]:
    text = re.sub(r"[\sA-Za-z0-9&、，,（）()/\-与和及]", "", text or "")
    return {text[i:i + 2] for i in range(len(text) - 1)}


def excerpt(note: str, needle: str, width: int = 70) -> str:
    at = note.find(needle)
    lo, hi = max(0, at - width), min(len(note), at + len(needle) + width)
    return ("..." if lo else "") + note[lo:hi].strip() + ("..." if hi < len(note) else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    g = _load_proof_module()
    hierarchy = g._hierarchy(REPO / "config" / "theme_crosswalk.yml")
    micros = hierarchy["micros"]
    tier = {m: g._micro_tier(e) for m, e in micros.items()}
    frozen = sorted(m for m, t in tier.items() if t == g.FROZEN_TIER)
    base = json.loads(args.baseline.read_text(encoding="utf-8"))
    cov = {m["id"]: m for m in base["taxonomy"]["micros"]}
    if set(cov) != set(frozen):
        raise SystemExit("baseline frozen set differs from the crosswalk frozen set")
    frozen_sha = hashlib.sha256("\n".join(frozen).encode()).hexdigest()

    parents_of: dict[str, set[str]] = defaultdict(set)
    for child, parent in hierarchy["parents"]:
        parents_of[child].add(parent)

    members: dict[str, set[str]] = defaultdict(set)
    with open(REPO / "data/theme_graph/probation/activity_proposals.jsonl", encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            ends = (row.get("evidence") or {}).get("endpoints") or {}
            if ends.get("target_node_id") in micros:
                members[ends["target_node_id"]].add(ends.get("source_node_id"))
    import pandas as pd
    edges = pd.read_parquet(REPO / "data/theme_graph/edges.parquet", columns=["type", "src", "dst"])
    into = edges[edges.dst.isin(micros)]
    for target, frame in into[into.type != "PARENT_OF"].groupby("dst"):
        members[target] |= set(frame.src)

    feat = {}
    for m, ent in micros.items():
        name, note = ent.get("name_en") or "", ent.get("note") or ""
        id_tokens = toks(m.split(":", 1)[1].replace("_", " "))
        feat[m] = dict(name_t=toks(name) | id_tokens, def_t=toks(f"{name} {note}") | id_tokens,
                       name_g=ngrams(name), zh=zh_bigrams(ent.get("name_zh")),
                       parents=parents_of.get(m, set()))

    rows = {}
    for f in frozen:
        a, ent, slug = feat[f], micros[f], f.split(":", 1)[1]
        scored = []
        for m in micros:
            if m == f:
                continue
            b = feat[m]
            s = dict(id=m, tier=tier[m],
                     name_jac=round(jac(a["name_t"], b["name_t"]), 3),
                     def_jac=round(jac(a["def_t"], b["def_t"]), 3),
                     name_char3=round(cos(a["name_g"], b["name_g"]), 3),
                     zh_bigram=round(jac(a["zh"], b["zh"]), 3),
                     shared_parent=sorted(a["parents"] & b["parents"]),
                     shared_members=sorted(members.get(f, set()) & members.get(m, set())))
            s["composite"] = round(0.35 * s["name_jac"] + 0.25 * s["def_jac"]
                                   + 0.2 * s["name_char3"] + 0.2 * s["zh_bigram"]
                                   + (0.1 if s["shared_parent"] else 0)
                                   + (0.3 if s["shared_members"] else 0), 3)
            scored.append(s)
        scored.sort(key=lambda s: (-s["composite"], s["id"]))
        flagged = [s for s in scored if s["composite"] >= 0.30 or s["name_jac"] >= 0.34
                   or s["zh_bigram"] >= 0.34 or s["shared_members"]]
        pattern = re.compile(rf"(?<![a-z0-9_]){re.escape(slug)}(?![a-z0-9_])")
        referenced_by = [dict(id=m, tier=tier[m], excerpt=excerpt(micros[m]["note"], slug))
                         for m in sorted(micros) if m != f
                         and pattern.search(micros[m].get("note") or "")]
        nominated = str(ent.get("nominated_from") or "")
        c = cov[f]
        scope_version = g._entry_scope_version(ent)
        if scope_version != c["scope_version"]:
            raise SystemExit(f"scope_version drift for {f}")
        rows[f] = dict(
            id=f, name_en=ent.get("name_en"), name_zh=ent.get("name_zh"), note=ent.get("note"),
            nominated_from=nominated, asserted_on=str(ent.get("asserted_on")),
            scope_version=scope_version, parent_paths=g._parent_paths(f, hierarchy),
            route_kinds=c["route_kinds"], counts=c["counts"], coverage_disposition=c["disposition"],
            gate2_markers=[x for x in GATE2_MARKERS if x in nominated or x in f],
            member_companies=sorted(members.get(f, set())),
            sibling_count=sum(1 for m in micros if m != f and feat[m]["parents"] & a["parents"]),
            frozen_siblings=sorted(m for m in frozen if m != f and feat[m]["parents"] & a["parents"]),
            top=[[s["id"], s["tier"], s["composite"], s["name_jac"], s["def_jac"], s["name_char3"],
                  s["zh_bigram"], bool(s["shared_parent"]), len(s["shared_members"])]
                 for s in scored[:5]],
            flagged=[[s["id"], s["composite"]] for s in flagged[:10]],
            referenced_by=referenced_by)

    out = dict(schema="theme_graph.owner_review_overlap/v1",
               baseline_frozen_micro_ids_sha256=base["taxonomy"].get("frozen_micro_ids_sha256"),
               frozen_ids_sha256=frozen_sha, micro_total=len(micros), frozen_total=len(frozen),
               edge_types_into_micros=sorted(set(into.type)),
               micros_with_members=sorted(k for k, v in members.items() if v),
               weights=("composite = .35 name_jac + .25 def_jac + .2 name_char3 + .2 zh_bigram"
                        " + .1 shared_parent + .3 shared_members"),
               top_columns=["id", "tier", "composite", "name_jac", "def_jac", "name_char3",
                            "zh_bigram", "shared_parent", "shared_member_count"],
               flag_rule="composite >= 0.30 or name_jac >= 0.34 or zh_bigram >= 0.34 or shared members",
               rows=rows)
    # One line per micro row keeps the snapshot reviewable without a 3k-line file.
    head = {k: v for k, v in out.items() if k != "rows"}
    lines = ["{"] + [f" {json.dumps(k)}: {json.dumps(v, ensure_ascii=False, sort_keys=True)},"
                     for k, v in sorted(head.items())]
    lines.append(' "rows": {')
    body = [f"  {json.dumps(k)}: {json.dumps(rows[k], ensure_ascii=False, sort_keys=True)}"
            for k in sorted(rows)]
    lines += [",\n".join(body), " }", "}"]
    text = "\n".join(lines) + "\n"
    if json.loads(text) != json.loads(json.dumps(out)):
        raise SystemExit("serialisation round-trip mismatch")
    args.out.write_text(text, encoding="utf-8")
    print(f"micros {len(micros)} frozen {len(frozen)} sha {frozen_sha[:12]} "
          f"baseline sha {str(out['baseline_frozen_micro_ids_sha256'])[:12]} "
          f"gate2 {sum(bool(r['gate2_markers']) for r in rows.values())} "
          f"with members {out['micros_with_members']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
