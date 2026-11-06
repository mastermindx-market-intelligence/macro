"""scripts/ingest_research.py — Research Vault hourly ingestion CLI (RV W1).

Builds the object store (R2 private bucket, or a local dir), runs the ingestion
pass (engine.research_vault.ingest.run), then publishes catalog.json + corpus.sqlite
to the store and prints a summary. Also snapshots to the repo, so the nightly
render can SSR-bake without R2:

  * ``data/research_vault/catalog.json``  — the public catalog;
  * ``data/research_vault/excerpts.json`` — the public first-pages excerpts
    (engine.research_vault.excerpt) that the per-report SEO pages publish
    outside the paywall. Derived from the corpus body text HERE because the
    corpus lives only in R2 and the render path must never reach for it.

Usage:
    python -m scripts.ingest_research                 # R2 (R2_RESEARCH_BUCKET + creds)
    RESEARCH_LOCAL_STORE=/tmp/rv python -m scripts.ingest_research --local /tmp/rv
    python -m scripts.ingest_research --dry-run       # ingest, but publish nothing
    python -m scripts.ingest_research --require-store # a missing store is a FAILURE

EXIT SEMANTICS (Wave 4, Defect 6) — fail soft on documents, fail closed on the
publication plane:

  * 0 — the plane completed. Individual documents may have failed; one malformed
    PDF must never red the hourly lane, and ``failed=N`` is reported as a warning.
  * 1 — a PLANE failure: the authoritative catalog was unavailable over a mature
    vault, the corpus could not be restored or published, the catalog could not be
    published, receipts could not be flushed behind a publish, no usable store was
    configured under ``--require-store``, or the run raised at top level.

The CLI used to be unconditionally never-raise (``exits 0 with a warning on
error``), and the workflow then discarded the captured rc as well — so an hour in
which ingestion accomplished nothing at all concluded green, twice over. The
per-document never-raise contract is unchanged; only plane outcomes now exit
non-zero.

The repo snapshots are written ONLY behind a successful canonical publish (freeze
§B): the git mirror exists so the nightly render can SSR-bake without R2, and a
mirror that advanced past a failed R2 publish would make the fallback copy
independently newer than the authority it mirrors.

Store precedence: --local > RESEARCH_LOCAL_STORE > R2_RESEARCH_BUCKET.
Mirrors the brevity of scripts/build_marketing.py.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import logging
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

log = logging.getLogger("ingest_research")

# Repo snapshots the nightly render SSR-bakes from (masterplan §4).
_REPO_SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "research_vault"


def _repo_snapshot_dir(override: str | None = None) -> Path:
    """Where the SSR snapshots are written; defaults to the committed mirror.

    Overridable via ``--repo-dir`` or ``RESEARCH_REPO_SNAPSHOT_DIR`` so that a run
    against a scratch store cannot write into the LIVE committed mirror. That is
    not a hypothetical: writing this wave's own CLI tests truncated
    ``data/research_vault/catalog.json`` from 1,402 rows to 1, because a
    subprocess ``--local`` run happily snapshotted its two-document scratch vault
    over the real file. A store override with no matching snapshot override is a
    footgun, so the two now travel together.
    """
    raw = override or os.environ.get("RESEARCH_REPO_SNAPSHOT_DIR", "")
    return Path(raw).expanduser() if raw else _REPO_SNAPSHOT_DIR


def _public_mirror_bytes(catalog_bytes: bytes) -> bytes | None:
    """The repo-mirror copy of the canonical catalog: producer_generation stripped.

    The committed ``data/research_vault/catalog.json`` is a PUBLIC snapshot the
    nightly render bakes into the site, while ``summary['catalog_bytes']`` (what
    was published to R2) stays the canonical PRIVATE document carrying the
    internal ``producer_generation`` block (producer/report cohort + content
    hashes). Only that ONE top-level field is removed here: key order and the
    engine's serializer conventions (``ensure_ascii=False``, ``indent=2``,
    trailing newline) are preserved, a same-named key nested inside an item is
    catalog content and is left alone, and when the field is absent the EXACT
    input bytes are returned untouched so a legacy mirror never churns
    whitespace or order.

    Returns None when the canonical bytes are not valid JSON: no safe stripped
    mirror can be derived, so the caller keeps the existing failing-mirror
    semantics (warn, do not advance) instead of publishing fabricated output.
    """
    try:
        doc = json.loads(catalog_bytes.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(doc, dict) or "producer_generation" not in doc:
        return catalog_bytes
    doc.pop("producer_generation", None)
    return (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _report_measured(summary: dict, dry_run: bool = False) -> None:
    """Print the per-field fill rate + the engine-measured tripwires.

    Annotations use a BARE print starting at column 0: GitHub only parses a
    workflow command when ``::`` starts the line, and this CLI's logging format
    prefixes ``%(levelname)s``, which would silently swallow it.

    Every condition here is a WARNING or a NOTICE, never a failure — the hourly
    job's contract is that a bad document never blocks the batch, and the same
    holds for a document we merely learned something unflattering about. (The one
    fail-CLOSED gate in this lane is upstream of the CLI: the workflow refuses to
    ingest at all on a host with no ``pdftotext``, because ingesting bodyless
    writes receipts that freeze the damage — see research-ingest.yml.)

    The re-extraction lines below describe rows that were CHANGED, so like the
    sidecar lines they may claim nothing under --dry-run, which publishes nothing.
    """
    try:
        from engine.research_vault import catalog as catalog_mod

        cov = summary.get("coverage") or {}
        if cov:
            lines, dead = catalog_mod.coverage_lines(cov)
            print("ingest_research: catalog field coverage")
            for ln in lines:
                print(ln)
            for field in dead:
                # A schema field that no producer ever fills. Loud on purpose: this
                # is the state that sat unnoticed across every document in the vault
                # while needs_metadata reported a clean bill of health.
                print(f"::warning::research_vault: catalog field '{field}' is empty on "
                      f"ALL {cov[field]['total']} items — no producer fills it",
                      flush=True)

        # Both of these describe rows that were CHANGED, so neither may claim
        # anything under --dry-run, which publishes nothing: "folded into
        # already-published rows" would be simply false.
        if summary.get("summaries_recovered") and not dry_run:
            # A NOTICE, not a warning: this is the repair working. It is worth
            # surfacing because the number is also the count of rows that shipped
            # "Summary pending" to the public site until this run healed them.
            print(f"::notice title=research_vault::{summary['summaries_recovered']} "
                  f"late sidecar summary(ies) folded into already-published rows "
                  f"({summary.get('sidecars_checked', 0)} sidecar(s) re-checked)",
                  flush=True)

        if summary.get("summaries_resynced") and not dry_run:
            # Rows whose bullets reached the catalog but not the corpus — the
            # skew a failed corpus publish leaves behind. Non-zero means a PRIOR
            # run's publish failed, so it is worth seeing even though it healed.
            print(f"::warning title=research_vault::"
                  f"{summary['summaries_resynced']} corpus summary(ies) were out of "
                  f"sync with the catalog and have been resynced — a previous "
                  f"corpus publish did not land", flush=True)

        if summary.get("bodies_reextracted") and not dry_run:
            # A NOTICE, not a warning: this is the repair working. The number is
            # also the count of rows that were invisible to body search — and
            # served to the full-report reader as excerpt-only — until this run
            # healed them (see ingest._reextract_bodies).
            print(f"::notice title=research_vault::{summary['bodies_reextracted']} "
                  f"empty body(ies) re-extracted into already-published rows "
                  f"({summary.get('reextract_checked', 0)} re-checked)", flush=True)

        if summary.get("reextract_remaining") and not dry_run:
            # Mirrors the sidecar-cap precedent: a bound that truncates coverage
            # must SAY so, or the notice above reads as "the backlog is drained".
            print(f"::warning title=research_vault::body re-extraction capped — "
                  f"{summary['reextract_remaining']} candidate row(s) not "
                  f"re-checked this run", flush=True)

        if summary.get("reextract_aborted") and not dry_run:
            # The 2026-07-30 fault itself, still live: the pass refuses to stamp
            # anything from an extraction that never ran, so the backlog stands
            # until poppler is back on this host.
            print("::warning title=research_vault::body re-extraction could not "
                  "run — pdftotext is still unavailable on this host, so the "
                  "bodyless rows stay bodyless (install poppler)", flush=True)

        if summary.get("no_text_layer"):
            print(f"::warning::research_vault: {summary['no_text_layer']} document(s) "
                  f"ingested with no/thin text layer — body search cannot find them",
                  flush=True)
        if summary.get("text_unavailable"):
            print(f"::warning::research_vault: pdftotext unavailable for "
                  f"{summary['text_unavailable']} document(s) — HOST fault, not a "
                  f"document property (install poppler)", flush=True)
        if summary.get("duplicate_bytes"):
            print(f"::warning::research_vault: {summary['duplicate_bytes']} "
                  f"byte-identical duplicate(s) ingested under a second id", flush=True)
    except Exception as exc:  # noqa: BLE001 — reporting must never fail the job
        log.warning("ingest_research: coverage report failed: %s", exc)


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s %(message)s",
                        stream=sys.stderr)
    ap = argparse.ArgumentParser(description="Research Vault ingestion (RV W1)")
    ap.add_argument("--local", metavar="DIR",
                    help="use a local filesystem store rooted at DIR (no R2)")
    ap.add_argument("--dry-run", action="store_true",
                    help="run ingest but do NOT publish corpus/catalog back to R2")
    ap.add_argument("--materialize-only", action="store_true",
                    help="bounded immutable derivatives only; no mutable publication or repo snapshot")
    ap.add_argument("--corpus", metavar="PATH",
                    help="legacy corpus.sqlite path (default: a temp file); generation runs own a private workspace")
    ap.add_argument("--repo-dir", metavar="DIR",
                    help="write the SSR repo snapshots (catalog.json, excerpts.json) "
                         "under DIR instead of the committed data/research_vault "
                         "mirror. Env: RESEARCH_REPO_SNAPSHOT_DIR")
    ap.add_argument("--require-store", action="store_true",
                    help="treat a missing/unusable store as a FAILURE (exit 1). Set "
                         "on the scheduled production run, where 'no store' means "
                         "the secrets did not reach the runner — not 'nothing to do'")
    ap.add_argument("--generation-source-commit", metavar="HEX40",
                    help="explicit producer source commit (40 lowercase hex); "
                         "requires --generation-run and --generation-evidence-path; supplied provenance does not "
                         "establish writer admission")
    ap.add_argument("--generation-run", metavar="ID",
                    help="explicit producer run identity; requires --generation-source-commit and --generation-evidence-path; "
                         "incompatible with --dry-run and --materialize-only")
    ap.add_argument("--generation-evidence-path", metavar="PATH",
                    help="new private journal outside the checkout/public mirror; required with generation identity")
    a = ap.parse_args()
    if a.materialize_only and (a.dry_run or a.corpus or a.repo_dir):
        ap.error("--materialize-only owns private scratch and forbids dry-run/corpus/repo-dir overrides")
    gen_src = a.generation_source_commit
    gen_run = a.generation_run
    evidence_path = a.generation_evidence_path
    present = (gen_src is not None, gen_run is not None, evidence_path is not None)
    if any(present) and not all(present):
        ap.error("--generation-source-commit, --generation-run and --generation-evidence-path must be supplied together")
    if evidence_path is not None and not evidence_path.strip():
        ap.error("--generation-evidence-path must be non-empty")
    if gen_src is not None or gen_run is not None:
        if a.materialize_only:
            ap.error("--generation-source-commit/--generation-run cannot be combined with --materialize-only")
        if a.dry_run:
            ap.error("--generation-source-commit/--generation-run cannot be combined with --dry-run")
        if a.corpus is not None:
            ap.error("generation runs own a new private corpus workspace and forbid --corpus overrides")
        if not re.fullmatch(r"[0-9a-f]{40}", gen_src or ""):
            ap.error("--generation-source-commit must be exactly 40 lowercase hex characters")
        if not gen_run or gen_run != gen_run.strip():
            ap.error("--generation-run must be non-empty with no surrounding whitespace")

    repo_dir = _repo_snapshot_dir(a.repo_dir)
    repo_catalog = repo_dir / "catalog.json"
    repo_excerpts = repo_dir / "excerpts.json"

    evidence = None
    try:
        scope = nullcontext(None)
        if evidence_path is not None:
            from engine.research_vault.generation_evidence import FileGenerationEvidence, EvidenceUnavailable
            try:
                path = Path(evidence_path).expanduser()
                resolved = path.resolve()
                public_roots = (Path(__file__).resolve().parent.parent, repo_dir.resolve())
            except (OSError, RuntimeError, ValueError) as exc:
                raise EvidenceUnavailable("private evidence path unavailable: " + type(exc).__name__) from None
            for public_root in public_roots:
                if resolved == public_root or public_root in resolved.parents:
                    raise EvidenceUnavailable("private evidence must be outside the source checkout and public mirror")
            scope = FileGenerationEvidence.create(path, {"source_commit": gen_src, "run": gen_run})
        try:
            with scope as evidence:
                if evidence is not None:
                    # mkdir without exist_ok reserves this original invocation's
                    # scratch, including SQLite/restore sidecars. Preserve any
                    # previous occupant and never fall back to shared /tmp.
                    workspace = path.with_name(path.name + ".workspace")
                    try:
                        workspace.mkdir(mode=0o700)
                    except (OSError, ValueError) as exc:
                        # The original host path must not enter public job logs.
                        raise EvidenceUnavailable("original workspace unavailable: " + type(exc).__name__) from None
                    a.corpus = str(workspace / "corpus.sqlite")
                return _run_pipeline(a, gen_src, gen_run, evidence, repo_catalog, repo_excerpts)
        finally:
            if evidence is not None:
                # Bind only the bytes this original invocation durably wrote.
                # Private records/path remain on their host carrier. This is a
                # capture notice, not completion or remote-settlement evidence.
                try:
                    digest = evidence.capture_sha256
                except EvidenceUnavailable:
                    pass
                else:
                    try:
                        print("ingest_research: original_capture_sha256=" + digest, flush=True)
                    except (OSError, ValueError):
                        # A broken/closed output carrier must not replace the
                        # ingest result, original exception, or cancellation.
                        # No delivered capture means no recovery authority.
                        pass
    except Exception as exc:  # noqa: BLE001 — report, then FAIL the lane
        # Still never-RAISE (the salvage step must run), but no longer never-fail:
        # an unexpected top-level exception means the plane did not complete, and
        # returning 0 here reported a dead hour as a healthy one.
        log.warning("ingest_research: run failed: %s", exc)
        print(f"::error title=research-ingest::ingest raised at top level — "
              f"{type(exc).__name__}: {exc}", flush=True)
        return 1


def _run_pipeline(a, gen_src, gen_run, evidence, repo_catalog, repo_excerpts):
    from engine.research_vault import ingest as ingest_mod
    from engine.research_vault import r2_store

    # Only a VALIDATED generation identity (checked in main() before this ran)
    # asks the store for its single-attempt write client, so the producer's own
    # publications are never silently repeated by hidden SDK PUT retries.
    # Ordinary CLI/materialize/default callers keep the exact legacy signature
    # and behaviour; no env or user retry-policy flag exists.
    if gen_src is not None and gen_run is not None:
        store = r2_store.build_store(local_dir=a.local, single_attempt_writes=True)
    else:
        store = r2_store.build_store(local_dir=a.local)
    if store is None:
        # On a developer box this is genuinely nothing to do. On the hourly
        # production run it means the R2 secrets did not reach the runner, and
        # a green lane would report "ingested nothing" as success forever.
        if a.require_store or a.materialize_only or evidence is not None:
            print("::error title=research-ingest::no research store configured "
                  "(RESEARCH_LOCAL_STORE / --local / R2_RESEARCH_BUCKET + creds) "
                  "— the hourly ingest could not run at all", flush=True)
            return 1
        print("ingest_research: no store (set RESEARCH_LOCAL_STORE, --local, "
              "or R2_RESEARCH_BUCKET + R2 creds) — nothing to do", file=sys.stderr)
        return 0

    if a.materialize_only:
        from engine.research_vault import materialize_published
        result = materialize_published.run(store)
        print("ingest_research: materialize-only " + json.dumps(result, sort_keys=True))
        return 1 if result.get("error") else 0

    corpus_path = Path(a.corpus) if a.corpus else \
        Path(tempfile.gettempdir()) / "research_vault_corpus.sqlite"

    run_kwargs = {"dry_run": a.dry_run}
    if gen_src is not None and gen_run is not None:
        run_kwargs["generation_identity"] = {"source_commit": gen_src, "run": gen_run}
        run_kwargs["generation_evidence"] = evidence
    summary = ingest_mod.run(store, corpus_path, **run_kwargs)

    catalog_bytes = summary.get("catalog_bytes") or b""

    if a.dry_run:
        print(f"ingest_research: DRY-RUN — ingested={summary['ingested']} "
              f"skipped={summary['skipped']} failed={summary['failed']} "
              f"needs_metadata={summary['needs_metadata']} "
              f"titles_repaired={summary.get('titles_repaired', 0)} "
              f"summaries_recovered={summary.get('summaries_recovered', 0)} "
              f"(corpus={corpus_path}; nothing published)")
        _report_measured(summary, dry_run=True)
        return 0

    # The publication plane's own verdict. A per-document failure is NOT here:
    # `failed=N` stays a warning, because one bad PDF must never red the lane.
    plane_ok = bool(summary.get("corpus_published")
                    and summary.get("catalog_published")
                    and not summary.get("error")
                    and not summary.get("receipts_unflushed"))

    # Snapshot catalog.json to the repo for the nightly SSR bake — but ONLY
    # behind a successful canonical publish (freeze §B). The mirror exists so
    # the render can build without R2; it is not a second authority, and a
    # mirror that advanced past a failed R2 publish would be independently
    # newer than the catalog it mirrors — exactly the split that let a failed
    # catalog PUT still ship a "newer" generation to git (Defect 4).
    if catalog_bytes and plane_ok:
        # The mirror is a PUBLIC projection of the canonical catalog: strip
        # the internal producer_generation block on the way out. The bytes
        # PUT to R2 (summary['catalog_bytes']) are not touched — the mirror
        # is a projection, never a second authority.
        mirror_bytes = _public_mirror_bytes(catalog_bytes)
        if mirror_bytes is None:
            # Unparseable canonical bytes: keep the last fully published
            # mirror rather than advancing it with output nobody vouched
            # for — the same failing-mirror semantics as a write error,
            # never a fake clean publication.
            log.warning("ingest_research: repo catalog mirror NOT advanced — "
                        "canonical catalog bytes are not valid JSON, so no "
                        "stripped public mirror could be derived")
        else:
            try:
                repo_catalog.parent.mkdir(parents=True, exist_ok=True)
                repo_catalog.write_bytes(mirror_bytes)
            except Exception as exc:  # noqa: BLE001
                log.warning("ingest_research: repo snapshot write failed: %s", exc)
    elif not plane_ok:
        print(f"::warning title=research-ingest::repo catalog mirror NOT advanced "
              f"— canonical publish did not complete (corpus_published="
              f"{summary.get('corpus_published')}, catalog_published="
              f"{summary.get('catalog_published')}, error="
              f"{summary.get('error') or 'none'}). The last fully published "
              f"mirror is kept.", flush=True)

    # Public first-pages excerpts, snapshotted beside the catalog so the
    # nightly render stays R2-free (the corpus body text lives only in R2).
    # Own never-raise guard: an excerpt is never worth failing the hourly job,
    # and a failure here simply leaves yesterday's committed snapshot in place.
    n_excerpts = 0
    try:
        # Same gate as the catalog mirror: the excerpts are a projection of the
        # very corpus+catalog that failed to publish, so advancing them would
        # ship public first-page text for a generation that never went live.
        if plane_ok and corpus_path.is_file() and catalog_bytes:
            from engine.research_vault import excerpt as excerpt_mod

            items = (json.loads(catalog_bytes.decode("utf-8")) or {}).get("items") or []
            ids = {it["id"] for it in items if isinstance(it, dict) and it.get("id")}
            # READ-ONLY: this connection must never mutate the corpus that was
            # just published to R2.
            conn = sqlite3.connect(f"{corpus_path.resolve().as_uri()}?mode=ro", uri=True)
            try:
                excerpts = excerpt_mod.snapshot(conn, ids)
            finally:
                conn.close()
            if excerpt_mod.write_repo_snapshot(excerpts, repo_excerpts):
                n_excerpts = len(excerpts)
    except Exception as exc:  # noqa: BLE001 — keep the hourly job alive
        log.warning("ingest_research: excerpt snapshot failed: %s", exc)

    print(f"ingest_research: ok — ingested={summary['ingested']} "
          f"skipped={summary['skipped']} failed={summary['failed']} "
          f"needs_metadata={summary['needs_metadata']} "
          f"titles_repaired={summary.get('titles_repaired', 0)} "
          f"(from_pdf={summary.get('titles_recovered', 0)}, "
          f"filename_only={summary.get('titles_unresolved', 0)}) "
          f"summaries_recovered={summary.get('summaries_recovered', 0)} "
          f"(checked={summary.get('sidecars_checked', 0)}, "
          f"resynced={summary.get('summaries_resynced', 0)}) "
          f"bodies_reextracted={summary.get('bodies_reextracted', 0)} "
          f"(checked={summary.get('reextract_checked', 0)}, "
          f"remaining={summary.get('reextract_remaining', 0)}) "
          f"corpus_published={summary.get('corpus_published')} "
          f"catalog_published={summary.get('catalog_published')} "
          f"catalog_state={summary.get('catalog_state')} "
          f"excerpts={n_excerpts} snapshot={repo_catalog}")
    _report_measured(summary)

    if not plane_ok:
        # Every plane failure has ALREADY printed its own ::error with the
        # specific cause (engine side). This is the exit code that makes the
        # workflow red, which is the part that was missing.
        print(f"::error title=research-ingest::publication plane FAILED "
              f"(error={summary.get('error') or 'none'}, corpus_published="
              f"{summary.get('corpus_published')}, catalog_published="
              f"{summary.get('catalog_published')}, receipts_unflushed="
              f"{summary.get('receipts_unflushed', 0)}) — nothing user-visible "
              f"advanced this run", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
