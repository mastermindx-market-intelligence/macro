"""Real-PDF acceptance through existing intake; isolated local stores only.

Usage: python -B verify_usda_local_intake.py REPOSITORY RETAINED_PDF NEW_OUTPUT_DIR
The PDF is not fetched, a provider is never called, and existing output is refused.
This proves local Research consumer compatibility, not canonical source admission.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PDF_SHA = "6cc97c08be7e683b6114ae8e16d49fce2f21dce3ed3f9933b0acbd2d37e6840b"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_hashes(root):
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob("*"))
            if p.is_file()}


def main():
    repo, pdf, output = [Path(x).resolve() for x in sys.argv[1:]]
    assert digest(pdf) == PDF_SHA, "retained PDF hash mismatch"
    assert not output.exists(), "existing evidence must not be overwritten"
    output.mkdir(parents=True)
    sys.path.insert(0, str(repo))
    network_attempts = []

    def audit(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
            network_attempts.append(event)
            raise RuntimeError("network forbidden in local intake acceptance")

    sys.addaudithook(audit)
    from engine.research_vault import ingest, r2_store
    from engine.press import desk_planner as planner

    sidecar_path = Path(__file__).with_name("usda_sidecar.json")
    sidecar_bytes = sidecar_path.read_bytes()
    sidecar = json.loads(sidecar_bytes)
    source_files = ["engine/research_vault/ingest.py", "engine/research_vault/sidecar.py",
                    "engine/research_vault/corpus.py", "engine/research_vault/r2_store.py",
                    "engine/press/desk_planner.py", "config/press.yml"]
    source_hashes = {p: digest(repo / p) for p in source_files}
    results = []

    def passed(name, condition):
        assert condition, name
        results.append({"check": name, "passed": True})

    def setup_store(name):
        root = output / name
        inbox = root / "research_inbox"
        inbox.mkdir(parents=True)
        (inbox / "usda-wasde-676.pdf").write_bytes(pdf.read_bytes())
        (inbox / "usda-wasde-676.json").write_bytes(sidecar_bytes)
        return r2_store.LocalStore(root)

    now = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)
    dry_store = setup_store("dry-store")
    dry_before = tree_hashes(dry_store.root)
    dry = ingest.run(dry_store, output / "dry.sqlite", now=now, dry_run=True)
    passed("dry_run_ingests_one_real_pdf", dry["ingested"] == 1 and dry["failed"] == 0)
    passed("dry_run_does_not_mutate_store", tree_hashes(dry_store.root) == dry_before)
    dry_catalog = json.loads(dry["catalog_bytes"])
    passed("publication_date_not_restamped", dry_catalog["items"][0]["published_at"] == "2026-10-09T16:00:00Z")

    local_store = setup_store("local-store")
    local = ingest.run(local_store, output / "local.sqlite", now=now, dry_run=False)
    passed("isolated_local_publish_completes", local["ingested"] == 1 and local["failed"] == 0
           and local.get("corpus_published") and local.get("catalog_published"))
    cat = json.loads(local["catalog_bytes"])
    passed("one_catalog_row", len(cat["items"]) == 1)
    item = cat["items"][0]
    passed("measured_pdf_pages", item["pages"] == 40)
    passed("source_identity_and_summary_retained", item["id"] == sidecar["id"]
           and item["summary_points"] == sidecar["summary_points"]
           and item["published_at"] == "2026-10-09T16:00:00Z" and item["tickers"] == [])
    with sqlite3.connect(f"file:{output / 'local.sqlite'}?mode=ro", uri=True) as conn:
        row = conn.execute("select published_at, body from documents where doc_id=?", (item["id"],)).fetchone()
        passed("searchable_body_and_true_date", row and row[0] == "2026-10-09T16:00:00Z"
               and "October 9, 2026" in row[1] and "740 million" in row[1])
    again = ingest.run(local_store, output / "local.sqlite", now=now, dry_run=False)
    passed("same_source_is_not_reingested", again["ingested"] == 0 and again["skipped"] == 1
           and again["failed"] == 0 and len(json.loads(again["catalog_bytes"])["items"]) == 1)

    fixture = output / "planner-fixture"
    cat_path = fixture / "data/research_vault/catalog.json"
    cat_path.parent.mkdir(parents=True)
    cat_path.write_bytes(local["catalog_bytes"])
    cfg = planner.load_config(repo)
    passed("cutover_remains_false", cfg["cutover"] is False)
    as_of = date(2026, 10, 14)

    def plan(blocked=()):
        return planner.plan(["research_desk"], as_of=as_of, root=fixture,
                            cfg=cfg, extra_blocked_refs=blocked)

    slots = plan()
    ref = "research_vault:" + item["id"]
    passed("real_source_reaches_research_planner", len(slots) == 1 and slots[0]["sources"] == [ref])
    passed("no_issuer_invented", slots[0]["story"]["tickers"] == [])
    passed("held_ref_is_excluded", plan([ref]) == [])
    for name, changes in [
        ("future_report_refused", {"published_at": "2026-10-15"}),
        ("stale_research_report_refused", {"published_at": "2026-09-22"}),
        ("summary_missing_refused", {"summary_points": []}),
    ]:
        changed = copy.deepcopy(cat)
        changed["items"][0].update(changes)
        cat_path.write_text(json.dumps(changed))
        passed(name, plan() == [])
    cat_path.write_bytes(local["catalog_bytes"])
    passed("no_network_attempts", network_attempts == [])
    passed("application_sources_unchanged", source_hashes == {p: digest(repo / p) for p in source_files})
    passed("retained_source_and_sidecar_unchanged", digest(pdf) == PDF_SHA
           and sidecar_path.read_bytes() == sidecar_bytes)
    result = {"observed_at": datetime.now(timezone.utc).isoformat(),
              "source_pdf_sha256": PDF_SHA, "sidecar_sha256": digest(sidecar_path),
              "source_hashes": source_hashes, "checks": results,
              "slot": slots[0], "network_attempts": network_attempts,
              "production_writes": 0, "press_writer_calls": 0,
              "press_staging_writes": 0, "canonical_admission": False,
              "public_article_accepted": False, "publication_enabled": False}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"checks_passed": len(results), "result": str(output / 'result.json'),
                      "canonical_admission": False, "production_writes": 0}))


if __name__ == "__main__":
    main()
