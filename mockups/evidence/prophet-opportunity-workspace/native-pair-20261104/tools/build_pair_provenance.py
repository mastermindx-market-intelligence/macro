"""Derive the native-pair provenance receipt from the workspace it describes.

Every number in the output is READ from the workspace at run time; nothing is
typed in by hand. Re-running this on the same tree reproduces the same bytes.

Usage:
    python3 build_pair_provenance.py --workspace <ws> --source-head <sha> \\
        --build-receipt <build.json> --publication-pair <publication-pair.json> \\
        --render <render/observations.json> --output <pair-provenance.json>
"""
from __future__ import annotations

from pathlib import Path
import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys

from bs4 import BeautifulSoup

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--workspace", required=True, type=Path)
parser.add_argument("--source-head", required=True)
parser.add_argument("--build-receipt", required=True, type=Path)
parser.add_argument("--publication-pair", required=True, type=Path)
parser.add_argument("--render", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()

ROOT = args.workspace.resolve()
HEAD = args.source_head
sys.path.insert(0, str(ROOT))

assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == HEAD


def sha(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def side(path: Path) -> dict:
    raw = path.read_bytes()
    doc = json.loads(raw)
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "as_of": doc.get("as_of"),
        "emit": doc.get("emit"),
        "eligible": doc.get("eligible"),
    }


board_path = ROOT / "site/factordata/us_standouts.json"
gate_path = ROOT / "site/factordata/signal_gate.json"
board = side(board_path)
gate = side(gate_path)

# ── coherence, from the repository's own guard ──────────────────────────────
coherence = subprocess.run(
    [sys.executable, "scripts/check_signal_gate_coherence.py",
     str(board_path), str(gate_path)],
    cwd=ROOT, capture_output=True, text=True)
coherence_out = (coherence.stdout + coherence.stderr).strip()

# ── board-contradictions, the other diff-gated CI guard ─────────────────────
contradictions = subprocess.run(
    [sys.executable, "scripts/check_board_contradictions.py", str(board_path)],
    cwd=ROOT, capture_output=True, text=True)

# ── index / Plan source consumer ────────────────────────────────────────────
index_path = ROOT / "site/prophet/index.json"
index = json.loads(index_path.read_text())
snapshot_rel = index.get("source_board_snapshot_path", "")
snapshot_path = ROOT / snapshot_rel
snapshot_ok = False
snapshot_decompressed_sha = None
if snapshot_path.exists():
    decompressed = gzip.decompress(snapshot_path.read_bytes())
    snapshot_decompressed_sha = hashlib.sha256(decompressed).hexdigest()
    snapshot_ok = snapshot_decompressed_sha == board["sha256"]

# ── protected/public separation, measured on the bytes ──────────────────────
page_bytes = (ROOT / "site/us_stocks.html").read_bytes()
page = BeautifulSoup(page_bytes, "html.parser")
payload = json.loads((ROOT / "site/premiumdata/us_stocks.json").read_text())
public_root = b"".join(p.read_bytes() for p in sorted((ROOT / "site").glob("*.html")))

CARD = re.compile(r'<article[^>]*\bclass="[^"]*\bpo-card\b[^"]*"[^>]*>.*?</article>', re.S)


def cards(html):
    out = []
    for m in CARD.finditer(html or ""):
        tag = m.group(0)[: m.group(0).find(">") + 1]
        t = re.search(r'data-ticker="([^"]+)"', tag)
        if t:
            out.append((t.group(1), m.group(0)))
    return out


protected_cards = cards(payload.get("cards_html"))
public_cards = cards(page_bytes.decode("utf-8", "replace"))
protected_pool = [r["data-ticker"] for r in
                  BeautifulSoup(payload.get("candidate_pool_html"), "html.parser").select(".ucp-row")]
public_pool = [r["data-ticker"] for r in page.select("#us-candidate-pool .ucp-row")]
verbatim = [t for t, blk in protected_cards if len(blk) > 300 and blk.encode() in public_root]

# ── Save fixture: which of ITS recorded sources still hold ─────────────────
save_receipt_path = ROOT / "mockups/evidence/prophet-opportunity-workspace/save-visual-20261104-fabric/save-inputs.json"
save_fixture = {"receipt": str(save_receipt_path.relative_to(ROOT)), "exists": save_receipt_path.exists()}
if save_fixture["exists"]:
    recorded = json.loads(save_receipt_path.read_text())
    unchanged, changed = [], []
    for rel, want in recorded["source_sha256"].items():
        p = ROOT / rel
        now = sha(p) if p.exists() else "ABSENT"
        entry = {"path": rel, "recorded_sha256": want, "now_sha256": now}
        (unchanged if now == want else changed).append(entry)
    save_fixture.update({
        "recorded_board_as_of": recorded.get("board_as_of"),
        "recorded_anchor": {"ticker": recorded.get("ticker"), "card_id": recorded.get("card_id")},
        "unchanged_sources": unchanged,
        "superseded_sources": changed,
    })

receipt = {
    "schema": "prophet.native_pair_provenance/v1",
    "source_head": HEAD,
    "pair": {"board": board, "gate": gate,
             "same_run": board["emit"].get("pair_id") == gate["emit"].get("pair_id"),
             "same_as_of": board["as_of"] == gate["as_of"]},
    "coherence_guard": {
        "command": "python3 scripts/check_signal_gate_coherence.py site/factordata/us_standouts.json site/factordata/signal_gate.json",
        "exit": coherence.returncode,
        "output": coherence_out,
        "mismatched_tickers": 0 if coherence.returncode == 0 else None,
    },
    "board_contradictions_guard": {
        "command": "python3 scripts/check_board_contradictions.py site/factordata/us_standouts.json",
        "exit": contradictions.returncode,
        "output": (contradictions.stdout + contradictions.stderr).strip(),
    },
    "native_build": json.loads(args.build_receipt.read_text()),
    "publication_consumers": {
        "public_html": {"path": "site/us_stocks.html", "sha256": sha(ROOT / "site/us_stocks.html"),
                        "bytes": (ROOT / "site/us_stocks.html").stat().st_size},
        "essential_payload": {"path": "site/premiumdata/us_stocks.json",
                              "sha256": sha(ROOT / "site/premiumdata/us_stocks.json"),
                              "bytes": (ROOT / "site/premiumdata/us_stocks.json").stat().st_size},
        "prophet_index": {"path": "site/prophet/index.json", "sha256": sha(index_path),
                          "bytes": index_path.stat().st_size,
                          "asof": index.get("asof"), "recorded_at": index.get("recorded_at"),
                          "source_asof": index.get("source_asof"),
                          "source_board_asof": index.get("source_board_asof"),
                          "plan_count": index.get("plan_count"),
                          "active_count": index.get("active_count"),
                          "open_count": index.get("open_count"),
                          "source_board_sha256": index.get("source_board_sha256"),
                          "source_board_snapshot_path": snapshot_rel,
                          "snapshot_present": snapshot_path.exists(),
                          "snapshot_decompressed_sha256": snapshot_decompressed_sha,
                          "index_binds_this_board": index.get("source_board_sha256") == board["sha256"],
                          "snapshot_is_this_board": snapshot_ok},
    },
    "publication_pair_guards": json.loads(args.publication_pair.read_text()),
    "protected_public_separation": {
        "public_pool_rows": public_pool,
        "protected_pool_rows": len(protected_pool),
        "public_pool_disjoint_from_protected": not (set(public_pool) & set(protected_pool)),
        "public_screener_cards": [t for t, _ in public_cards],
        "protected_screener_cards": len(protected_cards),
        "public_cards_disjoint_from_protected_cards":
            not ({t for t, _ in public_cards} & {t for t, _ in protected_cards}),
        "protected_card_blocks_verbatim_in_public_root": verbatim,
        "protected_plan_controls_in_public_html": len(page.select("[data-pvs-plan-target]")),
        "public_today_grid_present": page.select_one("#us-today-grid") is not None,
        "public_today_visible": (page.select_one("#us-today").get("data-today-visible")
                                  if page.select_one("#us-today") else None),
        "public_today_total": (page.select_one("#us-today").get("data-today-total")
                                if page.select_one("#us-today") else None),
    },
    "render": json.loads(args.render.read_text()),
    "save_fixture": save_fixture,
    "scope": (
        "Native generated publication artifacts and their source proof, from one build "
        "snapshot. Not an authenticated, entitled, live, Paper or production acceptance."
    ),
}
args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
print("WROTE", args.output)
print(json.dumps({
    "same_run": receipt["pair"]["same_run"],
    "same_as_of": receipt["pair"]["same_as_of"],
    "coherence_exit": receipt["coherence_guard"]["exit"],
    "index_binds_this_board": receipt["publication_consumers"]["prophet_index"]["index_binds_this_board"],
    "snapshot_is_this_board": receipt["publication_consumers"]["prophet_index"]["snapshot_is_this_board"],
    "guards_all_true": all(receipt["publication_pair_guards"]["checks"].values()),
    "guards_count": len(receipt["publication_pair_guards"]["checks"]),
    "pool": receipt["publication_pair_guards"]["eligible_pool"],
    "protected_plan_controls_in_public_html":
        receipt["protected_public_separation"]["protected_plan_controls_in_public_html"],
    "save_superseded": [s["path"] for s in save_fixture.get("superseded_sources", [])],
}, indent=2))
