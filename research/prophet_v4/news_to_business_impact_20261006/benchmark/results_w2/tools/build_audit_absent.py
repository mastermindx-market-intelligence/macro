"""Seat tool: addendum audit stratum over the slots both families marked ABSENT.
usage: python3 build_audit_absent.py SCRATCH_W2 OUT_DIR            (draw sample + write cards)
       python3 build_audit_absent.py SCRATCH_W2 --control           (window recall on agreed values)
Adds strata the w2 audit (seed 20261014) left unaudited; it never redraws that audit.
Seed 20261015, rows sorted by (case_id, field) before sampling:
  agree_absent 20 (of 129), absent_reason_differs 6 (all 6).
Each card shows both absences plus every keyword window in the body for the slot, so a
shared miss (a value both families failed to find) is visible to the judge.
--control is the positive control: on the 40 agree_present slots (a value both families found
and whose span replays), it reports how many agreed spans fall inside a window the card would
show. A window procedure that misses agreed values cannot certify an absence.
The cards quote filing text: they are scratch-only and are never committed.
"""
import json, random, re, sys
from pathlib import Path

STRATA = [("agree_absent", 20), ("absent_reason_differs", 6)]
SEED = 20261015
ISSUANCE = r"|offering|offered|issued|issuance|notes due|senior notes|principal amount|facility|term loan|credit agreement|proceeds|commitment|consideration|sold"
KW = {
    "incremental_amount": r"authori[sz]|repurchase|buyback|buy-back|increase[sd]? (?:the|its)|dividend|targeting" + ISSUANCE,
    "remaining_authorization": r"remain|available|capacity|left under|outstanding under|authori[sz]",
    "executed_amount": r"repurchased|bought back|purchased|repurchases of|returned .{0,40}(?:share|stockholder|shareholder)|offering price|aggregate principal|closed|completed" + ISSUANCE,
    "stated_amount": r"\$\s?\d|guidance|outlook|expect|anticipate|range|target",
    "stated_quantity": r"\$\s?\d|aggregate|valued|consideration|principal amount|purchase price",
}
MONEY = re.compile(r"[$£€]\s?\d[\d,.]*\s*(?:million|billion|thousand|[mbk]\b)?|\d[\d,.]*\s*(?:million|billion)\b|\d{1,3}(?:,\d{3})+\s+(?:shares|of (?:its|the|our))", re.I)
PAD, CAP = 200, 12


def spans(text, field):
    """Character ranges [a, b) of keyword windows that contain a number; overlapping windows merge."""
    out = []
    for m in re.finditer(KW[field], text, re.I):
        a, b = max(0, m.start() - PAD), min(len(text), m.end() + PAD)
        if not MONEY.search(text[a:b]):
            continue
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def load(w2, cid, fam):
    return json.loads((w2 / "labels_canon_full" / f"{cid}.{fam}.json").read_text())


def body(w2, cid):
    return (w2 / "bundles_graded" / cid / "source.txt").read_bytes()


def control(w2):
    rows = [json.loads(l) for l in open(w2 / "score" / "critical_slots.jsonl")]
    hit = miss = 0
    for r in rows:
        if r["class"] != "agree_present":
            continue
        raw = body(w2, r["case_id"])
        text = raw.decode("utf-8", "replace")
        sp = load(w2, r["case_id"], "fam_a")["fields"][r["field"]].get("source_span") or {}
        c0 = len(raw[: sp.get("byte_start", 0)].decode("utf-8", "replace"))
        c1 = len(raw[: sp.get("byte_end", 0)].decode("utf-8", "replace"))
        ws = spans(text, r["field"])[:CAP]
        if any(a <= c0 and c1 <= b for a, b in ws):
            hit += 1
        else:
            miss += 1
            print(f"MISS {r['case_id']} {r['template']} {r['field']} windows={len(ws)} excerpt={sp.get('excerpt','')[:90]!r}")
    print(f"control agree_present: hit {hit} miss {miss}")


def absent(entry):
    ta = entry.get("typed_absence")
    if isinstance(ta, dict):
        ev = ta.get("evidence") or {}
        return f"ABSENT reason={ta.get('reason')} note={str(ta.get('note') or ev.get('note') or '')[:120]}"
    return f"RAW value={json.dumps(entry.get('value'))[:160]}"


def cards(w2, out):
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(w2 / "score" / "critical_slots.jsonl")]
    rng = random.Random(SEED)
    sample = []
    for cls, n in STRATA:
        pool = sorted((r for r in rows if r["class"] == cls), key=lambda r: (r["case_id"], r["field"]))
        pick = rng.sample(pool, min(n, len(pool)))
        sample += sorted(pick, key=lambda r: (r["case_id"], r["field"]))
    meta, lines = [], []
    for i, r in enumerate(sample, 1):
        cid, f = r["case_id"], r["field"]
        text = body(w2, cid).decode("utf-8", "replace")
        ent = {fam: load(w2, cid, fam)["fields"].get(f) or {} for fam in ("fam_a", "fam_b")}
        meta.append({"n": i, "case_id": cid, "field": f, "template": r["template"], "class": r["class"], "fold": r["fold"]})
        ws = spans(text, f)
        lines.append(f"=== A{i} {cid} {r['template']} {f} [{r['class']}] body_chars={len(text)}")
        for fam in ("fam_a", "fam_b"):
            lines.append(f"  {fam}: {absent(ent[fam])}")
        lines.append(f"  keyword hits={len(re.findall(KW[f], text, re.I))}; windows with a number: {len(ws)} (showing {min(len(ws), CAP)})")
        for j, (a, b) in enumerate(ws[:CAP], 1):
            snip = re.sub(r"\s+", " ", text[a:b])
            lines.append(f"   [{j}] {snip}")
    (out / "sample_absent.json").write_text(json.dumps({"seed": SEED, "strata": STRATA, "cards": meta}, indent=1) + "\n")
    chunks, cur, size = [], [], 0
    for ln in lines:
        if ln.startswith("=== ") and size > 9000:
            chunks.append(cur); cur, size = [], 0
        cur.append(ln); size += len(ln)
    if cur:
        chunks.append(cur)
    for old in out.glob("batch_absent_*.txt"):
        old.unlink()
    for j, ch in enumerate(chunks, 1):
        (out / f"batch_absent_{j}.txt").write_text("\n".join(ch) + "\n")
    print(len(meta), "cards,", len(chunks), "batches")


if __name__ == "__main__":
    w2 = Path(sys.argv[1])
    if sys.argv[2] == "--control":
        control(w2)
    else:
        cards(w2, Path(sys.argv[2]))
