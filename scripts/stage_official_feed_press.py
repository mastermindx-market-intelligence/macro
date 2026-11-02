"""scripts/stage_official_feed_press.py — private staging for ONE qualified
official-feed (OCC or DOJ) Press candidate.

One explicit invocation stages exactly one already-qualified official candidate
through the incumbent Press runner.  This is a thin caller, not a second
pipeline: planning, validation, the checkpoint discipline, the staging tree and
the writer/validator rail are all the existing ones.

    python -m scripts.stage_official_feed_press \\
        --feed <retained occ_news.xml> --feed-sha256 <hex> \\
        --qualification <retained qualification.json> --qualification-sha256 <hex> \\
        --confirm-private-staging

What one invocation does, in order, and what it refuses:

  1. RE-PLANS.  ``plan_official_feed_candidate`` re-runs against the hash-bound
     retained feed and qualification bytes and CURRENT REAL TIME — the publisher
     clock, the observed-at clock and the Brief window are all re-checked.  The
     CLI deliberately offers no date flag, so this rail cannot be back-dated
     (test fixtures inject a clock in-process instead).
  2. REFUSES existing coverage.  The same source can never stage twice across
     dates or revisions: canonical published refs and live staged refs both
     block it, exactly as the ordinary planner is blocked.
  3. REFUSES a replay.  The staged slot id binds the canonical release URL, so a repeated
     invocation of the SAME candidate collides with the durable
     ``provider_started`` checkpoint and can never overwrite or replay it.
  4. REFUSES at the daily Brief cadence ceiling.  The ceiling counts TODAY'S
     existing Brief attempts in the canonical staging tree — whatever their
     status, including in_progress, quarantined and approval_required — plus
     today's published ledger rows, with a slot that is both staged and
     published counted once, by id.  Successes are not the unit of count;
     attempts are.
  5. STAGES one ordinary Brief slot through the EXISTING
     ``_stage_preplanned_slots`` rail into the NORMAL canonical staging root:
     durable exclusive checkpoint before the provider call, exactly one
     provider attempt (``single_provider_attempt=True`` with
     ``max_regenerations=0``), the ORDINARY Press run-token budget and circuit
     breaker.  The separate earnings 12k admitted-token contract is neither
     borrowed nor loosened, and ``run_admitted_earnings_staging`` is not used —
     this is not earnings and must never be labelled as earnings.

What one invocation never does: it never emits, never writes under content/ or
site/ or the ledger, and never promotes anything anywhere.

AUTHORITY.  A private staging action is authorized by the calling principal —
which is why the CLI demands an explicit ``--confirm-private-staging``.  The
qualification is CANDIDATE-ONLY: it records editorial acceptance of a source
candidate and conveys no public release grant.  The staged record therefore
carries ``provenance.admission_receipt.rail = "private_official_feed"`` with
``public_article_approved: false``, and ``scripts/run_press.py --emit`` fails
closed on that provenance — and on the ``official_feed:`` source-ref trail that
survives any provenance strip — even when the deterministic validators passed.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
# An existing later entry does not protect against an earlier foreign package.
sys.path.insert(0, str(_REPO))

from engine.press import desk_planner, validators, writer  # noqa: E402
from engine.press.official_feed_candidate import plan_official_feed_candidate  # noqa: E402
# The incumbent runner owns the staging rail and its small shared helpers; a
# thin caller imports them rather than forking copies that can drift.
from scripts.run_press import (  # noqa: E402
    _annotate, _env_int, _now, _paths, _stage_preplanned_slots,
)

log = logging.getLogger("stage_official_feed_press")

#: The provenance rail recorded on every staged record.  ``run_press --emit``
#: refuses this rail fail-closed; the constant must stay in sync with the
#: guard's ``_OFFICIAL_STAGE_RAIL`` there.
STAGE_RAIL = "private_official_feed"


def _official_slot(plan: dict, cfg: dict) -> dict:
    """The ordinary Brief slot this candidate stages as — planner-shaped.

    Every field is either copied from the plan's validation context (which the
    qualification pinned), a desk identity value from the shipped config, or a
    deterministic identity of the plan itself.  Nothing is invented: the facts,
    their dates, the primary source and the allowed links are the plan's own,
    and the raw source document is the agency's complete RSS summary.
    """
    desk_cfg = (cfg.get("desks") or {}).get("brief") or {}
    ctx = dict(plan["validation_context"])
    facts = [dict(f) for f in (ctx.get("facts") or [])]
    slot = dict(ctx)
    slot.update({
        "id": _stable_slot_id(plan),
        "cluster": str(desk_cfg.get("cluster") or "market-brief"),
        "model_key": str(desk_cfg.get("model_key") or "press_brief"),
        # The plan deliberately exposes no headline prose; the story block
        # carries only the reviewed event identity.  The writer is told the
        # external-source law by build_prompt from primary_source.kind.
        "story": {"kind": "official_feed", "event_date": plan["event_date"]},
        "sources": [plan["source_ref"], _stable_source_ref(plan)],
        "source_revisions": dict(plan["source_revisions"]),
        # Same identity shape the planner writes: the refs of the facts that
        # seed the piece (the official source ref plus any reviewed artifact).
        "seed_refs": sorted({str(f.get("ref")) for f in facts if f.get("ref")}),
        # No chronicle context is injected on this rail: the qualification is
        # the exact evidence contract, and unreviewed narrative must not reach
        # the writer prompt through a side door.
        "chronicle_context": {"lines": [], "narratives": [], "budget_used": 0,
                              "coverage": {"start": None, "end": None,
                                           "note": "official candidate rail: no chronicle context injected"}},
        "slug_hint": "official-" + str(plan["candidate_id"]).removeprefix("press-external-"),
    })
    return slot


def _stable_source_ref(plan: dict) -> str:
    # The publisher may change a GUID or feed bytes without creating a new
    # release. Persist this URL identity in the ordinary sources/ledger trail.
    url = plan["validation_context"]["primary_source"]["url"]
    return "official_feed:url:" + desk_planner.story_key(url)


def _stable_slot_id(plan: dict) -> str:
    return "press-official-" + _stable_source_ref(plan).rsplit(":", 1)[1]


def _canonical_paths(root: Path, cfg: dict) -> dict:
    paths = _paths(cfg, root)
    for key, rel in (("staging", "data/press/staging"),
                     ("ledger", "data/press/published.jsonl")):
        path = paths[key]
        if path != root / rel or any(p.is_symlink() for p in (path, *path.parents)
                                     if p != root and root in p.parents):
            raise ValueError(f"official staging requires canonical {key} path")
        if path.exists() and (not path.is_dir() if key == "staging" else not path.is_file()):
            raise ValueError(f"invalid canonical {key} path")
    return paths


def _accounting_rows(paths: dict) -> tuple[list[dict], list[dict]]:
    """Fail closed before a provider effect; corrupt records cannot free quota."""
    def read(path: Path, *, lines: bool = False) -> list[dict]:
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("not a regular accounting file")
            raw = path.read_text(encoding="utf-8")
            rows = ([json.loads(line) for line in raw.splitlines() if line.strip()]
                    if lines else [json.loads(raw)])
            for row in rows:
                if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                        or not row["id"] or not isinstance(row.get("desk"), str)
                        or not row["desk"]):
                    raise ValueError("missing accounting identity")
                for key in ("sources", "seed_refs"):
                    refs = row.get(key, [])
                    if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
                        raise ValueError("malformed accounting source refs")
            return rows
        except (OSError, UnicodeError, ValueError) as exc:
            raise ValueError(f"unreadable staging/ledger accounting: {path.name}") from exc

    staged = []
    for path in sorted(paths["staging"].glob("*.json")):
        if not path.name.startswith("_"):
            staged.extend(read(path))
    ledger = read(paths["ledger"], lines=True) if paths["ledger"].exists() else []
    return staged, ledger


def _attempt_day(row: dict, *, ledger: bool) -> str:
    """The UTC attempt/publication day, independent of the host's timezone.

    Legacy records without an instant use their explicit booked date. Never
    replace a malformed clock with a date that would silently free capacity.
    """
    key = "ts" if ledger else "staged_at"
    instant = row.get(key)
    try:
        if key in row:
            stamp = datetime.fromisoformat(instant.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timezone required")
            return stamp.astimezone(timezone.utc).date().isoformat()
        return date.fromisoformat(row["as_of"]).isoformat()
    except (TypeError, AttributeError, KeyError, ValueError) as exc:
        raise ValueError("Brief accounting requires an explicit valid attempt clock") from exc


def _brief_attempts_today(staged: list[dict], ledger: list[dict],
                          run_date: str, ceiling: int) -> tuple[int, int]:
    ids = {row["id"] for is_ledger, rows in ((False, staged), (True, ledger))
           for row in rows if row["desk"] == "brief"
           and _attempt_day(row, ledger=is_ledger) == run_date}
    return len(ids), int(ceiling)


def _same_source(row: dict, plan: dict) -> bool:
    if row.get("id") == _stable_slot_id(plan):
        return True
    refs = set(row.get("sources", [])) | set(row.get("seed_refs", []))
    if refs.intersection({plan["source_ref"], _stable_source_ref(plan)}):
        return True
    slot = row.get("slot") or {}
    primary = slot.get("primary_source") or {} if isinstance(slot, dict) else {}
    return (isinstance(primary, dict) and primary.get("url")
            == plan["validation_context"]["primary_source"]["url"])


def stage_official_feed_candidate(root, cfg, *, feed_path, feed_sha256,
                                  qualification_path, qualification_sha256,
                                  release_path=None, policy_path=None,
                                  now: datetime | None = None) -> dict:
    """Stage one qualified official-feed candidate as an ordinary Brief slot.

    Explicit invocation by the calling principal is the private-staging
    authorization.  The qualification is candidate-only: the staged record is
    written with public-article approval false and conveys no release grant.
    Every refusal below happens BEFORE any provider effect, so a refused run
    spends exactly zero tokens and reserves exactly zero slots.

    ``now`` is the current real time and is deliberately absent from the CLI:
    only an in-process caller (a test fixture) may inject a clock.
    """
    root = Path(root).resolve()
    paths = _canonical_paths(root, cfg)
    staged_rows, ledger_rows = _accounting_rows(paths)
    moment = now if now is not None else datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("injected clock must carry a timezone")

    # 1. Re-plan against the retained bytes and the given clock.  Bad hashes,
    #    stale/changed bytes, an unqualified source or an out-of-window event
    #    raise here — before any state is touched.
    plan = plan_official_feed_candidate(
        feed_path=Path(feed_path), feed_sha256=str(feed_sha256).lower(),
        qualification_path=Path(qualification_path),
        qualification_sha256=str(qualification_sha256).lower(),
        root=root, as_of=moment.isoformat(), cfg=cfg,
        release_path=release_path, policy_path=policy_path,
    )
    run_date = str(plan["validation_context"]["as_of"])
    identity = {
        "candidate_id": plan["candidate_id"],
        "staged_slot_id": _stable_slot_id(plan),
        "source_ref": plan["source_ref"],
        "feed_sha256": plan["feed_sha256"],
        "qualification_sha256": plan["qualification_sha256"],
        "event_date": plan["event_date"],
    }

    def _refuse(reason: str) -> dict:
        _annotate("warning", "press_official_stage_refused",
                  f"official feed staging refused: {plan['candidate_id']} — {reason}")
        return {"staged": False, "rail": STAGE_RAIL, "reason": reason,
                "run_date": run_date, "public_article_approved": False,
                "allow_emit": False, **identity}

    # A third-party-only candidate cannot satisfy the existing own-value gate.
    # Refuse before reserving its immutable attempt or spending provider tokens.
    context = plan["validation_context"]
    available = {value for value, tier in validators.fact_tier_index(context)
                 if tier == "first_party" and math.isfinite(value)}
    if not available:
        return _refuse("no usable first-party numeric context for the existing own-value gate")
    minimum = int(context.get("min_anchored_receipts")
                  or (cfg.get("validators") or {}).get("min_anchored_receipts") or 0)
    if len(available) < minimum:
        return _refuse(f"insufficient distinct first-party receipts ({len(available)} of {minimum})")

    # 2. Existing canonical coverage blocks the same source across dates and
    #    revisions — published first, then anything live in staging, with the
    #    plan's own blocked flag as the belt-and-braces backstop.
    published_refs, published_slugs = desk_planner.published_refs(root, cfg)
    staged_refs, staged_slugs = desk_planner.staged_refs(root, cfg)
    if any(_same_source(row, plan) for row in ledger_rows):
        return _refuse("source already has existing canonical coverage")
    if any(_same_source(row, plan) for row in staged_rows):
        return _refuse("source already sits in the canonical staging tree; replay refused")
    if plan["blocked_by_existing_coverage"]:
        return _refuse("source already has existing canonical coverage")

    # 3. A repeated slot can never overwrite or replay its checkpoint.
    slot_path = paths["staging"] / f"{_stable_slot_id(plan)}.json"
    if slot_path.exists():
        return _refuse("replay of an existing staged slot — the same slot identity "
                       "is already reserved")

    # 4. The daily Brief cadence ceiling counts today's attempts, not wins.
    consumed, ceiling = _brief_attempts_today(staged_rows, ledger_rows, run_date, plan["cadence_per_day"])
    if consumed >= ceiling:
        return _refuse(
            f"daily Brief cadence ceiling reached ({consumed} of {ceiling} "
            f"attempt(s) today, all statuses counted)")

    # 5. Stage through the incumbent rail: ordinary budget, ordinary breaker,
    #    one provider attempt, durable checkpoint before the call.
    receipt = {
        "rail": STAGE_RAIL,
        "private_staging_only": True,
        "public_article_approved": False,
        "authorized_by": "calling_principal",
        "planned_at": moment.isoformat(),
        "published_at": plan["published_at"],
        "item_url": plan["validation_context"]["primary_source"]["url"],
        "staged_at": _now(),
        **identity,
    }
    slot = _official_slot(plan, cfg)
    llm_cfg = (cfg.get("llm") or {})
    state = writer.RunState(
        # The ORDINARY Press budget — deliberately not the earnings rail's
        # separate 12k admitted contract, which is neither borrowed nor loosened.
        token_budget=_env_int("PRESS_RUN_TOKEN_BUDGET",
                              int(llm_cfg.get("run_token_budget") or 240_000)),
        breaker_threshold=_env_int("PRESS_CIRCUIT_BREAKER_FAILURES",
                                   int(llm_cfg.get("circuit_breaker_consecutive_failures") or 3)),
    )
    taken = desk_planner.taken_slugs(root) | published_slugs | staged_slugs
    summary = _stage_preplanned_slots(
        root, cfg,
        slots=[slot],
        staging_dir=paths["staging"],
        run_date=run_date,
        state=state,
        max_regenerations=0,
        taken_slugs=taken,
        admission_receipt=receipt,
        single_provider_attempt=True,
    )
    items = summary.get("items") or []
    status = str(items[0].get("status")) if items else ""
    _annotate("notice", "press_official_staged",
              f"official feed candidate staged PRIVATELY: {plan['candidate_id']} "
              f"status {status} (public article approval: false — no emit path)")
    return {
        "staged": True,
        "rail": STAGE_RAIL,
        "run_date": run_date,
        "status": status,
        "staging_path": str(slot_path.relative_to(root)),
        "public_article_approved": False,
        "allow_emit": False,
        "cadence": {"consumed_before": consumed, "ceiling": ceiling},
        "writer_state": summary.get("writer_state"),
        "summary": summary,
        **identity,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Privately stage ONE qualified official-feed (OCC or DOJ) Press "
                    "candidate through the incumbent runner. Never emits.")
    ap.add_argument("--feed", required=True, help="retained feed evidence file")
    ap.add_argument("--feed-sha256", required=True, help="SHA256 of the feed evidence")
    ap.add_argument("--qualification", required=True, help="retained qualification file")
    ap.add_argument("--qualification-sha256", required=True,
                    help="SHA256 of the qualification file")
    ap.add_argument("--release", help="DOJ only: retained full release bound by qualification")
    ap.add_argument("--policy", help="DOJ only: retained reuse policy bound by qualification")
    ap.add_argument("--root", default="", help="repo root override (tests)")
    ap.add_argument("--confirm-private-staging", action="store_true",
                    help="required acknowledgement: the calling principal authorizes "
                         "this PRIVATE staging action; the qualification is "
                         "candidate-only and conveys no public release grant")
    # Deliberately NO --as-of: this rail re-plans against current real time and
    # cannot be back-dated.  Test fixtures inject a clock in-process.
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    def _emit_result(out: dict) -> int:
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 0 if out.get("staged") else 1

    if not args.confirm_private_staging:
        _annotate("warning", "press_official_stage_refused",
                  "official feed staging refused: --confirm-private-staging is "
                  "required — a private staging action must be explicit")
        return _emit_result({"staged": False, "rail": STAGE_RAIL,
                             "reason": "private staging not confirmed by the caller",
                             "public_article_approved": False})

    root = Path(args.root).resolve() if args.root else _REPO
    cfg = desk_planner.load_config(root)
    if not cfg:
        _annotate("error", "press_config",
                  "config/press.yml is missing or unparsable — press lane cannot run")
        return 1

    try:
        out = stage_official_feed_candidate(
            root, cfg,
            feed_path=Path(args.feed), feed_sha256=args.feed_sha256,
            qualification_path=Path(args.qualification),
            qualification_sha256=args.qualification_sha256,
            release_path=Path(args.release) if args.release else None,
            policy_path=Path(args.policy) if args.policy else None,
        )
    except ValueError as exc:
        # Every planning refusal is a ValueError carrying its own reason.  The
        # provider was never reached: report and exit non-zero.
        return _emit_result({"staged": False, "rail": STAGE_RAIL, "reason": str(exc),
                             "public_article_approved": False})
    return _emit_result(out)


if __name__ == "__main__":
    sys.exit(main())
