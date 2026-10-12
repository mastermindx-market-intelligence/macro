"""Read a reviewed White House source into a planning-only Press context.

This consumes the existing sentinel's retained bytes. It is not a rights
registry, publisher, provider or automatic feed admission. Qualification is a
reviewed input pinned by its caller; hashes prove identity, not legal authority.
The return is deliberately not a writer slot and ordinary plan() never calls it.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

from engine.whitehouse_feed import FEEDS, _slug_id


def _read_bound(path: Path, digest: str, limit: int) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
        raise ValueError("evidence requires a full SHA256")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("evidence must be a bounded regular file")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("evidence hash mismatch")
    return raw.decode("utf-8")


def _instant(value: str) -> datetime:
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        raise ValueError("source clocks must carry a timezone")
    return instant.astimezone(timezone.utc)


def _value(atom: str) -> Decimal:
    # Closed literal grammar for reviewed values. It performs no interpretation
    # of arbitrary prose and never evaluates an input expression.
    words = {"eleven": Decimal(11)}
    if atom in words:
        return words[atom]
    match = re.fullmatch(r"\$?(\d+(?:\.\d+)?)(B|M| billion| million|%)?", atom)
    if not match:
        raise ValueError("unsupported reviewed quantity literal")
    return Decimal(match[1])


def _dollars(atom: str) -> Decimal:
    value = _value(atom)
    if atom.endswith(("B", " billion")):
        return value * Decimal(1_000_000_000)
    if atom.endswith(("M", " million")):
        return value * Decimal(1_000_000)
    raise ValueError("share operands require explicit currency magnitudes")


def plan_whitehouse_candidate(*, document_path: Path, document_sha256: str,
                              qualification_path: Path, qualification_sha256: str,
                              policy_path: Path, as_of: str, root: Path,
                              cfg: dict | None = None) -> dict:
    from engine.press import desk_planner as planner
    from lib.pages import rendered_ticker_pages

    qualification = json.loads(_read_bound(qualification_path, qualification_sha256, 100_000))
    document = json.loads(_read_bound(document_path, document_sha256, 100_000))
    if not isinstance(document, dict) or not isinstance(qualification, dict):
        raise ValueError("source and qualification must be objects")
    q = qualification.get("external_planning")
    if not isinstance(q, dict) or set(q) != {
        "document_sha256", "feed_url", "normalization", "body_origin", "body_truncated",
        "reviewed_claims", "reviewed_tickers", "derived_share",
    }:
        raise ValueError("explicit external planning qualification required")
    retained = qualification["retained_public_source"]
    _read_bound(policy_path, retained["policy_file_sha256"], 100_000)
    rights = qualification.get("rights_basis", {})
    if (qualification.get("kind") != "editorial_source_qualification"
            or qualification.get("review", {}).get("result") != "accepted_as_editorial_candidate_only"
            or rights.get("qualification") != "government_authored_factual_reporting"
            or rights.get("policy_url") != "https://www.whitehouse.gov/copyright/"
            or not isinstance(rights.get("scope"), str) or not rights["scope"].strip()
            or rights.get("publication_approval") is not False
            or qualification.get("allow_stage") is not False
            or qualification.get("allow_emit") is not False):
        raise ValueError("source-specific candidate rights qualification required")
    expected = qualification["existing_feed_ingress"]["candidate"]
    for key in ("id", "guid", "title", "url", "published", "section"):
        if not isinstance(document.get(key), str) or not document[key] or document[key] != expected.get(key):
            raise ValueError("qualified source identity mismatch")
    url = urlsplit(document["url"])
    if (url.scheme != "https" or url.netloc != "www.whitehouse.gov"
            or url.query or url.fragment
            or not url.path.startswith(f"/{document['section']}/")
            or document["id"] != _slug_id(document["url"], document["published"])):
        raise ValueError("source is not its canonical White House document")
    feed = next((u for u, section in FEEDS if section == document["section"]), None)
    if q["feed_url"] != feed or q["feed_url"] != qualification["existing_feed_ingress"]["url"]:
        raise ValueError("source feed identity mismatch")
    body = document.get("body")
    if (document.get("schema") != "whitehouse.source_document.v1"
            or document.get("normalization") != q["normalization"]
            or q["normalization"] != "whitehouse-feed-text/v1"
            or document.get("body_origin") != q["body_origin"] or q["body_origin"] != "content_encoded"
            or document.get("body_truncated") is not False or q["body_truncated"] is not False
            or document.get("rights_status") != "unqualified"
            or document.get("allow_stage") is not False or document.get("allow_emit") is not False
            or not isinstance(body, str) or not body.strip() or len(body) > 12000
            or document_sha256 != q["document_sha256"]):
        raise ValueError("retained source provenance is incomplete or changed")
    body_sha = hashlib.sha256(body.encode()).hexdigest()
    if body_sha != document.get("body_sha256") or body_sha != retained["body_sha256"]:
        raise ValueError("source body hash mismatch")
    now, published = _instant(as_of), _instant(document["published"])
    observed = _instant(qualification["observed_at"])
    event_text = qualification.get("event_date")
    if not isinstance(event_text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", event_text):
        raise ValueError("reviewed event date must be an ISO calendar date")
    event_date = date.fromisoformat(event_text)
    cfg = cfg if cfg is not None else planner.load_config(root)
    desk = cfg["desks"]["brief"]
    if (published > now or observed > now or observed < published
            or event_date > published.date()):
        raise ValueError("event, publication and observation clocks are inconsistent")
    # A later publication must not move the reviewed event into a newer window.
    if (now.date() - event_date).days > int(desk["window_days"]):
        raise ValueError("event is outside the current Brief publication window")
    claims = q["reviewed_claims"]
    if not isinstance(claims, list) or not 1 <= len(claims) <= 20:
        raise ValueError("bounded reviewed source claims required")
    source_ref = "whitehouse:" + document["id"]
    facts, quantities = [], {}
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {"id", "literal", "quantity_literal"}:
            raise ValueError("reviewed claim fields mismatch")
        key, literal, atom = claim["id"], claim["literal"], claim["quantity_literal"]
        if (not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", key)
                or key in quantities or not isinstance(literal, str) or not literal
                or literal not in body or not isinstance(atom, str) or not atom
                or not re.search(r"(?<![\w.$])" + re.escape(atom) + r"(?![\w.])", literal)):
            raise ValueError("reviewed claim is not bound to a literal source span")
        value = _value(atom)
        quantities[key] = atom
        facts.append({"text": literal, "values": [str(value)], "tier": "third_party",
                      "ref": source_ref, "dated": qualification["event_date"]})
    derivation = q["derived_share"]
    if not isinstance(derivation, dict) or set(derivation) != {"numerators", "denominator", "percent"}:
        raise ValueError("external share derivation fields mismatch")
    numerators = derivation["numerators"]
    if (not isinstance(numerators, list) or not 1 <= len(numerators) <= len(claims)
            or any(not isinstance(k, str) or k not in quantities for k in numerators)
            or len(set(numerators)) != len(numerators)
            or derivation["denominator"] not in quantities):
        raise ValueError("external share operands are not reviewed claims")
    denominator = _dollars(quantities[derivation["denominator"]])
    if denominator <= 0:
        raise ValueError("external share denominator must be positive")
    share = sum((_dollars(quantities[k]) for k in numerators), Decimal(0)) / denominator * 100
    share_text = format(share.normalize(), "f")
    if not share.is_finite() or share_text != derivation["percent"]:
        raise ValueError("external share arithmetic differs")
    facts.append({"text": f"Reviewed commitments represent approximately {share_text}% of the stated package.",
                  "values": [share_text], "tier": "third_party", "ref": source_ref,
                  "dated": qualification["event_date"], "derived_from_external": True})
    tickers = q["reviewed_tickers"]
    if not isinstance(tickers, dict) or not tickers or len(tickers) > 10:
        raise ValueError("explicit reviewed ticker association required")
    available = rendered_ticker_pages(root / "site")
    links = []
    for ticker, source_name in tickers.items():
        if (not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker)
                or not isinstance(source_name, str) or not source_name or source_name not in body
                or ticker not in available):
            raise ValueError("reviewed ticker has no source association or rendered dossier")
        links.append(f"https://www.mastermind-x.com/stocks/{ticker}.html")
    pub, _ = planner.published_refs(root, cfg)
    staged, _ = planner.staged_refs(root, cfg)
    blocked = source_ref in pub | staged
    context = {
        "desk": "brief", "publication": desk["publication"], "byline": desk["byline"],
        "as_of": now.date().isoformat(), "min_words": desk["min_words"], "max_words": desk["max_words"],
        "min_anchored_receipts": desk["min_anchored_receipts"],
        "facts": facts, "raw_documents": [{"ref": source_ref, "text": body}],
        "primary_source": {"kind": "external", "name": "The White House", "url": document["url"], "ref": source_ref},
        "allowed_links": planner._allowed_links(cfg, links),
    }
    return {"schema": "press.external_candidate_plan.v1", "operation": "planning_only",
            "candidate_id": "press-external-" + planner.story_key(source_ref, document_sha256, qualification_sha256),
            "source_ref": source_ref, "document_sha256": document_sha256,
            "qualification_sha256": qualification_sha256, "body_sha256": body_sha,
            "source_clocks": {"event_date": event_text, "published_at": published.isoformat(),
                              "observed_at": observed.isoformat(), "as_of": now.isoformat()},
            "source_revisions": {source_ref: "sha256:" + document_sha256},
            "blocked_by_existing_coverage": blocked,
            "cadence_per_day": desk["cadence_per_day"], "cadence_consumed": False,
            "validation_context": context, "allow_stage": False, "allow_emit": False,
            "publication_approved": False}
