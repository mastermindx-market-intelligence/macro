"""Replay the retained editorial candidate through existing Press checks.

Research evidence only: this does not create a planner slot, stage record,
Chronicle event, provider request, publication, or rights approval. The context
below is an explicitly unadmitted validation input, never a writer input.
Run from the repository root with python3 <this file>.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine.press import desk_planner, validators
from lib.pages import rendered_ticker_pages

HERE = Path(__file__).resolve().parent


def bound_file(path: str, expected: str) -> bytes:
    p = (ROOT / path).resolve()
    if not p.is_relative_to(HERE):
        raise ValueError("Candidate evidence must remain in its retained directory")
    b = p.read_bytes()
    if hashlib.sha256(b).hexdigest() != expected:
        raise ValueError(f"Retained evidence changed: {path}")
    return b


def replay(peer_root: Path | None = None) -> dict:
    receipt_bytes = (HERE / "whitehouse_event_source_receipt.json").read_bytes()
    receipt = json.loads(receipt_bytes)
    retained = receipt["retained_public_source"]
    source = json.loads(bound_file(retained["path"], retained["sha256"]))
    bound_file(retained["policy_path"], retained["policy_file_sha256"])
    draft_record = receipt["draft"]
    md = bound_file(draft_record["path"], draft_record["sha256"]).decode()
    if hashlib.sha256(source["body"].encode()).hexdigest() != retained["body_sha256"]:
        raise ValueError("Source body hash mismatch")
    if source["url"] != receipt["existing_feed_ingress"]["candidate"]["url"]:
        raise ValueError("Source identity mismatch")
    body = md.split("\n---\n")[1].strip()
    # Retain every prose word. Only turn the candidate's simple Markdown links
    # and paragraphs into the HTML shape consumed by the existing validators.
    def paragraph(text):
        escaped = html.escape(" ".join(text.split()))
        return "<p>" + re.sub(r"\[([^]]+)\]\((https://[^)]+)\)",
                               r'<a href="\2">\1</a>', escaped) + "</p>"
    draft = {"title": md.splitlines()[0].removeprefix("# "),
             "body_html": "\n".join(paragraph(p) for p in body.split("\n\n"))}
    source_ref = "whitehouse:" + source["id"]
    # This is the closed set reviewed in the source receipt, not every number
    # in the full government document. Values remain third_party, including
    # arithmetic derived exclusively from the external source.
    facts = []
    for text, values in [
        ("NVIDIA ($1B)", ["1 billion"]),
        ("$2.4B in SI for science tools and compute credits", ["2.4 billion"]),
        ("eleven industry partners", ["11"]),
        ("over 15 Federal agencies", ["15"]),
        ("AMD ($500M)", ["500 million"]),
        ("OpenAI ($200M)", ["200 million"]),
        ("$150M each from Anthropic and Google", ["150 million"]),
        ("over $6 billion", ["6 billion"]),
    ]:
        if text not in source["body"]:
            raise ValueError("Reviewed fact is absent from retained source")
        facts.append({"text": text, "values": values, "tier": "third_party",
                      "ref": source_ref, "dated": receipt["event_date"]})
    derived = (1 + .5) / 2.4 * 100
    if derived != receipt["derived_checks"]["approximate_share_pct"]:
        raise ValueError("Reviewed arithmetic differs")
    facts.append({"text": f"NVIDIA and AMD commitments together represent approximately {derived}% of the stated package.",
                  "values": [str(derived)], "tier": "third_party", "ref": source_ref,
                  "dated": receipt["event_date"], "derived_from_external": True})
    cfg = desk_planner.load_config(ROOT)
    desk = cfg["desks"]["brief"]
    url = "https://www.mastermind-x.com/stocks/NVDA.html"
    if "NVDA" not in rendered_ticker_pages(ROOT / "site"):
        raise ValueError("NVIDIA dossier is not present in the rendered estate")
    context = {"desk": "brief", "publication": desk["publication"],
               "byline": desk["byline"], "as_of": receipt["observed_at"][:10],
               "min_words": desk["min_words"],
               "max_words": desk["max_words"],
               "min_anchored_receipts": desk["min_anchored_receipts"],
               "facts": facts, "raw_documents": [{"ref": source_ref, "text": source["body"]}],
               "primary_source": {"kind": "external", "name": "The White House", "url": source["url"]},
               "allowed_links": [url]}
    # Full suite is intentionally allowed to report missing publishing metadata
    # and furniture. This candidate is not silently upgraded into a Press draft.
    peer_root = (peer_root or ROOT).resolve()
    peer_inputs = {}
    paths = cfg.get("paths") or {}
    staging = peer_root / str(paths.get("staging_dir") or "data/press/staging")
    for p in sorted(staging.glob("*.json")):
        if not p.name.startswith("_"):
            peer_inputs[str(p.relative_to(peer_root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    ledger = peer_root / str(paths.get("ledger") or "data/press/published.jsonl")
    if ledger.is_file():
        peer_inputs[str(ledger.relative_to(peer_root))] = hashlib.sha256(ledger.read_bytes()).hexdigest()
    report = validators.validate(draft, context, cfg, root=peer_root)
    return {"kind": "unadmitted_editorial_candidate_replay",
            "tested_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "peer_root": str(peer_root), "peer_input_hashes": peer_inputs,
            "config_sha256": hashlib.sha256((ROOT / "config/press.yml").read_bytes()).hexdigest(),
            "validator_sha256": hashlib.sha256((ROOT / "engine/press/validators.py").read_bytes()).hexdigest(),
            "draft_sha256": draft_record["sha256"], "source_sha256": retained["sha256"],
            "validator_report": report, "press_admitted": False, "allow_stage": False,
            "allow_emit": False, "publication_approved": False,
            "d14_generated_batch_credit": False,
            "scope": "Offline replay against retained source and current local corpus; not current upstream source/rights verification or planner admission."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--peer-root", type=Path, help="Read-only existing stage/ledger corpus for overlap checks")
    args = parser.parse_args()
    print(json.dumps(replay(args.peer_root), ensure_ascii=False, indent=2))
