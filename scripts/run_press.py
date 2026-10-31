"""scripts/run_press.py — Media Network W1 (docket D14) press orchestrator.

Two modes, and the default is the safe one:

    python -m scripts.run_press                 # --staging (default)
    python -m scripts.run_press --staging       # plan -> write -> validate
    python -m scripts.run_press --emit          # publish what already passed

--staging  Plans slots, writes drafts, runs the whole deterministic validator
           suite, and writes one JSON per slot (draft + validator_report +
           attempt history) to data/press/staging/.  It writes NOTHING under
           content/ or site/.  That is a tested invariant, not a convention:
           tests/test_press_run.py::test_staging_writes_nothing_outside_staging
           snapshots the tree and fails on any other write.

           A non-publishable record precedes each slot's first provider call;
           returned drafts are retained before validation. An interrupted slot
           stays reserved by the existing planner until its same attempt is
           reconciled. Provider-owned accounting may still write its own ledgers.

--emit     Revalidates staged items whose status is `passed`, writes
           content/seo/blog/<slug>.md, renders the estate with the EXISTING
           free-content builder, copies the /blog/ subtree (pages + feed.xml)
           into site/, and appends one row per piece to
           data/press/published.jsonl.

           site/sitemap.xml is NEVER written here — the nightly owns it.
           Only site/blog/** is copied out of the render, so this lane cannot
           clobber the learn/tools/calculator pages the render lanes own.

W1.5 EMIT ROUTING (config/press.yml `cutover`).  Each passing draft is routed by
its DESK's publication:

  cutover: false (today)   every desk keeps the path above, byte for byte.  The
                           property trees still get built by
                           scripts/build_press_properties.py, but nothing about
                           this lane's writes changes.
  cutover: true            a publication that carries `property_tree` takes its
                           own road: the .md goes to that publication's
                           content_dir (NOT content/seo/blog), the free-content
                           estate render is SKIPPED for it entirely, and its
                           property tree is re-rendered from the ledger.

Both branches now write `url` and `title` on the ledger row.  That is what makes
the cutover migration-free: a row states where IT was published, so pre-cutover
rows keep pointing at /blog/ forever and no historic row is ever rewritten.  The
ledger is append-only and every consumer reads it with .get(), so rows written
before this change (which carry neither field) stay readable.

DELTA VS W1 (declared, not incidental): the ledger row's `publication` now comes
from the DESK's config entry at emit time, not from the staged record's copy of
it.  W1 read `obj["publication"]`, which was written when the draft was STAGED —
so re-pointing a desk to another publication between staging and emit published
the piece under the new routing while recording the old name.  The staged value
remains the fallback for a desk that has since been deleted from config.

QUARANTINE FLOW: fail -> regenerate (<= quarantine.max_regenerations) -> drop
the slot with a logged reason.  A thin day beats a padded one, so a dropped
slot is a normal outcome and exits 0.

The render replay is the non-obvious part of --emit.  The committed estate is
NOT the builder's raw output — the render lanes run idempotent sweeps over
site/ afterwards (externalize_css, optimize_assets), and
`build_free_content --check` replays those sweeps before comparing.  So an emit
that committed raw builder output would turn the estate drift check red on the
very next PR.  This replays the same sweeps, through the same helpers --check
uses, so what lands in site/blog/ is the post-sweep image --check expects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from engine.press import desk_planner, properties, validators, writer  # noqa: E402

log = logging.getLogger("run_press")

_SITE_BASE = "https://www.mastermind-x.com"

# ``canonical_story.v1`` packets are deliberately source-ready only.  This
# writer/emit rail has no verified-approval compiler, so no value written into
# a mutable staging JSON file can turn one into publishable copy.  Keep the
# marker list broad: callers may supply an incomplete canonical slot after a
# failed/interrupted stage, and that ambiguity must block rather than fall back
# to generic-Press behaviour.
_CANONICAL_SLOT_MARKERS = frozenset({
    "canonical_story_id",
    "canonical_story_revision_id",
    "canonical_story_status",
    "canonical_emit_allowed",
    "approved_claim_ids",
    "article_derivative_id",
})


def _is_canonical_story_slot(slot: object) -> bool:
    """Whether a staged slot belongs to the currently non-emittable rail."""
    if not isinstance(slot, dict):
        return False
    if any(key in slot for key in _CANONICAL_SLOT_MARKERS):
        return True
    story = slot.get("story")
    if isinstance(story, dict) and any(
        key in story for key in ("canonical_story_id", "canonical_story_revision_id")
    ):
        return True
    return str(slot.get("id") or "").startswith("press-earnings-")


def _is_unverified_earnings_story_stage(item: object) -> bool:
    """Detect any earnings article that lacks immutable approval provenance.

    The staging file is an audit artifact, not an approval credential.  Looking
    only at ``slot.canonical_emit_allowed`` made a one-field JSON edit enough
    to downgrade a canonical item into generic Press.  Preserve independent
    identity trails from the outer envelope (id / evidence seed / Chronicle
    source) so stripping a slot marker or its nested id still fails closed.

    Legacy and canonical earnings slots deliberately share the
    ``chronicle:defeatbeta`` namespace.  Once every canonical marker has been
    stripped, a mutable staging file cannot prove which producer created it.
    Therefore the safe boundary is broader: *all* DefeatBeta earnings articles
    remain non-emittable until the future immutable approval ingress can attest
    an exact packet.  Other Press desks are unaffected.
    """
    if not isinstance(item, dict):
        return False
    if any(key in item for key in _CANONICAL_SLOT_MARKERS):
        return True
    if str(item.get("id") or "").startswith("press-earnings-"):
        return True
    if _is_canonical_story_slot(item.get("slot")):
        return True
    source_refs = {str(ref) for ref in (item.get("sources") or []) if isinstance(ref, str)}
    seed_refs = {str(ref) for ref in (item.get("seed_refs") or []) if isinstance(ref, str)}
    return (
        any(ref.startswith("chronicle:defeatbeta:") for ref in source_refs)
        or any(ref.startswith("earnings-evidence:") for ref in seed_refs)
    )


# `scripts/stage_official_feed_press.py` stages one qualified official-feed
# candidate as an ordinary Brief draft.  Its staged record carries an explicit
# private-official provenance receipt with public-article approval false: the
# qualification is candidate-only and conveys no release grant.  The receipt
# lives in a mutable staging file, so — exactly as for the earnings guard
# above — the refusal keeps an independent identity trail: the `official_feed:`
# source ref IS the story's source, so it survives any provenance strip that
# leaves the record recognisable as this story at all.
_OFFICIAL_STAGE_RAIL = "private_official_feed"
_OFFICIAL_SOURCE_PREFIX = "official_feed:"


def _is_private_official_stage(item: object) -> bool:
    """Detect a private agency/issuer/market candidate — never emittable here."""
    if not isinstance(item, dict):
        return False
    slot = item.get("slot")
    holders = [item] + ([slot] if isinstance(slot, dict) else [])
    for holder in holders:
        if str(holder.get("id") or "").startswith(("press-official-", "press-issuer-", "press-market-")):
            return True
        provenance = holder.get("provenance")
        if not isinstance(provenance, dict):
            continue
        receipt = provenance.get("admission_receipt")
        if (isinstance(receipt, dict)
                and str(receipt.get("rail") or "") in (_OFFICIAL_STAGE_RAIL, "private_issuer_release", "private_market_snapshot")):
            return True
    refs: set[str] = set()
    for holder in holders:
        for key in ("sources", "seed_refs"):
            refs.update(str(r) for r in (holder.get(key) or []) if isinstance(r, str))
        for key in ("facts", "raw_documents"):
            for fact in holder.get(key) or []:
                if isinstance(fact, dict) and isinstance(fact.get("ref"), str):
                    refs.add(fact["ref"])
        revisions = holder.get("source_revisions")
        if isinstance(revisions, dict):
            refs.update(str(r) for r in revisions)
    return any(ref.startswith((_OFFICIAL_SOURCE_PREFIX, "issuer_sec:", "market_snapshot:", "market_snapshot_inputs:")) for ref in refs)


# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────


def _paths(cfg: dict, root: Path) -> dict:
    p = (cfg.get("paths") or {}) if isinstance(cfg, dict) else {}
    return {
        "staging": root / str(p.get("staging_dir") or "data/press/staging"),
        "ledger": root / str(p.get("ledger") or "data/press/published.jsonl"),
        "content": root / str(p.get("content_dir") or "content/seo/blog"),
        "site_blog": root / "site" / "blog",
    }


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit_route(cfg: dict, root: Path, paths: dict, obj: dict, slug: str) -> dict:
    """Where this piece publishes, and under what URL.

    Returns {publication, routed, md_dir, url}.  `routed` is the ONLY switch in
    this file that the cutover flag moves, and it is deliberately conservative:
    a publication is routed only when cutover is true AND it carries all three
    of property_tree / content_dir / base_url.  A half-filled registry entry
    therefore keeps the existing estate path instead of writing a page at a URL
    it cannot name — and load_config already refuses that combination at
    cutover, so this is the second of two locks on the same door.

    The DESK's publication wins over the staged item's copy of it: the staged
    record was written by an earlier run and a desk can be re-pointed between
    staging and emit.
    """
    desks = (cfg.get("desks") or {}) if isinstance(cfg, dict) else {}
    desk_cfg = desks.get(str(obj.get("desk") or ""))
    desk_cfg = desk_cfg if isinstance(desk_cfg, dict) else {}
    pub_key = str(desk_cfg.get("publication") or obj.get("publication") or "")

    pubs = (cfg.get("publications") or {}) if isinstance(cfg, dict) else {}
    pub = pubs.get(pub_key)
    pub = pub if isinstance(pub, dict) else {}
    tree, content_dir = pub.get("property_tree"), pub.get("content_dir")
    base_url = str(pub.get("base_url") or "").rstrip("/")

    if cfg.get("cutover") is True and tree and content_dir and base_url:
        return {"publication": pub_key, "routed": True,
                "md_dir": root / str(content_dir),
                "url": f"{base_url}/articles/{slug}.html"}
    return {"publication": pub_key, "routed": False,
            "md_dir": paths["content"],
            "url": f"{_SITE_BASE}/blog/{slug}.html"}


def _env_int(name: str, default: int) -> int:
    """Env override for a config-supplied spend guard.

    Empty or unparsable falls back to the config value — a typo in a workflow
    variable must not silently uncap the budget.
    """
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        log.warning("press: %s=%r is not an integer — using config value %s",
                    name, raw, default)
        return default


def _annotate(level: str, title: str, message: str) -> None:
    """GitHub annotation.  Bare print, line-start, flushed — a logger would
    prefix the line and GitHub would silently drop it (house law)."""
    print(f"::{level} title={title}::{message}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Slug de-collision (runs BEFORE validation, never after)
# ─────────────────────────────────────────────────────────────────────────────


def _unique_slug(base: str, slot: dict, taken: set[str]) -> str:
    """A free slug for this draft.

    De-colliding AFTER validation would invalidate the frontmatter check that
    just passed, so it happens here, once, before anything is scored.  The
    suffix mirrors the research-vault idiom: a short stable hash of the story.
    """
    slug = desk_planner.slugify(base) or "market-note"
    if slug not in taken:
        return slug
    suffix = desk_planner.story_key(str(slot.get("id") or ""), slug)[:6]
    return f"{slug[:70 - len(suffix) - 1]}-{suffix}".strip("-")


# ─────────────────────────────────────────────────────────────────────────────
# STAGING
# ─────────────────────────────────────────────────────────────────────────────


def _source_revisions(obj: dict) -> dict[str, str]:
    """Revision receipts recorded on a slot, staged item, or ledger row."""

    raw = obj.get("source_revisions") if isinstance(obj, dict) else None
    if not isinstance(raw, dict):
        slot = obj.get("slot") if isinstance(obj, dict) else None
        raw = slot.get("source_revisions") if isinstance(slot, dict) else None
    out = {
        str(ref): str(receipt).lower()
        for ref, receipt in (raw or {}).items()
        if ref and receipt
    }
    if out:
        return out
    # Compatibility with the first revision-aware staged shape, which carried
    # the receipt only under primary_source before the top-level map existed.
    slot = obj.get("slot") if isinstance(obj, dict) else None
    slot = slot if isinstance(slot, dict) else obj
    primary = slot.get("primary_source") if isinstance(slot, dict) else None
    if isinstance(primary, dict) and primary.get("ref") and primary.get("receipt"):
        return {str(primary["ref"]): str(primary["receipt"]).lower()}
    return {}


def _read_ledger_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        log.warning("press revision reconciliation: cannot read %s: %s", path, exc)
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception as exc:  # noqa: BLE001
            log.warning("press revision reconciliation: invalid ledger row: %s", exc)
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _mark_revision_state(path: Path, obj: dict, *, status: str, reason: str,
                         details: dict) -> bool:
    """Persist one terminal/non-emittable revision state exactly once."""

    if obj.get("status") == status and obj.get("revision_state") == details:
        return False
    obj["status"] = status
    obj["revision_state"] = details
    obj["quarantine_reason"] = reason
    obj[f"{status}_at"] = _now()
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return True


def reconcile_earnings_call_revisions(root: Path, cfg: dict) -> dict:
    """Reconcile mutable transcript revisions with immutable Press state.

    Pending stale drafts are retained but made non-emittable.  Once a prior
    revision has been published, a changed (or unverifiable legacy) revision is
    represented by an explicit ``correction_required`` staging record; it is
    never converted into a normal passing draft automatically.
    """

    paths = _paths(cfg, root)
    paths["staging"].mkdir(parents=True, exist_ok=True)
    current = desk_planner.earnings_call_revisions(root)

    published: dict[str, dict] = {}
    for row in _read_ledger_rows(paths["ledger"]):
        revisions = _source_revisions(row)
        for ref in row.get("sources") or []:
            ref = str(ref)
            if ref in current:
                # Append-only ledger order: the last row is the latest explicit
                # publication state for this stable story ref.
                published[ref] = {
                    "row": row,
                    "receipt": revisions.get(ref, ""),
                }

    mismatches: dict[str, dict] = {}
    for ref, state in current.items():
        prior = published.get(ref)
        if prior is None:
            continue
        current_receipt = str(state.get("receipt") or "")
        published_receipt = str(prior.get("receipt") or "")
        if not state.get("valid") or current_receipt != published_receipt:
            mismatches[ref] = {
                "current": state,
                "published": prior,
            }

    stage_rows: list[tuple[Path, dict]] = []
    for path in sorted(paths["staging"].glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            log.warning("press revision reconciliation: unreadable %s: %s", path, exc)
            continue
        if isinstance(obj, dict):
            stage_rows.append((path, obj))

    superseded = 0
    resolved = 0
    for path, obj in stage_rows:
        revisions = _source_revisions(obj)
        tracked_refs = [ref for ref in revisions if ref in current]
        # Only a ref THIS reconciliation owns can go missing from it.  Other
        # rails' revision receipts (official_feed:, whitehouse:, artifact:) sit
        # in the same map but were never transcript revisions; treating them as
        # vanished earnings refs would falsely supersede their records.
        missing_refs = [ref for ref in revisions
                        if ref not in current and ref.startswith("chronicle:")]

        if obj.get("status") == "correction_required":
            active = [
                ref for ref in tracked_refs
                if ref in mismatches
                and revisions.get(ref) == str(current[ref].get("receipt") or "")
            ]
            if active:
                continue
            details = {
                "state": "published_revision_now_current"
                if tracked_refs and not any(ref in mismatches for ref in tracked_refs)
                else "correction_record_superseded",
                "recorded": revisions,
                "current": {
                    ref: str(current[ref].get("receipt") or "") for ref in tracked_refs
                },
            }
            if _mark_revision_state(
                path, obj, status="resolved", reason=details["state"], details=details,
            ):
                resolved += 1
            continue

        stale_refs = [
            ref for ref in tracked_refs
            if not current[ref].get("valid")
            or revisions.get(ref) != str(current[ref].get("receipt") or "")
        ]
        published_changed = [ref for ref in tracked_refs if ref in mismatches]
        if missing_refs or stale_refs or published_changed:
            reason = (
                "published_revision_changed_requires_correction"
                if published_changed else "source_revision_changed"
            )
            details = {
                "state": reason,
                "recorded": revisions,
                "current": {
                    ref: str(current[ref].get("receipt") or "") for ref in tracked_refs
                },
                "missing_current_refs": missing_refs,
            }
            if _mark_revision_state(
                path, obj, status="superseded", reason=reason, details=details,
            ):
                superseded += 1

    correction_required = 0
    # Re-read the small staging set conceptually through stage_rows plus any
    # state changes above.  A matching correction record is idempotent and
    # prevents one file per run.
    existing_corrections: set[tuple[str, str]] = set()
    for _path, obj in stage_rows:
        if obj.get("status") != "correction_required":
            continue
        for ref, receipt in _source_revisions(obj).items():
            existing_corrections.add((ref, receipt))

    for ref, mismatch in sorted(mismatches.items()):
        state = mismatch["current"]
        receipt = str(state.get("receipt") or "")
        if (ref, receipt) in existing_corrections:
            continue
        prior = mismatch["published"]
        row = prior["row"]
        correction_id = (
            "press-correction-"
            + desk_planner.story_key(ref, receipt or "unverifiable")
        )
        correction = {
            "id": correction_id,
            "desk": row.get("desk") or "brief",
            "publication": row.get("publication") or "mastermind_news",
            "as_of": state.get("date") or date.today().isoformat(),
            "staged_at": _now(),
            "status": "correction_required",
            "correction_reason": (
                "published_source_revision_changed"
                if receipt else "current_source_revision_unverifiable"
            ),
            "sources": [ref],
            "source_revisions": {ref: receipt},
            "seed_refs": [],
            "slug": "",
            "draft": None,
            "validator_report": None,
            "attempts": [],
            "correction": {
                "state": "requires_editorial_correction",
                "auto_emit_allowed": False,
                "source_ref": ref,
                "published": {
                    "id": row.get("id"),
                    "receipt": prior.get("receipt") or None,
                    "url": row.get("url"),
                    "ts": row.get("ts"),
                },
                "current": state,
            },
        }
        (paths["staging"] / f"{correction_id}.json").write_text(
            json.dumps(correction, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        correction_required += 1

    return {
        "current_sources": len(current),
        "superseded": superseded,
        "resolved": resolved,
        "correction_required": correction_required,
        "published_mismatches": len(mismatches),
    }


def _write_stage_checkpoint(path: Path, item: dict, *, create: bool = False) -> None:
    """Durably retain one slot without exposing a partially written JSON record.

    The first write must never replace a prior attempt: even a caller bypassing
    planner deduplication cannot replay an unsettled provider effect. Later
    writes belong to that same invocation. These are ordinary staging records,
    never a publication approval or a separate execution queue.
    """
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False, indent=2, default=str) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if create:
            os.link(temporary, path)  # atomic exclusive create, including symlinks
        else:
            os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _stage_preplanned_slots(
    root: Path,
    cfg: dict,
    *,
    slots: list[dict],
    staging_dir: Path,
    run_date: str,
    state: writer.RunState,
    max_regenerations: int,
    taken_slugs: set[str],
    revision_reconciliation: dict | None = None,
    admission_receipt: dict | None = None,
    single_provider_attempt: bool = False,
    admitted_token_cap: bool = False,
    prepare_slot: Callable[[dict], dict] | None = None,
    before_write: Callable[[dict], None] | None = None,
) -> dict:
    """Write already-selected slots through the normal writer/validator rail.

    Selection and source-revision reconciliation deliberately live outside this
    helper.  The ordinary Press run supplies both; a future immutable ingress
    can supply one already-verified candidate without calling either mutable
    discovery surface.  ``admission_receipt`` is copied into the stage record
    solely as provenance — it never changes validation, status, retry, or emit
    behaviour.
    """
    staging_dir.mkdir(parents=True, exist_ok=True)
    if max_regenerations < 0:
        raise ValueError("max_regenerations must be non-negative")
    summary = {"run_at": _now(), "as_of": run_date, "planned": len(slots),
               "passed": 0, "quarantined": 0, "items": []}
    if revision_reconciliation is not None:
        summary["revision_reconciliation"] = revision_reconciliation

    for slot in slots:
        attempts: list[dict] = []
        prior: list[str] = []
        passed_payload = None
        out = staging_dir / f"{slot['id']}.json"
        checkpoint = _stage_item(slot, None, attempts, run_date,
                                 admission_receipt=admission_receipt)
        checkpoint.pop("quarantine_reason", None)
        checkpoint.update(status="in_progress",
                          progress={"phase": "provider_started", "attempt": 0})
        _write_stage_checkpoint(out, checkpoint, create=True)
        writer_kwargs: dict = {}
        if single_provider_attempt:
            writer_kwargs["single_provider_attempt"] = True
            if max_regenerations == 0:
                writer_kwargs["single_attempt"] = True
        if admitted_token_cap:
            writer_kwargs["admitted_token_cap"] = True

        for attempt in range(max_regenerations + 1):
            if attempt:
                checkpoint["progress"] = {"phase": "provider_started", "attempt": attempt}
                _write_stage_checkpoint(out, checkpoint)
            if prepare_slot is not None or before_write is not None:
                from engine.press.qbus_news import PrivateNewsUnavailable

                try:
                    if prepare_slot is not None:
                        prepared = prepare_slot(slot)
                        if not isinstance(prepared, dict) or prepared.get("id") != slot["id"]:
                            raise PrivateNewsUnavailable("source_preparation_changed_slot_identity")
                        slot = prepared
                        checkpoint.update(
                            slot=slot, sources=list(slot.get("sources") or []),
                            seed_refs=list(slot.get("seed_refs") or []),
                            source_revisions=dict(slot.get("source_revisions") or {}),
                        )
                        _write_stage_checkpoint(out, checkpoint)
                    # Permission and identity checks run AFTER the provenance
                    # checkpoint, immediately before each actual writer call.
                    if before_write is not None:
                        before_write(slot)
                except PrivateNewsUnavailable as exc:
                    attempts.append({"attempt": attempt, "ok": False, "reason": str(exc)})
                    break
            if before_write is not None:
                # Bind the prepared attempt for a final check after provider
                # construction and at the actual external request boundary.
                writer_kwargs["private_admission_check"] = lambda prepared=slot: before_write(prepared)
            res = writer.write(slot, cfg, state=state, attempt=attempt,
                               prior_failures=prior or None, **writer_kwargs)
            if not res.get("ok"):
                attempt_row = {"attempt": attempt, "ok": False,
                               "reason": res.get("reason")}
                if admitted_token_cap:
                    attempt_row["provider"] = res.get("provider")
                for key in ("token_cap", "provider_usage"):
                    if key in res:
                        attempt_row[key] = res[key]
                attempts.append(attempt_row)
                if res.get("reason") in ("circuit_open", "token_budget_exhausted",
                                         "no_provider", "llm_disabled"):
                    break                       # a run-level stop, not a draft problem
                prior = [f"writer: {res.get('reason')}"]
                continue

            draft = dict(res["draft"])
            draft["slug"] = _unique_slug(draft.get("slug") or slot.get("slug_hint") or "",
                                         slot, taken_slugs)
            checkpoint.update(draft=draft, slug=draft["slug"],
                              provider=res.get("provider"), model=res.get("model"),
                              retained_draft_attempt=attempt,
                              validator_report=None,
                              writer_state=res.get("state"),
                              progress={"phase": "validation_pending", "attempt": attempt})
            for key in ("token_cap", "provider_usage"):
                if key in res:
                    checkpoint[key] = res[key]
            _write_stage_checkpoint(out, checkpoint)
            report = validators.validate(draft, slot, cfg, root=root)
            checkpoint["validator_report"] = report
            attempt_row = {"attempt": attempt, "ok": bool(report["ok"]),
                           "failed": report["failed"],
                           "our_value_share": report.get("our_value_share"),
                           "max_block_jaccard": report.get("max_block_jaccard"),
                           "provider": res.get("provider")}
            for key in ("token_cap", "provider_usage"):
                if key in res:
                    attempt_row[key] = res[key]
            attempts.append(attempt_row)
            if report["ok"]:
                taken_slugs.add(draft["slug"])
                passed_payload = (draft, report, res)
                break
            prior = [f"{c['name']}: {c['detail']}" for c in report["checks"] if not c["ok"]]

        item = _stage_item(
            slot,
            passed_payload,
            attempts,
            run_date,
            admission_receipt=admission_receipt,
        )
        if passed_payload is None and checkpoint.get("draft") is not None:
            # A failed validator verdict is evidence, not permission to erase
            # the returned prose. Retain its exact last draft/report while
            # keeping the terminal status and quarantine reason unchanged.
            # A later provider failure may follow this draft; its own attempt
            # remains in attempts, and retained_draft_attempt identifies which
            # response these fields describe.
            for key in ("draft", "slug", "provider", "model", "writer_state",
                        "retained_draft_attempt", "validator_report",
                        "token_cap", "provider_usage"):
                if key in checkpoint:
                    item[key] = checkpoint[key]
        _write_stage_checkpoint(out, item)
        summary["items"].append({"id": slot["id"], "desk": slot["desk"],
                                 "status": item["status"],
                                 "reason": item.get("quarantine_reason", "")})
        if item["status"] == "passed":
            summary["passed"] += 1
        else:
            summary["quarantined"] += 1
            log.warning("press: slot %s quarantined — %s", slot["id"],
                        item.get("quarantine_reason"))

    summary["writer_state"] = state.snapshot()
    _write_stage_checkpoint(staging_dir / "_run_summary.json", summary)

    _annotate("notice", "press_staging",
              f"press staging: {summary['passed']} passed, "
              f"{summary['quarantined']} quarantined of {summary['planned']} planned "
              f"(tokens {state.tokens_used}/{state.token_budget})")
    if summary["planned"] and not summary["passed"]:
        _annotate("warning", "press_staging_empty",
                  "press staging produced NO passing draft — every planned slot was "
                  "quarantined or dropped. A thin day is legal; a permanently thin "
                  "lane is a defect. Check data/press/staging/ for reasons.")
    return summary


def run_staging(root: Path, cfg: dict, *, desks=None, as_of=None,
                max_slots: int | None = None, single_attempt: bool = False) -> dict:
    """Plan, reconcile, then stage the ordinary multi-slot Press run.

    Qualification runs may opt into one provider-adapter invocation per slot,
    disabling Anthropic SDK retries, Press fallback and draft regeneration.
    Codex CLI internal requests are outside this bound. This does not change
    source admission, token accounting, validation or publication authority.
    """
    paths = _paths(cfg, root)
    # Preserve the generic lane's original timing: its staging directory
    # existed before either mutable discovery step ran.
    paths["staging"].mkdir(parents=True, exist_ok=True)

    run_date = as_of or date.today().isoformat()
    revision_reconciliation = reconcile_earnings_call_revisions(root, cfg)
    slots = desk_planner.plan(desks, as_of=run_date, root=root, cfg=cfg)
    if max_slots is not None:
        slots = slots[:max_slots]

    llm_cfg = (cfg.get("llm") or {})
    state = writer.RunState(
        token_budget=_env_int("PRESS_RUN_TOKEN_BUDGET",
                              int(llm_cfg.get("run_token_budget") or 240_000)),
        breaker_threshold=_env_int("PRESS_CIRCUIT_BREAKER_FAILURES",
                                   int(llm_cfg.get("circuit_breaker_consecutive_failures") or 3)),
    )
    max_regen = int(((cfg.get("quarantine") or {}).get("max_regenerations")) or 2)
    if single_attempt:
        max_regen = 0

    _pub_refs, pub_slugs = desk_planner.published_refs(root, cfg)
    _stg_refs, stg_slugs = desk_planner.staged_refs(root, cfg)
    taken = desk_planner.taken_slugs(root) | pub_slugs | stg_slugs
    return _stage_preplanned_slots(
        root,
        cfg,
        slots=slots,
        staging_dir=paths["staging"],
        run_date=run_date,
        state=state,
        max_regenerations=max_regen,
        taken_slugs=taken,
        revision_reconciliation=revision_reconciliation,
        single_provider_attempt=single_attempt,
    )


def run_admitted_earnings_staging(
    root: Path,
    cfg: dict,
    *,
    slot: dict,
    admission_receipt: dict,
    staging_dir: str | Path,
) -> dict:
    """Stage one preverified earnings candidate in an isolated directory.

    This is intentionally not an approval verifier or an emit path.  The
    caller must already have verified the immutable admission receipt.  We
    retain it verbatim for provenance, make exactly one writer attempt, and
    leave the existing generic staging tree untouched for ``run_emit``.
    """
    if not isinstance(slot, dict) or not slot:
        raise ValueError("admitted earnings staging requires one preverified slot object")
    if not isinstance(admission_receipt, dict) or not admission_receipt:
        raise ValueError("admitted earnings staging requires one immutable admission receipt object")
    slot_id = slot.get("id")
    if (
        not isinstance(slot_id, str)
        or not slot_id
        or Path(slot_id).name != slot_id
    ):
        raise ValueError("admitted earnings slot id must be a safe filename")

    destination = Path(staging_dir)
    generic_staging = _paths(cfg, root)["staging"]
    resolved_destination = destination.resolve()
    resolved_generic = generic_staging.resolve()
    if (
        resolved_destination == resolved_generic
        or resolved_generic in resolved_destination.parents
    ):
        raise ValueError("admitted earnings staging must use a dedicated non-generic directory")

    llm_cfg = (cfg.get("llm") or {})
    configured_budget = _env_int(
        "PRESS_RUN_TOKEN_BUDGET",
        int(llm_cfg.get("run_token_budget") or 240_000),
    )
    state = writer.RunState(
        token_budget=min(configured_budget, 12_000),
        breaker_threshold=_env_int(
            "PRESS_CIRCUIT_BREAKER_FAILURES",
            int(llm_cfg.get("circuit_breaker_consecutive_failures") or 3),
        ),
    )
    run_date = str(slot.get("as_of") or date.today().isoformat())
    return _stage_preplanned_slots(
        root,
        cfg,
        slots=[slot],
        staging_dir=destination,
        run_date=run_date,
        state=state,
        max_regenerations=0,
        taken_slugs=set(),
        admission_receipt=dict(admission_receipt),
        single_provider_attempt=True,
        admitted_token_cap=True,
    )


def run_private_news_staging(
    root: Path, cfg: dict, *, slot: dict, database, universe_path,
    receipt_paths, staging_dir: str | Path,
) -> dict:
    """Ground one existing Press slot with blog_draft news; never enable emit.

    The private directory is outside all generic staging/content/site paths.
    Every attempt rebuilds from the original slot and checks admission again
    after checkpoint IO. Provider fallback and regeneration remain disabled.
    """
    import copy
    from engine.press import qbus_news

    source_slot = copy.deepcopy(slot)
    candidate = qbus_news.private_slot(source_slot)
    if _is_canonical_story_slot(source_slot) or _is_private_official_stage({"slot": source_slot}):
        raise qbus_news.PrivateNewsUnavailable("qbus_draft_requires_ordinary_press_slot")
    receipt_paths = tuple(receipt_paths)
    if not receipt_paths:
        raise qbus_news.PrivateNewsUnavailable("qbus_draft_rights_required")
    destination = Path(staging_dir).resolve()
    paths = _paths(cfg, root)
    forbidden = [
        paths["staging"].resolve(), paths["content"].resolve(),
        (root / "content").resolve(), (root / "site").resolve(),
        (root / "properties").resolve(),
    ]
    # Press properties are independently served publication trees, not merely
    # source inputs. Include actual configured roots as well as canonical roots.
    for publication in (cfg.get("publications") or {}).values():
        if isinstance(publication, dict):
            for key in ("property_tree", "content_dir"):
                value = publication.get(key)
                if isinstance(value, str) and value:
                    forbidden.append((root / value).resolve())
    if any(destination == path or path in destination.parents
           or destination in path.parents for path in forbidden):
        raise qbus_news.PrivateNewsUnavailable("qbus_draft_requires_private_directory")
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)

    def prepare(_previous: dict) -> dict:
        # Never append new reports to an earlier attempt's evidence/facts.
        return qbus_news.prepare_slot(
            source_slot, database=database, universe_path=universe_path,
            receipt_paths=receipt_paths,
        )

    def verify(prepared: dict) -> None:
        qbus_news.verify_slot(
            prepared, universe_path=universe_path, receipt_paths=receipt_paths,
        )

    llm_cfg = cfg.get("llm") or {}
    state = writer.RunState(
        token_budget=min(_env_int(
            "PRESS_RUN_TOKEN_BUDGET", int(llm_cfg.get("run_token_budget") or 240_000)
        ), 12_000),
        breaker_threshold=_env_int(
            "PRESS_CIRCUIT_BREAKER_FAILURES",
            int(llm_cfg.get("circuit_breaker_consecutive_failures") or 3),
        ),
    )
    return _stage_preplanned_slots(
        root, cfg, slots=[candidate], staging_dir=destination,
        run_date=str(source_slot.get("as_of") or ""),
        state=state, max_regenerations=0, taken_slugs=set(),
        single_provider_attempt=True, admitted_token_cap=True,
        prepare_slot=prepare, before_write=verify,
    )


def _stage_item(
    slot: dict,
    passed_payload,
    attempts: list[dict],
    run_date: str,
    *,
    admission_receipt: dict | None = None,
) -> dict:
    """One staging record — the whole audit trail for a slot, pass or fail."""
    base = {
        "id": slot["id"],
        "desk": slot["desk"],
        "publication": slot.get("publication"),
        "as_of": slot.get("as_of") or run_date,
        "staged_at": _now(),
        "sources": list(slot.get("sources") or []),
        "source_revisions": dict(slot.get("source_revisions") or {}),
        "seed_refs": list(slot.get("seed_refs") or []),
        "slot": slot,
        "attempts": attempts,
    }
    if admission_receipt is not None:
        base["provenance"] = {"admission_receipt": dict(admission_receipt)}
    if passed_payload is None:
        # Explicit branches, not an `or` chain: `"validators: " + ""` is a
        # TRUTHY empty-list join, so the chained form could never reach its own
        # fallback and an attempt-less slot was quarantined with the reason
        # "validators: " — a blank explanation in the one field the operator
        # reads to find out why the day was thin.
        last = attempts[-1] if attempts else {}
        failed = last.get("failed") or []
        if last.get("reason"):
            reason = str(last["reason"])
        elif failed:
            reason = "validators: " + ", ".join(failed)
        else:
            reason = "no draft produced"
        base.update({"status": "quarantined", "slug": "", "draft": None,
                     "validator_report": None, "quarantine_reason": reason})
        return base
    draft, report, res = passed_payload
    base.update({
        "status": "passed",
        "slug": draft["slug"],
        "draft": draft,
        "validator_report": report,
        "provider": res.get("provider"),
        "model": res.get("model"),
    })
    return base


# ─────────────────────────────────────────────────────────────────────────────
# EMIT
# ─────────────────────────────────────────────────────────────────────────────


def _frontmatter_md(draft: dict, slot: dict, cfg: dict) -> str:
    """The .md file: frontmatter fence + the HTML body fragment.

    Frontmatter keys and their order follow the six hand-written posts in
    content/seo/blog/ so the estate reads as one corpus.
    """
    fm = validators.frontmatter_for(draft, slot, cfg)
    title = str(fm["title"]).replace('"', "'")
    desc = str(fm["description"]).replace('"', "'")
    lines = [
        "---",
        f"slug: {fm['slug']}",
        "family: article",
        f'title: "{title}"',
        f'description: "{desc}"',
        f"cluster: {fm['cluster']}",
        f"published: {fm['published']}",
        f"updated: {fm['updated']}",
        "---",
        draft["body_html"].strip(),
        "",
    ]
    return "\n".join(lines)


# daily.yml's alert-ticker tag. This lane cannot replay that sweep, so it
# carries the committed page's tag across instead of dropping it.
_WHB_TAG_RE = re.compile(rb"[ \t]*<script[^>]*\bdata-whb\b[^>]*></script>\n?")


def _carry_wh_banner(rendered: bytes, committed: Path) -> bytes:
    """Re-attach the committed page's wh_banner tag to a legitimately-changed page.

    `_same_page` stops us rewriting pages that only DIFFER by this tag, but a
    page that genuinely changed (blog/index.html gaining a card) still gets
    rendered without it, because only daily.yml injects it. `--check`
    normalises the tag away so it would never notice — and the page would ship
    without its alert ticker until the next nightly. One day of a regressed
    page is a day too many for a tag we can simply carry over.
    """
    if not committed.exists() or committed.suffix != ".html":
        return rendered
    if _WHB_TAG_RE.search(rendered):
        return rendered
    m = _WHB_TAG_RE.search(committed.read_bytes())
    if not m:
        return rendered
    tag = m.group(0)
    # Re-insert where the sweep puts it: immediately before </body>.
    idx = rendered.rfind(b"</body>")
    if idx == -1:
        return rendered
    return rendered[:idx] + tag + rendered[idx:]


def _same_page(rendered: Path, committed: Path) -> bool:
    """True when the committed file already IS this render, in the projection
    this lane is accountable for.

    HTML uses build_free_content._comparable for the separately owned banner
    and asset stamps. A missing common-renderer Shared Shell block is projected
    in memory before that comparison; an existing block is never regenerated.
    Everything else (the RSS feed) remains a plain byte compare.
    """
    if not committed.exists():
        return False
    a, b = rendered.read_bytes(), committed.read_bytes()
    if a == b:
        return True
    if rendered.suffix != ".html":
        return False
    from scripts.build_free_content import _comparable  # noqa: PLC0415
    from lib.pages import dbase_prefix  # noqa: PLC0415
    from lib.shared_shell import END, START, inject_shared_shell_text  # noqa: PLC0415

    def comparison_text(raw: bytes, path: Path) -> str:
        text = raw.decode("utf-8")
        if START not in text and END not in text:
            # The common renderer owns this additive sweep. Explicit digests
            # keep this comparison pure; _comparable already ignores stamp values.
            # Never regenerate a present block: doing so could erase extra content
            # or malformed markup inside its markers and hide a real difference.
            text = inject_shared_shell_text(
                text, dbase_prefix(path), version="00000000", css_version="00000000",
            )
        return _comparable(text)

    try:
        return comparison_text(a, rendered) == comparison_text(b, committed)
    except (UnicodeDecodeError, ValueError):
        return False


def _render_blog_subtree(root: Path) -> tuple[list[str], list[str]]:
    """Render the estate to a temp tree, replay the render-lane sweeps, and copy
    ONLY site/blog/** back.  Returns (copied_relpaths, unowned_new_assets).

    Reuses build_free_content's own sweep helpers so what lands in site/ is the
    exact post-image `--check` compares against.  tests/test_press_run.py pins
    these helper names: a rename upstream must fail loudly here, not quietly
    ship raw pages that turn the drift check red on someone else's PR.

    A page is only rewritten when it differs in the projection this lane is
    ACCOUNTABLE for — `_comparable()`, the same projection `--check` uses.  Two
    sweeps cannot be replayed here: daily.yml's wh_banner tag, and the `?v=`
    asset stamps whose hashes track files this lane does not own.  Copying on a
    raw byte diff would strip the banner from every already-committed article on
    the way past — six unrelated pages rewritten, and invisible to `--check`
    because it normalises exactly those two things away.
    """
    from scripts.build_free_content import (  # noqa: PLC0415
        _comparable, _normalize_like_render_lane, _seed_hashable_assets, render_all,
    )

    copied: list[str] = []
    unowned: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_site = Path(tmp) / "site"      # named "site" so lib.pages resolves depth
        tmp_site.mkdir(parents=True, exist_ok=True)
        render_all(tmp_site)
        _seed_hashable_assets(tmp_site)
        _normalize_like_render_lane(tmp_site)

        for src in sorted((tmp_site / "blog").rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(tmp_site)
            dst = root / "site" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if _same_page(src, dst):
                continue
            dst.write_bytes(_carry_wh_banner(src.read_bytes(), dst))
            copied.append(str(rel))

        # externalize_css lifts inline <style> into site/assets/css/<hash>.css.
        # Every estate article shares one stylesheet, so a press article should
        # never mint a new one — but if it does, the workflow's git-add scope
        # (content/seo/blog + site/blog + the ledger) would leave it behind and
        # `build_free_content --check` would go red with "MISSING in site/".
        # Say so loudly rather than discovering it in someone else's PR.
        for src in sorted((tmp_site / "assets" / "css").glob("*.css")):
            if not (root / "site" / "assets" / "css" / src.name).exists():
                unowned.append(f"site/assets/css/{src.name}")

    return copied, unowned


def run_emit(root: Path, cfg: dict, *, reviewed_promotion: dict | None = None) -> dict:
    paths = _paths(cfg, root)
    stage = paths["staging"]
    if not stage.exists():
        _annotate("notice", "press_emit", "press emit: no staging directory — nothing to do")
        return {"emitted": 0, "items": []}

    # Re-check the exact Chronicle receipt at the last safe boundary.  A call
    # can be corrected after staging; no previously-passing draft is allowed to
    # cross that race as stale copy.
    revision_reconciliation = reconcile_earnings_call_revisions(root, cfg)

    sitemap = root / "site" / "sitemap.xml"
    sitemap_before = sitemap.read_bytes() if sitemap.exists() else None

    items = []
    for path in sorted(stage.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            log.warning("press emit: unreadable staging file %s: %s", path, exc)
            continue
        if isinstance(obj, dict) and obj.get("status") == "passed" and obj.get("draft"):
            slot = obj.get("slot") if isinstance(obj.get("slot"), dict) else {}
            from engine.press.qbus_news import is_private_stage

            if is_private_stage(obj):
                obj["status"] = "approval_required"
                obj["quarantine_reason"] = (
                    "private qbus news draft: source processing permission "
                    "does not authorize public-article release"
                )
                _write_stage_checkpoint(path, obj)
                _annotate("warning", "press_emit_qbus_approval",
                          f"press emit: private news candidate {obj.get('id')} not emitted")
                continue
            if _is_unverified_earnings_story_stage(obj):
                obj["status"] = "approval_required"
                obj["quarantine_reason"] = (
                    "earnings story publishing is disabled until a separate "
                    "verified-approval compiler and immutable ingress exist"
                )
                path.write_text(
                    json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                    encoding="utf-8",
                )
                _annotate(
                    "warning", "press_emit_canonical_approval",
                    f"press emit: canonical slot {obj.get('id')} requires verified approval",
                )
                continue
            if _is_private_official_stage(obj):
                # Candidate-only qualification: staging proved the source, not
                # a release grant.  A passed deterministic suite changes no
                # approval state, so this refuses BEFORE any revalidation or
                # content/site/ledger write.
                obj["status"] = "approval_required"
                obj["quarantine_reason"] = (
                    "privately staged external candidate (official-feed or issuer): the candidate-only "
                    "qualification conveys no public-article approval"
                )
                path.write_text(
                    json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                    encoding="utf-8",
                )
                _annotate(
                    "warning", "press_emit_external_approval",
                    f"press emit: private external candidate {obj.get('id')} requires "
                    f"public-article approval — not emitted",
                )
                continue
            # Staging is mutable: its saved report describes the earlier draft,
            # not necessarily the copy we just loaded. Re-run the same suite
            # before ANY content/render/ledger write and retain the fresh report
            # for both quarantine and the eventual ledger row. The validator's
            # slot-id exclusion keeps this candidate out of its staged peers.
            report = validators.validate(obj["draft"], slot, cfg, root=root)
            obj["validator_report"] = report
            if not report["ok"]:
                obj["status"] = "quarantined"
                obj["quarantine_reason"] = "validators at emit: " + ", ".join(report["failed"])
            path.write_text(
                json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
            if not report["ok"]:
                _annotate(
                    "warning", "press_emit_validation",
                    f"press emit: slot {obj.get('id')} quarantined — {obj['quarantine_reason']}",
                )
                continue
            items.append((path, obj))

    if not items:
        _annotate("notice", "press_emit",
                  "press emit: no passing staged drafts — nothing published")
        return {"emitted": 0, "items": [],
                "revision_reconciliation": revision_reconciliation}

    paths["content"].mkdir(parents=True, exist_ok=True)
    written: list[dict] = []
    for path, obj in items:
        slot = obj.get("slot") or {}
        draft = obj["draft"]
        route = _emit_route(cfg, root, paths, obj, draft["slug"])
        md_path = route["md_dir"] / f"{draft['slug']}.md"
        if md_path.exists():
            # The slug was free when it was staged and is not now — another lane
            # or an earlier emit took it.  Re-slugging here would bypass the
            # frontmatter check that passed against THIS slug, so quarantine it.
            obj["status"] = "quarantined"
            obj["quarantine_reason"] = f"slug collision at emit: {draft['slug']}.md exists"
            path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                            encoding="utf-8")
            _annotate("warning", "press_emit_collision",
                      f"press emit: slug {draft['slug']} already exists — slot quarantined")
            continue
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_frontmatter_md(draft, slot, cfg), encoding="utf-8")
        written.append({"staging_path": path, "obj": obj, "md_path": md_path,
                        "route": route})

    if not written:
        return {"emitted": 0, "items": []}

    # The rows are built BEFORE the render so a routed publication's property can
    # be re-rendered WITH the piece it is publishing in this same pass. They are
    # appended only after everything succeeds, so a failed render still leaves
    # the ledger untouched.
    ledger_rows = []
    for w in written:
        obj, draft, route = w["obj"], w["obj"]["draft"], w["route"]
        ledger_rows.append({
            "id": obj["id"],
            "ts": _now(),
            "desk": obj.get("desk"),
            "publication": route["publication"] or obj.get("publication"),
            "slug": draft["slug"],
            # W1.5 additive fields. `url` is what makes the cutover
            # migration-free: the row states where IT was published, so no
            # historic row ever needs rewriting. `title` lets a consumer list
            # the archive without opening every .md.
            "title": str(draft.get("title") or ""),
            "url": route["url"],
            "sources": list(obj.get("sources") or []),
            "source_revisions": dict(_source_revisions(obj)),
            "seed_refs": list(obj.get("seed_refs") or []),
            "validator_report": obj.get("validator_report"),
            **({"reviewed_promotion": reviewed_promotion} if reviewed_promotion else {}),
            "urls": [route["url"]],
        })

    # ── ATOMIC FROM HERE ─────────────────────────────────────────────────────
    # The .md files are already on disk and the render is about to rewrite
    # site/blog/ (and, post-cutover, the property trees). If anything below
    # raises, the tree must go back to exactly what it was: a run that leaves
    # .md files with no matching rendered pages is the render-clobber class —
    # `build_free_content --check` reports the missing pages and the NEXT PR
    # inherits a red estate it did not cause.
    site_snapshot = {p: p.read_bytes()
                     for p in (root / "site" / "blog").rglob("*") if p.is_file()}
    routed_pubs: list[str] = []
    for w in written:
        key = w["route"]["publication"]
        if w["route"]["routed"] and key not in routed_pubs:
            routed_pubs.append(key)
    tree_snapshots: dict[Path, dict] = {}
    for key in routed_pubs:
        tree = properties.property_tree_path(root, cfg, key)
        tree_snapshots[tree] = {p: p.read_bytes()
                                for p in tree.rglob("*") if p.is_file()} \
            if tree.exists() else {}

    try:
        # A routed piece never touches the free-content estate, so an emit whose
        # every piece is routed skips that render entirely. Pre-cutover nothing
        # is routed and this is the existing call, unchanged.
        if any(not w["route"]["routed"] for w in written):
            copied, unowned = _render_blog_subtree(root)
            if unowned:
                _annotate("warning", "press_emit_unowned_asset",
                          "press emit produced asset(s) outside the workflow's git-add "
                          "scope: " + ", ".join(unowned)
                          + " — commit them or the estate drift check will go red.")
        else:
            copied = []

        for key in routed_pubs:
            pending = [row for row, w in zip(ledger_rows, written)
                       if w["route"]["routed"] and w["route"]["publication"] == key]
            properties.render_property(root, cfg, key, extra_rows=pending)

        # The nightly owns the sitemap.  Assert it, do not assume it.
        sitemap_after = sitemap.read_bytes() if sitemap.exists() else None
        if sitemap_after != sitemap_before:
            raise RuntimeError("press emit modified site/sitemap.xml — the nightly owns it")
    except BaseException:
        _rollback_emit(root, written, site_snapshot, tree_snapshots)
        _annotate("error", "press_emit_rollback",
                  "press emit failed after writing content — rolled the tree back "
                  "to its pre-emit state (no .md without a rendered page).")
        raise

    try:
        append_ledger(paths["ledger"], ledger_rows)
    except BaseException:
        _rollback_emit(root, written, site_snapshot, tree_snapshots)
        _annotate("error", "press_emit_rollback",
                  "press ledger append failed — rolled the tree back. Published "
                  "content with no ledger row is an unrecorded publication.")
        raise

    # Staged items that are now in the ledger are consumed.  Quarantined items
    # deliberately stay put — the admin panel is where the operator reads them.
    for w in written:
        try:
            w["staging_path"].unlink()
        except OSError:
            pass

    routed_note = (f"; properties re-rendered: {', '.join(routed_pubs)}"
                   if routed_pubs else "")
    _annotate("notice", "press_emit",
              f"press emit: {len(ledger_rows)} article(s) published; "
              f"{len(copied)} file(s) written under site/blog/{routed_note}")
    return {"emitted": len(ledger_rows), "items": ledger_rows, "site_files": copied,
            "properties": routed_pubs,
            "revision_reconciliation": revision_reconciliation}


def _restore_tree(base: Path, snapshot: dict) -> None:
    """Restore one rendered tree to `snapshot`, removing anything it gained.

    Best-effort per path: one unwritable file must not stop the rest of the
    rollback.  Empty directories are left behind on purpose — they hold no
    content, and pruning them is how a rollback grows a second failure mode.
    """
    if not base.exists():
        return
    for path in list(base.rglob("*")):
        if not path.is_file():
            continue
        try:
            if path in snapshot:
                if path.read_bytes() != snapshot[path]:
                    path.write_bytes(snapshot[path])
            else:
                path.unlink()                # added by the failed render
        except OSError as exc:  # noqa: PERF203
            log.warning("press rollback: could not restore %s: %s", path, exc)


def _rollback_emit(root: Path, written: list[dict], site_snapshot: dict,
                   tree_snapshots: dict | None = None) -> None:
    """Put the tree back exactly as the emit found it.

    Deletes every .md this run created — which after cutover means the routed
    publication's content_dir as well as content/seo/blog, because `md_path` is
    the ROUTED path — and restores every site/blog file and every property-tree
    file that existed before it, removing any the render added.
    """
    for w in written:
        try:
            w["md_path"].unlink(missing_ok=True)
        except OSError as exc:  # noqa: PERF203
            log.warning("press rollback: could not remove %s: %s", w["md_path"], exc)
    _restore_tree(root / "site" / "blog", site_snapshot)
    for tree, snapshot in (tree_snapshots or {}).items():
        _restore_tree(tree, snapshot)


def append_ledger(path: Path, rows: list[dict]) -> int:
    """Append-only.  The press --emit path is the SOLE writer of this file."""
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return len(rows)


# Reviewed bundles are release inputs committed through the normal protected PR.
# They attest an editorial decision over exact bytes, not new approval for the
# private official/earnings rails. No model or alternate publisher is involved.
_REVIEWED_PREFIX = "research/agentic_media/press_reviewed/"
_REVIEWED_REPO = "mastermindx-market-intelligence/macro"
_REVIEWED_SCOPES = (
    "engine/press/validators.py", "engine/press/adjusted_baseline.py",
    "engine/marketing/copywriter.py", "engine/marketing/sentinel.py",
    "config/press.yml", "scripts/run_press.py", "scripts/build_free_content.py",
    ".github/workflows/press-publish.yml",
)


def _promotion_git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        raise ValueError("reviewed promotion Git evidence unavailable") from exc


def _promotion_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    if (not isinstance(relative, str) or not relative or path.is_absolute()
            or any(part in (".", "..") for part in relative.split("/"))
            or "\\" in relative or any(ord(c) < 32 for c in relative)):
        raise ValueError("unsafe reviewed promotion path")
    resolved = root / path
    if any(p.is_symlink() for p in (resolved, *resolved.parents) if p.is_relative_to(root)):
        raise ValueError("symlink in reviewed promotion path")
    return resolved


def _promotion_refs(item: dict) -> set[str]:
    return {str(ref) for holder in (item, item.get("slot") or {})
            for ref in holder.get("sources", []) if isinstance(ref, str)}


def _promotion_item(raw: bytes, slot_id: str) -> dict:
    try:
        item = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid reviewed stage JSON") from exc
    if (not isinstance(item, dict) or item.get("id") != slot_id
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", slot_id)
            or item.get("status") != "passed" or not isinstance(item.get("draft"), dict)
            or not isinstance(item.get("slot"), dict) or item["slot"].get("id") != slot_id
            or (item.get("validator_report") or {}).get("ok") is not True
            or not _promotion_refs(item)):
        raise ValueError("reviewed stage is not one passing identified slot")
    if _is_unverified_earnings_story_stage(item) or _is_private_official_stage(item):
        raise ValueError("reviewed bundle cannot approve private official or earnings rail")
    return item


def _promotion_dependencies(root: Path, head: str, item: dict) -> dict[str, str]:
    """Freeze semantic article inputs, not a whole catalog or the UI estate.

    Report and Chronicle selectors ignore unrelated appends. Immutable hashes
    already in the exact stage remain in the review; private provenance paths
    are never dereferenced or made into new repository publication requirements.
    Current templates/assets are intentionally left to the normal renderer.
    """
    snapshot = {}

    def bind(relative: str, key: str, select=lambda raw: raw):
        path = _promotion_path(root, relative)
        reviewed = select(_promotion_git(root, "show", f"{head}:{relative}"))
        current = select(_promotion_git(root, "show", f"HEAD:{relative}"))
        working = select(path.read_bytes()) if path.is_file() else current
        if reviewed != current or reviewed != working:
            raise ValueError(f"reviewed source dependency is missing or changed: {key}")
        snapshot[key] = hashlib.sha256(reviewed).hexdigest()

    files = _promotion_git(root, "ls-tree", "-r", "--name-only", head,
                           "--", *_REVIEWED_SCOPES).decode().splitlines()
    for relative in files:
        bind(relative, relative)
    if "config/press.yml" not in snapshot:
        raise ValueError("reviewed source dependencies missing Press config")

    refs = set()
    for holder in (item, item.get("slot") or {}):
        refs.update(holder.get("sources") or [])
        refs.update(holder.get("seed_refs") or [])
        refs.update((holder.get("source_revisions") or {}).keys())
        for fact in holder.get("facts") or []:
            if isinstance(fact, dict):
                # Artifact revisions are actual numerical evidence. No private
                # source/provenance path is inferred from a report's metadata.
                if str(fact.get("ref") or "").startswith("artifact:"):
                    refs.add(fact["ref"])
                refs.update((fact.get("input_revisions") or {}).keys())
    for ref in sorted(refs):
        if not isinstance(ref, str):
            raise ValueError("invalid reviewed source reference")
        if ref.startswith("artifact:"):
            bind(ref.removeprefix("artifact:").split("#", 1)[0], ref)
        elif ref.startswith("research_vault:"):
            report_id = ref.removeprefix("research_vault:")
            def report_entry(raw, report_id=report_id):
                rows = [row for row in json.loads(raw).get("items", [])
                        if isinstance(row, dict) and row.get("id") == report_id]
                if len(rows) != 1:
                    raise ValueError("reviewed report entry missing or ambiguous")
                return json.dumps(rows[0], sort_keys=True, ensure_ascii=False,
                                  separators=(",", ":")).encode()
            bind("data/research_vault/catalog.json", ref, report_entry)
        elif ref.startswith("chronicle:"):
            source_ref = ref.removeprefix("chronicle:")
            def event_entry(raw, source_ref=source_ref):
                rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
                matches = [row for row in rows if isinstance(row, dict)
                           and (row.get("source_ref") or row.get("id")) == source_ref]
                if len(matches) != 1:
                    raise ValueError("reviewed Chronicle entry missing or ambiguous")
                return json.dumps(matches[0], sort_keys=True, ensure_ascii=False,
                                  separators=(",", ":")).encode()
            bind("data/chronicle/events.jsonl", ref, event_entry)
    return snapshot


def prepare_reviewed_bundle(root: Path, stage_path: Path, output_path: Path,
                            *, confirm_reviewed: bool = False) -> dict:
    """Package already-reviewed local bytes; never edit the stage or call a writer.

    The caller must commit this bundle via the existing protected release path.
    Its digest is then an explicit workflow input. This function grants nothing
    to source-ready private rails, even if their mutable report claims approval.
    """
    if not confirm_reviewed:
        raise ValueError("explicit editorial confirmation required")
    stage_path = stage_path if stage_path.is_absolute() else root / stage_path
    output_path = output_path if output_path.is_absolute() else root / output_path
    relative = output_path.relative_to(root).as_posix()
    if not relative.startswith(_REVIEWED_PREFIX) or not relative.endswith(".json"):
        raise ValueError("reviewed bundle must use the repository review directory")
    _promotion_path(root, relative)
    raw = stage_path.read_bytes()
    obj = json.loads(raw)
    item = _promotion_item(raw, str(obj.get("id") or ""))
    head = _promotion_git(root, "rev-parse", "HEAD").decode().strip()
    bundle = {"schema": "press.reviewed_bundle/v1", "repository": _REVIEWED_REPO,
              "bundle_path": relative, "source_head": head, "slot_id": item["id"],
              "stage_sha256": hashlib.sha256(raw).hexdigest(),
              "stage_json": raw.decode("utf-8"),
              "dependencies": _promotion_dependencies(root, head, item)}
    payload = (json.dumps(bundle, ensure_ascii=False, indent=2) + "\n").encode()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("xb") as handle:
        handle.write(payload)
    return {"bundle_path": relative, "bundle_sha256": hashlib.sha256(payload).hexdigest(),
            "slot_id": item["id"], "source_head": head}


def _promotion_workflow() -> dict[str, str]:
    keys = ("GITHUB_REPOSITORY", "GITHUB_WORKFLOW_REF", "GITHUB_REF", "GITHUB_SHA",
            "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")
    binding = {key: os.environ.get(key, "") for key in keys}
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or binding["GITHUB_REPOSITORY"] != _REVIEWED_REPO
            or binding["GITHUB_REF"] != "refs/heads/main"
            or binding["GITHUB_WORKFLOW_REF"] != (
                _REVIEWED_REPO + "/.github/workflows/press-publish.yml@refs/heads/main")
            or not re.fullmatch(r"[0-9a-f]{40}", binding["GITHUB_SHA"])
            or not all(re.fullmatch(r"[0-9]+", binding[key])
                       for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"))):
        raise ValueError("reviewed promotion requires the main Press workflow and repository")
    return binding


def check_reviewed_bundle(root: Path, cfg: dict, bundle_path: Path,
                          expected_sha256: str, expected_slot: str, *, published=False) -> dict:
    """Reconcile exact review, current dependencies and the strict publication ledger."""
    binding = _promotion_workflow()
    _promotion_git(root, "merge-base", "--is-ancestor", binding["GITHUB_SHA"], "HEAD")
    raw = bundle_path.read_bytes()
    if (not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
            or hashlib.sha256(raw).hexdigest() != expected_sha256):
        raise ValueError("reviewed bundle SHA256 mismatch")
    bundle = json.loads(raw)
    if (bundle.get("schema") != "press.reviewed_bundle/v1"
            or bundle.get("repository") != _REVIEWED_REPO
            or bundle.get("slot_id") != expected_slot
            or not re.fullmatch(r"[0-9a-f]{40}", str(bundle.get("source_head")))):
        raise ValueError("reviewed bundle identity mismatch")
    relative = str(bundle.get("bundle_path") or "")
    if not relative.startswith(_REVIEWED_PREFIX) or not relative.endswith(".json"):
        raise ValueError("reviewed bundle path is outside the review directory")
    _promotion_path(root, relative)
    if _promotion_git(root, "show", f"HEAD:{relative}") != raw:
        raise ValueError("reviewed bundle differs from committed repository bytes")
    stage_raw = bundle["stage_json"].encode("utf-8")
    if hashlib.sha256(stage_raw).hexdigest() != bundle.get("stage_sha256"):
        raise ValueError("reviewed stage digest mismatch")
    item = _promotion_item(stage_raw, expected_slot)
    # A protected squash rewrites source ancestry. The committed bundle and
    # exact snapshot hashes bind the reviewed source; source_head is retained
    # provenance, while the actual workflow head is checked separately.
    if _promotion_dependencies(root, "HEAD", item) != bundle.get("dependencies"):
        raise ValueError("reviewed source dependencies changed")
    ledger = _paths(cfg, root)["ledger"]
    try:
        rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()] if ledger.exists() else []
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError("non-object publication row")
    except (ValueError, OSError) as exc:
        raise ValueError("publication ledger is unreadable") from exc
    own = [row for row in rows if row.get("id") == expected_slot]
    if (not published and own) or (published and len(own) != 1):
        raise ValueError("reviewed slot already published or publication missing")
    if published and (own[0].get("reviewed_promotion") or {}).get("bundle_sha256") != expected_sha256:
        raise ValueError("published slot has different reviewed bundle")
    refs = _promotion_refs(item)
    if any(refs.intersection(_promotion_refs(row)) for row in rows if row.get("id") != expected_slot):
        raise ValueError("reviewed source already published")
    return {"bundle": bundle, "item": item, "stage_raw": stage_raw}


def _check_promotion_staging(root: Path, cfg: dict, expected_slot: str, stage_raw: bytes,
                             *, require_stage: bool = False) -> Path:
    stage = _paths(cfg, root)["staging"]
    selected = _promotion_path(root, (stage / (expected_slot + ".json")).relative_to(root).as_posix())
    for path in stage.glob("*.json"):
        if path.name.startswith("_"):
            continue
        obj = json.loads(path.read_bytes())
        if path == selected:
            if path.read_bytes() != stage_raw:
                raise ValueError("reviewed stage bytes changed")
        elif isinstance(obj, dict) and obj.get("status") == "passed":
            raise ValueError("additional passed stage is not part of this promotion")
    if require_stage and (not selected.is_file() or selected.read_bytes() != stage_raw):
        raise ValueError("reviewed stage artifact missing or changed")
    return selected


def import_reviewed_bundle(root: Path, cfg: dict, bundle_path: Path,
                           expected_sha256: str, expected_slot: str) -> dict:
    checked = check_reviewed_bundle(root, cfg, bundle_path, expected_sha256, expected_slot)
    if _promotion_git(root, "rev-parse", "HEAD").decode().strip() != _promotion_workflow()["GITHUB_SHA"]:
        raise ValueError("reviewed artifact import head differs from workflow head")
    selected = _check_promotion_staging(root, cfg, expected_slot, checked["stage_raw"])
    # The ordinary validator rechecks the exact draft BEFORE any artifact write.
    report = validators.validate(checked["item"]["draft"], checked["item"]["slot"], cfg, root=root)
    if not report["ok"]:
        raise ValueError("reviewed stage no longer passes validators: " + ", ".join(report["failed"]))
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_bytes(checked["stage_raw"])
    (selected.parent / "_reviewed_bundle.json").write_bytes(bundle_path.read_bytes())
    (selected.parent / "_reviewed_workflow.json").write_text(json.dumps(_promotion_workflow()))
    summary = {"passed": 1, "slot_id": expected_slot, "bundle_sha256": expected_sha256}
    (selected.parent / "_run_summary.json").write_text(json.dumps(summary))
    return summary


def promote_reviewed_bundle(root: Path, cfg: dict, bundle_path: Path,
                            expected_sha256: str, expected_slot: str) -> dict:
    checked = check_reviewed_bundle(root, cfg, bundle_path, expected_sha256, expected_slot)
    stage = _paths(cfg, root)["staging"]
    if json.loads((stage / "_reviewed_workflow.json").read_bytes()) != _promotion_workflow():
        raise ValueError("reviewed workflow artifact belongs to a different run or head")
    _check_promotion_staging(root, cfg, expected_slot, checked["stage_raw"], require_stage=True)
    bundle = checked["bundle"]
    out = run_emit(root, cfg, reviewed_promotion={
        "bundle_sha256": expected_sha256, "stage_sha256": bundle["stage_sha256"],
        "source_head": bundle["source_head"],
    })
    if out["emitted"] != 1 or out["items"][0]["id"] != expected_slot:
        raise ValueError("reviewed promotion did not emit exactly the reviewed slot")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Media Network W1 press orchestrator.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--staging", action="store_true",
                      help="plan + write + validate into data/press/staging/ (default)")
    mode.add_argument("--emit", action="store_true",
                      help="publish PASSING staged drafts to content/seo/blog + site/blog")
    mode.add_argument("--prepare-reviewed-bundle", metavar="STAGE_JSON")
    mode.add_argument("--import-reviewed-bundle", metavar="BUNDLE_JSON")
    mode.add_argument("--promote-reviewed-bundle", metavar="BUNDLE_JSON")
    mode.add_argument("--check-reviewed-bundle", metavar="BUNDLE_JSON")
    ap.add_argument("--bundle-output", default="")
    ap.add_argument("--confirm-reviewed", action="store_true")
    ap.add_argument("--promotion-sha256", default="")
    ap.add_argument("--promotion-slot", default="")
    ap.add_argument("--published", action="store_true")
    ap.add_argument("--desks", default="",
                    help="comma-separated desk names (default: every desk in config)")
    ap.add_argument("--as-of", default="", help="run date YYYY-MM-DD (default: today)")
    ap.add_argument("--root", default="", help="repo root override (tests)")
    ap.add_argument("--max-slots", type=int, default=None,
                    help="cap the number of slots this run attempts")
    ap.add_argument("--single-attempt", action="store_true",
                    help="stage with one provider-adapter invocation per slot; "
                         "disable Anthropic SDK retries, Press fallback and "
                         "regeneration (Codex CLI internal requests are not bounded)")
    mode.add_argument("--stage-qbus-news", action="store_true",
                      help="ground one private Press draft from qualified qbus news; never emit")
    ap.add_argument("--qbus-slot", default="", help="existing planned Press slot JSON")
    ap.add_argument("--qbus-db", default="", help="canonical qbus database")
    ap.add_argument("--qbus-universe", default="", help="owner-supplied news universe JSON")
    ap.add_argument("--qbus-rights", action="append", default=[],
                    help="blog_draft rights receipt; repeat for additional publishers")
    ap.add_argument("--qbus-staging-dir", default="", help="dedicated private output directory")
    args = ap.parse_args(argv)
    qbus_inputs = (args.qbus_slot, args.qbus_db, args.qbus_universe,
                   args.qbus_rights, args.qbus_staging_dir)
    if args.stage_qbus_news:
        if not all(qbus_inputs):
            ap.error("--stage-qbus-news requires all --qbus-* source/output arguments")
        if args.desks or args.as_of or args.max_slots is not None:
            ap.error("private news staging uses exactly the supplied current-day slot")
    elif any(qbus_inputs):
        ap.error("--qbus-* arguments require --stage-qbus-news")
    if args.emit and args.single_attempt:
        ap.error("--single-attempt applies only to staging, not --emit")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    root = Path(args.root).resolve() if args.root else _REPO
    cfg = desk_planner.load_config(root)
    if not cfg:
        _annotate("error", "press_config",
                  "config/press.yml is missing or unparsable — press lane cannot run")
        return 1

    desks = [d.strip() for d in args.desks.split(",") if d.strip()] or None

    if args.stage_qbus_news:
        try:
            slot = json.loads(Path(args.qbus_slot).read_text(encoding="utf-8"))
            out = run_private_news_staging(
                root, cfg, slot=slot, database=args.qbus_db,
                universe_path=args.qbus_universe, receipt_paths=args.qbus_rights,
                staging_dir=args.qbus_staging_dir,
            )
        except (OSError, ValueError) as exc:
            _annotate("error", "press_private_news", str(exc))
            return 1
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 0 if out["passed"] == 1 else 1
    if args.prepare_reviewed_bundle:
        if not args.bundle_output:
            ap.error("--bundle-output is required")
        out = prepare_reviewed_bundle(root, Path(args.prepare_reviewed_bundle),
                                      Path(args.bundle_output), confirm_reviewed=args.confirm_reviewed)
    elif args.import_reviewed_bundle or args.promote_reviewed_bundle or args.check_reviewed_bundle:
        if not args.promotion_sha256 or not args.promotion_slot:
            ap.error("reviewed promotion requires --promotion-sha256 and --promotion-slot")
        path = Path(args.import_reviewed_bundle or args.promote_reviewed_bundle or args.check_reviewed_bundle)
        path = path if path.is_absolute() else root / path
        if args.import_reviewed_bundle:
            out = import_reviewed_bundle(root, cfg, path, args.promotion_sha256, args.promotion_slot)
        elif args.promote_reviewed_bundle:
            out = promote_reviewed_bundle(root, cfg, path, args.promotion_sha256, args.promotion_slot)
        else:
            check_reviewed_bundle(root, cfg, path, args.promotion_sha256, args.promotion_slot,
                                  published=args.published)
            out = {"verified": True}
    elif args.emit:
        out = run_emit(root, cfg)
    else:
        out = run_staging(root, cfg, desks=desks,
                          as_of=(args.as_of or None), max_slots=args.max_slots,
                          single_attempt=args.single_attempt)

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
