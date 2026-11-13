#!/usr/bin/env python3
"""Emit a local-only Alpha/RS research view to stdout, never canonical storage.

Example: python -m scripts.build_leadership_lab --source-ref <40-char-commit>
         --reference-session 2026-10-02 --format html > /path/to/local-preview.html
A redirected preview is not an accepted private production publication.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from engine.leadership_lab.catalyst import attach_catalyst_readiness
from engine.leadership_lab.context import compose_current_context
from engine.leadership_lab.earnings import attach_earnings_evidence
from engine.leadership_lab.groups import attach_group_leadership
from engine.leadership_lab.peers import attach_independent_peer_context
from engine.leadership_lab.recovery import recover_snapshot

ROOT = Path(__file__).resolve().parents[1]
OWNER_PATHS = {
    "alpha": "site/factordata/alpha.json",
    "factors": "site/factordata/factors.json",
    "baskets": "site/basketdata/baskets.json",
}
CONTEXT_PATHS = {
    "radar": "site/leaderradar/radar.json",
    "theme_state": "data/neuralweb/theme_state.json",
    "entry_radar_ledger": "data/entry_radar/ledger_state.json",
}
EPISODE_HEAD_PATH = "data/us_prophet_rank/episodes/HEAD.json"
_EPISODE_GENERATION_RE = re.compile(r"peg:[0-9a-f]{64}")


def _require_commit(repo_root: Path, ref: str, *, label: str) -> None:
    if not isinstance(ref, str) or not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise ValueError(f"{label} reference must be a full immutable commit SHA")
    try:
        kind = subprocess.check_output(
            ["git", "-C", str(repo_root), "cat-file", "-t", ref],
            stderr=subprocess.PIPE, timeout=20).strip()
        if kind != b"commit":
            raise ValueError(f"{label} reference must name a commit")
    except (subprocess.SubprocessError, OSError) as exc:
        raise ValueError(f"{label} commit unavailable") from exc


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> None:
    raise ValueError(f"non-finite JSON constant: {token}")


def _read_json_blob(repo_root: Path, ref: str, path: str, *, required: bool) -> tuple[object | None, dict]:
    try:
        raw = subprocess.check_output(
            ["git", "-C", str(repo_root), "show", f"{ref}:{path}"],
            stderr=subprocess.PIPE, timeout=20)
        payload = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        if required:
            raise ValueError(f"required owner source unavailable or malformed: {path}") from exc
        return None, {"path": path, "sha256": None, "git_blob": None,
                      "bytes": None, "read_status": "UNAVAILABLE"}
    return payload, {
        "path": path, "read_status": "READ", "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw), "git_blob": hashlib.sha1(f"blob {len(raw)}".encode() + bytes([0]) + raw).hexdigest(),
    }


def _read_current_issuer_master(repo_root: Path, ref: str):
    """Read the canonical Data OS issuer snapshot at one immutable Git commit.

    This is CURRENT issuer evidence only; its reader explicitly does not supply
    historical issuer lineage at an earlier candidate/earnings decision cut.
    Missing, corrupt, or oversized inputs fail closed for Earnings evidence.
    """
    source = "data/reference/security_master.parquet"
    unavailable = {
        "path": source, "read_status": "UNAVAILABLE",
        "sha256": None, "git_blob": None, "bytes": None,
        "identity_scope": "CURRENT_ONLY_NOT_HISTORICAL",
    }
    try:
        raw = subprocess.check_output(
            ["git", "-C", str(repo_root), "show", f"{ref}:{source}"],
            stderr=subprocess.PIPE, timeout=20)
        if not raw or len(raw) > 16_000_000:
            raise ValueError("native issuer master source size invalid")
        import pandas as pd
        from lib.dataos.identity import IssuerMaster
        records = pd.read_parquet(io.BytesIO(raw)).to_dict("records")
        master = IssuerMaster.from_records(records)
        if not master.rows:
            raise ValueError("native issuer master empty")
    except Exception:  # noqa: BLE001 — optional source read is fail-closed
        # No fallback to ticker parsing or caller-declared issuer identity.
        return None, unavailable
    return master, {
        "path": source, "read_status": "READ",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob": hashlib.sha1(f"blob {len(raw)}".encode() + bytes([0]) + raw).hexdigest(),
        "bytes": len(raw),
        "identity_scope": "CURRENT_ONLY_NOT_HISTORICAL",
    }


def build_view(
    source_ref: str, reference_session: str, *, repo_root: Path = ROOT,
    limit: int = 40, sort_by: str = "legacy_alpha", context_ref: str | None = None,
    earnings_details: dict | None = None,
    earnings_subject_bindings: dict | None = None,
    episode_store: Path | None = None,
) -> dict:
    """Read immutable recovery/context owner blobs; never use working-copy fallback."""
    repo_root = Path(repo_root)
    _require_commit(repo_root, source_ref, label="source")

    payloads, receipts = {}, {}
    for label, path in OWNER_PATHS.items():
        payload, receipt = _read_json_blob(
            repo_root, source_ref, path, required=(label == "alpha"))
        payloads[label], receipts[label] = payload, receipt

    view = recover_snapshot(payloads["alpha"], payloads["factors"], payloads["baskets"],
                            source_ref=source_ref, reference_session=reference_session,
                            limit=limit, sort_by=sort_by)
    for label, receipt in receipts.items():
        view["sources"].setdefault(label, {}).update(receipt)

    if context_ref is None:
        if earnings_details is not None or earnings_subject_bindings is not None:
            raise ValueError("earnings details require a native episode context")
        return view

    _require_commit(repo_root, context_ref, label="context")
    context_payloads, context_receipts = {}, {}
    for label, path in CONTEXT_PATHS.items():
        payload, receipt = _read_json_blob(repo_root, context_ref, path, required=False)
        context_payloads[label], context_receipts[label] = payload, receipt

    episode_head, head_receipt = _read_json_blob(
        repo_root, context_ref, EPISODE_HEAD_PATH, required=False)
    context_receipts["episode_head"] = head_receipt
    generation_id = None
    episode_book = None
    book_receipt = {
        "path": None, "sha256": None, "git_blob": None,
        "bytes": None, "read_status": "UNAVAILABLE",
    }
    if (
        isinstance(episode_head, dict)
        and episode_head.get("schema") == "prophet.candidate_episode_head/v1"
        and isinstance(episode_head.get("generation_id"), str)
        and _EPISODE_GENERATION_RE.fullmatch(episode_head["generation_id"]) is not None
    ):
        generation_id = episode_head["generation_id"]
        book_path = (
            "data/us_prophet_rank/episodes/generations/"
            f"{generation_id}/all_candidates.json"
        )
        episode_book, book_receipt = _read_json_blob(
            repo_root, context_ref, book_path, required=False)
    context_receipts["episode_book"] = book_receipt

    view = compose_current_context(
        view, context_payloads["radar"], context_payloads["theme_state"],
        context_ref=context_ref, episode_book=episode_book,
        episode_generation_id=generation_id)
    view["current_context"]["sources"] = context_receipts
    validation = {"status": "NOT_VALIDATED", "historical_identity_qualified": False}
    if episode_store is not None:
        from engine.leadership_lab.owner_binding import validate_native_episode_binding
        validation = validate_native_episode_binding(
            episode_store=episode_store, generation_id=generation_id,
            head_sha256=head_receipt.get("sha256"), book_sha256=book_receipt.get("sha256"))
    view["current_context"]["episode_book"]["source_validation"] = validation
    view = attach_independent_peer_context(view)
    view = attach_group_leadership(view)
    view = attach_catalyst_readiness(view, context_payloads["entry_radar_ledger"])
    if earnings_subject_bindings is not None and earnings_details is None:
        raise ValueError("earnings subject bindings require prebuilt owner details")
    if earnings_details is not None:
        native_master, master_receipt = _read_current_issuer_master(repo_root, context_ref)
        view["current_context"]["sources"]["issuer_master"] = master_receipt
        view = attach_earnings_evidence(
            view, earnings_details,
            subject_bindings_by_episode=earnings_subject_bindings,
            issuer_master=native_master)
    return view


def render_html(view: dict) -> str:
    """Self-contained review copy using house CSS, with no font/network fetches."""
    env = Environment(loader=FileSystemLoader(ROOT / "templates"),
                      autoescape=select_autoescape(("html", "xml", "j2")))
    shared_css = (ROOT / "templates/theme.css").read_text(encoding="utf-8")
    # Embed the canonical styles without requests to fonts or the production nav.
    # The original stylesheet is unmodified; no fonts are copied or distributed.
    shared_css = re.sub(r"@import\s+[^;]+;", "", shared_css)
    shared_css = re.sub(r"@font-face\s*\{[^}]*\}", "", shared_css)
    page_css = (ROOT / "templates/leadership_lab.css").read_text(encoding="utf-8")
    return env.get_template("leadership_lab.html.j2").render(
        view=view, theme_css=shared_css, page_css=page_css,
        sectors=sorted({row["sector"] for row in view["shortlist"]}),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", required=True, help="exact 40-character owner commit")
    parser.add_argument("--reference-session", required=True, help="explicit YYYY-MM-DD owner reference session")
    parser.add_argument("--context-ref", help="optional exact commit for current Radar/ThemeState context")
    parser.add_argument("--episode-store", type=Path, help="read-only native B1 store; complete generation must match context-ref")
    parser.add_argument("--format", choices=("json", "html"), default="json")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--sort-by", choices=("legacy_alpha", "legacy_rs"), default="legacy_alpha")
    args = parser.parse_args(argv)
    try:
        view = build_view(
            args.source_ref, args.reference_session, limit=args.limit,
            sort_by=args.sort_by, context_ref=args.context_ref, episode_store=args.episode_store)
        output = render_html(view) if args.format == "html" else json.dumps(
            view, ensure_ascii=False, indent=2, allow_nan=False)
    except (ValueError, OSError) as exc:
        print(f"Leadership Lab unavailable: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
